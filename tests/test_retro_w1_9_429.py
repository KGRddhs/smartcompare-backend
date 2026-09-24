"""R-AUTH retro-fix, unit W1-9 429 (lockout path) -- RED phase.

Spec: the retroactive adversary report for ``W1-9 429 contract on both classes
(PR #152, merge a4e7b08b), lockout path focus``, under the orchestrator's
binding ruling **W1-9b -- UNFLAGGED (a permanent lockout is a defect)**:

* lockout ARMING is ATOMIC: a failed-login increment can never exist without
  its ``LOCKOUT_WINDOW_SECONDS`` window (``SET key 0 EX <window> NX`` + ``INCR``,
  or a pipeline / MULTI -- the pinned ``upstash-redis`` 1.7.0 supports
  ``set(..., nx=True, ex=...)``, ``expire(..., nx=True)``, ``pttl``,
  ``pipeline()`` and ``multi()`` -- measured on the venv);
* ``check_account_locked`` treats a missing TTL (``-1``) as "re-arm with the
  window", never "locked forever";
* the W1-9 lockout 429 then carries a real window: ``Retry-After`` header ==
  ``retry_after_seconds`` body field, positive, at most window + 1.

WHAT IS WRONG TODAY (re-measured on origin/main 1c6f6796, pinned venv)
---------------------------------------------------------------------
``auth_service.track_failed_login`` does ``count = incr(key)`` and then
``expire(key, 900)`` ONLY when ``count == 1``, over Upstash REST (two HTTP
round trips, ``rest_retries=0`` under the bounded transport), with every
exception swallowed. One lost EXPIRE -- or an INCR that ran on the server but
timed out on the client -- leaves a key with NO TTL for good. Five failed
logins over ANY span of time then lock the account permanently, and
``check_account_locked`` returns ``retry_after = max(ttl=-1, 0) = 0``, which
``error_handler._detail_retry_after`` refuses, so the 429 ships with no
``Retry-After`` and no ``retry_after_seconds``. ``clear_failed_logins`` only
runs after a success that the lock itself blocks, so there is no way out.

Reviewer's reproduction, re-run here as ``test_w1_9b_lost_expire_*``: an
in-memory Upstash fake whose ``expire()`` raises ``TimeoutError`` on its first
call, POST /auth/login x7 with ``login_user`` failing -> today
``[401 x5, 429 x2]``, no Retry-After, key ttl -1, count 5.

THE FAKE
--------
``FakeUpstash`` mirrors the upstash-redis 1.7.0 surface that a lockout
implementation can reasonably use -- ``get``, ``set`` (nx/xx/ex/px/keepttl),
``setex``, ``incr``, ``incrby``, ``expire`` (nx/xx/gt/lt), ``ttl``, ``pttl``,
``delete``, ``exists``, ``pipeline()`` / ``multi()`` with ``exec()`` -- with
REAL Redis semantics (TTL -2 missing / -1 no expiry / rounded-to-nearest
seconds, as ``ttlGenericCommand`` does) on a controllable clock. ``eval`` is
deliberately NOT implemented (raises ``NotImplementedError``): a Lua-based
green must extend the fake, visibly.

Fault injection is by COMMAND NAME and occurrence, in two modes: ``before``
(the command never reached Redis) and ``after`` (Redis applied it, the client
timed out). A pipeline/MULTI ``exec`` counts every command in its stack, and
a fault on any of them applies to the whole batch (atomic semantics). So each
RED node describes a failure of the NETWORK, not of a particular
implementation.

ZERO NETWORK: an autouse guard blocks every non-loopback ``connect`` and
``getaddrinfo`` and fails the node on any attempt.
"""
from __future__ import annotations

import math
import socket
import threading
from collections import Counter
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api import auth_routes
from app.api.auth_routes import get_current_user
from app.main import app
from app.middleware.rate_limiter import limiter
from app.services import auth_service, cache_service

LOGIN_URL = "/api/v1/auth/login"
EMAIL_URL = "/api/v1/auth/email"
PASSWORD_URL = "/api/v1/auth/password"

WINDOW = auth_service.LOCKOUT_WINDOW_SECONDS  # 900
THRESHOLD = auth_service.LOCKOUT_THRESHOLD  # 5

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}


# ===========================================================================
# autouse: zero network
# ===========================================================================
@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: List[str] = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _host_of(address: Any) -> str:
        if isinstance(address, tuple) and address:
            return str(address[0])
        return str(address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is None or str(host) in _LOOPBACK_HOSTS:
            return real_getaddrinfo(host, *args, **kwargs)
        attempts.append("getaddrinfo:" + str(host))
        raise OSError("zero-network guard: getaddrinfo(" + str(host) + ") blocked")

    def guarded_connect(self, address):
        if self.family == getattr(socket, "AF_UNIX", object()) or _host_of(address) in _LOOPBACK_HOSTS:
            return real_connect(self, address)
        attempts.append("connect:" + _host_of(address))
        raise OSError("zero-network guard: connect(" + _host_of(address) + ") blocked")

    def guarded_connect_ex(self, address):
        if self.family == getattr(socket, "AF_UNIX", object()) or _host_of(address) in _LOOPBACK_HOSTS:
            return real_connect_ex(self, address)
        attempts.append("connect_ex:" + _host_of(address))
        raise OSError("zero-network guard: connect_ex(" + _host_of(address) + ") blocked")

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    yield
    assert not attempts, "zero-network guard: non-loopback network attempted: " + repr(attempts)


# ===========================================================================
# the Upstash fake
# ===========================================================================
class FakeUpstash:
    _WRITE_COMMANDS = {"set", "setex", "incr", "incrby", "expire", "delete"}

    def __init__(self) -> None:
        self.now = 1_800_000_000.0
        self.data: Dict[str, str] = {}
        self.expire_at: Dict[str, float] = {}
        self.log: List[tuple] = []
        self.faults: List[Dict[str, Any]] = []
        self.ttl_override: Optional[int] = None
        self.raise_everything = False
        self._counts: Counter = Counter()
        self._lock = threading.RLock()

    # -- test controls -------------------------------------------------------
    def add_fault(self, cmd: str, occurrence: int = 1, mode: str = "before", exc: Optional[BaseException] = None):
        self.faults.append({
            "cmd": cmd, "occurrence": occurrence, "mode": mode,
            "exc": exc or TimeoutError("fake upstash: " + cmd + " timed out"), "fired": False,
        })

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def seed(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        self.data[key] = value
        if ttl is None:
            self.expire_at.pop(key, None)
        else:
            self.expire_at[key] = self.now + ttl

    def raw_ttl(self, key: str) -> int:
        with self._lock:
            return self._ttl(key)

    # -- internals -----------------------------------------------------------
    def _purge(self, key: str) -> None:
        exp = self.expire_at.get(key)
        if exp is not None and self.now >= exp:
            self.data.pop(key, None)
            self.expire_at.pop(key, None)

    def _ttl(self, key: str) -> int:
        self._purge(key)
        if key not in self.data:
            return -2
        exp = self.expire_at.get(key)
        if exp is None:
            return -1
        ms = round((exp - self.now) * 1000)
        return (ms + 500) // 1000  # Redis ttlGenericCommand rounding

    def _pttl(self, key: str) -> int:
        self._purge(key)
        if key not in self.data:
            return -2
        exp = self.expire_at.get(key)
        if exp is None:
            return -1
        return round((exp - self.now) * 1000)

    def _apply(self, name: str, args: tuple, kwargs: dict):
        if name == "get":
            (key,) = args
            self._purge(key)
            return self.data.get(key)
        if name == "set":
            key, value = args[0], args[1]
            nx, xx = kwargs.get("nx"), kwargs.get("xx")
            ex, px = kwargs.get("ex"), kwargs.get("px")
            keepttl = kwargs.get("keepttl")
            self._purge(key)
            exists = key in self.data
            if (nx and exists) or (xx and not exists):
                return False
            self.data[key] = str(value)
            if ex is not None:
                self.expire_at[key] = self.now + int(ex)
            elif px is not None:
                self.expire_at[key] = self.now + int(px) / 1000.0
            elif not keepttl:
                self.expire_at.pop(key, None)
            return True
        if name == "setex":
            key, seconds, value = args
            self.data[key] = str(value)
            self.expire_at[key] = self.now + int(seconds)
            return True
        if name in ("incr", "incrby"):
            key = args[0]
            inc = int(args[1]) if name == "incrby" else 1
            self._purge(key)
            new = int(self.data.get(key, "0")) + inc
            self.data[key] = str(new)
            return new
        if name == "expire":
            key, seconds = args[0], int(args[1])
            self._purge(key)
            if key not in self.data:
                return False
            current = self.expire_at.get(key)
            if kwargs.get("nx") and current is not None:
                return False
            if kwargs.get("xx") and current is None:
                return False
            new_exp = self.now + seconds
            if kwargs.get("gt") and (current is None or new_exp <= current):
                return False
            if kwargs.get("lt") and current is not None and new_exp >= current:
                return False
            self.expire_at[key] = new_exp
            return True
        if name == "ttl":
            if self.ttl_override is not None:
                return self.ttl_override
            return self._ttl(args[0])
        if name == "pttl":
            if self.ttl_override is not None:
                return self.ttl_override * 1000 if self.ttl_override > 0 else self.ttl_override
            return self._pttl(args[0])
        if name == "delete":
            n = 0
            for key in args:
                self._purge(key)
                if key in self.data:
                    n += 1
                    self.data.pop(key, None)
                    self.expire_at.pop(key, None)
            return n
        if name == "exists":
            n = 0
            for key in args:
                self._purge(key)
                n += key in self.data
            return n
        raise AssertionError("FakeUpstash: unknown command " + name)  # pragma: no cover

    def _exec(self, commands: List[tuple]) -> List[Any]:
        with self._lock:
            if self.raise_everything:
                raise TimeoutError("fake upstash: unavailable")
            triggered = []
            for name, _a, _k in commands:
                self._counts[name] += 1
                for f in self.faults:
                    if not f["fired"] and f["cmd"] == name and self._counts[name] == f["occurrence"]:
                        f["fired"] = True
                        triggered.append(f)
            self.log.extend(commands)
            for f in triggered:
                if f["mode"] == "before":
                    raise f["exc"]
            results = [self._apply(n, a, k) for n, a, k in commands]
            for f in triggered:
                raise f["exc"]
            return results

    # -- the upstash-redis surface ------------------------------------------
    def get(self, key):
        return self._exec([("get", (key,), {})])[0]

    def set(self, key, value, nx=None, xx=None, get=None, ex=None, px=None, exat=None, pxat=None, keepttl=None):
        if exat is not None or pxat is not None or get:
            raise NotImplementedError("FakeUpstash.set: exat/pxat/get not modelled -- extend the fake")
        return self._exec([("set", (key, value), {"nx": nx, "xx": xx, "ex": ex, "px": px, "keepttl": keepttl})])[0]

    def setex(self, key, seconds, value):
        return self._exec([("setex", (key, seconds, value), {})])[0]

    def incr(self, key):
        return self._exec([("incr", (key,), {})])[0]

    def incrby(self, key, increment):
        return self._exec([("incrby", (key, increment), {})])[0]

    def expire(self, key, seconds, nx=False, xx=False, gt=False, lt=False):
        return self._exec([("expire", (key, seconds), {"nx": nx, "xx": xx, "gt": gt, "lt": lt})])[0]

    def ttl(self, key):
        return self._exec([("ttl", (key,), {})])[0]

    def pttl(self, key):
        return self._exec([("pttl", (key,), {})])[0]

    def delete(self, *keys):
        return self._exec([("delete", keys, {})])[0]

    def exists(self, *keys):
        return self._exec([("exists", keys, {})])[0]

    def eval(self, *_a, **_k):
        raise NotImplementedError("FakeUpstash: EVAL is not modelled -- a Lua green must extend this fake")

    evalsha = eval

    def pipeline(self):
        return _FakePipeline(self)

    def multi(self):
        return _FakePipeline(self)


class _FakePipeline:
    _QUEUEABLE = ("get", "set", "setex", "incr", "incrby", "expire", "ttl", "pttl", "delete", "exists")

    def __init__(self, parent: FakeUpstash) -> None:
        self._parent = parent
        self._stack: List[tuple] = []

    def __getattr__(self, name):
        if name not in self._QUEUEABLE:
            raise AttributeError(name)

        def _queue(*args, **kwargs):
            if name == "set":
                args = (args[0], args[1])
                kwargs = {k: kwargs.get(k) for k in ("nx", "xx", "ex", "px", "keepttl")}
            elif name == "expire":
                kwargs = {k: kwargs.get(k, False) for k in ("nx", "xx", "gt", "lt")}
            self._stack.append((name, tuple(args), dict(kwargs)))
            return self

        return _queue

    def exec(self):
        stack, self._stack = self._stack, []
        return self._parent._exec(stack)

    execute = exec

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


# ===========================================================================
# fixtures / helpers
# ===========================================================================
@pytest.fixture
def fake(monkeypatch):
    redis = FakeUpstash()
    monkeypatch.setattr(auth_service, "redis_client", redis)
    monkeypatch.setattr(cache_service, "redis_client", redis)
    return redis


@pytest.fixture
def audit(monkeypatch):
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(auth_routes, "log_audit_event", mock)
    return mock


@pytest.fixture
def failing_login(monkeypatch):
    mock = AsyncMock(return_value={"success": False, "error": "Invalid email or password"})
    monkeypatch.setattr(auth_routes, "login_user", mock)
    return mock


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _key(email: str) -> str:
    return auth_service._login_attempt_key(email)


def _login(client, email: str):
    limiter.reset()  # POST /login is 5/minute; the lockout is what is under test
    return client.post(LOGIN_URL, json={"email": email, "password": "wrong-password-1"})


def _assert_real_window(resp, where: str) -> int:
    body = resp.json()
    assert resp.status_code == 429 and body.get("code") == "ACCOUNT_LOCKED", where + ": " + resp.text
    header = resp.headers.get("Retry-After")
    field = body.get("retry_after_seconds")
    assert header is not None and field is not None, (
        where + ": a locked 429 must carry Retry-After AND retry_after_seconds; headers="
        + repr(dict(resp.headers)) + " body=" + resp.text
    )
    assert header == str(field), where + ": header " + repr(header) + " != body " + repr(field)
    assert isinstance(field, int) and 0 < field <= WINDOW + 1, where + ": window out of range: " + repr(field)
    return field


# ===========================================================================
# W1-9b RED -- a lost arming step must never make a permanent lock
# ===========================================================================
def test_w1_9b_lost_expire_does_not_make_a_permanent_lock(client, fake, audit, failing_login):
    """RED -- the reviewer's exact reproduction. ``expire()`` raises
    ``TimeoutError`` on its first call (the command never reached Redis).

    MEASURED TODAY: statuses ``[401 x5, 429 x2]``, both 429s WITHOUT
    ``Retry-After`` / ``retry_after_seconds``, the key's TTL is -1 and its
    count 5 -- for good."""
    email = "w19b-lost-expire@example.com"
    fake.add_fault("expire", occurrence=1, mode="before")
    statuses, locked = [], []
    for _ in range(7):
        resp = _login(client, email)
        statuses.append(resp.status_code)
        if resp.status_code == 429:
            locked.append(resp)
    assert statuses == [401] * THRESHOLD + [429, 429], statuses  # the lock itself is unchanged
    for i, resp in enumerate(locked):
        _assert_real_window(resp, "locked attempt " + str(i + 1))
    ttl = fake.raw_ttl(_key(email))
    assert 0 < ttl <= WINDOW, "the counter key must carry its window, never live forever; ttl=" + str(ttl)


def test_w1_9b_incr_applied_but_client_timed_out_is_not_permanent(client, fake, audit, failing_login):
    """RED. The FIRST ``incr`` reaches Redis and is applied, but the client times
    out (mode ``after``) -- the reviewer's "INCR that ran on the server but
    timed out on the client". MEASURED TODAY: the key holds ``1`` with TTL -1,
    ``expire`` is never sent (it only runs when the client SEES count == 1),
    and every later failure piles onto a key that never expires."""
    email = "w19b-incr-after@example.com"
    fake.add_fault("incr", occurrence=1, mode="after")
    resp = _login(client, email)
    assert resp.status_code == 401, resp.text
    ttl = fake.raw_ttl(_key(email))
    assert ttl != -1, (
        "a failed-login increment must never exist without its window; key="
        + repr(fake.data.get(_key(email))) + " ttl=" + str(ttl)
    )


def test_w1_9b_failures_hours_apart_do_not_accumulate_into_a_lock(client, fake, audit, failing_login):
    """RED. "Five failed logins over ANY span of time then lock the account
    permanently." One failure whose arming was lost, two HOURS of silence, then
    four more failures: the account must NOT be locked on the sixth attempt,
    because the first failure's 15-minute window ended long ago.

    MEASURED TODAY: the sixth attempt is 429 ACCOUNT_LOCKED (count 5, TTL -1)."""
    email = "w19b-span@example.com"
    fake.add_fault("incr", occurrence=1, mode="after")
    assert _login(client, email).status_code == 401
    fake.advance(2 * 3600)
    for _ in range(4):
        assert _login(client, email).status_code == 401
    sixth = _login(client, email)
    assert sixth.status_code == 401, (
        "failures two hours apart must not combine into one lock window; sixth attempt got "
        + str(sixth.status_code) + " " + sixth.text + " (count=" + repr(fake.data.get(_key(email)))
        + ", ttl=" + str(fake.raw_ttl(_key(email))) + ")"
    )


@pytest.mark.parametrize("route", ["login", "email", "password"])
def test_w1_9b_existing_ttl_less_lock_is_rearmed_not_permanent(client, fake, audit, failing_login, monkeypatch, route):
    """RED -- the ``check_account_locked`` half of the ruling, on all three
    lockout routes. Keys that are ALREADY stuck in prod Redis (count >= 5, TTL
    -1) must be re-armed with the window on the next check, and the 429 must
    carry that window.

    MEASURED TODAY: 429 ACCOUNT_LOCKED with no Retry-After / no
    retry_after_seconds, and the key keeps TTL -1."""
    email = "w19b-stuck-" + route + "@example.com"
    fake.seed(_key(email), "5", ttl=None)
    if route == "login":
        resp = _login(client, email)
    else:
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "user-w19b-" + route, "email": email, "access_token": "at-w19b"}
        if route == "email":
            resp = client.put(EMAIL_URL, json={"new_email": "new-" + email, "current_password": "x"})
        else:
            resp = client.put(PASSWORD_URL, json={"current_password": "x", "new_password": "Abcdefgh1234"})
    _assert_real_window(resp, route + " with a TTL-less stuck key")
    ttl = fake.raw_ttl(_key(email))
    assert 0 < ttl <= WINDOW, "a TTL-less lock must be re-armed with the window; ttl=" + str(ttl)


@pytest.mark.parametrize("raced_ttl", [-2, 0])
def test_w1_9b_locked_429_is_never_windowless(client, fake, audit, failing_login, raced_ttl):
    """RED -- "the lockout 429 then carries a real retry_after". GET says the
    account is at the threshold, then TTL reads ``-2`` (the key expired between
    the two round trips) or ``0`` (it is about to). Either the caller is let
    through (the lock has lifted) or the 429 carries a positive window -- a
    windowless ACCOUNT_LOCKED 429 is never acceptable.

    MEASURED TODAY: 429 ACCOUNT_LOCKED with no Retry-After for both values.
    (Report defect 3; the rounding half of that defect is out of this ruling.)"""
    email = "w19b-race" + str(raced_ttl) + "@example.com"
    fake.seed(_key(email), "5", ttl=WINDOW)
    fake.ttl_override = raced_ttl
    resp = _login(client, email)
    if resp.status_code == 429:
        _assert_real_window(resp, "ttl raced to " + str(raced_ttl))
    else:
        assert resp.status_code == 401, resp.text  # let through to the (failing) login


# ===========================================================================
# PINS -- green today, must stay green
# ===========================================================================
def test_pin_happy_path_lock_after_threshold_with_real_window(client, fake, audit, failing_login):
    """PIN: no faults -> ``[401 x5, 429 x2]``, every 429 carries the window,
    the key carries a TTL <= the window, count == threshold."""
    email = "pin-happy@example.com"
    statuses, locked = [], []
    for _ in range(7):
        resp = _login(client, email)
        statuses.append(resp.status_code)
        if resp.status_code == 429:
            locked.append(resp)
    assert statuses == [401] * THRESHOLD + [429, 429]
    for resp in locked:
        field = _assert_real_window(resp, "happy path")
        assert field >= WINDOW - 1
    assert 0 < fake.raw_ttl(_key(email)) <= WINDOW
    assert int(fake.data[_key(email)]) == THRESHOLD, "locked attempts must not keep counting"
    assert failing_login.await_count == THRESHOLD, "a locked attempt must never reach login_user"


def test_pin_live_window_is_not_extended(client, fake, audit, failing_login):
    """PIN: re-arming is ONLY for a missing TTL. A locked key with 300 s left
    reports ~300 s and keeps ~300 s -- a check never extends a live window."""
    email = "pin-live-window@example.com"
    fake.seed(_key(email), "5", ttl=300)
    field = _assert_real_window(_login(client, email), "live window")
    assert 299 <= field <= 302, field
    assert 0 < fake.raw_ttl(_key(email)) <= 300


def test_pin_window_expiry_unlocks(client, fake, audit, failing_login):
    """PIN: once the window passes, the account is unlocked and counting restarts."""
    email = "pin-expiry@example.com"
    fake.seed(_key(email), "5", ttl=WINDOW)
    assert _login(client, email).status_code == 429
    fake.advance(WINDOW + 1)
    assert _login(client, email).status_code == 401
    assert fake.data.get(_key(email)) == "1"
    assert 0 < fake.raw_ttl(_key(email)) <= WINDOW


def test_pin_success_clears_the_counter(client, fake, audit, failing_login, monkeypatch):
    """PIN: a successful login deletes the counter."""
    email = "pin-clear@example.com"
    for _ in range(3):
        assert _login(client, email).status_code == 401
    assert fake.data.get(_key(email)) == "3"
    ok = {"success": True, "user": {"id": "u-pin", "email": email, "preferences_completed": False},
          "session": {"access_token": "a", "refresh_token": "r", "expires_at": 1}}
    monkeypatch.setattr(auth_routes, "login_user", AsyncMock(return_value=ok))
    resp = _login(client, email)
    assert resp.status_code == 200, resp.text
    assert _key(email) not in fake.data


def test_pin_track_failed_login_return_contract(fake):
    """PIN: ``track_failed_login`` keeps its ``{"locked", "attempts"}`` contract."""
    import asyncio

    email = "pin-contract@example.com"
    results = [asyncio.run(auth_service.track_failed_login(email)) for _ in range(THRESHOLD)]
    assert [r["attempts"] for r in results] == [1, 2, 3, 4, 5]
    assert [r["locked"] for r in results] == [False, False, False, False, True]
    assert asyncio.run(auth_service.check_account_locked(email))["locked"] is True
    assert asyncio.run(auth_service.check_account_locked("other-" + email)) == {"locked": False, "retry_after": 0}


def test_pin_no_redis_fails_open(client, monkeypatch, audit, failing_login):
    """PIN: ``redis_client is None`` -> lockout fails open (never locks)."""
    monkeypatch.setattr(auth_service, "redis_client", None)
    email = "pin-noredis@example.com"
    assert [_login(client, email).status_code for _ in range(7)] == [401] * 7


def test_pin_redis_down_fails_open(client, fake, audit, failing_login):
    """PIN: every Redis call raising -> lockout fails open (never locks)."""
    fake.raise_everything = True
    email = "pin-redisdown@example.com"
    assert [_login(client, email).status_code for _ in range(7)] == [401] * 7


@pytest.mark.parametrize("route", ["email", "password"])
def test_pin_put_routes_carry_the_window_through_the_real_check(client, fake, audit, route):
    """PIN (report defect 4: kills the ``retry_after`` detail-key rename
    mutation that left 23 tests green). PUT /auth/email and PUT /auth/password
    run the REAL ``check_account_locked`` against a locked key with a live TTL
    and must emit ``Retry-After`` == ``retry_after_seconds``."""
    email = "pin-put-" + route + "@example.com"
    fake.seed(_key(email), "5", ttl=600)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "user-pin-" + route, "email": email, "access_token": "at-pin"}
    if route == "email":
        resp = client.put(EMAIL_URL, json={"new_email": "new-" + email, "current_password": "x"})
    else:
        resp = client.put(PASSWORD_URL, json={"current_password": "x", "new_password": "Abcdefgh1234"})
    field = _assert_real_window(resp, "PUT /" + route)
    assert 599 <= field <= 602, field


def test_pin_fake_models_redis_ttl_rounding():
    """Self-check of the fake (not of the product): TTL rounds to nearest like
    Redis, PTTL is exact, -1 / -2 are distinguished."""
    r = FakeUpstash()
    r.seed("k", "1", ttl=None)
    assert r.ttl("k") == -1 and r.pttl("k") == -1
    assert r.ttl("missing") == -2
    r.expire("k", 10)
    r.advance(9.4)
    assert r.ttl("k") == 1 and r.pttl("k") == 600
    r.advance(0.2)
    assert r.ttl("k") == 0 and math.isclose(r.pttl("k"), 400, abs_tol=1)
    p = r.pipeline()
    p.set("n", 0, nx=True, ex=30)
    p.incr("n")
    assert p.exec() == [True, 1] and r.ttl("n") == 30

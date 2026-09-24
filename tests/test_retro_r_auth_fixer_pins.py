"""R-AUTH retro FIXER pins -- the adversary's two defects and its four
tests-that-prove-nothing rows, each folded into a load-bearing node.

Defect 1 (major): with ``ENABLE_LOGOUT_UPSTREAM_REVOCATION`` on, the
expired-bearer logout branch was an UNAUTHENTICATED, UNTHROTTLED way to make
the server POST /auth/v1/token (gotrue's per-IP refresh budget, shared by the
whole fleet from the Railway IP), write the Redis blacklist and log a WARNING
-- 40 forged requests -> 40 of each (reproduced). The branch now spends the
``/auth/refresh`` budget (10/minute per limiter key) from its own bucket BEFORE
anything upstream or in Redis; over budget it re-raises the route's original
401.

Defect 2 (minor): ``track_failed_login``'s ``SET NX EX`` cannot arm a legacy
counter already stuck without a TTL, nor a counter that expired between the SET
and the INCR (INCR recreates it TTL-less). An ``EXPIRE key window NX`` after the
INCR closes both, never extends a live window, and a failure of it never turns
an applied count into "attempts 0".

Proves-nothing rows folded in: the 503 body text of a TYPE-classified refresh
failure; the TYPE-only logging of the expired-branch backstop and of the
refresh WARNING; the exact ``exp`` boundary; and the ``status_code != 401``
guard in ``_LogoutRoute``.

ZERO NETWORK: an autouse guard blocks every non-loopback ``connect`` and
``getaddrinfo`` and fails the node on any attempt.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import socket
from types import SimpleNamespace
from typing import Any, List

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError, AuthRetryableError, UserDoesntExist

from app.api import auth_routes
from app.api.auth_routes import get_current_user
from app.main import app
from app.middleware.rate_limiter import limiter
from app.services import auth_service, cache_service
from tests.test_retro_w1_4_server import (
    API_VERSION_HEADER,
    _FakeGoTrue,
    _live_supabase_timers,
    make_jwt,
)
from tests.test_retro_w1_9_429 import FakeUpstash

LOGOUT_URL = "/api/v1/auth/logout"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_FLAG = "ENABLE_LOGOUT_UPSTREAM_REVOCATION"
REUSE_FLAG = "ENABLE_SUPABASE_CLIENT_REUSE"
PROXY_FLAG = "ENABLE_PROXY_AWARE_RATELIMIT"
OK_BODY = {"success": True, "message": "Logged out successfully"}
TRANSIENT_ERROR_TEXT = "Connection failed. Please try again."
REFRESH_BUDGET = 10  # @limiter.limit("10/minute") on POST /auth/refresh

WINDOW = auth_service.LOCKOUT_WINDOW_SECONDS  # 900
THRESHOLD = auth_service.LOCKOUT_THRESHOLD  # 5

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}

_EXPIRED_JWT_USER_REPLY = (
    "json", 401,
    {"code": "bad_jwt", "message": "invalid JWT: unable to parse or verify signature, token has invalid claims: token is expired"},
    API_VERSION_HEADER,
)
_REJECTED_REFRESH_REPLY = (
    "json", 400,
    {"code": "refresh_token_not_found", "message": "Invalid Refresh Token: Refresh Token Not Found"},
    API_VERSION_HEADER,
)


# ===========================================================================
# autouse: zero network, no leaked SDK timers, clean flags, clean limiter
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


@pytest.fixture(autouse=True)
def _cancel_leaked_sdk_timers():
    before = set(_live_supabase_timers())
    yield
    for t in _live_supabase_timers():
        if t not in before:
            t.cancel()


@pytest.fixture(autouse=True)
def _clean_flags_and_limiter(monkeypatch):
    monkeypatch.delenv(LOGOUT_FLAG, raising=False)
    monkeypatch.delenv(REUSE_FLAG, raising=False)
    monkeypatch.delenv(PROXY_FLAG, raising=False)
    prior = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = prior


@pytest.fixture
def gotrue(monkeypatch):
    fake = _FakeGoTrue()
    fake.behaviour["user"] = _EXPIRED_JWT_USER_REPLY
    monkeypatch.setattr(auth_service, "SUPABASE_URL", fake.url)
    monkeypatch.setattr(auth_service, "SUPABASE_ANON_KEY", "retro-rauth-fixer-anon-key")

    def _no_admin():
        raise RuntimeError("admin client disabled in the R-AUTH fixer tests")

    monkeypatch.setattr(auth_service, "get_admin_client", _no_admin)
    yield fake
    fake.close()


class _BlacklistRedis:
    def __init__(self) -> None:
        self.setex_calls: List[tuple] = []

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))

    def get(self, key):
        return None


@pytest.fixture
def blacklist(monkeypatch):
    fake = _BlacklistRedis()
    monkeypatch.setattr(cache_service, "redis_client", fake)
    return fake


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token_posts(fake: _FakeGoTrue) -> List[dict]:
    return [r for r in fake.requests if r["method"] == "POST" and r["path"] == "/auth/v1/token"]


def _logout_warnings(caplog) -> List[str]:
    return [r.getMessage() for r in caplog.records
            if r.name == "app.services.auth_service" and r.levelno == logging.WARNING
            and "logout upstream leg failed" in r.getMessage()]


def _unauth_signature(resp) -> tuple:
    body = resp.json()
    return resp.status_code, body.get("code"), body.get("error"), body.get("success")


def _emitted(caplog) -> str:
    return "\n".join(r.getMessage() for r in caplog.records)


# ===========================================================================
# Defect 1 -- the expired-bearer branch spends the /auth/refresh budget
# ===========================================================================
def test_forged_expired_bearers_are_capped_at_the_refresh_budget(client, gotrue, blacklist, monkeypatch, caplog):
    """The adversary's reproduction, bounded: flag ON, a MADE-UP expired JWT
    (bogus signature) + a made-up refresh token, sent 12 times from one client
    key. The first 10 are served as before (200, one POST /token each, one
    blacklist write each, one TYPE-only WARNING each); the 11th and 12th get
    the route's ORIGINAL 401 -- the flag-OFF answer -- with NO upstream call,
    NO Redis write and NO WARNING. A different client key has its own budget,
    and the branch's bucket is not /auth/refresh's own bucket.

    MEASURED BEFORE THIS FIX: 12 x 200, 12 POST /token, 12 setex, 12 WARNINGs.
    """
    monkeypatch.setenv(PROXY_FLAG, "true")  # per-client keys, so the key is visible
    gotrue.behaviour["refresh"] = _REJECTED_REFRESH_REPLY
    attacker = {"X-Forwarded-For": "203.0.113.7"}

    def _forged(i: int, headers: dict):
        h = dict(headers)
        h["Authorization"] = "Bearer " + make_jwt(-120, tag="forged-" + str(i))
        return client.post(LOGOUT_URL, json={"refresh_token": "RT-FORGED-" + str(i)}, headers=h)

    off = _forged(0, attacker)  # flag OFF: today's 401, spends nothing
    assert off.status_code == 401 and _token_posts(gotrue) == []

    monkeypatch.setenv(LOGOUT_FLAG, "true")
    with caplog.at_level(logging.DEBUG):
        statuses = [_forged(i, attacker).status_code for i in range(1, REFRESH_BUDGET + 1)]
        assert statuses == [200] * REFRESH_BUDGET, statuses
        assert len(_token_posts(gotrue)) == REFRESH_BUDGET
        assert len(blacklist.setex_calls) == REFRESH_BUDGET
        assert len(_logout_warnings(caplog)) == REFRESH_BUDGET

        over = [_forged(100 + i, attacker) for i in range(2)]
        for resp in over:
            assert _unauth_signature(resp) == _unauth_signature(off), (resp.status_code, resp.text)
        assert len(_token_posts(gotrue)) == REFRESH_BUDGET, "an over-budget request reached gotrue"
        assert len(blacklist.setex_calls) == REFRESH_BUDGET, "an over-budget request wrote Redis"
        assert len(_logout_warnings(caplog)) == REFRESH_BUDGET, "an over-budget request logged a WARNING"

        other = _forged(200, {"X-Forwarded-For": "198.51.100.4"})
        assert other.status_code == 200 and other.json() == OK_BODY, other.text
        assert len(_token_posts(gotrue)) == REFRESH_BUDGET + 1

    # Its own bucket: the spent logout budget does not 429 /auth/refresh.
    refresh = client.post(REFRESH_URL, json={"refresh_token": "RT-FORGED-REFRESH"}, headers=attacker)
    assert refresh.status_code == 401, refresh.text


def test_legit_expired_logout_within_budget_is_unchanged(client, gotrue, blacklist, monkeypatch):
    """PIN: under the budget the expired-bearer path is exactly the ruling-2
    path (rotation then local sign-out, 200)."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-LEGIT-EXPIRED"},
                       headers={"Authorization": "Bearer " + make_jwt(-120, tag="legit")})
    assert resp.status_code == 200 and resp.json() == OK_BODY, resp.text
    posts = [(r["path"], r["query"]) for r in gotrue.requests if r["method"] == "POST"]
    assert posts == [("/auth/v1/token", {"grant_type": "refresh_token"}), ("/auth/v1/logout", {"scope": "local"})], posts


def test_budget_store_failure_fails_closed_to_todays_401(client, gotrue, blacklist, monkeypatch):
    """A limiter-storage error never opens the branch: today's 401, nothing
    upstream, nothing in Redis."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")

    class _Broken:
        def hit(self, *_a, **_k):
            raise RuntimeError("limiter storage down")

    monkeypatch.setattr(type(limiter), "limiter", property(lambda _self: _Broken()))
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-STORE-DOWN"},
                       headers={"Authorization": "Bearer " + make_jwt(-120, tag="store-down")})
    assert resp.status_code == 401 and resp.json().get("code") == "AUTH_REQUIRED", resp.text
    assert _token_posts(gotrue) == [] and blacklist.setex_calls == []


# ===========================================================================
# Proves-nothing 4 -- the `status_code != 401` guard in _LogoutRoute
# ===========================================================================
def test_non_401_from_the_dependency_is_reraised_even_with_flag_on(client, monkeypatch):
    """A non-401 HTTPException from the route's dependencies is re-raised as
    is, even with the flag ON and a qualifying expired bearer + refresh token:
    only a 401 may enter the expired branch. (Equivalent today --
    ``get_current_user`` raises only 401 -- this makes the guard load-bearing.)"""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    reached: List[tuple] = []

    async def _record(*a, **k):
        reached.append((a, k))
        return OK_BODY

    def _forbidden():
        raise HTTPException(status_code=403, detail="forbidden by a dependency")

    monkeypatch.setattr(auth_routes, "logout_user", _record)
    app.dependency_overrides[get_current_user] = _forbidden
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-NON-401"},
                       headers={"Authorization": "Bearer " + make_jwt(-120, tag="non401")})
    assert resp.status_code == 403, resp.text
    assert reached == [], "a non-401 entered the expired-bearer branch"


# ===========================================================================
# Proves-nothing 3 -- the exact `exp` boundary
# ===========================================================================
def _tok(payload) -> str:
    enc = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return "eyJhbGciOiJIUzI1NiJ9." + enc + ".sig"


def test_expiry_boundary_is_exact(monkeypatch):
    """Frozen clock: ``exp == now`` and ``exp == now - 1`` are expired;
    ``exp == now + 1`` is NOT (a token one second from expiry keeps today's
    401 and never takes the expired branch)."""
    now = 1_900_000_000
    monkeypatch.setattr(auth_routes, "time", SimpleNamespace(time=lambda: float(now)))
    assert auth_routes._unverified_jwt_is_expired(_tok({"exp": now - 1})) is True
    assert auth_routes._unverified_jwt_is_expired(_tok({"exp": now})) is True
    assert auth_routes._unverified_jwt_is_expired(_tok({"exp": now + 1})) is False
    assert auth_routes._unverified_jwt_is_expired(_tok({"exp": now + 0.5})) is False


def test_rejected_token_30s_from_expiry_keeps_todays_401(client, gotrue, blacklist, monkeypatch):
    """Route level, near the edge: a rejected (e.g. revoked) bearer whose JWT
    still has 30 s to live does NOT take the expired branch."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    resp = client.post(LOGOUT_URL, json={"refresh_token": "RT-NEAR-EDGE"},
                       headers={"Authorization": "Bearer " + make_jwt(30, tag="near-edge")})
    assert resp.status_code == 401 and resp.json().get("code") == "AUTH_REQUIRED", resp.text
    assert _token_posts(gotrue) == [] and blacklist.setex_calls == []


# ===========================================================================
# Proves-nothing 2 -- TYPE-only logging on the two new lines
# ===========================================================================
def test_expired_branch_backstop_logs_type_only(client, gotrue, monkeypatch, caplog):
    """The route backstop in ``_logout_with_expired_bearer`` (reachable when
    ``logout_user`` raises) logs the exception TYPE, never its text, and never
    the presented tokens -- still 200."""
    monkeypatch.setenv(LOGOUT_FLAG, "true")
    secret = "RETRO-FIXER-BACKSTOP-SECRET"
    expired = make_jwt(-120, tag="backstop")
    refresh = "RT-FIXER-BACKSTOP"

    async def _boom(*_a, **_k):
        raise UserDoesntExist(secret + " " + expired + " " + refresh)

    monkeypatch.setattr(auth_routes, "logout_user", _boom)
    with caplog.at_level(logging.DEBUG):
        resp = client.post(LOGOUT_URL, json={"refresh_token": refresh},
                           headers={"Authorization": "Bearer " + expired})
    assert resp.status_code == 200 and resp.json() == OK_BODY, resp.text
    route_lines = [r.getMessage() for r in caplog.records if r.name == "app.api.auth_routes"]
    assert any("UserDoesntExist" in m for m in route_lines), route_lines
    emitted = _emitted(caplog)
    for value in (secret, expired, refresh):
        assert value not in emitted, "the backstop logged exception text / a token: " + emitted[:400]


class _RaisingAuth:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def refresh_session(self, refresh_token=None):
        raise self._exc


_TYPED_TRANSIENTS = [
    ("AuthRetryableError_503", lambda s: AuthRetryableError("Service Unavailable " + s, 503)),
    ("AuthApiError_429", lambda s: AuthApiError("Request rate limit reached " + s, 429, "over_request_rate_limit")),
    ("httpx_ReadTimeout", lambda s: httpx.ReadTimeout("timed out " + s)),
]


@pytest.mark.parametrize("make_exc", [m for _i, m in _TYPED_TRANSIENTS], ids=[i for i, _m in _TYPED_TRANSIENTS])
def test_refresh_type_transient_is_the_categorisers_transient_dict_and_logs_type_only(client, monkeypatch, caplog, make_exc):
    """(a) The 503 body carries the categoriser's transient text, and the
    service dict is byte-identical to the substring branch's transient dict;
    (b) the new refresh WARNING logs the exception TYPE, never its text."""
    secret = "RETRO-FIXER-REFRESH-SECRET"
    exc = make_exc(secret)
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: SimpleNamespace(auth=_RaisingAuth(exc)))

    expected = auth_service._categorize_auth_error(Exception("connection failed"), "refresh")
    assert asyncio.run(auth_service.refresh_session("RT-FIXER-SERVICE")) == expected
    assert expected["error"] == TRANSIENT_ERROR_TEXT

    with caplog.at_level(logging.DEBUG):
        resp = client.post(REFRESH_URL, json={"refresh_token": "RT-FIXER-ROUTE"})
    body = resp.json()
    assert resp.status_code == 503, resp.text
    assert body.get("code") == "REFRESH_UPSTREAM_UNAVAILABLE", resp.text
    assert body.get("error") == TRANSIENT_ERROR_TEXT, resp.text
    lines = [r.getMessage() for r in caplog.records if "refresh upstream unavailable" in r.getMessage()]
    assert lines and all(type(exc).__name__ in m for m in lines), lines
    assert secret not in _emitted(caplog), _emitted(caplog)[:400]


# ===========================================================================
# Defect 2 -- the two TTL-less counter paths the SET NX cannot arm
# ===========================================================================
@pytest.fixture
def upstash(monkeypatch):
    redis = FakeUpstash()
    monkeypatch.setattr(auth_service, "redis_client", redis)
    monkeypatch.setattr(cache_service, "redis_client", redis)
    return redis


def _key(email: str) -> str:
    return auth_service._login_attempt_key(email)


def _fail(email: str) -> dict:
    return asyncio.run(auth_service.track_failed_login(email))


def test_legacy_ttl_less_counter_is_armed_on_its_next_failure(upstash):
    """Probe B: a legacy key stuck at count 3 with NO TTL. One failure 30 days
    later -> attempts 4 AND the key now carries the window; one more failure
    30 days after that starts a FRESH count (1, unlocked) instead of locking.

    MEASURED BEFORE THIS FIX: attempts 4 with ttl -1, then locked True."""
    email = "fixer-legacy@example.com"
    upstash.seed(_key(email), "3", ttl=None)
    upstash.advance(30 * 86400)
    first = _fail(email)
    assert first == {"locked": False, "attempts": 4}, first
    assert 0 < upstash.raw_ttl(_key(email)) <= WINDOW, upstash.raw_ttl(_key(email))
    upstash.advance(30 * 86400)
    second = _fail(email)
    assert second == {"locked": False, "attempts": 1}, second
    assert 0 < upstash.raw_ttl(_key(email)) <= WINDOW


def test_counter_expiring_between_arm_and_incr_gets_its_window(upstash, monkeypatch):
    """Probe C: the key is live (1 s left) at the SET NX, which is therefore a
    no-op; the clock passes 2 s before the INCR, which recreates the key.
    It must still carry the window.

    MEASURED BEFORE THIS FIX: value 1, ttl -1."""
    email = "fixer-race@example.com"
    upstash.seed(_key(email), "4", ttl=1)
    real_incr = upstash.incr

    def _late_incr(key):
        upstash.advance(2)
        return real_incr(key)

    monkeypatch.setattr(upstash, "incr", _late_incr)
    result = _fail(email)
    assert result == {"locked": False, "attempts": 1}, result
    assert 0 < upstash.raw_ttl(_key(email)) <= WINDOW, upstash.raw_ttl(_key(email))


def test_backstop_expire_never_extends_a_live_window(upstash):
    """``EXPIRE ... NX``: a counter with 300 s left keeps <= 300 s."""
    email = "fixer-live@example.com"
    upstash.seed(_key(email), "2", ttl=300)
    assert _fail(email) == {"locked": False, "attempts": 3}
    assert 0 < upstash.raw_ttl(_key(email)) <= 300, upstash.raw_ttl(_key(email))


def test_backstop_expire_failure_keeps_the_applied_count(upstash):
    """A failed backstop EXPIRE never turns an applied count into the
    fail-open ``attempts 0``: the return contract counts on, and the lock still
    lands at the threshold."""
    email = "fixer-expire-down@example.com"
    for i in range(1, THRESHOLD + 1):
        upstash.add_fault("expire", occurrence=i, mode="before")
    results = [_fail(email) for _ in range(THRESHOLD)]
    assert [r["attempts"] for r in results] == [1, 2, 3, 4, 5], results
    assert results[-1]["locked"] is True
    assert 0 < upstash.raw_ttl(_key(email)) <= WINDOW

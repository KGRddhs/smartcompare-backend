"""S81-24 AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE: the frozen RED file.

Spec: .qa-s80/S81-24_UNIT_SPEC.md (sha256 e545cd4a...) as amended by the review
(B1-B3, C1-C9, RC1-RC5) and RULINGS_S81_24 (R-S24-19..R-S24-32):
- R-S24-19 COUNT-ONLY login backoff: the gate refuses only while a wait armed by a
  PREVIOUS counted failure is live; the n-th consecutive failure arms
  min(2^(n-1), cap) seconds; a success clears. LOGIN_GATE / LOGIN_FAIL re-derived.
- R-S24-20 the interval keys expire at the interval, the login backoff key at the
  TTL knob, the account window key at its window, the Riyadh-day counter 24 h.
- R-S24-21 a per-process per-endpoint 60 s memo on the skipped WARNING.
- R-S24-22 every route row resets the slowapi storage before each request and
  every 429 assertion also asserts the V2 marker line.
- R-S24-23 the [HOP_PROBE] line gains uvicorn_forwarded_allow_ips_set=<bool>.
- R-S24-24 the LOGIN_FAIL / LOGIN_CLEAR writes are shielded (durable).
- R-S24-30 C3 / C6 / C8 / Q8 / Q10 / Q11.

Every RED row fails at base on an AssertionError only (the new module and its
names are read through find_spec / hasattr helpers); every PIN row is green at
base and runs with the FULL configuration (the pepper and every knob set to
synthetic values, ENABLE_HOP_PROBE_LOG OFF) and the call recorders.

Hermetic: no network, no .env, no real credential; every email is synthetic and
built at run time; the Lua scripts run as Python models keyed on their exact
text (R-S24-29; no Lua runtime on the pinned venv).
"""
import ast
import asyncio
import calendar
import concurrent.futures
import hashlib
import hmac
import importlib
import importlib.util
import logging
import math
import re
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = "app.services.auth_throttle"
RID_MOD = "app.middleware.request_id"
FLAG = "ENABLE_AUTH_THROTTLE_V2"
HOP_FLAG = "ENABLE_HOP_PROBE_LOG"
PEPPER_ENV_NAME = "AUTH_THROTTLE_" + "PEPPER"
UVICORN_ENV_NAME = "FORWARDED_ALLOW_IPS"
PEPPER_VALUE = "s24-pepper-" + "q" * 8
OTHER_PEPPER_VALUE = "s24-other-" + "z" * 8

E1 = "user-a" + "@" + "example.com"
E2 = "user-b" + "@" + "example.com"
UID1 = str(uuid.UUID(int=0x5240001))
UID2 = str(uuid.UUID(int=0x5240002))
BAD_PW = "Wrong" + "pass" + "123"
GOOD_PW = "Good" + "pass" + "1234"
NEW_PW = "Fresh" + "pass" + "5678"

T0_MS = calendar.timegm((2026, 11, 7, 10, 0, 0)) * 1000  # 13:00 Asia/Riyadh

ENDPOINTS = ("login", "register", "password_reset", "resend_verification",
             "change_password", "update_email")

KNOB_DEFAULTS = {
    "AUTH_THROTTLE_LOGIN_CAP_SECONDS": (60, 8, 3600),
    "AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS": (60, 10, 3600),
    "AUTH_THROTTLE_RESET_INTERVAL_SECONDS": (60, 10, 3600),
    "AUTH_THROTTLE_RESET_PER_DAY": (5, 1, 100),
    "AUTH_THROTTLE_ACCOUNT_PER_WINDOW": (5, 1, 100),
    "AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS": (600, 60, 86400),
    "AUTH_THROTTLE_TTL_SECONDS": (21600, 60, 86400),
}
TIMEOUT_KNOB = "AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS"

FULL_KNOBS = (
    ("AUTH_THROTTLE_LOGIN_CAP_SECONDS", "30"),
    ("AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS", "20"),
    ("AUTH_THROTTLE_RESET_INTERVAL_SECONDS", "15"),
    ("AUTH_THROTTLE_RESET_PER_DAY", "3"),
    ("AUTH_THROTTLE_ACCOUNT_PER_WINDOW", "2"),
    ("AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS", "120"),
    ("AUTH_THROTTLE_TTL_SECONDS", "7200"),
    (TIMEOUT_KNOB, "0.25"),
)

THROTTLED_MESSAGE = "Rate limit exceeded. Please try again later."

# ---------------------------------------------------------------------------
# the six frozen Lua texts (LF join, no trailing LF) and their sha256 (R04)
# ---------------------------------------------------------------------------
LUA_LINES = {
    "LOGIN_GATE_SCRIPT": (
        "local u = tonumber(redis.call('HGET', KEYS[1], 'u') or '0')",
        "local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')",
        "local now = tonumber(ARGV[1])",
        "if now < u then return {0, math.ceil((u - now) / 1000), c} end",
        "return {1, 0, c}",
    ),
    "LOGIN_FAIL_SCRIPT": (
        "local c = redis.call('HINCRBY', KEYS[1], 'c', 1)",
        "local w = 1000",
        "for i = 2, math.min(c, 23) do w = w * 2 end",
        "if w > tonumber(ARGV[2]) then w = tonumber(ARGV[2]) end",
        "redis.call('HSET', KEYS[1], 'u', tonumber(ARGV[1]) + w)",
        "redis.call('EXPIRE', KEYS[1], ARGV[3])",
        "return c",
    ),
    "LOGIN_CLEAR_SCRIPT": (
        "return redis.call('DEL', KEYS[1])",
    ),
    "INTERVAL_SCRIPT": (
        "local now = tonumber(ARGV[1])",
        "local u = tonumber(redis.call('GET', KEYS[1]) or '0')",
        "if now < u then return {0, math.ceil((u - now) / 1000), 1} end",
        "redis.call('SET', KEYS[1], now + tonumber(ARGV[2]), 'EX', ARGV[3])",
        "return {1, 0, 1}",
    ),
    "RESET_SCRIPT": (
        "local now = tonumber(ARGV[1])",
        "local u = tonumber(redis.call('GET', KEYS[1]) or '0')",
        "local d = tonumber(redis.call('GET', KEYS[2]) or '0')",
        "if now < u then return {0, math.ceil((u - now) / 1000), d} end",
        "if d >= tonumber(ARGV[3]) then return {0, tonumber(ARGV[6]), d} end",
        "redis.call('SET', KEYS[1], now + tonumber(ARGV[2]), 'EX', ARGV[4])",
        "d = redis.call('INCR', KEYS[2])",
        "if d == 1 then redis.call('EXPIRE', KEYS[2], ARGV[5]) end",
        "return {1, 0, d}",
    ),
    "ACCOUNT_SCRIPT": (
        "local now = tonumber(ARGV[1])",
        "local w = tonumber(ARGV[3])",
        "local s = tonumber(redis.call('HGET', KEYS[1], 's') or '0')",
        "local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')",
        "if now - s >= w then",
        "  s = now",
        "  c = 0",
        "end",
        "if c >= tonumber(ARGV[2]) then return {0, math.ceil((s + w - now) / 1000), c} end",
        "c = c + 1",
        "redis.call('HSET', KEYS[1], 's', s, 'c', c)",
        "redis.call('EXPIRE', KEYS[1], ARGV[4])",
        "return {1, 0, c}",
    ),
}
FROZEN_TEXT = {name: "\n".join(lines) for name, lines in LUA_LINES.items()}
FROZEN_SCRIPT_SHA256 = {
    "LOGIN_GATE_SCRIPT": "8adceb7c822c392167dd7ae3d6b8f52e929d9d35cc634571d5be2dc70cd81315",
    "LOGIN_FAIL_SCRIPT": "941fa5bc181ff187592dcb384dfb52e358365ed0b6dc9cb39ea1abb0f4f9d578",
    "LOGIN_CLEAR_SCRIPT": "d5c2157a7f09aca2b3faee49953d80b5905a98c0afadb442553830b3952e58a1",
    "INTERVAL_SCRIPT": "8d04ebbfe5236d3a9a9090e71dfd8e5fb76530ab0f32bcb22aead3b0843d4251",
    "RESET_SCRIPT": "963aab4312555db335dc98ec5c8958559f480356841f06eb88cff122497460ff",
    "ACCOUNT_SCRIPT": "8e3153ec40ac995ccf49506763518a4fc5a1af7c0047be40ccdd8114ea85085d",
}

THROTTLED_RE = re.compile(r"\[AUTH_THROTTLE\] throttled endpoint=([a-z_]+) count=(\d+) retry_after=(\d+)")
SKIPPED_RE = re.compile(r"\[AUTH_THROTTLE\] skipped endpoint=([a-z_]+) type=([A-Za-z_][A-Za-z0-9_]*)")
PEPPER_LINE = "[AUTH_THROTTLE] pepper unset"
HOP_RE = re.compile(
    r"\[HOP_PROBE\] xff_entries=(\d+) xff_leftmost_is_peer=(true|false) "
    r"xff_rightmost_is_peer=(true|false) xff_leftmost_public=(true|false) "
    r"x_real_ip_present=(true|false) x_real_ip_is_peer=(true|false) "
    r"x_real_ip_public=(true|false) forwarded_present=(true|false) "
    r"cf_present=(true|false) peer_public=(true|false) "
    r"uvicorn_forwarded_allow_ips_set=(true|false)"
)

BAD_RESULT = {"success": False, "error": "Invalid email or password"}

# base literals (measured at daf86d32: spec 1.2-1.4, probe_bodies.json)
HDR_200 = sorted([
    "content-length", "content-security-policy", "content-type", "permissions-policy",
    "referrer-policy", "strict-transport-security", "x-content-type-options",
    "x-frame-options", "x-request-id", "x-xss-protection",
])
HDR_429 = sorted(HDR_200 + ["retry-after"])
RESET_BODY = {"success": True, "message": "If an account with that email exists, a reset link has been sent."}
RESEND_BODY = {"success": True, "message": "Verification email sent if account exists"}
LOGIN_401 = {"success": False, "error": "Invalid email or password", "code": "AUTH_REQUIRED"}
LOCKED_ERR = "Account temporarily locked due to too many failed attempts"
SLOWAPI_429 = {"success": False, "error": THROTTLED_MESSAGE, "code": "RATE_LIMITED"}


def _lift_lockout(fake, email=E1):
    """The W1-9b 5-in-15-min lockout (untouched) would answer the 6th failure with
    ACCOUNT_LOCKED; rows that drive a longer backoff sequence lift its counter so
    the V2 backoff is measured alone (the lockout is pinned by R15 / P70)."""
    fake.store.pop(_lock_key(email), None)
    fake.exp.pop(_lock_key(email), None)


def _lock_key(email):
    return "failed_login:" + hashlib.sha256(email.lower().encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# module access helpers (missing symbols are AssertionErrors, never import errors)
# ---------------------------------------------------------------------------
def _mod():
    spec = importlib.util.find_spec(MOD)
    assert spec is not None, "app/services/auth_throttle.py is absent (S81-24 change 1)"
    return importlib.import_module(MOD)


def _need(attr, module=None):
    m = module if module is not None else _mod()
    assert hasattr(m, attr), "%s.%s is missing" % (m.__name__, attr)
    return getattr(m, attr)


def _rid():
    return importlib.import_module(RID_MOD)


def _mod_if_present():
    if importlib.util.find_spec(MOD) is None:
        return None
    return importlib.import_module(MOD)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
class Clock:
    def __init__(self, ms=T0_MS):
        self.ms = int(ms)

    def advance(self, seconds):
        self.ms += int(round(seconds * 1000))


NO_OVERRIDE = object()


def _ceil_div(a, b):
    return -((-a) // b)


class FakeRedis:
    """upstash-redis shaped recorder (eval(script, keys=, args=)) over a dict store
    with TTLs on the fake clock; the Lua scripts run as Python models keyed on
    their exact frozen text, one script at a time (as Redis serialises them)."""

    def __init__(self, clock):
        self.clock = clock
        self.store = {}
        self.exp = {}
        self.calls = []
        self.fail_with = None
        self.delay = 0.0
        self.reply_override = NO_OVERRIDE
        self.release = None
        self._lock = threading.Lock()
        self._models = {
            FROZEN_TEXT["LOGIN_GATE_SCRIPT"]: ("LOGIN_GATE_SCRIPT", self._m_gate),
            FROZEN_TEXT["LOGIN_FAIL_SCRIPT"]: ("LOGIN_FAIL_SCRIPT", self._m_fail),
            FROZEN_TEXT["LOGIN_CLEAR_SCRIPT"]: ("LOGIN_CLEAR_SCRIPT", self._m_clear),
            FROZEN_TEXT["INTERVAL_SCRIPT"]: ("INTERVAL_SCRIPT", self._m_interval),
            FROZEN_TEXT["RESET_SCRIPT"]: ("RESET_SCRIPT", self._m_reset),
            FROZEN_TEXT["ACCOUNT_SCRIPT"]: ("ACCOUNT_SCRIPT", self._m_account),
        }

    # -- plain commands (the W1-9b lockout) ---------------------------------
    def _rec(self, name, *args, **kwargs):
        self.calls.append((name, args, tuple(sorted(kwargs.items()))))

    def _purge(self, key):
        e = self.exp.get(key)
        if e is not None and e <= self.clock.ms:
            self.store.pop(key, None)
            self.exp.pop(key, None)

    def _expire_at(self, key, seconds):
        self.exp[key] = self.clock.ms + int(seconds) * 1000

    def get(self, key):
        self._rec("get", key)
        self._purge(key)
        v = self.store.get(key)
        return None if v is None else str(v)

    def set(self, key, value, **kwargs):
        self._rec("set", key, value, **kwargs)
        self._purge(key)
        if kwargs.get("nx") and key in self.store:
            return None
        self.store[key] = value
        self.exp.pop(key, None)
        if kwargs.get("ex") is not None:
            self._expire_at(key, kwargs["ex"])
        return True

    def incr(self, key):
        self._rec("incr", key)
        self._purge(key)
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def expire(self, key, seconds, **kwargs):
        self._rec("expire", key, seconds, **kwargs)
        self._purge(key)
        if key not in self.store:
            return 0
        if kwargs.get("nx") and key in self.exp:
            return 0
        self._expire_at(key, seconds)
        return 1

    def ttl(self, key):
        self._rec("ttl", key)
        self._purge(key)
        if key not in self.store:
            return -2
        if key not in self.exp:
            return -1
        return _ceil_div(self.exp[key] - self.clock.ms, 1000)

    def delete(self, *keys):
        self._rec("delete", *keys)
        n = 0
        for k in keys:
            self._purge(k)
            if k in self.store:
                n += 1
                self.store.pop(k, None)
                self.exp.pop(k, None)
        return n

    # -- eval ---------------------------------------------------------------
    def eval(self, script, keys=None, args=None):
        return self._eval(script, list(keys or []), list(args or []))

    def _eval(self, script, keys, args):
        assert script in self._models, "EVAL of an unknown script text"
        name, model = self._models[script]
        self.calls.append(("eval", (name, tuple(keys), tuple(str(a) for a in args)), ()))
        if self.release is not None:
            self.release.wait(5.0)
        if self.delay:
            time.sleep(self.delay)
        if self.fail_with is not None:
            raise self.fail_with("s24 fake failure")
        with self._lock:
            out = model(keys, [str(a) for a in args])
        if self.reply_override is not NO_OVERRIDE:
            return self.reply_override
        return out

    def evals(self, name=None):
        out = [c[1] for c in self.calls if c[0] == "eval"]
        if name is not None:
            out = [c for c in out if c[0] == name]
        return out

    def _hash(self, key):
        self._purge(key)
        h = self.store.get(key)
        if not isinstance(h, dict):
            h = {}
            self.store[key] = h
        return h

    def _hget(self, key, field):
        self._purge(key)
        h = self.store.get(key)
        if isinstance(h, dict) and field in h:
            return int(h[field])
        return 0

    def _m_gate(self, keys, args):
        k = keys[0]
        u = self._hget(k, "u")
        c = self._hget(k, "c")
        now = int(args[0])
        if now < u:
            return [0, _ceil_div(u - now, 1000), c]
        return [1, 0, c]

    def _m_fail(self, keys, args):
        k = keys[0]
        h = self._hash(k)
        c = int(h.get("c", 0)) + 1
        h["c"] = c
        w = 1000
        for _ in range(2, min(c, 23) + 1):
            w *= 2
        if w > int(args[1]):
            w = int(args[1])
        h["u"] = int(args[0]) + w
        self._expire_at(k, int(args[2]))
        return c

    def _m_clear(self, keys, args):
        k = keys[0]
        self._purge(k)
        if k in self.store:
            self.store.pop(k, None)
            self.exp.pop(k, None)
            return 1
        return 0

    def _m_interval(self, keys, args):
        k = keys[0]
        now = int(args[0])
        self._purge(k)
        u = int(self.store.get(k, 0) or 0)
        if now < u:
            return [0, _ceil_div(u - now, 1000), 1]
        self.store[k] = now + int(args[1])
        self._expire_at(k, int(args[2]))
        return [1, 0, 1]

    def _m_reset(self, keys, args):
        ki, kd = keys[0], keys[1]
        now = int(args[0])
        self._purge(ki)
        self._purge(kd)
        u = int(self.store.get(ki, 0) or 0)
        d = int(self.store.get(kd, 0) or 0)
        if now < u:
            return [0, _ceil_div(u - now, 1000), d]
        if d >= int(args[2]):
            return [0, int(args[5]), d]
        self.store[ki] = now + int(args[1])
        self._expire_at(ki, int(args[3]))
        d = d + 1
        self.store[kd] = d
        if d == 1:
            self._expire_at(kd, int(args[4]))
        return [1, 0, d]

    def _m_account(self, keys, args):
        k = keys[0]
        now = int(args[0])
        w = int(args[2])
        s = self._hget(k, "s")
        c = self._hget(k, "c")
        if now - s >= w:
            s = now
            c = 0
        if c >= int(args[1]):
            return [0, _ceil_div(s + w - now, 1000), c]
        c += 1
        h = self._hash(k)
        h["s"] = s
        h["c"] = c
        self._expire_at(k, int(args[3]))
        return [1, 0, c]


FakeRedis.__module__ = "upstash_redis.s24fake"


class FakeRedisPy(FakeRedis):
    """redis-py 8.1.0 shape: eval(script, numkeys, *keys_and_args)."""

    def eval(self, script, numkeys, *keys_and_args):
        n = int(numkeys)
        return self._eval(script, list(keys_and_args[:n]), list(keys_and_args[n:]))


FakeRedisPy.__module__ = "redis.s24fake"


class LogCap(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def lines(self, prefix=None):
        out = []
        for r in self.records:
            msg = r.getMessage()
            if prefix is None or msg.startswith(prefix):
                out.append(msg)
        return out

    def app_records(self):
        return [(r.name, r.levelname, r.getMessage()) for r in self.records if r.name.startswith("app")]

    def clear(self):
        self.records = []


# ---------------------------------------------------------------------------
# fixtures (no assertion inside a fixture: a RED row fails in its body)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _s24_env(monkeypatch):
    import app.main  # noqa: F401  (the DOTENV GUARD rule: import first, then setenv)
    for name in (FLAG, HOP_FLAG, PEPPER_ENV_NAME, UVICORN_ENV_NAME, "ENABLE_CONSENT_REQUIRED",
                 "ENABLE_PROXY_AWARE_RATELIMIT", "ENABLE_DEFAULT_RATE_LIMITS"):
        monkeypatch.delenv(name, raising=False)
    for name, _v in FULL_KNOBS:
        monkeypatch.delenv(name, raising=False)
    from app.middleware.rate_limiter import limiter
    limiter.reset()
    m = _mod_if_present()
    if m is not None:
        for seam in ("_reset_pepper_warning", "_reset_skip_memo"):
            fn = getattr(m, seam, None)
            if callable(fn):
                fn()
    yield
    if m is not None:
        for seam in ("_reset_pepper_warning", "_reset_skip_memo"):
            fn = getattr(m, seam, None)
            if callable(fn):
                fn()
    limiter.reset()


@pytest.fixture
def logs():
    lg = logging.getLogger("app")
    cap = LogCap()
    old = lg.level
    lg.addHandler(cap)
    lg.setLevel(logging.INFO)
    yield cap
    lg.removeHandler(cap)
    lg.setLevel(old)


def _full_config(monkeypatch, flag_value=None, pepper=True):
    for name, value in FULL_KNOBS:
        monkeypatch.setenv(name, value)
    if pepper:
        monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
    if flag_value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag_value)


def _install(monkeypatch, fake):
    from app.services import auth_service, cache_service
    monkeypatch.setattr(auth_service, "redis_client", fake)
    monkeypatch.setattr(cache_service, "redis_client", fake)


def _arm(monkeypatch, clock, flag="true", pepper=True, fake_cls=FakeRedis, full=True):
    """flag ON + FULL config + the clock seam + a fake client; returns (at, fake)."""
    at = _mod()
    if full:
        _full_config(monkeypatch, flag, pepper=pepper)
    else:
        if pepper:
            monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
        monkeypatch.setenv(FLAG, flag)
    _need("_now_ms", at)
    monkeypatch.setattr(at, "_now_ms", lambda: clock.ms)
    _need("_reset_pepper_warning", at)()
    _need("_reset_skip_memo", at)()
    fake = fake_cls(clock) if fake_cls is not None else None
    _install(monkeypatch, fake)
    return at, fake


class Svc:
    """Mocks the GoTrue-facing service calls at app.api.auth_routes and wraps the
    W1-9b calls (kept REAL over the recorder) to record the call order."""

    def __init__(self, monkeypatch):
        from app.api import auth_routes as ar
        self.ar = ar
        self.mp = monkeypatch
        self.order = []
        for name in ("check_account_locked", "track_failed_login", "clear_failed_logins"):
            monkeypatch.setattr(ar, name, self._wrap(name, getattr(ar, name)))
        monkeypatch.setattr(ar, "log_audit_event", self._audit)

    def _wrap(self, name, orig):
        async def wrapped(*a, **k):
            self.order.append(name)
            return await orig(*a, **k)
        return wrapped

    def _audit(self, **kw):
        self.order.append("audit:" + str(kw.get("event_type")))

        async def _noop():
            return None
        return _noop()

    def service(self, name, result=None, exc=None):
        async def fn(*a, **k):
            self.order.append(name)
            if exc is not None:
                raise exc
            return dict(result) if isinstance(result, dict) else result
        self.mp.setattr(self.ar, name, fn)


def _tc(client=None):
    from fastapi.testclient import TestClient
    from app.main import app
    if client is None:
        return TestClient(app)
    return TestClient(app, client=client)


def _send(c, method, path, json=None, headers=None):
    from app.middleware.rate_limiter import limiter
    limiter.reset()  # R-S24-22: the slowapi floor never answers a V2 row
    return c.request(method, path, json=json, headers=headers)


def _fields(resp):
    body = resp.json()
    return {k: v for k, v in body.items() if k != "request_id"}


def _names(resp):
    return sorted(k.lower() for k in resp.headers.keys())


def _login(c, email=E1, pw=BAD_PW):
    return _send(c, "POST", "/api/v1/auth/login", json={"email": email, "password": pw})


def _account_user(monkeypatch, uid=UID1, email=E1):
    from app.main import app
    from app.api.auth_routes import get_current_user
    monkeypatch.setitem(app.dependency_overrides, get_current_user,
                        lambda: {"id": uid, "email": email, "access_token": "t"})


def _expect_v2_429(resp, logs, endpoint, retry=None):
    """A V2 refusal: the slowapi-equal envelope AND the V2 marker line (R-S24-22)."""
    assert resp.status_code == 429, (resp.status_code, resp.text)
    body = resp.json()
    assert body.get("code") == "RATE_LIMITED"
    assert body.get("error") == THROTTLED_MESSAGE
    marks = [THROTTLED_RE.fullmatch(m) for m in logs.lines("[AUTH_THROTTLE] throttled")]
    assert marks and all(marks), "no V2 throttled marker for this 429"
    assert marks[-1].group(1) == endpoint
    ra = body.get("retry_after_seconds")
    assert isinstance(ra, int) and not isinstance(ra, bool) and ra >= 1
    assert resp.headers.get("retry-after") == str(ra)
    assert int(marks[-1].group(3)) == ra
    if retry is not None:
        assert ra == retry, (ra, retry)
    return ra


def _gate(at, endpoint, ident):
    """Run gate() on a fresh loop: None = allowed, an int = the refusal's retry."""
    from fastapi import HTTPException

    async def go():
        try:
            await at.gate(endpoint, ident)
            return None
        except HTTPException as exc:
            assert exc.status_code == 429
            assert exc.detail["code"] == "RATE_LIMITED"
            assert exc.detail["error"] == THROTTLED_MESSAGE
            return exc.detail["retry_after"]
    return asyncio.run(go())


def _digest(pepper, ident):
    return hmac.new(pepper.encode("utf-8"), ident.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def _riyadh_secs_to_midnight(now_s):
    local = now_s + 3 * 3600
    return 86400 - (local % 86400)


# ===========================================================================
# R01-R07: the module surface, the flag, the knobs, the scripts, keys, pepper, day
# ===========================================================================
def test_r01_module_surface():
    at = _mod()
    assert _need("FLAG", at) == FLAG
    assert _need("PEPPER_ENV", at) == PEPPER_ENV_NAME
    assert tuple(_need("ENDPOINTS", at)) == ENDPOINTS
    knobs = _need("KNOBS", at)
    for name, spec in KNOB_DEFAULTS.items():
        assert tuple(knobs[name]) == spec, name
    assert knobs[TIMEOUT_KNOB][0] == 0.5
    for name in LUA_LINES:
        assert isinstance(_need(name, at), str)
    for name in ("gate", "record_login_failure", "record_login_success"):
        assert asyncio.iscoroutinefunction(_need(name, at)), name
    for name in ("auth_throttle_v2_enabled", "digest", "email_ident", "account_ident",
                 "throttle_key", "riyadh_day_compact", "seconds_to_riyadh_midnight",
                 "knob", "redis_timeout_seconds", "_eval", "_parse_reply", "_pool",
                 "_now_ms", "_monotonic", "_reset_pepper_warning", "_reset_skip_memo"):
        assert callable(_need(name, at)), name
    assert _need("THROTTLED_MESSAGE", at) == THROTTLED_MESSAGE
    from app.middleware import error_handler
    assert THROTTLED_MESSAGE in Path(error_handler.__file__).read_text(encoding="utf-8")
    assert _need("SKIP_LOG_MEMO_SECONDS", at) == 60
    assert _need("DAY_KEY_TTL_SECONDS", at) == 86400


@pytest.mark.parametrize("raw,want", [
    (None, False), ("", False), ("false", False), ("0", False), ("off", False), ("no", False),
    ("garbage", False), ("true", True), ("1", True), ("yes", True), ("on", True),
    (" TRUE ", True), ("On", True),
])
def test_r02_flag_idiom_per_call(monkeypatch, raw, want):
    at = _mod()
    fn = _need("auth_throttle_v2_enabled", at)
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    assert fn() is want
    monkeypatch.setenv(FLAG, "false" if want else "true")
    assert fn() is (not want)


def test_r03_knobs_defensive_per_call(monkeypatch):
    at = _mod()
    knob = _need("knob", at)
    for name, (default, lo, hi) in KNOB_DEFAULTS.items():
        for raw in (None, "", "abc", "inf", "nan", "-5", "0", "60.5", str(lo - 1), str(hi + 1)):
            if raw is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, raw)
            assert knob(name) == default, (name, raw)
        for raw in (str(lo), str(hi), " %d " % lo):
            monkeypatch.setenv(name, raw)
            assert knob(name) == int(raw), (name, raw)
        monkeypatch.delenv(name, raising=False)
    tfn = _need("redis_timeout_seconds", at)
    for raw, want in ((None, 0.5), ("0.25", 0.25), ("0", 0.5), ("10", 0.5), ("nan", 0.5),
                      ("inf", 0.5), ("abc", 0.5), ("0.05", 0.05), ("5.0", 5.0), ("0.04", 0.5)):
        if raw is None:
            monkeypatch.delenv(TIMEOUT_KNOB, raising=False)
        else:
            monkeypatch.setenv(TIMEOUT_KNOB, raw)
        assert tfn() == want, raw
        assert knob(TIMEOUT_KNOB) == want, raw


def test_r04_scripts_frozen():
    at = _mod()
    for name, lines in LUA_LINES.items():
        text = _need(name, at)
        assert text == "\n".join(lines), name
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == FROZEN_SCRIPT_SHA256[name], name
        assert all(ord(ch) < 128 for ch in text), name
        assert not text.endswith("\n"), name


def test_r05_key_grammar_and_digest(monkeypatch):
    at = _mod()
    monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
    d = _need("digest", at)(E1)
    assert d == _digest(PEPPER_VALUE, E1)
    assert re.fullmatch(r"[0-9a-f]{32}", d)
    assert _need("throttle_key", at)("login", "backoff", d) == "auth_throttle:login:backoff:" + d
    ei = _need("email_ident", at)
    assert ei(" User-A@Example.COM ") == E1
    assert at.digest(ei(" User-A@Example.COM ")) == at.digest(ei(E1))
    monkeypatch.setenv(PEPPER_ENV_NAME, OTHER_PEPPER_VALUE)
    assert at.digest(E1) != d
    monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
    key = at.throttle_key("login", "backoff", at.digest(ei(E1)))
    assert "@" not in key and "user-a" not in key and PEPPER_VALUE not in key
    ai = _need("account_ident", at)
    assert ai(" " + UID1 + " ") == UID1
    assert ai("") is None and ai(None) is None and ai(5) is None
    assert ei("") is None and ei("   ") is None and ei(None) is None and ei(7) is None
    assert at.digest(ai(UID1)) == _digest(PEPPER_VALUE, UID1) != at.digest(E1)


def test_r06_pepper_unset_fail_open_once(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock, pepper=False)
    for _ in range(2):
        assert _gate(at, "login", E1) is None
    monkeypatch.setenv(PEPPER_ENV_NAME, "   ")
    assert _gate(at, "login", E1) is None
    assert fake.calls == []
    warns = [r for r in logs.records if r.levelno == logging.WARNING and "[AUTH_THROTTLE]" in r.getMessage()]
    assert [r.getMessage() for r in warns] == [PEPPER_LINE]


def test_r07_riyadh_day():
    at = _mod()
    rdc = _need("riyadh_day_compact", at)
    stm = _need("seconds_to_riyadh_midnight", at)
    a = calendar.timegm((2026, 11, 6, 20, 59, 59))
    b = calendar.timegm((2026, 11, 6, 21, 0, 0))
    assert rdc(a) == "20261106"
    assert rdc(b) == "20261107"
    from app.services import llm_spend_breaker
    from datetime import datetime, timezone
    for t in (a, b):
        assert llm_spend_breaker.riyadh_day(datetime.fromtimestamp(t, timezone.utc))[0].replace("-", "") == rdc(t)
    assert stm(b) == 86400
    assert stm(a) == 1


# ===========================================================================
# R10-R16: login (count-only backoff, R-S24-19)
# ===========================================================================
def test_r10_login_backoff_sequence(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    c = _tc()
    seen = []
    for n in range(1, 9):
        before = len(fake.evals())
        r = _login(c)
        assert r.status_code == 401 and _fields(r) == LOGIN_401, n
        _lift_lockout(fake)
        assert [e[0] for e in fake.evals()[before:]] == ["LOGIN_GATE_SCRIPT", "LOGIN_FAIL_SCRIPT"], n
        logs.clear()
        r2 = _login(c)
        ra = _expect_v2_429(r2, logs, "login")
        assert m_count(logs) == n
        seen.append(ra)
        clock.advance(ra)
    assert seen == [1, 2, 4, 8, 16, 30, 30, 30]


def m_count(logs):
    return int(THROTTLED_RE.fullmatch(logs.lines("[AUTH_THROTTLE] throttled")[-1]).group(2))


def test_r11_success_clears(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    c = _tc()
    svc.service("login_user", BAD_RESULT)
    waits = []
    for _ in range(3):
        assert _login(c).status_code == 401
        logs.clear()
        waits.append(_expect_v2_429(_login(c), logs, "login"))
        clock.advance(waits[-1])
    assert waits == [1, 2, 4]
    svc.service("login_user", {"success": True, "user": {"id": UID1}, "session": {"access_token": "t"}})
    r = _login(c, pw=GOOD_PW)
    assert r.status_code == 200
    assert fake.evals()[-1][0] == "LOGIN_CLEAR_SCRIPT"
    svc.service("login_user", BAD_RESULT)
    assert _login(c).status_code == 401
    logs.clear()
    assert _expect_v2_429(_login(c), logs, "login") == 1


@pytest.mark.parametrize("result", [
    {"success": False, "error": "Please verify your email before logging in"},
    {"success": False, "error": "Connection failed. Please try again.", "code": "UPSTREAM_UNAVAILABLE"},
    {"success": False, "error": "Something went wrong. Please try again later."},
    {"success": False, "error": "Login failed"},
])
def test_r12_only_credential_failures_count(monkeypatch, result):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("login_user", result)
    c = _tc()
    for _ in range(3):
        r = _login(c)
        assert r.status_code == 401
    assert [e[0] for e in fake.evals()] == ["LOGIN_GATE_SCRIPT"] * 3
    key = at.throttle_key("login", "backoff", _digest(PEPPER_VALUE, E1))
    assert key not in fake.store


def test_r13_default_cap(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    monkeypatch.delenv("AUTH_THROTTLE_LOGIN_CAP_SECONDS", raising=False)
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    c = _tc()
    waits = []
    for _ in range(10):
        assert _login(c).status_code == 401
        _lift_lockout(fake)
        logs.clear()
        waits.append(_expect_v2_429(_login(c), logs, "login"))
        clock.advance(waits[-1])
    assert max(waits) == 60 and waits[-1] == 60
    assert waits[:6] == [1, 2, 4, 8, 16, 32]


def test_r14_login_placement_order(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    c = _tc()
    assert _login(c).status_code == 401
    kinds = [x[0] for x in fake.calls]
    assert "eval" in kinds and "get" in kinds
    assert kinds.index("eval") < kinds.index("get")
    assert svc.order[:2] == ["check_account_locked", "login_user"]
    svc.order.clear()
    calls_before = list(fake.calls)
    logs.clear()
    _expect_v2_429(_login(c), logs, "login")
    assert svc.order == []
    assert [x[0] for x in fake.calls[len(calls_before):]] == ["eval"]


def test_r15_w19b_untouched_on(monkeypatch):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    c = _tc()
    lk = _lock_key(E1)
    assert _login(c).status_code == 401
    seq = [(x[0],) + ((x[1][0],) if x[0] == "eval" else tuple(x[1])) + tuple(x[2]) for x in fake.calls]
    assert seq == [
        ("eval", "LOGIN_GATE_SCRIPT"),
        ("get", lk),
        ("set", lk, 0, ("ex", 900), ("nx", True)),
        ("incr", lk),
        ("expire", lk, 900, ("nx", True)),
        ("eval", "LOGIN_FAIL_SCRIPT"),
    ]
    clock.advance(5)
    fake.calls.clear()
    svc.service("login_user", {"success": True, "user": {"id": UID1}, "session": {"access_token": "t"}})
    assert _login(c, pw=GOOD_PW).status_code == 200
    seq = [(x[0],) + ((x[1][0],) if x[0] == "eval" else tuple(x[1])) + tuple(x[2]) for x in fake.calls]
    assert seq == [("eval", "LOGIN_GATE_SCRIPT"), ("get", lk), ("delete", lk), ("eval", "LOGIN_CLEAR_SCRIPT")]


def test_r16_concurrent_first_attempts_all_pass(monkeypatch):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    from fastapi import HTTPException

    async def burst():
        res = await asyncio.gather(*[at.gate("login", E1) for _ in range(5)], return_exceptions=True)
        return res

    assert asyncio.run(burst()) == [None] * 5
    asyncio.run(at.record_login_failure(E1, dict(BAD_RESULT)))
    res = asyncio.run(burst())
    assert all(isinstance(x, HTTPException) for x in res), res
    assert [x.detail["retry_after"] for x in res] == [1] * 5
    assert [e[0] for e in fake.evals()] == ["LOGIN_GATE_SCRIPT"] * 5 + ["LOGIN_FAIL_SCRIPT"] + ["LOGIN_GATE_SCRIPT"] * 5


# ===========================================================================
# R20-R22: register
# ===========================================================================
def _reg(c, email, extra=None):
    body = {"email": email, "password": GOOD_PW}
    body.update(extra or {})
    return _send(c, "POST", "/api/v1/auth/register", json=body)


def test_r20_register_interval(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("register_user", {"success": True, "user": {"id": UID1}})
    c = _tc()
    assert _reg(c, E1).status_code == 200
    assert [e[0] for e in fake.evals()] == ["INTERVAL_SCRIPT"]
    logs.clear()
    _expect_v2_429(_reg(c, E1), logs, "register", retry=20)
    assert svc.order.count("register_user") == 1
    assert _reg(c, E2).status_code == 200
    clock.advance(20)
    assert _reg(c, E1).status_code == 200
    assert svc.order.count("register_user") == 3


def test_r21_register_existence_blind(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    c = _tc()
    svc.service("register_user", {"success": False, "error": "An account with this email already exists"})
    r1 = _reg(c, E1)
    assert r1.status_code == 400
    assert _fields(r1) == {"success": False, "error": "An account with this email already exists", "code": "BAD_REQUEST"}
    svc.service("register_user", {"success": True, "user": {"id": UID2}})
    r2 = _reg(c, E2)
    assert r2.status_code == 200
    logs.clear()
    a = _reg(c, E1)
    ra = _expect_v2_429(a, logs, "register")
    logs.clear()
    b = _reg(c, E2)
    rb = _expect_v2_429(b, logs, "register")
    assert ra == rb == 20
    assert _fields(a) == _fields(b)
    assert _names(a) == _names(b) == HDR_429


def test_r22_register_gate_after_consent(monkeypatch):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    monkeypatch.setenv("ENABLE_CONSENT_REQUIRED", "true")
    svc = Svc(monkeypatch)
    svc.service("register_user", {"success": True, "user": {"id": UID1}})
    c = _tc()
    r = _reg(c, E1)
    assert r.status_code == 400 and r.json().get("code") == "TERMS_ACCEPTANCE_REQUIRED"
    assert fake.evals() == []
    r = _reg(c, E1, {"terms_accepted": True, "terms_version": "2026-10-14", "age_attested": True})
    assert r.status_code == 200
    assert [e[0] for e in fake.evals()] == ["INTERVAL_SCRIPT"]


# ===========================================================================
# R30-R34: password reset / resend verification
# ===========================================================================
def _reset(c, email=E1):
    return _send(c, "POST", "/api/v1/auth/password-reset", json={"email": email})


def _resend(c, email=E1):
    return _send(c, "POST", "/api/v1/auth/resend-verification", json={"email": email})


def _day_cycle(monkeypatch, logs, clock, fake, at, call, endpoint):
    c = _tc()
    r = call(c)
    assert r.status_code == 200
    logs.clear()
    _expect_v2_429(call(c), logs, endpoint, retry=15)
    clock.advance(15)
    assert call(c).status_code == 200
    clock.advance(15)
    assert call(c).status_code == 200
    clock.advance(15)
    logs.clear()
    want = _riyadh_secs_to_midnight(clock.ms // 1000)
    assert want == 39600 - 45
    assert at.seconds_to_riyadh_midnight(clock.ms // 1000) == want
    _expect_v2_429(call(c), logs, endpoint, retry=want)
    clock.ms = calendar.timegm((2026, 11, 7, 21, 0, 5)) * 1000
    assert call(c).status_code == 200
    days = sorted({k for k in fake.store if (":" + endpoint + ":day") in k})
    assert [k.split(":")[2] for k in days] == ["day20261107", "day20261108"]


def test_r30_reset_interval_and_day(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("request_password_reset", {"success": True})
    _day_cycle(monkeypatch, logs, clock, fake, at, _reset, "password_reset")
    assert {e[0] for e in fake.evals()} == {"RESET_SCRIPT"}


def test_r31_resend_own_keys(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("request_password_reset", {"success": True})
    svc.service("resend_verification_email", True)
    c = _tc()
    assert _reset(c).status_code == 200
    r = _resend(c)
    assert r.status_code == 200 and r.json() == RESEND_BODY
    keys = [e[1] for e in fake.evals("RESET_SCRIPT")]
    assert all(k.startswith("auth_throttle:password_reset:") for k in keys[0])
    assert all(k.startswith("auth_throttle:resend_verification:") for k in keys[1])
    fake2 = FakeRedis(clock)
    _install(monkeypatch, fake2)
    _day_cycle(monkeypatch, logs, clock, fake2, at, _resend, "resend_verification")


def test_r32_reset_existence_blind(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    c = _tc()
    svc.service("request_password_reset", {"success": True})
    a1 = _reset(c, E1)
    svc.service("request_password_reset", {"success": False, "error": "x"})
    b1 = _reset(c, E2)
    assert a1.json() == b1.json() == RESET_BODY
    replies = [e for e in fake.evals("RESET_SCRIPT")]
    assert len(replies) == 2
    logs.clear()
    a2 = _reset(c, E1)
    ra = _expect_v2_429(a2, logs, "password_reset")
    svc.service("request_password_reset", {"success": True})
    logs.clear()
    b2 = _reset(c, E2)
    rb = _expect_v2_429(b2, logs, "password_reset")
    assert ra == rb and _fields(a2) == _fields(b2) and _names(a2) == _names(b2)


def test_r33_reset_never_blocked_by_login(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    svc.service("request_password_reset", {"success": True})
    svc.service("complete_password_recovery", {"success": True})
    c = _tc()
    for _ in range(6):
        assert _login(c).status_code == 401
        _lift_lockout(fake)
        clock.advance(40)
    assert _login(c).status_code == 401
    logs.clear()
    assert _expect_v2_429(_login(c), logs, "login") == 30
    n = len(fake.evals())
    r = _reset(c)
    assert r.status_code == 200 and r.json() == RESET_BODY
    new = fake.evals()[n:]
    assert [e[0] for e in new] == ["RESET_SCRIPT"]
    assert all(k.startswith("auth_throttle:password_reset:") for k in new[0][1])
    n = len(fake.evals())
    _send(c, "POST", "/api/v1/auth/password-recovery",
          json={"access_token": "t", "refresh_token": "r", "new_password": NEW_PW})
    assert fake.evals()[n:] == []


def test_r34_ttls(monkeypatch):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    _account_user(monkeypatch)
    svc.service("register_user", {"success": True, "user": {"id": UID1}})
    svc.service("request_password_reset", {"success": True})
    svc.service("change_user_password", {"success": True, "message": "ok"})
    c = _tc()
    _reg(c, E1)
    (_n, _k, args) = fake.evals("INTERVAL_SCRIPT")[-1]
    assert args[1] == "20000" and args[2] == "20"  # the interval key expires at the interval
    _reset(c)
    (_n, _k, args) = fake.evals("RESET_SCRIPT")[-1]
    assert args[1] == "15000" and args[2] == "3" and args[3] == "15" and args[4] == "86400"
    dkeys = [k for k in fake.store if ":day" in k]
    assert len(dkeys) == 1
    dkey = dkeys[0]
    assert fake.exp[dkey] == clock.ms + 86400 * 1000
    clock.advance(16)
    _reset(c)
    assert fake.exp[dkey] == clock.ms - 16000 + 86400 * 1000  # the first increment only
    asyncio.run(at.record_login_failure(E1, dict(BAD_RESULT)))
    (_n, _k, args) = fake.evals("LOGIN_FAIL_SCRIPT")[-1]
    assert args[1] == "30000" and args[2] == "7200"
    _send(c, "PUT", "/api/v1/auth/password", json={"current_password": GOOD_PW, "new_password": NEW_PW})
    (_n, _k, args) = fake.evals("ACCOUNT_SCRIPT")[-1]
    assert args[1] == "2" and args[2] == "120000" and args[3] == "120"
    monkeypatch.setenv("AUTH_THROTTLE_TTL_SECONDS", "60")
    monkeypatch.setenv("AUTH_THROTTLE_LOGIN_CAP_SECONDS", "120")
    asyncio.run(at.record_login_failure(E2, dict(BAD_RESULT)))
    (_n, _k, args) = fake.evals("LOGIN_FAIL_SCRIPT")[-1]
    assert args[2] == "120"  # effective TTL = max(TTL, the cap)


# ===========================================================================
# R40-R42: the per-account routes
# ===========================================================================
def _pw(c):
    return _send(c, "PUT", "/api/v1/auth/password", json={"current_password": GOOD_PW, "new_password": NEW_PW})


def _em(c):
    return _send(c, "PUT", "/api/v1/auth/email", json={"current_password": GOOD_PW, "new_email": E2})


def _account_case(monkeypatch, logs, call, service, endpoint):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    _account_user(monkeypatch)
    svc.service(service, {"success": True, "message": "ok"})
    c = _tc()
    assert call(c).status_code == 200
    assert call(c).status_code == 200
    logs.clear()
    ra = _expect_v2_429(call(c), logs, endpoint)
    assert 1 <= ra <= 120
    assert svc.order.count(service) == 2
    keys = [k for e in fake.evals("ACCOUNT_SCRIPT") for k in e[1]]
    assert set(keys) == {at.throttle_key(endpoint, "account", _digest(PEPPER_VALUE, UID1))}
    assert not any(k.startswith("auth_throttle:login:") for k in fake.store)
    clock.advance(120)
    assert call(c).status_code == 200
    return at, fake, svc


def test_r40_change_password_account_window(monkeypatch, logs):
    _account_case(monkeypatch, logs, _pw, "change_user_password", "change_password")


def test_r41_update_email_account_window(monkeypatch, logs):
    _account_case(monkeypatch, logs, _em, "update_user_email", "update_email")


@pytest.mark.parametrize("call,service", [(_pw, "change_user_password"), (_em, "update_user_email")])
def test_r42_account_routes_keep_w19b(monkeypatch, call, service):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    _account_user(monkeypatch)
    svc.service(service, {"success": False, "error": "Current password is incorrect"})
    c = _tc()
    assert call(c).status_code == 400
    kinds = [x[0] if x[0] != "eval" else x[1][0] for x in fake.calls]
    assert kinds[0] == "ACCOUNT_SCRIPT"
    assert kinds[1:] == ["get", "set", "incr", "expire"]
    assert svc.order == ["check_account_locked", service, "track_failed_login"]
    svc.service(service, {"success": True, "message": "ok"})
    svc.order.clear()
    assert call(c).status_code == 200
    assert svc.order == ["check_account_locked", service, "clear_failed_logins"]


# ===========================================================================
# R50-R51: the 429 envelope
# ===========================================================================
def test_r50_v2_429_equals_slowapi_429(monkeypatch, logs):
    from app.middleware.rate_limiter import limiter
    svc = Svc(monkeypatch)
    svc.service("request_password_reset", {"success": True})
    c = _tc()
    limiter.reset()
    for _ in range(3):
        assert c.post("/api/v1/auth/password-reset", json={"email": E1}).status_code == 200
    slow = c.post("/api/v1/auth/password-reset", json={"email": E1})
    assert slow.status_code == 429
    assert not logs.lines("[AUTH_THROTTLE] throttled")
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    assert _reset(c, E2).status_code == 200
    logs.clear()
    v2 = _reset(c, E2)
    _expect_v2_429(v2, logs, "password_reset")
    sb, vb = slow.json(), v2.json()
    assert list(sb) == list(vb) == ["success", "error", "code", "request_id", "retry_after_seconds"]
    for k in ("success", "error", "code"):
        assert sb[k] == vb[k]
    assert [type(sb[k]) for k in sb] == [type(vb[k]) for k in vb]
    assert _names(slow) == _names(v2) == HDR_429
    assert v2.headers["retry-after"] == str(vb["retry_after_seconds"])


@pytest.mark.parametrize("retry", [0, -3])
def test_r51_retry_after_at_least_one(monkeypatch, logs, retry):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    svc.service("request_password_reset", {"success": True})
    fake.reply_override = [0, retry, 1]
    c = _tc()
    logs.clear()
    assert _expect_v2_429(_reset(c), logs, "password_reset") == 1


# ===========================================================================
# R60-R68: fail-open, the memo, the log hygiene, the shield
# ===========================================================================
def _route_cases(monkeypatch, svc):
    _account_user(monkeypatch)
    svc.service("register_user", {"success": True, "user": {"id": UID1}})
    svc.service("request_password_reset", {"success": True})
    svc.service("resend_verification_email", True)
    svc.service("change_user_password", {"success": True, "message": "ok"})
    svc.service("update_user_email", {"success": True, "message": "ok"})
    return [
        ("login_fail", lambda c: _login(c), 401, ["login", "login_fail"]),
        ("login_ok", lambda c: _login(c, pw=GOOD_PW), 200, ["login", "login_clear"]),
        ("register", lambda c: _reg(c, E1), 200, ["register"]),
        ("password_reset", _reset, 200, ["password_reset"]),
        ("resend", _resend, 200, ["resend_verification"]),
        ("change_password", _pw, 200, ["change_password"]),
        ("update_email", _em, 200, ["update_email"]),
    ]


def _set_login(svc, label):
    if label == "login_fail":
        svc.service("login_user", BAD_RESULT)
    elif label == "login_ok":
        svc.service("login_user", {"success": True, "user": {"id": UID1}, "session": {"access_token": "t"}})


def test_r60_no_client_fail_open(monkeypatch, logs):
    clock = Clock()
    at, _f = _arm(monkeypatch, clock, fake_cls=None)
    svc = Svc(monkeypatch)
    c = _tc()
    for label, call, status, endpoints in _route_cases(monkeypatch, svc):
        _set_login(svc, label)
        at._reset_skip_memo()
        logs.clear()
        r = call(c)
        assert r.status_code == status, label
        got = [SKIPPED_RE.fullmatch(m) for m in logs.lines("[AUTH_THROTTLE]")]
        assert all(got), label
        assert [(m.group(1), m.group(2)) for m in got] == [(e, "RedisUnconfigured") for e in endpoints], label
        for rec in logs.records:
            if rec.getMessage().startswith("[AUTH_THROTTLE] skipped"):
                assert rec.levelno == logging.WARNING


def test_r61_eval_raises_fail_open(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    fake.fail_with = ConnectionError
    svc = Svc(monkeypatch)
    c = _tc()
    for label, call, status, endpoints in _route_cases(monkeypatch, svc):
        _set_login(svc, label)
        at._reset_skip_memo()
        logs.clear()
        assert call(c).status_code == status, label
        got = [SKIPPED_RE.fullmatch(m) for m in logs.lines("[AUTH_THROTTLE]")]
        assert [(m.group(1), m.group(2)) for m in got] == [(e, "ConnectionError") for e in endpoints], label


def test_r62_eval_timeout_fail_open(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    monkeypatch.setenv(TIMEOUT_KNOB, "0.05")
    fake.delay = 0.5
    t0 = time.monotonic()
    assert _gate(at, "password_reset", E1) is None
    assert time.monotonic() - t0 < 0.4
    got = [SKIPPED_RE.fullmatch(m) for m in logs.lines("[AUTH_THROTTLE]")]
    assert [(m.group(1), m.group(2)) for m in got] == [("password_reset", "TimeoutError")]


@pytest.mark.parametrize("reply", [None, [1], ["1", "0", "0"], {}, [True, 0, 0], [2, 0, 0], (1, 0), "x"])
def test_r63_malformed_reply_fail_open(monkeypatch, logs, reply):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    fake.reply_override = reply
    assert _gate(at, "register", E1) is None
    got = [SKIPPED_RE.fullmatch(m) for m in logs.lines("[AUTH_THROTTLE]")]
    assert [(m.group(1), m.group(2)) for m in got] == [("register", "ValueError")]


def test_r64_record_failures_harmless(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    c = _tc()
    real_eval = fake._eval

    def flaky(script, keys, args):
        if script != FROZEN_TEXT["LOGIN_GATE_SCRIPT"]:
            raise RuntimeError("s24 record failure")
        return real_eval(script, keys, args)
    fake._eval = flaky
    svc.service("login_user", BAD_RESULT)
    r = _login(c)
    assert r.status_code == 401 and _fields(r) == LOGIN_401
    svc.service("login_user", {"success": True, "user": {"id": UID1}, "session": {"access_token": "t"}})
    r = _login(c, pw=GOOD_PW)
    assert r.status_code == 200
    got = [SKIPPED_RE.fullmatch(m) for m in logs.lines("[AUTH_THROTTLE]")]
    assert [(m.group(1), m.group(2)) for m in got] == [("login_fail", "RuntimeError"), ("login_clear", "RuntimeError")]


def test_r65_log_hygiene(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    svc = Svc(monkeypatch)
    c = _tc()
    for label, call, status, endpoints in _route_cases(monkeypatch, svc):
        _set_login(svc, label)
        call(c)
        call(c)
        call(c)
    fake.fail_with = ConnectionError
    at._reset_skip_memo()
    for label, call, status, endpoints in _route_cases(monkeypatch, svc):
        _set_login(svc, label)
        call(c)
    monkeypatch.delenv(PEPPER_ENV_NAME)
    at._reset_pepper_warning()
    _login(c)
    msgs = logs.lines("[AUTH_THROTTLE]")
    assert any(THROTTLED_RE.fullmatch(m) for m in msgs)
    assert any(SKIPPED_RE.fullmatch(m) for m in msgs)
    assert PEPPER_LINE in msgs
    forbidden = [E1, E2, "user-a", "user-b", PEPPER_VALUE, UID1, "auth_throttle:"]
    for m in msgs:
        assert THROTTLED_RE.fullmatch(m) or SKIPPED_RE.fullmatch(m) or m == PEPPER_LINE, m
        for f in forbidden:
            assert f not in m, m
        assert not re.search(r"[0-9a-f]{32}", m), m
    for r in logs.records:
        if r.name == MOD:
            assert r.levelno in (logging.INFO, logging.WARNING)


@pytest.mark.parametrize("ident", [None, 123, b"x", "", "   "])
def test_r66_bad_ident_allows(monkeypatch, logs, ident):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    assert _gate(at, "login", ident) is None
    assert fake.calls == [] and logs.lines("[AUTH_THROTTLE]") == []
    assert _gate(at, "login", E1) is None
    assert len(fake.evals()) == 1


def test_r67_skip_memo_per_endpoint(monkeypatch, logs):
    clock = Clock()
    at, _f = _arm(monkeypatch, clock, fake_cls=None)
    mono = [1000.0]
    monkeypatch.setattr(at, "_monotonic", lambda: mono[0])
    at._reset_skip_memo()
    for _ in range(3):
        assert _gate(at, "login", E1) is None
    assert _gate(at, "register", E1) is None
    eps = [SKIPPED_RE.fullmatch(m).group(1) for m in logs.lines("[AUTH_THROTTLE] skipped")]
    assert eps == ["login", "register"]
    mono[0] += 59.0
    assert _gate(at, "login", E1) is None
    assert len(logs.lines("[AUTH_THROTTLE] skipped")) == 2
    mono[0] += 1.5
    assert _gate(at, "login", E1) is None
    eps = [SKIPPED_RE.fullmatch(m).group(1) for m in logs.lines("[AUTH_THROTTLE] skipped")]
    assert eps == ["login", "register", "login"]
    at._reset_skip_memo()
    assert _gate(at, "register", E1) is None
    assert len(logs.lines("[AUTH_THROTTLE] skipped")) == 4


def test_r68_record_writes_shielded_gate_cancellable(monkeypatch, logs):
    clock = Clock()
    at, fake = _arm(monkeypatch, clock)
    monkeypatch.setenv(TIMEOUT_KNOB, "0.05")
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="s24-test")
    monkeypatch.setattr(at, "_pool", lambda: ex)
    hold = threading.Event()
    try:
        ex.submit(hold.wait, 5.0)

        async def cancelled_record():
            t = asyncio.ensure_future(at.record_login_failure(E1, dict(BAD_RESULT)))
            await asyncio.sleep(0.01)
            t.cancel()
            try:
                await t
            except BaseException:
                pass
        asyncio.run(cancelled_record())
        asyncio.run(at.record_login_success(E2))   # times out at 0.05 s while queued
        asyncio.run(at.gate("login", E1))          # times out while queued: cancelled
        hold.set()
    finally:
        hold.set()
        ex.shutdown(wait=True)
    names = [e[0] for e in fake.evals()]
    assert names == ["LOGIN_FAIL_SCRIPT", "LOGIN_CLEAR_SCRIPT"], names


# ===========================================================================
# R82-R83: AST placement pins
# ===========================================================================
def _routes_tree():
    src = (REPO / "app" / "api" / "auth_routes.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    return {n.name: n for n in tree.body if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))}


def _is_flag_if(node):
    if not isinstance(node, ast.If):
        return False
    t = node.test
    return (isinstance(t, ast.Call) and isinstance(t.func, ast.Attribute)
            and isinstance(t.func.value, ast.Name) and t.func.value.id == "auth_throttle"
            and t.func.attr == "auth_throttle_v2_enabled" and not t.args)


def _awaited_call(node, attr):
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Await)):
        return None
    call = node.value.value
    if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == "auth_throttle"
            and call.func.attr == attr):
        return call
    return None


def _body_wo_doc(fn):
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


GATED = {
    "login": ("login", "body.email"),
    "register": ("register", "body.email"),
    "password_reset": ("password_reset", "body.email"),
    "resend_verification": ("resend_verification", "body.email"),
    "change_password": ("change_password", "current_user['id']"),
    "update_email": ("update_email", "current_user['id']"),
}


def test_r82_v2_placement_ast():
    fns = _routes_tree()
    for fname, (endpoint, ident) in GATED.items():
        body = _body_wo_doc(fns[fname])
        idx = [i for i, s in enumerate(body) if _is_flag_if(s)
               and len(s.body) == 1 and _awaited_call(s.body[0], "gate") is not None]
        assert len(idx) == 1, fname
        i = idx[0]
        node = body[i]
        assert not node.orelse, fname
        call = _awaited_call(node.body[0], "gate")
        assert [ast.unparse(a) for a in call.args] == [repr(endpoint), ident], fname
        assert not call.keywords, fname
        for s in body[:i]:
            assert not any(isinstance(n, ast.Await) for n in ast.walk(s)), fname
        if fname == "register":
            prev = body[i - 1]
            assert isinstance(prev, ast.If) and "consent_required_enabled" in ast.unparse(prev.test)
        else:
            assert i == 0, fname
    for fname in ("refresh", "password_recovery", "social_login", "delete_account", "get_me",
                  "verify_auth", "update_profile", "update_push_token", "update_reengagement_subs",
                  "update_preference_toggles", "save_demographics", "save_attribution", "logout",
                  "get_preferences", "save_preferences", "get_cohort_profile"):
        if fname in fns:
            assert "auth_throttle" not in ast.unparse(fns[fname]), fname
    src = (REPO / "app" / "api" / "auth_routes.py").read_text(encoding="utf-8")
    assert "from app.services import auth_throttle" in src


def test_r83_login_record_placement_ast():
    fn = _routes_tree()["login"]
    top = _body_wo_doc(fn)
    fail_if = [s for s in top if isinstance(s, ast.If) and ast.unparse(s.test) == "not result['success']"]
    assert len(fail_if) == 1
    inner = fail_if[0].body
    idx = [i for i, s in enumerate(inner) if ast.unparse(s) == "await track_failed_login(body.email)"]
    assert len(idx) == 1
    nxt = inner[idx[0] + 1]
    assert _is_flag_if(nxt) and len(nxt.body) == 1
    call = _awaited_call(nxt.body[0], "record_login_failure")
    assert call is not None and [ast.unparse(a) for a in call.args] == ["body.email", "result"]
    idx = [i for i, s in enumerate(top) if ast.unparse(s) == "await clear_failed_logins(body.email)"]
    assert len(idx) == 1
    nxt = top[idx[0] + 1]
    assert _is_flag_if(nxt) and len(nxt.body) == 1
    call = _awaited_call(nxt.body[0], "record_login_success")
    assert call is not None and [ast.unparse(a) for a in call.args] == ["body.email"]
    n_records = ast.unparse(fn).count("auth_throttle.record_login_")
    assert n_records == 2


# ===========================================================================
# R90-R93: env safety, leaf imports, hygiene, the pool
# ===========================================================================
def test_r90_pepper_in_credentials_unset():
    from tests import _env_safety
    assert PEPPER_ENV_NAME in _env_safety.CREDENTIALS_UNSET
    m = _mod()
    src = Path(m.__file__).read_text(encoding="utf-8")
    assert ("DEVICE_KEY" + "_PEPPER").lower() not in src.lower()


def _throttle_src():
    m = _mod()
    return Path(m.__file__).read_text(encoding="utf-8")


def test_r91_leaf_imports(monkeypatch):
    src = _throttle_src()
    tree = ast.parse(src)
    stdlib = set(sys.stdlib_module_names)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in stdlib, a.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.split(".")[0] in stdlib or mod == "__future__":
                continue
            if mod.split(".")[0] == "fastapi":
                continue
            assert mod == "app.services", mod
            assert [(a.name, a.asname) for a in node.names] == [("cache_service", "_cache_service")]
    for bad in ("auth_service", "llm_spend_breaker", "usage_service", "request" + "_context",
                "import redis_client"):
        assert bad not in src, bad
    at = _mod()
    clock = Clock()
    out = []
    for cls in (FakeRedis, FakeRedisPy):
        f = cls(clock)
        out.append(at._eval(f, FROZEN_TEXT["INTERVAL_SCRIPT"], ["k1"], [str(T0_MS), "1000", "1"]))
        assert f.evals() == [("INTERVAL_SCRIPT", ("k1",), (str(T0_MS), "1000", "1"))]
    assert out[0] == out[1] == [1, 0, 1]


GITLEAKS_WORDS = ("access", "auth", "api", "credential", "creds", "key", "password", "secret", "token")
G1_NEEDLES = ("request" + "_context", ("device_key" + "_pepper"), "x-ai-consent" + "-version",
              "x-compare" + "-request-id", "header" + "_state")


def _hygiene(path):
    raw = path.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0, path.name
    text = raw.decode("ascii").lower()
    for n in G1_NEEDLES:
        assert n not in text, (path.name, n)
    tree = ast.parse(raw.decode("ascii"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", node.value.value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assert not any(w in t.id.lower() for w in GITLEAKS_WORDS), t.id


def test_r92_hygiene():
    m = _mod()
    _hygiene(Path(m.__file__))
    _hygiene(REPO / "app" / "middleware" / "request_id.py")
    assert b"\r\n" not in Path(m.__file__).read_bytes()
    src = Path(m.__file__).read_text(encoding="utf-8")
    for needle in ("BeautifulSoup", "QarenBot", "kb_", "chat.completions"):
        assert needle not in src, needle


def test_r93_pool_shape(monkeypatch):
    at = _mod()
    assert _need("POOL_WORKERS", at) == 4
    assert _need("POOL_THREAD_PREFIX", at) == "auth-throttle"
    _need("_POOL", at)
    monkeypatch.setattr(at, "_POOL", None)
    pool = at._pool()
    try:
        assert isinstance(pool, concurrent.futures.ThreadPoolExecutor)
        assert pool._max_workers == 4
        assert pool._thread_name_prefix == "auth-throttle"
        assert at._pool() is pool
        names = []
        pool.submit(lambda: names.append(threading.current_thread().name)).result(5)
        assert names and names[0].startswith("auth-throttle")
    finally:
        pool.shutdown(wait=False)


# ===========================================================================
# R100-R108: the MS4 echo line (R-S24-23, C2, C3)
# ===========================================================================
def _hop_lines(logs):
    return logs.lines("[HOP_PROBE]")


def _hop(line):
    m = HOP_RE.fullmatch(line)
    assert m, line
    return m.groups()


def test_r100_hop_probe_health_line(monkeypatch, logs):
    monkeypatch.setenv(HOP_FLAG, "true")
    c = _tc(client=("100.64.0.1", 50000))
    r = c.get("/health", headers={"X-Forwarded-For": "8.8.8.8, 100.64.0.1"})
    assert r.status_code == 200
    assert _hop_lines(logs) == [
        "[HOP_PROBE] xff_entries=2 xff_leftmost_is_peer=false xff_rightmost_is_peer=true "
        "xff_leftmost_public=true x_real_ip_present=false x_real_ip_is_peer=false "
        "x_real_ip_public=false forwarded_present=false cf_present=false peer_public=false "
        "uvicorn_forwarded_allow_ips_set=false"
    ]
    recs = [x for x in logs.records if x.getMessage().startswith("[HOP_PROBE]")]
    assert recs[0].levelno == logging.INFO and recs[0].name == RID_MOD


def test_r101_hop_probe_version_headers(monkeypatch, logs):
    monkeypatch.setenv(HOP_FLAG, "1")
    c = _tc(client=("100.64.0.1", 50000))
    r = c.get("/api/v1/app/version", headers={"X-Real-IP": "100.64.0.1", "Forwarded": "for=192.0.2.1",
                                               "CF-Connecting-IP": "192.0.2.1"})
    assert r.status_code == 200
    assert _hop_lines(logs) == [
        "[HOP_PROBE] xff_entries=0 xff_leftmost_is_peer=false xff_rightmost_is_peer=false "
        "xff_leftmost_public=false x_real_ip_present=true x_real_ip_is_peer=true "
        "x_real_ip_public=false forwarded_present=true cf_present=true peer_public=false "
        "uvicorn_forwarded_allow_ips_set=false"
    ]


def test_r102_hop_probe_paths_only(monkeypatch, logs):
    monkeypatch.setenv(HOP_FLAG, "true")
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    c = _tc(client=("100.64.0.1", 50000))
    xff = {"X-Forwarded-For": "8.8.8.8"}
    _send(c, "POST", "/api/v1/auth/login", json={"email": E1, "password": BAD_PW}, headers=xff)
    _send(c, "GET", "/", headers=xff)
    _send(c, "GET", "/api/v1/usage/status", headers=xff)
    _send(c, "HEAD", "/health", headers=xff)
    _send(c, "POST", "/health", headers=xff)
    _send(c, "GET", "/healthz", headers=xff)
    assert _hop_lines(logs) == []
    _send(c, "GET", "/health", headers=xff)
    assert len(_hop_lines(logs)) == 1


def test_r103_hop_probe_no_values(monkeypatch, logs):
    monkeypatch.setenv(HOP_FLAG, "true")
    monkeypatch.setenv(UVICORN_ENV_NAME, "198.51.100.77")
    c = _tc(client=("203.0.113.9", 41000))
    vals = ["8.8.4.4", "203.0.113.9", "198.51.100.23", "192.0.2.44", "for=192.0.2.45"]
    c.get("/health", headers={"X-Forwarded-For": "8.8.4.4, 198.51.100.23", "X-Real-IP": "192.0.2.44",
                              "Forwarded": "for=192.0.2.45", "CF-Connecting-IP": "8.8.4.4"})
    c.get("/api/v1/app/version", headers={"X-Forwarded-For": "not-an-ip"})
    lines = _hop_lines(logs)
    assert len(lines) == 2
    for line in lines:
        _hop(line)
        for v in vals + ["198.51.100.77", "not-an-ip"]:
            assert v not in line
        assert not re.search(r"\d+\.\d+\.\d+\.\d+", line)
    assert lines[0].endswith("uvicorn_forwarded_allow_ips_set=true")


def test_r104_hop_probe_garbage(monkeypatch, logs):
    c = _tc(client=("100.64.0.1", 50000))
    cases = [
        ({"X-Forwarded-For": "not-an-ip, , 300.1.1.1"}, "2"),
        ({"X-Forwarded-For": ", ".join("10.0.%d.%d" % (i // 250, i % 250) for i in range(200))}, "200"),
        ({"X-Forwarded-For": b"caf" + bytes([0xC3, 0xA9])}, "1"),
    ]
    off = []
    for headers, _n in cases:
        r = c.get("/health", headers=headers)
        off.append((r.status_code, sorted(r.json())))
    assert _hop_lines(logs) == []
    monkeypatch.setenv(HOP_FLAG, "on")
    for (headers, n), (st, keys) in zip(cases, off):
        logs.clear()
        r = c.get("/health", headers=headers)
        assert (r.status_code, sorted(r.json())) == (st, keys)
        lines = _hop_lines(logs)
        assert len(lines) == 1
        g = _hop(lines[0])
        assert g[0] == n
        if n != "200":
            assert g[1:4] == ("false", "false", "false")


@pytest.mark.parametrize("raw,want", [
    (None, False), ("", False), ("false", False), ("0", False), ("off", False), ("no", False),
    ("garbage", False), ("true", True), ("1", True), ("yes", True), ("on", True),
    (" TRUE ", True), ("On", True),
])
def test_r105_hop_probe_flag_idiom(monkeypatch, logs, raw, want):
    fn = _need("hop_probe_log_enabled", _rid())
    if raw is None:
        monkeypatch.delenv(HOP_FLAG, raising=False)
    else:
        monkeypatch.setenv(HOP_FLAG, raw)
    assert fn() is want
    c = _tc(client=("100.64.0.1", 50000))
    c.get("/health")
    assert len(_hop_lines(logs)) == (1 if want else 0)
    monkeypatch.setenv(HOP_FLAG, "false" if want else "true")
    c.get("/health")
    assert len(_hop_lines(logs)) == 1


def test_r107_hop_probe_uvicorn_boolean(monkeypatch, logs):
    monkeypatch.setenv(HOP_FLAG, "true")
    c = _tc(client=("100.64.0.1", 50000))
    c.get("/health")
    monkeypatch.setenv(UVICORN_ENV_NAME, "127.0.0.1")
    c.get("/health")
    monkeypatch.setenv(UVICORN_ENV_NAME, "")
    c.get("/health")
    monkeypatch.delenv(UVICORN_ENV_NAME)
    c.get("/health")
    flags = [_hop(x)[-1] for x in _hop_lines(logs)]
    assert flags == ["false", "true", "true", "false"]
    assert _need("HOP_PROBE_PATHS", _rid()) == ("/health", "/api/v1/app/version")


def test_r108_hop_probe_client_none_and_raising_request(monkeypatch, logs):
    from starlette.requests import Request
    fn = _need("_log_hop_probe", _rid())
    scope = {"type": "http", "method": "GET", "path": "/health", "query_string": b"",
             "headers": [(b"x-forwarded-for", b"8.8.8.8")]}
    req = Request(scope)
    assert req.client is None
    fn(req)
    lines = _hop_lines(logs)
    assert len(lines) == 1
    g = _hop(lines[0])
    assert g[0] == "1" and g[1] == "false" and g[2] == "false" and g[3] == "true" and g[9] == "false"

    class Boom:
        client = None

        @property
        def headers(self):
            raise RuntimeError("s24 boom")
    logs.clear()
    raised = None
    try:
        out = fn(Boom())
    except Exception as exc:  # the bare except is the contract: never raises
        raised, out = type(exc).__name__, None
    assert raised is None and out is None
    assert _hop_lines(logs) == []


# ===========================================================================
# PIN rows (green at base): the flag-OFF identity with the FULL configuration
# ===========================================================================
OFF_SPELLINGS = [None, "", "false", "0", "off", " FALSE "]

LOGIN_CASES = {
    "fail": (BAD_RESULT, 401, LOGIN_401, HDR_200,
             lambda lk: [("get", lk), ("set", lk, 0, ("ex", 900), ("nx", True)), ("incr", lk),
                         ("expire", lk, 900, ("nx", True))],
             ["check_account_locked", "login_user", "track_failed_login", "audit:login_failed"]),
    "ok": ({"success": True, "user": {"id": UID1}, "session": {"access_token": "t"}}, 200,
           {"success": True, "user": {"id": UID1}, "session": {"access_token": "t"}, "message": None, "error": None},
           HDR_200, lambda lk: [("get", lk), ("delete", lk)],
           ["check_account_locked", "login_user", "clear_failed_logins", "audit:login_success"]),
    "locked": (BAD_RESULT, 429, {"success": False, "error": LOCKED_ERR, "code": "ACCOUNT_LOCKED",
                                 "retry_after_seconds": 900}, HDR_429,
               lambda lk: [("get", lk), ("ttl", lk)],
               ["check_account_locked", "audit:brute_force_lockout"]),
}


def _seq(fake):
    return [(x[0],) + tuple(x[1]) + tuple(x[2]) for x in fake.calls]


def _off_common(monkeypatch, spelling):
    _full_config(monkeypatch, spelling)
    m = _mod_if_present()
    if m is not None:
        monkeypatch.setattr(m, "_POOL", None, raising=False)
    clock = Clock()
    fake = FakeRedis(clock)
    _install(monkeypatch, fake)
    return m, clock, fake


def _off_checks(m, fake, logs):
    assert [x for x in fake.calls if x[0] == "eval"] == []
    assert logs.lines("[AUTH_THROTTLE]") == []
    assert logs.lines("[HOP_PROBE]") == []
    if m is not None:
        assert getattr(m, "_POOL", None) is None


@pytest.mark.parametrize("spelling", OFF_SPELLINGS)
@pytest.mark.parametrize("case", sorted(LOGIN_CASES))
def test_p70_off_identity_login(monkeypatch, logs, case, spelling):
    m, clock, fake = _off_common(monkeypatch, spelling)
    result, status, fields, hdrs, seqf, order = LOGIN_CASES[case]
    lk = _lock_key(E1)
    if case == "locked":
        fake.store[lk] = 5
        fake.exp[lk] = clock.ms + 900 * 1000
    svc = Svc(monkeypatch)
    svc.service("login_user", result)
    c = _tc()
    logs.clear()
    r = _login(c, pw=BAD_PW if case != "ok" else GOOD_PW)
    assert r.status_code == status
    assert _fields(r) == fields
    assert _names(r) == hdrs
    if status == 429:
        assert r.headers["retry-after"] == "900"
    assert _seq(fake) == seqf(lk)
    assert svc.order == order
    assert logs.app_records() == []
    _off_checks(m, fake, logs)


OTHER_CASES = {
    "register_ok": ("register_user", {"success": True, "user": {"id": UID1}}, None,
                    lambda c: _reg(c, E1), 200, {"success": True, "user": {"id": UID1}, "session": None,
                                                 "message": None, "error": None}, [], ["register_user"]),
    "register_exists": ("register_user", {"success": False, "error": "An account with this email already exists"},
                        None, lambda c: _reg(c, E1), 400,
                        {"success": False, "error": "An account with this email already exists", "code": "BAD_REQUEST"},
                        [], ["register_user"]),
    "reset_ok": ("request_password_reset", {"success": True}, None, _reset, 200, RESET_BODY, [],
                 ["request_password_reset"]),
    "reset_fail": ("request_password_reset", {"success": False, "error": "x"}, None, _reset, 200, RESET_BODY, [],
                   ["request_password_reset"]),
    "resend_ok": ("resend_verification_email", True, None, _resend, 200, RESEND_BODY, [],
                  ["resend_verification_email"]),
    "resend_raise": ("resend_verification_email", None, RuntimeError("s24 boom"), _resend, 200, RESEND_BODY,
                     [], ["resend_verification_email"]),
    "pw_ok": ("change_user_password", {"success": True, "message": "ok"}, None, _pw, 200,
              {"success": True, "message": "ok"}, "ok", ["check_account_locked", "change_user_password",
                                                         "clear_failed_logins"]),
    "pw_wrong": ("change_user_password", {"success": False, "error": "Current password is incorrect"}, None, _pw,
                 400, {"success": False, "error": "Current password is incorrect", "code": "BAD_REQUEST"}, "fail",
                 ["check_account_locked", "change_user_password", "track_failed_login"]),
    "pw_locked": ("change_user_password", {"success": True, "message": "ok"}, None, _pw, 429,
                  {"success": False, "error": LOCKED_ERR, "code": "ACCOUNT_LOCKED", "retry_after_seconds": 900},
                  "locked", ["check_account_locked", "audit:brute_force_lockout"]),
    "em_ok": ("update_user_email", {"success": True, "message": "ok"}, None, _em, 200,
              {"success": True, "message": "ok"}, "ok", ["check_account_locked", "update_user_email",
                                                         "clear_failed_logins"]),
    "em_wrong": ("update_user_email", {"success": False, "error": "Current password is incorrect"}, None, _em,
                 400, {"success": False, "error": "Current password is incorrect", "code": "BAD_REQUEST"}, "fail",
                 ["check_account_locked", "update_user_email", "track_failed_login"]),
    "em_locked": ("update_user_email", {"success": True, "message": "ok"}, None, _em, 429,
                  {"success": False, "error": LOCKED_ERR, "code": "ACCOUNT_LOCKED", "retry_after_seconds": 900},
                  "locked", ["check_account_locked", "audit:brute_force_lockout"]),
}


def _w19b_seq(kind, lk):
    if kind == "ok":
        return [("get", lk), ("delete", lk)]
    if kind == "fail":
        return [("get", lk), ("set", lk, 0, ("ex", 900), ("nx", True)), ("incr", lk),
                ("expire", lk, 900, ("nx", True))]
    if kind == "locked":
        return [("get", lk), ("ttl", lk)]
    return []


@pytest.mark.parametrize("spelling", OFF_SPELLINGS)
@pytest.mark.parametrize("case", sorted(OTHER_CASES))
def test_p71_off_identity_other_routes(monkeypatch, logs, case, spelling):
    m, clock, fake = _off_common(monkeypatch, spelling)
    service, result, exc, call, status, fields, seqkind, order = OTHER_CASES[case]
    lk = _lock_key(E1)
    if seqkind == "locked":
        fake.store[lk] = 5
        fake.exp[lk] = clock.ms + 900 * 1000
    svc = Svc(monkeypatch)
    svc.service(service, result, exc)
    _account_user(monkeypatch)
    c = _tc()
    logs.clear()
    r = call(c)
    assert r.status_code == status
    assert _fields(r) == fields
    assert _names(r) == (HDR_429 if status == 429 else HDR_200)
    if status == 429:
        assert r.headers["retry-after"] == "900"
    assert _seq(fake) == (_w19b_seq(seqkind, lk) if seqkind else [])
    assert svc.order == order
    want_logs = [("app.api.auth_routes", "ERROR", "Resend verification error: s24 boom")] if case == "resend_raise" else []
    assert logs.app_records() == want_logs
    _off_checks(m, fake, logs)


def test_p72_off_no_throttle_records(monkeypatch, logs):
    m, clock, fake = _off_common(monkeypatch, "false")
    svc = Svc(monkeypatch)
    svc.service("login_user", BAD_RESULT)
    svc.service("register_user", {"success": True, "user": {"id": UID1}})
    svc.service("request_password_reset", {"success": True})
    svc.service("resend_verification_email", True)
    svc.service("change_user_password", {"success": True, "message": "ok"})
    svc.service("update_user_email", {"success": True, "message": "ok"})
    _account_user(monkeypatch)
    c = _tc()
    for _ in range(4):
        for call in (_login, lambda c: _reg(c, E1), _reset, _resend, _pw, _em):
            call(c)
            clock.advance(1)
    _off_checks(m, fake, logs)


@pytest.mark.parametrize("v2", ["true", None])
@pytest.mark.parametrize("spelling", OFF_SPELLINGS)
def test_p73_hop_probe_off_silent(monkeypatch, logs, spelling, v2):
    _full_config(monkeypatch, v2)
    if spelling is None:
        monkeypatch.delenv(HOP_FLAG, raising=False)
    else:
        monkeypatch.setenv(HOP_FLAG, spelling)
    c = _tc(client=("100.64.0.1", 50000))
    forged = {"X-Forwarded-For": "192.0.2.1, 8.8.8.8", "X-Real-IP": "192.0.2.2", "Forwarded": "for=192.0.2.3",
              "CF-Connecting-IP": "192.0.2.4"}
    h = c.get("/health", headers=forged)
    v = c.get("/api/v1/app/version", headers=forged)
    assert h.status_code == 200 and v.status_code == 200
    # the TestClient runs no lifespan here, so /health carries no adapter_executor key
    assert sorted(h.json()) == ["loop_lag_max_60s_ms", "loop_lag_max_ms", "loop_lag_ms", "message", "status"]
    assert sorted(v.json()) == ["force_update", "latest_version", "min_version", "update_url_android",
                                "update_url_ios"]
    assert _names(h) == HDR_200
    assert logs.lines("[HOP_PROBE]") == []


@pytest.mark.parametrize("v2", [None, "true"])
def test_p74_429_contract_both_states(monkeypatch, logs, v2):
    _full_config(monkeypatch, v2)
    _install(monkeypatch, None)
    from app.middleware.rate_limiter import limiter
    svc = Svc(monkeypatch)
    svc.service("request_password_reset", {"success": True})
    c = _tc()
    limiter.reset()
    for _ in range(3):
        r = c.post("/api/v1/auth/password-reset", json={"email": E1})
        assert r.status_code == 200 and r.json() == RESET_BODY
    r = c.post("/api/v1/auth/password-reset", json={"email": E1})
    assert r.status_code == 429
    body = r.json()
    assert list(body) == ["success", "error", "code", "request_id", "retry_after_seconds"]
    assert _fields(r) == dict(SLOWAPI_429, retry_after_seconds=body["retry_after_seconds"])
    assert 1 <= body["retry_after_seconds"] <= 61
    assert r.headers["retry-after"] == str(body["retry_after_seconds"])
    assert _names(r) == HDR_429
    assert logs.lines("[AUTH_THROTTLE] throttled") == []


DECORATOR_TABLE = [
    ("register", "post", "/register", "3/minute"),
    ("login", "post", "/login", "5/minute"),
    ("refresh", "post", "/refresh", "10/minute"),
    ("password_reset", "post", "/password-reset", "3/minute"),
    ("password_recovery", "post", "/password-recovery", "5/minute"),
    ("update_email", "put", "/email", "5/minute"),
    ("change_password", "put", "/password", "5/minute"),
    ("social_login", "post", "/social-login", "10/minute"),
    ("delete_account", "delete", "/account", "1/minute"),
    ("resend_verification", "post", "/resend-verification", "3/minute"),
    ("update_push_token", "put", "/push-token", "10/minute"),
    ("update_reengagement_subs", "put", "/reengagement-subs", "10/minute"),
    ("update_preference_toggles", "put", "/preference-toggles", "10/minute"),
    ("save_demographics", "put", "/demographics", "5/minute"),
    ("save_attribution", "post", "/attribution", "30/minute"),
]
UNDECORATED = ["get_me", "verify_auth", "update_profile", "get_preferences", "save_preferences",
               "get_cohort_profile"]


def _deco_info(fn):
    router = []
    limits = []
    for i, d in enumerate(fn.decorator_list):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
            owner = ast.unparse(d.func.value)
            if owner == "router":
                router.append((i, d.func.attr, d.args[0].value if d.args else None))
            elif owner == "limiter" and d.func.attr == "limit":
                limits.append((i, d))
    return router, limits


def test_p80_decorator_table_ast():
    fns = _routes_tree()
    got = []
    for name, fn in fns.items():
        router, limits = _deco_info(fn)
        if router and limits:
            assert len(limits) == 1, name
            d = limits[0][1]
            assert not d.keywords and len(d.args) == 1, name
            got.append((name, router[0][1], router[0][2], d.args[0].value))
    assert got == DECORATOR_TABLE
    for name in UNDECORATED:
        router, limits = _deco_info(fns[name])
        assert router and not limits, name
    src = (REPO / "app" / "api" / "auth_routes.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    budget = [n for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "_EXPIRED_LOGOUT_BUDGET" for t in n.targets)]
    assert len(budget) == 1 and ast.unparse(budget[0].value) == "parse_rate_limit('10/minute')"


def test_p81_decorator_order_ast():
    fns = _routes_tree()
    n = 0
    for name, fn in fns.items():
        router, limits = _deco_info(fn)
        if limits:
            assert len(router) == 1 and len(limits) == 1, name
            assert limits[0][0] == router[0][0] + 1, name
            n += 1
    assert n == 15


def test_p83_red_file_setenv_hygiene():
    """C6: no high-entropy literal beside an AUTH_THROTTLE_* name in a setenv line,
    no gitleaks-keyword constant beside a 64-hex literal, pure ASCII + LF."""
    path = Path(__file__)
    raw = path.read_bytes()
    assert sum(1 for b in raw if b > 127) == 0
    assert b"\r\n" not in raw
    tree = ast.parse(raw.decode("ascii"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setenv":
            if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant) \
                    and str(node.args[0].value).startswith("AUTH_"):
                v = node.args[1]
                if isinstance(v, ast.Constant):
                    assert len(str(v.value)) <= 8, ast.unparse(node)
    _hygiene(path)
    lowered = raw.decode("ascii").lower()
    for n in G1_NEEDLES:
        assert n not in lowered


def test_p106_probe_paths_unchanged_on(monkeypatch):
    c = _tc(client=("100.64.0.1", 50000))
    hdr = {"X-Forwarded-For": "192.0.2.1"}
    out = []
    for flag in (None, "true"):
        if flag is None:
            monkeypatch.delenv(HOP_FLAG, raising=False)
        else:
            monkeypatch.setenv(HOP_FLAG, flag)
        h = c.get("/health", headers=hdr)
        v = c.get("/api/v1/app/version", headers=hdr)
        out.append((h.status_code, sorted(h.json()), _names(h), v.status_code, v.json(), _names(v)))
    assert out[0] == out[1]

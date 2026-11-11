"""S81-09 DEVICE-QUOTA-RIYADH: RED + PIN rows (ENABLE_DEVICE_DAILY_QUOTA and
ENABLE_RIYADH_RESET, both new names, default OFF, read per call).

Spec: .qa-s80/S81-09_UNIT_SPEC.md (base e7c81956, sha 33fd9b53) as amended by its
adversarial review (.qa-s80/S81-09_SPEC_REVIEW.md: B1-B2, RC1-RC8, C1-C19) and the
BINDING orchestrator rulings RULINGS_S81_09.md (session-81 state folder). Where
they disagree the rulings win, then the review corrections, then the spec. The
rulings this file encodes:

- R-S09-1 (the status contract): under the quota flag /usage/status sends
  remaining.daily = min(account-daily remaining, device-daily remaining) and
  used.daily = the matching (binding-axis) used figure; remaining.device_daily
  only with a device key; counted_scope 'device_daily' when the device axis binds
  (ties name the device), else 'daily'; remaining.monthly the full allowance;
  remaining.lifetime_free 0; used.lifetime present. Rows r19, r20, r37 and the
  S81-08 reader port r38 (stateFromStatus / openRemaining / the counter of
  sc-s81-s08 HEAD bcf75f84, hand-ported to Python).
- R-S09-2: the referral-reward pause folded in (r40, r41, p15).
- R-S09-3: the request-scoped debit stash; the L6 row r39 (consume under ON,
  refund after the flag goes OFF still refunds the device key from the stash).
- R-S09-4 / R-S09-5: account-based exemption (premium + the allow-list), the
  predicate tier == 'free' (a NULL tier runs the base path: p16).
- R-S09-6: NO cap knob; the module constant DEVICE_DAILY_CAP = 3 (r02) and an
  additive limits.device_daily = 3 on the status (r19).
- R-S09-8: zero [USAGE-DEVICE] records when a device key exists (r06, r10); the
  M33 case (account 3 + device 3 -> scope device_daily) in r08; r10 asserts the
  full code-0 result dict.
- R-S09-9: the golden fixture stores route and status bodies as RAW response text
  and result dicts as insertion-order dumps (key order pinned).
- R-S09-10: no Lua runtime on the box: the fake emulates both scripts in Python
  keyed on the module constants; r35 pins the literals, r35b parses their shape.
- R-S09-14: the status quota path at lifetime 0 and 2 (r37).

RED rows fail at base on an AssertionError ONLY: every missing symbol is read
through _need() (getattr + assert). PIN rows pass at base and run with the FULL
configuration (both flags OFF in one of the five OFF spellings, the request
context middleware ON with a valid X-Device-Fingerprint bound, DEVICE_KEY_PEPPER,
the decoy DEVICE_DAILY_QUOTA_CAP=7, DEVICE_QUOTA_EXEMPT_USER_IDS naming another
synthetic uid, ENABLE_PAID_ROUTE_METERING=true) plus call recorders (ruling B1).

Hermetic: Redis and Supabase are fakes, no network, no credential value; every
id, fingerprint and pepper is synthetic (the pepper is built by concatenation).
The golden fixture tests/fixtures/s81_s09_flag_off_golden.json was recorded AT
BASE by _record_golden() below (never hand-written).
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import copy
import hashlib
import hmac
import inspect
import json
import logging
import math
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.main as app_main  # FIRST: the dotenv guard (load_dotenv at import)
from app.api import image_routes, text_routes, url_routes, usage_routes
from app.api.auth_routes import get_current_user, get_optional_user
from app.middleware import error_handler as eh
from app.services import (
    content_safety_service,
    extraction_service,
    feedback_service,
    llm_spend_breaker as lsb,
    referral_service as rsvc,
    url_extraction_service,
    usage_service as us,
)
from app.utils import request_context as rc

# ---------------------------------------------------------------------------
# names and synthetic values
# ---------------------------------------------------------------------------
QUOTA = "ENABLE_DEVICE_DAILY_QUOTA"
RIYADH = "ENABLE_RIYADH_RESET"
CTX = "ENABLE_REQUEST_CONTEXT_HEADERS"
PEPPER_ENV = "DEVICE_KEY_PEPPER"
EXEMPT = "DEVICE_QUOTA_EXEMPT_USER_IDS"
CAP_DECOY = "DEVICE_DAILY_QUOTA_CAP"  # the spec's knob; R-S09-6 retired it
METER = "ENABLE_PAID_ROUTE_METERING"
ASYNC_R = "ENABLE_ASYNC_REDIS_OFFLOAD"
ANON = "ENABLE_ANON_USAGE_GATE"

CLEAN_ENV = (
    QUOTA, RIYADH, CTX, PEPPER_ENV, EXEMPT, CAP_DECOY, METER, ASYNC_R, ANON,
    "ENABLE_USAGE_PATH_OFFLOOP", "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_URL_MODE_V2",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_COMPARISON_ID_ECHO",
    "ENABLE_SEARCH_LOG_TRUTH", "ENABLE_RESULT_STATUS_METADATA",
    "ENABLE_PREVERDICT_DISCONNECT_ABORT", "ENABLE_FULL_STREAM_DEADLINE",
    "ENABLE_RESULT_GATE",  # S81-20 E9: an exported result gate refuses these rows' thin compare bodies
)

OFF = (None, "false", "0", "off", "")  # the five OFF spellings (None = unset)

US_LOGGER = "app.services.usage_service"
REF_LOGGER = "app.services.referral_service"
TAG = "[USAGE-DEVICE]"

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "app"
GOLDEN_PATH = REPO / "tests" / "fixtures" / "s81_s09_flag_off_golden.json"

# uuid-shaped synthetic ids (no digit run longer than two)
UID = "5a09c0de-5a09-4a09-8a09-5a09c0de0a01"
OTHER_UID = "5a09c0de-5a09-4a09-8a09-5a09c0de0a02"
UID2 = "5a09c0de-5a09-4a09-8a09-5a09c0de0a03"
TOKEN = "synthetic-access"
USER = {"id": UID, "access_token": TOKEN}
FP = "a" * 64
FP2 = "b" * 64
PEPPER = "s09" + "-pepper-" + "synthetic"

UTC = timezone.utc
T0 = datetime(2026, 10, 29, 20, 30, 0, tzinfo=UTC)
T1 = datetime(2026, 10, 29, 20, 59, 59, tzinfo=UTC)
T2 = datetime(2026, 10, 29, 21, 0, 0, tzinfo=UTC)
T3 = datetime(2026, 10, 29, 21, 0, 30, tzinfo=UTC)
T4 = datetime(2026, 10, 31, 21, 0, 0, tzinfo=UTC)
T5 = datetime(2026, 12, 31, 21, 30, 0, tzinfo=UTC)
T6 = datetime(2026, 10, 29, 20, 30, 0, 400000, tzinfo=UTC)
PREV_DAY_AT = datetime(2026, 10, 30, 0, 0, 30, tzinfo=UTC)

# The two Lua scripts of spec 2.4, joined with LF and no trailing LF (the S81-04
# RECORD_SCRIPT / RESERVE_SCRIPT precedent).
CONSUME_SCRIPT_LINES = (
    "local a = tonumber(redis.call('GET', KEYS[1]) or '0')",
    "local d = 0",
    "if #KEYS > 1 then",
    "  d = tonumber(redis.call('GET', KEYS[2]) or '0')",
    "  if d >= tonumber(ARGV[2]) then return {2, a, d} end",
    "end",
    "if a >= tonumber(ARGV[1]) then return {1, a, d} end",
    "if #KEYS > 1 then",
    "  d = redis.call('INCR', KEYS[2])",
    "  redis.call('EXPIREAT', KEYS[2], ARGV[3])",
    "end",
    "a = redis.call('INCR', KEYS[1])",
    "redis.call('EXPIREAT', KEYS[1], ARGV[3])",
    "return {0, a, d}",
)
REFUND_SCRIPT_LINES = (
    "local out = {}",
    "for i, k in ipairs(KEYS) do",
    "  local v = tonumber(redis.call('GET', k) or '0')",
    "  if v > 0 then out[i] = redis.call('DECR', k) else out[i] = -1 end",
    "end",
    "return out",
)
EXPECTED_CONSUME_SCRIPT = "\n".join(CONSUME_SCRIPT_LINES)
EXPECTED_REFUND_SCRIPT = "\n".join(REFUND_SCRIPT_LINES)

_REAL_CONSUME = us.consume_comparison_credit
_REAL_STATUS = us.get_usage_status


def _epoch(dt):
    return int(dt.timestamp())


def _D(day="2026-10-29", uid=UID):
    return "usage:daily:%s:%s" % (uid, day)


def _M(month="2026-10", uid=UID):
    return "usage:monthly:%s:%s" % (uid, month)


def _devhex(fp=FP, pepper=PEPPER):
    return hmac.new(pepper.encode("utf-8"), fp.encode("ascii"), hashlib.sha256).hexdigest()


def _DV(day="2026-10-29", fp=FP):
    return "usage:device:%s:%s" % (_devhex(fp), day)


def _dumps(obj):
    """Insertion-order JSON: equality of two dumps asserts values AND key order."""
    return json.dumps(obj, default=str)


def _jr(obj):
    """A JSON round trip (tuples -> lists), so live observations compare with
    the loaded golden."""
    return json.loads(json.dumps(obj, default=str))


# ---------------------------------------------------------------------------
# fixtures and small helpers
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _s09_env(monkeypatch):
    for name in CLEAN_ENV:
        monkeypatch.delenv(name, raising=False)
    rc._reset_pepper_warning()
    yield
    rc._reset_pepper_warning()
    app_main.app.dependency_overrides.pop(get_optional_user, None)
    app_main.app.dependency_overrides.pop(get_current_user, None)


def _need(mod, name):
    obj = getattr(mod, name, None)
    assert obj is not None, "S81-09 not implemented: %s.%s" % (mod.__name__, name)
    return obj


def _set_raw(mp, name, raw):
    if raw is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, raw)


def _full_config(mp, idx=0, *, quota=None, riyadh=None, ctx="true", pepper=True):
    """The B1 configuration. Both flags OFF in rotating spellings (mixed: the
    Riyadh spelling is offset by two) unless named."""
    _set_raw(mp, QUOTA, OFF[idx % len(OFF)] if quota is None else quota)
    _set_raw(mp, RIYADH, OFF[(idx + 2) % len(OFF)] if riyadh is None else riyadh)
    _set_raw(mp, CTX, ctx)
    if pepper:
        mp.setenv(PEPPER_ENV, PEPPER)
    else:
        mp.delenv(PEPPER_ENV, raising=False)
    mp.setenv(CAP_DECOY, "7")
    mp.setenv(EXEMPT, OTHER_UID)
    mp.setenv(METER, "true")


def _quota_live():
    """Guard for quota-ON rows that are otherwise inert at base: the S81-09
    reader must exist and read the flag ON."""
    reader = _need(us, "device_daily_quota_enabled")
    assert reader() is True, "device_daily_quota_enabled() must read ON"


class FakeDT:
    """Stands in for usage_service.datetime (the m18 FakeDatetime pattern)."""

    current = T0

    @classmethod
    def now(cls, tz=None):
        return cls.current


def _freeze(mp, at):
    FakeDT.current = at
    mp.setattr(us, "datetime", FakeDT)


def _tier(mp, tier="free", life=5, bonus=0, reads=None):
    async def _t(uid):
        if reads is not None:
            reads.append(("tier", uid))
        return {"subscription_tier": tier, "lifetime_comparisons_used": life}

    async def _b(uid):
        if reads is not None:
            reads.append(("bonus", uid))
        return bonus

    mp.setattr(us, "_get_user_tier_info", _t)
    mp.setattr(us, "_get_active_referral_bonus", _b)


_UNSET = object()


def _script_kind(script):
    if script == getattr(us, "DEVICE_CONSUME_SCRIPT", _UNSET):
        return "consume"
    if script == getattr(us, "DEVICE_REFUND_SCRIPT", _UNSET):
        return "refund"
    return "unknown"


class FakeRedis:
    """Recording Upstash stand-in (redis-py eval shape). EVAL emulates the two
    module scripts in Python, keyed on the module constants; any other script
    text raises AssertionError inside the fake (a mutated script is a red row)."""

    def __init__(self, store=None, *, eval_raises=None, eval_reply=_UNSET):
        self.store = dict(store or {})
        self.calls = []
        self.expireat = {}
        self.eval_threads = []
        self._eval_raises = eval_raises
        self._eval_reply = eval_reply

    def _int(self, key):
        return int(self.store.get(key, 0))

    def get(self, key):
        self.calls.append(["get", key])
        value = self.store.get(key)
        return None if value is None else str(value)

    def incrby(self, key, n):
        self.calls.append(["incrby", key, n])
        self.store[key] = self._int(key) + n
        return self.store[key]

    def incr(self, key):
        self.calls.append(["incr", key])
        self.store[key] = self._int(key) + 1
        return self.store[key]

    def decrby(self, key, n):
        self.calls.append(["decrby", key, n])
        self.store[key] = self._int(key) - n
        return self.store[key]

    def decr(self, key):
        self.calls.append(["decr", key])
        self.store[key] = self._int(key) - 1
        return self.store[key]

    def expire(self, key, ttl):
        self.calls.append(["expire", key, ttl])
        return True

    def expireat(self, key, when):
        self.calls.append(["expireat", key, when])
        return True

    def eval(self, script, numkeys, *keys_and_args):
        keys = list(keys_and_args[:numkeys])
        args = list(keys_and_args[numkeys:])
        return self._eval(script, keys, args)

    def _eval(self, script, keys, args):
        kind = _script_kind(script)
        self.calls.append(["eval", kind, keys, args])
        self.eval_threads.append(threading.get_ident())
        if kind == "unknown":
            raise AssertionError("FakeRedis: an unknown EVAL script")
        if self._eval_raises is not None:
            raise self._eval_raises
        if self._eval_reply is not _UNSET:
            return self._eval_reply
        if kind == "consume":
            a = self._int(keys[0])
            d = 0
            if len(keys) > 1:
                d = self._int(keys[1])
                if d >= int(args[1]):
                    return [2, a, d]
            if a >= int(args[0]):
                return [1, a, d]
            if len(keys) > 1:
                d = d + 1
                self.store[keys[1]] = d
                self.expireat[keys[1]] = int(args[2])
            a = a + 1
            self.store[keys[0]] = a
            self.expireat[keys[0]] = int(args[2])
            return [0, a, d]
        out = []
        for key in keys:
            value = self._int(key)
            if value > 0:
                self.store[key] = value - 1
                out.append(value - 1)
            else:
                out.append(-1)
        return out


class UpstashShaped(FakeRedis):
    """upstash-redis 1.7.0 shape: eval(script, keys=, args=)."""

    def eval(self, script, keys=None, args=None):  # noqa: D102
        return self._eval(script, list(keys or []), list(args or []))


UpstashShaped.__module__ = "upstash_redis.fake"


class _LogRec(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append((record.name, record.levelname, record.getMessage()))

    def lines(self, name=None):
        return [[lvl, msg] for (n, lvl, msg) in self.records if name is None or n == name]

    def tagged(self):
        return [[lvl, msg] for (n, lvl, msg) in self.records if TAG in msg]


@contextlib.contextmanager
def _logs(*names):
    handler = _LogRec()
    saved = []
    for name in names or ("",):
        lg = logging.getLogger(name)
        saved.append((lg, lg.level))
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        for lg, level in saved:
            lg.removeHandler(handler)
            lg.setLevel(level)


def _arun(fn, headers="ok"):
    """Run fn() on a fresh loop inside a bound request context (the S81-05
    ContextVars, as the middleware binds them). headers: "ok" = the valid FP,
    None = nothing bound, else a list of raw (name, value) pairs."""

    async def main():
        tokens = None
        if headers is not None:
            raw = [(b"x-device-fingerprint", FP.encode("ascii"))] if headers == "ok" else list(headers)
            tokens = rc.bind_from_headers(raw)
        try:
            return await fn()
        finally:
            if tokens is not None:
                rc.reset_request_context(tokens)

    return asyncio.run(main())


def _install_redis(mp, store=None, **kw):
    red = FakeRedis(store, **kw)
    mp.setattr(us, "redis_client", red)
    return red


def _evals(red, kind=None):
    return [c for c in red.calls if c[0] == "eval" and (kind is None or c[1] == kind)]


def _consume(device_fp, uid=UID):
    """consume_comparison_credit(uid, token, device_fp=...) through a signature
    check, so a base without the keyword fails on an AssertionError, never a
    TypeError (the RED rule)."""
    fn = us.consume_comparison_credit
    params = inspect.signature(fn).parameters
    assert "device_fp" in params and params["device_fp"].kind is inspect.Parameter.KEYWORD_ONLY, (
        "S81-09 not implemented: consume_comparison_credit(..., *, device_fp=None)")
    return fn(uid, TOKEN, device_fp=device_fp)


# ---------------------------------------------------------------------------
# route harness (TestClient through the real middleware stack)
# ---------------------------------------------------------------------------
JPEG = b"\xff\xd8" + b"\x00" * 64
OK_RESULT = {
    "success": True,
    "products": [{"brand": "A", "name": "one"}, {"brand": "B", "name": "two"}],
    "metadata": {"total_cost": 0.01},
}
FAIL_RESULT = {"success": False, "code": "TIMEOUT", "error": "s09 probe timeout",
               "elapsed_seconds": 30.0, "total_cost": 0.0}
GENERATE_RETURN = (
    {"winner_index": 1, "recommendation": "The second one.", "key_differences": ["price"]},
    {"prompt_tokens": 1, "completion_tokens": 2},
)


def _done(value=None):
    async def _r():
        return value
    return _r()


class _Svc:
    def __init__(self, result=None, events=None):
        self._result = OK_RESULT if result is None else result
        self._events = events or [("complete", copy.deepcopy(OK_RESULT))]

    async def compare_from_text(self, *_a, **_kw):
        return copy.deepcopy(self._result)

    async def compare_from_text_streaming(self, *_a, **_kw):
        for event in self._events:
            yield event


class _Safety:
    async def moderate_vision_output(self, _extracted):
        return content_safety_service.SafetyResult(allowed=True)


def _vision(n):
    return {"products": [{"brand": "B%d" % i, "name": "N%d" % i} for i in range(n)], "cost": 0.003}


def _stub_routes(mp, *, result=None, events=None, vision=None, vision_raises=False,
                 url_ok=True, lifetime=None):
    """Stub every leaf below the five consume sites (no Supabase, no OpenAI, no
    Serper, no network); the usage gate itself stays REAL."""

    async def _prefs(_uid):
        return {"success": False}

    mp.setattr(text_routes, "get_user_preferences", _prefs)
    svc = _Svc(result, events)
    mp.setattr(text_routes, "get_comparison_service", lambda: svc)

    def _noop(*_a, **_kw):
        return _done()

    def _lifetime(user_id, access_token="", *_a, **_kw):
        if lifetime is not None:
            lifetime.append(user_id)
        return _done()

    for mod in (text_routes, url_routes, image_routes):
        mp.setattr(mod, "log_search", _noop, raising=False)
        mp.setattr(mod, "save_comparison_and_track_cohort", _noop, raising=False)
        mp.setattr(mod, "record_lifetime_comparison", _lifetime, raising=False)
    mp.setattr(feedback_service, "save_comparison_and_track_cohort", _noop, raising=False)

    async def _extract(url):
        if not url_ok:
            return {"success": False, "error": "s09 probe: extraction refused"}
        tag = url.rsplit("/", 1)[-1]
        return {"success": True, "product": {
            "brand": "Probe", "name": tag, "category": "electronics",
            "search_query": "Probe %s" % tag, "price": {"amount": 1.0, "currency": "BHD"}}}

    mp.setattr(url_extraction_service, "extract_from_url", _extract)

    async def _allow(_url):
        return True

    mp.setattr(url_routes, "_validate_url_offloop_or_sync", _allow)

    async def _generate(*_a, **_kw):
        return GENERATE_RETURN

    mp.setattr(extraction_service, "generate_comparison", _generate)

    async def _identify(_images):
        if vision_raises:
            raise RuntimeError("s09 probe: vision unavailable")
        return _vision(2) if vision is None else vision

    mp.setattr(image_routes, "identify_products", _identify)
    mp.setattr(content_safety_service, "get_content_safety_service", lambda: _Safety())
    from app.services import audit_service
    mp.setattr(audit_service, "log_content_blocked", lambda **_kw: _done())

    class _CamService:
        async def compare_from_text(self, *_a, **_kw):
            return copy.deepcopy(OK_RESULT)

    mp.setattr(image_routes, "StructuredComparisonService", _CamService)


@contextlib.contextmanager
def _as_user(user):
    app_main.app.dependency_overrides[get_optional_user] = lambda: user
    app_main.app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        app_main.app.dependency_overrides.pop(get_optional_user, None)
        app_main.app.dependency_overrides.pop(get_current_user, None)


def _client():
    return TestClient(app_main.app, raise_server_exceptions=False)


SITES = ("text_post", "text_get", "text_stream", "url_post", "url_get", "image")
_Q = "Alpha One vs Beta Two"
_U1 = "https://example.test/alpha"
_U2 = "https://example.test/beta"


def _req(client, site, fp=FP):
    headers = {"X-Device-Fingerprint": fp} if fp else {}
    if site == "text_post":
        return client.post("/api/v1/text/compare", json={"query": _Q}, headers=headers)
    if site == "text_get":
        return client.get("/api/v1/text/compare", params={"q": _Q}, headers=headers)
    if site == "text_stream":
        return client.get("/api/v1/text/compare/stream", params={"q": _Q}, headers=headers)
    if site == "url_post":
        return client.post("/api/v1/url/compare", json={"url1": _U1, "url2": _U2}, headers=headers)
    if site == "url_get":
        return client.get("/api/v1/url/compare", params={"url1": _U1, "url2": _U2}, headers=headers)
    if site == "image":
        files = [("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)]
        return client.post("/api/v1/image/identify", files=files, headers=headers)
    raise AssertionError("unknown site %s" % site)


def _norm_rid(resp):
    text = resp.text
    try:
        rid = resp.json().get("request_id")
    except Exception:  # noqa: BLE001 - a non-JSON body keeps its text
        rid = None
    if isinstance(rid, str) and rid:
        text = text.replace(rid, "<rid>")
    return text


class _ConsumeRec:
    """Records every consume call (positional args and kwargs) and delegates to
    the real usage_service.consume_comparison_credit."""

    def __init__(self):
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((list(args), dict(kwargs)))
        return await _REAL_CONSUME(*args, **kwargs)


def _install_consume_rec(mp):
    rec = _ConsumeRec()
    for mod in (us, text_routes, url_routes, image_routes):
        mp.setattr(mod, "consume_comparison_credit", rec, raising=False)
    return rec


def _status_route(fp=FP):
    headers = {"X-Device-Fingerprint": fp} if fp else {}
    with _as_user(USER):
        return _client().get("/api/v1/usage/status", headers=headers)


# ---------------------------------------------------------------------------
# the golden observations (shared by the recorder and the PIN rows)
# ---------------------------------------------------------------------------
UNIT_SCENARIOS = {
    "consume_free_lifetime": dict(kind="consume", store={}, tier="free", life=0),
    "consume_free_paid": dict(kind="consume", store={}, tier="free", life=5),
    "consume_free_daily_limit": dict(kind="consume", store={"D": 3, "M": 3}, tier="free", life=5),
    "consume_free_monthly_limit": dict(kind="consume", store={"D": 0, "M": 10}, tier="free", life=5),
    "consume_premium": dict(kind="consume", store={}, tier="premium", life=100, bonus=4),
    "consume_no_redis": dict(kind="consume", store=None, tier="free", life=5),
    "refund_nokeys": dict(kind="refund", store={"D": 1, "M": 1}, tier="free", life=5),
    "refund_nokeys_prevday": dict(kind="refund", store={"D": 1, "M": 1}, tier="free", life=5,
                                  at=PREV_DAY_AT),
    "refund_keys": dict(kind="refund_keys", store={"D": 1, "M": 1}, tier="free", life=5),
    "status_free_lifetime": dict(kind="status", store={"D": 3, "M": 9}, tier="free", life=1),
    "status_free_paid": dict(kind="status", store={"D": 2, "M": 7}, tier="free", life=5),
    "status_premium": dict(kind="status", store={"D": 5, "M": 20}, tier="premium", life=100, bonus=4),
}
CONSUME_NAMES = sorted(n for n, s in UNIT_SCENARIOS.items() if s["kind"] == "consume")
REFUND_NAMES = sorted(n for n, s in UNIT_SCENARIOS.items() if s["kind"].startswith("refund"))
STATUS_NAMES = sorted(n for n, s in UNIT_SCENARIOS.items() if s["kind"] == "status")


def _resolve_store(store):
    if store is None:
        return None
    return {{"D": _D(), "M": _M()}.get(k, k): v for k, v in store.items()}


def _observe_unit(mp, name, idx=0, *, quota=None, riyadh=None, at=None, red=None, headers="ok"):
    sc = UNIT_SCENARIOS[name]
    _full_config(mp, idx, quota=quota, riyadh=riyadh)
    _freeze(mp, at or sc.get("at", T0))
    _tier(mp, sc["tier"], sc["life"], sc.get("bonus", 0))
    store = _resolve_store(sc["store"])
    if red is None:
        red = None if store is None else FakeRedis(store)
    elif store is not None:
        red.store.update(store)
    mp.setattr(us, "redis_client", red)
    kind = sc["kind"]

    async def call():
        if kind == "consume":
            return await us.consume_comparison_credit(UID, TOKEN)
        if kind == "refund":
            return await us.refund_comparison_credit(UID)
        if kind == "refund_keys":
            return await us.refund_comparison_credit(UID, {"daily": _D(), "monthly": _M()})
        return await us.get_usage_status(UID, TOKEN)

    with _logs(US_LOGGER) as lg:
        res = _arun(call, headers=headers)
    return _jr({
        "calls": red.calls if red is not None else [],
        "result": None if res is None else _dumps(res),
        "logs": lg.lines(US_LOGGER),
    })


def _observe_route_status(mp, name, idx=0, *, quota=None, riyadh=None):
    sc = UNIT_SCENARIOS[name]
    _full_config(mp, idx, quota=quota, riyadh=riyadh)
    _freeze(mp, T0)
    _tier(mp, sc["tier"], sc["life"], sc.get("bonus", 0))
    red = _install_redis(mp, _resolve_store(sc["store"]))
    resp = _status_route()
    return _jr({"status": resp.status_code, "body": resp.text, "calls": red.calls})


def _observe_route_429(mp, site, idx=0, *, quota=None, riyadh=None):
    _full_config(mp, idx, quota=quota, riyadh=riyadh)
    _freeze(mp, T0)
    _tier(mp, "free", 5)
    red = _install_redis(mp, {_D(): 3, _M(): 3})
    _stub_routes(mp)
    with _as_user(USER):
        resp = _req(_client(), site)
    return _jr({"status": resp.status_code, "body": _norm_rid(resp),
                "retry_after": resp.headers.get("retry-after"), "calls": red.calls})


HANDLER_DETAIL = {
    "error": "Comparison limit reached (device_daily_limit)",
    "code": "USAGE_LIMIT",
    "resets_at": "2026-10-30T00:00:00+03:00",
    "scope": "device_daily",
    "retry_after": 60,
}


def _mini_app(detail, status=429):
    mini = FastAPI()
    mini.add_exception_handler(HTTPException, eh.http_exception_handler)

    @mini.get("/probe")
    async def _probe():
        raise HTTPException(status_code=status, detail=detail)

    return mini


def _observe_handler(mp, idx=0, *, quota=None, detail=None):
    _full_config(mp, idx, quota=quota)
    resp = TestClient(_mini_app(HANDLER_DETAIL if detail is None else detail)).get("/probe")
    return _jr({"status": resp.status_code, "body": resp.text,
                "retry_after": resp.headers.get("retry-after")})


def _observe_anon_image(mp, idx=0, *, quota=None):
    _full_config(mp, idx, quota=quota)
    mp.setenv(ANON, "true")
    _freeze(mp, T0)
    anon = "anon:%s" % FP2
    red = _install_redis(mp, {_D(uid=anon): 3, _M(uid=anon): 3})
    _stub_routes(mp)
    with _as_user(None):
        resp = _req(_client(), "image", fp=FP2)
    return _jr({"status": resp.status_code, "body": _norm_rid(resp),
                "retry_after": resp.headers.get("retry-after"), "calls": red.calls})


def _observe_key_helpers(mp, idx=0, *, riyadh=None):
    _full_config(mp, idx, riyadh=riyadh)
    out = {}
    for at in ("2026-10-29T20:59:59+00:00", "2026-10-29T21:00:00+00:00", "2026-10-31T23:30:00+00:00"):
        _freeze(mp, datetime.fromisoformat(at))
        out[at] = [us._daily_key("u"), us._previous_daily_key("u"),
                   us._monthly_key("u"), us._previous_monthly_key("u")]
    return _jr(out)


# --- referral (R-S09-2) -----------------------------------------------------
REF_UID = UID
INVITEE_UID = UID2
CMP_ID = "cmp-s09-synthetic"
INVITE = {"id": "inv-s09-1", "referrer_user_id": REF_UID, "redeemed_by_user_id": INVITEE_UID,
          "redeemed_at": None, "invitee_first_comparison_id": None,
          "device_fingerprint_hash": "dev-s09-synthetic"}
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def _norm_ts(obj):
    if isinstance(obj, dict):
        return {k: _norm_ts(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_norm_ts(v) for v in obj]
    if isinstance(obj, str) and _TS.match(obj):
        return "<ts>"
    return obj


class _RefQuery:
    def __init__(self, client, table):
        self._client = client
        self._table = table
        self._chain = []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self._chain.append([name, list(args), dict(kwargs)])
            return self
        return method

    def execute(self):
        self._client.ops.append([self._table] + self._chain)
        return SimpleNamespace(data=self._client.respond(self._table, self._chain), count=None)


class _RefClient:
    def __init__(self):
        self.ops = []

    def table(self, name):
        return _RefQuery(self, name)

    @staticmethod
    def respond(table, chain):
        verbs = [c[0] for c in chain]
        if "insert" in verbs or "update" in verbs:
            if table == "referral_invites" and "insert" in verbs:
                return [{"id": INVITE["id"]}]
            return [{}]
        selected = " ".join(str(a) for c in chain if c[0] == "select" for a in c[1])
        if table == "comparisons":
            return {"id": CMP_ID, "user_id": REF_UID, "share_token": "tok" + "-s09-synthetic"}
        if table == "users":
            if "referral_code" in selected:
                return {"referral_code": "QRSYN0"}
            if "referral_bonus_comparisons_this_month" in selected:
                return {"referral_bonus_comparisons_this_month": 2}
            if "lifetime_invites_consumed" in selected:
                return {"lifetime_invites_consumed": 1}
        return {}


class _PassAbuse:
    def evaluate_invite(self, *_a, **_kw):
        return {"passed": True, "flagged_reason": None}


def _observe_referral(mp, which, idx=0, *, quota=None):
    _full_config(mp, idx, quota=quota)
    client = _RefClient()
    mp.setattr(rsvc, "get_admin_supabase_client", lambda: client)
    pushes = []

    async def _push(**kwargs):
        pushes.append(dict(kwargs))

    from app.services import push_service
    mp.setattr(push_service, "send_loop2_push", _push)
    svc = rsvc.ReferralService()
    result = None
    with _logs(REF_LOGGER) as lg:
        if which == "create_invite":
            res = asyncio.run(svc.create_invite(
                referrer_user_id=REF_UID, comparison_id=CMP_ID, share_target="copy"))
            result = _dumps(res)
        else:
            async def _r(value):
                return value

            mp.setattr(svc, "_find_unredeemed_invite_for_invitee", lambda _u: _r(dict(INVITE)))
            mp.setattr(svc, "_count_user_comparisons", lambda _u: _r(1))
            mp.setattr(svc, "_load_invitee", lambda _u: _r(
                {"id": INVITEE_UID, "email": "", "display_name": "Synthetic"}))
            mp.setattr(svc, "_referrer_device_lifetime_count", lambda _u: _r(0))
            mp.setattr(svc, "_get_referrer_subscription_tier", lambda _u: _r("free"))
            mp.setattr(rsvc, "AbuseDetectionService", _PassAbuse)
            asyncio.run(svc.try_trigger_loop2(INVITEE_UID, CMP_ID))
    return _jr({"ops": _norm_ts(client.ops), "pushes": pushes, "result": result,
                "logs": lg.lines(REF_LOGGER)})


def _record_golden(mp):
    """Every flag-OFF observation of the PIN rows, under the full configuration
    (spelling 0 = both flags unset). Run AT BASE to write the committed fixture."""
    out = {}
    for name in sorted(UNIT_SCENARIOS):
        out["unit_" + name] = _observe_unit(mp, name)
    for name in STATUS_NAMES:
        out["route_" + name] = _observe_route_status(mp, name)
    for site in SITES:
        out["route_429_" + site] = _observe_route_429(mp, site)
    out["handler_429_usage_limit_extras"] = _observe_handler(mp)
    out["anon_429_image"] = _observe_anon_image(mp)
    out["key_helpers"] = _observe_key_helpers(mp)
    out["referral_create_invite"] = _observe_referral(mp, "create_invite")
    out["referral_loop2"] = _observe_referral(mp, "loop2")
    return {k: out[k] for k in sorted(out)}


def _golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# the S81-08 client readers (sc-s81-s08 HEAD bcf75f84), hand-ported (R-S09-1)
# ---------------------------------------------------------------------------
def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _port_open_remaining(status):
    rem = status["remaining"]
    lf = rem.get("lifetime_free")
    if status.get("tier") != "free" or not _is_num(lf) or lf <= 0:
        return min(rem["daily"], rem["monthly"])
    used = status.get("used") or {}
    limits = status.get("limits") or {}
    try:
        headroom = min(limits["daily"] - used["daily"], limits["monthly"] - used["monthly"])
    except (KeyError, TypeError):
        headroom = None
    if _is_num(headroom):
        return lf + max(0, headroom - lf)
    return min(rem["daily"], rem["monthly"], lf)


def _port_state_from_status(status):
    """PaywallScreen.stateFromStatus."""
    rem = status.get("remaining") if isinstance(status, dict) else None
    if not status or not rem or not _is_num(rem.get("daily")) or not _is_num(rem.get("monthly")):
        return None
    if rem["monthly"] == 0:
        return {"kind": "monthly", "used": (status.get("used") or {}).get("monthly"),
                "limit": (status.get("limits") or {}).get("monthly")}
    if rem["daily"] == 0:
        return {"kind": "daily", "used": (status.get("used") or {}).get("daily"),
                "limit": (status.get("limits") or {}).get("daily")}
    return {"kind": "open", "remaining": _port_open_remaining(status)}


def _port_counter(status, used, session=0):
    """useComparisonCounter: canCompare and the pill (used/total)."""
    free_limit = 3
    local_used = used + session
    limits = status.get("limits") or {}
    lifetime_free = limits.get("lifetime_free")
    lifetime_free = free_limit if lifetime_free is None else lifetime_free
    is_premium = status.get("tier") == "premium"
    remaining = status.get("remaining")
    has_axes = isinstance(remaining, dict) and _is_num(remaining.get("daily")) and _is_num(remaining.get("monthly"))
    fetched = (status.get("used") or {}).get("lifetime")
    consumed = max(0, local_used - fetched) if _is_num(fetched) else 0
    allows = has_axes and (
        ((remaining.get("lifetime_free") if remaining.get("lifetime_free") is not None else 0) - consumed > 0)
        or (remaining["daily"] - consumed > 0 and remaining["monthly"] - consumed > 0)
    )
    can_compare = is_premium or (allows if has_axes else local_used < free_limit)
    total = free_limit if is_premium else lifetime_free
    scope = status.get("counted_scope")
    axis = remaining.get(scope) if (scope in ("daily", "device_daily") and isinstance(remaining, dict)) else None
    pill_used, pill_total = local_used, total
    if _is_num(axis):
        cap = limits.get("daily")
        pill_total = cap if _is_num(cap) else free_limit
        pill_used = max(0, pill_total - max(0, axis - consumed))
    return {"canCompare": bool(can_compare), "pill": "%s/%s" % (pill_used, pill_total)}


# ===========================================================================
# RED rows (fail at base on an AssertionError)
# ===========================================================================
_TRUTH = [(None, False), ("", False), ("false", False), ("0", False), ("no", False),
          ("off", False), ("garbage", False), (" FALSE ", False), ("true", True),
          ("1", True), ("yes", True), ("on", True), (" TRUE ", True)]


def test_r01_flag_readers_truth_table(monkeypatch):
    """RED: usage_service.device_daily_quota_enabled / riyadh_reset_enabled and
    error_handler._device_quota_keys_enabled (the same name, a local one-liner)
    follow the house idiom over 13 spellings, re-read per call."""
    readers = [(QUOTA, _need(us, "device_daily_quota_enabled")),
               (RIYADH, _need(us, "riyadh_reset_enabled")),
               (QUOTA, _need(eh, "_device_quota_keys_enabled"))]
    for name, reader in readers:
        for raw, want in _TRUTH:
            _set_raw(monkeypatch, name, raw)
            assert reader() is want, (name, raw)
        monkeypatch.setenv(name, "true")
        assert reader() is True
        monkeypatch.setenv(name, "off")
        assert reader() is False, "re-read per call"


def test_r02_device_daily_cap_is_a_constant(monkeypatch):
    """RED (R-S09-6): DEVICE_DAILY_CAP = 3 is a module constant (an int, not a
    bool) and no env knob moves it: with DEVICE_DAILY_QUOTA_CAP=1 a device at 1
    used still debits (cap 3)."""
    cap = _need(us, "DEVICE_DAILY_CAP")
    assert type(cap) is int and cap == 3, cap
    _full_config(monkeypatch, quota="true")
    monkeypatch.setenv(CAP_DECOY, "1")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_DV(): 1})
    res = _arun(lambda: _consume(FP))
    assert res["allowed"] is True and res.get("consumed") is True, res
    assert [c[3][:2] for c in _evals(red, "consume")] == [["3", "3"]], red.calls


def test_r03_exempt_list_parse(monkeypatch):
    """RED (R-S09-4): DEVICE_QUOTA_EXEMPT_USER_IDS splits on commas and
    whitespace, keeps canonical uuid tokens (case-insensitive), ignores garbage,
    at most the first 50 valid tokens; unset / blank = nobody."""
    fn = _need(us, "_device_quota_exempt")
    monkeypatch.setenv(EXEMPT, "%s, garbage ,,\t%s" % (UID.upper(), OTHER_UID))
    assert fn(UID) and fn(OTHER_UID) and fn(UID.upper())
    assert not fn(UID2)
    assert not fn("garbage")
    monkeypatch.setenv(EXEMPT, "   ")
    assert not fn(UID)
    monkeypatch.delenv(EXEMPT)
    assert not fn(UID)
    tokens = ["5a09c0de-5a09-4a09-8a09-%012x" % (0xabcde0 + i) for i in range(50)]
    monkeypatch.setenv(EXEMPT, ",".join(tokens + [UID2]))
    assert fn(tokens[0]) and fn(tokens[49])
    assert not fn(UID2), "the 51st valid token is ignored"


_WINDOW = [
    (T1, True, "2026-10-29", datetime(2026, 10, 29, 21, 0, tzinfo=UTC)),
    (T2, True, "2026-10-30", datetime(2026, 10, 30, 21, 0, tzinfo=UTC)),
    (T4, True, "2026-11-01", datetime(2026, 11, 1, 21, 0, tzinfo=UTC)),
    (T5, True, "2027-01-01", datetime(2027, 1, 1, 21, 0, tzinfo=UTC)),
    (T1, False, "2026-10-29", datetime(2026, 10, 30, 0, 0, tzinfo=UTC)),
    (T2, False, "2026-10-29", datetime(2026, 10, 30, 0, 0, tzinfo=UTC)),
    (T4, False, "2026-10-31", datetime(2026, 11, 1, 0, 0, tzinfo=UTC)),
    (T5, False, "2026-12-31", datetime(2027, 1, 1, 0, 0, tzinfo=UTC)),
]


@pytest.mark.parametrize("now,on,day,nxt", _WINDOW,
                         ids=["%s-%s" % (w[0].isoformat()[:19], "on" if w[1] else "off") for w in _WINDOW])
def test_r04_usage_window(monkeypatch, now, on, day, nxt):
    """RED: _usage_window(now) -> (the date, the next reset as an aware UTC
    instant strictly after now): Riyadh +03:00 under the flag, UTC otherwise;
    the default now reads usage_service.datetime (FakeDatetime honoured)."""
    fn = _need(us, "_usage_window")
    _set_raw(monkeypatch, RIYADH, "true" if on else None)
    got_day, got_next = fn(now)
    assert got_day.isoformat() == day
    assert got_next == nxt and got_next > now
    _freeze(monkeypatch, now)
    d2, n2 = fn()
    assert d2.isoformat() == day and n2 == nxt


@pytest.mark.parametrize("now,on,want", [
    (T4, True, ["usage:daily:u:2026-11-01", "usage:daily:u:2026-10-31",
                "usage:monthly:u:2026-11", "usage:monthly:u:2026-10"]),
    (T1, True, ["usage:daily:u:2026-10-29", "usage:daily:u:2026-10-28",
                "usage:monthly:u:2026-10", "usage:monthly:u:2026-09"]),
    (T2, True, ["usage:daily:u:2026-10-30", "usage:daily:u:2026-10-29",
                "usage:monthly:u:2026-10", "usage:monthly:u:2026-09"]),
    (T2, False, ["usage:daily:u:2026-10-29", "usage:daily:u:2026-10-28",
                 "usage:monthly:u:2026-10", "usage:monthly:u:2026-09"]),
], ids=["T4-on", "T1-on", "T2-on", "T2-off"])
def test_r05_key_helpers_riyadh(monkeypatch, now, on, want):
    """RED: the four key helpers follow the one date helper (Riyadh under the
    flag; UTC strings byte for byte otherwise)."""
    _need(us, "_usage_window")
    _set_raw(monkeypatch, RIYADH, "true" if on else None)
    _freeze(monkeypatch, now)
    got = [us._daily_key("u"), us._previous_daily_key("u"), us._monthly_key("u"),
           us._previous_monthly_key("u")]
    assert got == want


def test_r06_one_eval_per_consume(monkeypatch):
    """RED: quota ON, free, lifetime 0, header bound, pepper set (the decoy cap
    knob at 7): exactly ONE Redis call, an EVAL of DEVICE_CONSUME_SCRIPT with
    KEYS [account, device] and ARGV ["3", "3", expireat]; no incrby / expire /
    get / decrby; zero [USAGE-DEVICE] records (R-S09-8)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 0)
    red = _install_redis(monkeypatch)
    with _logs(US_LOGGER) as lg:
        res = _arun(lambda: _consume(FP))
    exp = _epoch(datetime(2026, 10, 30, 1, 0, tzinfo=UTC))
    assert red.calls == [["eval", "consume", [_D(), _DV()], ["3", "3", str(exp)]]], red.calls
    assert res["allowed"] is True
    assert lg.tagged() == [], lg.tagged()


@pytest.mark.parametrize("on,when", [(True, datetime(2026, 10, 29, 22, 0, tzinfo=UTC)),
                                     (False, datetime(2026, 10, 30, 1, 0, tzinfo=UTC))],
                         ids=["riyadh_on", "riyadh_off"])
def test_r07_expireat_value(monkeypatch, on, when):
    """RED: EXPIREAT = the next reset + 3600 (T0: 22:00Z Riyadh, 01:00Z UTC)."""
    _full_config(monkeypatch, quota="true", riyadh="true" if on else None)
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch)
    _arun(lambda: _consume(FP))
    evals = _evals(red, "consume")
    assert len(evals) == 1 and evals[0][3][2] == str(_epoch(when)), red.calls
    assert red.expireat == {_D(): _epoch(when), _DV(): _epoch(when)}


@pytest.mark.parametrize("life,acct,dev", [(0, 0, 3), (0, 3, 3)], ids=["fresh_dev3_acct0", "m33_dev3_acct3"])
def test_r08_device_before_lifetime_free(monkeypatch, life, acct, dev):
    """RED: a fresh account (lifetime 0) on a device at the cap is refused with
    reason device_daily_limit / scope device_daily, consumed False, nothing
    written; with BOTH axes exhausted the device is reported (M33, Q15)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", life)
    store = {_D(): acct, _DV(): dev}
    red = _install_redis(monkeypatch, store)
    res = _arun(lambda: _consume(FP))
    assert res["allowed"] is False and res["reason"] == "device_daily_limit", res
    assert res.get("scope") == "device_daily" and res.get("consumed") is False, res
    assert res["remaining"].get("device_daily") == 0, res
    assert red.store == store, "a refusal writes nothing"
    assert [c[0] for c in red.calls] == ["eval"], red.calls


def test_r09_account_daily_refusal(monkeypatch):
    """RED: account at 3, device at 1: reason daily_limit, scope daily,
    remaining.daily 0, remaining.device_daily 2, store unchanged."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    store = {_D(): 3, _DV(): 1}
    red = _install_redis(monkeypatch, store)
    res = _arun(lambda: _consume(FP))
    assert res["allowed"] is False and res["reason"] == "daily_limit" and res.get("scope") == "daily", res
    assert res["remaining"]["daily"] == 0 and res["remaining"].get("device_daily") == 2, res
    assert red.store == store and [c[0] for c in red.calls] == ["eval"]


def test_r10_success_shape(monkeypatch):
    """RED (R-S09-8 / C2d): the code-0 result as a FULL dict (key order
    included): consumed_keys {daily, device_daily} (no monthly), remaining
    {daily, monthly 10, lifetime_free 0, device_daily}; both counters +1; no
    retry_after / resets_at / scope; zero [USAGE-DEVICE] records."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 0)
    red = _install_redis(monkeypatch, {_D(): 0, _DV(): 0})
    with _logs(US_LOGGER) as lg:
        res = _arun(lambda: _consume(FP))
    want = {"allowed": True, "reason": None, "tier": "free", "consumed": True,
            "consumed_keys": {"daily": _D(), "device_daily": _DV()},
            "remaining": {"daily": 2, "monthly": 10, "lifetime_free": 0, "device_daily": 2}}
    assert _dumps(res) == _dumps(want), res
    assert red.store == {_D(): 1, _DV(): 1}
    assert lg.tagged() == []


@pytest.mark.parametrize("now,on,secs,resets", [
    (T0, True, 1800, "2026-10-30T00:00:00+03:00"),
    (T0, False, 12600, "2026-10-30T00:00:00+00:00"),
    (T2, True, 86400, "2026-10-31T00:00:00+03:00"),
    (T6, True, 1800, "2026-10-30T00:00:00+03:00"),
], ids=["T0-on", "T0-off", "T2-on", "T6-on-ceil"])
def test_r11_retry_after_and_resets_at(monkeypatch, now, on, secs, resets):
    """RED: a device refusal carries retry_after = ceil(seconds to the reset)
    (an int, never a bool) and resets_at in the reset zone."""
    _full_config(monkeypatch, quota="true", riyadh="true" if on else None)
    _freeze(monkeypatch, now)
    _tier(monkeypatch, "free", 5)
    day = "2026-10-30" if (on and now >= T2) else "2026-10-29"
    _install_redis(monkeypatch, {_DV(day): 3})
    res = _arun(lambda: _consume(FP))
    assert res["allowed"] is False, res
    ra = res.get("retry_after")
    assert type(ra) is int and ra == secs, res
    assert res.get("resets_at") == resets, res


def _device_capped_route(mp, *, riyadh="true"):
    _full_config(mp, quota="true", riyadh=riyadh)
    _freeze(mp, T0)
    _tier(mp, "free", 5)
    red = _install_redis(mp, {_DV(): 3})
    _stub_routes(mp)
    return red


def test_r12_post_compare_429_on_the_wire(monkeypatch):
    """RED: POST /api/v1/text/compare on a capped device (quota ON, RIYADH ON,
    T0): 429 {success, error, code, request_id, resets_at, scope,
    retry_after_seconds 1800} + Retry-After 1800; the compare never runs."""
    _device_capped_route(monkeypatch)
    ran = []

    class _Never(_Svc):
        async def compare_from_text(self, *_a, **_kw):
            ran.append(1)
            return copy.deepcopy(OK_RESULT)

    monkeypatch.setattr(text_routes, "get_comparison_service", lambda: _Never())
    with _as_user(USER):
        resp = _req(_client(), "text_post")
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert isinstance(body.get("request_id"), str)
    body.pop("request_id")
    assert body == {"success": False, "error": "Comparison limit reached (device_daily_limit)",
                    "code": "USAGE_LIMIT", "resets_at": "2026-10-30T00:00:00+03:00",
                    "scope": "device_daily", "retry_after_seconds": 1800}, body
    assert resp.headers.get("retry-after") == "1800"
    assert ran == []


@pytest.mark.parametrize("site", SITES)
def test_r13_every_consume_site_passes_device_fp(monkeypatch, site):
    """RED: under the quota flag every consume site passes device_fp = the bound
    fingerprint (metering ON for url / image), and its 429 carries resets_at,
    scope and retry_after_seconds."""
    _device_capped_route(monkeypatch)
    rec = _install_consume_rec(monkeypatch)
    with _as_user(USER):
        resp = _req(_client(), site)
    assert [kw.get("device_fp") for _a, kw in rec.calls] == [FP], rec.calls
    assert resp.status_code == 429, resp.text
    body = resp.json()
    assert body.get("scope") == "device_daily" and body.get("resets_at") == "2026-10-30T00:00:00+03:00", body
    assert body.get("retry_after_seconds") == 1800, body


def test_r14_handler_allow_list(monkeypatch):
    """RED: the flag-gated USAGE_LIMIT pass-through: resets_at (a str) and scope
    (in the value set) reach the wire; a bad scope / a non-str resets_at are
    dropped; RATE_LIMITED and NOT_PRODUCT_PAGE 429 details keep the base key set
    (+ retry_after_seconds only)."""
    _full_config(monkeypatch, quota="true")
    body = json.loads(_observe_handler(monkeypatch, quota="true")["body"])
    assert body.get("resets_at") == "2026-10-30T00:00:00+03:00" and body.get("scope") == "device_daily", body
    assert body.get("retry_after_seconds") == 60
    for bad in ({"scope": "weekly"}, {"scope": 7}, {"resets_at": 5}):
        detail = dict(HANDLER_DETAIL, **bad)
        got = json.loads(_observe_handler(monkeypatch, quota="true", detail=detail)["body"])
        for key, value in bad.items():
            assert key not in got, (bad, got)
        assert got.get("retry_after_seconds") == 60
    for code in ("RATE_LIMITED", "NOT_PRODUCT_PAGE"):
        detail = dict(HANDLER_DETAIL, code=code)
        got = json.loads(_observe_handler(monkeypatch, quota="true", detail=detail)["body"])
        assert sorted(got) == ["code", "error", "request_id", "retry_after_seconds", "success"], got


def test_r15_refund_decrements_both_keys_once(monkeypatch):
    """RED (R-S09-3): a quota-path debit is refunded by ONE EVAL of
    DEVICE_REFUND_SCRIPT over [account, device] from the request-scoped stash; a
    refund for ANOTHER user in the same context runs only that user's base
    fallback; a second refund for the same debit makes no Redis call."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})
    marks = {}

    async def flow():
        res = await _consume(FP)
        marks["after_consume"] = len(red.calls)
        await us.refund_comparison_credit(UID2)
        marks["after_other"] = len(red.calls)
        await us.refund_comparison_credit(UID)
        marks["after_refund"] = len(red.calls)
        await us.refund_comparison_credit(UID)
        marks["after_second"] = len(red.calls)
        return res

    res = _arun(flow)
    assert res.get("consumed") is True, res
    other = red.calls[marks["after_consume"]:marks["after_other"]]
    assert all(c[0] != "eval" for c in other), other
    assert not any(_D() in json.dumps(c) or _DV() in json.dumps(c) for c in other), other
    refund = red.calls[marks["after_other"]:marks["after_refund"]]
    assert refund == [["eval", "refund", [_D(), _DV()], []]], refund
    assert red.calls[marks["after_refund"]:marks["after_second"]] == [], "second refund is a no-op"
    assert red.store[_D()] == 1 and red.store[_DV()] == 1


@pytest.mark.parametrize("site", ["text_post", "text_stream", "url_post", "image"])
def test_r16_route_failure_refunds_both(monkeypatch, site):
    """RED: a failed compare (POST text TIMEOUT, stream error event, url
    extraction failure, camera vision exception) refunds BOTH keys exactly once
    after the fire-and-forget drain (no route refund edit: the stash)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})
    _stub_routes(monkeypatch, result=FAIL_RESULT,
                 events=[("error", {"error": "s09 probe", "code": "TIMEOUT"})],
                 vision_raises=True, url_ok=False)
    with _as_user(USER):
        with TestClient(app_main.app, raise_server_exceptions=False) as client:
            resp = _req(client, site)
    assert resp.status_code != 429, resp.text
    assert len(_evals(red, "consume")) == 1, red.calls
    assert len(_evals(red, "refund")) == 1, red.calls
    assert red.store.get(_D()) == 1 and red.store.get(_DV()) == 1, red.store


def test_r17_refund_after_riyadh_midnight_is_exact(monkeypatch):
    """RED: consume at T1 (Riyadh day 10-29), refund at T3 (Riyadh 10-30): the
    10-29 keys are decremented; no 10-30 key is touched or created."""
    _full_config(monkeypatch, quota="true", riyadh="true")
    _freeze(monkeypatch, T1)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})

    async def flow():
        await _consume(FP)
        FakeDT.current = T3
        await us.refund_comparison_credit(UID)

    _arun(flow)
    assert _evals(red, "refund") == [["eval", "refund", [_D(), _DV()], []]], red.calls
    assert red.store == {_D(): 1, _DV(): 1}
    assert "2026-10-30" not in json.dumps(red.calls)


def test_r18_previous_daily_key_is_riyadh_yesterday(monkeypatch):
    """RED: RIYADH ON, quota OFF: a base consume at T1 refunded (no keys) at T3
    reads today 10-30 (0) then Riyadh-yesterday 10-29 and decrements it; a
    UTC-dated key written under RIYADH OFF at 22:00Z is found as
    Riyadh-yesterday after the flip (22:00:30Z)."""
    _full_config(monkeypatch, riyadh="true")
    _freeze(monkeypatch, T1)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch)

    async def flow():
        await us.consume_comparison_credit(UID, TOKEN)
        FakeDT.current = T3
        mark = len(red.calls)
        await us.refund_comparison_credit(UID)
        return mark

    mark = _arun(flow)
    assert red.calls[mark:mark + 3] == [["get", _D("2026-10-30")], ["get", _D("2026-10-29")],
                                       ["decrby", _D("2026-10-29"), 1]], red.calls[mark:]
    # the transition: written under OFF (UTC 10-29 at 22:00Z), refunded under ON
    _set_raw(monkeypatch, RIYADH, None)
    _freeze(monkeypatch, datetime(2026, 10, 29, 22, 0, tzinfo=UTC))
    red2 = _install_redis(monkeypatch)

    async def flow2():
        await us.consume_comparison_credit(UID, TOKEN)
        monkeypatch.setenv(RIYADH, "true")
        FakeDT.current = datetime(2026, 10, 29, 22, 0, 30, tzinfo=UTC)
        mark2 = len(red2.calls)
        await us.refund_comparison_credit(UID)
        return mark2

    mark2 = _arun(flow2)
    assert red2.calls[mark2:mark2 + 3] == [["get", _D("2026-10-30")], ["get", _D("2026-10-29")],
                                         ["decrby", _D("2026-10-29"), 1]], red2.calls[mark2:]


def _quota_status(mp, *, life, acct, dev, fp=FP, riyadh=None, tier="free", bonus=0, reads=None,
                  extra_store=None):
    _full_config(mp, quota="true", riyadh=riyadh)
    _freeze(mp, T0)
    _tier(mp, tier, life, bonus, reads=reads)
    store = {_D(): acct, _DV(): dev}
    store.update(extra_store or {})
    red = _install_redis(mp, store)
    resp = _status_route(fp=fp)
    assert resp.status_code == 200, resp.text
    return resp, red


def test_r19_status_body_device(monkeypatch):
    """RED (R-S09-1 / R-S09-6): quota ON, RIYADH ON, T0, header bound, lifetime
    7, account 1 used, device 2 used: the device axis binds, so remaining.daily
    = 1 and used.daily = 2; limits.device_daily = 3 (additive); the RAW body,
    key order included."""
    resp, _red = _quota_status(monkeypatch, life=7, acct=1, dev=2, riyadh="true")
    want = ('{"tier":"free","used":{"daily":2,"monthly":0,"lifetime":7},'
            '"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3,'
            '"device_daily":3},'
            '"remaining":{"daily":1,"monthly":10,"lifetime_free":0,"device_daily":1},'
            '"resets_at":"2026-10-30T00:00:00+03:00","counted_scope":"device_daily"}')
    assert resp.text == want, resp.text


@pytest.mark.parametrize("acct,dev,fp,scope,daily,used_daily,dev_rem", [
    (1, 2, FP, "device_daily", 1, 2, 1),
    (2, 1, FP, "daily", 1, 2, 2),
    (1, 1, FP, "device_daily", 2, 1, 2),
    (1, 3, None, "daily", 2, 1, None),
], ids=["device_binds", "account_binds", "tie_names_device", "no_header"])
def test_r20_counted_scope(monkeypatch, acct, dev, fp, scope, daily, used_daily, dev_rem):
    """RED (R-S09-1): counted_scope names the binding axis (ties name the
    device); remaining.daily / used.daily are the binding axis; without a device
    key counted_scope is 'daily' and remaining.device_daily is ABSENT."""
    resp, _red = _quota_status(monkeypatch, life=7, acct=acct, dev=dev, fp=fp)
    body = resp.json()
    assert body.get("counted_scope") == scope, body
    assert body["remaining"]["daily"] == daily and body["used"]["daily"] == used_daily, body
    if dev_rem is None:
        assert "device_daily" not in body["remaining"], body
    else:
        assert body["remaining"].get("device_daily") == dev_rem, body


def test_r21_status_reads_on_quota_path(monkeypatch):
    """RED: the free quota-path status reads the tier once and GETs the account
    and device daily counters; no referral_redemptions read, no monthly GET."""
    reads = []
    _resp, red = _quota_status(monkeypatch, life=7, acct=1, dev=1, reads=reads,
                               extra_store={_M(): 4})
    assert reads == [("tier", UID)], reads
    assert sorted(red.calls) == sorted([["get", _D()], ["get", _DV()]]), red.calls


@pytest.mark.parametrize("case,state", [
    ("absent", "absent"), ("malformed", "malformed"), ("no_pepper", "ok"), ("ctx_off", "absent"),
])
def test_r22_no_header_is_account_only_plus_one_metric(monkeypatch, case, state):
    """RED: a missing / malformed / unkeyable header (or the middleware OFF) is
    account-only (ONE EVAL, KEYS [account]) plus exactly ONE INFO
    '[USAGE-DEVICE] account-only header=<state>'; the route answers 200."""
    _full_config(monkeypatch, quota="true", ctx=None if case == "ctx_off" else "true",
                 pepper=case != "no_pepper")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch)
    _stub_routes(monkeypatch)
    fp = {"absent": None, "malformed": "XYZ", "no_pepper": FP, "ctx_off": FP}[case]
    with _logs(US_LOGGER) as lg:
        with _as_user(USER):
            resp = _req(_client(), "text_post", fp=fp)
    assert resp.status_code == 200, resp.text
    exp = _epoch(datetime(2026, 10, 30, 1, 0, tzinfo=UTC))
    assert red.calls == [["eval", "consume", [_D()], ["3", "3", str(exp)]]], red.calls
    assert lg.tagged() == [["INFO", "[USAGE-DEVICE] account-only header=%s" % state]], lg.records


def test_r23_no_secret_in_any_log(monkeypatch):
    """RED: over the R06 / R15 / R22 / R26 flows no log line carries the
    fingerprint, the device key, either Redis key, the user id or the pepper
    (the flows must actually take the quota path: an EVAL was issued)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})
    with _logs() as lg:
        async def flow():
            await _consume(FP)
            await us.refund_comparison_credit(UID)
            await _consume(None)

        _arun(flow, headers=[])
        red._eval_raises = ConnectionError("s09 probe outage")
        _arun(lambda: _consume(FP))
    assert len(_evals(red)) >= 3, red.calls
    text = "\n".join(m for (_n, _l, m) in lg.records)
    for secret in (FP, _devhex(), _D(), _DV(), UID, PEPPER):
        assert secret not in text, "a log line carries a secret value"


def test_r24_allow_list_runs_the_base_path(monkeypatch):
    """RED guard + PIN body (R-S09-4): quota ON and the uid in
    DEVICE_QUOTA_EXEMPT_USER_IDS (upper-cased): the consume Redis calls and
    result equal the golden consume_free_paid, the status equals the golden
    free body, no EVAL."""
    golden = _golden()
    _full_config(monkeypatch, quota="true")
    monkeypatch.setenv(EXEMPT, "%s %s" % (OTHER_UID, UID.upper()))
    _quota_live()
    assert _need(us, "_device_quota_exempt")(UID)
    obs = _observe_unit_keep_env(monkeypatch, "consume_free_paid")
    assert obs == golden["unit_consume_free_paid"], obs
    st = _observe_route_status_keep_env(monkeypatch, "status_free_paid")
    assert st == golden["route_status_free_paid"], st


def _observe_unit_keep_env(mp, name):
    """_observe_unit without re-applying the configuration (the caller set it)."""
    sc = UNIT_SCENARIOS[name]
    _freeze(mp, sc.get("at", T0))
    _tier(mp, sc["tier"], sc["life"], sc.get("bonus", 0))
    red = FakeRedis(_resolve_store(sc["store"]) or {})
    mp.setattr(us, "redis_client", red)

    async def call():
        if sc["kind"] == "consume":
            return await _consume(FP)
        if sc["kind"] == "refund":
            return await us.refund_comparison_credit(UID)
        return await us.get_usage_status(UID, TOKEN)

    with _logs(US_LOGGER) as lg:
        res = _arun(call)
    return _jr({"calls": red.calls, "result": None if res is None else _dumps(res),
                "logs": lg.lines(US_LOGGER)})


def _observe_route_status_keep_env(mp, name, extra_store=None):
    sc = UNIT_SCENARIOS[name]
    _freeze(mp, T0)
    _tier(mp, sc["tier"], sc["life"], sc.get("bonus", 0))
    store = _resolve_store(sc["store"])
    store.update(extra_store or {})
    red = _install_redis(mp, store)
    resp = _status_route()
    return _jr({"status": resp.status_code, "body": resp.text, "calls": red.calls})


def test_r25_premium_is_not_device_capped(monkeypatch):
    """RED guard + PIN body (Q1 / R-S09-4): quota ON, premium, the device counter
    at 99: consume calls and result equal the golden consume_premium; a refund
    after it runs the base fallback (no EVAL: the device refund block is driven
    only by a quota-path debit); the status equals the golden premium body."""
    golden = _golden()
    _full_config(monkeypatch, quota="true")
    _quota_live()
    sc = UNIT_SCENARIOS["consume_premium"]
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, sc["tier"], sc["life"], sc["bonus"])
    red = _install_redis(monkeypatch, {_DV(): 99})
    marks = {}

    async def flow():
        res = await _consume(FP)
        marks["c"] = len(red.calls)
        await us.refund_comparison_credit(UID)
        return res

    with _logs(US_LOGGER) as lg:
        res = _arun(flow)
    assert _jr(red.calls[:marks["c"]]) == golden["unit_consume_premium"]["calls"]
    assert _dumps(res) == golden["unit_consume_premium"]["result"]
    assert _jr(red.calls[marks["c"]:]) == golden["unit_refund_nokeys"]["calls"], red.calls
    assert lg.lines(US_LOGGER) == []
    assert red.store[_DV()] == 99
    st = _observe_route_status_keep_env(monkeypatch, "status_premium", extra_store={_DV(): 99})
    assert st["body"] == golden["route_status_premium"]["body"], st


def test_r26_fail_open_with_outage_metric(monkeypatch):
    """RED: the EVAL raises: allowed True, consumed False, no consumed_keys,
    exactly ONE WARNING '[USAGE-DEVICE] consume fail-open type=ConnectionError';
    a later refund makes no EVAL and no write (deviation note: the spec's 'no
    Redis call' conflicts with 2.6, whose no-stash path is the base fallback,
    GETs only)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, eval_raises=ConnectionError("s09 probe outage"))
    marks = {}

    async def flow():
        res = await _consume(FP)
        marks["c"] = len(red.calls)
        await us.refund_comparison_credit(UID)
        return res

    with _logs(US_LOGGER) as lg:
        res = _arun(flow)
    assert res["allowed"] is True and res.get("consumed") is False and "consumed_keys" not in res, res
    assert lg.tagged() == [["WARNING", "[USAGE-DEVICE] consume fail-open type=ConnectionError"]], lg.records
    later = red.calls[marks["c"]:]
    assert all(c[0] == "get" for c in later), later


@pytest.mark.parametrize("reply", ["OK", [0, 1], None, [5, 1, 1], [True, 1, 1]],
                         ids=["str", "short", "none", "code5", "bool"])
def test_r27_bad_reply_fails_open(monkeypatch, reply):
    """RED (C19): a reply that is not a 3-int list with a code in {0, 1, 2}
    fails open with type=BadReply (never read as a debit)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, eval_reply=reply)
    with _logs(US_LOGGER) as lg:
        res = _arun(lambda: _consume(FP))
    assert len(_evals(red, "consume")) == 1, red.calls
    assert res["allowed"] is True and res.get("consumed") is False and "consumed_keys" not in res, res
    assert lg.tagged() == [["WARNING", "[USAGE-DEVICE] consume fail-open type=BadReply"]], lg.records


def test_r28_upstash_client_shape(monkeypatch):
    """RED (Q4): an upstash-redis shaped client receives eval(script, keys=,
    args=) (the llm_spend_breaker._eval reuse)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = UpstashShaped()
    monkeypatch.setattr(us, "redis_client", red)
    res = _arun(lambda: _consume(FP))
    exp = _epoch(datetime(2026, 10, 30, 1, 0, tzinfo=UTC))
    assert red.calls == [["eval", "consume", [_D(), _DV()], ["3", "3", str(exp)]]], red.calls
    assert res.get("consumed") is True


@pytest.mark.parametrize("offload", [True, False], ids=["offload_on", "offload_off"])
def test_r29_offload_dispatch(monkeypatch, offload):
    """RED: ENABLE_ASYNC_REDIS_OFFLOAD ON runs the consume and refund EVALs on a
    worker thread; OFF on the loop thread."""
    _full_config(monkeypatch, quota="true")
    _set_raw(monkeypatch, ASYNC_R, "true" if offload else None)
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch)
    loop_thread = {}

    async def flow():
        loop_thread["id"] = threading.get_ident()
        await _consume(FP)
        await us.refund_comparison_credit(UID)

    _arun(flow)
    assert [c[1] for c in _evals(red)] == ["consume", "refund"], red.calls
    if offload:
        assert all(t != loop_thread["id"] for t in red.eval_threads), red.eval_threads
    else:
        assert all(t == loop_thread["id"] for t in red.eval_threads), red.eval_threads


@pytest.mark.parametrize("now", [T0, T1, T2, T3, T4, T5, T6], ids=["T0", "T1", "T2", "T3", "T4", "T5", "T6"])
def test_r30_riyadh_drift_pin(monkeypatch, now):
    """RED: under ENABLE_RIYADH_RESET the usage day and the next reset + 3600
    equal llm_spend_breaker.riyadh_day(now) (the two Riyadh days never drift)."""
    fn = _need(us, "_usage_window")
    monkeypatch.setenv(RIYADH, "true")
    day, nxt = fn(now)
    want_day, want_exp = lsb.riyadh_day(now)
    assert day.isoformat() == want_day and int(nxt.timestamp()) + 3600 == want_exp


def test_r31_status_route_passes_device_fp(monkeypatch):
    """RED: under the quota flag GET /usage/status calls
    get_device_usage_status with device_fp = the bound fingerprint."""
    seen = []
    real = getattr(us, "get_device_usage_status", None)

    async def rec(*args, **kwargs):
        seen.append(kwargs.get("device_fp"))
        if real is None:
            return {}
        return await real(*args, **kwargs)

    for mod in (us, usage_routes):
        monkeypatch.setattr(mod, "get_device_usage_status", rec, raising=False)
    _quota_status(monkeypatch, life=7, acct=1, dev=1)
    assert seen == [FP], seen


def test_r32_device_key_is_the_hmac(monkeypatch):
    """RED: the device key is 'usage:device:' + HMAC-SHA256(pepper, fp) hex +
    ':' + day; the raw fingerprint appears in no Redis key or argument."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch)
    _arun(lambda: _consume(FP))
    evals = _evals(red, "consume")
    assert evals and evals[0][2][1] == "usage:device:" + _devhex() + ":2026-10-29", red.calls
    assert FP not in json.dumps(red.calls)


def test_r33_retired_monthly_and_bonus(monkeypatch):
    """RED: quota ON, the monthly counter at 10 (pre-flip), a referral bonus of
    5, account 0, device 0: allowed; no monthly key touched; the status reports
    limits.monthly_bonus 0 and remaining.monthly 10."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 7, 5)
    red = _install_redis(monkeypatch, {_M(): 10, _D(): 0, _DV(): 0})
    res = _arun(lambda: _consume(FP))
    assert res["allowed"] is True, res
    assert _M() not in json.dumps(red.calls), red.calls
    resp, _red = _quota_status(monkeypatch, life=7, acct=1, dev=1, bonus=5, extra_store={_M(): 10})
    body = resp.json()
    assert body["limits"]["monthly_bonus"] == 0 and body["remaining"]["monthly"] == 10, body


def test_r34_camera_consume_and_refund(monkeypatch):
    """RED: metering ON + quota ON: the camera consume carries device_fp; a
    zero-product vision exit refunds both keys exactly once (the closure latch
    and the stash latch)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})
    _stub_routes(monkeypatch, vision=_vision(0))
    rec = _install_consume_rec(monkeypatch)
    with _as_user(USER):
        with TestClient(app_main.app, raise_server_exceptions=False) as client:
            resp = _req(client, "image")
    assert resp.status_code == 200, resp.text
    assert [kw.get("device_fp") for _a, kw in rec.calls] == [FP], rec.calls
    assert len(_evals(red, "refund")) == 1, red.calls
    assert red.store.get(_D()) == 1 and red.store.get(_DV()) == 1, red.store


def test_r35_scripts_are_pinned_literals():
    """RED: the two module constants equal the spec 2.4 texts byte for byte
    (LF-joined, no trailing LF)."""
    assert _need(us, "DEVICE_CONSUME_SCRIPT") == EXPECTED_CONSUME_SCRIPT
    assert _need(us, "DEVICE_REFUND_SCRIPT") == EXPECTED_REFUND_SCRIPT


def test_r35b_script_shape_static():
    """RED (R-S09-10, no Lua runtime): the consume script reads KEYS[1..2] and
    ARGV[1..3] only, checks and debits the device BEFORE the account, sets
    EXPIREAT ARGV[3] on both keys and never a plain EXPIRE / SET / DEL; the
    refund script takes no ARGV and DECRs only behind a > 0 floor."""
    consume = _need(us, "DEVICE_CONSUME_SCRIPT")
    refund = _need(us, "DEVICE_REFUND_SCRIPT")
    assert set(re.findall(r"KEYS\[(\d+)\]", consume)) == {"1", "2"}
    assert set(re.findall(r"ARGV\[(\d+)\]", consume)) == {"1", "2", "3"}
    assert re.findall(r"'EXPIREAT', (KEYS\[\d\]), (ARGV\[\d\])", consume) == [
        ("KEYS[2]", "ARGV[3]"), ("KEYS[1]", "ARGV[3]")]
    assert not re.search(r"'(EXPIRE|SET|DEL|INCRBY|DECRBY)'", consume)
    assert _pos(consume, "return {2,") < _pos(consume, "return {1,") < _pos(consume, "return {0,")
    assert _pos(consume, "'INCR', KEYS[2]") < _pos(consume, "'INCR', KEYS[1]")
    assert "ARGV" not in refund
    assert _pos(refund, "if v > 0 then") < _pos(refund, "'DECR', k")
    assert not re.search(r"'(SET|DEL|EXPIRE|EXPIREAT|INCR|INCRBY)'", refund)


def _pos(text, needle):
    """The index of needle in text, asserted present (an AssertionError, never
    a ValueError, when a mutated script drops it)."""
    assert needle in text, "script lacks %r" % needle
    return text.index(needle)


def test_r36_usage_limit_extras_helper(monkeypatch):
    """RED: usage_limit_extras returns {} for every golden base consume result
    and exactly retry_after / resets_at / scope for a quota refusal."""
    fn = _need(us, "usage_limit_extras")
    golden = _golden()
    for name in CONSUME_NAMES:
        assert fn(json.loads(golden["unit_" + name]["result"])) == {}, name
    _full_config(monkeypatch, quota="true", riyadh="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    _install_redis(monkeypatch, {_DV(): 3})
    res = _arun(lambda: _consume(FP))
    assert fn(res) == {"retry_after": 1800, "resets_at": "2026-10-30T00:00:00+03:00",
                       "scope": "device_daily"}, fn(res)


@pytest.mark.parametrize("life,acct,dev,daily,dev_rem,scope", [
    (0, 0, 3, 0, 0, "device_daily"),
    (0, 2, 2, 1, 1, "device_daily"),
    (2, 2, 2, 1, 1, "device_daily"),
], ids=["fresh_on_capped_device", "fresh_l0_shared", "fresh_l2_shared"])
def test_r37_status_quota_path_fresh_accounts(monkeypatch, life, acct, dev, daily, dev_rem, scope):
    """RED (R-S09-1 / R-S09-14): below lifetime 3 the quota-path status never
    reports the base lifetime-free full allowance: remaining.lifetime_free 0,
    remaining.daily the binding axis, used.lifetime present."""
    resp, _red = _quota_status(monkeypatch, life=life, acct=acct, dev=dev)
    body = resp.json()
    assert body["remaining"]["lifetime_free"] == 0, body
    assert body["remaining"]["daily"] == daily and body["remaining"].get("device_daily") == dev_rem, body
    assert body.get("counted_scope") == scope and body["used"].get("lifetime") == life, body


@pytest.mark.parametrize("life,acct,dev,scope", [
    (0, 0, 3, "device_daily"), (7, 1, 3, "device_daily"), (7, 3, 1, "daily"),
], ids=["fresh_account_used_device", "old_account_capped_device", "account_capped"])
def test_r38_s81_08_reader_port_sees_the_binding_axis(monkeypatch, life, acct, dev, scope):
    """RED (R-S09-1, the probe row): the S81-08 readers (sc-s81-s08 HEAD bcf75f84
    PaywallScreen.stateFromStatus + useComparisonCounter, hand-ported) fed the
    quota-path status of a capped axis: canCompare False, the sheet state
    'daily' with 0 left, the pill 3/3, counted_scope naming the axis."""
    resp, _red = _quota_status(monkeypatch, life=life, acct=acct, dev=dev)
    status = resp.json()
    assert status.get("counted_scope") == scope, status
    sheet = _port_state_from_status(status)
    assert sheet is not None and sheet["kind"] == "daily", (sheet, status)
    assert sheet["limit"] - sheet["used"] == 0, (sheet, status)
    counter = _port_counter(status, used=life)
    assert counter == {"canCompare": False, "pill": "3/3"}, (counter, status)


def test_r39_refund_after_flag_off_uses_the_stash(monkeypatch):
    """RED (R-S09-3, the L6 row): consume under ON (stash set), the flag goes
    OFF, the refund (no keys) still refunds the device key from the stash: ONE
    EVAL over [account, device], no base-path GET / DECRBY."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    red = _install_redis(monkeypatch, {_D(): 1, _DV(): 1})
    marks = {}

    async def flow():
        await _consume(FP)
        monkeypatch.setenv(QUOTA, "false")
        marks["c"] = len(red.calls)
        await us.refund_comparison_credit(UID)

    _arun(flow)
    assert red.calls[marks.get("c", 0):] == [["eval", "refund", [_D(), _DV()], []]], red.calls
    assert red.store == {_D(): 1, _DV(): 1}


def _ref_writes(ops):
    flat = []
    for op in ops:
        table = op[0]
        for step in op[1:]:
            if step[0] in ("insert", "update"):
                flat.append((table, step[0], json.dumps(step[1], sort_keys=True)))
    return flat


def test_r40_referral_loop1_credit_paused(monkeypatch):
    """RED (R-S09-2): under the quota flag create_invite skips the Loop-1
    deep_review_credits grant with ONE INFO line (constants only); the invite
    itself and the response are unchanged."""
    golden = _golden()
    obs = _observe_referral(monkeypatch, "create_invite", quota="true")
    writes = _ref_writes(obs["ops"])
    assert not [w for w in writes if w[0] == "deep_review_credits"], writes
    assert [w for w in writes if w[0] == "referral_invites" and w[1] == "insert"], writes
    assert obs["result"] == golden["referral_create_invite"]["result"]
    assert [lvl for lvl, _m in obs["logs"]] == ["INFO"], obs["logs"]
    for value in (REF_UID, CMP_ID, INVITE["id"]):
        assert value not in json.dumps(obs["logs"])


def test_r41_referral_loop2_rewards_and_push_paused(monkeypatch):
    """RED (R-S09-2): under the quota flag Loop 2 grants no bonus (no
    referral_redemptions row, no users bonus bump), no invitee Deep Review
    credit and sends no reward push, with ONE INFO line each for the grants and
    the push (constants only). Step 4 (lifetime_invites_consumed) and the
    redeemed mark are NOT asserted (open question for the gate)."""
    obs = _observe_referral(monkeypatch, "loop2", quota="true")
    writes = _ref_writes(obs["ops"])
    assert not [w for w in writes if w[0] == "referral_redemptions"], writes
    assert not [w for w in writes if w[0] == "users" and "referral_bonus_comparisons_this_month" in w[2]], writes
    assert not [w for w in writes if w[0] == "deep_review_credits"], writes
    assert obs["pushes"] == [], obs["pushes"]
    assert [lvl for lvl, _m in obs["logs"]] == ["INFO", "INFO"], obs["logs"]
    for value in (REF_UID, INVITEE_UID, CMP_ID, INVITE["id"]):
        assert value not in json.dumps(obs["logs"])


def test_r42_riyadh_alone_moves_only_the_date(monkeypatch):
    """RED (the T2 half of spec P11): RIYADH ON, quota OFF at T2 (Riyadh
    10-30): the consume_free_paid call list is the golden one with the daily
    date moved to 2026-10-30; no EVAL; the status key set is the base one."""
    golden = _golden()
    obs = _observe_unit(monkeypatch, "consume_free_paid", riyadh="true", at=T2)
    want = json.loads(json.dumps(golden["unit_consume_free_paid"]["calls"]).replace(
        _D("2026-10-29"), _D("2026-10-30")))
    assert obs["calls"] == want, obs["calls"]
    st = _observe_unit(monkeypatch, "status_free_paid", riyadh="true", at=T2)
    assert list(json.loads(st["result"])) == list(json.loads(golden["unit_status_free_paid"]["result"]))


# ===========================================================================
# PIN rows (green at base; the FULL configuration; recorders)
# ===========================================================================
@pytest.mark.parametrize("idx", range(5), ids=["unset", "false", "0", "off", "empty"])
@pytest.mark.parametrize("name", CONSUME_NAMES)
def test_p01_golden_consume_flag_off(monkeypatch, name, idx):
    """PIN: both flags OFF (five spellings, mixed): the consume Redis calls,
    result dict (key order) and usage_service log lines equal the golden."""
    assert _observe_unit(monkeypatch, name, idx) == _golden()["unit_" + name]


@pytest.mark.parametrize("idx", range(5), ids=["unset", "false", "0", "off", "empty"])
@pytest.mark.parametrize("name", REFUND_NAMES)
def test_p02_golden_refund_flag_off(monkeypatch, name, idx):
    """PIN: the three refund scenarios equal the golden under the five OFF
    spellings."""
    assert _observe_unit(monkeypatch, name, idx) == _golden()["unit_" + name]


@pytest.mark.parametrize("idx", range(5), ids=["unset", "false", "0", "off", "empty"])
@pytest.mark.parametrize("name", STATUS_NAMES)
def test_p03_golden_status_flag_off(monkeypatch, name, idx):
    """PIN: the three status scenarios, function result AND the RAW route body,
    equal the golden (byte-equal, key order)."""
    golden = _golden()
    assert _observe_unit(monkeypatch, name, idx) == golden["unit_" + name]
    assert _observe_route_status(monkeypatch, name, idx) == golden["route_" + name]


@pytest.mark.parametrize("site", SITES)
def test_p04_route_429_envelope_flag_off(monkeypatch, site):
    """PIN: the five consume sites' USAGE_LIMIT 429 bodies (RAW, request id
    normalised) and Redis calls equal the golden, no Retry-After, with the
    device header present."""
    idx = SITES.index(site)
    obs = _observe_route_429(monkeypatch, site, idx)
    assert obs == _golden()["route_429_" + site]
    assert obs["retry_after"] is None


@pytest.mark.parametrize("site", SITES + ("status",))
def test_p05_consume_call_shape_flag_off(monkeypatch, site):
    """PIN: flag OFF each consume site calls consume_comparison_credit with
    exactly (uid, token) and no kwargs; the status route calls
    get_usage_status(user_id=, access_token=)."""
    idx = (SITES + ("status",)).index(site)
    _full_config(monkeypatch, idx)
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    _install_redis(monkeypatch)
    _stub_routes(monkeypatch)
    if site == "status":
        seen = []

        async def rec(*args, **kwargs):
            seen.append((list(args), dict(kwargs)))
            return await _REAL_STATUS(*args, **kwargs)

        monkeypatch.setattr(usage_routes, "get_usage_status", rec)
        resp = _status_route()
        assert resp.status_code == 200
        assert seen == [([], {"user_id": UID, "access_token": TOKEN})], seen
        return
    rec = _install_consume_rec(monkeypatch)
    with _as_user(USER):
        resp = _req(_client(), site)
    assert resp.status_code == 200, resp.text
    assert rec.calls == [([UID, TOKEN], {})], rec.calls


@pytest.mark.parametrize("idx", range(5), ids=["unset", "false", "0", "off", "empty"])
def test_p06_handler_flag_off(monkeypatch, idx):
    """PIN: flag OFF a USAGE_LIMIT 429 detail carrying resets_at / scope /
    retry_after 60 reaches the wire as the W1-9 base {success, error, code,
    request_id, retry_after_seconds} + Retry-After, no resets_at / scope."""
    obs = _observe_handler(monkeypatch, idx)
    assert obs == _golden()["handler_429_usage_limit_extras"]
    body = json.loads(obs["body"])
    assert "resets_at" not in body and "scope" not in body and obs["retry_after"] == "60"


@pytest.mark.parametrize("idx", range(5), ids=["unset", "false", "0", "off", "empty"])
def test_p07_key_helpers_utc_flag_off(monkeypatch, idx):
    """PIN: the key helper table at T1, T2 and 2026-10-31T23:30Z equals the
    golden (UTC strings) under the five OFF spellings."""
    assert _observe_key_helpers(monkeypatch, idx) == _golden()["key_helpers"]


def test_p08_no_eval_and_no_context_read_flag_off(monkeypatch):
    """PIN (B1): flag OFF with an EVAL that raises and every request_context
    accessor (and llm_spend_breaker._eval) patched to RAISE: the consume,
    refund and status scenarios still equal the golden."""
    golden = _golden()

    def boom(*_a, **_kw):
        raise AssertionError("S81-09 state read with the flag OFF")

    for name in ("device_fingerprint", "device_key", "header_state", "consent_version",
                 "compare_request_id"):
        monkeypatch.setattr(rc, name, boom)
    monkeypatch.setattr(lsb, "_eval", boom)
    for i, name in enumerate(sorted(UNIT_SCENARIOS)):
        if UNIT_SCENARIOS[name]["store"] is None:
            obs = _observe_unit(monkeypatch, name, i)
        else:
            red = FakeRedis(eval_raises=AssertionError("EVAL with the flag OFF"))
            obs = _observe_unit(monkeypatch, name, i, red=red)
        assert obs == golden["unit_" + name], name


def test_p09_knobs_not_read_flag_off(monkeypatch):
    """PIN (B1): flag OFF the consume / refund / status paths never read
    DEVICE_QUOTA_EXEMPT_USER_IDS or the decoy DEVICE_DAILY_QUOTA_CAP
    (os.getenv recorder)."""
    seen = []
    real_getenv = os.getenv

    def rec(name, default=None):
        seen.append(name)
        return real_getenv(name, default)

    monkeypatch.setattr(os, "getenv", rec)
    for i, name in enumerate(sorted(UNIT_SCENARIOS)):
        _observe_unit(monkeypatch, name, i)
    assert seen, "the recorder saw the flag reads"
    assert EXEMPT not in seen and CAP_DECOY not in seen, sorted(set(seen))


def test_p10_anon_gate_untouched_quota_on(monkeypatch):
    """PIN: quota ON + ENABLE_ANON_USAGE_GATE ON: the anonymous camera 429 (anon
    keys, body without extras, Redis calls) equals the golden recorded OFF."""
    obs = _observe_anon_image(monkeypatch, quota="true")
    assert obs == _golden()["anon_429_image"]
    assert sorted(json.loads(obs["body"])) == ["code", "error", "request_id", "success"]


@pytest.mark.parametrize("name", CONSUME_NAMES)
def test_p11_riyadh_alone_same_day_is_golden(monkeypatch, name):
    """PIN (the T0 half of spec P11): RIYADH ON, quota OFF at T0 (the Riyadh
    and UTC dates agree): the consume scenarios equal the golden; no EVAL."""
    obs = _observe_unit(monkeypatch, name, riyadh="true")
    assert obs == _golden()["unit_" + name]


def test_p12_tier_limits_literal():
    """PIN: TIER_LIMITS (read by ast) is the base literal (the legal parity
    pins D11 and the register benefits read it)."""
    tree = ast.parse((APP / "services" / "usage_service.py").read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "TIER_LIMITS" for t in n.targets)]
    assert len(nodes) == 1
    assert ast.literal_eval(nodes[0].value) == {
        "free": {"lifetime_free": 3, "monthly": 10, "daily": 3},
        "premium": {"lifetime_free": 0, "monthly": 70, "daily": 10},
    }


def test_p13_check_usage_allowed_unchanged_quota_on(monkeypatch):
    """PIN: check_usage_allowed (no caller) returns the same result with the
    same Redis calls with the quota flag ON and OFF."""
    out = []
    for quota in (None, "true"):
        _full_config(monkeypatch, quota=quota)
        _freeze(monkeypatch, T0)
        _tier(monkeypatch, "free", 5)
        red = _install_redis(monkeypatch, {_D(): 1, _M(): 2, _DV(): 3})
        res = _arun(lambda: us.check_usage_allowed(UID, TOKEN))
        out.append((_dumps(res), red.calls))
    assert out[0] == out[1], out


def test_p14_success_records_lifetime(monkeypatch):
    """PIN: quota ON success through POST /text/compare still fires
    record_lifetime_comparison once (the lifetime counter keeps counting)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, "free", 5)
    _install_redis(monkeypatch)
    lifetime = []
    _stub_routes(monkeypatch, lifetime=lifetime)
    with _as_user(USER):
        resp = _req(_client(), "text_post")
    assert resp.status_code == 200, resp.text
    assert lifetime == [UID], lifetime


@pytest.mark.parametrize("idx", range(5), ids=["unset", "false", "0", "off", "empty"])
@pytest.mark.parametrize("which", ["create_invite", "loop2"])
def test_p15_referral_flag_off_golden(monkeypatch, which, idx):
    """PIN (R-S09-2): flag OFF the referral writes (normalised Supabase op list),
    the push and the response equal the golden; no INFO line."""
    obs = _observe_referral(monkeypatch, which, idx)
    assert obs == _golden()["referral_" + which]
    assert obs["logs"] == []


def test_p16_null_tier_runs_the_base_path(monkeypatch):
    """PIN (R-S09-5): quota ON, a NULL subscription_tier: the predicate is
    tier == 'free', so the base path runs (the golden consume_free_paid calls;
    no EVAL; monthly cap kept)."""
    _full_config(monkeypatch, quota="true")
    _freeze(monkeypatch, T0)
    _tier(monkeypatch, None, 5)
    red = _install_redis(monkeypatch)
    res = _arun(lambda: us.consume_comparison_credit(UID, TOKEN))
    assert _jr(red.calls) == _golden()["unit_consume_free_paid"]["calls"], red.calls
    assert res["allowed"] is True and res["consumed"] is True and res["tier"] is None

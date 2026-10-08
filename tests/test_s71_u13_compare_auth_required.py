"""U13 -- the paid routes require a caller (ENABLE_COMPARE_AUTH_REQUIRED). RED file 1 of 2.

Spec (authoritative): docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md,
section 6 "File 1", as corrected by "Review corrections (BINDING)" C1-C11 and the
"Orchestrator rulings (BINDING)" UR1-UR15. Test ids T01-T24 plus T16b (C5) are in every
node name. Expected at BASE eb86075e (UR10): 68 RED / 69 PIN.

Routes (spec 2.1): USER = U1-U6 (the app's six paid routes, `require_paid_route_user`),
ADMIN = A1-A4 (no app caller, `require_paid_route_admin`, UR3). ALL = the ten.

Conventions (spec section 6 + the RED brief):
  * hermetic: every provider / usage / prefs / anon-gate / log / persist / DNS leg is
    patched at the ROUTE module's import name (`_install_stubs`), and
    `auth_routes.verify_token` is an AsyncMock keyed on the two bearer sentinels
    (`u13.valid.jwt` -> a user, `u13.expired.jwt` -> None, the Supabase-rejection shape);
  * every node sets or deletes EVERY flag it depends on (`_flags`), including
    ADMIN_API_KEY, which other modules set at collection (spec 2.8);
  * nothing this unit creates is imported at module top: `compare_auth_required_enabled`
    is imported inside the bodies and the two guards are matched by `__name__`, so a RED
    is a test failure, never a collection ERROR; this module imports no `app.*` at module
    top at all, so the recorder below can neutralise credentials first;
  * a fixed X-Request-ID on every request; sentinels are plain words, never an sk- shape;
  * route lookups go through tests/_route_introspection (walk_routes / find_route).

T17 + T23 baseline (UR11, C4): ONE committed fixture,
tests/fixtures/s71_u13_flag_off_baseline.json, holds the 30 flag-OFF records of T17
(10 routes x {anonymous, valid bearer, rejected bearer}; status, content type, body --
for the stream route the joined SSE chunks --, the stub call counts, the
fire_and_forget label sequence and the verify_token await count) and the base OpenAPI
operation objects of the ten routes plus `components` (T23). It is written by
`record_flag_off_baseline` (a plain function, not collected) and compared record by
record. Recorder command, run ONLY in a DETACHED scratch worktree at BASE eb86075e
(never an install, never a .env), from that worktree's root:

    PYTHONIOENCODING=utf-8 <pinned venv python> -m tests.test_s71_u13_compare_auth_required \
        --record tests/fixtures/s71_u13_flag_off_baseline.json --recorded-at <base sha>

The recorder neutralises credentials and installs the network guard BEFORE importing
`app.*` (the conftest order). Normalised fields: NONE (`NORMALISED_FIELDS` below) -- two
recorder runs at base produced byte-identical output, so nothing needed normalising.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import sys
from pathlib import Path
from typing import NamedTuple
from unittest.mock import AsyncMock

import pytest

from tests._route_introspection import (
    assert_route_table_visible,
    find_route,
    route_method_paths,
    walk_routes,
)

# ---------------------------------------------------------------------------
# names (UR8, verbatim) and sentinels
# ---------------------------------------------------------------------------
FLAG = "ENABLE_COMPARE_AUTH_REQUIRED"
STRICT = "ENABLE_STRICT_OPTIONAL_AUTH"
METER = "ENABLE_PAID_ROUTE_METERING"
ANON_GATE = "ENABLE_ANON_USAGE_GATE"
ADMIN_ENV = "ADMIN_API_KEY"
HARNESS_OPT_IN = "HARNESS_SEND_ADMIN_KEY"
SYN_TOKEN = "SEARCH_LOG_SYNTHETIC_TOKEN"
REFERRAL = "ENABLE_REFERRAL_SYSTEM"

# Every env name that one of the ten routes (or a route-level helper they call) reads
# per call. All are deleted before every node; a node then sets what it needs.
CLEAN_ENV = (
    FLAG, STRICT, METER, ANON_GATE, HARNESS_OPT_IN, SYN_TOKEN, REFERRAL,
    "ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
    "ENABLE_COMPARISON_ID_ECHO", "ENABLE_PREVERDICT_DISCONNECT_ABORT",
    "ENABLE_CAMERA_FAILURE_ENVELOPE", "ENABLE_LLM_PREFLIGHT_BREAKER",
    "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_OFFLOOP_DNS_RESOLVE",
    "ENABLE_PROXY_AWARE_RATELIMIT", "ENABLE_ARABIC_VERDICT_OUTPUT",
)

USER_GUARD = "require_paid_route_user"
ADMIN_GUARD = "require_paid_route_admin"
AUTH_TEXT = "Sign in to continue."

ADMIN_SENTINEL = "u13-admin-sentinel-key"
WRONG_ADMIN = "u13-wrong-admin-key"
VALID_JWT = "u13.valid.jwt"
EXPIRED_JWT = "u13.expired.jwt"
REQUEST_ID = "u13-fixed-request-id"
DEVICE_FP = "0123456789abcdef" * 4
QUERY_SENTINEL = "U13QUERYSENTINEL"
PRICE_SENTINEL = "IPHONE-U13-SENTINEL"
QUERY = f"{QUERY_SENTINEL} alpha vs {QUERY_SENTINEL} beta"
URL1 = "https://u13-one.example.invalid/p/1"
URL2 = "https://u13-two.example.invalid/p/2"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 60
USER = {"id": "u13-user-id", "email": "u13@example.invalid", "access_token": VALID_JWT}

BASE_SHA_PREFIX = "eb86075e"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "s71_u13_flag_off_baseline.json"
RECORDER = "tests/test_s71_u13_compare_auth_required.py::record_flag_off_baseline"
# UR11: every normalised field, with its reason. Measured: two recorder runs at base
# were byte-identical, so no field is normalised.
NORMALISED_FIELDS: dict = {}

COMPARE_RESULT = {
    "success": True,
    "products": [{"brand": "U13", "name": "alpha"}, {"brand": "U13", "name": "beta"}],
    "metadata": {"total_cost": 0.0},
}
URL_RESULT = {
    "success": True,
    "products": [{"brand": "U13", "name": "one"}, {"brand": "U13", "name": "two"}],
    "metadata": {"total_cost": 0.0},
}
EXTRACT_RESULT = {"success": True, "product": {"brand": "U13", "name": "one"}}
PRICES_RESULT = {"prices": {"bahrain": None}, "u13": "regional-prices-stub"}
VISION_RESULT = {"error": "u13-vision-stub", "cost": 0.0}
USAGE_OK = {
    "allowed": True, "reason": None, "tier": "free", "consumed": True,
    "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
}
ANON_OK = {
    "allowed": True, "reason": None, "tier": "free", "consumed": False,
    "remaining": {"daily": 2, "monthly": 9},
}
PREFS = {"success": True, "preferences_completed": False}


class Route(NamedTuple):
    key: str
    method: str
    path: str
    kind: str        # "user" | "admin"
    provider: str    # the stub key of the route's paid leg


ROUTES = (
    Route("U1", "POST", "/api/v1/text/compare", "user", "text_routes.compare_from_text"),
    Route("U2", "GET", "/api/v1/text/compare", "user", "text_routes.compare_from_text"),
    Route("U3", "GET", "/api/v1/text/compare/stream", "user",
          "text_routes.compare_from_text_streaming"),
    Route("U4", "POST", "/api/v1/url/compare", "user", "url_routes.compare_from_urls"),
    Route("U5", "GET", "/api/v1/url/compare", "user", "url_routes.compare_from_urls"),
    Route("U6", "POST", "/api/v1/image/identify", "user", "image_routes.identify_products"),
    Route("A1", "POST", "/api/v1/text/quick", "admin", "text_routes.compare_from_text"),
    Route("A2", "GET", "/api/v1/text/prices/{product}", "admin",
          "text_routes.get_regional_prices"),
    Route("A3", "POST", "/api/v1/url/extract", "admin", "url_routes.extract_from_url"),
    Route("A4", "GET", "/api/v1/url/extract", "admin", "url_routes.extract_from_url"),
)
USER_ROUTES = tuple(r for r in ROUTES if r.kind == "user")
ADMIN_ROUTES = tuple(r for r in ROUTES if r.kind == "admin")
ROUTE_BY_KEY = {r.key: r for r in ROUTES}
ALL_METHOD_PATHS = {f"{r.method} {r.path}" for r in ROUTES}
U13E_ADMIN_ONLY = frozenset({"GET /api/v1/url/detect", "POST /api/v1/url/detect"})

SCENARIOS = ("anonymous", "valid_bearer", "rejected_bearer")
SCENARIO_NAMES = tuple(f"{r.key}.{s}" for r in ROUTES for s in SCENARIOS)


def _ids(routes):
    return [f"{r.key}-{r.method}-{r.path}" for r in routes]


# ---------------------------------------------------------------------------
# env, stubs, client, requests
# ---------------------------------------------------------------------------
def _flags(mp, *, auth=False, strict=False, meter=False, anon_gate=False,
           admin_key=None, referral=False):
    """Set or delete EVERY flag a node depends on (never inherit the ambient env)."""
    for name in CLEAN_ENV:
        mp.delenv(name, raising=False)
    mp.delenv(ADMIN_ENV, raising=False)
    if auth:
        mp.setenv(FLAG, "true")
    if strict:
        mp.setenv(STRICT, "true")
    if meter:
        mp.setenv(METER, "true")
    if anon_gate:
        mp.setenv(ANON_GATE, "true")
    if referral:
        mp.setenv(REFERRAL, "true")
    if admin_key is not None:
        mp.setenv(ADMIN_ENV, admin_key)


@pytest.fixture(autouse=True)
def _u13_clean_env_and_limiter(monkeypatch):
    _flags(monkeypatch)
    from app.middleware.rate_limiter import limiter
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()


class _Stubs:
    """Records every stubbed leg at CALL time (fire_and_forget targets are BUILT
    synchronously, so a recorder sees them even when no task runs)."""

    def __init__(self):
        self.calls: dict = {}
        self.labels: list = []
        self.verify_token = None

    def hit(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1

    def count(self, name):
        return self.calls.get(name, 0)

    def total(self):
        return sum(self.calls.values())


def _install_stubs(mp):
    from app.api import auth_routes, image_routes, text_routes, url_routes

    st = _Stubs()

    def _async(name, value):
        async def _stub(*_a, **_k):
            st.hit(name)
            return copy.deepcopy(value)
        return _stub

    def _plain(name):
        def _stub(*_a, **_k):
            st.hit(name)
            return ("u13-stub-call", name)
        return _stub

    def _ff_factory(prefix):
        def _ff(coro, label=None, *_a, **_k):
            st.hit(f"{prefix}.fire_and_forget")
            st.labels.append(label)
            if asyncio.iscoroutine(coro):
                coro.close()
            return None
        return _ff

    class _Service:
        async def compare_from_text(self, *_a, **_k):
            st.hit("text_routes.compare_from_text")
            return copy.deepcopy(COMPARE_RESULT)

        def compare_from_text_streaming(self, *_a, **_k):
            st.hit("text_routes.compare_from_text_streaming")

            async def _gen():
                yield "status", {"stage": "u13", "progress": 10}
                yield "complete", copy.deepcopy(COMPARE_RESULT)
            return _gen()

    def _get_service(*_a, **_k):
        st.hit("text_routes.get_comparison_service")
        return _Service()

    class _ImageService:
        def __init__(self, *_a, **_k):
            st.hit("image_routes.StructuredComparisonService")

        async def compare_from_text(self, *_a, **_k):
            st.hit("image_routes.compare_from_text")
            return copy.deepcopy(COMPARE_RESULT)

    async def _verify(token, *_a, **_k):
        if token == VALID_JWT:
            return dict(USER)
        return None

    st.verify_token = AsyncMock(side_effect=_verify)
    mp.setattr(auth_routes, "verify_token", st.verify_token)

    t = "text_routes"
    mp.setattr(text_routes, "get_comparison_service", _get_service)
    mp.setattr(text_routes, "get_regional_prices", _async(f"{t}.get_regional_prices", PRICES_RESULT))
    mp.setattr(text_routes, "consume_comparison_credit", _async(f"{t}.consume_comparison_credit", USAGE_OK))
    mp.setattr(text_routes, "refund_comparison_credit", _plain(f"{t}.refund_comparison_credit"))
    mp.setattr(text_routes, "record_lifetime_comparison", _plain(f"{t}.record_lifetime_comparison"))
    mp.setattr(text_routes, "get_user_preferences", _async(f"{t}.get_user_preferences", PREFS))
    mp.setattr(text_routes, "check_anon_usage_allowed", _async(f"{t}.check_anon_usage_allowed", ANON_OK))
    mp.setattr(text_routes, "record_anon_comparison", _plain(f"{t}.record_anon_comparison"))
    mp.setattr(text_routes, "log_search", _plain(f"{t}.log_search"))
    mp.setattr(text_routes, "save_comparison_and_track_cohort",
               _plain(f"{t}.save_comparison_and_track_cohort"))
    mp.setattr(text_routes, "fire_and_forget", _ff_factory(t))

    u = "url_routes"
    mp.setattr(url_routes, "_validate_url_offloop_or_sync", _async(f"{u}._validate_url_offloop_or_sync", True))
    mp.setattr(url_routes, "compare_from_urls", _async(f"{u}.compare_from_urls", URL_RESULT))
    mp.setattr(url_routes, "extract_from_url", _async(f"{u}.extract_from_url", EXTRACT_RESULT))
    mp.setattr(url_routes, "consume_comparison_credit", _async(f"{u}.consume_comparison_credit", USAGE_OK))
    mp.setattr(url_routes, "refund_comparison_credit", _plain(f"{u}.refund_comparison_credit"))
    mp.setattr(url_routes, "record_lifetime_comparison", _plain(f"{u}.record_lifetime_comparison"))
    mp.setattr(url_routes, "save_comparison_and_track_cohort",
               _plain(f"{u}.save_comparison_and_track_cohort"))
    mp.setattr(url_routes, "log_search", _plain(f"{u}.log_search"))
    mp.setattr(url_routes, "fire_and_forget", _ff_factory(u))

    i = "image_routes"
    mp.setattr(image_routes, "identify_products", _async(f"{i}.identify_products", VISION_RESULT))
    mp.setattr(image_routes, "StructuredComparisonService", _ImageService)
    mp.setattr(image_routes, "check_anon_usage_allowed", _async(f"{i}.check_anon_usage_allowed", ANON_OK))
    mp.setattr(image_routes, "record_anon_comparison", _plain(f"{i}.record_anon_comparison"))
    mp.setattr(image_routes, "consume_comparison_credit", _async(f"{i}.consume_comparison_credit", USAGE_OK))
    mp.setattr(image_routes, "refund_comparison_credit", _plain(f"{i}.refund_comparison_credit"))
    mp.setattr(image_routes, "refund_anon_comparison_credit", _plain(f"{i}.refund_anon_comparison_credit"))
    mp.setattr(image_routes, "record_lifetime_comparison", _plain(f"{i}.record_lifetime_comparison"))
    mp.setattr(image_routes, "save_comparison_and_track_cohort",
               _plain(f"{i}.save_comparison_and_track_cohort"))
    mp.setattr(image_routes, "log_search", _plain(f"{i}.log_search"))
    mp.setattr(image_routes, "fire_and_forget", _ff_factory(i))
    return st


@pytest.fixture
def stubs(monkeypatch):
    return _install_stubs(monkeypatch)


def _new_client():
    from fastapi.testclient import TestClient

    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client():
    return _new_client()


def _headers(*, bearer=None, admin=None, fingerprint=False, extra=None):
    h = {"X-Request-ID": REQUEST_ID}
    if bearer is not None:
        h["Authorization"] = f"Bearer {bearer}"
    if admin is not None:
        h["X-Admin-Key"] = admin
    if fingerprint:
        h["X-Device-Fingerprint"] = DEVICE_FP
    if extra:
        h.update(extra)
    return h


def _send(client, route, headers, *, product="U13-PRODUCT"):
    k = route.key
    if k == "U1":
        return client.post(route.path, json={"query": QUERY}, headers=headers)
    if k in ("U2", "U3"):
        return client.get(route.path, params={"q": QUERY}, headers=headers)
    if k == "U4":
        return client.post(route.path, json={"url1": URL1, "url2": URL2}, headers=headers)
    if k == "U5":
        return client.get(route.path, params={"url1": URL1, "url2": URL2}, headers=headers)
    if k == "U6":
        files = [("images", ("u13-a.jpg", JPEG, "image/jpeg")),
                 ("images", ("u13-b.jpg", JPEG, "image/jpeg"))]
        return client.post(route.path, files=files, headers=headers)
    if k == "A1":
        return client.post(route.path, json={"product1": "U13 alpha", "product2": "U13 beta"},
                           headers=headers)
    if k == "A2":
        return client.get(f"/api/v1/text/prices/{product}", headers=headers)
    if k == "A3":
        return client.post(route.path, json={"url": URL1}, headers=headers)
    if k == "A4":
        return client.get(route.path, params={"url": URL1}, headers=headers)
    raise AssertionError(f"unknown route {k}")


def _assert_envelope(resp, status, code, error=None):
    assert resp.status_code == status, (
        f"status {resp.status_code} != expected {status}: {resp.text[:300]!r}")
    ctype = resp.headers.get("content-type", "")
    assert ctype.startswith("application/json"), ctype
    body = resp.json()
    assert set(body) == {"success", "error", "code", "request_id"}, body
    assert body["success"] is False, body
    assert body["code"] == code, body
    assert body["request_id"] == REQUEST_ID, body
    if error is not None:
        assert body["error"] == error, body
    return body


def _dependant_call_names(dependant):
    names = []
    stack = list(getattr(dependant, "dependencies", None) or [])
    while stack:
        dep = stack.pop()
        call = getattr(dep, "call", None)
        names.append(getattr(call, "__name__", repr(call)))
        stack.extend(getattr(dep, "dependencies", None) or [])
    return names


# ---------------------------------------------------------------------------
# T17 / T23 recorder (UR11) -- plain functions, never collected
# ---------------------------------------------------------------------------
def _scenario_headers(scenario):
    if scenario == "valid_bearer":
        return _headers(bearer=VALID_JWT)
    if scenario == "rejected_bearer":
        return _headers(bearer=EXPIRED_JWT)
    return _headers()


def _record_one(mp, route, scenario):
    """Drive ONE flag-OFF scenario (flag, strict and metering unset) and return its
    record: status, content type, body (JSON, or the joined SSE text), stub call
    counts, the fire_and_forget label sequence and the verify_token await count."""
    from app.middleware.rate_limiter import limiter

    _flags(mp)
    st = _install_stubs(mp)
    limiter.reset()
    resp = _send(_new_client(), route, _scenario_headers(scenario))
    ctype = resp.headers.get("content-type", "")
    body = {"json": resp.json()} if ctype.startswith("application/json") else {"text": resp.text}
    return {
        "scenario": f"{route.key}.{scenario}",
        "route": f"{route.method} {route.path}",
        "status": resp.status_code,
        "content_type": ctype,
        "body": body,
        "stub_calls": dict(sorted(st.calls.items())),
        "fire_and_forget_labels": list(st.labels),
        "verify_token_awaits": st.verify_token.await_count,
    }


def _openapi_snapshot():
    """The ten operation objects + components, through a FRESH schema build; the
    app's cached schema is restored afterwards."""
    from app.main import app

    saved = app.openapi_schema
    app.openapi_schema = None
    try:
        schema = app.openapi()
    finally:
        app.openapi_schema = saved
    ops = {f"{r.method} {r.path}": schema["paths"][r.path][r.method.lower()] for r in ROUTES}
    return json.loads(json.dumps({"operations": ops, "components": schema.get("components", {})}))


def record_flag_off_baseline(out_path, recorded_at):
    """UR11 recorder. Run ONLY at BASE in a detached scratch worktree (see the module
    docstring). Neutralises credentials and installs the network guard BEFORE any
    `app.*` import, exactly as tests/conftest.py does."""
    from tests._env_safety import install_dotenv_guard, neutralize_credentials

    neutralize_credentials()
    install_dotenv_guard()
    from tests import _netguard

    _netguard.install()
    records = []
    for route in ROUTES:
        for scenario in SCENARIOS:
            with pytest.MonkeyPatch.context() as mp:
                records.append(_record_one(mp, route, scenario))
    with pytest.MonkeyPatch.context() as mp:
        _flags(mp)
        openapi = _openapi_snapshot()
    doc = {
        "_meta": {
            "spec": "docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md",
            "rule": ("U13 flag OFF (ENABLE_COMPARE_AUTH_REQUIRED, ENABLE_STRICT_OPTIONAL_AUTH, "
                     "ENABLE_PAID_ROUTE_METERING unset) is byte-identical per route for "
                     "anonymous, valid-bearer and rejected-bearer callers; the ten operations "
                     "and components of the OpenAPI schema are unchanged"),
            "recorder": RECORDER,
            "recorded_at": recorded_at,
            "normalised_fields": NORMALISED_FIELDS,
            "records": len(records),
        },
        "flag_off_records": records,
        "openapi": openapi,
    }
    text = json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    Path(out_path).write_bytes(text.encode("ascii"))
    return doc


def _load_fixture():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


# ===========================================================================
# T01-T03  the flag reader
# ===========================================================================
@pytest.mark.parametrize("value", [None, "", "false", "0", "no", "off", "garbage"])
def test_T01_flag_default_off(monkeypatch, value):
    """RED T01: unset / "" / false / 0 / no / off / garbage -> False (default OFF)."""
    _flags(monkeypatch)
    if value is not None:
        monkeypatch.setenv(FLAG, value)
    from app.api.text_routes import compare_auth_required_enabled
    assert compare_auth_required_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TRUE ", "On"])
def test_T02_flag_truthy_values(monkeypatch, value):
    """RED T02: 1 / true / yes / on / " TRUE " / On -> True (strip + lower)."""
    _flags(monkeypatch)
    monkeypatch.setenv(FLAG, value)
    from app.api.text_routes import compare_auth_required_enabled
    assert compare_auth_required_enabled() is True


def test_T03_flag_read_per_call(monkeypatch):
    """RED T03: read per call, never cached (mutant X2)."""
    _flags(monkeypatch)
    from app.api.text_routes import compare_auth_required_enabled
    monkeypatch.setenv(FLAG, "true")
    assert compare_auth_required_enabled() is True
    monkeypatch.delenv(FLAG, raising=False)
    assert compare_auth_required_enabled() is False
    monkeypatch.setenv(FLAG, "true")
    assert compare_auth_required_enabled() is True


# ===========================================================================
# T04-T05  inventory
# ===========================================================================
@pytest.mark.parametrize("route", ROUTES, ids=_ids(ROUTES))
def test_T04_inventory_guard_declared(monkeypatch, route):
    """RED T04: each of the ten routes' dependant tree carries exactly ONE call named
    require_paid_route_user (USER) / require_paid_route_admin (ADMIN), and none of the
    other guard (mutant X10)."""
    _flags(monkeypatch)
    from app.main import app
    assert_route_table_visible(app)
    entry = find_route(app, route.path, route.method)
    assert entry is not None, f"{route.method} {route.path} not mounted"
    names = _dependant_call_names(entry.route.dependant)
    want, other = (USER_GUARD, ADMIN_GUARD) if route.kind == "user" else (ADMIN_GUARD, USER_GUARD)
    assert names.count(want) == 1, (
        f"{route.key} {route.method} {route.path}: {want} occurs {names.count(want)} times "
        f"in the dependant tree {sorted(names)}")
    assert names.count(other) == 0, (route.key, sorted(names))


def test_T05_inventory_out_of_scope_untouched(monkeypatch):
    """PIN T05: no route outside the ten (incl. referral invite GET / quiz POST,
    /url/retailers, /share/{token}, /home/*, /feedback, /events,
    /legal/*, /app/version, /health, /text/parse, /text/price-kpi, DELETE /text/cache,
    /api/v1/admin/*) has a dependency named require_paid_route_*. Non-vacuous: the
    route table is visible and the named out-of-scope routes are present.
    (/url/detect x2 is admin-only since U13e: skipped like the ten, kept in must_exist.)"""
    _flags(monkeypatch)
    from app.main import app
    assert_route_table_visible(app)
    present = route_method_paths(app)
    must_exist = {
        "GET /api/v1/referrals/invite/{share_token}",
        "POST /api/v1/referrals/invite/{share_token}/quiz",
        "GET /api/v1/url/detect", "POST /api/v1/url/detect", "GET /api/v1/url/retailers",
        "GET /api/v1/share/{token}", "GET /api/v1/home/trending", "POST /api/v1/feedback",
        "POST /api/v1/events", "GET /api/v1/legal/privacy", "GET /api/v1/app/version",
        "GET /health", "GET /api/v1/text/parse", "GET /api/v1/text/price-kpi",
        "DELETE /api/v1/text/cache", "GET /api/v1/admin/costs",
    }
    assert not (must_exist - present), sorted(must_exist - present)
    assert ALL_METHOD_PATHS <= present, sorted(ALL_METHOD_PATHS - present)
    offenders = []
    checked = 0
    for entry in walk_routes(app):
        dependant = getattr(entry.route, "dependant", None)
        if dependant is None:
            continue
        for method in entry.methods:
            if f"{method} {entry.path}" in ALL_METHOD_PATHS | U13E_ADMIN_ONLY:
                continue
            checked += 1
            names = [n for n in _dependant_call_names(dependant)
                     if n.startswith("require_paid_route_")]
            if names:
                offenders.append((f"{method} {entry.path}", names))
    assert checked >= 60, checked
    assert not offenders, offenders


# ===========================================================================
# T06-T07  anonymous refused (flag ON)
# ===========================================================================
@pytest.mark.parametrize("route", ROUTES, ids=_ids(ROUTES))
def test_T06_anonymous_refused_flag_on(monkeypatch, stubs, client, route):
    """RED T06: flag ON, no credential: 401 AUTH_REQUIRED envelope ("Sign in to
    continue."), and ZERO calls to every stubbed leg (provider, usage, prefs, anon gate,
    log_search, fire_and_forget, DNS). A1 and U6 run with ENABLE_ANON_USAGE_GATE=true
    and a valid X-Device-Fingerprint so the anon gate is armed (mutant X5)."""
    armed = route.key in ("A1", "U6")
    _flags(monkeypatch, auth=True, anon_gate=armed)
    resp = _send(client, route, _headers(fingerprint=armed))
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert stubs.calls == {}, stubs.calls
    assert stubs.labels == [], stubs.labels
    assert stubs.verify_token.await_count == 0


def test_T07_sse_refusal_is_plain_json(monkeypatch, stubs, client):
    """RED T07: anonymous GET /text/compare/stream with the flag ON is a 401
    application/json envelope BEFORE any stream byte; no `event:` / `data:` bytes and
    get_comparison_service is never called."""
    _flags(monkeypatch, auth=True)
    resp = _send(client, ROUTE_BY_KEY["U3"], _headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert "event:" not in resp.text and "data:" not in resp.text, resp.text[:200]
    assert stubs.count("text_routes.get_comparison_service") == 0
    assert stubs.calls == {}, stubs.calls


# ===========================================================================
# T08-T14  bearer and admin credentials (flag ON)
# ===========================================================================
@pytest.mark.parametrize("route", USER_ROUTES, ids=_ids(USER_ROUTES))
def test_T08_valid_bearer_passes_user_routes(monkeypatch, stubs, client, route):
    """PIN T08: flag ON + a valid bearer on a USER route: not 401/403, the route's paid
    leg runs once, verify_token awaited EXACTLY once (the dependency cache; mutant X3)."""
    _flags(monkeypatch, auth=True)
    resp = _send(client, route, _headers(bearer=VALID_JWT))
    assert resp.status_code not in (401, 403), (resp.status_code, resp.text[:300])
    assert stubs.count(route.provider) == 1, stubs.calls
    assert stubs.verify_token.await_count == 1


@pytest.mark.parametrize("route", ADMIN_ROUTES, ids=_ids(ADMIN_ROUTES))
def test_T09_bearer_is_not_enough_on_admin_routes(monkeypatch, stubs, client, route):
    """RED T09: flag ON + a valid bearer and no admin header on an ADMIN route: 401
    AUTH_REQUIRED, verify_token NOT awaited (no bearer resolution, UR3), zero calls."""
    _flags(monkeypatch, auth=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, route, _headers(bearer=VALID_JWT))
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.verify_token.await_count == 0
    assert stubs.calls == {}, stubs.calls


@pytest.mark.parametrize("route", ROUTES, ids=_ids(ROUTES))
def test_T10_admin_credential_passes(monkeypatch, stubs, client, route):
    """PIN T10: flag ON, ADMIN_API_KEY = sentinel, matching X-Admin-Key, no bearer: not
    401/403, the paid leg runs once, verify_token not awaited."""
    _flags(monkeypatch, auth=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, route, _headers(admin=ADMIN_SENTINEL))
    assert resp.status_code not in (401, 403), (resp.status_code, resp.text[:300])
    assert stubs.count(route.provider) == 1, stubs.calls
    assert stubs.verify_token.await_count == 0


@pytest.mark.parametrize("route", ROUTES, ids=_ids(ROUTES))
def test_T11_wrong_admin_key_is_403(monkeypatch, stubs, client, route):
    """RED T11: flag ON, key set, a present non-empty WRONG X-Admin-Key: 403 FORBIDDEN,
    never a fall-through to anonymous; zero calls."""
    _flags(monkeypatch, auth=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, route, _headers(admin=WRONG_ADMIN))
    _assert_envelope(resp, 403, "FORBIDDEN")
    assert stubs.calls == {}, stubs.calls


def test_T12_admin_header_but_key_unset_is_403(monkeypatch, stubs, client):
    """RED T12: ADMIN_API_KEY deleted, X-Admin-Key present: 403 (verify_admin_key's
    empty-expected rule), zero calls."""
    _flags(monkeypatch, auth=True, admin_key=None)
    resp = _send(client, ROUTE_BY_KEY["U1"], _headers(admin="anything"))
    _assert_envelope(resp, 403, "FORBIDDEN")
    assert stubs.calls == {}, stubs.calls


def test_T13_empty_admin_header_is_absent(monkeypatch, stubs, client):
    """RED T13: X-Admin-Key "" with no bearer is "no admin attempt": 401 AUTH_REQUIRED,
    not 403 (the emptiness guard runs before any compare; mutant X4)."""
    _flags(monkeypatch, auth=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, ROUTE_BY_KEY["U1"], _headers(admin=""))
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls


def test_T14_non_ascii_admin_header_is_403_never_500(monkeypatch, stubs, client):
    """RED T14: an X-Admin-Key carrying byte 0xE9 (sent as BYTES -- httpx raises on a
    non-ASCII str value) is a 403, never a 500."""
    _flags(monkeypatch, auth=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, ROUTE_BY_KEY["U1"], _headers(extra={"X-Admin-Key": b"\xe9u13"}))
    _assert_envelope(resp, 403, "FORBIDDEN")
    assert stubs.calls == {}, stubs.calls


# ===========================================================================
# T15-T16b  rejected bearers and composition
# ===========================================================================
@pytest.mark.parametrize("route", USER_ROUTES, ids=_ids(USER_ROUTES))
def test_T15_rejected_bearer_strict_off_is_401(monkeypatch, stubs, client, route):
    """RED T15: flag ON, strict OFF, a rejected bearer on a USER route: 401
    AUTH_REQUIRED (never the silent anonymous downgrade); zero provider/usage calls
    (mutant X1)."""
    _flags(monkeypatch, auth=True, strict=False)
    resp = _send(client, route, _headers(bearer=EXPIRED_JWT))
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls


@pytest.mark.parametrize("route", USER_ROUTES, ids=_ids(USER_ROUTES))
def test_T16_rejected_bearer_strict_on_is_401(monkeypatch, stubs, client, route):
    """PIN T16: flag ON + ENABLE_STRICT_OPTIONAL_AUTH, a rejected bearer: 401
    AUTH_REQUIRED (get_optional_user raises first); zero calls."""
    _flags(monkeypatch, auth=True, strict=True)
    resp = _send(client, route, _headers(bearer=EXPIRED_JWT))
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls


def test_T16b_a_valid_bearer_wins_over_a_wrong_admin_key(monkeypatch, stubs, client):
    """PIN T16b(a) (C5): USER route, flag ON, valid bearer + X-Admin-Key wrong: passes
    AS THE USER (the admin header is consulted only when no user resolved), not 403."""
    _flags(monkeypatch, auth=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, ROUTE_BY_KEY["U1"], _headers(bearer=VALID_JWT, admin=WRONG_ADMIN))
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    assert stubs.count("text_routes.consume_comparison_credit") == 1, stubs.calls
    assert stubs.count("text_routes.compare_from_text") == 1, stubs.calls
    assert stubs.verify_token.await_count == 1


def test_T16b_b_rejected_bearer_plus_valid_admin_key_strict_off(monkeypatch, stubs, client):
    """PIN T16b(b) (C5): strict OFF, flag ON, rejected bearer + VALID admin key: an admin
    pass (runs like today's anonymous caller: no usage consumption)."""
    _flags(monkeypatch, auth=True, strict=False, admin_key=ADMIN_SENTINEL)
    resp = _send(client, ROUTE_BY_KEY["U1"], _headers(bearer=EXPIRED_JWT, admin=ADMIN_SENTINEL))
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])
    assert stubs.count("text_routes.compare_from_text") == 1, stubs.calls
    assert stubs.count("text_routes.consume_comparison_credit") == 0, stubs.calls


def test_T16b_c_rejected_bearer_plus_valid_admin_key_strict_on(monkeypatch, stubs, client):
    """PIN T16b(c) (C5): strict ON, flag ON, rejected bearer + valid admin key: 401
    AUTH_REQUIRED from get_optional_user before the guard body; the key cannot rescue a
    rejected bearer under strict."""
    _flags(monkeypatch, auth=True, strict=True, admin_key=ADMIN_SENTINEL)
    resp = _send(client, ROUTE_BY_KEY["U1"], _headers(bearer=EXPIRED_JWT, admin=ADMIN_SENTINEL))
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls


# ===========================================================================
# T17  flag OFF byte identity (UR11 fixture, record by record)
# ===========================================================================
@pytest.mark.parametrize("scenario", SCENARIO_NAMES)
def test_T17_flag_off_byte_identity(monkeypatch, scenario):
    """PIN T17 (UR11): flag, strict and metering unset; this scenario re-driven now
    equals its record in tests/fixtures/s71_u13_flag_off_baseline.json (recorded at base
    eb86075e by record_flag_off_baseline): status, content type, body (the joined SSE
    chunks for U3), stub call counts, fire_and_forget labels, verify_token awaits
    (USER: 1 per bearer request; ADMIN: 0 -- mutant X6)."""
    _flags(monkeypatch)
    doc = _load_fixture()
    meta = doc["_meta"]
    assert meta["recorder"] == RECORDER
    assert str(meta["recorded_at"]).startswith(BASE_SHA_PREFIX), meta["recorded_at"]
    assert meta["normalised_fields"] == NORMALISED_FIELDS
    records = doc["flag_off_records"]
    assert meta["records"] == len(records) == 30
    assert [r["scenario"] for r in records] == list(SCENARIO_NAMES)
    want = {r["scenario"]: r for r in records}[scenario]
    key, scen = scenario.split(".", 1)
    got = _record_one(monkeypatch, ROUTE_BY_KEY[key], scen)
    moved = {k: (want.get(k), got.get(k)) for k in sorted(set(got) | set(want))
             if got.get(k) != want.get(k)}
    assert not moved, f"{scenario} moved from the base recording: {moved!r}"


# ===========================================================================
# T18-T19  ordering and the limiter
# ===========================================================================
def test_T18a_guard_precedes_body_validation(monkeypatch, stubs, client):
    """RED T18a: flag ON, anonymous POST /text/compare with body {} -> 401 (base 422)."""
    _flags(monkeypatch, auth=True)
    resp = client.post("/api/v1/text/compare", json={}, headers=_headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls


def test_T18b_guard_precedes_query_validation(monkeypatch, stubs, client):
    """RED T18b: flag ON, anonymous GET /text/compare with q of 501 chars -> 401
    (base 422; tests/test_security_regression.py::TestQueryMaxLength's flag-ON twin)."""
    _flags(monkeypatch, auth=True)
    resp = client.get("/api/v1/text/compare", params={"q": "x" * 501}, headers=_headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls


def test_T18c_json_decode_precedes_the_guard(monkeypatch, stubs, client):
    """PIN T18c (L5, framework order): flag ON, anonymous POST /text/compare with a
    malformed JSON body -> 422 (pydantic `json_invalid`, msg "JSON decode error"), zero
    stub calls."""
    _flags(monkeypatch, auth=True)
    headers = _headers(extra={"Content-Type": "application/json"})
    resp = client.post("/api/v1/text/compare", content=b"{not json", headers=headers)
    body = _assert_envelope(resp, 422, "VALIDATION_ERROR")
    assert "JSON decode error" in body["error"], body
    assert stubs.calls == {}, stubs.calls


def test_T19_refusals_do_not_burn_the_bucket(monkeypatch, stubs, client):
    """RED T19: limiter reset and enabled; flag ON; 12 anonymous POST /text/compare
    (all 401) then one valid-bearer POST -> not 429 and the paid leg runs (mutant X5).
    Base: the anonymous calls consume 10/minute and the bearer call 429s."""
    from app.middleware.rate_limiter import limiter

    _flags(monkeypatch, auth=True)
    prior = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    try:
        anon = [client.post("/api/v1/text/compare", json={"query": QUERY},
                            headers=_headers()).status_code for _ in range(12)]
        bearer = client.post("/api/v1/text/compare", json={"query": QUERY},
                             headers=_headers(bearer=VALID_JWT))
    finally:
        limiter.reset()
        limiter.enabled = prior
    assert bearer.status_code != 429, (
        f"the valid-bearer compare was rate limited after 12 anonymous calls "
        f"(anonymous statuses {anon})")
    assert anon == [401] * 12, anon
    assert bearer.status_code == 200, (bearer.status_code, bearer.text[:300])
    assert stubs.count("text_routes.compare_from_text") == 1, stubs.calls


# ===========================================================================
# T20-T21  logging
# ===========================================================================
T20_SCENARIOS = {
    "anonymous": ("U1", {}, "POST /api/v1/text/compare", "NO_CREDENTIAL"),
    "rejected_bearer": ("U1", {"bearer": EXPIRED_JWT}, "POST /api/v1/text/compare",
                        "BEARER_REJECTED"),
    "wrong_admin_key": ("U1", {"admin": WRONG_ADMIN}, "POST /api/v1/text/compare",
                        "ADMIN_KEY_INVALID"),
    "valid_admin_key": ("U1", {"admin": ADMIN_SENTINEL}, "POST /api/v1/text/compare",
                        "admin credential accepted"),
    "prices_template": ("A2", {}, "GET /api/v1/text/prices/{product}", "NO_CREDENTIAL"),
}
SENT_HEADER_VALUES = (VALID_JWT, EXPIRED_JWT, f"Bearer {EXPIRED_JWT}", ADMIN_SENTINEL,
                      WRONG_ADMIN, REQUEST_ID, DEVICE_FP)


def _drive_t20(client, name):
    key, hkw, _label, _reason = T20_SCENARIOS[name]
    return _send(client, ROUTE_BY_KEY[key], _headers(**hkw), product=PRICE_SENTINEL)


def _paid_auth_records(records):
    return [r for r in records if "[paid-auth]" in r.getMessage()]


@pytest.mark.parametrize("name", list(T20_SCENARIOS))
def test_T20_refusal_log_line(monkeypatch, stubs, client, caplog, name):
    """RED T20 (D7, UR6): flag ON; exactly ONE INFO `[paid-auth]` record on the
    text_routes logger per request, naming the route TEMPLATE (`METHOD path`) and the
    reason (NO_CREDENTIAL / BEARER_REJECTED / ADMIN_KEY_INVALID), or "admin credential
    accepted" for an admin pass; GET /text/prices/IPHONE-U13-SENTINEL logs the template
    /api/v1/text/prices/{product}, never the concrete path."""
    _flags(monkeypatch, auth=True, strict=False, admin_key=ADMIN_SENTINEL)
    caplog.set_level(logging.INFO, logger="app.api.text_routes")
    _drive_t20(client, name)
    _key, _hkw, label, reason = T20_SCENARIOS[name]
    paid = [r for r in _paid_auth_records(caplog.records) if r.name == "app.api.text_routes"]
    assert len(paid) == 1, (
        f"{name}: expected exactly one [paid-auth] INFO record on app.api.text_routes, "
        f"got {[r.getMessage() for r in _paid_auth_records(caplog.records)]}")
    msg = paid[0].getMessage()
    assert paid[0].levelname == "INFO", paid[0].levelname
    assert label in msg and reason in msg, msg
    assert PRICE_SENTINEL not in msg, msg


def test_T21_nothing_secret_logged(monkeypatch, stubs, client, caplog):
    """RED T21 (C2 rewrite, UR6): across T20's five scenarios at DEBUG on all loggers:
    (a) NO record carries a bearer sentinel or an admin-key value; (b) no `[paid-auth]`
    record carries the query sentinel, IPHONE-U13-SENTINEL, `testclient` or any header
    value this test sent; (c) non-vacuity: each scenario produced at least one
    `[paid-auth]` record (mutant X7)."""
    _flags(monkeypatch, auth=True, strict=False, admin_key=ADMIN_SENTINEL)
    caplog.set_level(logging.DEBUG)
    per_scenario = {}
    all_records = []
    for name in T20_SCENARIOS:
        caplog.clear()
        _drive_t20(client, name)
        recs = list(caplog.records)
        all_records.extend(recs)
        per_scenario[name] = len(_paid_auth_records(recs))
    secrets = (VALID_JWT, EXPIRED_JWT, ADMIN_SENTINEL, WRONG_ADMIN)
    leaked = [(r.name, r.getMessage()[:160]) for r in all_records
              if any(s in r.getMessage() for s in secrets)]
    assert not leaked, leaked
    forbidden = (QUERY_SENTINEL, PRICE_SENTINEL, "testclient") + SENT_HEADER_VALUES
    bad = [r.getMessage() for r in _paid_auth_records(all_records)
           if any(f in r.getMessage() for f in forbidden)]
    assert not bad, bad
    assert all(n >= 1 for n in per_scenario.values()), (
        f"[paid-auth] records per scenario: {per_scenario}")


# ===========================================================================
# T22-T24  out of scope, OpenAPI, composition with metering
# ===========================================================================
def test_T22a_invitee_quiz_stays_anonymous(monkeypatch, client):
    """PIN T22a (UR2): flag ON, the invitee quiz POST (referral service stubbed) is
    not 401/403."""
    _flags(monkeypatch, auth=True, referral=True)
    from app.api import auth_routes, referral_routes

    calls = []

    class _Referral:
        async def run_invitee_quiz(self, **kw):
            calls.append(sorted(kw))
            return {"success": True, "u13": "quiz-stub"}

    monkeypatch.setattr(referral_routes, "ReferralService", _Referral)
    monkeypatch.setattr(auth_routes, "verify_token", AsyncMock(return_value=None))
    resp = client.post(
        "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
        json={"priority": "best_price", "budget": "mid", "brand_attitude": "function_first"},
        headers=_headers(),
    )
    assert resp.status_code not in (401, 403), (resp.status_code, resp.text[:300])
    assert resp.status_code == 200 and len(calls) == 1, (resp.status_code, calls)


def test_T22b_url_detect_admin_only_u13e(monkeypatch, stubs, client):
    """PIN T22b (UR2 superseded by U13e, W0 = guard): flag ON, anonymous GET /url/detect is 401."""
    _flags(monkeypatch, auth=True)
    resp = client.get("/api/v1/url/detect", params={"url": URL1}, headers=_headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert stubs.calls == {}, stubs.calls


def _referenced_components(snapshot):
    """UG1: the snapshot's `components` restricted to the transitive closure of the
    `$ref`s reachable from its ten operation objects, keyed by the `$ref` string. The
    same function runs on the recorded and the live snapshot, so a model no route of
    the ten uses can change without touching T23, while any change inside the closure
    still reddens it."""
    def _refs(node, out):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                out.append(ref)
            for value in node.values():
                _refs(value, out)
        elif isinstance(node, list):
            for value in node:
                _refs(value, out)

    closure = {}
    pending = []
    _refs(snapshot["operations"], pending)
    while pending:
        ref = pending.pop()
        if ref in closure:
            continue
        node = {"components": snapshot["components"]}
        for part in ref.lstrip("#/").split("/"):
            node = node.get(part) if isinstance(node, dict) else None
        closure[ref] = node
        _refs(node, pending)
    return closure


@pytest.mark.parametrize("route", ROUTES, ids=_ids(ROUTES))
def test_T23_openapi_unchanged(monkeypatch, route):
    """PIN T23 (C4, UG1): the FULL operation JSON (sort_keys) of the route, and the
    schema's `components` restricted to the transitive closure of the `$ref`s reachable
    from the ten operations (computed the same way on both sides), equal the base
    recording in the UR11 fixture (so the parameter sets of spec 2.4 hold, and no
    security/response/tag drift). app.openapi_schema is rebuilt fresh and restored."""
    _flags(monkeypatch)
    doc = _load_fixture()
    want = doc["openapi"]
    got = _openapi_snapshot()
    op_key = f"{route.method} {route.path}"
    assert json.dumps(got["operations"][op_key], sort_keys=True) == json.dumps(
        want["operations"][op_key], sort_keys=True), op_key
    want_closure = _referenced_components(want)
    assert want_closure, "non-vacuity: the ten operations reference no component"
    assert json.dumps(_referenced_components(got), sort_keys=True) == json.dumps(
        want_closure, sort_keys=True)


def test_T24_prices_composition_with_metering(monkeypatch, stubs, client):
    """RED T24: flag ON + ENABLE_PAID_ROUTE_METERING: anonymous GET /text/prices -> 401
    AUTH_REQUIRED (not the in-handler 403), nothing called; a valid admin key -> 200 and
    get_regional_prices called once (the W2-1 in-handler check still passes)."""
    _flags(monkeypatch, auth=True, meter=True, admin_key=ADMIN_SENTINEL)
    route = ROUTE_BY_KEY["A2"]
    anon = _send(client, route, _headers())
    _assert_envelope(anon, 401, "AUTH_REQUIRED")
    assert stubs.calls == {}, stubs.calls
    admin = _send(client, route, _headers(admin=ADMIN_SENTINEL))
    assert admin.status_code == 200, (admin.status_code, admin.text[:300])
    assert stubs.count("text_routes.get_regional_prices") == 1, stubs.calls


# ---------------------------------------------------------------------------
# recorder entry point (UR11): python -m tests.test_s71_u13_compare_auth_required
# ---------------------------------------------------------------------------
def _main(argv):
    import argparse

    ap = argparse.ArgumentParser(description="U13 flag-OFF baseline recorder (UR11)")
    ap.add_argument("--record", required=True, help="output JSON path")
    ap.add_argument("--recorded-at", required=True, help="the base commit sha")
    args = ap.parse_args(argv)
    doc = record_flag_off_baseline(args.record, args.recorded_at)
    print(f"[u13-recorder] wrote {len(doc['flag_off_records'])} records to {args.record}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

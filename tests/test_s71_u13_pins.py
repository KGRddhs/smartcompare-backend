"""U13 supplementary pins P1-P4 (ENABLE_COMPARE_AUTH_REQUIRED), ruling UF2 of
docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md. The code under
test is correct, so every node PASSES at HEAD; each pin names the mutant it kills (each
kill was proved: byte copy, mutate, run, FAIL, restore, sha256 equal).
  P1 exact admin key: MF (case-insensitive prefix match), MA (plain == compare).
  P2 flag OFF never reads the admin header: XA / XB (the flag check of either guard
     moved below the _admin_credential_passes call).
  P3 refusal reasons + label fallback: MR (ADMIN_REQUIRED logged as NO_CREDENTIAL),
     ML (the "?" fallback of _paid_route_label -> the concrete path).
  P4 the redirect keyword: MD (allow_redirects removed from run_query, UF1).
Fix round after the pins adversary (same file, test-only):
  P1 an unconfigured key never admits an empty or absent header: EMPTYKEY.
  P1 near-miss keys padded with one space: STRIP (the supplied value stripped).
  P3 the no-secret check captures DEBUG on all loggers: LEAKDBG (the bearer logged
     at DEBUG on the ADMIN_REQUIRED path).

Conventions copied (not imported) from tests/test_s71_u13_compare_auth_required.py:
paid and side-effect legs stubbed at text_routes' import names, verify_token an
AsyncMock, every node sets or deletes EVERY flag it reads (`_flags`, ADMIN_API_KEY
included), a fixed X-Request-ID, no app.* import at module top, plain-word sentinels.
USER route = POST /api/v1/text/compare (U1); ADMIN route = GET /api/v1/text/prices/{product}.
"""
from __future__ import annotations

import copy
import importlib.util
import logging
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAG = "ENABLE_COMPARE_AUTH_REQUIRED"
ADMIN_ENV = "ADMIN_API_KEY"
HARNESS_OPT_IN = "HARNESS_SEND_ADMIN_KEY"
# Every env name the two routes, the guards or the harness helper read per call; all are
# deleted before every node, then the node sets what it needs.
CLEAN_ENV = (
    FLAG, ADMIN_ENV, HARNESS_OPT_IN,
    "ENABLE_STRICT_OPTIONAL_AUTH", "ENABLE_PAID_ROUTE_METERING", "ENABLE_ANON_USAGE_GATE",
    "ENABLE_CAMERA_FAILURE_ENVELOPE", "SEARCH_LOG_SYNTHETIC_TOKEN", "ENABLE_REFERRAL_SYSTEM",
    "ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
    "ENABLE_COMPARISON_ID_ECHO", "ENABLE_PREVERDICT_DISCONNECT_ABORT",
    "ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_OFFLOOP_DNS_RESOLVE",
    "ENABLE_PROXY_AWARE_RATELIMIT", "ENABLE_ARABIC_VERDICT_OUTPUT",
)

ADMIN_SENTINEL = "u13-pins-admin-sentinel"
WRONG_ADMIN = "u13-pins-wrong-admin"
VALID_JWT = "u13.pins.valid.jwt"
BASIC_CRED = "u13pinsbasiccredential"
REQUEST_ID = "u13-pins-fixed-request-id"
PRODUCT = "U13PINSPRODUCT"
QUERY = "U13PINSQUERY alpha vs U13PINSQUERY beta"
USER = {"id": "u13-pins-user", "email": "u13-pins@example.invalid", "access_token": VALID_JWT}
AUTH_TEXT = "Sign in to continue."

COMPARE_RESULT = {"success": True, "metadata": {"total_cost": 0.0},
                  "products": [{"brand": "U13", "name": "alpha"}, {"brand": "U13", "name": "beta"}]}
ASYNC_STUBS = {
    "get_regional_prices": {"prices": {"bahrain": None}, "u13": "regional-prices-stub"},
    "consume_comparison_credit": {"allowed": True, "reason": None, "tier": "free", "consumed": True,
                                  "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2}},
    "check_anon_usage_allowed": {"allowed": True, "reason": None, "tier": "free", "consumed": False,
                                 "remaining": {"daily": 2, "monthly": 9}},
    "get_user_preferences": {"success": True, "preferences_completed": False},
}
PLAIN_STUBS = ("refund_comparison_credit", "record_lifetime_comparison", "record_anon_comparison",
               "log_search", "save_comparison_and_track_cohort")

KINDS = ("user", "admin")
PROVIDER = {"user": "compare_from_text", "admin": "get_regional_prices"}
METHOD = {"user": "POST", "admin": "GET"}
# P1 near-miss keys. The sentinel starts with a letter, so the case flip really differs.
# The two padded keys differ from the sentinel only by one space (kills STRIP: a guard
# that strips the supplied value; the test client delivers the space to the app).
P1_VARIANTS = {
    "minus_last_char": ADMIN_SENTINEL[:-1],
    "first_char_only": ADMIN_SENTINEL[:1],
    "one_char_case_flipped": ADMIN_SENTINEL[0].swapcase() + ADMIN_SENTINEL[1:],
    "plus_one_char": ADMIN_SENTINEL + "x",
    "leading_space": " " + ADMIN_SENTINEL,
    "trailing_space": ADMIN_SENTINEL + " ",
}
PADDED_VARIANTS = ("leading_space", "trailing_space")


def _flags(mp, *, auth=None, admin_key=None):
    """Set or delete EVERY flag a node depends on; `auth` is the raw flag value."""
    for name in CLEAN_ENV:
        mp.delenv(name, raising=False)
    if auth is not None:
        mp.setenv(FLAG, auth)
    if admin_key is not None:
        mp.setenv(ADMIN_ENV, admin_key)


@pytest.fixture(autouse=True)
def _pins_clean_env_and_limiter(monkeypatch):
    _flags(monkeypatch)
    from app.middleware.rate_limiter import limiter
    limiter.reset()
    yield  # pytest runs the teardown below whatever the node's outcome
    limiter.reset()


@pytest.fixture
def stubs(monkeypatch):
    """Every paid / usage / prefs / anon-gate / log / persist leg of the two routes,
    stubbed at text_routes' import names (calls counted in `calls`); verify_token is an
    AsyncMock that resolves VALID_JWT only."""
    from app.api import auth_routes, text_routes

    calls = Counter()

    def _async(name, value):
        async def _stub(*_a, **_k):
            calls[name] += 1
            return copy.deepcopy(value)
        return _stub

    def _plain(name):
        def _stub(*_a, **_k):
            calls[name] += 1
            return ("u13-pins-stub-call", name)
        return _stub

    def _ff(coro, label=None, *_a, **_k):
        calls["fire_and_forget"] += 1
        if hasattr(coro, "close"):
            coro.close()

    def _get_service(*_a, **_k):
        calls["get_comparison_service"] += 1
        return SimpleNamespace(compare_from_text=_async("compare_from_text", COMPARE_RESULT))

    async def _verify(token, *_a, **_k):
        return dict(USER) if token == VALID_JWT else None

    st = SimpleNamespace(calls=calls, verify_token=AsyncMock(side_effect=_verify))
    monkeypatch.setattr(auth_routes, "verify_token", st.verify_token)
    monkeypatch.setattr(text_routes, "get_comparison_service", _get_service)
    monkeypatch.setattr(text_routes, "fire_and_forget", _ff)
    for name, value in ASYNC_STUBS.items():
        monkeypatch.setattr(text_routes, name, _async(name, value))
    for name in PLAIN_STUBS:
        monkeypatch.setattr(text_routes, name, _plain(name))
    return st


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _headers(*, admin=None, authorization=None):
    h = {"X-Request-ID": REQUEST_ID, "X-Admin-Key": admin, "Authorization": authorization}
    return {k: v for k, v in h.items() if v is not None}


def _send(client, kind, headers):
    if kind == "user":
        return client.post("/api/v1/text/compare", json={"query": QUERY}, headers=headers)
    return client.get(f"/api/v1/text/prices/{PRODUCT}", headers=headers)


def _assert_envelope(resp, status, code):
    assert resp.status_code == status, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert body["success"] is False and body["code"] == code, body
    assert body["request_id"] == REQUEST_ID, body
    return body


# --- P1  exact admin key (kills MF, MA, EMPTYKEY and STRIP) --------------------------
def test_P1_text_routes_reuses_admin_routes_verify_admin_key():
    """P1: the guard's comparison IS admin_routes.verify_admin_key (bytes, surrogateescape,
    hmac.compare_digest), never a local re-implementation (MA, MF)."""
    from app.api import admin_routes, text_routes
    assert text_routes.verify_admin_key is admin_routes.verify_admin_key


@pytest.mark.parametrize("variant", list(P1_VARIANTS))
@pytest.mark.parametrize("kind", KINDS)
def test_P1_near_miss_admin_key_is_403(monkeypatch, stubs, client, kind, variant):
    """P1: flag ON, ADMIN_API_KEY = sentinel; a near-miss X-Admin-Key (prefix, first
    character, one case flip, one extra character, one leading or trailing space) is
    403 FORBIDDEN, zero stub calls."""
    value = P1_VARIANTS[variant]
    assert value and value != ADMIN_SENTINEL, value
    if variant == "one_char_case_flipped":
        assert value.lower() == ADMIN_SENTINEL.lower(), value
    if variant in PADDED_VARIANTS:
        assert value.strip() == ADMIN_SENTINEL, value
    _flags(monkeypatch, auth="true", admin_key=ADMIN_SENTINEL)
    _assert_envelope(_send(client, kind, _headers(admin=value)), 403, "FORBIDDEN")
    assert stubs.calls == {}, stubs.calls
    assert stubs.verify_token.await_count == 0


@pytest.mark.parametrize("header", ["absent", "empty"])
@pytest.mark.parametrize("configured", [None, ""], ids=["admin_key_unset", "admin_key_empty"])
@pytest.mark.parametrize("kind", KINDS)
def test_P1_unconfigured_key_never_admits_an_empty_header(monkeypatch, stubs, client, kind,
                                                          configured, header):
    """P1 (fix round, kills EMPTYKEY): flag ON, ADMIN_API_KEY unset or empty, no
    Authorization, X-Admin-Key absent or empty: 401 AUTH_REQUIRED, zero stub calls, no
    bearer resolved. The emptiness guard runs before any compare, because
    compare_digest(b"", b"") is True."""
    _flags(monkeypatch, auth="true", admin_key=configured)
    resp = _send(client, kind, _headers(admin="" if header == "empty" else None))
    assert _assert_envelope(resp, 401, "AUTH_REQUIRED")["error"] == AUTH_TEXT
    assert stubs.calls == {}, stubs.calls
    assert stubs.verify_token.await_count == 0


@pytest.mark.parametrize("supplied", ["exact", "wrong"])
@pytest.mark.parametrize("kind", KINDS)
def test_P1_exact_key_passes_and_reaches_verify_admin_key_once(monkeypatch, stubs, client,
                                                               kind, supplied):
    """P1: the exact sentinel passes (paid leg once, no bearer resolved) and a wrong key is
    403; a spy on text_routes.verify_admin_key sees the supplied header value exactly once
    per request (no inline compare beside it, no second call)."""
    from app.api import text_routes

    _flags(monkeypatch, auth="true", admin_key=ADMIN_SENTINEL)
    real = text_routes.verify_admin_key
    seen = []

    def _spy(value, *a, **k):
        seen.append(value)
        return real(value, *a, **k)

    monkeypatch.setattr(text_routes, "verify_admin_key", _spy)
    value = ADMIN_SENTINEL if supplied == "exact" else WRONG_ADMIN
    resp = _send(client, kind, _headers(admin=value))
    assert seen == [value], seen
    assert stubs.verify_token.await_count == 0
    if supplied == "exact":
        assert resp.status_code == 200, (resp.status_code, resp.text[:300])
        assert stubs.calls[PROVIDER[kind]] == 1, stubs.calls
    else:
        _assert_envelope(resp, 403, "FORBIDDEN")
        assert stubs.calls == {}, stubs.calls


# --- P2  flag OFF never consults the admin header (kills XA and XB) -----------------
def _spy_admin_credential(mp):
    """Wrap the real _admin_credential_passes (behaviour unchanged, node-scoped through
    monkeypatch) and return the list of recorded calls (the request method)."""
    from app.api import text_routes

    real, calls = text_routes._admin_credential_passes, []

    def _spy(request):
        calls.append(request.method)
        return real(request)

    mp.setattr(text_routes, "_admin_credential_passes", _spy)
    return calls


@pytest.mark.parametrize("key", ["valid_key", "wrong_key"])
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("flag", [None, "false"], ids=["flag_unset", "flag_false"])
def test_P2_flag_off_never_consults_admin_header(monkeypatch, stubs, client, flag, kind, key):
    """P2: flag unset or "false", every other flag unset: with an X-Admin-Key (valid or
    wrong) the guard never calls _admin_credential_passes, and status, body and stub calls
    equal those of the same request without the header."""
    _flags(monkeypatch, auth=flag, admin_key=ADMIN_SENTINEL)
    spy_calls = _spy_admin_credential(monkeypatch)
    plain = _send(client, kind, _headers())
    plain_calls = dict(stubs.calls)
    stubs.calls.clear()
    keyed = _send(client, kind, _headers(admin=ADMIN_SENTINEL if key == "valid_key" else WRONG_ADMIN))
    assert spy_calls == [], f"flag OFF consulted the admin header: {spy_calls}"
    assert plain.status_code == 200, (plain.status_code, plain.text[:300])
    assert keyed.status_code == plain.status_code, (keyed.status_code, keyed.text[:300])
    assert keyed.content == plain.content, (keyed.text[:300], plain.text[:300])
    assert dict(stubs.calls) == plain_calls, (stubs.calls, plain_calls)
    assert plain_calls.get(PROVIDER[kind]) == 1, plain_calls


@pytest.mark.parametrize("kind", KINDS)
def test_P2_control_spy_sees_flag_on(monkeypatch, stubs, client, kind):
    """P2 non-vacuity: the same spy, flag ON, valid key -> exactly one call and a pass,
    so the zero-call assertion above watches the real call path."""
    _flags(monkeypatch, auth="true", admin_key=ADMIN_SENTINEL)
    spy_calls = _spy_admin_credential(monkeypatch)
    resp = _send(client, kind, _headers(admin=ADMIN_SENTINEL))
    assert spy_calls == [METHOD[kind]], spy_calls
    assert resp.status_code == 200, (resp.status_code, resp.text[:300])


# --- P3  refusal reasons and the label fallback (kills MR, ML and LEAKDBG) ----------
@pytest.mark.parametrize("kind, authorization, expected", [
    ("admin", f"Bearer {VALID_JWT}",
     "[paid-auth] refused route=GET /api/v1/text/prices/{product} reason=ADMIN_REQUIRED"),
    ("user", f"Basic {BASIC_CRED}",
     "[paid-auth] refused route=POST /api/v1/text/compare reason=BEARER_REJECTED"),
], ids=["bearer_only_on_admin_route", "basic_scheme_on_user_route"])
def test_P3_refusal_reason(monkeypatch, stubs, client, caplog, kind, authorization, expected):
    """P3: flag ON, strict OFF. A bearer-only caller (even a VALID bearer) on the ADMIN
    route, and an `Authorization: Basic` header on the USER route: 401 AUTH_REQUIRED,
    verify_token never awaited, zero stub calls, exactly one [paid-auth] record with
    reason ADMIN_REQUIRED / BEARER_REJECTED; no record, captured at DEBUG on all loggers
    (as T21), carries the header value (kills LEAKDBG)."""
    _flags(monkeypatch, auth="true", admin_key=ADMIN_SENTINEL)
    caplog.set_level(logging.DEBUG)
    resp = _send(client, kind, _headers(authorization=authorization))
    assert _assert_envelope(resp, 401, "AUTH_REQUIRED")["error"] == AUTH_TEXT
    assert stubs.verify_token.await_count == 0
    assert stubs.calls == {}, stubs.calls
    messages = [r.getMessage() for r in caplog.records]
    assert [m for m in messages if "[paid-auth]" in m] == [expected], messages
    secret = authorization.split(" ", 1)[1]
    assert not [m for m in messages if secret in m], "a log record carries the header value"


@pytest.mark.parametrize("case, method", [
    ("no_route_in_scope", "GET"), ("empty_template", "POST"), ("non_string_template", "GET"),
])
def test_P3_label_fallback_is_question_mark(case, method):
    """P3: _paid_route_label returns "<METHOD> ?" when the scope carries no route or the
    route template is empty / not a string -- never the concrete request path."""
    from starlette.requests import Request

    from app.api import text_routes

    path = f"/api/v1/text/prices/{PRODUCT}"
    scope = {"type": "http", "method": method, "path": path, "raw_path": path.encode(),
             "root_path": "", "scheme": "http", "server": ("testserver", 80),
             "query_string": b"", "headers": []}
    if case != "no_route_in_scope":
        scope["route"] = SimpleNamespace(path="" if case == "empty_template" else None)
    label = text_routes._paid_route_label(Request(scope))
    assert label == f"{method} ?", label


# --- P4  the redirect keyword (kills MD) ---------------------------------------------
def _load_validation_matrix():
    path = REPO_ROOT / "scripts" / "run_validation_matrix.py"
    spec = importlib.util.spec_from_file_location("_s71_u13_pins_run_validation_matrix", path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.mark.parametrize("opt_in", ["1", "true", "yes", "on"])
def test_P4_validation_matrix_opted_in_never_follows_redirects(monkeypatch, opt_in):
    """P4: opted in, run_query's captured requests.get keywords are exactly params,
    timeout, headers and allow_redirects False (requests forwards X-Admin-Key across a
    cross-host redirect, UF1). The not-opted-in shape is pinned by H06."""
    import requests as real_requests

    _flags(monkeypatch, admin_key=ADMIN_SENTINEL)
    monkeypatch.setenv(HARNESS_OPT_IN, opt_in)
    mod = _load_validation_matrix()
    captured = []

    def _get(url, **kwargs):  # a 503 answer: run_query never reads a body
        captured.append((url, kwargs))
        return SimpleNamespace(status_code=503)

    monkeypatch.setattr(mod, "requests", SimpleNamespace(
        get=_get, RequestException=real_requests.RequestException))
    record = {"id": "u13-pins-1", "query": "a vs b", "category": "electronics", "region": "bahrain"}
    weights = {"price_accuracy": 0.25, "specs_correctness": 0.25,
               "winner_correctness": 0.30, "factual_claim_integrity": 0.20}
    mod.run_query("http://u13-pins.test", record, weights, 15.0, 5.0)
    assert len(captured) == 1, captured
    url, kwargs = captured[0]
    assert url == "http://u13-pins.test/api/v1/text/compare", url
    assert set(kwargs) == {"params", "timeout", "headers", "allow_redirects"}, sorted(kwargs)
    assert kwargs["allow_redirects"] is False, kwargs["allow_redirects"]
    assert kwargs["headers"] == {"X-Admin-Key": ADMIN_SENTINEL}, sorted(kwargs["headers"])

"""U13e -- /api/v1/url/detect joins the admin-only paid-route guard (+ #304). U13e pins.

Spec (authoritative, the later wins): s74-state/specs/U13E_SPEC.md section 4.1,
U13E_REVIEW.md, FABLE_RULINGS_U13E.md U1-U10 (BINDING). Node ids E01-E14 and W01-W07
are in every node name. Expected at base fdbfa2e7: 47 nodes = 26 RED + 21 PIN.
The post-adversary rulings U11/U12 add 13 nodes (60 in all): W01 +4, W04 +3, W05b +3
and W07b +3, each RED on its byte-copy mutant of the #304 strip sites.

Contract (spec section 2): with ENABLE_COMPARE_AUTH_REQUIRED truthy both detect verbs
need the admin credential (X-Admin-Key) and refuse everything else with the paid-route
401 / 403 envelope BEFORE the SSRF validator resolves DNS on the event loop; flag OFF
they are byte-identical to base. #304: a whitespace-only ADMIN_API_KEY counts as unset
at both env read sites (admin_routes.verify_admin_key and the /admin static mount);
the compare stays RAW against the unstripped value (U4, W07).

Conventions:
  * hermetic: the validator (`url_routes._validate_url_offloop_or_sync`) is a counting
    async stub with a configurable result (E09 alone runs the REAL validator over a
    `socket.getaddrinfo` recorder), `url_routes.detect_retailer` a counting wrapper
    over the real one, `url_routes.extract_from_url` a counting stub and
    `auth_routes.verify_token` an AsyncMock;
  * no `app.*` import at module top and the guards are matched by `__name__`, so a RED
    is a test failure, never a collection error;
  * the autouse fixture imports app.main BEFORE it deletes the env names (U9: the
    first import runs load_dotenv(override=True)) and resets the limiter before and
    after every node;
  * the admin sentinel and every key value are built at runtime (concatenation or
    chr); a fixed X-Request-ID on every request; pure ASCII.
"""
from __future__ import annotations

import base64
import json
import logging
import socket
from collections import Counter
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from tests._route_introspection import assert_route_table_visible, find_route

# ---------------------------------------------------------------------------
# names and sentinels
# ---------------------------------------------------------------------------
FLAG = "ENABLE_COMPARE_AUTH_REQUIRED"
METER = "ENABLE_PAID_ROUTE_METERING"
ADMIN_ENV = "ADMIN_API_KEY"
CLEAN_ENV = (
    FLAG, METER, "ENABLE_STRICT_OPTIONAL_AUTH", "ENABLE_OFFLOOP_DNS_RESOLVE",
    "ENABLE_PROXY_AWARE_RATELIMIT", "HARNESS_SEND_ADMIN_KEY", ADMIN_ENV,
)

ADMIN_GUARD = "require_paid_route_admin"
USER_GUARD = "require_paid_route_user"
TEXT_LOGGER = "app.api.text_routes"
AUTH_TEXT = "Sign in to continue."
FORBIDDEN_TEXT = "Invalid admin key"
BLOCKED_TEXT = "URL blocked by security policy"
NOT_CONFIGURED = "Admin not configured"

ADMIN = "u13e-admin-" + "sentinel"
WRONG = "u13e-wrong-" + "key"
BEARER = "u13e." + "bearer.jwt"
NL = chr(10)
WS3 = " " * 3
WS_ENVS = {"spaces3": WS3, "tab": chr(9), "space_newline_space": " " + NL + " "}
# U11: W01 adds the non-ASCII and the non-SP/HTAB/LF whitespace str.strip() also removes
# (NBSP, NEL, CRLF, VT); the /admin static-mount Basic leg (W04) and W05b add tab and NBSP
# (the tab key is WS_ENVS["tab"] already, so the dict keeps one tab node).
W01_ENVS = {**WS_ENVS, "nbsp": chr(0xA0), "nel": chr(0x85), "crlf": chr(13) + NL,
            "vt": chr(11)}
STATIC_WS_ENVS = {**WS_ENVS, "tab": chr(9), "nbsp": chr(0xA0)}
REQUEST_ID = "u13e-fixed-request-id"
HOST = "u13e-one.example.invalid"
URL = "https://" + HOST + "/p/1"
PUBLIC_IP = "93.184.216.34"
DETECT = "/api/v1/url/detect"
EXTRACT = "/api/v1/url/extract"
ADMIN_PAGE = "/admin/costs.html"
VERBS = ("GET", "POST")

# E13 (U10 / review n6): the two detect operation objects of the base OpenAPI
# document (base sha256 888f7350...41aa5d, byte-identical on the patched copy).
_RESPONSES = {
    "200": {"content": {"application/json": {"schema": {}}},
            "description": "Successful Response"},
    "422": {"content": {"application/json": {"schema": {
        "$ref": "#/components/schemas/HTTPValidationError"}}},
        "description": "Validation Error"},
}
BASE_DETECT_OPS = {
    "get": {
        "description": "GET version of detect for easy testing.",
        "operationId": "detect_retailer_get_api_v1_url_detect_get",
        "parameters": [{
            "description": "URL to detect retailer", "in": "query", "name": "url",
            "required": True,
            "schema": {"description": "URL to detect retailer", "title": "Url",
                       "type": "string"},
        }],
        "responses": _RESPONSES,
        "summary": "Detect Retailer Get",
        "tags": ["url-comparison"],
    },
    "post": {
        "description": ("Detect retailer from URL without full extraction." + NL + NL
                        + "Useful for validating URLs before processing."),
        "operationId": "detect_retailer_endpoint_api_v1_url_detect_post",
        "requestBody": {"content": {"application/json": {"schema": {
            "$ref": "#/components/schemas/URLExtractRequest"}}}, "required": True},
        "responses": _RESPONSES,
        "summary": "Detect Retailer Endpoint",
        "tags": ["url-comparison"],
    },
}


# ---------------------------------------------------------------------------
# env, legs, client, requests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _u13e_clean_env_and_limiter(monkeypatch):
    import app.main  # noqa: F401  (U9: load_dotenv runs at first import, before delenv)
    for name in CLEAN_ENV:
        monkeypatch.delenv(name, raising=False)
    from app.middleware.rate_limiter import limiter
    limiter.reset()
    try:
        yield
    finally:
        limiter.reset()


def _env(mp, *, auth=None, meter=None, admin_key=None):
    """On top of the clean fixture, set exactly what a node needs (None = unset)."""
    if auth is not None:
        mp.setenv(FLAG, auth)
    if meter is not None:
        mp.setenv(METER, meter)
    if admin_key is not None:
        mp.setenv(ADMIN_ENV, admin_key)


def _real_detect(url):
    from app.services.url_extraction_service import detect_retailer
    return detect_retailer(url)


class _Legs:
    """Counting stubs for every leg /url/detect and /url/extract can reach."""

    def __init__(self, mp, *, valid=True, real_validator=False):
        from app.api import auth_routes, url_routes

        self.valid = valid
        self.v = 0
        self.r = 0
        self.extract = 0

        async def _validator(_url, *_a, **_k):
            self.v += 1
            return self.valid

        def _detect(url, *a, **k):
            self.r += 1
            return _real_detect(url, *a, **k)

        async def _extract(*_a, **_k):
            self.extract += 1
            return {"success": True, "product": {"brand": "U13E", "name": "one"}}

        self.verify_token = AsyncMock(
            return_value={"id": "u13e-user", "email": "u13e@example.invalid"})
        if not real_validator:
            mp.setattr(url_routes, "_validate_url_offloop_or_sync", _validator)
        mp.setattr(url_routes, "detect_retailer", _detect)
        mp.setattr(url_routes, "extract_from_url", _extract)
        mp.setattr(auth_routes, "verify_token", self.verify_token)

    def reset(self):
        self.v = 0
        self.r = 0
        self.extract = 0


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _headers(*, admin=None, bearer=None, basic_password=None):
    h = {"X-Request-ID": REQUEST_ID}
    if admin is not None:
        h["X-Admin-Key"] = admin
    if bearer is not None:
        h["Authorization"] = "Bearer " + bearer
    if basic_password is not None:
        raw = ("u13e:" + basic_password).encode("utf-8")
        h["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    return h


def _detect(client, verb, headers, *, url=URL):
    if verb == "GET":
        return client.get(DETECT, params={"url": url}, headers=headers)
    return client.post(DETECT, json={"url": url}, headers=headers)


def _ok_body(url=URL):
    retailer = _real_detect(url)
    return {"url": url, "retailer": retailer, "supported": retailer["key"] != "unknown"}


def _assert_envelope(resp, status, code, error):
    assert resp.status_code == status, (
        f"status {resp.status_code} != expected {status}: {ascii(resp.text[:300])}")
    ctype = resp.headers.get("content-type", "")
    assert ctype.startswith("application/json"), ctype
    body = resp.json()
    want = {"success": False, "error": error, "code": code, "request_id": REQUEST_ID}
    assert body == want, body
    return body


def _paid_auth(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == TEXT_LOGGER and "[paid-auth]" in r.getMessage()]


def _assert_paid_auth(caplog, want):
    got = _paid_auth(caplog)
    assert got == want, f"[paid-auth] records on {TEXT_LOGGER}: expected {want}, got {got}"


def _refused(verb, reason):
    return f"[paid-auth] refused route={verb} {DETECT} reason={reason}"


def _accepted(verb):
    return f"[paid-auth] admin credential accepted route={verb} {DETECT}"


def _dependant_call_names(dependant):
    names = []
    stack = list(getattr(dependant, "dependencies", None) or [])
    while stack:
        dep = stack.pop()
        call = getattr(dep, "call", None)
        names.append(getattr(call, "__name__", repr(call)))
        stack.extend(getattr(dep, "dependencies", None) or [])
    return names


def _debug_on_all_loggers(caplog):
    """DEBUG on the root and on every known logger; caplog's handler is added to the
    non-propagating ones (returned, so the caller removes it again)."""
    caplog.set_level(logging.DEBUG)
    attached = []
    for name in sorted(logging.root.manager.loggerDict):
        caplog.set_level(logging.DEBUG, logger=name)
        lg = logging.getLogger(name)
        if not lg.propagate and caplog.handler not in lg.handlers:
            lg.addHandler(caplog.handler)
            attached.append(lg)
    return attached


# ===========================================================================
# E01-E14  /url/detect behind require_paid_route_admin
# ===========================================================================
@pytest.mark.parametrize("verb", VERBS)
def test_E01_detect_dependant_tree_carries_the_admin_guard(verb):
    """RED E01: the detect route's dependant tree carries exactly ONE call named
    require_paid_route_admin and none named require_paid_route_user."""
    from app.main import app
    assert_route_table_visible(app)
    entry = find_route(app, DETECT, verb)
    assert entry is not None, f"{verb} {DETECT} not mounted"
    names = _dependant_call_names(entry.route.dependant)
    assert names.count(ADMIN_GUARD) == 1, (
        f"{verb} {DETECT}: {ADMIN_GUARD} occurs {names.count(ADMIN_GUARD)} times in the "
        f"dependant tree {sorted(names)}")
    assert names.count(USER_GUARD) == 0, sorted(names)


@pytest.mark.parametrize("verb", VERBS)
def test_E02_anonymous_refused_before_the_validator(monkeypatch, caplog, verb):
    """RED E02 (C1): flag ON, ADMIN_API_KEY set, no credential: the exact 401
    AUTH_REQUIRED envelope; validator 0, detect_retailer 0, verify_token 0."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    caplog.set_level(logging.INFO, logger=TEXT_LOGGER)
    resp = _detect(_client(), verb, _headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert (legs.v, legs.r, legs.verify_token.await_count) == (0, 0, 0), (
        legs.v, legs.r, legs.verify_token.await_count)
    _assert_paid_auth(caplog, [_refused(verb, "NO_CREDENTIAL")])


@pytest.mark.parametrize("verb", VERBS)
def test_E03_empty_admin_header_is_no_credential(monkeypatch, caplog, verb):
    """RED E03 (C2): flag ON, X-Admin-Key "" is refused exactly like no credential."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    caplog.set_level(logging.INFO, logger=TEXT_LOGGER)
    resp = _detect(_client(), verb, _headers(admin=""))
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert (legs.v, legs.r, legs.verify_token.await_count) == (0, 0, 0), (
        legs.v, legs.r, legs.verify_token.await_count)
    _assert_paid_auth(caplog, [_refused(verb, "NO_CREDENTIAL")])


@pytest.mark.parametrize("verb", VERBS)
def test_E04_bearer_only_is_admin_required(monkeypatch, caplog, verb):
    """RED E04 (C3): flag ON, a bearer and no admin key: 401 AUTH_REQUIRED, the bearer
    is never resolved (verify_token 0), exactly one refused ... reason=ADMIN_REQUIRED."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    caplog.set_level(logging.INFO, logger=TEXT_LOGGER)
    resp = _detect(_client(), verb, _headers(bearer=BEARER))
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert legs.verify_token.await_count == 0, legs.verify_token.await_count
    assert (legs.v, legs.r) == (0, 0), (legs.v, legs.r)
    _assert_paid_auth(caplog, [_refused(verb, "ADMIN_REQUIRED")])


@pytest.mark.parametrize("verb", VERBS)
def test_E05_wrong_admin_key_is_403(monkeypatch, caplog, verb):
    """RED E05 (C4): flag ON, a wrong non-empty key: 403 FORBIDDEN "Invalid admin key";
    validator 0, detect_retailer 0; reason ADMIN_KEY_INVALID."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    caplog.set_level(logging.INFO, logger=TEXT_LOGGER)
    resp = _detect(_client(), verb, _headers(admin=WRONG))
    _assert_envelope(resp, 403, "FORBIDDEN", FORBIDDEN_TEXT)
    assert (legs.v, legs.r) == (0, 0), (legs.v, legs.r)
    _assert_paid_auth(caplog, [_refused(verb, "ADMIN_KEY_INVALID")])


@pytest.mark.parametrize("verb", VERBS)
def test_E06_admin_key_passes_with_the_flag_off_response(monkeypatch, caplog, verb):
    """RED E06 (C5, validator True): flag ON + the right key: status and body equal the
    flag-OFF anonymous response of the same request; validator 1, detect_retailer 1;
    exactly one "admin credential accepted route=<VERB> /api/v1/url/detect"."""
    _env(monkeypatch, admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    client = _client()
    ref = _detect(client, verb, _headers())
    assert ref.status_code == 200, (ref.status_code, ascii(ref.text[:300]))
    assert ref.json() == _ok_body(), ref.json()
    legs.reset()
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.INFO, logger=TEXT_LOGGER)
    caplog.clear()
    resp = _detect(client, verb, _headers(admin=ADMIN))
    assert (resp.status_code, resp.json()) == (ref.status_code, ref.json()), (
        resp.status_code, ascii(resp.text[:300]))
    assert (legs.v, legs.r) == (1, 1), (legs.v, legs.r)
    _assert_paid_auth(caplog, [_accepted(verb)])


@pytest.mark.parametrize("verb", VERBS)
def test_E07_admin_key_blocked_url_is_400(monkeypatch, verb):
    """PIN E07 (C5, validator False): flag ON + the right key, the validator refuses:
    400 BAD_REQUEST "URL blocked by security policy"; validator 1, detect_retailer 0."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch, valid=False)
    resp = _detect(_client(), verb, _headers(admin=ADMIN))
    _assert_envelope(resp, 400, "BAD_REQUEST", BLOCKED_TEXT)
    assert (legs.v, legs.r) == (1, 0), (legs.v, legs.r)


@pytest.mark.parametrize("cred", ("none", "wrong", "key"))
@pytest.mark.parametrize("auth", (None, "false"), ids=("auth_unset", "auth_false"))
@pytest.mark.parametrize("verb", VERBS)
def test_E08_flag_off_ignores_every_credential(monkeypatch, verb, auth, cred):
    """PIN E08 (C9): flag unset or "false", ADMIN_API_KEY set, no / wrong / right key:
    200 with the content of the no-header request, validator 1 per request, and the
    admin-credential check is never consulted (no header read)."""
    _env(monkeypatch, auth=auth, admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    from app.api import text_routes
    real = text_routes._admin_credential_passes
    seen = []

    def _spy(request):
        seen.append(1)
        return real(request)

    monkeypatch.setattr(text_routes, "_admin_credential_passes", _spy)
    client = _client()
    ref = _detect(client, verb, _headers())
    assert ref.status_code == 200, (ref.status_code, ascii(ref.text[:300]))
    assert (legs.v, legs.r) == (1, 1), (legs.v, legs.r)
    legs.reset()
    hdr = {"none": _headers(), "wrong": _headers(admin=WRONG),
           "key": _headers(admin=ADMIN)}[cred]
    resp = _detect(client, verb, hdr)
    assert resp.status_code == 200, (resp.status_code, ascii(resp.text[:300]))
    assert resp.content == ref.content, (ascii(resp.text[:300]), ascii(ref.text[:300]))
    assert (legs.v, legs.r) == (1, 1), (legs.v, legs.r)
    assert seen == [], f"_admin_credential_passes called {len(seen)} times with the flag OFF"


@pytest.mark.parametrize("verb", VERBS)
def test_E09_no_dns_before_the_guard(monkeypatch, verb):
    """RED E09 (ordering): the REAL validator over a socket.getaddrinfo recorder. Flag
    ON: an anonymous request is 401 with the recorder EMPTY; then the right key is 200
    with exactly one resolve of the URL host."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch, real_validator=True)
    resolved = []

    def _recorder(host, port, *_a, **_k):
        resolved.append(host.decode("ascii", "replace") if isinstance(host, bytes) else host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _recorder)
    client = _client()
    resp = _detect(client, verb, _headers())
    assert (resp.status_code, resolved) == (401, []), (
        f"anonymous {verb} {DETECT}: expected 401 with the getaddrinfo recorder [] (no DNS "
        f"before the guard), got {resp.status_code} with recorder {resolved}")
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert legs.r == 0, legs.r
    resp = _detect(client, verb, _headers(admin=ADMIN))
    assert resp.status_code == 200, (resp.status_code, ascii(resp.text[:300]))
    assert resp.json() == _ok_body(), resp.json()
    assert resolved == [HOST], resolved
    assert legs.r == 1, legs.r


def test_E10_metering_alone_never_gates_detect(monkeypatch, caplog):
    """PIN E10 (C10): ENABLE_PAID_ROUTE_METERING on, ENABLE_COMPARE_AUTH_REQUIRED unset,
    anonymous GET: 200 as at base; validator 1, detect_retailer 1; no [paid-auth] line."""
    _env(monkeypatch, meter="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    caplog.set_level(logging.INFO, logger=TEXT_LOGGER)
    resp = _detect(_client(), "GET", _headers())
    assert resp.status_code == 200, (resp.status_code, ascii(resp.text[:300]))
    assert resp.json() == _ok_body(), resp.json()
    assert (legs.v, legs.r) == (1, 1), (legs.v, legs.r)
    _assert_paid_auth(caplog, [])


@pytest.mark.parametrize("verb", VERBS)
def test_E11_guard_precedes_request_validation(monkeypatch, verb):
    """RED E11 (C11): flag ON, GET without `url` / POST `{}`, no credential: 401
    AUTH_REQUIRED (the guard runs before the 422), validator 0."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    client = _client()
    if verb == "GET":
        resp = client.get(DETECT, headers=_headers())
    else:
        resp = client.post(DETECT, json={}, headers=_headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert (legs.v, legs.r) == (0, 0), (legs.v, legs.r)


def test_E12_refusals_never_consume_the_rate_limit_bucket(monkeypatch):
    """RED E12 (C12): flag ON, 25 anonymous GETs are 25 x 401 and never 429 (a refusal
    precedes the 20/minute decorator); the admin call after them is 200."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    legs = _Legs(monkeypatch)
    client = _client()
    statuses = [_detect(client, "GET", _headers()).status_code for _ in range(25)]
    assert statuses == [401] * 25, (
        f"25 anonymous GETs: expected 25x401 and no 429 (a refusal never reaches the "
        f"20/minute bucket), got {dict(Counter(statuses))} in order {statuses}")
    assert (legs.v, legs.r) == (0, 0), (legs.v, legs.r)
    resp = _detect(client, "GET", _headers(admin=ADMIN))
    assert resp.status_code == 200, (resp.status_code, ascii(resp.text[:300]))
    assert (legs.v, legs.r) == (1, 1), (legs.v, legs.r)


@pytest.mark.parametrize("verb", VERBS)
def test_E13_openapi_detect_operation_unchanged(verb):
    """PIN E13 (U10 / n6): a fresh OpenAPI build (the cached schema restored): GET
    parameter names == ["url"], POST has no `parameters`, no `security`, and the whole
    operation object equals the base one."""
    from app.main import app
    saved = app.openapi_schema
    app.openapi_schema = None
    try:
        schema = app.openapi()
    finally:
        app.openapi_schema = saved
    assert app.openapi_schema is saved
    op = schema["paths"][DETECT][verb.lower()]
    if verb == "GET":
        assert [p.get("name") for p in op.get("parameters", [])] == ["url"], (
            op.get("parameters"))
    else:
        assert "parameters" not in op, op.get("parameters")
    assert "security" not in op, op.get("security")
    got = json.dumps(op, sort_keys=True)
    want = json.dumps(BASE_DETECT_OPS[verb.lower()], sort_keys=True)
    assert got == want, f"{verb} {DETECT} operation differs from base: {got}"


def test_E14_no_key_value_reaches_any_log_record(monkeypatch, caplog):
    """RED E14: flag ON, DEBUG on all loggers, the wrong and the right key on both
    verbs: no record carries either key value; non-vacuity: at least one [paid-auth]
    record."""
    _env(monkeypatch, auth="true", admin_key=ADMIN)
    _Legs(monkeypatch)
    attached = _debug_on_all_loggers(caplog)
    try:
        client = _client()
        for verb in VERBS:
            for key in (WRONG, ADMIN):
                _detect(client, verb, _headers(admin=key))
        records = list(caplog.records)
    finally:
        for lg in attached:
            lg.removeHandler(caplog.handler)
    leaked = [(r.name, ascii(r.getMessage()[:160])) for r in records
              if ADMIN in r.getMessage() or WRONG in r.getMessage()]
    assert not leaked, leaked
    paid = [r.getMessage() for r in records if "[paid-auth]" in r.getMessage()]
    assert len(paid) >= 1, (
        f"expected >= 1 [paid-auth] record across the wrong and the right key on both "
        f"verbs, got {len(paid)} of {len(records)} records")


# ===========================================================================
# W01-W07  #304: a whitespace-only ADMIN_API_KEY counts as unset (raw compare)
# ===========================================================================
@pytest.mark.parametrize("label", list(W01_ENVS))
def test_W01_whitespace_only_env_counts_as_unset(monkeypatch, label):
    """RED W01: ADMIN_API_KEY whitespace-only and the SAME value supplied:
    verify_admin_key raises the 403 "Invalid admin key" (base: True). U11: NBSP, NEL,
    CRLF and VT kill an ASCII-only strip at admin_routes."""
    from app.api.admin_routes import verify_admin_key
    env = W01_ENVS[label]
    _env(monkeypatch, admin_key=env)
    try:
        got = verify_admin_key(env)
    except HTTPException as exc:
        got = (exc.status_code, exc.detail)
    assert got == (403, FORBIDDEN_TEXT), (
        f"verify_admin_key(<the whitespace-only ADMIN_API_KEY {label}>) returned {got!r}, "
        f"expected HTTPException 403 {FORBIDDEN_TEXT!r} (#304: whitespace-only = unset)")


def test_W02_exact_key_passes_and_a_padded_supplied_key_fails(monkeypatch):
    """PIN W02: ADMIN_API_KEY = sentinel: the sentinel is True; " " + sentinel is 403
    (the supplied value is never stripped)."""
    from app.api.admin_routes import verify_admin_key
    _env(monkeypatch, admin_key=ADMIN)
    assert verify_admin_key(ADMIN) is True
    with pytest.raises(HTTPException) as info:
        verify_admin_key(" " + ADMIN)
    assert (info.value.status_code, info.value.detail) == (403, FORBIDDEN_TEXT)


@pytest.mark.parametrize("path", (EXTRACT, DETECT), ids=("GET-url-extract", "GET-url-detect"))
def test_W03_whitespace_env_and_header_refused(monkeypatch, path):
    """RED W03: flag ON, ADMIN_API_KEY "   ", X-Admin-Key "   ": 403 FORBIDDEN; the
    provider / detect_retailer and the validator are never called (base: 200)."""
    _env(monkeypatch, auth="true", admin_key=WS3)
    legs = _Legs(monkeypatch)
    resp = _client().get(path, params={"url": URL}, headers=_headers(admin=WS3))
    _assert_envelope(resp, 403, "FORBIDDEN", FORBIDDEN_TEXT)
    assert (legs.v, legs.r, legs.extract) == (0, 0, 0), (legs.v, legs.r, legs.extract)


@pytest.mark.parametrize(("cred", "label"), [
    *[pytest.param("basic_password", label, id="basic_password-" + label)
      for label in STATIC_WS_ENVS],
    pytest.param("x_admin_key", "spaces3", id="x_admin_key"),
])
def test_W04_admin_static_whitespace_env_is_not_configured(monkeypatch, cred, label):
    """RED W04: ADMIN_API_KEY whitespace-only and the same whitespace as the Basic password
    (U11: every STATIC_WS_ENVS value) or the X-Admin-Key ("   "): GET /admin/costs.html is
    503 "Admin not configured" (base: 200)."""
    env = STATIC_WS_ENVS[label]
    _env(monkeypatch, admin_key=env)
    if cred == "basic_password":
        hdr = _headers(basic_password=env)
    else:
        hdr = _headers(admin=env)
    resp = _client().get(ADMIN_PAGE, headers=hdr)
    assert resp.status_code == 503, (
        f"GET {ADMIN_PAGE}, ADMIN_API_KEY whitespace-only ({label}), {cred} = the same "
        f"whitespace: status {resp.status_code}, expected 503 {NOT_CONFIGURED!r}")
    assert resp.text == NOT_CONFIGURED, ascii(resp.text[:80])


def test_W05a_admin_static_exact_key_serves(monkeypatch):
    """PIN W05a: ADMIN_API_KEY = sentinel, X-Admin-Key = sentinel: 200."""
    _env(monkeypatch, admin_key=ADMIN)
    resp = _client().get(ADMIN_PAGE, headers=_headers(admin=ADMIN))
    assert resp.status_code == 200, resp.status_code


@pytest.mark.parametrize("label", list(STATIC_WS_ENVS))
def test_W05b_admin_static_whitespace_env_no_credential_is_503(monkeypatch, label):
    """RED W05b: ADMIN_API_KEY whitespace-only (U11: every STATIC_WS_ENVS value), no
    credential: 503 "Admin not configured" (base: 401)."""
    _env(monkeypatch, admin_key=STATIC_WS_ENVS[label])
    resp = _client().get(ADMIN_PAGE, headers=_headers())
    assert resp.status_code == 503, (
        f"GET {ADMIN_PAGE}, ADMIN_API_KEY whitespace-only ({label}), no credential: status "
        f"{resp.status_code}, expected 503 {NOT_CONFIGURED!r}")
    assert resp.text == NOT_CONFIGURED, ascii(resp.text[:80])


def test_W06_whitespace_env_no_header_paid_route_is_401(monkeypatch):
    """PIN W06: flag ON, ADMIN_API_KEY "   ", no header, GET /url/extract: 401
    AUTH_REQUIRED; provider and validator 0."""
    _env(monkeypatch, auth="true", admin_key=WS3)
    legs = _Legs(monkeypatch)
    resp = _client().get(EXTRACT, params={"url": URL}, headers=_headers())
    _assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)
    assert (legs.v, legs.extract) == (0, 0), (legs.v, legs.extract)


def test_W07_padded_env_raw_compare_fails_closed(monkeypatch):
    """PIN W07 (U4): ADMIN_API_KEY = " " + sentinel + " ": the bare sentinel is 403 and
    only the identical padded value is True (raw compare; kills the env-strip mutant)."""
    from app.api.admin_routes import verify_admin_key
    padded = " " + ADMIN + " "
    _env(monkeypatch, admin_key=padded)
    with pytest.raises(HTTPException) as info:
        verify_admin_key(ADMIN)
    assert (info.value.status_code, info.value.detail) == (403, FORBIDDEN_TEXT)
    assert verify_admin_key(" " + ADMIN + " ") is True


@pytest.mark.parametrize("cred", ("x_admin_key_bare", "basic_padded", "basic_bare"))
def test_W07b_admin_static_padded_env_raw_compare_fails_closed(monkeypatch, cred):
    """PIN W07b (U12, the W07 twin for the /admin static mount): ADMIN_API_KEY = " " +
    sentinel + " ": X-Admin-Key = the bare sentinel is 401, the Basic password = the
    identical padded value is 200, the Basic password = the bare sentinel is 401 (raw
    compare at main.py; kills the env-strip mutant M13)."""
    padded = " " + ADMIN + " "
    _env(monkeypatch, admin_key=padded)
    hdr, want = {
        "x_admin_key_bare": (_headers(admin=ADMIN), 401),
        "basic_padded": (_headers(basic_password=padded), 200),
        "basic_bare": (_headers(basic_password=ADMIN), 401),
    }[cred]
    resp = _client().get(ADMIN_PAGE, headers=hdr)
    assert resp.status_code == want, (
        f"GET {ADMIN_PAGE}, ADMIN_API_KEY = the padded sentinel, {cred}: status "
        f"{resp.status_code}, expected {want} (raw compare against the unstripped value)")
    if want == 401:
        assert resp.text == "Unauthorized", ascii(resp.text[:80])

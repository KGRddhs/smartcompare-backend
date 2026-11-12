"""S81-12d OPENAI-EGRESS-STOP: the frozen RED file B, the end-to-end no-byte
proof (spec S81-12d section 5 file B, as amended by RULINGS_S81_12D D-2, I-3,
I-5 and J-5: E10 re-ruled, E11 and E12 new).

Every entry runs the REAL route, the REAL orchestrator, the REAL router and the
REAL chokepoint against the pinned SDK (openai 3.3.1 over httpx2); the ONLY
OpenAI transport is the class-level recorder of file A, which answers every
OpenAI request with a synthetic 401 (production's rejected credential) and
refuses every other host. L3 moderation is NOT stubbed. Product data comes from
the conftest-neutralised I/O (Serper keyless, the Shopify catalog and noon
stubbed to a miss, the w49 quota_outage harness); a socket guard fails the row
on any other egress.

Each RED row is a PAIR in one test: the stop OFF (the base path, counted) and
the stop ON (ZERO OpenAI requests; the same status and the same body after
normalisation; the same credit calls). At base the ON half still sends
requests, so every RED row fails on an AssertionError only. E08 is the PIN: the
flag-OFF request count per path and the normalised body digest of every entry
equal the values measured at base 445f8de3 and frozen below as literals
(ruling I-5: digests are base64, built from the base measurement). Pure ASCII.
"""

import app.main  # noqa: F401  (first: the dotenv guard, tests/_env_safety)

import asyncio
import base64
import collections
import hashlib
import json
import os
import socket
import sys
import types

import pytest

from app.services import api_budget_service as abs_
from app.services import llm_router
from app.services import llm_spend_breaker as sb
from app.services import model_config
from tests.test_s81_s12d_openai_egress_stop import (
    FLAG,
    FULL,
    JPEG,
    ROLE_FLAGS,
    SYN_OPENAI,
    _sdk_texts,
    install_stop_counter,
    install_wire,
    new_symbol,
    reset_clients,
    stop_message,
)

ADMIN_SYN = "s12d" + "-admin-" + "q" * 8
USER = {
    "id": "s12d-e2e-user",
    "email": "s12d-e2e@example.test",
    "access_token": "s12d-e2e-" + "bearer",
}
PAIR = {
    "product_a": "Creed Aventus 100ml",
    "product_b": "Parfums de Marly Layton 125ml",
    "selected_category": "fragrances",
    "nocache": "true",
}
QUERY = PAIR["product_a"] + " vs " + PAIR["product_b"]
URLS = {
    "url1": "https://shop-a.example.test/products/creed-aventus-100ml",
    "url2": "https://shop-b.example.test/products/pdm-layton-125ml",
}
PAGE = (
    "<html><head><title>Creed Aventus Eau de Parfum 100ml</title>"
    '<meta property="og:type" content="product">'
    '<meta property="og:title" content="Creed Aventus Eau de Parfum 100ml">'
    "</head><body><h1>Creed Aventus Eau de Parfum 100ml</h1>"
    '<div class="product"><p>An aromatic fruity chypre fragrance.</p>'
    '<button class="add-to-cart">Add to cart</button></div></body></html>'
)
# Keys whose values change run to run (ids, clocks, durations): dropped before
# a body is compared or digested. Measured at base (two OFF runs per entry).
VOLATILE = frozenset(
    {
        "request_id",
        "comparison_id",
        "share_token",
        "timestamp",
        "generated_at",
        "created_at",
        "cached_at",
        "fetched_at",
        "duration_ms",
        "elapsed_ms",
        "elapsed",
        "elapsed_seconds",
        "duration",
        "latency_ms",
        "timings",
        "timing",
        "response_time_ms",
        "processing_time_ms",
        "total_time_ms",
        "search_time_ms",
        "processing_time",
        "as_of",
        "asof",
    }
)
ERR_TOKEN = "<ERR>"


# ---------------------------------------------------------------------------
# environment and recorders
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _s12d_e2e_env(monkeypatch):
    for k in list(os.environ):
        if (
            k.startswith("ENABLE_")
            or k.startswith("ANTHROPIC_")
            or k.startswith("LLM_SPEND_")
            or k.startswith("OPENAI_")
            or k.startswith("LLM_BREAKER_")
            or k.startswith("SERPER_")
        ):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", SYN_OPENAI)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_SYN)
    reset = new_symbol("_reset_openai_egress_stop_state")
    if reset is not None:
        reset()
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()
    monkeypatch.setattr(abs_, "_openai_breaker_cache", None)
    yield
    from app.api.auth_routes import get_optional_user
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides.pop(get_optional_user, None)
    if reset is not None:
        reset()
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()


def _price_service_globals():
    """Every app.services.price_service module dict a caller can reach (the
    w49 lesson: a fresh import after a del leaves an orphaned dict)."""
    found = {}
    live = sys.modules.get("app.services.price_service")
    if live is not None:
        found[id(vars(live))] = vars(live)
    for mod in list(sys.modules.values()):
        try:
            fn = vars(mod).get("fetch_shopify_price")
        except TypeError:
            continue
        g = getattr(fn, "__globals__", None)
        if isinstance(g, dict) and g.get("__name__") == "app.services.price_service":
            found[id(g)] = g
    return list(found.values())


def _guard(mp):
    """Every non-loopback connect / DNS lookup and every curl_cffi transfer is
    refused and recorded (the w49 socket guard)."""
    attempts = []
    real_connect = socket.socket.connect
    real_gai = socket.getaddrinfo

    def _loop(host):
        return host in ("127.0.0.1", "::1", "localhost", "", None)

    def _connect(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if not _loop(host):
            attempts.append(("connect", str(host)))
            raise OSError("s12d guard: connect blocked")
        return real_connect(self, addr)

    def _gai(host, *a, **k):
        if not _loop(host):
            attempts.append(("getaddrinfo", str(host)))
            raise socket.gaierror("s12d guard: DNS blocked")
        return real_gai(host, *a, **k)

    mp.setattr(socket.socket, "connect", _connect)
    mp.setattr(socket, "getaddrinfo", _gai)
    import curl_cffi.curl as _curl
    import curl_cffi.requests as _curl_requests

    def _req(self, method, url, *a, **k):
        attempts.append(("curl_cffi", str(url)))
        raise OSError("s12d guard: curl_cffi blocked")

    async def _areq(self, method, url, *a, **k):
        attempts.append(("curl_cffi", str(url)))
        raise OSError("s12d guard: curl_cffi blocked")

    def _perform(self, *a, **k):
        attempts.append(("curl_cffi.perform", "?"))
        raise OSError("s12d guard: curl_cffi blocked")

    mp.setattr(_curl_requests.Session, "request", _req)
    mp.setattr(_curl_requests.AsyncSession, "request", _areq)
    mp.setattr(_curl.Curl, "perform", _perform)
    return attempts


class Run(types.SimpleNamespace):
    pass


def setup(mp, stop, env=None, roles=(), consent="unset"):
    """The FULL configuration (spec 5 + D-2) with the stop per the row, the
    recorders, the quota_outage stubs and an authenticated caller."""
    from app.api import image_routes, text_routes, url_routes
    from app.api.auth_routes import get_optional_user
    from app.main import app as fastapi_app
    from app.middleware.rate_limiter import limiter
    from app.services import serper_service, usage_service
    from app.services import structured_comparison_service as scs
    from app.services.model_router_service import model_router

    for k, v in FULL.items():
        mp.setenv(k, v)
    for name in ROLE_FLAGS:
        mp.delenv(name, raising=False)
    mp.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
    mp.delenv("OPENAI_BASE_URL", raising=False)
    mp.delenv("ENABLE_OPENAI_PRE_V3", raising=False)
    if stop is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, stop)
    for k, v in (env or {}).items():
        mp.setenv(k, v)
    for name in roles:
        mp.setenv(name, "true")
    if consent != "unset":
        from app.utils import request_context as rc

        mp.setattr(rc, "consent_version", lambda: consent)

    run = Run(consumes=[], refunds=[], labels=[], saves=[], captured=[])
    run.wire = install_wire(mp)
    run.attempts = _guard(mp)
    run.stops = install_stop_counter(mp)
    reset_clients(mp)
    mp.setattr(limiter, "enabled", False)
    mp.setattr(serper_service, "SERPER_API_KEY", None)

    async def _miss(*_a, **_k):
        return None

    for g in _price_service_globals():
        mp.setitem(g, "_fetch_shopify_catalog", _miss)
    mp.setattr(scs, "fetch_noon_price", _miss)

    async def _gm(*_a, **_k):
        return model_config.verdict_model()

    mp.setattr(model_router, "get_model", _gm)
    mp.setattr(model_router, "record_usage", _miss)

    async def _no(*_a, **_k):
        return False

    mp.setattr(sb, "entry_refuses_async", _no)
    mp.setattr(sb, "admit_openai_dispatch", _miss)
    mp.setattr(sb, "record_openai_response_soon", lambda *a, **k: None)

    def _consume(user_id, *_a, **_k):
        run.consumes.append(user_id)

        async def _r():
            return {
                "allowed": True,
                "reason": None,
                "tier": "free",
                "consumed": True,
                "consumed_keys": None,
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
            }

        return _r()

    def _refund(user_id, consumed_keys=None, *_a, **_k):
        run.refunds.append((user_id, consumed_keys))

        async def _r():
            return None

        return _r()

    for mod in (usage_service, text_routes, url_routes, image_routes):
        mp.setattr(mod, "consume_comparison_credit", _consume, raising=False)
        mp.setattr(mod, "refund_comparison_credit", _refund, raising=False)

    def _save(*a, **k):
        run.saves.append((a, k))

        async def _r():
            return None

        return _r()

    for name in ("save_comparison", "save_comparison_and_track_cohort"):
        for mod in (text_routes, url_routes):
            if hasattr(mod, name):
                mp.setattr(mod, name, _save)

    for mod in (text_routes, url_routes, image_routes):
        real_ff = getattr(mod.fire_and_forget, "_s12d_real", mod.fire_and_forget)

        def _ff(coro, *a, _real=real_ff, **kw):
            run.labels.append(kw.get("label"))
            return _real(coro, *a, **kw)

        _ff._s12d_real = real_ff
        mp.setattr(mod, "fire_and_forget", _ff)

    import sentry_sdk

    mp.setattr(sentry_sdk, "capture_message", lambda *a, **k: run.captured.append(a))
    mp.setattr(sentry_sdk, "capture_exception", lambda *a, **k: run.captured.append(a))
    fastapi_app.dependency_overrides[get_optional_user] = lambda: dict(USER)
    return run


def _client():
    from fastapi.testclient import TestClient

    from app.main import app as fastapi_app

    return TestClient(fastapi_app, raise_server_exceptions=False)


def _json(resp):
    try:
        return resp.json()
    except ValueError:
        return {"<text>": resp.text}


def _sse(text):
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        ev, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                ev = line[len("event: "):]
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[len("data: "):])
                except ValueError:
                    data = line[len("data: "):]
        events.append((ev, data))
    return events


# ---------------------------------------------------------------------------
# the entries
# ---------------------------------------------------------------------------
def _e_text_get(run):
    resp = _client().get("/api/v1/text/compare", params=PAIR)
    return resp.status_code, _json(resp)


def _e_text_post(run):
    body = {
        "product_a": PAIR["product_a"],
        "product_b": PAIR["product_b"],
        "selected_category": "fragrances",
    }
    resp = _client().post("/api/v1/text/compare", json=body)
    return resp.status_code, _json(resp)


def _e_stream(run):
    resp = _client().get("/api/v1/text/compare/stream", params=PAIR)
    events = _sse(resp.text)
    names = [e for e, _ in events]
    terminal = [d for e, d in events if e in ("complete", "error", "settle_complete")]
    return resp.status_code, {"events": names, "terminal": terminal}


def _e_camera(run):
    files = [("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)]
    resp = _client().post("/api/v1/image/identify", files=files)
    return resp.status_code, _json(resp)


def _e_url(run, mp):
    from app.services import url_extraction_service as urlsvc

    async def _page(url):
        return PAGE

    async def _page_v2(url):
        return {
            "status": 200,
            "final_url": url,
            "text": PAGE,
            "outcome": "ok",
            "error_type": None,
        }

    async def _valid(url):
        return True

    from app.api import url_routes

    mp.setattr(url_routes, "_validate_url_offloop_or_sync", _valid)
    mp.setattr(urlsvc, "fetch_page", _page)
    mp.setattr(urlsvc, "_fetch_page_v2", _page_v2)
    resp = _client().post("/api/v1/url/compare", json=dict(URLS))
    return resp.status_code, _json(resp)


def _e_quick(run):
    resp = _client().post(
        "/api/v1/text/quick",
        json={"product1": PAIR["product_a"], "product2": PAIR["product_b"]},
        headers={"X-Admin-Key": ADMIN_SYN},
    )
    return resp.status_code, _json(resp)


def _e_parse(run):
    resp = _client().get(
        "/api/v1/text/parse", params={"q": QUERY}, headers={"X-Admin-Key": ADMIN_SYN}
    )
    return resp.status_code, _json(resp)


def _e_price_kpi(run):
    resp = _client().get(
        "/api/v1/text/price-kpi",
        params={"q": PAIR["product_a"]},
        headers={"X-Admin-Key": ADMIN_SYN},
    )
    return resp.status_code, _json(resp)


def _e_warmer(run):
    from scripts import cron_warm_price_cache as warmer

    tally = asyncio.run(warmer._warm_one({"query": QUERY, "region": "bahrain"}))
    return 0, tally


ENTRIES = {
    "e01_text_get": (_e_text_get, {}),
    "e02_text_post": (_e_text_post, {}),
    "e03_stream": (_e_stream, {}),
    "e03_stream_deadline": (_e_stream, {"ENABLE_FULL_STREAM_DEADLINE": "true"}),
    "e04_camera": (_e_camera, {}),
    "e04_camera_vision_v2": (_e_camera, {"ENABLE_VISION_IDENTITY_V2": "true"}),
    "e05_url": (_e_url, {}),
    "e05_url_mode_v2": (_e_url, {"ENABLE_URL_MODE_V2": "true"}),
    "e06_quick": (_e_quick, {}),
    "e06_parse": (_e_parse, {}),
    "e06_price_kpi": (_e_price_kpi, {}),
    "e07_warmer": (_e_warmer, {}),
}


def drive(mp, entry, stop, env=None, roles=(), consent="unset"):
    fn, own_env = ENTRIES[entry]
    merged = dict(own_env)
    merged.update(env or {})
    run = setup(mp, stop, env=merged, roles=roles, consent=consent)
    if fn is _e_url:
        run.status, run.body = fn(run, mp)
    else:
        run.status, run.body = fn(run)
    run.paths = collections.Counter(run.wire.paths())
    bad = [a for a in run.attempts if not str(a[1]).endswith(".invalid")]
    assert bad == [], ("real egress attempted", entry, bad)
    other = [h for h in run.wire.other if not str(h[0]).endswith(".invalid")]
    assert other == [], ("a non-OpenAI host reached the recorder", other)
    return run


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------
def _texts():
    out = list(_sdk_texts())
    msg = stop_message()
    if isinstance(msg, str) and msg:
        out.append(msg)
    return sorted(set(t for t in out if t), key=len, reverse=True)


# Lists whose order follows the completion order of concurrent tasks (measured:
# metadata.source_trace.products swapped between two runs of one process under
# load): compared as multisets.
ORDER_FREE = frozenset({"source_trace"})


def _scrub(value, texts):
    if isinstance(value, dict):
        out = {
            k: _scrub(v, texts) for k, v in sorted(value.items()) if k not in VOLATILE
        }
        for k in ORDER_FREE & set(out):
            inner = out[k]
            if isinstance(inner, dict):
                for ik, iv in list(inner.items()):
                    if isinstance(iv, list):
                        inner[ik] = sorted(iv, key=lambda x: json.dumps(x, sort_keys=True, default=repr))
        return out
    if isinstance(value, (list, tuple)):
        return [_scrub(v, texts) for v in value]
    if isinstance(value, str):
        for t in texts:
            if t in value:
                value = value.replace(t, ERR_TOKEN)
        return value
    return value


def norm(value):
    return json.loads(json.dumps(_scrub(value, _texts()), sort_keys=True, default=repr))


def digest(value):
    raw = json.dumps(norm(value), sort_keys=True).encode("utf-8")
    return base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")


def _total(run):
    return sum(run.paths.values())


def _stops_by_path(run):
    """The stop counter mapped to the path each surface would have used."""
    path = {"chat_completions": "/v1/chat/completions", "moderations": "/v1/moderations"}
    return collections.Counter(path.get(s, s) for s in run.stops.surfaces)


def assert_pair(off, on, entry, same_stops=True):
    assert _total(off) >= 1, (entry, "the OFF half sent no OpenAI request", off.paths)
    assert on.wire.requests == [], (entry, "ON sent", on.wire.paths())
    assert on.status == off.status, (entry, off.status, on.status)
    assert norm(on.body) == norm(off.body), (entry, norm(off.body), norm(on.body))
    assert on.consumes == off.consumes, (entry, off.consumes, on.consumes)
    assert on.refunds == off.refunds, (entry, off.refunds, on.refunds)
    assert norm(on.saves) == norm(off.saves), entry
    if same_stops:
        assert _stops_by_path(on) == off.paths, (entry, off.paths, on.stops.surfaces)
    assert on.captured == [], (entry, on.captured)


# ---------------------------------------------------------------------------
# E01 .. E07: the pair per entry (RED)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "entry", ("e01_text_get", "e02_text_post"), ids=("E01_get", "E02_post")
)
def test_e01_e02_text_compare_sends_no_byte(monkeypatch, entry):
    """RED (ON half sends at base): the text compare. OFF: chat requests plus
    one moderation request, a delivered result. ON: ZERO requests, the same
    status, the same body (normalised), the same credit calls and save
    payload; one stop per OFF request per path."""
    off = drive(monkeypatch, entry, None)
    on = drive(monkeypatch, entry, "true")
    assert off.paths.get("/v1/moderations", 0) == 1, off.paths
    assert_pair(off, on, entry)


@pytest.mark.parametrize("entry", ("e03_stream", "e03_stream_deadline"))
def test_e03_stream_sends_no_byte(monkeypatch, entry):
    """RED: the SSE stream (both ENABLE_FULL_STREAM_DEADLINE states, D-2): the
    same event-name sequence and terminal bodies; ZERO requests ON."""
    off = drive(monkeypatch, entry, None)
    on = drive(monkeypatch, entry, "true")
    assert off.body["events"], off.body
    assert_pair(off, on, entry)


@pytest.mark.parametrize("entry", ("e04_camera", "e04_camera_vision_v2"))
def test_e04_camera_coded_503_with_the_same_refund(monkeypatch, entry):
    """RED: the camera (the ruled exception R-12D-3). OFF: ONE vision request,
    500 SERVER_ERROR. ON: ZERO requests, 503 LLM_UNAVAILABLE with the friendly
    message; in BOTH one consume, one refund under the vision_exception label,
    no moderation request; ON no capture call."""
    from app.services.structured_comparison_service import (
        LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
    )

    off = drive(monkeypatch, entry, None)
    on = drive(monkeypatch, entry, "true")
    assert off.paths == collections.Counter({"/v1/chat/completions": 1}), off.paths
    assert off.status == 500 and off.body.get("code") == "SERVER_ERROR", off.body
    assert on.wire.requests == [], on.wire.paths()
    assert on.status == 503, (on.status, on.body)
    assert on.body.get("code") == "LLM_UNAVAILABLE", on.body
    assert on.body.get("error") == LLM_UNAVAILABLE_FRIENDLY_MESSAGE, on.body
    assert on.body.get("success") is False, on.body
    for r in (off, on):
        assert r.consumes == [USER["id"]], r.consumes
        assert r.refunds == [(USER["id"], None)], r.refunds
        assert "usage_refund.image.vision_exception" in r.labels, r.labels
    assert on.captured == [], on.captured
    assert _stops_by_path(on) == off.paths, on.stops.surfaces


@pytest.mark.parametrize("entry", ("e05_url", "e05_url_mode_v2"))
def test_e05_link_compare_sends_no_byte(monkeypatch, entry):
    """RED: the link compare with pages lacking a structured price (so
    extract_with_ai runs): OFF and ON the same coded answer and refund; ZERO
    requests ON; stops == OFF requests."""
    off = drive(monkeypatch, entry, None)
    on = drive(monkeypatch, entry, "true")
    assert_pair(off, on, entry)


@pytest.mark.parametrize("entry", ("e06_quick", "e06_parse", "e06_price_kpi"))
def test_e06_other_entries_send_no_byte(monkeypatch, entry):
    """RED: POST /text/quick and GET /text/parse (admin key), GET
    /text/price-kpi: ON ZERO requests; status and body equal OFF."""
    off = drive(monkeypatch, entry, None)
    on = drive(monkeypatch, entry, "true")
    assert_pair(off, on, entry)


def test_e07_price_warmer_sends_no_byte(monkeypatch):
    """RED: the price-warmer's _warm_one: ON ZERO requests; the tally equals
    OFF."""
    off = drive(monkeypatch, "e07_warmer", None)
    on = drive(monkeypatch, "e07_warmer", "true")
    assert_pair(off, on, "e07_warmer")


# ---------------------------------------------------------------------------
# E08: the flag-OFF e2e identity (PIN), frozen at base 445f8de3
# ---------------------------------------------------------------------------
# entry -> (status, {path: count}, base64 sha256 of the normalised body)
BASE_OFF = {
    "e01_text_get": (
        200,
        {"/v1/chat/completions": 11, "/v1/moderations": 1},
        "tHgoYuUf2mG84jUOSqBA17bUJThLg0D9vekCPaeChF8=",
    ),
    "e02_text_post": (
        200,
        {"/v1/chat/completions": 11, "/v1/moderations": 1},
        "sfdq870tzzvte+PhjmbSb+3wbiT1DBFq5xsePkIe8xE=",
    ),
    "e03_stream": (
        200,
        {"/v1/chat/completions": 11, "/v1/moderations": 1},
        "r0xkcim2NzHIvWd6Fm6BXLHn1n4qECPM7iMcpmVPsXc=",
    ),
    "e03_stream_deadline": (
        200,
        {"/v1/chat/completions": 11, "/v1/moderations": 1},
        "r0xkcim2NzHIvWd6Fm6BXLHn1n4qECPM7iMcpmVPsXc=",
    ),
    "e04_camera": (
        500,
        {"/v1/chat/completions": 1},
        "vKLHrLLg5Nf7qD0XgWQAP4JtmnsVpS9SGm4CcpNFGLM=",
    ),
    "e04_camera_vision_v2": (
        500,
        {"/v1/chat/completions": 1},
        "vKLHrLLg5Nf7qD0XgWQAP4JtmnsVpS9SGm4CcpNFGLM=",
    ),
    "e05_url": (
        503,
        {"/v1/chat/completions": 3},
        "HdhjVXwwInasb1KmbFkWQ0sccwquwOwy8Knwqh2sH0M=",
    ),
    "e05_url_mode_v2": (
        503,
        {"/v1/chat/completions": 3},
        "HdhjVXwwInasb1KmbFkWQ0sccwquwOwy8Knwqh2sH0M=",
    ),
    "e06_parse": (
        200,
        {"/v1/chat/completions": 1},
        "0w/QSCX/KofNC+9JHdioCeZw9JgV7cRJZD2Nu4Kc4JQ=",
    ),
    "e06_price_kpi": (
        200,
        {"/v1/chat/completions": 3},
        "KQknOK0767rZ+XND+Z7px7kKTEL1oq/di3N77msucsI=",
    ),
    "e06_quick": (
        400,
        {"/v1/chat/completions": 1},
        "6v9pRcFSdB6+yQTCmvD47aUckK9E1g9KsSRv2F7pbuo=",
    ),
    "e07_warmer": (
        0,
        {"/v1/chat/completions": 1},
        "zZGn8na9lDB5aGD0XsWmWT0G1si4KTknGCJuzT5Wdl4=",
    ),
}


@pytest.mark.parametrize("stop", (None, "false", " garbage "), ids=("unset", "false", "garbage"))
@pytest.mark.parametrize("entry", sorted(ENTRIES))
def test_e08_flag_off_e2e_identity(monkeypatch, entry, stop):
    """PIN: flag OFF (unset / "false" / " garbage "), the FULL configuration:
    per entry the status, the OpenAI request count per path and the
    normalised body equal the base measurement frozen above; no stop runs."""
    run = drive(monkeypatch, entry, stop)
    want_status, want_paths, want_digest = BASE_OFF[entry]
    assert run.status == want_status, (entry, run.status)
    assert dict(run.paths) == want_paths, (entry, dict(run.paths))
    assert digest(run.body) == want_digest, (entry, norm(run.body))
    assert run.stops.surfaces == [], run.stops.surfaces


# ---------------------------------------------------------------------------
# E09 .. E12: mixed configurations (rulings J-5)
# ---------------------------------------------------------------------------
def _claude_stub(mp, calls):
    async def _claude(site, spec, request, lane):
        calls.append(site)
        if site.startswith("verdict"):
            content = json.dumps(
                {
                    "winner_index": 0,
                    "recommendation": "synthetic",
                    "key_differences": [],
                }
            )
        elif site == "parse":
            content = json.dumps({"products": []})
        else:
            content = json.dumps({})
        return llm_router.ClaudeChatResult(
            content, "stop", {}, model_config.anthropic_model("text"), "end_turn"
        )

    mp.setattr(llm_router, "_dispatch_claude", _claude)


def test_e09_claude_text_and_verdict_moderation_on_openai(monkeypatch):
    """RED (the moderation request at base): the text and verdict roles ON,
    consent 3 (Claude stubbed at _dispatch_claude), moderation and vision
    roles OFF, the stop ON: a text compare sends ZERO OpenAI requests (the
    moderation call is the one that would have gone) and the Claude stub ran."""
    calls = []
    _claude_stub(monkeypatch, calls)
    run = drive(
        monkeypatch,
        "e01_text_get",
        "true",
        roles=("ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VERDICT"),
        consent=3,
    )
    assert run.wire.requests == [], run.wire.paths()
    assert calls, "the Claude stub never ran"


def _pair_role_on(mp, entry, roles, consent, env=None, stub=False):
    calls = []
    if stub:
        _claude_stub(mp, calls)
    off = drive(mp, entry, None, env=env, roles=roles, consent=consent)
    if stub:
        _claude_stub(mp, calls)
    on = drive(mp, entry, "true", env=env, roles=roles, consent=consent)
    return off, on, calls


def test_e10_pre_v3_text_compare_equals_the_401_answer(monkeypatch):
    """RED (J-5, E10 re-ruled): the text and verdict roles ON, no consent
    version, ENABLE_OPENAI_PRE_V3 ON, the stop ON: one text compare sends ZERO
    OpenAI requests and its status and body EQUAL the same configuration with
    the stop OFF and the 401 recorder (never the coded LLM_UNAVAILABLE where
    the 401 delivered); no ERROR record from a stop."""
    roles = ("ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VERDICT")
    env = {"ENABLE_OPENAI_PRE_V3": "true"}
    off, on, _ = _pair_role_on(monkeypatch, "e01_text_get", roles, None, env=env)
    assert_pair(off, on, "E10")


def test_e11_staged_roles_text_on_verdict_off(monkeypatch):
    """RED (J-5, NEW E11): the text role ON with consent 3 (Claude stubbed),
    the verdict role OFF, the stop ON: ZERO OpenAI requests, and the answer
    equals the stop-OFF / 401 answer of that configuration, never the coded
    LLM_UNAVAILABLE envelope."""
    roles = ("ENABLE_ANTHROPIC_TEXT",)
    off, on, calls = _pair_role_on(monkeypatch, "e01_text_get", roles, 3, stub=True)
    assert calls, "the Claude stub never ran"
    assert (on.body or {}).get("code") != "LLM_UNAVAILABLE" or (
        (off.body or {}).get("code") == "LLM_UNAVAILABLE"
    ), on.body
    assert_pair(off, on, "E11")


def test_e12_link_compare_role_on_pre_v3(monkeypatch):
    """RED (J-5, NEW E12): a link comparison with the text role ON, no consent
    version, ENABLE_OPENAI_PRE_V3 ON, the stop ON: equal to the stop-OFF / 401
    answer of that configuration, with its refund; ZERO requests."""
    roles = ("ENABLE_ANTHROPIC_TEXT",)
    env = {"ENABLE_OPENAI_PRE_V3": "true"}
    off, on, _ = _pair_role_on(monkeypatch, "e05_url", roles, None, env=env)
    assert_pair(off, on, "E12")

"""W4-9 (PO-RECORDED-MEASURED-05) — the leak class one layer down, in
``app/services/extraction_service.py`` (FABLE REVIEW RULINGS R2(b), R2(c), R3).

R2(b) ``parse_product_query``'s catch returns ``{"products": [], "error": str(e)}``
and the orchestrator parser exits ship that dict as the nested ``parsed`` key of
the result / SSE error event. Measured at b63a8368: an OpenAI-429 string with
``insufficient_quota`` and an org id reaches the SSE wire under
``$.parsed.error``. Ruling: the catch stores a constant and logs with
``exc_info=True``; the parser exits emit ``parsed`` with ONLY ``products`` (or
drop it).

R2(c) ``generate_comparison``'s catch returns ``{"winner_index": 0, "error": str(e)}``
and that rides SUCCESS payloads: ``$.comparison.error`` on the sync 200 body,
on the SSE ``verdict`` / ``settle_complete`` / ``complete`` events, in the row
``save_comparison`` persists (it passes ``_validate_renderable``) and on the
unauthenticated ``GET /api/v1/share/{token}``. Ruling: constant + log.

Every test drives the REAL extraction function with the LLM call
(``api_budget_service.guarded_llm_create``) raising an OpenAI-429-shaped
string carrying a FAKE org id, under a socket guard that blocks every
non-loopback connect + DNS lookup. The pipeline tests use the phones' request
shape (``product_a``/``product_b`` -> explicit_pair) with only
``_fetch_product_data`` stubbed; scoring, response building and the real
verdict function run.

R2(e) — measured at b63a8368 with EVERY OpenAI call failing on the phones'
explicit_pair path (no stubs below the LLM call): ``extract_reviews``' catch
(``{"average_rating": None, "error": str(e)}``) ALSO rides the success body at
``$.products[i].reviews.error``. By R2(e)'s own criterion that site is IN; the
r2e test pins it (orchestrator ruling pending — see the red-phase report).

RED at b63a8368: 04 (x3), 04c, r2c_* (direct, sync body, SSE x2, row, share),
r2e (sync, sse).
Added in the fix round (adversary finding: exc_info on the two catches was
unpinned): r2c_pin_verdict_failure_still_logged_with_exc_info and
r2e_extract_reviews_catch_returns_no_raw_text_and_logs_exc_info (both RED at
b63a8368 on their exc_info half).
PIN (green at b63a8368): r2c_pin_success_payload_is_still_delivered_and_renderable.
"""
import asyncio
import json
import logging
import os
import socket
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.services.extraction_service as es  # noqa: E402
import app.services.structured_comparison_service as scs  # noqa: E402
from app.main import app  # noqa: E402

# A FAKE org id and request id: nothing here is a real credential.
_FAKE_ORG = "org-W49FAKEORG0000000000000"
_SECRET_429 = (
    "Error code: 429 - {'error': {'message': 'You exceeded your current quota, "
    f"please check your plan and billing details. {_FAKE_ORG} req_w49fake', "
    "'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}}"
)
_MARKERS = (_FAKE_ORG, "insufficient_quota", "Error code: 429")

# LITERAL parser copy (R3 — never the imported constant).
_PARSE_COPY = "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'"

_PAIR = ("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml")
_PAIR_PARAMS = {"product_a": _PAIR[0], "product_b": _PAIR[1],
                "selected_category": "fragrances", "nocache": "true"}


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.middleware.rate_limiter import limiter

    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    yield


@pytest.fixture(autouse=True)
def _default_flag_state(monkeypatch):
    for name in ("ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_COMPARISON_ID_ECHO",
                 "ENABLE_PREVERDICT_DISCONNECT_ABORT", "ENABLE_SELF_CRITIQUE",
                 "ENABLE_FULL_STREAM_DEADLINE"):
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def _serper_unconfigured(monkeypatch):
    """Pin Serper to "no key" for every test in this file, whatever ran first.

    conftest pops SERPER_API_KEY/SERPER_API_KEYS from the environment, but
    ``serper_service.SERPER_API_KEY`` is a MODULE global read once at import.
    ``tests/test_hotfix_shopping_query_clean.py`` (3 tests) does
    ``monkeypatch.setenv("SERPER_API_KEY", "test-key")`` then
    ``importlib.reload(serper_service)``; monkeypatch restores the env var but
    not the reloaded global, so in the one-process CI suite every later test
    sees a configured key and the unstubbed quota_outage path fires real
    Serper lookups (CI, PR #178: 22 x getaddrinfo google.serper.dev)."""
    from app.services import serper_service

    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", None)
    assert serper_service._active_serper_key() is None
    yield


@pytest.fixture(autouse=True)
def socket_guard(monkeypatch):
    """Block every non-loopback connect and DNS lookup (and every curl_cffi
    transfer); fail the test if anything but the conftest-neutralised
    ``*.invalid`` sentinel was tried."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _loop(host):
        return host in ("127.0.0.1", "::1", "localhost", "", None)

    def _connect(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if not _loop(host):
            attempts.append(("connect", str(host)))
            raise OSError(f"W4-9 socket guard: connect to {host!r} blocked")
        return real_connect(self, addr)

    def _connect_ex(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if not _loop(host):
            attempts.append(("connect_ex", str(host)))
            raise OSError(f"W4-9 socket guard: connect_ex to {host!r} blocked")
        return real_connect_ex(self, addr)

    def _gai(host, *a, **k):
        if not _loop(host):
            attempts.append(("getaddrinfo", str(host)))
            raise socket.gaierror(f"W4-9 socket guard: DNS for {host!r} blocked")
        return real_gai(host, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", _gai)

    # curl_cffi drives NATIVE libcurl, which never touches the Python socket
    # module, so the three patches above cannot see it (CI, PR #178: the
    # quota_outage tests reached www.noon.com for real — "HTTP/2 stream 1
    # reset by server"). Block and record it at the Python entry points.
    from urllib.parse import urlsplit

    import curl_cffi.curl as _curl
    import curl_cffi.requests as _curl_requests

    def _curl_host(url):
        return urlsplit(str(url)).hostname or str(url)

    def _curl_request(self, method, url, *a, **k):
        attempts.append(("curl_cffi", _curl_host(url)))
        raise OSError(f"W4-9 socket guard: curl_cffi {method} {url!r} blocked")

    async def _curl_request_async(self, method, url, *a, **k):
        attempts.append(("curl_cffi", _curl_host(url)))
        raise OSError(f"W4-9 socket guard: curl_cffi {method} {url!r} blocked")

    def _curl_perform(self, *a, **k):
        attempts.append(("curl_cffi.perform", "?"))
        raise OSError("W4-9 socket guard: curl_cffi perform blocked")

    monkeypatch.setattr(_curl_requests.Session, "request", _curl_request)
    monkeypatch.setattr(_curl_requests.AsyncSession, "request", _curl_request_async)
    monkeypatch.setattr(_curl.Curl, "perform", _curl_perform)
    yield attempts
    unexpected = [a for a in attempts if not a[1].endswith(".invalid")]
    assert not unexpected, f"W4-9 socket guard: real egress attempted: {unexpected}"


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def llm_429():
    """The REAL extraction functions run; only the OpenAI call raises."""
    boom = AsyncMock(side_effect=Exception(_SECRET_429))
    with patch.object(es._llm_breaker, "guarded_llm_create", boom):
        yield boom


@pytest.fixture()
def verdict_pipeline(llm_429):
    """Drive the orchestrators to the REAL generate_comparison: product data
    stubbed ($0, no network), scoring + response builder real, L3 moderation
    allowed, the verdict model id pinned (model_router would read Redis)."""
    from app.services.content_safety_service import ContentSafetyService, SafetyResult
    from app.services.model_config import verdict_model

    async def _fake_fetch(self, product_info, region, include_specs, include_reviews,
                          nocache=False, **kw):
        name = product_info.get("name") or product_info.get("search_query") or "Fragrance"
        brand = product_info.get("brand") or "Tom Ford"
        return {
            "brand": brand, "name": name, "full_name": f"{brand} {name}".strip(),
            "variant": "100ml", "category": product_info.get("category") or "other",
            "query": name,
            "specs": {"concentration": "Eau de Parfum", "longevity": "8-10 hours",
                      "scent_family": "Woody Oriental", "top_notes": "Bergamot",
                      "size": "100 ml"},
            "price": {"amount": 78.0 if "Soleil" in str(name) else 64.0,
                      "currency": "BHD", "retailer": "example.com",
                      "url": "https://example.com/p", "estimated": False,
                      "source_method": "page_scrape_jsonld"},
            "rating": 4.4, "review_count": 120,
            "rating_source": {"url": "https://example.com", "name": "Retailer"},
            "image_url": None, "fact_check": {"overall_confidence": "high"},
        }

    with patch.object(scs.StructuredComparisonService, "_fetch_product_data", _fake_fetch), \
         patch("app.services.model_router_service.model_router.get_model",
               AsyncMock(return_value=verdict_model())), \
         patch.object(ContentSafetyService, "moderate_output",
                      AsyncMock(return_value=SafetyResult(allowed=True))):
        yield llm_429


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dumps(obj):
    return json.dumps(obj, default=str, ensure_ascii=False)


def _leaked(text):
    return [m for m in _MARKERS if m in text]


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
                data = json.loads(line[len("data: "):])
        events.append((ev, data))
    return events


def _drain(agen):
    async def _go():
        return [ev async for ev in agen]
    return asyncio.run(_go())


def _raw_logged_with_exc_info(caplog, logger_name):
    hits = [r for r in caplog.records
            if r.name == logger_name and _FAKE_ORG in r.getMessage()]
    return hits, any(r.exc_info for r in hits)


# ===========================================================================
# R2(b) / R3 test 4 — the REAL parser failing
# ===========================================================================

@pytest.mark.parametrize("surface", ["service_sync", "service_stream", "sse_route"])
def test_04_real_parser_429_is_sanitised_and_logged(surface, llm_429, client, caplog):
    """RED at b63a8368 (measured: $.parsed.error carries the 429 string with
    the org id on the sync result and on the SSE error event; the parser's
    logger.error has no exc_info). The parser exit's own sentence is product
    copy (LITERAL) and stays codeless."""
    with caplog.at_level(logging.ERROR):
        if surface == "service_sync":
            out = asyncio.run(scs.StructuredComparisonService().compare_from_text(
                query="alpha vs beta"))
            wire = _dumps(out)
        elif surface == "service_stream":
            events = _drain(scs.StructuredComparisonService().compare_from_text_streaming(
                query="alpha vs beta"))
            assert events[-1][0] == "error", [e[0] for e in events]
            out = events[-1][1]
            wire = _dumps(events)
        else:
            resp = client.get("/api/v1/text/compare/stream", params={"q": "alpha vs beta"})
            assert resp.status_code == 200, resp.text
            events = _sse(resp.text)
            assert events[-1][0] == "error", [e[0] for e in events]
            out = events[-1][1]
            wire = resp.text
    assert llm_429.await_count >= 1, "the real parser never reached the LLM call"
    assert not _leaked(wire), f"parser exception text reached the {surface} surface: {out!r}"
    if "parsed" in out:
        assert isinstance(out["parsed"], dict) and set(out["parsed"]) <= {"products"}, out
    assert out.get("error") == _PARSE_COPY
    assert "code" not in out, out
    hits, has_exc = _raw_logged_with_exc_info(caplog, "app.services.extraction_service")
    assert hits, "the parser failure no longer reaches the extraction_service log"
    assert has_exc, "R2(b): the parser catch must log with exc_info=True"


def test_04c_parse_product_query_catch_returns_no_raw_text(llm_429, caplog):
    """RED at b63a8368: the function-level contract behind test 04 —
    parse_product_query's catch returns {"products": [], "error": str(e)}."""
    with caplog.at_level(logging.ERROR):
        parsed, usage = asyncio.run(es.parse_product_query("alpha vs beta"))
    assert llm_429.await_count == 1
    assert parsed.get("products") == []
    assert not _leaked(_dumps(parsed)), f"raw exception text returned: {parsed!r}"
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0}
    hits, has_exc = _raw_logged_with_exc_info(caplog, "app.services.extraction_service")
    assert hits and has_exc, "R2(b): raw text must go to logger.error(..., exc_info=True)"


# ===========================================================================
# R2(c) — the verdict catch rides SUCCESS payloads
# ===========================================================================

def test_r2c_generate_comparison_catch_returns_no_raw_text(llm_429):
    """RED at b63a8368: generate_comparison's catch returns
    {"winner_index": 0, "error": str(e)}."""
    from app.services.model_config import verdict_model

    p = {"brand": "A", "name": "One", "specs": {}, "price": None}
    q = {"brand": "B", "name": "Two", "specs": {}, "price": None}
    with patch("app.services.model_router_service.model_router.get_model",
               AsyncMock(return_value=verdict_model())):
        comparison, usage = asyncio.run(es.generate_comparison(p, q, "bahrain"))
    assert llm_429.await_count >= 1
    assert comparison.get("winner_index") == 0
    assert not _leaked(_dumps(comparison)), f"raw exception text returned: {comparison!r}"


def test_r2c_pin_verdict_failure_still_logged_with_exc_info(llm_429, caplog):
    """R2(c) / ruling 1(b): the verdict catch keeps its raw diagnostic in the
    log WITH exc_info — once the response carries a constant, the log line
    and Sentry are the only place the raw text lives. The log line itself was
    green at b63a8368; the exc_info half was RED there (the catch logged with
    no traceback). Reddens if exc_info=True is dropped from the catch."""
    from app.services.model_config import verdict_model

    with caplog.at_level(logging.ERROR), \
         patch("app.services.model_router_service.model_router.get_model",
               AsyncMock(return_value=verdict_model())):
        asyncio.run(es.generate_comparison({"name": "One"}, {"name": "Two"}, "bahrain"))
    hits, has_exc = _raw_logged_with_exc_info(caplog, "app.services.extraction_service")
    assert hits, "the verdict failure no longer reaches the extraction_service log"
    assert has_exc, "R2(c): generate_comparison's catch must log with exc_info=True"


def test_r2e_extract_reviews_catch_returns_no_raw_text_and_logs_exc_info(llm_429, caplog):
    """Ruling 1(b): the function-level contract behind the r2e pipeline test —
    extract_reviews' catch returned {"average_rating": None, "error": str(e)}
    at b63a8368 (RED there on both halves: raw text returned, no exc_info).
    The REAL function runs; only the OpenAI call raises. The `error` key stays
    truthy (consumers test it for presence) and average_rating stays None."""
    with caplog.at_level(logging.ERROR):
        reviews, usage = asyncio.run(es.extract_reviews(
            "Tom Ford", "Soleil Neige", "100ml", "no search context", "fragrances"))
    assert llm_429.await_count == 1, "the real extract_reviews never reached the LLM call"
    assert reviews.get("average_rating") is None
    assert reviews.get("error"), "the catch must still mark the failure"
    assert not _leaked(_dumps(reviews)), f"raw exception text returned: {reviews!r}"
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0}
    hits, has_exc = _raw_logged_with_exc_info(caplog, "app.services.extraction_service")
    assert hits, "the reviews failure no longer reaches the extraction_service log"
    assert has_exc, "ruling 1(b): extract_reviews' catch must log with exc_info=True"


def test_r2c_pin_success_payload_is_still_delivered_and_renderable(verdict_pipeline):
    """PIN (green at b63a8368): a failed verdict LLM call does NOT fail the
    comparison — the deterministic-scoring payload is still a success and
    still passes save_comparison's renderability gate. The fix must redact
    the text, not turn this into a failure (that would be a result fork)."""
    from app.services.database_service import _validate_renderable

    result = asyncio.run(scs.StructuredComparisonService().compare_from_text(
        query=f"{_PAIR[0]} vs {_PAIR[1]}", explicit_pair=_PAIR,
        selected_category="fragrances", nocache=True))
    assert verdict_pipeline.await_count >= 1, "the real verdict never reached the LLM call"
    assert result.get("success") is True, result.get("error")
    assert _validate_renderable(result) is True


def test_r2c_sync_200_body_carries_no_raw_text(client, verdict_pipeline):
    """RED at b63a8368 (measured: $.comparison.error on the 200 body). The
    phones' shape: GET /text/compare?product_a=&product_b=."""
    resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
    assert verdict_pipeline.await_count >= 1, "the real verdict never reached the LLM call"
    assert resp.status_code == 200, resp.text
    assert resp.json().get("success") is True
    assert not _leaked(resp.text), f"verdict exception text on the sync 200 body: {_leaked(resp.text)}"


@pytest.mark.parametrize("deadline", ["off", "on"])
def test_r2c_every_sse_event_carries_no_raw_text(client, verdict_pipeline, monkeypatch, deadline):
    """RED at b63a8368 (measured: verdict / settle_complete / complete carry
    $.comparison.error). Both states of ENABLE_FULL_STREAM_DEADLINE, which
    forks how the verdict coroutine is awaited."""
    if deadline == "on":
        monkeypatch.setenv("ENABLE_FULL_STREAM_DEADLINE", "true")
    resp = client.get("/api/v1/text/compare/stream", params=_PAIR_PARAMS)
    assert resp.status_code == 200, resp.text
    events = _sse(resp.text)
    types = [e for e, _ in events]
    assert "complete" in types and "verdict" in types, types
    assert verdict_pipeline.await_count >= 1
    leaking = [e for e, d in events if _leaked(_dumps(d))]
    assert not leaking, f"verdict exception text on SSE events: {leaking}"


def _price_service_globals():
    """Every distinct ``app.services.price_service`` module dict a caller can
    reach: the one in ``sys.modules`` now, plus the ``__globals__`` of every
    ``fetch_shopify_price`` function object bound by name in any loaded module.

    They differ in the one-process CI suite (PR #178 round 2):
    ``tests/test_platform_router.py::test_does_not_import_price_service`` does
    ``del sys.modules[...price_service...]`` as an import-cycle proof, so the
    next import builds a FRESH module object, while ``scs`` still holds the
    ``fetch_shopify_price`` it bound at ITS import (``from
    app.services.price_service import (... fetch_shopify_price ...)``), whose
    ``__globals__`` is the ORPHANED old module dict. A stub set on the fresh
    module never reached the function the orchestrator calls. A reload() keeps
    one dict (re-executes into it), a fresh import makes two; covering the
    set handles both."""
    found = {}
    live = sys.modules.get("app.services.price_service")
    if live is not None:
        found[id(vars(live))] = vars(live)
    for mod in list(sys.modules.values()):
        try:
            fn = vars(mod).get("fetch_shopify_price")
        except TypeError:  # None placeholders / objects without __dict__
            continue
        g = getattr(fn, "__globals__", None)
        if isinstance(g, dict) and g.get("__name__") == "app.services.price_service":
            found[id(g)] = g
    return list(found.values())


@pytest.fixture()
def quota_outage(llm_429, monkeypatch):
    """R2(e) — the REAL orchestrator end to end (no _fetch_product_data stub):
    EVERY OpenAI call (specs, reviews, price, verdict) raises the 429 string,
    as in a real `insufficient_quota` outage. L3 moderation allowed and the
    verdict model id pinned; Serper is keyless (``_serper_unconfigured``);
    the two curl_cffi scrapers this path reaches — the Shopify
    ``/products.json`` catalog and the noon-BH adapter, measured 16 native
    fetches per run that the socket patches cannot see — are stubbed to a
    MISS; every other I/O is left to the conftest neutralisation + the socket
    guard, which now also fails the test on any other curl_cffi transfer.

    The Shopify stub is set in EVERY price_service module dict the running
    code can resolve ``_fetch_shopify_catalog`` from (``_price_service_globals``)
    — not on whichever module object an import happens to return — and is
    restored per key by monkeypatch (``patch.dict`` would clear and refill a
    live module dict on exit)."""
    from app.services.content_safety_service import ContentSafetyService, SafetyResult
    from app.services.model_config import verdict_model

    shopify_miss = AsyncMock(return_value=None)
    for g in _price_service_globals():
        monkeypatch.setitem(g, "_fetch_shopify_catalog", shopify_miss)

    with patch("app.services.model_router_service.model_router.get_model",
               AsyncMock(return_value=verdict_model())), \
         patch.object(ContentSafetyService, "moderate_output",
                      AsyncMock(return_value=SafetyResult(allowed=True))), \
         patch.object(scs, "fetch_noon_price", AsyncMock(return_value=None)):
        yield llm_429


@pytest.mark.parametrize("surface", ["sync", "sse"])
def test_r2e_quota_outage_on_the_phone_path_leaks_no_org_id(client, quota_outage, surface):
    """RED at b63a8368 — R2(e)'s own criterion ("any that reaches a response
    body ... through the orchestrator is IN"), measured: with every OpenAI
    call failing on the phones' explicit_pair shape, the SUCCESS body carries
    the org id at $.products[0].reviews.error, $.products[1].reviews.error
    (extract_reviews' catch, extraction_service.py:~1701) and
    $.comparison.error (generate_comparison, R2(c)). extract_specs /
    extract_price did NOT surface on this path (measured)."""
    if surface == "sync":
        resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
        assert resp.status_code == 200, resp.text
        assert resp.json().get("success") is True
        leaking = _leaked(resp.text)
    else:
        resp = client.get("/api/v1/text/compare/stream", params=_PAIR_PARAMS)
        assert resp.status_code == 200, resp.text
        events = _sse(resp.text)
        assert "complete" in [e for e, _ in events], [e for e, _ in events]
        leaking = [e for e, d in events if _leaked(_dumps(d))]
    assert quota_outage.await_count >= 2, "the real pipeline never reached the LLM calls"
    assert not leaking, f"OpenAI quota error text on the phone-path {surface} surface: {leaking}"


def _persist(full_response):
    """Run the REAL persist path (feedback_service.persist_comparison ->
    database_service.save_comparison) against an in-memory table."""
    from app.services import database_service as ds
    from app.services import feedback_service as fs

    captured = {}

    class _Table:
        def insert(self, record):
            captured["record"] = record
            return SimpleNamespace(
                execute=lambda: SimpleNamespace(data=[{"id": "row-w49", **record}]))

    with patch.object(ds, "get_supabase_client",
                      lambda: SimpleNamespace(table=lambda name: _Table())):
        row_id = asyncio.run(fs.persist_comparison(
            full_response=full_response, query=f"{_PAIR[0]} vs {_PAIR[1]}",
            input_type="text", user_id="user-w49"))
    return row_id, captured.get("record")


def test_r2c_persisted_row_carries_no_raw_text(client, verdict_pipeline):
    """RED at b63a8368 (measured: $.full_response.comparison.error in the
    inserted row)."""
    resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
    assert resp.status_code == 200, resp.text
    row_id, record = _persist(resp.json())
    assert row_id == "row-w49" and record is not None, "save_comparison refused the payload"
    assert not _leaked(_dumps(record)), f"verdict exception text persisted: {_leaked(_dumps(record))}"


def test_r2c_share_payload_carries_no_raw_text(client, verdict_pipeline):
    """RED at b63a8368: the persisted row is served verbatim on the
    UNAUTHENTICATED GET /api/v1/share/{token}."""
    resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
    assert resp.status_code == 200, resp.text
    _, record = _persist(resp.json())
    assert record is not None
    row = {**record, "id": "row-w49", "created_at": "2026-09-23T00:00:00Z"}
    with patch("app.api.share_routes.get_shared_comparison", AsyncMock(return_value=row)):
        shared = client.get("/api/v1/share/W49sharetokenAAAAAAAA")
    assert shared.status_code == 200, shared.text
    assert shared.json().get("comparison", {}).get("full_response"), shared.text
    assert not _leaked(shared.text), f"verdict exception text on the share page: {_leaked(shared.text)}"

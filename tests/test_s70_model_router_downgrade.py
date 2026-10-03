"""Session 70 OAI_OBS item 2 (issue #268, memo R-C14) -- the silent DAILY_4O_CAP
downgrade.

``ModelRouterService.get_model(priority="high")`` returns the standard model
once today's gpt-4o token counter reaches ``SWITCH_THRESHOLD`` (0.80) of
``DAILY_4O_CAP`` (class constant 1_000_000) and says nothing: no log line, no
marker on the response, and the cap cannot be moved without a deploy.

Requirements pinned here (OAI_OBS_SPEC.md R2.1-R2.8 + review corrections C8,
OQ1, OQ4):
  R2.1 ``daily_4o_cap()`` reads env ``DAILY_4O_CAP`` on EVERY call; unset,
       blank, garbage, non-finite and < 1 fall back to the class constant;
       otherwise ``int(float(raw))``.
  R2.2 exactly ONE INFO line per downgrade decision on the module logger.
  R2.4 ``generate_comparison``'s SUCCESS usage dict carries
       ``model_downgraded: True`` when the verdict ran on the standard model
       (cap downgrade AND the 429/rate/quota fallback, OQ1); absent otherwise;
       the failure tuple is byte-identical.
  R2.5-R2.7 the marker reaches ``$.metadata.model_downgraded`` on the sync body
       and the SSE ``settle_complete`` + ``complete`` events, absent-unless-true.
  R2.6 the self-critique regen: the served verdict's marker wins.
  R2.8 the admin gauge reports the cap the router uses.

BASE = 4bd5a09f (OR14; app/ and tests/ are byte-identical to 94c097cd).
RED at BASE: every test whose docstring says RED. PIN (green at BASE): the rest.

Nothing this unit creates is imported at module top (review correction C3): the
new names (``daily_4o_cap``, ...) are looked up inside the test bodies, so the
file collects at base and every PIN runs there.

The pipeline tests copy the minimal W4-9 harness
(tests/test_w49_extraction_catch_redaction.py) instead of importing another
test module: product data stubbed ($0, no network), scoring + the response
builder + the REAL generate_comparison run, only the OpenAI call is mocked at
``guarded_llm_create`` (OR6), L3 moderation allowed, the router's Redis-backed
get_model/record_usage patched. One stub is ADDED to the harness (C4's gate:
no ``[netguard]`` line may name a tests/test_s70_ node): the routes'
``log_search`` (a ``search_logs`` insert that otherwise reaches the
neutralised Supabase sentinel host).
"""
import asyncio
import json
import logging
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.services.extraction_service as es
import app.services.structured_comparison_service as scs
from app.main import app
from app.services.model_router_service import ModelRouterService

_ROUTER_LOGGER = "app.services.model_router_service"

_PAIR = ("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml")
_PAIR_PARAMS = {"product_a": _PAIR[0], "product_b": _PAIR[1],
                "selected_category": "fragrances", "nocache": "true"}

_VERDICT_JSON = json.dumps({
    "winner_index": 0, "winner_declaration": "Soleil Neige wins",
    "winner_reason": "Longer lasting.", "key_tradeoff": "Oud Voyager is cheaper.",
    "product_0_pros": ["Long lasting"], "product_1_pros": ["Cheaper"],
    "product_0_cons": ["Pricier"], "product_1_cons": ["Shorter wear"],
})


# ---------------------------------------------------------------------------
# fixtures (copied from the W4-9 harness, never imported)
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
                 "ENABLE_FULL_STREAM_DEADLINE",
                 # this unit's knob and the model ids it compares against
                 "DAILY_4O_CAP", "OPENAI_MODEL_VERDICT", "OPENAI_MODEL_STANDARD"):
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def _serper_unconfigured(monkeypatch):
    """Pin Serper to "no key" whatever ran first (a reloaded serper_service
    module global would otherwise survive; see the W4-9 harness)."""
    from app.services import serper_service

    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", None)
    assert serper_service._active_serper_key() is None
    yield


@pytest.fixture(autouse=True)
def socket_guard(monkeypatch):
    """Block every non-loopback connect / DNS lookup / curl_cffi transfer and
    fail the test if anything but a ``*.invalid`` sentinel was tried."""
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
            raise OSError(f"s70 socket guard: connect to {host!r} blocked")
        return real_connect(self, addr)

    def _connect_ex(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if not _loop(host):
            attempts.append(("connect_ex", str(host)))
            raise OSError(f"s70 socket guard: connect_ex to {host!r} blocked")
        return real_connect_ex(self, addr)

    def _gai(host, *a, **k):
        if not _loop(host):
            attempts.append(("getaddrinfo", str(host)))
            raise socket.gaierror(f"s70 socket guard: DNS for {host!r} blocked")
        return real_gai(host, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", _gai)

    from urllib.parse import urlsplit

    import curl_cffi.curl as _curl
    import curl_cffi.requests as _curl_requests

    def _curl_host(url):
        return urlsplit(str(url)).hostname or str(url)

    def _curl_request(self, method, url, *a, **k):
        attempts.append(("curl_cffi", _curl_host(url)))
        raise OSError(f"s70 socket guard: curl_cffi {method} {url!r} blocked")

    async def _curl_request_async(self, method, url, *a, **k):
        attempts.append(("curl_cffi", _curl_host(url)))
        raise OSError(f"s70 socket guard: curl_cffi {method} {url!r} blocked")

    def _curl_perform(self, *a, **k):
        attempts.append(("curl_cffi.perform", "?"))
        raise OSError("s70 socket guard: curl_cffi perform blocked")

    monkeypatch.setattr(_curl_requests.Session, "request", _curl_request)
    monkeypatch.setattr(_curl_requests.AsyncSession, "request", _curl_request_async)
    monkeypatch.setattr(_curl.Curl, "perform", _curl_perform)
    yield attempts
    unexpected = [a for a in attempts if not a[1].endswith(".invalid")]
    assert not unexpected, f"s70 socket guard: real egress attempted: {unexpected}"


@pytest.fixture()
def client():
    return TestClient(app)


def _chat_response(content=_VERDICT_JSON):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)
    return resp


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


def _pipeline(routed_model):
    """Context manager stack driving the orchestrators to the REAL
    generate_comparison with the router returning ``routed_model``."""
    from contextlib import ExitStack

    from app.services.content_safety_service import ContentSafetyService, SafetyResult

    stack = ExitStack()
    llm = AsyncMock(return_value=_chat_response())
    stack.enter_context(patch.object(
        scs.StructuredComparisonService, "_fetch_product_data", _fake_fetch))
    stack.enter_context(patch.object(es._llm_breaker, "guarded_llm_create", llm))
    stack.enter_context(patch(
        "app.services.model_router_service.model_router.get_model",
        AsyncMock(return_value=routed_model)))
    stack.enter_context(patch(
        "app.services.model_router_service.model_router.record_usage", AsyncMock()))
    stack.enter_context(patch.object(
        ContentSafetyService, "moderate_output",
        AsyncMock(return_value=SafetyResult(allowed=True))))
    # C4: the fire-and-forget search_logs insert would hit the neutralised
    # Supabase sentinel host (a [netguard] line naming this node).
    stack.enter_context(patch(
        "app.api.text_routes.log_search", AsyncMock(return_value=None)))
    return stack, llm


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


def _router_with_usage(monkeypatch, used):
    svc = ModelRouterService()
    calls = {"n": 0}

    async def _usage():
        calls["n"] += 1
        return used

    monkeypatch.setattr(svc, "_get_4o_usage_today", _usage)
    return svc, calls


def _router_records(caplog):
    return [r for r in caplog.records if r.name == _ROUTER_LOGGER]


def _std():
    from app.services.model_config import standard_model
    return standard_model()


def _vm():
    from app.services.model_config import verdict_model
    return verdict_model()


# ===========================================================================
# R2.2 -- one INFO line per downgrade decision
# ===========================================================================

@pytest.mark.asyncio
async def test_downgrade_logs_exactly_one_info_line(monkeypatch, caplog):
    """RED at base (measured: zero records). At 800,000 used of the default
    1,000,000 cap the router downgrades and says so ONCE, at INFO, on its own
    module logger, with the used/cap/threshold numbers."""
    svc, _ = _router_with_usage(monkeypatch, 800_000)
    caplog.set_level(logging.DEBUG, logger=_ROUTER_LOGGER)
    model = await svc.get_model(priority="high")
    assert model == _std() == "gpt-4o-mini"
    recs = _router_records(caplog)
    assert len(recs) == 1, [r.getMessage() for r in recs]
    rec = recs[0]
    assert rec.levelno == logging.INFO
    msg = rec.getMessage()
    assert "[MODEL_ROUTER] 4o cap reached: routing verdict to gpt-4o-mini" in msg
    assert "used=800000" in msg and "cap=1000000" in msg, msg
    assert msg == (
        "[MODEL_ROUTER] 4o cap reached: routing verdict to gpt-4o-mini "
        "(used=800000 cap=1000000 threshold=0.80)"
    ), msg


@pytest.mark.asyncio
async def test_downgrade_logs_once_per_decision(monkeypatch, caplog):
    """RED at base: three downgrade decisions -> three lines (one each), never
    batched, never deduplicated away."""
    svc, _ = _router_with_usage(monkeypatch, 950_000)
    caplog.set_level(logging.DEBUG, logger=_ROUTER_LOGGER)
    for _ in range(3):
        assert await svc.get_model(priority="high") == _std()
    recs = _router_records(caplog)
    assert len(recs) == 3, [r.getMessage() for r in recs]
    assert all(r.levelno == logging.INFO for r in recs)
    assert all("used=950000 cap=1000000" in r.getMessage() for r in recs)


@pytest.mark.asyncio
async def test_no_router_log_below_threshold_or_standard_priority(monkeypatch, caplog):
    """PIN: below the threshold the verdict model is returned and nothing is
    logged; priority != "high" returns the standard model without reading the
    counter and without logging, even at the full cap."""
    caplog.set_level(logging.DEBUG, logger=_ROUTER_LOGGER)
    svc, _ = _router_with_usage(monkeypatch, 799_999)
    assert await svc.get_model(priority="high") == _vm() == "gpt-4o"
    svc2, calls2 = _router_with_usage(monkeypatch, 1_000_000)
    assert await svc2.get_model(priority="standard") == _std()
    assert await svc2.get_model() == _std()
    assert calls2["n"] == 0
    assert _router_records(caplog) == [], [r.getMessage() for r in _router_records(caplog)]


# ===========================================================================
# R2.1 -- DAILY_4O_CAP read per call
# ===========================================================================

@pytest.mark.asyncio
async def test_daily_cap_env_read_per_call(monkeypatch):
    """RED at base (measured: the env is ignored, 1,000,000 used stays on mini
    with DAILY_4O_CAP=2000000). The SAME instance follows every env change."""
    svc, _ = _router_with_usage(monkeypatch, 1_000_000)
    monkeypatch.setenv("DAILY_4O_CAP", "2000000")
    assert await svc.get_model(priority="high") == "gpt-4o"
    monkeypatch.setenv("DAILY_4O_CAP", "1000000")
    assert await svc.get_model(priority="high") == "gpt-4o-mini"
    monkeypatch.setenv("DAILY_4O_CAP", "1250000")  # 1,000,000 / 1,250,000 == 0.80 -> downgrade
    assert await svc.get_model(priority="high") == "gpt-4o-mini"
    monkeypatch.setenv("DAILY_4O_CAP", "1250001")
    assert await svc.get_model(priority="high") == "gpt-4o"
    monkeypatch.delenv("DAILY_4O_CAP")
    assert await svc.get_model(priority="high") == "gpt-4o-mini"


def test_daily_cap_resolver_unset_returns_class_constant():
    """RED at base (the method is absent): unset -> the class constant, an int."""
    svc = ModelRouterService()
    cap = svc.daily_4o_cap()
    assert cap == 1_000_000 and isinstance(cap, int) and not isinstance(cap, bool)


@pytest.mark.parametrize("raw,expected", [
    ("2000000", 2_000_000),
    (" 2000000 ", 2_000_000),
    ("1_000_000", 1_000_000),
    ("2e6", 2_000_000),
    ("2000000.9", 2_000_000),
    ("1", 1),
])
def test_daily_cap_resolver_accepts_finite_values(monkeypatch, raw, expected):
    """RED at base: finite values >= 1 are read per call and truncated to int
    (float() accepts underscores and exponent form -- measured, spec section 2)."""
    monkeypatch.setenv("DAILY_4O_CAP", raw)
    cap = ModelRouterService().daily_4o_cap()
    assert cap == expected and isinstance(cap, int), (raw, cap)


_GARBAGE = ["abc", "0", "-5", "0.5", "inf", "-inf", "nan", "1e309",
            "1,000,000", "", "   "]


@pytest.mark.parametrize("raw", _GARBAGE)
def test_daily_cap_garbage_resolver_returns_default(monkeypatch, raw):
    """RED at base (the method is absent): garbage, blank, non-positive, < 1
    and NON-FINITE values (float() accepts inf/nan -- they must be rejected)
    fall back to 1,000,000 and never raise."""
    monkeypatch.setenv("DAILY_4O_CAP", raw)
    cap = ModelRouterService().daily_4o_cap()
    assert cap == 1_000_000 and isinstance(cap, int), (raw, cap)


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", _GARBAGE)
async def test_daily_cap_garbage_routing_falls_back(monkeypatch, raw):
    """PIN (green at base because the env is ignored there): with a garbage
    DAILY_4O_CAP the routing equals the default cap's -- 800,000 used is a
    downgrade, 799,999 is not. Never a ZeroDivisionError, never an inf/nan
    comparison that silently routes everything to gpt-4o."""
    monkeypatch.setenv("DAILY_4O_CAP", raw)
    svc, _ = _router_with_usage(monkeypatch, 800_000)
    assert await svc.get_model(priority="high") == "gpt-4o-mini"
    svc2, _ = _router_with_usage(monkeypatch, 799_999)
    assert await svc2.get_model(priority="high") == "gpt-4o"


def test_class_constants_unchanged():
    """PIN: the class constants stay (tests/test_model_router.py and the admin
    gauge read them)."""
    assert ModelRouterService.DAILY_4O_CAP == 1_000_000
    assert isinstance(ModelRouterService.DAILY_4O_CAP, int)
    assert ModelRouterService.SWITCH_THRESHOLD == 0.80


# ===========================================================================
# R2.4 -- the carrier on generate_comparison's success usage dict
# ===========================================================================

async def _run_generate(routed, create_side_effect=None, create_return=None):
    mock_client = AsyncMock()
    if create_side_effect is not None:
        mock_client.chat.completions.create = AsyncMock(side_effect=create_side_effect)
    else:
        mock_client.chat.completions.create = AsyncMock(
            return_value=create_return or _chat_response())
    # #117 -- the 429 fallback goes through client.with_options(max_retries=...);
    # route it back to the same recording create (tests/test_verdict_response_format.py).
    mock_client.with_options = MagicMock(return_value=mock_client)
    record = AsyncMock()
    with patch("app.services.extraction_service.get_client", return_value=mock_client), \
            patch("app.services.model_router_service.model_router.get_model",
                  new=AsyncMock(return_value=routed)), \
            patch("app.services.model_router_service.model_router.record_usage",
                  new=record):
        parsed, usage = await es.generate_comparison(
            product1={"name": "A", "brand": "X"}, product2={"name": "B", "brand": "Y"},
            region="bahrain")
    return parsed, usage, mock_client, record


@pytest.mark.asyncio
async def test_generate_comparison_marks_cap_downgrade():
    """RED at base (measured: usage == {prompt 80, completion 20}, no key).
    The router downgraded, the verdict SUCCEEDED on the standard model."""
    parsed, usage, _, _ = await _run_generate(_std())
    assert "error" not in parsed, parsed
    assert usage.get("model_downgraded") is True, usage
    assert usage["prompt_tokens"] == 80 and usage["completion_tokens"] == 20
    assert "model_downgraded" not in parsed, "parsed (the comparison) is never touched"


@pytest.mark.asyncio
async def test_generate_comparison_marks_429_fallback():
    """RED at base (OQ1 accepted: the verdict ran on the standard model). The
    router chose gpt-4o, the first call 429s, the bounded fallback succeeds."""
    calls = {"n": 0}
    fallback = _chat_response()

    async def _create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("429 rate limit exceeded")
        return fallback

    parsed, usage, mock_client, _ = await _run_generate(_vm(), create_side_effect=_create)
    assert calls["n"] == 2, "expected the primary call + the fallback call"
    assert mock_client.with_options.called
    assert "error" not in parsed, parsed
    assert usage.get("model_downgraded") is True, usage


@pytest.mark.asyncio
async def test_generate_comparison_no_marker_on_verdict_model():
    """PIN: the verdict ran on the configured verdict model -> the key is
    ABSENT and the usage dict is exactly today's."""
    parsed, usage, _, record = await _run_generate(_vm())
    assert "error" not in parsed, parsed
    assert usage == {"prompt_tokens": 80, "completion_tokens": 20}, usage
    record.assert_awaited_once_with("gpt-4o", 100)


@pytest.mark.asyncio
async def test_generate_comparison_failure_has_no_marker():
    """PIN: a downgraded verdict that FAILS (a 429 on the standard model does
    not fall back and re-raises into the catch) returns today's failure tuple
    byte for byte -- no marker on the zero usage dict."""
    async def _create(**kwargs):
        raise RuntimeError("429 rate limit exceeded")

    parsed, usage, _, _ = await _run_generate(_std(), create_side_effect=_create)
    assert parsed == {"winner_index": 0, "error": es.COMPARISON_GENERATION_ERROR}
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0}
    assert "model_downgraded" not in usage


@pytest.mark.asyncio
async def test_generate_comparison_no_marker_when_verdict_model_is_standard(monkeypatch):
    """PIN: when the CONFIGURED verdict model equals the standard model there
    is no downgrade to report (R2.4: standard_model() != verdict_model())."""
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "gpt-4o-mini")
    assert _vm() == _std()
    parsed, usage, _, _ = await _run_generate(_std())
    assert "error" not in parsed, parsed
    assert "model_downgraded" not in usage, usage


# ===========================================================================
# R2.5-R2.7 -- the marker on the sync body and the SSE terminal events
# ===========================================================================

def test_sync_body_carries_model_downgraded(client):
    """RED at base (measured: success True, no comparison.error, the key is
    absent from metadata)."""
    stack, llm = _pipeline(_std())
    with stack:
        resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
    assert llm.await_count >= 1, "the real generate_comparison never reached the LLM call"
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    assert body.get("success") is True, body.get("error")
    assert "error" not in (body.get("comparison") or {}), body.get("comparison")
    assert body["metadata"].get("model_downgraded") is True, sorted(body["metadata"])


@pytest.mark.parametrize("deadline", ["off", "on"])
def test_sse_settle_and_complete_carry_model_downgraded(client, monkeypatch, deadline):
    """RED at base (the key is absent although the verdict succeeded). With
    ENABLE_FULL_STREAM_DEADLINE unset and ``true`` (the verdict then runs under
    the residual-budget ``asyncio.wait_for``), BOTH terminal events --
    ``settle_complete`` and ``complete`` -- carry ``metadata.model_downgraded``
    (R2.4 carrier = generate_comparison's success usage dict, R2.5, R2.7)."""
    if deadline == "on":
        monkeypatch.setenv("ENABLE_FULL_STREAM_DEADLINE", "true")
    stack, llm = _pipeline(_std())
    with stack:
        resp = client.get("/api/v1/text/compare/stream", params=_PAIR_PARAMS)
    assert llm.await_count >= 1
    assert resp.status_code == 200
    events = _sse(resp.text)
    names = [e for e, _ in events]
    settle = [d for e, d in events if e == "settle_complete"]
    done = [d for e, d in events if e == "complete"]
    assert settle and done, names
    for payload in (settle[-1], done[-1]):
        assert payload.get("success") is True, payload.get("error")
        assert "error" not in (payload.get("comparison") or {}), payload.get("comparison")
    markers = [p["metadata"].get("model_downgraded") for p in (settle[-1], done[-1])]
    assert markers == [True, True], ("settle_complete, complete", markers)


@pytest.mark.parametrize("surface", ["sync", "sse_off", "sse_on"])
def test_no_marker_key_when_verdict_model_used(client, monkeypatch, surface):
    """PIN: the verdict ran on the verdict model -> ``model_downgraded`` is
    ABSENT (not False) from metadata, keeping a non-downgraded response
    byte-identical to base (the W4-12 ``verdict_scrubbed`` precedent)."""
    if surface == "sse_on":
        monkeypatch.setenv("ENABLE_FULL_STREAM_DEADLINE", "true")
    stack, llm = _pipeline(_vm())
    with stack:
        if surface == "sync":
            resp = client.get("/api/v1/text/compare", params=_PAIR_PARAMS)
            assert resp.status_code == 200, resp.text[:300]
            payloads = [resp.json()]
        else:
            resp = client.get("/api/v1/text/compare/stream", params=_PAIR_PARAMS)
            assert resp.status_code == 200
            events = _sse(resp.text)
            payloads = [d for e, d in events if e in ("settle_complete", "complete")]
            assert payloads, [e for e, _ in events]
    assert llm.await_count >= 1
    for payload in payloads:
        assert payload.get("success") is True, payload.get("error")
        assert "model_downgraded" not in payload["metadata"], sorted(payload["metadata"])


# ===========================================================================
# R2.6 -- the self-critique regeneration (ENABLE_SELF_CRITIQUE, default OFF)
# ===========================================================================

_REGEN_CASES = {
    # id: (original marker, regen usage marker, regenerated, timeout, expected)
    "regen_on_mini_served": (False, True, True, False, True),        # RED at base
    "regen_on_verdict_model_served": (True, None, True, False, False),  # RED at base
    "regen_rejected_keeps_original_false": (False, True, False, False, False),  # PIN
    "regen_rejected_keeps_original_true": (True, None, False, False, True),     # PIN
    "critique_timeout_keeps_original": (False, True, True, True, False),        # PIN
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(_REGEN_CASES))
async def test_self_critique_regen_marker(monkeypatch, case):
    """R2.6: when the regenerated verdict is SERVED (outcome.regenerated True)
    the marker becomes the regen's own value; a rejected regen or the 8 s
    critique timeout keeps the original verdict's value. Driven directly
    through ``_apply_self_critique`` with ``critique_and_maybe_regenerate``
    patched to call the real ``_regenerate`` closure. RED at base on the two
    'served' cases; the other three are PINs."""
    from app.services import verdict_critique_service as vcs

    original, regen_marker, regenerated, timeout, expected = _REGEN_CASES[case]
    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")

    original_cmp = {"winner_index": 0, "winner_reason": "original"}
    regen_cmp = {"winner_index": 0, "winner_reason": "regenerated"}
    regen_usage = {"prompt_tokens": 5, "completion_tokens": 7}
    if regen_marker is not None:
        regen_usage["model_downgraded"] = regen_marker
    regen_calls = {"n": 0}

    async def _fake_generate(*args, **kwargs):
        regen_calls["n"] += 1
        return dict(regen_cmp), dict(regen_usage)

    monkeypatch.setattr(scs, "generate_comparison", _fake_generate)

    critique = vcs.CritiqueResult(
        axis_scores={"specificity": 3}, needs_regen=True, low_axes=["specificity"],
        regen_reason="specificity", critic_model="gpt-4o-mini",
        usage={"prompt_tokens": 1, "completion_tokens": 1},
    )

    async def _fake_critique(*, comparison, product_names, regenerate,
                             pain_workflow_context=None, comparison_quality="normal"):
        new_cmp = await regenerate(critique)
        if timeout:
            raise asyncio.TimeoutError()
        return vcs.CritiqueOutcome(
            final_comparison=new_cmp if regenerated else comparison,
            critique=critique, regenerated=regenerated,
            critique_usage={"prompt_tokens": 1, "completion_tokens": 1},
        )

    monkeypatch.setattr(vcs, "critique_and_maybe_regenerate", _fake_critique)

    svc = scs.StructuredComparisonService()
    svc._verdict_model_downgraded = original
    served = await svc._apply_self_critique(
        comparison=dict(original_cmp), product_names=["A", "B"],
        regen_args={"product1": {"name": "A"}, "product2": {"name": "B"},
                    "region": "bahrain"},
    )
    assert regen_calls["n"] == 1, "the regenerate closure never ran"
    if regenerated and not timeout:
        assert served == regen_cmp
    else:
        assert served == original_cmp
    assert getattr(svc, "_verdict_model_downgraded", False) is expected, (
        case, getattr(svc, "_verdict_model_downgraded", "<absent>"))


# ===========================================================================
# R2.8 -- the admin gauge reads the cap the router uses
# ===========================================================================

def _gauge(client, monkeypatch, redis_value):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    with patch("app.services.cache_service._redis_get", return_value=redis_value), \
            patch("app.api.admin_routes.get_usage_summary",
                  return_value={"providers": {}, "circuit_breakers": {}}):
        resp = client.get("/api/v1/admin/costs/gauges",
                          headers={"X-Admin-Key": "test-admin-key"})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()["openai_4o_today"]


def test_admin_gauge_uses_env_cap(client, monkeypatch):
    """RED at base (the gauge reads the class constant): DAILY_4O_CAP=2000000
    and 500,000 used -> cap 2,000,000, 25 %."""
    monkeypatch.setenv("DAILY_4O_CAP", "2000000")
    gauge = _gauge(client, monkeypatch, "500000")
    assert gauge == {"used": 500000, "cap": 2000000, "pct": 25.0}, gauge


def test_admin_gauge_unset_env_is_byte_identical(client, monkeypatch):
    """PIN: with the env unset the gauge is exactly today's (TestCostsGauges)."""
    gauge = _gauge(client, monkeypatch, "500000")
    assert gauge == {"used": 500000, "cap": 1000000, "pct": 50.0}, gauge


def test_admin_gauge_garbage_env_falls_back(client, monkeypatch):
    """PIN at base (the env is ignored there); stays green after R2.8 because
    garbage falls back to the default cap."""
    monkeypatch.setenv("DAILY_4O_CAP", "1,000,000")
    gauge = _gauge(client, monkeypatch, "500000")
    assert gauge == {"used": 500000, "cap": 1000000, "pct": 50.0}, gauge

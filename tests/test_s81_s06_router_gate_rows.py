"""S81-06 ANTHROPIC-ROUTER: the rows the RED gate told GREEN to ADD (GATE_S81_06
GC-1, GC-2, GC-3, GC-4, GC-5; the S81-05 GC-1 precedent), kept in their own file so
the frozen RED file (tests/test_s81_s06_anthropic_router.py) keeps its sha256.

Every row reuses the RED file's hermetic harness (the ModuleSpec'd fake anthropic
SDK installed by its autouse fixture, the consent recorder, the Redis fake, the
route harness); PIN halves run with the FULL unit configuration (ruling B1).
"""

import asyncio
import logging

import pytest

from tests.test_s81_s06_anthropic_router import (  # noqa: F401  (the autouse fixture + helpers)
    ANTH,
    ESC_FLAG,
    HAIKU,
    JPEG_BYTES,
    PIN_OFF,
    PRE_FLAG,
    ROLE_FLAGS,
    RateLimitError,
    _base_dispatch_kwargs,
    _capture,
    _full_config,
    _knobs,
    _mod_setup,
    _open_state,
    _route_harness,
    _router,
    _run,
    _s06_env,
    _set_flag,
    abs_,
    c_msg,
    consent,
    css,
    es,
    redis_fake,
    run_site,
    scs,
    urlsvc,
)
from app.services import cache_service  # noqa: E402

FLAG_ROWS = tuple(ROLE_FLAGS.values())


# ===========================================================================
# G01 (GC-2): the Claude moderation classifier fails CLOSED on malformed JSON
# ===========================================================================
@pytest.mark.parametrize("reply", ["not json", '["flagged"]', '{"flagged": tru'])
def test_g01_moderation_malformed_json_fails_closed(monkeypatch, consent, reply):
    """GC-2: MODERATION ON + consent 3: a malformed or non-object classifier answer is
    SafetyResult(allowed=False, reason='malformed'); moderations.create is never called.
    """
    mods = _mod_setup(monkeypatch, consent)
    ANTH.default = c_msg(reply)
    res = _run(
        css.get_content_safety_service().moderate_output("a product description text")
    )
    assert ANTH.calls, "the Claude classifier was never called"
    assert (res.allowed, res.reason) == (False, "malformed"), res
    assert mods == []


# ===========================================================================
# G02 (GC-3 / R-S06-12): the comparison cache key gains the provider axis ON only
# ===========================================================================
BASE_KEY = "comparison:bahrain:apple_iphone_17_vs_galaxy_s25"


@pytest.mark.parametrize("off_value", PIN_OFF)
def test_g02a_flag_off_comparison_key_byte_identical(monkeypatch, consent, off_value):
    """GC-3 PIN (FULL config): every role flag OFF (each spelling) -> the base key
    literal, the consent accessor never read."""
    _full_config(monkeypatch, consent)
    monkeypatch.setenv(ESC_FLAG, "true")
    monkeypatch.setenv(PRE_FLAG, "true")
    for name in FLAG_ROWS:
        _set_flag(monkeypatch, name, off_value)
    key = cache_service.get_comparison_cache_key(
        ["Apple iPhone 17", "Galaxy S25"], "bahrain"
    )
    assert key == BASE_KEY
    assert consent.reads == []


def test_g02b_comparison_key_axis_only_when_the_verdict_routes_to_claude(
    monkeypatch, consent
):
    """GC-3 RED: VERDICT ON + consent 3 -> ':anthropic:<model>'; consent 2 with PRE_V3 ON
    (OpenAI serves) -> the base key; TEXT ON alone -> the base key."""
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_VERDICT", "true")
    key = cache_service.get_comparison_cache_key(
        ["Apple iPhone 17", "Galaxy S25"], "bahrain"
    )
    assert key == BASE_KEY + ":anthropic:" + HAIKU
    consent.set(2, "ok")
    monkeypatch.setenv(PRE_FLAG, "true")
    assert (
        cache_service.get_comparison_cache_key(
            ["Apple iPhone 17", "Galaxy S25"], "bahrain"
        )
        == BASE_KEY
    )
    monkeypatch.delenv("ENABLE_ANTHROPIC_VERDICT")
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    consent.set(3)
    assert (
        cache_service.get_comparison_cache_key(
            ["Apple iPhone 17", "Galaxy S25"], "bahrain"
        )
        == BASE_KEY
    )


# ===========================================================================
# G03 (GC-3 / R-S06-12): the four dispatch-level refusal log sites log at WARNING by type
# ===========================================================================
def _records(caplog, needle):
    return [r for r in caplog.records if needle in r.getMessage()]


def test_g03a_parse_and_url_sites_warn_by_type_under_on(monkeypatch, consent, caplog):
    """GC-3 RED: TEXT ON + consent 2 + PRE_V3 OFF: the parse and url-extract refusals log
    ONE WARNING carrying the type name (no exc_info, no ERROR record)."""
    _knobs(monkeypatch)
    consent.set(2, "ok")
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    caplog.set_level(logging.INFO)
    _run(_capture(run_site("parse", monkeypatch)))
    _run(_capture(run_site("url_extract", monkeypatch)))
    for needle in ("Product parsing error", "AI extraction error"):
        recs = _records(caplog, needle)
        assert recs and all(r.levelno == logging.WARNING for r in recs), (needle, recs)
        assert all(r.exc_info is None for r in recs), needle
        assert any(
            r.getMessage().endswith("ConsentUpdateRequiredError") for r in recs
        ), needle


def test_g03b_verdict_site_warns_by_type_under_on(monkeypatch, consent, caplog):
    """GC-3 RED: VERDICT ON + consent 3 + a Claude 429: the verdict non-delivery logs ONE
    WARNING by type and no exc_info ERROR."""
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_VERDICT", "true")
    ANTH.script = [RateLimitError("rate limit")]
    caplog.set_level(logging.INFO)
    st, _out = _run(_capture(run_site("verdict", monkeypatch)))
    assert st == "raised"
    recs = _records(caplog, "Comparison generation error")
    assert recs and all(
        r.levelno == logging.WARNING and r.exc_info is None for r in recs
    ), recs
    assert recs[0].getMessage().endswith("AnthropicDispatchError")


def test_g03c_flag_off_parse_site_keeps_the_base_error_line(
    monkeypatch, consent, caplog
):
    """GC-3 PIN (FULL config): role flags OFF, an LLMUnavailableError at the parse site
    keeps the base exc_info ERROR line (bytes unchanged)."""
    _full_config(monkeypatch, consent)
    caplog.set_level(logging.INFO)
    _run(
        _capture(
            run_site(
                "parse",
                monkeypatch,
                oai_exc=abs_.LLMUnavailableError("openai breaker open"),
            )
        )
    )
    recs = _records(caplog, "Product parsing error")
    assert (
        len(recs) == 1 and recs[0].levelno == logging.ERROR and recs[0].exc_info
    ), recs
    assert recs[0].getMessage() == "Product parsing error: openai breaker open"


def test_g03d_camera_refusal_warns_by_type(monkeypatch, consent, request, caplog):
    """GC-3 RED: the camera refusal (VISION ON, consent None, PRE_V3 OFF) logs the vision
    exit at WARNING by type, never the exception text at ERROR."""
    from app.api import image_routes

    _knobs(monkeypatch)
    consent.set(None)
    monkeypatch.setenv("ENABLE_ANTHROPIC_VISION", "true")

    async def _identify(images):
        raise AssertionError("identify ran")

    monkeypatch.setattr(image_routes, "identify_products", _identify)
    client, led, _user = _route_harness(monkeypatch, request)
    monkeypatch.setattr(
        image_routes, "consume_comparison_credit", led.consume, raising=False
    )
    monkeypatch.setattr(
        image_routes, "refund_comparison_credit", led.refund, raising=False
    )
    caplog.set_level(logging.INFO)
    files = [
        ("images", ("a.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
        ("images", ("b.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
    ]
    resp = client.post("/api/v1/image/identify", files=files)
    assert resp.status_code == 503
    recs = _records(caplog, "[IMAGE] Vision call failed")
    assert len(recs) == 1 and recs[0].levelno == logging.WARNING, recs
    assert (
        recs[0].getMessage() == "[IMAGE] Vision call failed: ConsentUpdateRequiredError"
    )


# ===========================================================================
# G04 (GC-3 / R-S06-7): the additive /health anthropic breaker key
# ===========================================================================
def test_g04_health_anthropic_breaker_key_only_after_a_role_flag_was_on(
    monkeypatch, consent
):
    """GC-3: a fresh process with every role flag OFF (FULL config, a site dispatched)
    -> no `anthropic_breaker` key; once a role flag was ON -> the key is present."""
    import app.main as app_main

    _full_config(monkeypatch, consent)
    _run(run_site("parse", monkeypatch))
    body = _run(app_main.health_check())
    assert "anthropic_breaker" not in body, body
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    _router().decide("text")
    body = _run(app_main.health_check())
    assert set(body.get("anthropic_breaker") or {}) == {
        "state",
        "memo_age_seconds",
    }, body


# ===========================================================================
# G05 (GC-1 / R-S06-4): the preflight AND covers moderation and the enabled critic
# ===========================================================================
def _preflight(
    monkeypatch, redis_fake, roles, openai_open, anth_open, self_critique=False
):
    monkeypatch.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
    for role, name in ROLE_FLAGS.items():
        _set_flag(monkeypatch, name, "true" if role in roles else None)
    _set_flag(monkeypatch, "ENABLE_SELF_CRITIQUE", "true" if self_critique else None)
    redis_fake.data.clear()
    if openai_open:
        redis_fake.data[abs_._circuit_key("openai")] = _open_state(5)
    if anth_open:
        redis_fake.data[abs_._circuit_key("anthropic")] = _open_state(5)
    abs_._reset_openai_breaker_cache()
    _router()._reset_router_state()
    return scs._llm_preflight_short_circuits()


@pytest.mark.parametrize(
    "cell",
    [
        # (roles ON, openai OPEN, anthropic OPEN, ENABLE_SELF_CRITIQUE) -> short-circuits?
        (
            ({"moderation"}, False, True, False),
            True,
        ),  # moderation on Claude, text/verdict on OpenAI
        (({"moderation"}, True, False, False), True),
        (({"moderation"}, False, False, False), False),
        (
            ({"text", "verdict"}, True, False, True),
            True,
        ),  # critic enabled, still on OpenAI
        (
            ({"text", "verdict"}, True, False, False),
            False,
        ),  # critic not enabled: OpenAI unused
        (({"text", "verdict", "critic"}, True, False, True), False),
        (({"text", "verdict", "critic"}, False, True, True), True),
    ],
)
def test_g05_preflight_and_covers_moderation_and_critic(
    monkeypatch, consent, redis_fake, cell
):
    """GC-1 RED: moderation routed to Claude adds the anthropic breaker; the critic adds
    its provider when ENABLE_SELF_CRITIQUE is ON."""
    _knobs(monkeypatch)
    consent.set(3)
    (roles, openai_open, anth_open, self_critique), want = cell
    got = _preflight(
        monkeypatch, redis_fake, roles, openai_open, anth_open, self_critique
    )
    assert got is want, cell


# ===========================================================================
# G06 (R-S06-2 / R-S06-3): the URL compare maps an LLMUnavailableError to LLM_UNAVAILABLE
# ===========================================================================
def _product(name):
    return {
        "name": name,
        "brand": "Brand",
        "category": "electronics",
        "price": {"amount": 1.0},
    }


def test_g06a_url_extraction_llm_unavailable_is_coded_under_on(monkeypatch, consent):
    """RED: TEXT ON: an extraction that raised an LLMUnavailableError makes compare_from_urls
    return the coded LLM_UNAVAILABLE result (never the codeless 400)."""
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    calls = []

    async def _extract(url, url_mode_v2=False):
        calls.append(url)
        raise _router().AnthropicDispatchError("X", 529, True)

    monkeypatch.setattr(urlsvc, "extract_from_url", _extract)
    out = _run(
        urlsvc.compare_from_urls(
            "https://a.example.test/p/1", "https://b.example.test/p/2"
        )
    )
    assert out == {
        "success": False,
        "code": "LLM_UNAVAILABLE",
        "error": scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
    }, out
    assert len(calls) == 2


def test_g06b_url_verdict_llm_unavailable_is_coded_under_on(monkeypatch, consent):
    """RED: VERDICT ON: generate_comparison re-raises the verdict non-delivery and
    compare_from_urls returns the coded LLM_UNAVAILABLE result (never a 500)."""
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_VERDICT", "true")

    async def _extract(url, url_mode_v2=False):
        return {"success": True, "product": _product(url[-1])}

    async def _cat(products, selected, parser_path=False):
        return "electronics", False, None

    async def _verdict(*a, **k):
        raise _router().AnthropicRefusalError()

    monkeypatch.setattr(urlsvc, "extract_from_url", _extract)
    monkeypatch.setattr(scs, "_resolve_pair_category", _cat)
    monkeypatch.setattr(es, "generate_comparison", _verdict)
    st, out = _run(
        _capture(
            urlsvc.compare_from_urls(
                "https://a.example.test/p/1", "https://b.example.test/p/2"
            )
        )
    )
    assert st == "ok" and isinstance(out, dict), (st, out)
    assert out.get("code") == "LLM_UNAVAILABLE" and out.get("success") is False, out


def test_g06c_flag_off_url_paths_unchanged(monkeypatch, consent):
    """PIN (FULL config): role flags OFF, an extraction raising an LLMUnavailableError keeps
    the base codeless body; a verdict raising it propagates as at base."""
    _full_config(monkeypatch, consent)

    async def _extract(url, url_mode_v2=False):
        raise abs_.LLMUnavailableError("openai breaker open")

    monkeypatch.setattr(urlsvc, "extract_from_url", _extract)
    out = _run(
        urlsvc.compare_from_urls(
            "https://a.example.test/p/1", "https://b.example.test/p/2"
        )
    )
    assert out.get("success") is False and "code" not in out
    assert out.get("error") == "Could not extract both products"

    async def _extract_ok(url, url_mode_v2=False):
        return {"success": True, "product": _product(url[-1])}

    async def _cat(products, selected, parser_path=False):
        return "electronics", False, None

    async def _verdict(*a, **k):
        raise abs_.LLMUnavailableError("openai breaker open")

    monkeypatch.setattr(urlsvc, "extract_from_url", _extract_ok)
    monkeypatch.setattr(scs, "_resolve_pair_category", _cat)
    monkeypatch.setattr(es, "generate_comparison", _verdict)
    st, exc = _run(
        _capture(
            urlsvc.compare_from_urls(
                "https://a.example.test/p/1", "https://b.example.test/p/2"
            )
        )
    )
    assert st == "raised" and isinstance(exc, abs_.LLMUnavailableError)


# ===========================================================================
# G07 (GC-4): the /url/compare consent gate runs BEFORE the credit reserve
# ===========================================================================
@pytest.mark.parametrize("verb", ["post", "get"])
def test_g07_url_gate_before_the_reserve(monkeypatch, consent, request, verb):
    """GC-4 RED: TEXT ON, consent None, PRE_V3 OFF: the coded 503 with NOTHING consumed and
    nothing refunded."""
    from app.api import url_routes

    _knobs(monkeypatch)
    consent.set(None)
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")

    async def _cmp(*a, **k):
        raise AssertionError("compare_from_urls ran")

    monkeypatch.setattr(url_routes, "compare_from_urls", _cmp)
    client, led, _user = _route_harness(monkeypatch, request)
    u1, u2 = (
        "https://www.example-retailer.test/p/a",
        "https://www.example-retailer.test/p/b",
    )
    if verb == "post":
        resp = client.post("/api/v1/url/compare", json={"url1": u1, "url2": u2})
    else:
        resp = client.get("/api/v1/url/compare", params={"url1": u1, "url2": u2})
    assert resp.status_code == 503 and resp.json().get("code") == "LLM_UNAVAILABLE"
    assert led.consumes == [] and led.refunds == []


# ===========================================================================
# G08 (GC-5): the camera gate refuses when ANY role the request reaches is ON
# ===========================================================================
@pytest.mark.parametrize("role", ["text", "verdict", "critic", "moderation"])
def test_g08_camera_gate_covers_the_compare_roles(monkeypatch, consent, request, role):
    """GC-5 RED: VISION OFF, one compare role ON, consent None, PRE_V3 OFF: /image/identify
    refuses BEFORE identify_products with the coded 503 (no paid vision call)."""
    from app.api import image_routes

    _knobs(monkeypatch)
    consent.set(None)
    monkeypatch.setenv(ROLE_FLAGS[role], "true")
    calls = []

    async def _identify(images):
        calls.append(len(images))
        return {"products": [], "error": "x", "tokens_used": 0, "cost": 0}

    monkeypatch.setattr(image_routes, "identify_products", _identify)
    client, led, _user = _route_harness(monkeypatch, request)
    monkeypatch.setattr(
        image_routes, "consume_comparison_credit", led.consume, raising=False
    )
    monkeypatch.setattr(
        image_routes, "refund_comparison_credit", led.refund, raising=False
    )
    files = [
        ("images", ("a.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
        ("images", ("b.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
    ]
    resp = client.post("/api/v1/image/identify", files=files)
    assert calls == [] and resp.status_code == 503, (calls, resp.status_code)
    assert resp.json().get("code") == "LLM_UNAVAILABLE"
    assert len(led.refunds) == len(led.consumes)


def test_g08b_flag_off_camera_reaches_identify(monkeypatch, consent, request):
    """GC-5 PIN (FULL config, consent None): role flags OFF -> identify_products runs once
    (the base path; the refusal gate reads five flags and nothing else)."""
    from app.api import image_routes

    _full_config(monkeypatch, consent, consent_value=None)
    calls = []

    async def _identify(images):
        calls.append(len(images))
        return {"products": [], "error": "x", "tokens_used": 0, "cost": 0}

    monkeypatch.setattr(image_routes, "identify_products", _identify)
    client, led, _user = _route_harness(monkeypatch, request)
    monkeypatch.setattr(
        image_routes, "consume_comparison_credit", led.consume, raising=False
    )
    monkeypatch.setattr(
        image_routes, "refund_comparison_credit", led.refund, raising=False
    )
    files = [
        ("images", ("a.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
        ("images", ("b.jpg", JPEG_BYTES + b"\x00" * 2048, "image/jpeg")),
    ]
    client.post("/api/v1/image/identify", files=files)
    assert calls == [2] and consent.reads == []


def test_g09_escalation_alone_never_routes(monkeypatch, consent):
    """PIN: ENABLE_SONNET_ESCALATION alone with a bound-scope attempt binds nothing."""
    _full_config(monkeypatch, consent)
    monkeypatch.setenv(ESC_FLAG, "true")

    async def _go():
        return _router().bind_request_scope(), _router().escalation_allowed()

    assert _run(_go()) == (None, False)
    assert asyncio.iscoroutinefunction(_router().route)

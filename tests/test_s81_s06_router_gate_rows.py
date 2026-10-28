"""S81-06 ANTHROPIC-ROUTER: the rows the RED gate told GREEN to ADD (GATE_S81_06
GC-1, GC-2, GC-3, GC-4, GC-5; the S81-05 GC-1 precedent), kept in their own file so
the frozen RED file (tests/test_s81_s06_anthropic_router.py) keeps its sha256.

Every row reuses the RED file's hermetic harness (the ModuleSpec'd fake anthropic
SDK installed by its autouse fixture, the consent recorder, the Redis fake, the
route harness); PIN halves run with the FULL unit configuration (ruling B1).
"""

import ast
import asyncio
import json
import logging
import pathlib

import pytest

from tests.test_s81_s06_anthropic_router import (  # noqa: F401  (the autouse fixture + helpers)
    ANTH,
    ESC_FLAG,
    HAIKU,
    JPEG_BYTES,
    P1,
    P2,
    PIN_OFF,
    PRE_FLAG,
    ROLE_FLAGS,
    TERMINAL,
    DispatchRec,
    RateLimitError,
    _base_dispatch_kwargs,
    _capture,
    _classify_case,
    _full_config,
    _knobs,
    _mod_setup,
    _open_state,
    _patch_router_models,
    _route,
    _route_harness,
    _router,
    _run,
    _s06_env,
    _set_flag,
    _sym,
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


# ===========================================================================
# FIX ROUND 1 (RULINGS_FIX1_S81_06): F1-6, F1-7, F1-8, F1-14
# ===========================================================================
FACTORY_SENTINEL = "FACTORY" + "BROKE" + "k4"


def _factory_boom(**kw):
    raise RuntimeError("factory broke " + FACTORY_SENTINEL)


def _no_sentinel_logged(caplog, needle):
    return [r.getMessage() for r in caplog.records if needle in r.getMessage()]


# ---------------------------------------------------------------------------
# G10 (F1-6; correctness MAJ-1; mutant A-IMPLARM): the REAL impl path of the REST
# entry maps an in-impl LLMUnavailableError to the coded LLM_UNAVAILABLE result
# ---------------------------------------------------------------------------
async def _parse_raises(self, query):
    raise abs_.LLMUnavailableError("verdict unavailable")


@pytest.mark.parametrize("flag", FLAG_ROWS)
def test_g10_rest_impl_llm_unavailable_is_coded_under_on(monkeypatch, consent, flag):
    """F1-6 (R-S06-2 on the REAL impl body): a role flag ON + consent 3, an
    LLMUnavailableError raised INSIDE _compare_from_text_impl (the parse-step seam)
    reaches the REST entry as the coded LLM_UNAVAILABLE result (the impl's own
    except arm maps it; the wrapper's arm is unreachable for an in-impl error)."""
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv(flag, "true")
    monkeypatch.setattr(
        scs.StructuredComparisonService, "_parse_with_budget", _parse_raises
    )
    st, res = _run(
        _capture(scs.StructuredComparisonService().compare_from_text("a vs b"))
    )
    assert st == "ok" and isinstance(res, dict), (st, res)
    assert res.get("success") is False and res.get("code") == "LLM_UNAVAILABLE", res


@pytest.mark.parametrize("off_value", PIN_OFF)
def test_g10b_flag_off_rest_impl_keeps_the_base_internal_error(
    monkeypatch, consent, off_value
):
    """F1-6 PIN (FULL config, ruling B1): every role flag OFF (each spelling), the
    same in-impl LLMUnavailableError -> the base INTERNAL_ERROR body; the consent
    accessor is never read."""
    _full_config(monkeypatch, consent)
    monkeypatch.setenv(ESC_FLAG, "true")
    monkeypatch.setenv(PRE_FLAG, "true")
    for name in FLAG_ROWS:
        _set_flag(monkeypatch, name, off_value)
    monkeypatch.setattr(
        scs.StructuredComparisonService, "_parse_with_budget", _parse_raises
    )
    st, res = _run(
        _capture(scs.StructuredComparisonService().compare_from_text("a vs b"))
    )
    assert st == "ok" and isinstance(res, dict), (st, res)
    assert res.get("success") is False and res.get("code") == "INTERNAL_ERROR", res
    assert consent.reads == []


# ---------------------------------------------------------------------------
# G11 (F1-7; correctness MAJ-2): client construction inside the guarded region;
# the moderation classifier fails CLOSED on every failure class
# ---------------------------------------------------------------------------
def test_g11a_moderation_client_factory_error_fails_closed(
    monkeypatch, consent, caplog
):
    """F1-7: MODERATION ON + consent 3 + the key set, the client factory raising a
    non-typed error -> SafetyResult(allowed=False, reason='unavailable');
    moderations.create is never called; the error text is never logged."""
    caplog.set_level(logging.DEBUG)
    mods = _mod_setup(monkeypatch, consent)
    monkeypatch.setattr(_router(), "_anthropic_client_factory", _factory_boom)
    _router()._reset_router_state()
    res = _run(
        css.get_content_safety_service().moderate_output("a synthetic shopping text")
    )
    assert (res.allowed, res.reason) == (False, "unavailable"), res
    assert mods == []
    assert _no_sentinel_logged(caplog, FACTORY_SENTINEL) == []


def test_g11b_verdict_client_factory_error_is_a_non_delivery(
    monkeypatch, consent, caplog
):
    """F1-7 (R-S06-2): VERDICT ON + consent 3, the client factory raising a
    non-typed error -> generate_comparison raises an LLMUnavailableError (the
    non-delivery), never the base degraded delivery dict; no error text logged."""
    caplog.set_level(logging.DEBUG)
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_VERDICT", "true")
    monkeypatch.setattr(_router(), "_anthropic_client_factory", _factory_boom)
    _router()._reset_router_state()
    _patch_router_models(monkeypatch)
    st, out = _run(
        _capture(es.generate_comparison(P1, P2, "bahrain", category="electronics"))
    )
    assert st == "raised" and isinstance(out, abs_.LLMUnavailableError), (st, out)
    assert _no_sentinel_logged(caplog, FACTORY_SENTINEL) == []


def test_g11c_client_factory_error_is_a_typed_dispatch_error_and_releases_the_probe(
    monkeypatch, consent, redis_fake, caplog
):
    """F1-7: TEXT ON + consent 3, the breaker OPEN past its cooldown (the half-open
    probe admitted), the client factory raising -> AnthropicDispatchError
    ('RuntimeError', None, False) with no cause and no SDK text, no record_failure,
    one WARNING by type (never the error text), and the held probe released (the
    next request is admitted)."""
    caplog.set_level(logging.DEBUG)
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    redis_fake.data[abs_._circuit_key("anthropic")] = _open_state(
        abs_.CB_RECOVERY_TIMEOUT + 5
    )
    fails = []
    real_fail = abs_.record_failure
    monkeypatch.setattr(
        abs_, "record_failure", lambda p: (fails.append(p), real_fail(p))[1]
    )
    real_factory = _router()._anthropic_client_factory
    monkeypatch.setattr(_router(), "_anthropic_client_factory", _factory_boom)
    _router()._reset_router_state()
    st, exc = _run(
        _capture(_route("parse", DispatchRec(), **_base_dispatch_kwargs("parse")))
    )
    disp = _sym("AnthropicDispatchError")
    assert st == "raised" and isinstance(exc, disp), (st, exc)
    assert (exc.error_class, exc.status, exc.transient) == ("RuntimeError", None, False)
    assert exc.__cause__ is None and exc.__suppress_context__ is True
    assert str(exc) == "anthropic dispatch suppressed"
    assert fails == []
    assert ANTH.calls == []
    warns = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.WARNING and "RuntimeError" in r.getMessage()
    ]
    assert warns, "no WARNING by type for the factory failure"
    assert _no_sentinel_logged(caplog, FACTORY_SENTINEL) == []
    monkeypatch.setattr(_router(), "_anthropic_client_factory", real_factory)
    _router()._reset_router_state()
    st, _res = _run(
        _capture(_route("parse", DispatchRec(), **_base_dispatch_kwargs("parse")))
    )
    assert st == "ok" and len(ANTH.calls) == 1, "the held probe was not released"


def test_g11d_moderation_any_other_failure_fails_closed(monkeypatch, consent):
    """F1-7: MODERATION ON + consent 3, a failure of any other class inside the
    classifier step (not an LLMUnavailableError / ValueError / TypeError) ->
    SafetyResult(allowed=False, reason='unavailable'), never the base fail-open."""
    mods = _mod_setup(monkeypatch, consent)

    async def _boom(**kw):
        raise LookupError("classifier step broke " + FACTORY_SENTINEL)

    monkeypatch.setattr(_router(), "guarded_anthropic_create", _boom)
    res = _run(
        css.get_content_safety_service().moderate_output("a synthetic shopping text")
    )
    assert (res.allowed, res.reason) == (False, "unavailable"), res
    assert mods == []


# ---------------------------------------------------------------------------
# G12 (F1-8; correctness m2; mutant M20): a HALF_OPEN probe answered by a
# terminal 4xx records success once and no failure (the W1-3b rule)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("i", range(len(TERMINAL)))
def test_g12_half_open_probe_terminal_4xx_records_success_once(
    monkeypatch, consent, redis_fake, i
):
    """F1-8: TEXT ON + consent 3, circuit:anthropic OPEN past its cooldown (the
    half-open probe admitted), the call ends in a terminal 4xx -> a terminal
    AnthropicDispatchError, record_success('anthropic') exactly once and no
    record_failure."""
    _knobs(monkeypatch)
    consent.set(3)
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    redis_fake.data[abs_._circuit_key("anthropic")] = _open_state(
        abs_.CB_RECOVERY_TIMEOUT + 5
    )
    probes, succ, fails = [], [], []
    real_icc, real_succ, real_fail = (
        abs_.is_circuit_closed,
        abs_.record_success,
        abs_.record_failure,
    )
    monkeypatch.setattr(
        abs_, "is_circuit_closed", lambda p: (probes.append(p), real_icc(p))[1]
    )
    monkeypatch.setattr(
        abs_, "record_success", lambda p: (succ.append(p), real_succ(p))[1]
    )
    monkeypatch.setattr(
        abs_, "record_failure", lambda p: (fails.append(p), real_fail(p))[1]
    )
    ANTH.script = [TERMINAL[i]()]
    st, exc = _run(
        _capture(_route("parse", DispatchRec(), **_base_dispatch_kwargs("parse")))
    )
    disp = _sym("AnthropicDispatchError")
    assert st == "raised" and isinstance(exc, disp), (st, exc)
    assert exc.transient is False and isinstance(exc.status, int), exc
    assert probes == ["anthropic"], probes
    assert succ == ["anthropic"], succ
    assert fails == [], fails


# ---------------------------------------------------------------------------
# G13 (F1-14; engineering m2; mutant MPC): no direct guarded_llm_create call in
# app/ outside the router and its definition module
# ---------------------------------------------------------------------------
APP_DIR = pathlib.Path(__file__).resolve().parents[1] / "app"
ROUTING_EXEMPT = {
    APP_DIR / "services" / "llm_router.py",
    APP_DIR / "services" / "api_budget_service.py",
}


def _dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _direct_guarded_calls(tree):
    return [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and _dotted_name(n.func).split(".")[-1] == "guarded_llm_create"
    ]


def _routed_calls(tree):
    return [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and _dotted_name(n.func).split(".")[-1] == "route"
        and "llm_router" in _dotted_name(n.func)
        and len(n.args) >= 2
        and _dotted_name(n.args[1]).split(".")[-1] == "guarded_llm_create"
    ]


# RB6-5 (m-RV5; mutant RV15): the EXACT set of the 16 routed site keys (names, not
# a floor): an aliased un-route, a new site or a renamed key changes the set.
G13_SITE_KEYS = frozenset(
    {
        "classify",
        "parse",
        "specs",
        "price",
        "price_training",
        "reviews",
        "verdict",
        "verdict_fallback",
        "image_tier3",
        "vision_v1",
        "vision_v2",
        "specs_targeted",
        "specs_synthesized",
        "disambiguate",
        "url_extract",
        "critique",
    }
)


def _routed_site_keys(tree):
    """The literal site key of every routed call (the _routed_calls predicate); a
    non-literal key reads '<non-literal>', which no pinned name equals."""
    keys = []
    for n in ast.walk(tree):
        if (
            isinstance(n, ast.Call)
            and _dotted_name(n.func).split(".")[-1] == "route"
            and "llm_router" in _dotted_name(n.func)
            and len(n.args) >= 2
            and _dotted_name(n.args[1]).split(".")[-1] == "guarded_llm_create"
        ):
            first = n.args[0]
            literal = isinstance(first, ast.Constant) and isinstance(first.value, str)
            keys.append(first.value if literal else "<non-literal>")
    return keys


def test_g13_every_llm_site_dispatches_through_the_router():
    """F1-14: an AST census over app/ finds NO call to guarded_llm_create( outside
    app/services/llm_router.py and app/services/api_budget_service.py; RB6-5
    (m-RV5, mutant RV15): the _llm_router.route(<site>, <x>.guarded_llm_create, ...)
    calls carry EXACTLY the 16 pinned site keys (a frozenset of names, not a floor
    >= 16), each routed once; self-checks: a direct call, a routed call and its
    site key are each recognised."""
    direct_src = (
        "async def f(c):\n    await _llm_breaker.guarded_llm_create(c, model='m')\n"
    )
    routed_src = (
        "async def f(c):\n"
        "    await _llm_router.route('x', _llm_breaker.guarded_llm_create, c)\n"
    )
    assert _direct_guarded_calls(ast.parse(direct_src)), "harness: direct call missed"
    assert _routed_calls(ast.parse(routed_src)), "harness: routed call missed"
    assert _routed_site_keys(ast.parse(routed_src)) == ["x"], "harness: key missed"
    assert (
        _direct_guarded_calls(ast.parse(routed_src)) == []
    ), "harness: routed != direct"
    direct, keys = [], []
    for path in sorted(APP_DIR.rglob("*.py")):
        if path in ROUTING_EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(APP_DIR.parent).as_posix()
        direct += ["%s:%d" % (rel, ln) for ln in _direct_guarded_calls(tree)]
        keys += _routed_site_keys(tree)
    assert direct == [], "guarded_llm_create called outside the router: %s" % direct
    assert len(G13_SITE_KEYS) == 16
    assert frozenset(keys) == G13_SITE_KEYS, "routed site keys: missing %s, new %s" % (
        sorted(G13_SITE_KEYS - set(keys)),
        sorted(set(keys) - G13_SITE_KEYS),
    )
    assert len(keys) == len(G13_SITE_KEYS), "a site key routed twice: %s" % sorted(keys)


# ===========================================================================
# REBASE ROUND (RULINGS_REBASE_S81_06 RB6-2, RB6-3, RB6-4; RB6-5 is G13 above):
# the pins the fix-1 re-verifier named (m-RV1, m-RV2, m-RV4)
# ===========================================================================
MOD_STEP_LINE = "[ROUTER] moderation step failed class=%s -- failing closed"


# ---------------------------------------------------------------------------
# G14 (RB6-2; m-RV1; mutant RV7): the moderation catch-all logs the TYPE only
# ---------------------------------------------------------------------------
def test_g14_moderation_catch_all_logs_the_type_only(monkeypatch, consent, caplog):
    """RB6-2: MODERATION ON + consent 3, a failure of any other class inside the
    classifier step -> SafetyResult(allowed=False, reason='unavailable') and ONE
    WARNING carrying type(exc).__name__ only; the exception text reaches no log
    record (message, args or traceback)."""
    caplog.set_level(logging.DEBUG)
    mods = _mod_setup(monkeypatch, consent)
    text = "classifier step broke " + FACTORY_SENTINEL

    async def _boom(**kw):
        raise LookupError(text)

    monkeypatch.setattr(_router(), "guarded_anthropic_create", _boom)
    res = _run(
        css.get_content_safety_service().moderate_output("a synthetic shopping text")
    )
    assert (res.allowed, res.reason) == (False, "unavailable"), res
    assert mods == []
    lines = [
        r
        for r in caplog.records
        if r.getMessage().startswith("[ROUTER] moderation step failed")
    ]
    got = [r.getMessage() for r in lines]
    assert got == [MOD_STEP_LINE % "LookupError"], got
    assert [r.levelno for r in lines] == [logging.WARNING]
    assert [r.exc_info for r in lines] == [None]
    assert _no_sentinel_logged(caplog, FACTORY_SENTINEL) == []
    assert FACTORY_SENTINEL not in caplog.text


# ---------------------------------------------------------------------------
# G15 (RB6-3; m-RV2; mutant RV9): a CLOSED breaker (no probe) answered by a
# terminal 4xx records NO success and no failure, for every terminal class
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seeded", [False, True], ids=["closed-empty", "closed-fails2"])
@pytest.mark.parametrize("i", range(len(TERMINAL)))
def test_g15_closed_breaker_terminal_4xx_records_no_success(
    monkeypatch, consent, redis_fake, i, seeded
):
    """RB6-3: TEXT ON + consent 3, circuit:anthropic CLOSED (no state, or a CLOSED
    state carrying 2 failures: no half-open probe either way), the call ends in a
    terminal 4xx -> a terminal AnthropicDispatchError, record_success ZERO times
    (succ == []), no record_failure and no breaker write: a terminal 4xx never
    resets a CLOSED failure streak."""
    key = abs_._circuit_key("anthropic")
    if seeded:
        redis_fake.data[key] = json.dumps(
            {"state": abs_.CB_CLOSED, "failure_count": 2, "tripped_at": 0}
        )
    st, exc, fails, succ = _classify_case(monkeypatch, consent, TERMINAL[i], redis_fake)
    disp = _sym("AnthropicDispatchError")
    assert st == "raised" and isinstance(exc, disp), (st, exc)
    assert exc.transient is False, exc
    assert succ == [], succ
    assert fails == [], fails
    assert [k for k in redis_fake.sets if k == key] == []
    if seeded:
        assert json.loads(redis_fake.data[key])["failure_count"] == 2


# ---------------------------------------------------------------------------
# G16 (RB6-4; m-RV4; the ONE code hunk of the rebase round): a parseable answer
# whose `flagged` is not a bool is MALFORMED and fails CLOSED
# ---------------------------------------------------------------------------
_MISSING = object()


def _mod_answer(flagged):
    body = {"category": "violence", "uncertain": False}
    if flagged is not _MISSING:
        body["flagged"] = flagged
    return json.dumps(body)


@pytest.mark.parametrize(
    "flagged, want",
    [
        ("true", (False, "malformed")),
        ("false", (False, "malformed")),
        (1, (False, "malformed")),
        (None, (False, "malformed")),
        (_MISSING, (False, "malformed")),
        (True, (False, "violence")),
        (False, (True, None)),
    ],
    ids=[
        "str-true",
        "str-false",
        "int-1",
        "null",
        "missing",
        "bool-true",
        "bool-false",
    ],
)
def test_g16_moderation_non_bool_flagged_is_malformed(
    monkeypatch, consent, flagged, want
):
    """RB6-4: MODERATION ON + consent 3, a parseable classifier answer whose
    `flagged` is not a bool (the strings 'true' / 'false', an int, null, absent) ->
    SafetyResult(allowed=False, reason='malformed'); a bool `flagged` keeps its R29
    outcome (True -> blocked with the category, False -> allowed);
    moderations.create is never called."""
    mods = _mod_setup(monkeypatch, consent)
    ANTH.default = c_msg(_mod_answer(flagged))
    res = _run(
        css.get_content_safety_service().moderate_output("a product description text")
    )
    assert ANTH.calls, "the Claude classifier was never called"
    assert (res.allowed, res.reason) == want, res
    assert mods == []

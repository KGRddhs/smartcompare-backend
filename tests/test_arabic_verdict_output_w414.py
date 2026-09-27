"""W4-14 Part B -- a `lang` on the three text compare routes, threaded inertly to
`generate_comparison`, and ONE behaviour fork behind ENABLE_ARABIC_VERDICT_OUTPUT
(default OFF, read per call): the `_ARABIC_OUTPUT_DIRECTIVE` appended LAST to the
verdict system message when output_lang == "ar".

Row labels (docstrings): RED = fails at the unit base 3985eaac because the named
behaviour is absent; PIN = green at the base and must stay green.

Every symbol the unit adds is resolved INSIDE the test body (getattr + assert), so an
absent symbol reddens the individual node with an assertion naming it, never the
module's collection. The capture harness extends
tests/test_verdict_prompt_unification.py::_capture_prod_system_msg (stubbed
`get_client` + stubbed model_router) to the user message and the call kwargs; no
node reaches the network (route tests use a mocked service and a stubbed log_search).
Comparisons are relative: the "base" of a cell is the same cell captured in the same
process with the Arabic flag OFF and no output_lang kwarg, so the matrix holds in both
ENABLE_VERDICT_PROMPT_TRUTH states (W4-11).
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parent.parent
COPY_POLICY = REPO / "SmartCompareApp" / "src" / "i18n" / ".copy-policy.json"

_FLAG = "ENABLE_ARABIC_VERDICT_OUTPUT"
_RESET_FLAGS = (
    _FLAG,
    "ENABLE_GPT_WINNER",
    "ENABLE_REVIEW_SOURCE_CONSULT",
    "ENABLE_YOUTUBE_SOURCE",
    "ENABLE_SELF_CRITIQUE",
    "ENABLE_FULL_STREAM_DEADLINE",
)
_ABSENT = object()

_PREFS = {"priorities": ["longevity", "price"], "budget": "mid", "lifestyle": [],
          "brand_attitude": "best_of_both"}
_DEMO = {"country": "Bahrain", "language": "Arabic",
         "cohort_match": {"match_quality": "exact", "confidence": "high",
                          "cohort_key": "k", "n": 40}}

# 18 cells (spec 9.3) + 6 demographics cells (rulings C10: the Arabic users' path).
CELLS = [
    (cat, pname, q, None)
    for cat in ("fragrances", "electronics", "other")
    for pname in ("noprefs", "prefs")
    for q in ("normal", "weak", "weird")
] + [
    (cat, pname, "normal", "demo")
    for cat in ("fragrances", "electronics", "other")
    for pname in ("noprefs", "prefs")
]
CELL_IDS = [f"{c}-{p}-{q}" + ("-demo" if d else "") for c, p, q, d in CELLS]


@pytest.fixture(autouse=True)
def _w414_env(monkeypatch):
    """Flag/env reset (the unit's own flag + every flag that changes the verdict
    prompt), the slowapi limiter disabled for this file's route calls, and the
    cohort service stubbed so a demographics cell never reaches Supabase."""
    for name in _RESET_FLAGS:
        monkeypatch.delenv(name, raising=False)
    from app.middleware.rate_limiter import limiter as _limiter
    monkeypatch.setattr(_limiter, "enabled", False)

    class _CohortSvc:
        def get_cohort_modal_for_key(self, key):
            return {"top_deciding_factor": "Quality"}

    import app.services.cohort_service as cs
    monkeypatch.setattr(cs, "get_cohort_service", lambda: _CohortSvc())
    yield


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Belt-and-braces zero-network guard on top of the conftest netguard: any
    non-loopback resolution/connection or a curl_cffi GET fails the node."""
    import socket

    attempts = []
    local = ("127.0.0.1", "::1", "localhost", b"127.0.0.1", b"::1", b"localhost", "", None)
    real_gai = socket.getaddrinfo
    real_connect = socket.socket.connect

    def _gai(host, *a, **k):
        if host not in local:
            attempts.append(("getaddrinfo", host))
            raise OSError(f"W4-14 tests: network blocked (getaddrinfo {host!r})")
        return real_gai(host, *a, **k)

    def _connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in local:
            attempts.append(("connect", host))
            raise OSError(f"W4-14 tests: network blocked (connect {host!r})")
        return real_connect(self, address)

    def _curl_get(*a, **k):
        attempts.append(("curl_cffi.requests.get", a[:1]))
        raise OSError("W4-14 tests: network blocked (curl_cffi.requests.get)")

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    monkeypatch.setattr(socket.socket, "connect", _connect)
    try:
        import curl_cffi.requests as _cr
        monkeypatch.setattr(_cr, "get", _curl_get)
    except Exception:  # pragma: no cover - curl_cffi is pinned in CI
        pass
    yield
    assert attempts == [], f"a W4-14 test attempted network access: {attempts}"


# --------------------------------------------------------------------- helpers


def _es():
    from app.services import extraction_service as es
    return es


def _require(obj, name, what):
    got = getattr(obj, name, None)
    assert got is not None, f"W4-14 absent: {what} ({name}) does not exist"
    return got


def _require_param(fn, name, what):
    params = inspect.signature(fn).parameters
    assert name in params, (
        f"W4-14 absent: {what} has no `{name}` parameter (params: {list(params)})"
    )


def _directive():
    d = _require(_es(), "_ARABIC_OUTPUT_DIRECTIVE", "the Arabic output directive constant")
    assert isinstance(d, str) and d.strip(), "the Arabic output directive is empty"
    return d


def _capture(category, prefs, quality, *, demographics=None, output_lang=_ABSENT,
             scores="A=70 B=60", with_result=False):
    """Run the REAL generate_comparison with a stubbed client/router; return the
    system message, user message and the call kwargs as {name: repr(value)} (the
    VALUES, not only the names: a flag-OFF fork on e.g. the max_tokens value must
    redden the identity pins 30/31/32 - adversary mutant N16)."""
    es = _es()
    captured = {}

    async def fake_create(*args, **kwargs):
        for m in kwargs.get("messages") or []:
            captured[m["role"]] = m["content"]
        captured["kwargs"] = {k: repr(v) for k, v in sorted(kwargs.items()) if k != "messages"}
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = (
            '{"winner_index": 0, "winner_reason": "x", "product_0_pros": [], '
            '"product_1_pros": []}'
        )
        resp.choices = [choice]
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        return resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=fake_create)
    fake_router = MagicMock()
    fake_router.get_model = AsyncMock(return_value="gpt-4o-mini")
    fake_router.record_usage = AsyncMock(return_value=None)
    p1 = {"brand": "Lattafa", "name": "Yara", "category": category, "category_used": category,
          "price": {"amount": 12.5, "currency": "BHD", "source_method": "local_bhd"}}
    p2 = {"brand": "Lattafa", "name": "Fakhar", "category": category, "category_used": category,
          "price": {"amount": 14.0, "currency": "BHD", "source_method": "local_bhd"}}
    extra = {} if output_lang is _ABSENT else {"output_lang": output_lang}
    loop = asyncio.new_event_loop()
    try:
        with patch.object(es, "get_client", return_value=fake_client), \
             patch("app.services.model_router_service.model_router", fake_router):
            result = loop.run_until_complete(es.generate_comparison(
                p1, p2, "bahrain", "value", user_preferences=prefs, scores_summary=scores,
                category=category, demographics_profile=demographics,
                comparison_quality=quality, **extra))
    finally:
        loop.close()
    assert "system" in captured, "harness: the verdict call was never made"
    # Positive control: the value-level capture really carries the verdict call's
    # token budget, so an output_lang-dependent max_tokens is visible to 30/31/32.
    assert "max_tokens" in captured["kwargs"] or "max_completion_tokens" in captured["kwargs"], (
        f"harness: no token-limit kwarg captured ({sorted(captured['kwargs'])})"
    )
    out = {"system": captured["system"], "user": captured["user"], "kwargs": captured["kwargs"]}
    if with_result:
        out["result"] = result  # (comparison, usage) - the RETURN, for test_40
    return out


def _cell_args(cell, monkeypatch):
    cat, pname, q, demo = cell
    if demo:
        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
    return cat, (_PREFS if pname == "prefs" else None), q, (copy.deepcopy(_DEMO) if demo else None)


def _base(cell, monkeypatch):
    """The HEAD capture of a cell: Arabic flag OFF, no output_lang kwarg."""
    monkeypatch.delenv(_FLAG, raising=False)
    cat, prefs, q, demo = _cell_args(cell, monkeypatch)
    return _capture(cat, prefs, q, demographics=demo)


# ------------------------------------------------------------ B1 reader + normaliser


@pytest.mark.parametrize("raw,expected", [
    ("ar", "ar"), ("AR", "ar"), (" ar-BH ", "ar"), ("ar_SA", "ar"),
    ("en", "en"), ("en-US", "en"),
    ("fr", None), ("", None), (None, None), (5, None),
    ("arabic", None), ("ARABIC", None), ("ara_SA", None), ("eng", None), ("english-US", None),
])
def test_25_red_normalize_output_lang(raw, expected):
    """RED (absent normaliser). normalize_output_lang: non-str/empty -> None; strip,
    lower, primary subtag before '-'/'_'; 'ar' or 'en', anything else None. The
    primary subtag is the WHOLE part before the separator, never a 2-char prefix:
    'arabic' / 'ara_SA' / 'eng' / 'english-US' are not codes (kills B5, `s[:2]`)."""
    fn = _require(_es(), "normalize_output_lang", "the output-language normaliser")
    assert fn(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("1", True), ("true", True), ("yes", True), ("on", True), (" TRUE ", True),
    ("", False), ("0", False), ("false", False), ("off", False), (None, False),
    # Fable pin (adversary r2 X4): an UNRECOGNISED value reads as OFF - the reader is
    # an allowlist of the house truthy set, never "anything that is not falsy".
    ("2", False), ("enabled", False), ("y", False), ("t", False), ("tru", False),
    ("TRUE", True), ("On", True), (" yes ", True),
])
def test_38_red_flag_reader_values_and_per_call(monkeypatch, raw, expected):
    """RED (absent reader). arabic_verdict_output_enabled() follows the house
    truthy set and is read PER CALL (a flip after the first read is honoured -
    kills a reader memoised at import, M11, and a reader forced True, M10)."""
    fn = _require(_es(), "arabic_verdict_output_enabled", "the flag reader")
    if raw is None:
        monkeypatch.delenv(_FLAG, raising=False)
    else:
        monkeypatch.setenv(_FLAG, raw)
    assert fn() is expected
    monkeypatch.setenv(_FLAG, "false" if expected else "true")
    assert fn() is (not expected), "the flag reader is not read per call"


# ------------------------------------------------------------ B2 route field (inert)


def test_26_red_text_compare_request_keeps_lang_and_bounds_it():
    """RED. TextCompareRequest gains `lang: Optional[str] = Field(None, max_length=8)`:
    it round-trips in model_dump(); 9 characters is a ValidationError. HEAD: the
    pydantic default `extra=ignore` drops it silently."""
    from pydantic import ValidationError
    from app.api.text_routes import TextCompareRequest

    m = TextCompareRequest(product_a="a", product_b="b", lang="ar")
    assert m.model_dump().get("lang") == "ar", (
        f"TextCompareRequest has no lang field (dump keys: {sorted(m.model_dump())})"
    )
    with pytest.raises(ValidationError):
        TextCompareRequest(product_a="a", product_b="b", lang="x" * 9)


def _mock_service(monkeypatch):
    svc = MagicMock()
    svc.compare_from_text = AsyncMock(return_value={
        "success": True, "products": [], "comparison": {},
        "category_used": "fragrances", "category_switched": False,
    })

    async def _empty_stream():
        if False:  # pragma: no cover - an async generator that yields nothing
            yield None

    svc.compare_from_text_streaming = MagicMock(side_effect=lambda *a, **k: _empty_stream())
    monkeypatch.setattr("app.api.text_routes.get_comparison_service", lambda: svc)
    monkeypatch.setattr("app.api.text_routes.log_search", AsyncMock(return_value=None))
    return svc


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _call(handler, lang=_ABSENT):
    client = _client()
    if handler == "post":
        body = {"product_a": "Lattafa Yara", "product_b": "Lattafa Fakhar"}
        if lang is not _ABSENT:
            body["lang"] = lang
        return client.post("/api/v1/text/compare", json=body)
    params = {"product_a": "Lattafa Yara", "product_b": "Lattafa Fakhar"}
    if lang is not _ABSENT:
        params["lang"] = lang
    path = "/api/v1/text/compare" if handler == "get" else "/api/v1/text/compare/stream"
    return client.get(path, params=params)


def _service_kwargs(svc, handler):
    mock = svc.compare_from_text_streaming if handler == "stream" else svc.compare_from_text
    assert mock.call_args is not None, f"{handler}: the service was never called"
    return mock.call_args.kwargs


def test_26b_red_http_post_overlong_lang_is_422(monkeypatch):
    """RED. POST /text/compare with lang='x'*9 is a 422 before any work (the M13-25
    bounding idiom). HEAD: the field is ignored and the compare runs."""
    svc = _mock_service(monkeypatch)
    resp = _call("post", "x" * 9)
    assert resp.status_code == 422, f"over-long lang not rejected: {resp.status_code}"
    svc.compare_from_text.assert_not_awaited()


@pytest.mark.parametrize("path", ["/api/v1/text/compare", "/api/v1/text/compare/stream"])
def test_27_red_get_routes_declare_a_bounded_lang_query_param(monkeypatch, path):
    """RED. GET /text/compare and /text/compare/stream declare `lang` as a query
    param (route dependant) bounded at 8 characters (lang='x'*9 -> 422). HEAD: the
    param list is nocache, product_a, product_b, pros_cons, q, region, reviews,
    selected_category, specs."""
    from app.api import text_routes as tr

    routes = [r for r in tr.router.routes
              if getattr(r, "path", "").endswith(path.replace("/api/v1/text", ""))
              and "GET" in (getattr(r, "methods", None) or set())]
    assert routes, f"harness: no GET route for {path}"
    names = sorted(p.name for p in routes[0].dependant.query_params)
    assert "lang" in names, f"GET {path} declares no lang query param: {names}"
    svc = _mock_service(monkeypatch)
    resp = _call("get" if path.endswith("/compare") else "stream", "x" * 9)
    assert resp.status_code == 422, f"over-long lang not rejected on {path}: {resp.status_code}"
    svc.compare_from_text.assert_not_awaited()


@pytest.mark.parametrize("handler", ["post", "get", "stream"])
@pytest.mark.parametrize("lang", ["ar", "AR", " ar-BH "])
def test_28_red_handlers_forward_normalised_output_lang(monkeypatch, handler, lang):
    """RED. Each of the 3 handlers normalises `lang` and passes output_lang='ar' to
    the service (rulings C4: 'AR' and ' ar-BH ' too - a route forwarding the raw
    value is killed). HEAD: no output_lang kwarg is ever passed."""
    svc = _mock_service(monkeypatch)
    resp = _call(handler, lang)
    assert resp.status_code == 200, resp.status_code
    kw = _service_kwargs(svc, handler)
    assert kw.get("output_lang") == "ar", (
        f"{handler} lang={lang!r}: output_lang not forwarded (kwargs: {sorted(kw)})"
    )


@pytest.mark.parametrize("handler", ["post", "get", "stream"])
@pytest.mark.parametrize("lang", [_ABSENT, "fr", ""], ids=["absent", "fr", "empty"])
def test_28b_pin_no_output_lang_kwarg_when_lang_absent_or_unrecognised(monkeypatch, handler, lang):
    """PIN (green at HEAD). A request without `lang` (every shipped phone) or with an
    unrecognised one produces a service call carrying NO output_lang kwarg - the
    conditional-kwargs form (kills M14: output_lang=None passed unconditionally)."""
    svc = _mock_service(monkeypatch)
    resp = _call(handler, lang)
    assert resp.status_code == 200, resp.status_code
    kw = _service_kwargs(svc, handler)
    assert "output_lang" not in kw, f"{handler}: output_lang kwarg sent for lang={lang!r}"


@pytest.mark.parametrize("handler", ["post", "get", "stream"])
def test_35_pin_no_lang_with_flag_on_is_the_phone_contract(monkeypatch, handler):
    """PIN (green at HEAD). The 561d2cba phone contract with the flag ON: no lang ->
    the service is called WITHOUT an output_lang kwarg, and the verdict prompt for
    such a call equals the flag-OFF base (no directive can reach it)."""
    monkeypatch.setenv(_FLAG, "true")
    svc = _mock_service(monkeypatch)
    resp = _call(handler)
    assert resp.status_code == 200, resp.status_code
    assert "output_lang" not in _service_kwargs(svc, handler)
    on = _capture("fragrances", None, "normal")
    monkeypatch.delenv(_FLAG, raising=False)
    off = _capture("fragrances", None, "normal")
    assert on == off


# ------------------------------------------------------------ B3 threading (inert)


class _Stop(RuntimeError):
    pass


def _sync_harness(monkeypatch):
    """Drive compare_from_text fully mocked to the verdict stage: explicit pair,
    mocked _fetch_product_data, fairness no-op, the real scoring service (a private
    instance). generate_comparison is replaced by a recorder that returns a verdict;
    _apply_self_critique by a recorder of regen_args that stops the run."""
    import app.services.structured_comparison_service as scs
    from app.services import scoring_service as _ss

    service = scs.get_comparison_service()
    monkeypatch.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache=False,
                          partial_slot=0, **kw):
        name = f"{product.get('brand') or ''} {product.get('name') or ''}".strip() or "X Y"
        return {
            "brand": product.get("brand") or "X", "name": product.get("name") or "Y",
            "full_name": name, "category": "electronics",
            "specs": {"battery_mah": 4000, "storage_gb": 128},
            "price": {"amount": 120.0, "currency": "BHD", "estimated": False,
                      "source_method": "local_bhd", "retailer": "Best Buy",
                      "url": "https://www.bestbuy.com/site/x/1.p", "title": name,
                      "in_stock": True},
            "best_price": 120.0, "retailer": "Best Buy",
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }

    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)
    monkeypatch.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    return service


def _install_recorders(monkeypatch, service):
    import app.services.structured_comparison_service as scs

    holder = {"gen": [], "regen_args": []}

    async def _gen(*a, **k):
        holder["gen"].append(dict(k))
        return ({"winner_index": 0, "winner_declaration": "A", "winner_reason": "x"},
                {"prompt_tokens": 1, "completion_tokens": 1})

    async def _critique(*a, **k):
        holder["regen_args"].append(dict(k.get("regen_args") or {}))
        raise _Stop("W4-14: regen_args recorded")

    monkeypatch.setattr(scs, "generate_comparison", _gen)
    monkeypatch.setattr(service, "_apply_self_critique", _critique)
    return holder


def _run_sync(monkeypatch, **extra):
    service = _sync_harness(monkeypatch)
    holder = _install_recorders(monkeypatch, service)
    try:
        asyncio.run(service.compare_from_text(
            query="Samsung Galaxy S24 vs Apple iPhone 15", region="bahrain",
            explicit_pair=("Samsung Galaxy S24", "Apple iPhone 15"),
            selected_category="electronics", user_id=None, nocache=True, **extra))
    except _Stop:
        pass
    return holder


def _mock_stream_to_verdict(monkeypatch, service):
    """tests/test_m13_04_full_stream_deadline.py::_mock_to_verdict, verbatim shape."""
    import app.services.structured_comparison_service as scs

    monkeypatch.setattr(scs, "parse_product_query", AsyncMock(return_value=(
        {"products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
         "comparison_type": "value"}, {})))

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache,
                          partial_slot=0, **kw):
        return {
            "brand": product.get("brand", "X"), "name": product.get("name", "Y"),
            "specs": {"k": "v"},
            "price": {"amount": 10.0, "currency": "BHD", "estimated": False},
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }
    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)

    scoring = MagicMock()
    scoring.compute_scores.return_value = {
        "scores": {"product_0": {"breakdown": {"value_score": 60}},
                   "product_1": {"breakdown": {"value_score": 50}}},
        "winner_index": 0, "win_margin": 5, "dimension_winners": {}, "price_tiers": {},
    }
    scoring.build_scores_summary.return_value = ""
    scoring.compute_confidence.return_value = 0.5
    scoring.compute_value_badge.return_value = ""
    scoring.compute_tradeoff_pairs.return_value = []
    monkeypatch.setattr(scs, "get_scoring_service", lambda: scoring)
    monkeypatch.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)


def _run_stream(monkeypatch, **extra):
    import app.services.structured_comparison_service as scs

    service = scs.get_comparison_service()
    _mock_stream_to_verdict(monkeypatch, service)
    holder = _install_recorders(monkeypatch, service)

    async def _drain():
        gen = service.compare_from_text_streaming(query="A vs B", **extra)
        try:
            async for _ev in gen:
                pass
        except _Stop:
            pass

    asyncio.run(asyncio.wait_for(_drain(), timeout=30))
    return holder


def test_29_red_compare_from_text_threads_output_lang(monkeypatch):
    """RED (sync). compare_from_text(output_lang='ar') hands output_lang='ar' to
    generate_comparison AND puts it in the self-critique regen_args (kills M16 on
    the sync builder). HEAD: the service has no output_lang parameter."""
    import app.services.structured_comparison_service as scs

    _require_param(scs.StructuredComparisonService.compare_from_text, "output_lang",
                   "compare_from_text")
    holder = _run_sync(monkeypatch, output_lang="ar")
    assert holder["gen"], "generate_comparison was never reached"
    assert holder["gen"][0].get("output_lang") == "ar", sorted(holder["gen"][0])
    assert holder["regen_args"], "_apply_self_critique was never reached"
    assert holder["regen_args"][0].get("output_lang") == "ar", sorted(holder["regen_args"][0])


def test_29b_red_compare_from_text_streaming_threads_output_lang(monkeypatch):
    """RED (SSE). compare_from_text_streaming(output_lang='ar') hands it to
    generate_comparison and to the regen_args (kills M13 - the streaming threading
    dropped - while the sync node stays green, and M16 on the stream builder).
    HEAD: no output_lang parameter."""
    import app.services.structured_comparison_service as scs

    _require_param(scs.StructuredComparisonService.compare_from_text_streaming,
                   "output_lang", "compare_from_text_streaming")
    holder = _run_stream(monkeypatch, output_lang="ar")
    assert holder["gen"], "generate_comparison was never reached on the stream path"
    assert holder["gen"][0].get("output_lang") == "ar", sorted(holder["gen"][0])
    assert holder["regen_args"], "_apply_self_critique was never reached (stream)"
    assert holder["regen_args"][0].get("output_lang") == "ar", sorted(holder["regen_args"][0])


@pytest.mark.parametrize("path", ["sync", "stream"])
def test_29c_pin_no_output_lang_is_kwarg_identical(monkeypatch, path):
    """PIN (green at HEAD). Without output_lang the verdict call and the regen_args
    carry NO output_lang key - the no-lang path is kwarg-identical to HEAD (the
    conditional-kwargs form of B3)."""
    holder = _run_sync(monkeypatch) if path == "sync" else _run_stream(monkeypatch)
    assert holder["gen"], "generate_comparison was never reached"
    assert "output_lang" not in holder["gen"][0], sorted(holder["gen"][0])
    assert holder["regen_args"], "_apply_self_critique was never reached"
    assert "output_lang" not in holder["regen_args"][0], sorted(holder["regen_args"][0])


# ------------------------------------------------------------ B4 the one fork


def test_36_red_directive_constant_is_pinned_non_empty_with_its_fragments():
    """RED (absent constant; M18 = the directive emptied/truncated reddens here).
    The directive names every prose field of the verdict JSON incl.
    independent_winner_basis (R4.4), the keep-as-given list, Western digits, and the
    copy-policy Arabic banned + scary vocabulary as forbidden words (R4.3)."""
    d = _directive()
    assert d.startswith("\n\n## Output language\n"), ascii(d[:40])
    for frag in ("winner_reason", "key_tradeoff", "value_context", "best_for",
                 "product_0_pros", "product_0_cons", "product_1_pros", "product_1_cons",
                 "specs_comparison", "personalized_insights", "independent_winner_basis",
                 "Modern Standard Arabic", "JSON key", "winner_declaration", "focus_area",
                 "Western digits"):
        assert frag in d, f"directive lacks {frag!r}"
    policy = json.loads(COPY_POLICY.read_text(encoding="utf-8"))
    words = [e["pattern"] for e in policy["banned_ar"]] + list(policy["scary_vocab_ar"])
    assert len(words) == 9, len(words)
    missing = [ascii(w) for w in words if w not in d]
    assert not missing, f"directive does not forbid the copy-policy Arabic terms: {missing}"
    # The EXACT text ruling R3 accepted (fragments alone pinned the vocabulary, not
    # what the directive tells the model to do: the adversary's N3 keep-list ->
    # "Translate into Arabic as well", N4 "Never write" -> "Prefer", N5 Western ->
    # Arabic-Indic digits all survived). Rebuilt from the copy-policy file (the
    # forbidden words in file order: banned_ar, then scary_vocab_ar, '; '-joined),
    # so it stays the cross-language fence R3 asks for, plus R3's recorded identity.
    expected = (
        "\n\n## Output language\n"
        "The reader of this verdict reads Arabic. Write EVERY human-readable string value "
        "in the JSON in Modern Standard Arabic: winner_reason, key_tradeoff, both "
        "value_context sentences, both best_for sentences, every item of product_0_pros, "
        "product_0_cons, product_1_pros and product_1_cons, every item of "
        "specs_comparison, every personalized_insights[].insight, and "
        "independent_winner_basis when it is requested.\n"
        "Keep EXACTLY as given, never translated or transliterated: every JSON key, the "
        "winner_declaration value (the product name), product and brand names, model "
        "numbers, units, currency codes, and personalized_insights[].focus_area.\n"
        "Write every number with Western digits (0-9).\n"
        "Never write these Arabic words or phrases: " + "; ".join(words) + ".\n"
        "Every other rule above still applies unchanged."
    )
    assert d == expected, "the directive text differs from the R3-accepted text"
    assert len(d) == 874, len(d)
    assert hashlib.sha256(d.encode("utf-8")).hexdigest()[:16] == "cef4fdeb0fd89ccb"


@pytest.mark.parametrize("cell", CELLS, ids=CELL_IDS)
def test_30_red_flag_on_ar_appends_the_directive_last(monkeypatch, cell):
    """RED. Flag ON + output_lang='ar': system == base_system + DIRECTIVE exactly
    (full strings) and system != base; the user message and the call kwargs equal
    the base. Over the 18 cells + 6 demographics cells. Kills M12 (directive not
    last) and M18 (empty directive: system == base)."""
    _require_param(_es().generate_comparison, "output_lang", "generate_comparison")
    directive = _directive()
    base = _base(cell, monkeypatch)
    monkeypatch.setenv(_FLAG, "true")
    cat, prefs, q, demo = _cell_args(cell, monkeypatch)
    on = _capture(cat, prefs, q, demographics=demo, output_lang="ar")
    assert on["system"] != base["system"], "flag ON + ar left the system message unchanged"
    assert on["system"] == base["system"] + directive, (
        "the flag-ON system message is not base + directive (suffix gate)"
    )
    assert on["user"] == base["user"]
    assert on["kwargs"] == base["kwargs"]


_CANARY_FMT = "[ARABIC_VERDICT_OUTPUT] directive appended category=%s"


@pytest.mark.parametrize("flag,lang,category,expect", [
    ("true", "ar", "fragrances", True),
    ("true", "ar", "electronics", True),
    ("true", "en", "fragrances", False),
    ("true", None, "fragrances", False),
    (None, "ar", "fragrances", False),
], ids=["on-ar-fragrances", "on-ar-electronics", "on-en", "on-none", "off-ar"])
def test_39_red_canary_line_is_logged_once_exactly_when_the_directive_is_appended(
        monkeypatch, flag, lang, category, expect):
    """RED (absent parameter). The activation monitor named in the flag row: the
    line `[ARABIC_VERDICT_OUTPUT] directive appended category=<c>` is logged at INFO
    exactly once per verdict call that took the directive path, with the call's
    category, and never otherwise (kills B2, the line removed). The spy sits on the
    module's own logger, so no logging configuration or handler order can mask it."""
    es = _es()
    _require_param(es.generate_comparison, "output_lang", "generate_comparison")
    if flag is None:
        monkeypatch.delenv(_FLAG, raising=False)
    else:
        monkeypatch.setenv(_FLAG, flag)
    calls = []
    real_info = es.logger.info

    def _spy(msg, *args, **kwargs):
        calls.append((msg, args))
        return real_info(msg, *args, **kwargs)

    monkeypatch.setattr(es.logger, "info", _spy)
    got = _capture(category, None, "normal", output_lang=lang)
    canary = [(m, a) for m, a in calls
              if isinstance(m, str) and m.startswith("[ARABIC_VERDICT_OUTPUT]")]
    if expect:
        assert got["system"].endswith(_directive())
        assert len(canary) == 1, canary
        msg, args = canary[0]
        assert msg == _CANARY_FMT
        assert msg % args == f"[ARABIC_VERDICT_OUTPUT] directive appended category={category}"
    else:
        assert canary == [], canary


@pytest.mark.parametrize("cell", CELLS, ids=CELL_IDS)
@pytest.mark.parametrize("lang", [None, "en", "ar"])
def test_31_red_flag_off_output_lang_is_byte_identical(monkeypatch, cell, lang):
    """RED at HEAD only because the parameter is absent (the value it pins is the
    HEAD prompt). Flag OFF: output_lang None / 'en' / 'ar' -> system, user and call
    kwargs identical to the no-kwarg base. Kills M10 (reader forced True)."""
    _require_param(_es().generate_comparison, "output_lang", "generate_comparison")
    base = _base(cell, monkeypatch)
    cat, prefs, q, demo = _cell_args(cell, monkeypatch)
    got = _capture(cat, prefs, q, demographics=demo, output_lang=lang)
    assert got == base


@pytest.mark.parametrize("cell", CELLS, ids=CELL_IDS)
@pytest.mark.parametrize("lang", [None, "en"])
def test_32_red_flag_on_non_arabic_output_lang_is_byte_identical(monkeypatch, cell, lang):
    """RED at HEAD only because the parameter is absent. Flag ON with output_lang
    None or 'en' -> identical to the flag-OFF base (only 'ar' forks)."""
    _require_param(_es().generate_comparison, "output_lang", "generate_comparison")
    base = _base(cell, monkeypatch)
    monkeypatch.setenv(_FLAG, "true")
    cat, prefs, q, demo = _cell_args(cell, monkeypatch)
    got = _capture(cat, prefs, q, demographics=demo, output_lang=lang)
    assert got == base


def test_33_red_self_critique_regen_keeps_the_directive(monkeypatch):
    """RED. ENABLE_SELF_CRITIQUE on, flag ON, regen_args carrying output_lang='ar',
    a low critique score forces ONE regeneration through the REAL
    generate_comparison: the regen's system message also ends with the directive.
    HEAD: the regen call drops output_lang (and no directive exists)."""
    directive = _directive()
    es = _es()
    _require_param(es.generate_comparison, "output_lang", "generate_comparison")
    import app.services.structured_comparison_service as scs
    from app.services import verdict_critique_service as vcs

    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
    monkeypatch.setenv(_FLAG, "true")
    crit = {"bias_score": 9, "vagueness_score": 4, "hedging_score": 9,
            "missing_citation_score": 9, "pain_workflow_align_score": 9}
    msg = MagicMock()
    msg.content = json.dumps(crit)
    choice = MagicMock()
    choice.message = msg
    cresp = MagicMock()
    cresp.choices = [choice]
    cresp.usage = MagicMock(prompt_tokens=900, completion_tokens=50)
    critique_client = MagicMock()
    critique_client.chat.completions.create = AsyncMock(return_value=cresp)

    systems = []

    async def fake_create(*args, **kwargs):
        for m in kwargs.get("messages") or []:
            if m["role"] == "system":
                systems.append(m["content"])
        resp = MagicMock()
        ch = MagicMock()
        ch.message.content = '{"winner_index": 0, "winner_reason": "regen"}'
        resp.choices = [ch]
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        return resp

    verdict_client = MagicMock()
    verdict_client.chat.completions.create = AsyncMock(side_effect=fake_create)
    fake_router = MagicMock()
    fake_router.get_model = AsyncMock(return_value="gpt-4o-mini")
    fake_router.record_usage = AsyncMock(return_value=None)

    regen_args = dict(
        product1={"name": "A", "category_used": "fragrances"},
        product2={"name": "B", "category_used": "fragrances"},
        region="bahrain", concern="value", user_preferences=None,
        scores_summary="A leads on price.", category="fragrances",
        demographics_profile=None, comparison_quality="normal", output_lang="ar",
    )
    svc = scs.StructuredComparisonService()
    with patch.object(vcs, "get_client", return_value=critique_client), \
         patch.object(es, "get_client", return_value=verdict_client), \
         patch("app.services.model_router_service.model_router", fake_router):
        asyncio.run(svc._apply_self_critique(
            comparison={"winner_index": 0, "winner_declaration": "A", "winner_reason": "x"},
            product_names=["A", "B"], regen_args=regen_args,
        ))
    assert systems, "no regeneration ran (critique did not force one)"
    assert systems[-1].endswith(directive), "the self-critique regen lost the directive"


def test_34_pin_cohort_user_context_line_is_unchanged(monkeypatch):
    """PIN (green at HEAD). The cohort block's `Language=Arabic` stays METADATA:
    `USER CONTEXT: Country=Bahrain, Language=Arabic`, and the block never carries an
    output-language instruction - with the Arabic flag OFF and ON."""
    es = _es()
    monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
    for state in (None, "true"):
        if state:
            monkeypatch.setenv(_FLAG, state)
        block = es._build_cohort_priors_block(copy.deepcopy(_DEMO))
        ctx = [ln for ln in block.splitlines() if ln.startswith("USER CONTEXT")]
        assert ctx == ["USER CONTEXT: Country=Bahrain, Language=Arabic"], ctx
        assert "Output language" not in block
        assert "Modern Standard Arabic" not in block


_FORBIDDEN_EN = ["estimated", "reference price", "couldn't", "try again", "failed to",
                 "we couldn't", "unable to"]


@pytest.mark.parametrize("category", ["fragrances", "electronics", "other"])
def test_37_red_flag_on_system_message_passes_the_forbidden_words_audit(monkeypatch, category):
    """RED (R4.3: the forbidden-words audit extended to generate_comparison's
    flag-ON system message). With the flag ON and output_lang='ar' the system
    message carries the directive AND stays clean of the EN forbidden vocabulary of
    tests/test_verdict_prompt_forbidden_words_audit.py. HEAD: no directive."""
    directive = _directive()
    _require_param(_es().generate_comparison, "output_lang", "generate_comparison")
    monkeypatch.setenv(_FLAG, "true")
    got = _capture(category, _PREFS, "normal", output_lang="ar")
    assert got["system"].endswith(directive)
    low = got["system"].lower()
    bad = [w for w in _FORBIDDEN_EN if w in low]
    assert not bad, f"forbidden EN vocabulary in the flag-ON verdict prompt: {bad}"


# ------------------------------------------------------------ Fable pin (adversary r2 X2)


@pytest.mark.parametrize("category", ["fragrances", "electronics", "other"])
@pytest.mark.parametrize("lang", [None, "en", "ar"])
def test_40_pin_flag_off_result_is_identical_not_only_the_prompt(monkeypatch, category, lang):
    """PIN (Fable, adversary r2 X2). Flag OFF: the (comparison, usage) that
    generate_comparison RETURNS for output_lang None / 'en' / 'ar' equals the no-kwarg
    base - the identity claim covers the result, not only the prompt and the call
    kwargs (kills an output-side fork such as `if output_lang == 'ar':
    parsed[...] = ...` with no flag check). Flag ON with None / 'en' is identical too;
    flag ON + 'ar' changes the PROMPT only, never the stubbed result."""
    _require_param(_es().generate_comparison, "output_lang", "generate_comparison")
    monkeypatch.delenv(_FLAG, raising=False)
    base = _capture(category, None, "normal", with_result=True)
    got = _capture(category, None, "normal", output_lang=lang, with_result=True)
    assert got == base
    monkeypatch.setenv(_FLAG, "true")
    on = _capture(category, None, "normal", output_lang=lang, with_result=True)
    if lang == "ar":
        assert on["result"] == base["result"], "flag ON + ar changed the RESULT, not only the prompt"
    else:
        assert on == base

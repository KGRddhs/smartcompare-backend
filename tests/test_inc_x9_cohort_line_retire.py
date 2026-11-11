"""INC-X9 COHORT-LINE-RETIRE (G-INC-1, the S92-FIX incident lane) RED rows.

Spec: .qa-s80/G-INC-1_UNIT_SPEC.md section "Unit INC-X9" (X9.5), as amended by the batch
rulings: R-G1-6 (the helper `_build_cohort_summary` keeps its signature and its three call
sites; its body becomes a docstring plus `return None`; ADD one RED row per call site: the
text entry, the streaming `complete` frame and the camera entry, each with a demographics
profile that passes `was_cohort_block_active` and ENABLE_COHORT_PERSONALIZATION on) and
R-G1-11 (the two builder shapes: with a scoring result and without one).

UNFLAGGED production bug fix: N in "+N shoppers in <governorate>" was the sign-up survey
group size, not agreement on the pair. RED rows fail at base on an AssertionError only (the
block is present at base). PIN rows are green at base and stay green.

Hermetic: the compare rows drive the REAL entries and the REAL `_fetch_product_data` over a
faked pipeline (the FY25 driver, copied from tests/test_s81_s18_kb_first_serve.py, never
imported); every leaf is faked; the demographics fetch is a stub; the post-response
fire-and-forget writes are closed locally. Synthetic region words only ("Northern",
"Capital"). Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import copy
import inspect
import json
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

FLAG = "ENABLE_COHORT_PERSONALIZATION"
P0 = ("Acme", "Nimbus Noir Eau de Parfum")
P1 = ("Zephyra", "Velvet Dusk Eau de Toilette")
QUERY = "Acme Nimbus Noir Eau de Parfum vs Zephyra Velvet Dusk Eau de Toilette"
VISION = [{"brand": P0[0], "name": P0[1]}, {"brand": P1[0], "name": P1[1]}]
LLM_PARSED = {"products": [
    {"brand": P0[0], "name": P0[1], "variant": None, "category": "fragrances", "search_query": " ".join(P0)},
    {"brand": P1[0], "name": P1[1], "variant": None, "category": "fragrances", "search_query": " ".join(P1)},
], "comparison_type": "value"}
USAGE = {"prompt_tokens": 100, "completion_tokens": 50}
UID = "-".join(["facefeed", "beef", "4bad", "8cab", "deadbeefcafe"])
CLEARED_ENV = (
    "ENABLE_KB_FIRST_SERVE", "ENABLE_VERDICT_CACHE_LOG", "ENABLE_KB_INGEST", "ENABLE_FIELD_STATUS_METADATA",
    "ENABLE_LIVE_ROBOTS_REGISTRY", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH", "ENABLE_PARSE_PRESPLIT",
    "ENABLE_PARSE_BUDGET", "ENABLE_UNIFIED_SEARCH_BOUND", "ENABLE_PHASE2_RESIDUAL_GUARD",
    "PHASE2_MIN_RESIDUAL_SECONDS", "DEBUG_STAGE_TIMINGS", "ENABLE_FULL_STREAM_DEADLINE",
    "ENABLE_RESULT_STATUS_METADATA", "ENABLE_LLM_LEDGER_V2", "ENABLE_LLM_SPEND_BREAKER",
    "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION", "ENABLE_ANTHROPIC_VERDICT", "ENABLE_ANTHROPIC_CRITIC",
    "ENABLE_ANTHROPIC_MODERATION", "ENABLE_SONNET_ESCALATION", "ENABLE_OPENAI_PRE_V3",
    "ENABLE_FRAGRANCE_ONLY_GATE", "ENABLE_JSONLD_RATING", "ENABLE_IMAGE_PIPELINE_V2", "ENABLE_DATA_GUARDS_V2",
    "ENABLE_TIER_FILL_RESIDUAL_GUARD", "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT", "ENABLE_ARABIC_VERDICT_OUTPUT",
    "ENABLE_RESULT_GATE", "ENABLE_VISION_IDENTITY_V2", "ENABLE_HONEST_PARTIAL_SCORING",
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(FLAG, "true")
    yield


def _scs():
    import app.services.structured_comparison_service as scs
    return scs


def _profile(*, n=53, governorate="Northern", quality="exact", confidence="medium",
             cohort_key="25-34|Male|Northern|English"):
    return {
        "governorate": governorate,
        "country": "Bahrain",
        "language": "English",
        "cohort_match": {"cohort_key": cohort_key, "match_quality": quality, "confidence": confidence,
                         "n": n, "persona_label": "Quality-first focused buyer"},
    }


def _build(profile):
    return _scs().StructuredComparisonService._build_cohort_summary(profile)


# ---------------------------------------------------------------------------
# the faked compare (the FY25 driver of tests/test_s81_s18_kb_first_serve.py, copied)
# ---------------------------------------------------------------------------

def _install(mp, svc, state):
    scs = _scs()
    from app.services import audit_service as _audit
    from app.services import content_safety_service as _cs
    from app.services import scoring_service as _ss

    async def _parse(query):
        return json.loads(json.dumps(LLM_PARSED)), dict(USAGE)

    async def _gen(*_a, **_k):
        return ({"winner_index": 0, "winner_declaration": "Acme wins", "winner_reason": "longevity",
                 "verdict": "v", "pros": {}, "cons": {}}, {"prompt_tokens": 7, "completion_tokens": 3})

    async def _cat_llm(*_a, **_k):
        return "fragrances"

    async def _search(query, num_results=10, **kwargs):
        return {"organic": [{"title": "T " + query[:20], "link": "https://example.com/a",
                             "snippet": "eau de parfum woody longevity 8 hours"}]}

    async def _specs(*a, **_k):
        return {"concentration": "Eau de Parfum", "scent_family": "amber", "longevity": "8 hours"}

    async def _price(*a, **_k):
        return {"amount": 55.0, "currency": "BHD", "estimated": False, "source_method": "local_bhd",
                "retailer": "Live Store", "url": "https://live-store.example.com/p/1", "title": "x",
                "in_stock": True}

    async def _reviews(*a, **_k):
        return {"highlights": ["good"], "summary": "ok"}

    async def _rating(*a, **_k):
        return {"rating": 4.5, "review_count": 10, "rating_verified": True,
                "rating_source": {"name": "example", "url": "https://example.com/r"}}

    async def _empty(*a, **_k):
        return {}

    async def _image(*a, **_k):
        return None

    async def _moderate(_self, _text):
        return _cs.SafetyResult(allowed=True)

    def _reconcile(product_data, query, category, candidates_by_name=None, **kw):
        return None

    async def _blocked_log(*_a, **_k):
        return None

    async def _no_profile(*_a, **_k):
        return None

    async def _demo(*_a, **_k):
        state["demo_calls"] = state.get("demo_calls", 0) + 1
        return copy.deepcopy(state.get("demographics_profile"))

    def _ff(coro, label=None, *a, **k):
        close = getattr(coro, "close", None)
        if callable(close):
            close()

    mp.setattr(_audit, "log_content_blocked", _blocked_log)
    mp.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
    mp.setattr(scs, "parse_product_query", _parse)
    mp.setattr(scs, "generate_comparison", _gen)
    mp.setattr(scs, "reconcile_pair_fairness", _reconcile)
    mp.setattr(scs, "classify_category_llm", _cat_llm)
    mp.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    mp.setattr(scs, "search_web", _search)
    mp.setattr(scs, "tier2_fill_non_negotiables", _empty)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    mp.setattr(scs, "get_product_image_url", _image)
    mp.setattr(scs, "get_user_demographics", _demo)
    mp.setattr(scs, "_fire_and_forget", _ff)
    svc._get_specs = _specs
    svc._get_price = _price
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _empty
    svc._fetch_behavior_profile = _no_profile


async def _compare(mp, kind, *, vision=None, state=None, **kw):
    scs = _scs()
    state = state if state is not None else {}
    mp.setattr(scs, "STREAM_HARD_CAP_SECONDS", 30.0)
    svc = scs.StructuredComparisonService()
    _install(mp, svc, state)
    kwargs = dict(kw)
    if vision:
        kwargs["vision_products"] = copy.deepcopy(vision)
    if kind == "rest":
        return await asyncio.wait_for(svc.compare_from_text(QUERY, region="bahrain", nocache=True, **kwargs), 60)
    events = []

    async def _drain():
        async for event in svc.compare_from_text_streaming(QUERY, region="bahrain", nocache=True, **kwargs):
            events.append(list(event))
    await asyncio.wait_for(_drain(), 60)
    return events


def _complete(events):
    for kind, payload in events:
        if kind == "complete":
            return payload
    raise AssertionError("no complete event: %r" % ([e[0] for e in events],))


def _entry_body(mp, entry):
    state = {"demographics_profile": _profile()}
    if entry == "text":
        body = asyncio.run(_compare(mp, "rest", state=state, user_id=UID))
    elif entry == "stream":
        body = _complete(asyncio.run(_compare(mp, "stream", state=state, user_id=UID)))
    else:
        body = asyncio.run(_compare(mp, "rest", vision=VISION, state=state, user_id=UID))
    assert state.get("demo_calls") == 1, state
    assert isinstance(body, dict) and body.get("success") is True, str(body)[:300]
    assert (body.get("metadata") or {}).get("cohort_injected") is True, body.get("metadata")
    return body


# ---------------------------------------------------------------------------
# builder fixtures (the tests/test_partial_response_no_fabricated_scores.py shape)
# ---------------------------------------------------------------------------

def _product(brand, model, amount, rating, reviews, slug):
    name = brand + " " + model
    return {
        "brand": brand, "name": name, "full_name": name, "category": "electronics",
        "price": {"amount": amount, "currency": "BHD", "retailer": "Example Store", "title": name,
                  "url": "https://example.com/p/" + slug, "source_method": "local_bhd", "estimated": False},
        "best_price": amount,
        "specs": {"storage_gb": 256, "ram_gb": 8, "screen_size": 6.5},
        "reviews": {"review_summary": {"overall_sentiment": "positive", "consensus": "solid", "highlights": [],
                                       "review_volume": "moderate", "agreement_level": "moderate"}},
        "rating": rating, "rating_source": "Example Store", "review_count": reviews,
        "image_url": None, "fact_check": {},
    }


def _pair():
    return [_product("Alpha", "Phone", 250.0, 4.1, 12, "alpha"), _product("Beta", "Phone", 150.0, 4.6, 950, "beta")]


def _builder(cohort, *, scored):
    from app.services.response_builder import build_comparison_response
    from app.services.scoring_service import get_scoring_service

    products = _pair()
    scoring = get_scoring_service().compute_scores(_pair()) if scored else None
    comparison = {"winner_index": 1, "winner_declaration": "Beta Phone",
                  "winner_reason": "Cheaper and far better reviewed.",
                  "key_tradeoff": "Alpha Phone has the brighter screen."}
    return build_comparison_response(product_data=products, comparison=comparison, scoring_result=scoring,
                                     category_used="electronics", query="Alpha Phone vs Beta Phone",
                                     cohort_summary=copy.deepcopy(cohort))


VOLATILE_ALLOWED = frozenset({"timestamp", "generated_at", "created_at", "elapsed_ms", "elapsed_seconds",
                              "request_id", "cached_at", "fetched_at", "retrieved_at"})


def _volatile_paths(a, b, path=()):
    out = set()
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.add(path + (k,))
            else:
                out |= _volatile_paths(a[k], b[k], path + (k,))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out |= _volatile_paths(x, y, path + (i,))
    elif a != b:
        out.add(path)
    return out


def _identical_but_the_key(scored):
    base1 = _builder(None, scored=scored)
    base2 = _builder(None, scored=scored)
    vol = _volatile_paths(base1, base2)
    assert all(p and p[-1] in VOLATILE_ALLOWED for p in vol), sorted(map(str, vol))
    with_block = _builder({"peer_count": 53, "governorate": "Northern"}, scored=scored)
    assert with_block.get("cohort_summary") == {"peer_count": 53, "governorate": "Northern"}
    trimmed = dict(with_block)
    trimmed.pop("cohort_summary")
    assert _drop_volatile(trimmed) == _drop_volatile(base1)
    assert _drop_volatile(base2) == _drop_volatile(base1)


def _drop_volatile(obj):
    """Remove every key named in VOLATILE_ALLOWED at any depth (a clock read can differ
    between two builds of the same input)."""
    if isinstance(obj, dict):
        return {k: _drop_volatile(v) for k, v in obj.items() if k not in VOLATILE_ALLOWED}
    if isinstance(obj, list):
        return [_drop_volatile(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r9_1_resolved_cohort_yields_none(monkeypatch):
    """R9-1: a profile that passes was_cohort_block_active (exact / medium / key / n=53 /
    Northern), flag "true": the helper returns None."""
    from app.services.extraction_service import was_cohort_block_active

    monkeypatch.setenv(FLAG, "true")
    assert was_cohort_block_active(_profile()) is True
    assert _build(_profile()) is None


def test_r9_2_none_for_padded_flag_and_broadened(monkeypatch):
    """R9-2: the flag "  TRUE " and quality broadened_governorate: None."""
    from app.services.extraction_service import was_cohort_block_active

    monkeypatch.setenv(FLAG, "  TRUE ")
    prof = _profile(quality="broadened_governorate")
    assert was_cohort_block_active(prof) is True
    assert _build(prof) is None


def test_r9_3_partial_response_has_no_block(monkeypatch):
    """R9-3: the hard-cap partial (scs:3917 call site) with the profile in its build ctx:
    no cohort_summary key."""
    scs = _scs()
    svc = scs.get_comparison_service()
    svc._partial_build_ctx = {"query": "Alpha Phone vs Beta Phone", "region": "bahrain",
                              "category_used": "electronics", "from_cache": False,
                              "user_preferences": None, "demographics_profile": _profile()}
    svc._partial_product_data = _pair()
    svc._partial_scoring_result = None
    svc._partial_comparison = None
    svc._partial_product_names = None
    svc._early_specs_buffer = _pair()
    result = svc._build_partial_response(elapsed_seconds=1.0)
    assert isinstance(result, dict) and result.get("products"), str(result)[:300]
    assert "cohort_summary" not in result, result.get("cohort_summary")


@pytest.mark.parametrize("entry", ["text", "stream", "camera"])
def test_r9_4_entry_response_has_no_block(monkeypatch, entry):
    """R9-4 (R-G1-6, one row per call site): the text entry (scs:4806), the streaming
    complete frame (scs:5698) and the camera entry (vision products through
    compare_from_text) with a matched cohort and the flag ON: no cohort_summary key.
    metadata.cohort_injected stays True (the verdict-prompt cohort block is untouched)."""
    body = _entry_body(monkeypatch, entry)
    assert "cohort_summary" not in body, body.get("cohort_summary")


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

def test_p9_1_prompt_cohort_gate_untouched(monkeypatch):
    """P9-1: was_cohort_block_active is True with the flag ON and False with "false"."""
    from app.services.extraction_service import was_cohort_block_active

    monkeypatch.setenv(FLAG, "true")
    assert was_cohort_block_active(_profile()) is True
    monkeypatch.setenv(FLAG, "false")
    assert was_cohort_block_active(_profile()) is False


def test_p9_2_scored_response_identical_but_the_key():
    """P9-2: with a scoring result, resp(dict) minus cohort_summary == resp(None) (volatile
    keys measured by two identical builds, a subset of VOLATILE_ALLOWED)."""
    _identical_but_the_key(scored=True)


def test_p9_3_legacy_response_identical_but_the_key():
    """P9-3: the same without a scoring result (the legacy GPT-index shape)."""
    _identical_but_the_key(scored=False)


def test_p9_4_builder_still_accepts_dict_and_none():
    """P9-4: the builder attaches a valid dict and omits None."""
    block = {"peer_count": 7, "governorate": "Capital"}
    assert _builder(block, scored=True)["cohort_summary"] == block
    assert "cohort_summary" not in _builder(None, scored=True)


def test_p9_5_call_sites_unchanged():
    """P9-5 (footprint; adapted to R-G1-6): the three call-site strings keep the counts the
    wiring guard asserts (2 + 1) and was_cohort_block_active( is still called at the two
    metadata sites OUTSIDE the helper (the helper's own call is removed by R-G1-6)."""
    scs = _scs()
    src = inspect.getsource(scs)
    assert src.count("cohort_summary=self._build_cohort_summary(demographics_profile),") == 2
    assert src.count('cohort_summary=self._build_cohort_summary(ctx.get("demographics_profile")),') == 1
    helper_src = inspect.getsource(scs.StructuredComparisonService._build_cohort_summary)
    outside = src.replace(helper_src, "")
    assert outside.count("was_cohort_block_active(") == 2, outside.count("was_cohort_block_active(")

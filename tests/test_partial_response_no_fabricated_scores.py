"""W4-4 / PO-VERDICT-TRUTH-02 — a partial must not invent a score it never computed.

Spec: `.qa-w4/W4_4_UNIT_SPEC.md` § 4, AS AMENDED by its binding "FABLE REVIEW
RULINGS (2026-09-23)" section (R1 stage split, R4 vocabulary, R6 test list).

Flag `ENABLE_HONEST_PARTIAL_SCORING` (default OFF, read per call). With it ON:

* R1(i)  post-gather stash present (`_partial_product_data`) and scoring absent
         ⇒ `_build_partial_response` runs `compute_scores` on the stash (pure CPU,
         no LLM, no network) and builds NORMALLY: real `scoring_v2`, real crown.
* R1(ii) early-buffer only (no post-gather stash) ⇒ `scoring_v2: null` — the key
         stays, its value is None (never popped).
* R1(iii) whenever `scoring_v2` is nulled ⇒ `overview.winner.reason`,
         `overview.winner.key_tradeoff` and the top-level `recommendation` alias
         are blanked ("").

UNFLAGGED: `metadata.partial_stage` on every `_build_partial_response` body, one of
`gather | post_gather | scoring | verdict` (R4 — never `none`).

Test numbering follows the spec's § 4 table; each docstring says RED (the behaviour
is absent at base `b63a8368`) or PIN (passes at base and must stay green).
Everything is in-process: products are dicts, the orchestrator is a real
`get_comparison_service()` instance with its partial stash set by hand, no network
(an autouse socket guard), no LLM (`generate_comparison` is replaced by a mock that
fails the test if awaited).
"""

import copy
import json
import logging
import socket
from unittest.mock import AsyncMock

import pytest

from app.services import response_builder as rb
from app.services import structured_comparison_service as scs
from app.services.database_service import _validate_renderable
from app.services.response_builder import _build_scoring_v2, build_comparison_response
from app.services.scoring_service import ScoringService, get_scoring_service
from app.services.structured_comparison_service import get_comparison_service

FLAG = "ENABLE_HONEST_PARTIAL_SCORING"
QUERY = "Alpha Phone vs Beta Phone"
CATEGORY = "electronics"
STAGES = ("gather", "post_gather", "scoring", "verdict")

# The fabricated pair the `, 50)` defaults at `_build_scoring_v2` produce today.
FABRICATED_OVERALL = {"product_a": 70, "product_b": 69, "winner_idx": 0}
TODAY_REASON = "Alpha Phone is the stronger overall pick."

FLAG_ON_VALUES = ("1", "true", "on")
FLAG_OFF_VALUES = (None, "", "false", "0", "no", "off")


# ---------------------------------------------------------------------------
# Guards: zero network, zero LLM
# ---------------------------------------------------------------------------
_LOOPBACK = ("127.0.0.1", "::1", "localhost")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail the test on any non-loopback connect (loopback stays open so the
    asyncio self-pipe socketpair on Windows keeps working)."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _host(address):
        return address[0] if isinstance(address, tuple) and address else address

    def _guarded_connect(self, address, *a, **k):
        if _host(address) in _LOOPBACK:
            return real_connect(self, address, *a, **k)
        raise AssertionError(f"W4-4 test attempted a network connect to {address!r}")

    def _guarded_connect_ex(self, address, *a, **k):
        if _host(address) in _LOOPBACK:
            return real_connect_ex(self, address, *a, **k)
        raise AssertionError(f"W4-4 test attempted a network connect to {address!r}")

    real_getaddrinfo = socket.getaddrinfo

    def _guarded_getaddrinfo(host, *a, **k):
        name = host.decode() if isinstance(host, bytes) else host
        if name is None or name in _LOOPBACK:
            return real_getaddrinfo(host, *a, **k)
        raise AssertionError(f"W4-4 test attempted a DNS lookup of {host!r}")

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)
    yield


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """`generate_comparison` is the GPT verdict call. R1(i) says the partial path
    computes scores with NO LLM call; any await of it fails the test."""
    mock = AsyncMock(side_effect=AssertionError("W4-4: generate_comparison awaited on a partial"))
    monkeypatch.setattr(scs, "generate_comparison", mock)
    yield mock


@pytest.fixture
def compute_spy(monkeypatch):
    """Counts every `ScoringService.compute_scores` call while delegating to the
    real method (so results are the real ones)."""
    calls = []
    real = ScoringService.compute_scores

    def _spy(self, *a, **k):
        calls.append((a, k))
        return real(self, *a, **k)

    monkeypatch.setattr(ScoringService, "compute_scores", _spy)
    return calls


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


# ---------------------------------------------------------------------------
# Fixture products — spec § 1.3: Alpha BHD 250, 4.1★/12; Beta BHD 150, 4.6★/950.
# `local_bhd` + title + PDP url keep both prices SHOWABLE through the response
# chokepoint, so the price/value dimensions are real (price 79/85 winner=1).
# ---------------------------------------------------------------------------
def _product(brand, model, amount, rating, reviews, slug):
    name = f"{brand} {model}"
    return {
        "brand": brand,
        "name": name,
        "full_name": name,
        "category": CATEGORY,
        "price": {
            "amount": amount,
            "currency": "BHD",
            "retailer": "Example Store",
            "title": name,
            "url": f"https://example.com/p/{slug}",
            "source_method": "local_bhd",
            "estimated": False,
        },
        "best_price": amount,
        "specs": {"storage_gb": 256, "ram_gb": 8, "screen_size": 6.5},
        "reviews": {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "solid",
                "highlights": [],
                "review_volume": "moderate",
                "agreement_level": "moderate",
            }
        },
        "rating": rating,
        "rating_source": "Example Store",
        "review_count": reviews,
        "image_url": None,
        "fact_check": {},
    }


def _alpha():
    return _product("Alpha", "Phone", 250.0, 4.1, 12, "alpha")


def _beta():
    return _product("Beta", "Phone", 150.0, 4.6, 950, "beta")


def _pair():
    return [_alpha(), _beta()]


def _specs_only(p):
    q = copy.deepcopy(p)
    q["price"] = None
    q["best_price"] = None
    q["rating"] = None
    q["review_count"] = None
    return q


def _gpt_verdict():
    """A GPT-shaped verdict naming the product `compute_scores` crowns (Beta)."""
    return {
        "winner_index": 1,
        "winner_declaration": "Beta Phone",
        "winner_reason": "Cheaper and far better reviewed.",
        "key_tradeoff": "Alpha Phone has the brighter screen.",
    }


def _real_scoring():
    return get_scoring_service().compute_scores(_pair())


def _builder(*, scoring_result=None, comparison=None, products=None, partial=True):
    kwargs = dict(
        product_data=products if products is not None else _pair(),
        comparison={} if comparison is None else comparison,
        scoring_result={} if scoring_result is None else scoring_result,
        category_used=CATEGORY,
        query=QUERY,
    )
    if partial:
        kwargs["metadata"] = {"partial": True}
    return build_comparison_response(**kwargs)


def _twin(*, product_data=None, scoring_result=None, comparison=None, early=None):
    """A real orchestrator instance with its partial stash set exactly as
    `_compare_from_text_impl` sets it at each stage."""
    svc = get_comparison_service()
    svc._partial_build_ctx = {
        "query": QUERY,
        "region": "bahrain",
        "category_used": CATEGORY,
        "from_cache": False,
        "user_preferences": None,
    }
    svc._partial_product_data = product_data
    svc._partial_scoring_result = scoring_result
    svc._partial_comparison = comparison
    svc._partial_product_names = None
    svc._early_specs_buffer = early
    return svc


def _post_gather_twin():
    return _twin(product_data=_pair(), early=_pair())


def _early_twin(specs_only=False):
    early = [_specs_only(_alpha()), _specs_only(_beta())] if specs_only else _pair()
    return _twin(product_data=None, early=early)


def _stage_twin(stage):
    if stage == "gather":
        return _twin(product_data=None, early=_pair())
    if stage == "post_gather":
        return _twin(product_data=_pair(), early=_pair())
    if stage == "scoring":
        return _twin(product_data=_pair(), scoring_result=_real_scoring(), early=_pair())
    if stage == "verdict":
        return _twin(
            product_data=_pair(), scoring_result=_real_scoring(),
            comparison=_gpt_verdict(), early=_pair(),
        )
    raise AssertionError(stage)


def _build(svc):
    return svc._build_partial_response(elapsed_seconds=30.0)


def _fe_crown(resp):
    """The client's crown rule, ResultsScreen.tsx:772-778 (HEAD) / :689-695 (97b5f15):
    scoring_v2 truthy ⇒ (product_a ?? 0) >= (product_b ?? 0) ? 0 : 1;
    else ⇒ winner_index === 1 ? 1 : 0."""
    v2 = resp.get("scoring_v2")
    if v2:  # JS truthiness of an object: any dict (even {}) is truthy
        ov = v2.get("overall_score") or {}
        a = ov.get("product_a")
        b = ov.get("product_b")
        return 0 if (a if a is not None else 0) >= (b if b is not None else 0) else 1
    return 1 if resp.get("winner_index") == 1 else 0


def _assert_verdict_text_blank(resp):
    w = resp["overview"]["winner"]
    assert w["reason"] == "", f"overview.winner.reason not blanked: {w['reason']!r}"
    assert w["key_tradeoff"] == "", f"overview.winner.key_tradeoff not blanked: {w['key_tradeoff']!r}"
    assert resp["recommendation"] == "", f"recommendation not blanked: {resp['recommendation']!r}"


# ===========================================================================
# 1 — RED. Builder, flag ON, empty scoring_result ⇒ scoring_v2 null + blanks.
# ===========================================================================
@pytest.mark.parametrize("flag_value", FLAG_ON_VALUES)
def test_01_flag_on_builder_empty_scoring_nulls_scoring_v2_and_blanks_verdict(monkeypatch, flag_value):
    """RED (R1(ii)+(iii) at the builder). Today: a dict carrying 70/69, margin 1,
    and the input-order reason 'Alpha Phone is the stronger overall pick.'"""
    _set_flag(monkeypatch, flag_value)
    res = _builder()
    assert "scoring_v2" in res, "scoring_v2 must stay a key (null, never popped — R2)"
    assert res.get("scoring_v2") is None, (
        f"flag ON + no computed overall must ship scoring_v2=None, got {res.get('scoring_v2')!r:.160}"
    )
    _assert_verdict_text_blank(res)
    assert res["metadata"]["partial"] is True
    assert res["success"] is True


def test_01b_flag_on_builder_blanks_gpt_prose_when_scoring_absent(monkeypatch):
    """RED (R1(iii), discriminating fixture: GPT prose present so a no-op on the
    already-empty key_tradeoff cannot pass). Defence-in-depth for the PUBLIC
    builder — the orchestrator never stashes a verdict without a scoring result
    (`_partial_comparison` is assigned strictly after `_partial_scoring_result`)."""
    _set_flag(monkeypatch, "true")
    comparison = {
        "winner_index": 0,
        "winner_declaration": "Alpha Phone",
        "winner_reason": "Alpha Phone has the brighter screen.",
        "key_tradeoff": "Beta Phone is cheaper.",
    }
    res = _builder(comparison=comparison)
    assert res.get("scoring_v2") is None
    _assert_verdict_text_blank(res)


def test_01c_extra_flag_on_bc_comparison_alias_also_blank(monkeypatch):
    """RED — EXTRA, NOT in spec/rulings (flagged for Fable): the BC
    `result["comparison"]` alias carries the SAME scrubbed reason/key_tradeoff
    and is persisted to comparisons.full_response. If R1(iii) blanks only the
    overview/recommendation projections, the alias still ships the input-order
    verdict. Drop this test if the ruling intends the alias to be left alone."""
    _set_flag(monkeypatch, "true")
    comparison = {
        "winner_index": 0,
        "winner_declaration": "Alpha Phone",
        "winner_reason": "Alpha Phone has the brighter screen.",
        "key_tradeoff": "Beta Phone is cheaper.",
    }
    res = _builder(comparison=comparison)
    assert res.get("scoring_v2") is None
    assert res["comparison"].get("winner_reason", "") == ""
    assert res["comparison"].get("key_tradeoff", "") == ""


# ===========================================================================
# 2 — RED. _build_scoring_v2, flag ON, any absent `overall` ⇒ None.
# ===========================================================================
_ABSENT_OVERALL_ROWS = [
    pytest.param({}, id="empty"),
    pytest.param({"scores": {}}, id="scores-empty"),
    # rows below: defence-in-depth for the PUBLIC builder — unreachable through the
    # orchestrator (compute_scores yields both products or neither; settled, R6).
    pytest.param({"scores": {"product_0": {"overall": 62.0}}}, id="did-p0-only"),
    pytest.param({"scores": {"product_1": {"overall": 62.0}}}, id="did-p1-only"),
    pytest.param({"scores": {"product_0": {"overall": None}, "product_1": {"overall": 48.0}}}, id="did-p0-None"),
]


@pytest.mark.parametrize("winner_index", (0, 1))
@pytest.mark.parametrize("scoring_result", _ABSENT_OVERALL_ROWS)
def test_02_flag_on_absent_overall_returns_none(monkeypatch, scoring_result, winner_index):
    """RED. Today every row returns a calibrated dict (70/69, 76/70, 70/69 …)."""
    _set_flag(monkeypatch, "true")
    v2 = _build_scoring_v2(_pair(), copy.deepcopy(scoring_result), CATEGORY, winner_index)
    assert v2 is None, f"expected None, got {v2!r:.160}"


# ===========================================================================
# 3 — RED. Orchestrator twin, post-gather stash, flag ON ⇒ compute + normal build.
# ===========================================================================
def test_03_flag_on_post_gather_partial_computes_real_scores(monkeypatch, compute_spy, _no_llm):
    """RED (R1(i)). The reference is the SAME partial built from a stash whose
    scoring landed (`_partial_scoring_result = compute_scores(pair)`), i.e.
    "build normally". Today: scoring.scores == {}, 70/69 fabricated, crown 0."""
    _set_flag(monkeypatch, None)
    ref_sr = _real_scoring()
    ref = _build(_twin(product_data=_pair(), scoring_result=ref_sr, early=_pair()))
    assert ref_sr["winner_index"] == 1, "fixture premise: compute_scores crowns Beta"
    compute_spy.clear()

    _set_flag(monkeypatch, "true")
    resp = _build(_post_gather_twin())

    assert resp["winner_index"] == ref_sr["winner_index"], (
        f"crown must be compute_scores' winner ({ref_sr['winner_index']}), got {resp['winner_index']}"
    )
    assert compute_spy, "compute_scores was never called on the post-gather stash"
    scores = resp["scoring"]["scores"]
    assert {k: (scores.get(k) or {}).get("overall") for k in ("product_0", "product_1")} == {
        k: ref_sr["scores"][k]["overall"] for k in ("product_0", "product_1")
    }
    v2 = resp["scoring_v2"]
    assert isinstance(v2, dict) and v2, "post-gather partial must keep a real scoring_v2"
    assert v2["overall_score"] != FABRICATED_OVERALL
    assert v2["overall_score"] == ref["scoring_v2"]["overall_score"]
    assert v2["win_margin"] == ref["scoring_v2"]["win_margin"]
    assert v2["dimensions"] == ref["scoring_v2"]["dimensions"]
    assert v2["factual_verdict"] == ref["scoring_v2"]["factual_verdict"]
    assert v2["confidence_legs"] == ref["scoring_v2"]["confidence_legs"]
    assert resp["overview"]["winner"] == ref["overview"]["winner"]
    assert resp["overview"]["tradeoffs"] == ref["overview"]["tradeoffs"]
    assert resp["recommendation"] == ref["recommendation"]
    assert resp["recommendation"] != ""  # real scores ⇒ NOT blanked
    assert resp["metadata"]["partial"] is True
    assert resp["success"] is True
    _no_llm.assert_not_awaited()


@pytest.mark.parametrize("flag_value", (None, "true"))
@pytest.mark.parametrize("stage", STAGES)
def test_03b_pin_partial_never_calls_the_llm(monkeypatch, _no_llm, flag_value, stage):
    """PIN (both flag states, every stage). No GPT verdict call and no network on a
    partial — the autouse guards fail the test otherwise. Green today."""
    _set_flag(monkeypatch, flag_value)
    resp = _build(_stage_twin(stage))
    assert resp["success"] is True
    _no_llm.assert_not_awaited()


def test_03c_flag_on_scoring_stage_reuses_the_stash(monkeypatch, compute_spy):
    """PIN. When scoring already landed (stage `scoring`/`verdict`), flag ON must
    not recompute: output identical to flag OFF and zero compute_scores calls."""
    sr = _real_scoring()
    _set_flag(monkeypatch, None)
    off = _build(_twin(product_data=_pair(), scoring_result=copy.deepcopy(sr), early=_pair()))
    _set_flag(monkeypatch, "true")
    compute_spy.clear()
    on = _build(_twin(product_data=_pair(), scoring_result=copy.deepcopy(sr), early=_pair()))
    assert compute_spy == []
    assert on["scoring_v2"] == off["scoring_v2"]
    assert on["overview"]["winner"] == off["overview"]["winner"]
    assert on["recommendation"] == off["recommendation"]


_PRICE_PRIORITY = {"priorities": ["price"]}


def test_03d_flag_on_post_gather_compute_threads_ctx_user_preferences(monkeypatch, compute_spy):
    """PIN (Ruling 2: "compute_scores on the stash with the ctx user_preferences").
    A signed-in user's explicit priorities must reach the post-gather partial
    crown. Discriminating fixture: `{"priorities": ["price"]}` moves the real
    overalls (54.2/77.5 → 53.0/81.0) and flips `scoring_method` to
    `personalized`, so dropping the kwarg (preferences=None) reddens both the
    spy assertion AND the result-level ones."""
    unpersonalised = get_scoring_service().compute_scores(_pair())
    personalised = get_scoring_service().compute_scores(_pair(), preferences=copy.deepcopy(_PRICE_PRIORITY))
    ov = lambda sr: {k: sr["scores"][k]["overall"] for k in ("product_0", "product_1")}  # noqa: E731
    assert ov(personalised) != ov(unpersonalised), "fixture premise: price priority moves the overalls"
    assert personalised["scoring_method"] == "personalized"
    assert unpersonalised["scoring_method"] != "personalized"

    _set_flag(monkeypatch, "true")
    svc = _post_gather_twin()
    svc._partial_build_ctx["user_preferences"] = copy.deepcopy(_PRICE_PRIORITY)
    compute_spy.clear()
    resp = _build(svc)

    assert len(compute_spy) == 1, f"expected exactly one compute_scores call, got {len(compute_spy)}"
    _args, kwargs = compute_spy[0]
    assert kwargs.get("preferences") == _PRICE_PRIORITY, (
        f"ctx user_preferences not threaded into compute_scores: {kwargs!r:.200}"
    )
    assert resp["scoring"]["scoring_method"] == "personalized"
    assert {k: resp["scoring"]["scores"][k]["overall"] for k in ("product_0", "product_1")} == ov(personalised)
    assert resp["winner_index"] == personalised["winner_index"]


def test_03e_flag_on_post_gather_compute_does_not_write_back_to_the_stash(monkeypatch):
    """PIN. The R1(i) compute is local to the build: `_partial_scoring_result`
    stays None, so a later build on the same instance still reports
    `post_gather` (the stage the partial CARRIED) rather than a `scoring` stage
    that never ran in the pipeline. Mutation N5 (write the computed scores back
    into the stash) reddens this test."""
    _set_flag(monkeypatch, "true")
    svc = _post_gather_twin()
    first = _build(svc)
    assert svc._partial_scoring_result is None, "computed scores written back into the stash"
    second = _build(svc)
    assert first["metadata"]["partial_stage"] == "post_gather"
    assert second["metadata"]["partial_stage"] == "post_gather"


# ===========================================================================
# 4 — RED. Orchestrator twin, early buffer only, flag ON ⇒ null + blanks.
# ===========================================================================
@pytest.mark.parametrize("specs_only", (False, True), ids=("early-full", "early-specs-only"))
def test_04_flag_on_early_buffer_partial_nulls_scoring_v2(monkeypatch, specs_only):
    """RED (R1(ii)+(iii)). Today: 70/69 margin 1 and the input-order reason."""
    _set_flag(monkeypatch, "true")
    svc = _early_twin(specs_only=specs_only)
    assert svc._partial_has_usable_data() is True
    resp = _build(svc)
    assert "scoring_v2" in resp
    assert resp.get("scoring_v2") is None, f"got {resp.get('scoring_v2')!r:.160}"
    _assert_verdict_text_blank(resp)
    assert resp["metadata"]["partial"] is True
    assert resp["success"] is True


# ===========================================================================
# 5 — PIN. Flag OFF ⇒ today's bytes (the § 1.3 / § 1.4 table), every OFF spelling.
# ===========================================================================
@pytest.mark.parametrize("flag_value", FLAG_OFF_VALUES)
def test_05a_pin_flag_off_builder_is_unchanged(monkeypatch, flag_value):
    """PIN (flag-OFF identity). Mutation 'reader returns True' reddens this."""
    _set_flag(monkeypatch, flag_value)
    res = _builder()
    assert res["scoring_v2"]["overall_score"] == FABRICATED_OVERALL
    assert res["scoring_v2"]["win_margin"] == 1
    assert res["overview"]["winner"]["reason"] == TODAY_REASON
    assert res["recommendation"] == TODAY_REASON
    assert res["winner_index"] == 0
    assert "scoring_v2" in res


@pytest.mark.parametrize("flag_value", FLAG_OFF_VALUES)
def test_05b_pin_flag_off_post_gather_partial_is_unchanged(monkeypatch, compute_spy, flag_value):
    """PIN (flag-OFF identity for R1(i)): no compute, scores {}, 70/69, reason kept."""
    _set_flag(monkeypatch, flag_value)
    resp = _build(_post_gather_twin())
    assert compute_spy == [], "flag OFF must not compute scores on the partial path"
    assert resp["scoring"]["scores"] == {}
    assert resp["scoring_v2"]["overall_score"] == FABRICATED_OVERALL
    assert resp["scoring_v2"]["win_margin"] == 1
    assert resp["overview"]["winner"]["reason"] == TODAY_REASON
    assert resp["winner_index"] == 0


@pytest.mark.parametrize("flag_value", FLAG_OFF_VALUES)
def test_05c_pin_flag_off_early_partial_is_unchanged(monkeypatch, flag_value):
    """PIN (flag-OFF identity for R1(ii)/(iii))."""
    _set_flag(monkeypatch, flag_value)
    resp = _build(_early_twin())
    assert resp["scoring_v2"]["overall_score"] == FABRICATED_OVERALL
    assert resp["scoring_v2"]["win_margin"] == 1
    assert resp["overview"]["winner"]["reason"] == TODAY_REASON
    assert resp["recommendation"] == TODAY_REASON


# ===========================================================================
# 6 — PIN. Real scores ⇒ identical in both flag states.
# ===========================================================================
@pytest.mark.parametrize("flag_value", (None, "true"))
def test_06_pin_real_scores_unchanged_in_both_flag_states(monkeypatch, flag_value):
    """PIN. 62/48 ⇒ 76/69 margin 7; and a full-scores build keeps its reason."""
    _set_flag(monkeypatch, flag_value)
    sr = {"scores": {"product_0": {"overall": 62.0}, "product_1": {"overall": 48.0}}}
    v2 = _build_scoring_v2(_pair(), sr, CATEGORY, 0)
    assert v2["overall_score"] == {"product_a": 76, "product_b": 69, "winner_idx": 0}
    assert v2["win_margin"] == 7
    res = _builder(scoring_result=_real_scoring(), comparison=_gpt_verdict())
    assert isinstance(res["scoring_v2"], dict) and res["scoring_v2"]
    assert res["overview"]["winner"]["reason"] == "Cheaper and far better reviewed."
    assert res["recommendation"] == "Cheaper and far better reviewed."
    assert res["overview"]["winner"]["key_tradeoff"] == "Alpha Phone has the brighter screen."


# ===========================================================================
# 7 — PIN. The `len(product_data) < 2 → {}` guard fires first, both flag states.
# ===========================================================================
@pytest.mark.parametrize("flag_value", (None, "true"))
@pytest.mark.parametrize("n_products", (0, 1))
def test_07_pin_fewer_than_two_products_still_returns_empty_dict(monkeypatch, flag_value, n_products):
    """PIN (guard ORDER). `{}`, never None — tests/test_scoring_v2_confidence.py
    asserts isinstance(dict). Mutation 'branch above the guard' reddens this."""
    _set_flag(monkeypatch, flag_value)
    v2 = _build_scoring_v2(_pair()[:n_products], {}, CATEGORY, 0)
    assert v2 == {}
    assert isinstance(v2, dict)


# ===========================================================================
# 8 — rewritten by R6 for the stage split.
# ===========================================================================
def test_08a_flag_on_post_gather_crown_is_the_scored_winner(monkeypatch):
    """RED (R6). Post-gather ⇒ crown = compute_scores' winner (Beta, index 1) on
    EVERY crown surface, including the client's own crown rule. Today: 0 (input
    order) on all of them."""
    _set_flag(monkeypatch, "true")
    resp = _build(_post_gather_twin())
    assert resp["winner_index"] == 1
    assert resp["overview"]["winner"]["product_index"] == 1
    assert resp["overview"]["winner"]["name"] == "Beta Phone"
    assert resp["scoring_v2"]["overall_score"]["winner_idx"] == 1
    assert resp["scoring_v2"]["overall_score"]["product_b"] > resp["scoring_v2"]["overall_score"]["product_a"]
    assert resp["comparison"]["winner_index"] == 1
    assert _fe_crown(resp) == 1


def test_08b_flag_on_early_buffer_crown_stays_input_order_with_null_and_blanks(monkeypatch):
    """RED (R6). Early buffer ⇒ winner_index 0 (unchanged; no backend-only fix
    moves it), scoring_v2 null AND reason/key_tradeoff/recommendation blank; the
    legacy `scoring` fallback premise (`!scoring_v2 && scoring`) still holds."""
    _set_flag(monkeypatch, "true")
    resp = _build(_early_twin())
    assert resp.get("scoring_v2") is None
    _assert_verdict_text_blank(resp)
    assert resp["winner_index"] == 0
    assert resp["overview"]["winner"]["product_index"] == 0
    assert _fe_crown(resp) == 0
    scoring = resp["scoring"]
    assert isinstance(scoring, dict) and scoring
    assert set(scoring) == {
        "scores", "dimension_winners", "price_tiers", "is_cross_tier",
        "scoring_method", "category_weights",
    }
    assert [p["overall_score"] for p in resp["overview"]["products"]] == [None, None]


# ===========================================================================
# 9 — PIN. Serialisable + persistable in both flag states, every partial shape.
# ===========================================================================
@pytest.mark.parametrize("flag_value", (None, "true"))
@pytest.mark.parametrize("shape", ("builder", "post_gather", "early"))
def test_09_pin_partial_serialises_and_stays_renderable(monkeypatch, flag_value, shape):
    """PIN. json.dumps succeeds and database_service._validate_renderable is True."""
    _set_flag(monkeypatch, flag_value)
    if shape == "builder":
        resp = _builder()
    elif shape == "post_gather":
        resp = _build(_post_gather_twin())
    else:
        resp = _build(_early_twin())
    blob = json.dumps(resp, default=str)
    assert len(blob) > 1000
    assert _validate_renderable(resp) is True


# ===========================================================================
# 10 — RED, UNFLAGGED. metadata.partial_stage on every partial.
# ===========================================================================
@pytest.mark.parametrize("flag_value", (None, "true"))
@pytest.mark.parametrize("stage", STAGES)
def test_10_partial_stage_names_the_stage_the_partial_carried(monkeypatch, flag_value, stage):
    """RED (R4 vocabulary gather/post_gather/scoring/verdict — never `none`).
    Unflagged, so both flag states must carry it. Today the key is ABSENT."""
    _set_flag(monkeypatch, flag_value)
    resp = _build(_stage_twin(stage))
    got = resp["metadata"].get("partial_stage", "<ABSENT>")
    assert got == stage, f"metadata.partial_stage: expected {stage!r}, got {got!r}"
    assert got in STAGES
    assert resp["metadata"]["partial"] is True


# ===========================================================================
# 11 — PIN. A non-partial response has no partial_stage.
# ===========================================================================
@pytest.mark.parametrize("flag_value", (None, "true"))
def test_11_pin_non_partial_response_has_no_partial_stage(monkeypatch, flag_value):
    """PIN. Mutation 'add partial_stage to the auto-built metadata' reddens this."""
    _set_flag(monkeypatch, flag_value)
    res = _builder(scoring_result=_real_scoring(), comparison=_gpt_verdict(), partial=False)
    assert "partial_stage" not in res["metadata"]
    assert "partial" not in res["metadata"]


# ===========================================================================
# 12 — the reader (new symbol; red at base because it does not exist).
# ===========================================================================
def _reader():
    reader = getattr(rb, "_honest_partial_scoring_enabled", None)
    assert callable(reader), "response_builder._honest_partial_scoring_enabled is absent"
    return reader


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, False),
        ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True), (" on ", True),
        ("false", False), ("0", False), ("", False), ("maybe", False), ("off", False), ("no", False),
    ],
)
def test_12_reader_truth_table(monkeypatch, value, expected):
    """RED at base (symbol absent), green once written. A constant stub fails on
    the opposite half of the table."""
    reader = _reader()
    _set_flag(monkeypatch, value)
    assert reader() is expected


def test_12b_reader_is_read_per_call(monkeypatch):
    """RED at base (symbol absent). A setenv AFTER import flips the very next
    call — a memoised/module-constant reader fails here."""
    reader = _reader()
    monkeypatch.delenv(FLAG, raising=False)
    assert reader() is False
    monkeypatch.setenv(FLAG, "true")
    assert reader() is True
    monkeypatch.setenv(FLAG, "0")
    assert reader() is False


def test_12c_orchestrator_honours_a_flip_between_two_partials(monkeypatch):
    """RED (per-call read on the ORCHESTRATOR side too — R1(i) lives in
    structured_comparison_service, which may keep its own reader). Same process,
    two partials: OFF ⇒ today's bytes; ON ⇒ computed scores."""
    monkeypatch.delenv(FLAG, raising=False)
    off = _build(_post_gather_twin())
    assert off["scoring"]["scores"] == {}
    monkeypatch.setenv(FLAG, "true")
    on = _build(_post_gather_twin())
    assert on["scoring"]["scores"] != {}, "flag flipped ON after import but the partial ignored it"
    monkeypatch.delenv(FLAG, raising=False)
    off_again = _build(_post_gather_twin())
    assert off_again["scoring"]["scores"] == {}


# ===========================================================================
# 13 — PIN. The key SETS do not move with the flag (null, never popped).
# ===========================================================================
@pytest.mark.parametrize("shape", ("builder", "post_gather", "early"))
def test_13_pin_key_sets_identical_across_flag_states(monkeypatch, shape):
    """PIN. Top-level, overview, overview.winner and metadata key sets are equal in
    both flag states. Mutation 'pop scoring_v2' / 'pop reason' reddens this."""
    def _one():
        if shape == "builder":
            return _builder()
        if shape == "post_gather":
            return _build(_post_gather_twin())
        return _build(_early_twin())

    _set_flag(monkeypatch, None)
    off = _one()
    _set_flag(monkeypatch, "true")
    on = _one()
    assert sorted(on) == sorted(off)
    assert "scoring_v2" in on
    assert sorted(on["overview"]) == sorted(off["overview"])
    assert sorted(on["overview"]["winner"]) == sorted(off["overview"]["winner"])
    assert sorted(on["metadata"]) == sorted(off["metadata"])


# ===========================================================================
# 14 — EXTRA (not in spec/rulings, flagged for Fable): fail-soft compute.
# ===========================================================================
def test_14_extra_flag_on_compute_failure_degrades_to_null_not_error(monkeypatch, caplog):
    """RED — EXTRA. If `compute_scores` raises on the post-gather stash, the
    partial must still ship (success:true) and must fall back to the R1(ii)
    honest shape (scoring_v2 null + blanks), never to the fabricated 70/69 and
    never to an exception out of `_build_partial_response` (which today's caller
    would turn into INSUFFICIENT_DATA, losing a renderable partial).

    POLISH pin: the PR's canary line `[W4-4] partial compute_scores failed` is
    a WARNING emitted exactly once, naming the exception TYPE and never echoing
    str(e) (a compute error message can carry product/user text). Mutation
    'log line -> pass' reddens this test."""
    _set_flag(monkeypatch, "true")
    user_text = "W4-4 user text: Chanel No 5 vs Dior Sauvage"

    def _boom(self, *a, **k):
        raise RuntimeError(user_text)

    monkeypatch.setattr(ScoringService, "compute_scores", _boom)
    with caplog.at_level(logging.WARNING, logger=scs.logger.name):
        resp = _build(_post_gather_twin())
    assert resp["success"] is True
    assert resp.get("scoring_v2") is None, f"got {resp.get('scoring_v2')!r:.160}"
    _assert_verdict_text_blank(resp)
    canary = [
        r for r in caplog.records
        if r.getMessage().startswith("[W4-4] partial compute_scores failed")
    ]
    assert len(canary) == 1, [r.getMessage() for r in caplog.records]
    assert canary[0].levelno == logging.WARNING
    assert canary[0].name == scs.logger.name
    assert "RuntimeError" in canary[0].getMessage()
    assert user_text not in canary[0].getMessage()


# ===========================================================================
# 15 — PIN (added at GREEN for FABLE RED-GATE ruling 1): the null and the
# blanks are SCOPED to partials. A NON-partial build with an absent-overall
# scoring_result keeps today's calibrated behaviour in both flag states.
# ===========================================================================
@pytest.mark.parametrize("flag_value", (None, "true"))
def test_15_pin_non_partial_absent_overall_keeps_calibrated_block(monkeypatch, flag_value):
    """PIN. Without it the partial scoping is guarded only by flag-ON runs of
    other files (CI runs flag OFF). Mutation 'honest_null unscoped' reddens the
    flag-ON row."""
    _set_flag(monkeypatch, flag_value)
    res = _builder(partial=False)
    assert isinstance(res["scoring_v2"], dict) and res["scoring_v2"]
    assert res["scoring_v2"]["overall_score"] == FABRICATED_OVERALL
    assert res["scoring_v2"]["win_margin"] == 1
    assert res["overview"]["winner"]["reason"] == TODAY_REASON
    assert res["recommendation"] == TODAY_REASON

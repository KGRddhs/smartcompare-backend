"""Issue #110 — reconcile winner PROSE with the deterministic winner index.

Baseline note (spec challenge, recorded in the unit report): issue #110 was
written against 593ec1e, BEFORE the #99 winner-card reconciliation merged
(dd4c849 / ffccbaf). #99 already ships, UNFLAGGED, on the mismatch path:
  - overview.winner.name    := deterministic winner's product name
  - overview.winner.declaration := ""
  - reason / key_tradeoff   := generic fallback ONLY when they name the loser
  - comparison["winner_index"] := deterministic index (BC alias)
So the flag-OFF pin below asserts the MERGED #99 behavior (the real base of
this branch), not the 593ec1e behavior the issue transcribed. What #110 adds
behind ENABLE_WINNER_PROSE_RECONCILE (default OFF):
  - declaration/reason/key_tradeoff become the deterministic TEMPLATE strings
    (shared helper `deterministic_verdict_fields`, overwrite semantics) —
    replacing prose about GPT's pick even when it never names the loser, and
    sidestepping #123's prefix over-scrub entirely on the flag-ON path;
  - the SSE `verdict` event carries the deterministic index + the same
    reconciled prose, so the streamed winner never flips mid-stream.

Harness copied from tests/test_gpt_winner_lever.py (products / scoring) and
tests/test_streaming.py (SSE fixtures), with a naming comparison factory —
the lever harness's placeholder prose ("x"/"y"/"z") cannot exercise a name
assertion.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.response_builder import build_comparison_response
from app.services.text_sanitize import has_score_internals


# ---------------------------------------------------------------------------
# Harness (sync path) — copied from tests/test_gpt_winner_lever.py
# ---------------------------------------------------------------------------

def _products():
    return [
        {"name": "iPhone 15", "category": "electronics",
         "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.7, "review_count": 1200,
         "specs": {"ram": "6 GB", "storage": "128 GB"}},
        {"name": "Galaxy S24", "category": "electronics",
         "price": {"amount": 280, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.6, "review_count": 1500,
         "specs": {"ram": "8 GB", "storage": "128 GB"}},
    ]


def _scoring_result(winner_index):
    return {
        "scores": {
            "product_0": {"overall": 60.0, "breakdown": {"performance_score": 60.0}},
            "product_1": {"overall": 80.0, "breakdown": {"performance_score": 80.0}},
        },
        "winner_index": winner_index,
        "win_margin": 20.0,
        "is_cross_tier": False,
    }


def _comparison_naming(idx, names=("iPhone 15", "Galaxy S24")):
    """GPT prose that NAMES real products (the lever harness's placeholder
    prose cannot exercise a name assertion)."""
    w, l = names[idx], names[1 - idx]
    return {
        "winner_index": idx,
        "winner_declaration": f"{w} wins",
        "winner_reason": f"{w} has the stronger camera.",
        "key_tradeoff": f"{l} offers more RAM.",
    }


_TRADEOFFS = [{"loser_wins": {"dimension": "price_score", "product": "iPhone 15"}}]


@pytest.fixture
def reconcile_on(monkeypatch):
    monkeypatch.setenv("ENABLE_WINNER_PROSE_RECONCILE", "true")
    yield


@pytest.fixture
def reconcile_off(monkeypatch):
    monkeypatch.delenv("ENABLE_WINNER_PROSE_RECONCILE", raising=False)
    yield


def _mismatch_response(**overrides):
    """Deterministic winner = Galaxy S24 (idx 1), GPT prose names iPhone 15."""
    kwargs = dict(
        product_data=_products(),
        comparison=_comparison_naming(0),
        scoring_result=_scoring_result(1),
        tradeoffs=_TRADEOFFS,
        category_used="electronics",
    )
    kwargs.update(overrides)
    return build_comparison_response(**kwargs)


# ---------------------------------------------------------------------------
# 1. Flag OFF — pin the MERGED #99 mismatch behavior (this branch's true base)
# ---------------------------------------------------------------------------

def test_flag_off_prose_is_unchanged_on_mismatch(reconcile_off):
    """Flag-OFF equivalence guard. NOTE: the issue transcribed the 593ec1e
    behavior (GPT prose survives intact); #99 merged since and reconciles
    name/declaration/loser-naming-prose UNFLAGGED, so THIS is the base."""
    resp = _mismatch_response()
    w = resp["overview"]["winner"]
    assert w["product_index"] == 1
    # #99: name field = deterministic winner's name, declaration dropped.
    assert w["name"] == "Galaxy S24"
    assert w["declaration"] == ""
    # #99: GPT reason names the loser (iPhone 15) -> generic fallback.
    assert w["reason"] == "Galaxy S24 is the stronger overall pick."
    # #99 residual defect (what #110 fixes): GPT's key_tradeoff frames the
    # SHIPPED WINNER as the staying-competitive loser, and survives because
    # it never names the loser.
    assert w["key_tradeoff"] == "Galaxy S24 offers more RAM."
    # #99: BC alias index already deterministic.
    assert resp["comparison"]["winner_index"] == 1
    assert resp["recommendation"] == w["reason"]


# ---------------------------------------------------------------------------
# 2-5. Flag ON — mismatch: deterministic template overwrites (RED first)
# ---------------------------------------------------------------------------

def test_winner_name_matches_winner_index_on_mismatch(reconcile_on):
    resp = _mismatch_response()
    w = resp["overview"]["winner"]
    # General invariant: winner.name IS the product at winner.product_index.
    assert w["name"] == ["iPhone 15", "Galaxy S24"][w["product_index"]]
    assert w["name"] == "Galaxy S24"
    # RED at HEAD: #99 drops the declaration to ""; the #110 template ships
    # the winner's name as the declaration.
    assert w["declaration"] == "Galaxy S24"


def test_winner_reason_replaced_on_mismatch(reconcile_on):
    resp = _mismatch_response()
    reason = resp["overview"]["winner"]["reason"]
    assert "iPhone 15" not in reason
    # RED at HEAD: #99 ships the generic "is the stronger overall pick."
    # fallback; #110 ships the deterministic template (both overalls numeric).
    assert reason == "Galaxy S24 edges ahead on the overall picture."


def test_reason_replaced_even_without_loser_name(reconcile_on):
    """The design point #99's containment check cannot cover: GPT prose about
    ITS OWN pick that never names either product survives #99 verbatim.
    Under #110 the prose is REPLACED on mismatch, not name-filtered."""
    comparison = _comparison_naming(0)
    comparison["winner_reason"] = "The camera and chipset are simply stronger."
    resp = _mismatch_response(comparison=comparison)
    assert (
        resp["overview"]["winner"]["reason"]
        == "Galaxy S24 edges ahead on the overall picture."
    )


def test_key_tradeoff_replaced_on_mismatch(reconcile_on):
    resp = _mismatch_response()
    # RED at HEAD: ships "Galaxy S24 offers more RAM." (names the winner).
    assert (
        resp["overview"]["winner"]["key_tradeoff"]
        == "iPhone 15 stays competitive on price."
    )
    # Companion: no tradeoff derivable -> "" (today's GPT-omitted value),
    # never a fabricated sentence.
    resp_empty = _mismatch_response(tradeoffs=[])
    assert resp_empty["overview"]["winner"]["key_tradeoff"] == ""


def test_recommendation_alias_matches_reconciled_reason(reconcile_on):
    resp = _mismatch_response()
    assert resp["recommendation"] == resp["overview"]["winner"]["reason"]
    assert resp["comparison"]["winner_reason"] == resp["recommendation"]
    assert resp["comparison"]["winner_index"] == resp["winner_index"] == 1


# ---------------------------------------------------------------------------
# 6-8. Flag ON — pins (must be GREEN before AND after)
# ---------------------------------------------------------------------------

def test_no_change_when_indices_agree(reconcile_on):
    """The common path: indices agree -> GPT prose ships untouched."""
    resp = _mismatch_response(comparison=_comparison_naming(1))
    w = resp["overview"]["winner"]
    assert w["product_index"] == 1
    assert w["name"] == "Galaxy S24 wins"
    assert w["declaration"] == "Galaxy S24 wins"
    assert w["reason"] == "Galaxy S24 has the stronger camera."
    assert w["key_tradeoff"] == "iPhone 15 offers more RAM."


def test_scoring_winner_none_leaves_gpt_untouched(reconcile_on):
    """Legacy fixtures / scoring-disabled: no deterministic winner -> GPT's
    index and prose both stand (the else branch of the H1 override)."""
    resp = _mismatch_response(scoring_result={"scores": {}})
    w = resp["overview"]["winner"]
    assert resp["winner_index"] == 0
    assert w["product_index"] == 0
    assert w["name"] == "iPhone 15 wins"
    assert w["declaration"] == "iPhone 15 wins"
    assert w["reason"] == "iPhone 15 has the stronger camera."
    assert w["key_tradeoff"] == "Galaxy S24 offers more RAM."


def test_reconciled_prose_carries_no_score_internals(reconcile_on):
    """Constrains the NEW template family — the deterministic partial verdict
    leaked a score once before (see the margin comment in
    _deterministic_partial_verdict)."""
    resp = _mismatch_response()
    assert has_score_internals(resp["overview"]["winner"]["reason"]) is False
    assert has_score_internals(resp["overview"]["winner"]["key_tradeoff"]) is False


# ---------------------------------------------------------------------------
# Harness (SSE path) — copied from tests/test_streaming.py
# ---------------------------------------------------------------------------

def _sse_product_data():
    return [
        {
            "brand": "Apple", "name": "iPhone 15", "full_name": "Apple iPhone 15",
            "variant": "128GB", "category": "electronics", "query": "Apple iPhone 15",
            "specs": {"ram": "6GB", "storage": "128GB"},
            "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon", "url": None, "estimated": False},
            "best_price": 299, "currency": "BHD", "retailer": "Amazon",
            "reviews": {
                "average_rating": 4.5, "total_reviews": 1200,
                "review_summary": {
                    "overall_sentiment": "positive",
                    "consensus": "Great phone overall with excellent camera.",
                    "highlights": [{"point": "Excellent camera", "sentiment": "positive"}],
                    "review_volume": "high", "agreement_level": "strong",
                },
            },
            "rating": 4.5, "review_count": 1200, "rating_verified": True,
            "rating_source": {"name": "Amazon", "url": None},
            "fact_check": {"overall_confidence": "high"},
            "data_freshness": "fresh",
        },
        {
            "brand": "Samsung", "name": "Galaxy S24", "full_name": "Samsung Galaxy S24",
            "variant": "128GB", "category": "electronics", "query": "Samsung Galaxy S24",
            "specs": {"ram": "8GB", "storage": "128GB"},
            "price": {"amount": 279, "currency": "BHD", "retailer": "Noon", "url": None, "estimated": False},
            "best_price": 279, "currency": "BHD", "retailer": "Noon",
            "reviews": {
                "average_rating": 4.3, "total_reviews": 800,
                "review_summary": {
                    "overall_sentiment": "positive",
                    "consensus": "Good Android phone with great display.",
                    "highlights": [{"point": "Great display", "sentiment": "positive"}],
                    "review_volume": "high", "agreement_level": "moderate",
                },
            },
            "rating": 4.3, "review_count": 800, "rating_verified": True,
            "rating_source": {"name": "Noon", "url": None},
            "fact_check": {"overall_confidence": "medium"},
            "data_freshness": "fresh",
        },
    ]


def _sse_comparison():
    return {
        "winner_index": 0,
        "winner_declaration": "Apple iPhone 15",
        "winner_reason": "Stronger camera and faster chip at similar price",
        "key_tradeoff": "Galaxy S24 has more RAM and better value",
        "value_context": "Both products are mid-range flagships with competitive pricing",
        "best_for": {
            "product_0": "Best if you prioritize camera quality",
            "product_1": "Best if you want more RAM and better value",
        },
        "product_0_pros": ["Great camera", "Long battery"],
        "product_0_cons": ["Higher price"],
        "product_1_pros": ["Better value", "More RAM"],
        "product_1_cons": ["Shorter updates"],
        "specs_comparison": {
            "product_0_advantages": ["Better camera"],
            "product_1_advantages": ["More RAM"],
            "similar": ["Storage"],
        },
    }


def _sse_scoring_result(winner_index=0):
    return {
        "scores": {
            "product_0": {"overall": 78, "breakdown": {"price_score": 70, "spec_score": 80, "value_score": 65}},
            "product_1": {"overall": 72, "breakdown": {"price_score": 85, "spec_score": 65, "value_score": 58}},
        },
        "winner_index": winner_index,
        "win_margin": 6,
        "scoring_method": "category_weighted",
        "dimension_winners": {
            "price_score": {"winner": "Samsung Galaxy S24", "margin": 15.0},
            "spec_score": {"winner": "Apple iPhone 15", "margin": 15.0},
        },
        "price_tiers": {"iPhone 15": "mid", "Galaxy S24": "mid"},
        "is_cross_tier": False,
        "category_weights": {"price_score": 0.2, "spec_score": 0.25},
    }


def _setup_scoring_mock(scoring_svc, mock_scoring_result):
    scoring_svc.compute_scores.return_value = mock_scoring_result
    scoring_svc.build_scores_summary.return_value = "summary"
    scoring_svc.compute_value_badge.return_value = "fair_price"
    scoring_svc.compute_tradeoff_pairs.return_value = []
    scoring_svc.compute_confidence.return_value = {
        "price": {"source_count": 2, "method": "retailer_verified", "freshness": "live"},
        "rating": {"review_count": 1200, "source": "Amazon", "verified": True},
        "specs": {"verified_pct": 80, "citation_count": 10},
        "overall": "high",
    }


async def _run_streaming_events(scoring_result):
    """Run compare_from_text_streaming with the test_streaming harness and a
    forced scoring winner; return {event_type: data} (last event of each type).
    Copied from test_streaming.py::test_verdict_event_has_structured_winner."""
    from app.services.structured_comparison_service import StructuredComparisonService

    service = StructuredComparisonService()
    with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
         patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
         patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
         patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

        mock_parse.return_value = ({
            "products": [
                {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
            ],
            "comparison_type": "value",
        }, {"prompt_tokens": 0, "completion_tokens": 0})
        mock_fetch.side_effect = _sse_product_data()
        mock_gen.return_value = (_sse_comparison(), {"prompt_tokens": 0, "completion_tokens": 0})
        scoring_svc = MagicMock()
        _setup_scoring_mock(scoring_svc, scoring_result)
        mock_scoring.return_value = scoring_svc

        events = {}
        async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
            events[event_type] = data
        return events


# ---------------------------------------------------------------------------
# 9-11. SSE verdict event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse_verdict_event_uses_deterministic_winner_index(reconcile_on):
    """RED at HEAD: the verdict emit reads GPT's comparison["winner_index"]
    (0) even though scoring_result (winner 1) is in scope four lines up."""
    events = await _run_streaming_events(_sse_scoring_result(winner_index=1))
    verdict = events["verdict"]
    assert verdict["winner"]["product_index"] == 1
    # Streaming product_names are "{brand} {name}" — the deterministic
    # template's declaration IS the winner's name.
    assert verdict["winner"]["name"] == "Samsung Galaxy S24"


@pytest.mark.asyncio
async def test_sse_verdict_and_complete_agree_on_winner(reconcile_on):
    """The mid-stream-flip regression pin: the winner must never flip between
    the verdict event and the complete event of one run."""
    events = await _run_streaming_events(_sse_scoring_result(winner_index=1))
    assert (
        events["verdict"]["winner"]["product_index"]
        == events["complete"]["overview"]["winner"]["product_index"]
    )


@pytest.mark.asyncio
async def test_sse_flag_off_verdict_event_unchanged(reconcile_off):
    """Flag OFF: the verdict event still carries GPT's index and declaration,
    byte-identical to base (the flip stands, as it does today)."""
    events = await _run_streaming_events(_sse_scoring_result(winner_index=1))
    verdict = events["verdict"]
    assert verdict["winner"]["product_index"] == 0
    assert verdict["winner"]["name"] == "Apple iPhone 15"

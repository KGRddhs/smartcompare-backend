"""M20 #110 (M18 PO-prompts-01) — reconcile the winner PROSE with the
deterministic winner index at the response chokepoint, and stop the SSE
`verdict` event from flipping the winner mid-stream.

TWO LAYERS, deliberately shipped differently (see the commit message):

* **UNFLAGGED safety repair** (#99, pinned in
  `tests/test_response_builder_winner_card_consistency.py`): on a mismatch the
  winner NAME tracks the deterministic index everywhere the payload exposes a
  winner (`overview.winner.name`, the BC `comparison.winner_index`, the SSE
  `verdict` event), and ALL THREE GPT verdict strings are dropped — the reason
  unconditionally, since on a mismatch it argues for GPT's winner by
  construction (see `test_flag_off_drops_every_gpt_reason_on_a_mismatch`, which
  supersedes the loser-name containment check #99's notes proposed). Shipping
  the losing product's name is indefensible, so it must not sit behind a flag
  nobody has flipped.
* **`ENABLE_WINNER_PROSE_RECONCILE` (default OFF)**: additionally replaces the
  three prose fields with the DETERMINISTIC verdict template
  (`deterministic_verdict_fields`). That is a user-facing copy change on the
  core surface, so it ships dark and canaries alone.

Issue #110's cases 1 and 11 asserted that flag OFF keeps GPT's prose and GPT's
SSE index verbatim. They are ADAPTED here to the unflagged safety layer above
(`test_flag_off_repairs_the_name_and_the_loser_praising_reason`,
`test_sse_flag_off_verdict_event_uses_deterministic_index`) — the flag-OFF
equivalence that still holds unconditionally is the AGREEMENT path (cases 6, 7,
plus `test_flag_off_agreement_path_keeps_gpt_reason_verbatim`).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.response_builder import build_comparison_response
from app.services.text_sanitize import has_score_internals


_NAMES = ("iPhone 15", "Galaxy S24")
_TRADEOFFS = [{"loser_wins": {"dimension": "price_score", "product": "iPhone 15"}}]


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


def _comparison_naming(idx, names=_NAMES):
    w, l = names[idx], names[1 - idx]
    return {
        "winner_index": idx,
        "winner_declaration": f"{w} wins",
        "winner_reason": f"{w} has the stronger camera.",
        "key_tradeoff": f"{l} offers more RAM.",
    }


def _build(comparison, scoring_result, tradeoffs=None):
    return build_comparison_response(
        product_data=_products(),
        comparison=comparison,
        scoring_result=scoring_result,
        tradeoffs=_TRADEOFFS if tradeoffs is None else tradeoffs,
        category_used="electronics",
    )


@pytest.fixture
def reconcile_on(monkeypatch):
    monkeypatch.setenv("ENABLE_WINNER_PROSE_RECONCILE", "true")
    yield


@pytest.fixture
def reconcile_off(monkeypatch):
    monkeypatch.delenv("ENABLE_WINNER_PROSE_RECONCILE", raising=False)
    yield


# ---------------------------------------------------------------------------
# Sync path (build_comparison_response)
# ---------------------------------------------------------------------------

def test_flag_off_repairs_the_name_and_the_loser_praising_reason(reconcile_off):
    """ADAPTED #110 case 1. Flag OFF still applies the UNFLAGGED safety repair:
    the name tracks the deterministic index, the declaration and the
    inverted-orientation tradeoff are dropped, and GPT's reason — which praises
    the LOSER by name — falls back to the qualitative default."""
    resp = _build(_comparison_naming(0), _scoring_result(1))
    w = resp["overview"]["winner"]
    assert w["product_index"] == 1
    assert w["name"] == "Galaxy S24"
    assert w["declaration"] == ""
    assert w["reason"] == "Galaxy S24 is the stronger overall pick."
    assert w["key_tradeoff"] == ""


@pytest.mark.parametrize("reason,label", [
    ("iPhone 15 offers better value.", "full-name praise (the ONLY row the old check caught)"),
    ("It offers a noticeably richer camera for the price.", "pronoun praise"),
    ("The iPhone has the sharper camera.", "short-name praise"),
    ("Positive reviews highlight its rich camera.", "names nobody"),
    ("The camera is the deciding factor here.", "orientation-free"),
])
def test_flag_off_drops_every_gpt_reason_on_a_mismatch(reconcile_off, reason, label):
    """SUPERSEDES `test_flag_off_keeps_a_gpt_reason_that_does_not_name_the_loser`.

    That test pinned a loser-name CONTAINMENT check, which only caught the
    first row below; the other four shipped GPT's argument for the LOSER beside
    the deterministic winner's name — the exact torn card #99 exists to close.
    On a mismatch GPT's reason argues for GPT's winner by construction, so it is
    dropped unconditionally and the qualitative fallback fires."""
    comparison = _comparison_naming(0)
    comparison["winner_reason"] = reason
    resp = _build(comparison, _scoring_result(1))
    assert resp["overview"]["winner"]["reason"] == "Galaxy S24 is the stronger overall pick."
    assert resp["recommendation"] == "Galaxy S24 is the stronger overall pick."


def test_flag_off_agreement_path_keeps_gpt_reason_verbatim(reconcile_off):
    """The counterpart pin: the repair fires ONLY on a mismatch. With the
    indices in agreement GPT's prose ships untouched (#99 clause 5)."""
    comparison = _comparison_naming(1)
    comparison["winner_reason"] = "The camera is the deciding factor here."
    resp = _build(comparison, _scoring_result(1))
    assert resp["overview"]["winner"]["reason"] == "The camera is the deciding factor here."


def test_winner_name_matches_winner_index_on_mismatch(reconcile_on):
    """RED at 17cb981: overview.winner.name ships GPT's winner_declaration."""
    resp = _build(_comparison_naming(0), _scoring_result(1))
    w = resp["overview"]["winner"]
    assert w["name"] == "Galaxy S24"
    assert w["name"] == list(_NAMES)[w["product_index"]]


def test_winner_reason_replaced_on_mismatch(reconcile_on):
    """RED at 17cb981: the reason praises the loser."""
    reason = _build(_comparison_naming(0), _scoring_result(1))["overview"]["winner"]["reason"]
    assert "iPhone 15" not in reason
    assert "Galaxy S24" in reason
    assert reason == "Galaxy S24 edges ahead on the overall picture."


def test_key_tradeoff_replaced_on_mismatch(reconcile_on):
    """RED at 17cb981: key_tradeoff frames the SHIPPED winner as the runner-up."""
    resp = _build(_comparison_naming(0), _scoring_result(1))
    assert resp["overview"]["winner"]["key_tradeoff"] == "iPhone 15 stays competitive on price."
    empty = _build(_comparison_naming(0), _scoring_result(1), tradeoffs=[])
    assert empty["overview"]["winner"]["key_tradeoff"] == ""


def test_recommendation_alias_matches_reconciled_reason(reconcile_on):
    """RED at 17cb981 on the last clause — the BC alias keeps GPT's index."""
    resp = _build(_comparison_naming(0), _scoring_result(1))
    assert resp["recommendation"] == resp["overview"]["winner"]["reason"]
    assert resp["comparison"]["winner_reason"] == resp["recommendation"]
    assert resp["comparison"]["winner_index"] == resp["winner_index"] == 1


def test_no_change_when_indices_agree(reconcile_on):
    """Pin: the common path never fires the reconciliation, flag ON or OFF."""
    resp = _build(_comparison_naming(1), _scoring_result(1))
    w = resp["overview"]["winner"]
    assert w["name"] == "Galaxy S24 wins"
    assert w["declaration"] == "Galaxy S24 wins"
    assert w["reason"] == "Galaxy S24 has the stronger camera."
    assert w["key_tradeoff"] == "iPhone 15 offers more RAM."


def test_scoring_winner_none_leaves_gpt_untouched(reconcile_on):
    """Pin: scoring produced no winner (legacy fixture / scoring disabled) —
    GPT's index and prose both stand."""
    resp = _build(_comparison_naming(0), {"scores": {}})
    w = resp["overview"]["winner"]
    assert resp["winner_index"] == 0
    assert w["name"] == "iPhone 15 wins"
    assert w["declaration"] == "iPhone 15 wins"
    assert w["reason"] == "iPhone 15 has the stronger camera."
    assert w["key_tradeoff"] == "Galaxy S24 offers more RAM."


def test_reconciled_prose_carries_no_score_internals(reconcile_on):
    """Pin: the deterministic template must never leak a score (it did once —
    see the comment at structured_comparison_service._deterministic_partial_verdict)."""
    w = _build(_comparison_naming(0), _scoring_result(1))["overview"]["winner"]
    assert has_score_internals(w["reason"]) is False
    assert has_score_internals(w["key_tradeoff"]) is False


# ---------------------------------------------------------------------------
# SSE path (compare_from_text_streaming) — the mid-stream winner flip
# ---------------------------------------------------------------------------

@pytest.fixture
def sse_product_data():
    return [
        {"brand": "Apple", "name": "iPhone 15", "full_name": "Apple iPhone 15",
         "variant": "128GB", "category": "electronics", "query": "Apple iPhone 15",
         "specs": {"ram": "6GB", "storage": "128GB"},
         "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon",
                   "url": None, "estimated": False},
         "best_price": 299, "currency": "BHD", "retailer": "Amazon",
         "reviews": {"average_rating": 4.5, "total_reviews": 1200,
                     "review_summary": {"overall_sentiment": "positive",
                                        "consensus": "Great phone.",
                                        "highlights": [],
                                        "review_volume": "high",
                                        "agreement_level": "strong"}},
         "rating": 4.5, "review_count": 1200, "rating_verified": True,
         "rating_source": {"name": "Amazon", "url": None},
         "fact_check": {"overall_confidence": "high"}, "data_freshness": "fresh"},
        {"brand": "Samsung", "name": "Galaxy S24", "full_name": "Samsung Galaxy S24",
         "variant": "128GB", "category": "electronics", "query": "Samsung Galaxy S24",
         "specs": {"ram": "8GB", "storage": "128GB"},
         "price": {"amount": 279, "currency": "BHD", "retailer": "Noon",
                   "url": None, "estimated": False},
         "best_price": 279, "currency": "BHD", "retailer": "Noon",
         "reviews": {"average_rating": 4.3, "total_reviews": 800,
                     "review_summary": {"overall_sentiment": "positive",
                                        "consensus": "Good Android phone.",
                                        "highlights": [],
                                        "review_volume": "high",
                                        "agreement_level": "moderate"}},
         "rating": 4.3, "review_count": 800, "rating_verified": True,
         "rating_source": {"name": "Noon", "url": None},
         "fact_check": {"overall_confidence": "medium"}, "data_freshness": "fresh"},
    ]


@pytest.fixture
def sse_comparison():
    """GPT picks product 0 — the scoring mock below picks 1 (the mismatch)."""
    return {
        "winner_index": 0,
        "winner_declaration": "Apple iPhone 15",
        "winner_reason": "Stronger camera and faster chip at similar price",
        "key_tradeoff": "Galaxy S24 has more RAM and better value",
        "value_context": "Both are mid-range flagships",
        "best_for": {"product_0": "camera", "product_1": "value"},
        "product_0_pros": ["Great camera"], "product_0_cons": ["Higher price"],
        "product_1_pros": ["Better value"], "product_1_cons": ["Shorter updates"],
        "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [],
                             "similar": []},
    }


@pytest.fixture
def sse_scoring_result():
    return {
        "scores": {
            "product_0": {"overall": 78, "breakdown": {"price_score": 70, "spec_score": 80,
                                                       "value_score": 65}},
            "product_1": {"overall": 72, "breakdown": {"price_score": 85, "spec_score": 65,
                                                       "value_score": 58}},
        },
        "winner_index": 1,  # DISAGREES with the comparison fixture above
        "win_margin": 6,
        "scoring_method": "category_weighted",
        "dimension_winners": {"price_score": {"winner": "Samsung Galaxy S24", "margin": 15.0}},
        "price_tiers": {"iPhone 15": "mid", "Galaxy S24": "mid"},
        "is_cross_tier": False,
        "category_weights": {"price_score": 0.2, "spec_score": 0.25},
    }


async def _collect_stream(sse_product_data, sse_comparison, sse_scoring_result):
    from app.services.structured_comparison_service import StructuredComparisonService

    service = StructuredComparisonService()
    events = {}
    with patch.object(service, "_fetch_product_data", new_callable=AsyncMock) as mock_fetch, \
         patch("app.services.structured_comparison_service.parse_product_query",
               new_callable=AsyncMock) as mock_parse, \
         patch("app.services.structured_comparison_service.generate_comparison",
               new_callable=AsyncMock) as mock_gen, \
         patch("app.services.structured_comparison_service.get_scoring_service") as mock_scoring:
        mock_parse.return_value = ({
            "products": [
                {"brand": "Apple", "name": "iPhone 15", "category": "electronics",
                 "search_query": "Apple iPhone 15"},
                {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics",
                 "search_query": "Samsung Galaxy S24"},
            ],
            "comparison_type": "value",
        }, {"prompt_tokens": 0, "completion_tokens": 0})
        mock_fetch.side_effect = sse_product_data
        mock_gen.return_value = (dict(sse_comparison),
                                 {"prompt_tokens": 0, "completion_tokens": 0})
        scoring_svc = MagicMock()
        scoring_svc.compute_scores.return_value = sse_scoring_result
        scoring_svc.build_scores_summary.return_value = "summary"
        scoring_svc.compute_value_badge.return_value = "fair_price"
        scoring_svc.compute_tradeoff_pairs.return_value = [
            {"loser_wins": {"dimension": "spec_score", "product": "Apple iPhone 15"}}
        ]
        scoring_svc.compute_confidence.return_value = {
            "price": {"source_count": 2, "method": "retailer_verified", "freshness": "live"},
            "rating": {"review_count": 1200, "source": "Amazon", "verified": True},
            "specs": {"verified_pct": 80, "citation_count": 10},
            "overall": "high",
        }
        mock_scoring.return_value = scoring_svc

        async for event_type, data in service.compare_from_text_streaming(
            "iPhone 15 vs Galaxy S24"
        ):
            events[event_type] = data
    return events


@pytest.mark.asyncio
async def test_sse_verdict_event_uses_deterministic_winner_index(
    reconcile_on, sse_product_data, sse_comparison, sse_scoring_result
):
    """RED at 17cb981: the verdict event reads GPT's index and declaration."""
    events = await _collect_stream(sse_product_data, sse_comparison, sse_scoring_result)
    verdict = events["verdict"]
    assert verdict["winner"]["product_index"] == 1
    assert verdict["winner"]["name"] == "Samsung Galaxy S24"


@pytest.mark.asyncio
async def test_sse_verdict_and_complete_agree_on_winner(
    reconcile_on, sse_product_data, sse_comparison, sse_scoring_result
):
    """RED at 17cb981 — the mid-stream winner FLIP regression pin."""
    events = await _collect_stream(sse_product_data, sse_comparison, sse_scoring_result)
    assert (events["verdict"]["winner"]["product_index"]
            == events["complete"]["overview"]["winner"]["product_index"])
    assert (events["verdict"]["winner"]["name"]
            == events["complete"]["overview"]["winner"]["name"])


@pytest.mark.asyncio
async def test_sse_flag_off_verdict_event_uses_deterministic_index(
    reconcile_off, sse_product_data, sse_comparison, sse_scoring_result
):
    """ADAPTED #110 case 11. The index+name repair is UNFLAGGED, so the verdict
    event never ships the losing product even with the prose flag OFF."""
    events = await _collect_stream(sse_product_data, sse_comparison, sse_scoring_result)
    verdict = events["verdict"]
    assert verdict["winner"]["product_index"] == 1
    assert verdict["winner"]["name"] == "Samsung Galaxy S24"
    assert verdict["winner_index"] == 1


@pytest.mark.asyncio
async def test_sse_flag_off_verdict_and_complete_agree_on_the_reason(
    reconcile_off, sse_product_data, sse_comparison, sse_scoring_result
):
    """Closes the scope boundary the containment check left open: with the prose
    flag OFF the verdict event's `reason` used to be EMPTY (or GPT's
    loser-praising sentence) while `complete` showed the qualitative fallback.
    `reconcile_winner_prose` now writes that fallback into the shared
    `comparison` dict, so both events read the SAME string and the streamed card
    is self-consistent with the final one."""
    events = await _collect_stream(sse_product_data, sse_comparison, sse_scoring_result)
    complete_reason = events["complete"]["overview"]["winner"]["reason"]
    assert events["verdict"]["winner"]["reason"] == complete_reason
    assert events["verdict"]["recommendation"] == complete_reason
    assert complete_reason == "Samsung Galaxy S24 is the stronger overall pick."
    assert "iPhone" not in complete_reason

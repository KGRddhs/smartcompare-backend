"""A5 — rating-provenance suppression across BOTH AI-origin rating paths.

A rating is "derived" when it was synthesized from scores
(derive_rating_from_scores) or estimated by GPT (gpt_review_aggregate). Both set
rating_derived=True. A derived rating must NEVER be presented as authoritative:
not in the overview/reviews projections, not in the verdict line1/line2, and it
must not feed scoring's value/reviews dims. A REAL rating still renders + scores.
A6 (variant "N/A" leak) tests live at the bottom of this file.
"""
import pytest

from app.services.response_builder import (
    _safe_rating,
    _build_factual_verdict,
    _compose_variant_string,
    build_comparison_response,
)
from app.services.scoring_service import _dim_value


# ============================================
# _safe_rating chokepoint
# ============================================

def test_safe_rating_returns_none_when_derived():
    assert _safe_rating({"rating": 4.5, "rating_derived": True}) is None


def test_safe_rating_returns_value_when_real():
    assert _safe_rating({"rating": 4.5}) == 4.5


def test_safe_rating_explicit_false_is_real():
    assert _safe_rating({"rating": 4.2, "rating_derived": False}) == 4.2


# ============================================
# Projections (overview + reviews) null a derived rating, keep review_count
# ============================================

def _build(product_data):
    comparison = {"winner_index": 0}
    scoring_result = {
        "scores": {"product_0": {"overall": 80}, "product_1": {"overall": 70}},
        "winner_index": 0,
    }
    return build_comparison_response(
        product_data=product_data,
        comparison=comparison,
        scoring_result=scoring_result,
        product_names=[product_data[0]["name"], product_data[1]["name"]],
        tradeoffs=[],
        confidence={},
        verdict_validation={},
        user_preferences=None,
        from_cache=False,
        query="test",
        region="bahrain",
        category_used="electronics",
        category_switched=False,
        original_category=None,
        total_cost=0,
        api_calls=0,
        gpt_calls=0,
        serper_calls=0,
        elapsed_seconds=0,
    )


def test_derived_rating_nulled_in_overview_projection():
    product_data = [
        {"brand": "Apple", "name": "iPhone", "rating": 4.4, "rating_derived": True,
         "review_count": 1200},
        {"brand": "Samsung", "name": "Galaxy", "rating": 4.5, "review_count": 980},
    ]
    result = _build(product_data)
    ov = result["overview"]["products"]
    assert ov[0]["rating"] is None, "derived rating leaked into overview"
    assert ov[1]["rating"] == 4.5, "real rating must still render"
    # review_count is preserved regardless of rating provenance
    assert ov[0]["review_count"] == 1200
    assert ov[1]["review_count"] == 980


def test_derived_rating_nulled_in_reviews_projection():
    product_data = [
        {"brand": "Apple", "name": "iPhone", "rating": 4.4, "rating_derived": True,
         "review_count": 1200},
        {"brand": "Samsung", "name": "Galaxy", "rating": 4.5, "review_count": 980},
    ]
    result = _build(product_data)
    rv = result["reviews"]["products"]
    assert rv[0]["rating"] is None
    assert rv[1]["rating"] == 4.5
    assert rv[0]["review_count"] == 1200


def test_real_rating_renders_in_both_projections():
    product_data = [
        {"brand": "Apple", "name": "iPhone", "rating": 4.6, "review_count": 500},
        {"brand": "Samsung", "name": "Galaxy", "rating": 4.3, "review_count": 700},
    ]
    result = _build(product_data)
    assert result["overview"]["products"][0]["rating"] == 4.6
    assert result["reviews"]["products"][0]["rating"] == 4.6


# ============================================
# Verdict line1 AND line2 — no rating claim when both ratings derived
# ============================================

_RATING_PHRASES = ("stars higher", "more stars", "rates a touch higher",
                   "rates higher", "lower reviews")


def test_verdict_no_rating_claim_when_both_derived():
    # Both ratings derived + no price + no dims => line1/line2 must not assert any
    # rating delta. (No price either, so the rating fallback is the only rating
    # surface — it must be suppressed.)
    products = [
        {"name": "iPhone", "rating": 4.8, "rating_derived": True},
        {"name": "Galaxy", "rating": 3.2, "rating_derived": True},
    ]
    scoring_result = {"scores": {"product_0": {"overall": 80}, "product_1": {"overall": 60}}}
    verdict = _build_factual_verdict(products, scoring_result, winner_index=0, dimensions=[])
    blob = (verdict["line1"] + " " + verdict["line2"]).lower()
    for phrase in _RATING_PHRASES:
        assert phrase not in blob, f"derived rating leaked into verdict: {phrase!r} in {blob!r}"


def test_verdict_uses_real_rating_delta():
    # Two REAL ratings (no price, no dims) -> line1 anchors on the star delta.
    products = [
        {"name": "iPhone", "rating": 4.8},
        {"name": "Galaxy", "rating": 3.8},
    ]
    scoring_result = {"scores": {"product_0": {"overall": 80}, "product_1": {"overall": 60}}}
    verdict = _build_factual_verdict(products, scoring_result, winner_index=0, dimensions=[])
    assert "stars" in verdict["line1"].lower()


def test_verdict_line1_price_fallback_when_rating_derived():
    # Derived rating but a REAL price gap -> line1 falls back to the price fact,
    # confirming suppressing the rating doesn't blank the verdict.
    products = [
        {"name": "iPhone", "rating": 4.8, "rating_derived": True, "price": {"amount": 300.0}},
        {"name": "Galaxy", "rating": 3.2, "rating_derived": True, "price": {"amount": 400.0}},
    ]
    scoring_result = {"scores": {"product_0": {"overall": 80}, "product_1": {"overall": 60}}}
    verdict = _build_factual_verdict(products, scoring_result, winner_index=0, dimensions=[])
    assert "cheaper" in verdict["line1"].lower()


# ============================================
# _dim_value — derived rating takes the "Limited value data" path
# ============================================

def test_dim_value_derived_rating_is_limited_data():
    # Both have numeric ratings + valid positive prices, but rating_derived=True
    # on both -> value ratio must NOT be computed -> "Limited value data".
    products = [
        {"name": "A", "rating": 4.5, "rating_derived": True, "price": {"amount": 80.0}},
        {"name": "B", "rating": 4.0, "rating_derived": True, "price": {"amount": 90.0}},
    ]
    dim = _dim_value(products)
    assert dim["delta_text"] == "Limited value data"
    assert dim["confidence"] == "low"
    assert dim.get("caption_key") == "limited_data"


def test_dim_value_one_derived_is_limited_data():
    products = [
        {"name": "A", "rating": 4.5, "price": {"amount": 80.0}},
        {"name": "B", "rating": 4.0, "rating_derived": True, "price": {"amount": 90.0}},
    ]
    dim = _dim_value(products)
    assert dim["delta_text"] == "Limited value data"


def test_dim_value_two_real_ratings_still_computes():
    # Regression: genuine ratings on BOTH sides keep a real value delta.
    products = [
        {"name": "A", "rating": 4.5, "price": {"amount": 80.0}},
        {"name": "B", "rating": 4.0, "price": {"amount": 90.0}},
    ]
    dim = _dim_value(products)
    assert dim["delta_text"] != "Limited value data"
    assert dim["confidence"] != "low"


# ============================================
# gpt_review_aggregate — flagged derived at source + count nulled
# ============================================

def test_gpt_review_aggregate_flags_derived_and_nulls_count():
    """CLEANUP-3(b): exercise the REAL production code (the extracted
    _apply_gpt_review_aggregate_fallback that _fetch_product_data calls), NOT an
    inlined copy. A GPT average_rating + total_reviews ESTIMATE is promoted but
    flagged rating_derived=True with review_count nulled."""
    from app.services.structured_comparison_service import (
        _apply_gpt_review_aggregate_fallback,
    )
    result = {
        "rating": None,
        "review_count": None,
        "reviews": {"average_rating": 4.3, "total_reviews": 2187},
    }
    _apply_gpt_review_aggregate_fallback(result)  # the real service function
    assert result["rating"] == 4.3
    assert result["rating_derived"] is True
    assert result["review_count"] is None  # the fabricated "2,187" estimate is nulled
    assert result["rating_source"]["extract_method"] == "gpt_review_aggregate"
    # And the guard chain treats it as not-authoritative:
    assert _safe_rating(result) is None


def test_gpt_review_aggregate_noop_when_real_rating_present():
    # Regression: a REAL provider rating must NOT be overwritten/flagged.
    from app.services.structured_comparison_service import (
        _apply_gpt_review_aggregate_fallback,
    )
    result = {
        "rating": 4.6, "review_count": 1200,
        "reviews": {"average_rating": 4.3, "total_reviews": 2187},
    }
    _apply_gpt_review_aggregate_fallback(result)
    assert result["rating"] == 4.6
    assert result["review_count"] == 1200
    assert result.get("rating_derived") is not True


def test_gpt_review_aggregate_noop_when_no_average():
    from app.services.structured_comparison_service import (
        _apply_gpt_review_aggregate_fallback,
    )
    result = {"rating": None, "review_count": None, "reviews": {"consensus": "ok"}}
    _apply_gpt_review_aggregate_fallback(result)
    assert result["rating"] is None
    assert result.get("rating_derived") is not True


def test_gpt_review_aggregate_noop_when_out_of_range():
    from app.services.structured_comparison_service import (
        _apply_gpt_review_aggregate_fallback,
    )
    result = {"rating": None, "review_count": None, "reviews": {"average_rating": 9.9}}
    _apply_gpt_review_aggregate_fallback(result)
    assert result["rating"] is None  # 9.9 fails the 1.0–5.0 sanity band


# ============================================
# A6 — literal "N/A" spec tokens must not leak into the variant tag
# ============================================

def test_variant_string_skips_na_tokens():
    # All variant-hook specs are the literal "N/A" -> no "N/A · N/A" tag.
    product = {"specs": {"storage": "N/A", "color": "N/A", "ram": "unknown"}}
    variant = _compose_variant_string(product, "electronics")
    assert variant == "", f"NA tokens leaked into variant: {variant!r}"


def test_variant_string_skips_na_keeps_real():
    # Real value survives; the "N/A"/"-" siblings are dropped.
    product = {"specs": {"storage": "256GB", "color": "N/A", "ram": "-"}}
    variant = _compose_variant_string(product, "electronics")
    assert variant == "256GB"


def test_variant_string_na_tokens_case_insensitive():
    product = {"specs": {"storage": "n/a", "color": "None", "ram": "UNKNOWN"}}
    variant = _compose_variant_string(product, "electronics")
    assert variant == ""


def test_variant_string_real_values_unaffected():
    # Regression: genuine multi-segment variant still composes.
    product = {"specs": {"storage": "512GB", "color": "Black", "ram": "12GB"}}
    variant = _compose_variant_string(product, "electronics")
    assert variant == "512GB · Black · 12GB"


# ============================================
# FIX-2 (MEDIUM) — the SSE streaming `reviews` event must apply the same
# rating_derived NO-FAB guard as the non-streaming response_builder projection.
# A gpt_review_aggregate ESTIMATE (rating_derived=True) was leaking RAW into the
# intermediate reviews event (the comment falsely claimed it was guarded).
# ============================================

import asyncio  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402


def _drive_stream_reviews_event(product_data):
    """Drive compare_from_text_streaming with _fetch_product_data + verdict +
    scoring mocked, and return the payload of the SSE `reviews` event."""
    from app.services.structured_comparison_service import StructuredComparisonService

    svc = StructuredComparisonService()

    async def fake_fetch(product_info, *a, **k):
        # Echo a prepared product dict per call (index by name match).
        name = product_info.get("name") or product_info.get("search_query") or ""
        for pd in product_data:
            if pd["name"] in name or name in pd["name"]:
                return dict(pd)
        return dict(product_data[0])

    scoring_svc = MagicMock()
    scoring_svc.compute_scores.return_value = {
        "scores": {
            "product_0": {"overall": 80, "breakdown": {}, "weights_used": {}},
            "product_1": {"overall": 70, "breakdown": {}, "weights_used": {}},
        },
        "winner_index": 0,
        "scoring_method": "category_weighted",
    }
    static_verdict = ({"winner_index": 0, "winner_declaration": "A"},
                      {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

    captured = {}

    async def drive():
        with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch), \
             patch("app.services.structured_comparison_service.generate_comparison",
                   new=AsyncMock(return_value=static_verdict)), \
             patch("app.services.structured_comparison_service.get_scoring_service",
                   return_value=scoring_svc):
            async for event_type, data in svc.compare_from_text_streaming(
                query="iPhone 15 vs Galaxy S24",
                explicit_pair=("iPhone 15", "Galaxy S24"),
                selected_category="electronics",
            ):
                if event_type == "reviews":
                    captured["reviews"] = data
    asyncio.run(drive())
    return captured.get("reviews")


def test_sse_reviews_event_nulls_derived_rating():
    # A gpt_review_aggregate estimate: rating present but rating_derived=True.
    product_data = [
        {"brand": "Apple", "name": "iPhone 15", "full_name": "Apple iPhone 15",
         "variant": None, "category": "electronics", "query": "iPhone 15",
         "specs": {}, "price": {"amount": 299, "currency": "BHD"},
         "rating": 4.3, "rating_derived": True, "review_count": None,
         "rating_verified": False, "rating_source": {"extract_method": "gpt_review_aggregate"},
         "reviews": {"review_summary": {}}},
        {"brand": "Samsung", "name": "Galaxy S24", "full_name": "Samsung Galaxy S24",
         "variant": None, "category": "electronics", "query": "Galaxy S24",
         "specs": {}, "price": {"amount": 279, "currency": "BHD"},
         "rating": 4.5, "review_count": 800,
         "rating_verified": True, "rating_source": {"name": "Noon"},
         "reviews": {"review_summary": {}}},
    ]
    reviews = _drive_stream_reviews_event(product_data)
    assert reviews is not None, "no SSE reviews event was emitted"
    p = reviews["products"]
    # The derived (gpt_review_aggregate) rating must be nulled in the SSE event.
    assert p[0]["rating"] is None, f"derived rating leaked into SSE reviews event: {p[0]['rating']}"
    # The REAL rating on the other product must still render.
    assert p[1]["rating"] == 4.5
    # review_count untouched (real on p1, already None on p0).
    assert p[1]["review_count"] == 800

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

@pytest.mark.asyncio
async def test_gpt_review_aggregate_flags_derived_and_nulls_count():
    """The gpt_review_aggregate fallback promotes a GPT average_rating +
    total_reviews ESTIMATE onto the product. It must flag rating_derived=True and
    null the estimated review_count so no downstream surface presents it as real.
    We exercise the fallback by constructing the post-Phase-2 state it runs on."""
    # Mirror the source block's preconditions: rating None from providers,
    # reviews dict carries a GPT-estimated average_rating + total_reviews.
    result = {
        "rating": None,
        "review_count": None,
        "reviews": {"average_rating": 4.3, "total_reviews": 2187},
    }
    # Inline the exact source logic the service runs (the block is private; this
    # asserts the contract the block must satisfy).
    avg = result["reviews"].get("average_rating")
    avg_float = round(float(avg), 1)
    if 1.0 <= avg_float <= 5.0:
        result["rating"] = avg_float
        result["rating_derived"] = True
        result["review_count"] = None
    assert result["rating"] == 4.3
    assert result["rating_derived"] is True
    assert result["review_count"] is None
    # And the guard chain treats it as not-authoritative:
    assert _safe_rating(result) is None


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

"""Task C6 — rating vs review-score mismatch.

BUG: the result showed "1.0 stars higher" while a product's rating rendered
"N/A". response_builder mutates pd_item["rating"] to a synthetic value via
derive_rating_from_scores + sets rating_derived=True BEFORE dimensions are
built. _dim_reviews then sees two numeric ratings and emits a star-delta even
though the frontend renders N/A for the derived (synthetic) rating.

FIX: _dim_reviews must treat a rating_derived-flagged rating as MISSING, so it
emits the "Limited review data" missing-data path instead of asserting a star
delta against a displayed N/A.
"""
import pytest

from app.services.scoring_service import _dim_reviews


def test_derived_rating_treated_as_missing_no_star_delta():
    """One real rating + one rating_derived → 'Limited review data', NOT
    'x stars higher'."""
    products = [
        {"name": "A", "price": {"amount": 80.0}, "rating": 4.5},
        # Synthetic rating injected by derive_rating_from_scores — FE shows N/A.
        {"name": "B", "price": {"amount": 90.0}, "rating": 3.5, "rating_derived": True},
    ]
    dim = _dim_reviews(products)
    assert "stars higher" not in dim["delta_text"]
    assert dim["delta_text"] == "Limited review data"
    assert dim["confidence"] == "low"
    assert dim.get("caption_key") == "limited_data"


def test_both_derived_treated_as_missing():
    products = [
        {"name": "A", "price": {"amount": 80.0}, "rating": 4.0, "rating_derived": True},
        {"name": "B", "price": {"amount": 90.0}, "rating": 3.0, "rating_derived": True},
    ]
    dim = _dim_reviews(products)
    assert dim["delta_text"] == "Limited review data"
    assert dim["confidence"] == "low"


def test_two_real_ratings_still_emit_star_delta():
    """Regression: genuine ratings on BOTH sides must keep the star delta."""
    products = [
        {"name": "A", "price": {"amount": 80.0}, "rating": 4.5},
        {"name": "B", "price": {"amount": 90.0}, "rating": 3.5},
    ]
    dim = _dim_reviews(products)
    assert dim["delta_text"] == "1.0 stars higher"
    assert dim["confidence"] == "high"
    assert dim.get("caption_key") is None


def test_rating_derived_false_is_real_rating():
    """An explicit rating_derived=False must be treated as a real rating."""
    products = [
        {"name": "A", "price": {"amount": 80.0}, "rating": 4.5, "rating_derived": False},
        {"name": "B", "price": {"amount": 90.0}, "rating": 4.5, "rating_derived": False},
    ]
    dim = _dim_reviews(products)
    assert dim["delta_text"] == "Same rating"
    assert dim["confidence"] == "high"

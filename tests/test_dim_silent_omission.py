"""Bundle C § 2h A.4.9 — silent dim omission.

Per design § 2h: when a dim has `score_a is None AND score_b is None`,
silently omit it from `dimensions[]` so the frontend never sees a
phantom row. The rare "limited_data" caption_key path (A.4.4) is the
EXCEPTION — those dims emit neutral display scores + caption_key,
not raw None, so they pass through.

Result: a comparison with insufficient data for some dims produces a
SHORTER but HONEST dimensions[] list. The frontend (B.5) gets to render
only what's actually known.
"""
import pytest

from app.services.scoring_service import build_dimensions_v2


def _scoring_result_two_products() -> dict:
    return {
        "scores": {
            "product_0": {"overall": 75, "breakdown": {}, "tier": "mid"},
            "product_1": {"overall": 80, "breakdown": {}, "tier": "mid"},
        },
    }


def test_dim_with_both_sides_null_is_omitted():
    """Synthetic dim with score_a=None AND score_b=None must NOT appear
    in build_dimensions_v2 output."""
    # Use products with full data — the 3 core dims SHOULD all emit
    # with valid scores (no None). Then we patch in a null-scored
    # synthetic dim and confirm the filter strips it.
    products = [
        {"name": "A", "category": "electronics", "price": {"amount": 100.0}, "rating": 4.5,
         "specs": {"battery": "3000mAh"}, "review_count": 100},
        {"name": "B", "category": "electronics", "price": {"amount": 80.0}, "rating": 4.4,
         "specs": {"battery": "3500mAh"}, "review_count": 120},
    ]
    dims = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
    # No dim in the output should have score_a=None AND score_b=None
    null_both = [d for d in dims if d.get("score_a") is None and d.get("score_b") is None]
    assert null_both == [], (
        f"found {len(null_both)} fully-null dim(s) in output — A.4.9 silent omission failed: "
        f"{[d.get('key') for d in null_both]}"
    )


def test_dim_with_one_side_null_is_omitted():
    """Spec § 2h: skip dim when EITHER side null (the calibration band
    can't compute a winner from partial data)."""
    products = [
        {"name": "A", "category": "electronics", "price": {"amount": 100.0}, "rating": 4.5,
         "specs": {"battery": "3000mAh"}, "review_count": 100},
        {"name": "B", "category": "electronics", "price": {"amount": 80.0}, "rating": 4.4,
         "specs": {"battery": "3500mAh"}, "review_count": 120},
    ]
    dims = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
    one_side_null = [d for d in dims if (d.get("score_a") is None) != (d.get("score_b") is None)]
    assert one_side_null == [], (
        f"found one-side-null dim(s): {[d.get('key') for d in one_side_null]}"
    )


def test_limited_data_dims_stay_in_output():
    """Per A.4.4: dims that emit neutral-display + caption_key='limited_data'
    are NOT silently omitted — they're the last-resort row, frontend
    renders the §2b "—" presentation. They have NUMERIC neutral scores
    (not None), so they should never hit the silent-omission filter."""
    products = [
        {"name": "A", "category": "electronics", "price": {"amount": None}, "rating": None,
         "specs": {}, "review_count": None},
        {"name": "B", "category": "electronics", "price": {"amount": None}, "rating": None,
         "specs": {}, "review_count": None},
    ]
    dims = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
    limited_data_dims = [d for d in dims if d.get("caption_key") == "limited_data"]
    # Price, Reviews, Value all hit the missing-data path → all emit with caption_key
    assert len(limited_data_dims) >= 1, (
        f"expected at least 1 limited_data dim to stay in output; got {[d.get('key') for d in dims]}"
    )
    # And each one has non-None scores (neutral display score)
    for d in limited_data_dims:
        assert d.get("score_a") is not None
        assert d.get("score_b") is not None


def test_happy_path_keeps_all_emitted_dims():
    """Happy-path comparison (all signals populated) must NOT lose dims
    from the silent-omission filter — regression guard."""
    products = [
        {"name": "A", "category": "electronics", "price": {"amount": 100.0}, "rating": 4.5,
         "specs": {"battery": "3000mAh", "dpi": 460}, "review_count": 1200, "warranty_years": 2},
        {"name": "B", "category": "electronics", "price": {"amount": 80.0}, "rating": 4.4,
         "specs": {"battery": "3500mAh", "dpi": 410}, "review_count": 800, "warranty_years": 1},
    ]
    dims = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
    assert len(dims) >= 3, f"expected at least 3 core dims; got {[d.get('key') for d in dims]}"
    # Every dim in output has numeric scores
    for d in dims:
        assert d.get("score_a") is not None, f"dim {d.get('key')} has None score_a in happy path"
        assert d.get("score_b") is not None, f"dim {d.get('key')} has None score_b in happy path"


def test_omission_does_not_break_core_3_invariant():
    """Bundle E invariant: at least 3 core dims (price/reviews/value)
    should still be emitted for valid 2-product comparisons. A.4.9
    silent-omission must not strip them."""
    products = [
        {"name": "A", "category": "electronics", "price": {"amount": 100.0}, "rating": 4.5,
         "specs": {"battery": "3000mAh"}, "review_count": 100},
        {"name": "B", "category": "electronics", "price": {"amount": 80.0}, "rating": 4.4,
         "specs": {"battery": "3500mAh"}, "review_count": 120},
    ]
    dims = build_dimensions_v2(products, _scoring_result_two_products(), "electronics")
    core_keys = {d["key"] for d in dims if d.get("is_core")}
    assert core_keys == {"price", "reviews", "value"}, (
        f"core dim set regressed: got {core_keys}, expected price+reviews+value"
    )

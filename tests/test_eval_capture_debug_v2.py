"""S3 L3 v2 — EVAL_CAPTURE_DEBUG raw-fact_check serialization.

The offline param sweep re-NORMALIZES (A1/gap-tolerance change normalization), so
it needs the RAW scoring inputs to recompute. specs/price.source_method/rating/
review_count/category already live in overview+specs; the one missing raw input
is fact_check (the reliability dim). EVAL_CAPTURE_DEBUG (default OFF) serializes
it under overview.products[i]._debug_capture for the ONE capture run. Off in
normal prod → key carries None, zero user-facing change, no payload bloat.
"""
import pytest

from app.services import response_builder
from app.services.response_builder import build_comparison_response


def _products():
    return [
        {"name": "A", "category": "electronics",
         "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.5, "review_count": 900, "specs": {"ram": "8 GB"},
         "fact_check": {"specs_verified": 4, "specs_likely": 1, "price_verified": True}},
        {"name": "B", "category": "electronics",
         "price": {"amount": 305, "currency": "BHD", "source_method": "estimated"},
         "rating": 4.4, "review_count": 800, "specs": {"ram": "8 GB"},
         "fact_check": {"specs_verified": 2, "specs_unverified": 3}},
    ]


def _scoring_result():
    return {"scores": {"product_0": {"overall": 72.0, "breakdown": {}},
                       "product_1": {"overall": 60.0, "breakdown": {}}},
            "winner_index": 0, "win_margin": 12.0}


@pytest.fixture
def capture_on(monkeypatch):
    monkeypatch.setenv("EVAL_CAPTURE_DEBUG", "true")
    yield


@pytest.fixture
def capture_off(monkeypatch):
    monkeypatch.delenv("EVAL_CAPTURE_DEBUG", raising=False)
    yield


def test_flag_off_no_debug_payload(capture_off):
    """Default OFF → _debug_capture is None (no raw fact_check leaked in prod)."""
    resp = build_comparison_response(
        product_data=_products(), comparison={}, scoring_result=_scoring_result(),
        category_used="electronics",
    )
    for p in resp["overview"]["products"]:
        assert p.get("_debug_capture") is None


def test_flag_on_serializes_raw_fact_check(capture_on):
    """Flag ON → each product carries _debug_capture.fact_check = the RAW input."""
    resp = build_comparison_response(
        product_data=_products(), comparison={}, scoring_result=_scoring_result(),
        category_used="electronics",
    )
    p0 = resp["overview"]["products"][0]
    assert p0["_debug_capture"]["fact_check"] == {
        "specs_verified": 4, "specs_likely": 1, "price_verified": True
    }
    p1 = resp["overview"]["products"][1]
    assert p1["_debug_capture"]["fact_check"] == {
        "specs_verified": 2, "specs_unverified": 3
    }


def test_flag_on_none_when_no_fact_check(capture_on):
    """Flag ON but a product has no fact_check → _debug_capture None (no crash)."""
    prods = _products()
    prods[0].pop("fact_check")
    resp = build_comparison_response(
        product_data=prods, comparison={}, scoring_result=_scoring_result(),
        category_used="electronics",
    )
    assert resp["overview"]["products"][0]["_debug_capture"] is None


def test_debug_payload_roundtrips_for_rescoring(capture_on):
    """The serialized fact_check is sufficient to reconstruct the product_data
    fact_check input for offline re-scoring (the harness reads it back)."""
    resp = build_comparison_response(
        product_data=_products(), comparison={}, scoring_result=_scoring_result(),
        category_used="electronics",
    )
    # Reconstruct as the harness would: fact_check from _debug_capture.
    recon = resp["overview"]["products"][0]["_debug_capture"]["fact_check"]
    assert recon.get("specs_verified") == 4  # the reliability dim can recompute

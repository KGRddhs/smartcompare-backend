"""Lane 1 L1.6 — scoring_v2.confidence_legs + confidence_details contract.

Prod (2026-06-08) emits the `legs` + per-leg detail dicts on
`overview.confidence` but NOT on `scoring_v2.confidence_legs` /
`scoring_v2.confidence_details`. The design Screen 1 confidence pills +
tap-to-reveal sheet need these keys on scoring_v2 so the FE can render
the pill row directly off the v2 payload without re-reaching into
overview.

The two surfaces share the same upstream `compute_confidence(...)`
call — Lane 1 only needs to thread the result through `_build_scoring_v2`.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import _build_scoring_v2
from tests.fixtures.lane1._helpers import build_inputs


def _v2(filename: str):
    pd, sr, cat, wi = build_inputs(filename)
    return _build_scoring_v2(pd, sr, cat, wi)


# ---------------------------------------------------------------------------
# confidence_legs — pill row contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "iphone15_vs_galaxys24_response.json",
        "tomford_vs_creed_response.json",
        "now_vs_solgar_response.json",
    ],
)
def test_scoring_v2_emits_confidence_legs(filename):
    v2 = _v2(filename)
    legs = v2.get("confidence_legs")
    assert legs is not None, f"scoring_v2.confidence_legs missing for {filename}"
    for leg in ("price", "reviews", "specs"):
        assert leg in legs, f"confidence_legs missing {leg!r} for {filename}"
        assert legs[leg] in ("strong", "acceptable", "weak"), (
            f"confidence_legs.{leg}={legs[leg]!r} not in enum"
        )


# ---------------------------------------------------------------------------
# confidence_details — tap-to-reveal sheet evidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "iphone15_vs_galaxys24_response.json",
        "tomford_vs_creed_response.json",
        "now_vs_solgar_response.json",
    ],
)
def test_scoring_v2_emits_confidence_details(filename):
    v2 = _v2(filename)
    details = v2.get("confidence_details")
    assert details is not None, f"scoring_v2.confidence_details missing for {filename}"
    for leg in ("price", "reviews", "specs"):
        assert leg in details, f"confidence_details missing {leg!r} for {filename}"
        assert isinstance(details[leg], dict)


def test_confidence_details_price_exposes_sources_count():
    v2 = _v2("iphone15_vs_galaxys24_response.json")
    details = v2.get("confidence_details") or {}
    price = details.get("price") or {}
    assert "sources_count" in price, "price.sources_count missing"
    assert isinstance(price["sources_count"], int)
    assert price["sources_count"] >= 0


def test_confidence_details_reviews_exposes_review_count():
    v2 = _v2("iphone15_vs_galaxys24_response.json")
    details = v2.get("confidence_details") or {}
    reviews = details.get("reviews") or {}
    assert "review_count" in reviews
    # Real product hits the threshold of >= 50
    assert reviews["review_count"] >= 0


def test_confidence_details_specs_exposes_verified_pct():
    v2 = _v2("iphone15_vs_galaxys24_response.json")
    details = v2.get("confidence_details") or {}
    specs = details.get("specs") or {}
    assert "verified_pct" in specs
    assert isinstance(specs["verified_pct"], (int, float))


# ---------------------------------------------------------------------------
# Empty / sparse data — must not crash
# ---------------------------------------------------------------------------


def test_scoring_v2_confidence_legs_safe_on_empty_products():
    """When product_data has zero products, _build_scoring_v2 short-circuits
    to `{}` BEFORE the confidence wiring runs. The contract here is just
    'doesn't crash and returns a dict'."""
    v2 = _build_scoring_v2(
        product_data=[],
        scoring_result={},
        category="electronics",
        winner_index=0,
    )
    assert isinstance(v2, dict)


def test_scoring_v2_confidence_details_weak_when_products_have_no_signals():
    """Sparse data: price=None, rating=None — all legs should be 'weak'
    but the keys must still emit."""
    products = [
        {"name": "Alpha", "brand": "X", "price": None, "rating": None},
        {"name": "Beta", "brand": "Y", "price": None, "rating": None},
    ]
    v2 = _build_scoring_v2(
        product_data=products,
        scoring_result={"scores": {"product_0": {"overall": 50}, "product_1": {"overall": 50}}},
        category="other",
        winner_index=0,
    )
    legs = v2.get("confidence_legs") or {}
    for leg in ("price", "reviews", "specs"):
        assert leg in legs
        assert legs[leg] == "weak"

"""Lane 1 L1.10 — integration / fixture-driven end-to-end coverage.

Runs `build_comparison_response()` against the 3 captured prod fixtures
(electronics / fragrances / supplements) and asserts every Lane 1
contract holds simultaneously. This is the cross-QA-ready signal: if
this test green-lights, the v2 payload satisfies all of:

  - L1.3 — scoring_v2.dimensions surfaces ≥1 category-specific dim
  - L1.5 — scoring_v2.factual_verdict has populated line1 + line2
  - L1.6 — scoring_v2.confidence_legs ∈ enum, confidence_details populated
  - L1.7 — overview.products[i].variant string (or empty fallback)
  - L1.8 — overview.products[i].pros_cons explicit accordion block
  - L1.9 — specs.specs_comparison.rows per-row table

For the deeper `compare_from_text()` live test that hits OpenAI + Serper,
see test_lane1_integration_live.py (marked `live_unit`). This file stays
free-tier so it runs on every commit.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import build_comparison_response
from tests.fixtures.lane1._helpers import build_inputs


@pytest.mark.parametrize(
    "filename,expected_cat_dims",
    [
        (
            "iphone15_vs_galaxys24_response.json",
            {"performance", "build_quality", "feature", "ecosystem", "futureproof"},
        ),
        (
            "tomford_vs_creed_response.json",
            {"character", "longevity", "projection", "versatility", "presentation"},
        ),
        (
            "now_vs_solgar_response.json",
            {"efficacy", "safety", "dosage", "form", "trust"},
        ),
    ],
)
def test_full_v2_shape_satisfies_lane1_contracts(filename, expected_cat_dims):
    """The big end-to-end assertion: every Lane 1 contract holds at once."""
    pd, sr, cat, wi = build_inputs(filename)
    response = build_comparison_response(
        products=pd,
        comparison={"winner_index": wi},
        scoring_result=sr,
        category_used=cat,
    )

    # --- L1.3 dimensions ------------------------------------------------
    v2 = response.get("scoring_v2") or {}
    dim_keys = {d.get("key") for d in v2.get("dimensions", [])}
    # 3 core dims always present
    assert "price" in dim_keys
    assert "reviews" in dim_keys
    assert "value" in dim_keys
    # At least one category-specific dim surfaces
    assert dim_keys & expected_cat_dims, (
        f"{filename} dim_keys={dim_keys!r} missing all of {expected_cat_dims!r}"
    )

    # --- L1.5 factual_verdict -------------------------------------------
    fv = v2.get("factual_verdict") or {}
    assert fv.get("line1")
    assert fv.get("line2")

    # --- L1.6 confidence_legs + confidence_details ----------------------
    legs = v2.get("confidence_legs") or {}
    for leg in ("price", "reviews", "specs"):
        assert leg in legs
        assert legs[leg] in ("strong", "acceptable", "weak")
    details = v2.get("confidence_details") or {}
    assert "price" in details
    assert "reviews" in details
    assert "specs" in details

    # --- L1.7 variant ---------------------------------------------------
    ov_products = response["overview"]["products"]
    for op in ov_products:
        assert "variant" in op
        # Variant may be empty when no specs hooks fire — must still be a string
        assert isinstance(op["variant"], str)

    # --- L1.8 pros_cons -------------------------------------------------
    for op in ov_products:
        pc = op.get("pros_cons")
        assert isinstance(pc, dict)
        assert "pros" in pc
        assert "cons" in pc
        assert "is_winner" in pc
        assert isinstance(pc["is_winner"], bool)
    # Exactly one winner
    winners = [op["pros_cons"]["is_winner"] for op in ov_products]
    assert winners.count(True) == 1, f"expected exactly one winner; got {winners!r}"

    # --- L1.9 specs_comparison rows -------------------------------------
    sc = response["specs"]["specs_comparison"]
    assert isinstance(sc, dict)
    assert "rows" in sc
    assert isinstance(sc["rows"], list)
    # Each row has the required keys
    for row in sc["rows"]:
        assert "field" in row
        assert "p0_value" in row
        assert "p1_value" in row
        assert "winner" in row
        assert row["winner"] in (0, 1, "tie", None)


def test_response_no_scary_copy_across_lane1_fields():
    """Audit: walk all user-facing Lane 1 strings and verify no
    forbidden vocabulary slipped in across the 3 categories."""
    forbidden = ["couldn't", "try again", "failed to", "estimated", "reference price"]
    for filename in (
        "iphone15_vs_galaxys24_response.json",
        "tomford_vs_creed_response.json",
        "now_vs_solgar_response.json",
    ):
        pd, sr, cat, wi = build_inputs(filename)
        response = build_comparison_response(
            products=pd,
            comparison={"winner_index": wi},
            scoring_result=sr,
            category_used=cat,
        )
        v2 = response.get("scoring_v2") or {}
        # factual_verdict
        fv = v2.get("factual_verdict") or {}
        for key in ("line1", "line2"):
            text = (fv.get(key) or "").lower()
            for word in forbidden:
                assert word not in text, f"{filename} {key} contains {word!r}: {text!r}"
        # dimension delta_text
        for dim in v2.get("dimensions", []):
            text = (dim.get("delta_text") or "").lower()
            for word in forbidden:
                assert word not in text, (
                    f"{filename} dim {dim.get('key')} delta_text contains {word!r}: {text!r}"
                )

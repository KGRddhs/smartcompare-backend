"""S2 I3.5 — suppress one-sided MISSING_SCORE dim-winner (Decision B render).

Ahmed's Decision B (2026-06-11): "no misleading and false certainty." When
ONE product has a real dimension score and the OTHER is MISSING_SCORE (data
gap, not a low score), declaring the real-score side the per-dimension winner
is FALSE CERTAINTY — it tells the buyer "product X is better on ecosystem"
when the truth is "we don't know product Y's ecosystem at all".

The both-sided-MISSING case is already handled (silent omission +
_dim_winner returns None). This closes the asymmetric gap: a per-DIMENSION
winner must be None when EXACTLY ONE side is MISSING.

Two layers under test:
  1. _dim_winner gains was_missing_a / was_missing_b params → None when
     exactly one is True (both-missing already → None; neither → existing
     margin logic).
  2. build_dimensions_v2 plumbs the per-side missing markers from
     _dim_from_category_lookup so a one-sided-missing category dim never
     ships a winner.
"""
from __future__ import annotations

import pytest

from app.services.scoring_service import (
    MISSING_SCORE,
    _dim_winner,
    build_dimensions_v2,
)


# ---------------------------------------------------------------------------
# Layer 1 — _dim_winner with explicit was_missing flags
# ---------------------------------------------------------------------------

class TestDimWinnerOneSidedMissing:

    def test_one_sided_missing_a_returns_none(self):
        """A real on A, MISSING on B → no winner (don't crown A on a gap)."""
        assert _dim_winner(85, 50, "medium",
                           was_missing_a=False, was_missing_b=True) is None

    def test_one_sided_missing_b_returns_none(self):
        assert _dim_winner(50, 85, "medium",
                           was_missing_a=True, was_missing_b=False) is None

    def test_both_missing_returns_none(self):
        assert _dim_winner(50, 50, "medium",
                           was_missing_a=True, was_missing_b=True) is None

    def test_neither_missing_preserves_winner(self):
        """Real scores on both with a margin → existing winner logic holds."""
        assert _dim_winner(85, 70, "medium",
                           was_missing_a=False, was_missing_b=False) == 0
        assert _dim_winner(70, 85, "medium",
                           was_missing_a=False, was_missing_b=False) == 1

    def test_neither_missing_sub_threshold_tie_still_none(self):
        """Margin under tie threshold → None even with both present."""
        assert _dim_winner(80, 81, "medium",
                           was_missing_a=False, was_missing_b=False) is None

    def test_flags_default_false_backward_compatible(self):
        """Existing callers that don't pass the flags keep current behavior
        (both-MISSING_SCORE-sentinel → None; real margin → winner)."""
        assert _dim_winner(85, 70, "medium") == 0
        assert _dim_winner(MISSING_SCORE, MISSING_SCORE, "medium") is None

    def test_low_confidence_still_suppresses(self):
        """confidence='low' suppression is independent of the missing flags."""
        assert _dim_winner(85, 70, "low",
                           was_missing_a=False, was_missing_b=False) is None


# ---------------------------------------------------------------------------
# Layer 2 — build_dimensions_v2 plumbs per-side missing into category dims
# ---------------------------------------------------------------------------

def _elec_product(name, price, *, rating=4.5, review_count=500):
    return {
        "brand": "BrandX", "name": name, "category": "electronics",
        "price": {"amount": price, "currency": "BHD", "estimated": False},
        "rating": rating, "review_count": review_count, "specs": {},
        "brand_reputation": "established", "warranty_years": 2,
    }


def _scoring_one_sided_missing_ecosystem():
    """product_0 has a real ecosystem score; product_1's ecosystem is
    MISSING_SCORE (the gap). Other dims fully populated so the row is
    emitted (not both-missing-omitted) and reaches _dim_winner."""
    return {
        "scores": {
            "product_0": {"overall": 85, "breakdown": {
                "performance_score": 85, "value_score": 80,
                "build_quality_score": 82, "feature_score": 88,
                "ecosystem_score": 90, "futureproof_score": 78,
            }},
            "product_1": {"overall": 75, "breakdown": {
                "performance_score": 70, "value_score": 82,
                "build_quality_score": 70, "feature_score": 72,
                "ecosystem_score": MISSING_SCORE,  # the one-sided gap
                "futureproof_score": 80,
            }},
        },
        "winner_index": 0,
        "win_margin": 10,
        "scoring_method": "category_weighted",
    }


class TestBuildDimensionsV2OneSidedMissing:

    def test_one_sided_missing_category_dim_has_no_winner(self):
        products = [_elec_product("Phone A", 300), _elec_product("Phone B", 280)]
        dims = build_dimensions_v2(
            products, _scoring_one_sided_missing_ecosystem(), "electronics"
        )
        eco = next((d for d in dims if d["key"] == "ecosystem"), None)
        assert eco is not None, (
            f"ecosystem dim should still emit (only one side missing, not "
            f"both): {[d['key'] for d in dims]}"
        )
        assert eco["winner"] is None, (
            f"ecosystem has product_1 MISSING — winner must be None (no false "
            f"certainty), got {eco['winner']}"
        )

    def test_fully_populated_category_dim_keeps_winner(self):
        """Regression: a dim where BOTH sides have real scores still crowns
        a winner (the suppression is targeted, not blanket)."""
        products = [_elec_product("Phone A", 300), _elec_product("Phone B", 280)]
        dims = build_dimensions_v2(
            products, _scoring_one_sided_missing_ecosystem(), "electronics"
        )
        perf = next((d for d in dims if d["key"] == "performance"), None)
        assert perf is not None
        # product_0 performance 85 vs product_1 70 → margin 15 → winner 0.
        assert perf["winner"] == 0, (
            f"performance fully populated (85 vs 70) must crown product_0, "
            f"got {perf['winner']}"
        )

"""Bundle D Task 2.B.5 — A.6.2-A.6.5 richer value-math copy + metadata.

A.6.2 tests in this file. A.6.3 + A.6.4 + A.6.5 land in follow-on commits.
"""
from __future__ import annotations

import pytest


def _mk(rating: float, price: float):
    return {"rating": rating, "price": {"amount": price}}


class TestA62RicherDeltaText:
    """A.6.2 — `_dim_value` delta_text varies by value-ratio gap magnitude
    instead of returning one of 2 hardcoded strings.

    Buckets:
      - identical va == vb            → "Comparable value"
      - gap < 5%                       → "Nearly identical value"
      - gap 5-15%                      → "Slightly better value ..."
      - gap 15-35%                     → "Noticeably more per dinar ..."
      - gap > 35%                      → "Substantially stronger value ..."
    """

    def test_identical_value_returns_comparable(self):
        from app.services.scoring_service import _dim_value
        # Same rating, same price → va == vb exactly
        dim = _dim_value([_mk(4.5, 100), _mk(4.5, 100)])
        assert dim["delta_text"] == "Comparable value"

    def test_tiny_gap_returns_nearly_identical(self):
        from app.services.scoring_service import _dim_value
        # 4.5/100=0.045, 4.4/100=0.044 → gap ~2.2%
        dim = _dim_value([_mk(4.5, 100), _mk(4.4, 100)])
        assert dim["delta_text"] == "Nearly identical value"

    def test_small_gap_returns_slightly_better(self):
        from app.services.scoring_service import _dim_value
        # 4.5/100=0.045 vs 4.0/100=0.040 → gap ~11.1%
        dim = _dim_value([_mk(4.5, 100), _mk(4.0, 100)])
        assert "Slightly better value here" == dim["delta_text"]

    def test_small_gap_other_side_wins(self):
        from app.services.scoring_service import _dim_value
        # Product B better: 4.0/100=0.040 vs 4.5/100=0.045
        dim = _dim_value([_mk(4.0, 100), _mk(4.5, 100)])
        assert "Slightly better value on the other side" == dim["delta_text"]

    def test_moderate_gap_returns_noticeable(self):
        from app.services.scoring_service import _dim_value
        # 4.5/100=0.045 vs 4.5/130=0.0346 → gap ~23%
        dim = _dim_value([_mk(4.5, 100), _mk(4.5, 130)])
        assert "Noticeably more per dinar here" == dim["delta_text"]

    def test_large_gap_returns_substantial(self):
        from app.services.scoring_service import _dim_value
        # 4.5/50=0.09 vs 4.5/100=0.045 → gap 50%
        dim = _dim_value([_mk(4.5, 50), _mk(4.5, 100)])
        assert "Substantially stronger value ratio" == dim["delta_text"]

    def test_large_gap_other_side_wins(self):
        from app.services.scoring_service import _dim_value
        # Product B 0.09 vs product A 0.045 → gap 50%
        dim = _dim_value([_mk(4.5, 100), _mk(4.5, 50)])
        assert "Substantially stronger value on the other side" == dim["delta_text"]

    def test_limited_data_still_returns_existing_caption(self):
        """When price or rating is missing the existing limited_data
        short-circuit takes precedence over A.6.2 — preserve Bundle C
        contract (caption_key='limited_data', delta='Limited value data')."""
        from app.services.scoring_service import _dim_value
        # No rating on product B
        dim = _dim_value([_mk(4.5, 100), {"price": {"amount": 100}}])
        assert dim["delta_text"] == "Limited value data"
        assert dim["caption_key"] == "limited_data"
        assert dim["confidence"] == "low"


class TestA63CrossTierFraming:
    """A.6.3 — when is_cross_tier=True, the delta_text gets a cross-tier
    framing prefix and the dim exposes `is_cross_tier=True` for FE."""

    def test_same_tier_no_cross_tier_prefix(self):
        from app.services.scoring_service import _dim_value
        dim = _dim_value([_mk(4.5, 50), _mk(4.5, 100)], is_cross_tier=False)
        assert dim["is_cross_tier"] is False
        assert "Across tiers" not in dim["delta_text"]

    def test_cross_tier_adds_prefix(self):
        from app.services.scoring_service import _dim_value
        dim = _dim_value([_mk(4.5, 50), _mk(4.5, 100)], is_cross_tier=True)
        assert dim["is_cross_tier"] is True
        assert dim["delta_text"].startswith("Across tiers — ")

    def test_cross_tier_with_comparable_value_no_prefix(self):
        """Edge case: identical va==vb returns 'Comparable value' — the
        cross-tier prefix would read awkwardly ('Across tiers —
        comparable value'). Keep the bare phrase for the equal case."""
        from app.services.scoring_service import _dim_value
        dim = _dim_value([_mk(4.5, 100), _mk(4.5, 100)], is_cross_tier=True)
        assert dim["delta_text"] == "Comparable value"
        # But flag still exposed
        assert dim["is_cross_tier"] is True

    def test_dim_value_is_cross_tier_default_false(self):
        """When called without is_cross_tier kwarg, default to False
        (backwards compat with pre-Bundle-D callers)."""
        from app.services.scoring_service import _dim_value
        dim = _dim_value([_mk(4.5, 50), _mk(4.5, 100)])
        assert dim["is_cross_tier"] is False

    def test_build_dimensions_v2_propagates_is_cross_tier(self):
        """build_dimensions_v2 reads scoring_result['is_cross_tier'] and
        forwards it to _dim_value."""
        from app.services.scoring_service import build_dimensions_v2

        products = [
            {"name": "A", "category": "electronics",
             "rating": 4.5, "price": {"amount": 50}, "review_count": 1500},
            {"name": "B", "category": "electronics",
             "rating": 4.5, "price": {"amount": 100}, "review_count": 1200},
        ]
        dims = build_dimensions_v2(
            products, scoring_result={"is_cross_tier": True}, category="electronics",
        )
        value_dim = next(d for d in dims if d["key"] == "value")
        assert value_dim["is_cross_tier"] is True
        assert "Across tiers" in value_dim["delta_text"]

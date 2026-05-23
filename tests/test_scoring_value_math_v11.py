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

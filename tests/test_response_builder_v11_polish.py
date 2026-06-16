"""Bundle D v1.1 polish tests for response_builder + scoring_service.

Covers the Bundle C GREEN-gate items punted from Bundle C → Bundle D:
- A.7.2 strip price.note when source_method=estimated (this file)
- A.8.1 build_dimensions_v2 from CATEGORY_DIMENSIONS (see test_scoring_dimensions_v2.py)
- A.4.8 Tier 3 GPT-4o batched synthesis (see test_extraction_tier3_synthesis.py)
- A.6.2-A.6.5 richer value-math copy + metadata (see test_scoring_value_math_v11.py)
"""
from __future__ import annotations

import pytest


class TestA72StripPriceNote:
    """Bundle D Task 2.B.2 / A.7.2 — when a product's price has
    source_method=='estimated', the user-facing `note` field must be
    stripped to None in the response payload. Defense-in-depth alongside
    the frontend silence on Bundle C `ca84eff`.
    """

    def _minimal_products(self, source_method: str, note: str):
        return [
            {
                "name": "iPhone 16",
                "specs": {},
                "price": {
                    "amount": 1199,
                    "currency": "BHD",
                    "source_method": source_method,
                    "note": note,
                },
            },
            {
                "name": "Galaxy S25",
                "specs": {},
                "price": {
                    "amount": 1099,
                    "currency": "BHD",
                    "source_method": "local_bhd",
                    "note": "Real retailer price",
                },
            },
        ]

    def test_estimated_price_becomes_pending(self):
        """SUPERSEDED by Task C1 (price-pending presentation): an `estimated`
        price is NOT showable, so the chokepoint now replaces the whole price
        object with the price-pending shape — NO misleading amount AND no note
        leak. (Was: A.7.2 kept source_method=estimated and only nulled note;
        C1's null-the-amount supersedes that for the estimated case.)"""
        from app.services.response_builder import build_comparison_response

        products = self._minimal_products(
            source_method="estimated",
            note="Estimated from training data",
        )
        response = build_comparison_response(
            products=products,
            comparison={"winner_index": 0},
        )
        # Product 0 was source_method=estimated → price-pending, no amount, no note.
        p0_price = response["overview"]["products"][0]["price"]
        assert p0_price["amount"] is None
        assert p0_price["unavailable"] is True
        assert p0_price["reason"] == "pending_genuine"
        assert p0_price.get("note") is None

    def test_non_estimated_price_note_preserved(self):
        """source_method=local_bhd / converted_usd / page_scrape / etc.
        keeps its note field (real retailer attribution etc.).
        """
        from app.services.response_builder import build_comparison_response

        products = self._minimal_products(
            source_method="estimated",
            note="Estimated from training data",
        )
        response = build_comparison_response(
            products=products,
            comparison={"winner_index": 0},
        )
        # Product 1 was source_method=local_bhd → note preserved
        p1_price = response["overview"]["products"][1]["price"]
        assert p1_price["source_method"] == "local_bhd"
        assert p1_price["note"] == "Real retailer price"

    def test_estimated_with_no_note_does_not_crash(self):
        """A price dict that's source_method=estimated but has NO note
        field at all should be left untouched (no KeyError, no spurious
        note insertion).
        """
        from app.services.response_builder import build_comparison_response

        products = [
            {
                "name": "Iherb",
                "specs": {},
                "price": {
                    "amount": 50,
                    "currency": "USD",
                    "source_method": "estimated",
                    # note: absent
                },
            },
            {
                "name": "NOW",
                "specs": {},
                "price": {"amount": 50, "currency": "USD"},  # no source_method
            },
        ]
        response = build_comparison_response(
            products=products,
            comparison={"winner_index": 0},
        )
        # SUPERSEDED by Task C1: estimated price (no note) → price-pending shape.
        p0_price = response["overview"]["products"][0]["price"]
        assert p0_price["amount"] is None
        assert p0_price["unavailable"] is True
        # No spurious note key on the pending shape.
        if "note" in p0_price:
            assert p0_price["note"] is None

    def test_none_price_does_not_crash_a72_pass(self):
        """The A.7.2 normalization pass must skip products with price=None
        (degraded path — price service returned no result). Pre-existing
        downstream code still requires price to be dict-or-None; covering
        the scalar-int case is out of A.7.2 scope.
        """
        from app.services.response_builder import build_comparison_response

        products = [
            {
                "name": "A", "specs": {},
                "price": {"amount": 10, "source_method": "estimated", "note": "x"},
            },
            {"name": "B", "specs": {}, "price": None},  # degraded
        ]
        # Should not raise — A.7.2 + C1 isinstance(dict) guards skip None
        response = build_comparison_response(
            products=products,
            comparison={"winner_index": 0},
        )
        assert response["success"] is True
        # SUPERSEDED by Task C1: Product A's estimated price → price-pending
        # (no amount, no note leak). Product B's None price stays None.
        p0_price = response["overview"]["products"][0]["price"]
        assert p0_price["amount"] is None
        assert p0_price["unavailable"] is True
        assert p0_price.get("note") is None

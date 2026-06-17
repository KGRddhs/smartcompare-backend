"""Phase 1b Task #2 — wrong-cheap price guards (F1.2).

F1.2 prod evidence:
  - Tom Ford Tobacco Vanille showed **28.2 BHD** (genuine ~118) — a decant /
    all-over-body-spray leak. The current flat designer floor (25 BHD/100ml) is
    TOO LOW for premium/niche houses (Tom Ford / Creed / Amouage genuinely cost
    80-150+/100ml), so 28.2 slipped through. → a PREMIUM fragrance floor tier.
  - K18 showed **4.51 BHD** (genuine ~30+). K18 is HAIRCARE, not fragrance — the
    fragrance guard never applied. → a premium-haircare floor.

Both feed `is_price_showable` so a wrong-cheap price becomes price-pending
(Phase-4 line) instead of a misleading number. Genuine cheap products (mass-market
body spray, a 5-BHD shampoo) are NOT over-rejected.
"""

import pytest

from app.services.price_service import (
    is_implausible_low_fragrance_price,
    is_implausible_low_haircare_price,
    is_price_showable,
)


# ---------------------------------- F1.2a — premium fragrance floor tier ---

class TestPremiumFragranceFloor:
    def test_tobacco_vanille_28bhd_rejected(self):
        # The exact prod leak: Tom Ford Tobacco Vanille at 28.2 BHD (no size →
        # 100ml basis) must be rejected — genuine is ~118.
        assert is_implausible_low_fragrance_price("Tom Ford Tobacco Vanille", 28.2) is True

    def test_creed_aventus_40bhd_rejected(self):
        # Creed Aventus 100ml at 40 BHD is a decant/wrong-SKU (genuine ~120+).
        assert is_implausible_low_fragrance_price("Creed Aventus", 40.0) is True

    def test_amouage_45bhd_rejected(self):
        # Amouage 100ml at 45 BHD is below the 50/100ml premium floor (genuine
        # ~120+). 50 BHD is the floor boundary — kept conservative to avoid
        # over-rejecting a genuinely discounted premium fragrance.
        assert is_implausible_low_fragrance_price("Amouage Reflection Man", 45.0) is True

    def test_premium_genuine_100ml_kept(self):
        # A genuine Tom Ford 100ml at ~118 BHD passes.
        assert is_implausible_low_fragrance_price("Tom Ford Tobacco Vanille", 118.0) is False

    def test_premium_genuine_decant_with_size_kept(self):
        # A REAL 10ml Tom Ford decant priced sanely for 10ml is kept (size-aware
        # floor scales down). 12 BHD for a 10ml premium decant is plausible.
        assert is_implausible_low_fragrance_price(
            "Tom Ford Tobacco Vanille", 12.0, title="Tom Ford Tobacco Vanille 10ml decant"
        ) is False

    def test_standard_designer_floor_unchanged(self):
        # A non-premium designer (e.g. a Versace) keeps the standard 25/100ml
        # floor — 28 BHD is ABOVE it, so NOT rejected (no over-rejection of the
        # cheaper designer tier).
        assert is_implausible_low_fragrance_price("Versace Eros", 28.0) is False

    def test_mass_market_body_spray_not_rejected(self):
        # A generic body spray can be genuinely cheap — never floored.
        assert is_implausible_low_fragrance_price("AXE Dark Temptation body spray", 3.0) is False


# ------------------------------------------ F1.2b — premium haircare floor ---

class TestPremiumHaircareFloor:
    def test_k18_4bhd_rejected(self):
        # The exact prod leak: K18 at 4.51 BHD (genuine ~30+).
        assert is_implausible_low_haircare_price("K18 Leave-In Molecular Repair Hair Mask", 4.51) is True

    def test_olaplex_5bhd_rejected(self):
        assert is_implausible_low_haircare_price("Olaplex No. 3 Hair Perfector", 5.0) is True

    def test_kerastase_6bhd_rejected(self):
        assert is_implausible_low_haircare_price("Kerastase Nutritive Mask", 6.0) is True

    def test_k18_genuine_30bhd_kept(self):
        assert is_implausible_low_haircare_price("K18 Leave-In Molecular Repair Hair Mask", 30.0) is False

    def test_olaplex_genuine_22bhd_kept(self):
        assert is_implausible_low_haircare_price("Olaplex No. 3", 22.0) is False

    def test_drugstore_shampoo_not_rejected(self):
        # A mass-market shampoo is genuinely cheap — not a premium brand, no floor.
        assert is_implausible_low_haircare_price("Pantene Pro-V shampoo", 3.5) is False

    def test_non_haircare_not_affected(self):
        # A phone is not haircare — guard is a no-op.
        assert is_implausible_low_haircare_price("iPhone 15", 4.51) is False

    def test_none_and_zero_safe(self):
        assert is_implausible_low_haircare_price("K18", None) is False
        assert is_implausible_low_haircare_price("K18", 0.0) is False


# ------------------------------------------ is_price_showable composition ---

class TestShowableComposesNewGuards:
    def test_premium_fragrance_leak_not_showable(self):
        price = {"amount": 28.2, "currency": "BHD", "source_method": "converted_usd",
                 "title": "Tom Ford Tobacco Vanille"}
        assert is_price_showable("Tom Ford Tobacco Vanille", price) is False

    def test_haircare_leak_not_showable(self):
        price = {"amount": 4.51, "currency": "BHD", "source_method": "converted_usd",
                 "title": "K18 Leave-In Molecular Repair Hair Mask"}
        assert is_price_showable("K18 Leave-In Molecular Repair Hair Mask", price) is False

    def test_genuine_premium_fragrance_showable(self):
        price = {"amount": 118.0, "currency": "BHD", "source_method": "page_scrape_jsonld",
                 "title": "Tom Ford Tobacco Vanille EDP 100ml"}
        assert is_price_showable("Tom Ford Tobacco Vanille", price) is True

    def test_genuine_haircare_showable(self):
        price = {"amount": 30.0, "currency": "BHD", "source_method": "page_scrape_jsonld",
                 "title": "K18 Leave-In Molecular Repair Hair Mask 50ml"}
        assert is_price_showable("K18 Leave-In Molecular Repair Hair Mask", price) is True


# ----------------------------------- F1.3 — supplement non-CF source path ---
# F1.3 finding: NOW Foods/Solgar D3 returned price=None AND hit the 30s hard cap
# (partial verdict). The empty-verdict half is Phase 4.4; the price-gap half is
# closed structurally by the Phase-1 cache warmer (a warmed genuine supplement
# price serves from the 7d cache instantly, never re-running the 31s cascade).
# These hermetic tests confirm the non-CF iHerb path RESOLVES a price (the path
# was never broken — the failure was the cascade being CUT by the cap), and that
# a supplement iHerb price is showable.

import asyncio
from contextlib import ExitStack
from unittest.mock import patch, AsyncMock


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestSupplementNonCFPath:
    def _service(self):
        from app.services.structured_comparison_service import StructuredComparisonService
        return StructuredComparisonService()

    def test_iherb_price_resolved_for_supplement(self):
        """When iHerb returns a genuine supplement price, the cascade returns it
        (the non-CF source path works — the F1.3 failure was the 30s cap cutting
        the cascade, not the path being broken)."""
        service = self._service()
        iherb_price = {
            "amount": 8.5, "currency": "BHD", "retailer": "iHerb",
            "url": "https://iherb.com/pr/now-foods-d3", "source_method": "converted_usd",
        }
        with ExitStack() as es:
            es.enter_context(patch(
                "app.services.structured_comparison_service.validate_price_query",
                return_value=True))
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=None))
            es.enter_context(patch(
                "app.services.product_data_service.get_cached_price",
                new=AsyncMock(return_value=None)))
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_negative_cache",
                return_value=None))
            es.enter_context(patch(
                "app.services.structured_comparison_service.is_supplement_query",
                return_value=True))
            # Tier 1 Serper Shopping returns ZERO for supplements (the documented
            # behavior) so the cascade reaches the iHerb branch.
            es.enter_context(patch(
                "app.services.structured_comparison_service.search_product_prices",
                new=AsyncMock(return_value={"shopping": [], "organic": []})))
            es.enter_context(patch(
                "app.services.structured_comparison_service.should_escalate",
                return_value=False))
            es.enter_context(patch(
                "app.services.structured_comparison_service.fetch_iherb_price",
                new=AsyncMock(return_value=iherb_price)))
            es.enter_context(patch(
                "app.services.structured_comparison_service.set_cached"))
            es.enter_context(patch.object(
                type(service), "_save_price_to_db", return_value=None))
            result = _run(service._get_price(
                "NOW Foods", "Vitamin D3", None, "bahrain",
                "NOW Foods Vitamin D3", nocache=False, category="supplements",
            ))
        assert result["amount"] == 8.5
        assert result["retailer"] == "iHerb"

    def test_supplement_iherb_price_showable(self):
        from app.services.price_service import is_price_showable
        price = {"amount": 8.5, "currency": "BHD", "source_method": "converted_usd",
                 "title": "NOW Foods Vitamin D3 1000 IU 180 softgels"}
        assert is_price_showable("NOW Foods Vitamin D3", price) is True

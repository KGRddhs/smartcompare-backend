"""S3-reopen T2 — honest source_method on Serper-shopping prices.

THE BUG (team-lead diagnosed; confirmed in code): extract_price_from_shopping
(price_service.py:634) hard-codes source_method="local_bhd" on EVERY candidate,
regardless of whether the price was native BHD or a gl=us-fallback USD price
that got converted. search_product_prices does gl=bh → (empty) → gl=us retry
and returns shopping_region="us_fallback"; those converted USD prices were then
mislabeled local_bhd — violating Ahmed's directive (US-converted must be
HONESTLY labeled converted_usd, NEVER local_bhd).

THE FIX: extract_price_from_shopping stamps converted_usd when a candidate's
price was non-target-currency (so it was converted) OR the shopping_region is
the us_fallback; local_bhd ONLY for genuinely native-BHD prices.

Pure-function tests, no network. Free-tier safe.
"""

import pytest

from app.services.price_service import extract_price_from_shopping


def _item(price, title="Apple iPhone 15 128GB", source="Amazon",
          link="https://www.amazon.com/dp/x"):
    return {"price": price, "title": title, "source": source, "link": link}


class TestShoppingSourceMethodHonesty:
    def test_native_bhd_price_is_local_bhd(self):
        """A genuinely BHD-priced shopping item stamps local_bhd."""
        res = extract_price_from_shopping(
            "Apple iPhone 15 128GB", [_item("BHD 339.000")], "BHD",
        )
        assert res is not None
        assert res["source_method"] == "local_bhd"

    def test_usd_price_converted_is_converted_usd_not_local_bhd(self):
        """A USD-priced item (gl=us fallback) converted to BHD must be labeled
        converted_usd — NEVER local_bhd (the mislabel bug)."""
        res = extract_price_from_shopping(
            "Apple iPhone 15 128GB", [_item("$799.00")], "BHD",
        )
        assert res is not None
        assert res["source_method"] == "converted_usd"
        assert res["source_method"] != "local_bhd"

    def test_shopping_region_us_fallback_forces_converted_usd(self):
        """When the shopping_region is the gl=us fallback, even an item whose
        price string lacks an explicit currency symbol is labeled converted_usd
        (the region is the ground truth that these are US prices)."""
        res = extract_price_from_shopping(
            "Apple iPhone 15 128GB", [_item("799.00")], "BHD",
            shopping_region="us_fallback",
        )
        assert res is not None
        assert res["source_method"] == "converted_usd"

    def test_bh_region_native_price_stays_local_bhd(self):
        """shopping_region='bh' + a BHD price → local_bhd (the genuine path)."""
        res = extract_price_from_shopping(
            "Apple iPhone 15 128GB", [_item("BHD 339.000")], "BHD",
            shopping_region="bh",
        )
        assert res is not None
        assert res["source_method"] == "local_bhd"

    def test_default_region_none_preserves_per_item_currency_logic(self):
        """No shopping_region passed (back-compat): a USD item is still
        converted_usd via per-item currency detection."""
        res = extract_price_from_shopping(
            "Apple iPhone 15 128GB", [_item("$799.00")], "BHD",
        )
        assert res is not None
        assert res["source_method"] == "converted_usd"

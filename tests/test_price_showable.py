"""Task C1 — price-pending presentation: correctly FLAG non-showable prices.

Per Ahmed's decision, we do NOT just raise a floor — instead, when a price is
NOT genuine/showable, the backend flags it so the app can render an engaging
"pricing in a future update" line (FE work, Phase 4). The BACKEND job here is to
identify non-showable prices and normalize them to the price-pending shape:

    {"amount": None, "currency": "BHD", "unavailable": True,
     "reason": "pending_genuine", "size": <if known>}

A resolved price is NOT showable when:
  - source_method == "estimated", OR
  - it fails the implausibility/sample guards
    (is_implausible_low_fragrance_price / is_implausible_high_value_price), OR
  - it is a sample/decant/tester/vial listing (title token OR a tiny size like
    2ml/5ml with a per-ml-implausible price), OR
  - there is no price at all.

Showable prices (genuine BHD, page_scrape_jsonld, shopify_json, AND a real
converted_usd) still display unchanged.
"""

import pytest

from app.services.price_service import is_price_showable


# ---------------------------------------------------------------- showable ---

class TestShowablePrices:
    def test_genuine_local_bhd_shown(self):
        price = {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd"}
        assert is_price_showable("Tom Ford Ombré Leather", price) is True

    def test_page_scrape_jsonld_shown(self):
        price = {"amount": 79.5, "currency": "BHD", "source_method": "page_scrape_jsonld"}
        assert is_price_showable("Creed Aventus", price) is True

    def test_shopify_json_shown(self):
        price = {"amount": 244.99, "currency": "BHD", "source_method": "shopify_json"}
        assert is_price_showable("Sony WH-1000XM5", price) is True

    def test_converted_usd_real_price_shown(self):
        # A real converted price is fine — explicitly part of the showable set.
        price = {"amount": 85.0, "currency": "BHD", "source_method": "converted_usd"}
        assert is_price_showable("Tom Ford Ombré Leather", price) is True

    def test_electronics_genuine_unaffected(self):
        price = {"amount": 399.0, "currency": "BHD", "source_method": "local_bhd"}
        assert is_price_showable("iPhone 15 Pro", price) is True


# ------------------------------------------------------------ not showable ---

class TestEstimatedNotShowable:
    def test_estimated_fragrance_not_showable(self):
        price = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

    def test_estimated_electronics_not_showable(self):
        price = {"amount": 399.0, "currency": "BHD", "source_method": "estimated"}
        assert is_price_showable("iPhone 15 Pro", price) is False


class TestImplausibleGuardsNotShowable:
    def test_sample_grade_fragrance_price_not_showable(self):
        # Ombré 19.93 BHD with no size → below the designer full-bottle floor.
        price = {
            "amount": 19.93, "currency": "BHD", "source_method": "converted_usd",
            "title": "Tom Ford Ombré Leather",
        }
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

    def test_accessory_leak_high_value_not_showable(self):
        # An 11.9 BHD "phone" is an accessory leak (high-value guard).
        price = {
            "amount": 11.9, "currency": "BHD", "source_method": "converted_usd",
            "title": "Galaxy S24 case",
        }
        assert is_price_showable("Samsung Galaxy S24", price) is False


class TestSampleDecantListingNotShowable:
    @pytest.mark.parametrize("token", ["sample", "decant", "tester", "vial"])
    def test_sample_token_in_title_not_showable(self, token):
        price = {
            "amount": 60.0, "currency": "BHD", "source_method": "converted_usd",
            "title": f"Tom Ford Ombré Leather {token} 5ml",
        }
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

    def test_tiny_size_per_ml_implausible_not_showable(self):
        # A 2ml listing priced like a full bottle is a decant — not showable.
        price = {
            "amount": 60.0, "currency": "BHD", "source_method": "converted_usd",
            "title": "Tom Ford Ombré Leather 2ml",
        }
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

    def test_genuine_full_bottle_with_size_still_showable(self):
        # A genuine 100ml at a real price is NOT a sample — stays showable.
        price = {
            "amount": 80.0, "currency": "BHD", "source_method": "local_bhd",
            "title": "Tom Ford Ombré Leather EDP 100ml",
        }
        assert is_price_showable("Tom Ford Ombré Leather", price) is True


class TestNoPriceNotShowable:
    def test_none_price_not_showable(self):
        assert is_price_showable("Tom Ford Ombré Leather", None) is False

    def test_missing_amount_not_showable(self):
        price = {"amount": None, "currency": "BHD", "source_method": "local_bhd"}
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

    def test_zero_amount_not_showable(self):
        price = {"amount": 0.0, "currency": "BHD", "source_method": "local_bhd"}
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

    def test_no_source_method_not_showable(self):
        # An amount with an unknown/blank source method is not trustworthy.
        price = {"amount": 80.0, "currency": "BHD"}
        assert is_price_showable("Tom Ford Ombré Leather", price) is False

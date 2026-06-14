"""S3 electronics-authority (prod-verify fix, prong a) — 3P marketplace reseller
deprioritization.

PROD-VERIFY (f9e0277): iPhone 15 → Walmart-3P "YYWireless" $339→127.8 BHD won
over the genuine sharafdg 244.99, because Serper Shopping us_fallback's CHEAPEST
passing match is a gray-market 3P reseller. extract_price_from_shopping picks
lowest-price; the 3P resellers (Walmart - <seller>, Amazon - <seller>, swappa/
gazelle/unclaimed-baggage used-goods) pass is_counterfeit_listing (it targets
DHgate/AliExpress domains, not marketplace-seller source strings).

Fix: is_marketplace_reseller(source) flags these; extract_price_from_shopping
deprioritizes them so a first-party/authorized listing (Best Buy) is preferred
over a 3P reseller at the same query, and a 3P-only result carries a LOW
authority signal (never out-ranks a genuine BH price downstream).

Inputs are the REAL prod shopping items captured in the live trace.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


# Real prod Serper-Shopping us_fallback items for "Apple iPhone 15" (trace 2026-06-14).
PROD_IPHONE_SHOPPING = [
    {"title": "Apple iPhone 15", "source": "Best Buy", "price": "$449.00",
     "link": "https://www.google.com/search?ibp=oshop&q=iphone15&bestbuy"},
    {"title": "Apple iPhone 15 128GB Black - Available With Cricket Wireless",
     "source": "Cricket Wireless", "price": "$349.99", "link": "https://x/cricket"},
    {"title": "Apple iPhone 15 128GB 6.1\" Fully Unlocked Blue (Refurbished)",
     "source": "Walmart - Wireless Source", "price": "$428.99", "link": "https://x/ws"},
    {"title": "Apple iPhone 15 128GB", "source": "Walmart - YYWireless",
     "price": "$339.00", "link": "https://x/yy"},
    {"title": "iPhone 15 128GB (Unlocked) in Black", "source": "Gazelle Store",
     "price": "$367.99", "link": "https://x/gazelle"},
]


class TestIsMarketplaceReseller:
    def test_walmart_3p_seller_is_reseller(self):
        from app.services.price_service import is_marketplace_reseller
        assert is_marketplace_reseller("Walmart - YYWireless") is True
        assert is_marketplace_reseller("Walmart - Wireless Source") is True
        assert is_marketplace_reseller("Walmart - Kiss Electronics") is True

    def test_amazon_3p_seller_is_reseller(self):
        from app.services.price_service import is_marketplace_reseller
        assert is_marketplace_reseller("Amazon - SomeSeller") is True

    def test_used_goods_marketplaces_are_resellers(self):
        from app.services.price_service import is_marketplace_reseller
        assert is_marketplace_reseller("Gazelle Store") is True
        assert is_marketplace_reseller("Swappa") is True
        assert is_marketplace_reseller("Unclaimed Baggage") is True

    def test_first_party_retailers_are_NOT_resellers(self):
        from app.services.price_service import is_marketplace_reseller
        assert is_marketplace_reseller("Best Buy") is False
        assert is_marketplace_reseller("Walmart") is False  # 1st-party Walmart, no " - seller"
        assert is_marketplace_reseller("Amazon.com") is False
        assert is_marketplace_reseller("Cricket Wireless") is False
        assert is_marketplace_reseller("bahrain.sharafdg.com") is False

    def test_empty_source_is_not_reseller(self):
        from app.services.price_service import is_marketplace_reseller
        assert is_marketplace_reseller("") is False
        assert is_marketplace_reseller(None) is False


class TestShoppingPrefersFirstPartyOver3P:
    def test_first_party_preferred_over_cheaper_3p(self):
        """The prod bug: YYWireless $339 (cheapest) won over Best Buy $449. After
        the fix, a 3P reseller must NOT be picked when a first-party listing for
        the same product exists — even though the 3P is cheaper."""
        from app.services.price_service import extract_price_from_shopping
        picked = extract_price_from_shopping(
            "Apple iPhone 15", PROD_IPHONE_SHOPPING, "BHD",
            shopping_region="us_fallback",
        )
        assert picked is not None
        retailer = (picked.get("retailer") or "").lower()
        assert "yywireless" not in retailer and " - " not in retailer, (
            f"picked a 3P reseller {picked.get('retailer')!r}; a first-party listing "
            f"(Best Buy/Cricket) must be preferred over a cheaper 3P reseller"
        )

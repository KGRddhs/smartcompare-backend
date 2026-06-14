"""S3 coverage #2 — a GLOBAL-tier domain's scrape must NEVER carry a genuine
local_bhd/page_scrape* label, and a USD-fallback JSON-LD price must be labeled
converted_usd (not page_scrape).

Root cause (prod-verify): iPhone 15 -> 198.9 BHD page_scrape_jsonld retailer=
apple.com. apple.com is registry tier="global" (no BH Apple Store). The real
discovered URL was a US REFURBISHED iPhone 15 ($529 USD), converted to 198.9
BHD and stamped genuine. Two honesty bugs:
  (a) extract_price_from_html's USD-fallback converts but stamps `page_scrape`.
  (b) _curl_scraper stamps page_scrape_jsonld on ANY domain incl. global-tier.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest


# --- The hermetic fixture that reproduced the exact 198.9 (synthetic JSON-LD) ---
APPLE_REFURB_HTML = """<!DOCTYPE html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"Refurbished iPhone 15 128GB - Blue (Unlocked)",
 "brand":{"@type":"Brand","name":"Apple"},
 "offers":[{"@type":"Offer","priceCurrency":"USD","price":529.0,
   "itemCondition":"http://schema.org/RefurbishedCondition",
   "availability":"http://schema.org/InStock","sku":"FTLY3LL/A"}]}
</script></head><body>Refurbished iPhone 15</body></html>"""

# A genuine BH retailer JSON-LD (BHD) — must STILL be page_scrape (control).
SHARAFDG_BHD_HTML = """<!DOCTYPE html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"Apple iPhone 15 128GB Black",
 "brand":{"@type":"Brand","name":"Apple"},
 "offers":{"@type":"Offer","priceCurrency":"BHD","price":244.99,
   "availability":"http://schema.org/InStock"}}
</script></head><body>iPhone 15</body></html>"""


class TestNoonRenderFlag:
    """Fix (c): noon.com is Akamai-walled — plain curl gets 0-byte + its JSON-LD
    price is a hardcoded-0 placeholder (real price hydrates in the Next.js RSC
    stream). Flag the registry row is_render_only=True so the cascade routes it
    to the render tier instead of wasting a plain-curl. noon stays SECONDARY
    breadth (gcc-tier), never authoritative."""

    def test_noon_is_render_only(self):
        from app.services.source_router import is_render_only_domain
        assert is_render_only_domain("noon.com") is True
        assert is_render_only_domain("www.noon.com") is True
        assert is_render_only_domain("https://www.noon.com/bahrain-en/iphone-15") is True

    def test_noon_stays_gcc_tier_not_promoted(self):
        from app.services.source_router import registry_tier
        # render-routing must NOT promote noon to bahrain/authoritative.
        assert registry_tier("noon.com") == "gcc"


class TestRegistryTierHelper:
    def test_apple_com_is_global_tier(self):
        from app.services.source_router import registry_tier
        assert registry_tier("apple.com") == "global"
        assert registry_tier("www.apple.com") == "global"
        # subdomain collapses to apex
        assert registry_tier("store.apple.com") == "global"

    def test_sharafdg_bahrain_subdomain_is_bahrain_tier(self):
        from app.services.source_router import registry_tier
        assert registry_tier("bahrain.sharafdg.com") == "bahrain"

    def test_unknown_domain_tier_is_none(self):
        from app.services.source_router import registry_tier
        assert registry_tier("some-random-shop.example") is None


class TestUsdFallbackLabeledConverted:
    """Fix (a): a USD-fallback JSON-LD price (converted to BHD) must carry
    source_method=converted_usd, NOT the genuine page_scrape."""

    def test_apple_refurb_usd_jsonld_is_converted_not_page_scrape(self):
        from app.services.price_service import extract_price_from_html
        result = extract_price_from_html(
            APPLE_REFURB_HTML, "Apple iPhone 15", "BHD", "apple.com",
            "https://www.apple.com/shop/product/ftly3ll/a/refurbished-iphone-15",
        )
        assert result is not None
        # converted figure still present...
        assert result["amount"] > 0
        # ...but provenance is HONEST: converted_usd, never genuine page_scrape.
        assert result["source_method"] == "converted_usd", (
            f"USD-fallback stamped {result['source_method']} — must be converted_usd"
        )

    def test_genuine_bhd_jsonld_stays_page_scrape(self):
        """Control: a real BHD JSON-LD price keeps genuine page_scrape."""
        from app.services.price_service import extract_price_from_html
        result = extract_price_from_html(
            SHARAFDG_BHD_HTML, "Apple iPhone 15", "BHD", "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black",
        )
        assert result is not None
        assert abs(result["amount"] - 244.99) < 0.01
        assert result["source_method"] == "page_scrape"
        assert result["currency"] == "BHD"


@pytest.mark.asyncio
class TestCurlScraperGlobalTierDowngrade:
    """Fix (b): _curl_scraper must NOT stamp page_scrape_jsonld (genuine) on a
    global-tier domain — it downgrades to converted_usd."""

    async def test_global_tier_apple_downgraded_to_converted(self, monkeypatch):
        import app.services.structured_comparison_service as scs

        async def fake_fetch_page_price(url, full_name, currency):
            # simulate a genuine-looking BHD page_scrape from a GLOBAL domain
            return {
                "amount": 198.9, "currency": "BHD", "original_currency": "BHD",
                "retailer": "apple.com", "url": url, "source_method": "page_scrape",
                "estimated": False,
            }
        monkeypatch.setattr(scs, "fetch_page_price", fake_fetch_page_price)

        cand = await scs._curl_scraper(
            "https://www.apple.com/shop/product/ftly3ll/a/refurbished-iphone-15",
            "Apple iPhone 15", "BHD", "apple.com",
        )
        assert cand is not None
        # global-tier ⇒ NEVER genuine page_scrape_jsonld
        assert cand["source_method"] == "converted_usd", (
            f"global-tier apple.com stamped {cand['source_method']} — must downgrade to converted_usd"
        )
        assert cand["raw_data"]["source_method"] == "converted_usd"

    async def test_bahrain_tier_sharafdg_stays_genuine(self, monkeypatch):
        """Control: a bahrain-tier domain keeps genuine page_scrape_jsonld."""
        import app.services.structured_comparison_service as scs

        async def fake_fetch_page_price(url, full_name, currency):
            return {
                "amount": 244.99, "currency": "BHD", "original_currency": "BHD",
                "retailer": "bahrain.sharafdg.com", "url": url,
                "source_method": "page_scrape", "estimated": False,
            }
        monkeypatch.setattr(scs, "fetch_page_price", fake_fetch_page_price)

        cand = await scs._curl_scraper(
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black",
            "Apple iPhone 15", "BHD", "bahrain.sharafdg.com",
        )
        assert cand is not None
        assert cand["source_method"] == "page_scrape_jsonld"  # genuine preserved

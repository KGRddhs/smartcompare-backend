"""S3 electronics-authority (prod-verify fix, prong c) — AUTHORITY over price at
SELECTION: a genuine BH price (page_scrape / local_bhd / shopify_json) MUST beat
a converted_usd price REGARDLESS of price.

PROD-VERIFY (f9e0277): the cascade returned a converted_usd 127.8 BHD (Walmart-3P
us_fallback) instead of the genuine sharafdg 244.99 — partly because the genuine
wasn't reached (prong b), partly because cheapness was winning. This pins the
contract at the _get_price integration level so the genuine BH price wins even
when it's PRICIER than the converted, and a future change can't regress it.

CLAUDE.md invariant: "MOST AUTHORITATIVE not lowest" — official > authorized >
marketplace; a genuine BH shelf price beats a converted foreign figure.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import patch, AsyncMock

from app.services.structured_comparison_service import StructuredComparisonService


@pytest.mark.asyncio
async def test_genuine_bh_pagescrape_beats_cheaper_converted_usd():
    """Tier-1 parks a converted_usd 127.8; escalation finds a genuine BH
    page_scrape 244.99. The PRICIER genuine BH price MUST win (authority>price)."""
    svc = StructuredComparisonService()
    ssc = "app.services.structured_comparison_service"

    # Tier-1 Serper Shopping returns a converted_usd price (gl=us fallback).
    async def fake_shopping(*_a, **_k):
        return {
            "shopping": [{"title": "Apple iPhone 15", "source": "Best Buy",
                          "price": "$449.00", "link": "https://x/bb"}],
            "organic": [], "shopping_region": "us_fallback",
        }

    # extract_price_from_shopping → a converted_usd price (parked, not returned).
    def fake_extract_shopping(name, items, currency, shopping_region=None, **kwargs):
        return {"amount": 127.8, "currency": "BHD", "original_currency": "USD",
                "retailer": "Best Buy", "source_method": "converted_usd",
                "retailer_score": 0.5}

    # Escalation fires + the fan_out finds the GENUINE sharafdg page_scrape 244.99.
    async def fake_fan_out(*_a, **_k):
        return {
            "best": {
                "raw_data": {"amount": 244.99, "currency": "BHD",
                             "original_currency": "BHD",
                             "retailer": "bahrain.sharafdg.com",
                             "source_method": "page_scrape", "in_stock": True},
                "source_method": "page_scrape_jsonld", "rank": 85,
            },
            "alternates": [], "cancelled_count": 0, "elapsed_seconds": 1.0,
        }

    with patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=fake_shopping)), \
         patch(f"{ssc}.extract_price_from_shopping", side_effect=fake_extract_shopping), \
         patch(f"{ssc}._should_escalate_price_scrape", return_value=True), \
         patch(f"{ssc}.fan_out_price_lookup", new=AsyncMock(side_effect=fake_fan_out)), \
         patch(f"{ssc}.search_web", new=AsyncMock(return_value={"organic": [
             {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black",
              "title": "Apple iPhone 15 128GB Black"}]})), \
         patch(f"{ssc}.get_shopify_sources_for_category", return_value=[]), \
         patch(f"{ssc}.get_algolia_sources_for_category", return_value=[]), \
         patch(f"{ssc}.get_unbxd_sources_for_category", return_value=[]), \
         patch(f"{ssc}.get_noon_sources_for_category", return_value=[]), \
         patch(f"{ssc}.get_cached", return_value=None), \
         patch(f"{ssc}.set_cached", return_value=True), \
         patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)), \
         patch.object(svc, "_save_price_to_db"):
        price = await svc._get_price(
            brand="Apple", name="iPhone 15", variant=None, region="bahrain",
            search_query="Apple iPhone 15", nocache=True, category="electronics",
        )

    assert price is not None
    # The genuine BH page_scrape 244.99 WINS over the cheaper converted_usd 127.8.
    assert price["source_method"] in ("page_scrape", "page_scrape_jsonld"), (
        f"genuine BH price lost to converted — got {price.get('source_method')!r} "
        f"@ {price.get('amount')}"
    )
    assert abs(price["amount"] - 244.99) < 0.01, (
        f"expected genuine 244.99, got {price.get('amount')} (cheaper converted won)"
    )
    assert "sharafdg" in (price.get("retailer") or "").lower()

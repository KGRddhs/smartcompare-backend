"""Phase 0 validation: Test Firecrawl + Scrape.do with real API keys."""
import asyncio
import os
import sys
import re
import json

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services import firecrawl_service, scrapedo_service


async def test_firecrawl():
    print("=" * 60)
    print("FIRECRAWL TEST")
    print("=" * 60)

    available = firecrawl_service.is_available()
    print(f"Available: {available}")
    if not available:
        print("SKIP - Firecrawl not available")
        return

    # Test with Bloomingdales (known to work from earlier test)
    url = "https://www.bloomingdales.ae/en/product/gucci-guilty-eau-de-toilette-for-men-90ml/p/671872"
    print(f"\nScraping: {url}")

    html, status = await firecrawl_service.scrape_page_with_status(url)
    print(f"Status: {status}")
    print(f"HTML length: {len(html) if html else 0}")

    if html:
        # Try JSON-LD extraction
        ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        ld_matches = re.findall(ld_pattern, html, re.DOTALL)
        print(f"\nJSON-LD blocks found: {len(ld_matches)}")
        for i, match in enumerate(ld_matches):
            try:
                data = json.loads(match.strip())
                print(f"\n  Block {i}: type={data.get('@type', 'unknown')}")
                if 'offers' in data:
                    print(f"  Offers: {json.dumps(data['offers'], indent=2)[:500]}")
                if 'price' in data:
                    print(f"  Price: {data['price']}")
            except json.JSONDecodeError as e:
                print(f"  Block {i}: JSON parse error: {e}")

        # Try OG meta tags
        og_price = re.search(r'<meta[^>]*property=["\']og:price:amount["\'][^>]*content=["\']([^"\']+)', html)
        if og_price:
            print(f"\nOG Price: {og_price.group(1)}")

        og_currency = re.search(r'<meta[^>]*property=["\']og:price:currency["\'][^>]*content=["\']([^"\']+)', html)
        if og_currency:
            print(f"OG Currency: {og_currency.group(1)}")

        # Try microdata
        price_match = re.search(r'itemprop=["\']price["\'][^>]*content=["\']([^"\']+)', html)
        if price_match:
            print(f"\nMicrodata price: {price_match.group(1)}")

        # Look for any price-like patterns in the HTML
        price_patterns = re.findall(r'(?:AED|BHD|SAR|USD)\s*[\d,]+\.?\d*', html)
        if price_patterns:
            print(f"\nCurrency+price patterns found: {price_patterns[:5]}")

        # Also check for numeric prices near "price" keywords
        price_nearby = re.findall(r'["\']price["\']\s*:\s*["\']?([\d,.]+)', html)
        if price_nearby:
            print(f"Price key values: {price_nearby[:5]}")


async def test_scrapedo():
    print("\n" + "=" * 60)
    print("SCRAPE.DO TEST")
    print("=" * 60)

    available = scrapedo_service.is_available()
    print(f"Available: {available}")
    if not available:
        print("SKIP - Scrape.do not available")
        return

    # Test with a simpler URL first
    url = "https://www.ounass.ae/product/gucci-guilty-eau-de-toilette-90ml-FRGGRP34AEGR/?country=AE"
    print(f"\nRendering: {url}")

    try:
        html, status, cost = await scrapedo_service.render_page_with_status(url)
        print(f"Status: {status} (cost={cost})")
        print(f"HTML length: {len(html) if html else 0}")

        if html:
            # Quick price check
            price_patterns = re.findall(r'(?:AED|BHD|SAR|USD)\s*[\d,]+\.?\d*', html)
            if price_patterns:
                print(f"Price patterns: {price_patterns[:5]}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


async def main():
    print("Phase 0 Validation - Price Scraping Services")
    print(f"FIRECRAWL_API_KEY: {'set' if os.getenv('FIRECRAWL_API_KEY') else 'NOT SET'}")
    print(f"SCRAPEDO_API_TOKEN: {'set' if os.getenv('SCRAPEDO_API_TOKEN') else 'NOT SET'}")
    print()

    await test_firecrawl()
    await test_scrapedo()

    print("\n" + "=" * 60)
    print("PHASE 0 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

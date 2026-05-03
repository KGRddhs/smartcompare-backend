"""Test Firecrawl + Scrape.do on LV official site with updated timeout."""
import asyncio
import os
import sys
import re
import json

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app.services import firecrawl_service, scrapedo_service


URL = "https://me.louisvuitton.com/eng-ae/products/alma-mm-monogram-nvprod7370048v/M27327"


def extract_prices(html, label):
    print(f"\n  [{label}] HTML length: {len(html)}")

    # JSON-LD
    ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    ld_matches = re.findall(ld_pattern, html, re.DOTALL)
    print(f"  JSON-LD blocks: {len(ld_matches)}")
    for i, match in enumerate(ld_matches):
        try:
            data = json.loads(match.strip())
            print(f"    Block {i}: {json.dumps(data, indent=2)[:500]}")
        except json.JSONDecodeError:
            pass

    # OG meta
    og_price = re.search(r'<meta[^>]*property=["\']og:price:amount["\'][^>]*content=["\']([^"\']+)', html)
    if og_price:
        og_cur = re.search(r'<meta[^>]*property=["\']og:price:currency["\'][^>]*content=["\']([^"\']+)', html)
        print(f"  OG Price: {og_price.group(1)} {og_cur.group(1) if og_cur else ''}")

    # Currency patterns
    prices = re.findall(r'(?:AED|BHD|SAR|USD|EUR)\s*[\d,]+\.?\d*', html)
    if prices:
        print(f"  Currency patterns: {prices[:10]}")

    # JSON price keys
    price_keys = re.findall(r'"price"\s*:\s*"?([\d,.]+)', html)
    if price_keys:
        print(f"  JSON price keys: {price_keys[:10]}")

    # Check for "14,600" specifically
    if '14,600' in html or '14600' in html:
        print("  >>> FOUND 14,600 AED in HTML!")


async def main():
    print(f"URL: {URL}")
    print(f"FIRECRAWL_TIMEOUT: {firecrawl_service.FIRECRAWL_TIMEOUT}s\n")

    # Firecrawl
    print("=" * 60)
    print("FIRECRAWL (30s timeout)")
    print("=" * 60)
    try:
        html, status = await firecrawl_service.scrape_page_with_status(URL)
        print(f"Status: {status}")
        if html:
            extract_prices(html, "Firecrawl")
        else:
            print("  No HTML returned")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())

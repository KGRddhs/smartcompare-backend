"""Test Firecrawl on Gucci official site."""
import asyncio
import os
import sys
import re
import json

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app.services import firecrawl_service

URL = "https://www.gucci.com/us/en/pr/women/handbags/top-handle-bags-for-women/borsetto-large-boston-bag-p-866734AAGIR2146"


def extract_prices(html):
    print(f"HTML length: {len(html)}")

    # JSON-LD
    ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    ld_matches = re.findall(ld_pattern, html, re.DOTALL)
    print(f"JSON-LD blocks: {len(ld_matches)}")
    for i, match in enumerate(ld_matches):
        try:
            data = json.loads(match.strip())
            print(f"  Block {i}: @type={data.get('@type', '?')}")
            if 'offers' in data:
                print(f"  Offers: {json.dumps(data['offers'], indent=2)[:500]}")
            if 'price' in data:
                print(f"  Price: {data['price']}")
        except json.JSONDecodeError:
            print(f"  Block {i}: parse error")

    # OG meta
    og_price = re.search(r'<meta[^>]*property=["\']og:price:amount["\'][^>]*content=["\']([^"\']+)', html)
    if og_price:
        og_cur = re.search(r'<meta[^>]*property=["\']og:price:currency["\'][^>]*content=["\']([^"\']+)', html)
        print(f"OG Price: {og_price.group(1)} {og_cur.group(1) if og_cur else ''}")

    # Microdata
    price_match = re.search(r'itemprop=["\']price["\'][^>]*content=["\']([^"\']+)', html)
    if price_match:
        print(f"Microdata price: {price_match.group(1)}")

    # Currency patterns
    prices = re.findall(r'(?:AED|BHD|SAR|USD|EUR|\$|£|€)\s*[\d,]+\.?\d*', html)
    if prices:
        print(f"Currency patterns: {prices[:10]}")

    # JSON price keys
    price_keys = re.findall(r'"price"\s*:\s*"?([\d,.]+)', html)
    if price_keys:
        print(f"JSON price keys: {price_keys[:10]}")

    # Page title
    title = re.search(r'<title>(.*?)</title>', html)
    if title:
        print(f"Title: {title.group(1)[:120]}")


async def main():
    print(f"URL: {URL}")
    print(f"Timeout: {firecrawl_service.FIRECRAWL_TIMEOUT}s\n")

    html, status = await firecrawl_service.scrape_page_with_status(URL)
    print(f"Status: {status}")
    if html:
        extract_prices(html)
    else:
        print("No HTML returned")


if __name__ == "__main__":
    asyncio.run(main())

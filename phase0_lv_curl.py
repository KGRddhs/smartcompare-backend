"""Direct curl_cffi test on LV - check if price is in raw HTML."""
import asyncio
import re
import json
from curl_cffi.requests import AsyncSession


URL = "https://me.louisvuitton.com/eng-ae/products/alma-mm-monogram-nvprod7370048v/M27327"


async def main():
    print(f"URL: {URL}\n")

    async with AsyncSession() as s:
        try:
            r = await asyncio.wait_for(
                s.get(URL, impersonate="chrome", timeout=15),
                timeout=20
            )
            html = r.text
            print(f"Status: {r.status_code}")
            print(f"HTML length: {len(html)}")

            # JSON-LD
            ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            ld_matches = re.findall(ld_pattern, html, re.DOTALL)
            print(f"JSON-LD blocks: {len(ld_matches)}")
            for i, match in enumerate(ld_matches):
                try:
                    data = json.loads(match.strip())
                    print(f"  Block {i}: {json.dumps(data, indent=2)[:800]}")
                except json.JSONDecodeError:
                    print(f"  Block {i}: parse error, raw: {match[:200]}")

            # OG meta
            og_price = re.search(r'<meta[^>]*property=["\']og:price:amount["\'][^>]*content=["\']([^"\']+)', html)
            if og_price:
                print(f"OG Price: {og_price.group(1)}")

            # Currency patterns
            prices = re.findall(r'(?:AED|BHD|SAR|USD|EUR)\s*[\d,]+\.?\d*', html)
            if prices:
                print(f"Currency patterns: {prices[:10]}")

            # JSON price keys
            price_keys = re.findall(r'"price"\s*:\s*"?([\d,.]+)', html)
            if price_keys:
                print(f"JSON price keys: {price_keys[:10]}")

            # Check for price in embedded JSON/state
            state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if state_match:
                print(f"\n__INITIAL_STATE__ found ({len(state_match.group(1))} chars)")
                # Look for price in it
                state_prices = re.findall(r'"price"\s*:\s*"?([\d,.]+)', state_match.group(1))
                if state_prices:
                    print(f"  Prices in state: {state_prices[:10]}")

            # Any script with price data
            all_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            for i, script in enumerate(all_scripts):
                if 'price' in script.lower() and len(script) > 50:
                    price_vals = re.findall(r'"price"\s*:\s*"?([\d,.]+)', script)
                    if price_vals:
                        print(f"\nScript {i} has prices: {price_vals[:5]}")
                        print(f"  Context: {script[script.lower().find('price')-50:script.lower().find('price')+100][:200]}")

        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())

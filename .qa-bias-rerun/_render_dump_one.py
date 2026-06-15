"""Dump the rendered HTML head of one render-walled BH PDP to see WHY no price
extracts (price-less SPA shell vs bot-block vs wrong page). Cache disabled."""
import os, sys, asyncio, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FAN_OUT_BUDGET_SECONDS"] = "35"
os.environ["PRICE_RACE_TIMEOUT"] = "60"
os.environ["STREAM_HARD_CAP_SECONDS"] = "150"
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass
os.environ["UPSTASH_REDIS_URL"] = ""; os.environ["UPSTASH_REDIS_TOKEN"] = ""
os.environ["ENABLE_FIRECRAWL"] = "true"
logging.basicConfig(level=logging.WARNING, format="%(message)s")
from app.services import firecrawl_service

URLS = [
    "https://bolo.bh/products/tom-ford-tobacco-vanille-eau-de-parfum",
    "https://www.boutiqaat.com/en-bh/olaplex-no-3-hair-perfector/",
]

async def main():
    for url in URLS:
        print(f"\n===== {url} =====")
        html = await firecrawl_service.scrape_page(url)
        if not html:
            print("  NO HTML")
            continue
        print(f"  len={len(html)}")
        low = html.lower()
        for marker in ("application/ld+json", "bhd", "price", "captcha",
                       "just a moment", "enable javascript", "cloudflare",
                       "add to cart", "product"):
            print(f"  has[{marker!r}]={marker in low}")
        print("  --- first 1200 chars ---")
        print(html[:1200])

if __name__ == "__main__":
    asyncio.run(main())

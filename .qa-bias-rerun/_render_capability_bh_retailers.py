"""WS3 capability test (Genuine-BH latency+warmer bundle) — does Firecrawl /
Scrape.do RENDER + EXTRACT a genuine BHD price from the render-walled BH
retailers (Sephora BH, bolo.bh, boutiqaat) for a luxury fragrance + a haircare
item, with FAN_OUT_BUDGET_SECONDS=35 (off-clock budget)?

Cache DISABLED (writes NOTHING to prod Redis). Targets specific PDP URLs so the
test isolates RENDER capability (no dependence on Serper discovery finding the
retailer). Budget: Firecrawl 450 LIFETIME — a handful of URLs only. Run once.

Usage: python .qa-bias-rerun/_render_capability_bh_retailers.py
"""
import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Off-clock render budget: the explicit ask is FAN_OUT_BUDGET_SECONDS=35 so a
# luxury SPA can finish rendering. PRICE_RACE_TIMEOUT/STREAM cap raised too.
os.environ["FAN_OUT_BUDGET_SECONDS"] = "35"
os.environ["PRICE_RACE_TIMEOUT"] = "60"
os.environ["STREAM_HARD_CAP_SECONDS"] = "150"

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Disable shared cache — write NOTHING to prod Redis.
os.environ["UPSTASH_REDIS_URL"] = ""
os.environ["UPSTASH_REDIS_TOKEN"] = ""
os.environ["ENABLE_FIRECRAWL"] = "true"
os.environ["ENABLE_SCRAPEDO"] = "true"
os.environ["ENABLE_PAGE_SCRAPE"] = "true"
os.environ["SCRAPING_MODE"] = "hard"
logging.basicConfig(level=logging.INFO, format="%(message)s")

from app.services import firecrawl_service, scrapedo_service
from app.services.price_service import extract_jsonld_price, extract_price_from_html

# (retailer, category, brand-for-jsonld, query_name, candidate PDP URL)
# NOTE: URLs are best-effort PDP guesses for the render-walled retailers. If a
# URL 404s/redirects, that is itself a finding (the slug shape changed) — record
# it. Replace with a live PDP URL from a manual site search if needed.
TARGETS = [
    ("sephora_bh", "fragrance", "Tom Ford", "Tom Ford Ombre Leather",
     "https://www.sephora.bh/en/p/ombre-leather-eau-de-parfum-P10000016.html"),
    ("bolo_bh", "fragrance", "Tom Ford", "Tom Ford Tobacco Vanille",
     "https://bolo.bh/products/tom-ford-tobacco-vanille-eau-de-parfum"),
    ("boutiqaat", "haircare", "Olaplex", "Olaplex No.3 Hair Perfector",
     "https://www.boutiqaat.com/en-bh/olaplex-no-3-hair-perfector/"),
    ("bolo_bh", "haircare", "Kerastase", "Kerastase Nutritive Bain Satin",
     "https://bolo.bh/products/kerastase-nutritive-bain-satin"),
]


async def _try_render(name, url, fn):
    try:
        html = await fn(url)
        return html
    except Exception as e:  # noqa: BLE001
        print(f"    {name} EXC {type(e).__name__}: {e}")
        return None


async def main():
    print(f"FAN_OUT_BUDGET_SECONDS={os.environ['FAN_OUT_BUDGET_SECONDS']} "
          f"firecrawl_avail={firecrawl_service.is_available()} "
          f"scrapedo_avail={scrapedo_service.is_available()}")
    for retailer, cat, brand, qname, url in TARGETS:
        print(f"\n===== [{retailer}] [{cat}] {qname} =====\n  url={url}")
        for engine, fn in (("firecrawl", firecrawl_service.scrape_page),
                           ("scrapedo", scrapedo_service.render_page)):
            html = await _try_render(engine, url, fn)
            if not html:
                print(f"    {engine}: NO HTML (render failed / unavailable)")
                continue
            print(f"    {engine}: rendered {len(html)} bytes")
            # Try JSON-LD first (the genuine-BH path), then the generic HTML
            # price extractor as a fallback signal.
            jp = None
            try:
                jp = extract_jsonld_price(html, brand, "BHD", query_name=qname)
            except Exception as e:  # noqa: BLE001
                print(f"    {engine}: extract_jsonld_price EXC {e}")
            if jp and jp.get("amount"):
                print(f"    {engine}: GENUINE-BHD via JSON-LD -> "
                      f"{jp.get('amount')} {jp.get('currency')} (name={jp.get('name')})")
            else:
                hp = None
                try:
                    hp = extract_price_from_html(html, qname, "BHD", retailer, url)
                except Exception:
                    hp = None
                if hp and hp.get("amount"):
                    print(f"    {engine}: price via HTML extractor -> "
                          f"{hp.get('amount')} {hp.get('currency')}")
                else:
                    print(f"    {engine}: rendered but NO BHD price extracted")


if __name__ == "__main__":
    asyncio.run(main())

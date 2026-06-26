"""A/B: Zyte vs Scrape.do(super+geoCode=bh) as the luxury render provider.

For each luxury product it (1) runs the NEW Zyte key's productList search on
sephora.me (structured BHD price), then (2) renders the SAME sephora PDP via
Scrape.do super+geoCode=bh and extracts a price from the HTML (JSON-LD/OG). It
reports, per product and provider: success / price / latency / cost / whether the
Akamai wall blocked it — so we can decide which provider the render-tier uses.

Burns Zyte + Scrape.do credits (a few each). Run:  python -m scripts.ab_render_providers
"""
from __future__ import annotations

import os

# Render config (off-clock): enable Zyte, enable Scrape.do super+BH geo, raise timeouts.
os.environ["ENABLE_ZYTE_RENDER"] = "true"
os.environ.setdefault("ZYTE_TIMEOUT", "100")
os.environ["SCRAPEDO_SUPER"] = "true"
os.environ["SCRAPEDO_GEOCODE"] = "bh"
os.environ["SCRAPEDO_TIMEOUT"] = os.getenv("AB_SCRAPEDO_TIMEOUT", "70")

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=True)

import asyncio
import time
import urllib.parse

import app.services.zyte_service as Z
from app.services import scrapedo_service as SD
from app.services.price_service import extract_price_from_html

SD.reset_super_flags_cache()  # re-read SCRAPEDO_SUPER/geoCode set above

# (brand, full query) — sephora-carried designer luxury.
PRODUCTS = [
    ("Tom Ford", "Tom Ford Oud Wood"),
    ("YSL", "YSL Black Opium"),
    ("Dior", "Dior Sauvage"),
]


async def zyte_probe(brand: str, query: str):
    t0 = time.perf_counter()
    store = Z.ZYTE_STORES["sephora.me"]
    url = store["search"].format(q=urllib.parse.quote(query))
    data = await Z._zyte_extract(url, {"productList": True})
    dt = time.perf_counter() - t0
    if not data:
        return {"ok": False, "why": "empty/error extract", "dt": dt, "pdp": None}
    products = (data.get("productList") or {}).get("products") or []
    hit = Z._match_product(products, query, brand)
    if not hit:
        return {"ok": False, "why": f"no match ({len(products)} cands)", "dt": dt, "pdp": None}
    amt = Z.normalize_bhd_amount(hit.get("price"))
    return {"ok": amt is not None, "price": amt, "title": hit.get("name"),
            "pdp": hit.get("url"), "dt": dt, "why": ""}


async def scrapedo_probe(query: str, pdp_url: str | None):
    """Render the PDP (preferred, has JSON-LD) — fall back to the search URL."""
    target = pdp_url or Z.ZYTE_STORES["sephora.me"]["search"].format(q=urllib.parse.quote(query))
    t0 = time.perf_counter()
    html, status, cost = await SD.render_page_with_status(target)
    dt = time.perf_counter() - t0
    info = {"status": status, "cost": cost, "dt": dt, "target": target}
    if not html:
        info.update({"ok": False, "why": f"no html (status {status})"})
        return info
    blocked = any(s in html for s in ("AkamaiGHost", "Access Denied", "Reference&#32;#", "Pardon Our Interruption"))
    info["html_kb"] = len(html) // 1024
    info["blocked"] = blocked
    price = extract_price_from_html(html, query, "BHD", "sephora.me", target)
    if price and price.get("amount"):
        info.update({"ok": True, "price": price["amount"], "method": price.get("source_method"),
                     "cur": price.get("currency")})
    else:
        info.update({"ok": False, "why": "no price in html" + (" (AKAMAI BLOCK)" if blocked else "")})
    return info


async def main():
    print(f"Zyte key: {(os.getenv('ZYTE_API_KEY') or '')[:6]}…   "
          f"Scrape.do token: {(os.getenv('SCRAPEDO_API_TOKEN') or '')[:6]}…   "
          f"super={SD._super_enabled()}\n")
    for brand, query in PRODUCTS:
        print(f"{'='*78}\n{query!r}")
        z = await zyte_probe(brand, query)
        if z["ok"]:
            print(f"  ZYTE      OK   {z['price']:.3f} BHD  ({z['dt']:.1f}s)  {z.get('title')!r}")
        else:
            print(f"  ZYTE      FAIL {z['why']}  ({z['dt']:.1f}s)")
        sd = await scrapedo_probe(query, z.get("pdp"))
        if sd["ok"]:
            print(f"  SCRAPE.DO OK   {sd['price']} {sd.get('cur')} via {sd.get('method')}  "
                  f"({sd['dt']:.1f}s, {sd.get('html_kb')}KB, cost={sd['cost']}, status={sd['status']})")
        else:
            print(f"  SCRAPE.DO FAIL {sd['why']}  "
                  f"({sd['dt']:.1f}s, status={sd['status']}, cost={sd['cost']}, "
                  f"blocked={sd.get('blocked')}, kb={sd.get('html_kb')})")
            print(f"            target={sd['target']}")


if __name__ == "__main__":
    asyncio.run(main())

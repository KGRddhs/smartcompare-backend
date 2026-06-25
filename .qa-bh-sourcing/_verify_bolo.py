"""LIVE-VERIFY probe — bolo.bh adapter (Wave 3a, verify-or-omit gate).

Out-of-band (NOT a unit test). curl-fetches a REAL bolo PDP and confirms the
adapter's parse path (JSON-LD main-product offer, then the Nuxt fallback) pulls a
genuine BHD amount, binding the MAIN product (not a carousel item). The adapter
ships ONLY if this reproduces a real BHD amount.

NOTE on discovery: fetch_bolo_price() resolves the PDP via the Wave-2 Redis
sitemap index (built off-clock by cron_index_sitemaps.py — an Ahmed activation).
That index may not be built in a dev box, so this probe tests the FETCH+PARSE leg
directly against a known-live PDP URL (the registry sample_url) — the part that
must produce a genuine price once discovery resolves. It ALSO runs the full
fetch_bolo_price() with a monkeypatched resolver to prove the end-to-end wiring.

Usage:  python .qa-bh-sourcing/_verify_bolo.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.price_service as ps  # noqa: E402
from app.services.price_service import (  # noqa: E402
    curl_fetch_html,
    _bolo_jsonld_main_price,
    _bolo_nuxt_main_price,
    fetch_bolo_price,
)

# Live PDPs (registry sample_url + a skincare PDP found in products1.xml).
PDPS = [
    ("Kensington Wireless Presenter K33272WW",
     "https://www.bolo.bh/products/UO0872Z3OMT-kensington-wireless-presenter-with-red-laser-pointer-k33272ww"),
    ("e.l.f. Holy Hydration Triple Bounce Serum",
     "https://www.bolo.bh/products/UO0OFC4G13M-elf-skin-holy-hydration-triple-bounce-serum-17-hyaluronic-acid-serum-for-plump-bouncy-skin-great-for-hydrating-dry-skin"),
]


async def main() -> int:
    any_genuine = False
    for name, url in PDPS:
        html = await curl_fetch_html(url)
        if not html:
            print(f"[FETCH-FAIL] '{name}' -> no HTML ({url})")
            continue
        parsed = _bolo_jsonld_main_price(html, name, "BHD") or _bolo_nuxt_main_price(html, "BHD")
        if parsed and parsed.get("amount"):
            any_genuine = True
            print(f"[GENUINE] '{name}' -> {parsed['amount']} {parsed['currency']} (page_scrape_jsonld) {url}")
        else:
            print(f"[MISS] '{name}' -> {parsed}")

    # End-to-end wiring: monkeypatch the resolver to a live PDP, prove the full
    # fetch_bolo_price() stamps page_scrape_jsonld.
    name, url = PDPS[0]
    ps_disc = sys.modules.get("app.services.sitemap_discovery_service")
    if ps_disc is None:
        import app.services.sitemap_discovery_service as ps_disc  # noqa: F811
    orig = ps_disc.resolve_pdp_via_sitemap
    ps_disc.resolve_pdp_via_sitemap = lambda domain, query: url
    try:
        e2e = await fetch_bolo_price(name, "BHD")
    finally:
        ps_disc.resolve_pdp_via_sitemap = orig
    print(f"[E2E fetch_bolo_price] '{name}' -> {e2e}")

    if any_genuine:
        print("\nVERDICT: GO — bolo PDP yields a genuine BHD price (page_scrape_jsonld).")
        return 0
    print("\nVERDICT: NO-GO — no genuine BHD extracted from a live bolo PDP.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

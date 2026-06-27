"""Off-clock Zyte luxury-price seed — the sephora-only PROOF (no cron yet).

Renders a curated luxury fragrance/beauty gold-set on the Akamai-walled sephora.me
via Zyte (geolocation=BH) OFF-CLOCK and writes the genuine BHD prices into the
SHARED price cache (7-day genuine TTL). Live /text/compare requests then serve them
INSTANT (cache-first) — the slow Zyte render never touches the 15s request clock.

It does NOT run a full compare per pair (that would burn Serper on specs/reviews):
it parses each pair (1 GPT call) then calls the price path directly. For a
sephora-carried product the cascade's gated Zyte tier hits + caches + returns
BEFORE any Serper shopping; a non-sephora product (e.g. Creed — not stocked) pends
honestly.

Sets ENABLE_ZYTE_RENDER + raised price timeout BEFORE importing the comparison
service (the price modules read the timeout at import).

Manual run (the "small proof"):  python -m scripts.seed_zyte_luxury
"""
from __future__ import annotations

import os

os.environ["ENABLE_ZYTE_RENDER"] = "true"
# Off-clock: raise the request-time price clock so the slow Zyte render finishes.
os.environ["PRICE_RACE_TIMEOUT"] = os.getenv("SEED_PRICE_RACE_TIMEOUT", "120")
os.environ.setdefault("ZYTE_TIMEOUT", "100")

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # never clobber the overrides above / Railway env
except Exception:
    pass

import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Curated luxury gold-set — SEPHORA-CARRIED designer brands (Tom Ford / Dior / YSL
# / Lancome / Mugler / Versace / Armani / Prada / Valentino / Marc Jacobs / V&R).
# Niche houses sephora does NOT stock (Creed, Parfums de Marly, …) are excluded —
# they would pend honestly (the strict no-fab match rejects a wrong-brand result).
LUXURY_PAIRS: List[str] = [
    "Tom Ford Oud Wood vs Tom Ford Black Orchid",
    "Tom Ford Tobacco Vanille vs Tom Ford Lost Cherry",
    "Dior Sauvage vs Dior Homme Intense",
    "Dior Miss Dior vs YSL Mon Paris",
    "YSL Black Opium vs YSL Libre",
    "Lancome La Vie Est Belle vs Mugler Alien",
    "Versace Eros vs Paco Rabanne 1 Million",
    "Giorgio Armani Acqua di Gio vs Prada Luna Rossa",
    "Marc Jacobs Daisy vs Viktor Rolf Flowerbomb",
    "Valentino Born In Roma vs Carolina Herrera Good Girl",
]


async def _seed_one(svc, pair: str) -> Dict[str, int]:
    from app.services.extraction_service import parse_product_query
    tally = {"genuine": 0, "pending": 0}
    try:
        parsed, _usage = await parse_product_query(pair)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[seed_zyte] parse failed for %r: %s", pair, exc)
        return tally
    for prod in (parsed.get("products") or [])[:2]:
        brand = (prod.get("brand") or "").strip()
        name = (prod.get("name") or "").strip()
        variant = prod.get("variant")
        if not (brand or name):
            continue
        full = f"{brand} {name} {variant or ''}".strip()
        try:
            price = await svc._get_price(
                brand, name, variant, "bahrain", full, nocache=True, category="fragrances",
            )
        except Exception as exc:  # noqa: BLE001 — one product must not kill the run
            logger.warning("[seed_zyte] price failed for %r: %s", full, exc)
            continue
        if isinstance(price, dict) and price.get("source_method") == "zyte_render_bhd" and price.get("amount"):
            tally["genuine"] += 1
            logger.info("  SEEDED  %-44s %.3f BHD  (sephora.me via Zyte)", full[:44], price["amount"])
        else:
            tally["pending"] += 1
            sm = (price or {}).get("source_method") or (price or {}).get("reason") or "none"
            logger.info("  pend    %-44s (%s)", full[:44], sm)
    return tally


async def main() -> Dict[str, int]:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not os.getenv("ZYTE_API_KEY"):
        logger.warning("[seed_zyte] ZYTE_API_KEY not set — nothing to seed")
        return {"genuine": 0, "pending": 0}
    import sys
    # Clear the per-run Zyte account-dead kill-switch at the START of each seed run
    # so a repeated IN-PROCESS invocation (a future cron/warmer) is not silently
    # disabled by a terminal 4xx from a prior run after the account has recovered.
    from app.services.zyte_service import reset_account_state
    reset_account_state()
    # CLI: explicit "Brand X vs Brand Y" pair args override the full gold-set
    # (a TARGETED re-seed conserves a fragile Zyte trial).
    pairs = sys.argv[1:] or LUXURY_PAIRS
    from app.services.structured_comparison_service import get_comparison_service
    svc = get_comparison_service()
    logger.info("[seed_zyte] seeding %d luxury pairs into the price cache (off-clock Zyte)…", len(pairs))
    totals = {"genuine": 0, "pending": 0}
    for pair in pairs:
        t = await _seed_one(svc, pair)
        totals["genuine"] += t["genuine"]
        totals["pending"] += t["pending"]
    logger.info(
        "[seed_zyte] done — %d genuine luxury BHD prices cached (7d), %d pending. "
        "Live compares now serve the cached prices instantly.",
        totals["genuine"], totals["pending"],
    )
    return totals


if __name__ == "__main__":
    asyncio.run(main())

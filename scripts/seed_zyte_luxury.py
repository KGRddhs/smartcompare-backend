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
from typing import Any, Dict, List, Optional, Tuple

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

# TRUTH-CRITICAL single-product seeds (Wave C C4) — each pinned to an EXACT,
# recon-confirmed PDP + variant. Unlike LUXURY_PAIRS (Zyte productList search +
# strict match, which stamps in_stock unconditionally and can land a DEFAULT
# variant), these render the pinned PDP with Zyte PRODUCT-DETAIL extraction
# (`fetch_zyte_pdp_price`): it returns the SIZE + real AVAILABILITY, fail-closed
# on a size the PDP contradicts or cannot confirm. The write mirrors the
# _get_price Zyte-tier block exactly (should_cache_price gate -> set_cached at
# build_size_aware_price_cache_key + L2 DB) so the warmed key is byte-identical
# to what a live compare / measure_warmed_kpi reads (parity pinned in
# tests/test_zyte_seed_variant.py). NO GPT parse, NO Serper — Zyte only.
TRUTH_CRITICAL_SEEDS: List[Dict[str, Any]] = [
    {
        # kpi-frag-005 — Prada Luna Rossa Carbon EDT 100ml. Recon 2026-07-02
        # (recon_fragrances): sephora.me product-detail size "Eau de Toilette
        # 100ml", InStock, raw 58500.0 -> fils-fix 58.5 BHD. ounass is REAL-OOS
        # for this SKU; the noon adapter (C3) is the durable path, this seed the
        # immediate one.
        "id": "kpi-frag-005",
        "brand": "Prada",
        "name": "Luna Rossa Carbon",
        "variant": "Eau de Toilette 100ml",
        "category": "fragrances",
        "region": "bahrain",
        "domain": "sephora.me",
        "pdp_url": (
            "https://www.sephora.me/bh-en/p/luna-rossa-carbon-eau-de-toilette/"
            "P2909014?productVariantId=374448"
        ),
    },
]


def _truth_label(entry: Dict[str, Any]) -> str:
    """The full product string a live parse would carry — feeds BOTH the identity
    match and the size-aware cache key (parity with _get_price's search_query)."""
    return f"{entry['brand']} {entry['name']} {entry.get('variant') or ''}".strip()


def _select_targets(
    argv: List[str],
    pairs: Optional[List[str]] = None,
    truth: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """(pairs_to_run, truth_entries_to_run) from the CLI args.

    `--only <match>` filters BOTH lists by case-insensitive substring (a targeted
    re-seed conserves the fragile Zyte budget; a match that hits nothing runs
    NOTHING — never the full set). Explicit positional pair args keep the existing
    pair-only targeted-re-seed semantics (truth entries excluded unless --only
    names them). No args = the full gold-set + all truth-critical entries."""
    pairs = list(LUXURY_PAIRS if pairs is None else pairs)
    truth = list(TRUTH_CRITICAL_SEEDS if truth is None else truth)
    args = list(argv)
    only: Optional[str] = None
    if "--only" in args:
        i = args.index("--only")
        only = (args[i + 1] if i + 1 < len(args) else "").strip().lower()
        del args[i:i + 2]
    explicit_pairs = [a for a in args if not a.startswith("--")]
    run_pairs = explicit_pairs or pairs
    run_truth = [] if explicit_pairs and not only else truth
    if only is not None:
        run_pairs = [p for p in run_pairs if only and only in p.lower()]
        run_truth = [t for t in run_truth if only and only in _truth_label(t).lower()]
    return run_pairs, run_truth


async def _seed_truth_entry(svc, entry: Dict[str, Any]) -> Dict[str, int]:
    """Seed ONE truth-critical entry from its pinned PDP via Zyte product-detail
    extraction. Mirrors the _get_price Zyte-tier write block exactly (the
    fail-closed should_cache_price gate -> set_cached at the size-aware key +
    fire-and-forget L2 DB) so the seeded key IS the key a live compare reads."""
    from app.services.zyte_service import fetch_zyte_pdp_price
    from app.services.price_service import (
        build_size_aware_price_cache_key, price_cache_ttl, should_cache_price,
    )
    from app.services.cache_service import set_cached

    tally = {"genuine": 0, "pending": 0}
    brand = entry["brand"]
    name = entry["name"]
    variant = entry.get("variant")
    region = entry.get("region", "bahrain")
    category = entry.get("category", "fragrances")
    full = _truth_label(entry)
    try:
        price = await fetch_zyte_pdp_price(
            entry["domain"], entry["pdp_url"], full, category=category, brand=brand,
        )
    except Exception as exc:  # noqa: BLE001 — one entry must not kill the run
        logger.warning("[seed_zyte] truth-critical fetch failed for %r: %s", full, exc)
        price = None
    if (
        isinstance(price, dict)
        and price.get("source_method") == "zyte_render_bhd"
        and price.get("amount")
    ):
        cache_key = build_size_aware_price_cache_key(brand, name, variant, region, full)
        if should_cache_price(full, price, category):
            set_cached(cache_key, price, price_cache_ttl(price))
            svc._save_price_to_db(cache_key, brand, name, variant, region, price)
            tally["genuine"] += 1
            logger.info(
                "  SEEDED  %-44s %.3f BHD  (pinned PDP detail, in_stock=%s, key=%s)",
                full[:44], price["amount"], price.get("in_stock"), cache_key,
            )
        else:
            tally["pending"] += 1
            logger.info("  pend    %-44s (write gate refused — fail-closed)", full[:44])
    else:
        tally["pending"] += 1
        logger.info("  pend    %-44s (no verified detail price)", full[:44])
    return tally


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
    # (a TARGETED re-seed conserves a fragile Zyte trial); `--only <match>`
    # substring-filters BOTH the pairs and the truth-critical entries.
    pairs, truth_entries = _select_targets(sys.argv[1:])
    from app.services.structured_comparison_service import get_comparison_service
    svc = get_comparison_service()
    logger.info(
        "[seed_zyte] seeding %d truth-critical entries + %d luxury pairs into the "
        "price cache (off-clock Zyte)…", len(truth_entries), len(pairs),
    )
    totals = {"genuine": 0, "pending": 0}
    for entry in truth_entries:
        t = await _seed_truth_entry(svc, entry)
        totals["genuine"] += t["genuine"]
        totals["pending"] += t["pending"]
    for pair in pairs:
        t = await _seed_one(svc, pair)
        totals["genuine"] += t["genuine"]
        totals["pending"] += t["pending"]
    if totals["genuine"]:
        # Let the fire-and-forget L2 DB writes flush before the loop closes.
        await asyncio.sleep(2)
    logger.info(
        "[seed_zyte] done — %d genuine luxury BHD prices cached (7d), %d pending. "
        "Live compares now serve the cached prices instantly.",
        totals["genuine"], totals["pending"],
    )
    return totals


if __name__ == "__main__":
    asyncio.run(main())

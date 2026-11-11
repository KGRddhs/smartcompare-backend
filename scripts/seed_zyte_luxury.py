"""Off-clock Zyte luxury-price seed: RETIRED by S81-23, it seeds nothing.

Every target this script held was sephora.me (the curated luxury pairs, routed
through the cascade's Zyte tier whose only store is sephora.me, and the one
truth-critical pinned PDP). sephora.me is Akamai-protected, and under the robots
policy (docs/policies/2026-08-31-robots-unreadable-ruling.md: a challenge is a
stop, never a target; owner decision 12) those seeds were removed: LUXURY_PAIRS
and TRUTH_CRITICAL_SEEDS are empty, so main() makes no Zyte, GPT or Serper call.

The scaffold is kept on purpose (RULINGS_S81_G1 R-G1-7): the startup-key guard
("no key -> no paid call") and its pins stay meaningful for any future target
that is robots-allowed, unchallenged and carries a ToS verdict. With targets, it
parses each pair (1 GPT call) and calls the price path directly, and renders each
truth-critical entry from its pinned PDP with Zyte product-detail extraction,
writing genuine BHD prices into the SHARED price cache (7-day genuine TTL)
off-clock, so the slow Zyte render never touches the 15s request clock.

Sets ENABLE_ZYTE_RENDER + raised price timeout BEFORE importing the comparison
service (the price modules read the timeout at import).

Manual run:  python -m scripts.seed_zyte_luxury
"""
from __future__ import annotations

import os

os.environ["ENABLE_ZYTE_RENDER"] = "true"
# Off-clock: raise the request-time price clock so the slow Zyte render finishes.
os.environ["PRICE_RACE_TIMEOUT"] = os.getenv("SEED_PRICE_RACE_TIMEOUT", "120")
os.environ.setdefault("ZYTE_TIMEOUT", "100")
# Wave-2 B3a — OFF-CLOCK warm signal (arms warmer_write_veto at cache-write; the
# live 15s path is untouched). See scripts/cron_warm_price_cache.py.
os.environ.setdefault("WARMER_CONTEXT", "1")

# House rule ("no key -> no paid call"): the intended-run decision is made from
# whether ZYTE_API_KEY was in the PROCESS ENVIRONMENT AT STARTUP, snapshotted
# HERE, ABOVE the load_dotenv() call below. That call is override=False, which
# still SETS a name that is ABSENT from the process env - so it REFILLS
# ZYTE_API_KEY from the repo .env, and a guard reading a live ``os.getenv``
# afterwards would be a no-op even when the operator never exported the key,
# leaking live calls to Zyte (a PAID vendor). The snapshot is taken before any
# dotenv load can run, so it reflects the environment the operator launched
# with. Overridable in-process for tests.
_STARTUP_ZYTE_KEY = (os.environ.get("ZYTE_API_KEY") or "").strip()

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # never clobber the overrides above / Railway env
except Exception:
    pass

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Curated luxury gold-set: retired 2026-10-29 by S81-23 (owner decision 12):
# every pair was routed to sephora.me, which is Akamai-walled; robots policy,
# challenge = stop. Kept as an empty list (the scaffold, R-G1-7); a future
# target must be robots-allowed, unchallenged and carry a ToS verdict.
LUXURY_PAIRS: List[str] = []

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
# Retired 2026-10-29 by S81-23 (owner decision 12): the one entry was a pinned
# sephora.me PDP, which is Akamai-walled; robots policy, challenge = stop. Kept
# as an empty list (the scaffold, R-G1-7).
TRUTH_CRITICAL_SEEDS: List[Dict[str, Any]] = []


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
    # Decided from the STARTUP snapshot, never a live getenv: the module-top
    # load_dotenv(override=False) above REFILLS ZYTE_API_KEY from the repo .env
    # when it is absent from the process env, so a live check here would pass
    # with the operator's key unexported and leak a real (paid) Zyte call.
    if not _STARTUP_ZYTE_KEY:
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

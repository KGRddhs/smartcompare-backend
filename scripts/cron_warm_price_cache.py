#!/usr/bin/env python3
"""Background price-cache warmer cron — Bundle B S3 (the 70%-genuine lever).

Scrapes GENUINE Bahrain (BHD) prices OFF-CLOCK (PRICE_RACE_TIMEOUT raised so the
slow genuine curl / JSON-LD scrape actually finishes) and writes them to the
SHARED price cache (24h TTL). Live /text/compare requests run the real 15s clock
and READ the cache, so a warmed product is served GENUINE + INSTANT. Proven by
hand 2026-06-14 (.qa-bias-rerun/_cache_warm_poc.py); this is the scheduled
production version.

Why a warmer at all: real-time genuine BH scraping is latency-capped — heavy
categories blow the 15s request budget, so the cascade converts to converted_usd.
Decoupling the scrape from the request budget is the only way to reach high
genuine-BH-share WITHOUT sacrificing wall latency.

CATALOG: the gold-truth queries (data/validation_gold_truth.json) — the
representative product set the eval grades. WARMER_SUBSET=smoke20 (~20 queries,
the default) is a budget-safe run; WARMER_SUBSET=full warms the whole set
(~600-1,000 Serper credits — a pre-eval / paid-tier operation, NOT a free-tier
daily).

BUDGET: each query warms 2 products at ~10-30 Serper credits. MAX_QUERIES_PER_RUN
(default 25) HARD-bounds the spend. A ROTATION cursor in Redis advances the
window each run so successive runs cover different products (the whole catalog
over N runs). Free Serper is ~2,500/mo: ~25 queries (~500 credits) per run is
~5 runs/mo, so the warmer's coverage scales with the Serper plan — paid Serper
unlocks daily full coverage.

Gated by ENABLE_PRICE_CACHE_WARMER (fail-CLOSED, same posture as the other crons).

  RAILWAY CRON REGISTRATION IS A DISPATCHER DECISION — this script registers
  nothing. To enable:
    1. Set ENABLE_PRICE_CACHE_WARMER=true on the Railway cron service.
    2. Register a Railway cron service:
         schedule:  0 */12 * * *        (every 12h — beats the 24h cache TTL)
         command:   python -m scripts.cron_warm_price_cache
    3. Size MAX_QUERIES_PER_RUN / WARMER_SUBSET to the Serper plan.

Failures are swallowed + logged — a broken warm must NEVER crash-loop the worker.
"""
from __future__ import annotations

import os

# Off-clock warm: raise the request-time price clock BEFORE importing the
# comparison service (the price modules read PRICE_RACE_TIMEOUT at import). The
# live web service keeps its own 15s PRICE_RACE_TIMEOUT — this override only
# affects THIS warmer process.
os.environ["PRICE_RACE_TIMEOUT"] = os.getenv("WARMER_PRICE_RACE_TIMEOUT", "60")
os.environ["STREAM_HARD_CAP_SECONDS"] = os.getenv("WARMER_STREAM_HARD_CAP", "150")
# WS3/D5 — raise the curl+render fan-out budget so Firecrawl/Scrape.do can finish
# a slow luxury SPA off-clock (live keeps the 12s default; this override is
# warmer-only). Also raise the render-scraper per-call timeouts to match, so a
# residential-proxy render isn't cut short inside the larger budget. Set BEFORE
# importing the comparison/scraper services (those read the env at import).
os.environ["FAN_OUT_BUDGET_SECONDS"] = os.getenv("WARMER_FAN_OUT_BUDGET", "35")
os.environ.setdefault("FIRECRAWL_TIMEOUT", os.getenv("WARMER_FIRECRAWL_TIMEOUT", "45"))
os.environ.setdefault("SCRAPEDO_TIMEOUT", os.getenv("WARMER_SCRAPEDO_TIMEOUT", "35"))

# Load .env for LOCAL/manual runs (Railway injects env directly — load_dotenv
# no-ops in the container since there is no .env file). override=False preserves
# the PRICE_RACE_TIMEOUT override above and never clobbers Railway's injected env.
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.eval_runner import load_gold_truth, select_queries

logger = logging.getLogger(__name__)

# WS4/D6 — the STRUCTURAL warmer-only catalog (luxury fragrance / haircare /
# gadgets whose genuine BH price is reachable-but-slow). Kept SEPARATE from the
# gold-truth set so it never shifts the eval baseline. MERGED into the warmer's
# query set in main(). Path resolves relative to the repo root (this file lives
# in scripts/).
_WARMER_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "warmer_catalog.json"

# Genuine BH source methods (a real BHD shelf price). converted_usd / estimated
# are honest but NOT genuine.
_GENUINE = {
    "local_bhd", "page_scrape", "page_scrape_jsonld", "page_scrape_rendered",
    "shopify_json", "firecrawl", "scrapedo_rendered",
}


def _flag_on() -> bool:
    """Fail-closed flag mirror (same truthy set as the other crons)."""
    return os.getenv("ENABLE_PRICE_CACHE_WARMER", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def load_warmer_catalog(path: Path = _WARMER_CATALOG_PATH) -> List[Dict[str, Any]]:
    """Load the structural warmer-only catalog (data/warmer_catalog.json) as a
    list of query records. Missing / malformed file -> [] (the warmer still runs
    on the gold set). Never raises."""
    try:
        if not path.exists():
            logger.info("[cron_warm] warmer catalog absent (%s) — gold set only", path)
            return []
        doc = json.loads(path.read_text(encoding="utf-8"))
        return list(doc.get("queries") or [])
    except Exception as exc:  # noqa: BLE001 — catalog is additive, never fatal
        logger.warning("[cron_warm] warmer catalog load failed: %s", exc)
        return []


def _merge_catalog(
    gold_queries: List[Dict[str, Any]],
    catalog_queries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Append the structural catalog onto the (subset-selected) gold queries,
    de-duped by the `query` string (case-insensitive) so a catalog pair already
    present in gold isn't warmed twice. Catalog pairs go LAST so the rotation
    cursor still cycles the gold set first on a small MAX_QUERIES_PER_RUN."""
    seen = {(q.get("query") or "").strip().lower() for q in gold_queries}
    merged = list(gold_queries)
    added = 0
    for q in catalog_queries:
        key = (q.get("query") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(q)
        added += 1
    if added:
        logger.info("[cron_warm] merged %d structural catalog pairs", added)
    return merged


def _rotation_window(queries: List[Dict[str, Any]], size: int) -> List[Dict[str, Any]]:
    """Pick `size` queries starting at a Redis-persisted cursor that advances by
    `size` each run, so successive runs cover DIFFERENT products and the whole
    catalog stays warm over N runs. Cursor unavailable -> offset 0 (still correct,
    just no rotation). Wraps around the catalog."""
    n = len(queries)
    if n == 0 or size >= n:
        return list(queries)
    offset = 0
    try:
        from app.services.cache_service import redis_client
        if redis_client is not None:
            new_val = int(redis_client.incrby("warmer:cursor", size) or 0)
            offset = (new_val - size) % n  # window START for THIS run
    except Exception as exc:  # noqa: BLE001 — rotation is best-effort
        logger.info("[cron_warm] rotation cursor unavailable (%s) — offset 0", exc)
        offset = 0
    return [queries[(offset + i) % n] for i in range(size)]


async def _warm_one(record: Dict[str, Any]) -> Dict[str, int]:
    """Warm one gold query (2 products) into the shared cache. Returns a
    {genuine, converted, estimated, none} tally. NEVER raises."""
    from app.services.structured_comparison_service import get_comparison_service
    tally = {"genuine": 0, "converted": 0, "estimated": 0, "none": 0}
    try:
        svc = get_comparison_service()
        r = await svc.compare_from_text(
            record["query"], region=record.get("region", "bahrain"), nocache=True,
        )
        prods = r.get("products") or (r.get("overview") or {}).get("products") or []
        for p in prods:
            price = p.get("price") or {}
            m = price.get("source_method") or ""
            if not price.get("amount"):
                tally["none"] += 1
            elif m in _GENUINE:
                tally["genuine"] += 1
            elif m == "converted_usd":
                tally["converted"] += 1
            elif m == "estimated":
                tally["estimated"] += 1
            else:
                tally["none"] += 1
    except Exception as exc:  # noqa: BLE001 — one bad query must not kill the run
        logger.warning("[cron_warm] warm failed for %r: %s", record.get("query"), exc)
    return tally


async def main() -> Optional[Dict[str, int]]:
    """Cron entrypoint. Returns the run tally (or None when skipped). Idempotent;
    safe to retry — each run re-warms its window into the shared cache."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not _flag_on():
        logger.info("[cron_warm] ENABLE_PRICE_CACHE_WARMER not set — skipping run")
        return None

    subset: Optional[str] = (os.getenv("WARMER_SUBSET", "smoke20").strip() or None)
    if subset == "full":
        subset = None
    max_q = _int_env("MAX_QUERIES_PER_RUN", 25)

    try:
        gold = load_gold_truth()
        queries = select_queries(gold, subset=subset)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_warm] gold load failed: %s", exc)
        return None

    # WS4/D6 — always fold in the structural warmer-only pairs (luxury fragrance/
    # haircare/gadgets incl. the Tom Ford repro). They carry `warm-*` ids absent
    # from the smoke20 subset, so they'd never be selected from gold — merge them
    # AFTER select_queries so they warm on every run regardless of subset.
    queries = _merge_catalog(queries, load_warmer_catalog())

    window = _rotation_window(queries, max_q)
    logger.info(
        "[cron_warm] warming %d/%d queries (subset=%s, PRICE_RACE_TIMEOUT=%s) off-clock",
        len(window), len(queries), subset or "full", os.environ["PRICE_RACE_TIMEOUT"],
    )

    totals = {"genuine": 0, "converted": 0, "estimated": 0, "none": 0}
    for record in window:
        tally = await _warm_one(record)
        for k in totals:
            totals[k] += tally[k]

    priced = totals["genuine"] + totals["converted"] + totals["estimated"]
    share = (totals["genuine"] / priced) if priced else 0.0
    logger.info(
        "[cron_warm] done — products: genuine=%d converted=%d estimated=%d none=%d "
        "| genuine-share=%.1f%% of priced (warmed into shared cache, 24h TTL)",
        totals["genuine"], totals["converted"], totals["estimated"], totals["none"],
        share * 100,
    )
    return totals


# Alias for the cron test contract (mirror cron_eval_nightly).
run = main


if __name__ == "__main__":
    asyncio.run(main())

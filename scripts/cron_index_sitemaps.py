#!/usr/bin/env python3
"""Off-clock SITEMAP INDEX cron — Wave 2 (BH Source-Intelligence, 2026-06-23).

Builds the ``{normalized_slug → pdp_url}`` Redis index for every Bahrain-tier
``mechanism="sitemap"`` storefront (bolo.bh today; boutiqaat.com conditional) so
the 15s request path can RESOLVE a product name → PDP URL with ZERO network (it
only READS the cached index — see ``sitemap_discovery_service``).

🚨 OFF-CLOCK ONLY. The sitemaps are huge (bolo = 16 children × ~21k = ~336k URLs
/ ~20MB; boutiqaat = 27MB + 20MB) — they MUST NEVER be fetched on the request
clock. This cron is the ONLY caller of ``build_sitemap_index``.

$0 + SERPER-INDEPENDENT — this job hits the stores' OWN sitemaps via plain
curl_cffi; it does NOT call Serper / OpenAI / a render provider, so it is
DECOUPLED from the paid-Serper warmer (a SEPARATE flag + cron). Do NOT fold it
into ``cron_warm_price_cache``.

Gated by ENABLE_SITEMAP_INDEX (fail-CLOSED, same posture as the other crons).

  RAILWAY CRON REGISTRATION IS A DISPATCHER/AHMED DECISION — this script
  registers nothing. To enable:
    1. Set ENABLE_SITEMAP_INDEX=true on the Railway cron service.
    2. Register a Railway cron service:
         schedule:  0 3 * * *           (daily 03:00 — the index TTL is 24h)
         command:   python -m scripts.cron_index_sitemaps
    3. Size MAX_DOMAINS_PER_RUN to the storefront count (default 8 covers all).

Failures are swallowed + logged — a broken index build must NEVER crash-loop the
worker (and a partial/failed build just leaves the prior index, or a cold miss
that resolves to honest pending — never a fabricated price).
"""
from __future__ import annotations

import os
from typing import Union

# Load .env for LOCAL/manual runs (Railway injects env directly — load_dotenv
# no-ops in the container since there is no .env file). override=False never
# clobbers Railway's injected env.
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

import asyncio
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# The 9 product categories — iterated so a sitemap source tagged for ANY category
# is discovered (a source with empty `categories` matches every one).
_CATEGORIES = (
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
)

# Per-domain sitemap-INDEX URL(s) (the entry point(s) the builder fetches first).
# The value may be a single URL (str) OR a LIST of URLs for a store that splits
# its catalog across several locale/section index files — build_sitemap_index
# fetches + validates EACH independently (per-index SSRF guard) and UNIONs them
# before the single bucket+persist+meta write. A domain absent here falls back to
# the ``https://www.{domain}/sitemap.xml`` convention. Verified live 2026-06-23
# (recon fixtures in .qa-bh-sourcing/).
_INDEX_URLS: Dict[str, Union[str, List[str]]] = {
    "bolo.bh": "https://www.bolo.bh/products-sitemap.xml",
    # boutiqaat's product urlset lives under the locale path (recon: the index
    # at /en-bh/women/sitemap.xml points to .../products.xml). Codex MED-1: the
    # women-only index lists 47,239 women + 0 men (the design promised ~82k
    # women+men), so index BOTH the women AND men section sitemaps. Conditional —
    # only present in the registry if Wave-4 re-verify promotes it off render.
    # ⚠️ The men URL needs a LIVE re-verify before activation (off-clock + cron
    # ships OFF, so this is safe to land now and confirm before flipping the flag).
    "boutiqaat.com": [
        "https://www.boutiqaat.com/en-bh/women/sitemap.xml",
        "https://www.boutiqaat.com/en-bh/men/sitemap.xml",
    ],
}


def _flag_on() -> bool:
    """Fail-closed flag mirror (same truthy set as the other crons)."""
    return os.getenv("ENABLE_SITEMAP_INDEX", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _sitemap_domains() -> List[str]:
    """De-duped, registry-ordered list of every Bahrain-tier sitemap-mechanism
    domain across all categories. Never raises."""
    try:
        from app.services.source_router import get_sitemap_sources_for_category
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_index] source_router import failed: %s", exc)
        return []
    seen: set = set()
    ordered: List[str] = []
    for cat in _CATEGORIES:
        try:
            for s in get_sitemap_sources_for_category(cat):
                d = (s.domain or "").replace("www.", "").strip().lower()
                if d and d not in seen:
                    seen.add(d)
                    ordered.append(d)
        except Exception as exc:  # noqa: BLE001 — one bad category must not kill the run
            logger.info("[cron_index] selector failed for %s: %s", cat, exc)
    return ordered


def _index_url_for(domain: str) -> Union[str, List[str]]:
    """The sitemap-INDEX entry point(s) for ``domain`` — a str OR a list of URLs
    (a store that splits its catalog across section index files). Passed straight
    to ``build_sitemap_index``, which accepts either."""
    return _INDEX_URLS.get(domain, f"https://www.{domain}/sitemap.xml")


def _rotation_window(domains: List[str], size: int) -> List[str]:
    """Pick `size` domains from a Redis-persisted cursor that advances each run,
    so a small MAX_DOMAINS_PER_RUN still covers the whole set over N runs. Cursor
    unavailable → offset 0 (still correct). Wraps. (Default size covers all
    domains, so rotation is a safety net for a future large source set.)"""
    n = len(domains)
    if n == 0 or size >= n:
        return list(domains)
    offset = 0
    try:
        from app.services.cache_service import redis_client
        if redis_client is not None:
            new_val = int(redis_client.incrby("sitemap_index:cursor", size) or 0)
            offset = (new_val - size) % n
    except Exception as exc:  # noqa: BLE001 — rotation is best-effort
        logger.info("[cron_index] rotation cursor unavailable (%s) — offset 0", exc)
        offset = 0
    return [domains[(offset + i) % n] for i in range(size)]


async def _index_one(domain: str) -> int:
    """Build one domain's sitemap index. Returns the PDP count (0 on any
    failure). NEVER raises — a broken sitemap must not kill the run."""
    from app.services.sitemap_discovery_service import build_sitemap_index
    try:
        return await build_sitemap_index(domain, index_url=_index_url_for(domain))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_index] index build failed for %s: %s", domain, exc)
        return 0


async def main() -> dict | None:
    """Cron entrypoint. Returns a {domain: pdp_count} tally (or None when
    skipped). Idempotent; safe to retry — each run re-builds its window into the
    shared Redis index."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not _flag_on():
        logger.info("[cron_index] ENABLE_SITEMAP_INDEX not set — skipping run")
        return None

    domains = _sitemap_domains()
    if not domains:
        logger.info("[cron_index] no sitemap-mechanism sources in registry — nothing to do")
        return {}

    max_d = _int_env("MAX_DOMAINS_PER_RUN", 8)
    window = _rotation_window(domains, max_d)
    logger.info(
        "[cron_index] indexing %d/%d sitemap domains off-clock", len(window), len(domains),
    )

    tally: dict = {}
    failed: List[str] = []
    for domain in window:
        count = await _index_one(domain)
        tally[domain] = count
        # MED-4: a 0 count is an HONEST failure (index fetch empty / no PDPs / META
        # write failed — build_sitemap_index returns 0 on a failed META write, so
        # the index is unreadable on the request path). Do NOT treat it as success.
        if count <= 0:
            failed.append(domain)
            logger.warning(
                "[cron_index] %s: indexed 0 PDP slugs — build failed or empty "
                "(index unusable on the request path)", domain,
            )

    total = sum(tally.values())
    logger.info(
        "[cron_index] done — %d PDP slugs across %d domains (%d failed: %s): %s",
        total, len(window), len(failed), failed or "none", tally,
    )
    return tally


# Alias for the cron test contract (mirror cron_warm_price_cache / cron_eval_nightly).
run = main


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Off-clock robots registry cron (S81-15 REGISTRY-ROBOTS-DENY).

Reads ``/robots.txt`` of every due kb_merchants host once a day as the named
robots agent (``app.services.robots_eval.QARENBOT_UA``; no browser
impersonation), fail-closed, one request at a time with a delay of
max(Crawl-delay, 2 s), redirects followed by hand with the SSRF check on every
hop, and writes each host's robots record and status transition with ONE
conditional update. The logic, the transition table and the D14 record contract
live in ``app/services/robots_registry.py``; this file is only the entry point.

Gated by ENABLE_ROBOTS_REGISTRY_CRON (default OFF, fail-closed, read per run):
flag off, the run logs one INFO line and returns without reading the table or
fetching anything.

RAILWAY (the owner creates and schedules it; this script registers nothing):
  1. Create a NEW Railway service from this repo for the cron, never ``web`` or
     ``price-warmer``, with config file ``railway.robots.json`` (start command
     ``python -m scripts.cron_robots_registry``, restart policy NEVER, watch
     patterns limited to this script, ``app/services/robots_registry.py``,
     ``app/services/robots_eval.py`` and the config file, so an unrelated push
     does not re-run it). Railway deprecates config-as-code for legacy services
     on 2026-12-01: set the same start command and watch paths in the dashboard
     if the file stops being honoured.
  2. Schedule it daily (for example ``30 2 * * *``).
  3. Variables on THAT service only (NAMES; values live only in Railway):
     SUPABASE_URL, SUPABASE_SERVICE_KEY, ENABLE_ROBOTS_REGISTRY_CRON=true, and
     optionally ROBOTS_CRON_MAX_HOSTS (default 500 hosts per run) and
     ROBOTS_CHALLENGE_PARK_DAYS (default 7).
  4. Migration 045 must be applied and the seed run first.

Failures are swallowed and logged by type: a broken run never crash-loops the
service, and a host whose robots cannot be read is never treated as allowed.
"""
from __future__ import annotations

import asyncio
import logging

# Load .env for LOCAL/manual runs (Railway injects env directly; override=False
# never clobbers the service's variables).
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except Exception:  # noqa: BLE001
    pass

logger = logging.getLogger(__name__)


async def main() -> None:
    """Cron entry point. Returns None; the counts are logged by ``run_cron``."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from app.services import robots_registry as rr

    if not rr.robots_registry_cron_enabled():
        logger.info("[ROBOTS_CRON] ENABLE_ROBOTS_REGISTRY_CRON not set; skipping run")
        return None
    try:
        from app.services.database_service import get_admin_supabase_client

        client = get_admin_supabase_client()
    except Exception as exc:  # noqa: BLE001 - no client: nothing to do this run
        logger.warning("[ROBOTS_CRON] no client reason=%s", type(exc).__name__)
        return None
    try:
        await rr.run_cron(client, rr.default_fetch, asyncio.sleep, rr.utc_now, rr.default_validate)
    except Exception as exc:  # noqa: BLE001 - run_cron never raises; belt and braces
        logger.warning("[ROBOTS_CRON] run failed reason=%s", type(exc).__name__)
    return None


# Alias for the cron test contract (mirrors the other cron scripts).
run = main


if __name__ == "__main__":
    asyncio.run(main())

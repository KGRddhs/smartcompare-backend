#!/usr/bin/env python3
"""Nightly eval-loop cron entrypoint - Bundle B Phase B.6 (F4.5).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.5
Pattern: scripts/cron_reengagement.py

Runs the FULL gold set (data/validation_gold_truth.json) against the
deployed comparison endpoint (TARGET_BASE_URL, ?nocache=true), grades all
4 axes, persists ONE eval_runs row (run_kind='nightly', gold_truth_version
= git SHA of the gold file), and logs the report including the p95-vs-30s
cap check. This is the daily trend signal feeding the /admin/accuracy
dashboard (Bundle B S3 Lane S5).

Gated by ENABLE_EVAL_CRON (fail-CLOSED, same posture as
ENABLE_REENGAGEMENT_PUSHES): absent/false -> no run. A cold-cache full run
burns ~600-1,000 Serper credits, so this MUST stay off until the
dispatcher decides to register it.

  RAILWAY CRON REGISTRATION IS A DISPATCHER DECISION - this script
  registers nothing. To enable nightly, the dispatcher:
    1. Sets ENABLE_EVAL_CRON=true + TARGET_BASE_URL on Railway.
    2. Registers a Railway cron service with:
         schedule:  0 2 * * *          (02:00 UTC = 05:00 GCC, off-peak)
         command:   python -m scripts.cron_eval_nightly
       Cost note: ~$2/night (Serper + GPT). Plan F4.5 leaves the
       register-or-defer-to-S3 call to the S1-close dispatcher review.

Any run failure (network, parse, DB) is swallowed + logged - a broken
nightly must never crash-loop the cron worker.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from scripts.eval_runner import (
    DEFAULT_PROD_URL,
    STREAM_HARD_CAP_SECONDS,
    gold_truth_version,
    load_axis_weights,
    load_gold_truth,
    run_eval,
    select_queries,
)
from scripts.eval_persistence import persist_eval_run

logger = logging.getLogger(__name__)


def _flag_on() -> bool:
    """Fail-closed flag mirror (same truthy set as cron_reengagement)."""
    return os.getenv("ENABLE_EVAL_CRON", "").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


async def main() -> Optional[str]:
    """Cron entrypoint. Returns the eval_runs row id (or None). Idempotent;
    safe to retry - each run writes a fresh row."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not _flag_on():
        logger.info("[cron_eval_nightly] ENABLE_EVAL_CRON not set - skipping run")
        return None

    base_url = os.getenv("TARGET_BASE_URL", DEFAULT_PROD_URL)

    try:
        gold = load_gold_truth()
        queries = select_queries(gold, subset=None)  # full set nightly
        axis_weights = load_axis_weights(gold)  # canonical weights (hard-fail if malformed)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_eval_nightly] gold load failed: %s", exc)
        return None

    logger.info(
        "[cron_eval_nightly] starting nightly eval: base=%s n=%d", base_url, len(queries)
    )

    try:
        report = await run_eval(queries, base_url=base_url, weights=axis_weights)
    except Exception as exc:  # noqa: BLE001 - a failed run must not crash the worker
        logger.warning("[cron_eval_nightly] eval run failed: %s", exc)
        return None

    logger.info(
        "[cron_eval_nightly] pass_rate=%.4f (%d/%d) price=%.3f specs=%.3f "
        "winner=%.3f factual=%.3f p50=%sms p95=%sms",
        report.pass_rate, report.queries_passing, report.queries_total,
        report.axis_avg_price, report.axis_avg_specs, report.axis_avg_winner,
        report.axis_avg_factual, report.wall_p50_ms, report.wall_p95_ms,
    )
    if report.p95_over_cap:
        logger.warning(
            "[cron_eval_nightly] p95 wall %sms OVER the %dms cap "
            "(STREAM_HARD_CAP_SECONDS=%.1f)",
            report.wall_p95_ms, int(STREAM_HARD_CAP_SECONDS * 1000),
            STREAM_HARD_CAP_SECONDS,
        )

    metadata: Dict[str, Any] = {"base_url": base_url, "subset": "full",
                                "source": "nightly_cron", "axis_weights_used": axis_weights}
    try:
        run_id = persist_eval_run(
            report, run_kind="nightly",
            gold_version=gold_truth_version(), metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cron_eval_nightly] persist failed: %s", exc)
        return None

    logger.info("[cron_eval_nightly] done - eval_runs row %s", run_id)
    return run_id


# Alias for backwards-compat with the cron test contract.
run = main


if __name__ == "__main__":
    asyncio.run(main())

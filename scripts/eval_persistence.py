#!/usr/bin/env python3
"""Bundle B Phase B.6 — eval_runs persistence (F4.3).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.3
Schema: migrations/031_eval_runs.sql

Writes ONE eval_runs row per eval run via the service-role Supabase client
(get_admin_supabase_client — the table is service-role-only per migration
031 RLS posture). gold_truth_version is the git SHA of the gold-truth file
(computed by the caller via eval_runner.gold_truth_version).

Persistence failures are swallowed (logged, return None): an eval run's
PRIMARY output is the gate decision + console report; the DB row is
observability. A Supabase outage must not fail the gate.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.database_service import get_admin_supabase_client

logger = logging.getLogger(__name__)

# Mirror of the migration 031 run_kind CHECK enum.
VALID_RUN_KINDS = frozenset({"ci_pr", "nightly", "manual", "staging_smoke"})

# eval_runs columns we write (the rest default: id, created_at).
_INSERT_COLUMNS = (
    "run_kind",
    "gold_truth_version",
    "queries_total",
    "queries_passing",
    "pass_rate",
    "axis_avg_price",
    "axis_avg_specs",
    "axis_avg_winner",
    "axis_avg_factual",
    "wall_p50_ms",
    "wall_p95_ms",
    "metadata",
)


def persist_eval_run(
    report: "Any",  # eval_runner.EvalReport — annotated loosely to avoid import cycle
    *,
    run_kind: str,
    gold_version: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Insert one eval_runs row from an EvalReport. Returns the new row id,
    or None on DB error. Raises ValueError for an invalid run_kind (a
    programming error, surfaced loudly — not a runtime/network condition)."""
    if run_kind not in VALID_RUN_KINDS:
        raise ValueError(
            f"invalid run_kind {run_kind!r}; expected one of {sorted(VALID_RUN_KINDS)}"
        )

    # Merge caller metadata with run-derived context (failing ids + cap flag
    # land in the schema-on-read jsonb column for later drift analysis).
    merged_metadata: Dict[str, Any] = dict(metadata or {})
    merged_metadata.setdefault("failing_ids", list(report.failing_ids))
    merged_metadata.setdefault("p95_over_cap", bool(report.p95_over_cap))

    row = {
        "run_kind": run_kind,
        "gold_truth_version": gold_version,
        "queries_total": report.queries_total,
        "queries_passing": report.queries_passing,
        "pass_rate": report.pass_rate,
        "axis_avg_price": report.axis_avg_price,
        "axis_avg_specs": report.axis_avg_specs,
        "axis_avg_winner": report.axis_avg_winner,
        "axis_avg_factual": report.axis_avg_factual,
        "wall_p50_ms": report.wall_p50_ms,
        "wall_p95_ms": report.wall_p95_ms,
        "metadata": merged_metadata,
    }

    try:
        client = get_admin_supabase_client()
        resp = client.table("eval_runs").insert(row).execute()
        rows = resp.data or []
        return rows[0]["id"] if rows else None
    except Exception as exc:  # noqa: BLE001 — observability write, never fatal
        logger.warning("[eval_persistence] eval_runs insert failed: %s", exc)
        return None


def fetch_eval_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single eval_runs row by id (for regression-mode baseline
    comparison). Returns the row dict or None when absent / on error."""
    try:
        client = get_admin_supabase_client()
        resp = (
            client.table("eval_runs")
            .select(
                "id, pass_rate, axis_avg_price, axis_avg_specs, "
                "axis_avg_winner, axis_avg_factual"
            )
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("[eval_persistence] eval_runs fetch failed for %s: %s", run_id, exc)
        return None

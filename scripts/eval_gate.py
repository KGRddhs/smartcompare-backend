#!/usr/bin/env python3
"""Bundle B Phase B.6  -  two-mode eval gate (F4.4).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.4
Design: docs/plans/2026-06-10-bundle-b-intelligence-layer-design.md (two-mode gate)

Two gate modes, returning (pass: bool, message: str):

  absolute    -  fail if pass_rate < threshold. The bundle-EXIT gate
               (threshold 0.95 per design).

  regression  -  fail if ANY of the 4 per-axis averages drops more than
               REGRESSION_TOLERANCE (2 percentage points) below the named
               baseline eval_runs row. The DURING-bundle gate: catches a
               feature that quietly degrades one axis even while overall
               pass-rate looks fine.

The caller (eval_runner.main) maps pass->exit 0, fail->exit 1.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional, Tuple

from scripts.eval_persistence import fetch_eval_run

# Per-axis regression tolerance: a drop strictly greater than this (absolute,
# on the 0..1 axis-average scale) fails the regression gate. 2% per plan F4.4.
REGRESSION_TOLERANCE = 0.02

# The canonical full-uuid form the warmer/regression baseline anchor MUST use.
# A TRUNCATED id (e.g. `54b603e8`) casts to `uuid` server-side with 22P02, which
# fetch_eval_run swallows → a silent None → an ambiguous "not found". Validating
# the format up front turns that into a clear malformed-id error that names the
# correct full form.
_FULL_BASELINE_EXAMPLE = "54b603e8-4eab-41c9-a34d-a5e391446559"

_AXES = ("price", "specs", "winner", "factual")


def evaluate_gate(
    report: "Any",  # eval_runner.EvalReport
    *,
    mode: str = "absolute",
    threshold: float = 0.95,
    baseline_run_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """Evaluate the gate for an EvalReport. Returns (passed, human message)."""
    if mode == "absolute":
        return _absolute_gate(report, threshold)
    if mode == "regression":
        return _regression_gate(report, baseline_run_id)
    return False, f"GATE FAIL: unknown mode {mode!r}"


def _absolute_gate(report: "Any", threshold: float) -> Tuple[bool, str]:
    passed = report.pass_rate >= threshold
    verdict = "PASS" if passed else "FAIL"
    return passed, (
        f"GATE {verdict} [absolute]: pass_rate={report.pass_rate:.4f} "
        f"vs threshold {threshold:.4f}"
    )


def _axis_value(obj: "Any", axis: str) -> float:
    """Read axis_avg_<axis> from either an EvalReport (attr) or a baseline
    row dict (key)."""
    key = f"axis_avg_{axis}"
    if isinstance(obj, dict):
        return float(obj.get(key) or 0.0)
    return float(getattr(obj, key))


def _regression_gate(report: "Any", baseline_run_id: Optional[str]) -> Tuple[bool, str]:
    if not baseline_run_id:
        return False, "GATE FAIL [regression]: no --baseline-run-id provided"

    # Validate the id is a FULL uuid BEFORE the DB round-trip. A truncated id
    # (e.g. `54b603e8`) would 22P02 server-side and fetch_eval_run would swallow
    # it into a silent None → the ambiguous "not found" below. Fail LOUD + CLEAR
    # here so the operator knows the id is malformed, not the row missing.
    try:
        uuid.UUID(str(baseline_run_id))
    except (ValueError, AttributeError, TypeError):
        return False, (
            f"GATE FAIL [regression]: baseline id {baseline_run_id!r} is not a "
            f"valid UUID. A truncated/short id silently matches NOTHING (Postgres "
            f"22P02) — pass the FULL uuid, e.g. {_FULL_BASELINE_EXAMPLE}"
        )

    baseline = fetch_eval_run(baseline_run_id)
    if baseline is None:
        return False, (
            f"GATE FAIL [regression]: baseline run {baseline_run_id!r} not found "
            f"in eval_runs"
        )

    regressions = []
    for axis in _AXES:
        current = _axis_value(report, axis)
        base = _axis_value(baseline, axis)
        drop = base - current
        if drop > REGRESSION_TOLERANCE:
            regressions.append(f"{axis} {base:.4f}->{current:.4f} (-{drop:.4f})")

    if regressions:
        return False, (
            f"GATE FAIL [regression] vs {baseline_run_id}: axis drop >"
            f"{REGRESSION_TOLERANCE:.2f} on " + "; ".join(regressions)
        )
    return True, (
        f"GATE PASS [regression] vs {baseline_run_id}: no axis dropped more "
        f"than {REGRESSION_TOLERANCE:.2f}"
    )

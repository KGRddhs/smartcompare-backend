"""Tests for scripts/eval_gate.py + the smoke20 subset — B.6 (F4.4).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.4

Two gate modes:
  --mode absolute  --threshold T   : fail if pass_rate < T
  --mode regression --baseline-run-id ID : fail if ANY axis drops >2% vs that row

Smoke subset: data/eval_smoke_subset.json — 20 curated ids spanning all 9
categories, all present in the gold set.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import eval_gate
from scripts.eval_runner import EvalReport, GradedQuery, load_gold_truth, select_queries


REPO_ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = REPO_ROOT / "data" / "validation_gold_truth.json"
SMOKE_PATH = REPO_ROOT / "data" / "eval_smoke_subset.json"


def _report(*, pass_rate=0.95, price=0.9, specs=0.9, winner=0.95, factual=1.0) -> EvalReport:
    return EvalReport(
        queries_total=20, queries_passing=int(round(pass_rate * 20)), pass_rate=pass_rate,
        axis_avg_price=price, axis_avg_specs=specs, axis_avg_winner=winner,
        axis_avg_factual=factual, wall_p50_ms=12000, wall_p95_ms=20000,
        per_query=[], failing_ids=[], p95_over_cap=False,
    )


# ---------------------------------------------------------------------------
# Absolute mode
# ---------------------------------------------------------------------------

def test_absolute_pass_at_threshold():
    ok, msg = eval_gate.evaluate_gate(_report(pass_rate=0.95), mode="absolute", threshold=0.95)
    assert ok is True
    assert "PASS" in msg


def test_absolute_pass_above_threshold():
    ok, _ = eval_gate.evaluate_gate(_report(pass_rate=0.97), mode="absolute", threshold=0.95)
    assert ok is True


def test_absolute_fail_below_threshold():
    ok, msg = eval_gate.evaluate_gate(_report(pass_rate=0.80), mode="absolute", threshold=0.95)
    assert ok is False
    assert "FAIL" in msg
    assert "0.80" in msg or "80" in msg


# ---------------------------------------------------------------------------
# Regression mode
# ---------------------------------------------------------------------------

def _baseline(price=0.90, specs=0.90, winner=0.95, factual=1.0, pass_rate=0.95):
    return {"id": "base-1", "pass_rate": pass_rate, "axis_avg_price": price,
            "axis_avg_specs": specs, "axis_avg_winner": winner, "axis_avg_factual": factual}


def test_regression_pass_when_axes_flat():
    current = _report(price=0.90, specs=0.90, winner=0.95, factual=1.0)
    with patch("scripts.eval_gate.fetch_eval_run", return_value=_baseline()):
        ok, msg = eval_gate.evaluate_gate(current, mode="regression", baseline_run_id="base-1")
    assert ok is True
    assert "PASS" in msg


def test_regression_pass_when_axes_improve():
    current = _report(price=0.95, specs=0.93, winner=0.98, factual=1.0)
    with patch("scripts.eval_gate.fetch_eval_run", return_value=_baseline()):
        ok, _ = eval_gate.evaluate_gate(current, mode="regression", baseline_run_id="base-1")
    assert ok is True


def test_regression_pass_within_2pct_drop():
    # winner drops 0.95 -> 0.934 = 1.6% absolute drop → within the 2% tolerance.
    current = _report(price=0.90, specs=0.90, winner=0.934, factual=1.0)
    with patch("scripts.eval_gate.fetch_eval_run", return_value=_baseline()):
        ok, _ = eval_gate.evaluate_gate(current, mode="regression", baseline_run_id="base-1")
    assert ok is True


def test_regression_fail_when_any_axis_drops_more_than_2pct():
    # price drops 0.90 -> 0.87 = 3% absolute drop → fails.
    current = _report(price=0.87, specs=0.90, winner=0.95, factual=1.0)
    with patch("scripts.eval_gate.fetch_eval_run", return_value=_baseline()):
        ok, msg = eval_gate.evaluate_gate(current, mode="regression", baseline_run_id="base-1")
    assert ok is False
    assert "FAIL" in msg
    assert "price" in msg


def test_regression_fail_lists_every_dropping_axis():
    current = _report(price=0.85, specs=0.80, winner=0.95, factual=1.0)
    with patch("scripts.eval_gate.fetch_eval_run", return_value=_baseline()):
        ok, msg = eval_gate.evaluate_gate(current, mode="regression", baseline_run_id="base-1")
    assert ok is False
    assert "price" in msg and "specs" in msg


def test_regression_requires_baseline_run_id():
    ok, msg = eval_gate.evaluate_gate(_report(), mode="regression", baseline_run_id=None)
    assert ok is False
    assert "baseline" in msg.lower()


def test_regression_fail_when_baseline_row_missing():
    with patch("scripts.eval_gate.fetch_eval_run", return_value=None):
        ok, msg = eval_gate.evaluate_gate(_report(), mode="regression", baseline_run_id="ghost")
    assert ok is False
    assert "not found" in msg.lower() or "missing" in msg.lower()


# ---------------------------------------------------------------------------
# Smoke20 subset integrity
# ---------------------------------------------------------------------------

def test_smoke_subset_file_exists_and_has_20_ids():
    doc = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
    ids = doc["ids"]
    assert len(ids) == 20
    assert len(set(ids)) == 20  # no dupes


def test_smoke_subset_ids_all_exist_in_gold():
    gold = load_gold_truth(GOLD_PATH)
    gold_ids = {q["id"] for q in gold["queries"]}
    doc = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
    missing = [i for i in doc["ids"] if i not in gold_ids]
    assert missing == [], f"smoke ids absent from gold: {missing}"


def test_smoke_subset_spans_all_nine_categories():
    gold = load_gold_truth(GOLD_PATH)
    by_id = {q["id"]: q for q in gold["queries"]}
    doc = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
    cats = {by_id[i]["category"] for i in doc["ids"]}
    expected = {"electronics", "grocery", "supplements", "makeup", "skincare",
                "haircare", "fragrances", "fashion", "other"}
    assert cats == expected, f"missing categories: {expected - cats}"


def test_select_queries_smoke20_returns_subset():
    gold = load_gold_truth(GOLD_PATH)
    selected = select_queries(gold, subset="smoke20", subset_path=SMOKE_PATH)
    assert len(selected) == 20
    doc = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
    assert {q["id"] for q in selected} == set(doc["ids"])


def test_select_queries_full_returns_all():
    gold = load_gold_truth(GOLD_PATH)
    assert len(select_queries(gold, subset=None)) == 50

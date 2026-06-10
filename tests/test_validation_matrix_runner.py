"""Tests for A-L4.3 — validation matrix runner pure scoring functions.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.3
Doc:  docs/plans/2026-06-08-A-validation-matrix-50q.md

We avoid hitting the network here — the run_query() function calls Railway
and is exercised by the dispatcher M2 step on the integrated branch. The
scoring helpers + the gold-truth shape are unit-testable in isolation.
"""

import json
from pathlib import Path

import pytest

# Import via path manipulation — scripts/ isn't a package.
import importlib.util

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_validation_matrix.py"


def _load_runner_module():
    import sys
    spec = importlib.util.spec_from_file_location("run_validation_matrix", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_validation_matrix"] = mod
    spec.loader.exec_module(mod)
    return mod


runner = _load_runner_module()


# ---------------------------------------------------------------------------
# Price scorer
# ---------------------------------------------------------------------------

def test_price_within_tolerance_inside_range():
    assert runner._price_within_tolerance(300.0, 290.0, 400.0, 15.0)


def test_price_within_tolerance_outside_range_but_within_pct_of_midpoint():
    # midpoint=345, ±15% = [293, 397]
    assert runner._price_within_tolerance(295.0, 290.0, 300.0, 15.0)


def test_price_within_tolerance_outside_pct():
    assert not runner._price_within_tolerance(500.0, 290.0, 400.0, 15.0)


def test_price_within_tolerance_none_value():
    assert not runner._price_within_tolerance(None, 290.0, 400.0, 15.0)


def test_score_price_both_products_match():
    response = {
        "products": [
            {"price": {"amount": 350.0}},
            {"price": {"amount": 300.0}},
        ]
    }
    expected = {
        "product_0": {"min": 300, "max": 400},
        "product_1": {"min": 290, "max": 350},
    }
    assert runner.score_price(response, expected, 15.0) == 1.0


def test_score_price_one_product_off():
    response = {
        "products": [
            {"price": {"amount": 700.0}},
            {"price": {"amount": 300.0}},
        ]
    }
    expected = {
        "product_0": {"min": 300, "max": 400},
        "product_1": {"min": 290, "max": 350},
    }
    assert runner.score_price(response, expected, 15.0) == 0.5


def test_score_price_missing_products():
    assert runner.score_price({"products": []}, {"product_0": {"min": 1, "max": 2}, "product_1": {"min": 1, "max": 2}}, 15.0) == 0.0


# ---------------------------------------------------------------------------
# Spec scorer
# ---------------------------------------------------------------------------

def test_score_specs_full_match():
    response = {
        "products": [
            {"specs": {"display": "6.1 inch OLED", "storage": "128GB SSD"}},
            {"specs": {"storage": "128GB UFS"}},
        ]
    }
    expected = {
        "product_0": {"display": "6.1", "storage": "128GB"},
        "product_1": {"storage": "128GB"},
    }
    # product_0: 2/2 = 1.0; product_1: 1/1 = 1.0 → avg = 1.0
    assert runner.score_specs(response, expected) == 1.0


def test_score_specs_partial_match():
    response = {
        "products": [
            {"specs": {"display": "6.1 inch", "storage": "256GB"}},
            {"specs": {}},
        ]
    }
    expected = {
        "product_0": {"display": "6.1", "storage": "128GB"},
        "product_1": {"storage": "128GB"},
    }
    # product_0: 1/2 = 0.5; product_1: 0/1 = 0.0 → avg = 0.25
    assert runner.score_specs(response, expected) == pytest.approx(0.25)


def test_score_specs_unauthored_gold_doesnt_penalise():
    response = {"products": [{"specs": {}}, {"specs": {}}]}
    expected = {"product_0": {}, "product_1": {}}
    assert runner.score_specs(response, expected) == 1.0


# ---------------------------------------------------------------------------
# Winner scorer
# ---------------------------------------------------------------------------

def test_score_winner_match():
    response = {"overview": {"winner": {"product_index": 0}}}
    assert runner.score_winner(response, 0) == 1.0


def test_score_winner_mismatch():
    response = {"overview": {"winner": {"product_index": 1}}}
    assert runner.score_winner(response, 0) == 0.0


def test_score_winner_legacy_alias():
    response = {"winner_index": 1}
    assert runner.score_winner(response, 1) == 1.0


def test_score_winner_missing_returns_zero():
    assert runner.score_winner({}, 0) == 0.0


def test_score_winner_unauthored_returns_one():
    assert runner.score_winner({}, None) == 1.0


# ---------------------------------------------------------------------------
# Factual scorer
# ---------------------------------------------------------------------------

def test_score_factual_clean_verdict():
    response = {
        "overview": {
            "verdict": {
                "winner_reason": "iPhone wins on camera",
                "key_tradeoff": "Battery life on the runner-up",
                "value_context": "Apple ecosystem lock-in"
            }
        }
    }
    assert runner.score_factual(response, ["8K video", "USB-C 3.2"]) == 1.0


def test_score_factual_one_hallucination():
    response = {
        "overview": {
            "verdict": {
                "winner_reason": "iPhone wins with 8K video recording",
                "key_tradeoff": "",
                "value_context": ""
            }
        }
    }
    # 1 of 2 forbidden facts triggered → 1 - 0.5 = 0.5
    assert runner.score_factual(response, ["8K video", "USB-C 3.2"]) == pytest.approx(0.5)


def test_score_factual_empty_forbidden_returns_one():
    assert runner.score_factual({"overview": {}}, []) == 1.0


# ---------------------------------------------------------------------------
# Weighted aggregation
# ---------------------------------------------------------------------------

def test_weighted_all_pass():
    weights = {"price_accuracy": 0.25, "specs_correctness": 0.25, "winner_correctness": 0.30, "factual_claim_integrity": 0.20}
    assert runner._weighted(1.0, 1.0, 1.0, 1.0, weights) == pytest.approx(1.0)


def test_weighted_winner_dominates_marginal():
    weights = {"price_accuracy": 0.25, "specs_correctness": 0.25, "winner_correctness": 0.30, "factual_claim_integrity": 0.20}
    # Winner missing = 0.30 lost; everything else 1.0 = 0.70
    assert runner._weighted(1.0, 1.0, 0.0, 1.0, weights) == pytest.approx(0.70)
    # Winner present, price + specs lost = 0.50
    assert runner._weighted(0.0, 0.0, 1.0, 1.0, weights) == pytest.approx(0.50)


# ---------------------------------------------------------------------------
# Gold-truth integrity (the file we'll actually run against)
# ---------------------------------------------------------------------------

def test_gold_truth_has_200_queries():
    # Bundle B F5: gold set expanded 50 -> 200 (50 original + 150 new).
    gold = json.loads((REPO_ROOT / "data" / "validation_gold_truth.json").read_text(encoding="utf-8"))
    assert len(gold["queries"]) == 200


def test_gold_truth_queries_unique_ids():
    gold = json.loads((REPO_ROOT / "data" / "validation_gold_truth.json").read_text(encoding="utf-8"))
    ids = [q["id"] for q in gold["queries"]]
    assert len(set(ids)) == len(ids)


def test_gold_truth_covers_all_9_categories():
    gold = json.loads((REPO_ROOT / "data" / "validation_gold_truth.json").read_text(encoding="utf-8"))
    cats = {q["category"] for q in gold["queries"]}
    expected = {"electronics", "supplements", "fragrances", "makeup", "skincare", "haircare", "fashion", "grocery", "other"}
    assert cats == expected


def test_gold_truth_metadata_block():
    gold = json.loads((REPO_ROOT / "data" / "validation_gold_truth.json").read_text(encoding="utf-8"))
    meta = gold["_metadata"]
    assert meta["queries"] == 200  # Bundle B F5: expanded 50 -> 200
    assert meta["pass_threshold_per_query"] == 0.80
    assert meta["gate_aggregate_pass_rate"] == 0.80
    assert meta["price_tolerance_pct"] == 15.0
    assert sum(meta["axis_weights"].values()) == pytest.approx(1.0)


def test_every_gold_query_has_required_fields():
    gold = json.loads((REPO_ROOT / "data" / "validation_gold_truth.json").read_text(encoding="utf-8"))
    required = {"id", "query", "category", "region", "expected_prices", "expected_specs", "expected_winner_index", "forbidden_facts", "max_wall_seconds"}
    for q in gold["queries"]:
        missing = required - set(q.keys())
        assert not missing, f"{q.get('id')} missing fields: {missing}"
        assert q["expected_winner_index"] in (0, 1)
        assert isinstance(q["forbidden_facts"], list)

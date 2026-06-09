"""Unit tests for the 4 pure grading functions — Bundle B Phase B.6 (F4.2).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.2

Each grader is pure (no I/O) and tested in isolation here. The orchestrator
integration is covered in test_eval_runner.py.

Contract (dispatcher brief):
  grade_price   -> bool   within [min*0.85, max*1.15]
  grade_specs   -> float  fraction matched (case/unit-tolerant)
  grade_winner  -> bool   index equality vs deterministic winner
  grade_factual -> bool   no forbidden_fact substring (case-insensitive)
  weighted pass: price .30 / specs .30 / winner .25 / factual .15
"""
from __future__ import annotations

import pytest

from scripts import eval_runner as er


# ---------------------------------------------------------------------------
# grade_price
# ---------------------------------------------------------------------------

def test_price_inside_band_passes():
    assert er.grade_price(320.0, {"min": 290, "max": 400}) is True


def test_price_at_lower_tolerance_edge_passes():
    # min=100 → lower bound 85.0; 85 passes, 84.9 fails.
    assert er.grade_price(85.0, {"min": 100, "max": 200}) is True
    assert er.grade_price(84.9, {"min": 100, "max": 200}) is False


def test_price_at_upper_tolerance_edge_passes():
    # max=200 → upper bound 230.0; 230 passes, 230.1 fails.
    assert er.grade_price(230.0, {"min": 100, "max": 200}) is True
    assert er.grade_price(230.1, {"min": 100, "max": 200}) is False


def test_price_none_actual_fails_when_band_authored():
    assert er.grade_price(None, {"min": 100, "max": 200}) is False


def test_price_empty_expected_is_vacuously_true():
    assert er.grade_price(None, {}) is True
    assert er.grade_price(123.0, {}) is True


def test_price_partial_band_missing_max_is_vacuous():
    # Defensive: a malformed band missing a bound is treated as un-authored.
    assert er.grade_price(None, {"min": 100}) is True


# ---------------------------------------------------------------------------
# grade_specs
# ---------------------------------------------------------------------------

def test_specs_all_match_returns_one():
    actual = {"storage": "128GB", "os": "iOS"}
    expected = {"storage": "128GB", "os": "iOS"}
    assert er.grade_specs(actual, expected) == 1.0


def test_specs_unit_spacing_tolerant():
    # "128GB" gold vs "128 GB" actual must match.
    assert er.grade_specs({"storage": "128 GB"}, {"storage": "128GB"}) == 1.0
    assert er.grade_specs({"storage": "128GB"}, {"storage": "128 GB"}) == 1.0


def test_specs_case_insensitive():
    assert er.grade_specs({"os": "android"}, {"os": "Android"}) == 1.0


def test_specs_substring_match():
    # gold "iOS" is a substring of actual "iOS 17" → match.
    assert er.grade_specs({"os": "iOS 17"}, {"os": "iOS"}) == 1.0


def test_specs_half_match_returns_half():
    actual = {"storage": "128GB", "os": "Android"}
    expected = {"storage": "128GB", "os": "iOS"}
    assert er.grade_specs(actual, expected) == 0.5


def test_specs_missing_key_counts_as_miss():
    assert er.grade_specs({"storage": "128GB"}, {"storage": "128GB", "os": "iOS"}) == 0.5


def test_specs_empty_expected_returns_one():
    assert er.grade_specs({"anything": "x"}, {}) == 1.0
    assert er.grade_specs(None, {}) == 1.0


def test_specs_none_actual_with_authored_expected_is_zero():
    assert er.grade_specs(None, {"os": "iOS"}) == 0.0


# ---------------------------------------------------------------------------
# grade_winner
# ---------------------------------------------------------------------------

def test_winner_match_passes():
    assert er.grade_winner(0, 0) is True
    assert er.grade_winner(1, 1) is True


def test_winner_mismatch_fails():
    assert er.grade_winner(0, 1) is False
    assert er.grade_winner(1, 0) is False


def test_winner_none_actual_fails():
    assert er.grade_winner(None, 0) is False


def test_winner_expected_none_is_vacuously_true():
    assert er.grade_winner(0, None) is True
    assert er.grade_winner(None, None) is True


# ---------------------------------------------------------------------------
# grade_factual
# ---------------------------------------------------------------------------

def test_factual_no_forbidden_fact_passes():
    text = "The iPhone wins on camera and ecosystem."
    assert er.grade_factual(text, ["8K video recording", "USB-C 3.2 Gen 2"]) is True


def test_factual_forbidden_fact_present_fails():
    text = "This phone supports 8K video recording natively."
    assert er.grade_factual(text, ["8K video recording"]) is False


def test_factual_case_insensitive_detection():
    text = "Apple Intelligence on iPhone 15 base model."
    assert er.grade_factual(text, ["apple intelligence on iphone 15 base"]) is False


def test_factual_empty_forbidden_list_passes():
    assert er.grade_factual("anything goes here", []) is True


def test_factual_empty_text_passes():
    assert er.grade_factual("", ["8K video"]) is True


# ---------------------------------------------------------------------------
# weighted_pass_score
# ---------------------------------------------------------------------------

def test_weights_sum_to_one():
    assert sum(er.AXIS_WEIGHTS.values()) == pytest.approx(1.0)


def test_weighted_all_pass_is_one():
    assert er.weighted_pass_score(True, 1.0, True, True) == pytest.approx(1.0)


def test_weighted_all_fail_is_zero():
    assert er.weighted_pass_score(False, 0.0, False, False) == pytest.approx(0.0)


def test_weighted_winner_only_fail_drops_by_winner_weight():
    # Everything passes except winner (.25 weight) → 0.75.
    assert er.weighted_pass_score(True, 1.0, False, True) == pytest.approx(0.75)


def test_weighted_specs_half_contributes_half_its_weight():
    # price+winner+factual pass (.70), specs=0.5 → +0.15 → 0.85.
    assert er.weighted_pass_score(True, 0.5, True, True) == pytest.approx(0.85)


def test_query_pass_threshold_is_080():
    assert er.QUERY_PASS_THRESHOLD == 0.80

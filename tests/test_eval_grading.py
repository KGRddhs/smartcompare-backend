"""Unit tests for the 4 pure grading functions  -  Bundle B Phase B.6 (F4.2).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.2

Each grader is pure (no I/O) and tested in isolation here. The orchestrator
integration is covered in test_eval_runner.py.

Contract (dispatcher brief):
  grade_price   -> bool   within [min*0.85, max*1.15]
  grade_specs   -> float  fraction matched (case/unit-tolerant)
  grade_winner  -> bool   index equality vs deterministic winner
  grade_factual -> bool   no forbidden_fact substring (case-insensitive)
  weighted pass: canonical weights from gold _metadata.axis_weights
                 (currently price .25 / specs .25 / winner .30 / factual .20)
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
    # min=100 -> lower bound 85.0; 85 passes, 84.9 fails.
    assert er.grade_price(85.0, {"min": 100, "max": 200}) is True
    assert er.grade_price(84.9, {"min": 100, "max": 200}) is False


def test_price_at_upper_tolerance_edge_passes():
    # max=200 -> upper bound 230.0; 230 passes, 230.1 fails.
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
    # gold "iOS" is a complete token of actual "iOS 17" -> match.
    assert er.grade_specs({"os": "iOS 17"}, {"os": "iOS"}) == 1.0


def test_specs_boundary_rejects_numeric_substring():
    # F3 cross-QA finding: '55' must NOT be credited inside '155 cm'.
    assert er.grade_specs({"display": "155 cm"}, {"display": "55"}) == 0.0


def test_specs_boundary_rejects_partial_capacity():
    # '8GB' must NOT be credited inside '128GB'.
    assert er.grade_specs({"storage": "128GB"}, {"storage": "8GB"}) == 0.0


def test_specs_unit_spacing_survives_boundary_fix():
    # The tolerances the boundary fix must NOT break.
    assert er.grade_specs({"storage": "8 GB"}, {"storage": "8GB"}) == 1.0
    assert er.grade_specs({"storage": "128 GB storage"}, {"storage": "128GB"}) == 1.0


def test_specs_boundary_rejects_more_numeric_substrings():
    # Further boundary rejects beyond F3's two: a number inside a longer
    # number must not credit (e.g. SPF '46' inside '146').
    assert er.grade_specs({"spf": "146"}, {"spf": "46"}) == 0.0
    assert er.grade_specs({"battery": "1500 mAh"}, {"battery": "500"}) == 0.0


def test_specs_multi_word_complete_value_matches():
    # A complete multi-word expected value found as a run in the actual
    # matches; a longer expected than the actual does not.
    assert er.grade_specs({"type": "Whey Protein Isolate"}, {"type": "Whey Protein"}) == 1.0
    assert er.grade_specs({"type": "Whey Protein"}, {"type": "Whey Protein Isolate"}) == 0.0


def test_specs_regex_special_chars_are_literal():
    # Spec values carry regex metacharacters ('1.5T' AC capacity, 'A+'
    # grade, 'SPF50+'). re.escape must treat them literally — otherwise '.'
    # would match any char and credit '1.5' inside '145'.
    assert er.grade_specs({"cap": "1.5T split AC"}, {"cap": "1.5T"}) == 1.0
    assert er.grade_specs({"cap": "145 units"}, {"cap": "1.5"}) == 0.0
    assert er.grade_specs({"grade": "A+ rated"}, {"grade": "A+"}) == 1.0


def test_specs_empty_expected_value_does_not_credit():
    # The boundary rewrite changed empty-expected from "matches everything"
    # (old substring free credit) to "matches nothing" — the safer
    # semantics. No gold entry has an empty spec value, but pin the contract.
    assert er.grade_specs({"k": "128GB"}, {"k": ""}) == 0.0
    assert er.grade_specs({"k": "128GB"}, {"k": "   "}) == 0.0


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


def test_fallback_constant_matches_gold_current_values():
    # The module-level AXIS_WEIGHTS is the FALLBACK, mirroring the gold
    # file's current _metadata.axis_weights (short-key form). Canonical
    # source is the gold file; this constant is only used when metadata is
    # absent/malformed.
    assert er.AXIS_WEIGHTS == {"price": 0.25, "specs": 0.25, "winner": 0.30, "factual": 0.20}


def test_weighted_all_pass_is_one():
    assert er.weighted_pass_score(True, 1.0, True, True) == pytest.approx(1.0)


def test_weighted_all_fail_is_zero():
    assert er.weighted_pass_score(False, 0.0, False, False) == pytest.approx(0.0)


def test_weighted_winner_only_fail_drops_by_winner_weight():
    # Everything passes except winner (.30 weight under canonical gold
    # weights) -> 0.70.
    assert er.weighted_pass_score(True, 1.0, False, True) == pytest.approx(0.70)


def test_weighted_specs_half_contributes_half_its_weight():
    # price+winner+factual pass (.25+.30+.20=.75), specs=0.5 -> +.125 -> 0.875.
    assert er.weighted_pass_score(True, 0.5, True, True) == pytest.approx(0.875)


def test_weighted_accepts_explicit_weights_override():
    # weighted_pass_score takes an optional weights dict; passing the old
    # plan-draft weights reproduces the old result, proving it's threaded.
    plan_draft = {"price": 0.30, "specs": 0.30, "winner": 0.25, "factual": 0.15}
    assert er.weighted_pass_score(True, 1.0, False, True, weights=plan_draft) == pytest.approx(0.75)


def test_query_pass_threshold_is_080():
    assert er.QUERY_PASS_THRESHOLD == 0.80


# ---------------------------------------------------------------------------
# load_axis_weights  -  canonical weights from gold _metadata (F4 correction)
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

_GOLD_PATH = Path(__file__).resolve().parent.parent / "data" / "validation_gold_truth.json"

_LONG = {
    "price_accuracy": 0.25,
    "specs_correctness": 0.25,
    "winner_correctness": 0.30,
    "factual_claim_integrity": 0.20,
}


def test_load_axis_weights_maps_long_keys_to_short():
    weights = er.load_axis_weights({"_metadata": {"axis_weights": dict(_LONG)}})
    assert weights == {"price": 0.25, "specs": 0.25, "winner": 0.30, "factual": 0.20}


def test_load_axis_weights_real_gold_file_is_canonical():
    import json
    import io
    gold = json.loads(io.open(_GOLD_PATH, encoding="utf-8").read())
    weights = er.load_axis_weights(gold)
    assert weights == {"price": 0.25, "specs": 0.25, "winner": 0.30, "factual": 0.20}
    assert sum(weights.values()) == pytest.approx(1.0)


def test_load_axis_weights_absent_metadata_falls_back_with_warning(caplog):
    with caplog.at_level("WARNING"):
        weights = er.load_axis_weights({"_metadata": {}})
    assert weights == er.AXIS_WEIGHTS
    assert any("axis_weights" in r.message and "fallback" in r.message.lower()
               for r in caplog.records)


def test_load_axis_weights_no_metadata_key_falls_back():
    weights = er.load_axis_weights({})
    assert weights == er.AXIS_WEIGHTS


def test_load_axis_weights_wrong_keys_hard_fails():
    # PRESENT but malformed (unknown key) -> ValueError, not silent fallback.
    bad = {"_metadata": {"axis_weights": {"price_accuracy": 0.5, "bogus_axis": 0.5}}}
    with pytest.raises(ValueError):
        er.load_axis_weights(bad)


def test_load_axis_weights_missing_one_axis_hard_fails():
    # Only 3 of 4 axes present -> ValueError (not exactly the 4-key set).
    bad = {"_metadata": {"axis_weights": {
        "price_accuracy": 0.34, "specs_correctness": 0.33, "winner_correctness": 0.33}}}
    with pytest.raises(ValueError):
        er.load_axis_weights(bad)


def test_load_axis_weights_bad_sum_hard_fails():
    bad = {"_metadata": {"axis_weights": {
        "price_accuracy": 0.5, "specs_correctness": 0.5,
        "winner_correctness": 0.5, "factual_claim_integrity": 0.5}}}
    with pytest.raises(ValueError):
        er.load_axis_weights(bad)


def test_load_axis_weights_sum_within_epsilon_passes():
    # 0.25+0.25+0.30+0.20 with a 1e-9 perturbation still validates.
    w = {"_metadata": {"axis_weights": {
        "price_accuracy": 0.25, "specs_correctness": 0.25,
        "winner_correctness": 0.30, "factual_claim_integrity": 0.20 + 1e-9}}}
    weights = er.load_axis_weights(w)
    assert weights["factual"] == pytest.approx(0.20)

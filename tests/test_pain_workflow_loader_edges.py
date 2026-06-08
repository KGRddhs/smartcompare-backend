"""Tests for A-L4.2 — pain_workflow_loader edge paths.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.2

Closes coverage on cohort-key normalisation edge cases, file-missing
fallbacks, JSON parse failure handling, the TL;DR-floor injection, and
the cohort-top-up branch when a cohort has < 3 non-zero workflows.
"""

import json
from pathlib import Path

import pytest

from app.services import pain_workflow_loader as pwl


# ---------------------------------------------------------------------------
# _cohort_key — every reject branch
# ---------------------------------------------------------------------------

def test_cohort_key_none_input():
    assert pwl._cohort_key(None) is None


def test_cohort_key_empty_dict():
    assert pwl._cohort_key({}) is None


def test_cohort_key_missing_age():
    assert pwl._cohort_key({"gender": "Female", "nationality": "Bahraini"}) is None


def test_cohort_key_missing_gender():
    assert pwl._cohort_key({"age_group": "25-34", "nationality": "Bahraini"}) is None


def test_cohort_key_missing_nationality():
    assert pwl._cohort_key({"age_group": "25-34", "gender": "Female"}) is None


def test_cohort_key_unknown_gender():
    assert pwl._cohort_key({"age_group": "25-34", "gender": "Other", "nationality": "Bahraini"}) is None


def test_cohort_key_unknown_nationality():
    assert pwl._cohort_key({"age_group": "25-34", "gender": "Female", "nationality": "Saudi"}) is None


def test_cohort_key_canonical_bahraini():
    assert pwl._cohort_key({"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}) == "25-34_female_bahraini"


def test_cohort_key_canonical_non_bahraini_hyphen():
    assert pwl._cohort_key({"age_group": "35-44", "gender": "Male", "nationality": "Non-Bahraini"}) == "35-44_male_non_bahraini"


def test_cohort_key_canonical_non_bahraini_underscore():
    assert pwl._cohort_key({"age_group": "18-24", "gender": "Female", "nationality": "non_bahraini"}) == "18-24_female_non_bahraini"


def test_cohort_key_canonical_expat_alias():
    assert pwl._cohort_key({"age_group": "45+", "gender": "Male", "nationality": "expat"}) == "45+_male_non_bahraini"


def test_cohort_key_whitespace_stripped():
    assert pwl._cohort_key({"age_group": "  25-34  ", "gender": " Female ", "nationality": " Bahraini "}) == "25-34_female_bahraini"


# ---------------------------------------------------------------------------
# File-missing + JSON parse failure paths
# ---------------------------------------------------------------------------

def test_load_pain_priors_missing_file_returns_none(monkeypatch, tmp_path):
    fake = tmp_path / "nope.json"
    monkeypatch.setattr(pwl, "_PAIN_FILE", fake)
    pwl.reset_cache()
    assert pwl._load_pain_priors() is None


def test_load_pain_priors_corrupt_file_returns_none(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(pwl, "_PAIN_FILE", bad)
    pwl.reset_cache()
    assert pwl._load_pain_priors() is None


def test_load_style_priors_missing_file_returns_none(monkeypatch, tmp_path):
    fake = tmp_path / "nope.json"
    monkeypatch.setattr(pwl, "_STYLE_FILE", fake)
    pwl.reset_cache()
    assert pwl._load_style_priors() is None


def test_load_style_priors_corrupt_file_returns_none(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(pwl, "_STYLE_FILE", bad)
    pwl.reset_cache()
    assert pwl._load_style_priors() is None


def test_top_pain_workflows_returns_empty_when_priors_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(pwl, "_PAIN_FILE", tmp_path / "nope.json")
    pwl.reset_cache()
    assert pwl.top_pain_workflows({"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}) == []


def test_build_pain_workflow_block_empty_when_priors_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(pwl, "_PAIN_FILE", tmp_path / "nope.json")
    pwl.reset_cache()
    assert pwl.build_pain_workflow_block({"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}) == ""


def test_top_decision_style_returns_none_when_priors_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(pwl, "_STYLE_FILE", tmp_path / "nope.json")
    pwl.reset_cache()
    assert pwl.top_decision_style({"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}) is None


def test_build_decision_style_block_empty_when_priors_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(pwl, "_STYLE_FILE", tmp_path / "nope.json")
    pwl.reset_cache()
    assert pwl.build_decision_style_block({"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}) == ""


# ---------------------------------------------------------------------------
# TL;DR floor — decision_speed always appended when not in top-3
# ---------------------------------------------------------------------------

def test_tldr_workflow_appended_when_not_in_top_3(monkeypatch, tmp_path):
    """Cohort top-3 that excludes decision_speed must still get the TL;DR
    instruction appended at position 4."""
    # Synth priors where decision_speed has weight 0 in the cohort but is
    # still in the workflow list.
    synth_priors = {
        "workflows": [
            {"rank": i, "name": name, "description": "d", "prompt_instruction": "i", "survey_weight": 0.5, "per_cohort_weight": {"25-34_female_bahraini": 0.5 if name != "decision_speed" else 0.0}}
            for i, name in enumerate(
                ["close_option_paralysis", "value_budget_uncertainty", "too_many_specs", "trust_paralysis", "post_decision_regret", "brand_loyalty_vs_evidence", "warranty_aftersales_missing", "decision_speed"],
                start=1,
            )
        ]
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(synth_priors), encoding="utf-8")
    monkeypatch.setattr(pwl, "_PAIN_FILE", f)
    pwl.reset_cache()

    cohort = {"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}
    block = pwl.build_pain_workflow_block(cohort)
    # 3 top-of-cohort + decision_speed = 4 numbered items
    assert "1. **d**" in block
    assert "4. **d**" in block


def test_tldr_not_double_injected_when_already_in_top_3(monkeypatch, tmp_path):
    """If decision_speed is already in cohort top-3 it must NOT be appended
    again (no duplicate floor)."""
    synth_priors = {
        "workflows": [
            {"rank": 1, "name": "decision_speed", "description": "ds", "prompt_instruction": "tldr instr", "survey_weight": 0.9, "per_cohort_weight": {"25-34_female_bahraini": 0.9}},
            {"rank": 2, "name": "close_option_paralysis", "description": "cop", "prompt_instruction": "tie-break instr", "survey_weight": 0.7, "per_cohort_weight": {"25-34_female_bahraini": 0.7}},
            {"rank": 3, "name": "too_many_specs", "description": "tms", "prompt_instruction": "max 3 instr", "survey_weight": 0.5, "per_cohort_weight": {"25-34_female_bahraini": 0.5}},
            {"rank": 4, "name": "value_budget_uncertainty", "description": "vbu", "prompt_instruction": "value", "survey_weight": 0.0, "per_cohort_weight": {}},
        ]
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(synth_priors), encoding="utf-8")
    monkeypatch.setattr(pwl, "_PAIN_FILE", f)
    pwl.reset_cache()

    cohort = {"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}
    block = pwl.build_pain_workflow_block(cohort)
    # Should have only 3 numbered items, not 4.
    assert "1. " in block
    assert "2. " in block
    assert "3. " in block
    assert "4. " not in block


# ---------------------------------------------------------------------------
# Cohort top-up branch — when cohort has < 3 non-zero workflows
# ---------------------------------------------------------------------------

def test_cohort_top_up_with_global_when_under_3(monkeypatch, tmp_path):
    """Cohort with only 1 non-zero workflow weight must be topped up to 3
    using global rank order (not return just 1)."""
    synth_priors = {
        "workflows": [
            {"rank": 1, "name": "close_option_paralysis", "description": "x", "prompt_instruction": "i1", "survey_weight": 0.0, "per_cohort_weight": {}},
            {"rank": 2, "name": "value_budget_uncertainty", "description": "x", "prompt_instruction": "i2", "survey_weight": 0.0, "per_cohort_weight": {"25-34_female_bahraini": 0.5}},
            {"rank": 3, "name": "too_many_specs", "description": "x", "prompt_instruction": "i3", "survey_weight": 0.0, "per_cohort_weight": {}},
            {"rank": 4, "name": "trust_paralysis", "description": "x", "prompt_instruction": "i4", "survey_weight": 0.0, "per_cohort_weight": {}},
            {"rank": 5, "name": "decision_speed", "description": "x", "prompt_instruction": "i5", "survey_weight": 0.0, "per_cohort_weight": {}},
        ]
    }
    f = tmp_path / "p.json"
    f.write_text(json.dumps(synth_priors), encoding="utf-8")
    monkeypatch.setattr(pwl, "_PAIN_FILE", f)
    pwl.reset_cache()

    cohort = {"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}
    chosen = pwl.top_pain_workflows(cohort)
    # 3 chosen — 1 cohort-weighted + 2 global-rank-topped-up.
    assert len(chosen) == 3
    # The cohort one (value_budget_uncertainty) ranks first.
    assert chosen[0]["name"] == "value_budget_uncertainty"


# ---------------------------------------------------------------------------
# Decision style fallback to _global when cohort absent
# ---------------------------------------------------------------------------

def test_top_decision_style_falls_back_to_global_when_cohort_unknown():
    """Cohort key not present in style priors should fall back to _global."""
    style = pwl.top_decision_style({"age_group": "99-100", "gender": "Female", "nationality": "Bahraini"})
    # _global is always present — non-None return expected
    assert style is not None


def test_top_decision_style_with_no_cohort_input_uses_global():
    style = pwl.top_decision_style(None)
    assert style is not None
    assert style in {"show_all_details", "show_only_main_differences", "show_2_or_3_options", "suggest_one_best"}


# ---------------------------------------------------------------------------
# reset_cache visible side-effect
# ---------------------------------------------------------------------------

def test_reset_cache_drops_cached_data(monkeypatch, tmp_path):
    """After reset, swapped data file is re-loaded."""
    # First load with real priors
    pwl.reset_cache()
    real_priors = pwl._load_pain_priors()
    assert real_priors is not None
    assert len(real_priors["workflows"]) == 8

    # Swap to a synthesised 2-workflow file + reset.
    synth = tmp_path / "p.json"
    synth.write_text(json.dumps({"workflows": [{"rank": 1, "name": "x"}, {"rank": 2, "name": "y"}]}), encoding="utf-8")
    monkeypatch.setattr(pwl, "_PAIN_FILE", synth)
    pwl.reset_cache()
    assert len(pwl._load_pain_priors()["workflows"]) == 2

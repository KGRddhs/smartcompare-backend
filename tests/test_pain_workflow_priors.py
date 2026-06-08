"""Tests for A-L4.1 — pain_workflow_priors + decision_style_priors ETL output.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.1
Design: docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6

These tests validate the shape and invariants of the two priors JSON files
emitted by scripts/etl_survey_to_priors.py. They do NOT require live survey
CSVs at test time — they read the checked-in JSON outputs.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAIN_FILE = REPO_ROOT / "data" / "pain_workflow_priors.json"
STYLE_FILE = REPO_ROOT / "data" / "decision_style_priors.json"


# ---------------------------------------------------------------------------
# pain_workflow_priors.json
# ---------------------------------------------------------------------------

def test_pain_workflow_file_exists():
    assert PAIN_FILE.exists(), f"missing {PAIN_FILE}"


def test_pain_workflow_priors_has_8_workflows():
    priors = json.loads(PAIN_FILE.read_text(encoding="utf-8"))
    assert "workflows" in priors
    assert len(priors["workflows"]) == 8


def test_pain_workflow_priors_first_workflow_is_close_option_paralysis():
    priors = json.loads(PAIN_FILE.read_text(encoding="utf-8"))
    first = priors["workflows"][0]
    assert first["rank"] == 1
    assert first["name"] == "close_option_paralysis"
    assert "prompt_instruction" in first
    assert isinstance(first["prompt_instruction"], str)
    assert len(first["prompt_instruction"]) >= 40


def test_pain_workflow_priors_all_workflows_have_required_fields():
    priors = json.loads(PAIN_FILE.read_text(encoding="utf-8"))
    expected_ranks = list(range(1, 9))
    seen_ranks = sorted(w["rank"] for w in priors["workflows"])
    assert seen_ranks == expected_ranks

    expected_names = {
        "close_option_paralysis",
        "too_many_specs",
        "value_budget_uncertainty",
        "trust_paralysis",
        "post_decision_regret",
        "brand_loyalty_vs_evidence",
        "warranty_aftersales_missing",
        "decision_speed",
    }
    seen_names = {w["name"] for w in priors["workflows"]}
    assert seen_names == expected_names

    for w in priors["workflows"]:
        assert "rank" in w
        assert "name" in w
        assert "prompt_instruction" in w
        assert "survey_weight" in w  # share of respondents triggering this workflow
        assert "description" in w
        assert isinstance(w["survey_weight"], (int, float))
        assert 0.0 <= w["survey_weight"] <= 1.0


def test_pain_workflow_priors_no_scary_copy():
    """Per design § 6 + memory/feedback_no_estimated_word_in_ui.md — verdict
    prompt injection MUST NOT carry scary vocabulary into the model prompt
    that could leak through into user-facing text."""
    priors = json.loads(PAIN_FILE.read_text(encoding="utf-8"))
    forbidden_en = ["couldn't", "Couldn't", "try again", "Try again", "Failed to", "failed to"]
    forbidden_ar = ["تعذر", "فشل"]
    for w in priors["workflows"]:
        instr = w["prompt_instruction"]
        for word in forbidden_en + forbidden_ar:
            assert word not in instr, f"workflow {w['name']!r} prompt_instruction contains forbidden vocab {word!r}"


def test_pain_workflow_priors_per_cohort_weights_present():
    """Each workflow stores a per-cohort weight dict {cohort_key: weight} for
    optional per-cohort ranking inside build_verdict_prompt."""
    priors = json.loads(PAIN_FILE.read_text(encoding="utf-8"))
    for w in priors["workflows"]:
        assert "per_cohort_weight" in w
        assert isinstance(w["per_cohort_weight"], dict)


def test_pain_workflow_priors_metadata_block():
    priors = json.loads(PAIN_FILE.read_text(encoding="utf-8"))
    assert "metadata" in priors
    meta = priors["metadata"]
    assert "source" in meta  # documents which CSVs fed the ETL
    assert "generated_at" in meta
    assert "total_responses" in meta
    assert meta["total_responses"] >= 400


# ---------------------------------------------------------------------------
# decision_style_priors.json
# ---------------------------------------------------------------------------

def test_decision_style_file_exists():
    assert STYLE_FILE.exists(), f"missing {STYLE_FILE}"


def test_decision_style_priors_global_block_present():
    """Survey n is too small for many fine-grained cohort buckets — the file
    must always carry a `_global` fallback summing to 1.0."""
    priors = json.loads(STYLE_FILE.read_text(encoding="utf-8"))
    assert "_global" in priors
    g = priors["_global"]
    assert sum(g.values()) == pytest.approx(1.0, abs=0.01)


def test_decision_style_priors_styles_are_canonical():
    priors = json.loads(STYLE_FILE.read_text(encoding="utf-8"))
    expected_styles = {
        "show_all_details",
        "show_only_main_differences",
        "show_2_or_3_options",
        "suggest_one_best",
    }
    for cohort_key, styles in priors.items():
        if cohort_key == "metadata":
            continue
        assert set(styles.keys()) == expected_styles, f"{cohort_key} has wrong style keys: {set(styles.keys())}"
        assert sum(styles.values()) == pytest.approx(1.0, abs=0.01), f"{cohort_key} styles don't sum to 1.0"


def test_decision_style_priors_metadata_block():
    priors = json.loads(STYLE_FILE.read_text(encoding="utf-8"))
    assert "metadata" in priors
    meta = priors["metadata"]
    assert "source" in meta
    assert "generated_at" in meta
    assert "total_responses" in meta

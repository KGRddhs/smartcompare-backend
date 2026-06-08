"""Tests for A-L4.1 — etl_survey_to_priors.py internal helpers.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.1

Coverage gaps the integration test (test_pain_workflow_priors.py) leaves
unfilled: cohort key construction, normalisation helpers, aggregation,
and the build_* JSON-emitter shape from synthetic input. End-to-end run
on real CSVs is exercised in CI by `python scripts/etl_survey_to_priors.py`.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "etl_survey_to_priors.py"


def _load_etl_module():
    spec = importlib.util.spec_from_file_location("etl_survey_to_priors", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["etl_survey_to_priors"] = mod
    spec.loader.exec_module(mod)
    return mod


etl = _load_etl_module()


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def test_normalise_describe_bahraini():
    assert etl._normalise_describe("Bahraini") == "Bahraini"
    assert etl._normalise_describe("بحريني - بحرينية") == "Bahraini"


def test_normalise_describe_non_bahraini():
    assert etl._normalise_describe("Non-Bahraini resident in Bahrain") == "Non-Bahraini"
    assert etl._normalise_describe("مقيم/مقيمة غير بحريني - ة في البحرين") == "Non-Bahraini"


def test_normalise_describe_prefer_not_to_say():
    assert etl._normalise_describe("Prefer not to say") == "_unknown"
    assert etl._normalise_describe("أفضل عدم الإجابة") == "_unknown"


def test_normalise_describe_unrecognised():
    assert etl._normalise_describe("Saudi") == "_unknown"
    assert etl._normalise_describe("") == "_unknown"


def test_normalise_age_canonical():
    for age in ("18-24", "25-34", "35-44", "45+"):
        assert etl._normalise_age(age) == age


def test_normalise_age_unrecognised():
    assert etl._normalise_age("99-100") == ""
    assert etl._normalise_age("") == ""


def test_normalise_gender_canonical():
    assert etl._normalise_gender("Female") == "Female"
    assert etl._normalise_gender("Male") == "Male"
    assert etl._normalise_gender("أنثى") == "Female"
    assert etl._normalise_gender("ذكر") == "Male"


def test_normalise_gender_unknown():
    assert etl._normalise_gender("Prefer not to say") == "_unknown"
    assert etl._normalise_gender("Prefer to self-describe") == "_unknown"
    assert etl._normalise_gender("Other") == "_unknown"


# ---------------------------------------------------------------------------
# _cohort_key
# ---------------------------------------------------------------------------

def test_cohort_key_canonical():
    assert etl._cohort_key("Bahraini", "25-34", "Female") == "25-34_female_bahraini"


def test_cohort_key_non_bahraini_normalised():
    assert etl._cohort_key("Non-Bahraini", "35-44", "Male") == "35-44_male_non_bahraini"


def test_cohort_key_missing_age_returns_none():
    assert etl._cohort_key("Bahraini", "", "Female") is None


def test_cohort_key_unknown_field_returns_none():
    assert etl._cohort_key("_unknown", "25-34", "Female") is None
    assert etl._cohort_key("Bahraini", "25-34", "_unknown") is None


# ---------------------------------------------------------------------------
# _split_multi
# ---------------------------------------------------------------------------

def test_split_multi_basic():
    assert etl._split_multi("Price,Quality - Reliability") == ["Price", "Quality - Reliability"]


def test_split_multi_empty_string():
    assert etl._split_multi("") == []


def test_split_multi_trims_whitespace():
    assert etl._split_multi(" Price , Value for money ") == ["Price", "Value for money"]


def test_split_multi_drops_empty_tokens():
    assert etl._split_multi("Price,,Value") == ["Price", "Value"]


# ---------------------------------------------------------------------------
# _row_get — synonyms across English + Arabic columns
# ---------------------------------------------------------------------------

def test_row_get_english_column():
    row = {"Q7 At what point did the choice feel hardest?": "When I found too many options"}
    assert etl._row_get(row, "q7") == "When I found too many options"


def test_row_get_arabic_fallback():
    row = {"في أي مرحلة حسّيت إن الاختيار كان أصعب شي؟": "لما لقيت خيارات كثيرة"}
    assert etl._row_get(row, "q7") == "لما لقيت خيارات كثيرة"


def test_row_get_returns_empty_when_no_match():
    assert etl._row_get({"unrelated": "value"}, "q7") == ""


def test_row_get_whitespace_stripped():
    row = {"What is your age group?": "  25-34  "}
    assert etl._row_get(row, "age") == "25-34"


# ---------------------------------------------------------------------------
# aggregate() — synthetic 3-row input
# ---------------------------------------------------------------------------

def _row_full(q7, diff, style, describe, age, gender, lang="English", gov="Capital Governorate"):
    return {
        "Q7 At what point did the choice feel hardest?": q7,
        "What were the top 2 difficulties you faced when trying to choose the right option?": diff,
        "Which style of assistance or advice would you prefer to make choosing the right option more clear?": style,
        "Which of the following best describes you?": describe,
        "What is your age group?": age,
        "What is your gender?": gender,
        "Which language do you usually use when searching for products or services?": lang,
        "Which governorate do you mainly live in?": gov,
    }


def test_aggregate_simple_row():
    rows = [
        _row_full(
            q7="When I was comparing 2 or 3 close options",
            diff="Price,Quality - Reliability",
            style="Show me all details",
            describe="Bahraini",
            age="25-34",
            gender="Female",
        ),
    ]
    agg = etl.aggregate(rows)
    assert agg["total_responses"] == 1
    assert agg["total_with_pain_signal"] == 1
    # Q7 → close_option_paralysis; Price → value_budget_uncertainty; Quality → trust_paralysis
    assert agg["workflow_counts"]["close_option_paralysis"] == 1
    assert agg["workflow_counts"]["value_budget_uncertainty"] == 1
    assert agg["workflow_counts"]["trust_paralysis"] == 1
    # Cohort recorded
    assert "25-34_female_bahraini" in agg["workflow_per_cohort"]
    # Style aggregated
    assert agg["style_global"]["show_all_details"] == 1


def test_aggregate_no_pain_signal_row():
    rows = [
        _row_full(
            q7="It did not feel hard",
            diff="Nothing made it hard",
            style="Suggest one best option with a reason",
            describe="Bahraini",
            age="18-24",
            gender="Male",
        ),
    ]
    agg = etl.aggregate(rows)
    assert agg["total_responses"] == 1
    assert agg["total_with_pain_signal"] == 0  # _no_pain doesn't count
    assert agg["style_global"]["suggest_one_best"] == 1


def test_aggregate_dedups_q7_overlap_with_difficulties():
    """A respondent whose Q7 → too_many_specs AND has 'Too many options' in
    difficulties should only count once."""
    rows = [
        _row_full(
            q7="When I found too many options",
            diff="Too many options,Price",
            style="Show me only the main differences",
            describe="Bahraini",
            age="25-34",
            gender="Female",
        ),
    ]
    agg = etl.aggregate(rows)
    # too_many_specs counted once (Q7), value_budget_uncertainty once (Price)
    assert agg["workflow_counts"]["too_many_specs"] == 1
    assert agg["workflow_counts"]["value_budget_uncertainty"] == 1


def test_aggregate_unknown_demographics_skip_cohort():
    """A respondent with 'Prefer not to say' demographics still counts toward
    workflow_counts but doesn't populate workflow_per_cohort."""
    rows = [
        _row_full(
            q7="When I was comparing 2 or 3 close options",
            diff="",
            style="Show me all details",
            describe="Prefer not to say",
            age="",
            gender="Prefer not to say",
        ),
    ]
    agg = etl.aggregate(rows)
    assert agg["workflow_counts"]["close_option_paralysis"] == 1
    assert agg["workflow_per_cohort"] == {}  # No cohort match


def test_aggregate_arabic_row():
    rows = [
        {
            "في أي مرحلة حسّيت إن الاختيار كان أصعب شي؟": "لما كنت أقارن بين خيارين أو ثلاثة قريبين من بعض",
            "شنو أكثر صعوبتين واجهتهم؟ اختر حتى 2": "السعر,الجودة - الاعتمادية",
            "لما تقارن بين خيارات متشابهة، شنو نوع المساعدة اللي تفضل تنعرض لك؟": "تقترح لي أفضل خيار مع توضيح السبب",
            "أي وحدة تصفك أكثر؟": "بحريني - بحرينية",
            "ما هي فئتك العمرية؟": "25-34",
            "ما هو جنسك؟": "أنثى",
        },
    ]
    agg = etl.aggregate(rows)
    assert agg["workflow_counts"]["close_option_paralysis"] == 1
    assert agg["workflow_counts"]["value_budget_uncertainty"] == 1
    assert agg["workflow_counts"]["trust_paralysis"] == 1
    assert "25-34_female_bahraini" in agg["workflow_per_cohort"]
    assert agg["style_global"]["suggest_one_best"] == 1


# ---------------------------------------------------------------------------
# build_pain_workflow_priors — synthetic aggregate
# ---------------------------------------------------------------------------

def test_build_pain_workflow_priors_ranks_by_weight():
    agg = {
        "total_responses": 10,
        "total_with_pain_signal": 10,
        "workflow_counts": {
            "close_option_paralysis": 8,
            "value_budget_uncertainty": 5,
            "too_many_specs": 3,
            "trust_paralysis": 0,
        },
        "workflow_per_cohort": {},
    }
    priors = etl.build_pain_workflow_priors(agg, sources=["test.csv"])
    assert len(priors["workflows"]) == 8
    # Top 3 ranked by weight
    assert priors["workflows"][0]["name"] == "close_option_paralysis"
    assert priors["workflows"][0]["rank"] == 1
    assert priors["workflows"][0]["survey_weight"] == 0.8
    assert priors["workflows"][1]["name"] == "value_budget_uncertainty"
    assert priors["workflows"][2]["name"] == "too_many_specs"


def test_build_pain_workflow_priors_metadata_block():
    agg = {"total_responses": 100, "total_with_pain_signal": 85, "workflow_counts": {}, "workflow_per_cohort": {}}
    priors = etl.build_pain_workflow_priors(agg, sources=["a.csv", "b.csv"])
    meta = priors["metadata"]
    assert meta["source"] == ["a.csv", "b.csv"]
    assert meta["total_responses"] == 100
    assert meta["total_with_pain_signal"] == 85
    assert meta["schema_version"] == 1


def test_build_pain_workflow_priors_per_cohort_share():
    agg = {
        "total_responses": 5,
        "total_with_pain_signal": 5,
        "workflow_counts": {"close_option_paralysis": 5},
        "workflow_per_cohort": {
            "25-34_female_bahraini": {"close_option_paralysis": 3, "value_budget_uncertainty": 1},
        },
    }
    priors = etl.build_pain_workflow_priors(agg, sources=["t.csv"])
    cop = next(w for w in priors["workflows"] if w["name"] == "close_option_paralysis")
    # 3 of (3+1) = 0.75 share for this cohort
    assert cop["per_cohort_weight"]["25-34_female_bahraini"] == 0.75


# ---------------------------------------------------------------------------
# build_decision_style_priors — synthetic aggregate
# ---------------------------------------------------------------------------

def test_build_decision_style_priors_emits_global():
    agg = {
        "total_responses": 4,
        "style_global": {"show_all_details": 2, "suggest_one_best": 2},
        "style_per_cohort": {},
    }
    priors = etl.build_decision_style_priors(agg, sources=["t.csv"])
    assert "_global" in priors
    assert sum(priors["_global"].values()) == pytest.approx(1.0)
    # All 4 styles present (Laplace smoothing keeps zero-bucket styles)
    assert set(priors["_global"].keys()) == {"show_all_details", "show_only_main_differences", "show_2_or_3_options", "suggest_one_best"}


def test_build_decision_style_priors_drops_small_cohorts():
    agg = {
        "total_responses": 50,
        "style_global": {"show_all_details": 50},
        "style_per_cohort": {
            "25-34_female_bahraini": {"show_all_details": 4},  # under min_cohort_n=8
            "18-24_male_bahraini": {"show_all_details": 10},   # over
        },
    }
    priors = etl.build_decision_style_priors(agg, sources=["t.csv"])
    assert "25-34_female_bahraini" not in priors
    assert "18-24_male_bahraini" in priors


def test_build_decision_style_priors_each_cohort_sums_to_1():
    agg = {
        "total_responses": 50,
        "style_global": {"show_all_details": 25, "suggest_one_best": 25},
        "style_per_cohort": {
            "25-34_female_bahraini": {"show_all_details": 8, "suggest_one_best": 4, "show_only_main_differences": 3, "show_2_or_3_options": 1},
        },
    }
    priors = etl.build_decision_style_priors(agg, sources=["t.csv"])
    for k, v in priors.items():
        if k == "metadata":
            continue
        assert sum(v.values()) == pytest.approx(1.0, abs=0.001)


def test_build_decision_style_priors_metadata_block():
    agg = {"total_responses": 100, "style_global": {}, "style_per_cohort": {}}
    priors = etl.build_decision_style_priors(agg, sources=["s.csv"])
    meta = priors["metadata"]
    assert meta["source"] == ["s.csv"]
    assert meta["total_responses"] == 100
    assert "min_cohort_n" in meta
    assert "laplace_prior" in meta


# ---------------------------------------------------------------------------
# _read_csv
# ---------------------------------------------------------------------------

def test_read_csv_missing_file_returns_empty(tmp_path):
    assert etl._read_csv(tmp_path / "nope.csv") == []


def test_read_csv_simple_file(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    rows = etl._read_csv(f)
    assert len(rows) == 2
    assert rows[0]["a"] == "1"
    assert rows[1]["b"] == "4"


# ---------------------------------------------------------------------------
# main() — end-to-end with synthetic CSVs
# ---------------------------------------------------------------------------

def test_main_runs_end_to_end_with_synthetic_csvs(tmp_path):
    eng = tmp_path / "eng.csv"
    arab = tmp_path / "arab.csv"
    out = tmp_path / "out"
    out.mkdir()

    # Minimal English CSV (1 row, all canonical fields)
    eng.write_text(
        "Q7 At what point did the choice feel hardest?,What were the top 2 difficulties you faced when trying to choose the right option?,Which style of assistance or advice would you prefer to make choosing the right option more clear?,Which of the following best describes you?,What is your age group?,What is your gender?\n"
        "When I found too many options,Too many options,Show me all details,Bahraini,25-34,Female\n",
        encoding="utf-8",
    )
    arab.write_text("", encoding="utf-8")

    rc = etl.main([
        "--eng", str(eng),
        "--arab", str(arab),
        "--out-dir", str(out),
        "--allow-missing",
        "--quiet",
    ])
    assert rc == 0
    pain = json.loads((out / "pain_workflow_priors.json").read_text(encoding="utf-8"))
    style = json.loads((out / "decision_style_priors.json").read_text(encoding="utf-8"))
    assert len(pain["workflows"]) == 8
    assert "_global" in style


def test_main_refuses_missing_csvs_without_allow_missing(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    rc = etl.main([
        "--eng", str(tmp_path / "nope1.csv"),
        "--arab", str(tmp_path / "nope2.csv"),
        "--out-dir", str(out),
        "--quiet",
    ])
    assert rc == 1
    cap = capsys.readouterr().err
    assert "missing" in cap.lower()

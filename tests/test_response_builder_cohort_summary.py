"""Phase 3.1 — `cohort_summary` root key on the comparison response.

The results screen's cohort proof line ("N shoppers in {governorate} leaned the
same way") reads `result.cohort_summary` = {"peer_count": int, "governorate": str}.
Before this change the backend never emitted the key, so the badge rendered for
nobody (CohortBadge hides when peer_count <= 0 || !governorate).

These tests pin the response-builder chokepoint contract:
- a valid cohort_summary kwarg → attached at the response ROOT verbatim;
- absent / zero peer_count / blank governorate → key OMITTED (badge hides);
- the same chokepoint feeds sync + streaming + partial paths, so one builder
  test covers the shape for all three (the orchestrator decides WHEN to pass it;
  see test_cohort_summary_orchestrator.py for the gating).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.response_builder import build_comparison_response


def _minimal_product_data():
    return [
        {
            "brand": "B0", "name": "P0", "full_name": "B0 P0",
            "category": "electronics", "price": None, "best_price": None,
            "specs": None, "reviews": None, "image_url": None,
            "rating": None, "rating_source": None, "review_count": 0,
            "fact_check": {},
        },
        {
            "brand": "B1", "name": "P1", "full_name": "B1 P1",
            "category": "electronics", "price": None, "best_price": None,
            "specs": None, "reviews": None, "image_url": None,
            "rating": None, "rating_source": None, "review_count": 0,
            "fact_check": {},
        },
    ]


def _minimal_scoring():
    return {
        "winner_index": 0,
        "scores": {"product_0": {"overall": 60.0}, "product_1": {"overall": 50.0}},
        "tradeoff_pairs": [],
        "value_badges": [],
        "comparison_quality": "normal",
        "personalization": {"applied_shifts": []},
        "price_tiers": {},
    }


def _build(**overrides):
    kwargs = dict(
        product_data=_minimal_product_data(),
        scoring_result=_minimal_scoring(),
        comparison=None, region="bahrain", query="A vs B",
        api_calls=0, elapsed_seconds=0.0, total_cost=0.0,
        gpt_calls=0, serper_calls=0, from_cache=False, verdict_validation={},
    )
    kwargs.update(overrides)
    return build_comparison_response(**kwargs)


# ---------- present + valid → attached at root ----------

def test_cohort_summary_attached_at_root_when_valid():
    """A resolved cohort (governorate + peer_count) → response['cohort_summary']
    == {'peer_count': N, 'governorate': 'Capital'} at the response ROOT (the key
    the FE ResultsScreen reads)."""
    resp = _build(cohort_summary={"peer_count": 19, "governorate": "Capital"})
    assert resp["cohort_summary"] == {"peer_count": 19, "governorate": "Capital"}


def test_cohort_summary_root_key_not_nested_under_personalization():
    """Contract pin — the FE reads the ROOT key first; it must be top-level
    (the `personalization.cohort` fallback is a separate, optional path)."""
    resp = _build(cohort_summary={"peer_count": 27, "governorate": "Northern"})
    assert "cohort_summary" in resp
    assert resp["cohort_summary"]["peer_count"] == 27
    assert resp["cohort_summary"]["governorate"] == "Northern"


# ---------- absent / graceful hide ----------

def test_cohort_summary_omitted_when_kwarg_absent():
    """Default (no cohort_summary passed) → key absent so the badge hides."""
    resp = _build()
    assert "cohort_summary" not in resp


def test_cohort_summary_omitted_when_none():
    """Explicit None → key absent (orchestrator passes None when no match)."""
    resp = _build(cohort_summary=None)
    assert "cohort_summary" not in resp


def test_cohort_summary_omitted_when_peer_count_zero():
    """Defensive re-validate: peer_count 0 → omitted (CohortBadge hides on <=0)."""
    resp = _build(cohort_summary={"peer_count": 0, "governorate": "Capital"})
    assert "cohort_summary" not in resp


def test_cohort_summary_omitted_when_peer_count_negative():
    resp = _build(cohort_summary={"peer_count": -5, "governorate": "Capital"})
    assert "cohort_summary" not in resp


def test_cohort_summary_omitted_when_governorate_blank():
    """Blank governorate → omitted (CohortBadge hides on !governorate)."""
    resp = _build(cohort_summary={"peer_count": 19, "governorate": ""})
    assert "cohort_summary" not in resp


def test_cohort_summary_omitted_when_governorate_missing():
    resp = _build(cohort_summary={"peer_count": 19})
    assert "cohort_summary" not in resp


def test_cohort_summary_omitted_when_not_a_dict():
    """Malformed (non-dict) → defensively omitted, never crashes the build."""
    resp = _build(cohort_summary="Capital")
    assert "cohort_summary" not in resp


# ---------- shape coercion ----------

def test_cohort_summary_peer_count_coerced_to_int():
    """peer_count arrives as the cohort prior's `n` (already int); pin int type
    so the FE gets a clean number (CohortBadge formats it)."""
    resp = _build(cohort_summary={"peer_count": 12, "governorate": "Muharraq"})
    assert isinstance(resp["cohort_summary"]["peer_count"], int)
    assert resp["cohort_summary"]["peer_count"] == 12

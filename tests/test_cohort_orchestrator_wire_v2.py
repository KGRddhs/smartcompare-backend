"""S3 L3 v2 (c) — orchestrator cohort wire: _derive_cohort_profile.

Seeds cohort-inferred preferences from demographics so compute_scores nudges the
weights (±10%). Fail-soft + explicit-prefs-win + demographics-absent → None.
"""
from unittest.mock import patch

from app.services.structured_comparison_service import StructuredComparisonService


def test_explicit_prefs_suppress_cohort():
    """When the user has explicit preferences, cohort is NOT derived (explicit
    ±30% wins; cohort is the weak inferred default)."""
    out = StructuredComparisonService._derive_cohort_profile(
        {"priorities": ["price"]}, {"age_group": "25-34", "gender": "Male"}
    )
    assert out is None


def test_no_demographics_returns_none():
    out = StructuredComparisonService._derive_cohort_profile(None, None)
    assert out is None
    out2 = StructuredComparisonService._derive_cohort_profile({}, None)
    assert out2 is None


def test_derives_cohort_profile_when_seed_has_priorities():
    """No explicit prefs + demographics present + seed yields priorities →
    returns the seeded preferences dict for the weighting."""
    seeded = {"priorities": ["quality"], "budget": "mid"}
    with patch("app.services.cohort_service.get_cohort_service") as gc:
        gc.return_value.seed_preferences.return_value = seeded
        out = StructuredComparisonService._derive_cohort_profile(
            None, {"age_group": "25-34", "gender": "Male", "nationality": "bahraini"}
        )
    assert out == seeded


def test_empty_seed_priorities_returns_none():
    """A cohort seed with no priorities is a no-op → None."""
    with patch("app.services.cohort_service.get_cohort_service") as gc:
        gc.return_value.seed_preferences.return_value = {"priorities": [], "budget": "mid"}
        out = StructuredComparisonService._derive_cohort_profile(
            None, {"age_group": "25-34"}
        )
    assert out is None


def test_fail_soft_on_cohort_error():
    """Any error in cohort seeding → None (must never break a comparison)."""
    with patch("app.services.cohort_service.get_cohort_service", side_effect=RuntimeError("boom")):
        out = StructuredComparisonService._derive_cohort_profile(
            None, {"age_group": "25-34"}
        )
    assert out is None

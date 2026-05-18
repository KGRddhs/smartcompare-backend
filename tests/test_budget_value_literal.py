"""Bundle C § 3a/3d/3b — BudgetValue 5-tier extension.

Per design § 3a + plan A.5.4: extend VALID_BUDGET in
app/api/auth_routes.py to accept `'luxury'` and `'top_tier'` alongside
the existing 3 tiers. Backwards-compat with the original 3 values is
mandatory per § 3d (existing user rows must keep validating).

Frontend types (B.1) committed the literal as exact lowercase strings
including snake_case `top_tier` — backend Pydantic must match exactly.
"""
import pytest
from pydantic import ValidationError

from app.api.auth_routes import UserPreferencesRequest, VALID_BUDGET


def _make_prefs(budget: str) -> dict:
    return {
        "priorities": ["price"],
        "budget": budget,
        "lifestyle": [],
        "brand_attitude": "function_first",
    }


def test_valid_budget_lists_5_tiers_in_order():
    """Spec § 3a: the 5 tier strings in order — budget → mid → premium →
    luxury → top_tier. Order matters because cohort_priors.json + frontend
    onboarding key off this exact list."""
    assert VALID_BUDGET == ["budget", "mid", "premium", "luxury", "top_tier"]


@pytest.mark.parametrize("tier", ["budget", "mid", "premium", "luxury", "top_tier"])
def test_user_preferences_accepts_all_5_tiers(tier):
    body = UserPreferencesRequest(**_make_prefs(tier))
    assert body.budget == tier


def test_user_preferences_still_accepts_legacy_3_tier_budget():
    """Backwards-compat per § 3d: existing rows with 'budget' / 'mid' /
    'premium' must keep validating."""
    for legacy in ("budget", "mid", "premium"):
        body = UserPreferencesRequest(**_make_prefs(legacy))
        assert body.budget == legacy


def test_user_preferences_rejects_unknown_budget():
    """Validation must reject anything outside the 5-tier set."""
    with pytest.raises(ValidationError):
        UserPreferencesRequest(**_make_prefs("ultra_mega"))


def test_user_preferences_rejects_hyphenated_top_tier():
    """Frontend + DB CHECK use snake_case `top_tier`. Reject hyphen
    variants so client/server stay in sync."""
    with pytest.raises(ValidationError):
        UserPreferencesRequest(**_make_prefs("top-tier"))


def test_user_preferences_rejects_uppercase_variants():
    """CHECK enum is lowercase. Reject case variants."""
    for variant in ("Luxury", "TOP_TIER", "Top_Tier"):
        with pytest.raises(ValidationError):
            UserPreferencesRequest(**_make_prefs(variant))

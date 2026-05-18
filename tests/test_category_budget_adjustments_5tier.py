"""Bundle C § 3b — CATEGORY_BUDGET_ADJUSTMENTS extends to 5 tiers.

Per design § 3b + plan A.5.3: each category gets `luxury` and `top_tier`
entries alongside the existing budget/mid/premium. `luxury` mirrors
`premium` (same shape); `top_tier` adds an extra +0.05 to the category's
headline spec dim on top of the luxury shape.

Headline spec dim per category (the dim that gets +0.10 under `premium`):
  electronics → performance_score
  grocery     → nutrition_score
  supplements → efficacy_score
  makeup      → longevity_score
  skincare    → actives_score
  haircare    → results_score
  fragrances  → character_score
  fashion     → craft_score
  other       → function_score
"""
import pytest

from app.services.scoring_service import CATEGORY_BUDGET_ADJUSTMENTS


HEADLINE_DIM = {
    "electronics": "performance_score",
    "grocery":     "nutrition_score",
    "supplements": "efficacy_score",
    "makeup":      "longevity_score",
    "skincare":    "actives_score",
    "haircare":    "results_score",
    "fragrances":  "character_score",
    "fashion":     "craft_score",
    "other":       "function_score",
}


@pytest.mark.parametrize("category", list(HEADLINE_DIM.keys()))
def test_every_category_has_luxury_entry(category):
    """Spec § 3b: luxury entry exists for every category."""
    assert "luxury" in CATEGORY_BUDGET_ADJUSTMENTS[category], (
        f"{category} missing 'luxury' tier"
    )


@pytest.mark.parametrize("category", list(HEADLINE_DIM.keys()))
def test_every_category_has_top_tier_entry(category):
    """Spec § 3b: top_tier entry exists for every category."""
    assert "top_tier" in CATEGORY_BUDGET_ADJUSTMENTS[category], (
        f"{category} missing 'top_tier' tier"
    )


@pytest.mark.parametrize("category,headline", list(HEADLINE_DIM.items()))
def test_luxury_boosts_headline_spec_dim(category, headline):
    """Spec § 3b: luxury mirrors the premium shape — headline dim gets a
    positive boost (we use the same +0.10 as premium for clarity)."""
    lux = CATEGORY_BUDGET_ADJUSTMENTS[category]["luxury"]
    assert lux.get(headline, 0) > 0, (
        f"{category} luxury must give {headline} a positive boost; got {lux}"
    )


@pytest.mark.parametrize("category,headline", list(HEADLINE_DIM.items()))
def test_top_tier_boosts_headline_dim_strictly_more_than_luxury(category, headline):
    """Spec § 3b: top_tier adds +0.05 to the headline dim on top of the
    luxury shape, so top_tier's headline boost is strictly greater than
    luxury's."""
    lux = CATEGORY_BUDGET_ADJUSTMENTS[category]["luxury"]
    top = CATEGORY_BUDGET_ADJUSTMENTS[category]["top_tier"]
    assert top.get(headline, 0) > lux.get(headline, 0), (
        f"{category} top_tier headline ({top.get(headline)}) must exceed "
        f"luxury headline ({lux.get(headline)})"
    )


@pytest.mark.parametrize("category,headline", list(HEADLINE_DIM.items()))
def test_top_tier_adds_exactly_005_over_luxury(category, headline):
    """Spec § 3b: '+0.05 to the headline spec dim'. Tight numeric assertion
    so the spec wording is honored exactly, not approximately."""
    lux = CATEGORY_BUDGET_ADJUSTMENTS[category]["luxury"]
    top = CATEGORY_BUDGET_ADJUSTMENTS[category]["top_tier"]
    delta = top.get(headline, 0) - lux.get(headline, 0)
    assert abs(delta - 0.05) < 1e-9, (
        f"{category}: top_tier {headline} should be exactly luxury+0.05, "
        f"got delta={delta}"
    )


def test_legacy_3_tiers_still_present():
    """Backwards-compat: budget/mid/premium entries remain on every category."""
    for category in HEADLINE_DIM:
        entry = CATEGORY_BUDGET_ADJUSTMENTS[category]
        for tier in ("budget", "mid", "premium"):
            assert tier in entry, f"{category} dropped legacy '{tier}' tier"

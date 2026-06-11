"""S2 I2.4 — `heat_stability` must NOT touch deterministic scoring.

Design §4 hard rule: NO new scoring dimension. The climate key is a
verdict-awareness extraction signal only. Because _score_specs uses
len(CATEGORY_SPEC_SCHEMAS[cat]) as its coverage denominator AND iterates the
schema fields, a naive add would (a) dilute coverage_ratio and (b) add a +1
to total_score whenever heat_stability is populated. Both would shift scores.

These tests pin that _score_specs is byte-identical with vs without a
populated heat_stability value, for the three affected categories.
"""

import pytest

from app.services.scoring_service import ScoringService


@pytest.fixture
def scorer():
    return ScoringService()


CASES = {
    "makeup": {
        "shade_range": "40 shades", "finish": "matte", "coverage": "full",
        "spf": "30", "volume": "30 ml", "long_lasting": "16 hours",
    },
    "skincare": {
        "skin_type": "oily", "active_ingredient": "niacinamide", "spf": "50",
        "volume": "30 ml", "ph_level": "5.5", "fragrance_free": "yes",
    },
    "fragrances": {
        "scent_family": "woody", "longevity": "8 hours", "sillage": "strong",
        "season": "all-season", "volume": "100 ml", "concentration": "EDP",
    },
}


@pytest.mark.parametrize("category", list(CASES.keys()))
def test_score_specs_unchanged_by_heat_stability(scorer, category):
    base_specs = dict(CASES[category])
    with_climate = dict(base_specs)
    with_climate["heat_stability"] = "Excellent — holds through 45C humidity"

    base_score = scorer._score_specs(base_specs, category)
    climate_score = scorer._score_specs(with_climate, category)

    assert base_score == climate_score, (
        f"{category}: heat_stability shifted spec score "
        f"{base_score} -> {climate_score}"
    )


@pytest.mark.parametrize("category", list(CASES.keys()))
def test_score_specs_unchanged_when_only_climate_present(scorer, category):
    """A specs dict containing ONLY heat_stability must score as zero-coverage
    (None), exactly as an empty dict would — the climate key is invisible to
    scoring."""
    empty_score = scorer._score_specs({}, category)
    climate_only = scorer._score_specs(
        {"heat_stability": "Good in heat"}, category
    )
    assert empty_score == climate_only
    assert climate_only is None

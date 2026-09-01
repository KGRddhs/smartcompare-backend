"""M20 #103 — behavioral sensitivity must translate into CATEGORY dimension keys,
and `scoring_method` must describe what actually moved the weights.

Two defects, one flag (`ENABLE_BEHAVIORAL_DIM_TRANSLATION`, default OFF):

1. `behavior_service.TAB_DIMENSION_MAP` emits sensitivity in the LEGACY universal
   key space (`spec_score` / `review_score` / `price_score`), but
   `apply_behavioral_adjustments` only builds a delta when the key is already a
   key of the CATEGORY weight dict. `spec_score` and `price_score` appear in NO
   category; `review_score` appears only in `other`. So the middle personalization
   tier is dead for 8 of 9 categories.
2. `compute_scores` sets `scoring_method = "behavioral"` on the mere PRESENCE of a
   profile, so the payload claims personalization for a run whose weights are
   identical to the anonymous one — and it shadows `"personalized"` when explicit
   prefs were the only layer that actually moved anything.

The doc/enum reconciliation (test 8) and the category-aware behavioral price tier
(`tests/test_behavior_service.py`) ship UNFLAGGED in the same change.
"""
import json
import os

import pytest

from app.services.scoring_service import (
    ScoringService,
    CATEGORY_DIMENSIONS,
    MAX_BEHAVIORAL_SHIFT_RATIO,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GOLDEN = os.path.join(_REPO_ROOT, "tests", "fixtures", "behavioral_flag_off_golden.json")

# A fully-populated profile in the LEGACY key space — exactly the shape
# behavior_service._compute_dimension_sensitivity emits and the DB stores.
LEGACY_PROFILE = {
    "dimension_sensitivity": {"spec_score": 0.7, "review_score": 0.2, "price_score": 0.1},
}


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def dim_translation_on(monkeypatch):
    monkeypatch.setenv("ENABLE_BEHAVIORAL_DIM_TRANSLATION", "true")
    yield


@pytest.fixture
def dim_translation_off(monkeypatch):
    monkeypatch.delenv("ENABLE_BEHAVIORAL_DIM_TRANSLATION", raising=False)
    yield


def _products(category="electronics"):
    return [
        {
            "brand": "Alpha", "name": "One", "category": category,
            "specs": {"ram": "6GB", "storage": "128GB"},
            "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon", "estimated": False},
            "reviews": {"average_rating": 4.5, "total_reviews": 1200},
            "rating": 4.5, "review_count": 1200, "rating_verified": True,
            "rating_source": {"name": "Amazon"}, "fact_check": {},
        },
        {
            "brand": "Beta", "name": "Two", "category": category,
            "specs": {"ram": "8GB", "storage": "256GB"},
            "price": {"amount": 279, "currency": "BHD", "retailer": "Noon", "estimated": False},
            "reviews": {"average_rating": 4.3, "total_reviews": 800},
            "rating": 4.3, "review_count": 800, "rating_verified": True,
            "rating_source": {"name": "Noon"}, "fact_check": {},
        },
    ]


# ---------------------------------------------------------------- defect 1


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS))
def test_sensitivity_moves_weights_in_all_nine_categories(
    service, dim_translation_on, category
):
    """A populated legacy-key sensitivity must move the weights in EVERY category."""
    base = service._compute_weights(None, category)
    moved = service.apply_behavioral_adjustments(dict(base), LEGACY_PROFILE, category)
    assert moved != base, (
        f"behavioral layer is dead for category={category!r}: weights unchanged"
    )


def test_translation_targets_the_signal_dim(service, dim_translation_on):
    """`spec_score` lands on the `spec` dim only — never also on `spec_secondary`.

    electronics: performance_score carries 'spec', feature_score carries
    'spec_secondary'. Splitting one tab's dwell across both would double-count
    the signal inside the +/-10% budget.

    NOTE the issue's literal wording ("feature_score did NOT change") is not
    checkable as an absolute: `_apply_capped_adjustments` RENORMALIZES to sum 1.0,
    so every dim's value moves even with a zero delta. The checkable claim is that
    feature_score received no TARGETED delta — i.e. it was scaled by exactly the
    same renormalization factor as the other no-delta dims, while
    performance_score was not.
    """
    profile = {"dimension_sensitivity": {"spec_score": 1.0, "review_score": 0.0, "price_score": 0.0}}
    base = service._compute_weights(None, "electronics")
    moved = service.apply_behavioral_adjustments(dict(base), profile, "electronics")

    assert moved["performance_score"] > base["performance_score"]

    # build_quality_score ('reliability') and ecosystem_score ('popularity') carry
    # no legacy signal, so they are pure renormalization references.
    ref = moved["build_quality_score"] / base["build_quality_score"]
    assert moved["ecosystem_score"] / base["ecosystem_score"] == pytest.approx(ref, rel=1e-9)
    assert moved["feature_score"] / base["feature_score"] == pytest.approx(ref, rel=1e-9), (
        "feature_score ('spec_secondary') received a targeted delta — spec_score "
        "must map to the primary 'spec' dim only"
    )
    assert moved["performance_score"] / base["performance_score"] != pytest.approx(ref, rel=1e-9)


def test_price_score_maps_to_category_value_dim(service, dim_translation_on):
    """`price_score` resolves to the category's VALUE dim (fragrances: wear_value_score)."""
    profile = {"dimension_sensitivity": {"spec_score": 0.0, "review_score": 0.0, "price_score": 1.0}}
    base = service._compute_weights(None, "fragrances")
    moved = service.apply_behavioral_adjustments(dict(base), profile, "fragrances")

    assert moved["wear_value_score"] != base["wear_value_score"]
    assert moved["wear_value_score"] > base["wear_value_score"]


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS))
def test_behavioral_cap_still_plus_minus_ten_percent(
    service, dim_translation_on, category
):
    """The +/-10% cap survives the new translation path.

    Tolerance is 1e-4, not the issue's 1e-9: `_apply_capped_adjustments` re-checks
    its cap with a literal `+ 0.0001` slack and then renormalizes once more
    afterwards, so it admits ~1e-4 of overshoot on EVERY path. That slack is
    pre-existing (measured at ~8.8e-05 on the legacy untranslated path at
    17cb981) and the issue explicitly says to leave `_apply_capped_adjustments`
    untouched, so this guards the cap at the implementation's own precision.
    """
    profile = {"dimension_sensitivity": {"spec_score": 1.0, "review_score": 0.0, "price_score": 0.0}}
    base = service._compute_weights(None, category)
    moved = service.apply_behavioral_adjustments(dict(base), profile, category)
    for dim in base:
        assert abs(moved[dim] - base[dim]) <= MAX_BEHAVIORAL_SHIFT_RATIO * base[dim] + 1e-4, (
            f"{category}.{dim} shifted beyond the +/-10% behavioral cap"
        )


def test_apply_behavioral_adjustments_default_category_is_other(service, dim_translation_on):
    """Calling without the new `category` argument is identical to category='other',
    so every existing caller and test keeps working unchanged."""
    base = service._compute_weights(None, "other")
    implicit = service.apply_behavioral_adjustments(dict(base), LEGACY_PROFILE)
    explicit = service.apply_behavioral_adjustments(dict(base), LEGACY_PROFILE, "other")
    assert implicit == explicit


def test_flag_off_two_arg_call_is_todays_untranslated_result(service, dim_translation_off):
    """Flag OFF, the legacy two-arg call keeps today's raw-key semantics: only a
    sensitivity key that IS already a category dim produces a delta."""
    base = service._compute_weights(None, "electronics")
    moved = service.apply_behavioral_adjustments(dict(base), LEGACY_PROFILE)
    assert moved == base  # none of the legacy keys is an electronics dim


# ---------------------------------------------------------------- defect 2


def test_scoring_method_not_behavioral_when_weights_unchanged(service, dim_translation_on):
    """A uniform sensitivity produces zero deltas — the label must not claim
    the run was personalized."""
    uniform = {"dimension_sensitivity": {"spec_score": 0.3, "review_score": 0.3, "price_score": 0.3}}
    result = service.compute_scores(_products(), behavior_profile=uniform)

    weights = result["scores"]["product_0"]["weights_used"]
    anon = service.compute_scores(_products())["scores"]["product_0"]["weights_used"]
    assert weights == anon, "precondition: this profile must not move the weights"
    assert result["scoring_method"] != "behavioral"


def test_explicit_prefs_take_label_precedence_over_profile(service, dim_translation_on):
    """Explicit +/-30% prefs moved the weights; the inferred profile did not
    (uniform). The label must say `personalized`, not `behavioral`."""
    uniform = {"dimension_sensitivity": {"spec_score": 0.3, "review_score": 0.3, "price_score": 0.3}}
    prefs = {"priorities": ["quality"], "budget": "mid"}

    anon = service.compute_scores(_products())["scores"]["product_0"]["weights_used"]
    result = service.compute_scores(_products(), preferences=prefs, behavior_profile=uniform)
    assert result["scores"]["product_0"]["weights_used"] != anon, (
        "precondition: these prefs must actually move the weights"
    )
    assert result["scoring_method"] == "personalized"


def test_scoring_method_is_behavioral_when_profile_actually_moved_weights(
    service, dim_translation_on
):
    """No explicit prefs + an EFFECTIVE profile == `behavioral`."""
    result = service.compute_scores(_products(), behavior_profile=LEGACY_PROFILE)
    anon = service.compute_scores(_products())["scores"]["product_0"]["weights_used"]
    assert result["scores"]["product_0"]["weights_used"] != anon
    assert result["scoring_method"] == "behavioral"


# ---------------------------------------------------------------- enum / docs


def test_every_emitted_scoring_method_is_documented():
    """Every literal the code can emit must appear in BOTH documented enum lines."""
    emitted = [
        "behavioral",
        "personalized",
        "cohort",
        "category_weighted",
        "default",
        "invitee_quiz",
    ]
    for rel in ("CLAUDE.md", os.path.join(".claude", "skills", "qaren-scoring", "SKILL.md")):
        path = os.path.join(_REPO_ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if "scoring_method" in ln and "enum" in ln]
        assert lines, f"{rel}: no scoring_method enum line found"
        blob = "\n".join(lines)
        for literal in emitted:
            assert literal in blob, f"{rel}: scoring_method enum line omits {literal!r}"


# ---------------------------------------------------------------- flag-OFF guard


def test_flag_off_weights_and_label_match_golden(service, dim_translation_off):
    """Flag OFF, `weights_used` and `scoring_method` are byte-identical to the
    golden captured at 17cb981 (pre-change) for all 9 categories."""
    with open(_GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    prefs = {"priorities": ["quality"], "budget": "mid"}
    assert sorted(golden) == sorted(CATEGORY_DIMENSIONS)
    for category, expected in golden.items():
        result = service.compute_scores(
            _products(category), preferences=prefs, behavior_profile=LEGACY_PROFILE,
        )
        assert result["scoring_method"] == expected["scoring_method"], category
        assert result["scores"]["product_0"]["weights_used"] == expected["weights_used"], category

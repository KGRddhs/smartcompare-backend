"""S3 L3 v2 (c) — cohort priors into the SCORE weights (not just the verdict).

Ahmed named "preferences" + the recommendation should reflect the buyer. Explicit
preferences + behavior already shape the dimension weights; cohort did NOT (it
only fed the verdict prompt). This wires the cohort's inferred priorities into
`compute_scores`' dimension weighting with a ±10% cap (like behavioral — an
INFERRED signal is weaker than an explicit ±30% preference).

Mechanism: compute_scores accepts a `cohort_profile` (the cohort-seeded
preferences shape: {priorities, budget, ...}). `apply_cohort_adjustments` nudges
the category weights toward the cohort's priorities, capped at ±10% of each
dimension's category weight, then renormalizes. Explicit preferences (when
present) still win — cohort is the weak default for anon-but-cohort'd users.
"""
import pytest

from app.services.scoring_service import (
    ScoringService,
    CATEGORY_DIMENSION_WEIGHTS,
    MAX_BEHAVIORAL_SHIFT_RATIO,
)


@pytest.fixture
def service():
    return ScoringService()


def test_apply_cohort_adjustments_shifts_toward_priority(service):
    """A cohort whose priority emphasizes quality nudges the quality-aligned
    electronics dims UP, capped at ±10%, renormalized to sum 1.0."""
    base = dict(CATEGORY_DIMENSION_WEIGHTS["electronics"])
    cohort = {"priorities": ["quality"]}
    adjusted = service.apply_cohort_adjustments(dict(base), cohort, "electronics")
    assert abs(sum(adjusted.values()) - 1.0) < 1e-6, "weights must renormalize to 1.0"
    # quality nudges performance_score / build_quality_score up vs value_score.
    assert adjusted["performance_score"] >= base["performance_score"]


def test_cohort_shift_capped_at_10pct(service):
    """No dimension shifts more than ±10% of its category weight."""
    base = dict(CATEGORY_DIMENSION_WEIGHTS["electronics"])
    cohort = {"priorities": ["quality", "durability"]}
    adjusted = service.apply_cohort_adjustments(dict(base), cohort, "electronics")
    # Compare pre-renormalization intent — after renorm, allow a small slack but
    # the cap invariant must hold within the behavioral tolerance.
    for dim, w in adjusted.items():
        cap = base[dim] * MAX_BEHAVIORAL_SHIFT_RATIO
        assert abs(w - base[dim]) <= cap + 0.02, (
            f"{dim} shifted {abs(w-base[dim]):.3f} > cap {cap:.3f}+slack"
        )


def test_no_cohort_priorities_is_noop(service):
    """Empty cohort priorities → weights unchanged."""
    base = dict(CATEGORY_DIMENSION_WEIGHTS["electronics"])
    for cohort in ({}, {"priorities": []}, None):
        adjusted = service.apply_cohort_adjustments(dict(base), cohort, "electronics")
        assert adjusted == base


def test_compute_scores_accepts_cohort_profile(service):
    """compute_scores accepts a cohort_profile kwarg and it shapes the winner
    when no explicit preferences are given. (Smoke: doesn't crash + produces a
    valid result with cohort applied.)"""
    p0 = {"name": "Perf", "category": "electronics",
          "price": {"amount": 400, "currency": "BHD", "source_method": "local_bhd"},
          "rating": 4.5, "review_count": 1000,
          "specs": {"ram": "16 GB", "storage": "512 GB", "battery": "5000 mAh"}}
    p1 = {"name": "Cheap", "category": "electronics",
          "price": {"amount": 200, "currency": "BHD", "source_method": "local_bhd"},
          "rating": 4.3, "review_count": 800,
          "specs": {"ram": "8 GB", "storage": "256 GB", "battery": "4000 mAh"}}
    r = service.compute_scores([p0, p1], cohort_profile={"priorities": ["quality"]})
    assert r["winner_index"] in (0, 1)
    assert r["scoring_method"] in ("cohort", "personalized", "behavioral", "category_weighted")


def test_explicit_preferences_take_precedence_over_cohort(service):
    """When BOTH explicit preferences and a cohort_profile are supplied, explicit
    preferences drive the weights (cohort is the weaker inferred default)."""
    p0 = {"name": "A", "category": "electronics",
          "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
          "rating": 4.5, "review_count": 900, "specs": {"ram": "8 GB", "storage": "256 GB"}}
    p1 = {"name": "B", "category": "electronics",
          "price": {"amount": 305, "currency": "BHD", "source_method": "local_bhd"},
          "rating": 4.4, "review_count": 800, "specs": {"ram": "8 GB", "storage": "256 GB"}}
    r = service.compute_scores(
        [p0, p1],
        preferences={"priorities": ["price"]},
        cohort_profile={"priorities": ["quality"]},
    )
    # scoring_method reflects explicit personalization, not cohort.
    assert r["scoring_method"] == "personalized"

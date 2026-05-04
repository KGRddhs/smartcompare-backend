"""Property-based + invariant tests for cohort_service against the live cohort_priors.json.

Idle work per Section C.8: hardens the cohort feature against subtle regressions
(non-deterministic match, broken fallback chain, persona_label drift, etc.)
without coupling tests to specific cohort key contents.

These tests load the REAL data/cohort_priors.json and assert structural
invariants that must hold for any valid build of the cohort priors file.

Pure unit tests — no Supabase, no network, no API calls.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


PRIORS_PATH = Path(__file__).resolve().parents[1] / "data" / "cohort_priors.json"


pytestmark = pytest.mark.skipif(
    not PRIORS_PATH.exists(),
    reason="cohort_priors.json not generated yet (run: python -m scripts.build_cohorts)",
)


@pytest.fixture(scope="module")
def priors():
    with open(PRIORS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def real_service(priors):
    """Real CohortService loaded from the real priors file."""
    from app.services.cohort_service import CohortService

    svc = CohortService.__new__(CohortService)
    svc._cohorts = priors
    return svc


# ============================================
# Top-level schema invariants
# ============================================


class TestPriorsSchemaInvariants:
    def test_top_level_keys(self, priors):
        for k in ("version", "built_at", "total_responses", "cohorts", "fallback_aggregates"):
            assert k in priors, f"missing top-level key: {k}"

    def test_total_responses_is_positive_int(self, priors):
        assert isinstance(priors["total_responses"], int)
        assert priors["total_responses"] > 0

    def test_total_responses_under_1000(self, priors):
        """We have ~400 responses — sanity check we haven't ingested wrong data."""
        assert priors["total_responses"] < 1000

    def test_no_cohort_below_n_5(self, priors):
        """ETL must drop cohorts with n<5."""
        for key, cohort in priors["cohorts"].items():
            assert cohort["n"] >= 5, f"cohort {key} has n={cohort['n']} < 5"

    def test_all_fallback_key(self, priors):
        """The 'all' aggregate must always be present."""
        assert "all" in priors["fallback_aggregates"]
        assert priors["fallback_aggregates"]["all"]["n"] >= 1

    def test_all_aggregate_n_matches_total_responses(self, priors):
        """Population aggregate n equals total_responses (no double counting)."""
        assert priors["fallback_aggregates"]["all"]["n"] == priors["total_responses"]


# ============================================
# Per-cohort structural invariants
# ============================================


class TestCohortStructure:
    def test_cohort_has_required_fields(self, priors):
        for key, cohort in priors["cohorts"].items():
            assert "n" in cohort, f"{key}: no n"
            assert "confidence" in cohort, f"{key}: no confidence"
            assert "modal" in cohort, f"{key}: no modal"
            assert "distribution" in cohort, f"{key}: no distribution"
            assert "persona_label" in cohort, f"{key}: no persona_label"

    def test_persona_label_non_empty(self, priors):
        for key, cohort in priors["cohorts"].items():
            assert isinstance(cohort["persona_label"], str)
            assert len(cohort["persona_label"]) > 0, f"{key}: empty persona_label"

    def test_confidence_value_is_valid(self, priors):
        for key, cohort in priors["cohorts"].items():
            assert cohort["confidence"] in ("low", "medium", "high"), (
                f"{key}: invalid confidence {cohort['confidence']!r}"
            )

    def test_confidence_matches_n_thresholds(self, priors):
        for key, cohort in priors["cohorts"].items():
            n = cohort["n"]
            conf = cohort["confidence"]
            if n >= 20:
                assert conf == "high", f"{key}: n={n} should be high, got {conf}"
            elif n >= 10:
                assert conf == "medium", f"{key}: n={n} should be medium, got {conf}"
            elif n >= 5:
                assert conf == "low", f"{key}: n={n} should be low, got {conf}"

    def test_cohort_key_format(self, priors):
        """Each cohort key has the form age|gender|governorate|language (4 parts, pipe-separated)."""
        for key in priors["cohorts"]:
            parts = key.split("|")
            assert len(parts) == 4, f"cohort key {key!r} has {len(parts)} parts, want 4"

    def test_cohort_keys_have_no_empty_parts(self, priors):
        """Per design 2.2, the cohort_key requires all 4 fields populated.

        Fixed in commit edd2f85: build_cohort_stats() now skips primary cohorts
        with any empty key part. Rows with missing fields still contribute to
        fallback_aggregates via the broader rollups.
        """
        empty_part_keys = [
            k for k in priors["cohorts"] if any(not p for p in k.split("|"))
        ]
        assert empty_part_keys == [], (
            f"primary cohorts must have all 4 key parts populated, found: {empty_part_keys}"
        )


# ============================================
# Distribution invariants
# ============================================


class TestDistributionInvariants:
    def test_distribution_sums_to_one(self, priors):
        """Each distribution dict must sum to ~1.0 (within float tolerance)."""
        for key, cohort in priors["cohorts"].items():
            for field, dist in cohort.get("distribution", {}).items():
                if not dist:
                    continue
                total = sum(dist.values())
                assert abs(total - 1.0) < 0.001, (
                    f"{key}.distribution.{field}: sum={total} != 1.0"
                )

    def test_distribution_values_are_valid_ratios(self, priors):
        for key, cohort in priors["cohorts"].items():
            for field, dist in cohort.get("distribution", {}).items():
                for value, ratio in dist.items():
                    assert 0 <= ratio <= 1, (
                        f"{key}.distribution.{field}.{value}: ratio={ratio}"
                    )


# ============================================
# Match() invariants — behavior doesn't depend on cohort identity
# ============================================


class TestMatchInvariants:
    SAMPLE_DEMOS = [
        {"age_group": "25-34", "gender": "Female", "governorate": "Northern", "language": "Arabic"},
        {"age_group": "35-44", "gender": "Male", "governorate": "Capital", "language": "English"},
        {"age_group": "18-24", "gender": "Female", "governorate": "Muharraq", "language": "Arabic"},
        {"age_group": "Prefer not to say", "gender": "Female"},
        {},
    ]

    def test_match_returns_consistent_for_identical_input(self, real_service):
        """match() is deterministic — same input → same cohort_key + match_quality."""
        for demo in self.SAMPLE_DEMOS:
            results = [real_service.match(demo) for _ in range(5)]
            keys = {(m.cohort_key, m.match_quality) for m in results if m}
            assert len(keys) <= 1, (
                f"match() not deterministic for {demo}: got {keys}"
            )

    def test_match_quality_has_valid_value(self, real_service):
        """Every match returns a recognized match_quality string."""
        valid = {
            "exact",
            "broadened_governorate",
            "broadened_language",
            "broadened_age",
            "population",
        }
        for demo in self.SAMPLE_DEMOS:
            m = real_service.match(demo)
            if m is not None:
                assert m.match_quality in valid, (
                    f"unknown match_quality {m.match_quality!r} for {demo}"
                )

    def test_match_n_is_positive(self, real_service):
        for demo in self.SAMPLE_DEMOS:
            m = real_service.match(demo)
            if m is not None:
                assert m.n > 0, f"non-positive n for {demo}"

    def test_match_persona_label_non_empty(self, real_service):
        for demo in self.SAMPLE_DEMOS:
            m = real_service.match(demo)
            if m is not None:
                assert isinstance(m.persona_label, str)
                assert len(m.persona_label) > 0


# ============================================
# Hierarchy invariants — broadening monotonically increases population
# ============================================


class TestHierarchyMonotonicity:
    def test_population_n_at_least_as_large_as_any_cohort(self, priors):
        """The population aggregate covers everyone — n >= every individual cohort."""
        all_n = priors["fallback_aggregates"]["all"]["n"]
        for key, cohort in priors["cohorts"].items():
            assert cohort["n"] <= all_n, (
                f"cohort {key} n={cohort['n']} > all n={all_n}"
            )

    def test_age_only_aggregate_covers_combinations(self, priors):
        """If '25-34' aggregate exists, its n >= each '25-34|...' cohort."""
        for age in ("18-24", "25-34", "35-44", "45-54", "55+"):
            age_agg = priors["fallback_aggregates"].get(age)
            if not age_agg:
                continue
            for key, cohort in priors["cohorts"].items():
                if key.startswith(f"{age}|"):
                    assert cohort["n"] <= age_agg["n"], (
                        f"{key} n={cohort['n']} > {age} aggregate n={age_agg['n']}"
                    )


# ============================================
# seed_preferences invariants
# ============================================


class TestSeedPreferencesInvariants:
    SAMPLE_DEMOS = [
        {"age_group": "25-34", "gender": "Female", "governorate": "Northern", "language": "Arabic"},
        {"age_group": "35-44", "gender": "Male"},
        {},
    ]

    def test_seed_always_returns_required_keys(self, real_service):
        for demo in self.SAMPLE_DEMOS:
            seeded = real_service.seed_preferences(demo)
            for k in ("priorities", "budget", "lifestyle", "brand_attitude", "_sources"):
                assert k in seeded

    def test_seed_lifestyle_always_empty_list(self, real_service):
        """Per design 5.2: lifestyle has no clean signal → always []."""
        for demo in self.SAMPLE_DEMOS:
            seeded = real_service.seed_preferences(demo)
            assert seeded["lifestyle"] == []

    def test_seed_priorities_within_max_three(self, real_service):
        """Existing schema caps priorities at 3 — seed must not exceed."""
        for demo in self.SAMPLE_DEMOS:
            seeded = real_service.seed_preferences(demo)
            assert len(seeded["priorities"]) <= 3

    def test_seed_sources_block_consistent_with_field_presence(self, real_service):
        """If a field has a value, _sources[field] must be 'inferred'.
        If a field is empty list / None, _sources[field] is None or 'inferred'."""
        for demo in self.SAMPLE_DEMOS:
            seeded = real_service.seed_preferences(demo)
            sources = seeded["_sources"]
            # lifestyle is always [] → source should be None
            assert sources.get("lifestyle") is None
            # priorities should be inferred when populated
            if seeded["priorities"]:
                assert sources["priorities"] == "inferred"


# ============================================
# get_display_profile invariants
# ============================================


class TestDisplayProfileInvariants:
    SAMPLE_DEMOS = [
        {"age_group": "25-34", "gender": "Female", "governorate": "Northern", "language": "Arabic"},
        {"age_group": "Prefer not to say"},  # population fallback → None
        {},  # population fallback → None
    ]

    def test_display_none_when_match_is_population_or_none(self, real_service):
        for demo in self.SAMPLE_DEMOS:
            m = real_service.match(demo)
            display = real_service.get_display_profile(demo)
            if m is None or m.match_quality == "population":
                assert display is None
            elif m.confidence == "low":
                assert display is None
            else:
                # high or medium confidence + non-population → display present
                assert display is not None
                assert "persona_label" in display
                assert "n" in display


# ============================================
# get_cohort_modal_for_key invariants
# ============================================


class TestCohortModalForKey:
    def test_modal_present_for_every_cohort(self, real_service, priors):
        for key in priors["cohorts"]:
            modal = real_service.get_cohort_modal_for_key(key)
            assert modal is not None, f"no modal for {key}"
            assert isinstance(modal, dict)

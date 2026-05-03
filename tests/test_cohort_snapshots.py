"""Snapshot-style tests covering distinct cohort match scenarios.

Idle work per Section C — exercises seed_preferences + display_profile
behavior across the FULL cross-product of (match_quality x confidence x
demographic combination), so that any subtle regression in cohort_service
output shape is caught.

Pure unit tests using a synthetic priors fixture — no IO.
"""
from __future__ import annotations

import pytest


SYNTHETIC_PRIORS = {
    "version": "1.0",
    "built_at": "2026-05-03T12:00:00Z",
    "total_responses": 100,
    "cohorts": {
        # Different confidence levels across cohorts
        "high_conf|Female|Northern|Arabic": {
            "n": 25,
            "confidence": "high",
            "modal": {
                "top_deciding_factor": "Quality",
                "second_deciding_factor": "Price",
                "spend_bracket": "25-50 BHD",
                "preferred_assistance_style": "Show me 2 or 3 suitable options",
                "if_info_incomplete": "Choose the brand I know",
            },
            "distribution": {"deciding_factor": {"Quality": 0.5, "Price": 0.3}},
            "persona_label": "Quality-first focused buyer",
        },
        "med_conf|Male|Capital|English": {
            "n": 12,
            "confidence": "medium",
            "modal": {
                "top_deciding_factor": "Brand",
                "second_deciding_factor": "Quality",
                "spend_bracket": "100-250 BHD",
                "preferred_assistance_style": "Suggest best with reason",
                "if_info_incomplete": "Choose the brand I know",
            },
            "distribution": {},
            "persona_label": "Premium brand-loyal buyer",
        },
        "low_conf|Female|Southern|Arabic": {
            "n": 6,
            "confidence": "low",
            "modal": {
                "top_deciding_factor": "Price",
                "spend_bracket": "<25 BHD",
                "preferred_assistance_style": "Show me 2 or 3 suitable options",
                "if_info_incomplete": "Look for more information",
            },
            "distribution": {},
            "persona_label": "Budget-conscious value seeker",
        },
    },
    "fallback_aggregates": {
        "high_conf|Female|Arabic": {
            "n": 35,
            "confidence": "high",
            "modal": {
                "top_deciding_factor": "Quality",
                "spend_bracket": "25-50 BHD",
            },
            "distribution": {},
            "persona_label": "Quality-first focused buyer",
        },
        "high_conf|Female": {
            "n": 50,
            "confidence": "high",
            "modal": {
                "top_deciding_factor": "Quality",
                "spend_bracket": "25-50 BHD",
            },
            "distribution": {},
            "persona_label": "Balanced shopper",
        },
        "Male": {
            "n": 20,
            "confidence": "high",
            "modal": {
                "top_deciding_factor": "Brand",
                "spend_bracket": "100-250 BHD",
            },
            "distribution": {},
            "persona_label": "Premium brand-loyal buyer",
        },
        "all": {
            "n": 100,
            "confidence": "high",
            "modal": {
                "top_deciding_factor": "Quality",
                "spend_bracket": "25-50 BHD",
            },
            "distribution": {},
            "persona_label": "Balanced shopper",
        },
    },
}


@pytest.fixture
def svc():
    from app.services.cohort_service import CohortService

    s = CohortService.__new__(CohortService)
    s._cohorts = SYNTHETIC_PRIORS
    return s


# ============================================
# Scenario matrix: each branch of seed_preferences output
# ============================================


class TestSeedScenarioMatrix:
    def test_seed_high_conf_quality_first(self, svc):
        seeded = svc.seed_preferences(
            {
                "age_group": "high_conf",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert seeded["budget"] == "mid"
        # Quality + Price → priorities should include both
        assert any("quality" in p.lower() for p in seeded["priorities"])
        assert seeded["_cohort_key"] == "high_conf|Female|Northern|Arabic"
        assert seeded["_sources"]["priorities"] == "inferred"

    def test_seed_med_conf_premium_brand(self, svc):
        seeded = svc.seed_preferences(
            {
                "age_group": "med_conf",
                "gender": "Male",
                "governorate": "Capital",
                "language": "English",
            }
        )
        assert seeded["budget"] == "premium"
        # Brand + Quality → at least one brand-related priority
        assert any(("brand" in p.lower() or "quality" in p.lower()) for p in seeded["priorities"])
        assert seeded["_cohort_key"] == "med_conf|Male|Capital|English"

    def test_seed_low_conf_budget_value(self, svc):
        seeded = svc.seed_preferences(
            {
                "age_group": "low_conf",
                "gender": "Female",
                "governorate": "Southern",
                "language": "Arabic",
            }
        )
        assert seeded["budget"] == "budget"
        # Low conf still seeds (per design 3.6 — only display is hidden, not seeding)
        assert seeded["_cohort_key"] == "low_conf|Female|Southern|Arabic"

    def test_seed_population_fallback(self, svc):
        """Even population fallback seeds preferences (per design 3.6 + 5.1)."""
        seeded = svc.seed_preferences({})
        # Population modal has Quality + 25-50 BHD → mid budget
        assert seeded["budget"] == "mid"
        assert seeded["_cohort_key"] == "all"


# ============================================
# Scenario matrix: get_display_profile visibility logic
# ============================================


class TestDisplayProfileScenarios:
    def test_display_high_confidence_visible(self, svc):
        d = svc.get_display_profile(
            {
                "age_group": "high_conf",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert d is not None
        assert d["persona_label"] == "Quality-first focused buyer"
        assert d["n"] == 25

    def test_display_medium_confidence_visible(self, svc):
        d = svc.get_display_profile(
            {
                "age_group": "med_conf",
                "gender": "Male",
                "governorate": "Capital",
                "language": "English",
            }
        )
        assert d is not None
        assert d["persona_label"] == "Premium brand-loyal buyer"
        assert d["n"] == 12

    def test_display_low_confidence_hidden(self, svc):
        d = svc.get_display_profile(
            {
                "age_group": "low_conf",
                "gender": "Female",
                "governorate": "Southern",
                "language": "Arabic",
            }
        )
        assert d is None

    def test_display_population_hidden(self, svc):
        d = svc.get_display_profile({})
        assert d is None


# ============================================
# Scenario matrix: match_quality through the fallback ladder
# ============================================


class TestMatchQualityScenarios:
    def test_exact_when_full_key_present(self, svc):
        m = svc.match(
            {
                "age_group": "high_conf",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert m.match_quality == "exact"
        assert m.cohort_key == "high_conf|Female|Northern|Arabic"

    def test_broadened_governorate_when_governorate_missing(self, svc):
        m = svc.match(
            {
                "age_group": "high_conf",
                "gender": "Female",
                "governorate": "NonexistentGov",
                "language": "Arabic",
            }
        )
        assert m.match_quality == "broadened_governorate"
        assert m.cohort_key == "high_conf|Female|Arabic"

    def test_broadened_language_when_language_missing(self, svc):
        m = svc.match(
            {
                "age_group": "high_conf",
                "gender": "Female",
                "governorate": "NonexistentGov",
                "language": "NonexistentLang",
            }
        )
        assert m.match_quality == "broadened_language"
        assert m.cohort_key == "high_conf|Female"

    def test_broadened_age_when_age_unknown(self, svc):
        m = svc.match(
            {
                "age_group": "NonexistentAge",
                "gender": "Male",
                "governorate": "NonexistentGov",
                "language": "NonexistentLang",
            }
        )
        assert m.match_quality == "broadened_age"
        assert m.cohort_key == "Male"

    def test_population_when_nothing_matches(self, svc):
        m = svc.match({"age_group": "Unknown", "gender": "Unknown"})
        assert m.match_quality == "population"
        assert m.cohort_key == "all"


# ============================================
# Cohort modal lookup scenarios
# ============================================


class TestCohortModalLookupScenarios:
    def test_lookup_primary_cohort(self, svc):
        modal = svc.get_cohort_modal_for_key("high_conf|Female|Northern|Arabic")
        assert modal["top_deciding_factor"] == "Quality"

    def test_lookup_fallback_aggregate(self, svc):
        modal = svc.get_cohort_modal_for_key("Male")
        assert modal["top_deciding_factor"] == "Brand"

    def test_lookup_population(self, svc):
        modal = svc.get_cohort_modal_for_key("all")
        assert modal is not None

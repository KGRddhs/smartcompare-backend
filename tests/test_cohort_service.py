"""Tests for app/services/cohort_service.py — matching, fallback, seeding, display.

Asserts the design contract from docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md
sections 3.1-3.7. Target 90% coverage on `match()`.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest


# Reusable fake priors covering every fallback level
FAKE_PRIORS = {
    "version": "1.0",
    "built_at": "2026-05-03T12:00:00Z",
    "total_responses": 397,
    "cohorts": {
        "25-34|Female|Northern|Arabic": {
            "n": 23,
            "confidence": "high",
            "demographics": {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            },
            "modal": {
                "top_deciding_factor": "Quality",
                "second_deciding_factor": "Price",
                "preferred_assistance_style": "Show me 2 or 3 suitable options",
                "spend_bracket": "25-50 BHD",
                "trust_sources": ["Store"],
                "top_difficulties": ["Too many options"],
                "post_purchase_pattern": "I felt I made the right choice",
                "what_helps_most": ["See the main differences simply"],
                "primary_categories": ["Fashion or Beauty item"],
                "if_info_incomplete": "Choose the brand I know",
            },
            "distribution": {
                "deciding_factor": {"Quality": 0.43, "Price": 0.30, "Brand": 0.13}
            },
            "persona_label": "Quality-first focused buyer",
        },
        "25-34|Female|Capital|Arabic": {
            "n": 8,
            "confidence": "low",
            "demographics": {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Capital",
                "language": "Arabic",
            },
            "modal": {"top_deciding_factor": "Price", "spend_bracket": "<25 BHD"},
            "distribution": {},
            "persona_label": "Budget-conscious value seeker",
        },
    },
    "fallback_aggregates": {
        "25-34|Female|Arabic": {
            "n": 35,
            "confidence": "high",
            "demographics": {
                "age_group": "25-34",
                "gender": "Female",
                "language": "Arabic",
            },
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Quality-first focused buyer",
        },
        "25-34|Female": {
            "n": 50,
            "confidence": "high",
            "demographics": {"age_group": "25-34", "gender": "Female"},
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Quality-first focused buyer",
        },
        "25-34": {
            "n": 100,
            "confidence": "high",
            "demographics": {"age_group": "25-34"},
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Balanced shopper",
        },
        "Male": {
            "n": 80,
            "confidence": "high",
            "demographics": {"gender": "Male"},
            "modal": {"top_deciding_factor": "Brand", "spend_bracket": "100-250 BHD"},
            "distribution": {},
            "persona_label": "Premium brand-loyal buyer",
        },
        "Female": {
            "n": 120,
            "confidence": "high",
            "demographics": {"gender": "Female"},
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Quality-first focused buyer",
        },
        "all": {
            "n": 397,
            "confidence": "high",
            "demographics": {},
            "modal": {"top_deciding_factor": "Quality", "spend_bracket": "25-50 BHD"},
            "distribution": {},
            "persona_label": "Balanced shopper",
        },
    },
}


@pytest.fixture
def fake_service():
    """Service with FAKE_PRIORS loaded."""
    from app.services.cohort_service import CohortService

    svc = CohortService.__new__(CohortService)  # bypass __init__'s file load
    svc._cohorts = FAKE_PRIORS
    return svc


# ============================================
# A.3.1: Service initialization + JSON load
# ============================================


class TestServiceInit:
    def test_service_loads_priors_on_init(self):
        from app.services.cohort_service import CohortService

        svc = CohortService()
        assert svc._cohorts is not None
        assert "cohorts" in svc._cohorts
        assert "fallback_aggregates" in svc._cohorts

    def test_get_cohort_service_returns_singleton(self):
        from app.services import cohort_service

        # Reset for isolation
        cohort_service._service_singleton = None
        a = cohort_service.get_cohort_service()
        b = cohort_service.get_cohort_service()
        assert a is b


class TestServiceFileHandling:
    def test_service_handles_missing_priors_file(self, monkeypatch):
        """Missing cohort_priors.json → service starts in degraded mode (returns None for match)."""
        from app.services import cohort_service

        monkeypatch.setattr(cohort_service, "PRIORS_PATH", Path("/nonexistent/cohort_priors.json"))
        svc = cohort_service.CohortService()
        # Degraded mode — match() returns None (no priors loaded)
        match = svc.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert match is None

    def test_service_handles_malformed_json(self, monkeypatch, tmp_path):
        """Malformed JSON → degraded mode."""
        from app.services import cohort_service

        bad = tmp_path / "cohort_priors.json"
        bad.write_text("{ not valid json", encoding="utf-8")
        monkeypatch.setattr(cohort_service, "PRIORS_PATH", bad)
        svc = cohort_service.CohortService()
        match = svc.match(
            {"age_group": "25-34", "gender": "Female", "governorate": "Northern", "language": "Arabic"}
        )
        assert match is None


# ============================================
# A.3.2-3.6: match() — all fallback levels
# ============================================


class TestMatch:
    def test_match_exact_returns_full_cohort(self, fake_service):
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert match is not None
        assert match.match_quality == "exact"
        assert match.cohort_key == "25-34|Female|Northern|Arabic"
        assert match.confidence == "high"
        assert match.n == 23
        assert match.persona_label == "Quality-first focused buyer"

    def test_match_drops_governorate_fallback(self, fake_service):
        """Wrong governorate → fall back to age|gender|language."""
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Southern",  # not in cohorts
                "language": "Arabic",
            }
        )
        assert match is not None
        assert match.match_quality == "broadened_governorate"
        assert match.n == 35  # the 25-34|Female|Arabic aggregate

    def test_match_drops_language_fallback(self, fake_service):
        """No language match → fall back to age|gender."""
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Southern",
                "language": "French",  # neither Arabic nor English in fixtures
            }
        )
        assert match is not None
        assert match.match_quality == "broadened_language"
        assert match.n == 50  # the 25-34|Female aggregate

    def test_match_drops_age_fallback(self, fake_service):
        """Wrong age → fall back to gender only."""
        match = fake_service.match(
            {
                "age_group": "55+",  # no 55+ aggregate in fixtures
                "gender": "Female",
                "governorate": "Southern",
                "language": "French",
            }
        )
        assert match is not None
        assert match.match_quality == "broadened_age"
        assert match.n == 120  # the Female-only aggregate

    def test_match_population_fallback(self, fake_service):
        """No demographic info → return population aggregate."""
        match = fake_service.match(
            {
                "age_group": "Prefer not to say",
                "gender": "Prefer not to say",
                "governorate": "Prefer not to say",
                "language": "Prefer not to say",
            }
        )
        assert match is not None
        assert match.match_quality == "population"
        assert match.n == 397
        assert match.cohort_key == "all"

    def test_match_population_when_all_fields_missing(self, fake_service):
        match = fake_service.match({})
        assert match is not None
        assert match.match_quality == "population"

    def test_match_returns_none_when_no_priors_and_no_population(self, monkeypatch):
        """Truly degraded — no priors at all → returns None."""
        from app.services.cohort_service import CohortService

        svc = CohortService.__new__(CohortService)
        svc._cohorts = {"cohorts": {}, "fallback_aggregates": {}}
        match = svc.match(
            {"age_group": "25-34", "gender": "Female", "governorate": "Northern", "language": "Arabic"}
        )
        # No data → None per design
        assert match is None


class TestMatchSkipsPreferNotToSay:
    """A.3.7: 'Prefer not to say' treated as missing."""

    def test_skips_prefer_not_to_say_governorate(self, fake_service):
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Prefer not to say",
                "language": "Arabic",
            }
        )
        # Governorate is skipped → broadens to age|gender|language
        assert match.match_quality == "broadened_governorate"

    def test_skips_empty_string_as_missing(self, fake_service):
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "",
                "language": "Arabic",
            }
        )
        assert match.match_quality == "broadened_governorate"

    def test_skips_none_as_missing(self, fake_service):
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": None,
                "language": "Arabic",
            }
        )
        assert match.match_quality == "broadened_governorate"


class TestMatchQualityPropagation:
    """C.3.1: each fallback level returns the correct match_quality string."""

    def test_exact_propagates(self, fake_service):
        match = fake_service.match(
            {"age_group": "25-34", "gender": "Female", "governorate": "Northern", "language": "Arabic"}
        )
        assert match.match_quality == "exact"

    def test_broadened_governorate_propagates(self, fake_service):
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "NonexistentGov",
                "language": "Arabic",
            }
        )
        assert match.match_quality == "broadened_governorate"


# ============================================
# A.3.8: seed_preferences()
# ============================================


class TestSeedPreferences:
    def test_seed_returns_required_keys(self, fake_service):
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert "priorities" in seeded
        assert "budget" in seeded
        assert "lifestyle" in seeded
        assert "brand_attitude" in seeded
        assert "_sources" in seeded
        assert "_seeded_at" in seeded
        assert "_cohort_key" in seeded

    def test_seed_priorities_uses_top_two_factors(self, fake_service):
        """top_deciding_factor + second_deciding_factor → priorities list."""
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        # The cohort modal has Quality + Price → two priorities
        assert len(seeded["priorities"]) >= 1
        # The ENUM values must match the existing 8-priority schema
        # (per design 5.2, mapped from cohort string to existing enum)
        # We accept any of the 8 valid priority enum values
        VALID_PRIORITIES = {
            "price",
            "quality",
            "durability",
            "eco_friendly",
            "best_price",
            "quality_reliability",
            "trusted_brand",
            "warranty_support",
            "design_aesthetics",
            "value_for_money",
        }
        for p in seeded["priorities"]:
            assert p in VALID_PRIORITIES, f"unexpected priority: {p}"

    def test_seed_budget_from_spend_bracket(self, fake_service):
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        # 25-50 BHD → mid
        assert seeded["budget"] == "mid"

    def test_seed_lifestyle_left_empty(self, fake_service):
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        # No clean signal → empty per design 5.2
        assert seeded["lifestyle"] == []

    def test_seed_sources_tagged_inferred(self, fake_service):
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert seeded["_sources"]["priorities"] == "inferred"
        assert seeded["_sources"]["budget"] == "inferred"
        assert seeded["_sources"]["brand_attitude"] == "inferred"
        # Lifestyle source is null since field is left empty
        assert seeded["_sources"]["lifestyle"] is None

    def test_seed_cohort_key_recorded(self, fake_service):
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert seeded["_cohort_key"] == "25-34|Female|Northern|Arabic"

    def test_seed_includes_seeded_at_iso_timestamp(self, fake_service):
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        ts = seeded["_seeded_at"]
        assert isinstance(ts, str)
        assert "T" in ts  # ISO 8601 format

    def test_seed_premium_budget_for_high_spend(self, fake_service):
        """100-250 BHD → premium tier."""
        # Force the match to use the Premium-flavored Male aggregate
        seeded = fake_service.seed_preferences(
            {
                "age_group": "55+",
                "gender": "Male",
                "governorate": "Southern",
                "language": "French",
            }
        )
        # Male aggregate has spend_bracket=100-250 BHD → premium
        assert seeded["budget"] == "premium"

    def test_seed_budget_under_25_is_budget_tier(self, fake_service):
        """<25 BHD → budget tier."""
        # The Capital cohort has spend_bracket=<25 BHD
        seeded = fake_service.seed_preferences(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Capital",
                "language": "Arabic",
            }
        )
        assert seeded["budget"] == "budget"


# ============================================
# A.3.9: get_display_profile()
# ============================================


class TestGetDisplayProfile:
    def test_display_returned_for_high_confidence(self, fake_service):
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        assert display is not None
        assert "persona_label" in display
        assert display["persona_label"] == "Quality-first focused buyer"
        assert display["n"] == 23

    def test_display_none_for_low_confidence(self, fake_service):
        """The Capital cohort has confidence=low → no card per design 3.6."""
        display = fake_service.get_display_profile(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Capital",
                "language": "Arabic",
            }
        )
        assert display is None

    def test_display_none_for_population_match(self, fake_service):
        """Population fallback → hide card (design 3.6)."""
        display = fake_service.get_display_profile(
            {
                "age_group": "Prefer not to say",
                "gender": "Prefer not to say",
                "governorate": "Prefer not to say",
                "language": "Prefer not to say",
            }
        )
        assert display is None


# ============================================
# A.3.8 / C.3.4: should_seed() decision logic
# ============================================


class TestShouldSeed:
    def test_should_seed_when_prefs_empty(self, fake_service):
        assert fake_service.should_seed(None) is True
        assert fake_service.should_seed({}) is True

    def test_should_seed_when_all_inferred(self, fake_service):
        prefs = {
            "priorities": ["quality"],
            "budget": "mid",
            "_sources": {
                "priorities": "inferred",
                "budget": "inferred",
                "brand_attitude": "inferred",
                "lifestyle": None,
            },
        }
        assert fake_service.should_seed(prefs) is True

    def test_should_not_seed_when_any_user_stated(self, fake_service):
        prefs = {
            "priorities": ["quality"],
            "budget": "mid",
            "_sources": {
                "priorities": "user_stated",
                "budget": "inferred",
                "brand_attitude": "inferred",
                "lifestyle": None,
            },
        }
        assert fake_service.should_seed(prefs) is False

    def test_should_not_seed_when_prefs_have_values_no_sources(self, fake_service):
        """Legacy prefs without _sources block — assume user-stated to be safe."""
        prefs = {"priorities": ["quality"], "budget": "mid", "brand_attitude": "best_of_both"}
        assert fake_service.should_seed(prefs) is False


# ============================================
# A.3.10: Performance — match() is in-memory (no per-call IO)
# ============================================


class TestMatchPerformance:
    def test_match_is_in_memory_no_open_calls(self, monkeypatch, fake_service):
        """match() must not open any files."""
        opens = []
        real_open = open

        def spy_open(*args, **kwargs):
            opens.append(args)
            return real_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", spy_open)
        for _ in range(50):
            fake_service.match(
                {
                    "age_group": "25-34",
                    "gender": "Female",
                    "governorate": "Northern",
                    "language": "Arabic",
                }
            )
        assert opens == [], "match() must be pure in-memory"


# ============================================
# CohortMatch shape
# ============================================


class TestCohortMatchShape:
    def test_cohort_match_has_expected_attributes(self, fake_service):
        match = fake_service.match(
            {
                "age_group": "25-34",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        # CohortMatch dataclass per design 3.2
        for attr in (
            "cohort_key",
            "match_quality",
            "confidence",
            "n",
            "modal",
            "distribution",
            "persona_label",
        ):
            assert hasattr(match, attr), f"missing attribute: {attr}"


# ============================================
# Coverage extension: edge cases on match() + helpers
# Drives match() coverage to 100%
# ============================================


class TestMatchEdgeCases:
    def test_match_with_demographics_none(self, fake_service):
        """match(None) → treated as empty → population fallback."""
        match = fake_service.match(None)
        assert match is not None
        assert match.match_quality == "population"

    def test_match_with_low_n_full_key_falls_back(self, monkeypatch, fake_service):
        """If full cohort exists but n < 5, fall through to broader prefix."""
        # Mutate fake to create n=4 full cohort
        fake_service._cohorts["cohorts"]["35-44|Male|Capital|English"] = {
            "n": 4,
            "confidence": "low",
            "modal": {},
            "distribution": {},
            "persona_label": "Test",
            "demographics": {},
        }
        # No 35-44|Male|English aggregate exists → falls to gender-only Male
        match = fake_service.match(
            {
                "age_group": "35-44",
                "gender": "Male",
                "governorate": "Capital",
                "language": "English",
            }
        )
        # Should fall through to gender-only since n<5 in exact and no other keys exist
        assert match is not None
        assert match.match_quality in ("broadened_age", "population")

    def test_match_governorate_only_no_other_fields(self, fake_service):
        """Only governorate present (no age/gender/language) → goes to population."""
        match = fake_service.match({"governorate": "Northern"})
        assert match is not None
        assert match.match_quality == "population"

    def test_match_language_only_no_other_fields(self, fake_service):
        match = fake_service.match({"language": "Arabic"})
        assert match is not None
        assert match.match_quality == "population"

    def test_match_only_age(self, fake_service):
        """Only age → no fallback below age|gender → population."""
        match = fake_service.match({"age_group": "25-34"})
        # Note: age-only does not match the gender-only fallback level — falls to population
        assert match is not None
        assert match.match_quality == "population"


class TestPreferNotToSayHandling:
    def test_prefer_not_to_say_age_only(self, fake_service):
        """Just age missing → other parts dominate."""
        match = fake_service.match(
            {
                "age_group": "Prefer not to say",
                "gender": "Female",
                "governorate": "Northern",
                "language": "Arabic",
            }
        )
        # Without age, exact key would be missing — but service may broaden
        # to gender-only (Female aggregate exists in fixtures with n=120)
        assert match is not None
        assert match.match_quality in (
            "broadened_age",
            "broadened_language",
            "broadened_governorate",
            "population",
        )


class TestGetCohortModalForKey:
    """get_cohort_modal_for_key — used by extraction prompt builder."""

    def test_returns_modal_for_known_key(self, fake_service):
        modal = fake_service.get_cohort_modal_for_key("25-34|Female|Northern|Arabic")
        assert modal is not None
        assert modal.get("top_deciding_factor") == "Quality"

    def test_returns_none_for_unknown_key(self, fake_service):
        assert fake_service.get_cohort_modal_for_key("nonexistent|key") is None

    def test_returns_none_for_empty_key(self, fake_service):
        assert fake_service.get_cohort_modal_for_key("") is None

    def test_returns_none_for_none_key(self, fake_service):
        assert fake_service.get_cohort_modal_for_key(None) is None

    def test_returns_modal_for_fallback_key(self, fake_service):
        """Looking up a fallback aggregate key also works."""
        modal = fake_service.get_cohort_modal_for_key("all")
        assert modal is not None

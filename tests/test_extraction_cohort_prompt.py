"""Snapshot + privacy tests for cohort prompt block injection in extraction_service.

Asserts the design contract from
docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md sections 4.1-4.7.

Critical privacy invariant: NO raw demographics (age value, gender value)
appear in the rendered prompt. Only AGGREGATE COHORT STATISTICS + thin
context line (country/language/region) are sent to OpenAI.

Written FIRST (red phase). Backend implements to make these green.
"""
from __future__ import annotations

import os
from unittest import mock

import pytest


# A representative full demographics_profile attached to a user record after
# they submit demographics. The cohort_match block is what the prompt builder
# uses to produce the cohort priors injection.
STRONG_MATCH_PROFILE = {
    "age_group": "25-34",
    "gender": "Female",
    "governorate": "Northern",
    "language": "Arabic",
    "country": "Bahrain",
    "submitted_at": "2026-05-03T14:23:00Z",
    "cohort_match": {
        "cohort_key": "25-34|Female|Northern|Arabic",
        "match_quality": "exact",
        "confidence": "high",
        "n": 23,
        "persona_label": "Quality-first focused buyer",
    },
}

POPULATION_MATCH_PROFILE = {
    "age_group": "Prefer not to say",
    "gender": "Prefer not to say",
    "governorate": "Prefer not to say",
    "language": "English",
    "country": "Bahrain",
    "submitted_at": "2026-05-03T14:23:00Z",
    "cohort_match": {
        "cohort_key": "all",
        "match_quality": "population",
        "confidence": "high",
        "n": 397,
        "persona_label": "Balanced shopper",
    },
}

LOW_CONF_PROFILE = {
    "age_group": "55+",
    "gender": "Male",
    "governorate": "Southern",
    "language": "English",
    "country": "Bahrain",
    "submitted_at": "2026-05-03T14:23:00Z",
    "cohort_match": {
        "cohort_key": "Male",
        "match_quality": "broadened_age",
        "confidence": "low",
        "n": 8,
        "persona_label": "Premium brand-loyal buyer",
    },
}


# A representative cohort modal that the cohort_service would lookup for the
# matched cohort_key. Used by the prompt builder to render the priors block.
SAMPLE_COHORT_MODAL = {
    "top_deciding_factor": "Quality",
    "second_deciding_factor": "Price",
    "preferred_assistance_style": "Show me 2 or 3 suitable options",
    "spend_bracket": "25-50 BHD",
    "trust_sources": ["Store", "Word of mouth"],
    "top_difficulties": ["Too many options", "Quality - Reliability"],
    "post_purchase_pattern": "I felt I made the right choice",
    "what_helps_most": ["See the main differences simply", "Know which option fits my budget"],
}


VALID_PREFS = {
    "priorities": ["quality_reliability", "best_price"],
    "budget": "mid",
    "lifestyle": [],
    "brand_attitude": "best_of_both",
}


def _patch_cohort_modal(modal):
    """Patch cohort_service.get_cohort_modal_for_key to return a known modal."""
    return mock.patch(
        "app.services.cohort_service.get_cohort_service",
        return_value=mock.MagicMock(
            get_cohort_modal_for_key=mock.MagicMock(return_value=modal)
        ),
    )


# ============================================
# C.5.1: Cohort block injected for strong match
# ============================================


class TestCohortBlockInjection:
    def test_block_injected_for_exact_match(self):
        """Exact match → priors block appears in rendered prompt."""
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )

        assert "COHORT-LEVEL PRIORS" in prompt or "cohort" in prompt.lower(), (
            "Strong match should inject cohort priors block"
        )

    def test_block_injected_for_broadened_governorate(self):
        from app.services.extraction_service import _build_preferences_prompt

        profile = {
            **STRONG_MATCH_PROFILE,
            "cohort_match": {
                **STRONG_MATCH_PROFILE["cohort_match"],
                "match_quality": "broadened_governorate",
                "confidence": "medium",
                "n": 15,
            },
        }
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(VALID_PREFS, demographics_profile=profile)
        assert "COHORT-LEVEL PRIORS" in prompt or "cohort" in prompt.lower()

    def test_block_includes_top_deciding_factors(self):
        """Priors block surfaces top deciding factors per design 4.2."""
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )

        # Top deciding factors: Quality, Price (from SAMPLE_COHORT_MODAL)
        assert "Quality" in prompt
        assert "Price" in prompt

    def test_block_includes_spend_bracket(self):
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        assert "25-50 BHD" in prompt or "25" in prompt

    def test_block_includes_n_count(self):
        """Block shows N — 'similar users' for credibility."""
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        assert "23" in prompt, "Sample size N=23 must appear in cohort priors block"

    def test_block_includes_population_statistics_disclaimer(self):
        """Per design 4.2: prompt explicitly states POPULATION STATISTICS, not facts about the user."""
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        assert "POPULATION STATISTICS" in prompt or "population" in prompt.lower()

    def test_block_includes_user_context_line(self):
        """Per design 4.2: USER CONTEXT line with country + language + region."""
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        assert "Bahrain" in prompt
        assert "Arabic" in prompt
        assert "Northern" in prompt


# ============================================
# C.5.2: Cohort block skipped for population match (negative)
# ============================================


class TestCohortBlockSkipped:
    def test_block_skipped_for_population_match(self):
        """Population fallback → no priors block (too generic per design 4.1)."""
        from app.services.extraction_service import _build_preferences_prompt

        with _patch_cohort_modal({"top_deciding_factor": "Quality"}):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=POPULATION_MATCH_PROFILE
            )
        assert "COHORT-LEVEL PRIORS" not in prompt, (
            "Population aggregate is too generic — block should be skipped"
        )

    def test_block_skipped_for_broadened_age(self):
        """broadened_age is not in the inject-allowed list per design 4.1."""
        from app.services.extraction_service import _build_preferences_prompt

        profile = {
            **STRONG_MATCH_PROFILE,
            "cohort_match": {
                **STRONG_MATCH_PROFILE["cohort_match"],
                "match_quality": "broadened_age",
                "confidence": "medium",
            },
        }
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(VALID_PREFS, demographics_profile=profile)

        # broadened_age is too broad — no block per design 4.1
        assert "COHORT-LEVEL PRIORS" not in prompt

    def test_block_skipped_for_no_demographics_profile(self):
        """No demographics_profile → no block."""
        from app.services.extraction_service import _build_preferences_prompt

        prompt = _build_preferences_prompt(VALID_PREFS, demographics_profile=None)
        assert "COHORT-LEVEL PRIORS" not in prompt

    def test_block_skipped_when_no_cohort_match(self):
        """Profile present but cohort_match is None → no block."""
        from app.services.extraction_service import _build_preferences_prompt

        prompt = _build_preferences_prompt(
            VALID_PREFS, demographics_profile={"age_group": "25-34", "cohort_match": None}
        )
        assert "COHORT-LEVEL PRIORS" not in prompt


# ============================================
# C.5.3: Feature flag ENABLE_COHORT_PERSONALIZATION
# ============================================


class TestFeatureFlag:
    def test_block_skipped_when_feature_flag_off(self, monkeypatch):
        """ENABLE_COHORT_PERSONALIZATION=false → skip injection per design 6.6."""
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "false")
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        assert "COHORT-LEVEL PRIORS" not in prompt, (
            "Feature flag off must skip cohort block injection"
        )

    def test_block_injected_when_feature_flag_on(self, monkeypatch):
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        assert "COHORT-LEVEL PRIORS" in prompt or "cohort" in prompt.lower()

    def test_default_flag_state_is_false(self, monkeypatch):
        """Per design 6.6 + plan A.5.4: default for ENABLE_COHORT_PERSONALIZATION is false."""
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.delenv("ENABLE_COHORT_PERSONALIZATION", raising=False)
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        # Default off → no block
        assert "COHORT-LEVEL PRIORS" not in prompt


# ============================================
# C.5.4: PRIVACY ASSERTION (CRITICAL)
# ============================================


class TestPromptPrivacy:
    """No RAW demographics in rendered prompt — only aggregate stats."""

    def test_no_raw_age_value_in_prompt(self, monkeypatch):
        """Raw 25-34 must NEVER appear in the prompt sent to OpenAI."""
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        # The raw age token "25-34" must not appear (cohort findings reference
        # the cohort, not the individual's age)
        assert "25-34" not in prompt, (
            "PRIVACY VIOLATION: raw age 25-34 leaked into prompt — "
            "design 4.5 requires age stays server-side"
        )

    def test_no_raw_gender_value_in_prompt(self, monkeypatch):
        """Raw gender 'Female' must NEVER appear in prompt."""
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        # Note: 'female' may appear as a substring of unrelated words; check the
        # standalone token (with word boundary) by scanning for the literal value
        import re

        assert not re.search(r"\bFemale\b", prompt), (
            "PRIVACY VIOLATION: raw gender 'Female' leaked into prompt"
        )

    def test_no_raw_identity_field_name_in_prompt(self, monkeypatch):
        """Identity (Bahraini/resident) is sensitive — must never appear per design 4.3."""
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
        profile_with_identity = {
            **STRONG_MATCH_PROFILE,
            "identity": "Bahraini",
        }
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=profile_with_identity
            )
        assert "Bahraini" not in prompt, (
            "PRIVACY VIOLATION: identity field 'Bahraini' must not appear in prompt"
        )

    def test_country_language_region_allowed(self, monkeypatch):
        """The thin context line CAN mention country + language + region per design 4.3."""
        from app.services.extraction_service import _build_preferences_prompt

        monkeypatch.setenv("ENABLE_COHORT_PERSONALIZATION", "true")
        with _patch_cohort_modal(SAMPLE_COHORT_MODAL):
            prompt = _build_preferences_prompt(
                VALID_PREFS, demographics_profile=STRONG_MATCH_PROFILE
            )
        # These three are EXPLICITLY allowed per design — they help GPT localize
        assert "Bahrain" in prompt
        assert "Arabic" in prompt
        assert "Northern" in prompt


# ============================================
# A.5.4 + Backwards compat: signature accepts legacy single-arg form
# ============================================


class TestBackwardsCompat:
    def test_signature_works_without_demographics_profile(self):
        """Existing callers pass only user_preferences — must not break."""
        from app.services.extraction_service import _build_preferences_prompt

        prompt = _build_preferences_prompt(VALID_PREFS)
        # Existing personalization block should still render
        assert "User Preferences" in prompt or "priorities" in prompt.lower()

    def test_signature_works_with_demographics_profile_none(self):
        """Explicit None for demographics_profile is supported."""
        from app.services.extraction_service import _build_preferences_prompt

        prompt = _build_preferences_prompt(VALID_PREFS, demographics_profile=None)
        assert "User Preferences" in prompt or "priorities" in prompt.lower()
        assert "COHORT-LEVEL PRIORS" not in prompt

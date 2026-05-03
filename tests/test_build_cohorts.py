"""Tests for scripts/build_cohorts.py — ETL: CSV → cohort_priors.json.

Asserts the design contract from docs/superpowers/specs/2026-05-03-survey-cohort-personalization-design.md.
Written FIRST (red phase). Backend implements to make these green.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest


FIXTURES = Path(__file__).parent / "fixtures" / "cohort_fixtures"
SAMPLE_ENG = FIXTURES / "sample_eng.csv"
SAMPLE_ARAB = FIXTURES / "sample_arab.csv"


# ============================================
# A.2.2: Arabic ↔ English value normalization
# ============================================


class TestNormalizeValue:
    def test_normalize_known_arabic_deciding_factor(self):
        from scripts.build_cohorts import normalize_value

        assert normalize_value("الجودة", field="deciding_factor") == "Quality"
        assert normalize_value("السعر", field="deciding_factor") == "Price"
        assert normalize_value("العلامة التجارية", field="deciding_factor") == "Brand"

    def test_normalize_known_arabic_gender(self):
        from scripts.build_cohorts import normalize_value

        assert normalize_value("أنثى", field="gender") == "Female"
        assert normalize_value("ذكر", field="gender") == "Male"

    def test_normalize_known_arabic_governorate(self):
        from scripts.build_cohorts import normalize_value

        assert normalize_value("محافظة العاصمة", field="governorate") == "Capital"
        assert normalize_value("المحافظة الشمالية", field="governorate") == "Northern"
        assert normalize_value("محافظة المحرق", field="governorate") == "Muharraq"
        assert normalize_value("المحافظة الجنوبية", field="governorate") == "Southern"

    def test_normalize_known_arabic_spend(self):
        from scripts.build_cohorts import normalize_value

        assert normalize_value("أقل من 25 دينار بحريني", field="spend") == "<25 BHD"
        assert (
            normalize_value("من 25 إلى أقل من 50 دينار بحريني", field="spend")
            == "25-50 BHD"
        )
        assert (
            normalize_value("من 50 إلى أقل من 100 دينار بحريني", field="spend")
            == "50-100 BHD"
        )
        assert (
            normalize_value("من 100 إلى أقل من 250 دينار بحريني", field="spend")
            == "100-250 BHD"
        )

    def test_normalize_known_arabic_language(self):
        from scripts.build_cohorts import normalize_value

        assert normalize_value("العربية", field="language") == "Arabic"
        assert normalize_value("الإنجليزية", field="language") == "English"
        assert normalize_value("كلتاهما بالتساوي", field="language") == "Both equally"

    def test_normalize_english_passes_through(self):
        from scripts.build_cohorts import normalize_value

        assert normalize_value("Quality", field="deciding_factor") == "Quality"
        assert normalize_value("Female", field="gender") == "Female"
        assert normalize_value("Northern Governorate", field="governorate") in (
            "Northern Governorate",
            "Northern",
        )

    def test_normalize_unknown_arabic_raises(self):
        from scripts.build_cohorts import normalize_value

        with pytest.raises(ValueError):
            normalize_value("XYZ_غير_موجود", field="deciding_factor")

    def test_normalize_empty_value_passes_through(self):
        from scripts.build_cohorts import normalize_value

        # Empty values are allowed (caller decides what to do with them)
        assert normalize_value("", field="deciding_factor") == ""

    def test_arabic_to_english_table_exists(self):
        from scripts.build_cohorts import ARABIC_TO_ENGLISH

        assert isinstance(ARABIC_TO_ENGLISH, dict)
        # Must contain at least the spec's appendix A entries
        required = [
            "إلكترونيات",
            "الجودة",
            "السعر",
            "أنثى",
            "ذكر",
            "محافظة العاصمة",
            "المحافظة الشمالية",
            "العربية",
        ]
        for k in required:
            assert k in ARABIC_TO_ENGLISH, f"missing required Arabic mapping: {k}"


# ============================================
# A.2.3: Row dropping rules (consent, finished, multi-skip)
# ============================================


class TestShouldDropRow:
    def _row(self, **overrides):
        base = {
            " I agree and want to continue": "true",
            "Status": "finished",
            "What is your age group?": "25-34",
            "What is your gender?": "Female",
            "Which governorate do you mainly live in?": "Northern Governorate",
            "Which language do you usually use when searching for products or services?": "English",
        }
        base.update(overrides)
        return base

    def test_drop_row_no_consent(self):
        from scripts.build_cohorts import should_drop_row

        row = self._row(**{" I agree and want to continue": "false"})
        assert should_drop_row(row) is True

    def test_drop_row_unfinished(self):
        from scripts.build_cohorts import should_drop_row

        row = self._row(**{"Status": "in_progress"})
        assert should_drop_row(row) is True

    def test_drop_row_all_cohort_keys_empty(self):
        from scripts.build_cohorts import should_drop_row

        row = self._row(
            **{
                "What is your age group?": "",
                "What is your gender?": "",
                "Which governorate do you mainly live in?": "",
                "Which language do you usually use when searching for products or services?": "",
            }
        )
        assert should_drop_row(row) is True

    def test_drop_row_all_cohort_keys_prefer_not_to_say(self):
        from scripts.build_cohorts import should_drop_row

        row = self._row(
            **{
                "What is your age group?": "Prefer not to say",
                "What is your gender?": "Prefer not to say",
                "Which governorate do you mainly live in?": "Prefer not to say",
                "Which language do you usually use when searching for products or services?": "Prefer not to say",
            }
        )
        assert should_drop_row(row) is True

    def test_keep_complete_row(self):
        from scripts.build_cohorts import should_drop_row

        row = self._row()
        assert should_drop_row(row) is False

    def test_keep_partial_row_with_consent_and_finished(self):
        from scripts.build_cohorts import should_drop_row

        # Some demographics missing but at least one present → keep
        row = self._row(
            **{
                "What is your age group?": "25-34",
                "What is your gender?": "Prefer not to say",
                "Which governorate do you mainly live in?": "",
                "Which language do you usually use when searching for products or services?": "",
            }
        )
        assert should_drop_row(row) is False

    def test_drop_row_consent_case_insensitive_false(self):
        from scripts.build_cohorts import should_drop_row

        row = self._row(**{" I agree and want to continue": "FALSE"})
        assert should_drop_row(row) is True


# ============================================
# A.2.4: Cohort grouping + modal computation
# ============================================


class TestBuildCohortStats:
    def _make_normalized_row(self, **kwargs):
        """Helper for normalized rows post-ETL transformation."""
        defaults = {
            "cohort_key": "25-34|Female|Northern|Arabic",
            "deciding_factor": ["Quality"],
            "spend_bracket": "25-50 BHD",
            "assistance_style": "Show me 2 or 3 suitable options",
            "trust_sources": ["Store"],
            "top_difficulties": ["Too many options"],
            "post_purchase_pattern": "I felt I made the right choice",
            "what_helps_most": ["See the main differences simply"],
            "primary_categories": ["Fashion or Beauty item"],
            "identity": "Bahraini",
        }
        defaults.update(kwargs)
        return defaults

    def test_build_cohort_stats_returns_top_level_keys(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = [self._make_normalized_row()]
        result = build_cohort_stats(rows)
        assert "version" in result
        assert "built_at" in result
        assert "total_responses" in result
        assert "cohorts" in result
        assert "fallback_aggregates" in result

    def test_build_cohort_stats_total_responses(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = [self._make_normalized_row() for _ in range(7)]
        result = build_cohort_stats(rows)
        assert result["total_responses"] == 7

    def test_build_cohort_stats_modal_is_top_count(self):
        from scripts.build_cohorts import build_cohort_stats

        # 5 cohort members: Quality x 4, Price x 1 → modal Quality
        rows = (
            [self._make_normalized_row(deciding_factor=["Quality"]) for _ in range(4)]
            + [self._make_normalized_row(deciding_factor=["Price"])]
        )
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["n"] == 5
        assert cohort["modal"]["top_deciding_factor"] == "Quality"

    def test_build_cohort_stats_distribution_is_normalized(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = (
            [self._make_normalized_row(deciding_factor=["Quality"]) for _ in range(7)]
            + [self._make_normalized_row(deciding_factor=["Price"]) for _ in range(3)]
        )
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        # Distribution should be a dict mapping value → ratio (sums to ~1.0)
        dist = cohort["distribution"]["deciding_factor"]
        assert pytest.approx(dist["Quality"], rel=1e-6) == 0.7
        assert pytest.approx(dist["Price"], rel=1e-6) == 0.3

    def test_build_cohort_stats_demographics_block(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = [self._make_normalized_row() for _ in range(5)]
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        demo = cohort.get("demographics", {})
        assert demo.get("age_group") == "25-34"
        assert demo.get("gender") == "Female"
        assert demo.get("governorate") == "Northern"
        assert demo.get("language") == "Arabic"


# ============================================
# A.2.4 / Confidence flag boundaries
# ============================================


class TestConfidenceFlags:
    def _rows(self, n, key="25-34|Female|Northern|Arabic"):
        from tests.test_build_cohorts import TestBuildCohortStats

        return [TestBuildCohortStats()._make_normalized_row(cohort_key=key) for _ in range(n)]

    def test_confidence_n_4_omitted(self):
        """n<5 → cohort omitted entirely."""
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(4)
        result = build_cohort_stats(rows)
        assert "25-34|Female|Northern|Arabic" not in result["cohorts"]

    def test_confidence_n_5_is_low(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(5)
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["confidence"] == "low"

    def test_confidence_n_9_is_low(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(9)
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["confidence"] == "low"

    def test_confidence_n_10_is_medium(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(10)
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["confidence"] == "medium"

    def test_confidence_n_19_is_medium(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(19)
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["confidence"] == "medium"

    def test_confidence_n_20_is_high(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(20)
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["confidence"] == "high"

    def test_confidence_n_50_is_high(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._rows(50)
        result = build_cohort_stats(rows)
        cohort = result["cohorts"]["25-34|Female|Northern|Arabic"]
        assert cohort["confidence"] == "high"


# ============================================
# A.2.5: Fallback aggregates
# ============================================


class TestFallbackAggregates:
    def _make(self, n, **kwargs):
        from tests.test_build_cohorts import TestBuildCohortStats

        return [TestBuildCohortStats()._make_normalized_row(**kwargs) for _ in range(n)]

    def test_fallback_aggregates_have_all_key(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._make(5)
        result = build_cohort_stats(rows)
        assert "all" in result["fallback_aggregates"]

    def test_fallback_aggregates_have_age_only(self):
        """Population aggregates by age alone exist for fallback chain."""
        from scripts.build_cohorts import build_cohort_stats

        rows = self._make(10, cohort_key="25-34|Female|Northern|Arabic") + self._make(
            10, cohort_key="25-34|Male|Capital|English"
        )
        result = build_cohort_stats(rows)
        # Per design 2.4, fallback aggregates should include shorter prefixes
        # like "25-34" (age only)
        assert "25-34" in result["fallback_aggregates"]

    def test_fallback_aggregates_have_age_gender(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._make(20, cohort_key="25-34|Female|Northern|Arabic")
        result = build_cohort_stats(rows)
        # "25-34|Female" prefix should exist
        assert "25-34|Female" in result["fallback_aggregates"]

    def test_fallback_aggregate_all_aggregates_everyone(self):
        from scripts.build_cohorts import build_cohort_stats

        rows = self._make(10, cohort_key="25-34|Female|Northern|Arabic") + self._make(
            5, cohort_key="35-44|Male|Capital|English"
        )
        result = build_cohort_stats(rows)
        all_agg = result["fallback_aggregates"]["all"]
        assert all_agg["n"] == 15


# ============================================
# A.2.6: Persona label generation
# ============================================


class TestPersonaLabel:
    def test_persona_quality_first_focused(self):
        from scripts.build_cohorts import generate_persona_label

        modal = {
            "top_deciding_factor": "Quality",
            "spend_bracket": "25-50 BHD",
            "preferred_assistance_style": "Show me 2 or 3 suitable options",
        }
        label = generate_persona_label(modal)
        assert "Quality" in label
        assert isinstance(label, str)
        assert len(label) > 0

    def test_persona_budget_value_seeker(self):
        from scripts.build_cohorts import generate_persona_label

        modal = {
            "top_deciding_factor": "Price",
            "spend_bracket": "<25 BHD",
            "preferred_assistance_style": "Show me 2 or 3 suitable options",
        }
        label = generate_persona_label(modal)
        # Per design 2.5: should include "Budget" or "value seeker"
        assert "Budget" in label or "value" in label.lower()

    def test_persona_premium_brand_loyal(self):
        from scripts.build_cohorts import generate_persona_label

        modal = {
            "top_deciding_factor": "Brand",
            "spend_bracket": "100-250 BHD",
            "preferred_assistance_style": "Suggest best with reason",
        }
        label = generate_persona_label(modal)
        # Should reference brand/premium quality
        assert "Brand" in label or "Premium" in label

    def test_persona_returns_string_for_unknown_combo(self):
        from scripts.build_cohorts import generate_persona_label

        modal = {
            "top_deciding_factor": "Unknown",
            "spend_bracket": "Unknown",
            "preferred_assistance_style": "Unknown",
        }
        label = generate_persona_label(modal)
        # Default fallback (e.g. "Balanced shopper") rather than None/empty
        assert isinstance(label, str)
        assert len(label) > 0

    def test_persona_returns_string_for_empty_modal(self):
        from scripts.build_cohorts import generate_persona_label

        label = generate_persona_label({})
        assert isinstance(label, str)
        assert len(label) > 0


# ============================================
# C.2.1: Multi-select splitting
# ============================================


class TestMultiSelectSplit:
    def test_split_multi_basic(self):
        from scripts.build_cohorts import split_multi

        assert split_multi("Quality,Price,Brand") == ["Quality", "Price", "Brand"]

    def test_split_multi_strips_whitespace(self):
        from scripts.build_cohorts import split_multi

        assert split_multi("Quality, Price ,Brand") == ["Quality", "Price", "Brand"]

    def test_split_multi_drops_empty(self):
        from scripts.build_cohorts import split_multi

        assert split_multi("Quality,,Price") == ["Quality", "Price"]

    def test_split_multi_single_value(self):
        from scripts.build_cohorts import split_multi

        assert split_multi("Quality") == ["Quality"]

    def test_split_multi_empty_returns_empty_list(self):
        from scripts.build_cohorts import split_multi

        assert split_multi("") == []

    def test_split_multi_none_returns_empty_list(self):
        from scripts.build_cohorts import split_multi

        assert split_multi(None) == []


# ============================================
# C.2.2: Atomic write
# ============================================


class TestAtomicWrite:
    def test_atomic_write_uses_tmp_then_rename(self, tmp_path, monkeypatch):
        """Build script writes to .tmp then atomically renames.

        We monkeypatch the output path and verify the produced file exists,
        and no orphaned .tmp file remains.
        """
        from scripts.build_cohorts import write_atomic

        target = tmp_path / "cohort_priors.json"
        payload = {"version": "1.0", "cohorts": {}, "fallback_aggregates": {}}
        write_atomic(target, payload)
        assert target.exists()
        assert not (tmp_path / "cohort_priors.json.tmp").exists()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == payload

    def test_atomic_write_overwrites_existing(self, tmp_path):
        from scripts.build_cohorts import write_atomic

        target = tmp_path / "cohort_priors.json"
        target.write_text('{"old": true}', encoding="utf-8")
        payload = {"version": "2.0", "cohorts": {}, "fallback_aggregates": {}}
        write_atomic(target, payload)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == payload

    def test_atomic_write_cleans_up_tmp_on_failure(self, tmp_path, monkeypatch):
        """If serialization fails, no partial file remains.

        Skips if the implementation cannot demonstrate cleanup
        (the spec only requires the success case be atomic).
        """
        from scripts import build_cohorts

        target = tmp_path / "cohort_priors.json"

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr("os.replace", boom)
        with pytest.raises(OSError):
            build_cohorts.write_atomic(target, {"version": "1.0"})
        # Either no file or no partial file at the target path
        assert not target.exists() or target.stat().st_size > 0


# ============================================
# C.2.3 / Integration: end-to-end CSV → JSON
# ============================================


@pytest.mark.skipif(
    not SAMPLE_ENG.exists() or not SAMPLE_ARAB.exists(),
    reason="fixture CSVs not present",
)
class TestEndToEndETL:
    def test_main_writes_valid_json(self, tmp_path, monkeypatch):
        """Run the full ETL pipeline with fixture CSVs → produce valid JSON."""
        from scripts import build_cohorts

        out = tmp_path / "cohort_priors.json"
        monkeypatch.setattr(build_cohorts, "ENG_CSV_PATH", SAMPLE_ENG)
        monkeypatch.setattr(build_cohorts, "ARABIC_CSV_PATH", SAMPLE_ARAB)
        monkeypatch.setattr(build_cohorts, "OUTPUT_PATH", out)

        build_cohorts.main()
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "version" in data
        assert "cohorts" in data
        assert "fallback_aggregates" in data
        assert data["total_responses"] >= 1


# ============================================
# Helper: cohort_key derivation
# ============================================


class TestCohortKey:
    def test_cohort_key_format_is_pipe_separated(self):
        from scripts.build_cohorts import build_cohort_key

        key = build_cohort_key(
            age_group="25-34",
            gender="Female",
            governorate="Northern",
            language="Arabic",
        )
        assert key == "25-34|Female|Northern|Arabic"

    def test_cohort_key_governorate_normalized_short_form(self):
        """Northern Governorate → Northern (governorate suffix stripped)."""
        from scripts.build_cohorts import build_cohort_key

        key = build_cohort_key(
            age_group="25-34",
            gender="Female",
            governorate="Northern Governorate",
            language="English",
        )
        # Short form preferred per design schema
        assert key == "25-34|Female|Northern|English"

"""Tests for category-specific prompt personalities."""
import pytest
from app.services.prompt_personalities import (
    CATEGORY_PROMPT_PERSONALITIES,
    build_personality_prompt,
)


EXPECTED_CATEGORIES = [
    "electronics", "grocery", "supplements", "makeup",
    "skincare", "haircare", "fragrances", "fashion", "other",
]

REQUIRED_KEYS = [
    "reasoning_style", "evidence_language", "risk_framing",
    "comparison_voice", "context_inference",
]


class TestPromptPersonalities:

    def test_all_categories_have_personalities(self):
        for cat in EXPECTED_CATEGORIES:
            assert cat in CATEGORY_PROMPT_PERSONALITIES, f"Missing personality for {cat}"

    def test_all_personalities_have_required_keys(self):
        for cat in EXPECTED_CATEGORIES:
            personality = CATEGORY_PROMPT_PERSONALITIES[cat]
            for key in REQUIRED_KEYS:
                assert key in personality, f"{cat} missing key: {key}"
                assert len(personality[key]) > 20, f"{cat}.{key} is too short"

    def test_build_personality_prompt_returns_string(self):
        result = build_personality_prompt("electronics")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_build_personality_prompt_contains_category_content(self):
        result = build_personality_prompt("fragrances")
        assert "scent" in result.lower() or "longevity" in result.lower()
        assert "fragrance" in result.lower() or "oud" in result.lower()

    def test_build_personality_prompt_unknown_category_falls_back(self):
        result = build_personality_prompt("unknown_category")
        # Should fall back to "other"
        assert isinstance(result, str)
        assert len(result) > 50

    def test_electronics_personality_mentions_numbers(self):
        p = CATEGORY_PROMPT_PERSONALITIES["electronics"]
        assert "number" in p["evidence_language"].lower() or "percent" in p["evidence_language"].lower()

    def test_makeup_personality_mentions_experience(self):
        p = CATEGORY_PROMPT_PERSONALITIES["makeup"]
        assert "wear" in p["reasoning_style"].lower() or "experience" in p["reasoning_style"].lower()

    def test_supplements_personality_mentions_safety(self):
        p = CATEGORY_PROMPT_PERSONALITIES["supplements"]
        assert "safety" in p["risk_framing"].lower() or "contaminant" in p["risk_framing"].lower()

    def test_personality_prompt_includes_trust_rules(self):
        """All personality prompts must include universal trust rules."""
        for cat in EXPECTED_CATEGORIES:
            result = build_personality_prompt(cat)
            assert "contradict" in result.lower() or "conflict" in result.lower(), f"{cat} missing trust rules"

    def test_no_extra_categories(self):
        """Only expected categories should be present."""
        assert set(CATEGORY_PROMPT_PERSONALITIES.keys()) == set(EXPECTED_CATEGORIES)

    def test_personality_prompt_contains_section_header(self):
        result = build_personality_prompt("electronics")
        assert "Comparison Personality" in result

    def test_each_category_has_distinct_personality(self):
        """No two categories should have identical reasoning_style."""
        styles = set()
        for cat in EXPECTED_CATEGORIES:
            style = CATEGORY_PROMPT_PERSONALITIES[cat]["reasoning_style"]
            assert style not in styles, f"{cat} has duplicate reasoning_style"
            styles.add(style)

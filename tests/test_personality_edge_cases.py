"""
Edge-case tests for category-specific prompt personalities.

These tests should FAIL (red) until prompt_personalities.py is created.
"""
import pytest


class TestPersonalityEdgeCases:
    """Edge cases for prompt personality system."""

    def test_empty_category_falls_back_to_other(self):
        from app.services.prompt_personalities import build_personality_prompt
        result = build_personality_prompt("")
        assert isinstance(result, str)
        assert len(result) > 50

    def test_none_category_falls_back_to_other(self):
        from app.services.prompt_personalities import build_personality_prompt
        result = build_personality_prompt(None)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_mixed_case_category_handled(self):
        from app.services.prompt_personalities import build_personality_prompt
        # Categories should be lowercase, but mixed case shouldn't crash
        result = build_personality_prompt("Electronics")
        assert isinstance(result, str)
        assert len(result) > 50

    def test_uppercase_category_handled(self):
        from app.services.prompt_personalities import build_personality_prompt
        result = build_personality_prompt("FASHION")
        assert isinstance(result, str)
        assert len(result) > 50

    def test_personality_prompt_token_budget(self):
        """Personality prompt should not be excessively long (rough char check).
        A prompt over 5000 chars is likely too costly in token budget.
        """
        from app.services.prompt_personalities import (
            CATEGORY_PROMPT_PERSONALITIES,
            build_personality_prompt,
        )
        for cat in CATEGORY_PROMPT_PERSONALITIES:
            result = build_personality_prompt(cat)
            assert len(result) < 5000, f"{cat} personality prompt is {len(result)} chars, exceeds 5000 budget"

    def test_all_categories_produce_different_prompts(self):
        """No two categories should produce identical personality prompts."""
        from app.services.prompt_personalities import (
            CATEGORY_PROMPT_PERSONALITIES,
            build_personality_prompt,
        )
        prompts = {}
        for cat in CATEGORY_PROMPT_PERSONALITIES:
            prompts[cat] = build_personality_prompt(cat)

        seen = set()
        for cat, prompt in prompts.items():
            assert prompt not in seen, f"{cat} has duplicate prompt with another category"
            seen.add(prompt)

    def test_personality_values_are_nonempty_strings(self):
        """Every personality field value must be a non-empty string."""
        from app.services.prompt_personalities import CATEGORY_PROMPT_PERSONALITIES
        required_keys = [
            "reasoning_style", "evidence_language", "risk_framing",
            "comparison_voice", "context_inference",
        ]
        for cat, personality in CATEGORY_PROMPT_PERSONALITIES.items():
            for key in required_keys:
                val = personality.get(key)
                assert isinstance(val, str), f"{cat}.{key} is not a string: {type(val)}"
                assert len(val.strip()) > 0, f"{cat}.{key} is empty/whitespace-only"

    def test_trust_rules_present_in_all_prompts(self):
        """Universal trust rules must appear in every personality prompt."""
        from app.services.prompt_personalities import (
            CATEGORY_PROMPT_PERSONALITIES,
            build_personality_prompt,
        )
        for cat in CATEGORY_PROMPT_PERSONALITIES:
            result = build_personality_prompt(cat)
            # Check for at least one trust-related keyword
            lower = result.lower()
            has_trust = (
                "contradict" in lower
                or "conflict" in lower
                or "trust" in lower
                or "mandatory" in lower
            )
            assert has_trust, f"{cat} prompt missing trust rules"

    def test_unknown_category_does_not_crash(self):
        """Completely unknown category names should gracefully fallback."""
        from app.services.prompt_personalities import build_personality_prompt
        for bad_cat in ["", "   ", "nonexistent", "123", "electronics!", None]:
            result = build_personality_prompt(bad_cat)
            assert isinstance(result, str)
            assert len(result) > 50

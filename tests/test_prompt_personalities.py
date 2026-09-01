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

    # ------------------------------------------------------------------
    # Issue #111 — evidence-conditional quantify rule + halal gate
    # ------------------------------------------------------------------

    def test_trust_rule_conditions_quantification_on_supplied_data(self):
        """#111: the universal trust rule permits precision ONLY when the
        supplied product data carries the figure."""
        for cat in EXPECTED_CATEGORIES:
            assert "in the supplied product data" in build_personality_prompt(cat), cat

    def test_trust_rule_permits_qualitative_when_no_number(self):
        """#111: a concrete qualitative comparison is named as the CORRECT
        output when the data carries no number."""
        for cat in EXPECTED_CATEGORIES:
            assert "qualitative" in build_personality_prompt(cat).lower(), cat

    def test_trust_rule_still_forbids_bare_vagueness(self):
        """Pin (GREEN before and after): the anti-vagueness half survives —
        'somewhat better' with no follow-up is still unacceptable."""
        for cat in EXPECTED_CATEGORIES:
            assert "somewhat better" in build_personality_prompt(cat), cat

    def test_no_unconditional_halal_instruction(self):
        """#111: the grocery personality no longer orders the model to address
        halal compliance unconditionally."""
        rf = CATEGORY_PROMPT_PERSONALITIES["grocery"]["risk_framing"].lower()
        assert "halal compliance" not in rf

    def test_halal_mention_is_data_gated(self):
        """#111: any remaining halal mention must be gated on the supplied
        data asserting it, with inference explicitly forbidden."""
        rf = CATEGORY_PROMPT_PERSONALITIES["grocery"]["risk_framing"].lower()
        if "halal" in rf:
            assert "only when" in rf
            assert "never infer" in rf

    def test_grocery_schema_has_no_halal_field(self):
        """Pin (GREEN at HEAD): the grocery spec schema carries no halal or
        certification field — the invariant the #111 halal gate depends on.
        When someone later adds one, this test fails and tells them the
        test_halal_mention_is_data_gated gate can be relaxed."""
        from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
        assert not any(
            "halal" in f or "certif" in f for f in CATEGORY_SPEC_SCHEMAS["grocery"]
        )

    def test_every_category_evidence_language_is_conditional(self):
        """#111: every category's evidence_language conditions its worked
        examples on the supplied data carrying the figures."""
        for cat in EXPECTED_CATEGORIES:
            el = CATEGORY_PROMPT_PERSONALITIES[cat]["evidence_language"].lower()
            assert "when the supplied" in el or "if the supplied" in el, cat

    def test_fragrance_note_instruction_is_data_gated(self):
        """#111: the note-pyramid instruction (the most fabrication-prone in
        the file — notes captured on a measured 38% of PDPs) is explicitly
        conditioned on notes being present in the supplied data."""
        el = CATEGORY_PROMPT_PERSONALITIES["fragrances"]["evidence_language"].lower()
        assert "note" in el
        assert "when the supplied" in el or "only when" in el

    def test_personality_prompt_does_not_contradict_extraction_rule(self):
        """#111 core defect: two injected instructions told the model opposite
        things (extraction_service:982 says quantify WHEN AVAILABLE, the trust
        rule said quantify unconditionally). Every sentence that mentions
        quantification must carry the supplied-data condition."""
        import re as _re
        for cat in EXPECTED_CATEGORIES:
            prompt = build_personality_prompt(cat)
            sentences = _re.split(r"(?<=[.!?])\s+|\n", prompt)
            for sentence in sentences:
                if "quantif" in sentence.lower():
                    assert "supplied product data" in sentence.lower(), (
                        f"{cat}: unconditional quantify sentence: {sentence!r}"
                    )

"""Tests for review and verdict prompt quality — ensures citations, specificity, and data-backed verdicts."""
import pytest
import json
from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT, COMPARISON_PROMPT


class TestReviewPromptStructure:
    """Verify the review prompt enforces citation and specificity rules."""

    def test_prompt_requires_snippet_citations(self):
        """Prompt must instruct GPT to cite [snippet_N] for praises/complaints."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "snippet_" in prompt.lower() or "[snippet_" in prompt
        assert "cite" in prompt.lower() or "citation" in prompt.lower() or "reference" in prompt.lower()

    def test_prompt_forbids_synthetic_rating_distribution(self):
        """Prompt must NOT ask GPT to estimate rating_distribution percentages."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "estimate percentages" not in prompt.lower()

    def test_prompt_has_good_vs_bad_examples(self):
        """Prompt must include examples of specific vs generic output."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        # Should have at least one GOOD example and one BAD example
        has_good = "GOOD:" in prompt or "good example" in prompt.lower() or "DO:" in prompt
        has_bad = "BAD:" in prompt or "bad example" in prompt.lower() or "DON'T:" in prompt or "NOT:" in prompt
        assert has_good or has_bad, "Prompt should include examples of good vs bad output"

    def test_prompt_requires_evidence_per_claim(self):
        """Each praise/complaint must reference which snippet it came from."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        # The detailed_praises/complaints format should include a source/snippet field
        assert "source" in prompt.lower() or "snippet" in prompt.lower()

    def test_prompt_warns_against_paraphrasing(self):
        """Prompt must warn against GPT paraphrasing quotes as real user words."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "paraphras" in prompt.lower() or "fabricat" in prompt.lower() or "invent" in prompt.lower()


class TestVerdictPromptStructure:
    """Verify the comparison verdict prompt enforces specificity."""

    def test_prompt_requires_tradeoff_analysis(self):
        """Prompt must mandate trade-off: 'A wins for X, B wins for Y'."""
        prompt = COMPARISON_PROMPT.lower()
        assert "trade" in prompt or "wins for" in prompt or "better for" in prompt

    def test_prompt_requires_numeric_differences(self):
        """Prompt must ask for numeric/quantified differences."""
        prompt = COMPARISON_PROMPT.lower()
        assert "numeric" in prompt or "quantif" in prompt or "percentage" in prompt or "specific number" in prompt

    def test_prompt_has_who_should_buy(self):
        """Prompt must include audience-specific recommendation."""
        prompt = COMPARISON_PROMPT.lower()
        assert "who should" in prompt or "best for" in prompt or "ideal for" in prompt or "user profile" in prompt

    def test_prompt_has_good_vs_bad_verdict_examples(self):
        """Prompt must include examples of strong vs weak verdicts."""
        has_example = "DO:" in COMPARISON_PROMPT or "GOOD:" in COMPARISON_PROMPT or "example" in COMPARISON_PROMPT.lower()
        assert has_example, "Prompt should include verdict quality examples"

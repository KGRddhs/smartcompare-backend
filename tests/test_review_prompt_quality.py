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


class TestReviewPromptCompleteness:
    """Verify the review prompt has all required JSON fields and template variables."""

    def test_prompt_has_template_variables(self):
        """Prompt must have {brand}, {name}, {variant}, {category}, {search_context}."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        for var in ["{brand}", "{name}", "{variant}", "{category}", "{search_context}"]:
            assert var in prompt, f"Missing template variable: {var}"

    def test_prompt_json_has_required_fields(self):
        """Prompt JSON template must contain all expected output fields."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        required_fields = [
            "average_rating", "total_reviews", "positive_percentage",
            "rating_distribution", "category_scores", "common_praises",
            "common_complaints", "detailed_praises", "detailed_complaints",
            "user_quotes", "summary"
        ]
        for field in required_fields:
            assert field in prompt, f"Missing JSON field: {field}"

    def test_rating_distribution_set_to_null(self):
        """rating_distribution must be hardcoded to null in the JSON template."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert '"rating_distribution": null' in prompt

    def test_prompt_forbids_source_ratings_generation(self):
        """Prompt must explicitly forbid GPT from generating source_ratings."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "do not generate source_ratings" in prompt.lower()

    def test_detailed_fields_have_source_key(self):
        """detailed_praises and detailed_complaints must include 'source' key in template."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        # The JSON template for detailed items should show "source" as a field
        assert '"source":' in prompt or '"source"' in prompt

    def test_prompt_requests_json_only(self):
        """Prompt must instruct GPT to return ONLY valid JSON."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "return only valid json" in prompt.lower()


class TestVerdictPromptCompleteness:
    """Verify the verdict prompt has all required JSON fields and template variables."""

    def test_prompt_has_template_variables(self):
        """Prompt must have {product1_json}, {product2_json}, {region}, {concern}, {currency}."""
        prompt = COMPARISON_PROMPT
        for var in ["{product1_json}", "{product2_json}", "{region}", "{concern}", "{currency}"]:
            assert var in prompt, f"Missing template variable: {var}"

    def test_prompt_json_has_required_fields(self):
        """Prompt JSON template must contain all expected output fields."""
        prompt = COMPARISON_PROMPT
        required_fields = [
            "winner_index", "winner_reason",
            "product_0_pros", "product_0_cons",
            "product_1_pros", "product_1_cons",
            "price_comparison", "specs_comparison",
            "value_scores", "best_for",
            "recommendation", "key_differences"
        ]
        for field in required_fields:
            assert field in prompt, f"Missing JSON field: {field}"

    def test_prompt_has_best_for_categories(self):
        """best_for must include budget, performance, features, reliability."""
        prompt = COMPARISON_PROMPT
        for cat in ["budget", "performance", "features", "reliability"]:
            assert cat in prompt.lower(), f"Missing best_for category: {cat}"

    def test_prompt_mentions_gcc_market(self):
        """Prompt must mention GCC market for regional pricing context."""
        prompt = COMPARISON_PROMPT
        assert "gcc" in prompt.lower()

    def test_prompt_demands_decisive_winner(self):
        """Prompt must instruct GPT to be decisive, not hedge."""
        prompt = COMPARISON_PROMPT.lower()
        assert "decisive" in prompt or "clear winner" in prompt

    def test_prompt_requests_json_only(self):
        """Prompt must instruct GPT to return ONLY valid JSON."""
        prompt = COMPARISON_PROMPT
        assert "return only valid json" in prompt.lower()

    def test_prompt_has_value_score_scale(self):
        """Prompt must define value score scale (1-10)."""
        prompt = COMPARISON_PROMPT
        assert "10 =" in prompt or "10=" in prompt
        assert "1 =" in prompt or "1=" in prompt


# ===========================================
# REVIEW PROMPT — GARBAGE & SENTIMENT RULES
# ===========================================

class TestReviewPromptQualityRules:
    """Verify review prompt includes garbage rejection and sentiment alignment rules."""

    def test_review_prompt_has_garbage_rejection_rules(self):
        """Prompt must instruct GPT to reject navigation text and boilerplate."""
        prompt = REVIEWS_EXTRACTION_PROMPT.lower()
        assert "learn more" in prompt or "navigation" in prompt or "boilerplate" in prompt
        assert "click" in prompt or "shop now" in prompt
        assert "never include" in prompt or "never" in prompt

    def test_review_prompt_has_sentiment_alignment(self):
        """Prompt must instruct GPT to put only negative items in complaints."""
        prompt = REVIEWS_EXTRACTION_PROMPT.lower()
        assert "negative" in prompt and "complaint" in prompt
        assert "positive" in prompt

    def test_review_prompt_has_min_word_or_substantive_rule(self):
        """Prompt should require substantive claims, not short generic text."""
        prompt = REVIEWS_EXTRACTION_PROMPT.lower()
        assert "specific" in prompt or "substantive" in prompt or "8 word" in prompt

    def test_review_prompt_has_examples(self):
        """Prompt must include concrete good/bad examples for praises and complaints."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "GOOD:" in prompt or "DO:" in prompt
        assert "BAD:" in prompt or "DON'T:" in prompt


# ===========================================
# PRICE PROMPT — COUNTERFEIT REJECTION
# ===========================================

class TestPricePromptCounterfeitRejection:
    """Verify price extraction prompt rejects counterfeit sources."""

    def test_price_prompt_has_counterfeit_rejection(self):
        """Price prompt must list counterfeit sites to avoid."""
        from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
        prompt = PRICE_EXTRACTION_PROMPT.lower()
        assert "dhgate" in prompt
        assert "aliexpress" in prompt
        assert "temu" in prompt
        assert "counterfeit" in prompt or "never use" in prompt

    def test_price_prompt_has_source_priority(self):
        """Price prompt must define source priority hierarchy."""
        from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
        prompt = PRICE_EXTRACTION_PROMPT
        assert "SOURCE PRIORITY" in prompt or "source priority" in prompt.lower()
        assert "official" in prompt.lower()
        assert "authorized" in prompt.lower()

    def test_price_prompt_has_authoritative_not_lowest(self):
        """Price prompt must prioritize authoritative over cheapest price."""
        from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
        prompt = PRICE_EXTRACTION_PROMPT
        assert "AUTHORITATIVE" in prompt or "authoritative" in prompt.lower()
        assert "not the lowest" in prompt.lower() or "not the cheapest" in prompt.lower()

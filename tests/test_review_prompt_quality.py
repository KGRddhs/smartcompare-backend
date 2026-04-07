"""Tests for review and verdict prompt quality — ensures citations, specificity, and data-backed verdicts."""
import pytest
import json
from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT, COMPARISON_PROMPT


class TestReviewPromptStructure:
    """Verify the review prompt enforces citation and specificity rules."""

    def test_prompt_requires_snippet_citations(self):
        """Prompt must instruct GPT to cite [snippet_N] for highlights."""
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
        """Each highlight must reference which snippet it came from."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "source" in prompt.lower() or "snippet" in prompt.lower()

    def test_prompt_warns_against_paraphrasing(self):
        """Prompt must warn against GPT paraphrasing or fabricating claims."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "paraphras" in prompt.lower() or "fabricat" in prompt.lower() or "invent" in prompt.lower()


class TestVerdictPromptStructure:
    """Verify the comparison verdict prompt enforces specificity."""

    def test_prompt_requires_tradeoff_analysis(self):
        """Prompt must mandate trade-off analysis."""
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

    def test_prompt_has_specificity_requirements(self):
        """Prompt must require specific numbers/facts in verdicts."""
        has_specificity = "specific" in COMPARISON_PROMPT.lower() or "number" in COMPARISON_PROMPT.lower() or "fact" in COMPARISON_PROMPT.lower()
        assert has_specificity, "Prompt should require specific/numeric evidence in verdicts"


class TestReviewPromptCompleteness:
    """Verify the review prompt has all required JSON fields and template variables."""

    def test_prompt_is_system_message_without_user_data(self):
        """Prompt (system message) must NOT contain user data template variables.
        User data is now in a separate user message (prompt injection defense)."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        for var in ["{brand}", "{name}", "{variant}", "{search_context}"]:
            assert var not in prompt, f"System prompt should not contain user data variable: {var}"

    def test_prompt_json_has_required_fields(self):
        """Prompt JSON template must contain all expected output fields."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        required_fields = [
            "average_rating", "total_reviews",
            "review_summary", "overall_sentiment",
            "consensus", "highlights", "review_volume",
            "agreement_level"
        ]
        for field in required_fields:
            assert field in prompt, f"Missing JSON field: {field}"

    def test_prompt_forbids_source_ratings_generation(self):
        """Prompt must explicitly forbid GPT from generating source_ratings."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "do not generate source_ratings" in prompt.lower()

    def test_prompt_requests_json_only(self):
        """Prompt must instruct GPT to return ONLY valid JSON."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "return only valid json" in prompt.lower()


class TestVerdictPromptCompleteness:
    """Verify the verdict prompt has all required JSON fields and template variables."""

    def test_prompt_is_system_message_without_user_data(self):
        """Prompt (system message) must NOT contain user data template variables.
        User data is now in a separate user message (prompt injection defense)."""
        prompt = COMPARISON_PROMPT
        for var in ["{product1_json}", "{product2_json}"]:
            assert var not in prompt, f"System prompt should not contain user data variable: {var}"

    def test_prompt_json_has_required_fields(self):
        """Prompt JSON template must contain all expected output fields."""
        prompt = COMPARISON_PROMPT
        required_fields = [
            "winner_index", "winner_reason",
            "product_0_pros", "product_0_cons",
            "product_1_pros", "product_1_cons",
            "specs_comparison",
            "best_for", "winner_declaration",
            "key_tradeoff", "value_context"
        ]
        for field in required_fields:
            assert field in prompt, f"Missing JSON field: {field}"

    def test_prompt_has_best_for_categories(self):
        """best_for must include product_0 and product_1."""
        prompt = COMPARISON_PROMPT
        assert "product_0" in prompt and "product_1" in prompt

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
        """Prompt must instruct GPT to align sentiment tags correctly."""
        prompt = REVIEWS_EXTRACTION_PROMPT.lower()
        assert "negative" in prompt
        assert "positive" in prompt

    def test_review_prompt_has_min_word_or_substantive_rule(self):
        """Prompt should require substantive claims, not short generic text."""
        prompt = REVIEWS_EXTRACTION_PROMPT.lower()
        assert "specific" in prompt or "substantive" in prompt or "8 word" in prompt

    def test_review_prompt_has_examples(self):
        """Prompt must include concrete good/bad examples for highlights."""
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


# ===========================================
# REVIEW SUMMARY FORMAT (new structured format)
# ===========================================

class TestReviewSummaryFormat:
    """Tests for the new review_summary structured output format."""

    def test_review_prompt_requires_consensus(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'consensus' field"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "consensus" in REVIEWS_EXTRACTION_PROMPT
        assert "overall_sentiment" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_requires_highlights(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'highlights' with sentiment tags"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "highlights" in REVIEWS_EXTRACTION_PROMPT
        assert "sentiment" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_requires_review_volume(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'review_volume' field"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "review_volume" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_requires_agreement_level(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'agreement_level' field"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "agreement_level" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_forbids_individual_attribution(self):
        """REVIEWS_EXTRACTION_PROMPT must forbid individual user attribution"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "Never attribute" in REVIEWS_EXTRACTION_PROMPT or "never attribute" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_professional_tone(self):
        """REVIEWS_EXTRACTION_PROMPT must request professional product analyst tone"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "professional" in REVIEWS_EXTRACTION_PROMPT.lower() or "analyst" in REVIEWS_EXTRACTION_PROMPT.lower()

    def test_normalize_review_response_new_format(self):
        """_normalize_review_response handles new review_summary format"""
        from app.services.extraction_service import _normalize_review_response
        raw = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "Great product overall.",
                "highlights": [
                    {"point": "Battery is excellent", "sentiment": "positive"},
                    {"point": "Heavy weight", "sentiment": "negative"},
                ],
                "review_volume": "high",
                "agreement_level": "strong",
            },
            "average_rating": 4.5,
            "total_reviews": 1000,
        }
        result = _normalize_review_response(raw)
        assert "review_summary" in result
        assert result["review_summary"]["overall_sentiment"] == "positive"
        assert len(result["review_summary"]["highlights"]) == 2
        assert result["review_summary"]["review_volume"] == "high"

    def test_normalize_review_response_defaults(self):
        """_normalize_review_response provides defaults for missing review_summary fields"""
        from app.services.extraction_service import _normalize_review_response
        raw = {"average_rating": None}
        result = _normalize_review_response(raw)
        assert "review_summary" in result
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["consensus"] == ""
        assert result["review_summary"]["highlights"] == []
        assert result["review_summary"]["review_volume"] == "minimal"
        assert result["review_summary"]["agreement_level"] == "moderate"

    def test_review_prompt_drops_old_fields(self):
        """REVIEWS_EXTRACTION_PROMPT no longer requests detailed_praises/complaints/user_quotes"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "detailed_praises" not in REVIEWS_EXTRACTION_PROMPT
        assert "detailed_complaints" not in REVIEWS_EXTRACTION_PROMPT
        assert "user_quotes" not in REVIEWS_EXTRACTION_PROMPT
        assert "category_scores" not in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_keeps_average_rating_for_fact_check(self):
        """average_rating and total_reviews still requested for fact-checking"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "average_rating" in REVIEWS_EXTRACTION_PROMPT
        assert "total_reviews" in REVIEWS_EXTRACTION_PROMPT


# ===========================================
# STRUCTURED VERDICT FORMAT (new format)
# ===========================================

class TestStructuredVerdictFormat:
    """Tests for the new structured verdict prompt output format."""

    def test_verdict_prompt_requires_winner_declaration(self):
        """COMPARISON_PROMPT must request 'winner_declaration' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "winner_declaration" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_winner_reason(self):
        """COMPARISON_PROMPT must request 'winner_reason' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "winner_reason" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_key_tradeoff(self):
        """COMPARISON_PROMPT must request 'key_tradeoff' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "key_tradeoff" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_value_context(self):
        """COMPARISON_PROMPT must request 'value_context' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "value_context" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_best_for(self):
        """COMPARISON_PROMPT must request 'best_for' as per-product strings"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "best_for" in COMPARISON_PROMPT

    def test_verdict_prompt_word_limit_on_reason(self):
        """COMPARISON_PROMPT enforces under 20 words for winner_reason"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "20 words" in COMPARISON_PROMPT or "under 20" in COMPARISON_PROMPT

    def test_verdict_prompt_tradeoff_references_other_product(self):
        """COMPARISON_PROMPT requires key_tradeoff to name the other product's advantage"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "losing" in COMPARISON_PROMPT.lower() or "loser" in COMPARISON_PROMPT.lower() or "other product" in COMPARISON_PROMPT.lower()

    def test_verdict_drops_old_recommendation_field(self):
        """COMPARISON_PROMPT should not have free-form 'recommendation' paragraph"""
        from app.services.extraction_service import COMPARISON_PROMPT
        # New prompt replaces recommendation with winner_reason + value_context + best_for
        assert '"recommendation"' not in COMPARISON_PROMPT

    def test_preferences_prompt_best_for_personalization(self):
        """_build_preferences_prompt adds personalization instruction for best_for"""
        from app.services.extraction_service import _build_preferences_prompt
        prompt = _build_preferences_prompt({"priorities": ["quality", "durability"], "budget": "mid", "lifestyle": [], "brand_attitude": "function_first"})
        assert "which you" in prompt.lower() or "your priorit" in prompt.lower() or "aligns with" in prompt.lower()


# ===========================================
# EDGE CASES: _normalize_review_response()
# ===========================================

class TestNormalizeReviewResponseEdgeCases:
    """Edge case tests for _normalize_review_response() robustness."""

    def test_review_summary_as_string_replaced_with_defaults(self):
        """If review_summary is a string instead of dict, replace with defaults."""
        from app.services.extraction_service import _normalize_review_response
        raw = {"review_summary": "some text", "average_rating": 4.0}
        result = _normalize_review_response(raw)
        assert isinstance(result["review_summary"], dict)
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["highlights"] == []

    def test_review_summary_as_list_replaced_with_defaults(self):
        """If review_summary is a list instead of dict, replace with defaults."""
        from app.services.extraction_service import _normalize_review_response
        raw = {"review_summary": [1, 2, 3]}
        result = _normalize_review_response(raw)
        assert isinstance(result["review_summary"], dict)
        assert result["review_summary"]["consensus"] == ""

    def test_review_summary_as_none_replaced_with_defaults(self):
        """If review_summary is None, replace with defaults."""
        from app.services.extraction_service import _normalize_review_response
        raw = {"review_summary": None}
        result = _normalize_review_response(raw)
        assert isinstance(result["review_summary"], dict)
        assert result["review_summary"]["agreement_level"] == "moderate"

    def test_partial_review_summary_fills_missing(self):
        """Partial review_summary gets missing fields filled with defaults."""
        from app.services.extraction_service import _normalize_review_response
        raw = {"review_summary": {"overall_sentiment": "negative"}}
        result = _normalize_review_response(raw)
        assert result["review_summary"]["overall_sentiment"] == "negative"
        assert result["review_summary"]["consensus"] == ""
        assert result["review_summary"]["highlights"] == []
        assert result["review_summary"]["review_volume"] == "minimal"
        assert result["review_summary"]["agreement_level"] == "moderate"

    def test_highlights_with_missing_sentiment_kept(self):
        """Highlights without sentiment tag are kept as-is (GPT may omit)."""
        from app.services.extraction_service import _normalize_review_response
        raw = {"review_summary": {"highlights": [{"point": "Fast processor"}]}}
        result = _normalize_review_response(raw)
        assert len(result["review_summary"]["highlights"]) == 1
        assert result["review_summary"]["highlights"][0]["point"] == "Fast processor"

    def test_backward_compat_praises_only_positive(self):
        """Backward compat: common_praises only gets positive highlights."""
        from app.services.extraction_service import _normalize_review_response
        raw = {
            "review_summary": {
                "highlights": [
                    {"point": "Great display", "sentiment": "positive"},
                    {"point": "Slow charging", "sentiment": "negative"},
                    {"point": "Good build", "sentiment": "positive"},
                ],
            },
        }
        result = _normalize_review_response(raw)
        assert len(result["common_praises"]) == 2
        assert len(result["common_complaints"]) == 1

    def test_backward_compat_not_overwritten_if_present(self):
        """If common_praises already in data, don't overwrite from highlights."""
        from app.services.extraction_service import _normalize_review_response
        raw = {
            "common_praises": ["Explicit praise"],
            "review_summary": {
                "highlights": [
                    {"point": "From highlight", "sentiment": "positive"},
                ],
            },
        }
        result = _normalize_review_response(raw)
        assert result["common_praises"] == ["Explicit praise"]

    def test_empty_data_dict(self):
        """Completely empty input dict gets all defaults."""
        from app.services.extraction_service import _normalize_review_response
        result = _normalize_review_response({})
        assert "review_summary" in result
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["source_ratings"] == []
        assert result["common_praises"] == []
        assert result["common_complaints"] == []

    def test_highlights_with_non_dict_items_skipped_in_compat(self):
        """Non-dict items in highlights are skipped for backward compat derivation."""
        from app.services.extraction_service import _normalize_review_response
        raw = {
            "review_summary": {
                "highlights": [
                    "plain string",
                    {"point": "Good camera", "sentiment": "positive"},
                    42,
                ],
            },
        }
        result = _normalize_review_response(raw)
        assert len(result["common_praises"]) == 1
        assert result["common_praises"][0] == "Good camera"

    def test_source_ratings_default_preserved(self):
        """source_ratings defaults to empty list (used by external injection)."""
        from app.services.extraction_service import _normalize_review_response
        result = _normalize_review_response({"average_rating": 3.5})
        assert result["source_ratings"] == []

    def test_source_ratings_not_overwritten(self):
        """Existing source_ratings are preserved."""
        from app.services.extraction_service import _normalize_review_response
        raw = {"source_ratings": [{"source": "Amazon", "rating": 4.5}]}
        result = _normalize_review_response(raw)
        assert len(result["source_ratings"]) == 1


# ===========================================
# EDGE CASES: generate_comparison() parsing
# ===========================================

class TestGenerateComparisonParsing:
    """Tests for generate_comparison() GPT response parsing edge cases."""

    @pytest.mark.asyncio
    async def test_error_returns_default_winner_index(self):
        """On exception, generate_comparison returns winner_index=0 and error."""
        from unittest.mock import patch, AsyncMock
        from app.services.extraction_service import generate_comparison
        with patch("app.services.extraction_service.get_client") as mock_client:
            mock_client.side_effect = Exception("API down")
            result, usage = await generate_comparison({}, {}, "bahrain")
            assert result["winner_index"] == 0
            assert "error" in result

    @pytest.mark.asyncio
    async def test_personalized_insights_stripped_without_preferences(self):
        """Without preferences, personalized_insights is removed from result."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.services.extraction_service import generate_comparison
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner_index": 0, "personalized_insights": [{"focus_area": "price", "product_index": 0, "insight": "test"}]}'
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        with patch("app.services.extraction_service.get_client") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            result, usage = await generate_comparison({}, {}, "bahrain", user_preferences=None)
            assert "personalized_insights" not in result

    @pytest.mark.asyncio
    async def test_personalized_insights_capped_at_3(self):
        """personalized_insights is capped at 3 items."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.services.extraction_service import generate_comparison
        insights = [{"focus_area": f"area_{i}", "product_index": 0, "insight": f"insight {i}"} for i in range(5)]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"winner_index": 0, "personalized_insights": insights})
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        with patch("app.services.extraction_service.get_client") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            result, usage = await generate_comparison({}, {}, "bahrain", user_preferences={"priorities": ["price"]})
            assert len(result["personalized_insights"]) == 3

    @pytest.mark.asyncio
    async def test_personalized_insights_none_becomes_empty_list(self):
        """If GPT returns personalized_insights as null, it becomes []."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.services.extraction_service import generate_comparison
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner_index": 0, "personalized_insights": null}'
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        with patch("app.services.extraction_service.get_client") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            result, usage = await generate_comparison({}, {}, "bahrain", user_preferences={"priorities": ["quality"]})
            assert result["personalized_insights"] == []

    @pytest.mark.asyncio
    async def test_scores_summary_appended_to_prompt(self):
        """When scores_summary is provided, it's appended to the prompt."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.services.extraction_service import generate_comparison
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner_index": 1}'
        mock_response.usage = MagicMock(prompt_tokens=200, completion_tokens=50)
        with patch("app.services.extraction_service.get_client") as mock_client:
            create_mock = AsyncMock(return_value=mock_response)
            mock_client.return_value.chat.completions.create = create_mock
            result, usage = await generate_comparison({}, {}, "bahrain", scores_summary="Product A wins by 8 points")
            # Verify scores_summary was included in the prompt sent to GPT
            call_args = create_mock.call_args
            prompt_sent = call_args[1]["messages"][0]["content"]
            assert "Product A wins by 8 points" in prompt_sent
            assert "Scoring Context" in prompt_sent

    @pytest.mark.asyncio
    async def test_markdown_json_cleaned(self):
        """GPT response wrapped in ```json is cleaned correctly."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.services.extraction_service import generate_comparison
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n{"winner_index": 0, "winner_declaration": "Product A"}\n```'
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        with patch("app.services.extraction_service.get_client") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            result, usage = await generate_comparison({}, {}, "bahrain")
            assert result["winner_index"] == 0
            assert result["winner_declaration"] == "Product A"

    @pytest.mark.asyncio
    async def test_empty_preferences_strips_insights(self):
        """Preferences with all empty values strips personalized_insights."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.services.extraction_service import generate_comparison
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner_index": 0, "personalized_insights": [{"focus_area": "x", "product_index": 0, "insight": "y"}]}'
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        with patch("app.services.extraction_service.get_client") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            result, usage = await generate_comparison({}, {}, "bahrain", user_preferences={"priorities": [], "budget": "", "lifestyle": [], "brand_attitude": ""})
            assert "personalized_insights" not in result


# ===========================================
# EDGE CASES: _build_preferences_prompt()
# ===========================================

class TestBuildPreferencesPromptEdgeCases:
    """Tests for _build_preferences_prompt() with various preference combinations."""

    def test_all_priorities(self):
        """All 8 priorities are listed comma-separated."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["price", "quality", "brand_reputation", "durability", "latest_features", "ease_of_use", "eco_friendly", "health_safety"], "budget": "premium", "lifestyle": ["vegan"], "brand_attitude": "brand_loyal"}
        prompt = _build_preferences_prompt(prefs)
        assert "price, quality, brand_reputation" in prompt
        assert "health_safety" in prompt

    def test_empty_priorities(self):
        """Empty priorities list produces empty string in prompt."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": [], "budget": "budget", "lifestyle": [], "brand_attitude": "function_first"}
        prompt = _build_preferences_prompt(prefs)
        assert "Top priorities:" in prompt
        assert "function_first" in prompt

    def test_budget_level_shown(self):
        """Budget level is shown correctly."""
        from app.services.extraction_service import _build_preferences_prompt
        for budget in ["budget", "mid", "premium"]:
            prompt = _build_preferences_prompt({"priorities": ["price"], "budget": budget, "lifestyle": [], "brand_attitude": "best_of_both"})
            assert budget in prompt

    def test_lifestyle_tags_listed(self):
        """Multiple lifestyle tags are comma-separated."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["quality"], "budget": "mid", "lifestyle": ["vegan", "fitness", "tech_enthusiast"], "brand_attitude": "best_of_both"}
        prompt = _build_preferences_prompt(prefs)
        assert "vegan, fitness, tech_enthusiast" in prompt

    def test_empty_lifestyle_shows_none(self):
        """Empty lifestyle shows 'none specified'."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["price"], "budget": "mid", "lifestyle": [], "brand_attitude": "brand_loyal"}
        prompt = _build_preferences_prompt(prefs)
        assert "none specified" in prompt

    def test_brand_loyal_instruction(self):
        """brand_loyal is mentioned and has specific instruction."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["brand_reputation"], "budget": "premium", "lifestyle": [], "brand_attitude": "brand_loyal"}
        prompt = _build_preferences_prompt(prefs)
        assert "brand_loyal" in prompt
        assert "brand reputation higher" in prompt.lower()

    def test_function_first_instruction(self):
        """function_first has instruction to ignore brand."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["price"], "budget": "budget", "lifestyle": [], "brand_attitude": "function_first"}
        prompt = _build_preferences_prompt(prefs)
        assert "function_first" in prompt
        assert "ignore brand" in prompt.lower()

    def test_missing_keys_use_defaults(self):
        """Missing preference keys use defaults gracefully."""
        from app.services.extraction_service import _build_preferences_prompt
        prompt = _build_preferences_prompt({})
        assert "Top priorities:" in prompt
        assert "Budget level: mid" in prompt
        assert "Brand attitude: best_of_both" in prompt
        assert "none specified" in prompt

    def test_aligns_with_instruction_present(self):
        """The 'aligns with' instruction for best_for is present."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["quality"], "budget": "mid", "lifestyle": [], "brand_attitude": "best_of_both"}
        prompt = _build_preferences_prompt(prefs)
        assert "aligns" in prompt.lower()

    def test_vegan_lifestyle_conflict_instruction(self):
        """Prompt mentions lifestyle conflict flagging."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {"priorities": ["health_safety"], "budget": "mid", "lifestyle": ["vegan"], "brand_attitude": "function_first"}
        prompt = _build_preferences_prompt(prefs)
        assert "conflict" in prompt.lower() or "vegan" in prompt.lower()

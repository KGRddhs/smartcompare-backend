"""Tests for AI Guidance System — personalized insights in verdict."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def sample_product_1():
    return {
        "brand": "Apple", "name": "iPhone 15",
        "specs": {"battery": "3349 mAh", "ram": "6 GB", "storage": "128 GB"},
        "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon"},
        "rating": 4.5, "review_count": 1200,
    }

@pytest.fixture
def sample_product_2():
    return {
        "brand": "Samsung", "name": "Galaxy S24",
        "specs": {"battery": "4000 mAh", "ram": "8 GB", "storage": "128 GB"},
        "price": {"amount": 259, "currency": "BHD", "retailer": "Jarir"},
        "rating": 4.3, "review_count": 800,
    }

@pytest.fixture
def sample_preferences():
    return {"priorities": ["price", "quality"], "budget": "budget", "lifestyle": ["fitness"], "brand_attitude": "function_first"}


class TestComparisonPromptHasInsightsSchema:
    def test_prompt_contains_personalized_insights_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "personalized_insights" in COMPARISON_PROMPT

    def test_prompt_contains_focus_area_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "focus_area" in COMPARISON_PROMPT

    def test_prompt_contains_product_index_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "product_index" in COMPARISON_PROMPT

    def test_prompt_contains_insight_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert '"insight"' in COMPARISON_PROMPT


class TestGenerateComparisonInsightsValidation:
    def _make_mock_response(self, extra_fields=None):
        base = {
            "winner_index": 0, "winner_reason": "Better camera",
            "product_0_pros": ["pro1"], "product_0_cons": ["con1"],
            "product_1_pros": ["pro1"], "product_1_cons": ["con1"],
            "price_comparison": {"cheaper_index": 1, "price_difference": "40 BHD", "better_value_index": 1},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 8.0],
            "best_for": {"budget": 1, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "Get Galaxy S24 for value.", "key_differences": ["diff1"],
        }
        if extra_fields:
            base.update(extra_fields)
        return base

    def _mock_client(self, response_dict):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(response_dict)))])
        )
        return mock_client

    @pytest.mark.asyncio
    async def test_insights_stripped_when_no_preferences(self, sample_product_1, sample_product_2):
        resp = self._make_mock_response({"personalized_insights": [{"focus_area": "price", "product_index": 1, "insight": "Cheaper"}]})
        with patch("app.services.extraction_service.get_client", return_value=self._mock_client(resp)):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(sample_product_1, sample_product_2, "bahrain", user_preferences=None)
            assert "personalized_insights" not in result

    @pytest.mark.asyncio
    async def test_insights_stripped_with_empty_preferences(self, sample_product_1, sample_product_2):
        resp = self._make_mock_response({"personalized_insights": [{"focus_area": "price", "product_index": 0, "insight": "Hallucinated"}]})
        with patch("app.services.extraction_service.get_client", return_value=self._mock_client(resp)):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(sample_product_1, sample_product_2, "bahrain", user_preferences={})
            assert "personalized_insights" not in result

    @pytest.mark.asyncio
    async def test_insights_truncated_to_3(self, sample_product_1, sample_product_2, sample_preferences):
        insights = [{"focus_area": f"area{i}", "product_index": 0, "insight": f"Insight {i}"} for i in range(5)]
        resp = self._make_mock_response({"personalized_insights": insights})
        with patch("app.services.extraction_service.get_client", return_value=self._mock_client(resp)):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(sample_product_1, sample_product_2, "bahrain", user_preferences=sample_preferences)
            assert len(result.get("personalized_insights", [])) <= 3

    @pytest.mark.asyncio
    async def test_insights_kept_when_preferences_present(self, sample_product_1, sample_product_2, sample_preferences):
        insights = [{"focus_area": "price", "product_index": 1, "insight": "15% cheaper"}, {"focus_area": "battery", "product_index": 1, "insight": "4000 vs 3349 mAh"}]
        resp = self._make_mock_response({"personalized_insights": insights})
        with patch("app.services.extraction_service.get_client", return_value=self._mock_client(resp)):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(sample_product_1, sample_product_2, "bahrain", user_preferences=sample_preferences)
            assert "personalized_insights" in result
            assert len(result["personalized_insights"]) == 2

    @pytest.mark.asyncio
    async def test_insights_empty_array_when_gpt_returns_none(self, sample_product_1, sample_product_2, sample_preferences):
        resp = self._make_mock_response()  # No insights field
        with patch("app.services.extraction_service.get_client", return_value=self._mock_client(resp)):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(sample_product_1, sample_product_2, "bahrain", user_preferences=sample_preferences)
            assert result.get("personalized_insights") == []

    @pytest.mark.asyncio
    async def test_insights_malformed_returns_empty_array(self, sample_product_1, sample_product_2, sample_preferences):
        resp = self._make_mock_response({"personalized_insights": "not a list"})
        with patch("app.services.extraction_service.get_client", return_value=self._mock_client(resp)):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(sample_product_1, sample_product_2, "bahrain", user_preferences=sample_preferences)
            assert result.get("personalized_insights") == []

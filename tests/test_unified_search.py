"""Tests for unified search call merging optimization.

Verifies that one Serper call is shared by specs + reviews, saving $0.001/product.
Run: python -m pytest tests/test_unified_search.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, call
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# B3 (test-infra hygiene): these "mocked" tests patch search_web + extract_* +
# the Redis cache, but call _get_specs / _get_reviews with the default
# nocache=False, so they still reach the un-mocked L2 DB cache
# (product_data_service.get_cached_specs / get_cached_reviews → live Supabase).
# That's a REAL network call, so they belong behind the live_unit mark like the
# cost-tracking class below — keeps them out of the free-unit filter where the
# Supabase round-trip flakes / errors under sandbox network restrictions.
# live_prod (#49): as the note above says, these reach the un-mocked L2 DB
# (product_data_service.get_cached_specs/save_specs -> the PRODUCTION Supabase), so they
# both read and write production rows. Excluded from the scheduled live suite.
@pytest.mark.live_unit
@pytest.mark.live_prod
class TestUnifiedSearchSharing:
    def test_specs_skips_own_search_when_results_provided(self, service):
        """_get_specs() should NOT call search_web when search_results is provided."""
        with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search, \
             patch("app.services.structured_comparison_service.extract_specs", new_callable=AsyncMock) as mock_extract, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None), \
             patch("app.services.structured_comparison_service.set_cached"):
            mock_extract.return_value = ({"display": "6.1 inch", "processor": "A16"}, {"prompt_tokens": 0, "completion_tokens": 0})
            pre_fetched = {"organic": [{"title": "Test", "snippet": "specs"}]}

            run_async(service._get_specs("Apple", "iPhone 16", None, "electronics", "Apple iPhone 16",
                                          search_results=pre_fetched))

            # search_web should NOT have been called (pre-fetched results provided)
            mock_search.assert_not_called()

    def test_specs_calls_own_search_when_no_results(self, service):
        """_get_specs() should call search_web when search_results is None."""
        with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search, \
             patch("app.services.structured_comparison_service.extract_specs", new_callable=AsyncMock) as mock_extract, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None), \
             patch("app.services.structured_comparison_service.set_cached"):
            mock_search.return_value = {"organic": []}
            mock_extract.return_value = ({"display": "6.1 inch"}, {"prompt_tokens": 0, "completion_tokens": 0})

            run_async(service._get_specs("Apple", "iPhone 16", None, "electronics", "Apple iPhone 16"))

            mock_search.assert_called_once()

    def test_reviews_skips_own_search_when_results_provided(self, service):
        """_get_reviews() should NOT call search_web when search_results is provided."""
        with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search, \
             patch("app.services.structured_comparison_service.extract_reviews", new_callable=AsyncMock) as mock_extract, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None), \
             patch("app.services.structured_comparison_service.set_cached"):
            mock_extract.return_value = ({"average_rating": 4.5, "common_praises": [], "common_complaints": []}, {"prompt_tokens": 0, "completion_tokens": 0})
            pre_fetched = {"organic": [{"title": "Review", "snippet": "good product"}]}

            run_async(service._get_reviews("Apple", "iPhone 16", None, "Apple iPhone 16",
                                            search_results=pre_fetched))

            mock_search.assert_not_called()


# --- Live cost tracking test ---

# live_prod (#49): GETs the PRODUCTION deployment and bills the production vendor budget;
# the prod server writes the resolved price to the production cache + L2 DB.
@pytest.mark.live_unit
@pytest.mark.live_prod
class TestCostTrackingLive:
    def test_comparison_within_budget(self, service):
        """A full comparison should cost <= $0.020 and use <= 20 API calls."""
        import httpx
        BASE_URL = "https://web-production-58776.up.railway.app"
        response = httpx.get(
            f"{BASE_URL}/api/v1/text/compare",
            params={"q": "iPhone 15 vs Samsung Galaxy S24", "nocache": "true"},
            timeout=150.0,
        )
        assert response.status_code == 200
        data = response.json()
        metadata = data.get("metadata", {})
        total_cost = metadata.get("total_cost", 0)
        api_calls = metadata.get("api_calls", 0)

        assert total_cost <= 0.020, f"Cost ${total_cost:.4f} exceeds $0.020 budget"
        assert api_calls <= 20, f"{api_calls} API calls exceeds 20-call budget"

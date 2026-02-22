"""Tests for singleton service state management.

Verifies state is properly reset between requests to prevent cross-request data leaks.
Run: python -m pytest tests/test_singleton_state.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    get_comparison_service,
)


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestSingletonPattern:
    def test_get_comparison_service_returns_same_instance(self):
        """get_comparison_service() should return the same instance."""
        import app.services.structured_comparison_service as mod
        mod._service_instance = None  # Reset for test
        s1 = get_comparison_service()
        s2 = get_comparison_service()
        assert s1 is s2
        mod._service_instance = None  # Cleanup


class TestStateReset:
    def test_shopping_cache_cleared_on_new_request(self, service):
        """_shopping_items_cache must be cleared at start of compare_from_text."""
        # Simulate leftover state from a previous request
        service._shopping_items_cache = {"old_product": [{"title": "stale data"}]}
        service.total_cost = 0.05
        service.api_calls = 10

        # Mock everything so compare_from_text runs but doesn't call real APIs
        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock) as mock_parse, \
             patch.object(service, "_fetch_product_data", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock) as mock_compare:
            mock_parse.return_value = {
                "products": [
                    {"brand": "A", "name": "Product1", "category": "other", "search_query": "A Product1"},
                    {"brand": "B", "name": "Product2", "category": "other", "search_query": "B Product2"},
                ]
            }
            mock_fetch.return_value = {"brand": "Test", "name": "Product", "specs": {}, "price": {"amount": 100, "currency": "BHD"}, "rating": 4.5}
            mock_compare.return_value = {"winner_index": 0, "recommendation": "Test"}

            run_async(service.compare_from_text("A Product1 vs B Product2"))

        # State should have been reset at start of compare_from_text
        # (total_cost/api_calls are modified during the call, but _shopping_items_cache
        # should NOT contain "old_product" anymore)
        assert "old_product" not in service._shopping_items_cache

    def test_cost_and_calls_reset_per_request(self, service):
        """total_cost and api_calls should be reset to 0 at start of each request."""
        service.total_cost = 0.05
        service.api_calls = 10

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock) as mock_parse:
            # Make it fail early — we just need to verify the reset happened
            mock_parse.side_effect = Exception("intentional test error")

            result = run_async(service.compare_from_text("test query"))

        # Even though the request failed, cost/calls should have been reset before the error
        assert service.total_cost == 0.0
        assert service.api_calls == 0

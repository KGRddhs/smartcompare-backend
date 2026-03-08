"""
Tests for SSE streaming comparison endpoint and async generator.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_product_data():
    """Two product dicts as returned by _fetch_product_data."""
    return [
        {
            "brand": "Apple",
            "name": "iPhone 15",
            "full_name": "Apple iPhone 15",
            "variant": "128GB",
            "category": "electronics",
            "query": "Apple iPhone 15",
            "specs": {"ram": "6GB", "storage": "128GB"},
            "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon", "url": None, "estimated": False},
            "best_price": 299,
            "currency": "BHD",
            "retailer": "Amazon",
            "reviews": {"average_rating": 4.5, "total_reviews": 1200, "summary": "Great phone"},
            "rating": 4.5,
            "review_count": 1200,
            "rating_verified": True,
            "rating_source": {"name": "Amazon", "url": None},
            "fact_check": {"overall_confidence": "high"},
            "data_freshness": "fresh",
        },
        {
            "brand": "Samsung",
            "name": "Galaxy S24",
            "full_name": "Samsung Galaxy S24",
            "variant": "128GB",
            "category": "electronics",
            "query": "Samsung Galaxy S24",
            "specs": {"ram": "8GB", "storage": "128GB"},
            "price": {"amount": 279, "currency": "BHD", "retailer": "Noon", "url": None, "estimated": False},
            "best_price": 279,
            "currency": "BHD",
            "retailer": "Noon",
            "reviews": {"average_rating": 4.3, "total_reviews": 800, "summary": "Good Android phone"},
            "rating": 4.3,
            "review_count": 800,
            "rating_verified": True,
            "rating_source": {"name": "Noon", "url": None},
            "fact_check": {"overall_confidence": "medium"},
            "data_freshness": "fresh",
        },
    ]


@pytest.fixture
def mock_comparison():
    """Comparison result from generate_comparison."""
    return {
        "winner_index": 0,
        "recommendation": "iPhone 15 is better overall",
        "key_differences": ["Better camera", "Higher price"],
        "product_0_pros": ["Great camera", "Long battery"],
        "product_0_cons": ["Higher price"],
        "product_1_pros": ["Better value", "More RAM"],
        "product_1_cons": ["Shorter updates"],
    }


@pytest.fixture
def mock_scoring_result():
    """Scoring result from scoring_service."""
    return {
        "scores": {
            "product_0": {"overall": 78, "breakdown": {"price_score": 70, "spec_score": 80}},
            "product_1": {"overall": 72, "breakdown": {"price_score": 85, "spec_score": 65}},
        },
        "winner_index": 0,
        "win_margin": 6,
        "scoring_method": "default",
    }


# ============================================
# Test SSE event format
# ============================================

class TestSSEEventFormat:
    """Test that SSE events have correct format."""

    def test_event_has_correct_format(self):
        """Each SSE event must have 'event: <type>\\ndata: <json>\\n\\n' format."""
        event_type = "status"
        data = {"message": "Parsing query..."}
        sse_line = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        assert sse_line.startswith("event: status\n")
        assert "data: " in sse_line
        assert sse_line.endswith("\n\n")

    def test_data_is_valid_json(self):
        """The data field must be valid JSON."""
        data = {"message": "test", "nested": {"key": [1, 2, 3]}}
        sse_line = f"event: test\ndata: {json.dumps(data)}\n\n"
        data_line = sse_line.split("\n")[1]
        json_str = data_line[len("data: "):]
        parsed = json.loads(json_str)
        assert parsed["message"] == "test"
        assert parsed["nested"]["key"] == [1, 2, 3]

    def test_double_newline_terminator(self):
        """SSE events must end with double newline."""
        event = f"event: status\ndata: {json.dumps({})}\n\n"
        assert event[-2:] == "\n\n"


# ============================================
# Test streaming generator
# ============================================

class TestStreamingGenerator:
    """Test the compare_from_text_streaming async generator."""

    @pytest.mark.asyncio
    async def test_yields_status_first(self, mock_product_data, mock_comparison, mock_scoring_result):
        """First yield should be a status event."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = mock_comparison
            scoring_svc = MagicMock()
            scoring_svc.compute_scores.return_value = mock_scoring_result
            scoring_svc.build_scores_summary.return_value = "Product 1 scores 78, Product 2 scores 72"
            mock_scoring.return_value = scoring_svc

            events = []
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                events.append((event_type, data))

            assert events[0][0] == "status"
            assert "Parsing" in events[0][1]["message"]

    @pytest.mark.asyncio
    async def test_event_sequence_order(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Events must follow the defined sequence."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = mock_comparison
            scoring_svc = MagicMock()
            scoring_svc.compute_scores.return_value = mock_scoring_result
            scoring_svc.build_scores_summary.return_value = "summary"
            mock_scoring.return_value = scoring_svc

            event_types = []
            async for event_type, _ in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                event_types.append(event_type)

            # Expected order: status, status, specs, prices, status, reviews, scores, status, verdict, complete
            assert event_types[0] == "status"   # Parsing query...
            assert event_types[1] == "status"   # Fetching specs...
            assert event_types[2] == "specs"
            assert event_types[3] == "prices"
            assert event_types[4] == "status"   # Analyzing reviews...
            assert event_types[5] == "reviews"
            assert event_types[6] == "scores"
            assert event_types[7] == "status"   # Generating verdict...
            assert event_types[8] == "verdict"
            assert event_types[9] == "complete"

    @pytest.mark.asyncio
    async def test_complete_event_has_full_response(self, mock_product_data, mock_comparison, mock_scoring_result):
        """The 'complete' event should contain the full response with success=True."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = mock_comparison.copy()
            scoring_svc = MagicMock()
            scoring_svc.compute_scores.return_value = mock_scoring_result
            scoring_svc.build_scores_summary.return_value = "summary"
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "complete":
                    complete_data = data

            assert complete_data is not None
            assert complete_data["success"] is True
            assert "products" in complete_data
            assert "comparison" in complete_data
            assert "scoring" in complete_data
            assert "metadata" in complete_data

    @pytest.mark.asyncio
    async def test_error_on_bad_query(self):
        """If query can't be parsed, should yield an error event."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {"products": []}

            events = []
            async for event_type, data in service.compare_from_text_streaming("just one product"):
                events.append((event_type, data))

            assert any(e[0] == "error" for e in events)
            error_event = next(e for e in events if e[0] == "error")
            assert error_event[1]["success"] is False

    @pytest.mark.asyncio
    async def test_error_on_exception(self, mock_product_data):
        """If an exception occurs mid-stream, should yield an error event."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch:

            mock_parse.return_value = {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
            }
            mock_fetch.side_effect = RuntimeError("GPT API failed")

            events = []
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                events.append((event_type, data))

            event_types = [e[0] for e in events]
            assert "error" in event_types

    @pytest.mark.asyncio
    async def test_specs_event_has_both_products(self, mock_product_data, mock_comparison, mock_scoring_result):
        """The specs event should contain data for both products."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = mock_comparison.copy()
            scoring_svc = MagicMock()
            scoring_svc.compute_scores.return_value = mock_scoring_result
            scoring_svc.build_scores_summary.return_value = "summary"
            mock_scoring.return_value = scoring_svc

            specs_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "specs":
                    specs_data = data

            assert specs_data is not None
            assert "product_0" in specs_data
            assert "product_1" in specs_data
            assert specs_data["product_0"]["specs"]["ram"] == "6GB"
            assert specs_data["product_1"]["specs"]["ram"] == "8GB"


# ============================================
# Test SSE endpoint via TestClient
# ============================================

class TestSSEEndpoint:
    """Test the /api/v1/text/compare/stream endpoint."""

    def _get_client(self):
        """Get a test client with mocked auth."""
        from app.main import app
        return TestClient(app)

    def test_stream_returns_event_stream_content_type(self):
        """Response should have text/event-stream content type."""
        client = self._get_client()
        with patch('app.api.text_routes.get_comparison_service') as mock_svc:
            service = MagicMock()

            async def fake_stream(**kwargs):
                yield ("status", {"message": "Parsing query..."})
                yield ("complete", {"success": True, "products": [], "metadata": {}})

            service.compare_from_text_streaming = fake_stream
            mock_svc.return_value = service

            with patch('app.api.text_routes.get_optional_user', return_value=None):
                response = client.get("/api/v1/text/compare/stream?q=iPhone+15+vs+Galaxy+S24")

            assert response.headers["content-type"].startswith("text/event-stream")

    def test_stream_returns_sse_headers(self):
        """Response should include Cache-Control and X-Accel-Buffering headers."""
        client = self._get_client()
        with patch('app.api.text_routes.get_comparison_service') as mock_svc:
            service = MagicMock()

            async def fake_stream(**kwargs):
                yield ("status", {"message": "test"})
                yield ("complete", {"success": True, "products": [], "metadata": {}})

            service.compare_from_text_streaming = fake_stream
            mock_svc.return_value = service

            with patch('app.api.text_routes.get_optional_user', return_value=None):
                response = client.get("/api/v1/text/compare/stream?q=test+vs+test2")

            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("x-accel-buffering") == "no"

    def test_stream_events_parseable(self):
        """Streamed events should be parseable as SSE."""
        client = self._get_client()
        with patch('app.api.text_routes.get_comparison_service') as mock_svc:
            service = MagicMock()

            async def fake_stream(**kwargs):
                yield ("status", {"message": "Parsing query..."})
                yield ("specs", {"product_0": {"specs": {"ram": "6GB"}}})
                yield ("complete", {"success": True, "products": [], "metadata": {}})

            service.compare_from_text_streaming = fake_stream
            mock_svc.return_value = service

            with patch('app.api.text_routes.get_optional_user', return_value=None):
                response = client.get("/api/v1/text/compare/stream?q=test+vs+test2")

            # Parse SSE events from response text
            text = response.text
            events = []
            for block in text.strip().split("\n\n"):
                lines = block.strip().split("\n")
                if len(lines) >= 2:
                    event_type = lines[0].replace("event: ", "")
                    data = json.loads(lines[1].replace("data: ", ""))
                    events.append((event_type, data))

            assert len(events) >= 2
            assert events[0][0] == "status"
            assert events[1][0] == "specs"

    def test_non_streaming_endpoint_still_works(self):
        """Existing GET /compare should still return JSON, not SSE."""
        client = self._get_client()
        mock_result = {"success": True, "products": [], "metadata": {"total_cost": 0}}

        with patch('app.api.text_routes.get_comparison_service') as mock_svc, \
             patch('app.api.text_routes.get_optional_user', return_value=None), \
             patch('app.middleware.rate_limiter.limiter.enabled', False):
            service = MagicMock()
            service.compare_from_text = AsyncMock(return_value=mock_result)
            mock_svc.return_value = service

            response = client.get("/api/v1/text/compare?q=test+vs+test2")

            assert response.headers["content-type"].startswith("application/json")
            assert response.json()["success"] is True

    def test_stream_requires_query_param(self):
        """Stream endpoint should require 'q' parameter."""
        client = self._get_client()
        response = client.get("/api/v1/text/compare/stream")
        assert response.status_code == 422  # Validation error


# ============================================
# Test edge cases
# ============================================

class TestStreamingEdgeCases:
    """Test edge cases and error handling in streaming."""

    @pytest.mark.asyncio
    async def test_state_reset_per_request(self):
        """Streaming should reset per-request state like non-streaming."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        service.total_cost = 999.0
        service.api_calls = 999
        service._shopping_items_cache = {"stale": "data"}

        with patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = {"products": []}

            async for _ in service.compare_from_text_streaming("bad query"):
                pass

            # State should have been reset at start
            assert service.total_cost < 999.0
            assert service.api_calls < 999
            assert "stale" not in service._shopping_items_cache

    @pytest.mark.asyncio
    async def test_category_switching_in_streaming(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Category switching should work in streaming mode."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = mock_comparison.copy()
            scoring_svc = MagicMock()
            scoring_svc.compute_scores.return_value = mock_scoring_result
            scoring_svc.build_scores_summary.return_value = "summary"
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming(
                "iPhone 15 vs Galaxy S24", selected_category="grocery"
            ):
                if event_type == "complete":
                    complete_data = data

            assert complete_data["category_switched"] is True
            assert complete_data["original_category"] == "grocery"
            assert complete_data["category_used"] == "electronics"

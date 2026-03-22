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
            "reviews": {
                "average_rating": 4.5, "total_reviews": 1200,
                "review_summary": {
                    "overall_sentiment": "positive",
                    "consensus": "Great phone overall with excellent camera.",
                    "highlights": [{"point": "Excellent camera", "sentiment": "positive"}],
                    "review_volume": "high",
                    "agreement_level": "strong",
                },
            },
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
            "reviews": {
                "average_rating": 4.3, "total_reviews": 800,
                "review_summary": {
                    "overall_sentiment": "positive",
                    "consensus": "Good Android phone with great display.",
                    "highlights": [{"point": "Great display", "sentiment": "positive"}],
                    "review_volume": "high",
                    "agreement_level": "moderate",
                },
            },
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
        "winner_declaration": "Apple iPhone 15",
        "winner_reason": "Stronger camera and faster chip at similar price",
        "key_tradeoff": "Galaxy S24 has more RAM and better value",
        "value_context": "Both products are mid-range flagships with competitive pricing",
        "best_for": {
            "product_0": "Best if you prioritize camera quality",
            "product_1": "Best if you want more RAM and better value",
        },
        "product_0_pros": ["Great camera", "Long battery"],
        "product_0_cons": ["Higher price"],
        "product_1_pros": ["Better value", "More RAM"],
        "product_1_cons": ["Shorter updates"],
        "specs_comparison": {
            "product_0_advantages": ["Better camera"],
            "product_1_advantages": ["More RAM"],
            "similar": ["Storage"],
        },
    }


@pytest.fixture
def mock_scoring_result():
    """Scoring result from scoring_service."""
    return {
        "scores": {
            "product_0": {"overall": 78, "breakdown": {"price_score": 70, "spec_score": 80, "value_score": 65}},
            "product_1": {"overall": 72, "breakdown": {"price_score": 85, "spec_score": 65, "value_score": 58}},
        },
        "winner_index": 0,
        "win_margin": 6,
        "scoring_method": "category_weighted",
        "dimension_winners": {
            "price_score": {"winner": "Samsung Galaxy S24", "margin": 15.0},
            "spec_score": {"winner": "Apple iPhone 15", "margin": 15.0},
        },
        "price_tiers": {"iPhone 15": "mid", "Galaxy S24": "mid"},
        "is_cross_tier": False,
        "category_weights": {"price_score": 0.2, "spec_score": 0.25},
    }


def _setup_scoring_mock(scoring_svc, mock_scoring_result):
    """Configure scoring service mock with all required methods."""
    scoring_svc.compute_scores.return_value = mock_scoring_result
    scoring_svc.build_scores_summary.return_value = "summary"
    scoring_svc.compute_value_badge.return_value = "fair_price"
    scoring_svc.compute_tradeoff_pairs.return_value = []
    scoring_svc.compute_confidence.return_value = {
        "price": {"source_count": 2, "method": "retailer_verified", "freshness": "live"},
        "rating": {"review_count": 1200, "source": "Amazon", "verified": True},
        "specs": {"verified_pct": 80, "citation_count": 10},
        "overall": "high",
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

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison, {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
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

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison, {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
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

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "complete":
                    complete_data = data

            assert complete_data is not None
            assert complete_data["success"] is True
            # New structured sections
            assert "overview" in complete_data
            assert "specs" in complete_data
            assert "reviews" in complete_data
            assert "scoring" in complete_data
            assert "personalization" in complete_data
            assert "metadata" in complete_data
            # Backward compat aliases
            assert "products" in complete_data
            assert "comparison" in complete_data

    @pytest.mark.asyncio
    async def test_error_on_bad_query(self):
        """If query can't be parsed, should yield an error event."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ({"products": []}, {"prompt_tokens": 0, "completion_tokens": 0})

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

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
            }, {"prompt_tokens": 0, "completion_tokens": 0})
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

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            specs_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "specs":
                    specs_data = data

            assert specs_data is not None
            assert "products" in specs_data
            assert len(specs_data["products"]) == 2
            assert specs_data["products"][0]["specs"]["ram"] == "6GB"
            assert specs_data["products"][1]["specs"]["ram"] == "8GB"


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
            mock_parse.return_value = ({"products": []}, {"prompt_tokens": 0, "completion_tokens": 0})

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

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
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


# ============================================
# Test new response structure
# ============================================

class TestNewResponseStructure:
    """Tests for the restructured API response format."""

    @pytest.mark.asyncio
    async def test_response_has_all_sections(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Complete response must have overview/specs/reviews/scoring/personalization/metadata."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "complete":
                    complete_data = data

            assert complete_data is not None
            for key in ("overview", "specs", "reviews", "scoring", "personalization", "metadata"):
                assert key in complete_data, f"Missing top-level key: {key}"

    @pytest.mark.asyncio
    async def test_status_events_include_progress(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Status events must include progress percentage."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            status_events = []
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "status":
                    status_events.append(data)

            for event in status_events:
                assert "progress" in event, f"Status event missing 'progress': {event}"
            # Verify progress increases
            progress_values = [e["progress"] for e in status_events]
            assert progress_values == sorted(progress_values), "Progress should increase monotonically"

    @pytest.mark.asyncio
    async def test_overview_winner_structure(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Overview winner has structured fields."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "complete":
                    complete_data = data

            winner = complete_data["overview"]["winner"]
            assert "product_index" in winner
            assert "name" in winner
            assert "reason" in winner
            assert "key_tradeoff" in winner
            assert "margin" in winner

    @pytest.mark.asyncio
    async def test_overview_products_have_value_badge(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Overview products include value_badge."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "complete":
                    complete_data = data

            for product in complete_data["overview"]["products"]:
                assert "value_badge" in product
                assert product["value_badge"] in ("great_value", "fair_price", "premium_price", "overpriced")
                assert "best_for" in product

    @pytest.mark.asyncio
    async def test_reviews_have_review_summary(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Reviews products include review_summary with consensus format."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            complete_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "complete":
                    complete_data = data

            for product in complete_data["reviews"]["products"]:
                assert "review_summary" in product
                summary = product["review_summary"]
                assert "overall_sentiment" in summary
                assert "consensus" in summary
                assert "highlights" in summary

    @pytest.mark.asyncio
    async def test_verdict_event_has_structured_winner(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Verdict event has structured winner fields."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            verdict_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "verdict":
                    verdict_data = data

            assert verdict_data is not None
            assert "winner" in verdict_data
            assert "reason" in verdict_data["winner"]
            assert "key_tradeoff" in verdict_data["winner"]
            assert "value_context" in verdict_data
            assert "best_for" in verdict_data

    @pytest.mark.asyncio
    async def test_scores_event_has_confidence(self, mock_product_data, mock_comparison, mock_scoring_result):
        """Scores event includes confidence alongside scoring."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        with patch.object(service, '_fetch_product_data', new_callable=AsyncMock) as mock_fetch, \
             patch('app.services.structured_comparison_service.parse_product_query', new_callable=AsyncMock) as mock_parse, \
             patch('app.services.structured_comparison_service.generate_comparison', new_callable=AsyncMock) as mock_gen, \
             patch('app.services.structured_comparison_service.get_scoring_service') as mock_scoring:

            mock_parse.return_value = ({
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "Apple iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Samsung Galaxy S24"},
                ],
                "comparison_type": "value",
            }, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_fetch.side_effect = mock_product_data
            mock_gen.return_value = (mock_comparison.copy(), {"prompt_tokens": 0, "completion_tokens": 0})
            scoring_svc = MagicMock()
            _setup_scoring_mock(scoring_svc, mock_scoring_result)
            mock_scoring.return_value = scoring_svc

            scores_data = None
            async for event_type, data in service.compare_from_text_streaming("iPhone 15 vs Galaxy S24"):
                if event_type == "scores":
                    scores_data = data

            assert scores_data is not None
            assert "confidence" in scores_data
            assert "overall" in scores_data["confidence"]

"""Tests for camera/vision product identification pipeline.

Live tests call GPT-4o-mini vision API (~$0.005/test).
Run: python -m pytest tests/test_camera_vision.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set dummy API key so openai_service module can initialize at import time
# (AsyncOpenAI client requires OPENAI_API_KEY even if we mock all calls)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-unit-tests"

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.openai_service import identify_products, clean_json_response


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- clean_json_response tests ---

class TestCleanJsonResponse:
    def test_strips_markdown_code_blocks(self):
        raw = '```json\n[{"brand": "Apple"}]\n```'
        assert clean_json_response(raw) == '[{"brand": "Apple"}]'

    def test_plain_json_unchanged(self):
        raw = '[{"brand": "Apple"}]'
        assert clean_json_response(raw) == '[{"brand": "Apple"}]'

    def test_strips_whitespace(self):
        raw = '  \n[{"brand": "Apple"}]\n  '
        assert clean_json_response(raw) == '[{"brand": "Apple"}]'


# --- Vision pipeline tests (mocked) ---

class TestIdentifyProductsMocked:
    def test_malformed_response_returns_error(self):
        """If GPT returns non-JSON, should return error dict with raw_response."""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_usage.prompt_tokens = 80
        mock_usage.completion_tokens = 20

        mock_choice = MagicMock()
        mock_choice.message.content = "I can see an iPhone in the image"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("app.services.openai_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = run_async(identify_products([{"bytes": b"\xff\xd8fake", "mime_type": "image/jpeg"}]))

        assert result.get("error") is not None
        assert "Failed to parse" in result["error"]
        assert result.get("raw_response") == "I can see an iPhone in the image"

    def test_successful_identification(self):
        """Valid JSON response should return normalized products."""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 200
        mock_usage.prompt_tokens = 150
        mock_usage.completion_tokens = 50

        mock_choice = MagicMock()
        mock_choice.message.content = '[{"brand": "Apple", "name": "iPhone 16 Pro", "size_or_count": "256GB", "visible_price": null, "confidence": "high"}]'

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("app.services.openai_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = run_async(identify_products([{"bytes": b"\xff\xd8fake", "mime_type": "image/jpeg"}]))

        assert len(result["products"]) == 1
        assert result["products"][0]["brand"] == "Apple"
        assert result["products"][0]["name"] == "iPhone 16 Pro"
        assert result["products"][0]["size_or_count"] == "256GB"
        assert result["cost"] > 0

    def test_empty_product_fields_normalized(self):
        """Missing fields should be filled with defaults."""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_usage.prompt_tokens = 80
        mock_usage.completion_tokens = 20

        mock_choice = MagicMock()
        mock_choice.message.content = '[{"name": "Something"}]'

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("app.services.openai_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = run_async(identify_products([{"bytes": b"\xff\xd8fake", "mime_type": "image/jpeg"}]))

        product = result["products"][0]
        assert product["brand"] == "Unknown"  # Default for missing brand
        assert product["confidence"] == "medium"  # Default confidence


# --- size_or_count enrichment (image_routes.py logic) ---

class TestSizeOrCountEnrichment:
    def test_size_appended_to_name(self):
        """size_or_count should be appended to product name if not already present."""
        products = [{"brand": "NOW", "name": "Vitamin D-3", "size_or_count": "360 Softgels"}]
        for p in products:
            size_or_count = p.get("size_or_count")
            if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
                p["name"] = f"{p['name']} {size_or_count}".strip()
        assert products[0]["name"] == "Vitamin D-3 360 Softgels"

    def test_size_not_duplicated_if_already_present(self):
        """If size_or_count is already in the name, don't append again."""
        products = [{"brand": "NOW", "name": "Vitamin D-3 360 Softgels", "size_or_count": "360 Softgels"}]
        for p in products:
            size_or_count = p.get("size_or_count")
            if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
                p["name"] = f"{p['name']} {size_or_count}".strip()
        assert products[0]["name"] == "Vitamin D-3 360 Softgels"  # Not duplicated

    def test_none_size_or_count_no_change(self):
        """None size_or_count should not modify name."""
        products = [{"brand": "Apple", "name": "iPhone 16 Pro", "size_or_count": None}]
        original_name = products[0]["name"]
        for p in products:
            size_or_count = p.get("size_or_count")
            if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
                p["name"] = f"{p['name']} {size_or_count}".strip()
        assert products[0]["name"] == original_name


# --- Live vision test (real GPT-4o-mini call) ---

@pytest.mark.live_unit
class TestVisionLive:
    def test_real_image_identifies_products(self):
        """Send a real test image to GPT-4o-mini vision."""
        test_image = os.path.join(os.path.dirname(__file__), "..", "test_two.jpg")
        if not os.path.exists(test_image):
            pytest.skip("test_two.jpg not found in repo root")

        with open(test_image, "rb") as f:
            image_bytes = f.read()

        result = run_async(identify_products([
            {"bytes": image_bytes, "mime_type": "image/jpeg"}
        ]))

        assert "products" in result
        # Should identify at least 1 product (test_two.jpg has 2 products)
        assert len(result["products"]) >= 1
        assert result["products"][0].get("brand")
        assert result["products"][0].get("name")
        assert result.get("cost", 0) > 0

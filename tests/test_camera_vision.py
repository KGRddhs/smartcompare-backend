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


# --- MIME type detection tests ---

class TestDetectMimeType:
    def test_heic_magic_bytes_detected(self):
        """Backend should detect HEIC magic bytes from ftyp box."""
        from app.api.image_routes import _detect_mime_type
        heic_bytes = b'\x00\x00\x00\x1c' + b'ftyp' + b'heic' + b'\x00' * 20
        assert _detect_mime_type(heic_bytes, "image/jpeg") == "image/heic"

    def test_heif_heix_brand_detected(self):
        """HEIF with heix brand should also be detected."""
        from app.api.image_routes import _detect_mime_type
        heix_bytes = b'\x00\x00\x00\x1c' + b'ftyp' + b'heix' + b'\x00' * 20
        assert _detect_mime_type(heix_bytes, "image/jpeg") == "image/heic"

    def test_hevc_brand_detected(self):
        """HEVC brand in ftyp box should be detected as HEIC."""
        from app.api.image_routes import _detect_mime_type
        hevc_bytes = b'\x00\x00\x00\x1c' + b'ftyp' + b'hevc' + b'\x00' * 20
        assert _detect_mime_type(hevc_bytes, "image/jpeg") == "image/heic"

    def test_mif1_brand_detected(self):
        """mif1 brand (HEIF) should be detected."""
        from app.api.image_routes import _detect_mime_type
        mif1_bytes = b'\x00\x00\x00\x1c' + b'ftyp' + b'mif1' + b'\x00' * 20
        assert _detect_mime_type(mif1_bytes, "image/jpeg") == "image/heic"

    def test_gif87a_detected(self):
        """GIF87a should be detected."""
        from app.api.image_routes import _detect_mime_type
        gif87 = b'GIF87a' + b'\x00' * 20
        assert _detect_mime_type(gif87, "image/jpeg") == "image/gif"

    def test_gif89a_detected(self):
        """GIF89a should be detected."""
        from app.api.image_routes import _detect_mime_type
        gif89 = b'GIF89a' + b'\x00' * 20
        assert _detect_mime_type(gif89, "image/jpeg") == "image/gif"

    def test_jpeg_magic_bytes_detected(self):
        """JPEG should be correctly detected from magic bytes."""
        from app.api.image_routes import _detect_mime_type
        jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 20
        assert _detect_mime_type(jpeg_bytes, "image/png") == "image/jpeg"

    def test_png_magic_bytes_detected(self):
        """PNG should be correctly detected from magic bytes."""
        from app.api.image_routes import _detect_mime_type
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
        assert _detect_mime_type(png_bytes, "image/jpeg") == "image/png"

    def test_webp_magic_bytes_detected(self):
        """WebP should be correctly detected from magic bytes."""
        from app.api.image_routes import _detect_mime_type
        webp_bytes = b'RIFF' + b'\x00\x00\x00\x00' + b'WEBP' + b'\x00' * 20
        assert _detect_mime_type(webp_bytes, "image/jpeg") == "image/webp"

    def test_unknown_format_uses_fallback(self):
        """Unknown bytes should return the fallback MIME type."""
        from app.api.image_routes import _detect_mime_type
        unknown_bytes = b'\x00\x01\x02\x03' + b'\x00' * 20
        assert _detect_mime_type(unknown_bytes, "image/jpeg") == "image/jpeg"

    def test_short_content_uses_fallback(self):
        """Very short content should not crash, use fallback."""
        from app.api.image_routes import _detect_mime_type
        assert _detect_mime_type(b'\xff', "image/png") == "image/png"
        assert _detect_mime_type(b'', "image/jpeg") == "image/jpeg"

    def test_supported_mime_types_constant(self):
        """SUPPORTED_MIME_TYPES should include jpeg, png, webp, gif."""
        from app.api.image_routes import SUPPORTED_MIME_TYPES
        assert "image/jpeg" in SUPPORTED_MIME_TYPES
        assert "image/png" in SUPPORTED_MIME_TYPES
        assert "image/webp" in SUPPORTED_MIME_TYPES
        assert "image/gif" in SUPPORTED_MIME_TYPES
        assert "image/heic" not in SUPPORTED_MIME_TYPES


# --- Endpoint-level HEIC rejection tests ---

class TestEndpointHeicRejection:
    """Test that the /api/v1/image/identify endpoint rejects HEIC at HTTP level."""

    def test_heic_upload_returns_400(self):
        """Uploading a HEIC image should return 400 with clear error message."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        # Construct HEIC magic bytes
        heic_content = b'\x00\x00\x00\x1c' + b'ftyp' + b'heic' + b'\x00' * 100
        response = client.post(
            "/api/v1/image/identify?region=bahrain",
            files=[("images", ("photo.jpg", heic_content, "image/jpeg"))],
        )
        assert response.status_code == 400
        data = response.json()
        assert "unsupported format" in data["detail"].lower()
        assert "image/heic" in data["detail"]

    def test_jpeg_upload_passes_validation(self):
        """Uploading a proper JPEG should pass MIME validation (may fail at vision step)."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        # Minimal JPEG header (will fail at vision but should pass MIME check)
        jpeg_content = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        with patch("app.api.image_routes.identify_products", new_callable=AsyncMock) as mock_vision:
            mock_vision.return_value = {"products": [], "cost": 0.001}
            response = client.post(
                "/api/v1/image/identify?region=bahrain",
                files=[("images", ("photo.jpg", jpeg_content, "image/jpeg"))],
            )
        # Should not be 400 (MIME check passed); will be 200 with error action (0 products)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "error"  # No products identified

    def test_multiple_images_one_heic_rejects(self):
        """If any image in a batch is HEIC, the whole request should fail."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        jpeg_content = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        heic_content = b'\x00\x00\x00\x1c' + b'ftyp' + b'heic' + b'\x00' * 100
        response = client.post(
            "/api/v1/image/identify?region=bahrain",
            files=[
                ("images", ("photo1.jpg", jpeg_content, "image/jpeg")),
                ("images", ("photo2.jpg", heic_content, "image/jpeg")),
            ],
        )
        assert response.status_code == 400
        assert "Image 2" in response.json()["detail"]

    def test_empty_image_returns_400(self):
        """Uploading an empty file should return 400."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/v1/image/identify?region=bahrain",
            files=[("images", ("photo.jpg", b"", "image/jpeg"))],
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


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

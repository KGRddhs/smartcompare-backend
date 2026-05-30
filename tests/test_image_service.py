"""Tests for image_service — tier cascade for product image URL resolution.

Mirrors price_service tier architecture:
- Tier 1.5 piggyback (page_scrape_image kwarg — FREE)
- Tier 1 Serper Images (paid, budget-gated)
- Tier 2 Firecrawl (existing breaker)
- Tier 2.5 Scrape.do (existing breaker)
- Tier 3 GPT extraction from organic results (paid, ~$0.0005)
- Final: None (frontend renders placeholder)
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Tier 1.5 — piggyback page-scrape image
# ---------------------------------------------------------------------------

class TestTier15Piggyback:
    @pytest.mark.asyncio
    async def test_piggyback_returns_immediately_without_any_paid_call(self):
        """When caller already has page_scrape_image, return it without firing any tier."""
        from app.services.image_service import get_product_image_url

        with patch("app.services.image_service.search_images", AsyncMock()) as m_serper, \
             patch("app.services.image_service.try_consume_serper_image_credit", MagicMock()) as m_consume, \
             patch("app.services.image_service.extract_image_via_gpt", AsyncMock()) as m_gpt:
            result = await get_product_image_url(
                "iPhone 15",
                region="bahrain",
                page_scrape_image="https://example.com/iphone15-page-scrape.jpg",
            )

        assert result == "https://example.com/iphone15-page-scrape.jpg"
        m_serper.assert_not_called()
        m_consume.assert_not_called()
        m_gpt.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_piggyback_falls_through_to_tier1(self):
        """Empty-string piggyback is treated as no piggyback; tier1 fires."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": [{"imageUrl": "https://serper.example/cat.jpg"}]}),
        ):
            result = await get_product_image_url("iPhone 15", region="bahrain", page_scrape_image="")

        assert result == "https://serper.example/cat.jpg"


# ---------------------------------------------------------------------------
# Tier 1 — Serper Images
# ---------------------------------------------------------------------------

class TestTier1SerperImages:
    @pytest.mark.asyncio
    async def test_tier1_returns_first_image_url(self):
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": [
                {"imageUrl": "https://serper.example/iphone15.jpg", "title": "iPhone 15"},
                {"imageUrl": "https://other.example/another.jpg"},
            ]}),
        ):
            result = await get_product_image_url("iPhone 15", region="bahrain")

        assert result == "https://serper.example/iphone15.jpg"

    @pytest.mark.asyncio
    async def test_tier1_skipped_when_budget_exhausted(self):
        """When try_consume returns False, Tier 1 is bypassed; search_images NOT called."""
        from app.services.image_service import get_product_image_url

        m_search = AsyncMock()
        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=False),
        ), patch("app.services.image_service.search_images", m_search), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("iPhone 15", region="bahrain")

        m_search.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_tier1_handles_empty_images_array(self):
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": []}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("Unknown Product XYZ", region="bahrain")

        assert result is None

    @pytest.mark.asyncio
    async def test_tier1_handles_missing_imageurl_key(self):
        """Serper returns item with no imageUrl key — falls through."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": [{"title": "no url"}]}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("Foo", region="bahrain")

        assert result is None

    @pytest.mark.asyncio
    async def test_tier1_handles_search_images_exception(self):
        """Serper API exception falls through; pipeline continues to Tier 3."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(side_effect=RuntimeError("network down")),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value="https://gpt.example/fallback.jpg"),
        ):
            result = await get_product_image_url(
                "Foo", region="bahrain",
                organic_results=[{"link": "https://foo.example", "snippet": "Foo product"}],
            )

        assert result == "https://gpt.example/fallback.jpg"

    @pytest.mark.asyncio
    async def test_tier1_handles_error_response_shape(self):
        """search_images returned {'images': [], 'error': 'Search not configured'} — falls through."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": [], "error": "Search not configured"}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("Foo", region="bahrain")

        assert result is None


# ---------------------------------------------------------------------------
# Tier 3 — GPT extraction from organic results
# ---------------------------------------------------------------------------

class TestTier3GPTFallback:
    @pytest.mark.asyncio
    async def test_tier3_returns_gpt_image_when_tier1_empty(self):
        from app.services.image_service import get_product_image_url

        organic = [
            {"link": "https://amazon.ae/iphone15", "snippet": "Apple iPhone 15"},
            {"link": "https://noon.com/iphone15", "snippet": "iPhone 15 Pro"},
        ]
        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": []}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value="https://gpt.example/iphone15-extracted.jpg"),
        ):
            result = await get_product_image_url(
                "iPhone 15", region="bahrain", organic_results=organic,
            )

        assert result == "https://gpt.example/iphone15-extracted.jpg"

    @pytest.mark.asyncio
    async def test_tier3_skipped_when_no_organic_results(self):
        from app.services.image_service import get_product_image_url

        m_gpt = AsyncMock()
        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": []}),
        ), patch("app.services.image_service.extract_image_via_gpt", m_gpt):
            result = await get_product_image_url("Foo", region="bahrain")

        m_gpt.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_tier3_handles_gpt_exception(self):
        """GPT exception → final None."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": []}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(side_effect=RuntimeError("openai timeout")),
        ):
            result = await get_product_image_url(
                "Foo", region="bahrain",
                organic_results=[{"link": "https://foo.example"}],
            )

        assert result is None


# ---------------------------------------------------------------------------
# Final fallback — None
# ---------------------------------------------------------------------------

class TestFinalFallback:
    @pytest.mark.asyncio
    async def test_returns_none_when_all_tiers_fail(self):
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": []}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url(
                "Foo", region="bahrain",
                organic_results=[{"link": "https://foo.example"}],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_product_name_empty(self):
        """Empty product name short-circuits to None — defensive gate against
        the GIGO pattern (per feedback_curl_test_vs_production_code: validate
        inputs first, don't burn paid credits on garbage queries)."""
        from app.services.image_service import get_product_image_url

        m_consume = MagicMock(return_value=True)
        m_search = AsyncMock()
        with patch(
            "app.services.image_service.try_consume_serper_image_credit", m_consume,
        ), patch("app.services.image_service.search_images", m_search):
            result = await get_product_image_url("", region="bahrain")

        assert result is None
        m_consume.assert_not_called()
        m_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_product_name_whitespace(self):
        from app.services.image_service import get_product_image_url

        m_consume = MagicMock(return_value=True)
        with patch(
            "app.services.image_service.try_consume_serper_image_credit", m_consume,
        ):
            result = await get_product_image_url("   ", region="bahrain")

        assert result is None
        m_consume.assert_not_called()


# ---------------------------------------------------------------------------
# Malformed Serper response edge cases (idle-time hardening per A3.5 brief)
# ---------------------------------------------------------------------------

class TestMalformedResponses:
    @pytest.mark.asyncio
    async def test_serper_returns_none_response(self):
        """search_images returns None (not a dict) — handled gracefully."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value=None),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("Foo", region="bahrain")

        assert result is None

    @pytest.mark.asyncio
    async def test_serper_returns_string_url_not_https(self):
        """Tier 1 image URL must be a string starting with http(s); reject other shapes."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": [{"imageUrl": "not-a-url"}]}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("Foo", region="bahrain")

        assert result is None

    @pytest.mark.asyncio
    async def test_serper_returns_non_string_imageurl(self):
        """imageUrl is a dict / number — reject + fall through."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": [{"imageUrl": 42}]}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value=None),
        ):
            result = await get_product_image_url("Foo", region="bahrain")

        assert result is None

    @pytest.mark.asyncio
    async def test_gpt_returns_non_url_string(self):
        """GPT returns a bare string but it's not a URL — reject."""
        from app.services.image_service import get_product_image_url

        with patch(
            "app.services.image_service.try_consume_serper_image_credit",
            MagicMock(return_value=True),
        ), patch(
            "app.services.image_service.search_images",
            AsyncMock(return_value={"images": []}),
        ), patch(
            "app.services.image_service.extract_image_via_gpt",
            AsyncMock(return_value="not-a-url"),
        ):
            result = await get_product_image_url(
                "Foo", region="bahrain",
                organic_results=[{"link": "https://foo.example"}],
            )

        assert result is None


# ---------------------------------------------------------------------------
# extract_image_via_gpt — Tier 3 internal helper
# ---------------------------------------------------------------------------

class TestExtractImageViaGPT:
    @pytest.mark.asyncio
    async def test_returns_url_from_gpt_response(self):
        """Happy path: GPT returns a JSON object with image_url."""
        from app.services import image_service

        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = (
            '{"image_url": "https://example.com/foo.jpg"}'
        )
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("app.services.image_service.get_client", return_value=mock_client):
            result = await image_service.extract_image_via_gpt(
                "Foo", [{"link": "https://foo.example", "snippet": "Foo product"}],
            )

        assert result == "https://example.com/foo.jpg"

    @pytest.mark.asyncio
    async def test_returns_none_when_gpt_returns_null(self):
        from app.services import image_service

        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '{"image_url": null}'
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("app.services.image_service.get_client", return_value=mock_client):
            result = await image_service.extract_image_via_gpt(
                "Foo", [{"link": "https://foo.example"}],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_response(self):
        """GPT wraps response in ```json ... ``` fences — strip them."""
        from app.services import image_service

        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = (
            '```json\n{"image_url": "https://example.com/foo.jpg"}\n```'
        )
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("app.services.image_service.get_client", return_value=mock_client):
            result = await image_service.extract_image_via_gpt(
                "Foo", [{"link": "https://foo.example"}],
            )

        assert result == "https://example.com/foo.jpg"

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_json(self):
        from app.services import image_service

        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "not json at all"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch("app.services.image_service.get_client", return_value=mock_client):
            result = await image_service.extract_image_via_gpt(
                "Foo", [{"link": "https://foo.example"}],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_when_organic_results_empty(self):
        from app.services import image_service

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        with patch("app.services.image_service.get_client", return_value=mock_client):
            result = await image_service.extract_image_via_gpt("Foo", [])

        assert result is None
        mock_client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_openai_exception(self):
        from app.services import image_service

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("openai 503"),
        )
        with patch("app.services.image_service.get_client", return_value=mock_client):
            result = await image_service.extract_image_via_gpt(
                "Foo", [{"link": "https://foo.example"}],
            )

        assert result is None

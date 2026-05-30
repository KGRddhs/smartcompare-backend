"""Contract tests for per-product image_url in the comparison response.

Per Bundle E S3 § A3.3 + § A3.4:
- Top level: response.products[i].image_url is `string | null`
- Canonical:  response.overview.products[i].image_url is `string | null`
- SSE specs event:  payload.products[i].image_url is `string | null`

Each test mocks at the boundary appropriate for the layer being asserted.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.response_builder import build_comparison_response


# ---------------------------------------------------------------------------
# response_builder contract
# ---------------------------------------------------------------------------

class TestResponseBuilderImageUrl:
    def test_overview_products_include_image_url_when_set(self):
        product_data = [
            {
                "brand": "Apple", "name": "iPhone 15",
                "image_url": "https://example.com/iphone15.jpg",
                "price": {"amount": 350, "currency": "BHD"},
                "rating": 4.6,
                "pros_cons": {"pros": ["a"], "cons": ["b"]},
            },
            {
                "brand": "Samsung", "name": "Galaxy S24",
                "image_url": "https://example.com/galaxy.jpg",
                "price": {"amount": 320, "currency": "BHD"},
                "rating": 4.4,
                "pros_cons": {"pros": ["c"], "cons": ["d"]},
            },
        ]
        result = build_comparison_response(
            product_data=product_data,
            comparison={"winner_index": 0},
        )

        ov = result["overview"]["products"]
        assert ov[0]["image_url"] == "https://example.com/iphone15.jpg"
        assert ov[1]["image_url"] == "https://example.com/galaxy.jpg"

    def test_overview_products_image_url_is_none_when_missing(self):
        product_data = [
            {"brand": "Apple", "name": "iPhone 15"},
            {"brand": "Samsung", "name": "Galaxy S24"},
        ]
        result = build_comparison_response(product_data=product_data, comparison={})
        for p in result["overview"]["products"]:
            assert p["image_url"] is None

    def test_legacy_products_alias_includes_image_url(self):
        """Top-level result['products'][i].image_url must mirror overview path
        (per memory/feedback_nested_field_path_in_parsers.md — parsers reading
        the alias must get the same shape)."""
        product_data = [
            {"brand": "A", "name": "X", "image_url": "https://a.example/x.jpg"},
            {"brand": "B", "name": "Y"},
        ]
        result = build_comparison_response(product_data=product_data, comparison={})
        assert result["products"][0]["image_url"] == "https://a.example/x.jpg"
        assert result["products"][1]["image_url"] is None

    def test_overview_image_url_field_always_present(self):
        """Even when neither product has image_url, the key must be in the
        overview payload (not just absent) — FE consumer relies on shape."""
        product_data = [{"brand": "A", "name": "X"}, {"brand": "B", "name": "Y"}]
        result = build_comparison_response(product_data=product_data, comparison={})
        for p in result["overview"]["products"]:
            assert "image_url" in p


# ---------------------------------------------------------------------------
# Orchestrator wiring — get_product_image_url is called from _fetch_product_data
# ---------------------------------------------------------------------------

class TestOrchestratorWiring:
    """Asserts the orchestrator calls get_product_image_url in Phase 1 and
    plumbs the result onto product_data[i]['image_url']. We test the
    private _fetch_product_data method directly with mocked tier collaborators
    to avoid spinning up the whole comparison pipeline."""

    @pytest.mark.asyncio
    async def test_phase1_calls_image_service_and_writes_to_result(self):
        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        product_info = {
            "brand": "Apple", "name": "iPhone 15", "variant": None,
            "category": "electronics", "search_query": "Apple iPhone 15",
        }

        # Mock all Phase 1 collaborators so we only exercise the image wiring
        with patch.object(
            service, "_get_specs", AsyncMock(return_value={"display": "6.1"})
        ), patch.object(
            service, "_get_price", AsyncMock(return_value={
                "amount": 350, "currency": "BHD", "retailer": "Apple Store",
                "image_url": None,
            }),
        ), patch.object(
            service, "_get_reviews", AsyncMock(return_value={
                "review_summary": {"overall_sentiment": "positive"},
            }),
        ), patch.object(
            service, "_get_verified_rating", AsyncMock(return_value={
                "rating": 4.6, "review_count": 100,
                "rating_verified": True, "rating_source": {"name": "test", "url": None},
            }),
        ), patch(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={"organic": []}),
        ), patch(
            "app.services.structured_comparison_service.get_product_image_url",
            AsyncMock(return_value="https://serper.example/iphone15.jpg"),
        ) as m_img, patch(
            "app.services.structured_comparison_service.tier2_fill_non_negotiables",
            AsyncMock(return_value={}),
        ), patch(
            "app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
            AsyncMock(return_value={}),
        ):
            result = await service._fetch_product_data(
                product_info, region="bahrain",
                include_specs=True, include_reviews=True, nocache=True,
            )

        m_img.assert_called_once()
        assert result["image_url"] == "https://serper.example/iphone15.jpg"

    @pytest.mark.asyncio
    async def test_page_scrape_image_overrides_tier1_result(self):
        """When _get_price returns an image_url on its price dict (Tier 1.5
        piggyback), it MUST override whatever the parallel-fired Serper
        Images / GPT result was — page-scrape image is FREE + higher fidelity."""
        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        product_info = {
            "brand": "Apple", "name": "iPhone 15", "variant": None,
            "category": "electronics", "search_query": "Apple iPhone 15",
        }

        with patch.object(
            service, "_get_specs", AsyncMock(return_value={"display": "6.1"}),
        ), patch.object(
            service, "_get_price", AsyncMock(return_value={
                "amount": 350, "currency": "BHD", "retailer": "Apple Store",
                # Tier 1.5 — price scraper found a page image
                "image_url": "https://apple.com/iphone15-hero.jpg",
            }),
        ), patch.object(
            service, "_get_reviews", AsyncMock(return_value={"review_summary": {}}),
        ), patch.object(
            service, "_get_verified_rating", AsyncMock(return_value={
                "rating": 4.6, "review_count": 100,
                "rating_verified": True, "rating_source": {"name": "test", "url": None},
            }),
        ), patch(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={"organic": []}),
        ), patch(
            "app.services.structured_comparison_service.get_product_image_url",
            AsyncMock(return_value="https://serper.example/iphone15.jpg"),
        ), patch(
            "app.services.structured_comparison_service.tier2_fill_non_negotiables",
            AsyncMock(return_value={}),
        ), patch(
            "app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
            AsyncMock(return_value={}),
        ):
            result = await service._fetch_product_data(
                product_info, region="bahrain",
                include_specs=True, include_reviews=True, nocache=True,
            )

        # Page-scrape image WINS over Tier 1 Serper result
        assert result["image_url"] == "https://apple.com/iphone15-hero.jpg"

    @pytest.mark.asyncio
    async def test_image_url_none_when_all_tiers_fail(self):
        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        product_info = {
            "brand": "Obscure", "name": "Widget X", "variant": None,
            "category": "other", "search_query": "Obscure Widget X",
        }

        with patch.object(
            service, "_get_specs", AsyncMock(return_value=None),
        ), patch.object(
            service, "_get_price", AsyncMock(return_value=None),
        ), patch.object(
            service, "_get_reviews", AsyncMock(return_value=None),
        ), patch.object(
            service, "_get_verified_rating", AsyncMock(return_value={
                "rating": None, "review_count": None,
                "rating_verified": False, "rating_source": None,
            }),
        ), patch(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={"organic": []}),
        ), patch(
            "app.services.structured_comparison_service.get_product_image_url",
            AsyncMock(return_value=None),
        ), patch(
            "app.services.structured_comparison_service.tier2_fill_non_negotiables",
            AsyncMock(return_value={}),
        ), patch(
            "app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
            AsyncMock(return_value={}),
        ):
            result = await service._fetch_product_data(
                product_info, region="bahrain",
                include_specs=True, include_reviews=True, nocache=True,
            )

        assert result["image_url"] is None

    @pytest.mark.asyncio
    async def test_image_url_exception_does_not_break_phase1(self):
        """When get_product_image_url raises, Phase 1 still returns; image_url is None."""
        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        product_info = {
            "brand": "Apple", "name": "iPhone 15", "variant": None,
            "category": "electronics", "search_query": "Apple iPhone 15",
        }

        with patch.object(
            service, "_get_specs", AsyncMock(return_value={"display": "6.1"}),
        ), patch.object(
            service, "_get_price", AsyncMock(return_value={
                "amount": 350, "currency": "BHD", "image_url": None,
            }),
        ), patch.object(
            service, "_get_reviews", AsyncMock(return_value={"review_summary": {}}),
        ), patch.object(
            service, "_get_verified_rating", AsyncMock(return_value={
                "rating": 4.6, "review_count": 100,
                "rating_verified": True, "rating_source": {"name": "test", "url": None},
            }),
        ), patch(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={"organic": []}),
        ), patch(
            "app.services.structured_comparison_service.get_product_image_url",
            AsyncMock(side_effect=RuntimeError("image pipeline crashed")),
        ), patch(
            "app.services.structured_comparison_service.tier2_fill_non_negotiables",
            AsyncMock(return_value={}),
        ), patch(
            "app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
            AsyncMock(return_value={}),
        ):
            result = await service._fetch_product_data(
                product_info, region="bahrain",
                include_specs=True, include_reviews=True, nocache=True,
            )

        # Phase 1 must complete; image_url falls through to None
        assert result.get("image_url") is None
        # Specs + price still populated — image failure isolated
        assert result["specs"] == {"display": "6.1"}

    @pytest.mark.asyncio
    async def test_organic_results_passed_to_image_service(self):
        """The unified search organic results must reach get_product_image_url
        so Tier 3 GPT can use them."""
        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        product_info = {
            "brand": "Apple", "name": "iPhone 15", "variant": None,
            "category": "electronics", "search_query": "Apple iPhone 15",
        }
        organic_payload = [
            {"link": "https://apple.com/iphone15", "snippet": "Apple iPhone 15"},
            {"link": "https://amazon.ae/iphone15", "snippet": "iPhone 15 256GB"},
        ]

        with patch.object(
            service, "_get_specs", AsyncMock(return_value={"display": "6.1"}),
        ), patch.object(
            service, "_get_price", AsyncMock(return_value={
                "amount": 350, "currency": "BHD", "image_url": None,
            }),
        ), patch.object(
            service, "_get_reviews", AsyncMock(return_value={"review_summary": {}}),
        ), patch.object(
            service, "_get_verified_rating", AsyncMock(return_value={
                "rating": 4.6, "review_count": 100,
                "rating_verified": True, "rating_source": {"name": "test", "url": None},
            }),
        ), patch(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={"organic": organic_payload}),
        ), patch(
            "app.services.structured_comparison_service.get_product_image_url",
            AsyncMock(return_value="https://gpt.example/x.jpg"),
        ) as m_img, patch(
            "app.services.structured_comparison_service.tier2_fill_non_negotiables",
            AsyncMock(return_value={}),
        ), patch(
            "app.services.structured_comparison_service.tier3_synthesize_non_negotiables",
            AsyncMock(return_value={}),
        ):
            await service._fetch_product_data(
                product_info, region="bahrain",
                include_specs=True, include_reviews=True, nocache=True,
            )

        # Verify get_product_image_url received the organic results
        call_kwargs = m_img.call_args.kwargs
        assert call_kwargs.get("organic_results") == organic_payload
        assert call_kwargs.get("region") == "bahrain"


# ---------------------------------------------------------------------------
# SSE specs event piggyback contract (A3.4)
# ---------------------------------------------------------------------------

class TestSSESpecsEventShape:
    """The streaming compare yields ('specs', payload). The payload's
    products[i] dict MUST include image_url. We assert by inspecting the
    yield directly via a thin shim around the generator."""

    def test_sse_specs_event_includes_image_url_field_in_payload_shape(self):
        """Static shape check — grep the source for the image_url key in the
        specs yield (defense against accidental removal in a future refactor)."""
        import inspect
        from app.services import structured_comparison_service

        src = inspect.getsource(structured_comparison_service)
        # The streaming specs yield projects per-product dicts. Verify the
        # image_url key is in the list-comprehension expression bounded by
        # the specs event tuple.
        # Find the streaming specs yield block.
        idx = src.find('yield ("specs"')
        assert idx >= 0, "could not locate streaming specs yield"
        # Look ahead for the closing of the dict literal that contains it
        # (next 800 chars cover the comprehension body).
        window = src[idx:idx + 800]
        assert '"image_url": pd.get("image_url")' in window, (
            "SSE specs event payload must include image_url per A3.4"
        )

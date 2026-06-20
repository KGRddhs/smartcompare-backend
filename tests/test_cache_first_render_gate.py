"""Phase 1 Task 1.2 — cache-first gate before ANY firecrawl/scrapedo render.

The free-tier-survival invariant: a cache hit must serve $0 WITHOUT touching the
heavy scrapers. `_get_price` checks L1 (Redis) → L2 (DB) → negative-cache BEFORE
the Tier-1.5 genuine scrape cascade (which is the only thing that fires
firecrawl/scrapedo, via fan_out_price_lookup). This pins that ordering: on any
cache hit, fan_out_price_lookup + the scraper services are NEVER called.

We assert on the heavy-render ENTRY points (fan_out_price_lookup and the
firecrawl/scrapedo service calls) rather than cascade internals, so the test
stays robust as the cascade evolves.
"""

import asyncio
from contextlib import ExitStack
from unittest.mock import patch, AsyncMock

import pytest


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _service():
    from app.services.structured_comparison_service import StructuredComparisonService
    return StructuredComparisonService()


class TestCacheFirstSkipsScrapers:
    def test_l1_hit_skips_firecrawl_scrapedo(self):
        """An L1 Redis hit returns immediately — fan_out + firecrawl + scrapedo
        are never called."""
        service = _service()
        cached = {"amount": 80.0, "currency": "BHD", "source_method": "page_scrape_jsonld"}
        with ExitStack() as es:
            es.enter_context(patch(
                "app.services.structured_comparison_service.validate_price_query",
                return_value=True))
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=cached))
            m_fan = es.enter_context(patch(
                "app.services.structured_comparison_service.fan_out_price_lookup",
                new=AsyncMock(return_value=[])))
            m_fc = es.enter_context(patch(
                "app.services.firecrawl_service.scrape_page_with_status",
                new=AsyncMock(return_value=(None, 0))))
            m_sd = es.enter_context(patch(
                "app.services.scrapedo_service.render_page_with_status",
                new=AsyncMock(return_value=(None, 0, 0))))
            result = run_async(service._get_price(
                "Apple", "iPhone 15", "256GB", "bahrain",
                "Apple iPhone 15 256GB", nocache=False, category="electronics",
            ))
        assert result["amount"] == 80.0
        assert result.get("_cached") is True
        m_fan.assert_not_called()
        m_fc.assert_not_called()
        m_sd.assert_not_called()

    def test_l2_hit_skips_firecrawl_scrapedo(self):
        """An L2 DB hit (L1 miss) also returns before the scrape cascade."""
        service = _service()
        db_price = {"amount": 244.99, "currency": "BHD", "source_method": "shopify_json"}
        with ExitStack() as es:
            es.enter_context(patch(
                "app.services.structured_comparison_service.validate_price_query",
                return_value=True))
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=None))
            es.enter_context(patch(
                "app.services.product_data_service.get_cached_price",
                new=AsyncMock(return_value=db_price)))
            es.enter_context(patch(
                "app.services.structured_comparison_service.set_cached"))
            m_fan = es.enter_context(patch(
                "app.services.structured_comparison_service.fan_out_price_lookup",
                new=AsyncMock(return_value=[])))
            m_fc = es.enter_context(patch(
                "app.services.firecrawl_service.scrape_page_with_status",
                new=AsyncMock(return_value=(None, 0))))
            m_sd = es.enter_context(patch(
                "app.services.scrapedo_service.render_page_with_status",
                new=AsyncMock(return_value=(None, 0, 0))))
            result = run_async(service._get_price(
                "Sony", "WH-1000XM5", None, "bahrain",
                "Sony WH-1000XM5", nocache=False, category="electronics",
            ))
        assert result["amount"] == 244.99
        assert result.get("_cached") is True
        m_fan.assert_not_called()
        m_fc.assert_not_called()
        m_sd.assert_not_called()

    def test_negative_cache_hit_skips_firecrawl_scrapedo(self):
        """A negative-cache (structural dead-end) hit also skips the scrapers —
        this is the whole point of Task 1.3: never re-burn a scrape on a known
        dead-end."""
        service = _service()
        stored = {"amount": 85.0, "currency": "BHD", "source_method": "converted_usd"}
        with ExitStack() as es:
            es.enter_context(patch(
                "app.services.structured_comparison_service.validate_price_query",
                return_value=True))
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=None))
            es.enter_context(patch(
                "app.services.product_data_service.get_cached_price",
                new=AsyncMock(return_value=None)))
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_negative_cache",
                return_value=stored))
            m_fan = es.enter_context(patch(
                "app.services.structured_comparison_service.fan_out_price_lookup",
                new=AsyncMock(return_value=[])))
            m_fc = es.enter_context(patch(
                "app.services.firecrawl_service.scrape_page_with_status",
                new=AsyncMock(return_value=(None, 0))))
            m_sd = es.enter_context(patch(
                "app.services.scrapedo_service.render_page_with_status",
                new=AsyncMock(return_value=(None, 0, 0))))
            result = run_async(service._get_price(
                "Tom Ford", "Tobacco Vanille", None, "bahrain",
                "Tom Ford Tobacco Vanille", nocache=False, category="fragrances",
            ))
        assert result["amount"] == 85.0
        m_fan.assert_not_called()
        m_fc.assert_not_called()
        m_sd.assert_not_called()

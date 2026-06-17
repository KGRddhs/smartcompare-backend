"""Phase 1 Task 1.3 — negative-cache structural dead-ends.

LOCKED: negative-cache TTL = 30 DAYS.

Some products have NO genuine BH source at all (luxury fragrance / haircare /
gadgets behind Cloudflare). For those, the expensive Tier-1.5 genuine scrape
cascade (discovery Serper + curl fan_out + firecrawl/scrapedo) runs, finds
nothing genuine, and falls back to a converted/estimated price EVERY time — a
pure waste of the finite free scraper budget on every request.

The negative-cache records that structural dead-end: when a full resolution
produces only a NON-genuine price, a `nogenuine:{price_cache_key}` sentinel is
written (30d). A second call within TTL returns the stored pending/estimated
result directly and SKIPS the scrape cascade — never re-burning a scrape for a
known dead-end.

This module tests:
  - the pure helpers (key shape, should-negative-cache predicate, TTL constant)
  - the _get_price short-circuit behavior (mocked cascade, like the cache-bust
    probe test) — sentinel present → cascade not run.
"""

import asyncio
from contextlib import ExitStack
from unittest.mock import patch, AsyncMock

import pytest

from app.services.price_service import (
    NEGATIVE_PRICE_CACHE_TTL,
    negative_cache_key,
    should_negative_cache,
)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ------------------------------------------------------------- helpers ---

class TestNegativeCacheHelpers:
    def test_ttl_is_30_days(self):
        assert NEGATIVE_PRICE_CACHE_TTL == 30 * 24 * 60 * 60

    def test_key_shape(self):
        assert negative_cache_key("price:abc123") == "nogenuine:price:abc123"

    def test_key_is_deterministic(self):
        assert negative_cache_key("price:x") == negative_cache_key("price:x")


class TestShouldNegativeCache:
    def test_estimated_should_negative_cache(self):
        assert should_negative_cache({"amount": 70.0, "source_method": "estimated"}) is True

    def test_converted_usd_should_negative_cache(self):
        # converted_usd is NOT genuine BH — it's a structural fallback; cache it
        # so we don't re-scrape hunting for a genuine price that isn't there.
        assert should_negative_cache({"amount": 85.0, "source_method": "converted_usd"}) is True

    def test_converted_fallback_should_negative_cache(self):
        assert should_negative_cache({"amount": 85.0, "source_method": "converted_fallback"}) is True

    def test_pending_genuine_should_negative_cache(self):
        # A price-pending shape (no amount, unavailable) is the strongest signal
        # of a structural gap.
        assert should_negative_cache({"amount": None, "unavailable": True, "reason": "pending_genuine"}) is True

    def test_genuine_local_bhd_should_not(self):
        assert should_negative_cache({"amount": 80.0, "source_method": "local_bhd"}) is False

    def test_genuine_page_scrape_jsonld_should_not(self):
        assert should_negative_cache({"amount": 79.5, "source_method": "page_scrape_jsonld"}) is False

    def test_genuine_shopify_json_should_not(self):
        assert should_negative_cache({"amount": 244.99, "source_method": "shopify_json"}) is False

    def test_none_price_should_negative_cache(self):
        assert should_negative_cache(None) is True

    def test_validation_rejected_should_not_negative_cache(self):
        # A garbage-query rejection is not a structural dead-end — don't cache it
        # as one (a real product typed later under the same key must re-resolve).
        assert should_negative_cache(
            {"amount": 0, "source_method": "validation_rejected"}
        ) is False


# ------------------------------------ _get_price short-circuit behavior ---

class TestGetPriceNegativeCacheShortCircuit:
    """Sentinel present → the cascade is NOT run; the stored non-genuine result
    is served. Mirrors the cache-bust probe's mock-the-cascade style so it pins
    BEHAVIOR (cascade skipped) not internals."""

    def _service(self):
        from app.services.structured_comparison_service import StructuredComparisonService
        return StructuredComparisonService()

    def test_sentinel_hit_skips_cascade(self):
        service = self._service()
        stored = {"amount": 85.0, "currency": "BHD", "source_method": "converted_usd"}
        with ExitStack() as es:
            es.enter_context(patch(
                "app.services.structured_comparison_service.validate_price_query",
                return_value=True))
            # L1 + L2 both MISS so we reach the sentinel check.
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=None))
            es.enter_context(patch(
                "app.services.product_data_service.get_cached_price",
                new=AsyncMock(return_value=None)))
            # The negative-cache sentinel is PRESENT (prior dead-end).
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_negative_cache",
                return_value=stored))
            # If the cascade runs, it would hit search_product_prices — assert it
            # does NOT (the whole point of the negative cache).
            m_search = es.enter_context(patch(
                "app.services.structured_comparison_service.search_product_prices",
                new=AsyncMock(return_value={"shopping": [], "organic": []})))
            result = run_async(service._get_price(
                "Tom Ford", "Tobacco Vanille", None, "bahrain",
                "Tom Ford Tobacco Vanille", nocache=False, category="fragrances",
            ))
        assert result["amount"] == 85.0
        assert result["source_method"] == "converted_usd"
        assert result.get("_cached") is True
        m_search.assert_not_called()

    def test_nocache_ignores_sentinel(self):
        """With nocache=True the sentinel is bypassed so a forced refresh can
        re-attempt the cascade (e.g. eval nocache runs). The load-bearing pin is
        that get_negative_cache is NEVER consulted under nocache — the cascade's
        final amount depends on the live Tier-1.5 path, so we don't assert on it
        (that would be a flaky network assertion)."""
        service = self._service()
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
            m_neg = es.enter_context(patch(
                "app.services.structured_comparison_service.get_negative_cache",
                return_value=stored))
            # Keep the cascade cheap + hermetic: no Serper shopping results and
            # no Tier-1.5 escalation, so it terminates at the mocked Tier-3.
            es.enter_context(patch(
                "app.services.structured_comparison_service.search_product_prices",
                new=AsyncMock(return_value={"shopping": [], "organic": []})))
            es.enter_context(patch(
                "app.services.structured_comparison_service.should_escalate",
                return_value=False))
            es.enter_context(patch(
                "app.services.structured_comparison_service.extract_price_from_training_data",
                new=AsyncMock(return_value=(
                    {"amount": 250, "currency": "BHD", "source_method": "estimated", "estimated": True},
                    {"prompt_tokens": 0, "completion_tokens": 0},
                ))))
            es.enter_context(patch(
                "app.services.structured_comparison_service.set_cached"))
            es.enter_context(patch.object(
                type(service), "_save_price_to_db", return_value=None))
            es.enter_context(patch(
                "app.services.structured_comparison_service.set_negative_cache"))
            result = run_async(service._get_price(
                "Tom Ford", "Tobacco Vanille", None, "bahrain",
                "Tom Ford Tobacco Vanille", nocache=True, category="fragrances",
            ))
        # nocache=True must NOT consult the sentinel (the whole point).
        m_neg.assert_not_called()
        # And a result is returned (the cascade ran instead of the sentinel).
        assert isinstance(result, dict)

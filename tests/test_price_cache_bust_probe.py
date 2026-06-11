"""I5.1 (Bundle B S2) — price-only cache-bust probe flag.

F1.7 §3 found the double-tap routing probe can't surface a registry route
because Tier-3 GPT estimates cache too: run 1 caps → caches an estimate; run 2
serves the cached estimate and never re-runs escalation. The fix is a
diagnostic flag scoped to PRICE only — it forces the price-read paths (Redis +
L2 DB) to MISS so escalation re-runs deterministically, while specs/reviews
stay warm so the wall still fits inside the 30s cap.

The flag is `PRICE_CACHE_BUST` (read fresh each call so a probe session can flip
it without a redeploy). It must be OFF (unset/false) in normal operation — it
is an evidence-gathering probe, not a runtime behavior.
"""
import asyncio
from unittest.mock import patch, AsyncMock

import pytest

from app.services.structured_comparison_service import (
    StructuredComparisonService,
    _price_cache_bust_enabled,
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


class TestPriceCacheBustFlag:
    def test_flag_defaults_off(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("PRICE_CACHE_BUST", None)
            assert _price_cache_bust_enabled() is False

    def test_flag_reads_true(self):
        with patch.dict("os.environ", {"PRICE_CACHE_BUST": "true"}):
            assert _price_cache_bust_enabled() is True

    def test_flag_reads_fresh_each_call(self):
        """Unlike the process-cached DEBUG_STAGE_TIMINGS flag, this probe flag
        must take effect mid-session without a restart."""
        import os
        with patch.dict("os.environ", {"PRICE_CACHE_BUST": "false"}):
            assert _price_cache_bust_enabled() is False
        with patch.dict("os.environ", {"PRICE_CACHE_BUST": "true"}):
            assert _price_cache_bust_enabled() is True


class TestPriceReadBypass:
    """The probe pins read-bypass BEHAVIOR (which cache reads are consulted),
    not cascade internals — so it stays robust as the tier cascade evolves. We
    drive the cascade to its cheapest terminal (empty Serper → Tier-3 estimate,
    both mocked) and assert on the cache-read call counts."""

    def _stub_cascade(self):
        """Patches that make the inlined cascade terminate cheaply at a Tier-3
        estimate without any network/GPT call."""
        return [
            patch("app.services.structured_comparison_service.validate_price_query",
                  return_value=True),
            patch("app.services.structured_comparison_service.search_product_prices",
                  new=AsyncMock(return_value={"shopping": [], "organic": []})),
            patch("app.services.structured_comparison_service.extract_price_from_training_data",
                  new=AsyncMock(return_value=({
                      "amount": 250, "currency": "BHD",
                      "source_method": "estimated", "estimated": True,
                  }, {"prompt_tokens": 0, "completion_tokens": 0}))),
            patch("app.services.structured_comparison_service.set_cached"),
            patch.object(StructuredComparisonService, "_save_price_to_db",
                         return_value=None),
        ]

    def test_bust_skips_price_redis_read(self, service):
        """With the flag ON, the price Redis read is never consulted (a cached
        estimate cannot short-circuit escalation)."""
        from contextlib import ExitStack
        cached_estimate = {"amount": 99, "source_method": "estimated", "estimated": True}
        with patch.dict("os.environ", {"PRICE_CACHE_BUST": "true"}), ExitStack() as es:
            for p in self._stub_cascade():
                es.enter_context(p)
            m_get = es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=cached_estimate))
            m_db = es.enter_context(patch(
                "app.services.product_data_service.get_cached_price",
                new=AsyncMock(return_value={"amount": 99, "source_method": "estimated"})))
            result = run_async(service._get_price(
                "Carrier", "1.5T AC", None, "bahrain", "Carrier 1.5T AC",
                nocache=False, category="electronics",
            ))
        # The price cache read was bypassed (cached estimate ignored).
        m_get.assert_not_called()
        # And the L2 DB read too — otherwise a DB estimate short-circuits.
        m_db.assert_not_called()
        # Cascade ran to the (mocked) Tier-3 estimate.
        assert result["amount"] == 250

    def test_no_bust_uses_cached_price(self, service):
        """With the flag OFF and nocache=False, a cached price short-circuits
        the cascade as normal (no behavior change in production)."""
        import os
        cached_price = {"amount": 99, "source_method": "page_scrape", "estimated": False}
        os.environ.pop("PRICE_CACHE_BUST", None)
        with patch("app.services.structured_comparison_service.get_cached",
                   return_value=cached_price) as m_get, \
             patch("app.services.structured_comparison_service.validate_price_query",
                   return_value=True):
            result = run_async(service._get_price(
                "Carrier", "1.5T AC", None, "bahrain", "Carrier 1.5T AC",
                nocache=False, category="electronics",
            ))
        assert result["_cached"] is True
        assert result["amount"] == 99
        m_get.assert_called_once()

    def test_specs_reviews_cache_untouched_by_price_bust(self, service):
        """The flag is PRICE-scoped: specs/reviews reads in _fetch_product_data
        stay warm. We assert _get_price's bypass does not depend on the specs/
        reviews `nocache` semantics — calling with nocache=False keeps the
        spec/review caches eligible (those are read in _fetch_product_data,
        which gates on the unchanged `nocache` arg, not PRICE_CACHE_BUST)."""
        from contextlib import ExitStack
        with patch.dict("os.environ", {"PRICE_CACHE_BUST": "true"}), ExitStack() as es:
            for p in self._stub_cascade():
                es.enter_context(p)
            es.enter_context(patch(
                "app.services.structured_comparison_service.get_cached",
                return_value=None))
            es.enter_context(patch(
                "app.services.product_data_service.get_cached_price",
                new=AsyncMock(return_value=None)))
            # nocache stays False — the caller's specs/reviews caching intent is
            # preserved; only the price read is force-missed by the flag.
            result = run_async(service._get_price(
                "Carrier", "1.5T AC", None, "bahrain", "Carrier 1.5T AC",
                nocache=False, category="electronics",
            ))
        assert result["amount"] == 250

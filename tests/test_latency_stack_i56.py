"""I5.6 (Bundle B S2) — S2-safe latency stack (zero quality risk).

First lever: _get_price must run CONCURRENTLY with the unified Serper search in
_fetch_product_data. Today the unified `search_web` is awaited (ssc ~2067)
BEFORE the Phase-1 task list (which builds the price task) is gathered — so the
unified-search wall and the price wall run SEQUENTIALLY even though price has no
dependency on the unified search (price runs its OWN search_product_prices /
Tier-1.5 cascade). Overlapping them shaves the smaller of the two off the
per-product wall with zero quality change.

This first test pins the concurrency: with a slow unified search and a slow
price fetch, the combined _fetch_product_data wall must be ~max(the two), NOT
~sum. RED until the change lands.
"""
import asyncio
import time
from unittest.mock import patch, AsyncMock

import pytest

from app.services.structured_comparison_service import StructuredComparisonService


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.mark.asyncio
async def test_price_starts_concurrent_with_unified_search():
    """_fetch_product_data must kick off the price fetch CONCURRENTLY with the
    unified search — proven by their START timestamps being near-simultaneous,
    not separated by the unified-search wall. This assertion is immune to
    network noise from un-mocked sibling calls (image/rating) because it
    measures WHEN the two start relative to each other, not the total wall.
    Pre-I5.6: price started only AFTER `await search_web` returned (gap ≈ the
    unified-search delay). Post-I5.6: gap ≈ 0."""
    svc = StructuredComparisonService()

    UNIFIED_DELAY = 1.0
    starts: dict = {}

    async def slow_unified(*_a, **_k):
        # Record only the FIRST unified-search start (there may be >1 search_web
        # call across the fetch; we only care when the FIRST one began, since
        # that's the wall the price task overlaps).
        starts.setdefault("unified", time.perf_counter())
        await asyncio.sleep(UNIFIED_DELAY)
        return {"organic": [], "shopping": []}

    async def timed_price(*_a, **_k):
        starts.setdefault("price", time.perf_counter())
        return {"amount": 100, "currency": "BHD", "source_method": "local_bhd"}

    async def fast(*_a, **_k):
        return {}

    product = {"brand": "Carrier", "name": "1.5T AC", "variant": None,
               "category": "electronics", "search_query": "Carrier 1.5T AC"}

    with patch("app.services.structured_comparison_service.search_web", new=AsyncMock(side_effect=slow_unified)), \
         patch("app.services.structured_comparison_service.search_product_prices", new=AsyncMock(return_value={"shopping": [], "organic": []})), \
         patch("app.services.structured_comparison_service.get_cached", return_value=None), \
         patch("app.services.structured_comparison_service.get_product_image_url", new=AsyncMock(return_value=None)), \
         patch.object(svc, "_get_price", new=AsyncMock(side_effect=timed_price)), \
         patch.object(svc, "_get_specs", new=AsyncMock(side_effect=fast)), \
         patch.object(svc, "_get_reviews", new=AsyncMock(side_effect=fast)):
        await svc._fetch_product_data(product, "bahrain", include_specs=True,
                                      include_reviews=True, nocache=True)

    assert "unified" in starts and "price" in starts, "both must run"
    gap = abs(starts["price"] - starts["unified"])
    # Concurrent: both start within a few ms of each other. Sequential would
    # put price's start ≈ UNIFIED_DELAY (1.0s) after unified's start.
    assert gap < 0.3, (
        f"price started {gap:.2f}s after the unified search — they ran "
        f"SEQUENTIALLY (gap ≈ unified delay {UNIFIED_DELAY}s); I5.6 requires "
        f"price to start concurrently (gap ≈ 0)"
    )

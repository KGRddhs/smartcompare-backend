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
async def test_price_runs_concurrent_with_unified_search():
    """_fetch_product_data overlaps the unified search with the price fetch:
    wall ≈ max(unified_delay, price_delay), not the sum."""
    svc = StructuredComparisonService()

    UNIFIED_DELAY = 1.0
    PRICE_DELAY = 1.0

    async def slow_unified(*_a, **_k):
        await asyncio.sleep(UNIFIED_DELAY)
        return {"organic": [], "shopping": []}

    async def slow_price(*_a, **_k):
        await asyncio.sleep(PRICE_DELAY)
        return {"amount": 100, "currency": "BHD", "source_method": "local_bhd"}

    async def fast_specs(*_a, **_k):
        return {"ram": "12 GB"}

    async def fast_reviews(*_a, **_k):
        return {"summary": "ok", "pros": [], "cons": []}

    async def fast_rating(*_a, **_k):
        return {"rating": 4.5, "review_count": 100, "rating_verified": False,
                "rating_source": {"name": "t", "url": None}}

    product = {"brand": "Carrier", "name": "1.5T AC", "variant": None,
               "category": "electronics", "search_query": "Carrier 1.5T AC"}

    with patch("app.services.structured_comparison_service.search_web", new=AsyncMock(side_effect=slow_unified)), \
         patch("app.services.structured_comparison_service.get_cached", return_value=None), \
         patch.object(svc, "_get_price", new=AsyncMock(side_effect=slow_price)), \
         patch.object(svc, "_get_specs", new=AsyncMock(side_effect=fast_specs)), \
         patch.object(svc, "_get_reviews", new=AsyncMock(side_effect=fast_reviews)), \
         patch.object(svc, "_get_rating", new=AsyncMock(side_effect=fast_rating)), \
         patch.object(svc, "_get_product_image", new=AsyncMock(return_value=None)):
        start = time.perf_counter()
        await svc._fetch_product_data(product, "bahrain", include_specs=True,
                                      include_reviews=True, nocache=True)
        elapsed = time.perf_counter() - start

    # Concurrent: ~max(1.0, 1.0)=1.0s + overhead. Sequential would be ~2.0s.
    assert elapsed < 1.6, (
        f"unified search + price ran SEQUENTIALLY ({elapsed:.2f}s ≈ sum); "
        f"I5.6 requires them concurrent (≈max ≈ 1.0s)"
    )

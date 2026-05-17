"""D2 Intervention 1 — _get_reviews must run in Phase 1 alongside specs+price,
not in Phase 2. Asserts wall-time = max(...), not sum."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.structured_comparison_service import (
    StructuredComparisonService, get_comparison_service,
)


@pytest.mark.asyncio
async def test_phase1_runs_reviews_in_parallel_with_specs_price():
    """Phase 1 should now run specs + price + reviews concurrently.
    Total wall time must equal max(specs, price, reviews), not their sum."""

    async def slow_specs(*args, **kwargs):
        await asyncio.sleep(0.8)
        return {"ram": "12 GB"}

    async def slow_price(*args, **kwargs):
        await asyncio.sleep(0.6)
        return {"amount": 100, "currency": "BHD", "source_method": "local_bhd"}

    async def slow_reviews(*args, **kwargs):
        await asyncio.sleep(0.7)
        return {"summary": "test", "pros": [], "cons": []}

    async def fast_rating(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"rating": 4.5, "review_count": 100, "rating_verified": False, "rating_source": {"name": "test", "url": None}}

    with patch.object(
        StructuredComparisonService, "_get_specs", new=slow_specs,
    ), patch.object(
        StructuredComparisonService, "_get_price", new=slow_price,
    ), patch.object(
        StructuredComparisonService, "_get_reviews", new=slow_reviews,
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating", new=fast_rating,
    ), patch(
        "app.services.structured_comparison_service.search_web",
        new=AsyncMock(return_value={"organic": []}),
    ):
        svc = get_comparison_service()
        product_info = {
            "brand": "Apple", "name": "iPhone 17", "variant": None,
            "category": "electronics", "search_query": "Apple iPhone 17",
        }

        start = asyncio.get_event_loop().time()
        result = await svc._fetch_product_data(
            product_info, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # If reviews runs IN PARALLEL with specs+price (D2 Intervention 1):
        #   Phase 1 wall = max(0.8, 0.6, 0.7) = 0.8s
        #   Phase 2 wall = max(0.1, ...) = ~0.1s
        #   Total ~0.9s
        # If reviews runs SEQUENTIALLY in Phase 2 (current behavior pre-D2):
        #   Phase 1 wall = max(0.8, 0.6) = 0.8s
        #   Phase 2 wall = max(0.7, 0.1) = 0.7s
        #   Total ~1.5s
        assert elapsed < 1.2, (
            f"Reviews appears to be running in Phase 2 (took {elapsed:.2f}s, "
            f"expected <1.2s for parallel with Phase 1). "
            f"D2 Intervention 1 not effective."
        )

        # Sanity: result must still have all 4 keys populated
        assert result.get("specs"), "specs missing from result"
        assert result.get("price"), "price missing from result"
        assert result.get("reviews"), "reviews missing from result"

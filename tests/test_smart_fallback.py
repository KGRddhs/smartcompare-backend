"""Bucket A bug 3c - smart-fallback for missing critical schema fields runs in parallel."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.structured_comparison_service import (
    StructuredComparisonService, get_comparison_service,
)


def _make_slow_search_web(fallback_delay: float, unified_delay: float = 0.0):
    """Mock search_web that distinguishes the fallback query (ends with
    'specifications') from the unified pre-Phase-1 search (ends with
    'specifications reviews price'). Lets timing assertions target the
    Phase 2 fallback path only."""
    async def _impl(*args, **kwargs):
        query = args[0] if args else kwargs.get("query", "")
        is_unified = "reviews price" in query
        await asyncio.sleep(unified_delay if is_unified else fallback_delay)
        if is_unified:
            return {"organic": [{"snippet": "spec context", "title": "t"}]}
        return {"organic": [{"snippet": "Galaxy S25 Ultra front camera: 12 MP"}]}
    return _impl


@pytest.mark.asyncio
async def test_smart_fallback_runs_in_parallel_with_phase_2():
    """The smart-fallback Serper queries must run concurrently with
    Phase 2 (reviews+rating). Total wall time should be max(phase2, fallback),
    not sum - within the 3s cap."""

    slow_search_web = _make_slow_search_web(fallback_delay=1.5, unified_delay=0.0)

    async def slow_get_reviews(*args, **kwargs):
        await asyncio.sleep(2.0)  # Phase 2 reviews
        return {"summary": "test", "pros": [], "cons": []}

    async def fast_get_rating(*args, **kwargs):
        await asyncio.sleep(0.5)
        return {"rating": 4.5, "review_count": 100, "rating_verified": False, "rating_source": {"name": "test", "url": None}}

    async def fake_extract_targeted(*args, **kwargs):
        # Simulates the small GPT call returning a filled field
        return {"front_camera": "12 MP f/2.2"}

    with patch.object(
        StructuredComparisonService, "_get_reviews", new=slow_get_reviews,
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating", new=fast_get_rating,
    ), patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "12 GB", "_field_confidence": {"ram": "snippet"}}),
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch(
        "app.services.structured_comparison_service.search_web", new=slow_search_web,
    ), patch(
        "app.services.openai_service.extract_specs_targeted", new=fake_extract_targeted,
    ):
        svc = get_comparison_service()
        product_info = {
            "brand": "Samsung",
            "name": "Galaxy S25 Ultra",
            "variant": None,
            "category": "electronics",
            "search_query": "Samsung Galaxy S25 Ultra",
        }

        start = asyncio.get_event_loop().time()
        result = await svc._fetch_product_data(
            product_info, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Parallel: max(phase2=2.0, fallback=1.5) = 2.0s
        # Sequential: 2.0 + 1.5 = 3.5s
        assert elapsed < 2.8, f"Smart-fallback ran sequentially with Phase 2 (took {elapsed:.2f}s, expected <2.8s for parallel)"


@pytest.mark.asyncio
async def test_smart_fallback_capped_at_3_seconds():
    """If fallback Serper query exceeds 3s cap, it gets cancelled gracefully."""

    slow_search_web = _make_slow_search_web(fallback_delay=5.0, unified_delay=0.0)

    async def fake_extract_targeted(*args, **kwargs):
        return {}

    with patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "12 GB"}),  # Missing front_camera etc
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch.object(
        StructuredComparisonService, "_get_reviews",
        new=AsyncMock(return_value={"summary": "ok", "pros": [], "cons": []}),
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating",
        new=AsyncMock(return_value={"rating": 4.5, "review_count": 100, "rating_verified": False, "rating_source": {"name": "test", "url": None}}),
    ), patch(
        "app.services.structured_comparison_service.search_web", new=slow_search_web,
    ), patch(
        "app.services.openai_service.extract_specs_targeted", new=fake_extract_targeted,
    ):
        svc = get_comparison_service()
        product_info = {
            "brand": "Samsung",
            "name": "Galaxy S25 Ultra",
            "variant": None,
            "category": "electronics",
            "search_query": "Samsung Galaxy S25 Ultra",
        }

        start = asyncio.get_event_loop().time()
        result = await svc._fetch_product_data(
            product_info, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Must complete despite slow fallback - within 3.5s (3s cap + buffer)
        assert elapsed < 3.5, f"Smart-fallback did not respect 3s cap (took {elapsed:.2f}s)"

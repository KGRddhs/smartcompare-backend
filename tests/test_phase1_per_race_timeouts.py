"""L2.6 — Tests for per-race wait_for caps on Phase 1.

Verifies the parallel topology in `_fetch_product_data` bounds each race
independently so one slow tier can't drag the whole comparison over the
STREAM_HARD_CAP_SECONDS budget. On timeout the race result is None;
downstream `_validate_renderable` decides whether to surface INSUFFICIENT_DATA.
"""

import asyncio
import os
import time

# Provide dummy env so module-level singleton clients init cleanly under test.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_one_slow_race_does_not_drag_others():
    """If `_get_price` hangs for 60s and the price-race timeout is 18s,
    the gather wall must be bounded by the timeout — the other races
    return their results normally."""
    from app.services.structured_comparison_service import get_comparison_service

    svc = get_comparison_service()

    async def slow_price(*_args, **_kwargs):
        await asyncio.sleep(60)  # would exceed Phase 1 budget
        return {"amount": 999.0, "currency": "BHD", "retailer": "stub"}

    async def fast_specs(*_args, **_kwargs):
        return {"spec_field": "fast value"}

    async def fast_reviews(*_args, **_kwargs):
        return {"common_praises": ["good"], "common_complaints": []}

    async def fast_image(*_args, **_kwargs):
        return "https://example.com/img.png"

    async def fast_search(*_args, **_kwargs):
        return {"organic": [], "shopping": []}

    with patch.object(svc, "_get_price", side_effect=slow_price), \
         patch.object(svc, "_get_specs", side_effect=fast_specs), \
         patch.object(svc, "_get_reviews", side_effect=fast_reviews), \
         patch(
             "app.services.structured_comparison_service.get_product_image_url",
             side_effect=fast_image,
         ), \
         patch(
             "app.services.structured_comparison_service.search_web",
             side_effect=fast_search,
         ):
        start = time.perf_counter()
        product = {
            "brand": "TestBrand",
            "name": "TestModel",
            "variant": None,
            "category": "electronics",
            "search_query": "TestBrand TestModel",
        }
        result = await svc._fetch_product_data(
            product, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = time.perf_counter() - start

        # Per-race price timeout is 18s; whole gather should land ~18s
        # (slowest race) + small overhead, NOT 60s.
        assert elapsed < 22.0, (
            f"gather wall {elapsed:.1f}s — per-race timeout did not fire"
        )

        # Slow race -> None; remaining fields populated by their (mocked) races.
        # We assert the timeout-fired path explicitly + that the other races
        # are not None (so the gather did not abandon them).
        assert result["price"] is None
        assert result["specs"] is not None
        assert result["reviews"] is not None
        assert result["image_url"] is not None


@pytest.mark.asyncio
async def test_per_race_timeouts_constants_are_defined_and_sane():
    """Documentation invariant: the timeout map must exist with reasonable
    values that respect STREAM_HARD_CAP_SECONDS=25s envelope."""
    # The map is local to `_fetch_product_data`; we verify via inspecting
    # source rather than importing, since constants are intentionally
    # method-scoped (rebound per request future-proofs runtime tuning).
    import inspect

    from app.services.structured_comparison_service import StructuredComparisonService

    source = inspect.getsource(StructuredComparisonService._fetch_product_data)
    assert "_PHASE1_TIMEOUTS" in source, "per-race timeout map missing"
    # I5.7 (Decision D pre-authorized): price cap tightened 18.0 -> 15.0.
    assert "\"price\": 15.0" in source or "'price': 15.0" in source
    assert "asyncio.wait_for" in source, (
        "races must be wrapped in asyncio.wait_for"
    )


@pytest.mark.asyncio
async def test_all_fast_races_complete_in_parallel():
    """When every race is fast, the gather wall is approximately the slowest
    race — proves we're parallel (not sequential)."""
    from app.services.structured_comparison_service import get_comparison_service

    svc = get_comparison_service()

    async def race_500ms(*_args, **_kwargs):
        await asyncio.sleep(0.5)
        return {"data": "ok"}

    async def fast_image(*_args, **_kwargs):
        await asyncio.sleep(0.5)
        return "https://example.com/img.png"

    async def fast_search(*_args, **_kwargs):
        return {"organic": [], "shopping": []}

    with patch.object(svc, "_get_price", side_effect=race_500ms), \
         patch.object(svc, "_get_specs", side_effect=race_500ms), \
         patch.object(svc, "_get_reviews", side_effect=race_500ms), \
         patch(
             "app.services.structured_comparison_service.get_product_image_url",
             side_effect=fast_image,
         ), \
         patch(
             "app.services.structured_comparison_service.search_web",
             side_effect=fast_search,
         ):
        start = time.perf_counter()
        product = {
            "brand": "B", "name": "N", "variant": None,
            "category": "electronics", "search_query": "B N",
        }
        await svc._fetch_product_data(
            product, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = time.perf_counter() - start

        # 4 parallel 500ms races -> wall ~0.5-1.5s, NOT 2s+ (serial sum)
        assert elapsed < 2.0, f"gather wall {elapsed:.1f}s — races appear serialized"

"""L5.3 (Bundle B S3) — lever-1 orphaned price task on cancel.

I5.6 lever-1 (structured_comparison_service.py ~2207) starts the price fetch
SPECULATIVELY via `asyncio.ensure_future(asyncio.wait_for(self._get_price(...)))`
so it overlaps the unified Serper search. It is later awaited inside the Phase-1
`asyncio.gather`. But between the `ensure_future` kickoff and the gather there are
`await` points (the unified `search_web` at ~2225, and the supplements
`find_matching_drugs` at ~2246). If the enclosing `_fetch_product_data` coroutine
is CANCELLED or any of those awaits RAISES before the gather is reached, the
speculative `_price_task` is left ORPHANED — an independent Task that keeps its
scrapers (Firecrawl / Scrape.do / curl) burning in the background, never awaited,
never cancelled. The S2 leak ledger §7 carried this as "lever-1 orphaned price
task on cancelled gather."

Lever-2 (the profile task) already guards this with a bound-to-None + cancel-in-
outer-handler pattern; lever-1 had no cleanup. These tests pin the cleanup
contract on BOTH the raise-in-window path and the external-cancel path.
"""
import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import patch, AsyncMock

from app.services.structured_comparison_service import StructuredComparisonService


_PRODUCT = {
    "brand": "Carrier", "name": "1.5T AC", "variant": None,
    "category": "electronics", "search_query": "Carrier 1.5T AC",
}


def _common_patches(svc, price_side_effect):
    """Patch the non-price siblings to no-op so only the price task's lifecycle
    is under test. The unified search is patched per-test (it's the trigger)."""
    return [
        patch("app.services.structured_comparison_service.search_product_prices",
              new=AsyncMock(return_value={"shopping": [], "organic": []})),
        patch("app.services.structured_comparison_service.get_cached", return_value=None),
        patch("app.services.structured_comparison_service.get_product_image_url",
              new=AsyncMock(return_value=None)),
        patch.object(svc, "_get_specs", new=AsyncMock(return_value={})),
        patch.object(svc, "_get_reviews", new=AsyncMock(return_value={})),
        patch.object(svc, "_get_price", new=AsyncMock(side_effect=price_side_effect)),
    ]


@pytest.mark.asyncio
async def test_lever1_price_task_cancelled_when_unified_search_raises():
    """If the unified search raises AFTER the speculative price task started, the
    price task must be cancelled — not orphaned to keep scraping in background.

    Proof: the price coroutine sleeps long; if it is allowed to run to completion
    it sets `state['completed']`. The cleanup must interrupt it with
    CancelledError instead, setting `state['cancelled']`.
    """
    svc = StructuredComparisonService()
    state = {"started": False, "completed": False, "cancelled": False}

    async def slow_price(*_a, **_k):
        state["started"] = True
        try:
            await asyncio.sleep(30)  # long enough that completion only happens if orphaned
            state["completed"] = True
            return {"amount": 100, "currency": "BHD", "source_method": "local_bhd"}
        except asyncio.CancelledError:
            state["cancelled"] = True
            raise

    async def raising_unified(*_a, **_k):
        # Yield once so the speculative price task actually starts before we blow up.
        await asyncio.sleep(0)
        raise RuntimeError("unified search boom")

    patches = _common_patches(svc, slow_price)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
         patch("app.services.structured_comparison_service.search_web",
               new=AsyncMock(side_effect=raising_unified)):
        with pytest.raises(RuntimeError, match="unified search boom"):
            await svc._fetch_product_data(
                _PRODUCT, "bahrain", include_specs=True, include_reviews=True, nocache=True
            )

    # Give the loop a tick so any cancellation actually delivers.
    await asyncio.sleep(0.05)

    assert state["started"], "speculative price task should have started (lever-1)"
    assert state["cancelled"], (
        "lever-1 price task was ORPHANED — it must be cancelled when the unified "
        "search raises before the Phase-1 gather, not left running in background"
    )
    assert not state["completed"], (
        "orphaned price task ran to completion in the background — cleanup failed"
    )


@pytest.mark.asyncio
async def test_lever1_price_task_cancelled_when_parent_cancelled():
    """If _fetch_product_data itself is cancelled (e.g. the outer
    STREAM_HARD_CAP_SECONDS wait_for fires) while awaiting the unified search,
    the speculative price task must not survive as an orphan."""
    svc = StructuredComparisonService()
    state = {"started": False, "completed": False, "cancelled": False}

    async def slow_price(*_a, **_k):
        state["started"] = True
        try:
            await asyncio.sleep(30)
            state["completed"] = True
            return {"amount": 100, "currency": "BHD", "source_method": "local_bhd"}
        except asyncio.CancelledError:
            state["cancelled"] = True
            raise

    async def hanging_unified(*_a, **_k):
        # Never returns — parent gets cancelled while awaiting here.
        await asyncio.sleep(30)
        return {"organic": [], "shopping": []}

    patches = _common_patches(svc, slow_price)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
         patch("app.services.structured_comparison_service.search_web",
               new=AsyncMock(side_effect=hanging_unified)):
        outer = asyncio.ensure_future(svc._fetch_product_data(
            _PRODUCT, "bahrain", include_specs=True, include_reviews=True, nocache=True
        ))
        # Let the speculative price task + the hanging unified search both start.
        await asyncio.sleep(0.05)
        assert state["started"], "speculative price task should have started"
        # Simulate the outer cap cancelling the whole product fetch.
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer

    await asyncio.sleep(0.05)

    assert state["cancelled"], (
        "lever-1 price task was ORPHANED on parent cancel — it must be cancelled "
        "so its scrapers stop, not left burning in background"
    )
    assert not state["completed"], "orphaned price task completed in background"

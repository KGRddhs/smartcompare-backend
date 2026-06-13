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


# ---------------------------------------------------------------------------
# L5.3 follow-up (gate Finding 1, MEDIUM) — REAL fan_out cancel-absorption.
# ---------------------------------------------------------------------------
# The two tests above mock `_get_price` with a slow_price that re-raises
# CancelledError directly, so they NEVER enter `fan_out_price_lookup`. The
# completeness critic proved a single cancel of the price task is ABSORBED when
# the task is suspended INSIDE the Tier-1.5 fan_out race: fan_out's `as_completed`
# loop catches the CancelledError (`except asyncio.CancelledError: continue` at
# price_service.py:1221) and keeps awaiting the remaining UN-cancelled inner
# scraper tasks — so the scrapers (Firecrawl up to 30s) run to completion and
# fan_out returns NORMALLY, no cancel propagated. The orphan-burn the L5.3 fix
# targets PERSISTS in the most expensive window.
#
# These tests exercise the REAL fan_out_price_lookup (no _get_price mock). The
# fix must distinguish an OUTER/parent cancel (cancel remaining scrapers +
# re-raise) from an individual-scraper CancelledError (the confirmation-cancel
# path, where `continue` is correct).


def _tracking_scraper(name, delay, state, value=100, rank=50):
    """A scraper that records whether it ran to COMPLETION or was CANCELLED."""
    async def _scraper(_product):
        try:
            await asyncio.sleep(delay)
            state[f"{name}_completed"] = True
            return {
                "value": value,
                "raw_data": {"amount": value, "currency": "BHD"},
                "source_method": "firecrawl",
                "rank": rank,
                "retailer": f"{name}.com",
            }
        except asyncio.CancelledError:
            state[f"{name}_cancelled"] = True
            raise
    return _scraper


@pytest.mark.asyncio
async def test_fan_out_propagates_outer_cancel_and_stops_scrapers():
    """A parent cancel while fan_out is mid-race must STOP the scrapers and
    PROPAGATE (not be absorbed). Pre-fix: the cancel is swallowed at
    price_service.py:1221 and the scrapers run to completion."""
    from app.services.price_service import fan_out_price_lookup

    state = {}
    # Both scrapers slow enough that, absent a real cancel, they'd run full.
    scrapers = [
        _tracking_scraper("s1", 5.0, state),
        _tracking_scraper("s2", 6.0, state),
    ]

    parent = asyncio.ensure_future(fan_out_price_lookup(
        {"full_name": "Dyson V15", "brand": "Dyson"},
        scrapers=scrapers,
        scraping_mode="hard",
    ))
    # Let both scrapers start + the as_completed loop suspend at `await fut`.
    await asyncio.sleep(0.3)
    parent.cancel()

    # The cancel MUST propagate — fan_out must not swallow it and return normally.
    with pytest.raises(asyncio.CancelledError):
        await parent

    # Give the loop a tick for cancellation to deliver to the inner scrapers.
    await asyncio.sleep(0.1)

    # NEITHER scraper may run to completion — the whole point is to stop the burn.
    assert not state.get("s1_completed"), (
        "scraper s1 ran to COMPLETION despite the parent cancel — fan_out "
        "absorbed the outer cancel (orphan-burn persists)"
    )
    assert not state.get("s2_completed"), "scraper s2 ran to completion despite parent cancel"
    # Both should have been cancelled.
    assert state.get("s1_cancelled"), "scraper s1 was not cancelled on outer cancel"
    assert state.get("s2_cancelled"), "scraper s2 was not cancelled on outer cancel"


@pytest.mark.asyncio
async def test_fan_out_outer_cancel_settles_promptly():
    """The parent must settle ~immediately on cancel, not linger until the
    slowest scraper finishes. Pre-fix it lingered ~5s (until s1's full delay)."""
    from app.services.price_service import fan_out_price_lookup
    import time as _time

    state = {}
    scrapers = [
        _tracking_scraper("a", 5.0, state),
        _tracking_scraper("b", 5.0, state),
    ]
    parent = asyncio.ensure_future(fan_out_price_lookup(
        {"full_name": "X", "brand": "X"}, scrapers=scrapers, scraping_mode="hard",
    ))
    await asyncio.sleep(0.3)
    t0 = _time.perf_counter()
    parent.cancel()
    with pytest.raises(asyncio.CancelledError):
        await parent
    settle = _time.perf_counter() - t0
    # Prompt = well under the 5s scraper delay. Pre-fix this was ~4.7s.
    assert settle < 1.0, (
        f"fan_out took {settle:.2f}s to settle after cancel — it lingered until "
        f"a scraper finished instead of propagating promptly"
    )


@pytest.mark.asyncio
async def test_fan_out_confirmation_cancel_still_works_after_fix():
    """REGRESSION GUARD: the fix must NOT disturb the confirmation-cancel path.
    When one scraper confirms (rank>=85), the OTHER pending scraper is cancelled
    via fan_out's own cancel block (an INNER-future cancel, cancelling()==0) —
    `continue` stays correct there, fan_out returns the winner NORMALLY (no
    propagation). This is the Bundle E Task 2.2 invariant."""
    from app.services.price_service import fan_out_price_lookup

    state = {}
    scrapers = [
        # Fast rank-90 winner confirms immediately.
        _tracking_scraper("winner", 0.05, state, value=100, rank=90),
        # Slow loser — must be cancelled by the confirmation block, NOT propagate.
        _tracking_scraper("loser", 3.0, state, value=99, rank=40),
    ]
    # No outer cancel here — fan_out runs to its natural confirmation.
    result = await fan_out_price_lookup(
        {"full_name": "X", "brand": "X"}, scrapers=scrapers, scraping_mode="hard",
    )
    # Winner landed, returned normally (no exception).
    assert result["best"] is not None
    assert result["best"]["value"] == 100
    # Loser was cancelled by the confirmation block (inner-future cancel).
    assert state.get("loser_cancelled"), "confirmation-cancel of the slow loser regressed"
    assert not state.get("loser_completed"), "slow loser ran to completion — confirmation-cancel broke"
    assert result.get("cancelled_count", 0) >= 1

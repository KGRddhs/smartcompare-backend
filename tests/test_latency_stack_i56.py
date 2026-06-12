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


# --- LEVER 2 -----------------------------------------------------------------
# The behavioral-profile + demographics fetch (for a logged-in user) must run
# CONCURRENTLY with the per-product data gather. Today both _compare_from_text_impl
# (ssc ~1363) and the streaming path (ssc ~1777) await the full product-data
# gather FIRST, THEN fetch behavior_profile + demographics in a separate gather.
# But those two fetches depend ONLY on user_id (known from the start) — they have
# zero dependency on product_data. Overlapping the profile fetch with the product
# gather shaves the smaller of (profile-fetch wall, product wall) off the request
# with zero quality change: scoring still consumes the same behavior_profile, and
# the verdict still consumes the same demographics_profile.
#
# As with lever 1, these tests measure the START GAP between the profile fetch and
# the product gather (gap≈0 = concurrent; gap≈product-delay = sequential) so the
# assertion is immune to network noise from un-mocked sibling work.

_EXPLICIT_PAIR = ("Carrier 1.5T AC", "LG 1.5T AC")


def _patch_downstream(svc, starts, product_delay):
    """Common patch set for the lever-2 start-gap tests. Records the start of the
    product-data fetch (slow) and of the behavior/demographics fetches, then lets
    the impl raise downstream (scoring/verdict un-mocked) — we only assert on the
    captured START timestamps, which land before any later crash."""

    async def slow_product(*_a, **_k):
        starts.setdefault("product", time.perf_counter())
        await asyncio.sleep(product_delay)
        # Minimal renderable shape so the dual-failure guard doesn't early-return
        # before the profile fetch line is reached.
        return {"brand": "X", "name": "Y", "specs": {"k": "v"},
                "price": {"amount": 1, "currency": "BHD"}}

    async def timed_behavior(*_a, **_k):
        starts.setdefault("behavior", time.perf_counter())
        return None

    async def timed_demographics(*_a, **_k):
        starts.setdefault("demographics", time.perf_counter())
        return None

    return [
        patch.object(svc, "_fetch_product_data", new=AsyncMock(side_effect=slow_product)),
        patch.object(svc, "_fetch_behavior_profile", new=AsyncMock(side_effect=timed_behavior)),
        patch("app.services.structured_comparison_service.get_user_demographics",
              new=AsyncMock(side_effect=timed_demographics)),
    ]


@pytest.mark.asyncio
async def test_profile_fetch_concurrent_with_product_gather_sync():
    """_compare_from_text_impl must kick off the behavior+demographics fetch
    CONCURRENTLY with the product-data gather. Pre-I5.6 lever-2: the profile fetch
    started only AFTER the product gather resolved (gap ≈ product delay).
    Post: gap ≈ 0."""
    svc = StructuredComparisonService()
    PRODUCT_DELAY = 1.0
    starts: dict = {}

    patches = _patch_downstream(svc, starts, PRODUCT_DELAY)
    try:
        with patches[0], patches[1], patches[2]:
            try:
                await svc._compare_from_text_impl(
                    "Carrier 1.5T AC vs LG 1.5T AC", "bahrain",
                    user_id="user-123", explicit_pair=_EXPLICIT_PAIR, nocache=True,
                )
            except Exception:
                # Downstream (scoring/verdict) is un-mocked and will raise after the
                # profile fetch — we only care about the captured start timestamps.
                pass
    finally:
        pass

    assert "product" in starts, "product gather must run"
    assert "behavior" in starts and "demographics" in starts, "profile fetch must run"
    gap = max(abs(starts["behavior"] - starts["product"]),
              abs(starts["demographics"] - starts["product"]))
    assert gap < 0.3, (
        f"profile fetch started {gap:.2f}s after the product gather — they ran "
        f"SEQUENTIALLY (gap ≈ product delay {PRODUCT_DELAY}s); I5.6 lever-2 requires "
        f"the behavior+demographics fetch to start concurrently (gap ≈ 0)"
    )


@pytest.mark.asyncio
async def test_profile_fetch_concurrent_with_product_gather_streaming():
    """Streaming path: the behavior+demographics fetch must overlap the product
    gather exactly like the sync path. Same START-GAP proof."""
    svc = StructuredComparisonService()
    PRODUCT_DELAY = 1.0
    starts: dict = {}

    patches = _patch_downstream(svc, starts, PRODUCT_DELAY)
    with patches[0], patches[1], patches[2]:
        try:
            async for _ev, _payload in svc.compare_from_text_streaming(
                "Carrier 1.5T AC vs LG 1.5T AC", "bahrain",
                user_id="user-123", explicit_pair=_EXPLICIT_PAIR, nocache=True,
            ):
                # Stop once the profile fetch has been observed — no need to drive
                # the stream through scoring/verdict.
                if "behavior" in starts and "demographics" in starts:
                    break
        except Exception:
            pass

    assert "product" in starts, "product gather must run"
    assert "behavior" in starts and "demographics" in starts, "profile fetch must run"
    gap = max(abs(starts["behavior"] - starts["product"]),
              abs(starts["demographics"] - starts["product"]))
    assert gap < 0.3, (
        f"[stream] profile fetch started {gap:.2f}s after the product gather — "
        f"SEQUENTIAL (gap ≈ product delay {PRODUCT_DELAY}s); I5.6 lever-2 requires "
        f"concurrency (gap ≈ 0)"
    )

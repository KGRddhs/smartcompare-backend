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


# --- LEVER 3 -----------------------------------------------------------------
# The Phase-2 verified-rating race (_get_verified_rating, ssc ~2348) runs UNCAPPED
# inside the Phase-2 asyncio.gather, unlike its sibling _smart_fallback_extract
# which is wrapped in asyncio.wait_for(timeout=5.0). A slow rating cascade (cold
# Serper Tier 1→2→3 + GPT fallback) can therefore drag the whole Phase-2 wall —
# and thus the per-product _fetch_product_data wall — well past budget. Lever 3
# caps the rating race at ~4s: on timeout the race yields the benign default
# rating ({rating: None, ...}), which the existing Phase-2 result loop already
# treats as "no verified rating" and falls back to the GPT-review-aggregate path.
# Zero quality change vs the status quo (a rating that would have taken >4s is one
# the user was already waiting on; the GPT-aggregate fallback covers the gap).

_RATING_CAP_SECONDS = 4.0


@pytest.mark.asyncio
async def test_phase2_rating_race_is_capped():
    """A rating fetch that hangs far past the cap must NOT contribute its full
    delay to the Phase-2 / _fetch_product_data wall. Pre-I5.6 lever-3: the rating
    ran to completion and the wall ≈ the slow-rating delay (uncapped). Post: the
    rating is cut at the cap and falls back to the benign default (None).

    The wall ceiling is set FAR below the rating hang (so the assertion cleanly
    separates capped from uncapped) but with generous headroom above the cap,
    because this sandbox has Redis down + a depleted Serper key, so un-mocked
    sibling budget/cache calls add several seconds of `getaddrinfo` retry latency
    to the wall (documented env noise — same lever-1/2 caveat). The two facts that
    PROVE the cap fired are (1) the wall is nowhere near the 60s hang and (2) the
    slow rating's value never reached the result (benign default instead)."""
    svc = StructuredComparisonService()
    SLOW_RATING = 60.0  # uncapped, this alone would put the wall ~60s+

    async def hanging_rating(*_a, **_k):
        await asyncio.sleep(SLOW_RATING)
        return {"rating": 4.7, "review_count": 100, "rating_verified": True,
                "rating_source": {"name": "should-never-land"}}

    async def fast_specs(*_a, **_k):
        return {"display": "6.1 inch", "battery": "3000mAh"}

    async def fast_price(*_a, **_k):
        return {"amount": 100, "currency": "BHD", "source_method": "local_bhd"}

    async def fast_reviews(*_a, **_k):
        return {"review_summary": {"overall_sentiment": "positive"}}

    product = {"brand": "Carrier", "name": "1.5T AC", "variant": None,
               "category": "electronics", "search_query": "Carrier 1.5T AC"}

    with patch("app.services.structured_comparison_service.search_web", new=AsyncMock(return_value={"organic": [], "shopping": []})), \
         patch("app.services.structured_comparison_service.search_product_prices", new=AsyncMock(return_value={"shopping": [], "organic": []})), \
         patch("app.services.structured_comparison_service.get_cached", return_value=None), \
         patch("app.services.structured_comparison_service.get_product_image_url", new=AsyncMock(return_value=None)), \
         patch("app.services.structured_comparison_service.collect_retailer_ratings", return_value=[]), \
         patch.object(svc, "_get_price", new=AsyncMock(side_effect=fast_price)), \
         patch.object(svc, "_get_specs", new=AsyncMock(side_effect=fast_specs)), \
         patch.object(svc, "_get_reviews", new=AsyncMock(side_effect=fast_reviews)), \
         patch.object(svc, "_get_verified_rating", new=AsyncMock(side_effect=hanging_rating)):
        t0 = time.perf_counter()
        result = await svc._fetch_product_data(product, "bahrain", include_specs=True,
                                               include_reviews=True, nocache=True)
        wall = time.perf_counter() - t0

    # Cap fires: the wall is bounded WELL below the 60s rating hang. (Uncapped it
    # would be ~60s+; capped it's cap + sandbox network-retry noise.)
    assert wall < 30.0, (
        f"_fetch_product_data took {wall:.1f}s — the uncapped rating race "
        f"({SLOW_RATING}s) dragged the Phase-2 wall; I5.6 lever-3 requires the "
        f"rating race capped at ~{_RATING_CAP_SECONDS}s"
    )
    # The slow rating never landed → benign default (None), GPT-aggregate fallback
    # owns the rating from here (no reviews.average_rating mocked, so it stays None).
    # This is the cap's functional proof: the 4.7 the hang would have returned is
    # absent because wait_for cut it at the cap.
    assert result.get("rating") is None, (
        "a rating that blew the cap must not be applied — expected the benign "
        f"default (None), got {result.get('rating')!r}"
    )

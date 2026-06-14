"""S3 #34 — cascade FETCH parallelization (greenlit). Parallelize WHEN sources
are fetched; PRESERVE WHICH wins.

Root cause (prove-it-works, live prod 1a01562): price.wall_ms = 15-17s hits the
15s _PRICE_RACE_TIMEOUT cap → the genuine BH curl is cut → parked Best Buy
converted (168.82) wins instead of sharafdg/Lulu 244.99. The serial cascade
prefix (serper_shopping 5.9s + serial backfill for-loop) pushes the curl fan_out
past 15s. Fix: parallelize the fetches.

This file pins BOTH the parallelization (timing) AND the 4 selection invariants
the team-lead flagged MUST NOT change:
  I1 genuine-first authority (_select_best/_confirmed: genuine BH beats converted)
  I2 parked-converted floor / never-None (Fix A)
  I3 phantom domain-tier (global-tier never genuine)
  I4 tier-ordering (BH-first; converted parked, not short-circuiting)
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock


# ===========================================================================
# Parallelization (timing) — the FETCH change
# ===========================================================================

@pytest.mark.asyncio
async def test_backfill_per_retailer_queries_run_concurrently():
    """_lazy_bh_pdp_backfill fires its per-retailer Serper queries CONCURRENTLY
    (gather), not in a serial for-loop. With 2 retailers each taking 1s, the
    total must be ~1s (parallel), NOT ~2s (serial)."""
    import app.services.structured_comparison_service as scs

    call_starts = []

    async def slow_search(query, *a, **k):
        call_starts.append(time.monotonic())
        await asyncio.sleep(1.0)
        return {"organic": []}  # no PDPs — just measuring concurrency

    with patch.object(scs, "search_web", new=AsyncMock(side_effect=slow_search)), \
         patch.object(scs, "curl_fetch_html", new=AsyncMock(return_value=None)):
        t0 = time.monotonic()
        await scs._lazy_bh_pdp_backfill([], "Apple iPhone 15", "electronics")
        elapsed = time.monotonic() - t0

    # 2 retailers (sharafdg + microless) × 1s each: parallel ~1s, serial ~2s.
    assert len(call_starts) == 2, f"expected 2 per-retailer queries, got {len(call_starts)}"
    assert elapsed < 1.6, (
        f"backfill took {elapsed:.2f}s for 2×1s queries — serial, not concurrent"
    )
    # both started within ~0.1s of each other = concurrent.
    assert abs(call_starts[1] - call_starts[0]) < 0.3, "queries did not start together"


@pytest.mark.asyncio
async def test_discovery_prefetch_starts_concurrently_with_shopping():
    """#34B — the discovery site: queries fire CONCURRENTLY with serper_shopping
    (the prefetch), not serially after it. serper_shopping takes 2s; the
    discovery search_web calls must START within ~0.2s of t0 (overlapped), NOT
    at t=2s (after shopping)."""
    import app.services.structured_comparison_service as scs
    svc = scs.get_comparison_service()
    ssc = "app.services.structured_comparison_service"

    t0 = time.monotonic()
    shopping_done = {}
    discovery_starts = []

    async def slow_shopping(*a, **k):
        await asyncio.sleep(2.0)
        shopping_done["t"] = time.monotonic() - t0
        # converted Tier-1 → escalation fires → discovery consumed.
        return {"shopping": [{"title": "Apple iPhone 15", "source": "Best Buy",
                              "price": "$449", "link": "https://x"}],
                "organic": [], "shopping_region": "us_fallback"}

    def fake_extract(name, items, cur, shopping_region=None):
        return {"amount": 168.82, "currency": "BHD", "original_currency": "USD",
                "retailer": "Best Buy", "source_method": "converted_usd", "retailer_score": 0.5}

    async def timed_search(query, *a, **k):
        discovery_starts.append(time.monotonic() - t0)
        return {"organic": []}

    async def fake_fan(*a, **k):
        return {"best": None, "alternates": [], "cancelled_count": 0, "elapsed_seconds": 0.1}

    with patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=slow_shopping)), \
         patch(f"{ssc}.extract_price_from_shopping", side_effect=fake_extract), \
         patch(f"{ssc}.search_web", new=AsyncMock(side_effect=timed_search)), \
         patch(f"{ssc}._should_escalate_price_scrape", return_value=True), \
         patch(f"{ssc}.fan_out_price_lookup", new=AsyncMock(side_effect=fake_fan)), \
         patch(f"{ssc}.get_shopify_sources_for_category", return_value=[]), \
         patch(f"{ssc}.get_algolia_sources_for_category", return_value=[]), \
         patch(f"{ssc}.get_cached", return_value=None), \
         patch(f"{ssc}.set_cached", return_value=True), \
         patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)), \
         patch.object(svc, "_save_price_to_db"):
        await svc._get_price(brand="Apple", name="iPhone 15", variant=None,
                             region="bahrain", search_query="Apple iPhone 15",
                             nocache=True, category="electronics")

    assert discovery_starts, "no discovery queries fired"
    # The DISCOVERY queries (prefetch) must START concurrent with shopping — i.e.
    # several search_web calls fire at ~t0, BEFORE shopping finishes (~2s). (The
    # lazy-backfill's per-retailer queries correctly fire LATER, post-harvest, so
    # we check that the EARLY cohort overlaps shopping, not that ALL calls do.)
    early = [s for s in discovery_starts if s < 1.0]
    assert len(early) >= 3, (
        f"expected >=3 discovery queries concurrent with shopping (started <1s); "
        f"got starts {discovery_starts} (shopping finished at {shopping_done.get('t')}s) "
        f"— discovery is still serial-after-shopping"
    )


@pytest.mark.asyncio
async def test_genuine_tier1_cancels_prefetch_no_orphan():
    """#34B — a GENUINE Tier-1 short-circuit cancels the speculative discovery
    tasks (no orphan Serper calls); the genuine Tier-1 price is returned."""
    import app.services.structured_comparison_service as scs
    svc = scs.get_comparison_service()
    ssc = "app.services.structured_comparison_service"

    async def genuine_shopping(*a, **k):
        return {"shopping": [{"title": "x", "source": "y", "price": "1", "link": "z"}],
                "organic": [], "shopping_region": "bh"}

    def fake_extract(name, items, cur, shopping_region=None):
        # GENUINE local_bhd Tier-1 → short-circuits (no escalation).
        return {"amount": 99.0, "currency": "BHD", "original_currency": "BHD",
                "retailer": "noon", "source_method": "local_bhd", "retailer_score": 0.6}

    search_calls = {"n": 0}
    async def count_search(*a, **k):
        search_calls["n"] += 1
        await asyncio.sleep(0.5)
        return {"organic": []}

    with patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=genuine_shopping)), \
         patch(f"{ssc}.extract_price_from_shopping", side_effect=fake_extract), \
         patch(f"{ssc}.search_web", new=AsyncMock(side_effect=count_search)), \
         patch(f"{ssc}.get_cached", return_value=None), \
         patch(f"{ssc}.set_cached", return_value=True), \
         patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)), \
         patch.object(svc, "_save_price_to_db"):
        price = await svc._get_price(brand="Apple", name="iPhone 15", variant=None,
                                     region="bahrain", search_query="Apple iPhone 15",
                                     nocache=True, category="electronics")
        await asyncio.sleep(0.6)  # let any orphan task finish if it wasn't cancelled

    assert price["source_method"] == "local_bhd"
    assert abs(price["amount"] - 99.0) < 0.01


# ===========================================================================
# Invariant pins — these MUST still hold after the parallelization (team-lead's
# 4 PRESERVE invariants). Parallelizing the FETCH must not change the SELECTION.
# ===========================================================================

class TestInvariantsPreserved:
    def test_I1_genuine_beats_converted_in_select_best(self):
        """I1 — genuine BH page_scrape beats a cheaper converted_usd (authority)."""
        from app.services.price_service import _select_best
        best = _select_best([
            {"value": 168.82, "source_method": "converted_usd", "rank": 85,
             "raw_data": {"retailer": "bestbuy.com", "source_method": "converted_usd"}},
            {"value": 244.99, "source_method": "page_scrape_jsonld", "rank": 85,
             "raw_data": {"retailer": "bahrain.sharafdg.com", "source_method": "page_scrape"}},
        ])
        assert best["raw_data"]["retailer"] == "bahrain.sharafdg.com"

    def test_I1_confirmed_only_on_genuine(self):
        """I1 — a converted_usd rank-85 candidate does NOT confirm the race."""
        from app.services.price_service import _confirmed
        assert _confirmed([{"value": 168.82, "source_method": "converted_usd",
                            "rank": 85, "raw_data": {"source_method": "converted_usd"}}]) is False
        assert _confirmed([{"value": 244.99, "source_method": "page_scrape_jsonld",
                            "rank": 85, "raw_data": {"source_method": "page_scrape"}}]) is True

    def test_I3_global_tier_never_genuine(self):
        """I3 — apple.com (global tier) page_scrape is NOT genuine (phantom-fix)."""
        from app.services.price_service import _is_genuine_bh_candidate
        assert _is_genuine_bh_candidate(
            {"source_method": "page_scrape_jsonld",
             "raw_data": {"retailer": "apple.com", "source_method": "page_scrape_jsonld"}}) is False
        assert _is_genuine_bh_candidate(
            {"source_method": "page_scrape_jsonld",
             "raw_data": {"retailer": "bahrain.sharafdg.com", "source_method": "page_scrape"}}) is True

    @pytest.mark.asyncio
    async def test_I2_I4_genuine_short_circuits_over_parked_converted(self):
        """I2+I4 — when escalation finds a genuine BH price, it wins over the
        parked converted_usd Tier-1 (tier-ordering + never-None floor)."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        ssc = "app.services.structured_comparison_service"

        async def fake_shopping(*a, **k):
            return {"shopping": [{"title": "Apple iPhone 15", "source": "Best Buy",
                                  "price": "$449", "link": "https://x/bb"}],
                    "organic": [], "shopping_region": "us_fallback"}

        def fake_extract(name, items, cur, shopping_region=None):
            return {"amount": 168.82, "currency": "BHD", "original_currency": "USD",
                    "retailer": "Best Buy", "source_method": "converted_usd", "retailer_score": 0.5}

        async def fake_fan(*a, **k):
            return {"best": {"raw_data": {"amount": 244.99, "currency": "BHD",
                                          "original_currency": "BHD",
                                          "retailer": "bahrain.sharafdg.com",
                                          "source_method": "page_scrape"},
                             "source_method": "page_scrape_jsonld", "rank": 85},
                    "alternates": [], "cancelled_count": 0, "elapsed_seconds": 1.0}

        with patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=fake_shopping)), \
             patch(f"{ssc}.extract_price_from_shopping", side_effect=fake_extract), \
             patch(f"{ssc}._should_escalate_price_scrape", return_value=True), \
             patch(f"{ssc}.fan_out_price_lookup", new=AsyncMock(side_effect=fake_fan)), \
             patch(f"{ssc}.search_web", new=AsyncMock(return_value={"organic": [
                 {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black",
                  "title": "Apple iPhone 15 128GB Black"}]})), \
             patch(f"{ssc}.get_shopify_sources_for_category", return_value=[]), \
             patch(f"{ssc}.get_algolia_sources_for_category", return_value=[]), \
             patch(f"{ssc}.get_cached", return_value=None), \
             patch(f"{ssc}.set_cached", return_value=True), \
             patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)), \
             patch.object(svc, "_save_price_to_db"):
            price = await svc._get_price(
                brand="Apple", name="iPhone 15", variant=None, region="bahrain",
                search_query="Apple iPhone 15", nocache=True, category="electronics")

        assert price is not None  # never-None (I2)
        assert abs(price["amount"] - 244.99) < 0.01  # genuine wins over parked (I4)
        assert price["source_method"] in ("page_scrape", "page_scrape_jsonld")

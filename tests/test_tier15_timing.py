"""D2 follow-up — Tier 1.5 luxury cascade timing improvements.

Two changes verified here:
1. The 3 Serper discovery queries (official → authorized → GCC retailers)
   run in PARALLEL via asyncio.gather, not SEQUENTIAL. Saves ~2s on
   every luxury query.
2. fan_out_price_lookup is bounded at 15s by asyncio.wait_for. After
   that, the code falls through to Tier 2 GPT extraction. Bounds the
   worst-case Cloudflare-protected scrape wall (e.g. ssense.com via
   Scrape.do typically 20-25s).

Tests use real asyncio.sleep to verify wall-time behaviour, not just
the call structure — a mock pattern that "looks parallel" but actually
awaits sequentially would not catch real regressions.
"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock


LUXURY_INPUTS = {
    "brand": "Louis Vuitton",
    "name": "Neverfull MM",
    "variant": None,
    "region": "bahrain",
    "search_query": "Louis Vuitton Neverfull MM price",
    "nocache": True,
    "category": "fashion",
}


@pytest.fixture
def clean_service(monkeypatch):
    """Fresh service with cache + DB writes neutralized so the live tier
    cascade fires, not a cached path. Mirrors test_fan_out_integration.py."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )

    service = scs_mod.get_comparison_service()
    service._save_price_to_db = MagicMock()
    return service


def _stub_tier1_empty(monkeypatch):
    """Force Tier 1 (Serper Shopping) to return nothing → flow proceeds to Tier 1.5."""
    monkeypatch.setattr(
        "app.services.structured_comparison_service.search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": []}),
    )
    monkeypatch.setattr(
        "app.services.structured_comparison_service.extract_price_from_shopping",
        lambda *a, **kw: None,
    )


def _stub_tier2_fallback(monkeypatch):
    """Stub the Tier 2 fall-through so any timeout/empty Tier 1.5 lands
    on a real-looking price instead of a hang or empty result."""
    monkeypatch.setattr(
        "app.services.structured_comparison_service.extract_price_from_organic",
        AsyncMock(return_value=(
            {"amount": 1500, "currency": "USD",
             "source_method": "gpt_organic_extract"},
            {"prompt_tokens": 100, "completion_tokens": 50},
        )),
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.structured_comparison_service.extract_price_from_training_data",
        AsyncMock(return_value=(
            {"amount": 1500, "currency": "USD",
             "source_method": "gpt_training_estimate"},
            {"prompt_tokens": 50, "completion_tokens": 25},
        )),
    )


@pytest.mark.asyncio
async def test_tier15_discovery_queries_run_in_parallel(monkeypatch, clean_service):
    """The 3 discovery Serper queries (official → authorized → GCC) must
    run concurrently. Each query mocked to take 1.5s.

    Sequential (current behaviour pre-fix): 3 × 1.5s = 4.5s
    Parallel (post-fix): max(1.5s, 1.5s, 1.5s) = 1.5s
    Threshold: assert total Tier 1.5 discovery+race wall < 3s.
    """
    _stub_tier1_empty(monkeypatch)
    _stub_tier2_fallback(monkeypatch)

    async def slow_search_web(query, *args, **kwargs):
        await asyncio.sleep(1.5)
        # Return a candidate URL for any discovery query so the race
        # also has something to do (we mock fan_out to be instant
        # so race time doesn't muddle the discovery measurement).
        return {"organic": [{"link": "https://www.louisvuitton.com/x"}]}

    monkeypatch.setattr(
        "app.services.structured_comparison_service.search_web",
        slow_search_web,
    )
    monkeypatch.setattr(
        "app.services.structured_comparison_service.get_official_domain",
        lambda *a, **kw: "louisvuitton.com",
    )
    # Fan_out returns a valid result instantly so we measure DISCOVERY wall only.
    monkeypatch.setattr(
        "app.services.structured_comparison_service.fan_out_price_lookup",
        AsyncMock(return_value={
            "best": {
                "value": 2000,
                "source_method": "firecrawl_brand_domain",
                "rank": 95,
                "raw_data": {"amount": 2000, "currency": "BHD", "retailer": "lv"},
            },
            "alternates": [],
            "cancelled_count": 0,
            "elapsed_seconds": 0.05,
        }),
    )

    start = time.perf_counter()
    result = await clean_service._get_price(**LUXURY_INPUTS)
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0, (
        f"Tier 1.5 discovery queries appear to run SEQUENTIALLY "
        f"(took {elapsed:.2f}s, expected <3s for parallel). "
        f"Each Serper query mocked at 1.5s — sequential is ~4.5s, "
        f"parallel is ~1.5s. Discovery refactor not effective."
    )
    # Sanity: result must still be the fan_out winner, not a Tier 2 fallback.
    assert result.get("source_method") == "firecrawl_brand_domain", (
        f"Expected fan_out winner (firecrawl_brand_domain) but got "
        f"{result.get('source_method')!r} — discovery returned no URLs, "
        f"race didn't run, fell through to Tier 2 incorrectly."
    )


@pytest.mark.asyncio
async def test_tier15_race_bounded_at_15s(monkeypatch, clean_service):
    """fan_out_price_lookup must be bounded by asyncio.wait_for(timeout=15s).
    If scrapers hang past 15s, _get_price falls through to Tier 2 GPT
    extraction instead of waiting indefinitely.

    Real-world failure mode: ssense.com / Cloudflare-protected sites
    sometimes have Scrape.do races taking 20+s, blowing the per-product
    wall budget. The 15s cap forces fall-through to Tier 2 organic
    extraction — quality trade-off (lose real scrape, gain GPT estimate)
    that the user explicitly opted into for wall-time predictability.
    """
    _stub_tier1_empty(monkeypatch)
    _stub_tier2_fallback(monkeypatch)

    monkeypatch.setattr(
        "app.services.structured_comparison_service.search_web",
        AsyncMock(return_value={
            "organic": [{"link": "https://www.louisvuitton.com/x"}],
        }),
    )
    monkeypatch.setattr(
        "app.services.structured_comparison_service.get_official_domain",
        lambda *a, **kw: "louisvuitton.com",
    )

    async def hanging_fan_out(*args, **kwargs):
        # Simulate a Cloudflare-protected scrape race that never completes.
        await asyncio.sleep(30.0)
        return {"best": None, "alternates": [],
                "cancelled_count": 0, "elapsed_seconds": 30.0}

    monkeypatch.setattr(
        "app.services.structured_comparison_service.fan_out_price_lookup",
        hanging_fan_out,
    )

    start = time.perf_counter()
    result = await clean_service._get_price(**LUXURY_INPUTS)
    elapsed = time.perf_counter() - start

    # 15s race cap + ~1s discovery + ~2s Tier 2 = should land well under 20s.
    assert elapsed < 20.0, (
        f"fan_out_price_lookup not bounded by asyncio.wait_for(timeout=15s) "
        f"(took {elapsed:.2f}s, expected <20s). Hanging scrapers would block "
        f"cold-cache luxury queries past the user's 25s wall-time budget."
    )
    # Sanity: result must be a non-Tier-1.5 fallback — Tier 2 (`local_bhd` /
    # `converted_usd` for GPT-extract from organic), Tier 3
    # (`gpt_training_estimate`), or the original Tier 2 markers
    # (`gpt_organic_extract`). Anything but a scraper source_method
    # (`firecrawl_*`, `page_scrape_jsonld`, `scrapedo_rendered`) is fine.
    SCRAPE_METHODS = {
        "firecrawl_brand_domain", "firecrawl_authorized_retailer",
        "firecrawl_gcc_retailer", "firecrawl",
        "page_scrape_jsonld", "page_scrape", "page_scrape_rendered",
        "scrapedo_rendered",
        "confirmed_multi_source",
    }
    sm = result.get("source_method")
    assert sm not in SCRAPE_METHODS, (
        f"Expected fall-through to Tier 2/3 after fan_out timeout, "
        f"but got a scraper source_method={sm!r}. The 15s wait_for didn't "
        f"actually cancel the hanging fan_out call. Result: {result}"
    )
    amount = result.get("amount") or 0
    assert amount > 0, (
        f"Fall-through returned empty/zero amount after fan_out timeout. "
        f"Result: {result}"
    )

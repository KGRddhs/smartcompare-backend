"""WS2 (genuine-bh-latency bundle) — price-path latency-trim unit tests.

The trace (TASK 0) proved the ~6s serper_shopping sub-stage dominates price_ms,
and for Shopify/Algolia categories the genuine BH price comes from the FREE
direct sources that previously ran SERIAL after shopping. WS2 fires those free
fetches speculatively, OVERLAPPED with the shopping wait, then CONSUMES (not
re-fires) them in the escalation block.

These tests pin the predicates that gate / drive that overlap — NO live calls,
NO timing assertions (timing is QA-measured):
  - the speculative-direct GATE (which categories trigger it).
  - the consume-not-refire invariant (the prefetched task is awaited, the inline
    fetch is NOT re-issued — so we don't double-spend the free fetch).
"""
import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import patch, AsyncMock

from app.services.source_router import (
    get_shopify_sources_for_category,
    get_algolia_sources_for_category,
)


class TestSpeculativeDirectGate:
    """The prefetch fires only when the category has a FREE genuine-BH direct
    source (Shopify or Algolia) — the categories where overlapping the free
    fetch with the 6s shopping wait actually saves wall. Electronics (no direct
    source, uses the Serper discovery prefetch instead) must NOT trigger it."""

    def test_fragrances_has_shopify_source(self):
        # asgharali (fragrances) is the registry Shopify row that makes the
        # speculative direct prefetch eligible for fragrances.
        assert len(get_shopify_sources_for_category("fragrances")) >= 1

    def test_electronics_not_driven_by_speculative_direct(self):
        # Electronics has no bahrain-tier Algolia source; its genuine path is the
        # Serper discovery prefetch, not the free-direct prefetch. (It may have a
        # Shopify row — almoayyed — but the point is the gate is registry-driven,
        # not hard-coded.)
        assert get_algolia_sources_for_category("electronics") == []

    def test_unknown_category_returns_empty(self):
        assert get_shopify_sources_for_category("nonexistent_cat") == []
        assert get_algolia_sources_for_category("nonexistent_cat") == []

    def test_getters_never_raise(self):
        for cat in ("fragrances", "fashion", "electronics", "supplements",
                    "skincare", "haircare", "makeup", "grocery", "other"):
            assert isinstance(get_shopify_sources_for_category(cat), list)
            assert isinstance(get_algolia_sources_for_category(cat), list)


class _FakeSource:
    def __init__(self, domain):
        self.domain = domain


@pytest.mark.asyncio
async def test_prefetched_shopify_consumed_not_refired(monkeypatch):
    """The consume-not-refire invariant: when a category has a Shopify source,
    _get_price fires ONE speculative fetch_shopify_price (the prefetch) and the
    escalation block CONSUMES it — it must not issue a SECOND inline fetch for
    the same domain. Pins that the overlap doesn't double-spend the free fetch.

    Drives the real _get_price with the heavy collaborators stubbed so it reaches
    the Shopify-direct block and the prefetch path is exercised. fetch_shopify_price
    returns an OFFICIAL-domain genuine hit so the block short-circuits cleanly.
    """
    from app.services import structured_comparison_service as scs

    svc = scs.get_comparison_service()

    shopify_calls = {"n": 0}

    async def _fake_shopify(domain, full_name, currency):
        shopify_calls["n"] += 1
        # Genuine BH hit on the OFFICIAL domain → short-circuits the block.
        return {
            "amount": 80.0, "currency": "BHD", "retailer": domain,
            "source_method": "shopify_json",
            "url": f"https://{domain}/products/x",
        }

    # Force the path: validation passes, caches miss, shopping empty (so the
    # parked-converted path is skipped), escalation FIRES, one Shopify source,
    # and that source IS the official domain (so the hit short-circuits).
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True)
    monkeypatch.setattr(scs, "fetch_shopify_price", _fake_shopify)
    monkeypatch.setattr(
        scs, "get_shopify_sources_for_category",
        lambda cat: [_FakeSource("asgharali.com")],
    )
    monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs, "get_official_domain", lambda name: "asgharali.com")
    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)

    async def _empty_shopping(*a, **k):
        return {"shopping": [], "organic": [], "shopping_region": "us_fallback"}
    monkeypatch.setattr(scs, "search_product_prices", _empty_shopping)
    # extract_price_from_shopping over empty items → None (no parked converted).
    monkeypatch.setattr(scs, "extract_price_from_shopping", lambda *a, **k: None)

    # DB read + cache write + persistence are no-ops (no network).
    async def _no_db_price(*a, **k):
        return None
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _no_db_price
    )
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None)
    # source-weight / metric helpers — keep them inert.
    monkeypatch.setattr(scs, "score_source", lambda *a, **k: 1.5)
    monkeypatch.setattr(scs, "record_tier15_attempt", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_tier15_hit", lambda *a, **k: None)

    result = await svc._get_price(
        brand="Asghar Ali", name="Oud", variant=None, region="bahrain",
        search_query="Asghar Ali Oud", nocache=True, category="fragrances",
    )

    assert result is not None
    assert result.get("amount") == 80.0
    # Exactly ONE Shopify fetch — the speculative prefetch, consumed (not refired).
    assert shopify_calls["n"] == 1, (
        f"expected 1 Shopify fetch (prefetch consumed), got {shopify_calls['n']} "
        "— the overlap double-spent the free fetch"
    )


@pytest.mark.asyncio
async def test_no_speculative_prefetch_for_no_source_category(monkeypatch):
    """A category with NO Shopify/Algolia source must not create the speculative
    direct prefetch (so the cancel path has nothing to clean up). Verified via
    fetch_shopify_price never being called when sources are empty."""
    from app.services import structured_comparison_service as scs

    svc = scs.get_comparison_service()
    shopify_calls = {"n": 0}

    async def _fake_shopify(*a, **k):
        shopify_calls["n"] += 1
        return None

    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True)
    monkeypatch.setattr(scs, "fetch_shopify_price", _fake_shopify)
    monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: False)

    async def _empty_shopping(*a, **k):
        return {"shopping": [], "organic": [], "shopping_region": "us_fallback"}
    monkeypatch.setattr(scs, "search_product_prices", _empty_shopping)
    monkeypatch.setattr(scs, "extract_price_from_shopping", lambda *a, **k: None)

    async def _no_db_price(*a, **k):
        return None
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _no_db_price
    )
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None)

    # Stub the GPT Tier-3 estimate so the no-escalation fall-through returns
    # cleanly without a live OpenAI call.
    async def _fake_estimate(*a, **k):
        return {"amount": 50.0, "currency": "BHD", "estimated": True,
                "source_method": "estimated"}
    monkeypatch.setattr(svc, "_estimate_price_with_gpt", _fake_estimate, raising=False)

    await svc._get_price(
        brand="Generic", name="Thing", variant=None, region="bahrain",
        search_query="Generic Thing", nocache=True, category="other",
    )
    assert shopify_calls["n"] == 0

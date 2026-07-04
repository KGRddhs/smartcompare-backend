"""F1.4 — Tier 1.5 routing path recorded for source_trace.

When a registry/legacy candidate wins the fan_out price race, `_get_price`
records `{route, source_weight}` in `self._tier15_routes[full_name]`. The
Phase-1 source_trace builder in `_fetch_product_data` then annotates the
`price` race entry with those fields.

This suite drives `_get_price` end-to-end (fan_out stubbed to a registry
winner) and asserts the routing record; the build-time round-trip of the
annotated trace shape is covered in test_source_trace_observability.py.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def clean_service(monkeypatch):
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


def _force_escalation(monkeypatch):
    """Tier 1 empty so the Tier 1.5 escalation cascade runs."""
    from app.services import structured_comparison_service as scs_mod
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": []}),
    )
    monkeypatch.setattr(
        scs_mod, "extract_price_from_shopping", lambda *a, **kw: None,
    )


@pytest.mark.asyncio
async def test_registry_winner_records_route(monkeypatch, clean_service):
    """A Bahrain registry candidate (bahrain.sharafdg.com) winning the fan_out
    race records route='registry' + source_weight=3.0 in _tier15_routes."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    # Isolate the fan_out registry-route path: neutralize the free genuine-BH
    # direct-fetch selectors (electronics now carries a live is_algolia sharafdg +
    # mechanism="unbxd" extra.com source — each fires a REAL network fetch that
    # returns a genuine local_bhd price BEFORE the mocked fan_out, shadowing the
    # registry-winner amount this test pins).
    monkeypatch.setattr(scs_mod, "get_algolia_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs_mod, "get_unbxd_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs_mod, "get_shopify_sources_for_category", lambda cat: [])
    # Wave C C3 — the noon-BH literal fires a REAL fetch too; neutralize alike.
    monkeypatch.setattr(scs_mod, "get_noon_sources_for_category", lambda cat: [])
    # Bahrain discovery returns a registry electronics retailer.
    monkeypatch.setattr(
        scs_mod, "search_web",
        AsyncMock(return_value={
            "organic": [{"link": "https://www.bahrain.sharafdg.com/product/iphone-15"}],
        }),
    )
    # fan_out returns a winner whose retailer is the registry domain.
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={
            "best": {
                "value": 320.0,
                "source_method": "page_scrape_jsonld",
                "rank": 85,
                "raw_data": {
                    "amount": 320.0, "currency": "BHD",
                    "retailer": "bahrain.sharafdg.com",
                    "url": "https://www.bahrain.sharafdg.com/product/iphone-15",
                },
            },
            "alternates": [], "cancelled_count": 0, "elapsed_seconds": 1.0,
        }),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant=None, region="bahrain",
        search_query="Apple iPhone 15 price", nocache=True, category="electronics",
    )

    assert result.get("amount") == 320.0
    full_name = "Apple iPhone 15"
    assert full_name in clean_service._tier15_routes
    rec = clean_service._tier15_routes[full_name]
    assert rec["route"] == "registry"
    assert rec["source_weight"] == 3.0


@pytest.mark.asyncio
async def test_legacy_winner_records_legacy_route(monkeypatch, clean_service):
    """A legacy-only authorized retailer (farfetch.com) winning the race
    records route='legacy_fallback'."""
    from app.services import structured_comparison_service as scs_mod
    from app.services.source_router import SOURCE_REGISTRY

    registry_domains = {s.domain for s in SOURCE_REGISTRY}
    assert "farfetch.com" not in registry_domains  # genuinely legacy-only

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    # No bahrain-tier fashion registry source returns it; authorized query
    # surfaces farfetch (legacy AUTHORIZED_LUXURY_RETAILERS member).
    monkeypatch.setattr(
        scs_mod, "search_web",
        AsyncMock(return_value={
            "organic": [{"link": "https://www.farfetch.com/bh/bag.aspx"}],
        }),
    )
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={
            "best": {
                "value": 1500.0,
                "source_method": "firecrawl_brand_domain",
                "rank": 90,
                "raw_data": {
                    "amount": 1500.0, "currency": "BHD",
                    "retailer": "farfetch.com",
                    "url": "https://www.farfetch.com/bh/bag.aspx",
                },
            },
            "alternates": [], "cancelled_count": 0, "elapsed_seconds": 1.0,
        }),
    )

    await clean_service._get_price(
        brand="Gucci", name="Marmont Bag", variant=None, region="bahrain",
        search_query="Gucci Marmont Bag price", nocache=True, category="fashion",
    )

    rec = clean_service._tier15_routes.get("Gucci Marmont Bag")
    assert rec is not None
    assert rec["route"] == "legacy_fallback"


@pytest.mark.asyncio
async def test_no_route_recorded_when_estimated(monkeypatch, clean_service):
    """When escalation yields no scraped winner (fan_out best=None) and the
    price falls through to a GPT estimate, no Tier 1.5 route is recorded."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(
        scs_mod, "search_web",
        AsyncMock(return_value={"organic": []}),
    )
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={
            "best": None, "alternates": [], "cancelled_count": 0, "elapsed_seconds": 0.0,
        }),
    )
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=(
            {"amount": 99, "currency": "USD", "source_method": "gpt_training_estimate"},
            {},
        )),
    )

    await clean_service._get_price(
        brand="Obscure", name="Widget 9000", variant=None, region="bahrain",
        search_query="Obscure Widget 9000 price", nocache=True, category="electronics",
    )

    assert "Obscure Widget 9000" not in clean_service._tier15_routes

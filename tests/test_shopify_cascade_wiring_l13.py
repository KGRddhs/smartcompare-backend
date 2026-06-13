"""L1.3 (Bundle B S3 'Sources') — Shopify direct-discovery wired into _get_price.

When Tier 1.5 escalation fires, the cascade now hits the Bahrain Shopify
registry stores' `/products.json` DIRECTLY (free, static BHD, no Serper) BEFORE
the Serper site: discovery. A confident Shopify hit short-circuits — returning
a real `source_method="shopify_json"` price and SKIPPING the Serper discovery +
fan_out race entirely (the credit win). On a Shopify miss, the existing
Serper+fan_out path runs unchanged as the fallback.

Driven end-to-end through `_get_price` with the Shopify fetch + Serper stubbed.
Free-tier safe (no live calls).
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
async def test_shopify_hit_short_circuits_before_serper(monkeypatch, clean_service):
    """A confident Shopify /products.json hit returns the BHD price and the
    Serper site: discovery (`search_web`) is NEVER called."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)

    # Shopify discovery returns a real BHD price for the electronics store.
    shopify_price = {
        "amount": 200.0, "currency": "BHD", "retailer": "shopalmoayyed.com",
        "url": "https://shopalmoayyed.com/products/super-general-washing-machine",
        "in_stock": True, "confidence": 0.95, "estimated": False,
        "source_method": "shopify_json", "title": "Super General 20 Kg Washing Machine",
    }
    fetch_mock = AsyncMock(return_value=shopify_price)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", fetch_mock)

    # Tripwires: Serper discovery + fan_out must NOT run on a Shopify hit.
    search_web_mock = AsyncMock(return_value={"organic": []})
    fan_out_mock = AsyncMock(return_value={"best": None})
    monkeypatch.setattr(scs_mod, "search_web", search_web_mock)
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", fan_out_mock)

    result = await clean_service._get_price(
        brand="Super General", name="20 Kg Washing Machine", variant=None,
        region="bahrain", search_query="Super General washing machine price",
        nocache=True, category="electronics",
    )

    assert result is not None
    assert result["amount"] == 200.0
    assert result["currency"] == "BHD"
    assert result["source_method"] == "shopify_json"
    # The whole point: Shopify fetch was called, Serper + fan_out were skipped.
    assert fetch_mock.await_count >= 1
    search_web_mock.assert_not_called()
    fan_out_mock.assert_not_called()


@pytest.mark.asyncio
async def test_shopify_miss_falls_through_to_serper(monkeypatch, clean_service):
    """When Shopify returns None, the existing Serper + fan_out path runs."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))

    search_web_mock = AsyncMock(return_value={
        "organic": [{"link": "https://www.bahrain.sharafdg.com/product/x"}],
    })
    monkeypatch.setattr(scs_mod, "search_web", search_web_mock)
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={
            "best": {
                "value": 320.0, "source_method": "page_scrape_jsonld", "rank": 85,
                "raw_data": {
                    "amount": 320.0, "currency": "BHD",
                    "retailer": "bahrain.sharafdg.com",
                    "url": "https://www.bahrain.sharafdg.com/product/x",
                },
            },
            "alternates": [], "cancelled_count": 0, "elapsed_seconds": 1.0,
        }),
    )

    result = await clean_service._get_price(
        brand="Sony", name="WH-1000XM5", variant=None, region="bahrain",
        search_query="Sony WH-1000XM5 price", nocache=True, category="electronics",
    )

    # Fell through to the Serper/fan_out winner.
    assert result is not None
    assert result["amount"] == 320.0
    search_web_mock.assert_called()  # Serper discovery DID run on the miss


@pytest.mark.asyncio
async def test_shopify_not_called_for_category_without_shopify_source(
    monkeypatch, clean_service
):
    """A category with no bahrain-tier Shopify source (e.g. grocery today) does
    not invoke fetch_shopify_price — no wasted fetch."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    fetch_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", fetch_mock)
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={"best": None}),
    )
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 5, "currency": "BHD"}, {})),
    )

    await clean_service._get_price(
        brand="Bertolli", name="Olive Oil", variant=None, region="bahrain",
        search_query="Bertolli olive oil price", nocache=True, category="grocery",
    )
    # grocery has no is_shopify bahrain source → fetch_shopify_price never called.
    fetch_mock.assert_not_called()


@pytest.mark.asyncio
async def test_shopify_hit_records_tier15_route(monkeypatch, clean_service):
    """A Shopify short-circuit records a Tier 1.5 route so source_trace + the
    hit-rate metric see it."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(
        scs_mod, "fetch_shopify_price",
        AsyncMock(return_value={
            "amount": 17.0, "currency": "BHD", "retailer": "bh.asgharali.com",
            "url": "https://bh.asgharali.com/products/oudh-collection",
            "in_stock": True, "confidence": 0.9, "estimated": False,
            "source_method": "shopify_json", "title": "Oudh Collection 10ML",
        }),
    )
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))

    await clean_service._get_price(
        brand="Asgharali", name="Oudh Collection", variant=None, region="bahrain",
        search_query="Asgharali Oudh Collection price", nocache=True,
        category="fragrances",
    )
    rec = clean_service._tier15_routes.get("Asgharali Oudh Collection")
    assert rec is not None
    assert rec["route"] == "shopify_direct"

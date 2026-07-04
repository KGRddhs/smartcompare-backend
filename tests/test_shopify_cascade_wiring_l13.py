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
    """2026-07-02 Wave C reconcile — neutralize every direct-adapter mechanism
    selector EXCEPT the Shopify one (Shopify IS the mechanism under test in
    this file; its tests keep the real get_shopify_sources_for_category and
    mock fetch_shopify_price directly). Same idiom as
    test_bh_gcc_cascade_wiring's _quiet_other_selectors / the C3 noon
    reconcile: the LITERAL registry rows (the Wave C noon_catalog row covers
    fragrances+electronics; bahrain.sharafdg.com algolia; extra.com unbxd)
    load flag-independently and fire LIVE network fetches inside _get_price —
    a live genuine hit (e.g. Tom Ford Black Orchid ~59.38 BHD via noon)
    preempts the mocked reseller(40)-vs-official(95) authority scenario and
    leaks real network into the free-unit suite. Applied file-wide at the
    fixture so every mocked scenario here races ONLY the mocks."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    for name in (
        "get_algolia_sources_for_category",
        "get_sitemap_sources_for_category", "get_jsonapi_sources_for_category",
        "get_woo_sources_for_category", "get_salla_sources_for_category",
        "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
        "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
        "get_noon_sources_for_category",
    ):
        monkeypatch.setattr(scs_mod, name, lambda c: [])
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
    """A confident OFFICIAL Shopify /products.json hit returns the BHD price and
    the Serper discovery RESULTS are never consumed (fan_out never runs).

    S3: short-circuit ONLY when the Shopify domain IS the official/authoritative
    domain for the brand (here get_official_domain → shopalmoayyed.com).

    NOTE (2026-06-27 genuine-BH starvation fix): electronics now FIRES the
    speculative discovery prefetch concurrently with serper_shopping (electronics
    has discovery-only BH sources like gcc.luluhypermarket.com whose genuine price
    the dominant electronics query — iPhone/Samsung/Sony, with no official BH
    Shopify store — depends on). On the rare OFFICIAL-Shopify hit (Super General →
    shopalmoayyed) those speculative `search_web` calls are CANCELLED via
    `_cancel_prefetched_discovery()` before their results are used — so the budget
    cost is bounded and the SELECTION is unchanged: the official Shopify price
    still wins and the fan_out race never runs. The invariant this pins is now
    "the discovery results are not CONSUMED" (fan_out not called), not "search_web
    is never fired"."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    # S3 — the Shopify hit's domain IS the official domain → authoritative,
    # short-circuit is allowed.
    monkeypatch.setattr(scs_mod, "get_official_domain",
                        lambda *a, **kw: "shopalmoayyed.com")

    shopify_price = {
        "amount": 200.0, "currency": "BHD", "retailer": "shopalmoayyed.com",
        "url": "https://shopalmoayyed.com/products/super-general-washing-machine",
        "in_stock": True, "confidence": 0.95, "estimated": False,
        "source_method": "shopify_json", "title": "Super General 20 Kg Washing Machine",
    }
    fetch_mock = AsyncMock(return_value=shopify_price)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", fetch_mock)

    # Tripwire: the fan_out race (which CONSUMES discovery results) must NOT run on
    # an OFFICIAL Shopify hit — the short-circuit returns before it.
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
    assert fetch_mock.await_count >= 1
    # SELECTION invariant: the discovery results are never consumed — the official
    # Shopify hit short-circuits before the fan_out race.
    fan_out_mock.assert_not_called()


@pytest.mark.asyncio
async def test_shopify_RESELLER_hit_does_not_short_circuit_before_official(
    monkeypatch, clean_service
):
    """S3 — a RESELLER Shopify hit (bh.asgharali.com, with an official brand
    domain that is NOT asgharali) must NOT short-circuit: the official + ranked
    discovery/fan_out STILL runs, and the authoritative fan_out winner is
    preferred over the reseller's (lowest) price."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    # Official domain for the brand is tomford.com, NOT the asgharali reseller.
    monkeypatch.setattr(scs_mod, "get_official_domain",
                        lambda *a, **kw: "tomford.com")

    reseller_hit = {
        "amount": 40.0, "currency": "BHD", "retailer": "bh.asgharali.com",
        "url": "https://bh.asgharali.com/products/tom-ford-black-orchid",
        "in_stock": True, "confidence": 0.9, "estimated": False,
        "source_method": "shopify_json", "title": "Tom Ford Black Orchid",
    }
    monkeypatch.setattr(scs_mod, "fetch_shopify_price",
                        AsyncMock(return_value=reseller_hit))

    # Discovery surfaces the official tomford.com; fan_out returns its price.
    search_web_mock = AsyncMock(return_value={
        "organic": [{"link": "https://www.tomford.com/black-orchid.html"}],
    })
    fan_out_mock = AsyncMock(return_value={
        "best": {
            "value": 95.0, "source_method": "firecrawl_brand_domain", "rank": 90,
            "raw_data": {"amount": 95.0, "currency": "BHD",
                         "retailer": "tomford.com",
                         "url": "https://www.tomford.com/black-orchid.html"},
        },
        "alternates": [], "cancelled_count": 0, "elapsed_seconds": 1.0,
    })
    monkeypatch.setattr(scs_mod, "search_web", search_web_mock)
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", fan_out_mock)

    result = await clean_service._get_price(
        brand="Tom Ford", name="Black Orchid", variant=None, region="bahrain",
        search_query="Tom Ford Black Orchid price", nocache=True,
        category="fragrances",
    )

    # Reseller did NOT auto-win: discovery+fan_out ran, official price preferred.
    search_web_mock.assert_called()
    assert result is not None
    assert result["amount"] == 95.0  # the authoritative tomford.com price
    assert result["amount"] != 40.0  # NOT the reseller's lowest price


@pytest.mark.asyncio
async def test_shopify_reseller_hit_used_as_fallback_when_fanout_empty(
    monkeypatch, clean_service
):
    """S3 — when the discovery/fan_out yields NOTHING, the reseller Shopify hit
    is used as a fallback (a real BH price beats falling to a GPT estimate)."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)

    reseller_hit = {
        "amount": 17.0, "currency": "BHD", "retailer": "bh.asgharali.com",
        "url": "https://bh.asgharali.com/products/oudh-collection",
        "in_stock": True, "confidence": 0.9, "estimated": False,
        "source_method": "shopify_json", "title": "Oudh Collection 10ML",
    }
    monkeypatch.setattr(scs_mod, "fetch_shopify_price",
                        AsyncMock(return_value=reseller_hit))
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup",
                        AsyncMock(return_value={"best": None}))
    # No Tier-2 estimate available either.
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=(None, {})),
    )

    result = await clean_service._get_price(
        brand="Asgharali", name="Oudh Collection", variant=None, region="bahrain",
        search_query="Asgharali Oudh Collection price", nocache=True,
        category="fragrances",
    )
    assert result is not None
    assert result["amount"] == 17.0  # the reseller fallback (real BH price)
    assert result["source_method"] == "shopify_json"


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
    # S3 — asgharali is a RESELLER (official_domain=None), fan_out empty → the
    # reseller hit is used via the FALLBACK route (not the auto-win short-circuit).
    assert rec["route"] == "shopify_fallback"


@pytest.mark.asyncio
async def test_official_shopify_hit_records_shopify_direct_route(
    monkeypatch, clean_service
):
    """An OFFICIAL-domain Shopify hit records route='shopify_direct' (the
    authoritative short-circuit path)."""
    from app.services import structured_comparison_service as scs_mod

    _force_escalation(monkeypatch)
    monkeypatch.setattr(scs_mod, "get_official_domain",
                        lambda *a, **kw: "shopalmoayyed.com")
    monkeypatch.setattr(
        scs_mod, "fetch_shopify_price",
        AsyncMock(return_value={
            "amount": 200.0, "currency": "BHD", "retailer": "shopalmoayyed.com",
            "url": "https://shopalmoayyed.com/products/x",
            "in_stock": True, "confidence": 0.95, "estimated": False,
            "source_method": "shopify_json", "title": "Super General Washing Machine",
        }),
    )
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))

    await clean_service._get_price(
        brand="Super General", name="Washing Machine", variant=None, region="bahrain",
        search_query="Super General Washing Machine price", nocache=True,
        category="electronics",
    )
    rec = clean_service._tier15_routes.get("Super General Washing Machine")
    assert rec is not None
    assert rec["route"] == "shopify_direct"

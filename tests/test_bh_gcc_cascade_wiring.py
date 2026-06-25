"""Wave C — the 6 new BH/GCC adapters' cascade wiring (data-driven prefetch +
_consume_adapter_prefetch). Mirrors test_algolia_tier2_wiring's _get_price seam.

Verifies a promoted woo (and salla) row's genuine BHD price short-circuits the
escalation through the new data-driven `_new_adapter_specs` machinery, and a miss
falls through to discovery.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock

from app.services.source_router import Source


def _live(domain, mechanism, cats=("fragrances",)):
    return Source(domain, "bahrain", cats, 3.0, mechanism=mechanism, status="live")


def _quiet_other_selectors(scs, monkeypatch, keep):
    """Force every direct-fetch selector to [] except the one under test."""
    for name in (
        "get_shopify_sources_for_category", "get_algolia_sources_for_category",
        "get_sitemap_sources_for_category", "get_jsonapi_sources_for_category",
        "get_woo_sources_for_category", "get_salla_sources_for_category",
        "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
        "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
    ):
        if name != keep:
            monkeypatch.setattr(scs, name, lambda c: [])


@pytest.mark.asyncio
class TestNewAdapterCascadeWiring:
    async def test_woo_genuine_hit_short_circuits(self, monkeypatch):
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()

        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        _quiet_other_selectors(scs, monkeypatch, keep="get_woo_sources_for_category")
        monkeypatch.setattr(
            scs, "get_woo_sources_for_category",
            lambda c: [_live("ownperfumes.com", "woo_store_json")],
        )

        async def fake_woo(domain, product_name, currency="BHD"):
            return {
                "amount": 21.5, "currency": "BHD", "retailer": "ownperfumes.com",
                "url": "https://ownperfumes.com/product/x", "in_stock": True,
                "estimated": False, "source_method": "woo_store_api", "confidence": 0.9,
            }
        monkeypatch.setattr(scs, "fetch_woocommerce_store_api_price", fake_woo)

        async def boom_search(*a, **k):
            raise AssertionError("discovery reached — woo did not short-circuit")
        monkeypatch.setattr(scs, "search_web", boom_search)

        price = await svc._get_price(
            brand="Creed", name="Aventus", variant=None, region="bahrain",
            search_query="Creed Aventus", nocache=True, category="fragrances",
        )
        assert price is not None
        assert price["source_method"] == "woo_store_api"
        assert abs(price["amount"] - 21.5) < 0.01
        assert price["retailer"] == "ownperfumes.com"

    async def test_salla_converted_hit_surfaces(self, monkeypatch):
        # A converted (non-BHD) salla price still surfaces — stamped converted_usd.
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()

        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        _quiet_other_selectors(scs, monkeypatch, keep="get_salla_sources_for_category")
        monkeypatch.setattr(
            scs, "get_salla_sources_for_category",
            lambda c: [_live("perfumya.com", "salla_api")],
        )

        async def fake_salla(domain, product_name, currency="BHD"):
            return {
                "amount": 18.0, "currency": "BHD", "original_currency": "SAR",
                "retailer": "perfumya.com", "url": "https://perfumya.com/p/x",
                "in_stock": True, "estimated": False,
                "source_method": "converted_usd", "confidence": 0.85,
            }
        monkeypatch.setattr(scs, "fetch_salla_api_price", fake_salla)

        price = await svc._get_price(
            brand="Creed", name="Aventus", variant=None, region="bahrain",
            search_query="Creed Aventus", nocache=True, category="fragrances",
        )
        assert price is not None
        assert price["source_method"] == "converted_usd"
        assert price["retailer"] == "perfumya.com"

    async def test_new_adapter_miss_falls_through(self, monkeypatch):
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()

        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        _quiet_other_selectors(scs, monkeypatch, keep="get_woo_sources_for_category")
        monkeypatch.setattr(
            scs, "get_woo_sources_for_category",
            lambda c: [_live("ownperfumes.com", "woo_store_json")],
        )

        async def fake_woo_none(domain, product_name, currency="BHD"):
            return None
        monkeypatch.setattr(scs, "fetch_woocommerce_store_api_price", fake_woo_none)

        reached = {"discovery": False}
        async def marker_search(*a, **k):
            reached["discovery"] = True
            return {"organic": [], "shopping": []}
        monkeypatch.setattr(scs, "search_web", marker_search)

        await svc._get_price(
            brand="Creed", name="Aventus", variant=None, region="bahrain",
            search_query="Creed Aventus", nocache=True, category="fragrances",
        )
        assert reached["discovery"] is True

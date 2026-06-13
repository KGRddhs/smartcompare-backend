"""L1.3 part 2 (Bundle B S3 'Sources') — Shopify direct-discovery price path.

Diagnostic finding (L1_DIAGNOSTIC_bh_scrapeability.md): the major BH retailer
storefronts are JS-SPAs whose prices are NOT in static curl-fetchable HTML, so
the free Tier-1.5 curl path can't extract them. BUT Shopify-platform BH sites
(shopalmoayyed.com, bh.asgharali.com) expose a static `/products.json` catalog
with real BHD prices — readable with zero Serper + zero render credits.

`fetch_shopify_price(domain, product_name, currency)` fetches `/products.json`,
matches the product by title (reusing the price_service matching helpers), and
returns a `source_method="shopify_json"` price dict or `None`.

This suite drives the PURE matcher `_match_shopify_product(catalog, ...)` against
a recorded fixture (tests/fixtures/shopify_products_almoayyed.json) — NO network.
The network fetch (`fetch_shopify_price`) is covered with a monkeypatched
catalog fetcher so it stays free-tier (no live calls).
"""

import json
from pathlib import Path

import pytest

from app.services.price_service import (
    _match_shopify_product,
    fetch_shopify_price,
)

FIXTURE = Path(__file__).parent / "fixtures" / "shopify_products_almoayyed.json"


@pytest.fixture
def catalog():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# --- Pure matcher --------------------------------------------------------

class TestMatchShopifyProduct:
    def test_matches_exact_titled_product(self, catalog):
        """A query matching a catalog title returns its BHD price."""
        res = _match_shopify_product(
            catalog, "Super General 20 Kg Washing Machine", "BHD",
            "shopalmoayyed.com",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(200.0)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "shopify_json"
        assert res["estimated"] is False
        assert res["retailer"] == "shopalmoayyed.com"

    def test_match_builds_product_url_from_handle(self, catalog):
        """The returned URL points at the matched product handle, not a search."""
        res = _match_shopify_product(
            catalog, "Panasonic Mixer Grinder Blender 2000W", "BHD",
            "shopalmoayyed.com",
        )
        assert res is not None
        assert "shopalmoayyed.com/products/" in res["url"]
        assert res["amount"] == pytest.approx(55.0)

    def test_no_match_returns_none(self, catalog):
        """An unrelated query matches nothing → None (no false positive)."""
        res = _match_shopify_product(
            catalog, "iPhone 15 Pro Max 256GB", "BHD", "shopalmoayyed.com",
        )
        assert res is None

    def test_empty_catalog_returns_none(self):
        assert _match_shopify_product({"products": []}, "anything", "BHD", "x.com") is None

    def test_malformed_catalog_returns_none(self):
        # Missing 'products' key / wrong shape must not raise.
        assert _match_shopify_product({}, "anything", "BHD", "x.com") is None
        assert _match_shopify_product(None, "anything", "BHD", "x.com") is None

    def test_zero_or_missing_price_skipped(self):
        cat = {"products": [
            {"title": "Test Widget 5000", "handle": "test-widget-5000",
             "variants": [{"price": "0.000", "available": True}]},
        ]}
        assert _match_shopify_product(cat, "Test Widget 5000", "BHD", "x.com") is None

    def test_in_stock_reflects_variant_availability(self, catalog):
        res = _match_shopify_product(
            catalog, "Super General 20 Kg Washing Machine", "BHD", "shopalmoayyed.com",
        )
        assert res is not None
        assert "in_stock" in res


# --- Network wrapper (monkeypatched catalog) -----------------------------

class TestFetchShopifyPrice:
    @pytest.mark.asyncio
    async def test_fetch_uses_catalog_and_matches(self, monkeypatch, catalog):
        from app.services import price_service as ps

        async def fake_fetch_catalog(domain):
            assert domain == "shopalmoayyed.com"
            return catalog

        monkeypatch.setattr(ps, "_fetch_shopify_catalog", fake_fetch_catalog)
        res = await fetch_shopify_price(
            "shopalmoayyed.com", "Super General 20 Kg Washing Machine", "BHD",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(200.0)
        assert res["source_method"] == "shopify_json"

    @pytest.mark.asyncio
    async def test_fetch_none_catalog_returns_none(self, monkeypatch):
        """Catalog fetch failure (None) → graceful None, never raises."""
        from app.services import price_service as ps

        async def fake_fetch_catalog(domain):
            return None

        monkeypatch.setattr(ps, "_fetch_shopify_catalog", fake_fetch_catalog)
        res = await fetch_shopify_price("shopalmoayyed.com", "anything", "BHD")
        assert res is None

    @pytest.mark.asyncio
    async def test_fetch_no_match_returns_none(self, monkeypatch, catalog):
        from app.services import price_service as ps

        async def fake_fetch_catalog(domain):
            return catalog

        monkeypatch.setattr(ps, "_fetch_shopify_catalog", fake_fetch_catalog)
        res = await fetch_shopify_price("shopalmoayyed.com", "Unrelated XYZ 999", "BHD")
        assert res is None

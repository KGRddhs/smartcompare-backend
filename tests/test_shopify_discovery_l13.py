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
from app.services.exchange_rate_service import FALLBACK_RATES

FIXTURE = Path(__file__).parent / "fixtures" / "shopify_products_almoayyed.json"


@pytest.fixture
def catalog():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _usd_catalog():
    """A Shopify catalog whose STORE base currency is USD (the steel-arm-
    supplements.myshopify.com case found in discovery) — price 95.00 must NOT
    be stamped 95 BHD."""
    return {
        "_store_currency": "USD",
        "products": [
            {"title": "Creatine Monohydrate 300g", "handle": "creatine-mono",
             "variants": [{"price": "95.00", "available": True}]},
        ],
    }


# === M1 (gate MUST-FIX): Shopify currency verification — no blind BHD stamp ===

class TestShopifyCurrencyVerification:
    def test_usd_store_price_is_converted_not_stamped_bhd(self):
        """A USD-base store: 95.00 USD must be CONVERTED to BHD (~35.8), never
        returned as '95 BHD' (~2.65x inflation = the wrong-price hole)."""
        res = _match_shopify_product(_usd_catalog(), "Creatine Monohydrate", "BHD",
                                     "steel-arm-supplements.myshopify.com")
        assert res is not None
        assert res["currency"] == "BHD"
        expected_bhd = round(95.00 * FALLBACK_RATES["USD"], 2)
        assert res["amount"] == pytest.approx(expected_bhd, abs=0.01)
        assert res["amount"] != pytest.approx(95.0)  # NOT the raw USD number
        assert res.get("original_currency") == "USD"

    def test_unknown_store_currency_skips_hit(self):
        """When the store currency can't be determined, DO NOT stamp BHD —
        return None and let the cascade continue (Decision-F: don't fabricate)."""
        cat = {"products": [
            {"title": "Mystery Widget 5000", "handle": "w",
             "variants": [{"price": "42.00", "available": True}]},
        ]}  # no _store_currency key
        res = _match_shopify_product(cat, "Mystery Widget 5000", "BHD", "x.myshopify.com")
        assert res is None

    def test_bhd_store_keeps_price(self, catalog):
        """A BHD-base store (the fixture now declares _store_currency=BHD) keeps
        its price unchanged."""
        res = _match_shopify_product(
            catalog, "Super General 20 Kg Washing Machine", "BHD", "shopalmoayyed.com",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(200.0)
        assert res["currency"] == "BHD"


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
        cat = {"_store_currency": "BHD", "products": [
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

    # --- S5 (gate): near-miss discrimination — pins the keyword + 0.4-overlap
    # gates that the matcher's value rests on (mutation-tested: strict_title_match
    # all()->any() and 0.4->0.0 BOTH shipped green before this). These cases
    # share a number/word with a fixture product but MUST be rejected PAST
    # numbers_match — at the keyword or overlap gate.

    def test_near_miss_rejected_by_keyword_gate(self, catalog):
        """'Bosch Mixer Grinder 2000W' shares 2000W + Mixer + Grinder with the
        Panasonic Mixer (55) but is a different brand — strict_title_match must
        reject it ('bosch' absent from the title), NOT match to 55 BHD. Reaches
        PAST numbers_match (2000 IS shared)."""
        res = _match_shopify_product(
            catalog, "Bosch Mixer Grinder 2000W", "BHD", "shopalmoayyed.com",
        )
        assert res is None

    def test_near_miss_shares_number_but_rejected(self, catalog):
        """'Hoover 2000W Vacuum Cleaner Bagless' shares 2000W with the Panasonic
        Mixer but is an unrelated product — rejected (its keywords aren't a
        subset of any title). Pins that a shared NUMBER alone never matches.

        Note: the matcher's 0.4 word-overlap gate is structurally correlated with
        strict_title_match (both measure query-keywords-in-title), so a case
        that passes strict_title_match but fails ONLY the 0.4 gate can't be
        constructed from catalog-title inputs — the load-bearing discrimination
        is the strict_title_match all()-not-any() invariant, pinned above."""
        res = _match_shopify_product(
            catalog, "Hoover 2000W Vacuum Cleaner Bagless", "BHD", "shopalmoayyed.com",
        )
        assert res is None

    def test_mutation_guard_strict_title_any_would_fail(self, catalog):
        """If strict_title_match were weakened all()->any(), 'Panasonic Toaster
        Oven' (shares only 'Panasonic' with the Mixer/Food-Processor) would
        wrongly match. It MUST be rejected — pins the all()-not-any() invariant."""
        res = _match_shopify_product(
            catalog, "Panasonic Toaster Oven 25 Litre", "BHD", "shopalmoayyed.com",
        )
        assert res is None


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


# === M2 (gate MUST-FIX): negative-cache _fetch_shopify_catalog failures ===
# A failed/slow catalog fetch must NOT be re-paid on every escalating request
# (it re-cost ~5s each at full-200, eating the fan_out budget). After a failure,
# a short-TTL negative sentinel is cached → the next call returns None WITHOUT
# re-fetching.

class TestShopifyCatalogNegativeCache:
    @pytest.mark.asyncio
    async def test_failure_is_negative_cached(self, monkeypatch):
        from app.services import price_service as ps

        store = {}
        monkeypatch.setattr(ps, "get_cached", lambda k: store.get(k))
        monkeypatch.setattr(ps, "set_cached", lambda k, v, ttl=0: store.__setitem__(k, v))

        calls = {"n": 0}

        class _Resp:
            status_code = 500
            text = ""
            def json(self):
                return {}

        def _fake_curl_get(*a, **kw):
            calls["n"] += 1
            return _Resp()

        # Patch curl_cffi.requests.get used inside _fetch_shopify_catalog.
        import curl_cffi.requests as _cr
        monkeypatch.setattr(_cr, "get", _fake_curl_get)

        # First call: fetch attempted (HTTP 500 → None), failure negative-cached.
        r1 = await ps._fetch_shopify_catalog("brokenstore.example")
        assert r1 is None
        first_calls = calls["n"]
        assert first_calls >= 1

        # Second call: must NOT re-fetch (served from the negative cache).
        r2 = await ps._fetch_shopify_catalog("brokenstore.example")
        assert r2 is None
        assert calls["n"] == first_calls, (
            "negative-cache miss: catalog re-fetched after a known failure"
        )

    @pytest.mark.asyncio
    async def test_negative_sentinel_not_returned_as_catalog(self, monkeypatch):
        """The negative sentinel must read back as None (not a fake catalog)."""
        from app.services import price_service as ps

        store = {}
        monkeypatch.setattr(ps, "get_cached", lambda k: store.get(k))
        monkeypatch.setattr(ps, "set_cached", lambda k, v, ttl=0: store.__setitem__(k, v))

        class _Resp:
            status_code = 404
            text = ""
            def json(self):
                return {}

        import curl_cffi.requests as _cr
        monkeypatch.setattr(_cr, "get", lambda *a, **kw: _Resp())

        await ps._fetch_shopify_catalog("missing.example")
        # Whatever sentinel got stored, _match must treat a re-read as no catalog.
        r = await ps._fetch_shopify_catalog("missing.example")
        assert r is None

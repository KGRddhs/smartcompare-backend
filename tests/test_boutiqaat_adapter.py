"""Wave 3c (BH Source-Intelligence, 2026-06-23) — boutiqaat.com adapter.

RE-VERIFIED LIVE 2026-06-23 (Wave-3c, out-of-band curl_cffi probe): the pre-
re-verify render-only/requires_super stance was CONSERVATIVE — boutiqaat /en-bh
PDPs actually serve a GENUINE native-BHD price in PLAIN-curl-readable JSON-LD (a
flat ``@type:Product`` node with ``offers.price`` + ``offers.priceCurrency="BHD"``
+ availability). Proven across 4 product types:
  - fragrance:   Ghuyoum Alqassar 100ml EDP           → 50.430 BHD
  - lens (conf): Daily Celebrity Contact Lenses        → 10.460 BHD
  - bundle:      Mother Day Box - 4 pcs                → 43.050 BHD
  - single:      Luminizer and Moisturizer Transparent → 15.930 BHD
                 Hair Revival Kit - 3 pcs              → 38.130 BHD

PER-SKU DATA GAP (verify-or-omit): some SKUs (a few bdl/sold-out items)
server-render ONLY an Organization JSON-LD block (no Product offer). On those the
adapter returns None — an honest miss, NOT a fabricated price — and the cascade
continues to an honest pending. NOT rate-limiting (a known-good PDP re-fetches its
price cleanly back-to-back, verified live).

``fetch_boutiqaat_price(name, currency)`` resolves the PDP via the SAME Wave-2
sitemap index as bolo (Redis read, no crawl) → curl-fetches it → parses the FLAT
JSON-LD ``@type:Product`` main offer (the bolo helper ``_bolo_jsonld_main_price``
handles the non-@graph ``[data]`` case) → a genuine
``source_method="page_scrape_jsonld"`` price dict, or ``None``. Stamps the EXISTING
genuine method (no new ``_GENUINE_BH_SOURCE_METHODS`` string).

The fixtures (tests/fixtures/boutiqaat_pdp_*.html) are SLIM REAL slices of the
live PDP JSON-LD blocks. NO network in the tests.
"""

from pathlib import Path

import pytest

from app.services.price_service import (
    _bolo_jsonld_main_price,
    fetch_boutiqaat_price,
)

FX_DIR = Path(__file__).parent / "fixtures"
FX_GHUYOUM = FX_DIR / "boutiqaat_pdp_ghuyoum_edp.html"
FX_MOISTURIZER = FX_DIR / "boutiqaat_pdp_moisturizer.html"
FX_ORG_ONLY = FX_DIR / "boutiqaat_pdp_org_only_noprice.html"


@pytest.fixture
def ghuyoum_html():
    return FX_GHUYOUM.read_text(encoding="utf-8")


@pytest.fixture
def moisturizer_html():
    return FX_MOISTURIZER.read_text(encoding="utf-8")


@pytest.fixture
def org_only_html():
    return FX_ORG_ONLY.read_text(encoding="utf-8")


# --- The flat-Product JSON-LD extraction (reusing the bolo helper) -----------

class TestBoutiqaatFlatJsonld:
    def test_extracts_fragrance_genuine_bhd(self, ghuyoum_html):
        """A flat @type:Product (no @graph) → 50.430 BHD via the bolo helper's
        non-@graph [data] branch."""
        res = _bolo_jsonld_main_price(
            ghuyoum_html, "Ghuyoum Alqassar Eau de Parfum 100ml", "BHD",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(50.43)
        assert res["currency"] == "BHD"
        assert res["in_stock"] is True

    def test_extracts_single_beauty_genuine_bhd(self, moisturizer_html):
        res = _bolo_jsonld_main_price(
            moisturizer_html, "Luminizer and Moisturizer Transparent", "BHD",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(15.93)
        assert res["currency"] == "BHD"

    def test_org_only_pdp_has_no_product_offer(self, org_only_html):
        """The per-SKU data gap: an Organization-only PDP yields no main offer."""
        assert _bolo_jsonld_main_price(org_only_html, "anything", "BHD") is None


# --- Network wrapper (monkeypatched resolve + fetch — NO live network) -------

class TestFetchBoutiqaatPrice:
    @pytest.mark.asyncio
    async def test_resolve_then_fetch_genuine_jsonld(self, ghuyoum_html, monkeypatch):
        """Happy path: resolve a PDP URL → curl-fetch → flat JSON-LD main price →
        genuine page_scrape_jsonld dict bound to boutiqaat.com."""
        import app.services.price_service as ps
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.boutiqaat.com/en-bh/women/ghuyoum-alqassar-100ml-edp-i-00000213650-1/p/",
        )

        async def fake_fetch(url, domain):
            return ghuyoum_html
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)

        res = await fetch_boutiqaat_price("Ghuyoum Alqassar Eau de Parfum 100ml", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(50.43)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape_jsonld"
        assert res["retailer"] == "boutiqaat.com"
        assert res["estimated"] is False
        assert res["url"].startswith("https://www.boutiqaat.com/en-bh/")

    @pytest.mark.asyncio
    async def test_resolve_passes_boutiqaat_domain(self, ghuyoum_html, monkeypatch):
        """The adapter resolves against the boutiqaat.com sitemap index — NOT bolo's
        (a per-domain dispatch invariant: a boutiqaat fetch must read the boutiqaat
        index)."""
        import app.services.price_service as ps
        seen = {}

        def fake_resolve(domain, query):
            seen["domain"] = domain
            return "https://www.boutiqaat.com/en-bh/women/x/p/"
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap", fake_resolve,
        )

        async def fake_fetch(url, domain):
            return ghuyoum_html
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)

        await fetch_boutiqaat_price("Ghuyoum Alqassar Eau de Parfum 100ml", "BHD")
        assert seen["domain"] == "boutiqaat.com"

    @pytest.mark.asyncio
    async def test_no_resolve_returns_none_not_pending(self, monkeypatch):
        """A cold/missing sitemap index (resolve → None) → None, NOT a pending dict
        (the cascade continues to an honest pending downstream)."""
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: None,
        )
        res = await fetch_boutiqaat_price("Dior Sauvage EDP 100ml", "BHD")
        assert res is None  # not a {"unavailable": True} pending dict

    @pytest.mark.asyncio
    async def test_resolve_but_fetch_empty_returns_none(self, monkeypatch):
        import app.services.price_service as ps
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.boutiqaat.com/en-bh/women/x/p/",
        )

        async def fake_fetch(url, domain):
            return None
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
        assert await fetch_boutiqaat_price("anything", "BHD") is None

    @pytest.mark.asyncio
    async def test_org_only_pdp_returns_none(self, org_only_html, monkeypatch):
        """An Organization-only PDP (per-SKU data gap) → honest None, never a
        fabricated price."""
        import app.services.price_service as ps
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.boutiqaat.com/en-bh/women/y/p/",
        )

        async def fake_fetch(url, domain):
            return org_only_html
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
        assert await fetch_boutiqaat_price("Bourjois Cloud Velvet Matte Lipstick", "BHD") is None

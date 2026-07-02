"""A5 (genuine-price KPI, 2026-07-02) — wire www.footlocker.com.bh for FASHION.

Built-but-dead recovery (the sharafdg/extra class): the Alshaya Shape-A
magento_graphql adapter is fully functional live (configs.json harvest +
productSearch return the exact fashion truth SKUs — AF1 '07 white 65 BHD inStock,
Samba OG 55 BHD inStock), but NO registry row carried mechanism="magento_graphql"
for fashion, so get_magento_gql_sources_for_category("fashion") == [] and the
adapter never fired. Three pieces pinned here:

  1. LITERAL Source row (bahrain, ("fashion","other"), 3.0, magento_graphql, BHD)
     so the fashion cascade prefetches footlocker.
  2. Shape-A PDP url = {base}/en/{urlKey} — the bare {base}/{urlKey} serves a
     ~3.4KB SPA stub (no og:title); all 6 Shape-A storefront roots 301 to /en/
     (live-verified 2026-07-02).
  3. Fashion colorway title enrichment — Shape-A names omit the colorway (it
     survives only in the urlKey tail "...-white-white") and the KPI colorway
     axis + strict_title_match REJECT a colourless title for a colour-stated
     query. BOUNDED: only recognized colour words are promoted, never an
     arbitrary slug tail.

NO network — curl_cffi.requests.get/post monkeypatched to recon-recorded
fixture payloads (tests/fixtures/bh_gcc/alshaya_footlocker_*.json).
"""
import json
import pathlib

import pytest

import app.services.magento_graphql_service as mg
from app.services.magento_graphql_service import (
    fetch_magento_graphql_price,
    _urlkey_colour_tail,
    _with_colour_tail,
)
from app.services.price_service import _selection_match, strict_title_match
from app.services.source_router import (
    get_magento_gql_sources_for_category,
    registry_tier,
    score_source,
)

FIX = pathlib.Path(__file__).parent / "fixtures" / "bh_gcc"

AF1_QUERY = "Nike Air Force 1 07 White"


def _load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class _FakeResp:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def _patch_curl(monkeypatch, *, post_resp: _FakeResp):
    """Configs GET → footlocker config fixture; graphql POST → the given payload."""
    from curl_cffi import requests as curl_requests

    def fake_get(url, *a, **k):
        if "/configs.json" in url:
            return _FakeResp(_load("alshaya_footlocker_configs.json"))
        return _FakeResp("{}", 404)

    monkeypatch.setattr(curl_requests, "get", fake_get)
    monkeypatch.setattr(curl_requests, "post", lambda *a, **k: post_resp)


@pytest.fixture(autouse=True)
def _enable_scrape(monkeypatch):
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    mg._CONFIG_CACHE.clear()
    yield
    mg._CONFIG_CACHE.clear()


# ---------------------------------------------------------------------------
# (a) Selector — the literal row routes fashion to footlocker
# ---------------------------------------------------------------------------

class TestSelectorWiring:
    def test_selector_returns_footlocker_for_fashion(self):
        srcs = get_magento_gql_sources_for_category("fashion")
        domains = [s.domain for s in srcs]
        assert "footlocker.com.bh" in domains, (
            "footlocker literal row missing — fashion magento_graphql is dead-wired"
        )
        row = next(s for s in srcs if s.domain == "footlocker.com.bh")
        assert row.tier == "bahrain"
        assert row.mechanism == "magento_graphql"
        assert row.currency == "BHD"
        assert row.categories == ("fashion", "other")

    def test_selector_scoped_out_of_unrelated_categories(self):
        # Category-bounded: footlocker never speculates on electronics/fragrances.
        for cat in ("electronics", "fragrances", "supplements"):
            assert "footlocker.com.bh" not in [
                s.domain for s in get_magento_gql_sources_for_category(cat)
            ], cat

    def test_www_pdp_urls_score_and_tier(self):
        # The row is APEX (a "www." row can never match — _normalize_domain
        # www-strips hosts), so the real www PDP urls score 3.0 + tier bahrain.
        url = "https://www.footlocker.com.bh/en/buy-nike-air-force-1-07-mens-shoes-white-white"
        assert score_source(url, "fashion") == 3.0
        assert score_source(url, "electronics") == 0.5  # category-scoped
        assert registry_tier(url) == "bahrain"


# ---------------------------------------------------------------------------
# (b) AF1 '07 truth SKU — /en/ PDP + colour-enriched title, passes both gates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_af1_07_white_resolves_genuine_bhd_with_en_pdp_and_colour_title(monkeypatch):
    _patch_curl(monkeypatch, post_resp=_FakeResp(_load("alshaya_footlocker_af1_productsearch.json")))
    # The cascade passes the APEX row domain — the adapter re-canonicalizes to
    # its pinned www host for the config GET / PDP url / retailer stamp.
    price = await fetch_magento_graphql_price(
        "footlocker.com.bh", AF1_QUERY, resolved_category="fashion"
    )
    assert price is not None, "the real in-stock AF1 '07 white item must resolve"
    assert price["source_method"] == "magento_graphql_bhd"
    assert price["currency"] == "BHD"
    assert price["amount"] == 65.0
    assert price["in_stock"] is True
    assert price["estimated"] is False
    assert price["retailer"] == "www.footlocker.com.bh"
    # PDP must carry the /en/ locale — the bare path is a 3.4KB stub.
    assert price["url"] == (
        "https://www.footlocker.com.bh/en/buy-nike-air-force-1-07-mens-shoes-white-white"
    )
    # Colorway enriched from the urlKey tail (the name itself omits it).
    assert "White" in price["title"]
    # The stored title passes BOTH runtime gates for the truth query.
    assert strict_title_match(AF1_QUERY, price["title"], candidate_brand="Nike")
    assert _selection_match(AF1_QUERY, price["title"], "fashion", candidate_brand="Nike")


def test_bare_shape_a_name_fails_the_gate_without_enrichment():
    # The discrimination the enrichment exists for: the raw Shape-A name (no
    # colorway) is REJECTED for the colour-stated truth query.
    assert not strict_title_match(
        AF1_QUERY, "Nike Air Force 1 '07 - Men's Shoes", candidate_brand="Nike"
    )


# ---------------------------------------------------------------------------
# (c) Samba OG — passes AS-IS; a non-colour slug tail is never promoted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_samba_og_passes_as_is(monkeypatch):
    _patch_curl(monkeypatch, post_resp=_FakeResp(_load("alshaya_footlocker_samba_productsearch.json")))
    price = await fetch_magento_graphql_price(
        "www.footlocker.com.bh", "Adidas Samba OG", resolved_category="fashion"
    )
    assert price is not None
    assert price["source_method"] == "magento_graphql_bhd"
    assert price["amount"] == 55.0
    assert price["in_stock"] is True
    # urlKey ends "...-white-gum": "gum" is not a colour word, so the walk stops
    # and NOTHING is appended — the title ships exactly as listed.
    assert price["title"] == "adidas Samba OG - Unisex Shoes"
    assert price["url"] == (
        "https://www.footlocker.com.bh/en/buy-adidas-samba-og-unisex-shoes-white-gum"
    )


# ---------------------------------------------------------------------------
# (d) Both directions — the Shadow flanker never crosses the gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shadow_flanker_rejected_for_07_white_query(monkeypatch):
    # Payload carrying ONLY the Shadow item → the '07 White query must MISS.
    af1 = json.loads(_load("alshaya_footlocker_af1_productsearch.json"))
    shadow_only = {"data": {"productSearch": {
        "items": [af1["data"]["productSearch"]["items"][1]]
    }}}
    _patch_curl(monkeypatch, post_resp=_FakeResp(json.dumps(shadow_only)))
    price = await fetch_magento_graphql_price(
        "www.footlocker.com.bh", AF1_QUERY, resolved_category="fashion"
    )
    assert price is None, "Air Force 1 Shadow must never be attributed to the '07"


@pytest.mark.asyncio
async def test_07_item_rejected_for_shadow_query(monkeypatch):
    # Converse direction: a Shadow query must not take the '07 white item
    # (payload carrying ONLY the '07 → MISS, never a nearest-flanker grab).
    af1 = json.loads(_load("alshaya_footlocker_af1_productsearch.json"))
    o7_only = {"data": {"productSearch": {
        "items": [af1["data"]["productSearch"]["items"][0]]
    }}}
    _patch_curl(monkeypatch, post_resp=_FakeResp(json.dumps(o7_only)))
    price = await fetch_magento_graphql_price(
        "www.footlocker.com.bh", "Nike Air Force 1 Shadow", resolved_category="fashion"
    )
    assert price is None


# ---------------------------------------------------------------------------
# Colour-tail helpers — bounded promotion
# ---------------------------------------------------------------------------

class TestColourTailBounds:
    def test_duplicate_colour_tail_dedupes(self):
        assert _urlkey_colour_tail("buy-nike-air-force-1-07-mens-shoes-white-white") == ["white"]

    def test_trailing_run_only(self):
        # "light"/"smoke" are NOT colour words — only the trailing colour RUN is
        # promoted, in slug order.
        assert _urlkey_colour_tail(
            "buy-nike-rise-cap-light-smoke-grey-light-smoke-grey-black"
        ) == ["grey", "black"]

    def test_non_colour_tail_stops_the_walk(self):
        # "gum"/"0" end the slug → nothing promoted (a colour EARLIER in the slug
        # is not a colorway tail).
        assert _urlkey_colour_tail("buy-adidas-samba-og-unisex-shoes-white-gum") == []
        assert _urlkey_colour_tail("buy-nike-futura-cap-black-0") == []

    def test_no_colour_tail(self):
        assert _urlkey_colour_tail("buy-nike-air-force-1-07-mens-shoes") == []
        assert _urlkey_colour_tail("") == []

    def test_name_already_carrying_colour_unchanged(self):
        assert _with_colour_tail("Nike Futura Cap Black", "buy-nike-futura-cap-black") == (
            "Nike Futura Cap Black"
        )

    def test_append_when_missing(self):
        assert _with_colour_tail(
            "Nike Air Force 1 '07 - Men's Shoes",
            "buy-nike-air-force-1-07-mens-shoes-white-white",
        ) == "Nike Air Force 1 '07 - Men's Shoes White"


@pytest.mark.asyncio
async def test_enrichment_is_fashion_scoped(monkeypatch):
    # A non-fashion resolved_category never rewrites titles (colour words can be
    # product identity elsewhere — fragrances "Black Opium"). The colourless
    # query matches the bare name; the title ships UN-enriched.
    _patch_curl(monkeypatch, post_resp=_FakeResp(_load("alshaya_footlocker_af1_productsearch.json")))
    price = await fetch_magento_graphql_price(
        "www.footlocker.com.bh", "Nike Air Force 1 07", resolved_category=None
    )
    assert price is not None
    assert price["title"] == "Nike Air Force 1 '07 - Men's Shoes"

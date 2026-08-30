"""UNIT B3 — Magento/Adobe-Commerce url_key GraphQL price adapter
(ENABLE_MAGENTO_GQL_ADAPTER, default OFF).

B4 measured live 3/3: POST https://<host>/graphql with a
``products(filter:{url_key:{eq:...}})`` query returns final_price + regular_price
+ currency in one call — arenal.com 51.45/105 EUR, jomashop.com 46.99 USD,
pacoperfumerias.co.uk 42.5/89 GBP. url_key = last URL path segment minus '.html'.
On jomashop the GraphQL POST answers 200 while the HTML PDP route is
Cloudflare-403-walled, so it is wired as a FALLBACK adapter in fetch_page_price.

Pins (offline — the _post_graphql transport seam is monkeypatched, NO network):
  (a) the 3 measured responses (verbatim fixtures) -> the right converted-BHD
      price + source_method converted_usd + original_currency carried;
  (b) url_key derivation, incl. the '.html' strip / query / fragment / slash;
  (c) the url_key sent to the POST equals the derived key;
  (d) flag-OFF (default) — the adapter NEVER fires (no POST issued, None);
  (e) a non-pinned host never POSTs;
  (f) a genuine empty (total_count 0) response -> None (no fabrication);
  (g) the fetch_page_price wiring: a walled Magento host recovers via the
      side-door with the flag ON, and is byte-identical (None) with it OFF.
"""
import asyncio
import json
import os

import pytest

import app.services.magento_graphql_service as mg
import app.services.price_service as ps
from app.services.exchange_rate_service import FALLBACK_RATES

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "magento_gql_b3")


def _load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def _run(coro):
    return asyncio.run(coro)


# The three measured responses keyed by the probed url_key.
ARENAL_KEY = "gentleman-society-ambree-givenchy-eau-parfum-hombre"
JOMASHOP_KEY = "gade-ladies-icon-roses-edp-spray-1-69-oz-fragrances-7290106294011"
PACO_KEY = "calvin-klein-eternity-eau-de-parfum-100ml-spray"

ROUTES = {
    ARENAL_KEY: _load("arenal_gentleman_society_ambree_eur.json"),
    JOMASHOP_KEY: _load("jomashop_gade_icon_roses_usd.json"),
    PACO_KEY: _load("paco_calvin_klein_eternity_gbp.json"),
}


@pytest.fixture(autouse=True)
def _pagescrape_on(monkeypatch):
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)


def _bypass_plausibility(monkeypatch):
    """Isolate the adapter from the ORTHOGONAL downstream plausibility filter
    (``is_price_showable``): the fragrance-floor guard legitimately drops a
    genuine-but-low converted price (CK Eternity 100ml at 42.5 GBP -> 20.19 BHD
    reads decant-low to it), and it is separately owned + tested — so the
    'measured response -> the right price' pin bypasses it to assert extraction +
    conversion + labelling deterministically. Every other gate (strict match,
    content safety) still runs."""
    monkeypatch.setattr(mg, "is_price_showable", lambda *a, **k: True)


def _patch_router(monkeypatch, routes=ROUTES):
    """Monkeypatch the _post_graphql transport seam. Records every (url, url_key)
    call and answers from the fixture keyed by the ``urlKey`` variable."""
    calls = []

    async def fake_post(url, query, variables, headers):
        calls.append((url, variables.get("urlKey")))
        # Pin the query shape: it must be the url_key filter, variable-driven.
        assert "url_key" in query and "$urlKey" in query
        return routes.get(variables.get("urlKey"))

    monkeypatch.setattr(mg, "_post_graphql", fake_post)
    return calls


# ---------------------------------------------------------------------------
# (b) url_key derivation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("https://www.jomashop.com/foo-bar.html", "foo-bar"),
    ("https://www.arenal.com/foo-bar", "foo-bar"),  # no .html suffix
    ("https://www.pacoperfumerias.co.uk/a/b/" + PACO_KEY + ".html?x=1#frag", PACO_KEY),
    ("https://www.arenal.com/foo-bar.html/", "foo-bar"),  # trailing slash
    ("https://www.arenal.com/" + ARENAL_KEY, ARENAL_KEY),
    ("https://www.jomashop.com/", ""),  # no segment
    ("", ""),
    ("https://www.jomashop.com/UP-CASE.HTML", "UP-CASE"),  # case-insensitive strip
])
def test_url_key_derivation(url, expected):
    assert mg._url_key_from_url(url) == expected


# ---------------------------------------------------------------------------
# (a)+(c) the 3 measured responses -> the right price, and the POST carries the
#         derived url_key
# ---------------------------------------------------------------------------

def test_arenal_eur_converted(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_router(monkeypatch)
    url = "https://www.arenal.com/" + ARENAL_KEY + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(
        url, "Gentleman Society Ambree", "BHD", resolved_category="fragrances",
    ))
    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "EUR"
    assert res["currency"] == "BHD"
    assert res["amount"] == pytest.approx(round(51.45 * FALLBACK_RATES["EUR"], 3))
    assert res["url"] == url
    assert res["retailer"] == "www.arenal.com"
    assert res["estimated"] is False
    # (c) the POST carried the derived url_key against the /graphql endpoint.
    assert calls == [("https://www.arenal.com/graphql", ARENAL_KEY)]


def test_jomashop_usd_converted_walks_past_cloudflare(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_router(monkeypatch)
    name = "Ga-De Ladies Icon Roses EDP Spray 1.69 oz Fragrances 7290106294011"
    url = "https://www.jomashop.com/" + JOMASHOP_KEY + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(url, name, "BHD",
                                                  resolved_category="fragrances"))
    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "USD"
    assert res["amount"] == pytest.approx(round(46.99 * FALLBACK_RATES["USD"], 3))
    assert calls == [("https://www.jomashop.com/graphql", JOMASHOP_KEY)]


def test_paco_gbp_converted(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    _patch_router(monkeypatch)
    url = "https://www.pacoperfumerias.co.uk/" + PACO_KEY + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(
        url, "Calvin Klein Eternity Eau de Parfum 100ml Spray", "BHD",
        resolved_category="fragrances",
    ))
    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "GBP"
    assert res["amount"] == pytest.approx(round(42.5 * FALLBACK_RATES["GBP"], 3))


# ---------------------------------------------------------------------------
# (d) flag-OFF — the adapter NEVER fires
# ---------------------------------------------------------------------------

def test_flag_off_never_posts(monkeypatch):
    monkeypatch.delenv("ENABLE_MAGENTO_GQL_ADAPTER", raising=False)
    calls = _patch_router(monkeypatch)
    url = "https://www.arenal.com/" + ARENAL_KEY + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(url, "Gentleman Society Ambree", "BHD"))
    assert res is None
    assert calls == []  # no POST issued on the flag-OFF path


@pytest.mark.parametrize("val", ["false", "0", "no", "off", ""])
def test_flag_off_variants(monkeypatch, val):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", val)
    assert mg.magento_gql_adapter_enabled() is False


@pytest.mark.parametrize("val", ["true", "1", "yes", "on", "TRUE", "On"])
def test_flag_on_variants(monkeypatch, val):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", val)
    assert mg.magento_gql_adapter_enabled() is True


# ---------------------------------------------------------------------------
# (e) non-pinned host never POSTs
# ---------------------------------------------------------------------------

def test_non_pinned_host_never_posts(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    calls = _patch_router(monkeypatch)
    res = _run(mg.fetch_magento_graphql_url_price(
        "https://www.somerandomstore.com/foo-bar.html", "Foo Bar", "BHD"))
    assert res is None
    assert calls == []


# ---------------------------------------------------------------------------
# (f) genuine empty response -> None (no fabrication)
# ---------------------------------------------------------------------------

def test_empty_response_is_none(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    empty = _load("no_match_empty_control.json")
    _patch_router(monkeypatch, routes={ARENAL_KEY: empty})
    url = "https://www.arenal.com/" + ARENAL_KEY + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(url, "Gentleman Society Ambree", "BHD"))
    assert res is None


def test_transport_none_is_none(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _patch_router(monkeypatch, routes={})  # _post_graphql -> None (transport fail)
    url = "https://www.arenal.com/" + ARENAL_KEY + ".html"
    res = _run(mg.fetch_magento_graphql_url_price(url, "Gentleman Society Ambree", "BHD"))
    assert res is None


def test_wrong_product_rejected(monkeypatch):
    """A pinned host + valid url_key that returns a product whose title does not
    match the query is strict-rejected (no wrong-product ship)."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _patch_router(monkeypatch)
    url = "https://www.arenal.com/" + ARENAL_KEY + ".html"
    # Query is for a completely different fragrance than the returned node.
    res = _run(mg.fetch_magento_graphql_url_price(
        url, "Chanel Bleu de Chanel Parfum 150ml", "BHD",
        resolved_category="fragrances"))
    assert res is None


# ---------------------------------------------------------------------------
# (g) fetch_page_price wiring — walled Magento host recovers via the side-door
# ---------------------------------------------------------------------------

def test_fetch_page_price_walled_host_recovers_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_router(monkeypatch)

    async def fake_walled(url, domain):  # HTML route Cloudflare-403-walled -> None
        return None

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_walled)
    # UNIT B4 — jomashop now PREFERS the Apollo persisted-query GET side-door
    # (_try_magento_gql_url_fallback tries it first). Stub that transport seam to
    # a miss so this B3 pin deterministically exercises the POST url_key fallback
    # (and stays OFFLINE — an unpatched seam would issue a live GET). The B4 GET
    # path is covered in tests/test_jomashop_persisted_query.py.
    async def fake_pq_get(endpoint, params, headers):
        return None

    monkeypatch.setattr(mg, "_get_persisted_query", fake_pq_get)
    name = "Ga-De Ladies Icon Roses EDP Spray 1.69 oz Fragrances 7290106294011"
    url = "https://www.jomashop.com/" + JOMASHOP_KEY + ".html"
    res = _run(ps.fetch_page_price(url, name, "BHD"))
    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["amount"] == pytest.approx(round(46.99 * FALLBACK_RATES["USD"], 3))
    assert calls == [("https://www.jomashop.com/graphql", JOMASHOP_KEY)]


def test_fetch_page_price_walled_host_flag_off_is_none(monkeypatch):
    monkeypatch.delenv("ENABLE_MAGENTO_GQL_ADAPTER", raising=False)
    calls = _patch_router(monkeypatch)

    async def fake_walled(url, domain):
        return None

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_walled)
    name = "Ga-De Ladies Icon Roses EDP Spray 1.69 oz Fragrances 7290106294011"
    url = "https://www.jomashop.com/" + JOMASHOP_KEY + ".html"
    res = _run(ps.fetch_page_price(url, name, "BHD"))
    assert res is None          # byte-identical to pre-B3 (walled -> None)
    assert calls == []          # the side-door POST was never issued

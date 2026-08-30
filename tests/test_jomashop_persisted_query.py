"""UNIT B4 — jomashop Apollo persisted-query price adapter
(ENABLE_MAGENTO_GQL_ADAPTER, same gate as B3 — same platform + same url_key key +
same price_range shape; only the transport differs: a GET with an
Automatic-Persisted-Query sha256 hash vs B3's POST query body).

B9 measured the exact browser GET replays byte-for-byte under plain curl_cffi
(9,461 bytes): url_key lelas-...-8681124608130 -> 69.99 USD, and swapping ONLY the
urlKey (persisted hash untouched) -> 46.99 USD for a different product. ONE capture
serves the whole host. The persisted hash is a build artifact that WILL rotate; a
non-200 or a 200-with-no-price-key is a re-capture TRIGGER (log + None, never a
stale wrong price).

Pins (offline — the _get_persisted_query transport seam is monkeypatched, NO
network):
  (a) the measured 69.99 response -> converted-BHD + source_method converted_usd +
      original_currency USD, and the GET carried operationName=productDetail, the
      pinned sha256 hash, and variables {urlKey, onServer:true};
  (b) swap ONLY the urlKey (hash byte-identical between the two calls) -> 46.99;
  (c) rotation trigger — a 200 PersistedQueryNotFound -> None (no crash);
  (d) rotation trigger — a 200 with a productDetail item but no price key -> None
      (no crash);
  (e) flag-OFF (default) — the adapter NEVER fires (no GET issued, None);
  (f) a non-jomashop host never GETs;
  (g) an empty url_key (no path segment) never GETs;
  (h) the fetch_page_price wiring: a walled jomashop PDP recovers via the
      persisted-query side-door with the flag ON, and is byte-identical (None) with
      it OFF.
"""
import asyncio
import json
import os

import pytest

import app.services.magento_graphql_service as mg
import app.services.price_service as ps
from app.services.exchange_rate_service import FALLBACK_RATES

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "jomashop_pq_b4")


def _load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def _run(coro):
    return asyncio.run(coro)


LELAS_KEY = "lelas-unisex-oud-edp-spray-2-87-oz-fragrances-8681124608130"
GADE_KEY = "gade-ladies-icon-roses-edp-spray-1-69-oz-fragrances-7290106294011"
LELAS_NAME = "Lelas Unisex Oud EDP Spray 2.87 oz Fragrances 8681124608130"
GADE_NAME = "Ga-De Ladies Icon Roses EDP Spray 1.69 oz Fragrances 7290106294011"

ROUTES = {
    LELAS_KEY: _load("jomashop_pq_lelas_oud_usd.json"),
    GADE_KEY: _load("jomashop_pq_gade_icon_roses_usd.json"),
}


@pytest.fixture(autouse=True)
def _pagescrape_on(monkeypatch):
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)


def _bypass_plausibility(monkeypatch):
    """Isolate the adapter from the ORTHOGONAL is_price_showable filter (the
    measured Lelas capture is OUT_OF_STOCK and a low converted fragrance price),
    so the extraction+conversion+labelling pins are deterministic. Every other
    gate (strict match, content safety) still runs."""
    monkeypatch.setattr(mg, "is_price_showable", lambda *a, **k: True)


def _patch_seam(monkeypatch, routes=ROUTES):
    """Monkeypatch the _get_persisted_query transport seam. Records every
    (endpoint, params) call and answers from the fixture keyed by the ``urlKey``
    inside the JSON-encoded ``variables`` query param."""
    calls = []

    async def fake_get(endpoint, params, headers):
        calls.append((endpoint, params))
        variables = json.loads(params["variables"])
        return routes.get(variables.get("urlKey"))

    monkeypatch.setattr(mg, "_get_persisted_query", fake_get)
    return calls


def _urlkey_of(call):
    return json.loads(call[1]["variables"])["urlKey"]


def _sha256_of(call):
    return json.loads(call[1]["extensions"])["persistedQuery"]["sha256Hash"]


# ---------------------------------------------------------------------------
# (a) the measured 69.99 response -> the right price; the GET carries the
#     persisted hash + operationName + variables
# ---------------------------------------------------------------------------

def test_lelas_69_99_usd_converted(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_seam(monkeypatch)
    url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    res = _run(mg.fetch_jomashop_persisted_query_price(
        url, LELAS_NAME, "BHD", resolved_category="fragrances"))
    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "USD"
    assert res["currency"] == "BHD"
    assert res["amount"] == pytest.approx(round(69.99 * FALLBACK_RATES["USD"], 3))
    assert res["url"] == url
    assert res["retailer"] == "www.jomashop.com"
    assert res["estimated"] is False
    # exactly one GET, against /graphql, carrying the pinned request shape.
    assert len(calls) == 1
    endpoint, params = calls[0]
    assert endpoint == "https://www.jomashop.com/graphql"
    assert params["operationName"] == "productDetail"
    variables = json.loads(params["variables"])
    assert variables == {"urlKey": LELAS_KEY, "onServer": True}
    assert _sha256_of(calls[0]) == mg._JOMASHOP_PQ_SHA256


# ---------------------------------------------------------------------------
# (b) swap ONLY the urlKey (hash byte-identical) -> the other product's price
# ---------------------------------------------------------------------------

def test_urlkey_swap_hash_untouched(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_seam(monkeypatch)

    lelas_url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    gade_url = "https://www.jomashop.com/" + GADE_KEY + ".html"
    r1 = _run(mg.fetch_jomashop_persisted_query_price(
        lelas_url, LELAS_NAME, "BHD", resolved_category="fragrances"))
    r2 = _run(mg.fetch_jomashop_persisted_query_price(
        gade_url, GADE_NAME, "BHD", resolved_category="fragrances"))

    assert r1["amount"] == pytest.approx(round(69.99 * FALLBACK_RATES["USD"], 3))
    assert r2["amount"] == pytest.approx(round(46.99 * FALLBACK_RATES["USD"], 3))
    # ONLY the urlKey changed between the two GETs; the persisted hash is identical.
    assert _urlkey_of(calls[0]) == LELAS_KEY
    assert _urlkey_of(calls[1]) == GADE_KEY
    assert _sha256_of(calls[0]) == _sha256_of(calls[1]) == mg._JOMASHOP_PQ_SHA256


# ---------------------------------------------------------------------------
# (c)+(d) rotation triggers -> None, never a crash / stale price
# ---------------------------------------------------------------------------

def test_persisted_query_not_found_is_none(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    rotated = _load("jomashop_pq_persisted_query_not_found.json")
    _patch_seam(monkeypatch, routes={LELAS_KEY: rotated})
    url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    res = _run(mg.fetch_jomashop_persisted_query_price(url, LELAS_NAME, "BHD"))
    assert res is None


def test_200_with_no_price_key_is_none(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    noprice = _load("jomashop_pq_no_price_key_control.json")
    _patch_seam(monkeypatch, routes={LELAS_KEY: noprice})
    url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    res = _run(mg.fetch_jomashop_persisted_query_price(url, LELAS_NAME, "BHD"))
    assert res is None


def test_transport_non_200_is_none(monkeypatch):
    """A non-200 (or transport error) surfaces from the seam as None -> None."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _patch_seam(monkeypatch, routes={})  # seam returns None
    url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    res = _run(mg.fetch_jomashop_persisted_query_price(url, LELAS_NAME, "BHD"))
    assert res is None


def test_wrong_product_rejected(monkeypatch):
    """A valid 200 whose title does not match the query is strict-rejected."""
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    _patch_seam(monkeypatch)
    url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    res = _run(mg.fetch_jomashop_persisted_query_price(
        url, "Chanel Bleu de Chanel Parfum 150ml", "BHD",
        resolved_category="fragrances"))
    assert res is None


# ---------------------------------------------------------------------------
# (e) flag-OFF — the adapter NEVER fires
# ---------------------------------------------------------------------------

def test_flag_off_never_gets(monkeypatch):
    monkeypatch.delenv("ENABLE_MAGENTO_GQL_ADAPTER", raising=False)
    calls = _patch_seam(monkeypatch)
    url = "https://www.jomashop.com/" + LELAS_KEY + ".html"
    res = _run(mg.fetch_jomashop_persisted_query_price(url, LELAS_NAME, "BHD"))
    assert res is None
    assert calls == []  # no GET issued on the flag-OFF path


# ---------------------------------------------------------------------------
# (f) non-jomashop host never GETs
# ---------------------------------------------------------------------------

def test_non_jomashop_host_never_gets(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    calls = _patch_seam(monkeypatch)
    res = _run(mg.fetch_jomashop_persisted_query_price(
        "https://www.arenal.com/" + LELAS_KEY + ".html", LELAS_NAME, "BHD"))
    assert res is None
    assert calls == []


# ---------------------------------------------------------------------------
# (g) empty url_key never GETs
# ---------------------------------------------------------------------------

def test_empty_url_key_never_gets(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    calls = _patch_seam(monkeypatch)
    res = _run(mg.fetch_jomashop_persisted_query_price(
        "https://www.jomashop.com/", LELAS_NAME, "BHD"))
    assert res is None
    assert calls == []


# ---------------------------------------------------------------------------
# (h) fetch_page_price wiring — walled jomashop recovers via the side-door
# ---------------------------------------------------------------------------

def test_fetch_page_price_walled_jomashop_recovers_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_MAGENTO_GQL_ADAPTER", "true")
    _bypass_plausibility(monkeypatch)
    calls = _patch_seam(monkeypatch)

    async def fake_walled(url, domain):  # HTML route Cloudflare-403-walled -> None
        return None

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_walled)
    url = "https://www.jomashop.com/" + GADE_KEY + ".html"
    res = _run(ps.fetch_page_price(url, GADE_NAME, "BHD"))
    assert res is not None
    assert res["source_method"] == "converted_usd"
    assert res["amount"] == pytest.approx(round(46.99 * FALLBACK_RATES["USD"], 3))
    assert _urlkey_of(calls[0]) == GADE_KEY


def test_fetch_page_price_walled_jomashop_flag_off_is_none(monkeypatch):
    monkeypatch.delenv("ENABLE_MAGENTO_GQL_ADAPTER", raising=False)
    calls = _patch_seam(monkeypatch)

    async def fake_walled(url, domain):
        return None

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_walled)
    url = "https://www.jomashop.com/" + GADE_KEY + ".html"
    res = _run(ps.fetch_page_price(url, GADE_NAME, "BHD"))
    assert res is None          # byte-identical to pre-B4 (walled -> None)
    assert calls == []          # the side-door GET was never issued

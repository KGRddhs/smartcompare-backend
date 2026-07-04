"""Offline fixture-based unit tests for fetch_magento_graphql_price (R3b).

Covers BOTH Magento/Adobe-Commerce GraphQL shapes:
  - Shape A (Alshaya Catalog Service): GET /configs.json (flat .data[] {key,value})
    → POST productSearch → SimpleProductView / ComplexProductView (branch by
    __typename).
  - Shape B (vanilla Magento core, klinq/trikart/ajmal-kwt): POST /graphql with
    Store:<view> header → products.items[].price_range.minimum_price.final_price.

NO network — curl_cffi.requests.get/post are monkeypatched (patched where the
adapter module imports them, i.e. the curl_cffi.requests module) to return the
captured fixture bytes.

Genuine vs converted: response .currency=="BHD" → stamp "magento_graphql_bhd";
any other currency → "converted_usd" via _convert_to_bhd, original_currency set.
"""
import json
import pathlib

import pytest

import app.services.magento_graphql_service as mg
from app.services.magento_graphql_service import fetch_magento_graphql_price

FIX = pathlib.Path(__file__).parent / "fixtures" / "bh_gcc"


def _load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


class _FakeResp:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def _patch_curl(monkeypatch, *, get_map=None, post_map=None, get_resp=None, post_resp=None):
    """Patch curl_cffi.requests.get/post.

    get_map / post_map: dict keyed by a substring of the URL → _FakeResp (first
    matching substring wins). get_resp / post_resp: single fallback _FakeResp.
    """
    from curl_cffi import requests as curl_requests

    def fake_get(url, *a, **k):
        if get_map:
            for needle, resp in get_map.items():
                if needle in url:
                    return resp
        if get_resp is not None:
            return get_resp
        return _FakeResp("{}", 404)

    def fake_post(url, *a, **k):
        if post_map:
            for needle, resp in post_map.items():
                if needle in url:
                    return resp
        if post_resp is not None:
            return post_resp
        return _FakeResp("{}", 404)

    monkeypatch.setattr(curl_requests, "get", fake_get)
    monkeypatch.setattr(curl_requests, "post", fake_post)


@pytest.fixture(autouse=True)
def _enable_scrape(monkeypatch):
    # The adapter gates on ENABLE_PAGE_SCRAPE — force it on for the tests.
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    # Clear the per-domain config cache so each test starts clean.
    mg._CONFIG_CACHE.clear()
    yield
    mg._CONFIG_CACHE.clear()


# ---------------------------------------------------------------------------
# Shape A — Alshaya Catalog Service (config.json + productSearch)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shape_a_simple_product_genuine_bhd(monkeypatch):
    """bathandbodyworks.com.bh — SimpleProductView, native BHD → genuine stamp."""
    _patch_curl(
        monkeypatch,
        get_map={"/configs.json": _FakeResp(_load("alshaya_bbw_configs.json"))},
        post_map={"graphql": _FakeResp(_load("alshaya_bbw_productsearch.json"))},
    )
    price = await fetch_magento_graphql_price(
        "www.bathandbodyworks.com.bh", "Eucalyptus Body Lotion"
    )
    assert price is not None
    assert price["source_method"] == "magento_graphql_bhd"
    assert price["currency"] == "BHD"
    assert price["estimated"] is False
    assert price["amount"] == 3.25  # final.amount.value
    assert price["in_stock"] is True
    assert "original_currency" not in price  # native BHD → no conversion marker
    # url built from commerce-base-endpoint + "/en/" + urlKey (no .html) — A5:
    # Alshaya PDPs live ONLY under the /en/ locale (the bare path serves a
    # ~3.4KB SPA stub; all 6 Shape-A roots 301 to /en/, live-verified 2026-07-02).
    assert price["url"] == (
        "https://www.bathandbodyworks.com.bh/en/buy-eucalyptus-body-lotion"
    )
    assert "Eucalyptus Body Lotion" in price["title"]


@pytest.mark.asyncio
async def test_shape_a_complex_product_typename_branch(monkeypatch):
    """footlocker.com.bh — ComplexProductView → priceRange.minimum.final path."""
    _patch_curl(
        monkeypatch,
        get_map={"/configs.json": _FakeResp(_load("alshaya_bbw_configs.json"))},
        post_map={"graphql": _FakeResp(_load("alshaya_footlocker_productsearch.json"))},
    )
    price = await fetch_magento_graphql_price(
        "www.footlocker.com.bh", "Nike Rise Cap"
    )
    assert price is not None
    assert price["source_method"] == "magento_graphql_bhd"
    assert price["currency"] == "BHD"
    # Rise Cap final = 8 (on sale from 15); Complex path reads priceRange.minimum.final
    assert price["amount"] == 8.0
    assert price["in_stock"] is True


@pytest.mark.asyncio
async def test_shape_a_config_keys_read_not_hardcoded(monkeypatch):
    """The x-api-key + endpoint must come from the live /configs.json, proving
    no hardcoded credentials. Capture the headers the POST is sent with."""
    captured = {}

    from curl_cffi import requests as curl_requests

    def fake_get(url, *a, **k):
        return _FakeResp(_load("alshaya_bbw_configs.json"))

    def fake_post(url, *a, **k):
        captured["url"] = url
        captured["headers"] = k.get("headers", {})
        return _FakeResp(_load("alshaya_bbw_productsearch.json"))

    monkeypatch.setattr(curl_requests, "get", fake_get)
    monkeypatch.setattr(curl_requests, "post", fake_post)

    price = await fetch_magento_graphql_price(
        "www.bathandbodyworks.com.bh", "Eucalyptus Body Lotion"
    )
    assert price is not None
    # endpoint from config (commerce-endpoint)
    assert captured["url"] == "https://www.bathandbodyworks.com.bh/graphql"
    h = captured["headers"]
    assert h.get("x-api-key") == "7e5451cc843747958c89f1f11ecd90c8"
    assert h.get("Magento-Environment-Id") == "886a81a6-9b3e-4797-b671-7bd4f8cde3ba"
    assert h.get("Magento-Store-View-Code") == "bhr_en"
    assert h.get("Magento-Website-Code") == "bhr"
    assert h.get("Magento-Store-Code") == "bahrain_store"


@pytest.mark.asyncio
async def test_shape_a_config_fetch_fail_returns_none(monkeypatch):
    """A non-200 /configs.json → None (no config → cannot query)."""
    _patch_curl(
        monkeypatch,
        get_map={"/configs.json": _FakeResp("nope", 503)},
    )
    price = await fetch_magento_graphql_price(
        "www.bathandbodyworks.com.bh", "Eucalyptus Body Lotion"
    )
    assert price is None


# ---------------------------------------------------------------------------
# Shape B — vanilla Magento core (klinq/trikart/ajmal)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shape_b_klinq_genuine_bhd(monkeypatch):
    """klinq.com — Store:default header, native BHD, .html url suffix."""
    _patch_curl(
        monkeypatch,
        post_map={"klinq.com/graphql": _FakeResp(_load("klinq_magento_graphql_products.json"))},
    )
    price = await fetch_magento_graphql_price("klinq.com", "Miss Dior Originale EDT")
    assert price is not None
    assert price["source_method"] == "magento_graphql_bhd"
    assert price["currency"] == "BHD"
    assert price["amount"] == 57.81
    assert price["in_stock"] is True
    # klinq REQUIRES the .html suffix
    assert price["url"] == "https://klinq.com/dior-miss-dior-originale-edt.html"
    assert "original_currency" not in price


@pytest.mark.asyncio
async def test_shape_b_klinq_store_header_sent(monkeypatch):
    """klinq POST must carry Store:default (Shape-B store-view header)."""
    captured = {}
    from curl_cffi import requests as curl_requests

    def fake_post(url, *a, **k):
        captured["headers"] = k.get("headers", {})
        return _FakeResp(_load("klinq_magento_graphql_products.json"))

    monkeypatch.setattr(curl_requests, "post", fake_post)
    monkeypatch.setattr(curl_requests, "get", lambda *a, **k: _FakeResp("{}", 404))

    await fetch_magento_graphql_price("klinq.com", "Miss Dior Originale EDT")
    assert captured["headers"].get("Store") == "default"


@pytest.mark.asyncio
async def test_shape_b_trikart_converted_kwd(monkeypatch):
    """trikart (KWD) → converted_usd, original_currency=KWD, OOS honored."""
    _patch_curl(
        monkeypatch,
        post_map={"trikart": _FakeResp(_load("trikart_magento_graphql_products.json"))},
    )
    # NOTE: fixture item is OUT_OF_STOCK; adapter still returns the price dict
    # with in_stock=False (cascade decides). Query matches "Apple iPhone 15 256GB".
    price = await fetch_magento_graphql_price(
        "trikart.com", "Apple iPhone 15 256GB", currency="BHD"
    )
    assert price is not None
    assert price["source_method"] == "converted_usd"
    assert price["currency"] == "BHD"
    assert price["original_currency"] == "KWD"
    assert price["in_stock"] is False
    # 199.9 KWD * 1.23 = 245.877 → round to 3 decimals
    assert price["amount"] == pytest.approx(245.877, abs=0.01)


@pytest.mark.asyncio
async def test_shape_b_strict_match_no_fab(monkeypatch):
    """A query that matches NO item title → None (no wrong-brand fabrication)."""
    _patch_curl(
        monkeypatch,
        post_map={"klinq.com/graphql": _FakeResp(_load("klinq_magento_graphql_products.json"))},
    )
    price = await fetch_magento_graphql_price("klinq.com", "Chanel No 5 Parfum")
    assert price is None


@pytest.mark.asyncio
async def test_shape_b_ajmal_kwt_converted(monkeypatch):
    """ajmal-kwt (KWD) Shape-B → converted_usd."""
    _patch_curl(
        monkeypatch,
        post_map={"ajmal": _FakeResp(_load("ajmal_kwt_magento_graphql_products.json"))},
    )
    price = await fetch_magento_graphql_price(
        "en-kwt.ajmal.com", "Violet Musc Hair Mist", currency="BHD"
    )
    assert price is not None
    assert price["source_method"] == "converted_usd"
    assert price["original_currency"] == "KWD"
    # 10 KWD * 1.23 = 12.3
    assert price["amount"] == pytest.approx(12.3, abs=0.01)


# ---------------------------------------------------------------------------
# Error / edge paths — never raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_domain_returns_none(monkeypatch):
    """A domain with no config entry → None (no shape known)."""
    _patch_curl(monkeypatch, post_resp=_FakeResp("{}", 200))
    price = await fetch_magento_graphql_price("randomstore.example", "anything")
    assert price is None


@pytest.mark.asyncio
async def test_non_200_post_returns_none(monkeypatch):
    """A non-200 graphql POST → None, never raises."""
    _patch_curl(
        monkeypatch,
        post_map={"klinq.com/graphql": _FakeResp("err", 500)},
    )
    price = await fetch_magento_graphql_price("klinq.com", "Miss Dior")
    assert price is None


@pytest.mark.asyncio
async def test_garbage_json_returns_none(monkeypatch):
    """Non-JSON 200 body → None, never raises."""
    _patch_curl(
        monkeypatch,
        post_map={"klinq.com/graphql": _FakeResp("<html>not json</html>", 200)},
    )
    price = await fetch_magento_graphql_price("klinq.com", "Miss Dior")
    assert price is None


@pytest.mark.asyncio
async def test_network_error_returns_none(monkeypatch):
    """A raised transport error → None, never propagates."""
    from curl_cffi import requests as curl_requests

    def boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(curl_requests, "post", boom)
    monkeypatch.setattr(curl_requests, "get", boom)
    price = await fetch_magento_graphql_price("klinq.com", "Miss Dior")
    assert price is None


@pytest.mark.asyncio
async def test_disabled_page_scrape_returns_none(monkeypatch):
    """ENABLE_PAGE_SCRAPE off → None before any network call."""
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", False, raising=False)

    called = {"n": 0}
    from curl_cffi import requests as curl_requests

    def counting(*a, **k):
        called["n"] += 1
        return _FakeResp("{}", 200)

    monkeypatch.setattr(curl_requests, "post", counting)
    monkeypatch.setattr(curl_requests, "get", counting)
    price = await fetch_magento_graphql_price("klinq.com", "Miss Dior")
    assert price is None
    assert called["n"] == 0

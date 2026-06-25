"""Offline fixture-based tests for the SAP-Hybris OCC v2 adapter
(`app/services/occ_service.fetch_occ_rest_price`).

NO network — `app.services.occ_service._curl.get` is monkeypatched to return a
fake response whose `.status_code` + `.json()`/`.text` are built from the
captured recon fixtures in `tests/fixtures/bh_gcc/`.

Coverage (BUILD-SPEC §2.3 / §5.1):
  - genuine BHD (value + url-prepend with storefront origin + OOS filter)
  - search name→code resolution (virgin search hits carry the same price shape)
  - converted SAR/QAR branch (al-dawaa SAR, virginQa QAR → ``converted_usd``)
  - ``special=false`` defensive + virgin-``special``-absent (dict.get) +
    al-dawaa ``simulatedDiscountPrice`` mirror (not a markdown)
  - ``Accept: application/json`` header sent (omit → server returns XML)
  - dead-baseSite / non-200 / garbage → None, NEVER raises
  - strict-title-match no-fab (a wrong-brand hit → None)
"""
import json
import os

import pytest

import app.services.occ_service as occ

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "fixtures", "bh_gcc"
)


def _load(name: str) -> str:
    with open(os.path.join(FIXTURE_DIR, name), "r", encoding="utf-8") as fh:
        return fh.read()


class _FakeResp:
    """Mimics a curl_cffi response: .status_code, .text, .json()."""

    def __init__(self, *, status_code=200, text="", json_obj=None):
        self.status_code = status_code
        self.text = text
        self._json_obj = json_obj

    def json(self):
        if self._json_obj is not None:
            return self._json_obj
        return json.loads(self.text)


# ---------------------------------------------------------------------------
# Helper: patch _curl.get with a router keyed on URL substring, and capture the
# headers/params each call received so we can assert Accept:application/json.
# ---------------------------------------------------------------------------
def _install_router(monkeypatch, routes):
    """`routes` = list of (url_substring, _FakeResp). First match wins.

    Returns a list that collects (url, kwargs) per call for assertions.
    """
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        for needle, resp in routes:
            if needle in url:
                return resp
        return _FakeResp(status_code=404, text="not found")

    monkeypatch.setattr(occ._curl, "get", fake_get)
    return calls


# Force the env gate ON for every test (the adapter returns None if off).
@pytest.fixture(autouse=True)
def _enable_page_scrape(monkeypatch):
    monkeypatch.setattr(occ, "ENABLE_PAGE_SCRAPE", True)


# ===========================================================================
# GENUINE BHD — virginBh
# ===========================================================================

@pytest.mark.asyncio
async def test_virginbh_genuine_bhd_from_search(monkeypatch):
    """virginBh search for AirPods Pro 3 → genuine BHD 107.9, occ_rest_bhd,
    url prepended with the STOREFRONT origin (not the occ host)."""
    search = _FakeResp(text=_load("virginmegastore_virginbh_occ_search_airpods.json"))
    calls = _install_router(monkeypatch, [("/products/search", search)])

    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is not None
    assert price["amount"] == 107.9
    assert price["currency"] == "BHD"
    assert price["source_method"] == "occ_rest_bhd"
    assert price["estimated"] is False
    assert price["retailer"] == "virginmegastore.bh"
    # RELATIVE url prepended with the storefront origin, NOT occ.virginmegastore.com
    assert price["url"].startswith("https://www.virginmegastore.bh/")
    assert "occ.virginmegastore.com" not in price["url"]
    assert "/apple-airpods-pro-3/p/1113883" in price["url"]
    assert "original_currency" not in price  # native BHD — no conversion tag
    # in_stock: search hit has NO stock field → treat as available (not dropped)
    assert price.get("in_stock") in (True, None)
    # Accept:application/json MUST be sent (omit → XML → json.loads breaks)
    assert calls, "no HTTP call was made"
    _url, kwargs = calls[0]
    headers = {k.lower(): v for k, v in (kwargs.get("headers") or {}).items()}
    assert headers.get("accept") == "application/json"


@pytest.mark.asyncio
async def test_virginbh_oos_product_dropped(monkeypatch):
    """The verified virginBh product 830170 is outOfStock → adapter returns None
    (we never ship an OOS price)."""
    # A search that returns ONLY the OOS Backbone product.
    detail = json.loads(_load("virginmegastore_virginbh_occ_product_830170.json"))
    search_payload = {"products": [detail]}
    search = _FakeResp(json_obj=search_payload)
    _install_router(monkeypatch, [("/products/search", search)])

    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh",
        "Backbone One for iPhone Mobile Gaming Controller PlayStation Edition",
        currency="BHD",
    )
    assert price is None


# ===========================================================================
# CONVERTED — virginQa (QAR) + al-dawaa (SAR)
# ===========================================================================

@pytest.mark.asyncio
async def test_virginqa_converted_qar(monkeypatch):
    """virginQa product 830170 is QAR 399 → converted to BHD, stamped
    converted_usd, original_currency=QAR. (Stock here is OOS — to exercise the
    convert branch we feed it via a search wrapper of an IN-stock variant.)"""
    detail = json.loads(_load("virginmegastore_virginqa_occ_product_830170.json"))
    # make it in-stock so the OOS filter doesn't mask the conversion assertion
    detail["stock"] = {"stockLevelStatus": "inStock"}
    detail["name"] = "Apple AirPods Pro 3"  # a clean query match
    search = _FakeResp(json_obj={"products": [detail]})
    _install_router(monkeypatch, [("/products/search", search)])

    price = await occ.fetch_occ_rest_price(
        "virginmegastore.qa", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is not None
    assert price["currency"] == "BHD"
    assert price["source_method"] == "converted_usd"
    assert price["original_currency"] == "QAR"
    # 399 QAR * 0.1033 ~= 41.2 BHD
    assert 35.0 < price["amount"] < 48.0
    assert price["url"].startswith("https://virginmegastore.qa/")


@pytest.mark.asyncio
async def test_aldawaa_converted_sar_special_false(monkeypatch):
    """al-dawaa product 234419 = SAR 1805.5, special=false → convert, do NOT
    treat special=false as a markdown."""
    detail = json.loads(_load("aldawaa_occ_product_234419.json"))
    # name is Arabic; match on the English searchKeywords-style query instead by
    # overriding the name to a clean ASCII query so strict_title_match is exercised.
    detail["name"] = "Chicco Baby Bed Next 2 Me Co-Sleeping Crib Stone"
    search = _FakeResp(json_obj={"products": [detail]})
    _install_router(monkeypatch, [("/products/search", search)])

    price = await occ.fetch_occ_rest_price(
        "al-dawaa.com",
        "Chicco Baby Bed Next 2 Me Co-Sleeping Crib Stone",
        currency="BHD",
    )
    assert price is not None
    assert price["source_method"] == "converted_usd"
    assert price["original_currency"] == "SAR"
    # 1805.5 SAR * 0.1003 ~= 181 BHD
    assert 150.0 < price["amount"] < 220.0


@pytest.mark.asyncio
async def test_aldawaa_search_simulated_discount_not_markdown(monkeypatch):
    """al-dawaa search hit exposes simulatedDiscountPrice that MIRRORS price (no
    real discount) → the resolved amount is price.value, not a phantom markdown,
    and the SAR price converts."""
    payload = json.loads(_load("aldawaa_occ_search_panadol.json"))
    # first hit: Panadol Night, SAR 11.6, simulatedDiscountPrice == price
    payload["products"][0]["name"] = "Panadol Night"
    search = _FakeResp(json_obj={"products": [payload["products"][0]]})
    _install_router(monkeypatch, [("/products/search", search)])

    price = await occ.fetch_occ_rest_price(
        "al-dawaa.com", "Panadol Night", currency="BHD"
    )
    assert price is not None
    assert price["source_method"] == "converted_usd"
    assert price["original_currency"] == "SAR"
    # 11.6 SAR * 0.1003 ~= 1.16 BHD (the genuine value, not 0)
    assert 0.9 < price["amount"] < 1.5


# ===========================================================================
# NO-FAB / error paths
# ===========================================================================

@pytest.mark.asyncio
async def test_wrong_brand_hit_rejected(monkeypatch):
    """A search that returns ONLY a non-matching brand → None (no wrong-brand
    price ever shipped)."""
    search = _FakeResp(text=_load("virginmegastore_virginbh_occ_search_airpods.json"))
    _install_router(monkeypatch, [("/products/search", search)])
    # The fixture has AirPods + accessory cases — none match "Galaxy Buds".
    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh", "Samsung Galaxy Buds Pro", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_non_200_returns_none(monkeypatch):
    """Dead baseSite / HTTP 400 → None, never raises."""
    _install_router(monkeypatch, [("/products/search", _FakeResp(status_code=400, text="Bad Request"))])
    price = await occ.fetch_occ_rest_price(
        "virginmegastore.ae", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_garbage_body_returns_none(monkeypatch):
    """HTTP 200 with non-JSON body → None, never raises."""
    _install_router(monkeypatch, [("/products/search", _FakeResp(status_code=200, text="<html>not json</html>"))])
    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_empty_products_returns_none(monkeypatch):
    """Empty products list → None."""
    _install_router(monkeypatch, [("/products/search", _FakeResp(json_obj={"products": []}))])
    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_unknown_domain_returns_none(monkeypatch):
    """A domain not in the OCC store config → None (no fetch attempted)."""
    price = await occ.fetch_occ_rest_price(
        "not-an-occ-store.com", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_page_scrape_gate_off_returns_none(monkeypatch):
    """ENABLE_PAGE_SCRAPE off → None without any network call."""
    monkeypatch.setattr(occ, "ENABLE_PAGE_SCRAPE", False)
    called = {"n": 0}

    def fake_get(url, **kwargs):
        called["n"] += 1
        return _FakeResp(text="{}")

    monkeypatch.setattr(occ._curl, "get", fake_get)
    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is None
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_network_exception_returns_none(monkeypatch):
    """A raised exception in the fetch → None (never propagates)."""

    def boom(url, **kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(occ._curl, "get", boom)
    price = await occ.fetch_occ_rest_price(
        "virginmegastore.bh", "Apple AirPods Pro 3", currency="BHD"
    )
    assert price is None

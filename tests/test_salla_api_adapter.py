"""Offline, fixture-based tests for the Salla storefront-API price adapter.

No network: we monkeypatch ``curl_cffi.requests.get`` (patched where
``salla_service`` imports it) to return an object with ``.status_code`` +
``.text``/``.json()`` built from the captured fixtures in
``tests/fixtures/bh_gcc/``.

Covers (SPEC §2.2):
  - store-id regex extraction from storefront HTML (+ negative)
  - genuine BHD parse (reefperfumes) vs converted SAR (perfumya) branch
  - MAJOR-units guard (price is NOT minor units — no /100)
  - stock edge (is_out_of_stock honored)
  - null sku/gtin/brand robustness (match on name only)
  - empty data[] / non-200 / garbage / no-match -> None (never raises)
"""

import json
import os
from typing import Any, Optional

import pytest

import app.services.salla_service as salla

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "bh_gcc")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


class _FakeResp:
    def __init__(self, status_code: int = 200, text: str = "", json_obj: Any = None):
        self.status_code = status_code
        self._text = text
        self._json = json_obj

    @property
    def text(self) -> str:
        return self._text

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        return json.loads(self._text)


# Real captured fixtures.
_REEF_STOREFRONT = _read("salla_storefront_reefperfumes.html")
_PERFUMYA_STOREFRONT = _read("salla_storefront_perfumya.html")
_REEF_API_TEXT = _read("salla_api_reefperfumes.json")
_PERFUMYA_API_TEXT = _read("salla_api_perfumya_sar.json")
_REEF_API = json.loads(_REEF_API_TEXT)
_PERFUMYA_API = json.loads(_PERFUMYA_API_TEXT)

# The genuine product name the reef fixture's data[0] matches (Arabic title; we
# match on the brand/model tokens that DO appear). The reef item0 title is an
# Arabic perfume name; pick a query whose tokens are present so strict-title
# match passes. We derive the matchable query from the fixture item names below.
_REEF_ITEM0_NAME = _REEF_API["data"][0]["name"]
_PERFUMYA_ITEM0_NAME = _PERFUMYA_API["data"][0]["name"]


def _patch_two_step(monkeypatch, storefront_html: str, api_obj: Any,
                    storefront_status: int = 200, api_status: int = 200):
    """Patch curl_cffi.requests.get so the FIRST call (storefront) returns the
    HTML and the SECOND call (api.salla.dev) returns the API payload."""
    calls = {"n": 0}

    def fake_get(url, *args, **kwargs):
        calls["n"] += 1
        if "api.salla.dev" in url:
            if isinstance(api_obj, _FakeResp):
                return api_obj
            return _FakeResp(api_status, json_obj=api_obj)
        return _FakeResp(storefront_status, text=storefront_html)

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)
    return calls


@pytest.fixture(autouse=True)
def _enable_flags(monkeypatch):
    # The adapter is gated by ENABLE_PAGE_SCRAPE — force it on for tests.
    monkeypatch.setattr(salla, "ENABLE_PAGE_SCRAPE", True, raising=False)
    # Clear the per-domain store-id cache between tests.
    salla._STORE_ID_CACHE.clear()


# ---------------------------------------------------------------------------
# store-id regex
# ---------------------------------------------------------------------------

def test_store_id_regex_reefperfumes():
    assert salla._extract_store_id(_REEF_STOREFRONT) == "254895921"


def test_store_id_regex_perfumya():
    assert salla._extract_store_id(_PERFUMYA_STOREFRONT) == "2008161730"


def test_store_id_regex_negative():
    assert salla._extract_store_id("<html>no store here</html>") is None
    assert salla._extract_store_id("") is None


# ---------------------------------------------------------------------------
# genuine BHD (reefperfumes)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_genuine_bhd_reefperfumes(monkeypatch):
    _patch_two_step(monkeypatch, _REEF_STOREFRONT, _REEF_API)
    # Use the actual item0 name so strict-title-match passes deterministically.
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is not None
    assert out["source_method"] == "salla_api"
    assert out["currency"] == "BHD"
    assert out["estimated"] is False
    # reef item0 price = 18 (MAJOR units — not 0.18, not 1800)
    assert out["amount"] == 18.0
    assert "original_currency" not in out
    assert out["retailer"] == "reefperfumes.com"
    assert out["url"].startswith("http")
    assert out["in_stock"] is True
    assert 0.7 <= out["confidence"] <= 0.95


# ---------------------------------------------------------------------------
# converted SAR (perfumya)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_converted_sar_perfumya(monkeypatch):
    _patch_two_step(monkeypatch, _PERFUMYA_STOREFRONT, _PERFUMYA_API)
    out = await salla.fetch_salla_api_price("perfumya.com", _PERFUMYA_ITEM0_NAME)
    assert out is not None
    assert out["source_method"] == "converted_usd"
    assert out["currency"] == "BHD"
    assert out["original_currency"] == "SAR"
    assert out["estimated"] is False
    # perfumya item0 SAR price = 440 -> 440 * 0.1003 = 44.132 BHD
    assert out["amount"] == pytest.approx(44.132, abs=0.01)
    assert out["retailer"] == "perfumya.com"


# ---------------------------------------------------------------------------
# stock edge — is_out_of_stock honored
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_out_of_stock_flag(monkeypatch):
    api = json.loads(_REEF_API_TEXT)
    api["data"] = [dict(api["data"][0])]
    api["data"][0]["is_out_of_stock"] = True
    _patch_two_step(monkeypatch, _REEF_STOREFRONT, api)
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is not None
    assert out["in_stock"] is False


# ---------------------------------------------------------------------------
# major-units guard: a 3-digit SAR price must NOT be divided
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_major_units_not_divided(monkeypatch):
    _patch_two_step(monkeypatch, _PERFUMYA_STOREFRONT, _PERFUMYA_API)
    out = await salla.fetch_salla_api_price("perfumya.com", _PERFUMYA_ITEM0_NAME)
    # 440 SAR -> ~44 BHD; if it had been treated as minor units (/100) the BHD
    # amount would be sub-1, which is implausibly low and would never reach 44.
    assert out["amount"] > 10


# ---------------------------------------------------------------------------
# null sku/gtin/brand robustness — match on name only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_null_sku_gtin_brand(monkeypatch):
    # perfumya item0 already has sku=None, gtin=None, brand={id:None,...}
    item = _PERFUMYA_API["data"][0]
    assert item.get("sku") is None
    assert item.get("brand", {}).get("name") is None
    _patch_two_step(monkeypatch, _PERFUMYA_STOREFRONT, _PERFUMYA_API)
    out = await salla.fetch_salla_api_price("perfumya.com", _PERFUMYA_ITEM0_NAME)
    assert out is not None  # did not crash on null brand/sku


# ---------------------------------------------------------------------------
# no-match / wrong-brand -> None (no-fab)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_match_returns_none(monkeypatch):
    _patch_two_step(monkeypatch, _REEF_STOREFRONT, _REEF_API)
    out = await salla.fetch_salla_api_price(
        "reefperfumes.com", "Sony PlayStation 5 Pro Console 2TB")
    assert out is None


@pytest.mark.asyncio
async def test_empty_data_returns_none(monkeypatch):
    api = {"status": 200, "success": True, "data": [], "cursor": {}}
    _patch_two_step(monkeypatch, _REEF_STOREFRONT, api)
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is None


# ---------------------------------------------------------------------------
# error paths — never raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_200_api_returns_none(monkeypatch):
    _patch_two_step(monkeypatch, _REEF_STOREFRONT, _FakeResp(500, text="boom"))
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is None


@pytest.mark.asyncio
async def test_garbage_json_returns_none(monkeypatch):
    _patch_two_step(monkeypatch, _REEF_STOREFRONT, _FakeResp(200, text="<<not json>>"))
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is None


@pytest.mark.asyncio
async def test_storefront_no_store_id_returns_none(monkeypatch):
    _patch_two_step(monkeypatch, "<html>no id</html>", _REEF_API)
    out = await salla.fetch_salla_api_price("nostore.example", _REEF_ITEM0_NAME)
    assert out is None


@pytest.mark.asyncio
async def test_network_exception_returns_none(monkeypatch):
    def boom(url, *a, **k):
        raise RuntimeError("connection reset")
    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", boom, raising=True)
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is None


@pytest.mark.asyncio
async def test_flag_off_returns_none(monkeypatch):
    monkeypatch.setattr(salla, "ENABLE_PAGE_SCRAPE", False, raising=False)
    out = await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    assert out is None


# ---------------------------------------------------------------------------
# store-id is cached per domain (skip the storefront round-trip on 2nd call)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_store_id_cached(monkeypatch):
    calls = _patch_two_step(monkeypatch, _REEF_STOREFRONT, _REEF_API)
    await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    n_after_first = calls["n"]
    await salla.fetch_salla_api_price("reefperfumes.com", _REEF_ITEM0_NAME)
    # Second call should NOT re-fetch the storefront (store-id cached) → exactly
    # one additional API call, not two.
    assert calls["n"] == n_after_first + 1

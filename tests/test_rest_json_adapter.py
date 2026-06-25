"""Offline fixture-based tests for fetch_rest_json_price (R4).

Covers the three custom-JSON families that dispatch by domain:
  - ourshopee (apios.ourshopee.com) — BHD GENUINE (rest_json_bhd)
  - panda (api.panda.sa) — SAR → converted_usd
  - beautyboothqa (admin.beautybooth.qa) — QAR → converted_usd

No network: curl_cffi.requests.get is monkeypatched to return a fake response
object built from the captured fixtures in tests/fixtures/bh_gcc/.
"""
import json
import os
from pathlib import Path

import pytest

from app.services import rest_json_service
from app.services.rest_json_service import fetch_rest_json_price

FIX_DIR = Path(__file__).parent / "fixtures" / "bh_gcc"


def _load_fixture_text(name: str) -> str:
    return (FIX_DIR / name).read_text(encoding="utf-8")


def _load_fixture_json(name: str):
    return json.loads(_load_fixture_text(name))


class FakeResp:
    """Minimal stand-in for a curl_cffi response."""

    def __init__(self, text="", status_code=200, json_obj=None):
        self.text = text
        self.status_code = status_code
        self._json_obj = json_obj

    def json(self):
        if self._json_obj is not None:
            return self._json_obj
        return json.loads(self.text)


def _patch_get(monkeypatch, handler):
    """Patch the curl_cffi.requests.get the adapter imports lazily.

    `handler(url, **kwargs) -> FakeResp` lets a test route per-URL.
    """
    import curl_cffi

    def fake_get(url, *args, **kwargs):
        return handler(url, **kwargs)

    monkeypatch.setattr(curl_cffi.requests, "get", fake_get)


@pytest.fixture(autouse=True)
def _enable_page_scrape(monkeypatch):
    # The adapter gates on price_service.ENABLE_PAGE_SCRAPE — force it on.
    monkeypatch.setattr(rest_json_service, "ENABLE_PAGE_SCRAPE", True)


# ---------------------------------------------------------------------------
# ourshopee — BHD GENUINE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ourshopee_genuine_bhd(monkeypatch):
    """A name lookup resolving to the Dell Latitude 7420 yields a genuine
    rest_json_bhd price (BHD, estimated False), parsed as a human number."""
    search_payload = _load_fixture_json("ourshopee_getTopSelling.json")

    def handler(url, **kwargs):
        # The search/listing endpoint carries data[] with price+sku+name.
        return FakeResp(json_obj=search_payload)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "ourshopee.com", "Dell Latitude 7420", currency="BHD"
    )
    assert price is not None
    assert price["currency"] == "BHD"
    assert price["source_method"] == "rest_json_bhd"
    assert price["estimated"] is False
    # display_price "200" → 200.0
    assert abs(price["amount"] - 200.0) < 0.001
    assert price["retailer"] == "ourshopee.com"
    assert "ourshopee.com" in price["url"]
    # The getTopSelling listing carries no stock field → no-fab: key omitted.
    assert "in_stock" not in price
    assert "original_currency" not in price  # native BHD, no conversion


@pytest.mark.asyncio
async def test_ourshopee_product_detail_shape(monkeypatch):
    """The product_detail shape (data.product[0]) is also parseable when the
    search returns that envelope."""
    detail_payload = _load_fixture_json("ourshopee_product_detail_PN1497.json")

    def handler(url, **kwargs):
        return FakeResp(json_obj=detail_payload)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "ourshopee.com",
        "Dell Latitude 7420 Laptop",
        currency="BHD",
    )
    assert price is not None
    assert price["currency"] == "BHD"
    assert price["source_method"] == "rest_json_bhd"
    # display_price 200 (the discounted display price), old_price 289
    assert abs(price["amount"] - 200.0) < 0.001
    assert price["in_stock"] is True


@pytest.mark.asyncio
async def test_ourshopee_name_miss_returns_none(monkeypatch):
    """A query with no matching product in the listing → None (no fab)."""
    search_payload = _load_fixture_json("ourshopee_getTopSelling.json")

    def handler(url, **kwargs):
        return FakeResp(json_obj=search_payload)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "ourshopee.com", "iPhone 15 Pro Max 256GB", currency="BHD"
    )
    assert price is None


# ---------------------------------------------------------------------------
# panda — SAR → converted_usd
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_panda_converted_sar(monkeypatch):
    """A panda SAR price converts to BHD and stamps the literal converted_usd."""
    payload = _load_fixture_json("panda_products_milk.json")

    def handler(url, **kwargs):
        return FakeResp(json_obj=payload)

    _patch_get(monkeypatch, handler)
    # The fixture's first product is "Always Feminine Pads Aloe Cool ..." 16.5 SAR.
    price = await fetch_rest_json_price(
        "panda.sa", "Always Feminine Pads Aloe Cool Long Maxi 50", currency="BHD"
    )
    assert price is not None
    assert price["currency"] == "BHD"
    assert price["source_method"] == "converted_usd"
    assert price["original_currency"] == "SAR"
    # 16.5 SAR converted (rate < 1) → strictly less than the SAR figure.
    assert 0 < price["amount"] < 16.5
    assert price["estimated"] is False
    assert price["in_stock"] is True


@pytest.mark.asyncio
async def test_panda_headers_sent(monkeypatch):
    """The 4 mandatory panda headers are sent (422 without them)."""
    payload = _load_fixture_json("panda_products_milk.json")
    seen = {}

    def handler(url, **kwargs):
        seen.update(kwargs.get("headers") or {})
        return FakeResp(json_obj=payload)

    _patch_get(monkeypatch, handler)
    await fetch_rest_json_price(
        "panda.sa", "Always Feminine Pads Aloe Cool Long Maxi 50", currency="BHD"
    )
    assert seen.get("X-Panda-Source") == "PandaClick"
    assert seen.get("X-PandaClick-Agent") == "4"
    assert seen.get("api-version") == "2025-10-01"
    assert seen.get("X-Language") == "en"


@pytest.mark.asyncio
async def test_panda_422_returns_none(monkeypatch):
    """A non-200 (e.g. 422 missing headers) → None, never raises."""
    def handler(url, **kwargs):
        return FakeResp(text="missing headers", status_code=422)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "panda.sa", "Always Feminine Pads", currency="BHD"
    )
    assert price is None


# ---------------------------------------------------------------------------
# beautyboothqa — QAR → converted_usd
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_beautybooth_converted_qar(monkeypatch):
    """A beautyboothqa best_sell.data[] item (QAR net_price) → converted_usd."""
    payload = _load_fixture_json("beautyboothqa_product.json")

    def handler(url, **kwargs):
        return FakeResp(json_obj=payload)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "beautybooth.qa", "The Ordinary Niacinamide 10% Zinc 30ml", currency="BHD"
    )
    assert price is not None
    assert price["currency"] == "BHD"
    assert price["source_method"] == "converted_usd"
    assert price["original_currency"] == "QAR"
    # net_price 72 QAR converted (rate < 1) → less than 72.
    assert 0 < price["amount"] < 72
    assert price["estimated"] is False
    assert price["in_stock"] is True


@pytest.mark.asyncio
async def test_beautybooth_wrong_brand_rejected(monkeypatch):
    """A fuzzy cross-brand hit must NOT be shipped (no-fab strict match)."""
    payload = _load_fixture_json("beautyboothqa_product.json")

    def handler(url, **kwargs):
        return FakeResp(json_obj=payload)

    _patch_get(monkeypatch, handler)
    # No product in the fixture matches this brand+model.
    price = await fetch_rest_json_price(
        "beautybooth.qa", "Estee Lauder Advanced Night Repair 50ml", currency="BHD"
    )
    assert price is None


# ---------------------------------------------------------------------------
# cross-cutting: gates + error paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_page_scrape_gate_off_returns_none(monkeypatch):
    monkeypatch.setattr(rest_json_service, "ENABLE_PAGE_SCRAPE", False)
    price = await fetch_rest_json_price(
        "ourshopee.com", "Dell Latitude 7420", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_unknown_domain_returns_none(monkeypatch):
    # A domain not in the dispatch map → None (never raises).
    price = await fetch_rest_json_price(
        "example.com", "Anything", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_network_error_returns_none(monkeypatch):
    def handler(url, **kwargs):
        raise RuntimeError("boom")

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "ourshopee.com", "Dell Latitude 7420", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_garbage_json_returns_none(monkeypatch):
    def handler(url, **kwargs):
        return FakeResp(text="<html>not json</html>", status_code=200)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "panda.sa", "Always Feminine Pads", currency="BHD"
    )
    assert price is None


@pytest.mark.asyncio
async def test_prices_not_minor_units(monkeypatch):
    """Regression guard: prices are HUMAN numbers, NOT minor units — a /1000
    bug would make ourshopee 200 BHD → 0.2 BHD."""
    search_payload = _load_fixture_json("ourshopee_getTopSelling.json")

    def handler(url, **kwargs):
        return FakeResp(json_obj=search_payload)

    _patch_get(monkeypatch, handler)
    price = await fetch_rest_json_price(
        "ourshopee.com", "Dell Latitude 7420", currency="BHD"
    )
    assert price is not None
    assert price["amount"] > 50  # not a /1000-divided fraction

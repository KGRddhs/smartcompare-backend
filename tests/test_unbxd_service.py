"""R3c — fetch_unbxd_price (extra.com BH genuine-BHD Unbxd search API).

Unbxd search-API returns response.products[] (NOT hits). extra-BH is native BHD
-> source_method=local_bhd. All HTTP mocked off the captured fixture.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import MagicMock, patch

_FX = Path(__file__).parent / "fixtures" / "bh_gcc"


def _load(name):
    return json.loads((_FX / f"{name}.json").read_text(encoding="utf-8"))


def _mock_get(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    resp.text = json.dumps(payload)
    return MagicMock(return_value=resp)


@pytest.fixture(autouse=True)
def _circuit_closed():
    with patch("app.services.unbxd_service.is_circuit_closed", return_value=True):
        yield


@pytest.mark.asyncio
async def test_extra_bh_genuine_local_bhd():
    import app.services.unbxd_service as un
    payload = _load("unbxd_extra_bh")
    with patch("curl_cffi.requests.get", _mock_get(payload)):
        out = await un.fetch_unbxd_price(
            "extra.com", "Apple iPhone 17 Pro Max 256GB", "electronics")
    assert out is not None
    assert out["currency"] == "BHD"
    assert out["source_method"] == "local_bhd"
    assert out["estimated"] is False
    assert out["amount"] == pytest.approx(559.99)
    assert "original_currency" not in out
    assert out["retailer"] == "extra.com"
    assert out["url"].startswith("https://www.extra.com/")
    assert out["in_stock"] is True  # inStockFlag == "true" (STRING)
    assert 0.7 <= out["confidence"] <= 0.95


@pytest.mark.asyncio
async def test_string_instock_false_parsed():
    import app.services.unbxd_service as un
    payload = _load("unbxd_extra_bh")
    # force the matched product out of stock (STRING boolean)
    payload["response"]["products"][0]["inStockFlag"] = "false"
    with patch("curl_cffi.requests.get", _mock_get(payload)):
        out = await un.fetch_unbxd_price(
            "extra.com", "Apple iPhone 17 Pro Max 256GB", "electronics")
    assert out is not None
    assert out["in_stock"] is False


@pytest.mark.asyncio
async def test_wrong_brand_no_fab_returns_none():
    import app.services.unbxd_service as un
    payload = _load("unbxd_extra_bh")
    with patch("curl_cffi.requests.get", _mock_get(payload)):
        out = await un.fetch_unbxd_price(
            "extra.com", "Samsung Galaxy Z Fold 6", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_zero_price_returns_none():
    import app.services.unbxd_service as un
    payload = _load("unbxd_extra_bh")
    # zero ALL price fields so the sellingPrice->price->wasPrice fallback finds none
    for k in ("sellingPrice", "price", "wasPrice"):
        payload["response"]["products"][0][k] = 0
    with patch("curl_cffi.requests.get", _mock_get(payload)):
        out = await un.fetch_unbxd_price(
            "extra.com", "Apple iPhone 17 Pro Max 256GB", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_non_200_returns_none_never_raises():
    import app.services.unbxd_service as un
    resp = MagicMock()
    resp.status_code = 401
    resp.json = MagicMock(side_effect=ValueError("no json"))
    resp.text = "unauthorized"
    with patch("curl_cffi.requests.get", MagicMock(return_value=resp)):
        out = await un.fetch_unbxd_price("extra.com", "Apple iPhone 17", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_garbage_body_returns_none_never_raises():
    import app.services.unbxd_service as un
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(side_effect=ValueError("not json"))
    resp.text = "garbage"
    with patch("curl_cffi.requests.get", MagicMock(return_value=resp)):
        out = await un.fetch_unbxd_price("extra.com", "Apple iPhone 17", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_transport_error_returns_none_never_raises():
    import app.services.unbxd_service as un
    with patch("curl_cffi.requests.get", MagicMock(side_effect=RuntimeError("boom"))):
        out = await un.fetch_unbxd_price("extra.com", "Apple iPhone 17", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_unknown_domain_returns_none():
    import app.services.unbxd_service as un
    with patch("curl_cffi.requests.get", MagicMock()) as g:
        out = await un.fetch_unbxd_price("not-a-store.com", "Apple iPhone 17", "electronics")
    assert out is None
    g.assert_not_called()


@pytest.mark.asyncio
async def test_disabled_by_flag(monkeypatch):
    import app.services.unbxd_service as un
    monkeypatch.setattr(un, "ENABLE_PAGE_SCRAPE", False)
    g = MagicMock()
    with patch("curl_cffi.requests.get", g):
        out = await un.fetch_unbxd_price("extra.com", "Apple iPhone 17", "electronics")
    assert out is None
    g.assert_not_called()


@pytest.mark.asyncio
async def test_circuit_open_returns_none():
    import app.services.unbxd_service as un
    g = MagicMock()
    with patch("app.services.unbxd_service.is_circuit_closed", return_value=False), \
         patch("curl_cffi.requests.get", g):
        out = await un.fetch_unbxd_price("extra.com", "Apple iPhone 17", "electronics")
    assert out is None
    g.assert_not_called()

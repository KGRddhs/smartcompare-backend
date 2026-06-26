"""Offline tests for the Zyte render-tier adapter (app/services/zyte_service.py).

HTTP mocked off the captured Zyte fixtures (tests/fixtures/zyte/). Covers the
fils-fix (BHD 3-decimal mis-parse), the OFF-CLOCK gate, strict-match no-fab
(sephora returns makeup for a "Creed Aventus" search → must reject), and the
genuine stamp.
"""
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import app.services.zyte_service as zs

_FX = Path(__file__).parent / "fixtures" / "zyte"


def _load(name):
    return json.loads((_FX / f"{name}.json").read_text(encoding="utf-8"))


def _mock_zyte(payload):
    """Patch httpx.AsyncClient so its .post returns a 200 with `payload`."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx)


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("ENABLE_ZYTE_RENDER", "true")
    monkeypatch.setenv("ZYTE_API_KEY", "test-key")


# --- fils-fix --------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("77000.0", 77.0),   # fils form (77.000 BHD)
    (77000, 77.0),
    ("11.0", 11.0),      # already-major form
    (11000.0, 11.0),     # the inconsistent fils form
    ("0", None), (-5, None), ("garbage", None), (None, None),
])
def test_normalize_bhd_fils_fix(raw, expected):
    assert zs.normalize_bhd_amount(raw) == expected


# --- genuine BHD via sephora productList -----------------------------------

@pytest.mark.asyncio
async def test_sephora_oud_wood_genuine_bhd(monkeypatch):
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum")
    assert out is not None, "should match the Oud Wood EDP"
    assert out["source_method"] == "zyte_render_bhd"
    assert out["currency"] == "BHD"
    assert out["amount"] == pytest.approx(77.0), "fils-fixed from 77000"
    assert out["retailer"] == "sephora.me"
    assert "sephora.me" in out["url"]
    assert out["estimated"] is False


# --- no-fab: a wrong-brand search must NOT ship a price --------------------

@pytest.mark.asyncio
async def test_wrong_brand_search_rejected(monkeypatch):
    # sephora doesn't carry Creed — the search returns makeup. Build that shape.
    makeup = {"productList": {"products": [
        {"name": "Dior Addict - Shine Lipstick", "price": "23000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/dior-addict-shine-lipstick/P1"},
        {"name": "Easy Bake Loose Baking & Setting Powder", "price": "20000.0", "currency": "BHD",
         "url": "https://www.sephora.me/bh-en/p/easy-bake/P2"},
    ]}}
    with patch("httpx.AsyncClient", _mock_zyte(makeup)):
        out = await zs.fetch_zyte_price("sephora.me", "Creed Aventus")
    assert out is None, "no Creed in the makeup results → must return None, never a wrong price"


# --- gates -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_off_clock_gate(monkeypatch):
    monkeypatch.delenv("ENABLE_ZYTE_RENDER", raising=False)  # gated OFF
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum")
    assert out is None, "gated OFF (ENABLE_ZYTE_RENDER unset) → never fires"


@pytest.mark.asyncio
async def test_no_api_key(monkeypatch):
    monkeypatch.delenv("ZYTE_API_KEY", raising=False)
    payload = _load("sephora_productlist_oud_wood")
    with patch("httpx.AsyncClient", _mock_zyte(payload)):
        out = await zs.fetch_zyte_price("sephora.me", "Tom Ford Oud Wood Eau de Parfum")
    assert out is None


@pytest.mark.asyncio
async def test_unknown_domain(monkeypatch):
    with patch("httpx.AsyncClient", _mock_zyte({"productList": {"products": []}})):
        out = await zs.fetch_zyte_price("random-store.com", "Tom Ford Oud Wood")
    assert out is None

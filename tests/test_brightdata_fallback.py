"""Bright Data SERP fallback (2026-07-07) — provider + serper fallback wiring.

Bright Data is a drop-in, Serper-shaped discovery provider used when the Serper
key is exhausted/erroring (the free-key-depletion class the audit surfaced). It
ships INERT: unless ENABLE_BRIGHTDATA_FALLBACK + BRIGHTDATA_API_KEY +
BRIGHTDATA_ZONE are all set, the serper path is byte-identical to Serper-only.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import brightdata_service as bd


# --- a representative Bright Data brd_json=1 Google SERP response ------------
_BD_ORGANIC = {
    "organic": [
        {"rank": 1, "title": "Ajmal Aristocrat EDP", "link": "https://en-bh.ajmal.com/products/aristocrat",
         "description": "Ajmal Aristocrat 75ml"},
        {"rank": 2, "title": "No link row", "url": "https://x.com/p", "snippet": "alt fields"},
        {"rank": 3, "title": "dropme"},  # no link/url -> dropped
    ],
}
_BD_SHOPPING = {
    "shopping": [
        {"title": "iPhone 15 128GB", "link": "https://noon.com/x", "seller": "noon", "price": "BHD 245"},
        {"name": "alt-name", "product_link": "https://y.com/z", "source": "extra"},
    ],
}


class TestEnabledGate:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ENABLE_BRIGHTDATA_FALLBACK", raising=False)
        assert bd._brightdata_enabled() is False

    def test_flag_on_but_no_creds(self, monkeypatch):
        monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")
        monkeypatch.delenv("BRIGHTDATA_API_KEY", raising=False)
        monkeypatch.delenv("BRIGHTDATA_ZONE", raising=False)
        assert bd._brightdata_enabled() is False  # creds required

    def test_fully_configured(self, monkeypatch):
        monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "tok")
        monkeypatch.setenv("BRIGHTDATA_ZONE", "serp")
        assert bd._brightdata_enabled() is True


class TestUrlBuilder:
    def test_search_url(self):
        u = bd._google_url("iphone 15", country="bh", num=10, shopping=False)
        assert u.startswith("https://www.google.com/search?")
        assert "q=iphone+15" in u and "gl=bh" in u and "hl=en" in u
        assert "brd_json=1" in u and "num=10" in u and "tbm=shop" not in u

    def test_shopping_url(self):
        u = bd._google_url("iphone 15", country="bh", num=10, shopping=True)
        assert "tbm=shop" in u


class TestMappers:
    def test_map_organic_to_serper_shape(self):
        rows = bd._map_bd_organic(_BD_ORGANIC)
        assert len(rows) == 2  # the no-link row is dropped
        assert rows[0] == {"title": "Ajmal Aristocrat EDP",
                           "link": "https://en-bh.ajmal.com/products/aristocrat",
                           "snippet": "Ajmal Aristocrat 75ml"}
        # defensive field reads: url -> link, snippet stays
        assert rows[1]["link"] == "https://x.com/p" and rows[1]["snippet"] == "alt fields"

    def test_map_shopping_to_serper_shape(self):
        rows = bd._map_bd_shopping(_BD_SHOPPING)
        assert len(rows) == 2
        assert rows[0]["title"] == "iPhone 15 128GB" and rows[0]["source"] == "noon"
        assert rows[0]["price"] == "BHD 245"
        assert rows[1]["link"] == "https://y.com/z" and rows[1]["source"] == "extra"

    def test_mappers_never_raise_on_junk(self):
        for junk in (None, {}, {"organic": "x"}, {"organic": [1, None, "s"]}):
            assert bd._map_bd_organic(junk) == []
        for junk in (None, {}, {"shopping": 5}):
            assert bd._map_bd_shopping(junk) == []


@pytest.mark.asyncio
class TestBdSearchWeb:
    async def _mock_post(self, monkeypatch, *, status=200, body=None, raises=False):
        resp = MagicMock(); resp.status_code = status; resp.json = MagicMock(return_value=body or _BD_ORGANIC)
        client = MagicMock()
        if raises:
            client.post = AsyncMock(side_effect=RuntimeError("boom"))
        else:
            client.post = AsyncMock(return_value=resp)
        cm = MagicMock(); cm.__aenter__ = AsyncMock(return_value=client); cm.__aexit__ = AsyncMock(return_value=False)
        monkeypatch.setattr(bd.httpx, "AsyncClient", lambda *a, **k: cm)
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "tok"); monkeypatch.setenv("BRIGHTDATA_ZONE", "serp")

    async def test_returns_mapped_organic(self, monkeypatch):
        await self._mock_post(monkeypatch)
        out = await bd.bd_search_web("iphone 15")
        assert len(out["organic"]) == 2 and out["organic"][0]["title"] == "Ajmal Aristocrat EDP"

    async def test_non_200_returns_empty(self, monkeypatch):
        await self._mock_post(monkeypatch, status=402)
        out = await bd.bd_search_web("iphone 15")
        assert out["organic"] == [] and out.get("error")

    async def test_exception_returns_empty_never_raises(self, monkeypatch):
        await self._mock_post(monkeypatch, raises=True)
        out = await bd.bd_search_web("iphone 15")
        assert out["organic"] == []

    async def test_non_json_response_self_diagnoses_returns_empty(self, monkeypatch):
        """A 200 with a NON-JSON body (e.g. raw HTML if brd_json is off) must not
        crash — resp.json() raises, _bd_post logs + returns None, fallback is empty."""
        resp = MagicMock(); resp.status_code = 200
        resp.json = MagicMock(side_effect=ValueError("no json")); resp.text = "<html>...</html>"
        client = MagicMock(); client.post = AsyncMock(return_value=resp)
        cm = MagicMock(); cm.__aenter__ = AsyncMock(return_value=client); cm.__aexit__ = AsyncMock(return_value=False)
        monkeypatch.setattr(bd.httpx, "AsyncClient", lambda *a, **k: cm)
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "tok"); monkeypatch.setenv("BRIGHTDATA_ZONE", "serp_api1")
        out = await bd.bd_search_web("iphone 15")
        assert out["organic"] == []

    async def test_no_creds_returns_none_shape(self, monkeypatch):
        monkeypatch.delenv("BRIGHTDATA_API_KEY", raising=False)
        monkeypatch.delenv("BRIGHTDATA_ZONE", raising=False)
        out = await bd.bd_search_web("iphone 15")
        assert out["organic"] == []


@pytest.mark.asyncio
class TestSerperFallbackWiring:
    async def test_search_web_falls_back_when_no_key_and_enabled(self, monkeypatch):
        import app.services.serper_service as ss
        monkeypatch.setattr(ss, "_active_serper_key", lambda: None)  # Serper unavailable
        monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")
        monkeypatch.setenv("BRIGHTDATA_API_KEY", "tok"); monkeypatch.setenv("BRIGHTDATA_ZONE", "serp")
        with patch("app.services.brightdata_service.bd_search_web",
                   new=AsyncMock(return_value={"organic": [{"link": "x"}]})) as m:
            out = await ss.search_web("iphone 15")
        m.assert_awaited_once()
        assert out["organic"] == [{"link": "x"}]

    async def test_search_web_no_fallback_when_disabled_byte_identical(self, monkeypatch):
        """Flag OFF -> the pre-fix path: no Serper key -> 'Search not configured',
        Bright Data never called (byte-identical to Serper-only)."""
        import app.services.serper_service as ss
        monkeypatch.setattr(ss, "_active_serper_key", lambda: None)
        monkeypatch.delenv("ENABLE_BRIGHTDATA_FALLBACK", raising=False)
        with patch("app.services.brightdata_service.bd_search_web", new=AsyncMock()) as m:
            out = await ss.search_web("iphone 15")
        m.assert_not_awaited()
        assert out == {"organic": [], "error": "Search not configured"}

"""Wave-1 — persist + rehydrate the resolved listing title on the L2 cache.

The DB (product_prices) never stored `title`, so a rehydrated L2 price was
title-less → not usable_exact_genuine, not re-cacheable. This pins the
flag-gated fix: when ENABLE_PRICE_TITLE_PERSIST is ON, save_price writes `title`
and get_cached_price selects + returns it. Flag OFF = byte-identical (no `title`
in the insert, no `title` in the returned dict) so it is safe before migration
033 lands.
"""
from __future__ import annotations

import asyncio

import pytest

from app.services import product_data_service as pds


class _FakeQuery:
    def __init__(self, sink, row=None):
        self._sink = sink
        self._row = row

    def insert(self, payload):
        self._sink["insert"] = payload
        return self

    def select(self, cols):
        self._sink["select_cols"] = cols
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        class _R:
            data = [self._row] if self._row is not None else []
        return _R()


class _FakeClient:
    def __init__(self, sink, row=None):
        self._sink = sink
        self._row = row

    def table(self, name):
        self._sink["table"] = name
        return _FakeQuery(self._sink, self._row)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _install_client(monkeypatch, sink, row=None):
    monkeypatch.setattr(pds, "get_admin_supabase_client",
                        lambda: _FakeClient(sink, row))


# --- SAVE side --------------------------------------------------------------

def test_save_price_omits_title_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_PRICE_TITLE_PERSIST", raising=False)
    sink = {}
    _install_client(monkeypatch, sink)
    _run(pds.save_price("k", "Dior", "Sauvage", None, "bahrain",
                        {"amount": 45.0, "currency": "BHD", "title": "Dior Sauvage EDT 100ml"}))
    assert "title" not in sink["insert"]


def test_save_price_writes_title_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    _install_client(monkeypatch, sink)
    _run(pds.save_price("k", "Dior", "Sauvage", None, "bahrain",
                        {"amount": 45.0, "currency": "BHD", "title": "Dior Sauvage EDT 100ml"}))
    assert sink["insert"]["title"] == "Dior Sauvage EDT 100ml"


# --- READ side --------------------------------------------------------------

_ROW = {
    "amount": 45.0, "currency": "BHD", "retailer": "theperfumesclub",
    "url": "https://x/p", "source_method": "woo_store_api", "estimated": False,
    "fetched_at": "2999-01-01T00:00:00+00:00", "title": "Dior Sauvage EDT 100ml",
}


def test_get_cached_price_excludes_title_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_PRICE_TITLE_PERSIST", raising=False)
    sink = {}
    _install_client(monkeypatch, sink, row=dict(_ROW))
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert "title" not in out
    assert "title" not in sink["select_cols"]


def test_get_cached_price_rehydrates_title_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    _install_client(monkeypatch, sink, row=dict(_ROW))
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert out["title"] == "Dior Sauvage EDT 100ml"
    assert "title" in sink["select_cols"]


def test_get_cached_price_flag_on_none_title_omits_title_key(monkeypatch):
    # A legacy/flag-OFF row rehydrated under the flag has title=None — the falsy
    # guard `_title_persist_enabled() and row.get("title")` must NOT inject a None
    # title (locks the truthiness check against a `'title' in row` refactor).
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    row = dict(_ROW); row["title"] = None
    _install_client(monkeypatch, {}, row=row)
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert "title" not in out


def test_get_cached_price_flag_on_missing_title_key_omits(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    row = {k: v for k, v in _ROW.items() if k != "title"}
    _install_client(monkeypatch, {}, row=row)
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert "title" not in out


def test_save_price_flag_on_preserves_all_columns(monkeypatch):
    # A column-drop regression (keeping title but losing brand/amount) must fail.
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    _install_client(monkeypatch, sink)
    _run(pds.save_price("k", "Dior", "Sauvage", None, "bahrain",
                        {"amount": 45.0, "currency": "BHD", "source_method": "woo_store_api",
                         "title": "Dior Sauvage EDT 100ml"}))
    ins = sink["insert"]
    for col in ("product_key", "brand", "name", "region", "amount", "source_method", "title"):
        assert col in ins, col

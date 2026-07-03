"""Wave-2 B1.2 — in_stock + brand L2 round-trip (migration 034) + the DB->L1
promotion re-gate (chokepoint R8c).

Extends the cherry-picked test_price_title_persistence.py (which pins the `title`
round-trip). Here:
  * product_data_service: flag-OFF byte-identity (no in_stock/brand in the SELECT
    cols or the insert row); flag-ON round-trip (save writes in_stock only when a
    bool; get rehydrates title/brand/in_stock, omitting a None in_stock).
  * the DB->L1 promotion re-gate in structured_comparison_service._get_price: a
    title-carrying wrong-SKU DB row is SERVED but NOT promoted when
    should_cache_price fails; a correct row IS promoted; a title-less legacy row
    is served-not-promoted; flag-OFF promotes unconditionally as before.
  * the KPI/display closure: a rehydrated in_stock=False DB-served price now
    FAILS the display OOS pend (guard_rejected='out_of_stock') with the flag ON.

All Supabase / cache access is mocked — NO live DB, NO live Redis.
"""
from __future__ import annotations

import asyncio

import pytest

from app.services import product_data_service as pds
from app.services import structured_comparison_service as scs
from app.services.price_service import is_price_showable, exact_gate_enabled


# --------------------------------------------------------------------------- #
# product_data_service fakes (mirror the cherry-picked title test's shape)
# --------------------------------------------------------------------------- #
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


_DB_ROW = {
    "amount": 45.0, "currency": "BHD", "retailer": "theperfumesclub",
    "url": "https://x/p", "source_method": "woo_store_api", "estimated": False,
    "fetched_at": "2999-01-01T00:00:00+00:00",
    "title": "Dior Sauvage EDT 100ml", "brand": "Dior", "in_stock": True,
}


# --------------------------------------------------------------------------- #
# SAVE side — in_stock persistence + flag-OFF byte-identity
# --------------------------------------------------------------------------- #
def test_save_price_omits_in_stock_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_PRICE_TITLE_PERSIST", raising=False)
    sink = {}
    _install_client(monkeypatch, sink)
    _run(pds.save_price("k", "Dior", "Sauvage", None, "bahrain",
                        {"amount": 45.0, "currency": "BHD",
                         "title": "Dior Sauvage EDT 100ml", "in_stock": True}))
    assert "in_stock" not in sink["insert"]
    assert "title" not in sink["insert"]


def test_save_price_writes_in_stock_when_flag_on_and_bool(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    _install_client(monkeypatch, sink)
    _run(pds.save_price("k", "Dior", "Sauvage", None, "bahrain",
                        {"amount": 45.0, "currency": "BHD",
                         "title": "Dior Sauvage EDT 100ml", "in_stock": False}))
    assert sink["insert"]["in_stock"] is False
    assert sink["insert"]["title"] == "Dior Sauvage EDT 100ml"


def test_save_price_omits_in_stock_when_none_even_flag_on(monkeypatch):
    """A None/absent in_stock leaves the column NULL (= unknown), pre-034 shape."""
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    _install_client(monkeypatch, sink)
    _run(pds.save_price("k", "Dior", "Sauvage", None, "bahrain",
                        {"amount": 45.0, "currency": "BHD",
                         "title": "Dior Sauvage EDT 100ml"}))  # no in_stock key
    assert "in_stock" not in sink["insert"]
    # brand is always persisted (function param, migration-012 column)
    assert sink["insert"]["brand"] == "Dior"


# --------------------------------------------------------------------------- #
# READ side — flag-OFF byte-identity + flag-ON rehydrate
# --------------------------------------------------------------------------- #
def test_get_cached_price_excludes_in_stock_brand_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_PRICE_TITLE_PERSIST", raising=False)
    sink = {}
    _install_client(monkeypatch, sink, row=dict(_DB_ROW))
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert "in_stock" not in out
    assert "brand" not in out
    assert "title" not in out
    # SELECT cols are byte-identical to pre-033/034
    assert "in_stock" not in sink["select_cols"]
    assert "brand" not in sink["select_cols"]
    assert "title" not in sink["select_cols"]


def test_get_cached_price_rehydrates_in_stock_brand_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    _install_client(monkeypatch, sink, row=dict(_DB_ROW))
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert out["title"] == "Dior Sauvage EDT 100ml"
    assert out["brand"] == "Dior"
    assert out["in_stock"] is True
    assert "brand" in sink["select_cols"]
    assert "in_stock" in sink["select_cols"]


def test_get_cached_price_omits_none_in_stock_when_flag_on(monkeypatch):
    """A NULL in_stock (legacy/flag-OFF-written row) is omitted, not coerced."""
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    row = dict(_DB_ROW)
    row["in_stock"] = None
    _install_client(monkeypatch, sink, row=row)
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert "in_stock" not in out  # None omitted, treated as pre-034


def test_get_cached_price_rehydrates_false_in_stock_when_flag_on(monkeypatch):
    """An explicit in_stock=False must round-trip (feeds the OOS display pend)."""
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    row = dict(_DB_ROW)
    row["in_stock"] = False
    _install_client(monkeypatch, sink, row=row)
    out = _run(pds.get_cached_price("k", "bahrain"))
    assert out is not None
    assert out["in_stock"] is False


# --------------------------------------------------------------------------- #
# The KPI/display closure — a rehydrated in_stock=False DB-served price FAILS
# the display OOS pend (census titleless/OOS-TTL closure).
# --------------------------------------------------------------------------- #
def test_rehydrated_oos_price_fails_display_pend(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    sink = {}
    row = dict(_DB_ROW)
    row["in_stock"] = False
    _install_client(monkeypatch, sink, row=row)
    served = _run(pds.get_cached_price("k", "bahrain"))
    assert served["in_stock"] is False
    # The display chokepoint now sees the rehydrated OOS flag and pends it.
    showable = is_price_showable(
        "Dior Sauvage Eau de Toilette 100ml", served, "fragrances",
        enforce_correctness=True,
    )
    assert showable is False
    assert served.get("guard_rejected") == "out_of_stock"


# --------------------------------------------------------------------------- #
# The DB->L1 promotion re-gate (chokepoint R8c)
# --------------------------------------------------------------------------- #
def _install_promotion_harness(monkeypatch, db_price):
    """Drive scs._get_price to the L2->L1 promotion block with a fixed DB hit.

    Mocks: L1 miss, cache-key builder, query validator, the weak read check
    (True — we isolate the NEW strong re-gate), the DB read, and set_cached
    (recorded). Keeps the REAL should_cache_price + _title_persist_enabled.
    """
    calls = {"set_cached": []}
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(scs, "build_size_aware_price_cache_key",
                        lambda *a, **k: "ck")
    monkeypatch.setattr(scs, "_price_cache_bust_enabled", lambda: False)
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)  # L1 miss
    monkeypatch.setattr(scs, "_cache_price_identity_ok",
                        lambda *a, **k: True)  # isolate the strong re-gate
    monkeypatch.setattr(scs, "price_cache_ttl", lambda *a, **k: 100)

    async def _fake_get_cached_price(cache_key, region):
        return dict(db_price)

    monkeypatch.setattr(pds, "get_cached_price", _fake_get_cached_price)
    monkeypatch.setattr(scs, "set_cached",
                        lambda *a, **k: calls["set_cached"].append(a))
    return calls


_CORRECT_DB = {
    "amount": 45.0, "currency": "BHD", "retailer": "theperfumesclub",
    "url": "https://theperfumesclub.com/p/dior-sauvage-edt-100",
    "source_method": "woo_store_api", "estimated": False,
    "title": "Dior Sauvage Eau de Toilette 100ml", "brand": "Dior",
    "in_stock": True,
}
_WRONG_SKU_DB = {  # Sauvage -> Elixir (census leak string)
    "amount": 45.0, "currency": "BHD", "retailer": "theperfumesclub",
    "url": "https://theperfumesclub.com/p/dior-sauvage-elixir",
    "source_method": "woo_store_api", "estimated": False,
    "title": "Dior Sauvage Elixir Eau de Parfum 100ml", "brand": "Dior",
    "in_stock": True,
}
_TITLELESS_DB = {
    "amount": 45.0, "currency": "BHD", "retailer": "theperfumesclub",
    "url": "https://theperfumesclub.com/p/x", "source_method": "woo_store_api",
    "estimated": False,  # no title (legacy row)
}


def test_promotion_regate_refuses_wrong_sku_but_serves(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    calls = _install_promotion_harness(monkeypatch, _WRONG_SKU_DB)
    svc = scs.get_comparison_service()
    out = _run(svc._get_price("Dior", "Sauvage", None, "bahrain",
                              "Dior Sauvage", nocache=False, category="fragrances"))
    # SERVED (current behavior preserved)
    assert out is not None
    assert out.get("_cached") is True
    assert out.get("_cache_source") == "db"
    # NOT promoted into L1 (should_cache_price failed on the wrong SKU)
    assert calls["set_cached"] == []


def test_promotion_regate_promotes_correct_sku(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    calls = _install_promotion_harness(monkeypatch, _CORRECT_DB)
    svc = scs.get_comparison_service()
    out = _run(svc._get_price("Dior", "Sauvage Eau de Toilette 100ml", None,
                              "bahrain", "Dior Sauvage Eau de Toilette 100ml",
                              nocache=False, category="fragrances"))
    assert out is not None
    assert out.get("_cache_source") == "db"
    # Promoted (correct SKU passes should_cache_price)
    assert len(calls["set_cached"]) == 1


def test_promotion_regate_titleless_served_not_promoted(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_PRICE_TITLE_PERSIST", "true")
    calls = _install_promotion_harness(monkeypatch, _TITLELESS_DB)
    svc = scs.get_comparison_service()
    out = _run(svc._get_price("Dior", "Sauvage", None, "bahrain",
                              "Dior Sauvage", nocache=False, category="fragrances"))
    assert out is not None
    assert out.get("_cache_source") == "db"
    # Title-less legacy row: served but not promoted (nothing to re-verify)
    assert calls["set_cached"] == []


def test_promotion_flag_off_promotes_unconditionally(monkeypatch):
    """Flag OFF -> byte-identical: even a wrong-SKU row is promoted (as before).

    This pins that the re-gate is entirely behind ENABLE_PRICE_TITLE_PERSIST.
    """
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.delenv("ENABLE_PRICE_TITLE_PERSIST", raising=False)
    calls = _install_promotion_harness(monkeypatch, _WRONG_SKU_DB)
    svc = scs.get_comparison_service()
    out = _run(svc._get_price("Dior", "Sauvage", None, "bahrain",
                              "Dior Sauvage", nocache=False, category="fragrances"))
    assert out is not None
    assert out.get("_cache_source") == "db"
    # Flag OFF: promotion is unconditional (the pre-B1.2 behavior)
    assert len(calls["set_cached"]) == 1

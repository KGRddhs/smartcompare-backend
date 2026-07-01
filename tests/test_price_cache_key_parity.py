"""Wave-1 — cache-key parity between the warmer WRITE and the live READ.

Recon (docs/investigations/2026-06-30-warmer-recon.md) established that the
warmer and a live compare use the SAME `_get_price` ->
`build_size_aware_price_cache_key(brand, name, variant, region, search_query)`
derivation, and that `_identity_cache_token` ALREADY alias-normalizes the
identity axes. These pin exactly what collapses to one key vs what stays
distinct — so a future change to the keying is a CONSCIOUS decision, and the
"warmed key != live key" fear is bounded to the ONE residual it actually is
(a size/qualifier axis PRESENT in the verbose warmed title but ABSENT from a
terse live query).

Prod default is `ENABLE_EXACT_PRICE_GATE` ON (the composite-token path).
"""
from __future__ import annotations

import os

import pytest

from app.services.price_service import build_size_aware_price_cache_key as K


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    # Pin the prod-default composite-identity-token path for every test here.
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    yield


# --- ALIAS PARITY: different wording of the SAME sku -> ONE key --------------

def test_edt_spelled_and_abbreviated_same_size_collapse():
    verbose = K("Dior", "Sauvage Eau de Toilette", None, "bahrain",
                "Dior Sauvage Eau de Toilette 100ml")
    abbrev = K("Dior", "Sauvage EDT", None, "bahrain", "Dior Sauvage EDT 100ml")
    assert verbose == abbrev, "EDT == 'eau de toilette' (same size) must be one key"


def test_oz_and_ml_same_bottle_collapse():
    ml = K("Dior", "Sauvage EDT", None, "bahrain", "Dior Sauvage EDT 100ml")
    oz = K("Dior", "Sauvage EDT", None, "bahrain", "Dior Sauvage EDT 3.4 oz")
    assert ml == oz, "3.4 oz snaps to 100ml -> one key"


def test_storage_brand_omitted_in_identity_still_one_key_when_brand_arg_set():
    # The parser normally fills brand='Samsung' for both the verbose and terse
    # query, so a brandless search_query still keys the same.
    with_brand_word = K("Samsung", "Galaxy S24 256GB", None, "bahrain",
                        "Samsung Galaxy S24 256GB")
    brandless_query = K("Samsung", "Galaxy S24 256GB", None, "bahrain",
                        "Galaxy S24 256GB")
    assert with_brand_word == brandless_query


# --- DISCRIMINATION: distinct VARIANTS must NOT collide ----------------------

def test_distinct_concentration_differs():
    edt = K("Dior", "Sauvage EDT", None, "bahrain", "Dior Sauvage EDT 100ml")
    edp = K("Dior", "Sauvage EDP", None, "bahrain", "Dior Sauvage EDP 100ml")
    assert edt != edp


def test_distinct_storage_differs():
    s256 = K("Samsung", "Galaxy S24 256GB", None, "bahrain", "Samsung Galaxy S24 256GB")
    s128 = K("Samsung", "Galaxy S24 128GB", None, "bahrain", "Samsung Galaxy S24 128GB")
    assert s256 != s128


# --- DOCUMENTED RESIDUAL: size present vs absent diverges --------------------

def test_size_presence_vs_absence_diverges_documented_on_device_residual():
    """The warmed verbose title carries a size the terse live query omits ->
    token `edt.100ml` vs `edt` -> DIFFERENT keys. This is the on-device parity
    residual (recon note s.2): the warmer catalog must phrase queries the way
    live users do, OR the key must derive from the RESOLVED-match identity (a
    larger change deferred out of Wave 1). Pinned so a future change is
    deliberate, not accidental."""
    with_size = K("Dior", "Sauvage EDT", None, "bahrain", "Dior Sauvage EDT 100ml")
    without_size = K("Dior", "Sauvage EDT", None, "bahrain", "Dior Sauvage EDT")
    assert with_size != without_size


# --- FLAG-OFF ROLLBACK: axis-less product keys identically both ways ---------

def test_flag_off_axisless_product_keys_identically_to_flag_on(monkeypatch):
    # A plain product with NO size/concentration/qualifier axis falls back to the
    # legacy get_price_cache_key on BOTH the flag-ON and flag-OFF paths, so the
    # cache namespace for sizeless products is byte-identical (no warm-cache
    # invalidation on a rollback). This is the load-bearing rollback invariant.
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    on = K("Dior", "Sauvage", None, "bahrain", "Dior Sauvage")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    off = K("Dior", "Sauvage", None, "bahrain", "Dior Sauvage")
    assert on == off

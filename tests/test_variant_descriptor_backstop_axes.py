# -*- coding: utf-8 -*-
"""genuine-price Wave-2 B1.1 - the descriptor BACKSTOP-axes upgrade pins.

backstop_identity_verdict is THE shared weak-chokepoint identity decision for
BOTH the display enforce block (is_price_showable) and the cache-read
_cache_price_identity_ok. This file pins:

  * FLAG-OFF byte-identity: backstop_identity_verdict == the legacy pair
    (_backstop_identity_ok and not _category_type_added) on a broad sample incl.
    the residual-census strings.
  * FLAG-ON new-axis closures BOTH directions (gender both-stated / femme-query /
    flanker / generation-add / prefixed clothing-size / model-year), reproduced
    at BOTH weak chokepoints (cache-read + display).
  * FLAG-ON over-rejection guards: the correct base products the new axes must
    NEVER pend (Black Opium For Women / Oud Wood / AirPods Pro USB-C / Dual SIM 2
    Nano / Anthelios SPF / descriptive supplement titles).

Free-unit suite: no network, no marks. ASCII-only source (Windows discipline).
"""

import pytest

from app.services import price_service as ps
from app.services.structured_comparison_service import _cache_price_identity_ok


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _axes_on(monkeypatch):
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")


def _axes_off(monkeypatch):
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "false")


_PDP = "https://shop.example.com/products/item-123"


def _price(title, **kw):
    base = {"amount": 95.0, "currency": "BHD", "title": title, "url": _PDP,
            "in_stock": True, "source_method": "local_bhd"}
    base.update(kw)
    return base


def _legacy_pair(q, t, cat):
    return (ps._backstop_identity_ok(q, t, cat)
            and not ps._category_type_added(q, t, cat))


def _display(q, title, cat, amount=95.0):
    return ps.is_price_showable(q, _price(title, amount=amount), cat,
                                enforce_correctness=True)


def _cacheread(q, title, cat):
    # brand="" so query_name == q (matches the display product_name)
    return _cache_price_identity_ok(_price(title), "", q, cat)


# ---------------------------------------------------------------------------
# FLAG-OFF byte-identity (default) — backstop_identity_verdict == legacy pair
# ---------------------------------------------------------------------------
_BYTE_IDENTITY_SAMPLE = [
    ("Dior Sauvage", "Dior Sauvage Elixir", "fragrances"),
    ("Dior Sauvage", "Dior Sauvage Parfum", "fragrances"),
    ("Dior Sauvage", "Dior Sauvage Eau de Parfum", "fragrances"),
    ("Carolina Herrera Good Girl", "Good Girl Supreme", "fragrances"),
    ("Versace Eros Pour Homme", "Versace Eros Pour Femme", "fragrances"),
    ("Versace Eros Pour Femme", "Versace Eros Eau de Parfum 100ml", "fragrances"),
    ("YSL Black Opium", "YSL Black Opium For Women EDP", "fragrances"),
    ("Tom Ford Oud Wood", "Tom Ford Private Blend Oud Wood Eau de Parfum", "fragrances"),
    ("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics"),
    ("Apple AirPods Pro", "Apple AirPods Pro (USB-C)", "electronics"),
    ("Apple iPhone SE 2020", "Apple iPhone SE (2022)", "electronics"),
    ("Samsung Galaxy S24", "Samsung Galaxy S24 FE", "electronics"),
    ("Samsung Galaxy", "Samsung Galaxy Dual SIM 2 Nano", "electronics"),
    ("Uniqlo Oxford Shirt Size M", "Uniqlo Oxford Shirt Size XL", "fashion"),
    ("Nike Air Force 1", "Nike Air Max 1", "fashion"),
    ("Kiehl's Ultra Facial Cream", "Kiehl's Ultra Facial Cream SPF 30", "skincare"),
]


@pytest.mark.parametrize("q,t,cat", _BYTE_IDENTITY_SAMPLE)
def test_flag_off_byte_identity(monkeypatch, q, t, cat):
    _axes_off(monkeypatch)
    ok, reason = ps.backstop_identity_verdict(q, t, cat)
    legacy = _legacy_pair(q, t, cat)
    assert ok is legacy
    assert (reason is None) is legacy  # reason "not_exact" only when it fails


def test_flag_off_reason_is_plain_not_exact(monkeypatch):
    # A legacy-rejected pair (flagship flanker) stamps the exact legacy value.
    _axes_off(monkeypatch)
    ok, reason = ps.backstop_identity_verdict("Dior Sauvage", "Dior Sauvage Parfum",
                                              "fragrances")
    assert ok is False
    assert reason == "not_exact"


def test_flag_off_display_guard_rejected_unchanged(monkeypatch):
    _axes_off(monkeypatch)
    p = _price("Dior Sauvage Parfum")
    assert ps.is_price_showable("Dior Sauvage", p, "fragrances",
                                enforce_correctness=True) is False
    assert p["guard_rejected"] == "not_exact"


# ---------------------------------------------------------------------------
# FLAG-ON — new-axis LEAK closures, BOTH weak chokepoints
# ---------------------------------------------------------------------------
def test_flanker_rejected_both_chokepoints(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Dior Sauvage", "Dior Sauvage Elixir", "fragrances") is False
    assert _cacheread("Dior Sauvage", "Dior Sauvage Elixir", "fragrances") is False
    assert _display("Carolina Herrera Good Girl", "Carolina Herrera Good Girl Supreme",
                    "fragrances") is False
    assert _cacheread("Carolina Herrera Good Girl", "Carolina Herrera Good Girl Supreme",
                      "fragrances") is False


def test_flanker_granular_reason(monkeypatch):
    _axes_on(monkeypatch)
    p = _price("Dior Sauvage Elixir")
    assert ps.is_price_showable("Dior Sauvage", p, "fragrances",
                                enforce_correctness=True) is False
    assert p["guard_rejected"] == "not_exact:flanker"


def test_gender_both_stated_rejected_both_chokepoints(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Versace Eros Pour Homme", "Versace Eros Pour Femme",
                    "fragrances") is False
    assert _cacheread("Versace Eros Pour Homme", "Versace Eros Pour Femme",
                      "fragrances") is False


def test_femme_query_unconfirmed_rejected_both_chokepoints(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Versace Eros Pour Femme", "Versace Eros Eau de Parfum 100ml",
                    "fragrances") is False
    assert _cacheread("Versace Eros Pour Femme", "Versace Eros Eau de Parfum 100ml",
                      "fragrances") is False


def test_generation_add_rejected_both_chokepoints(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics") is False
    assert _cacheread("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics") is False


def test_generation_reverse_direction_tolerated(monkeypatch):
    # ADD direction only: query PINS the generation, candidate omits it -> the
    # backstop tolerates (a bare-int omission stays a selection-side concern).
    _axes_on(monkeypatch)
    assert _display("Apple AirPods Pro 2", "Apple AirPods Pro", "electronics") is True


def test_prefixed_clothing_size_rejected(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Uniqlo Oxford Shirt Size M", "Uniqlo Oxford Shirt Size XL",
                    "fashion") is False
    assert _cacheread("Uniqlo Oxford Shirt Size M", "Uniqlo Oxford Shirt Size XL",
                      "fashion") is False


def test_model_year_both_stated_rejected(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Apple iPhone SE 2020", "Apple iPhone SE (2022)", "electronics") is False
    assert _cacheread("Apple iPhone SE 2020", "Apple iPhone SE (2022)",
                      "electronics") is False


# ---------------------------------------------------------------------------
# FLAG-ON — OVER-REJECTION guards (correct base products must STILL show/cache)
# ---------------------------------------------------------------------------
def test_black_opium_for_women_still_accepted(monkeypatch):
    # query gender unstated + candidate women = the tolerated base direction.
    _axes_on(monkeypatch)
    assert _display("YSL Black Opium", "YSL Black Opium For Women EDP", "fragrances") is True
    assert _cacheread("YSL Black Opium", "YSL Black Opium For Women EDP",
                      "fragrances") is True


def test_oud_wood_base_name_not_flanker_rejected(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Tom Ford Oud Wood",
                    "Tom Ford Private Blend Oud Wood Eau de Parfum", "fragrances") is True


def test_airpods_pro_usbc_not_generation_rejected(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Apple AirPods Pro", "Apple AirPods Pro (USB-C)", "electronics") is True


def test_dual_sim_2_nano_not_generation_rejected(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Samsung Galaxy S24", "Samsung Galaxy S24 Dual SIM 2 Nano 256GB",
                    "electronics") is True


def test_anthelios_spf_unaffected(monkeypatch):
    # one-sided SPF stays a HELD tolerated tradeoff — the new axes must not touch it.
    _axes_on(monkeypatch)
    assert _display("La Roche-Posay Anthelios",
                    "La Roche-Posay Anthelios SPF 50 Invisible Fluid", "skincare") is True


def test_descriptive_supplement_title_unaffected(monkeypatch):
    _axes_on(monkeypatch)
    assert _display("Now B-Complex", "Now B-Complex with B12 B6 Folate Biotin",
                    "supplements", amount=5.0) is True


def test_year_one_sided_tolerated(monkeypatch):
    # query no year, candidate annotation year -> one-sided, tolerated at the backstop.
    _axes_on(monkeypatch)
    assert _display("Apple iPad Air M3 128GB", "Apple iPad Air (2025) M3 128GB",
                    "electronics") is True

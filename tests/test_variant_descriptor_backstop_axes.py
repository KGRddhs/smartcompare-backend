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


def test_femme_query_unconfirmed_now_tolerated_at_backstop(monkeypatch):
    # B1-FIX ruling B REVERSES the prior B1.1 behaviour: the axis-only backstop
    # no longer rejects a feminine-query-unconfirmed pair (over-rejected correct
    # women's bases). The selection gate + should_cache_price still enforce it,
    # so the warmer write path is unaffected. See
    # test_gender_femme_query_unconfirmed_now_tolerated for the broader set.
    _axes_on(monkeypatch)
    assert _display("Versace Eros Pour Femme", "Versace Eros Eau de Parfum 100ml",
                    "fragrances") is True
    assert _cacheread("Versace Eros Pour Femme", "Versace Eros Eau de Parfum 100ml",
                      "fragrances") is True


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


# ---------------------------------------------------------------------------
# B1-FIX RULING A — GENERATION AXIS over-rejection bounds
# ---------------------------------------------------------------------------
# A1: a "(Nth generation)"/"(Nth gen)" PARENTHETICAL annotation is release
# padding (like "(2025)"), NOT a discriminator -> the ADD check ignores it.
_GEN_A1_TOLERATE = [
    ("Apple iPad Air M3", "Apple iPad Air M3 (4th generation)"),
    ("Apple Watch SE", "Apple Watch SE (2nd generation) GPS"),
    ("Google Nest Mini", "Google Nest Mini (2nd Generation)"),
    ("Amazon Fire TV Stick", "Amazon Fire TV Stick 4K (2nd Gen)"),
]


@pytest.mark.parametrize("q,t", _GEN_A1_TOLERATE)
def test_gen_A1_parenthetical_ordinal_is_padding(monkeypatch, q, t):
    _axes_on(monkeypatch)
    assert _display(q, t, "electronics") is True
    assert _cacheread(q, t, "electronics") is True


# A2: a bare inline digit 1-4 FOLLOWED by a quantity/spec/measurement noun is
# NOT a generation -> tolerate.
_GEN_A2_TOLERATE = [
    ("Instant Pot Mini", "Instant Pot Mini 3 Quart"),
    ("Garmin Watch", "Garmin Watch 3 ATM"),
    ("Apple iPad Pro", "Apple iPad Pro 4 Cameras"),
    ("DeWalt Max", "DeWalt Max 4 Ah"),
    ("Belkin Series Cable", "Belkin Series 2 Meter Cable"),
    ("Apple Watch", "Apple Watch 2 Pack"),
    ("Apple Pencil", "Apple Pencil 2 Pack"),
]


@pytest.mark.parametrize("q,t", _GEN_A2_TOLERATE)
def test_gen_A2_quantity_noun_not_generation(monkeypatch, q, t):
    _axes_on(monkeypatch)
    assert _display(q, t, "electronics") is True
    assert _cacheread(q, t, "electronics") is True


def test_gen_inline_add_still_rejects(monkeypatch):
    # The leak the axis exists for: an INLINE bare generation int the candidate
    # adds (title-terminal or followed by a non-quantity token) STILL rejects.
    _axes_on(monkeypatch)
    assert _display("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics") is False
    assert _cacheread("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics") is False
    # inline int followed by a NON-quantity token also fires.
    assert _display("Apple iPad Air", "Apple iPad Air 4 Wi-Fi", "electronics") is False


# ---------------------------------------------------------------------------
# B1-FIX2 — GENERATION count-noun exclusion (colors/sensors/tips/...)
# A bare digit that COUNTS the following marketing/spec noun ("AirPods Max
# 2 Colors" = 2 colorways, "... 2 Sensors" = 2 sensors) is a QUANTITY, not a
# generation -> tolerate. Convergence of the B1-fix re-sweep blind spot.
# ---------------------------------------------------------------------------
_GEN_B1FIX2_TOLERATE = [
    ("Apple AirPods Max", "Apple AirPods Max 2 Colors"),
    ("Apple AirPods Max", "Apple AirPods Max 2 Colours"),
    ("Apple AirPods Max", "Apple AirPods Max 2 Sensors"),
    ("Apple AirPods Pro", "Apple AirPods Pro 2 Tips"),
    ("Apple AirPods Pro", "Apple AirPods Pro 2 Ear Tips"),
    ("Sonos Max", "Sonos Max 2 Speakers"),
    ("Apple Watch", "Apple Watch 2 Bands"),
    ("Google Pixel", "Google Pixel 2 Options"),
]


@pytest.mark.parametrize("q,t", _GEN_B1FIX2_TOLERATE)
def test_gen_B1fix2_count_noun_not_generation(monkeypatch, q, t):
    _axes_on(monkeypatch)
    assert _display(q, t, "electronics") is True
    assert _cacheread(q, t, "electronics") is True


def test_gen_B1fix2_terminal_inline_int_still_rejects(monkeypatch):
    # The closure pins from B1fix-A must STILL fire: a title-terminal bare int,
    # or one followed by a NON-count token, is a real generation.
    _axes_on(monkeypatch)
    assert _display("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics") is False
    assert _cacheread("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics") is False
    assert _display("Amazon Echo Dot", "Amazon Echo Dot 3", "electronics") is False
    assert _display("Apple Pencil", "Apple Pencil 2", "electronics") is False
    assert _display("Samsung Galaxy Watch", "Samsung Galaxy Watch 4 Classic",
                    "electronics") is False
    assert _display("Apple iPad Air", "Apple iPad Air 4 Wi-Fi", "electronics") is False


# ---------------------------------------------------------------------------
# B1-FIX RULING B — GENDER contradiction-only at the backstop
# ---------------------------------------------------------------------------
_GENDER_B_TOLERATE = [
    ("YSL Black Opium Pour Femme", "YSL Black Opium Eau de Parfum 90ml"),
    ("Chanel Coco Mademoiselle For Women", "Chanel Coco Mademoiselle EDP"),
    ("Lancome La Vie Est Belle Pour Femme", "Lancome La Vie Est Belle EDP 100ml"),
]


@pytest.mark.parametrize("q,t", _GENDER_B_TOLERATE)
def test_gender_femme_query_unconfirmed_now_tolerated(monkeypatch, q, t):
    # RULING B: the axis-only backstop drops the feminine-query-unconfirmed
    # asymmetry (over-rejected correct women's bases). The selection-side check
    # still owns the warmer write path.
    _axes_on(monkeypatch)
    assert _display(q, t, "fragrances") is True
    assert _cacheread(q, t, "fragrances") is True


def test_gender_contradiction_still_rejects(monkeypatch):
    # Both-stated gender CONTRADICTION stays enforced at the backstop.
    _axes_on(monkeypatch)
    assert _display("Versace Eros Pour Homme", "Versace Eros Pour Femme",
                    "fragrances") is False
    assert _cacheread("Versace Eros Pour Homme", "Versace Eros Pour Femme",
                      "fragrances") is False


# ---------------------------------------------------------------------------
# B1-FIX RULING C — FLANKER ADD-direction-only at the backstop
# ---------------------------------------------------------------------------
def test_flanker_omit_now_tolerated(monkeypatch):
    # RULING C: query carries a flanker word the candidate omits (a canonical
    # base-line name, "Dior Homme Intense" -> "Dior Homme") -> tolerate at the
    # backstop (OMIT direction).
    _axes_on(monkeypatch)
    assert _display("Dior Homme Intense", "Dior Homme", "fragrances") is True
    assert _cacheread("Dior Homme Intense", "Dior Homme", "fragrances") is True


def test_flanker_add_still_rejects(monkeypatch):
    # ADD direction (candidate adds a flanker) STILL rejects.
    _axes_on(monkeypatch)
    assert _display("Dior Sauvage", "Dior Sauvage Elixir", "fragrances") is False
    assert _cacheread("Dior Sauvage", "Dior Sauvage Elixir", "fragrances") is False
    assert _display("Carolina Herrera Good Girl", "Carolina Herrera Good Girl Supreme",
                    "fragrances") is False


def test_flanker_both_present_matches(monkeypatch):
    # Both sides carry the same flanker -> matches.
    _axes_on(monkeypatch)
    assert _display("Carolina Herrera Good Girl Supreme",
                    "Carolina Herrera Good Girl Supreme", "fragrances") is True

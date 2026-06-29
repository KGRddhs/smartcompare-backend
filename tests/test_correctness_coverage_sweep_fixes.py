"""Coverage-driven sweep (post-PR#9) — leaks found by enumerating real products x every
axis x both directions and reproducing through the RUNTIME selectors the orchestrator
calls. 14 prior reviews (hypothesis-driven) missed these; a coverage sweep falsified the
"0 CRIT/HIGH leak" claim. Each test below reproduces through the SAME function the
orchestrator runs (_selection_match / should_cache_price / is_price_showable).

FIXED (a different/sibling SKU must now PEND), each paired with a GUARD proving the fix
opens no new over-rejection:
  - grocery flavour ADD        Cheerios -> Cheerios Chocolate   (asymmetric _flavour_mismatch)
  - supplement flavour CONTRA  Unflavored -> Fruit Punch / Cookies -> Cream  (+ tokens)
  - supplement 'multi' blend   Collagen Peptides -> Multi Collagen Peptides  (un-padded 'multi')
  - makeup shade-LINE          SoftMatte 240 -> Hydrating 240 (+ Glow, Dewy+Smooth)  (line guard)
  - fashion 'SE'               Air Max 90 <-> Air Max 90 SE     (kept short qualifier)
  - electronics accessory      should_cache_price(Galaxy S24, ...Charger/Adapter)  (cache gate)

HELD — INTENTIONALLY NOT CHANGED (a real leak whose token-only fix re-breaks a documented
worse case; pinned so the accepted trade can only change by a conscious edit):
  - fragrance gender flanker   base query -> Pour Femme   (symmetric rule mass-over-rejects
                               women's-base; see price_service.py:3584 + R6 pin)
  - skincare one-sided SPF     Cream -> Cream SPF 30      (asymmetric mass-over-rejects every
                               inherent-SPF sunscreen; see test_R6_overrej_skincare_spf_*)

HELD — DEFERRED real leaks (xfail: the DESIRED reject, not yet implemented because the safe
fix needs more than a token rule):
  - display backstop axis-only Sauvage -> Sauvage Elixir / AF1 -> Air Max 1  (live-path risk)
  - cross-unit size            340g -> 177ml             (g<->ml is density-ambiguous)
  - ReDoS-cap truncation       >512-char title drops the trailing storage axis (near-zero reach)
"""
import pytest

from app.services.price_service import (
    _selection_match,
    should_cache_price,
    is_price_showable,
)


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _m(q, c, cat, brand=""):
    return _selection_match(q, c, cat, candidate_brand=brand)


_PDP = "https://shop.example.com/products/item-123"


def _price(title, **kw):
    base = {"amount": 5.0, "currency": "BHD", "title": title, "url": _PDP,
            "in_stock": True, "source_method": "local_bhd"}
    base.update(kw)
    return base


# ===========================================================================
# FIXED — leaks that must now PEND (reproduced through the runtime selector)
# ===========================================================================
def test_grocery_flavour_add_rejected():
    # 'chocolate' is a generic grocery noun AND a flavour — the one-sided ADD slipped both
    # the contradiction axis and the variant-add guard before the asymmetric fix.
    assert _m("Cheerios", "Cheerios Chocolate", "grocery", "Cheerios") is False
    assert _m("Pepsi", "Pepsi Mango", "grocery", "Pepsi") is False


def test_supplement_flavour_contradiction_rejected():
    assert _m("Creatine Monohydrate Unflavored", "Creatine Monohydrate Fruit Punch",
              "supplements") is False
    assert _m("Creatine Monohydrate Cookies", "Creatine Monohydrate Cream",
              "supplements") is False


def test_supplement_multi_blend_rejected():
    # 'multi' is the distinctive blend modifier (single-source vs multi-collagen) — no longer padding.
    assert _m("Collagen Peptides", "Multi Collagen Peptides", "supplements") is False


def test_makeup_shade_line_rejected():
    # A formula/finish LINE word added over a shared shade NUMBER = a different product line.
    assert _m("Fenty Pro Filt'r Soft Matte Foundation 240",
              "Fenty Pro Filt'r Hydrating Longwear Foundation 240", "makeup", "Fenty") is False
    assert _m("L'Oreal Infallible Matte Foundation 130",
              "L'Oreal Infallible Glow Foundation 130", "makeup", "L'Oreal") is False
    assert _m("Maybelline Fit Me Foundation 128",
              "Maybelline Fit Me Dewy + Smooth Foundation 128", "makeup", "Maybelline") is False


def test_fashion_se_qualifier_rejected_both_directions():
    assert _m("Nike Air Max 90", "Nike Air Max 90 SE", "fashion", "Nike") is False
    assert _m("Nike Air Max 90 SE", "Nike Air Max 90", "fashion", "Nike") is False


def test_electronics_accessory_not_cached():
    # The cache-WRITE gate must reject a charger/adapter under the device query (the shared
    # matcher strips them as padding; select_best + is_price_showable already reject them).
    assert should_cache_price("Galaxy S24", _price("Samsung Galaxy S24 Charger", brand="Samsung"),
                              "electronics") is False
    assert should_cache_price("Galaxy S24", _price("Samsung Galaxy S24 Adapter", brand="Samsung"),
                              "electronics") is False


# ===========================================================================
# GUARDS — the fixes must NOT introduce these over-rejections
# ===========================================================================
def test_guard_supplement_one_sided_flavour_tolerated():
    # ISO100 -> ISO100 Vanilla is the SAME product (flavour is a sub-choice) — design intent.
    assert _m("Dymatize ISO100", "Dymatize ISO100 Vanilla 5lb", "supplements", "Dymatize") is True


def test_guard_makeup_shade_name_tolerated():
    assert _m("Maybelline Fit Me 240", "Maybelline Fit Me 240 Soft Sand", "makeup", "Maybelline") is True


def test_guard_grocery_generic_noun_tolerated():
    assert _m("Cheerios", "Cheerios Cereal", "grocery", "Cheerios") is True


def test_guard_fashion_colourway_tolerated():
    assert _m("Nike Air Max 90", "Nike Air Max 90 White Black", "fashion", "Nike") is True


def test_guard_multivitamin_class_noun_still_padding():
    # Only the bare blend-modifier 'multi' was un-padded; 'multivitamin' stays the tolerated class noun.
    assert _m("Centrum", "Centrum Multivitamin", "supplements", "Centrum") is True


def test_guard_accessory_query_accepts_accessory():
    # When the QUERY itself is the accessory, a charger listing is a valid match (both accessory).
    assert should_cache_price("Galaxy S24 Charger",
                              _price("Samsung Galaxy S24 Charger", brand="Samsung"),
                              "electronics") is True


# ===========================================================================
# HELD — deliberate tradeoffs (PIN the accepted behaviour; a leak, but the token-only
# fix re-breaks a worse documented case). Change only by a conscious edit.
# ===========================================================================
def test_held_gender_flanker_accepted_tradeoff():
    # Symmetrizing mass-over-rejects women's-base fragrances (Black Opium -> For Women).
    assert _m("Sauvage", "Dior Sauvage Pour Femme EDP", "fragrances", "Dior") is True
    assert _m("Versace Eros", "Versace Eros Pour Femme Eau de Parfum 100ml", "other", "Versace") is True


def test_held_skincare_one_sided_spf_accepted_tradeoff():
    # Asymmetric SPF mass-over-rejects inherent-SPF sunscreens (Anthelios). See R6 pin.
    assert _m("Kiehl's Ultra Facial Cream", "Kiehl's Ultra Facial Cream SPF 30", "skincare", "Kiehl's") is True


# ===========================================================================
# HELD — deferred real leaks (xfail asserts the DESIRED behaviour; not yet safely fixable)
# ===========================================================================
@pytest.mark.xfail(reason="display chokepoint uses the axis-only backstop; full-matcher "
                          "hardening is a live-path over-rejection risk, deferred to warmer reactivation",
                   strict=True)
def test_deferred_display_backstop_flanker():
    assert is_price_showable("Dior Sauvage",
                             _price("Dior Sauvage Elixir", amount=40.0), "fragrances",
                             enforce_correctness=True) is False


@pytest.mark.xfail(reason="cross-unit g<->ml is density-ambiguous (340g ~= 340ml water-based); "
                          "a safe tolerance needs more than a token rule",
                   strict=True)
def test_deferred_cross_unit_size():
    assert _m("CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream 177ml",
              "skincare", "CeraVe") is False


@pytest.mark.xfail(reason="the 512-char ReDoS cap drops a trailing storage axis; reachability "
                          "is near-zero (real titles < 200 chars)",
                   strict=True)
def test_deferred_redos_cap_truncation():
    long = "9" * 600
    assert _m("Galaxy " + long + " 256GB", "Galaxy " + long + " 512GB",
              "electronics", "Samsung") is False

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
  - ReDoS-cap truncation       >512-char title drops the trailing storage axis (near-zero reach)

NOTE (census P6a, no longer HELD): cross-unit size (340g -> 177ml, g<->ml density-ambiguous)
is now ENFORCED fail-closed (see test_cross_unit_size_pended below) — it was moved off the
deferred-xfail list. Wave-2 B2 additionally closes the two SUPPLEMENT over-rejection census
classes (flag-gated behind ENABLE_VARIANT_DESCRIPTOR_AXES; flag-OFF byte-identical):
  - C1 acronym-constituent  Optimum ZMA -> ...ZMA Zinc Magnesium Aspartate  (curated table)
  - C2 hyphen-vs-space      Nordic Naturals Omega-3 <-> Omega 3            (digit-hyphen fold)
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
    # 'chocolate'/'cheese' are generic grocery nouns AND flavours — the one-sided ADD slipped
    # both the contradiction axis and the variant-add guard before the asymmetric fix.
    assert _m("Cheerios", "Cheerios Chocolate", "grocery", "Cheerios") is False
    assert _m("Pepsi", "Pepsi Mango", "grocery", "Pepsi") is False
    assert _m("Pringles Original", "Pringles Cheese", "grocery", "Pringles") is False  # re-sweep LOW


def test_supplement_flavour_contradiction_rejected():
    assert _m("Creatine Monohydrate Unflavored", "Creatine Monohydrate Fruit Punch",
              "supplements") is False
    assert _m("Creatine Monohydrate Cookies", "Creatine Monohydrate Cream",
              "supplements") is False


def test_supplement_multi_blend_rejected():
    # 'multi' is the distinctive blend modifier (single-source vs multi-collagen) — no longer padding.
    assert _m("Collagen Peptides", "Multi Collagen Peptides", "supplements") is False


def test_makeup_shade_line_rejected():
    # A DIFFERENT formula line stated on BOTH sides (Soft Matte vs Hydrating; Matte vs Glow)
    # rejects via _finish_mismatch (glow/hydrating are now finish tokens). A ONE-SIDED formula
    # add ("Fit Me -> Dewy+Smooth") is the accepted trade — see test_held_makeup_one_sided_*.
    assert _m("Fenty Pro Filt'r Soft Matte Foundation 240",
              "Fenty Pro Filt'r Hydrating Longwear Foundation 240", "makeup", "Fenty") is False
    assert _m("L'Oreal Infallible Matte Foundation 130",
              "L'Oreal Infallible Glow Foundation 130", "makeup", "L'Oreal") is False


def test_fashion_se_qualifier_rejected_both_directions():
    assert _m("Nike Air Max 90", "Nike Air Max 90 SE", "fashion", "Nike") is False
    assert _m("Nike Air Max 90 SE", "Nike Air Max 90", "fashion", "Nike") is False


def test_fashion_spelled_edition_rejected():
    # Re-sweep HIGH: spelled "Special/Limited Edition" (the common GCC wording) leaked because
    # 'special'/'edition' were stripped as colour-edition tokens. Now normalized to one token.
    assert _m("Nike Air Force 1", "Nike Air Force 1 Special Edition", "fashion", "Nike") is False
    assert _m("Nike Air Max 90", "Nike Air Max 90 Limited Edition", "fashion", "Nike") is False


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


def test_guard_makeup_one_sided_formula_descriptive_tolerated():
    # Re-sweep: a one-sided formula word on the candidate over a shared shade number is
    # descriptive, not a line swap -> accept (avoids mass over-rejection of common Fit Me titles).
    assert _m("Maybelline Fit Me 310", "Maybelline Fit Me 310 Sun Beige Smooth Coverage", "makeup", "Maybelline") is True
    assert _m("Maybelline Fit Me 220", "Maybelline Fit Me 220 Natural Beige Glow", "makeup", "Maybelline") is True


def test_guard_fashion_se_alias_unified():
    # "SE" and the spelled "Special Edition" are the SAME edition SKU -> must MATCH.
    assert _m("Nike Air Force 1 SE", "Nike Air Force 1 Special Edition", "fashion", "Nike") is True


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
    # External review #4 RE-CONFIRMED this HELD: an SPF-add fail-close with a sunscreen
    # carve-out was implemented and reverted — the carve-out cannot cover the unbounded
    # set of sunscreen names (a coverage sweep over-rejected Vichy Capital Soleil /
    # Bioderma Photoderm / Banana Boat …), and the leak it prevents (base cream vs SPF
    # variant) is low-harm. Doing better needs structured variant metadata.
    assert _m("Kiehl's Ultra Facial Cream", "Kiehl's Ultra Facial Cream SPF 30", "skincare", "Kiehl's") is True


def test_held_makeup_one_sided_formula_line_accepted_tradeoff():
    # "Fit Me Foundation" -> "Fit Me Dewy + Smooth" is a real line difference but a ONE-SIDED
    # formula add; rejecting it mass-over-rejects common Fit Me descriptive titles (re-sweep).
    # The clear both-stated-different case (Soft Matte vs Hydrating) IS still rejected above.
    assert _m("Maybelline Fit Me Foundation 128",
              "Maybelline Fit Me Dewy + Smooth Foundation 128", "makeup", "Maybelline") is True


# ===========================================================================
# FIXED — external review #4 fail-closes (were deferred xfails; now enforced).
# ===========================================================================
def test_display_backstop_flagship_flanker_pended():
    # The display chokepoint adds a bounded flagship-concentration / supplement-type ADD
    # check (NOT the full superset, which over-rejected correct descriptive titles), so a
    # FLAGSHIP flanker that bypassed the primary gate ("Dior Sauvage" -> "Dior Sauvage
    # Parfum") is PENDED at the backstop.
    assert is_price_showable("Dior Sauvage",
                             _price("Dior Sauvage Parfum", amount=40.0), "fragrances",
                             enforce_correctness=True) is False


def test_display_backstop_same_token_flanker(monkeypatch):
    # Wave-2 B1.1b: the same-token concentration flanker ('Sauvage Elixir') is now
    # closed at the display backstop by the BOUNDED curated flanker_markers axis
    # (NOT the full superset, which over-rejected descriptive titles) — gated ON by
    # ENABLE_VARIANT_DESCRIPTOR_AXES. Flag OFF stays the documented leak (byte-identical
    # rollback); flag ON pends it. Was xfail-strict pre-Wave-2.
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    assert is_price_showable("Dior Sauvage",
                             _price("Dior Sauvage Elixir", amount=40.0), "fragrances",
                             enforce_correctness=True) is False
    # And the flag-OFF rollback still leaks (the accepted pre-Wave-2 behaviour) —
    # proving the closure is entirely behind the flag.
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "false")
    assert is_price_showable("Dior Sauvage",
                             _price("Dior Sauvage Elixir", amount=40.0), "fragrances",
                             enforce_correctness=True) is True


def test_cross_unit_size_pended():
    # Cross-unit g<->ml is unverifiable equivalence (density-ambiguous) -> fail-closed PEND.
    assert _m("CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream 177ml",
              "skincare", "CeraVe") is False


# ===========================================================================
# HELD — deferred real leak (xfail asserts the DESIRED behaviour; not yet safely fixable)
# ===========================================================================
@pytest.mark.xfail(reason="the 512-char ReDoS cap drops a trailing storage axis; reachability "
                          "is near-zero (real titles < 200 chars)",
                   strict=True)
def test_deferred_redos_cap_truncation():
    long = "9" * 600
    assert _m("Galaxy " + long + " 256GB", "Galaxy " + long + " 512GB",
              "electronics", "Samsung") is False


# ===========================================================================
# Parallel review-fix re-sweep (HEAD 562144c) — the bounded display backstop's
# _supplement_type_added over-rejected MULTI-CONSTITUENT supplement descriptive titles
# (B-Complex / Multivitamin / Prenatal enumerating their own contents) on the hero category.
# Fix: a multi-constituent QUERY excludes the bare element/vitamin constituent names from the
# type-add, recovering the descriptive titles WITHOUT leaking a single-element COMBO add.
# ===========================================================================
def _ips_supp(name, title, amount=5.0):
    return is_price_showable(name, _price(title, source_method="local_bhd", amount=amount),
                             "supplements", enforce_correctness=True)


def test_supplement_multi_constituent_enumeration_showable():
    # A descriptive title enumerating a multi-constituent product's own contents = SAME SKU.
    assert _ips_supp("Now B-Complex", "Now B-Complex with B12 B6 Folate Biotin") is True
    assert _ips_supp("Nature Made Prenatal", "Nature Made Prenatal Multi with Folic Acid and Iron") is True
    assert _ips_supp("Centrum Multivitamin", "Centrum Multivitamin with Iron Zinc") is True
    assert _ips_supp("One A Day Multivitamin", "One A Day Multivitamin Calcium Magnesium Zinc") is True


def test_supplement_combo_and_form_still_pend():
    # The fix must NOT leak: a SINGLE-constituent query + an added element = a different COMBO
    # SKU; a salt-form / formulation add stays a discriminator on both.
    assert _ips_supp("Calcium", "Now Calcium Magnesium Zinc") is False         # combo
    assert _ips_supp("Vitamin D3", "Vitamin D3 with Zinc") is False            # combo
    assert _ips_supp("Magnesium", "Magnesium Citrate") is False                # salt form
    assert _ips_supp("Magnesium", "Magnesium Glycinate") is False              # salt form
    assert _ips_supp("Whey Protein", "Optimum Whey Protein Isolate") is False  # formulation type


def test_supplement_acronym_constituent_flag_conditional(monkeypatch):
    # Wave-2 B2a (C1): a curated acronym->constituents table folds a descriptively-titled
    # correct product (Optimum ZMA -> "...ZMA Zinc Magnesium Aspartate") so it DISPLAYS —
    # gated ON by ENABLE_VARIANT_DESCRIPTOR_AXES. Flag OFF stays the documented over-rejection
    # (byte-identical rollback); flag ON accepts the correct product.
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    assert _ips_supp("Optimum ZMA", "Optimum ZMA Zinc Magnesium Aspartate 180 Caps") is True
    # And the flag-OFF default still over-rejects (the accepted pre-Wave-2 residual) —
    # proving the fold is entirely behind the flag.
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "false")
    assert _ips_supp("Optimum ZMA", "Optimum ZMA Zinc Magnesium Aspartate 180 Caps") is False


def test_supplement_acronym_calmag_flag_on(monkeypatch):
    # Same class — Cal-Mag / CalMag acronym query vs a title enumerating calcium+magnesium.
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    assert _ips_supp("Now CalMag", "Now CalMag Calcium Magnesium 240 Caps") is True
    assert _ips_supp("Now Cal-Mag", "Now Cal-Mag Calcium Magnesium 240 Caps") is True


def test_supplement_acronym_combo_leak_still_rejects_both_flags(monkeypatch):
    # The C1 fold must NOT reopen the combo-add leak: a SINGLE-ELEMENT query (Calcium is NOT
    # an acronym in the table) + an added element = a different COMBO SKU, both flags.
    for val in ("true", "false"):
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", val)
        assert _ips_supp("Calcium", "Now Calcium Magnesium Zinc") is False
        assert _ips_supp("Magnesium", "Magnesium Citrate") is False


# ===========================================================================
# Wave-2 B2b (C2) — hyphen-vs-space digit-adjacent fold. "Omega-3" == "Omega 3" == "Omega3"
# (and the same class B-12/B12/B 12, Co-Q10/CoQ10, D-3/D3). Flag-gated; the WH-1000XM5
# electronics guard must STILL collapse equal (hyphen-removal glue, unrelated to the fold).
# ===========================================================================
def test_omega3_hyphen_space_match_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    assert _m("Nordic Naturals Omega-3", "Nordic Naturals Omega 3", "supplements") is True
    assert _m("Nordic Naturals Omega 3", "Nordic Naturals Omega-3", "supplements") is True
    assert _m("Nordic Naturals Omega3", "Nordic Naturals Omega 3", "supplements") is True
    # B-12 / B 12 / B12 same class
    assert _m("Now B-12", "Now B 12", "supplements") is True
    assert _m("Now B 12", "Now B12", "supplements") is True


def test_omega3_hyphen_space_flag_off_residual(monkeypatch):
    # Flag OFF stays the documented over-rejection (byte-identical rollback).
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "false")
    assert _m("Nordic Naturals Omega-3", "Nordic Naturals Omega 3", "supplements") is False


def test_wh1000xm5_hyphen_guard_still_matches_both_flags(monkeypatch):
    # CRITICAL GUARD: the digit-hyphen fold must NOT break the model-code hyphen-removal
    # collapse (WH-1000XM5 == WH1000XM5 == WH-1000-XM5) and must NOT bridge unrelated tokens.
    for val in ("true", "false"):
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", val)
        assert _m("Sony WH-1000XM5", "Sony WH1000XM5", "electronics", "Sony") is True
        assert _m("Sony WH1000XM5", "Sony WH-1000XM5", "electronics", "Sony") is True
        assert _m("Sony WH-1000-XM5", "Sony WH1000XM5", "electronics", "Sony") is True

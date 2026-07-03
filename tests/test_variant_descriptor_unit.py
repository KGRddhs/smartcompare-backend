# -*- coding: utf-8 -*-
"""genuine-price Wave-2 A1 - direct unit pins for the VariantDescriptor layer.

Complements tests/test_variant_descriptor_golden.py (the 1149-case equivalence
replay): here we pin the NEW public surface directly -
  * extract_variant_descriptor field extraction (one representative product per
    category, incl. the Phase-A structured-first provenance TODO),
  * descriptor_verdict mode semantics (one pin per R2 comparator class:
    EXACT_BOTH_STATED / SET_EQUALITY / ASYMMETRIC_ADD / EITHER_SIDED /
    QUERY_STATED_REQUIRES_CANDIDATE / CROSS_CLASS_FAIL_CLOSED + the
    SELECTION-mode tolerances),
  * lru_cache hit behavior + the gate-keyed memoization,
  * the >512-char _MATCH_INPUT_CAP,
  * unhashable-input safety (loud TypeError, never a silent coercion),
  * wrapper parity (the converted thin wrappers agree with descriptor_verdict).

Free-unit suite: no network, no marks. ASCII-only source (Windows discipline).
"""

import dataclasses

import pytest

from app.services import price_service as ps


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    """The descriptor formalizes gate-scoped semantics; pin them gate-ON (the
    golden corpus env). Individual tests flip the flag where the pin needs it."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _verdict(q, t, cat, mode, brand=""):
    return ps.descriptor_verdict(
        ps.extract_variant_descriptor(q, cat, brand),
        ps.extract_variant_descriptor(t, cat, brand),
        cat, mode,
    )


ALL_MODES = (
    ps.DESCRIPTOR_MODE_SELECTION,
    ps.DESCRIPTOR_MODE_EXACT,
    ps.DESCRIPTOR_MODE_BACKSTOP,
)
STRICT_MODES = (ps.DESCRIPTOR_MODE_SELECTION, ps.DESCRIPTOR_MODE_EXACT)


# ---------------------------------------------------------------------------
# extract_variant_descriptor - one representative product per category
# ---------------------------------------------------------------------------

class TestExtractionPerCategory:
    def test_fragrances(self):
        d = ps.extract_variant_descriptor(
            "Dior Sauvage Eau de Parfum 100ml", "fragrances", "Dior")
        assert d.concentration == "EDP"
        assert d.size_ml_snapped == 100
        assert d.size_ml_raw == 100.0
        assert d.gender is None
        # brand + alias-house words and the concentration/measure tokens are
        # out of identity; only the product name remains.
        assert d.identity_core == frozenset({"sauvage"})
        assert d.brand_tokens >= frozenset({"dior", "christian"})

    def test_electronics(self):
        d = ps.extract_variant_descriptor(
            "Samsung Galaxy S24 Ultra 12GB RAM 256GB 5G Dual SIM",
            "electronics", "Samsung")
        assert d.storage_gb == 256.0       # MAX = storage-not-RAM
        assert d.ram_gb == frozenset({12})
        assert d.qualifiers == frozenset({"ultra"})  # 5g deliberately excluded
        assert d.condition is False
        assert {"galaxy", "s24"} <= d.identity_core
        assert "ultra" not in d.identity_core   # qualifiers compared on their own axis
        assert "256gb" not in d.identity_core   # measures compared on their own axis

    def test_supplements(self):
        d = ps.extract_variant_descriptor(
            "NOW Magnesium Glycinate 400mg 180 Veg Capsules", "supplements", "NOW")
        assert d.doses == frozenset({(400.0, "mg")})
        assert d.count == 180.0
        assert {"magnesium", "glycinate"} <= d.supplement_types
        assert d.bare_doses == frozenset()  # 400 is 3-digit, not a bare dose

    def test_makeup(self):
        d = ps.extract_variant_descriptor(
            "Maybelline Fit Me Matte and Poreless Foundation 130", "makeup",
            "Maybelline")
        assert d.finishes == frozenset({"matte", "poreless"})
        assert d.form is None  # foundation is not a discriminating form phrase
        assert "130" in d.identity_core  # the shade number IS identity

    def test_skincare(self):
        d = ps.extract_variant_descriptor(
            "La Roche-Posay Anthelios SPF 50 Invisible Fluid 50ml", "skincare",
            "La Roche-Posay")
        assert d.spfs == frozenset({50})
        assert d.size_ml_raw == 50.0
        assert d.form == "fluid"
        assert (50.0, "ml") in d.weights_volumes

    def test_haircare(self):
        d = ps.extract_variant_descriptor(
            "OGX Renewing Argan Oil of Morocco Shampoo 385ml", "haircare", "OGX")
        assert d.form == "shampoo"  # phrase order: shampoo wins over the later 'oil'
        assert d.size_ml_raw == 385.0

    def test_grocery(self):
        d = ps.extract_variant_descriptor(
            "Red Bull Sugar Free 250ml 4 Pack", "grocery", "Red Bull")
        assert d.packs == frozenset({4.0})
        assert (250.0, "ml") in d.weights_volumes
        assert "sugarfree" in d.fold_tokens  # the two-word diet variant is glued
        assert d.count is None  # 'pack' is the pack axis, not a unit count

    def test_fashion(self):
        d = ps.extract_variant_descriptor(
            "Nike Air Force 1 '07 White Leather US 9.5 Sneakers", "fashion", "Nike")
        assert d.shoe_sizes == frozenset({("us", 9.5)})
        assert d.materials == frozenset({"leather"})
        assert "white" in d.colors

    def test_other(self):
        d = ps.extract_variant_descriptor(
            "Stanley Quencher 40oz Tumbler", "other", "Stanley")
        assert d.size_ml_raw == pytest.approx(40 * 29.5735)
        assert d.qualifiers == frozenset()  # no qualifier table outside electronics

    def test_structured_code_phase_a_provenance_todo(self):
        # Phase A: structured codes are adapter-STAMPED onto the price dict
        # (algolia_service.py:532) and never parsed from title text, so the
        # field is always "" here. TODO(Wave-2 Phase B, R1 provenance):
        # structured-first stamping - a retailer-structured brand/code/size
        # wins over the title parse and marks provenance='structured'.
        d = ps.extract_variant_descriptor("Ray-Ban Aviator RB3025", "fashion",
                                          "Ray-Ban")
        assert d.structured_code == ""
        assert d.model_codes == frozenset({"rb3025"})

    def test_descriptor_is_frozen(self):
        d = ps.extract_variant_descriptor("Dior Sauvage", "fragrances", "Dior")
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.concentration = "EDT"


# ---------------------------------------------------------------------------
# descriptor_verdict - one pin per R2 comparator class
# ---------------------------------------------------------------------------

class TestComparatorClasses:
    def test_exact_both_stated_rejects_in_every_mode(self):
        # EXACT_BOTH_STATED: both sides state concentration and differ.
        for mode in ALL_MODES:
            v = _verdict("Dior Sauvage Eau de Parfum",
                         "Dior Sauvage Eau de Toilette", "fragrances", mode)
            assert v.match is False
            assert v.axis == "concentration"

    def test_exact_both_stated_one_sided_tolerated(self):
        # One side omits the axis -> UNKNOWN tolerated (every mode).
        for mode in ALL_MODES:
            v = _verdict("Dior Sauvage",
                         "Dior Sauvage Eau de Toilette 100ml", "fragrances", mode)
            assert v.match is True, mode

    def test_set_equality_electronics_qualifiers(self):
        for mode in ALL_MODES:
            v = _verdict("Samsung Galaxy S24", "Samsung Galaxy S24 FE",
                         "electronics", mode)
            assert v.match is False
            assert v.axis == "variant_qualifier"

    def test_set_equality_plus_stems(self):
        for mode in ALL_MODES:
            v = _verdict("La Roche-Posay Effaclar Duo",
                         "La Roche-Posay Effaclar Duo+ M", "skincare", mode)
            assert v.match is False
            assert v.axis == "plus_variant"

    def test_asymmetric_add_flagship_concentration_is_strict_only(self):
        # ASYMMETRIC_ADD lives in the strict block: SELECTION/EXACT reject,
        # BACKSTOP (axis-only) tolerates - the chokepoints pair the separate
        # bounded _category_type_added for exactly this class.
        for mode in STRICT_MODES:
            v = _verdict("Dior Sauvage", "Dior Sauvage Parfum", "fragrances", mode)
            assert v.match is False
            assert v.axis == "category_type_added"
        assert _verdict("Dior Sauvage", "Dior Sauvage Parfum", "fragrances",
                        ps.DESCRIPTOR_MODE_BACKSTOP).match is True

    def test_asymmetric_add_supplement_type(self):
        for mode in STRICT_MODES:
            v = _verdict("Dymatize Whey", "Dymatize Whey Isolate",
                         "supplements", mode)
            assert v.match is False
            assert v.axis == "category_type_added"

    def test_asymmetric_add_grocery_flavour_fires_loose_too(self):
        # The grocery flavour ADD is a loose-block axis: it also protects the
        # backstop chokepoints.
        for mode in ALL_MODES:
            v = _verdict("Cheerios", "Chocolate Cheerios", "grocery", mode)
            assert v.match is False
            assert v.axis == "flavour"

    def test_asymmetric_colors_query_subset_strict_only(self):
        for mode in STRICT_MODES:
            v = _verdict("Nike Air Force 1 White Green",
                         "Nike Air Force 1 White Red", "fashion", mode,
                         brand="Nike")
            assert v.match is False
            assert v.axis == "color"
        assert _verdict("Nike Air Force 1 White Green",
                        "Nike Air Force 1 White Red", "fashion",
                        ps.DESCRIPTOR_MODE_BACKSTOP, brand="Nike").match is True

    def test_either_sided_condition_both_directions(self):
        # condition is the ONLY either-direction one-sided reject - and it is a
        # loose-block axis (fires at the backstop too).
        for mode in ALL_MODES:
            v = _verdict("Sony WH-1000XM5", "Sony WH-1000XM5 Renewed",
                         "electronics", mode)
            assert v.match is False and v.axis == "condition", mode
            v = _verdict("Apple iPhone 13 Refurbished", "Apple iPhone 13",
                         "electronics", mode)
            assert v.match is False and v.axis == "condition", mode

    def test_query_stated_requires_candidate_strict_only(self):
        for mode in STRICT_MODES:
            v = _verdict("Dior Sauvage Eau de Parfum 100ml", "Dior Sauvage",
                         "fragrances", mode)
            assert v.match is False
            assert v.axis == "candidate_missing_query_axis"
        assert _verdict("Dior Sauvage Eau de Parfum 100ml", "Dior Sauvage",
                        "fragrances", ps.DESCRIPTOR_MODE_BACKSTOP).match is True

    def test_cross_class_fail_closed_g_vs_ml(self):
        for mode in ALL_MODES:
            v = _verdict("CeraVe Moisturizing Cream 340g",
                         "CeraVe Moisturizing Cream 177ml", "skincare", mode)
            assert v.match is False
            assert v.axis == "weight_volume"

    def test_unknown_mode_raises(self):
        d = ps.extract_variant_descriptor("Dior Sauvage", "fragrances")
        with pytest.raises(ValueError):
            ps.descriptor_verdict(d, d, "fragrances", "not-a-mode")


class TestSelectionTolerances:
    def test_year_annotation_tolerated_when_generation_pinned(self):
        assert _verdict("Apple iPad Air M3 128GB",
                        "Apple iPad Air (2025) M3 128GB WiFi", "electronics",
                        ps.DESCRIPTOR_MODE_SELECTION, brand="Apple").match is True

    def test_year_only_family_stays_rejected(self):
        # iPhone SE has NO non-year generation discriminator -> the annotation
        # year stays identity and the variant-add superset rejects.
        assert _verdict("Apple iPhone SE", "Apple iPhone SE (2022) 64GB",
                        "electronics", ps.DESCRIPTOR_MODE_SELECTION,
                        brand="Apple").match is False

    def test_electronics_ai_title_side_tolerated(self):
        assert _verdict("Samsung Galaxy S25",
                        "Samsung Galaxy S25 AI Smartphone 256GB", "electronics",
                        ps.DESCRIPTOR_MODE_SELECTION, brand="Samsung").match is True

    def test_inch_annotation_equality(self):
        assert _verdict("Apple MacBook Air M3 13",
                        "Apple MacBook Air M3 13-inch Midnight", "electronics",
                        ps.DESCRIPTOR_MODE_SELECTION, brand="Apple").match is True

    def test_fashion_construction_bigram(self):
        assert _verdict("Nike Sportswear Club T-Shirt",
                        "Nike Sportswear Club Crew Neck T-Shirt", "fashion",
                        ps.DESCRIPTOR_MODE_SELECTION, brand="Nike").match is True

    def test_eyewear_code_confirmed_annotations(self):
        assert _verdict("Ray-Ban Aviator RB3025",
                        "Ray-Ban Aviator RB3025 002/58 Gold 58mm Unisex",
                        "fashion", ps.DESCRIPTOR_MODE_SELECTION,
                        brand="Ray-Ban").match is True

    def test_makeup_shared_shade_number(self):
        assert _verdict("Maybelline Fit Me 240",
                        "Maybelline Fit Me 240 Soft Sand", "makeup",
                        ps.DESCRIPTOR_MODE_SELECTION, brand="Maybelline").match is True
        # an EXTRA shade number is a different shade and must still reject.
        assert _verdict("Maybelline Fit Me 220",
                        "Maybelline Fit Me 220 320", "makeup",
                        ps.DESCRIPTOR_MODE_SELECTION, brand="Maybelline").match is False


# ---------------------------------------------------------------------------
# Wrapper parity - the converted thin wrappers agree with descriptor_verdict
# ---------------------------------------------------------------------------

PARITY_CASES = [
    ("Samsung Galaxy S24 Ultra 256GB",
     "Samsung Galaxy S24 Ultra 12GB+256GB Titanium Black", "electronics", "Samsung"),
    ("Dior Sauvage Eau de Toilette 100ml", "Dior Sauvage Eau de Parfum 100ml",
     "fragrances", "Dior"),
    ("Nike Air Force 1", "Nike Air Max 1", "fashion", "Nike"),
    ("ON Gold Standard Whey Vanilla", "ON Gold Standard Whey Chocolate",
     "supplements", "Optimum Nutrition"),
    ("Maybelline Fit Me 240", "Maybelline Fit Me 240 Soft Sand", "makeup",
     "Maybelline"),
    ("Coca-Cola 6 Pack", "Coca-Cola 12 Pack", "grocery", "Coca-Cola"),
]


@pytest.mark.parametrize("q,t,cat,brand", PARITY_CASES)
def test_wrapper_parity(q, t, cat, brand):
    q_vd = ps.extract_variant_descriptor(q, cat, brand)
    t_vd = ps.extract_variant_descriptor(t, cat, brand)
    assert ps._selection_match(q, t, cat, candidate_brand=brand) == \
        ps.descriptor_verdict(q_vd, t_vd, cat, ps.DESCRIPTOR_MODE_SELECTION).match
    assert ps.is_exact_match(q, t, cat, candidate_brand=brand) == \
        ps.descriptor_verdict(q_vd, t_vd, cat, ps.DESCRIPTOR_MODE_EXACT).match
    qb = ps.extract_variant_descriptor(q, cat, "")
    tb = ps.extract_variant_descriptor(t, cat, "")
    assert ps._backstop_identity_ok(q, t, cat) == \
        ps.descriptor_verdict(qb, tb, cat, ps.DESCRIPTOR_MODE_BACKSTOP).match


# ---------------------------------------------------------------------------
# Memoization, cap, degenerate inputs
# ---------------------------------------------------------------------------

class TestMemoization:
    def test_lru_cache_hit_returns_same_object(self):
        ps._extract_variant_descriptor_cached.cache_clear()
        d1 = ps.extract_variant_descriptor(
            "Creed Aventus 100ml Eau de Parfum", "fragrances", "Creed")
        info1 = ps._extract_variant_descriptor_cached.cache_info()
        d2 = ps.extract_variant_descriptor(
            "Creed Aventus 100ml Eau de Parfum", "fragrances", "Creed")
        info2 = ps._extract_variant_descriptor_cached.cache_info()
        assert d1 is d2
        assert info2.hits == info1.hits + 1
        assert info2.misses == info1.misses

    def test_cache_is_gate_keyed(self, monkeypatch):
        # normalize_words (identity tokenization) branches on the gate flag ->
        # the memo key includes it so a flag flip never serves a stale entry.
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        d_on = ps.extract_variant_descriptor("Dell XPS 13 16 GB RAM",
                                             "electronics", "Dell")
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        d_off = ps.extract_variant_descriptor("Dell XPS 13 16 GB RAM",
                                              "electronics", "Dell")
        assert d_on is not d_off

    def test_none_input_is_empty_text(self):
        assert ps.extract_variant_descriptor(None, "fragrances") is \
            ps.extract_variant_descriptor("", "fragrances")


class TestCapAndSafety:
    def test_match_input_cap_bounds_axis_extraction(self):
        # 675-char input: the trailing 256GB token lies beyond the 512-char
        # _MATCH_INPUT_CAP the legacy _axis_mismatch applied (ReDoS guard) -
        # the descriptor replicates the truncation.
        redos_query = "Samsung Galaxy " + ("Ultra " * 110) + "256GB"
        assert len(redos_query) > ps._MATCH_INPUT_CAP
        d = ps.extract_variant_descriptor(redos_query, "electronics", "Samsung")
        assert d.storage_gb is None
        d2 = ps.extract_variant_descriptor("Samsung Galaxy 256GB",
                                           "electronics", "Samsung")
        assert d2.storage_gb == 256.0

    def test_unhashable_input_raises_typeerror(self):
        # lru_cache requires hashable arguments; an unhashable input must fail
        # LOUDLY (TypeError), never be silently coerced into a wrong key.
        with pytest.raises(TypeError):
            ps.extract_variant_descriptor(["Dior", "Sauvage"], "fragrances")

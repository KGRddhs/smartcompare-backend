# -*- coding: utf-8 -*-
"""Cellular-generation tokens ("5G"/"4G"/"3G"/"2G") must NOT be mis-parsed as a
gram weight in ELECTRONICS context.

PRE-EXISTING BUG (main): `_WEIGHT_VOLUME_RE` matched "5G" -> (5.0, "g"), so a
phone's base query ("Galaxy S24 FE") and its genuine "...5G Smartphone" PDP title
injected a phantom "5g" size token and hashed to DIFFERENT price cache keys — a
guaranteed warm-vs-live cache MISS across the electronics class that undermines the
price-cache warmer's parity.

CORRECT FIX (category-aware): exclude the bare cellular [2-5]G token from weight
parsing ONLY for electronics/gadget context, PRESERVING supplement/grocery gram
parsing — a category-blind strip would FALSE-MERGE "Creatine 5G" == "Creatine 10G"
(a strictly-worse wrong-SKU cache serve). The exclusion is gated by the exact-price
gate, so with ENABLE_EXACT_PRICE_GATE=false the legacy cache namespace is byte-
identical to b207bfa (a rollback must not orphan the warmed cache).

COVERAGE-DRIVEN (CLAUDE.md discipline): enumerate REAL electronics AND supplement/
grocery products in BOTH directions — collapse for electronics, stay-distinct for
gram categories — plus adversarial model tokens that embed a "G" (Moto G54, Nokia
G22) which must NOT be eaten by the cellular strip.
"""
import pytest

import app.services.price_service as ps


def _key(brand, name, identity, category, variant=None, region="bahrain"):
    return ps.build_size_aware_price_cache_key(
        brand, name, variant, region, identity, category=category
    )


# ---------------------------------------------------------------------------
# CLEAN-RED CORE (existing signatures only) — the reported parity bug, driven
# via the per-task ContextVar so it fails cleanly against un-patched main.
# ---------------------------------------------------------------------------

def test_core_parity_electronics_base_vs_5g_pdp_via_contextvar():
    ps.set_resolved_price_category("electronics")
    try:
        base = ps.build_size_aware_price_cache_key(
            "Samsung", "Galaxy S24 FE", None, "bahrain", "Galaxy S24 FE")
        pdp = ps.build_size_aware_price_cache_key(
            "Samsung", "Galaxy S24 FE", None, "bahrain",
            "Galaxy S24 FE 5G Smartphone")
        assert base == pdp
    finally:
        ps.set_resolved_price_category(None)


# ---------------------------------------------------------------------------
# extract_weight_or_volume — category-aware cellular exclusion
# ---------------------------------------------------------------------------

def test_extract_weight_electronics_excludes_bare_5g():
    assert ps.extract_weight_or_volume("5G", category="electronics") is None
    assert ps.extract_weight_or_volume(
        "Galaxy S24 FE 5G Smartphone", category="electronics") is None


@pytest.mark.parametrize("gen", ["2G", "3G", "4G", "5G"])
def test_extract_weight_electronics_excludes_all_cellular_generations(gen):
    assert ps.extract_weight_or_volume(f"Galaxy A55 {gen}", category="electronics") is None


def test_extract_weight_supplements_keeps_gram_weight():
    # A supplement/grocery "NG" IS N grams — the false-merge the task forbids.
    assert ps.extract_weight_or_volume("Creatine 5G", category="supplements") == (5.0, "g")
    assert ps.extract_weight_or_volume("Coffee Sachet 2G", category="grocery") == (2.0, "g")


def test_extract_weight_none_category_keeps_gram_weight():
    # Unresolved category is the SAFE (conservative) direction: DON'T strip, so a
    # gram weight is preserved (no risk of a false supplement/grocery merge).
    ps.set_resolved_price_category(None)
    assert ps.extract_weight_or_volume("Something 5G") == (5.0, "g")


def test_extract_weight_electronics_real_multidigit_gram_survives():
    # ONLY the bare cellular [2-5]G token is excluded — a genuine multi-digit weight
    # token ("250 g") is still parsed (proves the strip is surgical, not a blanket kill).
    assert ps.extract_weight_or_volume("Gadget 250 g", category="electronics") == (250.0, "g")


def test_extract_weight_electronics_storage_gb_never_grams():
    # "5GB" is storage — the trailing B blocks the \bG\b boundary, so it was never
    # a gram token and stays None regardless of the fix.
    assert ps.extract_weight_or_volume("Memory Card 5GB", category="electronics") is None


# ---------------------------------------------------------------------------
# size_variant_token — the phantom weight token is gone for electronics
# ---------------------------------------------------------------------------

def test_size_token_electronics_5g_is_empty():
    assert ps.size_variant_token("Galaxy S24 FE 5G", category="electronics") == ""
    assert ps.size_variant_token("Galaxy S24 FE", category="electronics") == ""


def test_size_token_supplement_grams_distinct():
    # THE required (b) invariant — "Creatine 5G" and "Creatine 10G" stay DISTINCT.
    assert ps.size_variant_token("Creatine 5G", category="supplements") == "5g"
    assert ps.size_variant_token("Creatine 10G", category="supplements") == "10g"
    assert (ps.size_variant_token("Creatine 5G", category="supplements")
            != ps.size_variant_token("Creatine 10G", category="supplements"))


def test_size_token_electronics_via_contextvar_when_no_explicit_category():
    ps.set_resolved_price_category("electronics")
    try:
        assert ps.size_variant_token("Galaxy S24 FE 5G") == ""
    finally:
        ps.set_resolved_price_category(None)


# ---------------------------------------------------------------------------
# CORE cache-key parity — explicit category (the production threading path)
# ---------------------------------------------------------------------------

def test_key_electronics_base_and_5g_pdp_collapse():
    # THE reported (a) invariant.
    base = _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE", "electronics")
    pdp = _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE 5G Smartphone", "electronics")
    assert base == pdp


def test_key_electronics_5g_in_name_collapses_onto_base():
    base = _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE", "electronics")
    named = _key("Samsung", "Galaxy S24 FE 5G", "Galaxy S24 FE 5G", "electronics")
    assert base == named


def test_key_electronics_fe_qualifier_still_discriminates():
    # 5G is noise, but the FE model qualifier is a REAL discriminator — a base "Galaxy
    # S24" must NOT collapse onto "Galaxy S24 FE" (only the cellular token is stripped).
    s24 = _key("Samsung", "Galaxy S24", "Galaxy S24 5G", "electronics")
    s24fe = _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE 5G", "electronics")
    assert s24 != s24fe


def test_key_electronics_5g_does_not_disturb_storage_variant():
    a = _key("Apple", "iPhone 15", "iPhone 15 128GB", "electronics")
    b = _key("Apple", "iPhone 15", "iPhone 15 128GB 5G", "electronics")
    assert a == b  # 5G stripped as noise; both keep the 128gb token
    c = _key("Apple", "iPhone 15", "iPhone 15 256GB 5G", "electronics")
    assert a != c  # storage still discriminates


# --- COVERAGE SWEEP: real electronics, base vs cellular-suffixed forms ------

_ELECTRONICS_COLLAPSE = [
    ("Samsung", "Galaxy S24 FE", "Galaxy S24 FE 5G Smartphone"),
    ("Samsung", "Galaxy A55", "Galaxy A55 5G Dual SIM"),
    ("Samsung", "Galaxy A37", "Galaxy A37 5G"),
    ("Samsung", "Galaxy Tab S10 Lite", "Galaxy Tab S10 Lite 5G"),
    ("Google", "Pixel 8", "Pixel 8 5G"),
    ("OnePlus", "Nord 4", "OnePlus Nord 4 5G"),
    ("Xiaomi", "Redmi Note 13", "Redmi Note 13 4G"),
    ("Motorola", "Moto G54", "Moto G54 5G"),   # model token embeds "G54" — must NOT be eaten
    ("Nokia", "G22", "Nokia G22 4G"),          # model IS "G22" — must NOT be eaten
]


@pytest.mark.parametrize("brand,name,cellular_title", _ELECTRONICS_COLLAPSE)
def test_sweep_electronics_cellular_suffix_collapses_onto_base(brand, name, cellular_title):
    base = _key(brand, name, name, "electronics")
    suffixed = _key(brand, name, cellular_title, "electronics")
    assert base == suffixed, (name, cellular_title)


# --- COVERAGE SWEEP: gram categories keep DISTINCT weights ------------------
# The SAME [2-5]G surface that COLLAPSES for electronics must stay a DISTINCT gram
# weight for supplement/grocery — the strictly-worse false-merge the task forbids.

_GRAM_DISTINCT = [
    ("Optimum", "Creatine", "Creatine 5G", "Creatine 10G", "supplements"),
    ("Nescafe", "Coffee Sachet", "Coffee Sachet 2G", "Coffee Sachet 4G", "grocery"),
    ("Generic", "Sugar Stick", "Sugar Stick 3G", "Sugar Stick 5G", "grocery"),
]


@pytest.mark.parametrize("brand,name,ta,tb,category", _GRAM_DISTINCT)
def test_sweep_gram_categories_stay_distinct(brand, name, ta, tb, category):
    assert _key(brand, name, ta, category) != _key(brand, name, tb, category), (ta, tb)


# --- "other" (LLM-mislabel) is re-inferred from the title ------------------

def test_other_labelled_phone_reinfers_electronics_and_collapses():
    base = _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE 5G Smartphone", "other")
    pdp = _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE", "other")
    assert base == pdp


def test_other_labelled_supplement_reinfers_and_keeps_grams():
    # CRITICAL safety: an "other"-labelled supplement must re-infer to supplements
    # (NOT electronics) so its gram weights stay distinct — no false merge.
    k5 = _key("Optimum", "Creatine", "Creatine Monohydrate 5G", "other")
    k10 = _key("Optimum", "Creatine", "Creatine Monohydrate 10G", "other")
    assert k5 != k10


# --- Brand-collision foods must NOT false-merge (coverage review R2, CRITICAL) ----
# A non-electronics product whose title carries an electronics-BRAND whole-token
# (apple/nothing/beats/…) PLUS a bare [2-5]G gram token must NOT be promoted to
# electronics by the cellular digit ITSELF (the brand+digit inference rule would
# otherwise fire on the "3" of "3G") — else the genuine gram weight is stripped and
# two different sizes collapse to ONE cache key. Category resolution must infer on the
# CELLULAR-STRIPPED text so the [2-5]G can never be the promoting digit.

_BRAND_COLLISION_FOODS = [
    ("Apple Sauce", "Apple Sauce 3G Jar", "Apple Sauce 5G Jar", "other"),
    ("Caramel Apple", "Caramel Apple 2G", "Caramel Apple 4G", "other"),
    ("Bundt Cake", "Nothing Bundt Cake 2G", "Nothing Bundt Cake 5G", "other"),
    ("Apple Sauce", "Apple Sauce 3G Jar", "Apple Sauce 5G Jar", None),
]


@pytest.mark.parametrize("brand_name,ta,tb,cat", _BRAND_COLLISION_FOODS)
def test_brand_collision_food_not_false_merged(brand_name, ta, tb, cat):
    assert _key("X", brand_name, ta, cat) != _key("X", brand_name, tb, cat), (ta, tb, cat)


def test_brand_collision_food_gram_preserved_extract():
    # The gram weight must survive for a brand-collision food even at category="other"/None
    # (the [2-5]G must NOT self-promote the text to electronics).
    assert ps.extract_weight_or_volume("Apple Sauce 3G Jar", category="other") == (3.0, "g")
    assert ps.extract_weight_or_volume("Nothing Bundt Cake 2G", category=None) == (2.0, "g")


def test_brand_collision_food_fairness_gram_preserved():
    # coverage review R2 finding #2 — the fairness extractors (no category arg) must keep
    # the like-for-like gram basis for a brand-collision food.
    assert ps._extract_grocery({"name": "Apple Sauce 3G"}) == 3.0
    assert ps._extract_grocery({"name": "Apple Sauce 5G"}) == 5.0


def test_phone_still_collapses_after_stripped_inference():
    # The fix (infer on the cellular-stripped text) must PRESERVE the "other"-labelled
    # phone collapse — "Galaxy S24 FE" (stripped) still infers electronics.
    assert (_key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE 5G Smartphone", "other")
            == _key("Samsung", "Galaxy S24 FE", "Galaxy S24 FE", "other"))


# ---------------------------------------------------------------------------
# ROLLBACK — flag OFF is byte-identical to b207bfa (the cellular strip is a no-op)
# ---------------------------------------------------------------------------

def test_flag_off_cellular_strip_is_noop(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    # b207bfa parity: "5G" is STILL parsed as grams flag-OFF, so the legacy cache
    # namespace is unchanged and a rollback does not orphan the warmed cache.
    assert ps.extract_weight_or_volume("5G", category="electronics") == (5.0, "g")
    assert ps.size_variant_token("Galaxy S24 FE 5G", category="electronics") == "5g"

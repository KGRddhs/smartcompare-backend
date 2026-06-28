# -*- coding: utf-8 -*-
"""COVERAGE-REVIEW findings (2026-06-28) — the 42 verified runtime leaks +
over-rejection false-pends a coverage-driven review workflow (7 agents, real-product
enumeration, BOTH directions, reproduced through the runtime) found that the 3 prior
fix passes + 2 hypothesis-driven review workflows all MISSED.

Spec: docs/plans/2026-06-28-genuine-price-correctness-STRUCTURAL-FIXES.md (clusters A-H).
Raw repros: .qa-correctness/coverage_findings.txt.

Every test was REPRODUCED through the RUNTIME function the orchestrator runs
(_selection_match / should_cache_price / extract_jsonld_price / reselect_to_target_value /
is_price_showable / _infer_category_from_query / the KPI) — NOT a helper in isolation
(the green-gate lesson). Each asserts the CORRECT fail-closed / no-over-rejection behaviour.

Two directions per axis:
  * LEAK guards  — a candidate that ADDS a distinctive token / differs on a missing axis
                   must REJECT (False). RED on the current branch.
  * OVER-REJECTION guards — a genuine descriptive / alias / one-sided title must ACCEPT
                   (True). Some are RED now (house-prefix, alias, No.3); the rest are
                   GREEN regression guards that the keystone must NOT break.
"""
import importlib
import json

import pytest

import app.services.price_service as ps


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _m(q, t, cat, brand=""):
    return ps._selection_match(q, t, cat, candidate_brand=brand)


def _jsonld(payload):
    return f'<html><script type="application/ld+json">{json.dumps(payload)}</script></html>'


# ===========================================================================
# CLUSTER A — SYSTEMIC superset/subset leak (the keystone). A candidate ADDING a
# distinctive token is accepted as the base SKU across EVERY category. Must REJECT.
# ===========================================================================

def test_A_electronics_canon_r6_vs_r6_mark_ii_rejected():
    assert _m("Canon EOS R6", "Canon EOS R6 Mark II", "electronics", "Canon") is False


def test_A_electronics_airpods_pro_vs_pro_2_rejected():
    assert _m("Apple AirPods Pro", "Apple AirPods Pro 2", "electronics", "Apple") is False


def test_A_electronics_switch_vs_switch_oled_rejected():
    assert _m("Nintendo Switch", "Nintendo Switch OLED", "electronics", "Nintendo") is False


def test_A_electronics_rtx_4070_vs_4070_ti_rejected():
    assert _m("RTX 4070", "RTX 4070 Ti", "electronics", "") is False


def test_A_supplement_magnesium_vs_glycinate_rejected():
    assert _m("NOW Magnesium", "NOW Magnesium Glycinate", "supplements", "NOW") is False


def test_A_supplement_centrum_vs_silver_rejected():
    assert _m("Centrum Multivitamin", "Centrum Silver Multivitamin", "supplements", "Centrum") is False


def test_A_supplement_fish_oil_vs_triple_strength_rejected():
    assert _m("Nordic Naturals Fish Oil", "Nordic Naturals Triple Strength Fish Oil",
              "supplements", "Nordic Naturals") is False


def test_A_supplement_creatine_vs_micronized_rejected():
    assert _m("Optimum Creatine", "Optimum Micronized Creatine", "supplements", "Optimum") is False


def test_A_makeup_pillow_talk_vs_medium_rejected():
    assert _m("Charlotte Tilbury Pillow Talk", "Charlotte Tilbury Pillow Talk Medium",
              "makeup", "Charlotte Tilbury") is False


def test_A_makeup_nars_orgasm_vs_orgasm_x_rejected():
    assert _m("NARS Orgasm", "NARS Orgasm X", "makeup", "NARS") is False


def test_A_fashion_samba_og_vs_classic_rejected():
    assert _m("Adidas Samba OG", "Adidas Samba Classic", "fashion", "Adidas") is False


def test_A_grocery_nescafe_gold_vs_decaf_rejected():
    assert _m("Nescafe Gold", "Nescafe Gold Decaf", "grocery", "Nescafe") is False


def test_A_fragrance_aventus_vs_aventus_cologne_rejected():
    # 'cologne' is in _FRAGRANCE_PADDING_TOKENS so the flanker strips it -> leak.
    assert _m("Creed Aventus", "Creed Aventus Cologne", "fragrances", "Creed") is False


# --- Cluster A OVER-REJECTION regression guards (must ACCEPT) ---------------

def test_A_overrej_electronics_descriptive_title_accepted():
    assert _m("Samsung Galaxy S24 256GB",
              "Samsung Galaxy S24 256GB Dual SIM Phantom Black 5G Smartphone",
              "electronics", "Samsung") is True


def test_A_overrej_electronics_same_model_accepted():
    assert _m("Apple AirPods Pro 2", "Apple AirPods Pro 2 (2nd Generation)",
              "electronics", "Apple") is True
    assert _m("Canon EOS R6 Mark II", "Canon EOS R6 Mark II Body",
              "electronics", "Canon") is True


def test_A_overrej_fashion_af1_07_year_suffix_accepted():
    assert _m("Nike Air Force 1 White", "Nike Air Force 1 '07 White", "fashion", "Nike") is True


def test_A_overrej_supplement_brand_form_and_generic_accepted():
    # Adding only the brand long-form (NOW->NOW Foods) + a generic class noun (protein)
    # must still match — the discriminating tokens (magnesium glycinate) are unchanged.
    assert _m("NOW Magnesium Glycinate", "NOW Foods Magnesium Glycinate",
              "supplements", "NOW Foods") is True


def test_A_overrej_supplement_paren_chem_name_accepted():
    # A parenthetical synonym/clarifier (Cholecalciferol == D3) is NOT a variant.
    assert _m("NOW Vitamin D3 5000 IU", "NOW Vitamin D3 (Cholecalciferol) 5000 IU",
              "supplements", "NOW") is True


# ===========================================================================
# CLUSTER B — missing NUMERIC axes. Each pair must REJECT (leak today).
# ===========================================================================

def test_B_supplement_protein_2lb_vs_5lb_rejected():
    assert _m("Optimum Nutrition Whey 2lb", "Optimum Nutrition Whey 5lb",
              "supplements", "Optimum Nutrition") is False


def test_B_supplement_protein_oz_weight_rejected():
    assert _m("Optimum Nutrition Whey 32 oz", "Optimum Nutrition Whey 80 oz",
              "supplements", "Optimum Nutrition") is False


def test_B_skincare_percent_strength_spaced_rejected():
    assert _m("The Ordinary Niacinamide 5 percent", "The Ordinary Niacinamide 10 percent",
              "skincare", "The Ordinary") is False


def test_B_skincare_percent_strength_decimal_rejected():
    assert _m("The Ordinary Retinol 1%", "The Ordinary Retinol 0.3%",
              "skincare", "The Ordinary") is False


def test_B_skincare_percent_one_sided_pends():
    # Query states 10%, candidate omits it -> unverified -> pend (fail-closed).
    assert _m("The Ordinary Niacinamide 10%", "The Ordinary Niacinamide",
              "skincare", "The Ordinary") is False


def test_B_fashion_shoe_size_us_9_vs_10_rejected():
    assert _m("Nike Air Max 90 US 9", "Nike Air Max 90 US 10", "fashion", "Nike") is False


def test_B_grocery_pack_count_6_vs_24_rejected():
    assert _m("Coca Cola 6 Pack", "Coca Cola 24 Pack", "grocery", "Coca Cola") is False


def test_B_fashion_single_digit_model_jordan_1_vs_4_rejected():
    assert _m("Air Jordan 1", "Air Jordan 4", "fashion", "") is False


def test_B_makeup_single_letter_shade_rejected():
    assert _m("MAC Lipstick A", "MAC Lipstick B", "makeup", "MAC") is False


# --- Cluster B OVER-REJECTION guards ---------------------------------------

def test_B_overrej_same_weight_lb_specific_query_accepted():
    # SPECIFIC query (carries the Gold Standard sub-line) + only a flavour/generic noun
    # added by the candidate must match. A LOOSE query that omits the sub-line correctly
    # pends (structurally identical to Centrum->Silver) — that is NOT an over-rejection.
    assert _m("Optimum Nutrition Gold Standard Whey 5lb Vanilla",
              "Optimum Nutrition Gold Standard Whey Protein 5lb Vanilla",
              "supplements", "Optimum Nutrition") is True


# ===========================================================================
# CLUSTER C — FORM axis. Supplements: one-sided candidate-adds-form -> pend.
# Skincare/haircare: ONE-SIDED tolerant (only both-stated-different reject).
# ===========================================================================

def test_C_supplement_form_softgel_vs_gummy_rejected():
    assert _m("NOW Vitamin D3 5000 IU Softgels", "NOW Vitamin D3 5000 IU Gummies",
              "supplements", "NOW") is False


def test_C_supplement_form_one_sided_gummy_pends():
    # Query omits form, candidate adds Gummies -> different delivery form -> pend.
    assert _m("NOW Vitamin D3 5000 IU", "NOW Vitamin D3 5000 IU Gummies",
              "supplements", "NOW") is False


def test_C_skincare_form_cream_vs_gel_rejected():
    assert _m("CeraVe Moisturizing Cream", "CeraVe Moisturizing Gel",
              "skincare", "CeraVe") is False


def test_C_haircare_form_oil_vs_balm_rejected():
    assert _m("Moroccanoil Treatment Oil", "Moroccanoil Treatment Balm",
              "haircare", "Moroccanoil") is False


def test_C_overrej_skincare_form_one_sided_serum_accepted():
    # Query omits the form; candidate states Serum -> the descriptive-PDP case -> accept.
    assert _m("The Ordinary Niacinamide", "The Ordinary Niacinamide Serum",
              "skincare", "The Ordinary") is True


def test_C_overrej_haircare_form_one_sided_accepted():
    assert _m("Olaplex No. 3", "Olaplex No. 3 Hair Perfector Treatment",
              "haircare", "Olaplex") is True


def test_C_overrej_supplement_default_form_softgel_accepted():
    # A DEFAULT pill form (softgel/capsule/tablet) added one-sided is the standard
    # presentation, not an alternative SKU -> tolerate. Only ALTERNATIVE forms
    # (gummy/powder/liquid) pend one-sided.
    assert _m("NOW Vitamin D3 5000 IU", "NOW Vitamin D3 5000 IU Softgels",
              "supplements", "NOW") is True
    assert _m("NOW Magnesium Glycinate", "NOW Magnesium Glycinate Veg Capsules",
              "supplements", "NOW") is True


# ===========================================================================
# CLUSTER D — cache write/read symmetry. should_cache_price must inherit the
# Cluster A/B/C leaks (a wrong-SKU candidate must NOT be cached).
# ===========================================================================

def _cache_price(title, **extra):
    p = {"amount": 30, "source_method": "local_bhd",
         "title": title, "url": "https://www.sharafdg.com/p/x", "in_stock": True}
    p.update(extra)
    return p


def test_D_should_cache_rejects_superset_leak_electronics():
    assert ps.should_cache_price(
        "Canon EOS R6", _cache_price("Canon EOS R6 Mark II"), "electronics") is False


def test_D_should_cache_rejects_form_leak_supplement():
    assert ps.should_cache_price(
        "NOW Vitamin D3 5000 IU", _cache_price("NOW Vitamin D3 5000 IU Gummies"),
        "supplements") is False


def test_D_should_cache_accepts_exact_descriptive():
    assert ps.should_cache_price(
        "Samsung Galaxy S24 256GB",
        _cache_price("Samsung Galaxy S24 256GB Dual SIM Phantom Black 5G Smartphone"),
        "electronics") is True


# ===========================================================================
# CLUSTER E — KPI. count_usable_exact_genuine must be fail-closed without truth,
# and must NOT use over-strict equality that scores a genuine DESCRIPTIVE price 0.
# ===========================================================================

def _body(*titles):
    prods = [{"price": {"amount": 30, "source_method": "local_bhd", "in_stock": True,
                        "title": t, "url": "https://x.com/p/%d" % i}}
             for i, t in enumerate(titles)]
    return {"overview": {"products": prods}}


def test_E_kpi_without_truth_is_fail_closed():
    er = importlib.import_module("scripts.eval_runner")
    # No truth entries -> identity UNVERIFIED -> must NOT auto-count as usable.
    body = _body("Samsung Galaxy S24 256GB", "Apple iPhone 15 128GB")
    usable, requested = er.count_usable_exact_genuine(body, None)
    assert requested == 2
    assert usable == 0


def test_E_kpi_genuine_descriptive_title_counts_usable():
    er = importlib.import_module("scripts.eval_runner")
    truth = [{"id": "e1", "query": "Samsung Galaxy S24 256GB", "category": "electronics",
              "expected": {"brand": "Samsung"}},
             {"id": "e2", "query": "Samsung Galaxy S24 256GB", "category": "electronics",
              "expected": {"brand": "Samsung"}}]
    # A genuine, in-stock, valid-PDP, DESCRIPTIVE-title price for the exact SKU must count.
    body = _body("Samsung Galaxy S24 256GB Dual SIM Phantom Black 5G Smartphone",
                 "Samsung Galaxy S24 256GB Dual SIM Phantom Black 5G Smartphone")
    usable, requested = er.count_usable_exact_genuine(body, truth)
    assert (usable, requested) == (2, 2)


def test_E_kpi_wrong_variant_not_usable():
    er = importlib.import_module("scripts.eval_runner")
    truth = [{"id": "e1", "query": "Canon EOS R6", "category": "electronics",
              "expected": {"brand": "Canon"}},
             {"id": "e2", "query": "Canon EOS R6", "category": "electronics",
              "expected": {"brand": "Canon"}}]
    body = _body("Canon EOS R6 Mark II Body", "Canon EOS R6 Mark II Body")
    usable, _ = er.count_usable_exact_genuine(body, truth)
    assert usable == 0


# ===========================================================================
# CLUSTER F — reselect bypass, chokepoint fail-OPEN, category inference None.
# ===========================================================================

def test_F_infer_category_skincare():
    assert ps._infer_category_from_query("The Ordinary Niacinamide 10% Serum") == "skincare"


def test_F_infer_category_haircare():
    assert ps._infer_category_from_query("Olaplex No. 3 Hair Perfector") == "haircare"


def test_F_infer_category_makeup():
    assert ps._infer_category_from_query("NARS Orgasm Blush") == "makeup"


def test_F_infer_category_fashion():
    assert ps._infer_category_from_query("Nike Air Jordan 1 Sneakers") == "fashion"


def test_F_chokepoint_genuine_no_url_no_title_pends():
    # A genuine-method price with NO title and NO url must PEND at the enforce gate.
    price = {"amount": 400, "source_method": "local_bhd"}
    assert ps.is_price_showable("Samsung Galaxy S24 256GB", price, "electronics",
                                enforce_correctness=True) is False


def test_F_reselect_rejects_wrong_strength_when_unit_matches():
    # reselect bypasses _selection_match: a candidate whose comparable-unit (30ml volume)
    # MATCHES the target but whose %-strength is WRONG must NOT be shipped. The fairness
    # unit (volume) is the deliberate re-select target; the strength axis must still gate.
    cands = [{"title": "The Ordinary Niacinamide 5% Serum 30ml", "size": "30ml",
              "amount": 5, "source_method": "local_bhd", "in_stock": True,
              "url": "https://x.com/p/n5",
              "raw_data": {"amount": 5, "source_method": "local_bhd",
                           "title": "The Ordinary Niacinamide 5% Serum 30ml", "size": "30ml",
                           "in_stock": True, "url": "https://x.com/p/n5"}}]
    out = ps.reselect_to_target_value(
        "The Ordinary Niacinamide 10% 30ml", cands, 30.0, "skincare")
    assert out is None


# ===========================================================================
# CLUSTER G — over-rejection false pends (must ACCEPT). RED now.
# ===========================================================================

def test_G_house_prefix_christian_dior_accepted():
    assert _m("Dior Sauvage", "Christian Dior Sauvage Eau de Toilette",
              "fragrances", "Dior") is True


def test_G_house_prefix_gianni_versace_accepted():
    assert _m("Versace Eros", "Gianni Versace Eros", "fragrances", "Versace") is True


def test_G_giorgio_armani_alias_accepted():
    assert _m("Armani Acqua di Gio", "Giorgio Armani Acqua di Gio",
              "fragrances", "Armani") is True


def test_G_lancome_paris_house_accepted():
    assert _m("Lancome Idole", "Lancome Paris Idole", "fragrances", "Lancome") is True


def test_G_no_3_punctuation_spacing_accepted():
    assert _m("Olaplex No.3", "Olaplex No. 3 Hair Perfector", "haircare", "Olaplex") is True


def test_G_spf_spacing_accepted():
    assert _m("La Roche-Posay Anthelios SPF30",
              "La Roche-Posay Anthelios SPF 30", "skincare", "La Roche-Posay") is True


# ===========================================================================
# CLUSTER H — flag-OFF byte-identity. extract_jsonld_price adds name/brand keys
# unconditionally; with the gate OFF they must NOT appear (b207bfa parity).
# ===========================================================================

# ===========================================================================
# ROUND 2 — residual leaks the curated-marker / no-superset design still missed
# (found by the dispatcher's own coverage repro + the re-run coverage review).
# ===========================================================================

def test_R2_fashion_af1_silhouette_mid_rejected():
    # Low/Mid/High is a different silhouette SKU (AF1 default Low vs AF1 Mid).
    assert _m("Nike Air Force 1", "Nike Air Force 1 Mid", "fashion", "Nike") is False


def test_R2_fashion_af1_silhouette_high_rejected():
    assert _m("Nike Air Force 1", "Nike Air Force 1 High", "fashion", "Nike") is False


def test_R2_overrej_fashion_same_silhouette_colorway_accepted():
    # Same Low silhouette + a colourway word (stripped for fashion) must still match.
    assert _m("Nike Air Force 1 Low", "Nike Air Force 1 Low White", "fashion", "Nike") is True


def test_R2_skincare_line_add_copper_peptides_rejected():
    # A candidate ADDING a distinctive product-line token is a different SKU even though
    # skincare titles are descriptive — Buffet vs Buffet + Copper Peptides.
    assert _m("The Ordinary Buffet", "The Ordinary Buffet + Copper Peptides 1%",
              "skincare", "The Ordinary") is False


def test_R2_haircare_line_add_duo_rejected():
    assert _m("La Roche-Posay Effaclar", "La Roche-Posay Effaclar Duo",
              "haircare", "La Roche-Posay") is False


def test_R2_overrej_skincare_descriptive_form_accepted():
    # The descriptive form/skin-type words a skincare title carries must NOT over-reject.
    # (NOTE: benefit-LINE words like "Brightening"/"Clarifying" are NOT padding — they are
    # the variant-line discriminator, so they correctly pend a line-omitting query.)
    assert _m("The Ordinary Niacinamide 10%",
              "The Ordinary Niacinamide 10% Serum Hydrating",
              "skincare", "The Ordinary") is True


def test_R2_overrej_skincare_size_only_added_accepted():
    assert _m("CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream 340g Tub",
              "skincare", "CeraVe") is True


# ===========================================================================
# ROUND 3 — the coverage re-review (49 findings). The curated-marker approach is
# structurally leaky (sub-line/formulation/flavour tokens are unbounded); the
# general superset guard + per-category padding is the fix. Both directions.
# ===========================================================================

# --- electronics sub-line / model-gen leaks (must REJECT) ------------------
def test_R3_elec_kindle_paperwhite_rejected():
    assert _m("Kindle", "Kindle Paperwhite", "electronics", "Amazon") is False

def test_R3_elec_surface_laptop_studio_rejected():
    assert _m("Surface Laptop", "Surface Laptop Studio", "electronics", "Microsoft") is False

def test_R3_elec_mx_master_3s_rejected():
    assert _m("Logitech MX Master", "Logitech MX Master 3S Wireless Mouse", "electronics", "Logitech") is False

def test_R3_elec_dyson_v8_absolute_rejected():
    assert _m("Dyson V8", "Dyson V8 Absolute Cordless Vacuum", "electronics", "Dyson") is False

# --- electronics over-rejections (must ACCEPT) -----------------------------
def test_R3_overrej_elec_ordinal_generation_accepted():
    assert _m("Apple AirPods Pro 2", "Apple AirPods Pro (2nd Generation)", "electronics", "Apple") is True

def test_R3_overrej_elec_inch_hyphen_accepted():
    # The inch-marked screen size is one-sided-tolerant (stripped from identity); a
    # both-stated DIFFERENT inch is caught by _inch_mismatch. Same product, both inch-marked.
    assert _m("MacBook Pro 16-inch M3", "Apple MacBook Pro 16-inch M3", "electronics", "Apple") is True
    assert _m("Apple MacBook Pro M3", "Apple MacBook Pro 16-inch M3", "electronics", "Apple") is True
    # but DIFFERENT screen sizes (both stated) reject.
    assert _m("MacBook Pro 14-inch M3", "Apple MacBook Pro 16-inch M3", "electronics", "Apple") is False

def test_R3_overrej_elec_ram_not_storage_accepted():
    # Query pins RAM (8GB) + storage (256GB); a 256GB candidate that omits RAM must match.
    assert _m("Galaxy S24 8GB 256GB", "Samsung Galaxy S24 256GB Phantom Black", "electronics", "Samsung") is True

def test_R3_overrej_elec_brand_in_title_accepted():
    # A genuine title that adds the brand word the (brandless) query omits must match.
    assert _m("16-inch MacBook Pro M5", "16-inch MacBook Pro Apple M5", "electronics", "") is True

# --- supplement formulation / line leaks (must REJECT) ---------------------
def test_R3_supp_creatine_monohydrate_rejected():
    assert _m("Creatine", "Optimum Creatine Monohydrate", "supplements", "Optimum") is False

def test_R3_supp_collagen_type_rejected():
    assert _m("Collagen Type I", "NOW Collagen Type II", "supplements", "NOW") is False

def test_R3_supp_coq10_ubiquinol_rejected():
    assert _m("CoQ10", "Doctor's Best CoQ10 Ubiquinol", "supplements", "Doctor's Best") is False

def test_R3_supp_probiotics_once_daily_rejected():
    assert _m("Garden of Life Probiotics", "Garden of Life Probiotics Once Daily", "supplements", "Garden of Life") is False

def test_R3_supp_size_omit_pends():
    # Query states 5lb; candidate omits weight -> unverified -> pend (fail-closed, parity
    # with skincare/grocery + the dose/count omit).
    assert _m("Whey Protein 5lb", "Optimum Whey Protein", "supplements", "Optimum") is False

# --- supplement over-rejections (must ACCEPT) ------------------------------
def test_R3_overrej_supp_default_form_one_sided_accepted():
    assert _m("Vitamin D3 5000 IU Softgels", "NOW Vitamin D3 5000 IU", "supplements", "NOW") is True

def test_R3_overrej_supp_high_absorption_descriptive_accepted():
    assert _m("Magnesium Glycinate", "Doctor's Best High Absorption Magnesium Glycinate 240 Tablets",
              "supplements", "Doctor's Best") is True

# --- makeup format leaks (must REJECT) -------------------------------------
def test_R3_makeup_liquid_blush_rejected():
    assert _m("NARS Orgasm Blush", "NARS Orgasm Liquid Blush", "makeup", "NARS") is False

def test_R3_makeup_studio_fix_plus_rejected():
    assert _m("MAC Studio Fix", "MAC Studio Fix Plus", "makeup", "MAC") is False

def test_R3_makeup_waterproof_rejected():
    assert _m("Maybelline Lash Sensational", "Maybelline Lash Sensational Waterproof", "makeup", "Maybelline") is False

# --- makeup over-rejection (must ACCEPT) -----------------------------------
def test_R3_overrej_makeup_shade_name_with_matching_number_accepted():
    assert _m("Fenty Pro Filt'r Foundation 240", "Fenty Pro Filt'r Foundation 240 Soft Sand",
              "makeup", "Fenty") is True

# --- grocery flavour leaks (must REJECT) -----------------------------------
def test_R3_grocery_coke_cherry_rejected():
    assert _m("Coca-Cola", "Coca-Cola Cherry", "grocery", "Coca-Cola") is False

def test_R3_grocery_lays_bbq_rejected():
    assert _m("Lays", "Lays BBQ", "grocery", "Lays") is False

def test_R3_grocery_redbull_sugarfree_rejected():
    assert _m("Red Bull 250ml", "Red Bull Sugar Free 250ml", "grocery", "Red Bull") is False

# --- grocery over-rejections (must ACCEPT) ---------------------------------
def test_R3_overrej_grocery_original_taste_accepted():
    assert _m("Coca-Cola", "Coca-Cola Original Taste Soft Drink", "grocery", "Coca-Cola") is True

def test_R3_overrej_grocery_instant_coffee_accepted():
    assert _m("Nescafe Gold", "Nescafe Gold Instant Coffee Jar", "grocery", "Nescafe") is True

# --- fashion over-rejection (retro is a line word, must ACCEPT) ------------
def test_R3_overrej_fashion_retro_accepted():
    assert _m("Nike Dunk Low Panda", "Nike Dunk Low Retro Panda", "fashion", "Nike") is True

# --- skincare/haircare over-rejections (spelling, must ACCEPT) -------------
def test_R3_overrej_skincare_zs_spelling_accepted():
    assert _m("CeraVe Moisturizing Cream", "CeraVe Moisturising Cream 340g", "skincare", "CeraVe") is True

def test_R3_skincare_niacinamide_zinc_line_add_rejected():
    # +Zinc is a different SKU (line-add leak) — the descriptive-category superset must catch it.
    assert _m("The Ordinary Niacinamide", "The Ordinary Niacinamide 10% + Zinc 1%",
              "skincare", "The Ordinary") is False

def test_R3_overrej_haircare_masque_spelling_accepted():
    assert _m("Kerastase Nutritive Mask", "Kerastase Nutritive Masque 200ml", "haircare", "Kerastase") is True

# --- category inference (must route correctly) -----------------------------
def test_R3_infer_vitamin_c_serum_is_skincare():
    assert ps._infer_category_from_query("Vitamin C 10% Serum") == "skincare"

def test_R3_infer_dior_lip_glow_is_makeup():
    assert ps._infer_category_from_query("Dior Addict Lip Glow") == "makeup"

def test_R3_infer_grocery():
    assert ps._infer_category_from_query("Nescafe Gold Instant Coffee") == "grocery"


# ===========================================================================
# ROUND 4 — coverage re-review of keystone v2 (general superset + padding). Leak
# direction is solid; these are the padding-tuning findings (both directions).
# ===========================================================================

# --- CRITICAL: apostrophe gender forms (fashion) must ACCEPT ----------------
def test_R4_overrej_fashion_apostrophe_gender_accepted():
    assert _m("Nike Air Force 1 White", "Nike Air Force 1 Men's White", "fashion", "Nike") is True
    assert _m("Adidas Samba OG", "Adidas Women's Samba OG", "fashion", "Adidas") is True

# --- CRITICAL: makeup shade-NAME must discriminate when no shared number -----
def test_R4_makeup_shade_name_no_number_rejected():
    assert _m("Fenty Pro Filt'r Foundation Soft Sand", "Fenty Pro Filt'r Foundation Honey",
              "makeup", "Fenty") is False

def test_R4_overrej_makeup_shade_name_shared_number_accepted():
    assert _m("Maybelline Fit Me 220", "Maybelline Fit Me 220 Natural Beige",
              "makeup", "Maybelline") is True

# --- HIGH leaks from over-broad padding (must REJECT) -----------------------
def test_R4_electronics_refurbished_rejected():
    assert _m("Apple iPhone 15 128GB", "Apple iPhone 15 128GB Refurbished", "electronics", "Apple") is False

def test_R4_supplement_flavour_contradiction_rejected():
    assert _m("Dymatize ISO100 Vanilla", "Dymatize ISO100 Chocolate", "supplements", "Dymatize") is False

def test_R4_makeup_finish_contradiction_rejected():
    assert _m("Maybelline Fit Me 220 Matte", "Maybelline Fit Me 220 Dewy", "makeup", "Maybelline") is False

def test_R4_grocery_class_swap_rejected():
    assert _m("Nescafe Gold Coffee", "Nescafe Gold Tea", "grocery", "Nescafe") is False

def test_R4_electronics_ipod_nano_rejected():
    assert _m("Apple iPod", "Apple iPod Nano", "electronics", "Apple") is False

def test_R4_fragrance_dior_homme_intense_rejected():
    assert _m("Dior Homme", "Dior Homme Intense", "fragrances", "Dior") is False

# --- HIGH over-rejection padding gaps (must ACCEPT) -------------------------
def test_R4_overrej_electronics_descriptors_accepted():
    assert _m("Sony WH-1000XM5", "Sony WH-1000XM5 Wireless Noise Cancelling Headphones Black",
              "electronics", "Sony") is True
    # The trim words (Detect/Absolute) are in the query; the candidate adds only generic/
    # descriptive words (cordless/vacuum/cleaner) — must accept.
    assert _m("Dyson V15 Detect Absolute", "Dyson V15 Detect Absolute Cordless Vacuum Cleaner",
              "electronics", "Dyson") is True

def test_R4_overrej_supplement_descriptors_accepted():
    assert _m("Turmeric Curcumin", "NOW Turmeric Curcumin Extract 665mg 120 Veg Capsules",
              "supplements", "NOW") is True
    assert _m("Whey Protein", "Optimum Nutrition Gold Standard 100% Whey Protein Powder",
              "supplements", "Optimum") is True

def test_R4_overrej_supplement_veg_capsule_count_accepted():
    assert _m("NOW Magnesium Glycinate", "NOW Magnesium Glycinate 180 Veg Capsules",
              "supplements", "NOW") is True

def test_R4_overrej_skincare_skintype_accepted():
    assert _m("CeraVe Moisturizing Cream", "CeraVe Moisturizing Cream Normal to Dry Skin",
              "skincare", "CeraVe") is True

def test_R4_overrej_fashion_footwear_accepted():
    assert _m("Birkenstock Arizona", "Birkenstock Arizona Sandals", "fashion", "Birkenstock") is True

def test_R4_overrej_electronics_screen_inch_one_sided_accepted():
    assert _m("Apple MacBook Air M2", "Apple MacBook Air M2 13-inch", "electronics", "Apple") is True

def test_R4_overrej_brand_house_suffix_accepted():
    assert _m("Lancome Idole", "Lancome Paris Idole", "fragrances", "Lancome") is True


def test_H_jsonld_flag_off_no_name_brand_keys(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    html = _jsonld({"@type": "Product", "name": "Dior Sauvage EDT 100ml", "brand": "Dior",
                    "offers": {"@type": "Offer", "price": "45.000", "priceCurrency": "BHD",
                               "availability": "https://schema.org/InStock"}})
    res = ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml")
    assert res is not None
    # Flag-OFF must be byte-identical to b207bfa, which did NOT carry name/brand.
    assert "name" not in res
    assert "brand" not in res

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

# -*- coding: utf-8 -*-
"""genuine-price Wave-2 A0 — GOLDEN EQUIVALENCE CORPUS dump (design lane R5 STEP 0).

Enumerates (query, candidate_title, category, param-combo) cases COVERAGE-DRIVEN
(every residual-census class with its exact reproduction strings, >=12 real
products per category x every applicable axis x BOTH directions, every tolerance
family from descriptor-design.json F1/F2) and records the CURRENT verdict of the
5 decision functions:

    _axis_mismatch (strict_extras=True/False, brand ""/case-brand)
    _selection_match (candidate_brand none/matching/wrong x category real/"other"/None)
    is_exact_match (candidate_brand ""/case-brand)
    _backstop_identity_ok
    _category_type_added

The dump is BEHAVIOR PINNING, not correctness assertion — whatever the functions
return today (including exceptions, recorded as {"error": "<ExceptionType>"}) is
the contract the Phase-A VariantDescriptor refactor must reproduce byte-for-byte.
Replayed by tests/test_variant_descriptor_golden.py.

Run from the worktree root:
    python scripts/dump_descriptor_golden_corpus.py

Writes (UTF-8, sorted keys):
    tests/data/variant_descriptor_golden_corpus.json
    tests/data/variant_descriptor_golden_corpus.coverage.txt  (per-axis tally)

Windows discipline: ONLY ASCII is printed to the console; all non-ASCII output
goes to the UTF-8 files. Non-ASCII case strings are built from escapes so this
source file stays ASCII-safe.
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CORPUS_PATH = REPO / "tests" / "data" / "variant_descriptor_golden_corpus.json"
COVERAGE_PATH = REPO / "tests" / "data" / "variant_descriptor_golden_corpus.coverage.txt"

# A brand that appears in neither side of most cases — the "WRONG brand" param leg.
WRONG_BRAND = "Golden Goose"

# Non-ASCII building blocks (escapes keep this source ASCII).
TM = "™"                    # trademark sign
NBH = "‑"                   # non-breaking hyphen U+2011
GIO = "Acqua di Giò"        # Giò
LANCOME = "Lancôme"         # Lancôme
KERASTASE = "Kérastase"     # Kérastase

# ReDoS-cap inputs (>512 chars — _MATCH_INPUT_CAP truncates before trailing axis).
REDOS_QUERY = "Samsung Galaxy " + ("Ultra " * 110) + "256GB"
REDOS_TITLE = "Samsung Galaxy " + ("Ultra " * 110) + "512GB"
REDOS_TITLE_2 = "Samsung Galaxy S24 " + ("Phantom " * 100) + "512GB"

# ---------------------------------------------------------------------------
# PHASE-A-CLOSURE (B1.0) >512-char CAPPED-PARSE SEMANTICS inputs — the exact
# drift-reviewer shapes. These pin the ACCEPTED ruling: axis extractors see the
# _MATCH_INPUT_CAP(512)-capped text (with the partial-token-safe strip), so an
# axis token entirely PAST the cap is invisible, and a token SLICED AT the cap
# contributes nothing (never a phantom "Parfum" out of "Parfumerie").
# ---------------------------------------------------------------------------

# 531-char title where "Parfumerie" starts at index 506 — the plain slice at
# byte 512 used to leave a trailing "Parfum" (a MANUFACTURED flagship
# concentration). The partial-token-safe cap strips the fragment.
CAP_PARFUMERIE_TITLE = ("Dior Sauvage 100 ml " + ("Amber " * 81)
                        + "Parfumerie de Paris Store")
assert len(CAP_PARFUMERIE_TITLE) == 531, len(CAP_PARFUMERIE_TITLE)
assert CAP_PARFUMERIE_TITLE[506:512] == "Parfum", CAP_PARFUMERIE_TITLE[506:512]
assert CAP_PARFUMERIE_TITLE[512] == "e"

# Fragrance flagship "Parfum" ENTIRELY past byte 512 — invisible to the capped
# parse (legacy uncapped _category_type_added would have fired).
CAP_FLAGSHIP_PAST_TITLE = "Chanel Bleu de Chanel " + ("Amber " * 84) + "Parfum"
assert len(CAP_FLAGSHIP_PAST_TITLE) == 532
assert CAP_FLAGSHIP_PAST_TITLE.index("Parfum") > 512

# Supplement TYPE token ("Isolate") entirely past the cap.
CAP_SUPPLEMENT_PAST_TITLE = ("Optimum Nutrition Gold Standard Whey "
                             + ("Premium " * 60) + "Isolate")
assert len(CAP_SUPPLEMENT_PAST_TITLE) == 524
assert CAP_SUPPLEMENT_PAST_TITLE.index("Isolate") > 512

# Trailing "Eau de Toilette" entirely past the cap — the candidate's
# concentration is invisible to the capped parse.
CAP_EDT_PAST_TITLE = "Dior Sauvage " + ("Amber " * 84) + "Eau de Toilette"
assert len(CAP_EDT_PAST_TITLE) == 532
assert CAP_EDT_PAST_TITLE.index("Eau de Toilette") > 512


# ---------------------------------------------------------------------------
# Case enumeration
# ---------------------------------------------------------------------------

_CASES = []


def add(category, brand, query, title, axes, note=""):
    _CASES.append({
        "category": category,
        "brand": brand,
        "query": query,
        "title": title,
        "axes": sorted(set(axes)),
        "note": note,
    })


def _census_cases():
    """All 21 residual-census classes, exact reproduction strings from
    docs/investigations/2026-07-03-wave2-recon/residual-census.json."""
    add("fragrances", "Versace", "Versace Eros",
        "Versace Eros Pour Femme Eau de Parfum 100ml",
        ["census_gender_flanker", "gender_flanker"])
    add("fragrances", "Versace", "Versace Eros Pour Homme", "Versace Eros Pour Femme",
        ["census_gender_both_stated", "gender_contradiction"])
    add("fragrances", "Versace", "Versace Eros Pour Femme", "Versace Eros Eau de Parfum 100ml",
        ["census_femme_query_unconfirmed", "feminine_query_unconfirmed"])
    add("skincare", "Kiehl's", "Kiehl's Ultra Facial Cream",
        "Kiehl's Ultra Facial Cream SPF 30",
        ["census_spf_one_sided", "spf_one_sided", "apostrophe_fold"])
    add("fragrances", "Dior", "Dior Sauvage", "Dior Sauvage Parfum",
        ["census_conc_flanker_flagship", "flagship_concentration_add"])
    add("fragrances", "Dior", "Dior Sauvage", "Dior Sauvage Elixir",
        ["census_conc_flanker_same_token", "conc_flanker_same_token"])
    add("fragrances", "Carolina Herrera", "Carolina Herrera Good Girl", "Good Girl Supreme",
        ["census_conc_flanker_same_token", "conc_flanker_same_token"])
    add("fashion", "Nike", "Nike Air Force 1", "Nike Air Max 1",
        ["census_related_model", "related_model"])
    add("electronics", "Apple", "Apple AirPods Pro", "Apple AirPods Pro 2",
        ["census_bare_generation_int", "bare_generation_int"])
    add("electronics", "Apple", "Apple iPhone SE 2020", "Apple iPhone SE (2022)",
        ["census_year_only_generation", "year_annotation"])
    add("electronics", "Apple", "Apple iPhone SE", "Apple iPhone SE (2022) 64GB",
        ["census_year_only_generation", "year_annotation"],
        note="SE-year-add over-rejection direction (deliberate C1 bound)")
    add("makeup", "Maybelline", "Maybelline Fit Me Foundation 128",
        "Maybelline Fit Me Dewy + Smooth Foundation 128",
        ["census_makeup_formula", "finish_makeup", "makeup_shade_number",
         "plus_symbol_fold"])
    add("supplements", "Optimum Nutrition", "Optimum ZMA",
        "Optimum ZMA Zinc Magnesium Aspartate 180 Caps",
        ["census_acronym", "zma_acronym"])
    add("supplements", "NOW", "NOW Cal-Mag", "NOW Calcium Magnesium 250 Tablets",
        ["census_acronym", "zma_acronym"])
    add("supplements", "Nordic Naturals", "Nordic Naturals Omega-3", "Nordic Naturals Omega 3",
        ["census_hyphen_vs_space", "omega_hyphen_space"])
    add("fashion", "Uniqlo", "Uniqlo Oxford Shirt M", "Uniqlo Oxford Shirt XL",
        ["census_apparel_bare_size_letter", "clothing_size"])
    add("fashion", "Uniqlo", "Uniqlo Oxford Shirt Size M", "Uniqlo Oxford Shirt Size XL",
        ["census_apparel_bare_size_letter", "clothing_size"])
    add("fashion", "Adidas", "Adidas Trefoil T-Shirt", "Adidas Trefoil Stitch T-Shirt",
        ["census_disney_stitch", "fashion_construction_bigram"])
    add("skincare", "CeraVe", "CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream 177ml",
        ["census_cross_unit_g_ml", "cross_base_g_ml"])
    add("fragrances", "Dior", "Dior Sauvage Eau de Parfum", "Dior Sauvage",
        ["census_candidate_omits_query_axis", "candidate_missing_query_axis"])
    add("skincare", "CeraVe", "CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream",
        ["census_candidate_omits_query_axis", "candidate_missing_query_axis"])
    add("fragrances", "Dior", "Dior Sauvage", "",
        ["census_titleless", "empty_title"])
    add("electronics", "Nintendo", "Nintendo Switch 2",
        "Nintendo Switch 2, Light Blue and Light Red",
        ["census_switch_light_colourway", "color_fashion"])
    # ladder-exposure F1: the core retry term judged against the flanker candidates.
    add("fragrances", "Versace", "Eros", "Versace Eros Pour Femme",
        ["census_ladder_exposure", "gender_flanker"])
    add("fragrances", "Dior", "Sauvage", "Dior Sauvage Elixir",
        ["census_ladder_exposure", "conc_flanker_same_token"])
    add("electronics", "Samsung", REDOS_QUERY, REDOS_TITLE,
        ["census_redos_cap", "redos_cap", "storage"])
    add("electronics", "Samsung", "Samsung Galaxy S24 256GB", REDOS_TITLE_2,
        ["census_redos_cap", "redos_cap", "storage"])
    # design-accepts baseline control rows
    add("supplements", "Dymatize", "Dymatize ISO100", "Dymatize ISO100 Vanilla 5lb",
        ["census_design_accept", "flavour_supplement"])
    add("electronics", "Sony", "Sony Headphones", "Sony WH-CH520 Wireless Headphones",
        ["census_design_accept", "brand_class_query_skip"])


def _electronics_cases():
    c = "electronics"
    add(c, "Apple", "Apple iPhone 15 Pro 256GB", "Apple iPhone 15 Pro 512GB", ["storage"])
    add(c, "Apple", "Apple iPhone 15 Pro 256GB",
        "Apple iPhone 15 Pro 256GB Dual SIM Natural Titanium 5G",
        ["storage", "overrej_descriptive"])
    add(c, "Apple", "Apple iPhone 15 256GB", "Apple iPhone 15",
        ["candidate_missing_query_axis", "storage"])
    add(c, "Samsung", "Samsung Galaxy S24", "Samsung Galaxy S24 FE", ["electronics_qualifiers"])
    add(c, "Samsung", "Samsung Galaxy S24 Ultra 256GB",
        "Samsung Galaxy S24 Ultra 12GB+256GB Titanium Black",
        ["storage_max_not_ram", "storage", "plus_symbol_fold"])
    add(c, "Samsung", "Samsung Galaxy S24 Ultra 256GB",
        "Samsung Galaxy S24 Ultra 512GB 12GB RAM", ["storage", "storage_max_not_ram"])
    add(c, "Dell", "Dell XPS 13 16GB RAM 512GB", "Dell XPS 13 8GB RAM 512GB", ["ram"])
    add(c, "Dell", "Dell XPS 13 16GB RAM", "Dell XPS 13 16 GB RAM Laptop",
        ["ram", "spaced_units"])
    add(c, "Sony", "Sony WH-1000XM5", "Sony WF-1000XM5", ["wh1000xm5_spellings"])
    add(c, "Sony", "Sony WH-1000XM5", "Sony WH1000XM5 Wireless Noise Cancelling Headphones",
        ["wh1000xm5_spellings", "overrej_descriptive"])
    add(c, "Sony", "Sony WH-1000XM5", "Sony WH 1000XM5 Wireless Headphones",
        ["wh1000xm5_spellings"])
    add(c, "Sony", "Sony WH" + NBH + "1000XM5", "Sony WH-1000XM5",
        ["u2011_hyphen", "wh1000xm5_spellings"])
    add(c, "Apple", "Apple MacBook Air M3 8" + NBH + "Core CPU",
        "Apple MacBook Air M3 8-Core CPU", ["u2011_hyphen", "core_count"])
    add(c, "Apple", "Apple AirPods Pro", "Apple AirPods Pro 2 with MagSafe Case",
        ["bare_generation_int"])
    add(c, "Apple", "Apple AirPods Pro 2nd Generation", "Apple AirPods Pro 2 Generation",
        ["ordinal_fold"])
    add(c, "Apple", "Apple iPad 10th Generation 64GB", "Apple iPad 10 Generation 64GB WiFi",
        ["ordinal_fold"])
    add(c, "Amazon", "Amazon Kindle Paperwhite 11th Gen", "Amazon Kindle Paperwhite 11 Gen",
        ["ordinal_fold"])
    add(c, "Apple", "Apple MacBook Air M3 13", "Apple MacBook Air M3 13-inch Midnight",
        ["inch"])
    add(c, "Apple", "Apple MacBook Pro 14 Inch M3", "Apple MacBook Pro 14 M3", ["inch"])
    add(c, "Apple", "Apple iPad Pro 11", "Apple iPad Pro 12.9-inch", ["inch"])
    add(c, "Apple", "Apple MacBook Pro M3 Pro", "Apple MacBook Pro M3 Max", ["chip_tier"])
    add(c, "Apple", "Apple MacBook Air M2", "Apple MacBook Air M2 Pro", ["chip_tier"])
    add(c, "Apple", "Apple MacBook Air M3 8-Core CPU", "Apple MacBook Air M3 10-Core CPU",
        ["core_count"])
    add(c, "Apple", "Apple MacBook Air M3 8-Core CPU", "Apple MacBook Air M3 CPU 8 Core 256GB",
        ["core_count"])
    add(c, "Apple", "Apple MacBook Pro M3 11-Core CPU 14-Core GPU",
        "Apple MacBook Pro M3 11-Core CPU 18-Core GPU", ["core_count"])
    add(c, "Apple", "Apple iPad Air M3 128GB", "Apple iPad Air (2025) M3 128GB WiFi",
        ["year_annotation"])
    add(c, "Apple", "Apple iPad Air M3 128GB", "Apple iPad Air GEN 2025 M3 128GB",
        ["year_annotation"])
    add(c, "Apple", "Apple MacBook Air M5 512GB", "Apple MacBook Air GEN-2025 M5 512GB",
        ["year_annotation"])
    add(c, "Samsung", "Samsung Galaxy S25", "Samsung Galaxy S25 AI Smartphone 256GB",
        ["electronics_ai_tolerance"])
    add(c, "Nothing", "Nothing AI Phone", "Nothing AI Phone 256GB",
        ["electronics_ai_tolerance"])
    add(c, "Samsung", "Samsung Galaxy Book 4", "Samsung Galaxy Book 4 AI PC 512GB",
        ["electronics_ai_tolerance"])
    add(c, "Samsung", "Samsung Galaxy S24+", "Samsung Galaxy S24 Plus 256GB",
        ["plus_symbol_fold", "plus_variant"])
    add(c, "Samsung", "Samsung Galaxy S24", "Samsung Galaxy S24+", ["plus_variant"])
    add(c, "Apple", "Apple iPhone 15 Plus", "Apple iPhone 15", ["plus_variant"])
    add(c, "Sony", "Sony WH-1000XM5", "Sony WH-1000XM5 Renewed", ["condition"])
    add(c, "Apple", "Apple iPhone 13 Refurbished", "Apple iPhone 13", ["condition"])
    add(c, "Apple", "Apple iPhone 12 128GB", "Apple iPhone 12 128GB Preowned Grade A",
        ["condition"])
    add(c, "Nintendo", "Nintendo Switch 2", "Nintendo Switch 2 Mario Kart World Bundle",
        ["variant_add"])
    add(c, "Nintendo", "Nintendo Switch", "Nintendo Switch Lite", ["electronics_qualifiers"])
    add(c, "Samsung", "Samsung Galaxy Tab S9 128GB", "Samsung Galaxy Tab S9 FE 128GB",
        ["electronics_qualifiers"])
    add(c, "Apple", "Apple Watch Series 9 45mm", "Apple Watch Series 9 41mm", ["variant_add"])
    add(c, "Sony", "Sony PlayStation 5 Digital Edition", "Sony PlayStation 5 Disc Edition",
        ["variant_add"])
    add(c, "Canon", "Canon EOS R6", "Canon EOS R6 Mark II", ["variant_add"])
    add(c, "Amazon", "Amazon Kindle", "Amazon Kindle Paperwhite", ["variant_add"])
    add(c, "Sony", "Sony Headphones", "Sony SRS-XB100 Speaker", ["generic_class_swap"])
    add(c, "Shark", "Shark Navigator Vacuum", "Shark" + TM + " Navigator Vacuum", ["tm_strip"])
    add(c, "Anker", "Anker PowerCore 10000", "Anker" + TM + " PowerCore 10000 Power Bank",
        ["tm_strip", "overrej_descriptive"])
    add(c, "Apple", "", "Apple iPhone 15 Pro 256GB", ["empty_query"])
    add(c, "Apple", "Apple iPhone 15 Pro 256GB", "", ["empty_title"])
    add(c, "", "", "", ["empty_query", "empty_title"], note="both empty")


def _fragrances_cases():
    c = "fragrances"
    add(c, "Dior", "Dior Sauvage Eau de Toilette 100ml", "Dior Sauvage Eau de Parfum 100ml",
        ["concentration"])
    add(c, "Dior", "Dior Sauvage EDT 100ml", "Dior Sauvage Eau de Toilette 100 ml Spray",
        ["concentration", "spaced_units", "size_ml", "overrej_descriptive"])
    add(c, "Chanel", "Chanel Bleu de Chanel EDP", "Chanel Bleu de Chanel EDT", ["concentration"])
    add(c, "Chanel", "Chanel Bleu de Chanel", "Bleu de Chanel Parfum",
        ["flagship_concentration_add"])
    add(c, "YSL", "YSL Black Opium", "Black Opium Extrait de Parfum",
        ["flagship_concentration_add"])
    add(c, "Versace", "Versace Eros EDT 100ml", "Versace Eros EDT 50ml", ["size_ml"])
    add(c, "Versace", "Versace Eros EDT 100ml", "Versace Eros EDT 3.4 oz", ["size_oz"])
    add(c, "Creed", "Creed Aventus 50ml", "Creed Aventus 1.7 oz EDP", ["size_oz"])
    add(c, "Versace", "Versace Eros Eau de Toilette 90ml", "Versace Eros Eau de Toilette 90 ml",
        ["spaced_units"])
    add(c, "Armani", "Armani " + GIO, "Armani Acqua di Gio Eau de Toilette",
        ["nfkd_diacritics"])
    add(c, LANCOME, LANCOME + " La Vie Est Belle", "Lancome La Vie Est Belle EDP 75ml",
        ["nfkd_diacritics"])
    add(c, "Versace", "Versace Eros 100ml", "Versace Eros", ["candidate_missing_query_axis"])
    add(c, "Dior", "Dior Sauvage", "Dior Sauvage Deodorant Spray 150ml",
        ["form_fragrance_one_sided"])
    add(c, "Mugler", "Mugler Angel", "Mugler Angel Candle", ["form_fragrance_one_sided"])
    add(c, "Tom Ford", "Tom Ford Oud Wood", "Tom Ford Private Blend Oud Wood Eau de Parfum",
        ["conc_flanker_same_token", "overrej_descriptive"],
        note="base-name-word over-rejection guard: Private Blend Oud Wood IS Oud Wood")
    add(c, "Creed", "Creed Aventus", "Creed Aventus Absolu", ["conc_flanker_same_token"])
    add(c, "Carolina Herrera", "Carolina Herrera Good Girl",
        "Carolina Herrera Good Girl Blush", ["variant_add"])
    add(c, "Dior", "Dior Homme", "Dior Homme Intense",
        ["brand_class_query_skip", "variant_add"])
    add(c, "YSL", "YSL Black Opium", "Yves Saint Laurent Black Opium Eau de Parfum 90ml",
        ["overrej_descriptive"], note="brand-alias fold YSL")
    add(c, "YSL", "YSL Black Opium", "YSL Black Opium For Women EDP",
        ["gender_flanker"], note="For Women = SAME product (over-rejection guard)")
    add(c, "Armani", "Armani Code Femme", "Armani Code", ["feminine_query_unconfirmed"])
    add(c, "Paco Rabanne", "Paco Rabanne 1 Million", "Paco Rabanne 1 Million Lucky",
        ["variant_add"])
    add(c, "Marc Jacobs", "Marc Jacobs Daisy", "Daisy Eau So Fresh", ["variant_add"],
        note="brand-omitted sephora-style title")
    add(c, "Valentino", "Valentino Uomo", "Valentino Uomo Born in Roma", ["variant_add"])
    add(c, "Prada", "Prada Luna Rossa", "Prada Luna Rossa Ocean", ["variant_add"])
    add(c, "Giorgio Armani", "Giorgio Armani Si", "Giorgio Armani Si Passione", ["variant_add"])
    add(c, "Mugler", "Mugler Alien", "Mugler Alien Goddess", ["variant_add"])
    add(c, "Dior", "Dior Sauvage Elixir 60ml", "Dior Sauvage Elixir 60ml Spray",
        ["overrej_descriptive", "conc_flanker_same_token"])
    add(c, "Versace", "Versace Eros Pour Femme EDP",
        "Versace Eros Pour Femme Eau de Parfum 100ml Spray for Women",
        ["feminine_query_unconfirmed", "overrej_descriptive"],
        note="femme query CONFIRMED by the candidate")
    add(c, "Gucci", "Gucci Bloom", "Gucci Bloom Nettare di Fiori", ["variant_add"])
    add(c, "Dior", "", "Dior Sauvage Eau de Toilette", ["empty_query"])
    add(c, "Mugler", "Mugler Angel", "", ["empty_title"])


def _fashion_cases():
    c = "fashion"
    add(c, "Nike", "Nike Dunk Low", "Nike Air Force 1", ["related_model"])
    add(c, "Nike", "Nike Air Force 1", "Nike Air Force 1 '07 White Mens Sneakers",
        ["overrej_descriptive", "apostrophe_fold"])
    add(c, "Adidas", "Adidas Trefoil T-Shirt", "Adidas Trefoil T-Shirt with stitched logo",
        ["fashion_construction_bigram"])
    add(c, "Nike", "Nike Sportswear Club T-Shirt", "Nike Sportswear Club Crew Neck T-Shirt",
        ["fashion_construction_bigram"])
    add(c, "Levi's", "Levi's 501 Jeans", "Levi's 501 contrast stitch Jeans",
        ["fashion_construction_bigram"])
    add(c, "Ray-Ban", "Ray-Ban Aviator RB3025", "Ray-Ban Aviator RB3025 002/58 Gold 58mm",
        ["eyewear_model_code", "eyewear_colorway", "eyewear_lens_mm"])
    add(c, "Ray-Ban", "Ray-Ban RB3025", "Ray-Ban 0RB3025 Aviator",
        ["zero_prefix_code", "eyewear_model_code"])
    add(c, "Oakley", "Oakley Holbrook OO9102", "Oakley Holbrook 0OO9102 Matte Black Prizm 55mm",
        ["zero_prefix_code", "eyewear_model_code", "eyewear_colorway", "eyewear_lens_mm"])
    add(c, "Ray-Ban", "Ray-Ban Wayfarer RB2140", "Ray-Ban Wayfarer RB2132",
        ["eyewear_model_code"])
    add(c, "Nike", "Nike Air Force 1 US 9", "Nike Air Force 1 US 10.5", ["shoe_size"])
    add(c, "Adidas", "Adidas Samba EU 42", "Adidas Samba EU 44", ["shoe_size"])
    add(c, "Nike", "Nike Air Force 1 US 9", "Nike Air Force 1",
        ["candidate_missing_query_axis", "shoe_size"])
    add(c, "Levi's", "Levi's 501 Jeans", "Levis 501 Original Jeans", ["apostrophe_fold"])
    add(c, "Levi's", "Levi's 501 Slim Fit", "Levi's 501 Regular Fit", ["fit_fashion"])
    add(c, "Nike", "Nike Tech Fleece Oversized Hoodie", "Nike Tech Fleece Fitted Hoodie",
        ["fit_fashion"])
    add(c, "Zara", "Zara Linen Blazer", "Zara Wool Blazer", ["material_fashion"])
    add(c, "Puma", "Puma Suede Classic", "Puma Leather Classic Sneakers", ["material_fashion"])
    add(c, "Puma", "Puma Suede Classic", "Puma Suede Classic XXI Sneakers",
        ["overrej_descriptive", "variant_add"])
    add(c, "Puma", "Puma Suede", "Puma RS-X", ["brand_class_query_skip"],
        note="fashion is EXCLUDED from the generic-query skip")
    add(c, "Adidas", "Adidas Samba SE", "Adidas Samba Special Edition",
        ["se_specialedition_unify"])
    add(c, "Nike", "Nike Air Max 90 SE", "Nike Air Max 90 Special Edition White",
        ["se_specialedition_unify"])
    add(c, "Nike", "Nike Air Max 90 SE", "Nike Air Max 90 Limited Edition",
        ["se_specialedition_unify"])
    add(c, "Adidas", "Adidas Samba", "Adidas Samba SE",
        ["se_specialedition_unify", "variant_add"])
    add(c, "Nike", "Nike Air Max 90", "Nike Air Max 2021", ["year_annotation"],
        note="bare mid-title year is a MODEL name — stays identity")
    add(c, "Nike", "Nike Air Max 2021", "Nike Air Max 2021 White", ["year_annotation",
        "overrej_descriptive"])
    add(c, "Tommy Hilfiger", "Tommy Hilfiger Polo Shirt", "Tommy Hilfiger Poloshirt Classic",
        ["polo_compound"])
    add(c, "Lacoste", "Lacoste Polo Shirt", "Lacoste Polo-Shirt Short Sleeve",
        ["polo_compound"])
    add(c, "Nike", "Nike Air Force 1 White", "Nike Air Force 1 Black", ["color_fashion"])
    add(c, "Adidas", "Adidas Gazelle Blue", "Adidas Gazelle Bold Pink",
        ["color_fashion", "variant_add"])
    add(c, "Adidas", "Adidas Superstar", "Golden Goose Superstar", ["wrong_brand_fence"],
        note="same-model-word different brand — the CRITICAL fence class")
    add(c, "New Balance", "New Balance 574", "New Balance 574 Grey Suede",
        ["material_fashion", "overrej_descriptive"])
    add(c, "H&M", "H&M Crew Neck T-Shirt", "H&amp;M Crew Neck T-Shirt",
        ["html_entity_amp", "fashion_construction_bigram"])
    add(c, "Zara", "Zara Dress", "Zara Skirt", ["generic_class_swap"])
    add(c, "Calvin Klein", "Calvin Klein Men's Cotton T-Shirt",
        "Calvin Klein Women's Cotton T-Shirt", ["gender_contradiction"])
    add(c, "Nike", "Nike Air Max 270 Women", "Nike Air Max 270",
        ["feminine_query_unconfirmed"])
    add(c, "Uniqlo", "Uniqlo Oxford Shirt", "Uniqlo Oxford Shirt Slim Fit L",
        ["clothing_size", "fit_fashion"])
    add(c, "Zara", "Zara Linen Blazer Size S", "Zara Linen Blazer Size L", ["clothing_size"])
    add(c, "Nike", "", "Nike Air Force 1 White", ["empty_query"])
    add(c, "Nike", "Nike Air Force 1", "", ["empty_title"])


def _supplements_cases():
    c = "supplements"
    add(c, "Nordic Naturals", "Nordic Naturals Omega 3 690mg",
        "Nordic Naturals Omega-3 690 mg Softgels",
        ["omega_hyphen_space", "strength", "spaced_units"])
    add(c, "NOW", "NOW Omega-3 200 Softgels", "NOW Omega-3 100 Softgels",
        ["count", "omega_hyphen_space"])
    add(c, "Jarrow", "Jarrow Co-Q10 100mg", "Jarrow CoQ10 100 mg 60 Capsules",
        ["omega_hyphen_space", "spaced_units", "strength"])
    add(c, "Optimum Nutrition", "Optimum Nutrition Gold Standard Whey",
        "Optimum Nutrition Gold Standard Whey Isolate", ["supplement_type_add"])
    add(c, "Dymatize", "Dymatize Whey Concentrate", "Dymatize Whey Hydrolysate",
        ["supplement_type_add"])
    add(c, "Optimum Nutrition", "ON Gold Standard Whey Vanilla", "ON Gold Standard Whey Chocolate",
        ["flavour_supplement"])
    add(c, "Optimum Nutrition", "ON Gold Standard Whey",
        "ON Gold Standard Whey Double Rich Chocolate 5lb",
        ["flavour_supplement", "weight_volume"],
        note="one-sided flavour add tolerated for supplements")
    add(c, "NOW", "NOW Magnesium", "NOW Magnesium Glycinate 400mg", ["supplement_salt_form"])
    add(c, "Solgar", "Solgar Zinc", "Solgar Zinc Picolinate 22mg", ["supplement_salt_form"])
    add(c, "Doctor's Best", "Doctor's Best Calcium", "Calcium Magnesium Zinc 90 Tablets",
        ["multi_constituent", "supplement_type_add", "apostrophe_fold"],
        note="single-constituent query + COMBO add must stay rejected")
    add(c, "NOW", "NOW B-Complex", "NOW B-Complex with B12 B6 Folate Biotin",
        ["multi_constituent"])
    add(c, "Centrum", "Centrum Multivitamin", "Centrum Multivitamin with Iron Zinc",
        ["multi_constituent"])
    add(c, "Garden of Life", "Garden of Life Prenatal",
        "Garden of Life Prenatal with Folic Acid and Iron", ["multi_constituent"])
    add(c, "Centrum", "Centrum", "Centrum Silver", ["supplement_type_add"])
    add(c, "Kirkland", "Kirkland Fish Oil", "Kirkland Fish Oil Triple Strength",
        ["supplement_type_add"])
    add(c, "Nature Made", "Nature Made Vitamin D3 1000 IU", "Nature Made Vitamin D3 2000 IU",
        ["strength"])
    add(c, "Nature Made", "Nature Made Vitamin D3 1,000 IU",
        "Nature Made Vitamin D3 1000 IU 100 Softgels",
        ["strength", "count", "overrej_descriptive"],
        note="comma-thousands dose spelling")
    add(c, "Solgar", "Solgar Vitamin C 100 Tablets", "Solgar Vitamin C 250 Tablets", ["count"])
    add(c, "Solgar", "Solgar Vitamin C 1000mg", "Solgar Vitamin E 1000mg", ["vitamin_letter"])
    add(c, "Nature Made", "Nature Made Vitamin D3", "Nature Made Vitamin C", ["vitamin_letter"])
    add(c, "Solgar", "Solgar Vitamin D3 5000", "Solgar Vitamin D3 1000", ["bare_dose"])
    add(c, "Natrol", "Natrol Melatonin 10", "Natrol Melatonin 5", ["bare_dose"])
    add(c, "MuscleTech", "MuscleTech Creatine", "MuscleTech Creatine Monohydrate 400g",
        ["variant_add", "weight_volume"])
    add(c, "NOW", "NOW Vitamin C", "NOW Vitamin C Gummies", ["supplement_form_added"])
    add(c, "Natrol", "Natrol Melatonin 5mg", "Natrol Melatonin 5mg Gummies",
        ["supplement_form_added", "strength"])
    add(c, "Solgar", "Solgar Vitamin D3 5000 IU", "Solgar Vitamin D3",
        ["candidate_missing_query_axis", "strength"])
    add(c, "Optimum Nutrition", "ON Gold Standard Whey 5lb", "ON Gold Standard Whey 2lb",
        ["weight_volume"])
    add(c, "Vitabiotics", "Vitabiotics Wellman", "Vitabiotics Wellwoman", ["variant_add"])
    add(c, "Dymatize", "Dymatize ISO100 908g", "Dymatize ISO100 908 g Whey Protein Isolate",
        ["spaced_units", "supplement_type_add", "overrej_descriptive"])
    add(c, "NOW", "NOW Vitamin C", "", ["empty_title"])


def _grocery_cases():
    c = "grocery"
    add(c, "Cheerios", "Cheerios", "Chocolate Cheerios", ["flavour_grocery_add"])
    add(c, "Pringles", "Pringles Original", "Pringles Cheese", ["flavour_grocery_add"])
    add(c, "Pringles", "Pringles", "Pringles Sour Cream and Onion", ["flavour_grocery_add"])
    add(c, "Cadbury", "Cadbury Dairy Milk", "Cadbury Dairy Milk Fruit and Nut",
        ["flavour_grocery_add"])
    add(c, "Nescafe", "Nescafe Gold", "Nescafe Gold Decaf", ["variant_add"])
    add(c, "Nescafe", "Nescafe Gold Instant Coffee", "Nescafe Gold Ground Coffee",
        ["grocery_prep"])
    add(c, "Quaker", "Quaker Instant Oats", "Quaker Whole Rolled Oats", ["grocery_prep"])
    add(c, "Skippy", "Skippy Smooth Peanut Butter", "Skippy Crunchy Peanut Butter",
        ["grocery_prep"])
    add(c, "Almarai", "Almarai Full Fat Milk 1L", "Almarai Skimmed Milk 1L",
        ["grocery_prep", "weight_volume"])
    add(c, "Coca-Cola", "Coca-Cola 6 Pack", "Coca-Cola 12 Pack", ["pack"])
    add(c, "Pepsi", "Pepsi 24 Pack Cans", "Pepsi 6 Pack Cans", ["pack"])
    add(c, "Coca-Cola", "Coca-Cola 6 Pack", "Coca-Cola", ["candidate_missing_query_axis",
        "pack"])
    add(c, "Red Bull", "Red Bull Sugar Free", "Red Bull Sugarfree 250ml", ["sugar_free_glue"])
    add(c, "Red Bull", "Red Bull", "Red Bull Sugar Free", ["sugar_free_glue", "variant_add"])
    add(c, "Monster", "Monster Energy Sugar Free 500ml", "Monster Energy Sugar-Free 500 ml",
        ["sugar_free_glue", "spaced_units"])
    add(c, "Nutella", "Nutella 750g", "Nutella 400g", ["weight_volume"])
    add(c, "Nutella", "Nutella 750g", "Nutella 750 g Jar", ["weight_volume", "spaced_units"])
    add(c, "Quaker", "Quaker Oats 1kg", "Quaker Oats 2 x 500g", ["weight_volume"],
        note="headline-max per base")
    add(c, "Coca-Cola", "Coca-Cola 330ml", "Coca-Cola 1.5L", ["weight_volume"])
    add(c, "Nescafe", "Nescafe Gold 200g", "Nescafe Gold 200ml", ["cross_base_g_ml"])
    add(c, "Heinz", "Heinz Tomato Ketchup 570g", "Heinz Tomato Ketchup 570ml",
        ["cross_base_g_ml"])
    add(c, "Lipton", "Lipton Yellow Label Tea 100 Bags", "Lipton Yellow Label Tea 200 Bags",
        ["count"])
    add(c, "Barilla", "Barilla Spaghetti 500g", "Barilla Penne 500g", ["variant_add"])
    add(c, "KitKat", "KitKat 4 Finger", "KitKat Chunky", ["variant_add", "count"])
    add(c, "Kellogg's", "Kellogg's Corn Flakes 500g", "Kelloggs Corn Flakes 500 g",
        ["apostrophe_fold", "spaced_units"])
    add(c, "Quaker", "Quaker Oats", "Quaker Oats 1kg", ["weight_volume",
        "overrej_descriptive"])
    add(c, "Heinz", "Heinz Ketchup", "", ["empty_title"])


def _makeup_cases():
    c = "makeup"
    add(c, "Maybelline", "Maybelline Fit Me 240", "Maybelline Fit Me 240 Soft Sand",
        ["makeup_shade_number"])
    add(c, "Maybelline", "Maybelline Fit Me 220", "Maybelline Fit Me 220 320",
        ["makeup_shade_number"], note="extra shade number must still reject")
    add(c, "Maybelline", "Maybelline Fit Me 240", "Maybelline Superstay 240",
        ["makeup_shade_number"], note="different line sharing a shade code")
    add(c, "Maybelline", "Maybelline Fit Me Matte and Poreless 130",
        "Maybelline Fit Me Dewy and Smooth 130", ["finish_makeup", "makeup_shade_number"])
    add(c, "L'Oreal", "L'Oreal Infallible Matte 130", "L'Oreal Infallible Glow 130",
        ["finish_makeup", "makeup_shade_number", "apostrophe_fold"])
    add(c, "Maybelline", "Maybelline Fit Me 310", "Maybelline Fit Me 310 Sun Beige Smooth Coverage",
        ["finish_makeup", "makeup_shade_number", "overrej_descriptive"],
        note="Smooth Coverage descriptive-title over-rejection guard")
    add(c, "NYX", "NYX Soft Matte Lip Cream", "NYX Hydrating Lip Cream", ["finish_makeup"])
    add(c, "Benefit", "Benefit Hoola Bronzer", "Benefit Hoola Matte Bronzer", ["finish_makeup"])
    add(c, "MAC", "MAC Ruby Woo", "MAC Ruby Woo Lipstick", ["form_makeup"])
    add(c, "Charlotte Tilbury", "Charlotte Tilbury Airbrush Flawless Setting Spray",
        "Charlotte Tilbury Airbrush Flawless Powder", ["form_makeup"])
    add(c, "Rare Beauty", "Rare Beauty Soft Pinch Liquid Blush",
        "Rare Beauty Soft Pinch Powder Blush", ["form_makeup", "variant_add"])
    add(c, "Fenty", "Fenty Beauty Pro Filt'r Foundation 240",
        "Fenty Beauty Pro Filt'r Foundation 250",
        ["makeup_shade_number", "apostrophe_fold"])
    add(c, "Dior", "Dior Backstage Foundation 2N", "Dior Backstage Foundation 3N",
        ["makeup_shade_number", "variant_add"])
    add(c, "Maybelline", "Maybelline Sky High Mascara", "Maybelline Sky High Waterproof Mascara",
        ["variant_add"])
    add(c, "L'Oreal", "L'Oreal Colour Riche Lipstick", "L'Oreal Color Riche Lipstick",
        ["british_spelling_fold"])
    add(c, "Revlon", "Revlon ColorStay Foundation", "Revlon ColourStay Foundation",
        ["british_spelling_fold"])
    add(c, "NARS", "NARS Radiant Creamy Concealer",
        "NARS Radiant Creamy Concealer Custard 6ml", ["variant_add", "overrej_descriptive"])
    add(c, "Huda Beauty", "Huda Beauty Easy Bake Loose Powder",
        "Huda Beauty Easy Bake Loose Powder Blondie", ["variant_add"])
    add(c, "NYX", "NYX Butter Gloss Praline", "NYX Butter Gloss Madeleine", ["variant_add"])
    add(c, "The Ordinary", "The Ordinary Concealer 2.0 N", "The Ordinary Concealer 3.0 N",
        ["makeup_shade_number", "variant_add"])
    add(c, "MAC", "MAC Studio Fix Fluid NC20 30ml", "MAC Studio Fix Fluid NC20 30 ml",
        ["spaced_units", "makeup_shade_number", "overrej_descriptive"])
    add(c, "Maybelline", "Maybelline Fit Me 128", "", ["empty_title"])


def _skincare_cases():
    c = "skincare"
    add(c, "La Roche-Posay", "La Roche-Posay Anthelios SPF 50", "La Roche-Posay Anthelios SPF 30",
        ["spf_both_stated"])
    add(c, "Aveeno", "Aveeno Daily Moisturizing Lotion SPF 15",
        "Aveeno Daily Moisturizing Lotion SPF 30", ["spf_both_stated"])
    add(c, "La Roche-Posay", "La Roche-Posay Anthelios",
        "La Roche-Posay Anthelios SPF 50 Invisible Fluid", ["spf_one_sided"],
        note="inherent-SPF sunscreen line — over-rejection guard")
    add(c, "Supergoop", "Supergoop Unseen Sunscreen SPF 40",
        "Supergoop Unseen Sunscreen SPF 40 50ml",
        ["spf_both_stated", "overrej_descriptive"])
    add(c, "The Ordinary", "The Ordinary Niacinamide 10% + Zinc 1%",
        "The Ordinary Niacinamide 10% Zinc 1% 30ml",
        ["percent", "plus_symbol_fold", "overrej_descriptive"])
    add(c, "The Ordinary", "The Ordinary Niacinamide 10%", "The Ordinary Niacinamide 5%",
        ["percent"])
    add(c, "The Ordinary", "The Ordinary Niacinamide 10%",
        "The Ordinary Niacinamide 10 percent Serum", ["percent"])
    add(c, "The Ordinary", "The Ordinary Hyaluronic Acid 2%", "The Ordinary Hyaluronic Acid 5%",
        ["percent"])
    add(c, "The Ordinary", "The Ordinary Niacinamide 10%", "The Ordinary Niacinamide",
        ["candidate_missing_query_axis", "percent"])
    add(c, "CeraVe", "CeraVe Moisturizing Cream", "CeraVe Moisturizing Lotion",
        ["form_both_stated"])
    add(c, "Eucerin", "Eucerin Advanced Repair Cream", "Eucerin Advanced Repair Lotion",
        ["form_both_stated"])
    add(c, "Cetaphil", "Cetaphil Gentle Skin Cleanser", "Cetaphil Gentle Skin Cream",
        ["form_both_stated"])
    add(c, "Neutrogena", "Neutrogena Hydro Boost Water Gel 50g",
        "Neutrogena Hydro Boost Water Gel 50ml", ["cross_base_g_ml"])
    add(c, "Bioderma", "Bioderma Sensibio H2O 500ml", "Bioderma Sensibio H2O 250ml",
        ["size_ml"])
    add(c, "Bioderma", "Bioderma Sensibio H2O 500ml", "Bioderma Sensibio H2O 500 ml Micellar Water",
        ["spaced_units", "size_ml", "overrej_descriptive"])
    add(c, "Garnier", "Garnier Micellar Water 400ml", "Garnier Micellar Water 700ml",
        ["size_ml"])
    add(c, "La Roche-Posay", "La Roche-Posay Effaclar Duo+", "La Roche-Posay Effaclar Duo Plus",
        ["plus_symbol_fold"])
    add(c, "La Roche-Posay", "La Roche-Posay Effaclar Duo", "La Roche-Posay Effaclar Duo+ M",
        ["plus_variant"])
    add(c, "The Ordinary", "The Ordinary Buffet", "The Ordinary Buffet + Copper Peptides",
        ["plus_variant", "variant_add"])
    add(c, "Vichy", "Vichy Mineral 89", "Vichy Mineral 89 Booster 50ml",
        ["overrej_descriptive"])
    add(c, "Olay", "Olay Regenerist Micro-Sculpting Cream",
        "Olay Regenerist Micro Sculpting Cream 50g", ["omega_hyphen_space",
        "overrej_descriptive"])
    add(c, "Clinique", "Clinique Moisture Surge 100H", "Clinique Moisture Surge 72H",
        ["variant_add"])
    add(c, "Kiehl's", "Kiehl's Ultra Facial Cream 50ml", "Kiehls Ultra Facial Cream 50ml",
        ["apostrophe_fold"])
    add(c, "CeraVe", "CeraVe Foaming Cleanser", "", ["empty_title"])


def _haircare_cases():
    c = "haircare"
    add(c, "Olaplex", "Olaplex No. 3", "Olaplex No 3 Hair Perfector 100ml",
        ["ordinal_fold", "overrej_descriptive"], note="no.-number glue fold")
    add(c, "Olaplex", "Olaplex No. 3", "Olaplex No. 5", ["variant_add"])
    add(c, "Rogaine", "Rogaine Minoxidil 5%", "Rogaine Minoxidil 2%", ["percent"])
    add(c, "Nizoral", "Nizoral Anti-Dandruff Shampoo 2%", "Nizoral Anti-Dandruff Shampoo 1%",
        ["percent"])
    add(c, "Moroccanoil", "Moroccanoil Treatment 100ml", "Moroccanoil Treatment 25ml",
        ["size_ml"])
    add(c, "OGX", "OGX Argan Oil Shampoo", "OGX Argan Oil Conditioner", ["form_both_stated"])
    add(c, "Dove", "Dove Intensive Repair Shampoo", "Dove Intensive Repair Conditioner",
        ["form_both_stated"])
    add(c, "Head & Shoulders", "Head & Shoulders Classic Clean",
        "Head &amp; Shoulders Classic Clean Shampoo 400ml",
        ["html_entity_amp", "overrej_descriptive"])
    add(c, "Pantene", "Pantene Pro-V Repair", "Pantene Pro V Repair Shampoo",
        ["omega_hyphen_space"])
    add(c, "Tresemme", "Tresemme Keratin Smooth Shampoo 400ml",
        "Tresemme Keratin Smooth Shampoo 700ml", ["size_ml"])
    add(c, "Batiste", "Batiste Dry Shampoo Original", "Batiste Dry Shampoo Cherry",
        ["variant_add"])
    add(c, KERASTASE, KERASTASE + " Elixir Ultime Oil", "Kerastase Elixir Ultime Oil 100ml",
        ["nfkd_diacritics", "overrej_descriptive"])
    add(c, "L'Oreal", "L'Oreal Elvive Total Repair 5", "Loreal Elvive Total Repair 5 Shampoo",
        ["apostrophe_fold"])
    add(c, "Herbal Essences", "Herbal Essences Bio Renew Argan Oil",
        "Herbal Essences Bio Renew Coconut Milk", ["variant_add"])
    add(c, "Aussie", "Aussie Miracle Moist Shampoo 300ml", "Aussie Miracle Moist Shampoo 300 ml",
        ["spaced_units", "size_ml"])
    add(c, "Shark", "Shark FlexStyle" + TM, "Shark FlexStyle Air Styler", ["tm_strip"])
    add(c, "Olaplex", "Olaplex No. 3", "", ["empty_title"])


def _other_cases():
    c = "other"
    add(c, "Lego", "Lego Star Wars Millennium Falcon", "Lego Star Wars X-Wing", ["variant_add"])
    add(c, "Stanley", "Stanley Quencher 40oz", "Stanley Quencher 30oz", ["size_oz"])
    add(c, "Yeti", "Yeti Rambler 20oz", "Yeti Rambler 20oz Stainless Steel Tumbler",
        ["size_oz", "overrej_descriptive"])
    add(c, "Zippo", "Zippo Classic Lighter", "Zippo Classic Lighter Brushed Chrome",
        ["overrej_descriptive"])
    add(c, "Moleskine", "Moleskine Classic Notebook Large", "Moleskine Classic Notebook Pocket",
        ["variant_add"])
    add(c, "Casio", "Casio F-91W", "Casio F91W Digital Watch", ["omega_hyphen_space"])
    add(c, "Parker", "Parker Jotter Pen", "Parker Jotter XL Pen", ["variant_add",
        "clothing_size"], note="XL outside fashion")
    add(c, "Rubik's", "Rubik's Cube 3x3", "Rubiks Cube 4x4", ["apostrophe_fold",
        "variant_add"])
    add(c, "Thermos", "Thermos Stainless King 1.2L", "Thermos Stainless King 470ml",
        ["weight_volume"])
    add(c, "3M", "3M Command Strips 12 Pack", "3M Command Strips 20 Pack", ["pack"],
        note="pack axis is grocery-scoped — pin the 'other' behavior")
    add(c, "Sharpie", "Sharpie Permanent Markers 12 Count", "Sharpie Permanent Markers 24 Count",
        ["count"])
    add(c, "Duracell", "Duracell AA Batteries 8 Count", "Duracell AAA Batteries 8 Count",
        ["variant_add"])
    add(c, "Stanley", "Stanley Quencher 40oz", "", ["empty_title"])


def _tolerance_param_probes():
    """Extra rows exercising folds/tolerances where the interesting variance is in
    the PARAM combos (brand subtraction, category=other/None re-inference)."""
    add("fragrances", "Marc Jacobs", "Marc Jacobs Daisy", "Daisy - Eau de Toilette",
        ["overrej_descriptive"], note="brand-omitted title: candidate_brand leg matters")
    add("fragrances", "Tom Ford", "TF Oud Wood", "Tom Ford Oud Wood Eau de Parfum 50ml",
        ["overrej_descriptive"], note="brand alias TF")
    add("electronics", "Apple", "AirPods Pro", "Apple AirPods Pro (2nd Generation)",
        ["bare_generation_int", "ordinal_fold"])
    add("electronics", "Apple", "Apple AirPods Pro 2", "Apple AirPods Pro",
        ["bare_generation_int"], note="census reverse direction, explicit")
    add("fashion", "Nike", "Nike Air Force 1", "Nike Air Force 1 Shadow",
        ["variant_add", "color_fashion"])
    add("supplements", "Optimum Nutrition", "Optimum ZMA 90 Caps", "Optimum ZMA 180 Caps",
        ["count", "zma_acronym"])
    add("grocery", "Red Bull", "Red Bull Sugarfree", "Red Bull Sugar Free 4 Pack",
        ["sugar_free_glue", "pack"])
    add("makeup", "Maybelline", "Maybelline Fit Me Concealer 20", "Maybelline Fit Me Concealer 25",
        ["makeup_shade_number", "variant_add"])
    add("skincare", "CeraVe", "CeraVe SA Cream", "CeraVe SA Smoothing Cream 340g",
        ["overrej_descriptive", "se_specialedition_unify"],
        note="SA tokens outside fashion SE-unify scope")
    add("haircare", "Pantene", "Pantene 2 in 1 Shampoo", "Pantene 3 Minute Miracle",
        ["variant_add"])
    add("other", "Casio", "Casio Watch", "Casio G-Shock GA-2100", ["brand_class_query_skip"],
        note="generic query in 'other' category")
    add("electronics", "Sony", "Sony 65 Inch Bravia TV", "Sony Bravia 65\" 4K TV",
        ["inch", "overrej_descriptive"])


def _capped_semantics_rows():
    """PHASE-A-CLOSURE (B1.0) — the >512-char capped-parse semantics rows,
    returned FULLY FORMED and appended AFTER the padded/swap passes in
    build_cases so every pre-existing case id stays stable (ids are positional).
    They deliberately skip the padded/swap passes: the padded pass excludes
    >400-char titles anyway, and each direction of interest is pinned
    explicitly here."""
    rows = [
        {
            "category": "fragrances", "brand": "Dior",
            "query": "Dior Sauvage", "title": CAP_PARFUMERIE_TITLE,
            "axes": sorted({"capped_semantics", "redos_cap",
                            "flagship_concentration_add"}),
            "note": ("531-char title: 'Parfumerie' sliced at byte 512 used to "
                     "manufacture a phantom flagship 'Parfum' — the "
                     "partial-token-safe cap strips the fragment"),
        },
        {
            "category": "fragrances", "brand": "Chanel",
            "query": "Chanel Bleu de Chanel", "title": CAP_FLAGSHIP_PAST_TITLE,
            "axes": sorted({"capped_semantics", "redos_cap",
                            "flagship_concentration_add"}),
            "note": ("flagship 'Parfum' entirely past byte 512 — invisible to "
                     "the capped parse (ACCEPTED ruling: supersedes legacy "
                     "uncapped _category_type_added at the chokepoints)"),
        },
        {
            "category": "supplements", "brand": "Optimum Nutrition",
            "query": "Optimum Nutrition Gold Standard Whey",
            "title": CAP_SUPPLEMENT_PAST_TITLE,
            "axes": sorted({"capped_semantics", "redos_cap",
                            "supplement_type_add"}),
            "note": ("supplement TYPE token 'Isolate' entirely past byte 512 — "
                     "invisible to the capped parse (ACCEPTED ruling)"),
        },
        {
            "category": "fragrances", "brand": "Dior",
            "query": "Dior Sauvage Eau de Parfum", "title": CAP_EDT_PAST_TITLE,
            "axes": sorted({"capped_semantics", "redos_cap", "concentration",
                            "candidate_missing_query_axis"}),
            "note": ("trailing 'Eau de Toilette' entirely past byte 512 — the "
                     "candidate's concentration is invisible to the capped "
                     "parse (query-stated axis rules decide)"),
        },
    ]
    return rows


REQUIRED_AXES = [
    # PHASE-A-CLOSURE (B1.0) capped-parse semantics rows
    "capped_semantics",
    # numeric/contradiction axes (F1)
    "concentration", "size_ml", "size_oz", "storage", "storage_max_not_ram", "ram",
    "count", "strength", "bare_dose", "weight_volume", "cross_base_g_ml", "percent",
    "spf_both_stated", "spf_one_sided", "plus_variant", "electronics_qualifiers",
    "shoe_size", "pack", "inch", "chip_tier", "core_count", "condition",
    "vitamin_letter", "clothing_size",
    # categorical/asymmetric axes (F2)
    "gender_contradiction", "feminine_query_unconfirmed", "gender_flanker",
    "form_fragrance_one_sided", "form_makeup", "form_both_stated",
    "flavour_grocery_add", "flavour_supplement", "finish_makeup", "material_fashion",
    "fit_fashion", "grocery_prep", "supplement_type_add", "supplement_salt_form",
    "supplement_form_added", "flagship_concentration_add", "multi_constituent",
    "candidate_missing_query_axis",
    # tolerance families (F2)
    "year_annotation", "electronics_ai_tolerance", "fashion_construction_bigram",
    "eyewear_model_code", "eyewear_colorway", "eyewear_lens_mm", "makeup_shade_number",
    # identity folds (F2)
    "apostrophe_fold", "zero_prefix_code", "polo_compound", "se_specialedition_unify",
    "british_spelling_fold", "sugar_free_glue", "ordinal_fold", "plus_symbol_fold",
    "tm_strip", "nfkd_diacritics", "html_entity_amp", "u2011_hyphen",
    "wh1000xm5_spellings", "omega_hyphen_space", "zma_acronym",
    # degenerate / cap inputs
    "redos_cap", "empty_title", "empty_query",
    # residual/structural classes
    "conc_flanker_same_token", "related_model", "bare_generation_int", "variant_add",
    "generic_class_swap", "brand_class_query_skip", "color_fashion",
    "overrej_descriptive", "wrong_brand_fence",
]
MIN_ROWS_PER_AXIS = 4


def build_cases():
    """Full enumeration + BOTH-directions swap pass + ids. Deterministic order."""
    _CASES.clear()
    _census_cases()
    _electronics_cases()
    _fragrances_cases()
    _fashion_cases()
    _supplements_cases()
    _grocery_cases()
    _makeup_cases()
    _skincare_cases()
    _haircare_cases()
    _other_cases()
    _tolerance_param_probes()

    # dedupe (merge axes) on the identity key
    merged = {}
    order = []
    for case in _CASES:
        key = (case["query"], case["title"], case["category"], case["brand"])
        if key in merged:
            merged[key]["axes"] = sorted(set(merged[key]["axes"]) | set(case["axes"]))
        else:
            merged[key] = case
            order.append(key)
    cases = [merged[k] for k in order]

    # PADDED-TITLE pass: re-pin every case with realistic retailer padding appended
    # to the candidate title — exercises the per-category PADDING subtraction and the
    # variant-add superset on descriptive titles (and, after the swap pass below, the
    # leak-direction subset with padding on the query side).
    _PAD_SUFFIX = {
        "electronics": "International Version with Warranty",
        "fragrances": "Natural Spray Authentic",
        "fashion": "New Season Authentic",
        "supplements": "Dietary Supplement Authentic",
        "grocery": "Imported Authentic",
        "makeup": "Authentic New",
        "skincare": "Authentic New",
        "haircare": "Authentic New",
        "other": "Authentic New",
    }
    padded = []
    for case in cases:
        if not case["title"] or len(case["title"]) > 400:
            continue
        suffix = _PAD_SUFFIX.get(case["category"], "Authentic New")
        padded.append({
            "category": case["category"],
            "brand": case["brand"],
            "query": case["query"],
            "title": case["title"] + " " + suffix,
            "axes": sorted(set(case["axes"]) | {"padded_title"}),
            "note": ("padded: " + case["note"]) if case["note"] else "padded",
        })
    cases = cases + padded

    # BOTH-directions swap pass: every asymmetric predicate (leak-direction subset,
    # variant-add superset, one-sided adds, feminine-query, condition either-direction)
    # gets its reverse-direction verdict pinned too.
    swapped = []
    seen = set((c["query"], c["title"], c["category"], c["brand"]) for c in cases)
    for case in cases:
        q, t = case["title"], case["query"]
        key = (q, t, case["category"], case["brand"])
        if q == t or key in seen:
            continue
        seen.add(key)
        swapped.append({
            "category": case["category"],
            "brand": case["brand"],
            "query": q,
            "title": t,
            "axes": case["axes"],
            "note": ("swap of: " + case["note"]) if case["note"] else "swap",
        })
    cases = cases + swapped

    # PHASE-A-CLOSURE (B1.0): >512-char capped-semantics rows appended LAST so
    # pre-existing case ids (positional) are untouched by the extension.
    cases = cases + _capped_semantics_rows()

    for i, case in enumerate(cases):
        case["id"] = "vd-{:04d}".format(i)
    return cases


def coverage_tally(cases):
    tally = {}
    for case in cases:
        for ax in case["axes"]:
            tally[ax] = tally.get(ax, 0) + 1
    return tally


# ---------------------------------------------------------------------------
# Verdict recording
# ---------------------------------------------------------------------------

def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # pinned behavior: an exception IS a verdict
        return {"error": type(exc).__name__}


def compute_verdicts(case):
    """Record the CURRENT verdict of every decision function for one case.
    Requires ENABLE_EXACT_PRICE_GATE=true in the environment (the functions
    read the flag per call)."""
    from app.services import price_service as ps

    q = case["query"]
    t = case["title"]
    cat = case["category"]
    brand = case["brand"]

    verdicts = {
        "axis_mismatch_strict": _safe(ps._axis_mismatch, q, t, cat, ""),
        "axis_mismatch_strict_brand": _safe(ps._axis_mismatch, q, t, cat, brand),
        "axis_mismatch_loose": _safe(ps._axis_mismatch, q, t, cat, "", strict_extras=False),
        "exact_match": _safe(ps.is_exact_match, q, t, cat),
        "exact_match_brand": _safe(ps.is_exact_match, q, t, cat, candidate_brand=brand),
        "backstop_ok": _safe(ps._backstop_identity_ok, q, t, cat),
        "category_type_added": _safe(ps._category_type_added, q, t, cat),
    }
    selection = {}
    for bkey, bval in (("none", ""), ("brand", brand), ("wrong", WRONG_BRAND)):
        for ckey, cval in (("real", cat), ("other", "other"), ("none", None)):
            selection["brand={}|cat={}".format(bkey, ckey)] = _safe(
                ps._selection_match, q, t, cval, candidate_brand=bval,
            )
    verdicts["selection_match"] = selection
    return verdicts


def main():
    os.environ["ENABLE_EXACT_PRICE_GATE"] = "true"

    cases = build_cases()
    tally = coverage_tally(cases)

    missing = {ax: tally.get(ax, 0) for ax in REQUIRED_AXES
               if tally.get(ax, 0) < MIN_ROWS_PER_AXIS}
    if missing:
        print("COVERAGE FAILURE - axes below {} rows:".format(MIN_ROWS_PER_AXIS))
        for ax, n in sorted(missing.items()):
            print("  {}: {}".format(ax, n))
        raise SystemExit(1)

    for case in cases:
        case["verdicts"] = compute_verdicts(case)

    corpus = {
        "_meta": {
            "generated_by": "scripts/dump_descriptor_golden_corpus.py",
            "purpose": ("Golden equivalence corpus for the Wave-2 VariantDescriptor "
                        "Phase-A refactor - pinned CURRENT verdicts of _axis_mismatch/"
                        "_selection_match/is_exact_match/_backstop_identity_ok/"
                        "_category_type_added"),
            "env": {"ENABLE_EXACT_PRICE_GATE": "true"},
            "wrong_brand": WRONG_BRAND,
            "n_cases": len(cases),
            "axis_tally": tally,
        },
        "cases": cases,
    }
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(str(CORPUS_PATH), "w", encoding="utf-8") as fh:
        json.dump(corpus, fh, ensure_ascii=True, sort_keys=True, indent=1)
        fh.write("\n")

    with open(str(COVERAGE_PATH), "w", encoding="utf-8") as fh:
        fh.write("Per-axis coverage tally ({} cases total)\n".format(len(cases)))
        fh.write("Required axes: {} (min {} rows each)\n\n".format(
            len(REQUIRED_AXES), MIN_ROWS_PER_AXIS))
        for ax in sorted(tally):
            marker = "" if ax in REQUIRED_AXES else "  (extra)"
            fh.write("{:40s} {:4d}{}\n".format(ax, tally[ax], marker))

    print("wrote {} cases -> {}".format(len(cases), CORPUS_PATH))
    print("coverage tally -> {}".format(COVERAGE_PATH))
    print("required axes covered: {}/{} (min {} rows each)".format(
        len(REQUIRED_AXES) - len(missing), len(REQUIRED_AXES), MIN_ROWS_PER_AXIS))


if __name__ == "__main__":
    main()

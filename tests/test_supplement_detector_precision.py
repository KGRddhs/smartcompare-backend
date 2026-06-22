"""WS-1 F1 — supplement detector precision (G2).

is_supplement_query moves from naive substring matching to whole-token
(lookaround word boundary) matching with corroboration for AMBIGUOUS tokens:

  - SUPPLEMENT_UNAMBIGUOUS (vitamin, softgel, ...) + supp/sports BRANDS stand
    alone.
  - SUPPLEMENT_AMBIGUOUS (iron, collagen, protein, zinc, calcium, omega, d3,
    magnesium, ...) count ONLY with a co-occurring dose (SUPPLEMENT_DOSE_RE) OR
    form token (softgel/capsule/...) OR a supp-brand.

Word boundary via lookaround (?<![a-z0-9])...(?![a-z0-9]) NOT \\b, so d3/d-3/
omega-3 match cleanly while "iron" does NOT match "environment".

This is double-used: extraction_service.classify_category_from_text routes a
True to "supplements", and structured_comparison_service routes the supplement
price branch off it — so a misroute is invisible to smoke20 (F1 HARD CONTRACT).
"""
import pytest

from app.services.price_service import (
    is_supplement_query,
    is_high_value_query,
)


# --- UNAMBIGUOUS tokens stand alone ---

@pytest.mark.parametrize("query", [
    "Vitamin D3 5000 IU",
    "Centrum Multivitamin",
    "NOW Vitamin D-3 5000 IU",
    "Solgar Vitamin C",
    "Garden of Life Probiotic",
])
def test_supplement_unambiguous_tokens(query):
    assert is_supplement_query(query) is True


# --- AMBIGUOUS tokens need corroboration ---

@pytest.mark.parametrize("query", [
    "Tefal steam iron",
    "collagen serum",
    "protein shaker",
    "protein bar",
    "cast iron skillet",
    "calcium antacid",
    "food container",
    "environmental sensor",
])
def test_ambiguous_tokens_without_corroboration_are_not_supplements(query):
    assert is_supplement_query(query) is False


@pytest.mark.parametrize("query", [
    "Solgar Magnesium Citrate 200mg",        # brand + dose
    "NOW Foods Omega-3 1000mg softgels",     # brand + dose + form
    "Magnesium Citrate 200mg",               # ambiguous token + dose
    "Collagen Peptides 10g powder",          # ambiguous token + dose
    "Zinc 50mg tablets",                     # ambiguous token + dose + form
])
def test_ambiguous_tokens_with_corroboration_are_supplements(query):
    assert is_supplement_query(query) is True


# --- Brand corroboration closes ambiguous queries ---

@pytest.mark.parametrize("query", [
    "Optimum Nutrition Whey Protein",        # brand closes "protein"
    "Nordic Naturals Omega-3",               # brand closes "omega-3" (test_error_paths:104)
    "Garden of Life Protein",                # brand closes "protein"
    "Dymatize ISO100 Protein",               # brand closes "protein"
    "MuscleTech Creatine",                   # creatine is unambiguous, brand present
])
def test_supplement_brand_corroboration(query):
    assert is_supplement_query(query) is True


# --- Word boundary: no substring false positives ---

@pytest.mark.parametrize("query", [
    "environmental sensor",   # 'iron' must NOT match inside 'environment'
    "food container",         # no supplement token
    "ironing board",          # 'iron' substring but no corroboration
])
def test_word_boundary_no_substring(query):
    assert is_supplement_query(query) is False


# --- d3/d-3/omega-3 lookaround matching ---

@pytest.mark.parametrize("query", [
    "Vitamin D3 5000 IU",
    "Vitamin D-3 5000 IU",
])
def test_d3_variants_match(query):
    assert is_supplement_query(query) is True


# --- Short-circuit decoupling/repoint: HV electronics are NOT supplements ---

@pytest.mark.parametrize("query", [
    "iPhone 15",
    "Apple iPhone 16 Pro",
    "Samsung Galaxy S24",
    "Samsung Galaxy Tablet S9",
    "MacBook Air M3",
])
def test_high_value_electronics_not_supplements(query):
    assert is_supplement_query(query) is False
    # And these ARE high-value (proves the predicate the supplement guard
    # decouples from / repoints to).
    assert is_high_value_query(query) is True


def test_real_supplement_still_routes_with_no_electronics_token():
    """The short-circuit decoupling pin: a genuine supplement is unaffected."""
    assert is_supplement_query("NOW Foods Omega-3 1000mg softgels") is True

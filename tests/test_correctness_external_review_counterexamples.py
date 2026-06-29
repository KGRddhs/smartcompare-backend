# -*- coding: utf-8 -*-
"""External-review (2026-06-28) counterexamples — the runtime leaks the first FIX
pass + the 2 in-session adversarial workflows MISSED (they only probed the prompted
fragrance/accessory/gender cases). Every test here was REPRODUCED gate-ON by the
dispatcher before being written, and asserts the CORRECT fail-closed behaviour.

RED on the current branch; the structural revision turns them green. The lesson: an
adversarial sweep is only as good as its COVERAGE — these enumerate category × axis
cases (electronics model-tokens, fashion colorway/size, the cache-guard semantics, the
KPI aggregate path, AggregateOffer-lowPrice-only) the prompted workflows never swept.
"""
import json

import pytest

import app.services.price_service as ps


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _m(q, t, cat, brand=""):
    return ps._selection_match(q, t, cat, candidate_brand=brand)


# ===========================================================================
# P1 — the matcher still accepts wrong products (subset + short-token loss +
# missing axes). All must REJECT (False).
# ===========================================================================

def test_electronics_short_model_token_m2_vs_m3_rejected():
    assert _m("MacBook Air M2 256GB", "Apple MacBook Air M3 256GB", "electronics", "Apple") is False


def test_electronics_short_model_token_canon_r6_vs_r5_rejected():
    assert _m("Canon EOS R6", "Canon EOS R5", "electronics", "Canon") is False


def test_electronics_short_model_token_kept_same_accepted():
    # The fix must PRESERVE the short model token, not drop it — same model still matches.
    assert _m("MacBook Air M2 256GB", "Apple MacBook Air M2 256GB", "electronics", "Apple") is True
    assert _m("Canon EOS R6", "Canon EOS R6 Body", "electronics", "Canon") is True


def test_supplement_vitamin_c_vs_d_rejected():
    assert _m("Vitamin C 1000mg", "Vitamin D 1000mg", "supplements", "NOW") is False


def test_supplement_d3_vs_d3_plus_zinc_rejected():
    assert _m("Now Vitamin D3 5000 IU", "Now Vitamin D3 with Zinc 5000 IU", "supplements", "Now") is False


def test_electronics_storage_omitted_by_candidate_pends():
    # Query states 256GB; candidate omits storage -> UNVERIFIED -> reject (fail-closed).
    assert _m("Samsung Galaxy S24 256GB", "Samsung Galaxy S24", "electronics", "Samsung") is False
    # but a candidate that STATES the 256 still matches (no over-rejection).
    assert _m("Samsung Galaxy S24 256GB",
              "Samsung Galaxy S24 256GB Dual SIM Phantom Black", "electronics", "Samsung") is True


def test_skincare_size_omitted_by_candidate_pends():
    assert _m("CeraVe Moisturizing Lotion 473ml", "CeraVe Moisturizing Lotion", "skincare", "CeraVe") is False
    assert _m("CeraVe Moisturizing Lotion 473ml",
              "CeraVe Moisturizing Lotion 473ml Pump", "skincare", "CeraVe") is True


def test_fashion_colorway_white_vs_black_rejected():
    assert _m("Nike Air Force 1 White", "Nike Air Force 1 Black", "fashion", "Nike") is False
    # same colorway still matches.
    assert _m("Nike Air Force 1 White", "Nike Air Force 1 '07 White", "fashion", "Nike") is True


def test_fashion_clothing_size_m_vs_l_rejected():
    assert _m("Nike Tech Fleece Hoodie Size M", "Nike Tech Fleece Hoodie Size L", "fashion", "Nike") is False


# ===========================================================================
# P1 — should_cache_price is not fail-closed (missing identity / URL / OOS).
# ===========================================================================

def test_should_cache_rejects_missing_identity():
    assert ps.should_cache_price("Samsung Galaxy S24 256GB",
                                 {"amount": 240, "source_method": "local_bhd"}, "electronics") is False


def test_should_cache_rejects_missing_url():
    assert ps.should_cache_price("Samsung Galaxy S24 256GB",
                                 {"amount": 240, "source_method": "local_bhd",
                                  "title": "Samsung Galaxy S24 256GB"}, "electronics") is False


def test_should_cache_rejects_out_of_stock():
    assert ps.should_cache_price("Samsung Galaxy S24 256GB",
                                 {"amount": 240, "source_method": "local_bhd",
                                  "title": "Samsung Galaxy S24 256GB",
                                  "url": "https://x.com/p/s24", "in_stock": False},
                                 "electronics") is False


def test_should_cache_accepts_exact_instock_valid_pdp():
    assert ps.should_cache_price("Samsung Galaxy S24 256GB",
                                 {"amount": 240, "source_method": "local_bhd",
                                  "title": "Samsung Galaxy S24 256GB",
                                  "url": "https://www.sharafdg.com/product/galaxy-s24-256gb/",
                                  "in_stock": True}, "electronics") is True


# ===========================================================================
# P1 — KPI aggregate path is still circular (no truth entry).
# ===========================================================================

def test_kpi_aggregate_uses_truth_and_rejects_wrong_identity():
    import importlib
    er = importlib.import_module("scripts.eval_runner")
    truth = [{"id": "k1", "query": "YSL Black Opium EDP 90ml", "category": "fragrances",
              "expected": {"brand": "Yves Saint Laurent"}},
             {"id": "k2", "query": "YSL Black Opium EDP 90ml", "category": "fragrances",
              "expected": {"brand": "Yves Saint Laurent"}}]
    libre = {"amount": 30, "source_method": "local_bhd", "in_stock": True,
             "title": "YSL Libre Eau de Parfum 90ml", "url": "https://x.com/p/libre"}
    body = {"overview": {"products": [{"price": libre}, {"price": libre}]}}
    # With the per-product truth, a Libre price must NOT count as exact for Black Opium.
    usable, requested = er.count_usable_exact_genuine(body, truth)
    assert (usable, requested) == (0, 2)


# ===========================================================================
# P1 — AggregateOffer lowPrice-only + missing availability.
# ===========================================================================

def _jsonld(payload):
    return f'<html><script type="application/ld+json">{json.dumps(payload)}</script></html>'


def test_aggregateoffer_lowprice_only_pends():
    html = _jsonld({"@type": "Product", "name": "Dior Sauvage Eau de Toilette 100ml",
                    "brand": "Dior",
                    "offers": {"@type": "AggregateOffer", "lowPrice": "22.000",
                               "priceCurrency": "BHD"}})
    assert ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml") is None


def test_missing_availability_is_unknown_not_instock():
    html = _jsonld({"@type": "Product", "name": "Dior Sauvage Eau de Toilette 100ml",
                    "brand": "Dior",
                    "offers": {"@type": "Offer", "price": "45.000", "priceCurrency": "BHD"}})
    res = ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml")
    assert res is not None
    # unknown availability must NOT be asserted as in_stock=True.
    assert res.get("in_stock") is not True


# ===========================================================================
# P2 — brand alias rejected by the literal brand-substring filter before the
# alias-aware matcher (YSL vs "Yves Saint Laurent").
# ===========================================================================

def test_jsonld_brand_alias_matches_before_literal_filter():
    html = _jsonld({"@type": "Product", "name": "Black Opium Eau de Parfum 90ml",
                    "brand": {"@type": "Brand", "name": "Yves Saint Laurent"},
                    "offers": {"@type": "Offer", "price": "55.000", "priceCurrency": "BHD",
                               "availability": "https://schema.org/InStock"}})
    res = ps.extract_jsonld_price(html, "YSL", "BHD", "YSL Black Opium EDP 90ml")
    assert res is not None and res["amount"] == pytest.approx(55.0)

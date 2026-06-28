# -*- coding: utf-8 -*-
"""Gate #4 (rollback truthful, B8) — with ENABLE_EXACT_PRICE_GATE=false the genuine-
price CORRECTNESS layer is BYTE-IDENTICAL to b207bfa: every new gate/selector/axis is a
no-op, the cache key namespace is unchanged, and the JSON-LD availability/AggregateOffer
semantics revert to the b207bfa literal. This is the escape hatch the rollback claim
promises — proven, not asserted.

Each test sets the flag OFF via monkeypatch (os.getenv read at call time)."""
import json

import pytest

import app.services.price_service as ps


@pytest.fixture(autouse=True)
def _gate_off(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


# --- the matcher / selector are no-ops -------------------------------------

def test_is_exact_match_is_noop_true():
    # Every wrong-SKU pair that the gate-ON contract REJECTS returns True flag-OFF.
    assert ps.is_exact_match("Samsung Galaxy S24 256GB", "Samsung Galaxy S24 FE 128GB",
                             "electronics") is True
    assert ps.is_exact_match("Bleu de Chanel EDP 100ml", "Bleu de Chanel EDT 30ml",
                             "fragrances") is True


def test_selection_match_is_noop_true():
    assert ps._selection_match("Versace Eros EDT", "Versace Eros Pour Femme EDT",
                               "fragrances", candidate_brand="Versace") is True
    assert ps._selection_match("YSL Black Opium", "YSL Black Opium Le Parfum 90ml",
                               "fragrances", candidate_brand="YSL") is True


def test_select_best_is_legacy_cheapest():
    cands = [
        {"amount": 300.0, "title": "Samsung Galaxy S24 256GB", "in_stock": True,
         "url": "https://x.com/p/s24", "source_method": "local_bhd"},
        {"amount": 240.0, "title": "Samsung Galaxy S24 FE 256GB", "in_stock": True,
         "url": "https://x.com/p/fe", "source_method": "local_bhd"},
    ]
    best = ps.select_best(cands, "Samsung Galaxy S24 256GB", "electronics")
    assert best is not None and best["amount"] == 240.0


def test_select_best_no_title_no_url_not_dropped_flag_off():
    # Flag-OFF: the B5 title/url fail-closed is OFF — the legacy cheapest pick stands.
    cands = [{"amount": 400.0, "in_stock": True, "source_method": "local_bhd"}]
    best = ps.select_best(cands, "Samsung Galaxy S24 256GB", "electronics")
    assert best is not None and best["amount"] == 400.0


# --- is_price_showable correctness backstop is OFF -------------------------

def test_is_price_showable_no_correctness_pend_flag_off():
    # An accessory / wrong-variant / listing-url price is showable flag-OFF (no
    # correctness backstop) — only the legacy guards (source_method/implausible) apply.
    acc = {"amount": 250.0, "currency": "BHD", "source_method": "local_bhd",
           "in_stock": True, "title": "Samsung Galaxy S24 Case",
           "url": "https://www.noon.com/search?q=s24"}
    assert ps.is_price_showable("Samsung Galaxy S24", acc, "electronics",
                                enforce_correctness=True) is True
    assert "guard_rejected" not in acc


def test_oos_still_showable_flag_off():
    # Flag-OFF the in_stock=False correctness pend is OFF too (b207bfa parity).
    oos = {"amount": 80.0, "currency": "BHD", "source_method": "local_bhd",
           "in_stock": False, "title": "Creed Aventus 100ml", "url": "https://x.com/p/a"}
    assert ps.is_price_showable("Creed Aventus", oos, "fragrances",
                                enforce_correctness=True) is True


# --- cache key namespace is the legacy size-token key ----------------------

def test_cache_key_is_legacy_namespace_flag_off():
    # Flag-OFF: no concentration/qualifier axis — EDP and EDT collapse to one key
    # (the b207bfa size-only namespace), so a rollback does not orphan the warm cache.
    k_edp = ps.build_size_aware_price_cache_key("Chanel", "Bleu de Chanel", None, "bahrain",
                                                "Bleu de Chanel EDP 100ml")
    k_edt = ps.build_size_aware_price_cache_key("Chanel", "Bleu de Chanel", None, "bahrain",
                                                "Bleu de Chanel EDT 100ml")
    assert k_edp == k_edt  # legacy: only the 100ml size token discriminates


def test_should_cache_price_is_noop_true_flag_off():
    wrong = {"amount": 240.0, "source_method": "local_bhd", "in_stock": True,
             "title": "Samsung Galaxy S24 FE 256GB", "url": "https://x.com/p/fe"}
    assert ps.should_cache_price("Samsung Galaxy S24 256GB", wrong, "electronics") is True


# --- JSON-LD: no stale/AggregateOffer-range drop; literal availability ------

def _jsonld(payload):
    return f'<html><script type="application/ld+json">{json.dumps(payload)}</script></html>'


def test_jsonld_aggregateoffer_range_kept_flag_off():
    # Flag-OFF: the AggregateOffer RANGE drop (B4) is OFF — lowPrice is taken (I5.8).
    html = _jsonld({"@type": "Product", "name": "Dior Sauvage Eau de Toilette 100ml",
                    "brand": "Dior",
                    "offers": {"@type": "AggregateOffer", "lowPrice": "22.000",
                               "highPrice": "60.000", "priceCurrency": "BHD"}})
    res = ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml")
    assert res is not None and res["amount"] == pytest.approx(22.0)


def test_jsonld_expired_offer_kept_flag_off():
    # Flag-OFF: priceValidUntil staleness drop is OFF.
    html = _jsonld({"@type": "Product", "name": "Dior Sauvage Eau de Toilette 100ml",
                    "brand": "Dior",
                    "offers": {"@type": "Offer", "price": "45.000", "priceCurrency": "BHD",
                               "priceValidUntil": "2020-01-01"}})
    res = ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml")
    assert res is not None and res["amount"] == pytest.approx(45.0)


def test_jsonld_availability_literal_flag_off():
    # Flag-OFF: SoldOut/Discontinued/PreOrder do NOT flip in_stock to False (only the
    # literal OutOfStock token does — b207bfa parity).
    for avail in ("https://schema.org/SoldOut", "https://schema.org/Discontinued",
                  "https://schema.org/PreOrder"):
        html = _jsonld({"@type": "Product", "name": "Acme Widget", "brand": "Acme",
                        "offers": {"@type": "Offer", "price": "9.90",
                                   "priceCurrency": "BHD", "availability": avail}})
        res = ps.extract_jsonld_price(html, "Acme", "BHD")
        assert res is not None and res["in_stock"] is True, (
            f"flag-OFF: {avail} must stay in_stock=True (b207bfa literal)"
        )
    # OutOfStock still flips (unchanged in b207bfa).
    html = _jsonld({"@type": "Product", "name": "Acme Widget", "brand": "Acme",
                    "offers": {"@type": "Offer", "price": "9.90", "priceCurrency": "BHD",
                               "availability": "https://schema.org/OutOfStock"}})
    res = ps.extract_jsonld_price(html, "Acme", "BHD")
    assert res is not None and res["in_stock"] is False


# --- unbxd restores the wasPrice fallback ----------------------------------

def test_unbxd_waspce_fallback_restored_flag_off():
    from app.services.unbxd_service import _parse_unbxd_amount
    assert _parse_unbxd_amount({"wasPrice": 50.0}) == 50.0

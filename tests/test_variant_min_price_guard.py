"""Variable-product MIN-variation DECANT LEAK guard (scraping audit 2026-07-08).

woo/shopify variable products were served their CHEAPEST variation (a 30ml decant) as
if it were the queried full bottle:
  - woo `_amount_from_prices` falls back to price_range.min_amount for a variable product.
  - shopify `_match_shopify_product` priced variants[0] (the store default/first, usually
    the smallest).
Fixed under ENABLE_VARIANT_MIN_PRICE_GUARD (default OFF; hard-requires ENABLE_EXACT_PRICE_GATE):
  - woo: a min != max price_range spread with no per-variation sizes to bind -> PEND (skip).
  - shopify: bind the queried size to a specific variant; size-unspecified fragrance ->
    flagship/largest bottle (never the decant); non-fragrance unbindable spread -> PEND.
Flag OFF -> exact current path (byte-identical). (magento deferred — its min-only GraphQL
needs a query-byte change; tracked separately.)
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services import price_service as ps
from app.services import woocommerce_service as woo
from app.services.price_service import _match_shopify_product


@pytest.fixture
def guard_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.setenv("ENABLE_VARIANT_MIN_PRICE_GUARD", "1")
    ps._extract_variant_descriptor_cached.cache_clear()
    yield
    ps._extract_variant_descriptor_cached.cache_clear()


@pytest.fixture
def guard_off(monkeypatch):
    # exact gate stays ON (so matching behaves identically) — only the variant guard is OFF.
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.delenv("ENABLE_VARIANT_MIN_PRICE_GUARD", raising=False)
    ps._extract_variant_descriptor_cached.cache_clear()
    yield
    ps._extract_variant_descriptor_cached.cache_clear()


# --------------------------------------------------------------------------
# WooCommerce — price_range spread pend
# --------------------------------------------------------------------------
def _woo_prod(name, price=None, price_range=None, currency="BHD", minor=3):
    prices = {"currency_code": currency, "currency_minor_unit": minor}
    if price is not None:
        prices["price"] = price
    if price_range is not None:
        prices["price_range"] = price_range
    return {"name": name, "prices": prices,
            "permalink": "https://alibaksh.com/product/lattafa-khamrah", "is_in_stock": True}


class TestWooSpread:
    def test_variable_spread_pends_guard_on(self, guard_on):
        # price null, range 12..45 BHD -> decant spread -> PEND (no candidate).
        prods = [_woo_prod("Lattafa Khamrah Eau de Parfum",
                           price_range={"min_amount": "12000", "max_amount": "45000"})]
        assert woo._match_woo_product(prods, "Lattafa Khamrah", "BHD", "fragrances") is None

    def test_variable_spread_returns_min_guard_off(self, guard_off):
        prods = [_woo_prod("Lattafa Khamrah Eau de Parfum",
                           price_range={"min_amount": "12000", "max_amount": "45000"})]
        out = woo._match_woo_product(prods, "Lattafa Khamrah", "BHD", "fragrances")
        assert out is not None and out["amount"] == 12.0   # byte-identical: min served

    def test_variable_min_equals_max_not_pended(self, guard_on):
        # apparel S/M/L all one price -> no spread -> still served.
        prods = [_woo_prod("Lattafa Khamrah Eau de Parfum",
                           price_range={"min_amount": "18000", "max_amount": "18000"})]
        out = woo._match_woo_product(prods, "Lattafa Khamrah", "BHD", "fragrances")
        assert out is not None and out["amount"] == 18.0

    def test_simple_product_unchanged(self, guard_on):
        prods = [_woo_prod("Lattafa Khamrah Eau de Parfum", price="20000")]
        out = woo._match_woo_product(prods, "Lattafa Khamrah", "BHD", "fragrances")
        assert out is not None and out["amount"] == 20.0

    def test_spread_helper_unit(self):
        assert woo._woo_variable_spread({"price_range": {"min_amount": "12000", "max_amount": "45000"}}) is True
        assert woo._woo_variable_spread({"price_range": {"min_amount": "12000", "max_amount": "12000"}}) is False
        assert woo._woo_variable_spread({"price": "20000"}) is False
        assert woo._woo_variable_spread({}) is False


# --------------------------------------------------------------------------
# Shopify — positive size binding
# --------------------------------------------------------------------------
def _shopify_catalog(variants, title="Dior Sauvage Eau de Parfum", vendor="Dior"):
    return {"_store_currency": "BHD", "products": [
        {"title": title, "vendor": vendor, "handle": "sauvage", "variants": variants}]}


def _v(size, price, available=True):
    return {"title": size, "price": price, "available": available}


class TestShopifyBinding:
    def test_stated_size_binds_matching_variant(self, guard_on):
        # Title carries 100ml (so a 100ml query matches upstream) but variants[0] is a 30ml
        # decant — the leak. Guard binds the 100ml variant.
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("100ml", "55.00")],
                               title="Dior Sauvage Eau de Parfum 100ml")
        out = _match_shopify_product(cat, "Dior Sauvage EDP 100ml", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 55.0 and out["size"] == "100ml"

    def test_stated_size_variants0_decant_guard_off(self, guard_off):
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("100ml", "55.00")],
                               title="Dior Sauvage Eau de Parfum 100ml")
        out = _match_shopify_product(cat, "Dior Sauvage EDP 100ml", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 25.0   # byte-identical: variants[0]=30ml decant leak

    def test_size_unspecified_fragrance_prefers_flagship(self, guard_on):
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("100ml", "55.00")])
        out = _match_shopify_product(cat, "Dior Sauvage", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 55.0   # 100ml flagship, never the 30ml decant

    def test_size_unspecified_variants0_decant_guard_off(self, guard_off):
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("100ml", "55.00")])
        out = _match_shopify_product(cat, "Dior Sauvage", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 25.0   # byte-identical: variants[0]=30ml decant leak

    def test_size_unspecified_no_flagship_prefers_largest(self, guard_on):
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("50ml", "40.00")])
        out = _match_shopify_product(cat, "Dior Sauvage", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 40.0   # largest (50ml), never the 30ml decant

    def test_stated_size_not_offered_pends(self, guard_on):
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("50ml", "40.00")])
        out = _match_shopify_product(cat, "Dior Sauvage EDP 200ml", "BHD", "d.bh", "fragrances")
        assert out is None   # 200ml not offered -> pend, never serve a different size

    def test_all_same_price_unambiguous(self, guard_on):
        cat = _shopify_catalog([_v("30ml", "25.00"), _v("100ml", "25.00")])
        out = _match_shopify_product(cat, "Dior Sauvage", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 25.0

    def test_single_variant_unchanged(self, guard_on):
        cat = _shopify_catalog([_v("100ml", "55.00")])
        out = _match_shopify_product(cat, "Dior Sauvage", "BHD", "d.bh", "fragrances")
        assert out is not None and out["amount"] == 55.0

    def test_selector_unit_stated_size(self):
        variants = [_v("30ml", "25.00"), _v("100ml", "55.00")]
        chosen = ps._select_shopify_variant(variants, "Dior Sauvage 100ml",
                                             "Dior Sauvage", "fragrances", True)
        assert chosen is not None and chosen["title"] == "100ml"

    def test_selector_unit_non_fragrance_spread_pends(self):
        # supplements 60/120 count at different prices, size-unspecified -> ambiguous -> pend
        variants = [_v("60 caps", "10.00"), _v("120 caps", "18.00")]
        chosen = ps._select_shopify_variant(variants, "NOW Vitamin C",
                                             "NOW Vitamin C", "supplements", False)
        assert chosen is None

"""Microdata price extractor — currency-default + upsell-node-hijack fixes (audit 2026-07-08).

`_extract_microdata_price` had two correctness bugs, both fixed under exact_gate_enabled()
(ENABLE_EXACT_PRICE_GATE, default ON; flag-OFF byte-identical):
  (a) a MISSING priceCurrency defaulted to 'USD' -> a BHD page that omits its currency tag
      was converted DOWN ~2.6x; a genuinely-converted foreign price kept source_method
      'page_scrape' (polluting the genuine-BH KPI).
  (b) the price was the MAX across all in-Offer itemprop=price nodes with NO query binding,
      so a pricier related-products / upsell Product node hijacked the price.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from bs4 import BeautifulSoup

from app.services import price_service as ps
from app.services.price_service import _extract_microdata_price


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def _product(name, price, currency=None, itemtype="http://schema.org/Product"):
    cur = f'<span itemprop="priceCurrency" content="{currency}">{currency}</span>' if currency else ""
    return f'''
    <div itemscope itemtype="{itemtype}">
      <span itemprop="name">{name}</span>
      <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
        <span itemprop="price" content="{price}">{price}</span>
        {cur}
      </div>
    </div>'''


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "1")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "1")
    ps._extract_variant_descriptor_cached.cache_clear()
    yield
    ps._extract_variant_descriptor_cached.cache_clear()


@pytest.fixture
def flag_off(monkeypatch):
    # exact_gate_enabled() DEFAULTS ON, so it must be explicitly disabled (not just unset).
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "0")
    ps._extract_variant_descriptor_cached.cache_clear()
    yield
    ps._extract_variant_descriptor_cached.cache_clear()


# --------------------------------------------------------------------------
# BUG (a) — currency default + converted relabel
# --------------------------------------------------------------------------
class TestCurrencyDefault:
    def test_missing_currency_defaults_to_region_flag_on(self, flag_on):
        # BHD page, price tag with NO priceCurrency anywhere -> keep BHD, no conversion.
        html = f'''<div itemscope itemtype="http://schema.org/Product">
          <span itemprop="name">Dior Sauvage EDT 100ml</span>
          <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
            <span itemprop="price" content="244.99">244.99</span>
          </div></div>'''
        out = _extract_microdata_price(_soup(html), "BHD", "example.bh", "https://example.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out["amount"] == 244.99
        assert out["currency"] == "BHD"
        assert out["source_method"] == "page_scrape"   # not converted

    def test_genuine_usd_offer_converts_and_relabels(self, flag_on, monkeypatch):
        monkeypatch.setattr(ps, "_convert_to_bhd", lambda amt, cur: round(amt * 0.376, 2))
        html = _product("Dior Sauvage EDT 100ml", "100", currency="USD")
        out = _extract_microdata_price(_soup(html), "BHD", "example.bh", "https://example.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out["currency"] == "BHD"
        assert out["amount"] == 37.6                    # 100 USD -> BHD (stubbed rate)
        assert out["source_method"] == "converted_usd"  # provenance honest

    def test_currency_on_product_ancestor_read_flag_on(self, flag_on):
        # priceCurrency declared on the PRODUCT scope, price in the nested Offer.
        html = '''<div itemscope itemtype="http://schema.org/Product">
          <span itemprop="name">Dior Sauvage EDT</span>
          <span itemprop="priceCurrency" content="BHD">BHD</span>
          <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
            <span itemprop="price" content="244.99">244.99</span>
          </div></div>'''
        out = _extract_microdata_price(_soup(html), "BHD", "example.bh", "https://example.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out["amount"] == 244.99 and out["currency"] == "BHD"
        assert out["source_method"] == "page_scrape"


# --------------------------------------------------------------------------
# BUG (b) — upsell/related-product node hijack
# --------------------------------------------------------------------------
class TestNodeBinding:
    def test_matched_node_outranks_pricier_upsell(self, flag_on):
        # Main product 244.99 (matches query) + a pricier UPSELL 299 (different product).
        html = (_product("Dior Sauvage EDT 100ml", "244.99", currency="BHD")
                + _product("Chanel Bleu de Chanel 100ml", "299.00", currency="BHD"))
        out = _extract_microdata_price(_soup(html), "BHD", "d.bh", "https://d.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out["amount"] == 244.99   # matched node wins over the pricier upsell

    def test_single_unmatched_product_still_returns_price(self, flag_on):
        # Only one product; its name does NOT match the query -> demote-only: still return.
        html = _product("Totally Unrelated Item XZ", "55.00", currency="BHD")
        out = _extract_microdata_price(_soup(html), "BHD", "d.bh", "https://d.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out is not None and out["amount"] == 55.00

    def test_nameless_scope_falls_back_to_max(self, flag_on):
        # No itemprop=name -> matched False everywhere -> legacy max-in-offer pick.
        html = '''<div itemscope itemtype="http://schema.org/Product">
          <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
            <span itemprop="price" content="120.00">120.00</span>
            <span itemprop="priceCurrency" content="BHD">BHD</span>
          </div></div>'''
        out = _extract_microdata_price(_soup(html), "BHD", "d.bh", "https://d.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out is not None and out["amount"] == 120.00


# --------------------------------------------------------------------------
# FLAG OFF — byte-identical pre-fix behaviour
# --------------------------------------------------------------------------
class TestFlagOffByteIdentical:
    def test_missing_currency_defaults_to_usd_flag_off(self, flag_off, monkeypatch):
        # Pre-fix: no currency -> 'USD' -> converts a BHD-page price DOWN (the bug), and
        # source_method stays 'page_scrape' (no converted relabel).
        seen = {}

        def fake_convert(price, target):
            seen["called"] = True
            price["currency"] = target

        monkeypatch.setattr(ps, "_convert_gpt_price_currency", fake_convert)
        html = f'''<div itemscope itemtype="http://schema.org/Product">
          <span itemprop="name">Dior Sauvage EDT 100ml</span>
          <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
            <span itemprop="price" content="244.99">244.99</span>
          </div></div>'''
        out = _extract_microdata_price(_soup(html), "BHD", "example.bh", "https://example.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert seen.get("called") is True               # USD default -> conversion fired (the bug)
        assert out["source_method"] == "page_scrape"     # no converted_usd relabel flag-OFF

    def test_max_node_wins_flag_off(self, flag_off):
        # Pre-fix: no query binding -> the pricier upsell node wins (the bug preserved).
        html = (_product("Dior Sauvage EDT 100ml", "244.99", currency="BHD")
                + _product("Chanel Bleu de Chanel 100ml", "299.00", currency="BHD"))
        out = _extract_microdata_price(_soup(html), "BHD", "d.bh", "https://d.bh/p",
                                       product_name="Dior Sauvage", category="fragrances")
        assert out["amount"] == 299.00                  # max-across-nodes, unchanged flag-OFF

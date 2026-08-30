# -*- coding: utf-8 -*-
"""UNIT B2 — three zero-fetch extractor fixes (ENABLE_EXTRACTOR_FIXES_2608).

Each fix is pinned to its measured B4 corpus page and each ships DEFAULT OFF, so
a flag-OFF run is byte-identical to main (the page stays a no-price residual, as
it is on origin/main today).

(a) PrestaShop DOUBLED-QUOTE JSON-LD — www.parfumdo.com emits
    ``"unitPricingMeasure":""35 ml""`` (a doubled quote in the VALUE position),
    which breaks ``json.loads`` and hides the real AggregateOffer members
    67.30 / 96.30 / 132.90 / 209.10 EUR. A tolerant re-parse is tried ONLY after
    the normal parse fails, and the repair collapses only the ``:""X""`` value
    shape, so it cannot corrupt a well-formed empty-string field (``"k":""``).

(b) LOWERCASE offer keys — www.aromas.es writes ``"lowprice"`` / ``"highprice"``
    (schema.org is ``lowPrice`` / ``highPrice``), so the AggregateOffer's price
    is missed entirely. The low/high lookup is made case-insensitive; the
    recovered "from" price is 43.95 EUR.

(c) og:product:price:amount ALIAS with a currency SYMBOL — www.beirutdutyfree.com
    ships ``<meta property="og:product:price:amount" content="$168">`` plus
    ``og:product:price:currency = USD``. The alias (``og:`` prefix) is not read
    by the OG branch, and the ``$`` sits inside the number. Reading the alias and
    letting the existing canonical money parser strip the leading symbol recovers
    168 USD.

The amounts below are copied from the B4 residual-recovery measurement and the
verbatim JSON-LD / OG bytes of the cached PDPs (SOURCES.json). The fixtures are
minimal cuts of _proof/global/html/ ; every price/currency/meta fragment is
verbatim, only the <head> boilerplate is authored.
"""
import os

import pytest

from app.services import price_service as ps

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "extractor_fixes_2608")

PARFUMDO = "parfumdo_coco_mademoiselle_doubledquote_eur.html"
AROMAS = "aromas_black_opium_lowercase_aggregateoffer_eur.html"
BEIRUT = "beirutdutyfree_armani_code_ogalias_dollar_usd.html"
CONTROL = "no_structured_price_control.html"


def _read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def _flag_on(monkeypatch):
    # Flag ON; exact gate OFF to isolate the extractor from the per-page identity
    # gate (the same isolation the microdata / OG / Woo / RSC rung tests use).
    monkeypatch.setenv("ENABLE_EXTRACTOR_FIXES_2608", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


# --------------------------------------------------------------------------- #
# (a) PrestaShop doubled-quote JSON-LD                                          #
# --------------------------------------------------------------------------- #
def test_parfumdo_doubled_quote_jsonld_recovers_cheapest(_flag_on):
    # The doubled-quote block breaks json.loads on main; the repair unlocks the
    # AggregateOffer and the no-query legacy path returns the cheapest member.
    result = ps.extract_jsonld_price(_read(PARFUMDO), "Chanel", "EUR", "")
    assert result is not None, "doubled-quote repair must unlock the JSON-LD block"
    assert result["amount"] == 67.30
    assert result["currency"] == "EUR"


def test_parfumdo_repair_helper_recovers_all_four_offers():
    # The scoped repair yields VALID json with every real offer intact.
    body = (
        '{"@type":"AggregateOffer","priceCurrency":"EUR",'
        '"offers":[{"price":"67.30","unitPricingMeasure":""35 ml""},'
        '{"price":"96.30","unitPricingMeasure":""50 ml""}]}'
    )
    data = ps._repair_doubled_quote_jsonld_parse(body)
    assert data is not None
    assert [o["price"] for o in data["offers"]] == ["67.30", "96.30"]
    # measured full set on the real page:
    real_data = ps._repair_doubled_quote_jsonld_parse(
        _extract_ld_body(_read(PARFUMDO))
    )
    prices = [o["price"] for o in real_data["offers"]["offers"]]
    assert prices == ["67.30", "96.30", "132.90", "209.10"]
    assert real_data["offers"]["priceCurrency"] == "EUR"


def test_repair_helper_leaves_wellformed_json_untouched():
    # A well-formed empty-string field must survive the repair unchanged — the
    # helper only ever runs after a real parse fails, but the targeted shape is
    # itself safe: ``"k":""`` is not the ``:""X""`` value pattern.
    import json

    wellformed = '{"a":"","b":"x","c":""}'
    # helper returns None when there is nothing to repair (no doubled-quote value)
    assert ps._repair_doubled_quote_jsonld_parse(wellformed) is None
    # and json.loads of it is still the honest object
    assert json.loads(wellformed) == {"a": "", "b": "x", "c": ""}


# --------------------------------------------------------------------------- #
# (b) lowercase lowprice / highprice AggregateOffer                             #
# --------------------------------------------------------------------------- #
def test_aromas_lowercase_aggregateoffer_recovered(_flag_on):
    result = ps.extract_jsonld_price(_read(AROMAS), "Yves Saint Laurent", "EUR", "")
    assert result is not None, "case-insensitive low/high lookup must find the offer"
    assert result["amount"] == 43.95
    assert result["currency"] == "EUR"


# --------------------------------------------------------------------------- #
# (c) og:product:price:amount alias + currency symbol                          #
# --------------------------------------------------------------------------- #
def test_beirut_og_product_price_alias_dollar_stripped(_flag_on):
    result = ps.extract_price_from_html(
        _read(BEIRUT), "Armani Code Parfum", "USD",
        "www.beirutdutyfree.com",
        "https://www.beirutdutyfree.com/product/giorgio-armani-code-parfum-125ml-4108",
    )
    assert result is not None, "og:product:price:amount alias must be read"
    # the leading $ is stripped by the shared money parser, not a second parser
    assert result["amount"] == 168.0
    assert result["currency"] == "USD"
    assert result["estimated"] is False


# --------------------------------------------------------------------------- #
# flag-OFF byte-identity — each page stays a no-price residual, as on main      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fixture, brand", [(PARFUMDO, "Chanel"), (AROMAS, "Yves Saint Laurent")])
def test_flag_off_jsonld_pages_return_none(monkeypatch, fixture, brand):
    monkeypatch.setenv("ENABLE_EXTRACTOR_FIXES_2608", "false")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    assert ps.extract_jsonld_price(_read(fixture), brand, "EUR", "") is None


def test_flag_off_beirut_returns_none(monkeypatch):
    monkeypatch.setenv("ENABLE_EXTRACTOR_FIXES_2608", "false")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    assert ps.extract_price_from_html(
        _read(BEIRUT), "Armani Code Parfum", "USD",
        "www.beirutdutyfree.com", "https://www.beirutdutyfree.com/product/x",
    ) is None


def test_flag_on_no_price_control_is_noop(_flag_on):
    # Flag ON on a page none of the three fixes touch: still None (the fixes add
    # recovery, never a fabricated price).
    assert ps.extract_price_from_html(
        _read(CONTROL), "Some Fragrance", "EUR",
        "example.com", "https://example.com/p/x",
    ) is None


def _extract_ld_body(html):
    import re

    m = re.search(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I
    )
    return m.group(1) if m else ""

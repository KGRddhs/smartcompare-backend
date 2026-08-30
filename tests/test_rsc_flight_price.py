# -*- coding: utf-8 -*-
"""UNIT B1 — RSC-flight price reader (ENABLE_RSC_FLIGHT_PRICE).

sephora.com.tr is a Next.js App Router in front of SFCC. The price is not in
JSON-LD / microdata / OG — it is carried in the React Server Component flight
stream ``self.__next_f`` as an escaped ``\\"price\\":<int>,\\"currency\\":\\"TRY\\"``
adjacency. B4 measured the top-level product price 3/3 on cached bytes:
armani-si 5050 TRY, bleu-de-chanel 8400 TRY, kayali 2090 TRY.

MINOR-UNIT CONVENTION (B4 open question, PINNED here): the flight integer is in
MAJOR currency units (whole TRY), confirmed against each row's visible shelf
price (armani 5050 == '5.050,00 TL'), so it is used as-is with NO /100.

The RSC rung is a LATE fallback (after JSON-LD/microdata/OG/Woo), so — like every
other fallback rung — it sits behind ``_page_identity_ok``. The sephora.com.tr
titles ("... KSA", "... Rose") don't token-match the query under the exact gate,
so these tests isolate the extractor with ``ENABLE_EXACT_PRICE_GATE=false`` (the
documented way to isolate extraction from the identity gate), exactly as the
microdata / OG / Woo rung tests do.
"""
import os

import pytest

from app.services import price_service as ps

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "rsc_flight")


def _read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


# (fixture, query, url, expected amount) — amounts are B4's measured top-level
# flight prices; each fixture also carries later variant decoys.
CASES = [
    ("sephora_com_tr_armani_si_flight_try.html", "Armani Si",
     "https://www.sephora.com.tr/p/armani-si-edp-100-ml-P1547001.html", 5050.0),
    ("sephora_com_tr_bleu_de_chanel_flight_try.html", "Bleu de Chanel",
     "https://www.sephora.com.tr/p/bleu-de-chanel-P1922003.html", 8400.0),
    ("sephora_com_tr_kayali_vanilla28_flight_try.html", "Kayali Vanilla 28",
     "https://www.sephora.com.tr/p/kayali-vanilla28---eau-de-parfum-P3551017.html", 2090.0),
]


@pytest.fixture(autouse=True)
def _isolate_extractor(monkeypatch):
    # Flag ON for these tests; exact gate OFF to isolate the extractor from the
    # per-page identity gate (the same isolation the microdata/OG/Woo tests use).
    monkeypatch.setenv("ENABLE_RSC_FLIGHT_PRICE", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


@pytest.mark.parametrize("fixture, query, url, expected", CASES)
def test_flight_price_measured(fixture, query, url, expected):
    html = _read(fixture)
    result = ps.extract_price_from_html(
        html, query, "TRY", "sephora.com.tr", url, "fragrances")
    assert result is not None, "RSC flight rung must produce a price"
    # PIN the measured amount+currency. amount is MAJOR units (no /100): 5050,
    # never 50.50.
    assert result["amount"] == expected
    assert result["currency"] == "TRY"
    assert result["original_currency"] == "TRY"
    # Threaded through the same page_scrape machinery as every other rung.
    assert result["source_method"] == "page_scrape"
    assert result["estimated"] is False
    assert result["retailer"] == "sephora.com.tr"
    assert result["url"] == url


def test_no_flight_page_returns_none():
    html = _read("no_flight_no_structured_price.html")
    result = ps.extract_price_from_html(
        html, "Giorgio Armani Si Eau de Parfum", "TRY", "example.com",
        "https://example.com/p/x", "fragrances")
    assert result is None


@pytest.mark.parametrize("fixture, query, url, expected", CASES)
def test_flag_off_returns_none_byte_identical(monkeypatch, fixture, query, url, expected):
    # With the flag OFF the RSC rung must not run: the cascade returns None on
    # these flight-only pages exactly as main (which has no reader) does.
    monkeypatch.setenv("ENABLE_RSC_FLIGHT_PRICE", "false")
    html = _read(fixture)
    result = ps.extract_price_from_html(
        html, query, "TRY", "sephora.com.tr", url, "fragrances")
    assert result is None


def test_helper_selects_top_level_over_variant_decoys():
    # The armani fixture's flight carries variant prices 2050 / 5050 / 8650 AFTER
    # the top-level 5050; the reader must return the FIRST adjacency (the product
    # price), never a min/max over the variant decoys.
    html = _read("sephora_com_tr_armani_si_flight_try.html")
    got = ps._extract_rsc_flight_price(
        html, "TRY", "sephora.com.tr",
        "https://www.sephora.com.tr/p/armani-si-edp-100-ml-P1547001.html")
    assert got is not None
    assert got["amount"] == 5050.0
    assert got["currency"] == "TRY"


def test_helper_none_without_flight():
    html = _read("no_flight_no_structured_price.html")
    assert ps._extract_rsc_flight_price(
        html, "TRY", "example.com", "https://example.com/p/x") is None

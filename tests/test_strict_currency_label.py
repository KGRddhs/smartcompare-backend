# -*- coding: utf-8 -*-
"""BLOCKER 4 - an UNRESOLVABLE source currency must never be stamped "BHD".

THE DEFECT (pre-existing on 8adaefb, not introduced by this wave).
``_convert_to_bhd`` (price_service.py:565) logs a warning and returns the amount
UNCHANGED when the currency token is not in ``FALLBACK_RATES`` - and then
``_convert_gpt_price_currency`` (:585) unconditionally executes
``price["currency"] = target_currency``. A foreign-currency number is therefore
relabelled as a Bahraini price at an implicit 1.0 rate. The docstring of that
very guard claims it "prevents the silent-failure mode where unknown currencies
were multiplied by 1.0 and labelled BHD"; it does exactly that.

Measured live on the cached corpus (ENABLE_EXACT_PRICE_GATE=false, EXTRACTION
isolation): ``qatarperfumeshop.com`` -> ``amount 32000.0``,
``original_currency U+0631 U+002E U+0642``, ``currency "BHD"``,
``source_method page_scrape``.

THE FIX, behind ENABLE_STRICT_CURRENCY_LABEL (default ON):
  (a) an unresolvable source currency PENDS the price (the branch returns None)
      instead of relabelling it; and
  (b) the common GCC display symbols normalise to ISO first, so the large class
      of pages that carry the Arabic riyal/dirham/dinar glyphs (or "KD" / "SR")
      converts properly instead of falling into (a) at all.

NOT in scope HERE, recorded as a follow-up and FIXED IN THE NEXT WAVE (BLOCKER
6, ENABLE_MONEY_PARSER_V2): ``parse_price_string``'s comma strip read the
COMMA-DECIMAL "320,00" on this very page as "32000". That is why the corpus
amount below is 32000 and not 320 - a second, independent bug whose blast
radius reaches every caller of parse_price_string. The tests in this file that
name a magnitude now pin the money-parser flag explicitly, so the two fixes
stay independently rollback-able.
"""
import hashlib
import io
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import app.services.price_service as ps


REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "_proof" / "html"
FIXTURES = Path(__file__).parent / "fixtures" / "jsonld_first"

QPS_URL = "https://qatarperfumeshop.com/product/reef-perfume/"

QAR_SYMBOL = "ر.ق"          # rial qatari
SAR_SYMBOL = "ر.س"          # rial saudi
AED_SYMBOL = "د.إ"          # dirham
OMR_SYMBOL = "ر.ع."         # rial omani
BHD_SYMBOL = ".د.ب"         # dinar bahraini (leading-dot form)
TUGRIK = "₮"                     # a genuinely unresolvable symbol


def _corpus_page(url: str) -> str:
    name = hashlib.sha1(("curl_cffi|" + url).encode()).hexdigest() + ".html"
    path = CORPUS / name
    if not path.exists():
        pytest.skip("cached corpus page missing: " + name)
    return io.open(path, encoding="utf-8", errors="replace").read()


@pytest.fixture(autouse=True)
def _extraction_isolation(monkeypatch):
    """EXTRACTION-isolation mode.

    With ENABLE_EXACT_PRICE_GATE=true the identity gate rejects most cached
    pages and everything returns None, which MASKS extraction bugs. Every
    number in this file is therefore measured with the exact gate OFF; the
    behaviour under test is the currency LABEL, which the exact gate does not
    participate in.
    """
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


def _woo_html(symbol: str, amount_text: str) -> str:
    """A minimal WooCommerce PDP carrying one price span."""
    return (
        "<html><body><p class='price'>"
        "<span class='woocommerce-Price-amount amount'>"
        "<span class='woocommerce-Price-currencySymbol'>" + symbol + "</span>"
        + amount_text +
        "</span></p></body></html>"
    )


def _woo_price(symbol, amount_text="350.00", target="BHD"):
    soup = BeautifulSoup(_woo_html(symbol, amount_text), "html.parser")
    return ps._extract_woocommerce_price(
        soup, target, "example.com", "https://example.com/p"
    )


# ---------------------------------------------------------------------------
# 1. The flag itself
# ---------------------------------------------------------------------------

class TestFlag:
    def test_default_is_on(self, monkeypatch):
        monkeypatch.delenv("ENABLE_STRICT_CURRENCY_LABEL", raising=False)
        assert ps.strict_currency_label_enabled() is True

    @pytest.mark.parametrize("raw", ["false", "0", "no", "off", "", "FALSE", " Off "])
    def test_off_values(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", raw)
        assert ps.strict_currency_label_enabled() is False

    def test_read_per_call_never_cached_at_import(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        assert ps.strict_currency_label_enabled() is False
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        assert ps.strict_currency_label_enabled() is True


# ---------------------------------------------------------------------------
# 2. (b) the GCC display-symbol -> ISO table
# ---------------------------------------------------------------------------

SYMBOL_CASES = [
    ("KD", "KWD"), ("KWD", "KWD"),
    (OMR_SYMBOL, "OMR"), ("OMR", "OMR"),
    (QAR_SYMBOL, "QAR"), ("QR", "QAR"), ("QAR", "QAR"),
    (SAR_SYMBOL, "SAR"), ("SR", "SAR"), ("SAR", "SAR"),
    (AED_SYMBOL, "AED"), ("AED", "AED"), ("DHS", "AED"),
    (BHD_SYMBOL, "BHD"), ("BD", "BHD"), ("BHD", "BHD"),
]


class TestSymbolNormalisation:
    """Every symbol the assignment names, plus the Latin variants."""

    @pytest.mark.parametrize("raw,iso", SYMBOL_CASES)
    def test_normalises_to_iso(self, raw, iso):
        assert ps._normalize_currency_code(raw) == iso

    @pytest.mark.parametrize("raw,iso", SYMBOL_CASES)
    def test_table_entries_are_in_the_rate_table(self, raw, iso):
        from app.services.exchange_rate_service import FALLBACK_RATES
        assert iso in FALLBACK_RATES, raw + " normalises to a rate-less code"

    def test_bidi_marks_and_nbsp_do_not_defeat_the_lookup(self):
        # Real GCC pages wrap the symbol in RLM/LRM and NBSP.
        assert ps._normalize_currency_code("‏" + QAR_SYMBOL + " ") == "QAR"

    def test_iso_code_is_never_overridden_by_the_symbol_table(self):
        assert ps._normalize_currency_code("usd") == "USD"
        assert ps._normalize_currency_code("EUR") == "EUR"

    @pytest.mark.parametrize(
        "raw", ["", None, "  ", TUGRIK, "ZZZ", "XYZ", 5, [], "$$$"]
    )
    def test_unresolvable_returns_none(self, raw):
        assert ps._normalize_currency_code(raw) is None

    @pytest.mark.parametrize("raw", ["DH", "RO", "R", "D", "RS"])
    def test_ambiguous_tokens_are_deliberately_absent(self, raw):
        """A wrong entry is a silently mis-CONVERTED price.

        "DH" is the Moroccan dirham as well as the Emirati one and MAD is ~2.7x
        from AED; "RO" is not a spelling Omani stores emit; bare initials are
        too short to be unambiguous. All of them must pend, not guess.
        """
        assert ps._normalize_currency_code(raw) is None


class TestConvertToBhdUsesTheTable:
    @pytest.mark.parametrize("symbol,iso", [
        (QAR_SYMBOL, "QAR"), (SAR_SYMBOL, "SAR"), (AED_SYMBOL, "AED"),
        (OMR_SYMBOL, "OMR"), (BHD_SYMBOL, "BHD"),
        ("KD", "KWD"), ("SR", "SAR"), ("QR", "QAR"), ("BD", "BHD"),
    ])
    def test_flag_on_converts_at_the_iso_rate(self, monkeypatch, symbol, iso):
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        assert ps._convert_to_bhd(100.0, symbol) == pytest.approx(
            100.0 * FALLBACK_RATES[iso]
        )

    @pytest.mark.parametrize("symbol", [
        QAR_SYMBOL, SAR_SYMBOL, AED_SYMBOL, OMR_SYMBOL, BHD_SYMBOL,
        "KD", "SR", "QR", "BD",
    ])
    def test_flag_off_is_the_8adaefb_passthrough(self, monkeypatch, symbol):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        assert ps._convert_to_bhd(100.0, symbol) == 100.0

    def test_flag_on_still_gives_up_on_a_genuinely_unknown_token(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        # Contract preserved for the 8 adapter modules that call this directly:
        # unresolvable -> amount UNCHANGED (they each re-check before stamping).
        assert ps._convert_to_bhd(100.0, "ZZZ") == 100.0

    def test_iso_rates_are_untouched_by_the_flag(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        for flag in ("true", "false"):
            monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", flag)
            assert ps._convert_to_bhd(100.0, "USD") == pytest.approx(
                100.0 * FALLBACK_RATES["USD"]
            )


# ---------------------------------------------------------------------------
# 3. (a) an unresolvable currency is NEVER stamped BHD
# ---------------------------------------------------------------------------

class TestConvertGptPriceCurrency:
    def _price(self, original):
        return {
            "amount": 320.0, "original_currency": original, "currency": original,
            "retailer": "example.com", "url": "https://example.com/p",
            "in_stock": True, "confidence": 0.9, "estimated": False,
            "source_method": "page_scrape",
        }

    def test_flag_on_unresolvable_does_not_relabel_and_reports_failure(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        p = self._price("ZZZ")
        ok = ps._convert_gpt_price_currency(p, "BHD")
        assert ok is False
        assert p["currency"] == "ZZZ", "an unresolvable currency was relabelled"
        assert p["amount"] == 320.0, "an unresolvable amount was silently mutated"

    def test_flag_off_reproduces_the_8adaefb_relabel(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        p = self._price("ZZZ")
        ps._convert_gpt_price_currency(p, "BHD")
        assert p["currency"] == "BHD"
        assert p["amount"] == 320.0

    def test_flag_on_resolvable_symbol_converts_and_labels_bhd(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        p = self._price(QAR_SYMBOL)
        ok = ps._convert_gpt_price_currency(p, "BHD")
        assert ok is True
        assert p["currency"] == "BHD"
        assert p["amount"] == pytest.approx(round(320.0 * FALLBACK_RATES["QAR"], 2))
        assert p["original_currency"] == QAR_SYMBOL

    def test_flag_on_arabic_bhd_symbol_is_not_converted_away(self, monkeypatch):
        """The dotted dinar glyph IS BHD - relabel it, never rate-convert it."""
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        p = self._price(BHD_SYMBOL)
        ok = ps._convert_gpt_price_currency(p, "BHD")
        assert ok is True
        assert p["currency"] == "BHD"
        assert p["amount"] == 320.0

    def test_return_value_is_true_on_the_ordinary_iso_path(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        p = self._price("USD")
        assert ps._convert_gpt_price_currency(p, "BHD") is True
        assert p["currency"] == "BHD"

    def test_no_amount_is_still_a_no_op(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        p = self._price("ZZZ")
        p["amount"] = 0
        assert ps._convert_gpt_price_currency(p, "BHD") is False
        assert p["currency"] == "ZZZ"

    def test_unresolvable_target_currency_also_fails_closed(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        p = self._price("USD")
        assert ps._convert_gpt_price_currency(p, "ZZZ") is False
        assert p["currency"] == "USD"
        assert p["amount"] == 320.0


# ---------------------------------------------------------------------------
# 4. the extractor branches PEND rather than serve a mislabelled price
# ---------------------------------------------------------------------------

class TestWooCommerceBranch:
    def test_flag_on_unresolvable_symbol_pends(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        assert _woo_price(TUGRIK) is None, "a Tugrik price was served as a BH price"

    def test_flag_off_serves_it_stamped_bhd(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        r = _woo_price(TUGRIK)
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 350.0

    def test_flag_on_gcc_symbol_converts_instead_of_pending(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        r = _woo_price(SAR_SYMBOL)
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(350.0 * FALLBACK_RATES["SAR"], 2))

    def test_flag_on_native_bhd_page_is_untouched(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        r = _woo_price("BHD", "45.500")
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 45.5


class TestOgBranch:
    def _og(self, code):
        return (
            "<html><head>"
            "<meta property='product:price:amount' content='350.00'>"
            "<meta property='product:price:currency' content='" + code + "'>"
            "</head><body></body></html>"
        )

    def test_flag_on_unresolvable_pends(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        soup = BeautifulSoup(self._og(TUGRIK), "html.parser")
        assert ps._extract_og_price(
            soup, "Reef", "BHD", "example.com", "https://example.com/p"
        ) is None

    def test_flag_off_serves_it_stamped_bhd(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        soup = BeautifulSoup(self._og(TUGRIK), "html.parser")
        r = ps._extract_og_price(
            soup, "Reef", "BHD", "example.com", "https://example.com/p"
        )
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 350.0

    def test_flag_on_gcc_symbol_converts(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        soup = BeautifulSoup(self._og(AED_SYMBOL), "html.parser")
        r = ps._extract_og_price(
            soup, "Reef", "BHD", "example.com", "https://example.com/p"
        )
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(350.0 * FALLBACK_RATES["AED"], 2))


class TestMicrodataBranch:
    def _micro(self, code):
        return (
            "<html><body><div itemscope itemtype='http://schema.org/Offer'>"
            "<meta itemprop='priceCurrency' content='" + code + "'>"
            "<meta itemprop='price' content='350.00'>"
            "</div></body></html>"
        )

    def test_flag_on_unresolvable_pends(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        soup = BeautifulSoup(self._micro(TUGRIK), "html.parser")
        assert ps._extract_microdata_price(
            soup, "BHD", "example.com", "https://example.com/p"
        ) is None

    def test_flag_off_serves_it_stamped_bhd(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        soup = BeautifulSoup(self._micro(TUGRIK), "html.parser")
        r = ps._extract_microdata_price(
            soup, "BHD", "example.com", "https://example.com/p"
        )
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 350.0


class TestJsonLdBranch:
    def _jsonld(self, code):
        return (
            "<html><head><script type='application/ld+json'>"
            '{"@context":"https://schema.org","@type":"Product",'
            '"name":"Reef 33 Black","brand":{"@type":"Brand","name":"Reef"},'
            '"offers":{"@type":"Offer","price":"350.00","priceCurrency":"' + code + '",'
            '"availability":"https://schema.org/InStock"}}'
            "</script></head><body></body></html>"
        )

    def _run(self, code):
        return ps.extract_price_from_html(
            self._jsonld(code), "Reef 33 Black", "BHD",
            "example.com", "https://example.com/p", category="fragrances",
        )

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_an_unresolvable_currency_never_reaches_the_label_step(self, monkeypatch, flag):
        """MEASURED, and the reason the JSON-LD guard is belt-and-braces.

        ``extract_jsonld_price`` filters on ``str(priceCurrency).upper() !=
        expected_currency.upper(): continue`` (price_service.py:9516), and
        ``extract_price_from_html`` only ever asks it for the target currency
        and then USD. So the JSON-LD branch can only ever hand
        ``_convert_gpt_price_currency`` a code that is already BHD (a no-op) or
        USD (resolvable) — an unresolvable one is dropped one layer earlier, on
        BOTH flag settings, and the price pends with no label written at all.
        The ``_label_ok`` guard on that branch is therefore defensive: it exists
        so a future loosening of the currency filter cannot reintroduce
        BLOCKER 4 there. Pinned in both directions so the claim stays true.
        """
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", flag)
        assert self._run(TUGRIK) is None

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_the_usd_needs_conversion_path_is_unchanged_by_the_flag(self, monkeypatch, flag):
        """The one currency this branch really does convert: the USD fallback."""
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", flag)
        r = self._run("USD")
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(350.0 * FALLBACK_RATES["USD"], 2))
        assert r["source_method"] == "converted_usd"

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_a_native_bhd_offer_is_unchanged_by_the_flag(self, monkeypatch, flag):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", flag)
        r = self._run("BHD")
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 350.0
        assert r["source_method"] == "page_scrape"


# ---------------------------------------------------------------------------
# 5. the CORPUS case the lead measured
# ---------------------------------------------------------------------------

class TestQatarPerfumeShopCorpus:
    """qatarperfumeshop.com -> 32,000 Bahraini dinar for a bottle of perfume."""

    def _run(self):
        html = _corpus_page(QPS_URL)
        return ps.extract_price_from_html(
            html, "Reef 33 Black for Men amp; Women", "BHD",
            "qatarperfumeshop.com", QPS_URL, category="fragrances",
        )

    def test_flag_off_reproduces_todays_behaviour_byte_identically(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        # BLOCKER 6 (a LATER wave) fixed the MAGNITUDE: the page's "320,00" is
        # 320.00 QAR, not 32000. This test pins the 8adaefb baseline, so it
        # needs BOTH rollback flags off - the 32000.0 below is the legacy
        # comma-strip, not the strict-currency behaviour this file is about.
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")
        assert self._run() == {
            "amount": 32000.0,
            "original_currency": QAR_SYMBOL,
            "currency": "BHD",
            "retailer": "qatarperfumeshop.com",
            "url": QPS_URL,
            "in_stock": True,
            "confidence": 0.9,
            "estimated": False,
            "source_method": "page_scrape",
        }

    def test_flag_on_is_no_longer_a_bhd_price_at_a_1_to_1_rate(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        r = self._run()
        if r is not None and r["currency"] == "BHD":
            assert r["amount"] != 32000.0, (
                "32,000 BHD for a bottle of perfume: "
                "the QAR symbol was relabelled, not converted"
            )

    @pytest.mark.parametrize("money_v2,riyals", [
        ("false", 32000.0),   # the legacy comma-strip reading of "320,00"
        ("true", 320.0),      # BLOCKER 6 - what the page actually prints
    ], ids=["money_parser_v1", "money_parser_v2"])
    def test_flag_on_converts_at_the_qar_rate(self, monkeypatch, money_v2, riyals):
        """The RATE is this file's subject and it is right in both states; the
        MAGNITUDE was BLOCKER 6's, fixed by ENABLE_MONEY_PARSER_V2. Pinning both
        rows keeps the two fixes independently rollback-able."""
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", money_v2)
        r = self._run()
        assert r is not None, "the QAR symbol is resolvable -> convert, do not pend"
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(riyals * FALLBACK_RATES["QAR"], 2))
        assert r["original_currency"] == QAR_SYMBOL


class TestShippedMode:
    """The defect measured with ENABLE_EXACT_PRICE_GATE=**true** (SHIPPED).

    The corpus page ALONE is not proof of production impact, and this is the
    trap the repro note warns about, sprung in the other direction: with the
    exact gate ON the identity gate rejects qatarperfumeshop.com's cached PDP
    outright, so that page pends on both strict settings and its 32000.0 never
    reaches a user. What makes the defect real in production is that NOTHING in
    the exact-identity layer inspects a currency - so a page whose identity DOES
    match still gets its glyph relabelled.

    This class builds exactly that page: a WooCommerce PDP whose og:title
    matches the query (so ``_page_identity_ok`` passes) priced at 350 in the
    Qatari-riyal glyph. Measured, exact gate ON:

        before -> 350.0 BHD   (a 350 QAR bottle sold as 350 Bahraini dinar,
                               9.7x over, and - unlike the corpus page's
                               32000 - entirely PLAUSIBLE, so every downstream
                               magnitude guard passes it through)
        after  -> 36.16 BHD   (350 * 0.1033, correct)
    """

    QAR_PDP = (
        "<html><head><title>Reef 33 Black Eau de Parfum 100ml</title>"
        "<meta property='og:title' content='Reef 33 Black Eau de Parfum 100ml'>"
        "</head><body><p class='price'>"
        "<span class='woocommerce-Price-amount amount'>"
        "<span class='woocommerce-Price-currencySymbol'>" + QAR_SYMBOL + "</span>350.00"
        "</span></p></body></html>"
    )

    def _run(self, html, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")   # SHIPPED mode
        return ps.extract_price_from_html(
            html, "Reef 33 Black Eau de Parfum 100ml", "BHD",
            "qatarperfumeshop.com", "https://qatarperfumeshop.com/product/reef/",
            category="fragrances",
        )

    def test_flag_off_sells_a_350_qar_bottle_as_350_bhd(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        r = self._run(self.QAR_PDP, monkeypatch)
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 350.0

    def test_flag_on_converts_at_the_qar_rate(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        r = self._run(self.QAR_PDP, monkeypatch)
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(350.0 * FALLBACK_RATES["QAR"], 2))

    def test_flag_on_pends_a_currency_the_table_cannot_resolve(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        r = self._run(self.QAR_PDP.replace(QAR_SYMBOL, TUGRIK), monkeypatch)
        assert r is None

    def test_flag_off_stamps_that_same_unresolvable_price_bhd(self, monkeypatch):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
        r = self._run(self.QAR_PDP.replace(QAR_SYMBOL, TUGRIK), monkeypatch)
        assert r is not None
        assert r["currency"] == "BHD"
        assert r["amount"] == 350.0


# ---------------------------------------------------------------------------
# 6. THE CURRENCY-EVIDENCE HIERARCHY
#
# WHY THIS SECTION EXISTS. `_currency_label_for` used to end with
# `or iso_currency_label(expected)`, which collapsed a PRESENT-but-unreadable
# currency token into the ASK currency. That reads "this page says something I
# cannot parse" as "this page says nothing", and those are not the same state:
# the second one is a page whose money is denominated in SOMETHING, and
# stamping it with the ask asserts a 1.0 rate nothing measured. It un-did
# BLOCKER 4 for every branch — the three `test_flag_on_unresolvable*` tests in
# section 4 above are the direct casualties — and it shipped two measured
# over-prices on the cached corpora, both re-pinned below.
#
# The hierarchy is now: (1) the branch's own token when it resolves to ISO;
# (2) PAGE-LEVEL evidence — an OG/product currency meta or any JSON-LD
# priceCurrency on the document; (3) evidence absent AND the token MISSING ->
# the expected currency (the sharafdg rule, unchanged); (4) evidence absent AND
# the token PRESENT-but-junk -> the RAW token, which conversion fails on and
# `strict_currency_label_enabled()` then pends at every call site.
# ---------------------------------------------------------------------------

NICHE_BEAUTY = "de_niche_beauty_com_microdata_no_pricecurrency.html"
SAMAWA = "ae_samawa_ae_og_no_currency_jsonld_aed.html"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestPageCurrencyEvidence:
    """Rung 2 in isolation. Provenance for both real pages is in
    tests/fixtures/jsonld_first/SOURCES.json."""

    def test_no_document_is_no_evidence(self):
        assert ps._page_currency_evidence(None) is None

    def test_a_silent_document_yields_none(self):
        soup = BeautifulSoup("<html><body><p>350.00</p></body></html>", "html.parser")
        assert ps._page_currency_evidence(soup) is None

    def test_a_document_whose_only_token_is_junk_yields_none(self):
        """The state that MUST stay distinguishable from 'silent' — otherwise
        rung 2 would launder the junk into a confident label."""
        soup = BeautifulSoup(
            "<html><head>"
            "<meta property='og:price:currency' content='N/A'>"
            "</head><body></body></html>", "html.parser",
        )
        assert ps._page_currency_evidence(soup) is None

    @pytest.mark.parametrize("prop", [
        "og:price:currency", "product:price:currency", "product:sale_price:currency",
    ])
    def test_each_price_currency_meta_is_read(self, prop):
        soup = BeautifulSoup(
            "<html><head><meta property='" + prop + "' content='EUR'>"
            "</head><body></body></html>", "html.parser",
        )
        assert ps._page_currency_evidence(soup) == "EUR"

    def test_a_meta_is_iso_normalised_not_stamped_raw(self):
        """flormar.com.tr publishes a lowercase code; the GCC hosts publish
        glyphs. Evidence goes through the same resolver rung 1 uses."""
        for raw, iso in (("try", "TRY"), ("aed", "AED"), (QAR_SYMBOL, "QAR")):
            soup = BeautifulSoup(
                "<html><head><meta property='og:price:currency' content='"
                + raw + "'></head><body></body></html>", "html.parser",
            )
            assert ps._page_currency_evidence(soup) == iso

    def test_a_jsonld_offer_price_currency_is_read(self):
        soup = BeautifulSoup(
            "<html><head><script type='application/ld+json'>"
            '{"@type":"Product","offers":{"@type":"Offer","price":"271.0",'
            '"priceCurrency":"AED"}}'
            "</script></head><body></body></html>", "html.parser",
        )
        assert ps._page_currency_evidence(soup) == "AED"

    def test_jsonld_evidence_survives_the_shapes_the_corpora_publish(self):
        """@graph members, hasVariant children and priceSpecification all count —
        this asks what currency the PAGE is written in, never what the price is."""
        shapes = (
            '{"@graph":[{"@type":"Product","offers":{"priceCurrency":"OMR"}}]}',
            '[{"@type":"ProductGroup","hasVariant":[{"offers":'
            '{"priceCurrency":"OMR"}}]}]',
            '{"@type":"Product","offers":{"priceSpecification":'
            '{"priceCurrency":"OMR"}}}',
        )
        for blob in shapes:
            soup = BeautifulSoup(
                "<html><head><script type='application/ld+json'>" + blob
                + "</script></head><body></body></html>", "html.parser",
            )
            assert ps._page_currency_evidence(soup) == "OMR", blob

    def test_an_unreadable_jsonld_block_is_skipped_not_raised(self):
        soup = BeautifulSoup(
            "<html><head>"
            "<script type='application/ld+json'>{not json,,,</script>"
            "<script type='application/ld+json'>"
            '{"offers":{"priceCurrency":"SAR"}}</script>'
            "</head><body></body></html>", "html.parser",
        )
        assert ps._page_currency_evidence(soup) == "SAR"

    def test_a_meta_outranks_a_jsonld_offer(self):
        """The metas are the storefront TEMPLATE's own declaration; a JSON-LD
        Offer may be one of several (a related-product rail carries them too)."""
        soup = BeautifulSoup(
            "<html><head><meta property='og:price:currency' content='EUR'>"
            "<script type='application/ld+json'>"
            '{"offers":{"priceCurrency":"USD"}}</script>'
            "</head><body></body></html>", "html.parser",
        )
        assert ps._page_currency_evidence(soup) == "EUR"


class TestLabelHierarchy:
    """`_currency_label_for` rung by rung, with the document threaded in."""

    def _soup(self, *metas):
        return BeautifulSoup(
            "<html><head>" + "".join(metas) + "</head><body></body></html>",
            "html.parser",
        )

    def test_rung_1_a_resolvable_token_never_consults_the_page(self):
        soup = self._soup("<meta property='og:price:currency' content='EUR'>")
        assert ps._currency_label_for(QAR_SYMBOL, "BHD", soup) == "QAR"
        assert ps._currency_label_for("bhd", "BHD", soup) == "BHD"

    def test_rung_2_evidence_beats_the_expected_currency_for_a_missing_token(self):
        soup = self._soup("<meta property='og:price:currency' content='EUR'>")
        assert ps._currency_label_for(None, "BHD", soup) == "EUR"
        assert ps._currency_label_for("", "BHD", soup) == "EUR"

    def test_rung_2_evidence_beats_a_junk_token(self):
        soup = self._soup("<meta property='product:price:currency' content='AED'>")
        assert ps._currency_label_for(TUGRIK, "BHD", soup) == "AED"

    def test_rung_3_missing_token_and_no_evidence_is_the_expected_currency(self):
        assert ps._currency_label_for(None, "BHD", self._soup()) == "BHD"
        assert ps._currency_label_for("  ", "BHD", self._soup()) == "BHD"

    def test_rung_4_a_junk_token_with_no_evidence_comes_back_RAW(self):
        """NOT the ask currency. Returning it raw is what re-arms the existing
        machinery: conversion fails on it and every call site already pends."""
        assert ps._currency_label_for(TUGRIK, "BHD", self._soup()) == TUGRIK
        assert ps._currency_label_for("N/A", "BHD", self._soup()) == "N/A"

    def test_the_document_is_optional(self):
        """A direct caller with no soup keeps rungs 1, 3 and 4."""
        assert ps._currency_label_for("usd", "BHD") == "USD"
        assert ps._currency_label_for(None, "BHD") == "BHD"
        assert ps._currency_label_for("N/A", "BHD") == "N/A"


class TestNicheBeautyMicrodataUsesTheOgCurrency:
    """de_niche_beauty_com_microdata_no_pricecurrency.html — the 2.27x.

    The page's Offer carries ``itemprop=price content="195.00"`` and NO
    ``itemprop=priceCurrency`` anywhere; three lines above it
    ``og:price:currency`` says EUR. Asked in BHD, the microdata branch used to
    label the 195 with the ASK and ship 195.0 "BHD" for a 195 EUR product.
    """

    def _run(self, monkeypatch, strict="true"):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", strict)
        return ps._extract_microdata_price(
            BeautifulSoup(_fixture(NICHE_BEAUTY), "html.parser"),
            "BHD", "niche-beauty.com",
            "https://www.niche-beauty.com/de-de/produkte/borntostandout-cola-addict/752-052",
        )

    def test_the_og_currency_is_consulted_and_the_price_is_converted(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        r = self._run(monkeypatch)
        assert r is not None, "EUR is resolvable — convert, do not pend"
        assert r["original_currency"] == "EUR"
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(195.0 * FALLBACK_RATES["EUR"], 2))
        assert r["source_method"] == "converted_usd"

    def test_it_is_no_longer_195_bahraini_dinar(self, monkeypatch):
        r = self._run(monkeypatch)
        assert not (r["currency"] == "BHD" and r["amount"] == 195.0), (
            "195 EUR shipped as 195 BHD — 2.27x, and entirely plausible, so no "
            "downstream magnitude guard catches it"
        )

    def test_an_eur_ask_still_reads_the_page_natively(self, monkeypatch):
        """The pre-existing EUR-ask pin in tests/test_jsonld_first_precedence.py
        (test_b_e / test_b_f) must not move: on an EUR ask rung 2 and rung 3
        agree, so the answer is the same 195.0 EUR either way."""
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
        r = ps._extract_microdata_price(
            BeautifulSoup(_fixture(NICHE_BEAUTY), "html.parser"),
            "EUR", "niche-beauty.com", "https://x/y",
        )
        assert r["amount"] == 195.0
        assert r["original_currency"] == "EUR"
        assert r["source_method"] == "page_scrape"


class TestSamawaOgUsesTheDeclinedJsonLdOffersCurrency:
    """ae_samawa_ae_og_no_currency_jsonld_aed.html — the 9.77x.

    samawa.ae publishes ``product:price:amount 271.00`` and, instead of a
    currency meta, a SECOND ``product:price:amount`` whose content is the literal
    "AED" (the store's own template bug). So the OG branch sees the currency tag
    as MISSING and used to fall straight to the ask. The document is not silent
    though: its Product JSON-LD Offer says AED — declined as a PRICE source
    (priceCurrency != the BHD ask, and OutOfStock), but perfectly good EVIDENCE
    of what the 271 is denominated in.
    """

    URL = ("https://samawa.ae/products/"
           "paco-rabanne-lady-million-prive-for-women-eau-de-parfum-80ml")

    def _run(self, monkeypatch, strict="true"):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", strict)
        return ps.extract_price_from_html(
            _fixture(SAMAWA),
            "Paco Rabanne Lady Million Prive for Women - Eau de Parfum, 80ml",
            "BHD", "samawa.ae", self.URL, category="fragrances",
        )

    def test_the_jsonld_offer_currency_is_the_page_evidence(self):
        assert ps._page_currency_evidence(
            BeautifulSoup(_fixture(SAMAWA), "html.parser")
        ) == "AED"

    def test_the_271_is_converted_out_of_aed(self, monkeypatch):
        from app.services.exchange_rate_service import FALLBACK_RATES
        r = self._run(monkeypatch)
        assert r is not None, "AED is resolvable — convert, do not pend"
        assert r["original_currency"] == "AED"
        assert r["currency"] == "BHD"
        assert r["amount"] == pytest.approx(round(271.0 * FALLBACK_RATES["AED"], 2))

    def test_it_is_no_longer_271_bahraini_dinar(self, monkeypatch):
        r = self._run(monkeypatch)
        assert not (r["currency"] == "BHD" and r["amount"] == 271.0), (
            "271 AED shipped as 271 BHD — 9.77x"
        )


class TestMissingEverythingStillMeansTheExpectedCurrency:
    """Rung 3, the sharafdg rule — the thing rung 4 must NOT swallow.

    Already pinned end to end at
    tests/test_og_branch_fixes.py::TestUnchangedOgBehaviour::
    test_currencyless_og_defaults_to_expected_not_usd (244.990 -> BHD, both
    ENABLE_OG_BRANCH_FIXES states) and at
    tests/test_og_branch_fixes.py::...::
    test_a_currencyless_og_price_uses_the_EXPECTED_currency_minor_unit (the
    "22,902" -> 22.902 tie-break, which only reads right if the LABEL fell back
    to BHD). Re-pinned here against the strict flag, which is what now decides
    whether a fallback happens at all.
    """

    SHARAFDG = (
        "<html><head>"
        '<meta property="product:price:amount" content="244.990">'
        "</head><body></body></html>"
    )

    @pytest.mark.parametrize("strict", ["true", "false"])
    def test_a_page_with_no_currency_anywhere_is_read_in_the_ask(self, monkeypatch, strict):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", strict)
        r = ps.extract_price_from_html(
            self.SHARAFDG, "Apple iPhone 15 128GB", "BHD", "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-blue/",
        )
        assert r is not None, "a currency-less BH page must not pend"
        assert r["amount"] == pytest.approx(244.990)
        assert r["currency"] == "BHD"
        assert r["source_method"] == "page_scrape", "not a conversion"

    def test_the_soup_is_what_makes_the_two_states_separable(self):
        """Same branch, same ask, one document silent and one document junk —
        different answers. That is the whole fix in one assertion."""
        silent = BeautifulSoup(self.SHARAFDG, "html.parser")
        assert ps._currency_label_for(None, "BHD", silent) == "BHD"
        assert ps._currency_label_for("N/A", "BHD", silent) == "N/A"


class TestJunkWithNoEvidenceStillPends:
    """Rung 4 through the branches — section 4's guarantee, restored.

    Section 4 already pins the three `test_flag_on_unresolvable*` cases; these
    add the case that motivates rung 4 specifically: a page that carries a real
    junk token AND nothing else to consult.
    """

    BROWNTHOMAS = (
        '<html><head><title>Aventus Eau de Parfum</title>'
        '<meta property="og:title" content="Aventus Eau de Parfum"/>'
        '<meta property="og:price:amount" content="285.00"/>'
        '<meta property="og:price:currency" content="N/A"/>'
        "</head><body></body></html>"
    )

    def _run(self, monkeypatch, strict):
        monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", strict)
        return ps.extract_price_from_html(
            self.BROWNTHOMAS, "Aventus Eau de Parfum", "EUR",
            "www.brownthomas.com", "https://x/y",
        )

    def test_flag_on_pends(self, monkeypatch):
        assert self._run(monkeypatch, "true") is None

    def test_flag_off_is_the_legacy_serve_with_the_ask_label(self, monkeypatch):
        """Rollback fidelity: 8adaefb relabelled the junk to the ask at an
        implicit rate and shipped it. It still does with the flag off."""
        r = self._run(monkeypatch, "false")
        assert r is not None
        assert r["currency"] == "EUR"
        assert r["original_currency"] == "N/A"


# ---------------------------------------------------------------------------
# 7. FOLLOW-UP (out of scope, pinned so it cannot be forgotten)
# ---------------------------------------------------------------------------

class TestCommaDecimalFollowUp:
    """The follow-up this file recorded - now FIXED as BLOCKER 6.

    "320,00" is a comma-DECIMAL (320.00 QAR) on qatarperfumeshop.com, and the
    unconditional ``cleaned.replace(",", "")`` read it as 32000 - a 100x
    over-price that survived the strict-currency fix as 3305.6 BHD. It was
    deliberately untouched HERE (its blast radius reaches every caller of
    parse_price_string, so it needed its own flag and its own measured
    before/after) and is fixed in the NEXT wave behind ENABLE_MONEY_PARSER_V2,
    using exactly the currency-minor-unit reasoning BLOCKER 2 applied to the OG
    parser. Both readings stay pinned here so this file keeps documenting which
    flag owns which number; the full table lives in
    tests/test_money_parser_v2.py.
    """

    def test_the_comma_decimal_is_fixed(self, monkeypatch):
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "true")
        assert ps.parse_price_string("320,00") == pytest.approx(320.0)

    def test_the_rollback_still_reads_it_as_thousands(self, monkeypatch):
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")
        assert ps.parse_price_string("320,00") == 32000.0

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_comma_thousands_still_works(self, monkeypatch, flag):
        """A REAL thousands group reads the same in both flag states - that is
        the whole reason the "depended on elsewhere" objection did not hold."""
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", flag)
        assert ps.parse_price_string("SAR 2,499") == 2499.0

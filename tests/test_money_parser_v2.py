# -*- coding: utf-8 -*-
"""SURVIVING BLOCKER 6 - ONE canonical money parser, behind ENABLE_MONEY_PARSER_V2.

THE DEFECT (pre-existing on 8adaefb, and it SURVIVED both earlier waves).
``parse_price_string`` does an UNCONDITIONAL ``cleaned.replace(",", "")``, so
every comma is read as a thousands separator. The WooCommerce shelf price
"320,00" on qatarperfumeshop.com (320.00 QAR) is therefore read as 32000.

Measured end-to-end on the cached page, ENABLE_EXACT_PRICE_GATE=false
(EXTRACTION isolation), BEFORE this fix::

    amount 3305.6   currency BHD   original_currency U+0631 U+002E U+0642

The strict-currency fix (BLOCKER 4) corrected the LABEL and the RATE - 32000
riyal-ish units converted at the real QAR rate - but never the MAGNITUDE. The
true price is 320.00 QAR = 33.06 BHD. It is the same 100x, one conversion later.

WHY IT IS IN SCOPE NOW. The 328-page / 163-host / 26-country global validation
turned this from a Qatari curiosity into a worldwide defect and, more usefully,
MEASURED which rule to replace it with:

  * "dot is decimal, comma is thousands" (today's rule) ....... 244/372 = 65.6%
      and it COLLAPSES regionally: 1/88 = 1% in EU-South, 39/70 = 56% in DACH.
      Real victims: "2.019 TL" read as 2.019 lira instead of 2019, "1.454 kr."
      as 1.454 instead of 1454, "73,39 EUR" as 7339 instead of 73.39.
  * LAST-SEPARATOR (the rightmost . or , with a 1-2 digit tail is the decimal
    point; everything left of it is grouping) ................. 368/372 = 98.9%
  * LAST-SEPARATOR + ONE FACT (a 3-digit tail is the DECIMAL FRACTION when the
    declared currency's ISO-4217 minor unit is 3 - BHD KWD OMR JOD TND IQD LYD
    - and a GROUPING otherwise) ............................... 371/371 = 100%
    in all six regions. Prerequisites: Arabic-Indic digit normalisation and
    NBSP folding.

  Hardest single string in the corpus: smartbuy-me.com "1,799.000 JOD" - comma
  grouping AND a 3-decimal fraction in one number. A naive single-separator
  variant fails on exactly this string; the mixed-separator rule ("the
  RIGHTMOST separator is the decimal point, whatever its tail length") gets it.

  Codepoint census over all 328 pages: U+00A0 x299, U+066B x3, U+202F x0,
  U+2009 x0 - so NBSP folding is real work and narrow-space folding is
  insurance, not a measured need. Both are implemented; only NBSP is measured.

THE TWO MODES, and why one parser still has two of them. ``display_text=True``
is human-visible shelf text ("2.019 TL"); ``display_text=False`` (the DEFAULT)
is a machine field whose format is SPECIFIED to use "." as the decimal point -
``og:price:amount``, a Shopify variant ``price``, a JSON API's price field. The
ONE cell where they differ is a lone DOT with a 3-digit tail on a currency whose
minor unit is not 3: display text reads "2.019 TL" as 2019 (measured), the
machine field keeps "3.000" = 3.0 (the ruling ``_parse_og_price_number`` already
shipped, pinned cell-by-cell in tests/test_og_branch_fixes.py, and the reading
that keeps the flag's blast radius at ZERO for every caller that does not
opt in). Every other rule - and the whole comma half, which is where BLOCKER 6
lives - is identical in both modes.

FLAG: ENABLE_MONEY_PARSER_V2, default ON. Flag OFF reproduces today's parse
EXACTLY, INCLUDING the 32000.0 / 3305.6 on qatarperfumeshop.com. That is the
rollback contract and it is pinned below, end-to-end, on the real cached bytes.
"""
import hashlib
import io
import math
from pathlib import Path

import pytest

import app.services.price_service as ps
from app.services.price_service import (
    _money_minor_unit,
    _parse_og_price_number,
    money_parser_v2_enabled,
    parse_money,
    parse_price_string,
)


REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "_proof" / "html"
QPS_URL = "https://qatarperfumeshop.com/product/reef-perfume/"


def _corpus_page(url: str) -> str:
    name = hashlib.sha1(("curl_cffi|" + url).encode()).hexdigest() + ".html"
    path = CORPUS / name
    if not path.exists():
        pytest.skip("cached corpus page missing: " + name)
    return io.open(path, encoding="utf-8", errors="replace").read()


@pytest.fixture
def v2_on(monkeypatch):
    monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "true")


@pytest.fixture
def v2_off(monkeypatch):
    monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")


# ---------------------------------------------------------------------------
# 1. The flag itself
# ---------------------------------------------------------------------------

class TestFlag:
    def test_defaults_on(self, monkeypatch):
        monkeypatch.delenv("ENABLE_MONEY_PARSER_V2", raising=False)
        assert money_parser_v2_enabled() is True

    @pytest.mark.parametrize("raw", ["false", "FALSE", "0", "no", "off", "", "  "])
    def test_off_words(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", raw)
        assert money_parser_v2_enabled() is False

    @pytest.mark.parametrize("raw", ["true", "TRUE", "1", "yes", "on", "anything"])
    def test_on_words(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", raw)
        assert money_parser_v2_enabled() is True

    def test_read_per_call_never_cached_at_import(self, monkeypatch):
        """House rule 1 - os.getenv PER CALL, so Railway can flip it live."""
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")
        assert money_parser_v2_enabled() is False
        assert parse_price_string("320,00") == 32000.0
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "true")
        assert money_parser_v2_enabled() is True
        assert parse_price_string("320,00") == pytest.approx(320.0)


# ---------------------------------------------------------------------------
# 2. BLOCKER 6 itself - the string, the function, and the real cached page
# ---------------------------------------------------------------------------

class TestBlocker6:
    def test_the_shelf_price_string_is_no_longer_100x(self, v2_on):
        """qatarperfumeshop.com prints "320,00" for 320.00 QAR."""
        assert parse_price_string("320,00") == pytest.approx(320.0)

    def test_flag_off_reproduces_todays_parse_exactly(self, v2_off):
        """The rollback contract, at the string level."""
        assert parse_price_string("320,00") == 32000.0
        assert parse_price_string("24,00") == 2400.0

    def test_end_to_end_on_the_real_cached_bytes(self, monkeypatch):
        """EXTRACTION isolation (ENABLE_EXACT_PRICE_GATE=false) so the identity
        gate cannot reject the page and mask the bug. The page is QAR; the
        pipeline converts to BHD, so the assertion is on the RATIO - flag ON
        must be exactly 100x lower than flag OFF, on the same bytes, same rate.
        """
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        html = _corpus_page(QPS_URL)

        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")
        before = ps.extract_price_from_html(
            html, "Reef Perfume", "BHD", "qatarperfumeshop.com", QPS_URL,
        )
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "true")
        after = ps.extract_price_from_html(
            html, "Reef Perfume", "BHD", "qatarperfumeshop.com", QPS_URL,
        )

        assert before is not None and after is not None
        assert before["amount"] == pytest.approx(3305.6, rel=1e-3), (
            "the pre-fix number measured on these bytes"
        )
        # abs=0.01 because the pipeline rounds the converted amount to 2dp:
        # 3305.6 / 100 is 33.056, which ships as 33.06.
        assert after["amount"] == pytest.approx(before["amount"] / 100.0, abs=0.01)
        assert after["amount"] == pytest.approx(33.06, abs=0.01), (
            "320.00 QAR at the same rate this branch already applies"
        )
        assert after["amount"] < 100.0, "320.00 QAR is ~33 BHD, not ~3306"
        # The BLOCKER 4 label fix is untouched by this wave.
        assert after["currency"] == "BHD"


# ---------------------------------------------------------------------------
# 3. THE GRID - 22 currencies x 51 shapes x 2 modes
# ---------------------------------------------------------------------------
#
# Every cell carries an expected value. The expectation depends on the currency
# ONLY through its ISO-4217 MINOR UNIT (0, 2 or 3) - that is the whole content
# of the "one fact" rule - so each shape row pins three values per mode and the
# 22 currencies below fan those out over 1122 cells per mode, 2244 in total.
# (The brief asked for 49 shapes / 1078 cells, on which the previous wave
# scored 882 PASS / 144 FAIL / 44 UNDECIDABLE. This grid is 51 x 22 and every
# cell is decided.)
# Nothing is left UNDECIDABLE: where a shape is genuinely ambiguous the row
# comment says so and names the reading we ship and why.

THREE_DECIMAL = ["BHD", "KWD", "OMR", "JOD", "TND", "LYD", "IQD"]   # minor unit 3
ZERO_DECIMAL = ["JPY", "KRW", "CLP", "ISK", "VND"]                  # minor unit 0
TWO_DECIMAL = ["USD", "EUR", "GBP", "SAR", "AED", "QAR",            # minor unit 2
               "EGP", "TRY", "DKK", "SEK"]

CURRENCIES = [(c, 3) for c in THREE_DECIMAL] \
    + [(c, 0) for c in ZERO_DECIMAL] \
    + [(c, 2) for c in TWO_DECIMAL]

assert len(CURRENCIES) == 22

NBSP = " "
RLM = "‏"

# (id, raw, display-mode {minor: expected}, machine-mode {minor: expected}, why)
SHAPES = [
    # --- separator-less: nothing to decide ---
    ("bare_zero", "0", {0: 0.0, 2: 0.0, 3: 0.0}, {0: 0.0, 2: 0.0, 3: 0.0},
     "no separator, no ambiguity"),
    ("bare_units", "7", {0: 7.0, 2: 7.0, 3: 7.0}, {0: 7.0, 2: 7.0, 3: 7.0},
     "no separator"),
    ("bare_hundreds", "799", {0: 799.0, 2: 799.0, 3: 799.0},
     {0: 799.0, 2: 799.0, 3: 799.0}, "no separator - the OG corpus bare integer"),
    ("bare_millions", "1234567", {0: 1234567.0, 2: 1234567.0, 3: 1234567.0},
     {0: 1234567.0, 2: 1234567.0, 3: 1234567.0}, "no separator"),

    # --- a 1-2 digit tail is ALWAYS the decimal fraction (the last-separator
    #     rule proper). This half is where BLOCKER 6 lives. ---
    ("dot_zero_head", "0.5", {0: 0.5, 2: 0.5, 3: 0.5}, {0: 0.5, 2: 0.5, 3: 0.5},
     "a grouping run can never have a 0 head"),
    ("comma_zero_head", "0,5", {0: 0.5, 2: 0.5, 3: 0.5}, {0: 0.5, 2: 0.5, 3: 0.5},
     "same, comma side"),
    ("dot_two_tail", "12.34", {0: 12.34, 2: 12.34, 3: 12.34},
     {0: 12.34, 2: 12.34, 3: 12.34}, "en-US cents"),
    ("comma_two_tail", "12,34", {0: 12.34, 2: 12.34, 3: 12.34},
     {0: 12.34, 2: 12.34, 3: 12.34}, "BLOCKER 6 - legacy read this as 1234"),
    ("qps_shelf_price", "320,00", {0: 320.0, 2: 320.0, 3: 320.0},
     {0: 320.0, 2: 320.0, 3: 320.0},
     "qatarperfumeshop.com QAR - legacy 32000, the whole blocker"),
    ("qps_dotted", "320.00", {0: 320.0, 2: 320.0, 3: 320.0},
     {0: 320.0, 2: 320.0, 3: 320.0}, "the same money, dotted"),
    ("eu_south_measured", "73,39", {0: 73.39, 2: 73.39, 3: 73.39},
     {0: 73.39, 2: 73.39, 3: 73.39},
     "measured EU-South failure - legacy read 73,39 EUR as 7339"),
    ("comma_one_tail", "1,5", {0: 1.5, 2: 1.5, 3: 1.5}, {0: 1.5, 2: 1.5, 3: 1.5},
     "a 1-digit tail is never a grouping run"),
    ("dot_one_tail", "1.5", {0: 1.5, 2: 1.5, 3: 1.5}, {0: 1.5, 2: 1.5, 3: 1.5},
     "same, dot side"),
    ("comma_four_tail", "1,2345", {0: 1.2345, 2: 1.2345, 3: 1.2345},
     {0: 1.2345, 2: 1.2345, 3: 1.2345},
     "a 4-digit tail is not a grouping run either - decimal"),
    ("trailing_separator", "123,", {0: 123.0, 2: 123.0, 3: 123.0},
     {0: 123.0, 2: 123.0, 3: 123.0}, "empty tail - float('123.') is 123.0"),

    # --- THE ONE FACT: a 3-digit tail is decided by the MINOR UNIT ---
    ("comma_three_tail", "1,234", {0: 1234.0, 2: 1234.0, 3: 1.234},
     {0: 1234.0, 2: 1234.0, 3: 1.234},
     "grouping on 0/2-minor currencies, the dinar fraction on 3-minor"),
    ("dot_three_tail", "1.234", {0: 1234.0, 2: 1234.0, 3: 1.234},
     {0: 1234.0, 2: 1.234, 3: 1.234},
     "THE ONE CELL where the modes differ - see the module docstring"),
    ("turkish_measured", "2.019", {0: 2019.0, 2: 2019.0, 3: 2.019},
     {0: 2019.0, 2: 2.019, 3: 2.019},
     "measured TR failure - '2.019 TL' is 2019 lira, legacy read 2.019"),
    ("danish_measured", "1.454", {0: 1454.0, 2: 1454.0, 3: 1.454},
     {0: 1454.0, 2: 1.454, 3: 1.454},
     "measured DACH/Nordics failure - '1.454 kr.' is 1454, legacy read 1.454"),
    ("bhd_comma_fraction", "22,902", {0: 22902.0, 2: 22902.0, 3: 22.902},
     {0: 22902.0, 2: 22902.0, 3: 22.902},
     "reefperfumes.com BHD - the BLOCKER 2 number, same answer here"),
    ("three_thousand_dot", "3.000", {0: 3000.0, 2: 3000.0, 3: 3.0},
     {0: 3000.0, 2: 3.0, 3: 3.0},
     "AMBIGUOUS: machine mode keeps the shipped og:price:amount ruling (3.0), "
     "display text reads the German/Turkish thousands group (3000)"),
    ("three_thousand_comma", "3,000", {0: 3000.0, 2: 3000.0, 3: 3.0},
     {0: 3000.0, 2: 3000.0, 3: 3.0}, "comma side of the same ambiguity"),
    ("gcc_twelve_five", "12,500", {0: 12500.0, 2: 12500.0, 3: 12.5},
     {0: 12500.0, 2: 12500.0, 3: 12.5}, "12.500 BHD vs twelve-and-a-half thousand"),
    ("sharafdg_bhd", "244.990", {0: 244990.0, 2: 244990.0, 3: 244.99},
     {0: 244990.0, 2: 244.99, 3: 244.99},
     "bahrain.sharafdg.com 3-decimal BHD (measured)"),
    ("og_whitespace", "  59.900  ", {0: 59900.0, 2: 59900.0, 3: 59.9},
     {0: 59900.0, 2: 59.9, 3: 59.9}, "surrounding whitespace is stripped"),

    # --- leading zero beats the tail rule, on every currency ---
    ("zero_head_three_tail_comma", "0,500", {0: 0.5, 2: 0.5, 3: 0.5},
     {0: 0.5, 2: 0.5, 3: 0.5},
     "a grouping run can never have a 0 head - 0,500 is 0.5 on ANY currency"),
    ("zero_head_three_tail_dot", "0.500", {0: 0.5, 2: 0.5, 3: 0.5},
     {0: 0.5, 2: 0.5, 3: 0.5}, "same, dot side"),
    ("double_zero_head", "00,500", {0: 0.5, 2: 0.5, 3: 0.5},
     {0: 0.5, 2: 0.5, 3: 0.5}, "leading-zero head, same ruling"),

    # --- MIXED separators are never ambiguous: the RIGHTMOST is the decimal ---
    ("en_us_full", "1,234.56", {0: 1234.56, 2: 1234.56, 3: 1234.56},
     {0: 1234.56, 2: 1234.56, 3: 1234.56}, "en-US"),
    ("de_de_full", "1.234,56", {0: 1234.56, 2: 1234.56, 3: 1234.56},
     {0: 1234.56, 2: 1234.56, 3: 1234.56}, "de-DE"),
    ("en_us_deep", "1,234,567.89", {0: 1234567.89, 2: 1234567.89, 3: 1234567.89},
     {0: 1234567.89, 2: 1234567.89, 3: 1234567.89}, "multi-group en-US"),
    ("de_de_deep", "1.234.567,89", {0: 1234567.89, 2: 1234567.89, 3: 1234567.89},
     {0: 1234567.89, 2: 1234567.89, 3: 1234567.89}, "multi-group de-DE"),
    ("smartbuy_jod", "1,799.000", {0: 1799.0, 2: 1799.0, 3: 1799.0},
     {0: 1799.0, 2: 1799.0, 3: 1799.0},
     "smartbuy-me.com '1,799.000 JOD' - the hardest string in the corpus: "
     "comma grouping AND a 3-decimal fraction. Mixed => rightmost wins, "
     "whatever its tail length; a naive single-separator rule fails here"),
    ("smartbuy_mirror", "1.799,000", {0: 1799.0, 2: 1799.0, 3: 1799.0},
     {0: 1799.0, 2: 1799.0, 3: 1799.0}, "the de-DE mirror of the same number"),

    # --- a REPEATED separator is a grouping run, whatever the currency ---
    ("comma_groups", "1,234,567", {0: 1234567.0, 2: 1234567.0, 3: 1234567.0},
     {0: 1234567.0, 2: 1234567.0, 3: 1234567.0},
     "two commas cannot both be decimal points"),
    ("dot_groups", "1.234.567", {0: 1234567.0, 2: 1234567.0, 3: 1234567.0},
     {0: 1234567.0, 2: 1234567.0, 3: 1234567.0}, "same, dot side"),

    # --- space grouping: NBSP x299 in the 328-page codepoint census ---
    ("nbsp_group_comma_dec", "1" + NBSP + "234,56",
     {0: 1234.56, 2: 1234.56, 3: 1234.56}, {0: 1234.56, 2: 1234.56, 3: 1234.56},
     "fr-FR / DACH NBSP grouping + comma decimal"),
    ("nbsp_group_dot_dec", "1" + NBSP + "234.56",
     {0: 1234.56, 2: 1234.56, 3: 1234.56}, {0: 1234.56, 2: 1234.56, 3: 1234.56},
     "NBSP grouping + dot decimal"),
    ("nbsp_groups_only", "1" + NBSP + "234" + NBSP + "567",
     {0: 1234567.0, 2: 1234567.0, 3: 1234567.0},
     {0: 1234567.0, 2: 1234567.0, 3: 1234567.0}, "NBSP grouping, no fraction"),
    ("ascii_space_group", "1 234,56", {0: 1234.56, 2: 1234.56, 3: 1234.56},
     {0: 1234.56, 2: 1234.56, 3: 1234.56},
     "ASCII space grouping - the legacy OG parser folded this and must keep to"),
    ("narrow_nospace_group", "1 234,56", {0: 1234.56, 2: 1234.56, 3: 1234.56},
     {0: 1234.56, 2: 1234.56, 3: 1234.56},
     "U+202F: ZERO occurrences in the census, folded as insurance"),
    ("thin_space_group", "1 234,56", {0: 1234.56, 2: 1234.56, 3: 1234.56},
     {0: 1234.56, 2: 1234.56, 3: 1234.56},
     "U+2009: ZERO occurrences in the census, folded as insurance"),

    # --- Arabic-Indic digits and the Arabic separators ---
    ("arabic_indic_int", "١٢٣٤",
     {0: 1234.0, 2: 1234.0, 3: 1234.0}, {0: 1234.0, 2: 1234.0, 3: 1234.0},
     "U+0660-0669 -> ASCII; legacy returned None for this string"),
    ("arabic_indic_decimal", "٣٢٠٫٠٠",
     {0: 320.0, 2: 320.0, 3: 320.0}, {0: 320.0, 2: 320.0, 3: 320.0},
     "U+066B (Arabic decimal separator, x3 in the census) -> '.'"),
    ("arabic_indic_group", "١٬٢٣٤",
     {0: 1234.0, 2: 1234.0, 3: 1.234}, {0: 1234.0, 2: 1234.0, 3: 1.234},
     "U+066C (Arabic thousands separator) -> ',' then the normal comma rules"),
    ("extended_arabic_indic", "۱۲۳٫۵",
     {0: 123.5, 2: 123.5, 3: 123.5}, {0: 123.5, 2: 123.5, 3: 123.5},
     "U+06F0-06F9 (Persian/Urdu forms) -> ASCII"),
    ("bidi_wrapped", RLM + "320,00" + RLM, {0: 320.0, 2: 320.0, 3: 320.0},
     {0: 320.0, 2: 320.0, 3: 320.0},
     "U+200F right-to-left mark around an RTL shelf price - stripped"),

    # --- sign, junk, and the hostile magnitude ---
    ("negative", "-12,50", {0: -12.5, 2: -12.5, 3: -12.5},
     {0: -12.5, 2: -12.5, 3: -12.5}, "sign survives (the caller rejects <= 0)"),
    ("empty", "", {0: None, 2: None, 3: None}, {0: None, 2: None, 3: None},
     "nothing to parse"),
    ("prose", "no price here", {0: None, 2: None, 3: None},
     {0: None, 2: None, 3: None}, "no digits at all"),
    ("four_hundred_nines", "9" * 400, {0: None, 2: None, 3: None},
     {0: None, 2: None, 3: None},
     "float() returns inf with no exponent character in sight - BLOCKER 3 "
     "refuses it rather than shipping Infinity into json.dumps"),
]

assert len(SHAPES) == 51, len(SHAPES)


@pytest.mark.parametrize("code,minor", CURRENCIES, ids=[c for c, _ in CURRENCIES])
@pytest.mark.parametrize(
    "raw,display,machine,why",
    [(s[1], s[2], s[3], s[4]) for s in SHAPES],
    ids=[s[0] for s in SHAPES],
)
def test_grid_display_text(code, minor, raw, display, machine, why):
    """1122 display-mode cells: 22 currencies x 51 shapes."""
    expected = display[minor]
    got = parse_money(raw, code, display_text=True)
    if expected is None:
        assert got is None, why
    else:
        assert got == pytest.approx(expected), "%s [%s]: %s" % (raw, code, why)


@pytest.mark.parametrize("code,minor", CURRENCIES, ids=[c for c, _ in CURRENCIES])
@pytest.mark.parametrize(
    "raw,display,machine,why",
    [(s[1], s[2], s[3], s[4]) for s in SHAPES],
    ids=[s[0] for s in SHAPES],
)
def test_grid_machine_field(code, minor, raw, display, machine, why):
    """1122 machine-field cells (the DEFAULT mode)."""
    expected = machine[minor]
    got = parse_money(raw, code, display_text=False)
    if expected is None:
        assert got is None, why
    else:
        assert got == pytest.approx(expected), "%s [%s]: %s" % (raw, code, why)


def test_the_grid_really_covers_every_cell_it_claims():
    assert len(CURRENCIES) * len(SHAPES) == 1122
    assert len(CURRENCIES) == 22 and len(SHAPES) == 51


def test_the_two_modes_differ_on_exactly_one_shape_family():
    """The blast radius of ``display_text`` stated as an assertion, not prose:
    the ONLY shapes whose reading depends on the mode are a LONE DOT with a
    3-digit tail on a currency whose minor unit is 2."""
    differing = set()
    for _id, raw, display, machine, _why in SHAPES:
        for minor in (0, 2, 3):
            if display[minor] != machine[minor]:
                differing.add((_id, minor))
    assert {m for _i, m in differing} == {2}, differing
    assert {i for i, _m in differing} == {
        "dot_three_tail", "turkish_measured", "danish_measured",
        "three_thousand_dot", "sharafdg_bhd", "og_whitespace",
    }, differing


# ---------------------------------------------------------------------------
# 4. The named strings from the global validation, spelled out
# ---------------------------------------------------------------------------

class TestMeasuredCorpusStrings:
    def test_smartbuy_jordan(self):
        """The single hardest string: comma grouping + a 3-decimal fraction."""
        assert parse_money("1,799.000", "JOD", display_text=True) == pytest.approx(1799.0)
        assert parse_money("1,799.000 JOD", "JOD", display_text=True) == pytest.approx(1799.0)

    def test_turkish_thousands(self):
        assert parse_money("2.019 TL", "TRY", display_text=True) == pytest.approx(2019.0)

    def test_danish_thousands(self):
        assert parse_money("1.454 kr.", "DKK", display_text=True) == pytest.approx(1454.0)
        assert parse_money("1.454 kr.", "ISK", display_text=True) == pytest.approx(1454.0)

    def test_eu_south_decimal(self):
        assert parse_money("73,39 EUR", "EUR", display_text=True) == pytest.approx(73.39)
        assert parse_money("73,39", "EUR", display_text=True) == pytest.approx(73.39)

    @pytest.mark.parametrize("code", ZERO_DECIMAL)
    def test_zero_decimal_currencies_never_read_a_3_digit_tail_as_a_fraction(self, code):
        """The 12 silently-wrong 1000x-LOW reads: ``_currency_minor_unit`` could
        only answer 3 or 2, so a zero-decimal currency was handled by accident.
        Here it is handled on purpose, in BOTH modes."""
        assert parse_money("1.234", code, display_text=True) == pytest.approx(1234.0)
        assert parse_money("1.234", code, display_text=False) == pytest.approx(1234.0)
        assert parse_money("1,234", code, display_text=True) == pytest.approx(1234.0)
        assert parse_money("3.000", code, display_text=False) == pytest.approx(3000.0)

    def test_arabic_indic_price_strings(self):
        # "320,00" in Arabic-Indic digits with the Arabic decimal separator.
        assert parse_money("٣٢٠٫٠٠", "QAR") == pytest.approx(320.0)
        # A full RTL shelf string: RLM + digits + NBSP + the QAR glyph.
        raw = "‏٣٢٠٫٠٠ ر.ق"
        assert parse_money(raw, "QAR", display_text=True) == pytest.approx(320.0)

    @pytest.mark.parametrize("raw,legacy,fixed,why", [
        ("١٢٣٤", 1234.0, 1234.0,
         "float() accepts ANY Unicode Nd digit, so bare Arabic-Indic already "
         "worked - the fold changes nothing here"),
        ("٣٢٠٫٠٠", 320.0, 320.0,
         "legacy got this RIGHT by accident: float() fails on U+066B, and the "
         "fallback regex's first \d+ run happens to be the whole integer part"),
        ("۱۲۳٫۵", 123.0, 123.5,
         "the same accident TRUNCATES the fraction - 123 instead of 123.5"),
        ("١٬٢٣٤", 1.0, 1234.0,
         "U+066C stops the fallback regex after one digit - 1 instead of 1234"),
        ("‏320,00‏", 32000.0, 320.0,
         "the bidi-wrapped RTL form of BLOCKER 6 itself"),
        ("1 234,56", 1.0, 1234.56,
         "NBSP grouping (299 occurrences in the census) - 1 instead of 1234.56"),
    ], ids=["arabic_int", "arabic_decimal", "persian_decimal",
            "arabic_group", "bidi_wrapped", "nbsp_group"])
    def test_what_the_legacy_parser_actually_did_with_these(
        self, monkeypatch, raw, legacy, fixed, why,
    ):
        """Blast-radius framing, MEASURED rather than assumed. The legacy parser
        was not simply blind to these - it answered, and three of its six
        answers were silently wrong by 10x-1000x."""
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")
        assert parse_price_string(raw) == pytest.approx(legacy), why
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "true")
        assert parse_price_string(raw, "QAR", display_text=True) == pytest.approx(fixed), why


# ---------------------------------------------------------------------------
# 5. The minor-unit table
# ---------------------------------------------------------------------------

class TestMinorUnit:
    @pytest.mark.parametrize("code", THREE_DECIMAL)
    def test_three(self, code):
        assert _money_minor_unit(code) == 3

    @pytest.mark.parametrize("code", ZERO_DECIMAL)
    def test_zero(self, code):
        assert _money_minor_unit(code) == 0

    @pytest.mark.parametrize("code", TWO_DECIMAL)
    def test_two(self, code):
        assert _money_minor_unit(code) == 2

    @pytest.mark.parametrize("junk", [None, "", "   ", "ZZZ", 7, [], {}, True, 3.5])
    def test_unknown_falls_back_to_two_and_never_raises(self, junk):
        assert _money_minor_unit(junk) == 2

    def test_gcc_display_glyphs_resolve_to_their_iso_minor_unit(self):
        """The WooCommerce branch hands us the SYMBOL child's text, not an ISO
        code. Without this fold a Bahraini Woo store's "12,500" would read as
        12500 - a 1000x HIGH price on the exact code path BLOCKER 6 lives in."""
        assert _money_minor_unit(".د.ب") == 3       # BHD glyph
        assert _money_minor_unit("ر.ق") == 2        # QAR glyph
        assert parse_money("12,500", ".د.ب", display_text=True) == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# 6. Totality - a hostile input must never raise (BLOCKER 3 / 5 contract)
# ---------------------------------------------------------------------------

HOSTILE = [
    "1e400", "-1e400", "1e999999", "9" * 10000, "inf", "-inf", "Infinity",
    "nan", "NaN", "0x10", "1_000", "", "   ", None, [], {}, True, False,
    [{"deep": ["1e400"]}], 0, 1, -1, 3.5, float("inf"), float("nan"),
    10 ** 400, "-", ",", ".", ",,,", "...", "1,,2", "1..2", ",5", ".5",
]


def _hid(value):
    text = repr(value)
    return text if len(text) <= 24 else "%s...len%d" % (text[:16], len(text))


@pytest.mark.parametrize("hostile", HOSTILE, ids=_hid)
@pytest.mark.parametrize("currency", ["BHD", "USD", None, "", 7, [], {"a": 1}], ids=_hid)
@pytest.mark.parametrize("display", [True, False], ids=["display", "machine"])
def test_parse_money_is_total(hostile, currency, display):
    value = parse_money(hostile, currency, display_text=display)
    assert value is None or (isinstance(value, float) and math.isfinite(value))


@pytest.mark.parametrize("hostile", HOSTILE, ids=_hid)
@pytest.mark.parametrize("flag", ["true", "false"])
def test_parse_price_string_never_raises_in_either_flag_state(monkeypatch, hostile, flag):
    """Flag OFF is legacy, and legacy RAISES on a non-string (re.sub(TypeError)).
    Both states are pinned here: OFF is allowed to raise TypeError and nothing
    else, ON must be total. That asymmetry IS the pre-existing defect, and it is
    stated rather than hidden."""
    monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", flag)
    if flag == "true":
        value = parse_price_string(hostile)
        assert value is None or (isinstance(value, float) and math.isfinite(value))
    else:
        try:
            parse_price_string(hostile)
        except TypeError:
            pass


def test_infinite_magnitudes_are_refused_not_shipped(v2_on):
    for raw in ("9" * 400, "9" * 10000, "1" + "0" * 400, "1e400", "inf", "NaN"):
        assert parse_price_string(raw) is None or math.isfinite(parse_price_string(raw))


# ---------------------------------------------------------------------------
# 7. THE CALLERS - what must NOT move
# ---------------------------------------------------------------------------
#
# parse_price_string is called from 12 sites across three services. The DEFAULT
# mode (machine field, currency unknown) is the reading those un-threaded sites
# get, and it is chosen so their prices cannot move: a lone dot stays a decimal
# point exactly as ``float()`` read it, so the only readings this flag changes
# for them are the COMMA ones - which is the bug.

LEGACY_PINS = [
    ("$699.99", 699.99, "tests/test_error_paths.py pin - Serper US shopping"),
    ("BHD 339.000", 339.0, "tests/test_error_paths.py pin - a 3-decimal BHD price"),
    ("SAR 2,499", 2499.0, "tests/test_error_paths.py pin - a REAL thousands group"),
    ("1,082.00", 1082.0, "cached corpus - comma thousands"),
    ("1,200.00", 1200.0, "cached corpus - comma thousands"),
    ("34.00", 34.0, "a Shopify variant price - the commonest machine field"),
    ("1234.00", 1234.0, "a Shopify variant price with no grouping at all"),
    ("12.500", 12.5, "an ourshopee BHD display_price - machine mode keeps 12.5"),
    ("339.000", 339.0, "the pharmacy adapter's price field"),
    ("0.000", 0.0, "the pharmacy adapter's 'no offer' sentinel"),
    ("799", 799.0, "bare integer"),
    ("no price here", None, "prose"),
    ("", None, "empty"),
    (None, None, "None - the shape test_error_paths pins"),
]


@pytest.mark.parametrize("raw,expected,why", LEGACY_PINS, ids=[p[0] or "empty" for p in LEGACY_PINS])
def test_existing_callers_do_not_move(v2_on, raw, expected, why):
    got = parse_price_string(raw)
    if expected is None:
        assert got is None, why
    else:
        assert got == pytest.approx(expected), why


@pytest.mark.parametrize("raw,expected,why", LEGACY_PINS, ids=[p[0] or "empty" for p in LEGACY_PINS])
def test_those_pins_are_identical_with_the_flag_off(v2_off, raw, expected, why):
    """Not merely "unchanged from the spec" - IDENTICAL to today's code."""
    got = parse_price_string(raw)
    if expected is None:
        assert got is None, why
    else:
        assert got == pytest.approx(expected), why


class TestDisplayTextOptIn:
    """The two DISPLAY sites inside price_service that opt in, and the currency
    each of them threads. Everything else keeps the machine-field default."""

    def test_woocommerce_span_text_is_display_text(self, v2_on):
        # The symbol child is extracted before the parse, so the parser sees a
        # bare number and the currency arrives separately.
        assert parse_price_string("320,00", "QAR", display_text=True) == pytest.approx(320.0)
        assert parse_price_string("2.019", "TRY", display_text=True) == pytest.approx(2019.0)

    def test_serper_shopping_strings_are_display_text(self, v2_on):
        assert parse_price_string("SAR 2,499", "SAR", display_text=True) == pytest.approx(2499.0)
        assert parse_price_string("BHD 22,902", "BHD", display_text=True) == pytest.approx(22.902)
        assert parse_price_string("$1,234.56", "USD", display_text=True) == pytest.approx(1234.56)

    def test_a_woo_bahraini_store_is_not_1000x(self, v2_on):
        """The dangerous direction. Without the currency thread this reads
        12500 - and 12.500 BHD is a real, common shelf price."""
        assert parse_price_string("12,500", "BHD", display_text=True) == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# 8. The OpenGraph parser - one parser now, same answers
# ---------------------------------------------------------------------------
#
# _parse_og_price_number's resolution table is pinned cell-by-cell in
# tests/test_og_branch_fixes.py. Routing it through parse_money must not move a
# single one of those cells, in EITHER flag state - that is what makes this
# "one canonical parser" rather than "a second parser with a new opinion".

OG_TABLE = [
    ("279,00", None, 279.00), ("195,00", None, 195.00), ("403,75", None, 403.75),
    ("1.234,56", None, 1234.56), ("1,234.56", None, 1234.56),
    ("1,234", None, 1234.0), ("3.000", None, 3.0),
    ("1,082.00", None, 1082.00), ("1,200.00", None, 1200.00),
    ("1,234,567", None, 1234567.0), ("24,00", None, 24.0),
    ("244.990", None, 244.990), ("32.505", None, 32.505), ("799", None, 799.0),
    ("  59.900  ", None, 59.900), ("BHD 279,00", None, 279.00),
    ("1.234.567,89", None, 1234567.89),
    ("22,902", "BHD", 22.902), ("22,902", "OMR", 22.902), ("22,902", "KWD", 22.902),
    ("22,902", "SAR", 22902.0), ("22,902", "USD", 22902.0), ("22,902", "EUR", 22902.0),
    ("22,902", None, 22902.0), ("22,902", "", 22902.0), ("22,902", "ZZZ", 22902.0),
    ("1,234", "BHD", 1.234), ("1,234", "USD", 1234.0),
    ("0,500", "BHD", 0.5), ("0,500", "USD", 0.5), ("00,500", "USD", 0.5),
    ("22.902", None, 22.902), ("22.902", "BHD", 22.902),
    ("3.000", "SAR", 3.0), ("3.000", "EUR", 3.0), ("3.000", "USD", 3.0),
    ("3.000", "BHD", 3.0), ("0.610", "EUR", 0.610), ("2.110", "USD", 2.110),
    ("20.10", "USD", 20.10), ("62.000", "SAR", 62.0),
]


@pytest.mark.parametrize("flag", ["true", "false"])
@pytest.mark.parametrize("raw,code,expected", OG_TABLE,
                         ids=["%s|%s" % (r.strip(), c) for r, c, _ in OG_TABLE])
def test_og_table_is_flag_invariant(monkeypatch, flag, raw, code, expected):
    monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", flag)
    assert _parse_og_price_number(raw, code) == pytest.approx(expected)


@pytest.mark.parametrize("flag", ["true", "false"])
@pytest.mark.parametrize("raw", ["", "   ", "on request", "abc", None, "-", ","])
def test_og_unparseable_is_flag_invariant(monkeypatch, flag, raw):
    monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", flag)
    assert _parse_og_price_number(raw) is None


@pytest.mark.parametrize("raw", ["3.000", "244.990", "62.000", "0.610", "799",
                                 "2.110", "20.10"])
def test_og_dot_only_still_matches_legacy_float(v2_on, raw):
    """The blast-radius proof the OG wave shipped, re-run through the new
    parser: a lone dot in a MACHINE field is still exactly float()."""
    assert _parse_og_price_number(raw) == pytest.approx(float(raw))


def test_og_gains_the_new_normalisations(v2_on):
    """What routing OG through the canonical parser BUYS: an RTL/Arabic-Indic
    or NBSP-grouped og:price:amount used to return None or a wrong number."""
    assert _parse_og_price_number("٣٢٠٫٠٠", "QAR") == pytest.approx(320.0)
    assert _parse_og_price_number("1 234,56", "EUR") == pytest.approx(1234.56)

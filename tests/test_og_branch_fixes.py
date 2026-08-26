"""Two OpenGraph-branch correctness defects - `ENABLE_OG_BRANCH_FIXES`.

`extract_price_from_html`'s OpenGraph fallback (price_service.py, Priority 2)
shipped two defects, both found by running the 92 cached fragrance PDPs in
``_proof/html/`` through the production extractor:

(a) **`in_stock` was hardcoded `True`.** The dict literal asserted stock with
    ZERO signal on the page. Measured: 3 of the 4 live Shopify targets have
    zero available variants while production reported them in stock. The OG
    namespace *does* carry a signal - ``product:availability`` appears on 20 of
    the 92 cached pages (14 "in stock", 5 "instock", 1 "out of stock") and
    ``og:availability`` on 1 more - so the branch now reads it through the same
    tri-state ``is_available_state`` the JSON-LD path uses, and emits **None**
    (unknown) when no tag exists. Never `True` by default.

(b) **`float(og_price['content'])` raised on a comma decimal.** Measured in the
    cached corpus: ``leperfumeqa`` "279,00", ``fyzara`` "195,00", ``mhgboutique``
    "403,75" - three real PDPs whose OG price production could not parse at all.
    ``parse_price_string`` is NOT usable here: it strips commas unconditionally
    (price_service.py:2835) and turns "24,00" into **2400.0** (pinned by
    ``test_parse_price_string_is_the_trap_we_avoid`` below). A local
    ``_parse_og_price_number`` distinguishes a comma DECIMAL separator from a
    comma THOUSANDS separator instead.

A third change, "(c)", once rode this flag: it moved the OG branch from Priority
2 down below microdata and the WooCommerce span. It is REVERTED - measured over
the same 92 cached pages it produced zero improvements and four regressions (see
``tests/test_og_cascade_position.py``, which now pins the OG branch's position
and owns every cascade-order assertion). The two microdata changes that rode
this flag as declared preconditions of (c) went with it. This file is therefore
about ``_extract_og_price``'s TAG READING only; nothing here may assert cascade
order.

Both remaining defects sit behind ONE flag, ``ENABLE_OG_BRANCH_FIXES``, default
ON, read per call from ``os.getenv``. Every behaviour below is asserted in BOTH
flag states: flag OFF must reproduce the exact legacy result.

No network, no fixtures on disk - synthetic meta-tag fragments only.
"""

import pytest

from app.services.price_service import (
    _parse_og_price_number,
    extract_price_from_html,
    og_branch_fixes_enabled,
    parse_price_string,
)

QUERY = "Oud Elite So Black Eau de Parfum 100ml"
DOMAIN = "bh.oudelite.com"
URL = "https://bh.oudelite.com/product/so-black"


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "true")
    return True


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "false")
    return False


def _og_html(amount, currency="BHD", availability=None, avail_prop="product:availability"):
    """Minimal OG head. No og:title / <title> so `_page_identity_ok` sees no
    identity signal and stays out of the way - these assertions isolate the OG
    branch itself."""
    parts = ["<html><head>"]
    if amount is not None:
        parts.append(f'<meta property="og:price:amount" content="{amount}">')
        parts.append(f'<meta property="og:price:currency" content="{currency}">')
    if availability is not None:
        parts.append(f'<meta property="{avail_prop}" content="{availability}">')
    parts.append("</head><body></body></html>")
    return "".join(parts)


def _extract(html, currency="BHD", domain=DOMAIN):
    return extract_price_from_html(html, QUERY, currency, domain, URL)


# ---------------------------------------------------------------------------
# The flag helper itself
# ---------------------------------------------------------------------------


class TestFlagHelper:
    def test_defaults_on(self, monkeypatch):
        monkeypatch.delenv("ENABLE_OG_BRANCH_FIXES", raising=False)
        assert og_branch_fixes_enabled() is True

    @pytest.mark.parametrize("raw", ["false", "0", "no", "off", "", "  OFF  "])
    def test_off_words(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", raw)
        assert og_branch_fixes_enabled() is False

    @pytest.mark.parametrize("raw", ["true", "1", "yes", "on", "TRUE"])
    def test_on_words(self, monkeypatch, raw):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", raw)
        assert og_branch_fixes_enabled() is True

    def test_read_per_call_never_cached_at_import(self, monkeypatch):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "false")
        assert og_branch_fixes_enabled() is False
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", "true")
        assert og_branch_fixes_enabled() is True


# ---------------------------------------------------------------------------
# (b) the numeric parser - comma DECIMAL vs comma THOUSANDS
# ---------------------------------------------------------------------------

# (raw content, expected float, why)
NUMERIC_SHAPES = [
    # --- the three REAL comma-decimal pages measured in _proof/html/ ---
    ("279,00", 279.00, "leperfumeqa.com - comma decimal (measured)"),
    ("195,00", 195.00, "fyzara.com - comma decimal (measured)"),
    ("403,75", 403.75, "mhgboutique.com - comma decimal (measured)"),
    # --- the four shapes the spec names explicitly ---
    ("1.234,56", 1234.56, "dot thousands + comma decimal -> comma is decimal"),
    ("1,234.56", 1234.56, "comma thousands + dot decimal -> comma is thousands"),
    ("1,234", 1234.0, "lone comma with a 3-digit tail -> thousands group"),
    ("3.000", 3.0, "AMBIGUOUS - pinned as a DECIMAL point, see the test below"),
    # --- two more real comma-THOUSANDS amounts out of the cached corpus ---
    ("1,082.00", 1082.00, "cached corpus - comma thousands"),
    ("1,200.00", 1200.00, "cached corpus - comma thousands"),
    # --- the rest ---
    ("1,234,567", 1234567.0, "multi-group comma thousands"),
    ("24,00", 24.0, "the parse_price_string trap - it returns 2400.0"),
    ("244.990", 244.990, "bahrain.sharafdg.com 3-decimal BHD (measured)"),
    ("32.505", 32.505, "reefperfumes.com 3-decimal BHD (measured)"),
    ("799", 799.0, "bare integer"),
    ("  59.900  ", 59.900, "surrounding whitespace"),
    ("BHD 279,00", 279.00, "currency-code prefix + comma decimal"),
    ("1.234.567,89", 1234567.89, "multi-group dot thousands + comma decimal"),
]

UNPARSEABLE = ["", "   ", "on request", "abc", None, "-", ","]


class TestOgNumericParser:
    @pytest.mark.parametrize(
        "raw,expected,why", NUMERIC_SHAPES, ids=[s[0].strip() for s in NUMERIC_SHAPES]
    )
    def test_shape(self, raw, expected, why):
        assert _parse_og_price_number(raw) == pytest.approx(expected), why

    @pytest.mark.parametrize("raw", UNPARSEABLE)
    def test_unparseable_returns_none(self, raw):
        assert _parse_og_price_number(raw) is None

    def test_parse_price_string_is_the_trap_we_avoid(self, monkeypatch):
        """WHY the helper was local: the shared parser stripped commas
        unconditionally and turned a 24,00 shelf price into 2400.0.

        That trap is GONE as of BLOCKER 6 - ``parse_price_string`` now routes
        through the same canonical parser, so the two agree. The legacy reading
        survives only as the ENABLE_MONEY_PARSER_V2 rollback, pinned here so the
        rollback contract stays visible from this file too."""
        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "false")
        assert parse_price_string("24,00") == pytest.approx(2400.0)
        assert _parse_og_price_number("24,00") == pytest.approx(24.0)

        monkeypatch.setenv("ENABLE_MONEY_PARSER_V2", "true")
        assert parse_price_string("24,00") == pytest.approx(24.0)
        assert _parse_og_price_number("24,00") == pytest.approx(24.0)

    def test_three_thousand_resolves_as_three_point_zero(self):
        """"3.000" is genuinely ambiguous: 3.000 BHD (a 3-decimal GCC currency)
        or three thousand. It is pinned to 3.0 - a lone dot is ALWAYS a decimal
        point - for two reasons:

        1. og:price:amount is specified as a plain decimal number, and the
           3-decimal GCC currencies (BHD/OMR/KWD) legitimately publish
           "244.990" / "3.000"; the cached corpus is full of them.
        2. `float("3.000")` is 3.0, i.e. EXACTLY what the pre-change code
           produced. Resolving the ambiguity this way means the helper only ever
           changes the outcome for input the old code could not parse at all,
           which keeps the blast radius of the flag at zero for dot-only prices.
        """
        assert _parse_og_price_number("3.000") == pytest.approx(3.0)
        assert _parse_og_price_number("3.000") == float("3.000")

    def test_every_dot_only_shape_matches_legacy_float(self):
        """Blast-radius proof for the ruling above."""
        for raw in ("3.000", "244.990", "62.000", "0.610", "799", "2.110", "20.10"):
            assert _parse_og_price_number(raw) == pytest.approx(float(raw))

    def test_a_three_digit_comma_tail_is_thousands_when_the_CURRENCY_IS_UNKNOWN(self):
        """The shape-only fallback, kept as the default for a currency-LESS call.

        A lone comma with a 3-digit tail cannot be told from a thousands group by
        shape alone, so with no currency to consult the parser keeps the legacy
        reading: "22,902" -> 22902.0. That default is safe ONLY because the
        production call sites always pass a currency (see
        ``TestCurrencyMinorUnitTieBreak`` below, and the end-to-end tests); it is
        the tie-break of last resort, not the tie-break we ship."""
        assert _parse_og_price_number("22,902") == pytest.approx(22902.0)
        assert _parse_og_price_number("22,902", None) == pytest.approx(22902.0)
        assert _parse_og_price_number("22,902", "") == pytest.approx(22902.0)
        assert _parse_og_price_number("22,902", "ZZZ") == pytest.approx(22902.0)
        # A dot tail is never in doubt, with or without a currency.
        assert _parse_og_price_number("22.902") == pytest.approx(22.902)
        assert _parse_og_price_number("22.902", "BHD") == pytest.approx(22.902)


# ---------------------------------------------------------------------------
# (b2) BLOCKER 2 - the comma tie-break is settled by the CURRENCY MINOR UNIT
# ---------------------------------------------------------------------------
#
# The shape-only rule above ("a 3-digit tail is a thousands group") is WRONG for
# the 3-decimal currencies, and it shipped. Reproduced through the real
# `extract_price_from_html` on a minimal OG-only page:
#
#     og:price:amount="0,500"  BHD -> 500.0    (should be 0.500)   1000x
#     og:price:amount="22,902" BHD -> 22902.0  (should be 22.902)  1000x
#     og:price:amount="60,660" OMR -> 60660.0  (should be 60.660)  1000x
#     og:price:amount="279,00" QAR -> 279.0    (correct - 2 decimals)
#
# The only downstream guard is `amount > 0`, so a 1000x over-price ships.
# Blast radius measured on _proof/sweep2_curl_cffi.jsonl: 27 of the 92 cached
# domains declare a page_currency of BHD/OMR/KWD outright (BHD 15, OMR 9, KWD 3)
# and 5 more of the 15 currency-less rows are GCC 3-decimal hosts by name
# (en-kwt.ajmal.com, bawwaba.om, capitalstoreoman.com, kwt.nazih.com,
# bloomingdales.com.kw) - so 27 certain, 32 upper bound, roughly a third of the
# corpus. Both amounts above are REAL: reefperfumes.com ships
# `product:sale_price:amount` = "22.902" BHD and bh.taifalemarat.com is a BHD
# storefront - today they happen to write the decimal with a DOT, which is why
# the corpus has no live victim yet. The moment either locale-formats with a
# comma, the price ships 1000x high with nothing downstream to catch it.
#
# THE RULE. Settle the ambiguity with the currency's ISO 4217 minor unit, not
# with the tail length:
#   1. A head that is "0" or carries a leading zero can NEVER be a thousands
#      group - "0,500" is unambiguous. Checked FIRST, before any currency.
#   2. More than one comma -> thousands groups ("1,234,567"); a string with two
#      commas has no single-decimal reading at all.
#   3. A tail that is not 3 digits long -> decimal ("279,00", "1,5").
#   4. A 3-digit tail -> DECIMAL for a 3-decimal currency, THOUSANDS otherwise.
# Rules 1-3 are currency-independent; only rule 4 consults the minor unit.

# ISO 4217 minor unit 3. All seven are in the extractor's constant.
THREE_DECIMAL = ["BHD", "OMR", "KWD", "JOD", "TND", "LYD", "IQD"]

# (currency, raw content, expected float, why - one line per cell)
MINOR_UNIT_MATRIX = [
    # --- BHD (minor unit 3) ---
    ("BHD", "0,500",    0.500,   "leading-zero head is never a thousands group - unambiguous 0.500 BHD"),
    ("BHD", "22,902",   22.902,  "the real reefperfumes.com BHD amount, comma-formatted - minor unit 3 -> decimal"),
    ("BHD", "60,660",   60.660,  "3-digit tail on a 3-decimal currency -> decimal"),
    ("BHD", "1,234",    1.234,   "UNDECIDABLE by shape (1.234 vs 1234 BHD); minor unit 3 pins the decimal, same as 22,902"),
    ("BHD", "1,234.56", 1234.56, "two separators - the RIGHTMOST is the decimal; currency never consulted"),
    ("BHD", "1.234,56", 1234.56, "two separators - the RIGHTMOST is the decimal; currency never consulted"),
    ("BHD", "279,00",   279.00,  "a 2-digit tail is a decimal on every currency - a thousands group is always 3 digits"),
    ("BHD", "3.000",    3.0,     "dot-only is ALWAYS a decimal point (unchanged ruling) and already right for 3.000 BHD"),
    ("BHD", "1,5",      1.5,     "a 1-digit tail cannot be a thousands group"),
    # --- OMR (minor unit 3) ---
    ("OMR", "0,500",    0.500,   "leading-zero head is never a thousands group - 0.500 OMR"),
    ("OMR", "22,902",   22.902,  "3-digit tail on a 3-decimal currency -> decimal"),
    ("OMR", "60,660",   60.660,  "the real bh.taifalemarat/OMR-shaped shelf price, comma-formatted -> 60.660"),
    ("OMR", "1,234",    1.234,   "UNDECIDABLE by shape; minor unit 3 pins the decimal"),
    ("OMR", "1,234.56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("OMR", "1.234,56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("OMR", "279,00",   279.00,  "2-digit tail -> decimal on every currency"),
    ("OMR", "3.000",    3.0,     "dot-only -> decimal point, 3.000 OMR"),
    ("OMR", "1,5",      1.5,     "1-digit tail -> decimal"),
    # --- KWD (minor unit 3) ---
    ("KWD", "0,500",    0.500,   "leading-zero head is never a thousands group - 0.500 KWD"),
    ("KWD", "22,902",   22.902,  "3-digit tail on a 3-decimal currency -> decimal"),
    ("KWD", "60,660",   60.660,  "3-digit tail on a 3-decimal currency -> decimal"),
    ("KWD", "1,234",    1.234,   "UNDECIDABLE by shape; minor unit 3 pins the decimal"),
    ("KWD", "1,234.56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("KWD", "1.234,56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("KWD", "279,00",   279.00,  "2-digit tail -> decimal on every currency"),
    ("KWD", "3.000",    3.0,     "dot-only -> decimal point, 3.000 KWD"),
    ("KWD", "1,5",      1.5,     "1-digit tail -> decimal"),
    # --- SAR (minor unit 2) ---
    ("SAR", "0,500",    0.500,   "leading-zero head is never a thousands group - 0.5 SAR, NOT 500, even at minor unit 2"),
    ("SAR", "22,902",   22902.0, "3-digit tail on a 2-decimal currency -> thousands group (legacy reading, still right)"),
    ("SAR", "60,660",   60660.0, "3-digit tail on a 2-decimal currency -> thousands group"),
    ("SAR", "1,234",    1234.0,  "the canonical thousands group - minor unit 2 keeps it"),
    ("SAR", "1,234.56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("SAR", "1.234,56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("SAR", "279,00",   279.00,  "2-digit tail -> decimal (a real Salla/QAR-style shape)"),
    ("SAR", "3.000",    3.0,     "dot-only -> decimal point; matches legacy float('3.000')"),
    ("SAR", "1,5",      1.5,     "1-digit tail -> decimal"),
    # --- AED (minor unit 2) ---
    ("AED", "0,500",    0.500,   "leading-zero head is never a thousands group - 0.5 AED"),
    ("AED", "22,902",   22902.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("AED", "60,660",   60660.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("AED", "1,234",    1234.0,  "canonical thousands group; beautiquefragrances/touchofoud really do ship 1,082.00 AED"),
    ("AED", "1,234.56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("AED", "1.234,56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("AED", "279,00",   279.00,  "2-digit tail -> decimal; mhgboutique.com ships 403,75 on an AED page"),
    ("AED", "3.000",    3.0,     "dot-only -> decimal point"),
    ("AED", "1,5",      1.5,     "1-digit tail -> decimal"),
    # --- QAR (minor unit 2) ---
    ("QAR", "0,500",    0.500,   "leading-zero head is never a thousands group - 0.5 QAR"),
    ("QAR", "22,902",   22902.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("QAR", "60,660",   60660.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("QAR", "1,234",    1234.0,  "canonical thousands group"),
    ("QAR", "1,234.56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("QAR", "1.234,56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("QAR", "279,00",   279.00,  "the real leperfumeqa.com QAR shelf price - the cell the lead confirmed correct"),
    ("QAR", "3.000",    3.0,     "dot-only -> decimal point"),
    ("QAR", "1,5",      1.5,     "1-digit tail -> decimal"),
    # --- USD (minor unit 2) ---
    ("USD", "0,500",    0.500,   "leading-zero head is never a thousands group - $0.50"),
    ("USD", "22,902",   22902.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("USD", "60,660",   60660.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("USD", "1,234",    1234.0,  "canonical en-US thousands group"),
    ("USD", "1,234.56", 1234.56, "the en-US shape - comma groups, dot decimates"),
    ("USD", "1.234,56", 1234.56, "the de-DE shape on a USD page - rightmost separator still wins"),
    ("USD", "279,00",   279.00,  "2-digit tail -> decimal even on USD; a thousands group is always 3 digits"),
    ("USD", "3.000",    3.0,     "dot-only -> decimal point; matches legacy float('3.000')"),
    ("USD", "1,5",      1.5,     "1-digit tail -> decimal"),
    # --- EUR (minor unit 2) ---
    ("EUR", "0,500",    0.500,   "leading-zero head is never a thousands group - 0.50 EUR"),
    ("EUR", "22,902",   22902.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("EUR", "60,660",   60660.0, "3-digit tail, minor unit 2 -> thousands group"),
    ("EUR", "1,234",    1234.0,  "UNDECIDABLE in a de-DE locale (1.234 EUR is legal there); minor unit 2 pins thousands, the legacy reading"),
    ("EUR", "1,234.56", 1234.56, "two separators - rightmost wins, currency-independent"),
    ("EUR", "1.234,56", 1234.56, "the canonical de-DE shape"),
    ("EUR", "279,00",   279.00,  "the canonical de-DE decimal comma"),
    ("EUR", "3.000",    3.0,     "UNDECIDABLE in de-DE (3.000 EUR means three thousand there); pinned to the safe legacy float('3.000') = 3.0"),
    ("EUR", "1,5",      1.5,     "1-digit tail -> decimal"),
]


class TestCurrencyMinorUnitTieBreak:
    """Every cell of {BHD,OMR,KWD,SAR,AED,QAR,USD,EUR} x nine comma/dot shapes."""

    @pytest.mark.parametrize(
        "code,raw,expected,why",
        MINOR_UNIT_MATRIX,
        ids=[f"{c}-{r}" for c, r, _e, _w in MINOR_UNIT_MATRIX],
    )
    def test_cell(self, code, raw, expected, why):
        assert _parse_og_price_number(raw, code) == pytest.approx(expected), why

    @pytest.mark.parametrize("code", THREE_DECIMAL)
    def test_all_seven_iso_minor_unit_3_currencies(self, code):
        """JOD/TND/LYD/IQD are 3-decimal too, not just the three GCC ones the
        corpus happens to contain - the constant must carry all seven."""
        assert _parse_og_price_number("22,902", code) == pytest.approx(22.902)
        assert _parse_og_price_number("1,234", code) == pytest.approx(1.234)

    @pytest.mark.parametrize("code", ["bhd", "  BHD  ", "Bhd", "\tomr\n"])
    def test_currency_code_is_case_and_whitespace_insensitive(self, code):
        """og:price:currency is page-authored - never trust its casing."""
        assert _parse_og_price_number("22,902", code) == pytest.approx(22.902)

    @pytest.mark.parametrize("code", [None, "", "   ", "ZZZ", "BH", "BHDD", 0])
    def test_unknown_currency_falls_back_to_the_2_decimal_reading(self, code):
        """No currency, or one we cannot recognise -> keep the legacy shape-only
        answer. Never guess 3-decimal: guessing wrong there under-prices 1000x,
        which the `amount > 0` guard would not catch either."""
        assert _parse_og_price_number("22,902", code) == pytest.approx(22902.0)

    def test_rule_1_beats_the_currency_on_a_2_decimal_page(self):
        """The leading-zero rule is checked FIRST and is currency-independent -
        "0,500" can never be five hundred, whatever the minor unit."""
        for code in ("SAR", "AED", "QAR", "USD", "EUR", "BHD", None):
            assert _parse_og_price_number("0,500", code) == pytest.approx(0.5)
        assert _parse_og_price_number("00,500", "USD") == pytest.approx(0.5)

    def test_a_multi_comma_string_is_always_thousands_groups(self):
        """Two commas have no single-decimal reading - rule 2, currency and
        leading zero alike are irrelevant."""
        for code in ("BHD", "OMR", "USD", None):
            assert _parse_og_price_number("1,234,567", code) == pytest.approx(1234567.0)

    def test_the_currency_argument_is_optional_and_defaults_to_legacy(self):
        """Every pre-existing caller and test calls with one argument."""
        for raw, expected in (("279,00", 279.0), ("1,234", 1234.0), ("3.000", 3.0)):
            assert _parse_og_price_number(raw) == pytest.approx(expected)
            assert _parse_og_price_number(raw) == _parse_og_price_number(raw, None)

    def test_dot_only_shapes_are_never_touched_by_the_currency(self):
        """Blast-radius proof: adding the currency argument moves NOTHING that
        the old code could already parse - a lone dot stays a decimal point and
        keeps matching legacy float()."""
        for raw in ("3.000", "244.990", "62.000", "0.610", "799", "2.110", "20.10"):
            for code in (None, "BHD", "OMR", "KWD", "SAR", "AED", "USD"):
                assert _parse_og_price_number(raw, code) == pytest.approx(float(raw))


class TestMinorUnitTieBreakEndToEnd:
    """The lead's four reproductions, through the REAL extract_price_from_html."""

    @pytest.mark.parametrize(
        "raw,code,expected,why",
        [
            ("0,500", "BHD", 0.500, "was 500.0 - 1000x"),
            ("22,902", "BHD", 22.902, "was 22902.0 - the real reefperfumes amount"),
            ("60,660", "OMR", 60.660, "was 60660.0 - a real taifalemarat-shaped amount"),
            ("279,00", "QAR", 279.00, "was already correct - must stay correct"),
        ],
    )
    def test_repro(self, flag_on, raw, code, expected, why):
        res = _extract(_og_html(raw, code), code, DOMAIN)
        assert res is not None
        assert res["amount"] == pytest.approx(expected), why
        assert res["currency"] == code

    @pytest.mark.parametrize("raw", ["0,500", "22,902", "60,660", "279,00"])
    def test_flag_off_drops_every_one_of_them(self, flag_off, raw):
        """Rollback is byte-identical: legacy float() raises on all four, the OG
        branch is skipped, and an OG-only page extracts to None."""
        assert _extract(_og_html(raw, "BHD"), "BHD", DOMAIN) is None

    def test_a_currencyless_og_price_uses_the_EXPECTED_currency_minor_unit(self):
        """bahrain.sharafdg.com ships product:price:amount with NO currency tag on
        a BHD page. The branch already falls back to the expected currency for the
        LABEL; the tie-break must read that same fallback, not default to 2."""
        html = (
            "<html><head>"
            '<meta property="og:price:amount" content="22,902">'
            "</head><body></body></html>"
        )
        res = _extract(html, "BHD", "bahrain.sharafdg.com")
        assert res is not None
        assert res["amount"] == pytest.approx(22.902)
        assert res["currency"] == "BHD"

    def test_the_PAGE_currency_wins_over_the_expected_currency(self):
        """A SAR-tagged price on a BHD-expected page is 22902 SAR (then converted),
        NOT 22.902 - the tie-break must use the DECLARED currency, the same one
        the amount is labelled with."""
        res = _extract(_og_html("22,902", "SAR"), "BHD", DOMAIN)
        assert res is not None
        assert res["original_currency"] == "SAR"
        # converted out of SAR, so compare against the pre-conversion magnitude
        assert res["amount"] > 1000, "22902 SAR must not have been read as 22.902"

    def test_the_sale_tag_probe_uses_the_sale_tags_own_currency(self):
        """reefperfumes.com ships the shelf price on `product:sale_price:amount`.
        The ENABLE_SALE_PRICE_FIRST usability probe parses that tag too, so it must
        parse it under the same currency the consumer will."""
        html = (
            "<html><head>"
            '<meta property="product:sale_price:amount" content="22,902">'
            '<meta property="product:sale_price:currency" content="BHD">'
            '<meta property="product:price:amount" content="45.000">'
            '<meta property="product:price:currency" content="BHD">'
            "</head><body></body></html>"
        )
        res = _extract(html, "BHD", "reefperfumes.com")
        assert res is not None
        assert res["amount"] == pytest.approx(22.902)
        assert res["currency"] == "BHD"

    def test_a_currencyless_sale_tag_inherits_the_list_prices_currency(self):
        """No product:sale_price:currency -> the branch already falls back to the
        LIST price's currency tag for the label; the tie-break must follow it."""
        html = (
            "<html><head>"
            '<meta property="product:sale_price:amount" content="22,902">'
            '<meta property="product:price:amount" content="45.000">'
            '<meta property="product:price:currency" content="BHD">'
            "</head><body></body></html>"
        )
        res = _extract(html, "BHD", "reefperfumes.com")
        assert res is not None
        assert res["amount"] == pytest.approx(22.902)

    def test_a_2_decimal_thousands_price_is_still_not_divided(self, flag_on):
        """The failure mode the fix must NOT introduce in the other direction:
        a genuine 1,082 AED must stay 1082.0, never 1.082."""
        res = _extract(_og_html("1,082", "AED"), "AED", "touchofoud.com")
        assert res is not None
        assert res["amount"] == pytest.approx(1082.0)


class TestCommaDecimalEndToEnd:
    """The three real pages, through the production extractor."""

    @pytest.mark.parametrize(
        "raw,expected,domain",
        [
            ("279,00", 279.00, "leperfumeqa.com"),
            ("195,00", 195.00, "fyzara.com"),
            ("403,75", 403.75, "mhgboutique.com"),
        ],
    )
    def test_flag_on_parses(self, flag_on, raw, expected, domain):
        res = _extract(_og_html(raw, "QAR"), "QAR", domain)
        assert res is not None
        assert res["amount"] == pytest.approx(expected)
        assert res["currency"] == "QAR"

    @pytest.mark.parametrize("raw", ["279,00", "195,00", "403,75"])
    def test_flag_off_still_drops_them(self, flag_off, raw):
        """Legacy: float("279,00") raises, the OG branch is skipped, and with no
        microdata / Woo on the page the whole extraction returns None."""
        assert _extract(_og_html(raw, "QAR"), "QAR", "leperfumeqa.com") is None

    def test_comma_thousands_is_not_multiplied(self, flag_on):
        """The failure mode we must NOT introduce: 1,082.00 -> 1082.0, never
        108200.0."""
        res = _extract(_og_html("1,082.00", "SAR"), "SAR", "3saf.com")
        assert res is not None
        assert res["amount"] == pytest.approx(1082.00)

    def test_comma_decimal_sale_tag_is_usable(self, flag_on, monkeypatch):
        """The Salla sale-price gate (ENABLE_SALE_PRICE_FIRST) tested a sale tag
        with float() too - a comma-decimal sale tag was rejected as junk and the
        LIST price shipped. It must now be accepted."""
        monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
        html = (
            "<html><head>"
            '<meta property="product:sale_price:amount" content="79,99">'
            '<meta property="product:sale_price:currency" content="SAR">'
            '<meta property="product:price:amount" content="129">'
            '<meta property="product:price:currency" content="SAR">'
            "</head><body></body></html>"
        )
        res = _extract(html, "SAR", "rend-bahrain.com")
        assert res is not None
        assert res["amount"] == pytest.approx(79.99)

    def test_junk_sale_tag_still_falls_through_to_the_list_price(self, flag_on, monkeypatch):
        monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
        html = (
            "<html><head>"
            '<meta property="product:sale_price:amount" content="on request">'
            '<meta property="product:price:amount" content="129">'
            '<meta property="product:price:currency" content="SAR">'
            "</head><body></body></html>"
        )
        res = _extract(html, "SAR", "rend-bahrain.com")
        assert res is not None
        assert res["amount"] == pytest.approx(129.0)


# ---------------------------------------------------------------------------
# (a) in_stock - real signal or None, NEVER a hardcoded True
# ---------------------------------------------------------------------------


class TestOgAvailability:
    def test_no_availability_tag_is_none_not_true(self, flag_on):
        """THE defect. No signal on the page -> in_stock is None (unknown)."""
        res = _extract(_og_html("23"))
        assert res is not None
        assert res["in_stock"] is None
        assert res["in_stock"] is not True

    def test_flag_off_reproduces_the_hardcoded_true(self, flag_off):
        res = _extract(_og_html("23"))
        assert res is not None
        assert res["in_stock"] is True

    @pytest.mark.parametrize(
        "raw,prop",
        [
            ("in stock", "product:availability"),     # 14 cached pages
            ("instock", "product:availability"),      # 5 cached pages
            ("instock", "og:availability"),           # 1 cached page
            ("InStock", "product:availability"),
            ("https://schema.org/InStock", "product:availability"),
        ],
    )
    def test_in_stock_signal_is_true(self, flag_on, raw, prop):
        res = _extract(_og_html("23", availability=raw, avail_prop=prop))
        assert res is not None
        assert res["in_stock"] is True

    @pytest.mark.parametrize(
        "raw",
        [
            "out of stock",                       # 1 cached page
            "outofstock",
            "OutOfStock",
            "https://schema.org/OutOfStock",
            "sold out",
            "Discontinued",
            "PreOrder",
        ],
    )
    def test_out_of_stock_signal_is_false(self, flag_on, raw):
        res = _extract(_og_html("23", availability=raw))
        assert res is not None
        assert res["in_stock"] is False

    def test_unrecognised_availability_word_is_none(self, flag_on):
        """An availability tag we cannot classify is UNKNOWN, not in stock."""
        res = _extract(_og_html("23", availability="ask the shop"))
        assert res is not None
        assert res["in_stock"] is None

    def test_flag_off_ignores_a_real_out_of_stock_tag(self, flag_off):
        """Byte-identity proof in the direction that hurts: legacy shipped True
        even with an explicit out-of-stock tag on the page."""
        res = _extract(_og_html("23", availability="out of stock"))
        assert res is not None
        assert res["in_stock"] is True

    def test_availability_does_not_disturb_the_amount(self, flag_on):
        res = _extract(_og_html("23", availability="out of stock"))
        assert res["amount"] == pytest.approx(23.0)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape"
        assert res["confidence"] == 0.9


# ---------------------------------------------------------------------------
# The OG branch's cascade POSITION is not this flag's business any more.
#
# The reverted "(c)" change gated it on this flag; the position is now
# unconditional at Priority 2 and every order assertion lives in
# tests/test_og_cascade_position.py. The two tests kept here are the ones that
# were always about the OG branch itself: it must behave identically in both
# flag states on a page where nothing else competes, and it must never outrank
# JSON-LD.
# ---------------------------------------------------------------------------


class TestOgBranchPositionIsFlagInvariant:
    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_og_only_page_is_unaffected_by_the_flag(self, monkeypatch, flag):
        """72 of the 92 cached pages carry an OG price. On a page where OG is
        the only structured source the flag must not move the amount at all."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        res = _extract(_og_html("23"))
        assert res is not None
        assert res["amount"] == pytest.approx(23.0)

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_jsonld_still_wins_over_og(self, monkeypatch, flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        html = """<html><head>
          <meta property="og:price:amount" content="99.000">
          <meta property="og:price:currency" content="BHD">
          <script type="application/ld+json">
            {"@type":"Product","name":"Oud Elite So Black Eau de Parfum 100ml",
             "offers":{"@type":"Offer","price":"41.000","priceCurrency":"BHD",
                       "availability":"https://schema.org/InStock"}}
          </script>
        </head><body></body></html>"""
        res = _extract(html)
        assert res is not None
        assert res["amount"] == pytest.approx(41.000)


# ---------------------------------------------------------------------------
# The microdata branch is NOT gated by this flag.
#
# Two microdata changes rode this flag as declared preconditions of the reverted
# (c) reorder - document-order-instead-of-max, and the converted_usd relabel.
# Both went with it. Each may well be a real fix, but each has to be measured on
# its own rather than as a rider on an OG-tag flag: on the cached corpus they
# moved faces.ae, a page where microdata ALREADY wins at Priority 3, from 569.64
# BHD page_scrape to 238.76 BHD converted_usd. These tests pin that the flag no
# longer reaches into microdata at all.
# ---------------------------------------------------------------------------

_TWO_OFFER_SCOPES = """<html><body>
  <div itemscope itemtype="https://schema.org/Product">
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <span itemprop="price" content="10">10</span>
      <meta itemprop="priceCurrency" content="QAR" />
    </div>
  </div>
  <div itemscope itemtype="https://schema.org/Product">
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <span itemprop="price" content="45">45</span>
      <meta itemprop="priceCurrency" content="QAR" />
    </div>
  </div>
</body></html>"""


class TestMicrodataIsUntouchedByThisFlag:
    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_offer_scope_selection_is_flag_invariant(self, monkeypatch, flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        res = extract_price_from_html(
            _TWO_OFFER_SCOPES, "Diva Car Freshener Musky Scent", "QAR",
            "nazih.qa", "https://nazih.qa/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(45.0)

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_converted_microdata_provenance_is_flag_invariant(
        self, monkeypatch, flag,
    ):
        html = """<html><body>
          <div itemscope itemtype="https://schema.org/Product">
            <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
              <span itemprop="price" content="15.000">15.000</span>
              <meta itemprop="priceCurrency" content="KWD" />
            </div>
          </div>
        </body></html>"""
        res = extract_price_from_html(
            html, "Miss Dior EDP", "BHD", "klinq.com", "https://klinq.com/p",
        )
        assert res is not None
        assert res["source_method"] == "page_scrape"
        assert res["currency"].upper() == "BHD"

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_offer_scoped_still_outranks_a_bare_price(self, monkeypatch, flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        html = """<html><body>
          <span itemprop="price" content="3.500">3.500</span>
          <div itemscope itemtype="https://schema.org/Product">
            <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
              <span itemprop="price" content="19.900">19.900</span>
              <meta itemprop="priceCurrency" content="BHD" />
            </div>
          </div>
        </body></html>"""
        res = extract_price_from_html(
            html, "Some Product", "BHD", "shop.bh", "https://shop.bh/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(19.900)


# ---------------------------------------------------------------------------
# Flag-OFF regression net for the sibling behaviours the OG branch already had
# ---------------------------------------------------------------------------


class TestUnchangedOgBehaviour:
    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_currencyless_og_defaults_to_expected_not_usd(self, monkeypatch, flag):
        """The sharafdg fix (test_og_price_currency_default.py) must survive."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        html = """<html><head>
          <meta property="product:price:amount" content="244.990">
        </head><body></body></html>"""
        res = extract_price_from_html(
            html, "Apple iPhone 15 128GB", "BHD", "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-blue/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(244.990)
        assert res["currency"].upper() == "BHD"

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_zero_and_negative_amounts_are_still_refused(self, monkeypatch, flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        assert _extract(_og_html("0")) is None
        assert _extract(_og_html("0.00")) is None

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_foreign_currency_og_is_relabelled_converted_usd(self, monkeypatch, flag):
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        res = _extract(_og_html("100.00", "USD"), "BHD", "example.com")
        assert res is not None
        assert res["source_method"] == "converted_usd"
        assert res["currency"].upper() == "BHD"
        assert res["amount"] < 100

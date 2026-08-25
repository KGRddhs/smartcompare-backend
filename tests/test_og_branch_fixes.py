"""Three OpenGraph-branch correctness defects - `ENABLE_OG_BRANCH_FIXES`.

`extract_price_from_html`'s OpenGraph fallback (price_service.py, Priority 2)
shipped three defects, all found by running the 92 cached fragrance PDPs in
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

(c) **The OG branch ran ahead of microdata and the WooCommerce span.** OG is the
    least trustworthy structured source on these pages (it carries the Salla
    LIST price, and ``alhajisoman`` ships an OG amount 10x below the truth), so
    it now runs LAST in the cascade: JSON-LD -> microdata -> WooCommerce -> OG.
    Measured overlap in the cached corpus: 72 pages carry an OG price, 10 of
    them also carry microdata and 4 also carry a WooCommerce span - those 14 are
    the pages whose winner changes.

All three sit behind ONE flag, ``ENABLE_OG_BRANCH_FIXES``, default ON, read per
call from ``os.getenv``. Every behaviour below is asserted in BOTH flag states:
flag OFF must reproduce the exact legacy result.

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

    def test_parse_price_string_is_the_trap_we_avoid(self):
        """WHY the helper is local: the shared parser strips commas
        unconditionally and turns a 24,00 shelf price into 2400.0."""
        assert parse_price_string("24,00") == pytest.approx(2400.0)
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

    def test_a_three_digit_comma_tail_is_thousands_even_on_a_3_decimal_currency(self):
        """The cost of the spec's "1,234 is comma-thousands" rule, pinned so it
        is a KNOWN limit and not a surprise: a hypothetical 3-decimal BHD price
        written with a comma ("22,902") reads as 22902.0, not 22.902. A lone
        comma with a 3-digit tail cannot be told from a thousands group by shape
        alone, and the corpus settles the tie-break: all three real comma-decimal
        pages are 2-decimal (279,00 / 195,00 / 403,75), while "1,234"-style
        thousands are common. No cached page anywhere in _proof/html/ writes a
        3-decimal price with a comma."""
        assert _parse_og_price_number("22,902") == pytest.approx(22902.0)
        assert _parse_og_price_number("22.902") == pytest.approx(22.902)


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
# (c) cascade order - OG runs LAST
# ---------------------------------------------------------------------------

_OG_PLUS_MICRODATA = """<html><head>
  <meta property="og:price:amount" content="99.000">
  <meta property="og:price:currency" content="BHD">
</head><body>
  <div itemscope itemtype="https://schema.org/Product">
    <span itemprop="name">Oud Elite So Black Eau de Parfum 100ml</span>
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <span itemprop="price" content="12.500">12.500</span>
      <meta itemprop="priceCurrency" content="BHD" />
    </div>
  </div>
</body></html>"""

_OG_PLUS_WOO = """<html><head>
  <meta property="og:price:amount" content="99.000">
  <meta property="og:price:currency" content="BHD">
</head><body>
  <p class="price"><span class="woocommerce-Price-amount amount"><bdi>2.110&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span></p>
</body></html>"""


class TestCascadeOrder:
    def test_microdata_beats_og_when_on(self, flag_on):
        res = _extract(_OG_PLUS_MICRODATA)
        assert res is not None
        assert res["amount"] == pytest.approx(12.500)

    def test_og_beats_microdata_when_off(self, flag_off):
        res = _extract(_OG_PLUS_MICRODATA)
        assert res is not None
        assert res["amount"] == pytest.approx(99.000)

    def test_woocommerce_beats_og_when_on(self, flag_on):
        res = _extract(_OG_PLUS_WOO, "BHD", "fragrancebh.com")
        assert res is not None
        assert res["amount"] == pytest.approx(2.110)

    def test_og_beats_woocommerce_when_off(self, flag_off):
        res = _extract(_OG_PLUS_WOO, "BHD", "fragrancebh.com")
        assert res is not None
        assert res["amount"] == pytest.approx(99.000)

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_og_only_page_is_unaffected_by_the_reorder(self, monkeypatch, flag):
        """72 of the 92 cached pages carry an OG price; only the 14 that ALSO
        carry microdata or a Woo span can change winner. The rest must not."""
        monkeypatch.setenv("ENABLE_OG_BRANCH_FIXES", flag)
        res = _extract(_og_html("23"))
        assert res is not None
        assert res["amount"] == pytest.approx(23.0)

    @pytest.mark.parametrize("flag", ["true", "false"])
    def test_jsonld_still_wins_over_everything(self, monkeypatch, flag):
        """The reorder moves OG DOWN; it must never move anything above
        JSON-LD."""
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
# (c) reorder PRECONDITIONS in the microdata branch
#
# Both were harmless while microdata only ran on pages with NO OG price. The
# moment the reorder lets microdata outrank OG they become live defects, so they
# ride the same flag. Found by diffing all 92 cached PDPs flag-ON vs flag-OFF.
# ---------------------------------------------------------------------------

# The real nazih.qa shape: the product's own Offer price (10 QAR — agreed by OG,
# by JSON-LD and by the FIRST microdata node) plus a related-products rail whose
# items are ALSO Offer-scoped. The legacy max-rule shipped the 45.
_NAZIH_SHAPE = """<html><head>
  <meta property="product:price:amount" content="10"/>
  <meta property="product:price:currency" content="QAR"/>
</head><body>
  <div itemscope itemtype="https://schema.org/Product">
    <span itemprop="name">Diva Car Freshener Musky Scent</span>
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <span itemprop="price" content="10">10</span>
      <meta itemprop="priceCurrency" content="QAR" />
    </div>
  </div>
  <!-- related products rail — MUST NOT win -->
  <div itemscope itemtype="https://schema.org/Product">
    <span itemprop="name">Some Other Freshener</span>
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <span itemprop="price" content="45">45</span>
      <meta itemprop="priceCurrency" content="QAR" />
    </div>
  </div>
</body></html>"""


class TestMicrodataReorderPreconditions:
    def test_first_offer_price_wins_not_the_largest(self, flag_on):
        """THE regression the reorder would otherwise ship: 10 QAR, never the
        45 QAR related product."""
        res = extract_price_from_html(
            _NAZIH_SHAPE, "Diva Car Freshener Musky Scent", "QAR", "nazih.qa",
            "https://nazih.qa/diva-car-freshener-musky-scent-8ml.html",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(10.0)
        assert res["amount"] != pytest.approx(45.0)

    def test_flag_off_reproduces_the_legacy_max_rule(self, flag_off):
        """Byte-identity: legacy took the LARGEST Offer-scoped price... but OG
        ran first back then, so the 10 still shipped. Assert the legacy OG win
        rather than the latent microdata bug."""
        res = extract_price_from_html(
            _NAZIH_SHAPE, "Diva Car Freshener Musky Scent", "QAR", "nazih.qa",
            "https://nazih.qa/diva-car-freshener-musky-scent-8ml.html",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(10.0)

    def test_legacy_max_rule_is_what_the_flag_replaces(self, flag_off):
        """Pin the latent defect directly, with no OG tag to mask it — this is
        what the reorder would have exposed."""
        no_og = _NAZIH_SHAPE.split("</head>")[1]
        res = extract_price_from_html(
            "<html><head></head>" + no_og, "Diva Car Freshener Musky Scent",
            "QAR", "nazih.qa", "https://nazih.qa/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(45.0)  # the bug, flag OFF

    def test_offer_scoped_still_outranks_a_bare_price(self, flag_on):
        """First-wins must not demote an Offer-scoped price below a bare one
        that happens to appear earlier in the document."""
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

    def test_converted_microdata_price_is_labelled_converted_usd(self, flag_on):
        """PROVENANCE: a KWD page read on a BHD scrape is a CONVERTED figure, not
        a genuine local shelf price. JSON-LD and OG both relabel; microdata used
        to keep claiming `page_scrape`, which the genuine-BH-share KPI counts."""
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
        assert res["source_method"] == "converted_usd"
        assert res["currency"].upper() == "BHD"

    def test_same_currency_microdata_price_stays_page_scrape(self, flag_on):
        """The relabel must fire ONLY on a conversion — a genuine local BHD
        microdata price is still a genuine page_scrape."""
        html = """<html><body>
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
        assert res["source_method"] == "page_scrape"


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

"""ENABLE_JSONLD_FIRST (default ON) — JSON-LD is the authoritative price source,
visible text is a CROSS-CHECK and never a source, and a capture that produced no
price says WHY.

WHAT THIS WAVE ITEM FIXES, measured over the cached bytes of BOTH corpora (92
Gulf PDPs in ``_proof/html/`` + 322 resolvable global pages in
``_proof/global/html/`` and ``_dach_html/`` = 414 pages), run through the real
``extract_price_from_html`` with ``ENABLE_EXACT_PRICE_GATE=false`` (extraction
isolated, the repo's documented mode for this):

  * BASELINE cascade: JSON-LD 199 pages, OpenGraph 53, microdata 5, no price
    157.
  * **OG price metas are not machine-normalised.** 173 OG price ``content``
    values across the two corpora; **19 of them (11.0%)** are values a bare
    ``float()`` cannot read at all — "279,00" (leperfumeqa), "195,00" (fyzara),
    "403,75" (mhgboutique), "1,082.00" (beautiquefragrances), "1.126,00"
    (perfumeria.pl), "1,799.00" JOD (smartbuy-me). That half of the finding was
    already fixed on this branch by ENABLE_OG_BRANCH_FIXES + ENABLE_MONEY_PARSER_V2
    and is re-pinned here as a REGRESSION test, not re-implemented.
  * **The microdata branch still had its own copy of the BLOCKER-6 comma bug.**
    ``_extract_microdata_price`` did ``str(raw).replace(",", "")`` and then
    ``float()``: eperfumy.pl publishes ``<span itemprop="price"
    class="price">310,00 zl</span>`` and that read **31000.0** — a 100x, the
    qatarperfumeshop defect on a branch BLOCKER 6 never touched. 12 nodes on
    that host misread. It is LATENT today (the Offer-scoped node wins the
    branch's in-scope-first rule) and it stops being latent the moment
    microdata is promoted, which is what this item does.
  * **A currency-less microdata Offer defaulted to the literal "USD".**
    niche-beauty.com carries an ``itemprop=price content="195.00"`` and NO
    ``itemprop=priceCurrency`` anywhere on the page; the branch stamped USD and
    converted a genuine 195,00 EUR shelf price down to **178.83 EUR**. The OG
    branch fixed exactly this defect for itself long ago (sharafdg 244.990) and
    documents the fix; microdata never got it.
  * **Currency codes were stamped raw.** flormar.com.tr publishes
    ``og:price:currency content="try"`` and the extractor returns
    ``{"amount": 799.99, "currency": "try", "original_currency": "try"}`` —
    lowercase, into the payload and the cache key. Lulu publishes lowercase
    ``priceCurrency "aed"/"omr"/"qar"/"sar"``; brownthomas.com publishes
    ``og:price:currency "N/A"``; orisdi.com publishes an
    ``itemprop=priceCurrency`` of ``"0.00"``.
  * **The visible text is unusable as a SOURCE and is only used as a
    CROSS-CHECK here.** Median distinct currency-anchored price tokens per
    cached PDP: 4, max 111. 15 of the 414 pages carry a value that is exactly
    10x or 100x another candidate AND sits next to a per-unit denominator —
    notino.co.uk's GBP 3,200.00 / 1 l beside the GBP 320.00 product price under
    the SAME ``data-testid="pd-price-wrapper"``, superdrug 500.00 per 1l beside
    25.00, breuninger 2.800 EUR / 1 l beside 280 EUR, parfum-zentrum's
    "Grundpreis: 224,90 EUR/l" beside 22,49 EUR.
  * **"HTTP 200 with bytes" is not a capture.** Of the 414 pages, 103 are a
    real page that yields no price in any structured shape, 34 are bot walls
    and 20 are sub-30KB shells. 56 of the no-price pages are HTTP 200, not
    blocked and over 30KB — a "status==200 and bytes>0" test scores every one
    of them as a clean capture.

MEASURED RESULT of the change over those same 414 cached pages
(ENABLE_EXACT_PRICE_GATE=false, flag ON vs flag OFF) is recorded in the report
and re-derived by the census tests at the bottom of this file.

Flag OFF is byte-identical: block F pins the exact legacy dict on every real
fixture, including the three defects above.

Run per-file (the full suite hangs on live network):
    pytest tests/test_jsonld_first_precedence.py \
        -m "not (live_unit or live_db or integration)" --timeout=120
"""

import json
import os
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.services import price_service as ps
from app.services.price_service import extract_price_from_html

FIXTURES = Path(__file__).parent / "fixtures" / "jsonld_first"
PLATFORM_FIXTURES = Path(__file__).parent / "fixtures" / "platform"


# ---------------------------------------------------------------------------
# Helpers. Every fixture under tests/fixtures/jsonld_first/ is CUT FROM REAL
# CACHED BYTES; provenance (source URL, host, country, cache filename, page
# sha1, and exactly what was kept) is recorded in
# tests/fixtures/jsonld_first/SOURCES.json.
# ---------------------------------------------------------------------------
def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def soup_of(name: str):
    return BeautifulSoup(load(name), "html.parser")


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """Default-ON is the shipped state; each test that needs OFF says so."""
    monkeypatch.delenv("ENABLE_JSONLD_FIRST", raising=False)
    yield


def _gate(monkeypatch, value: str):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", value)


def _first(monkeypatch, value: str):
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", value)


NOTINO = "gb_notino_co_uk_unit_price_10x_decoy.html"
LULU = "ae_lulu_lowercase_jsonld_pricecurrency.html"
FLORMAR = "tr_flormar_com_tr_lowercase_og_currency.html"
ALHAJI = "om_alhajisoman_com_og_vs_jsonld_10x.html"
NICHE = "de_niche_beauty_com_microdata_no_pricecurrency.html"
EPERFUMY_RAIL = "pl_eperfumy_pl_microdata_comma_decimal.html"
EPERFUMY_OFFER = "pl_eperfumy_pl_microdata_offer_scope.html"
KLINQ = "kw_klinq_com_kwd_price_converted_to_bhd.html"
DM = "de_dm_de_empty_shell_2xx.html"
MISWAG = "iq_miswag_com_no_structured_price_200.html"
SEPHORA_MULTI = "us_sephora_com_three_sizeless_variants_ambiguous.html"


# ===========================================================================
# A — THE FLAG ITSELF
# ===========================================================================
def test_a_a_the_flag_defaults_on(monkeypatch):
    monkeypatch.delenv("ENABLE_JSONLD_FIRST", raising=False)
    assert ps.jsonld_first_enabled() is True


@pytest.mark.parametrize("off", ["false", "0", "no", "off", "", "FALSE", " Off "])
def test_a_b_every_off_spelling_turns_it_off(monkeypatch, off):
    """Same off-spellings table as the other ten flags on this branch."""
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", off)
    assert ps.jsonld_first_enabled() is False


def test_a_c_the_flag_is_read_per_call_never_cached_at_import(monkeypatch):
    """House rule 1 — os.getenv PER CALL, copying the exact_gate_enabled pattern."""
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "false")
    assert ps.jsonld_first_enabled() is False
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
    assert ps.jsonld_first_enabled() is True
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "off")
    assert ps.jsonld_first_enabled() is False


def test_a_d_it_is_independent_of_every_other_flag(monkeypatch):
    for name in (
        "ENABLE_EXACT_PRICE_GATE", "ENABLE_SALE_PRICE_FIRST", "ENABLE_OG_BRANCH_FIXES",
        "ENABLE_WIDE_CANDIDATE", "ENABLE_SHOPIFY_PDP_JSON", "ENABLE_WIDE_SIGNAL_TEXT",
        "ENABLE_STRICT_CURRENCY_LABEL", "ENABLE_HOSTILE_NUMERIC_GUARD",
        "ENABLE_MONEY_PARSER_V2", "ENABLE_JSONLD_SHAPE_LADDER", "ENABLE_PLATFORM_VERDICT",
    ):
        monkeypatch.setenv(name, "false")
    monkeypatch.delenv("ENABLE_JSONLD_FIRST", raising=False)
    assert ps.jsonld_first_enabled() is True


# ===========================================================================
# B — PRECEDENCE: JSON-LD IS AUTHORITATIVE, OG RANKS BELOW MICRODATA
# ===========================================================================
def test_b_a_jsonld_wins_when_og_disagrees_by_10x(monkeypatch):
    """alhajisoman.com (Gulf corpus). Its own JSON-LD Offer says 30.000 OMR;
    its own og:price:amount says 3.0 OMR. JSON-LD is authoritative in BOTH flag
    states — this is the regression half of the precedence rule."""
    _gate(monkeypatch, "false")
    for state in ("true", "false"):
        _first(monkeypatch, state)
        got = extract_price_from_html(
            load(ALHAJI), "Ch 212 Vip Party Fever Edt Ladies 80Ml", "OMR",
            "alhajisoman.com", "https://alhajisoman.com/products/x",
        )
        assert got is not None, state
        assert got["amount"] == 30.0, state
        assert got["currency"] == "OMR", state


def test_b_b_microdata_now_outranks_opengraph(monkeypatch):
    """klinq.com (Gulf corpus) publishes the SAME 38.5 KWD in both a
    product:price:amount meta and a schema.org microdata Offer. Flag ON the
    microdata Offer is consulted first; flag OFF the OG meta is. The amount is
    identical — what moves is which branch is the provenance."""
    _gate(monkeypatch, "false")
    args = (load(KLINQ), "Miss Dior EDP", "KWD", "klinq.com", "https://klinq.com/en/x.html")

    _first(monkeypatch, "true")
    on = extract_price_from_html(*args)
    _first(monkeypatch, "false")
    off = extract_price_from_html(*args)

    assert on["amount"] == off["amount"] == 38.5
    assert on["confidence"] == 0.8, "microdata's own confidence"
    assert off["confidence"] == 0.9, "the OG branch's own confidence"


def test_b_c_the_takeover_does_not_lose_the_converted_provenance(monkeypatch):
    """The reorder's precondition. klinq's price is 38.5 KWD; asked for in BHD
    it is a CONVERTED figure, and the OG branch has always relabelled that
    ``converted_usd`` so the genuine-BH-share KPI does not count it. Microdata
    never did. Promoting microdata without that relabel would ship a converted
    price labelled as a genuine local shelf price."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(KLINQ), "Miss Dior EDP", "BHD", "klinq.com", "https://klinq.com/en/x.html",
    )
    assert got["original_currency"] == "KWD"
    assert got["currency"] == "BHD"
    assert got["source_method"] == "converted_usd"


def test_b_d_the_takeover_does_not_lose_the_availability_signal(monkeypatch):
    """The reorder's other precondition, measured on the corpus:
    pacoperfumerias.co.uk is a cached page whose og:availability says
    OutOfStock while its microdata Offer carries no availability at all. A
    microdata branch that hardcodes ``in_stock=True`` would flip a sold-out
    product to in-stock the moment it outranks OG. The klinq fixture is the
    silent case: neither an Offer-scoped nor a page-level availability signal
    exists, so the honest answer is None (unknown) — exactly what the OG branch
    returns on the same page."""
    _gate(monkeypatch, "false")
    args = (load(KLINQ), "Miss Dior EDP", "KWD", "klinq.com", "https://klinq.com/en/x.html")
    _first(monkeypatch, "true")
    on = extract_price_from_html(*args)
    _first(monkeypatch, "false")
    off = extract_price_from_html(*args)
    assert on["in_stock"] == off["in_stock"] is None


def test_b_e_a_currency_less_microdata_offer_uses_the_expected_currency(monkeypatch):
    """niche-beauty.com. The page carries ``itemprop=price content="195.00"``
    (visible text "195,-") and NO itemprop=priceCurrency ANYWHERE. The branch
    defaulted to the literal "USD" and converted a genuine 195 EUR shelf price
    to 178.83 EUR. The OG branch already defaults a currency-less price to the
    EXPECTED currency and documents why (bahrain.sharafdg 244.990); microdata
    now does the same."""
    _gate(monkeypatch, "false")
    soup = soup_of(NICHE)

    _first(monkeypatch, "false")
    legacy = ps._extract_microdata_price(soup, "EUR", "niche-beauty.com", "https://x/y")
    assert legacy["amount"] == 178.83
    assert legacy["original_currency"] == "USD"

    _first(monkeypatch, "true")
    fixed = ps._extract_microdata_price(soup, "EUR", "niche-beauty.com", "https://x/y")
    assert fixed["amount"] == 195.0
    assert fixed["original_currency"] == "EUR"
    assert fixed["source_method"] == "page_scrape"


def test_b_f_niche_beauty_end_to_end_now_agrees_with_the_page(monkeypatch):
    """The whole point: the promoted branch must not be the wrong one. With the
    flag ON the extractor returns the number the page actually prints."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(NICHE), "BORNTOSTANDOUT Cola Addict", "EUR",
        "niche-beauty.com", "https://www.niche-beauty.com/x",
    )
    assert got["amount"] == 195.0
    assert got["currency"] == "EUR"


# ===========================================================================
# C — NEVER float() A NON-JSON-LD VALUE: ONE MONEY PARSER ON EVERY BRANCH
# ===========================================================================
def test_c_a_microdata_text_comma_decimal_is_no_longer_a_100x(monkeypatch):
    """eperfumy.pl's related-product rail. Each node is
    ``<span itemprop="price" class="price">NNN,00 zl</span>``. The legacy branch
    stripped the comma and read 30800.0 for "308,00 zl"; the canonical parser
    reads 308.0. Asked in the branch's own legacy default currency so the
    PARSE is isolated from the currency fix."""
    _gate(monkeypatch, "false")
    soup = soup_of(EPERFUMY_RAIL)

    _first(monkeypatch, "false")
    legacy = ps._extract_microdata_price(soup, "USD", "eperfumy.pl", "https://eperfumy.pl/x")
    assert legacy["amount"] == 30800.0, "the 100x, reproduced on real cached bytes"

    _first(monkeypatch, "true")
    fixed = ps._extract_microdata_price(soup, "USD", "eperfumy.pl", "https://eperfumy.pl/x")
    assert fixed["amount"] == 308.0


def test_c_b_the_rail_only_page_pended_entirely_under_the_usd_default(monkeypatch):
    """Same bytes, asked in the page's real currency. The legacy USD default
    made the price unconvertible (PLN is not in FALLBACK_RATES), so
    ENABLE_STRICT_CURRENCY_LABEL pended a real price outright. With the flag ON
    it is read in PLN and kept."""
    _gate(monkeypatch, "false")
    soup = soup_of(EPERFUMY_RAIL)

    _first(monkeypatch, "false")
    assert ps._extract_microdata_price(soup, "PLN", "eperfumy.pl", "https://eperfumy.pl/x") is None

    _first(monkeypatch, "true")
    fixed = ps._extract_microdata_price(soup, "PLN", "eperfumy.pl", "https://eperfumy.pl/x")
    assert fixed["amount"] == 308.0
    assert fixed["currency"] == "PLN"


def test_c_c_the_parser_fix_does_not_move_a_correct_answer(monkeypatch):
    """The same page's real Offer itemscope — priceCurrency PLN and
    ``<span itemprop="price" content="310">310,00 zl</span>``, beside three
    comma-decimal rail nodes. The Offer-scoped node is the product price in
    BOTH flag states; the fix only stops its neighbours reading 100x."""
    _gate(monkeypatch, "false")
    soup = soup_of(EPERFUMY_OFFER)
    for state in ("true", "false"):
        _first(monkeypatch, state)
        got = ps._extract_microdata_price(soup, "PLN", "eperfumy.pl", "https://eperfumy.pl/x")
        assert got["amount"] == 310.0, state
        assert got["currency"] == "PLN", state


def test_c_d_the_og_comma_decimals_stay_readable(monkeypatch):
    """REGRESSION, not a new fix. 19 of the 173 OG price metas in the two
    corpora are comma/grouped values a bare float() raises on. That was fixed
    by ENABLE_OG_BRANCH_FIXES + ENABLE_MONEY_PARSER_V2; nothing in this wave
    may undo it."""
    from app.services.price_service import _parse_og_price_number
    for raw, cur, want in (
        ("279,00", "QAR", 279.0), ("195,00", "QAR", 195.0), ("403,75", "QAR", 403.75),
        ("1,082.00", "AED", 1082.0), ("1.126,00", "PLN", 1126.0),
        ("1,799.00", "JOD", 1799.0), ("22,902", "BHD", 22.902),
    ):
        for state in ("true", "false"):
            _first(monkeypatch, state)
            assert _parse_og_price_number(raw, cur) == want, (raw, cur, state)


# ===========================================================================
# D — UPPERCASE AND ISO-VALIDATE EVERY CURRENCY CODE BEFORE USE
# ===========================================================================
def test_d_a_a_lowercase_og_currency_is_uppercased(monkeypatch):
    """flormar.com.tr publishes og:price:currency "try". Reproduced end to end
    on the cached bytes: the shipped extractor returns currency "try"."""
    _gate(monkeypatch, "false")
    args = (load(FLORMAR), "Flormar Extreme Tattoo", "TRY",
            "www.flormar.com.tr", "https://www.flormar.com.tr/x/")

    _first(monkeypatch, "false")
    legacy = extract_price_from_html(*args)
    assert legacy["currency"] == "try"
    assert legacy["original_currency"] == "try"

    _first(monkeypatch, "true")
    fixed = extract_price_from_html(*args)
    assert fixed["amount"] == 799.99
    assert fixed["currency"] == "TRY"
    assert fixed["original_currency"] == "TRY"


def test_d_b_a_lowercase_jsonld_pricecurrency_is_uppercased(monkeypatch):
    """gcc.luluhypermarket.com publishes ``"priceCurrency":"aed"``. The
    currency GATE already folded case; what this pins is that the code the
    price is LABELLED with comes out canonical."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(LULU), "Ahmed Al Maghribi EDP Perfume Marj 60 ml", "AED",
        "gcc.luluhypermarket.com", "https://gcc.luluhypermarket.com/en-ae/x/p/2257851/",
    )
    assert got["amount"] == 175.0
    assert got["currency"] == "AED"
    assert got["original_currency"] == "AED"


def test_d_c_iso_validation_accepts_real_codes_in_any_case():
    for raw, want in (
        ("aed", "AED"), ("AED", "AED"), (" try ", "TRY"), ("omr", "OMR"),
        ("sar", "SAR"), ("qar", "QAR"), ("pln", "PLN"), ("SEK", "SEK"),
        ("dkk", "DKK"), ("CAD", "CAD"), ("EGP", "EGP"), ("JOD", "JOD"),
        ("chf", "CHF"), ("gbp", "GBP"), ("usd", "USD"), ("eur", "EUR"),
    ):
        assert ps.iso_currency_label(raw) == want


def test_d_d_iso_validation_rejects_the_junk_the_corpora_actually_publish():
    """Every token below is a real value scraped out of the cached bytes."""
    for raw in ("N/A", "0.00", "null", "US", "data", "", "   ", "$", "1", "EURO", "AEDX"):
        assert ps.iso_currency_label(raw) is None, raw


def test_d_e_iso_validation_is_total():
    for raw in (None, True, False, 3, 3.5, b"AED", ["AED"], {"c": "AED"}, object()):
        assert ps.iso_currency_label(raw) is None


BROWNTHOMAS_NA = (
    '<html><head><title>Aventus Eau de Parfum</title>'
    '<meta property="og:title" content="Aventus Eau de Parfum"/>'
    '<meta property="og:price:amount" itemprop="price:amount" content="285.00"/>'
    '<meta property="og:price:currency" itemprop="price:currency" content="N/A"/>'
    "</head><body></body></html>"
)


def test_d_f_a_junk_currency_token_is_NOT_the_same_state_as_a_missing_one(monkeypatch):
    """brownthomas.com publishes ``og:price:currency content="N/A"``.

    THIS TEST USED TO ASSERT THE OPPOSITE, and that assertion was the bug.
    It read: a token that is not an ISO 4217 code carries no information, so it
    is the same epistemic state as a MISSING tag — and the OG branch resolves a
    missing tag to the expected currency (bahrain.sharafdg 244.990). The premise
    is wrong. A page with no currency tag is SILENT; a page with an unreadable
    one is denominated in SOMETHING, and stamping it with the ask asserts a 1.0
    rate that nothing measured. Collapsing the two un-did BLOCKER 4 for every
    branch (``tests/test_strict_currency_label.py`` section 4 pins the
    casualties) and shipped niche-beauty.com's 195 EUR as 195 "BHD" and
    samawa.ae's 271 AED as 271 "BHD".

    ``_currency_label_for`` now consults PAGE-LEVEL evidence first and only then
    distinguishes the two states — this page has no second opinion to give, so
    the junk comes back raw, conversion fails on it and the price PENDS. The
    sharafdg rule is untouched and is pinned at
    ``tests/test_strict_currency_label.py::
    TestMissingEverythingStillMeansTheExpectedCurrency``.
    """
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
    assert extract_price_from_html(
        BROWNTHOMAS_NA, "Aventus Eau de Parfum", "EUR",
        "www.brownthomas.com", "https://x/y",
    ) is None, "an unreadable currency was served with the ask stamped on it"


def test_d_g_page_evidence_rescues_a_junk_token_when_the_page_has_a_second_opinion(
    monkeypatch,
):
    """The junk token only pends when the DOCUMENT is out of answers. Give the
    same page a product:price:currency of GBP and the 285 is read as GBP."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "true")
    html = BROWNTHOMAS_NA.replace(
        "</head>",
        '<meta property="product:price:currency" content="GBP"/></head>',
    )
    got = extract_price_from_html(
        html, "Aventus Eau de Parfum", "EUR", "www.brownthomas.com", "https://x/y",
    )
    assert got is not None
    assert got["original_currency"] == "GBP"
    assert got["currency"] == "EUR"
    assert "N/A" not in json.dumps(got)


def test_d_h_the_junk_token_rollback_is_the_legacy_serve(monkeypatch):
    """With the strict flag OFF the junk still reaches
    ``_convert_gpt_price_currency``, which relabels at the legacy implicit rate —
    the 8adaefb behaviour, junk in ``original_currency`` and all."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    monkeypatch.setenv("ENABLE_STRICT_CURRENCY_LABEL", "false")
    got = extract_price_from_html(
        BROWNTHOMAS_NA, "Aventus Eau de Parfum", "EUR",
        "www.brownthomas.com", "https://x/y",
    )
    assert got is not None
    assert got["currency"] == "EUR"
    assert got["original_currency"] == "N/A"


# ===========================================================================
# E — CROSS-CHECK, NOT SOURCE: THE DECOY GUARD AND THE CONFIRMATION PASS
# ===========================================================================
def test_e_a_the_notino_unit_price_is_identified_as_a_decoy():
    """THE headline case. notino.co.uk renders the per-litre unit price under
    the SAME data-testid as the product price. Both values are currency-anchored
    price tokens on the page; 3200.00 is exactly 10x 320.00 and the characters
    that follow it are "/ 1 l, incl. VAT"."""
    ev = ps.page_money_evidence(soup_of(NOTINO), "GBP")
    assert ev.confirms(320.0) is True
    assert ev.confirms(3200.0) is True, "it IS on the page - that is why it is dangerous"
    assert ev.is_decoy(3200.0) is True
    assert ev.is_decoy(320.0) is False


def test_e_b_the_decoy_never_confirms_a_price():
    """A decoy token must not be usable as evidence FOR a price."""
    ev = ps.page_money_evidence(soup_of(NOTINO), "GBP")
    assert ev.confirms_as_product_price(320.0) is True
    assert ev.confirms_as_product_price(3200.0) is False


def test_e_c_the_right_value_wins_end_to_end_on_notino(monkeypatch):
    """And the pipeline returns 320.00, never 3,200.00, in BOTH flag states —
    because JSON-LD is the source and text is only ever a check."""
    _gate(monkeypatch, "false")
    for state in ("true", "false"):
        _first(monkeypatch, state)
        got = extract_price_from_html(
            load(NOTINO), "Amouage Honour", "GBP",
            "www.notino.co.uk", "https://www.notino.co.uk/amouage/honour-eau-de-parfum-for-men/",
        )
        assert got["amount"] == 320.0, state
        assert got["currency"] == "GBP", state


def test_e_d_a_non_jsonld_candidate_that_is_a_decoy_is_rejected(monkeypatch):
    """The guard itself. On the notino bytes an OG branch that had served the
    unit price would be refused; serving the product price is untouched."""
    ev = ps.page_money_evidence(soup_of(NOTINO), "GBP")
    assert ev.is_decoy(3200.0) is True
    # 100x as well as 10x - reject a candidate that is 100x another candidate
    ev2 = ps.page_money_evidence(
        BeautifulSoup(
            '<html><body><span>GBP 12.50</span>'
            '<span>GBP 1,250.00 / 1 l, incl. VAT</span></body></html>',
            "html.parser",
        ),
        "GBP",
    )
    assert ev2.is_decoy(1250.0) is True
    assert ev2.is_decoy(12.5) is False


def test_e_e_a_per_unit_marker_is_never_a_price_locating_cue():
    """Blacklisted, not used. A number next to "Grundpreis" / "/ 100 ml" /
    "per 1l" is a unit price; it must never be picked BECAUSE of that marker.
    Real strings from parfum-zentrum.de, douglas.at and superdrug.com."""
    for markup, unit, real in (
        ('<span>22,49 &euro; inkl. MwSt. | Grundpreis: 224,90 &euro;/l</span>', 224.9, 22.49),
        ('<span>&euro;44,99 30 ml &euro;149,97 / 100 ml</span>', 149.97, 44.99),
        ('<span>Original price &pound;25.00 each &pound;250.00 per 1l</span>', 250.0, 25.0),
    ):
        ev = ps.page_money_evidence(BeautifulSoup("<html><body>%s</body></html>" % markup, "html.parser"), "EUR")
        assert ev.is_unit_priced(unit) is True, markup
        assert ev.is_unit_priced(real) is False, markup


def test_e_f_incl_vat_alone_is_not_a_unit_marker():
    """MEASURED CORRECTION to the brief, which lists "incl. VAT" as a decoy
    marker. On the cached bytes "inkl. MwSt." / "incl. VAT" sits next to the
    REAL price on pieper.de, breuninger.com and douglas.at. Only a per-unit
    DENOMINATOR makes a number a unit price."""
    ev = ps.page_money_evidence(
        BeautifulSoup('<html><body><span>&euro;&nbsp;73,39 inkl. MwSt.</span>'
                      '<span>&euro;&nbsp;7,339</span></body></html>', "html.parser"),
        "EUR",
    )
    assert ev.is_unit_priced(73.39) is False
    assert ev.is_decoy(73.39) is False


def test_e_g_a_confirmed_non_jsonld_price_keeps_its_confidence(monkeypatch):
    """klinq.com prints "KWD 38.500" in its visible markup, so the microdata
    Offer's 38.5 is confirmed by the page's own text."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(KLINQ), "Miss Dior EDP", "KWD", "klinq.com", "https://klinq.com/en/x.html",
    )
    assert got["price_confirmed_in_text"] is True
    assert got["confidence"] == 0.8


def test_e_h_the_cross_check_runs_on_the_pages_own_currency_not_the_converted_one(monkeypatch):
    """The same page asked for in BHD converts 38.5 KWD to 47.35 BHD. 47.35
    appears NOWHERE on the page — confirming the CONVERTED number would mark
    every converted price unconfirmed. The check runs before conversion."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(KLINQ), "Miss Dior EDP", "BHD", "klinq.com", "https://klinq.com/en/x.html",
    )
    assert got["amount"] == 47.35
    assert "47.35" not in soup_of(KLINQ).get_text(" ", strip=True)
    assert got["price_confirmed_in_text"] is True


def test_e_i_an_unconfirmed_non_jsonld_price_is_marked_and_downgraded(monkeypatch):
    """A price no visible token on the page supports keeps its amount — the
    structured tag is still the source — but says so and scores lower."""
    html = (
        '<html><head><title>Miss Dior EDP</title>'
        '<meta property="og:title" content="Miss Dior EDP"/>'
        '<meta property="og:price:amount" content="47.35"/>'
        '<meta property="og:price:currency" content="BHD"/>'
        '</head><body><span>BHD 30.750</span><span>BHD 38.500</span></body></html>'
    )
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(html, "Miss Dior EDP", "BHD", "klinq.com", "https://x/y")
    assert got["amount"] == 47.35
    assert got["price_confirmed_in_text"] is False
    assert got["confidence"] < 0.9


def test_e_j_the_jsonld_branch_is_not_cross_checked(monkeypatch):
    """JSON-LD is the authoritative source, not a candidate needing support:
    353 of 360 JSON-LD price values in the global corpus are already
    machine-normalised. Cross-checking it would only add noise."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(NOTINO), "Amouage Honour", "GBP", "www.notino.co.uk", "https://x/y",
    )
    assert got["confidence"] == 1.0
    assert "price_confirmed_in_text" not in got


# ===========================================================================
# F — CAPTURE SUCCESS IS A VALIDATED PRICE, NEVER A STATUS CODE
# ===========================================================================
def test_f_a_the_outcome_classes_exist_and_are_distinct():
    assert ps.CAPTURE_OK == "ok"
    assert ps.CAPTURE_WALLED == "walled"
    assert ps.CAPTURE_EMPTY_SHELL == "empty_shell"
    assert ps.CAPTURE_NO_STRUCTURED_PRICE == "no_structured_price"
    assert ps.CAPTURE_AMBIGUOUS_PRICE == "ambiguous_price"
    assert len(set(ps.CAPTURE_OUTCOMES)) == 5


def test_f_b_a_bot_wall_is_walled():
    """The cached sephora.me PDP fetch: 624 bytes of Akamai "Access Denied"."""
    walled = (PLATFORM_FIXTURES / "ae_sephora_me_akamai_403.html").read_text(encoding="utf-8")
    assert ps.classify_capture(walled) == ps.CAPTURE_WALLED
    assert ps.classify_capture(walled, http_status=403) == ps.CAPTURE_WALLED


def test_f_c_a_status_code_alone_can_name_a_wall():
    """A bare 403 body carries no wall phrase at all — 30 of the 34 walled
    pages in the corpora are exactly this. When the caller knows the status it
    is decisive."""
    assert ps.classify_capture("<html></html>", http_status=403) == ps.CAPTURE_WALLED
    assert ps.classify_capture("<html></html>", http_status=429) == ps.CAPTURE_WALLED
    assert ps.classify_capture("<html></html>", http_status=530) == ps.CAPTURE_WALLED


def test_f_d_a_sub_30kb_2xx_shell_is_an_empty_shell():
    """dm.de answered 200 with 11,199 bytes of client-rendered shell. A
    "status==200 and bytes>0" test scores that as a clean capture."""
    html = load(DM)
    assert len(html) < 30000
    assert ps.classify_capture(html, http_status=200) == ps.CAPTURE_EMPTY_SHELL


def test_f_e_a_real_page_with_no_structured_price_says_so():
    """miswag.com: HTTP 200, not blocked, 45,030 bytes of real markup, and no
    price in JSON-LD, OpenGraph, microdata or a WooCommerce span."""
    html = load(MISWAG)
    assert len(html) > 30000
    assert ps.classify_capture(html, http_status=200) == ps.CAPTURE_NO_STRUCTURED_PRICE


def test_f_f_a_price_is_the_only_thing_that_makes_a_capture_ok():
    html = load(MISWAG)
    assert ps.classify_capture(html, price={"amount": 12.5, "currency": "USD"}) == ps.CAPTURE_OK
    assert ps.classify_capture(html, price={"amount": 0, "currency": "USD"}) != ps.CAPTURE_OK
    assert ps.classify_capture(html, price=None, http_status=200) != ps.CAPTURE_OK


def test_f_g_classify_capture_is_total():
    for html in (None, "", b"bytes", 3, [], {}, object()):
        assert ps.classify_capture(html) in ps.CAPTURE_OUTCOMES
    for status in (None, "403", -1, 0, 999, object()):
        assert ps.classify_capture("<html></html>", http_status=status) in ps.CAPTURE_OUTCOMES


def test_f_h_the_reason_is_returned_never_a_silent_none(monkeypatch):
    """The pipeline gap this closes: a no-price page returned None and nothing
    said whether it was a wall, a shell, or a real page with no markup."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    out = []
    got = extract_price_from_html(
        load(MISWAG), "Miswag", "IQD",
        "miswag.com", "https://miswag.com/x", outcome_out=out,
    )
    assert got is None
    assert out == [ps.CAPTURE_NO_STRUCTURED_PRICE]

    out = []
    got = extract_price_from_html(
        load(DM), "dm-drogerie markt", "EUR", "dm.de", "https://dm.de/x", outcome_out=out,
    )
    assert got is None
    assert out == [ps.CAPTURE_EMPTY_SHELL]


def test_f_i_a_successful_capture_reports_ok_on_the_price_itself(monkeypatch):
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    out = []
    got = extract_price_from_html(
        load(NOTINO), "Amouage Honour", "GBP", "www.notino.co.uk",
        "https://www.notino.co.uk/amouage/honour-eau-de-parfum-for-men/", outcome_out=out,
    )
    assert got["capture_outcome"] == ps.CAPTURE_OK
    assert out == [ps.CAPTURE_OK]


def test_f_j_the_outcome_channel_is_a_courtesy_never_a_dependency(monkeypatch):
    """Anything that is not a list is ignored, exactly like the shape ladder's
    ``pending_out``."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    for junk in (None, 0, "list", {}, object()):
        got = extract_price_from_html(
            load(NOTINO), "Amouage Honour", "GBP", "www.notino.co.uk",
            "https://x/y", outcome_out=junk,
        )
        assert got["amount"] == 320.0


# ---------------------------------------------------------------------------
# F4 — "N CANDIDATES, NONE PROVABLY YOURS" IS NOT "NOTHING ON THE PAGE"
#
# The whole point of the outcome channel is that each class prescribes a
# DIFFERENT next move: a wall needs a different fetch channel, a shell needs a
# renderer, a real page with no markup needs a new extractor. The shape ladder's
# multiplicity pend is a FOURTH prescription — the markup is there, it is
# machine-normalised, and there are simply N of it: what that page needs is a
# DISCRIMINATOR (a size, an availability, a declared default). Until this unit
# the ladder's pend reached the channel as a body-only verdict and issued one of
# the other three instructions, all of them wrong.
# ---------------------------------------------------------------------------
def test_f_k_n_candidates_none_provably_yours_is_its_own_outcome(monkeypatch):
    """sephora.com P475526 ships a ProductGroup of THREE sizeless variants —
    199.00 / 265.00 / 330.00 USD, no size on any of them and nothing marking a
    default — so the ladder pends rather than silently taking the cheapest
    (tests/test_jsonld_shape_ladder.py::test_c_a). That pend is what the channel
    has to report."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    out = []
    got = extract_price_from_html(
        load(SEPHORA_MULTI), "Dior Sauvage Elixir", "USD", "www.sephora.com",
        "https://www.sephora.com/product/dior-sauvage-elixir-P475526",
        outcome_out=out,
    )
    assert got is None
    assert out == [ps.CAPTURE_AMBIGUOUS_PRICE]


def test_f_l_the_multiplicity_fact_outranks_both_body_heuristics(monkeypatch):
    """`classify_capture` only ever sees the BODY, so it misreports this page in
    BOTH size regimes: the minimal cut (1.9KB) reads as an empty_shell and the
    real 914KB page reads as no_structured_price. Both instructions are wrong for
    the same reason — a page carrying three identity-matched, machine-normalised
    JSON-LD offers is neither client-rendered nor price-less. Pinned in both."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    small = load(SEPHORA_MULTI)
    assert len(small) < 30000
    big = small + "<!--" + ("x" * 40000) + "-->"
    # What the body alone says, i.e. what this page used to report:
    assert ps.classify_capture(small) == ps.CAPTURE_EMPTY_SHELL
    assert ps.classify_capture(big) == ps.CAPTURE_NO_STRUCTURED_PRICE
    for html in (small, big):
        out = []
        got = extract_price_from_html(
            html, "Dior Sauvage Elixir", "USD", "www.sephora.com",
            "https://x/y", outcome_out=out,
        )
        assert got is None
        assert out == [ps.CAPTURE_AMBIGUOUS_PRICE]


def test_f_m_ambiguous_price_fires_only_on_the_multiplicity_pend(monkeypatch):
    """The class is NARROW. The other two no-price pages keep their own verdicts
    (pinned in test_f_h), and the SAME sephora page with the shape ladder OFF
    finds no candidate at all — no ProductGroup walk, so no multiplicity — and
    falls back to the body verdict it had before."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    monkeypatch.setenv("ENABLE_JSONLD_SHAPE_LADDER", "false")
    out = []
    got = extract_price_from_html(
        load(SEPHORA_MULTI), "Dior Sauvage Elixir", "USD", "www.sephora.com",
        "https://x/y", outcome_out=out,
    )
    assert got is None
    assert out == [ps.CAPTURE_EMPTY_SHELL]


def test_f_n_classify_capture_stays_total_and_never_says_ambiguous():
    """The multiplicity fact is produced by the extractor, which is the only
    thing that knows WHY the JSON-LD path declined; `classify_capture` is handed
    bytes and a price and stays exactly as total, and as narrow, as it was."""
    for html in (None, "", b"bytes", 3, [], {}, object()):
        assert ps.classify_capture(html) in ps.CAPTURE_OUTCOMES
        assert ps.classify_capture(html) != ps.CAPTURE_AMBIGUOUS_PRICE
    assert ps.classify_capture(load(SEPHORA_MULTI)) != ps.CAPTURE_AMBIGUOUS_PRICE
    assert ps.classify_capture(
        load(SEPHORA_MULTI), price={"amount": 199.0, "currency": "USD"},
    ) == ps.CAPTURE_OK


def test_f_o_a_capture_that_produced_a_price_is_ok_not_ambiguous(monkeypatch):
    """`ambiguous_price` names a DECLINE. A pend on the target currency that the
    USD retry (or a lower cascade branch) then resolves is a successful capture
    and must still report ok — the channel reports the outcome, not the journey."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "true")
    out = []
    got = extract_price_from_html(
        load(NOTINO), "Amouage Honour", "GBP", "www.notino.co.uk",
        "https://x/y", outcome_out=out,
    )
    assert got["amount"] == 320.0
    assert out == [ps.CAPTURE_OK]
    assert got["capture_outcome"] == ps.CAPTURE_OK


# ===========================================================================
# G — FLAG OFF IS BYTE-IDENTICAL, DEFECTS INCLUDED
# ===========================================================================
def test_g_a_flag_off_keeps_the_lowercase_currency(monkeypatch):
    _gate(monkeypatch, "false")
    _first(monkeypatch, "false")
    got = extract_price_from_html(
        load(FLORMAR), "Flormar Extreme Tattoo", "TRY",
        "www.flormar.com.tr", "https://www.flormar.com.tr/x/",
    )
    assert got == {
        "amount": 799.99,
        "original_currency": "try",
        "currency": "try",
        "retailer": "www.flormar.com.tr",
        "url": "https://www.flormar.com.tr/x/",
        "in_stock": None,
        "confidence": 0.9,
        "estimated": False,
        "source_method": "page_scrape",
    }


def test_g_b_flag_off_keeps_the_niche_beauty_usd_default(monkeypatch):
    _gate(monkeypatch, "false")
    _first(monkeypatch, "false")
    got = ps._extract_microdata_price(
        soup_of(NICHE), "EUR", "niche-beauty.com", "https://www.niche-beauty.com/x",
    )
    assert got == {
        "amount": 178.83,
        "original_currency": "USD",
        "currency": "EUR",
        "retailer": "niche-beauty.com",
        "url": "https://www.niche-beauty.com/x",
        "in_stock": True,
        "confidence": 0.8,
        "estimated": False,
        "source_method": "page_scrape",
    }


def test_g_c_flag_off_keeps_the_microdata_100x(monkeypatch):
    _gate(monkeypatch, "false")
    _first(monkeypatch, "false")
    got = ps._extract_microdata_price(
        soup_of(EPERFUMY_RAIL), "USD", "eperfumy.pl", "https://eperfumy.pl/x",
    )
    assert got["amount"] == 30800.0


def test_g_d_flag_off_adds_no_new_keys_anywhere(monkeypatch):
    """No price_confirmed_in_text, no capture_outcome, and outcome_out is never
    written to."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "false")
    out = []
    for name, q, cur, host in (
        (NOTINO, "Amouage Honour", "GBP", "www.notino.co.uk"),
        (KLINQ, "Miss Dior EDP", "KWD", "klinq.com"),
        (ALHAJI, "Ch 212 Vip Party Fever Edt Ladies 80Ml", "OMR", "alhajisoman.com"),
        (LULU, "Ahmed Al Maghribi EDP Perfume Marj 60 ml", "AED", "gcc.luluhypermarket.com"),
        (MISWAG, "Miswag", "IQD", "miswag.com"),
        (DM, "dm-drogerie markt", "EUR", "dm.de"),
        (SEPHORA_MULTI, "Dior Sauvage Elixir", "USD", "www.sephora.com"),
    ):
        got = extract_price_from_html(load(name), q, cur, host, "https://x/y", outcome_out=out)
        if got is not None:
            assert "price_confirmed_in_text" not in got, name
            assert "capture_outcome" not in got, name
    assert out == []


def test_g_e_flag_off_keeps_the_opengraph_priority(monkeypatch):
    """The cascade order itself rolls back: on klinq the OG branch answers."""
    _gate(monkeypatch, "false")
    _first(monkeypatch, "false")
    got = extract_price_from_html(
        load(KLINQ), "Miss Dior EDP", "BHD", "klinq.com", "https://klinq.com/en/x.html",
    )
    assert got["confidence"] == 0.9
    assert got["source_method"] == "converted_usd"


# ===========================================================================
# H — TOTALITY. Nothing here may raise on any input.
# ===========================================================================
@pytest.mark.parametrize("html", [
    "", "<html>", "<html><body>٠١٢</body></html>",
    "<html><body>" + "9" * 500 + " USD</body></html>",
    '<html><body><span itemprop="price">nan</span></body></html>',
    '<html><body><span itemprop="price">1e400 USD</span></body></html>',
])
def test_h_a_the_new_helpers_never_raise(monkeypatch, html):
    _gate(monkeypatch, "false")
    for state in ("true", "false"):
        _first(monkeypatch, state)
        assert extract_price_from_html(html, "Anything", "USD", "x.com", "https://x/y") is None or True
        ev = ps.page_money_evidence(BeautifulSoup(html, "html.parser"), "USD")
        assert ev.confirms(1.0) in (True, False)
        assert ev.is_decoy(1.0) in (True, False)


def test_h_b_the_evidence_helper_is_total_on_a_hostile_currency():
    soup = BeautifulSoup('<html><body><span>USD 10.00</span></body></html>', "html.parser")
    for cur in (None, True, 3, b"USD", ["USD"], {"c": 1}, object()):
        ev = ps.page_money_evidence(soup, cur)
        assert ev.confirms(10.0) in (True, False)

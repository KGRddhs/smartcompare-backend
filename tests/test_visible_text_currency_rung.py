"""M10 UNIT A1 — the ADJACENCY-ANCHORED visible-text currency rung.

THE DEFECT THIS PINS, measured 2026-08-31 on the real cached bytes of
``https://www.faces.ae/en/brands/tom-ford``
(``_proof/html/9b2d8db66a4d9a1bf9fc03852e802085724b39a8.html``), in SHIPPED mode
(``ENABLE_EXACT_PRICE_GATE`` at its default ON, ``ENABLE_NOT_A_PDP_FILTER``
unset):

    extract_price_from_html(faces_bytes, "Tom Ford", "BHD", "faces.ae", url)
      -> {'amount': 1515.0, 'currency': 'BHD', 'original_currency': 'BHD',
          'source_method': 'page_scrape', 'price_confirmed_in_text': True}

The page prints ``&#x2066;1515&#x2069; AED``. 1515 AED is about 155 BHD, so the
shipped answer is a **9.8x over-price** — the identical shape to the BLOCKER-4
cases (niche-beauty 195 EUR as "BHD", samawa.ae 271 AED as "BHD") that
``_currency_label_for``'s hierarchy exists to kill. It survives because:

  * every ``itemprop="price"`` on the page sits in an ``AggregateOffer`` with NO
    ``itemprop="priceCurrency"``, the single ld+json block is an ItemList with no
    ``priceCurrency``, and there are no price/currency metas — so
    ``_page_currency_evidence`` returns None and ``_currency_label_for`` falls to
    rung 3, the ASK currency;
  * ``_page_identity_ok("Tom Ford", soup, "fragrances")`` is True, because a BARE
    BRAND query legitimately matches a brand LISTING page's own title. Only a
    product-qualified query ("Tom Ford Oud Wood") is rejected. Bare brand is a
    query shape users type constantly.

The stamp follows the ASK, not the page: expected BHD/AED/SAR each come back
labelled BHD/AED/SAR on the same 1515.

THE FIX, and why each rule is in it (every number measured over the 414 cached
pages, zero network):

  * ``_page_currency_evidence`` returns None on 118 of 414 pages.
  * A naive "any ISO code present in the visible text" rung fires on 19 of those
    118 and is DANGEROUS: ``ALL`` (Albanian lek) and ``TRY`` (Turkish lira) are
    ordinary English words, so brownthomas.com scores ALL+TRY and
    solsticescents.com scores ALL against USD/EUR truths.
  * Requiring ADJACENCY to a price-shaped number collapses that to 7 pages, of
    which 6 carry exactly one distinct code and every one of them agrees with the
    corpus-recorded page currency (en-kwt.ajmal KWD, faces.ae AED, ouddubai.ae
    AED, bloomingdales.com.kw KWD, salams.com QAR, gcc.luluhypermarket KWD). The
    7th, spinneyslebanon.com, prints an exchange-rate line "1.00 USD = 89,700
    LBP" — two distinct adjacent codes, no right answer, so it must ABSTAIN.
  * Even under adjacency one English-word collision survives: spacenk.com matches
    ``TOP`` (Tongan pa'anga) in "| TOP 100". Hence the denylist {TOP, ALL, TRY},
    which admits those three only on a SECOND corroborating machine signal.
  * The rung must sit BELOW the two existing machine rungs. 95 pages have both
    machine evidence and a single adjacent code, and on 2 the adjacent code
    CONTRADICTS the (correct) machine evidence: bathandbodyworks.com.eg (og EGP,
    adjacent AED from a "3 for AED 125" cross-market banner, truth EGP) and
    spacenk.com (JSON-LD GBP, adjacent TOP, truth GBP). Promoting the text rung
    would ship two new mislabels to buy one repair.

Fixtures: ``tests/fixtures/visible_text_currency/`` — DOM-pruned cuts of the real
cached pages, each gated so the rung, a naive any-code scan,
``_page_currency_evidence`` and (faces.ae) ``extract_price_from_html`` return the
same values on the cut as on the full page. Provenance in that directory's
``SOURCES.json``.
"""
import os

import pytest
from bs4 import BeautifulSoup

from app.services import price_service as ps
from app.services.price_service import extract_price_from_html

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "visible_text_currency")
FACES_URL = "https://www.faces.ae/en/brands/tom-ford"


def load(name):
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as fh:
        return fh.read()


def soup_of(name):
    return BeautifulSoup(load(name), "html.parser")


def _rung(monkeypatch, value):
    monkeypatch.setenv("ENABLE_VISIBLE_TEXT_CURRENCY", value)


def _shipped_mode(monkeypatch):
    """The gate at its shipped default (ON) and the F1 filter at its (OFF)."""
    monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)


def ev(html_or_soup):
    if isinstance(html_or_soup, str):
        html_or_soup = BeautifulSoup(html_or_soup, "html.parser")
    return ps._visible_text_currency_evidence(html_or_soup)


# ===========================================================================
# A — THE RUNG IN ISOLATION
# ===========================================================================
def test_a_adjacent_code_after_a_number_is_evidence():
    assert ev("<html><body><p>Price 1515 AED</p></body></html>") == "AED"


def test_a_adjacent_code_before_a_number_is_evidence():
    assert ev("<html><body><p>AED 1515 total</p></body></html>") == "AED"


def test_a_a_bidi_isolated_code_resolves():
    """The faces.ae shape verbatim: U+2066 ... U+2069 around the number."""
    assert ev("<html><body><span> ⁦1515⁩ AED</span></body></html>") == "AED"


def test_a_a_nbsp_separated_code_resolves():
    """The space family folds out with the bidi controls, so a non-breaking
    space between the number and the code is not a barrier."""
    assert ev("<html><body><span>1515 KWD</span></body></html>") == "KWD"


def test_a_a_code_far_from_any_number_is_not_evidence():
    html = ("<html><body><p>Prices shown exclude delivery.</p>"
            "<footer>All AED transactions are processed in the UAE.</footer>"
            "</body></html>")
    assert ev(html) is None


def test_a_two_distinct_adjacent_codes_abstain():
    """The spinneyslebanon shape: an exchange-rate line naming two currencies.
    There is no right answer, and abstaining keeps rung 4 available."""
    html = ("<html><body><div>1.00 USD = 89,700 LBP</div>"
            "<div>Orange juice 30000 LBP</div></body></html>")
    assert ev(html) is None


@pytest.mark.parametrize("text", ["TOP 5", "ALL 12", "TRY 3", "5 TOP", "12 ALL"])
def test_a_english_word_codes_are_denied(text):
    """TOP / ALL / TRY are ordinary English words. Uncorroborated they are never
    evidence, and they never trigger the multiplicity abstention either."""
    assert ev("<html><body><p>%s</p></body></html>" % text) is None


def test_a_a_denied_code_does_not_suppress_a_real_one():
    """spacenk's "| TOP 100" sits next to a real price. Dropping TOP outright
    (rather than counting it toward multiplicity) is what lets the real code
    still be read."""
    html = ("<html><body><span>384 Reviews | TOP 100</span>"
            "<span>75.00 GBP</span></body></html>")
    assert ev(html) == "GBP"


def test_a_a_denied_code_is_admitted_on_a_second_machine_signal():
    """The denylist is not a blanket ban: a page that ALSO declares the code in a
    machine-readable microdata ``priceCurrency`` (which neither existing rung
    reads) has corroborated it, so it counts."""
    html = ('<html><body>'
            '<meta itemprop="priceCurrency" content="TRY">'
            '<span>8400 TRY</span></body></html>')
    assert ev(html) == "TRY"


@pytest.mark.parametrize("bad", [None, "", 0, 3.5, [], {}, object()])
def test_a_totality_never_raises(bad):
    assert ps._visible_text_currency_evidence(bad) is None


def test_a_totality_on_degenerate_documents():
    assert ev("<html>") is None
    assert ev("") is None
    assert ev("<html><body>" + ("x9, " * 400_000) + "</body></html>") is None


# ===========================================================================
# B — THE HIERARCHY. The new rung must stay BELOW the machine rungs.
# ===========================================================================
def test_b_og_currency_meta_still_wins_over_adjacent_text(monkeypatch):
    """bathandbodyworks.com.eg: og:price:currency EGP (truth EGP) while the
    visible text carries a cross-market "3 for AED 125" banner."""
    _rung(monkeypatch, "true")
    soup = soup_of("eg_bathandbodyworks_com_eg_og_egp_adjacent_aed.html")
    assert ps._visible_text_currency_evidence(soup) == "AED"
    assert ps._page_currency_evidence(soup) == "EGP"


def test_b_jsonld_pricecurrency_still_wins_over_adjacent_text(monkeypatch):
    """spacenk.com: JSON-LD priceCurrency GBP (truth GBP) while "| TOP 100"
    sits next to a number. Belt and braces — the denylist ALSO refuses TOP."""
    _rung(monkeypatch, "true")
    soup = soup_of("uk_spacenk_com_jsonld_gbp_adjacent_top.html")
    assert ps._visible_text_currency_evidence(soup) is None
    assert ps._page_currency_evidence(soup) == "GBP"


# ===========================================================================
# C — THE NAMED CORPUS PAGES. Five correct fires, one abstention, two decoys.
# ===========================================================================
@pytest.mark.parametrize("fixture,expected", [
    ("ae_faces_ae_brand_listing_adjacent_aed.html", "AED"),
    ("kw_ajmal_en_kwt_adjacent_kwd.html", "KWD"),
    ("kw_bloomingdales_com_kw_adjacent_kwd.html", "KWD"),
    ("qa_salams_com_adjacent_qar.html", "QAR"),
    ("kw_gcc_luluhypermarket_com_adjacent_kwd.html", "KWD"),
])
def test_c_the_five_correct_fires(fixture, expected):
    """Each of these pages returns None from _page_currency_evidence today and
    each agrees with the corpus-recorded page currency."""
    soup = soup_of(fixture)
    assert ps._page_currency_evidence(soup) is None
    assert ps._visible_text_currency_evidence(soup) == expected


def test_c_spinneyslebanon_abstains_on_two_codes():
    soup = soup_of("lb_spinneyslebanon_com_two_codes_abstain.html")
    assert ps._visible_text_currency_evidence(soup) is None


@pytest.mark.parametrize("fixture", [
    "ie_brownthomas_com_all_try_decoy.html",
    "us_solsticescents_com_all_decoy.html",
])
def test_c_the_english_word_decoys_never_fire(fixture):
    """These are exactly the pages a naive any-code-in-text rung gets wrong."""
    soup = soup_of(fixture)
    assert ps._page_currency_evidence(soup) is None
    assert ps._visible_text_currency_evidence(soup) is None


# ===========================================================================
# D — END TO END ON THE REAL faces.ae BYTES. The unit's reason to exist.
# ===========================================================================
def test_d_flag_off_shipped_mode_still_ships_the_bhd_mislabel(monkeypatch):
    """Pins TODAY. This test goes red the day someone repairs faces.ae another
    way, which is the point — the repair must be deliberate, not incidental."""
    _shipped_mode(monkeypatch)
    _rung(monkeypatch, "false")
    got = extract_price_from_html(
        load("ae_faces_ae_brand_listing_adjacent_aed.html"),
        "Tom Ford", "BHD", "faces.ae", FACES_URL)
    assert got is not None
    assert got["amount"] == 1515.0
    assert got["currency"] == "BHD"
    assert got["original_currency"] == "BHD"


def test_d_flag_on_labels_the_page_aed_and_the_price_converts(monkeypatch):
    """Once the page is read as AED the existing machinery does the rest: the
    price converts honestly at the FALLBACK_RATES table rate (offline, no
    network) and the provenance downgrades to ``converted_usd``.

    1515 AED -> 155.14 BHD. The shipped answer is 1515 "BHD" — a 9.76x
    over-price — so this single row is the whole unit."""
    _shipped_mode(monkeypatch)
    _rung(monkeypatch, "true")
    got = extract_price_from_html(
        load("ae_faces_ae_brand_listing_adjacent_aed.html"),
        "Tom Ford", "BHD", "faces.ae", FACES_URL)
    assert got is not None
    assert got["amount"] == 155.14
    assert got["currency"] == "BHD"
    assert got["original_currency"] == "AED"
    assert got["source_method"] == "converted_usd"


def test_d_flag_on_an_aed_ask_keeps_the_native_number(monkeypatch):
    """No conversion when the ask already IS the page's currency: the number is
    the page's own 1515 and the provenance stays ``page_scrape``."""
    _shipped_mode(monkeypatch)
    _rung(monkeypatch, "true")
    got = extract_price_from_html(
        load("ae_faces_ae_brand_listing_adjacent_aed.html"),
        "Tom Ford", "AED", "faces.ae", FACES_URL)
    assert got["amount"] == 1515.0
    assert got["currency"] == "AED"
    assert got["original_currency"] == "AED"
    assert got["source_method"] == "page_scrape"


@pytest.mark.parametrize("ask,converted", [
    ("BHD", 155.14), ("AED", 1515.0), ("SAR", 1546.72)])
def test_d_the_stamp_stops_following_the_ask(monkeypatch, ask, converted):
    """Flag OFF, the same 1515 is stamped BHD / AED / SAR according to the ASK —
    a 1.0 rate nothing measured. Flag ON, the page is read as AED and every ask
    gets the same money expressed in it."""
    _shipped_mode(monkeypatch)
    html = load("ae_faces_ae_brand_listing_adjacent_aed.html")
    _rung(monkeypatch, "false")
    off = extract_price_from_html(html, "Tom Ford", ask, "faces.ae", FACES_URL)
    assert (off["amount"], off["currency"], off["original_currency"]) == (
        1515.0, ask, ask)
    _rung(monkeypatch, "true")
    on = extract_price_from_html(html, "Tom Ford", ask, "faces.ae", FACES_URL)
    assert (on["amount"], on["currency"], on["original_currency"]) == (
        converted, ask, "AED")


@pytest.mark.parametrize("flag", ["false", "true"])
def test_d_a_size_qualified_query_is_rejected_in_both_modes(monkeypatch, flag):
    """The identity gate is untouched: a product-qualified query still finds no
    matching identity on a brand LISTING page."""
    _shipped_mode(monkeypatch)
    _rung(monkeypatch, flag)
    assert extract_price_from_html(
        load("ae_faces_ae_brand_listing_adjacent_aed.html"),
        "Tom Ford Oud Wood", "BHD", "faces.ae", FACES_URL) is None


def test_d_flag_off_is_byte_identical_at_the_rung(monkeypatch):
    """Flag OFF, _page_currency_evidence executes exactly its two pre-unit rungs
    and never consults the document text."""
    _rung(monkeypatch, "false")
    for fixture in ("ae_faces_ae_brand_listing_adjacent_aed.html",
                    "kw_ajmal_en_kwt_adjacent_kwd.html",
                    "qa_salams_com_adjacent_qar.html"):
        assert ps._page_currency_evidence(soup_of(fixture)) is None


def test_d_the_flag_is_read_per_call_never_cached_at_import(monkeypatch):
    """CLAUDE.md house rule 1 — Railway flips flags without a restart."""
    soup = soup_of("ae_faces_ae_brand_listing_adjacent_aed.html")
    _rung(monkeypatch, "false")
    assert ps._page_currency_evidence(soup) is None
    _rung(monkeypatch, "true")
    assert ps._page_currency_evidence(soup) == "AED"
    _rung(monkeypatch, "false")
    assert ps._page_currency_evidence(soup) is None


@pytest.mark.parametrize("off_value", ["", "false", "0", "no", "off", "FALSE", "Off"])
def test_d_the_off_spellings_match_the_other_flags(monkeypatch, off_value):
    monkeypatch.setenv("ENABLE_VISIBLE_TEXT_CURRENCY", off_value)
    assert ps.visible_text_currency_enabled() is False


@pytest.mark.parametrize("on_value", ["true", "1", "yes", "on", "TRUE", "On"])
def test_d_the_on_spellings_match_the_other_flags(monkeypatch, on_value):
    monkeypatch.setenv("ENABLE_VISIBLE_TEXT_CURRENCY", on_value)
    assert ps.visible_text_currency_enabled() is True


def test_d_the_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("ENABLE_VISIBLE_TEXT_CURRENCY", raising=False)
    assert ps.visible_text_currency_enabled() is False


# ===========================================================================
# E — WHAT MUST NOT MOVE. The sharafdg rule is rung 3 and it is correct.
# ===========================================================================
def test_e_a_silent_page_still_gets_the_ask_currency(monkeypatch):
    """bahrain.sharafdg.com publishes product:price:amount 244.990 with no
    currency anywhere. A page that says NOTHING is denominated in the currency
    the caller asked for — the rung must not disturb that."""
    _rung(monkeypatch, "true")
    soup = BeautifulSoup(
        '<html><body><span>244.990</span></body></html>', "html.parser")
    assert ps._page_currency_evidence(soup) is None
    assert ps._currency_label_for(None, "BHD", soup) == "BHD"


def test_e_a_present_but_unreadable_token_still_reaches_rung_4(monkeypatch):
    """Rung 4 (raw junk token, so strict_currency_label pends) must still be
    reachable when the rung abstains."""
    _rung(monkeypatch, "true")
    soup = BeautifulSoup(
        "<html><body><div>1.00 USD = 89,700 LBP</div></body></html>", "html.parser")
    assert ps._currency_label_for("د.ل", "BHD", soup) == "د.ل"

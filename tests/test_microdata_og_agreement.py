"""UNIT F2 — the nazih.qa regression: PROMOTED microdata must not outbid
OpenGraph when the two disagree.

WHAT BROKE. ``ENABLE_JSONLD_FIRST`` promotes ``_extract_microdata_price`` ABOVE
the OpenGraph branch. That branch's winner-selection rule is "prefer an
Offer-scoped price; among equals, the LARGER one", and the comment carrying it
(``price_service.py``, the ``key = (in_offer, amount)`` block) already named
nazih.qa as the known-latent weakness: the page publishes TEN
``itemprop=price`` nodes, every one of them wrapped in a
``schema.org/Offer`` itemscope, because the related-products RAIL emits a
hidden Product+Offer per card. The PDP's own Offer says 10 QAR; the rail runs
5 / 15 / 20 / 28 / 38 / 39 / 41.6 / 45. The max rule takes 45.

Latent is what it was, not what it is. OpenGraph used to run FIRST and cover
it. Promoted above OG, the rail price ships:

    base (8adaefb)            1.03 BHD / 10.0 QAR   via OpenGraph
    branch, flag ON, before   4.65 BHD / 45 QAR     via microdata   <- 4.5x

THE FIX, and why it is shaped like this. Measured over BOTH cached corpora
(414 pages, ``ENABLE_EXACT_PRICE_GATE=false``, every other flag at its shipped
default), ``_extract_microdata_price`` and ``_extract_og_price`` BOTH return a
price on **28** pages. On **27** of them they agree to the last cent —
relative difference exactly 0.0, not "close". The **one** page where they
diverge is nazih.qa, at 4.51x, and there the microdata pick is the wrong one.
niche-beauty.com was the second divergence when this unit was scoped; UNIT F1's
page-level currency evidence closed it (its currency-less Offer now reads EUR
from ``og:price:currency`` instead of defaulting), so post-F1 the two branches
agree there too and the corpus divergence count is 1 of 28.

So: on this corpus, agreement is the rule and disagreement is EVIDENCE AGAINST
MICRODATA — 1 for 1 here, 2 for 2 counting the pre-F1 niche-beauty state. The
guard therefore refuses the microdata winner when the page's own OG price
contradicts it and lets the cascade fall through to the OG branch, which is
exactly where the correct number was before the promotion.

TOLERANCE = 2%, and the number is deliberately loose. Nothing in the corpus
sits between 0% and 4.51%, so no measured page is anywhere near the line; the
band exists only to absorb representation noise a promotion must not be
brittle about — a ``content`` attribute rounded to two decimals against a
three-decimal GCC display value ("10.00" vs "10.000"), or a page that writes
the same money once with and once without a rounded fils tail. A tighter
number would buy nothing measurable and would start refusing microdata over
half a fils; a looser one would start admitting real 5%+ divergences.

WHERE THE GUARD LIVES, and why: inside ``_extract_microdata_price``, right
after the winner is chosen and BEFORE the currency conversion.

  * Before conversion, because that is the only place both numbers are still
    in the page's OWN denomination. After conversion the microdata amount is
    4.65 BHD while the OG tag still reads 10 QAR, and comparing those two
    requires a second rate lookup to say anything at all.
  * Inside the function rather than in the caller, because the caller has TWO
    call sites — the promoted one under ``if _first:`` and the legacy one
    below OpenGraph — and the guard is gated on the same ``jsonld_first_enabled()``
    that promotes the branch. Flag OFF, microdata runs BELOW OpenGraph, where a
    disagreement is not evidence of anything (OG already had its turn and
    declined), so the guard must not fire there. It cannot: the gate is the
    flag.

FAIL-OPEN, in three places, all deliberate. No OG price tag on the page, an OG
price that does not parse, or an OG price denominated in a DIFFERENT currency
than the microdata winner -> the guard does not fire and microdata keeps the
price. A disagreement between two different denominations is not a
disagreement about the amount, and the promotion's whole point (richer
availability, per-Offer scoping, real provenance) has to survive on the pages
where OG is silent.

Run per-file (the full suite hangs on live network):
    pytest tests/test_microdata_og_agreement.py \
        -m "not (live_unit or live_db or integration)" --timeout=120 \
        -p no:cacheprovider
"""

import os
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.services import price_service as ps
from app.services.price_service import extract_price_from_html

FIXTURES = Path(__file__).parent / "fixtures" / "jsonld_first"

NAZIH = "qa_nazih_qa_microdata_rail_outbids_og.html"
EPERFUMY_OFFER = "pl_eperfumy_pl_microdata_offer_scope.html"
KLINQ = "kw_klinq_com_kwd_price_converted_to_bhd.html"
NICHE = "de_niche_beauty_com_microdata_no_pricecurrency.html"

NAZIH_URL = "https://nazih.qa/diva-car-freshener-musky-scent-8ml.html"
NAZIH_NAME = "Diva Car Freshener Musky Scent 8ml"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def soup_of(name: str):
    return BeautifulSoup(load(name), "html.parser")


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """Default-ON is the shipped state; each test that needs OFF says so.
    ENABLE_EXACT_PRICE_GATE=false isolates EXTRACTION, the repo's documented
    mode for this (the gate rejects most cached pages, so everything would
    return None and the extraction bug would be invisible)."""
    monkeypatch.delenv("ENABLE_JSONLD_FIRST", raising=False)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    yield


def _first(monkeypatch, value: str):
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", value)


def nazih(currency: str):
    return extract_price_from_html(
        load(NAZIH), NAZIH_NAME, currency, "nazih.qa", NAZIH_URL,
    )


# ===========================================================================
# A — THE REGRESSION ITSELF
# ===========================================================================
def test_a_a_the_fixture_really_does_carry_the_rail_that_outbids():
    """Provenance check before any behaviour claim: the cut fixture keeps the
    PDP's own Offer (10 QAR) AND a rail node at 45 QAR, both verbatim, both
    inside a schema.org/Offer itemscope — which is what makes 45 beat 10 under
    the branch's max rule."""
    html = load(NAZIH)
    assert '<meta itemprop="price" content="10">' in html
    assert '<meta itemprop="price" content="45" />' in html
    assert '<meta property="product:price:amount" content="10"/>' in html
    assert '<meta property="product:price:currency" content="QAR"/>' in html


def test_a_b_the_rail_price_no_longer_outbids_opengraph(monkeypatch):
    """THE UNIT. Asked in BHD the JSON-LD branch hard-continues on the currency
    mismatch, so the cascade reaches the promoted microdata branch — which
    picks the 45 QAR rail item. The page's own product:price:amount says 10
    QAR. 45 is not 10, so microdata is refused and OpenGraph ships the price it
    shipped at 8adaefb: 10 QAR converted to 1.03 BHD."""
    _first(monkeypatch, "true")
    got = nazih("BHD")
    assert got is not None
    assert got["amount"] == 1.03, got
    assert got["original_currency"] == "QAR", got
    assert got["currency"] == "BHD", got
    assert got["source_method"] == "converted_usd", got


def test_a_c_the_native_currency_ask_is_the_jsonld_ten(monkeypatch):
    """Asked in QAR nothing changes and nothing should: the JSON-LD Offer
    matches the ask, so the authoritative branch answers before microdata is
    ever consulted. Pinned so the guard cannot be credited with — or blamed
    for — a number it never touched."""
    _first(monkeypatch, "true")
    got = nazih("QAR")
    assert got is not None
    assert got["amount"] == 10.0, got
    assert got["currency"] == "QAR", got
    assert got["source_method"] == "page_scrape", got
    assert got["confidence"] == 1.0, got


def test_a_d_the_number_45_is_gone_from_both_asks(monkeypatch):
    """The rail amount must not survive anywhere in the payload, converted or
    not: 45 QAR is 4.65 BHD."""
    _first(monkeypatch, "true")
    for currency, forbidden in (("BHD", 4.65), ("QAR", 45.0)):
        got = nazih(currency)
        assert got is not None
        assert got["amount"] != forbidden, (currency, got)


def test_a_e_flag_off_is_the_legacy_cascade_untouched(monkeypatch):
    """FLAG OFF (house rule 1). Microdata runs BELOW OpenGraph, so OG answers
    first and the guard is unreachable. These are the exact 8adaefb dicts."""
    _first(monkeypatch, "false")
    bhd = nazih("BHD")
    assert bhd == {
        "amount": 1.03, "original_currency": "QAR", "currency": "BHD",
        "retailer": "nazih.qa", "url": NAZIH_URL, "in_stock": None,
        "confidence": 0.9, "estimated": False, "source_method": "converted_usd",
    }, bhd
    qar = nazih("QAR")
    assert qar == {
        "amount": 10.0, "original_currency": "QAR", "currency": "QAR",
        "retailer": "nazih.qa", "url": NAZIH_URL, "in_stock": True,
        "confidence": 1.0, "estimated": False, "source_method": "page_scrape",
    }, qar


def test_a_f_flag_off_the_microdata_branch_still_picks_the_rail(monkeypatch):
    """The guard is gated on the promotion, not bolted onto the branch. Called
    directly with the flag OFF, ``_extract_microdata_price`` still returns the
    45 QAR rail winner — the legacy body, max rule and all. That is what makes
    the rollback a position rather than a behaviour change."""
    _first(monkeypatch, "false")
    got = ps._extract_microdata_price(soup_of(NAZIH), "QAR", "nazih.qa", NAZIH_URL)
    assert got is not None
    assert got["amount"] == 45.0, got


# ===========================================================================
# B — THE PROMOTION HAS TO SURVIVE
# ===========================================================================
def test_b_a_a_page_with_no_og_price_still_takes_the_microdata_price(monkeypatch):
    """eperfumy.pl (global corpus) publishes an Offer-scoped
    ``itemprop=price content="310"`` with ``priceCurrency PLN`` and NO OG or
    product price meta at all. The guard has nothing to compare against and
    must fail OPEN — the promotion is the point."""
    _first(monkeypatch, "true")
    assert 'property="og:price:amount"' not in load(EPERFUMY_OFFER)
    assert 'property="product:price:amount"' not in load(EPERFUMY_OFFER)
    got = extract_price_from_html(
        load(EPERFUMY_OFFER), "Paco Rabanne 1 Million Men Woda Toaletowa 200ml",
        "PLN", "eperfumy.pl", "https://eperfumy.pl/pl/x.html",
    )
    assert got is not None
    assert got["amount"] == 310.0, got
    assert got["currency"] == "PLN", got


def test_b_b_agreement_keeps_microdata_and_its_richer_provenance(monkeypatch):
    """klinq.com publishes the SAME 38.5 KWD in a ``product:price:amount`` meta
    and in a microdata Offer. They agree, so microdata keeps the price — which
    is the whole reason the branch was promoted: it reads the Offer's own
    availability and confidence rather than a page-global meta. ``confidence``
    0.8 is the microdata branch's signature; the OG branch stamps 0.9."""
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(KLINQ), "Miss Dior EDP", "KWD", "klinq.com",
        "https://klinq.com/en/dior-miss-dior-edp.html",
    )
    assert got is not None
    assert got["amount"] == 38.5, got
    assert got["currency"] == "KWD", got
    assert got["confidence"] == 0.8, got


def test_b_c_niche_beauty_agrees_post_f1_and_keeps_microdata(monkeypatch):
    """niche-beauty.com is the page UNIT F1 fixed: a currency-LESS microdata
    Offer of 195.00 beside ``og:price:currency EUR``. F1's page-level evidence
    labels the Offer EUR, so both branches now read 195 EUR and the guard sees
    agreement. Pinned here because this page was the SECOND divergence when
    this unit was scoped — it is no longer one, and that must not silently
    regress into a guard firing on it.

    ``confidence`` is 0.6 = the microdata branch's 0.8 taken down by the
    visible-text cross-check (the page prints the shelf price as "195,-", which
    does not confirm 195.00). The OG branch's 0.9 would come out as 0.675 —
    still a different number, so the assertion still names the branch."""
    _first(monkeypatch, "true")
    got = extract_price_from_html(
        load(NICHE), "Borntostandout Cola Addict", "EUR", "niche-beauty.com",
        "https://www.niche-beauty.com/de-de/produkte/borntostandout-cola-addict/752-052",
    )
    assert got is not None
    assert got["amount"] == 195.0, got
    assert got["currency"] == "EUR", got
    assert got["confidence"] == 0.6, got
    assert got["price_confirmed_in_text"] is False, got


# ===========================================================================
# C — THE TOLERANCE, AS A PURE PREDICATE
# ===========================================================================
def test_c_a_the_tolerance_is_two_percent_and_it_is_a_named_constant():
    assert ps._MICRODATA_OG_TOLERANCE == 0.02


@pytest.mark.parametrize(
    "micro, og, agree",
    [
        (10.0, 10.0, True),        # the 27-of-28 corpus case: exact
        (100.0, 98.0, True),       # exactly 2% apart - the band is INCLUSIVE
        (98.0, 100.0, True),       # ...and symmetric
        (100.0, 97.9, False),      # 2.1% - refused
        (10.0, 10.15, True),       # 1.48%: a rounded fils tail, not a decoy
        (45.0, 10.0, False),       # nazih.qa
        (195.0, 178.83, False),    # the pre-F1 niche-beauty divergence
    ],
)
def test_c_b_the_band_is_relative_and_symmetric(micro, og, agree):
    assert ps._amounts_agree(micro, og) is agree


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_c_c_a_degenerate_amount_never_makes_the_guard_fire(bad):
    """Fail-open on anything that cannot support a ratio. A guard must never be
    the thing that costs a real price."""
    assert ps._amounts_agree(10.0, bad) is True
    assert ps._amounts_agree(bad, 10.0) is True


# ===========================================================================
# D — WHAT THE GUARD READS OUT OF THE PAGE
# ===========================================================================
def test_d_a_it_reads_the_same_tag_the_og_branch_would():
    """``_og_price_for_agreement`` is a read-only mirror of the OG branch's tag
    precedence. On nazih.qa that is ``product:price:amount`` (the page carries
    no ``og:price:amount``), and the label comes back ISO-resolved."""
    got = ps._og_price_for_agreement(soup_of(NAZIH), "BHD", load(NAZIH), NAZIH_URL)
    assert got == (10.0, "QAR"), got


def test_d_b_a_page_with_no_og_price_reads_as_no_evidence():
    assert ps._og_price_for_agreement(
        soup_of(EPERFUMY_OFFER), "PLN", load(EPERFUMY_OFFER),
        "https://eperfumy.pl/pl/x.html",
    ) is None


def test_d_c_a_currency_less_og_tag_takes_the_expected_currency():
    """klinq.com publishes ``product:price:amount 38.5`` with no currency meta.
    That is the sharafdg rung of ``_currency_label_for``: a SILENT page takes
    the expected currency."""
    got = ps._og_price_for_agreement(
        soup_of(KLINQ), "KWD", load(KLINQ), "https://klinq.com/en/x.html",
    )
    assert got == (38.5, "KWD"), got


def test_d_d_a_disagreement_in_a_DIFFERENT_currency_is_not_evidence(monkeypatch):
    """FAIL-OPEN. Rewrite the nazih rail node to declare USD: the microdata
    winner is then 45 USD against an OG tag of 10 QAR. Those two numbers are
    not in disagreement about anything — they are different money — so the
    guard must not fire and microdata keeps the price."""
    _first(monkeypatch, "true")
    html = load(NAZIH).replace(
        '<meta itemprop="price" content="45" />\n'
        '            <meta itemprop="priceCurrency" content="QAR" />',
        '<meta itemprop="price" content="45" />\n'
        '            <meta itemprop="priceCurrency" content="USD" />',
    )
    assert 'content="USD"' in html
    soup = BeautifulSoup(html, "html.parser")
    got = ps._extract_microdata_price(soup, "USD", "nazih.qa", NAZIH_URL, html)
    assert got is not None
    assert got["amount"] == 45.0, got
    assert got["original_currency"] == "USD", got


def test_d_e_the_guard_is_total(monkeypatch):
    """A guard that raises is worse than no guard. Hostile / empty documents
    must all come back "no evidence", never an exception."""
    _first(monkeypatch, "true")
    for markup in ("", "<html></html>", "<meta property='product:price:amount'>",
                   '<meta property="og:price:amount" content="not a number">',
                   '<meta property="og:price:amount" content="0">'):
        soup = BeautifulSoup(markup, "html.parser")
        assert ps._og_price_for_agreement(soup, "BHD", markup, "https://x.test/p") is None


def test_d_f_the_predicate_never_raises_on_a_hostile_document(monkeypatch):
    _first(monkeypatch, "true")
    soup = BeautifulSoup("<html><body>x</body></html>", "html.parser")
    assert ps._microdata_og_agreement_ok(
        10.0, "QAR", soup, "BHD", "<html></html>", "https://x.test/p",
    ) is True


# ===========================================================================
# E — THE CASCADE STILL FALLS THROUGH, IT DOES NOT PEND
# ===========================================================================
def test_e_a_refusing_microdata_hands_the_page_to_a_real_price_not_to_none(monkeypatch):
    """The invariant this pins is "the guard must NEVER turn a real page into a
    pend". Post-M13-40 the BHD ask on nazih is answered by the JSON-LD
    foreign-currency pass — the SAME authoritative 10 QAR Offer that answers the
    QAR ask (test_a_c), converted to 1.03 BHD and labelled converted_usd at
    confidence 1.0 — rather than by the OG fallback it fell to before M13-40. The
    amount is unchanged (1.03 BHD, the PDP's own Offer, NOT the 45 QAR rail), the
    page still yields a real price, and the source is now the authoritative
    JSON-LD one. The microdata->OG handoff itself still runs on the flag-OFF
    cascade (test_a_e pins the legacy OG dict at confidence 0.9)."""
    _first(monkeypatch, "true")
    got = nazih("BHD")
    assert got is not None, "the guard must never turn a real page into a pend"
    assert got["amount"] == 1.03, got
    assert got["currency"] == "BHD", got
    assert got["source_method"] == "converted_usd", got
    assert got["confidence"] == 1.0, got  # JSON-LD (M13-40), was OG 0.9 pre-fix

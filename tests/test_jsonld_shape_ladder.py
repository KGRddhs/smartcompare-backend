"""ENABLE_JSONLD_SHAPE_LADDER (default ON) — the JSON-LD shape ladder.

WHAT THIS WAVE ITEM FIXES, measured, not asserted from the brief.

The brief that opened this item named five defects. Two of them do not exist in
the code and one does not exist in the corpus; they are pinned here as
REGRESSION tests (block E) rather than re-implemented, and the report says so.
What IS real, re-measured over the 328-row / 163-host global corpus by running
``extract_jsonld_price`` against the cached bytes with
``ENABLE_EXACT_PRICE_GATE=false`` (extraction isolated, the repo's documented
mode for this):

  * 322 cached pages resolve to a file; 124 yielded a price, 198 did not.
  * Of the 198, **150 carry no usable JSON-LD product shape at all** (the page
    is a bot wall or the price is client-rendered) — no ladder can help them.
  * **32 pages carry a top-level (or @graph-wrapped) ``ProductGroup`` whose
    Products live in ``hasVariant``**, which ``@type == "Product"`` never
    matched. That is the single biggest real cause, and it is 3.5x the "9
    pages" the brief estimated. Hosts: kicks.se 3, matas.dk 3, escentual.com 3,
    parfumdreams.de 2, lookfantastic.com 2, spacenk.com 2, microperfumes.com 2,
    scentsplit.com 2, luckyscent.com 2, sephora.com 2, marionnaud.fr 2,
    iciparisxl.be 2, arenal.com 1, fenwick.co.uk 1, jomalone.co.uk 1,
    olfactif.com 1.
  * **2 pages** (marksandspencer.com x2) put the money in
    ``offers.priceSpecification.price`` with the ``priceCurrency`` there too and
    NOT on the Offer, so both the price lookup and the currency gate missed.
  * **3 pages** (theperfumeshop.com x3) nest a LIST inside ``@graph``
    (``@graph: [BreadcrumbList, [ProductGroup, Product, ...]]``). HEAD iterated
    ``data["@graph"]`` requiring each item to be a dict, so the nested list was
    skipped whole. This one is not in the brief at all — it fell out of the
    measurement.

MEASURED RESULT of the ladder over those same cached bytes, with the query
taken from each page's own og:title (so mostly UNQUALIFIED — the harshest
case). Shipped configuration (exact gate ON): **+10 pages priced, -9 pended,
0 amounts changed**. Extraction-isolated (gate OFF): +14 / -15 / 0. Every one
of the pends is a page where HEAD was returning the CHEAPEST of several
contradictory prices (perfume.com 2.81, fragrancex 19.99, indigoperfumery 4.00
beside a 60.00 bottle), so the pends are the correctness half of this change,
not a coverage loss. Re-run with a SIZE-QUALIFIED query — what a real fragrance
compare sends — **23 of the 32 ProductGroup pages resolve to the EXACT variant
price, 0 mis-selections**; 5 pend explicitly (sephora x2 sizeless, lookfantastic
x2 duplicate-named, olfactif gender variants) and 4 carry no price in the page
currency at all.

Flag OFF is byte-identical: the full 322-page extraction record hashes to the
same sha256 as HEAD's, in BOTH exact-gate modes.

AND THE HARD PART, also re-measured. 15 of the 124 pages that DO yield a price
carry MORE THAN ONE distinct identity-matched amount, and on every one of them
HEAD returns the CHEAPEST: perfume.com 2.81 of {2.81 ... 24.91} for a full
bottle of Pink Sugar, fragrancex 19.99 of {19.99 ... 130.43} for Sauvage,
notino.co.uk 51.42 when the page's own default is 74.88. Adding the 32
ProductGroup pages adds more of the same shape (luckyscent lists a $5 1ml decant
beside the $195 100ml bottle). Multiplicity is therefore made an EXPLICIT
outcome here, never a silent pick — see block C for the rule and its
justification.

Run per-file (the full suite hangs on live network):
    pytest tests/test_jsonld_shape_ladder.py \
        -m "not (live_unit or live_db or integration)" --timeout=120
"""

import json
import os
from pathlib import Path

import pytest

from app.services import price_service as ps
from app.services.price_service import _is_product_type, extract_jsonld_price

FIXTURES = Path(__file__).parent / "fixtures" / "shapes"


# ---------------------------------------------------------------------------
# Helpers. Every fixture under tests/fixtures/shapes/ is CUT FROM REAL CACHED
# BYTES in _proof/global/html/ — each file is that page's own
# application/ld+json blocks plus its own og/product price meta tags and title.
# Provenance (source URL, host, country, cache filename, page sha1) is recorded
# in tests/fixtures/shapes/SOURCES.json.
# ---------------------------------------------------------------------------
def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _ladder_on(monkeypatch):
    """Default-ON is the shipped state; each test that needs OFF says so."""
    monkeypatch.delenv("ENABLE_JSONLD_SHAPE_LADDER", raising=False)
    yield


def _gate(monkeypatch, value: str):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", value)


def _ladder(monkeypatch, value: str):
    monkeypatch.setenv("ENABLE_JSONLD_SHAPE_LADDER", value)


# ===========================================================================
# A — THE LADDER REACHES THE NODE THE MONEY IS ON
# ===========================================================================
def test_a_a_productgroup_single_variant_now_yields_its_price(monkeypatch):
    """escentual.com ?country=GB. The whole document is ONE top-level
    ``ProductGroup`` with a single ``hasVariant`` member priced 275.00 GBP.
    There is no ``@type == "Product"`` node anywhere, so HEAD returned None and
    a real, unambiguous, in-stock shelf price was lost."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("gb_shopify_escentual_com_productgroup_single_variant.html"),
        "Initio", "GBP", "Initio Wild Rush Eau de Parfum 90ml",
    )
    assert got is not None
    assert got["amount"] == 275.0
    assert got["currency"] == "GBP"


def test_a_b_graph_wrapped_productgroup_resolves_the_queried_size(monkeypatch):
    """marionnaud.fr — ``@graph`` -> ProductGroup -> hasVariant[30ML/50mL/75ML]
    at 49 / 127.5 / 152 EUR. Two rungs at once: the @graph unwrap (which HEAD
    already had) and the hasVariant descent (which it did not)."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("fr_hybris_marionnaud_fr_graph_productgroup_3_sizes.html"),
        "Chloe", "EUR", "Chloe Nomade Eau de Parfum 50ml",
    )
    assert got is not None
    assert got["amount"] == 127.5


def test_a_c_the_same_shape_in_another_currency(monkeypatch):
    """marionnaud.ch, CHF 64.3 / 113.1 / 154.7 across 30/50/100 ML. Pins that
    the descent is not accidentally keyed on anything EUR- or FR-specific.

    The query carries the page's own spelling, "Lancôme". An unaccented
    "Lancome" query does NOT match this page — the brand gate is a plain
    substring test over ``name.lower().replace(" ", "")`` with no diacritic
    fold, so "lancome" is not in "lancômelavieestbelle...". That gap is
    PRE-EXISTING (it is the same gate on the flat-Product path and it predates
    this branch), it is not a shape problem, and fixing it here would have
    hidden whether the descent works. It is reported as a separate finding."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("ch_hybris_marionnaud_ch_graph_productgroup_3_sizes.html"),
        "Lancôme", "CHF", "Lancôme La Vie est Belle L'Elixir Very Cherry 50ml",
    )
    assert got is not None
    assert got["amount"] == 113.1


def test_a_d_a_variant_inherits_the_group_brand_it_does_not_declare(monkeypatch):
    """sephora.com Sauvage Elixir. Every ``hasVariant`` member is named bare
    "Sauvage Elixir" and declares NO brand; only the enclosing ProductGroup
    carries ``brand.name = "DIOR"``. Without inheritance the brand gate drops
    all three variants and the descent buys nothing. Proven through the pend
    channel, because this page is also the block-C ambiguity case."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load("us_sephora_com_productgroup_sizeless_variants.html"),
        "Dior", "USD", "Dior Sauvage Elixir 60ml", pending_out=pending,
    )
    assert got is None
    assert len(pending) == 1
    assert sorted(c["amount"] for c in pending[0]) == [199.0, 265.0, 330.0]


def test_a_e_pricespecification_price_is_read_when_the_offer_has_none(monkeypatch):
    """marksandspencer.com. The Offer carries neither ``price`` NOR
    ``priceCurrency``; both live on ``offers.priceSpecification``
    (UnitPriceSpecification, 28.8 GBP). HEAD failed the currency gate first and
    would have found no price after it, so BOTH lookups had to move."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("gb_mands_com_pricespecification_only_offer.html"),
        "Fragonard", "GBP", "Fragonard Rose de Mai Eau de Toilette 100ml",
    )
    assert got is not None
    assert got["amount"] == 28.8
    assert got["currency"] == "GBP"


def test_a_f_a_string_price_is_read_through_the_canonical_money_parser(monkeypatch):
    """spacenk.com writes its variant prices as STRINGS ("225.00"). The corpus
    carries no string price with an embedded symbol and none with a comma
    decimal, so ``float()`` happened to work — but the ladder routes strings
    through ``parse_money`` (BLOCKER 6's one canonical parser) so the first
    comma-decimal ProductGroup we meet is not a 100x. Same answer here."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("gb_spacenk_com_productgroup_size_field.html"),
        "Byredo", "GBP", "Byredo Young Rose Eau de Parfum 50ml",
    )
    assert got is not None
    assert got["amount"] == 155.0


def test_a_g_a_list_nested_inside_graph_is_walked(monkeypatch):
    """theperfumeshop.com — a THIRD shape, found by measurement rather than by
    the brief. Its block is ``@graph: [BreadcrumbList, [ProductGroup, Product,
    Product, Product]]``: a LIST nested inside @graph. HEAD iterated
    ``data["@graph"]`` and required each item to be a ``dict``, so the nested
    list was skipped whole and three cached pages lost a price that was sitting
    in plain sight. A uniform walk costs nothing and catches it. The 30ML
    variant is 30.00 GBP."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("gb_hybris_theperfumeshop_com_graph_nested_list.html"),
        "DKNY", "GBP", "DKNY Be Delicious Eau de Parfum Spray 30ML",
    )
    assert got is not None
    assert got["amount"] == 30.0


def test_a_h_rung_5_parses_float_first_and_the_money_parser_only_as_fallback(
    monkeypatch,
):
    """The ORDER inside rung 5, pinned, because getting it backwards silently
    broke two of this branch's own rollback levers.

    ``parse_money`` is canonical for MONEY TEXT, not for a JSON number literal:
    it strips the exponent out of "1e400" and reads 1.0. ``float()`` reads inf,
    which is what ``ENABLE_HOSTILE_NUMERIC_GUARD`` exists to catch — so
    ``float()`` runs FIRST and every value it already read keeps its exact
    legacy value. ``parse_money`` then rescues only the strings ``float()``
    REJECTS, which is the whole comma-decimal 100x family and is pure gain:
    today those offers are dropped."""
    _gate(monkeypatch, "false")

    def price(raw):
        node = {"@context": "https://schema.org", "@type": "Product",
                "name": "Dior Sauvage Eau de Toilette 100ml",
                "brand": {"@type": "Brand", "name": "Dior"},
                "offers": {"@type": "Offer", "price": raw, "priceCurrency": "GBP",
                           "availability": "https://schema.org/InStock"}}
        got = extract_jsonld_price(_wrap(node), "Dior", "GBP",
                                   "Dior Sauvage Eau de Toilette 100ml")
        return got["amount"] if got else None

    # float() reads it -> the hostile-numeric guard still sees inf and drops it.
    monkeypatch.setenv("ENABLE_HOSTILE_NUMERIC_GUARD", "true")
    assert price("1e400") is None
    # ... and with that guard rolled back, the legacy inf comes through, which
    # is only true because parse_money never got to read 1.0 out of it.
    monkeypatch.setenv("ENABLE_HOSTILE_NUMERIC_GUARD", "false")
    assert price("1e400") == float("inf")
    monkeypatch.delenv("ENABLE_HOSTILE_NUMERIC_GUARD", raising=False)

    # Unchanged for everything float() already read.
    assert price("199.00") == 199.0
    assert price(275.0) == 275.0
    # Rescued: float() raises on all three, so HEAD drops the offer entirely.
    assert price("320,00") == 320.0
    assert price("1.234,56") == 1234.56
    assert price("1,234.56") == 1234.56


def test_a_i_the_comma_decimal_rescue_is_the_ladders_alone(monkeypatch):
    """Same strings with the ladder OFF: dropped, exactly as HEAD drops them.
    This is what makes the rescue additive rather than a re-reading."""
    _gate(monkeypatch, "false")
    _ladder(monkeypatch, "false")
    node = {"@context": "https://schema.org", "@type": "Product",
            "name": "Dior Sauvage Eau de Toilette 100ml",
            "brand": {"@type": "Brand", "name": "Dior"},
            "offers": {"@type": "Offer", "price": "320,00", "priceCurrency": "GBP",
                       "availability": "https://schema.org/InStock"}}
    assert extract_jsonld_price(_wrap(node), "Dior", "GBP",
                                "Dior Sauvage Eau de Toilette 100ml") is None


# ===========================================================================
# B — THE RIGHT OFFER: NEVER THE FIRST, NEVER THE CHEAPEST
# ===========================================================================
def test_b_a_a_sized_query_takes_the_dearest_variant_when_that_is_the_match(monkeypatch):
    """luckyscent.com L'Eau Papier — 50ml $145 (FIRST), 100ml $195 (DEAREST),
    "1ml spray" $5 (CHEAPEST, a decant decoy). A 100ml query must return 195.0.
    First-wins would give 145, cheapest-wins would give 5. This single page
    falsifies both of the rules the extractor could have been given."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("us_luckyscent_com_productgroup_decant_decoy.html"),
        "Diptyque", "USD", "Diptyque L'Eau Papier Eau de Toilette 100ml",
    )
    assert got is not None
    assert got["amount"] == 195.0


def test_b_b_a_sized_query_skips_the_pages_own_default_variant(monkeypatch):
    """kicks.se lists the PDP's own default first ("...50 ml 50 ml", 1119 SEK)
    and the 90 ml at 1509 SEK last. A 90 ml query must return 1509.0 — not the
    page's default, not the 769 SEK 30 ml."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("se_kicks_se_productgroup_size_in_name.html"),
        "Armani", "SEK", "Armani My Way Eau de Parfum 90 ml",
    )
    assert got is not None
    assert got["amount"] == 1509.0


def test_b_c_the_size_field_resolves_when_the_name_carries_no_size(monkeypatch):
    """matas.dk — 100 ml default 1059.00 DKK first, 50 ml 759.95 DKK second.
    A 50 ml query takes the second member."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("dk_matas_dk_productgroup_two_sizes.html"),
        "Burberry", "DKK", "Burberry Hero Eau de Parfum 50 ml",
    )
    assert got is not None
    assert got["amount"] == 759.95


def test_b_d_a_size_the_page_does_not_stock_pends_it_does_not_substitute(monkeypatch):
    """The other half of the size rule. marionnaud.fr stocks 30/50/75 ML. A
    100ml query must NOT be answered with the 75ML price (or any other) — the
    page does not sell what was asked for."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load("fr_hybris_marionnaud_fr_graph_productgroup_3_sizes.html"),
        "Chloe", "EUR", "Chloe Nomade Eau de Parfum 100ml", pending_out=pending,
    )
    assert got is None
    assert sorted(c["amount"] for c in pending[0]) == [49.0, 127.5, 152.0]


# ===========================================================================
# C — MULTIPLICITY IS AN EXPLICIT OUTCOME
#
# THE RULE, and why each rung is where it is:
#   1. ONE distinct identity-matched amount  -> return it. No ambiguity exists,
#      so nothing changes for the overwhelming majority of pages.
#   2. the query names a size AND exactly one distinct amount survives the size
#      filter -> return that. This is the documented fragrance rule: a
#      size-qualified query selects the matching size.
#   3. anything else -> PEND. Hand the caller the candidates and return None.
#      NEVER the cheapest (the documented authority-not-cheapest principle:
#      every one of the 15 measured HEAD multiplicities returned the cheapest,
#      and on perfume.com / fragrancex / luckyscent the cheapest is a 1-2ml
#      decant, not the bottle). NEVER the first either — "first" is document
#      order, which asserts nothing; sephora.com's first variant is the 199 and
#      lookfantastic's is the 80, and neither page marks a default.
#
# The pend channel is an OPT-IN out-parameter, deliberately. extract_jsonld_price
# has three call sites, one of which does `price_data["amount"]` immediately
# after `if price_data:` — returning an amount-less dict would KeyError there.
# Returning None means every existing caller pends exactly as it already does
# when no price is found, while a caller that wants the candidates asks for them.
# ===========================================================================
def test_c_a_sizeless_variants_pend_and_hand_back_every_candidate(monkeypatch):
    """sephora.com Sauvage Elixir: three variants, three SKUs, three prices
    (199 / 265 / 330 USD), all named "Sauvage Elixir", none carrying a size or
    any default marker. Nothing on the page can resolve which one a query
    means. That is a pend, and the candidates come back so the caller can say
    so."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load("us_sephora_com_productgroup_sizeless_variants.html"),
        "Dior", "USD", "Dior Sauvage Elixir", pending_out=pending,
    )
    assert got is None
    assert len(pending) == 1
    assert sorted(c["amount"] for c in pending[0]) == [199.0, 265.0, 330.0]
    assert all(c["currency"] == "USD" for c in pending[0])


def test_c_b_duplicate_named_variants_pend(monkeypatch):
    """lookfantastic.com Le Male EDT 75ml: FOUR hasVariant members with the
    byte-identical name "Jean Paul Gaultier Le Male Eau de Toilette 75ml" at 80
    / 59.2 / 20 / 55 GBP. Even a fully size-qualified query cannot separate
    them — the size filter leaves four amounts standing, so rung 2 does not
    fire and rung 3 does."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load("gb_thg_lookfantastic_com_productgroup_duplicate_names.html"),
        "Jean", "GBP", "Jean Paul Gaultier Le Male Eau de Toilette 75ml",
        pending_out=pending,
    )
    assert got is None
    assert sorted(c["amount"] for c in pending[0]) == [20.0, 55.0, 59.2, 80.0]


def test_c_c_a_multi_offer_product_no_longer_silently_takes_the_cheapest(monkeypatch):
    """notino.co.uk ships ONE Product with an ``offers`` ARRAY of four prices
    (74.88 / 51.42 / 88.1 / 60.5 GBP) and nothing marking a default; the
    corpus's own survey recorded 74.88, the FIRST. HEAD (gate off) returned
    51.42 — the cheapest, which is neither. This is the multiplicity rule
    reaching a plain Offer array, not only a ProductGroup."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load("gb_notino_co_uk_offers_array_four_prices.html"),
        "Acqua", "GBP", "Acqua dell' Elba Arcipelago Women eau de parfum",
        pending_out=pending,
    )
    assert got is None
    assert sorted(c["amount"] for c in pending[0]) == [51.42, 60.5, 74.88, 88.1]


def test_c_d_the_pend_channel_is_opt_in_so_existing_callers_just_get_none(monkeypatch):
    """The three existing call sites pass no ``pending_out``. They must get a
    plain None — the same value they already get when a page has no JSON-LD at
    all — and nothing may raise."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("us_sephora_com_productgroup_sizeless_variants.html"),
        "Dior", "USD", "Dior Sauvage Elixir",
    )
    assert got is None


def test_c_e_an_unambiguous_page_never_touches_the_pend_channel(monkeypatch):
    """Rung 1. One distinct amount -> the list stays empty, so a caller can
    tell "we could not choose" apart from "there was nothing to choose"."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load("gb_hybris_superdrug_com_graph_product_single_offer.html"),
        "Paco", "GBP", "Paco Rabanne Lady Million Eau My Gold EDT 80ml",
        pending_out=pending,
    )
    assert got is not None and got["amount"] == 30.0
    assert pending == []


def test_c_g_availability_resolves_what_size_cannot(monkeypatch):
    """Rung 3. One product, two offers, no size difference — but the page itself
    says one is OutOfStock. That is not an ambiguity, it is one purchasable
    price and one that is not, so it resolves rather than pends. (The mirror of
    this — narrowing by stock must run AFTER the size rung, so a 100ml query is
    never answered with the in-stock 50ml — is pinned by test_b_d.)"""
    _gate(monkeypatch, "false")
    node = {
        "@context": "https://schema.org", "@type": "Product",
        "name": "Dior Sauvage Eau de Toilette 100ml",
        "brand": {"@type": "Brand", "name": "Dior"},
        "offers": [
            {"@type": "Offer", "price": "25", "priceCurrency": "GBP",
             "availability": "https://schema.org/OutOfStock"},
            {"@type": "Offer", "price": "40", "priceCurrency": "GBP",
             "availability": "https://schema.org/InStock"},
        ],
    }
    got = extract_jsonld_price(_wrap(node), "Dior", "GBP",
                              "Dior Sauvage Eau de Toilette 100ml")
    assert got is not None and got["amount"] == 40.0


def test_c_h_two_in_stock_prices_for_one_sku_pend_in_the_rollback_combination(
    monkeypatch,
):
    """THE COMPOSITE this file owns, moved here out of
    tests/test_sale_price_precedence.py so that file stays a ONE-flag rollback
    pin. theperfumeshop.com ships an EU-Omnibus was-price of 24.99 BELOW its
    29.99 shelf price, marked priceType=StrikethroughPrice. With
    ENABLE_SALE_PRICE_FIRST ON (the shipped default) the was-price is never a
    candidate and 29.99 wins. Roll THAT flag back and the page carries two
    distinct in-stock prices for one 90ML product with nothing marking a
    default — so the ladder pends instead of handing back the 24.99 the legacy
    cheapest-pick produced. Two rollback levers, and the safer one wins."""
    _gate(monkeypatch, "false")
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "false")
    html = (Path(__file__).parent / "fixtures" / "sale_price"
            / "uk_theperfumeshop_com_second_offer_omnibus_low.html"
            ).read_text(encoding="utf-8")
    query = "Lacoste Touch Of Pink Eau de Toilette Spray 90ml"
    pending = []
    got = extract_jsonld_price(html, "Lacoste", "GBP", query, pending_out=pending)
    assert got is None
    assert sorted(c["amount"] for c in pending[0]) == [24.99, 29.99]

    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
    assert extract_jsonld_price(html, "Lacoste", "GBP", query)["amount"] == 29.99


def test_c_f_the_no_query_legacy_path_is_left_alone(monkeypatch):
    """``structured_comparison_service`` calls this with NO query_name at all
    (the pre-S4 contract, documented in the function as the legacy
    cheapest-pick). With no identity to gate on there is nothing to adjudicate
    against, so that path keeps ``min(amount)`` in both flag states rather than
    pending every multi-offer page in a caller that never asked."""
    _gate(monkeypatch, "false")
    html = load("gb_notino_co_uk_offers_array_four_prices.html")
    assert extract_jsonld_price(html, "Acqua", "GBP")["amount"] == 51.42


# ===========================================================================
# D — FLAG OFF IS HEAD, EXACTLY
# ===========================================================================
_HEAD_TABLE = [
    # (fixture, brand, currency, query, HEAD amount gate-off, HEAD amount gate-on)
    ("gb_shopify_escentual_com_productgroup_single_variant.html", "Initio", "GBP",
     "Initio Wild Rush Eau de Parfum 90ml", None, None),
    ("fr_hybris_marionnaud_fr_graph_productgroup_3_sizes.html", "Chloe", "EUR",
     "Chloe Nomade Eau de Parfum 50ml", None, None),
    ("ch_hybris_marionnaud_ch_graph_productgroup_3_sizes.html", "Lancôme", "CHF",
     "Lancôme La Vie est Belle L'Elixir Very Cherry 50ml", None, None),
    ("us_sephora_com_productgroup_sizeless_variants.html", "Dior", "USD",
     "Dior Sauvage Elixir 60ml", None, None),
    ("gb_thg_lookfantastic_com_productgroup_duplicate_names.html", "Jean", "GBP",
     "Jean Paul Gaultier Le Male Eau de Toilette 75ml", None, None),
    ("gb_mands_com_pricespecification_only_offer.html", "Fragonard", "GBP",
     "Fragonard Rose de Mai Eau de Toilette 100ml", None, None),
    ("se_kicks_se_productgroup_size_in_name.html", "Armani", "SEK",
     "Armani My Way Eau de Parfum 30 ml", None, None),
    ("gb_spacenk_com_productgroup_size_field.html", "Byredo", "GBP",
     "Byredo Young Rose Eau de Parfum 50ml", None, None),
    ("us_luckyscent_com_productgroup_decant_decoy.html", "Diptyque", "USD",
     "Diptyque L'Eau Papier 100ml", None, None),
    # Block H's decants page. (None, None) is load-bearing: with the ladder OFF
    # this ProductGroup yields NOTHING in either gate mode, so a rollback does
    # not restore the 250.0 bottle price — it loses the page altogether.
    ("us_shopify_scentsplit_com_productgroup_decants_and_bottle.html", "Xerjoff",
     "USD", "xerjoff ilm sample decants", None, None),
    ("gb_notino_co_uk_offers_array_four_prices.html", "Acqua", "GBP",
     "Acqua dell' Elba Arcipelago Women eau de parfum", 51.42, None),
    ("gb_hybris_superdrug_com_graph_product_single_offer.html", "Paco", "GBP",
     "Paco Rabanne Lady Million Eau My Gold EDT 80ml", 30.0, 30.0),
    ("dk_matas_dk_productgroup_two_sizes.html", "Burberry", "DKK",
     "Burberry Hero Eau de Parfum 50 ml", None, None),
    ("gb_hybris_theperfumeshop_com_graph_nested_list.html", "DKNY", "GBP",
     "DKNY Be Delicious Eau de Parfum Spray 30ML", None, None),
]


@pytest.mark.parametrize("gate_mode", ["false", "true"])
@pytest.mark.parametrize(
    "fixture,brand,currency,query,head_off,head_on",
    _HEAD_TABLE, ids=[c[0][:38] for c in _HEAD_TABLE],
)
def test_d_flag_off_is_head_on_every_shape_fixture(
    monkeypatch, gate_mode, fixture, brand, currency, query, head_off, head_on,
):
    """The rollback contract, pinned against the values HEAD actually produces
    on these bytes (captured before a line of the ladder was written), in BOTH
    exact-gate modes."""
    _gate(monkeypatch, gate_mode)
    _ladder(monkeypatch, "false")
    got = extract_jsonld_price(load(fixture), brand, currency, query)
    expected = head_off if gate_mode == "false" else head_on
    assert (got["amount"] if got else None) == expected


@pytest.mark.parametrize("ladder", ["true", "false"])
@pytest.mark.parametrize("gate_mode", ["false", "true"])
def test_d_b_the_single_offer_graph_page_is_untouched_in_all_four_modes(
    monkeypatch, gate_mode, ladder,
):
    """superdrug.com: @graph -> Product -> one Offer, 30 GBP. The single
    commonest working shape in the corpus must not move under any combination
    of the two flags."""
    _gate(monkeypatch, gate_mode)
    _ladder(monkeypatch, ladder)
    got = extract_jsonld_price(
        load("gb_hybris_superdrug_com_graph_product_single_offer.html"),
        "Paco", "GBP", "Paco Rabanne Lady Million Eau My Gold EDT 80ml",
    )
    assert got is not None and got["amount"] == 30.0


def test_d_c_the_flag_is_read_per_call_never_cached_at_import(monkeypatch):
    """CLAUDE.md house rule 1 — Railway flips flags without a restart."""
    _gate(monkeypatch, "false")
    html = load("gb_shopify_escentual_com_productgroup_single_variant.html")
    args = ("Initio", "GBP", "Initio Wild Rush Eau de Parfum 90ml")
    _ladder(monkeypatch, "false")
    assert extract_jsonld_price(html, *args) is None
    _ladder(monkeypatch, "true")
    assert extract_jsonld_price(html, *args)["amount"] == 275.0
    _ladder(monkeypatch, "false")
    assert extract_jsonld_price(html, *args) is None


@pytest.mark.parametrize("off_value", ["false", "0", "no", "off", "FALSE", "Off"])
def test_d_d_the_off_spellings_match_the_other_seven_flags(monkeypatch, off_value):
    _gate(monkeypatch, "false")
    monkeypatch.setenv("ENABLE_JSONLD_SHAPE_LADDER", off_value)
    assert ps.jsonld_shape_ladder_enabled() is False


# ===========================================================================
# E — THREE CLAIMS THE CACHED BYTES REFUTE
#
# Pinned as tests so the next agent does not "fix" them a second time. Each is
# checked with the LADDER OFF, i.e. against pre-wave behaviour.
# ===========================================================================
def test_e_a_the_graph_key_was_already_unwrapped_before_this_wave(monkeypatch):
    """The brief said "the block is a dict with @graph, which is never
    unwrapped (marionnaud x2, superdrug x2)". Base 8adaefb unwraps a top-level
    dict's @graph at price_service.py:9809. superdrug's @graph Product resolves
    with the ladder OFF, and marionnaud's non-variant pages do too. Across all
    322 cached pages ZERO carry an @graph nested inside a top-level LIST — the
    one @graph shape that genuinely was not walked. The marionnaud failures are
    ProductGroup failures (test_a_b), not @graph failures."""
    _gate(monkeypatch, "false")
    _ladder(monkeypatch, "false")
    got = extract_jsonld_price(
        load("gb_hybris_superdrug_com_graph_product_single_offer.html"),
        "Paco", "GBP", "Paco Rabanne Lady Million Eau My Gold EDT 80ml",
    )
    assert got is not None and got["amount"] == 30.0


def test_e_b_type_as_a_list_was_already_accepted(monkeypatch):
    """The brief said to "accept @type as a LIST as well as a string".
    ``_is_product_type`` has done exactly that since base 8adaefb:8624. No
    corpus page uses the list form on a Product, so there is no real-bytes
    fixture to cut for it; this is the unit that already covers it."""
    assert _is_product_type({"@type": ["Product", "Vehicle"]}) is True
    assert _is_product_type({"@type": "Product"}) is True
    assert _is_product_type({"@type": ["ProductGroup"]}) is False
    assert _is_product_type({"@type": None}) is False
    assert _is_product_type("not a dict") is False


def test_e_c_og_price_amount_was_already_preferred_over_product_price_amount(monkeypatch):
    """The brief said "the OG fallback ... keys on product:price:amount while
    allbeauty, escentual and perfumania publish og:price:amount". Base
    8adaefb:9079 reads og:price:amount FIRST and only falls back to
    product:price:amount. Pinned on a page carrying BOTH, so the precedence is
    observable rather than asserted."""
    from bs4 import BeautifulSoup

    _gate(monkeypatch, "false")
    _ladder(monkeypatch, "false")
    html = (
        '<html><head>'
        '<meta property="og:price:amount" content="53.40">'
        '<meta property="og:price:currency" content="GBP">'
        '<meta property="product:price:amount" content="99.99">'
        '<meta property="product:price:currency" content="GBP">'
        '</head><body></body></html>'
    )
    got = ps._extract_og_price(
        BeautifulSoup(html, "html.parser"),
        "Gucci Guilty For Her Eau de Toilette Spray 50ml",
        "GBP", "allbeauty.com", "https://allbeauty.com/products/p-gucci-guilty", html,
    )
    assert got is not None and got["amount"] == 53.40


# ===========================================================================
# F — TOTALITY. The ladder walks attacker-shaped documents; it must never raise.
# ===========================================================================
def _wrap(node) -> str:
    return (
        '<html><head><script type="application/ld+json">'
        + json.dumps(node)
        + "</script></head><body></body></html>"
    )


def test_f_a_an_empty_offers_array_yields_no_candidate_and_never_raises(monkeypatch):
    """The brief named notino.co.uk's Sauvage EDT as "a real top-level Product
    whose offers is an EMPTY array". That page is not in the corpus and ZERO of
    the 322 cached pages carry an empty offers array, so this is a
    constructed-shape totality test, not a measured-page one. An empty array is
    simply no offer: no price, no crash, no fabricated fallback."""
    _gate(monkeypatch, "false")
    node = {"@context": "https://schema.org", "@type": "Product",
            "name": "Dior Sauvage Eau de Toilette 100ml", "offers": []}
    assert extract_jsonld_price(_wrap(node), "Dior",
                                "GBP", "Dior Sauvage Eau de Toilette 100ml") is None


@pytest.mark.parametrize("has_variant", [
    None, "", 0, "Product", 3.5, True, [], {}, [None], [3], ["Product"],
    [{"@type": "Product"}], {"@type": "Product"},
    [{"@type": "Product", "offers": None}],
    [{"@type": "Product", "offers": {"price": {}, "priceCurrency": "GBP"}}],
    [{"@type": "Product", "offers": {"priceSpecification": 7, "priceCurrency": "GBP"}}],
    [{"@type": "Product", "offers": {"priceSpecification": {"price": []}}}],
])
@pytest.mark.parametrize("ladder", ["true", "false"])
def test_f_b_a_hostile_hasvariant_never_raises(monkeypatch, has_variant, ladder):
    """BLOCKER 5's rule applied to the new descent: every shape reachable from
    ``hasVariant`` / ``priceSpecification`` is untyped in the wild, so the walk
    must be TOTAL in both flag states."""
    _gate(monkeypatch, "false")
    _ladder(monkeypatch, ladder)
    node = {"@context": "https://schema.org", "@type": "ProductGroup",
            "name": "Dior Sauvage", "brand": {"@type": "Brand", "name": "Dior"},
            "hasVariant": has_variant}
    got = extract_jsonld_price(_wrap(node), "Dior", "GBP", "Dior Sauvage 100ml")
    assert got is None or isinstance(got.get("amount"), float)


@pytest.mark.parametrize("ladder", ["true", "false"])
def test_f_c_a_self_referential_graph_terminates(monkeypatch, ladder):
    """A ProductGroup whose variant is itself a ProductGroup, nested past any
    plausible real depth. The walk is depth-bounded, so a hostile document
    cannot turn it into a hang or a RecursionError."""
    _gate(monkeypatch, "false")
    _ladder(monkeypatch, ladder)
    node = {"@type": "Product", "name": "Dior Sauvage 100ml",
            "offers": {"price": 1.0, "priceCurrency": "GBP"}}
    for _ in range(200):
        node = {"@type": "ProductGroup", "name": "Dior Sauvage",
                "brand": "Dior", "hasVariant": [node]}
    extract_jsonld_price(_wrap(node), "Dior", "GBP", "Dior Sauvage 100ml")


def test_f_d_pending_out_of_the_wrong_type_is_ignored_not_fatal(monkeypatch):
    """A caller that passes something that is not a list must not crash the
    extractor — the pend channel is a courtesy, never a dependency."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load("us_sephora_com_productgroup_sizeless_variants.html"),
        "Dior", "USD", "Dior Sauvage Elixir", pending_out="not-a-list",
    )
    assert got is None


# ===========================================================================
# G — THE FIXTURES ARE REAL BYTES
# ===========================================================================
def test_g_every_fixture_records_its_provenance():
    sources = json.loads((FIXTURES / "SOURCES.json").read_text(encoding="utf-8"))
    on_disk = {p.name for p in FIXTURES.glob("*.html")}
    assert on_disk, "no fixtures found"
    assert on_disk == set(sources["files"]), "SOURCES.json and the directory disagree"
    for name, meta in sources["files"].items():
        assert meta["url"].startswith("http")
        assert meta["cached_bytes"].endswith(".html")
        assert len(meta["cached_sha1_of_page"]) == 40


# ===========================================================================
# H — THE DECANTS PRODUCT DECISION. A PIN, NOT A CHANGE.
#
# ---------------------------------------------------------------------------
# THE 2026-08-30 OWNER DECISION, RECORDED VERBATIM
#
#     Ahmed, 2026-08-30:  "decant price for decants queries"
#
# ---------------------------------------------------------------------------
# WHAT IT SETTLES. Gate 4 of the wave-3 fix wave flagged the scentsplit.com
# decants PDPs as a suspected regression: HEAD had started returning the
# QUERIED DECANT's price (8.99 USD here; 3.99 on the sibling
# bon-parfumeur-001-sample-decants row) where the pre-ladder code returned the
# JSON-LD FIRST VALUE, which on these pages is the full bottle (250.00 here,
# 140.00 there — and 250.00 is what the corpus survey recorded as this page's
# `jsonld_price`). The owner has now RULED that the decant price is CORRECT for
# a decants query. That is a PRODUCT decision about what these pages sell, not
# an extractor bug, so it is pinned here rather than re-litigated: scentsplit
# is a decanting house, `.../products/xerjoff-ilm-sample-decants` is its decant
# listing, and a shopper who asked for decants is not shopping for the 50ml
# manufacturer's bottle that shares the URL.
#
# NOTHING IN THIS BLOCK CHANGES CODE. Every assertion below is HEAD's measured
# behaviour on 2026-08-30, recorded so the next wave sees drift instead of
# silently re-deciding this.
#
# ---------------------------------------------------------------------------
# THE PAGE (fixture cut from the real cached bytes; provenance in SOURCES.json).
# One top-level `ProductGroup`, three `hasVariant` Products, all InStock:
#
#     "'Ilm - 50ml in Manufacturer's bottle"   250.00 USD   <- JSON-LD FIRST
#     "'Ilm - 1ml Sample"                        8.99 USD   <- THE DECANT
#     "'Ilm - 2ml Glass Spray"                  16.99 USD
#
# plus `og:price:amount 250.00`. So "first value" and "the bottle" are the same
# number on this page, which is exactly why the change was legible to gate 4.
#
# ---------------------------------------------------------------------------
# THE MEASUREMENT, AND WHY THIS BLOCK IS SPLIT BY EXACT-GATE MODE.
#
# The first draft of this pin asserted the ruling at SHIPPED DEFAULTS and FAILED
# (`assert None is not None`). That failure is the finding, so it is pinned too:
#
#   * ENABLE_EXACT_PRICE_GATE unset (SHIPPED) -> None, for BOTH a decants query
#     and a bare "xerjoff ilm". `_selection_match` admits NEITHER variant, so
#     the page ships no price at all. The ruling's NEGATIVE half therefore holds
#     in production today — 250.00 is never served for a decants query — but its
#     POSITIVE half does not: the decant price is not shipped either. That is a
#     coverage pend of the documented fail-closed kind, not a wrong price.
#   * ENABLE_EXACT_PRICE_GATE=false (extraction-isolated — the mode CLAUDE.md
#     documents for isolating extraction from the gate) -> 8.99, the queried
#     decant, NOT 250.0. THIS is where the ruling is observable, and it is what
#     gate 4 measured.
#
# Say which mode you are in. A pin that only asserted the shipped default would
# record "no price" and lose the ruling; one that only asserted the gate-off
# value would claim a behaviour production does not have.
#
# The fixture reproduces the full cached page on all 20 measured
# (query x gate x category) combinations, so nothing here is an artifact of the
# cut.
# ===========================================================================
_DECANTS = "us_shopify_scentsplit_com_productgroup_decants_and_bottle.html"
_DECANTS_QUERY = "xerjoff ilm sample decants"


@pytest.mark.parametrize("category", [None, "fragrances"])
def test_h_a_a_decants_query_takes_the_queried_decant_not_the_bottle(
    monkeypatch, category,
):
    """THE RULING, pinned. Extraction-isolated, so the exact gate is not the
    thing under test. A decants query resolves to the 1ml Sample at 8.99 — not
    the 250.0 bottle that is both the JSON-LD first value and the og:price, and
    not the 16.99 second decant."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load(_DECANTS), "Xerjoff", "USD", _DECANTS_QUERY, category=category,
    )
    assert got is not None
    assert got["amount"] == 8.99
    assert got["amount"] != 250.0
    assert got["currency"] == "USD"
    assert got["name"] == "'Ilm - 1ml Sample"


def test_h_b_the_shipped_exact_gate_pends_this_page_in_both_directions(
    monkeypatch,
):
    """CURRENT SHIPPED BEHAVIOUR, right or wrong, so drift is visible.

    With the exact gate at its shipped default, `_selection_match` rejects both
    the sample and the bottle, so this page yields NO price for either query.
    The ruling is not contradicted (250.0 is never returned for a decants
    query) but neither is it delivered. If a future wave loosens the gate, THIS
    is the test that will go red and force the decision to be made in the open:
    the value that appears here must be 8.99, never 250.0."""
    monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
    assert ps.exact_gate_enabled() is True, "this test asserts the SHIPPED default"
    for query in (_DECANTS_QUERY, "xerjoff ilm"):
        pending = []
        got = extract_jsonld_price(
            load(_DECANTS), "Xerjoff", "USD", query, pending_out=pending,
        )
        assert got is None, f"{query!r} newly returns {got}"
        assert pending == [], f"{query!r} newly pends candidates {pending}"


def test_h_c_a_non_decant_query_does_not_take_the_decant_price(monkeypatch):
    """THE INVERSE CASE, measured rather than assumed. A query that does NOT
    ask for decants must not be answered with 8.99 just because it is on the
    page — the authority-not-cheapest rule of block C.

    Extraction-isolated, "xerjoff ilm" admits BOTH the bottle and the sample,
    names no size, and neither variant is out of stock, so every rung of
    `_adjudicate_jsonld_multiplicity` declines and the page PENDS with both
    candidates handed back. HEAD is right here; the pin exists so a future
    "make decants win" shortcut cannot quietly turn this into 8.99."""
    _gate(monkeypatch, "false")
    pending = []
    got = extract_jsonld_price(
        load(_DECANTS), "Xerjoff", "USD", "xerjoff ilm", pending_out=pending,
    )
    assert got is None
    assert sorted(c["amount"] for c in pending[0]) == [8.99, 250.0]


def test_h_d_a_size_qualified_bottle_query_still_reaches_the_bottle(monkeypatch):
    """The ruling is QUERY-CONDITIONAL, not "the decant always wins". The same
    page, asked for the 50ml, still returns 250.0 — so pinning H-a costs the
    bottle nothing."""
    _gate(monkeypatch, "false")
    got = extract_jsonld_price(
        load(_DECANTS), "Xerjoff", "USD", "Xerjoff 'Ilm 50ml",
    )
    assert got is not None
    assert got["amount"] == 250.0
    assert got["name"] == "'Ilm - 50ml in Manufacturer's bottle"


def test_h_e_the_2ml_glass_spray_decant_is_rejected_as_an_accessory(monkeypatch):
    """A SIDE FINDING, pinned as CURRENT behaviour and NOT fixed in this unit.

    The third variant, "'Ilm - 2ml Glass Spray" at 16.99, is never a candidate
    for ANY query — including its own name — because "glass" is in
    ACCESSORY_KEYWORDS (tempered-glass / screen-protector vocabulary) and
    `is_accessory_for_category` has no fragrance-scoped exemption for it, the
    way it has one for "skin" on pharmacy categories and "keyboard" on laptops.

    That is a real over-rejection on a decants page: a 2ml glass-spray decant
    is the product, not an accessory to it. It is recorded here rather than
    fixed because this unit changes no code, and because widening the exemption
    touches every category's accessory filter. If someone adds a fragrance
    exemption, this test goes red and is the place to record the new value."""
    _gate(monkeypatch, "false")
    assert ps.is_accessory_for_category("'Ilm - 2ml Glass Spray", "fragrances") is True
    assert ps.is_accessory_for_category("'Ilm - 1ml Sample", "fragrances") is False
    got = extract_jsonld_price(
        load(_DECANTS), "Xerjoff", "USD", "Xerjoff 'Ilm 2ml Glass Spray",
    )
    assert got is None, f"the 2ml glass spray is now reachable: {got}"

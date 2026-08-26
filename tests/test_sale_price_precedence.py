"""OpenGraph SALE-price precedence (the Salla P0) - `ENABLE_SALE_PRICE_FIRST`.

`extract_price_from_html`'s OpenGraph fallback used to read only
``og:price:amount`` -> ``product:price:amount``. On a Salla storefront
``product:price:amount`` is the **LIST** price and the real shelf price lives in
``product:sale_price:amount``; production therefore shipped the crossed-out
price. Measured over the 92 cached fragrance PDPs in ``_proof/html/``:
``product:sale_price:amount`` appears on 14 of the 86 mappable pages, **all 14
Salla**, and 10 of them diverge from the list price by 1.13x-4.57x.

New precedence (flag ON, the default):
    og:price:amount -> product:sale_price:amount -> product:price:amount

The fixtures below are the *meta-tag fragments* of those real pages (verbatim
amounts + currencies read out of the cached HTML), not full 2MB documents, and
carry NO ``og:title``/``<title>`` so ``_page_identity_ok`` sees no identity
signal and stays out of the way - the assertions isolate the tag precedence.
They also carry the one-line Salla platform signature the real pages ship
(``cdn.salla.network``), because as of 2026-08-26 the rule is SCOPED to
``detect_platform(...) in {salla, zid}`` - see the PLATFORM SCOPING block at
the bottom of this file for the measurement that forced that and for the
non-Gulf fixtures.

Both directions are asserted for every case: flag ON must return the SALE
price, flag OFF must return the byte-identical legacy LIST price.

No network, no fixtures on disk, no imports beyond price_service.
"""

import pytest

from app.services.price_service import (
    extract_price_from_html,
    sale_price_first_enabled,
)

# domain, list amount, list currency, sale amount, sale currency
# Verbatim from the cached Salla PDPs (see _proof/sweep2_curl_cffi.jsonl).
DIVERGING = [
    ("3saf.com", "799", "SAR", "175", "SAR"),
    ("laverne.com", "225", "SAR", "96", "SAR"),
    ("om.oudelite.com", "23", "OMR", "10.5", "OMR"),
    ("bh.oudelite.com", "23", "BHD", "11", "BHD"),
    ("sa.abdulsamadalqurashi.com", "990", "SAR", "495", "SAR"),
    ("sa.oudelite.com", "290", "SAR", "145", "SAR"),
    ("kw.oudelite.com", "14", "KWD", "7", "KWD"),
    ("rend-bahrain.com", "129", "SAR", "79.99", "SAR"),
    ("reefperfumes.com", "32.505", "BHD", "22.902", "BHD"),
    ("vanilla.sa", "490.1", "SAR", "435.1", "SAR"),
]

# The other 4 Salla pages carry a sale tag EQUAL to the list price (no discount
# live) - the fix must be a no-op there, in both flag states.
NON_DIVERGING = [
    ("bh.arabianoud.com", "49.005", "BHD", "49.005", "BHD"),
    ("banafaforoud.com", "125.01", "SAR", "125.01", "SAR"),
    ("store.rasasi.com.sa", "253", "SAR", "253", "SAR"),
    ("alrehabstore.com", "99", "SAR", "99", "SAR"),
]

QUERY = "Oud Elite So Black Eau de Parfum 100ml"


#: Verbatim from every one of the 14 cached Salla PDPs - the signature
#: `detect_platform` reads. Present by default so these fixtures stay faithful
#: to the pages they were lifted from now that the rule is platform-scoped.
SALLA_MARKER = '<link rel="preconnect" href="https://cdn.salla.network" crossorigin>'


def _salla_html(
    list_amount, list_currency, sale_amount, sale_currency=None,
    platform_marker=SALLA_MARKER,
):
    """Minimal Salla-shaped OpenGraph head: list price + optional sale price.

    ``platform_marker`` is the platform signature the document carries; pass ""
    for a page `detect_platform` cannot place.
    """
    tags = [
        platform_marker,
        '<meta property="og:type" content="product">',
        '<meta property="product:price:amount" content="%s">' % list_amount,
        '<meta property="product:price:currency" content="%s">' % list_currency,
    ]
    if sale_amount is not None:
        tags.append(
            '<meta property="product:sale_price:amount" content="%s">' % sale_amount
        )
        if sale_currency is not None:
            tags.append(
                '<meta property="product:sale_price:currency" content="%s">'
                % sale_currency
            )
    return "<html><head>" + "".join(tags) + "</head><body></body></html>"


def _extract(html, currency, domain):
    return extract_price_from_html(
        html, QUERY, currency, domain, "https://%s/en/p/1" % domain,
    )


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "false")


# --------------------------------------------------------------------------
# The flag helper itself
# --------------------------------------------------------------------------

def test_flag_defaults_on_when_unset(monkeypatch):
    monkeypatch.delenv("ENABLE_SALE_PRICE_FIRST", raising=False)
    assert sale_price_first_enabled() is True


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off", "", "  Off "])
def test_flag_off_values(monkeypatch, value):
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", value)
    assert sale_price_first_enabled() is False


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", "anything-else"])
def test_flag_on_values(monkeypatch, value):
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", value)
    assert sale_price_first_enabled() is True


def test_flag_is_read_per_call_not_cached_at_import(monkeypatch):
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "false")
    assert sale_price_first_enabled() is False
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
    assert sale_price_first_enabled() is True


# --------------------------------------------------------------------------
# (a) flag ON -> the SALE price
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "domain,list_amount,list_currency,sale_amount,sale_currency", DIVERGING
)
def test_flag_on_returns_sale_price(
    flag_on, domain, list_amount, list_currency, sale_amount, sale_currency
):
    html = _salla_html(list_amount, list_currency, sale_amount, sale_currency)
    result = _extract(html, list_currency, domain)
    assert result is not None
    assert result["amount"] == pytest.approx(float(sale_amount))
    assert result["currency"] == sale_currency
    assert result["original_currency"] == sale_currency
    # still a genuine local page scrape, not a converted figure
    assert result["source_method"] == "page_scrape"


# --------------------------------------------------------------------------
# (b) flag OFF -> byte-identical legacy LIST price
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "domain,list_amount,list_currency,sale_amount,sale_currency", DIVERGING
)
def test_flag_off_returns_legacy_list_price(
    flag_off, domain, list_amount, list_currency, sale_amount, sale_currency
):
    html = _salla_html(list_amount, list_currency, sale_amount, sale_currency)
    result = _extract(html, list_currency, domain)
    assert result is not None
    assert result["amount"] == pytest.approx(float(list_amount))
    assert result["currency"] == list_currency


@pytest.mark.parametrize(
    "domain,list_amount,list_currency,sale_amount,sale_currency", DIVERGING
)
def test_flag_off_result_is_identical_to_a_page_with_no_sale_tag(
    flag_off, domain, list_amount, list_currency, sale_amount, sale_currency
):
    """Flag OFF, the sale tag is invisible: the whole dict must equal what the
    same page WITHOUT the tag produces (the pre-change bytes)."""
    with_sale = _extract(
        _salla_html(list_amount, list_currency, sale_amount, sale_currency),
        list_currency,
        domain,
    )
    without_sale = _extract(
        _salla_html(list_amount, list_currency, None), list_currency, domain
    )
    assert with_sale == without_sale


# --------------------------------------------------------------------------
# No-op cases
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "domain,list_amount,list_currency,sale_amount,sale_currency", NON_DIVERGING
)
@pytest.mark.parametrize("flag", ["true", "false"])
def test_equal_sale_and_list_price_is_a_noop(
    monkeypatch, flag, domain, list_amount, list_currency, sale_amount, sale_currency
):
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", flag)
    result = _extract(
        _salla_html(list_amount, list_currency, sale_amount, sale_currency),
        list_currency,
        domain,
    )
    assert result is not None
    assert result["amount"] == pytest.approx(float(list_amount))
    assert result["currency"] == list_currency


@pytest.mark.parametrize("flag", ["true", "false"])
def test_no_sale_tag_page_is_untouched(monkeypatch, flag):
    """The other 72 mappable cached pages carry NO product:sale_price:amount -
    non-Salla platforms must take the exact legacy path in both flag states."""
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", flag)
    result = _extract(
        _salla_html("244.990", "BHD", None, platform_marker=""),
        "BHD",
        "bahrain.sharafdg.com",
    )
    assert result is not None
    assert result["amount"] == pytest.approx(244.990)
    assert result["currency"] == "BHD"


@pytest.mark.parametrize("flag", ["true", "false"])
def test_og_price_amount_still_wins_over_sale_tag(monkeypatch, flag):
    """Precedence is og:price:amount FIRST - a page that ships the canonical OG
    price keeps it, flag or no flag."""
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", flag)
    html = (
        "<html><head>"
        '<meta property="og:price:amount" content="55.5">'
        '<meta property="og:price:currency" content="BHD">'
        '<meta property="product:sale_price:amount" content="11">'
        '<meta property="product:sale_price:currency" content="BHD">'
        '<meta property="product:price:amount" content="23">'
        '<meta property="product:price:currency" content="BHD">'
        "</head><body></body></html>"
    )
    result = _extract(html, "BHD", "bh.oudelite.com")
    assert result is not None
    assert result["amount"] == pytest.approx(55.5)


def test_sale_tag_without_its_own_currency_borrows_the_list_currency(flag_on):
    """Spec case: a sale-price tag carrying no product:sale_price:currency takes
    the currency from product:price:currency (never the "USD" default)."""
    html = _salla_html("23", "OMR", "10.5", sale_currency=None)
    result = _extract(html, "OMR", "om.oudelite.com")
    assert result is not None
    assert result["amount"] == pytest.approx(10.5)
    assert result["currency"] == "OMR"
    assert result["original_currency"] == "OMR"
    assert result["source_method"] == "page_scrape"


def test_blank_sale_tag_falls_through_to_the_list_price(flag_on):
    html = _salla_html("23", "BHD", "")
    result = _extract(html, "BHD", "bh.oudelite.com")
    assert result is not None
    assert result["amount"] == pytest.approx(23.0)
    assert result["currency"] == "BHD"


def test_unparseable_sale_tag_falls_through_to_the_list_price(flag_on):
    """A sale amount we cannot turn into a positive float must NOT cost us the
    perfectly good list price (flag ON is never worse than flag OFF)."""
    html = _salla_html("23", "BHD", "on request")
    result = _extract(html, "BHD", "bh.oudelite.com")
    assert result is not None
    assert result["amount"] == pytest.approx(23.0)


def test_zero_sale_tag_falls_through_to_the_list_price(flag_on):
    html = _salla_html("23", "BHD", "0")
    result = _extract(html, "BHD", "bh.oudelite.com")
    assert result is not None
    assert result["amount"] == pytest.approx(23.0)


# ==========================================================================
# PLATFORM SCOPING (2026-08-26) - the rule belongs to Salla and Zid ONLY
# ==========================================================================
#
# THE MEASUREMENT. `product:sale_price:amount` was treated as a generic
# OpenGraph convention. It is not: it is a GULF platform convention, and
# outside Salla/Zid the rule is dead code that only ever fires on a page that
# should not have it. Counted over the cached bytes of BOTH corpora on
# 2026-08-26 (grep, then `detect_platform` on the same file):
#
#   _proof/html/          92 Gulf PDPs   -> 14 carry the tag, ALL 14 salla
#   _proof/global/html/  328 global rows ->  7 carry the tag, ALL 7 Gulf:
#                                            5 zid  (h3jssz.zid.store x4,
#                                                    mazeed.sa x1)
#                                            2 salla (ae.abdulsamadalqurashi)
#   206 usable non-Gulf PDPs across five regions -> ZERO. Not one.
#
# So the rule is scoped to `detect_platform(html, url) in {"salla", "zid"}`.
# On REAL pages that is a strict no-op - it cannot change any of the 21 pages
# that carry the tag, and the other 399 never entered the branch at all. What
# it removes is the FUTURE misfire: a German/UK/US storefront that starts
# emitting the tag (Facebook's catalogue spec does define it) would otherwise
# have its list price replaced by whatever that tag holds, on a platform where
# nobody has verified what it holds.
#
# Zid had to be taught to `platform_router` first: it is invisible to the
# original six regexes and all 8 cached Zid rows returned "unknown".
#
# FLAG: ENABLE_SALE_PRICE_FIRST, reused, still default ON. No new flag.
# Flag OFF the whole branch is skipped and `detect_platform` is never called,
# so the rollback stays byte-identical to 8adaefb.

from pathlib import Path

from app.services.platform_router import detect_platform

SALE_FIXTURES = Path(__file__).parent / "fixtures" / "sale_price"


def _fixture(name):
    return (SALE_FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def gate_off(monkeypatch):
    """ENABLE_EXACT_PRICE_GATE off - the identity gate rejects most cached
    pages, so it has to be out of the way for these fixtures to isolate
    EXTRACTION. Every number below is therefore an extraction number."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")


# --- the Gulf pages the rule exists for keep it ----------------------------

def test_the_cached_salla_page_still_returns_its_sale_price(flag_on, gate_off):
    """bh.oudelite.com, verbatim head fragment: list 23 BHD, sale 11 BHD."""
    html = _fixture("gulf_salla_bh_oudelite_com.html")
    assert detect_platform(html, "https://bh.oudelite.com/en/-/p1866281610") == "salla"
    result = _extract(html, "BHD", "bh.oudelite.com")
    assert result is not None
    assert result["amount"] == pytest.approx(11.0)
    assert result["currency"] == "BHD"


@pytest.mark.parametrize(
    "domain,list_amount,list_currency,sale_amount,sale_currency", DIVERGING
)
def test_every_diverging_salla_page_is_unchanged_by_the_scoping(
    flag_on, domain, list_amount, list_currency, sale_amount, sale_currency
):
    """The 10 diverging Salla pages of the P0 must be bit-for-bit what they
    were before the scoping - the fragments carry the real cdn.salla.network
    signature, so the platform gate admits them."""
    html = _salla_html(list_amount, list_currency, sale_amount, sale_currency)
    assert detect_platform(html, "https://%s/en/p/1" % domain) == "salla"
    result = _extract(html, list_currency, domain)
    assert result is not None
    assert result["amount"] == pytest.approx(float(sale_amount))
    assert result["currency"] == sale_currency


@pytest.mark.parametrize(
    "name,url",
    [
        ("gulf_zid_h3jssz_zid_store.html", "https://h3jssz.zid.store/products/40"),
        ("gulf_zid_mazeed_sa_behind_nuxt.html", "https://mazeed.sa/en/products/x"),
    ],
)
def test_a_zid_page_gets_the_rule(flag_on, gate_off, name, url):
    """Zid is the OTHER platform that publishes the tag - 5 of the 7 global
    occurrences. list 190.0 SAR -> sale 99.0 SAR. mazeed.sa is Zid behind a
    Nuxt front end, so this also pins that the platform beats the framework."""
    html = _fixture(name)
    assert detect_platform(html, url) == "zid"
    result = _extract(html, "SAR", url.split("/")[2])
    assert result is not None
    assert result["amount"] == pytest.approx(99.0)
    assert result["currency"] == "SAR"


@pytest.mark.parametrize(
    "name,url,currency,list_amount",
    [
        (
            "de_shopify_parfumgroup_de.html",
            "https://parfumgroup.de/products/carolina-herrera-good-girl-eau-de-parfum",
            "EUR",
            51.89,
        ),
        (
            "uk_magento_pacoperfumerias_co_uk.html",
            "https://www.pacoperfumerias.co.uk/calvin-klein-eternity-eau-de-parfum-100ml-spray.html",
            "GBP",
            42.5,
        ),
        (
            "us_shopify_olfactif_com.html",
            "https://www.olfactif.com/products/12-month-prepaid-subscription",
            "USD",
            250.0,
        ),
    ],
)
def test_a_non_gulf_page_does_not_get_the_rule(
    flag_on, gate_off, name, url, currency, list_amount
):
    """DE Shopify / UK Magento / US Shopify, real pages, real list prices, with
    the Gulf sale tag INJECTED at 9.99 (no non-Gulf page in the 328-row corpus
    ships one). The list price must survive: on these platforms nothing has
    established what `product:sale_price:amount` would mean."""
    html = _fixture(name)
    assert detect_platform(html, url) not in ("salla", "zid")
    result = _extract(html, currency, url.split("/")[2])
    assert result is not None
    assert result["amount"] == pytest.approx(list_amount)
    assert result["currency"] == currency


def test_an_unplaceable_page_does_not_get_the_rule(flag_on, gate_off):
    """No platform signature at all -> "unknown" -> the LIST price. The rule is
    an allow-list of two platforms, not a deny-list of the ones we happened to
    look at."""
    html = _salla_html("23", "BHD", "11", "BHD", platform_marker="")
    assert detect_platform(html, "https://example.com/p/1") == "unknown"
    result = _extract(html, "BHD", "example.com")
    assert result is not None
    assert result["amount"] == pytest.approx(23.0)


def test_the_scoping_reads_the_platform_not_the_domain(flag_on, gate_off):
    """A .sa / .bh domain proves nothing; the markup does. A Gulf-looking
    domain with no Salla/Zid signature still keeps its list price."""
    html = _salla_html("23", "BHD", "11", "BHD", platform_marker="")
    result = _extract(html, "BHD", "bh.some-custom-store.com")
    assert result is not None
    assert result["amount"] == pytest.approx(23.0)


@pytest.mark.parametrize(
    "name,url,currency,expected",
    [
        (
            "gulf_zid_h3jssz_zid_store.html",
            "https://h3jssz.zid.store/products/40",
            "SAR",
            190.0,
        ),
        ("de_shopify_parfumgroup_de.html", "https://parfumgroup.de/p", "EUR", 51.89),
    ],
)
def test_flag_off_is_the_legacy_list_price_on_every_platform(
    flag_off, gate_off, name, url, currency, expected
):
    """Rollback: with the flag OFF the sale tag is never looked up and
    `detect_platform` is never called, so every platform lands on the legacy
    list price."""
    result = _extract(_fixture(name), currency, url.split("/")[2])
    assert result is not None
    assert result["amount"] == pytest.approx(expected)


def test_the_platform_is_only_resolved_when_a_sale_tag_is_actually_present(
    flag_on, gate_off, monkeypatch
):
    """Cost guard. `detect_platform` scans up to 400KB; only 21 of the 420
    cached pages carry the tag, so it must not run on the other 399. Pinned by
    counting calls through the name price_service resolves.

    The counter is installed into the function's OWN `__globals__`, not onto a
    module fetched from `sys.modules`. `tests/test_platform_router.py` deletes
    price_service from `sys.modules` to prove the router has no import cycle, so
    in a full-suite run a later import hands back a DIFFERENT module object than
    the one this file's `extract_price_from_html` was defined in - patching that
    object silently misses (observed: the counter stayed at 0 while the real
    lookup went on resolving through the original globals)."""
    globals_ = extract_price_from_html.__globals__
    calls = []
    real = globals_["detect_platform"]

    def _counted(*a, **k):
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setitem(globals_, "detect_platform", _counted)
    _extract(_salla_html("23", "BHD", None), "BHD", "bh.oudelite.com")
    assert calls == [], "no sale tag on the page - the platform must not be resolved"
    _extract(_salla_html("23", "BHD", "11", "BHD"), "BHD", "bh.oudelite.com")
    assert len(calls) == 1


# ==========================================================================
# NON-GULF SALE STATE - schema.org/StrikethroughPrice
# ==========================================================================
#
# Scoping the OG rule leaves every other platform with no sale signal, so the
# question is where a non-Gulf sale state actually lives. Measured over the
# 328-row global corpus: `StrikethroughPrice` appears in the cached bytes of
# 7 pages, of which 5 are real JSON-LD and 2 are false positives.
#
#   REAL (offers.priceSpecification.priceType):
#     www.noon.com               AE  79.95 AED   strike 129 AED
#     www.noon.com               EG  1918.17 EGP strike 2200 EGP  (x2, en+ar)
#     www.dermokozmetika.com.tr  TR  769.94 TRY  strike 1399.90 TRY
#     www.theperfumeshop.com     GB  29.99 GBP   strike 50 GBP
#   NOT REAL:
#     www.walmart.com x2 - the grep hits the Next.js config key
#     `enableStrikethroughPricesDisclaimer`, there is no such JSON-LD.
#
# CORRECTION TO THE BRIEF, stated plainly: the assignment named
# `superdrug.com, 2 pages` as the StrikethroughPrice site. Both cached
# superdrug PDPs contain the string ZERO times. The four hosts above are what
# the bytes say, and they are the pages these tests are built from.
#
# The NESTED shape is already correct today - the extractor reads
# `offer["price"]` and never descends into `priceSpecification`, so all five
# real pages resolve the non-strikethrough offer. That is pinned below rather
# than changed.
#
# The SECOND-OFFER shape is not correct: `offers` is a list, every member
# becomes a candidate, and `select_best` uses amount as its last tiebreak
# (and, with ENABLE_EXACT_PRICE_GATE off, as its ONLY rule - `min(amount)`).
# A strikethrough member priced BELOW the shelf price therefore wins. That is
# not hypothetical money: the EU Omnibus "lowest price in the last 30 days"
# figure the global validation flagged as a legally mandated decoy is by
# definition <= the shelf price.


@pytest.mark.parametrize(
    "name,query,currency,domain,expected,strike",
    [
        (
            "uk_hybris_theperfumeshop_com_strikethrough.html",
            "Lacoste Touch Of Pink Eau de Toilette Spray 90ml",
            "GBP",
            "www.theperfumeshop.com",
            29.99,
            50.0,
        ),
        (
            "ae_noon_com_strikethrough.html",
            "Lattafa Khamrah Unisex Eau De Parfum 100ml",
            "AED",
            "www.noon.com",
            79.95,
            129.0,
        ),
    ],
)
@pytest.mark.parametrize("flag", ["true", "false"])
def test_a_nested_strikethrough_price_specification_resolves_the_real_offer(
    monkeypatch, gate_off, flag, name, query, currency, domain, expected, strike
):
    """The two real shapes, verbatim. The struck-through was-price must never
    be the answer, in either flag state."""
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", flag)
    result = extract_price_from_html(
        _fixture(name), query, currency, domain, "https://%s/p/1" % domain
    )
    assert result is not None
    assert result["amount"] == pytest.approx(expected)
    assert result["amount"] != pytest.approx(strike)
    assert result["currency"] == currency


STRIKE_QUERY = "Lacoste Touch Of Pink Eau de Toilette Spray 90ml"
STRIKE_DOMAIN = "www.theperfumeshop.com"
STRIKE_URL = (
    "https://www.theperfumeshop.com/lacoste/touch-of-pink/eau-de-toilette-spray"
    "/p/30820EDTJU"
)


def _strike_extract(name):
    return extract_price_from_html(
        _fixture(name), STRIKE_QUERY, "GBP", STRIKE_DOMAIN, STRIKE_URL
    )


def test_a_second_offer_marked_strikethrough_is_never_selected(flag_on, gate_off):
    """The RED case: a strikethrough Offer priced BELOW the shelf price. The
    real 29.99 GBP shelf price must win over the 24.99 Omnibus-shaped
    was-price."""
    result = _strike_extract("uk_theperfumeshop_com_second_offer_omnibus_low.html")
    assert result is not None
    assert result["amount"] == pytest.approx(29.99)


def test_the_strikethrough_guard_holds_with_the_exact_gate_on(monkeypatch):
    """Same case in the SHIPPED configuration (ENABLE_EXACT_PRICE_GATE on),
    where amount is select_best's last tiebreak rather than its only rule."""
    monkeypatch.setenv("ENABLE_SALE_PRICE_FIRST", "true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    result = _strike_extract("uk_theperfumeshop_com_second_offer_omnibus_low.html")
    assert result is not None
    assert result["amount"] == pytest.approx(29.99)


def test_a_second_offer_strikethrough_above_the_shelf_price_is_a_noop(
    flag_on, gate_off
):
    """The only shape the corpus actually carries - was-price ABOVE the shelf
    price - could never win selection, so the guard must not disturb it."""
    result = _strike_extract("uk_theperfumeshop_com_second_offer_strikethrough.html")
    assert result is not None
    assert result["amount"] == pytest.approx(29.99)


def test_flag_off_restores_the_legacy_strikethrough_behaviour(flag_off, gate_off):
    """Rollback honesty: with ENABLE_SALE_PRICE_FIRST off the guard is gone and
    the cheapest member wins again, exactly as it does at 8adaefb."""
    result = _strike_extract("uk_theperfumeshop_com_second_offer_omnibus_low.html")
    assert result is not None
    assert result["amount"] == pytest.approx(24.99)

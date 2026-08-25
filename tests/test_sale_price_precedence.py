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


def _salla_html(list_amount, list_currency, sale_amount, sale_currency=None):
    """Minimal Salla-shaped OpenGraph head: list price + optional sale price."""
    tags = [
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
        _salla_html("244.990", "BHD", None), "BHD", "bahrain.sharafdg.com"
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

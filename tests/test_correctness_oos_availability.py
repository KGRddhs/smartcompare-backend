"""Wave A regressions — in-stock + schema.org availability enforcement.

CARDINAL RULE (docs/plans/2026-06-27-genuine-price-correctness-IMPL-SPEC.md): a price
is showable ONLY if the exact product is IN STOCK on a current PDP. Today the JSON-LD
extractor (a) only recognizes the literal "OutOfStock", (b) still SELECTS an out-of-stock
offer (cheapest-offer bug, price_service:3298), and (c) can TypeError on a non-string
availability — and `is_price_showable` (the response chokepoint) never checks `in_stock`.

# RED tests fail on prod b207bfa, pass after Wave B (availability policy + is_price_showable
backstop). # GREEN tests pass now and MUST keep passing (no false pends on unknown stock).
"""
import pytest

from app.services.price_service import extract_jsonld_price, is_price_showable


def _ld_html(*products):
    """Wrap one-or-more JSON-LD Product dicts in a minimal HTML page."""
    import json
    scripts = "\n".join(
        f'<script type="application/ld+json">{json.dumps(p)}</script>'
        for p in products
    )
    return f"<html><head>{scripts}</head><body></body></html>"


def _product(name, offers, brand="Samsung"):
    return {
        "@type": "Product",
        "name": name,
        "brand": {"@type": "Brand", "name": brand},
        "offers": offers,
    }


def _offer(price, availability="https://schema.org/InStock", currency="BHD"):
    o = {"@type": "Offer", "price": str(price), "priceCurrency": currency}
    if availability is not None:
        o["availability"] = availability
    else:
        o["availability"] = None  # explicit JSON null
    return o


QUERY = "Samsung Galaxy S24 256GB"


# --------------------------------------------------------------------------- #
# 1. An out-of-stock offer must NOT be selected over an in-stock one, and an   #
#    only-OOS product must PEND (return None). Current code takes the cheapest #
#    offer regardless of availability (price_service:3298).                    #
# --------------------------------------------------------------------------- #
def test_jsonld_skips_cheaper_oos_offer_for_instock_one():
    # RED — single exact product, two offers: OOS @ 25 (cheaper) + InStock @ 40.
    html = _ld_html(_product(QUERY, [
        _offer(25, "https://schema.org/OutOfStock"),
        _offer(40, "https://schema.org/InStock"),
    ]))
    result = extract_jsonld_price(html, "Samsung", "BHD", query_name=QUERY)
    assert result is not None
    assert result["amount"] == 40, "must skip the cheaper OutOfStock offer, pick the in-stock 40"


def test_jsonld_only_oos_offer_returns_none():
    # RED — the only offer for the exact product is OutOfStock → PEND (None).
    html = _ld_html(_product(QUERY, [_offer(25, "https://schema.org/OutOfStock")]))
    result = extract_jsonld_price(html, "Samsung", "BHD", query_name=QUERY)
    assert result is None, "an only-OutOfStock product must pend (None), not ship the OOS price"


# --------------------------------------------------------------------------- #
# 2. schema.org availability variants beyond OutOfStock — SoldOut /            #
#    Discontinued / PreOrder / BackOrder are NOT a current in-stock price.     #
#    Current code only matches the literal "OutOfStock" so these all leak.     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("availability", [
    "https://schema.org/SoldOut",
    "https://schema.org/Discontinued",
    "https://schema.org/PreOrder",
    "https://schema.org/BackOrder",
])
def test_jsonld_non_instock_availability_pends(availability):
    # RED — a single offer in a non-purchasable/future state must not be shipped.
    html = _ld_html(_product(QUERY, [_offer(50, availability)]))
    result = extract_jsonld_price(html, "Samsung", "BHD", query_name=QUERY)
    assert result is None, f"{availability} is not a current in-stock price → must pend"


# --------------------------------------------------------------------------- #
# 3. TypeError-safety — a non-string availability (JSON null / list / dict)    #
#    must not abort the extractor. Current `"OutOfStock" not in availability`  #
#    raises TypeError on None and mis-behaves on list/dict.                    #
# --------------------------------------------------------------------------- #
def test_jsonld_none_availability_does_not_raise():
    # RED — first offer has availability None (explicit JSON null), a second is InStock.
    html = _ld_html(_product(QUERY, [
        _offer(50, None),
        _offer(40, "https://schema.org/InStock"),
    ]))
    try:
        result = extract_jsonld_price(html, "Samsung", "BHD", query_name=QUERY)
    except TypeError as exc:  # pragma: no cover - this is exactly the bug
        pytest.fail(f"extract_jsonld_price raised TypeError on null availability: {exc}")
    # unknown(None) availability is showable; in-stock is showable — a price is returned.
    assert result is not None
    assert result["amount"] > 0


def test_jsonld_list_availability_does_not_raise():
    # RED — availability as a LIST must not crash the offer loop.
    html = _ld_html(_product(QUERY, [
        {"@type": "Offer", "price": "55", "priceCurrency": "BHD",
         "availability": ["https://schema.org/InStock"]},
    ]))
    try:
        extract_jsonld_price(html, "Samsung", "BHD", query_name=QUERY)
    except TypeError as exc:  # pragma: no cover
        pytest.fail(f"extract_jsonld_price raised TypeError on list availability: {exc}")


# --------------------------------------------------------------------------- #
# 4. is_price_showable backstop — an explicitly out-of-stock price must PEND   #
#    even when genuine; unknown stock must NOT pend (no false pend).           #
# --------------------------------------------------------------------------- #
def test_is_price_showable_pends_explicit_out_of_stock():
    # RED — strengthened backstop (Wave B): in_stock False → not showable.
    price = {
        "amount": 50.0, "currency": "BHD", "source_method": "local_bhd",
        "in_stock": False, "url": "https://x.com/product/galaxy-s24-256gb",
        "title": QUERY,
    }
    assert is_price_showable(QUERY, price) is False


def test_is_price_showable_allows_unknown_stock():
    # GREEN — availability ABSENT (no in_stock key) on a genuine exact match is
    # showable (unknown != out-of-stock; must not false-pend clean adapters).
    price = {
        "amount": 50.0, "currency": "BHD", "source_method": "local_bhd",
        "url": "https://x.com/product/galaxy-s24-256gb", "title": QUERY,
    }
    assert is_price_showable(QUERY, price) is True

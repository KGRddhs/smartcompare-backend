# -*- coding: utf-8 -*-
"""Anti-over-rejection greens + valid-URL / converted_usd-gated reds for the
genuine-price CORRECTNESS build (branch ``feature/genuine-price-correctness``).

This file enforces the OTHER side of the CARDINAL RULE (IMPL-SPEC): the strict
exact-identity gate must NOT false-pend a legitimate product. The GREEN tests
assert that legitimately-matching products are still matched/showable on CURRENT
code AND must keep matching after the strict gate lands in Wave B/C. The
NEW-HELPER / valid-URL / converted-gating tests import the not-yet-existing
``is_exact_match`` inside the test body (so COLLECTION never errors) and assert
the strengthened ``is_price_showable`` behaviour — they FAIL on current code (the
gap) and pass after Wave B/C.

Run: python -m pytest tests/test_correctness_overrejection.py -q --tb=short
Windows: conftest auto-loads .env; any file opened here uses encoding='utf-8'.
"""

from app.services.price_service import (
    extract_jsonld_price,
    extract_price_from_shopping,
    is_price_showable,
)


# ===========================================================================
# GREEN — anti-over-rejection. Must PASS now AND after the strict gate.
# ===========================================================================

def test_green_jsonld_brand_field_only_match_exact_product_returns_price():
    """# GREEN
    JSON-LD brand-field-only match: the product NAME lacks the brand, but the
    ld+json ``brand`` field carries it (the verified bahrain.ounass.com shape —
    name "Orangey Dress", brand {"@type":"Brand","name":"Jessie and James"}).
    For an EXACT product this genuine BHD price must STILL be returned — the
    strict gate must not over-reject a brand-in-brand-field listing."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@type": "Product",
      "name": "Orangey Dress",
      "brand": {"@type": "Brand", "name": "Jessie and James"},
      "offers": {
        "@type": "Offer",
        "price": "45.000",
        "priceCurrency": "BHD",
        "availability": "https://schema.org/InStock"
      }
    }
    </script>
    </head><body></body></html>
    """
    result = extract_jsonld_price(
        html,
        brand="Jessie and James",
        expected_currency="BHD",
        query_name="Jessie and James Orangey Dress",
    )
    assert result is not None
    assert result["amount"] == 45.0
    assert result["currency"] == "BHD"


def test_green_storage_in_search_query_matches_title():
    """# GREEN
    Storage axis stated in the QUERY ("Samsung Galaxy S24 256GB") and present in
    the candidate title -> exact match, price selected. The strict gate must
    compare storage on its axis WITHOUT rejecting a title that legitimately
    carries the same storage."""
    shopping_items = [
        {
            "title": "Samsung Galaxy S24 256GB",
            "price": "BHD 250.00",
            "source": "noon",
            "link": "https://www.noon.com/bahrain-en/samsung-galaxy-s24-256gb/p/N12345",
        },
    ]
    result = extract_price_from_shopping(
        "Samsung Galaxy S24 256GB", shopping_items, "BHD",
    )
    assert result is not None
    assert result["amount"] == 250.0
    assert result["currency"] == "BHD"


def test_green_color_edition_alias_does_not_reject():
    """# GREEN
    A legit COLOR token on the candidate ("iPhone 15 256GB Blue") for a query
    that omits the color ("iPhone 15 256GB") must NOT reject — color is an open
    alias class, not an identity-discriminating axis."""
    shopping_items = [
        {
            "title": "iPhone 15 256GB Blue",
            "price": "BHD 320.00",
            "source": "noon",
            "link": "https://www.noon.com/bahrain-en/apple-iphone-15-256gb-blue/p/N67890",
        },
    ]
    result = extract_price_from_shopping(
        "iPhone 15 256GB", shopping_items, "BHD",
    )
    assert result is not None
    assert result["amount"] == 320.0


def test_green_accessory_stays_rejected_in_jsonld():
    """# GREEN
    An ACCESSORY of the query (a "Galaxy S24 Case") must stay REJECTED — the
    case's cheap price must never be attributed to the phone. is_accessory
    already guards this in extract_jsonld_price; the strict gate must not
    accidentally let it through."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@type": "Product",
      "name": "Samsung Galaxy S24 Case Silicone Cover",
      "brand": {"@type": "Brand", "name": "Samsung"},
      "offers": {
        "@type": "Offer",
        "price": "11.900",
        "priceCurrency": "BHD",
        "availability": "https://schema.org/InStock"
      }
    }
    </script>
    </head><body></body></html>
    """
    result = extract_jsonld_price(
        html,
        brand="Samsung",
        expected_currency="BHD",
        query_name="Samsung Galaxy S24 256GB",
    )
    # The accessory must NOT be returned as the phone's price.
    assert result is None or result["amount"] != 11.9


# ===========================================================================
# NEW-HELPER / valid-URL / converted-gating — RED until Wave B/C.
# Import is_exact_match INSIDE the body so collection never errors.
# ===========================================================================

def test_red_valid_url_gate_pends_listing_url_but_keeps_missing_url():
    """# RED (new-helper)
    is_price_showable must PEND a price whose url is a listing/search surface
    (https://x.com/search?q=...) even for an otherwise-genuine exact match
    (valid-PDP-URL gate, IMPL-SPEC 1E). And it must NOT pend a genuine local_bhd
    with NO url (a missing url is benign for some local_bhd sources). On current
    code is_price_showable ignores the url entirely -> the listing-url assertion
    FAILS now = the real red."""
    # Confirm the new identity primitive exists (RED via ImportError until Wave B).
    from app.services.price_service import is_exact_match  # noqa: F401

    listing_url_price = {
        "amount": 250.0,
        "currency": "BHD",
        "source_method": "local_bhd",
        "in_stock": True,
        "title": "Samsung Galaxy S24 256GB",
        "url": "https://www.noon.com/bahrain-en/search?q=samsung+galaxy+s24",
    }
    # A genuine local_bhd exact match served behind a SEARCH/listing url must PEND.
    assert is_price_showable(
        "Samsung Galaxy S24 256GB", listing_url_price, category="electronics",
        enforce_correctness=True,
    ) is False

    # A genuine local_bhd with NO url must NOT be pended for the missing url.
    no_url_price = {
        "amount": 250.0,
        "currency": "BHD",
        "source_method": "local_bhd",
        "in_stock": True,
        "title": "Samsung Galaxy S24 256GB",
    }
    assert is_price_showable(
        "Samsung Galaxy S24 256GB", no_url_price, category="electronics",
        enforce_correctness=True,
    ) is True


def test_red_converted_usd_must_also_be_exact():
    """# RED (new-helper)
    converted_usd is showable ONLY when it is the EXACT product (IMPL-SPEC 1J —
    converted must also be exact). A converted_usd price for a WRONG variant
    (query "iPhone 15 256GB" but candidate title "iPhone 15 128GB") must PEND.
    A converted_usd for the EXACT product must be showable. On current code
    is_price_showable does no identity check -> the wrong-variant assertion
    FAILS now = the real red."""
    from app.services.price_service import is_exact_match  # noqa: F401

    wrong_variant = {
        "amount": 300.0,
        "currency": "BHD",
        "source_method": "converted_usd",
        "in_stock": True,
        "title": "iPhone 15 128GB",
        "url": "https://www.example-store.com/products/iphone-15-128gb",
    }
    assert is_price_showable(
        "iPhone 15 256GB", wrong_variant, category="electronics",
        enforce_correctness=True,
    ) is False

    exact_variant = {
        "amount": 360.0,
        "currency": "BHD",
        "source_method": "converted_usd",
        "in_stock": True,
        "title": "iPhone 15 256GB",
        "url": "https://www.example-store.com/products/iphone-15-256gb",
    }
    assert is_price_showable(
        "iPhone 15 256GB", exact_variant, category="electronics",
        enforce_correctness=True,
    ) is True

"""Correctness — model-line variant + storage exactness on JSON-LD, WooCommerce,
and Shopping price paths (genuine-price CORRECTNESS build).

CARDINAL RULE (docs/plans/2026-06-27-genuine-price-correctness-IMPL-SPEC.md):
select a price ONLY if it is the EXACT requested product (model + storage +
variant), in stock, valid PDP, native BHD / honest converted. A miss must PEND.
Provenance is necessary but NOT sufficient, and the gate must NOT over-reject a
legitimate alias.

The REDs in this file genuinely exercise the current bugs on prod code (`b207bfa`):
- extract_jsonld_price (price_service:3169) takes the CHEAPEST offer/product
  (`price_val < best_price["amount"]`, :3298) with NO variant/storage reject when
  the brand matched in the NAME — so a cheaper "Galaxy S24 FE" node beats the
  requested "Galaxy S24".
- extract_price_from_shopping (price_service:2968) uses `strict_title_match`
  (a SUBSET check, :2354) — a "S24 FE 256GB" title is a superset of the "S24
  256GB" key-words → passes; `variant_mismatch` (:2386) does not list "FE" →
  leaks; `amount` is the last sort key → cheapest FE wins.
- _match_woo_product (woocommerce_service:115) keeps the CHEAPEST comparable hit
  (`bhd_amount >= best_amount: continue`, :178) with the same subset matcher → FE
  beats S24.

The GREENs assert the strict gate does NOT over-reject: a query that omits the
storage axis ("Samsung Galaxy S24") must still match a "Galaxy S24 256GB" listing
(absent-axis policy, IMPL-SPEC §"Absent-axis policy").

NEW-HELPER contract tests (is_exact_match / select_best — Wave B, not yet
written) import the symbol INSIDE the test body so COLLECTION never errors; they
fail with ImportError = a real red until Wave B lands.

Windows: any file opened uses encoding='utf-8'. conftest auto-loads .env.
"""
import json

import pytest

from app.services.price_service import (
    extract_jsonld_price,
    extract_price_from_shopping,
)
from app.services.woocommerce_service import _match_woo_product


# ---------------------------------------------------------------------------
# JSON-LD fixtures.  extract_jsonld_price reads <script type="application/ld+json">
# Product nodes (price_service:3185, _is_product_type at :3161) and matches by the
# brand appearing in the product name (:3237). priceCurrency must equal
# expected_currency (:3285); availability "OutOfStock" => out of stock (:3296).
# ---------------------------------------------------------------------------

def _ld_product(name: str, price: str, currency: str = "BHD",
                availability: str = "https://schema.org/InStock") -> dict:
    """A schema.org Product node shaped like a real retailer PDP JSON-LD."""
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "brand": {"@type": "Brand", "name": "Samsung"},
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": currency,
            "availability": availability,
        },
    }


def _html_with_ld(*nodes: dict) -> str:
    """Wrap one JSON-LD Product node per <script> block in a minimal HTML page."""
    scripts = "\n".join(
        '<script type="application/ld+json">' + json.dumps(node) + "</script>"
        for node in nodes
    )
    return f"<html><head>{scripts}</head><body></body></html>"


# --- RED 1: JSON-LD variant — S24 vs cheaper S24 FE, must pick the S24 (300) ---
def test_jsonld_variant_picks_exact_s24_not_cheaper_fe():  # RED
    html = _html_with_ld(
        _ld_product("Samsung Galaxy S24 256GB", "300"),       # the requested SKU
        _ld_product("Samsung Galaxy S24 FE 256GB", "240"),    # CHEAPER wrong variant
    )
    result = extract_jsonld_price(
        html, "Samsung", "BHD", query_name="Samsung Galaxy S24 256GB",
    )
    assert result is not None, "exact S24 node exists — must not be None"
    # Current code: takes cheapest (240, the FE). Correct: the exact S24 = 300.
    assert result["amount"] == 300, (
        f"expected the exact Galaxy S24 (300 BHD), got {result['amount']} "
        f"(cheapest-offer bug picked the S24 FE)"
    )


# --- RED 2: JSON-LD — ONLY the FE node present, no exact S24 -> must PEND (None) ---
def test_jsonld_variant_fe_only_returns_none():  # RED
    html = _html_with_ld(
        _ld_product("Samsung Galaxy S24 FE 256GB", "240"),    # ONLY the FE
    )
    result = extract_jsonld_price(
        html, "Samsung", "BHD", query_name="Samsung Galaxy S24 256GB",
    )
    # No EXACT S24 on the page -> caller must PEND. Current code returns 240 (FE).
    assert result is None, (
        "page has only the S24 FE (a different SKU) — the exact-gate must yield "
        f"None so the caller pends; got {result}"
    )


# --- RED 3a: JSON-LD storage — 256GB query, picks 256GB (300) not cheaper 128GB ---
def test_jsonld_storage_picks_256gb_not_cheaper_128gb():  # RED
    html = _html_with_ld(
        _ld_product("Samsung Galaxy S24 128GB", "250"),       # wrong storage, cheaper
        _ld_product("Samsung Galaxy S24 256GB", "300"),       # the requested storage
    )
    result = extract_jsonld_price(
        html, "Samsung", "BHD", query_name="Samsung Galaxy S24 256GB",
    )
    assert result is not None, "exact 256GB node exists — must not be None"
    assert result["amount"] == 300, (
        f"expected the 256GB SKU (300 BHD), got {result['amount']} "
        f"(cheapest-offer bug picked the 128GB)"
    )


# --- RED 3b: JSON-LD storage — 128GB only, no 256GB -> must PEND (None) ---
def test_jsonld_storage_128gb_only_returns_none():  # RED
    html = _html_with_ld(
        _ld_product("Samsung Galaxy S24 128GB", "250"),       # ONLY the 128GB
    )
    result = extract_jsonld_price(
        html, "Samsung", "BHD", query_name="Samsung Galaxy S24 256GB",
    )
    assert result is None, (
        "page has only the 128GB (wrong storage) — the exact-gate must yield None "
        f"so the caller pends; got {result}"
    )


# --- GREEN: JSON-LD absent-axis — query omits storage, must still match 256GB ---
def test_jsonld_absent_storage_axis_still_matches():  # GREEN
    html = _html_with_ld(
        _ld_product("Samsung Galaxy S24 256GB", "300"),
    )
    result = extract_jsonld_price(
        html, "Samsung", "BHD", query_name="Samsung Galaxy S24",
    )
    assert result is not None, (
        "query omits storage — an absent axis must NOT reject the S24 256GB node"
    )
    assert result["amount"] == 300


# ---------------------------------------------------------------------------
# WooCommerce fixtures.  _match_woo_product (woocommerce_service:115) reads the
# Store API products[] shape: prod["name"], prod["prices"] (with "price" in MINOR
# units + "currency_minor_unit" + "currency_code"), prod["permalink"],
# prod["is_in_stock"].  _amount_from_prices (:80) divides by 10**currency_minor_unit
# => BHD minor_unit 3, so price "300000" => 300.0, "240000" => 240.0.
# ---------------------------------------------------------------------------

def _woo_product(name: str, minor_price: str, *, in_stock: bool = True,
                 currency_code: str = "BHD", minor_unit: int = 3) -> dict:
    """A WooCommerce Store API product entry (prices in MINOR units)."""
    return {
        "name": name,
        "permalink": "https://example.bh/product/"
                     + name.lower().replace(" ", "-"),
        "is_in_stock": in_stock,
        "prices": {
            "price": minor_price,
            "currency_code": currency_code,
            "currency_minor_unit": minor_unit,
        },
    }


# --- RED 4: Woo variant — S24 vs cheaper S24 FE, must select the exact S24 ---
def test_woo_variant_selects_exact_s24_not_cheaper_fe():  # RED
    products = [
        # FE first AND cheaper — current `>= best_amount: continue` keeps cheapest.
        _woo_product("Samsung Galaxy S24 FE 256GB", "240000"),   # 240.0 BHD, wrong SKU
        _woo_product("Samsung Galaxy S24 256GB", "300000"),      # 300.0 BHD, exact SKU
    ]
    result = _match_woo_product(products, "Samsung Galaxy S24 256GB", "BHD")
    assert result is not None, "exact S24 256GB candidate exists — must not be None"
    assert result["amount"] == 300.0, (
        f"expected the exact Galaxy S24 256GB (300.0 BHD), got {result['amount']} "
        f"(the FE was selected by the cheapest-hit bug)"
    )
    assert "fe" not in (result.get("title") or "").lower(), (
        "selected candidate must be the S24, not the S24 FE"
    )


# --- GREEN: Woo absent-axis — query omits storage, must still match S24 256GB ---
def test_woo_absent_storage_axis_still_matches():  # GREEN
    products = [
        _woo_product("Samsung Galaxy S24 256GB", "300000"),
    ]
    result = _match_woo_product(products, "Samsung Galaxy S24", "BHD")
    assert result is not None, (
        "query omits storage — an absent axis must NOT reject the S24 256GB hit"
    )
    assert result["amount"] == 300.0


# ---------------------------------------------------------------------------
# Shopping fixtures.  extract_price_from_shopping (price_service:2968) reads
# Serper Shopping items: item["title"], item["price"] (a price string parsed by
# parse_price_string / detect_currency), item["source"], item["link"].  For a
# high-value query it applies strict_title_match (a SUBSET check).  "Samsung
# Galaxy S24 ..." is high-value (galaxy + the phone-model regex).
# ---------------------------------------------------------------------------

def _shopping_item(title: str, price_bhd: str, source: str = "Sharaf DG",
                   link: str = "") -> dict:
    """A Serper Shopping result item with a native-BHD price string."""
    return {
        "title": title,
        "price": f"BHD {price_bhd}",
        "source": source,
        "link": link or "https://www.sharafdg.com/product/"
                + title.lower().replace(" ", "-"),
    }


# --- RED 5: Shopping variant — S24 vs cheaper S24 FE, must pick exact S24 ---
def test_shopping_variant_picks_exact_s24_not_cheaper_fe():  # RED
    items = [
        _shopping_item("Samsung Galaxy S24 FE 256GB", "240"),    # cheaper wrong SKU
        _shopping_item("Samsung Galaxy S24 256GB", "300"),       # exact SKU
    ]
    result = extract_price_from_shopping(
        "Samsung Galaxy S24 256GB", items, "BHD",
    )
    assert result is not None, "exact S24 256GB item exists — must not be None"
    # Current code: amount is the last sort key => the 240 FE wins.
    assert result["amount"] == 300.0, (
        f"expected the exact Galaxy S24 256GB (300.0 BHD), got {result['amount']} "
        f"(cheapest-sort picked the S24 FE)"
    )


# ---------------------------------------------------------------------------
# NEW-HELPER contract tests (Wave B).  is_exact_match / select_best do NOT exist
# yet — import INSIDE the body so collection never errors; ImportError => a real
# red until Wave B.
# ---------------------------------------------------------------------------

def test_is_exact_match_rejects_fe_for_s24_query():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    # The FE is a DIFFERENT model-line variant — must NOT be exact.
    assert is_exact_match(
        "Samsung Galaxy S24 256GB", "Samsung Galaxy S24 FE 256GB", "electronics",
    ) is False
    # The exact SKU is exact.
    assert is_exact_match(
        "Samsung Galaxy S24 256GB", "Samsung Galaxy S24 256GB", "electronics",
    ) is True


def test_is_exact_match_rejects_wrong_storage():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    # 128GB is a different SKU than the requested 256GB.
    assert is_exact_match(
        "Samsung Galaxy S24 256GB", "Samsung Galaxy S24 128GB", "electronics",
    ) is False


def test_is_exact_match_absent_axis_does_not_reject():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    # Query omits storage — the candidate's 256GB must NOT cause a reject.
    assert is_exact_match(
        "Samsung Galaxy S24", "Samsung Galaxy S24 256GB", "electronics",
    ) is True


def test_select_best_picks_exact_over_cheaper_wrong_variant():  # RED (new-helper)
    from app.services.price_service import select_best
    candidates = [
        {
            "amount": 240.0, "currency": "BHD", "in_stock": True,
            "url": "https://www.sharafdg.com/p/galaxy-s24-fe-256gb",
            "title": "Samsung Galaxy S24 FE 256GB",
            "source_method": "local_bhd",
        },
        {
            "amount": 300.0, "currency": "BHD", "in_stock": True,
            "url": "https://www.sharafdg.com/p/galaxy-s24-256gb",
            "title": "Samsung Galaxy S24 256GB",
            "source_method": "local_bhd",
        },
    ]
    best = select_best(candidates, "Samsung Galaxy S24 256GB", "electronics")
    assert best is not None
    assert best["amount"] == 300.0, (
        "select_best must pick the exact S24 (300), never the cheaper FE (240)"
    )


def test_select_best_returns_none_when_no_exact():  # RED (new-helper)
    from app.services.price_service import select_best
    candidates = [
        {
            "amount": 240.0, "currency": "BHD", "in_stock": True,
            "url": "https://www.sharafdg.com/p/galaxy-s24-fe-256gb",
            "title": "Samsung Galaxy S24 FE 256GB",
            "source_method": "local_bhd",
        },
    ]
    best = select_best(candidates, "Samsung Galaxy S24 256GB", "electronics")
    assert best is None, (
        "no exact S24 256GB candidate — select_best must return None so the "
        "caller pends"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-q", "--tb=short"])

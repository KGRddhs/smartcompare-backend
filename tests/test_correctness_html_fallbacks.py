"""Genuine-price CORRECTNESS — HTML fallback identity gate (OG / microdata / Woo).

`extract_price_from_html` (price_service.py:3358) cascades JSON-LD → OpenGraph →
schema.org microdata → WooCommerce `.woocommerce-Price-amount` span. The JSON-LD
path (`extract_jsonld_price`) already does query matching, BUT the three fallback
paths (OG line ~3411, microdata line ~3450, Woo line ~3464) do ZERO identity
matching and hardcode `in_stock=True` — they grab the FIRST price on the page and
attribute it to whatever product the caller queried.

The CARDINAL RULE (IMPL-SPEC) is: select a price ONLY if it is the EXACT requested
product; a miss must PEND. So on a page whose OG/microdata/Woo price belongs to a
DIFFERENT product (a wrong SKU / related accessory / sibling on a multi-product
listing), `extract_price_from_html` must NOT mis-attribute that first price — it
must return None (→ caller pends). On a clean single-product PDP whose
og:title / page <title> carries the EXACT queried product, the price must still
be returned (no over-rejection regression).

These fixtures intentionally contain NO matching JSON-LD Product node, so the
JSON-LD branch returns None and the OG / microdata / Woo fallback paths are the
ones actually exercised (else an upstream JSON-LD match would mask the bug).

RED tests fail on the current code (it returns the wrong-identity price) and pass
after Wave B/C wires `is_exact_match` into the fallback paths.
GREEN tests pass on the current code and MUST keep passing after the strict gate.

Windows: any file open uses encoding='utf-8' (none opened here — fixtures inline).
"""

import pytest

from app.services.price_service import extract_price_from_html


# ---------------------------------------------------------------------------
# Fixtures: each has NO JSON-LD Product node, so the OG / microdata / Woo path
# is the one exercised. Amounts are PLAUSIBLE for the page product so that no
# pre-existing accuracy guard (high-value floor, fragrance/haircare floor) is
# the reason a wrong-identity price is rejected — the ONLY correct rejection
# reason is the identity mismatch.
# ---------------------------------------------------------------------------

# OG: page is a DIFFERENT phone (Galaxy A15 128GB) than the query (S24 256GB).
# 59.900 BHD is a plausible A15 price (NOT a low-accessory leak), so the
# high-value floor cannot be what rejects it — only identity can.
_OG_WRONG_HTML = """
<html><head>
<meta property="og:title" content="Samsung Galaxy A15 Smartphone 128GB" />
<meta property="og:price:amount" content="59.900" />
<meta property="og:price:currency" content="BHD" />
<title>Samsung Galaxy A15 Smartphone 128GB | x-store.example</title>
</head><body><h1>Samsung Galaxy A15 128GB</h1></body></html>
"""

# OG: page IS the exact queried product (S24 256GB), og:title + page title carry
# the full name. Must still return.
_OG_EXACT_HTML = """
<html><head>
<meta property="og:title" content="Samsung Galaxy S24 256GB Smartphone" />
<meta property="og:price:amount" content="259.900" />
<meta property="og:price:currency" content="BHD" />
<title>Samsung Galaxy S24 256GB Smartphone | x-store.example</title>
</head><body><h1>Samsung Galaxy S24 256GB</h1></body></html>
"""

# Microdata: the Offer-scoped itemprop=price belongs to a wrong product
# ("Generic Wireless Earbuds Pro") that has nothing to do with the query
# ("Samsung Galaxy S24 256GB"). The microdata path takes this first/only
# itemprop=price with zero query matching.
_MICRO_WRONG_HTML = """
<html><head><title>Wireless Earbuds Pro | shop.example</title></head><body>
<div itemscope itemtype="http://schema.org/Product">
  <span itemprop="name">Generic Wireless Earbuds Pro</span>
  <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
    <span itemprop="price" content="12.500">12.500</span>
    <meta itemprop="priceCurrency" content="BHD" />
  </div>
</div>
</body></html>
"""

# Microdata: the product IS the exact queried headphones. Must still return.
_MICRO_EXACT_HTML = """
<html><head><title>Sony WH-1000XM5 Headphones | shop.example</title>
<meta property="og:title" content="Sony WH-1000XM5 Wireless Headphones" />
</head><body>
<div itemscope itemtype="http://schema.org/Product">
  <span itemprop="name">Sony WH-1000XM5 Wireless Headphones</span>
  <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
    <span itemprop="price" content="129.000">129.000</span>
    <meta itemprop="priceCurrency" content="BHD" />
  </div>
</div>
</body></html>
"""

# WooCommerce: multi-product page. The FIRST .woocommerce-Price-amount span (NOT
# inside a <del>) is a DIFFERENT product (L'Oreal Shampoo) than the query
# (Kerastase Nutritive Mask). 18.500 BHD is plausible for that shampoo, so no
# accuracy floor is the rejection reason — only identity. There is a related
# product further down the page too (proves "no first-price grab").
_WOO_WRONG_HTML = """
<html><head><title>L'Oreal Elvive Shampoo 400ml | pharmacy.example</title></head><body>
<div class="product main">
  <h1>L'Oreal Elvive Total Repair Shampoo 400ml</h1>
  <p class="price"><span class="woocommerce-Price-amount amount"><bdi>18.500<span class="woocommerce-Price-currencySymbol">BHD</span></bdi></span></p>
</div>
<ul class="related products">
  <li><span class="woocommerce-Price-amount amount"><bdi>22.000<span class="woocommerce-Price-currencySymbol">BHD</span></bdi></span></li>
</ul>
</body></html>
"""

# WooCommerce: the page product IS the exact queried mask. Must still return.
_WOO_EXACT_HTML = """
<html><head><title>Kerastase Nutritive Masquintense Mask 200ml | pharmacy.example</title>
<meta property="og:title" content="Kerastase Nutritive Masquintense Mask 200ml" />
</head><body>
<div class="product main">
  <h1>Kerastase Nutritive Masquintense Mask 200ml</h1>
  <p class="price"><span class="woocommerce-Price-amount amount"><bdi>18.500<span class="woocommerce-Price-currencySymbol">BHD</span></bdi></span></p>
</div>
</body></html>
"""


def _is_wrong_identity_hit(res, wrong_amount):
    """A result that mis-attributes the wrong product's price = a real bug.

    The correct post-fix behaviour is to return None (caller pends). We treat a
    returned dict carrying the wrong amount (without an explicit pend flag) as a
    mis-attribution failure.
    """
    if res is None:
        return False
    if not isinstance(res, dict):
        return False
    # A pended / unavailable object is an acceptable miss, not a mis-attribution.
    if res.get("unavailable") or res.get("amount") is None:
        return False
    return res.get("amount") == pytest.approx(wrong_amount)


class TestOpenGraphIdentityGate:
    def test_og_wrong_identity_not_mis_attributed(self):
        # RED — current code returns the A15's 59.900 BHD for an S24 256GB query
        # (OG path does zero identity matching). After the fix it must return None.
        res = extract_price_from_html(
            _OG_WRONG_HTML,
            "Samsung Galaxy S24 256GB",
            "BHD",
            "x-store.example",
            "https://x-store.example/galaxy-a15-128gb",
        )
        assert not _is_wrong_identity_hit(res, 59.9), (
            f"OG path mis-attributed a wrong-SKU price to the query: {res!r}"
        )
        assert res is None, (
            "an OG price for a non-matching product must PEND (return None), "
            f"got {res!r}"
        )

    def test_og_exact_identity_still_returns(self):
        # GREEN — the OG price IS for the exact queried product (S24 256GB);
        # must still be returned (no over-rejection).
        res = extract_price_from_html(
            _OG_EXACT_HTML,
            "Samsung Galaxy S24 256GB",
            "BHD",
            "x-store.example",
            "https://x-store.example/galaxy-s24-256gb",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(259.9)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape"


class TestMicrodataIdentityGate:
    def test_microdata_wrong_identity_not_mis_attributed(self):
        # RED — current code returns the earbuds' 12.500 BHD for a Galaxy S24
        # query (microdata path does zero identity matching). After fix → None.
        res = extract_price_from_html(
            _MICRO_WRONG_HTML,
            "Samsung Galaxy S24 256GB",
            "BHD",
            "shop.example",
            "https://shop.example/wireless-earbuds-pro",
        )
        assert not _is_wrong_identity_hit(res, 12.5), (
            f"microdata path mis-attributed a wrong-product price: {res!r}"
        )
        assert res is None, (
            "a microdata price for a non-matching product must PEND (None), "
            f"got {res!r}"
        )

    def test_microdata_exact_identity_still_returns(self):
        # GREEN — microdata for the exact queried headphones; must still return.
        res = extract_price_from_html(
            _MICRO_EXACT_HTML,
            "Sony WH-1000XM5 Headphones",
            "BHD",
            "shop.example",
            "https://shop.example/sony-wh-1000xm5",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(129.0)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape"


class TestWooCommerceIdentityGate:
    def test_woocommerce_wrong_identity_not_first_price_grab(self):
        # RED — current code grabs the FIRST .woocommerce-Price-amount span
        # (L'Oreal shampoo 18.500 BHD) for a Kerastase mask query, regardless of
        # identity. After the fix it must return None (caller pends).
        res = extract_price_from_html(
            _WOO_WRONG_HTML,
            "Kerastase Nutritive Mask 200ml",
            "BHD",
            "pharmacy.example",
            "https://pharmacy.example/loreal-elvive-shampoo-400ml",
        )
        assert not _is_wrong_identity_hit(res, 18.5), (
            f"Woo path grabbed a wrong-product first price: {res!r}"
        )
        assert res is None, (
            "a WooCommerce first-price on a non-matching page must PEND (None), "
            f"got {res!r}"
        )

    def test_woocommerce_exact_identity_still_returns(self):
        # GREEN — the page product IS the exact queried mask; must still return
        # the genuine single-product PDP price.
        res = extract_price_from_html(
            _WOO_EXACT_HTML,
            "Kerastase Nutritive Mask 200ml",
            "BHD",
            "pharmacy.example",
            "https://pharmacy.example/kerastase-nutritive-masquintense-200ml",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(18.5)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape"

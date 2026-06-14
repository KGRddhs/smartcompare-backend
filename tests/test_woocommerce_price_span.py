"""S3-genuine (PDP curl Decision-F, 2026-06-14) — WooCommerce price-span extractor.

bahrainpharmacy.com/store PDPs are WooCommerce. Curling the live Panadol-Extra-48s
PDP through extract_price_from_html returned None: the page's JSON-LD Offer node
is empty (price=None), there's no OG/microdata price, and the real price lives in
a WooCommerce span:

  <span class="woocommerce-Price-amount amount"><bdi>2.110&nbsp;<span
    class="woocommerce-Price-currencySymbol">BHD </span></bdi></span>

This adds a Priority-4 CSS price-span extractor (after JSON-LD/OG/microdata): read
the FIRST .woocommerce-Price-amount (the product price; later ones are related
products), take its <bdi> numeric + the .woocommerce-Price-currencySymbol. BHD on
a .bh page → genuine local_bhd electronics/pharmacy price.

(megamart.bh is an Angular SPA — its price is JS-rendered, NOT in static curl
HTML — so it is a RENDER-tier source, not curl. This extractor targets the
WooCommerce-static case only.)
"""

import pytest

from app.services.price_service import extract_price_from_html


# Real bahrainpharmacy WooCommerce shape: empty JSON-LD offer + WC price span.
_BP_SHAPE = """<html><head>
  <script type="application/ld+json">
    {"@type":"Product","name":"Panadol Extra 48s",
     "offers":{"@type":"Offer","price":null,"priceCurrency":null}}
  </script>
</head><body>
  <p class="price"><span class="woocommerce-Price-amount amount"><bdi>2.110&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span></p>
  <!-- related products below (must NOT be picked) -->
  <span class="woocommerce-Price-amount amount"><bdi>0.610&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span>
</body></html>"""


class TestWooCommercePriceSpan:
    def test_extracts_first_wc_price_as_product_price(self):
        res = extract_price_from_html(
            _BP_SHAPE, "Panadol Extra 48s", "BHD", "bahrainpharmacy.com",
            "https://bahrainpharmacy.com/store/product/panadol-extra-48-s/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(2.110)
        # The FIRST .woocommerce-Price-amount (product), not the 0.610 related.
        assert res["amount"] != pytest.approx(0.610)
        assert res["currency"].upper() == "BHD"
        assert res.get("estimated") is not True

    def test_wc_price_currency_symbol_read(self):
        """The BHD from .woocommerce-Price-currencySymbol is honored (stays BHD,
        not spuriously converted)."""
        res = extract_price_from_html(
            _BP_SHAPE, "Panadol Extra 48s", "BHD", "bahrainpharmacy.com",
            "https://bahrainpharmacy.com/store/product/panadol-extra-48-s/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(2.110)
        assert res.get("original_currency", "BHD").upper() == "BHD"

    def test_no_wc_span_returns_none(self):
        """A page with neither structured data nor a WC price span → None (no
        false positive from unrelated numbers)."""
        html = "<html><body><p>No price here, just text 12345.</p></body></html>"
        res = extract_price_from_html(
            html, "Some Product", "BHD", "x.com", "https://x.com/p",
        )
        assert res is None


class TestWooCommerceSalePrice:
    def test_sale_price_skips_crossed_out_original(self):
        """Team-lead #3 scope: on a WooCommerce SALE item the markup is
        <del><span class=woocommerce-Price-amount>OLD</span></del>
        <ins><span class=woocommerce-Price-amount>NEW</span></ins>. The FIRST
        .woocommerce-Price-amount is the CROSSED-OUT original (inside <del>) —
        must be SKIPPED in favour of the <ins> sale price."""
        html = """<html><body>
        <p class="price">
          <del aria-hidden="true"><span class="woocommerce-Price-amount amount"><bdi>5.000&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span></del>
          <ins><span class="woocommerce-Price-amount amount"><bdi>3.250&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span></ins>
        </p>
        </body></html>"""
        res = extract_price_from_html(
            html, "Some Supplement", "BHD", "bahrainpharmacy.com",
            "https://bahrainpharmacy.com/store/product/x/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(3.250)   # the sale price
        assert res["amount"] != pytest.approx(5.000)   # NOT the crossed-out original
        assert res["currency"].upper() == "BHD"


    def test_from_price_range_takes_first_main_price(self):
        """A 'from' / price-range item (<span class=from>From </span> then a
        range low–high) — the MAIN/first .woocommerce-Price-amount is taken (the
        'from' low price), not a related-product price elsewhere on the page."""
        html = """<html><body>
        <p class="price"><span class="from">From </span>
          <span class="woocommerce-Price-amount amount"><bdi>1.500&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span>
          &ndash;
          <span class="woocommerce-Price-amount amount"><bdi>4.000&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span>
        </p>
        <div class="related"><span class="woocommerce-Price-amount amount"><bdi>9.990&nbsp;<span class="woocommerce-Price-currencySymbol">BHD&nbsp;</span></bdi></span></div>
        </body></html>"""
        res = extract_price_from_html(
            html, "Variable Product", "BHD", "bahrainpharmacy.com",
            "https://bahrainpharmacy.com/store/product/x/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(1.500)  # the 'from' low, not 9.990 related


class TestWooCommerceLivePdp:
    """Against the captured live bahrainpharmacy PDP (if present)."""

    def test_live_bahrainpharmacy_pdp_extracts_bhd(self):
        from pathlib import Path
        fix = Path(__file__).parent.parent / ".l1_pdp_probe" / "bahrainpharmacy.html"
        if not fix.exists():
            pytest.skip("live PDP capture not present (probe dir is gitignored)")
        html = fix.read_text(encoding="utf-8", errors="replace")
        res = extract_price_from_html(
            html, "Panadol Extra 48s", "BHD", "bahrainpharmacy.com",
            "https://bahrainpharmacy.com/store/product/panadol-extra-48-s/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(2.110)
        assert res["currency"].upper() == "BHD"

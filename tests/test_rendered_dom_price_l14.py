"""L1.4 (Bundle B S3 'Sources') — rendered-DOM price fallback.

Diagnostic: the major BH SPAs (sharafdg = WooCommerce Mustache `{{price}}` +
`$sprice` JS; Landmark = Next.js) have NO price in static curl HTML — the price
only exists after JS renders (Firecrawl). When the cascade DOES get rendered
HTML, the price still isn't in JSON-LD/OG/microdata for these sites: sharafdg
resolves it into a `<div class="price">…BHD</div>` text node; some Next.js sites
keep it in an embedded `<script>` JSON blob.

L1.4 adds a Priority-4 fallback to extract_price_from_html (fires ONLY after
JSON-LD → OG → microdata all miss):
  (a) embedded-JSON: a <script> blob with price + priceCurrency/currency
  (b) the rendered `.price` / `.woocommerce-Price-amount` text node — explicitly
      avoiding `.cross-price` / `.strike` (the strikethrough OLD price).

Fixtures are built from the EXACT observed sharafdg Mustache template (LTR
branch) with placeholders resolved the way the site's JS does — i.e. what
Firecrawl returns post-render. Offline TDD; the live Firecrawl proof rides the
gate smoke20/full-200. Free-tier safe.
"""

from pathlib import Path

import pytest

from app.services.price_service import extract_price_from_html

FIX = Path(__file__).parent / "fixtures"


def _read(name):
    return (FIX / name).read_text(encoding="utf-8")


class TestRenderedPriceTextNode:
    def test_sharafdg_rendered_price_div(self):
        """The resolved `.price` text node yields the CURRENT price (119), not
        the `.cross-price` strikethrough (129)."""
        html = _read("sharafdg_rendered_product.html")
        res = extract_price_from_html(
            html, "Sony WH-1000XM5", "BHD", "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/sony-wh-1000xm5/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(119.0)
        assert res["amount"] != pytest.approx(129.0)  # NOT the strikethrough
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape_rendered"

    def test_no_price_anywhere_returns_none(self):
        """A rendered page with no price node / blob → None (no false positive)."""
        html = "<html><body><div class='product'><h1>Widget</h1></div></body></html>"
        res = extract_price_from_html(
            html, "Widget", "BHD", "x.com", "https://x.com/p",
        )
        assert res is None


class TestEmbeddedJsonFallback:
    def test_embedded_json_price(self):
        html = _read("embedded_json_product.html")
        res = extract_price_from_html(
            html, "Samsung Galaxy S24", "BHD", "bhstore.com",
            "https://bhstore.com/p/galaxy-s24",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(289.9)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape_rendered"


class TestStructuredDataStillWins:
    def test_jsonld_takes_priority_over_text_node(self):
        """A page with BOTH JSON-LD and a `.price` text node uses JSON-LD
        (Priority 1) — the rendered-DOM fallback only fires on a structured-data
        miss, so it must NOT override a real JSON-LD price."""
        html = '''<html><head>
<script type="application/ld+json">
{"@type":"Product","name":"Test Phone","brand":{"@type":"Brand","name":"Acme"},
"offers":{"@type":"Offer","price":200.0,"priceCurrency":"BHD"}}
</script></head><body>
<div class="price"><span class="currency">BHD</span>999.000</div>
</body></html>'''
        res = extract_price_from_html(
            html, "Acme Test Phone", "BHD", "x.com", "https://x.com/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(200.0)  # JSON-LD, not the 999 div
        assert res["source_method"] == "page_scrape"  # not _rendered

    def test_rendered_jsonld_via_brand_field_still_works(self):
        """Regression: rendered JSON-LD with brand-in-field (L1.4 brand fix)
        still extracts — the fallback didn't break the primary path."""
        html = _read("ounass_bh_product_jsonld.html")
        res = extract_price_from_html(
            html, "Jessie and James Dress", "BHD", "bahrain.ounass.com",
            "https://bahrain.ounass.com/x.html",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(80.0)
        assert res["source_method"] == "page_scrape"

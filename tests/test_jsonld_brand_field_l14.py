"""L1.4 (Bundle B S3 'Sources') — JSON-LD brand-field match.

`extract_jsonld_price` gated a Product match on `brand in product["name"]`. Many
real BH retailers (verified: bahrain.ounass.com) put the brand in the dedicated
JSON-LD `brand` field, NOT in the product name — so a valid BHD price was
wrongly rejected (returned None) whenever the query brand lived only in the
`brand` field.

Repro (real ounass BH product, captured fixture): name="Orangey Dress in
Cotton-blend", brand={"name":"Jessie and James"}, offers price=80 BHD. Query
brand "Jessie" → pre-fix None; post-fix → 80 BHD.

Fix: match the query brand against the JSON-LD `brand` (string or {"name":...})
in addition to the product name. Offline-testable (ounass product pages expose
static Product JSON-LD — no Firecrawl needed). Free-tier safe.
"""

from pathlib import Path

import pytest

from app.services.price_service import extract_jsonld_price, extract_price_from_html

FIXTURE = Path(__file__).parent / "fixtures" / "ounass_bh_product_jsonld.html"


@pytest.fixture
def ounass_html():
    return FIXTURE.read_text(encoding="utf-8")


class TestBrandInBrandField:
    def test_brand_field_match_extracts_price(self, ounass_html):
        """Query brand 'Jessie' lives in the JSON-LD brand field (not the name)
        → the price is still extracted (pre-fix this returned None)."""
        res = extract_jsonld_price(ounass_html, "Jessie", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(80.0)
        assert res["currency"] == "BHD"

    def test_brand_in_name_still_works(self, ounass_html):
        """Regression: a brand word that IS in the product name still matches."""
        res = extract_jsonld_price(ounass_html, "Dress", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(80.0)

    def test_full_extractor_path_via_brand_field(self, ounass_html):
        """End-to-end through extract_price_from_html (brand = product's first
        word) returns a page_scrape BHD price."""
        res = extract_price_from_html(
            ounass_html, "Jessie and James Orangey Dress", "BHD",
            "bahrain.ounass.com", "https://bahrain.ounass.com/x.html",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(80.0)
        assert res["source_method"] == "page_scrape"
        assert res["currency"] == "BHD"

    def test_unrelated_brand_still_rejected(self, ounass_html):
        """A brand matching NEITHER the name NOR the brand field is rejected
        (no false positive — the gate still discriminates)."""
        res = extract_jsonld_price(ounass_html, "Samsung", "BHD")
        assert res is None


# === S4 (gate SHOULD-FIX): brand-field match must not grab a wrong-product ===
# price on a multi-Product same-brand page.

_MULTI_PRODUCT_HTML = '''<html><head>
<script type="application/ld+json">
[
 {"@type":"Product","name":"Cheap Keychain Accessory",
  "brand":{"@type":"Brand","name":"Acme"},
  "offers":{"@type":"Offer","price":5.000,"priceCurrency":"BHD"}},
 {"@type":"Product","name":"Galaxy Phone X 256GB",
  "brand":{"@type":"Brand","name":"Acme"},
  "offers":{"@type":"Offer","price":200.000,"priceCurrency":"BHD"}}
]
</script></head><body></body></html>'''


class TestBrandFieldWrongProduct:
    def test_brand_field_does_not_grab_cheapest_unrelated_sibling(self):
        """Query 'Acme Galaxy Phone X 256GB' on a page with two same-brand
        Products (a 5 BHD keychain + the 200 BHD phone). Matching via the brand
        field must STILL require the NAME to relate to the query — so it returns
        the 200 phone (or None), NEVER the cheapest 5 BHD keychain."""
        res = extract_price_from_html(
            _MULTI_PRODUCT_HTML, "Acme Galaxy Phone X 256GB", "BHD",
            "x.com", "https://x.com/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(200.0)
        assert res["amount"] != pytest.approx(5.0)  # NOT the unrelated keychain

    def test_brand_field_match_with_unrelated_query_rejected(self):
        """A query that shares the brand but relates to NEITHER product name is
        rejected (no min-price grab)."""
        res = extract_price_from_html(
            _MULTI_PRODUCT_HTML, "Acme Espresso Machine Deluxe", "BHD",
            "x.com", "https://x.com/p",
        )
        assert res is None

    def test_brand_in_name_unaffected(self):
        """When the brand is IN the name (the common case), behavior is
        unchanged — still extracts."""
        html = '''<html><head><script type="application/ld+json">
        {"@type":"Product","name":"Acme Galaxy Phone X 256GB",
         "offers":{"@type":"Offer","price":200.0,"priceCurrency":"BHD"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(html, "Acme Galaxy Phone X", "BHD",
                                      "x.com", "https://x.com/p")
        assert res is not None
        assert res["amount"] == pytest.approx(200.0)

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

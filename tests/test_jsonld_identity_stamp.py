"""Source-quality fix — the JSON-LD page-scrape branch must carry the matched
listing NAME as identity, so should_cache_price / the response chokepoint / the
usable_exact_genuine KPI can verify the exact SKU.

Warmer-gate diagnosis (docs/investigations/2026-06-30-warmer-kpi-result.md):
8/18 genuine PDP prices cached NOTHING because the JSON-LD branch of
extract_price_from_html built its result WITHOUT `name`/`title` (the OG /
microdata / WooCommerce branches already stamp `name` via the M2 pattern; the
JSON-LD branch omitted it). `should_cache_price` needs `title` OR `name` to
verify identity, so a title-less genuine price is correctly refused → never
cached → the warmer can't warm it.
"""
from __future__ import annotations

import pytest

from app.services.price_service import (
    extract_price_from_html, should_cache_price,
)

# A single-Product JSON-LD PDP in BHD, in-stock — the shape extra.com /
# luluhypermarket / boutiqaat / ounass serve. NB: no "5G" token (avoids the
# deferred cellular-generation weight-token confound).
_JSONLD_HTML = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"Apple iPhone 15 256GB Black",
 "brand":{"@type":"Brand","name":"Apple"},
 "offers":{"@type":"Offer","price":"279.99","priceCurrency":"BHD",
           "availability":"https://schema.org/InStock"}}
</script></head><body></body></html>"""


class TestJsonldIdentityStamp:
    def test_jsonld_result_carries_matched_listing_name(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        res = extract_price_from_html(
            _JSONLD_HTML, "iPhone 15 256GB", "BHD",
            "extra.com", "https://extra.com/en-bh/p/apple-iphone-15-256gb-black",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(279.99)
        assert res["source_method"] == "page_scrape"
        # The matched JSON-LD Product name is now the identity (NOT the query).
        assert res.get("name") == "Apple iPhone 15 256GB Black"

    def test_jsonld_stamped_identity_lets_genuine_price_cache(self, monkeypatch):
        # The end-to-end point: with identity present, the exact-SKU-matching
        # genuine PDP price now PASSES should_cache_price (was refused for
        # missing identity). page_scrape is relabeled page_scrape_jsonld upstream;
        # both are genuine — should_cache_price checks identity + url + match.
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        res = extract_price_from_html(
            _JSONLD_HTML, "iPhone 15 256GB", "BHD",
            "extra.com", "https://extra.com/en-bh/p/apple-iphone-15-256gb-black",
        )
        assert res is not None
        assert should_cache_price("Apple iPhone 15 256GB", res, "electronics") is True

    def test_jsonld_forwards_brand_for_brand_field_only_pdp(self, monkeypatch):
        # ounass-style: brand lives in the JSON-LD brand FIELD, the name is bare
        # ("Libre Eau de Parfum 90ml"). The fix must forward `brand` so
        # should_cache_price's brand-aware _selection_match subtracts the full
        # brand — else the brand-unaware gate requires 'yves/saint/laurent' IN the
        # bare name and over-rejects a CORRECT genuine price (sweep MED).
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        html = (
            '<html><head><script type="application/ld+json">'
            '{"@type":"Product","name":"Libre Eau de Parfum 90ml",'
            '"brand":{"@type":"Brand","name":"Yves Saint Laurent"},'
            '"offers":{"@type":"Offer","price":"42.5","priceCurrency":"BHD",'
            '"availability":"https://schema.org/InStock"}}'
            '</script></head><body></body></html>'
        )
        res = extract_price_from_html(
            html, "Yves Saint Laurent Libre Eau de Parfum 90ml", "BHD",
            "ounass.com", "https://bahrain.ounass.com/shop-ysl-libre-edp-90ml",
        )
        assert res is not None
        assert res.get("brand") == "Yves Saint Laurent"
        assert should_cache_price(
            "Yves Saint Laurent Libre Eau de Parfum 90ml", res, "fragrances") is True

    def test_jsonld_flag_off_omits_name_byte_identical(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        res = extract_price_from_html(
            _JSONLD_HTML, "iPhone 15 256GB", "BHD",
            "extra.com", "https://extra.com/en-bh/p/apple-iphone-15-256gb-black",
        )
        assert res is not None
        # Legacy JSON-LD branch never carried `name` — rollback stays byte-identical.
        assert "name" not in res

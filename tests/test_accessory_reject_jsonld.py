"""S3 #34 blocker — accessory rejection on the JSON-LD scrape path.

PROD-VERIFY (live 1a01562, post-#34): Galaxy S24 → 11.9 BHD local_bhd Sharaf DG
— a phone CASE matched as the phone (GENUINE-labeled CONFIDENT-WRONG product).
Root cause: extract_jsonld_price matches brand+name+variant_mismatch+numbers but
does NOT call is_accessory — so a sharafdg "Galaxy S24 Case" JSON-LD PDP (brand
Samsung, numbers 24, no model-line qualifier) passes → 11.9 extracted as the
phone. is_accessory is applied on the shopping (line 823) + Shopify (1560) paths
but was MISSING on the JSON-LD curl-scrape path (the backfill→fan_out route that
produced the 11.9). This is WORSE than honest-converted (a confident wrong answer
= the exact "wrong scrape" Ahmed forbids).
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


_GALAXY_CASE_JSONLD = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"Samsung Galaxy S24 Case Silicone Cover Black",
 "brand":{"@type":"Brand","name":"Samsung"},
 "offers":{"@type":"Offer","priceCurrency":"BHD","price":11.9,
   "availability":"http://schema.org/InStock"}}
</script></head><body>case</body></html>"""

_GALAXY_PHONE_JSONLD = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product",
 "name":"Samsung Galaxy S24 256GB Onyx Black 5G Smartphone",
 "brand":{"@type":"Brand","name":"Samsung"},
 "offers":{"@type":"Offer","priceCurrency":"BHD","price":282.0,
   "availability":"http://schema.org/InStock"}}
</script></head><body>phone</body></html>"""


class TestJsonldRejectsAccessory:
    def test_galaxy_case_jsonld_is_rejected(self):
        from app.services.price_service import extract_price_from_html
        r = extract_price_from_html(
            _GALAXY_CASE_JSONLD, "Samsung Galaxy S24", "BHD",
            "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/samsung-galaxy-s24-case/")
        assert r is None, (
            f"a Galaxy S24 CASE was extracted as the phone: {r} — accessory must "
            f"be rejected on the JSON-LD path (the 11.9 confident-wrong-product)"
        )

    def test_real_galaxy_phone_jsonld_accepted(self):
        from app.services.price_service import extract_price_from_html
        r = extract_price_from_html(
            _GALAXY_PHONE_JSONLD, "Samsung Galaxy S24", "BHD",
            "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/samsung-galaxy-s24-256gb/")
        assert r is not None and abs(r["amount"] - 282.0) < 0.01
        assert r["source_method"] == "page_scrape"

    def test_is_accessory_extended_keywords(self):
        """The accessory keyword set covers the team-lead's list."""
        from app.services.price_service import is_accessory
        for acc in ["Galaxy S24 case", "iPhone 15 cover", "S24 screen protector",
                    "iPhone charger", "USB-C cable", "power adapter",
                    "phone stand", "car holder", "screen guard"]:
            assert is_accessory(acc) is True, f"{acc!r} not flagged accessory"
        # real products are NOT accessories
        for prod in ["Samsung Galaxy S24 256GB", "Apple iPhone 15 128GB",
                     "MacBook Air M3 13-inch"]:
            assert is_accessory(prod) is False, f"{prod!r} wrongly flagged accessory"

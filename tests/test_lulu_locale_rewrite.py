"""S3 Lulu BH-locale — deterministic /en-XX/ -> /en-bh/ locale rewrite for
same-slug multi-locale GCC retailers (Lulu).

INVESTIGATION (live, 2026-06-14): Lulu's BH store serves genuine BHD page_scrape
for the SAME product slug at /en-bh/, but Serper discovers wrong-locale URLs
(/en-ae/ /en-kw/ /en-qa/ /en-om/). Because Lulu uses an IDENTICAL slug across
locales, rewriting the locale segment to /en-bh/ hits the genuine BH PDP:
  Nutella /en-kw/ -> /en-bh/ = 3.34 BHD; Maybelline /en-om/ -> /en-bh/ = 7.825;
  Head&Shoulders /en-qa/ -> /en-bh/ = 1.59; Centrum /en-om/ -> /en-bh/ = 12.09.
This is OPPOSITE the sharafdg/extra case (different SKU IDs per locale → no
rewrite), so the rewrite is ALLOW-SET gated (Decision-F: only verified
same-slug retailers).
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


class TestRewriteToBhLocale:
    def test_lulu_wrong_locale_rewritten_to_bh(self):
        from app.services.source_router import rewrite_to_bh_locale
        cases = [
            ("https://gcc.luluhypermarket.com/en-kw/nutella-hazelnut-spread-750g/",
             "https://gcc.luluhypermarket.com/en-bh/nutella-hazelnut-spread-750g/"),
            ("https://gcc.luluhypermarket.com/en-ae/bertolli-olive-oil-1-litre/",
             "https://gcc.luluhypermarket.com/en-bh/bertolli-olive-oil-1-litre/"),
            ("https://www.luluhypermarket.com/en-om/centrum-women-60/",
             "https://www.luluhypermarket.com/en-bh/centrum-women-60/"),
            ("https://gcc.luluhypermarket.com/ar-qa/head-shoulders-shampoo/",
             "https://gcc.luluhypermarket.com/en-bh/head-shoulders-shampoo/"),
        ]
        for src, want in cases:
            assert rewrite_to_bh_locale(src) == want, f"rewrite of {src}"

    def test_lulu_already_bh_returns_none(self):
        """An already-/en-bh/ Lulu URL needs no rewrite → None (nothing to add)."""
        from app.services.source_router import rewrite_to_bh_locale
        assert rewrite_to_bh_locale(
            "https://gcc.luluhypermarket.com/en-bh/nutella/") is None

    def test_lulu_no_locale_segment_returns_none(self):
        """A Lulu URL with no recognizable locale segment → None (can't rewrite)."""
        from app.services.source_router import rewrite_to_bh_locale
        assert rewrite_to_bh_locale(
            "https://gcc.luluhypermarket.com/some/path/product/") is None

    def test_non_allowset_domain_returns_none(self):
        """sharafdg/extra are NOT same-slug across locales → NEVER rewrite (would
        404 / mis-attribute). Only the allow-set (lulu) rewrites."""
        from app.services.source_router import rewrite_to_bh_locale
        assert rewrite_to_bh_locale(
            "https://www.extra.com/en-sa/apple-iphone-15-128gb/") is None
        assert rewrite_to_bh_locale(
            "https://bahrain.sharafdg.com/en-sa/product/apple-iphone-15/") is None

    def test_empty_and_garbage(self):
        from app.services.source_router import rewrite_to_bh_locale
        assert rewrite_to_bh_locale("") is None
        assert rewrite_to_bh_locale(None) is None


class TestHarvestRewritesLuluLocale:
    def test_harvest_rewrites_lulu_wronglocale_to_bh(self):
        """A wrong-locale Lulu URL in discovery is REWRITTEN to /en-bh/ in the
        candidate pool (not dropped) — the +30% multi-category lever."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {
            "bahrain": {
                "organic": [
                    {"link": "https://gcc.luluhypermarket.com/en-kw/nutella-hazelnut-spread-750g/",
                     "title": "Nutella Hazelnut Spread 750g"},
                ]
            }
        }
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="grocery", query_name="Nutella")
        links = [h[0] for h in harvested]
        assert any("/en-bh/nutella-hazelnut-spread-750g" in l for l in links), (
            f"Lulu wrong-locale URL not rewritten to /en-bh/ in pool: {links}"
        )
        # the wrong-locale /en-kw/ original is NOT in the pool (rewritten, not kept).
        assert not any("/en-kw/" in l for l in links)

    def test_harvest_drops_non_allowset_wronglocale(self):
        """A wrong-locale extra.com URL is still DROPPED (no rewrite — SKUs differ)."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {
            "bahrain": {
                "organic": [
                    {"link": "https://www.extra.com/en-sa/apple-iphone-15-128gb/",
                     "title": "Apple iPhone 15 128GB"},
                ]
            }
        }
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="electronics",
                                            query_name="Apple iPhone 15")
        links = [h[0] for h in harvested]
        assert not any("extra.com" in l for l in links), (
            f"extra.com wrong-locale should be dropped, not rewritten: {links}"
        )


# Guardrail 2 (team-lead GO): currency-verify the rewritten PDP — the /en-bh/
# result must actually be BHD; a non-BHD JSON-LD offer is DROPPED (M1).
_LULU_BHD_JSONLD = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Nutella Hazelnut Spread 750g",
 "offers":{"@type":"Offer","priceCurrency":"BHD","price":1.86,"availability":"http://schema.org/InStock"}}
</script></head><body>Nutella</body></html>"""
# A (hypothetical) Lulu page that somehow served a NON-BHD offer — must be dropped.
_LULU_NONBHD_JSONLD = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Nutella Hazelnut Spread 750g",
 "offers":{"@type":"Offer","priceCurrency":"KWD","price":1.10,"availability":"http://schema.org/InStock"}}
</script></head><body>Nutella</body></html>"""


class TestRewrittenPdpCurrencyVerify:
    def test_bhd_jsonld_extracts_genuine(self):
        from app.services.price_service import extract_price_from_html
        r = extract_price_from_html(_LULU_BHD_JSONLD, "Nutella", "BHD",
                                    "gcc.luluhypermarket.com",
                                    "https://gcc.luluhypermarket.com/en-bh/nutella-750g/")
        assert r is not None and abs(r["amount"] - 1.86) < 0.01
        assert r["currency"] == "BHD"
        assert r["source_method"] == "page_scrape"

    def test_non_bhd_jsonld_is_dropped_not_blind_stamped(self):
        """A non-BHD JSON-LD offer on the rewritten page is NOT stamped BHD — the
        extractor's priceCurrency filter drops it (M1: no blind BHD stamp). With
        no other price source on the page → None."""
        from app.services.price_service import extract_price_from_html
        r = extract_price_from_html(_LULU_NONBHD_JSONLD, "Nutella", "BHD",
                                    "gcc.luluhypermarket.com",
                                    "https://gcc.luluhypermarket.com/en-bh/nutella-750g/")
        # the KWD offer is rejected by the BHD currency filter; no other price.
        # (extract MAY return a USD-fallback-converted dict if the JSON-LD had a
        # USD offer — here it's KWD, no USD/OG/microdata → None.)
        assert r is None or r.get("source_method") == "converted_usd", (
            f"a non-BHD Lulu offer was blind-stamped genuine: {r}"
        )
        if r is not None:
            assert r.get("source_method") != "page_scrape" or r.get("currency") == "BHD"
            assert r.get("original_currency", "BHD") != "KWD" or "converted" in r.get("source_method", "")


# Guardrail 3: graceful stock-miss fall-through — a rewritten /en-bh/ that 404s /
# has no price returns None (the rewrite ADDS a candidate; never fabricates/errors).
class TestStockMissFallThrough:
    def test_404_page_yields_none_not_error(self):
        """A 404/empty rewritten page → extract None (graceful), not an exception.
        (Live-confirmed: the Bertolli/specific-Nutella /en-bh/ slugs 404.)"""
        from app.services.price_service import extract_price_from_html
        r = extract_price_from_html("<html><body>404 Not Found</body></html>",
                                    "Bertolli olive oil", "BHD",
                                    "gcc.luluhypermarket.com",
                                    "https://gcc.luluhypermarket.com/en-bh/bertolli/")
        assert r is None  # no price, no crash — cascade falls through

    def test_harvest_still_adds_rewrite_even_if_pdp_may_404(self):
        """The harvest ADDS the rewritten candidate regardless (it can't know the
        PDP 404s until scraped); the scrape's None is what falls through."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {"bahrain": {"organic": [
            {"link": "https://gcc.luluhypermarket.com/en-kw/bertolli-olive-oil-1l/",
             "title": "Bertolli Olive Oil 1L"}]}}
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="grocery", query_name="Bertolli olive oil")
        links = [h[0] for h in harvested]
        assert any("/en-bh/bertolli-olive-oil-1l" in l for l in links)

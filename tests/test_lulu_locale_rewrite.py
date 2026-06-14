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

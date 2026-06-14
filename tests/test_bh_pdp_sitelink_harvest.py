"""S3 electronics-authority (prod-verify fix, prong b — piece 1) — sitelink
harvest for BH PDPs.

PROD-VERIFY trace (f9e0277): the combined `site:bahrain.sharafdg.com OR ...`
discovery for "iPhone 15" returned extra.com/en-sa + lulu/en-om noise as the
PRIMARY organic links, while the genuine sharafdg base PDP
(apple-iphone-15-128gb-pink-2) appeared only as a NESTED SITELINK — which
_harvest_candidate_urls (organic[].link only) never extracted. So the genuine
244.99 PDP never entered the scrape pool.

Fix (piece 1, $0): the bahrain tier ALSO harvests item["sitelinks"][].link that
are PDP-shaped (/product/) + pass score_source>=1.5 + variant_mismatch + locale.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


class TestSitelinkHarvest:
    def test_pdp_sitelink_is_harvested(self):
        """A genuine sharafdg base-iPhone-15 PDP nested in sitelinks is harvested
        into the candidate pool (it would be missed by organic[].link-only)."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {
            "bahrain": {
                "organic": [
                    {
                        # primary link is a sharafdg SEARCH/category page (not a PDP)
                        "link": "https://bahrain.sharafdg.com/?q=iphone+15&post_type=product",
                        "title": "iphone 15 - Sharaf DG Bahrain",
                        "sitelinks": [
                            {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black-with-facetime/",
                             "title": "Apple iPhone 15 128GB Black"},
                            {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-pink-2/",
                             "title": "Apple iPhone 15 128GB Pink"},
                        ],
                    }
                ]
            }
        }
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="electronics",
                                            query_name="Apple iPhone 15")
        links = [h[0] for h in harvested]
        assert any("/product/apple-iphone-15-128gb-black" in l for l in links), (
            f"genuine sharafdg base PDP sitelink not harvested; got {links}"
        )

    def test_variant_mismatch_sitelink_rejected(self):
        """A Pro/Pro Max PDP in sitelinks is NOT harvested for a base-15 query."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {
            "bahrain": {
                "organic": [
                    {
                        "link": "https://bahrain.sharafdg.com/?q=iphone+15",
                        "title": "iphone 15 - Sharaf DG",
                        "sitelinks": [
                            {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-pro-max-1tb/",
                             "title": "Apple iPhone 15 Pro Max 1TB"},
                        ],
                    }
                ]
            }
        }
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="electronics",
                                            query_name="Apple iPhone 15")
        links = [h[0] for h in harvested]
        assert not any("pro-max" in l for l in links), (
            f"a Pro Max variant PDP was harvested for a base-15 query: {links}"
        )

    def test_non_pdp_sitelink_not_harvested(self):
        """A category/search sitelink (not /product/) is not harvested."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {
            "bahrain": {
                "organic": [
                    {
                        "link": "https://bahrain.sharafdg.com/c/mobiles",
                        "title": "Mobiles - Sharaf DG",
                        "sitelinks": [
                            {"link": "https://bahrain.sharafdg.com/c/mobiles/apple/",
                             "title": "Apple Phones"},
                        ],
                    }
                ]
            }
        }
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="electronics",
                                            query_name="Apple iPhone 15")
        links = [h[0] for h in harvested]
        assert not any("/c/mobiles/apple" in l for l in links)

    def test_no_sitelinks_key_does_not_crash(self):
        """An organic item without a sitelinks key still works (back-compat)."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        results = {
            "bahrain": {
                "organic": [
                    {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-black/",
                     "title": "Apple iPhone 15 128GB Black"},
                ]
            }
        }
        harvested = _harvest_candidate_urls(results, official_domain=None,
                                            category="electronics",
                                            query_name="Apple iPhone 15")
        links = [h[0] for h in harvested]
        assert any("apple-iphone-15-128gb-black" in l for l in links)

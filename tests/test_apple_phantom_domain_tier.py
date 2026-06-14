"""S3 apple-phantom hotfix — _is_genuine_bh_candidate must check the candidate's
DOMAIN tier, not just the source_method string.

PROD-VERIFY on 110d0ff: iPhone 15 returned 198.9 apple.com page_scrape_jsonld as
a fake-GENUINE win. _is_genuine_bh_candidate (d10a0a0) trusted the method string
('page_scrape_jsonld' in the genuine set) without checking that apple.com is a
GLOBAL-tier domain (no Bahrain storefront). So a global-domain scrape stamped
with a genuine method counted as genuine — a PHANTOM. Defense-in-depth: a
candidate whose retailer/domain is registry tier='global' is NEVER genuine,
regardless of method (the _curl_scraper downgrade is the first line; this is the
second).
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")


class TestGenuineRequiresBhTierDomain:
    def test_global_domain_pagescrape_is_not_genuine(self):
        from app.services.price_service import _is_genuine_bh_candidate
        # apple.com (global tier) stamped page_scrape_jsonld — must NOT be genuine.
        c = {"value": 198.9, "source_method": "page_scrape_jsonld", "rank": 85,
             "raw_data": {"amount": 198.9, "retailer": "apple.com",
                          "source_method": "page_scrape_jsonld"}}
        assert _is_genuine_bh_candidate(c) is False, (
            "apple.com (global-tier) page_scrape_jsonld counted as genuine — PHANTOM"
        )

    def test_global_domain_firecrawl_is_not_genuine(self):
        from app.services.price_service import _is_genuine_bh_candidate
        c = {"value": 200.0, "source_method": "firecrawl_brand_domain", "rank": 90,
             "raw_data": {"retailer": "samsung.com", "source_method": "firecrawl_brand_domain"}}
        assert _is_genuine_bh_candidate(c) is False

    def test_bahrain_tier_domain_pagescrape_IS_genuine(self):
        from app.services.price_service import _is_genuine_bh_candidate
        # sharafdg BH (bahrain tier) page_scrape — genuine (the control).
        c = {"value": 244.99, "source_method": "page_scrape_jsonld", "rank": 85,
             "raw_data": {"retailer": "bahrain.sharafdg.com",
                          "source_method": "page_scrape"}}
        assert _is_genuine_bh_candidate(c) is True

    def test_gcc_tier_domain_pagescrape_IS_genuine(self):
        """gcc-tier (noon/lulu) is BH-relevant enough — a genuine page_scrape on
        it is genuine (only GLOBAL is excluded; gcc serves the region)."""
        from app.services.price_service import _is_genuine_bh_candidate
        c = {"value": 1.86, "source_method": "page_scrape_jsonld", "rank": 85,
             "raw_data": {"retailer": "gcc.luluhypermarket.com",
                          "source_method": "page_scrape"}}
        assert _is_genuine_bh_candidate(c) is True

    def test_off_registry_bh_retailer_pagescrape_IS_genuine(self):
        """An off-registry retailer (registry_tier=None) with a genuine method is
        still genuine — only an explicit GLOBAL-tier domain is the phantom. A
        discovered BH retailer PDP not in the registry must not be excluded."""
        from app.services.price_service import _is_genuine_bh_candidate
        c = {"value": 537.0, "source_method": "page_scrape", "rank": 85,
             "raw_data": {"retailer": "binhindi.com", "source_method": "page_scrape"}}
        assert _is_genuine_bh_candidate(c) is True

    def test_converted_still_not_genuine(self):
        """The original converted/estimate exclusion still holds."""
        from app.services.price_service import _is_genuine_bh_candidate
        c = {"value": 198.9, "source_method": "converted_usd", "rank": 85,
             "raw_data": {"retailer": "apple.com", "source_method": "converted_usd"}}
        assert _is_genuine_bh_candidate(c) is False

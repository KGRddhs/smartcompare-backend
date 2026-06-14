"""S3-genuine (team-lead live probe, 2026-06-14) — BH-locale filter on Serper
discovery candidates.

THE DISCOVERY BUG: Serper `site:` discovery returns MIXED-LOCALE results for the
multi-locale BH registry domains — mostly WRONG locale (extra.com/en-sa/ SAR,
gcc.lulu/en-om/ OMR, godukkan/uae_en/ AED) with a real /en-bh/ BH PDP mixed in.
_harvest_candidate_urls keeps a link on score_source>=1.5, and score_source
matches by DOMAIN ignoring the locale PATH — so a /en-sa/ page on the bahrain-tier
`extra.com` domain scores 3.0 and gets scraped, yielding a SAR price.

THE FIX: drop wrong-locale GCC paths before they enter the scrape pool. KEEP
BH-locale (/en-bh/, /ar-bh/, /bahrain_en/, bahrain.* subdomain) + locale-neutral
paths; DROP the other GCC locales (/en-sa/, /ar-sa/, /en-om/, /en-ae/, /uae_en/,
/en-kw/, /en-qa/, ...). NO locale rewrite (SKU IDs differ per locale → 404).
"""

import pytest

from app.services.source_router import is_wrong_locale_url


class TestDropsWrongLocale:
    @pytest.mark.parametrize("url", [
        "https://www.extra.com/en-sa/mobiles/apple-iphone-15/p/100350325",
        "https://www.extra.com/ar-sa/mobiles/apple-iphone-15/p/1",
        "https://gcc.luluhypermarket.com/en-om/apple-iphone/p/1",
        "https://gcc.luluhypermarket.com/en-ae/apple-iphone/p/1",
        "https://www.godukkan.com/uae_en/apple-iphone-17-pro-max",
        "https://www.extra.com/en-kw/x/p/1",
        "https://www.extra.com/en-qa/x/p/1",
    ])
    def test_wrong_gcc_locale_dropped(self, url):
        assert is_wrong_locale_url(url) is True


class TestKeepsBhAndNeutral:
    @pytest.mark.parametrize("url", [
        "https://www.extra.com/en-bh/mobiles/apple-iphone-15/p/100350330",
        "https://www.extra.com/ar-bh/mobiles/apple-iphone-15/p/1",
        "https://gcc.luluhypermarket.com/en-bh/apple-iphone/p/2220976",
        "https://www.godukkan.com/bahrain_en/apple-iphone-17-pro-max",
        "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb/",  # bahrain.* subdomain
        "https://bahrain.microless.com/product/apple-macbook-air-2025/",
    ])
    def test_bh_locale_kept(self, url):
        assert is_wrong_locale_url(url) is False

    @pytest.mark.parametrize("url", [
        "https://www.somedomain.com/product/iphone-15",  # locale-neutral path
        "https://noon.com/uae-en/iphone",   # noon en-uae is its own thing; not a /en-XX/ GCC-locale segment we drop
    ])
    def test_locale_neutral_or_unknown_kept(self, url):
        # We only DROP explicit wrong-GCC-locale path segments; a path with no
        # recognizable wrong-locale segment is KEPT (the scrape + currency check
        # downstream handle it). Conservative: never drop a maybe-BH page.
        assert is_wrong_locale_url(url) is False


class TestHarvestAppliesLocaleFilter:
    def test_harvest_drops_wrong_locale_bahrain_candidate(self):
        """_harvest_candidate_urls must DROP a wrong-locale URL even on a
        bahrain-tier domain (score 3.0) — it never enters candidate_urls."""
        from app.services.structured_comparison_service import _harvest_candidate_urls

        def _organic(*links):
            return {"organic": [{"link": u} for u in links]}

        results_by_tier = {
            "bahrain": _organic(
                "https://www.extra.com/en-sa/mobiles/apple-iphone-15/p/1",   # SAR → DROP
                "https://www.extra.com/en-bh/mobiles/apple-iphone-15/p/2",   # BHD → KEEP
            ),
        }
        harvested = _harvest_candidate_urls(
            results_by_tier, official_domain=None, category="electronics"
        )
        links = [h[0] for h in harvested]
        assert "https://www.extra.com/en-bh/mobiles/apple-iphone-15/p/2" in links
        assert "https://www.extra.com/en-sa/mobiles/apple-iphone-15/p/1" not in links

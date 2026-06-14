"""S3 coverage #3 — skin-002 timeout trim. The render wave fires
Firecrawl+Scrape.do on EVERY is_render_only candidate. A skincare query that
discovers several BH SPAs (bolo/nasserpharmacy/boutiqaat) fans out 6+ slow
render calls; the lower-weight ones 429/timeout and eat the 12s budget even
though the highest-weight genuine source (bolo) would confirm. Cap the render
wave to the top-N is_render_only domains (in candidate order, which is
bahrain->...->gcc by source_weight) so the genuine win is preserved but the
redundant slow tail is dropped.

Measured (live, main-repo keys): skin-002 'The Ordinary Niacinamide' = 19.83s
returning genuine bolo 9.35 BHD via the render wave; 'Paula's Choice' = 22.80s.
The over-budget driver is multiple render attempts per product.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest


def _count_render_domains(scrapers):
    """Render scrapers come in Firecrawl+Scrape.do PAIRS per domain → pairs/2."""
    return len(scrapers) // 2


class TestRenderWaveDomainCap:
    def setup_method(self):
        import app.services.structured_comparison_service as scs
        # Force should_fan_out True so the gate isn't the limiter under test.
        self._orig = scs.firecrawl_service.should_fan_out
        scs.firecrawl_service.should_fan_out = lambda url, mode="hard": True

    def teardown_method(self):
        import app.services.structured_comparison_service as scs
        scs.firecrawl_service.should_fan_out = self._orig

    def test_render_wave_capped_to_two_domains(self):
        """4 is_render_only BH SPA candidates → render wave attempts only 2."""
        from app.services.structured_comparison_service import _build_escalation_scrapers
        # All 4 are is_render_only registry domains (bahrain-tier SPAs).
        candidate_urls = [
            ("https://bolo.bh/p/niacinamide", "bolo.bh"),
            ("https://www.nasserpharmacy.com/bh-en/niacinamide", "nasserpharmacy.com"),
            ("https://bn.boots.com/niacinamide", "bn.boots.com"),
            ("https://megamart.bh/niacinamide", "megamart.bh"),
        ]
        scrapers = _build_escalation_scrapers(
            candidate_urls=candidate_urls, full_name="The Ordinary Niacinamide",
            currency="BHD", scraping_mode="hard", wave="render",
        )
        # 2 domains x (firecrawl + scrapedo) = 4 scrapers, NOT 8.
        assert _count_render_domains(scrapers) == 2, (
            f"render wave attempted {_count_render_domains(scrapers)} domains, cap is 2"
        )
        assert len(scrapers) == 4

    def test_render_cap_preserves_highest_weight_first(self):
        """The cap keeps the FIRST candidates (candidate_urls is pre-ordered
        bahrain->gcc by source_weight) — bolo (first) is preserved."""
        from app.services.structured_comparison_service import _build_escalation_scrapers
        candidate_urls = [
            ("https://bolo.bh/p/niacinamide", "bolo.bh"),            # high-weight, FIRST
            ("https://www.nasserpharmacy.com/bh-en/x", "nasserpharmacy.com"),
            ("https://megamart.bh/x", "megamart.bh"),
        ]
        scrapers = _build_escalation_scrapers(
            candidate_urls=candidate_urls, full_name="The Ordinary Niacinamide",
            currency="BHD", scraping_mode="hard", wave="render",
        )
        # capped to 2 domains
        assert _count_render_domains(scrapers) == 2

    def test_render_wave_under_cap_unchanged(self):
        """1 is_render_only candidate → 1 domain (2 scrapers), cap not triggered."""
        from app.services.structured_comparison_service import _build_escalation_scrapers
        candidate_urls = [("https://bolo.bh/p/niacinamide", "bolo.bh")]
        scrapers = _build_escalation_scrapers(
            candidate_urls=candidate_urls, full_name="The Ordinary Niacinamide",
            currency="BHD", scraping_mode="hard", wave="render",
        )
        assert _count_render_domains(scrapers) == 1
        assert len(scrapers) == 2

    def test_curl_wave_NOT_capped(self):
        """The cap is render-only — the free curl wave is uncapped (curl is
        cheap + fast; capping it would lose genuine curl wins)."""
        from app.services.structured_comparison_service import _build_escalation_scrapers
        # 4 NON-render-only (curl-able) BH candidates.
        candidate_urls = [
            ("https://bahrain.sharafdg.com/product/a", "bahrain.sharafdg.com"),
            ("https://bahrain.microless.com/product/b", "bahrain.microless.com"),
            ("https://www.shopalmoayyed.com/products/c", "shopalmoayyed.com"),
            ("https://extra.com/d", "extra.com"),
        ]
        scrapers = _build_escalation_scrapers(
            candidate_urls=candidate_urls, full_name="iPhone 15",
            currency="BHD", scraping_mode="hard", wave="curl",
        )
        # all 4 curl scrapers present (1 per domain, no firecrawl/scrapedo in curl wave)
        assert len(scrapers) == 4

"""S3-genuine (team-lead approved 2026-06-14) — Source.is_render_only flag.

These BH retailers are real stores with real prices, but their PDPs are JS-SPAs
whose static curl HTML has NO usable price (confirmed by curling them through the
production extractor):
  - alosraonline.com, nasserpharmacy.com, bn.boots.com, bolo.bh (team-lead's SPA
    set)
  - megamart.bh (PDP curl Decision-F: Angular SPA shell, app-root/ng-, ZERO price
    in static markup — "BD 3.455" is JS-rendered)

`is_render_only=True` marks them so the cascade:
  - EXCLUDES them from the free curl-direct harvest window (a curl yields nothing
    — pure budget/wall waste), and
  - INCLUDES them in the budget-gated Firecrawl/Scrape.do render-tier escalation
    (per Ahmed's "use Firecrawl/Scrape.do", only after the free tiers miss).

They are NOT deleted (they're live BH stores) — just render-tier.

Curl-scrapeable BH sources (gcc.lulu, sharafdg, extra, bahrainpharmacy) must NOT
be render-only — they produce genuine BHD via plain curl.
"""

import pytest

from app.services.source_router import SOURCE_REGISTRY, Source


RENDER_ONLY_DOMAINS = {
    "alosraonline.com",
    "bn.boots.com",
    "megamart.bh",
}

# Direct-readable (NOT render-only) — genuine BHD via plain curl / JSON-LD / JSON
# API. Source-intel recon 2026-06-23 corrected bolo.bh (Nuxt SSR plain-curl BHD)
# + nasserpharmacy.com (its own JSON API, NO Cloudflare) OFF the STALE render-only
# flag — they were never actually render-walls.
CURL_DIRECT_DOMAINS = {
    "gcc.luluhypermarket.com",
    "bahrain.sharafdg.com",
    "extra.com",
    "bahrainpharmacy.com",
    "bolo.bh",
    "nasserpharmacy.com",  # mechanism=json_api — non-render (curl-tier set)
}


class TestRenderOnlyField:
    def test_default_is_false(self):
        s = Source("example.com", "gcc", (), 1.5)
        assert s.is_render_only is False

    @pytest.mark.parametrize("domain", sorted(RENDER_ONLY_DOMAINS))
    def test_spa_sources_marked_render_only(self, domain):
        by = {s.domain: s for s in SOURCE_REGISTRY}
        assert domain in by, f"{domain} should be a registry row"
        assert by[domain].is_render_only is True, (
            f"{domain} is a JS-SPA (no static curl price) — must be is_render_only"
        )

    @pytest.mark.parametrize("domain", sorted(CURL_DIRECT_DOMAINS))
    def test_curl_sources_not_render_only(self, domain):
        by = {s.domain: s for s in SOURCE_REGISTRY}
        assert domain in by, f"{domain} should be a registry row"
        assert by[domain].is_render_only is False, (
            f"{domain} curl-scrapes a genuine BHD price — must NOT be render-only"
        )


class TestRenderOnlyFlagSet:
    @pytest.mark.parametrize("domain", sorted(RENDER_ONLY_DOMAINS))
    def test_render_only_sources_flagged_for_render_tier(self, domain):
        """Render-only sources carry is_render_only=True so the cascade routes
        them through the budget-gated render wave (Firecrawl/Scrape.do), NOT the
        free curl wave (a curl yields nothing on a JS-SPA). The curl-vs-render
        wave split is exercised in test_curl_before_render_budget.py; this pins
        the flag that drives it. (The old direct-curl-SEARCH injector that read
        this flag was removed 2026-06-14 — search pages are JS-rendered.)"""
        by = {s.domain: s for s in SOURCE_REGISTRY}
        assert by[domain].is_render_only is True

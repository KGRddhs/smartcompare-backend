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
    "nasserpharmacy.com",
    "bn.boots.com",
    "bolo.bh",
    "megamart.bh",
}

# These curl-scrape fine — must stay curl-tier (is_render_only False).
CURL_DIRECT_DOMAINS = {
    "gcc.luluhypermarket.com",
    "bahrain.sharafdg.com",
    "extra.com",
    "bahrainpharmacy.com",
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


class TestRenderOnlyExcludedFromDirectCurl:
    def test_render_only_excluded_from_build_direct_bh_candidates(self):
        """The Serper-independent direct-curl injector must NOT emit render-only
        sources (a curl yields nothing — wasted fetch). nasserpharmacy is a
        supplements render-only source; it must be absent from the curl-direct
        supplements candidates."""
        from app.services.price_service import build_direct_bh_candidates
        cands = build_direct_bh_candidates("vitamin d 1000iu", "supplements")
        urls = " ".join(u for u, _ in cands)
        for dom in RENDER_ONLY_DOMAINS:
            assert dom not in urls, (
                f"{dom} is render-only — must not be a direct-curl candidate"
            )

"""S3-genuine (Approach A part 2, team-lead-approved 2026-06-14) — curl-before-render
budget split.

THE BUDGET VIOLATION (my fan_out audit): _build_escalation_scrapers emitted
curl + Firecrawl + Scrape.do per URL into ONE fan_out that launched them all
CONCURRENTLY — so paid render fired on EVERY escalated comparison, even when a
free curl already had the BH price. Ahmed: "don't overcrowd; render only on
curl-miss."

THE FIX: two waves. The FREE curl wave runs first (early-exit on a plausible
genuine price); the paid Firecrawl/Scrape.do RENDER wave fires ONLY if the curl
wave misses.

Tests the wave param (unit) + the budget invariant (render scrapers NOT built
when the curl wave lands a price).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestWaveParam:
    def test_curl_wave_emits_only_curl(self, monkeypatch):
        """wave='curl' → only the curl scraper. For an is_render_only domain the
        'all' wave emits render (Fix B: render fires for is_render_only); the
        'curl' wave skips it (Fix A: curl is wasted on a SPA)."""
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        # A curl-tier BH domain (sharafdg): 'curl'=1, 'all'=1 (NO render — Fix B
        # scopes render to is_render_only only).
        sharafdg = [("https://bahrain.sharafdg.com/product/iphone-15/", "bahrain.sharafdg.com")]
        assert len(scs_mod._build_escalation_scrapers(
            candidate_urls=sharafdg, full_name="iPhone 15", currency="BHD",
            scraping_mode="hard", wave="curl")) == 1
        assert len(scs_mod._build_escalation_scrapers(
            candidate_urls=sharafdg, full_name="iPhone 15", currency="BHD",
            scraping_mode="hard", wave="all")) == 1  # curl only, no render

    def test_render_wave_emits_render_only_for_render_only_domain(self, monkeypatch):
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        # Fix B: the render wave fires ONLY for is_render_only domains. A curl-tier
        # BH domain (sharafdg) gets NO render scraper (it curl-scrapes); an
        # is_render_only domain (nasserpharmacy) gets 2 (firecrawl+scrapedo).
        sharafdg = scs_mod._build_escalation_scrapers(
            candidate_urls=[("https://bahrain.sharafdg.com/product/iphone-15/", "bahrain.sharafdg.com")],
            full_name="iPhone 15", currency="BHD", scraping_mode="hard", wave="render",
        )
        assert len(sharafdg) == 0  # curl-tier → no render
        nasser = scs_mod._build_escalation_scrapers(
            candidate_urls=[("https://www.bn.boots.com/p/vitamin-d", "bn.boots.com")],
            full_name="Vitamin D", currency="BHD", scraping_mode="hard", wave="render",
        )
        assert len(nasser) == 2  # is_render_only → firecrawl + scrapedo

    def test_default_wave_is_all(self, monkeypatch):
        """Default wave='all'. Post-Fix-B counts: a curl-tier domain (sharafdg)
        → 1 (curl only, render scoped out); an is_render_only domain
        (nasserpharmacy) → 2 (curl skipped + render)."""
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        sharafdg = scs_mod._build_escalation_scrapers(
            candidate_urls=[("https://bahrain.sharafdg.com/product/iphone-15/", "bahrain.sharafdg.com")],
            full_name="iPhone 15", currency="BHD", scraping_mode="hard",
        )
        assert len(sharafdg) == 1  # curl only (Fix B: no render for curl-tier)
        nasser = scs_mod._build_escalation_scrapers(
            candidate_urls=[("https://www.bn.boots.com/p/x", "bn.boots.com")],
            full_name="x", currency="BHD", scraping_mode="hard",
        )
        assert len(nasser) == 2  # curl skipped (is_render_only) + render


class TestRenderOnlySourceRouting:
    """is_render_only INCLUSION side (team-lead Approach-A): an is_render_only
    SPA source (its Serper-discovered PDP) must SKIP the curl wave (a curl yields
    nothing on a JS-SPA — wasted fetch) and be INCLUDED in the render wave."""

    def test_render_only_url_skips_curl_wave(self, monkeypatch):
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        # bn.boots.com is an is_render_only registry source.
        urls = [("https://www.bn.boots.com/p/vitamin-d", "bn.boots.com")]
        curl_wave = scs_mod._build_escalation_scrapers(
            candidate_urls=urls, full_name="Vitamin D", currency="BHD",
            scraping_mode="hard", wave="curl",
        )
        # No curl scraper for an is_render_only source — a curl is wasted on a SPA.
        assert len(curl_wave) == 0

    def test_render_only_url_included_in_render_wave(self, monkeypatch):
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        urls = [("https://www.bn.boots.com/p/vitamin-d", "bn.boots.com")]
        render_wave = scs_mod._build_escalation_scrapers(
            candidate_urls=urls, full_name="Vitamin D", currency="BHD",
            scraping_mode="hard", wave="render",
        )
        # firecrawl + scrapedo = 2 — the render-only source IS routed into render.
        assert len(render_wave) == 2

    def test_curl_source_still_gets_curl_scraper(self, monkeypatch):
        """A non-render-only BH source (sharafdg) STILL gets its curl scraper in
        the curl wave (regression — the is_render_only skip must not over-apply)."""
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        urls = [("https://bahrain.sharafdg.com/product/iphone-15/", "bahrain.sharafdg.com")]
        curl_wave = scs_mod._build_escalation_scrapers(
            candidate_urls=urls, full_name="iPhone 15", currency="BHD",
            scraping_mode="hard", wave="curl",
        )
        assert len(curl_wave) == 1  # sharafdg curl-scrapes fine


class TestRenderWaveBhOnly:
    """Fix B (prod rollback 2026-06-14) — the render wave must fire ONLY on
    is_render_only BH-registry domains, NEVER on gl=us GLOBAL organic URLs.

    THE PROD BUG: _harvest pulls official/gcc tiers (samsung.com/us, amazon.ae)
    into candidate_urls; the part-2 render wave fired Firecrawl/Scrape.do on them
    via should_fan_out=True → 6+ slow render calls → blew the 15s price cap →
    price returned None. Scoping render to is_render_only kills both the
    budget-burn AND the timeout."""

    @pytest.mark.parametrize("url,domain", [
        ("https://www.samsung.com/us/smartphones/galaxy-s24/", "samsung.com"),
        ("https://www.samsung.com/in/smartphones/galaxy-s24/", "samsung.com"),
        ("https://www.amazon.ae/dp/B0XXX", "amazon.ae"),
    ])
    def test_render_wave_emits_zero_for_global_url(self, monkeypatch, url, domain):
        from app.services import structured_comparison_service as scs_mod
        # should_fan_out is True in hard mode (prod default) — but Fix B's
        # is_render_only gate must override it for non-BH globals.
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        render = scs_mod._build_escalation_scrapers(
            candidate_urls=[(url, domain)], full_name="Galaxy S24", currency="BHD",
            scraping_mode="hard", wave="render",
        )
        assert len(render) == 0, (
            f"render wave must NOT fire on the global URL {url} (prod budget-burn + timeout)"
        )

    def test_mixed_candidates_render_only_bh(self, monkeypatch):
        """A mix of global (samsung.com/us) + is_render_only BH (nasserpharmacy)
        → render wave fires ONLY for the BH render-only one (2 scrapers)."""
        from app.services import structured_comparison_service as scs_mod
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )
        urls = [
            ("https://www.samsung.com/us/x", "samsung.com"),       # global → 0
            ("https://www.amazon.ae/dp/x", "amazon.ae"),            # gcc global → 0
            ("https://www.bn.boots.com/p/x", "bn.boots.com"),  # BH render-only → 2
        ]
        render = scs_mod._build_escalation_scrapers(
            candidate_urls=urls, full_name="x", currency="BHD",
            scraping_mode="hard", wave="render",
        )
        assert len(render) == 2  # only nasserpharmacy's firecrawl + scrapedo


@pytest.fixture
def clean_service(monkeypatch):
    from app.services import structured_comparison_service as scs_mod
    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    service = scs_mod.get_comparison_service()
    service._save_price_to_db = MagicMock()
    return service


class TestRenderNotBuiltOnCurlHit:
    @pytest.mark.asyncio
    async def test_render_wave_skipped_when_curl_lands_bh(self, monkeypatch, clean_service):
        """THE BUDGET INVARIANT: when the curl wave lands a genuine BH price, the
        RENDER wave's scrapers are NEVER built (no Firecrawl/Scrape.do credits
        burned)."""
        from app.services import structured_comparison_service as scs_mod

        # Tier-1 empty → escalate. BH discovery returns a PDP.
        monkeypatch.setattr(
            scs_mod, "search_product_prices",
            AsyncMock(return_value={"shopping": [], "organic": []}),
        )
        monkeypatch.setattr(scs_mod, "extract_price_from_shopping", lambda *a, **kw: None)
        monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
        monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
        # Neutralize the free genuine-BH direct-fetch selectors: electronics now
        # carries a live is_algolia sharafdg + mechanism="unbxd" extra.com source
        # that returns a genuine local_bhd price BEFORE the curl/render fan_out,
        # short-circuiting the escalation this budget invariant is meant to pin.
        monkeypatch.setattr(scs_mod, "get_algolia_sources_for_category", lambda cat: [])
        monkeypatch.setattr(scs_mod, "get_unbxd_sources_for_category", lambda cat: [])
        # Wave C C3 — the noon-BH literal fires a REAL fetch too; neutralize alike.
        monkeypatch.setattr(scs_mod, "get_noon_sources_for_category", lambda cat: [])
        monkeypatch.setattr(
            scs_mod, "search_web",
            AsyncMock(return_value={"organic": [
                {"link": "https://bahrain.sharafdg.com/product/iphone-15/"}
            ]}),
        )
        monkeypatch.setattr(
            scs_mod.firecrawl_service, "should_fan_out", lambda *a, **k: True
        )

        # Record which waves _build_escalation_scrapers is called with.
        waves_built = []
        real_build = scs_mod._build_escalation_scrapers

        def _spy_build(*, candidate_urls, full_name, currency, scraping_mode, wave="all"):
            waves_built.append(wave)
            return real_build(
                candidate_urls=candidate_urls, full_name=full_name,
                currency=currency, scraping_mode=scraping_mode, wave=wave,
            )
        monkeypatch.setattr(scs_mod, "_build_escalation_scrapers", _spy_build)

        # The CURL wave lands a genuine BH price → fan_out returns it.
        async def _fan(product, *, scrapers, scraping_mode):
            return {"best": {
                "raw_data": {"amount": 244.990, "currency": "BHD",
                             "retailer": "bahrain.sharafdg.com",
                             "source_method": "page_scrape_jsonld"},
                "source_method": "page_scrape_jsonld",
            }}
        monkeypatch.setattr(scs_mod, "fan_out_price_lookup", _fan)

        result = await clean_service._get_price(
            brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
            search_query="Apple iPhone 15 128GB price", nocache=True,
            category="electronics",
        )
        assert result is not None
        assert result["amount"] == pytest.approx(244.990)
        # THE INVARIANT: only the curl wave ran; the render wave was NEVER built.
        assert "curl" in waves_built
        assert "render" not in waves_built, (
            f"render wave built despite curl-wave hit (budget burn): {waves_built}"
        )

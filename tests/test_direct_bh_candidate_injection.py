"""S3-genuine — build_direct_bh_candidates (the curl-search injector) is RETAINED
but NEUTRALIZED at the cascade call site.

The pivot idea was: construct each BH-tier non-Shopify source's SEARCH URL from
the registry (zero Serper) and prepend to candidate_urls so fan_out curls them
even with Serper down. The team-lead's live probe (2026-06-14, WRINKLE 2) — and
our own captures (gf_lulu/sharafdg_search/lulu_search all extract None) —
DISPROVED the search-page path: gcc.lulu /en-bh/search/?q= → 404; sharafdg ?s= →
JS-rendered (0 JSON-LD/itemprop, PDP links are noise). A curl-only search→PDP
path can't reach the PDPs (slugs are product-specific). So the prepend is NOT
wired — it only burned fan_out fetches. PDP discovery comes from the Serper
`site:` query (live again); Serper-independence is Shopify /products.json (works)
+ a future Firecrawl-render-search (deferred, budget-gated).

The PURE FUNCTION is kept (URL construction + Shopify/render-only exclusion) as
the shell for that future render-search path — these tests pin its contract. The
integration test pins that it is NOT prepended into the live cascade.
"""

import pytest

from app.services.price_service import build_direct_bh_candidates


def _urls(candidates):
    return [u for u, _label in candidates]


class TestConstructsBhRetailerUrls:
    def test_electronics_includes_lulu_and_extra(self):
        cands = build_direct_bh_candidates("iPhone 15", "electronics")
        urls = _urls(cands)
        # gcc.lulu BHD storefront + extra BH — both constructed without Serper.
        assert any("gcc.luluhypermarket.com/en-bh/search" in u for u in urls)
        assert any("extra.com/en-bh/search" in u for u in urls)

    def test_sharafdg_domain_resolves_to_bh_template(self):
        """REGRESSION: bahrain.sharafdg.com must resolve to its BH WooCommerce
        search URL. The RETAILER_SEARCH_URLS key was 'sharaf dg' (with a space)
        which the domain (no space) never matched — so sharafdg was silently
        dropped from the direct injector. It must be present."""
        cands = build_direct_bh_candidates("iPhone 15", "electronics")
        urls = _urls(cands)
        assert any("bahrain.sharafdg.com" in u for u in urls), (
            "sharafdg must be a direct BH candidate (domain->template resolution)"
        )

    def test_query_is_url_encoded(self):
        cands = build_direct_bh_candidates("Samsung Galaxy S24 Ultra", "electronics")
        urls = _urls(cands)
        # spaces encoded (either + or %20), never a raw space in the URL.
        for u in urls:
            assert " " not in u

    def test_label_carries_domain(self):
        cands = build_direct_bh_candidates("iPhone 15", "electronics")
        # The label should identify the BH retailer (for the source_trace), not
        # be empty — fan_out + harvest carry (url, label).
        for url, label in cands:
            assert label and isinstance(label, str)


class TestSerperIndependence:
    def test_no_serper_no_network_pure(self, monkeypatch):
        """The function must not call search_web / any network — it is pure URL
        construction. (If it imported/called search_web this would raise.)"""
        import app.services.price_service as ps
        # If the impl ever reaches for search_web, fail loudly.
        if hasattr(ps, "search_web"):
            monkeypatch.setattr(
                ps, "search_web",
                lambda *a, **k: (_ for _ in ()).throw(
                    AssertionError("build_direct_bh_candidates must not call search_web")
                ),
            )
        cands = build_direct_bh_candidates("iPhone 15", "electronics")
        assert isinstance(cands, list)
        assert len(cands) >= 2


class TestShopifyExclusion:
    def test_shopify_sources_not_duplicated_here(self):
        """Shopify BH stores (asgharali/almoayyed/ajmal/alhajis) already have a
        dedicated Serper-independent /products.json path — they must NOT also be
        injected here (would double-fetch + the search-URL path is wrong for
        them). Fragrances: the direct injector should yield only NON-Shopify BH
        sources (and may be empty if a category's BH tier is all-Shopify)."""
        cands = build_direct_bh_candidates("Tom Ford Oud Wood", "fragrances")
        urls = _urls(cands)
        # asgharali/ajmal/alhajis are Shopify → excluded from the direct injector.
        assert not any("asgharali" in u for u in urls)
        assert not any("ajmal" in u for u in urls)
        assert not any("alhajis" in u for u in urls)


class TestEmptyForNoBhSources:
    def test_unknown_category_yields_list(self):
        # 'other' has only all-category BH sources (gcc.lulu) — still returns a
        # list (never None); the caller prepends whatever it gets.
        cands = build_direct_bh_candidates("some gadget", "other")
        assert isinstance(cands, list)


# ---------- Integration: the wiring injects direct BH candidates with Serper DEAD ----------

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock


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


@pytest.mark.asyncio
async def test_direct_bh_candidates_NOT_injected_into_cascade(monkeypatch, clean_service):
    """NEUTRALIZED (WRINKLE 2): build_direct_bh_candidates is NOT prepended into
    candidate_urls. The BH SEARCH-URL path was proven dead (search pages are
    JS-rendered / 404 — they carry no extractable price), so wiring it only
    burned fan_out fetches. With Serper DEAD (search_web no-ops) AND no Shopify
    hit, the curl-search injector must NOT have slipped gcc.lulu/sharafdg search
    URLs into the scraper builder — candidate_urls is empty and the cascade
    falls through to tier-8 (until Serper-discovery, live again, supplies the
    PDP)."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": []}),
    )
    monkeypatch.setattr(scs_mod, "extract_price_from_shopping", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))

    captured = {"built": False}

    def _capture_scrapers(*, candidate_urls, full_name, currency, scraping_mode):
        captured["built"] = True
        captured["urls"] = list(candidate_urls)
        return []

    monkeypatch.setattr(scs_mod, "_build_escalation_scrapers", _capture_scrapers)
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={"best": None}),
    )
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 250.0, "currency": "BHD"}, {})),
    )

    await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )

    # Either the scraper-builder never ran (candidate_urls empty → guarded out),
    # or it ran with NO injected BH search URLs. Both prove the injector is not
    # wired — the dead search URLs must NOT reach fan_out.
    injected = " ".join(u for u, _ in captured.get("urls", []))
    assert "gcc.luluhypermarket.com" not in injected, (
        "curl-search injector leaked a gcc.lulu SEARCH url into fan_out (it's dead)"
    )
    assert "bahrain.sharafdg.com" not in injected, (
        "curl-search injector leaked a sharafdg SEARCH url into fan_out (it's dead)"
    )

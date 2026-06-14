"""S3-genuine (team-lead pivot 2026-06-14) — Serper-INDEPENDENT direct-BH
candidate injection.

THE GAP the pivot exposed: the BH registry retailers (gcc.lulu, sharafdg, extra,
godukkan, microless, ...) reach the price scraper ONLY via search_web(bahrain
site:-query) -> _harvest_candidate_urls -> fan_out. search_web NO-OPS without a
Serper key, so when the Serper account is dry, candidate_urls is empty and
fan_out never curls these directly-scrapeable BH pages. (Only the Shopify
/products.json path — asgharali/almoayyed/ajmal/alhajis — is Serper-independent
today, which is why fragrances work offline but electronics don't.)

THE FIX: `build_direct_bh_candidates(full_name, category)` constructs each
BH-tier NON-Shopify source's search/PDP URL straight from the registry +
RETAILER_SEARCH_URLS, with NO Serper call. These are PREPENDED to candidate_urls
so fan_out curls them regardless of Serper state. Purely additive — Serper
results still merge in when the account is funded.

Pure-function tests (no live calls). The price-extraction one-hop-vs-two-hop
question (search page vs PDP) is answered by a live probe; this pins the URL
construction + Serper-independence + Shopify-exclusion invariants.
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
async def test_direct_bh_candidates_injected_when_serper_dead(monkeypatch, clean_service):
    """THE pivot invariant: with Serper completely DEAD (search_web no-ops,
    Shopping empty), the Tier-1.5 fan_out STILL receives the direct BH retailer
    URLs (gcc.lulu, sharafdg) — built straight from the registry, zero Serper.
    Pre-fix candidate_urls was empty and fan_out never ran; now it does."""
    from app.services import structured_comparison_service as scs_mod

    # Serper Shopping empty → escalation fires.
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": []}),
    )
    monkeypatch.setattr(scs_mod, "extract_price_from_shopping", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    # Serper DEAD — search_web returns nothing (the dry-account state).
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    # No Shopify hit (electronics has no Shopify BH store in play here).
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))

    # Capture the candidate_urls handed to the scraper builder.
    captured = {}

    def _capture_scrapers(*, candidate_urls, full_name, currency, scraping_mode):
        captured["urls"] = list(candidate_urls)
        return []  # no scrapers → fan_out yields nothing → falls to tier-8

    monkeypatch.setattr(scs_mod, "_build_escalation_scrapers", _capture_scrapers)
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={"best": None}),
    )
    # Tier-8 estimate so _get_price completes.
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 250.0, "currency": "BHD"}, {})),
    )

    await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )

    assert "urls" in captured, "fan_out scraper-build never ran — candidate_urls was empty (the bug)"
    all_urls = " ".join(u for u, _ in captured["urls"])
    assert "gcc.luluhypermarket.com" in all_urls, (
        "direct gcc.lulu BH candidate was NOT injected with Serper dead"
    )
    assert "bahrain.sharafdg.com" in all_urls, (
        "direct sharafdg BH candidate was NOT injected with Serper dead"
    )

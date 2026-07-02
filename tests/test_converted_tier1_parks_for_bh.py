"""S3-genuine (Approach A, team-lead-approved 2026-06-14) — a CONVERTED_USD Tier-1
price is PARKED, not short-circuited, so the genuine-BH curl tier runs and wins.

THE KEYSTONE (e2e-proven twice): a plausible gl=us Tier-1 Serper-Shopping price
(converted_usd) RETURNED at the Tier-1 block BEFORE the Tier-1.5 BH scrape ran —
so iPhone resolved converted_usd even though sharafdg/extra extract genuine BHD.
§5 ordering: genuine-BH (tier 1-5) MUST beat converted_usd (tier-7).

THE FIX: a GENUINE Tier-1 price (local_bhd / page_scrape) may still early-exit;
a CONVERTED_USD Tier-1 price is PARKED and the cascade continues to Tier-1.5. The
parked converted price is the fallback ONLY after the BH curl+render tiers miss
(before the GPT estimate).

Drives _get_price end-to-end with the Tier-1.5 BH scrape stubbed.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def clean_service(monkeypatch):
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    # Neutralize the free genuine-BH direct-fetch selectors — electronics now
    # carries a live is_algolia sharafdg + mechanism="unbxd" extra.com source that
    # fires a REAL network fetch and returns a genuine local_bhd price BEFORE the
    # converted-parking / render-budget fallthrough these tests pin.
    monkeypatch.setattr(scs_mod, "get_algolia_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs_mod, "get_unbxd_sources_for_category", lambda cat: [])
    monkeypatch.setattr(scs_mod, "get_shopify_sources_for_category", lambda cat: [])
    # Wave C C3 — the noon-BH literal fires a REAL fetch too; neutralize alike.
    monkeypatch.setattr(scs_mod, "get_noon_sources_for_category", lambda cat: [])
    service = scs_mod.get_comparison_service()
    service._save_price_to_db = MagicMock()
    return service


def _converted_tier1(monkeypatch, scs_mod):
    """Tier-1 Serper Shopping returns a gl=us converted price (Walmart, low score)
    — the iPhone-keystone shape."""
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={
            "shopping": [{
                "title": "Apple iPhone 15 128GB",
                "price": "$799.00",   # ~300 BHD converted
                "source": "Walmart - YYWireless",
                "link": "https://www.walmart.com/ip/iphone-15",
            }],
            "organic": [],
            "shopping_region": "us_fallback",
        }),
    )


@pytest.mark.asyncio
async def test_converted_tier1_parked_bh_scrape_wins(monkeypatch, clean_service):
    """A converted_usd Tier-1 price is PARKED; the Tier-1.5 BH curl returns a
    genuine local_bhd (sharafdg 244.99) which WINS. iPhone resolves local_bhd,
    not converted_usd."""
    from app.services import structured_comparison_service as scs_mod

    _converted_tier1(monkeypatch, scs_mod)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    # Tier-1.5 discovery returns a BH PDP; fan_out curls it → genuine local_bhd.
    monkeypatch.setattr(
        scs_mod, "search_web",
        AsyncMock(return_value={"organic": [
            {"link": "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb/"}
        ]}),
    )
    monkeypatch.setattr(
        scs_mod, "fan_out_price_lookup",
        AsyncMock(return_value={"best": {
            "raw_data": {"amount": 244.990, "currency": "BHD",
                         "retailer": "bahrain.sharafdg.com",
                         "source_method": "page_scrape"},
            "source_method": "page_scrape",
        }}),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    assert result is not None
    # The genuine BH scrape WINS — not the parked converted_usd.
    assert result["amount"] == pytest.approx(244.990)
    assert result["source_method"] in ("page_scrape", "local_bhd")
    assert result["source_method"] != "converted_usd"
    assert result["source_method"] != "estimated"


@pytest.mark.asyncio
async def test_converted_tier1_used_when_bh_misses(monkeypatch, clean_service):
    """When the BH curl+render tiers MISS, the parked converted_usd is the
    fallback — and it BEATS the GPT estimate (§5: converted tier-7 > estimate
    tier-8)."""
    from app.services import structured_comparison_service as scs_mod

    _converted_tier1(monkeypatch, scs_mod)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    # BH discovery + fan_out yield NOTHING (the BH-miss case).
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(scs_mod, "search_price_organic",
                        AsyncMock(return_value={"organic": [], "knowledge_graph": None}))
    monkeypatch.setattr(scs_mod, "extract_price", AsyncMock(return_value=(None, {})))
    # A GPT estimate exists — but the parked converted price must win over it.
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 290.0, "currency": "BHD"}, {})),
    )

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    assert result is not None
    # The parked converted_usd is the fallback — NOT the estimate.
    assert result["source_method"] == "converted_usd"
    assert result["source_method"] != "estimated"
    assert result.get("estimated") is not True


@pytest.mark.asyncio
async def test_global_only_escalation_builds_no_render_scrapers(monkeypatch, clean_service):
    """Fix B structural latency proof (prod rollback): when the BH discovery
    surfaces ONLY a GLOBAL url (samsung.com/us — the prod-bug shape), the render
    wave must build ZERO render scrapers (no slow Firecrawl/Scrape.do on a global
    page), and _get_price returns the parked converted_usd. This proves B removes
    the render-on-global latency REGARDLESS of network — the structural cure for
    the prod timeout. (The real curl scraper is stubbed so this is pure logic.)"""
    from app.services import structured_comparison_service as scs_mod

    _converted_tier1(monkeypatch, scs_mod)
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "fetch_shopify_price", AsyncMock(return_value=None))
    # Discovery surfaces ONLY a global samsung.com/us page (the prod-bug shape).
    monkeypatch.setattr(
        scs_mod, "search_web",
        AsyncMock(return_value={"organic": [
            {"link": "https://www.samsung.com/us/smartphones/galaxy-s24/"}
        ]}),
    )

    # Spy on _build_escalation_scrapers to capture the render-wave scraper count.
    captured = {"render_count": None, "curl_count": None}
    real_build = scs_mod._build_escalation_scrapers

    def _spy(*, candidate_urls, full_name, currency, scraping_mode, wave="all"):
        scrapers = real_build(
            candidate_urls=candidate_urls, full_name=full_name,
            currency=currency, scraping_mode=scraping_mode, wave=wave,
        )
        if wave == "render":
            captured["render_count"] = len(scrapers)
        elif wave == "curl":
            captured["curl_count"] = len(scrapers)
        return scrapers
    monkeypatch.setattr(scs_mod, "_build_escalation_scrapers", _spy)
    # fan_out yields nothing (the global curl finds no BH price); estimate exists.
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(scs_mod, "search_price_organic",
                        AsyncMock(return_value={"organic": [], "knowledge_graph": None}))
    monkeypatch.setattr(scs_mod, "extract_price", AsyncMock(return_value=(None, {})))
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=({"amount": 290.0, "currency": "BHD"}, {})),
    )

    # Query iPhone 15 to match the _converted_tier1 Walmart shopping item (so the
    # gl=us converted price parks). The global discovery url is samsung.com/us
    # purely to exercise the global-render-skip — the matched parked price is the
    # iPhone Walmart one.
    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    # Non-vacuous: samsung.com DID enter candidate_urls (via OFFICIAL_BRAND_DOMAINS
    # legacy-fallback — the exact prod-bug path) so the curl wave saw it.
    assert captured["curl_count"] is not None and captured["curl_count"] >= 1, (
        "global url must have entered candidate_urls (else the render==0 is vacuous)"
    )
    # THE STRUCTURAL CURE: the render wave built ZERO scrapers for the global URL
    # (no Firecrawl/Scrape.do on samsung.com/us — that was the prod budget+timeout).
    assert captured["render_count"] == 0, (
        "render wave must build 0 scrapers for a global-only candidate (Fix B)"
    )
    # And the parked converted_usd is returned (Fix A path), never None/estimate.
    assert result is not None
    assert result["source_method"] == "converted_usd"


@pytest.mark.asyncio
async def test_genuine_local_bhd_tier1_still_short_circuits(monkeypatch, clean_service):
    """A GENUINE local_bhd Tier-1 price (already a real BH price) MAY still
    early-exit — the parking applies ONLY to converted prices. (Here Tier-1
    extracts a native-BHD price from a BH retailer in the shopping feed.)"""
    from app.services import structured_comparison_service as scs_mod

    # Tier-1 shopping with a native BHD price from a BH-locale retailer (high
    # score so it skips the high-value sanity branch and returns directly).
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={
            "shopping": [{
                "title": "Apple iPhone 15 128GB",
                "price": "BHD 244.990",
                "source": "sharafdg",
                "link": "https://bahrain.sharafdg.com/product/iphone-15/",
            }],
            "organic": [],
            "shopping_region": "bh",
        }),
    )
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)
    # If parking wrongly applied to genuine prices, the BH scrape would run; assert
    # it does NOT need to (fan_out should not even be reached). Stub it to blow up
    # if called so a regression (genuine price parked) is caught.
    async def _boom(*a, **k):
        raise AssertionError("genuine local_bhd Tier-1 should short-circuit, not escalate")
    monkeypatch.setattr(scs_mod, "fan_out_price_lookup", _boom)

    result = await clean_service._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )
    assert result is not None
    assert result["amount"] == pytest.approx(244.990)
    assert result["source_method"] == "local_bhd"

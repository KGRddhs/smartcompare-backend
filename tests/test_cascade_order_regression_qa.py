"""S3 QA (genuine BH pricing) — integrated price-cascade ORDER regression net.

Owner: L5/QA lane (feature/s3-qa-genuine-cascade). COMPLEMENTARY to L1's per-fix
unit TDD (test_converted_price_before_estimate_t1, test_shopping_source_method_t2,
test_price_plausibility_guard) — this file pins the CROSS-CUTTING, end-to-end
contract over the whole `_get_price` path so a regression introduced by ANY
future change (not just L1's commits) is caught.

The four contract invariants (team-lead, S3 reopen 2026-06-13):
  A1 ORDER — a genuine BH price (local_bhd / shopify_json / page_scrape) is
     preferred over a converted_usd price over an estimated price. An estimate
     must never win when a real source returned a usable price.
  A2 HONEST LABEL — a gl=us / non-BHD-original Serper-shopping price is NEVER
     stamped `local_bhd`; it must be `converted_usd` (b82af2a, asserted at the
     integration _get_price level rather than the pure extractor).
  A3 ESTIMATE-LAST — `source_method == "estimated"` (or estimated=True) only
     when shopping + escalation + broader-search ALL returned nothing usable.
  A4 RENDER-ONLY EXCLUSION — registry sources flagged usage="review" stay OUT
     of the price-discovery / curl-harvest pool.

All mocked/fixtures — NO live calls, NO OpenAI/Serper spend (credit gate).
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import patch, AsyncMock

from app.services.structured_comparison_service import StructuredComparisonService


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _svc():
    return StructuredComparisonService()


def _patches_for_get_price(
    *,
    shopping_items=None,
    organic_extract=None,
    training_estimate=None,
    escalate=False,
):
    """Patch every external seam of _get_price so only the cascade ORDER +
    source_method stamping is under test. Returns a list of context managers.

    - shopping_items: what Serper-shopping returns (Tier 1).
    - organic_extract: what extract_price returns (Tier 2, gl=us/organic path).
    - training_estimate: what extract_price_from_training_data returns (Tier 3).
    - escalate: whether the Tier-1.5 fan_out escalation fires (default off, so
      Tier 1 -> Tier 2 -> Tier 3 ordering is isolated).
    """
    ssc = "app.services.structured_comparison_service"

    async def fake_search_product_prices(*_a, **_k):
        return {"shopping": shopping_items or [], "organic": [], "shopping_region": "us"}

    async def fake_search_price_organic(*_a, **_k):
        return {"organic": [], "knowledge_graph": None}

    async def fake_extract_price(*_a, **_k):
        # returns (price_dict_or_None, usage)
        return (dict(organic_extract) if organic_extract else None, {})

    async def fake_training(*_a, **_k):
        return (dict(training_estimate) if training_estimate else None, {})

    return [
        patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=fake_search_product_prices)),
        patch(f"{ssc}.search_price_organic", new=AsyncMock(side_effect=fake_search_price_organic)),
        patch(f"{ssc}.extract_price", new=AsyncMock(side_effect=fake_extract_price)),
        patch(f"{ssc}.extract_price_from_training_data", new=AsyncMock(side_effect=fake_training)),
        # Skip the Tier-1.5 fan_out escalation unless a test wants it.
        patch(f"{ssc}._should_escalate_price_scrape", return_value=escalate),
        # Caches must miss so the live cascade runs; DB read returns None.
        patch(f"{ssc}.get_cached", return_value=None),
        patch(f"{ssc}.set_cached", return_value=True),
        patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)),
    ]


async def _run_get_price(svc, **kw):
    """Drive _get_price for a simple electronics query with the given patches."""
    return await svc._get_price(
        brand="Apple", name="iPhone 15", variant=None, region="bahrain",
        search_query="Apple iPhone 15", nocache=True, category="electronics",
    )


# ===========================================================================
# A2 — HONEST LABEL: gl=us / non-BHD original is never stamped local_bhd
# ===========================================================================

@pytest.mark.asyncio
async def test_gl_us_origin_stamped_converted_usd_not_local_bhd():
    """A USD-original Tier-2 extract (gl=us fallback) must be labeled
    converted_usd — NEVER local_bhd. Integration cross-check of b82af2a."""
    svc = _svc()
    # No shopping (Tier 1 empty) → falls to Tier 2 organic extract, which
    # returns a USD-original price.
    # original_currency=USD != region currency (BHD). The amount may be
    # currency-converted downstream (USD→BHD); the CONTRACT under test is the
    # source_method LABEL, not the post-conversion number.
    organic = {"amount": 999.0, "currency": "USD", "original_currency": "USD", "retailer": "Amazon"}
    with patch.object(svc, "_save_price_to_db"):
        patches = _patches_for_get_price(shopping_items=[], organic_extract=organic)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            price = await _run_get_price(svc)

    assert price.get("amount") is not None
    assert price.get("source_method") == "converted_usd", (
        f"a USD-original price was mislabeled {price.get('source_method')!r}; "
        f"gl=us / non-BHD-original must be converted_usd, never local_bhd"
    )
    assert price.get("source_method") != "local_bhd"


@pytest.mark.asyncio
async def test_genuine_bhd_origin_stamped_local_bhd():
    """A genuinely BHD-original Tier-2 extract IS local_bhd (the honest case)."""
    svc = _svc()
    organic = {"amount": 380.0, "currency": "BHD", "original_currency": "BHD", "retailer": "sharafdg"}
    with patch.object(svc, "_save_price_to_db"):
        patches = _patches_for_get_price(shopping_items=[], organic_extract=organic)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            price = await _run_get_price(svc)

    assert price.get("amount") == 380.0
    assert price.get("source_method") == "local_bhd", (
        f"a BHD-original price should be local_bhd, got {price.get('source_method')!r}"
    )


# ===========================================================================
# A3 — ESTIMATE-LAST: estimated only when every real source is empty
# ===========================================================================

@pytest.mark.asyncio
async def test_estimate_only_when_all_real_sources_empty():
    """Shopping empty + organic extract empty → Tier 3 estimate is the ONLY
    remaining option, so estimated is correct here."""
    svc = _svc()
    estimate = {"amount": 350.0, "currency": "BHD", "retailer": None}
    with patch.object(svc, "_save_price_to_db"):
        patches = _patches_for_get_price(
            shopping_items=[], organic_extract=None, training_estimate=estimate,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            price = await _run_get_price(svc)

    assert price.get("amount") == 350.0
    assert price.get("estimated") is True
    assert price.get("source_method") == "estimated"


@pytest.mark.asyncio
async def test_real_organic_price_beats_estimate_no_estimated_label():
    """When the Tier-2 organic extract returns a usable real price, the cascade
    must NOT fall through to the estimate — estimated must not win. (A1+A3.)"""
    svc = _svc()
    organic = {"amount": 410.0, "currency": "BHD", "original_currency": "BHD", "retailer": "sharafdg"}
    # An estimate is also available — it must be IGNORED because organic returned.
    estimate = {"amount": 350.0, "currency": "BHD", "retailer": None}
    with patch.object(svc, "_save_price_to_db"):
        patches = _patches_for_get_price(
            shopping_items=[], organic_extract=organic, training_estimate=estimate,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            price = await _run_get_price(svc)

    assert price.get("amount") == 410.0, "the real organic price must win over the estimate"
    assert price.get("source_method") == "local_bhd"
    assert price.get("estimated") is not True, "a real price must not be flagged estimated"


# ===========================================================================
# A1 — ORDER: genuine Tier-1 shopping beats the estimate
# ===========================================================================

@pytest.mark.asyncio
async def test_tier1_shopping_price_wins_over_estimate():
    """A usable Tier-1 Serper-shopping price short-circuits the cascade (returns
    before Tier 2/3) — the estimate never gets a chance."""
    svc = _svc()
    # extract_price_from_shopping is the REAL pure function; give it a shopping
    # item it can parse into a BHD price with a high retailer_score (official →
    # skips sanity check, deterministic).
    shopping = [{
        "title": "Apple iPhone 15 128GB", "price": "BHD 380.000",
        "source": "apple.com", "link": "https://apple.com/bh/iphone-15",
    }]
    estimate = {"amount": 350.0, "currency": "BHD", "retailer": None}
    with patch.object(svc, "_save_price_to_db"):
        patches = _patches_for_get_price(
            shopping_items=shopping, organic_extract=None, training_estimate=estimate,
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            price = await _run_get_price(svc)

    assert price.get("amount") is not None
    assert price.get("estimated") is not True, (
        "a usable Tier-1 shopping price must short-circuit the cascade; the "
        f"estimate must not win. got source_method={price.get('source_method')!r}"
    )
    assert price.get("source_method") != "estimated"


# ===========================================================================
# A4a — usage="review" EXCLUSION (existing flag): editorial/no-price sources
#       stay out of the price-discovery harvest entirely.
# ===========================================================================
# NB: usage="review" is DISTINCT from L1's NEW `is_render_only` flag (A4b
# below). usage="review" = source has NO prices (editorial sites) -> excluded
# from the price pool. is_render_only = source HAS BH prices but needs JS
# render -> out of curl-harvest BUT into the render-tier. These tests pin the
# usage="review" case only. The source_router unit tests
# (test_source_usage_field.py) pin the helper level; THIS pins the INTEGRATION
# harvest guard (_harvest_candidate_urls) — complementary, not duplicate.

from app.services.structured_comparison_service import _harvest_candidate_urls


def test_harvest_excludes_review_usage_domain_in_bahrain_tier():
    """A usage='review' registry domain (sayidaty.net for makeup) present in the
    bahrain organic results must NOT enter the price-discovery harvest pool."""
    # sayidaty.net is registered usage="review" for makeup; noon.com is a real
    # price source. Both appear in the discovery results.
    results_by_tier = {
        "bahrain": {"organic": [
            {"link": "https://www.sayidaty.net/article/best-foundations"},
            {"link": "https://noon.com/makeup-product-x"},
        ]},
    }
    harvested = _harvest_candidate_urls(results_by_tier, official_domain=None, category="makeup")
    harvested_links = [h[0] for h in harvested]

    assert not any("sayidaty.net" in link for link in harvested_links), (
        "a usage='review' domain leaked into the price-discovery harvest pool: "
        f"{harvested_links}"
    )


def test_harvest_keeps_real_price_domain():
    """Control: a genuine price source (amazon.ae) under the same category IS
    harvested — proving the exclusion is usage-specific, not a blanket drop.
    NB: amazon.ae chosen over noon.com so this control stays stable when noon
    flips is_render_only=True on the S3 coverage branch (noon is Akamai-walled)."""
    results_by_tier = {
        "bahrain": {"organic": [
            {"link": "https://amazon.ae/makeup-product-x"},
        ]},
    }
    harvested = _harvest_candidate_urls(results_by_tier, official_domain=None, category="makeup")
    harvested_links = [h[0] for h in harvested]
    assert any("amazon.ae" in link for link in harvested_links), (
        f"a genuine price source was wrongly excluded from the harvest: {harvested_links}"
    )


# ===========================================================================
# A4b — is_render_only TWO-SIDED CONTRACT (L1's flag, contract confirmed)
# ===========================================================================
# L1 confirmed the FINAL contract (msg 2026-06-14). is_render_only is DISTINCT
# from usage="review": a render-only source (alosra / nasserpharmacy / bn.boots
# / bolo / megamart — 5 SPAs, NOT 4) HAS genuine BH prices but needs JS render.
# IMPORTANT NUANCE (corrects my earlier assumption): render-only sources are NOT
# excluded from _harvest_candidate_urls — they DO enter candidate_urls when
# Serper discovers their PDP. The two-sided split happens in
# _build_escalation_scrapers(wave=...):
#   (a) wave="curl"   → SKIPS emitting a curl scraper for a render-only domain
#                       (a static curl yields nothing on a JS-SPA).
#   (b) wave="render" → emits Firecrawl/Scrape.do for it (fires only on curl miss).
#
# Merged-state split (verified on origin/main b58abc8):
#   (i)   Source.is_render_only field + the 5 domains → ON MAIN → pin GREEN.
#   (ii)  is_render_only_domain() helper → NOT on main (L1 fast-follow) → RED-first.
#   (iii) curl-skip in _build_escalation_scrapers(wave="curl") → NOT on main
#         (L1 fast-follow) → RED-first; L1 pings the fast-follow SHA when it greens.

from app.services.source_router import SOURCE_REGISTRY

_RENDER_ONLY_DOMAINS = {
    # Source-intel recon 2026-06-23: bolo.bh + nasserpharmacy.com flipped OFF
    # render-only (direct-readable: bolo Nuxt-SSR curl, nasser own JSON API).
    "alosraonline.com", "bn.boots.com", "megamart.bh",
    # S3 coverage (2026-06-14): noon.com flipped is_render_only=True — Akamai-walled
    # marketplace (plain curl returns 0-byte), routed to the render-tier. GCC-tier
    # (gray-import), not a BH SPA, but carries the flag so the cascade skips a wasted
    # plain-curl on it. L1 #2 apple-fix; dispatcher-confirmed at the coverage merge.
    "noon.com",
    # WS-G (fragrance-content-quality P8, 2026-06-22): the CF-walled BH
    # beauty/fragrance retailer sephora.me. is_render_only (no static curl price)
    # AND requires_super (routed ONLY when SCRAPEDO_SUPER is on) — see the gating
    # test in test_fragrance_content_quality.py. In the registry list but filtered
    # out of routing/discovery with the flag OFF (cost-neutral).
    # Wave-3c (2026-06-23): boutiqaat.com REMOVED from this set — the live re-verify
    # cracked it to a $0 curl sitemap adapter (genuine BHD JSON-LD), so it is now
    # mechanism="sitemap" (NOT render-only/super); see test_source_descriptor_fields.
    "sephora.me",  # sephora.me = canonical BH (was sephora.bh)
}


# --- (i) field + the 5 domains ---
# ROLLBACK NOTE (2026-06-14): the genuine-BH merge e33e13e was REVERTED for a
# prod-latency regression (main=3db3ddc). The is_render_only field + 5 domains +
# the two-wave _build_escalation_scrapers(wave=...) split are ALL gone from main
# pending L1's consolidated re-merge (fix-A timeout→parked-fallback + fix-B
# render-scope-to-BH + the ce0a78e helper/curl-skip). So ALL is_render_only tests
# are xfail-strict now and flip green TOGETHER when the consolidated branch lands.

def test_render_only_field_marks_the_six_render_domains():
    """The is_render_only flag exists on Source and exactly the render domains
    carry it: alosra/bn.boots/megamart (BH SPAs) + noon.com (Akamai-walled GCC
    marketplace, S3 coverage flip) + sephora.me (WS-G CF-walled BH beauty/fragrance,
    requires_super). Wave-3c flipped bolo/nasser/boutiqaat OFF render-only (genuine
    curl/API/sitemap adapters), so they are NOT in this set."""
    marked = {s.domain for s in SOURCE_REGISTRY if getattr(s, "is_render_only", False)}
    assert marked == _RENDER_ONLY_DOMAINS, (
        f"is_render_only domain set drifted: expected {_RENDER_ONLY_DOMAINS}, got {marked}"
    )


def test_non_spa_bh_source_is_not_render_only():
    """Control: a CURL-tier BH source (e.g. microless — L1: curl, not render)
    must NOT be flagged is_render_only."""
    by_domain = {s.domain: s for s in SOURCE_REGISTRY}
    # luluhypermarket is a known non-render BH source in the registry.
    if "luluhypermarket.com" in by_domain:
        assert getattr(by_domain["luluhypermarket.com"], "is_render_only", False) is False


# --- (ii) is_render_only_domain() helper: RED-first until L1 fast-follow ---

def test_is_render_only_domain_helper_resolves_spa():
    """is_render_only_domain(domain_or_url) → True for an SPA source, False for a
    curl source. Live on main since the S3 genuine-BH re-merge (3be92ce)."""
    from app.services.source_router import is_render_only_domain  # noqa: F401 — RED until merged
    # Bare domain + full-URL both resolve (L1 spec: accepts domain OR URL).
    assert is_render_only_domain("megamart.bh") is True
    assert is_render_only_domain("https://bn.boots.com/some-pdp") is True
    # Curl-tier domain → False (L1's exact example: sharafdg is curl, not render).
    assert is_render_only_domain("https://bahrain.sharafdg.com/p/x") is False
    # noon.com → True since the S3 coverage flip (Akamai-walled → render-tier).
    assert is_render_only_domain("noon.com") is True


# --- (iii) curl-skip for render-only URL: live on main since 3be92ce ---

def test_curl_wave_skips_render_only_domain():
    """_build_escalation_scrapers(wave="curl") must emit ZERO scrapers for a
    render-only domain's URL (a static curl can't render a JS-SPA → pure waste).

    RED-first (xfail strict): the curl-skip is L1's in-flight fast-follow. Today
    the curl wave emits 1 curl scraper for every candidate URL incl. render-only
    ones; this is xfail NOW and becomes xpass (loud, strict) when the skip lands.
    """
    from app.services.structured_comparison_service import _build_escalation_scrapers

    render_only_url = "https://bn.boots.com/product/centrum-multivitamin"
    scrapers = _build_escalation_scrapers(
        candidate_urls=[(render_only_url, "bn.boots.com")],
        full_name="Centrum Multivitamin",
        currency="BHD",
        scraping_mode="hard",
        wave="curl",
    )
    assert len(scrapers) == 0, (
        "wave='curl' emitted a curl scraper for a render-only (JS-SPA) domain — "
        f"a static curl yields nothing on it; expected 0, got {len(scrapers)}. "
        "(RED until L1's curl-skip fast-follow lands.)"
    )


def test_curl_wave_keeps_non_render_domain():
    """Control: wave="curl" DOES emit a curl scraper for a normal (non-render)
    domain — the skip is render-only-specific, not a blanket curl drop.
    NB: amazon.ae (not noon.com) — noon flips is_render_only=True on the S3
    coverage branch, which would (correctly) make the curl wave SKIP it and
    break this control; amazon.ae stays a stable non-render price source."""
    from app.services.structured_comparison_service import _build_escalation_scrapers

    normal_url = "https://amazon.ae/product/centrum-multivitamin"
    scrapers = _build_escalation_scrapers(
        candidate_urls=[(normal_url, "amazon.ae")],
        full_name="Centrum Multivitamin",
        currency="BHD",
        scraping_mode="hard",
        wave="curl",
    )
    assert len(scrapers) >= 1, (
        f"wave='curl' must emit a curl scraper for a normal domain; got {len(scrapers)}"
    )


# --- (b) render INCLUSION: render-only domain DOES get Firecrawl+Scrape.do ---
# This side of the two-sided contract is GREEN on main already: the render wave
# is gated by firecrawl_service.should_fan_out (True in hard mode), NOT by
# is_render_only — so a render-only PDP gets its 2 render scrapers regardless of
# the curl-skip. Pinning it guards against a future change that would wrongly
# drop render-only domains out of the render tier too (which would leave them
# with NO price path at all). L1 spec: wave="render" emits 2 (firecrawl+scrapedo).

def test_render_wave_includes_render_only_domain():
    """A render-only domain's PDP MUST get the Firecrawl + Scrape.do scrapers in
    wave='render' (2 scrapers) — it's the ONLY price path for a JS-SPA."""
    from app.services.structured_comparison_service import _build_escalation_scrapers

    render_only_url = "https://bn.boots.com/product/centrum-multivitamin"
    scrapers = _build_escalation_scrapers(
        candidate_urls=[(render_only_url, "bn.boots.com")],
        full_name="Centrum Multivitamin",
        currency="BHD",
        scraping_mode="hard",
        wave="render",
    )
    assert len(scrapers) == 2, (
        "wave='render' must emit Firecrawl+Scrape.do (2) for a render-only PDP — "
        f"it's the only price path for a JS-SPA; got {len(scrapers)}"
    )


# --- Fix B (THE PROD ROLLBACK FIX): render wave must NOT fire on a GLOBAL url ---
# This is the exact regression that rolled the genuine-BH merge back: render
# fired on gl=us GLOBAL organic URLs (samsung.com/us, amazon.ae, harvested from
# the official/gcc tiers) because should_fan_out is True-in-hard-mode → 6+ slow
# render calls → blew the 15s price cap → price None. L1's Fix B gates the render
# wave on `is_render_only_domain(...)` so a GLOBAL url gets 0 render scrapers
# (the parked converted_usd is the answer); only an is_render_only BH SPA renders.
# Live on main since the S3 genuine-BH re-merge (3be92ce).

def test_render_wave_skips_global_url_fix_b():
    """A GLOBAL organic url (samsung.com/us) must get ZERO render scrapers in
    wave='render' — rendering globals is THE prod regression that blew the 15s
    cap → None. Only is_render_only BH SPAs may render; a global's answer is the
    parked converted_usd."""
    from app.services.structured_comparison_service import _build_escalation_scrapers

    global_url = "https://www.samsung.com/us/smartphones/galaxy-s24/"
    scrapers = _build_escalation_scrapers(
        candidate_urls=[(global_url, "samsung.com")],
        full_name="Samsung Galaxy S24",
        currency="BHD",
        scraping_mode="hard",
        wave="render",
    )
    assert len(scrapers) == 0, (
        "wave='render' emitted render scrapers for a GLOBAL url — THE prod "
        f"regression (renders globals → blows the 15s cap → None); expected 0, got {len(scrapers)}"
    )


# ===========================================================================
# A5 — FALLBACK-ALWAYS-YIELDS-A-PRICE liveness invariant (the rollback lesson)
# ===========================================================================
# Why this exists: the genuine-BH re-order (reverted at 3db3ddc) shipped a
# prod-RUNTIME regression a mocked CONTRACT net can't catch — escalation blew
# the Phase-1 price-race timeout and returned None (no price) instead of falling
# back to the parked converted/estimate price. price→no-price on electronics.
#
# This invariant is the cross-cutting guard for exactly that: when the Tier-1.5
# escalation (fan_out) TIMES OUT or RAISES, _get_price MUST still return a price
# with a non-None amount (parked Shopify fallback OR Tier-2 converted OR Tier-3
# estimate) — NEVER {amount: None}. It is GREEN on the rolled-back base (the
# timeout is caught at ssc:3119 and falls through), and it STAYS the guard that
# fails loud if L1's re-merge reintroduces the timeout→None abort (fix-A makes
# it stay green). Mocked at the _get_price level (no live calls / no spend), but
# it exercises the REAL escalation→fallthrough control path, not just labels.

import asyncio as _asyncio


def _liveness_patches(svc, *, shopping_items, organic_extract, training_estimate, fan_out_effect):
    """Patch _get_price's seams to force the escalation path, then make the
    fan_out time out / raise, and assert a price still falls through."""
    ssc = "app.services.structured_comparison_service"

    async def fake_search_product_prices(*_a, **_k):
        return {"shopping": shopping_items or [], "organic": [], "shopping_region": "us"}

    async def fake_search_price_organic(*_a, **_k):
        return {"organic": [], "knowledge_graph": None}

    async def fake_extract_price(*_a, **_k):
        return (dict(organic_extract) if organic_extract else None, {})

    async def fake_training(*_a, **_k):
        return (dict(training_estimate) if training_estimate else None, {})

    async def fake_search_web(*_a, **_k):
        # discovery returns one harvestable BH candidate so candidate_urls is
        # non-empty → the fan_out (which we sabotage) actually runs.
        return {"organic": [{"link": "https://noon.com/centrum"}]}

    return [
        patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=fake_search_product_prices)),
        patch(f"{ssc}.search_price_organic", new=AsyncMock(side_effect=fake_search_price_organic)),
        patch(f"{ssc}.search_web", new=AsyncMock(side_effect=fake_search_web)),
        patch(f"{ssc}.extract_price", new=AsyncMock(side_effect=fake_extract_price)),
        patch(f"{ssc}.extract_price_from_training_data", new=AsyncMock(side_effect=fake_training)),
        # Force escalation ON regardless of Tier-1 confidence.
        patch(f"{ssc}._should_escalate_price_scrape", return_value=True),
        # Sabotage the fan_out: time out or raise (the regression trigger).
        patch(f"{ssc}.fan_out_price_lookup", new=AsyncMock(side_effect=fan_out_effect)),
        patch(f"{ssc}.get_cached", return_value=None),
        patch(f"{ssc}.set_cached", return_value=True),
        patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)),
    ]


async def _run_electronics_price(svc):
    return await svc._get_price(
        brand="Apple", name="iPhone 15", variant=None, region="bahrain",
        search_query="Apple iPhone 15", nocache=True, category="electronics",
    )


@pytest.mark.asyncio
async def test_escalation_timeout_falls_back_to_a_price_never_none():
    """When the Tier-1.5 fan_out TIMES OUT, _get_price must fall through to a
    real price (Tier-2 converted here) — NOT abort to {amount: None}. This is
    the exact regression that the reverted re-order shipped."""
    svc = _svc()

    async def time_out(*_a, **_k):
        raise _asyncio.TimeoutError()

    # Tier-1 shopping empty, but a Tier-2 organic extract is available as the
    # parked fallback after the escalation times out.
    organic = {"amount": 410.0, "currency": "BHD", "original_currency": "BHD", "retailer": "sharafdg"}
    with patch.object(svc, "_save_price_to_db"):
        p = _liveness_patches(
            svc, shopping_items=[], organic_extract=organic, training_estimate=None,
            fan_out_effect=time_out,
        )
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]:
            price = await _run_electronics_price(svc)

    assert price is not None
    assert price.get("amount") is not None, (
        "REGRESSION: escalation timeout aborted to a None price instead of falling "
        f"back to the parked Tier-2/Tier-3 price. got {price!r}"
    )
    assert price["amount"] == 410.0


@pytest.mark.asyncio
async def test_escalation_timeout_falls_back_to_estimate_when_only_estimate_left():
    """If the escalation times out AND there's no Tier-2 organic price, the
    cascade must still yield the Tier-3 estimate — never None."""
    svc = _svc()

    async def time_out(*_a, **_k):
        raise _asyncio.TimeoutError()

    estimate = {"amount": 350.0, "currency": "BHD", "retailer": None}
    with patch.object(svc, "_save_price_to_db"):
        p = _liveness_patches(
            svc, shopping_items=[], organic_extract=None, training_estimate=estimate,
            fan_out_effect=time_out,
        )
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]:
            price = await _run_electronics_price(svc)

    assert price is not None
    assert price.get("amount") is not None, (
        "REGRESSION: escalation timeout + no Tier-2 aborted to None instead of the "
        f"Tier-3 estimate. got {price!r}"
    )
    assert price["amount"] == 350.0
    assert price.get("estimated") is True


@pytest.mark.asyncio
async def test_escalation_raise_falls_back_to_a_price_never_none():
    """A non-timeout exception in the escalation must ALSO fall through to a
    price, not abort to None (defense-in-depth for the same liveness contract)."""
    svc = _svc()

    async def boom(*_a, **_k):
        raise RuntimeError("scraper pool exploded")

    organic = {"amount": 299.0, "currency": "BHD", "original_currency": "BHD", "retailer": "sharafdg"}
    with patch.object(svc, "_save_price_to_db"):
        p = _liveness_patches(
            svc, shopping_items=[], organic_extract=organic, training_estimate=None,
            fan_out_effect=boom,
        )
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]:
            price = await _run_electronics_price(svc)

    assert price is not None
    assert price.get("amount") == 299.0, (
        f"REGRESSION: escalation raise aborted to None instead of falling back; got {price!r}"
    )

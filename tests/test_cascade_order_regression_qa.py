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
    """Control: a genuine price source (noon.com) under the same category IS
    harvested — proving the exclusion is usage-specific, not a blanket drop."""
    results_by_tier = {
        "bahrain": {"organic": [
            {"link": "https://noon.com/makeup-product-x"},
        ]},
    }
    harvested = _harvest_candidate_urls(results_by_tier, official_domain=None, category="makeup")
    harvested_links = [h[0] for h in harvested]
    assert any("noon.com" in link for link in harvested_links), (
        f"a genuine price source was wrongly excluded from the harvest: {harvested_links}"
    )


# ===========================================================================
# A4b — is_render_only TWO-SIDED CONTRACT (L1's NEW flag) — PENDING L1 confirm
# ===========================================================================
# A render-only source (alosra / nasserpharmacy / bn.boots / bolo: HAS genuine
# BH prices, needs JS render) must be:
#   (a) OUT of the curl-harvest candidate pool (curl can't render the SPA), AND
#   (b) IN the Firecrawl/Scrape.do render-tier escalation pool.
# This is DISTINCT from usage="review" (A4a) — render-only sources DO have
# prices. The exact flag name + cascade mechanism is in L1's in-flight batch;
# coordination message sent. The test will be written failing-first against the
# confirmed contract so it greens when L1's batch lands. Deliberately NOT pinned
# yet to avoid mismatching L1's implementation (testing the wrong flag = a
# false guard). The A4a tests above do NOT cover this case.

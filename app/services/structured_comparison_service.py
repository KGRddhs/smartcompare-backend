"""Structured Comparison Service - Main orchestrator for product comparisons.

Delegates to focused modules:
- price_service: all price fetching, extraction, currency conversion
- rating_service: verified ratings from shopping data
- review_service: review fetching, cleaning, citation cleanup
- fact_check_service: spec/price/review cross-validation
- response_builder: builds the full response dict
"""
import os
import re
import json
import time
import asyncio
import hashlib
import logging
import httpx
from functools import partial
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote_plus

from app.services.extraction_service import (
    parse_product_query,
    extract_specs,
    extract_price,
    extract_price_from_training_data,
    extract_reviews,
    generate_comparison,
    get_specs_cache_key,
    get_price_cache_key,
    get_reviews_cache_key,
    was_cohort_block_active,
    GCC_REGIONS
)
from app.services.database_service import get_user_demographics
from app.services.serper_service import search_product_prices, search_price_organic, search_web
from app.services.cache_service import (
    get_cached,
    set_cached,
    record_tier15_attempt,
    record_tier15_hit,
    record_price_outcome,
)
from app.services.drug_database_service import find_matching_drugs, format_drug_context
from app.services.scoring_service import get_scoring_service, MISSING_SCORE
from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed,
)
from app.services import firecrawl_service, scrapedo_service


# Bundle C § 2e A.4.5 — comparison_quality detector. Returns one of
# 'normal' / 'weak' / 'weird' so the verdict prompt + frontend can adjust
# framing WITHOUT triggering a UI banner (per critical rule #1). The
# 'weird' label only fires on the three hard triggers from spec § 2e:
#   1. Cross-category (category_used mismatch).
#   2. Post-fallback >50% spec coverage gap on either product.
#   3. Price spread >= 10x order of magnitude.
# 'weak' is reserved for the softer signal: pre-fallback >50% spec gap
# (means Tier 2/3 still has a chance to fill).
_EXPECTED_SPEC_FIELD_COUNT = {
    "electronics": 6, "supplements": 5, "fragrances": 6, "fashion": 5,
    "skincare": 5, "haircare": 5, "makeup": 6, "grocery": 5, "other": 4,
}


def _product_category(p):
    return (p.get("category_used") or p.get("category") or "").strip().lower()


def _fire_and_forget(coro, label: str) -> None:
    """Thin wrapper around `app.utils.async_utils.fire_and_forget`.

    Originally introduced 2026-05-22 (M6 audit) for the
    scoring/personalization writeback paths in this file. Bundle D 2.B.6
    extracted the implementation to `app.utils.async_utils` so the 22
    fire-and-forget sites in `app/api/*.py` can reuse the same pattern
    without re-defining the helper per file. This name is preserved
    locally so existing call sites in this module keep their import.
    """
    from app.utils.async_utils import fire_and_forget
    fire_and_forget(coro, label)


def _phase1_completely_failed(pd: Dict[str, Any]) -> bool:
    """H6 (audit 2026-05-22): True when a product's Phase 1 fetches all came
    back as None — i.e., asyncio.gather caught exceptions for BOTH specs AND
    price. Distinct from 'got data but it's poor quality' (specs={} or
    price={'amount': None, ...}) which still lets scoring proceed.

    Used by compare_from_text + compare_from_text_streaming to bail out
    when both products satisfy this — otherwise scoring would run with
    all-MISSING_SCORE and the deterministic tie-break would always elect
    product_0 as a fake winner.
    """
    return pd.get("specs") is None and pd.get("price") is None


async def _cancel_profile_task(task) -> None:
    """I5.6 lever-2: cleanly cancel the early-started behavior/demographics fetch
    task on an early-return path (INSUFFICIENT_DATA / stream timeout) so no
    orphaned coroutine is left pending. Awaits the cancellation and swallows
    CancelledError (plus any error the fetch itself raised) — both fetches are
    already individually fail-soft (_fetch_behavior_profile returns None on error,
    get_user_demographics likewise), so there is nothing to surface here."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


def _product_price_amount(p):
    price = p.get("price")
    if isinstance(price, dict):
        amt = price.get("amount")
    else:
        amt = price
    try:
        amt = float(amt) if amt is not None else None
    except (TypeError, ValueError):
        return None
    return amt if (amt is not None and amt > 0) else None


def _product_spec_coverage(p):
    """Return (filled_count, expected_count) for the product's specs."""
    specs = p.get("specs") or {}
    if not isinstance(specs, dict):
        return 0, 1
    cat = _product_category(p) or "other"
    expected = _EXPECTED_SPEC_FIELD_COUNT.get(cat, _EXPECTED_SPEC_FIELD_COUNT["other"])
    # Count non-empty, non-N/A spec values.
    filled = sum(
        1 for v in specs.values()
        if v not in (None, "", "N/A", "n/a") and not (isinstance(v, str) and not v.strip())
    )
    return filled, max(expected, 1)


# Bundle C § 2f A.4.7 — Tier 2 spec fallback.
# Fires AFTER Tier 1 + smart-fallback when NON_NEGOTIABLE schema fields
# remain blank. Each missing field gets one targeted Serper + GPT-mini
# extract, in parallel via asyncio.gather, with strict wall budgets:
#   - 4s outer asyncio.wait_for (spec § 2f)
#   - 0.5s per-field budget (spec § 2f) — but parallel gather lets all
#     fields share the 4s wall, so per-field is enforced via wait_for
#     on each task.
# Silent omission per § 2h on timeout/failure — NO exception escapes.
_TIER2_WALL_SECONDS = 4.0
_TIER2_PER_FIELD_SECONDS = 3.5  # near-full wall; gather lets fields share


async def tier2_fill_non_negotiables(
    *,
    brand: str,
    name: str,
    variant,
    category: str,
    specs_so_far: dict,
) -> dict:
    """Bundle C § 2f A.4.7 — Tier 2 targeted fill for non-negotiable
    schema fields still blank after Tier 1 + smart-fallback.

    Returns a dict of {field: value} for fields successfully filled.
    Empty dict on no-op (all non-negotiables already filled) or on
    timeout/failure. NEVER raises — silent omission per § 2h.

    Wall-budget contract:
      - 4s outer asyncio.wait_for hard cap.
      - Runs targeted GPT extract per missing field in parallel.
      - Fires ONLY when at least one non-negotiable is blank — common
        happy-path comparisons skip Tier 2 entirely (zero added wall).
    """
    from app.services.extraction_service import (
        CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE,
    )

    non_negotiable = CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE.get(category, [])
    if not non_negotiable:
        return {}  # 'other' category + unknown categories have no non-negotiables

    # Identify still-missing non-negotiables (Tier 1 + smart-fallback already ran).
    missing = [
        f for f in non_negotiable
        if not specs_so_far.get(f) or specs_so_far.get(f) in ("N/A", "")
    ]
    if not missing:
        return {}  # Happy path — all non-negotiables already filled.

    full_name = f"{brand} {name} {variant or ''}".strip()

    async def _fill_one_field(field: str):
        """Fire one Serper search + targeted GPT extract for a single field.
        Returns {field: value} on success, {} on failure/timeout/empty
        response. NEVER raises."""
        try:
            from app.services.serper_service import search_web
            from app.services import openai_service as _openai_svc

            query = f"{full_name} {field.replace('_', ' ')} specifications"
            search_results = await search_web(query, num_results=3)
            snippets = []
            for hit in (search_results.get("organic") or [])[:3]:
                snippet = hit.get("snippet", "")
                if snippet:
                    snippets.append(snippet)
            context = "\n".join(snippets)
            if not context:
                return {}
            result = await _openai_svc.extract_specs_targeted(
                brand=brand,
                name=name,
                variant=variant,
                category=category,
                fields=[field],
                context=context,
            )
            if result and isinstance(result, dict):
                val = result.get(field)
                if val and val not in ("N/A", ""):
                    return {field: val}
            return {}
        except Exception:  # noqa: BLE001 — silent omission per § 2h
            return {}

    async def _run_all():
        # Parallel gather — all fields race within the 4s wall.
        tasks = [_fill_one_field(f) for f in missing]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged = {}
        for r in results:
            if isinstance(r, dict):
                merged.update(r)
        return merged

    try:
        return await asyncio.wait_for(_run_all(), timeout=_TIER2_WALL_SECONDS)
    except asyncio.TimeoutError:
        logger.info(
            f"[TIER2_FALLBACK] timeout filling {missing} for {brand} {name}"
        )
        return {}
    except Exception as e:  # noqa: BLE001 — never escape
        logger.warning(f"[TIER2_FALLBACK] error: {e}")
        return {}


# Bundle D Task 2.B.4 (A.4.8) — Tier 3 GPT-4o batched synthesis fallback.
# Fires AFTER Tier 1 + smart-fallback + Tier 2 when non-negotiable schema
# fields STILL remain blank. Last-resort: a single batched gpt-4o call
# (priority="high" via model_router) synthesizes all still-missing fields
# from the model's training knowledge in one round-trip — no Serper, no
# per-field fan-out. Marked confidence='tier3_synthesis' so downstream
# fact-check / trust validation can flag these values as inferred.
#
# Wall budget: 3s outer asyncio.wait_for (per spec § 2f).
# Cost guard: ONE gpt-4o call per product (vs Tier 2's per-field-mini fan-out).
#   Single call typical cost is ~$0.001-0.005 with priority="high" routing;
#   only fires when both Tier 1 + Tier 2 failed (rare on warm cache, more
#   likely on cold-cache niche products).
# Silent omission per § 2h on timeout/failure — NO exception escapes.
_TIER3_WALL_SECONDS = 3.0


async def tier3_synthesize_non_negotiables(
    *,
    brand: str,
    name: str,
    variant,
    category: str,
    specs_so_far: dict,
) -> dict:
    """Bundle D A.4.8 — Tier 3 batched GPT-4o synthesis for non-negotiable
    schema fields still blank after Tier 1 + smart-fallback + Tier 2.

    Returns a dict of {field: value} for fields successfully filled by
    GPT-4o synthesis. Empty dict on no-op (all non-negotiables already
    filled) or on timeout/failure. NEVER raises — silent omission per § 2h.

    Differs from Tier 2:
      - ONE GPT call per product (Tier 2 = N calls, one per field).
      - Uses gpt-4o (priority='high' via model_router) — better synthesis
        from training data; Tier 2 uses gpt-4o-mini for speed.
      - NO Serper search — pure training-data synthesis.
      - Marks each filled field as confidence='tier3_synthesis' so trust
        validation can treat it as inferred rather than retrieved.
    """
    from app.services.extraction_service import (
        CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE,
    )
    from app.services.model_router_service import model_router

    non_negotiable = CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE.get(category, [])
    if not non_negotiable:
        return {}

    missing = [
        f for f in non_negotiable
        if not specs_so_far.get(f) or specs_so_far.get(f) in ("N/A", "")
    ]
    if not missing:
        return {}

    full_name = f"{brand} {name} {variant or ''}".strip()

    async def _synth_call():
        from app.services import openai_service as _openai_svc

        # Single batched call — list all missing fields in one prompt.
        model = await model_router.get_model(priority="high")
        return await _openai_svc.extract_specs_synthesized(
            brand=brand,
            name=name,
            variant=variant,
            category=category,
            fields=missing,
            model=model,
        )

    try:
        result = await asyncio.wait_for(_synth_call(), timeout=_TIER3_WALL_SECONDS)
        if not result or not isinstance(result, dict):
            return {}
        filled = {}
        for field in missing:
            val = result.get(field)
            if val and val not in ("N/A", ""):
                filled[field] = val
        return filled
    except asyncio.TimeoutError:
        logger.info(
            f"[TIER3_SYNTH] timeout synthesizing {missing} for {brand} {name}"
        )
        return {}
    except AttributeError as e:
        # extract_specs_synthesized may not exist yet on openai_service in
        # some test fixtures — log + skip cleanly rather than crash.
        logger.warning(f"[TIER3_SYNTH] openai_service missing helper: {e}")
        return {}
    except Exception as e:  # noqa: BLE001 — never escape
        logger.warning(f"[TIER3_SYNTH] error: {e}")
        return {}


def _classify_comparison_quality(
    *,
    cat_a: str,
    cat_b: str,
    spec_coverage_a: float,
    spec_coverage_b: float,
    price_a: float,
    price_b: float,
) -> str:
    """Bundle C § 2e — explicit-args classifier (test-bundle-c contract).

    Used by unit tests that want to drive the classifier with already-
    computed coverage ratios + prices. detect_comparison_quality() is
    the products-list orchestration entry point and delegates here.
    """
    # Rule 1: cross-category → weird.
    if cat_a and cat_b and cat_a.strip().lower() != cat_b.strip().lower():
        return "weird"
    # Rule 3: 10x+ price spread → weird (boundary inclusive per spec).
    if price_a is not None and price_b is not None and price_a > 0 and price_b > 0:
        lo, hi = min(price_a, price_b), max(price_a, price_b)
        if hi / lo >= 10.0:
            return "weird"
    # Rule 2: post-fallback >50% missing on either side → weird.
    # (When callers pass already-resolved coverage ratios, those reflect the
    # post-fallback state — apply the weird-jump immediately.)
    if spec_coverage_a is not None and spec_coverage_a < 0.5:
        return "weird"
    if spec_coverage_b is not None and spec_coverage_b < 0.5:
        return "weird"
    # Soft signal: under 0.85 coverage on either side → weak (gives Tier 2/3 room).
    if (spec_coverage_a is not None and spec_coverage_a < 0.85) or (
        spec_coverage_b is not None and spec_coverage_b < 0.85
    ):
        return "weak"
    return "normal"


def detect_comparison_quality(products, post_fallback=False) -> str:
    """Bundle C § 2e — classify a comparison as normal / weak / weird.

    `post_fallback=True` signals that the 3-tier spec fallback has already
    run, so any remaining missing-spec gap is structural rather than fixable.
    Defaults to False so callers in pre-Phase-2 paths get the softer 'weak'
    label instead of jumping straight to 'weird'.

    Returns 'normal' for happy-path comparisons; spec § 2e detector triggers
    are intentionally conservative — 'weird' must reflect a genuinely
    suspect pairing, never just sparse early-pipeline data.
    """
    if not products or len(products) < 2:
        return "normal"

    # Rule 1: cross-category (category_used mismatch) → weird.
    cats = [_product_category(p) for p in products]
    if cats[0] and cats[1] and cats[0] != cats[1]:
        return "weird"

    # Rule 3: 10x+ price spread → weird (only when both prices present).
    p0 = _product_price_amount(products[0])
    p1 = _product_price_amount(products[1])
    if p0 is not None and p1 is not None:
        lo, hi = min(p0, p1), max(p0, p1)
        if lo > 0 and hi / lo >= 10.0:
            return "weird"

    # Rule 2: post-fallback spec coverage check. Either product < 50% filled → weird.
    if post_fallback:
        for p in products:
            filled, expected = _product_spec_coverage(p)
            if filled / expected < 0.5:
                return "weird"

    # Soft signal: pre-fallback heavy spec gap → weak (gives Tier 2/3 room).
    for p in products:
        filled, expected = _product_spec_coverage(p)
        if filled / expected < 0.5:
            return "weak"

    return "normal"


# Phase 2A.1 — env-gated per-stage timing instrumentation.
# Read once per process (cache_var lookup in hot path is O(1) attribute access).
# Process restart picks up env changes; tests can reset via `scs._DEBUG_STAGE_TIMINGS = None`.
_DEBUG_STAGE_TIMINGS = None


def _debug_timings_enabled() -> bool:
    """Cached env var lookup. Read once per process to avoid os.environ
    hits in the hot path. Process restart picks up env changes."""
    global _DEBUG_STAGE_TIMINGS
    if _DEBUG_STAGE_TIMINGS is None:
        _DEBUG_STAGE_TIMINGS = os.environ.get("DEBUG_STAGE_TIMINGS", "false").lower() == "true"
    return _DEBUG_STAGE_TIMINGS


def _price_cache_bust_enabled() -> bool:
    """I5.1 (Bundle B S2) — diagnostic probe flag scoped to PRICE only.

    When `PRICE_CACHE_BUST=true`, `_get_price` force-misses BOTH the Redis price
    cache and the L2 DB price read so the Tier-1.5 escalation re-runs
    deterministically (F1.7 §3: cached Tier-3 estimates otherwise short-circuit
    the routing probe). Specs/reviews caches are untouched — they gate on the
    unchanged `nocache` arg — so the wall still fits the 30s cap.

    Read FRESH each call (NOT process-cached like _debug_timings_enabled) so a
    probe session can flip the env mid-run without a redeploy. MUST be off
    (unset/false) in normal operation — this is evidence-gathering, not runtime.
    """
    return os.environ.get("PRICE_CACHE_BUST", "false").lower() == "true"


async def _timed_task(label: str, coro, timings_dict):
    """Await a coroutine and record its elapsed time into timings_dict[label + '_ms'].
    Safe inside asyncio.gather — each wrapper records its OWN per-task wall (independent
    measurement) while gather still runs them concurrently. timings_dict=None → no-op."""
    if timings_dict is None:
        return await coro
    import time as _t
    t = _t.perf_counter()
    try:
        return await coro
    finally:
        timings_dict[f"{label}_ms"] = round((_t.perf_counter() - t) * 1000, 1)


# Import from new modules
from app.services.price_service import (
    _convert_to_bhd,
    _convert_gpt_price_currency,
    validate_price_query,
    validate_scrape_url,
    is_counterfeit_listing,
    is_accessory,
    is_high_value_query,
    is_price_plausible,
    is_luxury_brand,
    is_supplement_query,
    extract_domain,
    parse_price_string,
    detect_currency,
    normalize_words,
    numbers_match,
    strict_title_match,
    get_retailer_score,
    has_retailer_url,
    build_retailer_url,
    sanitize_gpt_price,
    get_official_domain,
    extract_price_from_shopping,
    extract_jsonld_price,
    extract_price_from_html,
    curl_fetch_html,
    fetch_page_price,
    fetch_shopify_price,
    fetch_iherb_price,
    fetch_pharmacy_price,
    fan_out_price_lookup,
    # Constants re-exported for backward compat
    MODEL_VARIANT_PATTERN,
    PRICE_CACHE_TTL,
    RETAILER_TIERS,
    DEFAULT_RETAILER_SCORE,
    RETAILER_SEARCH_URLS,
    ACCESSORY_KEYWORDS,
    HIGH_VALUE_KEYWORDS,
    COUNTERFEIT_KEYWORDS,
    LUXURY_BRAND_KEYWORDS,
    OFFICIAL_BRAND_DOMAINS,
    AUTHORIZED_LUXURY_RETAILERS,
    GCC_LUXURY_RETAILERS,
    SUPPLEMENT_KEYWORDS,
    MANUFACTURER_BRAND_WORDS,
    PHARMACY_DOMAINS,
    CURRENCY_SYMBOLS,
    CURRENCY_CODES,
    PAGE_SCRAPE_TIMEOUT,
    TIER_15_BUDGET_TIMEOUT,
    ENABLE_PAGE_SCRAPE,
)
from app.services.rating_service import (
    get_rating_tier,
    collect_retailer_ratings,
    extract_rating_from_shopping,
    get_verified_rating,
    RATING_TIER_1,
    RATING_TIER_2,
    RATING_TIER_3,
)
# L2.5 — confidence-driven escalation replaces the legacy is_luxury_brand()
# gate. The predicate fires the Tier 1.5 page-scrape cascade for ANY category
# (electronics, supplements, fragrances, ...) when Tier 1 Serper data is
# low-confidence — not just for luxury brands.
from app.services.confidence_service import (
    compute_price_confidence,
    should_escalate,
)
from app.services.review_service import (
    clean_review_content,
    clean_review_citations,
    format_review_search_results,
    get_reviews as _get_reviews_standalone,
    REVIEWS_CACHE_TTL,
    CATEGORY_REVIEW_TERMS,
    GARBAGE_PATTERNS,
    NEGATIVE_INDICATORS,
    POSITIVE_INDICATORS,
)
from app.services.fact_check_service import (
    verify_spec_citations,
    cross_validate_specs_with_shopping,
    verify_review_sentiment,
    verify_price,
    build_fact_check,
    NUMERIC_SPEC_FIELDS,
)
from app.services.response_builder import (
    build_comparison_response,
    derive_rating_from_scores,
    _youtube_signal_for_response,  # S3 L2 — streaming reviews-event parity
)
from app.services.image_service import get_product_image_url
# B.0 (Bundle B Lane F1) — Bahrain-first source registry. Wires the weighted
# SOURCE_REGISTRY into the Tier 1.5 price-escalation cascade: a Bahrain
# `site:` discovery query runs FIRST, and every candidate is gated registry-
# first (score_source >= 1.5) with the legacy whitelist sets as fallback.
from app.services.source_router import (
    build_site_discovery_query,
    score_source,
    source_usage,
    is_wrong_locale_url,
    get_shopify_sources_for_category,
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

logger = logging.getLogger(__name__)

# Cache TTLs
SPECS_CACHE_TTL = 7 * 24 * 60 * 60    # 7 days

# Bundle E § Decision 8 + Decision 9 — hard cap on the streaming pipeline.
# A runaway scraper or slow GPT response cannot extend the SSE stream past
# this many seconds. asyncio.wait_for(...) wraps the data-fetch + scoring
# + verdict pipeline; on timeout the orchestrator yields a `settle_complete`
# with whatever fields we have so far and the client unblocks.
STREAM_HARD_CAP_SECONDS = float(os.getenv("STREAM_HARD_CAP_SECONDS", "25.0"))

# I5.6 lever-3 — per-race cap on the Phase-2 verified-rating fetch. The rating
# cascade (Serper Tier 1→2→3 + GPT fallback) was the one UNCAPPED Phase-2 race;
# 4s matches the measured warm rating floor with headroom while keeping a slow
# cold cascade from dragging the Phase-2 gather past budget. On timeout the rating
# falls back to the benign default + GPT-review-aggregate path (zero quality
# change vs the pre-cap behavior, which made the user wait on the same slow call).
_PHASE2_RATING_TIMEOUT = 4.0


def build_settle_update_event(
    *,
    field: str,
    new_value: Any,
    source_rank: int,
) -> Tuple[str, Dict[str, Any]]:
    """Compose a `settle_update` SSE event per design § Decision 8.

    Payload contract: `{field, new_value, source_rank}`. Frontend fades the
    new value into the corresponding spot in result state. Returned as the
    `(event_type, payload)` tuple our streaming generator yields.
    """
    return (
        "settle_update",
        {
            "field": field,
            "new_value": new_value,
            "source_rank": source_rank,
        },
    )


def build_confidence_upgrade_event(
    *,
    dimension_key: str,
    new_confidence: str,
) -> Tuple[str, Dict[str, Any]]:
    """Compose a `confidence_upgrade` SSE event per design § Decision 8.

    Payload contract: `{dimension_key, new_confidence}`. Frontend pops the
    confidence dot from gray to emerald when this fires for a dimension.
    """
    return (
        "confidence_upgrade",
        {
            "dimension_key": dimension_key,
            "new_confidence": new_confidence,
        },
    )


# Bundle E § Decision 8 — quality-ranker rank values for the luxury cascade.
# Mirrors PRICE_SOURCE_RANK in app/services/quality_ranker.py; centralised
# here so the scraper-builder can stamp each candidate at construction time
# without importing quality_ranker (which would create a circular dep risk
# in the future if quality_ranker grows to need price_service helpers).
_RANK_FIRECRAWL_BRAND_DOMAIN = 90
_RANK_PAGE_SCRAPE_JSONLD = 85
_RANK_SCRAPEDO_RENDERED = 70


async def _curl_scraper(
    url: str, full_name: str, currency: str, retailer_domain: str
) -> Optional[Dict[str, Any]]:
    """Wrap fetch_page_price() to return a fan_out candidate dict.

    fan_out_price_lookup expects `{value, source_method, rank, raw_data}`.
    fetch_page_price returns the legacy `{amount, currency, retailer, ...}`
    price dict — translate the shape here so the existing scraper stays
    untouched.
    """
    try:
        page_price = await fetch_page_price(url, full_name, currency)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[fan_out curl] {url} raised: {e}")
        return None
    if not page_price or not page_price.get("amount"):
        return None
    page_price.pop("_got_html", None)
    page_price["retailer"] = page_price.get("retailer") or retailer_domain
    # L2 content safety — fan-out curl scraper entry point (Bundle B,
    # team-lead expansion of spec sec 5.2). fetch_page_price() already
    # filters at the HTML-extraction level, but we re-check the candidate
    # surface here so retailer-domain garbling can't slip through.
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{page_price.get('title', '')} {page_price.get('retailer', '')} {full_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped fan-out curl candidate for %s", retailer_domain)
        return None
    return {
        "value": float(page_price["amount"]),
        "source_method": "page_scrape_jsonld",
        "rank": _RANK_PAGE_SCRAPE_JSONLD,
        "raw_data": page_price,
    }


async def _firecrawl_scraper(
    url: str, full_name: str, currency: str, retailer_domain: str
) -> Optional[Dict[str, Any]]:
    """Firecrawl wrapper that checks budget + circuit breaker before firing,
    records usage/failure, and returns the fan_out candidate shape."""
    if not (firecrawl_service.is_available()
            and is_circuit_closed("firecrawl")
            and has_budget("firecrawl")):
        return None
    try:
        html, status = await firecrawl_service.scrape_page_with_status(url)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[fan_out firecrawl] {url} raised: {e}")
        return None
    if status == 200:
        record_usage("firecrawl")
    if not html:
        if status in (429, 503) or status == 0:
            record_failure("firecrawl")
        return None
    record_success("firecrawl")
    price = extract_price_from_html(html, full_name, currency, retailer_domain, url)
    if not price or not price.get("amount"):
        return None
    price["source_method"] = "firecrawl"
    price["retailer"] = retailer_domain
    # L2 content safety — Firecrawl Tier 1.5a entry point (Bundle B,
    # team-lead expansion of spec sec 5.2).
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{price.get('title', '')} {retailer_domain} {full_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped Firecrawl candidate for %s", retailer_domain)
        return None
    return {
        "value": float(price["amount"]),
        "source_method": "firecrawl_brand_domain",
        "rank": _RANK_FIRECRAWL_BRAND_DOMAIN,
        "raw_data": price,
    }


async def _scrapedo_scraper(
    url: str, full_name: str, currency: str, retailer_domain: str
) -> Optional[Dict[str, Any]]:
    """Scrape.do wrapper — residential proxy fallback for SPA pages."""
    if not (scrapedo_service.is_available()
            and is_circuit_closed("scrapedo")
            and has_budget("scrapedo")):
        return None
    if not validate_scrape_url(url):
        return None
    try:
        html, status = await scrapedo_service.render_page_with_status(url)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[fan_out scrapedo] {url} raised: {e}")
        return None
    if status == 200:
        record_usage("scrapedo")
    if not html:
        if status in (429, 503) or status == 0:
            record_failure("scrapedo")
        return None
    record_success("scrapedo")
    price = extract_price_from_html(html, full_name, currency, retailer_domain, url)
    if not price or not price.get("amount"):
        return None
    price["source_method"] = "scrapedo_rendered"
    price["retailer"] = retailer_domain
    # L2 content safety — Scrape.do Tier 1.5d entry point (Bundle B,
    # team-lead expansion of spec sec 5.2).
    from app.services.content_safety_service import get_content_safety_service
    _surface = f"{price.get('title', '')} {retailer_domain} {full_name}"
    if not get_content_safety_service().is_text_safe(_surface):
        logger.info("[content_safety] L2 dropped Scrape.do candidate for %s", retailer_domain)
        return None
    return {
        "value": float(price["amount"]),
        "source_method": "scrapedo_rendered",
        "rank": _RANK_SCRAPEDO_RENDERED,
        "raw_data": price,
    }


def _should_escalate_price_scrape(
    sources: List[Dict[str, Any]],
    training_estimate: Optional[float] = None,
    brand: Optional[str] = None,
) -> bool:
    """L2.5 — confidence-driven Tier 1.5 escalation gate.

    Replaces the legacy ``is_luxury_brand()`` gate. Now fires for any
    category when Tier 1 Serper data is weak (single source from a low-score
    retailer, sources disagreeing, or a 40%+ deviation from the training
    estimate). ``brand`` is accepted for legacy compat but ignored —
    confidence metrics drive the decision.
    """
    if not sources:
        return True
    confidence = compute_price_confidence(
        sources, training_estimate=training_estimate
    )
    return should_escalate(confidence)


def _sanity_check_thresholds(
    sources: List[Dict[str, Any]],
) -> Tuple[float, float]:
    """B0-B Item 2 — confidence-driven Tier-1/Tier-2 sanity-check band.

    Replaces the legacy ``is_luxury_brand()`` band selection. Returns
    ``(high_threshold, low_threshold)`` for the Tier-3 sanity-check ratio:
    a Tier-1/Tier-2 amount outside ``[low * tier3, high * tier3]`` triggers
    a Tier-3 swap. Low-confidence sources (single weak source / sources
    disagree / low retailer score) get the tighter luxury-equivalent band
    (1.8 / 0.6); medium-or-better confidence gets the looser default
    (2.0 / 0.5).
    """
    confidence = compute_price_confidence(sources)
    if confidence.get("level") == "low":
        return 1.8, 0.6
    return 2.0, 0.5


def _build_escalation_scrapers(
    *,
    candidate_urls: List[Tuple[str, str]],
    full_name: str,
    currency: str,
    scraping_mode: str,
    wave: str = "all",
) -> List[Callable[[dict], Awaitable[Optional[Dict[str, Any]]]]]:
    """Bundle E § Decision 8 — build the scraper list for fan_out_price_lookup().

    `wave` (S3-genuine Approach A part 2 — budget-discipline two-wave split):
      - "curl"   → ONLY the free curl scrapers (the curl-first early-exit wave).
      - "render" → ONLY the paid Firecrawl/Scrape.do scrapers (escalation wave,
                   run ONLY after the curl wave misses — Ahmed: render not fired
                   every escalation).
      - "all"    → both (legacy single-wave behaviour; kept for callers that
                   don't split).

    For each (url, retailer_domain) pair (Serper-discovered, locale-filtered):
      - A curl scraper (free, fast) — emitted for wave in {curl, all}.
      - Firecrawl + Scrape.do if should_fan_out(url) passes (SCRAPING_MODE gate)
        — emitted for wave in {render, all}.

    Each scraper accepts a `product` dict (ignored — closure captures
    full_name/currency/retailer_domain) and returns either None or a
    `{value, source_method, rank, raw_data}` candidate. fan_out_price_lookup
    races them, applies select-best, cancels pending on confirm.
    """
    want_curl = wave in ("curl", "all")
    want_render = wave in ("render", "all")
    scrapers: List[Callable[[dict], Awaitable[Optional[Dict[str, Any]]]]] = []
    for url, retailer_domain in candidate_urls:
        if not validate_scrape_url(url):
            continue
        if want_curl:
            # Curl scrape — always free.
            async def _curl_with_args(_product, _url=url, _retailer=retailer_domain):
                return await _curl_scraper(_url, full_name, currency, _retailer)
            scrapers.append(_curl_with_args)

        # Firecrawl + Scrape.do gated by SCRAPING_MODE per design § Decision 8.
        # In soft mode only luxury/SPA domains get the rendered-scrape budget.
        if want_render and firecrawl_service.should_fan_out(url, mode=scraping_mode):
            async def _fc_with_args(_product, _url=url, _retailer=retailer_domain):
                return await _firecrawl_scraper(_url, full_name, currency, _retailer)
            scrapers.append(_fc_with_args)

            async def _sd_with_args(_product, _url=url, _retailer=retailer_domain):
                return await _scrapedo_scraper(_url, full_name, currency, _retailer)
            scrapers.append(_sd_with_args)

    return scrapers


# DEPRECATED — use _build_escalation_scrapers; remove in Bundle C.
# Legacy name retained for one release so existing monkeypatch tests
# (test_fan_out_integration.py) keep working without simultaneous churn.
_build_luxury_scrapers = _build_escalation_scrapers


def _harvest_candidate_urls(
    results_by_tier: Dict[str, Any],
    official_domain: Optional[str],
    category: str,
) -> List[Tuple[str, str, str, float]]:
    """B.0 (Lane F1) — order Serper discovery results into a candidate pool.

    Priority order: **bahrain (registry) -> official -> authorized -> gcc**.
    Returns `(link, domain_label, route, source_weight)` per candidate; the
    caller derives the legacy `(link, label)` `candidate_urls` shape and uses
    `route`/`source_weight` for `source_trace` observability (F1.4).

    Gating (registry-first, legacy-fallback — Dispatcher invariant #1):
    - bahrain tier: a link enters ONLY when `score_source(link, category) >= 1.5`
      (registry membership IS the counterfeit whitelist — unknown domains score
      0.5 and are rejected).
    - authorized / gcc tiers: registry pass (`score_source >= 1.5`) OR legacy
      whitelist membership (`OFFICIAL_BRAND_DOMAINS` / `AUTHORIZED_LUXURY_RETAILERS`
      / `GCC_LUXURY_RETAILERS`). The legacy sets remain the fallback path while
      we watch the registry win in `source_trace` before deleting them.
    - official tier: the existing same-domain check against `official_domain`.
    """
    harvested: List[Tuple[str, str, str, float]] = []

    # --- Bahrain registry tier (NEW, harvested FIRST) ---
    bh = results_by_tier.get("bahrain")
    if bh and bh.get("organic"):
        for item in bh["organic"][:4]:
            link = item.get("link", "")
            if not link or not validate_scrape_url(link):
                continue
            # S2 I2.5 — review-only registry domains carry no prices; keep them
            # out of the price scrape pool (usage in price/both only).
            if source_usage(link, category) == "review":
                continue
            weight = score_source(link, category)
            if weight >= 1.5:
                link_domain = urlparse(link).netloc.replace("www.", "").lower()
                harvested.append((link, link_domain, "registry", weight))

    # --- Official brand domain (same-domain check preserved) ---
    if official_domain and "official" in results_by_tier:
        official_results = results_by_tier["official"]
        if official_results and official_results.get("organic"):
            for organic_item in official_results["organic"][:2]:
                link = organic_item.get("link")
                if not link or not validate_scrape_url(link):
                    continue
                link_domain = urlparse(link).netloc.replace("www.", "").lower()
                od = official_domain.lower()
                if link_domain == od or link_domain.endswith("." + od):
                    harvested.append(
                        (link, official_domain, "official", score_source(link, category))
                    )

    # --- Authorized retailers (registry-first, legacy-fallback) ---
    if "authorized" in results_by_tier:
        retailer_results = results_by_tier["authorized"]
        if retailer_results and retailer_results.get("organic"):
            for item in retailer_results["organic"][:5]:
                link = item.get("link", "")
                if not link:
                    continue
                if source_usage(link, category) == "review":
                    continue  # S2 I2.5 — review-only domain, no prices
                link_domain = urlparse(link).netloc.replace("www.", "")
                weight = score_source(link, category)
                if weight >= 1.5:
                    harvested.append((link, link_domain, "registry", weight))
                elif (
                    link_domain in AUTHORIZED_LUXURY_RETAILERS
                    or link_domain in OFFICIAL_BRAND_DOMAINS
                ):
                    harvested.append((link, link_domain, "legacy_fallback", weight))

    # --- GCC retailers (registry-first, legacy-fallback) ---
    if "gcc" in results_by_tier:
        gcc_results = results_by_tier["gcc"]
        if gcc_results and gcc_results.get("organic"):
            for item in gcc_results["organic"][:3]:
                link = item.get("link", "")
                if not link:
                    continue
                if source_usage(link, category) == "review":
                    continue  # S2 I2.5 — review-only domain, no prices
                link_domain = urlparse(link).netloc.replace("www.", "")
                weight = score_source(link, category)
                if weight >= 1.5:
                    harvested.append((link, link_domain, "registry", weight))
                elif link_domain in GCC_LUXURY_RETAILERS:
                    harvested.append((link, link_domain, "legacy_fallback", weight))

    # S3-genuine (team-lead live probe 2026-06-14) — BH-LOCALE FILTER. Serper
    # `site:` discovery returns mixed-locale results for the multi-locale BH
    # registry domains; score_source matches by domain and IGNORES the locale
    # path, so an extra.com/en-sa/ (SAR) page scores 3.0 and would be scraped →
    # a Saudi price. Drop any candidate carrying a non-BH GCC locale segment
    # BEFORE it enters candidate_urls/fan_out (the genuine /en-bh/ PDP Serper
    # also returns survives and extracts BHD). No rewrite (SKUs differ per
    # locale). Applies across ALL tiers in one place.
    filtered = [h for h in harvested if not is_wrong_locale_url(h[0])]
    if len(filtered) != len(harvested):
        logger.info(
            "[PRICE] BH-locale filter dropped %d wrong-locale candidate(s)",
            len(harvested) - len(filtered),
        )
    return filtered


class StructuredComparisonService:
    """Main service for structured product comparisons.

    Orchestrates: parse -> fetch -> score -> compare -> build response.
    Delegates price/rating/review/fact-check to focused modules.
    """

    # Class-level constants preserved for backward compat (tests reference self.CONSTANT)
    ACCESSORY_KEYWORDS = ACCESSORY_KEYWORDS
    HIGH_VALUE_KEYWORDS = HIGH_VALUE_KEYWORDS
    COUNTERFEIT_KEYWORDS = COUNTERFEIT_KEYWORDS
    LUXURY_BRAND_KEYWORDS = LUXURY_BRAND_KEYWORDS
    OFFICIAL_BRAND_DOMAINS = OFFICIAL_BRAND_DOMAINS
    AUTHORIZED_LUXURY_RETAILERS = AUTHORIZED_LUXURY_RETAILERS
    GCC_LUXURY_RETAILERS = GCC_LUXURY_RETAILERS
    SUPPLEMENT_KEYWORDS = SUPPLEMENT_KEYWORDS
    MANUFACTURER_BRAND_WORDS = MANUFACTURER_BRAND_WORDS
    PHARMACY_DOMAINS = PHARMACY_DOMAINS
    CATEGORY_REVIEW_TERMS = CATEGORY_REVIEW_TERMS
    GARBAGE_PATTERNS = GARBAGE_PATTERNS
    NEGATIVE_INDICATORS = NEGATIVE_INDICATORS
    POSITIVE_INDICATORS = POSITIVE_INDICATORS
    RATING_TIER_1 = RATING_TIER_1
    RATING_TIER_2 = RATING_TIER_2
    RATING_TIER_3 = RATING_TIER_3
    CURRENCY_SYMBOLS = CURRENCY_SYMBOLS
    CURRENCY_CODES = CURRENCY_CODES
    PAGE_SCRAPE_TIMEOUT = PAGE_SCRAPE_TIMEOUT
    TIER_15_BUDGET_TIMEOUT = TIER_15_BUDGET_TIMEOUT

    def __init__(self):
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}
        # B.0 (Lane F1, F1.4) — per-request Tier 1.5 routing record, keyed by
        # full_name -> {route, source_weight}. Written when a registry/legacy
        # candidate wins the fan_out race; read by the source_trace builder so
        # each price-value trace entry records which path fired.
        self._tier15_routes: Dict[str, Dict[str, Any]] = {}

    # ============================================
    # Static method wrappers for backward compat
    # (tests call svc._is_luxury_brand() etc.)
    # ============================================

    @staticmethod
    def _is_counterfeit_listing(title: str) -> bool:
        return is_counterfeit_listing(title)

    @staticmethod
    def _is_accessory(title: str) -> bool:
        return is_accessory(title)

    @staticmethod
    def _is_high_value_query(product_name: str) -> bool:
        return is_high_value_query(product_name)

    @staticmethod
    def _is_luxury_brand(product_name: str) -> bool:
        return is_luxury_brand(product_name)

    @staticmethod
    def _is_supplement_query(product_name: str) -> bool:
        return is_supplement_query(product_name)

    @staticmethod
    def _validate_price_query(brand: str, name: str, region: str) -> bool:
        return validate_price_query(brand, name, region)

    @staticmethod
    def _validate_scrape_url(url: str) -> bool:
        return validate_scrape_url(url)

    @staticmethod
    def _extract_domain(url: str) -> str:
        return extract_domain(url)

    @staticmethod
    def _parse_price_string(price_str: str) -> Optional[float]:
        return parse_price_string(price_str)

    @staticmethod
    def _detect_currency(price_str: str) -> Optional[str]:
        return detect_currency(price_str)

    @staticmethod
    def _normalize_words(text: str) -> set:
        return normalize_words(text)

    @staticmethod
    def _numbers_match(product_name: str, title: str) -> bool:
        return numbers_match(product_name, title)

    @staticmethod
    def _strict_title_match(product_name: str, title: str) -> bool:
        return strict_title_match(product_name, title)

    @staticmethod
    def _get_retailer_score(retailer_name: str) -> float:
        return get_retailer_score(retailer_name)

    @staticmethod
    def _sanitize_gpt_price(price: Optional[Dict]) -> None:
        sanitize_gpt_price(price)

    @staticmethod
    def _convert_gpt_price_currency(price: Optional[Dict], target_currency: str) -> None:
        _convert_gpt_price_currency(price, target_currency)

    @staticmethod
    def _extract_jsonld_price(html: str, brand: str, expected_currency: str) -> Optional[Dict[str, Any]]:
        return extract_jsonld_price(html, brand, expected_currency)

    @staticmethod
    def _get_rating_tier(source: str) -> int:
        return get_rating_tier(source)

    @staticmethod
    def _clean_specs(specs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean specs for display; lift _source markers into _field_confidence."""
        if not specs or not isinstance(specs, dict):
            return {}
        meta_keys = {"brand", "model", "variant", "category", "_cached", "error"}

        # Lift _source siblings into a confidence map: snippet_N -> 'snippet',
        # 'training' -> 'training_data'. Used by UI to subtly indicate which
        # specs came from live search vs general product knowledge.
        field_confidence: Dict[str, str] = {}
        for key, value in specs.items():
            if not key.endswith("_source"):
                continue
            base_key = key[: -len("_source")]
            if not isinstance(value, str):
                continue
            if value.startswith("snippet"):
                field_confidence[base_key] = "snippet"
            elif value == "training":
                field_confidence[base_key] = "training_data"
            else:
                field_confidence[base_key] = value

        cleaned = {}
        for key, value in specs.items():
            if key in meta_keys:
                continue
            if key.endswith("_source"):
                continue
            if key.startswith("_"):
                continue
            if value is None or value == "" or value == "null" or (isinstance(value, str) and "or null" in value.lower()):
                cleaned[key] = "N/A"
            elif isinstance(value, list):
                cleaned[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                cleaned[key] = json.dumps(value)
            else:
                cleaned[key] = str(value) if not isinstance(value, str) else value

        if field_confidence:
            cleaned["_field_confidence"] = field_confidence
        return cleaned

    def _has_retailer_url(self, source: str) -> bool:
        return has_retailer_url(source)

    def _build_retailer_url(self, source: str, product_name: str) -> Optional[str]:
        return build_retailer_url(source, product_name)

    def _get_official_domain(self, product_name: str) -> Optional[str]:
        return get_official_domain(product_name)

    def _derive_rating_from_scores(self, overall_score: float) -> float:
        return derive_rating_from_scores(overall_score)

    # Delegated methods
    def _clean_review_content(self, reviews: dict) -> dict:
        return clean_review_content(reviews)

    def _clean_review_citations(self, reviews: dict, search_results: list) -> dict:
        return clean_review_citations(reviews, search_results)

    def _verify_spec_citations(self, specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
        return verify_spec_citations(specs, search_snippets)

    def _cross_validate_specs_with_shopping(self, specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
        return cross_validate_specs_with_shopping(specs, shopping_items)

    def _verify_review_sentiment(self, reviews: Dict, source_ratings: List[Dict]) -> Dict:
        return verify_review_sentiment(reviews, source_ratings)

    def _verify_price(self, price: Dict, shopping_items: List[Dict]) -> Dict:
        return verify_price(price, shopping_items)

    def _build_fact_check(self, product: Dict) -> Dict:
        return build_fact_check(product)

    def _extract_price_from_shopping(self, product_name: str, shopping_items: List[Dict], currency: str, shopping_region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return extract_price_from_shopping(product_name, shopping_items, currency, shopping_region=shopping_region)

    def _extract_price_from_html(self, html: str, product_name: str, currency: str, domain: str, url: str) -> Optional[Dict[str, Any]]:
        return extract_price_from_html(html, product_name, currency, domain, url)

    def _extract_rating_from_shopping(self, product_name: str, shopping_items: List[Dict]) -> Dict[str, Any]:
        return extract_rating_from_shopping(product_name, shopping_items)

    def _collect_retailer_ratings(self, full_name: str) -> List[Dict[str, Any]]:
        return collect_retailer_ratings(full_name, self._shopping_items_cache)

    async def _fetch_page_price(self, url: str, product_name: str, currency: str = "BHD") -> Optional[Dict[str, Any]]:
        """Fetch a product page via curl_cffi and extract price from structured data.
        Kept as instance method so tests can patch _curl_fetch_html via patch.object."""
        if not ENABLE_PAGE_SCRAPE:
            return None
        domain = urlparse(url).netloc.replace("www.", "")
        html = await self._curl_fetch_html(url)
        if html:
            price = extract_price_from_html(html, product_name, currency, domain, url)
            if price:
                return price
            return {"_got_html": True}
        return None

    async def _curl_fetch_html(self, url: str) -> Optional[str]:
        return await curl_fetch_html(url)

    async def _fetch_iherb_price(self, query: str, brand: str, full_name: str, region_code: str, currency: str) -> Optional[Dict[str, Any]]:
        return await fetch_iherb_price(query, brand, full_name, region_code, currency)

    async def _fetch_pharmacy_price(self, serper_organic: List[Dict], brand: str, full_name: str, currency: str) -> Optional[Dict[str, Any]]:
        return await fetch_pharmacy_price(serper_organic, brand, full_name, currency, track_serper_cost_fn=self._track_serper_cost)

    async def _try_pharmacy_urls(self, pharmacy_urls: List[Tuple[str, str]], brand: str, currency: str) -> Optional[Dict[str, Any]]:
        from app.services.price_service import _try_pharmacy_urls
        return await _try_pharmacy_urls(pharmacy_urls, brand, currency)

    # ============================================
    # Main entry points
    # ============================================

    async def compare_from_text(
        self,
        query: str,
        region: str = "bahrain",
        include_specs: bool = True,
        include_reviews: bool = True,
        include_pros_cons: bool = True,
        nocache: bool = False,
        selected_category: Optional[str] = None,
        vision_products: Optional[List[Dict]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        explicit_pair: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """L2.7 — hard-capped entry point: wraps `_compare_from_text_impl` in
        asyncio.wait_for(STREAM_HARD_CAP_SECONDS) so the non-streaming path
        gets the same 25s ceiling the streaming path already has. On timeout
        a graceful `success:false, code:TIMEOUT` response is returned instead
        of propagating asyncio.TimeoutError to the caller.
        """
        try:
            return await asyncio.wait_for(
                self._compare_from_text_impl(
                    query=query,
                    region=region,
                    include_specs=include_specs,
                    include_reviews=include_reviews,
                    include_pros_cons=include_pros_cons,
                    nocache=nocache,
                    selected_category=selected_category,
                    vision_products=vision_products,
                    user_preferences=user_preferences,
                    user_id=user_id,
                    explicit_pair=explicit_pair,
                ),
                timeout=STREAM_HARD_CAP_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[L2.7] compare_from_text hard-cap %.1fs hit for query=%r",
                STREAM_HARD_CAP_SECONDS, query,
            )
            return {
                "success": False,
                "error": "We couldn't finish this comparison in time. Try again.",
                "code": "TIMEOUT",
                "total_cost": self.total_cost,
            }

    async def _compare_from_text_impl(
        self,
        query: str,
        region: str = "bahrain",
        include_specs: bool = True,
        include_reviews: bool = True,
        include_pros_cons: bool = True,
        nocache: bool = False,
        selected_category: Optional[str] = None,
        vision_products: Optional[List[Dict]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        explicit_pair: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """Main entry point for text-based comparisons (post-L2.7 inner impl).

        explicit_pair: when provided (Bundle B dual-shape), the service
        skips parse_product_query() and trusts the caller's pair.
        """
        start_time = datetime.now()
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}

        # I5.6 lever-2 — bound to None at the top so the outer exception handler
        # can always cancel it (an exception raised before the kickoff line would
        # otherwise NameError on the cancel in the handler).
        _profile_task = None

        # Phase 2A.1 — orchestrator-level stage timings (only allocated when flag is on)
        orchestrator_timings = {} if _debug_timings_enabled() else None

        # L2.9 — per-request source_trace collector. Always-on observability
        # for which tiers fired for each race (price / specs / reviews /
        # image). Populated by `_fetch_product_data` then merged into
        # response.metadata.source_trace at response build time.
        self._source_trace: Dict[str, Any] = {}
        self._tier15_routes = {}

        # L1 content safety pre-filter (spec sec 5.2). Runs on the canonical query
        # string — for explicit_pair shape, this is the concatenated "A vs B"
        # form (validator already built it in text_routes.py), so the joined
        # surface is checked even on dual-shape input.
        from app.services.content_safety_service import get_content_safety_service
        from app.services.audit_service import log_content_blocked
        _safety = get_content_safety_service()
        _l1 = _safety.check_query_intent(query)
        if not _l1.allowed:
            _fire_and_forget(
                log_content_blocked(
                    layer="query_prefilter",
                    query_hash=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                ),
                "log_content_blocked(query_prefilter)",
            )
            return {
                "success": False,
                "error": "We don't compare this category",
                "code": "CONTENT_UNAVAILABLE",
                "layer": "query_prefilter",
            }

        try:
            # Step 1: Resolve products list (vision > explicit_pair > GPT parser)
            if vision_products and len(vision_products) >= 2:
                products = []
                for vp in vision_products[:2]:
                    brand = vp.get("brand", "Unknown")
                    vname = vp.get("name", "Unknown Product")
                    full = f"{brand} {vname}".strip()
                    category = "supplements" if is_supplement_query(full) else "other"
                    products.append({
                        "brand": brand, "name": vname,
                        "variant": vp.get("size_or_count"),
                        "category": category, "search_query": full, "_vision": True,
                    })
                parsed = {}
            elif explicit_pair:
                # Dual-shape (Bundle B): user explicitly typed both halves. Skip
                # parse_product_query() but still run sanitize_prompt_input on each
                # half so the same injection defense applies regardless of shape.
                from app.utils.prompt_sanitizer import sanitize_prompt_input
                products = []
                for raw in explicit_pair[:2]:
                    safe = sanitize_prompt_input(raw, max_length=80)
                    category = "supplements" if is_supplement_query(safe) else "other"
                    products.append({
                        "brand": "", "name": safe, "variant": None,
                        "category": category, "search_query": safe, "_explicit": True,
                    })
                parsed = {"comparison_type": "value"}
            else:
                query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
                logger.info(f"Parsing query: query_hash={query_hash} length={len(query)}")
                parsed, usage = await parse_product_query(query)
                self._track_gpt_cost(usage)

                if not parsed.get("products") or len(parsed["products"]) < 2:
                    return {
                        "success": False,
                        "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'",
                        "parsed": parsed
                    }

                products = parsed["products"][:2]

            # Determine category
            detected_category = products[0].get("category", "other")
            category_switched = False
            original_category = None
            if selected_category and selected_category != detected_category:
                category_switched = True
                original_category = selected_category
            category_used = detected_category

            # I5.6 lever-2 — start the behavioral-profile + demographics fetch
            # CONCURRENTLY with the product-data gather. Both fetches depend ONLY
            # on user_id (known here) and have zero dependency on product_data, so
            # kicking them off now overlaps their Supabase round-trips with the
            # product gather instead of running them sequentially after it. The
            # task is awaited at its original site below (just before scoring), so
            # scoring still consumes the same behavior_profile and the verdict the
            # same demographics_profile — zero quality change, pure latency. The
            # early-return paths between here and the await CANCEL this task so no
            # orphaned coroutine is left pending.
            if user_id:
                _profile_task = asyncio.ensure_future(asyncio.gather(
                    self._fetch_behavior_profile(user_id),
                    get_user_demographics(user_id),
                ))

            # Step 2: Fetch data for each product (parallel)
            product_data = await asyncio.gather(
                self._fetch_product_data(products[0], region, include_specs, include_reviews, nocache),
                self._fetch_product_data(products[1], region, include_specs, include_reviews, nocache)
            )

            # H6 (audit 2026-05-22): when both products' Phase 1 fetches
            # totally failed (specs=None AND price=None on both, meaning the
            # underlying gather caught exceptions for everything), bail out
            # instead of marching to scoring with all-MISSING_SCORE. The
            # deterministic tie-break in that path always picks product_0,
            # producing a fake "winner" with no data backing the verdict.
            if _phase1_completely_failed(product_data[0]) and _phase1_completely_failed(product_data[1]):
                logger.warning(
                    "INSUFFICIENT_DATA: both products' Phase 1 fetches returned None "
                    "for specs+price — refusing to score; query=%r region=%s",
                    query, region,
                )
                await _cancel_profile_task(_profile_task)
                return {
                    "success": False,
                    "error": "Comparison data was incomplete — choose different products.",
                    "code": "INSUFFICIENT_DATA",
                    "elapsed_seconds": (datetime.now() - start_time).total_seconds(),
                    "total_cost": self.total_cost,
                    "api_calls": self.api_calls,
                }

            # Fetch behavioral profile + demographics_profile if user is logged in.
            # I5.6 lever-2: the fetch was kicked off above (concurrent with the
            # product gather); here we just await the already-running task.
            behavior_profile = None
            demographics_profile = None
            if _profile_task is not None:
                behavior_profile, demographics_profile = await _profile_task

            # Step 3: Compute deterministic scores
            scoring_service = get_scoring_service()
            t_score = time.perf_counter() if orchestrator_timings is not None else None
            # S3 L3 v2 (c) — cohort priors into the SCORE weights. When the user
            # has no explicit preferences but has demographics, seed cohort-
            # inferred preferences and pass them as cohort_profile (compute_scores
            # applies them ±10%, only when no explicit prefs). Fail-soft: any error
            # leaves cohort_profile=None (pure category-weighted scoring).
            cohort_profile = self._derive_cohort_profile(user_preferences, demographics_profile)
            scoring_result = scoring_service.compute_scores(
                product_data, preferences=user_preferences, behavior_profile=behavior_profile,
                cohort_profile=cohort_profile,
            )
            if orchestrator_timings is not None:
                orchestrator_timings["scoring_ms"] = round((time.perf_counter() - t_score) * 1000, 1)
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in product_data
            ]
            scores_summary = scoring_service.build_scores_summary(scoring_result, product_names)

            # Step 4: Generate comparison (passes demographics_profile so the cohort
            # priors block in extraction_service can render when conditions are met).
            t_verdict = time.perf_counter() if orchestrator_timings is not None else None
            comparison, usage = await generate_comparison(
                product_data[0], product_data[1], region,
                parsed.get("comparison_type", "value") if not vision_products else "value",
                user_preferences=user_preferences,
                scores_summary=scores_summary, category=detected_category,
                demographics_profile=demographics_profile,
            )
            if orchestrator_timings is not None:
                orchestrator_timings["verdict_ms"] = round((time.perf_counter() - t_verdict) * 1000, 1)
            self._track_gpt_cost(usage)

            # I3.1 — optional self-critique pass (flag-gated OFF; no-op in prod
            # until ENABLE_SELF_CRITIQUE flips). May regenerate the verdict ONCE
            # when a quality axis scores low. Cost + latency tracked inside.
            comparison = await self._apply_self_critique(
                comparison=comparison,
                product_names=product_names,
                regen_args=dict(
                    product1=product_data[0], product2=product_data[1], region=region,
                    concern=parsed.get("comparison_type", "value") if not vision_products else "value",
                    user_preferences=user_preferences, scores_summary=scores_summary,
                    category=detected_category, demographics_profile=demographics_profile,
                ),
                pain_workflow_context=scores_summary,
                stage_timings=orchestrator_timings,
            )

            # Trust validation
            from app.services.trust_validation_service import validate_verdict
            verdict_validation = validate_verdict(comparison, scoring_result, detected_category)

            # Extract pros/cons
            if include_pros_cons:
                # Bundle C v1 hot-fix (round 2) § 1a diagnostic — log BEFORE
                # the pop so we see whether the keys are present in the
                # parsed comparison dict at this stage. If keys ARE present
                # but lists are empty → GPT emitted [] (prompt issue still).
                # If keys are MISSING → upstream stripper. Always-on WARNING
                # level — appears in Railway prod logs without flag gate.
                logger.warning(
                    "PROS_POP_DIAGNOSTIC path=compare_from_text keys=%s "
                    "p0_pros_present=%s p1_pros_present=%s "
                    "p0_pros_type=%s p1_pros_type=%s "
                    "p0_pros_len=%s p1_pros_len=%s",
                    list(comparison.keys()),
                    "product_0_pros" in comparison,
                    "product_1_pros" in comparison,
                    type(comparison.get("product_0_pros")).__name__,
                    type(comparison.get("product_1_pros")).__name__,
                    len(comparison.get("product_0_pros") or []) if isinstance(comparison.get("product_0_pros"), list) else "non-list",
                    len(comparison.get("product_1_pros") or []) if isinstance(comparison.get("product_1_pros"), list) else "non-list",
                )
                product_data[0]["pros_cons"] = {
                    "pros": comparison.pop("product_0_pros", []),
                    "cons": comparison.pop("product_0_cons", []),
                }
                product_data[1]["pros_cons"] = {
                    "pros": comparison.pop("product_1_pros", []),
                    "cons": comparison.pop("product_1_cons", []),
                }

            # Compute value badges
            for i, product in enumerate(product_data):
                value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
                price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
                product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)

            # Compute tradeoffs and confidence
            tradeoffs = scoring_service.compute_tradeoff_pairs(
                scoring_result.get("dimension_winners", {}), product_names, scoring_result.get("winner_index", 0)
            )
            from_cache = not nocache
            confidence = scoring_service.compute_confidence(
                product_data, shopping_count=len(self._shopping_items_cache), cached=from_cache
            )

            elapsed = (datetime.now() - start_time).total_seconds()

            t_build = time.perf_counter() if orchestrator_timings is not None else None
            # L2.9 — emit metadata.source_trace when the collector accumulated
            # any per-product records. Absent when the orchestrator never ran
            # Phase 1 (e.g. early-return on content-safety block).
            _metadata_override: Dict[str, Any] = {}
            if getattr(self, "_source_trace", None):
                _metadata_override["source_trace"] = self._source_trace
            # I3.2 — thread the self-critique outcome (internal key) so the
            # post-save path can persist it once the comparison_id exists.
            # Present only when the flag is ON and a critique actually ran.
            _crit_meta = self._verdict_critique_metadata()
            if _crit_meta:
                _metadata_override["_verdict_critique"] = _crit_meta

            result = build_comparison_response(
                product_data=product_data,
                comparison=comparison,
                scoring_result=scoring_result,
                product_names=product_names,
                tradeoffs=tradeoffs,
                confidence=confidence,
                verdict_validation=verdict_validation,
                user_preferences=user_preferences,
                from_cache=from_cache,
                query=query,
                region=region,
                category_used=category_used,
                category_switched=category_switched,
                original_category=original_category,
                total_cost=self.total_cost,
                api_calls=self.api_calls,
                gpt_calls=self.gpt_calls,
                serper_calls=self.serper_calls,
                elapsed_seconds=elapsed,
                metadata=_metadata_override or None,
            )
            if orchestrator_timings is not None:
                orchestrator_timings["response_build_ms"] = round((time.perf_counter() - t_build) * 1000, 1)
                orchestrator_timings["total_ms"] = round(
                    (datetime.now() - start_time).total_seconds() * 1000, 1
                )
                per_product = []
                for p in product_data:
                    t = p.pop("_stage_timings_ms", None)
                    if t:
                        per_product.append(t)
                orchestrator_timings["per_product"] = per_product
                result.setdefault("metadata", {})["stage_timings_ms"] = orchestrator_timings

            # Record whether the cohort priors block was active for this verdict.
            # Read by text_routes to write a `cohort_injected` user_events row
            # (powers vw_cohort_feedback_lift).
            if isinstance(result.get("metadata"), dict):
                result["metadata"]["cohort_injected"] = was_cohort_block_active(
                    demographics_profile
                )

            # L3 output moderation (spec sec 5.2). Joined verdict text + product
            # names + top review excerpts → omni-moderation-latest. Fails OPEN
            # on API exception (Build Principle #4). $0 — no _track_cost bump.
            # value_context is a per-product dict ({product_0, product_1} per
            # extraction_service.py:519). Flatten to a string before joining
            # — empty dicts are falsy and filtered by `filter(None,...)`, but
            # non-empty dicts pass through and crash str.join with
            # "expected str instance, dict found".
            _vc = comparison.get("value_context", "")
            if isinstance(_vc, dict):
                _vc = " ".join(str(v) for v in _vc.values() if v)
            _l3_text = " ".join(filter(None, [
                comparison.get("winner_declaration", ""),
                comparison.get("winner_reason", ""),
                comparison.get("key_tradeoff", ""),
                _vc,
                *product_names,
                *[
                    (h.get("text") if isinstance(h, dict) else str(h))
                    for pd in product_data
                    for h in (pd.get("reviews", {}) or {}).get("highlights", [])
                ][:10],
            ]))
            _l3 = await _safety.moderate_output(_l3_text)
            if not _l3.allowed:
                _fire_and_forget(
                    log_content_blocked(
                        layer="moderation_api",
                        query_hash=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    ),
                    "log_content_blocked(moderation_api)",
                )
                return {
                    "success": False,
                    "error": "We don't compare this category",
                    "code": "CONTENT_UNAVAILABLE",
                    "layer": "moderation_api",
                }

            # Fire-and-forget: update behavioral profile (M6: tracked so
            # silent task failures surface as WARNING logs).
            if user_id:
                _fire_and_forget(
                    self._update_behavior_profile(user_id),
                    "behavior_profile_update",
                )

            return result

        except Exception as e:
            logger.error(f"Comparison error: {e}", exc_info=True)
            # I5.6 lever-2 — if the failure happened before the profile task was
            # awaited, cancel it so no orphaned coroutine is left pending.
            await _cancel_profile_task(_profile_task)
            return {"success": False, "error": str(e), "total_cost": self.total_cost}

    async def compare_from_text_streaming(
        self,
        query: str,
        region: str = "bahrain",
        include_specs: bool = True,
        include_reviews: bool = True,
        include_pros_cons: bool = True,
        nocache: bool = False,
        selected_category: Optional[str] = None,
        vision_products: Optional[List[Dict]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        explicit_pair: Optional[Tuple[str, str]] = None,
    ):
        """Async generator version of compare_from_text that yields partial results."""
        start_time = datetime.now()
        self.total_cost = 0.0
        self.api_calls = 0
        self.gpt_calls = 0
        self.serper_calls = 0
        self._shopping_items_cache = {}

        # I5.6 lever-2 — bound to None at the top so the outer exception handler
        # can always cancel it (mirror of the sync path).
        _profile_task = None

        # Phase 2A.1 — orchestrator-level stage timings (only allocated when flag is on)
        orchestrator_timings = {} if _debug_timings_enabled() else None

        # L2.9 — per-request source_trace collector. Always-on observability
        # for which tiers fired for each race (price / specs / reviews /
        # image). Populated by `_fetch_product_data` then merged into
        # response.metadata.source_trace at response build time.
        self._source_trace: Dict[str, Any] = {}
        self._tier15_routes = {}

        # L1 content safety pre-filter (spec sec 5.2). Same gate as sync path —
        # blocked queries terminate the stream with an error event before any
        # parse/scrape work runs.
        from app.services.content_safety_service import get_content_safety_service
        from app.services.audit_service import log_content_blocked
        _safety = get_content_safety_service()
        _l1 = _safety.check_query_intent(query)
        if not _l1.allowed:
            _fire_and_forget(
                log_content_blocked(
                    layer="query_prefilter",
                    query_hash=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                ),
                "log_content_blocked(query_prefilter)",
            )
            yield ("error", {
                "success": False,
                "error": "We don't compare this category",
                "code": "CONTENT_UNAVAILABLE",
                "layer": "query_prefilter",
            })
            return

        try:
            # Step 1: Parse the query
            yield ("status", {"message": "Parsing query...", "progress": 10})

            if vision_products and len(vision_products) >= 2:
                products = []
                for vp in vision_products[:2]:
                    brand = vp.get("brand", "Unknown")
                    vname = vp.get("name", "Unknown Product")
                    full = f"{brand} {vname}".strip()
                    category = "supplements" if is_supplement_query(full) else "other"
                    products.append({
                        "brand": brand, "name": vname,
                        "variant": vp.get("size_or_count"),
                        "category": category, "search_query": full, "_vision": True,
                    })
                parsed = {}
            elif explicit_pair:
                # Dual-shape (Bundle B): user explicitly typed both halves. Skip
                # parse_product_query() but still sanitize each half.
                from app.utils.prompt_sanitizer import sanitize_prompt_input
                products = []
                for raw in explicit_pair[:2]:
                    safe = sanitize_prompt_input(raw, max_length=80)
                    category = "supplements" if is_supplement_query(safe) else "other"
                    products.append({
                        "brand": "", "name": safe, "variant": None,
                        "category": category, "search_query": safe, "_explicit": True,
                    })
                parsed = {"comparison_type": "value"}
            else:
                parsed, usage = await parse_product_query(query)
                self._track_gpt_cost(usage)

                if not parsed.get("products") or len(parsed["products"]) < 2:
                    yield ("error", {
                        "success": False,
                        "error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'",
                        "parsed": parsed,
                    })
                    return

                products = parsed["products"][:2]

            # Determine category
            detected_category = products[0].get("category", "other")
            category_switched = False
            original_category = None
            if selected_category and selected_category != detected_category:
                category_switched = True
                original_category = selected_category
            category_used = detected_category

            # Step 2: Fetch product data
            yield ("status", {"message": "Fetching specs and prices...", "progress": 20})

            # I5.6 lever-2 — start the behavioral-profile + demographics fetch
            # CONCURRENTLY with the product-data gather (mirror of the sync path).
            # Both fetches depend only on user_id and have zero dependency on
            # product_data, so overlapping their Supabase round-trips with the
            # product gather is pure latency. Awaited at the original site below;
            # the timeout + INSUFFICIENT_DATA early-return paths cancel it.
            if user_id:
                _profile_task = asyncio.ensure_future(asyncio.gather(
                    self._fetch_behavior_profile(user_id),
                    get_user_demographics(user_id),
                ))

            # Bundle E § Decision 8 — hard 25s cap on the data-fetch step.
            # Wraps both products' fetches together so a single hung scraper
            # can't extend the stream beyond the budget. On timeout we yield
            # `settle_complete` with partial data + the backward-compat
            # `complete` event, then exit cleanly.
            try:
                product_data = await asyncio.wait_for(
                    asyncio.gather(
                        self._fetch_product_data(products[0], region, include_specs, include_reviews, nocache),
                        self._fetch_product_data(products[1], region, include_specs, include_reviews, nocache),
                    ),
                    timeout=STREAM_HARD_CAP_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[stream] hard cap %.1fs exceeded while fetching product data for %r — "
                    "yielding settle_complete with partial response",
                    STREAM_HARD_CAP_SECONDS, query,
                )
                await _cancel_profile_task(_profile_task)
                partial_response = {
                    "success": False,
                    "error": "Comparison timed out — please try again.",
                    "code": "STREAM_TIMEOUT",
                    "elapsed_seconds": (datetime.now() - start_time).total_seconds(),
                    "total_cost": self.total_cost,
                    "api_calls": self.api_calls,
                }
                yield ("settle_complete", partial_response)
                yield ("complete", partial_response)
                return

            # H6 (audit 2026-05-22): same dual-failure guard as the sync path.
            # Refuse to march downstream when both products' fetches totally
            # failed — otherwise the SSE stream would yield empty `specs` +
            # `prices` events followed by a fake-winner verdict.
            if _phase1_completely_failed(product_data[0]) and _phase1_completely_failed(product_data[1]):
                logger.warning(
                    "INSUFFICIENT_DATA (stream): both products' Phase 1 fetches "
                    "returned None for specs+price — query=%r region=%s",
                    query, region,
                )
                await _cancel_profile_task(_profile_task)
                insufficient_response = {
                    "success": False,
                    "error": "Comparison data was incomplete — choose different products.",
                    "code": "INSUFFICIENT_DATA",
                    "elapsed_seconds": (datetime.now() - start_time).total_seconds(),
                    "total_cost": self.total_cost,
                    "api_calls": self.api_calls,
                }
                yield ("settle_complete", insufficient_response)
                yield ("complete", insufficient_response)
                return

            # Yield specs (Bundle E S3 — piggyback image_url onto specs event
            # since both land together at end of Phase 1; avoids adding a new
            # SSE event type that frontend would need to subscribe to).
            yield ("specs", {
                "products": [
                    {
                        "brand": pd.get("brand"),
                        "name": pd.get("name"),
                        "specs": pd.get("specs"),
                        "fact_check": pd.get("fact_check"),
                        "image_url": pd.get("image_url"),
                    }
                    for pd in product_data
                ]
            })

            # Yield prices
            scoring_service = get_scoring_service()
            prices_payload = {}
            for i, pd in enumerate(product_data):
                key = f"product_{i}"
                prices_payload[key] = {
                    "brand": pd.get("brand"), "name": pd.get("name"),
                    "price": pd.get("price"), "best_price": pd.get("best_price"),
                    "currency": pd.get("currency"), "retailer": pd.get("retailer"),
                }
            yield ("prices", prices_payload)

            # Yield reviews
            yield ("status", {"message": "Analyzing reviews...", "progress": 50})
            yield ("reviews", {
                "products": [
                    {
                        "brand": pd.get("brand"), "name": pd.get("name"),
                        "rating": pd.get("rating"), "review_count": pd.get("review_count"),
                        "rating_verified": pd.get("rating_verified"),
                        "rating_source": pd.get("rating_source"),
                        # See response_builder.py:963 — same (X or {}).get fix.
                        # Regression: PYTHON-FASTAPI-J event ecaa64acab224c599c9aba3bb92dfc89.
                        "review_summary": (pd.get("reviews") or {}).get("review_summary", {
                            "overall_sentiment": "mixed", "consensus": "",
                            "highlights": [], "review_volume": "minimal", "agreement_level": "moderate",
                        }),
                        # S3 L2 — streaming parity with the non-streaming reviews
                        # section (response_builder). Flag-gated; None when
                        # ENABLE_YOUTUBE_SOURCE OFF / no signal.
                        "youtube_review_signal": _youtube_signal_for_response(pd),
                    }
                    for pd in product_data
                ]
            })

            # Bundle E Task 2.5 § Decision 8 — first_paint marks "all core
            # dimensions ready, frontend can paint the UI." Fires after
            # specs+prices+reviews land; before scoring/verdict.
            yield ("first_paint", {
                "products": [
                    {"brand": pd.get("brand"), "name": pd.get("name")}
                    for pd in product_data
                ]
            })

            # Fetch behavioral profile + demographics_profile.
            # I5.6 lever-2: the fetch was kicked off above (concurrent with the
            # product gather); here we just await the already-running task.
            behavior_profile = None
            demographics_profile = None
            if _profile_task is not None:
                behavior_profile, demographics_profile = await _profile_task

            # Step 3: Compute scores
            t_score = time.perf_counter() if orchestrator_timings is not None else None
            # S3 L3 v2 (c) — cohort priors into the score weights (fail-soft).
            cohort_profile = self._derive_cohort_profile(user_preferences, demographics_profile)
            scoring_result = scoring_service.compute_scores(
                product_data, preferences=user_preferences, behavior_profile=behavior_profile,
                cohort_profile=cohort_profile,
            )
            if orchestrator_timings is not None:
                orchestrator_timings["scoring_ms"] = round((time.perf_counter() - t_score) * 1000, 1)
            product_names = [
                f"{p.get('brand', '')} {p.get('name', '')}".strip()
                for p in product_data
            ]
            scores_summary = scoring_service.build_scores_summary(scoring_result, product_names)

            from_cache = not nocache
            confidence = scoring_service.compute_confidence(
                product_data, shopping_count=len(self._shopping_items_cache), cached=from_cache
            )
            yield ("scores", {
                "scores": scoring_result.get("scores", {}),
                "dimension_winners": scoring_result.get("dimension_winners", {}),
                "winner_index": scoring_result.get("winner_index", 0),
                "win_margin": scoring_result.get("win_margin", 0),
                "confidence": confidence,
            })

            # Step 4: Generate verdict (passes demographics_profile so the cohort
            # priors block in extraction_service can render when conditions are met).
            yield ("status", {"message": "Generating verdict...", "progress": 80})
            t_verdict = time.perf_counter() if orchestrator_timings is not None else None
            comparison, usage = await generate_comparison(
                product_data[0], product_data[1], region,
                parsed.get("comparison_type", "value") if not vision_products else "value",
                user_preferences=user_preferences,
                scores_summary=scores_summary, category=detected_category,
                demographics_profile=demographics_profile,
            )
            if orchestrator_timings is not None:
                orchestrator_timings["verdict_ms"] = round((time.perf_counter() - t_verdict) * 1000, 1)
            self._track_gpt_cost(usage)

            # I3.1 — optional self-critique pass (flag-gated OFF; no-op in prod).
            # Same flow as the sync path; may regenerate the verdict ONCE.
            comparison = await self._apply_self_critique(
                comparison=comparison,
                product_names=product_names,
                regen_args=dict(
                    product1=product_data[0], product2=product_data[1], region=region,
                    concern=parsed.get("comparison_type", "value") if not vision_products else "value",
                    user_preferences=user_preferences, scores_summary=scores_summary,
                    category=detected_category, demographics_profile=demographics_profile,
                ),
                pain_workflow_context=scores_summary,
                stage_timings=orchestrator_timings,
            )

            from app.services.trust_validation_service import validate_verdict
            verdict_validation = validate_verdict(comparison, scoring_result, detected_category)

            if include_pros_cons:
                # Bundle C v1 hot-fix (round 2) § 1a diagnostic — streaming path
                logger.warning(
                    "PROS_POP_DIAGNOSTIC path=compare_from_text_streaming keys=%s "
                    "p0_pros_present=%s p1_pros_present=%s "
                    "p0_pros_type=%s p1_pros_type=%s "
                    "p0_pros_len=%s p1_pros_len=%s",
                    list(comparison.keys()),
                    "product_0_pros" in comparison,
                    "product_1_pros" in comparison,
                    type(comparison.get("product_0_pros")).__name__,
                    type(comparison.get("product_1_pros")).__name__,
                    len(comparison.get("product_0_pros") or []) if isinstance(comparison.get("product_0_pros"), list) else "non-list",
                    len(comparison.get("product_1_pros") or []) if isinstance(comparison.get("product_1_pros"), list) else "non-list",
                )
                product_data[0]["pros_cons"] = {
                    "pros": comparison.pop("product_0_pros", []),
                    "cons": comparison.pop("product_0_cons", []),
                }
                product_data[1]["pros_cons"] = {
                    "pros": comparison.pop("product_1_pros", []),
                    "cons": comparison.pop("product_1_cons", []),
                }

            # Compute value badges
            for i, product in enumerate(product_data):
                value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
                price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
                product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)

            # Compute tradeoffs
            tradeoffs = scoring_service.compute_tradeoff_pairs(
                scoring_result.get("dimension_winners", {}), product_names, scoring_result.get("winner_index", 0)
            )

            winner_index = comparison.get("winner_index", 0)
            win_margin = scoring_result.get("win_margin", 0)

            yield ("verdict", {
                "winner": {
                    "product_index": winner_index,
                    "name": comparison.get("winner_declaration", product_names[winner_index] if product_names else ""),
                    "reason": comparison.get("winner_reason", ""),
                    "key_tradeoff": comparison.get("key_tradeoff", ""),
                    "margin": win_margin,
                },
                "value_context": comparison.get("value_context", ""),
                "best_for": comparison.get("best_for", {}),
                "personalized_insights": comparison.get("personalized_insights", []),
                "comparison": comparison,
                "winner_index": winner_index,
                "recommendation": comparison.get("winner_reason", ""),
                "key_differences": [],
            })

            # Step 5: Build complete response
            elapsed = (datetime.now() - start_time).total_seconds()

            t_build = time.perf_counter() if orchestrator_timings is not None else None
            # L2.9 — source_trace pass-through for streaming path. Same
            # contract as the non-streaming compare_from_text_impl call site.
            _metadata_override: Dict[str, Any] = {}
            if getattr(self, "_source_trace", None):
                _metadata_override["source_trace"] = self._source_trace
            # I3.2 — thread the self-critique outcome (internal key) so the
            # post-save path can persist it once the comparison_id exists.
            # Present only when the flag is ON and a critique actually ran.
            _crit_meta = self._verdict_critique_metadata()
            if _crit_meta:
                _metadata_override["_verdict_critique"] = _crit_meta

            complete_response = build_comparison_response(
                product_data=product_data,
                comparison=comparison,
                scoring_result=scoring_result,
                product_names=product_names,
                tradeoffs=tradeoffs,
                confidence=confidence,
                verdict_validation=verdict_validation,
                user_preferences=user_preferences,
                from_cache=from_cache,
                query=query,
                region=region,
                category_used=category_used,
                category_switched=category_switched,
                original_category=original_category,
                total_cost=self.total_cost,
                api_calls=self.api_calls,
                gpt_calls=self.gpt_calls,
                serper_calls=self.serper_calls,
                elapsed_seconds=elapsed,
                metadata=_metadata_override or None,
            )
            if orchestrator_timings is not None:
                orchestrator_timings["response_build_ms"] = round((time.perf_counter() - t_build) * 1000, 1)
                orchestrator_timings["total_ms"] = round(
                    (datetime.now() - start_time).total_seconds() * 1000, 1
                )
                per_product = []
                for p in product_data:
                    t = p.pop("_stage_timings_ms", None)
                    if t:
                        per_product.append(t)
                orchestrator_timings["per_product"] = per_product
                complete_response.setdefault("metadata", {})["stage_timings_ms"] = orchestrator_timings

            # Mark cohort_injected on the complete response so route handler can
            # log a `cohort_injected` user_events row (powers vw_cohort_feedback_lift).
            if isinstance(complete_response.get("metadata"), dict):
                complete_response["metadata"]["cohort_injected"] = was_cohort_block_active(
                    demographics_profile
                )

            # Fire-and-forget: update behavioral profile (M6: tracked so
            # silent task failures surface as WARNING logs).
            if user_id:
                _fire_and_forget(
                    self._update_behavior_profile(user_id),
                    "behavior_profile_update",
                )

            # L3 output moderation (spec sec 5.2) — runs once before the
            # terminal events so a flagged response replaces the streamed
            # accumulator with a graceful refusal payload. Prior stream
            # events (specs/prices/reviews/scores/verdict) have already
            # reached the client; frontend treats `complete` with
            # success=false as the terminal refusal regardless of priors.
            # value_context is a per-product dict — flatten before joining
            # (see sync path comment above for the join-crash repro).
            _vc = comparison.get("value_context", "")
            if isinstance(_vc, dict):
                _vc = " ".join(str(v) for v in _vc.values() if v)
            _l3_text = " ".join(filter(None, [
                comparison.get("winner_declaration", ""),
                comparison.get("winner_reason", ""),
                comparison.get("key_tradeoff", ""),
                _vc,
                *product_names,
                *[
                    (h.get("text") if isinstance(h, dict) else str(h))
                    for pd in product_data
                    for h in (pd.get("reviews", {}) or {}).get("highlights", [])
                ][:10],
            ]))
            _l3 = await _safety.moderate_output(_l3_text)
            if not _l3.allowed:
                _fire_and_forget(
                    log_content_blocked(
                        layer="moderation_api",
                        query_hash=hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    ),
                    "log_content_blocked(moderation_api)",
                )
                refusal = {
                    "success": False,
                    "error": "We don't compare this category",
                    "code": "CONTENT_UNAVAILABLE",
                    "layer": "moderation_api",
                }
                yield ("settle_complete", refusal)
                yield ("complete", refusal)
                return

            # Bundle E Task 2.3 § Decision 8 — settle_complete closes the
            # settle window; no further settle_update events can fire
            # after this. Existing `complete` event is preserved
            # immediately after for backward-compat with current EAS
            # builds that listen on `complete`.
            yield ("settle_complete", complete_response)
            yield ("complete", complete_response)

        except Exception as e:
            logger.error(f"Streaming comparison error: {e}", exc_info=True)
            # I5.6 lever-2 — cancel the profile task if the failure happened
            # before it was awaited (mirror of the sync path).
            await _cancel_profile_task(_profile_task)
            yield ("error", {
                "success": False, "error": str(e), "total_cost": self.total_cost,
            })

    # ============================================
    # Internal orchestration methods
    # ============================================

    @staticmethod
    def _derive_cohort_profile(
        user_preferences: Optional[Dict[str, Any]],
        demographics_profile: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """S3 L3 v2 (c) — seed cohort-inferred preferences from the user's
        demographics so compute_scores can nudge the dimension weights toward the
        cohort (±10%). Returns None (→ pure category-weighted scoring) when the
        user has EXPLICIT preferences (those win, ±30%), when demographics are
        absent, or on any error (fail-soft — cohort scoring must never break a
        comparison)."""
        if user_preferences:  # explicit prefs win; cohort is the weak default
            return None
        if not demographics_profile:
            return None
        try:
            from app.services.cohort_service import get_cohort_service
            seeded = get_cohort_service().seed_preferences(demographics_profile)
            # Only return when the cohort actually produced priorities — an empty
            # priorities list is a no-op for the weighting.
            if seeded and seeded.get("priorities"):
                return seeded
        except Exception as exc:  # noqa: BLE001 — cohort scoring is best-effort
            logger.debug("cohort_profile derivation skipped: %s", exc)
        return None

    async def _fetch_behavior_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user's behavioral profile from Supabase."""
        try:
            from app.services.database_service import get_supabase_client
            supabase = get_supabase_client()
            result = supabase.table("users").select("behavior_profile").eq("id", user_id).single().execute()
            if result.data and result.data.get("behavior_profile"):
                return result.data["behavior_profile"]
        except Exception as e:
            logger.debug(f"Failed to fetch behavior profile: {e}")
        return None

    async def _update_behavior_profile(self, user_id: str):
        """Fire-and-forget: update user's behavioral profile after comparison."""
        try:
            from app.services.behavior_service import get_behavior_service
            from app.services.database_service import get_supabase_client

            behavior_service = get_behavior_service()
            supabase = get_supabase_client()

            comparisons = supabase.table("comparisons").select("category_used, products, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
            feedback = supabase.table("comparison_feedback").select("useful").eq("user_id", user_id).execute()
            events = supabase.table("user_events").select("event_type, metadata").eq("user_id", user_id).order("created_at", desc=True).limit(200).execute()

            profile = await behavior_service.build_behavior_profile(
                comparisons.data or [], feedback.data or [], events.data or [],
            )
            supabase.table("users").update({"behavior_profile": profile}).eq("id", user_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update behavior profile: {e}")

    async def _fetch_product_data(
        self, product_info: Dict, region: str, include_specs: bool, include_reviews: bool, nocache: bool = False
    ) -> Dict[str, Any]:
        """Fetch all data for a single product."""
        brand = product_info.get("brand", "")
        name = product_info.get("name", "")
        variant = product_info.get("variant")
        category = product_info.get("category", "other")
        search_query = product_info.get("search_query", f"{brand} {name} {variant or ''}")
        is_vision = product_info.get("_vision", False)

        if is_vision:
            full_name = search_query
            display_name = full_name
        else:
            full_name = f"{brand} {name} {variant or ''}".strip()
            display_name = name

        result = {
            "brand": brand, "name": display_name, "full_name": full_name,
            "variant": variant, "category": category, "query": search_query,
        }

        # Phase 2A.1 — per-product stage timings (only allocated when flag is on)
        stage_timings = {} if _debug_timings_enabled() else None

        # L2.6 — per-race timeout caps (moved above the unified search for I5.6
        # so the price race can start concurrently with the unified search; the
        # dict is a plain literal with no dependencies). Each race is wrapped in
        # asyncio.wait_for so a single slow tier (e.g., 15s Tier 1.5 fan-out for
        # price) cannot drag the whole Phase 1 wall over the
        # STREAM_HARD_CAP_SECONDS budget. On timeout the race result is None
        # (handled below as `result[key] = None`); response_builder treats None
        # as missing data and `_validate_renderable` decides whether to surface
        # an INSUFFICIENT_DATA error.
        _PHASE1_TIMEOUTS = {
            "specs": 8.0,     # GPT-4o-mini extraction
            # I5.7 (Bundle B S2, Decision D pre-authorized): price 18s→15s. This
            # OUTER cap wraps the whole _get_price path (Tier 1 + escalation
            # decision + the now-12s inner fan_out race + Tier 3 estimate).
            # S3 L1.3 (gate M2b): the pre-fan_out window now also runs the
            # Shopify /products.json discovery, capped at 3s (wait_for 3.0). That
            # fits inside the ~3s headroom above the 12s fan_out — and because a
            # failed/slow catalog is negative-cached (30min, M2a), the 3s tax is
            # a rare FIRST-COLD edge, not per-query; the fan_out's 2-source/rank
            # early-exit absorbs the ~2s it might lose on that one query. KEPT at
            # 15 (NOT raised to 18 — that would risk the 30s STREAM_HARD_CAP on
            # Phase-2 + verdict). The 3s Shopify wait_for cancels its own inner
            # gather on timeout, so nothing survives to be orphaned at the cap.
            "price": 15.0,    # Tier 1 + 1.5 cascade (inner fan_out race now 12s)
            "reviews": 10.0,  # Serper + GPT cleanup (measured 4-5s + headroom)
            "image_url": 5.0, # Serper Images + Tier 3 GPT fallback
        }

        # I5.6 (Bundle B S2) — start the price fetch CONCURRENTLY with the
        # unified search. _get_price runs its OWN search_product_prices +
        # Tier-1.5 cascade and has zero dependency on the unified-search result,
        # so kicking it off here (before the unified search is awaited) overlaps
        # the two walls instead of running them sequentially. Wrapped in the
        # same per-race wait_for cap + _timed_task as before; awaited below
        # inside the Phase-1 gather (added FIRST to phase1_tasks so the
        # result-key order is unchanged). Zero quality change — pure latency.
        _price_task = asyncio.ensure_future(asyncio.wait_for(
            _timed_task("price", self._get_price(brand, name, variant, region, search_query, nocache, category), stage_timings),
            timeout=_PHASE1_TIMEOUTS["price"],
        ))

        async def _cleanup_orphan_price_task() -> None:
            """L5.3 (S3) — cancel + drain the speculative lever-1 price task if it
            never made it into (or through) the Phase-1 gather. Between the
            ensure_future kickoff above and the gather there are await points (the
            unified search; the supplements drug lookup) where a raise OR an
            external cancel (e.g. the outer STREAM_HARD_CAP_SECONDS wait_for) would
            otherwise leave _price_task running in the background — its scrapers
            (Firecrawl / Scrape.do / curl) keep burning, result discarded. Mirrors
            the lever-2 profile-task cleanup. No-op once the gather has resolved it
            (the happy path), so zero behaviour change there."""
            if not _price_task.done():
                _price_task.cancel()
                try:
                    await _price_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass

        # I5.6 lever-1 orphan guard: any BaseException (incl. CancelledError)
        # raised in the window before/within the Phase-1 gather must not strand
        # the speculative price task. On the happy path _price_task is done by the
        # time the gather returns, so the cleanup is a no-op and the result/timing
        # path below is unchanged.
        try:
            # === Unified web search === (runs CONCURRENTLY with the price task
            # started above — I5.6: the price Serper round-trip is already in flight
            # via _price_task, so awaiting the unified search here overlaps the two
            # instead of running them sequentially. specs/reviews still consume the
            # resolved unified_search below.)
            unified_search = None
            if include_specs or include_reviews:
                specs_key = get_specs_cache_key(brand, name, variant)
                reviews_key = get_reviews_cache_key(brand, name, variant)
                specs_hit = get_cached(specs_key) if not nocache else None
                reviews_hit = get_cached(reviews_key) if not nocache else None
                if (include_specs and not specs_hit) or (include_reviews and not reviews_hit):
                    t0 = time.perf_counter() if stage_timings is not None else None
                    unified_search = await search_web(
                        f"{search_query} specifications reviews price", num_results=10
                    )
                    if stage_timings is not None:
                        stage_timings["unified_search_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                    self._track_serper_cost()

            if stage_timings is not None and "unified_search_ms" not in stage_timings:
                stage_timings["unified_search_ms"] = 0.0  # cache hit or skipped — no Serper call

            # === Phase 1: specs + price + reviews (parallel) ===
            # D2 Intervention 1: reviews moved from Phase 2 to Phase 1. _get_reviews
            # has no dependency on specs — it just needs unified_search +
            # retailer_ratings (which can be None; reviews skips snippet
            # enrichment in that case).
            phase1_tasks = []
            phase1_keys = []

            drug_context = ""
            if include_specs and category == "supplements":
                try:
                    drugs = await find_matching_drugs(search_query, limit=5)
                    drug_context = format_drug_context(drugs)
                    if drug_context:
                        logger.info(f"Drug DB: found {len(drugs)} matches for '{search_query}'")
                except Exception as e:
                    logger.warning(f"Drug DB lookup failed: {e}")

            # (_PHASE1_TIMEOUTS defined above the unified search for I5.6 — reviews
            # was bumped 6.0 → 10.0 in the post-ec2751b hotfix because the measured
            # post-D2 floor is 4-5s, per memory/feedback_measure_before_optimize.md.)

            if include_specs:
                phase1_tasks.append(asyncio.wait_for(
                    _timed_task("specs", self._get_specs(brand, name, variant, category, search_query, nocache, search_results=unified_search, drug_context=drug_context), stage_timings),
                    timeout=_PHASE1_TIMEOUTS["specs"],
                ))
                phase1_keys.append("specs")

            # I5.6 — price already started above (concurrent with the unified
            # search); add the running task here so its result-key position
            # (after specs) is unchanged. asyncio.gather awaits an already-running
            # task fine — it just collects the result.
            phase1_tasks.append(_price_task)
            phase1_keys.append("price")

            if include_reviews:
                # D2 Intervention 1: reviews moved from Phase 2 to Phase 1.
                # retailer_ratings is None here because shopping_items_cache is
                # populated DURING _get_price (Phase 1) so we can't pre-collect.
                # _get_reviews accepts None and skips retailer_ratings enrichment.
                phase1_tasks.append(asyncio.wait_for(
                    _timed_task("reviews", self._get_reviews(
                        brand, name, variant, search_query, nocache,
                        category=category, retailer_ratings=None,
                        search_results=unified_search,
                    ), stage_timings),
                    timeout=_PHASE1_TIMEOUTS["reviews"],
                ))
                phase1_keys.append("reviews")

            # Bundle E S3 — image_url resolution runs in parallel with specs+price
            # +reviews. Tier 1.5 piggyback happens AFTER Phase 1 returns (because
            # the page-scrape image, when present, lives inside the price result
            # which we don't have yet). Here we kick off Tier 1 (Serper Images) +
            # Tier 3 (GPT) eagerly; the post-Phase1 piggyback short-circuit will
            # override with the FREE result when available. Net: piggyback hit
            # path costs zero extra wall (we discard the eager Tier 1/3 result),
            # piggyback miss path saves zero wall too (Tier 1/3 already running).
            phase1_tasks.append(asyncio.wait_for(
                _timed_task("image_url", get_product_image_url(
                    full_name, region=region,
                    page_scrape_image=None,  # piggyback evaluated post-Phase1 below
                    organic_results=(unified_search.get("organic", []) if unified_search else None),
                ), stage_timings),
                timeout=_PHASE1_TIMEOUTS["image_url"],
            ))
            phase1_keys.append("image_url")

            t1 = time.perf_counter() if stage_timings is not None else None
            phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
        except BaseException:
            # L5.3 — orphan guard: a raise (e.g. unified search) or a cancel
            # (outer cap) in the pre-gather window, or a gather cancellation,
            # must not strand the speculative lever-1 price task. Cancel +
            # drain it, then re-raise so the caller's error/cancel semantics
            # are unchanged.
            await _cleanup_orphan_price_task()
            raise
        if stage_timings is not None:
            # phase1_wall_ms = gather wall (max of parallel tasks);
            # specs_ms / price_ms / reviews_ms / image_url_ms = per-task wall.
            stage_timings["phase1_wall_ms"] = round((time.perf_counter() - t1) * 1000, 1)
            for k in ("specs", "price", "reviews", "image_url"):
                stage_timings.setdefault(f"{k}_ms", 0.0)

        for i, key in enumerate(phase1_keys):
            if isinstance(phase1_results[i], asyncio.TimeoutError):
                # L2.6 — per-race timeout fired. Distinct WARNING (not ERROR)
                # because graceful degrade is the contracted behavior; the
                # missing field gets a None and downstream renderers + the
                # INSUFFICIENT_DATA validator decide whether the overall
                # comparison still ships.
                logger.warning(
                    "[L2.6] Phase 1 race timeout for %s (limit %.1fs)",
                    key, _PHASE1_TIMEOUTS.get(key, 0.0),
                )
                result[key] = None
            elif isinstance(phase1_results[i], Exception):
                logger.error(f"Error fetching {key}: {phase1_results[i]}")
                result[key] = None
            else:
                result[key] = phase1_results[i]

        # S3 L1.5 — record the real-vs-estimate price outcome for this product
        # (per-category /admin/costs gauge; the live counterpart to L4's eval
        # estimate-share). Fire-and-forget + fail-open; only counts when a price
        # was actually produced (None price = race timeout/error, not an
        # estimate decision, so it's excluded from the ratio).
        try:
            _settled_price = result.get("price")
            if isinstance(_settled_price, dict) and _settled_price.get("amount"):
                record_price_outcome(category, _settled_price.get("source_method"))
        except Exception:  # noqa: BLE001 — metric must never break the response
            pass

        # L2.9 — emit a per-product source_trace record into the orchestrator
        # collector. Tier names are the labels the renderer surfaces; in the
        # absence of full per-tier hit/miss info we collapse to "race-fired
        # / race-yielded" pairs derived from result presence.
        try:
            tracker = getattr(self, "_source_trace", None)
            if tracker is not None:
                product_key = f"product_{len(tracker.get('products', []))}"
                per_product = {
                    "name": full_name,
                    "races": {},
                }
                for k in ("specs", "price", "reviews", "image_url"):
                    if k in phase1_keys:
                        wall_ms = 0
                        if stage_timings is not None:
                            wall_ms = int(stage_timings.get(f"{k}_ms", 0) or 0)
                        race_entry = {
                            "sources_tried": [k],
                            "sources_returned_value": ([k] if result.get(k) else []),
                            "wall_ms": wall_ms,
                        }
                        # F1.4 — annotate the price race with the Tier 1.5
                        # routing path (registry / legacy_fallback / official /
                        # tier1_5) + the registry source_weight, when an
                        # escalation candidate won the fan_out race for this
                        # product. Absent on Tier-1-only / estimated prices.
                        if k == "price":
                            route_rec = self._tier15_routes.get(full_name)
                            if route_rec:
                                race_entry["route"] = route_rec["route"]
                                race_entry["source_weight"] = route_rec["source_weight"]
                        per_product["races"][k if k != "image_url" else "image"] = race_entry
                tracker.setdefault("products", []).append(per_product)
        except Exception as e:
            logger.warning("[L2.9] source_trace record failed: %s", e)

        if result.get("price"):
            result["best_price"] = result["price"].get("amount")
            result["currency"] = result["price"].get("currency", "BHD")
            result["retailer"] = result["price"].get("retailer")
            # Bundle E S3 — Tier 1.5 piggyback override. If the price tier
            # already scraped a real product page and the page yielded an
            # og:image / JSON-LD image, prefer that over the Serper Images
            # / GPT result we kicked off in parallel. Page-scrape images
            # are FREE (already paid by the price scrape) AND usually
            # higher fidelity (real product hero shot vs Serper thumbnail).
            page_img = result["price"].get("image_url")
            if page_img and isinstance(page_img, str) and (
                page_img.startswith("http://") or page_img.startswith("https://")
            ):
                result["image_url"] = page_img.strip()

        # Fact-check: verify spec citations
        if result.get("specs") and isinstance(result["specs"], dict):
            raw_specs = result["specs"]
            search_snippets = raw_specs.pop("_search_snippets", [])
            citation_confidence = verify_spec_citations(raw_specs, search_snippets)
            shopping_items = self._shopping_items_cache.get(full_name, [])
            shopping_flags = cross_validate_specs_with_shopping(raw_specs, shopping_items)
            spec_confidence = {}
            for key in citation_confidence:
                if shopping_flags.get(key) == "verified":
                    spec_confidence[key] = "verified"
                else:
                    spec_confidence[key] = citation_confidence[key]
            result["_spec_confidence"] = spec_confidence

        if result.get("specs"):
            result["specs"] = self._clean_specs(result["specs"])

        # === Phase 2: verified rating + smart-fallback for missing critical specs ===
        # D2 Intervention 1: reviews moved to Phase 1. retailer_ratings is still
        # collected here (after Phase 1 populated shopping_items_cache via
        # _get_price) for downstream verify_review_sentiment + fact-check use.
        retailer_ratings = collect_retailer_ratings(full_name, self._shopping_items_cache)

        phase2_tasks = []
        phase2_keys = []

        # D2 Intervention 1: reviews moved to Phase 1. Phase 2 now only runs
        # verified rating + smart-fallback (Bucket A bug 3c) in parallel.
        # I5.6 lever-3 — cap the rating race at 4s. Previously UNCAPPED, unlike
        # its Phase-2 sibling _smart_fallback_extract (5s wait_for), so a slow
        # rating cascade (cold Serper Tier 1→2→3 + GPT fallback) could drag the
        # whole Phase-2 gather wall past budget. On timeout we return the benign
        # default rating dict (same shape as the rating_data default at the result
        # loop) — the existing loop then treats it as "no verified rating" and the
        # GPT-review-aggregate fallback (below) owns the value. Logged at info, not
        # error: a rating timeout is an expected graceful-degrade, not a failure.
        async def _rating_with_cap():
            try:
                return await asyncio.wait_for(
                    self._get_verified_rating(full_name),
                    timeout=_PHASE2_RATING_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.info(
                    "[RATING] cap %.1fs hit for %r — falling back to default "
                    "(GPT-review-aggregate path owns the rating)",
                    _PHASE2_RATING_TIMEOUT, full_name,
                )
                return {"rating": None, "review_count": None,
                        "rating_verified": False, "rating_source": None}

        phase2_tasks.append(_timed_task("rating", _rating_with_cap(), stage_timings))
        phase2_keys.append("_rating_data")

        # Smart-fallback (Bucket A bug 3c): identify critical schema fields still
        # missing after primary extraction. Run a targeted Serper + small GPT
        # extract in parallel with Phase 2; max 6 fields per product, 5s cap.
        # D2 post-deploy tuning: bumped from [:2]/3s to [:6]/5s — Phase 2 wall
        # budget freed up after Intervention 1 moved reviews to Phase 1 (was
        # tight at 3s when reviews ran here too). [:6] covers electronics's
        # max critical-field count; live bench showed iPhone 17 occasionally
        # had 3 of 6 critical fields needing fill-in but the old [:2] cap
        # silently dropped the 3rd, producing flaky test_post_d2_per_category_
        # critical_fields_intact failures.
        from app.services.extraction_service import CRITICAL_SCHEMA_FIELDS
        critical_fields = CRITICAL_SCHEMA_FIELDS.get(category, [])
        specs_so_far = result.get("specs") or {}
        missing_critical = [
            f for f in critical_fields
            if specs_so_far.get(f) in (None, "", "N/A")
        ][:6]
        fallback_added = False
        if missing_critical:
            phase2_tasks.append(_timed_task("smart_fallback", self._smart_fallback_extract(
                brand, name, variant, category, missing_critical,
            ), stage_timings))
            phase2_keys.append("_smart_fallback")
            fallback_added = True

        t2 = time.perf_counter() if stage_timings is not None else None
        phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
        if stage_timings is not None:
            # phase2_wall_ms = gather wall (max of parallel tasks);
            # rating_ms / smart_fallback_ms = per-task wall (populated by _timed_task).
            stage_timings["phase2_wall_ms"] = round((time.perf_counter() - t2) * 1000, 1)
            stage_timings.setdefault("rating_ms", 0.0)
            if "_smart_fallback" in phase2_keys:
                stage_timings.setdefault("smart_fallback_ms", 0.0)

        # Apply smart-fallback results before the regular Phase 2 result loop,
        # so the rest of the function sees the fully-populated specs dict.
        # Live-bench hotfix: filter out fallback values that are themselves
        # literal "N/A" - GPT sometimes echoes the placeholder back instead
        # of returning null, which would noop-overwrite and stamp the wrong
        # _field_confidence marker. Treat "N/A" as no-knowledge from fallback.
        if fallback_added:
            fb_idx = phase2_keys.index("_smart_fallback")
            fb_result = phase2_results[fb_idx]
            if not isinstance(fb_result, Exception) and fb_result:
                result_specs = result.get("specs") or {}
                fc = result_specs.setdefault("_field_confidence", {})
                for field, value in fb_result.items():
                    if not value or value == "N/A":
                        continue
                    existing = result_specs.get(field)
                    if existing in (None, "", "N/A"):
                        result_specs[field] = value
                        fc[field] = "smart_fallback"
                result["specs"] = result_specs

        # Bundle C § 2f A.4.7 — Tier 2 fallback. Fires ONLY when Tier 1 +
        # smart-fallback left non-negotiable schema fields blank. 4s outer
        # wall cap (tier2_fill_non_negotiables handles per-field parallelism).
        # Stays inside STREAM_HARD_CAP_SECONDS=25 because Tier 2 fires only
        # when there's a real gap (most happy-path comparisons skip it
        # entirely — zero added wall).
        result_specs_now = result.get("specs") or {}
        t_tier2 = time.perf_counter() if stage_timings is not None else None
        tier2_filled = await tier2_fill_non_negotiables(
            brand=brand, name=name, variant=variant,
            category=category, specs_so_far=result_specs_now,
        )
        if stage_timings is not None:
            stage_timings["tier2_fallback_ms"] = round(
                (time.perf_counter() - t_tier2) * 1000, 1
            )
        if tier2_filled:
            fc = result_specs_now.setdefault("_field_confidence", {})
            for field, value in tier2_filled.items():
                existing = result_specs_now.get(field)
                if existing in (None, "", "N/A"):
                    result_specs_now[field] = value
                    fc[field] = "tier2_fallback"
            result["specs"] = result_specs_now

        # Bundle D A.4.8 — Tier 3 batched GPT-4o synthesis. Fires ONLY when
        # non-negotiable schema fields STILL blank after Tier 2. Single
        # gpt-4o call per product (vs Tier 2's per-field mini fan-out).
        # 3s outer wall cap. Skips entirely when nothing's missing — happy
        # path adds zero wall.
        t_tier3 = time.perf_counter() if stage_timings is not None else None
        tier3_filled = await tier3_synthesize_non_negotiables(
            brand=brand, name=name, variant=variant,
            category=category, specs_so_far=result_specs_now,
        )
        if stage_timings is not None:
            stage_timings["tier3_synth_ms"] = round(
                (time.perf_counter() - t_tier3) * 1000, 1
            )
        if tier3_filled:
            fc = result_specs_now.setdefault("_field_confidence", {})
            for field, value in tier3_filled.items():
                existing = result_specs_now.get(field)
                if existing in (None, "", "N/A"):
                    result_specs_now[field] = value
                    fc[field] = "tier3_synthesis"
            result["specs"] = result_specs_now

        rating_data = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}
        for i, key in enumerate(phase2_keys):
            if key == "_smart_fallback":
                continue  # Handled in the smart-fallback merge block above
            if isinstance(phase2_results[i], Exception):
                logger.error(f"Error fetching {key}: {phase2_results[i]}")
                continue
            if key == "_rating_data":
                rating_data = phase2_results[i]

        result["rating"] = rating_data.get("rating")
        result["review_count"] = rating_data.get("review_count")
        result["rating_verified"] = rating_data.get("rating_verified", False)
        result["rating_source"] = rating_data.get("rating_source")

        # Fallback: use GPT-extracted average_rating
        if result["rating"] is None and result.get("reviews") and isinstance(result["reviews"], dict):
            avg = result["reviews"].get("average_rating")
            if avg is not None:
                try:
                    avg_float = round(float(avg), 1)
                    if 1.0 <= avg_float <= 5.0:
                        result["rating"] = avg_float
                        result["review_count"] = result["reviews"].get("total_reviews")
                        result["rating_verified"] = False
                        result["rating_source"] = {
                            "name": "Aggregated from reviews", "url": None,
                            "extract_method": "gpt_review_aggregate", "confidence": "low",
                        }
                except (ValueError, TypeError):
                    pass

        # Inject verified rating into reviews
        if result.get("reviews") and isinstance(result["reviews"], dict) and rating_data.get("rating"):
            result["reviews"]["verified_rating"] = {
                "rating": rating_data["rating"],
                "review_count": rating_data.get("review_count"),
                "source": rating_data.get("rating_source", {}).get("name"),
                "verified": rating_data.get("rating_verified", False),
            }

        if rating_data.get("expert_pros"):
            result["expert_pros"] = rating_data["expert_pros"]
        if rating_data.get("expert_cons"):
            result["expert_cons"] = rating_data["expert_cons"]

        # === Fact-checking ===
        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["_review_verification"] = verify_review_sentiment(result["reviews"], retailer_ratings)
        else:
            result["_review_verification"] = {"sentiment_consistent": None, "gpt_rating": None, "serper_avg_rating": None, "deviation": None}

        shopping_items = self._shopping_items_cache.get(full_name, [])
        result["_price_verification"] = verify_price(result.get("price"), shopping_items)

        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["reviews"] = clean_review_content(result["reviews"])

        if result.get("reviews") and isinstance(result["reviews"], dict):
            result["reviews"] = clean_review_citations(
                result["reviews"],
                unified_search.get("organic", []) if unified_search else []
            )

        result["fact_check"] = build_fact_check(result)
        result["data_freshness"] = self._calculate_freshness(result)

        if stage_timings is not None:
            result["_stage_timings_ms"] = stage_timings

        return result

    async def _get_specs(
        self, brand: str, name: str, variant: Optional[str], category: str,
        search_query: str, nocache: bool = False, search_results: Optional[Dict] = None, drug_context: str = ""
    ) -> Dict[str, Any]:
        """Get specs with caching (L1: Redis, L2: DB)."""
        cache_key = get_specs_cache_key(brand, name, variant)
        cached = get_cached(cache_key) if not nocache else None
        if cached:
            cached["_cached"] = True
            return cached

        # L2: Check DB before API call
        if not nocache:
            from app.services.product_data_service import get_cached_specs
            db_specs = await get_cached_specs(cache_key)
            if db_specs:
                set_cached(cache_key, db_specs, SPECS_CACHE_TTL)
                db_specs["_cached"] = True
                db_specs["_cache_source"] = "db"
                return db_specs

        if search_results is None:
            search_results = await search_web(f"{search_query} specifications features")
            self._track_serper_cost()

        search_context, raw_snippets = self._format_numbered_search_results(search_results)
        specs, usage = await extract_specs(brand, name, variant, category, search_context, drug_context=drug_context)
        self._track_gpt_cost(usage)

        if specs and not specs.get("error"):
            set_cached(cache_key, specs, SPECS_CACHE_TTL)
            # Save to L2 DB (fire-and-forget — B0-B Item 4: wrapped per
            # audit convention 2026-05-22 so DB write exceptions WARNING-log
            # instead of silently disappearing).
            from app.services.product_data_service import save_specs
            _fire_and_forget(
                save_specs(cache_key, brand, name, variant, category, specs),
                label="save_specs",
            )

        specs["_search_snippets"] = raw_snippets
        specs["_cached"] = False
        return specs

    async def _get_price(
        self, brand: str, name: str, variant: Optional[str], region: str,
        search_query: str, nocache: bool = False, category: str = "other"
    ) -> Dict[str, Any]:
        """Get price with 3-tier strategy."""
        if not validate_price_query(brand, name, region):
            return {"amount": 0, "currency": "BHD", "estimated": True, "source_method": "validation_rejected"}

        cache_key = get_price_cache_key(brand, name, variant, region)
        # I5.1 — price-only cache-bust probe forces the price reads to miss so
        # the routing escalation re-runs deterministically (specs/reviews stay
        # warm — they gate on `nocache` in _fetch_product_data, not this flag).
        price_nocache = nocache or _price_cache_bust_enabled()
        cached = get_cached(cache_key) if not price_nocache else None
        if cached:
            cached["_cached"] = True
            return cached

        # L2: Check DB before tier cascade
        if not price_nocache:
            from app.services.product_data_service import get_cached_price
            db_price = await get_cached_price(cache_key, region)
            if db_price:
                set_cached(cache_key, db_price, PRICE_CACHE_TTL)
                db_price["_cached"] = True
                db_price["_cache_source"] = "db"
                return db_price

        region_info = GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])
        currency = region_info["currency"]
        if variant and variant.lower() in name.lower():
            full_name = f"{brand} {name}".strip()
        else:
            full_name = f"{brand} {name} {variant or ''}".strip()

        is_supplement = (category == "supplements") or is_supplement_query(full_name)

        # --- Tier 1: Direct Serper Shopping extraction ---
        shopping_region = None  # T2 — gl region the shopping items came from
        if is_supplement:
            search_results = {"shopping": [], "organic": []}
            shopping_items = []
            self._shopping_items_cache[full_name] = []
        else:
            search_results = await search_product_prices(search_query, region_info["code"])
            self._track_serper_cost()
            shopping_items = search_results.get("shopping", [])
            self._shopping_items_cache[full_name] = shopping_items
            # Bundle C v1 hot-fix — always-on log of gl=us fallback activity.
            # Helps Ahmed/qa see in Railway logs WHY non-supplement queries
            # still hit estimated despite the A.3.3-fix-2 gl=us fallback.
            # Lightweight (1 line per product, INFO level) — no flag gate.
            shopping_region = search_results.get("shopping_region", "unknown")
            logger.info(
                f"[GL_FALLBACK_TRACE] query={search_query!r} "
                f"region={region_info['code']} shopping_region={shopping_region} "
                f"items={len(shopping_items)} category={category}"
            )

        tier3_estimate = None
        # S3-genuine (Approach A, team-lead-approved 2026-06-14) — a CONVERTED_USD
        # Tier-1 price is PARKED here, not returned, so the genuine-BH curl tier
        # (Tier-1.5) runs and can WIN. §5 ordering: genuine-BH (tier 1-5) beats
        # converted_usd (tier-7). The parked converted price is the fallback ONLY
        # after BH curl+render miss (before the GPT estimate). A GENUINE Tier-1
        # price (local_bhd / page_scrape) still short-circuits below.
        converted_fallback = None

        price = extract_price_from_shopping(
            full_name, shopping_items, currency, shopping_region=shopping_region
        )
        if price and price.get("amount"):
            if price.get("retailer_score", 0) >= 1.0:
                pass  # Official domain — skip sanity check
            elif is_high_value_query(full_name) and price.get("retailer_score", 0) < 1.0:
                # S3-reopen T1 (team-lead Decision-F 2026-06-14) — the GPT
                # estimate is the judge of NOTHING. The old code fetched the GPT
                # training guess and NULLED this real Tier-1 price when it merely
                # deviated from the guess (then the cascade fell to that same
                # guess — a real price thrown away for an estimate). Now the gate
                # is ABSOLUTE category plausibility: a plausible Tier-1 price is
                # KEPT (a wrong guess is exactly why we don't let it veto a cited
                # price); only a grossly-implausible amount (a mis-extracted
                # installment / accessory / currency error) is dropped — and
                # dropping it falls through to the BH scrape cascade, never
                # promotes it. No estimate is fetched here just to veto.
                if not is_price_plausible(_convert_to_bhd(price["amount"], currency), category):
                    price = None
            if price and price.get("amount"):
                price.pop("retailer_score", None)
                # Approach A — PARK a CONVERTED_USD Tier-1 price; defer to the
                # genuine-BH Tier-1.5 curl tier below. A genuine Tier-1 price
                # (local_bhd / page_scrape / any non-converted) short-circuits now.
                if price.get("source_method") == "converted_usd":
                    converted_fallback = dict(price)
                else:
                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                    self._save_price_to_db(cache_key, brand, name, variant, region, price)
                    price["_cached"] = False
                    return price

        # --- Tier 1.5: Page scraping cascade (confidence-driven, all categories) ---
        # L2.5 — replaced the legacy is_luxury_brand() gate with
        # _should_escalate_price_scrape(), which fires for any category
        # whenever Tier 1 confidence is low (no source, single weak source,
        # disagreement, or >40% deviation from training estimate). Tom Ford
        # still escalates; Xiaomi 14 with a bogus 20-BHD Tier-1 result now
        # also escalates instead of being blocked by the luxury gate.
        # Bundle E § Decision 8 — scatter-gather refactor. The 3 Serper
        # discovery queries (official → authorized → GCC retailers) run in
        # PARALLEL via asyncio.gather; the per-URL page-scrape attempts are
        # then RACED via fan_out_price_lookup, bounded by asyncio.wait_for(15s).
        tier1_sources: List[Dict[str, Any]] = []
        if price and price.get("amount"):
            tier1_sources.append({
                "src": price.get("source_method") or "serper_shopping",
                "amount": float(price["amount"]),
                "retailer_score": float(price.get("retailer_score") or 0.0),
            })

        if ENABLE_PAGE_SCRAPE and _should_escalate_price_scrape(
            tier1_sources,
            training_estimate=(
                float(tier3_estimate["amount"])
                if tier3_estimate and tier3_estimate.get("amount")
                else None
            ),
            brand=brand,
        ):
            scraping_mode = os.environ.get("SCRAPING_MODE", "hard")
            candidate_urls: List[Tuple[str, str]] = []

            # official_domain is needed by BOTH the Shopify authority gate (S3)
            # and the discovery below — compute it once, up front.
            official_domain = get_official_domain(full_name)

            # --- S3 L1.3: Shopify direct-discovery (FREE, real BHD) ---
            # The major BH retailers are JS-SPAs whose prices aren't in static
            # curl HTML (L1_DIAGNOSTIC_bh_scrapeability.md), but Shopify-platform
            # BH stores expose a static /products.json catalog with real BHD
            # prices — hit it DIRECTLY (zero Serper, zero render credits).
            #
            # S3 gate (authority): a Shopify hit SHORT-CIRCUITS only when its
            # domain IS the official/authoritative brand domain. The registry's
            # Shopify stores (asgharali, almoayyed) are RESELLERS — a reseller
            # hit must NOT pre-empt the official-brand discovery, and must not
            # auto-win on lowest price. So a reseller hit is parked as a
            # `shopify_fallback` and the normal discovery + ranked fan_out runs;
            # the fallback is only used if the fan_out yields nothing (a real BH
            # price still beats a GPT estimate).
            #
            # M2b gate (latency): the fetch is capped at 3s (was 8s) so it can
            # never push the pre-fan_out budget past the 15s _price_task cap's
            # ~3s headroom. M2a's negative-cache bounds a cold/dead store to
            # 1-2 fetches per domain / 30min, so the 3s tax is a rare first-cold
            # edge the fan_out's early-exit absorbs. The 3s wait_for cancels its
            # inner gather on timeout (self-contained — completes well before the
            # outer 15s cap, so no orphaned Shopify task survives L5's cancel).
            shopify_fallback = None
            shopify_sources = get_shopify_sources_for_category(category)
            if shopify_sources:
                try:
                    shop_results = await asyncio.wait_for(
                        asyncio.gather(
                            *(
                                fetch_shopify_price(s.domain, full_name, currency)
                                for s in shopify_sources
                            ),
                            return_exceptions=True,
                        ),
                        timeout=3.0,
                    )
                except asyncio.TimeoutError:
                    shop_results = []
                except Exception as e:  # noqa: BLE001 — discovery is best-effort
                    logger.warning(f"[PRICE] Shopify discovery failed: {e}")
                    shop_results = []

                # Lowest valid BHD among the trusted Shopify set (the product's
                # actual in-catalog price). NOTE: "lowest" here is only WITHIN
                # the Shopify set; S3 ensures it never out-ranks the official
                # brand below.
                shop_best = None
                for r in shop_results:
                    if isinstance(r, dict) and r.get("amount") and r["amount"] > 0:
                        if shop_best is None or r["amount"] < shop_best["amount"]:
                            shop_best = r
                if shop_best:
                    shop_best["source_method"] = shop_best.get(
                        "source_method", "shopify_json"
                    )
                    win_domain = str(
                        shop_best.get("retailer") or ""
                    ).replace("www.", "").lower()
                    off = (official_domain or "").replace("www.", "").lower()
                    is_official_shopify = bool(off) and (
                        win_domain == off or win_domain.endswith("." + off)
                        or off.endswith("." + win_domain)
                    )
                    if is_official_shopify:
                        # Authoritative (official brand store) → short-circuit.
                        self._tier15_routes[full_name] = {
                            "route": "shopify_direct",
                            "source_weight": score_source(
                                shop_best.get("url", "") or f"https://{win_domain}",
                                category,
                            ),
                        }
                        record_tier15_attempt(category)
                        record_tier15_hit(category, win_domain or None)
                        set_cached(cache_key, shop_best, PRICE_CACHE_TTL)
                        self._save_price_to_db(
                            cache_key, brand, name, variant, region, shop_best
                        )
                        shop_best["_cached"] = False
                        logger.info(
                            "[PRICE] Shopify OFFICIAL-domain hit for %s: %.3f %s "
                            "via %s (zero Serper/render)",
                            full_name, shop_best["amount"], currency, win_domain,
                        )
                        return shop_best
                    # Reseller hit → park as fallback; let discovery+fan_out run.
                    shopify_fallback = shop_best
                    logger.info(
                        "[PRICE] Shopify reseller hit for %s parked as fallback: "
                        "%.3f %s via %s (ranked discovery still runs)",
                        full_name, shop_best["amount"], currency, win_domain,
                    )

            # --- Discovery: all queries fire concurrently ---
            # B.0 (Lane F1): a Bahrain-first `site:` discovery query leads the
            # cascade for non-luxury escalations, so Lulu/Sharaf DG/Carrefour BH
            # listings outrank a distant amazon.com result. Counterfeit safety
            # preserved: even with `site:louisvuitton.com`, Serper sometimes
            # returns off-domain marketplace links — every candidate is gated
            # post-fetch (registry-first `score_source >= 1.5`, legacy whitelist
            # fallback) before entering the pool. Dispatcher invariant #1.
            # (official_domain computed above for the S3 Shopify authority gate.)
            # I5.5 (Bundle B S2) — category-aware authorized/gcc discovery.
            # These were hard-coded FASHION/luxury strings (farfetch/ssense/
            # net-a-porter + ounass/bloomingdales/namshi) sent for EVERY
            # category — nonsense for an AC. Build them from the registry per
            # category instead: an AC now looks at noon/amazon.ae/sharafdg
            # (gcc electronics) + brand officials (global tier), while fashion
            # still gets ounass/bloomingdales/tryano (its own gcc tier).
            # Counterfeit safety unchanged — every candidate is still gated
            # post-fetch by score_source >= 1.5. Defensive fallback to the bare
            # product name keeps the discovery slot non-empty for any category
            # with no sources in a tier (noon/amazon.ae are all-category, so in
            # practice both tiers are always non-empty).
            retailer_query = build_site_discovery_query(
                full_name, category, tier="global", limit=8
            ) or full_name
            gcc_query = build_site_discovery_query(
                full_name, category, tier="gcc", limit=8
            ) or full_name

            discovery_tasks = []
            # Bahrain registry discovery FIRST (gated by has_budget("serper")
            # implicitly — search_web no-ops without a key). Skipped only when
            # the category has zero Bahrain-tier registry sources.
            # I5.4 (Bundle B S2) — limit=8 (was 4) so the whole live
            # bahrain-electronics registry is queryable in this single Serper
            # call. After I5.3's dead-domain purge there are 6 live electronics
            # rows; limit=4 sliced off shopalmoayyed.com (index 5, the F1.5
            # appliance/AC JSON-LD source) — the electronics 0/14 starvation.
            # Same one Serper call, just a longer `site:a OR site:b ...` chain.
            bahrain_query = build_site_discovery_query(
                full_name, category, tier="bahrain", limit=8
            )
            if bahrain_query:
                discovery_tasks.append(("bahrain", search_web(bahrain_query)))
            if official_domain:
                discovery_tasks.append(
                    ("official", search_web(f"{full_name} site:{official_domain}"))
                )
            discovery_tasks.append(("authorized", search_web(retailer_query)))
            discovery_tasks.append(("gcc", search_web(gcc_query)))

            results_by_tier = {}
            try:
                gathered = await asyncio.gather(
                    *(coro for _, coro in discovery_tasks),
                    return_exceptions=True,
                )
                for (tier_name, _), result in zip(discovery_tasks, gathered):
                    if isinstance(result, Exception):
                        logger.warning(f"[PRICE] Tier 1.5 {tier_name}-discovery failed: {result}")
                        continue
                    self.api_calls += 1
                    self._track_cost_amount(0.001)
                    results_by_tier[tier_name] = result
            except Exception as e:
                # gather itself failed (very unlikely with return_exceptions=True)
                logger.warning(f"[PRICE] Tier 1.5 parallel discovery failed: {e}")

            # Build candidate_urls in priority order:
            # bahrain (registry) → official → authorized → gcc.
            # Registry-first gate with legacy-whitelist fallback lives in
            # _harvest_candidate_urls; `harvested` carries route + source_weight
            # for the source_trace record (F1.4).
            harvested = _harvest_candidate_urls(
                results_by_tier, official_domain, category
            )
            candidate_urls = [(link, label) for link, label, _route, _w in harvested]

            # S3-genuine — the curl-SEARCH-URL injector (build_direct_bh_candidates)
            # was REMOVED 2026-06-14. Team-lead live probe (WRINKLE 2) + our own
            # captures: the BH retailers' SEARCH pages are JS-rendered (gcc.lulu
            # /en-bh/search/?q= → 404; sharafdg ?s= → 0 JSON-LD/itemprop, PDP links
            # are noise). So a curl-only search→PDP path can't reach the PDPs.
            # PDP DISCOVERY for these non-Shopify retailers is the Serper `site:`
            # query above (locale-filtered to BH); the genuine BH price is then
            # produced by the curl wave below curling the discovered PDP + the
            # JSON-LD/microdata/OG extractor. Serper-independence = Shopify
            # /products.json (works) + a future Firecrawl-render-search (deferred,
            # budget-gated per Ahmed).

            # --- Race: fan_out_price_lookup runs all per-URL scrapers in
            # parallel, cancels pending tasks when 2 sources confirm within
            # 5% (or rank≥85 lands), returns the highest-ranked candidate.
            # Bounded by asyncio.wait_for(timeout=12s) — Cloudflare-protected
            # scrapes (e.g. ssense.com via Scrape.do) can blow 20+s and have
            # to fall through to Tier 2 to honor the per-product wall budget.
            # I5.7 (Bundle B S2, Decision D pre-authorized): tightened 15s→12s.
            # The race already early-exits on 2-source-confirm / rank≥85, so the
            # cap only bites the slow-scraper tail; trimming 3s off that tail is
            # pure wall improvement. Escalation TRIGGERING
            # (_should_escalate_price_scrape above) is UNCHANGED. ---
            if candidate_urls:
                # F1.6 — count one Tier 1.5 escalation attempt (fail-open).
                record_tier15_attempt(category)

                def _finalize_fan_winner(fan_result):
                    """Stamp + route-record + cache a fan_out winner; returns the
                    winning_price dict or None. Shared by the curl + render waves."""
                    best = fan_result.get("best")
                    if not (best and best.get("raw_data") and best["raw_data"].get("amount")):
                        return None
                    winning_price = best["raw_data"]
                    winning_price["source_method"] = best.get("source_method", "page_scrape")
                    win_domain = str(winning_price.get("retailer") or "").replace("www.", "").lower()
                    for _link, _label, _route, _weight in harvested:
                        if _label.lower() == win_domain or win_domain.endswith("." + _label.lower()) or _label.lower().endswith("." + win_domain):
                            self._tier15_routes[full_name] = {"route": _route, "source_weight": _weight}
                            break
                    else:
                        self._tier15_routes[full_name] = {
                            "route": "tier1_5",
                            "source_weight": score_source(
                                winning_price.get("url", "") or f"https://{win_domain}", category
                            ),
                        }
                    record_tier15_hit(category, win_domain or None)
                    set_cached(cache_key, winning_price, PRICE_CACHE_TTL)
                    self._save_price_to_db(cache_key, brand, name, variant, region, winning_price)
                    winning_price["_cached"] = False
                    if fan_result.get("cancelled_count", 0) > 0:
                        logger.info(
                            "[PRICE] fan_out cancelled %d pending scrapers after confirmation (elapsed=%.2fs)",
                            fan_result["cancelled_count"], fan_result.get("elapsed_seconds", 0.0),
                        )
                    return winning_price

                # S3-genuine Approach A part 2 — TWO-WAVE budget split. Run the
                # FREE curl wave FIRST (early-exit on a plausible genuine price);
                # the paid Firecrawl/Scrape.do RENDER wave fires ONLY if the curl
                # wave misses (Ahmed: render not fired every escalation). This
                # also trims wall — most BH PDPs (sharafdg/extra/gcc.lulu/microless)
                # are curl-extractable, so the render wave rarely runs.
                #
                # I5.7 wall-cap invariant preserved: the TWO waves SHARE a single
                # 12s deadline (curl gets up to 12s; render gets the REMAINDER),
                # so the total Tier-1.5 scrape time stays <= the 12s the single
                # fan_out had — it never exceeds the 15s outer _PHASE1_TIMEOUTS
                # ["price"] cap.
                _FAN_OUT_BUDGET = 12.0
                _t15_start = time.monotonic()
                for _wave in ("curl", "render"):
                    _remaining = _FAN_OUT_BUDGET - (time.monotonic() - _t15_start)
                    if _remaining <= 0.5:
                        break  # shared 12s budget spent — fall through to Tier 2
                    _scrapers = _build_escalation_scrapers(
                        candidate_urls=candidate_urls,
                        full_name=full_name,
                        currency=currency,
                        scraping_mode=scraping_mode,
                        wave=_wave,
                    )
                    if not _scrapers:
                        continue  # render wave empty when no URL needs render
                    try:
                        _fan = await asyncio.wait_for(
                            fan_out_price_lookup(
                                product={"full_name": full_name, "brand": brand},
                                scrapers=_scrapers,
                                scraping_mode=scraping_mode,
                            ),
                            timeout=_remaining,
                        )
                    except asyncio.TimeoutError:
                        logger.info(
                            "[PRICE] Tier 1.5 %s-wave hit the shared 12s budget for "
                            "%s; %s", _wave, full_name,
                            "trying render wave" if _wave == "curl" else "falling through to Tier 2",
                        )
                        continue
                    except Exception as e:  # noqa: BLE001
                        logger.warning(f"[PRICE] Tier 1.5 {_wave}-wave failed: {e}")
                        continue
                    _winner = _finalize_fan_winner(_fan)
                    if _winner is not None:
                        # Curl-wave win → genuine BH price, no render credits burned.
                        return _winner

            # S3 — the ranked discovery/fan_out yielded nothing. A parked
            # reseller Shopify hit (real BH price) is a better answer than a GPT
            # estimate, so use it as the fallback now (it did NOT pre-empt the
            # official-brand ranking — that already ran above and came up empty).
            if shopify_fallback:
                win_domain = str(
                    shopify_fallback.get("retailer") or ""
                ).replace("www.", "").lower()
                shopify_fallback["source_method"] = shopify_fallback.get(
                    "source_method", "shopify_json"
                )
                self._tier15_routes[full_name] = {
                    "route": "shopify_fallback",
                    "source_weight": score_source(
                        shopify_fallback.get("url", "") or f"https://{win_domain}",
                        category,
                    ),
                }
                record_tier15_attempt(category)
                record_tier15_hit(category, win_domain or None)
                set_cached(cache_key, shopify_fallback, PRICE_CACHE_TTL)
                self._save_price_to_db(
                    cache_key, brand, name, variant, region, shopify_fallback
                )
                shopify_fallback["_cached"] = False
                logger.info(
                    "[PRICE] Shopify reseller FALLBACK used for %s: %.3f %s via %s "
                    "(fan_out empty; real BH price beats estimate)",
                    full_name, shopify_fallback["amount"], currency, win_domain,
                )
                return shopify_fallback

        # --- Tier 2: GPT extraction from search context ---
        if is_supplement:
            iherb_query = re.sub(
                r'\b\d+\s*(softgels?|capsules?|tablets?|gummies?|caplets?|count|ct)\b',
                '', search_query, flags=re.IGNORECASE
            ).strip()
            iherb_query = re.sub(
                r'\b(supplement|vitamin|vitamins|mineral|minerals)\b',
                '', iherb_query, flags=re.IGNORECASE
            ).strip()
            iherb_query = re.sub(r'\s+', ' ', iherb_query)
            iherb_cc = region_info["code"]

            iherb_price = await fetch_iherb_price(iherb_query, brand, full_name, iherb_cc, currency)
            if iherb_price:
                iherb_price["_cached"] = False
                if iherb_price.get("iherb_rating"):
                    self._shopping_items_cache[full_name] = [{
                        "source": "iHerb",
                        "rating": iherb_price["iherb_rating"],
                        "ratingCount": iherb_price.get("iherb_review_count"),
                        "link": iherb_price["url"],
                        "title": full_name,
                    }]
                set_cached(cache_key, iherb_price, PRICE_CACHE_TTL)
                return iherb_price

            iherb_task = search_web(f"{iherb_query} iherb price", num_results=5, country=iherb_cc)
            bh_pharmacy_task = search_web(f"{brand} {name} price", num_results=5, country="bh")
            iherb_results, bh_pharmacy_results = await asyncio.gather(iherb_task, bh_pharmacy_task)
            self._track_serper_cost()
            self._track_serper_cost()
            iherb_organic = iherb_results.get("organic", [])
            bh_organic = bh_pharmacy_results.get("organic", [])

            pharmacy_price = await fetch_pharmacy_price(bh_organic, brand, full_name, currency, track_serper_cost_fn=self._track_serper_cost)
            if pharmacy_price:
                pharmacy_price["_cached"] = False
                set_cached(cache_key, pharmacy_price, PRICE_CACHE_TTL)
                return pharmacy_price

            if ENABLE_PAGE_SCRAPE:
                known_supplement_retailers = {"iherb.com", "bn.boots.com", "bolo.bh", "amazon.com", "noon.com"}
                for item in (iherb_organic + bh_organic)[:5]:
                    link = item.get("link", "")
                    link_domain = urlparse(link).netloc.replace("www.", "")
                    if link_domain in known_supplement_retailers or link_domain in PHARMACY_DOMAINS:
                        page_price = await fetch_page_price(link, full_name, currency)
                        if page_price and page_price.get("amount"):
                            page_price["_cached"] = False
                            set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                            return page_price

            combined_organic = iherb_organic + bh_organic
            if combined_organic:
                organic_results = {"organic": combined_organic, "knowledge_graph": None}
            else:
                organic_results = {"organic": [], "knowledge_graph": None}
        else:
            organic_results = await search_price_organic(search_query, region_info["code"])
            self._track_serper_cost()

        search_results["organic"] = organic_results.get("organic", [])
        search_results["knowledge_graph"] = organic_results.get("knowledge_graph")
        search_context = self._format_search_results(search_results)
        price, usage = await extract_price(brand, name, variant, region, search_context)
        self._track_gpt_cost(usage)
        sanitize_gpt_price(price)
        _convert_gpt_price_currency(price, currency)
        if price and price.get("amount"):
            original_cur = price.get("original_currency", "").upper()
            if original_cur and original_cur != currency:
                price["source_method"] = "converted_usd"
            else:
                price["source_method"] = "local_bhd"
            if is_supplement:
                if iherb_organic and not price.get("retailer"):
                    price["retailer"] = "iHerb"
                    price["url"] = f"https://{iherb_cc}.iherb.com/search?kw={quote_plus(full_name)}"
            else:
                # S3-reopen T1 (team-lead Decision-F 2026-06-14) — ABSOLUTE
                # plausibility, NOT deviation-from-GPT. The Tier-2 price is a real
                # cited (organic-extracted) number; the GPT training estimate is
                # a guess and the judge of NOTHING. The OLD code computed a
                # GPT-relative band and annotated price_deviates_from_estimate
                # (and pre-that, SWAPPED in the estimate — the "real price thrown
                # away for a guess" violation). Now: a plausible real price is
                # KEPT with its honest converted_usd/local_bhd label, EVEN IF it
                # differs 2-3x from the guess (the guess being wrong is exactly
                # why we don't trust it). A grossly-IMPLAUSIBLE amount is a
                # wrong-scrape (installment / accessory / currency error) — it is
                # DROPPED (not promoted) so the cascade falls to the tier-8
                # estimate, the lesser evil. No GPT estimate is fetched to veto.
                if not is_price_plausible(_convert_to_bhd(price["amount"], currency), category):
                    price = None
            if price and price.get("amount"):
                if price.get("retailer") and not price.get("url"):
                    price["url"] = build_retailer_url(price["retailer"], full_name)
                set_cached(cache_key, price, PRICE_CACHE_TTL)
                self._save_price_to_db(cache_key, brand, name, variant, region, price)
                price["_cached"] = False
                return price

        # --- Broader search fallback ---
        broader_name = full_name
        for _ in range(3):
            stripped = MODEL_VARIANT_PATTERN.sub('', broader_name).strip()
            if stripped == broader_name:
                break
            broader_name = stripped

        if broader_name != full_name and not is_supplement:
            broader_results = await search_product_prices(broader_name, region_info["code"])
            self._track_serper_cost()
            broader_shopping = broader_results.get("shopping", [])
            if broader_shopping:
                price = extract_price_from_shopping(
                    broader_name, broader_shopping, currency,
                    shopping_region=broader_results.get("shopping_region"),
                )
                if price and price.get("amount"):
                    price.pop("retailer_score", None)
                    set_cached(cache_key, price, PRICE_CACHE_TTL)
                    self._save_price_to_db(cache_key, brand, name, variant, region, price)
                    price["_cached"] = False
                    return price

        # --- §5 tier-7: parked CONVERTED_USD fallback (before the GPT estimate) ---
        # Approach A — the genuine-BH curl+render tiers + broader search all
        # missed; the converted_usd Tier-1 price we parked is a REAL cited price
        # (gl=us, labeled indicative), so it BEATS the GPT estimate (tier-8).
        if converted_fallback and converted_fallback.get("amount"):
            if converted_fallback.get("retailer") and not converted_fallback.get("url"):
                converted_fallback["url"] = build_retailer_url(
                    converted_fallback["retailer"], full_name
                )
            set_cached(cache_key, converted_fallback, PRICE_CACHE_TTL)
            self._save_price_to_db(cache_key, brand, name, variant, region, converted_fallback)
            converted_fallback["_cached"] = False
            logger.info(
                "[PRICE] parked converted_usd fallback used for %s (BH curl+render "
                "missed; beats GPT estimate)", full_name,
            )
            return converted_fallback

        # --- Tier 3: GPT training data fallback ---
        if tier3_estimate is None:
            tier3_estimate, usage = await extract_price_from_training_data(brand, name, variant, region)
            self._track_gpt_cost(usage)
            sanitize_gpt_price(tier3_estimate)
            _convert_gpt_price_currency(tier3_estimate, currency)
        price = tier3_estimate
        if price and price.get("amount"):
            price["estimated"] = True
            # Preserve the gpt_* source_method when the upstream extractor
            # provided one (Bundle E PRICE_SOURCE_RANK lookup needs the
            # specific tier name, not the generic "estimated" alias).
            # Legacy "estimated" stays as the fallback for callers that
            # didn't stamp a specific gpt_* method.
            existing_method = price.get("source_method", "")
            if not (isinstance(existing_method, str) and existing_method.startswith("gpt_")):
                price["source_method"] = "estimated"
            if price.get("retailer") and not price.get("url"):
                price["url"] = build_retailer_url(price["retailer"], full_name)
            set_cached(cache_key, price, PRICE_CACHE_TTL // 2)
            self._save_price_to_db(cache_key, brand, name, variant, region, price)
            price["_cached"] = False
            return price

        return {"amount": None, "currency": currency, "_cached": False}

    async def _get_reviews(
        self, brand: str, name: str, variant: Optional[str], search_query: str,
        nocache: bool = False, category: str = "other",
        retailer_ratings: Optional[List[Dict]] = None, search_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get reviews with caching."""
        return await _get_reviews_standalone(
            brand, name, variant, search_query, nocache=nocache,
            category=category, retailer_ratings=retailer_ratings,
            search_results=search_results,
            track_serper_cost_fn=self._track_serper_cost,
            track_gpt_cost_fn=self._track_gpt_cost,
        )

    async def _get_verified_rating(self, full_name: str) -> Dict[str, Any]:
        """Get verified rating."""
        return await get_verified_rating(full_name, self._shopping_items_cache, track_serper_cost_fn=self._track_serper_cost)

    async def _smart_fallback_extract(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        category: str,
        missing_fields: List[str],
    ) -> Dict[str, Any]:
        """Targeted Serper + small GPT extract for missing critical schema fields.

        Capped at 5s by asyncio.wait_for so the parallel Phase 2 gather can't
        be dragged past its budget. Returns {field: value} for fields filled;
        empty dict on timeout / failure (callers must treat empty as no-op).

        D2 post-deploy tuning: bumped 3s -> 5s after Intervention 1 moved
        reviews to Phase 1, freeing Phase 2 wall budget. Cold-cache Serper +
        OpenAI sometimes exceeded 3s, dropping the fallback fill silently.
        """
        if not missing_fields:
            return {}

        try:
            fields_text = " ".join(missing_fields).replace("_", " ")
            full_name = f"{brand} {name} {variant or ''}".strip()
            query = f"{full_name} {fields_text} specifications"

            async def _do_extract() -> Dict[str, Any]:
                from app.services import openai_service as _openai_svc

                search_results = await search_web(query, num_results=5)
                self._track_serper_cost()

                snippets = []
                for hit in (search_results.get("organic") or [])[:5]:
                    snippet = hit.get("snippet", "")
                    if snippet:
                        snippets.append(snippet)
                context = "\n".join(snippets[:5])

                if not context:
                    return {}

                return await _openai_svc.extract_specs_targeted(
                    brand=brand,
                    name=name,
                    variant=variant,
                    category=category,
                    fields=missing_fields,
                    context=context,
                )

            return await asyncio.wait_for(_do_extract(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.info(
                f"[SMART_FALLBACK] Timeout for {brand} {name} fields {missing_fields}"
            )
            return {}
        except Exception as e:
            logger.warning(f"[SMART_FALLBACK] Error for {brand} {name}: {e}")
            return {}

    # ============================================
    # Formatting helpers (kept in orchestrator)
    # ============================================

    def _format_search_results(self, results: Dict) -> str:
        """Format search results into context string."""
        if not results:
            return "No search results available."
        formatted = []
        organic = results.get("organic", [])[:5]
        for i, r in enumerate(organic):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            formatted.append(f"{i+1}. {title}\n   {snippet}")
        shopping = results.get("shopping", [])[:3]
        if shopping:
            formatted.append("\n--- Shopping Results ---")
            for s in shopping:
                title = s.get("title", "")
                price = s.get("price", "")
                source = s.get("source", "")
                formatted.append(f"- {title}: {price} ({source})")
        return "\n".join(formatted)

    def _format_numbered_search_results(self, results: Dict) -> Tuple[str, List[str]]:
        """Format search results with [snippet_N] labels."""
        if not results:
            return "No search results available.", []
        formatted = []
        raw_snippets = []
        organic = results.get("organic", [])[:5]
        for i, r in enumerate(organic):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            snippet_text = f"{title} - {snippet}"
            raw_snippets.append(snippet_text)
            formatted.append(f"[snippet_{i+1}] {title}\n   {snippet}")
        shopping = results.get("shopping", [])[:3]
        if shopping:
            formatted.append("\n--- Shopping Results ---")
            for s in shopping:
                title = s.get("title", "")
                price = s.get("price", "")
                source = s.get("source", "")
                formatted.append(f"- {title}: {price} ({source})")
        return "\n".join(formatted), raw_snippets

    def _calculate_freshness(self, product: Dict) -> str:
        """Calculate overall data freshness."""
        specs_cached = (product.get("specs") or {}).get("_cached", True)
        price_cached = (product.get("price") or {}).get("_cached", True)
        reviews_cached = (product.get("reviews") or {}).get("_cached", True)
        if not specs_cached and not price_cached:
            return "live"
        elif specs_cached and price_cached and reviews_cached:
            return "cached"
        else:
            return "mixed"

    # ============================================
    # Cost tracking
    # ============================================

    def _save_price_to_db(self, cache_key: str, brand: str, name: str, variant: Optional[str], region: str, price: Dict):
        """Fire-and-forget save price to L2 DB.

        B0-B Item 4: wrapped per audit convention 2026-05-22 so DB write
        exceptions WARNING-log via the `_fire_and_forget` done-callback
        instead of silently disappearing.
        """
        from app.services.product_data_service import save_price
        _fire_and_forget(
            save_price(cache_key, brand, name, variant, region, price),
            label="save_price",
        )

    async def _apply_self_critique(
        self,
        *,
        comparison: Dict[str, Any],
        product_names: List[str],
        regen_args: Dict[str, Any],
        pain_workflow_context: Optional[str] = None,
        stage_timings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """I3.1/I3.3 — run the flag-gated self-critique pass and return the
        (possibly regenerated) verdict.

        No-op + zero cost when ENABLE_SELF_CRITIQUE is OFF (the prod default)
        — `critique_and_maybe_regenerate` short-circuits before any API call.
        On a low-scoring axis it regenerates the verdict ONCE via a closure
        that re-runs generate_comparison with the critique feedback appended
        to the scoring context. NEVER raises — a critique/regeneration
        failure serves the original verdict.

        Cost: the critique call's tokens are tracked into self.total_cost via
        _track_gpt_cost (≤$0.002/cmp gate); the regeneration call tracks its
        own cost inside the closure. Latency: records `critique_ms` into
        stage_timings when DEBUG_STAGE_TIMINGS is on. The CritiqueResult is
        stashed on self for the metadata/persistence thread.
        """
        from app.services import verdict_critique_service as _vcs

        self._verdict_critique_outcome = None
        if not _vcs.is_self_critique_enabled():
            return comparison

        async def _regenerate(critique: "_vcs.CritiqueResult") -> Dict[str, Any]:
            # Re-run the verdict with the critique's low-axis feedback folded
            # into the scoring context (scores_summary is appended to the
            # verdict system prompt by generate_comparison).
            feedback = (
                "\n\n## Self-critique feedback (regenerate to fix)\n"
                f"The previous verdict scored low on: {critique.regen_reason}. "
                "Rewrite the verdict to be more specific, decisive, balanced, "
                "and grounded in the numbers — keep the same JSON schema."
            )
            args = dict(regen_args)
            args["scores_summary"] = (args.get("scores_summary") or "") + feedback
            regen_comparison, regen_usage = await generate_comparison(
                args["product1"], args["product2"], args["region"],
                args.get("concern", "value"),
                user_preferences=args.get("user_preferences"),
                scores_summary=args.get("scores_summary"),
                category=args.get("category", "other"),
                demographics_profile=args.get("demographics_profile"),
            )
            self._track_gpt_cost(regen_usage)
            return regen_comparison

        t_crit = time.perf_counter() if stage_timings is not None else None
        # G6 integration fix: bound critique+regen (~1-2s + 4-6s worst) so a
        # flag-ON regen can never push a completed comparison past the outer
        # 30s hard cap. Timeout serves the original verdict.
        try:
            outcome = await asyncio.wait_for(
                _vcs.critique_and_maybe_regenerate(
                    comparison=comparison,
                    product_names=product_names,
                    regenerate=_regenerate,
                    pain_workflow_context=pain_workflow_context,
                ),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            logger.warning("[SELF_CRITIQUE] critique+regen exceeded 8s — serving original verdict")
            self._verdict_critique_outcome = None
            return comparison
        if stage_timings is not None and t_crit is not None:
            stage_timings["critique_ms"] = round((time.perf_counter() - t_crit) * 1000, 1)

        # Track the critique call's own cost (zero when the flag was OFF or
        # critique short-circuited — _track_gpt_cost on all-zero usage still
        # bumps api/gpt counters, so only call it when a critique actually ran).
        if outcome.critique is not None:
            self._track_gpt_cost(outcome.critique_usage)

        self._verdict_critique_outcome = outcome
        return outcome.final_comparison

    def _verdict_critique_metadata(self) -> Optional[Dict[str, Any]]:
        """Serialize the stashed self-critique outcome for the response
        metadata `_verdict_critique` key (consumed by the post-save
        persistence path). None when no critique ran (flag OFF / failure)."""
        outcome = getattr(self, "_verdict_critique_outcome", None)
        if outcome is None or outcome.critique is None:
            return None
        c = outcome.critique
        return {
            "axis_scores": dict(c.axis_scores),
            "needs_regen": c.needs_regen,
            "low_axes": list(c.low_axes),
            "regen_reason": c.regen_reason,
            "critic_model": c.critic_model,
            "critic_tokens_used": c.tokens_used,
            "regenerated": outcome.regenerated,
        }

    def _track_gpt_cost(self, usage: dict):
        """Track real GPT cost from token usage."""
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
        self.total_cost += cost
        self.api_calls += 1
        self.gpt_calls += 1

    def _track_serper_cost(self):
        """Track a single Serper API call."""
        self.total_cost += 0.001
        self.api_calls += 1
        self.serper_calls += 1

    def _track_cost_amount(self, amount: float):
        """Track a generic cost amount (used by Tier 1.5 cascade)."""
        self.total_cost += amount

    def _format_review_search_results(self, results: Dict, retailer_ratings: List[Dict]) -> str:
        return format_review_search_results(results, retailer_ratings)


# ============================================
# GCC REGIONAL PRICING
# ============================================

async def get_regional_prices(
    brand: str, name: str, variant: Optional[str], search_query: str
) -> Dict[str, Any]:
    """Get prices across all GCC regions in parallel."""
    service = StructuredComparisonService()
    tasks = []
    for region in GCC_REGIONS.keys():
        tasks.append(service._get_price(brand, name, variant, region, search_query))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    regional = {}
    best_price = None
    best_region = None
    for region, result in zip(GCC_REGIONS.keys(), results):
        if isinstance(result, Exception):
            regional[region] = None
            continue
        regional[region] = result
        if result and result.get("amount"):
            amount_bhd = _convert_to_bhd(result["amount"], result.get("currency", "BHD"))
            if best_price is None or amount_bhd < best_price:
                best_price = amount_bhd
                best_region = region
    return {"regional_prices": regional, "best_region": best_region, "best_price_bhd": best_price}


# ============================================
# FACTORY
# ============================================

def get_comparison_service() -> StructuredComparisonService:
    """Create a new comparison service instance per request."""
    return StructuredComparisonService()

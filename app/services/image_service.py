"""Product image URL resolution — tier cascade.

Mirrors price_service tier architecture. Returns Optional[str] (real URL or
None; frontend renders placeholder on None).

Tiers in priority order:
  1.5  Piggyback page-scrape image  (FREE — caller already has it)
  1    Serper Images                 (paid, separate `serper_images` budget counter)
  3    GPT extraction from organic   (paid, ~$0.0005)
  -    None fallback                 ($0)

Firecrawl / Scrape.do Tiers 2 / 2.5 are not wired in text-mode comparisons —
they fire when the orchestrator already has a target URL (URL-mode path),
where url_extraction_service.extract_from_url already produces image_url
via the existing JSON-LD / og:image / microdata extractors. Tiers 2/2.5 stay
available for future explicit-URL flows but are not part of the text-mode
cascade because the budget counters are already tight from price-pipeline
use, and Tier 1 + Tier 3 cover the worst-case text-mode budget at
<$0.005/comparison.

Per memory/feedback_no_backend_internals_in_reveals.md — tier provenance is
logged but never returned to the frontend. The contract emits only a URL or
null; the FE renders an `<Image>` or a placeholder primitive.

Per memory/project_upstash_redis_singlepoint_failure.md — budget counter
checks fail-OPEN on Redis down (Tier 1 still tries; we'd rather burn a credit
than ship a placeholder).

Per memory/project_bahrain_shopping_feed_gap.md — Serper Images has no `gl=`
fallback unlike Serper Shopping because the Images endpoint already returns
universal results (no GCC vs US split observed in pre-implementation audit).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.services.api_budget_service import try_consume_serper_image_credit
from app.services import api_budget_service as _llm_breaker
from app.services import llm_router as _llm_router
from app.services.model_config import sampling_kwargs, standard_model, token_limit_kwargs
from app.services.openai_service import get_client
from app.services.serper_service import search_images
# D03 (ENABLE_DATA_GUARDS_V2): the ONE banned-host list (a stdlib-only leaf).
from app.services.deny_hosts import data_guards_v2_enabled, is_denied_url
# INC-I1 (ENABLE_IMAGE_RELEVANCE_GUARD, read per call): the picture-must-match guard
# (a leaf), by MODULE ATTRIBUTE so a patch of a leaf function takes effect at call time.
from app.services import image_relevance as _relevance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_image_url(value: Any) -> bool:
    """Validate that `value` looks like an http(s) URL string."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    valid = stripped.startswith("http://") or stripped.startswith("https://")
    # D03: an image on a banned host (fimgs.net = the Fragrantica image CDN) is
    # never valid in any tier; the flag is read only after a base-True verdict.
    if valid and data_guards_v2_enabled() and is_denied_url(stripped):
        return False
    return valid


# ---------------------------------------------------------------------------
# Tier 1.5b — FREE image from the unified Serper search payload (#21)
# ---------------------------------------------------------------------------
# Fragrance cards showed placeholders: the FREE piggyback image (Tier 1.5) rides
# the price-scrape, which doesn't fire when the price PENDS, and the paid Serper-
# Images tier can miss OR be exhausted (500/day budget). The unified Serper
# search the pipeline ALREADY ran almost always carries a usable image for a
# branded product in its Google Knowledge Graph card (and sometimes on an organic
# result) — a $0, budget-FREE, price-scrape-INDEPENDENT source. This tier reads
# it BEFORE the paid Serper-Images tier. Real-URL-only; never fabricated.

# Organic-result keys that have carried an image URL across Serper API shapes.
_ORGANIC_IMAGE_KEYS = ("imageUrl", "thumbnailUrl", "thumbnail", "image")


def extract_image_from_search(search_payload: Optional[Dict[str, Any]]) -> Optional[str]:
    """A product image URL from the unified Serper search payload, or None.

    Precedence: the Knowledge Graph card's image first (highest-fidelity branded
    hero shot — `knowledgeGraph`/`knowledge_graph`, `imageUrl`/`image`), then the
    first organic result carrying an image field. Drift-tolerant (any non-dict /
    unexpected shape -> None, never raises). Validated by `_is_valid_image_url`.
    """
    if not isinstance(search_payload, dict):
        return None

    # 1) Knowledge Graph card (camelCase + snake_case shapes).
    for kg_key in ("knowledgeGraph", "knowledge_graph"):
        kg = search_payload.get(kg_key)
        if isinstance(kg, dict):
            for img_key in ("imageUrl", "image", "imageURL", "thumbnailUrl"):
                cand = kg.get(img_key)
                if _is_valid_image_url(cand):
                    return cand.strip()

    # 2) First organic result carrying an image field.
    organic = search_payload.get("organic")
    if isinstance(organic, list):
        for item in organic:
            if not isinstance(item, dict):
                continue
            for img_key in _ORGANIC_IMAGE_KEYS:
                cand = item.get(img_key)
                if _is_valid_image_url(cand):
                    return cand.strip()

    # 3) Top-level inline image pack — Serper sometimes returns an `images`
    #    block on a web search. Lowest precedence (often a thumbnail) but a free
    #    extra fallback before the placeholder (N-4, code review 2026-06-18).
    images = search_payload.get("images")
    if isinstance(images, list):
        for item in images:
            if not isinstance(item, dict):
                continue
            for img_key in _ORGANIC_IMAGE_KEYS:
                cand = item.get(img_key)
                if _is_valid_image_url(cand):
                    return cand.strip()

    return None


# ---------------------------------------------------------------------------
# Tier 3 — GPT extraction from organic results
# ---------------------------------------------------------------------------

_TIER3_PROMPT = """You are a product image URL extractor.

Given a product name and a list of organic search results (link + snippet),
return the most likely product image URL.

Product: {product_name}

Organic results:
{organic_block}

Return ONLY valid JSON in this exact shape:
{{"image_url": "https://...jpg" }} or {{"image_url": null}}

Rules:
- Prefer official brand / authorized retailer domains over marketplaces
- The URL must end in .jpg / .jpeg / .png / .webp OR be a recognized image CDN URL
- Return null when no result clearly identifies a product image
- Do not fabricate URLs; if uncertain, return null"""


async def extract_image_via_gpt(
    product_name: str,
    organic_results: List[Dict[str, Any]],
) -> Optional[str]:
    """Tier 3 — ask gpt-4o-mini to pick the most likely product-image URL.

    Returns a URL string or None (no fallback URL allowed; the placeholder
    is rendered by the frontend instead of a fabricated image).
    """
    if not organic_results:
        return None

    # Defensive: drop None / non-dict entries before .get() — caller may pass
    # heterogeneous lists in pathological cases (Serper API drift, partial
    # parse failures upstream).
    organic_block = "\n".join(
        f"- {r.get('link', '')}: {r.get('snippet', '')}"
        for r in organic_results[:10]
        if isinstance(r, dict)
    )
    # W4-11 (R13): the third-party link + snippet text sits in ONE <SEARCH_RESULTS>
    # region (sanitized) under the do-not-follow guard sentence.
    from app.services.extraction_service import SEARCH_RESULTS_GUARD, _wrap_search_context

    prompt = SEARCH_RESULTS_GUARD + "\n\n" + _TIER3_PROMPT.format(
        product_name=product_name,
        organic_block=_wrap_search_context(organic_block) if organic_block else "(no results)",
    )

    try:
        client = get_client()
        _model = standard_model()
        # W4-11 (R7): through the W1-3 breaker chokepoint (a bare create with its flag OFF).
        completion = await _llm_router.route("image_tier3", _llm_breaker.guarded_llm_create,
            client,
            model=_model,
            messages=[{"role": "user", "content": prompt}],
            **token_limit_kwargs(_model, 120),
            **sampling_kwargs(_model, 0.1),
        )
        content = (completion.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("[image] Tier 3 GPT extraction failed: %r", e)
        return None

    # Strip markdown fences if GPT wraps the response
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.info("[image] Tier 3 GPT returned non-JSON: %r", content[:120])
        return None

    candidate = parsed.get("image_url")
    if _is_valid_image_url(candidate):
        return candidate.strip()
    return None


def _log_img_tier(tier: str, outcome: str, t0: float) -> None:
    """INC-X2a IMAGE-TIER-TIMING (log-only, unflagged): one INFO line per tier
    reached: a constant tier name, a closed-set outcome and elapsed ms. Never a
    product name, URL or query text."""
    logger.info("[IMG_TIER] tier=%s outcome=%s ms=%d", tier, outcome,
                int((time.perf_counter() - t0) * 1000))


# ---------------------------------------------------------------------------
# INC-I1 PICTURE-MUST-MATCH (ENABLE_IMAGE_RELEVANCE_GUARD): the guarded tier
# helpers. Reached only when get_product_image_url built a RelevanceCall (the flag
# reads ON and the caller handed the identity); the base helpers above are untouched.
# ---------------------------------------------------------------------------
_KG_IMAGE_KEYS = ("imageUrl", "image", "imageURL", "thumbnailUrl")


def _first_image(item: Dict[str, Any], keys: tuple) -> Optional[str]:
    """INC-I1: the first https value among ``keys`` that passes the base validator,
    else the first base-valid one (an http value: the guard rejects it with reason
    scheme and counts it), else None."""
    fallback = None
    for key in keys:
        cand = item.get(key)
        if _is_valid_image_url(cand):
            url = cand.strip()
            if url.startswith("https://"):
                return url
            if fallback is None:
                fallback = url
    return fallback


def _extract_relevant_image_from_search(search_payload: Any, rel: Any) -> Optional[str]:
    """INC-I1 Tier 1.5b under the guard: the base precedence (knowledge graph, organic,
    images), every item tested: a knowledge graph by its title (its type serves the
    fragrance word only; its website / description link and source feed the deny
    only), an organic item by its title + link host, an images item by its title +
    source and its link / domain host. The first accepted image, else None."""
    if not isinstance(search_payload, dict):
        return None
    for kg_key in ("knowledgeGraph", "knowledge_graph"):
        kg = search_payload.get(kg_key)
        if not isinstance(kg, dict):
            continue
        url = _first_image(kg, _KG_IMAGE_KEYS)
        if url and rel.accept(
            "search_payload", url, texts=(kg.get("title"),),
            fragrance_texts=(kg.get("type"),),
            deny_only_hosts=(kg.get("website"), kg.get("descriptionLink")),
            deny_only_texts=(kg.get("descriptionSource"),),
        ):
            return url
    organic = _relevance.dict_items(search_payload.get("organic"), _relevance.SEARCH_ITEMS_MAX)
    for item in organic:
        url = _first_image(item, _ORGANIC_IMAGE_KEYS)
        if url and rel.accept(
            "search_payload", url, texts=(item.get("title"),), hosts=(item.get("link"),),
        ):
            return url
    images = _relevance.dict_items(search_payload.get("images"), _relevance.SEARCH_ITEMS_MAX)
    for item in images:
        url = _first_image(item, _ORGANIC_IMAGE_KEYS)
        if url and rel.accept(
            "search_payload", url, texts=(item.get("title"), item.get("source")),
            hosts=(item.get("link"), item.get("domain")),
        ):
            return url
    return None


def _relevant_serper_image(images: Any, rel: Any) -> Optional[str]:
    """INC-I1 Tier 1 under the guard: walk ``images[:knob]`` in order and return the
    first item whose imageUrl passes the base validator and the guard (its title +
    source, its link / domain host); else None."""
    for item in _relevance.dict_items(images, rel.num()):
        cand = item.get("imageUrl")
        if not _is_valid_image_url(cand):
            continue
        url = cand.strip()
        if rel.accept(
            "serper_images", url, texts=(item.get("title"), item.get("source")),
            hosts=(item.get("link"), item.get("domain")),
        ):
            return url
    return None


def _log_img_relevance(rel: Any) -> None:
    """INC-I1: the ONE [IMG_RELEVANCE] line of a guarded call: closed-set words and
    one int; never a product name, URL, query, title or source text."""
    slot, tier, outcome, n, reason = rel.summary()
    logger.info("[IMG_RELEVANCE] product=%s tier=%s outcome=%s candidates=%d reason=%s",
                slot, tier, outcome, n, reason)


# ---------------------------------------------------------------------------
# Orchestrator — tier cascade
# ---------------------------------------------------------------------------

async def get_product_image_url(
    product_name: str,
    *,
    region: str = "bahrain",
    page_scrape_image: Optional[str] = None,
    organic_results: Optional[List[Dict[str, Any]]] = None,
    search_payload: Optional[Dict[str, Any]] = None,
    relevance: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Resolve product image URL via tier cascade. Returns None on full miss.

    Args:
        product_name: Display name for the product (e.g. "Apple iPhone 15 Pro").
        region: Region hint (unused today; reserved for future gl=... routing).
        page_scrape_image: Tier 1.5 piggyback — image already retrieved by the
            price tier. When truthy + valid URL, returned immediately (FREE).
        organic_results: Serper organic results (for Tier 3 GPT fallback).
        search_payload: #21 — the unified Serper search payload (knowledgeGraph +
            organic). Tier 1.5b reads a FREE, budget-free, price-scrape-INDEPENDENT
            image from it (the fragrance-placeholder fix). None for legacy callers.
        relevance: INC-I1 -- the identity for the picture-must-match guard
            ({brand, line, category, slot}); scs passes it for text compares only,
            and only under ENABLE_IMAGE_RELEVANCE_GUARD. None = the base cascade.

    Returns:
        A URL string (real image) or None (frontend should render placeholder).
    """
    name = (product_name or "").strip()
    if not name:
        return None

    # INC-I1 (ENABLE_IMAGE_RELEVANCE_GUARD, read per call): the guard runs for this
    # call only when the caller handed the identity AND the flag reads ON; otherwise
    # every tier below is the base path, byte for byte.
    _rel = None
    if relevance is not None and _relevance.guard_enabled():
        _rel = _relevance.RelevanceCall(name, relevance)

    _t_call = time.perf_counter()
    # INC-X2a: the tier in flight and its start, for the cancellation line.
    _inflight = ["piggyback", _t_call]
    try:
        # ----- Tier 1.5 — piggyback page-scrape image (FREE, highest fidelity) -----
        if page_scrape_image and _is_valid_image_url(page_scrape_image) and (
                _rel is None or _rel.accept_scheme("piggyback", page_scrape_image.strip())):
            _log_img_tier("piggyback", "hit", _inflight[1])
            logger.info("[image] Tier 1.5 piggyback hit for %r", name[:60])
            return page_scrape_image.strip()
        _log_img_tier("piggyback", "miss" if page_scrape_image else "skipped", _inflight[1])

        # ----- Tier 1.5b — FREE image from the unified search payload (#21) -----
        # Reads the Knowledge Graph / organic image the pipeline ALREADY fetched.
        # $0, no Serper-Images budget, independent of the price-scrape — fixes the
        # fragrance placeholder when the price pends.
        _inflight[0] = "search_payload"
        _inflight[1] = time.perf_counter()
        search_img = (extract_image_from_search(search_payload) if _rel is None
                      else _extract_relevant_image_from_search(search_payload, _rel))
        if search_img:
            _log_img_tier("search_payload", "hit", _inflight[1])
            logger.info("[image] Tier 1.5b unified-search image hit for %r", name[:60])
            return search_img
        _log_img_tier("search_payload", "skipped" if search_payload is None else "miss", _inflight[1])

        # ----- Tier 1 — Serper Images (paid, budget-gated) -----
        # The credit gate is the same single synchronous call as before; INC-X2a
        # only times it (it cannot be interrupted, L-X2a-3).
        _inflight[0] = "serper_budget"
        _inflight[1] = time.perf_counter()
        _granted = try_consume_serper_image_credit(1)
        _log_img_tier("serper_budget", "hit" if _granted else "miss", _inflight[1])
        _inflight[0] = "serper_images"
        _inflight[1] = time.perf_counter()
        if _granted:
            _outcome = "miss"
            try:
                if _rel is None:
                    response = await search_images(name, num_results=1)
                else:
                    # INC-I1: the full name (+ perfume for the fragrance category) and
                    # IMAGE_RELEVANCE_CANDIDATES results; still one credit per call.
                    response = await search_images(_rel.query(), num_results=_rel.num())
            except Exception as e:
                _outcome = "error:" + type(e).__name__
                logger.warning("[image] Tier 1 Serper Images raised: %r", e)
                response = None

            if isinstance(response, dict):
                images = response.get("images") or []
                # Defensive: future Serper API drift may return `images` as a
                # string / dict / int. We require a list before indexing — any
                # other shape falls through to Tier 3 instead of crashing.
                if _rel is not None:
                    # INC-I1: the guard walks images[:knob]; images[0] alone never wins.
                    candidate = _relevant_serper_image(images, _rel)
                    if candidate is not None:
                        _log_img_tier("serper_images", "hit", _inflight[1])
                        logger.info("[image] Tier 1 Serper hit for %r", name[:60])
                        return candidate
                elif isinstance(images, list) and images and isinstance(images[0], dict):
                    candidate = images[0].get("imageUrl")
                    if _is_valid_image_url(candidate):
                        _log_img_tier("serper_images", "hit", _inflight[1])
                        logger.info("[image] Tier 1 Serper hit for %r", name[:60])
                        return candidate.strip()
            _log_img_tier("serper_images", _outcome, _inflight[1])
        else:
            _log_img_tier("serper_images", "skipped", _inflight[1])

        # ----- Tier 3 — GPT extraction from organic results (paid) -----
        _inflight[0] = "llm_pick"
        _inflight[1] = time.perf_counter()
        # INC-I1: under the guard the LLM pick runs only when an organic result passes.
        if organic_results and (_rel is None or _rel.organic_passes(organic_results)):
            _outcome = "miss"
            try:
                gpt_url = await extract_image_via_gpt(name, organic_results)
            except Exception as e:
                _outcome = "error:" + type(e).__name__
                logger.warning("[image] Tier 3 orchestrator caught: %r", e)
                gpt_url = None
            if _is_valid_image_url(gpt_url) and (
                    _rel is None or _rel.accept_pick(gpt_url.strip(), organic_results)):
                _log_img_tier("llm_pick", "hit", _inflight[1])
                logger.info("[image] Tier 3 GPT hit for %r", name[:60])
                return gpt_url.strip()
            _log_img_tier("llm_pick", _outcome, _inflight[1])
        else:
            _log_img_tier("llm_pick", "skipped", _inflight[1])

        # ----- Final fallback — None (frontend renders placeholder) -----
        logger.info("[image] All tiers exhausted for %r — returning None", name[:60])
        return None
    except asyncio.CancelledError:
        # INC-X2a: the 5 s Phase-1 race cancelled this call. Log the tier in
        # flight; no await here, and the cancellation is re-raised unchanged.
        logger.info("[IMG_TIER] cancelled tier=%s tier_ms=%d total_ms=%d",
                    _inflight[0], int((time.perf_counter() - _inflight[1]) * 1000),
                    int((time.perf_counter() - _t_call) * 1000))
        raise
    finally:
        # INC-I1: exactly ONE [IMG_RELEVANCE] line per guarded call (a return, an
        # uncaught exception or the 5 s cancellation); no await here.
        if _rel is not None:
            _log_img_relevance(_rel)

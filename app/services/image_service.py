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
import hashlib
import json
import logging
import os
import re
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
# INC-I2a (ENABLE_IMAGE_LATE_BIND): the late-pick cache (Upstash through the shared
# redis-offloop pool) and the cache-name folder.
from app.services import category_gate as _cg
from app.services.cache_service import get_cached, set_cached
from app.utils.redis_offloop import run_redis_offloop_pool

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


# ---------------------------------------------------------------------------
# INC-I2a PICTURE-NOT-CUT (ENABLE_IMAGE_LATE_BIND, default OFF, read per call): the
# late, background cascade. scs starts it with the product (out of the 5 s Phase-1
# wait), binds it at the tail and caches every guard-accepted late pick in Upstash
# under PICK_CACHE_PREFIX. Additive: get_product_image_url above is not edited.
# ---------------------------------------------------------------------------
LATE_BIND_FLAG_ENV = "ENABLE_IMAGE_LATE_BIND"
_LATE_TRUTHY = ("true", "1", "yes", "on")
#: The guard-rules version: sha256 over the source of the image_relevance guard
#: functions and methods (INC-I2b I-2: the words helpers included) plus a
#: deterministic text of every word table check() reads ("\n"-joined), first 8 hex.
#: A unit that edits any of them bumps this constant (pinned by the E22 row).
PICK_GUARD_RULES = "7f9e0f4f"
PICK_CACHE_PREFIX = "imgpick:v1:" + PICK_GUARD_RULES + ":"
_LATE_MAX_SECONDS_CEILING = 30.0


def late_bind_enabled() -> bool:
    """True iff ``ENABLE_IMAGE_LATE_BIND`` is set truthy. Read PER CALL."""
    return os.getenv(LATE_BIND_FLAG_ENV, "false").strip().lower() in _LATE_TRUTHY


def _positive_knob(name: str, default: float) -> float:
    """A finite positive float from ``name``; unset, blank, garbage, inf, nan and
    <= 0 give ``default``."""
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not 0 < value < float("inf"):  # nan, inf and <= 0 fall back
        return default
    return value


def image_late_bind_max_wait_seconds() -> float:
    """IMAGE_LATE_BIND_MAX_WAIT_SECONDS (default 3.0): the longest bind wait."""
    return _positive_knob("IMAGE_LATE_BIND_MAX_WAIT_SECONDS", 3.0)


def image_late_bind_reserve_seconds() -> float:
    """IMAGE_LATE_BIND_RESERVE_SECONDS (default 2.0): kept free before the deadline."""
    return _positive_knob("IMAGE_LATE_BIND_RESERVE_SECONDS", 2.0)


def image_late_max_seconds() -> float:
    """IMAGE_LATE_MAX_SECONDS (default 20.0, clamped to at most 30.0): the job bound."""
    return min(_positive_knob("IMAGE_LATE_MAX_SECONDS", 20.0), _LATE_MAX_SECONDS_CEILING)


def image_pick_cache_ttl_seconds() -> int:
    """IMAGE_PICK_CACHE_TTL_SECONDS (default 604800 = 7 days): the cache entry TTL."""
    value = _positive_knob("IMAGE_PICK_CACHE_TTL_SECONDS", 604800.0)
    return int(value) if value >= 1 else 604800


def _name_part(text: Any) -> str:
    """One name part: category_gate.normalize minus size tokens (a SIZE_TOKEN, a
    UNIT_WORDS token, a number directly before a UNIT_WORDS token), space-joined."""
    toks = _cg.normalize(text[:_relevance.TEXT_MAX_CHARS] if isinstance(text, str) else "")
    out = []
    for i, tok in enumerate(toks):
        if _relevance.SIZE_TOKEN.fullmatch(tok) or tok in _relevance.UNIT_WORDS:
            continue
        if _relevance._NUMBER.fullmatch(tok) and i + 1 < len(toks) and toks[i + 1] in _relevance.UNIT_WORDS:
            continue
        out.append(tok)
    return " ".join(out)


def pick_cache_name(relevance: Any, variant: Any) -> str:
    """The cache name of a late pick: PICK_CACHE_PREFIX + 32 hex of sha256 over
    category|brand|line|conc|axis (each folded, sizes stripped; conc = the variant;
    axis s1 / s0 by ENABLE_IMAGE_GUARD_SHORT_LINE); never the slot, never raw text."""
    rel = relevance if isinstance(relevance, dict) else {}
    parts = [_name_part(rel.get("category")), _name_part(rel.get("brand")),
             _name_part(rel.get("line")), _name_part(variant),
             ("s1" if _relevance.short_line_enabled() else "s0")
             + ("w1:" + ",".join(sorted(_relevance._conc_labels(rel.get("typed"))))
                if _relevance.guard_words_enabled() else "w0")]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    return PICK_CACHE_PREFIX + digest


def _log_late_cache(outcome: str, t0: float) -> None:
    logger.info("IMG_LATE cache outcome=%s ms=%d", outcome, int((time.perf_counter() - t0) * 1000))


async def _read_cached_pick(name: str) -> Optional[Dict[str, str]]:
    """ONE pool job: the cached pick, or None. A hit needs a dict value whose ``u`` is
    an https string, not on a denied host (flag-free) and base-valid."""
    t0 = time.perf_counter()
    try:
        value = await run_redis_offloop_pool(get_cached, name)
    except Exception:  # noqa: BLE001 - a read failure is a miss; the cascade runs
        _log_late_cache("error", t0)
        return None
    url = value.get("u") if isinstance(value, dict) else None
    if (isinstance(url, str) and url.strip().startswith("https://")
            and not is_denied_url(url.strip()) and _is_valid_image_url(url)):
        _log_late_cache("hit", t0)
        return {"u": url.strip(), "t": str(value.get("t") or "")}
    _log_late_cache("miss", t0)
    return None


async def _store_pick(name: str, url: str, tier: str, state: Optional[Dict[str, Any]]) -> None:
    """ONE durable pool job: store ``{"u", "t"}`` for the TTL; ``stored`` only on True."""
    t0 = time.perf_counter()
    try:
        ok = await run_redis_offloop_pool(
            set_cached, name, {"u": url, "t": tier}, image_pick_cache_ttl_seconds(), durable=True,
        )
    except Exception:  # noqa: BLE001 - the picture is kept; the write is lost
        ok = False
    if ok is True:
        if isinstance(state, dict):
            state["stored"] = True
        _log_late_cache("stored", t0)
    else:
        _log_late_cache("store_failed", t0)


def _life_open(state: Optional[Dict[str, Any]]) -> bool:
    """R-18: the request's life (llm_pick runs only inside it)."""
    if not isinstance(state, dict):
        return True
    if not state.get("open", True):
        return False
    until = state.get("until")
    return until is None or time.monotonic() < until


async def get_product_image_url_late(
    product_name: str,
    *,
    region: str = "bahrain",
    payload: "asyncio.Future[Any]",
    variant: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
    relevance: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """INC-I2a: the late cascade: cache read -> piggyback skipped -> credit (pool) ->
    Serper Images -> the unified-search payload (``payload``, shielded) -> Tier 1.5b
    -> llm_pick on its organic while the request's life is open -> None. Every
    guard-accepted pick is stored; a miss, error, cut or cache hit never is."""
    name = (product_name or "").strip()
    if not name:
        return None
    _t_call = time.perf_counter()
    cache_name = None
    if relevance is not None and _relevance.guard_enabled():
        cache_name = pick_cache_name(relevance, variant)
    _inflight = ["cache", _t_call]
    _rel = None
    try:
        if cache_name is None:
            _log_late_cache("skipped", _t_call)
        else:
            hit = await _read_cached_pick(cache_name)
            if hit is not None:
                if isinstance(state, dict):
                    state["cached"] = True
                return hit["u"]
            _rel = _relevance.RelevanceCall(name, relevance)
        _inflight[0] = "piggyback"
        _inflight[1] = time.perf_counter()
        _log_img_tier("piggyback", "skipped", _inflight[1])

        _picked: Optional[str] = None
        _picked_tier = ""
        _inflight[0] = "serper_budget"
        _inflight[1] = time.perf_counter()
        _granted = await run_redis_offloop_pool(try_consume_serper_image_credit, 1)
        _log_img_tier("serper_budget", "hit" if _granted else "miss", _inflight[1])
        _inflight[0] = "serper_images"
        _inflight[1] = time.perf_counter()
        if _granted:
            _outcome = "miss"
            _t_aw = time.perf_counter()
            try:
                if _rel is None:
                    response = await search_images(name, num_results=1)
                else:
                    response = await search_images(_rel.query(), num_results=_rel.num())
            except Exception as e:  # noqa: BLE001 - the base tier's arm
                _outcome = "error:" + type(e).__name__
                logger.warning("[image] Tier 1 Serper Images raised: %r", e)
                response = None
            finally:
                _cur = asyncio.current_task()
                logger.info("IMG_LATE serper_await ms=%d cancelling=%d",
                            int((time.perf_counter() - _t_aw) * 1000),
                            1 if (_cur is not None and _cur.cancelling()) else 0)
            if isinstance(response, dict):
                images = response.get("images") or []
                if _rel is not None:
                    _picked = _relevant_serper_image(images, _rel)
                elif isinstance(images, list) and images and isinstance(images[0], dict):
                    cand = images[0].get("imageUrl")
                    _picked = cand.strip() if _is_valid_image_url(cand) else None
            if _picked is not None:
                _picked_tier = "serper_images"
                _log_img_tier("serper_images", "hit", _inflight[1])
            else:
                _log_img_tier("serper_images", _outcome, _inflight[1])
        else:
            _log_img_tier("serper_images", "skipped", _inflight[1])

        search_payload = None
        if _picked is None:
            _inflight[0] = "search_payload"
            _inflight[1] = time.perf_counter()
            search_payload = await asyncio.shield(payload)
            search_img = (extract_image_from_search(search_payload) if _rel is None
                          else _extract_relevant_image_from_search(search_payload, _rel))
            if search_img:
                _picked, _picked_tier = search_img, "search_payload"
                _log_img_tier("search_payload", "hit", _inflight[1])
            else:
                _log_img_tier("search_payload", "skipped" if search_payload is None else "miss",
                              _inflight[1])

        if _picked is None:
            _inflight[0] = "llm_pick"
            _inflight[1] = time.perf_counter()
            organic = search_payload.get("organic", []) if isinstance(search_payload, dict) else None
            if organic and _life_open(state) and (_rel is None or _rel.organic_passes(organic)):
                _outcome = "miss"
                try:
                    gpt_url = await extract_image_via_gpt(name, organic)
                except Exception as e:  # noqa: BLE001 - the base tier's arm
                    _outcome = "error:" + type(e).__name__
                    logger.warning("[image] Tier 3 orchestrator caught: %r", e)
                    gpt_url = None
                if _is_valid_image_url(gpt_url) and (
                        _rel is None or _rel.accept_pick(gpt_url.strip(), organic)):
                    _picked, _picked_tier = gpt_url.strip(), "llm_pick"
                    _log_img_tier("llm_pick", "hit", _inflight[1])
                else:
                    _log_img_tier("llm_pick", _outcome, _inflight[1])
            else:
                _log_img_tier("llm_pick", "skipped", _inflight[1])

        if _picked is None:
            return None
        if cache_name is not None and _rel is not None:
            _inflight[0] = "cache"
            _inflight[1] = time.perf_counter()
            await _store_pick(cache_name, _picked, _picked_tier, state)
        return _picked
    except asyncio.CancelledError:
        # The job's own bound or a cancel: the X2a line for the paid tiers in flight
        # only; no await here, re-raised unchanged.
        if _inflight[0] in ("serper_images", "llm_pick"):
            logger.info("[IMG_TIER] cancelled tier=%s tier_ms=%d total_ms=%d",
                        _inflight[0], int((time.perf_counter() - _inflight[1]) * 1000),
                        int((time.perf_counter() - _t_call) * 1000))
        raise
    finally:
        if _rel is not None:
            _log_img_relevance(_rel)


# ---------------------------------------------------------------------------
# INC-I2b SHOP-IMAGE-TIER: A (ENABLE_SHOP_PAGE_IMAGE, the WooCommerce listing photo
# stamped on the winning price dict) and B (ENABLE_SHOPPING_THUMB_IMAGE, OWNER POLICY:
# a guarded Google Shopping thumbnail as the last resort). Both read per call; A's
# reader lives in image_relevance (the adapter's leaf import). Never cached here.
# ---------------------------------------------------------------------------
SHOPPING_THUMB_FLAG_ENV = "ENABLE_SHOPPING_THUMB_IMAGE"
_SHOP_KEY_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")
_SHOP_PAGE_KEYS_MAX = 12
_SHOP_THUMB_KEYS_MAX = 24


def shopping_thumb_enabled() -> bool:
    """True iff ``ENABLE_SHOPPING_THUMB_IMAGE`` is set truthy. Read PER CALL."""
    return os.getenv(SHOPPING_THUMB_FLAG_ENV, "false").strip().lower() in _LATE_TRUTHY


def _key_names(item: Any, cap: int):
    """(names, other) of a dict's keys: the names fullmatching the closed pattern,
    sorted, at most ``cap``, comma-joined ("-" for none); other = the rest."""
    if not isinstance(item, dict):
        return "-", 0
    names = sorted(k for k in item if isinstance(k, str) and _SHOP_KEY_NAME.fullmatch(k))
    shown = names[:cap]
    return (",".join(shown) if shown else "-"), len(item) - len(shown)


def _shape_keys(images: Any):
    """(shape, keys, other) of a WooCommerce ``images`` value: the type class and the
    first item's key names (names only, never a value)."""
    if isinstance(images, list):
        first = images[0] if images else None
        keys, other = _key_names(first, _SHOP_PAGE_KEYS_MAX)
        return "list", keys, other
    if isinstance(images, dict):
        keys, other = _key_names(images, _SHOP_PAGE_KEYS_MAX)
        return "dict", keys, other
    if isinstance(images, str):
        return "str", "-", 0
    if images is None:
        return "none", "-", 0
    return "other", "-", 0


def _log_shop_page(platform: str, outcome: str, reason: str, shape: str, keys: str, other: int) -> None:
    logger.info("IMG_SHOP page platform=%s outcome=%s reason=%s shape=%s keys=%s other=%d",
                platform, outcome, reason, shape, keys, other)


def stamp_shop_image(price: Any, platform: str, product: Any, variant: Any,
                     product_name: Any, title: Any) -> None:
    """INC-I2b A: stamp the listing's own first https raster photo on the winning
    price dict as ``image_url`` when the guard reads ON and the listing title passes
    the words test (form, free intense). ``variant`` is reserved for the Shopify
    follow-up. Total: any raise leaves the dict untouched (outcome error)."""
    if not _relevance.guard_enabled():
        _log_shop_page(platform, "skipped", "none", "-", "-", 0)
        return
    try:
        images = product.get("images") if isinstance(product, dict) else None
        shape, keys, other = _shape_keys(images)
        src = None
        for item in _relevance.dict_items(images, _relevance.JSONLD_IMAGES_MAX):
            if isinstance(item.get("src"), str):
                src = item.get("src")
                break
        url = _relevance.first_https_raster(src) if src is not None else None
        reason = "none"
        if url is None:
            outcome = "no_image"
        else:
            why = _relevance.words_reason_for(product_name, title)
            if why is not None:
                outcome, reason = "refused", why
            elif isinstance(price, dict):
                price["image_url"] = url
                outcome = "stamped"
            else:
                outcome = "no_image"
    except Exception:  # noqa: BLE001 - the adapter never raises for a picture
        _log_shop_page(platform, "error", "none", "-", "-", 0)
        return
    _log_shop_page(platform, outcome, reason, shape, keys, other)


def _thumb_url(item: Dict[str, Any]) -> Optional[str]:
    for key in _ORGANIC_IMAGE_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _log_shop_keys(slot: str, items: Any) -> None:
    """INC-I2b B: the ONE keys line of a thumbnail call: the first item's key names,
    and counts of items with an image, an https one, a gstatic-labelled host."""
    walk = _relevance.dict_items(items, _relevance.SEARCH_ITEMS_MAX)
    names, other = _key_names(walk[0] if walk else None, _SHOP_THUMB_KEYS_MAX)
    with_url = https = gstatic = 0
    for item in walk:
        url = _thumb_url(item)
        if url is None:
            continue
        with_url += 1
        if url.startswith("https://"):
            https += 1
        if "gstatic" in _relevance._host(url).split("."):
            gstatic += 1
    logger.info("IMG_SHOP keys product=%s names=%s other=%d with_url=%d https=%d gstatic=%d",
                slot, names, other, with_url, https, gstatic)


def shopping_thumbnail(items: Any, product_name: Any, slot: Any,
                       relevance: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """INC-I2b B: the first Shopping item thumbnail that passes the guard AND the words
    test (whatever ENABLE_IMAGE_GUARD_WORDS reads, I-12); None without a relevance (the
    guard OFF, a camera product). Never stored, never in [IMG_RELEVANCE]."""
    if relevance is None:
        _slot = str(slot) if slot in (0, 1) and not isinstance(slot, bool) else "-"
        logger.info("IMG_SHOP thumb product=%s outcome=skipped candidates=0 reason=none", _slot)
        return None
    rel = _relevance.RelevanceCall(product_name, relevance)
    _log_shop_keys(rel.slot, items)
    found = None
    for item in _relevance.dict_items(items, _relevance.SEARCH_ITEMS_MAX):
        url = _first_image(item, _ORGANIC_IMAGE_KEYS)
        if url and rel.accept_thumb(
            url, texts=(item.get("title"), item.get("source")), hosts=(item.get("link"),),
        ):
            found = url
            break
    slot_s, _tier, outcome, n, reason = rel.summary()
    logger.info("IMG_SHOP thumb product=%s outcome=%s candidates=%d reason=%s",
                slot_s, outcome, n, reason)
    return found

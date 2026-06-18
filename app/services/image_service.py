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

import json
import logging
from typing import Any, Dict, List, Optional

from app.services.api_budget_service import try_consume_serper_image_credit
from app.services.openai_service import get_client
from app.services.serper_service import search_images

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_image_url(value: Any) -> bool:
    """Validate that `value` looks like an http(s) URL string."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped.startswith("http://") or stripped.startswith("https://")


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
    prompt = _TIER3_PROMPT.format(
        product_name=product_name,
        organic_block=organic_block or "(no results)",
    )

    try:
        client = get_client()
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.1,
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

    Returns:
        A URL string (real image) or None (frontend should render placeholder).
    """
    name = (product_name or "").strip()
    if not name:
        return None

    # ----- Tier 1.5 — piggyback page-scrape image (FREE, highest fidelity) -----
    if page_scrape_image and _is_valid_image_url(page_scrape_image):
        logger.info("[image] Tier 1.5 piggyback hit for %r", name[:60])
        return page_scrape_image.strip()

    # ----- Tier 1.5b — FREE image from the unified search payload (#21) -----
    # Reads the Knowledge Graph / organic image the pipeline ALREADY fetched.
    # $0, no Serper-Images budget, independent of the price-scrape — fixes the
    # fragrance placeholder when the price pends.
    search_img = extract_image_from_search(search_payload)
    if search_img:
        logger.info("[image] Tier 1.5b unified-search image hit for %r", name[:60])
        return search_img

    # ----- Tier 1 — Serper Images (paid, budget-gated) -----
    if try_consume_serper_image_credit(1):
        try:
            response = await search_images(name, num_results=1)
        except Exception as e:
            logger.warning("[image] Tier 1 Serper Images raised: %r", e)
            response = None

        if isinstance(response, dict):
            images = response.get("images") or []
            # Defensive: future Serper API drift may return `images` as a
            # string / dict / int. We require a list before indexing — any
            # other shape falls through to Tier 3 instead of crashing.
            if isinstance(images, list) and images and isinstance(images[0], dict):
                candidate = images[0].get("imageUrl")
                if _is_valid_image_url(candidate):
                    logger.info("[image] Tier 1 Serper hit for %r", name[:60])
                    return candidate.strip()

    # ----- Tier 3 — GPT extraction from organic results (paid) -----
    if organic_results:
        try:
            gpt_url = await extract_image_via_gpt(name, organic_results)
        except Exception as e:
            logger.warning("[image] Tier 3 orchestrator caught: %r", e)
            gpt_url = None
        if _is_valid_image_url(gpt_url):
            logger.info("[image] Tier 3 GPT hit for %r", name[:60])
            return gpt_url.strip()

    # ----- Final fallback — None (frontend renders placeholder) -----
    logger.info("[image] All tiers exhausted for %r — returning None", name[:60])
    return None

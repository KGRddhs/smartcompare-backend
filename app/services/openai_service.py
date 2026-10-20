"""
OpenAI Service - Vision and text processing for product comparison
"""
import asyncio
import json
import base64
import logging
import math
import os
from typing import Any, Dict, List, Optional

import httpx
from openai import AsyncOpenAI

from app.services.llm_provider import provider_base_url
from app.services.model_config import (
    openai_max_retries,
    sampling_kwargs,
    standard_model,
    token_limit_kwargs,
    verdict_model,
    vision_model,
)
from app.services import api_budget_service as _llm_breaker
from app.utils.prompt_sanitizer import sanitize_prompt_input

logger = logging.getLogger(__name__)

# Initialize async client (reads OPENAI_API_KEY from env at request time).
# Explicit timeout: 30s connect (Railway networking can be slow), 120s total.
# This module-level singleton is kept for back-compat with existing call sites.
# #117 — max_retries is the OPENAI_MAX_RETRIES knob (default 2 == the SDK
# default, byte-identical unset). Construction-time for THIS singleton (a
# Railway change needs a restart to reach it); the lazy clients below read it
# fresh at first build.
client = AsyncOpenAI(
    base_url=provider_base_url(),
    timeout=httpx.Timeout(120.0, connect=30.0),
    max_retries=openai_max_retries(),
)

# One memoised AsyncOpenAI, built lazily by get_client() (S75 U3b, decision
# D3 = C, 2026-10-08: no per-user project routing, so the private-key arm is gone).
_client_cache: Dict[str, AsyncOpenAI] = {}
_CLIENT_KEY = "default"


def get_client() -> AsyncOpenAI:
    """Return the memoised OpenAI async client, built on first use.

    U3b (decision D3 = C): one client for every call; it reads
    OPENAI_API_KEY from the environment when first built.
    """
    cached = _client_cache.get(_CLIENT_KEY)
    if cached is not None:
        return cached

    new_client = AsyncOpenAI(
        base_url=provider_base_url(),
        timeout=httpx.Timeout(120.0, connect=30.0),
        max_retries=openai_max_retries(),  # #117
    )
    _client_cache[_CLIENT_KEY] = new_client
    return new_client


def _log_cache_telemetry(response, call_label: str = "extract") -> None:
    """D2 Intervention 2: log OpenAI auto-prompt-cache hits.

    SDK shape: openai>=2.x exposes cached tokens at
    response.usage.prompt_tokens_details.cached_tokens (nested). Older SDK
    drafts and some Anthropic/proxy implementations expose it flat at
    response.usage.prompt_tokens_cached. Use a getattr fallback so the
    telemetry works regardless of which path the SDK populates.
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    cached_tokens = getattr(usage, "prompt_tokens_cached", None)
    if cached_tokens is None:
        details = getattr(usage, "prompt_tokens_details", None)
        cached_tokens = getattr(details, "cached_tokens", 0) if details is not None else 0
    cached_tokens = cached_tokens or 0
    if cached_tokens > 0:
        logger.info(f"[OPENAI_CACHE] {call_label} hit {cached_tokens} cached prompt tokens")


def encode_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")


def encode_image_bytes_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string"""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def clean_json_response(raw_content: str) -> str:
    """Remove markdown code blocks from OpenAI response"""
    content = raw_content.strip()
    if content.startswith("```"):
        # Remove opening ```json or ```
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    return content.strip()


# ---------------------------------------------------------------------------
# B3 VISION-IDENTITY-V2 (session 80): ENABLE_VISION_IDENTITY_V2, default OFF,
# read PER CALL. Flag OFF, identify_products runs the V1 body below
# byte-for-byte (prompt, message layout, kwargs, normaliser); nothing in this
# block is read or touched. Flag ON, _identify_products_v2 sends a SECOND
# prompt with a strict json_schema response_format under a bounded wait_for
# and a SECOND normaliser (one best candidate per image_index, the internal
# underscore keys the camera route strips from every wire body).
# ---------------------------------------------------------------------------
_VISION_TIMEOUT_DEFAULT = 20.0
_VISION_V2_MAX_TOKENS = 1000
# The nine canonical keys in the order of the A2b classifier prompt
# (extraction_service._CLASSIFY_CATEGORY_LLM_PROMPT); pinned equal to
# extraction_service._CANONICAL_CATEGORIES by the B3 unit file.
VISION_CATEGORY_KEYS = (
    "electronics", "grocery", "supplements", "makeup", "skincare", "haircare",
    "fragrances", "fashion", "other",
)
VISION_V2_PUBLIC_KEYS = ("brand", "name", "size_or_count", "visible_price", "confidence")
VISION_V2_INTERNAL_KEYS = (
    "_image_index", "_category", "_product_type", "_distinguishing_features", "_is_product",
)
_VISION_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}
_VISION_FEATURE_MAX_CHARS = 80
_VISION_FEATURE_MAX_ITEMS = 8
_VISION_FINISH_REASONS = frozenset(
    ("stop", "length", "tool_calls", "content_filter", "function_call")
)

VISION_PROMPT_V2 = (
    "You are a product identification expert with OCR skills. The images are numbered "
    "from 0 in the order they are given (image_index 0 is the first image). Identify "
    "every distinct retail product visible in each image.\n"
    "\n"
    "CRITICAL: READ the EXACT text printed on each product's packaging, label or screen. "
    "Do NOT guess from memory or training data. Only report what you can actually SEE in "
    "the image.\n"
    "\n"
    "For EACH product found, give:\n"
    "- image_index: the 0-based number of the image the product appears in.\n"
    "- brand: the manufacturer or brand name as printed on the label, logo or packaging; "
    "null when no brand text is readable.\n"
    "- name: the FULL product name exactly as printed, including model numbers, variants "
    "and edition text (\"Vitamin D-3 5000 IU\", \"iPhone 16 Pro Max 256GB\"); null when no "
    "name text is readable.\n"
    "- category: one of " + ", ".join(VISION_CATEGORY_KEYS) + " -- or null when you "
    "cannot tell. This is the same category list the rest of the service uses.\n"
    "- product_type: a short noun for what the object is (\"perfume bottle\", \"wrist "
    "watch\", \"shirt\", \"vitamin bottle\", \"violin\").\n"
    "- size_or_count: the quantity, count, weight, volume or storage size printed on the "
    "package (\"360 Softgels\", \"1000mg\", \"128GB\", \"500ml\"); null if not visible.\n"
    "- visible_price: any price shown in the image (shelf tag, screen, label) with its "
    "currency symbol; null if not visible.\n"
    "- distinguishing_features: short phrases that tell this item from a similar one "
    "(colour, pattern, material, edition text, cap shape, bottle shape, printed slogan). "
    "Empty list if none.\n"
    "- is_product: true when the object is a retail product someone could buy; false for "
    "a person, an animal, furniture, a background object or a part of the room.\n"
    "- confidence: \"high\" (brand and name text clearly readable), \"medium\" (partially "
    "readable, some inference), \"low\" (little or no readable text).\n"
    "\n"
    "RULES:\n"
    "- READ the label text character by character -- exact numbers and units matter.\n"
    "- One image may contain MULTIPLE products: list each of them with the same "
    "image_index (up to 4 products in total across all images).\n"
    "- If a product has NO readable brand or name text, do NOT invent one from its shape, "
    "colour or design. Report what you can see, set the unreadable fields to null and set "
    "confidence to \"low\".\n"
    "- If the label is written in Arabic script, keep any Latin brand text as printed and "
    "transliterate the Arabic product name into Latin letters.\n"
    "- For supplements and vitamins read the EXACT count from the front label; for "
    "electronics the EXACT model and storage; for food and grocery the weight, volume or "
    "count.\n"
    "- For screenshots of retailer pages, extract the product name exactly as shown.\n"
    "- If a price tag sits next to a product, associate it with that product.\n"
    "- Return ONLY the JSON object described below, nothing else.\n"
    "\n"
    "Return a JSON object: {\"products\": [ { \"image_index\": 0, \"brand\": \"NOW\", "
    "\"name\": \"Vitamin D-3 5000 IU\", \"category\": \"supplements\", \"product_type\": "
    "\"vitamin bottle\", \"size_or_count\": \"360 Softgels\", \"visible_price\": "
    "\"BHD 8.50\", \"distinguishing_features\": [\"orange cap\", \"white bottle\"], "
    "\"is_product\": true, \"confidence\": \"high\" } ]}"
)


def _vision_nullable_string() -> Dict[str, Any]:
    return {"type": ["string", "null"]}


# Strict structured outputs (rulings B3-R6(4) / GB-3): the category branch is the
# documented strict subset -- anyOf [{string enum of the nine}, {null}] -- never
# an enum that itself carries null. Passed as a literal response_format kwarg
# (M1 forbids only literal temperature= / max_tokens=).
VISION_RESPONSE_FORMAT_V2 = {
    "type": "json_schema",
    "json_schema": {
        "name": "vision_products_v2",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["products"],
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "image_index", "brand", "name", "category", "product_type",
                            "size_or_count", "visible_price", "distinguishing_features",
                            "is_product", "confidence",
                        ],
                        "properties": {
                            "image_index": {"type": "integer"},
                            "brand": _vision_nullable_string(),
                            "name": _vision_nullable_string(),
                            "category": {
                                "anyOf": [
                                    {"type": "string", "enum": list(VISION_CATEGORY_KEYS)},
                                    {"type": "null"},
                                ]
                            },
                            "product_type": _vision_nullable_string(),
                            "size_or_count": _vision_nullable_string(),
                            "visible_price": _vision_nullable_string(),
                            "distinguishing_features": {
                                "type": "array", "items": {"type": "string"},
                            },
                            "is_product": {"type": "boolean"},
                            "confidence": {
                                "type": "string", "enum": ["high", "medium", "low"],
                            },
                        },
                    },
                },
            },
        },
    },
}


def vision_identity_v2_enabled() -> bool:
    """B3: True iff ENABLE_VISION_IDENTITY_V2 is truthy (default OFF).

    The house idiom, read PER CALL (never cached), so a Railway flip takes
    effect on the next request without a restart."""
    return os.getenv("ENABLE_VISION_IDENTITY_V2", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def vision_timeout_seconds() -> float:
    """B3: the V2 vision call bound, VISION_TIMEOUT_SECONDS (default 20.0 s).

    Read per call, and only inside the V2 branch (flag OFF never reads it).
    Unset / blank -> the default silently; garbage, inf, nan or <= 0 -> the
    default with one WARNING naming the variable (the text_routes knob form)."""
    raw = os.getenv("VISION_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _VISION_TIMEOUT_DEFAULT
    try:
        value = float(raw)
    except (TypeError, ValueError):
        logger.warning(
            "VISION_TIMEOUT_SECONDS=%r is not a number; using the %.1fs default",
            raw, _VISION_TIMEOUT_DEFAULT,
        )
        return _VISION_TIMEOUT_DEFAULT
    if not math.isfinite(value) or value <= 0:
        logger.warning(
            "VISION_TIMEOUT_SECONDS=%r is not a positive finite number; "
            "using the %.1fs default",
            raw, _VISION_TIMEOUT_DEFAULT,
        )
        return _VISION_TIMEOUT_DEFAULT
    return value


def public_vision_products(products) -> list:
    """B3: the wire copy of the vision products -- a NEW list of NEW dicts with
    every underscore-prefixed (internal) key removed; a non-dict item passes
    through; None -> []. Unconditional (no flag read): a V1 product carries no
    underscore key, so with the flag OFF the copy equals the original."""
    return [
        {k: v for k, v in p.items() if not str(k).startswith("_")} if isinstance(p, dict) else p
        for p in (products or [])
    ]


def _vision_v2_text(value) -> Optional[str]:
    """A stripped non-empty str, else None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _vision_v2_image_index(value, n_images: int) -> Optional[int]:
    """The int image_index when it names one of the request's images
    (0 <= value < n_images, a bool is not an int here), else None (unpaired,
    rulings B3-R6(3) / GB-1)."""
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < n_images:
        return value
    return None


def _vision_v2_features(value) -> List[str]:
    """distinguishing_features: the non-empty str items, stripped, each cut at
    80 characters, at most 8; anything that is not a list -> []."""
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item:
            continue
        out.append(item[:_VISION_FEATURE_MAX_CHARS])
        if len(out) >= _VISION_FEATURE_MAX_ITEMS:
            break
    return out


def _normalize_vision_products_v2(items: list, n_images: int):
    """B3: coerce the V2 reply's list items into product dicts.

    Returns (candidates, counts). A non-dict item is dropped
    (`dropped_non_dict`); a candidate whose `is_product` is False is dropped
    (`dropped_not_product`, ruling B3-R6(6)); an image_index that does not name
    one of the request's images is kept with `_image_index` None and counted
    (`unpaired_index`). `candidates` counts every list item (GB-4)."""
    # Lazy import (the module-level reload in test_m18_openai_tpm_sizing must
    # not pull extraction_service in at openai_service import time).
    from app.services.extraction_service import canonicalize_category

    counts = {
        "candidates": len(items),
        "dropped_not_product": 0,
        "unpaired_index": 0,
        "dropped_non_dict": 0,
    }
    candidates = []
    for item in items:
        if not isinstance(item, dict):
            counts["dropped_non_dict"] += 1
            continue
        is_product = item.get("is_product")
        if not isinstance(is_product, bool):
            # A lenient (V1-shaped) item without the key is a product.
            is_product = True
        if not is_product:
            counts["dropped_not_product"] += 1
            continue
        image_index = _vision_v2_image_index(item.get("image_index"), n_images)
        if image_index is None:
            counts["unpaired_index"] += 1
        confidence = item.get("confidence")
        confidence = confidence.strip().lower() if isinstance(confidence, str) else ""
        if confidence not in _VISION_CONFIDENCE_RANK:
            confidence = "low"
        raw_category = item.get("category")
        category = (
            canonicalize_category(raw_category)
            if isinstance(raw_category, str) and raw_category.strip()
            else None
        )
        candidates.append({
            "brand": _vision_v2_text(item.get("brand")) or "Unknown",
            "name": _vision_v2_text(item.get("name")) or "Unknown Product",
            "size_or_count": _vision_v2_text(item.get("size_or_count")),
            "visible_price": _vision_v2_text(item.get("visible_price")),
            "confidence": confidence,
            "_image_index": image_index,
            "_category": category,
            "_product_type": _vision_v2_text(item.get("product_type")),
            "_distinguishing_features": _vision_v2_features(item.get("distinguishing_features")),
            "_is_product": True,
        })
    return candidates, counts


def _select_vision_products_v2(candidates: list, n_images: int) -> list:
    """B3 selection: per paired image_index (ascending) keep the best candidate
    (highest confidence, ties keep the earlier); a ONE-image request keeps the
    best TWO of image_index 0 (ruling B3-R6(2)). Unpaired candidates follow in
    reply order (ruling B3-R6(3)). No count cap (GB-2)."""
    keep_per_index = 2 if n_images == 1 else 1
    by_index: Dict[int, list] = {}
    unpaired = []
    for cand in candidates:
        idx = cand["_image_index"]
        if idx is None:
            unpaired.append(cand)
        else:
            by_index.setdefault(idx, []).append(cand)
    kept = []
    for idx in sorted(by_index):
        # sorted() is stable, so equal confidence keeps reply order.
        ranked = sorted(
            by_index[idx], key=lambda c: _VISION_CONFIDENCE_RANK[c["confidence"]], reverse=True,
        )
        kept.extend(ranked[:keep_per_index])
    kept.extend(unpaired)
    return kept


def _vision_finish_label(finish_reason) -> str:
    """A log-safe finish_reason: the SDK literal, 'None', or a type name."""
    if finish_reason is None:
        return "None"
    if isinstance(finish_reason, str) and finish_reason in _VISION_FINISH_REASONS:
        return finish_reason
    return type(finish_reason).__name__


def _vision_usage_int(usage, name: str) -> int:
    value = getattr(usage, name, None) if usage is not None else None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _vision_image_parts(image_data_list: List[Dict]) -> List[Dict]:
    """The image parts of the vision message, in input order (the V1 layout)."""
    parts = []
    for img_data in image_data_list:
        if "path" in img_data:
            base64_image = encode_image_to_base64(img_data["path"])
            mime_type = "image/jpeg"
            if img_data["path"].lower().endswith(".png"):
                mime_type = "image/png"
        else:
            base64_image = encode_image_bytes_to_base64(img_data["bytes"])
            mime_type = img_data.get("mime_type", "image/jpeg")
        parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_image}", "detail": "auto"},
        })
    return parts


async def _identify_products_v2(image_data_list: List[Dict]) -> Dict:
    """B3: the V2 vision call (ENABLE_VISION_IDENTITY_V2 ON).

    Raises LLMUnavailableError on a refused / None / choice-less reply and
    TimeoutError on the VISION_TIMEOUT_SECONDS bound (the camera route serves
    both as its existing coded 503 LLM_UNAVAILABLE); a finish_reason=length
    reply or an unparsable one returns the V1-shaped parse-failure dict (the
    route's existing action:"error" exit). Log lines carry ints, bools, the
    finish_reason literal and the bound only -- never a product string."""
    content = [{"type": "text", "text": VISION_PROMPT_V2}]
    content.extend(_vision_image_parts(image_data_list))

    bound = vision_timeout_seconds()
    _vision_model = vision_model()
    try:
        response = await asyncio.wait_for(
            _llm_breaker.guarded_llm_create(
                client,
                model=_vision_model,
                messages=[{"role": "user", "content": content}],
                response_format=VISION_RESPONSE_FORMAT_V2,
                **token_limit_kwargs(_vision_model, _VISION_V2_MAX_TOKENS),
                **sampling_kwargs(_vision_model, 0),
            ),
            timeout=bound,
        )
    except asyncio.TimeoutError:
        logger.warning("[VISION_V2] vision call timed out after %.1fs", bound)
        raise
    _log_cache_telemetry(response, "identify_products")

    usage = getattr(response, "usage", None)
    tokens_used = _vision_usage_int(usage, "total_tokens")
    choices = getattr(response, "choices", None) or []
    choice = choices[0] if choices else None
    finish_reason = getattr(choice, "finish_reason", None)
    message = getattr(choice, "message", None)
    raw_content = getattr(message, "content", None)
    refusal = getattr(message, "refusal", None)
    finish_label = _vision_finish_label(finish_reason)

    if refusal or not isinstance(raw_content, str):
        logger.warning(
            "[VISION_V2] no content: finish_reason=%s refused=%s", finish_label, bool(refusal),
        )
        # The message stays free of the rate / quota words the verdict
        # fallback matcher keys on (LLMUnavailableError contract).
        raise _llm_breaker.LLMUnavailableError("vision returned no content")

    def _parse_failure(error: str) -> Dict:
        return {
            "products": [],
            "error": error,
            "raw_response": raw_content,
            "tokens_used": tokens_used,
            "cost": 0,
        }

    if finish_reason == "length":
        logger.warning("[VISION_V2] finish_reason=length; treating the reply as a parse failure")
        return _parse_failure("Failed to parse response: finish_reason=length")

    try:
        parsed = json.loads(clean_json_response(raw_content))
    except json.JSONDecodeError as e:
        return _parse_failure(f"Failed to parse response: {str(e)}")

    if isinstance(parsed, dict) and isinstance(parsed.get("products"), list):
        items = parsed["products"]
    elif isinstance(parsed, list):
        items = parsed
    else:
        return _parse_failure(
            f"Failed to parse response: unexpected shape {type(parsed).__name__}"
        )

    n_images = len(image_data_list)
    candidates, counts = _normalize_vision_products_v2(items, n_images)
    kept = _select_vision_products_v2(candidates, n_images)
    logger.info(
        "[VISION_V2] candidates=%d kept=%d dropped_not_product=%d unpaired_index=%d "
        "dropped_non_dict=%d unknown_brand=%d unknown_name=%d images=%d finish_reason=%s",
        counts["candidates"],
        len(kept),
        counts["dropped_not_product"],
        counts["unpaired_index"],
        counts["dropped_non_dict"],
        sum(1 for p in kept if p["brand"] == "Unknown"),
        sum(1 for p in kept if p["name"] == "Unknown Product"),
        n_images,
        finish_label,
    )

    # The V1 cost formula (gpt-4o-mini list price), tolerant of a missing usage.
    if usage is None:
        cost = 0.0
    else:
        input_cost = (_vision_usage_int(usage, "prompt_tokens") * 0.15) / 1_000_000
        output_cost = (_vision_usage_int(usage, "completion_tokens") * 0.60) / 1_000_000
        cost = round(input_cost + output_cost, 6)
    return {"products": kept, "tokens_used": tokens_used, "cost": cost}


async def identify_products(image_data_list: List[Dict]) -> Dict:
    """
    Use OpenAI Vision to identify products from images.

    Args:
        image_data_list: List of dicts with either:
            - {"path": "/path/to/image.jpg"} for file paths
            - {"bytes": b"...", "mime_type": "image/jpeg"} for raw bytes

    Returns:
        {
            "products": [
                {"brand": "Apple", "name": "iPhone 16 Pro", "visible_price": "BHD 449", "confidence": "high"},
                ...
            ],
            "tokens_used": 1234,
            "cost": 0.00056
        }
    """
    if vision_identity_v2_enabled():
        return await _identify_products_v2(image_data_list)

    # Build message content with images
    content = [
        {
            "type": "text",
            "text": """You are a product identification expert with OCR skills. Analyze these images and identify EVERY distinct product visible.

CRITICAL: READ the EXACT text printed on each product's packaging, label, or screen. Do NOT guess from memory or training data. Only report what you can actually SEE in the image.

For EACH product found, extract:
- brand: Manufacturer/brand name. Read it from the label/logo/packaging.
- name: The FULL product name exactly as printed on the packaging. Include model numbers, variants, and descriptors. "Vitamin D-3 5000 IU" not just "Vitamin D". "iPhone 16 Pro Max 256GB" not just "iPhone".
- size_or_count: The quantity, count, weight, volume, or storage size printed on the package. Examples: "360 Softgels", "1000mg", "128GB", "500ml", "2.5kg". null if not visible.
- visible_price: Any price shown in the image (shelf tag, screen, label). Include currency symbol. null if not visible.
- confidence: "high" (text clearly readable), "medium" (partially readable, some inference), "low" (best guess)

RULES:
- READ the label text character by character — exact numbers and units matter
- One image may contain MULTIPLE products — identify ALL (up to 4 total across all images)
- For supplements/vitamins: read the EXACT count from the front label (e.g., "360 Softgels", "120 Tablets", "250 Capsules")
- For electronics: read the EXACT model and storage/memory if visible (e.g., "Galaxy S25 Ultra 512GB")
- For food/grocery: read weight, volume, or count (e.g., "500g", "1L", "12 pack")
- Identify products even WITHOUT packaging: use shape, color, logo, design cues (confidence="low")
- For screenshots of retailer pages: extract the product name exactly as shown
- If you see a price tag next to a product, associate it with that product
- Do NOT include markdown code blocks
- Return ONLY a valid JSON array, nothing else

EXAMPLES:
[
  {"brand": "NOW", "name": "Vitamin D-3 5000 IU", "size_or_count": "360 Softgels", "visible_price": "BHD 8.50", "confidence": "high"},
  {"brand": "Apple", "name": "iPhone 16 Pro", "size_or_count": "256GB", "visible_price": null, "confidence": "medium"}
]"""
        }
    ]
    
    # Add images to content
    for img_data in image_data_list:
        if "path" in img_data:
            base64_image = encode_image_to_base64(img_data["path"])
            mime_type = "image/jpeg"  # Default
            if img_data["path"].lower().endswith(".png"):
                mime_type = "image/png"
        else:
            base64_image = encode_image_bytes_to_base64(img_data["bytes"])
            mime_type = img_data.get("mime_type", "image/jpeg")
        
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}",
                "detail": "auto"  # "auto" lets GPT choose resolution — needed for reading label text
            }
        })
    
    # Call OpenAI Vision API
    _vision_model = vision_model()
    response = await _llm_breaker.guarded_llm_create(client,
        model=_vision_model,
        messages=[{"role": "user", "content": content}],
        **token_limit_kwargs(_vision_model, 500),
        # Deterministic output. Omitted automatically for GPT-5-family ids,
        # which reject a non-default temperature.
        **sampling_kwargs(_vision_model, 0),
    )
    _log_cache_telemetry(response, "identify_products")

    # Parse response
    raw_content = response.choices[0].message.content
    clean_content = clean_json_response(raw_content)
    
    try:
        products = json.loads(clean_content)
    except json.JSONDecodeError as e:
        # If parsing fails, return error info
        return {
            "products": [],
            "error": f"Failed to parse response: {str(e)}",
            "raw_response": raw_content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "cost": 0
        }

    # Normalize: ensure each product has all expected fields
    normalized = []
    for p in (products if isinstance(products, list) else []):
        normalized.append({
            "brand": p.get("brand") or "Unknown",
            "name": p.get("name") or "Unknown Product",
            "size_or_count": p.get("size_or_count"),
            "visible_price": p.get("visible_price"),
            "confidence": p.get("confidence", "medium"),
        })

    # Calculate cost (gpt-4o-mini pricing)
    # Input: $0.15 per 1M tokens, Output: $0.60 per 1M tokens
    usage = response.usage
    input_cost = (usage.prompt_tokens * 0.15) / 1_000_000
    output_cost = (usage.completion_tokens * 0.60) / 1_000_000
    total_cost = input_cost + output_cost

    return {
        "products": normalized,
        "tokens_used": usage.total_tokens,
        "cost": round(total_cost, 6)
    }


def _coerce_name_part(value) -> str:
    """W4-11 (R25): the unflagged name fence never raises. None -> '' (R3), a str
    stays as is, a list/tuple -> the str() of its items joined by one space, any
    other scalar -> str(value); only then is it sanitised."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value)
    return str(value)


def _sanitized_full_name(brand, name, variant) -> str:
    """W4-11 (A, R3, R25): parts coerced to str first, then tags neutralized, controls
    stripped, whitespace collapsed so a product name can never add a line to (or close
    a region in) the system prompt."""
    return " ".join(
        f"{sanitize_prompt_input(_coerce_name_part(brand))} {sanitize_prompt_input(_coerce_name_part(name))} {sanitize_prompt_input(_coerce_name_part(variant or ''))}".split()
    )


async def extract_specs_targeted(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    fields: List[str],
    context: str,
) -> Dict[str, Any]:
    """Extract a small set of specified fields from a focused context.

    Used by smart-fallback when primary spec extraction left critical
    fields null. Returns dict of {field: value} for fields it could fill.
    """
    if not fields:
        return {}

    from app.services.extraction_service import SEARCH_RESULTS_GUARD, _wrap_search_context

    fields_json = ",\n    ".join(f'"{f}": null' for f in fields)
    full_name = _sanitized_full_name(brand, name, variant)

    system = SEARCH_RESULTS_GUARD + "\n\n" + f"""Extract these specific fields for {full_name} from the snippets below.
Return ONLY valid JSON with these exact keys:
{{
    {fields_json}
}}

Rules:
- For each field, give a single short value (e.g. '12 MP', 'IP68', 'Snapdragon 8 Gen 3')
- If you cannot find or know the value, return null for that field
- NEVER return the literal string 'N/A' - return null instead
- Use your training data as a fallback when snippets are silent"""

    user = f"SNIPPETS:\n{_wrap_search_context(context)}\n\nReturn JSON for: {fields}"

    try:
        client_local = get_client()
        _model = standard_model()
        response = await _llm_breaker.guarded_llm_create(client_local,
            model=_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            **sampling_kwargs(_model, 0.1),
            **token_limit_kwargs(_model, 200),
        )
        _log_cache_telemetry(response, "extract_specs_targeted")
        content = response.choices[0].message.content
        result = json.loads(content) if content else {}
        # Filter to only requested fields, drop nulls + literal "N/A"
        # (defensive: prompt forbids "N/A" but GPT can still echo it).
        return {
            k: v for k, v in result.items()
            if k in fields and v is not None and v != "N/A"
        }
    except Exception as e:
        logger.warning(f"[EXTRACT_TARGETED] Failed: {e}")
        return {}


async def extract_specs_synthesized(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    fields: List[str],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Bundle D A.4.8 — Tier 3 batched synthesis (NO context).

    Last-resort fallback when Tier 1 + smart-fallback + Tier 2 all left
    non-negotiable schema fields blank. Uses the higher-capacity model
    (gpt-4o by default, routed via `model_router.get_model(priority='high')`)
    to synthesize values directly from training-data knowledge — no
    Serper search, no snippet context.

    Returns dict of {field: value} for fields the model could fill from
    training data. Caller marks each filled field as
    confidence='tier3_synthesis' so trust validation downstream can flag
    these as inferred rather than retrieved.

    Cost: one call per product, max_tokens=300, ~$0.001-0.005 with
    priority='high' routing. Only fires when Tier 2 also failed (rare).
    """
    if not fields:
        return {}

    fields_json = ",\n    ".join(f'"{f}": null' for f in fields)
    full_name = _sanitized_full_name(brand, name, variant)

    system = f"""You are a product specifications expert. Synthesize these specific fields for {full_name} from your training-data knowledge.
Return ONLY valid JSON with these exact keys:
{{
    {fields_json}
}}

Rules:
- For each field, give a single short value (e.g. '12 MP', 'IP68', 'Snapdragon 8 Gen 3')
- If you genuinely do not know a value, return null for that field — DO NOT guess
- NEVER return the literal string 'N/A' — return null instead
- Prefer high-confidence values from manufacturer documentation
- This is a last-resort fallback; accuracy matters more than completeness"""

    user = f"Synthesize JSON for category={category}, fields={fields}"

    try:
        client_local = get_client()
        # None means "the configured verdict model" — callers that pass an
        # explicit id (structured_comparison_service routes one in from
        # model_router) are unaffected.
        _model = model or verdict_model()
        response = await _llm_breaker.guarded_llm_create(client_local,
            model=_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            **sampling_kwargs(_model, 0.1),
            **token_limit_kwargs(_model, 300),
        )
        _log_cache_telemetry(response, "extract_specs_synthesized")
        content = response.choices[0].message.content
        result = json.loads(content) if content else {}
        return {
            k: v for k, v in result.items()
            if k in fields and v is not None and v != "N/A"
        }
    except Exception as e:
        logger.warning(f"[EXTRACT_SYNTH] Failed: {e}")
        return {}


async def disambiguate_variant_line(
    category: Optional[str],
    query: str,
    candidate_title: str,
    axis: str,
) -> Dict[str, Any]:
    """genuine-price Wave-2 B3b — the NARROW off-clock product-line disambiguator.

    Answers, for a single ambiguous variant axis (gender / spf / formula), whether
    `candidate_title` is a DISTINCT product line from `query` (a different SKU at a
    different price) or the SAME product with a descriptive suffix. Used ONLY by the
    off-clock warmer cache-write veto, and ONLY after the deterministic curated
    reference (data/variant_hint_reference.json) missed. NEVER on the live 15s path
    (the caller gates on the warm signal + ENABLE_VARIANT_LLM_HINT before ever
    constructing the client).

    gpt-4o-mini, temperature=0, response_format json_object (house shape). Returns:
        {"distinct_product": True|False|"unknown",
         "confidence": "high"|"low",
         "cost": float}
    Any client/parse error -> {"distinct_product": "unknown", "confidence": "low",
    "cost": 0.0} so the caller fail-closes (vetoes the write). No exception escapes."""
    system = "Product-catalog disambiguator. STRICT JSON only."
    user = json.dumps({
        "category": category,
        "query": query,
        "candidate_title": candidate_title,
        "axis": axis,
        "question": (
            "is the candidate a DISTINCT product line from the query "
            "(different SKU/price), or the same product with a descriptive suffix?"
        ),
        "respond_with": {
            "distinct_product": "true|false|unknown",
            "confidence": "high|low",
        },
    })
    try:
        client_local = get_client()
        _model = standard_model()
        response = await _llm_breaker.guarded_llm_create(client_local,
            model=_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            **sampling_kwargs(_model, 0),
            **token_limit_kwargs(_model, 60),
        )
        _log_cache_telemetry(response, "disambiguate_variant_line")
        content = response.choices[0].message.content
        parsed = json.loads(content) if content else {}
        if not isinstance(parsed, dict):
            return {"distinct_product": "unknown", "confidence": "low", "cost": 0.0}

        raw_distinct = parsed.get("distinct_product")
        if isinstance(raw_distinct, bool):
            distinct: Any = raw_distinct
        elif isinstance(raw_distinct, str):
            low = raw_distinct.strip().lower()
            if low == "true":
                distinct = True
            elif low == "false":
                distinct = False
            else:
                distinct = "unknown"
        else:
            distinct = "unknown"

        conf = str(parsed.get("confidence") or "").strip().lower()
        if conf not in ("high", "low"):
            conf = "low"

        cost = 0.0
        usage = getattr(response, "usage", None)
        if usage is not None:
            input_cost = (getattr(usage, "prompt_tokens", 0) * 0.15) / 1_000_000
            output_cost = (getattr(usage, "completion_tokens", 0) * 0.60) / 1_000_000
            cost = round(input_cost + output_cost, 6)

        return {"distinct_product": distinct, "confidence": conf, "cost": cost}
    except Exception as e:  # noqa: BLE001 — hint is additive; fail-closed on any error
        logger.warning(f"[VARHINT] disambiguate_variant_line failed: {e}")
        return {"distinct_product": "unknown", "confidence": "low", "cost": 0.0}

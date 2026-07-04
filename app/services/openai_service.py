"""
OpenAI Service - Vision and text processing for product comparison
"""
import json
import base64
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Initialize async client (reads OPENAI_API_KEY from env at request time).
# Explicit timeout: 30s connect (Railway networking can be slow), 120s total.
# This module-level singleton is kept for back-compat with existing call sites.
client = AsyncOpenAI(timeout=httpx.Timeout(120.0, connect=30.0))

# Memoised per-project clients for the dual-project routing in
# select_client_for_user. Filled lazily by get_client(); resolved against
# OPENAI_API_KEY (shared, default) and OPENAI_API_KEY_PRIVATE (non-shared,
# PDPL opt-out). When the private key isn't configured we fall back to the
# shared client — the API contract still holds.
_client_cache: Dict[bool, AsyncOpenAI] = {}


def get_client(use_shared_project: bool = True) -> AsyncOpenAI:
    """Return the OpenAI async client for the requested project.

    Args:
        use_shared_project: True (default) routes through the data-sharing
            project (free under daily caps). False routes through the
            non-shared project at standard pricing — used when a user opts
            out of the AI Quality Improvement Program (design 6.1).
    """
    cached = _client_cache.get(use_shared_project)
    if cached is not None:
        return cached

    if use_shared_project:
        # Shared (default). Existing OPENAI_API_KEY env handles this.
        new_client = AsyncOpenAI(timeout=httpx.Timeout(120.0, connect=30.0))
    else:
        # Private. Fall back to default key if a separate one isn't set —
        # acceptable on day 1; the routing API stays correct.
        private_key = os.getenv("OPENAI_API_KEY_PRIVATE") or os.getenv("OPENAI_API_KEY")
        new_client = AsyncOpenAI(
            api_key=private_key,
            timeout=httpx.Timeout(120.0, connect=30.0),
        )
    _client_cache[use_shared_project] = new_client
    return new_client


def select_client_for_user(user_prefs: Optional[Dict[str, Any]] = None) -> AsyncOpenAI:
    """Select shared vs non-shared OpenAI client based on the user's PDPL toggle.

    Default ON: anonymous calls and users without an explicit preference go
    through the shared (data-sharing) project. When the user has explicitly
    set ``ai_sharing_enabled = False`` we route through the private client.
    """
    if user_prefs is not None and user_prefs.get("ai_sharing_enabled") is False:
        return get_client(use_shared_project=False)
    return get_client(use_shared_project=True)


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
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": content}],
        max_tokens=500,
        temperature=0  # Deterministic output
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

    fields_json = ",\n    ".join(f'"{f}": null' for f in fields)
    full_name = f"{brand} {name} {variant or ''}".strip()

    system = f"""Extract these specific fields for {full_name} from the snippets below.
Return ONLY valid JSON with these exact keys:
{{
    {fields_json}
}}

Rules:
- For each field, give a single short value (e.g. '12 MP', 'IP68', 'Snapdragon 8 Gen 3')
- If you cannot find or know the value, return null for that field
- NEVER return the literal string 'N/A' - return null instead
- Use your training data as a fallback when snippets are silent"""

    user = f"SNIPPETS:\n{context}\n\nReturn JSON for: {fields}"

    try:
        client_local = get_client()
        response = await client_local.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200,
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
    model: str = "gpt-4o",
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
    full_name = f"{brand} {name} {variant or ''}".strip()

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
        response = await client_local.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=300,
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
        response = await client_local.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=60,
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

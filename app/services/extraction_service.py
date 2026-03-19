"""
Structured Extraction Service - Extract structured product data with optimized prompts
"""
from dotenv import load_dotenv
load_dotenv(override=True)  # Load .env FIRST before anything else

import os
import json
import hashlib
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Lazy initialization - don't create client at import time
_client = None

def get_client() -> AsyncOpenAI:
    """Get OpenAI client (lazy initialization)"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"Initializing OpenAI client with key ending in: ...{api_key[-10:] if api_key else 'NONE'}")
        _client = AsyncOpenAI(api_key=api_key, timeout=httpx.Timeout(120.0, connect=30.0))
    return _client

# GCC Region mappings
GCC_REGIONS = {
    "bahrain": {"code": "bh", "currency": "BHD", "lang": "en"},
    "saudi_arabia": {"code": "sa", "currency": "SAR", "lang": "en"},
    "uae": {"code": "ae", "currency": "AED", "lang": "en"},
    "kuwait": {"code": "kw", "currency": "KWD", "lang": "en"},
    "qatar": {"code": "qa", "currency": "QAR", "lang": "en"},
    "oman": {"code": "om", "currency": "OMR", "lang": "en"},
}


# ============================================
# PROMPT TEMPLATES
# ============================================

PRODUCT_PARSER_PROMPT = """You are a product parsing expert. Extract product information from user queries.

INPUT: "{query}"

Extract and return ONLY valid JSON (no markdown, no explanation):
{{
    "products": [
        {{
            "brand": "brand name",
            "name": "product name",
            "variant": "variant/size if mentioned (e.g., 128GB, Pro, 2.5kg)",
            "category": "electronics|grocery|supplements|makeup|skincare|haircare|fragrances|fashion|other",
            "search_query": "optimized search query for this product"
        }}
    ],
    "comparison_type": "price|specs|general",
    "region_hint": "detected region or null"
}}

RULES:
- Extract ALL products mentioned (typically 2 for comparison)
- Normalize brand names (e.g., "iphone" → "Apple", "galaxy" → "Samsung")
- Include variant if specified (storage, size, color, etc.)
- search_query should be specific for price searches
- Category detection — match based on PRODUCT TYPE, not brand:
  * electronics: phones, laptops, TVs, cameras, headphones, tablets, consoles, smartwatches
  * grocery: food, beverages, household items, cleaning products
  * supplements: vitamins, minerals, health supplements, protein powder
  * makeup: foundation, lipstick, mascara, eyeshadow, concealer, blush, primer
  * skincare: moisturizer, serum, cleanser, sunscreen, toner, face wash
  * haircare: shampoo, conditioner, hair treatment, styling products, hair oil
  * fragrances: perfume, cologne, eau de toilette, eau de parfum, body spray
  * fashion: hats, caps, bags, handbags, shoes, sneakers, jackets, coats, scarves, belts, wallets, clothing, dresses, watches, jewelry, sunglasses
  * other: anything not fitting above categories
- IMPORTANT: Category is determined by PRODUCT TYPE, never by brand. An LV hat is fashion. A Chanel perfume is fragrances. A Rolex watch is fashion.
- Return valid JSON only"""


CATEGORY_SPEC_SCHEMAS = {
    "electronics": [
        "display", "processor", "ram", "storage", "battery",
        "rear_camera", "front_camera", "os", "connectivity",
        "weight", "water_resistance"
    ],
    "grocery": [
        "count", "size", "ingredients", "nutrition_calories", "nutrition_protein",
        "nutrition_fat", "nutrition_carbs", "origin", "organic",
        "allergens", "shelf_life"
    ],
    "supplements": [
        "count", "serving_size", "active_ingredient", "dosage",
        "form", "allergens", "certifications", "origin",
        "organic", "shelf_life", "nutrition_calories"
    ],
    "other": [
        "dimensions", "weight", "material", "color",
        "features", "origin", "warranty"
    ],

    # Beauty & Personal Care
    "makeup": [
        "shade_range",      # e.g., "50 shades", "Light to Deep"
        "finish",           # matte, glossy, satin, dewy
        "coverage",         # sheer, medium, full
        "skin_type",        # oily, dry, combination, sensitive
        "ingredients",      # key ingredients list
        "cruelty_free",     # yes/no
        "vegan",            # yes/no
        "spf",              # sun protection factor
        "volume",           # ml/oz
        "waterproof",       # yes/no
        "long_lasting",     # hours or yes/no
    ],

    "skincare": [
        "skin_type",           # oily, dry, combination, sensitive
        "skin_concern",        # acne, aging, hydration, brightening
        "ingredients",         # key ingredients
        "active_ingredient",   # retinol, vitamin C, niacinamide, etc.
        "spf",                 # sun protection factor
        "fragrance_free",      # yes/no
        "cruelty_free",        # yes/no
        "vegan",               # yes/no
        "volume",              # ml/oz
        "ph_level",            # pH balance
    ],

    "haircare": [
        "hair_type",        # straight, wavy, curly, coily
        "hair_concern",     # frizz, damage, volume, color-treated
        "ingredients",      # key ingredients
        "sulfate_free",     # yes/no
        "paraben_free",     # yes/no
        "silicone_free",    # yes/no
        "cruelty_free",     # yes/no
        "vegan",            # yes/no
        "volume",           # ml/oz
        "scent",            # fragrance description
    ],

    "fragrances": [
        "scent_family",     # floral, woody, oriental, fresh, etc.
        "notes_top",        # top notes (first impression)
        "notes_heart",      # heart/middle notes (main character)
        "notes_base",       # base notes (lasting impression)
        "longevity",        # hours of wear
        "sillage",          # projection (soft, moderate, strong)
        "season",           # spring, summer, fall, winter, all-season
        "occasion",         # day, evening, formal, casual
        "volume",           # ml/oz
        "concentration",    # eau de toilette, eau de parfum, parfum
    ],

    "fashion": [
        "material",           # e.g., "100% cotton", "cashmere", "leather"
        "style",              # e.g., "five-panel cap", "tote bag", "low-top sneaker"
        "closure_type",       # e.g., "adjustable back strap", "zip", "snap"
        "size_options",       # e.g., "S/M/L", "One size", "36-44"
        "care_instructions",  # e.g., "Dry clean only", "Machine wash"
        "craftsmanship",      # e.g., "Hand-stitched", "Machine-made"
        "collection_season",  # e.g., "Spring/Summer 2025", "Permanent collection"
        "origin",             # e.g., "Made in Italy", "Made in France"
        "color",              # e.g., "Light Grey", "Black"
        "design_details",     # e.g., "Embroidered LV monogram, mesh back panel"
    ],
}


def _build_specs_prompt(brand: str, name: str, variant: str, category: str, search_context: str, drug_context: str = "") -> str:
    schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
    fields = CATEGORY_SPEC_SCHEMAS[schema_key]

    fields_json = ",\n    ".join(f'"{f}": null' for f in fields)

    variant_note = f'(variant: {variant})' if variant else '(base model)'

    return f"""You are a product specifications expert. Extract specs for ONE specific configuration of this product.

PRODUCT: {brand} {name} {variant_note}
CATEGORY: {category}

Search results for context:
{search_context}
{drug_context}

Return ONLY valid JSON (no markdown) with EXACTLY these fields:
{{
    "brand": "{brand}",
    "model": "{name}",
    "variant": "{variant}",
    "category": "{category}",
    {fields_json}
}}

CRITICAL RULES:
- Extract specs for ONE specific unit — the base/standard model unless a variant is specified
- Each field must be a SINGLE value, NEVER a list of options (e.g. storage: "128 GB" NOT "128, 256, 512 GB")
- If the user specified a variant like "512GB", use that config. Otherwise use the base/entry-level config
- If the product name or variant contains a count/quantity (e.g. "360 Softgels", "120 tablets", "1000mg"), use EXACTLY that number for the "count" field. Do NOT substitute a different count
- Only include fields that are GENUINELY RELEVANT to this specific product. Omit irrelevant fields rather than writing N/A or null. A hat does not need "power". A phone does not need "care_instructions". Use search results first, then your training knowledge.
- For well-known products, you KNOW the specs — do NOT return null for fields that clearly apply (e.g. os, weight, water_resistance for smartphones)
- Be precise with numbers and units
- Include ONLY the fields listed above, plus the _source citation fields described below
- ONLY functional specs — NO launch price, MSRP, release date, or marketing names
- For connectivity: list supported standards (e.g. "Wi-Fi 6, 5G, Bluetooth 5.3, NFC")
- Keep each value short and factual (e.g. "6.1-inch Super Retina XDR OLED" not a paragraph)
- For well-known products (iPhones, Galaxy, Pixel, etc.) you KNOW the specs — do NOT return null for basic fields like os, weight, or water_resistance
- For EACH spec field, also include a "{{field}}_source" field with the snippet number (e.g. "snippet_1") where you found this value, or "training" if from your own knowledge
- Example: "battery": "4422 mAh", "battery_source": "snippet_2"
- The _source field should reference the [snippet_N] labels shown in the search results above
- Category-specific guidance:
  * Electronics: include all tech specs (display, processor, ram, storage, battery, camera)
  * Fashion: focus on material, style, craftsmanship, origin, design_details. Skip irrelevant fields.
  * Supplements: include count, dosage, form, certifications. Skip tech fields.
  * Fragrances: include scent notes, longevity, sillage, concentration. Skip tech fields."""


PRICE_EXTRACTION_PROMPT = """You are a price extraction expert for GCC markets. Your goal is to find the MOST AUTHORITATIVE retail price, not the cheapest one.

PRODUCT: {brand} {name} {variant}
REGION: {region} ({currency})

Search results:
{search_context}

Return ONLY valid JSON:
{{
    "amount": numeric_price_or_null,
    "original_currency": "USD",
    "currency": "{currency}",
    "retailer": null,
    "url": null,
    "in_stock": true,
    "confidence": 0.0
}}

SOURCE PRIORITY (use the HIGHEST available):
1. Official brand website (hermes.com, louisvuitton.com, apple.com, chanel.com) — ALWAYS prefer this
2. Authorized retailers (Nordstrom, Sephora, Harrods, Farfetch, SSENSE, Net-a-Porter, Amazon)
3. Major GCC retailers (Noon, Jarir, Extra, Sharaf DG, LuLu)
4. Resellers (eBay, StockX, TheRealReal) — ONLY if nothing else available, flag confidence 0.3
5. NEVER use: DHgate, AliExpress, Temu, Wish — these sell counterfeits

RULES:
- Extract the MOST AUTHORITATIVE price, NOT the lowest. A $630 price from hermes.com is correct; a $94 price from eBay is likely counterfeit/resale.
- Do NOT convert currencies — return the exact price as shown in the source
- original_currency: the ACTUAL currency of the price you found (detect from symbols: $ = USD, £ = GBP, € = EUR, BHD/BD = BHD, SAR/SR = SAR, AED = AED, KWD = KWD)
- currency: always set to "{currency}" (the target currency — conversion happens later)
- Confidence: 1.0 = official brand/authorized retailer, 0.7 = major marketplace, 0.3 = reseller, 0.0 = not found
- Return null for amount if no reliable price found from Priority 1-3 sources
- retailer: the actual store name, or null if unknown

DO: Extract $630 from hermes.com (official brand site)
DON'T: Extract $94 from eBay reseller listing — that's counterfeit/resale pricing

DO: Extract $999 from apple.com or $999 from Amazon (both authorized)
DON'T: Extract $750 from unknown electronics reseller

DO: Extract BHD 8.500 from iherb.com (authorized supplement retailer)
DON'T: Extract BHD 2.000 from unverified supplement seller"""


PRICE_FALLBACK_PROMPT = """You are a price estimation expert. The product below could NOT be found in any current retailer listing.
Provide your BEST ESTIMATE of its current retail price from your training data.

PRODUCT: {brand} {name} {variant}
REGION: {region} ({currency})

Return ONLY valid JSON:
{{
    "amount": numeric_estimated_price,
    "original_currency": "USD",
    "currency": "{currency}",
    "retailer": null,
    "confidence": 0.5,
    "note": "Estimated from training data"
}}

RULES:
- Give your best estimate of the current retail price in USD (most training data uses USD)
- original_currency: set to the currency you are estimating in (usually "USD")
- currency: always set to "{currency}" (the target currency — conversion happens later)
- Do NOT attempt to convert currencies yourself — just report the price and original_currency
- This is a LAST RESORT — clearly mark confidence as 0.5
- NEVER return null for amount — always provide an estimate"""


REVIEWS_EXTRACTION_PROMPT = """You are a review analysis expert. Extract a FACTUAL review analysis for this product using ONLY the search results provided.

PRODUCT: {brand} {name} {variant}
CATEGORY: {category}

Search results and retailer data:
{search_context}

Return ONLY valid JSON:
{{
    "average_rating": 0.0-5.0 or null,
    "total_reviews": estimated_count or null,
    "positive_percentage": 0-100 or null,
    "rating_distribution": null,
    "category_scores": {{
        "aspect_name": score_out_of_10
    }},
    "common_praises": ["[snippet_N] specific praise with evidence"],
    "common_complaints": ["[snippet_N] specific complaint with evidence"],
    "detailed_praises": [
        {{"text": "specific praise", "frequency": "how often mentioned", "source": "snippet_N"}}
    ],
    "detailed_complaints": [
        {{"text": "specific complaint", "frequency": "how often mentioned", "source": "snippet_N"}}
    ],
    "user_quotes": [
        {{"text": "exact words from snippet", "sentiment": "positive|negative|mixed", "source": "snippet_N", "aspect": "what aspect it covers"}}
    ],
    "summary": "2-3 sentence specific, opinionated summary"
}}

RULES:
- EVERY praise and complaint MUST cite its source as [snippet_N] — if you cannot cite a snippet, do NOT include the claim
- category_scores: pick 4-6 aspects relevant to the product category (e.g. for phones: camera, battery, display, performance, value, build quality). Score 1-10 based on review consensus from snippets
- common_praises/common_complaints: prefix each with [snippet_N] citation. 3-5 items each
- detailed_praises/detailed_complaints: MUST include "source" field referencing the snippet
- user_quotes: extract 3-5 EXACT phrases from the search snippets — actual words as written. Do NOT paraphrase, invent, or fabricate quotes
- rating_distribution: always set to null — real distribution data is injected separately
- DO NOT generate source_ratings — retailer ratings are injected separately from real data
- summary: be SPECIFIC and opinionated, referencing actual findings from snippets

DO: "[snippet_3] Battery drains to 20% by 3pm with heavy camera use"
DON'T: "Battery life could be better" (too vague, no citation)

DO: "[snippet_1] 48MP main sensor captures sharp detail in low light"
DON'T: "Great camera quality" (generic, no evidence)

- Return null/empty for fields without reliable data from the provided snippets"""


COMPARISON_PROMPT = """You are a product comparison expert. Compare these products with SPECIFIC, DATA-BACKED analysis. Be decisive — users want a clear answer, not fence-sitting.

PRODUCT 1:
{product1_json}

PRODUCT 2:
{product2_json}

User's region: {region}
Primary concern: {concern}

Return ONLY valid JSON:
{{
    "winner_index": 0 or 1,
    "winner_reason": "clear 1-sentence reason with a specific number or fact",
    "product_0_pros": ["specific pro with number/fact", "..."],
    "product_0_cons": ["specific con with number/fact", "..."],
    "product_1_pros": ["specific pro with number/fact", "..."],
    "product_1_cons": ["specific con with number/fact", "..."],
    "price_comparison": {{
        "cheaper_index": 0 or 1,
        "price_difference": "X {currency} (Y%)",
        "better_value_index": 0 or 1
    }},
    "specs_comparison": {{
        "product_0_advantages": ["advantage with specific number"],
        "product_1_advantages": ["advantage with specific number"],
        "similar": ["shared feature"]
    }},
    "value_scores": [0.0-10.0, 0.0-10.0],
    "best_for": {{
        "budget": 0 or 1,
        "performance": 0 or 1,
        "features": 0 or 1,
        "reliability": 0 or 1
    }},
    "recommendation": "2-3 sentence decisive recommendation",
    "key_differences": [
        "difference 1 with numbers",
        "difference 2 with numbers",
        "difference 3 with numbers",
        "difference 4 with numbers",
        "difference 5 with numbers"
    ],
    "personalized_insights": [
        {{{{
            "focus_area": "user priority area (e.g., battery_life, price, camera)",
            "product_index": 0 or 1,
            "insight": "1-2 sentence insight with specific number (max 200 chars)"
        }}}}
    ]
}}

RULES:
- 4-6 pros, 2-4 cons per product — each MUST include a specific number, percentage, or measurable fact
- DO: "50% larger battery (5000 vs 3274 mAh) means 2+ hours more screen-on time"
- DON'T: "Better battery life" (vague, no numbers)
- DO: "15% cheaper at $799 vs $949 while matching camera quality"
- DON'T: "Good value for money" (meaningless without numbers)
- winner_reason MUST cite the single most important numeric advantage
- recommendation MUST state: who should buy Product 1, who should buy Product 2, and the specific trade-off between them
- key_differences: each must include actual specs/numbers, not generic descriptions
- Consider price-to-value ratio heavily for GCC market
- Value score: 10 = exceptional value, 5 = average, 1 = poor value
- Be DECISIVE — pick a clear winner and defend it with data
- personalized_insights: Generate ONLY when personalization context is provided. 2-3 insights, each tied to a different user priority. Each must cite a specific number. If no personalization context, omit this field entirely."""


# ============================================
# EXTRACTION FUNCTIONS
# ============================================

async def parse_product_query(query: str) -> Dict[str, Any]:
    """
    Parse a natural language query to extract product information.
    
    Examples:
    - "iPhone 15 vs S24" → [iPhone 15, Samsung S24]
    - "compare Nido 2.5kg with Almarai milk" → [Nido 2.5kg, Almarai milk]
    """
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": PRODUCT_PARSER_PROMPT.format(query=query)}
            ],
            max_tokens=500,
            temperature=0.1,  # Low temperature for consistency
        )
        
        result = response.choices[0].message.content.strip()

        # Clean markdown if present
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        return json.loads(result), usage

    except Exception as e:
        logger.error(f"Product parsing error: {e}")
        return {"products": [], "error": str(e)}, {"prompt_tokens": 0, "completion_tokens": 0}


async def extract_specs(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    search_context: str,
    drug_context: str = ""
) -> Dict[str, Any]:
    """Extract structured specifications for a product, enforcing a fixed schema."""
    try:
        client = get_client()
        prompt = _build_specs_prompt(
            brand, name, variant or "", category,
            search_context[:3000],
            drug_context=drug_context
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.1,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        raw = json.loads(result)

        # Enforce schema: only keep fields in the category schema + meta keys + _source citations
        schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
        allowed_fields = set(CATEGORY_SPEC_SCHEMAS[schema_key])
        meta_keys = {"brand", "model", "variant", "category"}

        cleaned = {}
        for key in list(meta_keys) + CATEGORY_SPEC_SCHEMAS[schema_key]:
            val = raw.get(key)
            if key in meta_keys:
                cleaned[key] = val
            elif val is None or val == "" or val == "null" or (isinstance(val, str) and "or null" in val.lower()):
                cleaned[key] = "N/A"
            elif isinstance(val, list):
                cleaned[key] = ", ".join(str(v) for v in val)
            else:
                cleaned[key] = str(val)

        # Preserve _source citation fields from GPT response (used for fact-checking)
        for key in CATEGORY_SPEC_SCHEMAS[schema_key]:
            source_key = f"{key}_source"
            source_val = raw.get(source_key)
            if source_val and isinstance(source_val, str):
                cleaned[source_key] = source_val

        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        return cleaned, usage

    except Exception as e:
        logger.error(f"Specs extraction error: {e}")
        return {"brand": brand, "model": name, "error": str(e)}, {"prompt_tokens": 0, "completion_tokens": 0}


async def extract_price(
    brand: str,
    name: str,
    variant: Optional[str],
    region: str,
    search_context: str
) -> Dict[str, Any]:
    """Extract price for a specific GCC region."""
    region_info = GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])
    
    try:
        client = get_client()
        prompt = PRICE_EXTRACTION_PROMPT.format(
            brand=brand,
            name=name,
            variant=variant or "",
            region=region,
            currency=region_info["currency"],
            search_context=search_context[:2000]
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        return json.loads(result), usage

    except Exception as e:
        logger.error(f"Price extraction error: {e}")
        return {"amount": None, "currency": region_info["currency"], "error": str(e)}, {"prompt_tokens": 0, "completion_tokens": 0}


async def extract_price_from_training_data(
    brand: str,
    name: str,
    variant: Optional[str],
    region: str,
) -> Dict[str, Any]:
    """Last-resort: ask GPT for an estimated price from training data."""
    region_info = GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])
    try:
        client = get_client()
        prompt = PRICE_FALLBACK_PROMPT.format(
            brand=brand,
            name=name,
            variant=variant or "",
            region=region,
            currency=region_info["currency"],
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
        )
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        return json.loads(result), usage
    except Exception as e:
        logger.error(f"Price fallback error: {e}")
        return {"amount": None, "currency": region_info["currency"], "error": str(e)}, {"prompt_tokens": 0, "completion_tokens": 0}


async def extract_reviews(
    brand: str,
    name: str,
    variant: Optional[str],
    search_context: str,
    category: str = "other"
) -> Dict[str, Any]:
    """Extract and summarize reviews with enhanced structured data."""
    try:
        client = get_client()
        prompt = REVIEWS_EXTRACTION_PROMPT.format(
            brand=brand,
            name=name,
            variant=variant or "",
            category=category,
            search_context=search_context[:4000]
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        data = json.loads(result)
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        return _normalize_review_response(data), usage

    except Exception as e:
        logger.error(f"Reviews extraction error: {e}")
        return {"average_rating": None, "error": str(e)}, {"prompt_tokens": 0, "completion_tokens": 0}


def _normalize_review_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize review response for backward compatibility and field presence."""
    # Ensure common_praises/common_complaints stay as List[str]
    for key in ("common_praises", "common_complaints"):
        val = data.get(key)
        if isinstance(val, list):
            data[key] = [str(item) if not isinstance(item, str) else item for item in val]
        else:
            data[key] = []

    # Ensure all enhanced fields exist with defaults
    data.setdefault("rating_distribution", None)
    data.setdefault("category_scores", None)
    data.setdefault("source_ratings", [])
    data.setdefault("detailed_praises", [])
    data.setdefault("detailed_complaints", [])
    data.setdefault("user_quotes", [])
    data.setdefault("summary", data.get("summary"))

    # Ensure each user_quote has source, sentiment, and aspect fields
    quotes = data.get("user_quotes", [])
    for quote in quotes:
        quote.setdefault("source", "unknown")
        quote.setdefault("sentiment", "mixed")
        quote.setdefault("aspect", "general")
    data["user_quotes"] = quotes

    return data


def _build_preferences_prompt(user_preferences: Dict[str, Any]) -> str:
    """Build the personalization section to append to the comparison prompt."""
    priorities = ", ".join(user_preferences.get("priorities", []))
    budget = user_preferences.get("budget", "mid")
    lifestyle = ", ".join(user_preferences.get("lifestyle", [])) or "none specified"
    brand_attitude = user_preferences.get("brand_attitude", "best_of_both")

    return f"""

## User Preferences (personalize your verdict to this user)
- Top priorities: {priorities}
- Budget level: {budget} (interpret contextually for this product category)
- Lifestyle: {lifestyle}
- Brand attitude: {brand_attitude}

Based on these preferences, your recommendation MUST:
1. Explain WHY this product is better FOR THIS USER (not generically)
2. Reference specific preferences ("You prioritize battery life, and Product A has 5000mAh vs 3349mAh")
3. Interpret budget contextually: "budget" for phones means <$300, for supplements means <$15
4. Flag if a product conflicts with lifestyle (e.g., non-vegan supplement for vegan user)
5. For brand_loyal users: weight established brand reputation higher
6. For function_first users: ignore brand entirely, focus on specs and value
7. For best_of_both users: prefer branded options when specs are similar, but recommend better-performing product even if lesser brand"""


async def generate_comparison(
    product1: Dict,
    product2: Dict,
    region: str,
    concern: str = "value",
    user_preferences: Optional[Dict[str, Any]] = None,
    scores_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate detailed comparison between two products."""
    try:
        client = get_client()
        prompt = COMPARISON_PROMPT.format(
            product1_json=json.dumps(product1, indent=2),
            product2_json=json.dumps(product2, indent=2),
            region=region,
            currency=GCC_REGIONS.get(region, GCC_REGIONS["bahrain"])["currency"],
            concern=concern
        )

        # Append scoring context so GPT can reference deterministic scores
        if scores_summary:
            prompt += f"\n\n## Scoring Context\n{scores_summary}\nReference these scores in your verdict to support your recommendation with data."

        # Append personalization section if user has preferences
        if user_preferences:
            prompt += _build_preferences_prompt(user_preferences)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        parsed = json.loads(result)

        # Validate personalized_insights
        has_preferences = user_preferences and any(user_preferences.values())
        if not has_preferences:
            parsed.pop("personalized_insights", None)
        else:
            insights = parsed.get("personalized_insights")
            if insights is None or not isinstance(insights, list):
                parsed["personalized_insights"] = []
            elif len(insights) > 3:
                parsed["personalized_insights"] = insights[:3]

        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        return parsed, usage

    except Exception as e:
        logger.error(f"Comparison generation error: {e}")
        return {"winner_index": 0, "error": str(e)}, {"prompt_tokens": 0, "completion_tokens": 0}


# ============================================
# CACHE KEY GENERATION
# ============================================

def generate_cache_key(prefix: str, *args) -> str:
    """Generate a consistent cache key."""
    key_string = "|".join(str(arg).lower().strip() for arg in args if arg)
    hash_value = hashlib.md5(key_string.encode()).hexdigest()[:12]
    return f"{prefix}:{hash_value}"


def get_specs_cache_key(brand: str, name: str, variant: Optional[str]) -> str:
    return generate_cache_key("specs", brand, name, variant)


def get_price_cache_key(brand: str, name: str, variant: Optional[str], region: str) -> str:
    return generate_cache_key("price", brand, name, variant, region)


def get_reviews_cache_key(brand: str, name: str, variant: Optional[str]) -> str:
    return generate_cache_key("reviews", brand, name, variant)
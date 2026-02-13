"""
Structured Extraction Service - Extract structured product data with optimized prompts
"""
from dotenv import load_dotenv
load_dotenv(override=True)  # Load .env FIRST before anything else

import os
import json
import hashlib
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
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
        _client = AsyncOpenAI(api_key=api_key)
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
            "category": "electronics|grocery|beauty|fashion|home|sports|automotive|other",
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
- Return valid JSON only"""


CATEGORY_SPEC_SCHEMAS = {
    "electronics": [
        "display", "processor", "ram", "storage", "battery",
        "rear_camera", "front_camera", "os", "connectivity",
        "weight", "water_resistance"
    ],
    "grocery": [
        "size", "ingredients", "nutrition_calories", "nutrition_protein",
        "nutrition_fat", "nutrition_carbs", "origin", "organic",
        "allergens", "shelf_life", "halal"
    ],
    "other": [
        "dimensions", "weight", "material", "color", "warranty",
        "power", "features", "included", "compatibility", "origin",
        "certifications"
    ],
}


def _build_specs_prompt(brand: str, name: str, variant: str, category: str, search_context: str) -> str:
    schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
    fields = CATEGORY_SPEC_SCHEMAS[schema_key]

    fields_json = ",\n    ".join(f'"{f}": "value or null"' for f in fields)

    variant_note = f'(variant: {variant})' if variant else '(base model)'

    return f"""You are a product specifications expert. Extract specs for ONE specific configuration of this product.

PRODUCT: {brand} {name} {variant_note}
CATEGORY: {category}

Search results for context:
{search_context}

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
- EVERY field MUST have a value. Use search results first, then your training knowledge. null is ONLY acceptable if the spec truly does not exist for this product (e.g. water_resistance for a budget phone that has none)
- Be precise with numbers and units
- Include ONLY the fields listed above, no extra keys
- ONLY functional specs — NO launch price, MSRP, release date, or marketing names
- For connectivity: list supported standards (e.g. "Wi-Fi 6, 5G, Bluetooth 5.3, NFC")
- Keep each value short and factual (e.g. "6.1-inch Super Retina XDR OLED" not a paragraph)
- For well-known products (iPhones, Galaxy, Pixel, etc.) you KNOW the specs — do NOT return null for basic fields like os, weight, or water_resistance"""


PRICE_EXTRACTION_PROMPT = """You are a price extraction expert for GCC markets.

PRODUCT: {brand} {name} {variant}
REGION: {region} ({currency})

Search results:
{search_context}

Return ONLY valid JSON:
{{
    "amount": numeric_price_or_null,
    "currency": "{currency}",
    "retailer": "store name or null",
    "url": "product url or null",
    "in_stock": true|false|null,
    "confidence": 0.0-1.0
}}

RULES:
- Extract the most reliable/recent price
- Convert to {currency} if in different currency
- Confidence: 1.0 = exact match from retailer, 0.5 = estimated, 0.0 = not found
- Return null for amount if no reliable price found
- Prefer official retailers over resellers"""


PRICE_FALLBACK_PROMPT = """You are a price estimation expert. The product below could NOT be found in any current retailer listing.
Provide your BEST ESTIMATE of its current retail price from your training data.

PRODUCT: {brand} {name} {variant}
REGION: {region} ({currency})

Return ONLY valid JSON:
{{
    "amount": numeric_estimated_price,
    "currency": "{currency}",
    "retailer": "estimated",
    "confidence": 0.5,
    "note": "Estimated from training data"
}}

RULES:
- Give your best estimate of the current retail price in {currency}
- This is a LAST RESORT — clearly mark confidence as 0.5
- Use reasonable market prices for the region
- NEVER return null for amount — always provide an estimate"""


REVIEWS_EXTRACTION_PROMPT = """You are a review analysis expert. Provide a COMPREHENSIVE review analysis for this product.

PRODUCT: {brand} {name} {variant}
CATEGORY: {category}

Search results and retailer data:
{search_context}

Return ONLY valid JSON:
{{
    "average_rating": 0.0-5.0 or null,
    "total_reviews": estimated_count or null,
    "positive_percentage": 0-100 or null,
    "rating_distribution": {{
        "5_star": percentage,
        "4_star": percentage,
        "3_star": percentage,
        "2_star": percentage,
        "1_star": percentage
    }},
    "category_scores": {{
        "aspect_name": score_out_of_10
    }},
    "source_ratings": [
        {{"source": "retailer/site name", "rating": 4.5, "review_count": 1234}}
    ],
    "common_praises": ["praise 1", "praise 2", "praise 3"],
    "common_complaints": ["complaint 1", "complaint 2", "complaint 3"],
    "detailed_praises": [
        {{"text": "specific praise", "frequency": "how often mentioned", "quote": "actual user words if available"}}
    ],
    "detailed_complaints": [
        {{"text": "specific complaint", "frequency": "how often mentioned", "quote": "actual user words if available"}}
    ],
    "user_quotes": [
        {{"text": "exact or near-exact user quote from snippets", "sentiment": "positive|negative|mixed", "source": "where from", "aspect": "what aspect it covers"}}
    ],
    "summary": "2-3 sentence specific, opinionated summary"
}}

RULES:
- Aggregate from ALL sources shown (search results + retailer ratings)
- category_scores: pick 4-6 aspects relevant to the product category (e.g. for phones: camera, battery, display, performance, value, build quality)
- Score each aspect 1-10 based on review consensus
- common_praises/common_complaints: keep as simple string lists (3-5 items each)
- detailed_praises/detailed_complaints: structured versions with frequency and real quotes
- user_quotes: extract 3-5 real user quotes/phrases from the search snippets — actual words people used, not your paraphrasing
- source_ratings: combine ratings from both search results and the retailer data section
- rating_distribution: estimate percentages based on available data (must sum to ~100)
- summary: be SPECIFIC and opinionated (e.g. "The camera system is class-leading but battery life disappoints power users" not "This is a good phone")
- Return null/empty for fields without reliable data"""


PROS_CONS_PROMPT = """You are a product analyst. Generate pros and cons for this product.

PRODUCT: {brand} {name} {variant}
CATEGORY: {category}

Specs:
{specs_json}

Reviews summary:
{reviews_json}

Price: {price} {currency}

Return ONLY valid JSON:
{{
    "pros": [
        "specific pro 1",
        "specific pro 2",
        "specific pro 3",
        "specific pro 4",
        "specific pro 5"
    ],
    "cons": [
        "specific con 1",
        "specific con 2",
        "specific con 3"
    ]
}}

RULES:
- 4-6 pros, 2-4 cons (be balanced but fair)
- Be specific, not generic
- Consider: price, quality, features, durability, value
- Base on specs and reviews, don't invent"""


COMPARISON_PROMPT = """You are a product comparison expert. Compare these products and pick a winner.

PRODUCT 1:
{product1_json}

PRODUCT 2:
{product2_json}

User's region: {region}
Primary concern: {concern}

Return ONLY valid JSON:
{{
    "winner_index": 0 or 1,
    "winner_reason": "clear 1-sentence reason",
    "price_comparison": {{
        "cheaper_index": 0 or 1,
        "price_difference": "X {currency} (Y%)",
        "better_value_index": 0 or 1
    }},
    "specs_comparison": {{
        "product_0_advantages": ["advantage 1", "advantage 2"],
        "product_1_advantages": ["advantage 1", "advantage 2"],
        "similar": ["shared feature 1", "shared feature 2"]
    }},
    "value_scores": [0.0-10.0, 0.0-10.0],
    "best_for": {{
        "budget": 0 or 1,
        "performance": 0 or 1,
        "features": 0 or 1,
        "reliability": 0 or 1
    }},
    "recommendation": "2-3 sentence recommendation for the user",
    "key_differences": [
        "difference 1",
        "difference 2",
        "difference 3",
        "difference 4",
        "difference 5"
    ]
}}

RULES:
- Be objective and fair
- Consider price-to-value ratio heavily for GCC market
- Key differences should be meaningful, not trivial
- Value score: 10 = exceptional value, 5 = average, 1 = poor value"""


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
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"Product parsing error: {e}")
        return {"products": [], "error": str(e)}


async def extract_specs(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    search_context: str
) -> Dict[str, Any]:
    """Extract structured specifications for a product, enforcing a fixed schema."""
    try:
        client = get_client()
        prompt = _build_specs_prompt(
            brand, name, variant or "", category,
            search_context[:3000]
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        raw = json.loads(result)

        # Enforce schema: only keep fields in the category schema + meta keys
        schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
        allowed_fields = set(CATEGORY_SPEC_SCHEMAS[schema_key])
        meta_keys = {"brand", "model", "variant", "category"}

        cleaned = {}
        for key in list(meta_keys) + CATEGORY_SPEC_SCHEMAS[schema_key]:
            val = raw.get(key)
            if key in meta_keys:
                cleaned[key] = val
            elif val is None or val == "" or val == "null":
                cleaned[key] = "N/A"
            elif isinstance(val, list):
                cleaned[key] = ", ".join(str(v) for v in val)
            else:
                cleaned[key] = str(val)

        return cleaned

    except Exception as e:
        logger.error(f"Specs extraction error: {e}")
        return {"brand": brand, "model": name, "error": str(e)}


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
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"Price extraction error: {e}")
        return {"amount": None, "currency": region_info["currency"], "error": str(e)}


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
        return json.loads(result)
    except Exception as e:
        logger.error(f"Price fallback error: {e}")
        return {"amount": None, "currency": region_info["currency"], "error": str(e)}


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
            max_tokens=800,
            temperature=0.2,
        )

        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]

        data = json.loads(result)
        return _normalize_review_response(data)

    except Exception as e:
        logger.error(f"Reviews extraction error: {e}")
        return {"average_rating": None, "error": str(e)}


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

    return data


async def generate_pros_cons(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    specs: Dict,
    reviews: Dict,
    price: float,
    currency: str
) -> Dict[str, Any]:
    """Generate pros and cons based on specs and reviews."""
    try:
        client = get_client()
        prompt = PROS_CONS_PROMPT.format(
            brand=brand,
            name=name,
            variant=variant or "",
            category=category,
            specs_json=json.dumps(specs, indent=2),
            reviews_json=json.dumps(reviews, indent=2),
            price=price or "Unknown",
            currency=currency
        )
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3,
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"Pros/cons generation error: {e}")
        return {"pros": [], "cons": [], "error": str(e)}


async def generate_comparison(
    product1: Dict,
    product2: Dict,
    region: str,
    concern: str = "value"
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
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.2,
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"Comparison generation error: {e}")
        return {"winner_index": 0, "error": str(e)}


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
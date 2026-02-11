"""
Lite Comparison Service - Cost-optimized product comparison
Target: ~$0.003-0.004 per comparison (vs $0.01 for full)

Optimizations:
1. Single Serper search per product (vs 3-4)
2. Single AI extraction call (vs multiple)
3. Skip detailed reviews/pros-cons
4. Use search snippets directly where possible
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import json
import logging
import time
import httpx
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

_client = None
def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# Cost tracking
COSTS = {
    "serper": 0.001,  # $0.001 per search
    "openai_input": 0.00015,  # $0.15 per 1M tokens
    "openai_output": 0.0006,  # $0.60 per 1M tokens
}


# ============================================
# COMBINED SEARCH (1 call instead of 3-4)
# ============================================

async def search_product_all(product_name: str, region: str = "ae") -> Dict[str, Any]:
    """
    Single search that gets specs, price, and basic reviews.
    Cost: $0.001 (1 Serper call)
    """
    if not SERPER_API_KEY:
        return {"error": "Search not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Combined search query
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": f"{product_name} specs price review",
                    "num": 10,
                    "gl": region
                }
            )
            search_data = response.json() if response.status_code == 200 else {}
            
            # Shopping search for accurate prices
            shopping_response = await client.post(
                "https://google.serper.dev/shopping",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": product_name,
                    "num": 5,
                    "gl": region
                }
            )
            shopping_data = shopping_response.json() if shopping_response.status_code == 200 else {}
            
            return {
                "organic": search_data.get("organic", []),
                "shopping": shopping_data.get("shopping", []),
                "knowledge_graph": search_data.get("knowledgeGraph"),
                "serper_calls": 2,
                "cost": 0.002
            }
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"error": str(e)}


# ============================================
# COMBINED AI EXTRACTION (1 call instead of 4-5)
# ============================================

LITE_EXTRACTION_PROMPT = """Extract product data from search results. Return ONLY valid JSON.

PRODUCT: {product_name}
REGION: {region}

SEARCH RESULTS:
{search_results}

SHOPPING (prices):
{shopping_results}

Return JSON:
{{
    "brand": "brand or null",
    "name": "short product name",
    "category": "electronics|grocery|beauty|fashion|home|other",
    "price": numeric_price_or_null,
    "currency": "{currency}",
    "specs": {{"key": "value"}} (top 5-6 specs only),
    "rating": 0.0-5.0 or null,
    "pros": ["pro1", "pro2", "pro3"],
    "cons": ["con1", "con2"]
}}

Rules:
- Extract price from SHOPPING results first
- Specs: only include verified specs from results
- Pros/cons: derive from search snippets
- Be concise"""


async def extract_product_lite(
    product_name: str,
    search_results: Dict,
    region: str = "bahrain"
) -> Dict[str, Any]:
    """
    Single AI call to extract all product data.
    Cost: ~$0.0008 (400 input + 300 output tokens)
    """
    currency_map = {
        "bahrain": "BHD", "saudi": "SAR", "uae": "AED",
        "kuwait": "KWD", "qatar": "QAR", "oman": "OMR"
    }
    currency = currency_map.get(region, "USD")
    
    # Format search results
    organic_text = ""
    for r in search_results.get("organic", [])[:5]:
        organic_text += f"- {r.get('title', '')}: {r.get('snippet', '')}\n"
    
    shopping_text = ""
    for s in search_results.get("shopping", [])[:5]:
        shopping_text += f"- {s.get('title', '')}: {s.get('price', 'N/A')} ({s.get('source', '')})\n"
    
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": LITE_EXTRACTION_PROMPT.format(
                    product_name=product_name,
                    region=region,
                    currency=currency,
                    search_results=organic_text[:1500],
                    shopping_results=shopping_text[:500]
                )
            }],
            max_tokens=400,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1].replace("json", "", 1)
        
        data = json.loads(result)
        data["_tokens"] = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens
        }
        return data
    
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return {"error": str(e)}


# ============================================
# LITE COMPARISON (1 AI call)
# ============================================

LITE_COMPARISON_PROMPT = """Compare these two products. Return ONLY valid JSON.

PRODUCT 1: {product1}
PRODUCT 2: {product2}

Return JSON:
{{
    "winner_index": 0 or 1,
    "winner_reason": "one sentence reason",
    "price_winner": 0 or 1,
    "value_winner": 0 or 1,
    "key_differences": ["diff1", "diff2", "diff3"]
}}"""


async def compare_products_lite(product1: Dict, product2: Dict) -> Dict[str, Any]:
    """
    Single AI call for comparison.
    Cost: ~$0.0005
    """
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": LITE_COMPARISON_PROMPT.format(
                    product1=json.dumps(product1, indent=2)[:800],
                    product2=json.dumps(product2, indent=2)[:800]
                )
            }],
            max_tokens=250,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1].replace("json", "", 1)
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        return {"winner_index": 0, "error": str(e)}


# ============================================
# MAIN LITE COMPARISON FUNCTION
# ============================================

async def compare_text_lite(query: str, region: str = "bahrain") -> Dict[str, Any]:
    """
    Lite text comparison - optimized for cost.
    
    Cost breakdown:
    - Parse: $0.0003 (1 small AI call)
    - Search: $0.002 (2 Serper calls per product = 4 total)
    - Extract: $0.0008 x 2 = $0.0016
    - Compare: $0.0005
    Total: ~$0.0044
    """
    start_time = time.time()
    total_cost = 0.0
    api_calls = 0
    
    # Step 1: Parse query to get product names
    parse_result = await parse_query_lite(query)
    total_cost += 0.0003
    api_calls += 1
    
    if not parse_result.get("products") or len(parse_result["products"]) < 2:
        return {
            "success": False,
            "error": "Could not identify two products to compare",
            "hint": "Try: 'iPhone 15 vs Galaxy S24'"
        }
    
    products = []
    
    # Step 2: Search and extract each product
    for p in parse_result["products"][:2]:
        product_name = f"{p.get('brand', '')} {p.get('name', '')}".strip()
        
        # Search
        search_results = await search_product_all(product_name, "ae")
        total_cost += search_results.get("cost", 0.002)
        api_calls += search_results.get("serper_calls", 2)
        
        # Extract
        extracted = await extract_product_lite(product_name, search_results, region)
        total_cost += 0.0008
        api_calls += 1
        
        products.append({
            "brand": extracted.get("brand") or p.get("brand"),
            "name": extracted.get("name") or p.get("name"),
            "full_name": product_name,
            "category": extracted.get("category", "other"),
            "price": extracted.get("price"),
            "currency": extracted.get("currency", "BHD"),
            "specs": extracted.get("specs", {}),
            "rating": extracted.get("rating"),
            "pros": extracted.get("pros", []),
            "cons": extracted.get("cons", [])
        })
    
    # Step 3: Compare
    comparison = await compare_products_lite(products[0], products[1])
    total_cost += 0.0005
    api_calls += 1
    
    elapsed = time.time() - start_time
    
    return {
        "success": True,
        "mode": "lite",
        "products": products,
        "comparison": comparison,
        "winner_index": comparison.get("winner_index", 0),
        "winner_reason": comparison.get("winner_reason", ""),
        "key_differences": comparison.get("key_differences", []),
        "metadata": {
            "query": query,
            "region": region,
            "elapsed_seconds": round(elapsed, 2),
            "total_cost": round(total_cost, 4),
            "api_calls": api_calls,
            "mode": "lite"
        }
    }


async def parse_query_lite(query: str) -> Dict[str, Any]:
    """Minimal query parsing."""
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f'Extract products from: "{query}"\nReturn JSON: {{"products": [{{"brand": "...", "name": "..."}}]}}'
            }],
            max_tokens=150,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.split("```")[1].replace("json", "", 1)
        
        return json.loads(result)
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return {"products": []}


# ============================================
# LITE URL COMPARISON
# ============================================

async def compare_urls_lite(url1: str, url2: str, region: str = "bahrain") -> Dict[str, Any]:
    """
    Lite URL comparison.
    
    Cost: ~$0.004
    - 2 Serper searches per URL = 4 total ($0.004)
    - 2 AI extractions ($0.0016)
    - 1 comparison ($0.0005)
    """
    from app.services.url_extraction_service import (
        detect_retailer,
        extract_product_name_from_url
    )
    
    start_time = time.time()
    total_cost = 0.0
    api_calls = 0
    
    products = []
    
    for url in [url1, url2]:
        retailer = detect_retailer(url)
        product_name = extract_product_name_from_url(url)
        
        if not product_name:
            product_name = retailer.get("product_id", "Unknown")
        
        # Search
        search_results = await search_product_all(product_name, "ae")
        total_cost += 0.002
        api_calls += 2
        
        # Extract
        extracted = await extract_product_lite(product_name, search_results, region)
        total_cost += 0.0008
        api_calls += 1
        
        products.append({
            "brand": extracted.get("brand"),
            "name": extracted.get("name"),
            "full_name": product_name,
            "price": extracted.get("price"),
            "currency": extracted.get("currency", "AED"),
            "specs": extracted.get("specs", {}),
            "rating": extracted.get("rating"),
            "pros": extracted.get("pros", []),
            "cons": extracted.get("cons", []),
            "source_url": url,
            "retailer": retailer.get("name")
        })
    
    # Compare
    comparison = await compare_products_lite(products[0], products[1])
    total_cost += 0.0005
    api_calls += 1
    
    elapsed = time.time() - start_time
    
    return {
        "success": True,
        "mode": "lite",
        "products": products,
        "comparison": comparison,
        "winner_index": comparison.get("winner_index", 0),
        "winner_reason": comparison.get("winner_reason", ""),
        "key_differences": comparison.get("key_differences", []),
        "metadata": {
            "elapsed_seconds": round(elapsed, 2),
            "total_cost": round(total_cost, 4),
            "api_calls": api_calls,
            "mode": "lite"
        }
    }

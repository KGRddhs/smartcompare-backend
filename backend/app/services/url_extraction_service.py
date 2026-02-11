"""
URL Extraction Service - Extract product data using Serper (Google Search)
No direct scraping - uses Google's indexed data to avoid blocking
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import re
import json
import logging
import httpx
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, unquote
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# API Keys
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Lazy OpenAI client
_client = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# ============================================
# RETAILER DETECTION & URL PARSING
# ============================================

SUPPORTED_RETAILERS = {
    "amazon.ae": {"name": "Amazon UAE", "region": "uae", "currency": "AED", "id_pattern": r"/dp/([A-Z0-9]{10})"},
    "amazon.sa": {"name": "Amazon Saudi", "region": "saudi_arabia", "currency": "SAR", "id_pattern": r"/dp/([A-Z0-9]{10})"},
    "amazon.com": {"name": "Amazon US", "region": "us", "currency": "USD", "id_pattern": r"/dp/([A-Z0-9]{10})"},
    "noon.com": {"name": "Noon", "region": "uae", "currency": "AED", "id_pattern": r"/([NZ]\d+)"},
    "carrefour": {"name": "Carrefour", "region": "bahrain", "currency": "BHD", "id_pattern": r"/p/(\d+)"},
    "sharafdg.com": {"name": "Sharaf DG", "region": "uae", "currency": "AED", "id_pattern": r"/(\d+)"},
    "luluhypermarket": {"name": "Lulu Hypermarket", "region": "bahrain", "currency": "BHD", "id_pattern": r"/p/(\d+)"},
    "extra.com": {"name": "Extra Stores", "region": "saudi_arabia", "currency": "SAR", "id_pattern": r"/(\d+)"},
    "jarir.com": {"name": "Jarir Bookstore", "region": "saudi_arabia", "currency": "SAR", "id_pattern": r"/(\d+)"},
    "xcite.com": {"name": "Xcite Kuwait", "region": "kuwait", "currency": "KWD", "id_pattern": r"/(\d+)"},
}


def detect_retailer(url: str) -> Dict[str, Any]:
    """Detect retailer and extract product ID from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    
    retailer_info = {
        "key": "unknown",
        "domain": domain,
        "name": domain,
        "region": "unknown",
        "currency": "USD",
        "product_id": None
    }
    
    for key, info in SUPPORTED_RETAILERS.items():
        if key in domain:
            retailer_info.update({
                "key": key,
                "name": info["name"],
                "region": info["region"],
                "currency": info["currency"]
            })
            
            # Extract product ID
            if "id_pattern" in info:
                match = re.search(info["id_pattern"], url)
                if match:
                    retailer_info["product_id"] = match.group(1)
            break
    
    return retailer_info


def extract_product_name_from_url(url: str) -> str:
    """Extract product name from URL path."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    # Remove common URL parts
    path = re.sub(r'/dp/[A-Z0-9]+', '', path)
    path = re.sub(r'/ref=.*', '', path)
    path = re.sub(r'/[NZ]\d+/?$', '', path)
    
    # Get the product name part
    parts = [p for p in path.split('/') if p and len(p) > 3]
    if parts:
        # Convert URL-friendly name to readable name
        name = parts[-1] if len(parts[-1]) > 10 else parts[0]
        name = name.replace('-', ' ').replace('_', ' ')
        # Clean up
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    return ""


# ============================================
# SERPER SEARCH (NO BLOCKING!)
# ============================================

async def search_product_info(query: str, site: str = None) -> Dict[str, Any]:
    """Search for product information using Serper."""
    if not SERPER_API_KEY:
        logger.error("SERPER_API_KEY not set")
        return {"error": "Search not configured"}
    
    search_query = query
    if site:
        search_query = f"site:{site} {query}"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Regular search
            search_response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"q": search_query, "num": 10, "gl": "ae"}
            )
            search_results = search_response.json() if search_response.status_code == 200 else {}
            
            # Shopping search for prices
            shopping_response = await client.post(
                "https://google.serper.dev/shopping",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"q": query, "num": 10, "gl": "ae"}
            )
            shopping_results = shopping_response.json() if shopping_response.status_code == 200 else {}
            
            # Additional price search
            price_response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"q": f"{query} price AED UAE buy", "num": 5, "gl": "ae"}
            )
            price_results = price_response.json() if price_response.status_code == 200 else {}
            
            return {
                "organic": search_results.get("organic", []),
                "shopping": shopping_results.get("shopping", []),
                "price_search": price_results.get("organic", []),
                "knowledge_graph": search_results.get("knowledgeGraph"),
            }
    
    except Exception as e:
        logger.error(f"Serper search error: {e}")
        return {"error": str(e)}


async def search_by_url(url: str) -> Dict[str, Any]:
    """Search for product information using the URL directly."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"q": url, "num": 5}
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"URL search error: {e}")
    
    return {}


async def search_product_price(product_name: str, retailer: str = None) -> Dict[str, Any]:
    """Dedicated price search for a product."""
    if not SERPER_API_KEY:
        return {"error": "Search not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            shopping_response = await client.post(
                "https://google.serper.dev/shopping",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"q": product_name, "num": 10, "gl": "ae"}
            )
            shopping_data = shopping_response.json() if shopping_response.status_code == 200 else {}
            
            shopping_results = shopping_data.get("shopping", [])
            if shopping_results:
                logger.info(f"Shopping results for '{product_name}':")
                for item in shopping_results[:3]:
                    logger.info(f"  - {item.get('title', 'N/A')}: {item.get('price', 'N/A')}")
            
            return {"shopping": shopping_results, "query": product_name}
    
    except Exception as e:
        logger.error(f"Price search error: {e}")
        return {"error": str(e)}


def extract_price_from_shopping(shopping_results: List[Dict], product_name: str) -> Optional[Dict]:
    """Extract the best matching price from shopping results."""
    if not shopping_results:
        return None
    
    product_lower = product_name.lower()
    
    for item in shopping_results:
        title = item.get("title", "").lower()
        price_str = item.get("price", "")
        source = item.get("source", "")
        
        if any(word in title for word in product_lower.split()[:3]):
            if price_str:
                price_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
                if price_match:
                    try:
                        amount = float(price_match.group())
                        currency = "AED"
                        if "SAR" in price_str:
                            currency = "SAR"
                        elif "BHD" in price_str:
                            currency = "BHD"
                        elif "USD" in price_str or "$" in price_str:
                            currency = "USD"
                        
                        return {
                            "amount": amount,
                            "currency": currency,
                            "retailer": source,
                            "source": "shopping"
                        }
                    except ValueError:
                        continue
    
    # Fallback: return first result with price
    for item in shopping_results:
        price_str = item.get("price", "")
        if price_str:
            price_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
            if price_match:
                try:
                    return {
                        "amount": float(price_match.group()),
                        "currency": "AED",
                        "retailer": item.get("source", "Unknown"),
                        "source": "shopping_fallback"
                    }
                except ValueError:
                    continue
    
    return None


# ============================================
# AI EXTRACTION FROM SEARCH RESULTS
# ============================================

URL_EXTRACTION_PROMPT = """You are a product data extraction expert. Extract product information from these search results.

ORIGINAL URL: {url}
RETAILER: {retailer}
PRODUCT ID: {product_id}

SEARCH RESULTS:
{search_results}

SHOPPING RESULTS (with prices):
{shopping_results}

PRICE SEARCH RESULTS:
{price_results}

Extract and return ONLY valid JSON:
{{
    "brand": "brand name or null",
    "name": "product name (short, without brand)",
    "full_name": "complete product title",
    "price": numeric_price_or_null,
    "currency": "{currency}",
    "category": "electronics|grocery|beauty|fashion|home|sports|automotive|other",
    "variant": "size/storage/color if mentioned or null",
    "specs": {{
        "key": "value for important specifications"
    }},
    "rating": 0.0-5.0 or null,
    "review_count": number or null,
    "in_stock": true|false|null,
    "image_url": "product image URL or null",
    "description": "brief product description or null"
}}

RULES:
- IMPORTANT: Extract price from SHOPPING RESULTS first - they show actual prices like "AED 1,999"
- Convert price strings to numbers: "AED 1,999" becomes 1999
- If multiple prices, use the most common or from {retailer}
- Be accurate - use null only if price is truly not found anywhere
- For brand, detect from product name if not explicit (Xbox -> Microsoft, iPhone -> Apple)"""


async def extract_with_ai(url: str, retailer: Dict, search_results: Dict) -> Dict[str, Any]:
    """Use AI to extract structured product data from search results."""
    
    organic_text = ""
    for i, r in enumerate(search_results.get("organic", [])[:5]):
        organic_text += f"\n{i+1}. {r.get('title', '')}\n   {r.get('snippet', '')}\n   URL: {r.get('link', '')}\n"
    
    shopping_text = ""
    for i, s in enumerate(search_results.get("shopping", [])[:5]):
        price = s.get('price', 'N/A')
        shopping_text += f"\n{i+1}. {s.get('title', '')} - {price}\n   Source: {s.get('source', '')}\n"
    
    price_text = ""
    for i, p in enumerate(search_results.get("price_search", [])[:3]):
        price_text += f"\n{i+1}. {p.get('title', '')}\n   {p.get('snippet', '')}\n"
    
    kg = search_results.get("knowledge_graph")
    if kg:
        organic_text += f"\n\nKNOWLEDGE GRAPH:\nTitle: {kg.get('title', '')}\nDescription: {kg.get('description', '')}\n"
        if kg.get("attributes"):
            organic_text += f"Attributes: {kg.get('attributes')}\n"
    
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": URL_EXTRACTION_PROMPT.format(
                    url=url,
                    retailer=retailer.get("name", "Unknown"),
                    product_id=retailer.get("product_id", "Unknown"),
                    currency=retailer.get("currency", "USD"),
                    search_results=organic_text or "No results found",
                    shopping_results=shopping_text or "No shopping results",
                    price_results=price_text or "No price results"
                )
            }],
            max_tokens=800,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
    
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        return {"error": str(e)}


# ============================================
# MAIN EXTRACTION FUNCTION
# ============================================

async def extract_from_url(url: str) -> Dict[str, Any]:
    """Main function to extract product data from a URL using Serper."""
    
    # Step 1: Detect retailer
    retailer = detect_retailer(url)
    logger.info(f"Detected retailer: {retailer['name']}, Product ID: {retailer.get('product_id')}")
    
    # Step 2: Build search query
    product_name = extract_product_name_from_url(url)
    product_id = retailer.get("product_id", "")
    
    if product_id and "amazon" in retailer["key"]:
        search_query = f"{product_id} Amazon"
    elif product_name:
        search_query = f"{product_name} {retailer['name']}"
    else:
        search_query = url
    
    logger.info(f"Search query: {search_query}")
    
    # Step 3: Search using Serper
    search_results = await search_product_info(search_query)
    
    if search_results.get("error"):
        return {"success": False, "error": search_results["error"], "url": url}
    
    # Also search by URL directly
    url_results = await search_by_url(url)
    if url_results.get("organic"):
        search_results["organic"] = url_results.get("organic", []) + search_results.get("organic", [])
    
    # Step 4: Extract with AI
    extracted = await extract_with_ai(url, retailer, search_results)
    
    if extracted.get("error"):
        return {"success": False, "error": extracted["error"], "url": url}
    
    # Step 5: If price missing, do dedicated search
    if not extracted.get("price"):
        product_full_name = extracted.get("full_name") or extracted.get("name") or product_name
        if product_full_name:
            logger.info(f"Price missing, doing dedicated search for: {product_full_name}")
            price_results = await search_product_price(product_full_name, retailer.get("name"))
            price_data = extract_price_from_shopping(price_results.get("shopping", []), product_full_name)
            
            if price_data:
                extracted["price"] = price_data["amount"]
                extracted["price_retailer"] = price_data["retailer"]
                logger.info(f"Found price: {price_data['currency']} {price_data['amount']}")
    
    # Step 6: Normalize
    price_amount = extracted.get("price")
    if isinstance(price_amount, dict):
        price_amount = price_amount.get("amount")
    
    normalized = {
        "brand": extracted.get("brand"),
        "name": extracted.get("name") or extracted.get("full_name", "Unknown Product"),
        "full_name": extracted.get("full_name") or extracted.get("name", "Unknown Product"),
        "variant": extracted.get("variant"),
        "category": extracted.get("category", "other"),
        "price": {
            "amount": price_amount,
            "currency": extracted.get("currency") or retailer.get("currency", "USD"),
            "retailer": extracted.get("price_retailer") or retailer.get("name"),
            "url": url,
            "in_stock": extracted.get("in_stock")
        },
        "specs": extracted.get("specs", {}),
        "reviews": {
            "rating": extracted.get("rating"),
            "count": extracted.get("review_count")
        },
        "image_url": extracted.get("image_url"),
        "description": extracted.get("description"),
        "source_url": url,
        "retailer": retailer
    }
    
    return {
        "success": True,
        "product": normalized,
        "retailer": retailer,
        "source_url": url,
        "extraction_method": "serper_ai"
    }


# ============================================
# COMPARE FROM URLs
# ============================================

async def compare_from_urls(url1: str, url2: str, region: str = "bahrain") -> Dict[str, Any]:
    """Compare two products from their URLs."""
    import asyncio
    from app.services.extraction_service import generate_comparison
    
    results = await asyncio.gather(
        extract_from_url(url1),
        extract_from_url(url2),
        return_exceptions=True
    )
    
    products = []
    errors = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"URL {i+1}: {str(result)}")
        elif not result.get("success"):
            errors.append(f"URL {i+1}: {result.get('error', 'Extraction failed')}")
        else:
            products.append(result["product"])
    
    if len(products) < 2:
        return {
            "success": False,
            "error": "Could not extract both products",
            "details": errors
        }
    
    comparison = await generate_comparison(products[0], products[1], region)
    
    return {
        "success": True,
        "products": products,
        "comparison": comparison,
        "winner_index": comparison.get("winner_index", 0),
        "recommendation": comparison.get("recommendation", ""),
        "key_differences": comparison.get("key_differences", []),
        "source_urls": [url1, url2]
    }
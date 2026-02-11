"""
SmartCompare v3 - Robust Comparison Service
Guaranteed complete responses with validation and fallbacks
NO DEFAULT RATINGS - Only verified data with provenance
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import json
import logging
import time
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Debug mode - includes extra info in API responses
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

# API Keys
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# Lazy clients
_openai_client = None
_supabase_client = None

def get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client

def get_supabase() -> Optional[Client]:
    global _supabase_client
    if _supabase_client is None and SUPABASE_URL and SUPABASE_KEY:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Supabase init error: {e}")
    return _supabase_client


# ============================================
# CATEGORY-SPECIFIC SPECS
# ============================================

CATEGORY_SPECS = {
    "electronics": ["display", "processor", "ram", "storage", "battery", "camera", "os", "connectivity"],
    "smartphone": ["display", "processor", "ram", "storage", "battery", "camera", "os", "5g"],
    "laptop": ["display", "processor", "ram", "storage", "battery", "graphics", "os", "weight"],
    "tv": ["display_size", "resolution", "panel_type", "smart_features", "hdmi_ports", "refresh_rate"],
    "grocery": ["weight", "size", "ingredients", "nutrition", "origin", "expiry"],
    "beauty": ["size", "ingredients", "skin_type", "benefits", "usage"],
    "fashion": ["material", "size", "color", "care_instructions", "origin"],
    "home": ["dimensions", "material", "weight", "color", "warranty"],
    "gaming": ["platform", "storage", "resolution", "fps", "features", "controller"],
    "default": ["brand", "model", "features", "warranty", "dimensions", "weight"]
}

BRAND_DETECTION = {
    "iphone": "Apple", "ipad": "Apple", "macbook": "Apple", "airpods": "Apple", "apple watch": "Apple",
    "galaxy": "Samsung", "samsung": "Samsung",
    "pixel": "Google", "chromecast": "Google",
    "xbox": "Microsoft", "surface": "Microsoft",
    "playstation": "Sony", "ps5": "Sony", "ps4": "Sony",
    "dell": "Dell", "xps": "Dell", "alienware": "Dell",
    "hp": "HP", "pavilion": "HP", "envy": "HP",
    "lenovo": "Lenovo", "thinkpad": "Lenovo", "ideapad": "Lenovo",
    "asus": "ASUS", "rog": "ASUS", "zenbook": "ASUS",
    "nike": "Nike", "adidas": "Adidas", "puma": "Puma",
    "nido": "Nestle", "milo": "Nestle", "maggi": "Nestle",
    "almarai": "Almarai",
}


# ============================================
# DATABASE OPERATIONS
# ============================================

async def get_cached_product(product_name: str, region: str) -> Optional[Dict]:
    """Check database for cached product data."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        # Normalize name for lookup
        normalized = product_name.lower().strip()
        
        # Check products table
        result = supabase.table("products").select("*").ilike("canonical_name", f"%{normalized}%").limit(1).execute()
        
        if not result.data:
            return None
        
        product = result.data[0]
        product_id = product["id"]
        
        # Get fresh specs
        specs_result = supabase.table("product_specs").select("*").eq("product_id", product_id).gt("expires_at", datetime.utcnow().isoformat()).order("extracted_at", desc=True).limit(1).execute()
        
        # Get fresh price for region
        price_result = supabase.table("product_prices").select("*").eq("product_id", product_id).eq("region", region).gt("expires_at", datetime.utcnow().isoformat()).order("recorded_at", desc=True).limit(1).execute()
        
        # Get reviews
        reviews_result = supabase.table("product_reviews").select("*").eq("product_id", product_id).gt("expires_at", datetime.utcnow().isoformat()).limit(1).execute()
        
        if specs_result.data and price_result.data:
            return {
                "id": product_id,
                "name": product["canonical_name"],
                "brand": product["brand"],
                "category": product["category"],
                "specs": specs_result.data[0]["specs"] if specs_result.data else {},
                "price": price_result.data[0] if price_result.data else None,
                "reviews": reviews_result.data[0] if reviews_result.data else None,
                "cached": True
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Database lookup error: {e}")
        return None


async def save_product_to_db(product: Dict, region: str) -> Optional[str]:
    """Save product data to database for future use."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        # Upsert product
        product_data = {
            "canonical_name": product.get("name", "").lower(),
            "brand": product.get("brand", "Unknown"),
            "category": product.get("category", "other"),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("products").upsert(product_data, on_conflict="canonical_name").execute()
        
        if not result.data:
            return None
        
        product_id = result.data[0]["id"]
        
        # Save specs
        if product.get("specs"):
            supabase.table("product_specs").insert({
                "product_id": product_id,
                "specs": product["specs"],
                "source": "serper_ai",
                "confidence": product.get("confidence", 0.8),
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }).execute()
        
        # Save price
        if product.get("price") and product["price"].get("amount"):
            supabase.table("product_prices").insert({
                "product_id": product_id,
                "region": region,
                "currency": product["price"].get("currency", "BHD"),
                "amount": product["price"]["amount"],
                "retailer": product["price"].get("retailer"),
                "url": product["price"].get("url"),
                "in_stock": product["price"].get("in_stock"),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }).execute()
        
        # Save reviews
        if product.get("rating") or product.get("pros"):
            supabase.table("product_reviews").insert({
                "product_id": product_id,
                "average_rating": product.get("rating"),
                "total_reviews": product.get("review_count"),
                "pros": product.get("pros", []),
                "cons": product.get("cons", []),
                "source": "serper_ai",
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }).execute()
        
        return product_id
        
    except Exception as e:
        logger.error(f"Database save error: {e}")
        return None


async def log_search(query: str, input_type: str, products: List, success: bool, cost: float, duration_ms: int, error: str = None):
    """Log search for analytics and learning."""
    supabase = get_supabase()
    if not supabase:
        return
    
    try:
        supabase.table("search_logs").insert({
            "query": query,
            "input_type": input_type,
            "products_found": [p.get("name") for p in products] if products else [],
            "success": success,
            "error_message": error,
            "cost": cost,
            "duration_ms": duration_ms
        }).execute()
    except Exception as e:
        logger.error(f"Log error: {e}")


# ============================================
# SEARCH FUNCTIONS
# ============================================

async def search_all_data(product_name: str, region: str = "ae") -> Dict[str, Any]:
    """
    Comprehensive search: specs, prices, reviews in parallel.
    Also extracts verified ratings from shopping results.
    Cost: ~$0.003 (3 Serper calls)
    """
    if not SERPER_API_KEY:
        return {"error": "Search not configured"}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        
        # Parallel searches
        tasks = [
            # Specs search
            client.post("https://google.serper.dev/search", headers=headers,
                       json={"q": f"{product_name} specifications features specs", "num": 8, "gl": region}),
            # Shopping/price search
            client.post("https://google.serper.dev/shopping", headers=headers,
                       json={"q": product_name, "num": 12, "gl": region}),
            # Reviews search
            client.post("https://google.serper.dev/search", headers=headers,
                       json={"q": f"{product_name} review rating pros cons", "num": 5, "gl": region}),
        ]
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results = {
                "specs_search": [],
                "shopping": [],
                "reviews_search": [],
                "knowledge_graph": None,
                "verified_rating": None,
                "verified_review_count": None,
                "serper_calls": 3,
                "cost": 0.003
            }
            
            for i, resp in enumerate(responses):
                if isinstance(resp, Exception):
                    logger.error(f"Search {i} error: {resp}")
                    continue
                    
                if resp.status_code == 200:
                    data = resp.json()
                    if i == 0:  # Specs
                        results["specs_search"] = data.get("organic", [])
                        results["knowledge_graph"] = data.get("knowledgeGraph")
                    elif i == 1:  # Shopping
                        shopping_items = data.get("shopping", [])
                        results["shopping"] = shopping_items
                        
                        # Extract verified rating from shopping results
                        for item in shopping_items:
                            rating = item.get("rating")
                            reviews = item.get("reviews") or item.get("ratingCount")
                            
                            if rating and not results["verified_rating"]:
                                try:
                                    rating_val = float(rating)
                                    if 0 < rating_val <= 5:
                                        results["verified_rating"] = round(rating_val, 1)
                                        logger.info(f"Found verified rating in shopping: {rating_val}")
                                except (ValueError, TypeError):
                                    pass
                            
                            if reviews and not results["verified_review_count"]:
                                try:
                                    count = int(str(reviews).replace(",", "").replace("+", ""))
                                    if count > 0:
                                        results["verified_review_count"] = count
                                        logger.info(f"Found verified review count: {count}")
                                except (ValueError, TypeError):
                                    pass
                                    
                    elif i == 2:  # Reviews
                        results["reviews_search"] = data.get("organic", [])
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"error": str(e)}


async def search_price_fallback(product_name: str, region: str) -> Optional[Dict]:
    """Fallback price search with multiple attempts if primary fails."""
    if not SERPER_API_KEY:
        return None
    
    # Try multiple search queries
    search_queries = [
        f"{product_name} price",
        f"{product_name} buy",
        f"{product_name} shop",
        f"buy {product_name}",
    ]
    
    # Add region-specific queries
    region_terms = {
        "bahrain": ["Bahrain", "BHD", "BD"],
        "saudi": ["Saudi Arabia", "SAR", "KSA"],
        "uae": ["UAE", "Dubai", "AED"],
        "kuwait": ["Kuwait", "KWD"],
        "qatar": ["Qatar", "QAR"],
        "oman": ["Oman", "OMR"],
    }
    
    for term in region_terms.get(region, [""])[:1]:
        if term:
            search_queries.insert(0, f"{product_name} price {term}")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        
        for query in search_queries[:3]:  # Try up to 3 queries
            try:
                # Shopping search
                response = await client.post(
                    "https://google.serper.dev/shopping",
                    headers=headers,
                    json={"q": query, "num": 10, "gl": "ae"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    shopping = data.get("shopping", [])
                    
                    # Log what we found
                    if shopping:
                        logger.info(f"Price fallback found {len(shopping)} results for: {query}")
                    
                    for item in shopping:
                        price_str = item.get("price", "")
                        if price_str:
                            import re
                            # Match various price formats
                            match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
                            if match:
                                amount = float(match.group())
                                # Skip obviously wrong prices (too low or too high)
                                if amount < 1 or amount > 100000:
                                    continue
                                    
                                return {
                                    "amount": amount,
                                    "currency": detect_currency(price_str, region),
                                    "retailer": item.get("source", "Unknown"),
                                    "source": "fallback_search"
                                }
                
                # Also try regular search for prices in snippets
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query, "num": 5, "gl": "ae"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for result in data.get("organic", []):
                        snippet = result.get("snippet", "")
                        # Look for price patterns in snippets
                        import re
                        price_patterns = [
                            r"(?:AED|SAR|BHD|USD|\$)\s*([\d,]+\.?\d*)",
                            r"([\d,]+\.?\d*)\s*(?:AED|SAR|BHD|USD)"
                        ]
                        for pattern in price_patterns:
                            match = re.search(pattern, snippet)
                            if match:
                                try:
                                    amount = float(match.group(1).replace(",", ""))
                                    if 10 < amount < 50000:  # Reasonable price range
                                        return {
                                            "amount": amount,
                                            "currency": detect_currency(snippet, region),
                                            "retailer": result.get("link", "").split("/")[2] if result.get("link") else "Unknown",
                                            "source": "snippet_search"
                                        }
                                except ValueError:
                                    continue
                
            except Exception as e:
                logger.error(f"Price fallback error for '{query}': {e}")
                continue
    
    logger.warning(f"No price found for: {product_name}")
    return None


async def search_price_global(product_name: str, target_region: str) -> Optional[Dict]:
    """
    Search for price globally (US, UK, EU) when GCC prices not found.
    Converts to target region currency.
    """
    if not SERPER_API_KEY:
        return None
    
    logger.info(f"Searching global prices for: {product_name}")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        
        for region_info in GLOBAL_SEARCH_REGIONS:
            region_code = region_info["code"]
            expected_currency = region_info["currency"]
            
            try:
                # Shopping search in this region
                response = await client.post(
                    "https://google.serper.dev/shopping",
                    headers=headers,
                    json={
                        "q": product_name,
                        "num": 10,
                        "gl": region_code
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    shopping = data.get("shopping", [])
                    
                    if shopping:
                        logger.info(f"Found {len(shopping)} results in {region_code.upper()}")
                    
                    for item in shopping:
                        price_str = item.get("price", "")
                        if price_str:
                            import re
                            match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
                            if match:
                                amount = float(match.group())
                                
                                # Skip unreasonable prices
                                if amount < 1 or amount > 100000:
                                    continue
                                
                                # Detect currency from price string
                                source_currency = detect_currency_global(price_str, expected_currency)
                                
                                # Convert to target region currency
                                converted = convert_to_region_currency(amount, source_currency, target_region)
                                
                                logger.info(f"Global price found: {source_currency} {amount} -> {converted['currency']} {converted['amount']}")
                                
                                return {
                                    "amount": converted["amount"],
                                    "currency": converted["currency"],
                                    "retailer": item.get("source", "Unknown"),
                                    "original_amount": amount,
                                    "original_currency": source_currency,
                                    "source": f"global_{region_code}"
                                }
                
            except Exception as e:
                logger.error(f"Global search error ({region_code}): {e}")
                continue
    
    logger.warning(f"No global price found for: {product_name}")
    return None


def detect_currency_global(price_str: str, default_currency: str) -> str:
    """Detect currency from price string with global support."""
    price_upper = price_str.upper()
    
    # GCC currencies
    if "BHD" in price_upper or " BD " in price_upper:
        return "BHD"
    elif "SAR" in price_upper or " SR " in price_upper:
        return "SAR"
    elif "AED" in price_upper or "DHS" in price_upper:
        return "AED"
    elif "KWD" in price_upper or " KD " in price_upper:
        return "KWD"
    elif "QAR" in price_upper or " QR " in price_upper:
        return "QAR"
    elif "OMR" in price_upper:
        return "OMR"
    
    # Global currencies
    elif "$" in price_str and "A$" not in price_str:
        return "USD"
    elif "£" in price_str or "GBP" in price_upper:
        return "GBP"
    elif "€" in price_str or "EUR" in price_upper:
        return "EUR"
    elif "₹" in price_str or "INR" in price_upper:
        return "INR"
    
    return default_currency


async def search_rating_global(product_name: str) -> Optional[Dict]:
    """
    Search for product rating globally when not found locally.
    Returns rating and review count.
    """
    if not SERPER_API_KEY:
        return None
    
    logger.info(f"Searching global ratings for: {product_name}")
    
    # Multiple query strategies for finding ratings
    queries = [
        f"{product_name} review rating stars",
        f"{product_name} reviews amazon",
        f"{product_name} user rating",
        f'"{product_name}" rating out of 5',
    ]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        
        # First try shopping results - they often have ratings
        try:
            response = await client.post(
                "https://google.serper.dev/shopping",
                headers=headers,
                json={"q": product_name, "num": 15, "gl": "us"}
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get("shopping", []):
                    rating = item.get("rating")
                    if rating:
                        try:
                            rating = float(rating)
                            if 0 < rating <= 5:
                                reviews = item.get("reviews") or item.get("ratingCount")
                                review_count = None
                                if reviews:
                                    review_count = int(str(reviews).replace(",", "").replace("+", ""))
                                
                                logger.info(f"Found rating in shopping: {rating} ({review_count} reviews)")
                                return {
                                    "rating": round(rating, 1),
                                    "review_count": review_count,
                                    "source": "shopping_global"
                                }
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            logger.error(f"Shopping rating search error: {e}")
        
        # Then try regular search
        for query in queries[:2]:  # Limit to save cost
            try:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query, "num": 10, "gl": "us"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check knowledge graph first (most reliable)
                    kg = data.get("knowledgeGraph", {})
                    if kg:
                        rating_str = kg.get("rating") or kg.get("ratingValue")
                        if rating_str:
                            try:
                                rating = float(str(rating_str).replace("/5", "").strip())
                                if 0 < rating <= 5:
                                    review_count = None
                                    rc = kg.get("ratingCount") or kg.get("reviewCount")
                                    if rc:
                                        review_count = int(str(rc).replace(",", "").replace("+", ""))
                                    
                                    logger.info(f"Found rating in KG: {rating} ({review_count} reviews)")
                                    return {
                                        "rating": round(rating, 1),
                                        "review_count": review_count,
                                        "source": "knowledge_graph"
                                    }
                            except (ValueError, TypeError):
                                pass
                    
                    # Search in snippets for rating patterns
                    import re
                    for result in data.get("organic", []):
                        snippet = result.get("snippet", "")
                        title = result.get("title", "")
                        combined = f"{title} {snippet}"
                        
                        # Multiple patterns to catch various rating formats
                        patterns = [
                            r"(\d\.?\d?)\s*(?:out of|\/)\s*5",
                            r"(\d\.?\d?)\s*stars?",
                            r"(?:rated?|rating)[:\s]+(\d\.?\d?)(?:\s*\/?\s*5)?",
                            r"(\d\.?\d?)\s*(?:\/5|out of 5)",
                            r"average[:\s]+(\d\.?\d?)",
                            r"score[:\s]+(\d\.?\d?)(?:\s*\/?\s*(?:5|10))?",
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, combined, re.IGNORECASE)
                            if match:
                                try:
                                    rating = float(match.group(1))
                                    # Normalize if out of 10
                                    if rating > 5:
                                        rating = rating / 2
                                    if 0 < rating <= 5:
                                        # Try to find review count
                                        review_match = re.search(r"([\d,]+)\s*(?:reviews?|ratings?|votes?)", combined, re.IGNORECASE)
                                        review_count = None
                                        if review_match:
                                            review_count = int(review_match.group(1).replace(",", ""))
                                        
                                        logger.info(f"Found rating in snippet: {rating}")
                                        return {
                                            "rating": round(rating, 1),
                                            "review_count": review_count,
                                            "source": "snippet_search"
                                        }
                                except (ValueError, TypeError):
                                    continue
                
            except Exception as e:
                logger.error(f"Rating search error: {e}")
                continue
    
    logger.warning(f"No rating found for: {product_name}")
    return None


async def search_review_count(product_name: str) -> Optional[Dict]:
    """
    Quick search specifically for review count.
    """
    if not SERPER_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": product_name, "num": 10, "gl": "us"}
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get("shopping", []):
                    reviews = item.get("reviews") or item.get("ratingCount")
                    if reviews:
                        try:
                            count = int(str(reviews).replace(",", "").replace("+", ""))
                            if count > 0:
                                return {"count": count, "source": "shopping"}
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logger.error(f"Review count search error: {e}")
    
    return None


async def search_msrp_price(product_name: str, target_region: str) -> Optional[Dict]:
    """
    Search for MSRP/launch price for new products not yet in retail.
    Useful for newly announced or pre-order products.
    """
    if not SERPER_API_KEY:
        return None
    
    logger.info(f"Searching MSRP/launch price for: {product_name}")
    
    # Queries optimized for finding MSRP
    queries = [
        f"{product_name} MSRP price",
        f"{product_name} launch price USD",
        f"{product_name} official price",
        f"{product_name} starting price",
    ]
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        
        for query in queries[:2]:  # Limit to 2 queries to save cost
            try:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query, "num": 10, "gl": "us"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check knowledge graph
                    kg = data.get("knowledgeGraph", {})
                    if kg:
                        for key in ["price", "msrp", "startingPrice"]:
                            if kg.get(key):
                                price_str = str(kg[key])
                                amount = extract_price_amount(price_str)
                                if amount:
                                    currency = detect_currency_global(price_str, "USD")
                                    converted = convert_to_region_currency(amount, currency, target_region)
                                    logger.info(f"Found MSRP in KG: {currency} {amount}")
                                    return {
                                        "amount": converted["amount"],
                                        "currency": converted["currency"],
                                        "retailer": "MSRP",
                                        "original_amount": amount,
                                        "original_currency": currency,
                                        "estimated": True,
                                        "note": f"MSRP/Launch price: {currency} {amount}"
                                    }
                    
                    # Search in snippets
                    import re
                    for result in data.get("organic", []):
                        snippet = result.get("snippet", "")
                        title = result.get("title", "")
                        combined = f"{title} {snippet}"
                        
                        # Patterns for MSRP prices
                        patterns = [
                            r"MSRP[:\s]+\$?([\d,]+)",
                            r"starting\s+(?:at|from)?\s*\$?([\d,]+)",
                            r"launch(?:es|ed)?\s+(?:at|for)\s*\$?([\d,]+)",
                            r"priced?\s+(?:at|from)\s*\$?([\d,]+)",
                            r"\$([\d,]+)\s*(?:MSRP|USD|starting)",
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, combined, re.IGNORECASE)
                            if match:
                                try:
                                    amount = float(match.group(1).replace(",", ""))
                                    # Validate reasonable GPU price range ($100 - $3000)
                                    if 100 < amount < 5000:
                                        converted = convert_to_region_currency(amount, "USD", target_region)
                                        logger.info(f"Found MSRP in snippet: USD {amount}")
                                        return {
                                            "amount": converted["amount"],
                                            "currency": converted["currency"],
                                            "retailer": "MSRP",
                                            "original_amount": amount,
                                            "original_currency": "USD",
                                            "estimated": True,
                                            "note": f"MSRP/Launch price: USD {amount}"
                                        }
                                except (ValueError, TypeError):
                                    continue
                
            except Exception as e:
                logger.error(f"MSRP search error: {e}")
                continue
    
    logger.warning(f"No MSRP found for: {product_name}")
    return None


def extract_price_amount(price_str: str) -> Optional[float]:
    """Extract numeric price from string."""
    import re
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    if match:
        try:
            return float(match.group())
        except ValueError:
            pass
    return None


def detect_currency(price_str: str, region: str) -> str:
    """Detect currency from price string or region."""
    price_upper = price_str.upper()
    
    if "BHD" in price_upper or " BD" in price_upper:
        return "BHD"
    elif "SAR" in price_upper or " SR" in price_upper:
        return "SAR"
    elif "AED" in price_upper or "DHS" in price_upper or "DIRHAM" in price_upper:
        return "AED"
    elif "KWD" in price_upper or " KD" in price_upper:
        return "KWD"
    elif "QAR" in price_upper or " QR" in price_upper:
        return "QAR"
    elif "OMR" in price_upper or " RO" in price_upper:
        return "OMR"
    elif "$" in price_str or "USD" in price_upper:
        return "USD"
    
    # Default to AED for UAE retailers (most common)
    return "AED"


# Currency conversion rates to BHD
CURRENCY_TO_BHD = {
    "BHD": 1.0,
    "AED": 0.1025,  # 1 AED = 0.1025 BHD
    "SAR": 0.1003,  # 1 SAR = 0.1003 BHD
    "USD": 0.377,   # 1 USD = 0.377 BHD
    "KWD": 1.22,    # 1 KWD = 1.22 BHD
    "QAR": 0.1035,  # 1 QAR = 0.1035 BHD
    "OMR": 0.98,    # 1 OMR = 0.98 BHD
    "GBP": 0.47,    # 1 GBP = 0.47 BHD
    "EUR": 0.41,    # 1 EUR = 0.41 BHD
    "INR": 0.0045,  # 1 INR = 0.0045 BHD
}

# Global retailers for fallback
GLOBAL_SEARCH_REGIONS = [
    {"code": "us", "currency": "USD", "retailers": ["amazon.com", "bestbuy", "walmart", "newegg"]},
    {"code": "uk", "currency": "GBP", "retailers": ["amazon.co.uk", "currys", "argos"]},
    {"code": "de", "currency": "EUR", "retailers": ["amazon.de", "mediamarkt"]},
]


def convert_to_region_currency(amount: float, from_currency: str, to_region: str) -> dict:
    """Convert price to the target region's currency."""
    region_currencies = {
        "bahrain": "BHD", "saudi": "SAR", "uae": "AED",
        "kuwait": "KWD", "qatar": "QAR", "oman": "OMR"
    }
    target_currency = region_currencies.get(to_region, "BHD")
    
    if from_currency == target_currency:
        return {"amount": amount, "currency": target_currency}
    
    # Convert via BHD as base
    to_bhd = CURRENCY_TO_BHD.get(from_currency, 1.0)
    from_bhd = CURRENCY_TO_BHD.get(target_currency, 1.0)
    
    converted = (amount * to_bhd) / from_bhd
    
    return {
        "amount": round(converted, 2),
        "currency": target_currency,
        "original_amount": amount,
        "original_currency": from_currency
    }


def convert_price_to_region(price_data: dict, region: str) -> dict:
    """
    Convert extracted price to target region currency.
    Detects source currency from retailer domain if not specified.
    """
    if not price_data or not price_data.get("amount"):
        return price_data
    
    amount = price_data.get("amount")
    source_currency = price_data.get("currency", "AED")
    retailer = price_data.get("retailer", "")
    
    # Detect currency from retailer if it looks like AED was mislabeled
    retailer_lower = retailer.lower() if retailer else ""
    
    # If retailer is UAE-based, currency should be AED
    if any(x in retailer_lower for x in [".ae", "uae", "dubai", "noon", "istyle", "sharaf"]):
        source_currency = "AED"
    elif any(x in retailer_lower for x in [".sa", "saudi", "jarir", "extra"]):
        source_currency = "SAR"
    elif any(x in retailer_lower for x in [".com", "amazon.com"]):
        source_currency = "USD"
    
    # If price > 500 and marked as BHD, it's probably AED (common mistake)
    if source_currency == "BHD" and amount > 500:
        source_currency = "AED"
    
    region_currencies = {
        "bahrain": "BHD", "saudi": "SAR", "uae": "AED",
        "kuwait": "KWD", "qatar": "QAR", "oman": "OMR"
    }
    target_currency = region_currencies.get(region, "BHD")
    
    # Convert if needed
    if source_currency != target_currency:
        converted = convert_to_region_currency(amount, source_currency, region)
        return {
            "amount": converted["amount"],
            "currency": target_currency,
            "retailer": retailer,
            "original_amount": amount,
            "original_currency": source_currency
        }
    
    return price_data


# ============================================
# AI EXTRACTION WITH VALIDATION
# ============================================

EXTRACTION_PROMPT = """Extract product data from search results. BE FACTUAL - only extract data that EXISTS.

PRODUCT: {product_name}
CATEGORY: {category}
TARGET REGION: {region} (prices in {currency})

SPECS SEARCH RESULTS:
{specs_results}

SHOPPING RESULTS (PRICES):
{shopping_results}

REVIEW RESULTS:
{reviews_results}

KNOWLEDGE GRAPH:
{knowledge_graph}

Return ONLY valid JSON:
{{
    "brand": "brand name (REQUIRED)",
    "name": "product name (REQUIRED)",
    "category": "{category}",
    "price": {{
        "amount": number or null,
        "currency": "detected currency (AED/SAR/USD)",
        "retailer": "store name"
    }},
    "specs": {{
        {specs_fields}
    }},
    "pros": ["pro1", "pro2", "pro3"] (derive from specs/features),
    "cons": ["con1", "con2"] (derive from limitations),
    "confidence": 0.0-1.0
}}

IMPORTANT RULES:
1. DO NOT include rating or review_count - these are fetched separately from verified sources
2. PRICE: Extract from SHOPPING RESULTS with detected currency
3. SPECS: Extract actual specifications from results
4. PROS/CONS: Derive from specs and features (this is OK to generate)
5. Brand: NVIDIA RTX=NVIDIA, Radeon/RX=AMD, iPhone=Apple, Galaxy=Samsung"""


async def extract_product_data(
    product_name: str,
    search_results: Dict,
    region: str,
    category: str = "electronics"
) -> Dict[str, Any]:
    """
    Extract complete product data with validation.
    Ensures all required fields are present.
    """
    currency_map = {
        "bahrain": "BHD", "saudi": "SAR", "uae": "AED",
        "kuwait": "KWD", "qatar": "QAR", "oman": "OMR"
    }
    currency = currency_map.get(region, "USD")
    
    # Format search results
    specs_text = "\n".join([
        f"- {r.get('title', '')}: {r.get('snippet', '')}"
        for r in search_results.get("specs_search", [])[:6]
    ]) or "No specs found"
    
    shopping_text = "\n".join([
        f"- {s.get('title', '')}: {s.get('price', 'N/A')} from {s.get('source', '')}"
        for s in search_results.get("shopping", [])[:6]
    ]) or "No shopping results"
    
    reviews_text = "\n".join([
        f"- {r.get('title', '')}: {r.get('snippet', '')}"
        for r in search_results.get("reviews_search", [])[:4]
    ]) or "No reviews found"
    
    kg = search_results.get("knowledge_graph")
    kg_text = ""
    if kg:
        kg_text = f"Title: {kg.get('title', '')}\nDescription: {kg.get('description', '')}\n"
        if kg.get("attributes"):
            kg_text += f"Attributes: {json.dumps(kg['attributes'])}"
    
    # Category-specific specs fields
    spec_fields = CATEGORY_SPECS.get(category, CATEGORY_SPECS["default"])
    specs_template = ",\n        ".join([f'"{f}": "value or null"' for f in spec_fields])
    
    try:
        client = get_openai()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(
                    product_name=product_name,
                    category=category,
                    region=region,
                    currency=currency,
                    specs_results=specs_text[:2000],
                    shopping_results=shopping_text[:1000],
                    reviews_results=reviews_text[:1000],
                    knowledge_graph=kg_text[:500],
                    specs_fields=specs_template
                )
            }],
            max_tokens=700,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean markdown
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        data = json.loads(result)
        
        # Validate and fix
        data = validate_and_fix_product(data, product_name, category, region, currency, search_results)
        
        return data
        
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return create_fallback_product(product_name, category, region, currency)


def validate_and_fix_product(
    data: Dict,
    product_name: str,
    category: str,
    region: str,
    currency: str,
    search_results: Dict
) -> Dict:
    """Validate product data and fix missing fields."""
    
    # Fix brand
    if not data.get("brand"):
        data["brand"] = detect_brand(product_name)
    
    # Fix name
    if not data.get("name"):
        data["name"] = product_name
    
    # Fix category
    if not data.get("category"):
        data["category"] = category
    
    # Fix price structure
    if not isinstance(data.get("price"), dict):
        data["price"] = {"amount": data.get("price"), "currency": currency, "retailer": None}
    
    if not data["price"].get("currency"):
        data["price"]["currency"] = currency
    
    # Mark if price is estimated/converted
    if data["price"].get("original_currency") and data["price"]["original_currency"] != data["price"].get("currency"):
        data["price"]["estimated"] = True
        data["price"]["note"] = f"Converted from {data['price']['original_currency']} {data['price'].get('original_amount', 'N/A')}"
    
    # If still no price, mark as unavailable with reason
    if not data["price"].get("amount"):
        data["price"]["unavailable"] = True
        data["price"]["note"] = "Price not found in any region"
    
    # Fix specs - ensure minimum fields
    if not data.get("specs") or len(data.get("specs", {})) < 3:
        data["specs"] = extract_specs_from_search(search_results, category)
    
    # Fix pros - ensure minimum 3
    if not data.get("pros") or len(data.get("pros", [])) < 3:
        data["pros"] = generate_pros(data, category)
    
    # Fix cons - ensure minimum 2
    if not data.get("cons") or len(data.get("cons", [])) < 2:
        data["cons"] = generate_cons(data, category)
    
    # Add confidence
    data["confidence"] = calculate_confidence(data)
    
    return data


def detect_brand(product_name: str) -> str:
    """Detect brand from product name."""
    name_lower = product_name.lower()
    
    for keyword, brand in BRAND_DETECTION.items():
        if keyword in name_lower:
            return brand
    
    # First word might be brand
    words = product_name.split()
    if words:
        return words[0].capitalize()
    
    return "Unknown"


def extract_specs_from_search(search_results: Dict, category: str) -> Dict:
    """Extract specs directly from search results."""
    specs = {}
    
    # From knowledge graph
    kg = search_results.get("knowledge_graph", {})
    if kg and kg.get("attributes"):
        specs.update(kg["attributes"])
    
    # Default specs for category
    defaults = CATEGORY_SPECS.get(category, CATEGORY_SPECS["default"])
    for field in defaults:
        if field not in specs:
            specs[field] = None
    
    return specs


def generate_pros(data: Dict, category: str) -> List[str]:
    """Generate pros from available data."""
    pros = list(data.get("pros", []))
    
    # Generate from specs
    specs = data.get("specs", {})
    
    generic_pros = {
        "electronics": [
            "Good build quality",
            "Reliable performance",
            "Popular brand with good support"
        ],
        "smartphone": [
            "Modern display technology",
            "Good camera capabilities",
            "Fast performance"
        ],
        "default": [
            "Good value for money",
            "Reliable quality",
            "Popular choice"
        ]
    }
    
    while len(pros) < 3:
        category_pros = generic_pros.get(category, generic_pros["default"])
        for p in category_pros:
            if p not in pros:
                pros.append(p)
                break
        if len(pros) < 3:
            pros.append("Well-reviewed by users")
            break
    
    return pros[:5]


def generate_cons(data: Dict, category: str) -> List[str]:
    """Generate cons from available data."""
    cons = list(data.get("cons", []))
    
    generic_cons = {
        "electronics": [
            "May be expensive compared to alternatives",
            "Limited availability in some regions"
        ],
        "smartphone": [
            "Premium pricing",
            "May lack some niche features"
        ],
        "default": [
            "Check compatibility before purchase",
            "Compare with alternatives"
        ]
    }
    
    while len(cons) < 2:
        category_cons = generic_cons.get(category, generic_cons["default"])
        for c in category_cons:
            if c not in cons:
                cons.append(c)
                break
        if len(cons) < 2:
            cons.append("Research thoroughly before buying")
            break
    
    return cons[:4]


def calculate_confidence(data: Dict) -> float:
    """Calculate confidence score based on data completeness and verification."""
    score = 0.0
    
    # Required fields
    if data.get("brand") and data["brand"] != "Unknown":
        score += 0.15
    if data.get("name"):
        score += 0.1
    
    # Price scoring
    price = data.get("price", {})
    if price.get("amount"):
        if price.get("estimated"):
            score += 0.15  # Lower score for estimated price
        else:
            score += 0.25  # Full score for local price
    
    # Specs scoring
    if len(data.get("specs", {})) >= 5:
        score += 0.2
    elif len(data.get("specs", {})) >= 3:
        score += 0.1
    
    # Rating scoring - higher for verified
    if data.get("rating"):
        if data.get("rating_verified"):
            score += 0.12  # Higher confidence for verified rating
        else:
            score += 0.05  # Lower for AI-extracted (might be wrong)
    
    # Review count scoring
    if data.get("review_count"):
        score += 0.05
    
    # Pros/cons scoring
    if len(data.get("pros", [])) >= 3:
        score += 0.08
    if len(data.get("cons", [])) >= 2:
        score += 0.05
    
    return min(1.0, round(score, 2))


def create_fallback_product(product_name: str, category: str, region: str, currency: str) -> Dict:
    """Create fallback product when extraction fails."""
    return {
        "brand": detect_brand(product_name),
        "name": product_name,
        "category": category,
        "price": {"amount": None, "currency": currency, "retailer": None},
        "specs": {k: None for k in CATEGORY_SPECS.get(category, CATEGORY_SPECS["default"])},
        "rating": None,
        "review_count": None,
        "pros": generate_pros({}, category),
        "cons": generate_cons({}, category),
        "confidence": 0.2,
        "fallback": True
    }


# ============================================
# COMPARISON ENGINE
# ============================================

COMPARISON_PROMPT = """Compare these two products objectively.

PRODUCT 1:
{product1}

PRODUCT 2:
{product2}

USER REGION: {region}

Return ONLY valid JSON:
{{
    "winner_index": 0 or 1,
    "winner_reason": "Clear one-sentence reason",
    "confidence": 0.0-1.0,
    "price_comparison": {{
        "cheaper_index": 0 or 1 or null,
        "price_difference": "X {currency} (Y%)" or "Prices unavailable",
        "better_value_index": 0 or 1
    }},
    "specs_comparison": {{
        "product_0_advantages": ["adv1", "adv2"],
        "product_1_advantages": ["adv1", "adv2"],
        "similar_features": ["feature1", "feature2"]
    }},
    "value_scores": [0-10, 0-10],
    "best_for": {{
        "budget": 0 or 1,
        "performance": 0 or 1,
        "features": 0 or 1,
        "reliability": 0 or 1
    }},
    "key_differences": [
        "difference1",
        "difference2",
        "difference3",
        "difference4",
        "difference5"
    ],
    "recommendation": "2-3 sentence recommendation"
}}"""


async def compare_products(product1: Dict, product2: Dict, region: str) -> Dict[str, Any]:
    """Generate comprehensive comparison."""
    currency_map = {
        "bahrain": "BHD", "saudi": "SAR", "uae": "AED",
        "kuwait": "KWD", "qatar": "QAR", "oman": "OMR"
    }
    currency = currency_map.get(region, "USD")
    
    try:
        client = get_openai()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": COMPARISON_PROMPT.format(
                    product1=json.dumps(product1, indent=2)[:1200],
                    product2=json.dumps(product2, indent=2)[:1200],
                    region=region,
                    currency=currency
                )
            }],
            max_tokens=600,
            temperature=0.2,
        )
        
        result = response.choices[0].message.content.strip()
        
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        return json.loads(result)
        
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        return {
            "winner_index": 0,
            "winner_reason": "Unable to determine winner due to incomplete data",
            "error": str(e)
        }


# ============================================
# MAIN COMPARISON FUNCTION
# ============================================

async def compare_v3(query: str, region: str = "bahrain") -> Dict[str, Any]:
    """
    SmartCompare v3 - Complete comparison with validation.
    
    Guarantees:
    - Both products have complete data
    - All required fields present
    - Fallbacks for missing data
    - Results saved to database
    """
    start_time = time.time()
    total_cost = 0.0
    api_calls = 0
    
    # Step 1: Parse query
    products_parsed = await parse_query(query)
    total_cost += 0.0003
    api_calls += 1
    
    if len(products_parsed) < 2:
        return {
            "success": False,
            "error": "Could not identify two products. Try: 'iPhone 15 vs Galaxy S24'",
            "parsed": products_parsed
        }
    
    products = []
    
    # Step 2: Process each product
    for p in products_parsed[:2]:
        product_name = f"{p.get('brand', '')} {p.get('name', '')}".strip()
        category = p.get("category", "electronics")
        
        # Check cache first
        cached = await get_cached_product(product_name, region)
        
        if cached:
            logger.info(f"Cache hit for: {product_name}")
            products.append({
                "brand": cached["brand"],
                "name": cached["name"],
                "full_name": product_name,
                "category": category,
                "price": cached.get("price", {}),
                "specs": cached.get("specs", {}),
                "rating": cached.get("reviews", {}).get("average_rating") if cached.get("reviews") else None,
                "pros": cached.get("reviews", {}).get("pros", []) if cached.get("reviews") else [],
                "cons": cached.get("reviews", {}).get("cons", []) if cached.get("reviews") else [],
                "cached": True,
                "confidence": 0.95
            })
            continue
        
        # Search for data
        logger.info(f"Searching for: {product_name}")
        search_results = await search_all_data(product_name, "ae")
        total_cost += search_results.get("cost", 0.003)
        api_calls += search_results.get("serper_calls", 3)
        
        # Extract with validation (NO RATINGS - fetched separately via deterministic method)
        extracted = await extract_product_data(product_name, search_results, region, category)
        total_cost += 0.001
        api_calls += 1
        
        # Remove any AI-generated ratings (should not exist but safety check)
        extracted.pop("rating", None)
        extracted.pop("review_count", None)
        
        # Fetch verified rating from Google Shopping data
        # Uses pre-fetched shopping results first, then falls back to dedicated search
        logger.info(f"[RATING] Extracting verified rating for: {product_name}")

        try:
            from app.services.rating_extractor import get_verified_rating, validate_rating_for_api, ExtractedRating

            # Pass pre-fetched shopping data to avoid extra API calls
            shopping_data = search_results.get("shopping", [])
            rating_result = await get_verified_rating(product_name, shopping_data=shopping_data)
            total_cost += 0.001  # Only costs extra if fallback search needed
            api_calls += 1
            
            # Add rating data with full provenance
            rating_data = rating_result.to_api_response()
            extracted["rating"] = rating_data.get("rating")
            extracted["review_count"] = rating_data.get("review_count")
            extracted["rating_verified"] = rating_data.get("rating_verified", False)
            extracted["rating_source"] = rating_data.get("rating_source")
            
            # Include debug info
            extracted["_rating_debug"] = rating_result.to_debug()
            
            # Log rating result with source
            if rating_data.get("rating_verified"):
                src = rating_data.get("rating_source", {})
                logger.info(f"[RATING] ✓ VERIFIED: {rating_data['rating']}/5 ({rating_data.get('review_count')} reviews)")
                logger.info(f"[RATING]   Source: {src.get('name')} | Method: {src.get('extract_method')}")
                logger.info(f"[RATING]   URL: {src.get('url')}")
            else:
                logger.warning(f"[RATING] ✗ No verified rating found for: {product_name}")
            
            # API layer validation - STRICT: strips ratings without source_url
            extracted = validate_rating_for_api(extracted)
            
        except ImportError as e:
            logger.warning(f"[RATING] Rating extractor not available: {e}")
            # Fallback: no rating (don't crash the whole comparison)
            extracted["rating"] = None
            extracted["review_count"] = None
            extracted["rating_verified"] = False
            extracted["rating_source"] = None
        except Exception as e:
            logger.error(f"[RATING] Rating extraction error: {e}")
            extracted["rating"] = None
            extracted["review_count"] = None
            extracted["rating_verified"] = False
            extracted["rating_source"] = None
        
        # Price fallback if missing - try GCC first, then global
        if not extracted.get("price", {}).get("amount"):
            logger.info(f"Price missing, trying GCC fallback for: {product_name}")
            fallback_price = await search_price_fallback(product_name, region)
            total_cost += 0.001
            api_calls += 1
            
            if fallback_price:
                extracted["price"] = fallback_price
            else:
                # Try global search (US, UK, EU)
                logger.info(f"GCC price not found, trying global for: {product_name}")
                global_price = await search_price_global(product_name, region)
                total_cost += 0.003  # Up to 3 regions searched
                api_calls += 3
                
                if global_price:
                    extracted["price"] = global_price
                else:
                    # Last resort: Try MSRP/announcement price for new products
                    logger.info(f"No retail price found, trying MSRP for: {product_name}")
                    msrp_price = await search_msrp_price(product_name, region)
                    total_cost += 0.001
                    api_calls += 1
                    
                    if msrp_price:
                        extracted["price"] = msrp_price
        
        # Final validation (excludes rating - already handled)
        extracted = validate_and_fix_product(
            extracted, product_name, category, region,
            {"bahrain": "BHD", "saudi": "SAR", "uae": "AED"}.get(region, "USD"),
            search_results
        )
        
        # Convert price to target region currency
        if extracted.get("price", {}).get("amount"):
            extracted["price"] = convert_price_to_region(extracted["price"], region)
        
        extracted["full_name"] = product_name
        extracted["cached"] = False
        
        # Save to database
        await save_product_to_db(extracted, region)
        
        products.append(extracted)
    
    # Step 3: Compare
    comparison = await compare_products(products[0], products[1], region)
    total_cost += 0.0008
    api_calls += 1
    
    elapsed = time.time() - start_time
    
    # Log search
    await log_search(
        query=query,
        input_type="text",
        products=products,
        success=True,
        cost=total_cost,
        duration_ms=int(elapsed * 1000)
    )
    
    return {
        "success": True,
        "version": "v3",
        "products": products,
        "comparison": comparison,
        "winner_index": comparison.get("winner_index", 0),
        "winner_reason": comparison.get("winner_reason", ""),
        "recommendation": comparison.get("recommendation", ""),
        "key_differences": comparison.get("key_differences", []),
        "metadata": {
            "query": query,
            "region": region,
            "elapsed_seconds": round(elapsed, 2),
            "total_cost": round(total_cost, 4),
            "api_calls": api_calls,
            "cache_hits": sum(1 for p in products if p.get("cached")),
            "version": "v3"
        }
    }


async def parse_query(query: str) -> List[Dict]:
    """Parse comparison query to extract products."""
    try:
        client = get_openai()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f'''Extract products from: "{query}"
Return JSON: {{"products": [{{"brand": "...", "name": "...", "category": "electronics|grocery|beauty|fashion|home|other"}}]}}'''
            }],
            max_tokens=200,
            temperature=0.1,
        )
        
        result = response.choices[0].message.content.strip()
        if "```" in result:
            result = result.split("```")[1].replace("json", "", 1)
        
        data = json.loads(result)
        return data.get("products", [])
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return []
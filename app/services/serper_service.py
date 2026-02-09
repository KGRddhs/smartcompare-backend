"""
Serper Service - Web search via Serper API (Google Search)
Enhanced for structured product data extraction
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_BASE_URL = "https://google.serper.dev"


# ============================================
# ORIGINAL FUNCTIONS (backward compatibility)
# ============================================

async def search_product_price(product_name: str, country: str = "Bahrain") -> Dict[str, Any]:
    """
    Original function - Search for product prices.
    Kept for backward compatibility with comparison_service.py
    """
    country_codes = {
        "Bahrain": "bh",
        "Saudi Arabia": "sa",
        "UAE": "ae",
        "Kuwait": "kw",
        "Qatar": "qa",
        "Oman": "om"
    }
    
    code = country_codes.get(country, "bh")
    query = f"{product_name} price {country}"
    
    results = await search_product_prices(product_name, code)
    
    # Format for backward compatibility
    return {
        "query": query,
        "organic": results.get("organic", []),
        "shopping": results.get("shopping", []),
        "knowledge_graph": results.get("knowledge_graph")
    }


# ============================================
# CORE SEARCH FUNCTIONS
# ============================================

async def search_web(
    query: str,
    num_results: int = 10,
    country: str = "bh"
) -> Dict[str, Any]:
    """
    General web search.
    
    Args:
        query: Search query
        num_results: Number of results (max 100)
        country: Country code for localized results
    
    Returns:
        Search results with organic, featured snippets, etc.
    """
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set")
        return {"organic": [], "error": "Search not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/search",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": num_results,
                    "gl": country,
                    "hl": "en"
                }
            )
            response.raise_for_status()
            return response.json()
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"organic": [], "error": str(e)}


async def search_product_prices(
    product: str,
    country: str = "bh",
    currency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search specifically for product prices.
    Uses shopping search for better price results.
    
    Args:
        product: Product name/query
        country: Country code (bh, sa, ae, kw, qa, om)
        currency: Optional currency filter
    """
    if not SERPER_API_KEY:
        return {"shopping": [], "organic": [], "error": "Search not configured"}
    
    # Country-specific search enhancements
    country_terms = {
        "bh": "Bahrain price BHD buy",
        "sa": "Saudi Arabia price SAR buy",
        "ae": "UAE Dubai price AED buy",
        "kw": "Kuwait price KWD buy",
        "qa": "Qatar price QAR buy",
        "om": "Oman price OMR buy"
    }
    
    location_term = country_terms.get(country, "price buy")
    search_query = f"{product} {location_term}"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Try shopping search first
            shopping_response = await client.post(
                f"{SERPER_BASE_URL}/shopping",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": product,
                    "gl": country,
                    "hl": "en",
                    "num": 10
                }
            )
            
            shopping_results = {}
            if shopping_response.status_code == 200:
                shopping_results = shopping_response.json()
            
            # Also do regular search for additional price sources
            organic_response = await client.post(
                f"{SERPER_BASE_URL}/search",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": search_query,
                    "gl": country,
                    "hl": "en",
                    "num": 10
                }
            )
            
            organic_results = {}
            if organic_response.status_code == 200:
                organic_results = organic_response.json()
            
            return {
                "shopping": shopping_results.get("shopping", []),
                "organic": organic_results.get("organic", []),
                "knowledge_graph": organic_results.get("knowledgeGraph"),
                "query": search_query
            }
    
    except Exception as e:
        logger.error(f"Price search error: {e}")
        return {"shopping": [], "organic": [], "error": str(e)}


async def search_product_specs(
    product: str,
    category: str = "electronics"
) -> Dict[str, Any]:
    """
    Search for product specifications.
    
    Args:
        product: Product name
        category: Product category for targeted search
    """
    # Category-specific search terms
    category_terms = {
        "electronics": "specifications specs features technical details",
        "grocery": "ingredients nutrition facts details",
        "beauty": "ingredients benefits how to use",
        "fashion": "material size guide care instructions",
        "home": "specifications dimensions features",
    }
    
    spec_terms = category_terms.get(category, "specifications details features")
    query = f"{product} {spec_terms}"
    
    return await search_web(query, num_results=10)


async def search_product_reviews(
    product: str,
    include_video: bool = False
) -> Dict[str, Any]:
    """
    Search for product reviews and ratings.
    
    Args:
        product: Product name
        include_video: Include video review results
    """
    query = f"{product} review rating user experience pros cons"
    
    results = await search_web(query, num_results=10)
    
    if include_video:
        video_results = await search_videos(f"{product} review")
        results["videos"] = video_results.get("videos", [])
    
    return results


async def search_videos(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for videos (reviews, tutorials, etc.)."""
    if not SERPER_API_KEY:
        return {"videos": [], "error": "Search not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/videos",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            return response.json()
    
    except Exception as e:
        logger.error(f"Video search error: {e}")
        return {"videos": [], "error": str(e)}


async def search_images(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for product images."""
    if not SERPER_API_KEY:
        return {"images": [], "error": "Search not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/images",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            return response.json()
    
    except Exception as e:
        logger.error(f"Image search error: {e}")
        return {"images": [], "error": str(e)}


async def search_news(
    query: str,
    num_results: int = 5
) -> Dict[str, Any]:
    """Search for recent news about a product."""
    if not SERPER_API_KEY:
        return {"news": [], "error": "Search not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/news",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": num_results
                }
            )
            response.raise_for_status()
            return response.json()
    
    except Exception as e:
        logger.error(f"News search error: {e}")
        return {"news": [], "error": str(e)}


# ============================================
# GCC Store-specific searches
# ============================================

GCC_RETAILERS = {
    "bahrain": [
        "carrefour bahrain",
        "lulu hypermarket bahrain",
        "sharaf dg bahrain",
        "virgin megastore bahrain",
        "best al yousifi",
        "ashraf"
    ],
    "saudi_arabia": [
        "amazon.sa",
        "jarir bookstore",
        "extra stores",
        "carrefour saudi",
        "noon.com"
    ],
    "uae": [
        "amazon.ae",
        "noon.com",
        "sharaf dg",
        "carrefour uae",
        "lulu hypermarket"
    ],
    "kuwait": [
        "xcite kuwait",
        "best al yousifi",
        "carrefour kuwait",
        "lulu hypermarket"
    ],
    "qatar": [
        "carrefour qatar",
        "lulu hypermarket qatar",
        "jarir bookstore qatar",
        "virgin megastore qatar"
    ],
    "oman": [
        "carrefour oman",
        "lulu hypermarket oman",
        "sharaf dg oman"
    ]
}


async def search_gcc_retailer_prices(
    product: str,
    region: str = "bahrain"
) -> List[Dict[str, Any]]:
    """
    Search specific GCC retailers for prices.
    
    Returns list of prices from different retailers.
    """
    retailers = GCC_RETAILERS.get(region, GCC_RETAILERS["bahrain"])
    results = []
    
    # Search top 3 retailers
    for retailer in retailers[:3]:
        query = f"{product} {retailer} price"
        search_result = await search_web(query, num_results=3)
        
        results.append({
            "retailer": retailer,
            "results": search_result.get("organic", [])[:2]
        })
    
    return results


# ============================================
# Utility functions
# ============================================

def extract_prices_from_text(text: str, currency: str = "BHD") -> List[Dict]:
    """
    Extract price patterns from text.
    
    Patterns:
    - BHD 99.99
    - 99.99 BHD
    - BD 99.99
    - $99.99
    """
    import re
    
    patterns = [
        # BHD/BD patterns
        r'(?:BHD|BD)\s*(\d+(?:\.\d{1,3})?)',
        r'(\d+(?:\.\d{1,3})?)\s*(?:BHD|BD)',
        # SAR patterns
        r'(?:SAR|SR)\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:SAR|SR)',
        # AED patterns
        r'(?:AED|DHS?)\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:AED|DHS?)',
        # USD patterns
        r'\$\s*(\d+(?:\.\d{1,2})?)',
        # Generic number with decimal
        r'(\d+\.\d{2,3})\s*(?:dinar|riyal)?'
    ]
    
    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                amount = float(match)
                if 0.1 < amount < 10000:  # Reasonable price range
                    prices.append({
                        "amount": amount,
                        "currency": currency,
                        "raw_text": match
                    })
            except ValueError:
                continue
    
    return prices

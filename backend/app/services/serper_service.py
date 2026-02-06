"""
Serper Service - Web search for product prices
"""
import os
import httpx
from typing import Dict, Optional

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_URL = "https://google.serper.dev/search"


async def search_product_price(
    brand: str,
    name: str,
    size: Optional[str] = None,
    country: str = "Bahrain"
) -> Dict:
    """
    Search for product price using Serper Google Search API.
    
    Args:
        brand: Product brand name
        name: Product name
        size: Product size/weight (optional)
        country: Target country for search
    
    Returns:
        {
            "success": True,
            "snippets": [
                {"title": "...", "snippet": "...", "link": "..."},
                ...
            ],
            "query": "search query used"
        }
        
        OR on failure:
        {
            "success": False,
            "error": "Error message",
            "query": "search query used"
        }
    """
    
    # Build search query
    query_parts = [brand, name]
    if size:
        query_parts.append(size)
    query_parts.extend(["price", country])
    query = " ".join(query_parts)
    
    # Country code mapping for Serper
    country_codes = {
        "Bahrain": "bh",
        "Saudi Arabia": "sa",
        "UAE": "ae",
        "Kuwait": "kw",
        "Qatar": "qa",
        "Oman": "om",
        "USA": "us",
        "UK": "uk"
    }
    gl_code = country_codes.get(country, "bh")
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": query,
        "num": 5,  # Only 5 results to minimize cost
        "gl": gl_code,
        "hl": "en"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.post(
                SERPER_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                organic_results = data.get("organic", [])
                
                # Extract relevant fields
                snippets = []
                for result in organic_results[:5]:
                    snippets.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "link": result.get("link", "")
                    })
                
                return {
                    "success": True,
                    "snippets": snippets,
                    "query": query,
                    "results_count": len(snippets)
                }
            
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "Invalid Serper API key",
                    "query": query
                }
            
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "Serper rate limit exceeded",
                    "query": query
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Serper API error: HTTP {response.status_code}",
                    "query": query
                }
    
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Search request timed out",
            "query": query
        }
    
    except httpx.ConnectError:
        return {
            "success": False,
            "error": "Could not connect to Serper API",
            "query": query
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "query": query
        }


async def search_product_reviews(
    brand: str,
    name: str,
    size: Optional[str] = None
) -> Dict:
    """
    Search for product reviews (optional feature for future use).
    
    Args:
        brand: Product brand name
        name: Product name
        size: Product size/weight (optional)
    
    Returns:
        Similar structure to search_product_price
    """
    
    query_parts = [brand, name]
    if size:
        query_parts.append(size)
    query_parts.append("review")
    query = " ".join(query_parts)
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": query,
        "num": 3,
        "hl": "en"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.post(
                SERPER_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                organic_results = data.get("organic", [])
                
                snippets = []
                for result in organic_results[:3]:
                    snippets.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "link": result.get("link", "")
                    })
                
                return {
                    "success": True,
                    "snippets": snippets,
                    "query": query
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "query": query
                }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

"""
Serper Service - Web search via Serper API (Google Search)
Enhanced for structured product data extraction
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

# Bundle C § 1c A.3.3-fix-1 — Serper credit-meter integration. Every
# successful Serper call (HTTP 200) bumps the Redis counter so the
# admin/costs Serper figure reflects actual usage. Missing-API-key and
# exception paths skip the bump (we don't bill non-events).
from app.services.api_budget_service import record_usage

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
            record_usage("serper")
            return response.json()

    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"organic": [], "error": str(e)}


# Bundle C § 1c A.3.3-fix-2 — Serper Shopping has thin GCC coverage.
# Direct-curl diagnostic (Session 52) showed gl=bh returns empty
# shopping[] for mainstream queries (iPhone 16, CeraVe, Centrum) while
# gl=us returns 20-40 items. The fallback below retries once with gl=us
# when the primary GCC country returns empty; downstream price_service
# converts USD→BHD via exchange_rate_service + tags source_method:
# 'converted_usd'. OPERATIONAL STOPGAP until Google Shopping's Bahrain
# merchant feed catches up.
_GCC_COUNTRIES = frozenset({"bh", "sa", "ae", "kw", "qa", "om"})


# Bundle C HOTFIX-2 round 2 — GPT-emitted product_info["search_query"]
# sometimes appends operator-style suffixes like "price", "buy", "best
# price" because PRODUCT_PARSER_PROMPT (extraction_service.py:71+82)
# tells GPT to emit "an optimized search query for price searches".
# Direct curl proves these suffixes KILL Google Shopping match:
#   q="Apple iPhone 16 price" gl=us → 0 items
#   q="iPhone 16"             gl=us → 20 items
# Strip defensively so cached + new GPT outputs both work. The match
# is case-insensitive, only trailing tokens, only the operator words
# below (does not touch product-essential keywords like "Pro", "Plus").
import re as _re

_SHOPPING_QUERY_TAIL_NOISE = _re.compile(
    r"(?:\s+(?:price|prices|pricing|cost|buy|best\s+price|cheapest|deals?|sale|"
    r"on\s+sale|amazon|noon|carrefour|bahrain|saudi(?:\s+arabia)?|uae|"
    r"dubai|kuwait|qatar|oman|bhd|sar|aed|kwd|qar|omr|usd))+\s*$",
    _re.IGNORECASE,
)


def _clean_shopping_query(product: str) -> str:
    """Strip trailing operator-style suffixes that wreck Google Shopping
    match. Idempotent — calling twice is a no-op. Preserves all interior
    tokens (only the trailing run is removed). Applied repeatedly until
    no more trailing tail noise — handles 'iPhone price Bahrain BHD buy'
    by chewing one operator-run at a time."""
    if not product:
        return product
    prev = None
    cleaned = product
    while cleaned != prev:
        prev = cleaned
        cleaned = _SHOPPING_QUERY_TAIL_NOISE.sub("", cleaned).strip()
    return cleaned or product  # never return empty string


async def _do_serper_shopping(product: str, gl: str) -> Dict[str, Any]:
    """Single Serper Shopping call. Records usage on HTTP 200. Returns
    parsed JSON or {} on error. No retry, no fallback — fallback logic
    lives in the caller (search_product_prices)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            shopping_response = await client.post(
                f"{SERPER_BASE_URL}/shopping",
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": product,
                    "gl": gl,
                    "hl": "en",
                    "num": 10
                }
            )
            if shopping_response.status_code == 200:
                record_usage("serper")
                return shopping_response.json()
            # Bundle C v1.1 § 1c SERPER_SHOPPING_NON_200 — capture what
            # Serper actually returns when not 200 so we can disambiguate
            # the 3 likely production failure modes:
            #   1. HTTP 429 + Retry-After  → rate limit (op fix)
            #   2. HTTP 200 empty shopping  → genuine coverage gap
            #      (this branch never fires for empty-but-200; here for
            #      completeness as a reminder that 200 is the success arm)
            #   3. HTTP 4xx other-shape    → request-side bug grep missed
            # All Serper POSTs in this codebase explicitly set
            # Content-Type: application/json AND use httpx json= kwarg
            # (auto-set) — verified by grep at all 7 sites. So a 400
            # here would point to a different cause than the header.
            # Always-on WARNING — appears in Railway prod without flag.
            # Body truncated to 300 chars to keep log lines bounded.
            try:
                body_snippet = (shopping_response.text or "")[:300]
            except Exception:  # noqa: BLE001
                body_snippet = "<unreadable>"
            retry_after = shopping_response.headers.get("retry-after")
            ratelimit_remaining = shopping_response.headers.get(
                "x-ratelimit-remaining"
            )
            logger.warning(
                "SERPER_SHOPPING_NON_200 gl=%s status=%s "
                "retry_after=%s ratelimit_remaining=%s "
                "body=%r product=%r",
                gl,
                shopping_response.status_code,
                retry_after,
                ratelimit_remaining,
                body_snippet,
                product[:80],
            )
            return {}
    except Exception as e:
        logger.error(f"Serper shopping call error (gl={gl}): {e}")
        return {}


async def search_product_prices(
    product: str,
    country: str = "bh",
    currency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for product prices via Serper Shopping API.

    Bundle C § 1c A.3.3-fix-2: when the GCC primary call returns an empty
    `shopping[]` array, retry ONCE with `gl=us` so downstream USD→BHD
    conversion can land real prices. The response's `shopping_region`
    field identifies which call's items are returned so admin
    dashboards can monitor fallback rate.

    Organic search is deferred to search_price_organic() and only
    called if both shopping calls return empty (Saudi-only items like
    Almarai laban — pipeline naturally falls through to Tier 1.5).
    """
    if not SERPER_API_KEY:
        return {"shopping": [], "organic": [], "error": "Search not configured"}

    # HOTFIX-2 round 2 — drop GPT-emitted " price"/"buy"/etc. tails.
    # Both primary GCC and us_fallback share the cleaned string so
    # behaviour is consistent. Log when we actually changed something
    # so Ahmed can see in Railway whether old GPT outputs are still
    # producing dirty queries.
    original_product = product
    product = _clean_shopping_query(product)
    if product != original_product:
        logger.info(
            f"[SHOPPING_QUERY_CLEAN] before={original_product!r} after={product!r}"
        )

    primary = await _do_serper_shopping(product, gl=country)
    primary_shopping = primary.get("shopping", []) or []
    if primary_shopping:
        return {
            "shopping": primary_shopping,
            "organic": [],
            "query": product,
            "shopping_region": country,
        }

    # GCC fallback to gl=us — only when primary is empty AND country is GCC.
    if country in _GCC_COUNTRIES:
        fallback = await _do_serper_shopping(product, gl="us")
        fallback_shopping = fallback.get("shopping", []) or []
        if fallback_shopping:
            return {
                "shopping": fallback_shopping,
                "organic": [],
                "query": product,
                "shopping_region": "us_fallback",
            }
        # Both empty — pipeline falls through to Tier 1.5 / Tier 2 / Tier 3.
        return {
            "shopping": [],
            "organic": [],
            "query": product,
            "shopping_region": "us_fallback",
        }

    # Non-GCC primary returned empty — no fallback, just echo the primary
    # region tag so callers know we tried.
    return {
        "shopping": [],
        "organic": [],
        "query": product,
        "shopping_region": country,
    }


async def search_price_organic(
    product: str,
    country: str = "bh",
) -> Dict[str, Any]:
    """
    Organic search for price context — only called when Tier 1 shopping fails.
    Returns organic results for GPT Tier 2 price extraction.
    """
    if not SERPER_API_KEY:
        return {"organic": [], "error": "Search not configured"}

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
            response = await client.post(
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

            results = {}
            if response.status_code == 200:
                results = response.json()
                record_usage("serper")

            return {
                "organic": results.get("organic", []),
                "knowledge_graph": results.get("knowledgeGraph"),
                "query": search_query
            }

    except Exception as e:
        logger.error(f"Price organic search error: {e}")
        return {"organic": [], "error": str(e)}


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
            record_usage("serper")
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
            record_usage("serper")
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
            record_usage("serper")
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

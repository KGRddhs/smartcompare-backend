"""
Deterministic Rating Extraction Service
Fetches actual product pages and extracts ratings from structured data

NO AI GENERATION - Only real data from real pages
NO DEFAULTS - Never return 4.5/150 or any placeholder

Extraction methods (in order of preference):
1. JSON-LD structured data (schema.org/AggregateRating)
2. Meta tags (og:rating, product:rating)
3. Site-specific CSS selectors

Supported sources:
- Amazon (.com, .ae, .sa)
- Newegg
- BestBuy
- Walmart
- Ubuy
- Noon
- B&H Photo
"""
import os
import re
import json
import logging
import httpx
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse
from dataclasses import dataclass

# Try to import BeautifulSoup, provide fallback if not available
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Supported retailers with their search patterns
SUPPORTED_RETAILERS = {
    "amazon.com": {
        "name": "Amazon US",
        "search_query": "{product} site:amazon.com",
        "rating_selectors": ["#acrPopover", "[data-hook='rating-out-of-text']", ".a-icon-star"],
        "review_selectors": ["#acrCustomerReviewText", "[data-hook='total-review-count']"],
    },
    "amazon.ae": {
        "name": "Amazon UAE",
        "search_query": "{product} site:amazon.ae",
        "rating_selectors": ["#acrPopover", "[data-hook='rating-out-of-text']"],
        "review_selectors": ["#acrCustomerReviewText"],
    },
    "newegg.com": {
        "name": "Newegg",
        "search_query": "{product} site:newegg.com",
        "rating_selectors": [".product-rating", "[itemprop='ratingValue']"],
        "review_selectors": [".product-review-count", "[itemprop='reviewCount']"],
    },
    "bestbuy.com": {
        "name": "Best Buy",
        "search_query": "{product} site:bestbuy.com",
        "rating_selectors": [".c-ratings-reviews", "[itemprop='ratingValue']"],
        "review_selectors": [".c-ratings-reviews-count", "[itemprop='reviewCount']"],
    },
    "walmart.com": {
        "name": "Walmart",
        "search_query": "{product} site:walmart.com",
        "rating_selectors": ["[data-testid='product-ratings']", ".stars-container"],
        "review_selectors": ["[data-testid='reviews-count']"],
    },
    "ubuy.com.bh": {
        "name": "Ubuy Bahrain",
        "search_query": "{product} site:ubuy.com.bh",
        "rating_selectors": [".product-rating", ".star-rating"],
        "review_selectors": [".review-count"],
    },
    "noon.com": {
        "name": "Noon",
        "search_query": "{product} site:noon.com",
        "rating_selectors": [".rating", "[class*='rating']"],
        "review_selectors": [".reviewCount", "[class*='review']"],
    },
    "bhphotovideo.com": {
        "name": "B&H Photo",
        "search_query": "{product} site:bhphotovideo.com",
        "rating_selectors": ["[itemprop='ratingValue']", ".ratings"],
        "review_selectors": ["[itemprop='reviewCount']"],
    },
}


@dataclass
class ExtractedRating:
    """Verified rating with full provenance."""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[str] = None
    extract_method: Optional[str] = None  # "json_ld", "meta_tags", "css_selector"
    raw_data: Optional[Dict] = None  # For debugging
    
    def is_valid(self) -> bool:
        """Rating is valid only if we have rating + source_url."""
        return (
            self.rating is not None and
            0 < self.rating <= 5 and
            self.source_url is not None and
            len(self.source_url) > 0
        )
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format."""
        if not self.is_valid():
            return {
                "rating": None,
                "review_count": None,
                "rating_verified": False,
                "rating_source": None
            }
        
        return {
            "rating": round(self.rating, 1),
            "review_count": self.review_count,
            "rating_verified": True,
            "rating_source": {
                "name": self.source_name,
                "url": self.source_url,
                "retrieved_at": self.retrieved_at,
                "extract_method": self.extract_method,
                "confidence": "high" if self.extract_method == "json_ld" else "medium"
            }
        }
    
    def to_debug(self) -> Dict[str, Any]:
        """Full debug info."""
        return {
            "rating": self.rating,
            "review_count": self.review_count,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "extract_method": self.extract_method,
            "is_valid": self.is_valid(),
            "raw_data": self.raw_data
        }


async def extract_rating_deterministic(product_name: str) -> ExtractedRating:
    """
    Extract rating using deterministic methods:
    1. Find product page on supported retailers
    2. Fetch the page
    3. Extract rating from JSON-LD or selectors
    
    Returns ExtractedRating with full provenance.
    """
    if not BS4_AVAILABLE:
        logger.warning("[RATING] BeautifulSoup not available - install with: pip install beautifulsoup4")
        return ExtractedRating()
    
    logger.info(f"[RATING] Starting deterministic extraction for: {product_name}")
    
    # Try each retailer in order of reliability
    retailer_order = [
        "amazon.com",      # Best structured data
        "newegg.com",      # Good for tech
        "bestbuy.com",     # Good structured data
        "bhphotovideo.com", # Good for electronics
        "walmart.com",     # Large catalog
        "amazon.ae",       # GCC region
        "ubuy.com.bh",     # GCC region
        "noon.com",        # GCC region
    ]
    
    for retailer_domain in retailer_order:
        retailer = SUPPORTED_RETAILERS[retailer_domain]
        logger.info(f"[RATING] Trying {retailer['name']}...")
        
        try:
            # Step 1: Find product page URL
            product_url = await find_product_page(product_name, retailer_domain, retailer)
            
            if not product_url:
                logger.debug(f"[RATING] No product page found on {retailer['name']}")
                continue
            
            logger.info(f"[RATING] Found product page: {product_url}")
            
            # Step 2: Fetch page content
            html_content = await fetch_page_content(product_url)
            
            if not html_content:
                logger.debug(f"[RATING] Could not fetch page: {product_url}")
                continue
            
            # Step 3: Extract rating (try multiple methods)
            rating = extract_rating_from_html(html_content, product_url, retailer)
            
            if rating.is_valid():
                logger.info(f"[RATING] ✓ SUCCESS: {rating.rating}/5 ({rating.review_count} reviews) "
                           f"from {rating.source_name} via {rating.extract_method}")
                return rating
            else:
                logger.debug(f"[RATING] Could not extract rating from {product_url}")
                
        except Exception as e:
            logger.error(f"[RATING] Error with {retailer['name']}: {str(e)}")
            continue
    
    logger.warning(f"[RATING] No rating found for: {product_name}")
    return ExtractedRating()


async def find_product_page(product_name: str, domain: str, retailer: Dict) -> Optional[str]:
    """Find product page URL on a specific retailer."""
    if not SERPER_API_KEY:
        return None
    
    query = retailer["search_query"].format(product=product_name)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 5}
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Find first result that matches the domain
            for result in data.get("organic", []):
                url = result.get("link", "")
                if domain in url and is_product_page(url, domain):
                    return url
            
            return None
            
    except Exception as e:
        logger.error(f"[RATING] Search error: {e}")
        return None


def is_product_page(url: str, domain: str) -> bool:
    """Check if URL looks like a product page (not category/search)."""
    url_lower = url.lower()
    
    # Exclude patterns
    exclude_patterns = [
        "/s?", "/search", "/category", "/browse", "/b/", 
        "/gp/bestsellers", "/deals", "/stores"
    ]
    
    for pattern in exclude_patterns:
        if pattern in url_lower:
            return False
    
    # Include patterns (product pages)
    include_patterns = {
        "amazon": ["/dp/", "/gp/product/", "/product/"],
        "newegg": ["/p/", "/Product/"],
        "bestbuy": ["/site/", "/skuId="],
        "walmart": ["/ip/"],
        "bhphotovideo": ["/c/product/"],
        "noon": ["/p/"],
        "ubuy": ["/product/"],
    }
    
    for site, patterns in include_patterns.items():
        if site in domain:
            return any(p in url for p in patterns)
    
    # Default: accept if it has product-like patterns
    return "/product" in url_lower or "/dp/" in url_lower or "/p/" in url_lower


async def fetch_page_content(url: str) -> Optional[str]:
    """Fetch page HTML content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.debug(f"[RATING] Fetch failed with status {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"[RATING] Fetch error: {e}")
        return None


def extract_rating_from_html(html: str, url: str, retailer: Dict) -> ExtractedRating:
    """
    Extract rating from HTML using multiple methods:
    1. JSON-LD structured data (preferred)
    2. Meta tags
    3. Site-specific CSS selectors
    """
    retrieved_at = datetime.utcnow().isoformat() + "Z"
    source_name = retailer["name"]
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Method 1: JSON-LD structured data (most reliable)
    rating = extract_from_json_ld(soup)
    if rating["value"]:
        return ExtractedRating(
            rating=rating["value"],
            review_count=rating["count"],
            source_name=source_name,
            source_url=url,
            retrieved_at=retrieved_at,
            extract_method="json_ld",
            raw_data=rating.get("raw")
        )
    
    # Method 2: Schema.org microdata
    rating = extract_from_microdata(soup)
    if rating["value"]:
        return ExtractedRating(
            rating=rating["value"],
            review_count=rating["count"],
            source_name=source_name,
            source_url=url,
            retrieved_at=retrieved_at,
            extract_method="microdata",
            raw_data=rating.get("raw")
        )
    
    # Method 3: Meta tags
    rating = extract_from_meta_tags(soup)
    if rating["value"]:
        return ExtractedRating(
            rating=rating["value"],
            review_count=rating["count"],
            source_name=source_name,
            source_url=url,
            retrieved_at=retrieved_at,
            extract_method="meta_tags"
        )
    
    # Method 4: Site-specific selectors
    rating = extract_from_selectors(soup, retailer, html)
    if rating["value"]:
        return ExtractedRating(
            rating=rating["value"],
            review_count=rating["count"],
            source_name=source_name,
            source_url=url,
            retrieved_at=retrieved_at,
            extract_method="css_selector"
        )
    
    return ExtractedRating(source_url=url, source_name=source_name, retrieved_at=retrieved_at)


def extract_from_json_ld(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract rating from JSON-LD structured data."""
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            
            # Handle array of objects
            if isinstance(data, list):
                for item in data:
                    rating = find_aggregate_rating(item)
                    if rating["value"]:
                        return rating
            else:
                rating = find_aggregate_rating(data)
                if rating["value"]:
                    return rating
                    
        except (json.JSONDecodeError, TypeError):
            continue
    
    return {"value": None, "count": None}


def find_aggregate_rating(data: Dict) -> Dict[str, Any]:
    """Find AggregateRating in JSON-LD object."""
    if not isinstance(data, dict):
        return {"value": None, "count": None}
    
    # Direct AggregateRating
    if data.get("@type") == "AggregateRating":
        return parse_rating_object(data)
    
    # Nested in Product or other type
    aggregate = data.get("aggregateRating")
    if aggregate:
        return parse_rating_object(aggregate)
    
    # Check nested objects
    for key, value in data.items():
        if isinstance(value, dict):
            rating = find_aggregate_rating(value)
            if rating["value"]:
                return rating
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    rating = find_aggregate_rating(item)
                    if rating["value"]:
                        return rating
    
    return {"value": None, "count": None}


def parse_rating_object(obj: Dict) -> Dict[str, Any]:
    """Parse rating value and count from rating object."""
    rating_value = None
    review_count = None
    
    # Get rating value
    for key in ["ratingValue", "rating_value", "value"]:
        if obj.get(key):
            try:
                rating_value = float(obj[key])
                break
            except (ValueError, TypeError):
                continue
    
    # Get review count
    for key in ["reviewCount", "review_count", "ratingCount", "count"]:
        if obj.get(key):
            try:
                review_count = int(str(obj[key]).replace(",", ""))
                break
            except (ValueError, TypeError):
                continue
    
    # Validate rating is in expected range
    if rating_value:
        best_rating = float(obj.get("bestRating", 5))
        if rating_value > 5 and best_rating > 5:
            # Normalize to 5-star scale
            rating_value = (rating_value / best_rating) * 5
    
    return {
        "value": rating_value if rating_value and 0 < rating_value <= 5 else None,
        "count": review_count,
        "raw": obj
    }


def extract_from_microdata(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract rating from schema.org microdata."""
    # Find AggregateRating itemtype
    rating_element = soup.find(itemtype=re.compile(r"schema\.org.*AggregateRating", re.I))
    
    if rating_element:
        rating_value = None
        review_count = None
        
        # Find ratingValue
        value_elem = rating_element.find(itemprop="ratingValue")
        if value_elem:
            try:
                rating_value = float(value_elem.get("content") or value_elem.text.strip())
            except (ValueError, TypeError):
                pass
        
        # Find reviewCount
        count_elem = rating_element.find(itemprop="reviewCount")
        if count_elem:
            try:
                review_count = int((count_elem.get("content") or count_elem.text.strip()).replace(",", ""))
            except (ValueError, TypeError):
                pass
        
        if rating_value and 0 < rating_value <= 5:
            return {"value": rating_value, "count": review_count}
    
    # Also try finding by itemprop directly
    rating_elem = soup.find(itemprop="ratingValue")
    if rating_elem:
        try:
            rating_value = float(rating_elem.get("content") or rating_elem.text.strip())
            
            count_elem = soup.find(itemprop="reviewCount")
            review_count = None
            if count_elem:
                review_count = int((count_elem.get("content") or count_elem.text.strip()).replace(",", ""))
            
            if rating_value and 0 < rating_value <= 5:
                return {"value": rating_value, "count": review_count}
        except (ValueError, TypeError):
            pass
    
    return {"value": None, "count": None}


def extract_from_meta_tags(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract rating from meta tags."""
    rating_value = None
    review_count = None
    
    # Check various meta tag formats
    meta_patterns = [
        ("property", "og:rating"),
        ("property", "product:rating:value"),
        ("name", "rating"),
        ("itemprop", "ratingValue"),
    ]
    
    for attr, value in meta_patterns:
        meta = soup.find("meta", {attr: value})
        if meta and meta.get("content"):
            try:
                rating_value = float(meta["content"])
                if 0 < rating_value <= 5:
                    break
            except (ValueError, TypeError):
                continue
    
    # Review count meta
    count_patterns = [
        ("property", "og:rating:count"),
        ("property", "product:rating:count"),
        ("name", "review_count"),
    ]
    
    for attr, value in count_patterns:
        meta = soup.find("meta", {attr: value})
        if meta and meta.get("content"):
            try:
                review_count = int(meta["content"].replace(",", ""))
                break
            except (ValueError, TypeError):
                continue
    
    return {
        "value": rating_value if rating_value and 0 < rating_value <= 5 else None,
        "count": review_count
    }


def extract_from_selectors(soup: BeautifulSoup, retailer: Dict, html: str) -> Dict[str, Any]:
    """Extract rating using site-specific CSS selectors."""
    rating_value = None
    review_count = None
    
    # Try rating selectors
    for selector in retailer.get("rating_selectors", []):
        try:
            element = soup.select_one(selector)
            if element:
                # Extract rating from element
                text = element.get("title") or element.get("aria-label") or element.text
                rating_value = parse_rating_text(text)
                if rating_value:
                    break
        except Exception:
            continue
    
    # Try review count selectors
    for selector in retailer.get("review_selectors", []):
        try:
            element = soup.select_one(selector)
            if element:
                text = element.text
                review_count = parse_review_count(text)
                if review_count:
                    break
        except Exception:
            continue
    
    # Amazon-specific: look for rating in specific patterns
    if not rating_value:
        # Amazon pattern: "4.5 out of 5 stars"
        match = re.search(r'(\d+\.?\d*)\s*out of\s*5\s*stars?', html, re.I)
        if match:
            try:
                rating_value = float(match.group(1))
            except ValueError:
                pass
    
    # Look for review count pattern
    if not review_count:
        # Pattern: "1,234 ratings" or "1,234 reviews"
        match = re.search(r'([\d,]+)\s*(?:ratings?|reviews?|customer reviews?)', html, re.I)
        if match:
            try:
                review_count = int(match.group(1).replace(",", ""))
            except ValueError:
                pass
    
    return {
        "value": rating_value if rating_value and 0 < rating_value <= 5 else None,
        "count": review_count
    }


def parse_rating_text(text: str) -> Optional[float]:
    """Parse rating from various text formats."""
    if not text:
        return None
    
    patterns = [
        r'(\d+\.?\d*)\s*out of\s*5',
        r'(\d+\.?\d*)\s*/\s*5',
        r'(\d+\.?\d*)\s*stars?',
        r'rating[:\s]+(\d+\.?\d*)',
        r'^(\d+\.?\d*)$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                value = float(match.group(1))
                if 0 < value <= 5:
                    return value
            except ValueError:
                continue
    
    return None


def parse_review_count(text: str) -> Optional[int]:
    """Parse review count from text."""
    if not text:
        return None
    
    # Remove common words and extract number
    match = re.search(r'([\d,]+)', text)
    if match:
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            pass
    
    return None


# ============================================
# CACHING
# ============================================

async def get_cached_rating(product_name: str) -> Optional[ExtractedRating]:
    """Get rating from cache if not expired."""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return None
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Check for cached rating (TTL: 24 hours)
        result = supabase.table("rating_cache").select("*").eq(
            "product_name", product_name.lower()
        ).gt(
            "expires_at", datetime.utcnow().isoformat()
        ).limit(1).execute()
        
        if result.data:
            cached = result.data[0]
            return ExtractedRating(
                rating=cached.get("rating"),
                review_count=cached.get("review_count"),
                source_name=cached.get("source_name"),
                source_url=cached.get("source_url"),
                retrieved_at=cached.get("retrieved_at"),
                extract_method=cached.get("extract_method")
            )
        
        return None
        
    except Exception as e:
        logger.error(f"[RATING] Cache read error: {e}")
        return None


async def save_rating_to_cache(product_name: str, rating: ExtractedRating):
    """Save rating to cache with 24h TTL."""
    if not rating.is_valid():
        return
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Upsert rating cache
        supabase.table("rating_cache").upsert({
            "product_name": product_name.lower(),
            "rating": rating.rating,
            "review_count": rating.review_count,
            "source_name": rating.source_name,
            "source_url": rating.source_url,
            "retrieved_at": rating.retrieved_at,
            "extract_method": rating.extract_method,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }, on_conflict="product_name").execute()
        
        logger.info(f"[RATING] Cached rating for: {product_name}")
        
    except Exception as e:
        logger.error(f"[RATING] Cache write error: {e}")


# ============================================
# MAIN API
# ============================================

async def get_verified_rating(product_name: str) -> ExtractedRating:
    """
    Get verified rating with full provenance.
    Uses cache if available, otherwise extracts from real pages.
    """
    # Check cache first
    cached = await get_cached_rating(product_name)
    if cached and cached.is_valid():
        logger.info(f"[RATING] Cache hit for: {product_name}")
        return cached
    
    # Extract from real pages
    rating = await extract_rating_deterministic(product_name)
    
    # Cache valid ratings
    if rating.is_valid():
        await save_rating_to_cache(product_name, rating)
    
    return rating


def validate_rating_for_api(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    API layer validation - strips ratings without source_url.
    ENFORCES: rating must always include source_url.
    """
    rating = product_data.get("rating")
    source = product_data.get("rating_source")
    
    if rating is not None:
        # STRICT: Must have source with URL
        has_valid_source = (
            isinstance(source, dict) and
            source.get("url") and
            len(source.get("url", "")) > 0
        )
        
        if not has_valid_source:
            logger.warning(f"[RATING] Stripping rating {rating} - no source_url")
            product_data["rating"] = None
            product_data["review_count"] = None
            product_data["rating_verified"] = False
            product_data["rating_source"] = None
    
    return product_data


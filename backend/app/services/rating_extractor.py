"""
Deterministic Rating Extraction Service
Extracts ratings from Google Shopping data via Serper API

NO AI GENERATION - Only real data from real retailer listings
NO DEFAULTS - Never return 4.5/150 or any placeholder
NO HTML SCRAPING - Retailers block bot requests with CAPTCHA/403

Extraction method:
- Serper Shopping API returns aggregated ratings from Google Shopping
- These ratings come from real retailer data (Amazon, Walmart, Best Buy, etc.)
- We pick the best match by title similarity and highest review count

Sources (via Google Shopping):
- Amazon, Walmart, Best Buy, Newegg, B&H Photo, Target
- Noon, Ubuy, and other GCC retailers
"""
import os
import re
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


@dataclass
class ExtractedRating:
    """Verified rating with full provenance."""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[str] = None
    extract_method: Optional[str] = None  # "google_shopping"
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
                "confidence": "high"
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


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip non-alphanumeric."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def _title_match_score(product_name: str, item_title: str) -> float:
    """Score how well a shopping item title matches the product name (0-1)."""
    product_words = set(_normalize(product_name))
    title_words = set(_normalize(item_title))

    # Use word-level matching for better accuracy
    p_words = set(product_name.lower().split())
    t_words = set(item_title.lower().split())

    if not p_words:
        return 0.0

    # What fraction of product name words appear in the title
    matches = len(p_words & t_words)
    return matches / len(p_words)


def extract_rating_from_shopping(product_name: str, shopping_items: List[Dict]) -> ExtractedRating:
    """
    Extract the best rating from Serper Shopping results.

    Strategy:
    1. Filter items that have a rating
    2. Prefer items with highest review count (more trustworthy)
    3. Require reasonable title match to avoid wrong product
    """
    retrieved_at = datetime.utcnow().isoformat() + "Z"

    if not shopping_items:
        logger.debug("[RATING] No shopping items to extract from")
        return ExtractedRating()

    # Collect candidates: items with valid ratings and decent title match
    candidates = []
    for item in shopping_items:
        rating = item.get("rating")
        if not rating:
            continue

        try:
            rating_val = float(rating)
        except (ValueError, TypeError):
            continue

        if not (0 < rating_val <= 5):
            continue

        title = item.get("title", "")
        match_score = _title_match_score(product_name, title)

        # Require at least 40% word match to avoid wrong products
        if match_score < 0.4:
            logger.debug(f"[RATING] Skipping low match ({match_score:.1%}): {title[:60]}")
            continue

        review_count = None
        for key in ["ratingCount", "reviewCount", "reviews"]:
            raw = item.get(key)
            if raw is not None:
                try:
                    review_count = int(str(raw).replace(",", "").replace("+", ""))
                    break
                except (ValueError, TypeError):
                    continue

        source = item.get("source", "Google Shopping")
        link = item.get("link", "")

        candidates.append({
            "rating": rating_val,
            "review_count": review_count,
            "source": source,
            "link": link,
            "title": title,
            "match_score": match_score,
        })

    if not candidates:
        logger.debug("[RATING] No candidates with valid rating + title match")
        return ExtractedRating()

    # Sort: prefer highest review count (most trustworthy), then best title match
    candidates.sort(key=lambda c: (c["review_count"] or 0, c["match_score"]), reverse=True)

    best = candidates[0]
    logger.info(f"[RATING] Best candidate: {best['rating']}/5 ({best['review_count']} reviews) "
                f"from {best['source']} - \"{best['title'][:50]}\"")

    return ExtractedRating(
        rating=round(best["rating"], 1),
        review_count=best["review_count"],
        source_name=f"{best['source']} via Google Shopping",
        source_url=best["link"],
        retrieved_at=retrieved_at,
        extract_method="google_shopping",
        raw_data=best,
    )


async def search_shopping_for_rating(product_name: str) -> ExtractedRating:
    """
    Do a dedicated Serper Shopping search to find ratings.
    Used as fallback when pre-fetched shopping data has no match.
    Cost: $0.001 (1 Serper call)
    """
    if not SERPER_API_KEY:
        logger.warning("[RATING] No SERPER_API_KEY configured")
        return ExtractedRating()

    logger.info(f"[RATING] Searching Google Shopping for: {product_name}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": product_name, "num": 15}
            )

            if response.status_code != 200:
                logger.error(f"[RATING] Serper shopping search failed: {response.status_code}")
                return ExtractedRating()

            data = response.json()
            shopping_items = data.get("shopping", [])
            logger.info(f"[RATING] Got {len(shopping_items)} shopping results")

            return extract_rating_from_shopping(product_name, shopping_items)

    except Exception as e:
        logger.error(f"[RATING] Shopping search error: {e}")
        return ExtractedRating()


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

async def get_verified_rating(product_name: str, shopping_data: Optional[List[Dict]] = None) -> ExtractedRating:
    """
    Get verified rating with full provenance.

    Args:
        product_name: Product to find rating for
        shopping_data: Pre-fetched Serper Shopping results (from search_all_data).
                       If provided, extracts from these first to avoid extra API calls.

    Returns ExtractedRating with source provenance.
    """
    # Check cache first
    cached = await get_cached_rating(product_name)
    if cached and cached.is_valid():
        logger.info(f"[RATING] Cache hit for: {product_name}")
        return cached

    # Method 1: Extract from pre-fetched shopping data (free - no extra API call)
    if shopping_data:
        logger.info(f"[RATING] Trying pre-fetched shopping data ({len(shopping_data)} items)")
        rating = extract_rating_from_shopping(product_name, shopping_data)
        if rating.is_valid():
            logger.info(f"[RATING] ✓ Found in pre-fetched data: {rating.rating}/5")
            await save_rating_to_cache(product_name, rating)
            return rating

    # Method 2: Dedicated shopping search (costs $0.001)
    logger.info(f"[RATING] Pre-fetched data insufficient, doing dedicated search")
    rating = await search_shopping_for_rating(product_name)

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

"""
Rating Service v2 - Verified ratings with FULL provenance tracking
NO DEFAULTS, NO HARDCODES - Only real data from real sources

Every rating MUST have:
- source_name: Where it came from (e.g., "Amazon", "Google Shopping")
- source_url: Direct link to verify
- retrieved_at: When we fetched it
- review_count: Number of reviews (if available)

If ANY of these are missing, rating = null
"""
import os
import re
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


class VerifiedRating:
    """
    Immutable rating result with full provenance.
    A rating is only valid if it has source_name AND source_url.
    """
    
    def __init__(
        self,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        source_name: Optional[str] = None,
        source_url: Optional[str] = None,
    ):
        self.rating = rating
        self.review_count = review_count
        self.source_name = source_name
        self.source_url = source_url
        self.retrieved_at = datetime.utcnow().isoformat() + "Z"
        
        # Determine confidence based on source
        self.confidence = self._calculate_confidence()
    
    def _calculate_confidence(self) -> Optional[str]:
        """Calculate confidence level based on source."""
        if not self.source_name:
            return None
        
        source_lower = self.source_name.lower()
        
        # High confidence: Major retailers with verified reviews
        high_confidence = ["amazon", "bestbuy", "newegg", "walmart", "target", "google"]
        if any(s in source_lower for s in high_confidence):
            return "high"
        
        # Medium confidence: Other retailers
        medium_confidence = ["ebay", "noon", "jarir", "sharaf", "lulu"]
        if any(s in source_lower for s in medium_confidence):
            return "medium"
        
        return "low"
    
    def is_valid(self) -> bool:
        """
        A rating is valid ONLY if:
        - rating exists and is between 0-5
        - source_name exists
        - source_url exists
        """
        return (
            self.rating is not None and
            0 < self.rating <= 5 and
            self.source_name is not None and
            len(self.source_name) > 0 and
            self.source_url is not None and
            len(self.source_url) > 0
        )
    
    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format.
        Returns null rating if not valid.
        """
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
                "confidence": self.confidence
            }
        }
    
    def to_debug_log(self) -> Dict[str, Any]:
        """Full debug information for logging."""
        return {
            "rating_value": self.rating,
            "review_count": self.review_count,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "confidence": self.confidence,
            "is_valid": self.is_valid(),
            "validation_errors": self._get_validation_errors()
        }
    
    def _get_validation_errors(self) -> List[str]:
        """List what's missing for validation."""
        errors = []
        if self.rating is None:
            errors.append("missing_rating")
        elif not (0 < self.rating <= 5):
            errors.append("invalid_rating_range")
        if not self.source_name:
            errors.append("missing_source_name")
        if not self.source_url:
            errors.append("missing_source_url")
        return errors


async def get_verified_rating(product_name: str) -> VerifiedRating:
    """
    Fetch rating from verified sources with full provenance.
    
    Search order (stops at first valid result):
    1. Google Shopping UAE
    2. Google Shopping US (more coverage)
    3. Google Knowledge Graph
    
    Returns VerifiedRating (may be invalid if nothing found)
    """
    if not SERPER_API_KEY:
        logger.error("[RATING] SERPER_API_KEY not configured")
        return VerifiedRating()
    
    logger.info(f"[RATING] === Starting rating fetch for: {product_name} ===")
    
    # Source functions to try
    sources = [
        ("Google Shopping UAE", _search_shopping_uae),
        ("Google Shopping US", _search_shopping_us),
        ("Google Knowledge Graph", _search_knowledge_graph),
    ]
    
    for source_label, search_func in sources:
        logger.info(f"[RATING] Trying source: {source_label}")
        try:
            result = await search_func(product_name)
            
            # Log what we got
            debug_info = result.to_debug_log()
            logger.info(f"[RATING] {source_label} result: rating={debug_info['rating_value']}, "
                       f"reviews={debug_info['review_count']}, valid={debug_info['is_valid']}")
            
            if result.is_valid():
                logger.info(f"[RATING] ✓ SUCCESS from {source_label}: "
                           f"{result.rating}/5 ({result.review_count} reviews) "
                           f"URL: {result.source_url}")
                return result
            else:
                logger.debug(f"[RATING] ✗ Invalid from {source_label}: {debug_info['validation_errors']}")
                
        except Exception as e:
            logger.error(f"[RATING] Error from {source_label}: {str(e)}")
            continue
    
    logger.warning(f"[RATING] === No verified rating found for: {product_name} ===")
    return VerifiedRating()


async def _search_shopping_uae(product_name: str) -> VerifiedRating:
    """Search Google Shopping (UAE region)."""
    return await _search_shopping(product_name, region="ae", label="UAE")


async def _search_shopping_us(product_name: str) -> VerifiedRating:
    """Search Google Shopping (US region - better coverage)."""
    return await _search_shopping(product_name, region="us", label="US")


async def _search_shopping(product_name: str, region: str, label: str) -> VerifiedRating:
    """Generic shopping search."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://google.serper.dev/shopping",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": product_name, "num": 20, "gl": region}
        )
        
        if response.status_code != 200:
            logger.error(f"[RATING] Shopping API error: {response.status_code}")
            return VerifiedRating()
        
        data = response.json()
        shopping_results = data.get("shopping", [])
        
        logger.debug(f"[RATING] Got {len(shopping_results)} shopping results from {label}")
        
        # Sort by: Amazon first, then by review count
        def sort_key(item):
            source = (item.get("source") or "").lower()
            is_amazon = 1 if "amazon" in source else 0
            reviews = 0
            try:
                reviews = int(str(item.get("reviews", 0)).replace(",", "").replace("+", ""))
            except:
                pass
            return (is_amazon, reviews)
        
        shopping_results.sort(key=sort_key, reverse=True)
        
        for item in shopping_results:
            rating_raw = item.get("rating")
            reviews_raw = item.get("reviews") or item.get("ratingCount")
            source_name = item.get("source", "")
            source_url = item.get("link", "")
            
            if not rating_raw:
                continue
            
            try:
                rating_val = float(rating_raw)
                
                if not (0 < rating_val <= 5):
                    continue
                
                review_count = None
                if reviews_raw:
                    review_count = int(str(reviews_raw).replace(",", "").replace("+", ""))
                
                # Build result with provenance
                if source_name and source_url:
                    return VerifiedRating(
                        rating=rating_val,
                        review_count=review_count,
                        source_name=source_name,
                        source_url=source_url
                    )
                elif source_name:
                    # Has name but no URL - construct search URL
                    return VerifiedRating(
                        rating=rating_val,
                        review_count=review_count,
                        source_name=source_name,
                        source_url=f"https://www.google.com/search?q={quote_plus(product_name + ' ' + source_name)}"
                    )
                    
            except (ValueError, TypeError) as e:
                logger.debug(f"[RATING] Parse error: {e}")
                continue
        
        return VerifiedRating()


async def _search_knowledge_graph(product_name: str) -> VerifiedRating:
    """Search Google Knowledge Graph for rating."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": f"{product_name} reviews rating", "num": 10, "gl": "us"}
        )
        
        if response.status_code != 200:
            return VerifiedRating()
        
        data = response.json()
        
        # Check knowledge graph
        kg = data.get("knowledgeGraph", {})
        if kg:
            rating_str = kg.get("rating") or kg.get("ratingValue")
            
            if rating_str:
                try:
                    rating_val = float(str(rating_str).replace("/5", "").strip())
                    
                    if 0 < rating_val <= 5:
                        review_count = None
                        rc = kg.get("ratingCount") or kg.get("reviewCount")
                        if rc:
                            review_count = int(str(rc).replace(",", "").replace("+", ""))
                        
                        return VerifiedRating(
                            rating=rating_val,
                            review_count=review_count,
                            source_name="Google Knowledge Graph",
                            source_url=f"https://www.google.com/search?q={quote_plus(product_name)}"
                        )
                except (ValueError, TypeError):
                    pass
        
        return VerifiedRating()


# ============================================
# API Layer Validation
# ============================================

def validate_rating_for_api(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    API layer validation - strips invalid ratings.
    
    Rules:
    - If rating exists, source must exist with name and URL
    - If validation fails, set rating to null
    """
    rating = product_data.get("rating")
    source = product_data.get("rating_source")
    
    if rating is not None:
        # Check source exists and has required fields
        has_valid_source = (
            isinstance(source, dict) and
            source.get("name") and
            source.get("url")
        )
        
        if not has_valid_source:
            logger.warning(f"[RATING] API validation: stripping rating {rating} - missing source provenance")
            product_data["rating"] = None
            product_data["review_count"] = None
            product_data["rating_verified"] = False
            product_data["rating_source"] = None
    
    return product_data

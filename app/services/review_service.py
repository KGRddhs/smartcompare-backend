"""Review Service — all review-related functions extracted from structured_comparison_service.

Functions are standalone (no self).
FIX M5: _clean_review_citations processes review_summary.highlights[].point format.
FIX M6: Removed dead code processing detailed_praises/detailed_complaints (never populated).
"""
import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from app.services.extraction_service import (
    extract_reviews,
    get_reviews_cache_key,
)
from app.services.serper_service import search_web
from app.services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)

# Cache TTL
REVIEWS_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days

# Category-specific review search terms
CATEGORY_REVIEW_TERMS = {
    "electronics": "user reviews pros cons battery camera performance display",
    "grocery": "user reviews taste quality ingredients value",
    "beauty": "user reviews results skin ingredients effectiveness",
    "fashion": "user reviews fit quality comfort sizing",
    "home": "user reviews quality durability assembly value",
    "sports": "user reviews performance comfort durability",
}

GARBAGE_PATTERNS = [
    r"learn more about",
    r"see (full |more )?details",
    r"click (here|to)",
    r"read more",
    r"shop now",
    r"free (shipping|delivery|returns)",
    r"add to (cart|bag|wishlist)",
    r"available (in|at) (stores|select)",
    r"sign up for",
    r"join (our|the) (newsletter|waitlist)",
]

NEGATIVE_INDICATORS = {
    "bad", "poor", "disappointing", "issue", "problem", "broke", "broken",
    "flimsy", "cheap", "overpriced", "uncomfortable", "fragile", "peeling",
    "fading", "cracking", "defect", "flaw", "mediocre", "underwhelming",
    "lacking", "missing", "difficult", "annoying", "frustrating", "worse", "worst",
}

POSITIVE_INDICATORS = {
    "great", "excellent", "premium", "beautiful", "perfect", "love",
    "amazing", "wonderful", "fantastic", "superb", "outstanding", "impressive",
    "comfortable", "luxurious", "elegant", "sturdy", "durable", "quality",
}


def clean_review_content(reviews: dict) -> dict:
    """Remove garbage text, short items, and misclassified sentiments from reviews."""
    for section in ["common_praises", "common_complaints"]:
        items = reviews.get(section, [])
        if not items:
            continue
        cleaned = []
        for item in items:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if any(re.search(p, text, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                continue
            if len(text.split()) < 8:
                continue
            if "complaint" in section:
                words = set(text.lower().split())
                has_negative = bool(words & NEGATIVE_INDICATORS)
                has_positive = bool(words & POSITIVE_INDICATORS)
                if has_positive and not has_negative:
                    continue
            cleaned.append(item)
        reviews[section] = cleaned

    # FIX M5: Also clean review_summary.highlights[].point
    review_summary = reviews.get("review_summary", {})
    if isinstance(review_summary, dict):
        highlights = review_summary.get("highlights", [])
        if highlights and isinstance(highlights, list):
            cleaned_highlights = []
            for h in highlights:
                if isinstance(h, dict):
                    point = h.get("point", "")
                    if any(re.search(p, point, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                        continue
                    if len(point.split()) < 4:
                        continue
                    cleaned_highlights.append(h)
                else:
                    cleaned_highlights.append(h)
            review_summary["highlights"] = cleaned_highlights

    return reviews


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or ""
    except Exception:
        return ""


def clean_review_citations(reviews: dict, search_results: list) -> dict:
    """Replace [snippet_N] with source domain name in review text fields.

    FIX M5: Now processes review_summary.highlights[].point format (current format).
    FIX M6: Removed dead code for detailed_praises/detailed_complaints (never populated).
    """
    snippet_source_map = {}
    for i, result in enumerate(search_results or []):
        link = result.get("link", "")
        if link:
            snippet_source_map[str(i + 1)] = _extract_domain(link)

    def replace_citation(text: str) -> str:
        def replacer(match):
            snippet_num = match.group(1)
            domain = snippet_source_map.get(snippet_num, "")
            if domain:
                return f"Per {domain}: "
            return ""
        return re.sub(r'\[snippet_(\d+)\]\s*', replacer, text)

    cleaned = dict(reviews)

    # Legacy fields (common_praises, common_complaints)
    for key in ["common_praises", "common_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            cleaned[key] = [replace_citation(str(item)) for item in cleaned[key]]

    # FIX M5: Current format — review_summary.highlights[].point
    review_summary = cleaned.get("review_summary", {})
    if isinstance(review_summary, dict):
        highlights = review_summary.get("highlights", [])
        if highlights and isinstance(highlights, list):
            for h in highlights:
                if isinstance(h, dict) and "point" in h:
                    h["point"] = replace_citation(str(h["point"]))

    return cleaned


def format_review_search_results(results: Dict, retailer_ratings: List[Dict]) -> str:
    """Format search results for review extraction."""
    if not results:
        return "No search results available."

    formatted = []

    organic = results.get("organic", [])[:10]
    for i, r in enumerate(organic):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        domain = ""
        if link:
            try:
                domain = urlparse(link).netloc.replace("www.", "")
            except Exception:
                pass
        prefix = f"[{domain}] " if domain else ""
        formatted.append(f"{i+1}. {prefix}{title}\n   {snippet}")

    if retailer_ratings:
        formatted.append("\n--- Retailer Ratings (from shopping data) ---")
        for r in retailer_ratings:
            count_str = f" ({r['review_count']} reviews)" if r.get("review_count") else ""
            formatted.append(f"- {r['source']}: {r['rating']}/5{count_str}")

    return "\n".join(formatted)


async def get_reviews(
    brand: str,
    name: str,
    variant: Optional[str],
    search_query: str,
    nocache: bool = False,
    category: str = "other",
    retailer_ratings: Optional[List[Dict]] = None,
    search_results: Optional[Dict] = None,
    track_serper_cost_fn=None,
    track_gpt_cost_fn=None,
) -> Dict[str, Any]:
    """Get reviews with caching (L1: Redis, L2: DB)."""
    import asyncio
    cache_key = get_reviews_cache_key(brand, name, variant)

    cached = get_cached(cache_key) if not nocache else None
    if cached:
        logger.info(f"Reviews cache hit: {cache_key}")
        cached["_cached"] = True
        return cached

    # L2: Check DB before API call
    if not nocache:
        from app.services.product_data_service import get_cached_reviews
        db_reviews = await get_cached_reviews(cache_key)
        if db_reviews:
            set_cached(cache_key, db_reviews, REVIEWS_CACHE_TTL)
            db_reviews["_cached"] = True
            db_reviews["_cache_source"] = "db"
            return db_reviews

    review_terms = CATEGORY_REVIEW_TERMS.get(category, "user reviews pros cons rating")
    logger.info(f"Fetching reviews for: {brand} {name} (category: {category})")
    if search_results is None:
        search_results = await search_web(f"{search_query} {review_terms}")
        if track_serper_cost_fn:
            track_serper_cost_fn()

    search_context = format_review_search_results(
        search_results, retailer_ratings or []
    )

    reviews, usage = await extract_reviews(brand, name, variant, search_context, category=category)
    if track_gpt_cost_fn:
        track_gpt_cost_fn(usage)

    if retailer_ratings:
        reviews["source_ratings"] = retailer_ratings

    if reviews and not reviews.get("error"):
        set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
        # Save to L2 DB (fire-and-forget)
        from app.services.product_data_service import save_reviews
        asyncio.create_task(save_reviews(cache_key, brand, name, variant, reviews))

    reviews["_cached"] = False
    return reviews

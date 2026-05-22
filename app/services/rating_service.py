"""Rating Service — all rating-related functions extracted from structured_comparison_service.

Functions are standalone (no self) — pass shopping_items_cache dict where needed.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import Counter

import httpx

from app.services.price_service import (
    is_accessory,
    strict_title_match,
    numbers_match,
    normalize_words,
    has_retailer_url,
    build_retailer_url,
    RETAILER_SEARCH_URLS,
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

logger = logging.getLogger(__name__)

# Rating retailer tiers
RATING_TIER_1 = {
    "amazon", "apple", "samsung", "best buy", "bestbuy", "walmart",
    "target", "noon", "jarir", "extra", "newegg", "b&h", "bhphoto",
    "iherb", "sephora", "ulta",
}
RATING_TIER_2 = {
    "costco", "carrefour", "sharaf dg", "virgin megastore", "currys",
    "john lewis", "adorama", "micro center", "google store", "microsoft",
    "dell", "hp store", "lenovo", "fnac",
    "fragrantica", "sally beauty", "lookfantastic", "beautybay", "nykaa",
    "bath & body", "boots",
}
RATING_TIER_3 = {
    "ebay", "aliexpress", "alibaba", "temu", "wish",
}

# Luxury/fashion retailers for Tier 2 (used in extraction)
LUXURY_FASHION_RETAILERS = {
    "fragrantica", "sally beauty", "lookfantastic", "beautybay", "nykaa",
    "bath & body", "boots",
}


def get_rating_tier(source: str) -> int:
    """Classify a retailer into rating trust tiers. Returns 1, 2, or 3."""
    if not source:
        return 3
    source_lower = source.lower()
    for r in RATING_TIER_1:
        if r in source_lower:
            return 1
    for r in RATING_TIER_2:
        if r in source_lower:
            return 2
    if ".com" in source_lower or ".ae" in source_lower:
        return 2
    return 3


def collect_retailer_ratings(full_name: str, shopping_items_cache: Dict) -> List[Dict[str, Any]]:
    """Extract per-retailer rating data from shopping cache for review enrichment."""
    shopping_items = shopping_items_cache.get(full_name, [])
    ratings = []
    seen = set()

    for item in shopping_items:
        rating = item.get("rating")
        source = item.get("source", "")
        if not rating or not source:
            continue
        source_key = source.lower().strip()
        if source_key in seen:
            continue
        seen.add(source_key)

        review_count = None
        for key in ("ratingCount", "reviewCount", "reviews"):
            raw = item.get(key)
            if raw is not None:
                try:
                    review_count = int(str(raw).replace(",", "").replace("+", ""))
                    break
                except (ValueError, TypeError):
                    continue

        try:
            ratings.append({
                "source": source,
                "rating": round(float(rating), 1),
                "review_count": review_count,
            })
        except (ValueError, TypeError):
            continue

    return ratings


def extract_rating_from_shopping(
    product_name: str,
    shopping_items: List[Dict],
) -> Dict[str, Any]:
    """Extract best matching rating from Serper Shopping results.

    Tiered fallback: Tier 1 (trusted) -> Tier 2 (known) -> Tier 3 (marketplace, >1000 reviews).
    """
    empty = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

    if not shopping_items:
        return empty

    p_words = normalize_words(product_name)
    tier1_candidates = []
    tier2_candidates = []
    tier3_candidates = []

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
        source = item.get("source", "")

        if is_accessory(title):
            continue
        if not strict_title_match(product_name, title):
            continue
        if not numbers_match(product_name, title):
            continue

        t_words = normalize_words(title)
        match_score = len(p_words & t_words) / len(p_words) if p_words else 0
        if match_score < 0.4:
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

        candidate = {
            "rating": rating_val,
            "review_count": review_count,
            "source": source,
            "link": item.get("link"),
            "title": title,
            "match_score": match_score,
        }

        tier = get_rating_tier(source)
        if tier == 1:
            tier1_candidates.append(candidate)
        elif tier == 2:
            tier2_candidates.append(candidate)
        else:
            if review_count and review_count > 1000:
                tier3_candidates.append(candidate)

    # Check for Google aggregate consensus
    all_candidates = tier1_candidates + tier2_candidates + tier3_candidates
    if not tier1_candidates and not tier2_candidates and all_candidates:
        rating_counts = Counter(
            (c["rating"], c["review_count"]) for c in all_candidates if c["review_count"]
        )
        most_common, count = rating_counts.most_common(1)[0] if rating_counts else ((None, None), 0)
        if count >= 3:
            consensus = [c for c in all_candidates if (c["rating"], c["review_count"]) == most_common]
            consensus.sort(key=lambda c: (
                has_retailer_url(c["source"]),
                c["match_score"],
            ), reverse=True)
            best = consensus[0]
            logger.info(f"[RATING] CONSENSUS ({count} sellers): {best['rating']}/5 ({best['review_count']} reviews)")
            return {
                "rating": round(best["rating"], 1),
                "review_count": best["review_count"],
                "rating_verified": True,
                "rating_source": {
                    "name": "Google Shopping (product aggregate)",
                    "url": best.get("link") or build_retailer_url(best["source"], product_name),
                    "retrieved_at": datetime.now().isoformat() + "Z",
                    "extract_method": "google_shopping_consensus",
                    "confidence": "high"
                }
            }

    # Tiered fallback
    chosen_tier = None
    candidates = []
    if tier1_candidates:
        candidates = tier1_candidates
        chosen_tier = "tier1"
    elif tier2_candidates:
        candidates = tier2_candidates
        chosen_tier = "tier2"
    elif tier3_candidates:
        candidates = tier3_candidates
        chosen_tier = "tier3"

    if not candidates:
        return empty

    candidates.sort(key=lambda c: (c["review_count"] or 0, c["match_score"]), reverse=True)
    best = candidates[0]

    if chosen_tier == "tier3":
        confidence = "low"
        label = f"{best['source']} (marketplace rating)"
        verified = False
    else:
        confidence = "high" if chosen_tier == "tier1" else "medium"
        label = f"{best['source']} via Google Shopping"
        verified = True

    return {
        "rating": round(best["rating"], 1),
        "review_count": best["review_count"],
        "rating_verified": verified,
        "rating_source": {
            "name": label,
            "url": best.get("link") or build_retailer_url(best["source"], product_name),
            "retrieved_at": datetime.now().isoformat() + "Z",
            "extract_method": "google_shopping",
            "confidence": confidence
        }
    }


async def get_verified_rating(
    full_name: str,
    shopping_items_cache: Dict,
    track_serper_cost_fn=None,
) -> Dict[str, Any]:
    """Get verified rating with minimal cost.

    1. Reuse shopping data from price fetch (FREE)
    2. If no Tier 1/2 rating, ONE US shopping search (1 credit)
    """
    empty = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}

    shopping_items = shopping_items_cache.get(full_name, [])
    if shopping_items:
        logger.info(f"[RATING] Reusing {len(shopping_items)} shopping items from price fetch")
        result = extract_rating_from_shopping(full_name, shopping_items)
        if result and result.get("rating") and result.get("rating_source", {}).get("confidence") != "low":
            return result
        logger.info(f"[RATING] Bahrain data had no Tier 1/2 rating, trying US search")

    if not SERPER_API_KEY:
        return empty

    # M3 (audit 2026-05-22): apply the same operator-tail clean as
    # serper_service.search_product_prices (HOTFIX-2 / commit eb0f675).
    # Without this, vision-mode flows can pass `full_name = search_query`
    # with GPT-emitted tokens ("price", "best price", "Bahrain", etc.)
    # that produce zero Shopping hits — the same symptom that triggered
    # the price-path fix. Same cleaner, same fix class.
    from app.services.serper_service import _clean_shopping_query
    cleaned_query = _clean_shopping_query(full_name)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": cleaned_query, "gl": "us", "num": 10}
            )
            if track_serper_cost_fn:
                track_serper_cost_fn()

            if response.status_code != 200:
                return empty

            # Bundle C § 1c A.3.3-fix-1 — bump Redis credit meter on the
            # 7th Serper call site (US shopping fallback). track_serper_cost_fn
            # above only tracks per-request USD cost; this updates the
            # lifetime/monthly counter that admin/costs reads.
            from app.services.api_budget_service import record_usage
            record_usage("serper")

            us_items = response.json().get("shopping", [])
            if us_items:
                result = extract_rating_from_shopping(full_name, us_items)
                if result and result.get("rating"):
                    return result

    except Exception as e:
        logger.error(f"[RATING] US shopping search error: {e}")

    return empty

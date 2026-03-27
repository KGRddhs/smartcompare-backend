"""Response Builder — builds the full comparison response dict.

Extracted from duplicated response assembly code in compare_from_text()
and compare_from_text_streaming().
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.services.scoring_service import MISSING_SCORE


def derive_rating_from_scores(overall_score: float) -> float:
    """Derive a synthetic rating (1-5 scale) from overall score when no real rating exists."""
    rating = 2.5 + (overall_score / 100) * 2.3
    return round(min(rating, 4.8), 1)


def build_comparison_response(
    *,
    product_data: List[Dict[str, Any]],
    comparison: Dict[str, Any],
    scoring_result: Dict[str, Any],
    product_names: List[str],
    tradeoffs: List[Dict],
    confidence: Dict,
    verdict_validation: Dict,
    user_preferences: Optional[Dict[str, Any]],
    from_cache: bool,
    query: str,
    region: str,
    category_used: str,
    category_switched: bool,
    original_category: Optional[str],
    total_cost: float,
    api_calls: int,
    gpt_calls: int,
    serper_calls: int,
    elapsed_seconds: float,
) -> Dict[str, Any]:
    """Build the full structured comparison response.

    This is used by both compare_from_text() and compare_from_text_streaming()
    to avoid duplicating ~100 lines of response assembly.
    """
    winner_index = comparison.get("winner_index", 0)
    win_margin = scoring_result.get("win_margin", 0)

    # Build personalization metadata
    personalized = user_preferences is not None and bool(user_preferences)
    personalization_factors = []
    if personalized:
        for p in user_preferences.get("priorities", []):
            personalization_factors.append(f"priority_{p}")
        if user_preferences.get("budget"):
            personalization_factors.append(f"budget_{user_preferences['budget']}")
        for tag in user_preferences.get("lifestyle", []):
            personalization_factors.append(f"lifestyle_{tag}")

    # Derive ratings for products with no real ratings
    for i, pd_item in enumerate(product_data):
        if pd_item.get("rating") is None:
            key = f"product_{i}"
            overall = scoring_result.get("scores", {}).get(key, {}).get("overall", MISSING_SCORE)
            pd_item["rating"] = derive_rating_from_scores(overall)
            pd_item["rating_derived"] = True

    # Detect price method mismatch
    price_methods = [p.get("price", {}).get("source_method") for p in product_data if p.get("price")]
    unique_methods = set(m for m in price_methods if m)

    result = {
        "success": True,
        "query": query,
        "category": category_used,
        "category_switched": category_switched,
        "original_category": original_category,

        "overview": {
            "winner": {
                "product_index": winner_index,
                "name": comparison.get("winner_declaration", product_names[winner_index] if product_names else ""),
                "declaration": comparison.get("winner_declaration", ""),
                "reason": comparison.get("winner_reason", ""),
                "key_tradeoff": comparison.get("key_tradeoff", ""),
                "margin": win_margin,
            },
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "price": pd.get("price"),
                    "rating": pd.get("rating"),
                    "review_count": pd.get("review_count"),
                    "overall_score": scoring_result.get("scores", {}).get(f"product_{i}", {}).get("overall"),
                    "value_badge": pd.get("value_badge", "fair_price"),
                    "value_context": comparison.get("value_context", ""),
                    "pros": pd.get("pros_cons", {}).get("pros", []),
                    "cons": pd.get("pros_cons", {}).get("cons", []),
                    "best_for": comparison.get("best_for", {}).get(f"product_{i}", ""),
                }
                for i, pd in enumerate(product_data)
            ],
            "tradeoffs": tradeoffs,
            "confidence": confidence,
        },

        "specs": {
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "specs": pd.get("specs"),
                    "spec_advantages": comparison.get("specs_comparison", {}).get(f"product_{i}_advantages", []),
                }
                for i, pd in enumerate(product_data)
            ],
            "specs_comparison": comparison.get("specs_comparison", {}),
        },

        "reviews": {
            "products": [
                {
                    "brand": pd.get("brand"),
                    "name": pd.get("name"),
                    "rating": pd.get("rating"),
                    "review_count": pd.get("review_count"),
                    "rating_source": pd.get("rating_source"),
                    "review_summary": pd.get("reviews", {}).get("review_summary", {
                        "overall_sentiment": "mixed",
                        "consensus": "",
                        "highlights": [],
                        "review_volume": "minimal",
                        "agreement_level": "moderate",
                    }),
                }
                for pd in product_data
            ],
        },

        "scoring": {
            "scores": scoring_result.get("scores", {}),
            "dimension_winners": scoring_result.get("dimension_winners", {}),
            "price_tiers": scoring_result.get("price_tiers", {}),
            "is_cross_tier": scoring_result.get("is_cross_tier", False),
            "scoring_method": scoring_result.get("scoring_method", "category_weighted"),
            "category_weights": scoring_result.get("category_weights", {}),
        },

        "personalization": {
            "personalized": personalized,
            "factors": personalization_factors,
            "personalized_insights": comparison.get("personalized_insights", []),
        },

        "metadata": {
            "query": query,
            "region": region,
            "elapsed_ms": round(elapsed_seconds * 1000),
            "elapsed_seconds": round(elapsed_seconds, 2),
            "api_calls": api_calls,
            "total_cost": round(total_cost, 6),
            "gpt_calls": gpt_calls,
            "serper_calls": serper_calls,
            "cached": from_cache,
            "fact_check": {
                "product_0": product_data[0].get("fact_check", {}),
                "product_1": product_data[1].get("fact_check", {}),
            },
            "verdict_validation": verdict_validation,
            "timestamp": datetime.now().isoformat(),
        },
    }

    # Backward compatibility aliases
    result["products"] = product_data
    result["comparison"] = comparison
    result["recommendation"] = comparison.get("winner_reason", "")
    result["key_differences"] = []
    result["winner_index"] = winner_index
    result["category_used"] = category_used
    result["personalized"] = personalized
    result["personalization_factors"] = personalization_factors
    result["personalized_insights"] = comparison.get("personalized_insights", [])
    result["price_method_mismatch"] = len(unique_methods) > 1
    result["tier_context"] = {
        "price_tiers": scoring_result.get("price_tiers", {}),
        "is_cross_tier": scoring_result.get("is_cross_tier", False),
    }

    return result

"""Fact Check Service — all fact-checking functions extracted from structured_comparison_service.

Zero-cost cross-validation: spec citations, shopping cross-check, review sentiment, price deviation.
"""
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Fields where numeric values must match exactly during citation verification
NUMERIC_SPEC_FIELDS = {
    "ram", "storage", "battery", "weight", "display", "count", "dosage",
    "nutrition_calories", "nutrition_protein", "nutrition_fat", "nutrition_carbs",
}


def verify_spec_citations(specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
    """Verify GPT spec citations against actual search snippets.

    Returns dict mapping spec_field -> confidence:
      'verified': citation matches snippet text
      'likely': citation provided but can't fully cross-check
      'unverified': no citation or citation doesn't match
    """
    confidence = {}
    for key, value in specs.items():
        if key.endswith("_source") or key.startswith("_") or key in ("brand", "model", "variant", "category"):
            continue
        source_key = f"{key}_source"
        source = specs.get(source_key)

        if not source or source == "training":
            confidence[key] = "unverified"
        elif source.startswith("snippet_"):
            try:
                idx = int(source.split("_")[1]) - 1
                if 0 <= idx < len(search_snippets):
                    snippet_text = search_snippets[idx].lower()
                    value_str = str(value).lower()

                    spec_numbers = re.findall(r'\d+', value_str)

                    if key in NUMERIC_SPEC_FIELDS and spec_numbers:
                        sig_numbers = [n for n in spec_numbers if len(n) >= 2]
                        if sig_numbers:
                            matches = sum(1 for n in sig_numbers if n in snippet_text)
                            confidence[key] = "verified" if matches == len(sig_numbers) else "likely"
                        else:
                            terms = [t for t in value_str.split() if len(t) > 2]
                            if not terms:
                                confidence[key] = "likely"
                            else:
                                matches = sum(1 for t in terms if t in snippet_text)
                                confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                    else:
                        terms = [t for t in value_str.split() if len(t) > 2]
                        if not terms:
                            confidence[key] = "likely"
                        else:
                            matches = sum(1 for t in terms if t in snippet_text)
                            confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                else:
                    confidence[key] = "unverified"
            except (ValueError, IndexError):
                confidence[key] = "unverified"
        else:
            confidence[key] = "unverified"

    return confidence


def cross_validate_specs_with_shopping(specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
    """Cross-check spec values against Serper Shopping product titles/descriptions.

    Upgrades 'likely' to 'verified' if shopping data confirms.
    """
    if not shopping_items:
        return {}

    shopping_text = " ".join(
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in shopping_items
    ).lower()

    flags = {}
    checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
    for key in checkable:
        value = specs.get(key)
        if not value or value == "N/A":
            continue
        value_str = str(value).lower()
        spec_numbers = [n for n in re.findall(r'\d+', value_str) if len(n) >= 2]
        if spec_numbers:
            all_found = all(n in shopping_text for n in spec_numbers)
            if all_found:
                flags[key] = "verified"
        else:
            terms = [t for t in value_str.split() if len(t) > 2]
            found = sum(1 for t in terms if t in shopping_text)
            if terms and found >= len(terms) * 0.5:
                flags[key] = "verified"

    return flags


def verify_review_sentiment(reviews: Dict, source_ratings: List[Dict]) -> Dict:
    """Cross-check GPT review sentiment against real Serper ratings."""
    gpt_rating = reviews.get("average_rating")
    if not source_ratings or gpt_rating is None:
        return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

    total_weight = 0
    weighted_sum = 0
    for sr in source_ratings:
        rating = sr.get("rating")
        count = sr.get("review_count", 1) or 1
        if rating and isinstance(rating, (int, float)):
            weighted_sum += rating * count
            total_weight += count

    if total_weight == 0:
        return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

    serper_avg = round(weighted_sum / total_weight, 2)
    deviation = abs(gpt_rating - serper_avg)
    consistent = deviation <= 0.8

    return {
        "sentiment_consistent": consistent,
        "gpt_rating": gpt_rating,
        "serper_avg_rating": serper_avg,
        "deviation": round(deviation, 2),
    }


def verify_price(price: Dict, shopping_items: List[Dict]) -> Dict:
    """Cross-check final price against Serper Shopping prices."""
    if not price or not shopping_items:
        return {
            "price_verified": price is not None and not (price or {}).get("estimated", False),
            "deviation_pct": None,
            "source_count": 0,
        }

    final_amount = price.get("amount")
    if not final_amount:
        return {"price_verified": False, "deviation_pct": None, "source_count": 0}

    shopping_prices = []
    for item in shopping_items:
        p = item.get("price")
        if isinstance(p, (int, float)) and p > 0:
            shopping_prices.append(p)
        elif isinstance(p, str):
            nums = re.findall(r'[\d.]+', p.replace(',', ''))
            if nums:
                try:
                    shopping_prices.append(float(nums[0]))
                except ValueError:
                    pass

    if not shopping_prices:
        return {
            "price_verified": not price.get("estimated", False),
            "deviation_pct": None,
            "source_count": 0,
        }

    median = sorted(shopping_prices)[len(shopping_prices) // 2]
    deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None

    return {
        "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),
        "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
        "source_count": len(shopping_prices),
    }


def build_fact_check(product: Dict) -> Dict:
    """Assemble fact_check object from per-field verification results.

    Pops internal _spec_confidence, _review_verification, _price_verification
    keys from the product dict and returns a clean fact_check summary.
    """
    spec_confidence = product.pop("_spec_confidence", {})
    review_verification = product.pop("_review_verification", {})
    price_verification = product.pop("_price_verification", {})

    specs_verified = sum(1 for v in spec_confidence.values() if v == "verified")
    specs_likely = sum(1 for v in spec_confidence.values() if v == "likely")
    specs_flagged = sum(1 for v in spec_confidence.values() if v == "flagged")
    specs_unverified = sum(1 for v in spec_confidence.values() if v == "unverified")

    price_verified = price_verification.get("price_verified", False)
    sentiment_consistent = review_verification.get("sentiment_consistent")

    if specs_flagged > 0 or (sentiment_consistent is False):
        overall = "low"
    elif specs_unverified > specs_verified + specs_likely:
        overall = "medium"
    elif price_verified and (sentiment_consistent is True or sentiment_consistent is None):
        overall = "high"
    else:
        overall = "medium"

    return {
        "specs_verified": specs_verified,
        "specs_likely": specs_likely,
        "specs_flagged": specs_flagged,
        "specs_unverified": specs_unverified,
        "price_verified": price_verified,
        "price_deviation_pct": price_verification.get("deviation_pct"),
        "review_sentiment_consistent": sentiment_consistent,
        "review_rating_deviation": review_verification.get("deviation"),
        "overall_confidence": overall,
    }

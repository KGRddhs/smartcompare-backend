"""Pure-function confidence signal computation. No I/O.

Lane 2 (Backend Comparison Engine Overhaul) — confidence-driven escalation
replaces the legacy `is_luxury_brand()` gate so every category (electronics,
supplements, fragrances, makeup, skincare, haircare, fashion, grocery, other)
can fire Tier 1.5/2 page-scrape escalation when the Tier 1 Serper data is
weak. See `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md` Lane 2.

Three signal computers:
- compute_price_confidence: agreement across sources + training-estimate sanity
- compute_specs_confidence: ratio of schema fields with non-empty values
- compute_reviews_confidence: combined review-count + source-count check

`should_escalate` is the binary gate used by `_should_escalate_price_scrape`
in `structured_comparison_service.py` to decide whether to enter the Tier 1.5
cascade for the current product.
"""

from typing import Any, Dict, List, Optional


def compute_price_confidence(
    sources: List[Dict[str, Any]],
    training_estimate: Optional[float] = None,
) -> Dict[str, Any]:
    """Decide price confidence level from a list of candidate price sources.

    `sources` items expected shape::

        {"src": "serper_shopping", "amount": 142.12, "retailer_score": 0.9}

    Returns ``{"level": "high"|"medium"|"low", "reasons": [str], "median": float|None,
    "sources_count": int}``.
    """
    if not sources:
        return {"level": "low", "reasons": ["no_sources"], "median": None}

    amounts = [s["amount"] for s in sources if s.get("amount") is not None]
    if not amounts:
        return {"level": "low", "reasons": ["no_amounts"], "median": None}

    sorted_amounts = sorted(amounts)
    median = sorted_amounts[len(sorted_amounts) // 2]
    reasons: List[str] = []

    if len(amounts) >= 2:
        within_20pct = sum(1 for a in amounts if 0.8 * median <= a <= 1.2 * median)
        if within_20pct >= 2:
            agreement = "multi_source_agreement"
        else:
            agreement = "multi_source_disagreement"
            reasons.append("sources_disagree")
    else:
        agreement = "single_source"
        reasons.append("only_one_source")

    if training_estimate and training_estimate > 0:
        deviation = abs(median - training_estimate) / training_estimate
        if deviation > 0.40:
            reasons.append("deviation_from_training_estimate")

    top_retailer_score = max(
        (s.get("retailer_score", 0) for s in sources), default=0
    )
    if top_retailer_score < 0.7:
        reasons.append("low_retailer_score")

    if not reasons and agreement == "multi_source_agreement":
        level = "high"
    elif "deviation_from_training_estimate" in reasons or len(reasons) >= 2:
        level = "low"
    else:
        level = "medium"

    return {
        "level": level,
        "reasons": reasons,
        "median": median,
        "sources_count": len(sources),
    }


def compute_specs_confidence(
    populated: Dict[str, Any], schema_fields: List[str]
) -> Dict[str, Any]:
    """Confidence from the ratio of schema fields with non-empty values.

    Empty strings and ``None`` count as missing — only truthy field values
    increment the populated counter.
    """
    if not schema_fields:
        return {"level": "low", "reasons": ["no_schema"]}

    count_populated = sum(1 for f in schema_fields if populated.get(f))
    ratio = count_populated / len(schema_fields)

    if ratio >= 0.8:
        level = "high"
    elif ratio >= 0.5:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "ratio": ratio,
        "populated_count": count_populated,
        "schema_size": len(schema_fields),
    }


def compute_reviews_confidence(
    review_count_p0: int, review_count_p1: int, sources_count: int = 1
) -> Dict[str, Any]:
    """Combined review-count + source-count confidence.

    "high" requires BOTH ``min_count > 100`` AND ``sources_count >= 2``. Single
    Serper-only review fetch with a fat review_count still grades medium.
    """
    min_count = min(review_count_p0, review_count_p1)
    if min_count > 100 and sources_count >= 2:
        level = "high"
    elif min_count > 20:
        level = "medium"
    else:
        level = "low"
    return {"level": level, "min_count": min_count, "sources_count": sources_count}


def should_escalate(confidence_obj: Dict[str, Any]) -> bool:
    """Return True iff escalation to the next tier is warranted (level=='low')."""
    return confidence_obj.get("level") == "low"

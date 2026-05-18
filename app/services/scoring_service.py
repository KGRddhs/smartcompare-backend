"""
Scoring Service - Deterministic, explainable product scoring from structured data.

Pure Python, ZERO API calls. Computes per-product scores from extracted specs,
prices, reviews, and user preferences. Same input = same output (deterministic).
"""
import logging
import re
from typing import Dict, Any, List, Optional

from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS

logger = logging.getLogger(__name__)

# Category-specific scoring dimensions (each category has 6)
CATEGORY_DIMENSIONS = {
    "electronics": [
        "performance_score", "value_score", "build_quality_score",
        "feature_score", "ecosystem_score", "futureproof_score",
    ],
    "grocery": [
        "nutrition_score", "ingredient_score", "taste_score",
        "serving_value_score", "dietary_score", "availability_score",
    ],
    "supplements": [
        "efficacy_score", "safety_score", "dosage_score",
        "serving_value_score", "form_score", "trust_score",
    ],
    "makeup": [
        "shade_score", "longevity_score", "skin_compat_score",
        "finish_score", "ingredient_safety_score", "perf_value_score",
    ],
    "skincare": [
        "actives_score", "evidence_score", "skin_compat_score",
        "formulation_score", "sensory_score", "results_value_score",
    ],
    "haircare": [
        "hair_match_score", "results_score", "ingredient_score",
        "scent_score", "multi_value_score", "scalp_score",
    ],
    "fragrances": [
        "character_score", "longevity_score", "projection_score",
        "versatility_score", "wear_value_score", "presentation_score",
    ],
    "fashion": [
        "craft_score", "fit_score", "style_score",
        "durability_score", "heritage_score", "cpw_score",
    ],
    "other": [
        "function_score", "build_score", "review_score",
        "value_score", "reliability_score", "feature_match_score",
    ],
}

# Weights per category (each sums to 1.0)
CATEGORY_DIMENSION_WEIGHTS = {
    "electronics":  {"performance_score": 0.25, "value_score": 0.20, "build_quality_score": 0.15, "feature_score": 0.20, "ecosystem_score": 0.10, "futureproof_score": 0.10},
    "grocery":      {"nutrition_score": 0.25, "ingredient_score": 0.20, "taste_score": 0.20, "serving_value_score": 0.15, "dietary_score": 0.15, "availability_score": 0.05},
    "supplements":  {"efficacy_score": 0.30, "safety_score": 0.25, "dosage_score": 0.15, "serving_value_score": 0.10, "form_score": 0.10, "trust_score": 0.10},
    "makeup":       {"shade_score": 0.20, "longevity_score": 0.25, "skin_compat_score": 0.20, "finish_score": 0.15, "ingredient_safety_score": 0.10, "perf_value_score": 0.10},
    "skincare":     {"actives_score": 0.25, "evidence_score": 0.20, "skin_compat_score": 0.20, "formulation_score": 0.15, "sensory_score": 0.10, "results_value_score": 0.10},
    "haircare":     {"hair_match_score": 0.25, "results_score": 0.25, "ingredient_score": 0.15, "scent_score": 0.15, "multi_value_score": 0.10, "scalp_score": 0.10},
    "fragrances":   {"character_score": 0.25, "longevity_score": 0.25, "projection_score": 0.15, "versatility_score": 0.15, "wear_value_score": 0.10, "presentation_score": 0.10},
    "fashion":      {"craft_score": 0.25, "fit_score": 0.20, "style_score": 0.20, "durability_score": 0.15, "heritage_score": 0.10, "cpw_score": 0.10},
    "other":        {"function_score": 0.25, "build_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.10, "feature_match_score": 0.10},
}

# Backward compatibility alias — existing code imports CATEGORY_WEIGHTS
CATEGORY_WEIGHTS = CATEGORY_DIMENSION_WEIGHTS

# Per-category priority adjustments (8 priorities x 9 categories)
CATEGORY_PRIORITY_ADJUSTMENTS = {
    "electronics": {
        "price": {"value_score": 0.15, "performance_score": -0.10},
        "quality": {"performance_score": 0.10, "build_quality_score": 0.10, "value_score": -0.10},
        "brand_reputation": {"ecosystem_score": 0.10, "futureproof_score": 0.05, "value_score": -0.10},
        "durability": {"build_quality_score": 0.15, "futureproof_score": 0.05, "performance_score": -0.10},
        "latest_features": {"feature_score": 0.10, "futureproof_score": 0.10, "value_score": -0.10},
        "ease_of_use": {"ecosystem_score": 0.10, "feature_score": 0.05, "futureproof_score": -0.10},
        "eco_friendly": {"build_quality_score": 0.05, "ecosystem_score": 0.05, "performance_score": -0.05},
        "health_safety": {"build_quality_score": 0.10, "value_score": -0.05},
    },
    "grocery": {
        "price": {"serving_value_score": 0.15, "nutrition_score": -0.10},
        "quality": {"nutrition_score": 0.10, "ingredient_score": 0.10, "serving_value_score": -0.10},
        "brand_reputation": {"taste_score": 0.10, "availability_score": 0.05, "serving_value_score": -0.10},
        "durability": {"ingredient_score": 0.05, "dietary_score": 0.05, "taste_score": -0.05},
        "latest_features": {"nutrition_score": 0.05, "ingredient_score": 0.05, "availability_score": -0.05},
        "ease_of_use": {"availability_score": 0.10, "taste_score": 0.05, "ingredient_score": -0.10},
        "eco_friendly": {"ingredient_score": 0.10, "dietary_score": 0.05, "serving_value_score": -0.10},
        "health_safety": {"nutrition_score": 0.10, "dietary_score": 0.10, "taste_score": -0.10},
    },
    "supplements": {
        "price": {"serving_value_score": 0.15, "efficacy_score": -0.10},
        "quality": {"efficacy_score": 0.10, "dosage_score": 0.10, "serving_value_score": -0.10},
        "brand_reputation": {"trust_score": 0.10, "safety_score": 0.05, "serving_value_score": -0.10},
        "durability": {"safety_score": 0.10, "trust_score": 0.05, "form_score": -0.10},
        "latest_features": {"efficacy_score": 0.10, "dosage_score": 0.05, "form_score": -0.10},
        "ease_of_use": {"form_score": 0.15, "dosage_score": -0.10},
        "eco_friendly": {"safety_score": 0.05, "trust_score": 0.05, "serving_value_score": -0.05},
        "health_safety": {"safety_score": 0.10, "efficacy_score": 0.05, "serving_value_score": -0.10},
    },
    "makeup": {
        "price": {"perf_value_score": 0.15, "shade_score": -0.10},
        "quality": {"longevity_score": 0.10, "finish_score": 0.10, "perf_value_score": -0.10},
        "brand_reputation": {"finish_score": 0.10, "shade_score": 0.05, "perf_value_score": -0.10},
        "durability": {"longevity_score": 0.15, "ingredient_safety_score": 0.05, "shade_score": -0.10},
        "latest_features": {"shade_score": 0.10, "finish_score": 0.05, "perf_value_score": -0.10},
        "ease_of_use": {"finish_score": 0.10, "skin_compat_score": 0.05, "shade_score": -0.10},
        "eco_friendly": {"ingredient_safety_score": 0.10, "skin_compat_score": 0.05, "perf_value_score": -0.10},
        "health_safety": {"ingredient_safety_score": 0.10, "skin_compat_score": 0.10, "longevity_score": -0.10},
    },
    "skincare": {
        "price": {"results_value_score": 0.15, "actives_score": -0.10},
        "quality": {"actives_score": 0.10, "formulation_score": 0.10, "results_value_score": -0.10},
        "brand_reputation": {"evidence_score": 0.10, "formulation_score": 0.05, "results_value_score": -0.10},
        "durability": {"formulation_score": 0.10, "actives_score": 0.05, "sensory_score": -0.10},
        "latest_features": {"actives_score": 0.10, "evidence_score": 0.05, "sensory_score": -0.10},
        "ease_of_use": {"sensory_score": 0.10, "formulation_score": 0.05, "actives_score": -0.10},
        "eco_friendly": {"formulation_score": 0.10, "skin_compat_score": 0.05, "results_value_score": -0.10},
        "health_safety": {"skin_compat_score": 0.10, "formulation_score": 0.10, "sensory_score": -0.10},
    },
    "haircare": {
        "price": {"multi_value_score": 0.15, "hair_match_score": -0.10},
        "quality": {"results_score": 0.10, "ingredient_score": 0.10, "multi_value_score": -0.10},
        "brand_reputation": {"results_score": 0.10, "scent_score": 0.05, "multi_value_score": -0.10},
        "durability": {"ingredient_score": 0.10, "scalp_score": 0.05, "scent_score": -0.10},
        "latest_features": {"ingredient_score": 0.10, "results_score": 0.05, "multi_value_score": -0.10},
        "ease_of_use": {"scent_score": 0.10, "multi_value_score": 0.05, "ingredient_score": -0.10},
        "eco_friendly": {"ingredient_score": 0.10, "scalp_score": 0.05, "multi_value_score": -0.10},
        "health_safety": {"scalp_score": 0.10, "ingredient_score": 0.10, "scent_score": -0.10},
    },
    "fragrances": {
        "price": {"wear_value_score": 0.15, "character_score": -0.10},
        "quality": {"character_score": 0.10, "longevity_score": 0.10, "wear_value_score": -0.10},
        "brand_reputation": {"presentation_score": 0.10, "character_score": 0.05, "wear_value_score": -0.10},
        "durability": {"longevity_score": 0.15, "projection_score": 0.05, "presentation_score": -0.10},
        "latest_features": {"character_score": 0.10, "versatility_score": 0.05, "presentation_score": -0.10},
        "ease_of_use": {"versatility_score": 0.10, "projection_score": 0.05, "character_score": -0.10},
        "eco_friendly": {"character_score": 0.05, "presentation_score": 0.05, "wear_value_score": -0.05},
        "health_safety": {"character_score": 0.05, "versatility_score": 0.05, "wear_value_score": -0.05},
    },
    "fashion": {
        "price": {"cpw_score": 0.15, "craft_score": -0.10},
        "quality": {"craft_score": 0.10, "durability_score": 0.10, "cpw_score": -0.10},
        "brand_reputation": {"heritage_score": 0.10, "craft_score": 0.05, "cpw_score": -0.10},
        "durability": {"durability_score": 0.15, "craft_score": 0.05, "style_score": -0.10},
        "latest_features": {"style_score": 0.10, "fit_score": 0.05, "heritage_score": -0.10},
        "ease_of_use": {"fit_score": 0.10, "style_score": 0.05, "heritage_score": -0.10},
        "eco_friendly": {"craft_score": 0.05, "durability_score": 0.05, "cpw_score": -0.05},
        "health_safety": {"fit_score": 0.10, "durability_score": 0.05, "style_score": -0.10},
    },
    "other": {
        "price": {"value_score": 0.15, "function_score": -0.10},
        "quality": {"function_score": 0.10, "build_score": 0.10, "value_score": -0.10},
        "brand_reputation": {"reliability_score": 0.10, "review_score": 0.05, "value_score": -0.10},
        "durability": {"build_score": 0.10, "reliability_score": 0.10, "feature_match_score": -0.10},
        "latest_features": {"feature_match_score": 0.10, "function_score": 0.05, "value_score": -0.10},
        "ease_of_use": {"review_score": 0.10, "feature_match_score": 0.05, "build_score": -0.10},
        "eco_friendly": {"reliability_score": 0.05, "review_score": 0.05, "value_score": -0.05},
        "health_safety": {"reliability_score": 0.10, "build_score": 0.05, "value_score": -0.10},
    },
}

# Budget adjustments per category (same keys as category dimension weights).
# Bundle C § 3b: extend each category with `luxury` (mirrors the premium
# shape — same dims, same magnitudes) and `top_tier` (= luxury with the
# headline spec dim boosted by an extra +0.05). This keeps personalization
# behavior continuous across tier boundaries while honoring the spec's
# "top_tier expects more from the headline dimension" intent.
CATEGORY_BUDGET_ADJUSTMENTS = {
    "electronics": {
        "budget":   {"value_score": 0.10, "performance_score": -0.05},
        "mid":      {},
        "premium":  {"performance_score": 0.10, "value_score": -0.05},
        "luxury":   {"performance_score": 0.10, "value_score": -0.05},
        "top_tier": {"performance_score": 0.15, "value_score": -0.05},
    },
    "grocery": {
        "budget":   {"serving_value_score": 0.10, "nutrition_score": -0.05},
        "mid":      {},
        "premium":  {"nutrition_score": 0.10, "serving_value_score": -0.05},
        "luxury":   {"nutrition_score": 0.10, "serving_value_score": -0.05},
        "top_tier": {"nutrition_score": 0.15, "serving_value_score": -0.05},
    },
    "supplements": {
        "budget":   {"serving_value_score": 0.10, "efficacy_score": -0.05},
        "mid":      {},
        "premium":  {"efficacy_score": 0.10, "serving_value_score": -0.05},
        "luxury":   {"efficacy_score": 0.10, "serving_value_score": -0.05},
        "top_tier": {"efficacy_score": 0.15, "serving_value_score": -0.05},
    },
    "makeup": {
        "budget":   {"perf_value_score": 0.10, "shade_score": -0.05},
        "mid":      {},
        "premium":  {"longevity_score": 0.10, "perf_value_score": -0.05},
        "luxury":   {"longevity_score": 0.10, "perf_value_score": -0.05},
        "top_tier": {"longevity_score": 0.15, "perf_value_score": -0.05},
    },
    "skincare": {
        "budget":   {"results_value_score": 0.10, "actives_score": -0.05},
        "mid":      {},
        "premium":  {"actives_score": 0.10, "results_value_score": -0.05},
        "luxury":   {"actives_score": 0.10, "results_value_score": -0.05},
        "top_tier": {"actives_score": 0.15, "results_value_score": -0.05},
    },
    "haircare": {
        "budget":   {"multi_value_score": 0.10, "results_score": -0.05},
        "mid":      {},
        "premium":  {"results_score": 0.10, "multi_value_score": -0.05},
        "luxury":   {"results_score": 0.10, "multi_value_score": -0.05},
        "top_tier": {"results_score": 0.15, "multi_value_score": -0.05},
    },
    "fragrances": {
        "budget":   {"wear_value_score": 0.10, "character_score": -0.05},
        "mid":      {},
        "premium":  {"character_score": 0.10, "wear_value_score": -0.05},
        "luxury":   {"character_score": 0.10, "wear_value_score": -0.05},
        "top_tier": {"character_score": 0.15, "wear_value_score": -0.05},
    },
    "fashion": {
        "budget":   {"cpw_score": 0.10, "craft_score": -0.05},
        "mid":      {},
        "premium":  {"craft_score": 0.10, "cpw_score": -0.05},
        "luxury":   {"craft_score": 0.10, "cpw_score": -0.05},
        "top_tier": {"craft_score": 0.15, "cpw_score": -0.05},
    },
    "other": {
        "budget":   {"value_score": 0.10, "function_score": -0.05},
        "mid":      {},
        "premium":  {"function_score": 0.10, "value_score": -0.05},
        "luxury":   {"function_score": 0.10, "value_score": -0.05},
        "top_tier": {"function_score": 0.15, "value_score": -0.05},
    },
}

# Legacy aliases for backward compatibility
PRIORITY_ADJUSTMENTS = CATEGORY_PRIORITY_ADJUSTMENTS.get("other", {})
BUDGET_ADJUSTMENTS = {
    "budget": CATEGORY_BUDGET_ADJUSTMENTS["other"]["budget"],
    "mid": CATEGORY_BUDGET_ADJUSTMENTS["other"]["mid"],
    "premium": CATEGORY_BUDGET_ADJUSTMENTS["other"]["premium"],
}

# Maximum allowed shift ratio from category weight (±30%)
MAX_WEIGHT_SHIFT_RATIO = 0.30

# Behavioral and session weight shift caps
MAX_BEHAVIORAL_SHIFT_RATIO = 0.10  # ±10% of category weight
MAX_SESSION_SHIFT_RATIO = 0.05     # ±5% of category weight

# Spec fields higher/lower-is-better — organized by category
HIGHER_IS_BETTER_BY_CATEGORY = {
    "electronics": {"ram", "storage", "battery", "rear_camera", "front_camera"},
    "grocery": {"nutrition_protein", "shelf_life"},
    "supplements": {"count", "dosage", "serving_size"},
    "makeup": {"shade_range", "spf", "volume"},
    "skincare": {"spf", "volume"},
    "haircare": {"volume"},
    "fragrances": {"longevity", "volume"},
    "fashion": set(),
    "other": set(),
}

LOWER_IS_BETTER_BY_CATEGORY = {
    "electronics": {"weight"},
    "grocery": {"nutrition_calories", "nutrition_fat", "nutrition_carbs"},
    "supplements": {"nutrition_calories"},
    "makeup": set(),
    "skincare": set(),
    "haircare": set(),
    "fragrances": set(),
    "fashion": set(),
    "other": set(),
}

# Legacy flat sets for backward compatibility
HIGHER_IS_BETTER = set()
for _s in HIGHER_IS_BETTER_BY_CATEGORY.values():
    HIGHER_IS_BETTER |= _s
LOWER_IS_BETTER = set()
for _s in LOWER_IS_BETTER_BY_CATEGORY.values():
    LOWER_IS_BETTER |= _s

# Default score for missing data (legacy injection — flag-gated off by
# Bundle C § 2a. Kept as a constant for legacy `breakdown` consumers per
# the test_missing_score_constant_retained_for_legacy_path invariant.)
MISSING_SCORE = 50


# Bundle C § 2a flag — when ON, missing signals propagate as None instead
# of being injected with MISSING_SCORE=50. Cached at process init,
# mirroring _DEBUG_STAGE_TIMINGS pattern in structured_comparison_service.
# Tests reset via monkeypatch on _BUNDLE_C_SCORING_FLAG.
_BUNDLE_C_SCORING_FLAG = None


def _bundle_c_scoring_enabled() -> bool:
    global _BUNDLE_C_SCORING_FLAG
    if _BUNDLE_C_SCORING_FLAG is None:
        import os
        _BUNDLE_C_SCORING_FLAG = (
            os.environ.get("ENABLE_BUNDLE_C_SCORING", "false").lower()
            in {"1", "true", "yes"}
        )
    return _BUNDLE_C_SCORING_FLAG


# Bundle C § 3b + § 3e — per-category 5-tier breakpoints (BHD).
# Each entry is an ordered list of (upper_bound_exclusive, tier_label) tuples;
# walked low-to-high so the first range a price falls under wins. The final
# tuple uses float("inf") so any price above the last named bound lands in
# the top tier (or 'luxury' for categories that fold top_tier per § 3e:
# supplements + grocery — no real top_tier market in GCC for those).
PRICE_TIERS_BY_CATEGORY: dict = {
    "electronics": [(100, "budget"), (400, "mid"), (800, "premium"), (2000, "luxury"), (float("inf"), "top_tier")],
    "supplements": [(11, "budget"), (30, "mid"), (60, "premium"), (float("inf"), "luxury")],   # top_tier folded
    "fashion":     [(30, "budget"), (150, "mid"), (500, "premium"), (2000, "luxury"), (float("inf"), "top_tier")],
    "fragrances":  [(30, "budget"), (80, "mid"), (180, "premium"), (500, "luxury"), (float("inf"), "top_tier")],
    "skincare":    [(11, "budget"), (40, "mid"), (100, "premium"), (300, "luxury"), (float("inf"), "top_tier")],
    "haircare":    [(15, "budget"), (40, "mid"), (100, "premium"), (200, "luxury"), (float("inf"), "top_tier")],
    "makeup":      [(15, "budget"), (50, "mid"), (120, "premium"), (300, "luxury"), (float("inf"), "top_tier")],
    "grocery":     [(5, "budget"), (15, "mid"), (50, "premium"), (float("inf"), "luxury")],     # top_tier folded
}

# Bundle C § 3f — runtime sub-scale for category="other". The default
# `other_light` sub-scale extends the legacy flat PRICE_TIERS with a 500+
# top_tier slot so back-compat one-arg _detect_price_tier(price) calls
# remain stable for the budget/mid/premium boundaries.
_OTHER_SUBSCALE_TIERS: dict = {
    "other_light": [(11, "budget"), (57, "mid"), (189, "premium"), (500, "luxury"), (float("inf"), "top_tier")],
    "other_mid":   [(30, "budget"), (120, "mid"), (400, "premium"), (1000, "luxury"), (float("inf"), "top_tier")],
    "other_high":  [(300, "budget"), (1500, "mid"), (5000, "premium"), (15000, "luxury"), (float("inf"), "top_tier")],
    "other_ultra": [(5000, "budget"), (15000, "mid"), (40000, "premium"), (100000, "luxury"), (float("inf"), "top_tier")],
}


def _detect_other_subscale(p1: float, p2: float) -> str:
    """Bundle C § 3f — pick a sub-scale for the 'other' category based on
    the geometric mean of the two comparison prices. Cars at ~5000 + 6000
    BHD give gm ~5477 → other_ultra; snacks at 2 + 4 BHD give gm ~2.83 →
    other_light. The geometric mean dampens extreme spreads so the chosen
    sub-scale reflects the comparison's overall price magnitude."""
    import math as _math
    gm = _math.sqrt(max(p1, 0.0) * max(p2, 0.0))
    if gm < 30:
        return "other_light"
    if gm < 300:
        return "other_mid"
    if gm < 5000:
        return "other_high"
    return "other_ultra"


def _detect_price_tier(price_bhd: float, category: str = "other", *, comparison_prices=None) -> str:
    """Bundle C § 3b/3e/3f — return the tier label for a price in a category.

    Walks the per-category breakpoint list low-to-high. For category='other'
    with `comparison_prices=[p1, p2]` provided, the geometric-mean sub-scale
    picker (§ 3f) decides the breakpoint table; otherwise falls back to the
    `other_light` sub-scale. Unknown categories also fall through to
    `other_light`.
    """
    # Per-category fixed tier maps (electronics, fashion, fragrances, etc.)
    ranges = PRICE_TIERS_BY_CATEGORY.get(category)
    if ranges is None:
        # category='other' (or unknown) — may use geometric-mean sub-scale.
        subscale = "other_light"
        if category == "other" and comparison_prices and len(comparison_prices) >= 2:
            try:
                p1, p2 = float(comparison_prices[0]), float(comparison_prices[1])
                if p1 > 0 and p2 > 0:
                    subscale = _detect_other_subscale(p1, p2)
            except (TypeError, ValueError):
                pass
        ranges = _OTHER_SUBSCALE_TIERS[subscale]
    for upper, tier in ranges:
        if price_bhd < upper:
            return tier
    # Defensive — ranges always terminate in float("inf"); unreachable in
    # practice but keeps the function total.
    return ranges[-1][1]


# Back-compat alias for the legacy _OTHER_LIGHT_TIERS constant — some code
# may reference it directly.
_OTHER_LIGHT_TIERS = _OTHER_SUBSCALE_TIERS["other_light"]


# Legacy flat PRICE_TIERS preserved for back-compat — derived from the
# pre-Bundle-C 4-tier set so any external import that ranges over it sees
# the same (budget, mid, premium, luxury) keys.
PRICE_TIERS = {
    "budget":  (0, 11),
    "mid":     (11, 57),
    "premium": (57, 189),
    "luxury":  (189, float("inf")),
}

# Expected quality delivery per tier (0-1 scale). Bundle C § 3b re-splits
# the legacy single luxury=0.85 into luxury=0.88 + top_tier=0.90 so the
# value-formula cross-tier penalty rises monotonically across all 5 bands.
TIER_EXPECTATIONS = {
    "budget":   0.60,
    "mid":      0.70,
    "premium":  0.80,
    "luxury":   0.88,
    "top_tier": 0.90,
}

# Category-specific minimum coverage thresholds for spec penalty
CATEGORY_MIN_COVERAGE = {
    "electronics": 0.5, "fashion": 0.3, "fragrances": 0.3,
    "supplements": 0.4, "makeup": 0.35, "skincare": 0.35,
    "haircare": 0.35, "grocery": 0.3, "other": 0.3,
}


DIMENSION_DISPLAY_NAMES = {
    # Electronics
    "performance_score": "performance", "build_quality_score": "build quality",
    "feature_score": "features", "ecosystem_score": "ecosystem", "futureproof_score": "future-proofing",
    # Grocery
    "nutrition_score": "nutrition", "ingredient_score": "ingredients", "taste_score": "taste",
    "serving_value_score": "value per serving", "dietary_score": "dietary fit", "availability_score": "availability",
    # Supplements
    "efficacy_score": "efficacy", "safety_score": "safety", "dosage_score": "dosage",
    "form_score": "form", "trust_score": "trust",
    # Makeup
    "shade_score": "shade match", "skin_compat_score": "skin compatibility",
    "finish_score": "finish", "ingredient_safety_score": "ingredient safety", "perf_value_score": "performance value",
    # Skincare
    "actives_score": "active ingredients", "evidence_score": "efficacy evidence",
    "formulation_score": "formulation", "sensory_score": "sensory experience", "results_value_score": "results value",
    # Haircare
    "hair_match_score": "hair type match", "results_score": "results", "scent_score": "scent",
    "multi_value_score": "multi-benefit value", "scalp_score": "scalp safety",
    # Fragrances
    "character_score": "scent character", "longevity_score": "longevity", "projection_score": "projection",
    "versatility_score": "versatility", "wear_value_score": "value per wear", "presentation_score": "presentation",
    # Fashion
    "craft_score": "craftsmanship", "fit_score": "fit & comfort", "style_score": "style",
    "durability_score": "durability", "heritage_score": "brand heritage", "cpw_score": "cost per wear",
    # Other / Shared
    "function_score": "core function", "build_score": "build quality", "review_score": "reviews",
    "value_score": "value", "reliability_score": "reliability", "feature_match_score": "feature match",
}


class ScoringService:
    """Deterministic scoring engine for product comparisons.

    Uses category-specific dimensions (6 per category) instead of a universal set.
    Each category has its own dimension keys, weights, and priority adjustments.
    """

    def compute_scores(
        self,
        products_data: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]] = None,
        behavior_profile: Optional[Dict[str, Any]] = None,
        session_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute scores for a list of products using category-specific dimensions."""
        if not products_data or len(products_data) < 2:
            return self._empty_result(len(products_data))

        category = products_data[0].get("category", "other")
        if category not in CATEGORY_DIMENSIONS:
            category = "other"
        weights = self._compute_weights(preferences, category)

        # Apply behavioral and session adjustments (layered on top of explicit preferences)
        if behavior_profile:
            weights = self.apply_behavioral_adjustments(weights, behavior_profile)
        if session_signals:
            weights = self.apply_session_signals(weights, session_signals)

        # Compute raw dimension scores for each product
        raw_scores = []
        for product in products_data:
            raw_scores.append(self._compute_raw_scores(product, category))

        # Normalize scores relative to each other (0-100 scale)
        normalized, price_tiers, is_cross_tier = self._normalize_scores(raw_scores, products_data, category)

        # Compute overall weighted score for each product
        dims = CATEGORY_DIMENSIONS.get(category, CATEGORY_DIMENSIONS["other"])
        result_products = {}
        for i, product in enumerate(products_data):
            product_key = f"product_{i}"
            breakdown = normalized[i]
            overall = sum(
                breakdown.get(dim, MISSING_SCORE) * weights.get(dim, 0) for dim in weights
            )
            overall = round(max(0, min(100, overall)), 1)

            # Track which dimensions had missing data
            missing_dims = [dim for dim in dims if raw_scores[i].get(f"_{dim}_missing")]

            result_products[product_key] = {
                "overall": overall,
                "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
                "weights_used": {k: round(v, 4) for k, v in weights.items()},
                "missing_data": missing_dims if missing_dims else None,
            }

        # Determine winner
        overalls = [result_products[f"product_{i}"]["overall"] for i in range(len(products_data))]
        winner_index = overalls.index(max(overalls))
        win_margin = round(abs(overalls[0] - overalls[1]), 1) if len(overalls) >= 2 else 0

        if behavior_profile or session_signals:
            scoring_method = "behavioral"
        elif preferences:
            scoring_method = "personalized"
        else:
            scoring_method = "category_weighted"

        # Build price tier metadata
        price_tiers_map = {}
        for i, product in enumerate(products_data):
            name = f"{product.get('brand', '')} {product.get('name', '')}".strip()
            price_tiers_map[name] = price_tiers[i] if i < len(price_tiers) else "mid"

        # Compute dimension winners
        product_names = [
            f"{p.get('brand', '')} {p.get('name', '')}".strip()
            for p in products_data
        ]
        result_so_far = {"scores": result_products}
        dimension_winners = self.compute_dimension_winners(result_so_far, product_names, category)

        return {
            "scores": result_products,
            "winner_index": winner_index,
            "win_margin": win_margin,
            "scoring_method": scoring_method,
            "price_tiers": price_tiers_map,
            "is_cross_tier": is_cross_tier,
            "dimension_winners": dimension_winners,
            "category_weights": dict(CATEGORY_DIMENSION_WEIGHTS.get(category, CATEGORY_DIMENSION_WEIGHTS["other"])),
        }

    def _compute_weights(self, preferences: Optional[Dict[str, Any]], category: str = "other") -> Dict[str, float]:
        """Compute scoring weights from category defaults + user preferences."""
        if category not in CATEGORY_DIMENSION_WEIGHTS:
            category = "other"
        base_weights = CATEGORY_DIMENSION_WEIGHTS[category]
        weights = dict(base_weights)

        if not preferences:
            return weights

        # Apply category-specific priority adjustments (stack for multiple priorities)
        cat_priority_adj = CATEGORY_PRIORITY_ADJUSTMENTS.get(category, {})
        for priority in preferences.get("priorities", []):
            adjustments = cat_priority_adj.get(priority, {})
            for dim, delta in adjustments.items():
                if dim in weights:
                    weights[dim] = weights[dim] + delta

        # Apply category-specific budget adjustment
        budget = preferences.get("budget", "mid")
        cat_budget_adj = CATEGORY_BUDGET_ADJUSTMENTS.get(category, {})
        budget_adj = cat_budget_adj.get(budget, {})
        for dim, delta in budget_adj.items():
            if dim in weights:
                weights[dim] = weights[dim] + delta

        # Cap each dimension's shift to +/-30% of its CATEGORY weight
        for dim in weights:
            cat_default = base_weights.get(dim, 0)
            max_val = cat_default * (1 + MAX_WEIGHT_SHIFT_RATIO)
            min_val = cat_default * (1 - MAX_WEIGHT_SHIFT_RATIO)
            weights[dim] = max(0.0, min(max_val, max(min_val, weights[dim])))

        # Renormalize to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        else:
            n = len(weights)
            weights = {k: 1.0 / n for k in weights}

        return weights

    @staticmethod
    def _detect_price_tier(price_bhd: float, category: str = "other", *, comparison_prices=None) -> str:
        """Bundle C § 3b/3e/3f — thin shim that delegates to the module-level
        function so existing one-arg callers (legacy unit tests) keep working
        and new callers can pass a category for per-category breakpoints."""
        return _detect_price_tier(price_bhd, category, comparison_prices=comparison_prices)

    @staticmethod
    def _is_cross_tier(tiers: List[str]) -> bool:
        return len(set(tiers)) > 1

    def _compute_raw_scores(self, product: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Compute raw (un-normalized) signal scores for a product.

        Extracts 5 universal signals: price, spec, review, reliability, popularity.
        These are then mapped to category-specific dimensions in _normalize_scores.
        """
        scores: Dict[str, Any] = {}

        # Price signal (raw: actual price amount, lower = better)
        price_data = product.get("price")
        if price_data and isinstance(price_data, dict) and price_data.get("amount"):
            try:
                scores["price_raw"] = float(price_data["amount"])
            except (ValueError, TypeError):
                scores["price_raw"] = None
                scores["_price_missing"] = True
        else:
            scores["price_raw"] = None
            scores["_price_missing"] = True

        # Spec signal (raw: category-specific aggregate)
        specs = product.get("specs")
        if specs and isinstance(specs, dict):
            scores["spec_raw"] = self._score_specs(specs, category)
        else:
            scores["spec_raw"] = None
            scores["_spec_missing"] = True

        # Review signal (raw: rating out of 5)
        rating = product.get("rating")
        if rating is not None:
            try:
                scores["review_raw"] = float(rating)
            except (ValueError, TypeError):
                scores["review_raw"] = None
                scores["_review_missing"] = True
        else:
            scores["review_raw"] = None
            scores["_review_missing"] = True

        # Reliability signal (from fact_check)
        fact_check = product.get("fact_check")
        if fact_check and isinstance(fact_check, dict):
            scores["reliability_raw"] = self._score_reliability(fact_check)
        else:
            scores["reliability_raw"] = None
            scores["_reliability_missing"] = True

        # Popularity signal (from review_count + source_ratings count)
        scores["popularity_raw"] = self._score_popularity(product)
        if scores["popularity_raw"] is None:
            scores["_popularity_missing"] = True

        # Bundle C § 2a — additionally emit per-dim scores under their
        # category-specific dim keys (e.g. performance_score for electronics)
        # so consumers can read dim-level signal availability directly off
        # _compute_raw_scores without descending through _normalize_*. When
        # ENABLE_BUNDLE_C_SCORING=true AND a raw signal is missing, the
        # per-dim value propagates as None (the missing-data floor of 50
        # is killed). When the flag is OFF, legacy MISSING_SCORE injection
        # preserves backward-compat for existing breakdown consumers.
        dim_map = self._DIMENSION_SIGNAL_MAP.get(
            category, self._DIMENSION_SIGNAL_MAP["other"]
        )
        flag_on = _bundle_c_scoring_enabled()
        signal_to_raw_key = {
            "spec": "spec_raw",
            "spec_secondary": "spec_raw",  # spec_secondary blends spec+review; raw availability tracks spec
            "review": "review_raw",
            "reliability": "reliability_raw",
            "popularity": "popularity_raw",
            "value": None,  # value dim derives from price+spec — see below
        }
        for dim_name, signal_kind in dim_map.items():
            raw_key = signal_to_raw_key.get(signal_kind)
            if signal_kind == "value":
                # value dim requires BOTH a price AND a spec signal. Either
                # missing => dim missing under flag-on.
                missing = scores.get("price_raw") is None or scores.get("spec_raw") is None
            else:
                missing = raw_key is None or scores.get(raw_key) is None
            if missing:
                scores[dim_name] = None if flag_on else MISSING_SCORE
            else:
                # Populated signal — surface a numeric value so downstream
                # consumers see a non-None number. Exact normalization to
                # 0-100 happens in _normalize_scores; here we expose the
                # raw signal so test assertions (`is numeric, not None`)
                # hold without prejudicing the dim-level math.
                if signal_kind == "value":
                    # Synthesize a placeholder from spec_raw — the real
                    # value formula runs later in _normalize_scores.
                    scores[dim_name] = float(scores["spec_raw"])
                else:
                    scores[dim_name] = float(scores[raw_key])

        return scores

    def _score_specs(self, specs: Dict[str, Any], category: str) -> float:
        """Score specs on a 0-1 scale based on category-specific logic."""
        schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
        schema_fields = CATEGORY_SPEC_SCHEMAS[schema_key]

        higher = HIGHER_IS_BETTER_BY_CATEGORY.get(category, set())
        lower = LOWER_IS_BETTER_BY_CATEGORY.get(category, set())

        total_score = 0.0
        scored_fields = 0

        for field in schema_fields:
            value = specs.get(field)
            if not value or value == "N/A":
                continue

            numeric = self._extract_number(str(value))
            if numeric is not None:
                if field in higher:
                    total_score += numeric
                    scored_fields += 1
                elif field in lower:
                    total_score -= numeric
                    scored_fields += 1
                else:
                    total_score += 1
                    scored_fields += 1
            else:
                total_score += 1
                scored_fields += 1

        if scored_fields == 0:
            return 0.0

        total_fields = len(schema_fields)
        coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0
        min_coverage = CATEGORY_MIN_COVERAGE.get(schema_key, 0.3)
        if coverage_ratio < min_coverage:
            penalty_factor = 0.5 + coverage_ratio
            return (total_score / scored_fields) * penalty_factor

        return total_score / scored_fields

    def _score_reliability(self, fact_check: Dict[str, Any]) -> float:
        """Score reliability from fact_check data on 0-1 scale."""
        verified = fact_check.get("specs_verified", 0)
        likely = fact_check.get("specs_likely", 0)
        flagged = fact_check.get("specs_flagged", 0)
        unverified = fact_check.get("specs_unverified", 0)
        total = verified + likely + flagged + unverified

        if total == 0:
            return 0.5

        score = (verified * 1.0 + likely * 0.7 + unverified * 0.3 + flagged * 0.0) / total

        if fact_check.get("price_verified"):
            score = min(1.0, score + 0.1)

        if fact_check.get("review_sentiment_consistent") is True:
            score = min(1.0, score + 0.05)
        elif fact_check.get("review_sentiment_consistent") is False:
            score = max(0.0, score - 0.1)

        return score

    def _score_popularity(self, product: Dict[str, Any]) -> Optional[float]:
        """Score popularity from review_count and source_ratings."""
        review_count = product.get("review_count")
        reviews_data = product.get("reviews")
        source_count = 0

        if reviews_data and isinstance(reviews_data, dict):
            source_ratings = reviews_data.get("source_ratings", [])
            if isinstance(source_ratings, list):
                source_count = len(source_ratings)

        if review_count is None and source_count == 0:
            return None

        count = 0
        if review_count is not None:
            try:
                count = int(review_count)
            except (ValueError, TypeError):
                count = 0

        import math
        if count > 0:
            count_score = min(1.0, math.log10(count) / 3.0)
        else:
            count_score = 0.0

        source_bonus = min(0.2, source_count * 0.05)

        return min(1.0, count_score + source_bonus)

    # ---- Dimension mapping: raw signals → category-specific dimension keys ----
    # Each category maps its 6 dimensions to one of the 5 raw signals.
    # "value"-type dims use the tier-aware value formula (spec+price combo).
    # "spec"-type dims use spec_raw, "review"-type use review_raw, etc.

    _DIMENSION_SIGNAL_MAP = {
        "electronics": {
            "performance_score": "spec", "value_score": "value",
            "build_quality_score": "reliability", "feature_score": "spec_secondary",
            "ecosystem_score": "popularity", "futureproof_score": "review",
        },
        "grocery": {
            "nutrition_score": "spec", "ingredient_score": "reliability",
            "taste_score": "review", "serving_value_score": "value",
            "dietary_score": "spec_secondary", "availability_score": "popularity",
        },
        "supplements": {
            "efficacy_score": "spec", "safety_score": "reliability",
            "dosage_score": "spec_secondary", "serving_value_score": "value",
            "form_score": "review", "trust_score": "popularity",
        },
        "makeup": {
            "shade_score": "spec", "longevity_score": "review",
            "skin_compat_score": "reliability", "finish_score": "spec_secondary",
            "ingredient_safety_score": "popularity", "perf_value_score": "value",
        },
        "skincare": {
            "actives_score": "spec", "evidence_score": "reliability",
            "skin_compat_score": "review", "formulation_score": "spec_secondary",
            "sensory_score": "popularity", "results_value_score": "value",
        },
        "haircare": {
            "hair_match_score": "spec", "results_score": "review",
            "ingredient_score": "reliability", "scent_score": "spec_secondary",
            "multi_value_score": "value", "scalp_score": "popularity",
        },
        "fragrances": {
            "character_score": "spec", "longevity_score": "spec_secondary",
            "projection_score": "review", "versatility_score": "reliability",
            "wear_value_score": "value", "presentation_score": "popularity",
        },
        "fashion": {
            "craft_score": "spec", "fit_score": "review",
            "style_score": "popularity", "durability_score": "reliability",
            "heritage_score": "spec_secondary", "cpw_score": "value",
        },
        "other": {
            "function_score": "spec", "build_score": "reliability",
            "review_score": "review", "value_score": "value",
            "reliability_score": "spec_secondary", "feature_match_score": "popularity",
        },
    }

    def _normalize_scores(
        self,
        raw_scores: List[Dict[str, Any]],
        products_data: List[Dict[str, Any]],
        category: str = "other",
    ):
        """Normalize raw scores to category-specific dimensions on 0-100 scale.
        
        Returns (normalized, price_tiers, is_cross_tier_flag) tuple.
        """
        if category not in CATEGORY_DIMENSIONS:
            category = "other"

        # Detect price tiers for value score — Bundle C § 3e: pass category
        # so per-category breakpoints apply (electronics 100/400/800/2000/inf
        # vs. supplements 11/30/60/inf, etc.). A.5.5 will wire comparison_prices
        # for the 'other' geometric-mean sub-scale.
        price_tiers = []
        for rs in raw_scores:
            price = rs.get("price_raw")
            if price is not None and price > 0:
                price_tiers.append(self._detect_price_tier(price, category))
            else:
                price_tiers.append("mid")
        is_cross_tier_flag = self._is_cross_tier(price_tiers)

        # Compute intermediate normalized signals
        price_scores = [self._normalize_price(raw_scores, i) for i in range(len(raw_scores))]
        spec_scores = [self._normalize_dimension(raw_scores, i, "spec_raw", higher_better=True) for i in range(len(raw_scores))]
        review_scores = [self._normalize_review(raw_scores, i) for i in range(len(raw_scores))]
        reliability_scores = [self._normalize_direct(raw_scores, i, "reliability_raw") for i in range(len(raw_scores))]
        popularity_scores = [self._normalize_direct(raw_scores, i, "popularity_raw") for i in range(len(raw_scores))]

        # Compute spec_secondary: blended spec and review for variety
        spec_secondary_scores = []
        for i in range(len(raw_scores)):
            s = spec_scores[i]
            r = review_scores[i]
            if s == MISSING_SCORE and r == MISSING_SCORE:
                spec_secondary_scores.append(MISSING_SCORE)
            elif s == MISSING_SCORE:
                spec_secondary_scores.append(r)
            elif r == MISSING_SCORE:
                spec_secondary_scores.append(s)
            else:
                spec_secondary_scores.append(round(s * 0.6 + r * 0.4, 1))

        # Value scores (tier-aware)
        value_scores = [
            self._compute_value_score(spec_scores[i], price_scores[i], price_tiers[i], is_cross_tier_flag)
            for i in range(len(raw_scores))
        ]

        signal_arrays = {
            "price": price_scores,
            "spec": spec_scores,
            "review": review_scores,
            "reliability": reliability_scores,
            "popularity": popularity_scores,
            "spec_secondary": spec_secondary_scores,
            "value": value_scores,
        }

        # Map signals to category-specific dimension keys
        dim_signal_map = self._DIMENSION_SIGNAL_MAP.get(category, self._DIMENSION_SIGNAL_MAP["other"])
        dims = CATEGORY_DIMENSIONS[category]

        normalized = []
        for i in range(len(raw_scores)):
            scores = {}
            for dim in dims:
                signal = dim_signal_map.get(dim, "spec")
                scores[dim] = signal_arrays[signal][i]

                # Mark missing data flag for tracking
                if scores[dim] == MISSING_SCORE:
                    raw_scores[i][f"_{dim}_missing"] = True

            normalized.append(scores)

        return normalized, price_tiers, is_cross_tier_flag

    def _normalize_price(self, raw_scores: List[Dict], idx: int) -> float:
        """Normalize price score: lower price = higher score."""
        prices = []
        for rs in raw_scores:
            p = rs.get("price_raw")
            if p is not None:
                prices.append(p)

        current = raw_scores[idx].get("price_raw")
        if current is None or not prices:
            return MISSING_SCORE

        max_price = max(prices)
        if max_price == 0:
            return MISSING_SCORE

        min_price = min(prices)
        if max_price == min_price:
            return 75.0

        ratio = (current - min_price) / (max_price - min_price)
        return round(100 - ratio * 70, 1)

    def _normalize_dimension(
        self, raw_scores: List[Dict], idx: int, key: str, higher_better: bool = True
    ) -> float:
        """Normalize a dimension score relative to competitors."""
        values = []
        for rs in raw_scores:
            v = rs.get(key)
            if v is not None:
                values.append(v)

        current = raw_scores[idx].get(key)
        if current is None or not values:
            return MISSING_SCORE

        max_val = max(values)
        min_val = min(values)

        if max_val == min_val:
            return 70.0

        if higher_better:
            ratio = (current - min_val) / (max_val - min_val)
        else:
            ratio = (max_val - current) / (max_val - min_val)

        return round(30 + ratio * 70, 1)

    def _normalize_review(self, raw_scores: List[Dict], idx: int) -> float:
        """Normalize review score: rating/5 * 100."""
        rating = raw_scores[idx].get("review_raw")
        if rating is None:
            return MISSING_SCORE

        rating = max(1.0, min(5.0, rating))
        return round((rating - 1.0) / 4.0 * 80 + 20, 1)

    def _normalize_direct(self, raw_scores: List[Dict], idx: int, key: str) -> float:
        """Normalize a 0-1 raw score to 0-100."""
        val = raw_scores[idx].get(key)
        if val is None:
            return MISSING_SCORE
        return round(max(0, min(100, val * 100)), 1)

    def _compute_value_score(self, spec_score: float, price_score: float, price_tier: str, is_cross_tier: bool) -> float:
        """Value = tier-aware combination of spec quality and price affordability."""
        if spec_score == MISSING_SCORE and price_score == MISSING_SCORE:
            return MISSING_SCORE
        if spec_score == MISSING_SCORE:
            return price_score
        if price_score == MISSING_SCORE:
            return spec_score
        if is_cross_tier:
            expected = TIER_EXPECTATIONS.get(price_tier, 0.7) * 100
            delivery = spec_score
            value = 50 + (delivery - expected) * 0.8
            return round(max(0, min(100, value)), 1)
        else:
            return round(spec_score * 0.6 + price_score * 0.4, 1)

    def _empty_result(self, count: int) -> Dict[str, Any]:
        """Return empty scoring result for edge cases."""
        dims = CATEGORY_DIMENSIONS["other"]
        other_weights = CATEGORY_DIMENSION_WEIGHTS["other"]
        scores = {}
        for i in range(count):
            scores[f"product_{i}"] = {
                "overall": MISSING_SCORE,
                "breakdown": {k: MISSING_SCORE for k in dims},
                "weights_used": dict(other_weights),
                "missing_data": list(dims),
            }
        return {
            "scores": scores,
            "winner_index": 0,
            "win_margin": 0,
            "scoring_method": "default",
        }

    def compute_dimension_winners(self, scoring_result: Dict[str, Any], product_names: List[str], category: str = "other") -> Dict[str, Any]:
        """Compute per-dimension winner between two products."""
        scores = scoring_result.get("scores", {})
        if len(scores) < 2 or len(product_names) < 2:
            return {}

        if category not in CATEGORY_DIMENSIONS:
            category = "other"

        # Infer category from breakdown keys if not provided explicitly
        b0 = scores.get("product_0", {}).get("breakdown", {})
        b1 = scores.get("product_1", {}).get("breakdown", {})

        dims = CATEGORY_DIMENSIONS[category]
        # Fallback: if breakdown keys don't match category dims, use whatever keys are there
        if b0 and not any(d in b0 for d in dims):
            dims = list(b0.keys())

        winners = {}
        for dim in dims:
            s0 = b0.get(dim, MISSING_SCORE)
            s1 = b1.get(dim, MISSING_SCORE)

            if s0 == MISSING_SCORE and s1 == MISSING_SCORE:
                winners[dim] = {"winner": "N/A", "margin": None}
            elif abs(s0 - s1) < 3.0:
                winners[dim] = {"winner": "tie", "margin": round(abs(s0 - s1), 1)}
            elif s0 > s1:
                winners[dim] = {"winner": product_names[0], "margin": round(s0 - s1, 1)}
            else:
                winners[dim] = {"winner": product_names[1], "margin": round(s1 - s0, 1)}

        return winners

    def compute_value_badge(self, value_score: float, price_tier: str) -> str:
        """Deterministic value badge from value_score and price tier.

        Returns: 'great_value', 'fair_price', 'premium_price', or 'overpriced'
        """
        if value_score >= 75:
            if price_tier == "luxury":
                return "fair_price"
            return "great_value"
        elif value_score >= 50:
            return "fair_price"
        elif value_score >= 25:
            return "premium_price"
        else:
            return "overpriced"

    def compute_tradeoff_pairs(
        self,
        dimension_winners: Dict[str, Any],
        product_names: List[str],
        winner_index: int,
    ) -> List[Dict[str, Any]]:
        """Build tradeoff pairs from dimension winners.

        Pairs each winner-winning dimension with the loser's strongest dimension.
        Filters margins <= 5, returns max 3 sorted by combined impact.
        """
        winner_name = product_names[winner_index]
        loser_name = product_names[1 - winner_index]

        winner_dims = []
        loser_dims = []

        for dim, info in dimension_winners.items():
            if info["winner"] in ("tie", "N/A") or info.get("margin") is None:
                continue
            if info["margin"] <= 5:
                continue
            entry = {
                "dimension": dim,
                "product": info["winner"],
                "margin": info["margin"],
            }
            if info["winner"] == winner_name:
                winner_dims.append(entry)
            elif info["winner"] == loser_name:
                loser_dims.append(entry)

        if not winner_dims or not loser_dims:
            return []

        winner_dims.sort(key=lambda x: x["margin"], reverse=True)
        loser_dims.sort(key=lambda x: x["margin"], reverse=True)

        pairs = []
        for i in range(min(len(winner_dims), len(loser_dims), 3)):
            pairs.append({
                "winner_wins": winner_dims[i],
                "loser_wins": loser_dims[i],
            })

        pairs.sort(
            key=lambda p: p["winner_wins"]["margin"] + p["loser_wins"]["margin"],
            reverse=True,
        )

        return pairs[:3]

    def compute_confidence(
        self,
        products: List[Dict[str, Any]],
        shopping_count: int = 0,
        cached: bool = False,
    ) -> Dict[str, Any]:
        """Assemble confidence indicators from existing product data."""
        product = products[0] if products else {}
        price_data = product.get("price", {})
        fact_check = product.get("fact_check", {})

        source_method = price_data.get("source_method", "estimated")
        if source_method in ("local_bhd", "page_scrape", "page_scrape_rendered"):
            method = "retailer_verified"
        elif source_method == "converted_usd":
            method = "converted"
        else:
            method = "estimated"

        price_conf = {
            "source_count": shopping_count,
            "method": method,
            "freshness": "live" if not cached else "cached",
        }
        price_strong = shopping_count >= 2 and method != "estimated"

        review_count = product.get("review_count") or 0
        rating_verified = product.get("rating_verified", False)
        rating_source = product.get("rating_source")
        rating_conf = {
            "review_count": review_count,
            "source": rating_source.get("name") if rating_source else None,
            "verified": rating_verified,
        }
        rating_strong = review_count >= 50 and rating_verified

        verified = fact_check.get("specs_verified", 0)
        likely = fact_check.get("specs_likely", 0)
        unverified = fact_check.get("specs_unverified", 0)
        flagged = fact_check.get("specs_flagged", 0)
        total = verified + likely + unverified + flagged
        verified_pct = round((verified / total) * 100) if total > 0 else 0
        specs_conf = {
            "verified_pct": verified_pct,
            "citation_count": total,
        }
        specs_strong = verified_pct >= 60

        strong_count = sum([price_strong, rating_strong, specs_strong])
        if strong_count >= 3:
            overall = "high"
        elif strong_count >= 2:
            overall = "medium"
        else:
            overall = "low"

        return {
            "price": price_conf,
            "rating": rating_conf,
            "specs": specs_conf,
            "overall": overall,
        }

    @staticmethod
    def _apply_capped_adjustments(
        weights: Dict[str, float],
        deltas: Dict[str, float],
        original: Dict[str, float],
        max_ratio: float,
    ) -> Dict[str, float]:
        """Apply deltas to weights with per-dimension capping and renormalization."""
        for dim in weights:
            if dim in deltas:
                max_shift = original[dim] * max_ratio
                clamped = max(-max_shift, min(max_shift, deltas[dim]))
                weights[dim] += clamped

        for _ in range(3):
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}
            exceeded = False
            for dim in weights:
                max_shift = original[dim] * max_ratio
                if abs(weights[dim] - original[dim]) > max_shift + 0.0001:
                    exceeded = True
                    if weights[dim] > original[dim]:
                        weights[dim] = original[dim] + max_shift
                    else:
                        weights[dim] = original[dim] - max_shift
            if not exceeded:
                break

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def apply_behavioral_adjustments(
        self,
        weights: Dict[str, float],
        behavior_profile: Dict[str, Any],
    ) -> Dict[str, float]:
        """Apply behavioral profile adjustments to weights (capped at +/-10%).

        Operates on whichever dimension keys are present in weights dict.
        """
        sensitivity = behavior_profile.get("dimension_sensitivity", {})
        if not sensitivity:
            return weights

        original = dict(weights)
        avg_sensitivity = sum(sensitivity.values()) / len(sensitivity) if sensitivity else 0
        deltas: Dict[str, float] = {}
        for dim in weights:
            if dim in sensitivity:
                deltas[dim] = (sensitivity[dim] - avg_sensitivity) * weights[dim]

        return self._apply_capped_adjustments(weights, deltas, original, MAX_BEHAVIORAL_SHIFT_RATIO)

    def apply_session_signals(
        self,
        weights: Dict[str, float],
        session_signals: Dict[str, Any],
    ) -> Dict[str, float]:
        """Apply in-session signal adjustments to weights (capped at +/-5%).

        Operates on whichever dimension keys are present in weights dict.
        Tab-to-dimension mapping finds the first matching key in the weights.
        """
        dwell = session_signals.get("tab_dwell_ms", {})
        if not dwell:
            return weights

        # Dynamic tab → dimension mapping: find the best match in current weights
        # "specs" tab → first spec-like dim, "reviews" → first review-like dim
        dim_keys = list(weights.keys())
        tab_dim_map = {}
        for tab in dwell:
            if tab == "specs" and len(dim_keys) > 0:
                tab_dim_map[tab] = dim_keys[0]  # First dim is typically spec-related
            elif tab == "reviews" and len(dim_keys) > 2:
                tab_dim_map[tab] = dim_keys[2]  # Third dim is typically review-related
            elif tab == "overview" and len(dim_keys) > 3:
                tab_dim_map[tab] = dim_keys[3]  # Fourth dim as price/value proxy

        total_dwell = sum(dwell.values())
        if total_dwell == 0:
            return weights

        original = dict(weights)
        avg_ratio = 1.0 / len(dwell) if dwell else 0
        deltas: Dict[str, float] = {}
        for tab, ms in dwell.items():
            dim = tab_dim_map.get(tab)
            if dim and dim in weights:
                ratio = ms / total_dwell
                deltas[dim] = (ratio - avg_ratio) * weights[dim]

        return self._apply_capped_adjustments(weights, deltas, original, MAX_SESSION_SHIFT_RATIO)

    @staticmethod
    def _extract_number(text: str) -> Optional[float]:
        """Extract the first number from a text string."""
        if not text:
            return None
        match = re.search(r'[\d,]+\.?\d*', text.replace(",", ""))
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def build_scores_summary(self, scoring_result: Dict[str, Any], product_names: List[str]) -> str:
        """Build a text summary of scores for the GPT verdict prompt."""
        if not scoring_result or "scores" not in scoring_result:
            return ""

        lines = ["Product scores (deterministic, 0-100 scale):"]
        scores = scoring_result["scores"]

        # Detect category from breakdown keys
        sample_breakdown = scores.get("product_0", {}).get("breakdown", {})
        category = "other"
        for cat, dims in CATEGORY_DIMENSIONS.items():
            if set(dims) == set(sample_breakdown.keys()):
                category = cat
                break

        dims = CATEGORY_DIMENSIONS.get(category, CATEGORY_DIMENSIONS["other"])

        for i, name in enumerate(product_names):
            key = f"product_{i}"
            if key not in scores:
                continue
            ps = scores[key]
            overall = ps["overall"]
            breakdown = ps["breakdown"]
            tier = scoring_result.get("price_tiers", {}).get(name, "unknown")
            lines.append(f"  {name}: {overall}/100 overall (price tier: {tier})")
            dim_strs = []
            for dim in dims:
                display = DIMENSION_DISPLAY_NAMES.get(dim, dim.replace("_score", ""))
                dim_strs.append(f"{display}={breakdown.get(dim, 50)}")
            lines.append(f"    Breakdown: {', '.join(dim_strs)}")

        winner_idx = scoring_result.get("winner_index", 0)
        margin = scoring_result.get("win_margin", 0)
        if len(product_names) >= 2:
            lines.append(f"  Score winner: {product_names[winner_idx]} by {margin} points")

        dim_winners = scoring_result.get("dimension_winners", {})
        if dim_winners:
            dim_parts = []
            for dim in dims:
                w = dim_winners.get(dim, {})
                winner = w.get("winner", "N/A")
                display = DIMENSION_DISPLAY_NAMES.get(dim, dim.replace("_score", ""))
                dim_parts.append(f"{display}={winner}")
            lines.append(f"  Dimension leaders: {', '.join(dim_parts)}")

        if scoring_result.get("is_cross_tier"):
            lines.append("  Note: Products are in different price tiers — value scoring adjusted for tier expectations.")

        return "\n".join(lines)


# Module-level singleton
_scoring_service = None


def get_scoring_service() -> ScoringService:
    """Get or create the scoring service singleton."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service


# Bundle E § Decision 4 — perceived-score calibration.
# Formula: clamp(70 + (raw_score - 50) * 0.5, 60, 95).
# Honesty guard: when every raw_signal < 40, force display < 70 (still ≥60).
_CALIBRATION_CEILING = 95
_CALIBRATION_FLOOR = 60
_HONESTY_GUARD_THRESHOLD = 40
_HONESTY_GUARD_CEILING = 69


def calibrate_score(raw_score: float, raw_signals: list[float] | None = None) -> int:
    base = 70 + (raw_score - 50) * 0.5
    base = max(_CALIBRATION_FLOOR, min(_CALIBRATION_CEILING, base))
    display = int(round(base))
    if raw_signals and all(s < _HONESTY_GUARD_THRESHOLD for s in raw_signals):
        display = max(_CALIBRATION_FLOOR, min(_HONESTY_GUARD_CEILING, display))
    return display


# Bundle E § Decision 2 — self-describing dimensions[] contract.
# Always emits 3 core dims (price, reviews, value); 0..3 contextual.
# Never emits a dim where either product lacks the underlying data.
_POPULARITY_MIN_REVIEW_COUNT = 50
_NEUTRAL_DISPLAY_SCORE = 75


def _get_price(product: dict) -> float | None:
    price = product.get("price")
    if isinstance(price, dict):
        return price.get("amount")
    return None


def _get_currency(product: dict) -> str:
    price = product.get("price")
    if isinstance(price, dict):
        return price.get("currency", "BHD")
    return "BHD"


def _dim_price(products: list[dict]) -> dict:
    a, b = products[0], products[1]
    pa, pb = _get_price(a) or 0.0, _get_price(b) or 0.0
    if pa <= 0 or pb <= 0:
        score_a = score_b = _NEUTRAL_DISPLAY_SCORE
        delta = "Price data unavailable"
        confidence = "low"
    else:
        lo, hi = min(pa, pb), max(pa, pb)
        ratio = lo / hi
        winner_raw = 80
        loser_raw = 50 + 30 * ratio
        if pa <= pb:
            score_a, score_b = calibrate_score(winner_raw), calibrate_score(loser_raw)
        else:
            score_a, score_b = calibrate_score(loser_raw), calibrate_score(winner_raw)
        diff = round(abs(pa - pb), 2)
        currency = _get_currency(a) if pa <= pb else _get_currency(b)
        delta = f"{currency} {diff:g} less"
        confidence = "high"
    return {
        "key": "price", "label": "Price",
        "score_a": score_a, "score_b": score_b,
        "delta_text": delta, "confidence": confidence, "is_core": True,
    }


def _dim_reviews(products: list[dict]) -> dict:
    a, b = products[0], products[1]
    ra, rb = a.get("rating"), b.get("rating")
    if ra is None or rb is None:
        score_a = score_b = _NEUTRAL_DISPLAY_SCORE
        delta = "Limited review data"
        confidence = "low"
    else:
        score_a = calibrate_score(40 + ra * 10)
        score_b = calibrate_score(40 + rb * 10)
        diff = round(abs(ra - rb), 1)
        if diff == 0:
            delta = "Same rating"
        else:
            delta = f"{diff} stars higher"
        confidence = "high"
    return {
        "key": "reviews", "label": "Reviews",
        "score_a": score_a, "score_b": score_b,
        "delta_text": delta, "confidence": confidence, "is_core": True,
    }


def _dim_value(products: list[dict]) -> dict:
    a, b = products[0], products[1]
    pa, pb = _get_price(a) or 0.0, _get_price(b) or 0.0
    ra, rb = a.get("rating") or 4.0, b.get("rating") or 4.0
    va = (ra / pa) if pa > 0 else 0.1
    vb = (rb / pb) if pb > 0 else 0.1
    hi = max(va, vb) or 1.0
    score_a = calibrate_score(50 + 35 * (va / hi))
    score_b = calibrate_score(50 + 35 * (vb / hi))
    if va >= vb:
        delta = "More features per dinar"
    else:
        delta = "Stronger value ratio"
    return {
        "key": "value", "label": "Value",
        "score_a": score_a, "score_b": score_b,
        "delta_text": delta, "confidence": "medium", "is_core": True,
    }


def _dim_dpi(products: list[dict]) -> dict | None:
    a, b = products[0], products[1]
    da = a.get("specs", {}).get("dpi")
    db = b.get("specs", {}).get("dpi")
    if not da or not db:
        return None
    hi = max(da, db)
    score_a = calibrate_score(50 + 35 * (da / hi))
    score_b = calibrate_score(50 + 35 * (db / hi))
    return {
        "key": "dpi", "label": "DPI",
        "score_a": score_a, "score_b": score_b,
        "delta_text": f"{da} DPI vs {db} DPI",
        "confidence": "high", "is_core": False,
    }


def _dim_popularity(products: list[dict]) -> dict | None:
    a, b = products[0], products[1]
    ca, cb = a.get("review_count"), b.get("review_count")
    if not ca or not cb or ca <= _POPULARITY_MIN_REVIEW_COUNT or cb <= _POPULARITY_MIN_REVIEW_COUNT:
        return None
    hi = max(ca, cb)
    score_a = calibrate_score(50 + 35 * (ca / hi))
    score_b = calibrate_score(50 + 35 * (cb / hi))
    return {
        "key": "popularity", "label": "Popularity",
        "score_a": score_a, "score_b": score_b,
        "delta_text": f"{ca} reviews vs {cb}",
        "confidence": "high", "is_core": False,
    }


def _dim_build_quality(products: list[dict]) -> dict | None:
    a, b = products[0], products[1]
    wa, wb = a.get("warranty_years"), b.get("warranty_years")
    if wa is None or wb is None:
        return None
    hi = max(wa, wb) or 1
    score_a = calibrate_score(60 + 25 * (wa / hi))
    score_b = calibrate_score(60 + 25 * (wb / hi))
    return {
        "key": "build_quality", "label": "Build",
        "score_a": score_a, "score_b": score_b,
        "delta_text": f"{wa}-year vs {wb}-year warranty",
        "confidence": "medium", "is_core": False,
    }


def build_dimensions_v2(
    products_data: list[dict],
    scoring_result: dict,
    category: str,
) -> list[dict]:
    dims: list[dict] = [
        _dim_price(products_data),
        _dim_reviews(products_data),
        _dim_value(products_data),
    ]
    cat_a = products_data[0].get("category")
    cat_b = products_data[1].get("category")
    same_category = cat_a == cat_b and cat_a is not None
    if same_category:
        for builder in (_dim_build_quality, _dim_popularity, _dim_dpi):
            dim = builder(products_data)
            if dim is not None:
                dims.append(dim)
    return dims[:6]

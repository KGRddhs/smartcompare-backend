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

# Budget adjustments per category (same keys as category dimension weights)
CATEGORY_BUDGET_ADJUSTMENTS = {
    "electronics": {"budget": {"value_score": 0.10, "performance_score": -0.05}, "mid": {}, "premium": {"performance_score": 0.10, "value_score": -0.05}},
    "grocery": {"budget": {"serving_value_score": 0.10, "nutrition_score": -0.05}, "mid": {}, "premium": {"nutrition_score": 0.10, "serving_value_score": -0.05}},
    "supplements": {"budget": {"serving_value_score": 0.10, "efficacy_score": -0.05}, "mid": {}, "premium": {"efficacy_score": 0.10, "serving_value_score": -0.05}},
    "makeup": {"budget": {"perf_value_score": 0.10, "shade_score": -0.05}, "mid": {}, "premium": {"longevity_score": 0.10, "perf_value_score": -0.05}},
    "skincare": {"budget": {"results_value_score": 0.10, "actives_score": -0.05}, "mid": {}, "premium": {"actives_score": 0.10, "results_value_score": -0.05}},
    "haircare": {"budget": {"multi_value_score": 0.10, "results_score": -0.05}, "mid": {}, "premium": {"results_score": 0.10, "multi_value_score": -0.05}},
    "fragrances": {"budget": {"wear_value_score": 0.10, "character_score": -0.05}, "mid": {}, "premium": {"character_score": 0.10, "wear_value_score": -0.05}},
    "fashion": {"budget": {"cpw_score": 0.10, "craft_score": -0.05}, "mid": {}, "premium": {"craft_score": 0.10, "cpw_score": -0.05}},
    "other": {"budget": {"value_score": 0.10, "function_score": -0.05}, "mid": {}, "premium": {"function_score": 0.10, "value_score": -0.05}},
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

# Default score for missing data
MISSING_SCORE = 50

# Price tier thresholds (BHD)
PRICE_TIERS = {
    "budget":    (0, 11),
    "mid":       (11, 57),
    "premium":   (57, 189),
    "luxury":    (189, float("inf")),
}

# Expected quality delivery per tier (0-1 scale)
TIER_EXPECTATIONS = {"budget": 0.6, "mid": 0.7, "premium": 0.8, "luxury": 0.85}

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
    """Deterministic scoring engine for product comparisons."""

    def compute_scores(
        self,
        products_data: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]] = None,
        behavior_profile: Optional[Dict[str, Any]] = None,
        session_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute scores for a list of products.

        Args:
            products_data: List of product dicts (from _fetch_product_data).
                Each has: specs, price, reviews, rating, review_count,
                fact_check, rating_verified, rating_source, etc.
            preferences: Optional user preferences dict with:
                priorities (list), budget (str), lifestyle (list), brand_attitude (str)
            behavior_profile: Optional behavioral profile dict from user history.
                Applied as ±10% weight adjustment after explicit preferences.
            session_signals: Optional in-session signals dict from current session.
                Applied as ±5% weight adjustment after behavioral adjustments.

        Returns:
            Dict with per-product scores, winner, and metadata.
        """
        if not products_data or len(products_data) < 2:
            return self._empty_result(len(products_data))

        category = products_data[0].get("category", "other")
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
        normalized = self._normalize_scores(raw_scores, products_data)

        # Compute overall weighted score for each product
        result_products = {}
        for i, product in enumerate(products_data):
            product_key = f"product_{i}"
            breakdown = normalized[i]
            overall = sum(
                breakdown[dim] * weights[dim] for dim in weights
            )
            overall = round(max(0, min(100, overall)), 1)

            # Track which dimensions had missing data
            missing_dims = []
            for dim in CATEGORY_WEIGHTS["other"]:
                if raw_scores[i].get(f"_{dim}_missing"):
                    missing_dims.append(dim)

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
            price_tiers_map[name] = self._price_tiers[i] if hasattr(self, '_price_tiers') and i < len(self._price_tiers) else "mid"

        # Compute dimension winners
        product_names = [
            f"{p.get('brand', '')} {p.get('name', '')}".strip()
            for p in products_data
        ]
        result_so_far = {"scores": result_products}
        dimension_winners = self.compute_dimension_winners(result_so_far, product_names)

        return {
            "scores": result_products,
            "winner_index": winner_index,
            "win_margin": win_margin,
            "scoring_method": scoring_method,
            "price_tiers": price_tiers_map,
            "is_cross_tier": self._is_cross_tier_flag if hasattr(self, '_is_cross_tier_flag') else False,
            "dimension_winners": dimension_winners,
            "category_weights": dict(CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["other"])),
        }

    def _compute_weights(self, preferences: Optional[Dict[str, Any]], category: str = "other") -> Dict[str, float]:
        """Compute scoring weights from category defaults + user preferences."""
        base_weights = CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["other"])
        weights = dict(base_weights)

        if not preferences:
            return weights

        # Apply priority adjustments (stack for multiple priorities)
        for priority in preferences.get("priorities", []):
            adjustments = PRIORITY_ADJUSTMENTS.get(priority, {})
            for dim, delta in adjustments.items():
                weights[dim] = weights.get(dim, 0) + delta

        # Apply budget adjustment
        budget = preferences.get("budget", "mid")
        budget_adj = BUDGET_ADJUSTMENTS.get(budget, {})
        for dim, delta in budget_adj.items():
            weights[dim] = weights.get(dim, 0) + delta

        # Cap each dimension's shift to ±30% of its CATEGORY weight (not global default)
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
    def _detect_price_tier(price_bhd: float) -> str:
        for tier, (low, high) in PRICE_TIERS.items():
            if low <= price_bhd < high:
                return tier
        return "luxury"

    @staticmethod
    def _is_cross_tier(tiers: List[str]) -> bool:
        return len(set(tiers)) > 1

    def _compute_raw_scores(self, product: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Compute raw (un-normalized) dimension scores for a product."""
        scores: Dict[str, Any] = {}

        # Price score (raw: actual price amount, lower = better)
        price_data = product.get("price")
        if price_data and isinstance(price_data, dict) and price_data.get("amount"):
            try:
                scores["price_raw"] = float(price_data["amount"])
            except (ValueError, TypeError):
                scores["price_raw"] = None
                scores["_price_score_missing"] = True
        else:
            scores["price_raw"] = None
            scores["_price_score_missing"] = True

        # Spec score (raw: category-specific aggregate)
        specs = product.get("specs")
        if specs and isinstance(specs, dict):
            scores["spec_raw"] = self._score_specs(specs, category)
        else:
            scores["spec_raw"] = None
            scores["_spec_score_missing"] = True

        # Review score (raw: rating out of 5)
        rating = product.get("rating")
        if rating is not None:
            try:
                scores["review_raw"] = float(rating)
            except (ValueError, TypeError):
                scores["review_raw"] = None
                scores["_review_score_missing"] = True
        else:
            scores["review_raw"] = None
            scores["_review_score_missing"] = True

        # Reliability score (from fact_check)
        fact_check = product.get("fact_check")
        if fact_check and isinstance(fact_check, dict):
            scores["reliability_raw"] = self._score_reliability(fact_check)
        else:
            scores["reliability_raw"] = None
            scores["_reliability_score_missing"] = True

        # Popularity score (from review_count + source_ratings count)
        scores["popularity_raw"] = self._score_popularity(product)
        if scores["popularity_raw"] is None:
            scores["_popularity_score_missing"] = True

        return scores

    def _score_specs(self, specs: Dict[str, Any], category: str) -> float:
        """Score specs on a 0-1 scale based on category-specific logic."""
        schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
        schema_fields = CATEGORY_SPEC_SCHEMAS[schema_key]

        total_score = 0.0
        scored_fields = 0

        for field in schema_fields:
            value = specs.get(field)
            if not value or value == "N/A":
                continue

            numeric = self._extract_number(str(value))
            if numeric is not None:
                if field in HIGHER_IS_BETTER:
                    # Higher = better; raw numeric stored for normalization
                    total_score += numeric
                    scored_fields += 1
                elif field in LOWER_IS_BETTER:
                    # Lower = better; invert by using negative
                    total_score -= numeric
                    scored_fields += 1
                else:
                    # Neutral field — having data is slightly positive
                    total_score += 1
                    scored_fields += 1
            else:
                # Non-numeric field with data — counts as having info
                total_score += 1
                scored_fields += 1

        if scored_fields == 0:
            return 0.0

        # Penalty: if coverage below category threshold, penalize score
        total_fields = len(schema_fields)
        coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0
        min_coverage = CATEGORY_MIN_COVERAGE.get(schema_key, 0.3)
        if coverage_ratio < min_coverage:
            penalty_factor = 0.5 + coverage_ratio  # Range: 0.5 to 1.0
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

        # Weighted: verified=1.0, likely=0.7, unverified=0.3, flagged=0.0
        score = (verified * 1.0 + likely * 0.7 + unverified * 0.3 + flagged * 0.0) / total

        # Bonus for verified price
        if fact_check.get("price_verified"):
            score = min(1.0, score + 0.1)

        # Bonus for consistent review sentiment
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

        # Log scale for review count (1000 reviews = 1.0, 100 = 0.66, 10 = 0.33)
        import math
        if count > 0:
            count_score = min(1.0, math.log10(count) / 3.0)  # log10(1000) = 3
        else:
            count_score = 0.0

        # Source count bonus (more retailers = more popular)
        source_bonus = min(0.2, source_count * 0.05)

        return min(1.0, count_score + source_bonus)

    def _normalize_scores(
        self,
        raw_scores: List[Dict[str, Any]],
        products_data: List[Dict[str, Any]],
    ) -> List[Dict[str, float]]:
        """Normalize raw scores to 0-100 scale relative to each other."""
        # Detect price tiers for value score
        self._price_tiers = []
        for rs in raw_scores:
            price = rs.get("price_raw")
            if price is not None and price > 0:
                self._price_tiers.append(self._detect_price_tier(price))
            else:
                self._price_tiers.append("mid")  # default tier for missing price
        self._is_cross_tier_flag = self._is_cross_tier(self._price_tiers)

        normalized = []

        for i in range(len(raw_scores)):
            scores = {}

            # Price: lower is better, relative to competitors
            scores["price_score"] = self._normalize_price(
                raw_scores, i
            )

            # Spec: relative comparison
            scores["spec_score"] = self._normalize_dimension(
                raw_scores, i, "spec_raw", higher_better=True
            )

            # Review: rating/5 * 100
            scores["review_score"] = self._normalize_review(
                raw_scores, i
            )

            # Value: tier-aware scoring
            scores["value_score"] = self._compute_value_score(
                scores["spec_score"], scores["price_score"],
                self._price_tiers[i], self._is_cross_tier_flag
            )

            # Reliability: direct 0-1 → 0-100
            scores["reliability_score"] = self._normalize_direct(
                raw_scores, i, "reliability_raw"
            )

            # Popularity: direct 0-1 → 0-100
            scores["popularity_score"] = self._normalize_direct(
                raw_scores, i, "popularity_raw"
            )

            normalized.append(scores)

        return normalized

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

        # Lower price = better score
        # score = (1 - price/max_price) * 100
        # But we want minimum to still get a decent score, not 0
        min_price = min(prices)
        if max_price == min_price:
            return 75.0  # Both same price

        # Linear interpolation: cheapest = 100, most expensive = 30
        ratio = (current - min_price) / (max_price - min_price)  # 0 = cheapest, 1 = most expensive
        return round(100 - ratio * 70, 1)  # Range: 30-100

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
            return 70.0  # Tied

        if higher_better:
            ratio = (current - min_val) / (max_val - min_val)
        else:
            ratio = (max_val - current) / (max_val - min_val)

        # Map ratio 0-1 → score 30-100
        return round(30 + ratio * 70, 1)

    def _normalize_review(self, raw_scores: List[Dict], idx: int) -> float:
        """Normalize review score: rating/5 * 100."""
        rating = raw_scores[idx].get("review_raw")
        if rating is None:
            return MISSING_SCORE

        # Clamp to 1-5 range
        rating = max(1.0, min(5.0, rating))
        # Map 1-5 → 20-100
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
        scores = {}
        for i in range(count):
            scores[f"product_{i}"] = {
                "overall": MISSING_SCORE,
                "breakdown": {k: MISSING_SCORE for k in CATEGORY_WEIGHTS["other"]},
                "weights_used": dict(CATEGORY_WEIGHTS["other"]),
                "missing_data": list(CATEGORY_WEIGHTS["other"].keys()),
            }
        return {
            "scores": scores,
            "winner_index": 0,
            "win_margin": 0,
            "scoring_method": "default",
        }

    def compute_dimension_winners(self, scoring_result: Dict[str, Any], product_names: List[str]) -> Dict[str, Any]:
        """Compute per-dimension winner between two products."""
        scores = scoring_result.get("scores", {})
        if len(scores) < 2 or len(product_names) < 2:
            return {}

        dims = ["price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"]
        winners = {}
        b0 = scores.get("product_0", {}).get("breakdown", {})
        b1 = scores.get("product_1", {}).get("breakdown", {})

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

        # Sort both by margin descending
        winner_dims.sort(key=lambda x: x["margin"], reverse=True)
        loser_dims.sort(key=lambda x: x["margin"], reverse=True)

        # Pair them: strongest winner dim with strongest loser dim, etc.
        pairs = []
        for i in range(min(len(winner_dims), len(loser_dims), 3)):
            pairs.append({
                "winner_wins": winner_dims[i],
                "loser_wins": loser_dims[i],
            })

        # Sort by combined margin (most impactful first)
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
        """Assemble confidence indicators from existing product data.

        Returns dict with price, rating, specs, and overall confidence.
        """
        product = products[0] if products else {}
        price_data = product.get("price", {})
        fact_check = product.get("fact_check", {})

        # Price confidence
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

        # Rating confidence
        review_count = product.get("review_count") or 0
        rating_verified = product.get("rating_verified", False)
        rating_source = product.get("rating_source")
        rating_conf = {
            "review_count": review_count,
            "source": rating_source.get("name") if rating_source else None,
            "verified": rating_verified,
        }
        rating_strong = review_count >= 50 and rating_verified

        # Specs confidence
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

        # Overall
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
        """Apply deltas to weights with per-dimension capping and renormalization.

        Ensures no dimension shifts more than max_ratio * original[dim] from
        its original value, even after renormalization.
        """
        # Apply clamped deltas
        for dim in weights:
            if dim in deltas:
                max_shift = original[dim] * max_ratio
                clamped = max(-max_shift, min(max_shift, deltas[dim]))
                weights[dim] += clamped

        # Renormalize, then re-clamp iteratively (max 3 passes)
        for _ in range(3):
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}
            # Check if any dimension exceeds cap after renormalization
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

        # Final renormalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def apply_behavioral_adjustments(
        self,
        weights: Dict[str, float],
        behavior_profile: Dict[str, Any],
    ) -> Dict[str, float]:
        """Apply behavioral profile adjustments to weights (capped at +/-10%)."""
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
        """Apply in-session signal adjustments to weights (capped at +/-5%)."""
        dwell = session_signals.get("tab_dwell_ms", {})
        if not dwell:
            return weights

        tab_dim_map = {"specs": "spec_score", "reviews": "review_score", "overview": "price_score"}
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
        # Match numbers like 4422, 6.1, 3,274, 128
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

        for i, name in enumerate(product_names):
            key = f"product_{i}"
            if key not in scores:
                continue
            ps = scores[key]
            overall = ps["overall"]
            breakdown = ps["breakdown"]
            tier = scoring_result.get("price_tiers", {}).get(name, "unknown")
            lines.append(f"  {name}: {overall}/100 overall (price tier: {tier})")
            dims = []
            for dim in ["price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"]:
                dims.append(f"{dim.replace('_score', '')}={breakdown.get(dim, 50)}")
            lines.append(f"    Breakdown: {', '.join(dims)}")

        winner_idx = scoring_result.get("winner_index", 0)
        margin = scoring_result.get("win_margin", 0)
        if len(product_names) >= 2:
            lines.append(f"  Score winner: {product_names[winner_idx]} by {margin} points")

        # Add dimension winners
        dim_winners = scoring_result.get("dimension_winners", {})
        if dim_winners:
            dim_parts = []
            for dim in ["price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"]:
                w = dim_winners.get(dim, {})
                winner = w.get("winner", "N/A")
                dim_parts.append(f"{dim.replace('_score', '')}={winner}")
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

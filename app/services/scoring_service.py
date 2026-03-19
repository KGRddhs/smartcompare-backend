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

# Default scoring weights (sum to 1.0)
DEFAULT_WEIGHTS = {
    "price_score": 0.25,
    "spec_score": 0.25,
    "review_score": 0.20,
    "value_score": 0.15,
    "reliability_score": 0.10,
    "popularity_score": 0.05,
}

# Priority-based weight adjustments (deltas applied to default weights)
PRIORITY_ADJUSTMENTS = {
    "price": {"price_score": 0.15, "spec_score": -0.10, "value_score": 0.05},
    "quality": {"spec_score": 0.15, "review_score": 0.05, "price_score": -0.15},
    "brand_reputation": {"reliability_score": 0.10, "popularity_score": 0.10, "value_score": -0.15},
    "durability": {"spec_score": 0.10, "reliability_score": 0.10, "price_score": -0.10, "value_score": -0.05},
    "latest_features": {"spec_score": 0.15, "price_score": -0.10, "popularity_score": 0.05},
    "ease_of_use": {"review_score": 0.10, "spec_score": -0.05, "popularity_score": 0.05},
    "eco_friendly": {"reliability_score": 0.05, "review_score": 0.05, "price_score": -0.05},
    "health_safety": {"reliability_score": 0.10, "review_score": 0.05, "price_score": -0.10},
}

BUDGET_ADJUSTMENTS = {
    "budget": {"price_score": 0.10, "value_score": 0.10, "spec_score": -0.10},
    "mid": {},  # No adjustment for mid-range
    "premium": {"spec_score": 0.10, "review_score": 0.05, "price_score": -0.10},
}

# Maximum allowed shift ratio from default weight (±30%)
MAX_WEIGHT_SHIFT_RATIO = 0.30

# Spec fields where higher is better (electronics-focused)
HIGHER_IS_BETTER = {
    "ram", "storage", "battery", "rear_camera", "front_camera",
    "count", "dosage", "serving_size",
    "nutrition_protein", "shelf_life",
    "shade_range", "spf", "volume", "longevity",
}

# Spec fields where lower is better
LOWER_IS_BETTER = {
    "weight",  # Lighter electronics = better (usually)
    "nutrition_calories", "nutrition_fat", "nutrition_carbs",
}

# Default score for missing data
MISSING_SCORE = 50


class ScoringService:
    """Deterministic scoring engine for product comparisons."""

    def compute_scores(
        self,
        products_data: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute scores for a list of products.

        Args:
            products_data: List of product dicts (from _fetch_product_data).
                Each has: specs, price, reviews, rating, review_count,
                fact_check, rating_verified, rating_source, etc.
            preferences: Optional user preferences dict with:
                priorities (list), budget (str), lifestyle (list), brand_attitude (str)

        Returns:
            Dict with per-product scores, winner, and metadata.
        """
        if not products_data or len(products_data) < 2:
            return self._empty_result(len(products_data))

        weights = self._compute_weights(preferences)
        category = products_data[0].get("category", "other")

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
            for dim in DEFAULT_WEIGHTS:
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

        scoring_method = "personalized" if preferences else "default"

        return {
            "scores": result_products,
            "winner_index": winner_index,
            "win_margin": win_margin,
            "scoring_method": scoring_method,
        }

    def _compute_weights(self, preferences: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Compute scoring weights from user preferences."""
        weights = dict(DEFAULT_WEIGHTS)

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

        # Cap each dimension's shift to ±30% of its default weight
        for dim in weights:
            default_val = DEFAULT_WEIGHTS.get(dim, 0)
            max_val = default_val * (1 + MAX_WEIGHT_SHIFT_RATIO)
            min_val = default_val * (1 - MAX_WEIGHT_SHIFT_RATIO)
            weights[dim] = max(0.0, min(max_val, max(min_val, weights[dim])))

        # Renormalize to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        else:
            # Fallback: equal weights
            n = len(weights)
            weights = {k: 1.0 / n for k in weights}

        return weights

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

        # Penalty: if less than half of schema fields have data, penalize score
        total_fields = len(schema_fields)
        coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0
        if coverage_ratio < 0.5:
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

            # Value: spec_score / price (higher spec per dollar = better)
            scores["value_score"] = self._compute_value_score(
                scores["spec_score"], scores["price_score"]
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

    def _compute_value_score(self, spec_score: float, price_score: float) -> float:
        """Value = combination of spec quality and price affordability."""
        if spec_score == MISSING_SCORE and price_score == MISSING_SCORE:
            return MISSING_SCORE

        # Value is the average of spec and price scores (both already 0-100)
        # A product with great specs AND great price = great value
        return round((spec_score + price_score) / 2.0, 1)

    def _empty_result(self, count: int) -> Dict[str, Any]:
        """Return empty scoring result for edge cases."""
        scores = {}
        for i in range(count):
            scores[f"product_{i}"] = {
                "overall": MISSING_SCORE,
                "breakdown": {k: MISSING_SCORE for k in DEFAULT_WEIGHTS},
                "weights_used": dict(DEFAULT_WEIGHTS),
                "missing_data": list(DEFAULT_WEIGHTS.keys()),
            }
        return {
            "scores": scores,
            "winner_index": 0,
            "win_margin": 0,
            "scoring_method": "default",
        }

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
            lines.append(f"  {name}: {overall}/100 overall")
            dims = []
            for dim in ["price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"]:
                dims.append(f"{dim.replace('_score', '')}={breakdown.get(dim, 50)}")
            lines.append(f"    Breakdown: {', '.join(dims)}")

        winner_idx = scoring_result.get("winner_index", 0)
        margin = scoring_result.get("win_margin", 0)
        if len(product_names) >= 2:
            lines.append(f"  Score winner: {product_names[winner_idx]} by {margin} points")

        return "\n".join(lines)


# Module-level singleton
_scoring_service = None


def get_scoring_service() -> ScoringService:
    """Get or create the scoring service singleton."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service

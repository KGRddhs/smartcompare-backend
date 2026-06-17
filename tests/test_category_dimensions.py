"""Tests for category-specific scoring dimensions."""
import pytest
from app.services.scoring_service import (
    CATEGORY_DIMENSIONS,
    CATEGORY_DIMENSION_WEIGHTS,
    CATEGORY_PRIORITY_ADJUSTMENTS,
    DIMENSION_DISPLAY_NAMES,
    HIGHER_IS_BETTER_BY_CATEGORY,
    LOWER_IS_BETTER_BY_CATEGORY,
)


class TestCategoryDimensions:
    """Verify all 9 categories have valid dimension configs."""

    EXPECTED_CATEGORIES = [
        "electronics", "grocery", "supplements", "makeup",
        "skincare", "haircare", "fragrances", "fashion", "other",
    ]

    def test_all_categories_have_dimensions(self):
        for cat in self.EXPECTED_CATEGORIES:
            assert cat in CATEGORY_DIMENSIONS, f"Missing dimensions for {cat}"
            assert len(CATEGORY_DIMENSIONS[cat]) == 6, f"{cat} must have exactly 6 dimensions"

    def test_all_categories_have_weights(self):
        for cat in self.EXPECTED_CATEGORIES:
            assert cat in CATEGORY_DIMENSION_WEIGHTS, f"Missing weights for {cat}"
            weights = CATEGORY_DIMENSION_WEIGHTS[cat]
            assert len(weights) == 6, f"{cat} weights must have 6 entries"
            assert abs(sum(weights.values()) - 1.0) < 0.001, f"{cat} weights must sum to 1.0"

    def test_weight_keys_match_dimensions(self):
        for cat in self.EXPECTED_CATEGORIES:
            dim_keys = set(CATEGORY_DIMENSIONS[cat])
            weight_keys = set(CATEGORY_DIMENSION_WEIGHTS[cat].keys())
            assert dim_keys == weight_keys, f"{cat}: dimension keys {dim_keys} != weight keys {weight_keys}"

    def test_electronics_dimensions(self):
        dims = CATEGORY_DIMENSIONS["electronics"]
        assert "performance_score" in dims
        assert "value_score" in dims
        assert "build_quality_score" in dims
        assert "feature_score" in dims
        assert "ecosystem_score" in dims
        assert "futureproof_score" in dims

    def test_makeup_dimensions(self):
        dims = CATEGORY_DIMENSIONS["makeup"]
        assert "shade_score" in dims
        assert "longevity_score" in dims
        assert "skin_compat_score" in dims
        assert "finish_score" in dims

    def test_fragrances_dimensions(self):
        dims = CATEGORY_DIMENSIONS["fragrances"]
        assert "character_score" in dims
        assert "longevity_score" in dims
        assert "projection_score" in dims
        assert "versatility_score" in dims

    def test_supplements_dimensions(self):
        dims = CATEGORY_DIMENSIONS["supplements"]
        assert "efficacy_score" in dims
        assert "safety_score" in dims
        assert "dosage_score" in dims

    def test_fashion_dimensions(self):
        dims = CATEGORY_DIMENSIONS["fashion"]
        assert "craft_score" in dims
        assert "fit_score" in dims
        assert "style_score" in dims
        assert "durability_score" in dims
        assert "heritage_score" in dims
        assert "cpw_score" in dims

    def test_grocery_dimensions(self):
        dims = CATEGORY_DIMENSIONS["grocery"]
        assert "nutrition_score" in dims
        assert "ingredient_score" in dims
        assert "taste_score" in dims

    def test_skincare_dimensions(self):
        dims = CATEGORY_DIMENSIONS["skincare"]
        assert "actives_score" in dims
        assert "evidence_score" in dims
        assert "skin_compat_score" in dims

    def test_haircare_dimensions(self):
        dims = CATEGORY_DIMENSIONS["haircare"]
        assert "hair_match_score" in dims
        assert "results_score" in dims
        assert "scent_score" in dims

    def test_other_dimensions(self):
        dims = CATEGORY_DIMENSIONS["other"]
        assert "function_score" in dims
        assert "value_score" in dims
        assert "review_score" in dims

    def test_display_names_cover_all_dimensions(self):
        all_dims = set()
        for cat in self.EXPECTED_CATEGORIES:
            all_dims.update(CATEGORY_DIMENSIONS[cat])
        for dim in all_dims:
            assert dim in DIMENSION_DISPLAY_NAMES, f"Missing display name for {dim}"

    def test_no_dimension_weight_is_zero(self):
        """Fairness: no dimension should ever be zeroed out."""
        for cat in self.EXPECTED_CATEGORIES:
            for dim, weight in CATEGORY_DIMENSION_WEIGHTS[cat].items():
                assert weight > 0, f"{cat}.{dim} weight must be > 0 (fairness rule)"

    def test_priority_adjustments_exist_per_category(self):
        for cat in self.EXPECTED_CATEGORIES:
            assert cat in CATEGORY_PRIORITY_ADJUSTMENTS, f"Missing priority adjustments for {cat}"
            adj = CATEGORY_PRIORITY_ADJUSTMENTS[cat]
            # At minimum: price, quality, health_safety should have entries
            assert "price" in adj or "quality" in adj, f"{cat} must have at least price or quality adjustments"

    def test_priority_adjustments_reference_valid_dimensions(self):
        for cat in self.EXPECTED_CATEGORIES:
            valid_dims = set(CATEGORY_DIMENSIONS[cat])
            for priority, deltas in CATEGORY_PRIORITY_ADJUSTMENTS[cat].items():
                for dim_key in deltas:
                    assert dim_key in valid_dims, f"{cat}.{priority} references invalid dimension {dim_key}"

    def test_higher_is_better_by_category_exists(self):
        for cat in self.EXPECTED_CATEGORIES:
            assert cat in HIGHER_IS_BETTER_BY_CATEGORY, f"Missing HIGHER_IS_BETTER for {cat}"

    def test_lower_is_better_by_category_exists(self):
        for cat in self.EXPECTED_CATEGORIES:
            assert cat in LOWER_IS_BETTER_BY_CATEGORY, f"Missing LOWER_IS_BETTER for {cat}"

    def test_backward_compat_alias(self):
        """CATEGORY_WEIGHTS should be an alias for CATEGORY_DIMENSION_WEIGHTS."""
        from app.services.scoring_service import CATEGORY_WEIGHTS
        assert CATEGORY_WEIGHTS is CATEGORY_DIMENSION_WEIGHTS

    # Faithful-Results Phase 3.3 — the explicit no-cross-category-leak invariant.
    # The keystone (canonicalize_category) routes "Fragrances"→"fragrances" so
    # each category scores on its OWN dims; this pins that electronics-only dims
    # never leak into a non-electronics category (the Thrust-C "Build dim on a
    # fragrance" class of bug).
    _ELECTRONICS_ONLY_DIMS = {
        "performance_score", "build_quality_score", "feature_score",
        "ecosystem_score", "futureproof_score",
    }

    def test_no_electronics_only_dim_leaks_to_other_categories(self):
        for cat in self.EXPECTED_CATEGORIES:
            if cat == "electronics":
                continue
            leaked = set(CATEGORY_DIMENSIONS[cat]) & self._ELECTRONICS_ONLY_DIMS
            assert not leaked, f"{cat} leaks electronics-only dims: {leaked}"

    def test_fragrance_scores_on_scent_dims_not_build(self):
        dims = CATEGORY_DIMENSIONS["fragrances"]
        assert "character_score" in dims and "longevity_score" in dims and "projection_score" in dims
        assert "build_quality_score" not in dims and "feature_score" not in dims


from app.services.scoring_service import ScoringService


class TestCategoryScoring:
    """Test that scoring uses category-specific dimensions."""

    def _make_product(self, category, price=50, rating=4.0, review_count=100, specs=None):
        return {
            "category": category,
            "brand": "TestBrand",
            "name": "TestProduct",
            "price": {"amount": price, "currency": "BHD"},
            "rating": rating,
            "review_count": review_count,
            "specs": specs or {},
            "reviews": {"source_ratings": [{"rating": rating}]},
            "fact_check": {"specs_verified": 5, "specs_likely": 2, "specs_flagged": 0, "specs_unverified": 0, "price_verified": True, "review_sentiment_consistent": True},
        }

    def test_electronics_returns_electronics_dimensions(self):
        svc = ScoringService()
        products = [
            self._make_product("electronics", price=100, rating=4.5, specs={"processor": "A17", "ram": "8 GB", "battery": "4422 mAh"}),
            self._make_product("electronics", price=80, rating=4.0, specs={"processor": "Snapdragon 8", "ram": "6 GB", "battery": "3500 mAh"}),
        ]
        result = svc.compute_scores(products)
        breakdown = result["scores"]["product_0"]["breakdown"]
        assert "performance_score" in breakdown
        assert "value_score" in breakdown
        assert "build_quality_score" in breakdown
        assert "price_score" not in breakdown  # old dimension gone

    def test_makeup_returns_makeup_dimensions(self):
        svc = ScoringService()
        products = [
            self._make_product("makeup", price=30, rating=4.2, specs={"shade_range": "40 shades", "finish": "matte"}),
            self._make_product("makeup", price=25, rating=4.0, specs={"shade_range": "24 shades", "finish": "dewy"}),
        ]
        result = svc.compute_scores(products)
        breakdown = result["scores"]["product_0"]["breakdown"]
        assert "shade_score" in breakdown
        assert "longevity_score" in breakdown
        assert "skin_compat_score" in breakdown

    def test_fragrances_returns_fragrance_dimensions(self):
        svc = ScoringService()
        products = [
            self._make_product("fragrances", price=120, rating=4.5, specs={"longevity": "8 hours", "sillage": "strong"}),
            self._make_product("fragrances", price=90, rating=4.0, specs={"longevity": "4 hours", "sillage": "moderate"}),
        ]
        result = svc.compute_scores(products)
        breakdown = result["scores"]["product_0"]["breakdown"]
        assert "character_score" in breakdown
        assert "longevity_score" in breakdown
        assert "projection_score" in breakdown

    def test_personalization_uses_category_priority_adjustments(self):
        svc = ScoringService()
        products = [
            self._make_product("electronics", price=100, specs={"processor": "A17", "ram": "8 GB"}),
            self._make_product("electronics", price=80, specs={"processor": "SD8", "ram": "6 GB"}),
        ]
        # Quality priority in electronics should boost performance_score
        prefs = {"priorities": ["quality"], "budget": "premium"}
        result = svc.compute_scores(products, preferences=prefs)
        weights = result["scores"]["product_0"]["weights_used"]
        default_perf = 0.25  # from CATEGORY_DIMENSION_WEIGHTS
        assert weights["performance_score"] >= default_perf, "quality priority should boost performance"

    def test_scoring_deterministic(self):
        svc = ScoringService()
        products = [
            self._make_product("skincare", price=40, rating=4.3, specs={"active_ingredient": "retinol 0.3%", "skin_type": "all"}),
            self._make_product("skincare", price=35, rating=4.1, specs={"active_ingredient": "niacinamide 5%", "skin_type": "sensitive"}),
        ]
        r1 = svc.compute_scores(products)
        r2 = svc.compute_scores(products)
        assert r1["scores"]["product_0"]["overall"] == r2["scores"]["product_0"]["overall"]

    def test_dimension_winners_uses_new_keys(self):
        svc = ScoringService()
        products = [
            self._make_product("fashion", price=200, rating=4.5, specs={"material": "full-grain leather", "craftsmanship": "hand-stitched"}),
            self._make_product("fashion", price=80, rating=4.0, specs={"material": "bonded leather", "craftsmanship": "machine-made"}),
        ]
        result = svc.compute_scores(products)
        dim_winners = result["dimension_winners"]
        assert "craft_score" in dim_winners
        assert "fit_score" in dim_winners
        assert "price_score" not in dim_winners  # old key gone

    def test_build_scores_summary_uses_new_keys(self):
        svc = ScoringService()
        products = [
            self._make_product("supplements", price=25, rating=4.5, specs={"dosage": "500mg", "form": "capsule"}),
            self._make_product("supplements", price=20, rating=4.0, specs={"dosage": "250mg", "form": "gummy"}),
        ]
        result = svc.compute_scores(products)
        summary = svc.build_scores_summary(result, ["Product A", "Product B"])
        assert "efficacy" in summary or "safety" in summary
        assert "price=" not in summary  # old format gone

    def test_category_weights_returned_in_result(self):
        svc = ScoringService()
        products = [
            self._make_product("grocery", price=5, rating=4.0),
            self._make_product("grocery", price=4, rating=3.8),
        ]
        result = svc.compute_scores(products)
        assert "category_weights" in result
        assert "nutrition_score" in result["category_weights"]

    def test_other_category_fallback(self):
        svc = ScoringService()
        products = [
            self._make_product("unknown_xyz", price=50, rating=4.0),
            self._make_product("unknown_xyz", price=40, rating=3.8),
        ]
        result = svc.compute_scores(products)
        breakdown = result["scores"]["product_0"]["breakdown"]
        assert "function_score" in breakdown  # falls back to "other" dims

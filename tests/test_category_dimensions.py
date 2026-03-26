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

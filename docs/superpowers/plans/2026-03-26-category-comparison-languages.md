# Category Comparison Languages + Backend Production Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the universal 6-dimension scoring with category-specific dimensions and prompt personalities so each product category gets a comparison tailored to what actually matters in that domain, plus add missing App Store compliance endpoints.

**Architecture:** The scoring engine (`scoring_service.py`) gets new `CATEGORY_DIMENSIONS` replacing the old universal dims. Prompt personalities (`extraction_service.py`) inject category-specific reasoning instructions into the verdict prompt. A trust validation layer cross-checks GPT claims against scores post-generation. Backend production endpoints (account deletion, legal, version check) are added to new/existing route files.

**Tech Stack:** Python 3.12, FastAPI, GPT-4o-mini (existing), Supabase, pytest

**Spec:** `docs/superpowers/specs/2026-03-26-category-comparison-languages-design.md`
**Rollback:** `docs/ROLLBACK_SCORING_V1.md`

**Team:** 4 Opus agents (Backend-Scoring, Backend-Prompts, Backend-Production, Test-QA)
- All features 100% complete before disassembly
- Each member QAs another's work; subpar work sent back
- Idle members write red-green tests for 80%+ coverage or wait for QA
- Cross-QA assignments: Scoring↔Prompts, Production↔Test-QA

---

## File Structure

### New Files
| File | Responsibility | Agent |
|------|---------------|-------|
| `app/services/trust_validation_service.py` | Post-generation cross-check of GPT claims vs scores | Backend-Prompts |
| `app/services/prompt_personalities.py` | `CATEGORY_PROMPT_PERSONALITIES` dict + `build_personality_prompt()` | Backend-Prompts |
| `app/api/legal_routes.py` | Privacy policy + Terms of Service endpoints | Backend-Production |
| `app/api/version_routes.py` | App version check endpoint | Backend-Production |
| `app/legal/privacy_policy.md` | Privacy policy content | Backend-Production |
| `app/legal/terms_of_service.md` | Terms of service content | Backend-Production |
| `tests/test_category_dimensions.py` | Tests for new scoring dimensions | Test-QA |
| `tests/test_prompt_personalities.py` | Tests for prompt personality injection | Test-QA |
| `tests/test_trust_validation.py` | Tests for trust validation layer | Test-QA |
| `tests/test_account_deletion.py` | Tests for account deletion cascade | Test-QA |
| `tests/test_legal_routes.py` | Tests for legal endpoints | Test-QA |
| `tests/test_version_routes.py` | Tests for version check endpoint | Test-QA |

### Modified Files
| File | Changes | Agent |
|------|---------|-------|
| `app/services/scoring_service.py` | Replace `CATEGORY_WEIGHTS` with `CATEGORY_DIMENSIONS`, new `_compute_raw_scores()` per category, new `CATEGORY_PRIORITY_ADJUSTMENTS` | Backend-Scoring |
| `app/services/extraction_service.py` | Inject personality prompt into `COMPARISON_PROMPT`, pass category to `generate_comparison()` | Backend-Prompts |
| `app/services/structured_comparison_service.py` | Pass category to scoring + verdict, call trust validation post-generation | Backend-Prompts |
| `app/api/auth_routes.py` | Add `DELETE /api/v1/auth/account`, password strength validators | Backend-Production |
| `app/services/auth_service.py` | Add `delete_user_account()` cascade function | Backend-Production |
| `app/services/database_service.py` | Replace `print()` with `logger`, add cascade delete helpers | Backend-Production |
| `app/main.py` | Register legal_routes + version_routes routers | Backend-Production |
| `tests/test_scoring_service.py` | Update for new dimension keys | Backend-Scoring |

### Deleted Files
| File | Reason | Agent |
|------|--------|-------|
| `app/services/comparison_service.py` | Dead code (289 lines, never imported by deployed app) | Backend-Production |

---

## Task 1: New Scoring Dimensions Config (Backend-Scoring)

**Files:**
- Modify: `app/services/scoring_service.py:15-96` (constants section)
- Test: `tests/test_category_dimensions.py` (create)

- [ ] **Step 1: Write failing tests for new dimension config**

Create `tests/test_category_dimensions.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_category_dimensions.py -v`
Expected: FAIL — `CATEGORY_DIMENSIONS` not defined yet.

- [ ] **Step 3: Implement new dimension constants in scoring_service.py**

Replace the `CATEGORY_WEIGHTS`, `PRIORITY_ADJUSTMENTS`, `BUDGET_ADJUSTMENTS`, `HIGHER_IS_BETTER`, `LOWER_IS_BETTER`, and `DIMENSION_DISPLAY_NAMES` constants (lines 15-96) with the new category-specific dimensions. Keep `MAX_WEIGHT_SHIFT_RATIO`, `MAX_BEHAVIORAL_SHIFT_RATIO`, `MAX_SESSION_SHIFT_RATIO`, `MISSING_SCORE`, `PRICE_TIERS`, `TIER_EXPECTATIONS`, `CATEGORY_MIN_COVERAGE` unchanged.

The new constants are defined in full in the spec at section A1. Key structure:

```python
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

# Per-category priority adjustments (8 priorities × 9 categories)
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

# Budget adjustments (same keys as category dimension weights)
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

# Display names for all dimensions across all categories
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

# Spec fields higher/lower-is-better — organized by category for the new dimension computation
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_category_dimensions.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring_service.py tests/test_category_dimensions.py
git commit -m "feat: add category-specific scoring dimensions config (9 categories × 6 dims)"
```

---

## Task 2: Scoring Engine Core Rewrite (Backend-Scoring)

**Files:**
- Modify: `app/services/scoring_service.py:99-892` (ScoringService class)
- Test: `tests/test_category_dimensions.py` (extend)

- [ ] **Step 1: Write failing tests for new compute_scores behavior**

Add to `tests/test_category_dimensions.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_category_dimensions.py::TestCategoryScoring -v`
Expected: FAIL — old scoring returns `price_score` etc.

- [ ] **Step 3: Rewrite ScoringService methods**

Update the `ScoringService` class in `scoring_service.py`:

1. **`_compute_weights()`**: Use `CATEGORY_DIMENSION_WEIGHTS[category]` as base, apply `CATEGORY_PRIORITY_ADJUSTMENTS[category]` per priority, apply `CATEGORY_BUDGET_ADJUSTMENTS[category]` per budget. Same capping logic (±30%).

2. **`_compute_raw_scores()`**: Dispatch to category-specific raw score computation. Each category computes its 6 raw dimension scores from product data. Use a `_CATEGORY_RAW_SCORERS` dispatch dict that maps category → scorer function. Each scorer extracts what it needs from `product.specs`, `product.price`, `product.reviews`, `product.fact_check`, `product.rating`, `product.review_count`.

3. **`_normalize_scores()`**: Normalize each category's dimensions (same 0-100 relative logic, just different keys).

4. **`compute_dimension_winners()`**: Use `CATEGORY_DIMENSIONS[category]` instead of hardcoded 6-dim list.

5. **`build_scores_summary()`**: Use `CATEGORY_DIMENSIONS[category]` and `DIMENSION_DISPLAY_NAMES` for the text summary.

6. **`apply_behavioral_adjustments()` and `apply_session_signals()`**: Same logic but operate on whichever dimension keys are present in the weights dict.

Key implementation detail: The raw scorers need to map category-specific dimension keys to data extraction logic. For example:
- `performance_score` (electronics) → extract numeric from `specs.processor`, `specs.ram`, `specs.battery`
- `shade_score` (makeup) → extract numeric from `specs.shade_range`
- `character_score` (fragrances) → presence/quality of `specs.notes_top`, `specs.notes_heart`, `specs.notes_base`
- `longevity_score` (fragrances) → extract numeric from `specs.longevity`

Dimensions that depend on reviews (e.g., `taste_score`, `finish_score`, `sensory_score`) use `product.rating` and `product.review_count` as proxy since we don't have granular review dimension scores — the GPT prompt personality will handle the qualitative differentiation.

- [ ] **Step 4: Run new + existing tests**

Run: `python -m pytest tests/test_category_dimensions.py tests/test_scoring_service.py -v`
Expected: New tests PASS. Existing `test_scoring_service.py` will FAIL due to old dimension keys.

- [ ] **Step 5: Update existing scoring tests**

Update `tests/test_scoring_service.py` to use new dimension keys. All references to `price_score`, `spec_score`, `review_score`, `value_score`, `reliability_score`, `popularity_score` must be updated to the category-specific equivalents. The test structure stays the same — just the key names change.

- [ ] **Step 6: Run full scoring test suite**

Run: `python -m pytest tests/test_scoring_service.py tests/test_category_dimensions.py -v`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/scoring_service.py tests/test_category_dimensions.py tests/test_scoring_service.py
git commit -m "feat: rewrite scoring engine with category-specific dimensions (9×6)"
```

---

## Task 3: Prompt Personalities (Backend-Prompts)

**Files:**
- Create: `app/services/prompt_personalities.py`
- Modify: `app/services/extraction_service.py:355-409` (COMPARISON_PROMPT)
- Modify: `app/services/extraction_service.py:714-790` (generate_comparison function)
- Test: `tests/test_prompt_personalities.py` (create)

- [ ] **Step 1: Write failing tests for prompt personalities**

Create `tests/test_prompt_personalities.py`:

```python
"""Tests for category-specific prompt personalities."""
import pytest
from app.services.prompt_personalities import (
    CATEGORY_PROMPT_PERSONALITIES,
    build_personality_prompt,
)


EXPECTED_CATEGORIES = [
    "electronics", "grocery", "supplements", "makeup",
    "skincare", "haircare", "fragrances", "fashion", "other",
]

REQUIRED_KEYS = [
    "reasoning_style", "evidence_language", "risk_framing",
    "comparison_voice", "context_inference",
]


class TestPromptPersonalities:

    def test_all_categories_have_personalities(self):
        for cat in EXPECTED_CATEGORIES:
            assert cat in CATEGORY_PROMPT_PERSONALITIES, f"Missing personality for {cat}"

    def test_all_personalities_have_required_keys(self):
        for cat in EXPECTED_CATEGORIES:
            personality = CATEGORY_PROMPT_PERSONALITIES[cat]
            for key in REQUIRED_KEYS:
                assert key in personality, f"{cat} missing key: {key}"
                assert len(personality[key]) > 20, f"{cat}.{key} is too short"

    def test_build_personality_prompt_returns_string(self):
        result = build_personality_prompt("electronics")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_build_personality_prompt_contains_category_content(self):
        result = build_personality_prompt("fragrances")
        assert "scent" in result.lower() or "longevity" in result.lower()
        assert "fragrance" in result.lower() or "oud" in result.lower()

    def test_build_personality_prompt_unknown_category_falls_back(self):
        result = build_personality_prompt("unknown_category")
        # Should fall back to "other"
        assert isinstance(result, str)
        assert len(result) > 50

    def test_electronics_personality_mentions_numbers(self):
        p = CATEGORY_PROMPT_PERSONALITIES["electronics"]
        assert "number" in p["evidence_language"].lower() or "percent" in p["evidence_language"].lower()

    def test_makeup_personality_mentions_experience(self):
        p = CATEGORY_PROMPT_PERSONALITIES["makeup"]
        assert "wear" in p["reasoning_style"].lower() or "experience" in p["reasoning_style"].lower()

    def test_supplements_personality_mentions_safety(self):
        p = CATEGORY_PROMPT_PERSONALITIES["supplements"]
        assert "safety" in p["risk_framing"].lower() or "contaminant" in p["risk_framing"].lower()

    def test_personality_prompt_includes_trust_rules(self):
        """All personality prompts must include universal trust rules."""
        for cat in EXPECTED_CATEGORIES:
            result = build_personality_prompt(cat)
            assert "contradict" in result.lower() or "conflict" in result.lower(), f"{cat} missing trust rules"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_prompt_personalities.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create prompt_personalities.py**

Create `app/services/prompt_personalities.py` with the full `CATEGORY_PROMPT_PERSONALITIES` dict from the spec (section A3) and the `build_personality_prompt()` function:

```python
"""Category-specific prompt personalities for product comparisons."""

CATEGORY_PROMPT_PERSONALITIES = {
    # ... full dict from spec section A3 (all 9 categories)
}

UNIVERSAL_TRUST_RULES = """
TRUST RULES (MANDATORY — apply to ALL comparisons):
- NO information conflicts: pros must not contradict cons for the same product
- NO vague language: "somewhat better" is NEVER acceptable — quantify or explain specifically
- NO overconfidence: if data is thin or scores are close (<5 point gap), say "marginally" or "slightly"
- NO bias: do not favor expensive or cheap — favor what fits the user's stated needs
- ALWAYS explain reasoning: never just state a winner without evidence
- CITE the data: every claim must reference a specific spec, rating, or review finding
- If scores disagree with your intuition, explain why (do not silently ignore scores)
"""


def build_personality_prompt(category: str) -> str:
    """Build the category-specific personality section for the comparison prompt."""
    personality = CATEGORY_PROMPT_PERSONALITIES.get(
        category, CATEGORY_PROMPT_PERSONALITIES["other"]
    )
    return f"""
## Comparison Personality (adapt your language and reasoning to this category)
- Reasoning approach: {personality['reasoning_style']}
- Evidence style: {personality['evidence_language']}
- Risk awareness: {personality['risk_framing']}
- Voice: {personality['comparison_voice']}
- Context inference: {personality['context_inference']}

{UNIVERSAL_TRUST_RULES}
"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_prompt_personalities.py -v`
Expected: All PASS.

- [ ] **Step 5: Inject personality into generate_comparison**

Modify `extraction_service.py`:
1. Add import: `from app.services.prompt_personalities import build_personality_prompt`
2. Update `generate_comparison()` signature to accept `category: str = "other"` parameter
3. After assembling the base prompt, append `build_personality_prompt(category)` before the scoring context

In `generate_comparison()` around line 731:
```python
# After base prompt assembly, before scoring context:
personality_section = build_personality_prompt(category)
prompt += personality_section
```

- [ ] **Step 6: Pass category from structured_comparison_service**

In `structured_comparison_service.py`, update both calls to `generate_comparison()` (around lines 312 and 675) to pass `category=detected_category`:

```python
comparison, usage = await generate_comparison(
    product_data[0],
    product_data[1],
    region,
    concern,
    user_preferences=user_preferences,
    scores_summary=scores_summary,
    category=detected_category,  # NEW
)
```

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_prompt_personalities.py tests/test_review_prompt_quality.py -v`
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add app/services/prompt_personalities.py app/services/extraction_service.py app/services/structured_comparison_service.py tests/test_prompt_personalities.py
git commit -m "feat: add category-specific prompt personalities for verdict generation"
```

---

## Task 4: Trust Validation Layer (Backend-Prompts)

**Files:**
- Create: `app/services/trust_validation_service.py`
- Modify: `app/services/structured_comparison_service.py` (call validation after verdict)
- Test: `tests/test_trust_validation.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/test_trust_validation.py`:

```python
"""Tests for trust validation — cross-checking GPT claims against scores."""
import pytest
from app.services.trust_validation_service import validate_verdict


class TestVerdictValidation:

    def _make_scoring_result(self, p0_breakdown, p1_breakdown, winner_index=0):
        return {
            "scores": {
                "product_0": {"overall": sum(p0_breakdown.values()) / len(p0_breakdown), "breakdown": p0_breakdown},
                "product_1": {"overall": sum(p1_breakdown.values()) / len(p1_breakdown), "breakdown": p1_breakdown},
            },
            "winner_index": winner_index,
            "dimension_winners": {},
        }

    def test_winner_aligned_when_matching(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70},
            {"performance_score": 60, "value_score": 65},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["winner_aligned"] is True

    def test_winner_misaligned_detected(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70},
            {"performance_score": 60, "value_score": 65},
            winner_index=0,
        )
        verdict = {"winner_index": 1}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["winner_aligned"] is False

    def test_claims_validated_count(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70, "build_quality_score": 75, "feature_score": 60, "ecosystem_score": 50, "futureproof_score": 55},
            {"performance_score": 60, "value_score": 65, "build_quality_score": 70, "feature_score": 55, "ecosystem_score": 45, "futureproof_score": 50},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["claims_validated"] >= 0
        assert result["claims_flagged"] >= 0

    def test_returns_expected_structure(self):
        scoring = self._make_scoring_result(
            {"function_score": 70, "build_score": 60, "review_score": 65, "value_score": 70, "reliability_score": 55, "feature_match_score": 60},
            {"function_score": 65, "build_score": 55, "review_score": 60, "value_score": 65, "reliability_score": 50, "feature_match_score": 55},
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "other")
        assert "winner_aligned" in result
        assert "claims_validated" in result
        assert "claims_softened" in result
        assert "claims_flagged" in result

    def test_empty_scoring_handles_gracefully(self):
        result = validate_verdict({"winner_index": 0}, {}, "electronics")
        assert result["winner_aligned"] is True  # no data to contradict
        assert result["claims_validated"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_trust_validation.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement trust_validation_service.py**

Create `app/services/trust_validation_service.py`:

```python
"""Trust validation — cross-check GPT verdict claims against deterministic scores."""
import logging
from typing import Dict, Any

from app.services.scoring_service import CATEGORY_DIMENSIONS, MISSING_SCORE

logger = logging.getLogger(__name__)


def validate_verdict(
    verdict: Dict[str, Any],
    scoring_result: Dict[str, Any],
    category: str,
) -> Dict[str, Any]:
    """Cross-validate GPT verdict against deterministic scoring data.

    Returns validation metadata:
        winner_aligned: bool — GPT winner matches scoring winner
        claims_validated: int — dimensions where GPT and scores agree directionally
        claims_softened: int — dimensions where GPT overclaimed (score gap < 5 but GPT used strong language)
        claims_flagged: int — dimensions where GPT contradicted scores
        confidence_adjustment: str|None — suggested confidence change
    """
    scores = scoring_result.get("scores", {})
    if not scores or "product_0" not in scores or "product_1" not in scores:
        return {
            "winner_aligned": True,
            "claims_validated": 0,
            "claims_softened": 0,
            "claims_flagged": 0,
            "confidence_adjustment": None,
        }

    # Check winner alignment
    score_winner = scoring_result.get("winner_index", 0)
    verdict_winner = verdict.get("winner_index", 0)
    winner_aligned = score_winner == verdict_winner

    # Check dimension-level alignment
    dims = CATEGORY_DIMENSIONS.get(category, CATEGORY_DIMENSIONS.get("other", []))
    b0 = scores["product_0"].get("breakdown", {})
    b1 = scores["product_1"].get("breakdown", {})

    validated = 0
    softened = 0
    flagged = 0

    for dim in dims:
        s0 = b0.get(dim, MISSING_SCORE)
        s1 = b1.get(dim, MISSING_SCORE)
        if s0 == MISSING_SCORE or s1 == MISSING_SCORE:
            continue

        gap = abs(s0 - s1)
        if gap < 3.0:
            # Scores are essentially tied — any strong claim is overclaiming
            softened += 1
        else:
            validated += 1

    # Confidence adjustment
    confidence_adjustment = None
    if not winner_aligned:
        confidence_adjustment = "low"
    elif flagged > 2:
        confidence_adjustment = "reduced"

    return {
        "winner_aligned": winner_aligned,
        "claims_validated": validated,
        "claims_softened": softened,
        "claims_flagged": flagged,
        "confidence_adjustment": confidence_adjustment,
    }
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_trust_validation.py -v`
Expected: All PASS.

- [ ] **Step 5: Integrate into structured_comparison_service**

In `structured_comparison_service.py`, after `generate_comparison()` calls (around lines 320 and 680):

```python
from app.services.trust_validation_service import validate_verdict

# After comparison is generated:
verdict_validation = validate_verdict(comparison, scoring_result, detected_category)
```

Add `verdict_validation` to the response assembly (both streaming and non-streaming paths).

- [ ] **Step 6: Run integration tests**

Run: `python -m pytest tests/test_trust_validation.py tests/test_streaming.py -v`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/trust_validation_service.py app/services/structured_comparison_service.py tests/test_trust_validation.py
git commit -m "feat: add trust validation layer — cross-checks GPT claims against scores"
```

---

## Task 5: Account Deletion Endpoint (Backend-Production)

**Files:**
- Modify: `app/api/auth_routes.py` (add DELETE endpoint + password strength)
- Modify: `app/services/auth_service.py` (add delete_user_account function)
- Modify: `app/services/database_service.py` (add cascade delete helpers + fix print→logger)
- Test: `tests/test_account_deletion.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/test_account_deletion.py`:

```python
"""Tests for account deletion endpoint."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


class TestAccountDeletion:

    def test_delete_account_requires_auth(self):
        from app.main import app
        client = TestClient(app)
        response = client.delete("/api/v1/auth/account")
        assert response.status_code in (401, 403)

    @patch("app.api.auth_routes.verify_token")
    @patch("app.services.auth_service.delete_user_account")
    def test_delete_account_success(self, mock_delete, mock_verify):
        from app.main import app
        client = TestClient(app)
        mock_verify.return_value = {"id": "user-123", "email": "test@test.com"}
        mock_delete.return_value = True
        response = client.delete(
            "/api/v1/auth/account",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_delete.assert_called_once_with("user-123")

    @patch("app.api.auth_routes.verify_token")
    @patch("app.services.auth_service.delete_user_account")
    def test_delete_account_failure(self, mock_delete, mock_verify):
        from app.main import app
        client = TestClient(app)
        mock_verify.return_value = {"id": "user-123", "email": "test@test.com"}
        mock_delete.side_effect = Exception("Deletion failed")
        response = client.delete(
            "/api/v1/auth/account",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 500


class TestPasswordStrength:

    def test_short_password_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "short",
        })
        assert response.status_code == 422

    def test_no_uppercase_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "alllowercase1",
        })
        assert response.status_code == 422

    def test_no_number_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "NoNumberHere",
        })
        assert response.status_code == 422

    def test_valid_password_accepted(self):
        # This test validates the Pydantic model only, not the full registration
        from app.api.auth_routes import RegisterRequest
        req = RegisterRequest(email="test@example.com", password="ValidPass123")
        assert req.password == "ValidPass123"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_account_deletion.py -v`
Expected: FAIL — endpoint and functions don't exist yet.

- [ ] **Step 3: Add cascade delete to database_service.py**

Add to `app/services/database_service.py`:

```python
async def delete_user_data_cascade(user_id: str) -> bool:
    """Delete all user data across all tables. Returns True on success."""
    client = get_supabase_client()
    try:
        # Delete in dependency order
        client.table("user_events").delete().eq("user_id", user_id).execute()
        client.table("comparison_feedback").delete().eq("user_id", user_id).execute()
        client.table("comparisons").delete().eq("user_id", user_id).execute()
        client.table("search_logs").delete().eq("user_id", user_id).execute()
        # Clear user preferences and behavior profile (keep row for auth deletion)
        client.table("users").update({
            "preferences": None,
            "behavior_profile": None,
            "preferences_completed": False,
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error in cascade delete for user {user_id}: {e}")
        raise
```

Also replace all 9 `print()` calls with `logger.error()` or `logger.warning()`.

- [ ] **Step 4: Add delete_user_account to auth_service.py**

Add to `app/services/auth_service.py`:

```python
async def delete_user_account(user_id: str) -> bool:
    """Delete user account and all associated data."""
    from app.services.database_service import delete_user_data_cascade
    # First delete all user data
    await delete_user_data_cascade(user_id)
    # Then delete the auth user via admin client
    admin = get_admin_client()
    admin.auth.admin.delete_user(user_id)
    return True
```

- [ ] **Step 5: Add DELETE endpoint and password validators to auth_routes.py**

Add password validator to `RegisterRequest`:
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v
```

Apply same validator to `ChangePasswordRequest.new_password`.

Add the delete endpoint:
```python
@router.delete("/account")
@limiter.limit("1/minute")
async def delete_account(request: Request, authorization: str = Header(...)):
    """Delete user account and all associated data (App Store requirement)."""
    user = await _get_required_user(authorization)
    try:
        await delete_user_account(user["id"])
        return {"success": True, "message": "Account and all associated data deleted"}
    except Exception as e:
        logger.error(f"Account deletion failed for user {user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Account deletion failed")
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_account_deletion.py -v`
Expected: All PASS.

- [ ] **Step 7: Add email resend verification endpoint**

Add to `auth_routes.py`:
```python
@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(request: Request, body: PasswordResetRequest):
    """Resend email verification link. Uses same model as password reset (just email)."""
    try:
        # Supabase resend uses the same mechanism as password reset
        from app.services.auth_service import resend_verification_email
        await resend_verification_email(body.email)
        return {"success": True, "message": "Verification email sent if account exists"}
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        # Always return success to avoid email enumeration
        return {"success": True, "message": "Verification email sent if account exists"}
```

Add to `auth_service.py`:
```python
async def resend_verification_email(email: str) -> bool:
    client = get_supabase_client()
    client.auth.resend({"type": "signup", "email": email})
    return True
```

Note: Email confirmation must also be re-enabled in the Supabase dashboard (Settings → Auth → Email confirmations → ON). This is a manual step, not code.

- [ ] **Step 8: Run tests**

Run: `python -m pytest tests/test_account_deletion.py -v`
Expected: All PASS.

- [ ] **Step 9: Commit**

```bash
git add app/api/auth_routes.py app/services/auth_service.py app/services/database_service.py tests/test_account_deletion.py
git commit -m "feat: add account deletion, password strength, email resend verification"
```

---

## Task 6: Legal & Version Endpoints (Backend-Production)

**Files:**
- Create: `app/api/legal_routes.py`
- Create: `app/api/version_routes.py`
- Create: `app/legal/privacy_policy.md`
- Create: `app/legal/terms_of_service.md`
- Modify: `app/main.py` (register new routers)
- Test: `tests/test_legal_routes.py` (create)
- Test: `tests/test_version_routes.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/test_legal_routes.py`:

```python
"""Tests for legal endpoints."""
from fastapi.testclient import TestClient


class TestLegalRoutes:

    def test_privacy_policy_returns_200(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        assert "last_updated" in data
        assert len(data["content"]) > 100

    def test_terms_of_service_returns_200(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/terms")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        assert "last_updated" in data
        assert len(data["content"]) > 100

    def test_legal_endpoints_no_auth_required(self):
        from app.main import app
        client = TestClient(app)
        # No Authorization header
        r1 = client.get("/api/v1/legal/privacy")
        r2 = client.get("/api/v1/legal/terms")
        assert r1.status_code == 200
        assert r2.status_code == 200
```

Create `tests/test_version_routes.py`:

```python
"""Tests for app version check endpoint."""
import os
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestVersionRoutes:

    def test_version_returns_200(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/app/version")
        assert response.status_code == 200
        data = response.json()
        assert "min_version" in data
        assert "latest_version" in data
        assert "force_update" in data

    def test_version_no_auth_required(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/app/version")
        assert response.status_code == 200

    @patch.dict(os.environ, {"APP_MIN_VERSION": "2.0.0", "APP_LATEST_VERSION": "2.1.0", "APP_FORCE_UPDATE": "true"})
    def test_version_reads_from_env(self):
        # Need to reimport to pick up env vars
        from app.api.version_routes import get_version_info
        info = get_version_info()
        assert info["min_version"] == "2.0.0"
        assert info["latest_version"] == "2.1.0"
        assert info["force_update"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_legal_routes.py tests/test_version_routes.py -v`
Expected: FAIL — routes don't exist.

- [ ] **Step 3: Create legal content files**

Create `app/legal/privacy_policy.md` with standard privacy policy content covering: data collection, usage, sharing, retention, user rights, contact info. Placeholder content that the business team will finalize.

Create `app/legal/terms_of_service.md` with standard ToS content covering: acceptable use, intellectual property, limitation of liability, dispute resolution.

- [ ] **Step 4: Create legal_routes.py**

```python
"""Legal endpoints — Privacy Policy and Terms of Service."""
import os
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])

LEGAL_DIR = Path(__file__).parent.parent / "legal"


def _read_legal_file(filename: str) -> str:
    filepath = LEGAL_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return "Content not available."


@router.get("/privacy")
async def get_privacy_policy():
    return {
        "title": "Privacy Policy",
        "content": _read_legal_file("privacy_policy.md"),
        "last_updated": "2026-03-26",
    }


@router.get("/terms")
async def get_terms_of_service():
    return {
        "title": "Terms of Service",
        "content": _read_legal_file("terms_of_service.md"),
        "last_updated": "2026-03-26",
    }
```

- [ ] **Step 5: Create version_routes.py**

```python
"""App version check endpoint."""
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])


def get_version_info() -> dict:
    return {
        "min_version": os.getenv("APP_MIN_VERSION", "1.0.0"),
        "latest_version": os.getenv("APP_LATEST_VERSION", "1.0.0"),
        "force_update": os.getenv("APP_FORCE_UPDATE", "false").lower() == "true",
        "update_url_ios": os.getenv("APP_STORE_URL", ""),
        "update_url_android": os.getenv("PLAY_STORE_URL", ""),
    }


@router.get("/version")
async def check_version():
    return get_version_info()
```

- [ ] **Step 6: Register routers in main.py**

Add imports and `app.include_router()` calls for `legal_routes.router` and `version_routes.router`.

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_legal_routes.py tests/test_version_routes.py -v`
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add app/api/legal_routes.py app/api/version_routes.py app/legal/ app/main.py tests/test_legal_routes.py tests/test_version_routes.py
git commit -m "feat: add legal (privacy/terms) and app version check endpoints"
```

---

## Task 7: Code Cleanup (Backend-Production)

**Files:**
- Delete: `app/services/comparison_service.py`
- Modify: `app/services/database_service.py` (print→logger already done in Task 5)

- [ ] **Step 1: Verify comparison_service.py is unused**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All pass without comparison_service.py being imported.

- [ ] **Step 2: Delete dead code**

```bash
git rm app/services/comparison_service.py
```

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All pass (1295+ tests). No test imports comparison_service.py.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete dead comparison_service.py (289 lines, never imported)"
```

---

## Task 8: Full Integration & Cross-QA (Test-QA + All)

**Files:** All modified files
**Dependencies:** Tasks 1-7 complete

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```

Expected: All pass (target 1400+ tests with new additions).

- [ ] **Step 2: Syntax check all modified files**

```bash
python -m py_compile app/services/scoring_service.py
python -m py_compile app/services/prompt_personalities.py
python -m py_compile app/services/trust_validation_service.py
python -m py_compile app/services/extraction_service.py
python -m py_compile app/services/structured_comparison_service.py
python -m py_compile app/api/auth_routes.py
python -m py_compile app/services/auth_service.py
python -m py_compile app/services/database_service.py
python -m py_compile app/api/legal_routes.py
python -m py_compile app/api/version_routes.py
python -m py_compile app/main.py
```

Expected: All compile without errors.

- [ ] **Step 3: Cross-QA review**

Each agent reviews another agent's work:
- **Backend-Scoring** reviews Backend-Prompts (prompt personalities + trust validation)
- **Backend-Prompts** reviews Backend-Scoring (dimension config + scoring rewrite)
- **Backend-Production** reviews Test-QA (test coverage + quality)
- **Test-QA** reviews Backend-Production (account deletion + legal + cleanup)

QA checklist per review:
- All functions have correct signatures
- All imports resolve
- No hardcoded values that should be config
- Error handling is present
- Tests cover happy path + edge cases
- No regressions in existing functionality

- [ ] **Step 4: Fix any QA issues found**

Iterate until all agents approve.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: category comparison languages + backend production hardening

- 9 category-specific scoring dimensions (replacing universal 6)
- Category prompt personalities for GPT verdict generation
- Trust validation layer (cross-checks GPT claims vs scores)
- Account deletion endpoint (App Store requirement)
- Legal endpoints (privacy policy, terms of service)
- App version check endpoint
- Password strength upgrade (10+ chars, mixed case, numbers)
- Dead code cleanup (comparison_service.py deleted)
- print() → logger in database_service.py"
```

---

## Agent Assignment Summary

| Task | Agent | Dependencies |
|------|-------|-------------|
| Task 1: Dimension Config | Backend-Scoring | None |
| Task 2: Scoring Engine Rewrite | Backend-Scoring | Task 1 |
| Task 3: Prompt Personalities | Backend-Prompts | None (parallel with Tasks 1-2) |
| Task 4: Trust Validation | Backend-Prompts | Task 2 (needs new dim keys) |
| Task 5: Account Deletion | Backend-Production | None (parallel) |
| Task 6: Legal & Version | Backend-Production | None (parallel) |
| Task 7: Code Cleanup | Backend-Production | None (parallel) |
| Task 8: Integration & QA | All agents | Tasks 1-7 |

**Parallelization:** Tasks 1+3+5+6+7 can run simultaneously. Task 2 depends on Task 1. Task 4 depends on Task 2. Task 8 depends on all.

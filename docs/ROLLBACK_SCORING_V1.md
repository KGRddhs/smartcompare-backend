# Scoring System V1 — Rollback Reference

> **Purpose**: Preserves the original 6-dimension scoring system in case the new category-specific dimensions need to be reverted.

## V1 Scoring Dimensions (Universal, All Categories)

All 9 categories use the same 6 dimensions:

| Dimension | Key | Description |
|-----------|-----|-------------|
| Price Score | `price_score` | Lower price = higher score (30-100 range) |
| Spec Score | `spec_score` | Aggregate of category-specific spec fields |
| Review Score | `review_score` | Rating/5 mapped to 20-100 |
| Value Score | `value_score` | Tier-aware combo of spec + price |
| Reliability Score | `reliability_score` | Fact-check verification quality |
| Popularity Score | `popularity_score` | Log-scale review count + source count |

## V1 Category Weights

```python
CATEGORY_WEIGHTS = {
    "electronics":  {"price_score": 0.20, "spec_score": 0.25, "review_score": 0.20, "value_score": 0.15, "reliability_score": 0.15, "popularity_score": 0.05},
    "supplements":  {"price_score": 0.10, "spec_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.30, "popularity_score": 0.05},
    "fashion":      {"price_score": 0.10, "spec_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.25},
    "fragrances":   {"price_score": 0.10, "spec_score": 0.10, "review_score": 0.30, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.25},
    "grocery":      {"price_score": 0.25, "spec_score": 0.10, "review_score": 0.25, "value_score": 0.25, "reliability_score": 0.10, "popularity_score": 0.05},
    "makeup":       {"price_score": 0.15, "spec_score": 0.15, "review_score": 0.30, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.15},
    "skincare":     {"price_score": 0.15, "spec_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.20, "popularity_score": 0.10},
    "haircare":     {"price_score": 0.20, "spec_score": 0.10, "review_score": 0.30, "value_score": 0.20, "reliability_score": 0.10, "popularity_score": 0.10},
    "other":        {"price_score": 0.20, "spec_score": 0.20, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.10},
}
```

## V1 Priority Adjustments

```python
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
    "mid": {},
    "premium": {"spec_score": 0.10, "review_score": 0.05, "price_score": -0.10},
}
```

## V1 Weight Caps

- Explicit preferences: `MAX_WEIGHT_SHIFT_RATIO = 0.30` (±30% of category base)
- Behavioral profile: `MAX_BEHAVIORAL_SHIFT_RATIO = 0.10` (±10%)
- Session signals: `MAX_SESSION_SHIFT_RATIO = 0.05` (±5%)

## V1 Price Tiers (BHD)

```python
PRICE_TIERS = {
    "budget":  (0, 11),
    "mid":     (11, 57),
    "premium": (57, 189),
    "luxury":  (189, float("inf")),
}
TIER_EXPECTATIONS = {"budget": 0.6, "mid": 0.7, "premium": 0.8, "luxury": 0.85}
```

## V1 Spec Scoring

- `HIGHER_IS_BETTER`: ram, storage, battery, rear_camera, front_camera, count, dosage, serving_size, nutrition_protein, shelf_life, shade_range, spf, volume, longevity
- `LOWER_IS_BETTER`: weight, nutrition_calories, nutrition_fat, nutrition_carbs
- Coverage penalty: `CATEGORY_MIN_COVERAGE` thresholds per category
- Non-numeric fields: +1 score for having data

## V1 Value Badges

```python
def compute_value_badge(value_score, price_tier):
    if value_score >= 75:
        return "fair_price" if price_tier == "luxury" else "great_value"
    elif value_score >= 50: return "fair_price"
    elif value_score >= 25: return "premium_price"
    else: return "overpriced"
```

## V1 Tradeoff Pairs

- Pairs winner-winning dimensions with loser-winning dimensions
- Margin > 5% filter, max 3 pairs, sorted by combined impact

## V1 Confidence Indicators

- Price: source_count, method (retailer_verified/converted/estimated), freshness
- Rating: review_count, source, verified boolean
- Specs: verified_pct, citation_count
- Overall: high (3 strong) / medium (2 strong) / low

## Rollback Instructions

To revert from V2 category-specific dimensions back to V1:
1. Replace `CATEGORY_DIMENSIONS` in `scoring_service.py` with `CATEGORY_WEIGHTS` above
2. Restore `_compute_raw_scores()` to use V1's 6 universal dimensions
3. Restore `_normalize_scores()` to V1's 6 normalization methods
4. Restore `compute_dimension_winners()` to use V1's 6-dimension list
5. Restore `build_scores_summary()` to reference V1 dimension names
6. Update `PRIORITY_ADJUSTMENTS` and `BUDGET_ADJUSTMENTS` to V1 values
7. Run full test suite to verify: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)"`

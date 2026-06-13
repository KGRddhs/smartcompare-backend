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

# S2 I2.4 — spec schema fields that are EXTRACTION/verdict-awareness signals
# only and must NEVER enter deterministic scoring (design §4 hard rule: no new
# scoring dimension). `_score_specs` strips these from the schema field list so
# the coverage denominator and the per-field tally stay byte-identical to the
# pre-S2 behaviour. `heat_stability` (H8 Gulf-climate signal) is the first such
# key; the verdict prompt references it via the per-category H8 anti-pattern.
NON_SCORING_SPEC_KEYS = frozenset({"heat_stability"})

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


# S3 winner-mechanism Option A1 — normalization dampening (team-lead APPROVED as
# DEFAULT, 2026-06-13). `_normalize_dimension` previously mapped the relative
# position with `30 + ratio*70` (range 30–100), so the product with even a
# SLIGHTLY higher raw spec number got 100 and the other got 30 — a 70pt swing
# manufactured from noise (the corpus-pinned driver of the 47%-wrong-on-clean
# winner gap). A1 narrows the spread to `45 + ratio*40` (range 45–85), and the
# genuine-tie return to the new band midpoint (65). This compresses BOTH the
# user-visible dim bars AND the winner/overall contribution (the FULL version).
# `DISABLE_DIM_NORM_DAMPENING` (default OFF) is the escape hatch: reverts to the
# legacy 30–100 spread + 70 tie if Ahmed wants the dramatic bars kept.
_DIM_NORM_FLOOR_DAMPENED = 45.0
_DIM_NORM_SPAN_DAMPENED = 40.0
_DIM_NORM_TIE_DAMPENED = 65.0
_DIM_NORM_FLOOR_LEGACY = 30.0
_DIM_NORM_SPAN_LEGACY = 70.0
_DIM_NORM_TIE_LEGACY = 70.0


def _signal_missing_for(raw: Dict[str, Any], signal: str) -> bool:
    """S3 L3 v2 [gate finding B] — is a dimension's SOURCE SIGNAL missing for this
    product, read from the per-signal `_<sig>_missing` flags (the source of truth),
    NEVER `== MISSING_SCORE` value-equality (a computed 50 is a real score).

    Signal → raw-flag mapping (mirrors _DIMENSION_SIGNAL_MAP + _compute_raw_scores):
      spec / review / reliability / popularity → `_<signal>_missing`
      value           → spec OR price missing (the value dim needs both)
      spec_secondary  → spec AND review both missing (blends the two; present if
                        either side has signal — matches the spec_secondary
                        fallback in _normalize_scores).
    """
    if signal == "value":
        return bool(raw.get("_spec_missing")) or bool(raw.get("_price_missing"))
    if signal == "spec_secondary":
        return bool(raw.get("_spec_missing")) and bool(raw.get("_review_missing"))
    return bool(raw.get(f"_{signal}_missing"))


def _dim_norm_dampening_disabled() -> bool:
    """Escape hatch reader — when ENV DISABLE_DIM_NORM_DAMPENING is set, revert
    `_normalize_dimension` to the legacy 30–100 spread (+ legacy 70 tie + NO
    magnitude-awareness — full legacy behavior). Read live (not cached) so a
    monkeypatch test + a Railway flip take effect without a restart."""
    import os
    return os.environ.get("DISABLE_DIM_NORM_DAMPENING", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


# S3 L3 v2 — MAGNITUDE-AWARENESS (team-lead root-cause fix). _normalize_dimension
# mapped DIRECTION to the full band and ignored MAGNITUDE: relative min/max on a
# 2-product pair gave the higher value the ceiling + the lower the floor by ANY
# margin, so a +0.02% product got a decisive lead. The relative-gap tolerance
# makes the dim reflect the SIZE of the gap: gaps within the tolerance read as a
# ~tie (band midpoint); beyond it the lead opens scaled by the EXCESS gap
# ((gap−tol)/(1−tol)), smoothly (no cliff at the tolerance). Sweep-tunable via
# WINNER_DIM_GAP_TOLERANCE (deterministic post-data → offline-sweepable).
_DEFAULT_DIM_GAP_TOLERANCE = 0.08  # 8% relative gap ≈ tie


def _dim_gap_tolerance() -> float:
    import os
    raw = os.environ.get("WINNER_DIM_GAP_TOLERANCE")
    if raw is None:
        return _DEFAULT_DIM_GAP_TOLERANCE
    try:
        v = float(raw)
        return min(0.95, max(0.0, v))
    except (TypeError, ValueError):
        return _DEFAULT_DIM_GAP_TOLERANCE


def _magnitude_aware_ratio(current: float, lo: float, hi: float, higher_better: bool) -> float:
    """Return the 0..1 position of `current` between lo/hi AFTER applying the
    relative-gap tolerance: when the relative gap |hi−lo|/hi is within the
    tolerance, BOTH map to 0.5 (a tie at the band midpoint); beyond it, the
    effective ratio is scaled by how far past the tolerance the gap reaches so a
    small-but-real gap barely opens and a large gap opens fully. hi > lo assumed
    (caller handles hi==lo). Direction handled by `higher_better`."""
    span = hi - lo
    if span <= 0:
        return 0.5
    # S3 L3 v2 [gate finding C] — the relative-gap scale is the LARGER-magnitude
    # endpoint, max(|hi|, |lo|), NOT |hi|. With negative values |hi| can be the
    # SMALLER magnitude (e.g. lo=-100, hi=-10 → |hi|=10 ≪ |lo|=100), so dividing
    # by |hi| under-reported the scale and INFLATED rel_gap → a modest gap read
    # as decisive (the very noise→decisive failure A1 set out to kill). max(|.|)
    # is sign-agnostic and never smaller than |hi|, so positive-only pairs are
    # unchanged (hi is already the larger |.| there). Falls back to span only if
    # both endpoints are exactly 0 (span would be 0 → already returned above).
    denom = max(abs(hi), abs(lo))
    rel_gap = span / denom if denom > 0 else 1.0
    tol = _dim_gap_tolerance()
    if rel_gap <= tol:
        return 0.5  # within tolerance → genuine tie at the band midpoint
    # Excess factor in (0, 1]: how decisively the gap exceeds the tolerance.
    excess = (rel_gap - tol) / (1.0 - tol) if tol < 1.0 else 1.0
    excess = min(1.0, max(0.0, excess))
    # Position of `current` within [lo, hi] (0 at lo, 1 at hi).
    pos = (current - lo) / span
    if not higher_better:
        pos = 1.0 - pos
    # Pull `pos` toward the 0.5 midpoint by (1 - excess): a marginal gap keeps
    # both near 0.5; a decisive gap lets pos reach its extreme.
    return 0.5 + (pos - 0.5) * excess


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


# Bundle C § 4a — value-formula coefficients keyed by user's top priority.
# When `preferences.priorities[0]` matches a key, those (spec, price)
# weights win. First-match semantics: priorities=['quality','price'] uses
# the 'quality' row. Used only inside _compute_value_score and never
# exposed in API responses (critical rule #2: no internals in user-facing
# diagnostic reveals).
#
# S3 L3 v2 (b) lever 1 — VALUE = VALUE-FOR-MONEY. The default coefficients
# shifted spec 0.60/price 0.40 → 0.70/0.30 so "what you get" dominates "how
# cheap": a marginally-cheaper product with equal specs no longer wins the value
# dim on price alone (the S2-pinned cheaper-bias root cause — gold rewards the
# pricier product 64% of priced rows). The explicit `price` priority still
# leans price-heavy (a price-first shopper genuinely wants cheap). Coefficients
# never surface in API responses (critical rule #2).
VALUE_FORMULA_BY_PRIORITY = {
    "price":             {"spec": 0.45, "price": 0.55},
    "quality":           {"spec": 0.75, "price": 0.25},
    "durability":        {"spec": 0.70, "price": 0.30},
    "latest_features":   {"spec": 0.70, "price": 0.30},
    "brand_reputation":  {"spec": 0.70, "price": 0.30},
    "eco_friendly":      {"spec": 0.60, "price": 0.40},
    "ease_of_use":       {"spec": 0.60, "price": 0.40},
    "_default":          {"spec": 0.70, "price": 0.30},
}


# Bundle C § 7b A.9.1 — personalization chip qualitative-only contract.
# Compute applied_shifts[] from weights_used vs CATEGORY_DIMENSION_WEIGHTS
# defaults. Each shift is {dim_display, direction} ONLY — direction is
# 'up' / 'down' based on sign of delta. Magnitude is INTENTIONALLY hidden
# per critical rule #2 (no backend internals in user-facing reveals).
# Sorted by absolute magnitude descending; top 3 returned for the chip.
_APPLIED_SHIFT_NOISE_FLOOR = 0.001  # ignore <0.1% drift (rounding artifacts)


def _compute_applied_shifts(weights_used, defaults) -> list:
    """Bundle C § 7b A.9.1 — return the top 3 dim shifts as
    [{dim_display, direction}] ordered by absolute magnitude descending.

    Pure qualitative output — magnitude is computed internally for sorting
    but NEVER surfaces in the returned dicts. Empty list when:
      - either input is None/empty
      - all shifts are below the noise floor (genuinely no personalization)
    """
    if not weights_used or not defaults:
        return []
    try:
        deltas = []
        for dim, used in weights_used.items():
            default = defaults.get(dim, 0)
            delta = used - default
            if abs(delta) >= _APPLIED_SHIFT_NOISE_FLOOR:
                deltas.append((dim, delta))
        if not deltas:
            return []
        # Sort by absolute magnitude descending; keep top 3.
        deltas.sort(key=lambda kv: abs(kv[1]), reverse=True)
        out = []
        for dim, delta in deltas[:3]:
            out.append({
                "dim_display": DIMENSION_DISPLAY_NAMES.get(dim, dim),
                "direction": "up" if delta > 0 else "down",
            })
        return out
    except (TypeError, AttributeError):
        return []


def _resolve_value_coefficients(priorities=None) -> Dict[str, float]:
    """Bundle C § 4a — first-match-wins lookup against VALUE_FORMULA_BY_PRIORITY.
    Returns the (spec, price) coefficient dict for the highest-ranked priority
    that has an entry, or the default row when no priorities are supplied or
    none match. Stays internal; never bubbles into API responses."""
    if not priorities:
        return VALUE_FORMULA_BY_PRIORITY["_default"]
    for p in priorities:
        coeffs = VALUE_FORMULA_BY_PRIORITY.get(p)
        if coeffs is not None and p != "_default":
            return coeffs
    return VALUE_FORMULA_BY_PRIORITY["_default"]


# Bundle C § 5a — loosened confidence thresholds.
# - rating_strong: drop verified=True; require review_count >= 100.
# - price_strong:  drop the "method != estimated" blocker IF at least one
#                  product's source_method is in the trust set OR
#                  shopping_count >= 3 (Serper coverage alone qualifies).
# - specs_strong:  lower verified_pct >= 60 → 40, OR citation_count >= 8.
# - overall:       3 strong → high, 2 → medium, ≤1 → low (unchanged).
_PRICE_TRUST_SET = frozenset({
    "official_brand", "page_scrape", "page_scrape_rendered",
    "firecrawl", "scrapedo_rendered", "local_bhd",
})


def _product_review_count(p: Dict[str, Any]) -> int:
    val = p.get("review_count")
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return 0


def _product_shopping_count(p: Dict[str, Any]) -> int:
    val = p.get("shopping_count")
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return 0


def _product_source_method(p: Dict[str, Any]) -> str:
    price = p.get("price") or {}
    if not isinstance(price, dict):
        return "estimated"
    return price.get("source_method") or "estimated"


# ---------------------------------------------------------------------------
# S3 L3 v2 — PRICE-AUTHORITY AS A SCORE FACTOR (Ahmed pivot 2026-06-13).
# "Facts beat estimates" lives IN the genuine overall score, not a winner_index
# flip. A real Bahrain price (source_method in _PRICE_TRUST_SET) is the product's
# HONEST score → no penalty. An `estimated` price is the UNCERTAIN score → a
# modest penalty (display-honest shape: discount the estimate, don't inflate the
# real). `converted_usd` is a real converted figure but not local data → a
# SMALLER penalty. The penalty is applied to each product's `overall` BEFORE the
# argmax, so the winner emerges from the score + the effect is visible +
# consistent everywhere (rings/verdict/share/eval all argmax the same overall).
#
# MAGNITUDE: WINNER_PRICE_AUTHORITY_POINTS (the estimate penalty, on the 0-100
# overall scale). Sized SMALLER than a decisive real-signal lead so a clearly-
# better estimated product still wins; only genuine close calls tip to facts.
# Tunable post-measurement via the env (offline sweep over captured bodies).
# ---------------------------------------------------------------------------

_DEFAULT_PRICE_AUTHORITY_POINTS = 4.0
_CONVERTED_USD_PENALTY_RATIO = 0.5  # converted_usd penalty = ratio * estimate penalty


def _price_authority_points() -> float:
    import os
    raw = os.environ.get("WINNER_PRICE_AUTHORITY_POINTS")
    if raw is None:
        return _DEFAULT_PRICE_AUTHORITY_POINTS
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return _DEFAULT_PRICE_AUTHORITY_POINTS


def _price_authority_delta(product: Dict[str, Any]) -> float:
    """Return the additive authority adjustment (<= 0) for a product's `overall`,
    keyed on price provenance. Real BH price → 0 (honest score stands);
    `estimated` → −points; `converted_usd` → −(ratio*points) (real figure, not
    local). All other non-trust methods treated as estimate-grade."""
    method = _product_source_method(product)
    if method in _PRICE_TRUST_SET:
        return 0.0
    pts = _price_authority_points()
    if method == "converted_usd":
        return -pts * _CONVERTED_USD_PENALTY_RATIO
    return -pts


# S3 L3 v2 (b) lever 2 — value-dim WEIGHT reduction hatch. The value dim rewards
# cheapness (S2 root cause); WINNER_VALUE_WEIGHT_SCALE (default 1.0 = no change)
# scales the value-type dim's category weight, redistributing the freed weight
# proportionally across the non-value dims so genuine quality drives the pick.
# Deterministic post-data → offline-sweepable. The FINAL default lands by
# Ahmed's sign-off on the measured sweep.
def _value_weight_scale() -> float:
    import os
    raw = os.environ.get("WINNER_VALUE_WEIGHT_SCALE")
    if raw is None:
        return 1.0
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 1.0


def _scale_value_weight(weights: Dict[str, float], category: str) -> Dict[str, float]:
    """Scale the value-type dim's weight by WINNER_VALUE_WEIGHT_SCALE, redistribute
    the freed weight proportionally across the non-value dims, renormalize. No-op
    at scale 1.0. The value-type dim(s) are identified via _DIMENSION_SIGNAL_MAP."""
    scale = _value_weight_scale()
    if scale == 1.0:
        return weights
    dim_map = ScoringService._DIMENSION_SIGNAL_MAP.get(
        category, ScoringService._DIMENSION_SIGNAL_MAP["other"]
    )
    value_dims = {d for d, sig in dim_map.items() if sig == "value" and d in weights}
    if not value_dims:
        return weights
    out = dict(weights)
    freed = 0.0
    for d in value_dims:
        new_w = out[d] * scale
        freed += out[d] - new_w
        out[d] = new_w
    # Redistribute the freed weight proportionally across the non-value dims.
    non_value = {d: w for d, w in out.items() if d not in value_dims}
    nv_total = sum(non_value.values())
    if nv_total > 0 and freed > 0:
        for d in non_value:
            out[d] += freed * (non_value[d] / nv_total)
    total = sum(out.values())
    if total > 0:
        out = {k: v / total for k, v in out.items()}
    return out


# ---------------------------------------------------------------------------
# S3 L3 v2 — build_winner_evidence: qualitative reasons describing the GENUINE
# winner (the plain argmax of the authority-adjusted overall). NO winner_index
# flip, NO coefficients/caps/percentages (no_backend_internals_in_reveals).
# Reasons drawn from: real Bahrain price provenance, stronger review signal, and
# spec-lead — whichever genuinely favour the winner. Empty list when nothing
# clearly distinguishes the winner (close calls keep quiet rather than fabricate).
# ---------------------------------------------------------------------------


def _has_real_price(p: Dict[str, Any]) -> bool:
    """True iff the product carries a real (non-estimated) Bahrain-relevant
    price. `_PRICE_TRUST_SET` is the authoritative 'real data' set; everything
    else (`estimated`, `converted_usd`) is NOT a real local price."""
    return _product_source_method(p) in _PRICE_TRUST_SET


def _product_name_for_evidence(p: Dict[str, Any]) -> str:
    name = (f"{p.get('brand', '')} {p.get('name', '')}".strip()
            or (p.get('name') or '').strip())
    return name or "the winning option"


def _safe_rating_val(p: Dict[str, Any]) -> Optional[float]:
    r = p.get("rating")
    try:
        return float(r) if isinstance(r, (int, float)) else None
    except (TypeError, ValueError):
        return None


def build_winner_evidence(
    products_data: List[Dict[str, Any]],
    result_products: Dict[str, Any],
    winner_index: int,
    category: str,
) -> List[str]:
    """S3 L3 v2 — qualitative reasons backing the GENUINE winner. Reasons only
    (no numbers/coefficients/caps). Returns up to 2 reasons covering: real
    Bahrain price (when the winner has one and the runner-up does not), stronger
    reviews (clearly higher rating), and a clear overall lead. Empty when the
    winner doesn't clearly distinguish on these axes (avoids fabricated reasons
    on a genuine coin-flip)."""
    if len(products_data) != 2:
        return []
    win = products_data[winner_index]
    run = products_data[1 - winner_index]
    reasons: List[str] = []

    # Price provenance — winner has a real BH price, runner-up an estimate.
    if _has_real_price(win) and not _has_real_price(run):
        reasons.append("has a confirmed Bahrain price while the other relies on an indicative figure")

    # Review strength — winner clearly higher rated.
    rw, rr = _safe_rating_val(win), _safe_rating_val(run)
    if rw is not None and rr is not None and rw - rr >= 0.3:
        reasons.append("draws stronger reviewer ratings")

    # Overall lead — only as a fallback reason when no concrete axis fired but
    # the winner has a clear score margin (keeps a reason for a genuine lead).
    if not reasons:
        ow = result_products.get(f"product_{winner_index}", {}).get("overall")
        orun = result_products.get(f"product_{1 - winner_index}", {}).get("overall")
        try:
            if ow is not None and orun is not None and float(ow) - float(orun) >= 6.0:
                reasons.append("leads on the overall picture")
        except (TypeError, ValueError):
            pass

    if not reasons:
        return []
    name = _product_name_for_evidence(win)
    return [f"{name} {r}" for r in reasons[:2]]


def _product_fact_check_pcts(p: Dict[str, Any]) -> tuple[int, int]:
    """Return (verified_pct, citation_count). Tolerates two shapes:
    legacy {specs_verified, specs_likely, specs_unverified, specs_flagged}
    OR new {verified_pct, citation_count}."""
    fc = p.get("fact_check") or {}
    if not isinstance(fc, dict):
        return 0, 0
    if "verified_pct" in fc or "citation_count" in fc:
        return int(fc.get("verified_pct") or 0), int(fc.get("citation_count") or 0)
    verified = int(fc.get("specs_verified") or 0)
    likely = int(fc.get("specs_likely") or 0)
    unverified = int(fc.get("specs_unverified") or 0)
    flagged = int(fc.get("specs_flagged") or 0)
    total = verified + likely + unverified + flagged
    verified_pct = round((verified / total) * 100) if total > 0 else 0
    return verified_pct, total


def _classify_leg(strong: bool, near_strong: bool) -> str:
    """Map two-stage threshold check → user-facing leg strength enum."""
    if strong:
        return "strong"
    if near_strong:
        return "acceptable"
    return "weak"


def compute_confidence(
    products: List[Dict[str, Any]],
    cached: bool = False,
) -> Dict[str, Any]:
    """Bundle C § 5a — module-level confidence with loosened thresholds.

    New contract:
      {
        "legs": {"price": "strong|acceptable|weak", "reviews": ..., "specs": ...},
        "overall": "high|medium|low",      # backwards-compat per spec § 5d
        "price": {...details...},          # legacy per-leg detail dicts
        "rating": {...},
        "specs": {...},
      }

    Per-leg strength reads across ALL supplied products (e.g. price_strong
    fires if ANY product has trust-set source_method OR shopping_count >= 3).
    Frontend renders the 3 pills (Section B.7); legacy `overall` stays so
    existing consumers keep parsing.
    """
    products = products or []
    if not products:
        return {
            "legs": {"price": "weak", "reviews": "weak", "specs": "weak"},
            "overall": "low",
            "price": {"source_count": 0, "method": "estimated", "freshness": "live" if not cached else "cached"},
            "rating": {"review_count": 0, "source": None, "verified": False},
            "specs": {"verified_pct": 0, "citation_count": 0},
        }

    # --- reviews leg ---------------------------------------------------------
    max_reviews = max((_product_review_count(p) for p in products), default=0)
    reviews_strong = max_reviews >= 100
    reviews_acceptable = max_reviews >= 50

    # --- price leg -----------------------------------------------------------
    any_trust_method = any(_product_source_method(p) in _PRICE_TRUST_SET for p in products)
    max_shopping = max((_product_shopping_count(p) for p in products), default=0)
    price_strong = any_trust_method or max_shopping >= 3
    price_acceptable = max_shopping >= 2

    # --- specs leg -----------------------------------------------------------
    best_pct = 0
    best_citations = 0
    for p in products:
        pct, citations = _product_fact_check_pcts(p)
        best_pct = max(best_pct, pct)
        best_citations = max(best_citations, citations)
    specs_strong = best_pct >= 40 or best_citations >= 8
    specs_acceptable = best_pct >= 20 or best_citations >= 4

    legs = {
        "price":   _classify_leg(price_strong, price_acceptable),
        "reviews": _classify_leg(reviews_strong, reviews_acceptable),
        "specs":   _classify_leg(specs_strong, specs_acceptable),
    }

    strong_count = sum(1 for v in legs.values() if v == "strong")
    if strong_count >= 3:
        overall = "high"
    elif strong_count >= 2:
        overall = "medium"
    else:
        overall = "low"

    # Legacy per-leg detail dicts — preserved so older consumers
    # (admin dashboards, history serializers) keep working.
    product0 = products[0] or {}
    price_data = product0.get("price") if isinstance(product0.get("price"), dict) else {}
    source_method = (price_data or {}).get("source_method", "estimated")
    if source_method in ("local_bhd", "page_scrape", "page_scrape_rendered"):
        method = "retailer_verified"
    elif source_method == "converted_usd":
        method = "converted"
    else:
        method = source_method or "estimated"
    rating_source = product0.get("rating_source") if isinstance(product0, dict) else None
    return {
        "legs": legs,
        "overall": overall,
        "price": {
            "source_count": _product_shopping_count(product0),
            "method": method,
            "freshness": "live" if not cached else "cached",
        },
        "rating": {
            "review_count": _product_review_count(product0),
            "source": rating_source.get("name") if isinstance(rating_source, dict) else None,
            "verified": bool(product0.get("rating_verified")),
        },
        "specs": {
            "verified_pct": _product_fact_check_pcts(product0)[0],
            "citation_count": _product_fact_check_pcts(product0)[1],
        },
    }


def _compute_value_score(
    spec_score: float,
    price_score: float,
    priorities=None,
    *,
    price_tier: str = "mid",
    is_cross_tier: bool = False,
) -> float:
    """Bundle C § 4a — module-level value-formula entry point. Resolves
    priority-driven coefficients from VALUE_FORMULA_BY_PRIORITY and combines
    spec + price scores accordingly. For cross-tier comparisons the legacy
    TIER_EXPECTATIONS penalty still applies (spec § 4a cross-tier note —
    A.6.3 narrows the delivery multiplier further).

    `priorities` is the user's ordered priority list (e.g. ['price','durability']).
    Backwards-compat: the ScoringService._compute_value_score method below
    delegates here, passing the preferences it received via _normalize_scores."""
    # Sparse-signal fallbacks (mirror legacy method semantics — MISSING_SCORE
    # behavior preserved for legacy callers; flag-on None propagation handled
    # by upstream A.4.9 dim omission).
    if spec_score is None and price_score is None:
        return MISSING_SCORE
    if spec_score is None:
        return price_score
    if price_score is None:
        return spec_score
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

    coeffs = _resolve_value_coefficients(priorities)
    return round(spec_score * coeffs["spec"] + price_score * coeffs["price"], 1)

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
        cohort_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute scores for a list of products using category-specific dimensions.

        S3 L3 v2 (c): `cohort_profile` (the cohort-seeded preferences shape
        {priorities, ...}) nudges the dimension weights toward the cohort's
        inferred priorities (±10% cap), applied ONLY when no EXPLICIT preferences
        are supplied — explicit prefs are the stronger ±30% signal and win.
        """
        if not products_data or len(products_data) < 2:
            return self._empty_result(len(products_data))

        category = products_data[0].get("category", "other")
        if category not in CATEGORY_DIMENSIONS:
            category = "other"
        weights = self._compute_weights(preferences, category)

        # S3 L3 v2 (c) — cohort priors into the score weights, ONLY when the user
        # has no explicit preferences (cohort is the weak inferred default).
        cohort_applied = False
        if not preferences and cohort_profile and cohort_profile.get("priorities"):
            new_weights = self.apply_cohort_adjustments(weights, cohort_profile, category)
            cohort_applied = new_weights != weights
            weights = new_weights

        # Apply behavioral and session adjustments (layered on top of explicit preferences)
        if behavior_profile:
            weights = self.apply_behavioral_adjustments(weights, behavior_profile)
        if session_signals:
            weights = self.apply_session_signals(weights, session_signals)

        # Compute raw dimension scores for each product
        raw_scores = []
        for product in products_data:
            raw_scores.append(self._compute_raw_scores(product, category))

        # Normalize scores relative to each other (0-100 scale).
        # Bundle C § 4a: pass `preferences` so the value-formula can read
        # priorities and apply VALUE_FORMULA_BY_PRIORITY coefficients.
        normalized, price_tiers, is_cross_tier = self._normalize_scores(
            raw_scores, products_data, category, preferences=preferences,
        )

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

        # S3 L3 v2 — PRICE-AUTHORITY AS A SCORE FACTOR (Ahmed pivot 2026-06-13).
        # "Facts beat estimates" now lives IN the genuine `overall` score, NOT a
        # winner_index flip. Apply the per-product authority delta (estimate /
        # converted_usd penalty; real BH price unpenalized) to `overall` BEFORE
        # the argmax. v1's A2 value-neutralization + estimate-demotion + tie-break
        # index-overrides are DROPPED — the winner is now the plain argmax of the
        # genuine score, which the frontend's argmax(scoring_v2.overall_score)
        # matches automatically (ResultsScreen.tsx) — zero FE change.
        if len(products_data) == 2:
            n_dims = len(dims)
            for i in range(len(products_data)):
                pk = f"product_{i}"
                # Guard: don't penalize an all-MISSING product — its `overall`
                # is the MISSING-driven sentinel, not a genuine score, and the
                # orchestrator returns INSUFFICIENT_DATA for the both-missing
                # case anyway. Penalizing it would break the MISSING invariant.
                md = result_products[pk].get("missing_data")
                if md and len(md) >= n_dims:
                    continue
                delta = _price_authority_delta(products_data[i])
                if delta:
                    adjusted = round(max(0.0, min(100.0, result_products[pk]["overall"] + delta)), 1)
                    result_products[pk]["overall"] = adjusted

        # Determine winner — plain argmax of the genuine (authority-adjusted)
        # overall. No flip overrides anywhere.
        overalls = [result_products[f"product_{i}"]["overall"] for i in range(len(products_data))]
        winner_index = overalls.index(max(overalls))
        win_margin = round(abs(overalls[0] - overalls[1]), 1) if len(overalls) >= 2 else 0

        # S3 L3 v2 — qualitative winner_evidence describing the GENUINE winner
        # (price provenance + signal strength). Reasons only, no coefficients/
        # caps/percentages (no_backend_internals_in_reveals).
        winner_evidence: List[str] = []
        if len(products_data) == 2:
            winner_evidence = build_winner_evidence(
                products_data, result_products, winner_index, category,
            )

        if behavior_profile or session_signals:
            scoring_method = "behavioral"
        elif preferences:
            scoring_method = "personalized"
        elif cohort_applied:
            scoring_method = "cohort"
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

        result = {
            "scores": result_products,
            "winner_index": winner_index,
            "win_margin": win_margin,
            "scoring_method": scoring_method,
            "price_tiers": price_tiers_map,
            "is_cross_tier": is_cross_tier,
            "dimension_winners": dimension_winners,
            "category_weights": dict(CATEGORY_DIMENSION_WEIGHTS.get(category, CATEGORY_DIMENSION_WEIGHTS["other"])),
            # S3 L3 v2 — qualitative reasons describing the GENUINE winner
            # (price provenance + signal strength). Surfaced in scoring_v2 by L3.4.
            "winner_evidence": winner_evidence,
        }
        return result

    def _compute_weights(self, preferences: Optional[Dict[str, Any]], category: str = "other") -> Dict[str, float]:
        """Compute scoring weights from category defaults + user preferences."""
        if category not in CATEGORY_DIMENSION_WEIGHTS:
            category = "other"
        base_weights = CATEGORY_DIMENSION_WEIGHTS[category]
        weights = dict(base_weights)

        if not preferences:
            # S3 L3 v2 (b) lever 2 — apply the value-weight scale on the anon path too.
            return _scale_value_weight(weights, category)

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

        # S3 L3 v2 (b) lever 2 — apply the value-weight scale (hatched, default no-op).
        return _scale_value_weight(weights, category)

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
        # B0-A v2.1: _score_specs may return None when scored_fields == 0
        # (zero coverage). Handle that path identically to the missing-
        # specs-dict path so dim-level aggregation propagates the missing
        # flag and the flag-aware tie guard fires uniformly.
        specs = product.get("specs")
        if specs and isinstance(specs, dict):
            spec_score = self._score_specs(specs, category)
            scores["spec_raw"] = spec_score
            if spec_score is None:
                scores["_spec_missing"] = True
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
        # B0-A v2: _score_reliability may return None when fact_check has
        # zero populated buckets — handle that path identically to the
        # missing-fact_check path (set _reliability_missing flag so
        # downstream dim-level aggregation correctly omits the dim).
        fact_check = product.get("fact_check")
        if fact_check and isinstance(fact_check, dict):
            reliability_score = self._score_reliability(fact_check)
            scores["reliability_raw"] = reliability_score
            if reliability_score is None:
                scores["_reliability_missing"] = True
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

    def _score_specs(self, specs: Dict[str, Any], category: str) -> Optional[float]:
        """Score specs on a 0-1 scale based on category-specific logic.

        B0-A v2.1 site #4: return None when scored_fields == 0 (zero
        coverage: empty specs dict OR all fields are 'N/A'/empty). Pre-
        v2.1 returned 0.0 which downstream `_normalize_dimension` then
        compared with `max_val == min_val == 0` — the v2 guard caught
        that case but it was fragile (e.g. partial-coverage equal-
        average scenarios still leaked at non-zero). Killing the 0.0
        default at the source means downstream sees None directly, sets
        `_spec_missing=True`, and the flag-aware tie guard fires
        uniformly.
        """
        schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
        # S2 I2.4 — strip verdict-awareness-only keys (e.g. heat_stability) so
        # they never affect coverage_ratio or the per-field tally. Keeps
        # deterministic scoring byte-identical to pre-S2 (design §4).
        schema_fields = [
            f for f in CATEGORY_SPEC_SCHEMAS[schema_key]
            if f not in NON_SCORING_SPEC_KEYS
        ]

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
            return None  # B0-A v2.1: was `return 0.0` — phantom-tie source.

        total_fields = len(schema_fields)
        coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0
        min_coverage = CATEGORY_MIN_COVERAGE.get(schema_key, 0.3)
        if coverage_ratio < min_coverage:
            penalty_factor = 0.5 + coverage_ratio
            return (total_score / scored_fields) * penalty_factor

        return total_score / scored_fields

    def _score_reliability(self, fact_check: Dict[str, Any]) -> Optional[float]:
        """Score reliability from fact_check data on 0-1 scale.

        B0-A v2 fix (2026-06-08): return None when fact_check has zero
        populated buckets so downstream MISSING_SCORE propagation +
        silent dim omission fire. Pre-v2 constant 0.5 default was the
        phantom (30,30) literal source surfaced by the 24-query bias
        re-run (B0-D root-cause investigation).
        """
        # Coerce None-valued bucket entries to 0 so `total` math is safe.
        verified = fact_check.get("specs_verified") or 0
        likely = fact_check.get("specs_likely") or 0
        flagged = fact_check.get("specs_flagged") or 0
        unverified = fact_check.get("specs_unverified") or 0
        total = verified + likely + flagged + unverified

        if total == 0:
            return None  # B0-A v2: was `return 0.5` — phantom (30,30) source.

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
        preferences: Optional[Dict[str, Any]] = None,
    ):
        """Normalize raw scores to category-specific dimensions on 0-100 scale.

        Bundle C § 4a: `preferences` is threaded through so the value-formula
        can apply priority-driven coefficients via _compute_value_score.

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

        # B0-A v2.1 site #3 — collapse tied non-MISSING reliability/popularity
        # scores to MISSING_SCORE. _normalize_direct writes the raw value
        # multiplied by 100 directly into the dim breakdown, bypassing the
        # _normalize_dimension flag-aware tie guard. When BOTH products land
        # on the same numeric (e.g. both reliability_raw=0.3 → 30.0), it's
        # a phantom from sparse-coverage fact_check averaging — NEVER a
        # genuine signal tie per B0-D's 24-query bias matrix evidence
        # (ZERO genuine non-MISSING ties observed across the corpus).
        # Collapse to MISSING_SCORE so downstream silent dim omission
        # (build_dimensions_v2 § A.4.9) fires uniformly.
        if (
            len(reliability_scores) >= 2
            and len(set(reliability_scores)) == 1
            and reliability_scores[0] != MISSING_SCORE
        ):
            reliability_scores = [MISSING_SCORE] * len(reliability_scores)
            for rs in raw_scores:
                rs["_reliability_missing"] = True
        if (
            len(popularity_scores) >= 2
            and len(set(popularity_scores)) == 1
            and popularity_scores[0] != MISSING_SCORE
        ):
            popularity_scores = [MISSING_SCORE] * len(popularity_scores)
            for rs in raw_scores:
                rs["_popularity_missing"] = True
        # B0-A v2.2 — extend the v2.1 array-level collapse to spec_scores.
        # _normalize_dimension's flag-aware tie guard only fires when both
        # sides have `_spec_missing=True` set on raw_scores; partial-coverage
        # extraction (both products have 1-2 spec fields populated that
        # average to the same value) yields matching non-zero spec_raw
        # WITHOUT setting _spec_missing → flag check passes → falls through
        # to `return 70.0` genuine-tie branch. Phase 2 live verification
        # (B0-D 24-query Q02 fashion/Q03 other/Q17 fashion) surfaced 3
        # residual (70,70) phantoms via this exact path. Same array-level
        # collapse semantic as reliability/popularity above: B0-D corpus
        # evidence shows zero genuine non-MISSING ties → tied-non-MISSING
        # === phantom. spec_secondary_scores below benefit transitively
        # since they're computed from the post-collapse spec_scores.
        if (
            len(spec_scores) >= 2
            and len(set(spec_scores)) == 1
            and spec_scores[0] != MISSING_SCORE
        ):
            spec_scores = [MISSING_SCORE] * len(spec_scores)
            for rs in raw_scores:
                rs["_spec_missing"] = True

        # Compute spec_secondary: blended spec and review for variety.
        # S3 L3 v2 [gate finding B — THIRD site] — gate missingness on the
        # EXPLICIT per-product `_spec_missing` / `_review_missing` flags, NOT
        # `== MISSING_SCORE` value-equality. A genuine 2.5★ rating normalizes
        # to EXACTLY 50.0 (== the sentinel) via _normalize_review's
        # `(rating-1)/4*80+20` band — value-equality dropped it as absent so the
        # spec_secondary dim fell back to spec-only (review contribution lost)
        # AND would later be mis-flagged missing. The flags are set whenever the
        # underlying raw signal is None (the only true missing path) plus the
        # array-collapse guards above, so they are the source of truth.
        spec_secondary_scores = []
        for i in range(len(raw_scores)):
            s = spec_scores[i]
            r = review_scores[i]
            s_missing = bool(raw_scores[i].get("_spec_missing"))
            r_missing = bool(raw_scores[i].get("_review_missing"))
            if s_missing and r_missing:
                spec_secondary_scores.append(MISSING_SCORE)
            elif s_missing:
                spec_secondary_scores.append(r)
            elif r_missing:
                spec_secondary_scores.append(s)
            else:
                spec_secondary_scores.append(round(s * 0.6 + r * 0.4, 1))

        # Value scores (tier-aware + Bundle C § 4a priority-driven coefficients).
        # `preferences.priorities` (first-match) selects the coefficient pair
        # from VALUE_FORMULA_BY_PRIORITY. When preferences is None, falls
        # back to the legacy default (0.60 spec / 0.40 price) → identical
        # output to pre-A.6.1 behavior.
        priorities = (preferences or {}).get("priorities") if preferences else None
        value_scores = [
            self._compute_value_score(
                spec_scores[i], price_scores[i], price_tiers[i],
                is_cross_tier_flag, priorities=priorities,
            )
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

                # S3 L3 v2 [gate finding B] — mark the dim missing from the
                # SOURCE-SIGNAL missing flags, NOT `== MISSING_SCORE` value-
                # equality. A legitimately computed 50.0 (rating 2.5★ →
                # _normalize_review=50.0; reliability/popularity 0.5 →
                # _normalize_direct=50.0) is a REAL score, not the sentinel —
                # value-equality flagged it missing → the dim got SUPPRESSED in
                # build_dimensions_v2 while the ratings were on screen. The
                # per-signal `_<sig>_missing` flags (set during signal
                # normalization + the array-collapse guards) are the source of
                # truth for missingness.
                if _signal_missing_for(raw_scores[i], signal):
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
        """Normalize a dimension score relative to competitors.

        B0-A BUG #2 fix (2026-06-08): when all raw signals are zero (no
        spec data was extracted across any product), return MISSING_SCORE
        so the downstream silent-omission path (build_dimensions_v2 §
        A.4.9) drops the dim rather than surfacing a phantom 70.0/70.0
        tie pair. The legacy `return 70.0` here was an unfinished
        placeholder — for genuine non-zero ties it represented a "draw",
        but the same path triggered for missing-signal cases (both
        `_score_specs` returning 0.0), producing the
        `('craft', 70.0, 70.0)`, `('durability', 30.0, 30.0)` literals
        seen in the 24-query bias audit.
        """
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
            # B0-A BUG #2 v1: distinguish "no signal extracted" (max==min==0)
            # from "genuine tied non-zero signal" (max==min==X, X>0). The
            # no-signal case must propagate MISSING_SCORE so silent dim
            # omission in build_dimensions_v2 fires; otherwise we'd ship a
            # fake 70/70 tie row.
            #
            # B0-A BUG #2 v2: extend v1 to also check per-product
            # `_<signal>_missing` flags. Partial-coverage extraction
            # scenarios (e.g. both products have 1 spec field populated,
            # _score_specs returns ~1.0 for both → max==min==1.0 > 0) fell
            # through to `return 70.0` in v1 — phantom (70,70) literal pair
            # surfaced by the 24-query bias re-run. Flag check catches it.
            signal_kind = key.replace("_raw", "")
            flag_key = f"_{signal_kind}_missing"
            both_sides_flagged_missing = all(
                rs.get(flag_key) for rs in raw_scores
            )
            if max_val == 0 or both_sides_flagged_missing:
                return MISSING_SCORE
            # S3 A1 — genuine non-missing tie returns the band midpoint (65
            # dampened / 70 legacy), NOT a manufactured extreme.
            return (
                _DIM_NORM_TIE_LEGACY if _dim_norm_dampening_disabled()
                else _DIM_NORM_TIE_DAMPENED
            )

        # Legacy hatch path: raw direction-only ratio + 30–100 spread (no
        # dampening, no magnitude-awareness — full legacy behavior).
        if _dim_norm_dampening_disabled():
            if higher_better:
                ratio = (current - min_val) / (max_val - min_val)
            else:
                ratio = (max_val - current) / (max_val - min_val)
            return round(_DIM_NORM_FLOOR_LEGACY + ratio * _DIM_NORM_SPAN_LEGACY, 1)

        # S3 L3 v2 — MAGNITUDE-AWARE ratio (lever 2) into the dampened 45–85 band
        # (lever 1). A tiny relative gap → ~0.5 (tie at the 65 midpoint); a real
        # gap opens scaled by the excess past the tolerance. Kills the "+0.02%
        # product gets a 40pt lead" noise while keeping genuine leads.
        ratio = _magnitude_aware_ratio(current, min_val, max_val, higher_better)
        return round(_DIM_NORM_FLOOR_DAMPENED + ratio * _DIM_NORM_SPAN_DAMPENED, 1)

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

    def _compute_value_score(
        self,
        spec_score: float,
        price_score: float,
        price_tier: str,
        is_cross_tier: bool,
        priorities=None,
    ) -> float:
        """Bundle C § 4a — delegate to module-level _compute_value_score so
        priority-driven coefficients (VALUE_FORMULA_BY_PRIORITY) replace the
        legacy hard-coded 0.6/0.4 split. Backwards-compat: priorities=None
        falls back to the default coefficients identical to the legacy
        formula, so all existing tests that don't pass priorities still
        produce the same number."""
        return _compute_value_score(
            spec_score, price_score, priorities=priorities,
            price_tier=price_tier, is_cross_tier=is_cross_tier,
        )

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

        # S3 L3 v2 (d) — determine missingness from the EXPLICIT missing_data
        # lists, NOT by `== MISSING_SCORE` value-equality. A legitimately computed
        # 50.0 (rating 2.5★ → 50.0; reliability/popularity 0.5 → 50.0) must count
        # as a REAL score, not be dropped as "missing". A dim is missing for a
        # product only when it's absent from the breakdown OR listed in that
        # product's missing_data.
        md0 = set(scores.get("product_0", {}).get("missing_data") or [])
        md1 = set(scores.get("product_1", {}).get("missing_data") or [])

        winners = {}
        for dim in dims:
            missing0 = dim not in b0 or dim in md0
            missing1 = dim not in b1 or dim in md1
            s0 = b0.get(dim, MISSING_SCORE)
            s1 = b1.get(dim, MISSING_SCORE)

            if missing0 and missing1:
                winners[dim] = {"winner": "N/A", "margin": None}
            elif missing0:
                winners[dim] = {"winner": product_names[1], "margin": None}
            elif missing1:
                winners[dim] = {"winner": product_names[0], "margin": None}
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
        """Bundle C § 5a — delegate to module-level compute_confidence.
        Legacy callers pass a single `shopping_count` kwarg; we feed it
        into the first product so the new per-product computation sees
        it. Result includes both the legacy {price, rating, specs}
        per-leg dicts AND the new {legs, overall} contract."""
        # Inject the legacy single shopping_count into the first product
        # so the new contract (per-product shopping_count) reads it.
        enriched = []
        for i, p in enumerate(products or []):
            if i == 0 and shopping_count and "shopping_count" not in p:
                enriched.append({**p, "shopping_count": shopping_count})
            else:
                enriched.append(p)
        return compute_confidence(enriched, cached=cached)

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

    def apply_cohort_adjustments(
        self,
        weights: Dict[str, float],
        cohort_profile: Optional[Dict[str, Any]],
        category: str = "other",
    ) -> Dict[str, float]:
        """S3 L3 v2 (c) — nudge the dimension weights toward the COHORT's inferred
        priorities, capped at ±10% of each dim's category weight (like behavioral
        — an inferred signal is weaker than an explicit ±30% preference). Reuses
        the CATEGORY_PRIORITY_ADJUSTMENTS mapping, scaled so the cohort nudge
        fits inside the ±10% cap (the priority deltas are sized for ±30%).
        No-op when cohort_profile is empty or has no priorities."""
        if not cohort_profile:
            return weights
        priorities = cohort_profile.get("priorities") or []
        if not priorities:
            return weights

        cat_priority_adj = CATEGORY_PRIORITY_ADJUSTMENTS.get(category, {})
        # Priority deltas are tuned for the ±30% explicit cap; scale to ±10% so
        # the inferred cohort signal lands within the behavioral band.
        scale = MAX_BEHAVIORAL_SHIFT_RATIO / MAX_WEIGHT_SHIFT_RATIO  # 0.10/0.30
        original = dict(weights)
        deltas: Dict[str, float] = {}
        for priority in priorities:
            for dim, delta in cat_priority_adj.get(priority, {}).items():
                if dim in weights:
                    deltas[dim] = deltas.get(dim, 0.0) + delta * scale

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


def calibrate_score(
    raw_score: float | None,
    raw_signals: list[float] | None = None,
    *,
    has_signal: bool = True,
) -> int | None:
    """Calibrate a raw 0–100 score into the [60, 95] honest display band.

    Bundle C § 2c (A.4.3): when `has_signal=False`, short-circuit to None
    so downstream A.4.9 silent-dim-omission can route missing-data dims
    through cleanly — no phantom 60-floor sneaks into the response.

    `raw_signals` (optional list of contributing raw values): when ALL
    fall below the honesty-guard threshold (40), the display is capped
    at 69 so weak-evidence comparisons never inflate above the
    'genuinely respectable' band.

    Backwards-compat: `has_signal=True` (the default) preserves the
    legacy int-returning behavior for every existing call site.
    """
    if not has_signal:
        return None
    if raw_score is None:
        # Defensive — has_signal=True but raw_score=None means a caller
        # forgot to pass has_signal=False. Default to the calibration
        # floor rather than crashing.
        return _CALIBRATION_FLOOR
    base = 70 + (raw_score - 50) * 0.5
    base = max(_CALIBRATION_FLOOR, min(_CALIBRATION_CEILING, base))
    display = int(round(base))
    if raw_signals and all(s < _HONESTY_GUARD_THRESHOLD for s in raw_signals):
        display = max(_CALIBRATION_FLOOR, min(_HONESTY_GUARD_CEILING, display))
    return display


# Bundle E § Decision 2 — self-describing dimensions[] contract.
# Always emits 3 core dims (price, reviews, value); 0..3 contextual.
# Never emits a dim where either product lacks the underlying data.
# (B0-B Item 3: dropped `_POPULARITY_MIN_REVIEW_COUNT = 50` — only the
# deleted `_dim_popularity` builder consumed it.)
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


# F2.4 tie threshold — kept identical to compute_dimension_winners (line ~1463)
# so the v2 per-dim winner and the legacy dimension_winners agree on what
# counts as a tie. Sub-threshold margins resolve to None (NOT a phantom
# winner — B0-A phantom-tie invariant).
_DIM_WINNER_TIE_MARGIN = 3.0


def _dim_winner(
    score_a,
    score_b,
    confidence: str | None = None,
    *,
    was_missing_a: bool = False,
    was_missing_b: bool = False,
) -> int | None:
    """Authoritative per-dimension winner index for the v2 dimensions tab.

    Returns 0 (product A wins this dim), 1 (product B wins), or None
    (tie / limited data). The frontend `Dimension.winner?: 0 | 1 | null`
    contract reads this directly instead of re-deriving from the bars.

    None when: either score is missing/MISSING_SCORE, confidence is "low"
    (limited-data rows must not declare a winner), EXACTLY ONE side's data
    was missing (S2 I3.5 — Decision B: crowning the real-score side over a
    MISSING side is false certainty — we don't know the other product on
    this dim), or the absolute margin is under the tie threshold.

    `was_missing_a`/`was_missing_b` are explicit per-side gap flags plumbed
    from the dim builders (more robust than sniffing the MISSING_SCORE=50
    sentinel, which can coincide with a legitimately calibrated 50).
    """
    if score_a is None or score_b is None:
        return None
    # S2 I3.5 — any side's data missing → no winner. Catches the asymmetric
    # one-sided case Decision B targets (the both-missing case was already
    # suppressed by the MISSING_SCORE-sentinel check below + upstream omission).
    if was_missing_a or was_missing_b:
        return None
    if score_a in (MISSING_SCORE,) and score_b in (MISSING_SCORE,):
        return None
    if confidence == "low":
        return None
    try:
        a = float(score_a)
        b = float(score_b)
    except (TypeError, ValueError):
        return None
    if abs(a - b) < _DIM_WINNER_TIE_MARGIN:
        return None
    return 0 if a > b else 1


def _dim_price(products: list[dict]) -> dict:
    a, b = products[0], products[1]
    pa, pb = _get_price(a) or 0.0, _get_price(b) or 0.0
    caption_key = None  # Bundle C § 2b A.4.4 — limited_data marker for missing-data path
    if pa <= 0 or pb <= 0:
        score_a = score_b = _NEUTRAL_DISPLAY_SCORE
        delta = "Price data unavailable"
        confidence = "low"
        caption_key = "limited_data"
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
    result = {
        "key": "price", "label": "Price",
        "score_a": score_a, "score_b": score_b,
        "delta_text": delta, "confidence": confidence, "is_core": True,
    }
    if caption_key:
        result["caption_key"] = caption_key
    return result


def _dim_reviews(products: list[dict]) -> dict:
    a, b = products[0], products[1]
    ra, rb = a.get("rating"), b.get("rating")
    # Non-numeric rating shapes (e.g. {} from upstream extraction) are missing data
    ra = ra if isinstance(ra, (int, float)) else None
    rb = rb if isinstance(rb, (int, float)) else None
    caption_key = None  # Bundle C § 2b A.4.4
    if ra is None or rb is None:
        score_a = score_b = _NEUTRAL_DISPLAY_SCORE
        delta = "Limited review data"
        confidence = "low"
        caption_key = "limited_data"
    else:
        score_a = calibrate_score(40 + ra * 10)
        score_b = calibrate_score(40 + rb * 10)
        diff = round(abs(ra - rb), 1)
        if diff == 0:
            delta = "Same rating"
        else:
            delta = f"{diff} stars higher"
        confidence = "high"
    result = {
        "key": "reviews", "label": "Reviews",
        "score_a": score_a, "score_b": score_b,
        "delta_text": delta, "confidence": confidence, "is_core": True,
    }
    if caption_key:
        result["caption_key"] = caption_key
    return result


def _dim_value(products: list[dict], is_cross_tier: bool = False) -> dict:
    """Bundle C § 2g — kill the `rating or 4.0` fabricated default. When
    either rating OR price is missing on either side, the value ratio
    cannot be computed honestly; short-circuit to a neutral display
    score + low-confidence flag (mirrors the _dim_price / _dim_reviews
    pattern at lines 1411 / 1438). No phantom 4.0 stars, no phantom
    0.1 ratio injection.

    Bundle D A.6.3: when `is_cross_tier=True` (price tiers disagree e.g.
    budget vs luxury), the delta_text gets a cross-tier prefix so the
    user understands the value math is happening across different
    market positions, not within the same tier.
    """
    a, b = products[0], products[1]
    pa_raw = _get_price(a)
    pb_raw = _get_price(b)
    ra = a.get("rating")
    rb = b.get("rating")
    # Non-numeric rating shapes (e.g. {} from upstream extraction) are missing data
    ra = ra if isinstance(ra, (int, float)) else None
    rb = rb if isinstance(rb, (int, float)) else None

    # Honest-fallback: if any side lacks price or rating, the value ratio
    # is undefined. Return neutral display score with low confidence so
    # downstream calibration + UI don't surface a fake winner.
    if pa_raw is None or pb_raw is None or ra is None or rb is None or pa_raw <= 0 or pb_raw <= 0:
        return {
            "key": "value", "label": "Value",
            "score_a": _NEUTRAL_DISPLAY_SCORE, "score_b": _NEUTRAL_DISPLAY_SCORE,
            "delta_text": "Limited value data",
            "confidence": "low", "is_core": True,
            # Bundle C § 2b A.4.4 — limited_data marker for the missing-data path
            "caption_key": "limited_data",
        }

    pa, pb = float(pa_raw), float(pb_raw)
    ra_f, rb_f = float(ra), float(rb)
    va = ra_f / pa
    vb = rb_f / pb
    hi = max(va, vb)
    if hi <= 0:
        # Defensive — both ratings zero or negative; should not happen for
        # real review data but keeps the function total.
        return {
            "key": "value", "label": "Value",
            "score_a": _NEUTRAL_DISPLAY_SCORE, "score_b": _NEUTRAL_DISPLAY_SCORE,
            "delta_text": "Limited value data",
            "confidence": "low", "is_core": True,
            # Bundle C § 2b A.4.4 — limited_data marker for the missing-data path
            "caption_key": "limited_data",
        }
    score_a = calibrate_score(50 + 35 * (va / hi))
    score_b = calibrate_score(50 + 35 * (vb / hi))
    # Bundle D Task 2.B.5 (A.6.2) — richer delta_text. Vary copy by
    # magnitude of value-ratio gap so the user sees more than 2 hardcoded
    # strings. Magnitude buckets (relative): tiny (<5%), small (5-15%),
    # moderate (15-35%), large (>35%).
    if va == vb:
        delta = "Comparable value"
    else:
        winner_va = va > vb
        gap_ratio = abs(va - vb) / hi  # 0..1
        if gap_ratio < 0.05:
            delta = "Nearly identical value"
        elif gap_ratio < 0.15:
            # L1.4 — banned-word audit: "better" is on the test_dimensions_builder
            # banned list. Rephrase using the same factual register as the
            # other gap-ratio buckets ("Noticeably more...", "Substantially
            # stronger...").
            delta = (
                "Slightly higher value here"
                if winner_va else "Slightly higher value on the other side"
            )
        elif gap_ratio < 0.35:
            delta = (
                "Noticeably more per dinar here"
                if winner_va else "Noticeably more per dinar on the other side"
            )
        else:
            delta = (
                "Substantially stronger value ratio"
                if winner_va else "Substantially stronger value on the other side"
            )
    # Bundle D A.6.3 — cross-tier framing prefix. When the two products
    # sit in different price tiers (budget vs mid vs premium vs luxury vs
    # top_tier), the value-ratio comparison is happening across market
    # positions, not within one tier. Prefix the delta so the user
    # understands the framing.
    if is_cross_tier and delta != "Comparable value":
        delta = f"Across tiers — {delta.lower()[0]}{delta[1:]}" if delta else delta
    return {
        "key": "value", "label": "Value",
        "score_a": score_a, "score_b": score_b,
        "delta_text": delta, "confidence": "medium", "is_core": True,
        # Bundle D A.6.3 — expose cross-tier flag on the dim so FE can
        # render a different visual treatment if desired (caption, icon,
        # etc.). is_cross_tier on the parent scoring_result is also still
        # available; this is just a per-dim convenience flag.
        "is_cross_tier": bool(is_cross_tier),
    }


# B0-B Item 3 (audit MED #1) — the hand-coded `_dim_dpi`, `_dim_popularity`,
# and `_dim_build_quality` builders previously sat here. They were never
# called from `build_dimensions_v2` (Lane 1 L1.3 rewrite, line ~2255 below
# routes ALL same-category comparisons through the CATEGORY_DIMENSIONS
# lookup). `_dim_dpi` was also a latent AttributeError risk — it called
# `a.get("specs", {}).get("dpi")` which crashes when specs=None post the
# L2 timeout contract. Existing regression tests (test_dimensions_builder
# and test_scoring_dimensions_v2) already pin that the `dpi`, `popularity`,
# and `build_quality` keys must NOT appear in `build_dimensions_v2` output,
# so deleting the dead definitions is safe.


# Bundle D Task 2.B.3 (A.8.1) — human-readable labels for the
# category-specific dim keys in CATEGORY_DIMENSIONS. Each category's
# per-dim scores are projected from `scoring_result["scores"]` via the
# generic `_dim_from_category_lookup` adapter using these labels.
_DIMENSION_LABELS = {
    # electronics (also exposed for other paths that may render them)
    "performance_score": "Performance",
    "value_score": "Value",
    "build_quality_score": "Build quality",
    "feature_score": "Features",
    "ecosystem_score": "Ecosystem",
    "futureproof_score": "Future-proofing",
    # grocery
    "nutrition_score": "Nutrition",
    "ingredient_score": "Ingredients",
    "taste_score": "Taste",
    "serving_value_score": "Serving value",
    "dietary_score": "Dietary fit",
    "availability_score": "Availability",
    # supplements
    "efficacy_score": "Efficacy",
    "safety_score": "Safety",
    "dosage_score": "Dosage",
    "form_score": "Form",
    "trust_score": "Trust",
    # makeup
    "shade_score": "Shade range",
    "longevity_score": "Longevity",
    "skin_compat_score": "Skin compatibility",
    "finish_score": "Finish",
    "ingredient_safety_score": "Ingredient safety",
    "perf_value_score": "Performance vs value",
    # skincare
    "actives_score": "Active ingredients",
    "evidence_score": "Evidence",
    "formulation_score": "Formulation",
    "sensory_score": "Sensory",
    "results_value_score": "Results vs value",
    # haircare
    "hair_match_score": "Hair match",
    "results_score": "Results",
    "scent_score": "Scent",
    "multi_value_score": "Multi-use value",
    "scalp_score": "Scalp",
    # fragrances
    "character_score": "Character",
    "projection_score": "Projection",
    "versatility_score": "Versatility",
    "wear_value_score": "Wear value",
    "presentation_score": "Presentation",
    # fashion
    "craft_score": "Craftsmanship",
    "fit_score": "Fit",
    "style_score": "Style",
    "durability_score": "Durability",
    "heritage_score": "Heritage",
    "cpw_score": "Cost per wear",
    # other
    "function_score": "Function",
    "build_score": "Build",
    "review_score": "Reviews",
    "reliability_score": "Reliability",
    "feature_match_score": "Feature match",
}


def _dim_from_category_lookup(
    dim_key: str,
    scoring_result: dict,
    products_data: list[dict] | None = None,
) -> dict | None:
    """Lane 1 L1.3 — generic dim builder driven by CATEGORY_DIMENSIONS.

    Projects the per-dim score from `scoring_result["scores"]["product_i"]
    ["breakdown"][dim_key]`. (Bug fix: previously read
    `scores.product_i[dim_key]` which never resolves; the live shape nests
    breakdowns under a `breakdown` sub-dict — verified against the
    iphone15_vs_galaxys24, tomford_vs_creed, and now_vs_solgar prod
    captures used by the Lane 1 fixtures.)

    Emits with the `_score` suffix stripped from the dim key so the
    frontend renders `performance` / `longevity` / `efficacy` rather than
    `performance_score` / `longevity_score` / `efficacy_score`.

    Returns None when both products have MISSING_SCORE — same silent-
    omission contract as the hand-coded `_dim_X` builders.
    """
    scores_map = scoring_result.get("scores", {}) or {}
    a_score_dict = scores_map.get("product_0", {}) or {}
    b_score_dict = scores_map.get("product_1", {}) or {}

    # Bundle E Lane 1 — the live structure is
    # `scores.product_i.breakdown.<dim>_score`; fall back to the flat layout
    # for legacy fixtures that pre-date the breakdown wrap.
    a_breakdown = a_score_dict.get("breakdown") or {}
    b_breakdown = b_score_dict.get("breakdown") or {}
    score_a = a_breakdown.get(dim_key)
    if score_a is None:
        score_a = a_score_dict.get(dim_key)
    score_b = b_breakdown.get(dim_key)
    if score_b is None:
        score_b = b_score_dict.get(dim_key)

    # S3 L3 v2 [gate finding B — SECOND site] — determine missingness from the
    # EXPLICIT per-product `missing_data` list (the producer's source of truth)
    # + a genuinely-absent breakdown value (score is None), NEVER `==
    # MISSING_SCORE` value-equality. A legitimately computed 50.0 (rating 2.5★ →
    # _normalize_review=50.0; reliability/popularity 0.5 → _normalize_direct=
    # 50.0) is a REAL score — value-equality flagged it 'was missing' so
    # build_dimensions_v2's one-sided-missing suppression (Decision B) hid its
    # winner while the rating was on screen. `dim_key` here is the full
    # CATEGORY_DIMENSIONS key (with `_score` suffix), exactly the form stored in
    # missing_data (see compute_scores: `missing_dims = [dim for dim in dims ...]`).
    #
    # Legacy/synthetic shape (no `missing_data` key at all) predates the list and
    # still uses the sentinel VALUE as the gap marker — distinguish "key present
    # & None" (real: no gaps) from "key absent" (legacy) via the _ABSENT sentinel
    # so the real no-gap path never falls back to value-equality. Mirror the
    # reconciliation in count_missing_dim_cells.
    _ABSENT = object()

    def _was_missing(score, score_dict) -> bool:
        if score is None:
            return True  # genuinely absent from the breakdown
        md = score_dict.get("missing_data", _ABSENT)
        if md is not _ABSENT:
            return dim_key in (md or ())  # authoritative real shape
        return score == MISSING_SCORE  # legacy/synthetic fallback

    was_missing_a = _was_missing(score_a, a_score_dict)
    was_missing_b = _was_missing(score_b, b_score_dict)

    # Both missing → silent omission per § 2h
    if was_missing_a and was_missing_b:
        return None

    label = _DIMENSION_LABELS.get(dim_key, dim_key.replace("_score", "").replace("_", " ").title())
    # L1.3: emit user-friendly key without the `_score` suffix
    public_key = dim_key[:-6] if dim_key.endswith("_score") else dim_key
    return {
        "key": public_key,
        "label": label,
        "score_a": score_a,
        "score_b": score_b,
        # L1.4 composes richer delta_text per category; until then keep
        # the value minimal (per-row spec winner + bar chart already
        # carry the visual signal).
        "delta_text": _compose_delta_text(public_key, products_data or [], score_a, score_b),
        "confidence": "medium",
        "is_core": False,
        "was_missing_a": was_missing_a,
        "was_missing_b": was_missing_b,
    }


def _compose_delta_text(
    dim_key: str,
    products: list[dict],
    score_a,
    score_b,
) -> str:
    """L1.4 — best-effort category-aware delta phrase. Falls back to a
    score-margin summary when no concrete spec hook fires.

    Honours the FIVE critical rules (no scary copy, no backend internals,
    no `estimated` leakage). Strings are short + presentational so the
    bar-chart caption stays readable on narrow phones.
    """
    # S3 L3 v2 [gate finding B] — bail only on a genuinely-absent value (None),
    # NOT on a real computed 50.0 (== MISSING_SCORE value-equality would blank
    # the caption for an honest middling score).
    if score_a is None or score_b is None:
        return ""
    try:
        margin = abs(float(score_a) - float(score_b))
    except (TypeError, ValueError):
        return ""
    if margin < 1.0:
        return "Comparable"
    if len(products) < 2:
        return f"+{margin:.0f}pt edge"

    p0_specs = (products[0] or {}).get("specs") or {}
    p1_specs = (products[1] or {}).get("specs") or {}

    def _winner_side() -> int:
        return 0 if float(score_a) > float(score_b) else 1

    # --- Electronics ----------------------------------------------------
    if dim_key == "performance":
        # Battery life is the most common driver. Fall back to RAM/storage.
        ba = p0_specs.get("battery_hours_estimated") or p0_specs.get("battery_life_hours")
        bb = p1_specs.get("battery_hours_estimated") or p1_specs.get("battery_life_hours")
        if ba and bb:
            try:
                bf_a, bf_b = float(ba), float(bb)
                if bf_a and bf_b:
                    pct = round(abs(bf_a - bf_b) / max(bf_a, bf_b) * 100)
                    return f"+{pct}% battery life" if pct >= 5 else f"+{margin:.0f}pt"
            except (TypeError, ValueError):
                pass
        return f"+{margin:.0f}pt performance"
    if dim_key == "build_quality":
        wa, wb = p0_specs.get("warranty_years"), p1_specs.get("warranty_years")
        if wa and wb:
            try:
                if float(wa) != float(wb):
                    side = "longer" if (float(wa) > float(wb)) == (_winner_side() == 0) else "longer"
                    return f"{max(float(wa), float(wb)):.0f}-year warranty {side}"
            except (TypeError, ValueError):
                pass
    if dim_key == "feature":
        return f"+{margin:.0f}pt features"
    if dim_key == "ecosystem":
        return f"+{margin:.0f}pt ecosystem"
    if dim_key == "futureproof":
        return f"+{margin:.0f}pt longevity outlook"

    # --- Fragrances -----------------------------------------------------
    if dim_key == "longevity":
        la = p0_specs.get("longevity") or p0_specs.get("longevity_hours")
        lb = p1_specs.get("longevity") or p1_specs.get("longevity_hours")
        if la and lb:
            ha = _extract_hours(la)
            hb = _extract_hours(lb)
            if ha and hb:
                return f"{int(max(ha, hb))}h vs {int(min(ha, hb))}h"
        return f"+{margin:.0f}pt longevity"
    if dim_key == "projection":
        pa, pb = p0_specs.get("projection"), p1_specs.get("projection")
        if pa and pb:
            return f"{pa} vs {pb}"
        return f"+{margin:.0f}pt projection"
    if dim_key == "character":
        return f"+{margin:.0f}pt distinctiveness"
    if dim_key == "versatility":
        return f"+{margin:.0f}pt versatility"
    if dim_key == "presentation":
        return f"+{margin:.0f}pt presentation"
    if dim_key == "wear_value":
        return f"+{margin:.0f}pt value per wear"

    # --- Supplements ----------------------------------------------------
    if dim_key == "dosage":
        ai_a = (p0_specs.get("active_ingredient") or "").strip()
        ai_b = (p1_specs.get("active_ingredient") or "").strip()
        if ai_a and ai_b:
            dose_a = _extract_dose(ai_a)
            dose_b = _extract_dose(ai_b)
            if dose_a and dose_b and dose_a != dose_b:
                hi = max(dose_a, dose_b)
                lo = min(dose_a, dose_b)
                # L4 cross-QA nit (2026-06-08): the previous `×` framing
                # ("5000× dose vs 1000×") read as a multiplier of the raw
                # IU dose, which is wrong. Render the unit when we can
                # detect it (IU / mg / mcg / g); else fall back to a
                # multiplier-only phrasing ("5× higher dose") that's
                # unambiguous.
                unit = _extract_dose_unit(ai_a) or _extract_dose_unit(ai_b)
                if unit:
                    return f"{hi:g} {unit} vs {lo:g} {unit}"
                multiplier = hi / lo if lo > 0 else 0
                if multiplier >= 1.5:
                    return f"{multiplier:.1f}× higher dose"
                return f"{hi:g} vs {lo:g} per serving"
        return f"+{margin:.0f}pt dosage"
    if dim_key == "efficacy":
        return f"+{margin:.0f}pt efficacy signal"
    if dim_key == "safety":
        return f"+{margin:.0f}pt safety profile"
    if dim_key == "serving_value":
        return f"+{margin:.0f}pt per-serving value"
    if dim_key == "form":
        fa, fb = p0_specs.get("form"), p1_specs.get("form")
        if fa and fb and fa != fb:
            return f"{fa} vs {fb}"
        return f"+{margin:.0f}pt form factor"
    if dim_key == "trust":
        return f"+{margin:.0f}pt brand trust"

    # --- Skincare / makeup / haircare / fashion / grocery / other ------
    # Wave-2 idle-time fix (2026-06-08): the previous bare "+28pt" fallback
    # rendered identically across 28 dim×category cells, making the design
    # cards look like stubbed copy. Append the dim label so the user sees
    # "+28pt nutrition", "+28pt craft", "+28pt actives", etc.
    generic_label = _DIM_LABEL_FALLBACKS.get(dim_key)
    if generic_label:
        return f"+{margin:.0f}pt {generic_label}"
    return f"+{margin:.0f}pt"


# Wave-2 fallback labels for the dim keys whose `_compose_delta_text`
# branches above don't have category-specific copy. Covers the 28 cells
# across grocery (5) / makeup (5) / skincare (6) / haircare (6) /
# fashion (6) / other (6). Ordering aligns with CATEGORY_DIMENSIONS.
_DIM_LABEL_FALLBACKS = {
    # --- electronics (build_quality fall-through when no warranty data) --
    "build_quality": "build quality",
    # --- grocery --------------------------------------------------------
    "nutrition": "nutrition",
    "ingredient": "ingredients",
    "taste": "taste",
    "dietary": "dietary fit",
    "availability": "availability",
    # --- makeup ---------------------------------------------------------
    "shade": "shade range",
    "skin_compat": "skin compatibility",
    "finish": "finish",
    "ingredient_safety": "ingredient safety",
    "perf_value": "performance value",
    # --- skincare -------------------------------------------------------
    "actives": "active ingredients",
    "evidence": "evidence",
    # skin_compat already covered above (shared with makeup)
    "formulation": "formulation",
    "sensory": "sensory",
    "results_value": "results value",
    # --- haircare -------------------------------------------------------
    "hair_match": "hair match",
    "results": "results",
    # ingredient already covered above (shared with grocery)
    "scent": "scent",
    "multi_value": "multi-use value",
    "scalp": "scalp",
    # --- fashion --------------------------------------------------------
    "craft": "craftsmanship",
    "fit": "fit",
    "style": "style",
    "durability": "durability",
    "heritage": "heritage",
    "cpw": "cost per wear",
    # --- other ----------------------------------------------------------
    "function": "function",
    "build": "build",
    "review": "reviews",
    # `value` is reserved by the core _dim_value builder — skip
    "reliability": "reliability",
    "feature_match": "feature match",
}


def _extract_hours(value) -> float | None:
    """Pull the first numeric value (assumed hours) out of strings like
    `'8 hours'`, `'6-8h'`, or pre-numeric values. Returns None on no match."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _extract_dose(value) -> float | None:
    """Pull the first numeric dose value (IU, mg, mcg) out of a label like
    `'Vitamin D3 1000 IU'`. Falls back to plain numeric. Returns None on
    no match."""
    if not isinstance(value, str):
        return None
    match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:IU|mg|mcg|g)\b", value, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", "."))
    match = re.search(r"(\d+(?:[\.,]\d+)?)", value)
    return float(match.group(1).replace(",", ".")) if match else None


def _extract_dose_unit(value) -> str | None:
    """L4 cross-QA fix — pair with `_extract_dose` to render
    user-friendly delta_text. Returns the unit string with canonical
    casing (`'IU'`, `'mg'`, `'mcg'`, `'g'`) or None on no match."""
    if not isinstance(value, str):
        return None
    match = re.search(r"\d+(?:[\.,]\d+)?\s*(IU|mg|mcg|g)\b", value, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1)
    # Canonical casing: IU upper, mg/mcg/g lower
    return "IU" if raw.upper() == "IU" else raw.lower()


def build_dimensions_v2(
    products_data: list[dict],
    scoring_result: dict,
    category: str,
) -> list[dict]:
    """Build the v2 dimensions tab — 3 core dims (price/reviews/value) +
    up to 3 category-specific dims sourced from CATEGORY_DIMENSIONS.

    Lane 1 L1.3 (Bundle E): drop the electronics-only hand-coded extras
    (`_dim_dpi`, `_dim_popularity`, `_dim_build_quality`) and route ALL
    same-category comparisons through the CATEGORY_DIMENSIONS lookup so
    every category surfaces its own per-dim breakdown. Prod regression
    (2026-06-03): every category emitted only `['price','reviews','value']`
    or `['price','reviews','value','popularity']` because
    `_dim_from_category_lookup` read the wrong path inside `scoring_result`.
    """
    # Bundle D A.6.3 — pass is_cross_tier so _dim_value can prefix its
    # delta_text with cross-tier framing when products span price tiers.
    is_cross_tier = bool(scoring_result.get("is_cross_tier", False))
    dims: list[dict] = [
        _dim_price(products_data),
        _dim_reviews(products_data),
        _dim_value(products_data, is_cross_tier=is_cross_tier),
    ]
    cat_a = products_data[0].get("category")
    cat_b = products_data[1].get("category")
    same_category = cat_a == cat_b and cat_a is not None
    if same_category and category in CATEGORY_DIMENSIONS:
        # CATEGORY_DIMENSIONS[category] is exactly 6 keys; pick the first
        # 5 that aren't already covered by the core price/reviews/value
        # builders so the v2 tab caps at 8 rows total (3 core + 5
        # contextual). S2 I3.4 (Decision A, 2026-06-11) raised the cap
        # 6→8 so electronics surfaces ecosystem + futureproof rows.
        core_covered = {"price", "value", "reviews"}
        added = 0
        for dim_key in CATEGORY_DIMENSIONS[category]:
            if added >= 5:
                break
            # Strip the `_score` suffix to compare against the core keys.
            public = dim_key[:-6] if dim_key.endswith("_score") else dim_key
            if public in core_covered:
                continue
            if any(c in dim_key for c in ("value_", "_value_")):
                # Category-specific value proxies (e.g. perf_value_score,
                # serving_value_score) are already represented by _dim_value.
                continue
            dim = _dim_from_category_lookup(dim_key, scoring_result, products_data)
            if dim is not None:
                dims.append(dim)
                added += 1
    # Bundle C § 2h A.4.9 — silent dim omission. Any dim that escapes
    # an upstream builder with score_a is None AND score_b is None gets
    # silently omitted here so the frontend never sees a phantom row.
    dims = [
        d for d in dims
        if not (d.get("score_a") is None and d.get("score_b") is None)
    ]
    # F2.4 — emit the authoritative per-dim winner (0 | 1 | None) the
    # frontend Dimension.winner contract expects. No `_dim_*` builder set
    # this, so on prod every scoring_v2.dimensions[i].winner was None and
    # DimensionBars fell back to a score heuristic. Derive it from each
    # dim's own scores + confidence, sub-threshold → None (no phantom tie).
    # S2 I3.5 — pass the per-side was_missing markers (set by
    # _dim_from_category_lookup; absent → False for the core builders, which
    # already gate missing data via confidence='low') so a one-sided-missing
    # dim never crowns a winner (Decision B: no false certainty).
    for d in dims:
        d["winner"] = _dim_winner(
            d.get("score_a"),
            d.get("score_b"),
            d.get("confidence"),
            was_missing_a=bool(d.get("was_missing_a", False)),
            was_missing_b=bool(d.get("was_missing_b", False)),
        )
        # Internal-only markers — strip before the dict ships in the response
        # so the frontend Dimension contract stays clean (winner already
        # encodes the suppression decision).
        d.pop("was_missing_a", None)
        d.pop("was_missing_b", None)
    return dims[:8]


def count_missing_dim_cells(
    scoring_result: dict,
    category: str,
) -> dict:
    """S2 I3.6 — count the MISSING_SCORE dimension cells across BOTH
    products' per-dim breakdowns. The KPI dial for Ahmed's Decision B
    ("no missing data, no false certainty"): the Tier-3 spec-synthesis
    fallback FILLS gaps and the render suppression HIDES one-sided ones,
    but neither is measurable unless the gaps are counted.

    Counts the genuine data gap BEFORE display omission — build_dimensions_v2
    silently drops both-sided-missing dims, so counting the post-omission
    dimensions[] would under-report. Mirrors compute_dimension_winners'
    dim selection + `breakdown.get(dim, MISSING_SCORE)` default exactly so
    a "missing cell" here is the same gap that surfaces as a winner of
    "N/A" there.

    Returns {"count": int, "total": int, "fraction": float}.
    `total` is len(dims) * 2 (both products); `fraction` is count/total,
    0.0 when total == 0 (fewer than 2 products, or empty result).
    """
    scores = (scoring_result or {}).get("scores", {}) or {}
    b0_dict = scores.get("product_0") or {}
    b1_dict = scores.get("product_1") or {}
    # Fewer than 2 products → no cells to examine.
    if not b0_dict or not b1_dict:
        return {"count": 0, "total": 0, "fraction": 0.0}

    cat = category if category in CATEGORY_DIMENSIONS else "other"
    b0 = b0_dict.get("breakdown", {}) or {}
    b1 = b1_dict.get("breakdown", {}) or {}

    dims = CATEGORY_DIMENSIONS[cat]
    # Same fallback as compute_dimension_winners: if the breakdown keys
    # don't match the category dims, examine whatever keys are present so a
    # mis-tagged category still measures real gaps.
    if b0 and not any(d in b0 for d in dims):
        dims = list(b0.keys())

    # S3 L3 v2 [gate finding B — FOURTH site] — when the product carries an
    # explicit `missing_data` list (the real compute_scores shape), it is the
    # AUTHORITATIVE gap source. A breakdown value of EXACTLY 50.0 that is NOT in
    # missing_data is a genuine score (2.5★ review → _normalize_review=50.0; 0.5
    # reliability/popularity → _normalize_direct=50.0), NOT a gap — counting it
    # via `== MISSING_SCORE` value-equality INFLATED this very KPI dial that
    # Ahmed reads for "no missing data, no false certainty". Fall back to
    # value-equality + key-absence only for the legacy/synthetic shape that
    # predates missing_data (preserves the existing synthetic-result contract).
    # Distinguish "key present and None" (real shape: no gaps) from "key absent"
    # (legacy/synthetic shape) via a sentinel default — they would both read as
    # None otherwise and the real no-gap case would wrongly fall back to value-
    # equality. In the real compute_scores shape `missing_data` is ALWAYS a key
    # (a list, or None when no dim was missing); the legacy synthetic shape omits
    # it entirely.
    _ABSENT = object()
    md0 = b0_dict.get("missing_data", _ABSENT)
    md1 = b1_dict.get("missing_data", _ABSENT)

    def _cell_missing(breakdown: dict, md, dim: str) -> bool:
        if md is not _ABSENT:
            # Authoritative (real shape, md is a list or None): flagged missing,
            # OR genuinely absent from the breakdown. A present 50.0 not in the
            # list is a REAL score, never a gap.
            md_set = md or ()
            return (dim in md_set) or (dim not in breakdown)
        # Legacy/synthetic (no missing_data key): the sentinel value / key-absence.
        return breakdown.get(dim, MISSING_SCORE) == MISSING_SCORE

    count = 0
    for dim in dims:
        if _cell_missing(b0, md0, dim):
            count += 1
        if _cell_missing(b1, md1, dim):
            count += 1

    total = len(dims) * 2
    fraction = (count / total) if total else 0.0
    return {"count": count, "total": total, "fraction": round(fraction, 4)}

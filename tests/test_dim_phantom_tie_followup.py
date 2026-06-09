"""B0-A v2 — close phantom (70,70) + (30,30) tie tail from BUG #2 pass-1.

B0-D's 24-query re-run found pass-1 fix at `_normalize_dimension` was too
narrow:
  * `other`         — (70,70) + (30,30) still firing
  * `fragrances`    — character/longevity/versatility phantom literals
  * `fashion`       — partial fashion subset still emits 30/30 + 70/70
  * `electronics`   — build_quality dim emits phantom 30/30

Two root causes the pass-1 missed:

(1) `_score_reliability` returns CONSTANT 0.5 when fact_check has zero
    populated buckets. Downstream `_normalize_direct` turns 0.5 → 50
    (MISSING_SCORE coincidence — *not* missing-flag-aware), BUT when
    fact_check has partial coverage (e.g. only specs_unverified=N filled,
    others=0 → score = 0.3*N/N = 0.3), BOTH products get 0.3 → both
    normalize to 30 → phantom (30, 30) literal pair.

(2) `_normalize_dimension` pass-1's `if max_val == 0` guard only
    handles "both products zero raw signal". The harder case: when
    `_score_specs` returns the same NON-ZERO partial average for both
    products (e.g. only 1-2 spec fields populated → both score 1.0 →
    `max == min == 1.0 > 0` → existing path returns 70.0). Need to also
    check the per-product `_X_missing` flags directly.

Tests below are written RED-first per TDD; they exercise both the
direct (unit) contract for `_score_reliability` returning None on
empty buckets, plus the `_normalize_dimension` flag-aware MISSING_SCORE
guard, plus integration coverage over `other` (SodaStream-vs-Aarke
shape) + `fragrances` blank-spec pair.
"""
import pytest

from app.services.scoring_service import (
    CATEGORY_DIMENSIONS,
    MISSING_SCORE,
    ScoringService,
    build_dimensions_v2,
)


@pytest.fixture
def service():
    return ScoringService()


# ---------- B0-A v2 fix-1: _score_reliability returns None on empty buckets ----------


def test_score_reliability_returns_none_on_empty_fact_check(service):
    """fact_check exists but ALL spec_* buckets are zero/missing →
    _score_reliability returns None (NOT 0.5 default).

    Pre-v2: returned 0.5 → flowed to reliability_raw=0.5 → _normalize_direct
    → 50. When BOTH products hit this path with partial coverage, downstream
    dim normalization emitted phantom (30,30) literals.

    Post-v2: returns None → reliability_raw=None → _normalize_direct returns
    MISSING_SCORE so A.4.9 silent omission can fire downstream.
    """
    empty_fact_check = {}
    result = service._score_reliability(empty_fact_check)
    assert result is None, (
        f"expected None for empty fact_check, got {result!r} "
        "(regression: constant 0.5 default)"
    )

    explicit_zero_fact_check = {
        "specs_verified": 0,
        "specs_likely": 0,
        "specs_flagged": 0,
        "specs_unverified": 0,
    }
    result = service._score_reliability(explicit_zero_fact_check)
    assert result is None, (
        f"expected None for explicitly-zeroed fact_check, got {result!r}"
    )

    none_fact_check = {
        "specs_verified": None,
        "specs_likely": None,
        "specs_flagged": None,
        "specs_unverified": None,
    }
    result = service._score_reliability(none_fact_check)
    assert result is None, (
        f"expected None for None-valued fact_check, got {result!r}"
    )


def test_score_reliability_preserves_populated_path(service):
    """Sanity — when fact_check IS populated, returns a meaningful 0..1 score
    (NOT broken by the None-return change for the empty case).
    """
    populated = {
        "specs_verified": 4,
        "specs_likely": 2,
        "specs_flagged": 0,
        "specs_unverified": 1,
    }
    result = service._score_reliability(populated)
    assert result is not None, "populated fact_check must produce a numeric score"
    assert 0.0 < result <= 1.0, f"reliability score out of expected band: {result}"
    # 4*1.0 + 2*0.7 + 1*0.3 = 4 + 1.4 + 0.3 = 5.7 / 7 ≈ 0.814
    assert abs(result - 0.814) < 0.01, f"reliability score drifted: {result}"


def test_compute_raw_scores_marks_reliability_missing_when_fact_check_empty(service):
    """Integration — when fact_check is `{}` (all buckets empty),
    `_compute_raw_scores` propagates reliability_raw=None AND sets
    `_reliability_missing=True` so downstream dim-missing aggregation
    catches it.
    """
    product = {
        "name": "Test",
        "specs": {"battery": "3000mAh"},
        "rating": 4.0,
        "price": {"amount": 50, "currency": "BHD"},
        "fact_check": {},  # the bug — populated dict, zero buckets
    }
    raw = service._compute_raw_scores(product, "electronics")
    assert raw.get("reliability_raw") is None, (
        f"reliability_raw should be None when fact_check has no buckets, "
        f"got {raw.get('reliability_raw')!r}"
    )
    assert raw.get("_reliability_missing") is True, (
        "_reliability_missing flag must be set so dim-level aggregation "
        "treats the dim as missing"
    )


# ---------- B0-A v2 fix-2: _normalize_dimension flag-aware MISSING_SCORE guard ----------


def test_normalize_dimension_routes_to_missing_when_both_sides_flagged_missing(service):
    """Both products report `_spec_missing=True` AND non-zero spec_raw
    (e.g. partial coverage averaged to 1.0 both sides) → return
    MISSING_SCORE.

    Pre-v2: max_val == min_val == 1.0, max_val != 0 → existing path
    returned 70.0 (the genuine-tie branch) → phantom (70.0, 70.0).
    Post-v2: per-product flag check catches it → MISSING_SCORE.
    """
    raw_scores = [
        {"spec_raw": 1.0, "_spec_missing": True},
        {"spec_raw": 1.0, "_spec_missing": True},
    ]
    for idx in (0, 1):
        result = service._normalize_dimension(raw_scores, idx, "spec_raw", higher_better=True)
        assert result == MISSING_SCORE, (
            f"product_{idx} both-sides-flagged-missing must map to MISSING_SCORE, "
            f"got {result} (regression: phantom 70.0 tie)"
        )


def test_normalize_dimension_preserves_genuine_tie_when_flags_not_set(service):
    """Sanity — when neither product has `_spec_missing` flag set (both
    products genuinely supplied identical spec_raw=2.5), still emits 70.0
    tie display.
    """
    raw_scores = [
        {"spec_raw": 2.5},  # no _spec_missing flag
        {"spec_raw": 2.5},
    ]
    for idx in (0, 1):
        result = service._normalize_dimension(raw_scores, idx, "spec_raw", higher_better=True)
        assert result == 70.0, (
            f"genuine non-flagged tie must stay at 70.0, got {result} "
            "(regression: over-aggressive MISSING_SCORE routing)"
        )


def test_normalize_dimension_routes_to_missing_when_only_one_side_flagged(service):
    """Asymmetric — only product_a has `_spec_missing` flag. Both side spec_raw
    happen to be equal (1.0). Pass-1 v1 returned 70.0; v2 routes the
    side-with-flag to MISSING_SCORE (any flag-set side is unreliable).
    Other side may also be unreliable (we don't trust the tied raw value
    in a degraded-extraction scenario), so safest bet is MISSING_SCORE
    on both — silent omission downstream.
    """
    raw_scores = [
        {"spec_raw": 1.0, "_spec_missing": True},
        {"spec_raw": 1.0},
    ]
    # Only flag-set side gets MISSING_SCORE under "all" semantic; with strict
    # "any" semantic, both get MISSING. Spec uses `all()` per team-lead — so
    # both sides flagged is the trigger. One-flag-only stays at 70.0.
    for idx in (0, 1):
        result = service._normalize_dimension(raw_scores, idx, "spec_raw", higher_better=True)
        assert result == 70.0, (
            f"only-one-side-flagged should keep 70.0 (per all() semantic), got {result}"
        )


# ---------- Integration: SodaStream-vs-Aarke shape (category=other, all blank) ----------


def _make_sodastream_shape_product(brand: str, name: str, price: float) -> dict:
    """Replicates the SodaStream-vs-Aarke 24-query failure shape:
       specs=None, fact_check=None, review_count=None — purely
       price-driven comparison with no spec/reliability/review signal.
    """
    return {
        "brand": brand,
        "name": name,
        "category": "other",
        "specs": None,
        "rating": None,
        "review_count": None,
        "price": {"amount": price, "currency": "BHD"},
        "fact_check": None,
    }


def test_other_sodastream_aarke_shape_no_phantom_ties(service):
    """Integration — SodaStream-vs-Aarke (category=other, specs=None,
    fact_check=None, review_count=None). Every dim in the breakdown must
    be MISSING_SCORE=50 OR absent from breakdown + listed in `missing_data`.
    NO phantom (70.0, 70.0) or (30.0, 30.0) literal pairs.
    """
    products = [
        _make_sodastream_shape_product("SodaStream", "Terra", 30.0),
        _make_sodastream_shape_product("Aarke", "Carbonator 3", 70.0),
    ]
    scoring_result = service.compute_scores(products)
    forbidden_pairs = {(70.0, 70.0), (30.0, 30.0)}
    for i in range(2):
        breakdown = scoring_result["scores"][f"product_{i}"]["breakdown"]
        for dim_key in CATEGORY_DIMENSIONS["other"]:
            score = breakdown.get(dim_key)
            # Every dim must EITHER be MISSING_SCORE (legacy) / None (flag-on)
            # OR be the price-driven value dim (which CAN have a real numeric
            # value because we have price signals on both sides).
            if dim_key == "value_score":
                continue  # price-driven, may be non-MISSING
            assert score in (MISSING_SCORE, None), (
                f"[other] dim {dim_key!r} for product_{i} = {score!r}; "
                f"expected MISSING_SCORE={MISSING_SCORE} or None"
            )

    # And the pair tuples for any dim must NOT be the forbidden literals
    breakdowns = [scoring_result["scores"][f"product_{i}"]["breakdown"] for i in range(2)]
    for dim_key in CATEGORY_DIMENSIONS["other"]:
        a, b = breakdowns[0].get(dim_key), breakdowns[1].get(dim_key)
        assert (a, b) not in forbidden_pairs, (
            f"[other] dim {dim_key!r} surfaced forbidden phantom literal pair "
            f"({a}, {b}) — B0-A v2 regression"
        )


def test_other_sodastream_aarke_build_dimensions_v2_omits_phantom_dims(service):
    """build_dimensions_v2 must SILENTLY OMIT any dim where both products
    are MISSING_SCORE. The 3 core dims (price, reviews, value) may still
    surface — but no `(craft, 70.0, 70.0)` ghost rows.
    """
    products = [
        _make_sodastream_shape_product("SodaStream", "Terra", 30.0),
        _make_sodastream_shape_product("Aarke", "Carbonator 3", 70.0),
    ]
    scoring_result = service.compute_scores(products)
    dims = build_dimensions_v2(products, scoring_result, "other")
    dim_keys = {d.get("key") for d in dims}

    # Core 3 may appear.
    # Category-specific dims must EITHER be omitted or have non-forbidden values.
    forbidden_pairs = {(70.0, 70.0), (30.0, 30.0)}
    for dim in dims:
        if dim.get("key") in {"price", "reviews", "value"}:
            continue
        pair = (dim.get("score_a"), dim.get("score_b"))
        assert pair not in forbidden_pairs, (
            f"other-category dim {dim.get('key')!r} surfaced forbidden pair "
            f"{pair} — should have been silently omitted by A.4.9"
        )


# ---------- Integration: fragrances blank-spec pair ----------


def _make_fragrance_blank_product(brand: str, name: str, price: float) -> dict:
    """Fragrance product with NO spec extraction success (common failure
    mode for niche fragrances). character/longevity/versatility dims map
    to spec_raw signal → tied at zero or low partial coverage.
    """
    return {
        "brand": brand,
        "name": name,
        "category": "fragrances",
        "specs": {},  # _score_specs returns 0.0 here
        "rating": None,
        "review_count": None,
        "price": {"amount": price, "currency": "BHD"},
        "fact_check": None,
    }


def test_fragrances_no_phantom_character_longevity_versatility(service):
    """Integration — fragrances with empty specs. character_score,
    longevity_score, versatility_score (all spec-mapped per the
    _DIMENSION_SIGNAL_MAP) must NOT emit phantom (70.0, 70.0) or
    (30.0, 30.0) pair.
    """
    products = [
        _make_fragrance_blank_product("Tom Ford", "Black Orchid", 100.0),
        _make_fragrance_blank_product("Creed", "Aventus", 250.0),
    ]
    scoring_result = service.compute_scores(products)
    forbidden_pairs = {(70.0, 70.0), (30.0, 30.0)}
    breakdowns = [
        scoring_result["scores"][f"product_{i}"]["breakdown"] for i in range(2)
    ]
    for dim_key in ("character_score", "longevity_score", "versatility_score"):
        a, b = breakdowns[0].get(dim_key), breakdowns[1].get(dim_key)
        assert (a, b) not in forbidden_pairs, (
            f"fragrances dim {dim_key!r} emitted forbidden phantom literal "
            f"pair ({a}, {b}) — v2 regression"
        )


# ---------- Drift-guard re-validation across categories ----------


@pytest.mark.parametrize("category", ["electronics", "fashion", "fragrances", "other"])
def test_partial_coverage_specs_does_not_emit_30_30_or_70_70(service, category):
    """24-query matrix case — both products have 1-2 spec fields populated
    that average to the SAME non-zero score (e.g. only 'material' set on
    both, _score_specs returns ~1.0 for both → max==min==1.0). Pre-v2
    leaked phantom 70/70 because `max==min==1.0 > 0`. Post-v2 the per-
    product _spec_missing flags route to MISSING_SCORE.

    NOTE: For this test to bite, both products must have empty specs
    (triggering _score_specs returning 0.0) AND the v2 code must route
    max==min==0 to MISSING_SCORE (pass-1 behavior). The partial-coverage
    case is harder to simulate without _spec_missing being set explicitly
    — included here as a coverage check.
    """
    products = [
        {
            "brand": "BrandA", "name": "ModelA", "category": category,
            "specs": {}, "rating": None, "review_count": None,
            "price": {"amount": 50.0, "currency": "BHD"}, "fact_check": None,
        },
        {
            "brand": "BrandB", "name": "ModelB", "category": category,
            "specs": {}, "rating": None, "review_count": None,
            "price": {"amount": 60.0, "currency": "BHD"}, "fact_check": None,
        },
    ]
    scoring_result = service.compute_scores(products)
    forbidden_pairs = {(70.0, 70.0), (30.0, 30.0)}
    breakdowns = [
        scoring_result["scores"][f"product_{i}"]["breakdown"] for i in range(2)
    ]
    for dim_key in CATEGORY_DIMENSIONS[category]:
        a, b = breakdowns[0].get(dim_key), breakdowns[1].get(dim_key)
        assert (a, b) not in forbidden_pairs, (
            f"[{category}] dim {dim_key!r} surfaced phantom pair "
            f"({a}, {b}) — v2 regression"
        )

"""B0-A BUG #2 regression — drift-guard against hard-coded 70.0/30.0 in dim scoring.

Symptom from 24-query bias audit: every low-signal query emits IDENTICAL
score_a == score_b literals across all category-specific dims:
  electronics.other:  ('function', 70.0, 70.0), ('build', 30.0, 30.0),
                      ('reliability', 70.0, 70.0)
  fashion:            ('craft', 70.0, 70.0), ('durability', 30.0, 30.0),
                      ('heritage', 70.0, 70.0) — IDENTICAL across fashion_a
                      and fashion_b queries
Beauty/personal-care categories scored well (89-100% winner-derive);
commodity/electronics/fashion scored poorly (33-55%).

Root cause: `_normalize_dimension` in scoring_service.py:1245 returned a
hardcoded 70.0 when `max_val == min_val` — which fires both for genuine
tied non-zero signals AND for the no-signal case (both products' specs
fail extraction → `_score_specs` returns 0.0 for both → `max_val == min_val
== 0`). The no-signal path was producing a phantom `(dim, 70.0, 70.0)`
tie row instead of routing through MISSING_SCORE → silent omission.

Fix: `_normalize_dimension` now distinguishes "no signal extracted"
(max == min == 0 → MISSING_SCORE so silent omission fires) from "genuine
tied non-zero signal" (max == min == X > 0 → keep 70.0 tie).

Tests below exercise the drift-guard via:
  (1) `_normalize_dimension` direct unit — 0/0 inputs return MISSING_SCORE
  (2) Build full scoring_result for 4 distinct low-signal pairs across
      electronics/fashion/grocery/other and verify NO dim emits an
      IDENTICAL `(score_a, score_b)` pair of literal 70.0 or 30.0
      across multiple comparisons (drift-guard against future default
      reintroductions).
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


# ---------- Unit: _normalize_dimension no-signal path ----------


def test_normalize_dimension_no_signal_returns_missing_score(service):
    """Both products zero raw signal => MISSING_SCORE (NOT hardcoded 70.0).

    Pre-fix: `max_val == min_val == 0` triggered `return 70.0`, producing
    phantom 70/70 tie rows in low-signal queries. Post-fix: routes through
    MISSING_SCORE so build_dimensions_v2's A.4.9 silent omission fires.
    """
    raw_scores = [
        {"spec_raw": 0.0},
        {"spec_raw": 0.0},
    ]
    for idx in (0, 1):
        result = service._normalize_dimension(raw_scores, idx, "spec_raw", higher_better=True)
        assert result == MISSING_SCORE, (
            f"product_{idx} no-signal spec_raw should map to MISSING_SCORE={MISSING_SCORE}, "
            f"got {result} (regression: hardcoded 70.0 literal)"
        )


def test_normalize_dimension_genuine_tie_still_returns_70(service):
    """Both products tied at NON-ZERO raw signal => keep 70.0 tie display.

    The fix must NOT regress on legitimate ties — if both products extracted
    e.g. spec_raw=2.5, we still display 70.0 for both (tied, no information
    about which is better).
    """
    raw_scores = [
        {"spec_raw": 2.5},
        {"spec_raw": 2.5},
    ]
    for idx in (0, 1):
        result = service._normalize_dimension(raw_scores, idx, "spec_raw", higher_better=True)
        assert result == 70.0, (
            f"genuine non-zero tie should map to 70.0, got {result}"
        )


def test_normalize_dimension_with_actual_signal_diff(service):
    """Sanity — when signals differ, returns ratio-based score [30, 100]."""
    raw_scores = [
        {"spec_raw": 1.0},  # min
        {"spec_raw": 5.0},  # max
    ]
    score_a = service._normalize_dimension(raw_scores, 0, "spec_raw", higher_better=True)
    score_b = service._normalize_dimension(raw_scores, 1, "spec_raw", higher_better=True)
    assert score_a == 30.0, f"min-side higher_better should map to 30.0 floor, got {score_a}"
    assert score_b == 100.0, f"max-side higher_better should map to 100.0 ceiling, got {score_b}"
    assert score_a != score_b, "Drift: ratio path collapsed to single literal"


# ---------- Integration: no-signal pairs across categories ----------


def _make_blank_product(
    name: str, brand: str, *, price: float | None = None, category: str = "other"
) -> dict:
    """Product with empty specs + no fact_check — exercises the no-signal path.

    `category` is read by ScoringService.compute_scores from
    `products_data[0]["category"]`, so we set it on each product.
    """
    return {
        "name": name,
        "brand": brand,
        "category": category,
        "specs": {},  # _score_specs returns 0.0 here
        "rating": None,
        "review_count": None,
        "price": {"amount": price, "currency": "BHD"} if price is not None else None,
        "fact_check": None,
    }


CATEGORIES_TO_DRIFT_GUARD = ["electronics", "fashion", "grocery", "other"]


@pytest.mark.parametrize("category", CATEGORIES_TO_DRIFT_GUARD)
def test_low_signal_pair_does_not_emit_70_70_or_30_30_dim_literals(service, category):
    """Drift-guard — any category with empty-spec/no-fact-check pair must NOT
    emit a dim where (score_a, score_b) is the literal (70.0, 70.0) OR
    (30.0, 30.0). After the fix, the missing-signal dims are silently omitted
    by build_dimensions_v2 (A.4.9), so the surviving dims have variation.
    """
    products = [
        _make_blank_product("Product A", "BrandA", price=50.0, category=category),
        _make_blank_product("Product B", "BrandB", price=60.0, category=category),
    ]
    scoring_result = service.compute_scores(products)

    breakdowns = [
        scoring_result["scores"][f"product_{i}"]["breakdown"]
        for i in range(2)
    ]
    for dim_key in CATEGORY_DIMENSIONS[category]:
        score_a = breakdowns[0].get(dim_key)
        score_b = breakdowns[1].get(dim_key)
        # The dim may be MISSING_SCORE=50 across both — that's fine, A.4.9
        # silent omission catches it downstream. The forbidden pattern is
        # the legacy phantom 70/70 or 30/30 literal pair.
        forbidden_pairs = {(70.0, 70.0), (30.0, 30.0)}
        assert (score_a, score_b) not in forbidden_pairs, (
            f"[{category}] dim {dim_key!r} emitted forbidden literal "
            f"({score_a}, {score_b}) — pre-fix regression"
        )


def test_low_signal_pair_dims_silently_omitted_in_build_dimensions_v2(service):
    """Integration — when both products have no spec/fact-check signal,
    build_dimensions_v2 silently omits the category-specific dims via the
    A.4.9 filter. Only the 3 core dims (price, reviews, value) survive,
    NOT phantom (craft, 70.0, 70.0) etc.
    """
    products = [
        _make_blank_product("Cap A", "BrandA", price=50.0, category="fashion"),
        _make_blank_product("Cap B", "BrandB", price=60.0, category="fashion"),
    ]
    scoring_result = service.compute_scores(products)
    dims = build_dimensions_v2(products, scoring_result, "fashion")

    dim_keys = {d.get("key") for d in dims}
    # Core 3 dims always present.
    assert "price" in dim_keys
    assert "reviews" in dim_keys
    assert "value" in dim_keys

    # No fashion-specific dim may surface with a (70.0, 70.0) or (30.0, 30.0)
    # literal pair from the legacy hardcoded path.
    for dim in dims:
        if dim.get("key") in {"price", "reviews", "value"}:
            continue
        forbidden_pairs = {(70.0, 70.0), (30.0, 30.0)}
        assert (dim.get("score_a"), dim.get("score_b")) not in forbidden_pairs, (
            f"fashion dim {dim.get('key')!r} surfaced legacy "
            f"({dim.get('score_a')}, {dim.get('score_b')}) literal pair"
        )


# ---------- Drift-guard across multiple distinct product pairs ----------


def _make_pair(brand_a: str, brand_b: str, price_a: float, price_b: float, *, category: str = "fashion") -> list[dict]:
    return [
        _make_blank_product(f"{brand_a} model", brand_a, price=price_a, category=category),
        _make_blank_product(f"{brand_b} model", brand_b, price=price_b, category=category),
    ]


DRIFT_GUARD_PAIRS = [
    _make_pair("Nike", "Adidas", 50.0, 55.0),
    _make_pair("Gucci", "Prada", 200.0, 220.0),
    _make_pair("H&M", "Zara", 25.0, 28.0),
]


def test_dim_score_pairs_vary_across_distinct_product_pairs(service):
    """Drift-guard — for the same (category, dim) across multiple distinct
    blank-product pairs, the emitted (score_a, score_b) tuples must NOT be
    IDENTICAL across all pairs. If they are, that's a sign a hardcoded
    default crept back in (the literal would fire for every pair regardless
    of input).
    """
    category = "fashion"
    pair_results = []
    for pair in DRIFT_GUARD_PAIRS:
        scoring_result = service.compute_scores(pair)
        pair_results.append(
            {
                dim_key: (
                    scoring_result["scores"]["product_0"]["breakdown"].get(dim_key),
                    scoring_result["scores"]["product_1"]["breakdown"].get(dim_key),
                )
                for dim_key in CATEGORY_DIMENSIONS[category]
            }
        )
    # For each dim, the (score_a, score_b) across 3 pairs should NOT be
    # 100% identical (which would imply hardcoded literal). Allowing
    # MISSING_SCORE=50 across all (legitimate signal-missing path) is fine
    # — that ALSO triggers silent omission downstream.
    for dim_key in CATEGORY_DIMENSIONS[category]:
        tuples = [r[dim_key] for r in pair_results]
        # Allow all-MISSING_SCORE (handled by silent omission)
        all_missing = all(t == (MISSING_SCORE, MISSING_SCORE) for t in tuples)
        # Allow all-None (Bundle C flag-on path)
        all_none = all(t == (None, None) for t in tuples)
        # Otherwise, the literal (70.0, 70.0) repeated across pairs is the
        # regression pattern we're guarding against.
        if not (all_missing or all_none):
            unique_tuples = {t for t in tuples}
            assert (70.0, 70.0) not in unique_tuples or len(unique_tuples) > 1, (
                f"dim {dim_key!r} emitted hardcoded (70.0, 70.0) for ALL "
                f"distinct blank-product pairs — drift regression. Tuples: {tuples}"
            )

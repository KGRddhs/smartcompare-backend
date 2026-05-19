"""Bundle C v1 hot-fix — comparison_quality + applied_shifts response wiring.

Post-merge production probes showed both fields surfacing as None on
all 6 categories despite the helpers being shipped (A.4.5, A.9.1).
Root cause: response_builder never called them. This hot-fix adds
defensive wrappers that call the helpers and populate the response.
"""
import pytest
from app.services.response_builder import (
    build_comparison_response,
    _safe_detect_comparison_quality,
    _safe_compute_applied_shifts,
)


def _minimal_product_data():
    return [
        {"name": "iPhone 16", "category": "electronics", "category_used": "electronics",
         "price": {"amount": 350.0}, "rating": 4.5,
         "specs": {"battery": "3274", "processor": "A17", "ram": "8", "rear_camera": "48"}},
        {"name": "Galaxy S25", "category": "electronics", "category_used": "electronics",
         "price": {"amount": 280.0}, "rating": 4.4,
         "specs": {"battery": "4000", "processor": "S25", "ram": "12", "rear_camera": "50"}},
    ]


def _minimal_scoring_result():
    return {
        "scores": {
            "product_0": {
                "overall": 75, "breakdown": {},
                "weights_used": {"performance_score": 0.30, "value_score": 0.20},
            },
            "product_1": {
                "overall": 80, "breakdown": {},
                "weights_used": {"performance_score": 0.30, "value_score": 0.20},
            },
        },
        "winner_index": 1,
        "category_weights": {"performance_score": 0.20, "value_score": 0.20},
    }


# ---------------------------------------------------------------------------
# Helper-level smoke
# ---------------------------------------------------------------------------


def test_safe_detect_comparison_quality_returns_string():
    out = _safe_detect_comparison_quality(_minimal_product_data())
    assert out in {"normal", "weak", "weird"}


def test_safe_detect_comparison_quality_never_crashes_on_bad_input():
    assert _safe_detect_comparison_quality(None) is None or _safe_detect_comparison_quality(None) in {"normal"}
    assert _safe_detect_comparison_quality([]) in {"normal", None}


def test_safe_compute_applied_shifts_returns_list_not_none():
    """Spec § 7a: chip hides itself when list empty — so we MUST return []
    not None. Even on bad input / missing weights, return []."""
    out = _safe_compute_applied_shifts(_minimal_scoring_result())
    assert isinstance(out, list)


def test_safe_compute_applied_shifts_returns_empty_list_on_bad_input():
    """Defensive: bad scoring_result → still returns list, never None."""
    assert _safe_compute_applied_shifts(None) == []
    assert _safe_compute_applied_shifts({}) == []
    assert _safe_compute_applied_shifts({"scores": {}}) == []


def test_safe_compute_applied_shifts_returns_qualitative_shifts():
    """When weights_used differs from category_weights, surface shifts."""
    scoring = _minimal_scoring_result()
    # performance_score: 0.30 used vs 0.20 default → +0.10 → 'up'
    out = _safe_compute_applied_shifts(scoring)
    assert any(s.get("direction") == "up" for s in out)


# ---------------------------------------------------------------------------
# Response-level wiring
# ---------------------------------------------------------------------------


def test_response_metadata_includes_comparison_quality():
    """The hot-fix surface: response.metadata.comparison_quality must be
    populated (not None) on any well-formed comparison."""
    response = build_comparison_response(
        product_data=_minimal_product_data(),
        comparison={"winner_index": 1},
        scoring_result=_minimal_scoring_result(),
        product_names=["iPhone 16", "Galaxy S25"],
        tradeoffs=[],
        confidence={"overall": "high"},
        verdict_validation={},
        user_preferences=None,
        from_cache=False,
        query="iPhone 16 vs Galaxy S25",
        region="bahrain",
        category_used="electronics",
        category_switched=False,
        original_category=None,
        total_cost=0.01,
        api_calls=5,
        gpt_calls=3,
        serper_calls=2,
        elapsed_seconds=14.5,
    )
    assert "metadata" in response
    cq = response["metadata"].get("comparison_quality")
    assert cq is not None, (
        f"comparison_quality is None in response — hot-fix wiring failed. "
        f"metadata keys: {list(response['metadata'].keys())}"
    )
    assert cq in {"normal", "weak", "weird"}


def test_response_personalization_applied_shifts_is_list_not_none():
    """The hot-fix surface: response.personalization.applied_shifts must
    be a list (per spec § 7a — empty list when no priorities). NEVER None."""
    response = build_comparison_response(
        product_data=_minimal_product_data(),
        comparison={"winner_index": 1},
        scoring_result=_minimal_scoring_result(),
        product_names=["iPhone 16", "Galaxy S25"],
        tradeoffs=[],
        confidence={"overall": "high"},
        verdict_validation={},
        user_preferences=None,  # no priorities → applied_shifts should be []
        from_cache=False,
        query="iPhone 16 vs Galaxy S25",
        region="bahrain",
        category_used="electronics",
        category_switched=False,
        original_category=None,
        total_cost=0.01,
        api_calls=5,
        gpt_calls=3,
        serper_calls=2,
        elapsed_seconds=14.5,
    )
    assert "personalization" in response
    shifts = response["personalization"].get("applied_shifts")
    assert shifts is not None, (
        f"applied_shifts is None — spec § 7a says it must be a list (use [] "
        f"when no shifts)"
    )
    assert isinstance(shifts, list)


def test_response_scoring_v2_has_comparison_quality_round2_fix():
    """Hot-fix round 2: scoring_v2 must ALSO carry comparison_quality
    (in addition to metadata.comparison_quality) per spec § 2e — frontend
    HeroRings.tsx reads scoring_v2.comparison_quality for weird-mode em-dash."""
    response = build_comparison_response(
        product_data=_minimal_product_data(),
        comparison={"winner_index": 1},
        scoring_result=_minimal_scoring_result(),
        product_names=["iPhone 16", "Galaxy S25"],
        tradeoffs=[], confidence={"overall": "high"}, verdict_validation={},
        user_preferences=None, from_cache=False, query="x", region="bahrain",
        category_used="electronics", category_switched=False,
        original_category=None, total_cost=0.0, api_calls=0, gpt_calls=0,
        serper_calls=0, elapsed_seconds=1.0,
    )
    sv2 = response.get("scoring_v2") or {}
    cq = sv2.get("comparison_quality")
    assert cq is not None and cq in {"normal", "weak", "weird"}, (
        f"scoring_v2.comparison_quality missing or invalid: {cq!r} — "
        f"round-2 hot-fix not landed. sv2 keys: {list(sv2.keys())}"
    )


def test_response_scoring_v2_has_personalization_applied_shifts_round2_fix():
    """Hot-fix round 2: scoring_v2.personalization.applied_shifts must be
    a list (per spec § 7b) — frontend chip reads this path."""
    response = build_comparison_response(
        product_data=_minimal_product_data(),
        comparison={"winner_index": 1},
        scoring_result=_minimal_scoring_result(),
        product_names=["iPhone 16", "Galaxy S25"],
        tradeoffs=[], confidence={"overall": "high"}, verdict_validation={},
        user_preferences=None, from_cache=False, query="x", region="bahrain",
        category_used="electronics", category_switched=False,
        original_category=None, total_cost=0.0, api_calls=0, gpt_calls=0,
        serper_calls=0, elapsed_seconds=1.0,
    )
    sv2 = response.get("scoring_v2") or {}
    pers = sv2.get("personalization")
    assert pers is not None, (
        f"scoring_v2.personalization missing — round-2 hot-fix not landed. "
        f"sv2 keys: {list(sv2.keys())}"
    )
    shifts = pers.get("applied_shifts")
    assert shifts is not None and isinstance(shifts, list), (
        f"scoring_v2.personalization.applied_shifts must be list (NEVER None), "
        f"got {shifts!r}"
    )


def test_response_applied_shifts_qualitative_only_no_magnitude_leak():
    """Critical rule #2 still enforced in the hot-fix path: applied_shifts
    items must have ONLY {dim_display, direction}, NEVER magnitude/coefficient."""
    response = build_comparison_response(
        product_data=_minimal_product_data(),
        comparison={"winner_index": 1},
        scoring_result=_minimal_scoring_result(),
        product_names=["iPhone 16", "Galaxy S25"],
        tradeoffs=[],
        confidence={"overall": "high"},
        verdict_validation={},
        user_preferences=None,
        from_cache=False,
        query="x",
        region="bahrain",
        category_used="electronics",
        category_switched=False,
        original_category=None,
        total_cost=0.0,
        api_calls=0,
        gpt_calls=0,
        serper_calls=0,
        elapsed_seconds=1.0,
    )
    shifts = response["personalization"].get("applied_shifts") or []
    for shift in shifts:
        assert set(shift.keys()) == {"dim_display", "direction"}
        assert shift["direction"] in {"up", "down"}
        for forbidden in ("magnitude", "coefficient", "cap_pct",
                          "shift_magnitude", "shift_pct"):
            assert forbidden not in shift, (
                f"forbidden key {forbidden!r} leaked into applied_shifts: {shift!r}"
            )

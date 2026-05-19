"""Bundle C — personalization applied_shifts RED tests (Section C plan tasks C.8.1 / C.8.2).

Covers spec §7:
  - §7a — Compact qualitative chip — direction only, NEVER magnitudes
  - §7b — Backend contract — `response.personalization.applied_shifts: [{dim_display, direction}, ...]`
  - §7d — Cohort attribution stays separate (no merging with personalization chip)

The chip ITSELF is frontend (Section C frontend file). This file covers the
backend contract: shape, key restriction, sort order, empty-list rule.

RED until A.x implements `_compute_applied_shifts` and `response_builder`
emits `personalization.applied_shifts[]`.
"""
from __future__ import annotations

import json

import pytest

from tests._bundle_c_helpers import assert_no_magnitude_fields


# ---------------------------------------------------------------------------
# C.8.1 — applied_shifts contract: direction-only, no magnitude (spec §7b)
# ---------------------------------------------------------------------------


def test_applied_shifts_items_are_direction_only():
    """Spec §7b: each shift is {dim_display, direction} ONLY — never magnitude/coefficient."""
    try:
        from app.services.scoring_service import _compute_applied_shifts  # type: ignore
    except ImportError:
        pytest.fail(
            "RED: _compute_applied_shifts missing from scoring_service (A.x pending)"
        )
        return
    weights_used = {
        "performance_score": 0.35,
        "build_quality_score": 0.25,
        "ecosystem_score": 0.10,
        "value_score": 0.10,
        "futureproof_score": 0.10,
        "design_score": 0.10,
    }
    defaults = {
        "performance_score": 0.20,
        "build_quality_score": 0.20,
        "ecosystem_score": 0.20,
        "value_score": 0.15,
        "futureproof_score": 0.15,
        "design_score": 0.10,
    }
    shifts = _compute_applied_shifts(weights_used, defaults)
    # Every shift must be a 2-key dict
    for shift in shifts:
        assert set(shift.keys()) == {"dim_display", "direction"}, (
            f"shift has extra keys: {shift!r} — spec §7b forbids magnitude leak"
        )
        assert shift["direction"] in {"up", "down"}
    # Magnitude/coefficient walker
    assert_no_magnitude_fields({"applied_shifts": shifts})


def test_applied_shifts_sorted_by_absolute_magnitude_top_3():
    """Spec §7b: sorted by absolute magnitude (largest 3)."""
    try:
        from app.services.scoring_service import _compute_applied_shifts  # type: ignore
    except ImportError:
        pytest.fail("RED: _compute_applied_shifts missing")
        return
    weights_used = {"a": 0.50, "b": 0.10, "c": 0.30, "d": 0.05, "e": 0.05}
    defaults = {"a": 0.25, "b": 0.20, "c": 0.20, "d": 0.20, "e": 0.15}
    # Absolute shifts: a=+0.25, b=-0.10, c=+0.10, d=-0.15, e=-0.10
    # Top 3 by |shift|: a (0.25), d (0.15), b/c/e tied at 0.10 → take any one
    shifts = _compute_applied_shifts(weights_used, defaults)
    assert len(shifts) <= 3, "spec §7b limits chip to 3 strongest shifts"
    # 'a' has the biggest absolute shift, must be first
    if shifts:
        assert shifts[0]["dim_display"] == "a", (
            f"strongest shift should sort first, got {shifts[0]!r}"
        )


def test_applied_shifts_returns_empty_when_no_significant_shifts():
    """Spec §7a: chip hidden when no priorities set OR no significant shifts."""
    try:
        from app.services.scoring_service import _compute_applied_shifts  # type: ignore
    except ImportError:
        pytest.fail("RED: _compute_applied_shifts missing")
        return
    weights = {"a": 0.33, "b": 0.33, "c": 0.34}
    # Identical → no shift at all
    shifts = _compute_applied_shifts(weights, weights)
    assert shifts == [], f"identical weights must produce empty shifts list, got {shifts!r}"


def test_applied_shifts_returns_empty_when_passed_none_or_empty():
    """Defensive: None or empty dict → empty list."""
    try:
        from app.services.scoring_service import _compute_applied_shifts  # type: ignore
    except ImportError:
        pytest.fail("RED: _compute_applied_shifts missing")
        return
    assert _compute_applied_shifts({}, {}) == []
    # Some impls accept None — accept both
    try:
        result = _compute_applied_shifts(None, None)  # type: ignore[arg-type]
        assert result == []
    except (TypeError, AttributeError):
        pass  # acceptable to refuse None


# ---------------------------------------------------------------------------
# C.8.2 — Response payload has NO magnitude/coefficient anywhere (spec §7b)
# ---------------------------------------------------------------------------


def test_full_response_payload_audit_no_magnitude_keys():
    """Spec §7b: belt-and-braces — full response shape audit.

    Builds a response with personalization.applied_shifts populated, then
    serialises and asserts no forbidden magnitude keys leak.
    """
    try:
        from app.services.response_builder import build_comparison_response  # type: ignore
    except ImportError:
        pytest.skip("response_builder not importable in this build")
        return

    # Try the most permissive call shape — pre-populated personalization block
    try:
        response = build_comparison_response(
            products=[
                {"name": "iPhone", "specs": {}, "price": {"amount": 100}},
                {"name": "Galaxy", "specs": {}, "price": {"amount": 100}},
            ],
            comparison={"winner_index": 0},
            personalization={
                "applied_shifts": [
                    {"dim_display": "performance_score", "direction": "up"},
                    {"dim_display": "build_quality_score", "direction": "up"},
                    {"dim_display": "brand_recognition", "direction": "down"},
                ],
            },
        )
    except TypeError:
        pytest.fail(
            "RED: build_comparison_response signature does not yet accept "
            "personalization kwarg with applied_shifts — A.x wiring pending"
        )
        return

    # 1. Walker assertion on the response dict
    assert_no_magnitude_fields(response)
    # 2. Serialise + string-grep (defensive)
    serialized = json.dumps(response)
    for forbidden_key in [
        '"magnitude"',
        '"shift_pct"',
        '"coefficient"',
        '"cap_pct"',
        '"shift_magnitude"',
    ]:
        assert forbidden_key not in serialized, (
            f"serialized response contains {forbidden_key} (spec §7b violation)"
        )


def test_applied_shifts_list_is_default_empty_when_no_priorities():
    """Spec §7a: when no priorities → personalization.applied_shifts is [] (or omitted)
    so the frontend chip hides naturally.
    """
    try:
        from app.services.response_builder import build_comparison_response  # type: ignore
    except ImportError:
        pytest.skip("response_builder not importable")
        return
    try:
        response = build_comparison_response(
            products=[
                {"name": "a", "specs": {}, "price": {"amount": 100}},
                {"name": "b", "specs": {}, "price": {"amount": 100}},
            ],
            comparison={"winner_index": 0},
            personalization={"applied_shifts": []},
        )
    except TypeError:
        pytest.fail("RED: build_comparison_response personalization wiring pending")
        return
    personalization = response.get("personalization", {}) or {}
    shifts = personalization.get("applied_shifts", [])
    assert shifts == [], f"applied_shifts should be [], got {shifts!r}"

"""
Bundle E Task 1.2 RED — calibrate_score() curve + honesty guard.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 1.2)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 4.

Contract under test (`app.services.scoring_service.calibrate_score`):

    display_score = clamp(70 + (raw_score - 50) * 0.5, 60, 95)

Fixed anchors (per design § Decision 4):
    raw 30 → display 60   (clamped at floor)
    raw 50 → display 70   (today's "average" → above-average baseline)
    raw 70 → display 80   (today's "good")
    raw 90 → display 90   (today's "excellent")

Clamp behavior:
    raw  0 → display 60 (floor — never go below)
    raw 100 → display 95 (ceiling — never claim perfection)

Honesty guard (design § Decision 4 "Honesty guard" sub-section):
    "A product with **all raw signals below 40** must score below 70
    even after calibration."
    → Signature: `calibrate_score(raw_score, raw_signals=None)`.
    → When `raw_signals` is provided AND every value < 40, the function
      returns a value strictly below 70 regardless of `raw_score`.
    → This is the "everything looks fine" guard — calibration must not
      paper over universally-bad inputs.

Monotonicity invariant (plan § Agent A "Hard rules"):
    "Calibration is monotonic — winners must still rank correctly."
    → For any two raw scores r1 < r2, calibrate_score(r1) ≤
      calibrate_score(r2). Clamping ties at the floor/ceiling.

RED→GREEN trajectory:
  - At HEAD (pre-Task-1.2): `calibrate_score` does not exist in
    `app.services.scoring_service` → ImportError at module import.
    All test methods fail at collection.
  - After Agent A lands Task 1.2: all assertions pass.
"""

from __future__ import annotations

import pytest

# RED gate — this import will raise ImportError pre-Task-1.2 because
# `calibrate_score` is not yet defined in scoring_service. Once Agent A
# adds it, the import resolves and the assertions below execute.
from app.services.scoring_service import calibrate_score  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — Curve anchors from design § Decision 4
# ---------------------------------------------------------------------------

class TestCalibrationCurveAnchors:
    """The four named raw→display anchor points from design § Decision 4."""

    @pytest.mark.parametrize(
        ("raw_score", "expected"),
        [
            (30, 60),   # raw 30 → 70 + (30-50)*0.5 = 60 (at floor)
            (50, 70),   # raw 50 → "average" → above-average baseline
            (70, 80),   # raw 70 → "good"
            (90, 90),   # raw 90 → "excellent"
        ],
    )
    def test_anchor_points(self, raw_score: int, expected: int):
        result = calibrate_score(raw_score)
        # Allow tiny FP drift (the formula is exact at these anchors,
        # but Agent A may choose to round or use Decimal internally).
        assert abs(result - expected) < 0.5, (
            f"calibrate_score({raw_score}) expected ≈{expected}, got {result}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Floor (60) and ceiling (95) clamps
# ---------------------------------------------------------------------------

class TestCalibrationClamps:
    """Calibration must clamp to [60, 95] — never below 60, never above 95.
    Without the floor a raw 0 maps to 45 (too punitive); without the
    ceiling a raw 100 maps to 95 already but defensive clamping protects
    against any future formula change."""

    def test_floor_at_60_for_zero_raw(self):
        assert calibrate_score(0) == 60

    def test_floor_at_60_for_very_low_raw(self):
        # 10, 20 — both well below the floor's pre-clamp value (55, 65).
        # Formula: 70 + (10-50)*0.5 = 50 → clamped to 60.
        #          70 + (20-50)*0.5 = 55 → clamped to 60.
        assert calibrate_score(10) == 60
        assert calibrate_score(20) == 60

    def test_ceiling_at_95_for_max_raw(self):
        assert calibrate_score(100) == 95

    def test_ceiling_at_95_above_max_raw(self):
        # Defensive: even if some upstream produces raw > 100 (bug or
        # bonus signal), calibration must never exceed 95.
        assert calibrate_score(120) == 95

    def test_no_score_in_forbidden_band_above_95(self):
        """Sample 30 raw scores from 0..150 — none may exceed 95."""
        for raw in range(0, 151, 5):
            assert calibrate_score(raw) <= 95

    def test_no_score_in_forbidden_band_below_60(self):
        """Sample 30 raw scores from 0..150 — without the honesty guard,
        none may fall below 60."""
        for raw in range(0, 151, 5):
            assert calibrate_score(raw) >= 60


# ---------------------------------------------------------------------------
# Test 3 — Monotonicity (plan § Agent A "Hard rules")
# ---------------------------------------------------------------------------

class TestCalibrationMonotonicity:
    """Calibration is monotonic non-decreasing — for r1 < r2, calibrate(r1)
    ≤ calibrate(r2). A winner-flipping calibration is a bug per the plan."""

    def test_strictly_monotonic_inside_active_range(self):
        """Inside the active range (raw 20..100, where the function is
        not floored/ceilinged), calibration is strictly increasing."""
        previous = calibrate_score(20)
        for raw in range(21, 101):
            current = calibrate_score(raw)
            assert current >= previous, (
                f"monotonicity violated at raw={raw}: "
                f"calibrate({raw - 1})={previous}, calibrate({raw})={current}"
            )
            previous = current

    def test_winners_preserved_across_calibration(self):
        """Two products' rank-order must survive calibration. The plan
        explicitly calls out winner-flipping as a bug."""
        pairs = [
            (40, 60),   # mid raw gap
            (55, 65),   # close-call
            (75, 85),   # high band
            (50.1, 50.0),  # near-tie — > stays >=
        ]
        for r_high, r_low in pairs:
            assert calibrate_score(r_high) >= calibrate_score(r_low), (
                f"rank flip: raw {r_high} > {r_low} but calibrated "
                f"{calibrate_score(r_high)} < {calibrate_score(r_low)}"
            )


# ---------------------------------------------------------------------------
# Test 4 — Honesty guard (all raw signals < 40)
# ---------------------------------------------------------------------------

class TestHonestyGuard:
    """Design § Decision 4 "Honesty guard": a product where ALL raw signals
    are below 40 must score below 70 even after calibration.

    Contract: `calibrate_score(raw_score, raw_signals=None)`.
        - raw_signals=None → vanilla calibration (Tests 1-3 above).
        - raw_signals=[s1, s2, ...] → if every s_i < 40, returned display
          score is strictly below 70.
    """

    def test_all_signals_below_40_forces_sub_70_display(self):
        """The headline assertion. Even with a raw_score of 90 (which
        would normally calibrate to 90), the honesty guard pulls the
        display below 70 because every individual signal is < 40."""
        bad_signals = [35, 30, 38, 20]
        result = calibrate_score(90, raw_signals=bad_signals)
        assert result < 70, (
            f"honesty guard failed: signals {bad_signals} all <40 but "
            f"display={result} ≥70"
        )

    def test_one_signal_at_or_above_40_disables_guard(self):
        """Guard only fires when ALL signals are below 40. One signal at
        40 means the guard is OFF and normal calibration applies."""
        mixed_signals = [35, 30, 40, 38]  # one at 40
        result = calibrate_score(90, raw_signals=mixed_signals)
        # Normal calibration of raw 90 → display 90 (or very close).
        assert result >= 70, (
            f"guard fired incorrectly: one signal=40 should disable, "
            f"got display={result}"
        )

    def test_none_raw_signals_uses_vanilla_curve(self):
        """raw_signals=None must not trigger the guard. This is the
        common case — calibration is called with just a raw_score from
        the existing scoring path that hasn't been refactored yet."""
        assert calibrate_score(50) == calibrate_score(50, raw_signals=None)
        assert calibrate_score(70) == calibrate_score(70, raw_signals=None)

    def test_empty_raw_signals_does_not_trigger_guard(self):
        """An empty list means "no signal data provided", not "all signals
        are bad". The guard must require non-empty evidence to fire."""
        result = calibrate_score(90, raw_signals=[])
        assert result >= 80, (
            f"empty signal list spuriously triggered guard: display={result}"
        )

    def test_guard_still_respects_floor(self):
        """Even when the guard fires, display must remain at or above
        the 60 floor — we never claim a product is below acceptable, we
        just decline to claim it is acceptable."""
        result = calibrate_score(50, raw_signals=[10, 5, 15, 20])
        assert 60 <= result < 70, (
            f"honesty guard violated [60, 70) band: display={result}"
        )


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-1.2 run:
#     python -m pytest tests/test_scoring_calibration.py -v
#     → ImportError on `calibrate_score` (function does not exist in
#       app.services.scoring_service)
#     → 0 collected, 1 collection error → RED
#
# Post-Task-1.2 (Agent A lands calibrate_score):
#     → 4 test classes, ~16 assertions
#     → coverage on `calibrate_score` should be ~100% (one function,
#       three branches: floor, normal curve, ceiling, plus the guard).
#     → re-verify here, post SIGN-OFF with coverage % from:
#       pytest tests/test_scoring_calibration.py --cov=app.services.scoring_service --cov-report=term-missing

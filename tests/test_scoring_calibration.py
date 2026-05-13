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

    def test_random_pairs_preserve_order(self):
        """Dispatcher Test-1.2 case 6 — 100 random (x, y) pairs from 0..100
        with x < y must satisfy calibrate(x) <= calibrate(y). Property-style
        check that catches any non-monotonic regression a future calibration
        change might introduce."""
        import random
        rng = random.Random(20260513)  # deterministic seed — same pairs every run
        for _ in range(100):
            x = rng.randint(0, 100)
            y = rng.randint(0, 100)
            if x == y:
                continue
            lo, hi = (x, y) if x < y else (y, x)
            cl, ch = calibrate_score(lo), calibrate_score(hi)
            assert cl <= ch, (
                f"monotonicity violated on random pair: "
                f"calibrate({lo})={cl} > calibrate({hi})={ch}"
            )


# ---------------------------------------------------------------------------
# Test 3b — Win-gap survival (dispatcher Test-1.2 case 7)
# ---------------------------------------------------------------------------

class TestWinGapSurvival:
    """Dispatcher contract: `calibrate(80) - calibrate(50) > 5`. A
    calibration that flattens raw spreads into a too-narrow band makes
    every comparison feel like a tie and undermines the "winner" message.

    The design formula `70 + (raw-50)*0.5` halves raw gaps but never
    collapses them — a 30-point raw gap (50→80) yields a 15-point
    calibrated gap (70→85), well above the 5-point minimum below."""

    def test_30_point_raw_gap_yields_nontrivial_display_gap(self):
        gap = calibrate_score(80) - calibrate_score(50)
        assert gap > 5, (
            f"win-gap collapse: calibrate(80)-calibrate(50)={gap} "
            f"(≤5 — calibration is too flat to support a 'winner' verdict)"
        )

    def test_20_point_raw_gap_inside_active_band_yields_visible_gap(self):
        """A 20-point raw gap entirely inside the active band (50→70)
        must produce a calibrated gap ≥ 9 (= 0.5 * 20 — 1 fp epsilon)."""
        gap = calibrate_score(70) - calibrate_score(50)
        assert gap >= 9, (
            f"sub-active-band gap collapsed: calibrate(70)-calibrate(50)={gap}"
        )

    def test_close_call_still_yields_nonzero_gap(self):
        """A 5-point raw gap (60 vs 65) survives as a 2-3 point display
        gap — small but non-zero, so the winner card still has signal."""
        gap = calibrate_score(65) - calibrate_score(60)
        assert gap >= 2, (
            f"close-call gap collapsed: calibrate(65)-calibrate(60)={gap}"
        )


# ---------------------------------------------------------------------------
# Test 3c — Return type (dispatcher Test-1.2 case 8)
# ---------------------------------------------------------------------------

class TestReturnType:
    """Dispatcher contract: `result is int (no floats)`. The hero ring
    label and dimension bars render integer scores — returning 79.5
    would force callers to round and risks `79.5` slipping into JSON.

    Note: this anchors the contract that Agent A's `calibrate_score`
    rounds (or truncates) internally rather than letting the *0.5 curve
    produce halves like 79.5 (= 70 + (69-50)*0.5)."""

    def test_returns_int_on_integer_input(self):
        result = calibrate_score(70)
        assert isinstance(result, int), (
            f"calibrate(70) returned {type(result).__name__}, expected int"
        )

    def test_returns_int_on_curve_halfpoint(self):
        """raw 69 maps to 79.5 pre-round. Result must still be int."""
        result = calibrate_score(69)
        assert isinstance(result, int), (
            f"calibrate(69) returned {type(result).__name__}={result}, "
            f"expected int (function must round/truncate the *0.5 curve)"
        )

    def test_returns_int_at_floor(self):
        assert isinstance(calibrate_score(0), int)
        assert isinstance(calibrate_score(20), int)

    def test_returns_int_at_ceiling(self):
        assert isinstance(calibrate_score(100), int)
        assert isinstance(calibrate_score(120), int)

    def test_returns_int_under_honesty_guard(self):
        """Guard branch must also return int — defensive check that the
        guard doesn't sneak a float past the type contract."""
        result = calibrate_score(90, raw_signals=[35, 30, 38, 20])
        assert isinstance(result, int), (
            f"guard branch returned {type(result).__name__}, expected int"
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

"""Bundle C § 2c A.4.3 — calibration band [60, 95] + has_signal short-circuit.

Per design § 2c + plan A.4.3: `calibrate_score` already keeps populated
signals inside [60, 95] with an honesty guard (raw < 40 caps at 69).
A.4.3 explicitly tests those invariants AND adds a `has_signal=False`
short-circuit that returns None for the missing-data case — so the
A.4.9 silent-dim-omission path can route `None` through cleanly without
the dim builder having to guess what value to substitute.

Companion to test-bundle-c's
`test_calibrate_score_band_unchanged_for_populated_signals` parametrized
suite (already GREEN). This file adds the missing-signal contract.
"""
import pytest

from app.services.scoring_service import (
    calibrate_score,
    _CALIBRATION_FLOOR,
    _CALIBRATION_CEILING,
    _HONESTY_GUARD_CEILING,
    _HONESTY_GUARD_THRESHOLD,
)


# ---------------------------------------------------------------------------
# § 2c — populated signal stays in [60, 95]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", [40, 45, 50, 60, 70, 80, 90, 95, 100])
def test_populated_signal_falls_inside_60_95_band(raw):
    """For raw scores >= 40 (i.e. no honesty-guard cap), output must lie
    in [60, 95] inclusive."""
    out = calibrate_score(raw)
    assert _CALIBRATION_FLOOR <= out <= _CALIBRATION_CEILING, (
        f"calibrate_score({raw}) = {out} outside [{_CALIBRATION_FLOOR}, {_CALIBRATION_CEILING}]"
    )


def test_floor_clamps_low_raw_scores():
    """Raw scores below 40 still clamp to the floor (60) when no
    raw_signals context is supplied. The honesty guard only kicks in
    when ALL raw_signals are below the threshold."""
    assert calibrate_score(0) == _CALIBRATION_FLOOR
    assert calibrate_score(20) == _CALIBRATION_FLOOR


def test_ceiling_clamps_high_raw_scores():
    """Raw scores above 100 still clamp to the ceiling (95)."""
    assert calibrate_score(100) == _CALIBRATION_CEILING
    assert calibrate_score(150) == _CALIBRATION_CEILING


# ---------------------------------------------------------------------------
# § 2c — honesty guard: raw_signals < threshold → cap at 69
# ---------------------------------------------------------------------------


def test_honesty_guard_caps_display_at_69_when_all_signals_weak():
    """When raw_signals is supplied AND every signal is below the
    honesty-guard threshold (40), output is capped at 69 — no inflated
    'looks great!' score on genuinely sparse data."""
    weak_signals = [10, 20, 30]
    assert all(s < _HONESTY_GUARD_THRESHOLD for s in weak_signals)
    # Even with raw_score=95 (would normally calibrate to 92), honesty
    # guard caps the display at 69.
    out = calibrate_score(95, raw_signals=weak_signals)
    assert out <= _HONESTY_GUARD_CEILING


def test_honesty_guard_does_not_fire_when_any_signal_strong():
    """If even one raw_signal clears the threshold, the honesty guard
    stays out of the way."""
    mixed = [10, 50, 30]  # 50 >= 40 → strong enough
    out = calibrate_score(95, raw_signals=mixed)
    assert out > _HONESTY_GUARD_CEILING


# ---------------------------------------------------------------------------
# § 2c — has_signal=False → return None (A.4.3 new contract)
# ---------------------------------------------------------------------------


def test_missing_signal_returns_none_via_has_signal_kwarg():
    """When `has_signal=False`, calibrate_score short-circuits to None
    so the dim builder can silently omit the dimension (A.4.9). NO
    phantom calibrated-floor value sneaks back into the response.

    This is the explicit None-propagation contract added by A.4.3.
    """
    out = calibrate_score(50, has_signal=False)
    assert out is None


def test_has_signal_true_keeps_legacy_band_behavior():
    """Backwards-compat: has_signal=True (or omitted) returns the
    calibrated int as before."""
    assert calibrate_score(50, has_signal=True) == calibrate_score(50)
    assert calibrate_score(70, has_signal=True) == calibrate_score(70)


def test_none_raw_score_with_has_signal_false_still_none():
    """Edge case: explicit None raw + has_signal=False → None (not a crash)."""
    out = calibrate_score(None, has_signal=False)
    assert out is None


def test_default_has_signal_true_preserves_legacy_callers():
    """All existing call sites omit `has_signal` — they must keep
    getting an int back, not None."""
    out = calibrate_score(50)
    assert out is not None
    assert isinstance(out, int)

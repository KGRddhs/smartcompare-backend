"""Bundle C — calibration + missing-data RED tests (Section C plan tasks C.1.1 / C.1.3).

Covers spec §2:
  - §2a — Kill the missing-data floor of 50: missing signals propagate as None,
    NOT MISSING_SCORE.
  - §2g — Eliminate fabricated defaults (no more `rating or 4.0`, `price or 0.1`).

This file is RED until A.4.1 (None propagation) + A.4.2 (fabricated defaults
removal) ship. Existing `test_scoring_calibration.py` (Bundle E) stays untouched
to preserve regression coverage.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# C.1.1 — Missing data → None propagation, NOT MISSING_SCORE (§2a)
# ---------------------------------------------------------------------------


def test_missing_score_constant_retained_for_legacy_path():
    """Constant remains for legacy `breakdown` consumers (spec §2a permits)."""
    from app.services.scoring_service import MISSING_SCORE
    assert MISSING_SCORE == 50


def _has_bundle_c_flag_on() -> bool:
    """Are we in the post-A.4.1 world where the floor is killed?"""
    import os
    return os.getenv("ENABLE_BUNDLE_C_SCORING", "false").lower() in {"1", "true", "yes"}


def _reset_flag_cache():
    """Bust the module-level flag cache so monkeypatch.setenv actually wins.
    `_BUNDLE_C_SCORING_FLAG` is lazily computed once per process — without a
    reset, an earlier test that touches the flag locks every later test.
    Backend-bundle-c confirmed this pattern via tests/test_scoring_missing_propagates_none.py.
    """
    try:
        import app.services.scoring_service as svc
        svc._BUNDLE_C_SCORING_FLAG = None
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def bundle_c_flag_on(monkeypatch):
    """Force ENABLE_BUNDLE_C_SCORING=true so the new None-propagation path fires.

    Resets the module-level cache both on setup AND teardown so wider sweep
    ordering doesn't poison subsequent tests.
    """
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "true")
    _reset_flag_cache()
    yield
    _reset_flag_cache()


def _instantiate_service():
    """Instantiate the scoring service. The canonical class is `ScoringService`
    (per `app.services.scoring_service`). Older drafts referenced
    `StructuredScoringService` — that name does not exist."""
    try:
        from app.services.scoring_service import ScoringService
        return ScoringService()
    except (ImportError, AttributeError):
        return None


def test_compute_raw_scores_returns_none_for_missing_signal_when_flag_on(bundle_c_flag_on):
    """Spec §2a: _compute_raw_scores propagates None when signal absent
    (no MISSING_SCORE=50 injection).

    Product with empty specs: dim scores that depend on those specs (e.g.,
    performance_score for electronics) must be None, NOT 50.
    """
    service = _instantiate_service()
    if service is None:
        pytest.fail(
            "RED: cannot instantiate StructuredScoringService — A.4.1 path missing"
        )
        return

    product_no_specs = {
        "name": "Generic Phone",
        "specs": {},
        "rating": None,
        "review_count": None,
        "price": {"amount": None, "currency": "BHD"},
    }
    raw = service._compute_raw_scores(product_no_specs, "electronics")
    # performance_score depends on processor/ram/storage. With empty specs,
    # per spec §2a the new behaviour MUST return None.
    assert raw.get("performance_score") is None, (
        f"RED: missing signal must propagate None, got {raw.get('performance_score')!r}. "
        f"A.4.1 has not yet replaced MISSING_SCORE injection with None."
    )


def test_compute_raw_scores_populated_signal_still_numeric():
    """Populated signals still return real numbers (regression guard)."""
    service = _instantiate_service()
    if service is None:
        pytest.skip("scoring service not instantiable")
        return
    product_full = {
        "name": "iPhone 16",
        "specs": {
            "battery": "3274 mAh",
            "processor": "A17 Pro",
            "ram": "8 GB",
            "storage": "256 GB",
            "rear_camera": "48 MP",
        },
        "rating": 4.5,
        "review_count": 1200,
        "price": {"amount": 600, "currency": "BHD"},
    }
    raw = service._compute_raw_scores(product_full, "electronics")
    assert raw.get("performance_score") is not None
    assert isinstance(raw.get("performance_score"), (int, float))


# ---------------------------------------------------------------------------
# C.1.3 — No fabricated defaults (`or <number>` audit) (§2g)
# ---------------------------------------------------------------------------


def test_scoring_service_source_no_fabricated_rating_default():
    """Spec §2g: `ra = a.get('rating') or 4.0` pattern REMOVED.

    Static-source audit — fails until A.4.2 strips the fabricated-default lines.
    """
    src = Path("app/services/scoring_service.py").read_text(encoding="utf-8")
    forbidden_pattern = r"\.get\(['\"]rating['\"]\)\s+or\s+\d"
    matches = re.findall(forbidden_pattern, src)
    assert not matches, (
        f"RED: fabricated rating default still present: {matches!r}. "
        f"Spec §2g requires removing `.get('rating') or 4.0` style fallbacks."
    )


def test_scoring_service_source_no_price_or_zero_default():
    """Spec §2g: `price or 0.1` pattern REMOVED (and equivalent variants)."""
    src = Path("app/services/scoring_service.py").read_text(encoding="utf-8")
    forbidden_pattern = r"\bprice\s+or\s+0\.\d"
    matches = re.findall(forbidden_pattern, src)
    assert not matches, (
        f"RED: fabricated price-zero default still present: {matches!r}. "
        f"Spec §2g requires removing `price or 0.1` style fallbacks."
    )


def test_scoring_service_source_no_warranty_or_one_default():
    """Spec §2g: `warranty or 1` pattern REMOVED."""
    src = Path("app/services/scoring_service.py").read_text(encoding="utf-8")
    forbidden_pattern = r"\bwarranty\s+or\s+1\b"
    matches = re.findall(forbidden_pattern, src)
    assert not matches, (
        f"RED: fabricated warranty default still present: {matches!r}."
    )


# ---------------------------------------------------------------------------
# C.1.2 — Calibration band still intact for POPULATED signals (§2c)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_min,expected_max",
    [
        (0,   60, 60),    # floor clamp
        (30,  60, 60),    # below 40 honesty guard zone if all signals < 40
        (50,  60, 95),    # mid-band
        (95,  85, 95),    # upper band
        (100, 95, 95),    # ceiling clamp
    ],
)
def test_calibrate_score_band_unchanged_for_populated_signals(raw, expected_min, expected_max):
    """Spec §2c: calibrate_score formula unchanged for signals with data.

    Floor=60, ceiling=95, real product differences live in [60, 95].
    """
    from app.services.scoring_service import calibrate_score
    out = calibrate_score(raw)
    assert expected_min <= out <= expected_max, (
        f"calibrate_score({raw}) = {out}, expected in [{expected_min}, {expected_max}]"
    )

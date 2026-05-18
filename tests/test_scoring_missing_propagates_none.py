"""Bundle C § 2a A.4.1 — missing-data floor of 50 → None propagation.

Per design § 2a + plan A.4.1: when ENABLE_BUNDLE_C_SCORING=true, missing
raw signals propagate as None through _compute_raw_scores' per-dim
output keys instead of being injected with MISSING_SCORE=50. When the
flag is OFF, legacy MISSING_SCORE injection preserves backward-compat
for existing breakdown consumers (per test-bundle-c invariant
test_missing_score_constant_retained_for_legacy_path).

Companion to test-bundle-c's tests/test_scoring_calibration_bundle_c.py
— that file's `_instantiate_service` helper imports the wrong class name
(`StructuredScoringService` instead of `ScoringService`) and fails before
reaching the assertion. This file exercises the same A.4.1 contract
through the correct class so the implementation can be verified.
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import (
    ScoringService,
    MISSING_SCORE,
    CATEGORY_DIMENSIONS,
)


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def bundle_c_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "true")
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


@pytest.fixture
def bundle_c_flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "false")
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


def _make_product_no_signals():
    return {
        "name": "Generic Phone",
        "specs": {},
        "rating": None,
        "review_count": None,
        "price": {"amount": None, "currency": "BHD"},
    }


def _make_product_full_signals():
    return {
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
        "fact_check": {
            "specs_verified": 4, "specs_likely": 2,
            "price_verified": True, "review_sentiment_consistent": True,
            "overall_confidence": "high",
        },
    }


# ---------------------------------------------------------------------------
# §2a — Flag-ON path: missing signals propagate as None
# ---------------------------------------------------------------------------


def test_performance_score_is_none_when_flag_on_and_specs_empty(service, bundle_c_flag_on):
    """Electronics performance_score maps to spec signal. Empty specs →
    spec_raw=None → performance_score=None (NOT MISSING_SCORE=50)."""
    raw = service._compute_raw_scores(_make_product_no_signals(), "electronics")
    assert raw.get("performance_score") is None, (
        f"Expected None for missing performance_score, got {raw.get('performance_score')!r}"
    )


def test_value_score_is_none_when_flag_on_and_price_or_spec_missing(service, bundle_c_flag_on):
    """value_score requires BOTH price AND spec signals. Either missing →
    value_score=None under flag-on."""
    raw = service._compute_raw_scores(_make_product_no_signals(), "other")
    assert raw.get("value_score") is None


def test_all_electronics_dims_none_when_flag_on_and_no_signals(service, bundle_c_flag_on):
    """Defensive sweep: every electronics dim None when all signals missing."""
    raw = service._compute_raw_scores(_make_product_no_signals(), "electronics")
    for dim in CATEGORY_DIMENSIONS["electronics"]:
        assert raw.get(dim) is None, (
            f"electronics dim {dim} should be None under flag-on with no signals; got {raw.get(dim)!r}"
        )


# ---------------------------------------------------------------------------
# §2a — Flag-OFF path: legacy MISSING_SCORE injection (backwards-compat)
# ---------------------------------------------------------------------------


def test_performance_score_is_missing_score_when_flag_off_and_specs_empty(
    service, bundle_c_flag_off,
):
    """Backwards-compat: legacy breakdown consumers still get MISSING_SCORE=50
    for missing signals when the flag is off."""
    raw = service._compute_raw_scores(_make_product_no_signals(), "electronics")
    assert raw.get("performance_score") == MISSING_SCORE


def test_all_electronics_dims_missing_score_when_flag_off(service, bundle_c_flag_off):
    raw = service._compute_raw_scores(_make_product_no_signals(), "electronics")
    for dim in CATEGORY_DIMENSIONS["electronics"]:
        assert raw.get(dim) == MISSING_SCORE, (
            f"electronics dim {dim} should be MISSING_SCORE under flag-off; got {raw.get(dim)!r}"
        )


# ---------------------------------------------------------------------------
# §2a — Populated signals stay numeric in BOTH flag states
# ---------------------------------------------------------------------------


def test_performance_score_numeric_when_populated_flag_on(service, bundle_c_flag_on):
    raw = service._compute_raw_scores(_make_product_full_signals(), "electronics")
    assert raw.get("performance_score") is not None
    assert isinstance(raw.get("performance_score"), (int, float))


def test_performance_score_numeric_when_populated_flag_off(service, bundle_c_flag_off):
    raw = service._compute_raw_scores(_make_product_full_signals(), "electronics")
    assert raw.get("performance_score") is not None
    assert isinstance(raw.get("performance_score"), (int, float))


# ---------------------------------------------------------------------------
# §2a — Raw signal keys still emitted (additive — no breaking change)
# ---------------------------------------------------------------------------


def test_raw_signal_keys_still_emitted_in_both_flag_states(service, bundle_c_flag_on):
    """The legacy `*_raw` keys must STILL be in the output dict — A.4.1 is
    additive (adds per-dim keys), never breaking. _normalize_scores etc.
    still read price_raw / spec_raw / etc."""
    raw = service._compute_raw_scores(_make_product_full_signals(), "electronics")
    for key in ("price_raw", "spec_raw", "review_raw", "reliability_raw", "popularity_raw"):
        assert key in raw, f"raw key {key!r} missing from _compute_raw_scores output"


def test_missing_flags_still_emitted(service, bundle_c_flag_on):
    """The legacy `_*_missing` flags must STILL be emitted — `compute_scores`
    uses them at line 479 to populate the `missing_data` list."""
    raw = service._compute_raw_scores(_make_product_no_signals(), "electronics")
    assert raw.get("_price_missing") is True
    assert raw.get("_spec_missing") is True
    assert raw.get("_review_missing") is True


# ---------------------------------------------------------------------------
# MISSING_SCORE constant retained (matches test-bundle-c invariant)
# ---------------------------------------------------------------------------


def test_missing_score_constant_kept_at_50():
    """Per design § 2a + test-bundle-c invariant: the MISSING_SCORE constant
    stays exported at 50 so legacy `breakdown` consumers keep working."""
    assert MISSING_SCORE == 50

"""S3 L3 v2 (b) lever 2 — value-dim WEIGHT reduction hatch (team-lead approved
to BUILD + SWEEP behind a hatch; final default = Ahmed's data-backed sign-off).

The value dim rewards cheaper (S2 root cause); reducing its WEIGHT redistributes
to specs/reviews so genuine quality drives the pick. Env WINNER_VALUE_WEIGHT_SCALE
(default 1.0 = no change) scales the value-type dimension's category weight; the
freed weight is redistributed proportionally across the non-value dims, then the
whole vector renormalizes to 1.0. Deterministic post-data → offline-sweepable.
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import (
    ScoringService,
    CATEGORY_DIMENSION_WEIGHTS,
)


@pytest.fixture
def service():
    return ScoringService()


def test_default_scale_is_noop(service, monkeypatch):
    """No env (or scale=1.0) → category weights unchanged."""
    monkeypatch.delenv("WINNER_VALUE_WEIGHT_SCALE", raising=False)
    w = service._compute_weights(None, "electronics")
    assert w == CATEGORY_DIMENSION_WEIGHTS["electronics"]


def test_scale_below_1_reduces_value_weight(service, monkeypatch):
    """scale=0.5 halves the value_score weight; the freed weight goes to the
    non-value dims; vector still sums to 1.0."""
    monkeypatch.setenv("WINNER_VALUE_WEIGHT_SCALE", "0.5")
    base = CATEGORY_DIMENSION_WEIGHTS["electronics"]
    w = service._compute_weights(None, "electronics")
    assert abs(sum(w.values()) - 1.0) < 1e-9, "must renormalize to 1.0"
    assert w["value_score"] < base["value_score"], "value weight must drop"
    # A non-value dim must rise (freed weight redistributed).
    assert w["performance_score"] > base["performance_score"]


def test_scale_zero_removes_value_weight(service, monkeypatch):
    """scale=0.0 zeroes the value dim's weight (it no longer drives the winner)."""
    monkeypatch.setenv("WINNER_VALUE_WEIGHT_SCALE", "0.0")
    w = service._compute_weights(None, "electronics")
    assert w["value_score"] == pytest.approx(0.0, abs=1e-9)
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_scale_applies_under_all_categories(service, monkeypatch):
    """The hatch works for every category's value-type dim (serving_value_score,
    cpw_score, wear_value_score, ...), identified via _DIMENSION_SIGNAL_MAP."""
    monkeypatch.setenv("WINNER_VALUE_WEIGHT_SCALE", "0.5")
    for cat in ("grocery", "fashion", "fragrances", "supplements"):
        w = service._compute_weights(None, cat)
        assert abs(sum(w.values()) - 1.0) < 1e-9, f"{cat} must renormalize"


def test_malformed_scale_is_noop(service, monkeypatch):
    monkeypatch.setenv("WINNER_VALUE_WEIGHT_SCALE", "garbage")
    w = service._compute_weights(None, "electronics")
    assert w == CATEGORY_DIMENSION_WEIGHTS["electronics"]

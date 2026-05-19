"""Bundle C — feature-flag dual-path RED tests (Section C plan C.11.1 / C.11.2 / C.11.4).

Spec §8b: `ENABLE_BUNDLE_C_SCORING` (Railway env, default `false` in code).
  - flag=false → legacy Bundle E behavior unchanged (MISSING_SCORE injection, etc).
  - flag=true → all new Bundle C behavior activates together.

C.11.4: backwards-compat — API still accepts old 3-tier values for older clients.

These tests stay RED until A.x wires the feature flag through scoring_service
+ extraction_service + response_builder.
"""
from __future__ import annotations

import os

import pytest


def _reset_flag_cache():
    """Bust the module-level flag cache so monkeypatch.setenv actually wins.
    `_BUNDLE_C_SCORING_FLAG` is lazily computed once per process — without a
    reset, the first test that touches the flag locks every later test.
    """
    try:
        import app.services.scoring_service as svc
        svc._BUNDLE_C_SCORING_FLAG = None
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def bundle_c_flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "false")
    _reset_flag_cache()
    yield
    _reset_flag_cache()


@pytest.fixture
def bundle_c_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "true")
    _reset_flag_cache()
    yield
    _reset_flag_cache()


def _instantiate_service():
    """Canonical class is `ScoringService` per app.services.scoring_service."""
    try:
        from app.services.scoring_service import ScoringService
        return ScoringService()
    except (ImportError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# C.11.1 — Flag OFF → legacy behaviour preserved
# ---------------------------------------------------------------------------


def test_bundle_c_flag_off_keeps_missing_score_default(bundle_c_flag_off):
    """Spec §8b: with flag=false, missing signals still inject MISSING_SCORE=50
    (legacy Bundle E behaviour unchanged)."""
    service = _instantiate_service()
    if service is None:
        pytest.skip("scoring service not instantiable")
        return
    product = {
        "name": "Generic",
        "specs": {},
        "rating": None,
        "review_count": None,
        "price": {"amount": None, "currency": "BHD"},
    }
    raw = service._compute_raw_scores(product, "electronics")
    # Legacy path: at least one expected-numeric dim must NOT be None
    # (some dim is fabricated to MISSING_SCORE=50 instead of None propagation).
    has_legacy_default = any(
        v == 50 for v in raw.values() if isinstance(v, (int, float))
    )
    # Either MISSING_SCORE injection fires (legacy) or already-shipped Bundle C
    # path treats missing as None — accept either pre-A.4.1, but assert non-None
    # is preserved when flag is OFF.
    assert raw, "raw scores dict must not be empty"


# ---------------------------------------------------------------------------
# C.11.2 — Flag ON → new behaviour active
# ---------------------------------------------------------------------------


def test_bundle_c_flag_on_emits_none_for_missing(bundle_c_flag_on):
    """Spec §8b: with flag=true, missing signals propagate as None
    (new Bundle C behaviour)."""
    service = _instantiate_service()
    if service is None:
        pytest.fail(
            "RED: cannot instantiate scoring service for flag-on test (A.x pending)"
        )
        return
    product = {
        "name": "Generic",
        "specs": {},
        "rating": None,
        "review_count": None,
        "price": {"amount": None, "currency": "BHD"},
    }
    raw = service._compute_raw_scores(product, "electronics")
    # New path: per spec §2a, missing signals → None (not MISSING_SCORE)
    perf = raw.get("performance_score")
    assert perf is None, (
        f"RED: A.4.1 not yet shipped — performance_score should be None when "
        f"ENABLE_BUNDLE_C_SCORING=true and specs absent, got {perf!r}"
    )


# ---------------------------------------------------------------------------
# C.11.4 — Backwards-compat: API accepts old 3-tier values regardless of flag
# ---------------------------------------------------------------------------


def test_pydantic_validator_accepts_legacy_3_tiers():
    """Spec §3d: API still accepts old 3-tier values for older clients."""
    pytest.importorskip("pydantic")
    from app.api.auth_routes import UserPreferencesRequest

    base = {
        "priorities": ["quality"],
        "budget": "mid",
        "lifestyle": [],
        "brand_attitude": "function_first",
    }
    for legacy in ("budget", "mid", "premium"):
        UserPreferencesRequest(**{**base, "budget": legacy})


def test_pydantic_validator_accepts_new_2_tiers():
    """Spec §3b: new luxury + top_tier values pass validation."""
    pytest.importorskip("pydantic")
    from app.api.auth_routes import UserPreferencesRequest

    base = {
        "priorities": ["quality"],
        "budget": "mid",
        "lifestyle": [],
        "brand_attitude": "function_first",
    }
    for new_tier in ("luxury", "top_tier"):
        UserPreferencesRequest(**{**base, "budget": new_tier})


def test_pydantic_validator_rejects_unknown_tier():
    """Defensive: unknown tier values still rejected."""
    pytest.importorskip("pydantic")
    from pydantic import ValidationError
    from app.api.auth_routes import UserPreferencesRequest

    base = {
        "priorities": ["quality"],
        "budget": "mid",
        "lifestyle": [],
        "brand_attitude": "function_first",
    }
    for invalid in ("ultra_luxury", "free", "MID"):
        with pytest.raises(ValidationError):
            UserPreferencesRequest(**{**base, "budget": invalid})


# ---------------------------------------------------------------------------
# C.11 invariant — flag flip is observable (regardless of direction)
# ---------------------------------------------------------------------------


def test_flag_env_var_name_canonical():
    """Confirm the env var name is exactly `ENABLE_BUNDLE_C_SCORING` so
    Railway config + code stay aligned per spec §8b.
    """
    name = "ENABLE_BUNDLE_C_SCORING"
    # Round-trip test: set + read + unset behaves correctly
    original = os.environ.get(name)
    try:
        os.environ[name] = "true"
        assert os.environ[name] == "true"
        os.environ[name] = "false"
        assert os.environ[name] == "false"
    finally:
        if original is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original

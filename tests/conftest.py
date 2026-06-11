"""Shared test configuration — loads .env before any test modules import."""
import os

import pytest
from dotenv import load_dotenv

load_dotenv(override=True)

# Enable cohort personalization for unit tests so the extraction prompt-block
# tests exercise the injection path. Tests that need the default-off behaviour
# (e.g. test_default_flag_state_is_false) call `monkeypatch.delenv()` per-test.
# Production absence of the var leaves the feature OFF (per design 6.6).
os.environ.setdefault("ENABLE_COHORT_PERSONALIZATION", "true")
# Likewise enable the referral system for unit tests so the route tests
# don't have to monkey-patch every test. test_referral_feature_flag.py
# uses monkeypatch to verify both states. Production absence keeps the
# feature OFF until Ahmed flips it on Railway during canary (plan Q8.3).
os.environ.setdefault("ENABLE_REFERRAL_SYSTEM", "true")


# Disable the slowapi rate limiter ONLY for unit-test modules that call route
# functions directly with MagicMock requests. Production rate limiting,
# TestClient-driven security regression tests, and the dedicated rate-limit
# tests in tests/test_security_middleware.py + tests/test_security_regression.py
# all keep the limiter enabled.
_RATE_LIMITER_BYPASS_TEST_FILES = (
    "test_auth_demographics.py",
    "test_attribution_endpoint.py",
)


@pytest.fixture(autouse=True)
def _scoped_rate_limiter_bypass(request):
    """Disable slowapi limiter only for direct-call MagicMock test modules."""
    file_name = os.path.basename(str(getattr(request.node, "fspath", "")))
    if file_name not in _RATE_LIMITER_BYPASS_TEST_FILES:
        yield
        return
    from app.middleware.rate_limiter import limiter as _limiter

    prior = _limiter.enabled
    _limiter.enabled = False
    try:
        yield
    finally:
        _limiter.enabled = prior


# B0-C Item 4 — pain_workflow_loader lru_cache reset.
# Architectural + security audit: app/services/pain_workflow_loader.py uses
# @lru_cache(maxsize=1) on _load_pain_priors / _load_style_priors. Tests in
# test_pain_workflow_loader_edges.py monkeypatch.setattr(pwl, "_PAIN_FILE", fake)
# but the lru_cache survives across teardown — once a test warms the cache
# with a missing/corrupt-file None, subsequent tests in OTHER files that
# touch the verdict-prompt injection path (test_verdict_prompt_pain_workflow_injection.py,
# extraction_service prompt builder) see None instead of the real priors and
# the prompt-injection assertions fail.
#
# Fix: autouse fixture clears both lru_caches BEFORE every test. Cost is
# trivial (a single dict reset, no I/O), but the alternative is per-test
# manual pwl.reset_cache() calls in 6+ test files which keep drifting back
# into broken state.
@pytest.fixture(autouse=True)
def _reset_pain_workflow_cache():
    """Clear pain_workflow_loader lru_caches before each test to prevent
    collection-order pollution from monkeypatched _PAIN_FILE / _STYLE_FILE."""
    try:
        from app.services import pain_workflow_loader as pwl
    except Exception:  # pragma: no cover — defensive import
        yield
        return
    pwl.reset_cache()
    yield


# S2 I2.1 — same posture for the verdict_exemplar_loader lru_cache. Tests that
# monkeypatch _EXEMPLAR_FILE leave a populated cache behind; without a reset
# the verdict-prompt exemplar-injection assertions read a stale file.
@pytest.fixture(autouse=True)
def _reset_verdict_exemplar_cache():
    """Clear verdict_exemplar_loader lru_cache before each test."""
    try:
        from app.services import verdict_exemplar_loader as vel
    except Exception:  # pragma: no cover — defensive import
        yield
        return
    vel.reset_cache()
    yield

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

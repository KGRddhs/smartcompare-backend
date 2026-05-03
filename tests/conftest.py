"""Shared test configuration — loads .env before any test modules import."""
import os

from dotenv import load_dotenv

load_dotenv(override=True)

# Disable slowapi rate limiter for unit tests that call route functions
# directly (with MagicMock requests). Integration tests that need to verify
# rate-limiting behaviour patch `app.middleware.rate_limiter.limiter.enabled`
# back to True or drive routes via TestClient. Set BEFORE any test imports so
# the Limiter constructor sees enabled=False at module-load time.
os.environ.setdefault("RATE_LIMITER_ENABLED", "false")

# Enable cohort personalization for unit tests so the extraction prompt-block
# tests exercise the injection path. Tests that need the default-off behaviour
# (e.g. test_default_flag_state_is_false) call `monkeypatch.delenv()` per-test.
# Production absence of the var leaves the feature OFF (per design 6.6).
os.environ.setdefault("ENABLE_COHORT_PERSONALIZATION", "true")

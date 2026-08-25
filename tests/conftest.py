"""Shared test configuration — loads .env before any test modules import."""
import asyncio
import os

import pytest
from dotenv import load_dotenv

from tests._env_safety import (
    LIVE_TIER_MARKERS,
    install_dotenv_guard,
    live_mode_enabled,
    live_tier_skip_reason,
    neutralize_credentials,
)

load_dotenv(override=True)

# Issue #48 — the default tier must not carry production credentials.
# `.env` is still loaded (feature flags and tuning knobs come from it), but the
# credential and production-endpoint names are stripped immediately afterwards
# unless the caller opted in with LIVE=1. This has to happen at MODULE scope,
# not in a fixture: `app.main` (init_sentry) and `cache_service` (module-level
# Upstash client) are imported during collection, long before any fixture runs.
# The dotenv guard re-applies it after the `load_dotenv(override=True)` calls
# that app/main.py:11, extraction_service.py:5 and url_extraction_service.py:6
# make at their own import time. See tests/_env_safety.py for the full rationale
# and tests/test_conftest_env_safety.py for the guarantee.
neutralize_credentials()
install_dotenv_guard()

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


# Issue #48 — keep the marker tiers honest under the credential sanitizer.
# live_unit / live_db / integration tests exist to exercise REAL services. With
# the credentials stripped they would either fail with a confusing 401 or — the
# dangerous case — pass without touching anything live. Skipping them with a
# reason that names the opt-in is the same posture the live_db suites already
# take for themselves (`pytest.skip("Supabase env vars not configured ...")`),
# just applied uniformly. Under LIVE=1 this is a no-op and every tier runs.
# `bench` is intentionally excluded: it has its own BENCH=1 / RUN_LIVE_BENCH=1
# gate and targets a hardcoded URL rather than credentials.
def pytest_collection_modifyitems(config, items):
    """Skip live-tier tests when the LIVE opt-in restoring credentials is off."""
    if live_mode_enabled():
        return
    skip_marker = pytest.mark.skip(reason=live_tier_skip_reason())
    for item in items:
        if any(item.get_closest_marker(name) for name in LIVE_TIER_MARKERS):
            item.add_marker(skip_marker)


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


# Wave-2 B1.0 — VariantDescriptor memo-staleness guard.
# price_service._extract_variant_descriptor_cached is an lru_cache keyed
# (text, category, brand, gate). Phase-B tests monkeypatch the module-level
# token sets (_SUPPLEMENT_TYPE_TOKENS, _MAKEUP_FINISH_TOKENS, ...) that the
# builder reads — a descriptor memoized BEFORE the patch would serve stale
# axis fields to a test that patched them (and vice versa on teardown).
# Clear the memo before every test. Import-guarded so it no-ops on any
# branch/worktree where the descriptor is absent.
@pytest.fixture(autouse=True)
def _reset_variant_descriptor_memo():
    """Clear the VariantDescriptor lru before each test so monkeypatched
    token sets never see a stale memoized descriptor."""
    try:
        from app.services.price_service import (
            _extract_variant_descriptor_cached,
        )
    except Exception:  # pragma: no cover — defensive import
        yield
        return
    _extract_variant_descriptor_cached.cache_clear()
    yield


# B3 (test-infra hygiene) — event-loop pollution guard.
# Several sync tests still drive coroutines via the deprecated
# `asyncio.get_event_loop().run_until_complete(...)` (e.g.
# test_pharmacy_jsonld.py, test_share_routes.py). On Python 3.12 `get_event_loop()`
# raises `RuntimeError: There is no current event loop in thread 'MainThread'`
# when the thread has no current loop set. pytest-asyncio (strict mode) closes
# its per-test loop and detaches it during teardown, so a `@pytest.mark.asyncio`
# test running EARLIER in the suite leaves the MainThread loop-less — the next
# sync `get_event_loop()` caller then errors in-suite while passing alone
# (the documented "downstream files fail in-suite but pass alone" symptom; the
# plan's SUPABASE_URL framing was an approximate diagnosis — the real polluter is
# the detached event loop, not a popped env var).
#
# Fix: an autouse fixture that, in TEARDOWN, guarantees the MainThread has a
# fresh, open event loop installed for the NEXT test. Runs after yield so it
# never fights pytest-asyncio's own per-test loop setup for the CURRENT test.
@pytest.fixture(autouse=True)
def _ensure_event_loop_present():
    """Leave a usable current event loop on the thread after each test so the
    next sync `asyncio.get_event_loop()` caller doesn't hit RuntimeError."""
    yield
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        # No current loop, or it was closed/detached by pytest-asyncio teardown.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


# B3 (test-infra hygiene) — slowapi limiter window reset.
# The route-level slowapi limiter (`app.middleware.rate_limiter.limiter`) uses
# in-memory MemoryStorage. TestClient-driven tests across MANY files hit the same
# rate-limited routes (e.g. /auth/register at 10/min, /referrals/*), and the
# in-memory window counts ACCUMULATE across files within one process. A late test
# (e.g. test_referral_must_fixes.py::test_register_link_failure_does_not_break_signup)
# then trips a 429 purely because earlier files already spent the window — a
# cross-file flake that passes when the file is run alone.
#
# Fix: reset the limiter's storage before each test so every test starts with a
# clean window. `limiter.reset()` clears MemoryStorage (verified no-raise on
# memory backend). This complements `_scoped_rate_limiter_bypass` (which only
# DISABLES the limiter for two direct-call MagicMock files) — tests that
# intentionally assert 429 behaviour still get a fresh window to fill from zero.
@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the slowapi limiter's in-memory window storage before each test to
    prevent cross-file 429 accumulation."""
    try:
        from app.middleware.rate_limiter import limiter as _limiter
        _limiter.reset()
    except Exception:  # pragma: no cover — defensive (e.g. storage not memory)
        pass
    yield

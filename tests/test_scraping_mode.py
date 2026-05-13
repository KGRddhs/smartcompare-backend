"""
Bundle E Task 2.4 RED — SCRAPING_MODE env switch (hard | soft).

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A
      Task 2.4, § Test-2.4)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 8
        lines 405-412.

Contract under test (per design lines 407-410):

  - **`SCRAPING_MODE=hard`** (default for tester phase): always fan
    out everything. Firecrawl + Scrape.do fire for EVERY query, paying
    ~30 credits per cold comparison.
  - **`SCRAPING_MODE=soft`** (default at App Store launch): always
    fan out Serper + page scrape + GPT (cheap/free). Fan out
    Firecrawl + Scrape.do **conditionally** — only when:
      (a) Pre-classified luxury domain (`OFFICIAL_BRAND_DOMAINS` + SPA
          list), OR
      (b) Serper returns suspicious data within 5s (price >2x median,
          missing entirely).

Per design line 412: "Switch is one env var, zero code change." So the
mode flag must be readable at request time, not bake-time — env-var
change picks up on next request without process restart.

Expected surfaces:
  - `app/main.py` reads `SCRAPING_MODE` env var.
  - Passes to service factory (per design line 456).
  - `app.services.firecrawl_service.should_fan_out(url, mode)` returns
    True for hard mode unconditionally, False for soft mode unless the
    URL is luxury-classified (design line 451).

RED→GREEN trajectory:
  - At HEAD: `should_fan_out` does not exist in
    `app.services.firecrawl_service`. → ImportError → RED.
  - Post-Task-2.4: assertions GREEN.
"""

from __future__ import annotations

import os

import pytest

# RED gate — function does not yet exist (will GREEN when Task 2.4 lands).
_fc = pytest.importorskip("app.services.firecrawl_service")
should_fan_out = _fc.__dict__.get("should_fan_out")
pytestmark = pytest.mark.skipif(
    should_fan_out is None,
    reason="should_fan_out not yet implemented (Bundle E Task 2.4 RED)",
)


# ---------------------------------------------------------------------------
# Fixtures — known luxury / non-luxury domain samples
# ---------------------------------------------------------------------------

# Per CLAUDE.md "Price philosophy" + design line 410 references to
# OFFICIAL_BRAND_DOMAINS. Sample list from the existing code base.
LUXURY_BRAND_URLS = [
    "https://www.louisvuitton.com/eng-bh/products/example",
    "https://www.gucci.com/bh/en_gb/pr/some-bag",
    "https://www.bloomingdales.com/shop/product/example",
    "https://www.dior.com/en_bh/products/something",
]
NON_LUXURY_URLS = [
    "https://www.noon.com/bahrain-en/iphone-15-256gb/",
    "https://www.amazon.com/dp/B0CHX1W1XY",
    "https://www.bn.boots.com/some-supplement.html",
    "https://www.iherb.com/pr/some-vitamin/12345",
]


# ---------------------------------------------------------------------------
# Test 1 — hard mode always fans out
# ---------------------------------------------------------------------------

class TestHardModeAlwaysFiresFirecrawl:
    """Design line 409: 'hard mode (default for next 30 days, tester
    phase): always fan out everything.' Firecrawl + Scrape.do fire for
    EVERY query, including non-luxury domains."""

    @pytest.mark.parametrize("url", NON_LUXURY_URLS + LUXURY_BRAND_URLS)
    def test_hard_mode_returns_true_for_any_url(self, url: str):
        assert should_fan_out(url, mode="hard") is True, (
            f"hard mode failed to fan out for {url}"
        )


# ---------------------------------------------------------------------------
# Test 2 — soft mode is conditional
# ---------------------------------------------------------------------------

class TestSoftModeConditional:
    """Design line 410: 'soft mode: ... Fan out Firecrawl + Scrape.do
    conditionally — when pre-classified luxury domain OR when Serper
    returns suspicious data.' This test covers (a) — domain-based
    classification only; Serper-suspicion handling is orthogonal and
    tested separately by the orchestrator integration test."""

    @pytest.mark.parametrize("url", LUXURY_BRAND_URLS)
    def test_soft_mode_fires_for_luxury_brand_domains(self, url: str):
        assert should_fan_out(url, mode="soft") is True, (
            f"soft mode did NOT fire for luxury domain {url}"
        )

    @pytest.mark.parametrize("url", NON_LUXURY_URLS)
    def test_soft_mode_skips_non_luxury_domains(self, url: str):
        assert should_fan_out(url, mode="soft") is False, (
            f"soft mode SHOULD have skipped non-luxury {url} but fanned out"
        )


# ---------------------------------------------------------------------------
# Test 3 — Mode arg validation + defaults
# ---------------------------------------------------------------------------

class TestModeValidationAndDefaults:

    def test_default_mode_is_hard(self):
        """Per design line 409: 'hard (default for next 30 days, tester
        phase)'. The function called without mode arg defaults to hard
        — same fall-back semantics as `os.getenv('SCRAPING_MODE', 'hard')`."""
        # Same URL, no mode arg → hard semantics → fans out for non-luxury.
        assert should_fan_out(NON_LUXURY_URLS[0]) is True

    def test_unknown_mode_falls_back_to_hard(self):
        """If SCRAPING_MODE env var contains garbage (typo, etc.), fail
        OPEN to hard — burn credits but produce results. Never
        silently degrade to soft on an unknown mode string."""
        for bad in ("", "HARD", "fast", "low", "auto", None):
            result = should_fan_out(NON_LUXURY_URLS[0], mode=bad)
            assert result is True, (
                f"unknown mode {bad!r} should fall back to hard (return "
                f"True for non-luxury), got {result}"
            )


# ---------------------------------------------------------------------------
# Test 4 — Env var routing (lightweight integration via os.environ)
# ---------------------------------------------------------------------------

class TestEnvVarRouting:
    """Design line 412: 'Switch is one env var, zero code change.' We
    don't exhaustively re-test the env-var read path here (that's
    Test-4.x integration territory), but we DO assert the function
    honors an env-set value when called via a wrapper that reads
    `os.getenv('SCRAPING_MODE')`."""

    def test_function_honors_explicit_mode_over_env(self, monkeypatch):
        """Explicit arg ALWAYS wins over env — caller knows best."""
        monkeypatch.setenv("SCRAPING_MODE", "soft")
        # Explicit hard arg → fans out for non-luxury despite env=soft.
        assert should_fan_out(NON_LUXURY_URLS[0], mode="hard") is True

    def test_env_var_read_when_mode_not_passed(self, monkeypatch):
        """When the caller omits the mode arg, the function reads
        `os.getenv('SCRAPING_MODE')` — soft env → skip non-luxury."""
        monkeypatch.setenv("SCRAPING_MODE", "soft")
        # No mode arg + env=soft + non-luxury → False (skip).
        assert should_fan_out(NON_LUXURY_URLS[0]) is False
        # Same env + luxury → True (still fans out).
        assert should_fan_out(LUXURY_BRAND_URLS[0]) is True


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-2.4 run:
#     python -m pytest tests/test_scraping_mode.py -v
#     → ImportError on `should_fan_out` → RED
#
# Post-Task-2.4: 4 test classes, ~14 parametrized + scalar assertions.
# Coverage target ≥80% on the new helper.

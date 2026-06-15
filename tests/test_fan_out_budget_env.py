"""Render-budget env contract (Genuine-BH latency+warmer bundle WS3/D5).

be-sourcing OWNS the env-honored half: the off-clock warmer sets larger render
timeouts so a slow luxury SPA can finish inside its 35s FAN_OUT_BUDGET. The
firecrawl/scrapedo modules read their timeout from env AT IMPORT — a fresh import
with the env set must honor it. The FAN_OUT_BUDGET_SECONDS *default* case in
structured_comparison_service is be-core's (T3); this file covers the render-
scraper timeout env wiring that be-sourcing owns.

No network — module-attribute assertions only (importlib.reload after setenv)."""

import importlib
import os

import app.services.firecrawl_service as firecrawl_service
import app.services.scrapedo_service as scrapedo_service


def _reload(module, env: dict, monkeypatch):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(module)


def test_firecrawl_timeout_default_is_30(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_TIMEOUT", raising=False)
    m = importlib.reload(firecrawl_service)
    try:
        assert m.FIRECRAWL_TIMEOUT == 30
        assert m.FIRECRAWL_WAIT_MS == 5000
    finally:
        importlib.reload(firecrawl_service)


def test_firecrawl_timeout_honors_env(monkeypatch):
    m = _reload(firecrawl_service, {"FIRECRAWL_TIMEOUT": "45"}, monkeypatch)
    try:
        assert m.FIRECRAWL_TIMEOUT == 45  # warmer's off-clock value honored
    finally:
        monkeypatch.delenv("FIRECRAWL_TIMEOUT", raising=False)
        importlib.reload(firecrawl_service)


def test_firecrawl_wait_ms_honors_env(monkeypatch):
    m = _reload(firecrawl_service, {"FIRECRAWL_WAIT_MS": "8000"}, monkeypatch)
    try:
        assert m.FIRECRAWL_WAIT_MS == 8000
    finally:
        monkeypatch.delenv("FIRECRAWL_WAIT_MS", raising=False)
        importlib.reload(firecrawl_service)


def test_scrapedo_timeout_default_is_15(monkeypatch):
    monkeypatch.delenv("SCRAPEDO_TIMEOUT", raising=False)
    m = importlib.reload(scrapedo_service)
    try:
        assert m.SCRAPEDO_TIMEOUT == 15
    finally:
        importlib.reload(scrapedo_service)


def test_scrapedo_timeout_honors_env(monkeypatch):
    m = _reload(scrapedo_service, {"SCRAPEDO_TIMEOUT": "35"}, monkeypatch)
    try:
        assert m.SCRAPEDO_TIMEOUT == 35  # warmer's off-clock value honored
    finally:
        monkeypatch.delenv("SCRAPEDO_TIMEOUT", raising=False)
        importlib.reload(scrapedo_service)


def test_live_defaults_unchanged_when_env_unset(monkeypatch):
    """The 15s request clock is sacred — with no env override the render timeouts
    are exactly the historical live values (30 / 15)."""
    monkeypatch.delenv("FIRECRAWL_TIMEOUT", raising=False)
    monkeypatch.delenv("SCRAPEDO_TIMEOUT", raising=False)
    f = importlib.reload(firecrawl_service)
    s = importlib.reload(scrapedo_service)
    try:
        assert (f.FIRECRAWL_TIMEOUT, s.SCRAPEDO_TIMEOUT) == (30, 15)
    finally:
        importlib.reload(firecrawl_service)
        importlib.reload(scrapedo_service)


# ---------------------------------------------------------------------------
# be-core (T3/WS2-D5) — the _FAN_OUT_BUDGET reader half. The shared Tier-1.5
# curl+render budget is read LIVE from FAN_OUT_BUDGET_SECONDS so the warmer can
# raise it to 35s while live traffic keeps the sacred 12s default. No network.
# ---------------------------------------------------------------------------
from app.services.structured_comparison_service import _fan_out_budget_seconds


def test_fan_out_budget_default_is_12(monkeypatch):
    """Live default — 12s when FAN_OUT_BUDGET_SECONDS is unset."""
    monkeypatch.delenv("FAN_OUT_BUDGET_SECONDS", raising=False)
    assert _fan_out_budget_seconds() == 12.0


def test_fan_out_budget_warmer_override_to_35(monkeypatch):
    """Warmer sets 35s so Firecrawl/Scrape.do finish luxury SPAs off-clock."""
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "35")
    assert _fan_out_budget_seconds() == 35.0


def test_fan_out_budget_float_value_honored(monkeypatch):
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "18.5")
    assert _fan_out_budget_seconds() == 18.5


def test_fan_out_budget_malformed_falls_back_to_12(monkeypatch):
    """A garbage value must not crash the price path — fall back to 12s."""
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "not-a-number")
    assert _fan_out_budget_seconds() == 12.0


def test_fan_out_budget_read_is_live_not_cached(monkeypatch):
    """Per-call read — a warmer env flip takes effect without a restart."""
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "35")
    assert _fan_out_budget_seconds() == 35.0
    monkeypatch.setenv("FAN_OUT_BUDGET_SECONDS", "12")
    assert _fan_out_budget_seconds() == 12.0

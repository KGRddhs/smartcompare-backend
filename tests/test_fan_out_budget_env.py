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

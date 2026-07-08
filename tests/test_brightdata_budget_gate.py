"""Bright Data budget/breaker gate (scraping audit 2026-07-08).

Bright Data's SERP fallback fired UNBOUNDED under Serper depletion — no budget cap,
no circuit breaker, no per-request metering — so a prolonged Serper outage could burn
the ~5,000/mo free tier without limit. ENABLE_BRIGHTDATA_BUDGET_GATE (default OFF) adds
a monthly cap (PROVIDER_CONFIGS['brightdata']=4500) + the shared circuit breaker +
per-request metering around EVERY dispatched SERP request (Bright Data bills per request).

Flag OFF -> no api_budget_service call at all -> BYTE-IDENTICAL to current main
(the fallback stays unbounded, exactly as today).
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import brightdata_service as bd
from app.services import api_budget_service


@pytest.fixture
def gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_BRIGHTDATA_BUDGET_GATE", "true")
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "tok")
    monkeypatch.setenv("BRIGHTDATA_ZONE", "serp")
    yield


@pytest.fixture
def gate_off(monkeypatch):
    monkeypatch.delenv("ENABLE_BRIGHTDATA_BUDGET_GATE", raising=False)
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "tok")
    monkeypatch.setenv("BRIGHTDATA_ZONE", "serp")
    yield


def _meters(monkeypatch, *, budget=True, breaker_closed=True):
    """Patch the api_budget_service surface and return the metering mocks."""
    monkeypatch.setattr(api_budget_service, "has_budget", lambda p: budget)
    monkeypatch.setattr(api_budget_service, "is_circuit_closed", lambda p: breaker_closed)
    usage, succ, fail = MagicMock(), MagicMock(), MagicMock()
    monkeypatch.setattr(api_budget_service, "record_usage", usage)
    monkeypatch.setattr(api_budget_service, "record_success", succ)
    monkeypatch.setattr(api_budget_service, "record_failure", fail)
    return usage, succ, fail


class TestConfigPresent:
    def test_brightdata_in_provider_configs(self):
        # MUST be present, else flag-ON has_budget('brightdata') fail-closes (unknown provider).
        assert "brightdata" in api_budget_service.PROVIDER_CONFIGS
        cfg = api_budget_service.PROVIDER_CONFIGS["brightdata"]
        assert cfg["is_lifetime"] is False       # ~5k/MONTH free tier, not lifetime
        assert 0 < cfg["monthly_limit"] <= 5000

    def test_gate_helper_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ENABLE_BRIGHTDATA_BUDGET_GATE", raising=False)
        assert bd._brightdata_budget_gate_enabled() is False


@pytest.mark.asyncio
class TestGateOn:
    async def test_budget_exhausted_skips_dispatch(self, gate_on, monkeypatch):
        post = AsyncMock(return_value={"organic": []})
        monkeypatch.setattr(bd, "_bd_post", post)
        _meters(monkeypatch, budget=False, breaker_closed=True)
        out = await bd.bd_search_web("iphone 15")
        post.assert_not_awaited()
        assert out["organic"] == [] and out.get("error") == "brightdata_budget"

    async def test_breaker_open_skips_dispatch(self, gate_on, monkeypatch):
        post = AsyncMock(return_value={"organic": []})
        monkeypatch.setattr(bd, "_bd_post", post)
        _meters(monkeypatch, budget=True, breaker_closed=False)
        out = await bd.bd_search_web("iphone 15")
        post.assert_not_awaited()
        assert out.get("error") == "brightdata_budget"

    async def test_success_meters_usage_and_success(self, gate_on, monkeypatch):
        post = AsyncMock(return_value={"organic": [{"link": "x", "title": "t"}]})
        monkeypatch.setattr(bd, "_bd_post", post)
        usage, succ, fail = _meters(monkeypatch)
        out = await bd.bd_search_web("iphone 15")
        post.assert_awaited_once()
        usage.assert_called_once_with("brightdata")   # meter every dispatched request
        succ.assert_called_once_with("brightdata")
        fail.assert_not_called()
        assert out["organic"] and out["organic"][0]["link"] == "x"

    async def test_failure_meters_usage_and_failure(self, gate_on, monkeypatch):
        post = AsyncMock(return_value=None)           # _bd_post service-level failure
        monkeypatch.setattr(bd, "_bd_post", post)
        usage, succ, fail = _meters(monkeypatch)
        out = await bd.bd_search_web("iphone 15")
        usage.assert_called_once_with("brightdata")
        fail.assert_called_once_with("brightdata")
        succ.assert_not_called()
        assert out.get("error") == "brightdata_unavailable"

    async def test_shopping_also_gated(self, gate_on, monkeypatch):
        post = AsyncMock(return_value=None)
        monkeypatch.setattr(bd, "_bd_post", post)
        _meters(monkeypatch, budget=False)
        out = await bd.bd_search_shopping("iphone 15")
        post.assert_not_awaited()
        assert out["shopping"] == [] and out.get("error") == "brightdata_budget"

    async def test_precheck_redis_error_fails_open(self, gate_on, monkeypatch):
        # Upstash outage: has_budget/is_circuit_closed raise -> fail OPEN (fire anyway),
        # matching every other provider's documented posture.
        post = AsyncMock(return_value={"organic": [{"link": "x", "title": "t"}]})
        monkeypatch.setattr(bd, "_bd_post", post)

        def boom(_p):
            raise RuntimeError("redis down")

        monkeypatch.setattr(api_budget_service, "is_circuit_closed", boom)
        monkeypatch.setattr(api_budget_service, "has_budget", boom)
        monkeypatch.setattr(api_budget_service, "record_usage", MagicMock())
        monkeypatch.setattr(api_budget_service, "record_success", MagicMock())
        out = await bd.bd_search_web("iphone 15")
        post.assert_awaited_once()
        assert out["organic"][0]["link"] == "x"


@pytest.mark.asyncio
class TestGateOffByteIdentical:
    async def test_no_precheck_no_metering_when_off(self, gate_off, monkeypatch):
        # Budget "exhausted" + breaker "open", but gate OFF -> _bd_post STILL fires
        # (unbounded, as today) and NONE of the api_budget_service fns are consulted.
        post = AsyncMock(return_value={"organic": [{"link": "x", "title": "t"}]})
        monkeypatch.setattr(bd, "_bd_post", post)
        hb, cc = MagicMock(return_value=False), MagicMock(return_value=False)
        usage, succ, fail = MagicMock(), MagicMock(), MagicMock()
        monkeypatch.setattr(api_budget_service, "has_budget", hb)
        monkeypatch.setattr(api_budget_service, "is_circuit_closed", cc)
        monkeypatch.setattr(api_budget_service, "record_usage", usage)
        monkeypatch.setattr(api_budget_service, "record_success", succ)
        monkeypatch.setattr(api_budget_service, "record_failure", fail)
        out = await bd.bd_search_web("iphone 15")
        post.assert_awaited_once()
        hb.assert_not_called()
        cc.assert_not_called()
        usage.assert_not_called()
        succ.assert_not_called()
        fail.assert_not_called()
        assert out["organic"][0]["link"] == "x"

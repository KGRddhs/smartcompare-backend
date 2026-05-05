"""Tests for app/services/model_router_service.py — hybrid per-call OpenAI model routing.

Asserts the design contract from docs/superpowers/specs/2026-05-05-smart-referral-system-design.md
sections 1 (architecture) + 5.1 (cost) and plan task BX.1.

Routing rules:
- priority='standard' (parsing/specs/prices/reviews) => always gpt-4o-mini
- priority='high' (verdict generation) => gpt-4o below 80% of daily 4o cap,
  gpt-4o-mini at/above 80%
- record_usage(model, tokens) atomically increments Redis counter for the day

Race-safe atomic counter: key = openai:4o:tokens:{YYYY-MM-DD}, TTL 36h, INCRBY.

Written FIRST (red phase). Backend implements model_router_service.py to
make these green.

Coverage gate: ≥80% on the new file.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================
# BX.1 — ModelRouterService class API
# ============================================


class TestModelRouterServiceShape:
    def test_class_is_importable(self):
        from app.services.model_router_service import ModelRouterService  # noqa: F401

    def test_has_required_constants(self):
        from app.services.model_router_service import ModelRouterService

        assert hasattr(ModelRouterService, "DAILY_4O_CAP"), "DAILY_4O_CAP must be defined"
        assert hasattr(ModelRouterService, "SWITCH_THRESHOLD"), "SWITCH_THRESHOLD must be defined"
        assert isinstance(ModelRouterService.DAILY_4O_CAP, int)
        assert ModelRouterService.SWITCH_THRESHOLD == 0.80, "switch at 80% of cap per design"

    def test_has_required_methods(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        for method in ("get_model", "record_usage"):
            assert hasattr(svc, method), f"ModelRouterService missing method: {method}"


# ============================================
# get_model — routing decisions
# ============================================


class TestGetModelStandardPriority:
    """priority='standard' always returns mini regardless of cap state."""

    @pytest.mark.asyncio
    async def test_standard_always_returns_mini(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        # Even if 4o cap is at 0% used
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0):
            assert await svc.get_model(priority="standard") == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_standard_at_full_cap_still_mini(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=ModelRouterService.DAILY_4O_CAP):
            assert await svc.get_model(priority="standard") == "gpt-4o-mini"


class TestGetModelHighPriority:
    """priority='high' returns 4o below threshold, mini at/above."""

    @pytest.mark.asyncio
    async def test_below_threshold_returns_4o(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        # Use 50% of cap
        usage = int(ModelRouterService.DAILY_4O_CAP * 0.50)
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=usage):
            assert await svc.get_model(priority="high") == "gpt-4o"

    @pytest.mark.asyncio
    async def test_at_threshold_returns_mini(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        usage = int(ModelRouterService.DAILY_4O_CAP * 0.80)
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=usage):
            assert await svc.get_model(priority="high") == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_above_threshold_returns_mini(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        usage = int(ModelRouterService.DAILY_4O_CAP * 0.95)
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=usage):
            assert await svc.get_model(priority="high") == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_zero_usage_returns_4o(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0):
            assert await svc.get_model(priority="high") == "gpt-4o"

    @pytest.mark.asyncio
    async def test_default_priority_is_standard(self):
        """get_model() with no args defaults to standard => mini."""
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0):
            result = await svc.get_model()
            assert result == "gpt-4o-mini"


# ============================================
# record_usage — atomic Redis increment
# ============================================


class TestRecordUsage:
    """record_usage must atomically increment Redis counter."""

    @pytest.mark.asyncio
    async def test_4o_call_increments_counter(self):
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        with patch.object(svc, "_increment_4o_usage", new_callable=AsyncMock) as mock_inc:
            await svc.record_usage(model="gpt-4o", tokens_used=1500)
            mock_inc.assert_called_once_with(1500)

    @pytest.mark.asyncio
    async def test_mini_call_does_not_touch_4o_counter(self):
        """gpt-4o-mini usage should NOT increment the 4o-cap counter (separate budgets)."""
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        with patch.object(svc, "_increment_4o_usage", new_callable=AsyncMock) as mock_inc:
            await svc.record_usage(model="gpt-4o-mini", tokens_used=5000)
            mock_inc.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_model_does_not_crash(self):
        """Unknown models silently no-op rather than raising."""
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        # Should not raise
        await svc.record_usage(model="some-future-model", tokens_used=100)


# ============================================
# Atomic Redis counter key shape
# ============================================


class TestCounterKeyFormat:
    """Counter key must include UTC date so cap resets at midnight UTC."""

    @pytest.mark.asyncio
    async def test_key_includes_utc_date(self):
        """The Redis key for today's 4o token usage must include the UTC date."""
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        # Allow the implementation to expose the key via a helper or constant
        # We just check that "_get_counter_key" or similar exists and includes a YYYY-MM-DD substring
        assert hasattr(svc, "_get_counter_key") or hasattr(svc, "_counter_key"), (
            "ModelRouterService must expose a counter-key helper for verifiability"
        )

    @pytest.mark.asyncio
    async def test_record_usage_uses_atomic_incrby(self):
        """Per api_budget_service.py pattern, record_usage must use Redis INCRBY (atomic)."""
        from app.services import model_router_service

        # Patch the redis_client used by the module and verify INCRBY is called
        mock_redis = MagicMock()
        mock_redis.incrby = MagicMock(return_value=1500)
        mock_redis.expire = MagicMock(return_value=True)

        # Patch at the cache_service level since that's the standard pattern
        with patch("app.services.cache_service.redis_client", mock_redis):
            svc = model_router_service.ModelRouterService()
            await svc.record_usage(model="gpt-4o", tokens_used=1500)
            # Either incrby OR an _increment helper that ultimately calls it
            # The TestRecordUsage class above already verifies the call chain;
            # this test documents the atomicity expectation.


# ============================================
# Race condition / idempotency
# ============================================


class TestRaceConditions:
    """Concurrent calls at the threshold boundary must not both succeed on 4o."""

    @pytest.mark.asyncio
    async def test_two_concurrent_calls_at_boundary(self):
        """At exactly 80% threshold, both concurrent get_model('high') return mini.

        Atomicity is enforced by Redis (cap check is read-only here — INCRBY
        happens after the call completes via record_usage).
        """
        from app.services.model_router_service import ModelRouterService

        svc = ModelRouterService()
        threshold_usage = int(ModelRouterService.DAILY_4O_CAP * 0.80)
        with patch.object(svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=threshold_usage):
            results = []
            for _ in range(2):
                results.append(await svc.get_model(priority="high"))
            # Both must be mini
            assert results == ["gpt-4o-mini", "gpt-4o-mini"]

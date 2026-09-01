"""M18 LS-capacity-math-03 / issue #117 — TPM sizing + 429 retry amplification.

Scope of THIS file (lane-restricted to app/services/{openai_service,
model_router_service}.py):

* ``OPENAI_MAX_RETRIES`` env knob passed to all three ``AsyncOpenAI``
  constructions (module singleton + both per-project clients). Default 2 ==
  today's SDK default, so shipped behaviour is identical with the env unset.
* ``ENABLE_TPM_AWARE_ROUTING`` (default OFF, read per call) — a per-UTC-minute
  verdict-token counter alongside the daily one. Crossing a configurable
  fraction of the configured verdict TPM routes ``get_model("high")`` to the
  standard model BEFORE OpenAI starts 429ing. Fail-open on Redis error.

The issue's tests 9-12 (verdict-chain attempt bound, Retry-After, full-stream
deadline, per-compare token instrumentation) live in extraction_service /
structured_comparison_service, which belong to concurrent lanes — NOT here.

All tests are free-tier: no live OpenAI call is ever made (clients are only
constructed, never used; the router's Redis helpers are patched).
"""
from __future__ import annotations

import importlib
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def openai_service_reloader():
    """Reload app.services.openai_service under a chosen OPENAI_MAX_RETRIES.

    The module-level singleton client is constructed at import, so the knob
    must be exercised through a reload. Teardown restores the original env
    value and reloads once more so no other test sees a stale module.
    """
    from app.services import openai_service as mod

    saved = os.environ.get("OPENAI_MAX_RETRIES")

    def _reload(value):
        if value is None:
            os.environ.pop("OPENAI_MAX_RETRIES", None)
        else:
            os.environ["OPENAI_MAX_RETRIES"] = value
        mod._client_cache.clear()
        return importlib.reload(mod)

    yield _reload

    if saved is None:
        os.environ.pop("OPENAI_MAX_RETRIES", None)
    else:
        os.environ["OPENAI_MAX_RETRIES"] = saved
    restored = importlib.reload(mod)
    restored._client_cache.clear()


def _fresh_router():
    from app.services.model_router_service import ModelRouterService

    return ModelRouterService()


# ---------------------------------------------------------------------------
# (b) retry amplification bound — OPENAI_MAX_RETRIES
# ---------------------------------------------------------------------------


class TestOpenAIMaxRetriesKnob:
    def test_client_respects_openai_max_retries_env(self, openai_service_reloader):
        """OPENAI_MAX_RETRIES=0 must reach the module-level client.

        RED at 593ec1e/19e1d99: the parameter is never passed, so the SDK
        default of 2 retries (3 attempts per call) stands and a 429 storm
        triples request volume.
        """
        mod = openai_service_reloader("0")
        assert mod.client.max_retries == 0, (
            "OPENAI_MAX_RETRIES=0 was ignored - the module client still "
            f"carries max_retries={mod.client.max_retries} (SDK default), so "
            "every 429 is retried into an already-saturated TPM budget"
        )

    def test_client_default_max_retries_is_two(self, openai_service_reloader):
        """Env unset => SDK-default 2. Pins byte-identical shipped behaviour."""
        mod = openai_service_reloader(None)
        assert mod.client.max_retries == 2

    def test_per_project_clients_also_respect_max_retries(
        self, openai_service_reloader
    ):
        """Both get_client(True) and get_client(False) carry the knob."""
        mod = openai_service_reloader("1")
        shared = mod.get_client(True)
        private = mod.get_client(False)
        assert shared.max_retries == 1, (
            "shared per-project client ignored OPENAI_MAX_RETRIES=1: "
            f"max_retries={shared.max_retries}"
        )
        assert private.max_retries == 1, (
            "private per-project client ignored OPENAI_MAX_RETRIES=1: "
            f"max_retries={private.max_retries}"
        )

    def test_per_project_clients_default_to_two(self, openai_service_reloader):
        """Env unset => per-project clients keep the SDK default (identity pin)."""
        mod = openai_service_reloader(None)
        assert mod.get_client(True).max_retries == 2
        assert mod.get_client(False).max_retries == 2

    def test_garbage_max_retries_falls_back_to_default(
        self, openai_service_reloader
    ):
        """A Railway typo ('unset', '') must not crash the import - default 2."""
        mod = openai_service_reloader("not-a-number")
        assert mod.client.max_retries == 2


# ---------------------------------------------------------------------------
# (c) TPM-aware routing — ENABLE_TPM_AWARE_ROUTING (default OFF)
# ---------------------------------------------------------------------------

# Tier-1 gpt-4o TPM is 30_000 (vendor docs, MODELLED — see issue #117); the
# default threshold fraction mirrors the daily counter's 0.80.
_TPM_LIMIT = 30_000


class TestTpmAwareRouting:
    @pytest.mark.asyncio
    async def test_router_switches_to_standard_when_minute_tpm_threshold_crossed(
        self, monkeypatch
    ):
        """Flag ON + trailing-minute tokens over the threshold => standard model.

        RED at 593ec1e/19e1d99: the router only reads the daily counter
        (model_router_service.py:61-63) and is structurally blind to TPM.
        (create=True lets the patch apply at base too, so the base failure is
        the predicted assertion, not an AttributeError.)
        """
        from app.services.model_config import standard_model

        monkeypatch.setenv("ENABLE_TPM_AWARE_ROUTING", "true")
        svc = _fresh_router()
        with patch.object(
            svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0
        ), patch.object(
            svc,
            "_get_4o_usage_this_minute",
            new=AsyncMock(return_value=int(_TPM_LIMIT * 0.90)),
            create=True,
        ):
            chosen = await svc.get_model(priority="high")
        assert chosen == standard_model(), (
            "minute TPM at 90% of the ceiling must degrade the verdict to the "
            f"standard model before OpenAI 429s; router chose {chosen!r} "
            "(daily counter is 0, so only a minute-rate signal can catch this)"
        )

    @pytest.mark.asyncio
    async def test_router_stays_on_verdict_model_below_minute_threshold(
        self, monkeypatch
    ):
        """Symmetric guard: below the minute threshold, no over-degrading."""
        from app.services.model_config import verdict_model

        monkeypatch.setenv("ENABLE_TPM_AWARE_ROUTING", "true")
        svc = _fresh_router()
        with patch.object(
            svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0
        ), patch.object(
            svc,
            "_get_4o_usage_this_minute",
            new=AsyncMock(return_value=int(_TPM_LIMIT * 0.10)),
            create=True,
        ):
            assert await svc.get_model(priority="high") == verdict_model()

    @pytest.mark.asyncio
    async def test_router_flag_off_ignores_minute_counter(self, monkeypatch):
        """OFF-branch identity pin: flag absent => minute counter never consulted.

        Minute counter seeded FAR above the threshold; daily near zero. The
        shipped default must return the verdict model exactly as 593ec1e does.
        """
        from app.services.model_config import verdict_model

        monkeypatch.delenv("ENABLE_TPM_AWARE_ROUTING", raising=False)
        svc = _fresh_router()
        minute_mock = AsyncMock(return_value=_TPM_LIMIT * 100)
        with patch.object(
            svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0
        ), patch.object(
            svc, "_get_4o_usage_this_minute", new=minute_mock, create=True
        ):
            assert await svc.get_model(priority="high") == verdict_model()
        minute_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_router_minute_counter_fails_open_on_redis_error(
        self, monkeypatch
    ):
        """Redis down must NOT dark the verdict path (has_budget fail-open
        contract, api_budget_service.py:366-367): counter read raises =>
        verdict model still returned, no exception escapes."""
        from app.services.model_config import verdict_model

        monkeypatch.setenv("ENABLE_TPM_AWARE_ROUTING", "true")
        svc = _fresh_router()
        with patch.object(
            svc, "_get_4o_usage_today", new_callable=AsyncMock, return_value=0
        ), patch.object(
            svc,
            "_get_4o_usage_this_minute",
            new=AsyncMock(side_effect=ConnectionError("redis down")),
            create=True,
        ):
            assert await svc.get_model(priority="high") == verdict_model()

    @pytest.mark.asyncio
    async def test_minute_counter_key_rolls_over_and_expires(self):
        """Key embeds the UTC minute; a TTL is set on first write so a burst
        cannot poison the next minute. (Style: test_key_includes_utc_date.)"""
        svc = _fresh_router()
        assert hasattr(svc, "_get_minute_counter_key"), (
            "router exposes no minute-counter key helper - the per-minute TPM "
            "counter does not exist yet (issue #117 finding 2)"
        )

        t0 = datetime(2026, 9, 1, 12, 34, 59, tzinfo=timezone.utc)
        t1 = datetime(2026, 9, 1, 12, 35, 0, tzinfo=timezone.utc)
        key0 = svc._get_minute_counter_key(moment=t0)
        key1 = svc._get_minute_counter_key(moment=t1)
        assert "2026-09-01T12:34" in key0, key0
        assert "2026-09-01T12:35" in key1, key1
        assert key0 != key1, "key must roll over at the minute boundary"

        # TTL on write: the increment must both INCRBY atomically and EXPIRE.
        mock_redis = MagicMock()
        with patch("app.services.cache_service.redis_client", mock_redis), patch(
            "app.services.model_router_service._redis_expire"
        ) as mock_expire:
            await svc._increment_4o_minute_usage(4500)
        assert mock_redis.incrby.called, "minute counter must use atomic INCRBY"
        (key_arg, tokens_arg) = mock_redis.incrby.call_args[0]
        assert "minute" in key_arg and tokens_arg == 4500
        assert mock_expire.called, "minute counter key must carry a TTL"
        ttl = mock_expire.call_args[0][1]
        assert 60 <= ttl <= 600, f"minute-counter TTL should be short, got {ttl}"

    @pytest.mark.asyncio
    async def test_record_usage_feeds_minute_counter_when_flag_on(
        self, monkeypatch
    ):
        """Flag ON: verdict-model usage increments the minute counter too,
        through the existing record_usage seam (no call-site change needed).

        RED at base: record_usage only feeds the daily counter.
        """
        monkeypatch.setenv("ENABLE_TPM_AWARE_ROUTING", "true")
        svc = _fresh_router()
        minute_inc = AsyncMock()
        with patch.object(
            svc, "_increment_4o_usage", new_callable=AsyncMock
        ) as daily_inc, patch.object(
            svc, "_increment_4o_minute_usage", new=minute_inc, create=True
        ):
            await svc.record_usage(model="gpt-4o", tokens_used=4500)
        daily_inc.assert_awaited_once_with(4500)
        minute_inc.assert_awaited_once_with(4500), (
            "verdict usage must also feed the per-minute counter or the "
            "rate signal can never accumulate"
        )

    @pytest.mark.asyncio
    async def test_record_usage_flag_off_never_touches_minute_counter(
        self, monkeypatch
    ):
        """OFF-branch identity pin for the write side."""
        monkeypatch.delenv("ENABLE_TPM_AWARE_ROUTING", raising=False)
        svc = _fresh_router()
        minute_inc = AsyncMock()
        with patch.object(
            svc, "_increment_4o_usage", new_callable=AsyncMock
        ) as daily_inc, patch.object(
            svc, "_increment_4o_minute_usage", new=minute_inc, create=True
        ):
            await svc.record_usage(model="gpt-4o", tokens_used=4500)
        daily_inc.assert_awaited_once_with(4500)
        minute_inc.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_standard_model_usage_never_feeds_minute_counter(
        self, monkeypatch
    ):
        """Mini usage has its own 200K budget - only verdict tokens count
        against the 30K verdict TPM wall (mirrors the daily counter rule)."""
        monkeypatch.setenv("ENABLE_TPM_AWARE_ROUTING", "true")
        svc = _fresh_router()
        minute_inc = AsyncMock()
        with patch.object(
            svc, "_increment_4o_usage", new_callable=AsyncMock
        ) as daily_inc, patch.object(
            svc, "_increment_4o_minute_usage", new=minute_inc, create=True
        ):
            await svc.record_usage(model="gpt-4o-mini", tokens_used=20_000)
        daily_inc.assert_not_awaited()
        minute_inc.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_daily_breaker_still_wins_with_flag_on(self, monkeypatch):
        """The minute counter is an ADDITIONAL signal, not a replacement:
        daily usage over threshold degrades even when the minute is quiet."""
        from app.services.model_config import standard_model
        from app.services.model_router_service import ModelRouterService

        monkeypatch.setenv("ENABLE_TPM_AWARE_ROUTING", "true")
        svc = _fresh_router()
        with patch.object(
            svc,
            "_get_4o_usage_today",
            new_callable=AsyncMock,
            return_value=int(ModelRouterService.DAILY_4O_CAP * 0.85),
        ), patch.object(
            svc,
            "_get_4o_usage_this_minute",
            new=AsyncMock(return_value=0),
            create=True,
        ):
            assert await svc.get_model(priority="high") == standard_model()

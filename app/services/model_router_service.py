"""Hybrid per-call OpenAI model routing.

Selects ``gpt-4o`` for high-priority calls (verdict generation) and
``gpt-4o-mini`` for everything else, with a circuit breaker that flips
verdicts to mini when the daily 4o token budget reaches 80% — so we
never fall off the data-sharing free tier mid-day.

Design Sections 1, 5.1; plan task BX.1.

Counter is keyed by UTC date so the cap resets at midnight UTC. Atomic
writes use Redis ``INCRBY`` (matches ``api_budget_service.py`` pattern).
Reads are best-effort: when Redis is unavailable we fail-open and assume
0 usage so verdicts keep getting the better model.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.cache_service import _redis_expire, _redis_get
from app.services.model_config import standard_model, verdict_model

logger = logging.getLogger(__name__)


class ModelRouterService:
    """Owns the per-call model selection.

    Stateless beyond the Redis-backed daily counter — safe to instantiate
    per request. Tests patch the private helpers ``_get_4o_usage_today``
    and ``_increment_4o_usage`` to avoid touching Redis.
    """

    # Daily 4o token cap under OpenAI's data-sharing program.
    # Conservative ceiling — verify exact value at deploy.
    DAILY_4O_CAP: int = 1_000_000

    # Switch verdicts to mini at 80% of the daily 4o cap so we leave
    # headroom for the rest of the day (per design 9.4 risk #3).
    SWITCH_THRESHOLD: float = 0.80

    # 36h TTL on the counter so a stale day's key auto-expires.
    _COUNTER_TTL: int = 36 * 3600

    async def get_model(self, priority: str = "standard") -> str:
        """Choose the verdict model vs the standard model for the next call.

        Ids come from ``model_config`` (env-overridable); by default they are
        ``gpt-4o`` and ``gpt-4o-mini`` respectively.

        priority:
          - ``standard`` (default) — always returns the standard model.
          - ``high`` — returns the verdict model while daily usage is below
            ``SWITCH_THRESHOLD`` of ``DAILY_4O_CAP``; returns the standard
            model once usage hits or exceeds the threshold.
        """
        if priority != "high":
            return standard_model()

        used = await self._get_4o_usage_today()
        if used / self.DAILY_4O_CAP >= self.SWITCH_THRESHOLD:
            return standard_model()
        return verdict_model()

    async def record_usage(self, model: str, tokens_used: int) -> None:
        """Record token usage. Only the verdict-model counter is tracked — the
        standard and unknown models are silently ignored (the standard model has
        its own free tier with separate caps; unknown models no-op for safety).

        Compares against the configured verdict id so the counter keeps tracking
        the expensive model after an env-driven model change.
        """
        if model == verdict_model():
            await self._increment_4o_usage(tokens_used)
        # standard + unknown: no-op

    # ---------- internals (patched by tests) ----------

    def _get_counter_key(self, *, date: Optional[datetime] = None) -> str:
        """Redis key for today's 4o token usage. UTC date in the key so
        the cap rolls over cleanly at midnight UTC even on day boundaries."""
        d = date or datetime.now(timezone.utc)
        return f"openai:4o:tokens:{d.strftime('%Y-%m-%d')}"

    async def _get_4o_usage_today(self) -> int:
        """Read today's 4o token usage. Fail-open as 0 on Redis error."""
        try:
            raw = _redis_get(self._get_counter_key())
            return int(raw) if raw is not None else 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("[model_router] failed to read 4o usage: %s", exc)
            return 0

    async def _increment_4o_usage(self, tokens_used: int) -> None:
        """Atomically increment the 4o token counter via Redis ``INCRBY``.

        Best-effort: any Redis failure is logged and swallowed — verdict
        routing degrades to "always 4o" which is the safe default for
        users (we just lose cap protection until Redis is back).
        """
        from app.services.cache_service import redis_client

        key = self._get_counter_key()
        try:
            if redis_client is not None:
                redis_client.incrby(key, int(tokens_used))
            _redis_expire(key, self._COUNTER_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[model_router] failed to increment 4o usage: %s", exc)


# Module-level singleton — call sites use ``model_router.get_model(...)`` for ergonomics.
model_router = ModelRouterService()

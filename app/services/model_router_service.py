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
import os
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

    # Short TTL on the per-minute counter (issue #117 (c)) — long enough to
    # survive the minute it meters plus clock skew, short enough that a burst
    # can never poison a later minute.
    _MINUTE_COUNTER_TTL: int = 180

    # ---------- TPM-aware routing knobs (issue #117, default OFF) ----------
    #
    # All three are read PER CALL via os.environ (the repo's flag idiom) so a
    # Railway change takes effect on the next request and the OFF default is
    # byte-identical to the pre-#117 router. They would ideally live in
    # model_config, but this lane may only edit this module — same safe
    # pattern (plain env reads, safe defaults, zero credentials).

    @staticmethod
    def _tpm_routing_enabled() -> bool:
        """ENABLE_TPM_AWARE_ROUTING — default OFF, read per call."""
        raw = os.getenv("ENABLE_TPM_AWARE_ROUTING", "")
        return raw.strip().lower() in ("1", "true", "yes", "on")

    @staticmethod
    def _verdict_tpm_limit() -> int:
        """OPENAI_VERDICT_TPM_LIMIT — the verdict model's tokens-per-minute
        ceiling. Default 30_000 = OpenAI's PUBLISHED Tier-1 gpt-4o TPM
        (vendor documentation, NOT measured on this account — the account's
        real tier is a deliverable of issue #117 (a); set this to the
        dashboard value once recorded). ``<=0`` or garbage disables the
        minute branch rather than dividing by a lie."""
        raw = os.getenv("OPENAI_VERDICT_TPM_LIMIT", "")
        try:
            return int(raw.strip()) if raw.strip() else 30_000
        except ValueError:
            logger.warning(
                "[model_router] ignoring non-integer OPENAI_VERDICT_TPM_LIMIT=%r", raw
            )
            return 30_000

    @staticmethod
    def _tpm_switch_threshold() -> float:
        """TPM_SWITCH_THRESHOLD — fraction of the TPM ceiling at which
        verdicts degrade to the standard model. Default mirrors the daily
        counter's 0.80."""
        raw = os.getenv("TPM_SWITCH_THRESHOLD", "")
        try:
            return float(raw.strip()) if raw.strip() else 0.80
        except ValueError:
            logger.warning(
                "[model_router] ignoring non-numeric TPM_SWITCH_THRESHOLD=%r", raw
            )
            return 0.80

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

        # Issue #117 (c): rate signal FIRST — the daily counter is
        # structurally blind to a mid-minute TPM wall. Whole branch is gated
        # per call on ENABLE_TPM_AWARE_ROUTING (default OFF => the daily
        # check below runs exactly as before) and FAILS OPEN on any Redis
        # error (the has_budget contract, api_budget_service.py:366-367): a
        # Redis outage must not dark the verdict path.
        if self._tpm_routing_enabled():
            try:
                minute_used = await self._get_4o_usage_this_minute()
            except Exception as exc:  # noqa: BLE001 — fail-open
                logger.warning(
                    "[model_router] minute TPM read failed (fail-open): %s", exc
                )
                minute_used = 0
            tpm_limit = self._verdict_tpm_limit()
            if tpm_limit > 0 and minute_used >= tpm_limit * self._tpm_switch_threshold():
                logger.info(
                    "[model_router] minute TPM %d >= %.0f%% of %d — degrading "
                    "verdict to standard model for this minute",
                    minute_used,
                    self._tpm_switch_threshold() * 100,
                    tpm_limit,
                )
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
            # Issue #117 (c): feed the per-minute rate counter too — but only
            # under the flag, so the OFF default performs exactly the same
            # Redis operations as before (byte-identical write side).
            if self._tpm_routing_enabled():
                await self._increment_4o_minute_usage(tokens_used)
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

    def _get_minute_counter_key(self, *, moment: Optional[datetime] = None) -> str:
        """Redis key for the CURRENT UTC minute's verdict-token usage.

        The UTC minute is embedded in the key (mirroring the daily key's UTC
        date) so the counter rolls over cleanly at every minute boundary —
        no decrement logic, the old key simply expires.
        """
        d = moment or datetime.now(timezone.utc)
        return f"openai:4o:tokens:minute:{d.strftime('%Y-%m-%dT%H:%M')}"

    async def _get_4o_usage_this_minute(self) -> int:
        """Read this UTC minute's verdict-token usage. Fail-open as 0 on
        Redis error — a Redis outage must not dark the verdict path."""
        try:
            raw = _redis_get(self._get_minute_counter_key())
            return int(raw) if raw is not None else 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("[model_router] failed to read minute TPM usage: %s", exc)
            return 0

    async def _increment_4o_minute_usage(self, tokens_used: int) -> None:
        """Atomically increment the per-minute counter via Redis ``INCRBY``
        (same idiom as the daily counter / api_budget_service) and set a
        short TTL so a burst cannot poison a later minute. Best-effort:
        failures are logged and swallowed."""
        from app.services.cache_service import redis_client

        key = self._get_minute_counter_key()
        try:
            if redis_client is not None:
                redis_client.incrby(key, int(tokens_used))
            _redis_expire(key, self._MINUTE_COUNTER_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[model_router] failed to increment minute TPM usage: %s", exc
            )

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

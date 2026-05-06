"""Backend-owned internals tests for usage_service.

Closes the remaining defensive-path coverage gap qa-referral flagged
post-B5/B6: Redis-unavailable branches, exception swallows, and the
unparseable-reset_at path inside _maybe_reset_referral_bonus.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestRedisCountDefensive:
    """``_get_redis_count`` must fail-open (return 0) on every error path."""

    def test_returns_zero_when_redis_client_is_none(self):
        with patch("app.services.usage_service.redis_client", None):
            from app.services.usage_service import _get_redis_count

            assert _get_redis_count("any-key") == 0

    def test_returns_zero_on_redis_exception(self):
        broken = MagicMock()
        broken.get.side_effect = RuntimeError("redis network blip")
        with patch("app.services.usage_service.redis_client", broken):
            from app.services.usage_service import _get_redis_count

            assert _get_redis_count("any-key") == 0

    def test_returns_zero_when_value_is_none(self):
        client = MagicMock()
        client.get.return_value = None
        with patch("app.services.usage_service.redis_client", client):
            from app.services.usage_service import _get_redis_count

            assert _get_redis_count("any-key") == 0

    def test_parses_integer_string(self):
        client = MagicMock()
        client.get.return_value = "42"
        with patch("app.services.usage_service.redis_client", client):
            from app.services.usage_service import _get_redis_count

            assert _get_redis_count("any-key") == 42


class TestLazyResetDefensive:
    """``_maybe_reset_referral_bonus`` covers all branches without raising."""

    def test_missing_reset_at_supplies_zero_default(self):
        from app.services.usage_service import _maybe_reset_referral_bonus

        data = {"subscription_tier": "free"}
        result = _maybe_reset_referral_bonus(MagicMock(), "u1", data)
        assert result["referral_bonus_comparisons_this_month"] == 0

    def test_unparseable_reset_at_supplies_zero_default(self):
        """Malformed timestamp must NOT raise — fail open with bonus=0."""
        from app.services.usage_service import _maybe_reset_referral_bonus

        data = {"referral_bonus_reset_at": "not-a-date"}
        result = _maybe_reset_referral_bonus(MagicMock(), "u1", data)
        assert result["referral_bonus_comparisons_this_month"] == 0

    def test_future_reset_at_keeps_existing_bonus(self):
        from app.services.usage_service import _maybe_reset_referral_bonus

        future = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
        data = {
            "referral_bonus_reset_at": future,
            "referral_bonus_comparisons_this_month": 7,
        }
        result = _maybe_reset_referral_bonus(MagicMock(), "u1", data)
        # Bonus is preserved; setdefault doesn't override.
        assert result["referral_bonus_comparisons_this_month"] == 7

    def test_past_reset_at_zeros_and_rolls_forward(self):
        from app.services.usage_service import _maybe_reset_referral_bonus

        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        data = {
            "referral_bonus_reset_at": past,
            "referral_bonus_comparisons_this_month": 9,
        }
        client = MagicMock()
        result = _maybe_reset_referral_bonus(client, "u1", data)
        assert result["referral_bonus_comparisons_this_month"] == 0
        assert result["referral_bonus_reset_at"] != past
        # Update was issued
        client.table.return_value.update.assert_called_once()

    def test_past_reset_at_swallows_db_error(self):
        """DB failure during reset must NOT raise — usage check must still run."""
        from app.services.usage_service import _maybe_reset_referral_bonus

        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        data = {
            "referral_bonus_reset_at": past,
            "referral_bonus_comparisons_this_month": 9,
        }
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.side_effect = RuntimeError(
            "supabase down"
        )
        # Should NOT raise; counter is still zeroed in the returned dict.
        result = _maybe_reset_referral_bonus(client, "u1", data)
        assert result["referral_bonus_comparisons_this_month"] == 0

"""Tests for B4.3 — referral bonus extends monthly cap in usage_service.

Behaviour contract:
- Free user with 0 bonus  -> monthly cap = 10
- Free user with 15 bonus -> monthly cap = 25
- Premium with 30 bonus   -> monthly cap = 100
- Lazy reset: when ``referral_bonus_reset_at < now()`` the counter is
  reset to 0 and ``reset_at`` rolled forward by one month.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _fake_user_table(data: dict) -> MagicMock:
    """Build a chained Supabase mock that returns ``data`` from .single().execute()."""
    client = MagicMock()
    table = MagicMock()
    client.table.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.update.return_value = table
    table.execute.return_value = MagicMock(data=data)
    return client


def _fake_user_and_redemptions_table(
    user_data: dict, *, active_bonus_sum: int = 0
) -> MagicMock:
    """Per-table dispatcher mock for the path-(a) world.

    `users.single().execute()` returns user_data; `referral_redemptions`
    chained query returns rows summing to active_bonus_sum.
    """
    client = MagicMock()

    def factory(name):
        t = MagicMock()
        for m in ("select", "eq", "gt", "gte", "lt", "lte",
                  "is_", "single", "update", "limit", "order"):
            getattr(t, m).return_value = t
        if name == "users":
            t.execute.return_value = MagicMock(data=user_data)
        elif name == "referral_redemptions":
            rows = (
                [{"loop2_comparisons_granted": active_bonus_sum}]
                if active_bonus_sum > 0
                else []
            )
            t.execute.return_value = MagicMock(data=rows)
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    client.table.side_effect = factory
    return client


class TestReferralBonusExtendsMonthlyCap:
    @pytest.mark.asyncio
    async def test_free_with_zero_bonus_keeps_base_cap(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "9" if "monthly" in key else None
        client = _fake_user_table(
            {
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 0,
                "referral_bonus_reset_at": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
            }
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("user-1", "tok")
            assert result["allowed"] is True
            # 9 used, 10 cap, 0 bonus => 1 remaining
            assert result["remaining"]["monthly"] == 1

    @pytest.mark.asyncio
    async def test_free_with_15_bonus_extends_cap(self):
        """Path-(a): bonus comes from active referral_redemptions rows,
        not the INT counter. 15 active bonus + base 10 = cap 25."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "12" if "monthly" in key else None
        client = _fake_user_and_redemptions_table(
            {
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 15,  # display only
                "referral_bonus_reset_at": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
            },
            active_bonus_sum=15,
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("user-2", "tok")
            assert result["allowed"] is True
            # cap = 10 + 15 = 25; used 12; remaining 13
            assert result["remaining"]["monthly"] == 13

    @pytest.mark.asyncio
    async def test_premium_with_30_bonus_extends_cap(self):
        """Path-(a): premium tier base 70 + 30 active bonus = cap 100."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "70" if "monthly" in key else None
        client = _fake_user_and_redemptions_table(
            {
                "subscription_tier": "premium",
                "lifetime_comparisons_used": 100,
                "referral_bonus_comparisons_this_month": 30,  # display only
                "referral_bonus_reset_at": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
            },
            active_bonus_sum=30,
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("p-1", "tok")
            assert result["allowed"] is True
            # cap = 70 + 30 = 100; used 70; remaining 30
            assert result["remaining"]["monthly"] == 30

    @pytest.mark.asyncio
    async def test_blocks_when_used_exceeds_extended_cap(self):
        """Path-(a): 25 used, base 10 + 15 active bonus = cap 25, blocked."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "25" if "monthly" in key else None
        client = _fake_user_and_redemptions_table(
            {
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 15,  # display only
                "referral_bonus_reset_at": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
            },
            active_bonus_sum=15,
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("user-3", "tok")
            assert result["allowed"] is False
            assert result["reason"] == "monthly_limit"


class TestLazyReset:
    """When referral_bonus_reset_at is in the past, the counter rolls to 0
    and reset_at is rolled forward by one month — no cron needed."""

    @pytest.mark.asyncio
    async def test_past_reset_at_zeroes_bonus_and_rolls_forward(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "5" if "monthly" in key else None
        # reset_at is 1 day ago
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        client = _fake_user_table(
            {
                "subscription_tier": "free",
                "lifetime_comparisons_used": 5,
                "referral_bonus_comparisons_this_month": 12,
                "referral_bonus_reset_at": past,
            }
        )

        with patch("app.services.usage_service.redis_client", mock_redis), patch(
            "app.services.usage_service.get_admin_supabase_client", return_value=client
        ):
            from app.services.usage_service import check_usage_allowed

            result = await check_usage_allowed("user-4", "tok")
            # After reset, cap = 10 (no bonus); used 5; remaining 5
            assert result["allowed"] is True
            assert result["remaining"]["monthly"] == 5
            # update was called with new reset_at + zeroed bonus
            update_calls = [
                c for c in client.table.return_value.update.call_args_list
            ]
            assert update_calls, "lazy reset must update users row"

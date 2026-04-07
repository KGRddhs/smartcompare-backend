"""Tests for freemium usage tracking and tier enforcement."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


# Tier limits for reference:
# Free: 3 lifetime free, 10/month, 3/day
# Premium: 70/month, 10/day

class TestCheckUsageAllowed:
    @pytest.mark.asyncio
    async def test_free_user_first_comparison_allowed(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # No usage yet

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "free", "lifetime_comparisons_used": 0})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            assert result["allowed"] is True
            assert result["tier"] == "free"

    @pytest.mark.asyncio
    async def test_free_user_daily_limit_blocks(self):
        mock_redis = MagicMock()
        # Daily count = 3 (at limit)
        mock_redis.get.side_effect = lambda key: "3" if "daily" in key else "5" if "monthly" in key else None

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "free", "lifetime_comparisons_used": 5})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            assert result["allowed"] is False
            assert result["reason"] == "daily_limit"

    @pytest.mark.asyncio
    async def test_free_user_monthly_limit_blocks(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "2" if "daily" in key else "10" if "monthly" in key else None

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "free", "lifetime_comparisons_used": 10})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            assert result["allowed"] is False
            assert result["reason"] == "monthly_limit"

    @pytest.mark.asyncio
    async def test_premium_user_higher_limits(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "5" if "daily" in key else "30" if "monthly" in key else None

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "premium", "lifetime_comparisons_used": 50})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            assert result["allowed"] is True
            assert result["tier"] == "premium"

    @pytest.mark.asyncio
    async def test_fails_open_without_redis(self):
        """If Redis unavailable, allow comparison (fail-open)."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "free", "lifetime_comparisons_used": 0})

        with patch("app.services.usage_service.redis_client", None), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_free_user_lifetime_free_bypasses_daily_monthly(self):
        """First 3 lifetime comparisons bypass daily/monthly limits."""
        mock_redis = MagicMock()
        # Even if redis says daily=3, lifetime_free should override
        mock_redis.get.side_effect = lambda key: "3" if "daily" in key else "10" if "monthly" in key else None

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "free", "lifetime_comparisons_used": 2})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            assert result["allowed"] is True
            assert result["remaining"]["lifetime_free"] == 1

    @pytest.mark.asyncio
    async def test_db_error_returns_free_tier_defaults(self):
        """If DB is unavailable, default to free tier (fail-open)."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB down")

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import check_usage_allowed
            result = await check_usage_allowed("user-123", "fake-token")
            # Should default to free tier with 0 lifetime used -> allowed via lifetime_free
            assert result["allowed"] is True
            assert result["tier"] == "free"


class TestRecordComparison:
    @pytest.mark.asyncio
    async def test_increments_redis_counters(self):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1

        mock_client = MagicMock()
        mock_rpc = MagicMock()
        mock_client.rpc.return_value = mock_rpc
        mock_rpc.execute.return_value = MagicMock(data=None)

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import record_comparison
            await record_comparison("user-123", "fake-token")
            # Should increment both daily and monthly counters
            assert mock_redis.incr.call_count >= 2

    @pytest.mark.asyncio
    async def test_record_handles_redis_failure_gracefully(self):
        """Recording should not raise even if Redis fails."""
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis down")

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", side_effect=Exception("DB down")):
            from app.services.usage_service import record_comparison
            # Should not raise
            await record_comparison("user-123", "fake-token")

    @pytest.mark.asyncio
    async def test_record_calls_rpc_increment(self):
        """Should call the Supabase RPC function to increment lifetime count."""
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1

        mock_client = MagicMock()
        mock_rpc = MagicMock()
        mock_client.rpc.return_value = mock_rpc
        mock_rpc.execute.return_value = MagicMock(data=None)

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import record_comparison
            await record_comparison("user-123", "fake-token")
            mock_client.rpc.assert_called_once_with(
                "increment_lifetime_comparisons", {"target_user_id": "user-123"}
            )


class TestGetUsageStatus:
    @pytest.mark.asyncio
    async def test_returns_usage_summary(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "2" if "daily" in key else "7" if "monthly" in key else None

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "free", "lifetime_comparisons_used": 7})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import get_usage_status
            result = await get_usage_status("user-123", "fake-token")
            assert result["tier"] == "free"
            assert result["used"]["daily"] == 2
            assert result["used"]["monthly"] == 7
            assert result["limits"]["daily"] == 3
            assert result["limits"]["monthly"] == 10

    @pytest.mark.asyncio
    async def test_returns_premium_limits(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "5" if "daily" in key else "20" if "monthly" in key else None

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={"subscription_tier": "premium", "lifetime_comparisons_used": 100})

        with patch("app.services.usage_service.redis_client", mock_redis), \
             patch("app.services.usage_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.usage_service import get_usage_status
            result = await get_usage_status("user-123", "fake-token")
            assert result["tier"] == "premium"
            assert result["limits"]["daily"] == 10
            assert result["limits"]["monthly"] == 70
            assert result["remaining"]["daily"] == 5
            assert result["remaining"]["monthly"] == 50

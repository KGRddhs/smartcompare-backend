"""Tests for brute-force account lockout."""
import pytest
from unittest.mock import patch, MagicMock


class TestBruteForceProtection:
    @pytest.mark.asyncio
    async def test_tracks_failed_login_attempts(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        with patch("app.services.auth_service.redis_client", mock_redis):
            from app.services.auth_service import track_failed_login
            result = await track_failed_login("test@example.com")
            assert result["locked"] is False
            assert result["attempts"] == 1

    @pytest.mark.asyncio
    async def test_locks_after_five_failures(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "4"  # Already 4 failures
        mock_redis.incr.return_value = 5

        with patch("app.services.auth_service.redis_client", mock_redis):
            from app.services.auth_service import track_failed_login
            result = await track_failed_login("test@example.com")
            assert result["locked"] is True
            assert result["attempts"] == 5

    @pytest.mark.asyncio
    async def test_check_lockout_returns_false_when_not_locked(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "2"

        with patch("app.services.auth_service.redis_client", mock_redis):
            from app.services.auth_service import check_account_locked
            result = await check_account_locked("test@example.com")
            assert result["locked"] is False
            assert result["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_check_lockout_returns_true_when_locked(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "5"
        mock_redis.ttl.return_value = 600

        with patch("app.services.auth_service.redis_client", mock_redis):
            from app.services.auth_service import check_account_locked
            result = await check_account_locked("test@example.com")
            assert result["locked"] is True
            assert result["retry_after"] == 600

    @pytest.mark.asyncio
    async def test_successful_login_resets_counter(self):
        mock_redis = MagicMock()

        with patch("app.services.auth_service.redis_client", mock_redis):
            from app.services.auth_service import clear_failed_logins
            await clear_failed_logins("test@example.com")
            mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_lockout_graceful_without_redis(self):
        """If Redis is unavailable, lockout should fail-open (not block users)."""
        with patch("app.services.auth_service.redis_client", None):
            from app.services.auth_service import check_account_locked
            result = await check_account_locked("test@example.com")
            assert result["locked"] is False
            assert result["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_track_failed_graceful_without_redis(self):
        """If Redis is unavailable, tracking should fail-open."""
        with patch("app.services.auth_service.redis_client", None):
            from app.services.auth_service import track_failed_login
            result = await track_failed_login("test@example.com")
            assert result["locked"] is False
            assert result["attempts"] == 0

    @pytest.mark.asyncio
    async def test_clear_failed_graceful_without_redis(self):
        """If Redis is unavailable, clearing should not raise."""
        with patch("app.services.auth_service.redis_client", None):
            from app.services.auth_service import clear_failed_logins
            await clear_failed_logins("test@example.com")  # Should not raise

    @pytest.mark.asyncio
    async def test_email_hashed_in_redis_key(self):
        """Redis key should use hashed email, not raw PII."""
        from app.services.auth_service import _login_attempt_key
        key = _login_attempt_key("test@example.com")
        assert "test@example.com" not in key
        assert key.startswith("failed_login:")
        assert len(key) > len("failed_login:")

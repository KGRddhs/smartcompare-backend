"""L2.2 — YouTube Data API v3 daily-UNIT quota metering in api_budget_service.

YouTube's free quota is 10,000 UNITS/day (search.list=100u, videos.list=1u).
`try_consume_youtube_credit(units)` is an atomic per-UTC-day check-and-increment
that guards the expensive search.list, fails OPEN on Redis down, and rolls back
on over-budget. `record_usage("youtube")` meters successful units through the
shared counter path (and its 80%-burn alert plumbing).

All Redis access is mocked — zero live spend.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import MagicMock, patch

import app.services.api_budget_service as bs


# ---------------------------------------------------------------------------
# Provider registration
# ---------------------------------------------------------------------------

def test_youtube_is_a_known_provider():
    """has_budget / record_usage must recognise 'youtube' (else they no-op or
    return False unexpectedly)."""
    assert "youtube" in bs.PROVIDER_CONFIGS
    cfg = bs.PROVIDER_CONFIGS["youtube"]
    assert cfg["monthly_limit"] == 10000
    # Daily-resetting (not lifetime) so the unused monthly key would reset.
    assert cfg["is_lifetime"] is False


# ---------------------------------------------------------------------------
# try_consume_youtube_credit — atomic daily check-and-increment
# ---------------------------------------------------------------------------

def test_consume_increments_and_allows_under_budget():
    fake_redis = MagicMock()
    fake_redis.incrby.return_value = 100  # first call this day
    with patch("app.services.cache_service.redis_client", fake_redis):
        ok = bs.try_consume_youtube_credit(100)
    assert ok is True
    fake_redis.incrby.assert_called_once()
    # key includes today's UTC date + the youtube_units namespace
    key_arg = fake_redis.incrby.call_args.args[0]
    assert key_arg.startswith("budget:youtube_units:")
    assert fake_redis.incrby.call_args.args[1] == 100


def test_consume_sets_ttl_on_first_write_only():
    fake_redis = MagicMock()
    fake_redis.incrby.return_value = 100  # == units → first write
    with patch("app.services.cache_service.redis_client", fake_redis):
        bs.try_consume_youtube_credit(100)
    fake_redis.expire.assert_called_once()
    assert fake_redis.expire.call_args.args[1] == bs._YOUTUBE_UNIT_TTL

    # Subsequent write (counter already > units) → no TTL reset.
    fake_redis2 = MagicMock()
    fake_redis2.incrby.return_value = 200  # not the first write
    with patch("app.services.cache_service.redis_client", fake_redis2):
        bs.try_consume_youtube_credit(100)
    fake_redis2.expire.assert_not_called()


def test_consume_rejects_and_rolls_back_when_over_budget(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DAILY_UNIT_BUDGET", "9000")
    fake_redis = MagicMock()
    fake_redis.incrby.return_value = 9100  # would exceed 9000
    with patch("app.services.cache_service.redis_client", fake_redis):
        ok = bs.try_consume_youtube_credit(100)
    assert ok is False
    # Rolled back so the counter reflects consumed, not attempted.
    fake_redis.decrby.assert_called_once()
    assert fake_redis.decrby.call_args.args[1] == 100


def test_consume_fails_open_on_redis_none():
    """Redis unavailable → fail OPEN (a missed signal is cheaper than a hard
    failure). Returns True, attempts nothing."""
    with patch("app.services.cache_service.redis_client", None):
        ok = bs.try_consume_youtube_credit(100)
    assert ok is True


def test_consume_fails_open_on_redis_error():
    fake_redis = MagicMock()
    fake_redis.incrby.side_effect = RuntimeError("upstash down")
    with patch("app.services.cache_service.redis_client", fake_redis):
        ok = bs.try_consume_youtube_credit(100)
    assert ok is True  # fail-open on exception


def test_consume_zero_or_negative_units_is_noop_allow():
    fake_redis = MagicMock()
    with patch("app.services.cache_service.redis_client", fake_redis):
        assert bs.try_consume_youtube_credit(0) is True
        assert bs.try_consume_youtube_credit(-5) is True
    fake_redis.incrby.assert_not_called()


def test_consume_default_units_is_search_list_cost():
    """Default arg = 100 (search.list cost) — the guard is sized to the
    expensive call it protects."""
    fake_redis = MagicMock()
    fake_redis.incrby.return_value = 100
    with patch("app.services.cache_service.redis_client", fake_redis):
        bs.try_consume_youtube_credit()  # no arg
    assert fake_redis.incrby.call_args.args[1] == 100


def test_daily_budget_env_override(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DAILY_UNIT_BUDGET", "1234")
    assert bs._youtube_daily_unit_budget() == 1234
    # malformed → default
    monkeypatch.setenv("YOUTUBE_DAILY_UNIT_BUDGET", "not-a-number")
    assert bs._youtube_daily_unit_budget() == bs._DEFAULT_YOUTUBE_DAILY_UNITS


# ---------------------------------------------------------------------------
# get_youtube_unit_usage — read-only diagnostic
# ---------------------------------------------------------------------------

def test_usage_summary_reads_counter(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DAILY_UNIT_BUDGET", "9000")
    with patch("app.services.api_budget_service._redis_get", return_value="300"):
        usage = bs.get_youtube_unit_usage()
    assert usage == {"used": 300, "limit": 9000, "remaining": 8700}


def test_usage_summary_fail_safe_on_redis_error(monkeypatch):
    monkeypatch.setenv("YOUTUBE_DAILY_UNIT_BUDGET", "9000")
    with patch("app.services.api_budget_service._redis_get", side_effect=RuntimeError):
        usage = bs.get_youtube_unit_usage()
    assert usage["used"] == 0
    assert usage["remaining"] == 9000


# ---------------------------------------------------------------------------
# record_usage("youtube") — meters successful units through shared path
# ---------------------------------------------------------------------------

def test_record_usage_youtube_increments_counter():
    """record_usage('youtube', count=N) bumps the youtube budget key by N via
    the shared incrby path (so the admin summary + burn alert see real usage)."""
    fake_redis = MagicMock()
    fake_redis.incrby.return_value = 100
    with patch("app.services.cache_service.redis_client", fake_redis):
        bs.record_usage("youtube", count=100)
    fake_redis.incrby.assert_called_once()
    # Shared budget key for a non-lifetime provider is month-stamped.
    key_arg = fake_redis.incrby.call_args.args[0]
    assert key_arg.startswith("budget:youtube:")
    assert fake_redis.incrby.call_args.args[1] == 100

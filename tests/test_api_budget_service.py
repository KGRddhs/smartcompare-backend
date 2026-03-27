"""Tests for API budget service — credit tracking + circuit breakers."""
import json
import time
import pytest
from unittest.mock import patch, MagicMock, call

from app.services.api_budget_service import (
    has_budget, record_usage, record_failure, record_success,
    is_circuit_closed, get_usage_summary,
    PROVIDER_CONFIGS, CB_FAILURE_THRESHOLD, CB_RECOVERY_TIMEOUT,
    CB_CLOSED, CB_OPEN, CB_HALF_OPEN,
    _budget_key, _circuit_key,
)


@pytest.fixture
def mock_redis_helpers():
    """Mock _redis_get/_redis_set/_redis_incr/_redis_expire at the api_budget_service module level."""
    store = {}

    def fake_get(key):
        return store.get(key)

    def fake_set(key, value, ex=None):
        store[key] = value
        return True

    def fake_incr(key):
        val = int(store.get(key, 0)) + 1
        store[key] = str(val)
        return val

    def fake_expire(key, seconds):
        return True

    mock_client = MagicMock()
    mock_client.incrby = MagicMock(side_effect=lambda key, count: fake_incr(key) if count == 1 else [fake_incr(key) for _ in range(count)][-1])

    with patch("app.services.api_budget_service._redis_get", side_effect=fake_get) as m_get, \
         patch("app.services.api_budget_service._redis_set", side_effect=fake_set) as m_set, \
         patch("app.services.api_budget_service._redis_incr", side_effect=fake_incr) as m_incr, \
         patch("app.services.api_budget_service._redis_expire", side_effect=fake_expire) as m_expire, \
         patch("app.services.cache_service.redis_client", mock_client):
        yield {"get": m_get, "set": m_set, "incr": m_incr, "expire": m_expire, "store": store, "client": mock_client}


class TestBudgetKey:
    def test_lifetime_provider_key(self):
        key = _budget_key("firecrawl")
        assert key == "budget:firecrawl:lifetime"

    def test_monthly_provider_key(self):
        key = _budget_key("scrapedo")
        assert key.startswith("budget:scrapedo:")
        # Should contain YYYY-MM format
        parts = key.split(":")
        assert len(parts) == 3
        assert len(parts[2]) == 7  # YYYY-MM

    def test_serper_is_lifetime(self):
        key = _budget_key("serper")
        assert key == "budget:serper:lifetime"


class TestHasBudget:
    def test_under_limit(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = "100"
        assert has_budget("firecrawl") is True

    def test_at_limit(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = str(PROVIDER_CONFIGS["firecrawl"]["monthly_limit"])
        assert has_budget("firecrawl") is False

    def test_over_limit(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = "9999"
        assert has_budget("firecrawl") is False

    def test_no_usage_yet(self, mock_redis_helpers):
        # No key in store = first use
        assert has_budget("firecrawl") is True

    def test_unknown_provider(self, mock_redis_helpers):
        assert has_budget("nonexistent") is False

    def test_redis_error_fail_open(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            assert has_budget("firecrawl") is True

    def test_warning_logged_at_warn_threshold(self, mock_redis_helpers):
        warn_at = PROVIDER_CONFIGS["firecrawl"]["warn_at"]
        mock_redis_helpers["store"][_budget_key("firecrawl")] = str(warn_at)
        # Should still return True (warn_at < monthly_limit) but log warning
        assert has_budget("firecrawl") is True

    def test_scrapedo_monthly_budget(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("scrapedo")] = "50"
        assert has_budget("scrapedo") is True

    def test_scrapedo_exhausted(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("scrapedo")] = str(PROVIDER_CONFIGS["scrapedo"]["monthly_limit"])
        assert has_budget("scrapedo") is False


class TestRecordUsage:
    def test_increments_counter(self, mock_redis_helpers):
        record_usage("firecrawl")
        mock_redis_helpers["client"].incrby.assert_called_once()

    def test_multiple_increments(self, mock_redis_helpers):
        record_usage("firecrawl", count=3)
        mock_redis_helpers["client"].incrby.assert_called_once_with(
            _budget_key("firecrawl"), 3
        )

    def test_sets_ttl_for_monthly_provider(self, mock_redis_helpers):
        record_usage("scrapedo")  # monthly, not lifetime
        mock_redis_helpers["expire"].assert_called_once()

    def test_no_ttl_for_lifetime_provider(self, mock_redis_helpers):
        record_usage("firecrawl")  # lifetime
        mock_redis_helpers["expire"].assert_not_called()

    def test_redis_error_no_crash(self):
        with patch("app.services.api_budget_service._redis_incr", side_effect=Exception("Redis down")):
            record_usage("firecrawl")  # should not raise


class TestCircuitBreaker:
    def test_fresh_provider_is_closed(self, mock_redis_helpers):
        assert is_circuit_closed("firecrawl") is True

    def test_single_failure_stays_closed(self, mock_redis_helpers):
        record_failure("firecrawl")
        raw = mock_redis_helpers["store"].get(_circuit_key("firecrawl"))
        state = json.loads(raw)
        assert state["state"] == CB_CLOSED
        assert state["failure_count"] == 1

    def test_two_failures_stays_closed(self, mock_redis_helpers):
        record_failure("firecrawl")
        record_failure("firecrawl")
        raw = mock_redis_helpers["store"].get(_circuit_key("firecrawl"))
        state = json.loads(raw)
        assert state["state"] == CB_CLOSED
        assert state["failure_count"] == 2

    def test_threshold_failures_trips_breaker(self, mock_redis_helpers):
        # Pre-load state with failures just below threshold
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_CLOSED, "failure_count": CB_FAILURE_THRESHOLD - 1
        })
        record_failure("firecrawl")
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["state"] == CB_OPEN

    def test_open_breaker_blocks_calls(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_OPEN, "failure_count": 3, "tripped_at": time.time()
        })
        assert is_circuit_closed("firecrawl") is False

    def test_open_transitions_to_half_open_after_timeout(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_OPEN, "failure_count": 3,
            "tripped_at": time.time() - CB_RECOVERY_TIMEOUT - 1
        })
        assert is_circuit_closed("firecrawl") is True
        # Verify state was updated to half-open
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["state"] == CB_HALF_OPEN

    def test_half_open_allows_limited_calls(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_HALF_OPEN, "failure_count": 0, "half_open_calls": 0
        })
        assert is_circuit_closed("firecrawl") is True

    def test_half_open_blocks_excess_calls(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_HALF_OPEN, "failure_count": 0, "half_open_calls": 1
        })
        # CB_HALF_OPEN_MAX_CALLS is 1, so with 1 already made, should block
        assert is_circuit_closed("firecrawl") is False

    def test_success_closes_half_open(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_HALF_OPEN, "failure_count": 0, "half_open_calls": 0
        })
        record_success("firecrawl")
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["state"] == CB_CLOSED
        assert state["failure_count"] == 0

    def test_success_on_closed_no_state_is_noop(self, mock_redis_helpers):
        # No state in store
        record_success("firecrawl")
        # Should not crash, no state created

    def test_redis_error_fail_open(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            assert is_circuit_closed("firecrawl") is True

    def test_record_failure_redis_error_no_crash(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            record_failure("firecrawl")  # should not raise

    def test_record_success_redis_error_no_crash(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            record_success("firecrawl")  # should not raise

    def test_tripped_at_set_when_breaker_opens(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_CLOSED, "failure_count": CB_FAILURE_THRESHOLD - 1
        })
        before = time.time()
        record_failure("firecrawl")
        after = time.time()
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert before <= state["tripped_at"] <= after


class TestUsageSummary:
    def test_returns_all_providers(self, mock_redis_helpers):
        summary = get_usage_summary()
        for provider in PROVIDER_CONFIGS:
            assert provider in summary["providers"]
            assert "used" in summary["providers"][provider]
            assert "limit" in summary["providers"][provider]
            assert "remaining" in summary["providers"][provider]

    def test_returns_circuit_breaker_states(self, mock_redis_helpers):
        summary = get_usage_summary()
        assert "circuit_breakers" in summary
        for provider in PROVIDER_CONFIGS:
            assert provider in summary["circuit_breakers"]
            assert "state" in summary["circuit_breakers"][provider]
            assert "failures" in summary["circuit_breakers"][provider]

    def test_correct_remaining_calculation(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = "100"
        summary = get_usage_summary()
        fc = summary["providers"]["firecrawl"]
        assert fc["used"] == 100
        assert fc["remaining"] == PROVIDER_CONFIGS["firecrawl"]["monthly_limit"] - 100

    def test_zero_usage_default(self, mock_redis_helpers):
        summary = get_usage_summary()
        fc = summary["providers"]["firecrawl"]
        assert fc["used"] == 0
        assert fc["remaining"] == PROVIDER_CONFIGS["firecrawl"]["monthly_limit"]

    def test_lifetime_flag_present(self, mock_redis_helpers):
        summary = get_usage_summary()
        assert summary["providers"]["firecrawl"]["is_lifetime"] is True
        assert summary["providers"]["scrapedo"]["is_lifetime"] is False

    def test_circuit_breaker_open_reported(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_OPEN, "failure_count": 5
        })
        summary = get_usage_summary()
        assert summary["circuit_breakers"]["firecrawl"]["state"] == CB_OPEN
        assert summary["circuit_breakers"]["firecrawl"]["failures"] == 5

    def test_remaining_never_negative(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("firecrawl")] = "9999"
        summary = get_usage_summary()
        assert summary["providers"]["firecrawl"]["remaining"] == 0

    def test_redis_error_in_summary_returns_zero_usage(self):
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("Redis down")):
            summary = get_usage_summary()
            for provider in PROVIDER_CONFIGS:
                assert summary["providers"][provider]["used"] == 0


class TestEdgeCases:
    """Additional edge-case tests for coverage."""

    def test_budget_key_unknown_provider_defaults_monthly(self):
        # Unknown provider has no config, so is_lifetime is falsy → monthly key
        key = _budget_key("unknown_provider")
        assert key.startswith("budget:unknown_provider:")

    def test_circuit_key_format(self):
        assert _circuit_key("firecrawl") == "circuit:firecrawl"
        assert _circuit_key("scrapedo") == "circuit:scrapedo"

    def test_has_budget_one_under_limit(self, mock_redis_helpers):
        limit = PROVIDER_CONFIGS["firecrawl"]["monthly_limit"]
        mock_redis_helpers["store"][_budget_key("firecrawl")] = str(limit - 1)
        assert has_budget("firecrawl") is True

    def test_record_usage_unknown_provider_no_crash(self, mock_redis_helpers):
        # Unknown provider has no config — should not crash
        record_usage("unknown_provider")

    def test_record_failure_on_already_open_breaker(self, mock_redis_helpers):
        # Breaker already open — another failure should keep it open, increment count
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_OPEN, "failure_count": 5, "tripped_at": time.time()
        })
        record_failure("firecrawl")
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["state"] == CB_OPEN
        assert state["failure_count"] == 6

    def test_malformed_json_in_circuit_state_fail_open(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = "not-valid-json"
        # json.loads will raise, caught by except → fail-open
        assert is_circuit_closed("firecrawl") is True

    def test_record_failure_with_malformed_circuit_state(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = "not-valid-json"
        # Should not crash — exception caught
        record_failure("firecrawl")

    def test_success_resets_failure_count_on_closed(self, mock_redis_helpers):
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps({
            "state": CB_CLOSED, "failure_count": 2
        })
        record_success("firecrawl")
        raw = mock_redis_helpers["store"][_circuit_key("firecrawl")]
        state = json.loads(raw)
        assert state["failure_count"] == 0

    def test_has_budget_serper(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("serper")] = "100"
        assert has_budget("serper") is True

    def test_has_budget_serper_exhausted(self, mock_redis_helpers):
        mock_redis_helpers["store"][_budget_key("serper")] = str(PROVIDER_CONFIGS["serper"]["monthly_limit"])
        assert has_budget("serper") is False

    def test_record_usage_count_zero(self, mock_redis_helpers):
        record_usage("firecrawl", count=0)
        mock_redis_helpers["incr"].assert_not_called()

    def test_last_failure_at_recorded(self, mock_redis_helpers):
        before = time.time()
        record_failure("scrapedo")
        after = time.time()
        raw = mock_redis_helpers["store"][_circuit_key("scrapedo")]
        state = json.loads(raw)
        assert before <= state["last_failure_at"] <= after

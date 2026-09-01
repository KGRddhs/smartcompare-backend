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

    def test_serper_is_lifetime_and_key_scoped(self, monkeypatch):
        """S3 L4.3 — serper's lifetime counter is now KEY-SCOPED so a rotation
        starts a fresh honest counter (fixes the 5136-across-4-accounts false-
        trip). Format: budget:serper:{first8-of-SERPER_API_KEY}:lifetime."""
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843deadbeef")
        key = _budget_key("serper")
        assert key == "budget:serper:0cda9843:lifetime"


class TestSerperKeyScoping:
    """S3 L4.3 — key-scope budget:serper:lifetime + rotation-safe burn sentinel.

    The single shared counter carried burn across 4 rotated accounts and false-
    tripped at the 2200 cap mid-run (S2 G6). Scoping the key to the live key's
    8-char prefix means a rotation naturally starts a fresh counter, and the
    burn-alert sentinel re-arms on the new prefix without a manual DEL."""

    def test_key_prefix_reads_first_8_chars(self, monkeypatch):
        from app.services.api_budget_service import _serper_key_prefix
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843xxxxxxxxxxxx")
        assert _serper_key_prefix() == "0cda9843"

    def test_key_prefix_fallback_when_unset(self, monkeypatch):
        """Unset/empty SERPER_API_KEY → a stable 'nokey' sentinel prefix so the
        key is deterministic in test/CI environments without the secret."""
        from app.services.api_budget_service import _serper_key_prefix
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        assert _serper_key_prefix() == "nokey"
        monkeypatch.setenv("SERPER_API_KEY", "")
        assert _serper_key_prefix() == "nokey"

    def test_key_prefix_reads_env_fresh(self, monkeypatch):
        """Read fresh each call so a Railway env update / rotation takes effect
        without a process restart (mirrors _serper_image_daily_budget)."""
        from app.services.api_budget_service import _serper_key_prefix
        monkeypatch.setenv("SERPER_API_KEY", "aaaaaaaa1111")
        assert _serper_key_prefix() == "aaaaaaaa"
        monkeypatch.setenv("SERPER_API_KEY", "bbbbbbbb2222")
        assert _serper_key_prefix() == "bbbbbbbb"

    def test_budget_key_embeds_prefix(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843zzzz")
        assert _budget_key("serper") == "budget:serper:0cda9843:lifetime"

    def test_rotation_changes_the_counter_key(self, monkeypatch):
        """Two different keys → two different counter keys → a rotation cannot
        inherit the previous account's burn."""
        monkeypatch.setenv("SERPER_API_KEY", "3d304edepleted")
        old_key = _budget_key("serper")
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843fresh")
        new_key = _budget_key("serper")
        assert old_key != new_key
        assert old_key == "budget:serper:3d304ede:lifetime"
        assert new_key == "budget:serper:0cda9843:lifetime"

    def test_other_lifetime_providers_not_scoped(self):
        """Only serper is key-scoped; firecrawl stays on its plain lifetime key
        (not API-key-rotated the same way)."""
        assert _budget_key("firecrawl") == "budget:firecrawl:lifetime"

    def test_monthly_provider_unaffected(self):
        """scrapedo (monthly) keeps its month-stamped key, no prefix."""
        key = _budget_key("scrapedo")
        assert key.startswith("budget:scrapedo:")
        assert "lifetime" not in key

    def test_burn_sentinel_embeds_prefix(self, monkeypatch):
        """S3 L4.3 — the burn-alert sentinel is keyed by the prefix so a
        rotation re-arms the alert (new prefix → new sentinel key → not the
        latched no-expiry one from the previous key)."""
        from app.services.api_budget_service import _burn_sentinel_key
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843zzzz")
        sentinel = _burn_sentinel_key("serper")
        assert "0cda9843" in sentinel
        assert "burn_alert_fired" in sentinel

    def test_burn_sentinel_rotation_resets(self, monkeypatch):
        """Different keys → different sentinels → the latched lifetime alert
        from the old key does NOT suppress the new key's alert."""
        from app.services.api_budget_service import _burn_sentinel_key
        monkeypatch.setenv("SERPER_API_KEY", "3d304edepleted")
        old_sentinel = _burn_sentinel_key("serper")
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843fresh")
        new_sentinel = _burn_sentinel_key("serper")
        assert old_sentinel != new_sentinel

    def test_record_usage_increments_scoped_key(self, mock_redis_helpers, monkeypatch):
        """record_usage writes to the key-scoped counter, end-to-end."""
        from app.services import api_budget_service as abs_mod
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843zzzz")
        abs_mod.record_usage("serper", 1)
        assert mock_redis_helpers["store"]["budget:serper:0cda9843:lifetime"] == "1"

    def test_fresh_key_starts_at_zero_used(self, mock_redis_helpers, monkeypatch):
        """A rotation onto a fresh key reports 0 used even when the OLD key's
        counter is at the cap in Redis (the false-trip fix, end-to-end)."""
        from app.services.api_budget_service import get_burn_status
        # Old depleted key's counter is parked over the cap.
        mock_redis_helpers["store"]["budget:serper:3d304ede:lifetime"] = "5136"
        # Rotate onto the fresh key.
        monkeypatch.setenv("SERPER_API_KEY", "0cda9843fresh")
        status = get_burn_status("serper")
        assert status["used"] == 0
        assert status["over_threshold"] is False


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
        from app.services import api_budget_service as abs_mod
        state = {"state": CB_HALF_OPEN, "failure_count": 0, "half_open_calls": 1}
        mock_redis_helpers["store"][_circuit_key("firecrawl")] = json.dumps(state)
        # #115 — the admission count now lives in the atomic per-trip-window
        # probe counter (not the JSON blob), so seed THAT to represent the one
        # probe already admitted. Same pinned semantic: excess calls blocked.
        mock_redis_helpers["store"][abs_mod._half_open_probe_key("firecrawl", state)] = "1"
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


# ============================================================================
# Bundle E S3 — Serper Images dedicated daily counter
# ============================================================================

@pytest.fixture
def mock_image_redis():
    """Mock redis_client.incrby/decrby/expire for the image-counter tests."""
    store = {"counter": 0}

    def fake_incrby(key, n):
        store["counter"] += n
        store[key] = store["counter"]
        return store["counter"]

    def fake_decrby(key, n):
        store["counter"] -= n
        store[key] = store["counter"]
        return store["counter"]

    mock_client = MagicMock()
    mock_client.incrby = MagicMock(side_effect=fake_incrby)
    mock_client.decrby = MagicMock(side_effect=fake_decrby)
    mock_client.expire = MagicMock(return_value=True)

    with patch("app.services.cache_service.redis_client", mock_client):
        yield {"client": mock_client, "store": store}


class TestSerperImageCounter:
    def test_first_call_allowed_and_sets_ttl(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        result = try_consume_serper_image_credit(1)

        assert result is True
        mock_image_redis["client"].incrby.assert_called_once()
        # Counter at 1 → first write → TTL must be set
        mock_image_redis["client"].expire.assert_called_once()

    def test_subsequent_calls_do_not_reset_ttl(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        try_consume_serper_image_credit(1)
        try_consume_serper_image_credit(1)

        # First call sets TTL, second call should NOT
        assert mock_image_redis["client"].expire.call_count == 1

    def test_within_budget_returns_true(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        # Default budget is 500; 100 calls should still allow
        for _ in range(100):
            assert try_consume_serper_image_credit(1) is True

    def test_over_budget_returns_false_and_rolls_back(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        # Set counter near limit, then try to overflow
        mock_image_redis["store"]["counter"] = 499
        assert try_consume_serper_image_credit(1) is True   # 500 (at limit, still OK)
        assert try_consume_serper_image_credit(1) is False  # 501 → rejected + rollback

        # After rollback, counter should be back at 500
        assert mock_image_redis["store"]["counter"] == 500
        mock_image_redis["client"].decrby.assert_called_once()

    def test_n_zero_returns_true_without_redis_call(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        assert try_consume_serper_image_credit(0) is True
        mock_image_redis["client"].incrby.assert_not_called()

    def test_n_negative_returns_true_without_redis_call(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        assert try_consume_serper_image_credit(-1) is True
        mock_image_redis["client"].incrby.assert_not_called()

    def test_redis_none_fails_open(self):
        from app.services.api_budget_service import try_consume_serper_image_credit

        with patch("app.services.cache_service.redis_client", None):
            assert try_consume_serper_image_credit(1) is True

    def test_redis_exception_fails_open(self):
        """Redis errors must not block image pipeline — burn the credit, keep going.

        Per memory/project_upstash_redis_singlepoint_failure.md: image pipeline
        is a UX feature, not security; we'd rather risk over-spending Serper
        credit than ship a placeholder image when Redis is down.
        """
        from app.services.api_budget_service import try_consume_serper_image_credit

        mock_client = MagicMock()
        mock_client.incrby.side_effect = RuntimeError("Redis SET error")
        with patch("app.services.cache_service.redis_client", mock_client):
            assert try_consume_serper_image_credit(1) is True

    def test_expire_failure_does_not_block(self, mock_image_redis):
        """TTL expire failure is logged but the increment still counts."""
        from app.services.api_budget_service import try_consume_serper_image_credit

        mock_image_redis["client"].expire.side_effect = RuntimeError("EXPIRE failed")
        # Still returns True — counter was incremented even though TTL set failed
        assert try_consume_serper_image_credit(1) is True

    def test_custom_n_value_consumes_multiple_credits(self, mock_image_redis):
        from app.services.api_budget_service import try_consume_serper_image_credit

        assert try_consume_serper_image_credit(3) is True
        assert mock_image_redis["store"]["counter"] == 3

    def test_env_var_overrides_default_budget(self, mock_image_redis, monkeypatch):
        from app.services.api_budget_service import try_consume_serper_image_credit

        monkeypatch.setenv("SERPER_IMAGE_DAILY_BUDGET", "10")
        # First 10 calls succeed
        for _ in range(10):
            assert try_consume_serper_image_credit(1) is True
        # 11th call rejected
        assert try_consume_serper_image_credit(1) is False

    def test_env_var_malformed_falls_back_to_default(self, mock_image_redis, monkeypatch):
        """Garbage env value → use default 500."""
        from app.services.api_budget_service import (
            try_consume_serper_image_credit,
            _serper_image_daily_budget,
        )

        monkeypatch.setenv("SERPER_IMAGE_DAILY_BUDGET", "not_an_int")
        assert _serper_image_daily_budget() == 500
        assert try_consume_serper_image_credit(1) is True


class TestSerperImageUsageDiagnostic:
    def test_usage_summary_includes_serper_images_block(self, mock_redis_helpers):
        from app.services.api_budget_service import get_usage_summary

        result = get_usage_summary()
        assert "serper_images" in result["providers"]
        assert result["providers"]["serper_images"]["scope"] == "daily"
        assert result["providers"]["serper_images"]["used"] == 0
        assert result["providers"]["serper_images"]["limit"] == 500

    def test_usage_summary_reflects_consumed_credits(self, mock_redis_helpers):
        from app.services.api_budget_service import _serper_image_key, get_usage_summary

        mock_redis_helpers["store"][_serper_image_key()] = "42"
        result = get_usage_summary()
        assert result["providers"]["serper_images"]["used"] == 42
        assert result["providers"]["serper_images"]["remaining"] == 458

    def test_get_serper_image_usage_returns_dict(self, mock_redis_helpers):
        from app.services.api_budget_service import _serper_image_key, get_serper_image_usage

        mock_redis_helpers["store"][_serper_image_key()] = "5"
        usage = get_serper_image_usage()
        assert usage == {"used": 5, "limit": 500, "remaining": 495}

    def test_get_serper_image_usage_fail_safe_when_redis_errors(self):
        from app.services.api_budget_service import get_serper_image_usage

        with patch(
            "app.services.api_budget_service._redis_get",
            side_effect=Exception("Redis down"),
        ):
            usage = get_serper_image_usage()
            assert usage == {"used": 0, "limit": 500, "remaining": 500}


class TestSerperImageKey:
    def test_key_contains_today_date(self):
        from app.services.api_budget_service import _serper_image_key
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert _serper_image_key() == f"budget:serper_images:{today}"


# ============================================================================
# I5.0 (Bundle B S2) — 80%-burn alert + ceiling reconciliation
# ============================================================================
# Protects every measurement run this session: the S1 baseline depleted the
# key mid-run. has_budget() only warns at warn_at (~91% for serper); the burn
# alert fires a log + Sentry capture_message ONCE when a provider crosses 80%
# of its ceiling, de-duped via a Redis sentinel so it does not spam.


class TestBurnAlertThreshold:
    def test_burn_fraction_constant_is_80pct(self):
        from app.services.api_budget_service import WARN_BURN_FRACTION
        assert WARN_BURN_FRACTION == 0.80

    def test_serper_80pct_threshold_value(self):
        # 2200 ceiling * 0.80 = 1760 credits.
        from app.services.api_budget_service import _burn_threshold
        assert _burn_threshold("serper") == 1760

    def test_get_burn_status_below_threshold(self, mock_redis_helpers):
        from app.services.api_budget_service import get_burn_status
        mock_redis_helpers["store"][_budget_key("serper")] = "1000"
        status = get_burn_status("serper")
        assert status["used"] == 1000
        assert status["limit"] == 2200
        assert status["threshold"] == 1760
        assert status["over_threshold"] is False
        # fraction is dashboard-rounded to 4 decimals.
        assert status["fraction"] == round(1000 / 2200, 4)

    def test_get_burn_status_at_threshold(self, mock_redis_helpers):
        from app.services.api_budget_service import get_burn_status
        mock_redis_helpers["store"][_budget_key("serper")] = "1760"
        status = get_burn_status("serper")
        assert status["over_threshold"] is True

    def test_get_burn_status_unknown_provider(self, mock_redis_helpers):
        from app.services.api_budget_service import get_burn_status
        status = get_burn_status("nonexistent")
        assert status["over_threshold"] is False
        assert status["limit"] == 0

    def test_get_burn_status_fail_open_on_redis_error(self):
        from app.services.api_budget_service import get_burn_status
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("down")):
            status = get_burn_status("serper")
            # Fail-safe: no usage observed, never raises.
            assert status["used"] == 0
            assert status["over_threshold"] is False


class TestBurnAlertFires:
    def test_alert_fires_when_crossing_80pct(self, mock_redis_helpers):
        """Drill test (binding-table exit criterion): crossing 80% fires a
        Sentry capture_message + WARNING log exactly once."""
        from app.services import api_budget_service as abs_mod
        # Seed just below threshold so the next increment crosses it.
        mock_redis_helpers["store"][_budget_key("serper")] = "1759"

        fake_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": fake_sentry}):
            with patch.object(abs_mod.logger, "warning") as m_warn:
                abs_mod.record_usage("serper", 1)  # 1759 -> 1760, crosses 80%

        # Sentry alerted at warning level.
        assert fake_sentry.capture_message.called
        _args, _kwargs = fake_sentry.capture_message.call_args
        msg = _args[0] if _args else _kwargs.get("message", "")
        assert "serper" in msg.lower()
        assert "80%" in msg or "burn" in msg.lower()
        # WARNING log emitted with a burn marker.
        assert any("BURN" in str(c.args[0]).upper() or "burn" in str(c.args).lower()
                   for c in m_warn.call_args_list)

    def test_alert_does_not_fire_below_threshold(self, mock_redis_helpers):
        from app.services import api_budget_service as abs_mod
        mock_redis_helpers["store"][_budget_key("serper")] = "100"

        fake_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": fake_sentry}):
            abs_mod.record_usage("serper", 1)  # 100 -> 101, far below 1760

        assert not fake_sentry.capture_message.called

    def test_alert_fires_once_then_deduped(self, mock_redis_helpers):
        """The sentinel must suppress repeat alerts on every subsequent call
        within the same budget window."""
        from app.services import api_budget_service as abs_mod
        mock_redis_helpers["store"][_budget_key("serper")] = "1759"

        fake_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": fake_sentry}):
            abs_mod.record_usage("serper", 1)   # crosses -> alert #1
            abs_mod.record_usage("serper", 1)   # 1761 -> still over, deduped
            abs_mod.record_usage("serper", 5)   # 1766 -> still over, deduped

        assert fake_sentry.capture_message.call_count == 1

    def test_record_usage_still_increments_when_sentry_missing(self, mock_redis_helpers):
        """Alert path must never break the counter even if sentry_sdk import
        fails (ImportError swallowed)."""
        from app.services import api_budget_service as abs_mod
        mock_redis_helpers["store"][_budget_key("serper")] = "1759"

        # Force ImportError on `import sentry_sdk`.
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "sentry_sdk":
                raise ImportError("no sentry")
            return real_import(name, *a, **k)

        with patch("builtins.__import__", side_effect=fake_import):
            abs_mod.record_usage("serper", 1)

        assert mock_redis_helpers["store"][_budget_key("serper")] == "1760"

    def test_burn_alert_never_raises_on_redis_error(self, mock_redis_helpers):
        """If the sentinel read/write errors, record_usage must still complete
        (alert is best-effort, fail-open)."""
        from app.services import api_budget_service as abs_mod
        mock_redis_helpers["store"][_budget_key("serper")] = "1759"

        # _maybe_fire_burn_alert reads the sentinel via _redis_get; make that
        # specific path raise while the counter incrby (on the client) succeeds.
        with patch("app.services.api_budget_service._redis_get", side_effect=Exception("down")):
            # Should not raise.
            abs_mod.record_usage("serper", 1)


class TestBurnAlertSentinelTTL:
    """G1 ultracode finding F1 — the sentinel TTL ternary was INVERTED:
    lifetime providers (serper/firecrawl — the S1-depletion case) got the 1h
    _CB_TTL, so the sentinel expired after an hour and the alert re-fired
    HOURLY until rotation. The original dedup test couldn't catch it because
    the mock-redis never expires keys — so these tests assert the `ex` value
    passed to _redis_set directly, independent of mock expiry behavior.

    Correct semantics: a LIFETIME provider stays latched (no expiry) until the
    key is manually reset on rotation; a MONTHLY provider re-arms via its
    month-stamped sentinel key, bounded by _MONTHLY_TTL."""

    def _sentinel_set_ex(self, m_set, provider):
        """Return the `ex` kwarg _redis_set was called with for `provider`'s
        burn sentinel (None if the call wasn't made)."""
        from app.services.api_budget_service import _burn_sentinel_key
        sentinel = _burn_sentinel_key(provider)
        for call in m_set.call_args_list:
            args, kwargs = call
            key = args[0] if args else kwargs.get("key")
            if key == sentinel:
                return kwargs.get("ex", args[2] if len(args) > 2 else None)
        return "NO_CALL"

    def test_lifetime_sentinel_has_no_expiry_latched(self, mock_redis_helpers):
        """serper is lifetime → sentinel must be latched (ex=None), NOT 1h."""
        from app.services import api_budget_service as abs_mod
        from app.services.api_budget_service import _CB_TTL
        mock_redis_helpers["store"][_budget_key("serper")] = "1759"
        fake_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": fake_sentry}):
            abs_mod.record_usage("serper", 1)  # crosses 1760 → fires + sets sentinel
        ex = self._sentinel_set_ex(mock_redis_helpers["set"], "serper")
        assert ex != "NO_CALL", "lifetime crossing must set the sentinel"
        # The bug: ex == _CB_TTL (3600). The fix: latched (None) — never the 1h.
        assert ex != _CB_TTL, "F1: lifetime sentinel must NOT use the 1h _CB_TTL"
        assert ex is None, "lifetime sentinel must be latched (no expiry) until rotation"

    def test_monthly_sentinel_is_bounded_not_latched(self, mock_redis_helpers):
        """A monthly provider's sentinel is bounded by _MONTHLY_TTL (it re-arms
        on next month's key anyway). scrapedo is the monthly provider."""
        from app.services import api_budget_service as abs_mod
        from app.services.api_budget_service import _MONTHLY_TTL, _burn_threshold
        # Seed scrapedo just below its 80% threshold so the next call crosses.
        thr = _burn_threshold("scrapedo")
        mock_redis_helpers["store"][_budget_key("scrapedo")] = str(thr - 1)
        fake_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": fake_sentry}):
            abs_mod.record_usage("scrapedo", 1)
        ex = self._sentinel_set_ex(mock_redis_helpers["set"], "scrapedo")
        assert ex != "NO_CALL", "monthly crossing must set the sentinel"
        assert ex == _MONTHLY_TTL, "monthly sentinel must be bounded by _MONTHLY_TTL"


class TestHalfOpenCounterAtomicity:
    """#115 hard precondition for any ENABLE_ASYNC_REDIS_OFFLOAD canary:
    the half-open probe admission must be a single atomic Redis INCR, never a
    decode -> +1 -> _redis_set read-modify-write. Under to_thread offload,
    concurrent render-gate checks running the RMW in parallel all read the same
    half_open_calls and admit MULTIPLE paid render probes (spend leak).

    Assertion shape mirrors tests/test_model_router.py
    test_record_usage_uses_atomic_incrby.
    """

    def _half_open_state(self, half_open_calls=0, tripped_at=1000.0):
        return json.dumps({
            "state": CB_HALF_OPEN,
            "failure_count": 3,
            "half_open_calls": half_open_calls,
            "tripped_at": tripped_at,
        })

    def test_half_open_counter_is_atomic_incr(self, mock_redis_helpers):
        """The admission decision must come from the INCR return value, not
        from the JSON blob. Seed the blob at 0 but the atomic counter at 1
        (what a concurrent thread's INCR just did): the RMW implementation
        reads 0 -> +1 -> admits (True); the atomic implementation INCRs to 2
        -> rejects (False)."""
        from app.services import api_budget_service as abs_mod

        state_key = _circuit_key("firecrawl")
        mock_redis_helpers["store"][state_key] = self._half_open_state(0)
        probe_key = abs_mod._half_open_probe_key("firecrawl", {"tripped_at": 1000.0})
        mock_redis_helpers["store"][probe_key] = "1"  # concurrent probe already admitted

        assert is_circuit_closed("firecrawl") is False, (
            "admission ignored the atomic counter — the non-atomic RMW is back"
        )
        # And the atomic op actually ran (the seam the offload makes safe).
        incr_keys = [c.args[0] for c in mock_redis_helpers["incr"].call_args_list]
        assert probe_key in incr_keys, "half-open admission did not INCR the probe key"

    def test_half_open_admission_never_rewrites_count_from_blob(self, mock_redis_helpers):
        """Serial sanity: with a fresh probe window, the first check is admitted,
        the second rejected — same observable contract as M13-31, now atomic."""
        state_key = _circuit_key("scrapedo")
        mock_redis_helpers["store"][state_key] = self._half_open_state(0)

        assert is_circuit_closed("scrapedo") is True
        assert is_circuit_closed("scrapedo") is False

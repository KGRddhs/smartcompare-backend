"""M13-31 pin — the circuit-breaker HALF_OPEN state must admit exactly ONE probe.

Failure scenario (from the review): after 3 failures trip the breaker and the
recovery timeout elapses, `half_open_calls` is written and read but never
incremented, so every `is_circuit_closed` call in the half-open window returns
True — the whole Tier-1.5 render fan-out (~6-10 candidates) is admitted where a
single probe was designed. The review reproduced six consecutive True returns.

Zero-network: `_redis_get`/`_redis_set` are dict-stubbed at the module level, so
this exercises the state machine with no Upstash round trip.
"""
import json

from unittest.mock import patch

from app.services import api_budget_service as abs_mod
from app.services.api_budget_service import (
    is_circuit_closed,
    record_failure,
    CB_FAILURE_THRESHOLD,
    CB_RECOVERY_TIMEOUT,
    CB_HALF_OPEN_MAX_CALLS,
    CB_OPEN,
    CB_HALF_OPEN,
    _circuit_key,
)


def _dict_stubbed_redis():
    store = {}

    def fake_get(key):
        return store.get(key)

    def fake_set(key, value, ex=None):
        store[key] = value
        return True

    return store, fake_get, fake_set


def test_half_open_admits_exactly_one_probe_after_recovery():
    store, fake_get, fake_set = _dict_stubbed_redis()
    with patch.object(abs_mod, "_redis_get", side_effect=fake_get), \
         patch.object(abs_mod, "_redis_set", side_effect=fake_set):
        # Trip the breaker with CB_FAILURE_THRESHOLD failures.
        for _ in range(CB_FAILURE_THRESHOLD):
            record_failure("firecrawl")
        tripped = json.loads(store[_circuit_key("firecrawl")])
        assert tripped["state"] == CB_OPEN

        # Age the trip past the recovery window so the next check transitions
        # OPEN -> HALF_OPEN.
        tripped["tripped_at"] = tripped["tripped_at"] - CB_RECOVERY_TIMEOUT - 1
        store[_circuit_key("firecrawl")] = json.dumps(tripped)

        # Six consecutive gate checks — the whole render fan-out hitting the
        # gate. Exactly CB_HALF_OPEN_MAX_CALLS (== 1) must be admitted; the rest
        # must short-circuit until a success/failure resolves the probe.
        results = [is_circuit_closed("firecrawl") for _ in range(6)]

    assert sum(results) == CB_HALF_OPEN_MAX_CALLS == 1, (
        f"half-open admitted {sum(results)} probes; expected exactly 1 "
        f"(results={results})"
    )
    # And the very first check is the admitted probe (the transition itself).
    assert results[0] is True
    assert results[1:] == [False] * 5


def test_half_open_state_is_half_open_after_transition():
    """The transition still lands in HALF_OPEN state (not skipped to CLOSED)."""
    store, fake_get, fake_set = _dict_stubbed_redis()
    with patch.object(abs_mod, "_redis_get", side_effect=fake_get), \
         patch.object(abs_mod, "_redis_set", side_effect=fake_set):
        for _ in range(CB_FAILURE_THRESHOLD):
            record_failure("scrapedo")
        state = json.loads(store[_circuit_key("scrapedo")])
        state["tripped_at"] = state["tripped_at"] - CB_RECOVERY_TIMEOUT - 1
        store[_circuit_key("scrapedo")] = json.dumps(state)

        assert is_circuit_closed("scrapedo") is True  # probe admitted
        persisted = json.loads(store[_circuit_key("scrapedo")])
    assert persisted["state"] == CB_HALF_OPEN
    assert persisted["half_open_calls"] == CB_HALF_OPEN_MAX_CALLS

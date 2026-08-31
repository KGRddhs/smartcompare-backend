"""M13-06 pin — ENABLE_ASYNC_REDIS_OFFLOAD now covers the request-path WRITES and
the render-provider budget/breaker gate, not only the 4 reads.

Failure scenario: a warm streaming compare performs ~10 blocking Upstash SET round
trips (specs + price cache writes) plus per-provider budget/breaker reads, ALL
inline on the single event loop — ~163ms/write of head-of-line stall inside a 15s
race. The offload dispatch previously covered only the 4 reads. Flag OFF stays
byte-identical (inline).
"""
import threading

import pytest

import app.services.structured_comparison_service as scs


@pytest.mark.asyncio
async def test_cache_set_async_offloads_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    main = threading.current_thread()
    seen = {}

    def fake_set(key, value, ttl):
        seen["thread"] = threading.current_thread()
        return True
    monkeypatch.setattr(scs, "set_cached", fake_set)

    await scs._cache_set_async("k", {"v": 1}, 60)
    assert seen["thread"] is not main, "flag ON must run the SET off-loop"


@pytest.mark.asyncio
async def test_cache_set_async_inline_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}

    def fake_set(key, value, ttl):
        seen["thread"] = threading.current_thread()
        return True
    monkeypatch.setattr(scs, "set_cached", fake_set)

    await scs._cache_set_async("k", {"v": 1}, 60)
    assert seen["thread"] is main, "flag OFF must run inline (byte-identical to today)"


@pytest.mark.asyncio
async def test_provider_gate_batched_offload_and_value(monkeypatch):
    monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    main = threading.current_thread()
    threads = []

    def fake_breaker(p):
        threads.append(threading.current_thread())
        return True

    def fake_budget(p):
        threads.append(threading.current_thread())
        return True
    monkeypatch.setattr(scs, "is_circuit_closed", fake_breaker)
    monkeypatch.setattr(scs, "has_budget", fake_budget)

    ok = await scs._provider_gate_ok_async("firecrawl")
    assert ok is True
    # Both reads ran in the SAME off-loop worker (batched into one to_thread).
    assert threads and all(t is not main for t in threads)
    assert len(set(threads)) == 1


@pytest.mark.asyncio
async def test_provider_gate_open_breaker_short_circuits(monkeypatch):
    """has_budget is not consulted when the breaker is open (left-to-right, same
    as the inline `is_circuit_closed(p) and has_budget(p)`)."""
    monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    budget_calls = {"n": 0}
    monkeypatch.setattr(scs, "is_circuit_closed", lambda p: False)

    def fake_budget(p):
        budget_calls["n"] += 1
        return True
    monkeypatch.setattr(scs, "has_budget", fake_budget)

    ok = await scs._provider_gate_ok_async("scrapedo")
    assert ok is False
    assert budget_calls["n"] == 0


@pytest.mark.asyncio
async def test_provider_gate_inline_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}
    monkeypatch.setattr(scs, "is_circuit_closed", lambda p: True)

    def fake_budget(p):
        seen["thread"] = threading.current_thread()
        return True
    monkeypatch.setattr(scs, "has_budget", fake_budget)

    ok = await scs._provider_gate_ok_async("firecrawl")
    assert ok is True
    assert seen["thread"] is main, "flag OFF must evaluate the gate inline"

"""Async Redis offload — scs._cache_get_async (scraping audit 2026-07-08, PR1).

The module-level `redis_client` is a BLOCKING (httpx.Client) Upstash client, so every
get_cached from an async orchestrator method stalls the single worker event loop for the
full REST RTT (~6-8 guaranteed per warm compare). ENABLE_ASYNC_REDIS_OFFLOAD (default OFF)
offloads the sync GET to a worker thread (asyncio.to_thread) so the loop is free during the RTT.

The dispatch (`_cache_get_async`) lives in structured_comparison_service and references the
module-level `get_cached` in BOTH branches, so a test that patches
`structured_comparison_service.get_cached` still intercepts it (a cache_service-side wrapper
would silently bypass those patches). Flag OFF -> inline sync call -> byte-identical.
"""
import asyncio
import os
import time

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services import cache_service as cs
from app.services import structured_comparison_service as scs


@pytest.mark.asyncio
class TestCacheGetAsync:
    async def test_flag_off_runs_inline_no_offload(self, monkeypatch):
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
        monkeypatch.setattr(scs, "get_cached", lambda k: {"k": k})
        called = {"to_thread": False}
        real = asyncio.to_thread

        async def spy(fn, *a, **kw):
            called["to_thread"] = True
            return await real(fn, *a, **kw)

        monkeypatch.setattr(scs.asyncio, "to_thread", spy)
        out = await scs._cache_get_async("x")
        assert out == {"k": "x"}
        assert called["to_thread"] is False   # inline sync branch, no offload

    async def test_patch_point_preserved(self, monkeypatch):
        # THE reason dispatch lives in scs: patching scs.get_cached must intercept a HIT
        # through _cache_get_async (both flag states), so existing cache-hit tests keep working.
        monkeypatch.setattr(scs, "get_cached", lambda k: {"cached_hit": k})
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
        assert await scs._cache_get_async("h") == {"cached_hit": "h"}
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "1")
        assert await scs._cache_get_async("h") == {"cached_hit": "h"}

    async def test_flag_on_offloads_to_thread(self, monkeypatch):
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "1")
        monkeypatch.setattr(scs, "get_cached", lambda k: {"k": k})
        seen = {}
        real = asyncio.to_thread

        async def spy(fn, *a, **kw):
            seen["fn"], seen["args"] = fn, a
            return await real(fn, *a, **kw)

        monkeypatch.setattr(scs.asyncio, "to_thread", spy)
        out = await scs._cache_get_async("y")
        assert out == {"k": "y"}
        assert seen["fn"] is scs.get_cached and seen["args"] == ("y",)

    async def test_value_equality_on_vs_off(self, monkeypatch):
        monkeypatch.setattr(scs, "get_cached", lambda k: {"hit": k})
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "0")
        off = await scs._cache_get_async("p")
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "1")
        on = await scs._cache_get_async("p")
        assert off == on == {"hit": "p"}

    async def test_none_on_miss_both_ways(self, monkeypatch):
        monkeypatch.setattr(scs, "get_cached", lambda k: None)
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "0")
        assert await scs._cache_get_async("m") is None
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "1")
        assert await scs._cache_get_async("m") is None

    async def test_flag_on_does_not_block_loop(self, monkeypatch):
        # A blocking get (0.2s) under the flag must run in a thread so a concurrent
        # coroutine keeps ticking. If it blocked the loop inline, ticks would be ~0.
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "1")
        monkeypatch.setattr(scs, "get_cached", lambda k: (time.sleep(0.2), {"k": k})[1])
        ticks = {"n": 0}

        async def ticker():
            while True:
                await asyncio.sleep(0.005)
                ticks["n"] += 1

        tk = asyncio.create_task(ticker())
        out = await scs._cache_get_async("z")
        n_at_return = ticks["n"]
        tk.cancel()
        try:
            await tk
        except asyncio.CancelledError:
            pass
        assert out == {"k": "z"}
        assert n_at_return >= 10   # loop serviced the ticker during the 0.2s offload

    async def test_flag_off_blocks_loop_documents_fix(self, monkeypatch):
        # Contrast: flag OFF runs the blocking get inline -> the loop stalls -> the
        # concurrent ticker is starved during the 0.2s. Documents WHY the fix matters.
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
        monkeypatch.setattr(scs, "get_cached", lambda k: (time.sleep(0.2), {"k": k})[1])
        ticks = {"n": 0}

        async def ticker():
            while True:
                await asyncio.sleep(0.005)
                ticks["n"] += 1

        tk = asyncio.create_task(ticker())
        await asyncio.sleep(0)  # let the ticker start
        await scs._cache_get_async("z")
        n_at_return = ticks["n"]
        tk.cancel()
        try:
            await tk
        except asyncio.CancelledError:
            pass
        assert n_at_return <= 3   # loop was blocked inline (few/no ticks)


def test_flag_helper_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    assert cs._redis_offload_enabled() is False
    monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    assert cs._redis_offload_enabled() is True

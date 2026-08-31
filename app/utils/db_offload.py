"""M13-05 — ENABLE_SYNC_DB_OFFLOAD: move the REQUEST-PATH HOT SET of blocking
Supabase calls off the asyncio event loop.

The sync supabase client blocks the loop for a full Supabase RTT inside `async
def`, and on the single-worker uvicorn one user's profile fetch stalls every other
coroutine — and because the 15s price race and the 25/30s stream cap are wall-clock
deadlines, a burst of concurrent DB round trips converts directly into hard-cap
timeouts for unrelated requests.

`run_db(call)` runs a blocking `.execute()` (or any blocking client call) through
`asyncio.to_thread` when the flag is ON, and INLINE when OFF. Flag OFF is
byte-identical: `run_db` is an `async def` with no `await` on the inline branch, so
`await run_db(lambda: q.execute())` runs the call synchronously to completion with
no new suspension point or scheduling change — exactly a direct `q.execute()`.

Read PER CALL via os.getenv (the price_service.exact_gate_enabled idiom) so Railway
can flip it without a restart. Default OFF so the executor pressure can be measured
before it is universal.
"""
from __future__ import annotations

import asyncio
import os
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def sync_db_offload_enabled() -> bool:
    return os.getenv("ENABLE_SYNC_DB_OFFLOAD", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


async def run_db(call: Callable[[], T]) -> T:
    """Run a blocking Supabase call. Flag ON -> asyncio.to_thread (off-loop);
    flag OFF -> inline (byte-identical to a direct blocking call)."""
    if sync_db_offload_enabled():
        return await asyncio.to_thread(call)
    return call()

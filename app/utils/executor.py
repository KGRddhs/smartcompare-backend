"""M13-34 — an explicitly-sized default ThreadPoolExecutor for the ~33 to_thread
sites (adapter curl fetches, and the sync DB / Redis offload behind
ENABLE_SYNC_DB_OFFLOAD / ENABLE_ASYNC_REDIS_OFFLOAD).

Without this, `asyncio.to_thread` / `run_in_executor(None, ...)` uses CPython's
lazily-created default pool, sized `min(32, os.cpu_count() + 4)`. That is:
  - host-dependent — on Railway's high-core shared host it balloons toward 32,
    on a small-core box it is ~6, too few for the ~18-way adapter fan-out, which
    then serialises inside a 15s wall-clock race;
  - unnamed — every worker thread is `ThreadPoolExecutor-N_M`, so a thread dump
    during an incident cannot tell adapter fetches from DB offload.

Installing an explicit, named, bounded pool makes the ceiling deterministic
across hosts and observable in a stack dump. Sizing (default 40): a single
compare fans out up to ~18 adapter fetches concurrently plus a handful of DB /
Redis offload calls; 40 leaves headroom for ~2 concurrent full fan-outs on the
single-worker uvicorn without unbounded thread growth. Override with
ADAPTER_EXECUTOR_MAX_WORKERS for load tuning.
"""
from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = 40


def default_executor_size() -> int:
    try:
        override = int(os.getenv("ADAPTER_EXECUTOR_MAX_WORKERS", "0"))
        if override > 0:
            return override
    except (TypeError, ValueError):
        pass
    return _DEFAULT_MAX_WORKERS


def install_default_executor(
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> ThreadPoolExecutor:
    """Set an explicitly-sized, named ThreadPoolExecutor as ``loop``'s default
    executor and return it. Call once at app startup on the running loop."""
    if loop is None:
        loop = asyncio.get_event_loop()
    size = default_executor_size()
    executor = ThreadPoolExecutor(
        max_workers=size,
        thread_name_prefix="qaren-worker",
    )
    loop.set_default_executor(executor)
    logger.info("[executor] default ThreadPoolExecutor installed: max_workers=%d", size)
    return executor

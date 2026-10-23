"""S77 REDIS-OFFLOOP - ENABLE_PRICE_PATH_REDIS_OFFLOOP: run the price-path Upstash
calls (the multi-MB ``shopify_catalog:<domain>`` GETs and their neighbours) off
the asyncio event loop.

``run_redis_offloop(fn, *args, durable=False)`` takes the callable from the
CALLER's own namespace (so a test patching ``price_service.get_cached`` still
intercepts both branches) and:

- flag OFF: calls ``fn(*args)`` inline with no ``await``, so an awaited dispatch
  runs to completion with no suspension point: the same calls, order, args and
  thread as a direct call. No pool is ever built while OFF.
- flag ON: runs ``fn(*args)`` as ONE job on a dedicated ``redis-offloop``
  ``ThreadPoolExecutor`` in a copied contextvars context. Writes pass
  ``durable=True``: they are ``asyncio.shield``ed, so a dispatched SET lands even
  when the awaiting coroutine is cancelled (as an inline SET would have). Reads
  are not shielded: a read still queued behind a full pool is dropped on cancel.

The pool is dedicated (not the loop's ``qaren-worker`` default executor) so a
stalled Upstash parks at most ``REDIS_OFFLOOP_MAX_WORKERS`` threads and never the
adapter fan-out's. Leaf module: stdlib imports only.

The flag is read PER CALL; ``REDIS_OFFLOOP_MAX_WORKERS`` (default 16, clamped
1..32) is read ONCE, when the pool is built, so a change needs a restart.

S81 ST1 (ENABLE_USAGE_PATH_OFFLOOP): ``usage_path_offloop_enabled()`` reads that
flag per call, and ``run_redis_offloop_pool(fn, *args, durable=False)`` runs ONE
job on the same shared pool whatever ENABLE_PRICE_PATH_REDIS_OFFLOOP says (the
caller reads its own flag first).
"""
from __future__ import annotations

import asyncio
import contextvars
import functools
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = 16
_MAX_WORKERS_CEILING = 32

_REDIS_OFFLOOP_POOL: Optional[ThreadPoolExecutor] = None
_REDIS_OFFLOOP_POOL_LOCK = threading.Lock()


def redis_offloop_enabled() -> bool:
    return os.getenv("ENABLE_PRICE_PATH_REDIS_OFFLOOP", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def redis_offloop_max_workers() -> int:
    """REDIS_OFFLOOP_MAX_WORKERS: int(value.strip()) clamped to 1..32. Unset, empty,
    unparsable and non-finite ('inf'/'nan' fail int()) fall back to 16."""
    raw = (os.getenv("REDIS_OFFLOOP_MAX_WORKERS") or "").strip()
    if not raw:
        return _DEFAULT_MAX_WORKERS
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_MAX_WORKERS
    return max(1, min(_MAX_WORKERS_CEILING, n))


def _get_redis_offloop_pool() -> ThreadPoolExecutor:
    global _REDIS_OFFLOOP_POOL
    pool = _REDIS_OFFLOOP_POOL
    if pool is None:
        with _REDIS_OFFLOOP_POOL_LOCK:
            pool = _REDIS_OFFLOOP_POOL
            if pool is None:
                workers = redis_offloop_max_workers()
                pool = ThreadPoolExecutor(
                    max_workers=workers, thread_name_prefix="redis-offloop",
                )
                _REDIS_OFFLOOP_POOL = pool
                logger.info("[REDIS-OFFLOOP] pool built workers=%d", workers)
    return pool


def redis_offloop_pool_stats() -> Optional[Dict[str, int]]:
    """A pure read of the pool: None until it is built (or on attribute drift)."""
    pool = _REDIS_OFFLOOP_POOL
    if pool is None:
        return None
    try:
        return {"workers": pool._max_workers, "queued": pool._work_queue.qsize()}
    except Exception:  # noqa: BLE001 - executor internals may drift
        return None


def _retrieve_quietly(fut: "asyncio.Future[Any]") -> None:
    """Retrieve a durable write's outcome so asyncio never logs "Future exception
    was never retrieved" when the awaiting coroutine was cancelled first."""
    if not fut.cancelled():
        fut.exception()


async def run_redis_offloop(fn: Callable[..., Any], *args: Any, durable: bool = False) -> Any:
    """Run ``fn(*args)``: inline when the flag is OFF, else one job on the
    ``redis-offloop`` pool (writes shielded when ``durable``)."""
    if not redis_offloop_enabled():
        return fn(*args)
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    fut = loop.run_in_executor(
        _get_redis_offloop_pool(), functools.partial(ctx.run, fn, *args),
    )
    if durable:
        fut.add_done_callback(_retrieve_quietly)
        return await asyncio.shield(fut)
    return await fut


def usage_path_offloop_enabled() -> bool:
    """S81 ST1 ENABLE_USAGE_PATH_OFFLOOP - read PER CALL (default OFF)."""
    return os.getenv("ENABLE_USAGE_PATH_OFFLOOP", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


async def run_redis_offloop_pool(fn: Callable[..., Any], *args: Any, durable: bool = False) -> Any:
    """S81 ST1: run ``fn(*args)`` as ONE job on the shared ``redis-offloop`` pool
    WHATEVER ENABLE_PRICE_PATH_REDIS_OFFLOOP says (the caller owns its gate).
    The mechanics of run_redis_offloop's ON branch: a copied contextvars
    context; ``durable=True`` shields the job (it lands even when the awaiting
    coroutine is cancelled) and quietly retrieves its outcome; a read still
    queued behind a full pool is dropped on cancel."""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    fut = loop.run_in_executor(
        _get_redis_offloop_pool(), functools.partial(ctx.run, fn, *args),
    )
    if durable:
        fut.add_done_callback(_retrieve_quietly)
        return await asyncio.shield(fut)
    return await fut

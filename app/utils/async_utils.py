"""Shared asyncio utilities — fire-and-forget with audit-friendly logging.

Bundle D Task 2.B.6 (R15) — promoted from `structured_comparison_service.py`
to a top-level utility so `app/api/*.py` can use the same exception-aware
fire-and-forget pattern without re-defining the helper per file.

Pattern history:
- audit 2026-05-22 M6 added the `_fire_and_forget` helper in
  `structured_comparison_service.py` after we discovered plain
  `asyncio.create_task()` was silently swallowing exceptions in the
  scoring/personalization writeback path (the audit trail
  `_update_behavior_profile` was failing without surfacing to Sentry).
- Bundle D 2.B.6 found 22 plain `asyncio.create_task(...)` sites in
  `app/api/*.py` with the same problem.

Use this helper for ANY fire-and-forget asyncio task: audit logs, search
logs, comparison saves, push delivery, behavior-profile updates. If you
genuinely don't care about exceptions, document the "skip" reason in
the call site comment.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable

logger = logging.getLogger(__name__)


def fire_and_forget(coro: Awaitable, label: str) -> asyncio.Task:
    """Create a fire-and-forget asyncio task with an exception-logging done
    callback.

    Without the done callback, exceptions raised inside the coroutine are
    silently swallowed — the audit trail (log_search, log_audit_event,
    save_comparison_and_track_cohort, etc.) just stops getting written
    and nothing surfaces to Sentry or logs.

    The done callback logs a WARNING with the task label so failure
    patterns are visible without crashing the request.

    Args:
        coro: an awaitable to run in the background
        label: short stable identifier for the WARNING log line — use the
            same label every call to the same logical site (e.g.
            "log_search.text" or "audit.login_success") so a grep on the
            Sentry/Railway logs aggregates failures cleanly.

    Returns:
        The created asyncio.Task. Returned for testability (tests can
        await it in fixtures); production callers can ignore the return
        value.
    """
    task = asyncio.create_task(coro)

    def _on_done(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        try:
            exc = t.exception()
        except Exception:  # noqa: BLE001 — callback must never raise
            return
        if exc is not None:
            logger.warning("fire-and-forget %s failed: %r", label, exc)

    task.add_done_callback(_on_done)
    return task

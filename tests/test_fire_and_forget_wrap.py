"""B0-B Item 4 regression — verify the `save_specs` and `save_price`
fire-and-forget DB writeback sites in `structured_comparison_service.py`
are wrapped in `_fire_and_forget` so a raise inside the coroutine
WARNING-logs via the done-callback instead of being silently swallowed.

Background (per CLAUDE.md Audit conventions 2026-05-22 + security audit
MED #2): plain `asyncio.create_task(save_specs(...))` had two sites that
bypassed the done-callback and lost the audit trail. The fix wraps them
in `_fire_and_forget(coro, label="save_specs"|"save_price")`.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import pytest


# ----------------------------------------------------------------------------
# Static guard — neither old `asyncio.create_task(save_specs|save_price(...))`
# call shape can come back without a new audit.
# ----------------------------------------------------------------------------


def test_no_plain_asyncio_create_task_around_save_specs_or_save_price():
    """Future revert protection — if either call site is rewritten back to
    `asyncio.create_task(save_specs(...))` / `(save_price(...))`, the audit
    trail goes silent again. Fail loud if either reappears.
    """
    src = (
        Path(__file__).parent.parent
        / "app" / "services" / "structured_comparison_service.py"
    ).read_text(encoding="utf-8")
    # Strip comments so a docstring reference doesn't accidentally trip the
    # guard.
    code_only = "\n".join(
        line for line in src.splitlines()
        if not line.strip().startswith("#")
    )
    assert not re.search(r"asyncio\.create_task\(\s*save_specs\b", code_only), (
        "asyncio.create_task(save_specs(...)) re-appeared in "
        "structured_comparison_service.py — wrap it in _fire_and_forget("
        "..., label='save_specs') per audit convention 2026-05-22."
    )
    assert not re.search(r"asyncio\.create_task\(\s*save_price\b", code_only), (
        "asyncio.create_task(save_price(...)) re-appeared in "
        "structured_comparison_service.py — wrap it in _fire_and_forget("
        "..., label='save_price') per audit convention 2026-05-22."
    )


# ----------------------------------------------------------------------------
# Behavioral test — the wrapper's done-callback WARNING-logs on exception.
# Uses the shared `fire_and_forget` from app.utils.async_utils that the
# local `_fire_and_forget` delegates to.
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fire_and_forget_logs_warning_on_save_specs_raise(caplog):
    """Drop a `save_specs` coroutine that raises; expect the wrapper to
    surface the exception as a WARNING tagged with the `save_specs` label.
    """
    from app.services import structured_comparison_service as scs

    async def _raising_save_specs():
        raise RuntimeError("simulated DB write failure")

    with caplog.at_level(logging.WARNING, logger="app.utils.async_utils"):
        # Use the same in-module wrapper the production sites call.
        scs._fire_and_forget(_raising_save_specs(), label="save_specs")
        # Let the event loop drain the task + its done-callback.
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    matches = [
        r for r in caplog.records
        if "save_specs" in r.getMessage()
        and "simulated DB write failure" in r.getMessage()
        and r.levelno == logging.WARNING
    ]
    assert matches, (
        "Expected a WARNING log mentioning save_specs + the simulated "
        f"failure. Got: {[r.getMessage() for r in caplog.records]}"
    )


@pytest.mark.asyncio
async def test_fire_and_forget_logs_warning_on_save_price_raise(caplog):
    """Same as above but for save_price — confirms the second wrapped site
    uses the correct label string."""
    from app.services import structured_comparison_service as scs

    async def _raising_save_price():
        raise RuntimeError("simulated price write failure")

    with caplog.at_level(logging.WARNING, logger="app.utils.async_utils"):
        scs._fire_and_forget(_raising_save_price(), label="save_price")
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    matches = [
        r for r in caplog.records
        if "save_price" in r.getMessage()
        and "simulated price write failure" in r.getMessage()
        and r.levelno == logging.WARNING
    ]
    assert matches, (
        "Expected a WARNING log mentioning save_price + the simulated "
        f"failure. Got: {[r.getMessage() for r in caplog.records]}"
    )

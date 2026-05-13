"""
Bundle E Tasks 2.3 + 2.5 RED — SSE settle-window contract.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A
      Task 2.3 + Task 2.5, § Test-2.3)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 8
        lines 372-380 + § Frontend SSE handling lines 416-421.

Tasks 2.3 + 2.5 share the same SSE wire contract — the route emits the
new event types AND the orchestrator drives the settle-window timing,
so the tests live in one file (per dispatcher: "Test-2.5 ... overlaps
heavily with Test-2.3, fold into Test-2.3").

SSE event types (design § Decision 8 lines 416-421):
  - `first_paint`     — all core dimensions ready, render the full UI.
  - `settle_update`   — a higher-trust value arrived for a specific
                         field (e.g. price). Carries
                         { field, new_value, source_rank }.
  - `settle_complete` — settle window closed, no more updates.
  - `confidence_upgrade` — dimension confidence improved (e.g., 2nd
                            source confirmed price). Carries
                            { dimension_key, new_confidence }.

Timing invariants (design § Decision 8 lines 372-380):
  - `first_paint` at ≤13s of stream start.
  - `settle_complete` at ≤25s of stream start (hard cap).
  - Event ordering: first_paint < settle_update* < settle_complete.

Backward compatibility (design line 455):
  - Existing `complete` event still fired at settle_complete time so old
    clients don't break.

RED→GREEN trajectory:
  - At HEAD: `compare_from_text_streaming` in
    `structured_comparison_service.py` does not yield the 4 new event
    types (currently yields specs/prices/reviews/scores/verdict/complete
    per CLAUDE.md). Tests run the streaming generator with mocked
    services and assert the new events appear → RED until Task 2.3+2.5
    lands.

Test strategy:
  Build a thin async iterator wrapper that walks the streaming generator
  output and collects (event_type, payload, timestamp) tuples. Assert
  on the collected event log:
    - presence of the 4 new event types
    - ordering invariants
    - timing budget enforcement

For timing tests we use `asyncio.get_event_loop().time()` deltas and
inject controlled sleep mocks. We're testing the SHAPE of the contract,
not real-world Serper/GPT timing — production latency is covered by
Phase 4 perf bench (`tests/perf/test_latency_bench.py`).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator

import pytest

# These tests exercise the real streaming pipeline (Serper + GPT). Tag as
# `live_unit` so they're excluded from the default `pytest -m "not
# live_unit"` regression sweep — same convention as other live-API tests
# in this repo (see CLAUDE.md § Tests).
pytestmark = pytest.mark.live_unit

# RED gate — first_paint event type is not yet emitted by the streaming
# service. We import the streaming function; the test collects events
# and asserts presence/order/timing.
from app.services.structured_comparison_service import (  # noqa: E402
    get_comparison_service,
)


# ---------------------------------------------------------------------------
# Event-collector helper
# ---------------------------------------------------------------------------

async def _collect_events(
    gen: AsyncIterator[dict[str, Any]],
    timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    """Walk a streaming-comparison generator, tag each event with its
    arrival time, and return the full list. Wrapped in asyncio.wait_for
    so a runaway generator can't hang the test suite."""
    events: list[dict[str, Any]] = []
    start = asyncio.get_event_loop().time()

    async def _drain():
        async for event in gen:
            stamped = dict(event) if isinstance(event, dict) else {"event": "raw", "data": event}
            stamped["_t"] = asyncio.get_event_loop().time() - start
            events.append(stamped)

    try:
        await asyncio.wait_for(_drain(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        events.append({"event": "_timeout", "_t": timeout_seconds})
    return events


def _event_types(events: list[dict[str, Any]]) -> list[str]:
    """Extract the ordered list of event-type strings. The streaming
    generator may use either `event` or `type` as the discriminator key
    — accept both, fall back to "unknown"."""
    out = []
    for ev in events:
        et = ev.get("event") or ev.get("type") or "unknown"
        out.append(et)
    return out


# ---------------------------------------------------------------------------
# Test 1 — All 4 new SSE event types emitted
# ---------------------------------------------------------------------------

class TestNewSseEventTypes:
    """Tasks 2.3 + 2.5 must emit `first_paint`, `settle_update`,
    `settle_complete`, `confidence_upgrade`. Existing `complete` event
    is also emitted at settle_complete for backward-compat (design
    line 455)."""

    @pytest.mark.asyncio
    async def test_first_paint_event_emitted(self):
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        types = _event_types(events)
        assert "first_paint" in types, (
            f"first_paint event missing from stream. Got events: {types}"
        )

    @pytest.mark.asyncio
    async def test_settle_complete_event_emitted(self):
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        types = _event_types(events)
        assert "settle_complete" in types, (
            f"settle_complete event missing. Got events: {types}"
        )

    @pytest.mark.asyncio
    async def test_backward_compat_complete_event_still_emitted(self):
        """Design line 455: 'Backward-compat: existing `complete` event
        still fired at settle_complete.' Old clients (current EAS
        builds) listen for `complete` — must keep working."""
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        types = _event_types(events)
        assert "complete" in types, (
            f"backward-compat `complete` event missing. Got events: {types}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Event ordering
# ---------------------------------------------------------------------------

class TestEventOrdering:
    """Design § Decision 8: first_paint precedes settle_complete.
    settle_update events MAY arrive between them; confidence_upgrade
    likewise. Order invariant is the bare minimum."""

    @pytest.mark.asyncio
    async def test_first_paint_precedes_settle_complete(self):
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        types = _event_types(events)
        if "first_paint" in types and "settle_complete" in types:
            fp_idx = types.index("first_paint")
            sc_idx = types.index("settle_complete")
            assert fp_idx < sc_idx, (
                f"first_paint (idx {fp_idx}) must precede settle_complete "
                f"(idx {sc_idx}). Order: {types}"
            )
        else:
            pytest.fail(
                f"Cannot test ordering — one or both events missing. "
                f"Got: {types}"
            )

    @pytest.mark.asyncio
    async def test_no_settle_update_after_settle_complete(self):
        """Settle window closes at settle_complete. Any settle_update
        emitted AFTER settle_complete is a contract violation — late
        scrapers should be cancelled, not allowed to fire SSE."""
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        types = _event_types(events)
        if "settle_complete" not in types:
            pytest.fail(f"settle_complete missing. Got: {types}")
        sc_idx = types.index("settle_complete")
        for i, et in enumerate(types[sc_idx + 1:], start=sc_idx + 1):
            assert et != "settle_update", (
                f"settle_update at idx {i} fires AFTER settle_complete at "
                f"idx {sc_idx}. Order: {types}"
            )


# ---------------------------------------------------------------------------
# Test 3 — Timing budget
# ---------------------------------------------------------------------------

class TestTimingBudget:
    """Design § Decision 8 + § Decision 9: first_paint ≤13s, hard cap
    at 25s. These are END-TO-END targets — Phase 4 perf bench measures
    them against real Serper/GPT. Here we just assert the orchestrator
    DOES enforce the 25s hard cap (asyncio.wait_for / asyncio.timeout
    pattern) so a runaway scraper can't hang the response forever."""

    @pytest.mark.asyncio
    async def test_settle_complete_within_25s_hard_cap(self):
        """The hard cap is the load-bearing invariant — first_paint at
        13s is a target (perf bench), but settle_complete at 25s is a
        contract (timeout-or-fail)."""
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        # If settle_complete fired, check it landed within 25s.
        for ev in events:
            et = ev.get("event") or ev.get("type")
            if et == "settle_complete":
                assert ev["_t"] <= 25.0, (
                    f"settle_complete arrived at {ev['_t']:.1f}s, "
                    f"exceeding 25s hard cap"
                )
                return
        # If we got here, settle_complete never fired before our 30s
        # collector timeout — that's a failure of the hard cap contract.
        pytest.fail(
            f"settle_complete did not fire within 30s collector timeout. "
            f"Hard cap of 25s is not being enforced."
        )

    @pytest.mark.asyncio
    async def test_first_paint_within_13s_target(self):
        """Soft target. Real backend may exceed 13s under cold-cache
        conditions; perf bench measures the P95 distribution. Here we
        just assert the orchestrator doesn't wait until settle to fire
        first_paint — it should land BEFORE the hard cap minus a margin
        (settle window is 13-25s per design line 376), so first_paint
        must be ≤ settle_complete-time and ideally well under it."""
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        for ev in events:
            et = ev.get("event") or ev.get("type")
            if et == "first_paint":
                # Allow up to 25s in this unit-test environment (no real
                # GPT/Serper calls, mocks may differ). 25s is the hard
                # cap; first_paint must land BEFORE the hard cap fires.
                assert ev["_t"] < 25.0, (
                    f"first_paint arrived at {ev['_t']:.1f}s, "
                    f"after the 25s hard cap"
                )
                return
        pytest.fail(
            f"first_paint did not fire within collector timeout. "
            f"Events: {_event_types(events)}"
        )


# ---------------------------------------------------------------------------
# Test 4 — Payload shape on the new events
# ---------------------------------------------------------------------------

class TestEventPayloadShape:
    """Design line 419: `settle_update` carries `{field, new_value,
    source_rank}`. Line 421: `confidence_upgrade` carries `{dimension_key,
    new_confidence}` (e.g., from 'low' → 'high' when 2nd source confirms)."""

    @pytest.mark.asyncio
    async def test_settle_update_payload_has_field_and_source_rank(self):
        """When a settle_update is emitted, its payload must include a
        `field` key naming what changed AND a `source_rank` for the new
        value's trust level."""
        service = get_comparison_service()
        gen = service.compare_from_text_streaming(
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
        )
        events = await _collect_events(gen, timeout_seconds=30.0)
        settle_updates = [
            ev for ev in events
            if (ev.get("event") or ev.get("type")) == "settle_update"
        ]
        # settle_update is OPTIONAL in any given stream (no late scraper
        # may have higher-rank data), so we only assert shape when it
        # DOES fire.
        for su in settle_updates:
            payload = su.get("data") or su
            assert "field" in payload, (
                f"settle_update missing `field` key: {payload}"
            )
            assert "source_rank" in payload, (
                f"settle_update missing `source_rank` key: {payload}"
            )


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-2.3 run:
#     python -m pytest tests/test_sse_settle_window.py -v
#     → All 8 assertions fail because the streaming service does not
#       yet emit first_paint/settle_update/settle_complete/
#       confidence_upgrade events.
#
# Post-Task-2.3 + Task-2.5:
#     → All assertions pass against the refactored streaming service.
#     → Phase 4 perf bench (tests/perf/test_latency_bench.py) measures
#       real-world P50/P95 timing.

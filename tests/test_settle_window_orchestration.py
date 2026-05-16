"""Bundle E Task 2.3 — settle-window orchestration in compare_from_text_streaming.

Verifies the scatter-gather integration:
- Hard 25s outer timeout (asyncio.wait_for / asyncio.timeout) wraps the
  data-fetch + scoring + verdict pipeline. Tested by injecting a scraper
  that sleeps past 25s and asserting the stream still terminates with a
  `settle_complete` (or `error`) event within 30s.
- `settle_update` carries `{field, new_value, source_rank}` per design
  § Decision 8 lines 416-421.
- `confidence_upgrade` carries `{dimension_key, new_confidence}`.
- Both new event types are tagged as live_unit-free — they exercise the
  orchestrator's emission code path, not real Serper/GPT.

These tests run in the default `not live_unit` regression sweep because
they patch every external service call to keep the stream synthetic.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _event_type(event):
    if isinstance(event, dict):
        return event.get("event") or event.get("type")
    if isinstance(event, tuple) and len(event) >= 1:
        return event[0]
    return None


def _event_payload(event):
    if isinstance(event, dict):
        return event.get("data") or event
    if isinstance(event, tuple) and len(event) >= 2:
        return event[1]
    return {}


async def _collect_events(gen: AsyncIterator[Any], timeout: float = 30.0) -> list:
    events: list = []

    async def _drain():
        async for ev in gen:
            events.append(ev)

    try:
        await asyncio.wait_for(_drain(), timeout=timeout)
    except asyncio.TimeoutError:
        events.append(("_collector_timeout", {"_timeout": timeout}))
    return events


class TestHardCapEnforcement:
    """compare_from_text_streaming must terminate within ~25s even when a
    downstream call would otherwise hang. The orchestrator wraps the main
    data-fetch in asyncio.wait_for(timeout=25) so a slow scraper can't
    indefinitely block the SSE stream."""

    @pytest.mark.asyncio
    async def test_streaming_terminates_within_30s_when_fetch_hangs(self):
        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()

        async def _hang_forever(*args, **kwargs):
            await asyncio.sleep(60)  # would exceed any reasonable cap
            return {"brand": "X", "name": "Y"}

        with patch.object(service, "_fetch_product_data", new=_hang_forever), \
             patch("app.services.structured_comparison_service.parse_product_query",
                   new_callable=AsyncMock,
                   return_value=({"products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}], "comparison_type": "value"}, {})):
            gen = service.compare_from_text_streaming(query="A vs B")
            events = await _collect_events(gen, timeout=30.0)

        # Must terminate (either error or settle_complete) before our 30s collector kills it.
        types = [_event_type(e) for e in events]
        assert "_collector_timeout" not in types, (
            f"compare_from_text_streaming hung past 30s — hard cap not enforced. "
            f"Events: {types}"
        )


class TestSettleUpdatePayloadShape:
    """When settle_update fires, its payload must include `field`,
    `new_value`, and `source_rank` per design lines 416-421."""

    def test_helper_emit_settle_update_returns_correct_shape(self):
        """Direct unit test of the helper that builds settle_update payloads,
        independent of the streaming orchestrator."""
        from app.services.structured_comparison_service import (
            build_settle_update_event,
        )

        ev = build_settle_update_event(
            field="products[0].price",
            new_value={"amount": 99.0, "currency": "BHD"},
            source_rank=90,
        )
        # The helper returns a tuple (event_type, payload) following the
        # generator's existing yield contract.
        assert ev[0] == "settle_update"
        payload = ev[1]
        assert payload["field"] == "products[0].price"
        assert payload["new_value"] == {"amount": 99.0, "currency": "BHD"}
        assert payload["source_rank"] == 90


class TestConfidenceUpgradePayloadShape:
    def test_helper_emit_confidence_upgrade_returns_correct_shape(self):
        from app.services.structured_comparison_service import (
            build_confidence_upgrade_event,
        )

        ev = build_confidence_upgrade_event(
            dimension_key="price",
            new_confidence="high",
        )
        assert ev[0] == "confidence_upgrade"
        payload = ev[1]
        assert payload["dimension_key"] == "price"
        assert payload["new_confidence"] == "high"

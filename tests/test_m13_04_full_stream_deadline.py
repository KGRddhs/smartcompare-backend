"""M13-04 pin — ENABLE_FULL_STREAM_DEADLINE bounds the post-Phase-1 verdict tail.

Failure scenario: STREAM_HARD_CAP_SECONDS wraps ONLY Phase 1 (the two
_fetch_product_data calls); the verdict/critique/moderation tail runs UNBOUNDED, so
a slow GPT verdict keeps the SSE connection alive ~150s until the client's 120s
axios timeout with no error event. Flag ON: the verdict await is bounded by the
residual budget and a best-available PARTIAL is yielded on expiry. Flag OFF: the
tail stays unbounded (today).

All network is mocked; the verdict stage hangs deterministically.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.structured_comparison_service as scs


def _event_type(ev):
    return ev[0] if isinstance(ev, tuple) and ev else None


async def _collect(gen, timeout):
    events = []

    async def _drain():
        async for ev in gen:
            events.append(ev)

    try:
        await asyncio.wait_for(_drain(), timeout=timeout)
    except asyncio.TimeoutError:
        events.append(("_collector_timeout", {}))
    return events


def _mock_to_verdict(monkeypatch, service):
    """Drive compare_from_text_streaming to the verdict stage with valid Phase-1
    data + a synthetic scoring layer, so the only thing left is the verdict."""
    monkeypatch.setattr(
        scs, "parse_product_query",
        AsyncMock(return_value=(
            {"products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
             "comparison_type": "value"},
            {},
        )),
    )

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache, partial_slot=0, **kw):
        return {
            "brand": product.get("brand", "X"),
            "name": product.get("name", "Y"),
            "specs": {"k": "v"},
            "price": {"amount": 10.0, "currency": "BHD", "estimated": False},
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }
    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)

    scoring = MagicMock()
    scoring.compute_scores.return_value = {
        "scores": {"product_0": {"breakdown": {"value_score": 60}},
                   "product_1": {"breakdown": {"value_score": 50}}},
        "winner_index": 0, "win_margin": 5, "dimension_winners": {}, "price_tiers": {},
    }
    scoring.build_scores_summary.return_value = ""
    scoring.compute_confidence.return_value = 0.5
    scoring.compute_value_badge.return_value = ""
    scoring.compute_tradeoff_pairs.return_value = []
    monkeypatch.setattr(scs, "get_scoring_service", lambda: scoring)
    monkeypatch.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)


@pytest.mark.asyncio
async def test_hung_verdict_terminates_with_partial_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_FULL_STREAM_DEADLINE", "true")
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.5, raising=False)

    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)

    async def _hang_verdict(*a, **k):
        await asyncio.sleep(60)
        return ({}, {})
    monkeypatch.setattr(scs, "generate_comparison", _hang_verdict)

    gen = service.compare_from_text_streaming(query="A vs B")
    events = await _collect(gen, timeout=6.0)
    types = [_event_type(e) for e in events]

    assert "_collector_timeout" not in types, (
        f"flag ON: the hung verdict was NOT bounded — stream hung. Events: {types}"
    )
    # It reached the verdict stage (status 80) and then terminated with the
    # settle_complete/complete PARTIAL rather than a real verdict.
    assert "settle_complete" in types and "complete" in types
    assert "verdict" not in types, "the verdict hung; no real verdict event should fire"


@pytest.mark.asyncio
async def test_hung_verdict_is_unbounded_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_FULL_STREAM_DEADLINE", raising=False)
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.5, raising=False)

    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)

    async def _hang_verdict(*a, **k):
        await asyncio.sleep(60)
        return ({}, {})
    monkeypatch.setattr(scs, "generate_comparison", _hang_verdict)

    gen = service.compare_from_text_streaming(query="A vs B")
    events = await _collect(gen, timeout=2.5)
    types = [_event_type(e) for e in events]

    # Flag OFF: the tail is unbounded, so the collector's own timeout is what stops it.
    assert "_collector_timeout" in types, (
        f"flag OFF must leave the tail unbounded (today's behaviour). Events: {types}"
    )

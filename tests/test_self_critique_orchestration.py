"""S2 I3.1/I3.3 — orchestrator wiring of the self-critique pass.

Pins StructuredComparisonService._apply_self_critique:
  - ENABLE_SELF_CRITIQUE OFF (prod default) → complete no-op: original
    verdict, zero cost, zero gpt_calls, no _verdict_critique metadata.
  - ON + high scores → critique cost tracked, no regen, metadata threaded.
  - ON + low score → ONE regeneration fires (its cost also tracked), the
    regenerated verdict is returned, metadata.regenerated=True.
  - critique_ms stage-timing recorded when stage_timings is provided.

All OpenAI calls mocked — no live API.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.structured_comparison_service import StructuredComparisonService


_ORIGINAL = {"winner_index": 0, "winner_declaration": "A", "winner_reason": "x"}
_REGEN = {"winner_index": 0, "winner_declaration": "A", "winner_reason": "regenerated"}
_NAMES = ["Brand A Phone", "Brand B Phone"]


def _regen_args():
    return dict(
        product1={"name": "A"}, product2={"name": "B"}, region="bahrain",
        concern="value", user_preferences=None, scores_summary="A leads on price.",
        category="electronics", demographics_profile=None,
    )


def _critique_payload(low: bool = False):
    return {
        "bias_score": 9, "vagueness_score": 4 if low else 9, "hedging_score": 9,
        "missing_citation_score": 9, "pain_workflow_align_score": 9,
    }


def _mock_critique_response(payload):
    msg = MagicMock(); msg.content = json.dumps(payload)
    choice = MagicMock(); choice.message = msg
    resp = MagicMock(); resp.choices = [choice]
    usage = MagicMock(); usage.prompt_tokens = 900; usage.completion_tokens = 50
    resp.usage = usage
    return resp


@pytest.mark.asyncio
async def test_off_default_is_noop(monkeypatch):
    monkeypatch.delenv("ENABLE_SELF_CRITIQUE", raising=False)
    svc = StructuredComparisonService()
    cost_before, calls_before = svc.total_cost, svc.gpt_calls

    out = await svc._apply_self_critique(
        comparison=_ORIGINAL, product_names=_NAMES, regen_args=_regen_args(),
    )
    assert out is _ORIGINAL
    assert svc.total_cost == cost_before
    assert svc.gpt_calls == calls_before  # ZERO API calls when OFF
    assert svc._verdict_critique_metadata() is None


@pytest.mark.asyncio
async def test_on_high_scores_tracks_cost_no_regen(monkeypatch):
    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
    svc = StructuredComparisonService()

    from app.services import verdict_critique_service as vcs
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_mock_critique_response(_critique_payload(low=False)))

    with patch.object(vcs, "get_client", return_value=client):
        out = await svc._apply_self_critique(
            comparison=_ORIGINAL, product_names=_NAMES, regen_args=_regen_args(),
        )
    assert out is _ORIGINAL  # high scores → not regenerated
    assert svc.gpt_calls == 1  # the critique call was tracked
    assert svc.total_cost > 0
    meta = svc._verdict_critique_metadata()
    assert meta is not None
    assert meta["regenerated"] is False
    assert meta["needs_regen"] is False


@pytest.mark.asyncio
async def test_on_low_score_regenerates_once_and_tracks_both(monkeypatch):
    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
    svc = StructuredComparisonService()

    from app.services import verdict_critique_service as vcs
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_mock_critique_response(_critique_payload(low=True)))

    # The regen closure calls generate_comparison — mock it to return _REGEN.
    async def _fake_generate(*args, **kwargs):
        return _REGEN, {"prompt_tokens": 1500, "completion_tokens": 200}

    with patch.object(vcs, "get_client", return_value=client):
        with patch(
            "app.services.structured_comparison_service.generate_comparison",
            new=_fake_generate,
        ):
            out = await svc._apply_self_critique(
                comparison=_ORIGINAL, product_names=_NAMES, regen_args=_regen_args(),
            )
    assert out is _REGEN  # regenerated verdict shipped
    # Both the critique call AND the regeneration call tracked.
    assert svc.gpt_calls == 2
    meta = svc._verdict_critique_metadata()
    assert meta["regenerated"] is True
    assert meta["needs_regen"] is True
    assert "vagueness_score" in meta["low_axes"]


@pytest.mark.asyncio
async def test_critique_ms_recorded_in_stage_timings(monkeypatch):
    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
    svc = StructuredComparisonService()
    stage_timings: dict = {}

    from app.services import verdict_critique_service as vcs
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_mock_critique_response(_critique_payload(low=False)))

    with patch.object(vcs, "get_client", return_value=client):
        await svc._apply_self_critique(
            comparison=_ORIGINAL, product_names=_NAMES, regen_args=_regen_args(),
            stage_timings=stage_timings,
        )
    assert "critique_ms" in stage_timings
    assert isinstance(stage_timings["critique_ms"], (int, float))


@pytest.mark.asyncio
async def test_critique_failure_serves_original_no_crash(monkeypatch):
    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
    svc = StructuredComparisonService()

    from app.services import verdict_critique_service as vcs
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=RuntimeError("openai down"))

    with patch.object(vcs, "get_client", return_value=client):
        out = await svc._apply_self_critique(
            comparison=_ORIGINAL, product_names=_NAMES, regen_args=_regen_args(),
        )
    assert out is _ORIGINAL
    assert svc._verdict_critique_metadata() is None  # no critique recorded


@pytest.mark.asyncio
async def test_cost_within_002_gate(monkeypatch):
    """I3.3 gate — a single critique call (gpt-4o-mini, ~900+50 tok) costs
    well under the $0.002/comparison budget."""
    monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
    svc = StructuredComparisonService()

    from app.services import verdict_critique_service as vcs
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_mock_critique_response(_critique_payload(low=False)))

    with patch.object(vcs, "get_client", return_value=client):
        await svc._apply_self_critique(
            comparison=_ORIGINAL, product_names=_NAMES, regen_args=_regen_args(),
        )
    # 900*0.15/1e6 + 50*0.60/1e6 = 0.000135 + 0.00003 = 0.000165 — far under $0.002.
    assert svc.total_cost < 0.002, f"critique cost {svc.total_cost} exceeds $0.002 gate"

"""S2 I3.1 — verdict self-critique service (B.3).

A gpt-4o-mini pass scores the shipped verdict on 5 axes (0..10):
  bias / vagueness / hedging / missing_citation / pain_workflow_align.
Any axis < 7 → the caller triggers exactly ONE regeneration (hard cap,
enforced caller-side). The service itself just SCORES + flags.

Hard rules under test:
  - ENABLE_SELF_CRITIQUE default OFF in code (is_self_critique_enabled()).
  - Critique failure (API error, malformed JSON) → returns None so the
    caller serves the ORIGINAL verdict; NEVER raises.
  - needs_regen True iff any of the 5 axes < CRITIQUE_THRESHOLD (7).
  - Axis scores clamped to 0..10 (matches migration 030 CHECK).
  - usage dict carries prompt/completion tokens for cost tracking (I3.3).

All tests mock the OpenAI client — no live API, no cost.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import verdict_critique_service as vcs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VERDICT = {
    "winner_index": 0,
    "winner_declaration": "iPhone 15",
    "winner_reason": "20% better low-light camera at a 30 BHD premium.",
    "key_tradeoff": "Galaxy S24 wins on charging speed (45W vs 20W).",
    "value_context": {
        "product_0": "Holds resale value well for the GCC market.",
        "product_1": "More accessible entry price in Bahrain.",
    },
    "best_for": {
        "product_0": "Buyers locked into the Apple ecosystem.",
        "product_1": "Android users who want fast charging.",
    },
    "product_0_pros": ["48MP camera", "Strong resale", "iOS updates 5yr", "Premium build"],
    "product_0_cons": ["Higher price", "Slower charging"],
    "product_1_pros": ["45W charging", "Lower price", "120Hz AMOLED", "Bigger battery"],
    "product_1_cons": ["Weaker resale", "Bloatware"],
}

_PRODUCT_NAMES = ["Apple iPhone 15", "Samsung Galaxy S24"]


def _mock_openai_response(payload: dict, *, prompt_tokens=900, completion_tokens=60):
    """Build a fake OpenAI chat-completion response object."""
    msg = MagicMock()
    msg.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = prompt_tokens + completion_tokens
    resp.usage = usage
    return resp


def _patch_client(response_or_exc):
    """Patch verdict_critique_service.get_client to return a client whose
    chat.completions.create yields `response_or_exc` (or raises if it's an
    Exception)."""
    client = MagicMock()
    if isinstance(response_or_exc, Exception):
        client.chat.completions.create = AsyncMock(side_effect=response_or_exc)
    else:
        client.chat.completions.create = AsyncMock(return_value=response_or_exc)
    return patch.object(vcs, "get_client", return_value=client)


# ---------------------------------------------------------------------------
# Flag default
# ---------------------------------------------------------------------------

class TestFlagDefault:

    def test_self_critique_default_off(self, monkeypatch):
        monkeypatch.delenv("ENABLE_SELF_CRITIQUE", raising=False)
        assert vcs.is_self_critique_enabled() is False

    def test_self_critique_on_when_env_true(self, monkeypatch):
        monkeypatch.setenv("ENABLE_SELF_CRITIQUE", "true")
        assert vcs.is_self_critique_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "", "off"])
    def test_self_critique_off_for_falsey_values(self, monkeypatch, val):
        monkeypatch.setenv("ENABLE_SELF_CRITIQUE", val)
        assert vcs.is_self_critique_enabled() is False


# ---------------------------------------------------------------------------
# Critique scoring
# ---------------------------------------------------------------------------

class TestCritiqueScoring:

    @pytest.mark.asyncio
    async def test_all_high_scores_no_regen(self):
        payload = {
            "bias_score": 9, "vagueness_score": 8, "hedging_score": 9,
            "missing_citation_score": 8, "pain_workflow_align_score": 9,
        }
        with _patch_client(_mock_openai_response(payload)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result is not None
        assert result.needs_regen is False
        assert result.low_axes == []
        assert result.axis_scores["bias_score"] == 9

    @pytest.mark.asyncio
    async def test_one_low_axis_triggers_regen(self):
        payload = {
            "bias_score": 9, "vagueness_score": 4, "hedging_score": 9,
            "missing_citation_score": 8, "pain_workflow_align_score": 9,
        }
        with _patch_client(_mock_openai_response(payload)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result is not None
        assert result.needs_regen is True
        assert "vagueness_score" in result.low_axes
        assert result.regen_reason  # non-empty explanation for the DB row

    @pytest.mark.asyncio
    async def test_threshold_boundary_seven_does_not_regen(self):
        """Exactly 7 is acceptable (axis < 7 is the trigger, not <= 7)."""
        payload = {
            "bias_score": 7, "vagueness_score": 7, "hedging_score": 7,
            "missing_citation_score": 7, "pain_workflow_align_score": 7,
        }
        with _patch_client(_mock_openai_response(payload)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result.needs_regen is False

    @pytest.mark.asyncio
    async def test_six_is_below_threshold(self):
        payload = {
            "bias_score": 6, "vagueness_score": 8, "hedging_score": 8,
            "missing_citation_score": 8, "pain_workflow_align_score": 8,
        }
        with _patch_client(_mock_openai_response(payload)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result.needs_regen is True
        assert result.low_axes == ["bias_score"]

    @pytest.mark.asyncio
    async def test_scores_clamped_to_0_10(self):
        """Out-of-range model output is clamped to the migration-030 range."""
        payload = {
            "bias_score": 15, "vagueness_score": -3, "hedging_score": 8,
            "missing_citation_score": 8, "pain_workflow_align_score": 8,
        }
        with _patch_client(_mock_openai_response(payload)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result.axis_scores["bias_score"] == 10
        assert result.axis_scores["vagueness_score"] == 0

    @pytest.mark.asyncio
    async def test_usage_tokens_surfaced_for_cost_tracking(self):
        payload = {
            "bias_score": 9, "vagueness_score": 9, "hedging_score": 9,
            "missing_citation_score": 9, "pain_workflow_align_score": 9,
        }
        with _patch_client(_mock_openai_response(payload, prompt_tokens=1000, completion_tokens=50)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result.usage["prompt_tokens"] == 1000
        assert result.usage["completion_tokens"] == 50
        assert result.critic_model  # records which model scored


# ---------------------------------------------------------------------------
# Failure modes — NEVER raise, return None
# ---------------------------------------------------------------------------

class TestFailureServesOriginal:

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        with _patch_client(RuntimeError("openai 500")):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_json_returns_none(self):
        bad = MagicMock()
        bad.content = "not json at all {{{"
        choice = MagicMock(); choice.message = bad
        resp = MagicMock(); resp.choices = [choice]; resp.usage = None
        with _patch_client(resp):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_axis_keys_returns_none(self):
        """A response missing required axes can't be scored → None (serve
        original), never a partial/guessed critique."""
        payload = {"bias_score": 9}  # 4 axes absent
        with _patch_client(_mock_openai_response(payload)):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_content_returns_none(self):
        empty = MagicMock(); empty.content = None
        choice = MagicMock(); choice.message = empty
        resp = MagicMock(); resp.choices = [choice]; resp.usage = None
        with _patch_client(resp):
            result = await vcs.critique_verdict(
                comparison=_VERDICT, product_names=_PRODUCT_NAMES,
            )
        assert result is None

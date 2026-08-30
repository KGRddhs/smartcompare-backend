"""UNIT D1 — the spec-refill cascade under ENABLE_SPECS_NO_FABRICATION.

UNIT A3 (``tests/test_specs_no_fabrication_guard.py``) closed fabrication at
``extraction_service.extract_specs``: with the flag ON a schema field survives
only when the model cited a snippet for it, an unsupported field is DROPPED
rather than stamped ``"N/A"``, and the dict carries the internal
``_evidence_limited`` marker.

A3 documented its own scope boundary: the DOWNSTREAM refill cascade in
``structured_comparison_service`` — smart-fallback, Tier 2, Tier 3 — tests
``not specs_so_far.get(f) or specs_so_far.get(f) in ("N/A", "")``, which is
TRUE for an omitted field and for an "N/A" field alike. So each of the three
tiers saw A3's principled omission as a gap and refilled it through its own
UNGATED LLM call. Tier 3 is the sharpest case: ``extract_specs_synthesized``
takes NO snippet context at all — it is pure training-data synthesis, which is
exactly what the flag forbids.

These tests pin the closure at EACH cascade site:
  * flag ON  — the refill is SKIPPED, and zero completions are issued.
  * flag OFF — byte-identical to main: the refill fires, and the two refill
    prompts still carry their exact current wording (the pins in
    ``TestRefillPromptsUnchanged`` fail loudly if anyone forks a third prompt
    instead of gating the call site).
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.structured_comparison_service import (
    StructuredComparisonService,
    get_comparison_service,
    tier2_fill_non_negotiables,
    tier3_synthesize_non_negotiables,
)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SPECS_NO_FABRICATION", raising=False)
    return None


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "true")
    return None


class _Spy:
    """Async callable that records calls and returns a canned payload."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.payload


async def _fake_search(*args, **kwargs):
    return {"organic": [{"title": "t", "snippet": "Galaxy S25 Ultra battery 5000 mAh"}]}


# Electronics non-negotiables (battery / processor / ram / rear_camera) — the
# same set the existing Tier 2 / Tier 3 suites drive.
_ELECTRONICS_GAP = {"processor": "A17 Pro"}


# ---------------------------------------------------------------------------
# Site 1 — smart-fallback (_smart_fallback_extract)
# ---------------------------------------------------------------------------
class TestSmartFallbackSite:

    @pytest.mark.asyncio
    async def test_flag_on_skips_the_refill_entirely(self, flag_on):
        """Flag ON: no Serper search, no GPT call, empty result."""
        search_spy = _Spy({"organic": [{"snippet": "front cam 12 MP"}]})
        gpt_spy = _Spy({"front_camera": "12 MP f/2.2"})

        svc = get_comparison_service()
        with patch(
            "app.services.structured_comparison_service.search_web", new=search_spy,
        ), patch(
            "app.services.openai_service.extract_specs_targeted", new=gpt_spy,
        ):
            out = await svc._smart_fallback_extract(
                "Samsung", "Galaxy S25 Ultra", None, "electronics",
                ["front_camera", "battery"],
            )

        assert out == {}
        assert search_spy.calls == []
        assert gpt_spy.calls == []

    @pytest.mark.asyncio
    async def test_flag_off_refills_exactly_as_today(self, flag_off):
        """Flag OFF: byte-identical to main — the refill fires and fills."""
        search_spy = _Spy({"organic": [{"snippet": "front cam 12 MP"}]})
        gpt_spy = _Spy({"front_camera": "12 MP f/2.2"})

        svc = get_comparison_service()
        with patch(
            "app.services.structured_comparison_service.search_web", new=search_spy,
        ), patch(
            "app.services.openai_service.extract_specs_targeted", new=gpt_spy,
        ):
            out = await svc._smart_fallback_extract(
                "Samsung", "Galaxy S25 Ultra", None, "electronics",
                ["front_camera", "battery"],
            )

        assert out == {"front_camera": "12 MP f/2.2"}
        assert len(search_spy.calls) == 1
        assert len(gpt_spy.calls) == 1


# ---------------------------------------------------------------------------
# Site 2 — Tier 2 targeted per-field fill
# ---------------------------------------------------------------------------
class TestTier2Site:

    @pytest.mark.asyncio
    async def test_flag_on_skips_evidence_omitted_fields(self, flag_on):
        """Flag ON with A3's `_evidence_limited` marker: the missing
        non-negotiables ARE the evidence-omitted ones — no refill."""
        search_spy = _Spy({"organic": [{"snippet": "battery 5000 mAh"}]})
        gpt_spy = _Spy({"battery": "5000 mAh"})

        with patch(
            "app.services.serper_service.search_web", new=search_spy,
        ), patch(
            "app.services.openai_service.extract_specs_targeted", new=gpt_spy,
        ):
            out = await tier2_fill_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far=dict(_ELECTRONICS_GAP, _evidence_limited=True),
            )

        assert out == {}
        assert search_spy.calls == []
        assert gpt_spy.calls == []

    @pytest.mark.asyncio
    async def test_flag_on_skips_pre_flip_cached_na_fields_too(self, flag_on):
        """Flag ON WITHOUT the marker (a 7-day spec cache written before the
        flag was flipped still carries "N/A" stamps): refilling those is the
        same fabrication, so the gate is the FLAG, not the marker."""
        gpt_spy = _Spy({"battery": "5000 mAh"})

        with patch(
            "app.services.serper_service.search_web", new=_fake_search,
        ), patch(
            "app.services.openai_service.extract_specs_targeted", new=gpt_spy,
        ):
            out = await tier2_fill_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far={"processor": "A17 Pro", "battery": "N/A", "ram": ""},
            )

        assert out == {}
        assert gpt_spy.calls == []

    @pytest.mark.asyncio
    async def test_flag_off_refills_exactly_as_today(self, flag_off):
        gpt_spy = _Spy({"battery": "5000 mAh"})

        with patch(
            "app.services.serper_service.search_web", new=_fake_search,
        ), patch(
            "app.services.openai_service.extract_specs_targeted", new=gpt_spy,
        ):
            out = await tier2_fill_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far=dict(_ELECTRONICS_GAP),
            )

        assert out.get("battery") == "5000 mAh"
        assert gpt_spy.calls, "flag OFF must still fire the Tier 2 refill"


# ---------------------------------------------------------------------------
# Site 3 — Tier 3 batched synthesis (NO snippet context at all)
# ---------------------------------------------------------------------------
class TestTier3Site:

    @pytest.mark.asyncio
    async def test_flag_on_skips_the_synthesis(self, flag_on):
        """Tier 3 has no evidence channel — every value it returns is the
        training-data fallback the flag forbids, so it cannot be gated by a
        prompt contract; it must not run at all."""
        synth = AsyncMock(return_value={"battery": "4000 mAh"})
        router = AsyncMock(return_value="gpt-4o")

        with patch(
            "app.services.openai_service.extract_specs_synthesized", new=synth,
        ), patch(
            "app.services.model_router_service.model_router.get_model", new=router,
        ):
            out = await tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far=dict(_ELECTRONICS_GAP, _evidence_limited=True),
            )

        assert out == {}
        synth.assert_not_awaited()
        router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_flag_off_synthesizes_exactly_as_today(self, flag_off):
        synth = AsyncMock(return_value={"battery": "4000 mAh"})

        with patch(
            "app.services.openai_service.extract_specs_synthesized", new=synth,
        ), patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ):
            out = await tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far=dict(_ELECTRONICS_GAP),
            )

        assert out == {"battery": "4000 mAh"}
        synth.assert_awaited()

    @pytest.mark.asyncio
    async def test_flag_is_read_per_call_never_cached_at_import(self, monkeypatch):
        """House rule 1 — the same process must see a Railway flip without a
        restart. Same function, two calls, opposite env."""
        synth = AsyncMock(return_value={"battery": "4000 mAh"})
        with patch(
            "app.services.openai_service.extract_specs_synthesized", new=synth,
        ), patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ):
            monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "true")
            first = await tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics", specs_so_far=dict(_ELECTRONICS_GAP),
            )
            monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "false")
            second = await tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics", specs_so_far=dict(_ELECTRONICS_GAP),
            )

        assert first == {}
        assert second == {"battery": "4000 mAh"}


# ---------------------------------------------------------------------------
# Flag-OFF prompt byte-pins — the refill prompts must NOT be forked
# ---------------------------------------------------------------------------
class _CapturingClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(self._payload)))],
            usage=None,
        )


class TestRefillPromptsUnchanged:
    """Flag OFF, the two refill prompts render exactly as they do on main.

    These are the byte-pins for the rollback path. They also encode the D1
    design decision: the cascade is closed by SKIPPING the refill, never by
    forking a third no-fabrication prompt into ``openai_service``.
    """

    @pytest.mark.asyncio
    async def test_targeted_prompt_exact_substrings(self, flag_off):
        client = _CapturingClient({"battery": "5000 mAh"})
        from app.services import openai_service

        with patch.object(openai_service, "get_client", return_value=client):
            await openai_service.extract_specs_targeted(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics", fields=["battery"], context="snip",
            )

        system = client.calls[0]["messages"][0]["content"]
        assert "Extract these specific fields for Apple iPhone 16 from the snippets below." in system
        assert "- Use your training data as a fallback when snippets are silent" in system
        assert "- NEVER return the literal string 'N/A' - return null instead" in system

    @pytest.mark.asyncio
    async def test_synthesized_prompt_exact_substrings(self, flag_off):
        client = _CapturingClient({"battery": "5000 mAh"})
        from app.services import openai_service

        with patch.object(openai_service, "get_client", return_value=client):
            await openai_service.extract_specs_synthesized(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics", fields=["battery"], model="gpt-4o",
            )

        system = client.calls[0]["messages"][0]["content"]
        assert (
            "You are a product specifications expert. Synthesize these specific "
            "fields for Apple iPhone 16 from your training-data knowledge."
        ) in system
        assert "- This is a last-resort fallback; accuracy matters more than completeness" in system

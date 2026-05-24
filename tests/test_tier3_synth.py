"""Bundle D Task 2.B.4 (A.4.8) — Tier 3 GPT-4o batched synthesis tests.

These tests mock the openai_service + model_router so we don't burn real
API credits. The integration smoke (cost budget verification) happens in
the live-unit tier when ENABLE_LIVE_TESTS is set.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTier3SynthesizeNonNegotiables:
    """Bundle D A.4.8 — Tier 3 batched synthesis fallback contract."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_missing_fields(self):
        """Happy-path skip — when Tier 2 already filled all non-negotiables,
        Tier 3 should be a no-op (zero added wall, zero cost)."""
        from app.services.structured_comparison_service import (
            tier3_synthesize_non_negotiables,
        )

        result = await tier3_synthesize_non_negotiables(
            brand="Apple", name="iPhone 16", variant=None,
            category="electronics",
            specs_so_far={
                "battery": "3500 mAh",
                "processor": "A18",
                "ram": "8 GB",
                "rear_camera": "48 MP",
            },
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_for_other_category(self):
        """'other' category has no non-negotiables — skip entirely."""
        from app.services.structured_comparison_service import (
            tier3_synthesize_non_negotiables,
        )

        result = await tier3_synthesize_non_negotiables(
            brand="X", name="Y", variant=None,
            category="other",
            specs_so_far={},  # nothing filled, but no non-negotiables either
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_fires_when_non_negotiable_missing(self):
        """When non-negotiable field is blank → fires the GPT-4o synth call."""
        from app.services import structured_comparison_service as svc

        with patch(
            "app.services.openai_service.extract_specs_synthesized",
            new=AsyncMock(return_value={"battery": "4000 mAh", "processor": "A18 Pro"}),
        ) as mock_synth, patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ):
            result = await svc.tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far={
                    "battery": "N/A",
                    "processor": "",
                    "ram": "8 GB",      # already filled
                    "rear_camera": "48 MP",  # already filled
                },
            )
            assert result == {"battery": "4000 mAh", "processor": "A18 Pro"}
            assert mock_synth.await_count == 1
            # Verify it requested ONLY the missing fields (batched)
            call_kwargs = mock_synth.await_args.kwargs
            assert sorted(call_kwargs["fields"]) == ["battery", "processor"]

    @pytest.mark.asyncio
    async def test_uses_priority_high_routing(self):
        """Tier 3 escalates to gpt-4o via model_router priority='high'."""
        from app.services import structured_comparison_service as svc

        with patch(
            "app.services.openai_service.extract_specs_synthesized",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ) as mock_get_model:
            await svc.tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far={"battery": ""},  # one missing → triggers call
            )
            mock_get_model.assert_awaited_once_with(priority="high")

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_silently(self):
        """Wall budget breach → silent omission per § 2h. No exception escapes."""
        import asyncio

        from app.services import structured_comparison_service as svc

        async def _hang(**kw):
            await asyncio.sleep(10)  # > _TIER3_WALL_SECONDS=3.0
            return {"battery": "should never be returned"}

        with patch(
            "app.services.openai_service.extract_specs_synthesized",
            new=_hang,
        ), patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ):
            # Bypass the actual 3s wait via patching the wall constant
            with patch.object(svc, "_TIER3_WALL_SECONDS", 0.1):
                result = await svc.tier3_synthesize_non_negotiables(
                    brand="Apple", name="iPhone 16", variant=None,
                    category="electronics",
                    specs_so_far={"battery": ""},
                )
            assert result == {}

    @pytest.mark.asyncio
    async def test_exception_returns_empty_silently(self):
        """Any GPT exception → silent omission. Never propagates."""
        from app.services import structured_comparison_service as svc

        with patch(
            "app.services.openai_service.extract_specs_synthesized",
            new=AsyncMock(side_effect=RuntimeError("OpenAI down")),
        ), patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ):
            result = await svc.tier3_synthesize_non_negotiables(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                specs_so_far={"battery": ""},
            )
            assert result == {}

    @pytest.mark.asyncio
    async def test_filters_na_and_empty_from_synth_response(self):
        """If GPT returns 'N/A' or '' for a field, it must not be merged."""
        from app.services import structured_comparison_service as svc

        with patch(
            "app.services.openai_service.extract_specs_synthesized",
            new=AsyncMock(return_value={
                "battery": "4000 mAh",
                "processor": "N/A",
                "rear_camera": "",
            }),
        ), patch(
            "app.services.model_router_service.model_router.get_model",
            new=AsyncMock(return_value="gpt-4o"),
        ):
            result = await svc.tier3_synthesize_non_negotiables(
                brand="X", name="Y", variant=None,
                category="electronics",
                specs_so_far={"battery": "", "processor": "", "rear_camera": "", "ram": "8 GB"},
            )
            # Only the real value comes through
            assert result == {"battery": "4000 mAh"}


class TestExtractSpecsSynthesized:
    """Verify the openai_service.extract_specs_synthesized helper shape."""

    @pytest.mark.asyncio
    async def test_no_fields_returns_empty_dict(self):
        """Defensive — caller passing empty fields list should no-op."""
        from app.services.openai_service import extract_specs_synthesized

        result = await extract_specs_synthesized(
            brand="X", name="Y", variant=None,
            category="electronics", fields=[],
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_filters_na_and_unknown_keys(self):
        """Returned dict drops null + 'N/A' values, drops keys not in fields list."""
        import json

        from app.services import openai_service

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "battery": "4000 mAh",
            "processor": "N/A",
            "ram": None,
            "garbage_field": "should be dropped",
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(openai_service, "get_client", return_value=mock_client), \
             patch.object(openai_service, "_log_cache_telemetry"):
            result = await openai_service.extract_specs_synthesized(
                brand="Apple", name="iPhone 16", variant=None,
                category="electronics",
                fields=["battery", "processor", "ram"],
            )
        assert result == {"battery": "4000 mAh"}

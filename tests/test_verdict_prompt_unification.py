"""I5.10 (Bundle B S2) — prod/test verdict-prompt unification.

Before: prod `generate_comparison` (extraction_service.py) hand-assembled the
verdict system prompt (COMPARISON_SYSTEM + personality + pain_workflow +
decision_style) inline, while the test-only `build_verdict_prompt` assembled
the SAME static prefix in one place. Audits grepped `build_verdict_prompt`, not
what production actually ran — and I2's exemplar injection needs ONE injection
point.

After: prod builds its static prefix by CALLING `build_verdict_prompt`, then
appends the per-call dynamic blocks (scoring/preferences/cohort). This test
pins that the prod static prefix == `build_verdict_prompt(...)` output so the
two can never drift again.

Behavior-preserving: prod stays at comparison_quality="normal" (it never
injected _WEIRD_VERDICT_INSTRUCTION before) — the weird/missing-data decision
is I3's epic, out of scope here.
"""
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.services import extraction_service
from app.services.extraction_service import build_verdict_prompt


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _capture_prod_system_msg(category="electronics", demographics_profile=None):
    """Drive generate_comparison with the OpenAI call mocked, capturing the
    exact system message prod sent."""
    captured = {}

    async def fake_create(*args, **kwargs):
        messages = kwargs.get("messages") or (args[0] if args else [])
        for m in messages:
            if m.get("role") == "system":
                captured["system"] = m["content"]
        # Minimal valid verdict JSON.
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = (
            '{"winner_index": 0, "winner_reason": "x", '
            '"product_0_pros": [], "product_1_pros": []}'
        )
        resp.choices = [choice]
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        return resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=fake_create)

    fake_router = MagicMock()
    fake_router.get_model = AsyncMock(return_value="gpt-4o-mini")
    fake_router.record_usage = AsyncMock(return_value=None)

    p1 = {"brand": "Apple", "name": "iPhone 15", "category": category, "category_used": category}
    p2 = {"brand": "Samsung", "name": "Galaxy S24", "category": category, "category_used": category}

    with patch.object(extraction_service, "get_client", return_value=fake_client), \
         patch("app.services.model_router_service.model_router", fake_router):
        run_async(extraction_service.generate_comparison(
            p1, p2, "bahrain", "value",
            user_preferences=None, scores_summary=None, category=category,
            demographics_profile=demographics_profile,
        ))
    return captured.get("system", "")


class TestVerdictPromptUnification:
    def test_prod_static_prefix_equals_build_verdict_prompt_no_scoring(self):
        """With no scores_summary / preferences / cohort, prod's system message
        is EXACTLY build_verdict_prompt's static prefix."""
        category = "electronics"
        prod_msg = _capture_prod_system_msg(category=category, demographics_profile=None)

        products = [
            {"brand": "Apple", "name": "iPhone 15", "category": category, "category_used": category},
            {"brand": "Samsung", "name": "Galaxy S24", "category": category, "category_used": category},
        ]
        expected_prefix = build_verdict_prompt(
            products=products, comparison_quality="normal", user_cohort=None,
        )
        assert prod_msg == expected_prefix

    def test_prod_prefix_is_a_prefix_when_cohort_present(self):
        """With a cohort but still no scoring/preferences, prod's message is the
        build_verdict_prompt output for that cohort (the cohort flows through)."""
        category = "skincare"
        cohort = {"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"}
        prod_msg = _capture_prod_system_msg(category=category, demographics_profile=cohort)

        products = [
            {"brand": "CeraVe", "name": "Retinol", "category": category, "category_used": category},
            {"brand": "The Ordinary", "name": "Granactive", "category": category, "category_used": category},
        ]
        expected_prefix = build_verdict_prompt(
            products=products, comparison_quality="normal", user_cohort=cohort,
        )
        assert prod_msg == expected_prefix

    def test_build_verdict_prompt_accepts_explicit_category(self):
        """The unification threads prod's explicit `category` through; an
        explicit category overrides product-derived category so prod and test
        agree even when product dicts lack category_used."""
        products_no_cat = [{"name": "X"}, {"name": "Y"}]
        from_explicit = build_verdict_prompt(
            products=products_no_cat, comparison_quality="normal", category="electronics",
        )
        products_with_cat = [
            {"name": "X", "category_used": "electronics"},
            {"name": "Y", "category_used": "electronics"},
        ]
        from_derived = build_verdict_prompt(
            products=products_with_cat, comparison_quality="normal",
        )
        assert from_explicit == from_derived

    def test_prod_still_appends_scoring_block(self):
        """The dynamic scoring block is appended AFTER the unified static
        prefix — unification must not drop the per-call scoring context."""
        category = "electronics"
        captured = {}

        async def fake_create(*args, **kwargs):
            for m in kwargs.get("messages", []):
                if m.get("role") == "system":
                    captured["system"] = m["content"]
            resp = MagicMock()
            choice = MagicMock()
            choice.message.content = '{"winner_index": 0, "winner_reason": "x"}'
            resp.choices = [choice]
            resp.usage = MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2)
            return resp

        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(side_effect=fake_create)
        fake_router = MagicMock()
        fake_router.get_model = AsyncMock(return_value="gpt-4o-mini")
        fake_router.record_usage = AsyncMock(return_value=None)

        p1 = {"brand": "A", "name": "1", "category_used": category}
        p2 = {"brand": "B", "name": "2", "category_used": category}
        with patch.object(extraction_service, "get_client", return_value=fake_client), \
             patch("app.services.model_router_service.model_router", fake_router):
            run_async(extraction_service.generate_comparison(
                p1, p2, "bahrain", "value",
                scores_summary="Product A scores 80, Product B scores 70.",
                category=category,
            ))
        # Static prefix present AND the scoring block appended after it.
        assert "Scoring Context" in captured["system"]
        assert "Product A scores 80" in captured["system"]
        # The unified static prefix is still the leading content.
        prefix = build_verdict_prompt(
            products=[p1, p2], comparison_quality="normal",
        )
        assert captured["system"].startswith(prefix)

"""Phase 4 Task #5 — verdict prompt contract (F4.3 + F4.5).

The verdict prompt must instruct the model to:
  (a) make the winner's case convincingly (already present — decisive + data),
  (b) name a CONCRETE buyer who should pick the RUNNER-UP (F4.5), and
  (c) explicitly weave the user's stated priorities into the MAIN verdict prose
      (winner_reason / best_for), not only the personalized_insights side-array
      (F4.3 — Ahmed's "personalization isn't clicking").

These are prompt-contract assertions (the instruction text is present) + a
forbidden-words guard so the new copy never smuggles in scary/banned vocab.
"""

import pytest

from app.services.extraction_service import (
    COMPARISON_SYSTEM,
    _build_preferences_prompt,
)

# Mirrors the EN forbidden vocab the broader audit enforces.
_FORBIDDEN = [
    "estimated", "reference price", "couldn't", "try again", "failed to",
    "we couldn't", "unable to", "best pick", "winner!",
]


class TestRunnerUpCaseInBasePrompt:
    def test_key_tradeoff_instructs_runner_up_advantage(self):
        # The base prompt already names the loser's strongest advantage.
        assert "key_tradeoff" in COMPARISON_SYSTEM
        low = COMPARISON_SYSTEM.lower()
        assert "strongest advantage" in low or "strongest" in low

    def test_best_for_names_a_concrete_buyer_for_each(self):
        # F4.5 — best_for must describe WHO should pick each product (a concrete
        # buyer profile), including the runner-up.
        low = COMPARISON_SYSTEM.lower()
        assert "best_for" in COMPARISON_SYSTEM
        assert "who should" in low or "ideal buyer" in low or "buyer profile" in low

    def test_runner_up_concrete_buyer_instruction_present(self):
        # F4.5 — explicit instruction that the runner-up's best_for names a
        # concrete buyer (not just a product description).
        low = COMPARISON_SYSTEM.lower()
        assert "runner-up" in low or "the other product" in low or "losing product" in low


class TestPersonalizationWeavingEnforced:
    def test_winner_reason_must_reference_priority_when_personalized(self):
        prefs = {"priorities": ["battery_life", "value"], "budget": "mid"}
        prompt = _build_preferences_prompt(prefs)
        low = prompt.lower()
        # F4.3 — the personalization block must require the MAIN verdict prose
        # (winner_reason) to name the user's priority, not only side-insights.
        assert "winner_reason" in low
        assert "priorit" in low  # priorities / priority

    def test_priorities_listed_in_block(self):
        prefs = {"priorities": ["camera", "battery_life"], "budget": "premium"}
        prompt = _build_preferences_prompt(prefs)
        assert "camera" in prompt
        assert "battery_life" in prompt

    def test_best_for_aligns_with_priorities(self):
        prefs = {"priorities": ["value"], "budget": "budget"}
        prompt = _build_preferences_prompt(prefs)
        low = prompt.lower()
        assert "best_for" in low

    def test_empty_priorities_safe(self):
        # No priorities → block still builds (no crash), no forbidden vocab.
        prompt = _build_preferences_prompt({"priorities": [], "budget": "mid"})
        assert isinstance(prompt, str)
        low = prompt.lower()
        for bad in _FORBIDDEN:
            assert bad not in low


class TestForbiddenWordsClean:
    def test_base_prompt_no_forbidden(self):
        low = COMPARISON_SYSTEM.lower()
        for bad in _FORBIDDEN:
            assert bad not in low, f"COMPARISON_SYSTEM contains forbidden '{bad}'"

    def test_preferences_prompt_no_forbidden(self):
        prefs = {"priorities": ["battery_life", "value"], "budget": "mid",
                 "lifestyle": ["active"], "brand_attitude": "function_first"}
        low = _build_preferences_prompt(prefs).lower()
        for bad in _FORBIDDEN:
            assert bad not in low, f"_build_preferences_prompt contains forbidden '{bad}'"

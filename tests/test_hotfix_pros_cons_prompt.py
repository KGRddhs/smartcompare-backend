"""Bundle C v1 hot-fix — verdict prompt now explicitly forbids empty pros/cons.

Post-merge probes (qa D.4.2) showed `products[*].pros = []` on all 6
production probes despite A.3.1 `response_format={"type": "json_object"}`.
Root cause: the verdict-prompt rule `4-6 pros... each MUST include a
specific number, percentage, or measurable fact` made GPT defensively
emit `[]` when it couldn't satisfy the strict numeric requirement.

Hot-fix loosens the rule to allow qualitative attributes when numeric
isn't available, AND adds an explicit "NEVER return empty pros[] or
cons[]" directive. Combined with response_format=json_object, this
should reliably populate.
"""
from app.services.extraction_service import COMPARISON_SYSTEM


def test_comparison_prompt_explicitly_forbids_empty_pros_cons():
    """Hot-fix: prompt must contain an unambiguous directive against
    empty arrays. Regression test catches any future drift back to
    the strict-MUST phrasing."""
    assert "NEVER return empty pros" in COMPARISON_SYSTEM or "never return empty" in COMPARISON_SYSTEM.lower(), (
        "verdict prompt missing the explicit empty-arrays prohibition — "
        "GPT will revert to defensive [] emission under strict number rules"
    )


def test_comparison_prompt_allows_qualitative_attributes():
    """Hot-fix: prompt must allow qualitative attributes when numeric
    facts unavailable (so GPT can populate pros even for low-data products)."""
    body = COMPARISON_SYSTEM.lower()
    assert "qualitative attribute" in body or "concrete qualitative" in body, (
        "verdict prompt missing the qualitative-attribute fallback — "
        "low-numeric-data products will still produce empty pros"
    )


def test_comparison_prompt_dropped_strict_must_include_number_phrasing():
    """Regression test: the original strict 'MUST include a specific
    number, percentage, or measurable fact' phrasing is the root cause
    of the empty-arrays bug. Must NOT come back."""
    body = COMPARISON_SYSTEM
    # The exact original phrasing was 'each MUST include a specific'
    assert "each MUST include a specific number" not in body, (
        "regression: strict MUST-include-number phrasing is back — "
        "hot-fix root cause un-fixed"
    )


def test_comparison_prompt_preserves_4_6_pros_2_4_cons_range():
    """Hot-fix loosened the rule but kept the count guidance — verify
    the per-product pros/cons counts didn't get dropped accidentally."""
    body = COMPARISON_SYSTEM
    assert "4-6 pros" in body and "2-4 cons" in body, (
        "pros/cons count guidance dropped from prompt — GPT may emit too few items"
    )

"""Tests for A-L4.2 — verdict-prompt pain-workflow injection.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.2
Design: docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6

`build_verdict_prompt()` must inject the top-3 pain-workflow instructions
for the user's cohort (top-3 globally if cohort is unknown or too small),
plus a TL;DR-first instruction. Output must NEVER contain forbidden scary
copy (EN: couldn't, try again, Failed to; AR: تعذر, فشل).
"""

import pytest

from app.services.extraction_service import build_verdict_prompt


# ---------------------------------------------------------------------------
# Top-3 injection — verifiable by canonical workflow markers
# ---------------------------------------------------------------------------

def test_verdict_prompt_includes_top_3_pain_workflows_known_cohort():
    """For a populated cohort, the prompt must include at least the top-3
    survey-ranked workflows' canonical fingerprints."""
    products = [
        {"name": "iPhone 15", "category": "electronics", "category_used": "electronics"},
        {"name": "Galaxy S24", "category": "electronics", "category_used": "electronics"},
    ]
    prompt = build_verdict_prompt(
        products=products,
        user_cohort={"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    )
    lower = prompt.lower()

    # Close-option paralysis fingerprint
    assert ("tie-break" in lower) or ("tie break" in lower) or ("if budget matters" in lower)
    # Too-many-specs fingerprint
    assert ("max 3" in lower) or ("maximum of 3" in lower) or ("max of 3" in lower)
    # Value/budget fingerprint
    assert ("value-per-bhd" in lower) or ("value per bhd" in lower) or ("value-per" in lower)


def test_verdict_prompt_includes_top_3_pain_workflows_unknown_cohort():
    """Without a cohort, the prompt falls back to globally top-3 (which are
    the same first three on the survey aggregate)."""
    products = [{"name": "A", "category": "skincare", "category_used": "skincare"}]
    prompt = build_verdict_prompt(products=products)
    lower = prompt.lower()
    assert ("tie-break" in lower) or ("tie break" in lower)
    assert ("max 3" in lower) or ("maximum of 3" in lower)


def test_verdict_prompt_pain_workflow_section_header():
    """A clearly labelled section so downstream prompt audits can find it."""
    prompt = build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
        user_cohort={"age_group": "18-24", "gender": "Male", "nationality": "Bahraini"},
    )
    assert "## Buyer pain-workflow constraints" in prompt or "PAIN WORKFLOWS" in prompt.upper()


# ---------------------------------------------------------------------------
# TL;DR-first
# ---------------------------------------------------------------------------

def test_verdict_prompt_tldr_first_instruction_present():
    """Design § 6 workflow #8 (decision_speed) injects a TL;DR-first
    instruction; if not in top-3 by cohort it must still be present as the
    decision_speed shipping floor."""
    prompt = build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
    )
    lower = prompt.lower()
    assert ("tl;dr" in lower) or ("one-sentence" in lower) or ("one sentence" in lower)


# ---------------------------------------------------------------------------
# No scary copy
# ---------------------------------------------------------------------------

def test_verdict_prompt_no_scary_copy_en():
    prompt = build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
        user_cohort={"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    )
    forbidden = ["couldn't", "Couldn't", "try again", "Try again", "Failed to", "failed to"]
    for word in forbidden:
        assert word not in prompt, f"scary vocab {word!r} leaked into verdict prompt"


def test_verdict_prompt_no_scary_copy_ar():
    prompt = build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
        user_cohort={"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    )
    for word in ("تعذر", "فشل"):
        assert word not in prompt


# ---------------------------------------------------------------------------
# Cohort fallback hierarchy
# ---------------------------------------------------------------------------

def test_verdict_prompt_cohort_partial_input_falls_back():
    """Missing nationality must NOT crash — falls back to _global ranking."""
    prompt = build_verdict_prompt(
        products=[{"name": "X", "category_used": "skincare"}],
        user_cohort={"age_group": "25-34", "gender": "Female"},
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 200


def test_verdict_prompt_decision_style_block_present():
    """Top decision-style preference for the cohort is injected as a render
    hint — the model still produces a verdict, but matches the style users
    in this cohort prefer to read."""
    prompt = build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
        user_cohort={"age_group": "18-24", "gender": "Female", "nationality": "Bahraini"},
    )
    lower = prompt.lower()
    assert ("preferred style" in lower) or ("decision style" in lower) or ("verdict style" in lower)


# ---------------------------------------------------------------------------
# Backwards compatibility — old signature still works
# ---------------------------------------------------------------------------

def test_verdict_prompt_old_signature_still_works():
    """The pre-L4 callers pass only `products` + `comparison_quality`. New
    optional kwargs must not break them."""
    prompt = build_verdict_prompt(products=[{"name": "X", "category_used": "electronics"}])
    assert isinstance(prompt, str)
    assert len(prompt) > 200

    prompt_weird = build_verdict_prompt(
        products=[{"name": "X", "category_used": "electronics"}],
        comparison_quality="weird",
    )
    assert isinstance(prompt_weird, str)


def test_verdict_prompt_idempotent_no_duplicate_blocks():
    """Calling twice with same args should not produce a noticeably
    different prompt (build is pure)."""
    args = {
        "products": [{"name": "X", "category_used": "electronics"}],
        "user_cohort": {"age_group": "25-34", "gender": "Female", "nationality": "Bahraini"},
    }
    a = build_verdict_prompt(**args)
    b = build_verdict_prompt(**args)
    assert a == b

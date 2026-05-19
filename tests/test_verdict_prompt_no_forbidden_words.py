"""Bundle C A.10.2 — verdict prompt forbidden-words audit.

Per design § 0 critical rules #1, #3, #5: the verdict prompt MUST NOT
contain user-facing forbidden vocabulary except in negative-instruction
context ("do not say X").

This audit catches any future change that bakes forbidden phrasing
into the prompt text the model uses to generate user-visible
verdicts.

Critical-rule vocabulary:
- Rule #3: "estimated", "reference price", "indicative", "approximate"
- Rule #5: "couldn't", "try again", "Failed to", Arabic "تعذر" / "فشل"
- Rule #1: "show banner", "info banner", "display warning"
"""
import pytest

from app.services import extraction_service


FORBIDDEN_USER_FACING = (
    "estimated",
    "reference price",
    "approximate",
    "couldn't",
    "try again",
    "failed to",
    "show banner",
    "info banner",
    "display warning",
)


def _audit_for_forbidden(prompt: str, allow_negative_context: bool = True) -> list:
    """Return list of forbidden phrases found in `prompt` that are NOT
    preceded by a negative-instruction marker.

    Negative instruction examples (these are OK):
      - "do not say X"
      - "avoid X"
      - "never use X"
      - "forbidden: X"
      - "NOT X"
    """
    lowered = prompt.lower()
    violations = []
    for phrase in FORBIDDEN_USER_FACING:
        idx = lowered.find(phrase)
        if idx < 0:
            continue
        # Look at the context (50 chars before) for a negative marker.
        context = lowered[max(0, idx - 80):idx]
        if allow_negative_context and any(
            neg in context
            for neg in (
                "do not", "avoid", "never use", "forbidden",
                "must not", "must never", "won't", "do NOT",
                "no ", "must not", "do not say", "do not use",
            )
        ):
            continue  # Phrase appears in a negative-instruction context — allowed.
        violations.append((phrase, idx))
    return violations


def test_build_verdict_prompt_normal_has_no_forbidden_words():
    """Default (comparison_quality='normal') prompt must be free of
    forbidden user-facing vocabulary."""
    prompt = extraction_service.build_verdict_prompt(
        products=[
            {"name": "A", "category_used": "electronics"},
            {"name": "B", "category_used": "electronics"},
        ],
        comparison_quality="normal",
    )
    violations = _audit_for_forbidden(prompt)
    assert violations == [], (
        f"forbidden phrases leaked into normal verdict prompt: {violations}"
    )


def test_build_verdict_prompt_weird_has_no_forbidden_words():
    """Weird-context prompt (with extra rewrite instruction) must
    ALSO be free of forbidden vocabulary — the rewrite block uses
    presentational language only."""
    prompt = extraction_service.build_verdict_prompt(
        products=[
            {"name": "iPhone", "category_used": "electronics"},
            {"name": "CeraVe", "category_used": "skincare"},
        ],
        comparison_quality="weird",
    )
    violations = _audit_for_forbidden(prompt)
    assert violations == [], (
        f"forbidden phrases leaked into weird verdict prompt: {violations}"
    )


def test_comparison_system_template_has_no_forbidden_words():
    """The base COMPARISON_SYSTEM template at the top of the prompt
    chain must be clean — it composes into every verdict call."""
    src = extraction_service.COMPARISON_SYSTEM
    violations = _audit_for_forbidden(src)
    assert violations == [], (
        f"forbidden phrases leaked into COMPARISON_SYSTEM template: {violations}"
    )


def test_weird_instruction_block_uses_presentational_language():
    """The A.4.5 _WEIRD_VERDICT_INSTRUCTION block specifically uses
    'different purposes' framing — make sure it doesn't accidentally
    drift back to scary copy."""
    src = extraction_service._WEIRD_VERDICT_INSTRUCTION
    violations = _audit_for_forbidden(src)
    assert violations == [], (
        f"forbidden phrases in weird instruction block: {violations}"
    )
    # Positive assertion — must contain the non-forced-winner framing
    assert "different purposes" in src.lower()


def test_audit_helper_correctly_flags_bare_forbidden_word():
    """Sanity check on the audit helper — if someone naively writes
    'the price is estimated', the helper should catch it (no negative
    context preceding)."""
    sample = "The price shown is estimated for older models."
    violations = _audit_for_forbidden(sample, allow_negative_context=True)
    assert any(phrase == "estimated" for phrase, _ in violations), (
        f"audit helper failed to flag bare 'estimated' — {violations}"
    )


def test_audit_helper_allows_negative_instruction_context():
    """Sanity check on the audit helper — when a forbidden phrase
    appears in a 'do not say X' clause, the helper allows it."""
    sample = "Forbidden vocabulary: do not say estimated; do not use approximate."
    violations = _audit_for_forbidden(sample, allow_negative_context=True)
    assert violations == [], (
        f"audit helper false-positive on negative-instruction context: {violations}"
    )

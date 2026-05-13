"""
Bundle E Task 1.4 RED — build_factual_verdict() emits a deterministic
2-sentence verdict from dimension deltas, never from GPT-invented prose.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 1.4,
      § Test-1.4)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 5.

Contract under test (signature lifted verbatim from design § Decision 5):

    def build_factual_verdict(
        scoring: dict,
        products: list[dict],
        lang: str = "en",
    ) -> str:
        \"\"\"Compose verdict from dimension deltas.

        Returns 2 sentences max:
          Line 1: factual deltas — "BHD 30 less, 0.2★ higher, 12g lighter"
          Line 2: conditional alternative — "If you want PBT keycaps,
                  the {runner_brand_word} fits."
        \"\"\"

Invariants (design § Decision 5):

  1. No score numbers — no 2-or-3-digit integers anywhere in the output
     (the hero ring already shows the number; verdict is copy-only).
  2. No banned evaluative words from the 13-word deny list (single
     source of truth = banned_pattern fixture below).
  3. Verdict uses each picked dimension's `delta_text` directly — does
     NOT regenerate phrasing. We assert the top-3 winner deltas appear
     verbatim in line 1.
  4. Conditional pattern for runner-up: starts with "If you want " (or
     "If you prefer "), references a runner-up dimension's label, and
     names the runner product.
  5. Distinct dimension sets produce distinct verdicts — no template
     repetition across 4 phrasing variants.

RED→GREEN trajectory:
  - At HEAD: `app.services.verdict_builder` does not exist →
    ModuleNotFoundError at collection → RED.
  - After Agent A lands Task 1.4: all assertions pass.
"""

from __future__ import annotations

import re
import pytest

# RED gate — ModuleNotFoundError until Agent A lands Task 1.4.
from app.services.verdict_builder import build_factual_verdict  # noqa: E402


# ---------------------------------------------------------------------------
# Shared deny-list / regexes
# ---------------------------------------------------------------------------

BANNED_WORDS = frozenset({
    "best", "pick", "excellent", "great", "recommend", "winner", "worst",
    "better", "worse", "beats", "smart", "good", "choose",
})
BANNED_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")\b",
    flags=re.IGNORECASE,
)
# Two-or-three digit run that is NOT preceded/followed by a letter — i.e.
# a standalone number. Excludes things like "BHD 30 less" where "30" is
# part of a factual unit-bearing delta_text (allowed when inherited from
# delta_text); the test below uses a STRICT version that bans even the
# inherited numbers when checking the assembled verdict's standalone-score
# patterns. See test docstrings for nuance.
DIGIT_PATTERN = re.compile(r"\b\d{2,3}\b")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scoring(dims: list[dict], winner_idx: int = 0):
    """Build a scoring dict in the shape build_factual_verdict consumes.
    Includes `overall_score.winner_idx` per design § Decision 5 code
    sample (line 294)."""
    overall_a = 87 if winner_idx == 0 else 82
    overall_b = 82 if winner_idx == 0 else 87
    return {
        "overall_score": {
            "product_a": overall_a,
            "product_b": overall_b,
            "winner_idx": winner_idx,
        },
        "win_margin": abs(overall_a - overall_b),
        "dimensions": dims,
    }


def _products(name_a: str = "Glorious Model O", name_b: str = "Ducky One 2 Mini"):
    return [
        {"brand": "Glorious", "name": name_a, "category": "electronics"},
        {"brand": "Ducky", "name": name_b, "category": "electronics"},
    ]


def _full_dim_set(winner_is_a: bool):
    """3 core (price, reviews, value) all won by product_a (or _b),
    plus one contextual (build_quality) won by the runner-up — design
    § Decision 5 line 299 pivots on a dim where the runner-up wins."""
    a_higher = (95, 75) if winner_is_a else (75, 95)
    return [
        {"key": "price", "label": "Price",
         "score_a": a_higher[0], "score_b": a_higher[1],
         "delta_text": "BHD 30 less", "confidence": "high", "is_core": True},
        {"key": "reviews", "label": "Reviews",
         "score_a": a_higher[0], "score_b": a_higher[1],
         "delta_text": "0.2 stars higher", "confidence": "high", "is_core": True},
        {"key": "value", "label": "Value",
         "score_a": a_higher[0], "score_b": a_higher[1],
         "delta_text": "12g lighter", "confidence": "high", "is_core": True},
        # Runner-up wins build_quality (used by line 2 conditional)
        {"key": "build_quality", "label": "Build",
         "score_a": a_higher[1], "score_b": a_higher[0],
         "delta_text": "PBT keycaps, metal frame", "confidence": "medium",
         "is_core": False},
    ]


# ---------------------------------------------------------------------------
# Test 1 — No standalone score numbers in output
# ---------------------------------------------------------------------------

class TestNoScoreNumbersInOutput:
    """Design § Decision 5 + dispatcher Test-1.4 case 1: the hero ring
    already shows the score. The verdict copy is text-only. A regex
    match on `\\d{2,3}` against the verdict (excluding factual units
    inherited from delta_text) must return empty.

    Important nuance: factual delta_text legitimately CONTAINS numbers
    ("BHD 30 less", "0.2 stars higher", "12g lighter"). Those are
    permitted in line 1 because they're inherited verbatim from
    delta_text. The ban is on the verdict ADDING score-style numbers
    (e.g. "scored 87" or "82/100"). We test this two ways: (a) the
    dispatcher's literal `\\d{2,3}` regex MAY match inherited "30" — so
    we don't use it as an absolute filter; (b) instead we ban
    score-pattern substrings the verdict could ADD.
    """

    def test_no_score_slash_100_pattern(self):
        v = build_factual_verdict(_make_scoring(_full_dim_set(True)), _products())
        assert "/100" not in v, f"verdict contains '/100' score pattern: {v!r}"
        assert "out of 100" not in v.lower(), v

    def test_no_two_three_digit_run_appears_outside_delta_text_units(self):
        """STRICT check: every 2-3 digit run in the verdict MUST be
        followed by a unit-bearing word (BHD, g, ms, stars/★, %, year,
        mAh, etc.). Bare "82" or "87" appearing as a score reference is
        rejected. Inherited delta_text contributions like "BHD 30 less"
        pass because "30" is followed by " less" within a phrase already
        sourced from delta_text."""
        v = build_factual_verdict(_make_scoring(_full_dim_set(True)), _products())
        for match in DIGIT_PATTERN.finditer(v):
            digit_run = match.group(0)
            # Look at the surrounding 30 chars for a unit-indicator.
            start = max(0, match.start() - 5)
            end = min(len(v), match.end() + 15)
            window = v[start:end].lower()
            unit_indicators = (
                "bhd", "$", " g ", "g ", "g,", "g.", "ms", "%", "year",
                "stars", "★", "mah", "less", "higher", "lighter", "lower",
                "vs", "more", "x", " kw", " m", "mhz", "ghz",
            )
            assert any(u in window for u in unit_indicators), (
                f"bare score-like digit {digit_run!r} appears in verdict "
                f"without a unit indicator in window: {window!r}\n"
                f"full verdict: {v!r}"
            )


# ---------------------------------------------------------------------------
# Test 2 — No banned evaluative words
# ---------------------------------------------------------------------------

class TestNoBannedEvaluativeWords:

    def test_verdict_contains_no_banned_word_on_full_dim_set(self):
        v = build_factual_verdict(_make_scoring(_full_dim_set(True)), _products())
        match = BANNED_PATTERN.search(v)
        assert match is None, (
            f"banned word '{match.group(0)}' in verdict: {v!r}"
        )

    def test_verdict_contains_no_banned_word_on_close_call(self):
        """Close margins must not tempt the builder into evaluative
        phrasing to break the tie."""
        dims = _full_dim_set(True)
        scoring = _make_scoring(dims, winner_idx=0)
        scoring["overall_score"]["product_a"] = 82
        scoring["overall_score"]["product_b"] = 81
        scoring["win_margin"] = 1
        v = build_factual_verdict(scoring, _products())
        assert BANNED_PATTERN.search(v) is None, (
            f"banned word in close-call verdict: {v!r}"
        )

    def test_arabic_lang_passes_same_deny_list(self):
        """Verdict generated with lang='ar' still must not contain the
        English banned tokens — the Arabic copy will use different
        words, but English deny-list substrings must NEVER appear
        even by accident (e.g. brand name "Best" wouldn't get through)."""
        v = build_factual_verdict(_make_scoring(_full_dim_set(True)),
                                  _products(), lang="ar")
        assert BANNED_PATTERN.search(v) is None, (
            f"english banned word in ar verdict: {v!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Inherits delta_text verbatim
# ---------------------------------------------------------------------------

class TestUsesDeltaTextDirectly:

    def test_top_3_winner_deltas_appear_in_verdict(self):
        """Design § Decision 5 line 297: line 1 = ", ".join(d.delta_text
        for d in top-3 winner deltas). Verdict must contain each."""
        dims = _full_dim_set(True)
        v = build_factual_verdict(_make_scoring(dims), _products())
        for core in (d for d in dims if d["is_core"]):
            assert core["delta_text"] in v, (
                f"delta_text {core['delta_text']!r} for '{core['key']}' missing "
                f"from verdict: {v!r}"
            )

    def test_no_paraphrasing_of_delta_text(self):
        """Inherits *delta_text* literally — does not e.g. rewrite "BHD
        30 less" as "30 dinar lower". We assert the exact substring."""
        dims = [
            {"key": "price", "label": "Price",
             "score_a": 95, "score_b": 75,
             "delta_text": "BHD 30 less", "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews",
             "score_a": 95, "score_b": 75,
             "delta_text": "0.2 stars higher", "confidence": "high", "is_core": True},
            {"key": "value", "label": "Value",
             "score_a": 95, "score_b": 75,
             "delta_text": "12g lighter", "confidence": "high", "is_core": True},
            {"key": "build_quality", "label": "Build",
             "score_a": 75, "score_b": 95,
             "delta_text": "PBT keycaps", "confidence": "medium", "is_core": False},
        ]
        v = build_factual_verdict(_make_scoring(dims), _products())
        # The exact factual substrings must be in the verdict — not
        # paraphrases like "30 less" or "lighter by 12g".
        assert "BHD 30 less" in v
        assert "0.2 stars higher" in v
        assert "12g lighter" in v


# ---------------------------------------------------------------------------
# Test 4 — Conditional alternative for runner-up
# ---------------------------------------------------------------------------

class TestConditionalAlternative:
    """Design § Decision 5 lines 299-301: line 2 is a conditional that
    names a runner-up dim and the runner-up product. Approved patterns
    (§ Decision 5 lines 277-279):
      - "If you want X, pick the first one"
      - "Pick the other one if Y matters more"
    """

    def test_line_2_starts_with_if_you(self):
        dims = _full_dim_set(True)
        v = build_factual_verdict(_make_scoring(dims), _products())
        # The verdict must contain the conditional opener. Look for it
        # case-insensitively (verdict might be split across sentences).
        assert re.search(r"\bif you (want|prefer|prioriti[sz]e|need)\b",
                         v, flags=re.IGNORECASE), (
            f"verdict missing conditional 'If you want/prefer/prioritize/need': {v!r}"
        )

    def test_line_2_mentions_runner_up_dimension_label(self):
        """The conditional alternative must reference a dim where the
        runner-up wins (per code sample line 299). With our fixture the
        runner-up wins build_quality ("PBT keycaps, metal frame"), so
        either the dim label "Build" or a token from delta_text should
        appear in the conditional."""
        dims = _full_dim_set(True)
        v = build_factual_verdict(_make_scoring(dims), _products())
        # Find the conditional clause (text after "If you …").
        m = re.search(r"\bif you [^.]+\.?", v, flags=re.IGNORECASE)
        assert m is not None, f"no conditional clause found: {v!r}"
        conditional_clause = m.group(0).lower()
        # Either dim label OR a token from delta_text must appear.
        assert ("build" in conditional_clause
                or "pbt" in conditional_clause
                or "metal" in conditional_clause
                or "keycap" in conditional_clause), (
            f"conditional doesn't reference runner-up dim: {conditional_clause!r}"
        )

    def test_line_2_names_runner_up_product(self):
        """Code sample line 300-301: the conditional names the runner-up
        product, NOT the top match. With winner_idx=0 (Glorious wins),
        line 2 must mention 'Ducky' (the runner-up brand)."""
        dims = _full_dim_set(True)
        v = build_factual_verdict(_make_scoring(dims, winner_idx=0), _products())
        # Find the conditional sentence.
        m = re.search(r"\bif you [^.]+", v, flags=re.IGNORECASE)
        assert m is not None
        clause = m.group(0)
        # "Ducky" (runner-up brand) must appear; "Glorious" (winner)
        # MAY also appear if the builder names both products — but the
        # runner-up name is required.
        assert "Ducky" in clause or "Ducky" in v.split(clause)[-1] if clause in v else "Ducky" in v, (
            f"runner-up brand 'Ducky' missing from conditional: {clause!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Distinct dim sets produce distinct verdicts (no template
# repetition across 4 phrasing variants)
# ---------------------------------------------------------------------------

class TestPhrasingVariants:
    """Per dispatcher Test-1.4 case "test 4 phrasing variants to ensure
    no template repetition": four DIFFERENT dim sets (different
    delta_texts and/or runner-up dims) must produce four DIFFERENT
    verdict strings — proving the builder is genuinely sourcing from
    inputs, not stamping a hard-coded template."""

    def _variant_dims(self, deltas: tuple[str, str, str], runner_dim_label: str,
                      runner_delta: str):
        return [
            {"key": "price", "label": "Price",
             "score_a": 95, "score_b": 75,
             "delta_text": deltas[0], "confidence": "high", "is_core": True},
            {"key": "reviews", "label": "Reviews",
             "score_a": 95, "score_b": 75,
             "delta_text": deltas[1], "confidence": "high", "is_core": True},
            {"key": "value", "label": "Value",
             "score_a": 95, "score_b": 75,
             "delta_text": deltas[2], "confidence": "high", "is_core": True},
            {"key": "build_quality", "label": runner_dim_label,
             "score_a": 75, "score_b": 95,
             "delta_text": runner_delta, "confidence": "medium",
             "is_core": False},
        ]

    def test_four_variants_produce_four_distinct_verdicts(self):
        variants = [
            (("BHD 30 less", "0.2 stars higher", "12g lighter"),
             "Build", "PBT keycaps"),
            (("BHD 5 less", "0.5 stars higher", "20g lighter"),
             "Battery", "70hr battery"),
            (("BHD 50 less", "0.1 stars higher", "8g lighter"),
             "Switches", "Cherry MX switches"),
            (("BHD 12 less", "0.3 stars higher", "15g lighter"),
             "Warranty", "5-year warranty"),
        ]
        verdicts = []
        for deltas, runner_label, runner_delta in variants:
            dims = self._variant_dims(deltas, runner_label, runner_delta)
            verdicts.append(
                build_factual_verdict(_make_scoring(dims), _products())
            )
        assert len(set(verdicts)) == 4, (
            f"variant verdicts collapsed — template repetition detected.\n"
            f"distinct count: {len(set(verdicts))} / 4\n"
            f"verdicts: {verdicts}"
        )


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-1.4 run:
#     python -m pytest tests/test_verdict_builder.py -v
#     → ModuleNotFoundError on `app.services.verdict_builder` → RED
#
# Post-Task-1.4: ~13 assertions across 5 test classes. Coverage target
# ≥80% on the new module.

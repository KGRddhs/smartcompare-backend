"""
Bundle E Task 1.1 RED — Pydantic v2 model contract for scoring_v2.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 1.1)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 2.

This module asserts the contract for `app.models.scoring_v2`:

  - `Dimension` — one row in the new self-describing dimensions[] array.
    Required: key, label, score_a, score_b, delta_text, confidence, is_core
    (7 fields). delta_text is validated against an evaluative-language
    deny-list (no "best", "great", "winner", "better", etc.) because
    the dimensions[] contract promises factual phrasing only.
  - `ScoringV2` — the top-level scoring payload with overall_score
    (per product, calibrated 70-95 per Decision 4), win_margin, and a
    dimensions list. Invariants:
      * AT LEAST 3 dimensions where is_core=True
      * Those 3 core dimensions MUST be exactly {"price", "reviews", "value"}
        per design § Decision 2 (these three are universal — every product
        has a price, reviews can be measured, value is derivable from
        the other two).
      * AT MOST 6 dimensions total (3 core + 0..3 contextual).

The banned-word list for delta_text is anchored at the 13 words Agent A
flagged in pre-read (logged 16:17 in the QA log):
  best, pick, excellent, great, recommend, winner, worst, better, worse,
  beats, smart, good, choose
Tests below probe a representative subset (best, great, recommend,
winner, better) — same enforcement, smaller surface.

RED→GREEN trajectory:
  - At HEAD (pre-Task-1.1): `app.models.scoring_v2` does not exist →
    ImportError → all 4 tests fail. Verified via pytest dry run before
    commit.
  - After Agent A implements scoring_v2.py: all 4 tests pass against
    the new Pydantic v2 module.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.scoring_v2 import Dimension, ScoringV2  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — construct a known-valid Dimension or ScoringV2 instance so each
# negative test only mutates ONE field. Keeps the "what made this raise?"
# blast radius small when something breaks.
# ---------------------------------------------------------------------------

def _valid_dimension_kwargs(**overrides):
    """All 7 required Dimension fields with factual delta_text."""
    base = {
        "key": "price",
        "label": "Price",
        "score_a": 88,
        "score_b": 72,
        "delta_text": "BHD 30 less",
        "confidence": "high",
        "is_core": True,
    }
    base.update(overrides)
    return base


def _core_dimensions():
    """The 3 required is_core=True dimensions per design § Decision 2."""
    return [
        Dimension(**_valid_dimension_kwargs(
            key="price", label="Price", delta_text="BHD 30 less"
        )),
        Dimension(**_valid_dimension_kwargs(
            key="reviews", label="Reviews",
            score_a=82, score_b=78,
            delta_text="0.2 stars higher",
        )),
        Dimension(**_valid_dimension_kwargs(
            key="value", label="Value",
            score_a=90, score_b=76,
            delta_text="More features per dinar",
        )),
    ]


def _valid_scoring_v2_kwargs(**overrides):
    base = {
        "overall_score": {"product_a": 87, "product_b": 82},
        "win_margin": 5,
        "dimensions": _core_dimensions(),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1 — Dimension required fields
# ---------------------------------------------------------------------------

class TestDimensionRequiredFields:
    """Pydantic must reject Dimension instantiation with missing required
    fields, and accept it with all 7 fields populated."""

    def test_all_seven_fields_construct_successfully(self):
        d = Dimension(**_valid_dimension_kwargs())
        assert d.key == "price"
        assert d.label == "Price"
        assert d.score_a == 88
        assert d.score_b == 72
        assert d.delta_text == "BHD 30 less"
        assert d.confidence == "high"
        assert d.is_core is True

    def test_missing_key_raises(self):
        kwargs = _valid_dimension_kwargs()
        del kwargs["key"]
        with pytest.raises(ValidationError) as exc_info:
            Dimension(**kwargs)
        # Pydantic v2 surfaces missing-required as type=missing on the
        # named field. Spot-check the loc.
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("key",) for err in errors), (
            f"expected missing-field error on 'key', got: {errors}"
        )

    def test_missing_score_a_raises(self):
        kwargs = _valid_dimension_kwargs()
        del kwargs["score_a"]
        with pytest.raises(ValidationError) as exc_info:
            Dimension(**kwargs)
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("score_a",) for err in errors), (
            f"expected missing-field error on 'score_a', got: {errors}"
        )

    def test_missing_delta_text_raises(self):
        kwargs = _valid_dimension_kwargs()
        del kwargs["delta_text"]
        with pytest.raises(ValidationError) as exc_info:
            Dimension(**kwargs)
        errors = exc_info.value.errors()
        assert any(err["loc"] == ("delta_text",) for err in errors), (
            f"expected missing-field error on 'delta_text', got: {errors}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Evaluative-language validator on delta_text
# ---------------------------------------------------------------------------

class TestEvaluativeLanguageValidator:
    """delta_text must be factual. Evaluative words ('best', 'great',
    'recommend', 'winner', 'better', etc.) raise ValidationError. The
    error message must cite the offending word so backend logs are
    actionable."""

    @pytest.mark.parametrize(
        ("delta_text", "expected_word"),
        [
            ("It's the best", "best"),
            ("great value", "great"),
            ("we recommend it", "recommend"),
            ("winner here", "winner"),
            ("better build", "better"),
        ],
    )
    def test_evaluative_phrases_rejected_with_word_cited(
        self, delta_text: str, expected_word: str
    ):
        with pytest.raises(ValidationError) as exc_info:
            Dimension(**_valid_dimension_kwargs(delta_text=delta_text))
        # The validator must name the offending word in its error message
        # — string match on the rendered ValidationError. Pydantic v2
        # renders custom-validator messages under "ctx.error" or the
        # generic "Value error, <msg>" prefix; both forms include the
        # original message text.
        rendered = str(exc_info.value)
        assert expected_word in rendered.lower(), (
            f"expected '{expected_word}' to be cited in error, got: {rendered}"
        )

    def test_factual_delta_text_accepted(self):
        """The example phrase from design § Decision 2."""
        d = Dimension(**_valid_dimension_kwargs(delta_text="BHD 30 less"))
        assert d.delta_text == "BHD 30 less"

    def test_factual_delta_text_with_units_accepted(self):
        """Star-rating + gram weight phrases from design § Decision 3."""
        for factual in [
            "0.2 stars higher",
            "12g lighter",
            "30% lower price",
        ]:
            d = Dimension(**_valid_dimension_kwargs(delta_text=factual))
            assert d.delta_text == factual

    def test_evaluative_check_is_case_insensitive(self):
        """Capitalized 'Best' must still be caught — a sentence-initial
        'Best in class' is just as evaluative as lowercase 'best'."""
        with pytest.raises(ValidationError) as exc_info:
            Dimension(**_valid_dimension_kwargs(delta_text="Best in class"))
        assert "best" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 3 — At least 3 core dimensions, with the EXACT set {price, reviews,
# value}
# ---------------------------------------------------------------------------

class TestAtLeast3CoreDimensions:
    """ScoringV2 requires exactly the 3 universal core dimensions:
    price, reviews, value (design § Decision 2). Fewer than 3 cores OR a
    substitution (e.g. 'popularity' in place of 'value') must raise."""

    def test_three_canonical_core_dimensions_pass(self):
        sv = ScoringV2(**_valid_scoring_v2_kwargs())
        assert len(sv.dimensions) == 3
        assert sum(1 for d in sv.dimensions if d.is_core) == 3
        core_keys = {d.key for d in sv.dimensions if d.is_core}
        assert core_keys == {"price", "reviews", "value"}

    def test_one_core_dimension_raises(self):
        one_core = [
            Dimension(**_valid_dimension_kwargs(
                key="price", label="Price", delta_text="BHD 30 less"
            )),
        ]
        with pytest.raises(ValidationError):
            ScoringV2(**_valid_scoring_v2_kwargs(dimensions=one_core))

    def test_two_core_dimensions_raises(self):
        two_cores = _core_dimensions()[:2]  # price + reviews only
        with pytest.raises(ValidationError):
            ScoringV2(**_valid_scoring_v2_kwargs(dimensions=two_cores))

    def test_substituting_value_with_popularity_raises(self):
        """Even with 3 is_core=True dimensions, the SET must be exactly
        {price, reviews, value}. Swapping 'value' for 'popularity' (or
        any other key) must fail — value is universally derivable, the
        others are contextual."""
        swapped = [
            Dimension(**_valid_dimension_kwargs(
                key="price", label="Price", delta_text="BHD 30 less"
            )),
            Dimension(**_valid_dimension_kwargs(
                key="reviews", label="Reviews",
                score_a=82, score_b=78, delta_text="0.2 stars higher",
            )),
            Dimension(**_valid_dimension_kwargs(
                key="popularity", label="Popularity",  # ← substituted
                score_a=70, score_b=65, delta_text="1200 reviews vs 800",
            )),
        ]
        with pytest.raises(ValidationError):
            ScoringV2(**_valid_scoring_v2_kwargs(dimensions=swapped))


# ---------------------------------------------------------------------------
# Test 4 — Max 8 dimensions (3 core + 0..5 contextual)
# ---------------------------------------------------------------------------
# S2 I3.4 (Decision A, ratified 2026-06-11): cap raised 6→8 so electronics
# surfaces ecosystem + futureproof contextual rows. FE already supports
# (HERO_CAP=4 + expander). Boundary moved: 8 pass, 9 raises.

class TestMax8Dimensions:
    """ScoringV2 caps dimensions[] at 8 — 3 universal core + up to 5
    contextual extras (build, popularity, category-specific)."""

    def test_eight_dimensions_pass(self):
        dims = _core_dimensions() + [
            Dimension(**_valid_dimension_kwargs(
                key="build_quality", label="Build",
                score_a=80, score_b=88,
                delta_text="PBT keycaps, metal frame",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="popularity", label="Popularity",
                score_a=70, score_b=65,
                delta_text="1200 reviews vs 800",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="dpi", label="DPI",
                score_a=85, score_b=78,
                delta_text="16000 DPI vs 12000 DPI",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="ecosystem", label="Ecosystem",
                score_a=90, score_b=65,
                delta_text="3 first-party accessories vs 1",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="futureproof", label="Future-proofing",
                score_a=78, score_b=82,
                delta_text="4 years of OS updates vs 5",
                is_core=False,
            )),
        ]
        sv = ScoringV2(**_valid_scoring_v2_kwargs(dimensions=dims))
        assert len(sv.dimensions) == 8

    def test_six_dimensions_still_pass(self):
        """The pre-S2 6-dim shape must remain valid (it's a subset of 8)."""
        dims = _core_dimensions() + [
            Dimension(**_valid_dimension_kwargs(
                key="build_quality", label="Build",
                score_a=80, score_b=88,
                delta_text="PBT keycaps, metal frame",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="popularity", label="Popularity",
                score_a=70, score_b=65,
                delta_text="1200 reviews vs 800",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="dpi", label="DPI",
                score_a=85, score_b=78,
                delta_text="16000 DPI vs 12000 DPI",
                is_core=False,
            )),
        ]
        sv = ScoringV2(**_valid_scoring_v2_kwargs(dimensions=dims))
        assert len(sv.dimensions) == 6

    def test_nine_dimensions_raises(self):
        dims = _core_dimensions() + [
            Dimension(**_valid_dimension_kwargs(
                key="build_quality", label="Build",
                score_a=80, score_b=88,
                delta_text="PBT keycaps, metal frame",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="popularity", label="Popularity",
                score_a=70, score_b=65,
                delta_text="1200 reviews vs 800",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="dpi", label="DPI",
                score_a=85, score_b=78,
                delta_text="16000 DPI vs 12000 DPI",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="ecosystem", label="Ecosystem",
                score_a=90, score_b=65,
                delta_text="3 first-party accessories vs 1",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="futureproof", label="Future-proofing",
                score_a=78, score_b=82,
                delta_text="4 years of OS updates vs 5",
                is_core=False,
            )),
            Dimension(**_valid_dimension_kwargs(
                key="warranty", label="Warranty",
                score_a=82, score_b=88,
                delta_text="2 year vs 1 year",
                is_core=False,
            )),
        ]
        with pytest.raises(ValidationError):
            ScoringV2(**_valid_scoring_v2_kwargs(dimensions=dims))


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-1.1 run:
#     python -m pytest tests/test_scoring_v2_models.py -v
#     → ImportError on `app.models.scoring_v2` (module does not exist)
#     → 0 tests collected, 1 collection error → RED
#
# Post-Task-1.1 (Agent A commits scoring_v2.py):
#     → 4 test classes / ~14 individual assertions GREEN
#     → re-verify here; post SIGN-OFF with coverage % from
#       `pytest tests/test_scoring_v2_models.py --cov=app.models.scoring_v2`

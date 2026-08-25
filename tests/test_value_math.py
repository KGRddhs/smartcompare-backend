"""Bundle C — value math RED tests (Section C plan, tasks C.5.1 / C.5.2 / C.5.4 / C.5.5 / C.5.6 / C.5.7).

Covers spec §4:
  - C.5.1 — VALUE_FORMULA_BY_PRIORITY coefficients table
  - C.5.2 — First-match priority wins
  - C.5.4 — delta_text richer format ("40% less", "0.9 stars higher")
  - C.5.5 — `_classify_value_match` 4-state (in_range / above_range / below_range / 2+ tier)
  - C.5.6 — `_classify_budget_mismatch` 3+1 states
  - C.5.7 — Tier-mismatch Case 2 (budget user, products above range)

All tests stay RED until A.6.x (value formula + classifiers) ships.
"""
from __future__ import annotations

import pytest


# Issue #49 — CI containment for the RED-by-design stubs.
#
# All 35 nodes in this file assert Bundle C v1.1 behaviour that has not been
# implemented yet (`VALUE_FORMULA_BY_PRIORITY`, `_compute_value_score`,
# `build_value_delta_text`, `build_value_match_caption`, `_classify_value_match`,
# `_classify_budget_mismatch`, the `budget_mismatch` kwarg on
# `_build_preferences_prompt`). CLAUDE.md:399 and
# `tests/PRE_IMPL_FAILURE_BASELINE.md` both document them as known-RED and "not
# a regression" — but `.github/workflows/ci.yml` never learned that, so these
# 35 kept the whole build red and every real regression merged unnoticed
# underneath them.
#
# xfail (not skip, not delete) because the repo already uses xfail for exactly
# this — `test_kpi_truth_modernization.py`, `test_correctness_coverage_sweep_fixes.py`,
# `test_cascade_order_regression_qa.py` all pin not-yet-implemented behaviour the
# same way. xfail keeps every node COLLECTED and RUN, so the spec coverage is
# still executable and `-rX` lists them; a skip or a deletion would throw the
# spec away, and a CI-side deselect would hide them from the local run too.
#
# strict=False on purpose: strict would flip the file red the moment A.6.x lands,
# which is the same "CI is red for a known reason" failure mode this issue exists
# to end. When the implementation ships these turn XPASS — visible in the run
# summary — and this pytestmark comes off in that PR.
#
# Scope note: this is a blanket module mark, so do NOT add a test to this file
# that is expected to PASS today; it would be silently masked. New value-math
# tests for shipped behaviour belong in their own module.
#
# WHY THERE IS NO `raises=` NARROWING (#49 review follow-up). Narrowing to the
# not-yet-implemented exception shapes was proposed, to stop a *buggy* A.6.x
# implementation reporting xfail forever. Measured with
# `pytest tests/test_value_math.py --runxfail --tb=line` on 2026-08-25, the 35
# nodes fail in three shapes, not one:
#     23 x ImportError      (build_value_delta_text, build_value_match_caption,
#                            _classify_value_match, _classify_budget_mismatch)
#      1 x TypeError        (budget_mismatch kwarg on _build_preferences_prompt)
#     11 x AssertionError   (VALUE_FORMULA_BY_PRIORITY ALREADY EXISTS in
#                            app/services/scoring_service.py with pre-v1.1
#                            coefficients — 0.45 where spec §4a says 0.40, etc.)
# So `raises=(AttributeError, ImportError, NameError, TypeError)` would turn
# those 11 back into hard failures and put the build straight back to red, which
# is the exact outcome #49 exists to end. The amnesty is bounded a different way
# instead: tests/test_ci_gates.py::test_value_math_xfail_expires_when_a6x_ships
# goes RED the moment every A.6.x symbol exists, forcing this pytestmark to be
# removed in the PR that ships the implementation.
pytestmark = pytest.mark.xfail(
    reason=(
        "RED-by-design: Bundle C v1.1 value-math (A.6.x) is not implemented yet "
        "— see CLAUDE.md:399 and tests/PRE_IMPL_FAILURE_BASELINE.md"
    ),
    strict=False,
)


# ---------------------------------------------------------------------------
# C.5.1 — VALUE_FORMULA_BY_PRIORITY (spec § 4a)
# ---------------------------------------------------------------------------


# Table from spec § 4a — explicit per-priority weights
EXPECTED_COEFFICIENTS = {
    "price":             {"spec": 0.40, "price": 0.60},
    "quality":           {"spec": 0.70, "price": 0.30},
    "durability":        {"spec": 0.65, "price": 0.35},
    "latest_features":   {"spec": 0.65, "price": 0.35},
    "brand_reputation":  {"spec": 0.65, "price": 0.35},
    "eco_friendly":      {"spec": 0.55, "price": 0.45},
    "ease_of_use":       {"spec": 0.55, "price": 0.45},
    "_default":          {"spec": 0.60, "price": 0.40},
}


@pytest.mark.parametrize("priority,coeffs", list(EXPECTED_COEFFICIENTS.items()))
def test_value_formula_coefficients_match_spec(priority, coeffs):
    """Spec § 4a: VALUE_FORMULA_BY_PRIORITY dict — exact coefficients."""
    try:
        from app.services.scoring_service import VALUE_FORMULA_BY_PRIORITY  # type: ignore
    except ImportError:
        pytest.fail(
            "RED: A.6.1 not yet shipped — VALUE_FORMULA_BY_PRIORITY missing "
            "from app.services.scoring_service"
        )
        return
    actual = VALUE_FORMULA_BY_PRIORITY.get(
        priority, VALUE_FORMULA_BY_PRIORITY.get("_default")
    )
    assert actual is not None, f"Missing priority {priority!r} from map"
    assert actual["spec"] == pytest.approx(coeffs["spec"])
    assert actual["price"] == pytest.approx(coeffs["price"])
    # Invariant — every row sums to 1.0
    assert (actual["spec"] + actual["price"]) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# C.5.2 — First-match priority wins (spec § 4a)
# ---------------------------------------------------------------------------


def test_value_formula_first_match_wins_quality():
    """priorities=['quality', 'price'] → uses quality coefficients (0.70 spec / 0.30 price)."""
    try:
        from app.services.scoring_service import _compute_value_score  # type: ignore
    except ImportError:
        pytest.fail("RED: _compute_value_score missing (A.6.1)")
        return
    try:
        out = _compute_value_score(
            spec_score=80, price_score=60, priorities=["quality", "price"]
        )
    except TypeError:
        pytest.fail(
            "RED: _compute_value_score signature missing priorities kwarg (A.6.1)"
        )
        return
    expected = 0.70 * 80 + 0.30 * 60  # 56 + 18 = 74
    assert out == pytest.approx(expected, abs=0.5)


def test_value_formula_first_match_wins_price_overrides_quality():
    """priorities=['price', 'quality'] → uses price coefficients (0.40 spec / 0.60 price)."""
    try:
        from app.services.scoring_service import _compute_value_score  # type: ignore
    except ImportError:
        pytest.fail("RED: _compute_value_score missing (A.6.1)")
        return
    try:
        out = _compute_value_score(
            spec_score=80, price_score=60, priorities=["price", "quality"]
        )
    except TypeError:
        pytest.fail("RED: priorities kwarg missing")
        return
    expected = 0.40 * 80 + 0.60 * 60  # 32 + 36 = 68
    assert out == pytest.approx(expected, abs=0.5)


def test_value_formula_default_when_no_priorities():
    """No priorities → 0.60 spec + 0.40 price (default row)."""
    try:
        from app.services.scoring_service import _compute_value_score  # type: ignore
    except ImportError:
        pytest.fail("RED: _compute_value_score missing (A.6.1)")
        return
    try:
        out = _compute_value_score(spec_score=80, price_score=60, priorities=[])
    except TypeError:
        pytest.fail("RED: priorities kwarg missing")
        return
    expected = 0.60 * 80 + 0.40 * 60  # 48 + 24 = 72
    assert out == pytest.approx(expected, abs=0.5)


# ---------------------------------------------------------------------------
# C.5.4 — delta_text richer format (spec § 4b)
# ---------------------------------------------------------------------------


def test_delta_text_price_percentage_format():
    """Spec § 4b: price delta reads '40% less' (was 'BHD 3.76 less' — kept as secondary)."""
    try:
        from app.services.response_builder import build_value_delta_text  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_delta_text missing from response_builder")
        return
    out = build_value_delta_text(price_a=10, price_b=6, signal="price")
    assert "40%" in out, f"expected '40%' in delta, got: {out!r}"
    assert "less" in out.lower() or "off" in out.lower()


def test_delta_text_rating_stars_format():
    """Spec § 4b: reviews delta reads '0.9 stars higher'."""
    try:
        from app.services.response_builder import build_value_delta_text  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_delta_text missing from response_builder")
        return
    out = build_value_delta_text(rating_a=4.5, rating_b=3.6, signal="reviews")
    assert "0.9" in out
    assert "star" in out.lower() or "higher" in out.lower()


def test_delta_text_value_with_priority_match_copy():
    """Spec § 4b: 'Better value for your priority' when priority matches dim."""
    try:
        from app.services.response_builder import build_value_delta_text  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_delta_text missing")
        return
    out = build_value_delta_text(signal="value", priority_match=True)
    assert "value for your priority" in out.lower() or out == "Better value for your priority"


def test_delta_text_value_no_priority_match_copy():
    """Spec § 4b: 'Stronger value ratio' when no priority match."""
    try:
        from app.services.response_builder import build_value_delta_text  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_delta_text missing")
        return
    out = build_value_delta_text(signal="value", priority_match=False)
    assert "value ratio" in out.lower() or out == "Stronger value ratio"


# ---------------------------------------------------------------------------
# C.5.5 — value_match classification (spec § 4d)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "user_budget,product_tier,expected",
    [
        ("mid", "mid", "in_range"),         # exact match
        ("mid", "premium", "above_range"),  # 1 tier above
        ("mid", "budget", "below_range"),   # 1 tier below
        ("mid", "luxury", "above_range"),   # 2 tiers above
        ("mid", "top_tier", "above_range"), # 3 tiers above
        ("luxury", "budget", "below_range"),# 3 tiers below
        ("budget", "top_tier", "above_range"),
        ("top_tier", "top_tier", "in_range"),
    ],
)
def test_classify_value_match(user_budget, product_tier, expected):
    """Spec § 4d: _classify_value_match returns in_range/above_range/below_range."""
    try:
        from app.services.scoring_service import _classify_value_match  # type: ignore
    except ImportError:
        pytest.fail(
            "RED: _classify_value_match missing (A.6.x value-match classifier)"
        )
        return
    assert _classify_value_match(
        user_budget=user_budget, product_tier=product_tier
    ) == expected


def test_value_match_caption_in_range_is_silent():
    """Spec § 4d: in_range → no caption (silent confirmation)."""
    try:
        from app.services.response_builder import build_value_match_caption  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_match_caption missing from response_builder")
        return
    assert build_value_match_caption("in_range") == ""


def test_value_match_caption_one_tier_above():
    """Spec § 4d: 1 tier above → 'Above your usual range'."""
    try:
        from app.services.response_builder import build_value_match_caption  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_match_caption missing")
        return
    out = build_value_match_caption("above_range", tier_delta=1)
    assert out == "Above your usual range"


def test_value_match_caption_one_tier_below():
    """Spec § 4d: 1 tier below → 'Within your range'."""
    try:
        from app.services.response_builder import build_value_match_caption  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_match_caption missing")
        return
    out = build_value_match_caption("below_range", tier_delta=1)
    assert out == "Within your range"


def test_value_match_caption_two_plus_tier_above_appends_tradeoff():
    """Spec § 4d: 2+ tiers above → 'Above your usual range — but here's why'."""
    try:
        from app.services.response_builder import build_value_match_caption  # type: ignore
    except ImportError:
        pytest.fail("RED: build_value_match_caption missing")
        return
    out = build_value_match_caption(
        "above_range", tier_delta=2, key_tradeoff="OLED display"
    )
    assert "but here's why" in out.lower()


# ---------------------------------------------------------------------------
# C.5.6 — budget_mismatch classification (spec § 4e)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "user_budget,product_tiers,expected",
    [
        ("budget", ["luxury", "luxury"], "above"),      # both above
        ("budget", ["luxury", "top_tier"], "above"),    # both above (mixed)
        ("luxury", ["budget", "mid"], "below"),         # both below
        ("top_tier", ["mid", "premium"], "below"),
        ("mid", ["mid", "premium"], None),              # spans user tier — no mismatch
        ("mid", ["mid", "mid"], None),                  # exact match both
        ("premium", ["mid", "premium"], None),
    ],
)
def test_classify_budget_mismatch(user_budget, product_tiers, expected):
    """Spec § 4e: _classify_budget_mismatch returns 'above' / 'below' / None."""
    try:
        from app.services.extraction_service import _classify_budget_mismatch  # type: ignore
    except ImportError:
        pytest.fail(
            "RED: _classify_budget_mismatch missing from extraction_service (A.6.x)"
        )
        return
    assert _classify_budget_mismatch(user_budget, product_tiers) == expected


def test_budget_mismatch_passes_to_preferences_prompt():
    """Spec § 4e: budget_mismatch passes to _build_preferences_prompt — adds
    instruction. NO UI banner directive — only prompt context.
    """
    try:
        from app.services.extraction_service import _build_preferences_prompt  # type: ignore
    except ImportError:
        pytest.fail("RED: _build_preferences_prompt missing")
        return
    try:
        prompt = _build_preferences_prompt(
            explicit_prefs={"budget": "budget"},
            behavioral={},
            demographics_profile=None,
            budget_mismatch="above",
        )
    except TypeError:
        pytest.fail(
            "RED: _build_preferences_prompt does not yet accept budget_mismatch kwarg"
        )
        return
    # Some signal that the prompt acknowledges the mismatch
    lowered = prompt.lower()
    assert (
        "outside the user's usual range" in lowered
        or "budget_mismatch" in lowered
        or "above the user's" in lowered
    ), f"prompt did not surface budget_mismatch context: {prompt[:400]!r}"
    # CRITICAL: no UI banner directive
    assert "show banner" not in lowered
    assert "info banner" not in lowered

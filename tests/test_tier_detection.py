"""Bundle C — tier detection RED tests (Section C plan, tasks C.4.3 / C.4.4 / C.4.5).

Companion to `tests/test_price_tiers_by_category.py` (per-category breakpoint
tests landed by backend during A.5.1). This file covers the design-spec cases
NOT in that file:

  - C.4.3 — Pydantic `BudgetValue` Literal accepts 5 values (spec § 3b/3d).
  - C.4.4 — `_detect_other_subscale` + `_detect_price_tier(comparison_prices=...)`
    geometric-mean sub-scale resolution (spec § 3f).
  - C.4.5 — Spec § 3f car-comparison exact example
    (5000 + 6000 BHD → other_ultra → both 'mid').

Some tests stay RED until A.5.5 (other-category geometric-mean) ships.
"""
from __future__ import annotations

import math

import pytest

# ---------------------------------------------------------------------------
# C.4.3 — Pydantic BudgetValue Literal — 5-tier extension (spec § 3b/3d)
# ---------------------------------------------------------------------------


def _make_prefs(**overrides):
    """Build a valid UserPreferencesRequest payload, overriding any field."""
    base = {
        "priorities": ["quality"],
        "budget": "mid",
        "lifestyle": [],
        "brand_attitude": "function_first",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "val,should_pass",
    [
        ("budget", True),
        ("mid", True),
        ("premium", True),
        ("luxury", True),
        ("top_tier", True),
        # invalid values must fail validation
        ("free", False),
        ("ultra_luxury", False),
        ("", False),
        ("MID", False),  # case-sensitive
    ],
)
def test_budget_value_validator_accepts_5_tiers(val, should_pass):
    """Spec § 3b/3d: budget validator extended to 5 values; legacy 3 still pass."""
    pytest.importorskip("pydantic")
    from pydantic import ValidationError

    from app.api.auth_routes import UserPreferencesRequest

    if should_pass:
        try:
            UserPreferencesRequest(**_make_prefs(budget=val))
        except ValidationError as exc:  # RED if A.5.4 not yet shipped
            pytest.fail(f"Validator rejected {val!r}: {exc}")
    else:
        with pytest.raises(ValidationError):
            UserPreferencesRequest(**_make_prefs(budget=val))


def test_legacy_3tier_values_still_valid_for_backwards_compat():
    """Spec § 3d: API still accepts old 3-tier values for older clients."""
    pytest.importorskip("pydantic")
    from app.api.auth_routes import UserPreferencesRequest

    for legacy in ("budget", "mid", "premium"):
        UserPreferencesRequest(**_make_prefs(budget=legacy))


def test_valid_budget_enum_exposes_5_tiers():
    """Belt-and-braces: the VALID_BUDGET source-of-truth list contains all 5 tiers."""
    from app.api.auth_routes import VALID_BUDGET

    assert set(VALID_BUDGET) == {"budget", "mid", "premium", "luxury", "top_tier"}


# ---------------------------------------------------------------------------
# C.4.4 — `other` category geometric-mean sub-scale detection (spec § 3f)
# ---------------------------------------------------------------------------


# Spec § 3f sub-scale ranges:
#   other_light  : gm < 30        → budget <11 / mid 11–57   / premium 57–189   / luxury 189–500    / top_tier 500+
#   other_mid    : 30 ≤ gm < 300  → budget <30 / mid 30–120  / premium 120–400  / luxury 400–1000   / top_tier 1000+
#   other_high   : 300 ≤ gm < 5000 → budget <300/ mid 300–1500/ premium 1500–5000/ luxury 5000–15000 / top_tier 15000+
#   other_ultra  : gm ≥ 5000      → budget <5000/ mid 5000–15000/ premium 15000–40000/ luxury 40000–100000/ top_tier 100000+


@pytest.mark.parametrize(
    "p1,p2,expected_subscale",
    [
        (5, 10, "other_light"),       # gm ~7.07 < 30
        (20, 25, "other_light"),       # gm ~22.36 < 30
        (50, 100, "other_mid"),        # gm ~70.7 in [30, 300)
        (200, 300, "other_mid"),       # gm ~244 in [30, 300)
        (500, 2000, "other_high"),     # gm ~1000 in [300, 5000)
        (1000, 1000, "other_high"),    # gm = 1000 in [300, 5000)
        (5000, 8000, "other_ultra"),   # gm ~6324 ≥ 5000
        (10000, 50000, "other_ultra"), # gm ~22360 ≥ 5000
    ],
)
def test_other_subscale_from_geometric_mean(p1, p2, expected_subscale):
    """Spec § 3f: gm = sqrt(p1 * p2) decides sub-scale.

    RED until A.5.5 lands `_detect_other_subscale`.
    """
    try:
        from app.services.scoring_service import _detect_other_subscale  # type: ignore
    except ImportError:
        pytest.fail(
            "RED: A.5.5 not yet shipped — _detect_other_subscale missing from "
            "app.services.scoring_service"
        )
        return
    assert _detect_other_subscale(p1, p2) == expected_subscale


@pytest.mark.parametrize(
    "p1,p2,tier_p1,tier_p2",
    [
        # Snack comparison: 2 + 4 BHD → gm ~2.83 → other_light
        # other_light: budget <11 → both budget.
        (2, 4, "budget", "budget"),
        # Mid-range stuff: 100 + 200 BHD → gm ~141 → other_mid
        # other_mid: 100 in mid (30–120), 200 in premium (120–400)
        (100, 200, "mid", "premium"),
        # Car comparison from spec § 3f: 5000 + 6000 BHD → gm ~5477 → other_ultra
        # other_ultra: budget <5000 → 5000 in mid, 6000 in mid
        (5000, 6000, "mid", "mid"),
        # High-end pair: 20000 + 30000 → gm ~24494 → other_ultra → premium/premium
        (20000, 30000, "premium", "premium"),
    ],
)
def test_detect_price_tier_other_with_comparison_prices(p1, p2, tier_p1, tier_p2):
    """Spec § 3f: _detect_price_tier(price, 'other', comparison_prices=[..]) derives
    sub-scale from gm. RED until A.5.5 wires `comparison_prices` parameter.
    """
    from app.services.scoring_service import _detect_price_tier

    try:
        a = _detect_price_tier(p1, "other", comparison_prices=[p1, p2])
        b = _detect_price_tier(p2, "other", comparison_prices=[p1, p2])
    except TypeError:
        pytest.fail(
            "RED: A.5.5 not yet shipped — _detect_price_tier does not accept "
            "comparison_prices kwarg"
        )
        return
    assert a == tier_p1, f"product 1 ({p1} BHD) expected tier {tier_p1}, got {a}"
    assert b == tier_p2, f"product 2 ({p2} BHD) expected tier {tier_p2}, got {b}"


def test_other_category_no_comparison_prices_falls_back_to_other_light():
    """Spec § 3f: When comparison_prices=None and category='other',
    falls back to other_light sub-scale silently (already covered for legacy
    one-arg calls in tests/test_price_tiers_by_category.py — this is the
    explicit 'other' category path).
    """
    from app.services.scoring_service import _detect_price_tier

    # other_light: budget <11 → 5 BHD is budget
    assert _detect_price_tier(5, "other") == "budget"
    # other_light: 30 in mid (11–57)
    assert _detect_price_tier(30, "other") == "mid"


# ---------------------------------------------------------------------------
# C.4.5 — Spec § 3f car case full math path
# ---------------------------------------------------------------------------


def test_car_comparison_geometric_mean_value_matches_design_doc():
    """Sanity: design doc says 5000 + 6000 cars → gm ~5477. Verify our math."""
    p1, p2 = 5000.0, 6000.0
    gm = math.sqrt(p1 * p2)
    # 5477.225575051661
    assert 5476 < gm < 5478, f"geometric mean off: {gm}"
    # And gm ≥ 5000 → other_ultra (per spec § 3f)
    assert gm >= 5000


def test_car_comparison_spec_example_end_to_end():
    """Spec § 3f exact example: 5000 + 6000 BHD cars → both 'mid' in other_ultra.

    User searching "budget" + cars in this range gets the cheapest car's value
    lift via math (covered separately in tests/test_value_math.py once §4e ships).
    """
    from app.services.scoring_service import _detect_price_tier

    p1, p2 = 5000, 6000
    try:
        a = _detect_price_tier(p1, "other", comparison_prices=[p1, p2])
        b = _detect_price_tier(p2, "other", comparison_prices=[p1, p2])
    except TypeError:
        pytest.fail("RED: A.5.5 comparison_prices kwarg not yet implemented")
        return
    assert a == "mid"
    assert b == "mid"

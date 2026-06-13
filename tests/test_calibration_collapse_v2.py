"""S3 L3 v2 — CALIBRATION-COLLAPSE wrong-winner fix [gate finding A, HIGH].

The FE derives the winner SOLELY from scoring_v2.overall_score.product_a vs
product_b (ResultsScreen.tsx `(product_a>=product_b)?0:1`), never reads
winner_idx. But _build_scoring_v2 calibrates each independently via
calibrate_score = int(round(70+(raw-50)*0.5)), and the 0.5×+int rounding
COLLAPSES any sub-~2pt raw gap to product_a==product_b → the FE `>=` crowns
product_0 even when winner_index=1, splitting the hero ring from the verdict/
evidence/name. v2 (A1 band 45-85 + magnitude-awareness near-ties + ±4 authority)
makes the collapse the MODAL outcome.

FIX: _build_scoring_v2 enforces argmax(product_a, product_b) == winner_index —
the LOSER is nudged strictly below the winner (clamp to band floor 60). The
winner keeps its honest calibrated score; the displayed pair, winner_idx, eval,
and all surfaces now agree. Backend-only, zero FE change.
"""
import pytest

from app.services.response_builder import _build_scoring_v2


def _products():
    return [
        {"name": "A", "category": "electronics",
         "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.5, "review_count": 900, "specs": {"ram": "8 GB"}},
        {"name": "B", "category": "electronics",
         "price": {"amount": 305, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.4, "review_count": 800, "specs": {"ram": "8 GB"}},
    ]


def _sr(raw_a, raw_b, winner_index):
    return {"scores": {"product_0": {"overall": raw_a, "breakdown": {}},
                       "product_1": {"overall": raw_b, "breakdown": {}}},
            "winner_index": winner_index, "win_margin": abs(raw_a - raw_b)}


def test_subpoint_gap_winner1_displays_product_b_higher():
    """raw 72.0 / 72.6 (winner_index=1) — pre-fix both calibrate to 81 (tie) and
    the FE crowns product_0. Post-fix: product_b strictly > product_a so the FE
    `>=` agrees with winner_index=1."""
    sv2 = _build_scoring_v2(_products(), _sr(72.0, 72.6, 1), "electronics", 1)
    a = sv2["overall_score"]["product_a"]
    b = sv2["overall_score"]["product_b"]
    assert b > a, f"winner_index=1 must display product_b > product_a, got a={a} b={b}"
    assert sv2["overall_score"]["winner_idx"] == 1


def test_subpoint_gap_winner0_displays_product_a_higher():
    """Symmetric: raw 72.6 / 72.0 (winner_index=0) → product_a strictly > product_b."""
    sv2 = _build_scoring_v2(_products(), _sr(72.6, 72.0, 0), "electronics", 0)
    a = sv2["overall_score"]["product_a"]
    b = sv2["overall_score"]["product_b"]
    assert a > b, f"winner_index=0 must display product_a > product_b, got a={a} b={b}"


def test_converted_usd_close_call_displays_consistently():
    """The converted_usd authority case: raw 53.0 / 55.0 (winner_index=1) — both
    pre-fix calibrate to 72. Post-fix product_b > product_a."""
    sv2 = _build_scoring_v2(_products(), _sr(53.0, 55.0, 1), "electronics", 1)
    assert sv2["overall_score"]["product_b"] > sv2["overall_score"]["product_a"]


def test_winner_keeps_honest_calibrated_score():
    """The WINNER's calibrated score is unchanged (the honest value); only the
    LOSER is nudged below it. winner=product_0 with raw 72.6 → its calibrated 81
    stays; product_1 is pushed strictly below 81."""
    from app.services.scoring_service import calibrate_score
    sv2 = _build_scoring_v2(_products(), _sr(72.6, 72.0, 0), "electronics", 0)
    assert sv2["overall_score"]["product_a"] == calibrate_score(72.6)  # winner honest
    assert sv2["overall_score"]["product_b"] < sv2["overall_score"]["product_a"]


def test_loser_clamped_to_band_floor():
    """The nudged loser never drops below the calibration band floor (60)."""
    # Winner at the floor: raw such that calibrate→60, loser must stay >=60 but < winner.
    sv2 = _build_scoring_v2(_products(), _sr(10.0, 9.0, 0), "electronics", 0)
    b = sv2["overall_score"]["product_b"]
    assert b >= 60, f"loser must not drop below band floor 60, got {b}"


def test_floor_edge_winner1_both_calibrate_to_floor_raises_winner():
    """[gate re-review — A floor-edge hole] winner_index=1 with BOTH raw → the
    calibration FLOOR (60). The loser-nudge `max(60, min(60, 59)) = 60` can't
    separate at the floor → 60/60 tie → FE `>=` crowns product_0 (the LOSER).
    calibrate is monotonic so the floor is the ONE sub-case the loser-lower
    can't fix. Unreachable on default flags (A1 → overall ≥~41 → calibrated
    ≥~66), but DISABLE_DIM_NORM_DAMPENING's legacy 30-100 band reaches it. FIX:
    RAISE the winner above the loser when the winner sits at/below the floor.
    """
    # raw 30 → 70+(30-50)*0.5 = 60 (the floor) for BOTH; winner_index=1.
    sv2 = _build_scoring_v2(_products(), _sr(30.0, 30.0, 1), "electronics", 1)
    a = sv2["overall_score"]["product_a"]
    b = sv2["overall_score"]["product_b"]
    assert b > a, (
        f"winner_index=1 must display product_b > product_a even at the floor; "
        f"got a={a} b={b} (FE `>=` would crown the loser on a tie)"
    )
    assert sv2["overall_score"]["winner_idx"] == 1


def test_floor_edge_winner1_below_floor_raw_also_raises_winner():
    """Even more extreme: raw far below the floor-clamp threshold (both → 60).
    Same fix — winner_index=1 winner must end strictly above the loser."""
    sv2 = _build_scoring_v2(_products(), _sr(5.0, 8.0, 1), "electronics", 1)
    a = sv2["overall_score"]["product_a"]
    b = sv2["overall_score"]["product_b"]
    assert b > a, f"winner_index=1 at the floor must display product_b > product_a, got a={a} b={b}"


def test_floor_edge_raised_winner_stays_in_band():
    """The raised winner must not exceed the calibration ceiling (95)."""
    from app.services.scoring_service import _CALIBRATION_CEILING
    sv2 = _build_scoring_v2(_products(), _sr(30.0, 30.0, 1), "electronics", 1)
    b = sv2["overall_score"]["product_b"]
    assert b <= _CALIBRATION_CEILING, f"raised winner must stay <= ceiling, got {b}"


def test_floor_edge_via_disable_dampening_flag(monkeypatch):
    """The real production trigger: DISABLE_DIM_NORM_DAMPENING restores the
    legacy 30-100 band whose lows calibrate to the floor. End-to-end through
    compute_scores → _build_scoring_v2, winner_index=1 must still display
    product_b on top. (Belt-and-suspenders over the direct-input tests.)"""
    from app.services.scoring_service import ScoringService, calibrate_score
    monkeypatch.setenv("DISABLE_DIM_NORM_DAMPENING", "true")
    svc = ScoringService()
    # Two products where product_1 genuinely wins by a hair but both land low.
    p0 = {"name": "A", "category": "electronics",
          "price": {"amount": 999, "currency": "BHD", "source_method": "estimated"},
          "rating": 1.1, "review_count": 5, "specs": {"ram": "2 GB"}}
    p1 = {"name": "B", "category": "electronics",
          "price": {"amount": 990, "currency": "BHD", "source_method": "local_bhd"},
          "rating": 1.2, "review_count": 6, "specs": {"ram": "2 GB", "storage": "32 GB"}}
    r = svc.compute_scores([p0, p1])
    wi = r.get("winner_index")
    sv2 = _build_scoring_v2([p0, p1], r, "electronics", wi)
    a = sv2["overall_score"]["product_a"]
    b = sv2["overall_score"]["product_b"]
    # Whichever side won, the displayed pair must AGREE with winner_index via the
    # FE `>=` rule: winner strictly highest (no floor-tie crowning the loser).
    if wi == 1:
        assert b > a, f"winner_index=1 must display product_b strictly highest, got a={a} b={b}"
    elif wi == 0:
        assert a >= b, f"winner_index=0 may tie-or-lead via `>=`, got a={a} b={b}"


def test_decisive_gap_unchanged():
    """A decisive gap already displays correctly — the invariant is a no-op
    there (winner already strictly above)."""
    sv2 = _build_scoring_v2(_products(), _sr(90.0, 55.0, 0), "electronics", 0)
    from app.services.scoring_service import calibrate_score
    assert sv2["overall_score"]["product_a"] == calibrate_score(90.0)
    assert sv2["overall_score"]["product_b"] == calibrate_score(55.0)
    assert sv2["overall_score"]["product_a"] > sv2["overall_score"]["product_b"]

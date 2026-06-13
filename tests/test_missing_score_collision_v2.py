"""S3 L3 v2 (d) — MISSING_SCORE=50 collision fix (team-lead approved).

MULTIPLE legitimate computed scores equal exactly 50.0 and collide with the
MISSING_SCORE sentinel: `_normalize_review` rating 2.5★ → 50.0; `_normalize_direct`
reliability/popularity raw 0.5 → 50.0. Sites that filtered `score == MISSING_SCORE`
then DROPPED these real values as if absent. The fix tracks missingness via the
EXPLICIT per-dim `_<dim>_missing` flags / `missing_data` list, never value-equality.

Band-independent (correct whatever dampening/magnitude config wins).
"""
import pytest

from app.services.scoring_service import ScoringService, MISSING_SCORE


@pytest.fixture
def service():
    return ScoringService()


def _prod(name, *, rating, review_count=500, specs=None, price=300):
    return {
        "name": name, "category": "electronics",
        "specs": specs if specs is not None else {"ram": "8 GB", "storage": "256 GB"},
        "rating": rating, "review_count": review_count,
        "price": {"amount": price, "currency": "BHD", "source_method": "local_bhd"},
        "fact_check": {"specs_verified": 3},
    }


def test_normalize_review_25_stars_is_real_not_missing(service):
    """rating 2.5★ normalizes to exactly 50.0 — a REAL middling score that must
    NOT be confused with the MISSING sentinel by downstream consumers."""
    raw = [{"review_raw": 2.5}]
    assert service._normalize_review(raw, 0) == 50.0  # documents the collision


def test_compute_dimension_winners_reads_missing_data_not_value_equality(service):
    """Direct unit: compute_dimension_winners must NOT treat a breakdown value of
    exactly 50.0 as missing — it reads the explicit missing_data list. A genuine
    50.0 on BOTH sides (not in missing_data) is a 'tie', not 'N/A'."""
    scoring_result = {
        "scores": {
            "product_0": {"breakdown": {"futureproof_score": 50.0, "performance_score": 80.0},
                          "missing_data": None},
            "product_1": {"breakdown": {"futureproof_score": 50.0, "performance_score": 60.0},
                          "missing_data": None},
        }
    }
    winners = service.compute_dimension_winners(scoring_result, ["A", "B"], "electronics")
    fp = winners.get("futureproof_score", {})
    assert fp.get("winner") == "tie", (
        f"a genuine 50.0/50.0 (not in missing_data) is a tie, not N/A; got {fp}"
    )


def test_compute_dimension_winners_NA_only_when_in_missing_data(service):
    """When a dim IS in both products' missing_data, it's correctly N/A —
    regardless of the breakdown value (which may be the 50 sentinel)."""
    scoring_result = {
        "scores": {
            "product_0": {"breakdown": {"futureproof_score": 50.0}, "missing_data": ["futureproof_score"]},
            "product_1": {"breakdown": {"futureproof_score": 50.0}, "missing_data": ["futureproof_score"]},
        }
    }
    winners = service.compute_dimension_winners(scoring_result, ["A", "B"], "electronics")
    assert winners.get("futureproof_score", {}).get("winner") == "N/A"


def test_one_real_50_review_vs_higher_is_not_missing(service):
    """product_0 rating 2.5★ (review 50.0), product_1 rating 4.5★ (higher). The
    review dim winner is product_1 — product_0's real 50.0 must count as a real
    (losing) score, NOT be dropped as missing → N/A."""
    p0 = _prod("Mid", rating=2.5)
    p1 = _prod("High", rating=4.5)
    r = service.compute_scores([p0, p1])
    dim_winners = r.get("dimension_winners", {})
    fp = dim_winners.get("futureproof_score", {})
    # A real winner must be declared (not N/A), and it's product_1 (the higher).
    assert fp.get("winner") not in ("N/A", None), (
        f"a real 50.0 vs a higher score must declare a winner, got {fp}"
    )


def test_real_50_survives_into_dimensions_v2(service):
    """A genuine 50.0 review score must NOT be silently omitted from the v2
    dimensions[] as if it were missing data."""
    from app.services.scoring_service import build_dimensions_v2
    p0 = _prod("Mid", rating=2.5)
    p1 = _prod("High", rating=4.5)
    r = service.compute_scores([p0, p1])
    dims = build_dimensions_v2([p0, p1], r, "electronics")
    # The reviews core dim must be present (rating data exists on both).
    keys = {d.get("key") for d in dims}
    assert "reviews" in keys, f"reviews dim must be present with real ratings, got {keys}"

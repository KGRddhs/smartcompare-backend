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
    (losing) score, NOT be dropped as missing → N/A.

    [gate finding B] HARDENED: assert margin is not None (== the real gap), not
    just winner != N/A — the producer must not flag the real 50.0 missing."""
    p0 = _prod("Mid", rating=2.5)
    p1 = _prod("High", rating=4.5)
    r = service.compute_scores([p0, p1])
    dim_winners = r.get("dimension_winners", {})
    fp = dim_winners.get("futureproof_score", {})
    # A REAL winner with a REAL margin (the 2.5★ vs 4.5★ gap) — not N/A, not None.
    assert fp.get("winner") not in ("N/A", None), (
        f"a real 50.0 vs a higher score must declare a winner, got {fp}"
    )
    assert fp.get("margin") is not None and fp.get("margin") > 0, (
        f"the real review gap must be a positive margin, got {fp}"
    )
    # And the producer must NOT have flagged futureproof (review dim) missing for
    # product_1 (rating 4.5★, a genuine signal).
    assert "futureproof_score" not in (r["scores"]["product_1"].get("missing_data") or []), (
        "review dim with a real 4.5★ rating must not be flagged missing"
    )


def test_producer_does_not_flag_real_50_review_as_missing(service):
    """[gate finding B] producer: BOTH products rating 2.5★ (review→50.0). The
    review dim must NOT be flagged missing (it's a genuine 2.5★ tie, not absent
    data). Pins the producer-side fix (_signal_missing_for, not ==50)."""
    p0 = _prod("A", rating=2.5)
    p1 = _prod("B", rating=2.5)
    r = service.compute_scores([p0, p1])
    for pk in ("product_0", "product_1"):
        md = r["scores"][pk].get("missing_data") or []
        assert "futureproof_score" not in md, (
            f"a genuine 2.5★ review (50.0) must not be flagged missing; got {md}"
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


def test_dim_from_category_lookup_real_50_not_flagged_was_missing(service):
    """[gate finding B — SECOND site] _dim_from_category_lookup must NOT set
    was_missing_a/was_missing_b from `score in (None, MISSING_SCORE)` value-
    equality. A genuine breakdown value of exactly 50.0 that is NOT in that
    product's missing_data is a real (middling) score — flagging it 'was
    missing' makes build_dimensions_v2 suppress its winner (Decision B
    one-sided-missing suppression) and mislabels the row as a data gap.

    Source of truth = the per-product `missing_data` list (None here) +
    score-is-None (genuine absence), NEVER the 50 sentinel value."""
    from app.services.scoring_service import _dim_from_category_lookup
    scoring_result = {
        "scores": {
            "product_0": {"breakdown": {"futureproof_score": 50.0}, "missing_data": None},
            "product_1": {"breakdown": {"futureproof_score": 82.0}, "missing_data": None},
        }
    }
    dim = _dim_from_category_lookup("futureproof_score", scoring_result, None)
    assert dim is not None, "a real 50.0 vs 82.0 must produce a dim, not None"
    assert dim["score_a"] == 50.0 and dim["score_b"] == 82.0
    assert dim.get("was_missing_a") is False, (
        f"a genuine 50.0 (not in missing_data) must NOT be flagged was_missing, got {dim}"
    )
    assert dim.get("was_missing_b") is False


def test_dim_from_category_lookup_flags_was_missing_from_missing_data(service):
    """Conversely: when the dim IS in product_0's missing_data, was_missing_a
    must be True even though the breakdown carries a (sentinel) value — the
    list is authoritative, so one-sided suppression still fires for a real gap."""
    from app.services.scoring_service import _dim_from_category_lookup
    scoring_result = {
        "scores": {
            "product_0": {"breakdown": {"futureproof_score": 50.0},
                          "missing_data": ["futureproof_score"]},
            "product_1": {"breakdown": {"futureproof_score": 82.0}, "missing_data": None},
        }
    }
    dim = _dim_from_category_lookup("futureproof_score", scoring_result, None)
    assert dim is not None
    assert dim.get("was_missing_a") is True, (
        f"futureproof in product_0 missing_data must flag was_missing_a, got {dim}"
    )
    assert dim.get("was_missing_b") is False


def test_dim_from_category_lookup_both_missing_returns_none(service):
    """Both sides flagged in missing_data → silent omission (None), even though
    the breakdown values are present sentinels."""
    from app.services.scoring_service import _dim_from_category_lookup
    scoring_result = {
        "scores": {
            "product_0": {"breakdown": {"futureproof_score": 50.0},
                          "missing_data": ["futureproof_score"]},
            "product_1": {"breakdown": {"futureproof_score": 50.0},
                          "missing_data": ["futureproof_score"]},
        }
    }
    dim = _dim_from_category_lookup("futureproof_score", scoring_result, None)
    assert dim is None, f"both-missing (via missing_data) must omit the dim, got {dim}"


def test_dim_from_category_lookup_genuinely_absent_value_is_missing(service):
    """A score genuinely absent from the breakdown (None, dim not computed) IS a
    real gap regardless of missing_data — score-is-None remains a missing signal
    so a half-populated breakdown still suppresses correctly."""
    from app.services.scoring_service import _dim_from_category_lookup
    scoring_result = {
        "scores": {
            "product_0": {"breakdown": {}, "missing_data": None},  # no futureproof at all
            "product_1": {"breakdown": {"futureproof_score": 82.0}, "missing_data": None},
        }
    }
    dim = _dim_from_category_lookup("futureproof_score", scoring_result, None)
    assert dim is not None
    assert dim.get("was_missing_a") is True, (
        f"a score absent from the breakdown (None) is a real gap, got {dim}"
    )
    assert dim.get("was_missing_b") is False


def test_spec_secondary_blends_real_25star_review_not_drops_it(service):
    """[gate finding B — THIRD site, _normalize_scores spec_secondary] BOTH
    products have real (differing) specs + a genuine 2.5★ rating (review→50.0).
    The spec_secondary signal (electronics `feature_score`) must BLEND
    spec*0.6 + 50*0.4, NOT take the `elif r == MISSING_SCORE: append(s)` branch
    that drops the real 50.0 review as if absent. Pins the producer fix to gate
    on `_review_missing` (False here — 2.5★ is real), never `== MISSING_SCORE`.
    """
    # Differing specs so spec_score is a real, non-tied, non-50 value on at
    # least one side (the array-collapse only fires on a tied spec pair).
    p0 = _prod("Hi", rating=2.5, specs={"ram": "16 GB", "storage": "1 TB",
                                         "screen": "6.8", "battery_life_hours": "30"})
    p1 = _prod("Lo", rating=2.5, specs={"ram": "4 GB"})
    r = service.compute_scores([p0, p1])
    fb0 = r["scores"]["product_0"]["breakdown"]
    fb1 = r["scores"]["product_1"]["breakdown"]
    # feature_score is the spec_secondary dim for electronics. With a real 2.5★
    # review (50.0) blended in, neither side's feature_score may be flagged
    # missing (both have specs AND a rating → spec_secondary present).
    md0 = r["scores"]["product_0"].get("missing_data") or []
    md1 = r["scores"]["product_1"].get("missing_data") or []
    assert "feature_score" not in md0 and "feature_score" not in md1, (
        f"spec_secondary with real specs + real 2.5★ must not be missing; "
        f"md0={md0} md1={md1}"
    )
    # And the blended value must reflect the review: with spec != 50 on the
    # high side, blend (spec*0.6 + 50*0.4) pulls feature_score toward 50 vs a
    # spec-only fallback. Assert it is NOT exactly the spec-only value when the
    # spec side is clearly above the review midpoint.
    perf0 = fb0.get("performance_score")  # the pure-spec dim
    feat0 = fb0.get("feature_score")      # the spec_secondary blend
    if perf0 is not None and feat0 is not None and perf0 > 55:
        assert feat0 < perf0, (
            f"spec_secondary must blend the 50.0 review DOWN from a high spec "
            f"({perf0}); spec-only fallback would equal it. feat0={feat0}"
        )

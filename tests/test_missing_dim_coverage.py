"""S2 I3.6 — missing-dimension coverage metric (Decision B measurement).

Ahmed's Decision B (2026-06-11): "we don't want missing data — full
search/detect/research so we are fully certain; no misleading and false
certainty." The render-side suppression (I3.5) hides one-sided MISSING
dim-winners, and the Tier-3 spec synthesis fallback (I3.6 root) FILLS the
gaps — but neither is measurable unless we COUNT the gaps. This metric is
the KPI dial: how many dimension cells the engine had to leave at
MISSING_SCORE.

`count_missing_dim_cells(scoring_result, category)` counts MISSING_SCORE
cells across BOTH products' per-dim breakdowns — the genuine data-gap
measure BEFORE display omission (build_dimensions_v2 silently drops
both-sided-missing dims, so counting the post-omission dimensions[] would
under-report the real burden).

Contract:
    {
      "count": int,    # MISSING_SCORE cells across both products
      "total": int,    # cells examined (len(category dims) * 2)
      "fraction": float,  # count / total, 0.0 when total == 0
    }

Cells are counted over CATEGORY_DIMENSIONS[category] (6 keys) for each of
product_0 / product_1 = 12 possible cells. A key absent from a product's
breakdown counts as MISSING (mirrors compute_dimension_winners' default).
"""

from __future__ import annotations

import pytest

from app.services.scoring_service import (
    MISSING_SCORE,
    count_missing_dim_cells,
)


def _sr(breakdown_0: dict, breakdown_1: dict) -> dict:
    """Minimal scoring_result with two product breakdowns."""
    return {
        "scores": {
            "product_0": {"overall": 80, "breakdown": breakdown_0},
            "product_1": {"overall": 75, "breakdown": breakdown_1},
        },
    }


# Electronics dims: performance/value/build_quality/feature/ecosystem/futureproof
_FULL_ELEC = {
    "performance_score": 85, "value_score": 80, "build_quality_score": 82,
    "feature_score": 88, "ecosystem_score": 90, "futureproof_score": 78,
}


class TestCountMissingDimCells:

    def test_zero_missing_when_both_fully_populated(self):
        result = count_missing_dim_cells(_sr(_FULL_ELEC, _FULL_ELEC), "electronics")
        assert result["count"] == 0
        assert result["total"] == 12  # 6 dims * 2 products
        assert result["fraction"] == 0.0

    def test_counts_explicit_missing_score_cells(self):
        """MISSING_SCORE=50 values are counted as gaps."""
        b0 = dict(_FULL_ELEC)
        b0["ecosystem_score"] = MISSING_SCORE
        b0["futureproof_score"] = MISSING_SCORE
        result = count_missing_dim_cells(_sr(b0, _FULL_ELEC), "electronics")
        assert result["count"] == 2
        assert result["total"] == 12
        # fraction is rounded to 4 dp for clean JSON output.
        assert result["fraction"] == pytest.approx(2 / 12, abs=1e-4)

    def test_absent_keys_count_as_missing(self):
        """A dim key absent from a product's breakdown is a gap (mirrors
        compute_dimension_winners' breakdown.get(dim, MISSING_SCORE))."""
        b0 = {"performance_score": 85, "value_score": 80}  # 4 dims absent
        result = count_missing_dim_cells(_sr(b0, _FULL_ELEC), "electronics")
        # product_0 missing 4 (build_quality/feature/ecosystem/futureproof),
        # product_1 missing 0 → 4 total.
        assert result["count"] == 4
        assert result["total"] == 12

    def test_both_sides_missing_counts_both_cells(self):
        b0 = dict(_FULL_ELEC); b0["ecosystem_score"] = MISSING_SCORE
        b1 = dict(_FULL_ELEC); b1["ecosystem_score"] = MISSING_SCORE
        result = count_missing_dim_cells(_sr(b0, b1), "electronics")
        assert result["count"] == 2  # one cell on each side

    def test_all_missing(self):
        empty = {}
        result = count_missing_dim_cells(_sr(empty, empty), "electronics")
        assert result["count"] == 12
        assert result["total"] == 12
        assert result["fraction"] == 1.0

    def test_unknown_category_falls_back_to_other(self):
        """An unrecognized category uses the 'other' dim set (6 dims), not
        a crash."""
        result = count_missing_dim_cells(_sr({}, {}), "nonexistent_category")
        assert result["total"] == 12  # 'other' has 6 dims

    def test_single_product_returns_zero_total(self):
        """Fewer than 2 products → no cells to examine (no crash)."""
        sr = {"scores": {"product_0": {"overall": 80, "breakdown": _FULL_ELEC}}}
        result = count_missing_dim_cells(sr, "electronics")
        assert result["total"] == 0
        assert result["count"] == 0
        assert result["fraction"] == 0.0

    def test_empty_scoring_result_no_crash(self):
        result = count_missing_dim_cells({}, "electronics")
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["fraction"] == 0.0

    def test_breakdown_inference_from_keys_when_category_mismatch(self):
        """When breakdown keys don't match the category's dims, the function
        examines whatever keys are present (mirrors compute_dimension_winners
        fallback) so a mis-tagged category still measures real gaps."""
        # Supplements breakdown under an electronics tag.
        supp = {
            "efficacy_score": 80, "safety_score": 75, "dosage_score": MISSING_SCORE,
            "serving_value_score": 70, "form_score": 60, "trust_score": MISSING_SCORE,
        }
        result = count_missing_dim_cells(_sr(supp, supp), "electronics")
        # Falls back to the present keys (6 supp dims): 2 missing per side = 4.
        assert result["count"] == 4
        assert result["total"] == 12

    def test_missing_data_list_is_authoritative_over_value_equality(self):
        """[gate finding B] When the product carries an explicit `missing_data`
        list (the real compute_scores shape), it is AUTHORITATIVE — a breakdown
        value of exactly 50.0 that is NOT in missing_data is a REAL score, not a
        gap. Pins the collision: a genuine 2.5★ review (→50.0) / 0.5 reliability
        (→50.0) must NOT inflate the KPI dial Ahmed reads for 'no missing data'.
        """
        b0 = dict(_FULL_ELEC)
        b0["ecosystem_score"] = MISSING_SCORE   # genuine middling 50.0 (e.g. 0.5 popularity)
        b0["futureproof_score"] = MISSING_SCORE  # genuine middling 50.0 (e.g. 2.5★ review)
        sr = {
            "scores": {
                # missing_data EMPTY → none of these 50.0s are real gaps.
                "product_0": {"overall": 80, "breakdown": b0, "missing_data": None},
                "product_1": {"overall": 75, "breakdown": _FULL_ELEC, "missing_data": None},
            }
        }
        result = count_missing_dim_cells(sr, "electronics")
        assert result["count"] == 0, (
            f"genuine 50.0 cells NOT in missing_data must not count as gaps; got {result}"
        )

    def test_missing_data_list_counts_flagged_cells_even_if_value_nonsentinel(self):
        """Symmetric: a dim IN missing_data counts as a gap regardless of the
        breakdown value (the Tier-fallback may leave a non-50 placeholder)."""
        sr = {
            "scores": {
                "product_0": {"overall": 80, "breakdown": dict(_FULL_ELEC),
                              "missing_data": ["ecosystem_score", "futureproof_score"]},
                "product_1": {"overall": 75, "breakdown": dict(_FULL_ELEC),
                              "missing_data": None},
            }
        }
        result = count_missing_dim_cells(sr, "electronics")
        assert result["count"] == 2, f"flagged cells must count as gaps; got {result}"

    def test_real_compute_scores_genuine_25star_not_counted_missing(self):
        """End-to-end against compute_scores: BOTH products real specs + 2.5★
        (review→50.0). The review-driven dim (futureproof_score) must NOT be
        counted as a missing cell — it's a real 50.0, in neither missing_data."""
        from app.services.scoring_service import ScoringService
        svc = ScoringService()
        prod = lambda n, s: {
            "name": n, "category": "electronics", "specs": s,
            "rating": 2.5, "review_count": 500,
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "fact_check": {"specs_verified": 3},
        }
        p0 = prod("Hi", {"ram": "16 GB", "storage": "1 TB", "screen": "6.8",
                         "battery_life_hours": "30"})
        p1 = prod("Lo", {"ram": "8 GB", "storage": "256 GB"})
        r = svc.compute_scores([p0, p1])
        # futureproof_score is the review dim for electronics; with a real 2.5★
        # on both, it must be in NEITHER product's missing_data.
        for pk in ("product_0", "product_1"):
            md = r["scores"][pk].get("missing_data") or []
            assert "futureproof_score" not in md
        result = count_missing_dim_cells(r, "electronics")
        # The review dim is real on both sides → it contributes 0 to the count.
        # (Other dims may or may not be present, but the review dim specifically
        # must not be over-counted via the 50.0 collision.)
        # Re-derive the count WITHOUT the review dim's cells to prove no inflation:
        md0 = set(r["scores"]["product_0"].get("missing_data") or [])
        md1 = set(r["scores"]["product_1"].get("missing_data") or [])
        expected = len(md0) + len(md1)
        assert result["count"] == expected, (
            f"count must equal the union of explicit missing_data sizes "
            f"({expected}), not inflated by genuine 50.0s; got {result}"
        )

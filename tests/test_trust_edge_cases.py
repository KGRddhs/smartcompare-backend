"""
Edge-case tests for trust validation service.

These tests should FAIL (red) until trust_validation_service.py is created.
"""
import pytest


class TestTrustEdgeCases:
    """Edge cases for trust validation."""

    def _make_scoring_result(self, p0_breakdown, p1_breakdown, winner_index=0):
        def _safe_avg(d):
            vals = [v for v in d.values() if v is not None]
            return sum(vals) / max(len(vals), 1) if vals else 50
        return {
            "scores": {
                "product_0": {
                    "overall": _safe_avg(p0_breakdown),
                    "breakdown": p0_breakdown,
                },
                "product_1": {
                    "overall": _safe_avg(p1_breakdown),
                    "breakdown": p1_breakdown,
                },
            },
            "winner_index": winner_index,
            "dimension_winners": {},
        }

    def test_all_missing_score_dimensions(self):
        """Scoring result where all dimensions are MISSING_SCORE (50)."""
        from app.services.trust_validation_service import validate_verdict
        from app.services.scoring_service import MISSING_SCORE
        scoring = self._make_scoring_result(
            {
                "performance_score": MISSING_SCORE,
                "value_score": MISSING_SCORE,
                "build_quality_score": MISSING_SCORE,
                "feature_score": MISSING_SCORE,
                "ecosystem_score": MISSING_SCORE,
                "futureproof_score": MISSING_SCORE,
            },
            {
                "performance_score": MISSING_SCORE,
                "value_score": MISSING_SCORE,
                "build_quality_score": MISSING_SCORE,
                "feature_score": MISSING_SCORE,
                "ecosystem_score": MISSING_SCORE,
                "futureproof_score": MISSING_SCORE,
            },
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["winner_aligned"] is True
        # All tied at MISSING_SCORE -> all softened, none validated
        assert result["claims_flagged"] == 0

    def test_verdict_with_no_winner_index_key(self):
        """Verdict dict missing winner_index entirely."""
        from app.services.trust_validation_service import validate_verdict
        scoring = self._make_scoring_result(
            {"function_score": 70, "build_score": 60, "review_score": 65,
             "value_score": 70, "reliability_score": 55, "feature_match_score": 60},
            {"function_score": 65, "build_score": 55, "review_score": 60,
             "value_score": 65, "reliability_score": 50, "feature_match_score": 55},
            winner_index=0,
        )
        verdict = {}  # No winner_index
        result = validate_verdict(verdict, scoring, "other")
        # Should not crash; defaults to 0
        assert "winner_aligned" in result

    def test_scoring_result_with_only_1_product(self):
        """Scoring result with only product_0, no product_1."""
        from app.services.trust_validation_service import validate_verdict
        scoring = {
            "scores": {
                "product_0": {
                    "overall": 70,
                    "breakdown": {"function_score": 70},
                },
            },
            "winner_index": 0,
        }
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "other")
        # Should handle gracefully — no product_1 to compare
        assert result["winner_aligned"] is True
        assert result["claims_validated"] == 0

    def test_all_dimensions_tied(self):
        """Every dimension has gap < 3.0 (tie threshold)."""
        from app.services.trust_validation_service import validate_verdict
        scoring = self._make_scoring_result(
            {"craft_score": 70, "fit_score": 71, "style_score": 69,
             "durability_score": 70, "heritage_score": 70, "cpw_score": 72},
            {"craft_score": 71, "fit_score": 70, "style_score": 70,
             "durability_score": 71, "heritage_score": 69, "cpw_score": 71},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "fashion")
        # All gaps < 3.0 -> all softened
        assert result["claims_softened"] >= 5  # Most or all should be softened
        assert result["claims_validated"] == 0

    def test_empty_scoring_result(self):
        """Completely empty scoring result."""
        from app.services.trust_validation_service import validate_verdict
        result = validate_verdict({"winner_index": 0}, {}, "electronics")
        assert result["winner_aligned"] is True
        assert result["claims_validated"] == 0
        assert result["claims_softened"] == 0
        assert result["claims_flagged"] == 0

    def test_scoring_with_none_values(self):
        """Scoring result with None breakdown values."""
        from app.services.trust_validation_service import validate_verdict
        scoring = self._make_scoring_result(
            {"performance_score": None, "value_score": 70},
            {"performance_score": 80, "value_score": None},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        # Should not crash on None values
        result = validate_verdict(verdict, scoring, "electronics")
        assert "winner_aligned" in result

    def test_winner_misalignment_sets_confidence_low(self):
        """When GPT winner contradicts scoring winner, confidence should drop."""
        from app.services.trust_validation_service import validate_verdict
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 75, "build_quality_score": 70,
             "feature_score": 85, "ecosystem_score": 60, "futureproof_score": 65},
            {"performance_score": 50, "value_score": 55, "build_quality_score": 45,
             "feature_score": 40, "ecosystem_score": 35, "futureproof_score": 40},
            winner_index=0,
        )
        verdict = {"winner_index": 1}  # GPT picks loser
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["winner_aligned"] is False
        assert result["confidence_adjustment"] == "low"

    def test_unknown_category_does_not_crash(self):
        """Unknown category in trust validation should fallback gracefully."""
        from app.services.trust_validation_service import validate_verdict
        scoring = self._make_scoring_result(
            {"function_score": 80, "build_score": 70},
            {"function_score": 60, "build_score": 65},
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "nonexistent_category")
        assert "winner_aligned" in result

    def test_verdict_winner_index_as_string(self):
        """winner_index might come as string from GPT."""
        from app.services.trust_validation_service import validate_verdict
        scoring = self._make_scoring_result(
            {"function_score": 80},
            {"function_score": 60},
            winner_index=0,
        )
        # GPT might return "0" instead of 0
        verdict = {"winner_index": "0"}
        # Should handle gracefully (either convert or not crash)
        try:
            result = validate_verdict(verdict, scoring, "other")
            assert "winner_aligned" in result
        except (TypeError, ValueError):
            # Acceptable to raise if string not handled
            pass

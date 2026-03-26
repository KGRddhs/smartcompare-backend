"""Tests for trust validation — cross-checking GPT claims against scores."""
import pytest
from app.services.trust_validation_service import validate_verdict


class TestVerdictValidation:

    def _make_scoring_result(self, p0_breakdown, p1_breakdown, winner_index=0):
        return {
            "scores": {
                "product_0": {"overall": sum(p0_breakdown.values()) / len(p0_breakdown), "breakdown": p0_breakdown},
                "product_1": {"overall": sum(p1_breakdown.values()) / len(p1_breakdown), "breakdown": p1_breakdown},
            },
            "winner_index": winner_index,
            "dimension_winners": {},
        }

    def test_winner_aligned_when_matching(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70},
            {"performance_score": 60, "value_score": 65},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["winner_aligned"] is True

    def test_winner_misaligned_detected(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70},
            {"performance_score": 60, "value_score": 65},
            winner_index=0,
        )
        verdict = {"winner_index": 1}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["winner_aligned"] is False

    def test_misaligned_sets_confidence_low(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70},
            {"performance_score": 60, "value_score": 65},
            winner_index=0,
        )
        verdict = {"winner_index": 1}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["confidence_adjustment"] == "low"

    def test_claims_validated_count(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70, "build_quality_score": 75, "feature_score": 60, "ecosystem_score": 50, "futureproof_score": 55},
            {"performance_score": 60, "value_score": 65, "build_quality_score": 70, "feature_score": 55, "ecosystem_score": 45, "futureproof_score": 50},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["claims_validated"] >= 0
        assert result["claims_flagged"] >= 0

    def test_close_scores_counted_as_softened(self):
        # All gaps < 3 should be softened
        scoring = self._make_scoring_result(
            {"performance_score": 70, "value_score": 71},
            {"performance_score": 69, "value_score": 70},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["claims_softened"] == 2
        assert result["claims_validated"] == 0

    def test_wide_gap_scores_counted_as_validated(self):
        # All gaps >= 3 should be validated (avoid 50 which equals MISSING_SCORE)
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 75},
            {"performance_score": 60, "value_score": 55},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["claims_validated"] == 2
        assert result["claims_softened"] == 0

    def test_returns_expected_structure(self):
        scoring = self._make_scoring_result(
            {"function_score": 70, "build_score": 60, "review_score": 65, "value_score": 70, "reliability_score": 55, "feature_match_score": 60},
            {"function_score": 65, "build_score": 55, "review_score": 60, "value_score": 65, "reliability_score": 50, "feature_match_score": 55},
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "other")
        assert "winner_aligned" in result
        assert "claims_validated" in result
        assert "claims_softened" in result
        assert "claims_flagged" in result
        assert "confidence_adjustment" in result

    def test_empty_scoring_handles_gracefully(self):
        result = validate_verdict({"winner_index": 0}, {}, "electronics")
        assert result["winner_aligned"] is True  # no data to contradict
        assert result["claims_validated"] == 0

    def test_missing_product_scores_handles_gracefully(self):
        scoring = {"scores": {"product_0": {"overall": 70, "breakdown": {}}}}
        result = validate_verdict({"winner_index": 0}, scoring, "electronics")
        assert result["winner_aligned"] is True
        assert result["claims_validated"] == 0

    def test_aligned_winner_no_confidence_adjustment(self):
        scoring = self._make_scoring_result(
            {"performance_score": 80, "value_score": 70},
            {"performance_score": 60, "value_score": 65},
            winner_index=0,
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "electronics")
        assert result["confidence_adjustment"] is None

    def test_unknown_category_falls_back_to_other(self):
        scoring = self._make_scoring_result(
            {"function_score": 80, "value_score": 70},
            {"function_score": 60, "value_score": 65},
        )
        verdict = {"winner_index": 0}
        result = validate_verdict(verdict, scoring, "unknown_category")
        assert result["winner_aligned"] is True
        # Should still work with "other" dimensions
        assert isinstance(result["claims_validated"], int)

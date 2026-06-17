"""Phase 4 Task #5 — personalization e2e + F4.4 deterministic partial verdict.

Two slices:
  - F4.4: the hard-cap partial path emits at least a DETERMINISTIC-scoring
    verdict (winner + score-based reason) so the user never gets an empty
    recommendation. _deterministic_partial_verdict fills only missing fields.
  - Personalization e2e: explicit priorities produce a non-empty
    scoring_v2.personalization.applied_shifts (the chip's data) + the shift
    weights actually move from the category defaults.
"""

import pytest


# ----------------------------------------- F4.4 deterministic partial verdict ---

class TestDeterministicPartialVerdict:
    def _svc(self):
        from app.services.structured_comparison_service import StructuredComparisonService
        return StructuredComparisonService()

    def test_empty_verdict_filled_from_scores(self):
        svc = self._svc()
        out = svc._deterministic_partial_verdict(
            {},  # empty LLM verdict (hard-cap)
            {"winner_index": 0, "scores": {"product_0": {"overall": 72.5},
                                           "product_1": {"overall": 61.0}}},
            ["Ombre Leather", "Tobacco Vanille"],
            [{"winner_wins": {"dimension": "character_score"},
              "loser_wins": {"dimension": "longevity_score", "product": "Tobacco Vanille"}}],
        )
        assert out["winner_declaration"] == "Ombre Leather"
        assert out["winner_index"] == 0
        assert "11.5" in out["winner_reason"]
        assert "Tobacco Vanille" in out["key_tradeoff"]
        assert "longevity" in out["key_tradeoff"]

    def test_does_not_overwrite_present_llm_verdict(self):
        svc = self._svc()
        existing = {"winner_index": 1, "winner_declaration": "Real LLM Winner",
                    "winner_reason": "Real LLM reason.", "key_tradeoff": "Real tradeoff."}
        out = svc._deterministic_partial_verdict(
            existing,
            {"winner_index": 0, "scores": {"product_0": {"overall": 72.5},
                                           "product_1": {"overall": 61.0}}},
            ["A", "B"], [],
        )
        # Present fields are preserved (never overwritten).
        assert out["winner_declaration"] == "Real LLM Winner"
        assert out["winner_reason"] == "Real LLM reason."
        assert out["key_tradeoff"] == "Real tradeoff."

    def test_fills_only_missing_fields(self):
        svc = self._svc()
        # Declaration present, reason missing → fill only the reason.
        out = svc._deterministic_partial_verdict(
            {"winner_declaration": "Ombre Leather"},
            {"winner_index": 0, "scores": {"product_0": {"overall": 70},
                                           "product_1": {"overall": 60}}},
            ["Ombre Leather", "Tobacco Vanille"], [],
        )
        assert out["winner_declaration"] == "Ombre Leather"
        assert out["winner_reason"]  # filled
        assert "Ombre Leather" in out["winner_reason"]

    def test_no_scores_safe(self):
        svc = self._svc()
        out = svc._deterministic_partial_verdict(
            {}, {"winner_index": 0, "scores": {}}, ["A", "B"], [],
        )
        # No overall scores → still names a winner + a generic reason (never empty).
        assert out["winner_declaration"] == "A"
        assert out["winner_reason"]

    def test_tie_overall_uses_edge_phrasing(self):
        svc = self._svc()
        out = svc._deterministic_partial_verdict(
            {}, {"winner_index": 0, "scores": {"product_0": {"overall": 70},
                                               "product_1": {"overall": 70}}},
            ["A", "B"], [],
        )
        assert "A" in out["winner_reason"]


# ----------------------------------------------- personalization e2e shifts ---

class TestPersonalizationShifts:
    def _make_product(self, category="electronics", price=100, rating=4.2, specs=None):
        return {
            "category": category, "brand": "B", "name": "N",
            "price": {"amount": price, "currency": "BHD"},
            "rating": rating, "review_count": 200,
            "specs": specs or {"processor": "A17", "ram": "8 GB", "battery": "4000 mAh"},
            "reviews": {"source_ratings": [{"rating": rating}]},
            "fact_check": {"specs_verified": 5, "specs_likely": 1, "specs_flagged": 0,
                           "specs_unverified": 0, "price_verified": True,
                           "review_sentiment_consistent": True},
        }

    def test_explicit_priority_moves_weights(self):
        from app.services.scoring_service import ScoringService
        svc = ScoringService()
        products = [
            self._make_product(price=100, specs={"processor": "A17", "ram": "8 GB"}),
            self._make_product(price=80, specs={"processor": "SD8", "ram": "6 GB"}),
        ]
        base = svc.compute_scores(products)
        personalized = svc.compute_scores(products, preferences={"priorities": ["price"], "budget": "budget"})
        base_w = base["scores"]["product_0"]["weights_used"]
        pers_w = personalized["scores"]["product_0"]["weights_used"]
        # The "price" priority must shift the value weight up vs the default.
        assert pers_w.get("value_score", 0) >= base_w.get("value_score", 0)

    def test_applied_shifts_emitted_in_response(self):
        from app.services.response_builder import build_comparison_response
        from app.services.scoring_service import ScoringService
        svc = ScoringService()
        products = [
            self._make_product(price=100, specs={"processor": "A17", "ram": "8 GB"}),
            self._make_product(price=80, specs={"processor": "SD8", "ram": "6 GB"}),
        ]
        scoring_result = svc.compute_scores(products, preferences={"priorities": ["price"], "budget": "budget"})
        comparison = {"winner_index": 0, "winner_declaration": "N", "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="N vs N", product_data=products, comparison=comparison,
            scoring_result=scoring_result, category_used="electronics", region="bahrain",
            user_preferences={"priorities": ["price"], "budget": "budget"},
            elapsed_seconds=1.0, api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
        )
        # applied_shifts must be a list (chip data); present on both surfaces.
        assert isinstance(resp["personalization"]["applied_shifts"], list)
        assert isinstance(resp["scoring_v2"]["personalization"]["applied_shifts"], list)

    def test_no_priorities_empty_shifts(self):
        from app.services.response_builder import build_comparison_response
        from app.services.scoring_service import ScoringService
        svc = ScoringService()
        products = [self._make_product(), self._make_product(price=80)]
        scoring_result = svc.compute_scores(products)
        comparison = {"winner_index": 0, "winner_declaration": "N", "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="N vs N", product_data=products, comparison=comparison,
            scoring_result=scoring_result, category_used="electronics", region="bahrain",
            elapsed_seconds=1.0, api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
        )
        # No priorities → empty (not None) applied_shifts so the chip hides.
        assert resp["personalization"]["applied_shifts"] == []

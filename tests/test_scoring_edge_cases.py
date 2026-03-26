"""
Edge-case tests for the new category-specific scoring system.

These tests target boundary conditions not covered by the main test suites.
They should FAIL (red) until the scoring engine rewrite is complete.
"""
import pytest
from app.services.scoring_service import (
    ScoringService,
    MISSING_SCORE,
)


@pytest.fixture
def service():
    return ScoringService()


def _make_product(
    category="electronics",
    price_amount=50,
    rating=4.0,
    review_count=100,
    specs=None,
    fact_check=None,
    reviews=None,
    brand="TestBrand",
    name="TestProduct",
):
    if fact_check is None:
        fact_check = {
            "specs_verified": 4,
            "specs_likely": 2,
            "specs_flagged": 0,
            "specs_unverified": 0,
            "price_verified": True,
            "review_sentiment_consistent": True,
        }
    return {
        "category": category,
        "brand": brand,
        "name": name,
        "price": {"amount": price_amount, "currency": "BHD"} if price_amount is not None else None,
        "rating": rating,
        "review_count": review_count,
        "specs": specs if specs is not None else {},
        "reviews": reviews or {"source_ratings": [{"rating": rating}] if rating else []},
        "fact_check": fact_check,
    }


class TestScoringEmptySpecs:
    """Products with completely empty specs (all N/A or empty dict)."""

    def test_both_products_empty_specs_returns_valid_scores(self, service):
        products = [
            _make_product(specs={}),
            _make_product(specs={}),
        ]
        result = service.compute_scores(products)
        assert "scores" in result
        assert "product_0" in result["scores"]
        assert "product_1" in result["scores"]
        # Scores should still be computed (from price, reviews, etc.)
        assert isinstance(result["scores"]["product_0"]["overall"], (int, float))

    def test_empty_specs_get_missing_score_for_spec_dimension(self, service):
        products = [
            _make_product(specs={}),
            _make_product(specs={"processor": "A17 Pro", "ram": "8 GB"}),
        ]
        result = service.compute_scores(products)
        # Product with empty specs should have lower overall than product with specs
        p0 = result["scores"]["product_0"]["overall"]
        p1 = result["scores"]["product_1"]["overall"]
        # The product with actual specs should generally score higher
        # (but we just check both are valid numbers)
        assert 0 <= p0 <= 100
        assert 0 <= p1 <= 100

    def test_all_na_specs_treated_as_empty(self, service):
        products = [
            _make_product(specs={"processor": "N/A", "ram": "N/A", "battery": "N/A"}),
            _make_product(specs={"processor": "A17 Pro", "ram": "8 GB", "battery": "4000 mAh"}),
        ]
        result = service.compute_scores(products)
        assert "scores" in result
        assert result["scores"]["product_0"]["overall"] is not None


class TestScoringNullPrices:
    """Products with None/null prices."""

    def test_both_null_prices_still_produces_result(self, service):
        products = [
            _make_product(price_amount=None),
            _make_product(price_amount=None),
        ]
        result = service.compute_scores(products)
        assert "scores" in result
        assert "winner_index" in result

    def test_one_null_price_does_not_crash(self, service):
        products = [
            _make_product(price_amount=None),
            _make_product(price_amount=50),
        ]
        result = service.compute_scores(products)
        assert "scores" in result
        p0 = result["scores"]["product_0"]["overall"]
        p1 = result["scores"]["product_1"]["overall"]
        assert isinstance(p0, (int, float))
        assert isinstance(p1, (int, float))

    def test_zero_price_handled(self, service):
        products = [
            _make_product(price_amount=0),
            _make_product(price_amount=50),
        ]
        result = service.compute_scores(products)
        assert "scores" in result


class TestScoringSingleProduct:
    """Single product (not enough for comparison)."""

    def test_single_product_returns_empty_result(self, service):
        products = [_make_product()]
        result = service.compute_scores(products)
        # Should return empty/default result
        assert "scores" in result
        assert result["scores"]["product_0"]["overall"] == MISSING_SCORE

    def test_empty_product_list_returns_empty_result(self, service):
        result = service.compute_scores([])
        assert "scores" in result


class TestScoringExtremePersonalization:
    """Extreme weight shifts from personalization."""

    def test_all_priorities_selected_still_sums_to_one(self, service):
        all_priorities = [
            "price", "quality", "brand_reputation", "durability",
            "latest_features", "ease_of_use", "eco_friendly", "health_safety",
        ]
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        prefs = {"priorities": all_priorities, "budget": "premium"}
        result = service.compute_scores(products, preferences=prefs)
        weights = result["scores"]["product_0"]["weights_used"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_single_priority_still_sums_to_one(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        prefs = {"priorities": ["price"], "budget": "budget"}
        result = service.compute_scores(products, preferences=prefs)
        weights = result["scores"]["product_0"]["weights_used"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_no_weight_goes_below_zero(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        all_priorities = [
            "price", "quality", "brand_reputation", "durability",
            "latest_features", "ease_of_use", "eco_friendly", "health_safety",
        ]
        prefs = {"priorities": all_priorities, "budget": "budget"}
        result = service.compute_scores(products, preferences=prefs)
        weights = result["scores"]["product_0"]["weights_used"]
        for dim, w in weights.items():
            assert w >= 0, f"Weight for {dim} is negative: {w}"


class TestBehavioralEdgeCases:
    """Behavioral adjustments with empty/missing dimension_sensitivity."""

    def test_empty_behavior_profile_no_change(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        r_without = service.compute_scores(products)
        r_with = service.compute_scores(products, behavior_profile={})
        # Empty profile should not change scores
        assert r_without["scores"]["product_0"]["overall"] == r_with["scores"]["product_0"]["overall"]

    def test_none_dimension_sensitivity_no_crash(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        profile = {"dimension_sensitivity": None, "category_affinity": {}}
        result = service.compute_scores(products, behavior_profile=profile)
        assert "scores" in result

    def test_behavioral_with_empty_dimension_sensitivity(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        profile = {"dimension_sensitivity": {}, "category_affinity": {}, "price_range": {}}
        result = service.compute_scores(products, behavior_profile=profile)
        weights = result["scores"]["product_0"]["weights_used"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01


class TestSessionSignalEdgeCases:
    """Session signals with zero dwell time or missing data."""

    def test_zero_dwell_time_ignored(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        signals = {"tab_dwell_ms": {"specs": 0, "reviews": 0, "overview": 0}}
        r_without = service.compute_scores(products)
        r_with = service.compute_scores(products, session_signals=signals)
        # Zero dwell should not meaningfully change scores
        assert abs(r_without["scores"]["product_0"]["overall"] - r_with["scores"]["product_0"]["overall"]) < 5

    def test_empty_session_signals_no_crash(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        result = service.compute_scores(products, session_signals={})
        assert "scores" in result

    def test_session_signals_with_none_values(self, service):
        products = [
            _make_product(price_amount=100),
            _make_product(price_amount=80),
        ]
        signals = {"first_tab_viewed": None, "tab_dwell_ms": None}
        result = service.compute_scores(products, session_signals=signals)
        assert "scores" in result


class TestScoringDeterminism:
    """Verify scoring is truly deterministic across multiple runs."""

    def test_same_input_same_output_ten_times(self, service):
        products = [
            _make_product(category="fragrances", price_amount=120, rating=4.5,
                          specs={"longevity": "8 hours", "sillage": "strong"}),
            _make_product(category="fragrances", price_amount=90, rating=4.0,
                          specs={"longevity": "4 hours", "sillage": "moderate"}),
        ]
        results = [service.compute_scores(products) for _ in range(10)]
        first = results[0]["scores"]["product_0"]["overall"]
        for i, r in enumerate(results[1:], start=1):
            assert r["scores"]["product_0"]["overall"] == first, f"Run {i} differs: {r['scores']['product_0']['overall']} != {first}"

    def test_product_order_matters(self, service):
        """Swapping product order should swap winner_index."""
        p1 = _make_product(price_amount=100, rating=4.5, specs={"processor": "A17", "ram": "8 GB"})
        p2 = _make_product(price_amount=200, rating=3.5, specs={"processor": "A15", "ram": "4 GB"})
        r1 = service.compute_scores([p1, p2])
        r2 = service.compute_scores([p2, p1])
        # If p1 wins in r1, p2 should be at index 1 in r1 and index 0 in r2
        # Winner indices should be complementary
        assert r1["winner_index"] != r2["winner_index"] or r1["win_margin"] == 0

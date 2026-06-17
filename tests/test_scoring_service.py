"""
Tests for scoring_service.py — deterministic product scoring engine.
Target: 90%+ coverage, 25+ tests.

Updated for category-specific dimensions (9 categories x 6 dims each).
Electronics uses: performance_score, value_score, build_quality_score,
                  feature_score, ecosystem_score, futureproof_score
Other uses: function_score, build_score, review_score, value_score,
            reliability_score, feature_match_score
"""
import pytest
from app.services.scoring_service import (
    ScoringService,
    get_scoring_service,
    CATEGORY_WEIGHTS,
    CATEGORY_DIMENSION_WEIGHTS,
    CATEGORY_DIMENSIONS,
    MISSING_SCORE,
    CATEGORY_PRIORITY_ADJUSTMENTS,
    CATEGORY_BUDGET_ADJUSTMENTS,
    MAX_WEIGHT_SHIFT_RATIO,
)


@pytest.fixture
def service():
    return ScoringService()


def _make_product(
    price_amount=799,
    rating=4.5,
    review_count=1000,
    category="electronics",
    specs=None,
    fact_check=None,
    reviews=None,
):
    """Helper to build a product dict matching _fetch_product_data output."""
    if specs is None:
        specs = {
            "display": "6.1-inch OLED",
            "processor": "A17 Pro",
            "ram": "8 GB",
            "storage": "256 GB",
            "battery": "3274 mAh",
            "weight": "171 g",
        }
    if fact_check is None:
        fact_check = {
            "specs_verified": 4,
            "specs_likely": 2,
            "specs_flagged": 0,
            "specs_unverified": 0,
            "price_verified": True,
            "review_sentiment_consistent": True,
            "overall_confidence": "high",
        }
    if reviews is None:
        reviews = {
            "average_rating": rating,
            "source_ratings": [
                {"source": "Amazon", "rating": 4.5},
                {"source": "Best Buy", "rating": 4.3},
            ],
        }

    return {
        "brand": "Apple",
        "name": "iPhone 15",
        "category": category,
        "price": {"amount": price_amount, "currency": "BHD", "retailer": "Amazon"},
        "rating": rating,
        "review_count": review_count,
        "rating_verified": True,
        "specs": specs,
        "fact_check": fact_check,
        "reviews": reviews,
    }


# Electronics dimension keys for assertion
ELEC_DIMS = CATEGORY_DIMENSIONS["electronics"]
# "other" category dimension keys
OTHER_DIMS = CATEGORY_DIMENSIONS["other"]

# The "value" dimension for electronics is "value_score"
# The "spec-like" primary dimension for electronics is "performance_score"
# The "review-like" dimension for electronics is "futureproof_score"
# The "reliability-like" dimension for electronics is "build_quality_score"
# The "popularity-like" dimension for electronics is "ecosystem_score"


# ===========================================
# SINGLETON
# ===========================================

class TestSingleton:
    def test_get_scoring_service_returns_same_instance(self):
        s1 = get_scoring_service()
        s2 = get_scoring_service()
        assert s1 is s2

    def test_is_scoring_service_instance(self):
        s = get_scoring_service()
        assert isinstance(s, ScoringService)


# ===========================================
# DETERMINISM
# ===========================================

class TestDeterminism:
    def test_same_input_same_output(self, service):
        products = [_make_product(price_amount=799), _make_product(price_amount=999)]
        r1 = service.compute_scores(products)
        r2 = service.compute_scores(products)
        assert r1 == r2

    def test_same_input_different_call_same_output(self):
        """Different service instances produce same result."""
        s1 = ScoringService()
        s2 = ScoringService()
        products = [_make_product(), _make_product(price_amount=999, rating=4.0)]
        assert s1.compute_scores(products) == s2.compute_scores(products)


# ===========================================
# WEIGHT COMPUTATION
# ===========================================

class TestWeights:
    def test_default_weights_sum_to_one(self, service):
        weights = service._compute_weights(None)
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_personalized_weights_sum_to_one(self, service):
        prefs = {"priorities": ["price", "quality"], "budget": "budget"}
        weights = service._compute_weights(prefs)
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_price_priority_increases_value_weight(self, service):
        """Price priority in 'other' category boosts value_score."""
        default = service._compute_weights(None)
        prefs = {"priorities": ["price"]}
        adjusted = service._compute_weights(prefs)
        assert adjusted["value_score"] > default["value_score"]

    def test_quality_priority_increases_function_weight(self, service):
        """Quality priority in 'other' category boosts function_score."""
        default = service._compute_weights(None)
        prefs = {"priorities": ["quality"]}
        adjusted = service._compute_weights(prefs)
        assert adjusted["function_score"] > default["function_score"]

    def test_brand_reputation_increases_reliability(self, service):
        default = service._compute_weights(None)
        prefs = {"priorities": ["brand_reputation"]}
        adjusted = service._compute_weights(prefs)
        assert adjusted["reliability_score"] > default["reliability_score"]

    def test_budget_budget_increases_value_weight(self, service):
        """Budget tier in 'other' category boosts value_score."""
        default = service._compute_weights(None)
        prefs = {"budget": "budget"}
        adjusted = service._compute_weights(prefs)
        assert adjusted["value_score"] > default["value_score"]

    def test_premium_budget_increases_function_weight(self, service):
        """Premium tier in 'other' category boosts function_score."""
        default = service._compute_weights(None)
        prefs = {"budget": "premium"}
        adjusted = service._compute_weights(prefs)
        assert adjusted["function_score"] > default["function_score"]

    def test_multiple_priorities_stack(self, service):
        single = service._compute_weights({"priorities": ["price"]})
        double = service._compute_weights({"priorities": ["price", "quality"]})
        assert single != double

    def test_weights_never_negative(self, service):
        prefs = {"priorities": ["quality", "brand_reputation", "latest_features"], "budget": "premium"}
        weights = service._compute_weights(prefs)
        for v in weights.values():
            assert v >= 0.0

    def test_empty_preferences_uses_defaults(self, service):
        weights = service._compute_weights({})
        default = service._compute_weights(None)
        assert weights == default


# ===========================================
# PRICE-RELATED SCORING (via value dimension)
# ===========================================

class TestPriceScoring:
    """Test price-derived scores. For electronics, the value_score dimension
    includes price information via the tier-aware value formula."""

    def test_cheaper_product_scores_higher_on_value(self, service):
        """Cheaper product with same specs gets better value_score."""
        products = [
            _make_product(price_amount=500),
            _make_product(price_amount=900),
        ]
        result = service.compute_scores(products)
        # value_score is the "value" dimension for electronics
        assert result["scores"]["product_0"]["breakdown"]["value_score"] > \
               result["scores"]["product_1"]["breakdown"]["value_score"]

    def test_same_price_equal_value_scores(self, service):
        products = [
            _make_product(price_amount=799),
            _make_product(price_amount=799),
        ]
        result = service.compute_scores(products)
        assert result["scores"]["product_0"]["breakdown"]["value_score"] == \
               result["scores"]["product_1"]["breakdown"]["value_score"]

    def test_missing_price_gets_default(self, service):
        # B0-A v2.2: use DISTINCT specs for the two products so the
        # array-level spec_scores collapse does NOT fire (zero genuine non-
        # MISSING ties per B0-D's 24-query bias corpus). Pre-v2.2 this test
        # used identical specs from the _make_product default; that yielded
        # tied non-MISSING spec_scores which v2.2 now correctly treats as
        # phantom → MISSING. The intent of this test ("specs provide
        # fallback for missing price") is preserved by making spec_raw
        # distinct between products.
        products = [
            _make_product(price_amount=799, specs={
                "display": "6.1-inch OLED",
                "processor": "A17 Pro",
                "ram": "8 GB",
                "storage": "256 GB",
                "battery": "3274 mAh",
                "weight": "171 g",
            }),
            _make_product(price_amount=None, specs={
                "display": "6.7-inch AMOLED",
                "processor": "Snapdragon 8 Gen 3",
                "ram": "12 GB",
                "storage": "512 GB",
                "battery": "5000 mAh",
                "weight": "232 g",
            }),
        ]
        products[1]["price"] = {"amount": None}
        result = service.compute_scores(products)
        # value_score maps to "value" signal (spec+price combo).
        # When price is missing but specs exist (and differ from peer), value
        # falls back to spec_score (not MISSING_SCORE).
        breakdown = result["scores"]["product_1"]["breakdown"]
        assert breakdown["value_score"] != MISSING_SCORE  # specs provide fallback

    def test_zero_price_handled(self, service):
        products = [
            _make_product(price_amount=0),
            _make_product(price_amount=0),
        ]
        products[0]["price"]["amount"] = 0
        products[1]["price"]["amount"] = 0
        result = service.compute_scores(products)
        assert "product_0" in result["scores"]


# ===========================================
# REVIEW SCORING (mapped to futureproof_score for electronics)
# ===========================================

class TestReviewScoring:
    """Review signal maps to futureproof_score for electronics."""

    def test_higher_rating_scores_better(self, service):
        products = [
            _make_product(rating=4.8),
            _make_product(rating=3.5),
        ]
        result = service.compute_scores(products)
        # futureproof_score is the "review" mapped dim for electronics
        assert result["scores"]["product_0"]["breakdown"]["futureproof_score"] > \
               result["scores"]["product_1"]["breakdown"]["futureproof_score"]

    def test_null_rating_gets_default(self, service):
        products = [
            _make_product(rating=4.5),
            _make_product(rating=None),
        ]
        products[1]["rating"] = None
        result = service.compute_scores(products)
        assert result["scores"]["product_1"]["breakdown"]["futureproof_score"] == MISSING_SCORE

    def test_rating_5_is_max(self, service):
        products = [
            _make_product(rating=5.0),
            _make_product(rating=5.0),
        ]
        result = service.compute_scores(products)
        assert result["scores"]["product_0"]["breakdown"]["futureproof_score"] == 100.0


# ===========================================
# SPEC SCORING (mapped to performance_score for electronics)
# ===========================================

class TestSpecScoring:
    """Spec signal maps to performance_score for electronics."""

    def test_better_specs_score_higher(self, service):
        p1 = _make_product(specs={
            "ram": "12 GB", "storage": "512 GB", "battery": "5000 mAh",
        })
        p2 = _make_product(specs={
            "ram": "6 GB", "storage": "128 GB", "battery": "3000 mAh",
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["performance_score"] > \
               result["scores"]["product_1"]["breakdown"]["performance_score"]

    def test_missing_specs_gets_default(self, service):
        p1 = _make_product()
        p2 = _make_product(specs=None)
        p2["specs"] = None
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_1"]["breakdown"]["performance_score"] == MISSING_SCORE

    def test_na_specs_handled(self, service):
        p1 = _make_product(specs={"ram": "N/A", "storage": "N/A"})
        p2 = _make_product(specs={"ram": "8 GB", "storage": "256 GB"})
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["performance_score"] <= \
               result["scores"]["product_1"]["breakdown"]["performance_score"]


# ===========================================
# RELIABILITY SCORING (mapped to build_quality_score for electronics)
# ===========================================

class TestReliabilityScoring:
    """Reliability signal maps to build_quality_score for electronics."""

    def test_high_confidence_scores_better(self, service):
        p1 = _make_product(fact_check={
            "specs_verified": 10, "specs_likely": 0, "specs_flagged": 0,
            "specs_unverified": 0, "price_verified": True,
            "review_sentiment_consistent": True,
        })
        p2 = _make_product(fact_check={
            "specs_verified": 0, "specs_likely": 0, "specs_flagged": 5,
            "specs_unverified": 5, "price_verified": False,
            "review_sentiment_consistent": False,
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["build_quality_score"] > \
               result["scores"]["product_1"]["breakdown"]["build_quality_score"]

    def test_no_fact_check_gets_default(self, service):
        p1 = _make_product()
        p2 = _make_product()
        p2["fact_check"] = None
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_1"]["breakdown"]["build_quality_score"] == MISSING_SCORE


# ===========================================
# POPULARITY SCORING (mapped to ecosystem_score for electronics)
# ===========================================

class TestPopularityScoring:
    """Popularity signal maps to ecosystem_score for electronics."""

    def test_more_reviews_scores_higher(self, service):
        p1 = _make_product(review_count=10000)
        p2 = _make_product(review_count=10)
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["ecosystem_score"] > \
               result["scores"]["product_1"]["breakdown"]["ecosystem_score"]

    def test_null_review_count_and_no_sources(self, service):
        p1 = _make_product(review_count=None)
        p1["reviews"] = {"source_ratings": []}
        p2 = _make_product(review_count=1000)
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["ecosystem_score"] == MISSING_SCORE


# ===========================================
# VALUE SCORING
# ===========================================

class TestValueScoring:
    def test_value_combines_spec_and_price(self, service):
        p1 = _make_product(price_amount=400, specs={
            "ram": "12 GB", "storage": "512 GB", "battery": "5000 mAh",
        })
        p2 = _make_product(price_amount=1200, specs={
            "ram": "6 GB", "storage": "128 GB", "battery": "3000 mAh",
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["value_score"] > \
               result["scores"]["product_1"]["breakdown"]["value_score"]


# ===========================================
# OVERALL & WINNER
# ===========================================

class TestOverallAndWinner:
    def test_winner_index_is_highest_overall(self, service):
        products = [
            _make_product(price_amount=500, rating=4.8),
            _make_product(price_amount=1200, rating=3.5),
        ]
        result = service.compute_scores(products)
        overalls = [
            result["scores"]["product_0"]["overall"],
            result["scores"]["product_1"]["overall"],
        ]
        assert result["winner_index"] == overalls.index(max(overalls))

    def test_win_margin_positive(self, service):
        products = [
            _make_product(price_amount=500),
            _make_product(price_amount=900),
        ]
        result = service.compute_scores(products)
        assert result["win_margin"] >= 0

    def test_overall_score_range_0_to_100(self, service):
        products = [_make_product(), _make_product(price_amount=1200, rating=2.0)]
        result = service.compute_scores(products)
        for key in ["product_0", "product_1"]:
            assert 0 <= result["scores"][key]["overall"] <= 100

    def test_scoring_method_default(self, service):
        products = [_make_product(), _make_product()]
        result = service.compute_scores(products)
        assert result["scoring_method"] == "category_weighted"

    def test_scoring_method_personalized(self, service):
        products = [_make_product(), _make_product()]
        result = service.compute_scores(products, preferences={"priorities": ["price"]})
        assert result["scoring_method"] == "personalized"


# ===========================================
# EDGE CASES
# ===========================================

class TestEdgeCases:
    def test_empty_products_list(self, service):
        result = service.compute_scores([])
        assert result["winner_index"] == 0
        assert result["win_margin"] == 0

    def test_single_product(self, service):
        result = service.compute_scores([_make_product()])
        assert "product_0" in result["scores"]
        assert result["winner_index"] == 0

    def test_all_missing_data(self, service):
        p = {
            "brand": "X", "name": "Y", "category": "other",
            "price": None, "rating": None, "review_count": None,
            "specs": None, "fact_check": None, "reviews": None,
        }
        result = service.compute_scores([p, p])
        for key in ["product_0", "product_1"]:
            assert result["scores"][key]["overall"] == MISSING_SCORE

    def test_missing_data_flagged(self, service):
        p = {
            "brand": "X", "name": "Y", "category": "other",
            "price": None, "rating": None, "review_count": None,
            "specs": None, "fact_check": None, "reviews": None,
        }
        result = service.compute_scores([p, _make_product(category="other")])
        missing = result["scores"]["product_0"]["missing_data"]
        assert missing is not None
        # Should contain "other" category dimension keys, not old universal keys
        assert any(dim in missing for dim in OTHER_DIMS)


# ===========================================
# CATEGORY-SPECIFIC
# ===========================================

class TestCategorySpecific:
    def test_supplement_category(self, service):
        p1 = _make_product(
            category="supplements",
            specs={"count": "120 tablets", "dosage": "2000 IU", "form": "softgel"},
        )
        p2 = _make_product(
            category="supplements",
            specs={"count": "60 tablets", "dosage": "1000 IU", "form": "tablet"},
        )
        result = service.compute_scores([p1, p2])
        # efficacy_score is spec-mapped for supplements
        assert result["scores"]["product_0"]["breakdown"]["efficacy_score"] >= \
               result["scores"]["product_1"]["breakdown"]["efficacy_score"]

    def test_grocery_category(self, service):
        p1 = _make_product(
            category="grocery",
            specs={"nutrition_protein": "25g", "nutrition_calories": "150 kcal"},
        )
        p2 = _make_product(
            category="grocery",
            specs={"nutrition_protein": "10g", "nutrition_calories": "300 kcal"},
        )
        result = service.compute_scores([p1, p2])
        # nutrition_score is spec-mapped for grocery
        assert result["scores"]["product_0"]["breakdown"]["nutrition_score"] > \
               result["scores"]["product_1"]["breakdown"]["nutrition_score"]

    def test_unknown_category_uses_other(self, service):
        p1 = _make_product(category="unknown_xyz", specs={"weight": "500g"})
        p2 = _make_product(category="unknown_xyz", specs={"weight": "1000g"})
        result = service.compute_scores([p1, p2])
        assert "product_0" in result["scores"]
        # Should use "other" dimensions
        assert "function_score" in result["scores"]["product_0"]["breakdown"]


# ===========================================
# EXTRACT NUMBER UTILITY
# ===========================================

class TestExtractNumber:
    def test_simple_integer(self, service):
        assert service._extract_number("256 GB") == 256.0

    def test_decimal(self, service):
        assert service._extract_number("6.1-inch") == 6.1

    def test_comma_number(self, service):
        assert service._extract_number("3,274 mAh") == 3274.0

    def test_no_number(self, service):
        assert service._extract_number("OLED display") is None

    def test_empty_string(self, service):
        assert service._extract_number("") is None

    def test_none_input(self, service):
        assert service._extract_number(None) is None


# ===========================================
# SCORES SUMMARY (for GPT prompt)
# ===========================================

class TestScoresSummary:
    def test_builds_summary_string(self, service):
        products = [_make_product(), _make_product(price_amount=999)]
        result = service.compute_scores(products)
        summary = service.build_scores_summary(result, ["iPhone 15", "Galaxy S24"])
        assert "iPhone 15" in summary
        assert "Galaxy S24" in summary
        assert "/100" in summary
        assert "Score winner" in summary

    def test_empty_result_returns_empty_string(self, service):
        summary = service.build_scores_summary({}, ["A", "B"])
        assert summary == ""

    def test_none_result_returns_empty_string(self, service):
        summary = service.build_scores_summary(None, ["A", "B"])
        assert summary == ""


# ===========================================
# ADDITIONAL COVERAGE: TIE HANDLING
# ===========================================

class TestTieHandling:
    def test_identical_products_tie(self, service):
        p1 = _make_product(price_amount=799, rating=4.5)
        p2 = _make_product(price_amount=799, rating=4.5)
        result = service.compute_scores([p1, p2])
        assert result["win_margin"] == 0
        assert result["scores"]["product_0"]["overall"] == result["scores"]["product_1"]["overall"]

    def test_identical_products_equal_breakdowns(self, service):
        p1 = _make_product()
        p2 = _make_product()
        result = service.compute_scores([p1, p2])
        b0 = result["scores"]["product_0"]["breakdown"]
        b1 = result["scores"]["product_1"]["breakdown"]
        for dim in b0:
            assert b0[dim] == b1[dim], f"Mismatch on {dim}: {b0[dim]} != {b1[dim]}"


# ===========================================
# ADDITIONAL COVERAGE: ALL PRIORITIES STACKING
# ===========================================

class TestAllPrioritiesStacking:
    def test_all_priorities_weights_sum_to_one(self, service):
        all_priorities = [
            "price", "quality", "brand_reputation", "durability",
            "latest_features", "ease_of_use", "eco_friendly", "health_safety",
        ]
        prefs = {"priorities": all_priorities, "budget": "budget"}
        weights = service._compute_weights(prefs)
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_all_priorities_no_negative_weights(self, service):
        all_priorities = [
            "price", "quality", "brand_reputation", "durability",
            "latest_features", "ease_of_use", "eco_friendly", "health_safety",
        ]
        prefs = {"priorities": all_priorities, "budget": "premium"}
        weights = service._compute_weights(prefs)
        for k, v in weights.items():
            assert v >= 0.0, f"{k} has negative weight: {v}"

    def test_three_priorities_weights_valid(self, service):
        prefs = {"priorities": ["price", "quality", "eco_friendly"], "budget": "mid"}
        weights = service._compute_weights(prefs)
        assert abs(sum(weights.values()) - 1.0) < 1e-9
        for v in weights.values():
            assert v >= 0.0


# ===========================================
# ADDITIONAL COVERAGE: MORE CATEGORIES
# ===========================================

class TestMoreCategories:
    """Test category-specific scoring for beauty/other categories."""

    def test_makeup_category(self, service):
        p1 = _make_product(category="makeup", specs={
            "shade_range": "40 shades", "spf": "30", "volume": "30ml",
        })
        p2 = _make_product(category="makeup", specs={
            "shade_range": "10 shades", "spf": "15", "volume": "15ml",
        })
        result = service.compute_scores([p1, p2])
        # shade_score is spec-mapped for makeup
        assert result["scores"]["product_0"]["breakdown"]["shade_score"] > \
               result["scores"]["product_1"]["breakdown"]["shade_score"]

    def test_skincare_category(self, service):
        p1 = _make_product(category="skincare", specs={
            "spf": "50", "volume": "50ml",
        })
        p2 = _make_product(category="skincare", specs={
            "spf": "15", "volume": "30ml",
        })
        result = service.compute_scores([p1, p2])
        # actives_score is spec-mapped for skincare
        assert result["scores"]["product_0"]["breakdown"]["actives_score"] >= \
               result["scores"]["product_1"]["breakdown"]["actives_score"]

    def test_fragrances_category(self, service):
        p1 = _make_product(category="fragrances", specs={
            "volume": "100ml", "longevity": "8 hours",
        })
        p2 = _make_product(category="fragrances", specs={
            "volume": "50ml", "longevity": "4 hours",
        })
        result = service.compute_scores([p1, p2])
        # character_score is spec-mapped for fragrances
        assert result["scores"]["product_0"]["breakdown"]["character_score"] > \
               result["scores"]["product_1"]["breakdown"]["character_score"]

    def test_haircare_category(self, service):
        p1 = _make_product(category="haircare", specs={
            "volume": "500ml",
        })
        p2 = _make_product(category="haircare", specs={
            "volume": "250ml",
        })
        result = service.compute_scores([p1, p2])
        # hair_match_score is spec-mapped for haircare
        assert result["scores"]["product_0"]["breakdown"]["hair_match_score"] >= \
               result["scores"]["product_1"]["breakdown"]["hair_match_score"]


class TestWeightCapping:
    """Test that personalization weight shifts are capped at +/-30% of defaults."""

    def test_single_priority_capped(self):
        service = ScoringService()
        weights = service._compute_weights({"priorities": ["price"]})
        # "other" category: value_score = 0.15. With price priority: +0.15 -> capped at 0.15*1.3
        assert weights["value_score"] <= 0.40
        assert weights["function_score"] >= 0.05

    def test_multiple_priorities_capped(self):
        service = ScoringService()
        weights = service._compute_weights({
            "priorities": ["price", "quality", "durability"],
            "budget": "budget"
        })
        for dim, default_val in CATEGORY_DIMENSION_WEIGHTS["other"].items():
            if default_val > 0:
                assert weights[dim] <= default_val * 2.5, \
                    f"{dim} is {weights[dim]:.3f}, default {default_val:.3f} — too aggressive"

    def test_weight_cap_preserves_normalization(self):
        service = ScoringService()
        weights = service._compute_weights({
            "priorities": ["price", "health_safety"],
            "budget": "premium"
        })
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_no_preferences_unchanged(self):
        service = ScoringService()
        weights = service._compute_weights(None)
        for dim, val in CATEGORY_DIMENSION_WEIGHTS["other"].items():
            assert abs(weights[dim] - val) < 0.001

    def test_empty_preferences_unchanged(self):
        service = ScoringService()
        weights = service._compute_weights({})
        for dim, val in CATEGORY_DIMENSION_WEIGHTS["other"].items():
            assert abs(weights[dim] - val) < 0.001


# ===========================================
# CATEGORY WEIGHT SELECTION
# ===========================================

class TestCategoryWeightSelection:
    """Test category-specific weight profiles with new dimension keys."""

    def test_category_weights_electronics(self):
        w = CATEGORY_WEIGHTS["electronics"]
        assert w["performance_score"] == 0.25
        assert w["build_quality_score"] == 0.15
        assert abs(sum(w.values()) - 1.0) < 0.001

    def test_category_weights_fashion(self):
        w = CATEGORY_WEIGHTS["fashion"]
        assert w["craft_score"] == 0.25
        assert w["fit_score"] == 0.20
        assert w["cpw_score"] == 0.10

    def test_category_weights_supplements(self):
        w = CATEGORY_WEIGHTS["supplements"]
        assert w["efficacy_score"] == 0.30
        assert w["safety_score"] == 0.25

    def test_category_weights_fragrances(self):
        w = CATEGORY_WEIGHTS["fragrances"]
        assert w["character_score"] == 0.25
        assert w["longevity_score"] == 0.25

    def test_category_weights_grocery(self):
        w = CATEGORY_WEIGHTS["grocery"]
        assert w["nutrition_score"] == 0.25
        assert w["ingredient_score"] == 0.20

    def test_all_category_weights_sum_to_one(self):
        for cat, weights in CATEGORY_WEIGHTS.items():
            assert abs(sum(weights.values()) - 1.0) < 0.001, f"{cat} weights sum to {sum(weights.values())}"

    def test_all_categories_have_six_dimensions(self):
        for cat, weights in CATEGORY_WEIGHTS.items():
            assert len(weights) == 6, f"{cat} has {len(weights)} dimensions, expected 6"
            # Keys should match CATEGORY_DIMENSIONS for this category
            expected_dims = set(CATEGORY_DIMENSIONS[cat])
            assert set(weights.keys()) == expected_dims, f"{cat} keys mismatch: {set(weights.keys())} != {expected_dims}"

    def test_unknown_category_falls_back_to_other(self):
        service = ScoringService()
        weights = service._compute_weights(None, "nonexistent_category")
        assert weights == CATEGORY_DIMENSION_WEIGHTS["other"]

    def test_category_passed_to_compute_weights(self):
        service = ScoringService()
        elec_weights = service._compute_weights(None, "electronics")
        fashion_weights = service._compute_weights(None, "fashion")
        assert elec_weights != fashion_weights

    def test_personalized_weights_use_category_base(self):
        service = ScoringService()
        prefs = {"priorities": ["price"]}
        elec = service._compute_weights(prefs, "electronics")
        other = service._compute_weights(prefs, "other")
        assert elec != other


# ===========================================
# PRICE TIER DETECTION
# ===========================================

class TestPriceTierDetection:
    def test_price_tier_budget(self):
        assert ScoringService._detect_price_tier(5.0) == "budget"

    def test_price_tier_mid(self):
        assert ScoringService._detect_price_tier(30.0) == "mid"

    def test_price_tier_premium(self):
        assert ScoringService._detect_price_tier(100.0) == "premium"

    def test_price_tier_luxury(self):
        # Bundle C § 3e/3f — under the default 'other_light' sub-scale,
        # 189–500 is luxury, 500+ is the new top_tier slot.
        assert ScoringService._detect_price_tier(300.0) == "luxury"

    def test_price_tier_top_tier(self):
        # Bundle C § 3a — 500+ BHD under other_light → top_tier.
        assert ScoringService._detect_price_tier(800.0) == "top_tier"

    def test_price_tier_boundary_budget_mid(self):
        tier = ScoringService._detect_price_tier(15.0)
        assert tier in ("budget", "mid")

    def test_cross_tier_different(self):
        assert ScoringService._is_cross_tier(["budget", "luxury"]) is True

    def test_cross_tier_same(self):
        assert ScoringService._is_cross_tier(["luxury", "luxury"]) is False

    def test_cross_tier_adjacent(self):
        result = ScoringService._is_cross_tier(["budget", "mid"])
        assert isinstance(result, bool)


# ===========================================
# VALUE SCORE REDESIGN
# ===========================================

class TestValueScoreRedesign:
    def test_value_score_cross_tier_luxury(self):
        service = ScoringService()
        score = service._compute_value_score(85, 30, "luxury", True)
        assert 45 <= score <= 55

    def test_value_score_cross_tier_budget(self):
        service = ScoringService()
        score = service._compute_value_score(70, 95, "budget", True)
        assert score > 55

    def test_value_score_same_tier(self):
        # S3 L3 v2 (b) lever 1 — value-for-money default coeffs spec 0.70/price 0.30
        # (was 0.60/0.40) so "what you get" dominates "how cheap".
        service = ScoringService()
        score = service._compute_value_score(80, 60, "mid", False)
        expected = 80 * 0.70 + 60 * 0.30
        assert abs(score - expected) < 0.5

    def test_value_score_missing_spec(self):
        service = ScoringService()
        score = service._compute_value_score(MISSING_SCORE, 70, "mid", False)
        assert score == 70

    def test_value_score_missing_price(self):
        service = ScoringService()
        score = service._compute_value_score(70, MISSING_SCORE, "mid", False)
        assert score == 70

    def test_value_score_both_missing(self):
        service = ScoringService()
        score = service._compute_value_score(MISSING_SCORE, MISSING_SCORE, "mid", False)
        assert score == MISSING_SCORE


# ===========================================
# DIMENSION WINNERS
# ===========================================

class TestDimensionWinners:
    """Test per-dimension winner computation with new category-specific keys."""

    def test_dimension_winners_clear_winner(self):
        """Uses 'other' category dims via the breakdown fallback."""
        service = ScoringService()
        result = {"scores": {
            "product_0": {"breakdown": {"function_score": 80, "build_score": 60, "review_score": 50, "value_score": 50, "reliability_score": 50, "feature_match_score": 50}},
            "product_1": {"breakdown": {"function_score": 40, "build_score": 90, "review_score": 50, "value_score": 50, "reliability_score": 50, "feature_match_score": 50}},
        }}
        winners = service.compute_dimension_winners(result, ["A", "B"], "other")
        assert winners["function_score"]["winner"] == "A"
        assert winners["build_score"]["winner"] == "B"

    def test_dimension_winners_tie(self):
        service = ScoringService()
        result = {"scores": {
            "product_0": {"breakdown": {"function_score": 50, "build_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "feature_match_score": 50}},
            "product_1": {"breakdown": {"function_score": 51, "build_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "feature_match_score": 50}},
        }}
        winners = service.compute_dimension_winners(result, ["A", "B"], "other")
        assert winners["function_score"]["winner"] == "tie"

    def test_dimension_winners_both_missing(self):
        # S3 L3 v2 (d) — missingness is tracked via the EXPLICIT missing_data
        # list, NOT by `== MISSING_SCORE` value-equality (a computed 50 is a real
        # score). To mark function_score missing on both products, list it in
        # each product's missing_data.
        service = ScoringService()
        result = {"scores": {
            "product_0": {"breakdown": {"function_score": MISSING_SCORE, "build_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "feature_match_score": 50},
                          "missing_data": ["function_score"]},
            "product_1": {"breakdown": {"function_score": MISSING_SCORE, "build_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "feature_match_score": 50},
                          "missing_data": ["function_score"]},
        }}
        winners = service.compute_dimension_winners(result, ["A", "B"], "other")
        assert winners["function_score"]["winner"] == "N/A"
        assert winners["function_score"]["margin"] is None


# ===========================================
# COVERAGE THRESHOLD + PERSONALIZATION
# ===========================================

class TestCoverageThreshold:
    def test_fashion_coverage_no_penalty_at_30_percent(self, service):
        specs_with_3 = {
            "material": "Italian leather",
            "style": "Classic",
            "color": "Black",
        }
        score = service._score_specs(specs_with_3, "fashion")
        assert score > 0

    def test_electronics_coverage_penalized_at_30_percent(self, service):
        specs_with_few = {
            "ram": "8 GB",
            "storage": "256 GB",
        }
        score_few = service._score_specs(specs_with_few, "electronics")
        specs_with_many = {
            "ram": "8 GB",
            "storage": "256 GB",
            "battery": "4000 mAh",
            "display": "6.1-inch OLED",
            "processor": "A17 Pro",
            "rear_camera": "48 MP",
            "front_camera": "12 MP",
        }
        score_many = service._score_specs(specs_with_many, "electronics")
        assert score_many > score_few

    def test_personalization_capped_at_category_weight(self):
        """Personalization shift should be capped relative to category base weight."""
        service = ScoringService()
        # Fashion base: cpw_score = 0.10 (the "value" dimension for fashion)
        prefs = {"priorities": ["price"], "budget": "budget"}
        weights = service._compute_weights(prefs, "fashion")
        fashion_base = CATEGORY_WEIGHTS["fashion"]["cpw_score"]
        # Verify the final weight is reasonable (not 2x+ the base)
        assert weights["cpw_score"] < fashion_base * 2.0


# ===========================================
# VALUE BADGES
# ===========================================

class TestValueBadges:
    def test_great_value_non_luxury(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=80, price_tier="mid")
        assert badge == "great_value"

    def test_great_value_budget(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=75, price_tier="budget")
        assert badge == "great_value"

    def test_luxury_high_value_gets_fair_price(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=85, price_tier="luxury")
        assert badge == "fair_price"

    def test_fair_price_mid_range(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=60, price_tier="mid")
        assert badge == "fair_price"

    def test_fair_price_boundary_50(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=50, price_tier="premium")
        assert badge == "fair_price"

    def test_premium_price(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=35, price_tier="mid")
        assert badge == "premium_price"

    def test_overpriced(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=15, price_tier="premium")
        assert badge == "overpriced"

    def test_overpriced_boundary_24(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=24, price_tier="mid")
        assert badge == "overpriced"

    def test_boundary_75_non_luxury(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=75, price_tier="premium")
        assert badge == "great_value"

    def test_boundary_25(self):
        service = ScoringService()
        badge = service.compute_value_badge(value_score=25, price_tier="mid")
        assert badge == "premium_price"


# ===========================================
# TRADEOFF PAIRS
# ===========================================

class TestTradeoffPairs:
    """Tests for compute_tradeoff_pairs() — dimension keys are arbitrary strings."""

    def test_basic_tradeoff(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 12.0},
            "build_quality_score": {"winner": "tie", "margin": 2.0},
            "feature_score": {"winner": "Product A", "margin": 8.0},
            "ecosystem_score": {"winner": "tie", "margin": 1.0},
            "futureproof_score": {"winner": "Product B", "margin": 6.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) >= 1
        assert tradeoffs[0]["winner_wins"]["product"] == "Product A"
        assert tradeoffs[0]["loser_wins"]["product"] == "Product B"

    def test_winner_index_one(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 12.0},
            "build_quality_score": {"winner": "tie", "margin": 2.0},
            "feature_score": {"winner": "tie", "margin": 2.0},
            "ecosystem_score": {"winner": "tie", "margin": 1.0},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=1)
        assert len(tradeoffs) == 1
        assert tradeoffs[0]["winner_wins"]["product"] == "Product B"
        assert tradeoffs[0]["loser_wins"]["product"] == "Product A"

    def test_filters_small_margins(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 3.0},
            "value_score": {"winner": "Product B", "margin": 4.0},
            "build_quality_score": {"winner": "tie", "margin": 1.0},
            "feature_score": {"winner": "tie", "margin": 2.0},
            "ecosystem_score": {"winner": "tie", "margin": 0.5},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 0

    def test_max_three_tradeoffs(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 20.0},
            "value_score": {"winner": "Product B", "margin": 18.0},
            "build_quality_score": {"winner": "Product A", "margin": 15.0},
            "feature_score": {"winner": "Product B", "margin": 12.0},
            "ecosystem_score": {"winner": "Product A", "margin": 10.0},
            "futureproof_score": {"winner": "Product B", "margin": 8.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) <= 3

    def test_sorted_by_impact(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 10.0},
            "value_score": {"winner": "Product B", "margin": 25.0},
            "build_quality_score": {"winner": "Product A", "margin": 20.0},
            "feature_score": {"winner": "Product B", "margin": 8.0},
            "ecosystem_score": {"winner": "tie", "margin": 2.0},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) >= 1
        first_combined = tradeoffs[0]["winner_wins"]["margin"] + tradeoffs[0]["loser_wins"]["margin"]
        for t in tradeoffs[1:]:
            combined = t["winner_wins"]["margin"] + t["loser_wins"]["margin"]
            assert first_combined >= combined

    def test_no_tradeoff_when_one_side_dominates(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product A", "margin": 12.0},
            "build_quality_score": {"winner": "Product A", "margin": 10.0},
            "feature_score": {"winner": "Product A", "margin": 8.0},
            "ecosystem_score": {"winner": "Product A", "margin": 7.0},
            "futureproof_score": {"winner": "Product A", "margin": 6.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 0

    def test_na_dimensions_excluded(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "N/A", "margin": None},
            "build_quality_score": {"winner": "Product B", "margin": 10.0},
            "feature_score": {"winner": "tie", "margin": 2.0},
            "ecosystem_score": {"winner": "tie", "margin": 1.0},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 1
        assert tradeoffs[0]["winner_wins"]["dimension"] == "performance_score"
        assert tradeoffs[0]["loser_wins"]["dimension"] == "build_quality_score"

    def test_tradeoff_structure(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 12.0},
            "build_quality_score": {"winner": "tie", "margin": 2.0},
            "feature_score": {"winner": "tie", "margin": 2.0},
            "ecosystem_score": {"winner": "tie", "margin": 1.0},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 1
        t = tradeoffs[0]
        assert "dimension" in t["winner_wins"]
        assert "product" in t["winner_wins"]
        assert "margin" in t["winner_wins"]
        assert "dimension" in t["loser_wins"]
        assert "product" in t["loser_wins"]
        assert "margin" in t["loser_wins"]

    # Faithful-Results F4.2 — when the winner SWEEPS all dims, the dedicated
    # "where the runner-up wins" card was empty. With the optional `scores`
    # param, fall back to the loser's RELATIVELY-STRONGEST dimension so the card
    # renders. The 3-arg call (no scores) stays [] — backward-compatible.

    def _sweep_winners(self):
        return {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product A", "margin": 12.0},
            "build_quality_score": {"winner": "Product A", "margin": 10.0},
            "feature_score": {"winner": "Product A", "margin": 8.0},
            "ecosystem_score": {"winner": "Product A", "margin": 7.0},
            "futureproof_score": {"winner": "Product A", "margin": 6.0},
        }

    def test_sweep_without_scores_stays_empty(self):
        # Backward-compat: no scores param → no fallback (existing behavior).
        service = ScoringService()
        tradeoffs = service.compute_tradeoff_pairs(
            self._sweep_winners(), ["Product A", "Product B"], winner_index=0
        )
        assert tradeoffs == []

    def test_sweep_with_scores_falls_back_to_loser_strongest(self):
        service = ScoringService()
        scores = {
            "product_0": {"breakdown": {
                "performance_score": 90, "value_score": 85, "build_quality_score": 88,
                "feature_score": 80, "ecosystem_score": 75, "futureproof_score": 70,
            }},
            # Loser's RELATIVELY strongest dim is value_score (62 — highest of theirs).
            "product_1": {"breakdown": {
                "performance_score": 55, "value_score": 62, "build_quality_score": 50,
                "feature_score": 48, "ecosystem_score": 45, "futureproof_score": 40,
            }},
        }
        tradeoffs = service.compute_tradeoff_pairs(
            self._sweep_winners(), ["Product A", "Product B"], winner_index=0, scores=scores
        )
        assert len(tradeoffs) >= 1
        # The fallback pairs the winner's top dim with the loser's strongest dim.
        assert tradeoffs[0]["loser_wins"]["product"] == "Product B"
        assert tradeoffs[0]["loser_wins"]["dimension"] == "value_score"

    def test_sweep_fallback_winner_idx_1(self):
        service = ScoringService()
        winners = {
            "performance_score": {"winner": "Product B", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 12.0},
            "build_quality_score": {"winner": "Product B", "margin": 10.0},
            "feature_score": {"winner": "Product B", "margin": 8.0},
            "ecosystem_score": {"winner": "Product B", "margin": 7.0},
            "futureproof_score": {"winner": "Product B", "margin": 6.0},
        }
        scores = {
            "product_0": {"breakdown": {  # the LOSER here
                "performance_score": 50, "value_score": 48, "build_quality_score": 66,
                "feature_score": 45, "ecosystem_score": 40, "futureproof_score": 38,
            }},
            "product_1": {"breakdown": {
                "performance_score": 90, "value_score": 85, "build_quality_score": 80,
                "feature_score": 78, "ecosystem_score": 75, "futureproof_score": 70,
            }},
        }
        tradeoffs = service.compute_tradeoff_pairs(
            winners, ["Product A", "Product B"], winner_index=1, scores=scores
        )
        assert len(tradeoffs) >= 1
        assert tradeoffs[0]["loser_wins"]["product"] == "Product A"
        assert tradeoffs[0]["loser_wins"]["dimension"] == "build_quality_score"

    def test_normal_two_sided_unaffected_by_scores(self):
        # When the loser already wins a dim, scores does NOT change the pairing.
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 12.0},
            "build_quality_score": {"winner": "tie", "margin": 2.0},
            "feature_score": {"winner": "tie", "margin": 2.0},
            "ecosystem_score": {"winner": "tie", "margin": 1.0},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        scores = {
            "product_0": {"breakdown": {"performance_score": 90, "value_score": 60}},
            "product_1": {"breakdown": {"performance_score": 70, "value_score": 80}},
        }
        tradeoffs = service.compute_tradeoff_pairs(
            dimension_winners, ["Product A", "Product B"], winner_index=0, scores=scores
        )
        assert len(tradeoffs) == 1
        assert tradeoffs[0]["loser_wins"]["dimension"] == "value_score"


# ===========================================
# CONFIDENCE INDICATORS
# ===========================================

class TestConfidenceIndicators:
    def test_high_confidence_all_strong(self):
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "local_bhd", "retailer": "Amazon"},
                "rating": 4.5,
                "review_count": 1200,
                "rating_verified": True,
                "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                "fact_check": {"specs_verified": 8, "specs_likely": 2, "specs_unverified": 0, "specs_flagged": 0},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=3, cached=False)
        assert conf["overall"] == "high"
        assert conf["price"]["source_count"] == 3
        assert conf["price"]["method"] == "retailer_verified"
        assert conf["rating"]["review_count"] == 1200
        assert conf["rating"]["verified"] is True
        assert conf["specs"]["verified_pct"] > 70

    def test_medium_confidence_one_weak(self):
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "estimated", "retailer": None},
                "rating": 4.5,
                "review_count": 500,
                "rating_verified": True,
                "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                "fact_check": {"specs_verified": 8, "specs_likely": 2, "specs_unverified": 0, "specs_flagged": 0},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=0, cached=False)
        assert conf["overall"] == "medium"
        assert conf["price"]["method"] == "estimated"

    def test_low_confidence_two_weak(self):
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "estimated", "retailer": None},
                "rating": None,
                "review_count": 0,
                "rating_verified": False,
                "rating_source": None,
                "fact_check": {"specs_verified": 1, "specs_likely": 1, "specs_unverified": 5, "specs_flagged": 3},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=0, cached=False)
        assert conf["overall"] == "low"

    def test_freshness_live(self):
        service = ScoringService()
        products = [self._make_strong_product()]
        conf = service.compute_confidence(products, shopping_count=3, cached=False)
        assert conf["price"]["freshness"] == "live"

    def test_freshness_cached(self):
        service = ScoringService()
        products = [self._make_strong_product()]
        conf = service.compute_confidence(products, shopping_count=3, cached=True)
        assert conf["price"]["freshness"] == "cached"

    def test_source_method_converted(self):
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "converted_usd", "retailer": "BestBuy"},
                "rating": 4.0,
                "review_count": 300,
                "rating_verified": True,
                "rating_source": {"name": "BestBuy", "url": "https://bestbuy.com"},
                "fact_check": {"specs_verified": 5, "specs_likely": 3, "specs_unverified": 2, "specs_flagged": 0},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=2, cached=False)
        assert conf["price"]["method"] == "converted"

    def test_specs_verified_pct_calculation(self):
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "local_bhd", "retailer": "Amazon"},
                "rating": 4.5,
                "review_count": 100,
                "rating_verified": True,
                "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                "fact_check": {"specs_verified": 6, "specs_likely": 2, "specs_unverified": 1, "specs_flagged": 1},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=2, cached=False)
        assert conf["specs"]["verified_pct"] == 60
        assert conf["specs"]["citation_count"] == 10

    def test_multiple_products_uses_first(self):
        service = ScoringService()
        products = [self._make_strong_product(), self._make_strong_product()]
        conf = service.compute_confidence(products, shopping_count=3, cached=False)
        assert conf["overall"] == "high"

    def test_empty_products_list(self):
        service = ScoringService()
        conf = service.compute_confidence(products=[], shopping_count=0, cached=False)
        assert conf["overall"] == "low"
        assert conf["price"]["method"] == "estimated"
        assert conf["rating"]["review_count"] == 0
        assert conf["specs"]["verified_pct"] == 0

    @staticmethod
    def _make_strong_product():
        return {
            "price": {"source_method": "local_bhd", "retailer": "Amazon"},
            "rating": 4.5,
            "review_count": 1000,
            "rating_verified": True,
            "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
            "fact_check": {"specs_verified": 8, "specs_likely": 2, "specs_unverified": 0, "specs_flagged": 0},
        }


class TestTradeoffPairsWinnerIndex:
    def test_winner_index_1(self):
        service = ScoringService()
        dimension_winners = {
            "performance_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 20.0},
            "build_quality_score": {"winner": "Product B", "margin": 10.0},
            "feature_score": {"winner": "tie", "margin": 2.0},
            "ecosystem_score": {"winner": "tie", "margin": 1.0},
            "futureproof_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=1)
        assert len(tradeoffs) == 1
        assert tradeoffs[0]["winner_wins"]["product"] == "Product B"
        assert tradeoffs[0]["loser_wins"]["product"] == "Product A"
        assert tradeoffs[0]["loser_wins"]["dimension"] == "performance_score"

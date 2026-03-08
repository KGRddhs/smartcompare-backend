"""
Tests for scoring_service.py — deterministic product scoring engine.
Target: 90%+ coverage, 25+ tests.
"""
import pytest
from app.services.scoring_service import (
    ScoringService,
    get_scoring_service,
    DEFAULT_WEIGHTS,
    MISSING_SCORE,
    PRIORITY_ADJUSTMENTS,
    BUDGET_ADJUSTMENTS,
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

    def test_price_priority_increases_price_weight(self, service):
        default = service._compute_weights(None)
        prefs = {"priorities": ["price"]}
        adjusted = service._compute_weights(prefs)
        assert adjusted["price_score"] > default["price_score"]

    def test_quality_priority_increases_spec_weight(self, service):
        default = service._compute_weights(None)
        prefs = {"priorities": ["quality"]}
        adjusted = service._compute_weights(prefs)
        assert adjusted["spec_score"] > default["spec_score"]

    def test_brand_reputation_increases_reliability(self, service):
        default = service._compute_weights(None)
        prefs = {"priorities": ["brand_reputation"]}
        adjusted = service._compute_weights(prefs)
        assert adjusted["reliability_score"] > default["reliability_score"]

    def test_budget_budget_increases_price_weight(self, service):
        default = service._compute_weights(None)
        prefs = {"budget": "budget"}
        adjusted = service._compute_weights(prefs)
        assert adjusted["price_score"] > default["price_score"]

    def test_premium_budget_increases_spec_weight(self, service):
        default = service._compute_weights(None)
        prefs = {"budget": "premium"}
        adjusted = service._compute_weights(prefs)
        assert adjusted["spec_score"] > default["spec_score"]

    def test_multiple_priorities_stack(self, service):
        single = service._compute_weights({"priorities": ["price"]})
        double = service._compute_weights({"priorities": ["price", "quality"]})
        # With both price and quality, price weight should be different than just price alone
        assert single != double

    def test_weights_never_negative(self, service):
        # Extreme: all priorities that reduce price
        prefs = {"priorities": ["quality", "brand_reputation", "latest_features"], "budget": "premium"}
        weights = service._compute_weights(prefs)
        for v in weights.values():
            assert v >= 0.0

    def test_empty_preferences_uses_defaults(self, service):
        weights = service._compute_weights({})
        default = service._compute_weights(None)
        assert weights == default


# ===========================================
# PRICE SCORING
# ===========================================

class TestPriceScoring:
    def test_cheaper_product_scores_higher(self, service):
        products = [
            _make_product(price_amount=500),
            _make_product(price_amount=900),
        ]
        result = service.compute_scores(products)
        assert result["scores"]["product_0"]["breakdown"]["price_score"] > \
               result["scores"]["product_1"]["breakdown"]["price_score"]

    def test_same_price_equal_scores(self, service):
        products = [
            _make_product(price_amount=799),
            _make_product(price_amount=799),
        ]
        result = service.compute_scores(products)
        assert result["scores"]["product_0"]["breakdown"]["price_score"] == \
               result["scores"]["product_1"]["breakdown"]["price_score"]

    def test_missing_price_gets_default(self, service):
        products = [
            _make_product(price_amount=799),
            _make_product(price_amount=None),
        ]
        # Null out the price
        products[1]["price"] = {"amount": None}
        result = service.compute_scores(products)
        assert result["scores"]["product_1"]["breakdown"]["price_score"] == MISSING_SCORE

    def test_zero_price_handled(self, service):
        products = [
            _make_product(price_amount=0),
            _make_product(price_amount=0),
        ]
        products[0]["price"]["amount"] = 0
        products[1]["price"]["amount"] = 0
        result = service.compute_scores(products)
        # Should not crash, both get default
        assert "product_0" in result["scores"]


# ===========================================
# REVIEW SCORING
# ===========================================

class TestReviewScoring:
    def test_higher_rating_scores_better(self, service):
        products = [
            _make_product(rating=4.8),
            _make_product(rating=3.5),
        ]
        result = service.compute_scores(products)
        assert result["scores"]["product_0"]["breakdown"]["review_score"] > \
               result["scores"]["product_1"]["breakdown"]["review_score"]

    def test_null_rating_gets_default(self, service):
        products = [
            _make_product(rating=4.5),
            _make_product(rating=None),
        ]
        products[1]["rating"] = None
        result = service.compute_scores(products)
        assert result["scores"]["product_1"]["breakdown"]["review_score"] == MISSING_SCORE

    def test_rating_5_is_max(self, service):
        products = [
            _make_product(rating=5.0),
            _make_product(rating=5.0),
        ]
        result = service.compute_scores(products)
        assert result["scores"]["product_0"]["breakdown"]["review_score"] == 100.0


# ===========================================
# SPEC SCORING
# ===========================================

class TestSpecScoring:
    def test_better_specs_score_higher(self, service):
        p1 = _make_product(specs={
            "ram": "12 GB", "storage": "512 GB", "battery": "5000 mAh",
        })
        p2 = _make_product(specs={
            "ram": "6 GB", "storage": "128 GB", "battery": "3000 mAh",
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] > \
               result["scores"]["product_1"]["breakdown"]["spec_score"]

    def test_missing_specs_gets_default(self, service):
        p1 = _make_product()
        p2 = _make_product(specs=None)
        p2["specs"] = None
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_1"]["breakdown"]["spec_score"] == MISSING_SCORE

    def test_na_specs_handled(self, service):
        p1 = _make_product(specs={"ram": "N/A", "storage": "N/A"})
        p2 = _make_product(specs={"ram": "8 GB", "storage": "256 GB"})
        result = service.compute_scores([p1, p2])
        # p1 with N/A specs should score lower
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] <= \
               result["scores"]["product_1"]["breakdown"]["spec_score"]


# ===========================================
# RELIABILITY SCORING
# ===========================================

class TestReliabilityScoring:
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
        assert result["scores"]["product_0"]["breakdown"]["reliability_score"] > \
               result["scores"]["product_1"]["breakdown"]["reliability_score"]

    def test_no_fact_check_gets_default(self, service):
        p1 = _make_product()
        p2 = _make_product()
        p2["fact_check"] = None
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_1"]["breakdown"]["reliability_score"] == MISSING_SCORE


# ===========================================
# POPULARITY SCORING
# ===========================================

class TestPopularityScoring:
    def test_more_reviews_scores_higher(self, service):
        p1 = _make_product(review_count=10000)
        p2 = _make_product(review_count=10)
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["popularity_score"] > \
               result["scores"]["product_1"]["breakdown"]["popularity_score"]

    def test_null_review_count_and_no_sources(self, service):
        p1 = _make_product(review_count=None)
        p1["reviews"] = {"source_ratings": []}
        p2 = _make_product(review_count=1000)
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["popularity_score"] == MISSING_SCORE


# ===========================================
# VALUE SCORING
# ===========================================

class TestValueScoring:
    def test_value_combines_spec_and_price(self, service):
        # Product with great specs AND low price = great value
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
        assert result["scoring_method"] == "default"

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
        # Should not crash, all defaults
        for key in ["product_0", "product_1"]:
            assert result["scores"][key]["overall"] == MISSING_SCORE

    def test_missing_data_flagged(self, service):
        p = {
            "brand": "X", "name": "Y", "category": "other",
            "price": None, "rating": None, "review_count": None,
            "specs": None, "fact_check": None, "reviews": None,
        }
        result = service.compute_scores([p, _make_product()])
        missing = result["scores"]["product_0"]["missing_data"]
        assert missing is not None
        assert "price_score" in missing


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
        # p1 has higher count and dosage
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] >= \
               result["scores"]["product_1"]["breakdown"]["spec_score"]

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
        # p1: more protein (higher=better), fewer calories (lower=better)
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] > \
               result["scores"]["product_1"]["breakdown"]["spec_score"]

    def test_unknown_category_uses_other(self, service):
        p1 = _make_product(category="unknown_xyz", specs={"weight": "500g"})
        p2 = _make_product(category="unknown_xyz", specs={"weight": "1000g"})
        result = service.compute_scores([p1, p2])
        assert "product_0" in result["scores"]


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

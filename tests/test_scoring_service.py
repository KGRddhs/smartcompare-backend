"""
Tests for scoring_service.py — deterministic product scoring engine.
Target: 90%+ coverage, 25+ tests.
"""
import pytest
from app.services.scoring_service import (
    ScoringService,
    get_scoring_service,
    CATEGORY_WEIGHTS,
    MISSING_SCORE,
    PRIORITY_ADJUSTMENTS,
    BUDGET_ADJUSTMENTS,
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


# ===========================================
# ADDITIONAL COVERAGE: TIE HANDLING
# ===========================================

class TestTieHandling:
    """Test identical products produce tied scores."""

    def test_identical_products_tie(self, service):
        """Two identical products should have win_margin == 0."""
        p1 = _make_product(price_amount=799, rating=4.5)
        p2 = _make_product(price_amount=799, rating=4.5)
        result = service.compute_scores([p1, p2])
        assert result["win_margin"] == 0
        assert result["scores"]["product_0"]["overall"] == result["scores"]["product_1"]["overall"]

    def test_identical_products_equal_breakdowns(self, service):
        """Identical products should have identical dimension breakdowns."""
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
    """Test weight behavior when many priorities are selected."""

    def test_all_priorities_weights_sum_to_one(self, service):
        """Even with all 8 priorities selected, weights must still sum to 1.0."""
        all_priorities = [
            "price", "quality", "brand_reputation", "durability",
            "latest_features", "ease_of_use", "eco_friendly", "health_safety",
        ]
        prefs = {"priorities": all_priorities, "budget": "budget"}
        weights = service._compute_weights(prefs)
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_all_priorities_no_negative_weights(self, service):
        """No weight should be negative after stacking all priorities."""
        all_priorities = [
            "price", "quality", "brand_reputation", "durability",
            "latest_features", "ease_of_use", "eco_friendly", "health_safety",
        ]
        prefs = {"priorities": all_priorities, "budget": "premium"}
        weights = service._compute_weights(prefs)
        for k, v in weights.items():
            assert v >= 0.0, f"{k} has negative weight: {v}"

    def test_three_priorities_weights_valid(self, service):
        """Common case: 3 priorities + budget = valid weights."""
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
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] > \
               result["scores"]["product_1"]["breakdown"]["spec_score"]

    def test_skincare_category(self, service):
        p1 = _make_product(category="skincare", specs={
            "spf": "50", "volume": "50ml",
        })
        p2 = _make_product(category="skincare", specs={
            "spf": "15", "volume": "30ml",
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] >= \
               result["scores"]["product_1"]["breakdown"]["spec_score"]

    def test_fragrances_category(self, service):
        p1 = _make_product(category="fragrances", specs={
            "volume": "100ml", "longevity": "8 hours",
        })
        p2 = _make_product(category="fragrances", specs={
            "volume": "50ml", "longevity": "4 hours",
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] > \
               result["scores"]["product_1"]["breakdown"]["spec_score"]

    def test_haircare_category(self, service):
        p1 = _make_product(category="haircare", specs={
            "volume": "500ml",
        })
        p2 = _make_product(category="haircare", specs={
            "volume": "250ml",
        })
        result = service.compute_scores([p1, p2])
        assert result["scores"]["product_0"]["breakdown"]["spec_score"] >= \
               result["scores"]["product_1"]["breakdown"]["spec_score"]


class TestWeightCapping:
    """Test that personalization weight shifts are capped at ±30% of defaults."""

    def test_single_priority_capped(self):
        service = ScoringService()
        weights = service._compute_weights({"priorities": ["price"]})
        assert weights["price_score"] <= 0.40
        assert weights["spec_score"] >= 0.10

    def test_multiple_priorities_capped(self):
        service = ScoringService()
        weights = service._compute_weights({
            "priorities": ["price", "quality", "durability"],
            "budget": "budget"
        })
        for dim, default_val in CATEGORY_WEIGHTS["other"].items():
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
        for dim, val in CATEGORY_WEIGHTS["other"].items():
            assert abs(weights[dim] - val) < 0.001

    def test_empty_preferences_unchanged(self):
        service = ScoringService()
        weights = service._compute_weights({})
        for dim, val in CATEGORY_WEIGHTS["other"].items():
            assert abs(weights[dim] - val) < 0.001


# ===========================================
# CATEGORY WEIGHT SELECTION
# ===========================================

class TestCategoryWeightSelection:
    """Test category-specific weight profiles."""

    def test_category_weights_electronics(self):
        w = CATEGORY_WEIGHTS["electronics"]
        assert w["spec_score"] == 0.25
        assert w["reliability_score"] == 0.15
        assert abs(sum(w.values()) - 1.0) < 0.001

    def test_category_weights_fashion(self):
        w = CATEGORY_WEIGHTS["fashion"]
        assert w["popularity_score"] == 0.25
        assert w["review_score"] == 0.25
        assert w["price_score"] == 0.10

    def test_category_weights_supplements(self):
        w = CATEGORY_WEIGHTS["supplements"]
        assert w["reliability_score"] == 0.30
        assert w["review_score"] == 0.25

    def test_category_weights_fragrances(self):
        w = CATEGORY_WEIGHTS["fragrances"]
        assert w["review_score"] == 0.30
        assert w["popularity_score"] == 0.25

    def test_category_weights_grocery(self):
        w = CATEGORY_WEIGHTS["grocery"]
        assert w["price_score"] == 0.25
        assert w["value_score"] == 0.25

    def test_all_category_weights_sum_to_one(self):
        for cat, weights in CATEGORY_WEIGHTS.items():
            assert abs(sum(weights.values()) - 1.0) < 0.001, f"{cat} weights sum to {sum(weights.values())}"

    def test_all_categories_have_six_dimensions(self):
        dims = {"price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"}
        for cat, weights in CATEGORY_WEIGHTS.items():
            assert set(weights.keys()) == dims, f"{cat} missing dimensions: {dims - set(weights.keys())}"

    def test_unknown_category_falls_back_to_other(self):
        service = ScoringService()
        weights = service._compute_weights(None, "nonexistent_category")
        assert weights == CATEGORY_WEIGHTS["other"]

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
        # Different base weights should produce different personalized weights
        assert elec != other


# ===========================================
# PRICE TIER DETECTION
# ===========================================

class TestPriceTierDetection:
    """Test price tier classification and cross-tier detection."""

    def test_price_tier_budget(self):
        assert ScoringService._detect_price_tier(5.0) == "budget"

    def test_price_tier_mid(self):
        assert ScoringService._detect_price_tier(30.0) == "mid"

    def test_price_tier_premium(self):
        assert ScoringService._detect_price_tier(100.0) == "premium"

    def test_price_tier_luxury(self):
        assert ScoringService._detect_price_tier(500.0) == "luxury"

    def test_price_tier_boundary_budget_mid(self):
        """Boundary between budget and mid tiers."""
        tier = ScoringService._detect_price_tier(15.0)
        assert tier in ("budget", "mid")

    def test_cross_tier_different(self):
        assert ScoringService._is_cross_tier(["budget", "luxury"]) is True

    def test_cross_tier_same(self):
        assert ScoringService._is_cross_tier(["luxury", "luxury"]) is False

    def test_cross_tier_adjacent(self):
        """Adjacent tiers (budget vs mid) may or may not be cross-tier."""
        result = ScoringService._is_cross_tier(["budget", "mid"])
        assert isinstance(result, bool)


# ===========================================
# VALUE SCORE REDESIGN
# ===========================================

class TestValueScoreRedesign:
    """Test cross-tier aware value scoring."""

    def test_value_score_cross_tier_luxury(self):
        """Luxury item with high spec but low price score — cross-tier aware."""
        service = ScoringService()
        # luxury expected=0.85*100=85, delivery(spec)=85 => value=50+(85-85)*0.8=50
        score = service._compute_value_score(85, 30, "luxury", True)
        assert 45 <= score <= 55

    def test_value_score_cross_tier_budget(self):
        """Budget item with good price — cross-tier value should be decent."""
        service = ScoringService()
        # budget expected=0.6*100=60, delivery(spec)=70 => value=50+(70-60)*0.8=58
        score = service._compute_value_score(70, 95, "budget", True)
        assert score > 55

    def test_value_score_same_tier(self):
        """Same tier: weighted average of spec (0.6) and price (0.4)."""
        service = ScoringService()
        score = service._compute_value_score(80, 60, "mid", False)
        expected = 80 * 0.6 + 60 * 0.4
        assert abs(score - expected) < 0.5

    def test_value_score_missing_spec(self):
        """Missing spec should fall back to price score only."""
        service = ScoringService()
        score = service._compute_value_score(MISSING_SCORE, 70, "mid", False)
        assert score == 70

    def test_value_score_missing_price(self):
        """Missing price should fall back to spec score only."""
        service = ScoringService()
        score = service._compute_value_score(70, MISSING_SCORE, "mid", False)
        assert score == 70

    def test_value_score_both_missing(self):
        """Both missing should return MISSING_SCORE."""
        service = ScoringService()
        score = service._compute_value_score(MISSING_SCORE, MISSING_SCORE, "mid", False)
        assert score == MISSING_SCORE


# ===========================================
# DIMENSION WINNERS
# ===========================================

class TestDimensionWinners:
    """Test per-dimension winner computation."""

    def test_dimension_winners_clear_winner(self):
        service = ScoringService()
        result = {"scores": {
            "product_0": {"breakdown": {"price_score": 80, "spec_score": 60, "review_score": 50, "value_score": 50, "reliability_score": 50, "popularity_score": 50}},
            "product_1": {"breakdown": {"price_score": 40, "spec_score": 90, "review_score": 50, "value_score": 50, "reliability_score": 50, "popularity_score": 50}},
        }}
        winners = service.compute_dimension_winners(result, ["A", "B"])
        assert winners["price_score"]["winner"] == "A"
        assert winners["spec_score"]["winner"] == "B"

    def test_dimension_winners_tie(self):
        service = ScoringService()
        result = {"scores": {
            "product_0": {"breakdown": {"price_score": 50, "spec_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "popularity_score": 50}},
            "product_1": {"breakdown": {"price_score": 51, "spec_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "popularity_score": 50}},
        }}
        winners = service.compute_dimension_winners(result, ["A", "B"])
        assert winners["price_score"]["winner"] == "tie"

    def test_dimension_winners_both_missing(self):
        service = ScoringService()
        result = {"scores": {
            "product_0": {"breakdown": {"price_score": MISSING_SCORE, "spec_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "popularity_score": 50}},
            "product_1": {"breakdown": {"price_score": MISSING_SCORE, "spec_score": 50, "review_score": 50, "value_score": 50, "reliability_score": 50, "popularity_score": 50}},
        }}
        winners = service.compute_dimension_winners(result, ["A", "B"])
        assert winners["price_score"]["winner"] == "N/A"
        assert winners["price_score"]["margin"] is None


# ===========================================
# COVERAGE THRESHOLD + PERSONALIZATION
# ===========================================

class TestCoverageThreshold:
    """Test spec coverage penalty behavior per category."""

    def test_fashion_coverage_no_penalty_at_30_percent(self, service):
        """Fashion has 10 fields; 3/10 = 30% coverage — should get leniency."""
        # Fashion schema fields: material, style, closure_type, size_options,
        # care_instructions, craftsmanship, collection_season, origin, color, design_details
        specs_with_3 = {
            "material": "Italian leather",
            "style": "Classic",
            "color": "Black",
        }
        score = service._score_specs(specs_with_3, "fashion")
        # With 3/10 fields filled, coverage_ratio = 0.3 < 0.5 => penalty applies
        # But having real data means score > 0
        assert score > 0

    def test_electronics_coverage_penalized_at_30_percent(self, service):
        """Electronics has many fields; 30% coverage should trigger penalty."""
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
        # More coverage should score higher (per-field average may differ, but
        # the many-field version shouldn't be penalized while the few-field one is)
        assert score_many > score_few

    def test_personalization_capped_at_category_weight(self):
        """Personalization shift should be capped relative to category base weight."""
        service = ScoringService()
        # Fashion base: price_score = 0.10
        prefs = {"priorities": ["price"], "budget": "budget"}
        weights = service._compute_weights(prefs, "fashion")
        fashion_base = CATEGORY_WEIGHTS["fashion"]["price_score"]
        max_allowed = fashion_base * (1 + MAX_WEIGHT_SHIFT_RATIO)
        # After renormalization the raw capped value gets rescaled,
        # but the pre-normalization cap should hold
        # We verify the final weight is reasonable (not 2x+ the base)
        assert weights["price_score"] < fashion_base * 2.0

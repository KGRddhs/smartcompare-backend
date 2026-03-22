"""Tests for fact-checking logic: spec citation verification, shopping cross-validation,
review sentiment cross-check, price verification, and overall fact_check assembly.

All mocked — these test the verification logic with constructed data.
Run: python -m pytest tests/test_fact_checking.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import StructuredComparisonService
from app.services.extraction_service import _normalize_review_response


@pytest.fixture
def service():
    return StructuredComparisonService()


# =====================================================
# Review summary normalization (_normalize_review_response)
# =====================================================

class TestNormalizeReviewResponseSummary:
    def test_review_summary_defaults_when_missing(self):
        """Missing review_summary gets populated with defaults."""
        data = {"average_rating": 4.0}
        result = _normalize_review_response(data)
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["consensus"] == ""
        assert result["review_summary"]["highlights"] == []
        assert result["review_summary"]["review_volume"] == "minimal"
        assert result["review_summary"]["agreement_level"] == "moderate"

    def test_review_summary_preserves_existing(self):
        """Existing review_summary fields are preserved."""
        data = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "Great product.",
                "highlights": [{"point": "Fast", "sentiment": "positive"}],
                "review_volume": "high",
                "agreement_level": "strong",
            },
        }
        result = _normalize_review_response(data)
        assert result["review_summary"]["overall_sentiment"] == "positive"
        assert result["review_summary"]["consensus"] == "Great product."
        assert len(result["review_summary"]["highlights"]) == 1

    def test_backward_compat_common_praises_from_highlights(self):
        """common_praises populated from positive highlights for backward compat."""
        data = {
            "review_summary": {
                "highlights": [
                    {"point": "Great camera quality", "sentiment": "positive"},
                    {"point": "Poor battery", "sentiment": "negative"},
                ],
            },
        }
        result = _normalize_review_response(data)
        assert len(result["common_praises"]) == 1
        assert "camera" in result["common_praises"][0]
        assert len(result["common_complaints"]) == 1
        assert "battery" in result["common_complaints"][0]

    def test_empty_review_summary(self):
        """Empty review_summary dict gets populated with defaults."""
        data = {"review_summary": {}}
        result = _normalize_review_response(data)
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["highlights"] == []


# =====================================================
# Spec citation verification (_verify_spec_citations)
# =====================================================

class TestVerifySpecCitations:
    def test_verified_citation_matches_snippet(self, service):
        """snippet text contains spec value terms -> 'verified'."""
        specs = {
            "battery": "4422 mAh",
            "battery_source": "snippet_1",
        }
        snippets = ["The iPhone 16 Pro features a 4422 mAh battery capacity."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "verified"

    def test_unverified_when_no_citation(self, service):
        """No _source field -> 'unverified'."""
        specs = {
            "battery": "4422 mAh",
            # no battery_source
        }
        snippets = ["Some snippet text."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_unverified_when_training_source(self, service):
        """Source is 'training' -> 'unverified'."""
        specs = {
            "battery": "4422 mAh",
            "battery_source": "training",
        }
        snippets = ["The battery is 4422 mAh."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_likely_when_partial_match(self, service):
        """Some terms match snippet but not enough for 'verified' -> 'likely'."""
        specs = {
            "processor": "Apple A18 Pro Bionic chip",
            "processor_source": "snippet_1",
        }
        # Snippet has "Apple" and "Pro" but not "A18" or "Bionic" or "chip"
        snippets = ["Apple unveils new Pro lineup with improved performance and efficiency."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["processor"] == "likely"

    def test_unverified_when_snippet_index_out_of_range(self, service):
        """Snippet index beyond list length -> 'unverified'."""
        specs = {
            "storage": "256GB",
            "storage_source": "snippet_10",
        }
        snippets = ["Only one snippet here."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] == "unverified"

    def test_skips_meta_keys(self, service):
        """brand, model, variant, category are skipped."""
        specs = {
            "brand": "Apple",
            "model": "iPhone 16",
            "category": "electronics",
            "battery": "4422 mAh",
            "battery_source": "training",
        }
        snippets = []
        result = service._verify_spec_citations(specs, snippets)
        assert "brand" not in result
        assert "model" not in result
        assert "category" not in result
        assert "battery" in result


# =====================================================
# Spec shopping cross-validation (_cross_validate_specs_with_shopping)
# =====================================================

class TestCrossValidateSpecsWithShopping:
    def test_shopping_confirms_storage_spec(self, service):
        """'128GB' in shopping title confirms storage spec."""
        specs = {"storage": "128GB"}
        shopping_items = [
            {"title": "Samsung Galaxy S24 128GB Phantom Black", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert result.get("storage") == "verified"

    def test_no_shopping_returns_empty(self, service):
        """Empty shopping_items -> empty dict."""
        specs = {"storage": "128GB"}
        result = service._cross_validate_specs_with_shopping(specs, [])
        assert result == {}

    def test_numbers_in_shopping_titles(self, service):
        """Numeric cross-check works for multiple specs."""
        specs = {"storage": "256GB", "ram": "8GB"}
        shopping_items = [
            {"title": "iPhone 16 Pro 256GB 8GB RAM", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert result.get("storage") == "verified"

    def test_na_value_skipped(self, service):
        """Spec value 'N/A' is skipped."""
        specs = {"storage": "N/A"}
        shopping_items = [
            {"title": "Some product 256GB", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert "storage" not in result

    def test_non_checkable_field_ignored(self, service):
        """Fields not in checkable list are not cross-validated."""
        specs = {"color": "Black"}
        shopping_items = [
            {"title": "Product in Black color", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert "color" not in result


# =====================================================
# Review sentiment verification (_verify_review_sentiment)
# =====================================================

class TestVerifyReviewSentiment:
    def test_consistent_when_ratings_close(self, service):
        """GPT 4.5 vs Serper 4.3 -> consistent (within 0.8 tolerance)."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.3, "review_count": 500},
            {"rating": 4.4, "review_count": 300},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is True
        assert result["gpt_rating"] == 4.5
        assert result["serper_avg_rating"] is not None
        assert result["deviation"] is not None
        assert result["deviation"] <= 0.8

    def test_inconsistent_when_ratings_diverge(self, service):
        """GPT 4.8 vs Serper 3.2 -> inconsistent."""
        reviews = {"average_rating": 4.8}
        source_ratings = [
            {"rating": 3.2, "review_count": 1000},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is False
        assert result["deviation"] > 0.8

    def test_none_when_no_source_ratings(self, service):
        """No source_ratings -> sentiment_consistent is None."""
        reviews = {"average_rating": 4.5}
        result = service._verify_review_sentiment(reviews, [])
        assert result["sentiment_consistent"] is None

    def test_none_when_gpt_rating_missing(self, service):
        """No GPT average_rating -> sentiment_consistent is None."""
        reviews = {}
        source_ratings = [{"rating": 4.3, "review_count": 500}]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is None
        assert result["gpt_rating"] is None

    def test_weighted_average_calculation(self, service):
        """Serper average should be weighted by review_count."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": 4.0, "review_count": 900},   # 90% weight
            {"rating": 5.0, "review_count": 100},    # 10% weight
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        # Weighted avg: (4.0*900 + 5.0*100) / 1000 = 4.1
        assert result["serper_avg_rating"] == pytest.approx(4.1, abs=0.01)

    def test_non_numeric_ratings_skipped(self, service):
        """Source ratings with non-numeric rating values are ignored."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": "N/A", "review_count": 500},
            {"rating": 4.0, "review_count": 200},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is True
        assert result["serper_avg_rating"] == 4.0

    def test_none_review_count_defaults_to_one(self, service):
        """review_count of None defaults to weight of 1."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": 4.0, "review_count": None},
            {"rating": 4.2, "review_count": None},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        # Weighted avg: (4.0*1 + 4.2*1) / 2 = 4.1
        assert result["serper_avg_rating"] == pytest.approx(4.1, abs=0.01)
        assert result["sentiment_consistent"] is True

    def test_exact_boundary_0_8_is_consistent(self, service):
        """Deviation of exactly 0.8 is within tolerance -> consistent."""
        reviews = {"average_rating": 4.8}
        source_ratings = [
            {"rating": 4.0, "review_count": 1000},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["deviation"] == 0.8
        assert result["sentiment_consistent"] is True

    def test_single_source_rating(self, service):
        """Single source_rating works correctly."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.3, "review_count": 5000},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["serper_avg_rating"] == 4.3
        assert result["deviation"] == 0.2
        assert result["sentiment_consistent"] is True

    def test_all_ratings_non_numeric_returns_none(self, service):
        """If all source ratings are non-numeric, sentiment_consistent is None."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": "N/A", "review_count": 500},
            {"rating": None, "review_count": 200},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is None
        assert result["serper_avg_rating"] is None

    def test_zero_review_count_defaults_to_one(self, service):
        """review_count of 0 defaults to weight of 1 (0 is falsy)."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.0, "review_count": 0},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["serper_avg_rating"] == 4.0
        assert result["deviation"] == 0.5
        assert result["sentiment_consistent"] is True


# =====================================================
# Price verification (_verify_price)
# =====================================================

class TestVerifyPrice:
    def test_verified_when_within_30pct(self, service):
        """Price within 30% of median -> verified."""
        price = {"amount": 110, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": 95},
            {"price": 105},
            {"price": 100},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True
        assert result["deviation_pct"] is not None
        assert result["deviation_pct"] <= 30
        assert result["source_count"] == 3

    def test_not_verified_when_estimated(self, service):
        """Estimated price -> not verified even if within range."""
        price = {"amount": 100, "currency": "BHD", "estimated": True}
        shopping_items = [
            {"price": 100},
            {"price": 105},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_not_verified_when_deviation_high(self, service):
        """50% deviation -> not verified."""
        price = {"amount": 150, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": 90},
            {"price": 100},
            {"price": 110},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False
        assert result["deviation_pct"] > 30

    def test_no_price_returns_not_verified(self, service):
        """No price dict -> not verified."""
        result = service._verify_price(None, [{"price": 100}])
        assert result["price_verified"] is False

    def test_no_shopping_items(self, service):
        """No shopping items -> verified only if not estimated."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        result = service._verify_price(price, [])
        assert result["price_verified"] is True  # not estimated, just no cross-check data
        assert result["source_count"] == 0

    def test_string_prices_parsed(self, service):
        """Shopping items with string prices (e.g. '$99.99') are parsed."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "$95.00"},
            {"price": "$105.00"},
            {"price": "$100.00"},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["source_count"] == 3
        assert result["price_verified"] is True

    def test_price_amount_zero(self, service):
        """Price amount of 0 -> not verified."""
        price = {"amount": 0, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_price_amount_none(self, service):
        """Price amount of None -> not verified."""
        price = {"amount": None, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_all_invalid_shopping_prices(self, service):
        """All shopping items have invalid prices -> no cross-check."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "N/A"},
            {"price": ""},
            {"price": None},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True  # not estimated, just no valid prices to compare
        assert result["source_count"] == 0
        assert result["deviation_pct"] is None

    def test_comma_separated_string_prices(self, service):
        """String prices with commas like '1,299.99' are parsed correctly."""
        price = {"amount": 1300, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "1,299.99"},
            {"price": "1,350.00"},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["source_count"] == 2
        # Median is 1299.99 (sorted: [1299.99, 1350.0], middle index = 1 -> 1350.0)
        # Actually median of 2 items: sorted[1] = 1350.0 (integer division: 2//2 = 1)
        assert result["deviation_pct"] is not None

    def test_single_shopping_item(self, service):
        """Single shopping item: median = that item."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True
        assert result["deviation_pct"] == 0.0
        assert result["source_count"] == 1

    def test_empty_price_dict(self, service):
        """Empty dict (no amount key) -> not verified."""
        price = {"currency": "BHD"}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_boundary_exactly_30_pct(self, service):
        """Deviation of exactly 30% is within threshold -> verified."""
        price = {"amount": 130, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["deviation_pct"] == 30.0
        assert result["price_verified"] is True

    def test_just_over_30_pct(self, service):
        """Deviation of 31% is above threshold -> not verified."""
        price = {"amount": 131, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["deviation_pct"] == 31.0
        assert result["price_verified"] is False

    def test_negative_prices_excluded(self, service):
        """Negative shopping prices are filtered out."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": -50},
            {"price": 100},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["source_count"] == 1
        assert result["price_verified"] is True


# =====================================================
# Fact-check assembly (_build_fact_check)
# =====================================================

class TestBuildFactCheck:
    def test_high_confidence_all_verified(self, service):
        """All specs verified + price verified -> 'high'."""
        product = {
            "_spec_confidence": {
                "battery": "verified",
                "storage": "verified",
                "ram": "verified",
                "display": "verified",
            },
            "_review_verification": {
                "sentiment_consistent": True,
                "gpt_rating": 4.5,
                "serper_avg_rating": 4.4,
                "deviation": 0.1,
            },
            "_price_verification": {
                "price_verified": True,
                "deviation_pct": 5.0,
                "source_count": 3,
            },
        }
        result = service._build_fact_check(product)
        assert result["overall_confidence"] == "high"
        assert result["specs_verified"] == 4
        assert result["specs_flagged"] == 0
        assert result["price_verified"] is True
        assert result["review_sentiment_consistent"] is True

    def test_low_confidence_when_flagged(self, service):
        """Flagged specs -> 'low'."""
        product = {
            "_spec_confidence": {
                "battery": "flagged",
                "storage": "verified",
            },
            "_review_verification": {
                "sentiment_consistent": True,
                "deviation": 0.1,
            },
            "_price_verification": {
                "price_verified": True,
                "deviation_pct": 5.0,
                "source_count": 3,
            },
        }
        result = service._build_fact_check(product)
        assert result["overall_confidence"] == "low"
        assert result["specs_flagged"] == 1

    def test_low_confidence_when_sentiment_inconsistent(self, service):
        """Inconsistent sentiment -> 'low'."""
        product = {
            "_spec_confidence": {
                "battery": "verified",
                "storage": "verified",
            },
            "_review_verification": {
                "sentiment_consistent": False,
                "deviation": 1.5,
            },
            "_price_verification": {
                "price_verified": True,
                "deviation_pct": 5.0,
                "source_count": 3,
            },
        }
        result = service._build_fact_check(product)
        assert result["overall_confidence"] == "low"

    def test_medium_confidence_mixed(self, service):
        """Mix of verified and unverified -> 'medium'."""
        product = {
            "_spec_confidence": {
                "battery": "verified",
                "storage": "unverified",
                "ram": "likely",
                "display": "unverified",
                "processor": "unverified",
            },
            "_review_verification": {
                "sentiment_consistent": True,
                "deviation": 0.3,
            },
            "_price_verification": {
                "price_verified": False,
                "deviation_pct": 35.0,
                "source_count": 2,
            },
        }
        result = service._build_fact_check(product)
        assert result["overall_confidence"] == "medium"

    def test_internal_keys_popped(self, service):
        """_spec_confidence, _review_verification, _price_verification are removed from product."""
        product = {
            "_spec_confidence": {"battery": "verified"},
            "_review_verification": {"sentiment_consistent": None},
            "_price_verification": {"price_verified": True, "deviation_pct": None, "source_count": 0},
        }
        service._build_fact_check(product)
        assert "_spec_confidence" not in product
        assert "_review_verification" not in product
        assert "_price_verification" not in product

    def test_empty_verifications(self, service):
        """No verification data at all -> medium confidence."""
        product = {}
        result = service._build_fact_check(product)
        assert result["overall_confidence"] == "medium"
        assert result["specs_verified"] == 0
        assert result["specs_flagged"] == 0
        assert result["price_verified"] is False
        assert result["review_sentiment_consistent"] is None

    def test_fact_check_has_all_required_fields(self, service):
        """Fact check dict has all expected keys."""
        product = {
            "_spec_confidence": {"battery": "verified"},
            "_review_verification": {"sentiment_consistent": True, "deviation": 0.2},
            "_price_verification": {"price_verified": True, "deviation_pct": 5.0, "source_count": 3},
        }
        result = service._build_fact_check(product)
        expected_keys = {
            "specs_verified", "specs_likely", "specs_flagged", "specs_unverified",
            "price_verified", "price_deviation_pct",
            "review_sentiment_consistent", "review_rating_deviation",
            "overall_confidence",
        }
        assert set(result.keys()) == expected_keys

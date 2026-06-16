"""Tests for newly decomposed service modules extracted from the monolith.

Tests the PUBLIC functions/classes used by structured_comparison_service.py:
- response_builder.py: build_comparison_response(), derive_rating_from_scores()
- fact_check_service.py: verify_spec_citations(), cross_validate_specs_with_shopping(),
  verify_review_sentiment(), verify_price(), build_fact_check()
- review_service.py: clean_review_content(), clean_review_citations(), format_review_search_results()
- rating_service.py: get_rating_tier(), collect_retailer_ratings(), extract_rating_from_shopping()

All tests are mocked — no live API calls.
Run: python -m pytest tests/test_decomposed_services.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Import the new decomposed modules
from app.services.response_builder import build_comparison_response, derive_rating_from_scores
from app.services.fact_check_service import (
    verify_spec_citations,
    cross_validate_specs_with_shopping,
    verify_review_sentiment,
    verify_price,
    build_fact_check,
    NUMERIC_SPEC_FIELDS,
)
from app.services.review_service import (
    clean_review_content,
    clean_review_citations,
    format_review_search_results,
    GARBAGE_PATTERNS,
)
from app.services.rating_service import (
    get_rating_tier,
    collect_retailer_ratings,
    extract_rating_from_shopping,
    RATING_TIER_1,
    RATING_TIER_2,
    RATING_TIER_3,
)


# =====================================================
# response_builder.py tests
# =====================================================

class TestDeriveRatingFromScores:
    """Test synthetic rating derivation from overall scores."""

    def test_high_score_rating(self):
        """Score 90 should yield ~4.6 rating."""
        rating = derive_rating_from_scores(90)
        assert 4.5 <= rating <= 4.8
        assert isinstance(rating, float)

    def test_mid_score_rating(self):
        """Score 50 should yield ~3.6 rating."""
        rating = derive_rating_from_scores(50)
        assert 3.4 <= rating <= 3.8

    def test_low_score_rating(self):
        """Score 10 should yield ~2.7 rating."""
        rating = derive_rating_from_scores(10)
        assert 2.5 <= rating <= 2.9

    def test_max_cap_at_48(self):
        """Even score 100 shouldn't exceed 4.8."""
        rating = derive_rating_from_scores(100)
        assert rating <= 4.8

    def test_zero_score(self):
        """Score 0 yields 2.5."""
        rating = derive_rating_from_scores(0)
        assert rating == 2.5


class TestBuildComparisonResponse:
    """Test response assembly from product data, comparison, scoring."""

    def test_minimal_response_structure(self):
        """Test with minimal inputs — should not crash."""
        product_data = [
            {"brand": "Apple", "name": "iPhone 15", "rating": 4.5},
            {"brand": "Samsung", "name": "Galaxy S24", "rating": 4.3},
        ]
        comparison = {
            "winner_index": 0,
            "winner_declaration": "iPhone 15",
            "winner_reason": "Better camera",
            "key_tradeoff": "Price vs features",
        }
        scoring_result = {
            "scores": {
                "product_0": {"overall": 85, "breakdown": {"value_score": 70}},
                "product_1": {"overall": 75, "breakdown": {"value_score": 65}},
            },
            "dimension_winners": {},
            "winner_index": 0,
            "win_margin": 10,
        }
        product_names = ["Apple iPhone 15", "Samsung Galaxy S24"]
        tradeoffs = []
        confidence = {"overall_confidence": "high"}
        verdict_validation = {"winner_aligned": True, "claims_flagged": []}

        result = build_comparison_response(
            product_data=product_data,
            comparison=comparison,
            scoring_result=scoring_result,
            product_names=product_names,
            tradeoffs=tradeoffs,
            confidence=confidence,
            verdict_validation=verdict_validation,
            user_preferences=None,
            from_cache=False,
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
            category_used="electronics",
            category_switched=False,
            original_category=None,
            total_cost=0.005,
            api_calls=3,
            gpt_calls=2,
            serper_calls=1,
            elapsed_seconds=1.23,
        )

        # Check top-level keys
        assert result["success"] is True
        assert "overview" in result
        assert "specs" in result
        assert "reviews" in result
        assert "scoring" in result
        assert "metadata" in result
        assert "personalization" in result

    def test_backward_compat_aliases(self):
        """Test that legacy alias fields are present."""
        product_data = [
            {"brand": "Apple", "name": "iPhone 15"},
            {"brand": "Samsung", "name": "Galaxy S24"},
        ]
        comparison = {"winner_index": 0, "winner_reason": "Better value"}
        scoring_result = {
            "scores": {},
            "winner_index": 0,
            "win_margin": 5,
        }

        result = build_comparison_response(
            product_data=product_data,
            comparison=comparison,
            scoring_result=scoring_result,
            product_names=["iPhone 15", "Galaxy S24"],
            tradeoffs=[],
            confidence={},
            verdict_validation={},
            user_preferences=None,
            from_cache=True,
            query="test",
            region="bahrain",
            category_used="electronics",
            category_switched=False,
            original_category=None,
            total_cost=0,
            api_calls=0,
            gpt_calls=0,
            serper_calls=0,
            elapsed_seconds=0,
        )

        # Backward compat aliases
        assert "products" in result
        assert result["products"] == product_data
        assert "comparison" in result
        assert result["comparison"] == comparison
        assert "winner_index" in result
        assert result["winner_index"] == 0
        assert "recommendation" in result
        assert "key_differences" in result
        assert isinstance(result["key_differences"], list)

    def test_price_method_mismatch_detection(self):
        """Test that different price source methods are detected.

        Updated for Task C1 (price-pending): a price counts toward the method
        set only when SHOWABLE (positive amount + a showable source_method).
        `estimated` is now suppressed to a price-pending shape (no source_method),
        so this asserts the mismatch on two SHOWABLE-but-different methods —
        firecrawl (genuine-BH) vs converted_usd — the real apples-to-oranges case.
        """
        product_data = [
            {"brand": "LV", "name": "Bag", "price": {"source_method": "firecrawl", "amount": 250.0, "currency": "BHD"}},
            {"brand": "Gucci", "name": "Wallet", "price": {"source_method": "converted_usd", "amount": 300.0, "currency": "BHD"}},
        ]
        comparison = {"winner_index": 0}
        scoring_result = {"scores": {}, "winner_index": 0}

        result = build_comparison_response(
            product_data=product_data,
            comparison=comparison,
            scoring_result=scoring_result,
            product_names=["LV Bag", "Gucci Wallet"],
            tradeoffs=[],
            confidence={},
            verdict_validation={},
            user_preferences=None,
            from_cache=False,
            query="test",
            region="bahrain",
            category_used="fashion",
            category_switched=False,
            original_category=None,
            total_cost=0,
            api_calls=0,
            gpt_calls=0,
            serper_calls=0,
            elapsed_seconds=0,
        )

        assert result["price_method_mismatch"] is True

    def test_no_price_method_mismatch(self):
        """Test when both products have same source method."""
        product_data = [
            {"brand": "Apple", "name": "iPhone", "price": {"source_method": "local_bhd"}},
            {"brand": "Samsung", "name": "Galaxy", "price": {"source_method": "local_bhd"}},
        ]
        comparison = {"winner_index": 0}
        scoring_result = {"scores": {}, "winner_index": 0}

        result = build_comparison_response(
            product_data=product_data,
            comparison=comparison,
            scoring_result=scoring_result,
            product_names=["iPhone", "Galaxy"],
            tradeoffs=[],
            confidence={},
            verdict_validation={},
            user_preferences=None,
            from_cache=False,
            query="test",
            region="bahrain",
            category_used="electronics",
            category_switched=False,
            original_category=None,
            total_cost=0,
            api_calls=0,
            gpt_calls=0,
            serper_calls=0,
            elapsed_seconds=0,
        )

        assert result["price_method_mismatch"] is False

    def test_derived_rating_when_missing(self):
        """Test that None ratings get derived from scores."""
        product_data = [
            {"brand": "Apple", "name": "iPhone", "rating": None},
            {"brand": "Samsung", "name": "Galaxy", "rating": 4.5},
        ]
        comparison = {"winner_index": 0}
        scoring_result = {
            "scores": {
                "product_0": {"overall": 80},
                "product_1": {"overall": 70},
            },
            "winner_index": 0,
        }

        result = build_comparison_response(
            product_data=product_data,
            comparison=comparison,
            scoring_result=scoring_result,
            product_names=["iPhone", "Galaxy"],
            tradeoffs=[],
            confidence={},
            verdict_validation={},
            user_preferences=None,
            from_cache=False,
            query="test",
            region="bahrain",
            category_used="electronics",
            category_switched=False,
            original_category=None,
            total_cost=0,
            api_calls=0,
            gpt_calls=0,
            serper_calls=0,
            elapsed_seconds=0,
        )

        # Product 0 should have derived rating
        assert product_data[0]["rating"] is not None
        assert product_data[0]["rating_derived"] is True
        # Product 1 should keep original
        assert product_data[1]["rating"] == 4.5
        assert "rating_derived" not in product_data[1] or not product_data[1].get("rating_derived")


class TestPerProductValueContext:
    """Bug fix: overview.products[i].value_context must NOT be identical across products.

    Root cause: response_builder.py:126 read a single comparison-level
    `value_context` string and fanned it out to every product slot. With the
    prompt-side fix, `comparison['value_context']` is a dict keyed by
    product_0/product_1 (mirroring `best_for`), so each product gets a
    distinct value-context line.

    Backward-compat: a legacy string `value_context` still resolves (used for
    both products) — that preserves existing test fixtures without making the
    new behaviour silently regress.
    """

    def _kwargs(self, comparison: dict) -> dict:
        return dict(
            product_data=[
                {"brand": "Apple", "name": "iPhone 15"},
                {"brand": "Samsung", "name": "Galaxy S24"},
            ],
            comparison=comparison,
            scoring_result={
                "scores": {
                    "product_0": {"overall": 85, "breakdown": {"value_score": 70}},
                    "product_1": {"overall": 75, "breakdown": {"value_score": 65}},
                },
                "winner_index": 0,
                "win_margin": 10,
            },
            product_names=["Apple iPhone 15", "Samsung Galaxy S24"],
            tradeoffs=[],
            confidence={},
            verdict_validation={},
            user_preferences=None,
            from_cache=False,
            query="iPhone 15 vs Galaxy S24",
            region="bahrain",
            category_used="electronics",
            category_switched=False,
            original_category=None,
            total_cost=0,
            api_calls=0,
            gpt_calls=0,
            serper_calls=0,
            elapsed_seconds=0,
        )

    def test_dict_shape_yields_distinct_per_product_value_context(self):
        """When `comparison['value_context']` is a per-product dict, each
        product gets its own string in overview.products[i].value_context."""
        comparison = {
            "winner_index": 0,
            "value_context": {
                "product_0": "Flagship specs at 12% below category average for the GCC market.",
                "product_1": "Mid-range pricing with premium build quality; strong value in Bahrain retailers.",
            },
        }
        result = build_comparison_response(**self._kwargs(comparison))
        products = result["overview"]["products"]
        assert len(products) == 2
        vc0 = products[0]["value_context"]
        vc1 = products[1]["value_context"]
        assert vc0 == comparison["value_context"]["product_0"], vc0
        assert vc1 == comparison["value_context"]["product_1"], vc1
        # Core invariant: the two products must NOT receive identical strings.
        assert vc0 != vc1, (
            f"value_context is identical across products: {vc0!r}. "
            "Bug: response_builder fanned a single comparison-level string "
            "into every product slot."
        )

    def test_legacy_string_shape_falls_back_to_same_string(self):
        """Backward-compat: when the comparison still emits the old
        comparison-level string (pre-prompt-update), the builder must not
        crash — both products fall back to the same string. New consumers
        will see the dict shape and get distinct strings."""
        comparison = {
            "winner_index": 0,
            "value_context": "Both products are mid-range flagships with competitive pricing.",
        }
        result = build_comparison_response(**self._kwargs(comparison))
        products = result["overview"]["products"]
        assert products[0]["value_context"] == comparison["value_context"]
        assert products[1]["value_context"] == comparison["value_context"]


# =====================================================
# fact_check_service.py tests
# =====================================================

class TestVerifySpecCitations:
    """Test spec citation verification against search snippets."""

    def test_verified_numeric_field_matches(self):
        """Numeric field with matching snippet -> verified."""
        specs = {
            "battery": "4422 mAh",
            "battery_source": "snippet_1",
        }
        snippets = ["The iPhone 16 Pro features a 4422 mAh battery capacity."]
        result = verify_spec_citations(specs, snippets)
        assert result["battery"] == "verified"

    def test_unverified_when_no_citation(self):
        """No _source field -> unverified."""
        specs = {"battery": "4422 mAh"}
        snippets = ["Some snippet text."]
        result = verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_training_source_unverified(self):
        """source='training' -> unverified."""
        specs = {
            "ram": "8GB",
            "ram_source": "training",
        }
        snippets = ["Has 8GB of RAM"]
        result = verify_spec_citations(specs, snippets)
        assert result["ram"] == "unverified"

    def test_likely_when_partial_match(self):
        """Partial match on terms -> likely."""
        specs = {
            "processor": "A17 Bionic chip",
            "processor_source": "snippet_1",
        }
        snippets = ["The phone has a Bionic processor"]
        result = verify_spec_citations(specs, snippets)
        # Only "bionic" matches, not "a17", so likely
        assert result["processor"] in ["likely", "verified"]

    def test_skips_meta_keys(self):
        """Meta keys (brand, model, _cached, etc.) are skipped."""
        specs = {
            "brand": "Apple",
            "model": "iPhone 15",
            "_cached": True,
            "battery": "4000 mAh",
            "battery_source": "snippet_1",
        }
        snippets = ["Battery is 4000 mAh"]
        result = verify_spec_citations(specs, snippets)
        assert "brand" not in result
        assert "model" not in result
        assert "_cached" not in result
        assert "battery" in result


class TestCrossValidateSpecsWithShopping:
    """Test shopping data cross-validation."""

    def test_verified_when_shopping_confirms(self):
        """Shopping titles confirm spec values -> verified."""
        specs = {"storage": "256GB", "ram": "8GB"}
        shopping_items = [
            {"title": "iPhone 15 Pro 256GB 8GB RAM Natural Titanium"},
            {"title": "iPhone 15 Pro with 256GB storage and 8GB memory"},
        ]
        result = cross_validate_specs_with_shopping(specs, shopping_items)
        assert result.get("storage") == "verified"
        assert result.get("ram") == "verified"

    def test_empty_when_no_shopping(self):
        """No shopping items -> empty dict."""
        specs = {"storage": "256GB"}
        result = cross_validate_specs_with_shopping(specs, [])
        assert result == {}

    def test_no_flag_when_value_missing(self):
        """Spec value N/A or missing -> no flag."""
        specs = {"storage": "N/A", "ram": None}
        shopping_items = [{"title": "iPhone 15 Pro"}]
        result = cross_validate_specs_with_shopping(specs, shopping_items)
        assert "storage" not in result
        assert "ram" not in result


class TestVerifyReviewSentiment:
    """Test review sentiment cross-check against Serper ratings."""

    def test_consistent_sentiment(self):
        """GPT rating 4.5 vs Serper avg 4.3 -> consistent."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.3, "review_count": 100},
            {"rating": 4.5, "review_count": 50},
        ]
        result = verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is True
        assert abs(result["deviation"]) <= 0.8

    def test_inconsistent_sentiment(self):
        """GPT rating 4.8 vs Serper avg 3.2 -> inconsistent."""
        reviews = {"average_rating": 4.8}
        source_ratings = [
            {"rating": 3.2, "review_count": 200},
        ]
        result = verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is False
        assert result["deviation"] > 0.8

    def test_no_sentiment_check_when_missing(self):
        """No GPT rating or no source ratings -> None."""
        reviews = {}
        result = verify_review_sentiment(reviews, [])
        assert result["sentiment_consistent"] is None


class TestVerifyPrice:
    """Test price verification against shopping median."""

    def test_verified_when_within_30pct(self):
        """Final price within 30% of shopping median -> verified."""
        price = {"amount": 100, "currency": "BHD"}
        shopping_items = [
            {"price": "95 BHD"},
            {"price": 105},
            {"price": "100"},
        ]
        result = verify_price(price, shopping_items)
        assert result["price_verified"] is True
        assert result["deviation_pct"] <= 30

    def test_unverified_when_beyond_30pct(self):
        """Final price 50% above median -> not verified."""
        price = {"amount": 150, "currency": "BHD"}
        shopping_items = [
            {"price": 100},
            {"price": 95},
        ]
        result = verify_price(price, shopping_items)
        assert result["price_verified"] is False
        assert result["deviation_pct"] > 30

    def test_estimated_price_not_verified(self):
        """Estimated price is never verified."""
        price = {"amount": 100, "estimated": True}
        shopping_items = [{"price": 100}]
        result = verify_price(price, shopping_items)
        assert result["price_verified"] is False


class TestBuildFactCheck:
    """Test fact_check object assembly."""

    def test_high_confidence(self):
        """Specs verified, price verified, sentiment OK -> high."""
        product = {
            "_spec_confidence": {
                "storage": "verified",
                "ram": "verified",
                "battery": "likely",
            },
            "_review_verification": {"sentiment_consistent": True},
            "_price_verification": {"price_verified": True, "deviation_pct": 5},
        }
        fact_check = build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in fact_check
        assert fact_check["specs_verified"] == 2
        assert fact_check["specs_likely"] == 1
        assert fact_check["price_verified"] is True

    def test_medium_confidence(self):
        """Some specs unverified -> medium."""
        product = {
            "_spec_confidence": {
                "storage": "verified",
                "ram": "unverified",
                "battery": "unverified",
            },
            "_review_verification": {"sentiment_consistent": None},
            "_price_verification": {"price_verified": True},
        }
        fact_check = build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in fact_check
        assert fact_check["specs_unverified"] == 2

    def test_low_confidence_when_flagged(self):
        """Any flagged specs -> low."""
        product = {
            "_spec_confidence": {
                "storage": "verified",
                "ram": "flagged",
            },
            "_review_verification": {"sentiment_consistent": True},
            "_price_verification": {"price_verified": True},
        }
        fact_check = build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in fact_check
        assert fact_check["specs_flagged"] == 1

    def test_pops_internal_keys(self):
        """Internal _spec_confidence, _review_verification, _price_verification should be removed."""
        product = {
            "brand": "Apple",
            "_spec_confidence": {"ram": "verified"},
            "_review_verification": {},
            "_price_verification": {},
        }
        build_fact_check(product)
        assert "_spec_confidence" not in product
        assert "_review_verification" not in product
        assert "_price_verification" not in product
        assert "brand" in product  # Normal keys preserved


# =====================================================
# review_service.py tests
# =====================================================

class TestCleanReviewContent:
    """Test garbage filtering and sentiment alignment."""

    def test_removes_learn_more_garbage(self):
        """Garbage patterns filtered out."""
        reviews = {
            "common_praises": ["Learn more about the product conditions and details"],
        }
        cleaned = clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 0

    def test_removes_short_items(self):
        """Items with < 8 words removed."""
        reviews = {
            "common_praises": [
                "Great product",
                "Love it so much",
                "This is actually quite good for the price I paid",
            ],
        }
        cleaned = clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 1  # Only the 10-word one

    def test_removes_positive_from_complaints(self):
        """Positive indicators in complaints section -> removed."""
        reviews = {
            "common_complaints": [
                "The quality is excellent and the craftsmanship is absolutely amazing and beautiful"
            ],
        }
        cleaned = clean_review_content(reviews)
        assert len(cleaned["common_complaints"]) == 0

    def test_keeps_negative_complaints(self):
        """Actual negative complaints kept."""
        reviews = {
            "common_complaints": [
                "The stitching came loose after two months of regular daily use which is disappointing"
            ],
        }
        cleaned = clean_review_content(reviews)
        assert len(cleaned["common_complaints"]) == 1

    def test_cleans_review_summary_highlights(self):
        """Also cleans review_summary.highlights[].point format."""
        reviews = {
            "review_summary": {
                "highlights": [
                    {"point": "Learn more about this product here", "sentiment": "positive"},
                    {"point": "The battery life is excellent and lasts all day long", "sentiment": "positive"},
                    {"point": "Good", "sentiment": "positive"},  # Too short
                ],
            },
        }
        cleaned = clean_review_content(reviews)
        # Only the middle one should remain
        assert len(cleaned["review_summary"]["highlights"]) == 1
        assert "battery" in cleaned["review_summary"]["highlights"][0]["point"]


class TestCleanReviewCitations:
    """Test [snippet_N] replacement with domain names."""

    def test_replaces_snippet_citations(self):
        """[snippet_1] -> 'Per domain.com: '."""
        reviews = {
            "common_praises": ["[snippet_1] Great camera quality"],
        }
        search_results = [
            {"link": "https://www.cnet.com/reviews/iphone-15"},
        ]
        cleaned = clean_review_citations(reviews, search_results)
        assert "Per cnet.com:" in cleaned["common_praises"][0]
        assert "[snippet_1]" not in cleaned["common_praises"][0]

    def test_replaces_in_highlights(self):
        """Current format: review_summary.highlights[].point."""
        reviews = {
            "review_summary": {
                "highlights": [
                    {"point": "[snippet_2] Battery drains fast", "sentiment": "negative"},
                ],
            },
        }
        search_results = [
            {"link": "https://example.com/page1"},
            {"link": "https://techradar.com/reviews/phone"},
        ]
        cleaned = clean_review_citations(reviews, search_results)
        assert "Per techradar.com:" in cleaned["review_summary"]["highlights"][0]["point"]

    def test_removes_citation_when_no_domain(self):
        """No matching domain -> citation removed."""
        reviews = {
            "common_praises": ["[snippet_5] Good value"],
        }
        search_results = [
            {"link": "https://example.com/1"},
        ]
        cleaned = clean_review_citations(reviews, search_results)
        # snippet_5 doesn't exist (only snippet_1), so removed
        assert "[snippet_5]" not in cleaned["common_praises"][0]


class TestFormatReviewSearchResults:
    """Test search result formatting for review extraction."""

    def test_formats_organic_results(self):
        """Organic results formatted with domain prefix."""
        results = {
            "organic": [
                {"title": "iPhone Review", "snippet": "Great phone", "link": "https://cnet.com/review"},
            ],
        }
        formatted = format_review_search_results(results, [])
        assert "cnet.com" in formatted
        assert "iPhone Review" in formatted
        assert "Great phone" in formatted

    def test_formats_retailer_ratings(self):
        """Retailer ratings appended."""
        results = {"organic": []}
        retailer_ratings = [
            {"source": "Amazon", "rating": 4.5, "review_count": 1200},
        ]
        formatted = format_review_search_results(results, retailer_ratings)
        assert "Amazon" in formatted
        assert "4.5/5" in formatted
        assert "1200 reviews" in formatted

    def test_empty_results(self):
        """No results -> fallback message."""
        formatted = format_review_search_results(None, [])
        assert "No search results available" in formatted


# =====================================================
# rating_service.py tests
# =====================================================

class TestGetRatingTier:
    """Test retailer classification into tiers."""

    def test_tier_1_retailers(self):
        """Trusted retailers -> tier 1."""
        assert get_rating_tier("Amazon") == 1
        assert get_rating_tier("apple.com") == 1
        assert get_rating_tier("Best Buy") == 1
        assert get_rating_tier("iHerb") == 1

    def test_tier_2_retailers(self):
        """Known retailers -> tier 2."""
        assert get_rating_tier("Carrefour") == 2
        assert get_rating_tier("Boots") == 2
        assert get_rating_tier("Fnac") == 2

    def test_tier_3_marketplaces(self):
        """Marketplaces -> tier 3."""
        assert get_rating_tier("eBay") == 3
        assert get_rating_tier("AliExpress") == 3

    def test_generic_domains_tier_2(self):
        """Generic .com/.ae domains -> tier 2."""
        assert get_rating_tier("example.com") == 2
        assert get_rating_tier("shop.ae") == 2

    def test_unknown_source_tier_3(self):
        """Unknown sources -> tier 3."""
        assert get_rating_tier("") == 3
        assert get_rating_tier(None) == 3


class TestCollectRetailerRatings:
    """Test rating extraction from shopping cache."""

    def test_collects_ratings(self):
        """Extract ratings from shopping items."""
        shopping_cache = {
            "iPhone 15": [
                {"source": "Amazon", "rating": 4.5, "ratingCount": 1200},
                {"source": "Best Buy", "rating": 4.3, "reviewCount": 800},
            ],
        }
        ratings = collect_retailer_ratings("iPhone 15", shopping_cache)
        assert len(ratings) == 2
        assert ratings[0]["source"] == "Amazon"
        assert ratings[0]["rating"] == 4.5
        assert ratings[0]["review_count"] == 1200

    def test_skips_duplicates(self):
        """Same source appears once only."""
        shopping_cache = {
            "Product": [
                {"source": "Amazon", "rating": 4.5},
                {"source": "amazon", "rating": 4.6},  # Duplicate (case-insensitive)
            ],
        }
        ratings = collect_retailer_ratings("Product", shopping_cache)
        assert len(ratings) == 1

    def test_empty_when_no_cache(self):
        """No shopping data -> empty list."""
        ratings = collect_retailer_ratings("Unknown Product", {})
        assert ratings == []


class TestExtractRatingFromShopping:
    """Test rating extraction with tiered fallback."""

    def test_tier1_preferred(self):
        """Tier 1 source chosen over Tier 2/3."""
        shopping_items = [
            {"title": "iPhone 15 Pro", "source": "eBay", "rating": 4.8, "ratingCount": 5000, "link": "https://ebay.com/1"},
            {"title": "iPhone 15 Pro", "source": "Amazon", "rating": 4.5, "ratingCount": 1000, "link": "https://amazon.com/1"},
        ]
        result = extract_rating_from_shopping("iPhone 15 Pro", shopping_items)
        assert result["rating"] == 4.5
        assert result["rating_source"]["name"] == "Amazon via Google Shopping"
        assert result["rating_verified"] is True

    def test_tier3_with_high_reviews(self):
        """Tier 3 (eBay) accepted only if review_count > 1000."""
        shopping_items = [
            {"title": "Product", "source": "eBay", "rating": 4.5, "ratingCount": 500},
        ]
        result = extract_rating_from_shopping("Product", shopping_items)
        assert result["rating"] is None  # Rejected (< 1000 reviews)

    def test_google_consensus(self):
        """3+ identical ratings from Tier 3 sellers -> Google product aggregate."""
        # Use tier 3 sources (no .com, not in tier 1/2) so consensus logic triggers
        shopping_items = [
            {"title": "Product", "source": "Seller1", "rating": 4.5, "ratingCount": 1500, "link": "https://s1.shop"},
            {"title": "Product", "source": "Seller2", "rating": 4.5, "ratingCount": 1500, "link": "https://s2.shop"},
            {"title": "Product", "source": "Seller3", "rating": 4.5, "ratingCount": 1500, "link": "https://s3.shop"},
        ]
        result = extract_rating_from_shopping("Product", shopping_items)
        assert result["rating"] == 4.5
        assert "product aggregate" in result["rating_source"]["name"]
        assert result["rating_verified"] is True

    def test_skips_accessories(self):
        """Accessory listings skipped."""
        shopping_items = [
            {"title": "iPhone 15 Case", "source": "Amazon", "rating": 4.5, "ratingCount": 1000},
        ]
        result = extract_rating_from_shopping("iPhone 15", shopping_items)
        assert result["rating"] is None

    def test_empty_when_no_items(self):
        """No shopping items -> empty result."""
        result = extract_rating_from_shopping("Product", [])
        assert result["rating"] is None
        assert result["rating_verified"] is False


# =====================================================
# Integration: full flow mock test
# =====================================================

class TestDecomposedServicesIntegration:
    """Test that modules work together as expected."""

    def test_full_fact_check_flow(self):
        """Test full fact-checking flow: verify specs -> reviews -> price -> build."""
        # Specs with citations
        specs = {
            "storage": "256GB",
            "storage_source": "snippet_1",
            "ram": "8GB",
            "ram_source": "snippet_2",
        }
        snippets = [
            "This phone has 256GB storage",
            "Comes with 8GB of RAM",
        ]
        spec_confidence = verify_spec_citations(specs, snippets)
        assert spec_confidence["storage"] == "verified"
        assert spec_confidence["ram"] == "verified"

        # Cross-validate with shopping
        shopping_items = [
            {"title": "iPhone 15 Pro 256GB 8GB RAM", "price": 950},
        ]
        shopping_flags = cross_validate_specs_with_shopping(specs, shopping_items)
        assert shopping_flags.get("storage") == "verified"

        # Review sentiment
        reviews = {"average_rating": 4.5}
        source_ratings = [{"rating": 4.3, "review_count": 1000}]
        review_check = verify_review_sentiment(reviews, source_ratings)
        assert review_check["sentiment_consistent"] is True

        # Price verification
        price = {"amount": 950, "currency": "BHD"}
        price_check = verify_price(price, shopping_items)
        assert price_check["price_verified"] is True

        # Build fact_check
        product = {
            "_spec_confidence": spec_confidence,
            "_review_verification": review_check,
            "_price_verification": price_check,
        }
        fact_check = build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in fact_check
        assert fact_check["price_verified"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

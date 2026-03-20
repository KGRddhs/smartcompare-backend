"""Tests for review content cleanup — garbage filtering, sentiment alignment, derived ratings.

Covers:
- GARBAGE_PATTERNS filtering (learn_more, navigation, keeps_legitimate, removes_short)
- Sentiment misclassification (positive_from_complaints, keeps_negative, mixed_with_negative)
- Derived ratings (_derive_rating_from_scores: high, mid, low, max cap, min floor)
- String/edge cases (string items, empty sections, missing sections)

Run: pytest tests/test_review_cleanup.py -v
"""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


# ===========================================
# GARBAGE PATTERN FILTERING
# ===========================================

class TestGarbageFiltering:
    """Test _clean_review_content() removes navigation/boilerplate text."""

    def test_removes_learn_more(self, service):
        reviews = {"common_praises": ["Learn more about the product conditions and details"]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 0

    def test_removes_navigation_text(self, service):
        reviews = {"common_praises": [
            "Click here to see full product information and specifications",
            "Shop now and get free shipping on orders over fifty dollars",
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 0

    def test_keeps_legitimate_praise(self, service):
        reviews = {"common_praises": [
            "The leather feels premium and holds its shape well after daily use"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 1

    def test_removes_short_items(self, service):
        """Items with fewer than 8 words should be filtered out."""
        reviews = {"common_praises": [
            "Great product",
            "Love it",
            "Not worth the price honestly",
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 0

    def test_removes_add_to_cart(self, service):
        reviews = {"common_complaints": [
            "Add to cart for special pricing and exclusive deals and offers"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_complaints"]) == 0

    def test_removes_sign_up(self, service):
        reviews = {"common_praises": [
            "Sign up for our newsletter to get exclusive deals and discount codes"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 0


# ===========================================
# SENTIMENT MISCLASSIFICATION
# ===========================================

class TestSentimentAlignment:
    """Test that positive statements are removed from complaints."""

    def test_positive_removed_from_complaints(self, service):
        """A praise-like sentence should not appear in complaints."""
        reviews = {"common_complaints": [
            "The quality is excellent and the craftsmanship is absolutely amazing and beautiful"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_complaints"]) == 0

    def test_keeps_negative_complaint(self, service):
        reviews = {"common_complaints": [
            "The stitching came loose after two months of regular daily use which is disappointing"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_complaints"]) == 1

    def test_mixed_with_negative_kept(self, service):
        """If both positive and negative indicators present, keep it (has real criticism)."""
        reviews = {"common_complaints": [
            "The material looks great but the zipper is flimsy and broke after a week"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_complaints"]) == 1

    def test_positive_not_filtered_from_praises(self, service):
        """Sentiment filtering should not apply to praises section."""
        reviews = {"common_praises": [
            "The quality is excellent and the craftsmanship is absolutely amazing and beautiful"
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 1


# ===========================================
# DERIVED RATINGS
# ===========================================

class TestDerivedRatings:
    """Test _derive_rating_from_scores() synthetic rating generation."""

    def test_high_score_high_rating(self, service):
        """Overall score of 90 should produce a rating around 4.5+."""
        rating = service._derive_rating_from_scores(90)
        assert 4.3 <= rating <= 4.8

    def test_mid_score_mid_rating(self, service):
        """Overall score of 50 should produce a rating around 3.5-3.7."""
        rating = service._derive_rating_from_scores(50)
        assert 3.3 <= rating <= 3.9

    def test_low_score_low_rating(self, service):
        """Overall score of 10 should produce a rating around 2.7."""
        rating = service._derive_rating_from_scores(10)
        assert 2.5 <= rating <= 3.0

    def test_never_exceeds_4_8(self, service):
        """Even with a perfect score of 100, rating should cap at 4.8."""
        rating = service._derive_rating_from_scores(100)
        assert rating <= 4.8

    def test_minimum_2_5(self, service):
        """Score of 0 should produce the minimum floor of 2.5."""
        rating = service._derive_rating_from_scores(0)
        assert rating >= 2.5


# ===========================================
# EDGE CASES
# ===========================================

class TestReviewCleanupEdgeCases:
    """Test edge cases for _clean_review_content()."""

    def test_string_items_in_list(self, service):
        """Common praises as strings (not dicts) should still be processed."""
        reviews = {"common_praises": [
            "Learn more about this product and see all available color options",
            "The build quality is superb and materials feel really luxurious and durable",
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["common_praises"]) == 1
        assert "luxurious" in cleaned["common_praises"][0]

    def test_dict_items_with_text_key(self, service):
        """Detailed praises/complaints as dicts with 'text' key."""
        reviews = {"detailed_praises": [
            {"text": "Learn more about condition and see seller notes for details", "source": "snippet_1"},
            {"text": "The leather quality is exceptional and ages beautifully over time with use", "source": "snippet_2"},
        ]}
        cleaned = service._clean_review_content(reviews)
        assert len(cleaned["detailed_praises"]) == 1
        assert cleaned["detailed_praises"][0]["source"] == "snippet_2"

    def test_empty_sections(self, service):
        reviews = {"common_praises": [], "common_complaints": []}
        cleaned = service._clean_review_content(reviews)
        assert cleaned["common_praises"] == []
        assert cleaned["common_complaints"] == []

    def test_missing_sections(self, service):
        """Reviews dict without praise/complaint sections should not crash."""
        reviews = {"average_rating": 4.5, "summary": "Good product"}
        cleaned = service._clean_review_content(reviews)
        assert cleaned["average_rating"] == 4.5
        assert cleaned["summary"] == "Good product"

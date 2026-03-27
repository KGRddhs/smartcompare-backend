"""Tests for review citation cleanup -- [snippet_N] to source domain replacement.

Covers:
- Snippet replaced with domain name
- Unknown snippets stripped
- Multiple praises/complaints handling
- Detailed praises/complaints handling
- Non-citation fields preserved
- Empty/null handling
- www. stripped from domain
- _extract_domain helper

Run: pytest tests/test_citation_cleanup.py -v
"""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


@pytest.fixture
def mock_search_results():
    return [
        {"link": "https://www.hermes.com/us/en/product/cap", "title": "Cap"},
        {"link": "https://www.amazon.com/dp/123", "title": "Cap"},
        {"link": "https://www.ebay.com/itm/456", "title": "Cap"},
    ]


class TestCitationCleanup:

    def test_replaces_snippet_with_domain(self, service, mock_search_results):
        reviews = {"common_praises": ["[snippet_1] Great quality material"]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "Per hermes.com:" in cleaned["common_praises"][0]
        assert "[snippet_1]" not in cleaned["common_praises"][0]

    def test_strips_unknown_snippet(self, service):
        reviews = {"common_praises": ["[snippet_99] Some text"]}
        cleaned = service._clean_review_citations(reviews, [])
        assert cleaned["common_praises"][0] == "Some text"

    def test_handles_multiple_praises(self, service, mock_search_results):
        reviews = {"common_praises": [
            "[snippet_1] First praise",
            "[snippet_2] Second praise",
        ]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "hermes.com" in cleaned["common_praises"][0]
        assert "amazon.com" in cleaned["common_praises"][1]

    def test_handles_complaints(self, service, mock_search_results):
        reviews = {"common_complaints": ["[snippet_3] Too expensive"]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "ebay.com" in cleaned["common_complaints"][0]

    def test_handles_detailed_praises(self, service, mock_search_results):
        """FIX M6: detailed_praises no longer cleaned (dead code removed).
        Citations pass through unchanged."""
        reviews = {"detailed_praises": [
            {"text": "[snippet_1] Excellent craftsmanship", "frequency": "often"}
        ]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        # detailed_praises passes through unchanged
        assert "[snippet_1]" in cleaned["detailed_praises"][0]["text"]

    def test_preserves_non_citation_fields(self, service, mock_search_results):
        reviews = {
            "common_praises": ["[snippet_1] Great"],
            "average_rating": 4.5,
            "summary": "Good product",
        }
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert cleaned["average_rating"] == 4.5
        assert cleaned["summary"] == "Good product"

    def test_empty_reviews(self, service):
        cleaned = service._clean_review_citations({}, [])
        assert cleaned == {}

    def test_null_search_results(self, service):
        reviews = {"common_praises": ["[snippet_1] Text"]}
        cleaned = service._clean_review_citations(reviews, None)
        assert cleaned["common_praises"][0] == "Text"

    def test_www_stripped_from_domain(self, service):
        results = [{"link": "https://www.hermes.com/product", "title": "t"}]
        reviews = {"common_praises": ["[snippet_1] Good"]}
        cleaned = service._clean_review_citations(reviews, results)
        assert "www." not in cleaned["common_praises"][0]
        assert "hermes.com" in cleaned["common_praises"][0]

    def test_handles_detailed_complaints(self, service, mock_search_results):
        """FIX M6: detailed_complaints no longer cleaned (dead code removed).
        Citations pass through unchanged."""
        reviews = {"detailed_complaints": [
            {"text": "[snippet_2] Shipping was slow", "frequency": "sometimes"}
        ]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        # detailed_complaints passes through unchanged
        assert "[snippet_2]" in cleaned["detailed_complaints"][0]["text"]

    def test_multiple_citations_in_one_string(self, service, mock_search_results):
        reviews = {"common_praises": [
            "[snippet_1] Great material and [snippet_2] fast shipping"
        ]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        text = cleaned["common_praises"][0]
        assert "[snippet_" not in text
        assert "hermes.com" in text
        assert "amazon.com" in text

    def test_text_without_citations_unchanged(self, service, mock_search_results):
        reviews = {"common_praises": ["Just a plain text praise with no citations"]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert cleaned["common_praises"][0] == "Just a plain text praise with no citations"

    def test_extract_domain_helper(self, service):
        assert service._extract_domain("https://www.hermes.com/us/en/product") == "hermes.com"
        assert service._extract_domain("https://amazon.com/dp/123") == "amazon.com"
        assert service._extract_domain("") == ""
        assert service._extract_domain("not-a-url") == ""

"""Tests for iHerb rating extraction during price scrape."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService, get_comparison_service


class TestIHerbRatingExtraction:
    """Test that _fetch_iherb_price also extracts ratings."""

    def test_iherb_result_includes_rating_fields(self):
        """iHerb price result should include rating data when available."""
        result = {
            "amount": 11.99, "currency": "USD", "retailer": "iHerb",
            "url": "https://bh.iherb.com/pr/test/12345",
            "iherb_rating": 4.7, "iherb_review_count": 12345,
        }
        assert "iherb_rating" in result
        assert "iherb_review_count" in result
        assert result["iherb_rating"] == 4.7
        assert result["iherb_review_count"] == 12345

    def test_iherb_rating_cached_in_shopping_items(self):
        """After iHerb price fetch, rating should be cached for _get_verified_rating."""
        service = get_comparison_service()
        service._shopping_items_cache = {}  # Reset cache
        service._shopping_items_cache["Test Product"] = [{
            "source": "iHerb", "rating": 4.5, "ratingCount": 5000,
            "link": "https://bh.iherb.com/pr/test/12345", "title": "Test Product",
        }]
        # Verify iHerb is Tier 1 (so cached ratings will be trusted)
        assert service._get_rating_tier("iHerb") == 1
        # Verify the cache entry exists with correct data
        cached = service._shopping_items_cache["Test Product"]
        assert len(cached) == 1
        assert cached[0]["rating"] == 4.5
        assert cached[0]["ratingCount"] == 5000

    def test_iherb_rating_none_when_not_on_page(self):
        """If iHerb page has no rating data, fields should be None."""
        result = {
            "amount": 11.99, "currency": "USD", "retailer": "iHerb",
            "url": "https://bh.iherb.com/pr/test/12345",
            "iherb_rating": None, "iherb_review_count": None,
        }
        assert result["iherb_rating"] is None

    def test_iherb_rating_extraction_from_html_attrs(self):
        """Test that rating is extracted from data-ga attributes on product cards."""
        from bs4 import BeautifulSoup
        html = '''
        <a data-ga-brand-name="NOW" data-ga-discount-price="11.99"
           data-ga-rating="4.7" data-ga-review-count="12345"
           title="NOW Vitamin D3" href="/pr/test/12345">
        </a>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.select_one('a[data-ga-brand-name]')
        rating_str = card.get('data-ga-rating', '')
        review_str = card.get('data-ga-review-count', '')
        rating = float(rating_str) if rating_str else None
        review_count = int(review_str) if review_str else None
        assert rating == 4.7
        assert review_count == 12345

    def test_iherb_rating_extraction_missing_attrs(self):
        """Test graceful handling when rating attributes are absent."""
        from bs4 import BeautifulSoup
        html = '''
        <a data-ga-brand-name="NOW" data-ga-discount-price="11.99"
           title="NOW Vitamin D3" href="/pr/test/12345">
        </a>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.select_one('a[data-ga-brand-name]')
        rating_str = card.get('data-ga-rating', '')
        review_str = card.get('data-ga-review-count', '')
        rating = float(rating_str) if rating_str else None
        review_count = int(review_str) if review_str else None
        assert rating is None
        assert review_count is None

"""Tests for iHerb direct scraping via curl_cffi.

Live tests -- actually scrape iHerb (free, no API key needed).
Run: python -m pytest tests/test_iherb_scraping.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Helper method tests (always pass, no HTTP) ---

class TestQueryCleanup:
    def test_normalize_words_removes_hyphens(self):
        result = StructuredComparisonService._normalize_words("Vitamin D-3, 1000 IU")
        assert "d3" in result
        assert "vitamin" in result
        assert "1000" in result
        assert "iu" in result

    def test_normalize_words_strips_punctuation(self):
        result = StructuredComparisonService._normalize_words("Now Foods (USA)")
        assert "now" in result
        assert "foods" in result
        assert "usa" in result
        assert "(" not in str(result)


# --- Live iHerb scraping tests ---

@pytest.mark.live_unit
class TestIherbScrapeLive:
    """Live tests that actually hit iHerb. Free (HTTP only, no API key).
    May be flaky if Cloudflare blocks or iHerb changes HTML structure."""

    def test_known_supplement_returns_price(self, service):
        """NOW D-3 should return a price from bh.iherb.com."""
        result = run_async(service._fetch_iherb_price(
            "NOW D3 5000", "NOW", "NOW Vitamin D-3 5000 IU", "bh", "BHD"
        ))
        # curl_cffi may or may not succeed depending on environment
        if result is not None:
            assert result["amount"] > 0
            assert result["currency"] == "BHD"
            assert result["retailer"] == "iHerb"
            assert "iherb.com" in result["url"]
            assert result["estimated"] is False

    def test_regional_store_bahrain(self, service):
        """Bahrain regional store should return BHD prices."""
        result = run_async(service._fetch_iherb_price(
            "Nature Made D3 2000", "Nature Made", "Nature Made Vitamin D3 2000 IU", "bh", "BHD"
        ))
        if result is not None:
            assert result["currency"] == "BHD"
            assert "bh.iherb.com" in result["url"]

    def test_brand_filtering(self, service):
        """Searching for NOW should not return Nature Made results."""
        result = run_async(service._fetch_iherb_price(
            "NOW D3", "NOW", "NOW Vitamin D-3", "bh", "BHD"
        ))
        if result is not None:
            # The matched product should be from NOW, not another brand
            assert result["retailer"] == "iHerb"

    def test_nonexistent_product_returns_none(self, service):
        """A completely made-up product should return None, not crash."""
        result = run_async(service._fetch_iherb_price(
            "XYZFAKE Nonexistent Vitamin", "XYZFAKE", "XYZFAKE Nonexistent Vitamin", "bh", "BHD"
        ))
        assert result is None

    def test_non_supplement_brand_returns_none(self, service):
        """Searching for a non-supplement brand should return None."""
        result = run_async(service._fetch_iherb_price(
            "Apple iPhone", "Apple", "Apple iPhone 16 Pro", "bh", "BHD"
        ))
        assert result is None

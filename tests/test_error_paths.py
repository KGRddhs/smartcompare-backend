"""Tests for error handling and edge cases across the comparison pipeline.

All mocked — these edge cases can't be triggered live.
Run: python -m pytest tests/test_error_paths.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    _convert_to_bhd,
)


@pytest.fixture
def service():
    return StructuredComparisonService()


# --- _convert_to_bhd edge cases ---

class TestConvertToBhd:
    def test_none_currency_returns_amount_unchanged(self):
        """_convert_to_bhd(100, None) should return 100 (no conversion)."""
        assert _convert_to_bhd(100, None) == 100

    def test_usd_to_bhd(self):
        """1 USD = 0.377 BHD."""
        result = _convert_to_bhd(100, "USD")
        assert result == pytest.approx(37.7, abs=0.1)

    def test_bhd_to_bhd_is_identity(self):
        """BHD->BHD should be 1:1."""
        assert _convert_to_bhd(50, "BHD") == 50.0

    def test_unknown_currency_returns_amount(self):
        """Unknown currency code uses rate 1.0 (passthrough)."""
        assert _convert_to_bhd(100, "XYZ") == 100.0

    def test_case_insensitive_currency(self):
        """Currency code should be case-insensitive."""
        assert _convert_to_bhd(100, "usd") == _convert_to_bhd(100, "USD")


# --- _calculate_freshness with None price ---

class TestCalculateFreshness:
    def test_price_none_does_not_crash(self, service):
        """product.price = None (explicitly set) should not crash _calculate_freshness."""
        product = {"specs": {"_cached": False}, "price": None, "reviews": {"_cached": True}}
        result = service._calculate_freshness(product)
        assert result in ("live", "mixed", "cached")

    def test_all_live(self, service):
        product = {"specs": {"_cached": False}, "price": {"_cached": False}, "reviews": {"_cached": False}}
        assert service._calculate_freshness(product) == "live"

    def test_all_cached(self, service):
        product = {"specs": {"_cached": True}, "price": {"_cached": True}, "reviews": {"_cached": True}}
        assert service._calculate_freshness(product) == "cached"

    def test_mixed(self, service):
        product = {"specs": {"_cached": True}, "price": {"_cached": False}, "reviews": {"_cached": True}}
        assert service._calculate_freshness(product) == "mixed"


# --- _parse_price_string edge cases ---

class TestParsePriceString:
    def test_normal_dollar_price(self):
        assert StructuredComparisonService._parse_price_string("$699.99") == pytest.approx(699.99)

    def test_bhd_price(self):
        assert StructuredComparisonService._parse_price_string("BHD 339.000") == pytest.approx(339.0)

    def test_thousands_separator(self):
        assert StructuredComparisonService._parse_price_string("SAR 2,499") == pytest.approx(2499.0)

    def test_garbage_input_returns_none(self):
        assert StructuredComparisonService._parse_price_string("no price here") is None

    def test_empty_string_returns_none(self):
        assert StructuredComparisonService._parse_price_string("") is None

    def test_none_input_returns_none(self):
        assert StructuredComparisonService._parse_price_string(None) is None


# --- _is_supplement_query with anti-keywords ---

class TestIsSupplementQuery:
    def test_vitamin_d3_is_supplement(self):
        assert StructuredComparisonService._is_supplement_query("NOW Vitamin D-3 5000 IU") is True

    def test_galaxy_tablet_is_not_supplement(self):
        """'Galaxy' is in HIGH_VALUE_KEYWORDS — should NOT match even though 'tablet' looks supplement-ish."""
        assert StructuredComparisonService._is_supplement_query("Samsung Galaxy Tablet S9") is False

    def test_iphone_is_not_supplement(self):
        assert StructuredComparisonService._is_supplement_query("Apple iPhone 16 Pro") is False

    def test_omega_3_is_supplement(self):
        assert StructuredComparisonService._is_supplement_query("Nordic Naturals Omega-3") is True

    def test_plain_product_is_not_supplement(self):
        assert StructuredComparisonService._is_supplement_query("Nike Air Max 90") is False


# --- _strict_title_match with hyphens ---

class TestStrictTitleMatch:
    def test_exact_match(self):
        assert StructuredComparisonService._strict_title_match(
            "iPhone 16 Pro Max", "Apple iPhone 16 Pro Max 256GB"
        ) is True

    def test_hyphen_normalization(self):
        """'D-3' should match 'D3' (hyphens removed during normalization)."""
        assert StructuredComparisonService._strict_title_match(
            "Vitamin D-3", "NOW Vitamin D3 5000 IU"
        ) is True

    def test_short_words_skipped(self):
        """Words <=2 chars after hyphen removal are skipped (e.g., 'd3' is only 2 chars)."""
        # "D-3" → "d3" (2 chars) → skipped, only "vitamin" checked
        assert StructuredComparisonService._strict_title_match(
            "Vitamin D-3", "Some Vitamin Product"
        ) is True

    def test_mismatch(self):
        assert StructuredComparisonService._strict_title_match(
            "iPhone 16 Pro Max", "Samsung Galaxy S24 Ultra"
        ) is False

    def test_manufacturer_brand_skipped(self):
        """nvidia/amd/intel skipped since AIB partners rebrand."""
        assert StructuredComparisonService._strict_title_match(
            "NVIDIA RTX 4090", "EVGA GeForce RTX 4090"
        ) is True


# --- _numbers_match edge cases ---

class TestNumbersMatch:
    def test_matching_numbers(self):
        assert StructuredComparisonService._numbers_match(
            "NOW D-3 360 Softgels", "NOW Foods Vitamin D-3 360 Softgels"
        ) is True

    def test_mismatched_numbers(self):
        """360 vs 120 — should NOT match."""
        assert StructuredComparisonService._numbers_match(
            "NOW D-3 360 Softgels", "NOW Foods Vitamin D-3 120 Softgels"
        ) is False

    def test_no_significant_numbers_returns_true(self):
        """No numbers >= 10 in product name → always matches (no constraint to enforce)."""
        assert StructuredComparisonService._numbers_match(
            "NOW Vitamin D-3", "NOW Foods Vitamin D-3 500 IU"
        ) is True

    def test_single_digit_ignored(self):
        """Single digit '3' in D-3 is not a standalone 2+ digit number."""
        assert StructuredComparisonService._numbers_match(
            "Vitamin D-3", "Some Vitamin Product 120 Tablets"
        ) is True

    def test_year_and_count_both_present(self):
        """Both 2024 and 256 should be checked."""
        assert StructuredComparisonService._numbers_match(
            "iPhone 16 256GB", "Apple iPhone 16 256GB 2024"
        ) is True

    def test_year_missing_from_title(self):
        """Product has 256, title has 256 — match (even if year differs)."""
        assert StructuredComparisonService._numbers_match(
            "iPhone 16 256GB", "Apple iPhone 16 256GB"
        ) is True

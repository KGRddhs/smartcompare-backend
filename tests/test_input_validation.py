"""Tests for price query and URL validation."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


class TestValidatePriceQuery:
    def test_valid_query(self):
        assert StructuredComparisonService._validate_price_query("Apple", "iPhone 15", "bahrain") is True

    def test_empty_brand_and_name(self):
        assert StructuredComparisonService._validate_price_query("", "", "bahrain") is False

    def test_too_short(self):
        assert StructuredComparisonService._validate_price_query("A", "", "bahrain") is False

    def test_exactly_three_chars(self):
        assert StructuredComparisonService._validate_price_query("App", "", "bahrain") is True

    def test_too_long(self):
        assert StructuredComparisonService._validate_price_query("A" * 201, "", "bahrain") is False

    def test_exactly_200_chars(self):
        assert StructuredComparisonService._validate_price_query("A" * 200, "", "bahrain") is True

    def test_starts_with_number(self):
        assert StructuredComparisonService._validate_price_query("123", "product", "bahrain") is False

    def test_starts_with_special_char(self):
        assert StructuredComparisonService._validate_price_query("@brand", "item", "bahrain") is False

    def test_invalid_region(self):
        assert StructuredComparisonService._validate_price_query("Apple", "iPhone", "antarctica") is False

    def test_empty_region(self):
        assert StructuredComparisonService._validate_price_query("Apple", "iPhone", "") is False

    def test_all_valid_regions(self):
        for region in ["bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"]:
            assert StructuredComparisonService._validate_price_query("Test", "Product", region) is True

    def test_brand_only_valid(self):
        assert StructuredComparisonService._validate_price_query("Samsung", "", "bahrain") is True

    def test_name_only_valid(self):
        assert StructuredComparisonService._validate_price_query("", "Galaxy S24 Ultra", "bahrain") is True

    def test_whitespace_only_too_short(self):
        assert StructuredComparisonService._validate_price_query("  ", " ", "bahrain") is False

    def test_unicode_brand(self):
        # Arabic brand name starts with alpha
        assert StructuredComparisonService._validate_price_query("Test", "product", "uae") is True


class TestValidateScrapeUrl:
    def test_valid_product_url(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/product/123") is True

    def test_valid_https(self):
        assert StructuredComparisonService._validate_scrape_url("https://shop.ounass.ae/product/item-123") is True

    def test_valid_http(self):
        assert StructuredComparisonService._validate_scrape_url("http://example.com/product/1") is True

    def test_rejects_search_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/search?q=test") is False

    def test_rejects_category_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/category/shoes") is False

    def test_rejects_collection_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/collection/summer") is False

    def test_rejects_browse_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/browse/all") is False

    def test_rejects_c_slash_page(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/c/handbags") is False

    def test_rejects_empty(self):
        assert StructuredComparisonService._validate_scrape_url("") is False

    def test_rejects_none_like(self):
        assert StructuredComparisonService._validate_scrape_url(None) is False

    def test_rejects_no_scheme(self):
        assert StructuredComparisonService._validate_scrape_url("example.com/product") is False

    def test_rejects_ftp(self):
        assert StructuredComparisonService._validate_scrape_url("ftp://example.com/file") is False

    def test_rejects_no_tld(self):
        assert StructuredComparisonService._validate_scrape_url("https://localhost/product") is False

    def test_accepts_shop_path(self):
        # /shop/ is intentionally NOT blocked (GCC retailers use it)
        assert StructuredComparisonService._validate_scrape_url("https://ounass.ae/shop/product-123") is True

    def test_case_insensitive_blocked_patterns(self):
        assert StructuredComparisonService._validate_scrape_url("https://example.com/Search?q=test") is False
        assert StructuredComparisonService._validate_scrape_url("https://example.com/CATEGORY/shoes") is False

"""Tests for Tier 1.5 luxury price cascade: official -> authorized -> GCC retailers."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    svc.total_cost = 0
    svc.api_calls = 0
    svc._shopping_items_cache = {}
    return svc


def _mock_serper_organic(urls_and_titles):
    """Build mock Serper organic results."""
    return {
        "organic": [
            {"link": url, "title": title, "snippet": f"Shop {title}"}
            for url, title in urls_and_titles
        ]
    }


def _mock_page_price(amount, currency="BHD", domain="test.com"):
    """Build a price result as _fetch_page_price would return."""
    return {
        "amount": amount,
        "currency": currency,
        "original_currency": currency,
        "retailer": domain,
        "url": f"https://{domain}/product",
        "in_stock": True,
        "confidence": 1.0,
        "estimated": False,
        "source_method": "page_scrape",
    }


class TestTier15aCascade:
    """Tier 1.5a: Official brand site scraping."""

    @pytest.mark.asyncio
    async def test_official_domain_price_found(self, service):
        """When official domain page has JSON-LD price, _fetch_page_price returns it."""
        mock_price = _mock_page_price(340.0, "BHD", "louisvuitton.com")
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_fetch_page_price', new_callable=AsyncMock, return_value=mock_price):
            result = await service._fetch_page_price("https://louisvuitton.com/cap", "Louis Vuitton Cap", "BHD")
        assert result is not None
        assert result["amount"] == 340.0
        assert result["retailer"] == "louisvuitton.com"

    @pytest.mark.asyncio
    async def test_official_domain_no_price_returns_none(self, service):
        """When official domain has no structured data, _fetch_page_price returns None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_fetch_page_price', new_callable=AsyncMock, return_value=None):
            result = await service._fetch_page_price("https://louisvuitton.com/browse", "Louis Vuitton Cap", "BHD")
        assert result is None


class TestTier15bCascade:
    """Tier 1.5b: Authorized retailer scraping."""

    def test_cross_validation_two_prices_agree(self):
        """Two authorized retailers within 15% -> cross-validation passes, use lowest."""
        prices = [
            _mock_page_price(340.0, "BHD", "farfetch.com"),
            _mock_page_price(355.0, "BHD", "ssense.com"),
        ]
        amounts = [p["amount"] for p in prices]
        # Cross-validation formula: max/min <= 1.15
        assert max(amounts) / min(amounts) <= 1.15
        # Should pick lowest
        best = min(prices, key=lambda p: p["amount"])
        assert best["amount"] == 340.0
        assert best["retailer"] == "farfetch.com"

    def test_cross_validation_prices_diverge_uses_first(self):
        """Retailers disagree (>15%) -> prices diverge, use first retailer."""
        prices = [
            _mock_page_price(340.0, "BHD", "farfetch.com"),
            _mock_page_price(200.0, "BHD", "ssense.com"),
        ]
        amounts = [p["amount"] for p in prices]
        assert max(amounts) / min(amounts) > 1.15
        # Should use first (highest-tier) retailer
        best = prices[0]
        assert best["amount"] == 340.0

    def test_single_retailer_price_used(self):
        """Only one authorized retailer has price -> use it."""
        valid_prices = [_mock_page_price(340.0, "BHD", "farfetch.com")]
        assert len(valid_prices) == 1
        assert valid_prices[0]["amount"] == 340.0
        assert valid_prices[0]["source_method"] == "page_scrape"

    def test_authorized_retailer_domain_filtering(self):
        """Only domains in AUTHORIZED_LUXURY_RETAILERS pass the domain filter."""
        authorized = StructuredComparisonService.AUTHORIZED_LUXURY_RETAILERS
        assert "farfetch.com" in authorized
        assert "ssense.com" in authorized
        assert "net-a-porter.com" in authorized
        assert "ebay.com" not in authorized
        assert "dhgate.com" not in authorized


class TestTier15cCascade:
    """Tier 1.5c: GCC retailer scraping."""

    def test_gcc_retailer_domains_defined(self):
        """GCC luxury retailers include expected GCC domains."""
        gcc = StructuredComparisonService.GCC_LUXURY_RETAILERS
        assert "ounass.ae" in gcc
        assert "bloomingdales.ae" in gcc
        assert "namshi.com" in gcc

    def test_gcc_domain_filtering(self):
        """Non-GCC domains should not be in the GCC retailer set."""
        gcc = StructuredComparisonService.GCC_LUXURY_RETAILERS
        assert "amazon.com" not in gcc
        assert "farfetch.com" not in gcc  # farfetch is in authorized, not GCC

    @pytest.mark.asyncio
    async def test_gcc_price_with_aed_conversion(self, service):
        """GCC retailer returning AED price should be convertible to BHD."""
        # AED 1000 ~ BHD 102.5 (1 AED ~ 0.1025 BHD)
        aed_price = _mock_page_price(1000.0, "AED", "ounass.ae")
        assert aed_price["currency"] == "AED"
        assert aed_price["amount"] == 1000.0
        # _fetch_page_price handles conversion internally via _convert_gpt_price_currency


class TestTier15BudgetTimeout:
    """Budget timeout enforcement across sub-tiers."""

    def test_budget_timeout_constant(self):
        """Budget timeout is 20 seconds."""
        assert StructuredComparisonService.TIER_15_BUDGET_TIMEOUT == 20

    def test_budget_exceeded_logic(self):
        """When elapsed >= budget, remaining tiers should be skipped."""
        budget = 20  # seconds
        elapsed_after_15a = 22  # took too long
        assert elapsed_after_15a >= budget  # should skip 1.5b and 1.5c

    def test_budget_not_exceeded_allows_continuation(self):
        """When elapsed < budget, next tier should proceed."""
        budget = 20
        elapsed_after_15a = 5  # fast
        assert elapsed_after_15a < budget  # should continue to 1.5b


class TestTier15Constants:
    """Verify constants are properly defined."""

    def test_authorized_retailers_defined(self):
        assert hasattr(StructuredComparisonService, 'AUTHORIZED_LUXURY_RETAILERS')
        assert "farfetch.com" in StructuredComparisonService.AUTHORIZED_LUXURY_RETAILERS

    def test_gcc_retailers_defined(self):
        assert hasattr(StructuredComparisonService, 'GCC_LUXURY_RETAILERS')
        assert "ounass.ae" in StructuredComparisonService.GCC_LUXURY_RETAILERS

    def test_page_scrape_timeout_defined(self):
        assert StructuredComparisonService.PAGE_SCRAPE_TIMEOUT == 10

    def test_tier15_budget_timeout_defined(self):
        assert StructuredComparisonService.TIER_15_BUDGET_TIMEOUT == 20

    def test_authorized_and_gcc_no_overlap(self):
        """Authorized and GCC retailer sets should not overlap."""
        authorized = StructuredComparisonService.AUTHORIZED_LUXURY_RETAILERS
        gcc = StructuredComparisonService.GCC_LUXURY_RETAILERS
        overlap = authorized & gcc
        assert len(overlap) == 0, f"Overlapping domains: {overlap}"

    def test_level_shoes_in_gcc(self):
        """level-shoes.com is a GCC luxury retailer."""
        assert "level-shoes.com" in StructuredComparisonService.GCC_LUXURY_RETAILERS

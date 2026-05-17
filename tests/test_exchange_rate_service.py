"""Tests for exchange rate service — daily rates with Redis cache and fallback."""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from app.services.exchange_rate_service import (
    get_rate,
    _fetch_rates,
    _lookup_rate,
    _fallback_rate,
    FALLBACK_RATES,
    _CACHE_TTL,
)


@pytest.fixture
def mock_redis_helpers():
    """Mock _redis_get/_redis_set at the exchange_rate_service module level."""
    store = {}

    def fake_get(key):
        return store.get(key)

    def fake_set(key, value, ex=None):
        store[key] = value
        return True

    with patch("app.services.exchange_rate_service._redis_get", side_effect=fake_get) as m_get, \
         patch("app.services.exchange_rate_service._redis_set", side_effect=fake_set) as m_set:
        yield {"get": m_get, "set": m_set, "store": store}


@pytest.fixture
def mock_httpx():
    """Mock httpx.AsyncClient for API calls."""
    with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
        yield mock_client


class TestGetRateBasics:
    """Test basic get_rate() functionality."""

    @pytest.mark.asyncio
    async def test_same_currency_returns_one(self):
        """Same currency (BHD→BHD) should return 1.0."""
        rate = await get_rate("BHD", "BHD")
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_same_currency_case_insensitive(self):
        """Same currency in different cases should return 1.0."""
        rate = await get_rate("bhd", "BHD")
        assert rate == 1.0

        rate = await get_rate("USD", "usd")
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_hardcoded_fallback_usd_to_bhd(self, mock_redis_helpers, mock_httpx):
        """USD→BHD returns hardcoded 0.376 when API and Redis unavailable."""
        # Redis cache miss
        mock_redis_helpers["store"] = {}

        # API failure
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("API down"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("USD", "BHD")
        assert rate == 0.376

    @pytest.mark.asyncio
    async def test_hardcoded_fallback_eur_to_bhd(self, mock_redis_helpers, mock_httpx):
        """EUR→BHD returns approximately 0.41 when API unavailable."""
        mock_redis_helpers["store"] = {}

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("API down"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("EUR", "BHD")
        assert rate == 0.41

    @pytest.mark.asyncio
    async def test_hardcoded_fallback_sar_to_bhd(self, mock_redis_helpers, mock_httpx):
        """SAR→BHD returns approximately 0.1003 when API unavailable."""
        mock_redis_helpers["store"] = {}

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("API down"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("SAR", "BHD")
        assert rate == 0.1003


class TestRedisCache:
    """Test Redis caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_no_api_call(self, mock_redis_helpers, mock_httpx):
        """Cache hit should return cached rate without API call."""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"exchange_rates:{today}"

        # Populate cache with rates (USD-based)
        cached_rates = {
            "USD": 1.0,
            "BHD": 2.66,  # 1/0.376 ≈ 2.66
            "EUR": 0.92,
        }
        mock_redis_helpers["store"][cache_key] = json.dumps(cached_rates)

        rate = await get_rate("USD", "BHD")

        # Should get rate from cache: BHD/USD = 2.66/1.0 = 2.66
        assert rate == pytest.approx(2.66, rel=0.01)

        # Verify no API call made
        mock_httpx.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_api_success_sets_cache(self, mock_redis_helpers, mock_httpx):
        """Cache miss + API success should fetch and cache rate."""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"exchange_rates:{today}"

        # Cache miss
        mock_redis_helpers["store"] = {}

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {
                "BHD": 2.66,
                "EUR": 0.92,
                "GBP": 0.79,
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        rate = await get_rate("USD", "BHD")

        # Verify rate returned
        assert rate == pytest.approx(2.66, rel=0.01)

        # Verify cache was set
        mock_redis_helpers["set"].assert_called_once()
        call_args = mock_redis_helpers["set"].call_args
        assert call_args[0][0] == cache_key
        assert call_args[1]["ex"] == _CACHE_TTL

    @pytest.mark.asyncio
    async def test_cache_miss_api_failure_uses_fallback(self, mock_redis_helpers, mock_httpx):
        """Cache miss + API failure should use hardcoded fallback."""
        mock_redis_helpers["store"] = {}

        # Mock API failure
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("API error"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("USD", "BHD")

        # Should fall back to hardcoded
        assert rate == FALLBACK_RATES["USD"]

    @pytest.mark.asyncio
    async def test_malformed_cache_data_fetches_api(self, mock_redis_helpers, mock_httpx):
        """Malformed cache data should trigger API fetch."""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"exchange_rates:{today}"

        # Put invalid JSON in cache
        mock_redis_helpers["store"][cache_key] = "not-valid-json"

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {"BHD": 2.66}
        }
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        rate = await get_rate("USD", "BHD")

        # Should fetch from API despite cache presence
        assert rate == pytest.approx(2.66, rel=0.01)
        mock_httpx.assert_called_once()


class TestAPICall:
    """Test Frankfurter API interaction."""

    @pytest.mark.asyncio
    async def test_api_success_returns_rates(self, mock_redis_helpers, mock_httpx):
        """Successful API call should return rate data."""
        mock_redis_helpers["store"] = {}

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "base": "USD",
            "rates": {
                "BHD": 2.66,
                "EUR": 0.92,
                "GBP": 0.79,
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        rate = await get_rate("EUR", "BHD")

        # EUR→BHD = 2.66 / 0.92 ≈ 2.89
        expected = 2.66 / 0.92
        assert rate == pytest.approx(expected, rel=0.01)

    @pytest.mark.asyncio
    async def test_api_exception_uses_fallback(self, mock_redis_helpers, mock_httpx):
        """API exception should fall back to hardcoded rates."""
        mock_redis_helpers["store"] = {}

        # Mock API exception
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("Network error"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("GBP", "BHD")

        # Should use fallback
        assert rate == FALLBACK_RATES["GBP"]

    @pytest.mark.asyncio
    async def test_api_timeout_uses_fallback(self, mock_redis_helpers, mock_httpx):
        """API timeout should fall back to hardcoded rates."""
        mock_redis_helpers["store"] = {}

        # Mock timeout
        import httpx
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("EUR", "BHD")

        assert rate == FALLBACK_RATES["EUR"]

    @pytest.mark.asyncio
    async def test_correct_url_constructed(self, mock_redis_helpers, mock_httpx):
        """Verify correct Frankfurter API URL is used."""
        mock_redis_helpers["store"] = {}

        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"BHD": 2.66}}
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        await get_rate("USD", "BHD")

        # Verify API called with correct URL and params
        mock_instance.get.assert_called_once_with(
            "https://api.frankfurter.app/latest",
            params={"from": "USD"}
        )

    @pytest.mark.asyncio
    async def test_api_adds_usd_base_currency(self, mock_redis_helpers):
        """_fetch_rates should add USD: 1.0 to returned rates."""
        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "rates": {
                    "EUR": 0.92,
                    "GBP": 0.79,
                }
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            rates = await _fetch_rates()

            # Should include USD: 1.0
            assert "USD" in rates
            assert rates["USD"] == 1.0
            assert "EUR" in rates
            assert "GBP" in rates


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_unknown_currency_pair_returns_one(self, mock_redis_helpers, mock_httpx):
        """Unknown currency pair should fall back gracefully to 1.0."""
        mock_redis_helpers["store"] = {}

        # Mock API failure
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("API down"))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("XXX", "YYY")

        # Unknown currencies not in FALLBACK_RATES → should return 1.0
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_redis_error_during_get_doesnt_crash(self, mock_httpx):
        """Redis error during get should fail-open and try API."""
        # _redis_get returns None on error, which is how cache_service handles errors
        with patch("app.services.exchange_rate_service._redis_get", return_value=None):
            # Mock API success
            mock_response = MagicMock()
            mock_response.json.return_value = {"rates": {"BHD": 2.66}}
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_instance

            rate = await get_rate("USD", "BHD")

            # Should still get rate from API
            assert rate == pytest.approx(2.66, rel=0.01)

    @pytest.mark.asyncio
    async def test_redis_error_during_set_doesnt_crash(self, mock_redis_helpers, mock_httpx):
        """Redis error during set should not crash."""
        mock_redis_helpers["store"] = {}

        # Mock API success
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"BHD": 2.66}}
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        # _redis_set returns False on error (handled internally by cache_service)
        with patch("app.services.exchange_rate_service._redis_set", return_value=False):
            rate = await get_rate("USD", "BHD")

            # Should still return rate despite cache failure
            assert rate == pytest.approx(2.66, rel=0.01)

    @pytest.mark.asyncio
    async def test_cached_rate_missing_currency(self, mock_redis_helpers, mock_httpx):
        """Cache has rates but missing requested currency → fetch API."""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"exchange_rates:{today}"

        # Cache has some rates but not the one we need
        cached_rates = {
            "USD": 1.0,
            "EUR": 0.92,
            # Missing BHD
        }
        mock_redis_helpers["store"][cache_key] = json.dumps(cached_rates)

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {"BHD": 2.66}
        }
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        rate = await get_rate("USD", "BHD")

        # Should fetch from API since BHD not in cache
        assert rate == pytest.approx(2.66, rel=0.01)
        mock_httpx.assert_called_once()

    def test_lookup_rate_success(self):
        """_lookup_rate should compute cross-rate correctly."""
        rates = {
            "USD": 1.0,
            "EUR": 0.92,
            "BHD": 2.66,
        }

        # EUR→BHD = 2.66 / 0.92
        rate = _lookup_rate(rates, "EUR", "BHD")
        expected = 2.66 / 0.92
        assert rate == pytest.approx(expected, rel=0.001)

    def test_lookup_rate_missing_from_currency(self):
        """_lookup_rate returns None if from_currency missing."""
        rates = {"USD": 1.0, "EUR": 0.92}
        rate = _lookup_rate(rates, "GBP", "EUR")
        assert rate is None

    def test_lookup_rate_missing_to_currency(self):
        """_lookup_rate returns None if to_currency missing."""
        rates = {"USD": 1.0, "EUR": 0.92}
        rate = _lookup_rate(rates, "EUR", "GBP")
        assert rate is None

    def test_fallback_rate_usd_to_bhd(self):
        """_fallback_rate should return hardcoded USD→BHD."""
        rate = _fallback_rate("USD", "BHD")
        assert rate == FALLBACK_RATES["USD"]

    def test_fallback_rate_cross_rate(self):
        """_fallback_rate should compute cross-rate from BHD-based table."""
        # EUR→SAR = (EUR→BHD) / (SAR→BHD) = 0.41 / 0.1003
        rate = _fallback_rate("EUR", "SAR")
        expected = FALLBACK_RATES["EUR"] / FALLBACK_RATES["SAR"]
        assert rate == pytest.approx(expected, rel=0.001)

    def test_fallback_rate_unknown_from_currency(self):
        """_fallback_rate returns 1.0 for unknown from_currency."""
        rate = _fallback_rate("XXX", "BHD")
        assert rate == 1.0

    def test_fallback_rate_unknown_to_currency(self):
        """_fallback_rate returns 1.0 for unknown to_currency."""
        rate = _fallback_rate("USD", "YYY")
        assert rate == 1.0

    def test_fallback_rate_both_unknown(self):
        """_fallback_rate returns 1.0 when both currencies unknown."""
        rate = _fallback_rate("XXX", "YYY")
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_case_insensitive_currency_codes(self, mock_redis_helpers, mock_httpx):
        """Currency codes should be case-insensitive."""
        mock_redis_helpers["store"] = {}

        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"BHD": 2.66}}
        mock_response.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_instance

        # Test lowercase
        rate = await get_rate("usd", "bhd")
        assert rate == pytest.approx(2.66, rel=0.01)

        # Verify API called with uppercase (after normalization)
        mock_instance.get.assert_called_with(
            "https://api.frankfurter.app/latest",
            params={"from": "USD"}
        )

    @pytest.mark.asyncio
    async def test_api_http_error_uses_fallback(self, mock_redis_helpers, mock_httpx):
        """API HTTP error should fall back to hardcoded rates."""
        mock_redis_helpers["store"] = {}

        import httpx
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock()
        ))
        mock_httpx.return_value = mock_instance

        rate = await get_rate("AED", "BHD")

        assert rate == FALLBACK_RATES["AED"]

    @pytest.mark.asyncio
    async def test_all_gcc_currencies_have_fallbacks(self, mock_redis_helpers, mock_httpx):
        """All GCC currencies should have hardcoded fallback rates."""
        gcc_currencies = ["BHD", "SAR", "AED", "KWD", "QAR", "OMR"]

        for currency in gcc_currencies:
            assert currency in FALLBACK_RATES, f"{currency} missing from FALLBACK_RATES"

            # Verify fallback works
            mock_redis_helpers["store"] = {}

            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("API down"))
            mock_httpx.return_value = mock_instance

            rate = await get_rate(currency, "BHD")
            assert rate > 0  # Should get a valid rate


# ============================================================
# Bucket A bug 4 — Task 4.1: fallback rates cover all source currencies
# seen in scraped data (LV/Gucci luxury bench surfaced SGD as 1.0 BHD).
# ============================================================

REQUIRED_SOURCE_CURRENCIES = ["USD", "EUR", "GBP", "SGD", "JPY", "CNY", "INR"]
GCC_TARGET_CURRENCIES = ["BHD", "SAR", "AED", "KWD", "QAR", "OMR"]


def test_fallback_rates_cover_all_source_currencies():
    """Every currency we've seen in scraped data must have a fallback rate."""
    missing = [c for c in REQUIRED_SOURCE_CURRENCIES if c not in FALLBACK_RATES]
    assert not missing, f"FALLBACK_RATES missing source currencies: {missing}"


def test_fallback_rates_cover_all_gcc_targets():
    """All 6 GCC region currencies must be in the table."""
    missing = [c for c in GCC_TARGET_CURRENCIES if c not in FALLBACK_RATES]
    assert not missing, f"FALLBACK_RATES missing GCC target currencies: {missing}"


def test_sgd_to_bhd_in_reasonable_range():
    """SGD->BHD rate must be ~0.27-0.30 (1 SGD ~= 0.28 BHD as of 2026-05)."""
    rate = _fallback_rate("SGD", "BHD")
    assert 0.25 <= rate <= 0.32, f"SGD->BHD rate {rate} outside plausible band"


def test_jpy_to_bhd_in_reasonable_range():
    """JPY->BHD rate must be ~0.002-0.003."""
    rate = _fallback_rate("JPY", "BHD")
    assert 0.002 <= rate <= 0.004, f"JPY->BHD rate {rate} outside plausible band"


# Extra coverage (Bucket A bug 4 follow-up) ----------------------------------

def test_cny_to_bhd_in_reasonable_range():
    """CNY->BHD rate must be ~0.04-0.06."""
    rate = _fallback_rate("CNY", "BHD")
    assert 0.04 <= rate <= 0.07, f"CNY->BHD rate {rate} outside plausible band"


def test_inr_to_bhd_in_reasonable_range():
    """INR->BHD rate must be ~0.004-0.005."""
    rate = _fallback_rate("INR", "BHD")
    assert 0.003 <= rate <= 0.006, f"INR->BHD rate {rate} outside plausible band"


def test_fallback_rate_sgd_cross_rate_to_sar():
    """SGD->SAR cross rate is computed via SGD->BHD->SAR."""
    rate = _fallback_rate("SGD", "SAR")
    # SGD=0.282, SAR=0.1003 -> 0.282/0.1003 = ~2.81
    assert 2.7 <= rate <= 2.9, f"SGD->SAR cross rate {rate} outside plausible band"

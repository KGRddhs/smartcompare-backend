"""Exchange Rate Service — daily rates with Redis cache and hardcoded fallback.

Uses the free Frankfurter API (https://api.frankfurter.app) for daily rates.
Caches in Redis with 24h TTL. Falls back to hardcoded rates if API is unavailable.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx

from app.services.cache_service import _redis_get, _redis_set

logger = logging.getLogger(__name__)

# Hardcoded fallback rates (to BHD)
FALLBACK_RATES: Dict[str, float] = {
    "USD": 0.376,
    "EUR": 0.41,
    "GBP": 0.475,
    "SGD": 0.282,    # 1 SGD = 0.282 BHD (as of 2026-05)
    "JPY": 0.0025,
    "CNY": 0.052,
    "INR": 0.0045,
    "SAR": 0.1003,
    "AED": 0.1024,
    "KWD": 1.23,
    "QAR": 0.1033,
    "OMR": 0.977,
    "BHD": 1.0,
}

_CACHE_TTL = 24 * 3600  # 24 hours


async def get_rate(from_currency: str, to_currency: str = "BHD") -> float:
    """Get exchange rate from one currency to another.

    Args:
        from_currency: Source currency code (e.g. "USD", "EUR").
        to_currency: Target currency code, defaults to "BHD".

    Returns:
        The exchange rate as a float. Falls back to hardcoded rates on failure.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    # Try cached rates first
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"exchange_rates:{today}"

    cached = _redis_get(cache_key)
    if cached:
        try:
            rates = json.loads(cached)
            rate = _lookup_rate(rates, from_currency, to_currency)
            if rate is not None:
                return rate
        except (json.JSONDecodeError, KeyError):
            pass

    # Fetch fresh rates from Frankfurter API
    rates = await _fetch_rates()
    if rates:
        _redis_set(cache_key, json.dumps(rates), ex=_CACHE_TTL)
        rate = _lookup_rate(rates, from_currency, to_currency)
        if rate is not None:
            return rate

    # Fallback to hardcoded rates
    return _fallback_rate(from_currency, to_currency)


async def _fetch_rates() -> Optional[Dict[str, float]]:
    """Fetch latest rates from Frankfurter API. Returns dict of {currency: rate_to_USD}."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.frankfurter.app/latest",
                params={"from": "USD"},
            )
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})
            rates["USD"] = 1.0  # Add base currency
            return rates
    except Exception as e:
        logger.warning(f"[EXCHANGE] Failed to fetch rates: {e}")
        return None


def _lookup_rate(
    rates: Dict[str, float], from_currency: str, to_currency: str
) -> Optional[float]:
    """Compute cross-rate from USD-based rate table."""
    from_rate = rates.get(from_currency)
    to_rate = rates.get(to_currency)
    if from_rate and to_rate:
        return to_rate / from_rate
    return None


def _fallback_rate(from_currency: str, to_currency: str) -> float:
    """Compute rate from hardcoded BHD-based fallback table."""
    # FALLBACK_RATES maps currency -> BHD
    from_to_bhd = FALLBACK_RATES.get(from_currency)
    to_to_bhd = FALLBACK_RATES.get(to_currency)

    if from_to_bhd and to_to_bhd:
        # from_currency -> BHD -> to_currency
        return from_to_bhd / to_to_bhd

    # Unknown currency — return 1.0 as safe default
    logger.warning(
        f"[EXCHANGE] No fallback rate for {from_currency}->{to_currency}, returning 1.0"
    )
    return 1.0

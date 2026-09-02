"""Exchange Rate Service — daily rates with Redis cache and hardcoded fallback.

Uses the free Frankfurter API (https://api.frankfurter.app) for daily rates.
Caches in Redis with 24h TTL. Falls back to hardcoded rates if API is unavailable.
"""
import json
import logging
import os
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

# M13-38 — the currencies the _proof corpus actually carries that are ABSENT from
# FALLBACK_RATES, so their pages PEND today (a TRY page returns None, ENABLE_RSC_
# FLIGHT_PRICE's entire measured cohort is dead). Approximate BHD rates as of
# 2026 — the exact figure is not load-bearing (any positive rate converts instead
# of pending; the live table via _fetch_rates is the authoritative source when a
# fetcher is wired). Gated behind a DEFAULT-OFF flag so widening the table cannot
# change the flag-OFF extract_price_from_html output (TRY/PLN/CAD/JOD corpus pages
# that pend today would otherwise convert, breaking flag-OFF byte-identity).
FALLBACK_RATES_EXTENDED: Dict[str, float] = {
    "TRY": 0.0094,   # Turkish lira
    "PLN": 0.094,    # Polish zloty
    "CAD": 0.274,    # Canadian dollar
    "JOD": 0.531,    # Jordanian dinar (3-decimal)
    "SEK": 0.035,    # Swedish krona
    "DKK": 0.0545,   # Danish krone
    "CHF": 0.427,    # Swiss franc
    "EGP": 0.0078,   # Egyptian pound
    "NOK": 0.034,    # Norwegian krone
    "AUD": 0.245,    # Australian dollar
}


def extended_fallback_rates_enabled() -> bool:
    """True iff FALLBACK_RATES is widened with the corpus currencies (default OFF).

    M13-38. Read PER CALL from os.getenv so Railway can flip it without a
    restart; default OFF so the effective table — and therefore the flag-OFF
    extract_price_from_html output — is byte-identical to 5ee72e8.
    """
    return os.getenv("ENABLE_EXTENDED_FALLBACK_RATES", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def effective_fallback_rates() -> Dict[str, float]:
    """The rate table price_service should convert against: the base 13 currencies,
    plus the corpus tail when ``extended_fallback_rates_enabled()``. A NEW dict on
    each ON call (never mutate FALLBACK_RATES) so the base table stays pristine."""
    if extended_fallback_rates_enabled():
        return {**FALLBACK_RATES, **FALLBACK_RATES_EXTENDED}
    return FALLBACK_RATES


def is_convertible(currency: Optional[str]) -> bool:
    """True iff ``currency`` has a BHD rate in the EFFECTIVE fallback table.

    M21 W4 (CD-wave-diffs-08 residual) — the ONE convertibility gate every
    direct adapter (shopify_pdp/algolia/magento_graphql/occ/rest_json/unbxd/
    woocommerce/salla) consults before shipping a converted price, replacing
    eight per-module ``x in FALLBACK_RATES`` reads (and salla's hand-copied
    mirror set) that ignored ENABLE_EXTENDED_FALLBACK_RATES and so kept
    dropping TRY/PLN/CAD stores with the flag ON.

    Membership is EXACT — no case folding, no stripping — so with the flag
    unset this is byte-identical to the old ``x in FALLBACK_RATES`` gates
    (keys are uppercase ISO codes; each caller normalises case exactly as it
    did before). ``None``/empty never convert.
    """
    return (currency or "") in effective_fallback_rates()


# Maps backend region codes to their native currency.
# Used by price pipeline to display prices in the user's region currency.
REGION_TO_CURRENCY: Dict[str, str] = {
    "bahrain": "BHD",
    "saudi_arabia": "SAR",
    "uae": "AED",
    "kuwait": "KWD",
    "qatar": "QAR",
    "oman": "OMR",
}


def get_region_currency(region: Optional[str]) -> str:
    """Return native currency for a GCC region. Defaults to BHD."""
    if not region:
        return "BHD"
    return REGION_TO_CURRENCY.get(region.lower(), "BHD")


_CACHE_TTL = 24 * 3600  # 24 hours


async def get_rate(from_currency: str, to_currency: str = "BHD") -> Optional[float]:
    """Get exchange rate from one currency to another.

    Args:
        from_currency: Source currency code (e.g. "USD", "EUR").
        to_currency: Target currency code, defaults to "BHD".

    Returns:
        The exchange rate as a float, or None when neither the live nor the
        hardcoded table can resolve the pair. M13-39 — None replaces the old
        implicit-1.0 stamp: an UNKNOWN currency must NOT be silently treated as
        1:1 with the target (the exact failure the currency wave exists to kill).
        This function has zero production callers today; the production converter
        is price_service._convert_to_bhd.
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

    # Fallback to hardcoded rates. M13-39 — an unknown currency now yields None
    # (never an implicit 1.0), so surface that honestly rather than fabricating a
    # rate: the caller must treat None as "cannot convert" (pend), the same
    # posture strict_currency_label_enabled() takes on the production path.
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


def _fallback_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """Compute rate from hardcoded BHD-based fallback table.

    M13-39 — an unknown currency returns None, NOT 1.0. Returning 1.0 was the
    implicit-1.0 stamp the whole currency wave exists to eliminate: it declared a
    foreign amount to be 1:1 with the target and shipped it as a real number.
    None makes the caller pend instead. Same-currency (from == to) still returns
    1.0, and the extended-corpus tail participates so a TRY/PLN/CAD/JOD pair
    resolves when the extension flag is on.
    """
    # FALLBACK_RATES maps currency -> BHD; include the corpus tail when enabled.
    rates = effective_fallback_rates()
    from_to_bhd = rates.get(from_currency)
    to_to_bhd = rates.get(to_currency)

    if from_to_bhd and to_to_bhd:
        # from_currency -> BHD -> to_currency
        return from_to_bhd / to_to_bhd

    # Unknown currency — None, never an implicit 1.0 (M13-39).
    logger.warning(
        f"[EXCHANGE] No fallback rate for {from_currency}->{to_currency}, "
        "returning None (cannot convert)"
    )
    return None

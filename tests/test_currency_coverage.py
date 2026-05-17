"""Bucket A bug 4 — extra coverage for currency helpers.

Complements tests/test_exchange_rate_service.py and tests/test_price_service.py
by covering edge cases the team's TDD tests don't directly exercise:
- _convert_to_bhd case-insensitivity (lowercase currency input)
- _convert_to_bhd empty / None currency input
- get_region_currency case-insensitivity (e.g. "Bahrain" not "bahrain")
- get_region_currency boundary values (None, "", unknown)
- FALLBACK_RATES round-trip (currency -> BHD -> currency yields 1.0 for same input)
"""
import logging
import pytest

from app.services.exchange_rate_service import (
    FALLBACK_RATES,
    REGION_TO_CURRENCY,
    get_region_currency,
    _fallback_rate,
)
from app.services.price_service import _convert_to_bhd


# ---------------------------------------------------------------
# _convert_to_bhd — case-insensitivity + boundary input
# ---------------------------------------------------------------

def test_convert_to_bhd_lowercase_sgd_converts_correctly():
    """Lowercase 'sgd' must convert as if it were 'SGD' (no warning, real rate)."""
    result = _convert_to_bhd(1000.0, "sgd")
    expected = 1000.0 * FALLBACK_RATES["SGD"]
    assert result == pytest.approx(expected, rel=0.001), \
        f"Expected lowercase 'sgd' to convert like 'SGD' ({expected}), got {result}"


def test_convert_to_bhd_mixed_case_eur_converts_correctly():
    """Mixed-case 'Eur' must convert as if it were 'EUR'."""
    result = _convert_to_bhd(100.0, "Eur")
    expected = 100.0 * FALLBACK_RATES["EUR"]
    assert result == pytest.approx(expected, rel=0.001)


def test_convert_to_bhd_empty_string_returns_amount_unchanged():
    """Empty currency string is a 'no conversion' signal — must return amount as-is."""
    result = _convert_to_bhd(1234.56, "")
    assert result == 1234.56


def test_convert_to_bhd_none_currency_returns_amount_unchanged():
    """None currency must not crash; returns amount unchanged."""
    # type: ignore — runtime resilience for upstream callers that may pass None
    result = _convert_to_bhd(99.0, None)  # type: ignore[arg-type]
    assert result == 99.0


def test_convert_to_bhd_bhd_to_bhd_identity():
    """BHD source is a no-op multiplication by 1.0."""
    result = _convert_to_bhd(500.0, "BHD")
    assert result == 500.0


def test_convert_to_bhd_unknown_currency_logs_warning(caplog):
    """Unknown currency must log a warning explaining how to fix it."""
    caplog.set_level(logging.WARNING)
    result = _convert_to_bhd(1000.0, "ZZZ")

    # amount returned unchanged on unknown currency
    assert result == 1000.0

    # warning surfaces the offending currency
    warned = any(
        "ZZZ" in record.message
        for record in caplog.records
        if record.levelno >= logging.WARNING
    )
    assert warned, f"Expected WARNING mentioning ZZZ. Records: {[r.message for r in caplog.records]}"


def test_convert_to_bhd_zero_amount_safe():
    """Zero amount returns zero regardless of currency."""
    assert _convert_to_bhd(0.0, "SGD") == 0.0
    assert _convert_to_bhd(0.0, "BHD") == 0.0


# ---------------------------------------------------------------
# get_region_currency — case-insensitivity + boundary input
# ---------------------------------------------------------------

def test_get_region_currency_mixed_case_bahrain():
    """get_region_currency must lowercase input before lookup."""
    assert get_region_currency("Bahrain") == "BHD"
    assert get_region_currency("BAHRAIN") == "BHD"
    assert get_region_currency("BaHrAiN") == "BHD"


def test_get_region_currency_mixed_case_saudi_arabia():
    """saudi_arabia in any casing maps to SAR."""
    assert get_region_currency("Saudi_Arabia") == "SAR"
    assert get_region_currency("SAUDI_ARABIA") == "SAR"


def test_get_region_currency_mixed_case_uae():
    """UAE in any casing maps to AED."""
    assert get_region_currency("UAE") == "AED"
    assert get_region_currency("Uae") == "AED"
    assert get_region_currency("uae") == "AED"


def test_get_region_currency_none_returns_bhd():
    """None defaults to BHD."""
    assert get_region_currency(None) == "BHD"


def test_get_region_currency_empty_returns_bhd():
    """Empty string defaults to BHD."""
    assert get_region_currency("") == "BHD"


def test_get_region_currency_unknown_returns_bhd():
    """Unknown region defaults to BHD (Bahrain-first behaviour per docstring)."""
    assert get_region_currency("antarctica") == "BHD"
    assert get_region_currency("usa") == "BHD"
    assert get_region_currency("france") == "BHD"


def test_region_to_currency_table_completeness():
    """All 6 GCC region codes must be present in REGION_TO_CURRENCY."""
    expected_regions = {"bahrain", "saudi_arabia", "uae", "kuwait", "qatar", "oman"}
    actual_regions = set(REGION_TO_CURRENCY.keys())
    missing = expected_regions - actual_regions
    assert not missing, f"REGION_TO_CURRENCY missing GCC regions: {missing}"


def test_region_to_currency_values_match_fallback_rates():
    """Every currency in REGION_TO_CURRENCY must also exist in FALLBACK_RATES
    (else region-aware conversion will silently fall back to 1.0)."""
    for region, currency in REGION_TO_CURRENCY.items():
        assert currency in FALLBACK_RATES, \
            f"REGION_TO_CURRENCY[{region}]={currency} not in FALLBACK_RATES"


# ---------------------------------------------------------------
# FALLBACK_RATES — round-trip and plausibility
# ---------------------------------------------------------------

def test_fallback_rate_same_currency_is_one():
    """USD->USD via _fallback_rate must be 1.0 (table self-consistency)."""
    for currency in ["USD", "EUR", "SGD", "BHD", "SAR"]:
        assert _fallback_rate(currency, currency) == pytest.approx(1.0, rel=0.001), \
            f"{currency}->{currency} should be 1.0"


def test_fallback_rate_sgd_to_bhd_plausible():
    """SGD->BHD rate must sit in 0.25..0.32 (1 SGD ~= 0.28 BHD as of 2026-05)."""
    rate = _fallback_rate("SGD", "BHD")
    assert 0.25 <= rate <= 0.32, f"SGD->BHD rate {rate} outside plausible band"


def test_fallback_rate_jpy_to_bhd_plausible():
    """JPY->BHD rate must sit in 0.002..0.004."""
    rate = _fallback_rate("JPY", "BHD")
    assert 0.002 <= rate <= 0.004, f"JPY->BHD rate {rate} outside plausible band"


def test_fallback_rate_cny_to_bhd_plausible():
    """CNY->BHD rate must sit in 0.04..0.07 (1 CNY ~= 0.05 BHD as of 2026-05)."""
    rate = _fallback_rate("CNY", "BHD")
    assert 0.04 <= rate <= 0.07, f"CNY->BHD rate {rate} outside plausible band"


def test_fallback_rate_inr_to_bhd_plausible():
    """INR->BHD rate must sit in 0.003..0.006 (1 INR ~= 0.0045 BHD as of 2026-05)."""
    rate = _fallback_rate("INR", "BHD")
    assert 0.003 <= rate <= 0.006, f"INR->BHD rate {rate} outside plausible band"

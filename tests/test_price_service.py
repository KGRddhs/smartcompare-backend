"""Bucket A bug 4 — region-aware conversion + strict-fail on missing rate."""
import pytest

from app.services.exchange_rate_service import get_region_currency, REGION_TO_CURRENCY


def test_region_to_currency_covers_all_gcc_regions():
    """All 6 GCC regions must map to their native currency."""
    expected = {
        "bahrain": "BHD",
        "saudi_arabia": "SAR",
        "uae": "AED",
        "kuwait": "KWD",
        "qatar": "QAR",
        "oman": "OMR",
    }
    for region, currency in expected.items():
        assert REGION_TO_CURRENCY[region] == currency, \
            f"{region} should map to {currency}, got {REGION_TO_CURRENCY.get(region)}"


def test_get_region_currency_defaults_to_bhd_on_unknown():
    """Unknown region falls back to BHD (Bahrain-first behaviour)."""
    assert get_region_currency("antarctica") == "BHD"
    assert get_region_currency(None) == "BHD"
    assert get_region_currency("") == "BHD"


def test_get_region_currency_returns_native_for_known():
    """Known region returns the GCC-native currency."""
    assert get_region_currency("bahrain") == "BHD"
    assert get_region_currency("uae") == "AED"
    assert get_region_currency("saudi_arabia") == "SAR"


from app.services.price_service import _convert_to_bhd


def test_convert_to_bhd_unknown_currency_logs_warning(caplog):
    """Unknown currency must log a warning, not silently return same number."""
    import logging
    caplog.set_level(logging.WARNING)

    # XYZ is not in any rate table — should fall back to amount BUT log warning
    result = _convert_to_bhd(1000.0, "XYZ")

    # The existing behaviour returns 1.0 silently; new behaviour must warn
    warned = any("XYZ" in record.message and "no rate" in record.message.lower()
                 for record in caplog.records)
    assert warned, f"Expected WARNING about missing XYZ rate. Records: {[r.message for r in caplog.records]}"


def test_convert_to_bhd_sgd_converts_correctly():
    """SGD must convert to ~28% of input value when going to BHD."""
    result = _convert_to_bhd(1000.0, "SGD")
    assert 270 <= result <= 295, \
        f"SGD 1000 -> BHD should be ~282, got {result}"


# Extra coverage (Bucket A bug 4 follow-up) ----------------------------------

def test_convert_to_bhd_empty_currency_returns_amount_unchanged():
    """Empty currency string should be the same as no currency: amount unchanged, no log."""
    result = _convert_to_bhd(100.0, "")
    assert result == 100.0


def test_convert_to_bhd_lowercase_currency_normalises():
    """Lowercase currency input must be uppercased before lookup."""
    result = _convert_to_bhd(1000.0, "sgd")
    assert 270 <= result <= 295, f"sgd (lowercase) should still convert; got {result}"


def test_convert_to_bhd_mixed_case_currency_normalises():
    """Mixed-case currency input must be uppercased before lookup."""
    result = _convert_to_bhd(100.0, "uSd")
    assert 37.0 <= result <= 38.0, f"uSd (mixed case) should still convert; got {result}"


def test_convert_to_bhd_bhd_passes_through_unchanged():
    """BHD -> BHD is identity (rate = 1.0); should preserve amount."""
    assert _convert_to_bhd(123.45, "BHD") == 123.45


def test_get_region_currency_uppercase_region_normalised():
    """region.lower() ensures e.g. 'BAHRAIN' still maps to BHD."""
    assert get_region_currency("BAHRAIN") == "BHD"
    assert get_region_currency("Uae") == "AED"

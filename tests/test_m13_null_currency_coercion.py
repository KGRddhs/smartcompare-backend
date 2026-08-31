"""M13-44 — a null (JSON None) original_currency must not crash the tier cascade.

Pre-fix, ``_convert_gpt_price_currency`` and the Tier-2 label branch both did
``price.get("original_currency", "").upper()`` — but when the key is PRESENT with
value None, ``.get(key, "")`` returns None and ``None.upper()`` raised out of the
tier cascade, losing the price for the request (and re-losing it on every retry,
since the raise precedes any cache write). Pure defect fix, unflagged: a null
original_currency must degrade gracefully (Tier 3), never raise.
"""
from app.services.price_service import (
    _convert_gpt_price_currency,
    sanitize_gpt_price,
)


def test_m13_44_convert_gpt_price_null_currency_degrades_not_raises():
    """A Tier-2 dict with original_currency=None + an amount degrades (returns
    False = no conversion / fall to Tier 3), never raises."""
    price = {"amount": 100.0, "original_currency": None, "currency": None}
    # Must NOT raise AttributeError: 'NoneType' object has no attribute 'upper'.
    assert _convert_gpt_price_currency(price, "BHD") is False
    # The amount is untouched — the caller degrades it, not this function.
    assert price["amount"] == 100.0


def test_m13_44_convert_gpt_price_missing_currency_key_still_ok():
    """The already-working absent-key path stays False (regression guard)."""
    assert _convert_gpt_price_currency({"amount": 100.0}, "BHD") is False


def test_m13_44_sanitize_coerces_null_original_currency():
    """sanitize_gpt_price fixes a null/non-string original_currency ONCE at the
    boundary so no downstream .upper() can crash."""
    p = {"amount": 50.0, "original_currency": None, "retailer": "noon", "url": "x"}
    sanitize_gpt_price(p)
    assert isinstance(p["original_currency"], str)
    assert p["original_currency"] == ""


def test_m13_44_sanitize_leaves_real_currency_untouched():
    """A real currency string is left exactly as-is."""
    p = {"amount": 50.0, "original_currency": "AED", "retailer": "noon", "url": "x"}
    sanitize_gpt_price(p)
    assert p["original_currency"] == "AED"

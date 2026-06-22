"""WS-1 EL-2 — device-class floor precision (G4).

The high-value flagship floor (is_implausible_high_value_price) must protect a
genuine phone/laptop/console/GPU from an accessory-priced wrong-scrape (e.g. a
"Galaxy S24" CASE at 11.9 BHD) WITHOUT flooring genuine cheap accessories of the
same brand (a "Samsung 25W charger" at 8 BHD is real).

The split:
  - HIGH_VALUE_DEVICE_TOKENS — self-identifying device names (iphone, macbook,
    rtx, playstation, ...) → always high-value.
  - HIGH_VALUE_BRANDS — bare brands (samsung, galaxy, xiaomi, ...) → high-value
    ONLY with a co-occurring device noun OR a confirmed flagship phone-model
    (_PHONE_MODEL_RE).
  - HIGH_VALUE_DEVICE_NOUNS — device-class nouns; EXCLUDES watch/buds/band/fit.

G4 invariant: bare brands (samsung/galaxy/xiaomi/huawei/oneplus/nvidia/amd) must
NOT trip the flagship floor without a device-class signal.
"""
import pytest

from app.services.price_service import (
    is_high_value_query,
    is_implausible_high_value_price,
    _PHONE_MODEL_RE,
)


# --- is_high_value_query device-class precision ---

@pytest.mark.parametrize("query,expected", [
    # Bare brand + accessory noun → NOT high-value (the EL-2 win).
    ("Samsung 25W charger", False),
    ("Samsung Galaxy Buds2 Pro", False),
    ("Samsung Galaxy Watch 6", False),
    ("Xiaomi Mi Band 8", False),
    # Bare brand + device noun OR flagship model → high-value.
    ("Samsung Galaxy S24", True),          # flagship model via _PHONE_MODEL_RE
    ("Samsung Galaxy S24 phone", True),    # device noun
    ("Xiaomi 14 Ultra smartphone", True),  # device noun
    # Self-identifying device tokens → always high-value.
    ("iPhone 15", True),
    ("Apple iPhone 16 Pro", True),
    ("MacBook Air M3", True),
    ("NVIDIA RTX 4090", True),             # device-token path (rtx)
    ("PlayStation 5", True),
    # Documents the non-covered gap (no brand/token/noun match).
    ("Sony WH-1000XM5 headphones", False),
])
def test_is_high_value_query_device_class(query, expected):
    assert is_high_value_query(query) is expected


def test_bare_brand_alone_not_high_value():
    """A bare brand with no device noun and no flagship model is NOT high-value."""
    assert is_high_value_query("Samsung") is False
    assert is_high_value_query("Xiaomi") is False
    assert is_high_value_query("Huawei") is False


# --- _PHONE_MODEL_RE direction pressure-test ---

@pytest.mark.parametrize("text", [
    "Samsung Galaxy S24",
    "Galaxy S24 Ultra",
    "Galaxy Note 20",
    "Xiaomi 14",
])
def test_phone_model_regex_matches_flagship_models(text):
    assert _PHONE_MODEL_RE.search(text.lower()) is not None


@pytest.mark.parametrize("text", [
    "Xiaomi Mi Band 8",
    "Samsung Galaxy Watch 6",
    "Samsung Galaxy Buds2 Pro",
    "Galaxy Fit 3",
    "Samsung 25W charger",
])
def test_phone_model_regex_excludes_accessories(text):
    """The flagship phone-model regex must NOT match accessory model contexts
    (band/watch/buds/fit), else they would trip the floor."""
    assert _PHONE_MODEL_RE.search(text.lower()) is None


# --- is_implausible_high_value_price floor behavior ---

def test_charger_not_floored():
    """A genuine 8-BHD Samsung charger is NOT a high-value product → not floored."""
    assert is_implausible_high_value_price("Samsung 25W charger", 8.0) is False


def test_s24_floored():
    """The load-bearing case: an 11.9-BHD 'Galaxy S24' hit is an accessory leak —
    the floor protects the genuine flagship from a case-scrape."""
    assert is_implausible_high_value_price("Samsung Galaxy S24", 11.9) is True


def test_iphone_floored_under_floor():
    assert is_implausible_high_value_price("iPhone 15", 12.0) is True


def test_high_value_genuine_price_not_floored():
    assert is_implausible_high_value_price("Samsung Galaxy S24", 280.0) is False


def test_floor_false_on_missing_amount():
    assert is_implausible_high_value_price("Samsung Galaxy S24", None) is False
    assert is_implausible_high_value_price("Samsung Galaxy S24", 0.0) is False


def test_watch_not_floored():
    """A Galaxy Watch is an accessory class → never floored even at a low price."""
    assert is_implausible_high_value_price("Samsung Galaxy Watch 6", 90.0) is False

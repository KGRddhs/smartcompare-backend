"""M26 #100 — per-field spec normalization behind ENABLE_SPEC_FIELD_NORM.

`_score_specs` sums raw cross-unit magnitudes (a 5000 mAh battery + 128 GB
storage + 6.1 in display added as bare numbers), so whichever field carries the
biggest number dominates the spec dimension and a product wins on NOTATION
(mAh vs hours) rather than merit; the same divide-by-populated-fields mean
makes THINNER extraction win (PO-rubric-01 + PO-rubric-02, one root cause).

Fix (flag ON): each schema field contributes a unit-free 0..1 score relative
to the comparison pair (pair min-max via `_magnitude_aware_ratio`; a >=10x
same-field magnitude gap is a unit/notation artifact and reads as a tie; a
field present on one side only is a genuine 1.0-vs-0.0 advantage), the product
score is the mean over the UNION of populated fields (missing fields dilute),
and the coverage discount uses TOTAL schema fields as its basis:
`mean * (0.5 + scored_fields / total_fields)`.

Flag OFF (default) must stay byte-identical to base b073918 — pinned by the
literal golden captured at that commit (test_flag_off_matches_recorded_golden).
"""
import json
import os

import pytest

from app.services import scoring_service
from app.services.scoring_service import (
    CATEGORY_DIMENSIONS,
    ScoringService,
)
from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS

GOLDEN_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "spec_field_norm_flag_off_golden.json"
)

# The env knobs that can move compute_scores output — pinned to their prod
# defaults (unset) so goldens and assertions are environment-independent.
_SCORING_ENV_KNOBS = (
    "ENABLE_SPEC_FIELD_NORM",
    "ENABLE_MISSING_DIM_RENORM",
    "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
    "DISABLE_DIM_NORM_DAMPENING",
    "WINNER_DIM_GAP_TOLERANCE",
    "WINNER_VALUE_WEIGHT_SCALE",
    "WINNER_PRICE_AUTHORITY_POINTS",
)


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def clean_env(monkeypatch):
    for name in _SCORING_ENV_KNOBS:
        monkeypatch.delenv(name, raising=False)
    # _bundle_c_scoring_enabled caches into a module global — reset it so the
    # cleared env is what's actually read.
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


@pytest.fixture
def flag_on(clean_env, monkeypatch):
    monkeypatch.setenv("ENABLE_SPEC_FIELD_NORM", "true")
    yield


@pytest.fixture
def flag_off(clean_env):
    # clean_env already deleted ENABLE_SPEC_FIELD_NORM — default OFF.
    yield


# The 6 shared electronics fields (battery is supplied per-product → 7 total).
_COMMON_ELECTRONICS_FIELDS = {
    "display": "6.1 in OLED",
    "processor": "Octa-core 3.2 GHz",
    "ram": "8 GB",
    "storage": "256 GB",
    "rear_camera": "48 MP",
    "front_camera": "12 MP",
}


def _make_phone(name, battery, *, rating=4.5, review_count=1000, specs=None, price=300):
    if specs is None:
        specs = dict(_COMMON_ELECTRONICS_FIELDS)
        specs["battery"] = battery
    return {
        "name": name,
        "category": "electronics",
        "specs": specs,
        "rating": rating,
        "review_count": review_count,
        "price": {"amount": price, "currency": "BHD", "source_method": "local_bhd"},
    }


def _spec_raw_pair(service, products):
    """Run the raw + normalize pipeline and return the (possibly pair-relative
    recomputed) spec_raw values off raw_scores."""
    raw = [service._compute_raw_scores(p, "electronics") for p in products]
    service._normalize_scores(raw, products, "electronics")
    return raw


# ---------------------------------------------------------------------------
# Red-first pins (fail at base b073918 with the flag ON)
# ---------------------------------------------------------------------------


def test_battery_notation_does_not_decide_winner(service, flag_on):
    """Two electronics products identical except battery NOTATION
    ("5000mAh" vs "Up to 29 hours video playback") must land with comparable
    spec_raw. Fails at base: 760.9 vs 50.7 (the raw mAh magnitude is summed)."""
    p_mah = _make_phone("Phone M", "5000mAh")
    p_hours = _make_phone("Phone H", "Up to 29 hours video playback")
    raw = _spec_raw_pair(service, [p_mah, p_hours])
    a, b = raw[0]["spec_raw"], raw[1]["spec_raw"]
    assert a is not None and b is not None
    assert abs(a - b) < 5, (
        f"battery notation must not decide the spec dimension: spec_raw {a} vs {b}"
    )


def test_lower_rating_does_not_win_on_notation(service, flag_on):
    """Same notation pair; the mAh product is rated LOWER (4.5, 800 reviews)
    than the hours product (4.7, 1500). The hours product must win overall.
    Fails at base: winner_index == 0 (the 5000 raw magnitude drowns the
    review + popularity gap)."""
    p_mah = _make_phone("Phone M", "5000mAh", rating=4.5, review_count=800)
    p_hours = _make_phone(
        "Phone H", "Up to 29 hours video playback", rating=4.7, review_count=1500
    )
    res = service.compute_scores([p_mah, p_hours])
    assert res["winner_index"] == 1, (
        f"the better-rated product must win when specs differ only by notation; "
        f"got winner_index={res['winner_index']} "
        f"overalls={[res['scores'][f'product_{i}']['overall'] for i in range(2)]}"
    )


def test_sparse_capture_cannot_outscore_full_capture(service, flag_on):
    """A 1-field capture of the same phone must not outscore the full 7-field
    capture. Fails at base: sparse spec_raw 2954.5 (5000/1 * 0.59) beats the
    full capture's 760.9, and the sparse product wins overall."""
    sparse = _make_phone("Phone M sparse", None, specs={"battery": "5000mAh"})
    full = _make_phone("Phone M full", "5000mAh")
    raw = _spec_raw_pair(service, [sparse, full])
    assert raw[1]["spec_raw"] > raw[0]["spec_raw"], (
        f"full capture must outscore sparse capture of the same product: "
        f"sparse={raw[0]['spec_raw']} full={raw[1]['spec_raw']}"
    )
    res = service.compute_scores([sparse, full])
    assert res["winner_index"] == 1, (
        f"thinner extraction must not win; got winner_index={res['winner_index']}"
    )


def test_coverage_penalty_divides_by_total_fields(service, flag_on):
    """1-of-11 vs 11-of-11 coverage with identical values on the shared field:
    the 1-of-11 product's spec_raw must be strictly lower (the discount's
    divisor basis is TOTAL schema fields, and missing fields dilute the mean).
    Fails at base: 2954.5 vs 456.5 — the sparse product is ~6.5x higher."""
    sparse = _make_phone("Sparse", None, specs={"battery": "5000mAh"})
    full = _make_phone(
        "Full",
        None,
        specs={
            "display": "6.1 in",
            "processor": "A17 Pro",
            "ram": "8 GB",
            "storage": "128 GB",
            "battery": "5000mAh",
            "rear_camera": "48 MP",
            "front_camera": "12 MP",
            "os": "iOS 18",
            "connectivity": "5G Wi-Fi 6E",
            "weight": "180 g",
            "water_resistance": "IP68",
        },
    )
    raw = _spec_raw_pair(service, [sparse, full])
    assert raw[0]["spec_raw"] < raw[1]["spec_raw"], (
        f"1-of-11 coverage must score strictly below 11-of-11: "
        f"sparse={raw[0]['spec_raw']} full={raw[1]['spec_raw']}"
    )


def test_field_present_in_one_product_only(service, flag_on):
    """A field captured on one side only is a genuine advantage: no exception,
    and the holder's per-field contribution strictly exceeds the other side's
    (which is 0.0 for that field)."""
    a = _make_phone("A", None, specs={"display": "120Hz OLED", "ram": "8 GB"})
    b = _make_phone("B", None, specs={"ram": "8 GB"})
    raw = _spec_raw_pair(service, [a, b])
    ratios_a = raw[0]["_spec_field_ratios"]
    ratios_b = raw[1]["_spec_field_ratios"]
    assert ratios_a["display"] > ratios_b.get("display", 0.0), (
        f"the display holder must out-contribute the side that lacks it: "
        f"{ratios_a} vs {ratios_b}"
    )


def test_product_losing_every_comparable_field_cannot_win_dimension(service, flag_on):
    """Task pin: a product that loses (or at best ties, on a pure notation
    artifact) EVERY field must not win the spec dimension by carrying one
    huge-magnitude field. A ties battery on notation (5000 mAh vs 29 hours,
    a >=10x same-field unit artifact) and loses ram + storage outright; B must
    win spec_raw. Fails at base: A's mean is 1689.3 vs B's 97.7."""
    a = _make_phone(
        "A", None, specs={"battery": "5000mAh", "ram": "4 GB", "storage": "64 GB"}
    )
    b = _make_phone(
        "B",
        None,
        specs={
            "battery": "Up to 29 hours video playback",
            "ram": "8 GB",
            "storage": "256 GB",
        },
    )
    raw = _spec_raw_pair(service, [a, b])
    assert raw[1]["spec_raw"] > raw[0]["spec_raw"], (
        f"the product winning every comparable field must win the dimension: "
        f"A={raw[0]['spec_raw']} B={raw[1]['spec_raw']}"
    )


# ---------------------------------------------------------------------------
# Green-from-day-one guards
# ---------------------------------------------------------------------------


def test_zero_scored_fields_still_returns_none(service, clean_env, monkeypatch):
    """B0-A v2.1 guard: zero coverage returns None (never 0.0) with the flag
    both ON and OFF."""
    for flag_value in ("true", ""):
        if flag_value:
            monkeypatch.setenv("ENABLE_SPEC_FIELD_NORM", flag_value)
        else:
            monkeypatch.delenv("ENABLE_SPEC_FIELD_NORM", raising=False)
        assert service._score_specs({}, "electronics") is None
        assert service._score_specs({"battery": "N/A"}, "electronics") is None


def test_identical_specs_still_collapse_to_tie(service, flag_on):
    """Identical spec dicts must still hit the array-level tied-spec collapse:
    equal spec_raw on both sides and `_spec_missing` set on both raw entries
    after _normalize_scores (the B0-A v2.2 phantom-tie guard)."""
    specs = dict(_COMMON_ELECTRONICS_FIELDS, battery="4500 mAh")
    a = _make_phone("A", None, specs=dict(specs))
    b = _make_phone("B", None, specs=dict(specs))
    raw = _spec_raw_pair(service, [a, b])
    assert raw[0]["spec_raw"] == raw[1]["spec_raw"]
    assert raw[0].get("_spec_missing") is True
    assert raw[1].get("_spec_missing") is True


# ---------------------------------------------------------------------------
# Flag-OFF byte-identity golden (captured at base b073918)
# ---------------------------------------------------------------------------


def golden_fixture_products(category):
    """Deterministic per-category pair: A = full coverage with varied
    magnitudes, B = partial coverage carrying one huge-magnitude field (so a
    flag leak would move BOTH the concentration and the coverage-penalty
    paths)."""
    schema_key = category if category in CATEGORY_SPEC_SCHEMAS else "other"
    schema = CATEGORY_SPEC_SCHEMAS[schema_key]
    specs_a = {f: f"{(i + 2) * 3} units" for i, f in enumerate(schema)}
    half = schema[: len(schema) // 2 + 1]
    specs_b = {f: f"{(i + 1) * 5} units" for i, f in enumerate(half)}
    specs_b[half[0]] = "9000 mega"
    product_a = {
        "name": f"{category} A",
        "category": category,
        "specs": specs_a,
        "rating": 4.2,
        "review_count": 320,
        "price": {"amount": 120, "currency": "BHD", "source_method": "local_bhd"},
        "fact_check": {"specs_verified": 3, "specs_likely": 1},
    }
    product_b = {
        "name": f"{category} B",
        "category": category,
        "specs": specs_b,
        "rating": 3.1,
        "review_count": 45,
        "price": {"amount": 95, "currency": "BHD", "source_method": "local_bhd"},
        "fact_check": {"specs_verified": 1, "specs_flagged": 2},
    }
    return [product_a, product_b]


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS.keys()))
def test_flag_off_matches_recorded_golden(service, flag_off, category):
    """With ENABLE_SPEC_FIELD_NORM unset, compute_scores output must equal the
    literal golden captured at base b073918 — the mandatory flag-OFF
    byte-identity equivalent for the scoring surface."""
    with open(GOLDEN_PATH, encoding="utf-8") as fh:
        golden = json.load(fh)
    result = service.compute_scores(golden_fixture_products(category))
    assert json.loads(json.dumps(result)) == golden[category], (
        f"flag-OFF scoring output for {category!r} deviates from the base "
        f"b073918 golden"
    )

"""M20 #100 — normalize spec fields per-field before aggregating.

`_score_specs` sums RAW magnitudes across incompatible units (mAh + GB + MP +
counts) into one number, so spec NOTATION decides the winner instead of product
quality: an Apple-style `battery: "Up to 29 hours video playback"` scores 51.0
while a Samsung-style `battery: "5000mAh"` scores 761.1 on an otherwise
IDENTICAL phone (14.9x). The same raw-magnitude sum inverts the sparse-coverage
penalty: `{"battery": "5000mAh"}` alone scores `(5000/1) * (0.5 + 1/11)` =
2954.5, so a 1-of-11 capture BEATS a 7-of-11 capture of the same product --
exactly what the penalty exists to punish. M18 findings PO-rubric-01 and
PO-rubric-02, one root cause.

The fix (issue #100): each schema field contributes a unit-free 0-1 score
RELATIVE TO THE COMPARISON PAIR, the product score is the mean of those, and the
coverage discount `mean * (0.5 + scored_fields / total_fields)` is applied with
`total_fields` as the divisor basis so missing fields DILUTE instead of
concentrating. Gated behind `ENABLE_SPEC_FIELD_NORM` (default OFF).

Pair-relative min-max is deliberate: a `mAh <-> hours` conversion table would
need per-category per-field curation across 9 categories and would rot as new
fields land. Values expressed in DIFFERENT units are therefore treated as
different measurements (`battery@mah` vs `battery@hour`), which is what makes
the notation pair symmetric instead of a 14.9x landslide.
"""
import json
import os

import pytest

from app.services.scoring_service import (
    ScoringService,
    CATEGORY_DIMENSIONS,
    MISSING_SCORE,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GOLDEN = os.path.join(
    _REPO_ROOT, "tests", "fixtures", "spec_field_norm_flag_off_golden.json"
)

# The real 11-field electronics schema
# (app/services/extraction_service.py:CATEGORY_SPEC_SCHEMAS["electronics"]),
# 7 of them populated -- the shape the M18 review reproduced on.
_PHONE_7 = {
    "display": "6.7-inch OLED",
    "processor": "Snapdragon 8 Gen 3",
    "ram": "12GB",
    "storage": "256GB",
    "battery": "5000mAh",
    "rear_camera": "50MP",
    "front_camera": "12MP",
}

# Same phone, same 6 other fields, battery expressed in HOURS instead of mAh.
_PHONE_7_HOURS = dict(_PHONE_7)
_PHONE_7_HOURS["battery"] = "Up to 29 hours video playback"

# All 11 electronics schema fields populated.
_PHONE_11 = dict(_PHONE_7)
_PHONE_11.update({
    "os": "Android 14",
    "connectivity": "5G, Wi-Fi 7",
    "weight": "199 g",
    "water_resistance": "IP68",
})


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def norm_on(monkeypatch):
    """The flag reader is LIVE (env read per call, mirroring
    response_builder._gpt_winner_lever_enabled), so setenv alone is enough --
    there is no module-level cache to reset (unlike `_BUNDLE_C_SCORING_FLAG`)."""
    monkeypatch.setenv("ENABLE_SPEC_FIELD_NORM", "true")
    yield


@pytest.fixture
def norm_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SPEC_FIELD_NORM", raising=False)
    yield


@pytest.fixture(autouse=True)
def _isolate_sibling_flags(monkeypatch):
    """#101's flag ships in the same wave and is default-OFF; pin it OFF so this
    file measures ONE lever."""
    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    yield


def _prod(name, *, specs, rating=4.6, review_count=1000, price=300,
          category="electronics"):
    """Mirrors the `_prod()` helper shape in
    tests/test_missing_score_collision_v2.py:21."""
    return {
        "brand": "House", "name": name, "category": category,
        "specs": dict(specs),
        "rating": rating, "review_count": review_count,
        "price": {"amount": price, "currency": "BHD", "source_method": "local_bhd"},
        "fact_check": {"specs_verified": 3},
    }


def _spec_raws(service, products, category="electronics"):
    """spec_raw as the pipeline actually produces it: per-product from
    `_compute_raw_scores`, then through `_normalize_scores` (which is where the
    PAIR is visible and where #100 does the pair-relative step). The raw_scores
    dicts are mutated in place, so this reads the post-normalization value."""
    raw = [service._compute_raw_scores(p, category) for p in products]
    service._normalize_scores(raw, products, category)
    return [r.get("spec_raw") for r in raw], raw


# --- 1. notation must not decide the spec score ------------------------------

def test_battery_notation_does_not_decide_winner(service, norm_on):
    """mAh vs hours on an otherwise identical phone must not open a 14.9x gap."""
    products = [
        _prod("Phone M", specs=_PHONE_7),
        _prod("Phone H", specs=_PHONE_7_HOURS),
    ]
    spec_raws, _ = _spec_raws(service, products)
    a, b = spec_raws
    assert a is not None and b is not None
    assert abs(a - b) < 5, (
        f"battery NOTATION (mAh vs hours) still decides the spec score: "
        f"spec_raw={a} vs {b}"
    )


def test_lower_rating_does_not_win_on_notation(service, norm_on):
    """The mAh phone is rated LOWER (4.5/800) than the hours phone (4.7/1500) at
    the same price; once notation stops dominating, the better-rated phone wins."""
    products = [
        _prod("Phone M", specs=_PHONE_7, rating=4.5, review_count=800),
        _prod("Phone H", specs=_PHONE_7_HOURS, rating=4.7, review_count=1500),
    ]
    result = service.compute_scores(products)
    assert result["winner_index"] == 1, (
        "the lower-rated phone still wins on battery notation alone; overalls="
        + str([result["scores"][f"product_{i}"]["overall"] for i in range(2)])
    )


# --- 2. sparse capture must DILUTE, never concentrate ------------------------

def test_sparse_capture_cannot_outscore_full_capture(service, norm_on):
    """PO-rubric-02: a 1-of-11 capture of the SAME phone must not beat the
    7-of-11 capture. Today `(5000/1) * (0.5 + 1/11)` = 2954.5 beats 761.1."""
    products = [
        _prod("Phone sparse", specs={"battery": "5000mAh"}),
        _prod("Phone full", specs=_PHONE_7),
    ]
    spec_raws, _ = _spec_raws(service, products)
    a, b = spec_raws
    assert b > a, (
        f"thinner extraction still outscores fuller extraction: "
        f"sparse spec_raw={a} vs full spec_raw={b}"
    )
    result = service.compute_scores(products)
    assert result["winner_index"] == 1, (
        "the 1-of-11 capture still wins; overalls="
        + str([result["scores"][f"product_{i}"]["overall"] for i in range(2)])
    )


def test_coverage_penalty_divides_by_total_fields(service, norm_on):
    """The coverage discount must use `total_fields` as the divisor basis, so a
    1-of-11 product scores strictly lower than an 11-of-11 product whose shared
    field values are identical."""
    products = [
        _prod("One field", specs={"battery": "5000mAh"}),
        _prod("Eleven fields", specs=_PHONE_11),
    ]
    spec_raws, _ = _spec_raws(service, products)
    sparse, full = spec_raws
    assert sparse < full, (
        f"1-of-11 coverage is not diluted relative to 11-of-11: "
        f"{sparse} vs {full}"
    )


# --- 3. invariants that must hold with the flag in EITHER position -----------

@pytest.mark.parametrize("flag", ["on", "off"])
@pytest.mark.parametrize("specs", [{}, {"battery": "N/A"}])
def test_zero_scored_fields_still_returns_none(service, monkeypatch, flag, specs):
    """B0-A v2.1 phantom-tie guard: zero scored fields -> None, never 0.0."""
    if flag == "on":
        monkeypatch.setenv("ENABLE_SPEC_FIELD_NORM", "true")
    else:
        monkeypatch.delenv("ENABLE_SPEC_FIELD_NORM", raising=False)
    assert service._score_specs(specs, "electronics") is None


def test_field_present_in_one_product_only(service, norm_on):
    """A field only ONE product captured is a genuine advantage for that product
    (1.0 vs 0.0), never a penalty. Today the sparse product wins instead,
    because a smaller `scored_fields` divisor CONCENTRATES its raw sum."""
    products = [
        _prod("Has display", specs={"display": "120Hz OLED", "ram": "8GB"}),
        _prod("No display", specs={"ram": "8GB"}),
    ]
    spec_raws, raw = _spec_raws(service, products)
    a, b = spec_raws
    assert a > b, (
        f"capturing an extra field still LOWERS the score: {a} vs {b}"
    )
    # And at the per-field level the advantage is attributable to `display`.
    maps = [rs["_spec_fields"][0] for rs in raw]
    ratios = service._spec_field_pair_ratios(maps)
    assert ratios[0]["display"] > ratios[1]["display"], (
        f"per-field contribution for `display`: {ratios[0].get('display')} vs "
        f"{ratios[1].get('display')}"
    )


def test_identical_specs_still_collapse_to_tie(service, norm_on):
    """Both products identical on every field -> every ratio 0.5 -> identical
    spec_raw -> the existing array-level tied-spec collapse still fires."""
    products = [
        _prod("Twin A", specs=_PHONE_7),
        _prod("Twin B", specs=_PHONE_7),
    ]
    raw = [service._compute_raw_scores(p, "electronics") for p in products]
    service._normalize_scores(raw, products, "electronics")
    assert raw[0]["spec_raw"] == raw[1]["spec_raw"]
    assert raw[0]["_spec_missing"] is True
    assert raw[1]["_spec_missing"] is True


# --- 4. flag-OFF golden ------------------------------------------------------

_GOLDEN_SPECS_A = {
    "display": "6.7-inch OLED", "processor": "Snapdragon 8 Gen 3",
    "ram": "12GB", "storage": "256GB", "battery": "5000mAh",
    "rear_camera": "50MP", "front_camera": "12MP",
    "count": "60 capsules", "size": "500 g", "nutrition_protein": "20 g",
    "nutrition_calories": "150 kcal", "dosage": "1000 mg",
    "serving_size": "2 capsules",
    "spf": "50", "volume": "100 ml", "shade_range": "40 shades",
    "longevity": "8 hours", "sillage": "moderate",
    "concentration": "eau de parfum",
    "material": "100% cotton", "weight": "180 g", "color": "black",
}
_GOLDEN_SPECS_B = dict(_GOLDEN_SPECS_A)
_GOLDEN_SPECS_B["battery"] = "Up to 29 hours video playback"
_GOLDEN_SPECS_B["ram"] = "8GB"
_GOLDEN_SPECS_B["storage"] = "128GB"
_GOLDEN_SPECS_B["volume"] = "50 ml"
_GOLDEN_SPECS_B["longevity"] = "6 hours"
del _GOLDEN_SPECS_B["color"]
del _GOLDEN_SPECS_B["sillage"]


def _golden_products(category):
    """MUST mirror tests/fixtures/_gen_spec_field_norm_flag_off_golden.py."""
    return [
        {
            "brand": "Alpha", "name": "One", "category": category,
            "specs": dict(_GOLDEN_SPECS_A),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": 4.5, "review_count": 800,
            "fact_check": {"specs_verified": 3},
        },
        {
            "brand": "Beta", "name": "Two", "category": category,
            "specs": dict(_GOLDEN_SPECS_B),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": 4.7, "review_count": 1500,
            "fact_check": {"specs_verified": 3},
        },
    ]


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS))
def test_flag_off_matches_recorded_golden(service, norm_off, category):
    """Flag OFF -> byte-for-byte the pre-change output, across all 9 categories.
    `scripts/verify_flag_byte_identity.py` covers the price-EXTRACTION path only
    and does not apply to this unit; this golden is its mandatory equivalent."""
    with open(_GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    result = service.compute_scores(_golden_products(category))
    captured = {
        "winner_index": result["winner_index"],
        "win_margin": result["win_margin"],
        "scores": result["scores"],
    }
    assert json.loads(json.dumps(captured, sort_keys=True)) == golden[category]


# --- 5. blast-radius guards for the 8 categories the issue does NOT name -----

@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS))
def test_flag_on_is_bounded_and_total_in_every_category(service, norm_on, category):
    """The flag rewrites `spec_raw` for EVERY category, not just electronics.
    Whatever the schema, the result must stay a single Optional[float] inside
    the `mean * (0.5 + coverage)` bound of [0, 1.5] -- no unit magnitude may
    leak back through -- and `overall` must stay a valid 0-100 score."""
    products = _golden_products(category)
    spec_raws, _ = _spec_raws(service, products, category)
    for value in spec_raws:
        assert value is None or 0.0 <= value <= 1.5, (
            f"{category}: spec_raw {value} escaped the normalized band"
        )
    result = service.compute_scores(products)
    for i in range(2):
        assert 0 <= result["scores"][f"product_{i}"]["overall"] <= 100


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS))
def test_flag_on_does_not_reorder_when_specs_are_identical(service, monkeypatch,
                                                           category):
    """No-op case: when the two products carry the SAME specs, the spec signal
    cannot be what separates them, so flipping the flag must not move the
    winner in ANY category."""
    def winner(flag_on):
        if flag_on:
            monkeypatch.setenv("ENABLE_SPEC_FIELD_NORM", "true")
        else:
            monkeypatch.delenv("ENABLE_SPEC_FIELD_NORM", raising=False)
        products = _golden_products(category)
        products[1]["specs"] = dict(products[0]["specs"])
        return ScoringService().compute_scores(products)["winner_index"]

    assert winner(True) == winner(False), (
        f"{category}: the flag reordered the winner on an identical-spec pair"
    )


def test_missing_score_sentinel_unchanged():
    """Guards the constant the collapse paths above compare against."""
    assert MISSING_SCORE == 50

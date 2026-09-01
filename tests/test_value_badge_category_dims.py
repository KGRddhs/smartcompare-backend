"""M20 #102 — value_badge must read the value dim the product's CATEGORY emits.

Both badge call sites in `structured_comparison_service` read the literal
breakdown key `value_score`, which only `electronics` and `other` emit, and
look the price tier up under the bare product name while `price_tiers` is
keyed on `"{brand} {name}"`. Result: a constant `fair_price` for 7 of the 9
categories, and a dead `luxury -> fair_price` branch even for the 2 that work.

These tests pin:
  - `ScoringService.value_dim_for(category)` resolving the value dim from
    `_DIMENSION_SIGNAL_MAP` (one source of truth, no literal table),
  - `compute_scores` carrying `category` and `price_tiers_by_index`,
  - `ScoringService.apply_value_badges` (the single implementation both call
    sites delegate to) producing a VARYING badge for all 9 categories,
  - honest absence: no badge at all when the value dim is missing,
  - flag OFF byte-for-byte behaviour against a golden captured pre-change.

Flag: ENABLE_CATEGORY_VALUE_BADGE, default OFF.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services.scoring_service import CATEGORY_DIMENSIONS, ScoringService


ALL_CATEGORIES = list(CATEGORY_DIMENSIONS)  # the canonical 9
RENAMED_CATEGORIES = [
    "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion",
]

GOLDEN_PATH = (
    Path(__file__).parent / "fixtures" / "value_badge_flag_off_golden.json"
)
SCS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app" / "services" / "structured_comparison_service.py"
)


def _pair(category: str, cheap: float = 12.0, dear: float = 240.0):
    """Two spec-identical products with a wide price gap, so the category's
    value dim diverges hard (cheap -> ~100, dear -> ~30) while every other
    signal stays equal. Brands are non-empty so the tier lookup is exercised."""
    def _one(brand, name, amount):
        return {
            "brand": brand,
            "name": name,
            "category": category,
            "specs": {
                "volume": "100ml",
                "concentration": "eau de parfum",
                "longevity": "8 hours",
                "sillage": "strong",
                "scent_family": "woody",
            },
            "price": {
                "amount": amount, "currency": "BHD",
                "source_method": "page_scrape",
            },
            "rating": 4.6,
            "review_count": 900,
        }
    return [_one("HouseA", "ItemA", cheap), _one("HouseB", "ItemB", dear)]


def _luxury_electronics_pair():
    """Both prices land inside the electronics `luxury` band (800-2000 BHD),
    so product_0 gets value_score 100 AND tier 'luxury' -> the currently-dead
    `luxury -> fair_price` exception must fire."""
    def _one(brand, name, amount):
        return {
            "brand": brand,
            "name": name,
            "category": "electronics",
            "specs": {"processor": "A17", "ram": "8GB", "storage": "256GB"},
            "price": {
                "amount": amount, "currency": "BHD",
                "source_method": "page_scrape",
            },
            "rating": 4.7,
            "review_count": 2000,
        }
    return [_one("BrandLux", "ProLux", 900.0), _one("BrandUltra", "ProUltra", 1900.0)]


@pytest.fixture(autouse=True)
def _flag_off_by_default(monkeypatch):
    """Default OFF everywhere; the ON tests opt in explicitly."""
    monkeypatch.delenv("ENABLE_CATEGORY_VALUE_BADGE", raising=False)


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_CATEGORY_VALUE_BADGE", "true")


def _badges(products, scoring_result):
    svc = ScoringService()
    svc.apply_value_badges(products, scoring_result)
    return [p.get("value_badge") for p in products]


# ---------------------------------------------------------------------------
# 1 — dim resolution (guard)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_value_dim_resolves_for_all_nine_categories(category):
    dim = ScoringService.value_dim_for(category)
    assert dim in CATEGORY_DIMENSIONS[category], (
        f"{category}: resolved value dim {dim!r} is not one of "
        f"{CATEGORY_DIMENSIONS[category]!r}"
    )
    assert ScoringService._DIMENSION_SIGNAL_MAP[category][dim] == "value", (
        f"{category}: {dim!r} is not the 'value'-signal dim"
    )


# ---------------------------------------------------------------------------
# 2 — fragrances (red today: both fair_price)
# ---------------------------------------------------------------------------

def test_fragrance_pair_can_produce_non_fair_price_badge(flag_on):
    svc = ScoringService()
    products = _pair("fragrances")
    scoring_result = svc.compute_scores(products)
    svc.apply_value_badges(products, scoring_result)
    badges = {p.get("value_badge") for p in products}
    assert badges != {"fair_price"}, (
        "fragrances badge is a constant 'fair_price' — the value dim "
        "(wear_value_score) was not read"
    )


# ---------------------------------------------------------------------------
# 3 — the seven renamed categories (red today: all constant)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", RENAMED_CATEGORIES)
def test_badge_varies_across_all_seven_renamed_categories(flag_on, category):
    svc = ScoringService()
    products = _pair(category)
    scoring_result = svc.compute_scores(products)
    svc.apply_value_badges(products, scoring_result)
    badges = [p.get("value_badge") for p in products]
    assert any(b != "fair_price" for b in badges), (
        f"{category}: every badge is 'fair_price' {badges!r} — the category's "
        f"value dim {ScoringService.value_dim_for(category)!r} was not read"
    )


# ---------------------------------------------------------------------------
# 4 — the tier key (red today: always 'mid')
# ---------------------------------------------------------------------------

def test_price_tier_lookup_hits_for_branded_product(flag_on):
    svc = ScoringService()
    products = _luxury_electronics_pair()
    scoring_result = svc.compute_scores(products)

    by_name = scoring_result["price_tiers"]["BrandLux ProLux"]
    assert by_name == "luxury"  # fixture sanity

    by_index = scoring_result.get("price_tiers_by_index", {}).get("product_0")
    assert by_index == by_name, (
        "the index-keyed tier map must agree with the name-keyed one; "
        f"got {by_index!r} vs {by_name!r}"
    )

    # And the badge site must actually consult it: value_score is 100 here, so
    # a resolved 'luxury' tier downgrades great_value -> fair_price. A missed
    # lookup ('mid') would leave 'great_value'.
    svc.apply_value_badges(products, scoring_result)
    assert products[0]["value_badge"] == "fair_price", (
        "price tier did not resolve for a branded product — badge is "
        f"{products[0].get('value_badge')!r}, i.e. the 'mid' default was used"
    )


# ---------------------------------------------------------------------------
# 5 — the dead luxury branch (red today)
# ---------------------------------------------------------------------------

def test_luxury_tier_downgrades_great_value_to_fair_price(flag_on):
    svc = ScoringService()
    products = _luxury_electronics_pair()
    scoring_result = svc.compute_scores(products)
    assert scoring_result["scores"]["product_0"]["breakdown"]["value_score"] >= 75
    svc.apply_value_badges(products, scoring_result)
    assert products[0]["value_badge"] == "fair_price"


# ---------------------------------------------------------------------------
# 6 — honest absence (red today: defaulted fair_price)
# ---------------------------------------------------------------------------

def test_absent_value_dim_emits_no_badge(flag_on):
    products = [
        {"brand": "HouseA", "name": "ItemA", "category": "fragrances"},
        {"brand": "HouseB", "name": "ItemB", "category": "fragrances"},
    ]
    scoring_result = {
        "category": "fragrances",
        "scores": {
            # wear_value_score deliberately absent
            "product_0": {"breakdown": {"character_score": 80.0}},
            "product_1": {"breakdown": {"character_score": 40.0}},
        },
        "price_tiers": {"HouseA ItemA": "mid", "HouseB ItemB": "mid"},
        "price_tiers_by_index": {"product_0": "mid", "product_1": "mid"},
    }
    ScoringService().apply_value_badges(products, scoring_result)
    for p in products:
        assert "value_badge" not in p, (
            "a missing value dim must yield NO badge, not a defaulted claim; "
            f"got {p.get('value_badge')!r}"
        )


# ---------------------------------------------------------------------------
# 7 — the two call sites must not drift (guard)
# ---------------------------------------------------------------------------

def test_sync_and_streaming_sites_agree():
    src = SCS_PATH.read_text(encoding="utf-8")
    blocks = re.findall(
        r"[ \t]*# Compute value badges\n(?:[ \t]*\S.*\n){1,12}", src
    )
    assert len(blocks) == 2, (
        f"expected exactly 2 value-badge call sites, found {len(blocks)}"
    )
    a, b = (re.sub(r"[ \t]+", " ", blk).strip() for blk in blocks)
    assert a == b, (
        "the sync and streaming value-badge call sites have drifted:\n"
        f"--- sync ---\n{a}\n--- streaming ---\n{b}"
    )
    # Both must delegate rather than re-implement the resolution inline.
    for blk in blocks:
        assert "apply_value_badges" in blk, (
            "call site does not delegate to the shared helper:\n" + blk
        )
        assert 'get("value_score", 50)' not in blk, (
            "call site still hardcodes the electronics/other dim key:\n" + blk
        )

    # Functionally: one helper, one result -> identical badges by construction.
    svc = ScoringService()
    products_a = _pair("fragrances")
    products_b = _pair("fragrances")
    scoring_result = svc.compute_scores(_pair("fragrances"))
    svc.apply_value_badges(products_a, scoring_result)
    svc.apply_value_badges(products_b, scoring_result)
    assert [p.get("value_badge") for p in products_a] == [
        p.get("value_badge") for p in products_b
    ]


# ---------------------------------------------------------------------------
# 8 — compute_scores carries the category (red today: key absent)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_compute_scores_result_carries_category(category):
    svc = ScoringService()
    result = svc.compute_scores(_pair(category))
    assert result.get("category") == category, (
        f"compute_scores result does not carry the category: "
        f"{result.get('category')!r} != {category!r}"
    )


def test_compute_scores_unknown_category_canonicalizes_to_other():
    svc = ScoringService()
    result = svc.compute_scores(_pair("quantum-widgets"))
    assert result.get("category") == "other"


# ---------------------------------------------------------------------------
# 9 — flag OFF byte-identity against the pre-change golden (guard)
# ---------------------------------------------------------------------------

def test_flag_off_badges_match_golden():
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    svc = ScoringService()
    actual = {}
    for category in ALL_CATEGORIES:
        products = _pair(category)
        scoring_result = svc.compute_scores(products)
        svc.apply_value_badges(products, scoring_result)
        actual[category] = [p.get("value_badge") for p in products]
    assert actual == golden, (
        "flag-OFF badges changed vs the golden captured before this unit"
    )

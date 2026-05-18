"""Bundle C § 3b + 3e — PRICE_TIERS_BY_CATEGORY 5-tier dict.

Per design § 3a/3b/3e + plan A.5.1: replace the flat PRICE_TIERS map
with PRICE_TIERS_BY_CATEGORY (per-category breakpoints) and a new
_detect_price_tier(price, category, *, comparison_prices=None) that
walks the per-category list.

Categories per spec § 3e:
  electronics: <100 / 100–400 / 400–800 / 800–2000 / 2000+
  supplements: <11 / 11–30 / 30–60 / 60+ (top_tier folds into luxury)
  fashion:     <30 / 30–150 / 150–500 / 500–2000 / 2000+
  fragrances:  <30 / 30–80 / 80–180 / 180–500 / 500+
  skincare:    <11 / 11–40 / 40–100 / 100–300 / 300+
  haircare:    <15 / 15–40 / 40–100 / 100–200 / 200+
  makeup:      <15 / 15–50 / 50–120 / 120–300 / 300+
  grocery:     <5 / 5–15 / 15–50 / 50+ (top_tier folds into luxury)

Existing legacy ranges live as 'other_light' sub-scale per § 3f, so
the back-compat _detect_price_tier(price) one-arg call (existing
tests) keeps returning the same tier strings.
"""
import pytest

from app.services.scoring_service import (
    PRICE_TIERS_BY_CATEGORY,
    _detect_price_tier,
)


# ---------------------------------------------------------------------------
# Per-category breakpoints — spec § 3e table
# ---------------------------------------------------------------------------


def test_dict_contains_all_8_named_categories():
    expected = {"electronics", "supplements", "fashion", "fragrances",
                "skincare", "haircare", "makeup", "grocery"}
    assert expected.issubset(PRICE_TIERS_BY_CATEGORY.keys())


# ---- electronics ----------------------------------------------------------

def test_electronics_budget_under_100():
    assert _detect_price_tier(50, "electronics") == "budget"
    assert _detect_price_tier(99.99, "electronics") == "budget"


def test_electronics_mid_100_to_400():
    assert _detect_price_tier(100, "electronics") == "mid"
    assert _detect_price_tier(300, "electronics") == "mid"


def test_electronics_premium_400_to_800():
    assert _detect_price_tier(400, "electronics") == "premium"
    assert _detect_price_tier(600, "electronics") == "premium"


def test_electronics_luxury_800_to_2000():
    assert _detect_price_tier(800, "electronics") == "luxury"
    assert _detect_price_tier(1500, "electronics") == "luxury"


def test_electronics_top_tier_above_2000():
    assert _detect_price_tier(2000, "electronics") == "top_tier"
    assert _detect_price_tier(5000, "electronics") == "top_tier"


# ---- supplements: top_tier folds into luxury -------------------------------

def test_supplements_4_tiers_with_top_tier_folded():
    assert _detect_price_tier(8, "supplements") == "budget"
    assert _detect_price_tier(20, "supplements") == "mid"
    assert _detect_price_tier(45, "supplements") == "premium"
    assert _detect_price_tier(80, "supplements") == "luxury"
    # 500 BHD supplement still 'luxury' — no top_tier for supplements
    assert _detect_price_tier(500, "supplements") == "luxury"


# ---- fashion ---------------------------------------------------------------

def test_fashion_5_tiers():
    assert _detect_price_tier(20, "fashion") == "budget"
    assert _detect_price_tier(100, "fashion") == "mid"
    assert _detect_price_tier(300, "fashion") == "premium"
    assert _detect_price_tier(1000, "fashion") == "luxury"
    assert _detect_price_tier(3000, "fashion") == "top_tier"


# ---- fragrances ------------------------------------------------------------

def test_fragrances_5_tiers():
    assert _detect_price_tier(20, "fragrances") == "budget"
    assert _detect_price_tier(60, "fragrances") == "mid"
    assert _detect_price_tier(120, "fragrances") == "premium"
    assert _detect_price_tier(300, "fragrances") == "luxury"
    assert _detect_price_tier(800, "fragrances") == "top_tier"


# ---- skincare --------------------------------------------------------------

def test_skincare_5_tiers():
    assert _detect_price_tier(8, "skincare") == "budget"
    assert _detect_price_tier(25, "skincare") == "mid"
    assert _detect_price_tier(60, "skincare") == "premium"
    assert _detect_price_tier(200, "skincare") == "luxury"
    assert _detect_price_tier(500, "skincare") == "top_tier"


# ---- haircare --------------------------------------------------------------

def test_haircare_5_tiers():
    assert _detect_price_tier(10, "haircare") == "budget"
    assert _detect_price_tier(25, "haircare") == "mid"
    assert _detect_price_tier(60, "haircare") == "premium"
    assert _detect_price_tier(150, "haircare") == "luxury"
    assert _detect_price_tier(300, "haircare") == "top_tier"


# ---- makeup ----------------------------------------------------------------

def test_makeup_5_tiers():
    assert _detect_price_tier(10, "makeup") == "budget"
    assert _detect_price_tier(30, "makeup") == "mid"
    assert _detect_price_tier(80, "makeup") == "premium"
    assert _detect_price_tier(200, "makeup") == "luxury"
    assert _detect_price_tier(400, "makeup") == "top_tier"


# ---- grocery: top_tier folds into luxury -----------------------------------

def test_grocery_4_tiers_with_top_tier_folded():
    assert _detect_price_tier(3, "grocery") == "budget"
    assert _detect_price_tier(10, "grocery") == "mid"
    assert _detect_price_tier(30, "grocery") == "premium"
    assert _detect_price_tier(80, "grocery") == "luxury"
    # 500 BHD grocery still 'luxury'
    assert _detect_price_tier(500, "grocery") == "luxury"


# ---------------------------------------------------------------------------
# Back-compat with existing one-arg calls (other category, other_light sub-scale)
# ---------------------------------------------------------------------------


def test_back_compat_one_arg_call_uses_other_light_sub_scale():
    """Existing tests call _detect_price_tier(price) with no category.
    Per § 3f: the default `other_light` sub-scale extends the legacy
    4-tier PRICE_TIERS with a new top_tier 500+ slot. Legacy 3-tier
    boundaries (budget <11, mid <57, premium <189) remain identical so
    scoring on that range stays stable."""
    assert _detect_price_tier(5.0) == "budget"
    assert _detect_price_tier(30.0) == "mid"
    assert _detect_price_tier(100.0) == "premium"
    # Per spec § 3f other_light: 189–500 → luxury, 500+ → top_tier.
    assert _detect_price_tier(300.0) == "luxury"
    assert _detect_price_tier(800.0) == "top_tier"


def test_unknown_category_falls_back_to_other_light():
    """Unknown category strings (e.g., 'electronics_v2') must not crash —
    they fall back to the other_light sub-scale silently."""
    assert _detect_price_tier(5.0, "unknown_category") == "budget"
    assert _detect_price_tier(100.0, "unknown_category") == "premium"

"""Phase 6 Task #7 — fairness audit (F6.1 / F6.2 + edge cases).

The CATEGORY_FAIRNESS machinery (target_pair_value 4-rule plan + tolerance
bands + reconcile) shipped in a prior session and is covered by
test_category_fairness.py / test_fairness_target_rules.py (142 tests). This
module is the Phase-6 AUDIT: it pins the specific prod cases the findings name
so the audit is provably complete —
  F6.1 electronics honor-each (256GB vs 128GB → both shown, not pended),
  F6.2 grocery weight-fairness (Nutella 750g vs Biscoff 400g),
  + the four edge-case modes (missing size / tolerance / one-fixed / honor-each).
"""

import pytest

from app.services.price_service import (
    target_pair_value,
    values_within_tolerance,
    fairness_for_category,
    user_value_for,
)


def _p(specs=None, **kw):
    d = {"specs": specs or {}}
    d.update(kw)
    return d


# ---------------------------------------- F6.1 electronics honor-each (256/128) ---

class TestElectronicsHonorEach:
    def test_256_vs_128_honor_each(self):
        # Both storage tiers stated in the query → honor each (show both, no pend).
        plan = target_pair_value(
            "iPhone 15 256GB vs Galaxy S24 128GB",
            _p({"storage": "256 GB"}), _p({"storage": "128 GB"}),
            "electronics",
        )
        assert plan["mode"] == "honor_each"
        assert plan["per_product"][0] == 256
        assert plan["per_product"][1] == 128

    def test_128_vs_256_not_within_tolerance(self):
        # 128 vs 256 (×2) is a real discrete gap — never "similar".
        spec = fairness_for_category("electronics")
        assert values_within_tolerance(128, 256, spec) is False

    def test_256_vs_250_within_tolerance(self):
        # A 256 vs 250GB rounding still matches (discrete band).
        spec = fairness_for_category("electronics")
        assert values_within_tolerance(256, 250, spec) is True


# -------------------------------------------- F6.2 grocery weight-fairness ---

class TestGroceryWeightFairness:
    def test_nutella_750_vs_biscoff_400_honor_each_when_both_stated(self):
        plan = target_pair_value(
            "Nutella 750g vs Biscoff 400g",
            _p({"size": "750 g"}), _p({"size": "400 g"}),
            "grocery",
        )
        # Both weights stated → honor each (different real pack sizes).
        assert plan["mode"] == "honor_each"
        assert plan["per_product"][0] == 750
        assert plan["per_product"][1] == 400

    def test_grocery_230_vs_250_similar(self):
        # Continuous weight — a 230g vs 250g jar is "similar" (within band).
        spec = fairness_for_category("grocery")
        assert values_within_tolerance(230, 250, spec) is True

    def test_grocery_400_vs_750_not_similar(self):
        spec = fairness_for_category("grocery")
        assert values_within_tolerance(400, 750, spec) is False


# ----------------------------------------------------- the four edge modes ---

class TestFairnessEdgeModes:
    def test_one_mentioned_targets_it(self):
        # Rule 2a — one side states a value → target it for both.
        plan = target_pair_value(
            "iPhone 15 256GB vs Galaxy S24",
            _p({"storage": "256 GB"}), _p({"storage": "128 GB"}),
            "electronics",
        )
        assert plan["mode"] == "target"
        assert plan["target"] == 256

    def test_neither_mentioned_no_crash(self):
        # Rule 3 — neither side states a value → a plan (target/none), never raises.
        plan = target_pair_value(
            "iPhone 15 vs Galaxy S24",
            _p({"storage": "256 GB"}), _p({"storage": "256 GB"}),
            "electronics",
        )
        assert plan["mode"] in ("target", "honor_each", "none")

    def test_similar_values_honor_each(self):
        # Rule 4 — two near-equal fragrance sizes are already a fair basis.
        spec = fairness_for_category("fragrances")
        assert values_within_tolerance(90, 100, spec) is True

    def test_fashion_unit_none_mode_none(self):
        plan = target_pair_value(
            "Nike Air Force 1 vs Adidas Stan Smith",
            _p({"material": "leather"}), _p({"material": "leather"}),
            "fashion",
        )
        assert plan["mode"] == "none"

    def test_missing_size_one_side(self):
        # One side has NO size signal → not a confirmed match; plan still resolves.
        spec = fairness_for_category("fragrances")
        assert values_within_tolerance(None, 100, spec) is False


# ----------------------------------------------- F6.3 user_value parsing ---

class TestUserValueParsing:
    def test_storage_mention(self):
        assert user_value_for("iPhone 15 256GB", "electronics") == 256

    def test_ml_mention(self):
        assert user_value_for("Tom Ford 50ml", "fragrances") == 50

    def test_count_mention(self):
        assert user_value_for("Vitamin D3 120 capsules", "supplements") == 120

    def test_fashion_always_none(self):
        assert user_value_for("Nike size 42", "fashion") is None

    def test_no_value_none(self):
        assert user_value_for("iPhone 15", "electronics") is None


# ------------------------------------- Task 6.2 fragrance size capture (text) ---
# When the scraper passes variant-widget / PDP text through, extract_size_ml_any
# captures the ml from the common widget text forms (ml, oz, range, "Size:").
# The flagship-100ml default stays last-resort. (Size ONLY in an image with no
# text is a genuine free-tier blind spot — out of scope, no OCR.)

class TestFragranceSizeCaptureFromVariantText:
    @pytest.mark.parametrize("text,expected", [
        ("Size: 100 ml", 100),
        ("100ML", 100),
        ("Select size 50ml / 100ml", 50),   # smallest = conservative basis
        ("3.4 fl oz", 100),                  # oz → ml, snapped to standard bottle
        ("variant: 1.7oz", 50),
    ])
    def test_variant_widget_text_captures_ml(self, text, expected):
        from app.services.price_service import extract_size_ml_any
        assert extract_size_ml_any(text) == expected

    def test_no_size_text_returns_none(self):
        from app.services.price_service import extract_size_ml_any
        assert extract_size_ml_any("Add to bag") is None

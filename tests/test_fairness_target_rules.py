"""Refined pair-fairness TARGET-SELECTION rules (feature/fairness-target-rules).

Ahmed's directive replaces the old "single distinct user value, else the LARGER
present value, pend the side that can't reach it" target logic with a 4-rule
priority:

  1. MENTIONED PER PRODUCT -> honor each. If the USER QUERY specifies a value for
     BOTH products (per-product, by splitting the "A vs B" query OR the explicit
     product_a/product_b shape), keep each price at its own mentioned value — do
     NOT force-match, do NOT pend. The verdict's like-for-like rule flags the
     tier difference. Live case: "iPhone 256GB vs Galaxy 128GB" -> iPhone 256,
     Galaxy 128, BOTH shown.
  2. ONE MENTIONED, or one product FIXED-SIZE -> go by it. One user value, OR one
     product is only available in a single size (its retained candidates all
     share one value) -> target THAT value, reconcile the other to it.
  3. NEITHER MENTIONED -> common standard, both the same. Target the value BOTH
     products can satisfy from candidates — prefer the LARGEST shared value; fall
     back to the smaller shared value; only pend if there is no shared basis.
  4. SIMILAR VALUES -> treat as matching (tolerance), no pend. Per-category band:
     discrete units (storage GB, count) match within a tight band (equal or
     <=~5%); continuous units (ml, g/weight) are "similar" within ~+/-15%. So
     90ml vs 100ml (or 90-count vs 100-count under continuous) pass through.

`target_pair_value(query, p0, p1, category, candidates_by_name=...)` returns the
RICH plan: {"mode": "honor_each"|"target"|"none", "target": <value|None>,
"per_product": {0: v0|None, 1: v1|None}}. `reconcile_pair_fairness` consumes it:
  - honor_each -> leave both prices untouched (no reselect, no pend).
  - target     -> resolve both to target (reselect off-target, pend if it can't
                  reach it AND it's outside tolerance).
  - none       -> no comparable axis / incomparable base -> pass through.

Fragrances delegate reconcile to reconcile_pair_sizes verbatim (frozen), keeping
the flagship-100ml default for the no-signal case.

Run: pytest tests/test_fairness_target_rules.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    CATEGORY_FAIRNESS,
    target_pair_value,
    reconcile_pair_fairness,
    user_value_for,
    values_within_tolerance,
)


def _prod(name, amount, *, price_size=None, price_title=None, specs=None,
          variant=None, source_method="local_bhd"):
    price = {
        "amount": amount, "currency": "BHD",
        "source_method": source_method, "size": price_size,
    }
    if price_title is not None:
        price["title"] = price_title
    p = {
        "name": name, "full_name": name,
        "price": price,
        "best_price": amount,
        "retailer": "someshop.bh",
        "specs": specs or {},
    }
    if variant is not None:
        p["variant"] = variant
    return p


def _cand(amount, *, source_method="page_scrape_jsonld", title=None,
          retailer="someshop.bh", size=None, variant_rank=0.0):
    raw = {
        "amount": amount, "currency": "BHD", "source_method": source_method,
        "retailer": retailer, "url": f"https://{retailer}/p",
        "title": title, "size": size,
    }
    return {
        "value": amount, "rank": 85, "source_method": source_method,
        "retailer": retailer, "variant_rank": variant_rank, "raw_data": raw,
    }


# ===========================================================================
# Per-product query-value parser — user_value_for(query_side, category)
# ===========================================================================
class TestUserValueFor:
    def test_storage_side(self):
        assert user_value_for("iPhone 15 256GB", "electronics") == 256.0

    def test_storage_tb(self):
        assert user_value_for("MacBook 1TB", "electronics") == 1024.0

    def test_count_side(self):
        assert user_value_for("Vitamin D3 120 capsules", "supplements") == 120.0

    def test_ml_side(self):
        assert user_value_for("Dior Sauvage 50ml", "fragrances") == 50.0

    def test_no_value_side(self):
        assert user_value_for("Galaxy S24", "electronics") is None

    def test_ambiguous_side_two_values_none(self):
        # A single SIDE mentioning two storages is ambiguous -> no single value.
        assert user_value_for("iPhone 256GB or 512GB", "electronics") is None

    def test_unit_none_category_always_none(self):
        assert user_value_for("Leather Tote Large", "fashion") is None


# ===========================================================================
# Tolerance helper — values_within_tolerance(a, b, spec)
# ===========================================================================
class TestTolerance:
    def test_discrete_storage_equal_matches(self):
        spec = CATEGORY_FAIRNESS["electronics"]
        assert values_within_tolerance(256.0, 256.0, spec) is True

    def test_discrete_storage_128_vs_256_mismatch(self):
        spec = CATEGORY_FAIRNESS["electronics"]
        assert values_within_tolerance(128.0, 256.0, spec) is False

    def test_discrete_count_60_vs_62_within_band(self):
        # 62/60 = 3.3% <= 5% tight band -> match.
        spec = CATEGORY_FAIRNESS["supplements"]
        assert values_within_tolerance(60.0, 62.0, spec) is True

    def test_discrete_count_60_vs_120_mismatch(self):
        spec = CATEGORY_FAIRNESS["supplements"]
        assert values_within_tolerance(60.0, 120.0, spec) is False

    def test_continuous_90ml_vs_100ml_similar(self):
        # |10| <= 0.15 * 100 = 15 -> similar.
        spec = CATEGORY_FAIRNESS["haircare"]
        assert values_within_tolerance(90.0, 100.0, spec) is True

    def test_continuous_30ml_vs_100ml_mismatch(self):
        spec = CATEGORY_FAIRNESS["haircare"]
        assert values_within_tolerance(30.0, 100.0, spec) is False

    def test_every_category_has_tolerance(self):
        for cat, spec in CATEGORY_FAIRNESS.items():
            assert "tolerance" in spec, f"{cat} missing tolerance"


# ===========================================================================
# RULE 1 — both mentioned -> honor_each (the live 256-vs-128 fix)
# ===========================================================================
class TestRule1HonorEach:
    def test_target_plan_honor_each_storage(self):
        p0 = _prod("iPhone 15 256GB", 520.0)
        p1 = _prod("Galaxy S24 128GB", 420.0)
        plan = target_pair_value("iPhone 15 256GB vs Galaxy S24 128GB", p0, p1,
                                 "electronics")
        assert plan["mode"] == "honor_each"
        assert plan["per_product"][0] == 256.0
        assert plan["per_product"][1] == 128.0

    def test_reconcile_256_vs_128_honors_both_no_pend(self):
        # THE headline change: both prices kept, NEITHER pended.
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("Galaxy S24 128GB", 420.0, source_method="page_scrape_jsonld"),
        ]
        changed = reconcile_pair_fairness(
            pd, "iPhone 15 256GB vs Galaxy S24 128GB", "electronics",
            candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 520.0
        assert pd[1]["price"]["amount"] == 420.0
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"].get("unavailable") is not True

    def test_reconcile_honor_each_ignores_candidates(self):
        # Even with candidates that could re-rank, honor_each leaves prices alone.
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("Galaxy S24 128GB", 420.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Galaxy S24 128GB": [
                _cand(420.0, title="Galaxy S24 128GB", size="128GB"),
                _cand(560.0, title="Galaxy S24 256GB", size="256GB"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "iPhone 15 256GB vs Galaxy S24 128GB", "electronics",
            candidates_by_name=cands)
        assert changed is False
        assert pd[1]["price"]["amount"] == 420.0  # NOT bumped to 256GB candidate

    def test_explicit_versus_separator_also_splits(self):
        p0 = _prod("iPhone 15 256GB", 520.0)
        p1 = _prod("Galaxy S24 128GB", 420.0)
        plan = target_pair_value("iPhone 15 256GB versus Galaxy S24 128GB",
                                 p0, p1, "electronics")
        assert plan["mode"] == "honor_each"

    def test_pipe_separator_also_splits(self):
        p0 = _prod("iPhone 15 256GB", 520.0)
        p1 = _prod("Galaxy S24 128GB", 420.0)
        plan = target_pair_value("iPhone 15 256GB | Galaxy S24 128GB",
                                 p0, p1, "electronics")
        assert plan["mode"] == "honor_each"


# ===========================================================================
# RULE 2 — one mentioned / fixed-size -> target, reconcile the other
# ===========================================================================
class TestRule2OneMentionedOrFixed:
    def test_plan_one_mentioned_target(self):
        p0 = _prod("iPhone 15 256GB", 520.0)
        p1 = _prod("Galaxy S24", 420.0)
        plan = target_pair_value("iPhone 15 256GB vs Galaxy S24", p0, p1,
                                 "electronics")
        assert plan["mode"] == "target"
        assert plan["target"] == 256.0

    def test_reconcile_one_mentioned_reselects_other(self):
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("Galaxy S24 128GB", 420.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Galaxy S24 128GB": [
                _cand(420.0, title="Galaxy S24 128GB", size="128GB"),
                _cand(560.0, title="Galaxy S24 256GB", size="256GB"),
            ],
        }
        # Only the iPhone side carries a user-mentioned 256GB; Galaxy unspecified
        # in the query -> target 256, re-select Galaxy UP to its 256GB candidate.
        changed = reconcile_pair_fairness(
            pd, "iPhone 15 256GB vs Galaxy S24", "electronics",
            candidates_by_name=cands)
        assert changed is True
        assert pd[0]["price"]["amount"] == 520.0
        assert pd[1]["price"]["amount"] == 560.0  # re-selected to 256GB

    def test_fixed_size_product_sets_target(self):
        # Neither side MENTIONED in the query, but product B's candidates are all
        # one size (50ml) -> it's fixed-size -> target 50ml, match A to it.
        p0 = _prod("Serum A 100ml", 30.0)
        p1 = _prod("Serum B", 20.0)
        cands = {"Serum B": [
            _cand(20.0, title="Serum B 50ml", size="50ml"),
            _cand(21.0, title="Serum B 50ml alt", size="50ml"),
        ]}
        plan = target_pair_value("Serum A vs Serum B", p0, p1, "skincare",
                                 candidates_by_name=cands)
        assert plan["mode"] == "target"
        assert plan["target"] == 50.0

    def test_fixed_size_reconcile_matches_a_to_b(self):
        # A is 100ml; B fixed at 50ml. Target 50ml. A re-selects DOWN to its
        # genuine 50ml candidate; both shown at 50ml.
        pd = [
            _prod("Serum A 100ml", 30.0, source_method="page_scrape_jsonld"),
            _prod("Serum B 50ml", 20.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Serum A 100ml": [
                _cand(30.0, title="Serum A 100ml", size="100ml"),
                _cand(18.0, title="Serum A 50ml", size="50ml"),
            ],
            "Serum B 50ml": [
                _cand(20.0, title="Serum B 50ml", size="50ml"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "Serum A vs Serum B", "skincare", candidates_by_name=cands)
        assert changed is True
        assert pd[0]["price"]["amount"] == 18.0  # A -> its 50ml candidate
        assert pd[1]["price"]["amount"] == 20.0  # B already 50ml


# ===========================================================================
# RULE 3 — neither mentioned -> common standard (largest shared value)
# ===========================================================================
class TestRule3CommonStandard:
    def test_plan_largest_common_value(self):
        # Neither mentioned. Both candidate pools share 128 AND 256 -> target the
        # LARGEST shared = 256.
        p0 = _prod("iPhone 15 256GB", 520.0)
        p1 = _prod("iPhone 15 128GB", 420.0)
        cands = {
            "iPhone 15 256GB": [
                _cand(420.0, title="iPhone 15 128GB", size="128GB"),
                _cand(520.0, title="iPhone 15 256GB", size="256GB"),
            ],
            "iPhone 15 128GB": [
                _cand(415.0, title="iPhone 15 128GB", size="128GB"),
                _cand(540.0, title="iPhone 15 256GB", size="256GB"),
            ],
        }
        plan = target_pair_value("iPhone 15 vs iPhone 15", p0, p1, "electronics",
                                 candidates_by_name=cands)
        assert plan["mode"] == "target"
        assert plan["target"] == 256.0

    def test_plan_falls_back_to_smaller_common(self):
        # Pools share ONLY 128 (one side has no 256 candidate) -> target 128.
        p0 = _prod("iPhone 15 256GB", 520.0)
        p1 = _prod("iPhone 15 128GB", 420.0)
        cands = {
            "iPhone 15 256GB": [
                _cand(420.0, title="iPhone 15 128GB", size="128GB"),
                _cand(520.0, title="iPhone 15 256GB", size="256GB"),
            ],
            "iPhone 15 128GB": [
                _cand(415.0, title="iPhone 15 128GB", size="128GB"),
            ],
        }
        plan = target_pair_value("iPhone 15 vs iPhone 15", p0, p1, "electronics",
                                 candidates_by_name=cands)
        assert plan["mode"] == "target"
        assert plan["target"] == 128.0

    def test_reconcile_common_standard_both_priced(self):
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("iPhone 15 128GB", 420.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "iPhone 15 256GB": [
                _cand(420.0, title="iPhone 15 128GB", size="128GB"),
                _cand(520.0, title="iPhone 15 256GB", size="256GB"),
            ],
            "iPhone 15 128GB": [
                _cand(415.0, title="iPhone 15 128GB", size="128GB"),
                _cand(540.0, title="iPhone 15 256GB", size="256GB"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "iPhone 15 vs iPhone 15", "electronics",
            candidates_by_name=cands)
        assert changed is True
        # Both resolve to the largest shared standard (256).
        assert pd[0]["price"]["amount"] == 520.0
        assert pd[1]["price"]["amount"] == 540.0  # 128 side re-selected up to 256

    def test_no_shared_basis_pends(self):
        # Neither mentioned, neither FIXED-size (each pool has TWO values), and the
        # pools share NOTHING (256/512 vs 64/128) -> no common basis. The
        # resolved-base default (max present = 512) becomes the target; only the
        # 512-side reaches it (the 128-side has no 512 candidate) -> pend the
        # off-basis side.
        pd = [
            _prod("Phone A 512GB", 700.0, source_method="page_scrape_jsonld"),
            _prod("Phone B 128GB", 420.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Phone A 512GB": [
                _cand(620.0, title="Phone A 256GB", size="256GB"),
                _cand(700.0, title="Phone A 512GB", size="512GB"),
            ],
            "Phone B 128GB": [
                _cand(360.0, title="Phone B 64GB", size="64GB"),
                _cand(420.0, title="Phone B 128GB", size="128GB"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "Phone A vs Phone B", "electronics",
            candidates_by_name=cands)
        assert changed is True
        pended = [p for p in pd if p["price"].get("unavailable") is True]
        assert len(pended) == 1


# ===========================================================================
# RULE 4 — similar values -> treat as matching (tolerance), no pend
# ===========================================================================
class TestRule4Tolerance:
    def test_plan_90ml_vs_100ml_similar_honor_each(self):
        # Continuous: 90ml vs 100ml within +/-15% -> already-fair -> honor_each.
        p0 = _prod("Shampoo A 90ml", 5.0)
        p1 = _prod("Shampoo B 100ml", 6.0)
        plan = target_pair_value("Shampoo A vs Shampoo B", p0, p1, "haircare")
        assert plan["mode"] == "honor_each"

    def test_reconcile_90ml_vs_100ml_passes_through(self):
        pd = [
            _prod("Shampoo A 90ml", 5.0),
            _prod("Shampoo B 100ml", 6.0),
        ]
        changed = reconcile_pair_fairness(
            pd, "Shampoo A vs Shampoo B", "haircare", candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 5.0
        assert pd[1]["price"]["amount"] == 6.0

    def test_reconcile_30ml_vs_100ml_mismatch_handled(self):
        # 30ml vs 100ml is OUTSIDE tolerance -> not honor_each. No shared candidate
        # basis -> the off-target side pends (a genuine mismatch).
        pd = [
            _prod("Shampoo A 30ml", 3.0, source_method="page_scrape_jsonld"),
            _prod("Shampoo B 100ml", 6.0, source_method="page_scrape_jsonld"),
        ]
        changed = reconcile_pair_fairness(
            pd, "Shampoo A vs Shampoo B", "haircare", candidates_by_name={})
        assert changed is True
        pended = [p for p in pd if p["price"].get("unavailable") is True]
        assert len(pended) >= 1

    def test_storage_128_vs_256_is_discrete_mismatch_not_similar(self):
        # Discrete: 128 vs 256 must NOT be "similar" — they are a real tier gap.
        p0 = _prod("Phone A 128GB", 400.0)
        p1 = _prod("Phone B 256GB", 500.0)
        plan = target_pair_value("Phone A vs Phone B", p0, p1, "electronics")
        # Neither mentioned, no candidates -> common-standard default (resolved
        # base), NOT honor_each-by-tolerance.
        assert plan["mode"] != "honor_each"

    def test_supplements_60_vs_62_similar_honor_each(self):
        # Discrete count within the tight 5% band -> treat as matching.
        p0 = _prod("Vit D3 60 caps", 5.0)
        p1 = _prod("Vit D3 62 caps", 5.2)
        plan = target_pair_value("Vit D3 vs Vit D3 B", p0, p1, "supplements")
        assert plan["mode"] == "honor_each"


# ===========================================================================
# Net-effect / regression of the documented live cases
# ===========================================================================
class TestLiveCases:
    def test_iphone_256_vs_galaxy_128_shows_both(self):
        # The exact directive case: both mentioned -> both shown, no pend.
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("Galaxy S24 128GB", 420.0, source_method="page_scrape_jsonld"),
        ]
        reconcile_pair_fairness(pd, "iPhone 256GB vs Galaxy 128GB", "electronics",
                                candidates_by_name={})
        assert pd[0]["price"]["amount"] == 520.0
        assert pd[1]["price"]["amount"] == 420.0

    def test_fragrance_no_signal_flagship_both_unchanged(self):
        # "Ombré vs Tobacco" no sizes -> flagship 100ml both -> unchanged.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0),
            _prod("Tom Ford Tobacco Vanille", 90.0),
        ]
        changed = reconcile_pair_fairness(
            pd, "Tom Ford Ombré vs Tobacco Vanille", "fragrances",
            candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] == 90.0

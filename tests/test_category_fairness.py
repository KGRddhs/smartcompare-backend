"""Category-aware fairness standard — generalizes the fragrance pair-size
reconcile to EVERY category that has a comparable "must-match" unit.

ONE central per-category config (CATEGORY_FAIRNESS) drives:
  - the comparable unit + how to read it off a product / a query / a pair default
  - target_pair_value(query, p0, p1, category)  -> the fairness target
  - reconcile_pair_fairness(product_data, query, category) -> re-select OR pend
  - reselect_to_target_value(candidates, target, category) -> re-rank retained

Per category (Part 1):
  electronics -> storage GB (spec storage -> variant -> name; exact match)
  fragrances  -> ml (REUSE effective_pair_size_ml; flagship-100ml default)
  supplements -> unit count (caps/tablets/softgels)
  grocery     -> net weight/volume (g/kg/ml/L; kg->g, L->ml)
  makeup      -> volume/weight (ml/g)
  skincare    -> volume/weight (ml/g)
  haircare    -> volume (ml)
  fashion     -> None (no comparable unit)
  other       -> None

Run: pytest tests/test_category_fairness.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    CATEGORY_FAIRNESS,
    fairness_for_category,
    target_pair_value,
    reselect_to_target_value,
    reconcile_pair_fairness,
    # the existing fragrance machinery the generalization must preserve
    target_pair_size_ml,
    effective_pair_size_ml,
)


# ---------------------------------------------------------------------------
# Helpers — mirror tests/test_pair_size_reselection.py conventions.
# ---------------------------------------------------------------------------
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
# Part 1 — the CATEGORY_FAIRNESS config: shape + per-category extractors
# ===========================================================================
class TestConfigShape:
    def test_all_nine_categories_present(self):
        for cat in ("electronics", "grocery", "supplements", "makeup",
                    "skincare", "haircare", "fragrances", "fashion", "other"):
            assert cat in CATEGORY_FAIRNESS, f"{cat} missing from CATEGORY_FAIRNESS"

    def test_each_spec_has_required_keys(self):
        for cat, spec in CATEGORY_FAIRNESS.items():
            for key in ("unit", "extract", "normalize", "user_query_value",
                        "default_basis", "label"):
                assert key in spec, f"{cat}.{key} missing"
            assert callable(spec["extract"])
            assert callable(spec["normalize"])
            assert callable(spec["user_query_value"])
            assert callable(spec["default_basis"])

    def test_fashion_and_other_have_no_unit(self):
        assert CATEGORY_FAIRNESS["fashion"]["unit"] is None
        assert CATEGORY_FAIRNESS["other"]["unit"] is None

    def test_unit_labels(self):
        assert CATEGORY_FAIRNESS["electronics"]["unit"] == "GB"
        assert CATEGORY_FAIRNESS["fragrances"]["unit"] == "ml"
        assert CATEGORY_FAIRNESS["supplements"]["unit"] == "count"

    def test_fairness_for_category_canonicalizes_and_defaults(self):
        # Free-form input is canonicalized; unknown -> the "other" (unit=None) spec.
        assert fairness_for_category("Electronics")["unit"] == "GB"
        assert fairness_for_category("Fragrances")["unit"] == "ml"
        assert fairness_for_category("totally-unknown")["unit"] is None
        assert fairness_for_category(None)["unit"] is None


class TestElectronicsExtractor:
    def _extract(self, product):
        return CATEGORY_FAIRNESS["electronics"]["extract"](product)

    def test_storage_spec_gb(self):
        assert self._extract(_prod("iPhone 15", 400.0, specs={"storage": "256GB"})) == 256.0

    def test_storage_spec_tb_to_gb(self):
        assert self._extract(_prod("MacBook Pro", 900.0, specs={"storage": "1TB"})) == 1024.0

    def test_variant_field_when_no_spec(self):
        assert self._extract(_prod("iPhone 15", 400.0, variant="128GB")) == 128.0

    def test_name_when_no_spec_or_variant(self):
        assert self._extract(_prod("iPhone 15 Pro 512GB", 500.0)) == 512.0

    def test_spec_precedence_over_variant_and_name(self):
        p = _prod("iPhone 15 1TB", 500.0, specs={"storage": "256GB"}, variant="512GB")
        assert self._extract(p) == 256.0

    def test_none_when_no_storage_signal(self):
        assert self._extract(_prod("Some Gadget", 100.0)) is None


class TestSupplementsExtractor:
    def _extract(self, product):
        return CATEGORY_FAIRNESS["supplements"]["extract"](product)

    def test_count_spec(self):
        assert self._extract(_prod("Vitamin D3", 5.0, specs={"count": "60 capsules"})) == 60.0

    def test_count_from_name(self):
        assert self._extract(_prod("NOW Foods Magnesium 120 tablets", 8.0)) == 120.0

    def test_softgels(self):
        assert self._extract(_prod("Fish Oil 90 softgels", 9.0)) == 90.0

    def test_none_when_no_count(self):
        assert self._extract(_prod("Solgar D3", 5.0)) is None


class TestGroceryExtractor:
    def _extract(self, product):
        return CATEGORY_FAIRNESS["grocery"]["extract"](product)

    def test_grams(self):
        assert self._extract(_prod("Lurpak Butter 200g", 2.0)) == 200.0

    def test_kg_to_grams(self):
        assert self._extract(_prod("Basmati Rice 5kg", 6.0)) == 5000.0

    def test_litres_to_ml(self):
        assert self._extract(_prod("Olive Oil 1L", 4.0)) == 1000.0

    def test_ml_stays_ml(self):
        assert self._extract(_prod("Juice 500ml", 1.0)) == 500.0

    def test_size_spec_used(self):
        assert self._extract(_prod("Honey", 3.0, specs={"size": "250g"})) == 250.0

    def test_none_when_no_size(self):
        assert self._extract(_prod("Mystery Snack", 1.0)) is None


class TestVolumeWeightExtractors:
    @pytest.mark.parametrize("cat", ["makeup", "skincare", "haircare"])
    def test_ml_volume(self, cat):
        assert CATEGORY_FAIRNESS[cat]["extract"](_prod("Serum 50ml", 10.0)) == 50.0

    @pytest.mark.parametrize("cat", ["makeup", "skincare"])
    def test_grams_weight(self, cat):
        # makeup/skincare accept ml OR g
        assert CATEGORY_FAIRNESS[cat]["extract"](_prod("Cream 30g", 10.0)) == 30.0

    def test_haircare_volume_spec(self):
        assert CATEGORY_FAIRNESS["haircare"]["extract"](
            _prod("Shampoo", 5.0, specs={"volume": "400ml"})) == 400.0

    def test_none_when_no_volume(self):
        assert CATEGORY_FAIRNESS["skincare"]["extract"](_prod("Mystery Goo", 5.0)) is None


class TestFashionOtherExtractor:
    @pytest.mark.parametrize("cat", ["fashion", "other"])
    def test_extract_always_none(self, cat):
        # No comparable unit -> the extractor returns None for everything.
        assert CATEGORY_FAIRNESS[cat]["extract"](
            _prod("Leather Tote", 200.0, specs={"size_options": "S/M/L"})) is None


# ===========================================================================
# Part 2a — target_pair_value: the fairness PLAN per category
#
# REFACTORED (feature/fairness-target-rules): target_pair_value now returns the
# rich plan {"mode", "target", "per_product"} driving Ahmed's 4-rule selection,
# instead of a bare scalar target. These assertions read .mode/.target. The
# semantic targets are PRESERVED except where the new rules intentionally differ
# (a per-product-mentioned pair → honor_each instead of a forced common target).
# ===========================================================================
class TestTargetPairValue:
    def test_electronics_matched_pair_target(self):
        # Both 256GB, no per-product MENTION in the query -> already fair within
        # tolerance -> honor_each (both stay at 256; outcome identical to the old
        # "target 256").
        p0 = _prod("iPhone 15 256GB", 400.0)
        p1 = _prod("Galaxy S24 256GB", 450.0)
        plan = target_pair_value("iPhone vs Galaxy", p0, p1, "electronics")
        assert plan["mode"] == "honor_each"
        assert plan["per_product"][0] == 256.0
        assert plan["per_product"][1] == 256.0

    def test_electronics_mismatch_target_no_force_bump(self):
        # 128 vs 256, neither mentioned, no candidates -> common-standard falls
        # back to the resolved base (the larger present value, no invented flagship).
        p0 = _prod("iPhone 15 128GB", 400.0)
        p1 = _prod("Galaxy S24 256GB", 450.0)
        plan = target_pair_value("iPhone vs Galaxy", p0, p1, "electronics")
        assert plan["mode"] == "target"
        assert plan["target"] in (128.0, 256.0)  # a resolved base, not None

    def test_electronics_user_query_size_honored(self):
        # User typed "512GB" on ONE side -> target 512 (Rule 2a, one mentioned).
        p0 = _prod("iPhone 15", 400.0)
        p1 = _prod("Galaxy S24", 450.0)
        plan = target_pair_value("iPhone vs Galaxy 512GB", p0, p1, "electronics")
        assert plan["mode"] == "target"
        assert plan["target"] == 512.0

    def test_supplements_user_count(self):
        # "60 capsules" on the FIRST side, nothing on "B" -> one mentioned -> 60.
        p0 = _prod("Vit D3", 5.0)
        p1 = _prod("Vit D3 B", 6.0)
        plan = target_pair_value("Vit D3 60 capsules vs B", p0, p1, "supplements")
        assert plan["mode"] == "target"
        assert plan["target"] == 60.0

    def test_fashion_target_always_none(self):
        p0 = _prod("Tote A", 200.0)
        p1 = _prod("Tote B", 250.0)
        assert target_pair_value("Tote A vs Tote B", p0, p1, "fashion")["mode"] == "none"

    def test_other_target_always_none(self):
        p0 = _prod("Thing A", 20.0)
        p1 = _prod("Thing B", 25.0)
        assert target_pair_value("Thing A vs Thing B", p0, p1, "other")["mode"] == "none"

    def test_fragrance_target_matches_legacy(self):
        # No user sizes -> the fragrance target MUST still equal the existing
        # target_pair_size_ml (flagship 100ml). The plan's .target carries it.
        p0 = _prod("Tom Ford Ombré Leather", 80.0)
        p1 = _prod("Tom Ford Tobacco Vanille 30 ML", 28.2)
        q = "Tom Ford Ombré vs Tobacco Vanille"
        plan = target_pair_value(q, p0, p1, "fragrances")
        assert plan["target"] == target_pair_size_ml(q, p0, p1)
        assert plan["target"] == 100.0


# ===========================================================================
# Part 2b — reselect_to_target_value: re-rank retained candidates
# ===========================================================================
class TestReselectValue:
    def test_electronics_reselect_to_target_storage(self):
        cands = [
            _cand(400.0, title="iPhone 15 128GB", size="128GB"),
            _cand(520.0, title="iPhone 15 256GB", size="256GB"),
        ]
        out = reselect_to_target_value("iPhone 15", cands, 256.0, "electronics")
        assert out is not None
        assert out["amount"] == 520.0

    def test_electronics_no_candidate_at_target(self):
        cands = [_cand(400.0, title="iPhone 15 128GB", size="128GB")]
        assert reselect_to_target_value("iPhone 15", cands, 256.0, "electronics") is None

    def test_electronics_rejects_estimated(self):
        cands = [_cand(520.0, source_method="estimated", retailer=None,
                       title="iPhone 15 256GB", size="256GB")]
        assert reselect_to_target_value("iPhone 15", cands, 256.0, "electronics") is None

    def test_supplements_reselect_to_count(self):
        cands = [
            _cand(5.0, title="Vit D3 60 capsules", size="60 capsules"),
            _cand(9.0, title="Vit D3 120 capsules", size="120 capsules"),
        ]
        out = reselect_to_target_value("Vitamin D3", cands, 120.0, "supplements")
        assert out is not None
        assert out["amount"] == 9.0

    def test_fragrance_reselect_matches_legacy_behavior(self):
        # Same candidates as the fragrance suite -> picks the genuine 100ml.
        cands = [
            _cand(28.2, title="Tobacco Vanille 30 ML", size="30ml"),
            _cand(118.0, title="Tobacco Vanille 100ml EDP", size="100ml"),
        ]
        out = reselect_to_target_value("Tom Ford Tobacco Vanille", cands, 100.0, "fragrances")
        assert out is not None
        assert out["amount"] == 118.0

    def test_fashion_unit_none_returns_none(self):
        cands = [_cand(200.0, title="Tote", size=None)]
        assert reselect_to_target_value("Tote", cands, 1.0, "fashion") is None


# ===========================================================================
# Part 2c — reconcile_pair_fairness: the three outcomes, per category
# ===========================================================================
class TestReconcileElectronics:
    def test_128_vs_256_mismatch_reselects_when_possible(self):
        # The flagship electronics case: 128 vs 256. The resolved-base target is
        # 256 (the larger, no force-bump). The off-basis (128GB) product has a
        # retained 256GB candidate -> re-select UP to 256, BOTH priced.
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("iPhone 15 128GB", 400.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            # candidates retained under the OFF-basis (128GB) product's own name.
            "iPhone 15 128GB": [
                _cand(400.0, title="iPhone 15 128GB", size="128GB"),
                _cand(540.0, title="iPhone 15 256GB", size="256GB"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "iPhone 15", "electronics", candidates_by_name=cands,
        )
        assert changed is True
        # Target = 256 (resolved base, larger). The 128GB product re-selects UP to
        # its genuine 256GB listing; both now at 256.
        assert pd[0]["price"]["amount"] == 520.0       # already 256GB
        assert pd[1]["price"]["amount"] == 540.0       # re-selected to 256GB
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"].get("unavailable") is not True

    def test_128_vs_256_pends_off_basis_when_no_candidate(self):
        # 128 vs 256, no retained candidate at the target for the off-basis
        # product -> pend ONLY it (reason="unit_mismatch"); the matched one shows.
        pd = [
            _prod("iPhone 15 256GB", 520.0, source_method="page_scrape_jsonld"),
            _prod("iPhone 15 128GB", 400.0, source_method="page_scrape_jsonld"),
        ]
        changed = reconcile_pair_fairness(
            pd, "iPhone 15", "electronics", candidates_by_name={},
        )
        assert changed is True
        # Target = 256 (resolved base, larger). The 256GB product is already
        # at-target and STAYS priced; the 128GB product can't reach 256 (no
        # candidate) -> pends.
        assert pd[0]["price"]["amount"] == 520.0       # 256GB stays
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"]["amount"] is None         # 128GB pends
        assert pd[1]["price"]["unavailable"] is True
        assert pd[1]["price"]["reason"] == "unit_mismatch"

    def test_matched_storage_passes_through(self):
        # Both 256GB -> a valid common basis -> no change.
        pd = [
            _prod("iPhone 15 256GB", 520.0),
            _prod("Galaxy S24 256GB", 480.0),
        ]
        changed = reconcile_pair_fairness(
            pd, "iPhone vs Galaxy", "electronics", candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 520.0
        assert pd[1]["price"]["amount"] == 480.0


class TestReconcileSupplements:
    def test_60_vs_120_mismatch_reselects(self):
        # NEITHER count is in the QUERY ("Vit D3 vs Vit D3 B") -> Rule 3 common
        # standard. The product NAMES carry the differing counts (120 vs 60), no
        # shared candidate value -> resolved-base default = 120. The 60-count side
        # re-selects UP to its genuine 120 candidate; both priced.
        pd = [
            _prod("Vit D3 120 caps", 9.0, source_method="page_scrape_jsonld"),
            _prod("Vit D3 60 caps", 5.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Vit D3 60 caps": [
                _cand(5.0, title="Vit D3 60 capsules", size="60 capsules"),
                _cand(9.0, title="Vit D3 120 capsules", size="120 capsules"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "Vit D3 vs Vit D3 B", "supplements",
            candidates_by_name=cands)
        assert changed is True
        assert pd[0]["price"]["amount"] == 9.0
        assert pd[1]["price"]["amount"] == 9.0  # re-selected to 120 count

    def test_60_vs_120_pends_off_basis_when_no_candidate(self):
        # NEITHER count mentioned in the query -> Rule 3. No candidate to reach the
        # 120 default for the 60-count side -> pend ONLY it.
        pd = [
            _prod("Vit D3 120 caps", 9.0, source_method="page_scrape_jsonld"),
            _prod("Vit D3 60 caps", 5.0, source_method="page_scrape_jsonld"),
        ]
        changed = reconcile_pair_fairness(
            pd, "Vit D3 vs Vit D3 B", "supplements",
            candidates_by_name={})
        assert changed is True
        pended = [p for p in pd if p["price"].get("unavailable") is True]
        assert len(pended) == 1
        assert pended[0]["price"]["reason"] == "unit_mismatch"

    def test_both_counts_mentioned_honor_each_no_pend(self):
        # REFINED RULE 1: when the QUERY mentions BOTH counts ("120 caps vs 60
        # caps") -> honor each. Both prices kept at their own count, NEITHER pended
        # (the directive's net-effect change for an explicitly-stated pair).
        pd = [
            _prod("Vit D3 120 caps", 9.0, source_method="page_scrape_jsonld"),
            _prod("Vit D3 60 caps", 5.0, source_method="page_scrape_jsonld"),
        ]
        changed = reconcile_pair_fairness(
            pd, "Vit D3 120 caps vs Vit D3 60 caps", "supplements",
            candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 9.0
        assert pd[1]["price"]["amount"] == 5.0
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"].get("unavailable") is not True

    def test_matched_count_passes_through(self):
        pd = [
            _prod("Vit D3 A 60 caps", 5.0),
            _prod("Vit D3 B 60 caps", 6.0),
        ]
        changed = reconcile_pair_fairness(
            pd, "Vit D3 A vs Vit D3 B", "supplements", candidates_by_name={})
        assert changed is False


class TestReconcileNoUnit:
    @pytest.mark.parametrize("cat", ["fashion", "other"])
    def test_pass_through_untouched(self, cat):
        # unit=None -> NEVER touched, even with wildly different "sizes".
        pd = [
            _prod("Item A", 200.0, specs={"size_options": "S"}),
            _prod("Item B", 250.0, specs={"size_options": "XXL"}),
        ]
        changed = reconcile_pair_fairness(pd, "Item A vs Item B", cat,
                                          candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 200.0
        assert pd[1]["price"]["amount"] == 250.0


# ===========================================================================
# Part 2d — FRAGRANCE BEHAVIOR UNCHANGED through the generalized entry point
# ===========================================================================
class TestFragranceUnchanged:
    def test_outcome1_both_reselect_both_priced(self):
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, source_method="page_scrape_jsonld"),
            _prod("Tom Ford Tobacco Vanille 30 ML", 28.2, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Tom Ford Tobacco Vanille 30 ML": [
                _cand(28.2, title="Tobacco Vanille 30 ML", size="30ml"),
                _cand(118.0, title="Tobacco Vanille 100ml EDP", size="100ml"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "Tom Ford Ombré vs Tobacco Vanille", "fragrances",
            candidates_by_name=cands)
        assert changed is True
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] == 118.0

    def test_outcome2_pend_only_other_keeps_size_mismatch_reason(self):
        # Fragrance pend reason MUST stay "size_mismatch" (FE renders it), NOT the
        # generic "unit_mismatch" — the fragrance path is byte-preserved.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, source_method="page_scrape_jsonld"),
            _prod("Tom Ford Tobacco Vanille 30 ML", 28.2, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Tom Ford Tobacco Vanille 30 ML": [
                _cand(28.2, title="Tobacco Vanille 30 ML", size="30ml"),
                _cand(55.0, title="Tobacco Vanille 50ml", size="50ml"),
            ],
        }
        changed = reconcile_pair_fairness(
            pd, "Tom Ford Ombré vs Tobacco Vanille", "fragrances",
            candidates_by_name=cands)
        assert changed is True
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] is None
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_both_designer_unspecified_converge_unchanged(self):
        # Two unsized designer fragrances both default to 100ml -> pass through.
        pd = [
            _prod("Creed Aventus", 90.0),
            _prod("Tom Ford Oud Wood", 95.0),
        ]
        changed = reconcile_pair_fairness(
            pd, "Creed Aventus vs Tom Ford Oud Wood", "fragrances",
            candidates_by_name={})
        assert changed is False
        assert pd[0]["price"]["amount"] == 90.0
        assert pd[1]["price"]["amount"] == 95.0

    def test_shared_explicit_size_honored_unchanged(self):
        pd = [
            _prod("Dior Sauvage 50ml", 40.0, price_size="50ml"),
            _prod("YSL Y 50ml", 42.0, price_size="50ml"),
        ]
        changed = reconcile_pair_fairness(
            pd, "Dior Sauvage vs YSL Y", "fragrances", candidates_by_name={})
        assert changed is False

    def test_non_dict_product_data_safe(self):
        assert reconcile_pair_fairness(None, "x", "fragrances") is False
        assert reconcile_pair_fairness([{}], "x", "fragrances") is False

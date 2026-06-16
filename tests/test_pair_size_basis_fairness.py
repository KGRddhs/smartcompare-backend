"""ITEM 2 — same/similar SIZE basis across the pair (FAIRNESS).

User principle (explicit): "we always want same or similar sizes for fairness."
A comparison must put both products on a comparable size basis.

BUG: Ombré Leather resolved 100ml @ 80 BHD while Tobacco Vanille resolved
"30 ML" @ 28.2 — an unfair apples-to-oranges pairing. The size divergence came
from the product NAME/variant (one carries "30 ML", the other defaults to
flagship), but reconcile_pair_sizes only compared price.size annotations (often
both None) → "both unknown" → passed the mismatch through.

FIX: derive each product's EFFECTIVE size from ALL signals — product NAME, the
spec volume/concentration, AND price.size — then:
  - same effective size → pass through unchanged.
  - both size-unspecified designer fragrances → converge on the common flagship
    100ml basis (per-product selection already targets 100ml) → pass through.
  - DIFFERENT effective sizes with no safe common basis → mark BOTH price-pending
    (reason="size_mismatch") so no cross-size delta renders.

Run: pytest tests/test_pair_size_basis_fairness.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    reconcile_pair_sizes,
    effective_pair_size_ml,
)


def _prod(name, amount, *, price_size=None, specs=None, source_method="local_bhd",
          title=None):
    price = {
        "amount": amount, "currency": "BHD",
        "source_method": source_method, "size": price_size,
    }
    if title is not None:
        price["title"] = title
    return {
        "name": name, "full_name": name,
        "price": price,
        "best_price": amount,
        "retailer": "someshop.bh",
        "specs": specs or {},
    }


# ============================================================
# effective_pair_size_ml — derive from name / spec / price.size
# ============================================================
class TestEffectiveSize:
    def test_name_derived_size_detected(self):
        # The size lives in the NAME, price.size is None — must still resolve.
        p = _prod("Tom Ford Tobacco Vanille 30 ML", 28.2, price_size=None)
        assert effective_pair_size_ml(p) == 30.0

    def test_spec_volume_derived_size(self):
        p = _prod("Tom Ford Tobacco Vanille", 28.2, price_size=None,
                  specs={"volume": "50 ml"})
        assert effective_pair_size_ml(p) == 50.0

    def test_price_size_still_used(self):
        p = _prod("Some Perfume", 40.0, price_size="75ml")
        assert effective_pair_size_ml(p) == 75.0

    def test_designer_unspecified_defaults_flagship(self):
        # Designer fragrance, no size anywhere → flagship 100ml basis (matches
        # flagship_basis_bonus / the per-product selection convention).
        p = _prod("Tom Ford Ombré Leather", 80.0, price_size=None)
        assert effective_pair_size_ml(p) == 100.0

    def test_non_fragrance_unspecified_is_none(self):
        # A phone has no size basis — None (so two unsized phones stay None==None
        # and never trip the fragrance flagship default).
        p = _prod("iPhone 15 Pro", 400.0, price_size=None)
        assert effective_pair_size_ml(p) is None

    def test_name_precedence_over_spec_and_price(self):
        # NAME size wins when several signals are present (the listing the user
        # actually named is ground truth).
        p = _prod("Creed Aventus 50ml", 90.0, price_size="100ml",
                  specs={"volume": "75ml"})
        assert effective_pair_size_ml(p) == 50.0


# ============================================================
# reconcile_pair_sizes — the Ombré / Tobacco fairness case
# ============================================================
class TestOmbreTobaccoCase:
    def test_name_derived_mismatch_marked_pending(self):
        # THE bug: one product's NAME carries "30 ML", the other defaults to
        # flagship 100ml. price.size is None for BOTH (so the OLD code passed).
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, price_size=None),
            _prod("Tom Ford Tobacco Vanille 30 ML", 28.2, price_size=None),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is True
        for p in pd:
            assert p["price"]["amount"] is None
            assert p["price"]["unavailable"] is True
            assert p["price"]["reason"] == "size_mismatch"

    def test_spec_volume_mismatch_marked_pending(self):
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, specs={"volume": "100ml"}),
            _prod("Tom Ford Tobacco Vanille", 28.2, specs={"volume": "30ml"}),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is True
        assert pd[0]["price"]["amount"] is None
        assert pd[1]["price"]["amount"] is None

    def test_both_designer_unspecified_converge_flagship_unchanged(self):
        # Neither name/spec/price specifies a size → both converge on the common
        # flagship 100ml basis → fair → pass through (no false mismatch).
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, price_size=None),
            _prod("Tom Ford Tobacco Vanille", 90.0, price_size=None),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] == 90.0

    def test_shared_explicit_size_honored_unchanged(self):
        # User explicitly compared the SAME size in both names → honor it.
        pd = [
            _prod("Tom Ford Ombré Leather 50ml", 50.0, price_size=None),
            _prod("Tom Ford Tobacco Vanille 50ml", 55.0, price_size=None),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 50.0
        assert pd[1]["price"]["amount"] == 55.0

    def test_name_size_vs_flagship_default_mismatch(self):
        # One name 100ml explicit, the other name 30ml explicit → mismatch.
        pd = [
            _prod("Tom Ford Ombré Leather 100ml", 80.0, price_size=None),
            _prod("Tom Ford Tobacco Vanille 30ml", 28.2, price_size=None),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is True
        assert pd[0]["price"]["amount"] is None
        assert pd[1]["price"]["amount"] is None


# ============================================================
# Display consistency: spec size + price reflect the SAME size
# ============================================================
class TestDisplaySizeConsistency:
    def test_pending_preserves_each_size_annotation(self):
        # On mismatch, each side's own size annotation is preserved for FE
        # context (the FE can still show the bottle size).
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, price_size="100ml"),
            _prod("Tom Ford Tobacco Vanille", 28.2, price_size="30ml"),
        ]
        reconcile_pair_sizes(pd)
        assert pd[0]["price"].get("size") == "100ml"
        assert pd[1]["price"].get("size") == "30ml"

    def test_non_fragrance_pair_never_tripped(self):
        # Two phones, no size → effective None==None → unchanged (the fragrance
        # flagship default must NOT leak into electronics).
        pd = [
            _prod("iPhone 15 Pro", 400.0, price_size=None),
            _prod("Galaxy S24 Ultra", 450.0, price_size=None),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 400.0
        assert pd[1]["price"]["amount"] == 450.0


# ============================================================
# Regression: existing C2 behavior preserved (price.size path)
# ============================================================
class TestC2BackwardCompat:
    def test_genuinely_same_size_passes_through(self):
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, price_size="100ml"),
            _prod("Creed Aventus", 90.0, price_size="100ml"),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 80.0

    def test_one_side_pending_no_op(self):
        pd = [
            {"name": "A", "full_name": "A", "specs": {},
             "price": {"amount": None, "currency": "BHD", "unavailable": True,
                       "reason": "pending_genuine"}},
            _prod("Creed Aventus 30ml", 90.0, price_size=None),
        ]
        reconcile_pair_sizes(pd)
        assert pd[1]["price"]["amount"] == 90.0

    def test_non_dict_price_safe(self):
        pd = [
            {"name": "A", "full_name": "A", "price": None, "specs": {}},
            _prod("Creed Aventus 30ml", 90.0, price_size=None),
        ]
        reconcile_pair_sizes(pd)  # must not raise
        assert pd[1]["price"]["amount"] == 90.0

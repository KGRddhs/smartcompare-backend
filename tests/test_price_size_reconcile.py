"""Task C2 — consistent size basis (same-size GENUINE re-selection).

BUG: product_0 shows no size, product_1 shows "30 ML" → an apples-to-oranges
price delta + verdict. The orchestrator did NO pair-level size reconciliation.

FIX (current build — same-size GENUINE re-selection): after both products'
prices are resolved (post-selection, pre-scoring), the pair targets a COMMON
size (the user query's explicit size, else the designer-fragrance flagship
100ml). Each product resolves to that target, RE-SELECTING from the candidates
already fetched this request when off-target. Outcome priority:
  1. both reach the target → show both;
  2. only one reaches it → show that one, pend ONLY the other (size_mismatch) —
     a genuine common-basis price is never dropped because its partner can't
     match;
  3. neither → both pending.

Earlier this path marked BOTH pending on ANY size divergence (the conservative
fallback); the assertions below were revised to the improved pend-only-the-
off-basis-side behavior. Re-selection over RETAINED candidates is covered in
test_pair_size_reselection.py.
"""
import pytest

from app.services.price_service import reconcile_pair_sizes


def _prod(name, amount, size, source_method="local_bhd"):
    return {
        "name": name, "full_name": name,
        "price": {
            "amount": amount, "currency": "BHD",
            "source_method": source_method, "size": size,
        },
        "best_price": amount,
        "retailer": "someshop.bh",
    }


def test_off_basis_side_marked_pending_genuine_side_kept():
    # Ombré (designer, no size → flagship 100ml basis) vs Creed (designer, 30ml).
    # Target = flagship 100ml (both designer, no user size). Ombré is already at
    # the target → KEEP its 80; Creed can't reach 100 (no candidates) → pend
    # ONLY Creed. Strictly better than the prior both-pending.
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, None),       # at flagship 100
        _prod("Creed Aventus", 90.0, "30ml"),              # 30ml, off-basis
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"]["amount"] == 80.0                # genuine side kept
    assert pd[0]["price"].get("unavailable") is not True
    assert pd[1]["price"]["amount"] is None                # off-basis pended
    assert pd[1]["price"]["unavailable"] is True
    assert pd[1]["price"]["reason"] == "size_mismatch"


def test_different_explicit_sizes_off_basis_pended():
    # Ombré 100ml (at target) vs Creed 50ml (off target) → pend ONLY Creed.
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, "100ml"),
        _prod("Creed Aventus", 50.0, "50ml"),
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"]["amount"] == 80.0                # 100ml = target, kept
    assert pd[1]["price"]["amount"] is None                # 50ml off-target, pended
    assert pd[1]["price"]["reason"] == "size_mismatch"


def test_neither_at_target_both_pending():
    # Both off the flagship target with no candidate to reach it → both pending
    # (the prior behavior, outcome 3).
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, "50ml"),
        _prod("Creed Aventus", 50.0, "30ml"),
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"]["amount"] is None
    assert pd[1]["price"]["amount"] is None
    assert pd[0]["price"]["reason"] == "size_mismatch"


def test_matched_sizes_unchanged():
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, "100ml"),
        _prod("Creed Aventus", 90.0, "100ml"),
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"]["amount"] == 80.0
    assert pd[1]["price"]["amount"] == 90.0
    assert pd[0]["price"].get("unavailable") is not True


def test_both_sizes_missing_unchanged():
    # Both unsized → no basis to declare a mismatch; leave prices intact.
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, None),
        _prod("Creed Aventus", 90.0, None),
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"]["amount"] == 80.0
    assert pd[1]["price"]["amount"] == 90.0


def test_size_format_whitespace_and_case_normalized():
    # "100 ML" vs "100ml" are the SAME size — must NOT trip the mismatch.
    pd = [
        _prod("A", 80.0, "100 ML"),
        _prod("B", 90.0, "100ml"),
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"]["amount"] == 80.0
    assert pd[1]["price"]["amount"] == 90.0


def test_one_side_already_pending_no_op():
    # If C1 already nulled one price (no amount), there is no cross-size delta
    # risk — reconciliation must leave the genuine side intact.
    pd = [
        {"name": "A", "full_name": "A",
         "price": {"amount": None, "currency": "BHD", "unavailable": True,
                   "reason": "pending_genuine"}},
        _prod("B", 90.0, "30ml"),
    ]
    reconcile_pair_sizes(pd)
    assert pd[1]["price"]["amount"] == 90.0
    assert pd[1]["price"].get("unavailable") is not True


def test_non_dict_price_safe():
    pd = [
        {"name": "A", "full_name": "A", "price": None},
        _prod("B", 90.0, "30ml"),
    ]
    # Must not raise.
    reconcile_pair_sizes(pd)
    assert pd[1]["price"]["amount"] == 90.0


def test_preserves_each_size_for_fe_context():
    pd = [
        _prod("A", 80.0, "100ml"),
        _prod("B", 50.0, "50ml"),
    ]
    reconcile_pair_sizes(pd)
    assert pd[0]["price"].get("size") == "100ml"
    assert pd[1]["price"].get("size") == "50ml"

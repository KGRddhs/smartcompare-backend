"""Task C2 — consistent size basis (conservative fallback).

BUG: product_0 shows no size, product_1 shows "30 ML" → an apples-to-oranges
price delta + verdict. The orchestrator did NO pair-level size reconciliation.

CONSERVATIVE FIX (this build): after both products' prices are resolved
(post-selection, pre-scoring), compare the two price.size annotations. When BOTH
prices are showable but their sizes DIFFER (including one-sized / one-unsized),
we cannot reconcile to a common basis from the cached candidates safely, so we
mark BOTH prices price-pending (reason="size_mismatch") rather than render a
cross-size delta. Matched sizes pass through unchanged.

Candidate re-selection (re-picking a matching-size candidate from
_shopping_items_cache) was deliberately NOT attempted — it re-runs the deep
selection/match/counterfeit/tier logic and is the WS5-deferred work; the
conservative fallback is the lower-risk path blessed by the task.
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


def test_mismatched_sizes_both_marked_pending():
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, None),       # no size
        _prod("Creed Aventus", 90.0, "30ml"),              # 30ml
    ]
    reconcile_pair_sizes(pd)
    for p in pd:
        assert p["price"]["amount"] is None
        assert p["price"]["unavailable"] is True
        assert p["price"]["reason"] == "size_mismatch"


def test_different_explicit_sizes_marked_pending():
    pd = [
        _prod("Tom Ford Ombré Leather", 80.0, "100ml"),
        _prod("Creed Aventus", 50.0, "50ml"),
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

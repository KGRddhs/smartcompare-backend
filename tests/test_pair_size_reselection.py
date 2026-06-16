"""Final fragrance fix — same-size GENUINE re-selection (replaces "both pending").

When the user's QUERY specifies no size, a designer-fragrance pair targets the
flagship 100ml for BOTH products, and each product re-selects its price to that
common size from the candidates ALREADY fetched this request (no new network).

Outcome priority (strictly better than the prior "both pending"):
  1. Both reach the target size genuinely → show BOTH (the win).
  2. Only one reaches the target size → show that one, pend ONLY the other
     (reason="size_mismatch"). Never drop a genuine common-basis price just
     because its partner can't match.
  3. Neither → both pending (the prior behavior).

Two parts under test:
  A. target_pair_size_ml — the target comes from the USER QUERY, not a matched
     listing NAME. No user size → designer-fragrance flagship 100ml. Non-fragrance
     / mixed → None (so electronics never gets a fragrance target).
  B. reselect_to_target_size + reconcile_pair_sizes(user_query, candidates_by_name)
     — re-rank RETAINED genuine candidates to the target size.

Run: pytest tests/test_pair_size_reselection.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    target_pair_size_ml,
    reselect_to_target_size,
    reconcile_pair_sizes,
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


def _cand(amount, *, source_method="page_scrape_jsonld", title=None, retailer="ounass.com",
          size=None, variant_rank=0.0):
    """A retained fan_out / Tier-1 candidate. raw_data carries the actual price
    dict the selection stamps the source_method onto."""
    raw = {
        "amount": amount, "currency": "BHD", "source_method": source_method,
        "retailer": retailer, "url": f"https://{retailer}/p",
        "title": title, "size": size,
    }
    return {
        "value": amount, "rank": 85, "source_method": source_method,
        "retailer": retailer, "variant_rank": variant_rank, "raw_data": raw,
    }


# ============================================================
# A. target_pair_size_ml — target from the USER QUERY, not the matched name
# ============================================================
class TestTargetSize:
    def test_user_query_explicit_size_wins(self):
        # User asked for "50ml" → the target is 50, NOT a matched-name size.
        p0 = _prod("Tom Ford Ombré Leather", 80.0)
        p1 = _prod("Tom Ford Tobacco Vanille 30 ML", 28.2)
        assert target_pair_size_ml("Tom Ford Ombré vs Tobacco 50ml", p0, p1) == 50.0

    def test_no_user_size_designer_pair_defaults_flagship_100(self):
        # No size in the QUERY → designer-fragrance pair targets flagship 100ml,
        # EVEN though one matched NAME carries "30 ML" (that must NOT set target).
        p0 = _prod("Tom Ford Ombré Leather", 80.0)
        p1 = _prod("Tom Ford Tobacco Vanille 30 ML", 28.2)
        assert target_pair_size_ml("Tom Ford Ombré vs Tobacco Vanille", p0, p1) == 100.0

    def test_matched_name_size_does_not_set_target(self):
        # The CORE Part-A requirement: a backend-appended "30 ML" in a product NAME
        # must NOT become the target when the user query said no size.
        p0 = _prod("Creed Aventus 100ml", 90.0)
        p1 = _prod("Tom Ford Tobacco Vanille 30 ML", 28.2)
        # Query has no size → flagship 100, NOT 30 (from the name).
        assert target_pair_size_ml("Creed Aventus vs Tobacco Vanille", p0, p1) == 100.0

    def test_non_fragrance_pair_no_target(self):
        # Two phones, no user size → no fragrance flagship default; None so
        # electronics never gets a target (the existing flagship gate).
        p0 = _prod("iPhone 15 Pro", 400.0)
        p1 = _prod("Galaxy S24 Ultra", 450.0)
        assert target_pair_size_ml("iPhone 15 Pro vs Galaxy S24 Ultra", p0, p1) is None

    def test_mixed_pair_one_fragrance_no_target(self):
        # Only ONE side is a designer fragrance → no shared flagship basis.
        p0 = _prod("Tom Ford Ombré Leather", 80.0)
        p1 = _prod("iPhone 15 Pro", 400.0)
        assert target_pair_size_ml("Tom Ford Ombré vs iPhone 15", p0, p1) is None

    def test_user_size_honored_for_non_fragrance_only_if_present(self):
        # Even for electronics, an explicit user size is a target if present (rare
        # but consistent). Without one → None (above). This guards that the
        # explicit-size branch isn't fragrance-gated.
        p0 = _prod("Some Gadget", 100.0)
        p1 = _prod("Other Gadget", 120.0)
        assert target_pair_size_ml("Some Gadget vs Other Gadget 100ml", p0, p1) == 100.0


# ============================================================
# B1. reselect_to_target_size — pure re-rank over retained candidates
# ============================================================
class TestReselect:
    def test_picks_genuine_candidate_at_target_size(self):
        cands = [
            _cand(28.2, title="Tobacco Vanille 30 ML", size="30ml"),
            _cand(118.0, title="Tobacco Vanille 100ml EDP", size="100ml"),
        ]
        out = reselect_to_target_size("Tom Ford Tobacco Vanille", cands, 100.0)
        assert out is not None
        assert out["amount"] == 118.0
        assert out["source_method"] == "page_scrape_jsonld"

    def test_converted_usd_candidate_acceptable_at_target(self):
        # converted_usd is in the showable set ∪ genuine → acceptable for re-select.
        cands = [
            _cand(150.0, source_method="converted_usd", retailer="someshop.com",
                  title="Tobacco Vanille 100ml", size="100ml"),
        ]
        out = reselect_to_target_size("Tom Ford Tobacco Vanille", cands, 100.0)
        assert out is not None
        assert out["amount"] == 150.0

    def test_rejects_estimated_candidate(self):
        cands = [
            _cand(120.0, source_method="estimated", retailer=None,
                  title="Tobacco Vanille 100ml", size="100ml"),
        ]
        assert reselect_to_target_size("Tom Ford Tobacco Vanille", cands, 100.0) is None

    def test_rejects_implausible_low_fragrance_at_target(self):
        # A "100ml" listing under the full-bottle floor (sample/wrong-SKU) is
        # rejected even though its size matches the target.
        cands = [
            _cand(12.0, title="Tobacco Vanille 100ml", size="100ml"),
        ]
        assert reselect_to_target_size("Tom Ford Tobacco Vanille", cands, 100.0) is None

    def test_no_candidate_at_target_returns_none(self):
        cands = [
            _cand(28.2, title="Tobacco Vanille 30 ML", size="30ml"),
            _cand(55.0, title="Tobacco Vanille 50ml", size="50ml"),
        ]
        assert reselect_to_target_size("Tom Ford Tobacco Vanille", cands, 100.0) is None

    def test_empty_candidates_returns_none(self):
        assert reselect_to_target_size("Tom Ford Tobacco Vanille", [], 100.0) is None
        assert reselect_to_target_size("Tom Ford Tobacco Vanille", None, 100.0) is None

    def test_best_variant_rank_breaks_ties_at_target(self):
        # Two genuine 100ml candidates → higher variant_rank wins.
        cands = [
            _cand(120.0, title="Tobacco Vanille 100ml", size="100ml", variant_rank=0.0),
            _cand(118.0, title="Tobacco Vanille 100ml EDP", size="100ml", variant_rank=1.0),
        ]
        out = reselect_to_target_size("Tom Ford Tobacco Vanille", cands, 100.0)
        assert out["amount"] == 118.0  # variant_rank 1.0 wins over the cheaper 0.0


# ============================================================
# B2. reconcile_pair_sizes — the three outcomes (Tom Ford)
# ============================================================
class TestReconcileOutcomes:
    def test_outcome1_both_reselect_to_target_both_priced(self):
        # THE WIN: Ombré already at flagship 100 (no size), Tobacco latched 30ml
        # but has a genuine 100ml candidate retained → re-select → BOTH priced.
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
        changed = reconcile_pair_sizes(
            pd, user_query="Tom Ford Ombré vs Tobacco Vanille",
            candidates_by_name=cands,
        )
        assert changed is True  # Tobacco's price was swapped
        assert pd[0]["price"]["amount"] == 80.0          # Ombré priced
        assert pd[1]["price"]["amount"] == 118.0         # Tobacco re-selected to 100ml
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"].get("unavailable") is not True

    def test_outcome2_only_one_at_target_pend_only_other(self):
        # Tom Ford FALLBACK: Ombré at flagship 100 (priced), Tobacco can't reach
        # 100 from its candidates → pend ONLY Tobacco; Ombré 80 STILL shows.
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
        changed = reconcile_pair_sizes(
            pd, user_query="Tom Ford Ombré vs Tobacco Vanille",
            candidates_by_name=cands,
        )
        assert changed is True
        assert pd[0]["price"]["amount"] == 80.0          # Ombré STILL priced
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"]["amount"] is None          # Tobacco pended
        assert pd[1]["price"]["unavailable"] is True
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_outcome2_no_candidates_pend_only_off_basis(self):
        # No candidates at all (the conservative path): Ombré at flagship 100,
        # Tobacco 30ml-named → pend ONLY Tobacco. Ombré 80 STILL shows. This is
        # the minimum-level outcome and is strictly better than both-pending.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0),
            _prod("Tom Ford Tobacco Vanille 30 ML", 28.2),
        ]
        changed = reconcile_pair_sizes(pd, user_query="Tom Ford Ombré vs Tobacco Vanille")
        assert changed is True
        assert pd[0]["price"]["amount"] == 80.0          # Ombré STILL priced
        assert pd[1]["price"]["amount"] is None          # Tobacco pended
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_outcome3_neither_at_target_both_pending(self):
        # Both products carry an off-target NAME size and no 100ml candidate →
        # neither reaches the target → both pending (the prior behavior).
        pd = [
            _prod("Tom Ford Ombré Leather 50ml", 50.0),
            _prod("Tom Ford Tobacco Vanille 30 ML", 28.2),
        ]
        changed = reconcile_pair_sizes(pd, user_query="Tom Ford Ombré vs Tobacco Vanille")
        assert changed is True
        assert pd[0]["price"]["amount"] is None
        assert pd[1]["price"]["amount"] is None
        assert pd[0]["price"]["reason"] == "size_mismatch"
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_both_at_target_noop(self):
        # Both already at flagship 100 (no size) → fair → pass through.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0),
            _prod("Tom Ford Tobacco Vanille", 90.0),
        ]
        changed = reconcile_pair_sizes(pd, user_query="Tom Ford Ombré vs Tobacco Vanille")
        assert changed is False
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] == 90.0

    def test_non_fragrance_never_tripped_with_query(self):
        # Two phones + no user size → no target → legacy effective-size path →
        # None==None → no-op. The fragrance flagship default must NOT leak.
        pd = [
            _prod("iPhone 15 Pro", 400.0),
            _prod("Galaxy S24 Ultra", 450.0),
        ]
        changed = reconcile_pair_sizes(pd, user_query="iPhone 15 Pro vs Galaxy S24 Ultra")
        assert changed is False
        assert pd[0]["price"]["amount"] == 400.0
        assert pd[1]["price"]["amount"] == 450.0

    def test_user_explicit_size_both_reselect(self):
        # User asked for 50ml; both have a genuine 50ml candidate → both re-select
        # to 50ml and show.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, source_method="page_scrape_jsonld"),
            _prod("Tom Ford Tobacco Vanille", 90.0, source_method="page_scrape_jsonld"),
        ]
        cands = {
            "Tom Ford Ombré Leather": [
                _cand(80.0, title="Ombré Leather 100ml", size="100ml"),
                _cand(45.0, title="Ombré Leather 50ml", size="50ml"),
            ],
            "Tom Ford Tobacco Vanille": [
                _cand(90.0, title="Tobacco Vanille 100ml", size="100ml"),
                _cand(60.0, title="Tobacco Vanille 50ml", size="50ml"),
            ],
        }
        changed = reconcile_pair_sizes(
            pd, user_query="Tom Ford Ombré vs Tobacco Vanille 50ml",
            candidates_by_name=cands,
        )
        assert changed is True
        assert pd[0]["price"]["amount"] == 45.0
        assert pd[1]["price"]["amount"] == 60.0


# ============================================================
# B3. Backward-compat — the no-arg signature still works (no query/candidates)
# ============================================================
class TestNoArgBackwardCompat:
    def test_two_phones_no_args_noop(self):
        pd = [
            _prod("iPhone 15 Pro", 400.0),
            _prod("Galaxy S24 Ultra", 450.0),
        ]
        # No user_query, no candidates — legacy effective-size path.
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 400.0

    def test_designer_pair_no_args_uses_flagship_target(self):
        # Even with NO user_query, a designer-fragrance pair derives the flagship
        # target from the products themselves (both designer → 100ml), so the
        # off-basis side is pended (outcome 2), not both.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0),
            _prod("Tom Ford Tobacco Vanille 30 ML", 28.2),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is True
        assert pd[0]["price"]["amount"] == 80.0   # Ombré priced
        assert pd[1]["price"]["amount"] is None    # Tobacco pended only

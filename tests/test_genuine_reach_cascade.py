"""WS-3 — Genuine-reach in the price cascade (CDE-3 + DM-3 + CDE-4).

Three independent fixes, all in app/services/structured_comparison_service.py:

CDE-3 — seed self._price_candidates on each NON-cache short-circuit path with the
  FULL viable candidate set the path observed (Tier-1 Serper Shopping items /
  Shopify alternates / Algolia alternates), normalized to the fan_out candidate
  shape reconcile_pair_fairness/reselect_to_target_value expect. A WINNER-ONLY
  seed is a NO-OP (Open Question Q2) — a single short-circuit price has ONE size,
  so reconcile either passes it through at-tolerance (seed unused) or needs a
  DIFFERENT candidate at the target. The test pins that the FULL set is seeded.

DM-3 — bh["organic"][:4] -> [:8] domain-diversity lever (Open Question Q8): the
  limit=8 discovery queries up to 8 distinct BH registry domains; top-4 are often
  1-2 dominant domains, so genuine PDPs from the other queried domains land at
  positions 5-8 and were silently dropped. The downstream weight>=1.5 / variant /
  review-only gates still reject noise at the new positions.

CDE-4 — don't 30d-negative-cache a guard-rejected estimate: when a real candidate
  was DROPPED this request by is_implausible_high_value_price /
  is_implausible_low_fragrance_price (a wrong-cheap accessory / sample leak), the
  Tier-3 estimate that follows is NOT a structural genuine-BH dead-end — it's a
  transient guard reject. 30d-sentineling it would suppress a later-correct PDP
  for 30 days. So the estimate negcache is capped to 24h (PRICE_CACHE_TTL) when
  the guard fired. The converted_usd negcache path (SF-1) is untouched.

Run: pytest tests/test_genuine_reach_cascade.py -v
"""
import os
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.structured_comparison_service import StructuredComparisonService
from app.services.price_service import (
    reconcile_pair_fairness,
    PRICE_CACHE_TTL,
    NEGATIVE_PRICE_CACHE_TTL,
)


# ---------------------------------------------------------------------------
# shared fixtures — mirror the candidate shape from test_pair_size_reselection
# ---------------------------------------------------------------------------
def _prod(name, amount, *, price_size=None, source_method="page_scrape_jsonld",
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
        "specs": {},
    }


def _shopping_item(title, price_str, source="alhajis.com", link=None):
    """A raw Serper Shopping item as it sits in self._shopping_items_cache."""
    return {
        "title": title,
        "price": price_str,
        "source": source,
        "link": link or f"https://{source}/p",
    }


def _shopify_result(amount, title, retailer="asgharali.com", size=None,
                    source_method="shopify_json"):
    """A parsed Shopify/Algolia alternate (a price dict)."""
    return {
        "amount": amount, "currency": "BHD",
        "source_method": source_method, "retailer": retailer,
        "url": f"https://{retailer}/p", "title": title, "size": size,
    }


# ===========================================================================
# CDE-3 — short-circuit seeds the FULL candidate set (not the winner)
# ===========================================================================
class TestCDE3SeedsFullSet:
    def test_cde3_tier1_shortcircuit_seeds_candidates(self):
        """Fragrance pair, A wins via Tier-1 short-circuit holding 50ml AND 100ml
        shopping_items, common target 100ml -> A NOT pended (re-selected) where a
        winner-only seed (50ml) would have pended it."""
        svc = StructuredComparisonService()
        full_name = "Tom Ford Tobacco Vanille"
        # The path observed BOTH a 50ml and a 100ml genuine listing; the winner
        # short-circuit returned only ONE (say the 50ml). The FULL set must seed.
        svc._shopping_items_cache[full_name] = [
            _shopping_item("Tom Ford Tobacco Vanille 50ml EDP", "BHD 60.0"),
            _shopping_item("Tom Ford Tobacco Vanille 100ml EDP", "BHD 118.0"),
        ]
        svc._seed_shortcircuit_candidates(
            full_name, kind="tier1_shopping", currency="BHD",
        )
        seeded = svc._price_candidates.get(full_name) or []
        sizes = {c.get("size") for c in seeded}
        # PROOF the full set seeded, not just the winner: BOTH sizes present.
        assert "50ml" in sizes and "100ml" in sizes, (
            f"expected both 50ml+100ml candidates seeded, got sizes={sizes}"
        )
        # Each carries raw_data (so the genuine source_method survives the
        # is_price_showable gate during re-selection).
        assert all(isinstance(c.get("raw_data"), dict) for c in seeded)
        assert all(c["raw_data"].get("source_method") == "local_bhd" for c in seeded)

        # End-to-end: with the FULL set seeded, reconcile re-selects A to the 100ml
        # target -> A priced (NOT pended). A winner-only seed would have pended it.
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0),                  # at flagship 100
            _prod(full_name, 60.0, price_size="50ml"),              # latched 50ml
        ]
        changed = reconcile_pair_fairness(
            pd, "Tom Ford Ombré vs Tobacco Vanille", "fragrances",
            candidates_by_name=svc._price_candidates,
        )
        assert changed is True
        assert pd[1]["price"]["amount"] == 118.0          # re-selected to 100ml
        assert pd[1]["price"].get("unavailable") is not True

    def test_cde3_tier1_seed_rejects_wrong_variant_alternate(self):
        """WS-3 reviewer gate-fix: the tier1_shopping seed applies the SKU-match
        gate (shopping_listing_matches), so a wrong model-line variant
        ("iPhone 15 Pro Max" under an "iPhone 15" query) is NOT retained in the
        re-selection pool. is_price_showable checks price plausibility, NOT SKU
        match, so without the gate the Pro Max alternate (at a plausible price)
        could be re-selected as the iPhone 15's price = wrong-SKU attribution."""
        svc = StructuredComparisonService()
        full_name = "Apple iPhone 15"
        svc._shopping_items_cache[full_name] = [
            _shopping_item("Apple iPhone 15 128GB", "BHD 320.0", source="sharafdg.com"),
            _shopping_item("Apple iPhone 15 Pro Max 256GB", "BHD 480.0", source="sharafdg.com"),
        ]
        svc._seed_shortcircuit_candidates(
            full_name, kind="tier1_shopping", currency="BHD",
        )
        titles = [c.get("title") or "" for c in (svc._price_candidates.get(full_name) or [])]
        assert any("iPhone 15 128GB" in t for t in titles), titles      # correct base variant retained
        assert not any("Pro Max" in t for t in titles), titles          # wrong variant rejected

    def test_cde3_single_candidate_still_pends_honestly(self):
        """A holds only a 100ml short-circuit price, target 50ml, no 50ml candidate
        -> still pends (G1: no fabrication). Documents the residual."""
        svc = StructuredComparisonService()
        full_name = "Tom Ford Tobacco Vanille"
        svc._shopping_items_cache[full_name] = [
            _shopping_item("Tom Ford Tobacco Vanille 100ml EDP", "BHD 118.0"),
        ]
        svc._seed_shortcircuit_candidates(
            full_name, kind="tier1_shopping", currency="BHD",
        )
        # only the 100ml candidate is real — nothing to fabricate a 50ml from.
        pd = [
            _prod("Tom Ford Ombré Leather", 45.0, price_size="50ml"),
            _prod(full_name, 118.0, price_size="100ml"),
        ]
        changed = reconcile_pair_fairness(
            pd, "Tom Ford Ombré vs Tobacco Vanille 50ml", "fragrances",
            candidates_by_name=svc._price_candidates,
        )
        # Target = user's explicit 50ml; Tobacco has no 50ml candidate -> pend it.
        assert changed is True
        assert pd[1]["price"]["amount"] is None
        assert pd[1]["price"]["unavailable"] is True
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_cde3_at_target_shortcircuit_noop(self):
        """A's price already at target -> no re-selection, byte-identical price
        (tolerance pass-through regression guard)."""
        svc = StructuredComparisonService()
        a, b = "Tom Ford Ombré Leather", "Tom Ford Tobacco Vanille"
        svc._shopping_items_cache[a] = [
            _shopping_item("Tom Ford Ombré Leather 100ml EDP", "BHD 80.0"),
        ]
        svc._shopping_items_cache[b] = [
            _shopping_item("Tom Ford Tobacco Vanille 100ml EDP", "BHD 90.0"),
        ]
        svc._seed_shortcircuit_candidates(a, kind="tier1_shopping", currency="BHD")
        svc._seed_shortcircuit_candidates(b, kind="tier1_shopping", currency="BHD")
        pd = [
            _prod(a, 80.0, price_size="100ml"),
            _prod(b, 90.0, price_size="100ml"),
        ]
        changed = reconcile_pair_fairness(
            pd, "Tom Ford Ombré vs Tobacco Vanille", "fragrances",
            candidates_by_name=svc._price_candidates,
        )
        assert changed is False                       # both already at 100ml
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] == 90.0

    def test_cde3_no_seed_on_cache_hit_documented(self):
        """L1/L2/negative cache-hit path remains un-seeded (documented residual,
        not a regression): _seed_shortcircuit_candidates is never called on a cache
        hit because the path observed NO live candidate set. We assert the absence
        of a seed for a name whose cache the path served."""
        svc = StructuredComparisonService()
        full_name = "Cached Product"
        # A cache hit never populates _shopping_items_cache with live items AND
        # never calls the seed helper. The candidate map stays empty for that name.
        assert svc._price_candidates.get(full_name) is None

    def test_cde3_shopify_seeds_all_alternates(self):
        """Shopify short-circuit seeds ALL parsed alternates, not just shop_best."""
        svc = StructuredComparisonService()
        full_name = "Creed Aventus"
        alternates = [
            _shopify_result(90.0, "Creed Aventus 50ml", size="50ml"),
            _shopify_result(150.0, "Creed Aventus 100ml", size="100ml"),
        ]
        svc._seed_shortcircuit_candidates(
            full_name, kind="price_dicts", currency="BHD", price_dicts=alternates,
        )
        seeded = svc._price_candidates.get(full_name) or []
        sizes = {c.get("size") for c in seeded}
        assert "50ml" in sizes and "100ml" in sizes
        assert all(c["raw_data"].get("source_method") == "shopify_json" for c in seeded)

    def test_cde3_gates_unshowable_candidates(self):
        """G3 — a sample/estimated/non-genuine item is NOT seeded (is_price_showable
        gate). A designer-fragrance sample under the floor must not enter the pool."""
        svc = StructuredComparisonService()
        full_name = "Tom Ford Tobacco Vanille"
        svc._shopping_items_cache[full_name] = [
            # a genuine 100ml full bottle (kept)
            _shopping_item("Tom Ford Tobacco Vanille 100ml EDP", "BHD 118.0"),
            # an implausibly-low 100ml (sample/decant leak) — must be gated out
            _shopping_item("Tom Ford Tobacco Vanille 100ml", "BHD 9.0"),
        ]
        svc._seed_shortcircuit_candidates(
            full_name, kind="tier1_shopping", currency="BHD",
        )
        seeded = svc._price_candidates.get(full_name) or []
        amounts = {c["raw_data"].get("amount") for c in seeded}
        assert 118.0 in amounts
        assert 9.0 not in amounts, "sample-floor leak was seeded (G3 violation)"

    def test_cde3_seed_is_fail_open(self):
        """A malformed observed set must never raise (fail-open try/except)."""
        svc = StructuredComparisonService()
        # garbage shopping items + None price_dicts must be swallowed.
        svc._shopping_items_cache["X"] = [{"no_price": True}, None, 42]
        svc._seed_shortcircuit_candidates("X", kind="tier1_shopping", currency="BHD")
        svc._seed_shortcircuit_candidates("Y", kind="price_dicts", currency="BHD",
                                          price_dicts=None)
        # no exception; nothing meaningful seeded.
        assert svc._price_candidates.get("X", []) == []


# ===========================================================================
# DM-3 — bh["organic"][:4] -> [:8] domain-diversity harvest
# ===========================================================================
class TestDM3Window:
    @staticmethod
    def _organic_with_pdp_at(position, pdp_link, pdp_title, *, noise_title="iPhone 15"):
        """8 bahrain organic results: 1-based `position` carries a genuine PDP,
        all others are off-registry noise (score_source 0.5 < 1.5 threshold)."""
        organic = []
        for i in range(8):
            if i + 1 == position:
                organic.append({"link": pdp_link, "title": pdp_title})
            else:
                organic.append(
                    {"link": f"https://random-noise-{i}.com/p/x", "title": noise_title}
                )
        return {"bahrain": {"organic": organic}}

    def test_dm3_harvests_bh_pdp_at_position_5_8(self):
        """A genuine registry PDP at position 6 (weight>=1.5) is harvested post-fix
        — pre-fix the [:4] window dropped it. Real registry domain (lulu = 3.0)."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        rbt = self._organic_with_pdp_at(
            6, "https://gcc.luluhypermarket.com/p/iphone-15-256gb",
            "iPhone 15 256GB",
        )
        out = _harvest_candidate_urls(rbt, None, "electronics", query_name="iPhone 15")
        links = [link for (link, _lbl, _route, _w) in out]
        assert "https://gcc.luluhypermarket.com/p/iphone-15-256gb" in links, (
            "DM-3: position-6 genuine registry PDP was not harvested"
        )

    def test_dm3_position_5_8_noise_rejected(self):
        """An off-registry marketplace URL (weight<1.5) at position 6 is still
        rejected at the widened window — the weight>=1.5 gate holds."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        rbt = self._organic_with_pdp_at(
            6, "https://random-marketplace-xyz.com/p/iphone-15", "iPhone 15 256GB",
        )
        out = _harvest_candidate_urls(rbt, None, "electronics", query_name="iPhone 15")
        assert out == [], "DM-3: off-registry noise at position 6 was harvested"

    def test_dm3_variant_mismatch_still_rejected_in_window(self):
        """A position-7 'iPhone 15 Pro Max' PDP for an 'iPhone 15' query is rejected
        by variant_mismatch even though it's now in-window and on-registry."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        rbt = self._organic_with_pdp_at(
            7, "https://www.sharafdg.com/product/iphone-15-pro-max",
            "iPhone 15 Pro Max 256GB",
        )
        out = _harvest_candidate_urls(rbt, None, "electronics", query_name="iPhone 15")
        assert out == [], "DM-3: a wrong-variant PDP slipped through the window"

    def test_dm3_position_4_still_harvested_regression(self):
        """A registry PDP at position 4 (in-window pre AND post fix) is unaffected
        — the widening is strictly additive."""
        from app.services.structured_comparison_service import _harvest_candidate_urls
        rbt = self._organic_with_pdp_at(
            4, "https://www.sharafdg.com/product/iphone-15", "iPhone 15 256GB",
        )
        out = _harvest_candidate_urls(rbt, None, "electronics", query_name="iPhone 15")
        links = [link for (link, _lbl, _route, _w) in out]
        assert "https://www.sharafdg.com/product/iphone-15" in links

    def test_dm3_window_is_eight_not_four_source_guard(self):
        """Source-level anchor: the bahrain organic slice is [:8], not [:4]."""
        import inspect
        from app.services import structured_comparison_service as scs_mod
        full_src = inspect.getsource(scs_mod)
        assert 'bh["organic"][:8]' in full_src or "bh['organic'][:8]" in full_src
        assert 'bh["organic"][:4]' not in full_src and "bh['organic'][:4]" not in full_src


# ===========================================================================
# CDE-4 — don't 30d-negcache a guard-rejected estimate
# ===========================================================================
class TestCDE4NegcacheSkip:
    def test_cde4_guard_reject_caps_negcache_ttl(self):
        """When a guard rejected a real candidate this request, the Tier-3 estimate
        negcache TTL is capped to 24h (PRICE_CACHE_TTL), NOT the 30d sentinel."""
        svc = StructuredComparisonService()
        est = {"amount": 250.0, "currency": "BHD", "source_method": "estimated",
               "estimated": True}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache"
        ) as mock_set, patch(
            "app.services.structured_comparison_service.should_negative_cache",
            return_value=True,
        ):
            svc._record_negative_price_cache(
                "k", est, guard_rejected=True,
            )
            assert mock_set.called
            _key, _price, ttl = mock_set.call_args[0]
            assert ttl == PRICE_CACHE_TTL, (
                f"guard-rejected estimate negcache TTL must be 24h, got {ttl}"
            )
            assert ttl != NEGATIVE_PRICE_CACHE_TTL

    def test_cde4_genuine_structural_miss_still_negcaches_30d(self):
        """fan_out genuinely empty (no winner, no guard reject) -> Tier-3 estimate
        -> 30d sentinel IS written (Task 1.3 preserved — don't over-correct)."""
        svc = StructuredComparisonService()
        est = {"amount": 250.0, "currency": "BHD", "source_method": "estimated",
               "estimated": True}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache"
        ) as mock_set, patch(
            "app.services.structured_comparison_service.should_negative_cache",
            return_value=True,
        ):
            svc._record_negative_price_cache("k", est)  # guard_rejected default False
            assert mock_set.called
            _key, _price, ttl = mock_set.call_args[0]
            assert ttl == NEGATIVE_PRICE_CACHE_TTL

    def test_cde4_converted_path_unchanged(self):
        """A parked converted_fallback resolving -> should_negative_cache still
        False -> no sentinel at all (SF-1 regression guard, byte-identical)."""
        svc = StructuredComparisonService()
        converted = {"amount": 244.99, "currency": "BHD",
                     "source_method": "converted_usd"}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache"
        ) as mock_set:
            # real should_negative_cache: converted_usd -> False -> never writes.
            svc._record_negative_price_cache("k", converted, guard_rejected=True)
            assert not mock_set.called, (
                "converted_usd must NEVER be negcached regardless of guard_rejected"
            )

    def test_cde4_guard_rejected_param_optional(self):
        """The new guard_rejected kwarg is optional (call sites that don't pass it
        keep the 30d default) — backward-compat."""
        import inspect
        from app.services.structured_comparison_service import StructuredComparisonService as S
        sig = inspect.signature(S._record_negative_price_cache)
        assert "guard_rejected" in sig.parameters
        assert sig.parameters["guard_rejected"].default is False

    def test_cde4_later_correct_pdp_not_suppressed_30d(self):
        """The MECHANISM by which a later-correct PDP isn't suppressed for 30d: a
        guard-rejected estimate is sentineled for at most 24h (PRICE_CACHE_TTL),
        which is < 30d — so the cascade re-runs (and a now-valid PDP can win) far
        sooner than the structural-miss path. Pins the TTL relation, not Redis."""
        svc = StructuredComparisonService()
        est = {"amount": 250.0, "currency": "BHD", "source_method": "estimated",
               "estimated": True}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache"
        ) as mock_set, patch(
            "app.services.structured_comparison_service.should_negative_cache",
            return_value=True,
        ):
            svc._record_negative_price_cache("k", est, guard_rejected=True)
            _key, _price, ttl = mock_set.call_args[0]
            assert ttl < NEGATIVE_PRICE_CACHE_TTL, (
                "a guard-rejected estimate must NOT hold the 30d sentinel — a later "
                "correct PDP would be suppressed"
            )
            assert ttl == PRICE_CACHE_TTL

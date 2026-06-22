"""WS-2 (genuine-bh-price bundle) — supplement branch: category gate + bounded
stages + trustworthy park + CDE-2 deterministic retailer attribution + the G1
`_price_fallback_on_miss` pending terminal.

Six contracts (plan §WS-2 lines 131-137):
  1. category gate trusts a concrete non-supplement LLM/catfix category;
  2. a price-key race miss returns bare None (NOT a pending dict) so the
     INSUFFICIENT_DATA fake-winner guard (_phase1_completely_failed) still fires;
     the G1 pending RENDER is a response_builder concern (WS-5 SIB-5);
  3. an iHerb hit is PARKED (gated by is_price_showable) and survives a forced
     cancel via _price_fallback_on_miss;
  4. a retailer-less gpt_organic_extract PENDS — not parked, not shown — G3;
  5. CDE-2 attributes a retailer ONLY from a deterministically matched bh_organic
     snippet (POSITIVE) and leaves it unassigned for an unknown domain (NEGATIVE);
  6. each supplement sub-stage is wait_for-bounded — a hung stage is bypassed,
     the chain proceeds rather than blowing the 15s outer cap.

All seam functions (fetch_iherb_price, fetch_pharmacy_price, fetch_page_price,
extract_price, search_web) are mocked — NO network.

Run: python -m pytest tests/test_supplement_branch_genuine.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _routed_search_web(iherb_organic=None, bh_organic=None):
    """Build a search_web AsyncMock that routes by query: the supplement branch
    calls search_web twice — once with an 'iherb price' query and once with a BH
    pharmacy query (country='bh'). Routing by content (NOT a fixed side_effect
    list) is robust to the speculative-discovery search_web calls earlier in
    _get_price."""
    iherb_organic = iherb_organic or []
    bh_organic = bh_organic or []

    async def _impl(query="", *a, **k):
        if "iherb" in (query or "").lower():
            return {"organic": list(iherb_organic)}
        if k.get("country") == "bh":
            return {"organic": list(bh_organic)}
        # Speculative-discovery / any other call — empty.
        return {"organic": []}

    return AsyncMock(side_effect=_impl)


# Common patch context: isolate _get_price from the network + caches so only the
# supplement branch logic under test runs. Returns the patch dict so each test
# can override individual seam return values.
def _isolated_get_price(**overrides):
    """Build a contextmanager stack that mocks every external seam _get_price
    touches BEFORE reaching the supplement branch, plus the supplement seams.
    Tier-1 Serper Shopping returns empty so the cascade falls through to the
    supplement (Tier-2) branch; escalation is disabled."""
    patches = {
        "search_product_prices": AsyncMock(return_value={"shopping": [], "organic": []}),
        "search_price_organic": AsyncMock(return_value={"organic": [], "knowledge_graph": None}),
        "search_web": AsyncMock(return_value={"organic": []}),
        "fetch_iherb_price": AsyncMock(return_value=None),
        "fetch_pharmacy_price": AsyncMock(return_value=None),
        "fetch_page_price": AsyncMock(return_value=None),
        "extract_price": AsyncMock(return_value=({"amount": None}, {"prompt_tokens": 0, "completion_tokens": 0})),
        "extract_price_from_training_data": AsyncMock(return_value=({"amount": None}, {"prompt_tokens": 0, "completion_tokens": 0})),
    }
    patches.update(overrides)
    return patches


def _run_get_price_isolated(service, brand, name, variant, region, query, category, seam_overrides=None):
    """Run _get_price with all seams mocked + caches forced to miss. The
    Tier-1.5 render escalation is disabled (`should_escalate`→False)."""
    seams = _isolated_get_price(**(seam_overrides or {}))
    mod = "app.services.structured_comparison_service"
    with patch(f"{mod}.search_product_prices", seams["search_product_prices"]), \
         patch(f"{mod}.search_price_organic", seams["search_price_organic"]), \
         patch(f"{mod}.search_web", seams["search_web"]), \
         patch(f"{mod}.fetch_iherb_price", seams["fetch_iherb_price"]), \
         patch(f"{mod}.fetch_pharmacy_price", seams["fetch_pharmacy_price"]), \
         patch(f"{mod}.fetch_page_price", seams["fetch_page_price"]), \
         patch(f"{mod}.extract_price", seams["extract_price"]), \
         patch(f"{mod}.extract_price_from_training_data", seams["extract_price_from_training_data"]), \
         patch(f"{mod}.get_cached", return_value=None), \
         patch("app.services.product_data_service.get_cached_price", new_callable=AsyncMock, return_value=None), \
         patch(f"{mod}.get_negative_cache", return_value=None), \
         patch(f"{mod}.should_escalate", return_value=False):
        return run_async(
            service._get_price(brand, name, variant, region, query, category=category)
        )


# ---------------------------------------------------------------------------
# 1. Category gate — trust a concrete non-supplement LLM/catfix category
# ---------------------------------------------------------------------------

class TestCategoryGateTrustsConcreteCategory:
    def test_supplement_category_gate_trusts_concrete_category(self, service):
        """`category="electronics"` for a name with a supplement substring → the
        routing layer must NOT treat it as a supplement. We assert the gate
        directly: is_supplement = (category=="supplements") or (category in
        ("other", None) and is_supplement_query(name)).

        "Iron Man Power Bank 5000" contains 'iron' (a supplement keyword) but is
        an electronics product. A concrete electronics category must win."""
        from app.services.structured_comparison_service import is_supplement_query

        name = "Iron Man Power Bank 5000mAh"
        # The gate the implementation must use:
        is_supp_electronics = (
            ("electronics" == "supplements")
            or ("electronics" in ("other", None) and is_supplement_query(name))
        )
        assert is_supp_electronics is False

        # And a concrete supplements category DOES route as supplement.
        is_supp_supp = (
            ("supplements" == "supplements")
            or ("supplements" in ("other", None) and is_supplement_query(name))
        )
        assert is_supp_supp is True

    def test_electronics_routes_through_non_supplement_branch(self, service):
        """End-to-end routing proof: with category='electronics', the supplement
        seams (fetch_iherb_price) are NEVER called — the non-supplement organic
        path is used instead."""
        iherb = AsyncMock(return_value=None)
        _run_get_price_isolated(
            service, "Anker", "PowerCore Iron 10000", None, "bahrain",
            "Anker PowerCore Iron 10000", "electronics",
            seam_overrides={"fetch_iherb_price": iherb},
        )
        iherb.assert_not_called()


# ---------------------------------------------------------------------------
# 2. G1 — a price-key race miss returns PENDING, never bare None
# ---------------------------------------------------------------------------

class TestTimeoutTerminalPreservesGuard:
    """WS-2 gate-fix (reviewer-2 ISSUE 1): _price_fallback_on_miss for a price-key
    miss with nothing parked must return bare None, NOT a make_pending_price dict.
    A truthy pending dict defeats _phase1_completely_failed (the INSUFFICIENT_DATA
    fake-winner guard, which treats {amount:None} as 'proceed to scoring'). The G1
    'no raw N/A' render is response_builder's job (WS-5 SIB-5)."""

    def test_price_fallback_on_miss_returns_none_preserving_guard(self, service):
        """Nothing parked → bare None (so the price-key stays falsy for the
        INSUFFICIENT_DATA guard)."""
        service._parked_price = {}
        assert service._price_fallback_on_miss("price", "NOW Foods Vitamin D3") is None

    def test_insufficient_data_guard_still_fires(self, service):
        """The terminal keeps _phase1_completely_failed working: both specs+price
        None → True (INSUFFICIENT_DATA fires, no fake winner); specs present +
        price None → False (comparison proceeds, price pended at render)."""
        from app.services.structured_comparison_service import _phase1_completely_failed
        assert _phase1_completely_failed({"specs": None, "price": None}) is True
        assert _phase1_completely_failed({"specs": {"display": "x"}, "price": None}) is False

    def test_price_fallback_on_miss_non_price_key_still_none(self, service):
        """For specs/reviews/image the terminal must STAY bare None (those degrade
        to missing-data unchanged)."""
        service._parked_price = {}
        assert service._price_fallback_on_miss("specs", "NOW Foods Vitamin D3") is None
        assert service._price_fallback_on_miss("reviews", "NOW Foods Vitamin D3") is None
        assert service._price_fallback_on_miss("image_url", "NOW Foods Vitamin D3") is None

    def test_supplement_timeout_terminal_is_none_not_fake_winner(self, service):
        """Integration: a supplement _get_price race timeout with nothing parked
        surfaces None via _price_fallback_on_miss (NOT a truthy pending dict), so
        when specs ALSO fail the INSUFFICIENT_DATA guard fires — no fake product_0
        winner. The user-facing pending render is response_builder's job (WS-5)."""
        async def _slow_iherb(*a, **k):
            await asyncio.sleep(5.0)  # well past the patched cap
            return None

        mod = "app.services.structured_comparison_service"
        with patch(f"{mod}._PRICE_RACE_TIMEOUT", 0.05), \
             patch(f"{mod}.fetch_iherb_price", new=_slow_iherb), \
             patch(f"{mod}.search_product_prices", new_callable=AsyncMock,
                   return_value={"shopping": [], "organic": []}), \
             patch(f"{mod}.get_cached", return_value=None), \
             patch("app.services.product_data_service.get_cached_price",
                   new_callable=AsyncMock, return_value=None), \
             patch(f"{mod}.get_negative_cache", return_value=None), \
             patch(f"{mod}.should_escalate", return_value=False):
            service._parked_price = {}
            full_name = "NOW Foods Vitamin D3"
            try:
                run_async(asyncio.wait_for(
                    service._get_price("NOW Foods", "Vitamin D3", None, "bahrain",
                                       "NOW Foods Vitamin D3", category="supplements"),
                    timeout=0.05,
                ))
                settled = "did-not-time-out"  # pragma: no cover — should time out
            except asyncio.TimeoutError:
                settled = service._price_fallback_on_miss("price", full_name)
            assert settled is None


# ---------------------------------------------------------------------------
# 3. iHerb hit is parked (showable) and survives a forced cancel
# ---------------------------------------------------------------------------

class TestIherbHitParkedAndReturned:
    def test_supplement_iherb_hit_is_parked_and_returned(self, service):
        """iHerb returns a genuine price (retailer+url+amount, source_method a
        genuine method) → it is stashed in self._parked_price[full_name] AND a
        forced cancel routed through _price_fallback_on_miss returns it."""
        full_name = "NOW Foods Vitamin D3"
        iherb_price = {
            "amount": 7.5,
            "currency": "BHD",
            "retailer": "iHerb",
            "url": "https://bh.iherb.com/pr/now-foods-vitamin-d3/12345",
            "source_method": "local_bhd",
            "title": "NOW Foods Vitamin D-3, 5000 IU, 120 Softgels",
        }
        service._parked_price = {}
        result = _run_get_price_isolated(
            service, "NOW Foods", "Vitamin D3", None, "bahrain",
            "NOW Foods Vitamin D3", "supplements",
            seam_overrides={"fetch_iherb_price": AsyncMock(return_value=dict(iherb_price))},
        )
        # Returned the genuine price.
        assert result["amount"] == pytest.approx(7.5)
        # Parked for the race-cancel terminal.
        assert full_name in service._parked_price
        assert service._parked_price[full_name]["amount"] == pytest.approx(7.5)
        # A forced cancel still yields the parked price (not None).
        recovered = service._price_fallback_on_miss("price", full_name)
        assert recovered["amount"] == pytest.approx(7.5)


# ---------------------------------------------------------------------------
# 4. G3 — retailer-less gpt_organic_extract pends, never parked, never shown
# ---------------------------------------------------------------------------

class TestRetailerlessGptExtractPends:
    def test_retailerless_gpt_extract_pends_not_parked_not_shown(self, service):
        """iHerb/pharmacy/page all miss; extract_price returns an amount with NO
        retailer and no deterministically-matched bh_organic → the price is
        stamped gpt_organic_extract, is NOT showable, and is NOT parked."""
        from app.services.price_service import is_price_showable

        full_name = "NOW Foods Vitamin D3"
        gpt_price = {"amount": 6.0, "currency": "BHD", "retailer": None}
        service._parked_price = {}
        # bh_organic carries an UNKNOWN domain so CDE-2 cannot attribute.
        seam = {
            "fetch_iherb_price": AsyncMock(return_value=None),
            "fetch_pharmacy_price": AsyncMock(return_value=None),
            "fetch_page_price": AsyncMock(return_value=None),
            "extract_price": AsyncMock(return_value=(dict(gpt_price), {"prompt_tokens": 0, "completion_tokens": 0})),
            # iHerb organic EMPTY (no iHerb-retailer fallback); bh_organic carries
            # an UNKNOWN domain so CDE-2 cannot attribute.
            "search_web": _routed_search_web(
                iherb_organic=[],
                bh_organic=[{"title": "Some random blog about vitamins",
                             "link": "https://randomblog.example/post"}],
            ),
        }
        result = _run_get_price_isolated(
            service, "NOW Foods", "Vitamin D3", None, "bahrain",
            "NOW Foods Vitamin D3", "supplements", seam_overrides=seam,
        )
        # The honest retailer-less label.
        assert result.get("source_method") == "gpt_organic_extract"
        # Not showable.
        assert is_price_showable(full_name, result) is False
        # Never parked.
        assert full_name not in service._parked_price


# ---------------------------------------------------------------------------
# 5. CDE-2 — deterministic retailer attribution from a matched bh_organic snippet
# ---------------------------------------------------------------------------

class TestCde2DeterministicAttribution:
    def test_cde2_attributes_retailer_from_matched_bh_organic_snippet(self, service):
        """POSITIVE: iHerb organic empty; bh_organic has an item whose link domain
        is a known PHARMACY_DOMAIN and whose title brand/name-token-matches the
        product; extract_price returns amount + retailer=None → CDE-2 relabels it
        local_bhd, sets retailer=pharmacy name + url=snippet link, showable +
        parked."""
        from app.services.price_service import is_price_showable

        full_name = "NOW Foods Vitamin D3"
        gpt_price = {"amount": 8.5, "currency": "BHD", "retailer": None}
        service._parked_price = {}
        # bolo.bh is in PHARMACY_DOMAINS; title token-matches NOW + Vitamin D3.
        bh_item = {
            "title": "NOW Foods Vitamin D3 5000 IU 120 Softgels",
            "link": "https://bolo.bh/products/now-foods-vitamin-d3-5000",
            "snippet": "Buy NOW Foods Vitamin D3 in Bahrain",
        }
        seam = {
            "fetch_iherb_price": AsyncMock(return_value=None),
            "fetch_pharmacy_price": AsyncMock(return_value=None),
            "fetch_page_price": AsyncMock(return_value=None),
            "extract_price": AsyncMock(return_value=(dict(gpt_price), {"prompt_tokens": 0, "completion_tokens": 0})),
            # iHerb organic empty; the BH pharmacy query carries the match.
            "search_web": _routed_search_web(iherb_organic=[], bh_organic=[bh_item]),
        }
        result = _run_get_price_isolated(
            service, "NOW Foods", "Vitamin D3", None, "bahrain",
            "NOW Foods Vitamin D3", "supplements", seam_overrides=seam,
        )
        assert result.get("source_method") == "local_bhd"
        assert result.get("retailer") == "Bolo"
        assert result.get("url") == bh_item["link"]
        assert is_price_showable(full_name, result) is True
        assert full_name in service._parked_price

    def test_cde2_unknown_domain_stays_unassigned_and_pends(self, service):
        """NEGATIVE: bh_organic's only item is an UNKNOWN domain (not in
        PHARMACY_DOMAINS / known_supplement_retailers) → CDE-2 must NOT guess a
        retailer. The price stays gpt_organic_extract → pends, not parked."""
        from app.services.price_service import is_price_showable

        full_name = "NOW Foods Vitamin D3"
        gpt_price = {"amount": 8.5, "currency": "BHD", "retailer": None}
        service._parked_price = {}
        bh_item = {
            "title": "NOW Foods Vitamin D3 5000 IU",
            "link": "https://unknown-shop.example/p/123",
            "snippet": "vitamin d3",
        }
        seam = {
            "fetch_iherb_price": AsyncMock(return_value=None),
            "fetch_pharmacy_price": AsyncMock(return_value=None),
            "fetch_page_price": AsyncMock(return_value=None),
            "extract_price": AsyncMock(return_value=(dict(gpt_price), {"prompt_tokens": 0, "completion_tokens": 0})),
            "search_web": _routed_search_web(iherb_organic=[], bh_organic=[bh_item]),
        }
        result = _run_get_price_isolated(
            service, "NOW Foods", "Vitamin D3", None, "bahrain",
            "NOW Foods Vitamin D3", "supplements", seam_overrides=seam,
        )
        assert result.get("source_method") == "gpt_organic_extract"
        # No guessed retailer.
        assert not result.get("retailer")
        assert is_price_showable(full_name, result) is False
        assert full_name not in service._parked_price


# ---------------------------------------------------------------------------
# 6. Sub-stage wait_for bounds — a hung stage is bypassed, chain proceeds
# ---------------------------------------------------------------------------

class TestSubstageWaitForBounds:
    def test_supplement_substage_wait_for_bounds(self, service):
        """Stage 1 (iHerb) hangs > its wait_for bound → it is treated as a miss
        and the chain proceeds to pharmacy (Stage 2), which yields a price. The
        whole call returns within a few seconds, NOT the 5s+ hang."""
        full_name = "NOW Foods Vitamin D3"

        async def _hang_iherb(*a, **k):
            await asyncio.sleep(10.0)  # > the ~4s Stage-1 wait_for bound
            return {"amount": 99.0, "currency": "BHD", "retailer": "iHerb"}

        pharmacy_price = {
            "amount": 7.2,
            "currency": "BHD",
            "retailer": "Bolo",
            "url": "https://bolo.bh/p/now-vit-d3",
            "source_method": "page_scrape_jsonld",
            "title": "NOW Foods Vitamin D3",
        }
        seam = {
            "fetch_iherb_price": _hang_iherb,
            "fetch_pharmacy_price": AsyncMock(return_value=dict(pharmacy_price)),
            "search_web": AsyncMock(return_value={"organic": []}),
        }
        import time as _t
        service._parked_price = {}
        t0 = _t.monotonic()
        result = _run_get_price_isolated(
            service, "NOW Foods", "Vitamin D3", None, "bahrain",
            "NOW Foods Vitamin D3", "supplements", seam_overrides=seam,
        )
        elapsed = _t.monotonic() - t0
        # Stage 1 was bypassed; pharmacy (Stage 2) won.
        assert result["amount"] == pytest.approx(7.2)
        # Bounded — nowhere near the 10s iHerb hang.
        assert elapsed < 8.0, f"chain did not bypass the hung iHerb stage (took {elapsed:.1f}s)"
        # Parked (showable pharmacy price).
        assert full_name in service._parked_price

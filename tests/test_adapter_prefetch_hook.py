"""WS-3d — wire the bolo (sitemap) + nasser (json_api) genuine-BHD adapters into
the FREE direct-prefetch slot of _get_price (app/services/structured_comparison_
service.py), mirroring the Shopify/Algolia speculative-prefetch pattern.

Contract pinned here:
  - The non-supplement prefetch slot fires fetch_bolo_price (for a category bolo
    serves, via get_sitemap_sources_for_category) and fetch_nasser_price (via
    get_jsonapi_sources_for_category), in the same ensure_future/gather shape as
    the Shopify/Algolia prefetch.
  - A genuine BHD adapter hit SHORT-CIRCUITS _get_price (it never falls to a GPT
    estimate / converted_usd) and the resolved price is RETURNED.
  - The resolved price (and its observed alternates) reaches
    self._price_candidates so reconcile_pair_fairness / _select_best see it.
  - CRITICAL — SUPPLEMENTS ARE COVERED. bolo + nasser BOTH serve supplements;
    the new selectors do NOT inherit the `not is_supplement` gate that the
    Shopify/Algolia prefetch carries. A supplement compare MUST reach the bolo +
    nasser adapters (an explicit supplement Stage-1.5 between iHerb and pharmacy).
  - CANCELLATION — an unused (no-hit) prefetched adapter future is cancelled at
    the end of the path (no orphan HTTP task survives), exactly like the
    Shopify/Algolia speculative fetches.

All network is monkeypatched (NO live network). Run:
  pytest tests/test_adapter_prefetch_hook.py -v
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
import pytest
from unittest.mock import patch


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------
def _genuine_bolo(amount=8.16, title="elf SuperHydrate Moisturizer"):
    """A genuine page_scrape_jsonld bolo.bh price dict (what fetch_bolo_price
    returns on a hit)."""
    return {
        "amount": amount, "currency": "BHD", "retailer": "bolo.bh",
        "url": "https://www.bolo.bh/products/X-elf-superhydrate",
        "in_stock": True, "confidence": 1.0, "estimated": False,
        "source_method": "page_scrape_jsonld", "title": title,
    }


def _genuine_nasser(amount=13.341, title="Cerave Foaming Cleanser 473ml"):
    """A genuine local_bhd nasserpharmacy.com price dict (what fetch_nasser_price
    returns on a hit)."""
    return {
        "amount": amount, "currency": "BHD", "retailer": "nasserpharmacy.com",
        "url": "https://www.nasserpharmacy.com/bh-en/cerave-foaming-cleanser",
        "in_stock": True, "confidence": 1.0, "estimated": False,
        "source_method": "local_bhd", "title": title,
    }


def _stub_common(scs, svc, monkeypatch):
    """Stub the shared cascade so _get_price reaches the prefetch + escalation /
    supplement Stage-1.5 without touching the network. Caller still installs the
    adapter stubs + the escalation/discovery gate."""
    # No cache / DB / negative-cache so the live cascade runs.
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)

    async def _no_db_price(*a, **k):
        return None
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _no_db_price,
        raising=False,
    )

    # Save-to-db is fire-and-forget — no-op it.
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)


# --------------------------------------------------------------------------
@pytest.mark.asyncio
class TestNonSupplementAdapterHook:
    async def test_bolo_sitemap_hit_short_circuits_and_seeds(self, monkeypatch):
        """A makeup query → the sitemap prefetch fires fetch_bolo_price; a genuine
        page_scrape_jsonld hit short-circuits _get_price and seeds _price_candidates."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        _stub_common(scs, svc, monkeypatch)

        # bolo serves makeup; nasser too. Force escalation; kill Shopify/Algolia.
        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

        # Tier-1 Serper shopping → no price (forces escalation cleanly).
        async def no_shopping(*a, **k):
            return {"shopping": [], "organic": [], "shopping_region": "bahrain"}
        monkeypatch.setattr(scs, "search_product_prices", no_shopping)

        bolo_calls = {"n": 0}
        async def fake_bolo(product_name, currency="BHD"):
            bolo_calls["n"] += 1
            return _genuine_bolo()
        async def fake_nasser(product_name, currency="BHD"):
            return None
        monkeypatch.setattr(scs, "fetch_bolo_price", fake_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", fake_nasser, raising=False)

        # Discovery must NOT be reached — adapter short-circuit precedes it.
        async def boom_search(*a, **k):
            raise AssertionError("discovery reached — bolo did not short-circuit")
        monkeypatch.setattr(scs, "search_web", boom_search)

        price = await svc._get_price(
            brand="elf", name="SuperHydrate Moisturizer", variant=None,
            region="bahrain", search_query="elf SuperHydrate Moisturizer",
            nocache=True, category="makeup",
        )
        assert bolo_calls["n"] >= 1, "fetch_bolo_price was never called"
        assert price is not None
        assert price["source_method"] == "page_scrape_jsonld"
        assert abs(price["amount"] - 8.16) < 0.01
        assert price["retailer"] == "bolo.bh"

        # The resolved genuine price reached the per-request candidate pool.
        seeded = svc._price_candidates.get("elf SuperHydrate Moisturizer") or []
        assert any(
            (c.get("raw_data") or {}).get("source_method") == "page_scrape_jsonld"
            and abs((c.get("value") or 0) - 8.16) < 0.01
            for c in seeded
        ), f"genuine bolo price did not reach _price_candidates: {seeded!r}"

    async def test_nasser_jsonapi_hit_short_circuits(self, monkeypatch):
        """A makeup query, bolo misses but nasser hits → the json_api adapter wins."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        _stub_common(scs, svc, monkeypatch)

        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

        async def no_shopping(*a, **k):
            return {"shopping": [], "organic": [], "shopping_region": "bahrain"}
        monkeypatch.setattr(scs, "search_product_prices", no_shopping)

        async def fake_bolo(product_name, currency="BHD"):
            return None
        nasser_calls = {"n": 0}
        async def fake_nasser(product_name, currency="BHD"):
            nasser_calls["n"] += 1
            return _genuine_nasser()
        monkeypatch.setattr(scs, "fetch_bolo_price", fake_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", fake_nasser, raising=False)

        async def boom_search(*a, **k):
            raise AssertionError("discovery reached — nasser did not short-circuit")
        monkeypatch.setattr(scs, "search_web", boom_search)

        price = await svc._get_price(
            brand="Cerave", name="Foaming Cleanser", variant="473ml",
            region="bahrain", search_query="Cerave Foaming Cleanser 473ml",
            nocache=True, category="makeup",
        )
        assert nasser_calls["n"] >= 1, "fetch_nasser_price was never called"
        assert price is not None
        assert price["source_method"] == "local_bhd"
        assert abs(price["amount"] - 13.341) < 0.01
        assert price["retailer"] == "nasserpharmacy.com"

    async def test_adapter_miss_falls_through_to_discovery(self, monkeypatch):
        """Both adapters miss → the cascade continues to Serper discovery (not
        short-circuited) and the unused futures are cancelled (no orphan)."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        _stub_common(scs, svc, monkeypatch)

        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

        async def no_shopping(*a, **k):
            return {"shopping": [], "organic": [], "shopping_region": "bahrain"}
        monkeypatch.setattr(scs, "search_product_prices", no_shopping)

        async def fake_bolo(product_name, currency="BHD"):
            return None
        async def fake_nasser(product_name, currency="BHD"):
            return None
        monkeypatch.setattr(scs, "fetch_bolo_price", fake_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", fake_nasser, raising=False)

        reached = {"discovery": False}
        async def marker_search(*a, **k):
            reached["discovery"] = True
            return {"organic": [], "shopping": []}
        monkeypatch.setattr(scs, "search_web", marker_search)
        # The organic Tier-2 GPT path must not crash the fall-through.
        async def no_organic(*a, **k):
            return {"organic": [], "knowledge_graph": None}
        monkeypatch.setattr(scs, "search_price_organic", no_organic, raising=False)

        await svc._get_price(
            brand="elf", name="SuperHydrate Moisturizer", variant=None,
            region="bahrain", search_query="elf SuperHydrate Moisturizer",
            nocache=True, category="makeup",
        )
        assert reached["discovery"] is True, (
            "adapters returned None but the cascade did not fall through to discovery"
        )


# --------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSupplementAdapterCoverage:
    """The KEYSTONE of WS-3d: bolo + nasser cover SUPPLEMENTS, so the supplement
    branch MUST reach the new adapters (NOT gated out by `not is_supplement`)."""

    async def test_supplement_reaches_bolo_and_nasser(self, monkeypatch):
        """A SUPPLEMENT compare reaches fetch_bolo_price + fetch_nasser_price (the
        un-gate proof). A genuine nasser hit short-circuits with local_bhd."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        _stub_common(scs, svc, monkeypatch)

        # iHerb + pharmacy + page-scrape all miss → the supplement cascade must
        # reach the new Stage-1.5 adapters.
        async def no_iherb(*a, **k):
            return None
        monkeypatch.setattr(scs, "fetch_iherb_price", no_iherb, raising=False)
        async def no_pharmacy(*a, **k):
            return None
        monkeypatch.setattr(scs, "fetch_pharmacy_price", no_pharmacy, raising=False)

        async def no_search_web(*a, **k):
            return {"organic": [], "shopping": []}
        monkeypatch.setattr(scs, "search_web", no_search_web)

        bolo_calls = {"n": 0}
        nasser_calls = {"n": 0}
        async def fake_bolo(product_name, currency="BHD"):
            bolo_calls["n"] += 1
            return None
        async def fake_nasser(product_name, currency="BHD"):
            nasser_calls["n"] += 1
            return _genuine_nasser(
                amount=13.341, title="NOW Foods Vitamin D3 5000 IU 240 Softgels",
            )
        monkeypatch.setattr(scs, "fetch_bolo_price", fake_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", fake_nasser, raising=False)

        price = await svc._get_price(
            brand="NOW Foods", name="Vitamin D3 5000 IU", variant="240 Softgels",
            region="bahrain", search_query="NOW Foods Vitamin D3 5000 IU 240 Softgels",
            nocache=True, category="supplements",
        )
        # BOTH adapters were reached on the supplement path (the un-gate proof).
        assert bolo_calls["n"] >= 1, (
            "SUPPLEMENT compare did NOT reach fetch_bolo_price — the adapter is "
            "still gated out by `not is_supplement`"
        )
        assert nasser_calls["n"] >= 1, (
            "SUPPLEMENT compare did NOT reach fetch_nasser_price — the adapter is "
            "still gated out by `not is_supplement`"
        )
        # The genuine nasser hit short-circuits the supplement cascade.
        assert price is not None
        assert price["source_method"] == "local_bhd"
        assert price["retailer"] == "nasserpharmacy.com"

    async def test_supplement_bolo_hit_short_circuits_and_seeds(self, monkeypatch):
        """A supplement compare where bolo (sitemap) hits first → page_scrape_jsonld
        short-circuit + the genuine price reaches _price_candidates."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        _stub_common(scs, svc, monkeypatch)

        async def no_iherb(*a, **k):
            return None
        monkeypatch.setattr(scs, "fetch_iherb_price", no_iherb, raising=False)
        async def no_pharmacy(*a, **k):
            return None
        monkeypatch.setattr(scs, "fetch_pharmacy_price", no_pharmacy, raising=False)
        async def no_search_web(*a, **k):
            return {"organic": [], "shopping": []}
        monkeypatch.setattr(scs, "search_web", no_search_web)

        full = "Garden of Life Vitamin Code Raw 120 Capsules"
        async def fake_bolo(product_name, currency="BHD"):
            return _genuine_bolo(amount=22.5, title=full)
        async def fake_nasser(product_name, currency="BHD"):
            return None
        monkeypatch.setattr(scs, "fetch_bolo_price", fake_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", fake_nasser, raising=False)

        price = await svc._get_price(
            brand="Garden of Life", name="Vitamin Code Raw", variant="120 Capsules",
            region="bahrain", search_query=full,
            nocache=True, category="supplements",
        )
        assert price is not None
        assert price["source_method"] == "page_scrape_jsonld"
        assert price["retailer"] == "bolo.bh"
        seeded = svc._price_candidates.get(full) or []
        assert any(
            (c.get("raw_data") or {}).get("source_method") == "page_scrape_jsonld"
            for c in seeded
        ), f"genuine bolo supplement price did not reach _price_candidates: {seeded!r}"


# --------------------------------------------------------------------------
@pytest.mark.asyncio
class TestPrefetchCancellation:
    async def test_unused_prefetched_adapter_futures_are_cancelled(self, monkeypatch):
        """When an adapter prefetch is fired but a genuine Tier-1 price wins before
        escalation (no adapter consumption), the speculative adapter futures must be
        cancelled — no orphan HTTP task survives the request."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        _stub_common(scs, svc, monkeypatch)

        # bolo serves makeup → the prefetch fires the adapters. But a genuine
        # Tier-1 Serper Shopping price wins immediately (no escalation), so the
        # speculative adapter futures are never consumed → must be cancelled.
        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: False)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

        async def shopping_with_price(*a, **k):
            return {
                "shopping": [{
                    "title": "elf SuperHydrate Moisturizer",
                    "price": "BHD 8.50", "source": "bolo.bh",
                    "link": "https://www.bolo.bh/p",
                }],
                "organic": [], "shopping_region": "bahrain",
            }
        monkeypatch.setattr(scs, "search_product_prices", shopping_with_price)

        started = {"bolo": False, "nasser": False}
        cancelled = {"bolo": False, "nasser": False}

        async def slow_bolo(product_name, currency="BHD"):
            started["bolo"] = True
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled["bolo"] = True
                raise
            return None
        async def slow_nasser(product_name, currency="BHD"):
            started["nasser"] = True
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled["nasser"] = True
                raise
            return None
        monkeypatch.setattr(scs, "fetch_bolo_price", slow_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", slow_nasser, raising=False)

        async def boom_search(*a, **k):
            raise AssertionError("discovery reached — Tier-1 did not short-circuit")
        monkeypatch.setattr(scs, "search_web", boom_search)

        price = await svc._get_price(
            brand="elf", name="SuperHydrate Moisturizer", variant=None,
            region="bahrain", search_query="elf SuperHydrate Moisturizer",
            nocache=True, category="makeup",
        )
        assert price is not None  # Tier-1 shopping price won
        # Let the cancelled-task callbacks run.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        # The speculative adapter futures were fired then cancelled (no orphan).
        if started["bolo"]:
            assert cancelled["bolo"], "orphan bolo prefetch survived (not cancelled)"
        if started["nasser"]:
            assert cancelled["nasser"], "orphan nasser prefetch survived (not cancelled)"


# --------------------------------------------------------------------------
# Wave-3c — per-domain sitemap dispatch (_sitemap_fetch_coro)
# --------------------------------------------------------------------------
class TestSitemapPerDomainDispatch:
    """The sitemap prefetch dispatches by s.domain to the correct per-domain
    adapter — bolo.bh → fetch_bolo_price, boutiqaat.com → fetch_boutiqaat_price.
    A single hardcoded fetcher would mis-route boutiqaat through bolo's index."""

    def test_dispatch_routes_each_domain_to_its_own_fetcher(self, monkeypatch):
        import app.services.structured_comparison_service as scs
        calls = {"bolo": 0, "boutiqaat": 0}

        async def fake_bolo(name, currency="BHD"):
            calls["bolo"] += 1
            return None

        async def fake_boutiqaat(name, currency="BHD"):
            calls["boutiqaat"] += 1
            return None

        monkeypatch.setattr(scs, "fetch_bolo_price", fake_bolo, raising=False)
        monkeypatch.setattr(scs, "fetch_boutiqaat_price", fake_boutiqaat, raising=False)

        coro_bolo = scs._sitemap_fetch_coro("bolo.bh", "X", "BHD")
        coro_bq = scs._sitemap_fetch_coro("www.boutiqaat.com", "X", "BHD")  # www. + case-insensitive
        assert coro_bolo is not None and coro_bq is not None
        asyncio.get_event_loop().run_until_complete(asyncio.gather(coro_bolo, coro_bq))
        assert calls == {"bolo": 1, "boutiqaat": 1}

    def test_dispatch_unmapped_domain_returns_none(self, monkeypatch):
        import app.services.structured_comparison_service as scs
        assert scs._sitemap_fetch_coro("unknown.example", "X", "BHD") is None


# --------------------------------------------------------------------------
# Codex HIGH-4 — PER-SOURCE adapter timeout. One slow adapter coro in a gather
# must NOT discard another's already-completed valid result. The fix wraps each
# coro with `_timeout_none(coro, _ADAPTER_TIMEOUT)` BEFORE gathering, so a slow
# sibling resolves to None instead of collapsing the whole gather via a single
# outer wait_for.
# --------------------------------------------------------------------------
@pytest.mark.asyncio
class TestPerSourceAdapterTimeout:
    async def test_slow_source_does_not_discard_fast_source_result(self, monkeypatch):
        """source A (bolo) returns a valid 12.5 BHD dict immediately; source B
        (boutiqaat) sleeps past the timeout. The per-source-wrapped gather RETAINS
        bolo's 12.5 result (was: the single outer wait_for discarded BOTH)."""
        import app.services.structured_comparison_service as scs

        # Shrink the per-source timeout so the test runs fast (the slow source
        # sleeps well past it; the fast source resolves instantly).
        monkeypatch.setattr(scs, "_ADAPTER_TIMEOUT", 0.1, raising=False)

        async def fast_bolo(product_name, currency="BHD"):
            return _genuine_bolo(amount=12.5, title=product_name)

        async def slow_boutiqaat(product_name, currency="BHD"):
            await asyncio.sleep(30)  # never resolves within the per-source timeout
            return _genuine_bolo(amount=99.0, title=product_name)

        # Build the SAME gather composition the prefetch builds — each adapter
        # wrapped with the per-source `_timeout_none` via a ZERO-ARG FACTORY
        # (Codex MEDIUM re-review) so a slow sibling → None and no orphan coro is
        # created on a pre-run cancel.
        coros = [
            scs._timeout_none(lambda: fast_bolo("X Moisturizer"), scs._ADAPTER_TIMEOUT),
            scs._timeout_none(lambda: slow_boutiqaat("X Moisturizer"), scs._ADAPTER_TIMEOUT),
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

        # The fast source's valid result SURVIVED; the slow one yielded None.
        observed = [
            r for r in results
            if isinstance(r, dict) and r.get("amount") and r["amount"] > 0
        ]
        assert len(observed) == 1, (
            f"fast source result was discarded by the slow sibling: {results!r}"
        )
        assert abs(observed[0]["amount"] - 12.5) < 0.01
        assert observed[0]["retailer"] == "bolo.bh"
        # The slow source resolved to None (not an exception, not a hang).
        assert results[1] is None

    async def test_old_single_outer_wait_for_discards_fast_source_CONTROL(self):
        """CONTROL (Codex HIGH-4): reproduce the ORIGINAL bug to prove the fix is
        necessary and to catch a revert of the call sites back to bare coros under a
        single collapsing wait_for. The OLD composition — gather(*bare_coros) under
        ONE outer wait_for(timeout) — loses a COMPLETED fast result when a sibling
        overruns, because wait_for cancels the WHOLE gather on timeout."""
        async def fast_bolo():
            return {"amount": 12.5, "retailer": "bolo.bh"}

        async def slow_boutiqaat():
            await asyncio.sleep(30)
            return {"amount": 99.0, "retailer": "boutiqaat.com"}

        # OLD pattern: bare coros, single collapsing outer wait_for.
        observed = []
        try:
            old_results = await asyncio.wait_for(
                asyncio.gather(fast_bolo(), slow_boutiqaat(), return_exceptions=True),
                timeout=0.1,
            )
            observed = [r for r in old_results if isinstance(r, dict) and r.get("amount")]
        except asyncio.TimeoutError:
            observed = []  # the whole gather was cancelled — fast result LOST
        assert observed == [], (
            "CONTROL expected the OLD single-wait_for composition to DISCARD the "
            "fast source — if this now retains it, the bug is gone for another reason "
            "and this control is stale."
        )

        # NEW pattern: each adapter per-source-wrapped via a FACTORY → the fast
        # result survives.
        import app.services.structured_comparison_service as scs
        new_results = await asyncio.gather(
            scs._timeout_none(lambda: fast_bolo(), 0.1),
            scs._timeout_none(lambda: slow_boutiqaat(), 0.1),
            return_exceptions=True,
        )
        new_observed = [r for r in new_results if isinstance(r, dict) and r.get("amount")]
        assert len(new_observed) == 1 and abs(new_observed[0]["amount"] - 12.5) < 0.01

    async def test_timeout_none_returns_value_on_completion(self, monkeypatch):
        """`_timeout_none` is transparent for a coro that completes inside the
        timeout — it returns the underlying value unchanged."""
        import app.services.structured_comparison_service as scs

        async def quick():
            return {"amount": 7.0, "retailer": "bolo.bh"}

        out = await scs._timeout_none(lambda: quick(), 1.0)
        assert out == {"amount": 7.0, "retailer": "bolo.bh"}

    async def test_timeout_none_returns_none_on_slow(self, monkeypatch):
        """`_timeout_none` returns None (never raises) when the coro overruns the
        per-source timeout — and cancels the underlying coro (no orphan)."""
        import app.services.structured_comparison_service as scs

        cancelled = {"v": False}

        async def slow():
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled["v"] = True
                raise
            return {"amount": 1.0}

        out = await scs._timeout_none(lambda: slow(), 0.05)
        assert out is None
        # wait_for cancels the underlying coro on timeout — no orphan task.
        await asyncio.sleep(0)
        assert cancelled["v"] is True


# --------------------------------------------------------------------------
# Codex re-review #2/#3 M4 — adapter cancellation must NOT leak coroutines.
# `_timeout_none` takes a ZERO-ARG FACTORY (NOT an eager coroutine) AND the
# _get_price prefetch CALL SITES pass `lambda: adapter(...)`, so the adapter
# coroutine is created LAZILY inside the _timeout_none task body. When the
# speculative gather is cancelled BEFORE its bodies run (genuine Tier-1 short-
# circuit → `_cancel_prefetched_direct`), no adapter coroutine is ever created →
# no orphan, no "coroutine was never awaited" RuntimeWarning.
#
# DISCRIMINATION (Codex re-review #3 NIT): the OLD tests built their OWN gather
# of lazy lambdas, so they only re-tested the convention the TEST supplied and
# passed against an EAGER source revert (an eager `_timeout_none(coro, t)` never
# calls its first arg either → the factory-counter stayed 0; a test-supplied
# lambda is never a coro → the warning never fired). The discriminating test
# must observe the SOURCE's own `_timeout_none` call sites, so these drive the
# REAL `_get_price` construction+cancel path.
# --------------------------------------------------------------------------
@pytest.mark.asyncio
class TestAdapterCancellationNoOrphan:
    async def _drive_genuine_tier1_cancel(self, scs, svc, monkeypatch):
        """Run the genuine-Tier-1 short-circuit: Serper Shopping returns a genuine
        BHD price and escalation is OFF, so the speculative bolo/boutiqaat/nasser
        adapter prefetch is FIRED then CANCELLED before consumption (the
        `_cancel_prefetched_direct` path). Adapters are slow stubs that would leak
        if created eagerly then cancelled pre-run. Returns the resolved Tier-1
        price (mirrors test_unused_prefetched_adapter_futures_are_cancelled)."""
        _stub_common(scs, svc, monkeypatch)
        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: False)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

        async def shopping_with_price(*a, **k):
            return {
                "shopping": [{
                    "title": "elf SuperHydrate Moisturizer",
                    "price": "BHD 8.50", "source": "bolo.bh",
                    "link": "https://www.bolo.bh/p",
                }],
                "organic": [], "shopping_region": "bahrain",
            }
        monkeypatch.setattr(scs, "search_product_prices", shopping_with_price)

        async def slow_adapter(product_name, currency="BHD"):
            await asyncio.sleep(30)
            return None
        monkeypatch.setattr(scs, "fetch_bolo_price", slow_adapter, raising=False)
        monkeypatch.setattr(scs, "fetch_boutiqaat_price", slow_adapter, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", slow_adapter, raising=False)

        async def boom_search(*a, **k):
            raise AssertionError("discovery reached — Tier-1 did not short-circuit")
        monkeypatch.setattr(scs, "search_web", boom_search)

        return await svc._get_price(
            brand="elf", name="SuperHydrate Moisturizer", variant=None,
            region="bahrain", search_query="elf SuperHydrate Moisturizer",
            nocache=True, category="makeup",
        )

    async def test_prefetch_wraps_adapters_in_lazy_factory_not_eager_coro(self, monkeypatch):
        """DETERMINISTIC discriminator — spy on `_timeout_none` and assert every
        adapter the prefetch wraps is passed as a ZERO-ARG CALLABLE (a lazy
        factory), NEVER an already-created coroutine. An eager-coroutine source
        revert (`_timeout_none(adapter(...), t)` / `_timeout_none(_sitemap_fetch_
        coro(...), t)`) makes `asyncio.iscoroutine(arg)` True here → FAILS. The
        capture is SYNCHRONOUS at construction, so the verdict is independent of
        task scheduling (the flaw that made the old factory-counter non-
        discriminating)."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()

        captured = []
        real_timeout_none = scs._timeout_none

        def spy_timeout_none(make_coro, timeout=scs._ADAPTER_TIMEOUT):
            captured.append({
                "callable": callable(make_coro),
                "is_coroutine": asyncio.iscoroutine(make_coro),
            })
            return real_timeout_none(make_coro, timeout)
        monkeypatch.setattr(scs, "_timeout_none", spy_timeout_none)

        price = await self._drive_genuine_tier1_cancel(scs, svc, monkeypatch)
        assert price is not None  # Tier-1 shopping price won
        # The prefetch DID wrap adapters (bolo/boutiqaat via sitemap, nasser via
        # json_api) — otherwise there is nothing to discriminate.
        assert captured, "the prefetch wrapped no adapter in _timeout_none"
        # Every wrapped adapter is a lazy factory, NOT an eager coroutine.
        eager = [c for c in captured if c["is_coroutine"] or not c["callable"]]
        assert not eager, (
            f"an adapter was passed to _timeout_none as an EAGER coroutine instead "
            f"of a zero-arg factory ({len(eager)}/{len(captured)}) — a pre-run "
            f"cancel would orphan it ('coroutine was never awaited')"
        )

    async def test_lazy_factory_contract_holds_on_adapter_miss_cancel_path(self, monkeypatch):
        """Second real cancel TRIGGER — both adapters MISS so the cascade falls
        through to discovery and `_cancel_prefetched_direct` runs on that path too.
        The same `_timeout_none` spy proves the lazy-factory contract holds there
        as well (deterministic; the un-reliable deferred-GC 'never awaited' symptom
        can't be captured in-test — the cancelled-task machinery holds the coros
        past any in-test gc.collect — so we assert the construction-time contract
        on a second path instead of the flaky symptom)."""
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()

        captured = []
        real_timeout_none = scs._timeout_none

        def spy_timeout_none(make_coro, timeout=scs._ADAPTER_TIMEOUT):
            captured.append(asyncio.iscoroutine(make_coro) or not callable(make_coro))
            return real_timeout_none(make_coro, timeout)
        monkeypatch.setattr(scs, "_timeout_none", spy_timeout_none)

        _stub_common(scs, svc, monkeypatch)
        monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
        monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
        monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

        async def no_shopping(*a, **k):
            return {"shopping": [], "organic": [], "shopping_region": "bahrain"}
        monkeypatch.setattr(scs, "search_product_prices", no_shopping)

        async def miss_adapter(product_name, currency="BHD"):
            return None
        monkeypatch.setattr(scs, "fetch_bolo_price", miss_adapter, raising=False)
        monkeypatch.setattr(scs, "fetch_boutiqaat_price", miss_adapter, raising=False)
        monkeypatch.setattr(scs, "fetch_nasser_price", miss_adapter, raising=False)

        # Discovery returns nothing → graceful pending; the prefetch is consumed
        # then the (missed) futures are cancelled. No live network.
        async def empty_search(*a, **k):
            return {"organic": [], "shopping": []}
        monkeypatch.setattr(scs, "search_web", empty_search)

        await svc._get_price(
            brand="elf", name="SuperHydrate Moisturizer", variant=None,
            region="bahrain", search_query="elf SuperHydrate Moisturizer",
            nocache=True, category="makeup",
        )
        assert captured, "the prefetch wrapped no adapter in _timeout_none"
        assert not any(captured), (
            "an adapter was passed to _timeout_none as an EAGER coroutine instead "
            "of a zero-arg factory on the adapter-miss cancel path"
        )

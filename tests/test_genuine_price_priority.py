"""GENUINE-PRICE DETERMINISM (fix-ladder item 1) — ENABLE_GENUINE_PRICE_PRIORITY.

Build spec: recon_determinism.json (2026-07-01 lane recon). The structural root:
ALL genuine price tiers run SEQUENTIALLY inside ONE 15s cap (_PRICE_RACE_TIMEOUT)
and NO upstream sub-timeout is deadline-aware — a slow Tier-1 serper shopping /
shopify / algolia / adapter consume / discovery wait can eat the whole budget
before the genuine fan_out even starts; the outer Phase-1 wait_for then cancels
_get_price mid-flight and the handler serves the parked converted_usd — "parked
converted wins over an in-flight genuine curl".

THE FIX (flag ENABLE_GENUINE_PRICE_PRIORITY, default OFF — ships DORMANT):
  (a) a per-call race deadline + _pre_reserve_remaining() clamps at every
      upstream wait so GENUINE_MIN_BUDGET_SECONDS (default 6.0) remains for the
      genuine fan_out;
  (b) select_best(stable_tiebreak=True) — lexicographic (retailer, url) final
      tiebreak so equal-authority/precision/amount ties never follow arrival
      order;
  (c) race-miss genuine recovery in _price_fallback_on_miss — a COMPLETED
      showable genuine candidate (self._price_candidates) beats the parked
      converted. DISPLAY-ONLY: never a cache write from the cancel path.

FLAG-OFF BYTE-IDENTITY is pinned here by replicating the legacy behaviors with
the env var explicitly unset (incl. a verbatim replication of
test_price_timeout_returns_parked).

AWARENESS PIN (dispatcher note): a sharafdg-style price=0 + in_stock=True hit
must NOT count as a recoverable genuine candidate — select_best's own amount>0
candidate filter covers it; pinned in
test_race_miss_zero_amount_genuine_not_recovered.
"""

import asyncio
import inspect
import os
import time

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest


FULL_NAME = "Apple iPhone 15 128GB"

PARKED_CONVERTED = {
    "amount": 127.8, "currency": "BHD", "retailer": "Walmart",
    "source_method": "converted_usd", "estimated": False,
}

GENUINE_RAW = {
    "amount": 244.99, "currency": "BHD", "retailer": "sharafdg.com",
    "url": "https://www.sharafdg.com/product/apple-iphone-15-128gb/",
    "title": "Apple iPhone 15 128GB", "brand": "Apple",
    "source_method": "local_bhd", "in_stock": True,
}


def _seed_candidate(raw):
    """self._price_candidates entry in the fan/short-circuit retained shape."""
    return {
        "value": raw.get("amount"), "size": None,
        "source_method": raw.get("source_method") or "",
        "retailer": raw.get("retailer"), "title": raw.get("title"),
        "variant_rank": 0.0, "raw_data": dict(raw),
    }


class _FakeSource:
    def __init__(self, domain):
        self.domain = domain


@pytest.fixture
def scs_mod():
    from app.services import structured_comparison_service as mod
    return mod


@pytest.fixture
def service(monkeypatch, scs_mod):
    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", MagicMock())
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    svc = scs_mod.get_comparison_service()
    svc._save_price_to_db = MagicMock()
    return svc


def _patch_get_price_seams(monkeypatch, scs_mod, service, *, jsonapi=None, shopify=None):
    """Drive the REAL _get_price with every network/prod-write seam stubbed.

    NO Serper, NO GPT, NO shared-Redis/DB writes (set_cached / negcache /
    tier15 recorders / _save_price_to_db all no-op'd) — reproduces through the
    runtime per [[feedback-green-gate-not-correctness]] without polluting the
    shared prod cache (nocache bypasses the READ, not the WRITE)."""
    monkeypatch.setattr(scs_mod, "get_negative_cache", lambda *a, **k: None)
    monkeypatch.setattr(scs_mod, "set_negative_cache", MagicMock())
    monkeypatch.setattr(scs_mod, "record_tier15_attempt", lambda *a, **k: None)
    monkeypatch.setattr(scs_mod, "record_tier15_hit", lambda *a, **k: None)
    service._record_negative_price_cache = MagicMock()
    monkeypatch.setattr(scs_mod, "ENABLE_PAGE_SCRAPE", True)
    monkeypatch.setattr(scs_mod, "_should_escalate_price_scrape",
                        lambda *a, **k: True)
    # Selectors: everything quiet except what the test drives.
    monkeypatch.setattr(scs_mod, "get_shopify_sources_for_category",
                        lambda c: list(shopify or []))
    monkeypatch.setattr(scs_mod, "get_algolia_sources_for_category", lambda c: [])
    monkeypatch.setattr(scs_mod, "get_sitemap_sources_for_category", lambda c: [])
    monkeypatch.setattr(scs_mod, "get_jsonapi_sources_for_category",
                        lambda c: list(jsonapi or []))
    for fn in (
        "get_woo_sources_for_category", "get_salla_sources_for_category",
        "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
        "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
        "get_noon_sources_for_category",
    ):
        monkeypatch.setattr(scs_mod, fn, lambda c: [])
    monkeypatch.setattr(scs_mod, "_bahrain_discovery_only_sources", lambda c: [])
    # Discovery / Tier-2 / Tier-3 seams (all $0 in tests).
    monkeypatch.setattr(scs_mod, "search_web", AsyncMock(return_value={}))
    monkeypatch.setattr(
        scs_mod, "search_price_organic",
        AsyncMock(return_value={"organic": [], "knowledge_graph": None}),
    )
    monkeypatch.setattr(scs_mod, "extract_price",
                        AsyncMock(return_value=(None, {})))
    monkeypatch.setattr(scs_mod, "extract_price_from_training_data",
                        AsyncMock(return_value=(None, {})))


def _stub_phase1_siblings(monkeypatch, service):
    monkeypatch.setattr(service, "_get_specs", AsyncMock(return_value={"specs": {}}))
    monkeypatch.setattr(service, "_get_reviews", AsyncMock(return_value={"reviews": []}))
    monkeypatch.setattr(
        "app.services.structured_comparison_service.get_product_image_url",
        AsyncMock(return_value=None),
    )


# ---------------------------------------------------------------------------
# (a) FLAG-OFF byte-identity
# ---------------------------------------------------------------------------

class TestFlagOffByteIdentity:

    def test_flag_off_helpers_inert(self, monkeypatch, scs_mod):
        """Env unset → the flag helper is False and _pre_reserve_remaining
        (race_deadline=None) returns every legacy cap UNCHANGED — the four
        upstream consume timeouts still evaluate to 3.0 / 5.0 / 12.0 / 15.0."""
        monkeypatch.delenv("ENABLE_GENUINE_PRICE_PRIORITY", raising=False)
        assert scs_mod._genuine_priority_enabled() is False
        assert scs_mod._pre_reserve_remaining(3.0, None) == 3.0     # shopify consume
        assert scs_mod._pre_reserve_remaining(
            scs_mod._ALGOLIA_TIER2_TIMEOUT, None) == 5.0            # algolia consume
        assert scs_mod._pre_reserve_remaining(
            scs_mod._ADAPTER_TIMEOUT + 2.0, None) == 12.0           # adapter consume
        assert scs_mod._pre_reserve_remaining(15.0, None) == 15.0   # Tier-1 shopping

    def test_flag_on_helpers_math(self, monkeypatch, scs_mod):
        """Flag ON: reserve default 6.0 (env-overridable, malformed → 6.0);
        clamp = max(0.5, min(cap, deadline-now-reserve))."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        assert scs_mod._genuine_priority_enabled() is True
        monkeypatch.delenv("GENUINE_MIN_BUDGET_SECONDS", raising=False)
        assert scs_mod._genuine_min_budget_seconds() == 6.0
        monkeypatch.setenv("GENUINE_MIN_BUDGET_SECONDS", "2.0")
        assert scs_mod._genuine_min_budget_seconds() == 2.0
        monkeypatch.setenv("GENUINE_MIN_BUDGET_SECONDS", "abc")
        assert scs_mod._genuine_min_budget_seconds() == 6.0
        monkeypatch.delenv("GENUINE_MIN_BUDGET_SECONDS", raising=False)
        # 15s of runway, 6s reserve → a 12s cap clamps to ~9s.
        got = scs_mod._pre_reserve_remaining(12.0, time.monotonic() + 15.0)
        assert 8.5 < got <= 9.0
        # Runway below the reserve → the 0.5s floor (never negative/zero).
        assert scs_mod._pre_reserve_remaining(12.0, time.monotonic() + 1.0) == 0.5
        # Plenty of runway → the cap itself.
        got = scs_mod._pre_reserve_remaining(3.0, time.monotonic() + 60.0)
        assert got == 3.0

    def test_race_deadline_uses_module_constant(self, scs_mod):
        """The per-call deadline must be computed from the _PRICE_RACE_TIMEOUT
        MODULE ATTR (tests monkeypatch it; the warmer raises it to 60 via the
        PRICE_RACE_TIMEOUT env at import — tests/test_cron_warm_price_cache.py
        pins that env flows through), never a re-getenv."""
        source = inspect.getsource(
            scs_mod.StructuredComparisonService._get_price)
        assert "time.monotonic() + _PRICE_RACE_TIMEOUT" in source, (
            "_race_deadline must be derived from the _PRICE_RACE_TIMEOUT module "
            "attr so monkeypatched/warmer caps flow through the clamp math"
        )

    @pytest.mark.asyncio
    async def test_flag_off_timeout_returns_parked_converted(
            self, monkeypatch, scs_mod, service):
        """Verbatim replication of test_price_timeout_returns_parked with the
        flag EXPLICITLY unset — the legacy parked-converted-on-timeout contract
        is byte-identical flag-OFF."""
        monkeypatch.delenv("ENABLE_GENUINE_PRICE_PRIORITY", raising=False)
        monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 0.3, raising=False)

        async def _slow_get_price(brand, name, variant, region, search_query,
                                  nocache, category):
            full_name = f"{brand} {name} {variant or ''}".strip()
            service._parked_price[full_name] = dict(PARKED_CONVERTED)
            await asyncio.sleep(30)

        monkeypatch.setattr(service, "_get_price", _slow_get_price)
        _stub_phase1_siblings(monkeypatch, service)

        result = await service._fetch_product_data(
            {"brand": "Apple", "name": "iPhone 15", "variant": "128GB",
             "category": "electronics", "search_query": FULL_NAME},
            region="bahrain", include_specs=True, include_reviews=True,
            nocache=True,
        )
        price = result.get("price")
        assert price is not None
        assert price.get("amount") == pytest.approx(127.8)
        assert price.get("source_method") == "converted_usd"

    def test_race_miss_flag_off_ignores_candidates(
            self, monkeypatch, scs_mod, service):
        """Flag OFF: a seeded COMPLETED genuine candidate is IGNORED — the
        parked converted is returned exactly as before (pins legacy)."""
        monkeypatch.delenv("ENABLE_GENUINE_PRICE_PRIORITY", raising=False)
        service._parked_price[FULL_NAME] = dict(PARKED_CONVERTED)
        service._price_candidates[FULL_NAME] = [_seed_candidate(GENUINE_RAW)]
        got = service._price_fallback_on_miss("price", FULL_NAME, "electronics")
        assert got is not None
        assert got.get("source_method") == "converted_usd"
        assert got.get("amount") == pytest.approx(127.8)


# ---------------------------------------------------------------------------
# (b) genuine wins within the reserve (REAL _get_price, mocked seams)
# ---------------------------------------------------------------------------

class TestGenuineWinsWithinReserve:

    @pytest.mark.asyncio
    async def test_genuine_wins_within_reserve(
            self, monkeypatch, scs_mod, service):
        """Flag ON, cap 3.0s, reserve 1.5s: Tier-1 serper shopping hangs (10s —
        would starve the whole race flag-OFF) while the jsonapi adapter returns
        a genuine local_bhd in 0.2s. The clamp cuts the shopping wall at
        ~1.5s, the adapter consume still runs inside the cap, and the REAL
        _get_price returns the GENUINE price — not a timeout, not converted."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        monkeypatch.setenv("GENUINE_MIN_BUDGET_SECONDS", "1.5")
        monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 3.0, raising=False)
        _patch_get_price_seams(
            monkeypatch, scs_mod, service,
            jsonapi=[_FakeSource("nasserpharmacy.com")],
        )

        async def _slow_search(*a, **k):
            await asyncio.sleep(10)
            return {"shopping": [], "organic": []}

        async def _fast_genuine(*a, **k):
            await asyncio.sleep(0.2)
            return dict(GENUINE_RAW)

        monkeypatch.setattr(scs_mod, "search_product_prices", _slow_search)
        monkeypatch.setattr(scs_mod, "fetch_nasser_price", _fast_genuine)

        t0 = time.monotonic()
        result = await asyncio.wait_for(
            service._get_price("Apple", "iPhone 15", "128GB", "bahrain",
                               FULL_NAME, True, "electronics"),
            timeout=scs_mod._PRICE_RACE_TIMEOUT,
        )
        elapsed = time.monotonic() - t0
        assert result is not None
        assert result.get("source_method") == "local_bhd"
        assert result.get("amount") == pytest.approx(244.99)
        assert elapsed < 3.0

    @pytest.mark.asyncio
    async def test_flag_off_slow_upstream_starves_genuine(
            self, monkeypatch, scs_mod, service):
        """CONTROL (pins the legacy starvation the flag exists to fix): the
        IDENTICAL setup with the flag OFF runs the shopping wall unclamped →
        the outer wait_for cancels the race → nothing parked → None."""
        monkeypatch.delenv("ENABLE_GENUINE_PRICE_PRIORITY", raising=False)
        monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 3.0, raising=False)
        _patch_get_price_seams(
            monkeypatch, scs_mod, service,
            jsonapi=[_FakeSource("nasserpharmacy.com")],
        )

        async def _slow_search(*a, **k):
            await asyncio.sleep(10)
            return {"shopping": [], "organic": []}

        async def _fast_genuine(*a, **k):
            await asyncio.sleep(0.2)
            return dict(GENUINE_RAW)

        monkeypatch.setattr(scs_mod, "search_product_prices", _slow_search)
        monkeypatch.setattr(scs_mod, "fetch_nasser_price", _fast_genuine)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                service._get_price("Apple", "iPhone 15", "128GB", "bahrain",
                                   FULL_NAME, True, "electronics"),
                timeout=scs_mod._PRICE_RACE_TIMEOUT,
            )
        # Flag OFF the recovery is inert too: nothing parked → None.
        assert service._price_fallback_on_miss(
            "price", FULL_NAME, "electronics") is None


# ---------------------------------------------------------------------------
# (c) reserve honored under a tight deadline — the fan_out is REACHED
# ---------------------------------------------------------------------------

class TestReserveHonoredUnderTightDeadline:

    @pytest.mark.asyncio
    async def test_reserve_clamps_slow_upstream_reaches_fan_out(
            self, monkeypatch, scs_mod, service):
        """Flag ON, cap 2.0s, reserve 1.0s: a shopify prefetch future sleeping
        5s is clamped at ~1.0s so the REAL _get_price still REACHES the
        Tier-1.5 fan_out (spy: _build_escalation_scrapers invoked) with total
        elapsed well under the legacy 3s shopify wall."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        monkeypatch.setenv("GENUINE_MIN_BUDGET_SECONDS", "1.0")
        monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 2.0, raising=False)
        _patch_get_price_seams(
            monkeypatch, scs_mod, service,
            shopify=[_FakeSource("example-store.bh")],
        )

        async def _fast_empty_search(*a, **k):
            return {"shopping": [], "organic": [], "shopping_region": "bh"}

        async def _slow_shopify(*a, **k):
            await asyncio.sleep(5)
            return None

        monkeypatch.setattr(scs_mod, "search_product_prices", _fast_empty_search)
        monkeypatch.setattr(scs_mod, "fetch_shopify_price", _slow_shopify)
        monkeypatch.setattr(
            scs_mod, "_harvest_candidate_urls",
            lambda *a, **k: [(
                "https://www.example-store.bh/product/nike-air-force-1-white",
                "example-store.bh", "bahrain", 3.0,
            )],
        )
        _scraper_spy = MagicMock(return_value=[])
        monkeypatch.setattr(scs_mod, "_build_escalation_scrapers", _scraper_spy)

        t0 = time.monotonic()
        result = await service._get_price(
            "Nike", "Air Force 1", "White", "bahrain",
            "Nike Air Force 1 White", True, "fashion",
        )
        elapsed = time.monotonic() - t0
        assert _scraper_spy.called, (
            "the fan_out must be REACHED — the reserve exists so upstream "
            "clamps leave genuine-scrape runway"
        )
        assert elapsed < 2.5
        assert result is not None  # terminal pending dict at minimum


# ---------------------------------------------------------------------------
# (d) no regression when genuine misses
# ---------------------------------------------------------------------------

class TestConvertedStillServesWhenGenuineMisses:

    @pytest.mark.asyncio
    async def test_converted_serves_when_genuine_misses(
            self, monkeypatch, scs_mod, service):
        """Flag ON: every genuine tier misses → the parked converted_usd is
        still served at the §5 tier-7 fall-through (the flag must never turn a
        converted-coverage query into an estimate/None)."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        _patch_get_price_seams(monkeypatch, scs_mod, service)

        async def _fast_empty_search(*a, **k):
            return {"shopping": [], "organic": [], "shopping_region": "us"}

        monkeypatch.setattr(scs_mod, "search_product_prices", _fast_empty_search)
        monkeypatch.setattr(
            scs_mod, "extract_price_from_shopping",
            lambda *a, **k: dict(
                PARKED_CONVERTED,
                title="Apple iPhone 15 128GB",
                url="https://www.walmart.com/ip/apple-iphone-15-128gb/123",
            ),
        )

        result = await service._get_price(
            "Apple", "iPhone 15", "128GB", "bahrain",
            FULL_NAME, True, "electronics",
        )
        assert result is not None
        assert result.get("source_method") == "converted_usd"
        assert result.get("amount") == pytest.approx(127.8)

    def test_nothing_found_still_none(self, monkeypatch, scs_mod, service):
        """Flag ON, nothing parked, no candidates → _price_fallback_on_miss
        stays None (the INSUFFICIENT_DATA fake-winner guard input is honest)."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        service._parked_price = {}
        service._price_candidates = {}
        assert service._price_fallback_on_miss(
            "price", FULL_NAME, "electronics") is None
        # Non-price keys stay bare None too.
        assert service._price_fallback_on_miss(
            "specs", FULL_NAME, "electronics") is None


# ---------------------------------------------------------------------------
# (e) race-miss genuine recovery (display-only, never a cache write)
# ---------------------------------------------------------------------------

class TestRaceMissGenuineRecovery:

    def test_race_miss_prefers_completed_genuine(
            self, monkeypatch, scs_mod, service):
        """Flag ON: a COMPLETED showable genuine candidate beats the parked
        converted at the race-miss boundary — and NO cache write happens on
        the cancel path (set_cached + _save_price_to_db both untouched)."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        set_cached_spy = MagicMock()
        monkeypatch.setattr(scs_mod, "set_cached", set_cached_spy)
        service._parked_price[FULL_NAME] = dict(PARKED_CONVERTED)
        service._price_candidates[FULL_NAME] = [_seed_candidate(GENUINE_RAW)]

        got = service._price_fallback_on_miss("price", FULL_NAME, "electronics")
        assert got is not None
        assert got.get("source_method") == "local_bhd"
        assert got.get("amount") == pytest.approx(244.99)
        assert got.get("_cached") is False
        set_cached_spy.assert_not_called()
        service._save_price_to_db.assert_not_called()

    def test_race_miss_converted_candidates_fall_to_parked(
            self, monkeypatch, scs_mod, service):
        """Flag ON: candidates that are converted/estimate are NOT genuine-
        recovered — the parked converted serves (unchanged legacy answer)."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        conv = dict(GENUINE_RAW, source_method="converted_usd")
        est = dict(GENUINE_RAW, source_method="estimated")
        service._parked_price[FULL_NAME] = dict(PARKED_CONVERTED)
        service._price_candidates[FULL_NAME] = [
            _seed_candidate(conv), _seed_candidate(est),
        ]
        got = service._price_fallback_on_miss("price", FULL_NAME, "electronics")
        assert got is not None
        assert got.get("source_method") == "converted_usd"
        assert got.get("amount") == pytest.approx(127.8)

    def test_race_miss_zero_amount_genuine_not_recovered(
            self, monkeypatch, scs_mod, service):
        """AWARENESS PIN (recon lane): a sharafdg-style price=0 + in_stock=True
        genuine hit must NOT count as a recoverable in-flight genuine signal —
        amount must be truthy (select_best's own amount>0 filter). The parked
        converted serves instead."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        zero = dict(GENUINE_RAW, amount=0)
        service._parked_price[FULL_NAME] = dict(PARKED_CONVERTED)
        service._price_candidates[FULL_NAME] = [_seed_candidate(zero)]
        got = service._price_fallback_on_miss("price", FULL_NAME, "electronics")
        assert got is not None
        assert got.get("source_method") == "converted_usd"
        assert got.get("amount") == pytest.approx(127.8)

    def test_race_miss_wrong_sku_genuine_not_recovered(
            self, monkeypatch, scs_mod, service):
        """The recovery re-gates identity through select_best — a wrong-SKU
        genuine candidate (Pro Max under an iPhone 15 query) is NOT recovered;
        the parked converted serves (the cancel path must never become a
        wrong-SKU leak surface)."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        wrong = dict(
            GENUINE_RAW,
            title="Apple iPhone 15 Pro Max 256GB",
            url="https://www.sharafdg.com/product/apple-iphone-15-pro-max-256gb/",
        )
        service._parked_price[FULL_NAME] = dict(PARKED_CONVERTED)
        service._price_candidates[FULL_NAME] = [_seed_candidate(wrong)]
        got = service._price_fallback_on_miss("price", FULL_NAME, "electronics")
        assert got is not None
        assert got.get("source_method") == "converted_usd"

    @pytest.mark.asyncio
    async def test_fetch_product_data_race_miss_recovers_genuine_end_to_end(
            self, monkeypatch, scs_mod, service):
        """End-to-end through the REAL Phase-1 handler: a _get_price that seeds
        a completed genuine candidate + parks a converted then TIMES OUT must
        surface the GENUINE price (the category is threaded through both
        _price_fallback_on_miss call sites)."""
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 0.3, raising=False)

        async def _slow_get_price(brand, name, variant, region, search_query,
                                  nocache, category):
            full_name = f"{brand} {name} {variant or ''}".strip()
            service._parked_price[full_name] = dict(PARKED_CONVERTED)
            service._price_candidates[full_name] = [_seed_candidate(GENUINE_RAW)]
            await asyncio.sleep(30)

        monkeypatch.setattr(service, "_get_price", _slow_get_price)
        _stub_phase1_siblings(monkeypatch, service)

        result = await service._fetch_product_data(
            {"brand": "Apple", "name": "iPhone 15", "variant": "128GB",
             "category": "electronics", "search_query": FULL_NAME},
            region="bahrain", include_specs=True, include_reviews=True,
            nocache=True,
        )
        price = result.get("price")
        assert price is not None
        assert price.get("source_method") == "local_bhd"
        assert price.get("amount") == pytest.approx(244.99)


# ---------------------------------------------------------------------------
# (f) select_best stable tiebreak
# ---------------------------------------------------------------------------

class TestSelectBestStableTiebreak:

    def _tie_pair(self):
        base = {
            "amount": 10.0, "currency": "BHD",
            "title": "Acme Widget Pro X1", "in_stock": True,
        }
        a = dict(base, retailer="aaa-store.com",
                 url="https://aaa-store.com/product/acme-widget-pro-x1")
        b = dict(base, retailer="bbb-store.com",
                 url="https://bbb-store.com/product/acme-widget-pro-x1")
        return a, b

    def test_stable_tiebreak_order_invariant(self):
        """stable_tiebreak=True: two equal-authority/precision/amount
        candidates resolve to the SAME winner regardless of input order."""
        from app.services.price_service import select_best
        a, b = self._tie_pair()
        w1 = select_best([a, b], "Acme Widget Pro X1", None, stable_tiebreak=True)
        w2 = select_best([b, a], "Acme Widget Pro X1", None, stable_tiebreak=True)
        assert w1 is not None and w2 is not None
        assert w1.get("retailer") == w2.get("retailer") == "aaa-store.com"

    def test_default_kwarg_follows_insertion_order(self):
        """Default (stable_tiebreak omitted): the winner follows insertion
        order for true ties — pins flag-OFF byte-identity for ALL existing
        callers."""
        from app.services.price_service import select_best
        a, b = self._tie_pair()
        w1 = select_best([a, b], "Acme Widget Pro X1", None)
        w2 = select_best([b, a], "Acme Widget Pro X1", None)
        assert w1 is not None and w2 is not None
        assert w1.get("retailer") == "aaa-store.com"
        assert w2.get("retailer") == "bbb-store.com"

    def test_stable_tiebreak_never_overrides_authority(self):
        """The lexicographic tail is the LAST tiebreak — a higher-authority
        candidate still wins even when its retailer sorts later."""
        from app.services.price_service import select_best
        a, b = self._tie_pair()
        # b gains real authority via retailer_score (blended ×3 in
        # _candidate_authority) — the z-sorting retailer must still win.
        b = dict(b, retailer="zzz-store.com", retailer_score=1.0,
                 url="https://zzz-store.com/product/acme-widget-pro-x1")
        w = select_best([a, b], "Acme Widget Pro X1", None, stable_tiebreak=True)
        assert w is not None
        assert w.get("retailer") == "zzz-store.com"


# ---------------------------------------------------------------------------
# consume-adapter clamp shape — per-await fresh bound
# ---------------------------------------------------------------------------

def test_consume_adapter_prefetch_uses_fresh_bound_per_await():
    """The family consumes run SEQUENTIALLY (sitemap → jsonapi → the
    new-adapter families incl. Wave-C noon), so the outer bound must be a
    FRESH per-await closure (_consume_bound()) — a single computed-once
    _outer_bound cannot respect the deadline across 9 sequential waits."""
    from app.services.structured_comparison_service import (
        StructuredComparisonService,
    )
    source = inspect.getsource(StructuredComparisonService._get_price)
    assert "_consume_bound()" in source, (
        "adapter consume waits must use the per-await _consume_bound() closure"
    )
    assert "_outer_bound = _ADAPTER_TIMEOUT + 2.0" not in source, (
        "the computed-once _outer_bound must be replaced by _consume_bound()"
    )

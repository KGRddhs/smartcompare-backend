"""Bundle E follow-up — fan_out_price_lookup() wired into the live
_get_price() Tier 1.5 luxury cascade.

The plan § Task 2.3 hard rule: `fan_out_price_lookup MUST cancel
still-pending scrapers when 2+ sources confirm within 5%`. Tasks 2.1 + 2.2
built + tested fan_out_price_lookup() in isolation; this suite verifies
the LIVE integration inside _get_price().

Invariants preserved across the refactor (dispatcher's non-negotiables):
1. Counterfeit-domain results filtered (delegated to existing
   extract_price_from_html / is_counterfeit_listing helpers).
2. Official-brand priority via PRICE_SOURCE_RANK (firecrawl_brand_domain=90
   beats page_scrape_jsonld=85 beats serper_shopping=75).
3. should_fan_out() SCRAPING_MODE gate per-URL.
4. L2 DB cache + currency budget calls untouched.
5. Supplement path stays separate (iHerb + bn.boots.com).
6. STREAM_HARD_CAP_SECONDS=25.0 outermost wait_for stays.

Strategy: patch the URL-discovery helpers + the per-scraper coroutines
inside _get_price() to deterministic mocks. Assert that
fan_out_price_lookup() runs them in parallel + returns the highest-ranked
result. Cancellation semantics already covered by tests/test_scatter_gather_price.py
— here we focus on the wiring (right scraper list, right cancellation
behaviour, right counterfeit filtering).
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def service():
    """Fresh service instance per test (mirrors prod factory)."""
    from app.services.structured_comparison_service import get_comparison_service
    return get_comparison_service()


# ---------------------------------------------------------------------------
# Helper — build a synthetic candidate URL set the new scraper-builder
# will consume.
# ---------------------------------------------------------------------------

def _make_candidate(domain: str, source_method: str, value: float, rank: int):
    """A `fan_out_price_lookup` candidate result tuple."""
    return {
        "value": value,
        "source_method": source_method,
        "rank": rank,
        "raw_data": {"retailer": domain, "amount": value, "currency": "BHD"},
    }


# ---------------------------------------------------------------------------
# Test 1 — the new scraper-builder helper exists and wraps the cascade.
# ---------------------------------------------------------------------------

class TestScraperBuilderExists:
    """_build_escalation_scrapers() must return a list of zero-arg coroutines
    fan_out_price_lookup can call. Each coroutine yields a candidate dict
    in fan_out's expected shape."""

    def test_helper_importable(self):
        from app.services.structured_comparison_service import _build_escalation_scrapers  # noqa: F401

    @pytest.mark.asyncio
    async def test_builder_returns_scrapers_for_each_candidate_url(self):
        from app.services.structured_comparison_service import _build_escalation_scrapers

        candidate_urls = [
            ("https://www.louisvuitton.com/p/1", "louisvuitton.com"),
            ("https://www.farfetch.com/p/2", "farfetch.com"),
            ("https://www.ounass.ae/p/3", "ounass.ae"),
        ]

        scrapers = _build_escalation_scrapers(
            candidate_urls=candidate_urls,
            full_name="LV Neverfull",
            currency="BHD",
            scraping_mode="hard",
        )

        # At least one scraper per URL (curl always, firecrawl additionally
        # when should_fan_out + budget pass).
        assert len(scrapers) >= len(candidate_urls), (
            f"expected ≥{len(candidate_urls)} scrapers, got {len(scrapers)}"
        )
        # Each entry is callable + awaitable (returns coroutine when called)
        for s in scrapers:
            assert callable(s), f"scraper {s!r} not callable"


# ---------------------------------------------------------------------------
# Test 2 — quality ranker picks the highest-rank result across parallel scrapers
# ---------------------------------------------------------------------------

class TestQualityRankerWinsAcrossParallelScrapers:
    """When the parallel race returns multiple candidates with different
    ranks, the rank-90 result must beat rank-70 even if rank-70 lands first."""

    @pytest.mark.asyncio
    async def test_higher_rank_wins(self):
        from app.services.price_service import fan_out_price_lookup

        async def fast_low_rank(product):
            return _make_candidate("noon.com", "serper_shopping", 100.0, 75)

        async def slow_high_rank(product):
            await asyncio.sleep(0.05)
            return _make_candidate("louisvuitton.com", "firecrawl_brand_domain", 110.0, 90)

        result = await fan_out_price_lookup(
            product={"full_name": "LV"},
            scrapers=[fast_low_rank, slow_high_rank],
        )
        assert result["best"] is not None
        assert result["best"]["source_method"] == "firecrawl_brand_domain", (
            f"expected rank-90 to win, got {result['best']}"
        )
        assert result["best"]["rank"] == 90


# ---------------------------------------------------------------------------
# Test 3 — cancellation fires when 2 sources confirm within 5%
# ---------------------------------------------------------------------------

class TestCancellationOnAgreement:
    @pytest.mark.asyncio
    async def test_two_sources_within_5pct_cancels_pending(self):
        from app.services.price_service import fan_out_price_lookup

        cancellation_observed = {"third_cancelled": False}

        async def src_a(product):
            return _make_candidate("farfetch.com", "page_scrape_jsonld", 100.0, 85)

        async def src_b(product):
            await asyncio.sleep(0.01)
            return _make_candidate("ssense.com", "page_scrape_jsonld", 103.0, 85)

        async def src_c_slow(product):
            try:
                await asyncio.sleep(5.0)
                return _make_candidate("ounass.ae", "page_scrape_jsonld", 105.0, 85)
            except asyncio.CancelledError:
                cancellation_observed["third_cancelled"] = True
                raise

        result = await fan_out_price_lookup(
            product={"full_name": "LV"},
            scrapers=[src_a, src_b, src_c_slow],
        )

        assert cancellation_observed["third_cancelled"], (
            "slow 3rd scraper should have been cancelled when src_a + src_b agreed"
        )
        assert result["cancelled_count"] >= 1
        # When 2+ confirm within 5%, the selected "best" is marked as
        # confirmed_multi_source per quality_ranker. fan_out itself doesn't
        # rewrite to confirmed_multi_source — select_best_price does that
        # when called explicitly. Here we just assert best is one of the
        # confirming pair.
        assert result["best"]["value"] in (100.0, 103.0)


# ---------------------------------------------------------------------------
# Test 4 — counterfeit-domain filter survives the refactor
# ---------------------------------------------------------------------------

class TestCounterfeitFilterPreserved:
    """The existing counterfeit filter (DHgate, AliExpress, Temu, Wish)
    lives inside extract_price_from_html + the per-scraper helpers. Here
    we verify those scrapers, when wrapped for fan_out, would still
    REJECT a counterfeit-domain URL by returning None (so the candidate
    never enters the quality-ranker pool)."""

    @pytest.mark.asyncio
    async def test_counterfeit_url_rejected_by_should_fan_out(self):
        """Counterfeit domains aren't in OFFICIAL_BRAND_DOMAINS or
        AUTHORIZED_LUXURY_RETAILERS — the URL-discovery step (existing
        Tier 1.5b filter) excludes them. should_fan_out() is orthogonal
        (mode-gating), but verify a known-counterfeit URL doesn't
        accidentally pass through fan_out when the discovery filter
        omits it."""
        from app.services.price_service import (
            OFFICIAL_BRAND_DOMAINS,
            AUTHORIZED_LUXURY_RETAILERS,
        )
        # Sanity-check the safety net: the dispatcher's invariant #1
        # depends on counterfeit domains NEVER appearing in either
        # whitelist. This isn't a behaviour test of fan_out itself — it's
        # a contract check that the discovery filter still works.
        for bad in ("dhgate.com", "aliexpress.com", "temu.com", "wish.com"):
            assert bad not in OFFICIAL_BRAND_DOMAINS, (
                f"{bad} must NOT be an official brand domain (counterfeit risk)"
            )
            assert bad not in AUTHORIZED_LUXURY_RETAILERS, (
                f"{bad} must NOT be an authorized luxury retailer"
            )


# ---------------------------------------------------------------------------
# Test 5 — empty candidate set returns None without exploding
# ---------------------------------------------------------------------------

class TestEmptyCandidateSet:
    @pytest.mark.asyncio
    async def test_empty_url_list_yields_no_scrapers(self):
        from app.services.structured_comparison_service import _build_escalation_scrapers

        scrapers = _build_escalation_scrapers(
            candidate_urls=[],
            full_name="LV",
            currency="BHD",
            scraping_mode="hard",
        )
        assert scrapers == []

    @pytest.mark.asyncio
    async def test_fan_out_with_empty_scrapers_returns_none_best(self):
        from app.services.price_service import fan_out_price_lookup

        result = await fan_out_price_lookup(
            product={"full_name": "LV"},
            scrapers=[],
        )
        assert result["best"] is None
        assert result["alternates"] == []


# ===========================================================================
# Dispatcher-RED suite — fan_out wired into the LIVE _get_price() Tier 1.5
#
# At HEAD (cdf2c04) `_get_price()` still runs the sequential Tier 1.5a/b/c/d
# cascade. The 5 tests below drive `_get_price()` end-to-end with mocked
# scraper primitives + a stubbed `fan_out_price_lookup` and assert the
# observable integration contract:
#   1. highest-rank winner wins
#   2. pending scrapers get CancelledError on confirmation
#   3. counterfeit URLs never reach the scraper list
#   4. SCRAPING_MODE=soft + non-luxury → Firecrawl/Scrape.do omitted
#   5. all-None scrapers → Tier 2 (GPT) runs
#
# These will RED until backend-opus replaces the sequential cascade in
# `_get_price()` with `fan_out_price_lookup(scrapers=_build_escalation_scrapers(
# candidate_urls=..., full_name=..., currency=..., scraping_mode=...))`.
# ===========================================================================


@pytest.fixture
def luxury_inputs():
    """Inputs that route _get_price() into the Tier 1.5 cascade.

    Tier 1.5 is gated by `is_luxury_brand(full_name) and ENABLE_PAGE_SCRAPE`
    (structured_comparison_service.py:1334). Louis Vuitton matches
    LUXURY_BRAND_KEYWORDS, so once Tier 1 returns nothing (forced by the
    extract_price_from_shopping mock) Tier 1.5 runs."""
    return {
        "brand": "Louis Vuitton",
        "name": "Neverfull MM",
        "variant": None,
        "region": "bahrain",
        "search_query": "Louis Vuitton Neverfull MM price",
        "nocache": True,
        "category": "fashion",
    }


@pytest.fixture
def clean_service(monkeypatch):
    """Fresh StructuredComparisonService with cache + DB writes neutralized.

    Every call to get_cached / set_cached / get_cached_price returns None
    so the test exercises the live tier cascade rather than a cached path."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )

    service = scs_mod.get_comparison_service()
    service._save_price_to_db = MagicMock()
    return service


def _fan_out_candidate(value: float, source_method: str, rank: int) -> dict:
    """fan_out_price_lookup candidate shape per quality_ranker.py."""
    return {
        "value": value,
        "source_method": source_method,
        "rank": rank,
        "raw_data": {"amount": value, "currency": "BHD", "retailer": "test"},
    }


def _stub_tier1_empty(monkeypatch):
    """Force Tier 1 (Serper Shopping) to return nothing so flow proceeds
    to Tier 1.5 — the only tier under test in this suite."""
    monkeypatch.setattr(
        "app.services.structured_comparison_service.search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": []}),
    )
    monkeypatch.setattr(
        "app.services.structured_comparison_service.extract_price_from_shopping",
        lambda *a, **kw: None,
    )


class TestFanOutHighestRankWinner:
    """select_best_price() returns the highest-rank candidate even when a
    lower-rank scraper finishes first. The integration must honor
    fan_out's `best` selection, not the first task to complete."""

    @pytest.mark.asyncio
    async def test_fan_out_returns_highest_rank_winner(
        self, monkeypatch, luxury_inputs, clean_service
    ):
        _stub_tier1_empty(monkeypatch)
        monkeypatch.setattr(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={
                "organic": [
                    {"link": "https://www.louisvuitton.com/eng-bh/p/neverfull-mm"},
                    {"link": "https://www.farfetch.com/bh/lv-neverfull.aspx"},
                    {"link": "https://www.ounass.bh/lv-neverfull"},
                ]
            }),
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.get_official_domain",
            lambda *a, **kw: "louisvuitton.com",
        )

        # Patched fan_out returns ranks [90, 70, 70] — rank-90 must win.
        fan_out_mock = AsyncMock(return_value={
            "best": _fan_out_candidate(2150.0, "firecrawl_brand_domain", 90),
            "alternates": [
                _fan_out_candidate(2200.0, "scrapedo_rendered", 70),
                _fan_out_candidate(2180.0, "scrapedo_rendered", 70),
            ],
            "cancelled_count": 0,
            "elapsed_seconds": 1.2,
        })
        monkeypatch.setattr(
            "app.services.structured_comparison_service.fan_out_price_lookup",
            fan_out_mock,
        )

        result = await clean_service._get_price(**luxury_inputs)

        # RED gate: backend-opus's integration must invoke fan_out at least once.
        assert fan_out_mock.call_count >= 1, (
            "fan_out_price_lookup was never invoked from _get_price() — "
            "Tier 1.5 still runs the sequential cascade. Wire it via "
            "_build_escalation_scrapers(candidate_urls=..., full_name=..., "
            "currency=..., scraping_mode=...) then pass the list to "
            "fan_out_price_lookup()."
        )
        # GREEN gate: the price returned must be the rank-90 winner.
        amount = result.get("amount") or result.get("value")
        assert amount == 2150.0, (
            f"expected the rank-90 winner (2150.0) — got amount={amount}, "
            f"full result={result}"
        )
        assert result.get("source_method") == "firecrawl_brand_domain", (
            f"expected source_method=firecrawl_brand_domain (the rank-90 "
            f"winner) — got {result.get('source_method')}"
        )


class TestPendingScrapersCancelledOnConfirmation:
    """Design line 403: once 2 sources agree within 5% OR a single rank≥85
    result lands, fan_out cancels still-pending scrapers via
    asyncio.CancelledError. The integration must use the REAL
    fan_out_price_lookup (not bypass it) for this to reach the wire."""

    @pytest.mark.asyncio
    async def test_pending_scrapers_cancelled_on_confirmation(
        self, monkeypatch, luxury_inputs, clean_service
    ):
        cancelled: list[str] = []

        async def _fast_a(_product):
            await asyncio.sleep(0.02)
            return _fan_out_candidate(2100.0, "firecrawl_brand_domain", 90)

        async def _fast_b(_product):
            await asyncio.sleep(0.02)
            return _fan_out_candidate(2150.0, "page_scrape_jsonld", 85)

        async def _slow_c(_product):
            try:
                await asyncio.sleep(2.0)
                return _fan_out_candidate(99.0, "scrapedo_rendered", 70)
            except asyncio.CancelledError:
                cancelled.append("slow_c")
                raise

        async def _slow_d(_product):
            try:
                await asyncio.sleep(2.0)
                return _fan_out_candidate(99.0, "gpt_training_estimate", 40)
            except asyncio.CancelledError:
                cancelled.append("slow_d")
                raise

        # Force _build_escalation_scrapers to return our 4 controlled scrapers
        # so the cancellation behavior is deterministic.
        monkeypatch.setattr(
            "app.services.structured_comparison_service._build_escalation_scrapers",
            lambda **kw: [_fast_a, _fast_b, _slow_c, _slow_d],
        )
        _stub_tier1_empty(monkeypatch)
        monkeypatch.setattr(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={
                "organic": [{"link": "https://www.louisvuitton.com/x"}],
            }),
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.get_official_domain",
            lambda *a, **kw: "louisvuitton.com",
        )

        # Use the REAL fan_out_price_lookup (no patch) so true cancellation
        # semantics are exercised end-to-end.
        await clean_service._get_price(**luxury_inputs)

        assert len(cancelled) >= 1, (
            "Expected at least 1 pending scraper to receive "
            "asyncio.CancelledError after 2 sources agreed within 5%. "
            f"cancelled list: {cancelled}. RED means _get_price did not "
            "invoke fan_out_price_lookup — Tier 1.5 still sequential."
        )


class TestCounterfeitDomainFiltered:
    """Counterfeit domains (dhgate, aliexpress, temu, wish) must NEVER
    reach the scraper builder — burning Firecrawl/Scrape.do credits on a
    fake-product page is wasted budget. The discovery filter
    (OFFICIAL_BRAND_DOMAINS + AUTHORIZED_LUXURY_RETAILERS + GCC_LUXURY_RETAILERS
    whitelists) must survive the refactor."""

    @pytest.mark.asyncio
    async def test_counterfeit_domain_filtered_even_when_first(
        self, monkeypatch, luxury_inputs, clean_service
    ):
        _stub_tier1_empty(monkeypatch)
        # Search returns counterfeit URLs FIRST + a legitimate one last.
        monkeypatch.setattr(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={
                "organic": [
                    {"link": "https://www.dhgate.com/replica-lv-neverfull.html"},
                    {"link": "https://www.aliexpress.com/item/12345.html"},
                    {"link": "https://www.farfetch.com/bh/lv-neverfull.aspx"},
                ]
            }),
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.get_official_domain",
            lambda *a, **kw: "louisvuitton.com",
        )

        captured_urls: list[str] = []

        def _capture_scrapers(*, candidate_urls, **kw):
            for url, _domain in candidate_urls:
                captured_urls.append(url)
            return []  # empty → fan_out returns no best → Tier 2 fallback

        monkeypatch.setattr(
            "app.services.structured_comparison_service._build_escalation_scrapers",
            _capture_scrapers,
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.fan_out_price_lookup",
            AsyncMock(return_value={
                "best": None, "alternates": [],
                "cancelled_count": 0, "elapsed_seconds": 0.0,
            }),
        )
        # Tier 2 GPT fallback stub so _get_price doesn't error out.
        monkeypatch.setattr(
            "app.services.structured_comparison_service.extract_price_from_training_data",
            AsyncMock(return_value=(
                {"amount": 2200, "currency": "USD",
                 "source_method": "gpt_training_estimate"},
                {},
            )),
        )

        await clean_service._get_price(**luxury_inputs)

        # RED gate: if _build_escalation_scrapers is never invoked, captured_urls
        # stays empty — the assertion below catches the missing integration.
        assert len(captured_urls) >= 1, (
            "_build_escalation_scrapers was never invoked from _get_price() — "
            "fan_out integration missing. captured_urls is empty."
        )
        for url in captured_urls:
            assert "dhgate" not in url.lower(), (
                f"counterfeit domain dhgate.com leaked into the fan_out "
                f"scraper list: {url}. The discovery filter must reject "
                f"non-whitelisted domains BEFORE _build_escalation_scrapers sees them."
            )
            assert "aliexpress" not in url.lower(), (
                f"counterfeit domain aliexpress.com leaked into the fan_out "
                f"scraper list: {url}."
            )


class TestScrapingModeSoftSkipsFirecrawl:
    """firecrawl_service.should_fan_out(url, mode='soft') returns False for
    non-luxury domains. _build_escalation_scrapers honors the gate in isolation;
    the integration must FORWARD the scraping_mode arg so the gate fires
    end-to-end. With SCRAPING_MODE=soft + a non-luxury URL (amazon.ae),
    only the curl scraper should be in the list — no Firecrawl, no Scrape.do."""

    @pytest.mark.asyncio
    async def test_scrapingmode_soft_skips_firecrawl_for_non_luxury(
        self, monkeypatch, luxury_inputs, clean_service
    ):
        monkeypatch.setenv("SCRAPING_MODE", "soft")
        _stub_tier1_empty(monkeypatch)
        monkeypatch.setattr(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={
                "organic": [{"link": "https://www.amazon.ae/lv-neverfull"}],
            }),
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.get_official_domain",
            lambda *a, **kw: "amazon.ae",
        )

        captured_modes: list[str] = []

        def _capture_build(*, candidate_urls, full_name, currency, scraping_mode):
            captured_modes.append(scraping_mode)
            return []

        monkeypatch.setattr(
            "app.services.structured_comparison_service._build_escalation_scrapers",
            _capture_build,
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.fan_out_price_lookup",
            AsyncMock(return_value={
                "best": None, "alternates": [],
                "cancelled_count": 0, "elapsed_seconds": 0.0,
            }),
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.extract_price_from_training_data",
            AsyncMock(return_value=(
                {"amount": 100, "currency": "USD",
                 "source_method": "gpt_training_estimate"},
                {},
            )),
        )

        await clean_service._get_price(**luxury_inputs)

        assert len(captured_modes) >= 1, (
            "_build_escalation_scrapers was never invoked — fan_out integration "
            "missing in _get_price()."
        )
        assert "soft" in captured_modes, (
            f"SCRAPING_MODE=soft did not propagate to _build_escalation_scrapers. "
            f"captured_modes={captured_modes}. The integration must read the "
            f"env var and forward it via the scraping_mode kwarg so the "
            f"should_fan_out() gate fires."
        )

        # Sanity: should_fan_out() must agree this URL is non-luxury in soft mode.
        from app.services import firecrawl_service
        assert firecrawl_service.should_fan_out(
            "https://www.amazon.ae/lv-neverfull", mode="soft"
        ) is False, (
            "should_fan_out('amazon.ae', mode='soft') unexpectedly True. "
            "The luxury-domain list may have changed; revise this test."
        )


class TestFallthroughToTier2WhenAllScrapersFail:
    """When every scraper returns None (cold-cache luxury, all renderers
    time out), fan_out returns {best: None}. _get_price MUST fall through
    to Tier 2 (GPT extract from search context) rather than return a
    zero/empty price."""

    @pytest.mark.asyncio
    async def test_fan_out_falls_through_to_tier2_when_all_scrapers_fail(
        self, monkeypatch, luxury_inputs, clean_service
    ):
        _stub_tier1_empty(monkeypatch)
        monkeypatch.setattr(
            "app.services.structured_comparison_service.search_web",
            AsyncMock(return_value={
                "organic": [{"link": "https://www.louisvuitton.com/x"}],
            }),
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.get_official_domain",
            lambda *a, **kw: "louisvuitton.com",
        )

        fan_out_mock = AsyncMock(return_value={
            "best": None, "alternates": [],
            "cancelled_count": 0, "elapsed_seconds": 5.0,
        })
        monkeypatch.setattr(
            "app.services.structured_comparison_service.fan_out_price_lookup",
            fan_out_mock,
        )

        # Stub BOTH Tier 2 paths — refactor may name the fallback either
        # extract_price_from_organic or extract_price_from_training_data.
        # Either satisfies the contract: a gpt_* source_method + nonzero amount.
        monkeypatch.setattr(
            "app.services.structured_comparison_service.extract_price_from_organic",
            AsyncMock(return_value=(
                {"amount": 2400, "currency": "USD",
                 "source_method": "gpt_organic_extract"},
                {"prompt_tokens": 100, "completion_tokens": 50},
            )),
            raising=False,
        )
        monkeypatch.setattr(
            "app.services.structured_comparison_service.extract_price_from_training_data",
            AsyncMock(return_value=(
                {"amount": 2500, "currency": "USD",
                 "source_method": "gpt_training_estimate"},
                {"prompt_tokens": 50, "completion_tokens": 25},
            )),
        )

        result = await clean_service._get_price(**luxury_inputs)

        assert fan_out_mock.call_count >= 1, (
            "fan_out_price_lookup was never invoked from _get_price() — "
            "Tier 1.5 integration missing; test cannot verify fall-through."
        )
        amount = result.get("amount") or result.get("value") or 0
        assert amount > 0, (
            f"after fan_out returned best=None, _get_price returned an "
            f"empty/zero price. Expected fall-through to Tier 2 GPT extraction. "
            f"Got: {result}"
        )
        assert result.get("source_method") in {
            "gpt_organic_extract", "gpt_training_estimate"
        }, (
            f"after fan_out None, _get_price source_method="
            f"{result.get('source_method')}, expected a gpt_* method "
            f"indicating Tier 2/3 fallback ran. Got: {result}"
        )

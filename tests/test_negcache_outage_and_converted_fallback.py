"""KPI Wave A6 — two unconditional price-cascade safety fixes (recon_cascade R4+R5).

R4 NEGCACHE OUTAGE GUARD: a Serper outage (depleted/dead key) makes EVERY Tier-1.5
discovery `search_web` result carry an "error" key, so the Tier-3 estimate that
follows reflects the OUTAGE, not a structural genuine-BH gap — yet the terminal
wrote the 30-day `nogenuine` sentinel, freezing the outage estimate for a month.
Fix: thread a `discovery_degraded` bool from the discovery gather into
`_record_negative_price_cache`, capping the TTL to 24h (PRICE_CACHE_TTL) exactly
like `guard_rejected`. A legitimately-EMPTY discovery WITHOUT error keys stays a
real structural dead-end (30d unchanged — the finite-budget invariant).

R5 CONVERTED TERMINAL FALLBACK: when the $0 adapter prefetch yields ONLY converted
(GCC→BHD) hits, `_consume_adapter_prefetch` correctly refuses to short-circuit —
but it dropped the observations on the floor, so a full-cascade miss fell to a
Tier-3 GPT estimate even though a REAL cited GCC PDP price existed. Fix: park the
`select_best` winner (authority-not-cheapest, exact ∧ in-stock ∧ valid PDP) into
the existing converted_fallback/_parked_price plumbing so the §5 tier-7 fallback
serves it with honest `converted_usd` provenance. A genuine adapter hit still
short-circuits over it; converted stays SF-1-exempt from the negcache.

All network + GPT + cache writes are mocked — NO Serper, NO OpenAI, NO prod cache.
Run: python -m pytest tests/test_negcache_outage_and_converted_fallback.py -q
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.price_service import (
    NEGATIVE_PRICE_CACHE_TTL,
    PRICE_CACHE_TTL,
    should_negative_cache,
)


# Every registry selector the prefetch/consume consults — neutralized in the
# shared stub (literal Source rows load flag-independently; PR#13 reconcile rule),
# then a scenario re-patches the ONE mechanism it drives.
_ADAPTER_SELECTOR_NAMES = (
    "get_shopify_sources_for_category",
    "get_algolia_sources_for_category",
    "get_sitemap_sources_for_category",
    "get_jsonapi_sources_for_category",
    "get_woo_sources_for_category",
    "get_salla_sources_for_category",
    "get_occ_sources_for_category",
    "get_magento_gql_sources_for_category",
    "get_unbxd_sources_for_category",
    "get_restjson_sources_for_category",
    "get_noon_sources_for_category",  # Wave C C3 — noon-BH literal (flag-independent)
)


def _stub_cascade(scs, svc, monkeypatch, *, negcache_captured):
    """Drive _get_price through the FULL cascade deterministically with zero
    network: cache/DB/negcache reads miss, escalation forced, every selector
    empty, Tier-1 shopping + Tier-2 organic/GPT empty, Tier-3 a fixed estimate.
    The negative-cache WRITE is captured into `negcache_captured`."""
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(
        scs, "set_negative_cache",
        lambda key, value, ttl: negcache_captured.update(
            key=key, value=value, ttl=ttl,
        ),
    )

    async def _no_db_price(*a, **k):
        return None
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _no_db_price,
        raising=False,
    )
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)

    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
    for _name in _ADAPTER_SELECTOR_NAMES:
        monkeypatch.setattr(scs, _name, lambda c: [])

    # The sitemap-cold negcache axis is not under test — pin it quiet so the TTL
    # assertions isolate the R4 flag (and no Redis index probe fires).
    monkeypatch.setattr(scs, "sitemap_discovery_is_cold", lambda c: False)
    monkeypatch.setattr(scs, "sitemap_unbuilt_domains", lambda c: [])

    async def no_shopping(*a, **k):
        return {"shopping": [], "organic": [], "shopping_region": "bahrain"}
    monkeypatch.setattr(scs, "search_product_prices", no_shopping)

    async def no_organic(*a, **k):
        return {"organic": [], "knowledge_graph": None}
    monkeypatch.setattr(scs, "search_price_organic", no_organic, raising=False)

    async def no_tier2_extract(*a, **k):
        return None, {}
    monkeypatch.setattr(scs, "extract_price", no_tier2_extract)

    async def tier3_estimate(*a, **k):
        return {"amount": 70.0, "currency": "BHD"}, {}
    monkeypatch.setattr(scs, "extract_price_from_training_data", tier3_estimate)


def _search_web_returning(payload):
    async def _sw(*a, **k):
        return dict(payload)
    return _sw


# The depleted-key shape serper_service actually returns (search_web catches the
# HTTP 400 and surfaces {"organic": [], "error": str(e)}).
_DEGRADED_DISCOVERY = {
    "organic": [],
    "error": "Client error '400 Bad Request' — Not enough credits",
}
_CLEAN_EMPTY_DISCOVERY = {"organic": []}


def _converted_kwd_hit():
    """What a woo adapter returns for a KWD store: amount ALREADY converted to
    BHD, the literal converted_usd stamp, a real PDP url + exact title."""
    return {
        "amount": 39.5, "currency": "BHD", "retailer": "perfumeskuwait.com",
        "url": "https://perfumeskuwait.com/product/dior-sauvage-edt-100ml",
        "in_stock": True, "estimated": False, "confidence": 0.85,
        "source_method": "converted_usd", "original_currency": "KWD",
        "title": "Dior Sauvage Eau de Toilette 100ml",
    }


def _genuine_woo_hit():
    return {
        "amount": 42.0, "currency": "BHD", "retailer": "theperfumesclub.com",
        "url": "https://theperfumesclub.com/product/dior-sauvage-edt-100ml",
        "in_stock": True, "estimated": False, "confidence": 0.9,
        "source_method": "woo_store_api",
        "title": "Dior Sauvage Eau de Toilette 100ml",
    }


# ------------------------------------------ R4: _record_negative_price_cache ---


class TestRecordNegativeCacheDegradedFlag:
    """`discovery_degraded=True` caps the sentinel TTL to PRICE_CACHE_TTL (24h),
    exactly like guard_rejected / transient_discovery; the default stays 30d."""

    def _capture_ttl(self, **flags):
        from app.services.structured_comparison_service import (
            StructuredComparisonService,
        )
        service = StructuredComparisonService()
        price = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
        captured = {}
        with patch(
            "app.services.structured_comparison_service.set_negative_cache",
            side_effect=lambda k, v, t: captured.update(key=k, ttl=t),
        ):
            service._record_negative_price_cache("price:abc123", price, **flags)
        return captured

    def test_discovery_degraded_caps_to_24h(self):
        captured = self._capture_ttl(discovery_degraded=True)
        assert captured.get("ttl") == PRICE_CACHE_TTL
        assert captured["ttl"] != NEGATIVE_PRICE_CACHE_TTL

    def test_default_path_still_30d(self):
        captured = self._capture_ttl()
        assert captured.get("ttl") == NEGATIVE_PRICE_CACHE_TTL


# --------------------------------------- R4: end-to-end through _get_price ---


@pytest.mark.asyncio
class TestNegcacheOutageGuardEndToEnd:
    async def _run_to_tier3(self, monkeypatch, search_web_payload):
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        captured = {}
        _stub_cascade(scs, svc, monkeypatch, negcache_captured=captured)
        monkeypatch.setattr(
            scs, "search_web", _search_web_returning(search_web_payload),
        )
        price = await svc._get_price(
            brand="Tom Ford", name="Oud Wood", variant="100ml",
            region="bahrain", search_query="Tom Ford Oud Wood 100ml",
            nocache=True, category="fragrances",
        )
        return price, captured

    async def test_degraded_discovery_caps_sentinel_ttl(self, monkeypatch):
        # (a) EVERY discovery result carries the serper_service "error" key (the
        # depleted-key outage shape) → the Tier-3 estimate's sentinel must be
        # capped to <=24h or not written — never the 30d outage freeze.
        price, captured = await self._run_to_tier3(monkeypatch, _DEGRADED_DISCOVERY)
        assert price.get("estimated") is True  # the cascade fell to Tier-3 as staged
        assert (not captured) or captured["ttl"] <= PRICE_CACHE_TTL, (
            f"a Serper-outage estimate was 30d-frozen (ttl={captured.get('ttl')})"
        )

    async def test_clean_empty_discovery_keeps_30d_sentinel(self, monkeypatch):
        # (b) a legitimately-EMPTY discovery WITHOUT error keys is a REAL
        # structural dead-end — the 30d sentinel is unchanged (never re-burn the
        # scrape cascade every 24h for the structural tail on a finite budget).
        price, captured = await self._run_to_tier3(
            monkeypatch, _CLEAN_EMPTY_DISCOVERY,
        )
        assert price.get("estimated") is True
        assert captured.get("ttl") == NEGATIVE_PRICE_CACHE_TTL


# ------------------------------------------- R5: converted terminal fallback ---


def test_should_negative_cache_exempts_converted_usd():
    # Pin the SF-1 exemption the converted terminal relies on.
    assert should_negative_cache(_converted_kwd_hit()) is False


async def _run_converted_only_scenario(monkeypatch):
    """ONE woo source whose adapter yields ONLY a KWD→BHD converted hit; the
    rest of the cascade misses everywhere. Returns (svc, price, captured) —
    shared by the flag-ON park pins and the flag-OFF rollback pin."""
    import app.services.structured_comparison_service as scs
    svc = scs.get_comparison_service()
    captured = {}
    _stub_cascade(scs, svc, monkeypatch, negcache_captured=captured)
    monkeypatch.setattr(
        scs, "search_web", _search_web_returning(_CLEAN_EMPTY_DISCOVERY),
    )
    monkeypatch.setattr(
        scs, "get_woo_sources_for_category",
        lambda c: [SimpleNamespace(domain="perfumeskuwait.com")],
    )

    async def fake_woo(domain, product_name, currency="BHD", resolved_category=None):
        return _converted_kwd_hit()
    monkeypatch.setattr(scs, "fetch_woocommerce_store_api_price", fake_woo)

    price = await svc._get_price(
        brand="Dior", name="Sauvage", variant="EDT 100ml",
        region="bahrain", search_query="Dior Sauvage EDT 100ml",
        nocache=True, category="fragrances",
    )
    return svc, price, captured


@pytest.mark.asyncio
class TestConvertedTerminalFallback:
    """Flag-ON pins (ENABLE_EXACT_PRICE_GATE=true — explicit, so the park
    behaviour is pinned independent of the ambient env)."""

    @pytest.fixture(autouse=True)
    def _gate_on(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")

    async def _run_converted_only(self, monkeypatch):
        _, price, captured = await _run_converted_only_scenario(monkeypatch)
        return price, captured

    async def test_converted_only_adapter_hit_served_not_estimated(self, monkeypatch):
        # (c) the tier-7 fallback serves the REAL cited converted adapter price
        # (its own PDP url, honest converted_usd) instead of a Tier-3 estimate.
        price, _ = await self._run_converted_only(monkeypatch)
        assert price["source_method"] == "converted_usd", (
            f"converted adapter hit fell to {price.get('source_method')!r} "
            f"(estimated={price.get('estimated')!r}) instead of the tier-7 park"
        )
        assert price["url"] == "https://perfumeskuwait.com/product/dior-sauvage-edt-100ml"
        assert price["amount"] == pytest.approx(39.5)
        assert price.get("estimated") is not True

    async def test_converted_terminal_writes_no_nogenuine_sentinel(self, monkeypatch):
        # (e) converted_usd is a LIVE cited price (SF-1) — its terminal must not
        # write the nogenuine sentinel (the genuine scrape may succeed later).
        _, captured = await self._run_converted_only(monkeypatch)
        assert not captured, (
            f"the converted terminal wrote a negcache sentinel: {captured!r}"
        )

    async def test_genuine_adapter_hit_short_circuits_over_converted(self, monkeypatch):
        # (d) a genuine BHD hit alongside the converted one still short-circuits
        # (existing behavior pinned — the R5 park must not displace it).
        import app.services.structured_comparison_service as scs
        svc = scs.get_comparison_service()
        captured = {}
        _stub_cascade(scs, svc, monkeypatch, negcache_captured=captured)
        monkeypatch.setattr(
            scs, "search_web", _search_web_returning(_CLEAN_EMPTY_DISCOVERY),
        )
        monkeypatch.setattr(
            scs, "get_woo_sources_for_category",
            lambda c: [
                SimpleNamespace(domain="perfumeskuwait.com"),
                SimpleNamespace(domain="theperfumesclub.com"),
            ],
        )

        async def fake_woo(domain, product_name, currency="BHD", resolved_category=None):
            if domain == "theperfumesclub.com":
                return _genuine_woo_hit()
            return _converted_kwd_hit()
        monkeypatch.setattr(scs, "fetch_woocommerce_store_api_price", fake_woo)

        price = await svc._get_price(
            brand="Dior", name="Sauvage", variant="EDT 100ml",
            region="bahrain", search_query="Dior Sauvage EDT 100ml",
            nocache=True, category="fragrances",
        )
        assert price["source_method"] == "woo_store_api"
        assert price["retailer"] == "theperfumesclub.com"
        assert price["amount"] == pytest.approx(42.0)


# --------------------------------- R5: rollback gating (Wave B review MED) ---


@pytest.mark.asyncio
class TestConvertedTerminalFallbackRollbackGating:
    """With ENABLE_EXACT_PRICE_GATE=false, select_best degrades to min(amount)
    with ZERO identity/OOS/URL gating and should_cache_price is a no-op — an
    unconditional R5 park would serve+cache a wrong-SKU cheapest converted hit,
    a serving+write path the flag-OFF baseline (b207bfa) never had. The park
    must be gated on exact_gate_enabled(): flag-OFF restores the legacy
    terminal exactly (seed the observations, NO park, Tier-3 estimate)."""

    async def test_flag_off_converted_only_no_park_falls_to_estimate(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        svc, price, _ = await _run_converted_only_scenario(monkeypatch)
        assert price.get("source_method") != "converted_usd", (
            "flag-OFF still parked/served the R5 converted terminal fallback — "
            "the park must be gated on exact_gate_enabled()"
        )
        # legacy terminal: the cascade falls through to the Tier-3 estimate
        assert price.get("estimated") is True
        assert not svc._parked_price, (
            f"flag-OFF wrote the _parked_price mirror: {svc._parked_price!r}"
        )

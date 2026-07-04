# -*- coding: utf-8 -*-
"""genuine-price Wave-2 B3b - the NARROW OFF-CLOCK LLM variant-hint.

Recovers the CORRECT-product misses whose family is NOT in the curated B3a
reference: when _variant_hint_lookup returns "unknown" on a Class-B ambiguous
axis, the OFF-CLOCK warmer consults a narrow gpt-4o-mini disambiguator (Redis
verdict-cache first, cost-capped, fail-closed) instead of fail-closing blindly.

HARD INVARIANTS pinned here:
  1. LLM NEVER constructed/called on the live 15s path: fires ONLY when ALL of
     variant_descriptor_axes_enabled() AND ENABLE_VARIANT_LLM_HINT AND the warm
     signal AND curated=="unknown". The live-path assertion patches the client
     factory to RAISE and proves it is never called.
  2. Consulted at cache-WRITE time only (via warmer_write_veto_async).
  3. Fail-closed default (flag off / low confidence / client error / cap
     exceeded / "unknown" response) = VETO the write.
  4. Redis verdict-cache HIT short-circuits ($0, no client construction).
  5. Flag-OFF byte-identical (B3a battery re-run separately).

The OpenAI client + Redis are MOCKED throughout -- NEVER a live LLM in the suite.
ASCII-only source (Windows discipline).
"""
import asyncio

import pytest

from app.services import price_service as ps
from app.services import openai_service
from app.services import cache_service


# --------------------------------------------------------------------------
# Fixtures: gate ON, axes ON, LLM-hint ON, warm context ON. Redis verdict cache
# starts EMPTY (a fake in-memory store patched over _redis_get/_redis_set) and
# the per-run counter is reset each test.
# --------------------------------------------------------------------------
@pytest.fixture
def hint_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
    monkeypatch.setenv("WARMER_CONTEXT", "1")
    ps._reset_varhint_run_state()


@pytest.fixture
def fake_redis(monkeypatch):
    """An in-memory {key: value} store patched over cache_service._redis_get /
    _redis_set (the helpers import these lazily at call time). Starts empty."""
    store = {}

    def _get(key):
        return store.get(key)

    def _set(key, value, ex=None):
        store[key] = value
        return True

    monkeypatch.setattr(cache_service, "_redis_get", _get, raising=True)
    monkeypatch.setattr(cache_service, "_redis_set", _set, raising=True)
    return store


@pytest.fixture
def no_learned_write(monkeypatch):
    """Suppress the data/variant_hint_learned.json write so the suite never
    touches the committed data file."""
    monkeypatch.setattr(ps, "_varhint_append_learned", lambda *a, **k: None)


def _price(title, amount=95.0, url="https://theperfumesclub.com/product/x", brand="",
           in_stock=True):
    return {
        "title": title, "amount": amount, "currency": "BHD", "url": url,
        "brand": brand, "in_stock": in_stock, "source_method": "woo_store_api",
    }


def _mock_llm(monkeypatch, distinct, confidence, spy=None):
    """Patch openai_service.disambiguate_variant_line with a coroutine returning
    the given verdict. `spy` (a list) records each call's args."""
    async def _fake(category, query, candidate_title, axis):
        if spy is not None:
            spy.append((category, query, candidate_title, axis))
        return {"distinct_product": distinct, "confidence": confidence, "cost": 0.0001}
    monkeypatch.setattr(openai_service, "disambiguate_variant_line", _fake)


# A family deliberately NOT in the curated reference so _variant_hint_lookup
# returns "unknown" and the LLM path is exercised. "pour femme" is a real gender
# token so cd.gender fires; the base line is not a curated key.
_UNKNOWN_Q = "Obscure Niche House Ambrox"
_UNKNOWN_T = "Obscure Niche House Ambrox Pour Femme Eau de Parfum 100ml"


# ==========================================================================
# A) The async LLM-hint verdict paths (curated MISS -> LLM consulted)
# ==========================================================================
class TestAsyncHintVerdicts:
    def test_distinct_high_vetoes(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        _mock_llm(monkeypatch, distinct=True, confidence="high")
        allow, reason = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is False
        assert "gender" in (reason or "").lower()

    def test_same_high_allows(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        _mock_llm(monkeypatch, distinct=False, confidence="high")
        allow, _ = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is True

    def test_low_confidence_failclosed_veto(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        _mock_llm(monkeypatch, distinct=True, confidence="low")
        allow, reason = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is False
        assert "unknown" in (reason or "").lower() or "fail" in (reason or "").lower()

    def test_unknown_response_failclosed_veto(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        _mock_llm(monkeypatch, distinct="unknown", confidence="high")
        allow, reason = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is False
        assert "unknown" in (reason or "").lower() or "fail" in (reason or "").lower()

    def test_client_error_failclosed_veto(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        # The real disambiguator swallows client errors -> {"unknown","low"}.
        async def _boom(category, query, candidate_title, axis):
            return {"distinct_product": "unknown", "confidence": "low", "cost": 0.0}
        monkeypatch.setattr(openai_service, "disambiguate_variant_line", _boom)
        allow, _ = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is False


# ==========================================================================
# B) Redis verdict-cache HIT short-circuits (no client construction)
# ==========================================================================
class TestVerdictCacheShortCircuit:
    def test_cache_hit_distinct_no_llm_call(self, hint_on, fake_redis, monkeypatch):
        # Pre-seed the verdict cache with "distinct" for this family/axis.
        key = ps._varhint_verdict_key(_UNKNOWN_Q, _UNKNOWN_T, "gender")
        fake_redis[key] = "distinct"
        # If the LLM is constructed at all, this raises.
        def _no_client(*a, **k):
            raise AssertionError("LLM client must NOT be constructed on a cache HIT")
        monkeypatch.setattr(openai_service, "get_client", _no_client)
        allow, reason = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is False
        assert "distinct" in (reason or "").lower()

    def test_cache_hit_same_no_llm_call(self, hint_on, fake_redis, monkeypatch):
        key = ps._varhint_verdict_key(_UNKNOWN_Q, _UNKNOWN_T, "gender")
        fake_redis[key] = "same"
        def _no_client(*a, **k):
            raise AssertionError("LLM client must NOT be constructed on a cache HIT")
        monkeypatch.setattr(openai_service, "get_client", _no_client)
        allow, _ = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is True

    def test_resolved_verdict_written_to_cache(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        # A first miss resolves via the LLM and the verdict is persisted so a
        # second consult short-circuits.
        spy = []
        _mock_llm(monkeypatch, distinct=True, confidence="high", spy=spy)
        asyncio.run(ps.warmer_write_veto_async(_UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        key = ps._varhint_verdict_key(_UNKNOWN_Q, _UNKNOWN_T, "gender")
        assert fake_redis.get(key) == "distinct"
        assert len(spy) == 1
        # Second call: cache hit, no new LLM call.
        asyncio.run(ps.warmer_write_veto_async(_UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert len(spy) == 1, "second consult must short-circuit on the cache"


# ==========================================================================
# C) VARHINT_MAX_CALLS_PER_RUN cap enforced (N+1th fails-closed WITHOUT calling)
# ==========================================================================
class TestPerRunCap:
    def test_cap_enforced_no_call_beyond_limit(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        monkeypatch.setenv("VARHINT_MAX_CALLS_PER_RUN", "2")
        ps._reset_varhint_run_state()
        spy = []
        _mock_llm(monkeypatch, distinct=True, confidence="high", spy=spy)
        # 3 DISTINCT families so no cache-hit short-circuits (each is a fresh miss).
        families = [
            ("Alpha House Musk", "Alpha House Musk Pour Femme EDP 100ml"),
            ("Beta House Amber", "Beta House Amber Pour Femme EDP 100ml"),
            ("Gamma House Rose", "Gamma House Rose Pour Femme EDP 100ml"),
        ]
        results = []
        for q, t in families:
            results.append(asyncio.run(
                ps.warmer_write_veto_async(q, _price(t), "fragrances")))
        # Only 2 LLM calls happened; the 3rd fail-closed WITHOUT calling.
        assert len(spy) == 2, f"cap=2 must limit to 2 calls, got {len(spy)}"
        # First two resolved distinct -> veto; third fail-closed -> also veto.
        assert all(allow is False for allow, _ in results)
        # The 3rd reason is the fail-closed unknown, not a resolved distinct.
        assert "unknown" in (results[2][1] or "").lower() \
            or "fail" in (results[2][1] or "").lower()

    def test_reset_run_state_clears_counter(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        monkeypatch.setenv("VARHINT_MAX_CALLS_PER_RUN", "1")
        ps._reset_varhint_run_state()
        spy = []
        _mock_llm(monkeypatch, distinct=True, confidence="high", spy=spy)
        asyncio.run(ps.warmer_write_veto_async(
            "Alpha House Musk", _price("Alpha House Musk Pour Femme EDP 100ml"),
            "fragrances"))
        assert len(spy) == 1
        # Cap now hit; a fresh family fail-closes without calling.
        asyncio.run(ps.warmer_write_veto_async(
            "Beta House Amber", _price("Beta House Amber Pour Femme EDP 100ml"),
            "fragrances"))
        assert len(spy) == 1
        # Reset -> next run can call again.
        ps._reset_varhint_run_state()
        asyncio.run(ps.warmer_write_veto_async(
            "Gamma House Rose", _price("Gamma House Rose Pour Femme EDP 100ml"),
            "fragrances"))
        assert len(spy) == 2


# ==========================================================================
# D) LIVE-PATH assertion: NO OpenAI client construction at all when the warm
#    signal is absent OR ENABLE_VARIANT_LLM_HINT is off. Patch the client
#    factory to RAISE and assert it is never reached.
# ==========================================================================
class TestLivePathNoClientConstruction:
    def _raise_client(self, monkeypatch):
        def _boom(*a, **k):
            raise AssertionError("OpenAI client constructed on the live path")
        monkeypatch.setattr(openai_service, "get_client", _boom)

    def test_async_no_warm_signal_no_client(self, fake_redis, no_learned_write, monkeypatch):
        # Flags fully ON but NO warm signal (live path) -> the veto no-ops before
        # any axis detection; certainly no client.
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
        monkeypatch.delenv("WARMER_CONTEXT", raising=False)
        ps._reset_varhint_run_state()
        self._raise_client(monkeypatch)
        allow, _ = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is True  # live veto no-ops

    def test_async_hint_flag_off_no_client(self, fake_redis, no_learned_write, monkeypatch):
        # Warm signal present + axes on, but ENABLE_VARIANT_LLM_HINT OFF -> curated
        # unknown fail-closes WITHOUT ever constructing a client.
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.delenv("ENABLE_VARIANT_LLM_HINT", raising=False)
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        ps._reset_varhint_run_state()
        self._raise_client(monkeypatch)
        allow, reason = asyncio.run(ps.warmer_write_veto_async(
            _UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances"))
        assert allow is False  # curated-unknown fail-closed, no LLM
        assert "unknown" in (reason or "").lower() or "fail" in (reason or "").lower()

    def test_sync_veto_never_constructs_client(self, fake_redis, no_learned_write, monkeypatch):
        # The SYNC warmer_write_veto (called by should_cache_price on EVERY path,
        # incl. live) must NEVER construct a client even with the hint flag on and
        # warm context -- it only reads the $0 Redis verdict cache.
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        ps._reset_varhint_run_state()
        self._raise_client(monkeypatch)
        # Curated miss + empty verdict cache -> sync veto fail-closes, no LLM.
        allow, reason = ps.warmer_write_veto(_UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances")
        assert allow is False
        assert "unknown" in (reason or "").lower() or "fail" in (reason or "").lower()

    def test_sync_veto_reads_verdict_cache(self, fake_redis, monkeypatch):
        # The sync veto MAY use an already-resolved $0 verdict (live benefits) but
        # still never calls the LLM.
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
        monkeypatch.setenv("WARMER_CONTEXT", "1")
        ps._reset_varhint_run_state()
        self._raise_client(monkeypatch)
        key = ps._varhint_verdict_key(_UNKNOWN_Q, _UNKNOWN_T, "gender")
        fake_redis[key] = "same"
        allow, _ = ps.warmer_write_veto(_UNKNOWN_Q, _price(_UNKNOWN_T), "fragrances")
        assert allow is True  # cached "same" -> allow, no LLM


# ==========================================================================
# E) Curated HIT never reaches the LLM (B3a path unchanged by B3b)
# ==========================================================================
class TestCuratedHitNoLLM:
    def test_curated_distinct_no_llm(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        # Eros is curated (men) -> Pour Femme is DISTINCT via the reference; the
        # LLM must never be consulted.
        def _boom(*a, **k):
            raise AssertionError("LLM consulted on a curated HIT")
        monkeypatch.setattr(openai_service, "disambiguate_variant_line", _boom)
        allow, reason = asyncio.run(ps.warmer_write_veto_async(
            "Versace Eros", _price("Versace Eros Pour Femme Eau de Parfum 100ml"),
            "fragrances"))
        assert allow is False
        assert "gender" in (reason or "").lower()

    def test_curated_same_no_llm(self, hint_on, fake_redis, no_learned_write, monkeypatch):
        def _boom(*a, **k):
            raise AssertionError("LLM consulted on a curated HIT")
        monkeypatch.setattr(openai_service, "disambiguate_variant_line", _boom)
        allow, _ = asyncio.run(ps.warmer_write_veto_async(
            "YSL Black Opium",
            _price("YSL Black Opium For Women Eau de Parfum 90ml"), "fragrances"))
        assert allow is True


# ==========================================================================
# F) variant_llm_hint_enabled gating chain
# ==========================================================================
class TestHintEnabledGate:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.delenv("ENABLE_VARIANT_LLM_HINT", raising=False)
        assert ps.variant_llm_hint_enabled() is False

    def test_requires_axes(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.delenv("ENABLE_VARIANT_DESCRIPTOR_AXES", raising=False)
        monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
        assert ps.variant_llm_hint_enabled() is False

    def test_requires_exact_gate(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
        assert ps.variant_llm_hint_enabled() is False

    def test_on_when_all_set(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
        monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
        monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
        assert ps.variant_llm_hint_enabled() is True

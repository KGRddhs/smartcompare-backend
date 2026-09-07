"""Issue #54 — a Tier-3 GPT estimate must not clobber a concurrent genuine price.

There is no single-flight, lock or SETNX anywhere in `app/`, so the warmer, a
second live request and the nightly eval can all resolve the same `cache_key` at
once. Two defects then combine so a 12h estimate replaces a 7d genuine price at
BOTH cache layers:

  * **L1** — the Tier-3 terminal in `_get_price` wrote unconditionally
    (`_cache_set_async(cache_key, price, PRICE_CACHE_TTL // 2)` +
    `_save_price_to_db`). It never read the existing entry, so a slow estimate
    landed on top of a genuine price that arrived while it was in flight.
  * **L2** — `product_data_service.get_cached_price` read `.limit(1)` off a
    `fetched_at desc` order, and `product_prices` is append-only, so the estimate
    row appended after a genuine one *was* the newest row. Worse: once that
    estimate aged past its own 24h window the read returned `None` while a
    genuine row still inside its 7d window sat one position deeper — and the
    cascade re-burned a scrape.

Both halves ride ONE default-OFF flag, `ENABLE_GENUINE_PRICE_CLOBBER_GUARD`,
because they are one defect (the write guard alone still leaves already-written
estimate rows shadowing genuine ones at L2; the read preference alone still loses
the L1 entry).

What each part of this file is worth:
  * `is_genuine_source_method` — the string-level predicate the L2 selector needs.
    Hand-copying `_GENUINE_BH_SOURCE_METHODS` into product_data_service is exactly
    the drift defect tracked in #67, so there is a pin that the selector CALLS the
    canonical predicate and does not re-derive it.
  * Parity — `is_genuine_price` / `price_cache_ttl` must answer identically after
    being refactored onto the new helper.
  * The flag — default OFF, per-call read, and an AST pin that the env string is
    never touched at module import.
  * `_persist_tier3_estimate` — both flag directions x genuine / estimate /
    converted / missing L1 entry, plus the fail-open Redis path.
  * The race, end-to-end through `_get_price`: the genuine price *lands while the
    GPT call is in flight* (the L1 read at the top of `_get_price` has already
    happened and missed), and the Tier-3 terminal must not overwrite it. Flag OFF
    reproduces the bug in the same harness — that is what makes the ON assertion
    load-bearing rather than vacuous.
  * The L2 selector — as a pure unit AND driven through `get_cached_price` with a
    mock Supabase, both flag directions, plus the `.limit()` widening.

All free-tier: no network, no credentials, no live Redis, no live Supabase.
"""
from __future__ import annotations

import ast
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from app.services import price_service as ps  # noqa: E402
from app.services import product_data_service as pds  # noqa: E402
from app.services import structured_comparison_service as scs  # noqa: E402

FLAG = "ENABLE_GENUINE_PRICE_CLOBBER_GUARD"

_APP = Path(__file__).resolve().parent.parent / "app" / "services"
SCS_PATH = _APP / "structured_comparison_service.py"
PDS_PATH = _APP / "product_data_service.py"
PS_PATH = _APP / "price_service.py"

GENUINE = {"amount": 45.0, "currency": "BHD", "source_method": "woo_store_api"}
ESTIMATE = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
CONVERTED = {"amount": 60.0, "currency": "BHD", "source_method": "converted_usd"}


@pytest.fixture(autouse=True)
def _flag_off_by_default(monkeypatch):
    """`.env` is loaded with override=True by conftest; make every test state its
    own flag position instead of inheriting one."""
    monkeypatch.delenv(FLAG, raising=False)


# ---------------------------------------------------------------------------
# 1. The canonical string predicate + parity of what was refactored onto it
# ---------------------------------------------------------------------------


class TestIsGenuineSourceMethod:
    @pytest.mark.parametrize("method", sorted(ps._GENUINE_BH_SOURCE_METHODS))
    def test_every_genuine_method_is_genuine(self, method):
        assert ps.is_genuine_source_method(method) is True

    @pytest.mark.parametrize(
        "method",
        ["converted_usd", "converted_fallback", "estimated", "gpt_organic_extract",
         "validation_rejected", "sitemap_no_match", "some_future_method"],
    )
    def test_non_genuine_methods_are_not_genuine(self, method):
        assert ps.is_genuine_source_method(method) is False

    def test_blank_and_missing_are_not_genuine(self):
        assert ps.is_genuine_source_method(None) is False
        assert ps.is_genuine_source_method("") is False
        assert ps.is_genuine_source_method("   ") is False

    def test_genuine_apex_carrying_a_converted_or_estimate_token_is_not_genuine(self):
        assert ps.is_genuine_source_method("page_scrape_jsonld_converted") is False
        assert ps.is_genuine_source_method("local_bhd_estimate") is False

    def test_case_insensitive(self):
        assert ps.is_genuine_source_method("WOO_STORE_API") is True


class TestPredicateParityAfterTheRefactor:
    """`is_genuine_price` now delegates to `is_genuine_source_method`, and
    `price_cache_ttl` delegates to `is_genuine_price`. Pin that neither answer
    moved — the delegation is the one way this could have drifted."""

    @pytest.mark.parametrize("method", sorted(ps._GENUINE_BH_SOURCE_METHODS))
    def test_genuine_dicts_still_genuine_and_still_7d(self, method):
        assert ps.is_genuine_price({"source_method": method}) is True
        assert ps.price_cache_ttl({"source_method": method}) == ps.GENUINE_PRICE_CACHE_TTL

    @pytest.mark.parametrize(
        "price",
        [
            None, "not-a-dict", {}, {"source_method": ""}, {"source_method": "   "},
            {"source_method": None}, {"source_method": "converted_usd"},
            {"source_method": "estimated"}, {"source_method": "converted_fallback"},
            {"source_method": "page_scrape_jsonld_converted"},
            {"source_method": "local_bhd_estimate"},
            {"source_method": "some_future_method"},
        ],
    )
    def test_everything_else_still_non_genuine_and_still_24h(self, price):
        assert ps.is_genuine_price(price) is False
        assert ps.price_cache_ttl(price) == ps.PRICE_CACHE_TTL

    def test_the_two_ttls_are_distinct(self):
        # Guards the parity assertions from being vacuous.
        assert ps.GENUINE_PRICE_CACHE_TTL != ps.PRICE_CACHE_TTL

    def test_dict_and_string_predicates_agree_on_every_method(self):
        methods = sorted(ps._GENUINE_BH_SOURCE_METHODS) + [
            "", "   ", "converted_usd", "estimated", "whatever", "LOCAL_BHD",
        ]
        for m in methods:
            assert ps.is_genuine_price({"source_method": m}) is ps.is_genuine_source_method(m)


# ---------------------------------------------------------------------------
# 2. The flag
# ---------------------------------------------------------------------------


class TestFlagContract:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv(FLAG, raising=False)
        assert ps.genuine_clobber_guard_enabled() is False
        assert pds._genuine_clobber_guard_enabled() is False

    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on", " on "])
    def test_truthy_values_enable(self, monkeypatch, value):
        monkeypatch.setenv(FLAG, value)
        assert ps.genuine_clobber_guard_enabled() is True
        assert pds._genuine_clobber_guard_enabled() is True

    @pytest.mark.parametrize("value", ["", "false", "0", "no", "off", "maybe"])
    def test_falsy_values_disable(self, monkeypatch, value):
        monkeypatch.setenv(FLAG, value)
        assert ps.genuine_clobber_guard_enabled() is False
        assert pds._genuine_clobber_guard_enabled() is False

    def test_read_per_call_not_cached_at_import(self, monkeypatch):
        # The modules were imported at the top of this file with the flag unset;
        # a value set NOW must still be observed (exact_gate_enabled idiom).
        monkeypatch.delenv(FLAG, raising=False)
        assert ps.genuine_clobber_guard_enabled() is False
        monkeypatch.setenv(FLAG, "true")
        assert ps.genuine_clobber_guard_enabled() is True
        assert pds._genuine_clobber_guard_enabled() is True
        monkeypatch.setenv(FLAG, "false")
        assert ps.genuine_clobber_guard_enabled() is False
        assert pds._genuine_clobber_guard_enabled() is False

    def test_l2_helper_delegates_and_never_re_reads_the_env_itself(self, monkeypatch):
        """product_data_service must not grow its own copy of the env parse — it
        has to call the ONE definition in price_service."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setattr(ps, "genuine_clobber_guard_enabled", lambda: False)
        assert pds._genuine_clobber_guard_enabled() is False

    def test_l2_helper_fails_closed_when_the_import_blows_up(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def _boom(name, *args, **kwargs):
            if name == "app.services.price_service":
                raise RuntimeError("import exploded")
            return real_import(name, *args, **kwargs)

        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setattr(builtins, "__import__", _boom)
        assert pds._genuine_clobber_guard_enabled() is False


# ---------------------------------------------------------------------------
# 3. The L1 write guard, unit
# ---------------------------------------------------------------------------


def _svc():
    return scs.StructuredComparisonService()


_UNSET = object()


class _Writes:
    """Records what the terminal actually wrote."""

    def __init__(self, monkeypatch, existing):
        self.set_calls: list = []
        self.db_calls: list = []
        self.get_keys: list = []
        monkeypatch.setattr(
            scs, "set_cached",
            lambda k, v, t: self.set_calls.append((k, v, t)) or True,
        )
        monkeypatch.setattr(
            scs, "get_cached",
            lambda k: self.get_keys.append(k) or (
                dict(existing) if isinstance(existing, dict) else existing
            ),
        )
        self.svc = _svc()
        self.svc._save_price_to_db = lambda *a, **k: self.db_calls.append(a)

    async def run(self, price=None, category=_UNSET):
        """`category` is OMITTED entirely unless a test names one, so the
        signature default (None = today's answer for any caller that does not
        thread it) is exercised by every pre-existing case here."""
        kwargs = {} if category is _UNSET else {"category": category}
        return await self.svc._persist_tier3_estimate(
            "price:bahrain:iphone_15_128gb", "Apple", "iPhone 15", "128GB",
            "bahrain", dict(price if price is not None else ESTIMATE), **kwargs,
        )


class TestPersistTier3Estimate:
    @pytest.mark.asyncio
    async def test_flag_on_genuine_l1_entry_blocks_both_writes(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        w = _Writes(monkeypatch, GENUINE)
        wrote = await w.run()
        assert wrote is False
        assert w.set_calls == []
        assert w.db_calls == []
        # ...and it did read the existing entry under the price key.
        assert w.get_keys == ["price:bahrain:iphone_15_128gb"]

    @pytest.mark.asyncio
    async def test_flag_on_missing_l1_entry_writes_at_the_half_ttl(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        w = _Writes(monkeypatch, None)
        wrote = await w.run()
        assert wrote is True
        assert len(w.set_calls) == 1
        key, value, ttl = w.set_calls[0]
        assert key == "price:bahrain:iphone_15_128gb"
        assert value["source_method"] == "estimated"
        assert ttl == ps.PRICE_CACHE_TTL // 2
        assert len(w.db_calls) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "existing",
        [ESTIMATE, CONVERTED, {"amount": 1.0, "source_method": "whatever"},
         {"amount": 1.0}, "not-a-dict"],
        ids=["estimated", "converted_usd", "unknown_method", "no_method", "not_a_dict"],
    )
    async def test_flag_on_non_genuine_l1_entry_still_writes(self, monkeypatch, existing):
        monkeypatch.setenv(FLAG, "true")
        w = _Writes(monkeypatch, existing)
        assert await w.run() is True
        assert len(w.set_calls) == 1
        assert len(w.db_calls) == 1

    @pytest.mark.asyncio
    async def test_flag_off_writes_over_a_genuine_entry_without_even_reading_it(
        self, monkeypatch
    ):
        """Flag-OFF byte-identity: the pre-#54 terminal never looked at L1 and
        always wrote. This is also the assertion that keeps the flag-ON test
        above honest — the two differ ONLY by the flag."""
        monkeypatch.delenv(FLAG, raising=False)
        w = _Writes(monkeypatch, GENUINE)
        assert await w.run() is True
        assert w.get_keys == []  # no extra Redis round trip when OFF
        assert len(w.set_calls) == 1
        assert w.set_calls[0][2] == ps.PRICE_CACHE_TTL // 2
        assert len(w.db_calls) == 1

    @pytest.mark.asyncio
    async def test_fail_open_when_the_l1_read_raises(self, monkeypatch):
        """A Redis hiccup must never cost us the estimate we already paid GPT for."""
        monkeypatch.setenv(FLAG, "true")

        def _boom(key):
            raise RuntimeError("upstash down")

        w = _Writes(monkeypatch, None)
        monkeypatch.setattr(scs, "get_cached", _boom)
        assert await w.run() is True
        assert len(w.set_calls) == 1
        assert len(w.db_calls) == 1

    @pytest.mark.asyncio
    async def test_the_guard_read_honours_the_redis_offload_flag(self, monkeypatch):
        import threading

        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
        seen: dict = {}
        w = _Writes(monkeypatch, None)
        monkeypatch.setattr(
            scs, "get_cached",
            lambda k: seen.setdefault("thread", threading.current_thread()),
        )
        await w.run()
        assert seen["thread"] is not threading.current_thread()


# ---------------------------------------------------------------------------
# 3b. Guard READ PARITY with `_get_price`'s own L1 read
#
# Cache-coherence review of 7dd04c1, finding #3 (P2): the guard re-reads the SAME
# L1 key `_get_price` read ~2,200 lines above it, but applied NEITHER of that
# read's two rules. Half of that is now fixed and half is a documented decision:
#
#   * identity revalidation — FIXED. `_get_price` does
#     `if cached and not _cache_price_identity_ok(cached, brand, name, category):
#     cached = None`, so a genuine-method entry whose stored title does not match
#     the request is dropped on EVERY read. Blocking the estimate write on it
#     protected a price nobody can be served. The guard now runs the same
#     predicate, with `category` threaded in from `_get_price` because the verdict
#     is category-sensitive.
#   * `price_nocache` — DELIBERATELY NOT applied; see
#     TestNocacheIsNotAnEscapeHatch below.
# ---------------------------------------------------------------------------

# A genuine-method L1 entry whose title is a DIFFERENT SKU than the request
# ("Apple iPhone 15"): the read path drops it, so it must not block the write.
GENUINE_WRONG_TITLE = {
    "amount": 45.0, "currency": "BHD", "source_method": "woo_store_api",
    "title": "Apple iPhone 15 Pro Max 256GB",
}
# ...and one whose title matches: the read path serves it, so it must block.
GENUINE_RIGHT_TITLE = {
    "amount": 45.0, "currency": "BHD", "source_method": "woo_store_api",
    "title": "Apple iPhone 15 128GB",
}


class TestGuardReadParityWithTheReadPath:
    """Only an L1 entry the READ path would actually serve may block the write."""

    @pytest.fixture(autouse=True)
    def _gate_on(self, monkeypatch):
        """`_cache_price_identity_ok` is a no-op when ENABLE_EXACT_PRICE_GATE is
        OFF, so state the position explicitly instead of inheriting `.env`'s.
        (Default is ON, and it is ON in prod.)"""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")

    @pytest.mark.asyncio
    async def test_a_genuine_entry_that_passes_revalidation_still_blocks(
        self, monkeypatch
    ):
        w = _Writes(monkeypatch, GENUINE_RIGHT_TITLE)
        assert await w.run(category="electronics") is False
        assert w.set_calls == []
        assert w.db_calls == []

    @pytest.mark.asyncio
    async def test_a_genuine_entry_that_fails_revalidation_does_not_block(
        self, monkeypatch
    ):
        """THE fix. Pre-parity this returned False and wrote nothing, protecting an
        entry `_get_price` discards on every single read."""
        w = _Writes(monkeypatch, GENUINE_WRONG_TITLE)
        assert await w.run(category="electronics") is True
        assert len(w.set_calls) == 1
        assert w.set_calls[0][1]["source_method"] == "estimated"
        assert w.set_calls[0][2] == ps.PRICE_CACHE_TTL // 2
        assert len(w.db_calls) == 1

    @pytest.mark.asyncio
    async def test_the_threaded_category_is_what_makes_the_verdict(self, monkeypatch):
        """Why `category` had to be threaded rather than left at its default: the
        SAME entry passes revalidation with no category and FAILS under
        `electronics`. A guard reading with `category=None` would go on protecting
        exactly the entries the read path (which always has the real category)
        throws away — i.e. it would look fixed and not be."""
        assert scs._cache_price_identity_ok(
            GENUINE_WRONG_TITLE, "Apple", "iPhone 15", None) is True
        assert scs._cache_price_identity_ok(
            GENUINE_WRONG_TITLE, "Apple", "iPhone 15", "electronics") is False

        w_default = _Writes(monkeypatch, GENUINE_WRONG_TITLE)
        assert await w_default.run() is False          # category omitted -> None
        w_threaded = _Writes(monkeypatch, GENUINE_WRONG_TITLE)
        assert await w_threaded.run(category="electronics") is True

    @pytest.mark.asyncio
    async def test_a_title_less_genuine_entry_still_blocks(self, monkeypatch):
        """Regression: `_cache_price_identity_ok` serves a title-less entry (nothing
        to verify, don't over-invalidate), so the guard must keep protecting it —
        this is the shape every pre-existing case in this file uses."""
        w = _Writes(monkeypatch, GENUINE)
        assert await w.run(category="electronics") is False
        assert w.set_calls == []

    @pytest.mark.asyncio
    async def test_a_wrong_title_entry_that_is_NOT_genuine_never_reaches_the_check(
        self, monkeypatch
    ):
        """Genuineness is still the first question: a non-genuine entry is written
        over without any revalidation, exactly as before."""
        called: list = []
        monkeypatch.setattr(
            scs, "_cache_price_identity_ok",
            lambda *a, **k: called.append(a) or False,
        )
        w = _Writes(monkeypatch, dict(ESTIMATE, title="Apple iPhone 15 Pro Max"))
        assert await w.run(category="electronics") is True
        assert called == []

    @pytest.mark.asyncio
    async def test_exact_gate_off_means_no_revalidation_so_the_guard_still_blocks(
        self, monkeypatch
    ):
        """Coupling, stated: the parity fix inherits `ENABLE_EXACT_PRICE_GATE`.
        With that gate OFF `_cache_price_identity_ok` returns True for everything,
        so the guard's behaviour is the pre-parity behaviour. Nothing here is a
        second env fork — it is the same predicate the read path is subject to."""
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        w = _Writes(monkeypatch, GENUINE_WRONG_TITLE)
        assert await w.run(category="electronics") is False
        assert w.set_calls == []

    @pytest.mark.asyncio
    async def test_a_raising_revalidation_keeps_protecting(self, monkeypatch):
        """Fail-SAFE, the opposite direction from the L1 READ's fail-open: the read
        is fail-OPEN (a Redis hiccup must not cost us the estimate we paid GPT
        for), but a revalidation that BLOWS UP must not be the thing that lets an
        estimate land on a genuine price. It keeps today's answer."""
        def _boom(*a, **k):
            raise RuntimeError("descriptor extractor exploded")

        monkeypatch.setattr(scs, "_cache_price_identity_ok", _boom)
        w = _Writes(monkeypatch, GENUINE_WRONG_TITLE)
        assert await w.run(category="electronics") is False
        assert w.set_calls == []

    @pytest.mark.asyncio
    async def test_flag_off_never_revalidates_and_still_writes(self, monkeypatch):
        """Flag-OFF byte-identity: no L1 read, therefore no revalidation, and the
        `category` argument is never looked at."""
        monkeypatch.delenv(FLAG, raising=False)
        called: list = []
        monkeypatch.setattr(
            scs, "_cache_price_identity_ok",
            lambda *a, **k: called.append(a) or True,
        )
        w = _Writes(monkeypatch, GENUINE_RIGHT_TITLE)
        assert await w.run(category="electronics") is True
        assert w.get_keys == []
        assert called == []
        assert len(w.set_calls) == 1
        assert len(w.db_calls) == 1


# ---------------------------------------------------------------------------
# 4. The race, end-to-end through _get_price
# ---------------------------------------------------------------------------


@pytest.fixture
def race_harness(monkeypatch):
    """Drive `_get_price` all the way to the Tier-3 terminal with the whole
    cascade stubbed empty, and simulate the RACE: the concurrent request's
    genuine price lands in L1 *while the GPT training-data call is in flight*, so
    the L1 read at the top of `_get_price` has already missed.

    #54 x #53 (cache-coherence review finding #1) — the harness ALSO observes the
    third write to this logical slot, the 30d `nogenuine:` sentinel. That write does
    NOT go through `scs.set_cached` (which this fixture patches), it goes through the
    module-level `scs.set_negative_cache` imported at scs.py:54, so a harness that
    watches only `set_cached` is structurally blind to it — which is exactly how the
    defect survived #54's own race test. `scs.delete_cached` is recorded too so #53's
    sentinel invalidation is visible in the same timeline."""
    state = {
        "landed": False, "sets": [], "db": 0,
        "sentinel_sets": [], "sentinel_deletes": [],
        # Optional hook: an awaitable run at the instant the GPT call resolves, i.e.
        # the point where the concurrent resolver banks its genuine price. Used by
        # the both-flags-ON composition test to run the REAL #53 writer there.
        "on_race": None,
    }
    # The key `_get_price` will actually build for the arguments `_run_race` passes —
    # computed with the production builder so the sentinel-key assertions below pin
    # the real namespaced key, not a hand-written one.
    state["cache_key"] = scs.build_size_aware_price_cache_key(
        "Apple", "iPhone 15", "128GB", "bahrain",
        "Apple iPhone 15 128GB price", category="electronics",
    )

    def _get_cached(key: str):
        if state["landed"] and str(key).startswith("price:"):
            return dict(GENUINE)
        return None

    monkeypatch.setattr(scs, "get_cached", _get_cached)
    monkeypatch.setattr(
        scs, "set_cached", lambda k, v, t: state["sets"].append((k, v, t)) or True
    )
    monkeypatch.setattr(
        scs, "set_negative_cache",
        lambda k, v, t: state["sentinel_sets"].append((k, v, t)) or True,
    )
    monkeypatch.setattr(
        scs, "delete_cached",
        lambda k: state["sentinel_deletes"].append(k) or True,
    )
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    # Neutralize the free genuine-BH direct-fetch selectors (they fire REAL
    # network fetches) — same recipe as tests/test_converted_price_before_estimate_t1.
    for fn in ("get_algolia_sources_for_category", "get_unbxd_sources_for_category",
               "get_shopify_sources_for_category", "get_noon_sources_for_category"):
        monkeypatch.setattr(scs, fn, lambda cat: [])
    monkeypatch.setattr(
        scs, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": [], "shopping_region": "bh"}),
    )
    monkeypatch.setattr(scs, "get_official_domain", lambda *a, **kw: None)
    monkeypatch.setattr(scs, "fetch_shopify_price", AsyncMock(return_value=None))
    monkeypatch.setattr(scs, "search_web", AsyncMock(return_value={"organic": []}))
    monkeypatch.setattr(scs, "fan_out_price_lookup", AsyncMock(return_value={"best": None}))
    monkeypatch.setattr(
        scs, "search_price_organic",
        AsyncMock(return_value={"organic": [], "knowledge_graph": None}),
    )
    monkeypatch.setattr(scs, "extract_price", AsyncMock(return_value=(None, {})))

    async def _training(*a, **k):
        # THE RACE: a concurrent resolver banks a genuine BH price at L1 while
        # this request is still waiting on GPT.
        state["landed"] = True
        if state["on_race"] is not None:
            await state["on_race"]()
        return ({"amount": 290.0, "currency": "BHD"}, {})

    monkeypatch.setattr(scs, "extract_price_from_training_data", _training)

    svc = scs.get_comparison_service()
    svc._save_price_to_db = MagicMock(side_effect=lambda *a, **k: state.update(
        db=state["db"] + 1))
    state["svc"] = svc
    return state


async def _run_race(state):
    return await state["svc"]._get_price(
        brand="Apple", name="iPhone 15", variant="128GB", region="bahrain",
        search_query="Apple iPhone 15 128GB price", nocache=True,
        category="electronics",
    )


def _estimate_writes(state):
    return [
        c for c in state["sets"]
        if isinstance(c[1], dict) and c[1].get("source_method") == "estimated"
    ]


def _sentinel_writes(state):
    """The THIRD write to the same logical slot: `nogenuine:{cache_key}`, planted by
    `_record_negative_price_cache` through the module-level `scs.set_negative_cache`
    (NOT through `scs.set_cached`, which is why `_estimate_writes` cannot see it)."""
    return list(state["sentinel_sets"])


class TestTier3RaceEndToEnd:
    @pytest.mark.asyncio
    async def test_flag_off_reproduces_the_bug(self, monkeypatch, race_harness):
        """Today's behaviour, in the same harness: the estimate overwrites the
        genuine price that landed mid-flight, at BOTH layers."""
        monkeypatch.delenv(FLAG, raising=False)
        result = await _run_race(race_harness)
        assert result["source_method"] == "estimated"
        writes = _estimate_writes(race_harness)
        assert len(writes) == 1, "the pre-#54 terminal always wrote the estimate"
        assert writes[0][2] == ps.PRICE_CACHE_TTL // 2
        assert race_harness["db"] == 1

    @pytest.mark.asyncio
    async def test_flag_on_preserves_the_genuine_price(self, monkeypatch, race_harness):
        monkeypatch.setenv(FLAG, "true")
        result = await _run_race(race_harness)
        # The caller still gets its estimate — the issue explicitly does NOT
        # change what this request returns.
        assert result["source_method"] == "estimated"
        assert result["amount"] == pytest.approx(290.0)
        # ...but nothing was written over the genuine entry, at ANY layer.
        # #54 x #53 — "either layer" used to mean L1 + L2 only. The 30d
        # `nogenuine:` sentinel is a THIRD write to the same logical slot and it
        # OUTLIVES the 7d genuine entry the guard just protected, so it belongs in
        # this assertion; before the fix it fired here and this test could not see it
        # (the harness patched `set_cached`, the sentinel goes through
        # `set_negative_cache`).
        assert _estimate_writes(race_harness) == []
        assert race_harness["db"] == 0
        assert _sentinel_writes(race_harness) == []

    @pytest.mark.asyncio
    async def test_flag_on_without_a_race_still_caches_the_estimate(
        self, monkeypatch, race_harness
    ):
        """Control: no concurrent genuine price -> the estimate is cached and
        persisted exactly as before. The guard must not break the normal
        structural-dead-end path."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setattr(scs, "get_cached", lambda k: None)
        result = await _run_race(race_harness)
        assert result["source_method"] == "estimated"
        writes = _estimate_writes(race_harness)
        assert len(writes) == 1
        assert writes[0][2] == ps.PRICE_CACHE_TTL // 2
        assert race_harness["db"] == 1


# ---------------------------------------------------------------------------
# 4a. THE `nocache` DECISION (cache-coherence finding #3, consequence (b))
#
# The guard does NOT honour `price_nocache`. That is deliberate, and this section
# is the pin that lets the merge note SAY it: with ENABLE_GENUINE_PRICE_CLOBBER_
# GUARD ON, `?nocache=true` no longer replaces a genuine L1 entry with a Tier-3
# estimate — the poisoned-entry remedy is the #55 flush (DELETE /text/cache).
# ---------------------------------------------------------------------------


class TestNocacheIsNotAnEscapeHatch:
    @pytest.mark.asyncio
    async def test_nocache_no_longer_replaces_a_genuine_l1_entry_with_an_estimate(
        self, monkeypatch, race_harness
    ):
        """DECISION PIN — not a bug report.

        `_get_price` computes `price_nocache = nocache or _price_cache_bust_
        enabled()` and skips the L1 READ on it, so a forced refresh re-runs the
        routing escalation from scratch. The guard reads L1 anyway. Consequence:
        a `?nocache=true` refresh that degrades all the way to a Tier-3 estimate
        can no longer overwrite a genuine-method entry.

        KEEP IT. The warmer/seed race this issue exists for IS a forced refresh
        racing a genuine write, and "an estimate must never clobber a genuine
        price" does not acquire an exception because the caller asked loudly. The
        cost is real and is the thing to write down: `nocache` stops being one of
        the two documented remedies for a poisoned L1 entry. The remaining one is
        #55's `DELETE /api/v1/text/cache`, which REMOVES the entry instead of
        hoping a worse price lands on top of it.

        `_run_race` drives `_get_price(..., nocache=True)`. The read really was
        bypassed — the caller gets the 290.0 estimate, not the 45.0 genuine price
        sitting in L1 — and the write was still refused."""
        monkeypatch.setenv(FLAG, "true")
        result = await _run_race(race_harness)
        assert result["source_method"] == "estimated"
        assert result["amount"] == pytest.approx(290.0)   # nocache DID bypass L1
        assert _estimate_writes(race_harness) == []       # ...the guard did not
        assert race_harness["db"] == 0

    @pytest.mark.asyncio
    async def test_flag_off_nocache_does_replace_it(self, monkeypatch, race_harness):
        """The other direction, so the decision above is a CHANGE and not a
        restatement of today: with the flag OFF the same `nocache=True` refresh
        writes the estimate straight over the genuine entry."""
        monkeypatch.delenv(FLAG, raising=False)
        await _run_race(race_harness)
        writes = _estimate_writes(race_harness)
        assert len(writes) == 1
        assert writes[0][2] == ps.PRICE_CACHE_TTL // 2

    def test_the_named_remedy_is_a_real_endpoint(self):
        """The merge note points users at `DELETE /api/v1/text/cache`; make that a
        fact about the code rather than prose. #55 landed the live-price-key flush
        there behind ENABLE_FLUSH_LIVE_PRICE_KEY."""
        from app.api import text_routes

        assert hasattr(text_routes, "flush_product_cache")
        assert hasattr(text_routes, "_flush_price_cache_keys")
        assert hasattr(text_routes, "flush_live_price_key_enabled")
        assert any(
            getattr(r, "path", "").endswith("/cache")
            and "DELETE" in getattr(r, "methods", set())
            for r in text_routes.router.routes
        ), "DELETE /cache is not registered on the text router"


# ---------------------------------------------------------------------------
# 4b. #54 x #53 — the sentinel is the third write, and the guard must withhold it
#
# Cache-coherence review of 7dd04c1, finding #1 (P1), reproduced with this very
# harness: with BOTH flags ON the guard blocked the L1 and L2 writes and the
# terminal then planted `nogenuine:price:...` for 30d holding the estimate anyway.
# Because the negcache read in `_get_price` sits AFTER the L1 and L2 reads, and
# both genuine entries live only GENUINE_PRICE_CACHE_TTL (7d), the day-0 estimate
# gets served for the remaining ~23 days — and #53's deleter can never fire again,
# because the sentinel short-circuits the cascade before any live resolution runs.
# ---------------------------------------------------------------------------


class TestSentinelWithheldWhenTheGuardFires:
    @pytest.mark.asyncio
    async def test_flag_on_guard_fires_no_sentinel_is_planted(
        self, monkeypatch, race_harness
    ):
        """(b) The load-bearing one: guard ON + genuine already at L1 ->
        `set_negative_cache` is not called at all. Strip the `if _tier3_persisted:`
        branch in the Tier-3 terminal and this goes red with one 30d write."""
        monkeypatch.setenv(FLAG, "true")
        result = await _run_race(race_harness)
        assert result["source_method"] == "estimated"  # the caller still gets it
        assert race_harness["sentinel_sets"] == []

    @pytest.mark.asyncio
    async def test_flag_on_no_race_plants_the_sentinel_unchanged(
        self, monkeypatch, race_harness
    ):
        """(c) Guard ON but not fired (no genuine at L1) -> the structural
        dead-end sentinel is written exactly as before: same namespaced key, same
        payload, same 30d TTL. The fix must narrow the sentinel to the guard path
        ONLY."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setattr(scs, "get_cached", lambda k: None)
        result = await _run_race(race_harness)
        assert len(race_harness["sentinel_sets"]) == 1
        key, value, ttl = race_harness["sentinel_sets"][0]
        assert key == ps.negative_cache_key(race_harness["cache_key"])
        assert key.startswith("nogenuine:price:")
        assert value["source_method"] == "estimated"
        assert value["amount"] == pytest.approx(290.0)
        assert value is result  # the resolved estimate itself is the sentinel payload
        assert ttl == ps.NEGATIVE_PRICE_CACHE_TTL

    @pytest.mark.asyncio
    async def test_flag_off_plants_the_sentinel_unchanged(
        self, monkeypatch, race_harness
    ):
        """(d) Byte-identity pin. Flag OFF the guard never fires, so
        `_persist_tier3_estimate` always returns True and the sentinel write is the
        same unconditional call it has always been — including in the race, which is
        the case the flag exists to change."""
        monkeypatch.delenv(FLAG, raising=False)
        result = await _run_race(race_harness)
        assert len(race_harness["sentinel_sets"]) == 1
        key, value, ttl = race_harness["sentinel_sets"][0]
        assert key == ps.negative_cache_key(race_harness["cache_key"])
        assert value is result
        assert ttl == ps.NEGATIVE_PRICE_CACHE_TTL
        # ...and the pre-#54 clobber still happens when the flag is OFF: this test
        # asserts NO behaviour change, only that the sentinel half is untouched.
        assert len(_estimate_writes(race_harness)) == 1
        assert race_harness["db"] == 1

    @pytest.mark.asyncio
    async def test_both_flags_on_the_two_fixes_now_compose(
        self, monkeypatch, race_harness
    ):
        """(e) The composition test the wave was missing — the reviewer's exact
        end-to-end scenario with ENABLE_NEGCACHE_GENUINE_INVALIDATION AND
        ENABLE_GENUINE_PRICE_CLOBBER_GUARD both ON.

        Timeline inside one `_get_price`:
          t0   a prior dead-end resolution left `nogenuine:{key}` standing (30d);
          t1   the concurrent resolver banks a GENUINE price through #53's ONE
               writer (`_cache_price_and_clear_sentinel`) while this request is
               still blocked on GPT -> the sentinel is DELETED;
          t2   the in-flight estimate finishes, #54's guard withholds both writes;
          t3   the terminal must NOT re-plant the sentinel #53 just deleted.

        Before the fix, t3 re-created it — one fix undoing the other on the highest
        value path. `sentinel_deletes` proves #53 really ran here, so the empty
        `sentinel_sets` is a composition assertion and not a vacuous one."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_NEGCACHE_GENUINE_INVALIDATION", "true")

        async def _concurrent_genuine_resolver():
            # #53's real writer, unmocked, on the real key.
            await race_harness["svc"]._cache_price_and_clear_sentinel(
                race_harness["cache_key"], dict(GENUINE)
            )

        race_harness["on_race"] = _concurrent_genuine_resolver

        result = await _run_race(race_harness)

        # t1 really happened: #53 deleted the sentinel for this key.
        assert race_harness["sentinel_deletes"] == [
            ps.negative_cache_key(race_harness["cache_key"])
        ]
        # t2: the guard kept the genuine price at both layers.
        assert _estimate_writes(race_harness) == []
        assert race_harness["db"] == 0
        # t3: and nothing re-planted the sentinel behind #53's back.
        assert _sentinel_writes(race_harness) == []
        # The caller is still served its estimate — unchanged contract.
        assert result["source_method"] == "estimated"
        assert result["amount"] == pytest.approx(290.0)


# ---------------------------------------------------------------------------
# 5. The L2 row selector, pure
# ---------------------------------------------------------------------------


def _row(method: str, age: timedelta, amount: float = 1.0, **extra):
    row = {
        "amount": str(amount),
        "currency": "BHD",
        "retailer": "sporter.com",
        "url": "https://sporter.com/p",
        "source_method": method,
        "estimated": method == "estimated",
        "fetched_at": (datetime.now(timezone.utc) - age).isoformat(),
    }
    row.update(extra)
    return row


NOW = None  # resolved per call


def _select(rows):
    return pds._select_price_row(rows, datetime.now(timezone.utc))


class TestSelectPriceRow:
    def test_prefers_a_fresh_genuine_row_over_a_newer_estimate(self):
        rows = [_row("estimated", timedelta(hours=1), 70.0),
                _row("woo_store_api", timedelta(days=3), 45.0)]
        assert _select(rows)["source_method"] == "woo_store_api"

    def test_falls_back_to_the_estimate_when_the_genuine_row_is_out_of_its_window(self):
        rows = [_row("estimated", timedelta(hours=1), 70.0),
                _row("woo_store_api", timedelta(days=8), 45.0)]
        picked = _select(rows)
        assert picked["source_method"] == "estimated"

    def test_stale_estimate_does_not_hide_a_fresh_genuine_row(self):
        rows = [_row("estimated", timedelta(hours=30), 70.0),
                _row("woo_store_api", timedelta(days=3), 45.0)]
        assert _select(rows)["source_method"] == "woo_store_api"

    def test_nothing_fresh_returns_none(self):
        rows = [_row("estimated", timedelta(hours=30)),
                _row("woo_store_api", timedelta(days=8))]
        assert _select(rows) is None

    def test_empty_and_none_inputs(self):
        assert _select([]) is None
        assert _select(None) is None

    def test_newest_of_several_genuine_rows_wins(self):
        rows = [_row("woo_store_api", timedelta(days=5), 41.0),
                _row("local_bhd", timedelta(days=1), 42.0),
                _row("salla_api", timedelta(days=3), 43.0)]
        assert _select(rows)["amount"] == "42.0"

    def test_newest_fresh_row_wins_when_none_is_genuine(self):
        rows = [_row("converted_usd", timedelta(hours=10), 60.0),
                _row("estimated", timedelta(hours=2), 70.0)]
        assert _select(rows)["amount"] == "70.0"

    def test_input_order_does_not_matter(self):
        genuine = _row("woo_store_api", timedelta(days=3), 45.0)
        estimate = _row("estimated", timedelta(hours=1), 70.0)
        assert _select([genuine, estimate])["source_method"] == "woo_store_api"
        assert _select([estimate, genuine])["source_method"] == "woo_store_api"

    def test_malformed_rows_are_skipped_not_fatal(self):
        rows = [
            "not-a-dict",
            {"source_method": "woo_store_api"},                       # no fetched_at
            {"source_method": "woo_store_api", "fetched_at": "garbage"},
            {"source_method": "local_bhd", "fetched_at": None},
            _row("woo_store_api", timedelta(days=2), 45.0),
        ]
        assert _select(rows)["amount"] == "45.0"

    def test_all_rows_malformed_returns_none(self):
        assert _select(["x", {"fetched_at": "nope"}]) is None

    def test_no_freshness_window_is_widened(self):
        """A genuine row past 7d and an estimate past 24h are BOTH still rejected
        — the selector only reorders, it never extends a window."""
        assert _select([_row("woo_store_api", timedelta(days=8))]) is None
        assert _select([_row("estimated", timedelta(hours=25))]) is None
        assert _select([_row("converted_usd", timedelta(hours=25))]) is None


# ---------------------------------------------------------------------------
# 6. The L2 read, driven through get_cached_price
# ---------------------------------------------------------------------------


def _mock_supabase():
    client = MagicMock()
    client.table.return_value = client
    client.select.return_value = client
    client.eq.return_value = client
    client.single.return_value = client
    client.order.return_value = client
    client.limit.return_value = client
    return client


async def _cached_price(rows):
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data=rows)
    with patch("app.services.product_data_service.get_admin_supabase_client",
               return_value=client):
        result = await pds.get_cached_price("price:abc123def4", "bahrain")
    return result, client


EST_1H = lambda: _row("estimated", timedelta(hours=1), 70.0)          # noqa: E731
EST_30H = lambda: _row("estimated", timedelta(hours=30), 70.0)        # noqa: E731
GEN_3D = lambda: _row("woo_store_api", timedelta(days=3), 45.0)       # noqa: E731
GEN_8D = lambda: _row("woo_store_api", timedelta(days=8), 45.0)       # noqa: E731


class TestGetCachedPriceFlagOn:
    @pytest.fixture(autouse=True)
    def _on(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")

    @pytest.mark.asyncio
    async def test_estimate_no_longer_hides_a_fresh_genuine_row(self):
        result, _ = await _cached_price([EST_1H(), GEN_3D()])
        assert result["amount"] == 45.0
        assert result["source_method"] == "woo_store_api"

    @pytest.mark.asyncio
    async def test_genuine_row_outside_its_own_window_yields_the_estimate(self):
        result, _ = await _cached_price([EST_1H(), GEN_8D()])
        assert result["amount"] == 70.0
        assert result["source_method"] == "estimated"

    @pytest.mark.asyncio
    async def test_stale_estimate_over_a_fresh_genuine_row_no_longer_returns_none(self):
        result, _ = await _cached_price([EST_30H(), GEN_3D()])
        assert result is not None
        assert result["amount"] == 45.0

    @pytest.mark.asyncio
    async def test_regression_single_genuine_row_3d_is_returned(self):
        result, _ = await _cached_price([GEN_3D()])
        assert result["amount"] == 45.0

    @pytest.mark.asyncio
    async def test_regression_single_estimate_row_30h_is_none(self):
        result, _ = await _cached_price([EST_30H()])
        assert result is None

    @pytest.mark.asyncio
    async def test_regression_empty_result_is_none(self):
        result, _ = await _cached_price([])
        assert result is None

    @pytest.mark.asyncio
    async def test_scan_window_is_widened(self):
        _, client = await _cached_price([GEN_3D()])
        assert client.limit.call_args[0][0] == pds._L2_PRICE_ROW_SCAN
        assert pds._L2_PRICE_ROW_SCAN > 1


class TestGetCachedPriceFlagOffIsByteIdentical:
    """The pre-#54 answers, including the two WRONG ones the issue reports."""

    @pytest.fixture(autouse=True)
    def _off(self, monkeypatch):
        monkeypatch.delenv(FLAG, raising=False)

    @pytest.mark.asyncio
    async def test_newest_row_still_wins_even_when_it_hides_a_genuine_row(self):
        result, _ = await _cached_price([EST_1H(), GEN_3D()])
        assert result["source_method"] == "estimated"
        assert result["amount"] == 70.0

    @pytest.mark.asyncio
    async def test_stale_newest_estimate_still_returns_none(self):
        result, _ = await _cached_price([EST_30H(), GEN_3D()])
        assert result is None

    @pytest.mark.asyncio
    async def test_single_genuine_row_3d_is_returned(self):
        result, _ = await _cached_price([GEN_3D()])
        assert result["amount"] == 45.0

    @pytest.mark.asyncio
    async def test_single_estimate_row_30h_is_none(self):
        result, _ = await _cached_price([EST_30H()])
        assert result is None

    @pytest.mark.asyncio
    async def test_scan_window_is_still_one_row(self):
        _, client = await _cached_price([GEN_3D()])
        assert client.limit.call_args[0][0] == 1

    @pytest.mark.asyncio
    async def test_db_errors_are_still_swallowed(self):
        with patch("app.services.product_data_service.get_admin_supabase_client",
                   side_effect=Exception("DB down")):
            assert await pds.get_cached_price("k", "bahrain") is None


class TestGetCachedPriceFlagOnErrorHandling:
    @pytest.mark.asyncio
    async def test_db_errors_are_swallowed_with_the_guard_on(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        with patch("app.services.product_data_service.get_admin_supabase_client",
                   side_effect=Exception("DB down")):
            assert await pds.get_cached_price("k", "bahrain") is None

    @pytest.mark.asyncio
    async def test_all_rows_stale_returns_none(self, monkeypatch):
        monkeypatch.setenv(FLAG, "true")
        result, _ = await _cached_price([EST_30H(), GEN_8D()])
        assert result is None


# ---------------------------------------------------------------------------
# 7. AST pins — comments and docstrings cannot satisfy these
# ---------------------------------------------------------------------------


def _tree(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _class(tree, name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"class {name} not found")


def _func(scope, name):
    for node in scope.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found")


def _call_name(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else "?"
        return f"{base}.{f.attr}"
    return "?"


def _called(fn):
    return {_call_name(n) for n in ast.walk(fn) if isinstance(n, ast.Call)}


@pytest.fixture(scope="module")
def scs_tree():
    return _tree(SCS_PATH)


@pytest.fixture(scope="module")
def pds_tree():
    return _tree(PDS_PATH)


@pytest.fixture(scope="module")
def ps_tree():
    return _tree(PS_PATH)


class TestStructuralPins:
    def test_tier3_terminal_routes_through_the_guarded_writer(self, scs_tree):
        """`_get_price` must no longer contain a raw half-TTL price write; the
        Tier-3 terminal goes through `_persist_tier3_estimate`."""
        fn = _func(_class(scs_tree, "StructuredComparisonService"), "_get_price")
        raw_half_ttl = []
        routed = 0
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name == "self._persist_tier3_estimate":
                routed += 1
            elif name == "_cache_set_async" and len(node.args) == 3:
                ttl = node.args[2]
                if (isinstance(ttl, ast.BinOp) and isinstance(ttl.op, ast.FloorDiv)
                        and isinstance(ttl.left, ast.Name)
                        and ttl.left.id == "PRICE_CACHE_TTL"):
                    raw_half_ttl.append(node.lineno)
        assert routed == 1, "the Tier-3 terminal does not route through the writer"
        assert raw_half_ttl == [], (
            f"an unguarded PRICE_CACHE_TTL // 2 write survives at {raw_half_ttl}"
        )

    def test_the_writer_gates_on_the_flag_and_on_genuineness(self, scs_tree):
        fn = _func(_class(scs_tree, "StructuredComparisonService"),
                   "_persist_tier3_estimate")
        called = _called(fn)
        assert "genuine_clobber_guard_enabled" in called
        assert "_cache_get_async" in called
        assert "is_genuine_price" in called
        assert "_cache_set_async" in called
        assert "self._save_price_to_db" in called

    def test_the_writer_revalidates_identity_with_the_read_paths_helper(
        self, scs_tree
    ):
        """Read parity, structurally: the guard must call the SAME
        `_cache_price_identity_ok` the L1 read in `_get_price` calls (not a second
        copy of the rule), and must accept a `category` parameter to feed it —
        a docstring cannot satisfy either half."""
        fn = _func(_class(scs_tree, "StructuredComparisonService"),
                   "_persist_tier3_estimate")
        assert "_cache_price_identity_ok" in _called(fn)

        args = fn.args
        names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
        assert "category" in names, "the guard cannot revalidate on the read axes"
        # ...and it defaults, so every other caller keeps today's behaviour.
        defaulted = {
            a.arg for a, d in zip(args.args[len(args.args) - len(args.defaults):],
                                  args.defaults)
            if isinstance(d, ast.Constant) and d.value is None
        } | {
            a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults)
            if isinstance(d, ast.Constant) and d.value is None
        }
        assert "category" in defaulted, "`category` must default to None"

        # The read path uses the identical helper — that is what makes it PARITY.
        read = _func(_class(scs_tree, "StructuredComparisonService"), "_get_price")
        assert "_cache_price_identity_ok" in _called(read)

    def test_the_tier3_terminal_threads_the_real_category_into_the_writer(
        self, scs_tree
    ):
        """A defaulted parameter nobody passes is a no-op: the ONE production
        caller must hand the guard `_get_price`'s own `category`, because the
        revalidation verdict is category-sensitive."""
        fn = _func(_class(scs_tree, "StructuredComparisonService"), "_get_price")
        calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and _call_name(n) == "self._persist_tier3_estimate"
        ]
        assert len(calls) == 1
        kw = {k.arg: k.value for k in calls[0].keywords}
        assert "category" in kw, "the terminal does not thread `category`"
        assert isinstance(kw["category"], ast.Name) and kw["category"].id == "category"

    def test_the_tier3_sentinel_write_is_gated_on_the_persist_result(self, scs_tree):
        """REWRITTEN pin. It used to be `test_the_negative_cache_call_is_untouched`
        and asserted only that `self._record_negative_price_cache` still appeared in
        `_get_price` — "explicitly out of scope for #54". The cache-coherence review
        of 7dd04c1 (finding #1, P1) showed that omission is the defect: the withheld
        estimate was still sentinelled for 30d, outliving the 7d genuine entry the
        guard preserved, so #54 undid #53 with both flags ON.

        The pin therefore now says something stronger AND narrower:
          * the Tier-3 sentinel write (the kwargs-carrying call) must sit inside an
            `if` on the boolean `_persist_tier3_estimate` returns — a comment or a
            docstring cannot satisfy this;
          * the converted_fallback terminal's sentinel (the bare positional call, a
            different terminal with no guard in play) must stay UNCONDITIONAL, so
            this fix cannot silently widen into that path.
        """
        fn = _func(_class(scs_tree, "StructuredComparisonService"), "_get_price")

        # The name the terminal binds `_persist_tier3_estimate`'s bool to.
        targets = [
            node.targets[0].id
            for node in ast.walk(fn)
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Await)
            and _call_name(node.value.value) == "self._persist_tier3_estimate"
        ]
        assert len(targets) == 1, (
            "the Tier-3 terminal discards `_persist_tier3_estimate`'s return value "
            "instead of binding it"
        )
        persisted_name = targets[0]

        record_calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and _call_name(n) == "self._record_negative_price_cache"
        ]
        tier3_calls = [c for c in record_calls if c.keywords]
        fallback_calls = [c for c in record_calls if not c.keywords]
        assert len(tier3_calls) == 1, "the Tier-3 sentinel write is not where expected"
        assert len(fallback_calls) == 1, (
            "the converted_fallback sentinel write went missing"
        )

        gates = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.If)
            and isinstance(n.test, ast.Name)
            and n.test.id == persisted_name
        ]
        assert len(gates) == 1, (
            f"the Tier-3 sentinel write is not gated on `{persisted_name}`"
        )
        gated = {id(c) for c in ast.walk(gates[0]) if isinstance(c, ast.Call)}
        assert id(tier3_calls[0]) in gated, (
            "the Tier-3 `nogenuine:` sentinel is still planted unconditionally — the "
            "guard's withheld estimate would be cached for NEGATIVE_PRICE_CACHE_TTL"
        )
        assert id(fallback_calls[0]) not in gated, (
            "the converted_fallback sentinel must NOT be gated on the Tier-3 guard"
        )

    def test_l2_selector_uses_the_canonical_predicate_not_a_copy(self, pds_tree):
        """#67 — hand-copying `_GENUINE_BH_SOURCE_METHODS` is the defect. The
        selector must CALL price_service's predicate."""
        fn = _func(pds_tree, "_select_price_row")
        assert "is_genuine_source_method" in _called(fn)
        imported = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.ImportFrom) and n.module == "app.services.price_service"
        ]
        assert imported, "the predicate is not imported from price_service"
        assert any(a.name == "is_genuine_source_method"
                   for imp in imported for a in imp.names)

    def test_no_hand_copied_genuine_method_set_in_product_data_service(self, pds_tree):
        """No literal genuine-method string may be assigned into a set/frozenset
        in this module — that is how the two definitions would drift."""
        literals = {
            n.value for n in ast.walk(pds_tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        leaked = literals & set(ps._GENUINE_BH_SOURCE_METHODS)
        assert not leaked, f"genuine source_method strings hand-copied: {sorted(leaked)}"

    def test_get_cached_price_consults_the_flag_and_the_selector(self, pds_tree):
        fn = _func(pds_tree, "get_cached_price")
        called = _called(fn)
        assert "_genuine_clobber_guard_enabled" in called
        assert "_select_price_row" in called

    def test_the_flag_is_never_read_at_module_import(self, ps_tree, pds_tree, scs_tree):
        """The env string may appear ONLY inside price_service's per-call helper."""
        for tree, label in ((pds_tree, "product_data_service"), (scs_tree, "scs")):
            hits = [n for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and n.value == FLAG]
            assert not hits, f"{label} parses the env var itself instead of delegating"

        holder = [n for n in ast.walk(ps_tree)
                  if isinstance(n, ast.Constant) and n.value == FLAG]
        assert holder, f"{FLAG} not referenced at all"
        fn = _func(ps_tree, "genuine_clobber_guard_enabled")
        inside = {id(n) for n in ast.walk(fn) if isinstance(n, ast.Constant)}
        assert all(id(n) in inside for n in holder), (
            f"{FLAG} is referenced outside its per-call helper"
        )

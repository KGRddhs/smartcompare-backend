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

    async def run(self, price=None):
        return await self.svc._persist_tier3_estimate(
            "price:bahrain:iphone_15_128gb", "Apple", "iPhone 15", "128GB",
            "bahrain", dict(price if price is not None else ESTIMATE),
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
# 4. The race, end-to-end through _get_price
# ---------------------------------------------------------------------------


@pytest.fixture
def race_harness(monkeypatch):
    """Drive `_get_price` all the way to the Tier-3 terminal with the whole
    cascade stubbed empty, and simulate the RACE: the concurrent request's
    genuine price lands in L1 *while the GPT training-data call is in flight*, so
    the L1 read at the top of `_get_price` has already missed."""
    state = {"landed": False, "sets": [], "db": 0}

    def _get_cached(key: str):
        if state["landed"] and str(key).startswith("price:"):
            return dict(GENUINE)
        return None

    monkeypatch.setattr(scs, "get_cached", _get_cached)
    monkeypatch.setattr(
        scs, "set_cached", lambda k, v, t: state["sets"].append((k, v, t)) or True
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
        # ...but nothing was written over the genuine entry, at either layer.
        assert _estimate_writes(race_harness) == []
        assert race_harness["db"] == 0

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

    def test_the_negative_cache_call_is_untouched(self, scs_tree):
        """Explicitly out of scope for #54 — the sentinel write must still happen
        at the Tier-3 terminal."""
        fn = _func(_class(scs_tree, "StructuredComparisonService"), "_get_price")
        assert "self._record_negative_price_cache" in _called(fn)

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

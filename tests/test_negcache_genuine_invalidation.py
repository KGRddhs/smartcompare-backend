"""Issue #53 — a GENUINE price persist must delete that key's `nogenuine:` sentinel.

The bug: `nogenuine:{price_cache_key}` (30d, `price_service.NEGATIVE_PRICE_CACHE_TTL`)
was written and read but NEVER deleted anywhere in `app/` — `delete_cached` was not
even imported into `structured_comparison_service`. So the day-0 "no genuine BH
source exists" claim outlived its own disproof: an off-clock `nocache=True` writer
(the warmer / `scripts/seed_zyte_luxury.py` / the nightly eval — exactly the mode
that SKIPS the sentinel READ) resolves a genuine price on day 1, banks 7d at L1 and
7d at L2, and leaves the sentinel standing. On day 8 both genuine entries lapse, the
negcache read fires (it sits AFTER L1 and L2 in the read order) and the day-0
estimate is served for another ~23 days.

The fix routes every genuine L1 price write through ONE writer,
`StructuredComparisonService._cache_price_and_clear_sentinel`, which deletes the
sentinel when — and only when — the price is genuine. Behind
`ENABLE_NEGCACHE_GENUINE_INVALIDATION` (default OFF): clearing a sentinel
un-suppresses the expensive Tier-1.5 cascade for that key, i.e. it spends finite
Serper/Firecrawl budget to serve a correct price, so it is a real behavioural fork
and ships dark.

Coverage here, and what each part is worth:
  * `is_genuine_price` — the hoisted predicate, plus a PARITY pin proving
    `price_cache_ttl` still returns the identical TTL for every input after the
    refactor (the refactor is the only way the two rules could have drifted).
  * `_cache_price_and_clear_sentinel` — both flag directions x genuine /
    converted_usd / estimated / unknown-method, and both Redis-failure modes.
  * `_persist_genuine_price` — a REAL round trip: `_record_negative_price_cache`
    writes the sentinel through the production `set_negative_cache`, the persist
    runs, and `get_negative_cache` is re-read. Only `cache_service.redis_client` is
    faked, so every production cache function on the path actually executes.
  * The Zyte bypass site — driven end-to-end through `_get_price(nocache=True)`.
  * The other four bypass sites — an AST pin (comments are not in an AST, so prose
    cannot satisfy it) that each of the five routes through the shared writer and
    that the ONLY remaining raw genuine-TTL write in `_get_price` is the deliberately
    out-of-scope L2->L1 promotion.

All free-tier: no network, no credentials, no live Redis.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from app.services import cache_service
from app.services import price_service as ps
from app.services import structured_comparison_service as scs

SCS_PATH = (
    Path(__file__).resolve().parent.parent
    / "app" / "services" / "structured_comparison_service.py"
)

FLAG = "ENABLE_NEGCACHE_GENUINE_INVALIDATION"

GENUINE = {"amount": 77.0, "currency": "BHD", "source_method": "zyte_render_bhd"}
CONVERTED = {"amount": 77.0, "currency": "BHD", "source_method": "converted_usd"}
ESTIMATED = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}


class _FakeRedis:
    """Dict-backed stand-in for the blocking Upstash client. Only the four commands
    cache_service actually issues on this path (get / set / setex / delete)."""

    def __init__(self):
        self.store: dict = {}
        self.deleted: list = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value
        return True

    def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    def delete(self, key):
        self.deleted.append(key)
        self.store.pop(key, None)
        return 1


@pytest.fixture
def fake_redis(monkeypatch):
    """Swap ONLY the redis client — get_cached / set_cached / delete_cached /
    get_negative_cache / set_negative_cache all stay the real production functions,
    so this is a genuine round trip, not a mock of the thing under test."""
    fr = _FakeRedis()
    monkeypatch.setattr(cache_service, "redis_client", fr)
    return fr


def _svc():
    return scs.StructuredComparisonService()


# ---------------------------------------------------------------------------
# 1. The predicate, and the refactor's TTL parity
# ---------------------------------------------------------------------------


class TestIsGenuinePrice:
    @pytest.mark.parametrize("method", sorted(ps._GENUINE_BH_SOURCE_METHODS))
    def test_every_genuine_method_is_genuine(self, method):
        assert ps.is_genuine_price({"amount": 1.0, "source_method": method}) is True

    @pytest.mark.parametrize(
        "method",
        ["converted_usd", "converted_fallback", "estimated", "gpt_organic_extract",
         "validation_rejected", "sitemap_no_match", "some_future_method"],
    )
    def test_non_genuine_methods_are_not_genuine(self, method):
        assert ps.is_genuine_price({"amount": 1.0, "source_method": method}) is False

    def test_missing_blank_and_non_dict_are_not_genuine(self):
        assert ps.is_genuine_price(None) is False
        assert ps.is_genuine_price("page_scrape") is False
        assert ps.is_genuine_price({"amount": 1.0}) is False
        assert ps.is_genuine_price({"amount": 1.0, "source_method": ""}) is False
        assert ps.is_genuine_price({"amount": 1.0, "source_method": "   "}) is False
        assert ps.is_genuine_price({"amount": 1.0, "source_method": None}) is False

    def test_genuine_apex_carrying_a_converted_or_estimate_token_is_not_genuine(self):
        # Defensive guard inherited verbatim from price_cache_ttl.
        assert ps.is_genuine_price(
            {"source_method": "page_scrape_jsonld_converted"}
        ) is False
        assert ps.is_genuine_price({"source_method": "local_bhd_estimate"}) is False

    def test_case_insensitive(self):
        assert ps.is_genuine_price({"source_method": "LOCAL_BHD"}) is True


class TestPriceCacheTtlParityAfterRefactor:
    """`price_cache_ttl` now delegates to `is_genuine_price`. Pin that the TTL it
    returns is unchanged for every input class — this is the ONE place the hoist
    could have altered behaviour."""

    @pytest.mark.parametrize("method", sorted(ps._GENUINE_BH_SOURCE_METHODS))
    def test_genuine_methods_still_get_the_7d_ttl(self, method):
        assert ps.price_cache_ttl(
            {"source_method": method}
        ) == ps.GENUINE_PRICE_CACHE_TTL

    @pytest.mark.parametrize(
        "price",
        [
            None,
            "not-a-dict",
            {},
            {"source_method": ""},
            {"source_method": "   "},
            {"source_method": None},
            {"source_method": "converted_usd"},
            {"source_method": "estimated"},
            {"source_method": "converted_fallback"},
            {"source_method": "page_scrape_jsonld_converted"},
            {"source_method": "local_bhd_estimate"},
            {"source_method": "some_future_method"},
        ],
    )
    def test_everything_else_still_gets_the_24h_ttl(self, price):
        assert ps.price_cache_ttl(price) == ps.PRICE_CACHE_TTL

    def test_the_two_ttls_are_actually_distinct(self):
        # Guards the parity assertions above from being vacuous.
        assert ps.GENUINE_PRICE_CACHE_TTL != ps.PRICE_CACHE_TTL


# ---------------------------------------------------------------------------
# 2. The flag itself
# ---------------------------------------------------------------------------


class TestFlagContract:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv(FLAG, raising=False)
        assert scs._negcache_genuine_invalidation_enabled() is False

    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on", " on "])
    def test_truthy_values_enable(self, monkeypatch, value):
        monkeypatch.setenv(FLAG, value)
        assert scs._negcache_genuine_invalidation_enabled() is True

    @pytest.mark.parametrize("value", ["", "false", "0", "no", "off", "maybe"])
    def test_falsy_values_disable(self, monkeypatch, value):
        monkeypatch.setenv(FLAG, value)
        assert scs._negcache_genuine_invalidation_enabled() is False

    def test_read_per_call_not_cached_at_import(self, monkeypatch):
        # The module was imported at the top of this file with the flag unset; a
        # value set NOW must still be observed (the exact_gate_enabled idiom).
        monkeypatch.delenv(FLAG, raising=False)
        assert scs._negcache_genuine_invalidation_enabled() is False
        monkeypatch.setenv(FLAG, "true")
        assert scs._negcache_genuine_invalidation_enabled() is True
        monkeypatch.setenv(FLAG, "false")
        assert scs._negcache_genuine_invalidation_enabled() is False


# ---------------------------------------------------------------------------
# 3. The shared writer
# ---------------------------------------------------------------------------


class TestCachePriceAndClearSentinel:
    @pytest.mark.asyncio
    async def test_genuine_write_deletes_the_sentinel_flag_on(
        self, monkeypatch, fake_redis
    ):
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        cache_service.set_negative_cache(
            ps.negative_cache_key(key), ESTIMATED, ps.NEGATIVE_PRICE_CACHE_TTL
        )
        assert cache_service.get_negative_cache(ps.negative_cache_key(key)) is not None

        await _svc()._cache_price_and_clear_sentinel(key, GENUINE)

        assert cache_service.get_negative_cache(ps.negative_cache_key(key)) is None
        # ...and the price itself was still cached, at the genuine TTL.
        assert cache_service.get_cached(key) == GENUINE

    @pytest.mark.asyncio
    async def test_genuine_write_leaves_the_sentinel_flag_off(
        self, monkeypatch, fake_redis
    ):
        # Flag-OFF byte-identity: the write happens, nothing is deleted.
        monkeypatch.delenv(FLAG, raising=False)
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        cache_service.set_negative_cache(
            ps.negative_cache_key(key), ESTIMATED, ps.NEGATIVE_PRICE_CACHE_TTL
        )

        await _svc()._cache_price_and_clear_sentinel(key, GENUINE)

        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED
        assert fake_redis.deleted == []
        assert cache_service.get_cached(key) == GENUINE

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "price", [CONVERTED, ESTIMATED, {"amount": 1.0, "source_method": "whatever"}],
        ids=["converted_usd", "estimated", "unknown_method"],
    )
    async def test_non_genuine_write_leaves_the_sentinel_even_flag_on(
        self, monkeypatch, fake_redis, price
    ):
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        cache_service.set_negative_cache(
            ps.negative_cache_key(key), ESTIMATED, ps.NEGATIVE_PRICE_CACHE_TTL
        )

        await _svc()._cache_price_and_clear_sentinel(key, price)

        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED
        assert fake_redis.deleted == []

    @pytest.mark.asyncio
    async def test_deletes_the_namespaced_key_not_the_price_key(
        self, monkeypatch, fake_redis
    ):
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        await _svc()._cache_price_and_clear_sentinel(key, GENUINE)
        assert fake_redis.deleted == [f"nogenuine:{key}"]
        # The price key itself must survive its own write.
        assert cache_service.get_cached(key) == GENUINE

    @pytest.mark.asyncio
    async def test_redis_down_delete_returns_false_does_not_break_the_price(
        self, monkeypatch, fake_redis
    ):
        # delete_cached's own no-client branch: returns False, never raises.
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setattr(cache_service, "redis_client", None)
        writes: list = []
        monkeypatch.setattr(
            scs, "set_cached", lambda k, v, t: writes.append((k, v, t)) or True
        )
        await _svc()._cache_price_and_clear_sentinel("price:bahrain:x", GENUINE)
        assert writes == [
            ("price:bahrain:x", GENUINE, ps.GENUINE_PRICE_CACHE_TTL)
        ]

    @pytest.mark.asyncio
    async def test_raising_delete_is_swallowed_and_the_price_is_still_cached(
        self, monkeypatch, fake_redis
    ):
        monkeypatch.setenv(FLAG, "true")

        def _boom(key):
            raise RuntimeError("upstash down")

        monkeypatch.setattr(scs, "delete_cached", _boom)
        await _svc()._cache_price_and_clear_sentinel("price:bahrain:x", GENUINE)
        assert cache_service.get_cached("price:bahrain:x") == GENUINE

    @pytest.mark.asyncio
    async def test_delete_runs_after_the_write_never_before(
        self, monkeypatch, fake_redis
    ):
        # Ordering matters: a raising set_cached must not have already cleared the
        # sentinel (we would have dropped the dead-end record AND stored nothing).
        monkeypatch.setenv(FLAG, "true")
        order: list = []

        def _set(key, value, ttl):
            order.append(("set", key))
            raise RuntimeError("write failed")

        monkeypatch.setattr(scs, "set_cached", _set)
        monkeypatch.setattr(
            scs, "delete_cached", lambda k: order.append(("delete", k)) or True
        )
        with pytest.raises(RuntimeError):
            await _svc()._cache_price_and_clear_sentinel("price:bahrain:x", GENUINE)
        assert order == [("set", "price:bahrain:x")]

    @pytest.mark.asyncio
    async def test_delete_dispatch_honours_the_redis_offload_flag(
        self, monkeypatch, fake_redis
    ):
        import threading

        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
        seen: dict = {}
        monkeypatch.setattr(
            scs, "delete_cached",
            lambda k: seen.setdefault("thread", threading.current_thread()) or True,
        )
        await _svc()._cache_price_and_clear_sentinel("price:bahrain:x", GENUINE)
        assert seen["thread"] is not threading.current_thread()


# ---------------------------------------------------------------------------
# 4. _persist_genuine_price — the acceptance criteria, as a real round trip
# ---------------------------------------------------------------------------


async def _persist(svc, key, price, *, cacheable=True, monkeypatch=None):
    monkeypatch.setattr(scs, "should_cache_price", lambda *a, **k: cacheable)
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None)
    await svc._persist_genuine_price(
        key, price, "Tom Ford", "Oud Wood", "50ml", "bahrain",
        "Tom Ford Oud Wood 50ml", "fragrances",
    )


class TestPersistGenuinePrice:
    @pytest.mark.asyncio
    async def test_genuine_persist_clears_the_sentinel(self, monkeypatch, fake_redis):
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        svc = _svc()
        svc._record_negative_price_cache(key, ESTIMATED)
        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED

        await _persist(svc, key, GENUINE, monkeypatch=monkeypatch)

        assert cache_service.get_negative_cache(ps.negative_cache_key(key)) is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "price", [CONVERTED, ESTIMATED], ids=["converted_usd", "estimated"]
    )
    async def test_non_genuine_persist_leaves_the_sentinel_intact(
        self, monkeypatch, fake_redis, price
    ):
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        svc = _svc()
        svc._record_negative_price_cache(key, ESTIMATED)

        await _persist(svc, key, price, monkeypatch=monkeypatch)

        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED

    @pytest.mark.asyncio
    async def test_identity_rejection_neither_caches_nor_clears(
        self, monkeypatch, fake_redis
    ):
        # should_cache_price is the safety gate and stays OUTSIDE the writer: a
        # rejected price must keep today's early return and must NOT clear.
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        svc = _svc()
        svc._record_negative_price_cache(key, ESTIMATED)

        await _persist(svc, key, GENUINE, cacheable=False, monkeypatch=monkeypatch)

        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED
        assert cache_service.get_cached(key) is None
        assert fake_redis.deleted == []

    @pytest.mark.asyncio
    async def test_flag_off_persist_leaves_the_sentinel(self, monkeypatch, fake_redis):
        monkeypatch.delenv(FLAG, raising=False)
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        svc = _svc()
        svc._record_negative_price_cache(key, ESTIMATED)

        await _persist(svc, key, GENUINE, monkeypatch=monkeypatch)

        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED
        assert cache_service.get_cached(key) == GENUINE


# ---------------------------------------------------------------------------
# 5. Bypass site 1 of 5 driven end-to-end through _get_price
# ---------------------------------------------------------------------------


class TestZyteBypassSiteEndToEnd:
    """The Zyte render-tier write is the one bypass site reachable without the
    whole Tier-1.5 cascade, so it is driven for real: `_get_price(nocache=True)`
    (the off-clock writers' mode — the mode that SKIPS the sentinel read and is
    therefore exactly how the sentinel used to survive its own disproof)."""

    @staticmethod
    def _wire(monkeypatch, price):
        from app.services import zyte_service

        monkeypatch.setenv("ENABLE_ZYTE_RENDER", "true")
        monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
        monkeypatch.setattr(scs, "should_cache_price", lambda *a, **k: True)
        monkeypatch.setattr(
            zyte_service, "ZYTE_STORES", {"sephora.me": {"path": "/"}}
        )

        async def _fake_zyte(domain, full_name, currency, category, brand=None):
            return dict(price)

        monkeypatch.setattr(zyte_service, "fetch_zyte_price", _fake_zyte)

    @staticmethod
    def _key():
        return ps.build_size_aware_price_cache_key(
            "Tom Ford", "Oud Wood", "50ml", "bahrain",
            "Tom Ford Oud Wood 50ml", category="fragrances",
        )

    async def _run(self, svc):
        return await svc._get_price(
            "Tom Ford", "Oud Wood", "50ml", "bahrain",
            "Tom Ford Oud Wood 50ml", nocache=True, category="fragrances",
        )

    @pytest.mark.asyncio
    async def test_genuine_zyte_hit_clears_the_sentinel(self, monkeypatch, fake_redis):
        monkeypatch.setenv(FLAG, "true")
        self._wire(monkeypatch, GENUINE)
        key = self._key()
        svc = _svc()
        monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None)
        svc._record_negative_price_cache(key, ESTIMATED)
        assert cache_service.get_negative_cache(ps.negative_cache_key(key)) is not None

        out = await self._run(svc)

        assert out["source_method"] == "zyte_render_bhd"
        assert cache_service.get_negative_cache(ps.negative_cache_key(key)) is None

    @pytest.mark.asyncio
    async def test_genuine_zyte_hit_flag_off_leaves_the_sentinel(
        self, monkeypatch, fake_redis
    ):
        monkeypatch.delenv(FLAG, raising=False)
        self._wire(monkeypatch, GENUINE)
        key = self._key()
        svc = _svc()
        monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None)
        svc._record_negative_price_cache(key, ESTIMATED)

        out = await self._run(svc)

        assert out["source_method"] == "zyte_render_bhd"
        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED


# ---------------------------------------------------------------------------
# 6. All six write sites route through the shared writer (AST — comment-immune)
# ---------------------------------------------------------------------------


def _scs_class(tree):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StructuredComparisonService":
            return node
    raise AssertionError("StructuredComparisonService class not found")


def _method(cls, name):
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} not found on StructuredComparisonService")


def _call_name(call):
    """Dotted name of a call target, e.g. 'self._cache_price_and_clear_sentinel'."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else "?"
        return f"{base}.{f.attr}"
    return "?"


def _arg_label(node):
    if isinstance(node, ast.Name):
        return node.id
    return ast.dump(node)


def _price_ttl_locals(fn):
    """Locals in `fn` assigned (directly or by later re-assignment) from a
    `price_cache_ttl(...)` call.

    Issue #57 hoisted the L2->L1 promotion's TTL out of the call into a local
    (`_ttl = price_cache_ttl(db_price)`, then reduced by the row's age) so it can
    be clamped before the write. Without this resolution step the detector below
    would stop seeing that site as a genuine-TTL write and silently go blind —
    the pin has to follow the value, not the spelling."""
    names = set()
    changed = True
    while changed:  # resolve chains (`_t = price_cache_ttl(p)` -> `_u = _t`)
        changed = False
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            from_ttl = (
                (isinstance(value, ast.Call) and _call_name(value) == "price_cache_ttl")
                or (isinstance(value, ast.Name) and value.id in names)
            )
            if not from_ttl:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id not in names:
                    names.add(target.id)
                    changed = True
    return names


def _collect(fn):
    """(sites routed through the shared writer, raw genuine-TTL _cache_set_async
    sites), each labelled by the price variable being written."""
    routed, raw = [], []
    ttl_locals = _price_ttl_locals(fn)
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "self._cache_price_and_clear_sentinel" and len(node.args) == 2:
            routed.append(_arg_label(node.args[1]))
        elif name == "_cache_set_async" and len(node.args) == 3:
            ttl = node.args[2]
            inlined = isinstance(ttl, ast.Call) and _call_name(ttl) == "price_cache_ttl"
            hoisted = isinstance(ttl, ast.Name) and ttl.id in ttl_locals
            if inlined or hoisted:
                raw.append(_arg_label(node.args[1]))
    return routed, raw


@pytest.fixture(scope="module")
def scs_tree():
    return ast.parse(SCS_PATH.read_text(encoding="utf-8"))


class TestEveryGenuineWriteSiteRoutesThroughTheWriter:
    """An AST pin, not a grep: comments and docstrings cannot satisfy it, and it
    fails the moment any of the five bypass sites reverts to a raw
    `_cache_set_async(cache_key, X, price_cache_ttl(X))`."""

    def test_the_five_bypass_sites_in_get_price(self, scs_tree):
        fn = _method(_scs_class(scs_tree), "_get_price")
        routed, raw = _collect(fn)
        assert sorted(routed) == sorted([
            "_zp",             # Zyte render-tier
            "best",            # BH adapter direct hit
            "iherb_price",     # iHerb direct
            "pharmacy_price",  # BH pharmacy JSON-LD
            "page_price",      # supplement page-scrape
        ])
        # The ONLY genuine-TTL write left raw is the L2->L1 promotion, which is
        # out of the issue's scope (it re-caches a row already served, it does not
        # resolve a price). Any NEW name appearing here is an unrouted genuine write.
        assert raw == ["db_price"]

    def test_persist_genuine_price_routes_through_the_writer(self, scs_tree):
        fn = _method(_scs_class(scs_tree), "_persist_genuine_price")
        routed, raw = _collect(fn)
        assert routed == ["price_obj"]
        assert raw == []

    def test_the_writer_gates_on_the_flag_and_on_genuineness(self, scs_tree):
        fn = _method(_scs_class(scs_tree), "_cache_price_and_clear_sentinel")
        called = {_call_name(n) for n in ast.walk(fn) if isinstance(n, ast.Call)}
        assert "_negcache_genuine_invalidation_enabled" in called
        assert "is_genuine_price" in called
        assert "negative_cache_key" in called
        assert "_cache_delete_async" in called
        # The identity gate must NOT have migrated inside the writer.
        assert "should_cache_price" not in called

    def test_the_flag_is_not_read_at_module_import(self, scs_tree):
        """The env read must live inside the helper function, never at module scope."""
        holder = []
        for node in ast.walk(scs_tree):
            if isinstance(node, ast.Constant) and node.value == FLAG:
                holder.append(node)
        assert holder, f"{FLAG} not referenced at all"
        fn = None
        for node in scs_tree.body:
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "_negcache_genuine_invalidation_enabled"):
                fn = node
        assert fn is not None, "flag helper is not a module-level function"
        inside = {id(n) for n in ast.walk(fn) if isinstance(n, ast.Constant)}
        assert all(id(n) in inside for n in holder), (
            f"{FLAG} is referenced outside its per-call helper"
        )


# ---------------------------------------------------------------------------
# 7. The end-to-end regression the issue describes, at the read side
# ---------------------------------------------------------------------------


class TestDayEightRegression:
    """The concrete failure: sentinel written day 0, genuine resolved day 1 via a
    nocache writer, L1+L2 lapse on day 8 -> the negcache read serves the day-0
    estimate. After a genuine persist the sentinel read must find nothing, so the
    cascade re-runs instead."""

    @pytest.mark.asyncio
    async def test_negcache_read_no_longer_finds_a_disproven_sentinel(
        self, monkeypatch, fake_redis
    ):
        monkeypatch.setenv(FLAG, "true")
        key = "price:bahrain:tom_ford_oud_wood_50ml"
        svc = _svc()

        # Day 0 — full cascade found nothing genuine.
        svc._record_negative_price_cache(key, ESTIMATED)
        assert cache_service.get_negative_cache(
            ps.negative_cache_key(key)
        ) == ESTIMATED

        # Day 1 — an off-clock nocache writer resolves a genuine BH price.
        await _persist(svc, key, GENUINE, monkeypatch=monkeypatch)

        # Day 8 — L1 and L2 have lapsed; simulate by dropping just the price key.
        fake_redis.store.pop(key, None)

        # The negcache read (scs:_get_price) would fire here. It must miss.
        assert cache_service.get_negative_cache(ps.negative_cache_key(key)) is None


def test_module_imports_delete_cached():
    """`delete_cached` was not imported into the module at all before this fix —
    the mechanical reason no sentinel was ever deleted."""
    assert scs.delete_cached is cache_service.delete_cached
    assert asyncio.iscoroutinefunction(scs._cache_delete_async)

"""S77 REDIS-OFFLOOP: price-path Upstash calls off the event loop (RED tests).

Spec: .qa-s77/OFFLOOP_UNIT_SPEC.md (base main 7b224c5a) as amended by the BINDING
orchestrator rulings .qa-s77/RULINGS_S77_OFFLOOP.md (RO2 log lines, RO6 test list,
RO15 right-reason RED).

Flag ``ENABLE_PRICE_PATH_REDIS_OFFLOOP`` (default OFF, read PER CALL); knob
``REDIS_OFFLOOP_MAX_WORKERS`` (default 16, clamped 1..32, read ONCE when the pool is
built). The new leaf module ``app/utils/redis_offloop.py`` exposes
``redis_offloop_enabled``, ``redis_offloop_max_workers``, ``run_redis_offloop``,
``redis_offloop_pool_stats`` and the lazily built ``_REDIS_OFFLOOP_POOL``
(a ``ThreadPoolExecutor`` named ``redis-offloop``).

Sites (spec section 1): S1 price_service._fetch_shopify_catalog (catalog GET, neg SET,
catalog SET); S2 fetch_bolo_price / fetch_boutiqaat_price (resolve_pdp_via_sitemap);
S3 algolia_service._harvest_config (config GET / SETs); S4a scs._get_price negcache
read (+ sitemap_domains_now_built); S4b scs._get_price negcache writes (the two
_record_negative_price_cache terminals, arguments inside a lambda); S6
review_service.get_reviews L1 read + L2-promotion write.

RO15 contract: the helper module is imported INSIDE each test that needs it
(``_ro()``), so at base a missing module fails each test individually; the site tests
drive the real app functions and fail on the thread a recorded fake ran in. Every
flag-OFF pin and every AST "OFF path unchanged" pin passes at base.

Assertion style (tests/test_m18_offload_sweep_residual.py): every fake records
``(name, args, kwargs, threading.current_thread())``; ON means the fake ran in a
thread whose name starts with ``redis-offloop``; OFF means it ran on the event-loop
thread of the test (the main thread under pytest-asyncio).

Free tier: no network (the conftest netguard is active; curl_cffi.requests.get is
replaced wherever a site would fetch), no credentials, never LIVE=1.
"""
from __future__ import annotations

import ast
import asyncio
import concurrent.futures
import contextvars
import copy
import gc
import importlib
import logging
import re
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import algolia_service as als
from app.services import cache_service as cs
from app.services import price_service as ps
from app.services import review_service as rs
from app.services import sitemap_discovery_service as sds
from app.services import structured_comparison_service as scs

FLAG = "ENABLE_PRICE_PATH_REDIS_OFFLOOP"
KNOB = "REDIS_OFFLOOP_MAX_WORKERS"
ASYNC_FLAG = "ENABLE_ASYNC_REDIS_OFFLOAD"
PREFIX = "redis-offloop"
HELPER_MOD = "app.utils.redis_offloop"

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "app"

# S1 constants (price_service.py:15137 / :15140-15143 at 7b224c5a)
DOMAIN = "store.example"
SHOP_KEY = "shopify_catalog:store.example"
SHOP_NEG = {"_shopify_neg": True}
SHOP_NEG_TTL = 1800
SHOP_CATALOG_TTL = 21600
CATALOG = {"products": [{"title": "Thing One", "variants": []}], "_store_currency": "BHD"}
FRESH_PRODUCTS = {"products": [{"title": "Thing One", "variants": []}]}

# S2 constants
SM_NAME = "Lattafa Khamrah Qahwa"
SM_SLUG = "lattafa khamrah qahwa"
SM_URL = "https://bolo.bh/p/lattafa-khamrah-qahwa"

# S3 constants (algolia_service.py:138)
ALG_DOMAIN = "goldenscent.com"
ALG_KEY = "algolia_config:goldenscent.com"
ALG_TTL = 86400
ALG_CFG = {"app_id": "app", "api_key": "x", "index": "idx"}

# S4 constants (the sibling harness tests/test_negcache_outage_and_converted_fallback.py)
P_BRAND, P_NAME, P_VARIANT = "Tom Ford", "Oud Wood", "100ml"
P_QUERY = "Tom Ford Oud Wood 100ml"
P_CAT = "fragrances"

# S6 constants
R_BRAND, R_NAME, R_VARIANT = "Acme", "Widget Pro", None
R_QUERY = "Acme Widget Pro"

_SCS_LOGGER = scs.logger.name
_DROP = "[ADAPTER DROP]"
_NUM = r"\d+(?:\.\d+)?"

_ADAPTER_SELECTORS = (
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
    "get_noon_sources_for_category",
    "get_gcc_shopify_pagescrape_sources_for_category",
)

# A test-only ContextVar for the copied-context pin (test 10).
_S77_CV: contextvars.ContextVar = contextvars.ContextVar("s77_redis_offloop_cv", default="unset")


# ---------------------------------------------------------------------------
# Fixtures: environment, pool reset
# ---------------------------------------------------------------------------


def _drop_offloop_pools():
    """Drop any lazily built redis-offloop pool by TYPE and thread-name prefix
    (the tests/test_retro_w0_4.py _reset_parse_pools idiom). At base the helper
    module does not exist yet; nothing to drop."""
    try:
        mod = importlib.import_module(HELPER_MOD)
    except ImportError:
        return
    for name, value in list(vars(mod).items()):
        if isinstance(value, concurrent.futures.ThreadPoolExecutor) and str(
            getattr(value, "_thread_name_prefix", "")
        ).startswith(PREFIX):
            value.shutdown(wait=False, cancel_futures=True)
            setattr(mod, name, None)


@pytest.fixture(autouse=True)
def _s77_env(monkeypatch):
    for name in (
        FLAG,
        KNOB,
        ASYNC_FLAG,
        "PRICE_CACHE_BUST",
        "ENABLE_SITEMAP_MATCH_V2",
        "ENABLE_NORMALIZE_WORDS_EMPTY_FIX",
        "ENABLE_GENUINE_PRICE_PRIORITY",
        "ENABLE_GENUINE_PRICE_CLOBBER_GUARD",
        "ENABLE_REVIEW_SOURCE_CONSULT",
    ):
        monkeypatch.delenv(name, raising=False)
    _drop_offloop_pools()
    yield
    _drop_offloop_pools()


def _ro():
    """Import the helper module INSIDE the test (RO15): at base this raises
    ModuleNotFoundError in the test body, never a collection error."""
    return importlib.import_module(HELPER_MOD)


def _set_flag(monkeypatch, on: bool) -> None:
    if on:
        monkeypatch.setenv(FLAG, "true")
    else:
        monkeypatch.delenv(FLAG, raising=False)


# ---------------------------------------------------------------------------
# Recording fakes
# ---------------------------------------------------------------------------


class _Rec:
    """Records (name, args, kwargs, thread) for every fake call, thread-safe."""

    def __init__(self):
        self.calls = []
        self._lock = threading.Lock()

    def record(self, name, args, kwargs=None):
        with self._lock:
            self.calls.append(
                (name, copy.deepcopy(tuple(args)), dict(kwargs or {}), threading.current_thread())
            )

    def shapes(self):
        return [(n, a, k) for n, a, k, _t in self.calls]

    def named(self, name):
        return [c for c in self.calls if c[0] == name]

    def threads(self):
        return [t for _n, _a, _k, t in self.calls]


def _fake(rec, name, result=None, sleep=0.0, raises=None):
    """A sync fake recording its call. ``result`` may be a callable(*args)."""

    def fake(*args, **kwargs):
        rec.record(name, args, kwargs)
        if sleep:
            time.sleep(sleep)
        if raises is not None:
            raise raises
        value = result(*args) if callable(result) else result
        return copy.deepcopy(value)

    return fake


def _assert_placement(rec, flag_on, loop_thread, what, names=None):
    calls = [c for c in rec.calls if names is None or c[0] in names]
    assert calls, f"{what}: the recorded fake was never called"
    for name, _a, _k, t in calls:
        if flag_on:
            assert t.name.startswith(PREFIX), (
                f"{what}: {name} ran in thread {t.name!r} with {FLAG} ON; expected a "
                f"'{PREFIX}' pool thread (the site does not dispatch through "
                f"run_redis_offloop)"
            )
        else:
            assert t is loop_thread, (
                f"{what}: {name} left the event-loop thread ({t.name!r}) with the flag OFF"
            )


def _assert_on_threads(rec, what, names=None):
    calls = [c for c in rec.calls if names is None or c[0] in names]
    assert calls, f"{what}: the recorded fake was never called under ON"
    for name, _a, _k, t in calls:
        assert t.name.startswith(PREFIX), (
            f"{what}: {name} ran in thread {t.name!r} under ON; expected '{PREFIX}' "
            f"(site dispatch missing)"
        )


class _Resp:
    def __init__(self, status=200, payload=None, text="", json_raises=False):
        self.status_code = status
        self._payload = payload
        self.text = text
        self._json_raises = json_raises

    def json(self):
        if self._json_raises:
            raise ValueError("not json")
        return copy.deepcopy(self._payload)


def _patch_curl(monkeypatch, fn):
    import curl_cffi.requests as cr

    monkeypatch.setattr(cr, "get", fn)


def _curl_returning(resp, counter=None):
    def _get(*a, **k):
        if counter is not None:
            counter.append(a[:1])
        return resp

    return _get


def _curl_raising(*a, **k):
    raise RuntimeError("s77 curl failure")


# ---------------------------------------------------------------------------
# Loop observation helpers (tests/test_price_parse_offload.py + test_retro_w0_4.py)
# ---------------------------------------------------------------------------


async def _measure_loop_ticks(awaitable, tick=0.02):
    """Run a heartbeat concurrently with ``awaitable``; returns (result, ticks)."""
    ticks = 0
    stop = False

    async def _heartbeat():
        nonlocal ticks
        while not stop:
            await asyncio.sleep(tick)
            ticks += 1

    hb = asyncio.create_task(_heartbeat())
    await asyncio.sleep(0.01)
    before = ticks
    result = await awaitable
    during = ticks - before
    stop = True
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    return result, during


async def _measure_max_loop_gap(awaitable, tick=0.005):
    """Returns (result, max_gap_seconds, elapsed) for the awaited window."""
    stamps = []
    stop = False

    async def _heartbeat():
        while not stop:
            stamps.append(time.perf_counter())
            await asyncio.sleep(tick)

    hb = asyncio.create_task(_heartbeat())
    await asyncio.sleep(0.02)
    started = time.perf_counter()
    result = await awaitable
    ended = time.perf_counter()
    stop = True
    hb.cancel()
    try:
        await hb
    except asyncio.CancelledError:
        pass
    points = sorted([started, ended] + [s for s in stamps if started <= s <= ended])
    gaps = [b - a for a, b in zip(points, points[1:])]
    return result, (max(gaps) if gaps else 0.0), ended - started


async def _drain_pool(seconds=0.1):
    """Give in-flight pool jobs time to finish before the test loop closes."""
    await asyncio.sleep(seconds)


# ---------------------------------------------------------------------------
# _get_price harness (tests/test_negcache_outage_and_converted_fallback.py
# _stub_cascade + tests/test_retro_w1_8.py _price_harness), zero network: every
# selector empty, Tier-1/2 empty, Tier-3 a fixed estimate.
# ---------------------------------------------------------------------------


def _tier3_harness(monkeypatch, *, quiet_negcache=True):
    svc = scs.get_comparison_service()
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: True)
    if quiet_negcache:
        monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None)
        monkeypatch.setattr(scs, "set_negative_cache", lambda *a, **k: True)
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
    for sel in _ADAPTER_SELECTORS:
        monkeypatch.setattr(scs, sel, lambda c: [])
    monkeypatch.setattr(scs, "get_official_domain", lambda *a, **k: None)
    monkeypatch.setattr(scs, "sitemap_discovery_is_cold", lambda c: False)
    monkeypatch.setattr(scs, "sitemap_unbuilt_domains", lambda c: [])
    monkeypatch.setattr(scs, "sitemap_domains_now_built", lambda d: False)
    monkeypatch.setattr(
        scs, "search_product_prices",
        AsyncMock(side_effect=lambda *a, **k: {
            "shopping": [], "organic": [], "shopping_region": "bahrain"}),
    )
    monkeypatch.setattr(
        scs, "search_price_organic",
        AsyncMock(side_effect=lambda *a, **k: {"organic": [], "knowledge_graph": None}),
        raising=False,
    )
    monkeypatch.setattr(scs, "extract_price", AsyncMock(side_effect=lambda *a, **k: (None, {})))
    monkeypatch.setattr(
        scs, "extract_price_from_training_data",
        AsyncMock(side_effect=lambda *a, **k: ({"amount": 70.0, "currency": "BHD"}, {})),
    )
    monkeypatch.setattr(scs, "search_web", AsyncMock(side_effect=lambda *a, **k: {"organic": []}))
    return svc


_P_DEFAULT = (P_BRAND, P_NAME, P_VARIANT, P_QUERY, P_CAT)
# The converted terminal uses the sibling's proven product (the KWD woo hit below).
_P_CONVERTED = ("Dior", "Sauvage", "EDT 100ml", "Dior Sauvage EDT 100ml", "fragrances")


def _price_cache_key(product=_P_DEFAULT):
    brand, name, variant, query, cat = product
    return scs.build_size_aware_price_cache_key(
        brand, name, variant, "bahrain", query, category=cat,
    )


async def _run_get_price(svc, *, nocache, product=_P_DEFAULT, timeout=30.0):
    brand, name, variant, query, cat = product
    return await asyncio.wait_for(
        svc._get_price(
            brand=brand, name=name, variant=variant, region="bahrain",
            search_query=query, nocache=nocache, category=cat,
        ),
        timeout=timeout,
    )


def _converted_hit():
    return {
        "amount": 39.5, "currency": "BHD", "retailer": "perfumeskuwait.com",
        "url": "https://perfumeskuwait.com/product/dior-sauvage-edt-100ml",
        "in_stock": True, "estimated": False, "confidence": 0.85,
        "source_method": "converted_usd", "original_currency": "KWD",
        "title": "Dior Sauvage Eau de Toilette 100ml",
    }


def _install_converted_terminal(monkeypatch):
    """The converted (:8436) terminal: one woo source yields ONLY a converted hit,
    the cascade misses everywhere else (sibling _run_converted_only_scenario).
    should_negative_cache is patched True (RO6) so the terminal writes a sentinel."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setattr(
        scs, "get_woo_sources_for_category",
        lambda c: [SimpleNamespace(domain="perfumeskuwait.com")],
    )

    async def fake_woo(domain, product_name, currency="BHD", resolved_category=None):
        return _converted_hit()

    monkeypatch.setattr(scs, "fetch_woocommerce_store_api_price", fake_woo)
    monkeypatch.setattr(scs, "should_negative_cache", lambda p: True)


def _install_s4b_fakes(monkeypatch, rec, *, is_cold=False, unbuilt=(), raise_on_set=False):
    def fake_is_cold(category):
        rec.record("sitemap_discovery_is_cold", (category,))
        return is_cold

    def fake_unbuilt(category):
        rec.record("sitemap_unbuilt_domains", (category,))
        return list(unbuilt)

    def fake_set(key, value, ttl):
        rec.record("set_negative_cache", (key, value, ttl))
        if raise_on_set:
            raise RuntimeError("s77 negcache write failure")
        return True

    monkeypatch.setattr(scs, "sitemap_discovery_is_cold", fake_is_cold)
    monkeypatch.setattr(scs, "sitemap_unbuilt_domains", fake_unbuilt)
    monkeypatch.setattr(scs, "set_negative_cache", fake_set)


def _sentinel(cold_domains=None):
    value = {"amount": 61.0, "currency": "BHD", "estimated": True, "source_method": "estimated"}
    if cold_domains is not None:
        value["_sitemap_cold_domains"] = list(cold_domains)
    return value


def _install_s4a_fakes(monkeypatch, rec, *, sentinel=None, now_built=False):
    monkeypatch.setattr(scs, "get_negative_cache", _fake(rec, "get_negative_cache", result=sentinel))
    monkeypatch.setattr(
        scs, "sitemap_domains_now_built", _fake(rec, "sitemap_domains_now_built", result=now_built),
    )


# ---------------------------------------------------------------------------
# S6 harness
# ---------------------------------------------------------------------------


def _install_review_extraction_stubs(monkeypatch):
    monkeypatch.setattr(
        rs, "extract_reviews",
        AsyncMock(side_effect=lambda *a, **k: ({"pros": ["solid"], "cons": []}, {})),
    )
    monkeypatch.setattr(rs, "search_web", AsyncMock(side_effect=lambda *a, **k: {"organic": []}))
    monkeypatch.setattr(rs, "fire_and_forget", MagicMock(return_value=None))
    monkeypatch.setattr(
        "app.services.product_data_service.save_reviews",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(rs, "consult_review_sources", AsyncMock(return_value=[]))
    monkeypatch.setattr(rs, "consult_youtube_source", AsyncMock(return_value=None))


def _reviews_key():
    return rs.get_reviews_cache_key(R_BRAND, R_NAME, R_VARIANT)


async def _get_reviews(nocache=False):
    return await rs.get_reviews(
        R_BRAND, R_NAME, R_VARIANT, R_QUERY, nocache=nocache, category="other",
        search_results={"organic": [{"title": "t", "snippet": "s", "link": "https://x.example/r"}]},
    )


# ===========================================================================
# A. Flag reader and knob (pure)
# ===========================================================================


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True), ("TRUE", True), (" True ", True), ("1", True), ("yes", True),
        ("on", True), ("ON", True),
        (None, False), ("", False), ("  ", False), ("false", False), ("0", False),
        ("no", False), ("off", False), ("garbage", False), ("enabled", False),
    ],
)
def test_flag_reader_rows(monkeypatch, raw, expected):
    ro = _ro()
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    assert ro.redis_offloop_enabled() is expected


@pytest.mark.asyncio
async def test_flag_read_per_call(monkeypatch):
    ro = _ro()
    loop_thread = threading.current_thread()
    rec = _Rec()
    fake = _fake(rec, "fake", result=1)
    _set_flag(monkeypatch, False)
    await ro.run_redis_offloop(fake)
    _set_flag(monkeypatch, True)
    await ro.run_redis_offloop(fake)
    _set_flag(monkeypatch, False)
    await ro.run_redis_offloop(fake)
    threads = rec.threads()
    assert len(threads) == 3
    assert threads[0] is loop_thread
    assert threads[1].name.startswith(PREFIX), threads[1].name
    assert threads[2] is loop_thread


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, 16), ("8", 8), (" 8 ", 8), ("0", 1), ("-3", 1), ("999", 32),
        ("abc", 16), ("8.5", 16), ("inf", 16), ("nan", 16),
    ],
)
def test_max_workers_rows(monkeypatch, raw, expected):
    ro = _ro()
    if raw is None:
        monkeypatch.delenv(KNOB, raising=False)
    else:
        monkeypatch.setenv(KNOB, raw)
    assert ro.redis_offloop_max_workers() == expected


@pytest.mark.asyncio
async def test_pool_never_built_when_off(monkeypatch):
    ro = _ro()
    _set_flag(monkeypatch, False)
    for i in range(5):
        assert await ro.run_redis_offloop(lambda x: x * 2, i) == i * 2
    assert ro._REDIS_OFFLOOP_POOL is None
    assert ro.redis_offloop_pool_stats() is None


@pytest.mark.asyncio
async def test_pool_built_once_named_and_sized(monkeypatch, caplog):
    ro = _ro()
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, logger=HELPER_MOD)
    _set_flag(monkeypatch, True)
    await ro.run_redis_offloop(lambda: 1)
    pool = ro._REDIS_OFFLOOP_POOL
    await ro.run_redis_offloop(lambda: 2)
    assert ro._REDIS_OFFLOOP_POOL is pool, "a second ON call built a second pool"
    assert isinstance(pool, concurrent.futures.ThreadPoolExecutor)
    assert pool._thread_name_prefix == PREFIX
    assert pool._max_workers == 16
    lines = [r.getMessage() for r in caplog.records
             if "[REDIS-OFFLOOP] pool built workers=16" in r.getMessage()]
    assert len(lines) == 1, [r.getMessage() for r in caplog.records]


@pytest.mark.asyncio
async def test_knob_read_once_at_build(monkeypatch):
    """RO6: setting REDIS_OFFLOOP_MAX_WORKERS after the build changes nothing."""
    ro = _ro()
    _set_flag(monkeypatch, True)
    monkeypatch.delenv(KNOB, raising=False)
    await ro.run_redis_offloop(lambda: None)
    pool = ro._REDIS_OFFLOOP_POOL
    assert pool is not None and pool._max_workers == 16
    monkeypatch.setenv(KNOB, "4")
    await ro.run_redis_offloop(lambda: None)
    assert ro._REDIS_OFFLOOP_POOL is pool
    assert pool._max_workers == 16


@pytest.mark.asyncio
async def test_pool_stats_after_build(monkeypatch):
    """RO6: redis_offloop_pool_stats() after the build is a dict with workers==16
    and an int queue depth."""
    ro = _ro()
    _set_flag(monkeypatch, True)
    await ro.run_redis_offloop(lambda: None)
    stats = ro.redis_offloop_pool_stats()
    assert isinstance(stats, dict), stats
    assert stats["workers"] == 16
    assert isinstance(stats["queued"], int)
    assert stats["queued"] >= 0


@pytest.mark.asyncio
async def test_pool_is_not_the_default_executor(monkeypatch):
    """RO6: snapshot and restore app.utils.executor._INSTALLED_POOL and the loop's
    default executor; shut down what the test built."""
    ro = _ro()
    from app.utils import executor as ex

    loop = asyncio.get_running_loop()
    saved_installed = ex._INSTALLED_POOL
    saved_default = getattr(loop, "_default_executor", None)
    built = None
    try:
        built = ex.install_default_executor(loop)
        _set_flag(monkeypatch, True)
        rec = _Rec()
        await ro.run_redis_offloop(_fake(rec, "fake", result=1))
        (thread,) = rec.threads()
        assert thread.name.startswith(PREFIX), thread.name
        assert not thread.name.startswith("qaren-worker"), thread.name
    finally:
        ex._INSTALLED_POOL = saved_installed
        loop._default_executor = saved_default
        if built is not None:
            built.shutdown(wait=False, cancel_futures=True)


# ===========================================================================
# B. Helper semantics
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [False, True], ids=["off", "on"])
async def test_off_inline_no_yield(monkeypatch, flag_on):
    ro = _ro()
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    coro = ro.run_redis_offloop(_fake(rec, "fake", result="value"), 1, 2)
    if not flag_on:
        with pytest.raises(StopIteration) as stop:
            coro.send(None)
        assert stop.value.value == "value"
    else:
        completed = False
        try:
            coro.send(None)
        except StopIteration:
            completed = True
        finally:
            coro.close()
        await _drain_pool()
        assert not completed, "ON: run_redis_offloop completed without a suspension point"


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [False, True], ids=["off", "on"])
async def test_args_positional_no_kwargs(monkeypatch, flag_on):
    ro = _ro()
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    out = await ro.run_redis_offloop(_fake(rec, "fake", result=3), 1, 2)
    assert out == 3
    assert rec.shapes() == [("fake", (1, 2), {})]


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [False, True], ids=["off", "on"])
async def test_exception_identity_both_branches(monkeypatch, flag_on):
    ro = _ro()
    _set_flag(monkeypatch, flag_on)
    created = []

    def boom():
        exc = RuntimeError("boom")
        created.append(exc)
        raise exc

    with pytest.raises(RuntimeError, match="^boom$") as info:
        await ro.run_redis_offloop(boom)
    assert info.value is created[0]


@pytest.mark.asyncio
async def test_contextvars_copied_on(monkeypatch):
    ro = _ro()
    _set_flag(monkeypatch, True)
    token = _S77_CV.set("caller-value")
    seen = []

    def fake():
        seen.append((_S77_CV.get(), threading.current_thread().name))
        _S77_CV.set("worker-value")
        return True

    try:
        await ro.run_redis_offloop(fake)
        assert seen and seen[0][0] == "caller-value", seen
        assert seen[0][1].startswith(PREFIX), seen
        assert _S77_CV.get() == "caller-value", "a .set() in the worker leaked to the caller"
    finally:
        _S77_CV.reset(token)


@pytest.mark.asyncio
async def test_durable_write_lands_after_cancel(monkeypatch, caplog):
    ro = _ro()
    _set_flag(monkeypatch, True)
    done = threading.Event()
    completed = []

    def fake_set():
        time.sleep(0.3)
        completed.append(threading.current_thread().name)
        done.set()
        return True

    task = asyncio.ensure_future(ro.run_redis_offloop(fake_set, durable=True))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    for _ in range(100):
        if done.is_set():
            break
        await asyncio.sleep(0.01)
    assert done.is_set(), "the durable write did not land within 1 s of the cancel"
    assert len(completed) == 1 and completed[0].startswith(PREFIX), completed

    # A raising durable write after the cancel must not log
    # "Future exception was never retrieved".
    caplog.set_level(logging.ERROR, logger="asyncio")
    raised = threading.Event()

    def fake_raise():
        time.sleep(0.2)
        raised.set()
        raise ConnectionError("late write failure")

    task2 = asyncio.ensure_future(ro.run_redis_offloop(fake_raise, durable=True))
    await asyncio.sleep(0.05)
    task2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task2
    for _ in range(100):
        if raised.is_set():
            break
        await asyncio.sleep(0.01)
    assert raised.is_set()
    await asyncio.sleep(0.1)
    del task2
    gc.collect()
    await asyncio.sleep(0)
    gc.collect()
    leaked = [r.getMessage() for r in caplog.records if "never retrieved" in r.getMessage()]
    assert not leaked, leaked


@pytest.mark.asyncio
async def test_queued_read_dropped_on_cancel(monkeypatch):
    ro = _ro()
    _set_flag(monkeypatch, True)
    monkeypatch.setenv(KNOB, "1")
    gate = threading.Event()
    started = threading.Event()
    called2 = []

    def job1():
        started.set()
        gate.wait(5)
        return 1

    def job2():
        called2.append(threading.current_thread().name)
        return 2

    t1 = asyncio.ensure_future(ro.run_redis_offloop(job1))
    try:
        for _ in range(200):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert started.is_set(), "job 1 never started"
        assert ro._REDIS_OFFLOOP_POOL._max_workers == 1
        t2 = asyncio.ensure_future(ro.run_redis_offloop(job2))
        await asyncio.sleep(0.05)
        t2.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t2
    finally:
        gate.set()
    assert await asyncio.wait_for(t1, 5) == 1
    await asyncio.sleep(0.1)
    assert called2 == [], f"the cancelled queued read still ran: {called2}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "new_on,async_on",
    [(False, False), (False, True), (True, False), (True, True)],
    ids=["new_off-async_off", "new_off-async_on", "new_on-async_off", "new_on-async_on"],
)
async def test_composes_with_async_redis_offload(monkeypatch, new_on, async_on):
    _set_flag(monkeypatch, new_on)
    if async_on:
        monkeypatch.setenv(ASYNC_FLAG, "true")
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(ps, "get_cached", _fake(rec, "get_cached", result=CATALOG))
    out = await ps._fetch_shopify_catalog(DOMAIN)
    assert out == CATALOG
    assert len(rec.calls) == 1, rec.shapes()
    (thread,) = rec.threads()
    if new_on:
        assert thread.name.startswith(PREFIX), (
            f"new flag ON (async_on={async_on}): S1a ran in {thread.name!r}; expected a "
            f"'{PREFIX}' thread (site dispatch missing)"
        )
        assert not thread.name.startswith("qaren-worker"), thread.name
    else:
        assert thread is loop_thread, (
            f"new flag OFF (async_on={async_on}): S1a left the loop ({thread.name!r})"
        )


# ===========================================================================
# C. Thread placement per site, ON vs OFF
# ===========================================================================

FLAG_ROWS = pytest.mark.parametrize("flag_on", [False, True], ids=["off", "on"])


@pytest.mark.asyncio
@FLAG_ROWS
async def test_s1a_catalog_get_placement(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(ps, "get_cached", _fake(rec, "get_cached", result=CATALOG))
    monkeypatch.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
    out = await ps._fetch_shopify_catalog(DOMAIN)
    assert out == CATALOG
    assert rec.shapes() == [("get_cached", (SHOP_KEY,), {})]
    _assert_placement(rec, flag_on, loop_thread, "S1a")


_S1_FAILURE_BRANCHES = {
    "exception": _curl_raising,
    "http404": _curl_returning(_Resp(status=404)),
    "not_json": _curl_returning(_Resp(status=200, json_raises=True)),
    "no_products": _curl_returning(_Resp(status=200, payload={"items": []})),
}


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("branch", sorted(_S1_FAILURE_BRANCHES))
async def test_s1b_negcache_set_placement(monkeypatch, flag_on, branch):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(ps, "get_cached", _fake(rec, "get_cached", result=None))
    monkeypatch.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
    _patch_curl(monkeypatch, _S1_FAILURE_BRANCHES[branch])
    out = await ps._fetch_shopify_catalog(DOMAIN)
    assert out is None
    assert rec.shapes() == [
        ("get_cached", (SHOP_KEY,), {}),
        ("set_cached", (SHOP_KEY, SHOP_NEG, SHOP_NEG_TTL), {}),
    ]
    _assert_placement(rec, flag_on, loop_thread, f"S1b[{branch}]")


@pytest.mark.asyncio
@FLAG_ROWS
async def test_s1c_catalog_set_placement(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(ps, "get_cached", _fake(rec, "get_cached", result=None))
    monkeypatch.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
    monkeypatch.setattr(ps, "_fetch_shopify_currency", AsyncMock(return_value="BHD"))
    _patch_curl(monkeypatch, _curl_returning(_Resp(status=200, payload=FRESH_PRODUCTS)))
    out = await ps._fetch_shopify_catalog(DOMAIN)
    expected = dict(copy.deepcopy(FRESH_PRODUCTS), _store_currency="BHD")
    assert out == expected
    assert rec.shapes() == [
        ("get_cached", (SHOP_KEY,), {}),
        ("set_cached", (SHOP_KEY, expected, SHOP_CATALOG_TTL), {}),
    ]
    _assert_placement(rec, flag_on, loop_thread, "S1c")


_S2_SITES = {
    "bolo": ("bolo.bh", "fetch_bolo_price"),
    "boutiqaat": ("boutiqaat.com", "fetch_boutiqaat_price"),
}


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("site", sorted(_S2_SITES))
async def test_s2_sitemap_resolve_placement(monkeypatch, flag_on, site):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    domain, fn_name = _S2_SITES[site]
    rec = _Rec()
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(
        sds, "resolve_pdp_via_sitemap", _fake(rec, "resolve_pdp_via_sitemap", result=None),
    )
    out = await getattr(ps, fn_name)(SM_NAME)
    assert out is None
    assert rec.shapes() == [("resolve_pdp_via_sitemap", (domain, SM_NAME), {})]
    _assert_placement(rec, flag_on, loop_thread, f"S2[{site}]")


def _sds_get_fake(rec, *, meta=True, bucket=None, raises=None):
    """sitemap_discovery_service.get_cached fake: META present, every bucket key
    returns ``bucket``."""

    def result(key):
        if key.endswith(":meta"):
            return {"built": 1} if meta else None
        return bucket

    return _fake(rec, "sds.get_cached", result=result, raises=raises)


@pytest.mark.asyncio
@FLAG_ROWS
async def test_s2_inner_gets_run_in_same_worker(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(sds, "get_cached", _sds_get_fake(rec, bucket=[[SM_SLUG, SM_URL]]))
    fetched = []

    async def fake_same_site(url, expected):
        fetched.append((url, expected))
        return None

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_same_site)
    out = await ps.fetch_bolo_price(SM_NAME)
    assert out is None
    assert fetched == [(SM_URL, "bolo.bh")], fetched
    names = [n for n, _a, _k in rec.shapes()]
    assert names[0] == "sds.get_cached" and len(names) >= 2, rec.shapes()
    threads = rec.threads()
    if flag_on:
        assert threads[0].name.startswith(PREFIX), (
            f"S2 inner GETs ran in {threads[0].name!r} under ON; expected one "
            f"'{PREFIX}' job (site dispatch missing)"
        )
        assert all(t is threads[0] for t in threads), (
            "the meta and bucket GETs must run in ONE redis-offloop job: "
            f"{[t.name for t in threads]}"
        )
    else:
        assert all(t is loop_thread for t in threads), [t.name for t in threads]


@pytest.mark.asyncio
@FLAG_ROWS
async def test_s3_algolia_config_get_placement(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(als, "get_cached", _fake(rec, "get_cached", result=ALG_CFG))
    monkeypatch.setattr(als, "set_cached", _fake(rec, "set_cached", result=True))
    out = await als._harvest_config(ALG_DOMAIN)
    assert out == ALG_CFG
    assert rec.shapes() == [("get_cached", (ALG_KEY,), {})]
    _assert_placement(rec, flag_on, loop_thread, "S3 get")


def _s3_install_miss(monkeypatch, rec, branch):
    monkeypatch.setattr(als, "get_cached", _fake(rec, "get_cached", result=None))
    monkeypatch.setattr(als, "set_cached", _fake(rec, "set_cached", result=True))
    if branch == "neg_landing_404":
        _patch_curl(monkeypatch, _curl_returning(_Resp(status=404)))
    else:
        _patch_curl(monkeypatch, _curl_returning(_Resp(status=200, text="<html></html>")))
        monkeypatch.setattr(als, "extract_algolia_config", lambda *a, **k: dict(ALG_CFG))


_S3_SET_EXPECTED = {
    "neg_landing_404": ({"_algolia_neg": True}, None),
    "cfg_success": (ALG_CFG, ALG_CFG),
}


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("branch", sorted(_S3_SET_EXPECTED))
async def test_s3_algolia_config_sets_placement(monkeypatch, flag_on, branch):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    _s3_install_miss(monkeypatch, rec, branch)
    value, expected_out = _S3_SET_EXPECTED[branch]
    out = await als._harvest_config(ALG_DOMAIN)
    assert out == expected_out
    assert rec.shapes() == [
        ("get_cached", (ALG_KEY,), {}),
        ("set_cached", (ALG_KEY, value, ALG_TTL), {}),
    ]
    _assert_placement(rec, flag_on, loop_thread, f"S3 set[{branch}]")


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("row", ["plain_sentinel", "cold_domains_not_built"])
async def test_s4a_negcache_read_placement(monkeypatch, flag_on, row):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    svc = _tier3_harness(monkeypatch)
    rec = _Rec()
    sentinel = _sentinel(["bolo.bh"] if row == "cold_domains_not_built" else None)
    _install_s4a_fakes(monkeypatch, rec, sentinel=sentinel, now_built=False)
    price = await _run_get_price(svc, nocache=False)
    assert price["_cache_source"] == "negative"
    assert "_sitemap_cold_domains" not in price
    neg_key = ps.negative_cache_key(_price_cache_key())
    expected = [("get_negative_cache", (neg_key,), {})]
    if row == "cold_domains_not_built":
        expected.append(("sitemap_domains_now_built", (["bolo.bh"],), {}))
    assert rec.shapes() == expected
    _assert_placement(rec, flag_on, loop_thread, f"S4a[{row}]")


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("terminal", ["converted_8436", "tier3_8513"])
async def test_s4b_negcache_write_placement(monkeypatch, flag_on, terminal):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    svc = _tier3_harness(monkeypatch)
    rec = _Rec()
    _install_s4b_fakes(monkeypatch, rec, is_cold=False, unbuilt=())
    product = _P_DEFAULT
    if terminal == "converted_8436":
        _install_converted_terminal(monkeypatch)
        product = _P_CONVERTED
    price = await _run_get_price(svc, nocache=True, product=product)
    sets = rec.named("set_negative_cache")
    assert len(sets) == 1, rec.shapes()
    assert sets[0][1][0] == ps.negative_cache_key(_price_cache_key(product))
    if terminal == "converted_8436":
        assert price["source_method"] == "converted_usd", price
        assert rec.named("sitemap_discovery_is_cold") == []
        _assert_placement(rec, flag_on, loop_thread, "S4b[:8436]", names={"set_negative_cache"})
    else:
        assert price.get("estimated") is True, price
        assert [n for n, _a, _k in rec.shapes()] == [
            "sitemap_discovery_is_cold", "sitemap_unbuilt_domains", "set_negative_cache",
        ]
        _assert_placement(rec, flag_on, loop_thread, "S4b[:8513]")
        if flag_on:
            threads = rec.threads()
            assert all(t is threads[0] for t in threads), (
                "S4b[:8513]: sitemap_discovery_is_cold (the argument) must be evaluated "
                "inside the lambda, in the same redis-offloop job as the write: "
                f"{[t.name for t in threads]}"
            )


@pytest.mark.asyncio
@FLAG_ROWS
async def test_s6_reviews_l1_read_placement(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(rs, "get_cached", _fake(rec, "get_cached", result={"summary": "cached"}))
    monkeypatch.setattr(rs, "set_cached", _fake(rec, "set_cached", result=True))
    out = await _get_reviews()
    assert out == {"summary": "cached", "_cached": True}
    assert rec.shapes() == [("get_cached", (_reviews_key(),), {})]
    _assert_placement(rec, flag_on, loop_thread, "S6 read")


@pytest.mark.asyncio
@FLAG_ROWS
async def test_s6_reviews_l2_promotion_set_placement(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(rs, "get_cached", _fake(rec, "get_cached", result=None))
    monkeypatch.setattr(rs, "set_cached", _fake(rec, "set_cached", result=True))
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_reviews",
        AsyncMock(side_effect=lambda *a, **k: {"summary": "db"}),
    )
    out = await _get_reviews()
    assert out == {"summary": "db", "_cached": True, "_cache_source": "db"}
    key = _reviews_key()
    assert rec.shapes() == [
        ("get_cached", (key,), {}),
        ("set_cached", (key, {"summary": "db"}, rs.REVIEWS_CACHE_TTL), {}),
    ]
    _assert_placement(rec, flag_on, loop_thread, "S6 promotion set")


@pytest.mark.asyncio
async def test_s6_post_extraction_write_stays_inline_on(monkeypatch):
    """The F3/G2 exclusion: the post-extraction L1 write (review_service.py:722)
    stays inline on the loop even with the flag ON."""
    _set_flag(monkeypatch, True)
    loop_thread = threading.current_thread()
    rec = _Rec()
    monkeypatch.setattr(rs, "get_cached", _fake(rec, "get_cached", result=None))
    monkeypatch.setattr(rs, "set_cached", _fake(rec, "set_cached", result=True))
    _install_review_extraction_stubs(monkeypatch)
    out = await _get_reviews(nocache=True)
    assert out["_cached"] is False
    sets = rec.named("set_cached")
    assert len(sets) == 1, rec.shapes()
    assert sets[0][1][0] == _reviews_key()
    assert sets[0][1][2] == rs.REVIEWS_CACHE_TTL
    assert sets[0][3] is loop_thread, (
        f"the post-extraction write left the loop ({sets[0][3].name!r}); the F3 "
        "ordering requires it inline"
    )
    assert rec.named("get_cached") == []


# ===========================================================================
# D. Heartbeat (the measured symptom)
# ===========================================================================


@pytest.mark.asyncio
@FLAG_ROWS
async def test_heartbeat_single_slow_catalog_get(monkeypatch, flag_on):
    # Bounds measured on this box (Windows 15.6 ms timer, a 20 ms tick lands at
    # ~31 ms): an off-loop 0.4 s sleep gives 12 ticks, an inline one 0.
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    monkeypatch.setattr(ps, "get_cached", _fake(rec, "get_cached", result=CATALOG, sleep=0.4))
    out, ticks = await _measure_loop_ticks(ps._fetch_shopify_catalog(DOMAIN), tick=0.02)
    assert out == CATALOG
    if flag_on:
        assert ticks >= 8, f"ON: the loop ticked {ticks} times during a 0.4 s catalog GET"
    else:
        assert ticks <= 1, f"OFF: the loop ticked {ticks} times during an inline GET"


@pytest.mark.asyncio
async def test_heartbeat_fanout_18_catalog_gets(monkeypatch):
    """RO6: relative bounds (ON max gap <= OFF max gap / 4, ON wall <= OFF wall / 2)
    with loose absolute bounds."""
    rec = _Rec()
    monkeypatch.setattr(ps, "get_cached", _fake(rec, "get_cached", result=CATALOG, sleep=0.1))

    async def _fanout():
        return await asyncio.gather(
            *(ps._fetch_shopify_catalog(f"shop{i:02d}.example") for i in range(18))
        )

    _set_flag(monkeypatch, False)
    out_off, gap_off, wall_off = await _measure_max_loop_gap(_fanout())
    _set_flag(monkeypatch, True)
    out_on, gap_on, wall_on = await _measure_max_loop_gap(_fanout())
    detail = (f"OFF gap={gap_off:.3f}s wall={wall_off:.3f}s; "
              f"ON gap={gap_on:.3f}s wall={wall_on:.3f}s")
    assert out_off == out_on == [CATALOG] * 18
    assert gap_off >= 0.9, f"sanity: 18 inline 0.1 s GETs should stall the loop; {detail}"
    assert gap_on <= gap_off / 4, detail
    assert gap_on < 0.5, detail
    assert wall_on <= wall_off / 2, detail
    assert wall_on < 1.0, detail


@pytest.mark.asyncio
@FLAG_ROWS
async def test_heartbeat_sitemap_resolve(monkeypatch, flag_on):
    # Measured on this box: an off-loop 0.3 s sleep gives 9 ticks of 20 ms.
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(
        sds, "resolve_pdp_via_sitemap",
        _fake(rec, "resolve_pdp_via_sitemap", result=None, sleep=0.3),
    )
    out, ticks = await _measure_loop_ticks(ps.fetch_bolo_price(SM_NAME), tick=0.02)
    assert out is None
    if flag_on:
        assert ticks >= 6, f"ON: the loop ticked {ticks} times during a 0.3 s resolve"
    else:
        assert ticks <= 1, f"OFF: the loop ticked {ticks} times during an inline resolve"


# ===========================================================================
# E. ON == OFF result parity (each ON row also pins the redis-offloop thread, RO6)
# ===========================================================================


async def _run_both(monkeypatch, scenario):
    out = {}
    for flag_on in (False, True):
        _set_flag(monkeypatch, flag_on)
        rec = _Rec()
        result = await scenario(monkeypatch, rec)
        out[flag_on] = (result, rec)
    _set_flag(monkeypatch, False)
    return out


def _assert_parity(out, what, on_names=None):
    (r_off, rec_off), (r_on, rec_on) = out[False], out[True]
    assert r_off == r_on, f"{what}: ON result {r_on!r} != OFF result {r_off!r}"
    assert rec_on.shapes() == rec_off.shapes(), (
        f"{what}: ON calls {rec_on.shapes()} != OFF calls {rec_off.shapes()}"
    )
    _assert_on_threads(rec_on, what, names=on_names)


@pytest.mark.asyncio
@pytest.mark.parametrize("row", ["hit", "negative", "miss_404", "miss_success"])
async def test_parity_s1(monkeypatch, row):
    async def scenario(mp, rec):
        get_result = {"hit": CATALOG, "negative": SHOP_NEG}.get(row)
        mp.setattr(ps, "get_cached", _fake(rec, "get_cached", result=get_result))
        mp.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
        mp.setattr(ps, "_fetch_shopify_currency", AsyncMock(return_value="BHD"))
        if row == "miss_404":
            _patch_curl(mp, _curl_returning(_Resp(status=404)))
        elif row == "miss_success":
            _patch_curl(mp, _curl_returning(_Resp(status=200, payload=FRESH_PRODUCTS)))
        else:
            _patch_curl(mp, _curl_raising)
        return await ps._fetch_shopify_catalog(DOMAIN)

    out = await _run_both(monkeypatch, scenario)
    result, rec = out[False]
    get_call = ("get_cached", (SHOP_KEY,), {})
    if row == "hit":
        assert result == CATALOG and rec.shapes() == [get_call]
    elif row == "negative":
        assert result is None and rec.shapes() == [get_call]
    elif row == "miss_404":
        assert result is None
        assert rec.shapes() == [get_call, ("set_cached", (SHOP_KEY, SHOP_NEG, SHOP_NEG_TTL), {})]
    else:
        expected = dict(copy.deepcopy(FRESH_PRODUCTS), _store_currency="BHD")
        assert result == expected
        assert rec.shapes() == [get_call, ("set_cached", (SHOP_KEY, expected, SHOP_CATALOG_TTL), {})]
    _assert_parity(out, f"S1[{row}]")


@pytest.mark.asyncio
@pytest.mark.parametrize("row", ["index_cold", "bucket_match", "no_match"])
async def test_parity_s2(monkeypatch, row):
    async def scenario(mp, rec):
        mp.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
        if row == "index_cold":
            fake = _sds_get_fake(rec, meta=False)
        elif row == "bucket_match":
            fake = _sds_get_fake(rec, bucket=[[SM_SLUG, SM_URL]])
        else:
            fake = _sds_get_fake(rec, bucket=[["another product entirely", "https://bolo.bh/p/x"]])
        mp.setattr(sds, "get_cached", fake)
        fetched = []

        async def fake_same_site(url, expected):
            fetched.append(url)
            return None

        mp.setattr(ps, "curl_fetch_html_same_site", fake_same_site)
        result = await ps.fetch_bolo_price(SM_NAME)
        return (result, tuple(fetched))

    out = await _run_both(monkeypatch, scenario)
    (result, fetched), rec = out[False]
    keys = [a[0] for _n, a, _k in rec.shapes()]
    assert result is None
    assert keys[0] == "discovery:sitemap:bolo.bh:meta"
    if row == "index_cold":
        assert keys == ["discovery:sitemap:bolo.bh:meta"] and fetched == ()
    elif row == "bucket_match":
        assert fetched == (SM_URL,)
        assert len(keys) == 2
    else:
        assert fetched == ()
        assert len(keys) == 4, f"expected meta + exactly 3 bucket GETs: {keys}"
    _assert_parity(out, f"S2[{row}]")


@pytest.mark.asyncio
@pytest.mark.parametrize("row", ["config_hit", "neg_sentinel", "miss_neg_set", "miss_cfg_set"])
async def test_parity_s3(monkeypatch, row):
    async def scenario(mp, rec):
        if row in ("config_hit", "neg_sentinel"):
            result = ALG_CFG if row == "config_hit" else {"_algolia_neg": True}
            mp.setattr(als, "get_cached", _fake(rec, "get_cached", result=result))
            mp.setattr(als, "set_cached", _fake(rec, "set_cached", result=True))
            _patch_curl(mp, _curl_raising)
        else:
            _s3_install_miss(
                mp, rec, "neg_landing_404" if row == "miss_neg_set" else "cfg_success",
            )
        return await als._harvest_config(ALG_DOMAIN)

    out = await _run_both(monkeypatch, scenario)
    result, rec = out[False]
    get_call = ("get_cached", (ALG_KEY,), {})
    if row == "config_hit":
        assert result == ALG_CFG and rec.shapes() == [get_call]
    elif row == "neg_sentinel":
        assert result is None and rec.shapes() == [get_call]
    elif row == "miss_neg_set":
        assert result is None
        assert rec.shapes() == [get_call, ("set_cached", (ALG_KEY, {"_algolia_neg": True}, ALG_TTL), {})]
    else:
        assert result == ALG_CFG
        assert rec.shapes() == [get_call, ("set_cached", (ALG_KEY, ALG_CFG, ALG_TTL), {})]
    _assert_parity(out, f"S3[{row}]")


@pytest.mark.asyncio
@pytest.mark.parametrize("row", ["sentinel_absent", "sentinel_served", "cold_now_built"])
async def test_parity_s4a(monkeypatch, row):
    async def scenario(mp, rec):
        svc = _tier3_harness(mp)
        if row == "sentinel_absent":
            _install_s4a_fakes(mp, rec, sentinel=None)
        elif row == "sentinel_served":
            _install_s4a_fakes(mp, rec, sentinel=_sentinel())
        else:
            _install_s4a_fakes(mp, rec, sentinel=_sentinel(["bolo.bh"]), now_built=True)
        price = await _run_get_price(svc, nocache=False)
        return {k: price.get(k) for k in ("amount", "estimated", "source_method", "_cache_source")}

    out = await _run_both(monkeypatch, scenario)
    result, rec = out[False]
    neg_key = ps.negative_cache_key(_price_cache_key())
    if row == "sentinel_served":
        assert result["_cache_source"] == "negative" and result["amount"] == 61.0
        assert rec.shapes() == [("get_negative_cache", (neg_key,), {})]
    else:
        # Cascade continued (absent) or the sentinel was invalidated: Tier-3 estimate.
        assert result["estimated"] is True and result["_cache_source"] is None
        expected = [("get_negative_cache", (neg_key,), {})]
        if row == "cold_now_built":
            expected.append(("sitemap_domains_now_built", (["bolo.bh"],), {}))
        assert rec.shapes() == expected
    _assert_parity(out, f"S4a[{row}]")


@pytest.mark.asyncio
@pytest.mark.parametrize("row", ["default_30d", "transient_24h", "stamped_cold_domains"])
async def test_parity_s4b(monkeypatch, row):
    async def scenario(mp, rec):
        svc = _tier3_harness(mp)
        _install_s4b_fakes(
            mp, rec,
            is_cold=(row == "transient_24h"),
            unbuilt=(["bolo.bh"] if row == "stamped_cold_domains" else ()),
        )
        price = await _run_get_price(svc, nocache=True)
        return {k: price.get(k) for k in ("amount", "estimated", "source_method", "_cached")}

    out = await _run_both(monkeypatch, scenario)
    result, rec = out[False]
    assert result["estimated"] is True and result["_cached"] is False
    (s_name, (key, value, ttl), s_kwargs, _t) = rec.named("set_negative_cache")[0]
    assert key == ps.negative_cache_key(_price_cache_key())
    assert "_cached" not in value, "the stored sentinel must still lack _cached"
    if row == "transient_24h":
        assert ttl == ps.PRICE_CACHE_TTL
    else:
        assert ttl == ps.NEGATIVE_PRICE_CACHE_TTL
    if row == "stamped_cold_domains":
        assert value["_sitemap_cold_domains"] == ["bolo.bh"]
    else:
        assert "_sitemap_cold_domains" not in value
    _assert_parity(out, f"S4b[{row}]")


@pytest.mark.asyncio
@pytest.mark.parametrize("row", ["l1_hit", "l2_promotion", "nocache"])
async def test_parity_s6(monkeypatch, row):
    async def scenario(mp, rec):
        get_result = {"summary": "cached"} if row == "l1_hit" else None
        mp.setattr(rs, "get_cached", _fake(rec, "get_cached", result=get_result))
        mp.setattr(rs, "set_cached", _fake(rec, "set_cached", result=True))
        mp.setattr(
            "app.services.product_data_service.get_cached_reviews",
            AsyncMock(side_effect=lambda *a, **k: {"summary": "db"}),
        )
        _install_review_extraction_stubs(mp)
        return await _get_reviews(nocache=(row == "nocache"))

    out = await _run_both(monkeypatch, scenario)
    result, rec = out[False]
    key = _reviews_key()
    if row == "l1_hit":
        assert result == {"summary": "cached", "_cached": True}
        assert rec.shapes() == [("get_cached", (key,), {})]
        _assert_parity(out, "S6[l1_hit]")
    elif row == "l2_promotion":
        assert result["_cache_source"] == "db"
        assert rec.shapes() == [
            ("get_cached", (key,), {}),
            ("set_cached", (key, {"summary": "db"}, rs.REVIEWS_CACHE_TTL), {}),
        ]
        _assert_parity(out, "S6[l2_promotion]")
    else:
        # nocache: no in-scope call at all in either branch (no GET, no promotion);
        # the only recorded call is the post-extraction :722 write, inline in both.
        r_on, rec_on = out[True]
        assert result == r_on
        for rec_x in (rec, rec_on):
            assert rec_x.named("get_cached") == []
            assert [n for n, _a, _k in rec_x.shapes()] == ["set_cached"]
        assert rec.shapes() == rec_on.shapes()


# ===========================================================================
# F. Flag-OFF call-shape pins (base identity) and suspension pins
# ===========================================================================


async def _off_shape_s1a(mp, rec):
    mp.setattr(ps, "get_cached", _fake(rec, "get_cached", result=CATALOG))
    mp.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
    await ps._fetch_shopify_catalog(DOMAIN)
    return [("get_cached", ("shopify_catalog:store.example",), {})]


async def _off_shape_s1b(mp, rec):
    mp.setattr(ps, "get_cached", _fake(rec, "get_cached", result=None))
    mp.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
    _patch_curl(mp, _curl_returning(_Resp(status=404)))
    await ps._fetch_shopify_catalog(DOMAIN)
    return [
        ("get_cached", ("shopify_catalog:store.example",), {}),
        ("set_cached", ("shopify_catalog:store.example", {"_shopify_neg": True}, 1800), {}),
    ]


async def _off_shape_s1c(mp, rec):
    mp.setattr(ps, "get_cached", _fake(rec, "get_cached", result=None))
    mp.setattr(ps, "set_cached", _fake(rec, "set_cached", result=True))
    mp.setattr(ps, "_fetch_shopify_currency", AsyncMock(return_value="BHD"))
    _patch_curl(mp, _curl_returning(_Resp(status=200, payload=FRESH_PRODUCTS)))
    await ps._fetch_shopify_catalog(DOMAIN)
    return [
        ("get_cached", ("shopify_catalog:store.example",), {}),
        ("set_cached", (
            "shopify_catalog:store.example",
            {"products": [{"title": "Thing One", "variants": []}], "_store_currency": "BHD"},
            21600,
        ), {}),
    ]


async def _off_shape_s2_bolo(mp, rec):
    mp.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    mp.setattr(sds, "resolve_pdp_via_sitemap", _fake(rec, "resolve_pdp_via_sitemap", result=None))
    await ps.fetch_bolo_price("Lattafa Khamrah Qahwa")
    return [("resolve_pdp_via_sitemap", ("bolo.bh", "Lattafa Khamrah Qahwa"), {})]


async def _off_shape_s2_boutiqaat(mp, rec):
    mp.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    mp.setattr(sds, "resolve_pdp_via_sitemap", _fake(rec, "resolve_pdp_via_sitemap", result=None))
    await ps.fetch_boutiqaat_price("Lattafa Khamrah Qahwa")
    return [("resolve_pdp_via_sitemap", ("boutiqaat.com", "Lattafa Khamrah Qahwa"), {})]


async def _off_shape_s3(mp, rec):
    _s3_install_miss(mp, rec, "neg_landing_404")
    await als._harvest_config("goldenscent.com")
    return [
        ("get_cached", ("algolia_config:goldenscent.com",), {}),
        ("set_cached", ("algolia_config:goldenscent.com", {"_algolia_neg": True}, 86400), {}),
    ]


async def _off_shape_s4a(mp, rec):
    svc = _tier3_harness(mp)
    _install_s4a_fakes(mp, rec, sentinel=_sentinel(["bolo.bh"]), now_built=False)
    await _run_get_price(svc, nocache=False)
    neg_key = ps.negative_cache_key(_price_cache_key())
    assert neg_key.startswith("nogenuine:")
    return [
        ("get_negative_cache", (neg_key,), {}),
        ("sitemap_domains_now_built", (["bolo.bh"],), {}),
    ]


async def _off_shape_s4b(mp, rec):
    svc = _tier3_harness(mp)
    _install_s4b_fakes(mp, rec, is_cold=False, unbuilt=())
    await _run_get_price(svc, nocache=True)
    neg_key = ps.negative_cache_key(_price_cache_key())
    value = rec.named("set_negative_cache")[0][1][1]
    assert value["amount"] == 70.0 and value["estimated"] is True
    return [
        ("sitemap_discovery_is_cold", ("fragrances",), {}),
        ("sitemap_unbuilt_domains", ("fragrances",), {}),
        ("set_negative_cache", (neg_key, value, ps.NEGATIVE_PRICE_CACHE_TTL), {}),
    ]


async def _off_shape_s6(mp, rec):
    mp.setattr(rs, "get_cached", _fake(rec, "get_cached", result=None))
    mp.setattr(rs, "set_cached", _fake(rec, "set_cached", result=True))
    mp.setattr(
        "app.services.product_data_service.get_cached_reviews",
        AsyncMock(side_effect=lambda *a, **k: {"summary": "db"}),
    )
    await _get_reviews()
    key = _reviews_key()
    return [
        ("get_cached", (key,), {}),
        ("set_cached", (key, {"summary": "db"}, 7 * 24 * 60 * 60), {}),
    ]


_OFF_SHAPES = {
    "S1a": _off_shape_s1a,
    "S1b": _off_shape_s1b,
    "S1c": _off_shape_s1c,
    "S2_bolo": _off_shape_s2_bolo,
    "S2_boutiqaat": _off_shape_s2_boutiqaat,
    "S3": _off_shape_s3,
    "S4a": _off_shape_s4a,
    "S4b": _off_shape_s4b,
    "S6": _off_shape_s6,
}


@pytest.mark.asyncio
@pytest.mark.parametrize("site", sorted(_OFF_SHAPES))
async def test_off_call_shapes_exact(monkeypatch, site):
    _set_flag(monkeypatch, False)
    loop_thread = threading.current_thread()
    rec = _Rec()
    expected = await _OFF_SHAPES[site](monkeypatch, rec)
    assert rec.shapes() == expected
    for name, _a, kwargs, t in rec.calls:
        assert kwargs == {}, (name, kwargs)
        assert t is loop_thread, (name, t.name)


def _suspension_coro(mp, rec, site):
    """Each returns a NOT-yet-started coroutine for a path with no await today."""
    if site == "s1_hit":
        mp.setattr(ps, "get_cached", _fake(rec, "get_cached", result=CATALOG))
        return ps._fetch_shopify_catalog(DOMAIN)
    if site == "s1_negative":
        mp.setattr(ps, "get_cached", _fake(rec, "get_cached", result=SHOP_NEG))
        return ps._fetch_shopify_catalog(DOMAIN)
    if site == "s3_hit":
        mp.setattr(als, "get_cached", _fake(rec, "get_cached", result=ALG_CFG))
        return als._harvest_config(ALG_DOMAIN)
    if site == "s2_resolve_none":
        mp.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
        mp.setattr(sds, "resolve_pdp_via_sitemap", _fake(rec, "resolve_pdp_via_sitemap", result=None))
        return ps.fetch_bolo_price(SM_NAME)
    if site == "s6_l1_hit":
        mp.setattr(rs, "get_cached", _fake(rec, "get_cached", result={"summary": "cached"}))
        return _get_reviews_coro()
    raise AssertionError(site)


def _get_reviews_coro():
    return rs.get_reviews(
        R_BRAND, R_NAME, R_VARIANT, R_QUERY, nocache=False, category="other",
        search_results={"organic": []},
    )


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("site", ["s1_hit", "s1_negative", "s3_hit", "s2_resolve_none", "s6_l1_hit"])
async def test_off_no_new_suspension_on_hit_paths(monkeypatch, flag_on, site):
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    coro = _suspension_coro(monkeypatch, rec, site)
    if not flag_on:
        with pytest.raises(StopIteration):
            coro.send(None)
        assert len(rec.calls) == 1
    else:
        completed = False
        try:
            coro.send(None)
        except StopIteration:
            completed = True
        finally:
            coro.close()
        await _drain_pool()
        assert not completed, (
            f"ON: {site} completed on the first send; expected a suspension at the "
            "redis-offloop dispatch (site dispatch missing)"
        )


@pytest.mark.asyncio
@FLAG_ROWS
async def test_existing_positional_lambda_patches_still_work(monkeypatch, flag_on):
    """The tests/test_shopify_discovery_l13.py:238-239 shape keeps working."""
    _set_flag(monkeypatch, flag_on)
    store = {}
    monkeypatch.setattr(ps, "get_cached", lambda k: store.get(k))
    monkeypatch.setattr(ps, "set_cached", lambda k, v, ttl=0: store.__setitem__(k, v))
    calls = []
    _patch_curl(monkeypatch, _curl_returning(_Resp(status=500), counter=calls))
    assert await ps._fetch_shopify_catalog("brokenstore.example") is None
    assert await ps._fetch_shopify_catalog("brokenstore.example") is None
    assert len(calls) == 1, calls
    assert store == {"shopify_catalog:brokenstore.example": {"_shopify_neg": True}}


# ===========================================================================
# G. Exception parity (each ON row also pins the redis-offloop thread, RO6)
# ===========================================================================


@pytest.mark.asyncio
@FLAG_ROWS
async def test_exception_parity_s1_get(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    monkeypatch.setattr(
        ps, "get_cached", _fake(rec, "get_cached", raises=TypeError("non-str payload")),
    )
    with pytest.raises(TypeError, match="non-str payload"):
        await ps._fetch_shopify_catalog(DOMAIN)
    assert rec.shapes() == [("get_cached", (SHOP_KEY,), {})]
    if flag_on:
        _assert_on_threads(rec, "G S1 get")


@pytest.mark.asyncio
@FLAG_ROWS
async def test_exception_parity_s2(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    rec = _Rec()
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(sds, "get_cached", _sds_get_fake(rec, raises=ConnectionError("down")))
    out = await ps.fetch_bolo_price(SM_NAME)
    assert out is None
    assert [a[0] for _n, a, _k in rec.shapes()] == ["discovery:sitemap:bolo.bh:meta"]
    if flag_on:
        _assert_on_threads(rec, "G S2")


class _BrokenRedis:
    def __init__(self, rec):
        self.rec = rec

    def get(self, key):
        self.rec.record("redis.get", (key,))
        raise ConnectionError("upstash down")

    def setex(self, key, ex, value):
        self.rec.record("redis.setex", (key, ex))
        raise ConnectionError("upstash down")

    def set(self, key, value):
        self.rec.record("redis.set", (key,))
        raise ConnectionError("upstash down")


@pytest.mark.asyncio
@FLAG_ROWS
async def test_exception_parity_set_failopen(monkeypatch, caplog, flag_on):
    """The REAL get_cached/set_cached over a raising client: S1 miss returns None,
    the neg set returns quietly, the same error-log counts in both branches."""
    _set_flag(monkeypatch, flag_on)
    caplog.set_level(logging.ERROR, logger=cs.logger.name)
    rec = _Rec()
    assert ps.get_cached is cs.get_cached and ps.set_cached is cs.set_cached
    monkeypatch.setattr(cs, "redis_client", _BrokenRedis(rec))
    _patch_curl(monkeypatch, _curl_returning(_Resp(status=404)))
    out = await ps._fetch_shopify_catalog(DOMAIN)
    assert out is None
    assert rec.shapes() == [
        ("redis.get", (SHOP_KEY,), {}),
        ("redis.setex", (SHOP_KEY, SHOP_NEG_TTL), {}),
    ]
    msgs = [r.getMessage() for r in caplog.records]
    assert sum("Redis GET error" in m for m in msgs) == 1, msgs
    assert sum("Redis SET error" in m for m in msgs) == 1, msgs
    if flag_on:
        _assert_on_threads(rec, "G set fail-open")


@pytest.mark.asyncio
@FLAG_ROWS
async def test_exception_parity_s4b(monkeypatch, flag_on):
    _set_flag(monkeypatch, flag_on)
    svc = _tier3_harness(monkeypatch)
    rec = _Rec()
    _install_s4b_fakes(monkeypatch, rec, raise_on_set=True)
    price = await _run_get_price(svc, nocache=True)
    assert price.get("estimated") is True and price.get("amount") == 70.0, price
    assert len(rec.named("set_negative_cache")) == 1
    if flag_on:
        _assert_on_threads(rec, "G S4b", names={"set_negative_cache"})


# ===========================================================================
# H. Source pins (AST)
# ===========================================================================

_HELPER = "run_redis_offloop"
_WRAPPED = {
    "get_cached", "set_cached", "get_negative_cache", "sitemap_domains_now_built",
    "resolve_pdp_via_sitemap", "_record_negative_price_cache", "sitemap_discovery_is_cold",
}


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _find_function(path, name, cls=None):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    scope = tree.body
    if cls is not None:
        (klass,) = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls]
        scope = klass.body
    found = [n for n in scope
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    assert len(found) == 1, f"{path.name}: expected one def {name}"
    return found[0]


def _helper_dispatches(fn_node):
    """(target, durable, helper_call) per run_redis_offloop call in the function."""
    out = []
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call) and _call_name(node.func) == _HELPER:
            assert node.args, "run_redis_offloop called without a callable"
            first = node.args[0]
            if isinstance(first, ast.Lambda):
                assert not first.args.args, "the S4b lambda must take no arguments"
                body = first.body
                target = "lambda:" + (_call_name(body.func) if isinstance(body, ast.Call) else "?")
            else:
                target = _call_name(first)
            durable = any(
                kw.arg == "durable" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords
            )
            out.append((target, durable, node))
    return out


def _direct_wrapped_calls(fn_node):
    covered = set()
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call) and _call_name(node.func) == _HELPER:
            for arg in node.args:
                for sub in ast.walk(arg):
                    covered.add(id(sub))
    return [
        (_call_name(n.func), n.lineno)
        for n in ast.walk(fn_node)
        if isinstance(n, ast.Call) and _call_name(n.func) in _WRAPPED and id(n) not in covered
    ]


_SITE_FUNCS = [
    # (file, class, function, expected sorted dispatches, expected direct calls)
    ("services/price_service.py", None, "_fetch_shopify_catalog",
     [("get_cached", False), ("set_cached", True), ("set_cached", True)], []),
    ("services/price_service.py", None, "fetch_bolo_price",
     [("resolve_pdp_via_sitemap", False)], []),
    ("services/price_service.py", None, "fetch_boutiqaat_price",
     [("resolve_pdp_via_sitemap", False)], []),
    ("services/algolia_service.py", None, "_harvest_config",
     [("get_cached", False), ("set_cached", True), ("set_cached", True)], []),
    ("services/structured_comparison_service.py", "StructuredComparisonService", "_get_price",
     [("get_negative_cache", False),
      ("lambda:_record_negative_price_cache", True),
      ("lambda:_record_negative_price_cache", True),
      ("sitemap_domains_now_built", False)], []),
    ("services/review_service.py", None, "get_reviews",
     [("get_cached", False), ("set_cached", True)],
     ["set_cached", "set_cached", "set_cached"]),
]


@pytest.mark.parametrize(
    "rel,cls,func,expected,direct", _SITE_FUNCS, ids=[f[2] for f in _SITE_FUNCS],
)
def test_source_every_in_scope_site_routes_through_helper(rel, cls, func, expected, direct):
    """RO6: EXACT per-function dispatch counts (writes durable=True, reads not) and
    zero direct calls of the wrapped names outside the helper, except the three
    post-extraction set_cached calls in get_reviews."""
    fn = _find_function(APP / rel, func, cls)
    dispatches = _helper_dispatches(fn)
    got = sorted((t, d) for t, d, _n in dispatches)
    assert got == sorted(expected), (
        f"{func}: run_redis_offloop dispatches {got} != expected {sorted(expected)}"
    )
    got_direct = sorted(name for name, _ln in _direct_wrapped_calls(fn))
    assert got_direct == sorted(direct), (
        f"{func}: direct (un-dispatched) calls {_direct_wrapped_calls(fn)}; expected {direct}"
    )


@pytest.mark.parametrize(
    "rel,func,awaited_calls",
    [("services/price_service.py", "_fetch_shopify_catalog", 4),
     ("services/algolia_service.py", "_harvest_config", 3)],
)
def test_source_negcache_closure_is_async_and_awaited(rel, func, awaited_calls):
    """RO6: one of the two writes sits inside the nested ``async def _negcache``,
    and every one of its call sites is awaited."""
    fn = _find_function(APP / rel, func)
    nested = [n for n in ast.walk(fn)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_negcache"]
    assert len(nested) == 1, f"{func}: expected one nested _negcache"
    assert isinstance(nested[0], ast.AsyncFunctionDef), f"{func}: _negcache must be async def"
    inner = _helper_dispatches(nested[0])
    assert [(t, d) for t, d, _n in inner] == [("set_cached", True)], inner
    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and _call_name(n.func) == "_negcache"]
    awaited = [n for n in ast.walk(fn)
               if isinstance(n, ast.Await) and isinstance(n.value, ast.Call)
               and _call_name(n.value.func) == "_negcache"]
    assert len(calls) == awaited_calls and len(awaited) == awaited_calls, (
        f"{func}: {len(calls)} _negcache() calls, {len(awaited)} awaited; "
        f"expected {awaited_calls} awaited"
    )


def test_source_s4b_lambda_evaluates_is_cold_inside():
    """The :8513 lambda carries sitemap_discovery_is_cold(category) inside its body."""
    fn = _find_function(
        APP / "services/structured_comparison_service.py", "_get_price", "StructuredComparisonService",
    )
    lambdas = [n.args[0] for _t, _d, n in _helper_dispatches(fn) if isinstance(n.args[0], ast.Lambda)]
    assert len(lambdas) == 2, f"expected the two S4b lambdas, found {len(lambdas)}"
    with_is_cold = [
        lam for lam in lambdas
        if any(isinstance(s, ast.Call) and _call_name(s.func) == "sitemap_discovery_is_cold"
               for s in ast.walk(lam))
    ]
    assert len(with_is_cold) == 1, "exactly one S4b lambda must evaluate sitemap_discovery_is_cold"
    kwargs = {kw.arg for kw in with_is_cold[0].body.keywords}
    assert kwargs == {"guard_rejected", "transient_discovery", "discovery_degraded", "category"}, kwargs


def test_redis_offloop_module_is_a_leaf():
    path = APP / "utils" / "redis_offloop.py"
    assert path.exists(), f"{path} does not exist (the helper module is not written yet)"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [a.name for a in node.names if a.name == "app" or a.name.startswith("app.")]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level == 0 and (mod == "app" or mod.startswith("app.")):
                bad.append(mod)
            if node.level > 0:
                bad.append("." * node.level + mod)
    assert not bad, f"app/utils/redis_offloop.py must import stdlib only; found {bad}"


# ===========================================================================
# RO2. The two unflagged CONSUME-BOUND log lines, pinned under BOTH flag states
# ===========================================================================


@pytest.mark.asyncio
@FLAG_ROWS
@pytest.mark.parametrize("family", ["shopify", "algolia"])
async def test_ro2_consume_bound_log_line(monkeypatch, caplog, flag_on, family):
    """RO2: the silent TimeoutError branch of the bahrain Shopify consume
    (scs ~:7516) and of the Algolia consume (~:7618) logs ONE
    ``[ADAPTER DROP] <family>: CONSUME-BOUND after <cap:.2f>s`` line naming the cap
    it waited under; the cascade still falls through to Tier-3."""
    _set_flag(monkeypatch, flag_on)
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc = _tier3_harness(monkeypatch)

    async def _slow(*a, **k):
        await asyncio.sleep(5)
        return None

    if family == "shopify":
        monkeypatch.setattr(
            scs, "get_shopify_sources_for_category",
            lambda c: [SimpleNamespace(domain="store.example")],
        )
        monkeypatch.setattr(scs, "fetch_shopify_price", _slow)
        cap = 3.0
    else:
        monkeypatch.setattr(
            scs, "get_algolia_sources_for_category",
            lambda c: [SimpleNamespace(domain="goldenscent.com")],
        )
        monkeypatch.setattr(als, "fetch_algolia_price", _slow)
        cap = scs._ALGOLIA_TIER2_TIMEOUT
    real_reserve = scs._pre_reserve_remaining
    monkeypatch.setattr(
        scs, "_pre_reserve_remaining",
        lambda c, dl: 0.3 if c == cap else real_reserve(c, dl),
    )
    price = await _run_get_price(svc, nocache=True)
    assert price.get("estimated") is True, price
    drops = [r.getMessage() for r in caplog.records
             if r.name == _SCS_LOGGER and _DROP in r.getMessage()]
    lines = [m for m in drops
             if re.fullmatch(rf"\[ADAPTER DROP\] {family}: CONSUME-BOUND after {_NUM}s", m)]
    assert len(lines) == 1, f"{family}: expected ONE CONSUME-BOUND line, got {drops}"
    bound = re.fullmatch(r"\[ADAPTER DROP\] \w+: CONSUME-BOUND after (\d+(?:\.\d+)?)s", lines[0])
    assert bound and float(bound.group(1)) == pytest.approx(0.3, abs=0.051), lines[0]
    assert re.search(r"after \d+\.\d{2}s$", lines[0]), f"the cap is formatted :.2f: {lines[0]}"


# ===========================================================================
# RO6. Orchestrator-level: the bahrain Shopify consume under ON
# ===========================================================================


@pytest.mark.asyncio
async def test_orchestrator_bahrain_shopify_consume_on_collects_all(monkeypatch, caplog):
    """RO6: 12 Shopify sources, each catalog GET a blocking 0.1 s; with the flag ON
    and a test-level pool of 16, every catalog GET runs in a redis-offloop thread,
    they overlap, and all 12 results are collected inside the 3.0 s consume cap
    (no CONSUME-BOUND drop)."""
    _set_flag(monkeypatch, True)
    monkeypatch.setenv(KNOB, "16")
    caplog.set_level(logging.INFO, logger=_SCS_LOGGER)
    svc = _tier3_harness(monkeypatch)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    domains = [f"shop{i:02d}.example" for i in range(12)]
    monkeypatch.setattr(
        scs, "get_shopify_sources_for_category",
        lambda c: [SimpleNamespace(domain=d) for d in domains],
    )
    monkeypatch.setattr(scs, "fetch_shopify_price", ps.fetch_shopify_price)
    rec = _Rec()
    lock = threading.Lock()
    live = {"now": 0, "peak": 0}

    def fake_get(key):
        if not str(key).startswith("shopify_catalog:"):
            return None
        rec.record("get_cached", (key,))
        with lock:
            live["now"] += 1
            live["peak"] = max(live["peak"], live["now"])
        try:
            time.sleep(0.1)
        finally:
            with lock:
                live["now"] -= 1
        return copy.deepcopy(CATALOG)

    monkeypatch.setattr(ps, "get_cached", fake_get)
    matched = []

    def fake_match(catalog, product_name, currency, domain, resolved_category=None):
        matched.append(domain)
        return None

    monkeypatch.setattr(ps, "_match_shopify_product", fake_match)
    started = time.monotonic()
    price = await _run_get_price(svc, nocache=True)
    elapsed = time.monotonic() - started
    assert price.get("estimated") is True, price
    assert sorted(matched) == sorted(domains), f"collected {len(matched)}/12: {matched}"
    assert sorted(a[0] for _n, a, _k in rec.shapes()) == sorted(
        f"shopify_catalog:{d}" for d in domains
    )
    _assert_on_threads(rec, "orchestrator shopify consume")
    assert live["peak"] >= 4, f"the 12 catalog GETs did not overlap (peak {live['peak']})"
    drops = [r.getMessage() for r in caplog.records if "shopify: CONSUME-BOUND" in r.getMessage()]
    assert not drops, drops
    assert elapsed < 3.0, f"_get_price took {elapsed:.2f}s"

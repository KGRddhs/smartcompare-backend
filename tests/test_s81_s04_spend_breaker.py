"""S81-04 SPEND-BREAKER (ENABLE_LLM_SPEND_BREAKER): the RED file.

Per-Asia/Riyadh-day USD caps in four lanes (live, escalation, search, offclock)
on every LLM dispatch, read and recorded through one Upstash key per lane and
day. Contract: spec .qa-s80/S81-04_UNIT_SPEC.md as amended by its adversarial
review and RULINGS_S81_04 (rulings win, then the review corrections, then the
spec). The rulings that shape this file:

- R-S04-1  per-process memo of each lane total (LLM_SPEND_MEMO_SECONDS, 5.0)
           plus this process's own recorded deltas; Upstash read only when stale.
- R-S04-2  every awaited Redis call bounded (LLM_SPEND_REDIS_TIMEOUT_SECONDS,
           0.5) on a DEDICATED `llm-spend` pool of 4 workers; a timeout is
           fail-open naming TimeoutError; `_client() is None` short-circuits on
           the loop before any hop.
- R-S04-3  an unpriced call is bounded and recorded with the conservative
           per-provider rates (OpenAI: the gpt-4o row; Anthropic and any other
           provider: the Sonnet row), never zero.
- R-S04-4  the compare entry refuses when spent + LLM_SPEND_ENTRY_RESERVE_USD
           (0.10) >= cap (REST and SSE), through the existing LLM_UNAVAILABLE
           non-delivery (refund, no history row, R-A3).
- R-S04-5  reserve(lane, ub) = ONE Lua check-and-increment; settle(lane, ub,
           actual) = one INCRBYFLOAT of (actual - ub).
- R-S04-6  LLM_SPEND_CHOKEPOINT_LANE (default live, garbage -> live).
- R-S04-7  /health carries ONLY {lane: {exhausted, day}} + llm_spend_fail_open;
           the amounts live on GET /api/v1/admin/costs `spend_breaker`.
- R-S04-9  image bound per provider: OpenAI 1,445 tokens per image part,
           Anthropic ceil(w/28) x ceil(h/28) capped at 4,784.
- R-S04-10 the prompt bound adds response_format and tools; admit sanitises its
           bound; R10b; P08; fakes carry the measured client surface.

Every RED row fails at the base on an AssertionError only: missing symbols are
reached through ``_leaf()`` / ``_need()`` (find_spec / hasattr asserts), never
an ImportError or AttributeError. Every PIN row runs with the FULL
configuration (every knob set, a fake Upstash seeded OVER cap on every lane,
call recorders), so a not-gated mutant is killed (ruling B1).

Hermetic: no network (the conftest guard; the price leg is stubbed in the
compare rows so no adapter reaches a real store), no real Redis (fakes on
``cache_service.redis_client``), no real clock where a value matters (the
leaf's ``_utcnow`` / ``_monotonic`` seams), no .env, synthetic ids only.
Every 10-digit expectation and every epoch is built at run time.
"""
import ast
import asyncio
import concurrent.futures
import contextlib
import copy
import importlib
import importlib.util
import inspect
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai as openai_sdk
import pytest
from fastapi.testclient import TestClient

from app.main import app  # first: the import-time load_dotenv runs before any setenv
import app.main as main_mod
from app.api import auth_routes
from app.api import text_routes as tr
from app.middleware.rate_limiter import limiter
from app.services import api_budget_service as abs_mod
from app.services import audit_service
from app.services import brightdata_service as bd_mod
from app.services import cache_service
from app.services import content_safety_service
from app.services import extraction_service as extraction_mod
from app.services import firecrawl_service as fc_mod
from app.services import llm_pricing
from app.services import openai_pricing
from app.services import openai_service as oai
from app.services import serper_service as ss
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as url_extraction_mod
from app.utils import async_utils

ROOT = Path(__file__).resolve().parent.parent
LEAF = "app.services.llm_spend_breaker"
LEAF_PATH = ROOT / "app" / "services" / "llm_spend_breaker.py"
FLAG = "ENABLE_LLM_SPEND_BREAKER"
W13 = "ENABLE_LLM_PREFLIGHT_BREAKER"
W13_TTL = "LLM_BREAKER_CACHE_TTL"
CAP_ENV = {
    "live": "LLM_SPEND_CAP_LIVE_USD",
    "escalation": "LLM_SPEND_CAP_ESCALATION_USD",
    "search": "LLM_SPEND_CAP_SEARCH_USD",
    "offclock": "LLM_SPEND_CAP_OFFCLOCK_USD",
}
MEMO_ENV = "LLM_SPEND_MEMO_SECONDS"
TIMEOUT_ENV = "LLM_SPEND_REDIS_TIMEOUT_SECONDS"
RESERVE_ENV = "LLM_SPEND_ENTRY_RESERVE_USD"
LANE_ENV = "LLM_SPEND_CHOKEPOINT_LANE"
ALL_ENV = (FLAG, W13, W13_TTL, MEMO_ENV, TIMEOUT_ENV, RESERVE_ENV, LANE_ENV) + tuple(CAP_ENV.values())
LANES = ("live", "escalation", "search", "offclock")
DEFAULT_CAPS = {"live": 3.0, "escalation": 1.0, "search": 0.5, "offclock": 2.0}

UTC = timezone.utc
NOW = datetime(2026, 10, 23, 3, 34, tzinfo=UTC)
DAY = "2026-10-23"
EXPIREAT = int(datetime(2026, 10, 23, 22, 0, tzinfo=UTC).timestamp())
MINI = "gpt-4o-" + "mini"
GPT4O = "gpt-" + "4o"
HAIKU = "claude-haiku-" + "5-5"
SONNET = "claude-sonnet-" + "5-5"
UNPRICED_OPENAI = "gpt-" + "unpriced-test"
UNPRICED_ANTHROPIC = "claude-" + "unpriced-test"
# The base openai_pricing ledger entry for one gpt-4o-mini response with usage
# 1000 / 200 (measured at dfc6502f through record_openai_response).
BASE_LEDGER_ENTRY = {"model": MINI, "prompt_tokens": 1000, "completion_tokens": 200,
                     "cached_tokens": 0, "cost_usd": (1000 * 0.15 + 200 * 0.60) / 1e6}
# The /health keys the S77 pin allows (tests/test_s77_redis_offloop.py) plus the pool key.
BASE_HEALTH_KEYS = {"status", "message", "loop_lag_ms", "loop_lag_max_ms", "loop_lag_max_60s_ms",
                    "price_parse_pool", "adapter_executor", "brightdata_auth", "redis_offloop_pool"}
# GC-9: the two Lua texts pinned as compact literals (the S81-03 precedent).
# RECORD: KEYS[1] = the lane key, ARGV = [delta, expireat].
# RESERVE: KEYS[1] = the lane key, ARGV = [upper_bound, cap, expireat].
RECORD_SCRIPT_PIN = ("local v = redis.call('INCRBYFLOAT', KEYS[1], ARGV[1])\n"
                     "redis.call('EXPIREAT', KEYS[1], ARGV[2])\n"
                     "return v")
RESERVE_SCRIPT_PIN = ("local cur = tonumber(redis.call('GET', KEYS[1]) or '0')\n"
                      "if cur + tonumber(ARGV[1]) > tonumber(ARGV[2]) then return false end\n"
                      "local v = redis.call('INCRBYFLOAT', KEYS[1], ARGV[1])\n"
                      "redis.call('EXPIREAT', KEYS[1], ARGV[3])\n"
                      "return v")
# Clock / id fields that differ between two runs of the same tree (the FY25 set).
VOLATILE = frozenset({"elapsed_ms", "elapsed_seconds", "timestamp", "generated_at",
                      "created_at", "started_at", "cached_at", "fetched_at", "at",
                      "stage_timings_ms", "orchestrator_timings_ms", "request_id"})


# ---------------------------------------------------------------------------
# probes: every missing symbol is an AssertionError, never ImportError
# ---------------------------------------------------------------------------
def _leaf_or_none():
    if importlib.util.find_spec(LEAF) is None:
        return None
    return importlib.import_module(LEAF)


def _leaf():
    assert importlib.util.find_spec(LEAF) is not None, (
        "app/services/llm_spend_breaker.py does not exist (S81-04 leaf)")
    return importlib.import_module(LEAF)


def _need(mod, name):
    assert hasattr(mod, name), "%s has no attribute %r" % (getattr(mod, "__name__", mod), name)
    return getattr(mod, name)


def _f10(x):
    return "%.10f" % x


def _approx(x):
    return pytest.approx(x, rel=1e-9, abs=1e-12)


def _openai_rate(model):
    return openai_pricing.PRICE_USD_PER_1M[model]


def _anthropic_rate(model):
    return llm_pricing.ANTHROPIC_PRICE_USD_PER_1M[model]


def _conservative_openai(prompt, output):
    r = _openai_rate(GPT4O)
    return (prompt * r["input"] + output * r["output"]) / 1e6


def _conservative_anthropic(prompt, output, searches=0):
    r = _anthropic_rate(SONNET)
    return (prompt * r["input"] + output * r["output"]) / 1e6 + searches * 0.01


def _key(lane, day=DAY):
    return "llm_spend:%s:%s" % (lane, day)


class Clock:
    def __init__(self, t=0.0):
        self.t = float(t)

    def __call__(self):
        return self.t


def _freeze(monkeypatch, leaf, when=NOW, clock=None):
    _need(leaf, "_utcnow")
    _need(leaf, "_monotonic")
    clock = clock if clock is not None else Clock(1000.0)
    monkeypatch.setattr(leaf, "_utcnow", lambda: when)
    monkeypatch.setattr(leaf, "_monotonic", clock)
    return clock


# ---------------------------------------------------------------------------
# fake Redis clients (the measured client surface of app/, review correction 7)
# ---------------------------------------------------------------------------
class _FakeBase:
    def __init__(self, seed=None, eval_result=None):
        self.store = dict(seed or {})
        self.calls = []
        self.expireat = {}
        self.eval_result = eval_result
        self.block = None
        self.events = None
        self._lock = threading.Lock()

    def _rec(self, op, key, extra=None):
        t = threading.current_thread()
        self.calls.append((op, key, extra, t.ident, t.name))
        if self.events is not None and isinstance(key, str) and key.startswith("llm_spend:"):
            self.events.append(op)

    def get(self, key):
        self._rec("get", key)
        if self.block is not None:
            self.block.wait(8.0)
        return self.store.get(key)

    def set(self, key, value, ex=None, **kw):
        self._rec("set", key, value)
        self.store[key] = value
        return True

    def setex(self, key, ttl, value):
        self._rec("setex", key, value)
        self.store[key] = value
        return True

    def incr(self, key):
        self._rec("incr", key)
        self.store[key] = str(int(float(self.store.get(key, "0"))) + 1)
        return int(self.store[key])

    def incrby(self, key, n=1):
        self._rec("incrby", key, n)
        self.store[key] = str(int(float(self.store.get(key, "0"))) + int(n))
        return int(self.store[key])

    def decrby(self, key, n=1):
        self._rec("decrby", key, n)
        self.store[key] = str(int(float(self.store.get(key, "0"))) - int(n))
        return int(self.store[key])

    def incrbyfloat(self, key, amount):
        self._rec("incrbyfloat", key, amount)
        v = float(self.store.get(key, "0")) + float(amount)
        self.store[key] = repr(v)
        return v

    def mget(self, *keys):
        flat = list(keys[0]) if len(keys) == 1 and isinstance(keys[0], (list, tuple)) else list(keys)
        self._rec("mget", ",".join(map(str, flat)))
        return [self.store.get(k) for k in flat]

    def ttl(self, key):
        self._rec("ttl", key)
        return -1 if key in self.store else -2

    def expire(self, key, ttl):
        self._rec("expire", key, ttl)
        return True

    def delete(self, *keys):
        for k in keys:
            self._rec("delete", k)
            self.store.pop(k, None)
        return len(keys)

    def _run_script(self, script, keys, args):
        key = keys[0]
        self._rec("eval", key, (script, list(keys), [str(a) for a in args]))
        with self._lock:
            # GC-9: the fakes accept ONLY the pinned Lua texts.
            if script == RECORD_SCRIPT_PIN:
                new = float(self.store.get(key) or "0") + float(args[0])
                self.store[key] = repr(new)
                self.expireat[key] = int(args[1])
                return self.eval_result if self.eval_result is not None else repr(new)
            if script == RESERVE_SCRIPT_PIN:
                cur = float(self.store.get(key) or "0")
                ub, cap = float(args[0]), float(args[1])
                if cur + ub > cap:
                    return None
                new = cur + ub
                self.store[key] = repr(new)
                self.expireat[key] = int(args[2])
                return repr(new)
        raise AssertionError("fake redis: unrecognised Lua script %r" % (script,))


class FakeUpstash(_FakeBase):
    """upstash-redis 1.7.0 call shape: eval(script, keys=None, args=None)."""

    def eval(self, script, keys=None, args=None):
        return self._run_script(script, list(keys or []), list(args or []))


FakeUpstash.__module__ = "upstash_redis.client"


class FakeRedisPy(_FakeBase):
    """redis-py 8.1.0 call shape: eval(script, numkeys, *keys_and_args)."""

    def eval(self, script, numkeys, *keys_and_args):
        self.positional = (script, numkeys) + tuple(keys_and_args)
        keys = list(keys_and_args[:numkeys])
        args = list(keys_and_args[numkeys:])
        return self._run_script(script, keys, args)


FakeRedisPy.__module__ = "redis.client"


def _sentinel_text():
    return "spend-" + "sentinel-" + str(len(LANES) * 7)


class RaisingRedis(_FakeBase):
    def _boom(self, *a, **k):
        raise ConnectionError(_sentinel_text())

    get = _boom
    eval = _boom
    incrbyfloat = _boom


RaisingRedis.__module__ = "upstash_redis.client"


def _spend(fake, op=None):
    return [c for c in fake.calls
            if isinstance(c[1], str) and c[1].startswith("llm_spend:") and (op is None or c[0] == op)]


def _install(monkeypatch, fake):
    monkeypatch.setattr(cache_service, "redis_client", fake)
    return fake


def _full_seed(value="99.0"):
    """Every lane seeded OVER cap for the frozen Riyadh day AND today's real days."""
    days = {DAY, datetime.now(UTC).date().isoformat()}
    try:
        from datetime import timedelta
        days.add((datetime.now(UTC) + timedelta(hours=3)).date().isoformat())
    except Exception:  # pragma: no cover
        pass
    return {_key(lane, d): value for lane in LANES for d in days}


def _full_config(monkeypatch):
    """The FULL unit configuration for the PIN rows (ruling B1)."""
    monkeypatch.setenv(CAP_ENV["live"], "3.25")
    monkeypatch.setenv(CAP_ENV["escalation"], "1.5")
    monkeypatch.setenv(CAP_ENV["search"], "0.75")
    monkeypatch.setenv(CAP_ENV["offclock"], "2.5")
    monkeypatch.setenv(MEMO_ENV, "1.0")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    monkeypatch.setenv(RESERVE_ENV, "0.2")
    monkeypatch.setenv(LANE_ENV, "offclock")
    return _install(monkeypatch, FakeUpstash(seed=_full_seed()))


@contextlib.contextmanager
def _submit_spy():
    """Every ThreadPoolExecutor submit (the default pool, redis-offloop, llm-spend)."""
    seen = []
    orig = concurrent.futures.ThreadPoolExecutor.submit

    def spy(self, fn, *a, **k):
        seen.append(getattr(self, "_thread_name_prefix", ""))
        return orig(self, fn, *a, **k)

    with patch.object(concurrent.futures.ThreadPoolExecutor, "submit", spy):
        yield seen


async def _drain_spend_tasks():
    pending = [t for t in list(async_utils._BACKGROUND_TASKS)
               if not t.done() and "llm_spend" in (t.get_name() or "")]
    if pending:
        await asyncio.wait(pending, timeout=5.0)


# ---------------------------------------------------------------------------
# the W1-3 compare harness, COPIED from tests/test_openai_breaker.py:97-330
# ---------------------------------------------------------------------------
def _dict_breaker_redis(seed=None):
    store = dict(seed or {})
    ops = {"get": 0, "set": 0, "incr": 0, "expire": 0}

    def _get(key):
        ops["get"] += 1
        return store.get(key)

    def _set(key, value, ex=None):
        ops["set"] += 1
        store[key] = value
        return True

    def _incr(key):
        ops["incr"] += 1
        store[key] = str(int(store.get(key, "0")) + 1)
        return int(store[key])

    def _expire(key, ttl):
        ops["expire"] += 1
        return True

    return store, ops, _get, _set, _incr, _expire


def _patch_breaker_redis(get, set_, incr, expire):
    return (
        patch.object(abs_mod, "_redis_get", side_effect=get),
        patch.object(abs_mod, "_redis_set", side_effect=set_),
        patch.object(abs_mod, "_redis_incr", side_effect=incr),
        patch.object(abs_mod, "_redis_expire", side_effect=expire),
    )


def _half_open_breaker_seed(provider="openai"):
    return {
        abs_mod._circuit_key(provider): json.dumps({
            "state": abs_mod.CB_HALF_OPEN,
            "failure_count": abs_mod.CB_FAILURE_THRESHOLD,
            "tripped_at": time.time() - (abs_mod.CB_RECOVERY_TIMEOUT + 5),
            "half_open_calls": 0,
        })
    }


def _rate_limit_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return openai_sdk.RateLimitError("rate limit / credit balance exhausted", response=response, body=None)


def _usage(prompt=1000, completion=200):
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                           prompt_tokens_details=SimpleNamespace(cached_tokens=0))


def _mock_openai_client(raises=None, content='{"f": "v"}', usage=None, events=None, sent=None):
    """A stand-in AsyncOpenAI whose chat.completions.create is countable."""
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage

    async def _create(**kw):
        if events is not None:
            events.append("create")
        if sent is not None:
            sent.append(dict(kw))
        if raises is not None:
            raise raises
        return resp

    client.chat.completions.create = AsyncMock(side_effect=_create)
    client._resp = resp
    _flagged = MagicMock()
    _flagged.flagged = False
    _mod_resp = MagicMock()
    _mod_resp.results = [_flagged]
    client.moderations.create = AsyncMock(return_value=_mod_resp)
    return client


def _reset_breaker_memo():
    for module in (oai, scs, abs_mod):
        for name in ("_reset_openai_breaker_cache", "_reset_llm_breaker_cache", "_reset_openai_gate_cache"):
            hook = getattr(module, name, None)
            if callable(hook):
                hook()


def _arm_prod_search_config(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "0")
    monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "bd-test-dummy")
    monkeypatch.setenv("BRIGHTDATA_ZONE", "serp_api1")
    monkeypatch.delenv("ENABLE_BRIGHTDATA_BUDGET_GATE", raising=False)


class _FanOutCounters:
    def __init__(self):
        self.calls = {"search_web": 0, "bd_search_web": 0, "firecrawl": 0}

    async def search_web(self, *args, **kwargs):
        self.calls["search_web"] += 1
        return {"organic": [], "shopping": []}

    async def bd_search_web(self, *args, **kwargs):
        self.calls["bd_search_web"] += 1
        return {"organic": []}

    async def firecrawl(self, *args, **kwargs):
        self.calls["firecrawl"] += 1
        return None

    async def firecrawl_with_status(self, *args, **kwargs):
        self.calls["firecrawl"] += 1
        return None, 0

    def patches(self, llm_client):
        async def _no_price(*a, **k):
            return None

        return (
            patch.object(ss, "search_web", side_effect=self.search_web),
            patch.object(scs, "search_web", side_effect=self.search_web),
            patch.object(bd_mod, "bd_search_web", side_effect=self.bd_search_web),
            patch.object(fc_mod, "scrape_page", side_effect=self.firecrawl),
            patch.object(fc_mod, "scrape_page_with_status", side_effect=self.firecrawl_with_status),
            patch.object(oai, "get_client", return_value=llm_client),
            patch.object(extraction_mod, "get_client", return_value=llm_client),
            patch.object(url_extraction_mod, "get_client", return_value=llm_client),
            # the price leg is the only adapter fan-out that reaches real stores
            # (measured: algolia / unbxd / shopify / noon); stubbed so no row is egress
            patch.object(scs.StructuredComparisonService, "_get_price", side_effect=_no_price),
        )


@contextlib.contextmanager
def _all(*context_managers):
    with contextlib.ExitStack() as stack:
        for cm in context_managers:
            stack.enter_context(cm)
        yield


async def _run_compare(query="Acme Widget vs Globex Gadget"):
    service = scs.get_comparison_service()
    return await service.compare_from_text(
        query=query, region="bahrain", explicit_pair=("Acme Widget", "Globex Gadget"))


async def _run_stream(query="Acme Widget vs Globex Gadget"):
    service = scs.get_comparison_service()
    events = []
    async for event_type, data in service.compare_from_text_streaming(
            query=query, region="bahrain", explicit_pair=("Acme Widget", "Globex Gadget")):
        events.append((event_type, data))
    return events


def _stub_l1(calls):
    stub = MagicMock()

    def _check(query):
        calls.append(query)
        return SimpleNamespace(allowed=False, reason="probe", category="probe")

    stub.check_query_intent = _check

    async def _noop(*a, **k):
        return None

    return (patch.object(content_safety_service, "get_content_safety_service", return_value=stub),
            patch.object(audit_service, "log_content_blocked", _noop))


def _strip(obj):
    if isinstance(obj, dict):
        return {str(k): _strip(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, (list, tuple)):
        return [_strip(v) for v in obj]
    return obj


def _kw_key(kw):
    return json.dumps(kw, sort_keys=True, default=str)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in ALL_ENV:
        monkeypatch.delenv(name, raising=False)
    _reset_breaker_memo()
    leaf = _leaf_or_none()
    if leaf is not None and callable(getattr(leaf, "_reset_spend_breaker_state", None)):
        leaf._reset_spend_breaker_state()
    yield
    leaf = _leaf_or_none()
    if leaf is not None and callable(getattr(leaf, "_reset_spend_breaker_state", None)):
        leaf._reset_spend_breaker_state()
    _reset_breaker_memo()


# ===========================================================================
# R01-R09: the leaf, its knobs and its pure helpers
# ===========================================================================
_STDLIB = {"asyncio", "concurrent", "concurrent.futures", "contextvars", "functools", "json",
           "logging", "math", "os", "threading", "time", "datetime", "typing", "__future__"}
_APP_OK = {("app.services", "cache_service"), ("app.services", "llm_pricing"),
           ("app.services", "openai_pricing"), ("app.utils", "async_utils")}


def test_r01_leaf_exists_and_import_rule():
    _leaf()
    tree = ast.parse(LEAF_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name in _STDLIB, "top-level import %r is not stdlib" % a.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("app."):
                for a in node.names:
                    assert (mod, a.name) in _APP_OK, "top-level app import %s.%s" % (mod, a.name)
            else:
                assert mod in _STDLIB, "top-level import from %r is not stdlib" % mod
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr != "_LEDGER", "the leaf reads a ._LEDGER attribute (S81-03 A1)"
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("api_budget_service"):
            pass
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not re.match(r"^(gpt-|claude-|o[0-9]|omni-)", node.value), (
                "model-id literal %r in the leaf" % node.value)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").endswith("api_budget_service"), (
                "api_budget_service imported at the top of the leaf (cycle; import it in the arm)")


@pytest.mark.parametrize("value,expected", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False), ("off", False),
    ("garbage", False), (" FALSE ", False), ("true", True), ("1", True), ("yes", True),
    ("on", True), (" TRUE ", True),
])
def test_r02_flag_reader_idiom(monkeypatch, value, expected):
    leaf = _leaf()
    fn = _need(leaf, "spend_breaker_enabled")
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert fn() is expected
    monkeypatch.setenv(FLAG, "true" if not expected else "off")
    assert fn() is (not expected), "the flag is not re-read per call"


def test_r03_lanes_defaults_and_knob_names(monkeypatch):
    leaf = _leaf()
    assert _need(leaf, "LANES") == LANES == llm_pricing.SPEND_LANES
    assert _need(leaf, "DEFAULT_CAPS_USD") == DEFAULT_CAPS
    assert _need(leaf, "CAP_ENV") == CAP_ENV
    assert _need(leaf, "FLAG") == FLAG
    assert (leaf.LANE_LIVE, _need(leaf, "LANE_ESCALATION"), _need(leaf, "LANE_SEARCH"),
            _need(leaf, "LANE_OFFCLOCK")) == LANES
    assert _need(leaf, "RIYADH_UTC_OFFSET_HOURS") == 3
    assert _need(leaf, "KEY_PREFIX") == "llm_spend"
    assert _need(leaf, "memo_seconds")() == 5.0
    assert _need(leaf, "redis_timeout_seconds")() == 0.5
    assert _need(leaf, "entry_reserve_usd")() == pytest.approx(0.10)
    assert _need(leaf, "chokepoint_lane")() == "live"
    monkeypatch.setenv(MEMO_ENV, "7")
    monkeypatch.setenv(TIMEOUT_ENV, "0.25")
    monkeypatch.setenv(RESERVE_ENV, "0.3")
    monkeypatch.setenv(LANE_ENV, "offclock")
    assert (leaf.memo_seconds(), leaf.redis_timeout_seconds(), leaf.entry_reserve_usd(),
            leaf.chokepoint_lane()) == (7.0, 0.25, pytest.approx(0.3), "offclock")


_BAD_FLOATS = ["", "  ", "abc", "inf", "-inf", "nan", "0", "-1"]


@pytest.mark.parametrize("lane", LANES)
@pytest.mark.parametrize("raw,expected", [(None, None)] + [(b, None) for b in _BAD_FLOATS]
                         + [("4.5", 4.5), (" 7 ", 7.0)])
def test_r04_cap_knob_parse(monkeypatch, lane, raw, expected):
    leaf = _leaf()
    cap_usd = _need(leaf, "cap_usd")
    if raw is None:
        monkeypatch.delenv(CAP_ENV[lane], raising=False)
    else:
        monkeypatch.setenv(CAP_ENV[lane], raw)
    assert cap_usd(lane) == (DEFAULT_CAPS[lane] if expected is None else expected)


@pytest.mark.parametrize("env,getter,default", [
    (MEMO_ENV, "memo_seconds", 5.0),
    (TIMEOUT_ENV, "redis_timeout_seconds", 0.5),
    (RESERVE_ENV, "entry_reserve_usd", 0.10),
])
@pytest.mark.parametrize("raw,expected", [(None, None)] + [(b, None) for b in _BAD_FLOATS]
                         + [("2.5", 2.5), (" 7 ", 7.0)])
def test_r04b_other_knob_parse(monkeypatch, env, getter, default, raw, expected):
    leaf = _leaf()
    fn = _need(leaf, getter)
    if raw is None:
        monkeypatch.delenv(env, raising=False)
    else:
        monkeypatch.setenv(env, raw)
    assert fn() == pytest.approx(default if expected is None else expected)


@pytest.mark.parametrize("raw,expected", [
    (None, "live"), ("", "live"), ("garbage", "live"), ("llm", "live"), ("offclock", "offclock"),
    (" Search ", "search"), ("ESCALATION", "escalation"),
])
def test_r04c_chokepoint_lane_knob(monkeypatch, raw, expected):
    leaf = _leaf()
    fn = _need(leaf, "chokepoint_lane")
    if raw is None:
        monkeypatch.delenv(LANE_ENV, raising=False)
    else:
        monkeypatch.setenv(LANE_ENV, raw)
    assert fn() == expected


@pytest.mark.parametrize("instant,day,expire_day", [
    (datetime(2026, 10, 22, 20, 59, 59, tzinfo=UTC), "2026-10-22", (2026, 10, 22)),
    (datetime(2026, 10, 22, 21, 0, 0, tzinfo=UTC), "2026-10-23", (2026, 10, 23)),
    (datetime(2026, 12, 31, 21, 30, 0, tzinfo=UTC), "2027-01-01", (2027, 1, 1)),
    (datetime(2026, 10, 23, 3, 34, 0, tzinfo=UTC), "2026-10-23", (2026, 10, 23)),
])
def test_r05_riyadh_day(instant, day, expire_day):
    leaf = _leaf()
    got = _need(leaf, "riyadh_day")(instant)
    expire = int(datetime(*expire_day, 22, 0, tzinfo=UTC).timestamp())
    assert got == (day, expire)
    assert isinstance(got[1], int)
    assert _need(leaf, "spend_key")("live", "2026-10-23") == "llm_spend:live:2026-10-23"


def test_r06_unknown_lane_is_a_value_error(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash())
    for call in (lambda: _need(leaf, "admit")("llm", 0.1),
                 lambda: _need(leaf, "record")("llm", 0.1),
                 lambda: _need(leaf, "cap_usd")("x"),
                 lambda: _need(leaf, "spend_key")("x", DAY),
                 lambda: _need(leaf, "reserve")("llm", 0.1),
                 lambda: _need(leaf, "settle")("llm", 0.1, 0.2)):
        with pytest.raises(ValueError):
            call()
    assert fake.calls == []


def _msg(text):
    return [{"role": "user", "content": text}]


def _image_msg(url_len):
    url = "data:image/jpeg;base64," + "A" * url_len
    return [{"role": "user", "content": [
        {"type": "text", "text": "t" * 100},
        {"type": "image_url", "image_url": {"url": url, "detail": "auto"}},
    ]}]


_RF = {"type": "json_schema", "json_schema": {"name": "probe", "strict": True,
                                              "schema": {"type": "object", "properties": {}}}}
_TOOLS = [{"type": "function", "function": {"name": "probe_tool", "parameters": {"type": "object"}}}]


@pytest.mark.parametrize("case", ["text", "arabic", "image_big", "image_small", "none", "content_none",
                                  "unknown_part", "response_format", "tools", "anthropic_image"])
def test_r07_prompt_token_upper_bound(case):
    leaf = _leaf()
    fn = _need(leaf, "prompt_token_upper_bound")
    arabic = "".join(chr(0x0627 + i) for i in range(10))
    part = {"type": "x", "v": 1}
    table = {
        "text": (lambda: fn(_msg("x" * 4000)), 4020),
        "arabic": (lambda: fn(_msg(arabic)), 16 + 4 + 20),
        "image_big": (lambda: fn(_image_msg(1000000)), 16 + 4 + 100 + 1445),
        "image_small": (lambda: fn(_image_msg(10)), 16 + 4 + 100 + 1445),
        "none": (lambda: fn(None), 16),
        "content_none": (lambda: fn([{"role": "user", "content": None}]), 20),
        "unknown_part": (lambda: fn([{"role": "user", "content": [part]}]), 16 + 4 + len(json.dumps(part))),
        "response_format": (lambda: fn(_msg("x" * 100), response_format=_RF),
                            16 + 4 + 100 + len(json.dumps(_RF, default=str).encode("utf-8"))),
        "tools": (lambda: fn(_msg("x" * 100), tools=_TOOLS),
                  16 + 4 + 100 + len(json.dumps(_TOOLS, default=str).encode("utf-8"))),
        "anthropic_image": (lambda: fn([{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "data": "A" * 50000}}]}],
            provider="anthropic"), 16 + 4 + 4784),
    }
    call, expected = table[case]
    assert call() == expected


@pytest.mark.parametrize("wh,expected", [
    ((1092, 1092), 39 * 39), ((28, 28), 1), ((29, 28), 2), ((4000, 3000), 4784),
    ((0, 100), 4784), ((-5, 10), 4784), (("x", 10), 4784), ((True, 10), 4784),
])
def test_r07b_image_bounds_per_provider(wh, expected):
    leaf = _leaf()
    assert _need(leaf, "OPENAI_IMAGE_PART_TOKEN_BOUND") == 85 + 170 * 8 == 1445
    assert _need(leaf, "ANTHROPIC_IMAGE_TOKEN_CAP") == 4784
    assert _need(leaf, "anthropic_image_token_bound")(*wh) == expected


@pytest.mark.parametrize("args,expected", [
    ((800, None), 800), ((None, 1200), 1200), ((None, None), 16384), ((True, None), 16384),
    ((0, None), 16384), (("800", None), 16384),
])
def test_r08_output_token_bound(args, expected):
    leaf = _leaf()
    assert _need(leaf, "output_token_bound")(*args) == expected


@pytest.mark.parametrize("case", ["mini", "gpt4o", "haiku_search", "openai_search", "unpriced"])
def test_r09_upper_bound_literals(case):
    leaf = _leaf()
    fn = _need(leaf, "upper_bound_usd")
    table = {
        "mini": (("openai", MINI, 4020, 800), 0.001083),
        "gpt4o": (("openai", GPT4O, 4020, 800), 0.01805),
        "haiku_search": (("anthropic", HAIKU, 1000, 500, 2), 0.02035),
        "openai_search": (("openai", MINI, 1000, 500, 1), None),
        "unpriced": (("openai", UNPRICED_OPENAI, 1000, 500), None),
    }
    args, expected = table[case]
    got = fn(*args)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize("args,expected", [
    (("openai", 4020, 800), lambda: _conservative_openai(4020, 800)),
    (("anthropic", 1000, 500, 2), lambda: _conservative_anthropic(1000, 500, 2)),
    (("anthropic", 1000, 500), lambda: _conservative_anthropic(1000, 500)),
    ((None, 1000, 500), lambda: _conservative_anthropic(1000, 500)),
    (("mistral", 1000, 500), lambda: _conservative_anthropic(1000, 500)),
])
def test_r09b_conservative_bound_per_provider(args, expected):
    """R-S04-3: OpenAI -> the gpt-4o rates, Anthropic and any other provider ->
    the Sonnet rates; never None, never zero."""
    leaf = _leaf()
    got = _need(leaf, "conservative_bound_usd")(*args)
    assert got == _approx(expected()) and got > 0


# ===========================================================================
# R10-R21: admit / record against the fakes
# ===========================================================================
@pytest.mark.parametrize("lane", LANES)
def test_r10_admit_headroom_one_get(monkeypatch, lane):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(seed={_key(lane): "0.10"}))
    assert _need(leaf, "admit")(lane, 0.1) is None
    assert [(c[0], c[1]) for c in _spend(fake)] == [("get", _key(lane))]
    assert _spend(fake, "eval") == []


@pytest.mark.parametrize("lane,stored,ub,refused", [
    ("search", "0.45", 0.10, True), ("escalation", "0.95", 0.10, True),
    ("offclock", "1.95", 0.10, True), ("live", "1.95", 0.10, False),
])
def test_r10b_per_lane_cap_inside_admit(monkeypatch, lane, stored, ub, refused):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key(lane): stored}))
    if refused:
        with pytest.raises(abs_mod.LLMUnavailableError):
            leaf.admit(lane, ub)
    else:
        assert leaf.admit(lane, ub) is None


def test_r11_admit_refuses_with_the_existing_class(monkeypatch, caplog):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.80"}))
    caplog.set_level("WARNING")
    with pytest.raises(abs_mod.LLMUnavailableError) as ei:
        leaf.admit("live", 0.30)
    assert type(ei.value) is abs_mod.LLMUnavailableError
    low = str(ei.value).lower()
    assert "429" not in low and "rate" not in low and "quota" not in low
    msgs = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[SPEND]")]
    assert msgs == ["[SPEND] lane=live cap reached (spent_cents=280 cap_cents=300 bound_cents=30)"
                    " -- dispatch refused"]
    assert len(_spend(fake)) == 1


def test_r12_strict_boundary(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.50"}))
    assert leaf.admit("live", 0.50) is None
    leaf._reset_spend_breaker_state()
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.51"}))
    with pytest.raises(abs_mod.LLMUnavailableError):
        leaf.admit("live", 0.50)


def test_r13_missing_key_is_zero(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash())
    assert leaf.admit("live", 2.99) is None
    leaf._reset_spend_breaker_state()
    with pytest.raises(abs_mod.LLMUnavailableError):
        leaf.admit("live", 3.01)


@pytest.mark.parametrize("lane", LANES)
def test_r14_record_one_lua_eval(monkeypatch, lane):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(eval_result="1.25"))
    script = _need(leaf, "RECORD_SCRIPT")
    assert "INCRBYFLOAT" in script and "EXPIREAT" in script
    assert _need(leaf, "record")(lane, 0.00027) is None
    evals = _spend(fake, "eval")
    assert len(_spend(fake)) == 1 and len(evals) == 1
    got_script, keys, args = evals[0][2]
    assert got_script == script
    assert keys == [_key(lane)]
    assert args == [_f10(0.00027), str(EXPIREAT)]
    snap = _need(leaf, "admin_snapshot")()
    assert snap[lane]["spent_usd"] == pytest.approx(1.25)


@pytest.mark.parametrize("value", [0, -1, None, float("nan"), float("inf"), "x", True])
def test_r15_record_ignores_invalid(monkeypatch, value):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash())
    assert _need(leaf, "record")("live", value) is None
    assert fake.calls == []


def test_r16_redis_py_eval_shape(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeRedisPy())
    leaf.record("live", 0.5)
    assert fake.positional == (leaf.RECORD_SCRIPT, 1, _key("live"), _f10(0.5), str(EXPIREAT))


def test_r17_fail_open_and_rate_limited_warning(monkeypatch, caplog):
    leaf = _leaf()
    clock = _freeze(monkeypatch, leaf, clock=Clock(0.0))
    caplog.set_level("WARNING")
    _install(monkeypatch, None)
    assert leaf.admit("live", 0.1) is None
    assert leaf.record("live", 0.1) is None
    assert asyncio.run(_need(leaf, "entry_refuses_async")("live")) is False
    unconf = [r.getMessage() for r in caplog.records if "fail-open" in r.getMessage()]
    assert unconf and unconf[0] == "[SPEND] breaker fail-open (RedisUnconfigured) -- admitting and not recording"
    leaf._reset_spend_breaker_state()
    caplog.clear()
    _install(monkeypatch, RaisingRedis())
    for t in (0.0, 59.0, 60.0):
        clock.t = t
        assert leaf.admit("live", 0.1) is None
    assert leaf.record("live", 0.1) is None
    msgs = [r.getMessage() for r in caplog.records if "fail-open" in r.getMessage()]
    assert msgs == ["[SPEND] breaker fail-open (ConnectionError) -- admitting and not recording"] * 2
    assert _sentinel_text() not in caplog.text


@pytest.mark.parametrize("value", ["abc", "nan", "inf", "-1"])
def test_r18_bad_stored_value_fails_open(monkeypatch, caplog, value):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): value}))
    caplog.set_level("WARNING")
    assert leaf.admit("live", 2.5) is None
    msgs = [r.getMessage() for r in caplog.records if "fail-open" in r.getMessage()]
    assert msgs == ["[SPEND] breaker fail-open (ValueError) -- admitting and not recording"]


def test_r19_unpriced_model_bounds_conservatively(monkeypatch, caplog):
    """R-S04-3 (B2): the admit side of an unpriced model uses the conservative
    per-provider bound (OpenAI: the gpt-4o rates), never a bare admit."""
    leaf = _leaf()
    clock = _freeze(monkeypatch, leaf, clock=Clock(0.0))
    _install(monkeypatch, FakeUpstash())
    caplog.set_level("WARNING")
    dispatch = _need(leaf, "admit_openai_dispatch")
    asyncio.run(dispatch(UNPRICED_OPENAI, _msg("x" * 4000), 800, None))
    clock.t = 10.0
    asyncio.run(dispatch(UNPRICED_OPENAI, _msg("x" * 4000), 800, None))
    warns = [r.getMessage() for r in caplog.records if "unpriced" in r.getMessage()]
    assert len(warns) == 1 and warns[0].startswith("[SPEND] lane=live upper bound unpriced"), warns
    leaf._reset_spend_breaker_state()
    seen = []

    async def _spy(lane, ub):
        seen.append((lane, ub))

    monkeypatch.setattr(leaf, "admit_async", _spy)
    asyncio.run(dispatch(UNPRICED_OPENAI, _msg("x" * 4000), 800, None))
    assert len(seen) == 1 and seen[0][0] == "live"
    assert seen[0][1] == _approx(_conservative_openai(4020, 800))


@pytest.mark.parametrize("bad", [None, float("nan"), -0.5, "x", True])
def test_r19b_admit_sanitises_its_bound(monkeypatch, bad):
    """R-S04-10: a non-number, NaN, negative or bool bound is the conservative
    bound: never a TypeError out of admit, never an admit at zero cost."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.999"}))
    with pytest.raises(abs_mod.LLMUnavailableError):
        leaf.admit("live", bad)
    leaf._reset_spend_breaker_state()
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "0"}))
    assert leaf.admit("live", bad) is None


def test_r20_cap_read_per_call(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.0"}))
    monkeypatch.setenv(CAP_ENV["live"], "1.0")
    with pytest.raises(abs_mod.LLMUnavailableError):
        leaf.admit("live", 0.1)
    monkeypatch.setenv(CAP_ENV["live"], "5.0")
    assert leaf.admit("live", 0.1) is None


def test_r21_day_roll_moves_the_key(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf, when=datetime(2026, 10, 22, 20, 59, 59, tzinfo=UTC))
    fake = _install(monkeypatch, FakeUpstash())
    leaf.admit("live", 0.1)
    monkeypatch.setattr(leaf, "_utcnow", lambda: datetime(2026, 10, 22, 21, 0, 0, tzinfo=UTC))
    leaf.admit("live", 0.1)
    assert [c[1] for c in _spend(fake, "get")] == [_key("live", "2026-10-22"), _key("live", "2026-10-23")]


# ===========================================================================
# R22: off the loop on the dedicated pool, bounded, durable records
# ===========================================================================
@pytest.mark.asyncio
async def test_r22_redis_runs_on_the_dedicated_pool_and_record_is_durable(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash())
    loop_ident = threading.get_ident()
    await _need(leaf, "admit_async")("live", 0.1)
    gets = _spend(fake, "get")
    assert len(gets) == 1 and gets[0][3] != loop_ident
    assert gets[0][4].startswith("llm-spend"), "the GET ran on %r, not the llm-spend pool" % gets[0][4]
    pool = _need(leaf, "_get_llm_spend_pool")()
    assert getattr(pool, "_max_workers", None) == 4
    task = _need(leaf, "record_soon")("live", 0.2)
    assert isinstance(task, asyncio.Task)
    assert task in async_utils._BACKGROUND_TASKS
    await task
    evals = _spend(fake, "eval")
    assert len(evals) == 1 and evals[0][3] != loop_ident and evals[0][4].startswith("llm-spend")
    assert leaf.record_soon("live", 0) is None


@pytest.mark.asyncio
async def test_r22b_a_stalled_read_fails_open_inside_the_bound(monkeypatch, caplog):
    """R-S04-2 (B1): a read slower than LLM_SPEND_REDIS_TIMEOUT_SECONDS admits
    (fail-open naming TimeoutError) instead of parking the dispatch."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "99.0"}))
    fake.block = threading.Event()
    caplog.set_level("WARNING")
    try:
        t0 = time.monotonic()
        assert await leaf.admit_async("live", 0.1) is None
        assert time.monotonic() - t0 < 3.0
        msgs = [r.getMessage() for r in caplog.records if "fail-open" in r.getMessage()]
        assert msgs == ["[SPEND] breaker fail-open (TimeoutError) -- admitting and not recording"]
        monkeypatch.setenv(TIMEOUT_ENV, "0.2")
        leaf._reset_spend_breaker_state()
        t0 = time.monotonic()
        assert await leaf.entry_refuses_async("live") is False
        assert time.monotonic() - t0 < 3.0
    finally:
        fake.block.set()


@pytest.mark.asyncio
async def test_r22c_no_client_short_circuits_before_any_hop(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, None)
    with _submit_spy() as seen:
        assert await leaf.admit_async("live", 0.1) is None
        assert await leaf.entry_refuses_async("live") is False
        assert leaf.record_soon("live", 0.2) is None
        await leaf.admit_openai_dispatch(MINI, _msg("x"), 10, None)
    assert seen == [], "a hop to an executor with no Redis client: %r" % seen


@pytest.mark.asyncio
@pytest.mark.parametrize("stored,reserve,refuses", [
    ("2.95", None, True), ("2.85", None, False), ("2.95", "0.01", False), ("3.00", None, True),
    ("2.50", "0.5", True), ("2.25", "0.5", False),
])
async def test_r23_entry_reserve_boundary(monkeypatch, caplog, stored, reserve, refuses):
    """R-S04-4: the entry refuses when spent + LLM_SPEND_ENTRY_RESERVE_USD >= cap."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): stored}))
    if reserve is not None:
        monkeypatch.setenv(RESERVE_ENV, reserve)
    caplog.set_level("WARNING")
    assert await _need(leaf, "entry_refuses_async")("live") is refuses
    gets = _spend(fake, "get")
    assert len(gets) == 1 and _spend(fake, "eval") == []
    assert gets[0][4].startswith("llm-spend")
    msgs = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[SPEND]")]
    if refuses:
        assert len(msgs) == 1
        assert msgs[0].startswith("[SPEND] lane=live cap reached (")
        assert "spent_cents=%d" % int(round(float(stored) * 100)) in msgs[0]
        assert "cap_cents=300" in msgs[0]
        assert msgs[0].endswith("-- short-circuiting the compare BEFORE the provider fan-out")
        assert "Acme" not in msgs[0]
    else:
        assert msgs == []


# ===========================================================================
# R24-R30: the guarded_llm_create chokepoint
# ===========================================================================
def _on(monkeypatch, w13=False):
    monkeypatch.setenv(FLAG, "true")
    if w13:
        monkeypatch.setenv(W13, "true")
    else:
        monkeypatch.delenv(W13, raising=False)


@pytest.mark.asyncio
async def test_r24_chokepoint_admit_dispatch_record_order(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    events, sent = [], []
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "0.5"}))
    fake.events = events
    client = _mock_openai_client(usage=_usage(1000, 200), events=events, sent=sent)
    ledger = openai_pricing.start_openai_ledger()
    kwargs = {"model": MINI, "messages": _msg("x" * 40), "max_tokens": 800}
    out = await abs_mod.guarded_llm_create(client, **dict(kwargs))
    await _drain_spend_tasks()
    assert events == ["get", "create", "eval"]
    assert client.chat.completions.create.await_count == 1
    assert sent == [dict(kwargs, store=False)]
    assert out is client._resp
    evals = _spend(fake, "eval")
    assert evals[0][2][2][0] == _f10(llm_pricing.openai_usage_cost_usd(MINI, _usage(1000, 200)))
    assert len(ledger) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("w13", [False, True])
async def test_r25_chokepoint_refusal_precedes_the_breaker(monkeypatch, w13):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch, w13=w13)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.99"}))
    client = _mock_openai_client(usage=_usage())
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_half_open_breaker_seed())
    spy = MagicMock(wraps=abs_mod._openai_dispatch_admission)
    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              patch.object(abs_mod, "_openai_dispatch_admission", spy)):
        with pytest.raises(abs_mod.LLMUnavailableError):
            await abs_mod.guarded_llm_create(client, model=GPT4O, messages=_msg("x" * 4000), max_tokens=800)
    assert client.chat.completions.create.await_count == 0
    assert _spend(fake, "eval") == []
    assert spy.call_count == 0
    assert ops["incr"] == 0, "the half-open probe was spent by a spend refusal"


@pytest.mark.asyncio
async def test_r26_both_flags_on_records_on_the_breaker_tail(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch, w13=True)
    events = []
    fake = _install(monkeypatch, FakeUpstash())
    fake.events = events
    client = _mock_openai_client(usage=_usage(), events=events)
    success = MagicMock()
    with _all(patch.object(abs_mod, "_openai_dispatch_admission", return_value=(True, True, False)),
              patch.object(abs_mod, "openai_record_success", success)):
        await abs_mod.guarded_llm_create(client, model=MINI, messages=_msg("x"), max_tokens=10)
        await _drain_spend_tasks()
    assert client.chat.completions.create.await_count == 1
    assert success.call_count == 1
    assert events == ["get", "create", "eval"]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_kind", ["rate_limit", "cancelled"])
async def test_r27_raising_or_cancelled_create_records_nothing(monkeypatch, exc_kind):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    exc = _rate_limit_error() if exc_kind == "rate_limit" else asyncio.CancelledError()
    failures = {}
    for spend_on in (False, True):
        if spend_on:
            monkeypatch.setenv(FLAG, "true")
        else:
            monkeypatch.delenv(FLAG, raising=False)
        monkeypatch.setenv(W13, "true")
        fake = _install(monkeypatch, FakeUpstash())
        client = _mock_openai_client(raises=exc)
        rec_fail = MagicMock()
        with _all(patch.object(abs_mod, "_openai_dispatch_admission", return_value=(True, True, False)),
                  patch.object(abs_mod, "openai_record_failure", rec_fail)):
            with pytest.raises(BaseException) as ei:
                await abs_mod.guarded_llm_create(client, model=MINI, messages=_msg("x"), max_tokens=10)
            await _drain_spend_tasks()
        assert ei.value is exc
        assert _spend(fake, "eval") == []
        failures[spend_on] = rec_fail.call_count
    assert failures[True] == failures[False]
    _ = leaf


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["text", "image", "completion_tokens", "response_format"])
async def test_r28_chokepoint_bound_from_kwargs(monkeypatch, case):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    seen = []

    async def _spy(lane, ub):
        seen.append((lane, ub))

    monkeypatch.setattr(leaf, "admit_async", _spy)
    _install(monkeypatch, FakeUpstash())
    client = _mock_openai_client(usage=None)
    mini = _openai_rate(MINI)
    table = {
        "text": (dict(messages=_msg("x" * 4000), max_tokens=800), 4020, 800),
        "image": (dict(messages=_image_msg(1000000), max_tokens=500), 16 + 4 + 100 + 1445, 500),
        "completion_tokens": (dict(messages=_msg("x" * 4000), max_completion_tokens=1200), 4020, 1200),
        "response_format": (dict(messages=_msg("x" * 100), max_tokens=300, response_format=_RF),
                            16 + 4 + 100 + len(json.dumps(_RF, default=str).encode("utf-8")), 300),
    }
    kw, prompt, out = table[case]
    await abs_mod.guarded_llm_create(client, model=MINI, **kw)
    expected = (prompt * mini["input"] + out * mini["output"]) / 1e6
    assert seen == [("live", _approx(expected))]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,lane", [("offclock", "offclock"), ("garbage", "live")])
async def test_r28b_chokepoint_lane_knob(monkeypatch, raw, lane):
    """R-S04-6: LLM_SPEND_CHOKEPOINT_LANE picks the chokepoint lane per process."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    monkeypatch.setenv(LANE_ENV, raw)
    fake = _install(monkeypatch, FakeUpstash())
    client = _mock_openai_client(usage=_usage())
    await abs_mod.guarded_llm_create(client, model=MINI, messages=_msg("x"), max_tokens=10)
    await _drain_spend_tasks()
    assert [c[1] for c in _spend(fake)] == [_key(lane), _key(lane)]
    assert [c[0] for c in _spend(fake)] == ["get", "eval"]


@pytest.mark.asyncio
async def test_r29_unpriced_model_records_the_admitted_bound(monkeypatch):
    """R-S04-3 (B2): an unpriced served call records the ADMITTED upper bound,
    never the base mini-rate estimate."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "1.0"}))
    client = _mock_openai_client(usage=_usage(1000, 200))
    await abs_mod.guarded_llm_create(client, model=UNPRICED_OPENAI, messages=_msg("x" * 4000), max_tokens=800)
    await _drain_spend_tasks()
    evals = _spend(fake, "eval")
    assert len(evals) == 1
    assert evals[0][2][2][0] == _f10(_conservative_openai(4020, 800))
    assert evals[0][2][2][0] != _f10(llm_pricing.openai_usage_cost_usd(UNPRICED_OPENAI, _usage(1000, 200)))


def test_r29b_record_of_an_unpriced_actual_uses_the_admitted_bound(monkeypatch):
    """R-S04-3 contract for S81-06 / S81-16 / S81-21 / S81-22 (Anthropic-shaped):
    an unpriced actual records the admitted bound, a positive INCRBYFLOAT."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash())
    ub = leaf.conservative_bound_usd("anthropic", 1000, 500)
    assert leaf.admit("live", ub) is None
    leaf.record("live", llm_pricing.price_call("anthropic", UNPRICED_ANTHROPIC,
                                                input_tokens=1000, output_tokens=500), admitted_usd=ub)
    evals = _spend(fake, "eval")
    assert len(evals) == 1 and evals[0][2][2][0] == _f10(_conservative_anthropic(1000, 500))
    assert float(evals[0][2][2][0]) > 0


@pytest.mark.asyncio
async def test_r30_response_without_usage_records_the_admitted_bound(monkeypatch):
    """Gate GC-4 (amends R30; R-S04-3 "never zero"): a SERVED response with no
    usage (the stream shape) records the ADMITTED bound, one EVAL."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    fake = _install(monkeypatch, FakeUpstash())
    client = _mock_openai_client(usage=None)
    await abs_mod.guarded_llm_create(client, model=MINI, messages=_msg("x"), max_tokens=10)
    await _drain_spend_tasks()
    assert client.chat.completions.create.await_count == 1
    evals = _spend(fake, "eval")
    admitted = llm_pricing.price_call("openai", MINI, input_tokens=16 + 4 + 1, output_tokens=10)
    assert len(evals) == 1 and evals[0][2][2][0] == _f10(admitted)
    assert float(evals[0][2][2][0]) > 0


# ===========================================================================
# R31-R32: the compare entries (REST + SSE), orchestrator and route level
# ===========================================================================
@pytest.mark.asyncio
async def test_r31_rest_entry_short_circuits_before_fanout(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    _arm_prod_search_config(monkeypatch)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.95"}))
    fan = _FanOutCounters()
    client = _mock_openai_client(usage=_usage())
    with _all(*fan.patches(client)):
        result = await _run_compare()
    assert fan.calls == {"search_web": 0, "bd_search_web": 0, "firecrawl": 0}
    assert client.chat.completions.create.await_count == 0
    assert result.get("success") is False
    assert result.get("code") == "LLM_UNAVAILABLE"
    assert result.get("error") == scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE
    assert len(_spend(fake, "get")) == 1 and _spend(fake, "eval") == []


@pytest.mark.asyncio
async def test_r31b_rest_entry_admits_below_the_reserve(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.85"}))
    impl = AsyncMock(return_value={"success": True, "probe": "impl"})
    with patch.object(scs.StructuredComparisonService, "_compare_from_text_impl", impl):
        result = await _run_compare()
    assert impl.await_count == 1
    assert result == {"success": True, "probe": "impl"}
    assert len(_spend(fake, "get")) == 1


@pytest.mark.asyncio
async def test_r32_stream_entry_short_circuits_before_fanout(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    _arm_prod_search_config(monkeypatch)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.95"}))
    fan = _FanOutCounters()
    client = _mock_openai_client(usage=_usage())
    with _all(*fan.patches(client)):
        events = await _run_stream()
    assert fan.calls == {"search_web": 0, "bd_search_web": 0, "firecrawl": 0}
    assert [e for e, _ in events] == ["error"]
    body = events[0][1]
    assert body.get("success") is False and body.get("code") == "LLM_UNAVAILABLE"
    assert body.get("error") == scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE


@pytest.mark.asyncio
async def test_r32b_stream_entry_admits_below_the_reserve(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.85"}))
    l1_calls = []
    with _all(*_stub_l1(l1_calls)):
        events = await _run_stream()
    assert len(l1_calls) == 1, "the stream did not proceed past the entry"
    assert events and events[0][1].get("code") != "LLM_UNAVAILABLE"
    assert len(_spend(fake, "get")) == 1


class _Count:
    def __init__(self):
        self.n = 0

    def __call__(self, *a, **k):
        self.n += 1

        async def _done():
            return None
        return _done()


def _wire_route(monkeypatch):
    refund, save, lifetime = _Count(), _Count(), _Count()

    async def _prefs(uid):
        return {"success": True, "preferences_completed": False, "preferences": {}}

    async def _consume(uid, tok):
        return {"allowed": True, "reason": "daily", "tier": "free", "consumed": True,
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 0}}

    async def _log(*a, **k):
        return None

    monkeypatch.setattr(tr, "get_user_preferences", _prefs)
    monkeypatch.setattr(tr, "consume_comparison_credit", _consume)
    monkeypatch.setattr(tr, "refund_comparison_credit", refund)
    monkeypatch.setattr(tr, "record_lifetime_comparison", lifetime)
    monkeypatch.setattr(tr, "save_comparison_and_track_cohort", save)
    monkeypatch.setattr(tr, "log_search", _log)
    monkeypatch.setattr(limiter, "enabled", False)
    user = {"id": "s04-user", "email": "s04@example.test", "access_token": "s04-tok"}
    app.dependency_overrides[auth_routes.get_optional_user] = lambda: user
    return refund, save, lifetime


def _code_of(body):
    if not isinstance(body, dict):
        return None
    if body.get("code"):
        return body.get("code")
    detail = body.get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


@pytest.mark.parametrize("surface", ["rest", "sse"])
def test_r32c_route_refusal_is_a_refunded_non_delivery(monkeypatch, surface):
    """R-S04-4 + R-A3: the refusal travels through the existing LLM_UNAVAILABLE
    non-delivery: coded 503 / one error event, refund once, no history row, no
    lifetime bump."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "3.00"}))
    saved = dict(app.dependency_overrides)
    try:
        refund, save, lifetime = _wire_route(monkeypatch)
        client = TestClient(app, raise_server_exceptions=False)
        if surface == "rest":
            r = client.post("/api/v1/text/compare", json={"query": "Acme Widget vs Globex Gadget"})
            assert r.status_code == 503
            assert _code_of(r.json()) == "LLM_UNAVAILABLE"
        else:
            r = client.get("/api/v1/text/compare/stream", params={"q": "Acme Widget vs Globex Gadget"})
            text = r.text
            assert "LLM_UNAVAILABLE" in text and "event: error" in text
        assert refund.n == 1
        assert save.n == 0 and lifetime.n == 0
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


# ===========================================================================
# R33-R36: /health (exhausted + day + fail-open counter only) and the admin view
# ===========================================================================
def _health():
    return TestClient(app).get("/health").json()


def test_r33_health_object_after_admit(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "1.25"}))
    leaf.admit("live", 0.1)
    before = len(fake.calls)
    body = _health()
    assert len(fake.calls) == before, "/health issued a Redis command"
    assert body["llm_spend"] == {"live": {"exhausted": False, "day": DAY}}
    assert body["llm_spend_fail_open"] == 0
    assert set(body) - {"llm_spend", "llm_spend_fail_open"} <= BASE_HEALTH_KEYS
    assert body["status"] == "healthy" and body["message"] == "MYEZ API is running"
    raw = json.dumps(body)
    assert "spent_usd" not in raw and "cap_usd" not in raw, "amounts on the public /health"


def test_r34_health_exhausted_is_computed_per_call(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(eval_result="2.5"))
    monkeypatch.setenv(CAP_ENV["offclock"], "4")
    leaf.record("offclock", 0.5)
    assert _health()["llm_spend"] == {"offclock": {"exhausted": False, "day": DAY}}
    monkeypatch.setenv(CAP_ENV["offclock"], "2")
    assert _health()["llm_spend"] == {"offclock": {"exhausted": True, "day": DAY}}


def test_r34b_health_fail_open_counter(monkeypatch):
    """Q4 / R-S04-7: a pure fail-open process shows the counter on /health."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, None)
    leaf.admit("live", 0.1)
    body = _health()
    assert body["llm_spend_fail_open"] == 1 and body["llm_spend"] == {}
    leaf.admit("live", 0.1)
    assert _health()["llm_spend_fail_open"] == 2


def test_r35_health_survives_a_raising_snapshot(monkeypatch):
    leaf = _leaf()
    _need(main_mod, "llm_spend_health_snapshot")
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "1.0"}))
    leaf.admit("live", 0.1)
    assert "llm_spend" in _health(), "the breaker ran, so /health shows the key"

    def _boom():
        raise RuntimeError("probe")

    monkeypatch.setattr(leaf, "spend_snapshot", _boom)
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert "llm_spend" not in r.json() and "llm_spend_fail_open" not in r.json()


def test_r36_health_wiring_static():
    _need(main_mod, "llm_spend_health_snapshot")
    assert "llm_spend_health_snapshot()" in inspect.getsource(main_mod.health_check)


ADMIN_KEY = "s04-" + "admin-key"


def _get_admin_costs(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
    monkeypatch.setattr(limiter, "enabled", False)
    from app.api import admin_routes
    with _all(
        patch.object(admin_routes, "get_usage_summary", return_value={"providers": {}, "circuit_breakers": {}}),
        patch.object(admin_routes, "get_tier15_hit_rate", return_value={}),
        patch.object(admin_routes, "get_tier15_source_hits", return_value={}),
        patch.object(admin_routes, "get_burn_status", return_value={
            "used": 0, "limit": 2200, "threshold": 1760, "fraction": 0.0, "over_threshold": False}),
        patch.object(admin_routes, "get_supabase_client", side_effect=RuntimeError("no db")),
    ):
        return TestClient(app).get("/api/v1/admin/costs", headers={"X-Admin-Key": ADMIN_KEY})


def test_r36b_admin_costs_carries_the_amounts(monkeypatch):
    """R-S04-7: the amounts live on the X-Admin-Key surface, written only ON."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "1.25"}))
    leaf.admit("live", 0.1)
    r = _get_admin_costs(monkeypatch)
    assert r.status_code == 200
    block = r.json()["spend_breaker"]
    assert set(block) == {"live"}
    row = block["live"]
    assert row["spent_usd"] == pytest.approx(1.25) and row["cap_usd"] == 3.0 and row["day"] == DAY
    assert isinstance(row["memo_age_seconds"], (int, float)) and row["memo_age_seconds"] >= 0


# ===========================================================================
# R37-R38 + R43: static wiring, the CLAUDE.md row, the FY25 clear-list
# ===========================================================================
def _fn_node(path, name):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return tree, node
    raise AssertionError("%s not found in %s" % (name, path))


def _is_attr_call(node, attr):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "_llm_spend_breaker")


def _kwargs_get_names(call):
    names = []
    for a in list(call.args) + [k.value for k in call.keywords]:
        assert (isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and a.func.attr == "get"
                and isinstance(a.func.value, ast.Name) and a.func.value.id == "kwargs"), (
            "admit_openai_dispatch argument is not a kwargs.get(...) call")
        names.append(a.args[0].value)
    return names


def test_r37_chokepoint_and_entry_wiring_static():
    abs_path = ROOT / "app" / "services" / "api_budget_service.py"
    tree, fn = _fn_node(abs_path, "guarded_llm_create")
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "app.services"
               and any(a.name == "llm_spend_breaker" and a.asname == "_llm_spend_breaker" for a in n.names)]
    assert imports, "api_budget_service does not import llm_spend_breaker as _llm_spend_breaker"
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
    assert sum(_is_attr_call(c, "spend_breaker_enabled") for c in calls) == 1
    admits = [c for c in calls if _is_attr_call(c, "admit_openai_dispatch")]
    assert len(admits) == 1
    assert {"model", "messages", "max_tokens", "max_completion_tokens", "response_format",
            "tools"} <= set(_kwargs_get_names(admits[0]))
    assert sum(_is_attr_call(c, "record_openai_response_soon") for c in calls) == 2

    def _index(pred):
        for i, stmt in enumerate(fn.body):
            if any(pred(n) for n in ast.walk(stmt)):
                return i
        return None

    i_admit = _index(lambda n: _is_attr_call(n, "admit_openai_dispatch"))
    i_w13 = _index(lambda n: isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "_openai_dispatch_admission")
    assert i_admit is not None and i_w13 is not None and i_admit < i_w13
    scs_path = ROOT / "app" / "services" / "structured_comparison_service.py"
    stree = ast.parse(scs_path.read_text(encoding="utf-8"))
    entries = [n for n in ast.walk(stree) if _is_attr_call(n, "entry_refuses_async")]
    assert len(entries) == 2
    bools = [n for n in ast.walk(stree) if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.And)]
    guarded = 0
    for b in bools:
        if _is_attr_call(b.values[0], "spend_breaker_enabled") and any(
                any(_is_attr_call(x, "entry_refuses_async") for x in ast.walk(v)) for v in b.values[1:]):
            guarded += 1
    assert guarded == 2, "each entry check must be `spend_breaker_enabled() and await entry_refuses_async(...)`"


def test_r38_claude_md_row():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.find("`ENABLE_LLM_SPEND_BREAKER` (S81-04")
    assert start >= 0, "CLAUDE.md has no S81-04 flag row"
    end = text.find("\n**SESSION", start)
    row = text[start:end if end > 0 else len(text)]
    for token in list(CAP_ENV.values()) + [MEMO_ENV, TIMEOUT_ENV, RESERVE_ENV, LANE_ENV,
                                           "llm_spend:<lane>:", "/health", "llm_spend_fail_open",
                                           "spend_breaker", "S81-09", "S81-24"]:
        assert token in row, "the S81-04 row lacks %r" % token
    low = row.lower()
    assert "fail-open" in low and "last-resort" in low


def test_r43_fy25_unit_env_names_the_flag():
    tree = ast.parse((ROOT / "tests" / "test_s75_fanout_identity.py").read_text(encoding="utf-8"))
    names = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "UNIT_ENV"
                                                 for t in node.targets):
            names = [e.value for e in node.value.elts]
    assert names is not None and FLAG in names, "FY25 UNIT_ENV does not clear ENABLE_LLM_SPEND_BREAKER (E2)"


# ===========================================================================
# R39-R42: the memo (R-S04-1), reserve / settle (R-S04-5), ON accounting
# ===========================================================================
def test_r39_memo_fresh_stale_and_knob(monkeypatch):
    leaf = _leaf()
    clock = _freeze(monkeypatch, leaf, clock=Clock(0.0))
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "0.10"}))
    leaf.admit("live", 0.1)
    clock.t = 1.0
    leaf.admit("live", 0.1)
    assert len(_spend(fake, "get")) == 1, "a fresh memo re-read Upstash"
    clock.t = 6.0
    leaf.admit("live", 0.1)
    assert len(_spend(fake, "get")) == 2, "a stale memo was not re-read"
    monkeypatch.setenv(MEMO_ENV, "10")
    clock.t = 12.0
    leaf.admit("live", 0.1)
    assert len(_spend(fake, "get")) == 2, "LLM_SPEND_MEMO_SECONDS not read per call"


@pytest.mark.asyncio
async def test_r39b_memo_counts_the_local_delta_at_once(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf, clock=Clock(0.0))
    fake = _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.80"}))
    leaf.admit("live", 0.05)
    task = leaf.record_soon("live", 0.15)
    with pytest.raises(abs_mod.LLMUnavailableError):
        leaf.admit("live", 0.10)
    assert len(_spend(fake, "get")) == 1
    await task


def test_r40_two_parallel_reserves_admit_exactly_one(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash())
    reserve = _need(leaf, "reserve")
    barrier = threading.Barrier(2)
    outcomes = []

    def _one():
        barrier.wait(5.0)
        try:
            reserve("offclock", 1.5)
            outcomes.append("admitted")
        except abs_mod.LLMUnavailableError:
            outcomes.append("refused")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(lambda _: _one(), range(2)))
    assert sorted(outcomes) == ["admitted", "refused"]
    assert float(fake.store[_key("offclock")]) == pytest.approx(1.5)
    evals = _spend(fake, "eval")
    assert len(evals) == 2 and all(e[2][0] != leaf.RECORD_SCRIPT for e in evals)
    script, keys, args = evals[0][2]
    assert script == _need(leaf, "RESERVE_SCRIPT")
    assert "INCRBYFLOAT" in script and "EXPIREAT" in script and "GET" in script
    assert keys == [_key("offclock")] and args == [_f10(1.5), _f10(2.0), str(EXPIREAT)]


def test_r40b_settle_adjusts_by_actual_minus_bound(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    fake = _install(monkeypatch, FakeUpstash(seed={_key("offclock"): "1.5"}))
    settle = _need(leaf, "settle")
    settle("offclock", 1.5, 1.2)
    evals = _spend(fake, "eval")
    assert len(evals) == 1 and evals[0][2][0] == leaf.RECORD_SCRIPT
    assert evals[0][2][2] == [_f10(1.2 - 1.5), str(EXPIREAT)]
    settle("offclock", 1.5, None)
    settle("offclock", 1.5, 1.5)
    assert len(_spend(fake, "eval")) == 1, "an unpriced or exact settle must issue no command"


def test_r40c_reserve_fails_open(monkeypatch):
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, RaisingRedis())
    assert _need(leaf, "reserve")("offclock", 1.5) is None
    _install(monkeypatch, None)
    assert leaf.reserve("offclock", 1.5) is None


def _compare_harness(monkeypatch, fake, sent):
    _arm_prod_search_config(monkeypatch)
    _install(monkeypatch, fake)
    fan = _FanOutCounters()
    client = _mock_openai_client(usage=_usage(100, 20), sent=sent)
    return fan, client


@pytest.mark.asyncio
async def test_r42_on_with_headroom_accounts_every_create(monkeypatch):
    """P08's accounting half (RED): N creates through the real chokepoint ->
    N records (EVALs) and at most N + 1 reads (the entry + the admits; memo hits
    read nothing)."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    _on(monkeypatch)
    sent = []
    fake = FakeUpstash()
    fan, client = _compare_harness(monkeypatch, fake, sent)
    with _all(*fan.patches(client)):
        await _run_compare()
        await _drain_spend_tasks()
    n = client.chat.completions.create.await_count
    assert n > 0
    assert len(_spend(fake, "eval")) == n
    assert 1 <= len(_spend(fake, "get")) <= n + 1


# ===========================================================================
# R44-R46: the gate-named rows (GATE_S81_04 GC-9, GC-3, GC-6), added by GREEN
# ===========================================================================
def test_r44_gc9_lua_scripts_pinned():
    """GC-9: the RECORD and RESERVE Lua texts are pinned as compact literals
    (RECORD ARGV = [delta, expireat]; RESERVE ARGV = [upper_bound, cap,
    expireat]); the fakes above accept only these texts. Red at base (no leaf)."""
    leaf = _leaf()
    assert _need(leaf, "RECORD_SCRIPT") == RECORD_SCRIPT_PIN
    assert _need(leaf, "RESERVE_SCRIPT") == RESERVE_SCRIPT_PIN


def test_r45_gc3_fallback_bound_at_the_named_constant(monkeypatch):
    """GC-3: the fallback for a garbage or missing max_tokens / admitted bound is
    the conservative per-provider rate at LLM_SPEND_FALLBACK_OUTPUT_TOKENS =
    16384 output tokens (the 4o rates for OpenAI, the Sonnet 5.5 rates for
    Anthropic and an unknown provider); admit (no provider) uses the unknown
    branch."""
    leaf = _leaf()
    assert _need(leaf, "LLM_SPEND_FALLBACK_OUTPUT_TOKENS") == 16384
    assert leaf.output_token_bound(None, None) == leaf.LLM_SPEND_FALLBACK_OUTPUT_TOKENS
    fallback = _need(leaf, "fallback_bound_usd")
    openai_ref = llm_pricing.price_call("openai", GPT4O, input_tokens=0, output_tokens=16384)
    sonnet_ref = llm_pricing.price_call("anthropic", SONNET, input_tokens=0, output_tokens=16384)
    assert fallback("openai") == _approx(openai_ref)
    assert fallback("anthropic") == _approx(sonnet_ref)
    assert fallback(None) == _approx(sonnet_ref)
    _freeze(monkeypatch, leaf)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.83"}))
    assert leaf.admit("live", None) is None
    leaf._reset_spend_breaker_state()
    _install(monkeypatch, FakeUpstash(seed={_key("live"): "2.84"}))
    with pytest.raises(abs_mod.LLMUnavailableError):
        leaf.admit("live", None)


@pytest.mark.parametrize("reserve,stored,exhausted", [
    (None, "2.90", True), (None, "2.89", False), ("0.5", "2.50", True), ("0.5", "2.49", False),
])
def test_r46_gc6_one_exhausted_predicate_at_the_boundary(monkeypatch, reserve, stored, exhausted):
    """GC-6: ONE predicate, spent + LLM_SPEND_ENTRY_RESERVE_USD >= cap, used by the
    entry check AND the /health snapshot: spent = cap - reserve exactly is
    exhausted, 0.01 below is not."""
    leaf = _leaf()
    _freeze(monkeypatch, leaf)
    if reserve is not None:
        monkeypatch.setenv(RESERVE_ENV, reserve)
    _install(monkeypatch, FakeUpstash(seed={_key("live"): stored}))
    assert _need(leaf, "lane_exhausted")("live", float(stored)) is exhausted
    assert asyncio.run(leaf.entry_refuses_async("live")) is exhausted
    assert _health()["llm_spend"] == {"live": {"exhausted": exhausted, "day": DAY}}


# ===========================================================================
# PIN rows: flag OFF identity under the FULL configuration (ruling B1)
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "false", "0", "off", "", " FALSE ", "no", "garbage"])
async def test_p01_flag_off_chokepoint_identity(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    monkeypatch.delenv(W13, raising=False)
    fake = _full_config(monkeypatch)
    sent = []
    client = _mock_openai_client(usage=_usage(1000, 200), sent=sent)
    ledger = openai_pricing.start_openai_ledger()
    ff_calls, to_thread_calls = [], []
    orig_ff = async_utils.fire_and_forget
    orig_to_thread = asyncio.to_thread

    def _ff(coro, label):
        ff_calls.append(label)
        return orig_ff(coro, label)

    async def _tt(fn, *a, **k):
        to_thread_calls.append(getattr(fn, "__name__", "?"))
        return await orig_to_thread(fn, *a, **k)

    monkeypatch.setattr(async_utils, "fire_and_forget", _ff)
    monkeypatch.setattr(asyncio, "to_thread", _tt)
    kwargs = {"model": MINI, "messages": _msg("x" * 40), "max_tokens": 800,
              "response_format": {"type": "json_object"}}
    with _submit_spy() as submits:
        out = await abs_mod.guarded_llm_create(client, **dict(kwargs))
    assert sent == [dict(kwargs, store=False)]
    assert out is client._resp
    assert fake.calls == []
    assert submits == [] and ff_calls == [] and to_thread_calls == []
    assert ledger == [BASE_LEDGER_ENTRY]


@pytest.mark.asyncio
async def test_p02_flag_off_with_w13_on_touches_no_spend_key(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.setenv(W13, "true")
    fake = _full_config(monkeypatch)
    client = _mock_openai_client(usage=_usage())
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        await abs_mod.guarded_llm_create(client, model=MINI, messages=_msg("x"), max_tokens=10)
    assert client.chat.completions.create.await_count == 1
    assert _spend(fake) == []


@pytest.mark.asyncio
async def test_p03_flag_off_rest_entry_ignores_an_exhausted_lane(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    fake = _full_config(monkeypatch)
    impl = AsyncMock(return_value={"success": True, "probe": "impl"})
    with _submit_spy() as submits:
        with patch.object(scs.StructuredComparisonService, "_compare_from_text_impl", impl):
            result = await _run_compare()
    assert impl.await_count == 1 and result == {"success": True, "probe": "impl"}
    assert _spend(fake) == [] and submits == []


@pytest.mark.asyncio
async def test_p04_flag_off_stream_entry_ignores_an_exhausted_lane(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    fake = _full_config(monkeypatch)
    l1_calls = []
    with _all(*_stub_l1(l1_calls)):
        events = await _run_stream()
    assert len(l1_calls) == 1
    assert events and events[0][1].get("code") != "LLM_UNAVAILABLE"
    assert _spend(fake) == []


def test_p05_flag_off_health_has_no_spend_key(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    _full_config(monkeypatch)
    client = _mock_openai_client(usage=_usage())
    asyncio.run(abs_mod.guarded_llm_create(client, model=MINI, messages=_msg("x"), max_tokens=10))
    body = _health()
    assert "llm_spend" not in body and "llm_spend_fail_open" not in body
    assert set(body) <= BASE_HEALTH_KEYS
    assert body["status"] == "healthy" and body["message"] == "MYEZ API is running"


def test_p06_provider_configs_unchanged():
    assert set(abs_mod.PROVIDER_CONFIGS) == {"firecrawl", "scrapedo", "brightdata", "serper", "openai", "youtube"}
    assert not any("llm" in k for k in abs_mod.PROVIDER_CONFIGS)
    with patch.object(cache_service, "redis_client", None):
        summary = abs_mod.get_usage_summary()
    assert "spend_breaker" not in summary and "llm_spend" not in summary


def test_p07_no_new_credential_names():
    from tests import _env_safety
    for attr in ("CREDENTIALS_UNSET", "CREDENTIAL_PLACEHOLDERS"):
        names = getattr(_env_safety, attr, ())
        names = list(names.keys()) if isinstance(names, dict) else list(names)
        assert not any(str(n).startswith("LLM_SPEND") or n == FLAG for n in names)


@pytest.mark.asyncio
async def test_p08_on_with_headroom_changes_no_response_field(monkeypatch):
    """R-S04-10 (P08, replaces the FY25-ON sentence): the real chokepoint driven
    by the W1-3 compare harness, flag OFF then ON with headroom: field-equal
    bodies minus the volatile set, equal create kwargs and counts."""
    runs = {}
    for on in (False, True):
        if on:
            monkeypatch.setenv(FLAG, "true")
        else:
            monkeypatch.delenv(FLAG, raising=False)
        leaf = _leaf_or_none()
        if leaf is not None:
            leaf._reset_spend_breaker_state()
        sent = []
        fan, client = _compare_harness(monkeypatch, FakeUpstash(), sent)
        with _all(*fan.patches(client)):
            result = await _run_compare()
            await _drain_spend_tasks()
        runs[on] = (_strip(copy.deepcopy(result)), sorted(_kw_key(k) for k in sent),
                    client.chat.completions.create.await_count, dict(fan.calls))
    off, on_ = runs[False], runs[True]
    assert off[2] > 0, "the harness made no create: the identity proves nothing"
    assert on_[2] == off[2]
    assert on_[1] == off[1]
    assert on_[3] == off[3]
    assert on_[0] == off[0]


def test_p09_flag_off_admin_costs_has_no_spend_block(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    _full_config(monkeypatch)
    r = _get_admin_costs(monkeypatch)
    assert r.status_code == 200
    assert "spend_breaker" not in r.json()

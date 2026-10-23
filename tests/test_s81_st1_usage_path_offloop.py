"""S81 ST1 LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP): the usage reads and the reviews
L1 calls off the event loop (RED + PIN rows).

Spec: .qa-s80/ST1_UNIT_SPEC.md (base 95cf6f86, sha e4830eb3) as amended by the
adversarial review .qa-s80/ST1_SPEC_REVIEW.md and the BINDING orchestrator rulings
RULINGS_ST1.md (session-81 state folder). Where they differ the rulings win:

- R-ST1-1: the Supabase half goes through the EXISTING run_db (it honours
  ENABLE_SYNC_DB_OFFLOAD); no run_db_offloop. With ST1 ON and sync offload OFF only
  the two Upstash GETs leave the loop.
- R-ST1-2: no blocking twins. The ON path gathers the existing async helpers
  _get_user_tier_info / _get_active_referral_bonus with two
  run_redis_offloop_pool(_get_redis_count, key) jobs (keys computed on the loop).
- R-ST1-3: one compute body (_usage_status_body / _usage_allowed_body) called by
  both flag states; flag-OFF identity is pinned by behaviour (base literals in base
  key order, the base op sequence and thread placement, the W4-13 ledger).
- R-ST1-4: the reviews post-extraction L1 write and the two re-cache writes are
  DURABLE, NON-AWAITED pool writes on a deepcopy snapshot, chained per cache_key
  inside a request; the L2 save is scheduled first; the L2-promotion write stays
  inline (RO17).
- R-ST1-6: one hermetic 16-thread concurrency PIN of the admin client through run_db.

Row ids follow the spec table where the row survived the rulings (R1-R30), plus
R31 (probe-D saturation), R32 (snapshot), R33 (concurrency), R34 (W4-13 ledger),
R35 (one compute body). RED rows fail at base on an AssertionError ONLY: missing
symbols are read through _require(); every patch of a new symbol uses
raising=False. PIN rows pass at base and run with the FULL configuration
(REDIS_OFFLOOP_MAX_WORKERS=4, the other offload flags parametrized) and call /
thread recorders (ruling B1).

Hermetic: every client is a fake (no network; the conftest netguard is active and
R33 talks only to a loopback stub), no credential value, synthetic ids only.
"""
from __future__ import annotations

import ast
import asyncio
import collections
import concurrent.futures
import contextvars
import copy
import hashlib
import importlib
import inspect
import json
import logging
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.product_data_service as pds
from app.services import review_service as rs
from app.services import usage_service as us
from app.utils import db_offload as dbo
from app.utils import redis_offloop as ro

FLAG = "ENABLE_USAGE_PATH_OFFLOOP"
SYNC = "ENABLE_SYNC_DB_OFFLOAD"
S77 = "ENABLE_PRICE_PATH_REDIS_OFFLOOP"
ASYNC_R = "ENABLE_ASYNC_REDIS_OFFLOAD"
KNOB = "REDIS_OFFLOOP_MAX_WORKERS"
PREFIX = "redis-offloop"
UID = "u-synthetic-1"
TTL = 7 * 24 * 60 * 60
TAG = "[USAGE-OFFLOOP]"

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "app"

CLEAN_ENV = (
    FLAG, SYNC, ASYNC_R, S77, KNOB,
    "ENABLE_SUPABASE_CLIENT_REUSE", "ENABLE_REVIEW_SOURCE_CONSULT",
    "ENABLE_UNIFIED_SEARCH_BOUND", "ENABLE_YOUTUBE_SOURCE",
)

# Rotating spellings of OFF for the flag-OFF PIN rows (None = unset).
OFF_SPELLINGS = (None, "false", "0", "off", "", "no", "garbage")

# The real counter read, captured at import (the per-test wrapper delegates here).
_REAL_COUNT = us._get_redis_count

_ST1_CV: contextvars.ContextVar = contextvars.ContextVar("st1_usage_offloop_cv", default="unset")


# ---------------------------------------------------------------------------
# Fixtures and small helpers
# ---------------------------------------------------------------------------


def _drop_offloop_pools():
    """Drop any lazily built redis-offloop pool by type + thread-name prefix (the
    S77 idiom), so no pool leaks into a later node or its /health."""
    for name, value in list(vars(ro).items()):
        if isinstance(value, concurrent.futures.ThreadPoolExecutor) and str(
            getattr(value, "_thread_name_prefix", "")
        ).startswith(PREFIX):
            value.shutdown(wait=False, cancel_futures=True)
            setattr(ro, name, None)


@pytest.fixture(autouse=True)
def _st1_env(monkeypatch):
    for name in CLEAN_ENV:
        monkeypatch.delenv(name, raising=False)
    _drop_offloop_pools()
    yield
    _drop_offloop_pools()


def _require(mod, name):
    obj = getattr(mod, name, None)
    assert obj is not None, f"ST1 not implemented: {mod.__name__}.{name}"
    return obj


def _set(monkeypatch, name, on):
    if on:
        monkeypatch.setenv(name, "true")
    else:
        monkeypatch.delenv(name, raising=False)


def _set_off_spelling(monkeypatch, idx):
    raw = OFF_SPELLINGS[idx % len(OFF_SPELLINGS)]
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)


def _full_config(monkeypatch, *, sync=False, s77=False, async_r=False):
    """The B1-rule configuration: the pool knob set and the other offload flags in
    the requested combination."""
    monkeypatch.setenv(KNOB, "4")
    _set(monkeypatch, SYNC, sync)
    _set(monkeypatch, S77, s77)
    _set(monkeypatch, ASYNC_R, async_r)


def _cls(thread, main):
    if thread is main:
        return "main"
    if thread.name.startswith(PREFIX):
        return "pool"
    return "worker"


def _dumps(obj):
    """Insertion-order JSON: equality of two dumps asserts values AND key order."""
    return json.dumps(obj, default=str)


_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}$")
_MON = re.compile(r"\d{4}-\d{2}$")


def _norm_arg(value):
    if isinstance(value, str) and _TS.match(value):
        return "<ts>"
    return value


def _norm_keys(result):
    """Replace the date part of usage keys so a literal is date-independent."""
    text = _dumps(result)
    text = re.sub(r"(usage:daily:[^:\"]+:)\d{4}-\d{2}-\d{2}", r"\1<D>", text)
    text = re.sub(r"(usage:monthly:[^:\"]+:)\d{4}-\d{2}", r"\1<M>", text)
    return text


# ---------------------------------------------------------------------------
# Recorder and fakes
# ---------------------------------------------------------------------------


class Rec:
    """Thread-safe op recorder: one entry per blocking op, appended at op start
    (t0) and completed at op end (t1). ``sleep`` is the per-op blocking time;
    ``gate`` (a threading.Event) blocks the ops whose name starts with one of
    ``gate_ops`` until it is set (bounded by ``gate_timeout``)."""

    def __init__(self, sleep=0.0):
        self.sleep = sleep
        self.ops = []
        self.lock = threading.Lock()
        self.gate = None
        self.gate_ops = ()
        self.gate_timeout = 0.6
        self.gate_started = threading.Event()

    def op(self, name, _sleep=None, **info):
        entry = dict(op=name, thread=threading.current_thread(), t0=time.perf_counter(), t1=None)
        entry.update(info)
        with self.lock:
            self.ops.append(entry)
        if self.gate is not None and name.startswith(self.gate_ops):
            self.gate_started.set()
            self.gate.wait(self.gate_timeout)
        sleep = self.sleep if _sleep is None else _sleep
        if sleep:
            time.sleep(sleep)
        entry["t1"] = time.perf_counter()
        return entry

    def names(self, prefix=""):
        return [e["op"] for e in self.ops if e["op"].startswith(prefix)]

    def seq(self, main, prefix=""):
        return [[e["op"], _cls(e["thread"], main)] for e in self.ops if e["op"].startswith(prefix)]


RAISE = object()


class _FakeQuery:
    def __init__(self, client, table):
        self._client = client
        self._table = table
        self.chain = []

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def method(*args, **kwargs):
            if name == "update" and args and isinstance(args[0], dict):
                self.chain.append(["update", sorted(args[0])])
            else:
                item = [name] + [_norm_arg(a) for a in args]
                if kwargs:
                    item.append({k: _norm_arg(v) for k, v in sorted(kwargs.items())})
                self.chain.append(item)
            return self

        return method

    def execute(self):
        kind = "update" if any(c[0] == "update" for c in self.chain) else "select"
        self._client.rec.op("db:%s:%s" % (self._table, kind), chain=copy.deepcopy(self.chain))
        spec = self._client.users if self._table == "users" else self._client.red
        if spec is RAISE:
            raise RuntimeError(self._client.secret_text)
        if kind == "update":
            return SimpleNamespace(data=None)
        return SimpleNamespace(data=copy.deepcopy(spec))


class _FakeClient:
    def __init__(self, rec, users, red):
        self.rec = rec
        self.users = users
        self.red = red
        # Synthetic, built at run time (never a credential shape).
        self.secret_text = "synthetic-" + "db-failure-" + str(len(rec.ops) + 41)

    def table(self, name):
        return _FakeQuery(self, name)


class _FakeRedis:
    """Stateful counter store keyed by the real usage keys; the state's initial
    counts are served for any key of that window kind."""

    def __init__(self, rec, counts):
        self.rec = rec
        self.counts = dict(counts or {})
        self.store = {}

    @staticmethod
    def _kind(key):
        return key.split(":")[1]

    def _cur(self, key):
        if key in self.store:
            return self.store[key]
        raw = self.counts.get(self._kind(key))
        return int(raw) if raw else 0

    def get(self, key):
        self.rec.op("redis:get:" + self._kind(key), key=key)
        if key in self.store:
            return str(self.store[key])
        return self.counts.get(self._kind(key))

    def incrby(self, key, n):
        self.rec.op("redis:incrby:" + self._kind(key), key=key)
        self.store[key] = self._cur(key) + n
        return self.store[key]

    def incr(self, key):
        return self.incrby(key, 1)

    def decrby(self, key, n):
        self.rec.op("redis:decrby:" + self._kind(key), key=key)
        self.store[key] = self._cur(key) - n
        return self.store[key]

    def expire(self, key, ttl):
        self.rec.op("redis:expire:" + self._kind(key), key=key)
        return True


_FREE5 = {"subscription_tier": "free", "lifetime_comparisons_used": 5,
          "referral_bonus_comparisons_this_month": 0}

STATES = {
    "free_paid_window": dict(users=_FREE5, red=[], counts={"daily": "2", "monthly": "7"}),
    "free_lifetime": dict(users={"subscription_tier": "free", "lifetime_comparisons_used": 1},
                          red=[], counts={"daily": "3", "monthly": "9"}),
    "premium_bonus": dict(users={"subscription_tier": "premium", "lifetime_comparisons_used": 100},
                          red=[{"loop2_comparisons_granted": 4}], counts={"daily": "5", "monthly": "20"}),
    "free_reset_past": dict(users={"subscription_tier": "free", "lifetime_comparisons_used": 9,
                                   "referral_bonus_comparisons_this_month": 5,
                                   "referral_bonus_reset_at": "2020-01-01T00:00:00+00:00"},
                            red=[], counts={"daily": "1", "monthly": "1"}),
    "free_daily_exhausted": dict(users=_FREE5, red=[], counts={"daily": "3", "monthly": "4"}),
    "free_monthly_exhausted": dict(users=_FREE5, red=[], counts={"daily": "1", "monthly": "10"}),
    "premium_over": dict(users={"subscription_tier": "premium", "lifetime_comparisons_used": 100},
                         red=[], counts={"daily": "12", "monthly": "80"}),
    "redis_none": dict(users=_FREE5, red=[], counts=None),
    "tier_raises": dict(users=RAISE, red=[], counts={"daily": "1", "monthly": "2"}),
    "bonus_raises": dict(users=_FREE5, red=RAISE, counts={"daily": "1", "monthly": "2"}),
    "unknown_tier": dict(users={"subscription_tier": "gold", "lifetime_comparisons_used": 7},
                         red=[{"loop2_comparisons_granted": 2}, {"loop2_comparisons_granted": None}],
                         counts={"daily": "1", "monthly": "3"}),
}
STATE_IDS = list(STATES)

COMBOS = [(sync, s77, ar) for sync in (False, True) for s77 in (False, True) for ar in (False, True)]
COMBO_IDS = ["sync_%s-s77_%s-async_%s" % tuple("on" if x else "off" for x in c) for c in COMBOS]


def _install_usage(monkeypatch, state, rec):
    spec = STATES[state]
    users = spec["users"] if spec["users"] is RAISE else dict(spec["users"])
    red = spec["red"] if spec["red"] is RAISE else list(spec["red"])
    client = _FakeClient(rec, users, red)
    monkeypatch.setattr(us, "get_admin_supabase_client", lambda: client)
    if spec["counts"] is None:
        monkeypatch.setattr(us, "redis_client", None)
        fake_redis = None
    else:
        fake_redis = _FakeRedis(rec, spec["counts"])
        monkeypatch.setattr(us, "redis_client", fake_redis)
    def counting(key):
        rec.op("count:" + key.split(":")[1], _sleep=0.0, key=key)
        return _REAL_COUNT(key)

    monkeypatch.setattr(us, "_get_redis_count", counting)
    return client, fake_redis


class _Spy:
    """Records every call (and the calling thread); delegates to ``target`` when
    one exists. Installed with raising=False so a missing symbol never errors."""

    def __init__(self, target=None, is_async=False):
        self.target = target
        self.calls = []
        self.is_async = is_async or (target is not None and inspect.iscoroutinefunction(target))

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs, threading.current_thread()))
        if self.target is None:
            return None
        return self.target(*args, **kwargs)


def _install_dispatch_spies(monkeypatch):
    """Spies on the ST1 pool dispatcher in every namespace a caller can use."""
    spies = []
    for mod in (us, rs, ro):
        spy = _Spy(getattr(mod, "run_redis_offloop_pool", None))
        monkeypatch.setattr(mod, "run_redis_offloop_pool", spy, raising=False)
        spies.append(spy)
    return spies


async def _heartbeat(coro, period=0.005):
    gaps = []
    stop = []

    async def beat():
        loop = asyncio.get_running_loop()
        prev = loop.time()
        while not stop:
            await asyncio.sleep(period)
            now = loop.time()
            gaps.append(now - prev)
            prev = now

    task = asyncio.ensure_future(beat())
    await asyncio.sleep(0.02)
    t0 = time.perf_counter()
    result = await coro
    wall = time.perf_counter() - t0
    stop.append(True)
    await task
    return result, (max(gaps) if gaps else 0.0), wall


def _usage_records(caplog):
    return [r for r in caplog.records if r.getMessage().startswith(TAG)]


def _wait_event(event, timeout=3.0):
    return event.wait(timeout)


async def _await_event(event, timeout=3.0):
    deadline = time.perf_counter() + timeout
    while not event.is_set() and time.perf_counter() < deadline:
        await asyncio.sleep(0.005)
    return event.is_set()


# ---------------------------------------------------------------------------
# Base literals (recorded at base 95cf6f86 by the RED author's probe, the
# flag-OFF base bodies in BASE KEY ORDER; dates in usage keys normalised)
# ---------------------------------------------------------------------------

BASE_USAGE_RESULT = {'bonus_raises': '{"tier": "free", "used": {"daily": 1, "monthly": 2, "lifetime": 5}, "limits": '
                 '{"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0, '
                 '"lifetime_free": 3}, "remaining": {"daily": 2, "monthly": 8, "lifetime_free": '
                 '0}}',
 'free_daily_exhausted': '{"tier": "free", "used": {"daily": 3, "monthly": 4, "lifetime": 5}, '
                         '"limits": {"daily": 3, "monthly": 10, "monthly_base": 10, '
                         '"monthly_bonus": 0, "lifetime_free": 3}, "remaining": {"daily": 0, '
                         '"monthly": 6, "lifetime_free": 0}}',
 'free_lifetime': '{"tier": "free", "used": {"daily": 3, "monthly": 9, "lifetime": 1}, "limits": '
                  '{"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0, '
                  '"lifetime_free": 3}, "remaining": {"daily": 3, "monthly": 10, "lifetime_free": '
                  '2}}',
 'free_monthly_exhausted': '{"tier": "free", "used": {"daily": 1, "monthly": 10, "lifetime": 5}, '
                           '"limits": {"daily": 3, "monthly": 10, "monthly_base": 10, '
                           '"monthly_bonus": 0, "lifetime_free": 3}, "remaining": {"daily": 2, '
                           '"monthly": 0, "lifetime_free": 0}}',
 'free_paid_window': '{"tier": "free", "used": {"daily": 2, "monthly": 7, "lifetime": 5}, '
                     '"limits": {"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": '
                     '0, "lifetime_free": 3}, "remaining": {"daily": 1, "monthly": 3, '
                     '"lifetime_free": 0}}',
 'free_reset_past': '{"tier": "free", "used": {"daily": 1, "monthly": 1, "lifetime": 9}, "limits": '
                    '{"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0, '
                    '"lifetime_free": 3}, "remaining": {"daily": 2, "monthly": 9, "lifetime_free": '
                    '0}}',
 'premium_bonus': '{"tier": "premium", "used": {"daily": 5, "monthly": 20, "lifetime": 100}, '
                  '"limits": {"daily": 10, "monthly": 74, "monthly_base": 70, "monthly_bonus": 4, '
                  '"lifetime_free": 0}, "remaining": {"daily": 5, "monthly": 54, "lifetime_free": '
                  '0}}',
 'premium_over': '{"tier": "premium", "used": {"daily": 12, "monthly": 80, "lifetime": 100}, '
                 '"limits": {"daily": 10, "monthly": 70, "monthly_base": 70, "monthly_bonus": 0, '
                 '"lifetime_free": 0}, "remaining": {"daily": 0, "monthly": 0, "lifetime_free": '
                 '0}}',
 'redis_none': '{"tier": "free", "used": {"daily": 0, "monthly": 0, "lifetime": 5}, "limits": '
               '{"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0, '
               '"lifetime_free": 3}, "remaining": {"daily": 3, "monthly": 10, "lifetime_free": 0}}',
 'tier_raises': '{"tier": "free", "used": {"daily": 1, "monthly": 2, "lifetime": 0}, "limits": '
                '{"daily": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0, '
                '"lifetime_free": 3}, "remaining": {"daily": 3, "monthly": 10, "lifetime_free": '
                '3}}',
 'unknown_tier': '{"tier": "gold", "used": {"daily": 1, "monthly": 3, "lifetime": 7}, "limits": '
                 '{"daily": 3, "monthly": 12, "monthly_base": 10, "monthly_bonus": 2, '
                 '"lifetime_free": 3}, "remaining": {"daily": 2, "monthly": 9, "lifetime_free": '
                 '0}}'}

BASE_ALLOWED_RESULT = {'bonus_raises': '{"allowed": true, "reason": null, "tier": "free", "remaining": {"daily": 2, '
                 '"monthly": 8, "lifetime_free": 0}}',
 'free_daily_exhausted': '{"allowed": false, "reason": "daily_limit", "tier": "free", "remaining": '
                         '{"daily": 0, "monthly": 6, "lifetime_free": 0}}',
 'free_lifetime': '{"allowed": true, "reason": null, "tier": "free", "remaining": {"daily": 3, '
                  '"monthly": 10, "lifetime_free": 2}}',
 'free_monthly_exhausted': '{"allowed": false, "reason": "monthly_limit", "tier": "free", '
                           '"remaining": {"daily": 2, "monthly": 0, "lifetime_free": 0}}',
 'free_paid_window': '{"allowed": true, "reason": null, "tier": "free", "remaining": {"daily": 1, '
                     '"monthly": 3, "lifetime_free": 0}}',
 'free_reset_past': '{"allowed": true, "reason": null, "tier": "free", "remaining": {"daily": 2, '
                    '"monthly": 9, "lifetime_free": 0}}',
 'premium_bonus': '{"allowed": true, "reason": null, "tier": "premium", "remaining": {"daily": 5, '
                  '"monthly": 54, "lifetime_free": 0}}',
 'premium_over': '{"allowed": false, "reason": "daily_limit", "tier": "premium", "remaining": '
                 '{"daily": 0, "monthly": 0, "lifetime_free": 0}}',
 'redis_none': '{"allowed": true, "reason": null, "tier": "free", "remaining": {"daily": 3, '
               '"monthly": 10, "lifetime_free": 0}}',
 'tier_raises': '{"allowed": true, "reason": null, "tier": "free", "remaining": {"daily": 3, '
                '"monthly": 10, "lifetime_free": 3}}',
 'unknown_tier': '{"allowed": true, "reason": null, "tier": "gold", "remaining": {"daily": 2, '
                 '"monthly": 9, "lifetime_free": 0}}'}

BASE_USAGE_SEQ = {'bonus_raises|off': [['db:users:select', 'main'],
                      ['db:referral_redemptions:select', 'main'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'bonus_raises|on': [['db:users:select', 'worker'],
                     ['db:referral_redemptions:select', 'worker'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']],
 'free_daily_exhausted|off': [['db:users:select', 'main'],
                              ['db:referral_redemptions:select', 'main'],
                              ['count:daily', 'main'],
                              ['redis:get:daily', 'main'],
                              ['count:monthly', 'main'],
                              ['redis:get:monthly', 'main']],
 'free_daily_exhausted|on': [['db:users:select', 'worker'],
                             ['db:referral_redemptions:select', 'worker'],
                             ['count:daily', 'main'],
                             ['redis:get:daily', 'main'],
                             ['count:monthly', 'main'],
                             ['redis:get:monthly', 'main']],
 'free_lifetime|off': [['db:users:select', 'main'],
                       ['db:referral_redemptions:select', 'main'],
                       ['count:daily', 'main'],
                       ['redis:get:daily', 'main'],
                       ['count:monthly', 'main'],
                       ['redis:get:monthly', 'main']],
 'free_lifetime|on': [['db:users:select', 'worker'],
                      ['db:referral_redemptions:select', 'worker'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'free_monthly_exhausted|off': [['db:users:select', 'main'],
                                ['db:referral_redemptions:select', 'main'],
                                ['count:daily', 'main'],
                                ['redis:get:daily', 'main'],
                                ['count:monthly', 'main'],
                                ['redis:get:monthly', 'main']],
 'free_monthly_exhausted|on': [['db:users:select', 'worker'],
                               ['db:referral_redemptions:select', 'worker'],
                               ['count:daily', 'main'],
                               ['redis:get:daily', 'main'],
                               ['count:monthly', 'main'],
                               ['redis:get:monthly', 'main']],
 'free_paid_window|off': [['db:users:select', 'main'],
                          ['db:referral_redemptions:select', 'main'],
                          ['count:daily', 'main'],
                          ['redis:get:daily', 'main'],
                          ['count:monthly', 'main'],
                          ['redis:get:monthly', 'main']],
 'free_paid_window|on': [['db:users:select', 'worker'],
                         ['db:referral_redemptions:select', 'worker'],
                         ['count:daily', 'main'],
                         ['redis:get:daily', 'main'],
                         ['count:monthly', 'main'],
                         ['redis:get:monthly', 'main']],
 'free_reset_past|off': [['db:users:select', 'main'],
                         ['db:users:update', 'main'],
                         ['db:referral_redemptions:select', 'main'],
                         ['count:daily', 'main'],
                         ['redis:get:daily', 'main'],
                         ['count:monthly', 'main'],
                         ['redis:get:monthly', 'main']],
 'free_reset_past|on': [['db:users:select', 'worker'],
                        ['db:users:update', 'worker'],
                        ['db:referral_redemptions:select', 'worker'],
                        ['count:daily', 'main'],
                        ['redis:get:daily', 'main'],
                        ['count:monthly', 'main'],
                        ['redis:get:monthly', 'main']],
 'premium_bonus|off': [['db:users:select', 'main'],
                       ['db:referral_redemptions:select', 'main'],
                       ['count:daily', 'main'],
                       ['redis:get:daily', 'main'],
                       ['count:monthly', 'main'],
                       ['redis:get:monthly', 'main']],
 'premium_bonus|on': [['db:users:select', 'worker'],
                      ['db:referral_redemptions:select', 'worker'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'premium_over|off': [['db:users:select', 'main'],
                      ['db:referral_redemptions:select', 'main'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'premium_over|on': [['db:users:select', 'worker'],
                     ['db:referral_redemptions:select', 'worker'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']],
 'redis_none|off': [['db:users:select', 'main'],
                    ['db:referral_redemptions:select', 'main'],
                    ['count:daily', 'main'],
                    ['count:monthly', 'main']],
 'redis_none|on': [['db:users:select', 'worker'],
                   ['db:referral_redemptions:select', 'worker'],
                   ['count:daily', 'main'],
                   ['count:monthly', 'main']],
 'tier_raises|off': [['db:users:select', 'main'],
                     ['db:referral_redemptions:select', 'main'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']],
 'tier_raises|on': [['db:users:select', 'worker'],
                    ['db:referral_redemptions:select', 'worker'],
                    ['count:daily', 'main'],
                    ['redis:get:daily', 'main'],
                    ['count:monthly', 'main'],
                    ['redis:get:monthly', 'main']],
 'unknown_tier|off': [['db:users:select', 'main'],
                      ['db:referral_redemptions:select', 'main'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'unknown_tier|on': [['db:users:select', 'worker'],
                     ['db:referral_redemptions:select', 'worker'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']]}

BASE_ALLOWED_SEQ = {'bonus_raises|off': [['db:users:select', 'main'],
                      ['db:referral_redemptions:select', 'main'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'bonus_raises|on': [['db:users:select', 'worker'],
                     ['db:referral_redemptions:select', 'worker'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']],
 'free_daily_exhausted|off': [['db:users:select', 'main'],
                              ['db:referral_redemptions:select', 'main'],
                              ['count:daily', 'main'],
                              ['redis:get:daily', 'main'],
                              ['count:monthly', 'main'],
                              ['redis:get:monthly', 'main']],
 'free_daily_exhausted|on': [['db:users:select', 'worker'],
                             ['db:referral_redemptions:select', 'worker'],
                             ['count:daily', 'main'],
                             ['redis:get:daily', 'main'],
                             ['count:monthly', 'main'],
                             ['redis:get:monthly', 'main']],
 'free_lifetime|off': [['db:users:select', 'main'], ['db:referral_redemptions:select', 'main']],
 'free_lifetime|on': [['db:users:select', 'worker'], ['db:referral_redemptions:select', 'worker']],
 'free_monthly_exhausted|off': [['db:users:select', 'main'],
                                ['db:referral_redemptions:select', 'main'],
                                ['count:daily', 'main'],
                                ['redis:get:daily', 'main'],
                                ['count:monthly', 'main'],
                                ['redis:get:monthly', 'main']],
 'free_monthly_exhausted|on': [['db:users:select', 'worker'],
                               ['db:referral_redemptions:select', 'worker'],
                               ['count:daily', 'main'],
                               ['redis:get:daily', 'main'],
                               ['count:monthly', 'main'],
                               ['redis:get:monthly', 'main']],
 'free_paid_window|off': [['db:users:select', 'main'],
                          ['db:referral_redemptions:select', 'main'],
                          ['count:daily', 'main'],
                          ['redis:get:daily', 'main'],
                          ['count:monthly', 'main'],
                          ['redis:get:monthly', 'main']],
 'free_paid_window|on': [['db:users:select', 'worker'],
                         ['db:referral_redemptions:select', 'worker'],
                         ['count:daily', 'main'],
                         ['redis:get:daily', 'main'],
                         ['count:monthly', 'main'],
                         ['redis:get:monthly', 'main']],
 'free_reset_past|off': [['db:users:select', 'main'],
                         ['db:users:update', 'main'],
                         ['db:referral_redemptions:select', 'main'],
                         ['count:daily', 'main'],
                         ['redis:get:daily', 'main'],
                         ['count:monthly', 'main'],
                         ['redis:get:monthly', 'main']],
 'free_reset_past|on': [['db:users:select', 'worker'],
                        ['db:users:update', 'worker'],
                        ['db:referral_redemptions:select', 'worker'],
                        ['count:daily', 'main'],
                        ['redis:get:daily', 'main'],
                        ['count:monthly', 'main'],
                        ['redis:get:monthly', 'main']],
 'premium_bonus|off': [['db:users:select', 'main'],
                       ['db:referral_redemptions:select', 'main'],
                       ['count:daily', 'main'],
                       ['redis:get:daily', 'main'],
                       ['count:monthly', 'main'],
                       ['redis:get:monthly', 'main']],
 'premium_bonus|on': [['db:users:select', 'worker'],
                      ['db:referral_redemptions:select', 'worker'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'premium_over|off': [['db:users:select', 'main'],
                      ['db:referral_redemptions:select', 'main'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'premium_over|on': [['db:users:select', 'worker'],
                     ['db:referral_redemptions:select', 'worker'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']],
 'redis_none|off': [['db:users:select', 'main'],
                    ['db:referral_redemptions:select', 'main'],
                    ['count:daily', 'main'],
                    ['count:monthly', 'main']],
 'redis_none|on': [['db:users:select', 'worker'],
                   ['db:referral_redemptions:select', 'worker'],
                   ['count:daily', 'main'],
                   ['count:monthly', 'main']],
 'tier_raises|off': [['db:users:select', 'main'], ['db:referral_redemptions:select', 'main']],
 'tier_raises|on': [['db:users:select', 'worker'], ['db:referral_redemptions:select', 'worker']],
 'unknown_tier|off': [['db:users:select', 'main'],
                      ['db:referral_redemptions:select', 'main'],
                      ['count:daily', 'main'],
                      ['redis:get:daily', 'main'],
                      ['count:monthly', 'main'],
                      ['redis:get:monthly', 'main']],
 'unknown_tier|on': [['db:users:select', 'worker'],
                     ['db:referral_redemptions:select', 'worker'],
                     ['count:daily', 'main'],
                     ['redis:get:daily', 'main'],
                     ['count:monthly', 'main'],
                     ['redis:get:monthly', 'main']]}

BASE_CONSUME_SEQ = {'bonus_raises|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                 ['db:users:select', 'main']],
                          'redis': [['redis:incrby:daily', 'main'],
                                    ['redis:incrby:monthly', 'main']]},
 'bonus_raises|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                ['db:users:select', 'main']],
                         'redis': [['redis:incrby:daily', 'worker'],
                                   ['redis:incrby:monthly', 'worker']]},
 'bonus_raises|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                ['db:users:select', 'worker']],
                         'redis': [['redis:incrby:daily', 'main'],
                                   ['redis:incrby:monthly', 'main']]},
 'bonus_raises|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                               ['db:users:select', 'worker']],
                        'redis': [['redis:incrby:daily', 'worker'],
                                  ['redis:incrby:monthly', 'worker']]},
 'free_daily_exhausted|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                         ['db:users:select', 'main']],
                                  'redis': [['redis:incrby:daily', 'main'],
                                            ['redis:decrby:daily', 'main'],
                                            ['count:monthly', 'main'],
                                            ['redis:get:monthly', 'main']]},
 'free_daily_exhausted|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                        ['db:users:select', 'main']],
                                 'redis': [['redis:incrby:daily', 'worker'],
                                           ['redis:decrby:daily', 'worker'],
                                           ['count:monthly', 'worker'],
                                           ['redis:get:monthly', 'worker']]},
 'free_daily_exhausted|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                        ['db:users:select', 'worker']],
                                 'redis': [['redis:incrby:daily', 'main'],
                                           ['redis:decrby:daily', 'main'],
                                           ['count:monthly', 'main'],
                                           ['redis:get:monthly', 'main']]},
 'free_daily_exhausted|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                                       ['db:users:select', 'worker']],
                                'redis': [['redis:incrby:daily', 'worker'],
                                          ['redis:decrby:daily', 'worker'],
                                          ['count:monthly', 'worker'],
                                          ['redis:get:monthly', 'worker']]},
 'free_lifetime|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                  ['db:users:select', 'main']],
                           'redis': [['redis:incrby:daily', 'main'],
                                     ['redis:incrby:monthly', 'main']]},
 'free_lifetime|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                 ['db:users:select', 'main']],
                          'redis': [['redis:incrby:daily', 'worker'],
                                    ['redis:incrby:monthly', 'worker']]},
 'free_lifetime|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                 ['db:users:select', 'worker']],
                          'redis': [['redis:incrby:daily', 'main'],
                                    ['redis:incrby:monthly', 'main']]},
 'free_lifetime|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                                ['db:users:select', 'worker']],
                         'redis': [['redis:incrby:daily', 'worker'],
                                   ['redis:incrby:monthly', 'worker']]},
 'free_monthly_exhausted|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                           ['db:users:select', 'main']],
                                    'redis': [['redis:incrby:daily', 'main'],
                                              ['redis:incrby:monthly', 'main'],
                                              ['redis:decrby:monthly', 'main'],
                                              ['redis:decrby:daily', 'main']]},
 'free_monthly_exhausted|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                          ['db:users:select', 'main']],
                                   'redis': [['redis:incrby:daily', 'worker'],
                                             ['redis:incrby:monthly', 'worker'],
                                             ['redis:decrby:monthly', 'worker'],
                                             ['redis:decrby:daily', 'worker']]},
 'free_monthly_exhausted|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                          ['db:users:select', 'worker']],
                                   'redis': [['redis:incrby:daily', 'main'],
                                             ['redis:incrby:monthly', 'main'],
                                             ['redis:decrby:monthly', 'main'],
                                             ['redis:decrby:daily', 'main']]},
 'free_monthly_exhausted|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                                         ['db:users:select', 'worker']],
                                  'redis': [['redis:incrby:daily', 'worker'],
                                            ['redis:incrby:monthly', 'worker'],
                                            ['redis:decrby:monthly', 'worker'],
                                            ['redis:decrby:daily', 'worker']]},
 'free_paid_window|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                     ['db:users:select', 'main']],
                              'redis': [['redis:incrby:daily', 'main'],
                                        ['redis:incrby:monthly', 'main']]},
 'free_paid_window|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                    ['db:users:select', 'main']],
                             'redis': [['redis:incrby:daily', 'worker'],
                                       ['redis:incrby:monthly', 'worker']]},
 'free_paid_window|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                    ['db:users:select', 'worker']],
                             'redis': [['redis:incrby:daily', 'main'],
                                       ['redis:incrby:monthly', 'main']]},
 'free_paid_window|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                                   ['db:users:select', 'worker']],
                            'redis': [['redis:incrby:daily', 'worker'],
                                      ['redis:incrby:monthly', 'worker']]},
 'free_reset_past|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                    ['db:users:select', 'main'],
                                    ['db:users:update', 'main']],
                             'redis': [['redis:incrby:daily', 'main'],
                                       ['redis:incrby:monthly', 'main']]},
 'free_reset_past|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                   ['db:users:select', 'main'],
                                   ['db:users:update', 'main']],
                            'redis': [['redis:incrby:daily', 'worker'],
                                      ['redis:incrby:monthly', 'worker']]},
 'free_reset_past|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                   ['db:users:select', 'worker'],
                                   ['db:users:update', 'worker']],
                            'redis': [['redis:incrby:daily', 'main'],
                                      ['redis:incrby:monthly', 'main']]},
 'free_reset_past|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                                  ['db:users:select', 'worker'],
                                  ['db:users:update', 'worker']],
                           'redis': [['redis:incrby:daily', 'worker'],
                                     ['redis:incrby:monthly', 'worker']]},
 'premium_bonus|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                  ['db:users:select', 'main']],
                           'redis': [['redis:incrby:daily', 'main'],
                                     ['redis:incrby:monthly', 'main']]},
 'premium_bonus|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                 ['db:users:select', 'main']],
                          'redis': [['redis:incrby:daily', 'worker'],
                                    ['redis:incrby:monthly', 'worker']]},
 'premium_bonus|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                 ['db:users:select', 'worker']],
                          'redis': [['redis:incrby:daily', 'main'],
                                    ['redis:incrby:monthly', 'main']]},
 'premium_bonus|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                                ['db:users:select', 'worker']],
                         'redis': [['redis:incrby:daily', 'worker'],
                                   ['redis:incrby:monthly', 'worker']]},
 'premium_over|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                 ['db:users:select', 'main']],
                          'redis': [['redis:incrby:daily', 'main'],
                                    ['redis:decrby:daily', 'main'],
                                    ['count:monthly', 'main'],
                                    ['redis:get:monthly', 'main']]},
 'premium_over|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                ['db:users:select', 'main']],
                         'redis': [['redis:incrby:daily', 'worker'],
                                   ['redis:decrby:daily', 'worker'],
                                   ['count:monthly', 'worker'],
                                   ['redis:get:monthly', 'worker']]},
 'premium_over|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                ['db:users:select', 'worker']],
                         'redis': [['redis:incrby:daily', 'main'],
                                   ['redis:decrby:daily', 'main'],
                                   ['count:monthly', 'main'],
                                   ['redis:get:monthly', 'main']]},
 'premium_over|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                               ['db:users:select', 'worker']],
                        'redis': [['redis:incrby:daily', 'worker'],
                                  ['redis:decrby:daily', 'worker'],
                                  ['count:monthly', 'worker'],
                                  ['redis:get:monthly', 'worker']]},
 'redis_none|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                               ['db:users:select', 'main']],
                        'redis': [['count:daily', 'main'], ['count:monthly', 'main']]},
 'redis_none|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                              ['db:users:select', 'main']],
                       'redis': [['count:daily', 'worker'], ['count:monthly', 'worker']]},
 'redis_none|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                              ['db:users:select', 'worker']],
                       'redis': [['count:daily', 'main'], ['count:monthly', 'main']]},
 'redis_none|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                             ['db:users:select', 'worker']],
                      'redis': [['count:daily', 'worker'], ['count:monthly', 'worker']]},
 'tier_raises|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                ['db:users:select', 'main']],
                         'redis': [['redis:incrby:daily', 'main'],
                                   ['redis:incrby:monthly', 'main']]},
 'tier_raises|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                               ['db:users:select', 'main']],
                        'redis': [['redis:incrby:daily', 'worker'],
                                  ['redis:incrby:monthly', 'worker']]},
 'tier_raises|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                               ['db:users:select', 'worker']],
                        'redis': [['redis:incrby:daily', 'main'],
                                  ['redis:incrby:monthly', 'main']]},
 'tier_raises|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                              ['db:users:select', 'worker']],
                       'redis': [['redis:incrby:daily', 'worker'],
                                 ['redis:incrby:monthly', 'worker']]},
 'unknown_tier|off|off': {'db': [['db:referral_redemptions:select', 'main'],
                                 ['db:users:select', 'main']],
                          'redis': [['redis:incrby:daily', 'main'],
                                    ['redis:incrby:monthly', 'main']]},
 'unknown_tier|off|on': {'db': [['db:referral_redemptions:select', 'main'],
                                ['db:users:select', 'main']],
                         'redis': [['redis:incrby:daily', 'worker'],
                                   ['redis:incrby:monthly', 'worker']]},
 'unknown_tier|on|off': {'db': [['db:referral_redemptions:select', 'worker'],
                                ['db:users:select', 'worker']],
                         'redis': [['redis:incrby:daily', 'main'],
                                   ['redis:incrby:monthly', 'main']]},
 'unknown_tier|on|on': {'db': [['db:referral_redemptions:select', 'worker'],
                               ['db:users:select', 'worker']],
                        'redis': [['redis:incrby:daily', 'worker'],
                                  ['redis:incrby:monthly', 'worker']]}}

BASE_CONSUME_RESULT = {'bonus_raises': '{"allowed": true, "reason": null, "tier": "free", "consumed": true, '
                 '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                 '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 1, "monthly": 7, '
                 '"lifetime_free": 0}}',
 'free_daily_exhausted': '{"allowed": false, "reason": "daily_limit", "tier": "free", "consumed": '
                         'false, "remaining": {"daily": 0, "monthly": 6, "lifetime_free": 0}}',
 'free_lifetime': '{"allowed": true, "reason": null, "tier": "free", "consumed": true, '
                  '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                  '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 3, "monthly": 10, '
                  '"lifetime_free": 2}}',
 'free_monthly_exhausted': '{"allowed": false, "reason": "monthly_limit", "tier": "free", '
                           '"consumed": false, "remaining": {"daily": 2, "monthly": 0, '
                           '"lifetime_free": 0}}',
 'free_paid_window': '{"allowed": true, "reason": null, "tier": "free", "consumed": true, '
                     '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                     '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 0, "monthly": 2, '
                     '"lifetime_free": 0}}',
 'free_reset_past': '{"allowed": true, "reason": null, "tier": "free", "consumed": true, '
                    '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                    '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 1, "monthly": 8, '
                    '"lifetime_free": 0}}',
 'premium_bonus': '{"allowed": true, "reason": null, "tier": "premium", "consumed": true, '
                  '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                  '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 4, "monthly": 53, '
                  '"lifetime_free": 0}}',
 'premium_over': '{"allowed": false, "reason": "daily_limit", "tier": "premium", "consumed": '
                 'false, "remaining": {"daily": 0, "monthly": 0, "lifetime_free": 0}}',
 'redis_none': '{"allowed": true, "reason": null, "tier": "free", "consumed": true, '
               '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
               '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 3, "monthly": 10, '
               '"lifetime_free": 0}}',
 'tier_raises': '{"allowed": true, "reason": null, "tier": "free", "consumed": true, '
                '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 3, "monthly": 10, '
                '"lifetime_free": 3}}',
 'unknown_tier': '{"allowed": true, "reason": null, "tier": "gold", "consumed": true, '
                 '"consumed_keys": {"daily": "usage:daily:u-synthetic-1:<D>", "monthly": '
                 '"usage:monthly:u-synthetic-1:<M>"}, "remaining": {"daily": 1, "monthly": 8, '
                 '"lifetime_free": 0}}'}

BASE_REFUND_SEQ = {'keyed|off': [['redis:get:daily', 'main'],
               ['redis:decrby:daily', 'main'],
               ['redis:get:monthly', 'main'],
               ['redis:decrby:monthly', 'main']],
 'keyed|on': [['redis:get:daily', 'worker'],
              ['redis:decrby:daily', 'worker'],
              ['redis:get:monthly', 'worker'],
              ['redis:decrby:monthly', 'worker']],
 'legacy|off': [['redis:get:daily', 'main'],
                ['redis:decrby:daily', 'main'],
                ['redis:get:monthly', 'main'],
                ['redis:decrby:monthly', 'main']],
 'legacy|on': [['redis:get:daily', 'worker'],
               ['redis:decrby:daily', 'worker'],
               ['redis:get:monthly', 'worker'],
               ['redis:decrby:monthly', 'worker']]}

BASE_ROUTE = {'free_lifetime': (200,
                   '{"tier":"free","used":{"daily":3,"monthly":9,"lifetime":1},"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3},"remaining":{"daily":3,"monthly":10,"lifetime_free":2}}'),
 'free_paid_window': (200,
                      '{"tier":"free","used":{"daily":2,"monthly":7,"lifetime":5},"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3},"remaining":{"daily":1,"monthly":3,"lifetime_free":0}}'),
 'free_reset_past': (200,
                     '{"tier":"free","used":{"daily":1,"monthly":1,"lifetime":9},"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3},"remaining":{"daily":2,"monthly":9,"lifetime_free":0}}'),
 'premium_bonus': (200,
                   '{"tier":"premium","used":{"daily":5,"monthly":20,"lifetime":100},"limits":{"daily":10,"monthly":74,"monthly_base":70,"monthly_bonus":4,"lifetime_free":0},"remaining":{"daily":5,"monthly":54,"lifetime_free":0}}')}

BASE_REVIEWS_SEQ = {'l1_hit|off': [['l1:get', 'main']],
 'l1_hit|on': [['l1:get', 'pool']],
 'l2_hit|off': [['l1:get', 'main'], ['l2:get', 'main'], ['l1:set', 'main']],
 'l2_hit|on': [['l1:get', 'pool'], ['l2:get', 'main'], ['l1:set', 'main']],
 'miss|off': [['l1:get', 'main'], ['l2:get', 'main'], ['l1:set', 'main'], ['l2:save', 'main']],
 'miss|on': [['l1:get', 'pool'], ['l2:get', 'main'], ['l1:set', 'main'], ['l2:save', 'main']]}

BASE_REVIEWS_OUT = {'l1_hit|off': '{"summary": "cached", "_cached": true}',
 'l1_hit|on': '{"summary": "cached", "_cached": true}',
 'l2_hit|off': '{"summary": "db", "_cached": true, "_cache_source": "db"}',
 'l2_hit|on': '{"summary": "db", "_cached": true, "_cache_source": "db"}',
 'miss|off': '{"pros": ["solid"], "cons": ["pricey"], "summary": "fresh", "_cached": false}',
 'miss|on': '{"pros": ["solid"], "cons": ["pricey"], "summary": "fresh", "_cached": false}'}

BASE_CHAINS = {'db:referral_redemptions:select': [['select', 'loop2_comparisons_granted'],
                                    ['eq', 'referrer_user_id', 'u-synthetic-1'],
                                    ['gt', 'expires_at', '<ts>'],
                                    ['is_', 'consumed_at', 'null']],
 'db:users:select': [['select',
                      'subscription_tier, lifetime_comparisons_used, '
                      'referral_bonus_comparisons_this_month, referral_bonus_reset_at'],
                     ['eq', 'id', 'u-synthetic-1'],
                     ['single']],
 'db:users:update': [['update',
                      ['referral_bonus_comparisons_this_month', 'referral_bonus_reset_at']],
                     ['eq', 'id', 'u-synthetic-1']]}

BASE_DIGESTS = {('app/services/usage_service.py', 'TIER_LIMITS'): 'bc58-e3b4-6850-bbc2-9884-c49b-1809-dd3c',
 ('app/services/usage_service.py', '_atomic_consume'): '7469-c961-24b0-ce4e-174f-291a-5dda-e334',
 ('app/services/usage_service.py', '_atomic_consume_async'): '2708-af7b-03bc-a251-da04-cd93-00c6-a8c4',
 ('app/services/usage_service.py', '_bump_counters'): '3ea0-760e-673e-0827-7220-bf36-3f46-e3df',
 ('app/services/usage_service.py', '_bump_counters_async'): '44e4-203d-57b9-e339-203b-b99a-da7a-f233',
 ('app/services/usage_service.py', '_daily_key'): '3f76-488c-05ed-f55d-9222-4f55-3624-f146',
 ('app/services/usage_service.py', '_get_active_referral_bonus'): '75ad-cbc5-b9ed-1239-0561-f232-46fd-ad76',
 ('app/services/usage_service.py', '_get_redis_count'): '14f0-6465-a31c-293c-397c-2b8c-185b-6e64',
 ('app/services/usage_service.py', '_get_redis_count_async'): 'e06b-3012-6820-7c87-9dbf-1d07-c3da-f1fb',
 ('app/services/usage_service.py', '_get_user_tier_info'): 'd08d-f410-b0f2-54c5-c85b-2388-9e26-6afa',
 ('app/services/usage_service.py', '_maybe_reset_referral_bonus'): '0e22-0a05-bfef-8cc6-4330-1c0b-5461-dbe2',
 ('app/services/usage_service.py', '_monthly_key'): '63ff-3c9e-84fb-d1cb-c6d1-e76b-70af-5099',
 ('app/services/usage_service.py', '_previous_daily_key'): 'b3c3-dd2e-05cb-059e-a194-709c-a761-4d9f',
 ('app/services/usage_service.py', '_previous_monthly_key'): '885f-6947-965d-9c86-7e04-776e-15d1-b5de',
 ('app/services/usage_service.py', '_refund_credit_sync'): '2c8f-a576-0fcd-214b-f597-6333-6bef-7041',
 ('app/services/usage_service.py', '_refund_one_window'): '7eec-f1d0-72cc-e151-d097-ecc3-4e58-b286',
 ('app/services/usage_service.py', 'check_anon_usage_allowed'): '839e-d955-09d4-647b-23ec-e2ce-5a84-d5f0',
 ('app/services/usage_service.py', 'consume_comparison_credit'): 'cfe7-16e2-3081-b31c-09c4-9933-e294-a8cf',
 ('app/services/usage_service.py', 'record_lifetime_comparison'): 'f8ae-429c-bd5b-a91f-d6cf-c342-11bb-01af',
 ('app/services/usage_service.py', 'refund_comparison_credit'): '65ea-bb27-33f9-b964-66a3-cdfc-749d-a1b9',
 ('app/utils/db_offload.py', 'run_db'): 'a193-babb-9590-f520-dc2c-86c2-f38e-39b0',
 ('app/utils/db_offload.py', 'sync_db_offload_enabled'): '8cf1-4184-edf5-ed67-d7b2-4950-8337-e1b4',
 ('app/utils/redis_offloop.py', '_get_redis_offloop_pool'): '2559-7d3c-06b0-6dfc-9aa7-2b36-ac7d-065b',
 ('app/utils/redis_offloop.py', '_retrieve_quietly'): '5ccd-c320-98ec-4fe3-bbc3-54f5-a869-ec2a',
 ('app/utils/redis_offloop.py', 'redis_offloop_enabled'): '3f12-c97d-92e6-5263-21c5-49fa-06ec-c83f',
 ('app/utils/redis_offloop.py', 'redis_offloop_max_workers'): '35b8-ab2d-83bd-3d1c-1dc2-dbfc-f08b-ef16',
 ('app/utils/redis_offloop.py', 'redis_offloop_pool_stats'): 'db30-08ab-19c3-21b2-b6fb-7a09-5d48-f728',
 ('app/utils/redis_offloop.py', 'run_redis_offloop'): 'b030-3fb2-09a3-edf7-b39f-292f-0579-a0ca'}


# ---------------------------------------------------------------------------
# Reviews harness
# ---------------------------------------------------------------------------

R_BRAND, R_NAME, R_VARIANT, R_QUERY = "Acme", "Widget", None, "Acme Widget"
EXTRACTED = {"pros": ["solid"], "cons": ["pricey"], "summary": "fresh"}
QUOTES = [{"source": "store.example", "quote": "nice"}]
SIGNAL = {"video_id": "v-synthetic-1", "verdict": "positive"}


class _RevEnv:
    """Fakes for every store and helper get_reviews touches. set_cached records
    the payload AT LANDING TIME (after an optional per-payload delay), so a write
    that serialised the live dict instead of its snapshot is visible."""

    def __init__(self, monkeypatch, rec, *, l1=None, l2=None, consult=None, yt=None,
                 extract_hook=None, set_delay=None, consult_sleep=0.0):
        self.rec = rec
        self.l1, self.l2 = l1, l2
        self.consult_value, self.yt_value = consult, yt
        self.extract_hook, self.set_delay = extract_hook, set_delay
        self.consult_sleep = consult_sleep
        self.landed = threading.Event()
        self.landings = []
        self.saves = []
        self.ticks = None
        self.tick_at_l2 = None
        self.tick_at_set = None
        self._lock = threading.Lock()
        monkeypatch.setattr(rs, "get_cached", self.get_cached)
        monkeypatch.setattr(rs, "set_cached", self.set_cached)
        monkeypatch.setattr(pds, "get_cached_reviews", self.l2_get)
        monkeypatch.setattr(pds, "save_reviews", self.save)
        monkeypatch.setattr(rs, "extract_reviews", self.extract)
        monkeypatch.setattr(rs, "consult_review_sources", self.consult)
        monkeypatch.setattr(rs, "consult_youtube_source", self.yt)

    def get_cached(self, key):
        self.rec.op("l1:get", key=key)
        return copy.deepcopy(self.l1)

    def set_cached(self, key, value, ttl=86400):
        delay = self.set_delay(value) if self.set_delay else 0.0
        if delay:
            time.sleep(delay)
        if self.ticks is not None:
            self.tick_at_set = self.ticks[0]
        entry = self.rec.op("l1:set", key=key, ttl=ttl, payload=copy.deepcopy(value))
        with self._lock:
            self.landings.append(entry)
        self.landed.set()
        return True

    async def l2_get(self, key):
        self.rec.op("l2:get", key=key)
        if self.ticks is not None:
            self.tick_at_l2 = self.ticks[0]
        return copy.deepcopy(self.l2)

    async def save(self, cache_key, brand, name, variant, reviews):
        self.rec.op("l2:save")
        self.saves.append((cache_key, brand, name, variant))

    async def extract(self, brand, name, variant, ctx, category="other"):
        if self.extract_hook is not None:
            self.extract_hook()
        return copy.deepcopy(EXTRACTED), {"prompt_tokens": 1}

    async def consult(self, *args, **kwargs):
        if self.consult_sleep:
            await asyncio.sleep(self.consult_sleep)
        return copy.deepcopy(self.consult_value)

    async def yt(self, *args, **kwargs):
        return copy.deepcopy(self.yt_value)


def _rkey():
    return rs.get_reviews_cache_key(R_BRAND, R_NAME, R_VARIANT)


async def _get_reviews_call(nocache=False):
    return await rs.get_reviews(
        R_BRAND, R_NAME, R_VARIANT, R_QUERY, nocache=nocache, category="other",
        search_results={"organic": []},
    )


def _occupy_pool(n, gate=None, seconds=None):
    """Submit ``n`` blocking jobs to the SHARED redis-offloop pool (the catalog
    GETs of a cold compare in production)."""
    started = threading.Event()

    def blocker():
        started.set()
        if gate is not None:
            gate.wait(3.0)
        else:
            time.sleep(seconds)

    pool = ro._get_redis_offloop_pool()
    for _ in range(n):
        pool.submit(blocker)
    started.wait(1.0)


# ===========================================================================
# R1-R3: the new leaf helpers
# ===========================================================================


def test_r01_new_helpers_exist_and_no_db_twin():
    """RED: the flag reader and the flag-free pool dispatcher exist in the leaf
    module; R-ST1-1 dropped run_db_offloop (no new DB dispatch helper)."""
    reader = _require(ro, "usage_path_offloop_enabled")
    pool_fn = _require(ro, "run_redis_offloop_pool")
    assert callable(reader)
    assert inspect.iscoroutinefunction(pool_fn), "run_redis_offloop_pool must be async"
    assert not hasattr(dbo, "run_db_offloop"), "R-ST1-1: no run_db_offloop"


@pytest.mark.parametrize(
    "raw,expected",
    [(None, False), ("", False), ("false", False), ("0", False), ("off", False),
     ("no", False), ("garbage", False), ("truee", False), ("  ", False),
     ("true", True), ("TRUE", True), (" true ", True), ("1", True), ("yes", True),
     ("on", True), (" On ", True)],
)
def test_r02_flag_reader_truth_table(monkeypatch, raw, expected):
    reader = _require(ro, "usage_path_offloop_enabled")
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    assert reader() is expected, (raw, expected)


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
def test_r03a_pool_dispatch_is_independent_of_the_s77_flag(monkeypatch, caplog, s77):
    """RED: run_redis_offloop_pool runs fn on the SHARED redis-offloop pool whatever
    ENABLE_PRICE_PATH_REDIS_OFFLOOP says, builds exactly one pool (reused), and
    copies the caller's contextvars."""
    pool_fn = _require(ro, "run_redis_offloop_pool")
    monkeypatch.setenv(KNOB, "4")
    _set(monkeypatch, S77, s77)
    caplog.set_level(logging.INFO, logger=ro.logger.name)
    seen = []

    def job(x):
        seen.append((threading.current_thread().name, _ST1_CV.get()))
        _ST1_CV.set("worker-set")
        return x * 2

    async def main():
        token = _ST1_CV.set("caller-value")
        try:
            a = await pool_fn(job, 21)
            first = ro._REDIS_OFFLOOP_POOL
            b = await pool_fn(job, 4)
            second = ro._REDIS_OFFLOOP_POOL
            after = _ST1_CV.get()
        finally:
            _ST1_CV.reset(token)
        return a, b, first, second, after

    a, b, first, second, after = asyncio.run(main())
    assert (a, b) == (42, 8)
    assert first is not None and first is second, "one shared pool, built once and reused"
    assert ro._get_redis_offloop_pool() is first
    assert ro.redis_offloop_pool_stats()["workers"] == 4
    assert [n.startswith(PREFIX) for n, _cv in seen] == [True, True], seen
    assert [cv for _n, cv in seen] == ["caller-value", "caller-value"], seen
    assert after == "caller-value", "a .set() in the worker leaked to the caller"
    built = [r for r in caplog.records if r.getMessage() == "[REDIS-OFFLOOP] pool built workers=4"]
    assert len(built) == 1, [r.getMessage() for r in caplog.records]


def test_r03b_durable_write_lands_when_its_caller_is_cancelled_while_queued(monkeypatch):
    """RED: durable=True shields the job: queued behind a 1-worker blocker, a
    cancelled caller still lets the write run."""
    pool_fn = _require(ro, "run_redis_offloop_pool")
    monkeypatch.setenv(KNOB, "1")
    gate = threading.Event()
    started = threading.Event()
    landed = threading.Event()
    where = []

    def blocker():
        started.set()
        gate.wait(3.0)

    def write():
        where.append(threading.current_thread().name)
        landed.set()

    async def main():
        b = asyncio.ensure_future(pool_fn(blocker))
        ok = await _await_event(started, 2.0)
        w = asyncio.ensure_future(pool_fn(write, durable=True))
        await asyncio.sleep(0.05)
        w.cancel()
        try:
            await w
            cancelled = False
        except asyncio.CancelledError:
            cancelled = True
        gate.set()
        await b
        return ok, cancelled, await _await_event(landed, 2.0)

    try:
        ok, cancelled, did_land = asyncio.run(main())
    finally:
        gate.set()
    assert ok and cancelled
    assert did_land, "the durable write queued behind the blocker was dropped by the cancel"
    assert where and where[0].startswith(PREFIX), where


def test_r03c_non_durable_read_queued_is_dropped_on_cancel(monkeypatch):
    """RED: reads are not shielded (the S77 semantics): a queued read whose caller
    is cancelled never runs."""
    pool_fn = _require(ro, "run_redis_offloop_pool")
    monkeypatch.setenv(KNOB, "1")
    gate = threading.Event()
    started = threading.Event()
    ran = []

    def blocker():
        started.set()
        gate.wait(3.0)

    def read():
        ran.append(threading.current_thread().name)
        return 1

    async def main():
        b = asyncio.ensure_future(pool_fn(blocker))
        await _await_event(started, 2.0)
        r = asyncio.ensure_future(pool_fn(read))
        await asyncio.sleep(0.05)
        r.cancel()
        try:
            await r
            cancelled = False
        except asyncio.CancelledError:
            cancelled = True
        gate.set()
        await b
        await asyncio.sleep(0.1)
        return cancelled

    try:
        cancelled = asyncio.run(main())
    finally:
        gate.set()
    assert cancelled
    assert ran == [], f"the cancelled queued read still ran: {ran}"


# ===========================================================================
# R5-R11: get_usage_status / check_usage_allowed under the flag
# ===========================================================================


def _assert_on_placement(got, sync, label):
    db_cls = "worker" if sync else "main"
    for op, cls in got:
        if op.startswith("db:"):
            assert cls == db_cls, (
                f"{label}: {op} ran on {cls}; R-ST1-1 keeps the Supabase reads on run_db "
                f"(main with sync offload OFF, a worker thread with it ON): {got}")
        else:
            assert cls == "pool", f"{label}: {op} ran on {cls}, not the redis-offloop pool: {got}"


@pytest.mark.parametrize("combo", COMBOS, ids=COMBO_IDS)
@pytest.mark.parametrize("state", STATE_IDS)
def test_r05_usage_status_on_placement(monkeypatch, caplog, state, combo):
    """RED: ST1 ON: the exact base op multiset; the two counter reads on the
    redis-offloop pool in every combination of the other flags; the Supabase reads
    through run_db (main / worker by ENABLE_SYNC_DB_OFFLOAD); base result; no
    [USAGE-OFFLOOP] record on the happy path."""
    sync, s77, async_r = combo
    _full_config(monkeypatch, sync=sync, s77=s77, async_r=async_r)
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.WARNING)
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    main = threading.current_thread()
    result = asyncio.run(us.get_usage_status(UID, "synthetic-access"))
    assert _dumps(result) == BASE_USAGE_RESULT[state]
    got = rec.seq(main)
    expected = BASE_USAGE_SEQ["%s|off" % state]
    assert sorted(op for op, _c in got) == sorted(op for op, _c in expected), (got, expected)
    _assert_on_placement(got, sync, "get_usage_status[%s]" % state)
    assert _usage_records(caplog) == []


@pytest.mark.parametrize("sync", [False, True], ids=["sync_off", "sync_on"])
def test_r06_usage_status_on_loop_freeze(monkeypatch, sync):
    """RED: OP = 0.15 s per blocking op. Base freezes 4 x OP with sync offload OFF
    (0.6 s) and 2 x OP with it ON (the GETs). ST1 ON: sync OFF -> only the two
    Supabase reads stay inline (< 0.45 s); sync ON -> nothing on the loop (< 0.09 s)."""
    op_s = 0.15
    _full_config(monkeypatch, sync=sync)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec(sleep=op_s)
    _install_usage(monkeypatch, "free_paid_window", rec)
    result, gap, _wall = asyncio.run(_heartbeat(us.get_usage_status(UID, "synthetic-access")))
    assert _dumps(result) == BASE_USAGE_RESULT["free_paid_window"]
    limit = 0.09 if sync else 0.45
    assert gap < limit, f"loop freeze {gap:.3f} s >= {limit} s (sync offload {'ON' if sync else 'OFF'})"


@pytest.mark.parametrize("sync", [False, True], ids=["sync_off", "sync_on"])
def test_r07_usage_status_on_reads_in_one_gather(monkeypatch, sync):
    """RED: the reads run concurrently in ONE gather: sync ON -> all four reads
    overlap and the call takes about one op; sync OFF -> the two GETs overlap."""
    op_s = 0.15
    _full_config(monkeypatch, sync=sync)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec(sleep=op_s)
    _install_usage(monkeypatch, "free_paid_window", rec)
    result, _gap, wall = asyncio.run(_heartbeat(us.get_usage_status(UID, "synthetic-access")))
    assert _dumps(result) == BASE_USAGE_RESULT["free_paid_window"]
    reads = [e for e in rec.ops if e["op"].startswith(("db:", "redis:get:"))]
    gets = [e for e in reads if e["op"].startswith("redis:get:")]
    assert len(reads) == 4 and len(gets) == 2, [e["op"] for e in reads]
    if sync:
        assert max(e["t0"] for e in reads) < min(e["t1"] for e in reads), (
            "the four reads did not overlap (not one gather)")
        assert wall < 0.40, f"wall {wall:.3f} s (serial base 0.6 s)"
    else:
        assert max(e["t0"] for e in gets) < min(e["t1"] for e in gets), (
            "the two counter GETs did not overlap (not one gather)")


@pytest.mark.parametrize("fn", ["get_usage_status", "check_usage_allowed"])
@pytest.mark.parametrize("state", STATE_IDS)
def test_r08_on_equals_off_equals_base_literal(monkeypatch, fn, state):
    """PIN (R-ST1-3): the response dict, values AND key order, is the base literal
    with the flag OFF and identical with it ON, for every state."""
    _full_config(monkeypatch, s77=True)
    table = BASE_USAGE_RESULT if fn == "get_usage_status" else BASE_ALLOWED_RESULT
    out = {}
    for on in (False, True):
        _set(monkeypatch, FLAG, on)
        rec = Rec()
        _install_usage(monkeypatch, state, rec)
        out[on] = _dumps(asyncio.run(getattr(us, fn)(UID, "synthetic-access")))
    assert out[False] == table[state], (out[False], table[state])
    assert out[True] == out[False], (out[True], out[False])


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
@pytest.mark.parametrize("sync", [False, True], ids=["sync_off", "sync_on"])
@pytest.mark.parametrize("state", STATE_IDS)
@pytest.mark.parametrize("fn", ["get_usage_status", "check_usage_allowed"])
def test_r09_off_is_the_base_call_sequence(monkeypatch, caplog, fn, state, sync, s77):
    """PIN (B1 rule): ST1 OFF in a rotating spelling, full configuration: the exact
    base op sequence and thread placement (incl. ZERO counter reads on the
    lifetime-free path of check_usage_allowed), the base result, no pool built, the
    ST1 dispatcher never called, no [USAGE-OFFLOOP] record."""
    _full_config(monkeypatch, sync=sync, s77=s77)
    _set_off_spelling(monkeypatch, STATE_IDS.index(state) + 2 * sync + s77)
    caplog.set_level(logging.WARNING)
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    spies = _install_dispatch_spies(monkeypatch)
    main = threading.current_thread()
    result = asyncio.run(getattr(us, fn)(UID, "synthetic-access"))
    seq_table = BASE_USAGE_SEQ if fn == "get_usage_status" else BASE_ALLOWED_SEQ
    res_table = BASE_USAGE_RESULT if fn == "get_usage_status" else BASE_ALLOWED_RESULT
    assert _dumps(result) == res_table[state]
    assert rec.seq(main) == seq_table["%s|%s" % (state, "on" if sync else "off")]
    assert ro._REDIS_OFFLOOP_POOL is None, "the flag-OFF path built a redis-offloop pool"
    assert [len(s.calls) for s in spies] == [0, 0, 0], "ST1 dispatcher called with the flag OFF"
    assert _usage_records(caplog) == []


@pytest.mark.parametrize("combo", COMBOS, ids=COMBO_IDS)
@pytest.mark.parametrize("state", STATE_IDS)
def test_r10_check_usage_allowed_on_placement_and_equal(monkeypatch, caplog, state, combo):
    """RED: ST1 ON: check_usage_allowed reads the same four values in the one
    gather (stated limit L6: the counters are read on the lifetime-free path too),
    with the same placement as R5, and returns the base result."""
    sync, s77, async_r = combo
    _full_config(monkeypatch, sync=sync, s77=s77, async_r=async_r)
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.WARNING)
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    main = threading.current_thread()
    result = asyncio.run(us.check_usage_allowed(UID, "synthetic-access"))
    assert _dumps(result) == BASE_ALLOWED_RESULT[state]
    got = rec.seq(main)
    expected = BASE_USAGE_SEQ["%s|off" % state]
    assert sorted(op for op, _c in got) == sorted(op for op, _c in expected), (got, expected)
    _assert_on_placement(got, sync, "check_usage_allowed[%s]" % state)
    assert _usage_records(caplog) == []


def test_r11_check_allowed_on_reads_both_counters_on_the_lifetime_free_path(monkeypatch):
    """RED: ST1 ON, free_lifetime: exactly the two date-key GETs (base reads none)
    and the base result (the counters are ignored)."""
    _full_config(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    _install_usage(monkeypatch, "free_lifetime", rec)
    result = asyncio.run(us.check_usage_allowed(UID, "synthetic-access"))
    keys = sorted(e["key"] for e in rec.ops if e["op"].startswith("redis:get:"))
    assert keys == sorted([us._daily_key(UID), us._monthly_key(UID)]), keys
    assert _dumps(result) == BASE_ALLOWED_RESULT["free_lifetime"]


# ===========================================================================
# R12-R13: consume and refund untouched by the flag
# ===========================================================================


@pytest.mark.parametrize("async_r", [False, True], ids=["async_off", "async_on"])
@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
@pytest.mark.parametrize("sync", [False, True], ids=["sync_off", "sync_on"])
@pytest.mark.parametrize("state", STATE_IDS)
def test_r12_consume_is_unchanged_by_the_flag(monkeypatch, state, sync, s77, async_r):
    """PIN: consume_comparison_credit's ops, threads and result (consumed_keys shape
    included) equal the base literals with ST1 OFF and are identical with ST1 ON."""
    _full_config(monkeypatch, sync=sync, s77=s77, async_r=async_r)
    main = threading.current_thread()
    out = {}
    for on in (False, True):
        _set(monkeypatch, FLAG, on)
        rec = Rec()
        _install_usage(monkeypatch, state, rec)
        res = asyncio.run(us.consume_comparison_credit(UID, "synthetic-access"))
        seq = {"db": sorted(rec.seq(main, "db:")),
               "redis": [x for x in rec.seq(main) if not x[0].startswith("db:")]}
        out[on] = (_norm_keys(res), seq)
    key = "%s|%s|%s" % (state, "on" if sync else "off", "on" if async_r else "off")
    assert out[False] == (BASE_CONSUME_RESULT[state], BASE_CONSUME_SEQ[key]), out[False]
    assert out[True] == out[False]


@pytest.mark.parametrize("async_r", [False, True], ids=["async_off", "async_on"])
@pytest.mark.parametrize("form", ["keyed", "legacy"])
def test_r13_refund_is_unchanged_by_the_flag(monkeypatch, form, async_r):
    """PIN: refund_comparison_credit (consumed_keys and the legacy no-keys form):
    the base GET/DECRBY sequence on the base thread with ST1 OFF and ON."""
    _full_config(monkeypatch, async_r=async_r, s77=True)
    main = threading.current_thread()
    out = {}
    for on in (False, True):
        _set(monkeypatch, FLAG, on)
        rec = Rec()
        _install_usage(monkeypatch, "free_paid_window", rec)
        keys = ({"daily": us._daily_key(UID), "monthly": us._monthly_key(UID)}
                if form == "keyed" else None)
        asyncio.run(us.refund_comparison_credit(UID, keys))
        out[on] = rec.seq(main)
    assert out[False] == BASE_REFUND_SEQ["%s|%s" % (form, "on" if async_r else "off")]
    assert out[True] == out[False]


# ===========================================================================
# R14-R17: dispatch failure, cancel, the existing helpers
# ===========================================================================


@pytest.mark.parametrize("mode", ["sync_raise", "async_raise"])
@pytest.mark.parametrize("fn", ["get_usage_status", "check_usage_allowed"])
def test_r14_dispatch_failure_falls_back_inline(monkeypatch, caplog, fn, mode):
    """RED (correction 4): ST1 ON, the pool dispatcher fails with RuntimeError.
    sync_raise (raised at the call): the base inline body runs once, exact op list.
    async_raise (raised inside the gather): the base inline body is the TAIL of the
    op list and the extra ops are at most one read set (stated limit). Both: the
    base result and exactly one WARNING with the exact template, type only."""
    _full_config(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.WARNING)
    state = "free_paid_window"
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    text = "synthetic-" + "pool-down-" + str(7 * 6)
    if mode == "sync_raise":
        def boom(*args, **kwargs):
            raise RuntimeError(text)
    else:
        async def boom(*args, **kwargs):
            await asyncio.sleep(0)
            raise RuntimeError(text)
    monkeypatch.setattr(us, "run_redis_offloop_pool", boom, raising=False)
    main = threading.current_thread()
    try:
        result = asyncio.run(getattr(us, fn)(UID, "synthetic-access"))
    except Exception as exc:  # noqa: BLE001 - asserted below
        result = exc
    assert not isinstance(result, Exception), (
        "the dispatch failure escaped %s: %s" % (fn, type(result).__name__))
    res_table = BASE_USAGE_RESULT if fn == "get_usage_status" else BASE_ALLOWED_RESULT
    assert _dumps(result) == res_table[state]
    want = "[USAGE-OFFLOOP] dispatch failed fn=%s type=RuntimeError -- inline fallback" % fn
    recs = _usage_records(caplog)
    assert [r.getMessage() for r in recs] == [want], [r.getMessage() for r in recs]
    assert recs[0].levelno == logging.WARNING
    assert text not in caplog.text, "the exception text reached a log line"
    base = (BASE_USAGE_SEQ if fn == "get_usage_status" else BASE_ALLOWED_SEQ)["%s|off" % state]
    got = rec.seq(main)
    if mode == "sync_raise":
        assert got == base, got
    else:
        assert got[-len(base):] == base, got
        extra = collections.Counter(op for op, _c in got[:-len(base)])
        one_set = collections.Counter(op for op, _c in BASE_USAGE_SEQ["%s|off" % state])
        assert not (extra - one_set), f"more than one extra read set: {got}"
        assert all(c == "main" for _o, c in got), got


@pytest.mark.parametrize("sync", [False, True], ids=["sync_off", "sync_on"])
def test_r15_cancel_propagates_without_fallback(monkeypatch, caplog, sync):
    """RED: ST1 ON, the counter GETs block on a gate; cancelling the request while
    they run raises CancelledError, logs nothing and runs no inline fallback."""
    _full_config(monkeypatch, sync=sync)
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.WARNING)
    rec = Rec()
    rec.gate = threading.Event()
    rec.gate_ops = ("redis:get:",)
    rec.gate_timeout = 0.6
    _install_usage(monkeypatch, "free_paid_window", rec)
    main = threading.current_thread()

    async def run():
        task = asyncio.ensure_future(us.get_usage_status(UID, "synthetic-access"))
        started = await _await_event(rec.gate_started, 2.0)
        n_at_cancel = len(rec.ops)
        task.cancel()
        try:
            await task
            outcome = "returned"
        except asyncio.CancelledError:
            outcome = "cancelled"
        rec.gate.set()
        await asyncio.sleep(0.1)
        return started, n_at_cancel, outcome

    try:
        started, n_at_cancel, outcome = asyncio.run(run())
    finally:
        rec.gate.set()
    assert outcome == "cancelled", f"the request was not cancellable mid-read ({outcome})"
    assert started
    assert _usage_records(caplog) == [], "a cancel must not take the fallback branch"
    late_main = [e["op"] for e in rec.ops[n_at_cancel:] if e["thread"] is main]
    assert late_main == [], f"inline ops after the cancel: {late_main}"
    assert rec.names().count("db:users:select") == 1, rec.names()
    assert [e["op"] for e in rec.ops if e["op"].startswith("redis:get:") and e["thread"] is main] == []


@pytest.mark.parametrize("on", [False, True], ids=["st1_off", "st1_on"])
@pytest.mark.parametrize("fn", ["get_usage_status", "check_usage_allowed", "consume_comparison_credit"])
@pytest.mark.parametrize("state", ["free_paid_window", "free_reset_past", "premium_bonus"])
def test_r16_existing_helper_query_chains(monkeypatch, state, fn, on):
    """PIN (B2, R-ST1-2): the full query chains of _get_user_tier_info (select +
    the lazy-reset update keys) and _get_active_referral_bonus are the base chains,
    issued once each, whatever path and flag state reaches them."""
    _full_config(monkeypatch, s77=True)
    _set(monkeypatch, FLAG, on)
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    asyncio.run(getattr(us, fn)(UID, "synthetic-access"))
    chains = collections.defaultdict(list)
    for e in rec.ops:
        if e["op"].startswith("db:"):
            chains[e["op"]].append(e["chain"])
    want = {"db:users:select", "db:referral_redemptions:select"}
    if state == "free_reset_past":
        want.add("db:users:update")
    assert set(chains) == want, sorted(chains)
    for op, seen in chains.items():
        assert seen == [BASE_CHAINS[op]], (op, seen)


@pytest.mark.parametrize("sync", [False, True], ids=["sync_off", "sync_on"])
@pytest.mark.parametrize("fn", ["get_usage_status", "check_usage_allowed"])
def test_r17_on_path_awaits_the_existing_helpers(monkeypatch, fn, sync):
    """PIN (R-ST1-2): with ST1 ON the Supabase half is the EXISTING async helpers,
    each called once with the user id (no twin query)."""
    _full_config(monkeypatch, sync=sync)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    _install_usage(monkeypatch, "free_paid_window", rec)
    tier_spy = _Spy(us._get_user_tier_info)
    bonus_spy = _Spy(us._get_active_referral_bonus)
    monkeypatch.setattr(us, "_get_user_tier_info", tier_spy)
    monkeypatch.setattr(us, "_get_active_referral_bonus", bonus_spy)
    result = asyncio.run(getattr(us, fn)(UID, "synthetic-access"))
    assert [c[0] for c in tier_spy.calls] == [(UID,)], tier_spy.calls
    assert [c[0] for c in bonus_spy.calls] == [(UID,)], bonus_spy.calls
    res_table = BASE_USAGE_RESULT if fn == "get_usage_status" else BASE_ALLOWED_RESULT
    assert _dumps(result) == res_table["free_paid_window"]


# ===========================================================================
# R18-R24, R31, R32: review_service.get_reviews
# ===========================================================================


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off_RED", "s77_on_PIN"])
def test_r18_reviews_l1_read_on_runs_on_the_pool(monkeypatch, s77):
    """RED with the S77 flag OFF, PIN with it ON (correction 5): ST1 ON, L1 hit:
    get_cached on a redis-offloop thread; the base hit dict."""
    _full_config(monkeypatch, s77=s77)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    _RevEnv(monkeypatch, rec, l1={"summary": "cached"})
    main = threading.current_thread()
    out = asyncio.run(_get_reviews_call())
    assert _dumps(out) == BASE_REVIEWS_OUT["l1_hit|off"]
    assert rec.seq(main) == [["l1:get", "pool"]], rec.seq(main)


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
def test_r19_reviews_post_extraction_write_on_runs_on_the_pool(monkeypatch, s77):
    """RED: ST1 ON, L1 + L2 miss: the 7-day set_cached lands on a redis-offloop
    thread with the extracted payload; save_reviews ran once with the base args;
    the returned dict is the base dict."""
    _full_config(monkeypatch, s77=s77)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    env = _RevEnv(monkeypatch, rec)
    main = threading.current_thread()

    async def go():
        out = await _get_reviews_call()
        landed = await _await_event(env.landed, 3.0)
        await asyncio.sleep(0.02)
        return out, landed

    out, landed = asyncio.run(go())
    assert _dumps(out) == BASE_REVIEWS_OUT["miss|off"]
    assert landed, "the post-extraction write never landed"
    assert len(env.landings) == 1, [e["payload"] for e in env.landings]
    w = env.landings[0]
    assert (w["key"], w["ttl"], w["payload"]) == (_rkey(), TTL, EXTRACTED)
    assert _cls(w["thread"], main) == "pool", w["thread"].name
    assert env.saves == [(_rkey(), R_BRAND, R_NAME, R_VARIANT)], env.saves


def test_r19b_reviews_write_dispatch_failure_is_logged_and_swallowed(monkeypatch, caplog):
    """RED: a write dispatch that raises is logged ONCE by type (spec 2.6 template)
    and swallowed: the reviews leg returns the base dict and the L2 save ran."""
    _full_config(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level(logging.WARNING)
    rec = Rec()
    env = _RevEnv(monkeypatch, rec)
    text = "synthetic-" + "write-down-" + str(6 * 7)

    def boom(*args, **kwargs):
        raise RuntimeError(text)

    monkeypatch.setattr(rs, "run_redis_offloop_pool", boom, raising=False)

    async def go():
        out = await _get_reviews_call(nocache=True)
        await asyncio.sleep(0.1)
        return out

    try:
        out = asyncio.run(go())
    except Exception as exc:  # noqa: BLE001 - asserted below
        out = exc
    assert not isinstance(out, Exception), "the write dispatch failure escaped: %s" % type(out).__name__
    assert _dumps(out) == BASE_REVIEWS_OUT["miss|off"]
    msgs = [r.getMessage() for r in _usage_records(caplog)]
    assert msgs == ["[USAGE-OFFLOOP] reviews L1 write dispatch failed type=RuntimeError"], msgs
    assert text not in caplog.text
    assert env.saves == [(_rkey(), R_BRAND, R_NAME, R_VARIANT)], env.saves


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
def test_r20_reviews_l2_promotion_write_stays_inline(monkeypatch, s77):
    """PIN (RO17, L1): ST1 ON, L2 hit: the promotion set_cached runs on the loop
    thread with the base args and no suspension between the L2 read and the SET."""
    _full_config(monkeypatch, s77=s77)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    env = _RevEnv(monkeypatch, rec, l2={"summary": "db"})
    main = threading.current_thread()

    async def go():
        ticks = [0]
        stop = []

        async def tick():
            while not stop:
                ticks[0] += 1
                await asyncio.sleep(0)

        t = asyncio.ensure_future(tick())
        await asyncio.sleep(0)
        env.ticks = ticks
        out = await _get_reviews_call()
        stop.append(True)
        await t
        return out

    out = asyncio.run(go())
    assert _dumps(out) == BASE_REVIEWS_OUT["l2_hit|off"]
    assert len(env.landings) == 1
    w = env.landings[0]
    assert (w["key"], w["ttl"], w["payload"]) == (_rkey(), TTL, {"summary": "db"})
    assert w["thread"] is main, f"the L2-promotion write left the loop ({w['thread'].name})"
    assert env.tick_at_l2 == env.tick_at_set, "the coroutine yielded between the L2 read and the promotion SET"


def test_r21_reviews_recache_writes_on_land_in_order(monkeypatch):
    """RED (R-ST1-4 chain + snapshot): consult and YouTube ON: three writes on the
    pool, landing in order baseline -> + quotes -> + YouTube even when the first is
    the slowest, each payload the snapshot of its own moment (no _cached key)."""
    _full_config(monkeypatch)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()

    def delay(value):
        return 0.3 if "review_source_quotes" not in value else 0.0

    env = _RevEnv(monkeypatch, rec, consult=QUOTES, yt=SIGNAL, set_delay=delay)
    main = threading.current_thread()

    async def go():
        out = await _get_reviews_call()
        deadline = time.perf_counter() + 3.0
        while len(env.landings) < 3 and time.perf_counter() < deadline:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        return out

    out = asyncio.run(go())
    p1 = dict(EXTRACTED)
    p2 = dict(p1, review_source_quotes=QUOTES)
    p3 = dict(p2, youtube_review_signal=SIGNAL)
    assert _dumps(out) == _dumps(dict(p3, _cached=False))
    assert [e["payload"] for e in env.landings] == [p1, p2, p3], [e["payload"] for e in env.landings]
    assert [_cls(e["thread"], main) for e in env.landings] == ["pool"] * 3
    assert {(e["key"], e["ttl"]) for e in env.landings} == {(_rkey(), TTL)}


def test_r22_reviews_race_cancel_still_lands_the_write_and_the_save(monkeypatch):
    """RED (R-ST1-4 shield): ST1 ON, the single pool worker busy, the consult
    sleeping: the 0.3 s race cap cancels get_reviews and the request loop ends; the
    queued write still lands with the snapshot once the pool frees, and the L2 save
    (scheduled first) ran."""
    _full_config(monkeypatch)
    monkeypatch.setenv(KNOB, "1")
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    gate = threading.Event()
    env = _RevEnv(monkeypatch, rec, consult=QUOTES, consult_sleep=5.0,
                  extract_hook=lambda: _occupy_pool(1, gate=gate))
    main = threading.current_thread()

    async def go():
        try:
            await asyncio.wait_for(_get_reviews_call(), 0.3)
            return "returned"
        except asyncio.TimeoutError:
            return "timeout"

    try:
        outcome = asyncio.run(go())
    finally:
        gate.set()
    landed = _wait_event(env.landed, 3.0)
    assert outcome == "timeout"
    assert landed, "the queued write was dropped when the race cancelled the request"
    assert len(env.landings) == 1
    w = env.landings[0]
    assert w["payload"] == EXTRACTED, w["payload"]
    assert _cls(w["thread"], main) == "pool", w["thread"].name
    assert env.saves == [(_rkey(), R_BRAND, R_NAME, R_VARIANT)], env.saves


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
@pytest.mark.parametrize("path", ["l1_hit", "l2_hit", "miss"])
def test_r23_reviews_off_is_the_base_sequence(monkeypatch, path, s77):
    """PIN (B1 rule): ST1 OFF in a rotating spelling, full configuration: the base
    event order and threads, the base dict, the ST1 dispatcher never called, no pool
    built with the S77 flag OFF."""
    _full_config(monkeypatch, s77=s77)
    _set_off_spelling(monkeypatch, ["l1_hit", "l2_hit", "miss"].index(path) * 2 + s77)
    rec = Rec()
    _RevEnv(monkeypatch, rec, l1={"summary": "cached"} if path == "l1_hit" else None,
            l2={"summary": "db"} if path == "l2_hit" else None)
    spies = _install_dispatch_spies(monkeypatch)
    main = threading.current_thread()

    async def go():
        out = await _get_reviews_call()
        await asyncio.sleep(0.05)
        return out

    out = asyncio.run(go())
    key = "%s|%s" % (path, "on" if s77 else "off")
    assert rec.seq(main) == BASE_REVIEWS_SEQ[key], rec.seq(main)
    assert _dumps(out) == BASE_REVIEWS_OUT[key]
    assert [len(s.calls) for s in spies] == [0, 0, 0]
    if not s77:
        assert ro._REDIS_OFFLOOP_POOL is None


@pytest.mark.parametrize("on", [False, True], ids=["st1_off", "st1_on"])
def test_r24_reviews_nocache_reads_no_l1(monkeypatch, on):
    """PIN: nocache=True reads neither L1 nor L2 in either flag state."""
    _full_config(monkeypatch, s77=True)
    _set(monkeypatch, FLAG, on)
    rec = Rec()
    env = _RevEnv(monkeypatch, rec, l1={"summary": "cached"}, l2={"summary": "db"})

    async def go():
        out = await _get_reviews_call(nocache=True)
        await _await_event(env.landed, 3.0)
        await asyncio.sleep(0.02)
        return out

    out = asyncio.run(go())
    assert "l1:get" not in rec.names() and "l2:get" not in rec.names(), rec.names()
    assert _dumps(out) == BASE_REVIEWS_OUT["miss|off"]


@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
def test_r31_reviews_saturated_pool_returns_inside_the_cap(monkeypatch, s77):
    """RED (R-ST1-4, probe D): four 1.0 s jobs fill the 4-worker shared pool during
    the extraction; under a 0.5 s cap ST1 ON still returns the extracted reviews
    (the write is not awaited) and the write lands AFTER the response."""
    _full_config(monkeypatch, s77=s77)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    env = _RevEnv(monkeypatch, rec, extract_hook=lambda: _occupy_pool(4, seconds=1.0))
    main = threading.current_thread()

    async def go():
        try:
            out = await asyncio.wait_for(_get_reviews_call(), 0.5)
        except asyncio.TimeoutError:
            return None, None, None
        at_return = env.landed.is_set()
        ok = await _await_event(env.landed, 3.0)
        await asyncio.sleep(0.02)
        return out, at_return, ok

    out, at_return, ok = asyncio.run(go())
    assert out is not None, "the reviews leg hit the 0.5 s cap behind the saturated pool"
    assert _dumps(out) == BASE_REVIEWS_OUT["miss|off"]
    assert at_return is False, "the write landed before the response (it is on the response path)"
    assert ok, "the write never landed"
    w = env.landings[0]
    assert w["payload"] == EXTRACTED and _cls(w["thread"], main) == "pool"


def test_r32_reviews_write_stores_the_snapshot_taken_at_write_time(monkeypatch):
    """RED (R-ST1-4 deepcopy): the write queued behind a blocker stores the payload
    of its own moment although the caller mutates the returned dict (top level and
    a nested list) before the write runs."""
    _full_config(monkeypatch)
    monkeypatch.setenv(KNOB, "1")
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    gate = threading.Event()
    env = _RevEnv(monkeypatch, rec, extract_hook=lambda: _occupy_pool(1, gate=gate))

    async def go():
        out = await _get_reviews_call()
        pending = not env.landed.is_set()
        out["mutated_after_return"] = True
        out["pros"].append("mutated")
        gate.set()
        ok = await _await_event(env.landed, 3.0)
        return pending, ok

    try:
        pending, ok = asyncio.run(go())
    finally:
        gate.set()
    assert pending, "the write had already landed when get_reviews returned"
    assert ok
    assert env.landings[0]["payload"] == EXTRACTED, env.landings[0]["payload"]


# ===========================================================================
# R25: source inventory and frozen digests
# ===========================================================================


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _top(tree, name):
    found = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
            found.append(n)
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            found.append(n)
    assert len(found) == 1, (name, len(found))
    return found[0]


def _calls(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call) and _call_name(n.func) == name]


def _durable(call):
    return any(kw.arg == "durable" and isinstance(kw.value, ast.Constant) and kw.value.value is True
               for kw in call.keywords)


def _first_arg(call):
    return _call_name(call.args[0]) if call.args else None


def test_r25a_source_inventory():
    """RED: get_reviews keeps the S77 read dispatch and the four direct set_cached
    calls (RO17 + the OFF branch) and gains ONE non-durable
    run_redis_offloop_pool(get_cached, ...) read; every ST1 pool write of
    set_cached is durable; get_usage_status / check_usage_allowed read the flag in
    their first statement; the counter GETs go through run_redis_offloop_pool;
    usage_service gains no to_thread and no run_db_offloop (R-ST1-1)."""
    rs_tree = ast.parse((APP / "services" / "review_service.py").read_text(encoding="utf-8"))
    gr = _top(rs_tree, "get_reviews")
    s77 = [(_first_arg(c), _durable(c)) for c in _calls(gr, "run_redis_offloop")]
    assert s77 == [("get_cached", False)], s77
    pool_reads = [c for c in _calls(gr, "run_redis_offloop_pool") if _first_arg(c) == "get_cached"]
    assert len(pool_reads) == 1 and not _durable(pool_reads[0]), "one non-durable ST1 L1 read"
    covered = set()
    for name in ("run_redis_offloop", "run_redis_offloop_pool"):
        for c in _calls(gr, name):
            for arg in c.args:
                covered.update(id(s) for s in ast.walk(arg))
    direct = [c for c in _calls(gr, "set_cached") if id(c) not in covered]
    assert len(direct) == 4, f"{len(direct)} direct set_cached calls in get_reviews (base 4)"
    writes = [c for c in _calls(rs_tree, "run_redis_offloop_pool") if _first_arg(c) == "set_cached"]
    assert writes and all(_durable(c) for c in writes), "every ST1 L1 write is durable"

    us_tree = ast.parse((APP / "services" / "usage_service.py").read_text(encoding="utf-8"))
    for name in ("get_usage_status", "check_usage_allowed"):
        fn = _top(us_tree, name)
        body = fn.body
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
            body = body[1:]
        first = body[0]
        assert isinstance(first, ast.If) and any(
            isinstance(n, ast.Call) and _call_name(n.func) == "usage_path_offloop_enabled"
            for n in ast.walk(first.test)
        ), f"{name}: the first statement must read ENABLE_USAGE_PATH_OFFLOOP"
    def _reads_counter(call):
        # _get_redis_count passed by name, or (R-ST1-7, keys computed in the job,
        # equivalent by ruling) a lambda calling it.
        if _first_arg(call) == "_get_redis_count":
            return True
        first = call.args[0] if call.args else None
        return isinstance(first, ast.Lambda) and any(
            isinstance(n, ast.Call) and _call_name(n.func) == "_get_redis_count"
            for n in ast.walk(first.body))

    gets = [c for c in _calls(us_tree, "run_redis_offloop_pool") if _reads_counter(c)]
    assert len(gets) >= 2, "the two counter GETs go through run_redis_offloop_pool"
    assert len(_calls(us_tree, "to_thread")) == 4, "R-ST1-1: no new to_thread in usage_service"
    assert _calls(us_tree, "run_db_offloop") == []


@pytest.mark.parametrize("rel,name", sorted(BASE_DIGESTS), ids=["%s::%s" % k for k in sorted(BASE_DIGESTS)])
def test_r25b_frozen_digests(rel, name):
    """PIN: consume, refund, the key helpers, the two gathered helpers, the S77
    reader / pool functions and run_db are byte-unchanged (AST digest at base)."""
    tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
    got = hashlib.sha256(ast.dump(_top(tree, name)).encode()).hexdigest()[:32]
    assert got == BASE_DIGESTS[(rel, name)].replace("-", ""), (rel, name, got)


def test_r25c_db_offload_gains_no_helper():
    """PIN (R-ST1-1): app/utils/db_offload.py keeps exactly its two base functions."""
    tree = ast.parse((APP / "utils" / "db_offload.py").read_text(encoding="utf-8"))
    names = sorted(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    assert names == ["run_db", "sync_db_offload_enabled"], names


# ===========================================================================
# R26-R30: /health, the route, per-call flag, keys
# ===========================================================================


@pytest.mark.parametrize("on", [False, True], ids=["st1_off_PIN", "st1_on_RED"])
def test_r26_health_shows_the_existing_pool_key_after_an_on_read(monkeypatch, on):
    """S77 flag OFF: one get_usage_status with ST1 ON builds the shared pool, so
    /health carries the EXISTING redis_offloop_pool key {workers: 4, queued: int};
    with ST1 OFF the key is absent. status / message unchanged."""
    import app.main as app_main

    _full_config(monkeypatch)
    _set(monkeypatch, FLAG, on)
    rec = Rec()
    _install_usage(monkeypatch, "free_paid_window", rec)
    asyncio.run(us.get_usage_status(UID, "synthetic-access"))
    body = asyncio.run(app_main.health_check())
    assert body.get("status") == "healthy" and body.get("message") == "MYEZ API is running"
    if on:
        snap = body.get("redis_offloop_pool")
        assert isinstance(snap, dict) and set(snap) == {"workers", "queued"}, body
        assert type(snap["workers"]) is int and snap["workers"] == 4, snap
        assert type(snap["queued"]) is int and snap["queued"] >= 0, snap
    else:
        assert "redis_offloop_pool" not in body, sorted(body)


@pytest.mark.parametrize("on", [False, True], ids=["st1_off", "st1_on"])
@pytest.mark.parametrize("state", sorted(BASE_ROUTE))
def test_r27_usage_route_body_is_identical(monkeypatch, state, on):
    """PIN (correction 1): GET /api/v1/usage/status bytes equal the base byte
    literal with ST1 OFF and ON."""
    from fastapi.testclient import TestClient

    import app.main as app_main
    from app.api.auth_routes import get_current_user

    _full_config(monkeypatch, s77=True)
    _set(monkeypatch, FLAG, on)
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    app_main.app.dependency_overrides[get_current_user] = lambda: {
        "id": UID, "access_token": "synthetic-access"}
    try:
        resp = TestClient(app_main.app).get("/api/v1/usage/status")
    finally:
        app_main.app.dependency_overrides.pop(get_current_user, None)
    status, content = BASE_ROUTE[state]
    assert resp.status_code == status
    assert resp.content == content.encode("ascii"), resp.content


def test_r28_flag_is_read_per_call(monkeypatch):
    """RED: one process: ON (GETs on the pool), OFF (inline on the loop), ON again."""
    _full_config(monkeypatch)
    main = threading.current_thread()
    placements = []
    for on in (True, False, True):
        _set(monkeypatch, FLAG, on)
        rec = Rec()
        _install_usage(monkeypatch, "free_paid_window", rec)
        asyncio.run(us.get_usage_status(UID, "synthetic-access"))
        placements.append(sorted({c for _o, c in rec.seq(main, "redis:get:")}))
    assert placements == [["pool"], ["main"], ["pool"]], placements


@pytest.mark.parametrize("direction", ["on_then_off_RED", "off_then_on_PIN"])
def test_r28b_reviews_flag_is_read_once_per_call(monkeypatch, direction):
    """get_reviews reads the flag ONCE: a flip inside the extraction does not move
    the write away from the state of the read."""
    _full_config(monkeypatch)
    start_on = direction.startswith("on")
    _set(monkeypatch, FLAG, start_on)
    rec = Rec()
    env = _RevEnv(monkeypatch, rec, extract_hook=lambda: _set(monkeypatch, FLAG, not start_on))
    main = threading.current_thread()

    async def go():
        out = await _get_reviews_call()
        await _await_event(env.landed, 3.0)
        await asyncio.sleep(0.02)
        return out

    asyncio.run(go())
    want = "pool" if start_on else "main"
    got = [_cls(e["thread"], main) for e in rec.ops if e["op"] in ("l1:get", "l1:set")]
    assert got == [want, want], got


@pytest.mark.parametrize("on", [False, True], ids=["st1_off", "st1_on"])
@pytest.mark.parametrize("fn", ["get_usage_status", "check_usage_allowed"])
def test_r30_get_keys_are_the_date_keys(monkeypatch, fn, on):
    """PIN: the two GET keys are exactly _daily_key(uid) / _monthly_key(uid)."""
    _full_config(monkeypatch, s77=True)
    _set(monkeypatch, FLAG, on)
    rec = Rec()
    _install_usage(monkeypatch, "free_paid_window", rec)
    asyncio.run(getattr(us, fn)(UID, "synthetic-access"))
    keys = [e["key"] for e in rec.ops if e["op"].startswith("redis:get:")]
    want = [us._daily_key(UID), us._monthly_key(UID)]
    assert sorted(keys) == sorted(want), keys
    if not on:
        assert keys == want


# ===========================================================================
# R33: the hermetic admin-client concurrency PIN (R-ST1-6)
# ===========================================================================


class _StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    seen = []
    seen_lock = threading.Lock()

    def do_GET(self):  # noqa: N802 - http.server API
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        raw = (query.get("id") or [""])[0]
        ident = raw[3:] if raw.startswith("eq.") else raw
        with self.seen_lock:
            self.seen.append(ident)
        body = json.dumps({"id": ident, "subscription_tier": "free"}).encode("ascii")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@pytest.mark.parametrize("reuse", [False, True], ids=["client_reuse_off", "client_reuse_on"])
def test_r33_admin_client_concurrent_run_db_pin(monkeypatch, reuse):
    """PIN (R-ST1-6): 16 threads x 50 calls through run_db (sync offload ON, a
    16-thread default executor) on ONE admin client built by the real factory
    against a loopback stub: no exception, every response attributed to its own
    request (the id echoed back), all 800 requests seen."""
    import app.main  # noqa: F401 - the first app import (the B3-B pattern) before patching
    from app.services import database_service as ds

    _StubHandler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(ds, "SUPABASE_URL", "http://127.0.0.1:%d" % server.server_address[1])
        monkeypatch.setattr(ds, "SUPABASE_SERVICE_KEY", "synthetic" + "-service-value")
        _set(monkeypatch, "ENABLE_SUPABASE_CLIENT_REUSE", reuse)
        monkeypatch.setenv(SYNC, "true")
        ds._reset_client_cache_for_tests()

        async def main():
            loop = asyncio.get_running_loop()
            loop.set_default_executor(
                concurrent.futures.ThreadPoolExecutor(max_workers=16, thread_name_prefix="st1-conc"))
            client = ds.get_admin_supabase_client()
            results, errors, threads = [], [], set()

            async def worker(i):
                for j in range(50):
                    ident = "u-st1-%02d-%02d" % (i, j)

                    def call(ident=ident):
                        threads.add(threading.current_thread().name)
                        return (client.table("users").select("subscription_tier")
                                .eq("id", ident).single().execute())
                    try:
                        resp = await dbo.run_db(call)
                        results.append((ident, resp.data))
                    except Exception as exc:  # noqa: BLE001 - counted, asserted empty
                        errors.append(type(exc).__name__)

            await asyncio.gather(*(worker(i) for i in range(16)))
            return results, errors, threads

        results, errors, threads = asyncio.run(main())
    finally:
        server.shutdown()
        server.server_close()
        ds._reset_client_cache_for_tests()
    assert errors == [], collections.Counter(errors)
    assert len(results) == 800
    assert all(isinstance(d, dict) and d.get("id") == ident for ident, d in results), [
        (i, d) for i, d in results if not (isinstance(d, dict) and d.get("id") == i)][:5]
    assert sorted(_StubHandler.seen) == sorted(i for i, _d in results)
    assert len(threads) >= 2 and all(t.startswith("st1-conc") for t in threads), threads


# ===========================================================================
# R34: the W4-13 flag-off ledger with ST1 ON
# ===========================================================================


class TestW413LedgerUnderST1:
    """PIN: the W4-13 45-scenario route ledger (log_search kwargs, labels, status,
    bodies) is unchanged with ENABLE_USAGE_PATH_OFFLOOP set. The W4-13 module's
    autouse guards apply to this class only (zero network, flags cleaned, limiter
    off, overrides restored)."""

    from tests import test_w4_13_measurement_truth as _w413

    # staticmethod: the fixture objects must not bind to the test instance.
    _zero_network = staticmethod(_w413._zero_network)
    _clean_flags = staticmethod(_w413._clean_flags)
    _limiter_off = staticmethod(_w413._limiter_off)
    _restore_overrides = staticmethod(_w413._restore_overrides)

    def test_r34_w4_13_ledger_unchanged_with_st1_on(self, monkeypatch):
        import importlib.util as ilu
        import os

        for name in ("ENABLE_SEARCH_LOG_TRUTH", "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER",
                     "SEARCH_LOG_SYNTHETIC_TOKEN"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(FLAG, "true")
        fixtures = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        spec = ilu.spec_from_file_location(
            "_gen_w4_13_flag_off_ledger", os.path.join(fixtures, "_gen_w4_13_flag_off_ledger.py"))
        gen = ilu.module_from_spec(spec)
        spec.loader.exec_module(gen)
        with open(os.path.join(fixtures, "w4_13_flag_off_ledger.json"), encoding="utf-8") as fh:
            expected = json.load(fh)["records"]
        live = gen.build_ledger(monkeypatch)
        assert len(live) == len(expected) == 45
        moved = [w["scenario"] for g, w in zip(live, expected) if g != w]
        assert moved == [], moved


# ===========================================================================
# R35: one compute body (R-ST1-3)
# ===========================================================================


class _NoIO:
    def __getattr__(self, name):
        raise AssertionError("a compute body touched Redis (%s)" % name)


@pytest.mark.parametrize("state", STATE_IDS)
def test_r35_one_compute_body_for_both_flag_states(monkeypatch, state):
    """RED: _usage_status_body / _usage_allowed_body(user_info, bonus, daily_used,
    monthly_used) are pure and produce the base literals from the four values; each
    public function calls its body exactly once with the flag OFF and ON."""
    status_body = _require(us, "_usage_status_body")
    allowed_body = _require(us, "_usage_allowed_body")
    _full_config(monkeypatch)
    rec = Rec()
    _install_usage(monkeypatch, state, rec)
    user_info = asyncio.run(us._get_user_tier_info(UID))
    bonus = asyncio.run(us._get_active_referral_bonus(UID))
    daily = us._get_redis_count(us._daily_key(UID))
    monthly = us._get_redis_count(us._monthly_key(UID))

    def no_db():
        raise AssertionError("a compute body touched Supabase")

    monkeypatch.setattr(us, "get_admin_supabase_client", no_db)
    monkeypatch.setattr(us, "redis_client", _NoIO())
    assert _dumps(status_body(copy.deepcopy(user_info), bonus, daily, monthly)) == BASE_USAGE_RESULT[state]
    assert _dumps(allowed_body(copy.deepcopy(user_info), bonus, daily, monthly)) == BASE_ALLOWED_RESULT[state]
    for on in (False, True):
        _set(monkeypatch, FLAG, on)
        rec = Rec()
        _install_usage(monkeypatch, state, rec)
        s_spy, a_spy = _Spy(status_body), _Spy(allowed_body)
        monkeypatch.setattr(us, "_usage_status_body", s_spy)
        monkeypatch.setattr(us, "_usage_allowed_body", a_spy)
        r1 = asyncio.run(us.get_usage_status(UID, "synthetic-access"))
        assert (len(s_spy.calls), len(a_spy.calls)) == (1, 0), ("get_usage_status", on)
        r2 = asyncio.run(us.check_usage_allowed(UID, "synthetic-access"))
        assert (len(s_spy.calls), len(a_spy.calls)) == (1, 1), ("check_usage_allowed", on)
        assert _dumps(r1) == BASE_USAGE_RESULT[state] and _dumps(r2) == BASE_ALLOWED_RESULT[state]


# ===========================================================================
# R31b (GATE_ST1 GT-2, appended by GREEN): a re-cache write never waits on the
# request path
# ===========================================================================


# timing row (GT-5): four 1.0 s blockers vs a 0.5 s cap; on a slow runner widen
# the bounds in a test-only commit, never change the code.
@pytest.mark.parametrize("s77", [False, True], ids=["s77_off", "s77_on"])
def test_r31b_reviews_recache_write_under_saturated_pool_returns_inside_the_cap(monkeypatch, s77):
    """PIN (GT-2): the probe-D scenario with the consult path producing a re-cache
    write. Four 1.0 s jobs fill the 4-worker shared pool during the extraction;
    under a 0.5 s cap ST1 ON still returns the enriched reviews, because the
    re-cache write waits for the previous write's handle INSIDE its background
    task, never on the request path; both writes land after the response, in
    order, on the pool."""
    _full_config(monkeypatch, s77=s77)
    monkeypatch.setenv(FLAG, "true")
    rec = Rec()
    env = _RevEnv(monkeypatch, rec, consult=QUOTES,
                  extract_hook=lambda: _occupy_pool(4, seconds=1.0))
    main = threading.current_thread()

    async def go():
        try:
            out = await asyncio.wait_for(_get_reviews_call(), 0.5)
        except asyncio.TimeoutError:
            return None, None, None
        landed_at_return = len(env.landings)
        deadline = time.perf_counter() + 3.0
        while len(env.landings) < 2 and time.perf_counter() < deadline:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        return out, landed_at_return, len(env.landings)

    out, landed_at_return, landed = asyncio.run(go())
    assert out is not None, "a re-cache write waited on the request path behind the saturated pool"
    p1 = dict(EXTRACTED)
    p2 = dict(p1, review_source_quotes=QUOTES)
    assert _dumps(out) == _dumps(dict(p2, _cached=False))
    assert landed_at_return == 0, "a write landed before the response (it is on the response path)"
    assert landed == 2, [e["payload"] for e in env.landings]
    assert [e["payload"] for e in env.landings] == [p1, p2], [e["payload"] for e in env.landings]
    assert [_cls(e["thread"], main) for e in env.landings] == ["pool", "pool"]
    assert {(e["key"], e["ttl"]) for e in env.landings} == {(_rkey(), TTL)}

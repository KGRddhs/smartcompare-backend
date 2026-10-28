"""S81-15 REGISTRY-ROBOTS-DENY: the RED file (ENABLE_MERCHANT_REGISTRY_DB + ENABLE_ROBOTS_REGISTRY_CRON).

Spec .qa-s80/S81-15_UNIT_SPEC.md as amended by its adversarial review and by RULINGS_S81_15 (R-S15-1..19; the
rulings win, then the review corrections, then the spec). Base 98d85433.

House rules. R rows fail at base on an AssertionError ONLY: every missing module or name is read through
``_mod`` / ``_need`` (find_spec + getattr) and asserted, never raised. P rows are green at base and run with the
FULL configuration (ruling B1: the cron flag on, every knob set to a synthetic value, synthetic Supabase names,
an admin-client recorder that records and raises, patched at ``database_service`` AND at the
``merchant_registry._admin_client`` seam when the module exists) so a not-gated mutant is killed. Every flag a row
depends on is set or deleted inside the row (the autouse fixture deletes all of them first). Hermetic: every
Supabase client is the in-memory ``FakeClient``; every fetch, sleep, SSRF check and clock is an injected seam;
the netguard stays on. Hosts are public merchant domains or synthetic ``.test`` hosts.

The kb_merchants contract is S81-14's ``app/services/kb_service.py`` (GREEN 0910e7d0: KB_COLUMNS,
build_merchant_row and the registry entry validator; GATE_S81_14 GC-4). It is not on this base, so the ``kb``
fixture installs a transcription of its merchant half in sys.modules ONLY when the real module is absent; the
rows that take ``kb`` re-run against the real module at GREEN (which starts after S81-14 merges): R22, R23, R24,
R25, R26 and every row that seeds the fake table from ``build_seed_rows`` (R6, R8, R10, R12, P1 / P3 priming).
"""
from __future__ import annotations

import ast
import asyncio
import copy
import dataclasses
import hashlib
import importlib
import importlib.util
import json
import logging
import os
import random
import re
import subprocess
import sys
import threading
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.main  # noqa: F401  (the import-time load_dotenv override runs here, before any setenv)
from app.services import cache_service as cs
from app.services import database_service as dbs
from app.services import deny_hosts
from app.services import magento_graphql_service as mg
from app.services import platform_router as pr
from app.services import price_service as ps
from app.services import robots_eval
from app.services import search_descriptor_service as sdesc
from app.services import sitemap_discovery_service as sds
from app.services import source_router as sr
from app.services import structured_comparison_service as scs

REPO = Path(__file__).resolve().parents[1]
MR_NAME = "app.services.merchant_registry"
RR_NAME = "app.services.robots_registry"
KB_NAME = "app.services.kb_service"
SEED_NAME = "scripts.seed_kb_merchants"
CRON_NAME = "scripts.cron_robots_registry"
FIXTURE = REPO / "tests" / "fixtures" / "s81_s15_robots_record.json"
NOW = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)
DECODE_COLUMNS = {"host", "status", "deny", "blocked_reason", "registry", "partner"}

_FLAGS = (
    "ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_ROBOTS_REGISTRY_CRON", "ENABLE_DATA_GUARDS_V2",
    "ENABLE_LONGEST_HOST_MATCH", "ENABLE_BH_GCC_CATALOG_SOURCES", "ENABLE_WALL_SIGNATURE_ANCHOR",
    "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_SEARCH_DESCRIPTOR", "SCRAPEDO_SUPER", "BH_GCC_FANOUT_K",
)
_KNOBS = (
    "MERCHANT_REGISTRY_MEMO_SECONDS", "MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS",
    "MERCHANT_REGISTRY_MAX_STALE_SECONDS", "ROBOTS_CRON_MAX_HOSTS", "ROBOTS_CHALLENGE_PARK_DAYS",
)
FALSY = ("unset", "", "false", "0", "off", "no", "FALSE ")
TRUTHY = ("TRUE", " on ", "1", "Yes", "true")


# ---------------------------------------------------------------------------
# absent-safe access (RED rows assert, never raise)
# ---------------------------------------------------------------------------

def _mod(name):
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        return None
    return importlib.import_module(name)


def _need_mod(name):
    m = _mod(name)
    assert m is not None, "%s is missing (S81-15 change list)" % name
    return m


def _need(owner, attr):
    m = _need_mod(owner) if isinstance(owner, str) else owner
    v = getattr(m, attr, None)
    assert v is not None, "%s.%s is missing (S81-15 contract)" % (getattr(m, "__name__", m), attr)
    return v


def _g(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _run(coro_or_value):
    if asyncio.iscoroutine(coro_or_value):
        return asyncio.run(coro_or_value)
    return coro_or_value


def _setflag(monkeypatch, name, value):
    if value == "unset":
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


# ---------------------------------------------------------------------------
# the S81-14 kb_service merchant contract (transcribed from GREEN 0910e7d0; used only when absent)
# ---------------------------------------------------------------------------

_KB_MERCHANT_COLUMNS = (
    "host", "country", "currency_hint", "platform", "platform_confidence", "adapter",
    "search_template", "registry", "robots", "politeness", "health", "challenge", "tos",
    "deny", "status", "blocked_reason", "partner", "created_at", "updated_at",
)
_KB_HOST_REGEX = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?([.][a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"


def _make_kb_stub():
    m = types.ModuleType(KB_NAME)
    m.KB_COLUMNS = {"kb_merchants": _KB_MERCHANT_COLUMNS}
    m.KB_BUILDER_KEYS = {"kb_merchants": tuple(c for c in _KB_MERCHANT_COLUMNS if c != "created_at")}
    m.KB_MERCHANT_STATUS = ("candidate", "live", "blocked")
    m.KB_PLATFORM_CONFIDENCE = ("mechanism", "probe", "url", "operator")
    m.KB_REGISTRY_ORIGINS = ("literal", "catalog", "operator", "discovery")
    m.KB_HOST_REGEX = _KB_HOST_REGEX

    def _json_ok(value, kind):
        if not isinstance(value, kind):
            return False
        try:
            json.dumps(value, allow_nan=False)
            return True
        except (TypeError, ValueError):
            return False

    def _opt_len(value, lo, hi):
        return value is None or (isinstance(value, str) and lo <= len(value) <= hi)

    def _registry_ok(value):
        if not _json_ok(value, list):
            return False
        for entry in value:
            if not isinstance(entry, dict):
                return False
            if entry.get("origin") not in m.KB_REGISTRY_ORIGINS:
                return False
            order = entry.get("order")
            if not (isinstance(order, int) and not isinstance(order, bool)) or order < 0:
                return False
        return True

    def build_merchant_row(*, host, updated_at, country=None, currency_hint=None, platform=None,
                           platform_confidence=None, adapter=None, search_template=None, registry=None,
                           robots=None, politeness=None, health=None, challenge=None, tos=None,
                           deny=False, status="candidate", blocked_reason=None, partner=None):
        try:
            registry = [] if registry is None else registry
            objs = {k: ({} if v is None else v) for k, v in (
                ("robots", robots), ("politeness", politeness), ("health", health),
                ("challenge", challenge), ("tos", tos), ("partner", partner))}
            upd = (updated_at.isoformat() if isinstance(updated_at, datetime)
                   and updated_at.utcoffset() is not None else None)
            ok = (
                isinstance(host, str) and re.match(_KB_HOST_REGEX, host) is not None
                and (country is None or (isinstance(country, str) and re.match(r"^[A-Z]{2,3}$", country)))
                and (currency_hint is None or (isinstance(currency_hint, str)
                                               and re.match(r"^[A-Z]{3}$", currency_hint)))
                and _opt_len(platform, 1, 32)
                and (platform_confidence is None or platform_confidence in m.KB_PLATFORM_CONFIDENCE)
                and _opt_len(adapter, 1, 64) and _opt_len(search_template, 1, 1024)
                and _registry_ok(registry) and all(_json_ok(v, dict) for v in objs.values())
                and isinstance(deny, bool) and status in m.KB_MERCHANT_STATUS
                and _opt_len(blocked_reason, 1, 64) and (not deny or status == "blocked")
                and (status != "blocked" or blocked_reason is not None) and upd is not None
            )
            if not ok:
                return None
            return dict(host=host, country=country, currency_hint=currency_hint, platform=platform,
                        platform_confidence=platform_confidence, adapter=adapter,
                        search_template=search_template, registry=registry, deny=deny, status=status,
                        blocked_reason=blocked_reason, updated_at=upd, **objs)
        except Exception:
            return None

    m._registry_ok = _registry_ok
    m.build_merchant_row = build_merchant_row
    m.__s15_stub__ = True
    return m


@pytest.fixture
def kb(monkeypatch):
    real = _mod(KB_NAME)
    if real is not None:
        return real
    stub = _make_kb_stub()
    monkeypatch.setitem(sys.modules, KB_NAME, stub)
    import app.services as _pkg
    monkeypatch.setattr(_pkg, "kb_service", stub, raising=False)
    return stub


# ---------------------------------------------------------------------------
# fixtures: a clean environment per row; the B1 full configuration for PIN rows
# ---------------------------------------------------------------------------

class Recorder:
    def __init__(self):
        self.calls = []


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for n in _FLAGS + _KNOBS:
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setattr(sr, "_ROUTABLE_MEMO", None)
    monkeypatch.setattr(scs, "_BH_LOCALE_KNOWN_DOMAINS", None)
    try:
        from app.services import scrapedo_service as _sd
        _sd.reset_super_flags_cache()
    except Exception:  # noqa: BLE001
        _sd = None
    mr = _mod(MR_NAME)
    if mr is not None and hasattr(mr, "_reset_for_tests"):
        mr._reset_for_tests()
    yield
    if mr is not None and hasattr(mr, "_reset_for_tests"):
        mr._reset_for_tests()
    if _sd is not None:
        _sd.reset_super_flags_cache()


@pytest.fixture
def full_config(monkeypatch):
    monkeypatch.setenv("ENABLE_ROBOTS_REGISTRY_CRON", "true")
    monkeypatch.setenv("MERCHANT_REGISTRY_MEMO_SECONDS", "300")
    monkeypatch.setenv("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "900")
    monkeypatch.setenv("ROBOTS_CRON_MAX_HOSTS", "3")
    monkeypatch.setenv("ROBOTS_CHALLENGE_PARK_DAYS", "2")
    monkeypatch.setenv("SUPABASE_URL", "https://" + "unit-s15.supabase.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "unit-s15-" + "synthetic")
    rec = Recorder()

    def _admin(*a, **k):
        rec.calls.append("admin")
        raise ValueError("synthetic: no client in this row")

    monkeypatch.setattr(dbs, "get_admin_supabase_client", _admin)
    mr = _mod(MR_NAME)
    if mr is not None and hasattr(mr, "_admin_client"):
        monkeypatch.setattr(mr, "_admin_client", _admin)
    rec.admin = _admin
    return rec


# ---------------------------------------------------------------------------
# the in-memory Supabase client (records table / select / filters / range / execute / writes)
# ---------------------------------------------------------------------------

class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table):
        self.c = client
        self.tname = table
        self.cols = None
        self.filters = []
        self.rng = None
        self.op = "select"
        self.payload = None

    def select(self, cols="*", **kw):
        self.cols = cols
        self.c.calls.append(("select", self.tname, cols))
        return self

    def insert(self, rows, **kw):
        self.op, self.payload = "insert", rows
        self.c.calls.append(("insert", self.tname, len(rows) if isinstance(rows, list) else 1))
        return self

    def upsert(self, rows, **kw):
        self.op, self.payload = "upsert", rows
        self.c.calls.append(("upsert", self.tname, len(rows) if isinstance(rows, list) else 1))
        return self

    def update(self, payload, **kw):
        self.op, self.payload = "update", payload
        self.c.calls.append(("update", self.tname))
        return self

    def delete(self, **kw):
        self.op = "delete"
        self.c.calls.append(("delete", self.tname))
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        self.c.calls.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self.filters.append(("neq", col, val))
        self.c.calls.append(("neq", col, val))
        return self

    def in_(self, col, vals):
        vals = tuple(vals)
        self.filters.append(("in", col, vals))
        self.c.calls.append(("in_", col, tuple(sorted(vals))))
        return self

    def is_(self, col, val):
        self.filters.append(("is", col, val))
        self.c.calls.append(("is_", col, val))
        return self

    def range(self, a, b):
        self.rng = (a, b)
        self.c.calls.append(("range", a, b))
        return self

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _m(*a, **k):
            self.c.calls.append((name,) + tuple(a))
            return self
        return _m

    def _match(self, row):
        for kind, col, val in self.filters:
            have = row.get(col)
            if kind == "eq" and have != val:
                return False
            if kind == "neq" and have == val:
                return False
            if kind == "in" and have not in val:
                return False
            if kind == "is" and str(val).lower() in ("null", "none") and have is not None:
                return False
        return True

    def _project(self, row):
        if not self.cols or self.cols.strip() == "*":
            return copy.deepcopy(row)
        keep = [c.strip() for c in self.cols.split(",") if c.strip()]
        return {k: copy.deepcopy(row.get(k)) for k in keep}

    def execute(self):
        c = self.c
        c.calls.append(("execute", self.tname))
        c.exec_threads.append(threading.get_ident())
        c.n_exec += 1
        if c.delay:
            time.sleep(c.delay)
        if c.raise_exc is not None and (c.raise_on_exec_n is None or c.raise_on_exec_n == c.n_exec):
            raise c.raise_exc
        with c.lock:
            if self.op == "select":
                if c.data_override is not None:
                    return FakeResult(copy.deepcopy(c.data_override))
                rows = [r for r in c.rows if self._match(r)]
                if self.rng is not None:
                    rows = rows[self.rng[0]: self.rng[1] + 1]
                out = [self._project(r) for r in rows]
                for r in c.rows:
                    if r.get("host") in c.bump_on_read:
                        r["updated_at"] = "2099-01-01T00:00:00+00:00"
                return FakeResult(out)
            if self.op == "update":
                hit = [r for r in c.rows if self._match(r)]
                for r in hit:
                    r.update(copy.deepcopy(self.payload))
                c.updates.append((copy.deepcopy(self.payload), list(self.filters), len(hit)))
                return FakeResult(copy.deepcopy(hit))
            if self.op in ("insert", "upsert"):
                rows = self.payload if isinstance(self.payload, list) else [self.payload]
                c.inserts.append(copy.deepcopy(rows))
                c.rows.extend(copy.deepcopy(rows))
                return FakeResult(copy.deepcopy(rows))
            return FakeResult([])


class FakeClient:
    def __init__(self, rows=None):
        self.rows = copy.deepcopy(list(rows or []))
        self.calls = []
        self.exec_threads = []
        self.updates = []
        self.inserts = []
        self.delay = 0.0
        self.raise_exc = None
        self.raise_on_exec_n = None
        self.n_exec = 0
        self.data_override = None
        self.bump_on_read = set()
        self.lock = threading.Lock()
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        self.calls.append(("table", name))
        return FakeQuery(self, name)

    from_ = table

    def writes(self):
        return [c for c in self.calls if c[0] in ("insert", "upsert", "update", "delete")]

    def row(self, host):
        for r in self.rows:
            if r.get("host") == host:
                return r
        return None


class SyntheticPostgrestError(Exception):
    pass


class Clock:
    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t


# ---------------------------------------------------------------------------
# registry helpers
# ---------------------------------------------------------------------------

def _json_rows():
    return json.loads((REPO / "data" / "bh_gcc_sources.json").read_text(encoding="utf-8"))


def _src(domain, tier="bahrain", categories=("fragrances",), weight=1.0, **kw):
    return sr.Source(domain, tier, tuple(categories), weight, **kw)


def _entry(src, order, origin):
    return _need(MR_NAME, "source_to_entry")(src, order, origin)


def _krow(host, entries, status="live", deny=False, blocked_reason=None, partner=None, **extra):
    row = {
        "host": host, "country": None, "currency_hint": None, "platform": None, "platform_confidence": None,
        "adapter": None, "search_template": None, "registry": entries, "robots": {}, "politeness": {},
        "health": {}, "challenge": {}, "tos": {}, "deny": deny, "status": status,
        "blocked_reason": blocked_reason, "partner": partner if partner is not None else {},
        "created_at": "2026-10-23T00:00:00+00:00", "updated_at": "2026-10-23T00:00:00+00:00",
    }
    row.update(extra)
    return row


def _newshop_row(origin="operator", order=100000, partner=None, tier="bahrain", status="live"):
    src = _src("newshop.test", tier=tier, categories=("fragrances",), weight=1.0, currency="BHD")
    return _krow("newshop.test", [_entry(src, order, origin)], status=status, partner=partner)


def _seed_rows(kb):
    mr = _need_mod(MR_NAME)
    return _need(mr, "build_seed_rows")(list(sr._LITERAL_ROWS), _json_rows(), NOW)


def _install(monkeypatch, client, clock=None):
    mr = _need_mod(MR_NAME)
    assert hasattr(mr, "_admin_client"), "merchant_registry._admin_client seam is missing"
    monkeypatch.setattr(mr, "_admin_client", lambda: client)
    if clock is not None:
        assert hasattr(mr, "_monotonic"), "merchant_registry._monotonic seam is missing"
        monkeypatch.setattr(mr, "_monotonic", clock)
    return mr


def _refresh(mr):
    return asyncio.run(_need(mr, "refresh_merchant_registry")())


def _selection():
    return _need(sr, "registry_rows")()


def _lookup():
    return _need(sr, "registry_lookup_rows")()


def _domains(rows):
    return [s.domain for s in rows]


def _mr_records(caplog, level=None):
    out = [r for r in caplog.records if "[MERCHANT_REGISTRY]" in str(r.msg)]
    if level is not None:
        out = [r for r in out if r.levelno == level]
    return out


def _new_tasks(before):
    cur = asyncio.current_task()
    return [t for t in asyncio.all_tasks() if t not in before and t is not cur]


# ---------------------------------------------------------------------------
# the consumer snapshot (flag OFF base literals are its sha256 digests, measured at 98d85433)
# ---------------------------------------------------------------------------

_CATS = ("electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fragrances",
         "fashion", "other")
_SELECTORS = (
    "get_sources_for_category", "get_shopify_sources_for_category", "get_algolia_sources_for_category",
    "get_jsonapi_sources_for_category", "get_curl_pagescrape_sources_for_category",
    "get_sitemap_sources_for_category", "get_woo_sources_for_category", "get_salla_sources_for_category",
    "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
    "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
    "get_noon_sources_for_category", "get_gcc_shopify_pagescrape_sources_for_category",
)
_URLS = ("https://www.sephora.com/p/x", "https://bh.asgharali.com/p/1", "https://www.fragrantica.com/perfume/x",
         "https://www.noon.com/bahrain-en/x", "https://uae.sharafdg.com/p/1", "https://newshop.test/p/1",
         "https://shop.unknown.test/p/1")
_HOSTS = ("noon.com", "www.noon.com", "uae.sharafdg.com", "sephora.com", "fragrantica.com",
          "bh.asgharali.com", "bn.boots.com", "newshop.test", "shop.unknown.test")


def _consumer_snapshot():
    out = {}
    for fn in _SELECTORS:
        f = getattr(sr, fn)
        out[fn] = {c: [s.domain for s in f(c)] for c in _CATS}
    out["score_source"] = {u: {c: sr.score_source(u, c) for c in ("fragrances", "electronics")} for u in _URLS}
    out["source_usage"] = {u: sr.source_usage(u, "fragrances") for u in _URLS}
    out["registry_tier"] = {h: sr.registry_tier(h) for h in _HOSTS}
    out["match_registry_apex"] = {h: sr.match_registry_apex(h) for h in _HOSTS}
    out["is_render_only_domain"] = {h: sr.is_render_only_domain(h) for h in _HOSTS}
    out["build_site_discovery_query"] = {
        "%s|%s" % (c, t): sr.build_site_discovery_query("dior sauvage", c, tier=t)
        for c in ("fragrances", "electronics") for t in ("bahrain", "gcc", "global")
    }
    d = sdesc.descriptor_for_host("bh.jashanmal.com")
    out["descriptor"] = None if d is None else repr(d)
    out["curl_timeout"] = {u: ps._curl_timeout_for_url(u) for u in _URLS}
    out["registry_domains"] = cs._registry_domains()
    out["expected_currency"] = {h: mg._expected_currency_for(h) for h in
                                ("en-kwt.ajmal.com", "footlocker.com.bh", "extra.com", "newshop.test")}
    return out


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


#: sha256 of ``_consumer_snapshot()`` at base 98d85433, registry = the 44 literal rows (the CI catalog-OFF
#: state), keyed (ENABLE_DATA_GUARDS_V2, ENABLE_LONGEST_HOST_MATCH). Recorded by the RED probe.
BASE_SNAPSHOT_DIGEST = {
    ("off", "off"): "e1ee4e7f39e418e6753fad386ca4be6978e5e340343dd4d952f652aa3bb140c0",
    ("off", "on"): "e1ee4e7f39e418e6753fad386ca4be6978e5e340343dd4d952f652aa3bb140c0",
    ("on", "off"): "4f3b8ae3ce4401d758701a07c68257fe35f5f572ce9f5951651abd7e8d884f4b",
    ("on", "on"): "4f3b8ae3ce4401d758701a07c68257fe35f5f572ce9f5951651abd7e8d884f4b",
}
#: readable members of the same base snapshot (catalog OFF, both D03 states).
BASE_FRAG_DOMAINS_D03_OFF = json.dumps([
    "gcc.luluhypermarket.com", "nasserpharmacy.com", "boutiqaat.com", "bh.asgharali.com", "en-bh.ajmal.com",
    "alhajisbahrain.com", "jalilaperfumes.com", "bahrain.ounass.com", "noon.com", "noon.com", "amazon.ae",
    "ounass.com", "tryano.com", "sayidaty.net", "khaleejtimes.com", "gulfnews.com", "amazon.com",
    "sephora.com", "walmart.com", "fragrantica.com",
])


def _pin_literal_registry(monkeypatch):
    reg = list(sr._LITERAL_ROWS)
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", reg)
    monkeypatch.setattr(sr, "_ROUTABLE_MEMO", None)
    return reg


def _prime_fresh(monkeypatch, kb, extra_rows=(), clock=None):
    """GREEN only: load a DB list that differs from the code registry (newshop.test, a partner) into the memo
    with the flag ON, then leave the flag to the caller. No-op at base (the module is absent)."""
    mr = _mod(MR_NAME)
    if mr is None or not hasattr(mr, "refresh_merchant_registry"):
        return None
    rows = list(_seed_rows(kb)) + [_newshop_row(partner={"label": "Sponsored", "cta": "visit"})] + list(extra_rows)
    client = FakeClient(rows)
    monkeypatch.setattr(mr, "_admin_client", lambda: client)
    monkeypatch.setattr(mr, "_monotonic", clock or Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    asyncio.run(mr.refresh_merchant_registry())
    monkeypatch.delenv("ENABLE_MERCHANT_REGISTRY_DB", raising=False)
    return client


# ===========================================================================
# flags and knobs (2.1, R-S15-7)
# ===========================================================================

@pytest.mark.parametrize("value", TRUTHY + ("unset",) + FALSY[1:] + ("garbage",))
def test_r1_db_flag_reader(monkeypatch, value):
    reader = _need(MR_NAME, "merchant_registry_db_enabled")
    _setflag(monkeypatch, "ENABLE_MERCHANT_REGISTRY_DB", value)
    assert reader() is (value in TRUTHY)


@pytest.mark.parametrize("raw,want", [
    ("unset", 600.0), ("", 600.0), ("abc", 600.0), ("nan", 600.0), ("inf", 600.0), ("-5", 600.0),
    ("0", 600.0), ("60", 300.0), ("5000", 900.0), (" 450 ", 450.0), ("600", 600.0),
])
def test_r2_memo_seconds_knob(monkeypatch, raw, want):
    knob = _need(MR_NAME, "memo_seconds")
    _setflag(monkeypatch, "MERCHANT_REGISTRY_MEMO_SECONDS", raw)
    assert knob() == want


@pytest.mark.parametrize("name,fn,raw,want", [
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "unset", 5.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "abc", 5.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "nan", 5.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "inf", 5.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "0", 5.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "0.2", 1.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", "99", 30.0),
    ("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "read_timeout_seconds", " 7 ", 7.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "unset", 3600.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "garbage", 3600.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "-1", 3600.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "inf", 3600.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "10", 900.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "999999", 21600.0),
    ("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "max_stale_seconds", "1800", 1800.0),
])
def test_r2b_read_timeout_and_max_stale_knobs(monkeypatch, name, fn, raw, want):
    knob = _need(MR_NAME, fn)
    _setflag(monkeypatch, name, raw)
    assert knob() == want


@pytest.mark.parametrize("fn,raw,want", [
    ("max_hosts_per_run", "unset", 500), ("max_hosts_per_run", "0", 500), ("max_hosts_per_run", "abc", 500),
    ("max_hosts_per_run", "9999", 5000), ("max_hosts_per_run", "7", 7), ("max_hosts_per_run", "-3", 500),
    ("challenge_park_days", "unset", 7), ("challenge_park_days", "0", 7), ("challenge_park_days", "99", 30),
    ("challenge_park_days", "3", 3), ("challenge_park_days", "x", 7),
])
def test_r3_cron_knobs(monkeypatch, fn, raw, want):
    knob = _need(RR_NAME, fn)
    env = "ROBOTS_CRON_MAX_HOSTS" if fn == "max_hosts_per_run" else "ROBOTS_CHALLENGE_PARK_DAYS"
    _setflag(monkeypatch, env, raw)
    assert knob() == want


@pytest.mark.parametrize("value", TRUTHY + ("unset",) + FALSY[1:] + ("garbage",))
def test_r3b_cron_flag_reader(monkeypatch, value):
    reader = _need(RR_NAME, "robots_registry_cron_enabled")
    _setflag(monkeypatch, "ENABLE_ROBOTS_REGISTRY_CRON", value)
    assert reader() is (value in TRUTHY)


# ===========================================================================
# PIN rows: flag OFF identity (2.9, R-S15-1, R-S15-8) with the FULL configuration
# ===========================================================================

@pytest.mark.parametrize("falsy", FALSY)
@pytest.mark.parametrize("lhm", ("off", "on"))
@pytest.mark.parametrize("d03", ("off", "on"))
def test_p1_flag_off_consumers_identical(monkeypatch, full_config, kb, d03, lhm, falsy):
    """Flag OFF (each falsy spelling): every consumer equals the base literal (a digest of the whole consumer
    snapshot), even with a FRESH primed memo holding a different DB list (GREEN: newshop.test + a partner;
    kills M1b and an ungated partner_for_host); the admin-client recorder stays empty."""
    _prime_fresh(monkeypatch, kb)
    monkeypatch.setattr(dbs, "get_admin_supabase_client", full_config.admin)
    mr = _mod(MR_NAME)
    if mr is not None and hasattr(mr, "_admin_client"):
        monkeypatch.setattr(mr, "_admin_client", full_config.admin)
    _pin_literal_registry(monkeypatch)
    _setflag(monkeypatch, "ENABLE_MERCHANT_REGISTRY_DB", falsy)
    if d03 == "on":
        monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", "true")
    if lhm == "on":
        monkeypatch.setenv("ENABLE_LONGEST_HOST_MATCH", "true")
    snap = _consumer_snapshot()
    assert _digest(snap) == BASE_SNAPSHOT_DIGEST[(d03, lhm)]
    if d03 == "off":
        assert snap["get_sources_for_category"]["fragrances"] == json.loads(BASE_FRAG_DOMAINS_D03_OFF)
    if mr is not None and hasattr(mr, "partner_for_host"):
        assert mr.partner_for_host("newshop.test") is None
    assert full_config.calls == []


def test_p2_flag_off_object_identity(monkeypatch, full_config):
    before_reg, before_lit = sr.SOURCE_REGISTRY, sr._LITERAL_ROWS
    members = list(sr.SOURCE_REGISTRY)
    assert sr._routable_registry() is sr.SOURCE_REGISTRY
    for _ in range(5):
        _consumer_snapshot()
    assert sr._routable_registry() is sr.SOURCE_REGISTRY
    assert sr.SOURCE_REGISTRY is before_reg and sr._LITERAL_ROWS is before_lit
    assert all(a is b for a, b in zip(sr.SOURCE_REGISTRY, members)) and len(members) == len(sr.SOURCE_REGISTRY)
    assert len(sr._LITERAL_ROWS) == 44
    for name in ("registry_rows", "registry_lookup_rows"):
        fn = getattr(sr, name, None)
        if fn is not None:
            assert fn() is sr.SOURCE_REGISTRY
    assert full_config.calls == []


def test_p3_flag_off_no_task_in_a_running_loop(monkeypatch, full_config, kb, caplog):
    """Inside a running loop with an EXPIRED primed memo (GREEN), flag OFF: 20 consumer calls create no task,
    read nothing and log nothing (kills M1: the flag read skipped)."""
    clock = Clock(1000.0)
    _prime_fresh(monkeypatch, kb, clock=clock)
    clock.t = 1000.0 + 10_000.0
    monkeypatch.setattr(dbs, "get_admin_supabase_client", full_config.admin)
    mr = _mod(MR_NAME)
    if mr is not None and hasattr(mr, "_admin_client"):
        monkeypatch.setattr(mr, "_admin_client", full_config.admin)
    caplog.set_level(logging.DEBUG)
    caplog.clear()

    async def body():
        before = set(asyncio.all_tasks())
        for _ in range(4):
            sr.get_sources_for_category("fragrances")
            sr.registry_tier("noon.com")
            sr.score_source("https://www.sephora.com/p/x", "fragrances")
            ps._curl_timeout_for_url("https://bh.asgharali.com/p/1")
            cs._registry_domains()
        await asyncio.sleep(0)
        assert _new_tasks(before) == []

    asyncio.run(body())
    assert _mr_records(caplog) == []
    assert full_config.calls == []


def test_p4_bh_locale_set_untouched():
    tree = ast.parse((REPO / "app/services/structured_comparison_service.py").read_text(encoding="utf-8"))
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_bh_locale_known_retail_domains"]
    assert len(fn) == 1
    names = {n.id for n in ast.walk(fn[0]) if isinstance(n, ast.Name)}
    names |= {a.name for n in ast.walk(fn[0]) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert {"SOURCE_REGISTRY", "_CATALOG_DATA_PATH"} <= names


def _adapter_files():
    keys = ("shopify", "woo", "salla", "magento", "algolia", "noon", "unbxd", "occ", "rest_json", "bolo",
            "boutiqaat", "nasser", "iherb")
    return sorted(p for p in (REPO / "app/services").glob("*.py") if any(k in p.name for k in keys))


def test_p5_live_fetchers_read_no_robots_registry():
    allowed = {"app/services/robots_registry.py", "app/services/merchant_registry.py"}
    hits = []
    for p in sorted((REPO / "app").rglob("*.py")):
        rel = p.relative_to(REPO).as_posix()
        if rel in allowed:
            continue
        if "robots_registry" in p.read_text(encoding="utf-8", errors="replace"):
            hits.append(rel)
    assert hits == []
    files = [REPO / "app/services/price_service.py", REPO / "app/services/url_extraction_service.py",
             REPO / "app/services/shopify_pdp_service.py"] + _adapter_files()
    assert len(files) >= 6
    assert [p.name for p in files if "kb_merchants" in p.read_text(encoding="utf-8", errors="replace")] == []


def test_p6_scoring_never_reads_partner():
    for rel in ("app/services/scoring_service.py", "app/services/response_builder.py",
                "app/services/structured_comparison_service.py"):
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add(n.module or "")
                mods |= {a.name for a in n.names}
        assert not any("merchant_registry" in m for m in mods), rel
        consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        assert "partner" not in consts, rel


#: The base answers for the denied fragrantica row (measured at 98d85433; the review's probe_fragrantica).
FRAG_LINK = "https://www.fragrantica.com/bh-en/perfume/x"
FRAG_BASE = {
    "off": {"ev": False, "reason": ["global_tier"], "tier": "global", "harvest": [False, False], "valid": True},
    "on": {"ev": False, "reason": ["denied_host"], "tier": None, "harvest": [True, False], "valid": False},
}


def _frag_answers():
    r = []
    ev = ps._shopping_bh_host_evidence(FRAG_LINK, ask_currency="BHD", reason_out=r)
    return {"ev": ev, "reason": r, "tier": sr.registry_tier("fragrantica.com"),
            "harvest": list(scs._organic_host_bh_gcc_retail("fragrantica.com", "/bh-en/perfume/x")),
            "valid": ps.validate_scrape_url(FRAG_LINK)}


@pytest.mark.parametrize("d03", ("off", "on"))
def test_p7_fragrantica_base_answers(monkeypatch, full_config, d03):
    """R-S15-1 base half (PIN): the denied fragrantica literal keeps its base answers with the flag OFF."""
    if d03 == "on":
        monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", "true")
    assert _frag_answers() == FRAG_BASE[d03]
    assert full_config.calls == []


SEPHORA_LINK = "https://www.sephora.com/bh-en/p/x"


def _sephora_answers():
    r = []
    ev = ps._shopping_bh_host_evidence(SEPHORA_LINK, ask_currency="BHD", reason_out=r)
    cand = {"source_method": "page_scrape_jsonld",
            "raw_data": {"source_method": "page_scrape_jsonld", "retailer": "sephora.com"}}
    return {"ev": ev, "reason": r, "tier": sr.registry_tier("sephora.com"),
            "downgrade_tier": scs.registry_tier(SEPHORA_LINK),
            "genuine": ps._is_genuine_bh_candidate(cand),
            "harvest": list(scs._organic_host_bh_gcc_retail("sephora.com", "/bh-en/p/x"))}


SEPHORA_BASE = {"ev": False, "reason": ["global_tier"], "tier": "global", "downgrade_tier": "global",
                "genuine": False, "harvest": [False, False]}


def test_p8_sephora_global_refusals_at_base(full_config):
    """R-S15-1 base half (PIN): the global-tier refusals a cron block must not switch off."""
    assert _sephora_answers() == SEPHORA_BASE
    assert full_config.calls == []


# ===========================================================================
# the accessors (2.3, 2.8, R-S15-1)
# ===========================================================================

def test_r4_accessors_identity_off_and_source_gains_deny(monkeypatch):
    sel = _need(sr, "registry_rows")
    look = _need(sr, "registry_lookup_rows")
    for falsy in FALSY:
        _setflag(monkeypatch, "ENABLE_MERCHANT_REGISTRY_DB", falsy)
        assert sel() is sr.SOURCE_REGISTRY
        assert look() is sr.SOURCE_REGISTRY
    fields = {f.name: f for f in dataclasses.fields(sr.Source)}
    assert "deny" in fields and fields["deny"].default is False
    assert "status" in fields
    assert [f.name for f in dataclasses.fields(sr.Source)][:19] == [
        "domain", "tier", "categories", "weight", "usage", "is_shopify", "is_render_only", "is_algolia",
        "requires_super", "locale_paths", "subdomain_patterns", "currency", "discovery_query_templates",
        "mechanism", "pdp_url_pattern", "sample_url", "status", "priority_rank", "search_descriptor"]
    assert not any(s.deny for s in sr.SOURCE_REGISTRY)
    assert {s.status for s in sr._LITERAL_ROWS} <= {"", "live", "provider-test-candidate", "render-only"}


def test_r5_on_before_refresh_serves_code_registry(monkeypatch, full_config):
    mr = _need_mod(MR_NAME)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    assert _selection() is sr.SOURCE_REGISTRY
    assert _lookup() is sr.SOURCE_REGISTRY
    assert sr._routable_registry() is sr.SOURCE_REGISTRY
    assert full_config.calls == []
    assert _need(mr, "partner_for_host")("newshop.test") is None


def test_r6_single_flight_refresh_off_loop_with_status_filter(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    _pin_literal_registry(monkeypatch)
    base_frag = _domains(sr.get_sources_for_category("fragrances"))
    rows = list(_seed_rows(kb)) + [_newshop_row()]
    client = FakeClient(rows)
    client.delay = 0.05
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    loop_thread = threading.get_ident()

    async def body():
        before = set(asyncio.all_tasks())
        first = _domains(sr.get_sources_for_category("fragrances"))
        assert first == base_frag
        made = _new_tasks(before)
        assert len(made) == 1
        for _ in range(9):
            sr.get_sources_for_category("fragrances")
        assert len(_new_tasks(before)) == 1
        await asyncio.gather(*made)
        assert "newshop.test" in _domains(sr.get_sources_for_category("fragrances"))

    asyncio.run(body())
    assert client.tables == ["kb_merchants"]
    selects = [c for c in client.calls if c[0] == "select"]
    assert len(selects) == 1
    cols = {c.strip() for c in selects[0][2].split(",")}
    assert DECODE_COLUMNS <= cols <= DECODE_COLUMNS | {"updated_at"}
    assert ("in_", "status", ("blocked", "live")) in client.calls
    assert [c for c in client.calls if c[0] == "range"] == [("range", 0, 499)]
    assert [c for c in client.calls if c[0] == "execute"] == [("execute", "kb_merchants")]
    assert client.exec_threads and all(t != loop_thread for t in client.exec_threads)
    assert client.writes() == []


def test_r6b_paged_read(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    rows = []
    for i in range(1200):
        h = "shop%04d.test" % i
        rows.append(_krow(h, [_entry(_src(h), 100000 + i, "operator")]))
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert [c for c in client.calls if c[0] == "range"] == [("range", 0, 499), ("range", 500, 999),
                                                            ("range", 1000, 1499)]
    sel = _selection()
    assert len([s for s in sel if s.domain.endswith(".test")]) == 1200
    client2 = FakeClient(rows)
    client2.raise_exc = SyntheticPostgrestError("synthetic page failure")
    client2.raise_on_exec_n = 2
    mr._reset_for_tests()
    _install(monkeypatch, client2, Clock(1000.0))
    _refresh(mr)
    assert _selection() is sr.SOURCE_REGISTRY


@pytest.mark.parametrize("catalog", ("off", "on"))
@pytest.mark.parametrize("d03", ("off", "on"))
def test_r7_on_routes_operator_rows_in_both_catalog_states(monkeypatch, kb, catalog, d03):
    mr = _need_mod(MR_NAME)
    if catalog == "on":
        monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    if d03 == "on":
        monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", "true")
    client = FakeClient(list(_seed_rows(kb)) + [_newshop_row(origin="operator")])
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert "newshop.test" in _domains(sr.get_sources_for_category("fragrances"))
    assert sr.registry_tier("newshop.test") == "bahrain"
    assert ps._curl_timeout_for_url("https://newshop.test/p/1") == ps.BH_REGISTRY_CURL_TIMEOUT


@pytest.mark.parametrize("catalog", ("off", "on"))
def test_r8_record_equality(monkeypatch, kb, catalog):
    mr = _need_mod(MR_NAME)
    if catalog == "on":
        monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    cat = sr._load_catalog_rows() if catalog == "on" else []
    expected = [s for s in list(sr._LITERAL_ROWS) + cat if not deny_hosts.is_denied_host(s.domain)]
    assert len(expected) == (318 if catalog == "on" else 43)
    client = FakeClient(_seed_rows(kb))
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    got = _selection()
    assert len(got) == len(expected)
    for a, b in zip(got, expected):
        assert a == b, (a.domain, b.domain)


def test_r8b_lookup_set_keeps_blocked_and_denied_rows(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    rows = list(_seed_rows(kb))
    for r in rows:
        if r["host"] == "sephora.com":
            r.update(status="blocked", blocked_reason="robots_unreadable")
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    sel, look = _selection(), _lookup()
    assert "sephora.com" not in _domains(sel) and "fragrantica.com" not in _domains(sel)
    seph = [s for s in look if s.domain == "sephora.com"]
    frag = [s for s in look if s.domain == "fragrantica.com"]
    assert len(seph) == 1 and seph[0].status == "blocked" and seph[0].deny is False
    assert len(frag) == 1 and frag[0].deny is True and frag[0].status == "blocked"
    assert set(_domains(sel)) | {"sephora.com", "fragrantica.com"} == set(_domains(look))


def test_r9_entry_round_trip(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    to_entry = _need(mr, "source_to_entry")
    from_entry = _need(sr, "_source_from_entry")
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    sources = list(sr._LITERAL_ROWS) + sr._load_catalog_rows()
    assert len(sources) == 319
    want_keys = ({"order", "origin", "search"}
                 | {f.name for f in dataclasses.fields(sr.Source)} - {"domain", "search_descriptor", "deny"})
    for i, s in enumerate(sources):
        origin = "literal" if i < 44 else "catalog"
        e = to_entry(s, i if i < 44 else 1000 + i, origin)
        assert want_keys <= set(e), sorted(want_keys - set(e))
        e2 = json.loads(json.dumps(e))
        assert kb._registry_ok([e2])
        assert from_entry(s.domain, e2) == s, s.domain
    assert from_entry("bad.test", {"order": 1, "origin": "literal", "weight": "x"}) is None
    assert from_entry("bad.test", "not-a-dict") is None


def test_r10_noon_two_entries(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    rows = _seed_rows(kb)
    noon = [r for r in rows if r["host"] == "noon.com"]
    assert len(noon) == 1 and [e["order"] for e in noon[0]["registry"]] == [23, 24]
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert sr.registry_tier("noon.com") == "gcc"
    noons = sr.get_noon_sources_for_category("fragrances")
    assert [s.tier for s in noons if s.domain == "noon.com"] == ["bahrain"]


def test_r11_blocked_candidate_and_denied_never_selected(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    rows = list(_seed_rows(kb))
    for r in rows:
        if r["host"] == "sephora.com":
            r.update(status="blocked", blocked_reason="robots_unreadable")
        if r["host"] == "bh.asgharali.com":
            r.update(deny=True)
        if r["host"] == "fragrantica.com":
            r.update(status="live", deny=False, blocked_reason=None)
    rows.append(_newshop_row(status="candidate"))
    client = FakeClient(rows)
    client.data_override = copy.deepcopy(rows)  # a server that ignores the filter: the decode is the belt
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    gone = {"sephora.com", "bh.asgharali.com", "fragrantica.com", "newshop.test"}
    assert not gone & set(_domains(_selection()))
    assert not gone & set(_domains(sr.get_sources_for_category("fragrances")))
    q = sr.build_site_discovery_query("dior sauvage", "fragrances", tier="global")
    assert "sephora.com" not in q and "fragrantica.com" not in q


def test_r11b_cron_blocked_global_host_keeps_its_refusals(monkeypatch, kb):
    """R-S15-1: a host that leaves SELECTION keeps its tier and its global-tier refusals (the review's R-1)."""
    mr = _need_mod(MR_NAME)
    rows = list(_seed_rows(kb))
    for r in rows:
        if r["host"] == "sephora.com":
            r.update(status="blocked", blocked_reason="robots_unreadable")
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert "sephora.com" not in _domains(_selection())
    assert "sephora.com" not in _domains(sr.get_sources_for_category("fragrances"))
    assert _sephora_answers() == SEPHORA_BASE


@pytest.mark.parametrize("d03", ("off", "on"))
def test_r11c_fragrantica_flag_on_matches_base(monkeypatch, kb, d03):
    mr = _need_mod(MR_NAME)
    if d03 == "on":
        monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", "true")
    client = FakeClient(_seed_rows(kb))
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert "fragrantica.com" not in _domains(_selection())
    assert _frag_answers() == FRAG_BASE[d03]


def test_r12_catalog_flag_read_at_refresh(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    rows = list(_seed_rows(kb)) + [_newshop_row(origin="discovery", order=200000)]
    client = FakeClient(rows)
    clock = Clock(1000.0)
    _install(monkeypatch, client, clock)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    off = _selection()
    assert len(off) == 44 and "newshop.test" in _domains(off)
    assert "bh.jashanmal.com" not in _domains(off)
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    _refresh(mr)
    on = _selection()
    assert on is not off and len(on) == 319 and "bh.jashanmal.com" in _domains(on)


def test_r13_literal_dedup_from_every_literal_origin_entry(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    rows = [
        _krow("shop.test", [_entry(_src("shop.test"), 1, "literal")]),
        _krow("bh.shop.test", [_entry(_src("bh.shop.test"), 1001, "catalog")]),
        _krow("blocked.test", [_entry(_src("blocked.test"), 2, "literal")], status="blocked",
              blocked_reason="robots_unreadable"),
        _krow("bh.blocked.test", [_entry(_src("bh.blocked.test"), 1002, "catalog")]),
        _krow("other.test", [_entry(_src("other.test"), 1003, "catalog"),
                             _entry(_src("other.test", weight=0.5), 1004, "catalog")]),
        _krow("keep.test", [_entry(_src("keep.test"), 1005, "catalog")]),
    ]
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert _domains(_selection()) == ["shop.test", "other.test", "keep.test"]
    assert [s.weight for s in _selection() if s.domain == "other.test"] == [1.0]


def test_r14_order_independent_of_row_order(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    rows = list(_seed_rows(kb))
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    a = list(_selection())
    shuffled = list(rows)
    random.Random(1515).shuffle(shuffled)
    mr._reset_for_tests()
    _install(monkeypatch, FakeClient(shuffled), Clock(1000.0))
    _refresh(mr)
    assert list(_selection()) == a


@pytest.mark.parametrize("raw,window", [("60", 300.0), ("600", 600.0)])
def test_r15_memo_window(monkeypatch, raw, window):
    mr = _need_mod(MR_NAME)
    client = FakeClient([_newshop_row()])
    clock = Clock(1000.0)
    _install(monkeypatch, client, clock)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    monkeypatch.setenv("MERCHANT_REGISTRY_MEMO_SECONDS", raw)
    _refresh(mr)

    async def body():
        clock.t = 1000.0 + window - 1.0
        before = set(asyncio.all_tasks())
        sr.get_sources_for_category("fragrances")
        assert _new_tasks(before) == []
        clock.t = 1000.0 + window
        sr.get_sources_for_category("fragrances")
        made = _new_tasks(before)
        assert len(made) == 1
        await asyncio.gather(*made)

    asyncio.run(body())


def test_r16_snapshot_keeps_identity_and_sees_unbumped_edits(monkeypatch, kb):
    mr = _need_mod(MR_NAME)
    rows = [_newshop_row(), _krow("two.test", [_entry(_src("two.test"), 100001, "operator")])]
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", "true")
    _refresh(mr)
    first, filt = _selection(), sr._routable_registry()
    _refresh(mr)
    assert _selection() is first
    assert sr._routable_registry() is filt
    client.rows[1]["registry"][0]["weight"] = 0.25
    _refresh(mr)
    second = _selection()
    assert second is not first
    assert [s.weight for s in second if s.domain == "two.test"] == [0.25]
    client.rows[0]["updated_at"] = None
    client.rows[1]["status"] = "blocked"
    client.rows[1]["blocked_reason"] = "owner"
    _refresh(mr)
    assert "two.test" not in _domains(_selection())


def _fail_case(monkeypatch, case):
    mr = _need_mod(MR_NAME)
    client = FakeClient([_newshop_row()])
    if case == "no_client":
        def _raise():
            raise ValueError("synthetic: credentials unset")
        monkeypatch.setattr(mr, "_admin_client", _raise)
        return mr, None, ("ValueError",)
    if case == "execute_raises":
        client.raise_exc = SyntheticPostgrestError("synthetic")
        want = ("SyntheticPostgrestError",)
    elif case == "not_a_list":
        client.data_override = {"rows": 1}
        want = ("not_a_list",)
    elif case == "empty":
        client.rows = []
        want = ("empty",)
    elif case == "all_malformed":
        client.rows = [_krow("bad.test", "not-a-list"), _krow("bad2.test", [{"order": 1, "origin": "literal",
                                                                              "weight": "x"}])]
        want = ("empty",)
    else:
        client.delay = 1.3
        monkeypatch.setenv("MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "1")
        want = ("timeout", "TimeoutError")
    monkeypatch.setattr(mr, "_admin_client", lambda: client)
    return mr, client, want


@pytest.mark.parametrize("case", ("no_client", "execute_raises", "not_a_list", "empty", "all_malformed",
                                  "timeout"))
def test_r17_failures_fall_back_with_one_warning_per_window(monkeypatch, caplog, case):
    mr, client, want = _fail_case(monkeypatch, case)
    clock = Clock(1000.0)
    monkeypatch.setattr(mr, "_monotonic", clock)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    _refresh(mr)
    assert _selection() is sr.SOURCE_REGISTRY
    assert _lookup() is sr.SOURCE_REGISTRY
    warns = _mr_records(caplog, logging.WARNING)
    assert len(warns) == 1
    assert len(warns[0].args) == 1 and warns[0].args[0] in want
    _refresh(mr)
    assert len(_mr_records(caplog, logging.WARNING)) == 1
    clock.t += 600.0
    _refresh(mr)
    assert len(_mr_records(caplog, logging.WARNING)) == 2
    for r in _mr_records(caplog):
        text = r.getMessage()
        assert "newshop" not in text and "bad.test" not in text and "synthetic" not in text


def test_r17b_failed_refresh_keeps_last_good_list_until_max_stale(monkeypatch, caplog):
    mr = _need_mod(MR_NAME)
    client = FakeClient([_newshop_row()])
    clock = Clock(1000.0)
    _install(monkeypatch, client, clock)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    monkeypatch.setenv("MERCHANT_REGISTRY_MAX_STALE_SECONDS", "900")
    _refresh(mr)
    good = _selection()
    assert "newshop.test" in _domains(good)
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    client.raise_exc = SyntheticPostgrestError("synthetic")
    clock.t = 1000.0 + 700.0
    _refresh(mr)
    assert _selection() is good
    assert len(_mr_records(caplog, logging.WARNING)) == 1
    clock.t = 1000.0 + 950.0
    _refresh(mr)
    assert _selection() is sr.SOURCE_REGISTRY
    assert _lookup() is sr.SOURCE_REGISTRY


def test_r18_one_bad_row_or_entry_is_skipped(monkeypatch, caplog):
    mr = _need_mod(MR_NAME)
    good = _newshop_row()
    bad_entry = _entry(_src("half.test"), 100005, "operator")
    bad_entry["weight"] = "x"
    rows = [good, _krow("str.test", "not-a-list"),
            _krow("half.test", [bad_entry, _entry(_src("half.test", weight=0.7), 100006, "operator")])]
    client = FakeClient(rows)
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    caplog.set_level(logging.DEBUG)
    _refresh(mr)
    assert _domains(_selection()) == ["newshop.test", "half.test"]
    infos = [r for r in _mr_records(caplog, logging.INFO) if "skipped" in str(r.msg)]
    assert len(infos) == 1
    assert all(isinstance(a, int) and not isinstance(a, bool) for a in infos[0].args)
    assert "skipped=2" in infos[0].getMessage()


def test_r19_worker_thread_call_schedules_nothing(monkeypatch):
    mr = _need_mod(MR_NAME)
    client = FakeClient([_newshop_row()])
    clock = Clock(1000.0)
    _install(monkeypatch, client, clock)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    stale = _selection()
    clock.t = 1000.0 + 5000.0
    n_exec = client.n_exec
    out = {}

    def worker():
        try:
            out["v"] = sr.registry_rows()
        except Exception as exc:  # noqa: BLE001
            out["e"] = exc

    async def body():
        before = set(asyncio.all_tasks())
        t = threading.Thread(target=worker)
        t.start()
        t.join(10)
        await asyncio.sleep(0)
        assert _new_tasks(before) == []

    asyncio.run(body())
    assert "e" not in out and out["v"] is stale
    assert client.n_exec == n_exec


def test_r20_partner_for_host_gated_and_never_on_a_source(monkeypatch, full_config, kb):
    mr = _need_mod(MR_NAME)
    pfh = _need(mr, "partner_for_host")
    partner = {"label": "Sponsored", "cta": "visit"}
    client = FakeClient([_newshop_row(partner=partner)])
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert pfh("newshop.test") == partner
    assert pfh("unknown.test") is None
    assert "partner" not in {f.name for f in dataclasses.fields(sr.Source)}
    assert all("Sponsored" not in repr(s) for s in _selection())
    monkeypatch.setattr(mr, "_admin_client", full_config.admin)
    monkeypatch.delenv("ENABLE_MERCHANT_REGISTRY_DB", raising=False)
    assert pfh("newshop.test") is None
    assert full_config.calls == []


def test_r20b_rollback_next_call_is_the_code_registry(monkeypatch):
    mr = _need_mod(MR_NAME)
    client = FakeClient([_newshop_row()])
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert "newshop.test" in _domains(sr.get_sources_for_category("fragrances"))
    monkeypatch.delenv("ENABLE_MERCHANT_REGISTRY_DB")
    assert _selection() is sr.SOURCE_REGISTRY and _lookup() is sr.SOURCE_REGISTRY
    assert "newshop.test" not in _domains(sr.get_sources_for_category("fragrances"))


def test_r21_direct_readers_read_the_lookup_accessor(monkeypatch):
    look = _need(sr, "registry_lookup_rows")
    calls = []

    def rec(*a, **k):
        calls.append(1)
        return look(*a, **k)

    monkeypatch.setattr(sr, "registry_lookup_rows", rec)
    ps._curl_timeout_for_url("https://bh.asgharali.com/p/1")
    assert len(calls) == 1
    cs._registry_domains()
    assert len(calls) == 2
    mg._expected_currency_for("unknown-merchant.test")
    assert len(calls) == 3


def test_r21b_blocked_bahrain_host_keeps_its_curl_timeout(monkeypatch):
    mr = _need_mod(MR_NAME)
    blocked = _krow("blockedbh.test", [_entry(_src("blockedbh.test"), 100002, "operator")], status="blocked",
                    blocked_reason="robots_unreadable")
    client = FakeClient([_newshop_row(), blocked])
    _install(monkeypatch, client, Clock(1000.0))
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    _refresh(mr)
    assert ps._curl_timeout_for_url("https://newshop.test/p/1") == ps.BH_REGISTRY_CURL_TIMEOUT
    assert ps._curl_timeout_for_url("https://blockedbh.test/p/1") == ps.BH_REGISTRY_CURL_TIMEOUT
    assert "blockedbh.test" not in _domains(_selection())
    assert "blockedbh.test" in cs._registry_domains()


# ===========================================================================
# the seed (2.7, R-S15-4, R-S15-11, R-S15-13, R-S15-15, R-S15-17)
# ===========================================================================

RESIDENTIAL_HOSTS = ("klinq.com", "nazih.qa", "numberc.com")


def test_r22_seed_rows_counts_and_contract(kb):
    rows = _seed_rows(kb)
    assert len(rows) == 410
    st = {}
    for r in rows:
        st[r["status"]] = st.get(r["status"], 0) + 1
    assert st == {"live": 317, "candidate": 92, "blocked": 1}
    assert sum(len(r["registry"]) for r in rows) == 411
    frag = [r for r in rows if r["host"] == "fragrantica.com"][0]
    assert frag["deny"] is True and frag["status"] == "blocked" and frag["blocked_reason"] == "deny"
    foot = [r for r in rows if r["host"] == "footlocker.com.bh"][0]
    assert [(e["origin"], e["order"]) for e in foot["registry"]] == [("literal", 19)]
    cols = set(kb.KB_COLUMNS["kb_merchants"])
    for r in rows:
        assert set(r) == cols, r["host"]
        assert not {"id", "email", "user", "user_id", "device"} & set(r)
        assert kb._registry_ok(r["registry"]), r["host"]
        call = {k: v for k, v in r.items() if k not in ("created_at",)}
        call["updated_at"] = NOW
        assert kb.build_merchant_row(**call) is not None, r["host"]
    assert len({r["host"] for r in rows}) == 410
    for h in RESIDENTIAL_HOSTS:
        r = [x for x in rows if x["host"] == h][0]
        assert r["status"] == "live"
        assert r["robots"].get("source") == "residential" and r["robots"].get("state") == "allow", h
    dead = {j["domain"] for j in _json_rows() if j["status"] == "dead"} - {"footlocker.com.bh"}
    assert {r["status"] for r in rows if r["host"] in dead} == {"candidate"}


def test_r23_seed_platform_and_ops_columns(kb):
    mr = _need_mod(MR_NAME)
    pfm = _need(mr, "PLATFORM_FOR_MECHANISM")
    assert pfm == {"shopify": "shopify", "woo_store_json": "woocommerce", "salla_api": "salla",
                   "magento_graphql": "magento", "occ_rest": "sap_hybris"}
    rows = {r["host"]: r for r in _seed_rows(kb)}
    js = {j["domain"]: (i, j) for i, j in enumerate(_json_rows())}
    blank_live = 0
    for host, (i, j) in js.items():
        if host == "footlocker.com.bh":
            continue
        r = rows[host]
        mech = j.get("mechanism") or ""
        if mech in pfm:
            assert (r["platform"], r["platform_confidence"]) == (pfm[mech], "mechanism"), host
        else:
            assert (r["platform"], r["platform_confidence"]) == (None, None), host
        if not mech and j["status"] == "live":
            blank_live += 1
        assert r["country"] == j["country"] and r["currency_hint"] == (j.get("currency") or None), host
        assert r["adapter"] == (j.get("genuine_method") or None), host
        want_t = (j.get("search") or {}).get("url_template") or None
        assert r["search_template"] == want_t, host
        assert [(e["origin"], e["order"]) for e in r["registry"]] == [("catalog", 1000 + i)], host
        for col in ("politeness", "health", "challenge", "tos", "partner"):
            assert r[col] == {}, (host, col)
        if host not in RESIDENTIAL_HOSTS:
            assert r["robots"] == {}, host
    assert blank_live == 199
    lit_domains = [x.domain for x in sr._LITERAL_ROWS]
    for i, s in enumerate(sr._LITERAL_ROWS):
        r = rows[s.domain]
        assert r["country"] is None and r["adapter"] is None, s.domain
        if lit_domains.count(s.domain) == 1:
            assert r["currency_hint"] == (s.currency or None), s.domain
        assert ("literal", i) in [(e["origin"], e["order"]) for e in r["registry"]], s.domain


def _upd_items(updates):
    out = []
    for u in updates:
        if isinstance(u, dict):
            out.append((u.get("host"), {k: v for k, v in u.items() if k != "host"}))
        else:
            out.append((u[0], dict(u[1])))
    return out


def test_r24_plan_seed_idempotent_and_non_clobbering(kb):
    mr = _need_mod(MR_NAME)
    plan = _need(mr, "plan_seed")
    owned = set(_need(mr, "SEED_OWNED_COLUMNS"))
    forbidden = {"deny", "status", "blocked_reason", "robots", "challenge", "tos", "partner", "health",
                 "politeness"}
    assert not owned & forbidden
    assert {"registry", "updated_at"} <= owned
    rows = _seed_rows(kb)
    existing = {
        "bh.jashanmal.com": {"host": "bh.jashanmal.com", "platform": "shopify", "deny": True,
                             "status": "blocked", "blocked_reason": "owner"},
        "fragrantica.com": {"host": "fragrantica.com", "platform": None, "deny": False, "status": "live",
                            "blocked_reason": None},
        "en-bh.ajmal.com": {"host": "en-bh.ajmal.com", "platform": None, "deny": False, "status": "live",
                            "blocked_reason": None},
    }
    ins, upd = plan(rows, existing)
    ins2, upd2 = plan(rows, existing)
    assert ins == ins2 and upd == upd2
    assert len(ins) == 407 and {r["host"] for r in ins} == {r["host"] for r in rows} - set(existing)
    byhost = {r["host"]: r for r in rows}
    for r in ins:
        assert set(r) == set(byhost[r["host"]])
    items = dict(_upd_items(upd))
    assert set(items) == set(existing)
    for host, ch in items.items():
        extra = set(ch) - owned - {"platform", "platform_confidence"}
        if host == "fragrantica.com":
            assert extra <= {"deny", "status", "blocked_reason"}
            assert (ch.get("deny"), ch.get("status"), ch.get("blocked_reason")) == (True, "blocked", "deny")
        else:
            assert extra == set(), (host, extra)
        assert ch.get("deny", True) is not False
    assert "platform" not in items["bh.jashanmal.com"]


def _seed_main():
    seed = _need_mod(SEED_NAME)
    return _need(seed, "main")


def test_r25_seed_script_dry_run_writes_nothing_and_apply_batches(kb, capsys):
    main = _seed_main()
    fake = FakeClient([])
    _run(main([], client=fake))
    out = capsys.readouterr().out
    assert "rows=410 live=317 candidate=92 blocked=1 collisions=1 entries=411" in out
    assert fake.writes() == []
    fake2 = FakeClient([])
    _run(main(["--apply"], client=fake2))
    ops = [c[0] for c in fake2.calls if c[0] in ("select", "insert", "upsert", "update")]
    assert ops[0] == "select" and ops.count("select") == 1
    batches = [c[2] for c in fake2.calls if c[0] in ("insert", "upsert")]
    assert batches and all(b <= 100 for b in batches) and sum(batches) == 410
    assert len(fake2.rows) == 410
    rows = _seed_rows(kb)
    pre = {r["host"]: copy.deepcopy(r) for r in rows if r["host"] in ("bh.jashanmal.com", "en-bh.ajmal.com")}
    pre["bh.jashanmal.com"].update(status="blocked", blocked_reason="owner", robots={"state": "allow"})
    pre = list(pre.values())
    fake3 = FakeClient(pre)
    _run(main(["--apply"], client=fake3))
    assert len(fake3.rows) == 410
    j = fake3.row("bh.jashanmal.com")
    assert (j["status"], j["blocked_reason"], j["robots"]) == ("blocked", "owner", {"state": "allow"})


def test_r26_seed_classify_dry_run_and_apply(kb, capsys):
    main = _seed_main()
    rows = list(_seed_rows(kb))
    rows.append(_krow("aaa-preset.test", [_entry(_src("aaa-preset.test"), 100000, "operator")],
                      platform="woocommerce", platform_confidence="operator"))
    seen = []

    async def probe(row):
        seen.append(row["host"])
        return "shopify"

    fake = FakeClient(rows)
    _run(main(["--classify", "20"], client=fake, probe=probe))
    assert len(seen) == 20 and "aaa-preset.test" not in seen
    byhost = {r["host"]: r for r in rows}
    for h in seen:
        r = byhost[h]
        assert r["status"] == "live" and r["platform"] is None
        assert all(not (e.get("mechanism") or "") for e in r["registry"]), h
    assert fake.writes() == []
    out = capsys.readouterr().out
    assert any("shopify" in line and "20" in line for line in out.splitlines())
    seen.clear()
    fake2 = FakeClient(rows)
    _run(main(["--classify", "3", "--apply"], client=fake2, probe=probe))
    assert len(seen) == 3 and len(fake2.updates) == 3
    for payload, filters, n in fake2.updates:
        assert set(payload) <= {"platform", "platform_confidence", "updated_at"}
        assert payload.get("platform") == "shopify" and payload.get("platform_confidence") == "probe"


def test_r26b_seed_records_a_residential_read_by_flag():
    text = (REPO / "scripts" / "seed_kb_merchants.py").read_text(encoding="utf-8") if (
        REPO / "scripts" / "seed_kb_merchants.py").exists() else ""
    assert "--source" in text and "residential" in text and "--classify" in text and "--apply" in text


# ===========================================================================
# robots: decide / crawl-delay / record / challenge (2.5, R-S15-2/3/12)
# ===========================================================================

URL1 = "https://shop.test/products/x"
HTML_HDR = {"Content-Type": "text/html; charset=utf-8"}
TXT_HDR = {"Content-Type": "text/plain"}
CF_PAGE = ("<!DOCTYPE html><html><head><title>Just a moment...</title></head><body>"
           "<script>window._cf_chl_opt={cvId:'3'};</script></body></html>")


def _decide(status, headers, body, urls=(URL1,)):
    return _need(RR_NAME, "decide_robots")(status, headers, body, list(urls))


@pytest.mark.parametrize("anchor", ("off", "on"))
@pytest.mark.parametrize("status,headers,body,urls,state,vendor", [
    (200, TXT_HDR, "User-agent: *\nAllow: /\n", (URL1,), "allow", None),
    (200, TXT_HDR, "User-agent: *\nDisallow: /\n", (URL1,), "disallow", None),
    (200, TXT_HDR, "User-agent: QarenBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n", (URL1,), "disallow", None),
    (200, TXT_HDR, "User-agent: *\nDisallow: /products/\n\nUser-agent: QarenBot\nAllow: /\n", (URL1,),
     "disallow", None),
    (200, TXT_HDR, "User-agent: *\nDisallow: /products/\n", ("https://shop.test/", URL1), "disallow", None),
    (200, TXT_HDR, "User-agent: *\nDisallow: /cart\n", ("https://shop.test/", URL1), "allow", None),
    (404, {}, "", (URL1,), "allow", None),
    (410, {}, "", (URL1,), "allow", None),
    (403, {}, "", (URL1,), "unreadable", None),
    (500, {}, "", (URL1,), "unreadable", None),
    (None, {}, "", (URL1,), "unreadable", None),
    (301, {"Location": "https://www.shop.test/robots.txt"}, "", (URL1,), "unreadable", None),
    (200, HTML_HDR, CF_PAGE, (URL1,), "unreadable", "cloudflare"),
    (200, TXT_HDR, "", (URL1,), "allow", None),
    (200, TXT_HDR, "# access denied to bad bots; you are blocked if you scrape\nUser-agent: *\nDisallow: /admin\n",
     (URL1,), "allow", None),
    (520, {"Server": "cloudflare"}, "", (URL1,), "unreadable", None),
    (403, {"Server": "cloudflare"}, "", (URL1,), "unreadable", None),
    (403, {"CF-Mitigated": "challenge"}, "", (URL1,), "unreadable", "cloudflare"),
])
def test_r27_decide_robots_table(monkeypatch, anchor, status, headers, body, urls, state, vendor):
    if anchor == "on":
        monkeypatch.setenv("ENABLE_WALL_SIGNATURE_ANCHOR", "true")
    v = _decide(status, headers, body, urls)
    assert _g(v, "state") == state
    assert (_g(v, "challenge_vendor") or None) == vendor
    assert _g(v, "status") == status


@pytest.mark.parametrize("body,agent,want", [
    ("User-agent: *\nCrawl-delay: 5\n", "QarenBot", 5.0),
    ("User-agent: QarenBot\nDisallow: /x\nCrawl-delay: 10\nUser-agent: *\nDisallow: /y\nCrawl-delay: 3\n",
     "QarenBot", 10.0),
    ("User-agent: QarenBot\nDisallow: /x\nCrawl-delay: 10\nUser-agent: *\nDisallow: /y\nCrawl-delay: 3\n",
     "*", 3.0),
    ("User-agent: *\nCrawl-delay: abc\n", "QarenBot", None),
    ("User-agent: *\nCrawl-delay: -1\n", "QarenBot", None),
    ("User-agent: *\nCrawl-delay: nan\n", "QarenBot", None),
    ("User-agent: *\nCrawl-delay: inf\n", "QarenBot", None),
    ("User-agent: *\nDisallow: /a\n", "QarenBot", None),
    ("User-agent: *\nCrawl-delay: 999\n", "QarenBot", 60.0),
    ("User-agent: *\nDisallow: /a\nUser-agent: *\nCrawl-delay: 4\n", "*", 4.0),
    ("User-agent: foo\nUser-agent: *\nCrawl-delay: 6\n", "QarenBot", 6.0),
    ("User-agent: *\nCrawl-delay: 2.5\n", "*", 2.5),
])
def test_r28_crawl_delay(body, agent, want):
    assert _need(RR_NAME, "parse_crawl_delay")(body, agent) == want


def test_r28b_verdict_crawl_delay_is_the_max_of_both_groups():
    body = "User-agent: QarenBot\nDisallow: /x\nCrawl-delay: 10\nUser-agent: *\nDisallow: /y\nCrawl-delay: 3\n"
    assert _g(_decide(200, TXT_HDR, body), "crawl_delay") == 10.0
    body2 = "User-agent: QarenBot\nDisallow: /x\nCrawl-delay: 1\nUser-agent: *\nDisallow: /y\nCrawl-delay: 9\n"
    assert _g(_decide(200, TXT_HDR, body2), "crawl_delay") == 9.0


def _fixture():
    assert FIXTURE.exists(), "tests/fixtures/s81_s15_robots_record.json (the D14 contract fixture) is missing"
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_r29_robots_record_is_the_frozen_d14_contract():
    rr = _need_mod(RR_NAME)
    fx = _fixture()
    inp, want = fx["input"], fx["record"]
    assert set(want) == {"state", "status", "body_sha", "fetched_at", "next_reread", "crawl_delay", "origin",
                         "source", "rules", "probed"}
    assert set(want["rules"]) == {"qarenbot", "star"}
    assert want["body_sha"] == hashlib.sha256(inp["body"].encode("utf-8")).hexdigest()
    now = datetime.fromisoformat(inp["now"].replace("Z", "+00:00"))
    v = _decide(inp["status"], inp["headers"], inp["body"], inp["probe_urls"])
    rec = _need(rr, "robots_record")(v, now, inp["origin"], inp["source"])
    assert json.loads(json.dumps(rec)) == want
    fetched = datetime.fromisoformat(rec["fetched_at"].replace("Z", "+00:00"))
    nxt = datetime.fromisoformat(rec["next_reread"].replace("Z", "+00:00"))
    assert nxt - fetched == timedelta(hours=24) and rec["fetched_at"].endswith("Z")


def test_r29b_body_sha_by_status():
    assert _g(_decide(404, {}, ""), "body_sha") == ""
    assert _g(_decide(410, {}, ""), "body_sha") == ""
    assert _g(_decide(403, {}, "denied"), "body_sha") is None
    assert _g(_decide(None, {}, ""), "body_sha") is None
    body = "User-agent: *\nDisallow: /cart\n"
    assert _g(_decide(200, TXT_HDR, body), "body_sha") == hashlib.sha256(body.encode("utf-8")).hexdigest()


def _rebuilt_body(rules):
    lines = ["User-agent: *", "Disallow:"]
    lines += ["%s: %s" % (k.capitalize(), p) for k, p in rules["star"]]
    lines += ["", "User-agent: %s" % robots_eval.NAMED_AGENT, "Disallow:"]
    lines += ["%s: %s" % (k.capitalize(), p) for k, p in rules["qarenbot"]]
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("body", [
    "User-agent: *\nDisallow: /*?sort=\nDisallow: /private$\nAllow: /private/ok\n\nUser-agent: Googlebot\n"
    "Disallow: /\n",
    "User-agent: *\nDisallow: /\n\nUser-agent: QarenBot\nAllow: /products/\nDisallow: /products/secret\n",
    "User-agent: qarenbot\nUser-agent: other\nDisallow: /a\n\nUser-agent: *\nDisallow: /b\n",
])
def test_r29c_stored_rules_answer_per_url_without_a_fetch(body):
    rr = _need_mod(RR_NAME)
    v = _decide(200, TXT_HDR, body, ["https://shop.test/"])
    rec = _need(rr, "robots_record")(v, NOW, "https://shop.test", "datacenter")
    rebuilt = _rebuilt_body(rec["rules"])
    for path in ("/", "/x?sort=1", "/private", "/private/ok", "/privatex", "/a/private", "/products/a",
                 "/products/secret/1", "/a", "/b", "/c"):
        url = "https://shop.test" + path
        for agent in (robots_eval.NAMED_AGENT, "*"):
            assert robots_eval.can_fetch(rebuilt, agent, url) == robots_eval.can_fetch(body, agent, url), (path,
                                                                                                          agent)


def test_r29d_rule_lists_are_capped_at_200():
    rr = _need_mod(RR_NAME)
    body = "User-agent: *\n" + "".join("Disallow: /p%d\n" % i for i in range(300))
    rec = _need(rr, "robots_record")(_decide(200, TXT_HDR, body), NOW, "https://shop.test", "datacenter")
    jrec = json.loads(json.dumps(rec))
    assert len(jrec["rules"]["star"]) == 200 and len(jrec["rules"]["qarenbot"]) <= 200
    assert jrec["rules"]["star"][0] == ["disallow", "/p0"]


@pytest.mark.parametrize("status,headers,body,want", [
    (403, {"CF-Mitigated": "challenge"}, "", "cloudflare"),
    (200, HTML_HDR, CF_PAGE, "cloudflare"),
    (403, {"Server": "AkamaiGHost"}, "<html><body>Access Denied. Reference #18.2c</body></html>", "akamai"),
    (403, {}, "<html><body><h1>Access Denied</h1><p>Reference #18.2c3a</p></body></html>", "akamai"),
    (403, {}, '<html><body><div id="px-captcha"></div></body></html>', "perimeterx"),
    (403, {}, "<html><script src='/_Incapsula_Resource?x=1'></script></html>", "imperva"),
    (403, {}, "<html>INCAP_SES cookie</html>", "imperva"),
    (403, {}, "<html><body>distil_r_captcha</body></html>", "distil"),
    (403, {}, "<html><body>nothing here</body></html>", "unknown"),
])
def test_r30_challenge_vendor(status, headers, body, want):
    assert _need(RR_NAME, "challenge_vendor")(status, headers, body) == want


# ===========================================================================
# the cron: transitions, promotion gates, politeness, SSRF, ordering (2.6, R-S15-2/4/11/12/15/18)
# ===========================================================================

def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _cron_row(host, status="live", sample=None, mechanism="", tos=None, robots=None, challenge=None,
              blocked_reason=None, deny=False, health=None):
    sample = sample if sample is not None else "https://%s/products/x" % host
    entry = {"order": 100000, "origin": "operator", "tier": "bahrain", "categories": ["fragrances"],
             "weight": 1.0, "usage": "price", "is_shopify": mechanism == "shopify", "is_render_only": False,
             "is_algolia": False, "requires_super": False, "locale_paths": [], "subdomain_patterns": [],
             "currency": "BHD", "discovery_query_templates": [], "mechanism": mechanism, "pdp_url_pattern": "",
             "sample_url": sample, "status": "live", "priority_rank": 100, "search": None}
    return _krow(host, [entry], status=status, deny=deny, blocked_reason=blocked_reason,
                 tos=tos if tos is not None else {}, robots=robots if robots is not None else {},
                 challenge=challenge if challenge is not None else {},
                 health=health if health is not None else {})


class Net:
    """The injected fetch / sleep / SSRF seams. ``responses`` maps a URL to (status, headers, body)."""

    def __init__(self, responses=None, refuse=()):
        self.responses = dict(responses or {})
        self.refuse = set(refuse)
        self.fetched = []
        self.kwargs = []
        self.validated = []
        self.sleeps = []
        self.events = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def fetch(self, url, *args, **kwargs):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            self.fetched.append(url)
            headers = kwargs.get("headers", args[0] if args else None)
            self.kwargs.append(dict(kwargs, _headers=headers))
            self.events.append(("fetch", url))
            await asyncio.sleep(0.001)
            return self.responses.get(url, (404, {}, ""))
        finally:
            self.in_flight -= 1

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.events.append(("sleep", seconds))

    async def validate(self, url):
        self.validated.append(url)
        return url not in self.refuse and not any(url.startswith(p) for p in self.refuse)


def _cron(client, net, now=NOW):
    rr = _need_mod(RR_NAME)
    run = _need(rr, "run_cron")
    return asyncio.run(run(client, net.fetch, net.sleep, lambda: now, net.validate))


ALLOW = (200, TXT_HDR, "User-agent: *\nAllow: /\n")
DISALLOW_ALL = (200, TXT_HDR, "User-agent: *\nDisallow: /\n")
BIG_PDP = ("<!DOCTYPE html><html><head><title>Rose Oud 100ml</title></head><body><h1>Rose Oud</h1>"
           "<p>GOODPDP</p>" + "<p>An eau de parfum with a long trail of rose and oud notes.</p>" * 700
           + "</body></html>")


@pytest.fixture
def pdp_gates(monkeypatch):
    rec = types.SimpleNamespace(extract=[], verdict=[], platform="shopify")

    def _extract(html, *a, **k):
        rec.extract.append(1)
        if isinstance(html, str) and "GOODPDP" in html and "NOPRICE" not in html:
            return {"amount": 12.5, "currency": "BHD", "source_method": "page_scrape_jsonld"}
        return None

    def _verdict(html, url="", robots_txt="", *a, **k):
        rec.verdict.append(1)
        return pr.PlatformVerdict(rec.platform, "unknown")

    def _detect(html, url="", *a, **k):
        rec.verdict.append(1)
        return rec.platform

    monkeypatch.setattr(ps, "extract_price_from_html", _extract)
    monkeypatch.setattr(pr, "detect_platform_verdict", _verdict)
    monkeypatch.setattr(pr, "detect_platform", _detect)
    return rec


def _upd(client, host):
    return [p for p, filters, n in client.updates if ("eq", "host", host) in filters]


def test_r31_transitions(monkeypatch):
    nru = _need(RR_NAME, "next_row_update")
    monkeypatch.setenv("ROBOTS_CHALLENGE_PARK_DAYS", "2")
    allow, dis = _decide(*ALLOW), _decide(*DISALLOW_ALL)
    unr, chal = _decide(403, {}, ""), _decide(200, HTML_HDR, CF_PAGE)

    def after(row, v):
        u = nru(row, v, NOW) or {}
        merged = dict(row)
        merged.update(u)
        return merged

    live = _cron_row("a.test")
    r = after(live, allow)
    assert r["status"] == "live" and r.get("blocked_reason") is None and r["robots"]["state"] == "allow"
    for v, reason in ((dis, "robots_disallow"), (unr, "robots_unreadable"), (chal, "challenge")):
        r = after(live, v)
        assert (r["status"], r["blocked_reason"]) == ("blocked", reason)
        assert r["health"].get("pre_block_status") == "live"
    r = after(live, chal)
    assert r["challenge"]["vendor"] == "cloudflare"
    assert r["challenge"]["parked_until"] == _iso(NOW + timedelta(days=2))
    blocked = _cron_row("b.test", status="blocked", blocked_reason="robots_unreadable",
                        health={"pre_block_status": "live"}, challenge={"vendor": "cloudflare",
                                                                        "parked_until": _iso(NOW)})
    r = after(blocked, allow)
    assert (r["status"], r.get("blocked_reason"), r["challenge"]) == ("live", None, {})
    legacy = _cron_row("e.test", status="blocked", blocked_reason="robots_unreadable",
                       health={"pre_block_status": "candidate"})
    r = after(legacy, allow)
    assert (r["status"], r.get("blocked_reason")) == ("candidate", None)
    still = _cron_row("c.test", status="blocked", blocked_reason="robots_disallow",
                      health={"pre_block_status": "live"})
    r = after(still, dis)
    assert (r["status"], r["blocked_reason"], r["robots"]["state"]) == ("blocked", "robots_disallow", "disallow")
    cand = _cron_row("d.test", status="candidate")
    r = after(cand, dis)
    assert r["status"] == "candidate" and r.get("blocked_reason") is None
    assert r["health"]["promotion"]["failing_gate"] == "robots"
    r = after(cand, chal)
    assert r["status"] == "candidate" and r["challenge"]["parked_until"] == _iso(NOW + timedelta(days=2))


def test_r31b_residential_verdict_is_never_downgraded_by_the_datacenter(monkeypatch):
    young = {"state": "allow", "status": 200, "source": "residential", "fetched_at": _iso(NOW - timedelta(days=2)),
             "next_reread": _iso(NOW - timedelta(days=1)), "origin": "https://res.test"}
    old = dict(young, fetched_at=_iso(NOW - timedelta(days=40)), next_reread=_iso(NOW - timedelta(days=39)))
    client = FakeClient([_cron_row("res.test", robots=young), _cron_row("old.test", robots=old)])
    net = Net({"https://res.test/robots.txt": (403, {}, ""), "https://old.test/robots.txt": (403, {}, "")})
    _cron(client, net)
    r = client.row("res.test")
    assert r["status"] == "live" and r["robots"]["state"] == "allow" and r["robots"]["source"] == "residential"
    assert isinstance(r["health"].get("last_datacenter_result"), dict) and r["health"]["last_datacenter_result"]
    o = client.row("old.test")
    assert (o["status"], o["blocked_reason"]) == ("blocked", "robots_unreadable")


@pytest.mark.parametrize("case", ("pass", "tos_missing", "walled_pdp", "platform_unknown", "robots_disallow",
                                  "no_price", "search_url"))
def test_r32_promotion_gates(monkeypatch, pdp_gates, case):
    monkeypatch.setenv("ROBOTS_CHALLENGE_PARK_DAYS", "2")
    sample = "https://cand.test/products/rose-oud"
    tos = {"verdict": "allowed", "reviewed_at": "2026-10-20T00:00:00Z"}
    robots = ALLOW
    pdp = (200, HTML_HDR, BIG_PDP)
    if case == "tos_missing":
        tos = {}
    elif case == "walled_pdp":
        pdp = (200, HTML_HDR, CF_PAGE)
    elif case == "platform_unknown":
        pdp_gates.platform = "unknown"
    elif case == "robots_disallow":
        robots = (200, TXT_HDR, "User-agent: *\nDisallow: /products/\n")
    elif case == "no_price":
        pdp = (200, HTML_HDR, BIG_PDP.replace("GOODPDP", "GOODPDP NOPRICE"))
    elif case == "search_url":
        sample = "https://cand.test/search?q=rose"
    client = FakeClient([_cron_row("cand.test", status="candidate", sample=sample, tos=tos)])
    net = Net({"https://cand.test/robots.txt": robots, sample: pdp})
    _cron(client, net)
    r = client.row("cand.test")
    if case == "pass":
        assert r["status"] == "live" and r["platform"] == "shopify" and r["platform_confidence"] == "probe"
        assert "promotion" not in (r.get("health") or {})
        assert pdp_gates.extract and pdp_gates.verdict
        return
    gate = {"tos_missing": "tos", "walled_pdp": "pdp", "platform_unknown": "platform",
            "robots_disallow": "robots", "no_price": "pdp", "search_url": "pdp"}[case]
    assert r["status"] == "candidate" and r.get("blocked_reason") is None
    assert r["health"]["promotion"]["failing_gate"] == gate
    assert r["health"]["promotion"]["checked_at"] == _iso(NOW)
    if case in ("tos_missing", "robots_disallow", "search_url"):
        assert net.fetched == ["https://cand.test/robots.txt"]
    if case == "walled_pdp":
        assert r["challenge"]["parked_until"] == _iso(NOW + timedelta(days=2))


def test_r32b_adapter_path_joins_the_probe_set(monkeypatch):
    client = FakeClient([_cron_row("shopa.test", mechanism="shopify")])
    net = Net({"https://shopa.test/robots.txt": (200, TXT_HDR, "User-agent: *\nDisallow: /products.json\n")})
    _cron(client, net)
    r = client.row("shopa.test")
    assert (r["status"], r["blocked_reason"]) == ("blocked", "robots_disallow")
    assert {"/", "/products/x"} <= set(r["robots"]["probed"])


def _cron_main():
    cron = _need_mod(CRON_NAME)
    return cron, _need(cron, "main")


def test_r33_cron_flag_off_does_nothing(monkeypatch, full_config, caplog):
    cron, main = _cron_main()
    rr = _need_mod(RR_NAME)
    called = []

    async def _no(*a, **k):
        called.append(1)
        return {}

    monkeypatch.setattr(rr, "run_cron", _no)
    for falsy in FALSY:
        _setflag(monkeypatch, "ENABLE_ROBOTS_REGISTRY_CRON", falsy)
        caplog.set_level(logging.DEBUG)
        caplog.clear()
        assert _run(main()) is None
        infos = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(infos) == 1
    assert called == [] and full_config.calls == []


def test_r34_cron_is_sequential_polite_and_named(monkeypatch, pdp_gates, caplog):
    rows = [_cron_row("h1.test"), _cron_row("h2.test"), _cron_row("h3.test"),
            _cron_row("h4.test", status="candidate", tos={"verdict": "allowed"})]
    net = Net({
        "https://h1.test/robots.txt": (200, TXT_HDR, "User-agent: *\nDisallow: /cart\nCrawl-delay: 5\n"),
        "https://h2.test/robots.txt": ALLOW,
        "https://h3.test/robots.txt": ALLOW,
        "https://h4.test/robots.txt": (200, TXT_HDR, "User-agent: *\nDisallow: /cart\nCrawl-delay: 7\n"),
        "https://h4.test/products/x": (200, HTML_HDR, BIG_PDP),
    })
    client = FakeClient(rows)
    caplog.set_level(logging.DEBUG)
    _cron(client, net)
    assert net.max_in_flight == 1
    assert net.fetched == ["https://h1.test/robots.txt", "https://h2.test/robots.txt",
                           "https://h3.test/robots.txt", "https://h4.test/robots.txt", "https://h4.test/products/x"]
    assert net.sleeps == [2.0, 2.0, 2.0, 7.0]
    assert net.events[0][0] == "fetch"
    ua = _need(robots_eval, "QARENBOT_UA")
    for kw in net.kwargs:
        assert (kw["_headers"] or {}).get("User-Agent") == ua
        assert kw.get("allow_redirects") is False
        assert "impersonate" not in kw
    assert sorted({h for p, f, n in client.updates for k, c, h in f if k == "eq" and c == "host"}) == [
        "h1.test", "h2.test", "h3.test", "h4.test"]
    assert len(client.updates) == 4
    per = [r for r in caplog.records if "[ROBOTS_CRON]" in str(r.msg) and r.levelno == logging.INFO
           and isinstance(r.args, tuple) and len(r.args) == 2]
    assert sorted(a[0] for a in (r.args for r in per)) == ["h1.test", "h2.test", "h3.test", "h4.test"]
    for r in caplog.records:
        if "[ROBOTS_CRON]" in str(r.msg):
            assert "://" not in r.getMessage()


def test_r34b_redirects_followed_by_hand_with_ssrf_on_every_hop():
    hop = {"https://r.test/robots.txt": (301, {"Location": "https://www.r.test/robots.txt"}, ""),
           "https://www.r.test/robots.txt": (200, TXT_HDR, "User-agent: *\nDisallow: /\n")}
    chain = {"https://long.test/robots.txt": (302, {"Location": "https://long.test/r1"}, "")}
    for i in range(1, 7):
        chain["https://long.test/r%d" % i] = (302, {"Location": "https://long.test/r%d" % (i + 1)}, "")
    bad = {"https://ssrf.test/robots.txt": (302, {"Location": "http://169.254.169.254/latest"}, "")}
    client = FakeClient([_cron_row("r.test"), _cron_row("long.test"), _cron_row("ssrf.test")])
    net = Net(dict(hop, **chain, **bad), refuse=("http://169.254.169.254",))
    _cron(client, net)
    assert "https://www.r.test/robots.txt" in net.validated and "https://r.test/robots.txt" in net.validated
    assert all(kw.get("allow_redirects") is False for kw in net.kwargs)
    r = client.row("r.test")
    assert (r["status"], r["blocked_reason"]) == ("blocked", "robots_disallow")
    assert r["robots"]["origin"] == "https://r.test"
    lg = client.row("long.test")
    assert (lg["status"], lg["blocked_reason"]) == ("blocked", "robots_unreadable")
    assert len([u for u in net.fetched if u.startswith("https://long.test")]) <= 6
    s = client.row("ssrf.test")
    assert (s["status"], s["blocked_reason"]) == ("blocked", "ssrf_redirect")
    assert "http://169.254.169.254/latest" not in net.fetched


def test_r34c_robots_is_read_from_the_probe_origin():
    client = FakeClient([_cron_row("wwwshop.test", sample="https://www.wwwshop.test/products/x"),
                         _cron_row("redtag.test", mechanism="shopify",
                                   sample="https://rtplus.myshopify.test/products.json")])
    net = Net({"https://www.wwwshop.test/robots.txt": ALLOW})
    _cron(client, net)
    assert "https://www.wwwshop.test/robots.txt" in net.fetched
    w = client.row("wwwshop.test")
    assert w["robots"]["origin"] == "https://www.wwwshop.test" and w["status"] == "live"
    rt = client.row("redtag.test")
    assert "https://rtplus.myshopify.test" in (rt["robots"].get("other_origins") or [])


def test_r35_ssrf_refusal_and_sticky_rows_are_not_fetched():
    rows = [
        _cron_row("ssrf0.test"),
        _cron_row("deny.test", status="blocked", deny=True, blocked_reason="deny"),
        _cron_row("fragrantica.com"),
        _cron_row("owner.test", status="blocked", blocked_reason="owner"),
        _cron_row("tos.test", status="blocked", blocked_reason="tos"),
    ]
    client = FakeClient(rows)
    net = Net({}, refuse=("https://ssrf0.test",))
    _cron(client, net)
    assert net.fetched == []
    s = client.row("ssrf0.test")
    assert s["status"] == "blocked" and s["blocked_reason"] in ("robots_unreadable", "ssrf_redirect")
    for h in ("deny.test", "fragrantica.com", "owner.test", "tos.test"):
        assert _upd(client, h) == [], h
    assert client.row("fragrantica.com")["status"] == "live"


def test_r36_run_bound_due_order_parked_and_not_due(monkeypatch):
    monkeypatch.setenv("ROBOTS_CRON_MAX_HOSTS", "3")
    rr_ = lambda d: {"state": "allow", "next_reread": _iso(NOW + timedelta(days=d)), "source": "datacenter"}
    rows = [
        _cron_row("a.test"), _cron_row("b.test", robots=rr_(-3)), _cron_row("c.test", robots=rr_(-1)),
        _cron_row("d.test", robots=rr_(-2)), _cron_row("e.test"), _cron_row("f.test", robots=rr_(1)),
        _cron_row("g.test", status="blocked", blocked_reason="challenge",
                  challenge={"vendor": "cloudflare", "parked_until": _iso(NOW + timedelta(days=1))},
                  robots=rr_(-5)),
    ]
    client = FakeClient(rows)
    net = Net({"https://%s.test/robots.txt" % h: ALLOW for h in "abcdefg"})
    _cron(client, net)
    assert net.fetched == ["https://a.test/robots.txt", "https://e.test/robots.txt", "https://b.test/robots.txt"]


def test_r36b_cron_updates_are_conditional_and_a_lost_race_is_skipped(caplog):
    client = FakeClient([_cron_row("race.test"), _cron_row("ok.test")])
    seen = {r["host"]: r["updated_at"] for r in client.rows}
    client.bump_on_read = {"race.test"}
    net = Net({"https://race.test/robots.txt": DISALLOW_ALL, "https://ok.test/robots.txt": DISALLOW_ALL})
    caplog.set_level(logging.DEBUG)
    _cron(client, net)
    for payload, filters, n in client.updates:
        hosts = [v for k, c, v in filters if k == "eq" and c == "host"]
        assert len(hosts) == 1
        assert ("eq", "updated_at", seen[hosts[0]]) in filters
    assert client.row("race.test")["status"] == "live"
    assert client.row("ok.test")["status"] == "blocked"
    assert any("race.test" in r.getMessage() for r in caplog.records)


# ===========================================================================
# module shape: light import, hygiene, the UA, the D9 pin, Railway, no app importer
# ===========================================================================

def test_r37_registry_modules_import_light():
    code = ("import sys; sys.path.insert(0, %r)\n"
            "import app.services.robots_registry, app.services.merchant_registry\n"
            "bad = [m for m in ('app.services.price_service', 'app.services.extraction_service',"
            " 'app.services.database_service', 'app.services.kb_service', 'app.services.structured_comparison_service')"
            " if m in sys.modules]\n"
            "print('HEAVY=' + ','.join(bad))\n") % str(REPO)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ENABLE_", "SUPABASE", "OPENAI", "SERPER", "UPSTASH", "BRIGHTDATA"))}
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                          cwd=str(REPO), env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert proc.stdout.strip().splitlines()[-1] == "HEAVY="


_LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical"}


def _hygiene_problems(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            parents[ch] = node
    exc_names = {h.name for h in ast.walk(tree) if isinstance(h, ast.ExceptHandler) and h.name}
    probs = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "impersonate":
                probs.append("impersonate at line %d" % node.lineno)
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr in _LOG_METHODS and isinstance(f.value, ast.Name)
                and "log" in f.value.id.lower()):
            continue
        if not node.args or not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            probs.append("non-constant log format at line %d" % node.lineno)
        for a in node.args[1:]:
            if isinstance(a, ast.JoinedStr):
                probs.append("f-string log arg at line %d" % node.lineno)
            if isinstance(a, ast.Name) and a.id in exc_names:
                probs.append("exception text logged at line %d" % node.lineno)
            if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id in ("str", "repr", "format"):
                probs.append("str()/repr() log arg at line %d" % node.lineno)
        for kw in node.keywords:
            if kw.arg in ("exc_info", "stack_info") and not (isinstance(kw.value, ast.Constant)
                                                             and kw.value.value in (False, None)):
                probs.append("exc_info at line %d" % node.lineno)
        if f.attr in ("error", "exception", "critical"):
            p, inside = parents.get(node), False
            while p is not None:
                if isinstance(p, ast.ExceptHandler):
                    inside = True
                    break
                p = parents.get(p)
            if not inside:
                probs.append("ERROR outside an except arm at line %d" % node.lineno)
    return probs


def test_r38_no_impersonation_and_log_hygiene():
    for rel in ("app/services/robots_registry.py", "app/services/merchant_registry.py",
                "scripts/cron_robots_registry.py", "scripts/seed_kb_merchants.py"):
        p = REPO / rel
        assert p.exists(), rel
        assert _hygiene_problems(p) == [], rel
        raw = p.read_bytes()
        assert not any(b > 127 for b in raw) and b"\r\n" not in raw, rel
        assert "protego" not in raw.decode("ascii").lower(), rel


BASE_UA_SHA256 = "09692ab2fe190ed7a3436c158047e4d84cda320b925821bb0dc47d212f9a974f"


def test_r39_qarenbot_ua_lives_in_robots_eval():
    ua = _need(robots_eval, "QARENBOT_UA")
    assert hashlib.sha256(ua.encode("utf-8")).hexdigest() == BASE_UA_SHA256
    assert sds._ROBOTS_UA is ua
    assert ua.startswith(robots_eval.NAMED_AGENT + "/1.0 ")
    rr = _need_mod(RR_NAME)
    assert _need(rr, "QARENBOT_UA") is ua


def test_p9_base_ua_value(full_config):
    """PIN: the UA bytes the move must keep (sitemap_discovery_service._ROBOTS_UA at base)."""
    assert hashlib.sha256(sds._ROBOTS_UA.encode("utf-8")).hexdigest() == BASE_UA_SHA256


def test_r40_d9_emitter_pin_widened_by_exactly_robots_registry():
    tree = ast.parse((REPO / "tests/test_legal_disclosure_s77.py").read_text(encoding="utf-8"))
    files = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "QARENBOT_FILES" for t in node.targets):
            files = {e.value for e in node.value.elts}
    assert files is not None
    assert files == {"app/services/robots_eval.py", "app/services/search_descriptor_service.py",
                     "app/services/sitemap_discovery_service.py", "scripts/resolve_search_descriptors.py",
                     "app/services/robots_registry.py"}
    rr = REPO / "app/services/robots_registry.py"
    assert rr.exists() and "can_fetch" in rr.read_text(encoding="utf-8")
    for rel in ("app/services/merchant_registry.py", "scripts/seed_kb_merchants.py",
                "scripts/cron_robots_registry.py"):
        p = REPO / rel
        assert p.exists(), rel
        text = p.read_text(encoding="utf-8")
        assert "QarenBot" not in text and "NAMED_AGENT" not in text, rel


def test_r41_railway_robots_cron_config():
    p = REPO / "railway.robots.json"
    assert p.exists()
    cfg = json.loads(p.read_text(encoding="utf-8"))
    assert cfg["deploy"]["startCommand"] == "python -m scripts.cron_robots_registry"
    assert cfg["deploy"]["restartPolicyType"] == "NEVER"
    assert set(cfg["build"]["watchPatterns"]) == {"scripts/cron_robots_registry.py",
                                                  "app/services/robots_registry.py",
                                                  "app/services/robots_eval.py", "railway.robots.json"}
    doc = (REPO / "scripts/cron_robots_registry.py").read_text(encoding="utf-8")
    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "ENABLE_ROBOTS_REGISTRY_CRON", "ROBOTS_CRON_MAX_HOSTS"):
        assert name in doc, name
    assert "railway.robots.json" in doc


def test_r43_scripts_never_imported_by_app_and_exist():
    for rel in ("scripts/seed_kb_merchants.py", "scripts/cron_robots_registry.py"):
        assert (REPO / rel).exists(), rel
    for p in sorted((REPO / "app").rglob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        assert "seed_kb_merchants" not in text and "cron_robots_registry" not in text, p.name

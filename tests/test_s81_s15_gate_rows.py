"""S81-15 REGISTRY-ROBOTS-DENY: the gate-named rows GATE_S81_15 asks GREEN to add.

The RED file ``tests/test_s81_s15_registry_robots.py`` is frozen (sha256 5bb3bc4c...),
so the rows the gate names live here: GC-1 (robots_disallow is cron-managed), GC-2
(the seed wraps kb_service.build_merchant_row; created_at on INSERT only), GC-3
(full Source-field presence against the REAL post-fix S81-14 validator, with the
host argument it takes), GC-4 (the paged read is ordered by host), GC-5 (a
datacenter ALLOW never replaces a young residential record), GC-6 (initial SSRF
refusal = robots_unreadable + health.ssrf 'initial'; a refused hop =
ssrf_redirect), GC-7 (a cross-origin sample: the host row's own robots.txt is the
primary record), GC-8 (the --classify scope) and GC-10 (the PDP gate's product
name is the sanitised page title). Fix round 1 (RULINGS_FIX1_S81_15) adds the
rows named test_f1_<ruling>: the daily cadence and its slack knob (F1-3), a
parent-host sample is another origin (F1-4), the SELECTION half of GC-9 (F1-5),
the production fetch / validate / entry seams (F1-6, F1-11), the deny belt at
every entry point (F1-10), the memo task outside the lock in a fresh context
(F1-12), a resolver failure vs an SSRF refusal (F1-13), the young residential
re-read date (F1-14), the cron read order (F1-16) and the integer knob clamp
(F1-23); gc2, gc6 and gc7 read with .get() (F1-19), gc5 follows F1-14 and gc8 is
widened to every live platform-NULL row (F1-15). Hermetic: an in-memory client,
injected fetch / sleep / SSRF seams (or the production seams over a patched
curl_cffi / socket), the netguard on; hosts are synthetic ``.test`` hosts or the
public registry rows.
"""
from __future__ import annotations

import asyncio
import copy
import dataclasses
import hashlib
import json
import logging
import socket
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest

import app.main  # noqa: F401  (the import-time load_dotenv override runs first)
from app.services import kb_service as kb
from app.services import merchant_registry as mr
from app.services import platform_router as pr
from app.services import price_service as ps
from app.services import robots_eval
from app.services import robots_registry as rr
from app.services import source_router as sr

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)
TXT = {"Content-Type": "text/plain"}
HTML = {"Content-Type": "text/html; charset=utf-8"}
ALLOW = (200, TXT, "User-agent: *\nAllow: /\n")
_FLAGS = ("ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_ROBOTS_REGISTRY_CRON", "ENABLE_DATA_GUARDS_V2",
          "ENABLE_LONGEST_HOST_MATCH", "ENABLE_BH_GCC_CATALOG_SOURCES", "ENABLE_WALL_SIGNATURE_ANCHOR",
          "MERCHANT_REGISTRY_MEMO_SECONDS", "MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS",
          "MERCHANT_REGISTRY_MAX_STALE_SECONDS", "ROBOTS_CRON_MAX_HOSTS", "ROBOTS_CHALLENGE_PARK_DAYS",
          "ROBOTS_DUE_SLACK_SECONDS")


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in _FLAGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sr, "_ROUTABLE_MEMO", None)
    mr._reset_for_tests()
    yield
    mr._reset_for_tests()


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, table):
        self.c, self.table, self.op, self.payload = client, table, "select", None
        self.cols, self.filters, self.rng = "*", [], None

    def select(self, cols="*", **_kw):
        self.cols = cols
        self.c.calls.append(("select", self.table, cols))
        return self

    def update(self, payload, **_kw):
        self.op, self.payload = "update", payload
        self.c.calls.append(("update", self.table))
        return self

    def insert(self, rows, **_kw):
        self.op, self.payload = "insert", rows
        self.c.calls.append(("insert", self.table, len(rows)))
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        self.c.calls.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in", col, tuple(vals)))
        self.c.calls.append(("in_", col, tuple(sorted(vals))))
        return self

    def is_(self, col, val):
        self.filters.append(("is", col, val))
        self.c.calls.append(("is_", col, val))
        return self

    def order(self, col, **_kw):
        self.c.calls.append(("order", col))
        return self

    def range(self, a, b):
        self.rng = (a, b)
        self.c.calls.append(("range", a, b))
        return self

    def _match(self, row):
        for kind, col, val in self.filters:
            have = row.get(col)
            if kind == "eq" and have != val:
                return False
            if kind == "in" and have not in val:
                return False
            if kind == "is" and have is not None:
                return False
        return True

    def execute(self):
        self.c.calls.append(("execute", self.table))
        with self.c.lock:
            if self.op == "select":
                rows = [r for r in self.c.rows if self._match(r)]
                if self.rng is not None:
                    rows = rows[self.rng[0]: self.rng[1] + 1]
                if self.cols.strip() == "*":
                    return _Result(copy.deepcopy(rows))
                keep = [k.strip() for k in self.cols.split(",")]
                return _Result([{k: copy.deepcopy(r.get(k)) for k in keep} for r in rows])
            if self.op == "update":
                hit = [r for r in self.c.rows if self._match(r)]
                for r in hit:
                    r.update(copy.deepcopy(self.payload))
                self.c.updates.append((copy.deepcopy(self.payload), list(self.filters)))
                return _Result(copy.deepcopy(hit))
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            self.c.rows.extend(copy.deepcopy(rows))
            return _Result(copy.deepcopy(rows))


class _Client:
    def __init__(self, rows=()):
        self.rows = copy.deepcopy(list(rows))
        self.calls, self.updates, self.lock = [], [], threading.Lock()

    def table(self, name):
        self.calls.append(("table", name))
        return _Query(self, name)

    def row(self, host):
        return next(r for r in self.rows if r.get("host") == host)


class _Net:
    def __init__(self, responses=None, refuse=()):
        self.responses, self.refuse = dict(responses or {}), tuple(refuse)
        self.fetched, self.kwargs, self.sleeps = [], [], []

    async def fetch(self, url, **kwargs):
        self.fetched.append(url)
        self.kwargs.append(kwargs)
        return self.responses.get(url, (404, {}, ""))

    async def sleep(self, seconds):
        self.sleeps.append(seconds)

    async def validate(self, url):
        return not any(url.startswith(p) for p in self.refuse)


def _entry(host, order=100000, origin="operator", sample=None, mechanism=""):
    src = sr.Source(host, "bahrain", ("fragrances",), 1.0, currency="BHD", mechanism=mechanism,
                    sample_url=sample if sample is not None else "https://%s/products/x" % host,
                    is_shopify=(mechanism == "shopify"))
    return mr.source_to_entry(src, order, origin)


def _row(host, status="live", entries=None, **extra):
    row = {"host": host, "country": None, "currency_hint": "BHD", "platform": None, "platform_confidence": None,
           "adapter": None, "search_template": None, "registry": entries if entries is not None else [_entry(host)],
           "robots": {}, "politeness": {}, "health": {}, "challenge": {}, "tos": {}, "deny": False,
           "status": status, "blocked_reason": None, "partner": {}, "created_at": "2026-10-23T00:00:00+00:00",
           "updated_at": "2026-10-23T00:00:00+00:00"}
    row.update(extra)
    return row


def _cron(client, net):
    return asyncio.run(rr.run_cron(client, net.fetch, net.sleep, lambda: NOW, net.validate))


def _json_rows():
    return json.loads((REPO / "data" / "bh_gcc_sources.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# GC-1
# ---------------------------------------------------------------------------

def test_gc1_robots_disallow_is_a_cron_managed_block_reason():
    assert rr.CRON_REASONS == ("robots_unreadable", "robots_disallow", "challenge", "ssrf_redirect")
    row = _row("dis.test", status="blocked", blocked_reason="robots_disallow",
               health={"pre_block_status": "live"})
    upd = rr.next_row_update(row, rr.decide_robots(*ALLOW, ["https://dis.test/"]), NOW)
    assert (upd["status"], upd["blocked_reason"]) == ("live", None)
    live = _row("dis2.test")
    upd = rr.next_row_update(live, rr.decide_robots(200, TXT, "User-agent: *\nDisallow: /\n",
                                                    ["https://dis2.test/"]), NOW)
    assert (upd["status"], upd["blocked_reason"]) == ("blocked", "robots_disallow")


# ---------------------------------------------------------------------------
# GC-2 / GC-3: the seed against the REAL post-fix kb_service
# ---------------------------------------------------------------------------

def test_gc2_seed_wraps_build_merchant_row_and_created_at_on_insert_only(monkeypatch):
    calls = []
    real = kb.build_merchant_row

    def recorder(**kwargs):
        calls.append(kwargs["host"])
        return real(**kwargs)

    monkeypatch.setattr(kb, "build_merchant_row", recorder)
    rows = mr.build_seed_rows(list(sr._LITERAL_ROWS), _json_rows(), NOW)
    assert len(calls) == len(rows) == 410
    monkeypatch.setattr(kb, "build_merchant_row", real)
    for row in rows:
        assert row.get("created_at") is not None and row.get("created_at") == row.get("updated_at"), row.get(
            "host")
        call = {k: v for k, v in row.items() if k not in ("created_at", "updated_at")}
        assert real(updated_at=NOW, **call) == {k: v for k, v in row.items() if k != "created_at"}, row["host"]
    existing = {"bh.jashanmal.com": {"host": "bh.jashanmal.com", "platform": None, "deny": False,
                                     "status": "live", "blocked_reason": None}}
    inserts, updates = mr.plan_seed(rows, existing)
    assert all("created_at" in r for r in inserts) and len(inserts) == 409
    assert [h for h, _ in updates] == ["bh.jashanmal.com"]
    assert all("created_at" not in payload for _, payload in updates)


def test_gc3_entries_carry_every_source_field_and_pass_the_real_validator(monkeypatch):
    monkeypatch.setenv("ENABLE_BH_GCC_CATALOG_SOURCES", "true")
    sources = list(sr._LITERAL_ROWS) + sr._load_catalog_rows()
    assert len(sources) == 319
    want = {"order", "origin"} | ({f.name for f in dataclasses.fields(sr.Source)} - {"deny"})
    for i, s in enumerate(sources):
        entry = mr.source_to_entry(s, i if i < 44 else 1000 + i, "literal" if i < 44 else "catalog")
        assert set(entry) == want, s.domain
        e2 = json.loads(json.dumps(entry))
        assert kb._registry_ok([e2], s.domain), s.domain
        assert sr._source_from_entry(s.domain, e2) == s, s.domain
    monkeypatch.delenv("ENABLE_BH_GCC_CATALOG_SOURCES")
    for row in mr.build_seed_rows(list(sr._LITERAL_ROWS), _json_rows(), NOW):
        assert kb._registry_ok(row["registry"], row["host"]), row["host"]
        for entry in row["registry"]:
            assert set(entry) == want, row["host"]
    assert sr._source_from_entry("bad.test", dict(_entry("bad.test"), weight="x")) is None
    assert sr._source_from_entry("bad.test", dict(_entry("bad.test"), domain="other.test")) is None


# ---------------------------------------------------------------------------
# GC-4: the paged read is ordered by host
# ---------------------------------------------------------------------------

def test_gc4_paged_read_orders_by_host(monkeypatch):
    rows = [_row("shop%04d.test" % i, entries=[_entry("shop%04d.test" % i, order=100000 + i)])
            for i in range(1200)]
    client = _Client(rows)
    monkeypatch.setattr(mr, "_admin_client", lambda: client)
    monkeypatch.setattr(mr, "_monotonic", lambda: 1000.0)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    asyncio.run(mr.refresh_merchant_registry())
    chain = [c for c in client.calls if c[0] in ("select", "in_", "order", "range", "execute")]
    pages = [chain[i:i + 5] for i in range(0, len(chain), 5)]
    assert len(pages) == 3
    for n, page in enumerate(pages):
        assert [c[0] for c in page] == ["select", "in_", "order", "range", "execute"]
        assert page[2] == ("order", "host") and page[3] == ("range", 500 * n, 500 * n + 499)
    assert len(sr.registry_rows()) == 1200


# ---------------------------------------------------------------------------
# GC-5: a datacenter ALLOW never replaces a young residential record
# ---------------------------------------------------------------------------

def _residential(days_old, state="disallow"):
    at = NOW - timedelta(days=days_old)
    return {"state": state, "status": 200, "source": "residential", "fetched_at": _iso(at),
            "next_reread": _iso(at + timedelta(hours=24)), "origin": "https://res.test",
            "rules": {"qarenbot": [], "star": [["disallow", "/"]]}, "probed": {"/": state}}


def test_gc5_datacenter_allow_never_replaces_a_young_residential_record():
    young = _row("res.test", status="blocked", blocked_reason="robots_disallow",
                 robots=_residential(5), health={"pre_block_status": "live"})
    old = _row("old.test", status="blocked", blocked_reason="robots_disallow",
               robots=dict(_residential(40), origin="https://old.test"), health={"pre_block_status": "live"})
    client = _Client([young, old])
    net = _Net({"https://res.test/robots.txt": ALLOW, "https://old.test/robots.txt": ALLOW})
    _cron(client, net)
    y = client.row("res.test")
    assert (y["status"], y["blocked_reason"]) == ("blocked", "robots_disallow")
    lapse = _iso(NOW - timedelta(days=5) + timedelta(days=30))
    assert y["robots"] == dict(_residential(5), next_reread=lapse)  # F1-14: only next_reread moves
    assert y["health"]["last_datacenter_result"]["state"] == "allow"
    assert y["health"]["pre_block_status"] == "live"
    o = client.row("old.test")
    assert (o["status"], o["blocked_reason"]) == ("live", None)
    assert o["robots"]["source"] == "datacenter" and o["robots"]["state"] == "allow"
    upd = rr.next_row_update(young, rr.decide_robots(*ALLOW, ["https://res.test/"]), NOW)
    assert set(upd) == {"robots", "health", "updated_at"}
    assert upd["robots"] == dict(_residential(5), next_reread=lapse)


# ---------------------------------------------------------------------------
# GC-6: the initial URL vs a hop
# ---------------------------------------------------------------------------

def test_gc6_initial_ssrf_refusal_is_unreadable_and_a_refused_hop_is_ssrf_redirect():
    client = _Client([_row("first.test"), _row("hop.test")])
    net = _Net({"https://hop.test/robots.txt": (302, {"Location": "http://10.0.0.1/robots.txt"}, "")},
               refuse=("https://first.test", "http://10.0.0.1"))
    _cron(client, net)
    f = client.row("first.test")
    assert (f["status"], f["blocked_reason"]) == ("blocked", "robots_unreadable")
    assert (f.get("health") or {}).get("ssrf") == "initial"
    h = client.row("hop.test")
    assert (h["status"], h["blocked_reason"]) == ("blocked", "ssrf_redirect")
    assert (h.get("health") or {}).get("ssrf") == "hop"
    assert net.fetched == ["https://hop.test/robots.txt"]


# ---------------------------------------------------------------------------
# GC-7: one origin per host row
# ---------------------------------------------------------------------------

def test_gc7_cross_origin_sample_reads_the_host_rows_own_robots():
    cross = _row("redtag.test", entries=[_entry("redtag.test", mechanism="shopify",
                                                sample="https://rtplus.myshopify.test/products.json")])
    www = _row("wshop.test", entries=[_entry("wshop.test", sample="https://www.wshop.test/p/1")])
    client = _Client([cross, www])
    net = _Net({"https://redtag.test/robots.txt": ALLOW, "https://www.wshop.test/robots.txt": ALLOW})
    _cron(client, net)
    assert net.fetched == ["https://redtag.test/robots.txt", "https://www.wshop.test/robots.txt"]
    r = client.row("redtag.test").get("robots") or {}
    assert r.get("origin") == "https://redtag.test" and r.get("other_origins") == ["https://rtplus.myshopify.test"]
    assert set(r.get("probed") or {}) == {"/"}
    w = client.row("wshop.test")["robots"]
    assert w["origin"] == "https://www.wshop.test" and "other_origins" not in w
    assert set(w["probed"]) == {"/", "/p/1"}


# ---------------------------------------------------------------------------
# GC-8: the --classify scope
# ---------------------------------------------------------------------------

def test_gc8_classify_scope_is_every_live_platform_null_row_including_literals(capsys):
    seed = pytest.importorskip("scripts.seed_kb_merchants")
    assert seed._parse_args(["--classify"]).classify == 20
    lit = _row("a-literal.test", entries=[_entry("a-literal.test", order=3, origin="literal", sample="")])
    rows = [lit, _row("b-cand.test", status="candidate"), _row("c-set.test", platform="shopify",
                                                               platform_confidence="mechanism"),
            _row("d-mech.test", entries=[_entry("d-mech.test", mechanism="woo_store_json")]),
            _row("e-json.test", entries=[_entry("e-json.test", order=1004, origin="catalog")])]
    seen = []

    async def probe(row):
        seen.append(row["host"])
        return "woocommerce"

    client = _Client(rows)
    assert seed.main(["--classify"], client=client, probe=probe) == 0
    assert seen == ["a-literal.test", "d-mech.test", "e-json.test"]  # F1-15: any mechanism
    assert client.updates == [] and not [c for c in client.calls if c[0] in ("update", "insert")]
    out = capsys.readouterr().out
    assert "eligible=3 probed=3 woocommerce=3" in out


# ---------------------------------------------------------------------------
# GC-10: the PDP gate's product name
# ---------------------------------------------------------------------------

def test_gc10_pdp_gate_product_name_is_the_sanitised_page_title(monkeypatch):
    names = []

    def _extract(html, product_name, *a, **k):
        names.append(product_name)
        return {"amount": 12.5, "currency": "BHD"}

    monkeypatch.setattr(ps, "extract_price_from_html", _extract)
    monkeypatch.setattr(pr, "detect_platform_verdict", lambda *a, **k: pr.PlatformVerdict("shopify", "unknown"))
    page = ("<!DOCTYPE html><html><head><title>  Rose &amp; Oud\n <USER_INPUT> 100ml </title></head><body>"
            + "<p>An eau de parfum with a long trail of rose and oud notes.</p>" * 700 + "</body></html>")
    sample = "https://cand.test/products/rose-oud"
    client = _Client([_row("cand.test", status="candidate", tos={"verdict": "allowed"},
                           entries=[_entry("cand.test", sample=sample)])])
    net = _Net({"https://cand.test/robots.txt": ALLOW, sample: (200, HTML, page)})
    _cron(client, net)
    assert names == ["Rose & Oud [USER_INPUT] 100ml"]
    assert rr.pdp_product_name(page) == names[0]
    assert client.row("cand.test")["status"] == "live"


# ===========================================================================
# Fix round 1 (RULINGS_FIX1_S81_15): rows named after their ruling
# ===========================================================================

def _parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class _Ticker:
    """A fake clock that advances 3 s per read (the correctness adversary's cadence probe)."""

    def __init__(self, start):
        self.t = start

    def __call__(self):
        t = self.t
        self.t = t + timedelta(seconds=3)
        return t


# ---------------------------------------------------------------------------
# F1-3: a daily run re-reads every host the previous daily run read
# ---------------------------------------------------------------------------

def test_f1_3_a_daily_cron_rereads_every_host_every_day():
    knob = getattr(rr, "due_slack_seconds", None)
    assert callable(knob), "robots_registry.due_slack_seconds is missing (F1-3)"
    hosts = ["day%02d.test" % i for i in range(40)]
    client = _Client([_row(h) for h in hosts])
    net = _Net({"https://%s/robots.txt" % h: ALLOW for h in hosts})
    start = datetime(2026, 10, 24, 2, 30, 0, tzinfo=timezone.utc)
    seen = []
    for day in range(3):
        counts = asyncio.run(rr.run_cron(client, net.fetch, net.sleep, _Ticker(start + timedelta(days=day)),
                                         net.validate))
        seen.append((counts.get("due"), counts.get("written")))
    assert seen == [(40, 40), (40, 40), (40, 40)]
    rec = client.row("day39.test").get("robots") or {}
    assert rec.get("next_reread") and rec.get("fetched_at")
    assert _parse(rec["next_reread"]) - _parse(rec["fetched_at"]) == timedelta(hours=24)


@pytest.mark.parametrize("raw,want", [
    (None, 3600.0), ("", 3600.0), ("abc", 3600.0), ("nan", 3600.0), ("inf", 3600.0), ("-1", 3600.0),
    ("0", 0.0), (" 120 ", 120.0), ("99999", 21600.0),
])
def test_f1_3b_due_slack_knob(monkeypatch, raw, want):
    knob = getattr(rr, "due_slack_seconds", None)
    assert callable(knob), "robots_registry.due_slack_seconds is missing (F1-3)"
    if raw is not None:
        monkeypatch.setenv("ROBOTS_DUE_SLACK_SECONDS", raw)
    assert knob() == want


# ---------------------------------------------------------------------------
# F1-4: a sample on a PARENT host of the row is another origin
# ---------------------------------------------------------------------------

def test_f1_4_a_parent_host_sample_is_another_origin():
    row = _row("store1.mall.test", status="candidate",
               entries=[_entry("store1.mall.test", sample="https://mall.test/store1/products/x")])
    client = _Client([row])
    net = _Net({"https://store1.mall.test/robots.txt": ALLOW, "https://mall.test/robots.txt": ALLOW})
    _cron(client, net)
    assert net.fetched == ["https://store1.mall.test/robots.txt"]
    rec = client.row("store1.mall.test").get("robots") or {}
    assert rec.get("origin") == "https://store1.mall.test"
    assert rec.get("other_origins") == ["https://mall.test"]
    assert set(rec.get("probed") or {}) == {"/"}
    parents = []
    for r in mr.build_seed_rows(list(sr._LITERAL_ROWS), _json_rows(), NOW):
        samples = [e.get("sample_url") for e in r["registry"] if isinstance(e, dict) and e.get("sample_url")]
        s_host = (urlsplit(samples[0]).hostname or "") if samples else ""
        if s_host and r["host"].endswith("." + s_host):
            parents.append(r["host"])
            plan = rr.probe_plan(r)
            assert plan.robots_url == "https://%s/robots.txt" % r["host"], r["host"]
            assert plan.other_origins == ["https://" + s_host], r["host"]
    assert sorted(parents) == ["journey1.salla.sa", "parfumdeal.salla.sa", "rose-store-27.salla.sa"]


# ---------------------------------------------------------------------------
# F1-5: score_source / source_usage / is_render_only_domain read SELECTION
# ---------------------------------------------------------------------------

def _prime_cron_blocked(monkeypatch, host):
    """ENABLE_MERCHANT_REGISTRY_DB ON, the memo primed from the seeded table with ``host`` cron-blocked."""
    monkeypatch.setattr(sr, "_LOOKUP_MEMO", None)
    rows = mr.build_seed_rows(list(sr._LITERAL_ROWS), _json_rows(), NOW)
    hits = [r for r in rows if r["host"] == host]
    assert len(hits) == 1, host
    hits[0].update(status="blocked", blocked_reason="robots_unreadable", health={"pre_block_status": "live"})
    client = _Client(rows)
    monkeypatch.setattr(mr, "_admin_client", lambda: client)
    monkeypatch.setattr(mr, "_monotonic", lambda: 1000.0)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")
    asyncio.run(mr.refresh_merchant_registry())
    assert host not in [s.domain for s in sr.registry_rows()]
    assert host in [s.domain for s in sr.registry_lookup_rows()]


def test_f1_5a_score_source_reads_selection_for_a_cron_blocked_host(monkeypatch):
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", list(sr._LITERAL_ROWS))
    url = "https://www.sephora.com/p/x"
    assert sr.score_source(url, "fragrances") == 1.0
    _prime_cron_blocked(monkeypatch, "sephora.com")
    assert sr.score_source(url, "fragrances") == 0.5
    assert sr.registry_tier("sephora.com") == "global"
    assert sr.match_registry_apex("www.sephora.com") == "sephora.com"


def test_f1_5b_source_usage_reads_selection_for_a_cron_blocked_host(monkeypatch):
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", list(sr._LITERAL_ROWS))
    url = "https://www.sayidaty.net/beauty/1"
    assert sr.source_usage(url, "fragrances") == "review"
    _prime_cron_blocked(monkeypatch, "sayidaty.net")
    assert sr.source_usage(url, "fragrances") == "price"
    assert sr.registry_tier("sayidaty.net") == "gcc"
    assert sr.match_registry_apex("www.sayidaty.net") == "sayidaty.net"


def test_f1_5c_is_render_only_domain_reads_selection_for_a_cron_blocked_host(monkeypatch):
    monkeypatch.setattr(sr, "SOURCE_REGISTRY", list(sr._LITERAL_ROWS))
    assert sr.is_render_only_domain("bn.boots.com") is True
    _prime_cron_blocked(monkeypatch, "bn.boots.com")
    assert sr.is_render_only_domain("bn.boots.com") is False
    assert sr.registry_tier("bn.boots.com") == "bahrain"
    assert sr.match_registry_apex("bn.boots.com") == "bn.boots.com"


# ---------------------------------------------------------------------------
# F1-6 / F1-11: the production seams (curl_cffi and socket patched; no network)
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, status, headers, content, encoding="utf-8"):
        self.status_code, self.headers, self.content, self.encoding = status, headers, content, encoding

    @property
    def text(self):
        return self.content.decode(self.encoding, errors="replace")


def test_f1_6a_default_fetch_is_named_unredirected_and_byte_capped(monkeypatch):
    from curl_cffi import requests as cffi_requests

    cap = getattr(rr, "MAX_BODY_BYTES", None)
    assert cap is not None and cap == rr.MAX_BODY_CHARS, "robots_registry.MAX_BODY_BYTES is missing (F1-11)"
    two_bytes = chr(233).encode("utf-8")
    head = b"User-agent: *\n" + b"".join(b"Disallow: /p%d\n" % i for i in range(300))
    body = head + (b"# " + two_bytes * 40 + b"\n") * (cap // 83 + 10)
    assert len(body) > cap
    calls = []

    def _get(url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResp(200, {"Content-Type": "text/plain; charset=utf-8"}, body)

    monkeypatch.setattr(cffi_requests, "get", _get)
    status, headers, text = asyncio.run(rr.default_fetch("https://shop.test/robots.txt", allow_redirects=False))
    assert status == 200 and len(calls) == 1
    url, kw = calls[0]
    assert url == "https://shop.test/robots.txt"
    assert kw.get("allow_redirects") is False
    assert (kw.get("headers") or {}).get("User-Agent") == robots_eval.QARENBOT_UA
    assert "impersonate" not in kw
    want = body[:cap].decode("utf-8", errors="replace")
    assert text == want
    verdict = rr.decide_robots(status, headers, text, ["https://shop.test/"])
    rec = rr.robots_record(verdict, NOW, "https://shop.test", "datacenter")
    assert rec.get("rules_truncated") is True and len(rec["rules"]["star"]) == 200
    assert rec.get("body_sha") == hashlib.sha256(want.encode("utf-8")).hexdigest()


def test_f1_6b_default_validate_refuses_internal_targets_and_accepts_a_public_address(monkeypatch):
    ok, ssrf = getattr(rr, "VALIDATE_OK", None), getattr(rr, "VALIDATE_SSRF", None)
    assert ok is not None and ssrf is not None, "the default_validate reasons are missing (F1-13)"
    table = {"pub.test": "93.184.215.14", "ten.test": "10.0.0.1", "meta.test": "169.254.169.254"}

    def _gai(host, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (table.get(host, host), 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    for url in ("http://10.0.0.1/robots.txt", "http://169.254.169.254/latest/meta-data",
                "http://web.railway.internal/robots.txt", "http://localhost/robots.txt",
                "https://ten.test/robots.txt", "https://meta.test/robots.txt"):
        assert asyncio.run(rr.default_validate(url)) == ssrf, url
    assert asyncio.run(rr.default_validate("https://pub.test/robots.txt")) == ok


def test_f1_6c_cron_entry_wires_the_production_seams(monkeypatch):
    cron = pytest.importorskip("scripts.cron_robots_registry")
    import app.services.database_service as dbs

    seen = []
    sentinel = object()

    async def _run_cron(client, fetch, sleep, now_clock, validate):
        seen.append((client, fetch, sleep, now_clock, validate))
        return {}

    monkeypatch.setattr(rr, "run_cron", _run_cron)
    monkeypatch.setattr(dbs, "get_admin_supabase_client", lambda: sentinel)
    monkeypatch.setenv("ENABLE_ROBOTS_REGISTRY_CRON", "true")
    assert asyncio.run(cron.main()) is None
    assert len(seen) == 1
    client, fetch, sleep, now_clock, validate = seen[0]
    assert client is sentinel
    assert fetch is rr.default_fetch and sleep is asyncio.sleep and now_clock is rr.utc_now
    assert validate is rr.default_validate


# ---------------------------------------------------------------------------
# F1-10: the deny belt at every entry point (no fetch, the refusal recorded)
# ---------------------------------------------------------------------------

def _record_production_seams(monkeypatch):
    calls = {"fetch": [], "validate": []}

    async def _fetch(url, *a, **k):
        calls["fetch"].append(url)
        return (200, TXT, "User-agent: *\nAllow: /\n")

    async def _validate(url):
        calls["validate"].append(url)
        return True

    monkeypatch.setattr(rr, "default_fetch", _fetch)
    monkeypatch.setattr(rr, "default_validate", _validate)
    return calls


def test_f1_10a_residential_read_refuses_a_deny_hosts_host_before_any_fetch(monkeypatch, capsys, caplog):
    seed = pytest.importorskip("scripts.seed_kb_merchants")
    reason = getattr(rr, "DENY_REFUSAL", None)
    assert reason, "robots_registry.DENY_REFUSAL is missing (F1-10)"
    calls = _record_production_seams(monkeypatch)
    client = _Client([_row("fragrantica.com", status="blocked", deny=True, blocked_reason="deny")])
    caplog.set_level(logging.INFO)
    assert seed.main(["--source", "residential", "--hosts", "fragrantica.com", "--apply"], client=client) == 0
    assert calls == {"fetch": [], "validate": []}
    assert client.updates == []
    out = capsys.readouterr().out
    assert "host=fragrantica.com refused=%s" % reason in out
    assert any("refused" in r.getMessage() and "fragrantica.com" in r.getMessage() for r in caplog.records)


def test_f1_10b_classify_refuses_a_deny_hosts_host_before_any_fetch(monkeypatch, capsys, caplog):
    seed = pytest.importorskip("scripts.seed_kb_merchants")
    assert getattr(rr, "DENY_REFUSAL", None), "robots_registry.DENY_REFUSAL is missing (F1-10)"
    calls = _record_production_seams(monkeypatch)
    mis_seeded = _row("fragrantica.com", entries=[_entry("fragrantica.com", order=43, origin="literal")])
    client = _Client([mis_seeded])
    caplog.set_level(logging.INFO)
    assert seed.main(["--classify"], client=client) == 0
    assert calls == {"fetch": [], "validate": []}
    assert client.updates == []
    out = capsys.readouterr().out
    assert "classify refused=1" in out
    assert any("refused" in r.getMessage() and "fragrantica.com" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# F1-12: the memo refresh task: created outside _LOCK, in a fresh context
# ---------------------------------------------------------------------------

class _RecordingLock:
    def __init__(self):
        self._lock = threading.Lock()
        self.held = False

    def __enter__(self):
        self._lock.acquire()
        self.held = True
        return self

    def __exit__(self, *exc):
        self.held = False
        self._lock.release()
        return False

    def acquire(self, *a, **k):
        got = self._lock.acquire(*a, **k)
        if got:
            self.held = True
        return got

    def release(self):
        self.held = False
        self._lock.release()


def test_f1_12_refresh_task_is_created_outside_the_lock_in_a_fresh_context(monkeypatch):
    from app.utils import request_context as rc

    lock = _RecordingLock()
    monkeypatch.setattr(mr, "_LOCK", lock)
    created, inside = [], []

    async def _body():
        inside.append(rc._COMPARE_REQUEST_ID.get())

    def _refresh():
        created.append(lock.held)
        return _body()

    monkeypatch.setattr(mr, "refresh_merchant_registry", _refresh)
    monkeypatch.setenv("ENABLE_MERCHANT_REGISTRY_DB", "true")

    async def _request():
        token = rc._COMPARE_REQUEST_ID.set("req-" + "a" * 8)
        try:
            sr.registry_rows()
            handle = mr._REFRESH
            assert handle is not None
            await handle[1]
        finally:
            rc._COMPARE_REQUEST_ID.reset(token)

    asyncio.run(_request())
    assert created == [False]
    assert inside == [None]


# ---------------------------------------------------------------------------
# F1-13: a resolver failure is unreadable + health.dns, never an SSRF label
# ---------------------------------------------------------------------------

def test_f1_13a_a_resolver_failure_is_unreadable_with_health_dns(monkeypatch):
    def _gai(host, *a, **k):
        raise socket.gaierror("synthetic resolver failure")

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    client = _Client([_row("gone.test")])
    net = _Net({"https://gone.test/robots.txt": ALLOW})
    asyncio.run(rr.run_cron(client, net.fetch, net.sleep, lambda: NOW, rr.default_validate))
    g = client.row("gone.test")
    assert (g.get("status"), g.get("blocked_reason")) == ("blocked", "robots_unreadable")
    health = g.get("health") or {}
    assert health.get("dns") == "unresolved"
    assert "ssrf" not in health
    assert net.fetched == []


def test_f1_13b_a_metadata_address_is_an_initial_ssrf_refusal(monkeypatch):
    def _gai(host, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    client = _Client([_row("meta.test")])
    net = _Net({"https://meta.test/robots.txt": ALLOW})
    asyncio.run(rr.run_cron(client, net.fetch, net.sleep, lambda: NOW, rr.default_validate))
    m = client.row("meta.test")
    assert (m.get("status"), m.get("blocked_reason")) == ("blocked", "robots_unreadable")
    health = m.get("health") or {}
    assert health.get("ssrf") == "initial"
    assert "dns" not in health
    assert net.fetched == []


# ---------------------------------------------------------------------------
# F1-14: a young residential row is next due when its protection lapses
# ---------------------------------------------------------------------------

def test_f1_14_young_residential_row_is_due_when_the_protection_lapses():
    young = _row("res.test", status="blocked", blocked_reason="robots_disallow",
                 robots=_residential(5), health={"pre_block_status": "live"})
    upd = rr.next_row_update(young, rr.decide_robots(*ALLOW, ["https://res.test/"]), NOW) or {}
    robots = upd.get("robots") or {}
    lapse = NOW - timedelta(days=5) + timedelta(days=30)
    assert robots.get("next_reread") == _iso(lapse)
    assert {k: v for k, v in robots.items() if k != "next_reread"} == {
        k: v for k, v in _residential(5).items() if k != "next_reread"}
    merged = dict(young, **upd)
    assert rr.due_rows([merged], NOW + timedelta(days=1), 10) == []
    assert rr.due_rows([merged], lapse, 10) == [merged]


# ---------------------------------------------------------------------------
# F1-16: the cron's paged read is ordered by host
# ---------------------------------------------------------------------------

def test_f1_16_cron_paged_read_orders_by_host():
    client = _Client([_row("h%04d.test" % i) for i in range(1200)])
    rows = rr._read_rows(client)
    assert len(rows) == 1200
    chain = [c for c in client.calls if c[0] in ("select", "order", "range", "execute")]
    pages = [chain[i:i + 4] for i in range(0, len(chain), 4)]
    assert len(pages) == 3
    for n, page in enumerate(pages):
        assert [c[0] for c in page] == ["select", "order", "range", "execute"]
        assert page[1] == ("order", "host") and page[2] == ("range", 500 * n, 500 * n + 499)


# ---------------------------------------------------------------------------
# F1-23: the integer knobs clamp a fraction to 1 (spec 2.1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,fn,default", [("ROBOTS_CRON_MAX_HOSTS", "max_hosts_per_run", 500),
                                             ("ROBOTS_CHALLENGE_PARK_DAYS", "challenge_park_days", 7)])
def test_f1_23_integer_knobs_clamp_a_fraction_to_one(monkeypatch, name, fn, default):
    monkeypatch.setenv(name, "0.5")
    assert getattr(rr, fn)() == 1
    for raw in ("0", "-2", "nan", "abc"):
        monkeypatch.setenv(name, raw)
        assert getattr(rr, fn)() == default, raw

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
name is the sanitised page title). Hermetic: an in-memory client, injected fetch /
sleep / SSRF seams, the netguard on; hosts are synthetic ``.test`` hosts or the
public registry rows.
"""
from __future__ import annotations

import asyncio
import copy
import dataclasses
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.main  # noqa: F401  (the import-time load_dotenv override runs first)
from app.services import kb_service as kb
from app.services import merchant_registry as mr
from app.services import platform_router as pr
from app.services import price_service as ps
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
          "MERCHANT_REGISTRY_MAX_STALE_SECONDS", "ROBOTS_CRON_MAX_HOSTS", "ROBOTS_CHALLENGE_PARK_DAYS")


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
        assert row["created_at"] == row["updated_at"], row["host"]
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
    assert y["robots"] == _residential(5)
    assert y["health"]["last_datacenter_result"]["state"] == "allow"
    assert y["health"]["pre_block_status"] == "live"
    o = client.row("old.test")
    assert (o["status"], o["blocked_reason"]) == ("live", None)
    assert o["robots"]["source"] == "datacenter" and o["robots"]["state"] == "allow"
    upd = rr.next_row_update(young, rr.decide_robots(*ALLOW, ["https://res.test/"]), NOW)
    assert set(upd) == {"health", "updated_at"}


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
    assert f["health"]["ssrf"] == "initial"
    h = client.row("hop.test")
    assert (h["status"], h["blocked_reason"]) == ("blocked", "ssrf_redirect")
    assert h["health"]["ssrf"] == "hop"
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
    r = client.row("redtag.test")["robots"]
    assert r["origin"] == "https://redtag.test" and r["other_origins"] == ["https://rtplus.myshopify.test"]
    assert set(r["probed"]) == {"/"}
    w = client.row("wshop.test")["robots"]
    assert w["origin"] == "https://www.wshop.test" and "other_origins" not in w
    assert set(w["probed"]) == {"/", "/p/1"}


# ---------------------------------------------------------------------------
# GC-8: the --classify scope
# ---------------------------------------------------------------------------

def test_gc8_classify_scope_is_live_platform_null_blank_mechanism_rows_including_literals(capsys):
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
    assert seen == ["a-literal.test", "e-json.test"]
    assert client.updates == [] and not [c for c in client.calls if c[0] in ("update", "insert")]
    out = capsys.readouterr().out
    assert "eligible=2 probed=2 woocommerce=2" in out


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

"""S81-19 GAP-QUEUE RED rows (spec S81-G4, unit S81-19 section 5, as amended by
RULINGS_S81_G4, R-G4-6: the single flight fails CLOSED when Redis is absent or
raising, no ``exhausted`` state): the off-clock enrich worker
``scripts/cron_kb_enrich.py`` (ENABLE_KB_ENRICH_WORKER, the G2 mode idiom;
ENABLE_KB_GAP_FILL; the INERT ENABLE_KB_GAP_WEB_SEARCH) and ``railway.kbenrich.json``.

Every RED row fails at base on an AssertionError only (``_mod()`` = find_spec + an
assertion). The PIN rows P1 / P2 are green at base.

Fakes: the service-role client is an in-memory recorder (select / eq / gte / in_ /
like / order / limit / range / upsert(on_conflict, ignore_duplicates) / update /
execute) with insert-ignore semantics; Redis records ``set(key, value, nx=, ex=)`` /
``get`` / ``delete``; ``kb_seed_common.PoliteFetcher`` is replaced by a recorder
class (constructor kwargs, every ``get`` with its timeout) returning configured
``FetchResult``s; ``price_service.extract_price_from_html`` is a recorder;
``kb_seed_common._now`` is fixed; the spend-breaker functions are RAISING recorders.

Contract details this file fixes (stated in the RED report): ``main(argv=None,
client=None, redis=None) -> int`` with ``--leg all|gaps|refresh``, ``--dry-run``,
``--report``; Redis None -> ``cache_service.redis_client``; the DRY report is JSON
with ``queue`` (``product_key`` per entry, ranked) and ``spend``; the price gap is
filled by an offer row built exactly as ``kb_ingest.run_job`` builds one (the pid's
concentration axis, ``size_ml`` from the extracted ``size``, ``list_vs_sale`` left
at the builder default).

Hygiene: pure ASCII, LF; bounded runner only; netguard on; synthetic hosts only.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import importlib.util
import json
import logging
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote_plus

import pytest

ROOT = Path(__file__).resolve().parents[1]
MOD = "scripts.cron_kb_enrich"
FLAG = "ENABLE_KB_ENRICH_WORKER"
FILL = "ENABLE_KB_GAP_FILL"
WEB = "ENABLE_KB_GAP_WEB_SEARCH"
KNOBS = ("KB_ENRICH_MAX_GAPS", "KB_ENRICH_HOSTS_PER_GAP", "KB_ENRICH_HEAD_N", "KB_ENRICH_TAIL_MAX",
         "KB_ENRICH_TAIL_WEEKDAY", "KB_ENRICH_DEMAND_DAYS", "KB_ENRICH_FETCH_TIMEOUT_SECONDS",
         "KB_ENRICH_LOCK_SECONDS")
SCRIPT = ROOT / "scripts" / "cron_kb_enrich.py"
CONFIG = ROOT / "railway.kbenrich.json"
NOW = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)  # a Monday (ISO weekday 1)
HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
TEMPLATE_A = "https://" + HOST_A + "/search/suggest.json?q={q}&resources[type]=product"
PDP_A = "https://" + HOST_A + "/products/nimbus-noir"
PDP_A2 = "https://" + HOST_A + "/products/velvet-dusk"
PDP_A3 = "https://" + HOST_A + "/products/amber-field"
PDP_B = "https://" + HOST_B + "/products/nimbus-noir"
NAMES = {"A": ("Acme", "Nimbus Noir Eau de Parfum"), "B": ("Zephyra", "Velvet Dusk Eau de Toilette"),
         "C": ("Orvel", "Amber Field Extrait de Parfum"), "D": ("Lumio", "Quiet Tide Eau de Cologne")}
EXTRACTED = {"amount": 42.5, "currency": "BHD", "source_method": "page_scrape_jsonld", "estimated": False,
             "size": "100ml", "in_stock": True, "url": PDP_A, "retailer": HOST_A}
LOG_TEMPLATES = [
    re.compile(r"^\[KB_ENRICH\] mode=(off|dry|apply) gap_fill=[01] web_search=[01]$"),
    re.compile(r"^\[KB_ENRICH\] product step=(search|pdp_hint|refresh) host=([a-z0-9.-]+|-) "
               r"outcome=(filled|empty|refused:[a-z_]+|error:[A-Za-z_]+)$"),
    re.compile(r"^\[KB_ENRICH\] step=web_search status=not_built$"),
    re.compile(r"^\[KB_ENRICH\] totals( [a-z_]+=\d+)+$"),
    re.compile(r"^\[KB_ENRICH\] dry [a-z_]+( [a-z_]+=[A-Za-z0-9_.:|-]+)*$"),
]


def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _mod():
    assert _present(MOD), "scripts/cron_kb_enrich.py does not exist (S81-19 not implemented)"
    return importlib.import_module(MOD)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (S81-19 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


def _common():
    import scripts.kb_seed_common as common
    return common


def _kb():
    from app.services import kb_service as kb
    return kb


def _pid(key):
    return _kb().kb_product_id(*NAMES[key])


def _vid(pid, size_ml):
    kb = _kb()
    conc = pid.split("|")[3]
    conc = conc if conc in kb.kb_concentrations() else None
    return kb.kb_variant_key(pid, conc, size_ml)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in (FLAG, FILL, WEB) + KNOBS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(_common(), "_now", lambda: NOW)
    from app.services import llm_spend_breaker as br

    def _boom(*_a, **_k):
        raise AssertionError("S81-19 must never call the spend breaker")

    for name in ("reserve", "settle", "record"):
        if hasattr(br, name):
            monkeypatch.setattr(br, name, _boom)
    yield


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------

def _ts(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


def _cmp_key(value):
    v = _ts(value)
    if isinstance(v, datetime):
        return (0, v.timestamp(), "")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return (1, float(v), "")
    return (2, 0.0, str(v))


def _norm(value):
    if isinstance(value, (int, float, str)) and not isinstance(value, bool):
        try:
            return str(Decimal(str(value)).normalize())
        except (InvalidOperation, ValueError):
            return str(value)
    return str(value)


_CONFLICT = {
    "kb_products": ("id",), "kb_variants": ("id",), "kb_images": ("product_id", "url"),
    "kb_offers": ("variant_id", "merchant_id", "market", "observed_currency", "amount", "list_vs_sale"),
    "kb_gaps": ("product_key", "field"), "kb_specs": ("product_id", "field", "lang"),
}


class _Resp:
    def __init__(self, data):
        self.data = data
        self.count = None


class _Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.op, self.payload, self.kwargs = None, None, {}
        self.filters, self.orders, self.columns = [], [], None
        self.lim, self.rng = None, None

    def select(self, columns="*", **kwargs):
        if self.op is None:
            self.op = "select"
        self.columns = columns
        return self

    def upsert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "upsert", copy.deepcopy(rows), dict(kwargs)
        return self

    def insert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "insert", copy.deepcopy(rows), dict(kwargs)
        return self

    def update(self, payload, **kwargs):
        self.op, self.payload, self.kwargs = "update", copy.deepcopy(payload), dict(kwargs)
        return self

    def delete(self, **kwargs):
        self.op = "delete"
        return self

    def order(self, column, desc=False, **kwargs):
        self.orders.append((column, bool(desc)))
        return self

    def limit(self, n, **kwargs):
        self.lim = n
        return self

    def range(self, start, end, **kwargs):
        self.rng = (start, end)
        return self

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _filter(*args, **kwargs):
            self.filters.append((name, list(args)))
            return self
        return _filter

    def execute(self):
        return self.client._execute(self)


def _match(row, name, args):
    if len(args) < 2:
        return True
    col, val = args[0], args[1]
    have = row.get(col)
    if name == "eq":
        return str(have) == str(val)
    if name == "neq":
        return str(have) != str(val)
    if name == "in_":
        return have in list(val)
    if name in ("gte", "gt", "lte", "lt"):
        if have is None:
            return False
        a, b = _cmp_key(have), _cmp_key(val)
        return {"gte": a >= b, "gt": a > b, "lte": a <= b, "lt": a < b}[name]
    if name == "like":
        pat = "^" + re.escape(str(val)).replace("%", ".*").replace("_", ".") + "$"
        return re.match(pat, str(have)) is not None
    return True


class _Client:
    def __init__(self, tables, events, *, cas_empty=False):
        self.tables = copy.deepcopy(tables)
        self.events = events
        self.cas_empty = cas_empty
        self.ops = []
        self.lock = threading.Lock()

    def table(self, name):
        return _Query(self, name)

    def _key(self, table, row):
        return tuple(_norm(row.get(c)) for c in _CONFLICT.get(table, ("id",)))

    def _execute(self, q):
        with self.lock:
            entry = {"table": q.table, "op": q.op, "payload": q.payload, "kwargs": q.kwargs,
                     "filters": q.filters, "columns": q.columns}
            self.ops.append(entry)
            self.events.append(("db", q.op, q.table))
            rows = self.tables.setdefault(q.table, [])
            if q.op == "select":
                out = [dict(r) for r in rows if all(_match(r, n, a) for n, a in q.filters)]
                for col, desc in reversed(q.orders):
                    out.sort(key=lambda r: _cmp_key(r.get(col)), reverse=desc)
                if q.rng is not None:
                    out = out[q.rng[0]:q.rng[1] + 1]
                if q.lim is not None:
                    out = out[:q.lim]
                return _Resp(out)
            if q.op in ("upsert", "insert"):
                payload = q.payload if isinstance(q.payload, list) else [q.payload]
                inserted = []
                for row in payload:
                    key = self._key(q.table, row)
                    if any(self._key(q.table, r) == key for r in rows):
                        if q.kwargs.get("ignore_duplicates") is True:
                            continue
                    rows.append(dict(row))
                    inserted.append(dict(row))
                return _Resp(inserted)
            if q.op == "update":
                if q.table == "kb_gaps" and self.cas_empty:
                    return _Resp([])
                hit = [r for r in rows if all(_match(r, n, a) for n, a in q.filters)]
                for r in hit:
                    r.update(q.payload or {})
                return _Resp([dict(r) for r in hit])
            return _Resp([])

    def writes(self, table=None):
        return [o for o in self.ops if o["op"] in ("upsert", "insert", "update", "delete")
                and (table is None or o["table"] == table)]

    def sent(self, table):
        out = []
        for o in self.ops:
            if o["table"] == table and o["op"] in ("upsert", "insert"):
                out.extend(o["payload"] if isinstance(o["payload"], list) else [o["payload"]])
        return out

    def gap_updates(self):
        return [o for o in self.ops if o["table"] == "kb_gaps" and o["op"] == "update"]


class _Redis:
    def __init__(self, events, mode="ok"):
        self.events, self.mode = events, mode
        self.store, self.calls = {}, []

    def set(self, key, value, nx=None, ex=None, **kwargs):
        self.calls.append(("set", key, value, nx, ex))
        self.events.append(("redis.set", key))
        if self.mode == "raise":
            raise RuntimeError("s19 probe: redis set")
        if self.mode == "held" or (nx and key in self.store):
            return False
        self.store[key] = value
        return True

    def get(self, key):
        self.calls.append(("get", key))
        return self.store.get(key)

    def delete(self, *keys):
        self.calls.append(("delete",) + tuple(keys))
        for k in keys:
            self.store.pop(k, None)
        return len(keys)


class _FetchPlan:
    def __init__(self, events, plan):
        self.events, self.plan = events, plan
        self.inits, self.gets = [], []

    def cls(self):
        holder = self
        common = _common()

        class _Fetcher:
            def __init__(self, fetch=None, validate=None, sleep=None, require_tos=False):
                holder.inits.append({"require_tos": require_tos})
                self.require_tos = require_tos
                self.requests = 0

            async def get(self, url, row=None, now=None, *, gate=True, timeout=20.0, delay=None):
                holder.gets.append({"url": url, "timeout": timeout, "require_tos": self.require_tos,
                                    "gate": gate, "row_host": (row or {}).get("host")})
                holder.events.append(("fetch", url))
                self.requests += 1
                outcome = holder.plan.get(url, ("status", 404, ""))
                if outcome[0] == "raise":
                    raise outcome[1]
                if outcome[0] == "gate":
                    return common.FetchResult(None, {}, "", url, "gate", outcome[1])
                return common.FetchResult(outcome[1], {}, outcome[2], url, None, None)
        return _Fetcher


def _robots(host):
    iso = lambda m: m.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    rules = [["allow", "/"]]
    return {"state": "allow", "status": 200, "fetched_at": iso(NOW - timedelta(hours=1)),
            "next_reread": iso(NOW + timedelta(hours=23)), "crawl_delay": None, "origin": "https://" + host,
            "source": "robots_txt", "rules": {"qarenbot": rules, "star": rules}, "probed": "/"}


def _merchant(host, *, status="live", template=None, tos="allowed", reviewed=True):
    tos_rec = None if tos is None else {"verdict": tos, "terms_url": "https://" + host + "/terms",
                                        "reviewed_at": "2026-10-30T00:00:00Z" if reviewed else None}
    return {"host": host, "status": status, "deny": False,
            "blocked_reason": "manual" if status == "blocked" else None, "registry": [],
            "robots": _robots(host), "challenge": None, "tos": tos_rec, "currency_hint": "BHD",
            "country": "BH", "platform": "shopify", "updated_at": "2026-10-30T00:00:00Z",
            "search_template": template}


def _gap(pid, field, *, demand=1, last=None, state="open", hint=None):
    last = last if last is not None else NOW - timedelta(days=1)
    stamp = last.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return {"product_key": pid, "field": field, "demand_count": demand, "first_seen": stamp,
            "last_seen": stamp, "state": state, "source_hint": hint}


def _hint_field(host):
    return "pdp_" + hashlib.sha256(host.encode("utf-8")).hexdigest()[:16]


def _products(*keys):
    return [{"id": _pid(k), "brand": NAMES[k][0], "name": NAMES[k][1], "identity_confidence": "high",
             "concentration": _pid(k).split("|")[3]} for k in keys]


def _search_body():
    return json.dumps({"resources": {"results": {"products": [{"url": "/products/nimbus-noir"}]}}})


def _run(monkeypatch, caplog, mode, *, tables, plan=None, extract=None, redis="ok", argv=("--leg", "gaps"),
         fill=True, web=None, env=None, cas_empty=False, redis_none=False):
    mod = _mod()
    events = []
    if mode is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, mode)
    if fill:
        monkeypatch.setenv(FILL, "true")
    if web is not None:
        monkeypatch.setenv(WEB, web)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    fp = _FetchPlan(events, plan or {})
    monkeypatch.setattr(_common(), "PoliteFetcher", fp.cls())
    from app.services import cache_service, price_service
    extracts = []

    def _extract(html, product_name, currency, domain, url, category=None, outcome_out=None, final_url=None):
        extracts.append({"url": url, "currency": currency, "domain": domain, "category": category,
                         "product_name": product_name})
        events.append(("extract", url))
        out = (extract or {}).get(url)
        return copy.deepcopy(out) if out is not None else None

    monkeypatch.setattr(price_service, "extract_price_from_html", _extract)
    client = _Client(tables, events, cas_empty=cas_empty)
    rds = None if redis_none else _Redis(events, redis)
    monkeypatch.setattr(cache_service, "redis_client", None)
    caplog.set_level(logging.INFO)
    caplog.clear()
    rc = _attr(mod, "main")(list(argv), client=client, redis=rds)
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_ENRICH]")]
    return {"rc": rc, "client": client, "redis": rds, "fetch": fp, "events": events, "lines": lines,
            "extracts": extracts}


def _totals(lines):
    tot = [ln for ln in lines if ln.startswith("[KB_ENRICH] totals")]
    assert len(tot) == 1, lines
    return {k: int(v) for k, v in re.findall(r"([a-z_]+)=(\d+)", tot[0])}


def _filters(op):
    return sorted((name, args[0], str(args[1])) for name, args in op["filters"])


def _sf_key(pid):
    return "kbenrich:sf:" + hashlib.sha256(pid.encode("utf-8")).hexdigest()[:32]


def _price_scenario():
    pa = _pid("A")
    tables = {"kb_gaps": [_gap(pa, "price", demand=4)], "kb_products": _products("A"),
              "kb_merchants": [_merchant(HOST_A, template=TEMPLATE_A)], "kb_variants": [], "kb_offers": []}
    search_url = TEMPLATE_A.replace("{q}", quote_plus(" ".join(NAMES["A"])))
    plan = {search_url: ("status", 200, _search_body()), PDP_A: ("status", 200, "<html>pdp</html>")}
    return pa, tables, plan, search_url


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,want", [
    (None, "off"), ("", "off"), ("false", "off"), ("0", "off"), ("OFF", "off"), ("dry", "off"),
    ("garbage", "off"), ("true", "dry"), (" TRUE ", "dry"), ("1", "dry"), ("yes", "dry"), ("on", "dry"),
    ("apply", "apply"), (" Apply ", "apply"),
])
def test_r1_entry_exists_and_mode(monkeypatch, value, want):
    """R1: importable; enrich_mode() over the G2 matrix; the two sub-flags are house
    booleans read per call."""
    mod = _mod()
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert _attr(mod, "enrich_mode")() == want
    for name, reader in ((FILL, "gap_fill_enabled"), (WEB, "web_search_requested")):
        fn = _attr(mod, reader)
        for v in (None, "", "false", "0", "apply", "garbage"):
            if v is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, v)
            assert fn() is False, (reader, v)
        for v in ("true", " TRUE ", "1", "yes", "On"):
            monkeypatch.setenv(name, v)
            assert fn() is True, (reader, v)


def test_r2_off_is_inert(monkeypatch, caplog):
    """R2: mode off -> exit 0, ONE INFO line, no client resolve, no Redis call, no app
    module newly imported (the mode is read FIRST)."""
    mod = _mod()
    called = []
    monkeypatch.setattr(_common(), "_admin_client", lambda: called.append("admin") or None)
    monkeypatch.setenv(FILL, "true")
    monkeypatch.setenv(WEB, "true")
    monkeypatch.delenv(FLAG, raising=False)
    events = []
    rds = _Redis(events)
    before = {m for m in sys.modules if m == "app" or m.startswith("app.")}
    caplog.set_level(logging.INFO)
    caplog.clear()
    rc = _attr(mod, "main")([], client=None, redis=rds)
    after = {m for m in sys.modules if m == "app" or m.startswith("app.")}
    assert rc == 0
    assert called == [] and rds.calls == [] and events == []
    assert sorted(after - before) == []
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_ENRICH]")]
    assert lines == ["[KB_ENRICH] mode=off ENABLE_KB_ENRICH_WORKER not set; skipping run"], lines


def test_r3_dry_reads_only(monkeypatch, caplog, tmp_path):
    """R3: DRY prints the ranked queue + the plan + the spend bound (JSON --report), with
    zero fetches, zero Redis commands and zero writes."""
    pa, tables, plan, _s = _price_scenario()
    out = tmp_path / "enrich.json"
    res = _run(monkeypatch, caplog, "true", tables=tables, plan=plan, extract={PDP_A: EXTRACTED},
               argv=["--leg", "all", "--report", str(out)])
    assert res["rc"] == 0
    assert res["fetch"].gets == [] and res["redis"].calls == [] and res["client"].writes() == []
    assert res["extracts"] == []
    report = json.loads(out.read_text(encoding="ascii"))
    assert [q["product_key"] for q in report["queue"]] == [pa], report
    assert report["spend"]["lane"] == "offclock" and float(report["spend"]["planned_usd"]) == 0.0, report
    _res2 = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED},
                 argv=["--leg", "all", "--dry-run"])
    assert _res2["fetch"].gets == [] and _res2["client"].writes() == [] and _res2["redis"].calls == []


def test_r4_rank_and_window(monkeypatch, caplog, tmp_path):
    """R4: open non-pdp_ rows of the demand window ranked by demand then last_seen; older
    rows, pdp_ rows and non-open rows excluded; at most KB_ENRICH_MAX_GAPS rows."""
    pa, pb, pc, pd = _pid("A"), _pid("B"), _pid("C"), _pid("D")
    gaps = [
        _gap(pa, "price", demand=5, last=NOW - timedelta(days=1)),
        _gap(pb, "image", demand=5, last=NOW - timedelta(hours=2)),
        _gap(pc, "price", demand=9, last=NOW - timedelta(days=10)),
        _gap(pd, "size", demand=1, last=NOW - timedelta(days=1)),
        _gap(pc, "rating", demand=3, state="needs_operator"),
        _gap(pd, _hint_field(HOST_B), demand=0, state="open", hint=PDP_B),
    ]
    tables = {"kb_gaps": gaps, "kb_products": _products("A", "B", "C", "D"), "kb_merchants": []}
    out = tmp_path / "q.json"
    _run(monkeypatch, caplog, "true", tables=tables, argv=["--leg", "gaps", "--report", str(out)])
    report = json.loads(out.read_text(encoding="ascii"))
    assert [q["product_key"] for q in report["queue"]] == [pb, pa, pd], report["queue"]
    assert all(not f.startswith("pdp_") for q in report["queue"] for f in q.get("fields", [])), report
    tables["kb_gaps"] = gaps[:4]
    out2 = tmp_path / "q2.json"
    _run(monkeypatch, caplog, "true", tables=tables, argv=["--leg", "gaps", "--report", str(out2)],
         env={"KB_ENRICH_MAX_GAPS": "2"})
    report2 = json.loads(out2.read_text(encoding="ascii"))
    assert [q["product_key"] for q in report2["queue"]] == [pb, pa], report2["queue"]


def test_r5_single_flight(monkeypatch, caplog):
    """R5: SET kbenrich:sf:<32 hex> run_id NX EX 900 before any fetch of the product; a
    held lock -> no fetch, locked=1; Redis None or raising -> no fetch, lock_unavailable."""
    pa, tables, plan, _s = _price_scenario()
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED})
    sets = [c for c in res["redis"].calls if c[0] == "set"]
    assert sets and sets[0][1] == _sf_key(pa) and sets[0][3] is True and sets[0][4] == 900, sets
    assert isinstance(sets[0][2], str) and sets[0][2], sets
    ev = res["events"]
    first_set = ev.index(("redis.set", _sf_key(pa)))
    first_fetch = next(i for i, e in enumerate(ev) if e[0] == "fetch")
    assert first_set < first_fetch, ev
    assert ("delete", _sf_key(pa)) in res["redis"].calls, res["redis"].calls
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED}, redis="held")
    assert res["fetch"].gets == [] and _totals(res["lines"]).get("locked") == 1, res["lines"]
    assert not [c for c in res["redis"].calls if c[0] == "delete"], res["redis"].calls
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED},
               redis_none=True)
    assert res["fetch"].gets == [] and _totals(res["lines"]).get("lock_unavailable") == 1, res["lines"]
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED}, redis="raise")
    assert res["fetch"].gets == [] and _totals(res["lines"]).get("lock_unavailable") == 1, res["lines"]
    assert res["client"].gap_updates() == []


def test_r6_specs_gap_goes_licence(monkeypatch, caplog):
    """R6: a `specs` gap -> ONE CAS update to licence filtered on the open state; never
    fetched."""
    pa = _pid("A")
    tables = {"kb_gaps": [_gap(pa, "specs", demand=3)], "kb_products": _products("A"),
              "kb_merchants": [_merchant(HOST_A, template=TEMPLATE_A)]}
    res = _run(monkeypatch, caplog, "apply", tables=tables)
    ups = res["client"].gap_updates()
    assert len(ups) == 1 and ups[0]["payload"] == {"state": "licence"}, ups
    assert _filters(ups[0]) == [("eq", "field", "specs"), ("eq", "product_key", pa), ("eq", "state", "open")]
    assert res["fetch"].gets == [] and res["extracts"] == []


def test_r7_step1_search_template_polite(monkeypatch, caplog):
    """R7: the search URL is the template with the quoted query, fetched through the
    fetcher built with require_tos=True at timeout 4.0; the PDP candidate is fetched;
    the offer row is the builder's, sent insert-ignore; the price gap CAS -> closed."""
    kb = _kb()
    pa, tables, plan, search_url = _price_scenario()
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED})
    urls = [g["url"] for g in res["fetch"].gets]
    assert urls[:2] == [search_url, PDP_A], urls
    assert res["fetch"].inits and all(i["require_tos"] is True for i in res["fetch"].inits), res["fetch"].inits
    assert all(g["timeout"] == 4.0 and g["require_tos"] is True for g in res["fetch"].gets), res["fetch"].gets
    assert res["extracts"] and res["extracts"][0]["currency"] == "BHD", res["extracts"]
    want = kb.build_offer_row(
        variant_id=_vid(pa, 100), merchant_id=HOST_A, market="BH", amount=42.5, observed_currency="BHD",
        evidence_rung="page_evidence", canonical_url=PDP_A, captured_at=NOW, size_ml=100, in_stock=True)
    assert want is not None
    offers = [o for o in res["client"].ops if o["table"] == "kb_offers" and o["op"] == "upsert"]
    assert offers and all(o["kwargs"].get("ignore_duplicates") is True for o in offers), offers
    assert want in res["client"].sent("kb_offers"), res["client"].sent("kb_offers")
    ups = res["client"].gap_updates()
    assert [u["payload"] for u in ups] == [{"state": "closed"}], ups
    assert _filters(ups[0]) == [("eq", "field", "price"), ("eq", "product_key", pa), ("eq", "state", "open")]


@pytest.mark.parametrize("case", ["ok", "tos", "timeout", "http500"])
def test_r8_step2_pdp_hint_consumed(monkeypatch, caplog, case):
    """R8: a queued pdp_<16 hex> hint of the product is fetched (no search host): a 2xx ->
    the hint CAS queued -> closed; a ToS refusal -> needs_operator; a timeout or a
    non-2xx -> the hint stays queued (no update of the hint row)."""
    pa = _pid("A")
    field = _hint_field(HOST_B)
    tables = {"kb_gaps": [_gap(pa, "price", demand=2), _gap(pa, field, demand=0, state="queued", hint=PDP_B)],
              "kb_products": _products("A"), "kb_merchants": [_merchant(HOST_B)]}
    plan = {"ok": {PDP_B: ("status", 200, "<html/>")}, "tos": {PDP_B: ("gate", "tos")},
            "timeout": {PDP_B: ("raise", asyncio.TimeoutError())},
            "http500": {PDP_B: ("status", 500, "")}}[case]
    extract = {PDP_B: dict(EXTRACTED, url=PDP_B, retailer=HOST_B)}
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract=extract)
    assert [g["url"] for g in res["fetch"].gets] == [PDP_B], res["fetch"].gets
    hint_ups = [u for u in res["client"].gap_updates() if ("eq", "field", field) in _filters(u)]
    if case == "ok":
        assert [u["payload"] for u in hint_ups] == [{"state": "closed"}], hint_ups
        assert ("eq", "state", "queued") in _filters(hint_ups[0])
    elif case == "tos":
        assert [u["payload"] for u in hint_ups] == [{"state": "needs_operator"}], hint_ups
        assert ("eq", "state", "queued") in _filters(hint_ups[0])
    else:
        assert hint_ups == [], hint_ups


def test_r9_step3_inert(monkeypatch, caplog):
    """R9: ENABLE_KB_GAP_WEB_SEARCH ON -> exactly one `step=web_search status=not_built`
    line per run (two products reach the step); no LLM module imported; the breaker
    recorders never fire (autouse); OFF -> no such line."""
    pa, pb = _pid("A"), _pid("B")
    tables = {"kb_gaps": [_gap(pa, "price", demand=2), _gap(pb, "image", demand=1)],
              "kb_products": _products("A", "B"), "kb_merchants": []}
    import app.services as _svc_pkg
    for name in ("app.services.llm_router", "anthropic"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.delattr(_svc_pkg, "llm_router", raising=False)
    res = _run(monkeypatch, caplog, "apply", tables=tables, web="true")
    hits = [ln for ln in res["lines"] if ln == "[KB_ENRICH] step=web_search status=not_built"]
    assert len(hits) == 1, res["lines"]
    assert "app.services.llm_router" not in sys.modules and "anthropic" not in sys.modules
    assert _totals(res["lines"]).get("web_search_not_built") == 1
    res = _run(monkeypatch, caplog, "apply", tables=tables, web="false")
    assert not any("web_search" in ln and "not_built" in ln and "totals" not in ln for ln in res["lines"])


def test_r10_step4_blocked_to_operator(monkeypatch, caplog):
    """R10: every candidate host refused not_live on a blocked registry row -> the gap
    open -> needs_operator (one CAS, the open state filter)."""
    pa = _pid("A")
    field = _hint_field(HOST_B)
    tables = {"kb_gaps": [_gap(pa, "price", demand=2), _gap(pa, field, demand=0, state="queued", hint=PDP_B)],
              "kb_products": _products("A"), "kb_merchants": [_merchant(HOST_B, status="blocked")]}
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan={PDP_B: ("gate", "not_live")})
    gap_ups = [u for u in res["client"].gap_updates() if ("eq", "field", "price") in _filters(u)]
    assert [u["payload"] for u in gap_ups] == [{"state": "needs_operator"}], res["client"].gap_updates()
    assert ("eq", "state", "open") in _filters(gap_ups[0])


def test_r11_cas_never_moves_demand_or_hint(monkeypatch, caplog):
    """R11: every kb_gaps update payload is exactly {"state": <new>} filtered on
    product_key, field and the old state (a KB_GAP_STATES member); a lost CAS is not
    retried."""
    kb = _kb()
    pa, tables, plan, _s = _price_scenario()
    tables["kb_gaps"].append(_gap(pa, "specs", demand=1))
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED}, cas_empty=True)
    ups = res["client"].gap_updates()
    assert len(ups) == 2, ups
    for u in ups:
        assert set(u["payload"]) == {"state"} and u["payload"]["state"] in kb.KB_GAP_STATES, u
        names = sorted((n, a[0]) for n, a in u["filters"])
        assert names == [("eq", "field"), ("eq", "product_key"), ("eq", "state")], u["filters"]
    assert sorted(u["payload"]["state"] for u in ups) == ["closed", "licence"]


@pytest.mark.parametrize("weekday,want_tail", [("3", False), ("1", True)])
def test_r12_refresh_head_daily_tail_weekly(monkeypatch, caplog, weekday, want_tail):
    """R12: head = the top KB_ENRICH_HEAD_N products by summed demand; the tail (oldest
    last_seen first) only on KB_ENRICH_TAIL_WEEKDAY; every stored URL fetched at 4.0
    with require_tos; a same-amount re-observation = ONE update of KB_OFFER_UPSERT_SET;
    no adapter / render module imported."""
    kb = _kb()
    pa, pb, pc = _pid("A"), _pid("B"), _pid("C")

    def _offer(pid, url, days):
        stamp = (NOW - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        return {"variant_id": _vid(pid, 100), "merchant_id": HOST_A, "market": "BH", "observed_currency": "BHD",
                "amount": "42.500", "canonical_url": url, "last_seen": stamp, "captured_at": stamp,
                "first_seen": stamp, "list_vs_sale": "unknown", "evidence_rung": "page_evidence",
                "size_ml": 100, "in_stock": True}
    tables = {"kb_gaps": [_gap(pa, "price", demand=5), _gap(pb, "image", demand=2)],
              "kb_products": _products("A", "B", "C"),
              "kb_merchants": [_merchant(HOST_A, template=TEMPLATE_A)],
              "kb_offers": [_offer(pa, PDP_A, 3), _offer(pb, PDP_A2, 10), _offer(pc, PDP_A3, 20)],
              "kb_variants": []}
    plan = {u: ("status", 200, "<html/>") for u in (PDP_A, PDP_A2, PDP_A3)}
    extract = {u: dict(EXTRACTED, url=u) for u in (PDP_A, PDP_A2, PDP_A3)}
    import app.services as _svc_pkg
    watched = ("firecrawl_service", "scrapedo_service", "zyte_service", "magento_graphql_service",
               "shopify_pdp_service", "woocommerce_service", "algolia_service")
    for name in watched:
        monkeypatch.delitem(sys.modules, "app.services." + name, raising=False)
        monkeypatch.delattr(_svc_pkg, name, raising=False)
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract=extract,
               argv=["--leg", "refresh"], fill=False,
               env={"KB_ENRICH_HEAD_N": "1", "KB_ENRICH_TAIL_WEEKDAY": weekday})
    urls = [g["url"] for g in res["fetch"].gets]
    assert urls == ([PDP_A, PDP_A3, PDP_A2] if want_tail else [PDP_A]), urls
    assert all(g["timeout"] == 4.0 and g["require_tos"] is True for g in res["fetch"].gets)
    offer_ups = [o for o in res["client"].ops if o["table"] == "kb_offers" and o["op"] == "update"]
    assert len(offer_ups) == len(urls), offer_ups
    for o in offer_ups:
        assert set(o["payload"]) == set(kb.KB_OFFER_UPSERT_SET), o["payload"]
    for name in watched:
        assert "app.services." + name not in sys.modules, name
    assert res["client"].gap_updates() == []


def test_r13_log_lines_constants_only(monkeypatch, caplog):
    """R13: every [KB_ENRICH] line matches its template; no URL path, no product name,
    no query string."""
    pa, tables, plan, _s = _price_scenario()
    tables["kb_offers"] = []
    res = _run(monkeypatch, caplog, "apply", tables=tables, plan=plan, extract={PDP_A: EXTRACTED},
               argv=["--leg", "all"], web="true")
    assert res["lines"], "no [KB_ENRICH] line"
    for ln in res["lines"]:
        assert any(t.match(ln) for t in LOG_TEMPLATES), ln
        assert "/products" not in ln and "Nimbus" not in ln and "?q=" not in ln and "Acme" not in ln, ln
    assert any(ln.startswith("[KB_ENRICH] product step=search host=" + HOST_A) for ln in res["lines"]), res["lines"]


def test_r14_railway_config():
    """R14: railway.kbenrich.json as C2."""
    assert CONFIG.is_file(), "railway.kbenrich.json does not exist (S81-19 not implemented)"
    cfg = json.loads(CONFIG.read_text(encoding="ascii"))
    assert cfg["build"]["watchPatterns"] == [
        "scripts/cron_kb_enrich.py", "scripts/kb_seed_common.py", "railway.kbenrich.json"], cfg
    assert cfg["deploy"]["startCommand"] == "python -m scripts.cron_kb_enrich", cfg
    assert cfg["deploy"]["restartPolicyType"] == "NEVER", cfg


def test_r15_hygiene():
    """R15: the script and the config are LF and pure ASCII (the r27 rule)."""
    for path in (SCRIPT, CONFIG):
        assert path.is_file(), "%s does not exist (S81-19 not implemented)" % path.name
        raw = path.read_bytes()
        assert b"\r" not in raw, path.name
        assert all(b < 128 for b in raw), path.name


def test_p1_pdp_discovery_contract_unchanged():
    """P1 (PIN): cron_pdp_discovery.gap_field / gap_rows still produce the R-G2-13 hint
    row (state queued, demand 0, the canonical hint, field pdp_<16 hex>)."""
    import scripts.cron_pdp_discovery as pdp
    pa = _pid("A")
    run = pdp.HostRun(_merchant(HOST_B))
    rows, refused = pdp.gap_rows(run, [(pa, PDP_B + "?ref=x")], NOW)
    assert refused == 0 and len(rows) == 1, (rows, refused)
    row = rows[0]
    assert row["field"] == _hint_field(HOST_B) == pdp.gap_field(HOST_B)
    assert re.match(r"^pdp_[0-9a-f]{16}$", row["field"])
    assert row["state"] == "queued" and row["demand_count"] == 0 and row["source_hint"] == PDP_B, row
    assert row["product_key"] == pa


def test_p2_url_gate_tos_equals_verdict_plus_tos():
    """P2 (PIN): url_gate(require_tos=True) is None iff live_robots.url_verdict is None
    and the row's ToS verdict is allowed, over a matrix of rows and URLs."""
    from app.services import live_robots
    common = _common()
    rows = [_merchant(HOST_A), _merchant(HOST_A, tos=None), _merchant(HOST_A, tos="disallowed"),
            _merchant(HOST_A, status="blocked"), _merchant(HOST_A, status="candidate"),
            dict(_merchant(HOST_A), deny=True), None]
    urls = [PDP_A, "https://" + HOST_B + "/p", "ftp://" + HOST_A + "/x", "not a url"]
    seen = 0
    for row in rows:
        for url in urls:
            gate = common.url_gate(row, url, NOW, require_tos=True)
            verdict = live_robots.url_verdict(url, row, NOW)
            tos_ok = isinstance(row, dict) and isinstance(row.get("tos"), dict) and row["tos"].get("verdict") == "allowed"
            assert (gate is None) == (verdict is None and tos_ok), (row and row.get("status"), url, gate, verdict)
            seen += gate is None
    assert seen >= 1

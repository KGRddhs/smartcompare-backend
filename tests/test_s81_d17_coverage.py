"""D17 MEASURE-COVERAGE RED rows (spec S81-G4, unit D17 section 5, as amended by
RULINGS_S81_G4): the daily kb_coverage_daily rollup script
``scripts/cron_kb_coverage.py`` (flag ENABLE_KB_COVERAGE_ROLLUP, the G2 mode idiom:
unset / garbage OFF, the house truthy set DRY, ``apply`` WRITE) and its service
config ``railway.kbcoverage.json``.

Every row fails at base on an AssertionError only: the module is reached through
``_mod()`` (find_spec + an assertion), never imported at module top.

Contract details this file fixes (stated in the RED report): ``main(argv=None,
client=None, redis=None) -> int``; ``coverage_mode()``; the run day defaults to
yesterday UTC of ``kb_seed_common._now()``; ages are measured against that same
``_now()``; the offers come from the ``kb_offers_latest`` view (variant_id,
last_seen, captured_at); a share is rounded to 4 places and its n is the product
count; the host counters are read with ONE pipeline of HGETALL over the live +
blocked registry hosts and an EMPTY hash is an absent key.

Hygiene: pure ASCII, LF; bounded runner only; netguard on (the client and Redis
are in-memory fakes); synthetic hosts and identities only.
"""
from __future__ import annotations

import copy
import importlib
import importlib.util
import json
import logging
import re
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MOD = "scripts.cron_kb_coverage"
FLAG = "ENABLE_KB_COVERAGE_ROLLUP"
SCRIPT = ROOT / "scripts" / "cron_kb_coverage.py"
CONFIG = ROOT / "railway.kbcoverage.json"
NOW = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)
DAY = date(2026, 11, 1)
HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
HOST_C = "store-c.example.com"
SEARCH_LOG_COLUMNS = "products_found,success,is_synthetic,created_at"
METRIC_LINE = re.compile(r"^\[KB_COVERAGE\] metric=(\S+) value=(\S+) n=(\d+)$")
TOTALS_LINE = re.compile(r"^\[KB_COVERAGE\] totals rows=\d+ not_built=\d+ skipped_long=\d+ redis=[01]$")


def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _mod():
    assert _present(MOD), "scripts/cron_kb_coverage.py does not exist (D17 not implemented)"
    return importlib.import_module(MOD)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (D17 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


def _common():
    import scripts.kb_seed_common as common
    return common


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in (FLAG, "KB_COVERAGE_MAX_HOSTS", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(_common(), "_now", lambda: NOW)
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
        return str(have) == str(val) if not isinstance(val, bool) else have is val
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
        pat = "^" + re.escape(str(val)).replace("%", ".*") + "$"
        return re.match(pat, str(have)) is not None
    if name == "is_":
        return have is None if str(val).lower() in ("null", "none") else have == val
    return True


class _Client:
    def __init__(self, tables, raise_on=()):
        self.tables = copy.deepcopy(tables)
        self.raise_on = set(raise_on)
        self.ops = []
        self.lock = threading.Lock()

    def table(self, name):
        return _Query(self, name)

    def _execute(self, q):
        with self.lock:
            self.ops.append({"table": q.table, "op": q.op, "payload": q.payload,
                             "kwargs": q.kwargs, "filters": q.filters, "columns": q.columns})
            if q.table in self.raise_on:
                raise RuntimeError("d17 probe: read failed")
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
                rows.extend(dict(r) for r in payload)
                return _Resp([dict(r) for r in payload])
            return _Resp([])

    def writes(self):
        return [o for o in self.ops if o["op"] in ("upsert", "insert", "update", "delete")]


class _Pipe:
    def __init__(self, redis):
        self.redis, self.keys = redis, []

    def hgetall(self, key):
        self.redis.calls.append(("pipeline.hgetall", key))
        self.keys.append(key)
        return self

    def exec(self):
        self.redis.calls.append(("pipeline.exec", len(self.keys)))
        return [dict(self.redis.hashes.get(k, {})) for k in self.keys]

    def execute(self):
        return self.exec()


class _Redis:
    def __init__(self, hashes):
        self.hashes = dict(hashes)
        self.calls = []

    def pipeline(self):
        self.calls.append(("pipeline",))
        return _Pipe(self)

    def hgetall(self, key):
        self.calls.append(("hgetall", key))
        return dict(self.hashes.get(key, {}))

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _write(*args, **kwargs):
            self.calls.append(("WRITE:" + name, args))
            return None
        return _write


# ---------------------------------------------------------------------------
# the seeded KB (four products; hand-computed metrics below)
# ---------------------------------------------------------------------------

PA = "fragrances|acme|nimbus noir|edp"
PB = "fragrances|zephyra|velvet dusk|edt"
PC = "fragrances|orvel|amber field|edp"
PD = "fragrances|lumio|quiet tide|edc"


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _robots(host):
    return {"state": "allow", "origin": "https://" + host, "fetched_at": _iso(NOW - timedelta(hours=1)),
            "next_reread": _iso(NOW + timedelta(hours=23))}


def _merchant(host, status):
    return {"host": host, "status": status, "deny": False, "blocked_reason": "manual" if status == "blocked" else None,
            "registry": [], "robots": _robots(host), "challenge": None, "tos": None, "currency_hint": "BHD",
            "country": "BH", "platform": None, "updated_at": _iso(NOW)}


def _tables():
    spec = lambda pid, field, cited: {"product_id": pid, "field": field, "cited": cited, "lang": "en"}  # noqa: E731
    return {
        "kb_products": [
            {"id": PA, "brand": "Acme", "name": "Nimbus Noir", "identity_confidence": "high", "concentration": "edp"},
            {"id": PB, "brand": "Zephyra", "name": "Velvet Dusk", "identity_confidence": "high", "concentration": "edt"},
            {"id": PC, "brand": "Orvel", "name": "Amber Field", "identity_confidence": "medium", "concentration": None},
            {"id": PD, "brand": "Lumio", "name": "Quiet Tide", "identity_confidence": "low", "concentration": "edc"},
        ],
        "kb_variants": [
            {"id": PA + "|100", "product_id": PA, "size_ml": 100},
            {"id": PB + "|-", "product_id": PB, "size_ml": None},
            {"id": PC + "|50", "product_id": PC, "size_ml": 50},
        ],
        "kb_offers_latest": [
            {"variant_id": PA + "|100", "last_seen": _iso(NOW - timedelta(hours=48)),
             "captured_at": _iso(NOW - timedelta(hours=240))},
            {"variant_id": PB + "|-", "last_seen": _iso(NOW - timedelta(hours=240)),
             "captured_at": _iso(NOW - timedelta(hours=480))},
            {"variant_id": PD + "|-", "last_seen": _iso(NOW - timedelta(hours=24)),
             "captured_at": _iso(NOW - timedelta(hours=24))},
        ],
        "kb_images": [{"product_id": PA}, {"product_id": PB}],
        "kb_specs": [
            spec(PA, "concentration", True), spec(PA, "scent_family", True), spec(PA, "season", True),
            spec(PB, "concentration", True), spec(PB, "scent_family", True), spec(PB, "season", False),
            spec(PD, "concentration", True), spec(PD, "scent_family", True), spec(PD, "season", True),
        ],
        "kb_reviews": [{"product_id": PA}],
        "kb_gaps": [
            {"field": "price", "state": "open"}, {"field": "image", "state": "open"},
            {"field": "size", "state": "needs_operator"}, {"field": "specs", "state": "licence"},
            {"field": "pdp_" + "a" * 16, "state": "queued"}, {"field": "pdp_" + "b" * 16, "state": "queued"},
            {"field": "pdp_" + "c" * 16, "state": "closed"},
        ],
        "search_logs": [
            {"products_found": ["Acme Nimbus Noir", "Unknown Item"], "success": True, "is_synthetic": False,
             "created_at": "2026-11-01T10:00:00+00:00"},
            {"products_found": ["Nimbus Noir", "Zephyra Velvet Dusk"], "success": True, "is_synthetic": None,
             "created_at": "2026-11-01T11:00:00+00:00"},
            {"products_found": ["Acme Nimbus Noir", "Zephyra Velvet Dusk"], "success": True, "is_synthetic": True,
             "created_at": "2026-11-01T12:00:00+00:00"},
            {"products_found": ["Acme Nimbus Noir", "Zephyra Velvet Dusk"], "success": False, "is_synthetic": False,
             "created_at": "2026-11-01T13:00:00+00:00"},
            {"products_found": ["Acme Nimbus Noir", "Zephyra Velvet Dusk"], "success": True, "is_synthetic": False,
             "created_at": "2026-10-31T13:00:00+00:00"},
        ],
        "kb_merchants": [_merchant(HOST_A, "live"), _merchant(HOST_B, "blocked"), _merchant(HOST_C, "candidate")],
    }


def _hashes():
    return {
        "kbh:20261101:" + HOST_A: {"curl:robots_skip": "3", "woo:robots_skip": "2", "curl:ok": "10",
                                   "curl:challenge": "1"},
        "kbh:20261101:" + HOST_C: {"curl:robots_skip": "9"},
    }


EXPECTED = {
    "kb.products.total": ("4", 4),
    "kb.products.identity_high_share": ("0.5", 4),
    "kb.field.offer_share": ("0.75", 4),
    "kb.field.offer_fresh_share": ("0.5", 4),
    "kb.field.image_share": ("0.5", 4),
    "kb.field.specs_cited_share": ("0.5", 4),
    "kb.field.rating_share": ("0.25", 4),
    "kb.field.size_share": ("0.5", 4),
    "kb.field.concentration_share": ("0.75", 4),
    "kb.field.complete_share": ("0.25", 4),
    "kb.price.age_median_hours": ("48", 3),
    "kb.price.capture_age_median_hours": ("240", 3),
    "kb.gaps.state.open": ("2", 2),
    "kb.gaps.state.queued": ("0", 0),
    "kb.gaps.state.needs_operator": ("1", 1),
    "kb.gaps.state.licence": ("1", 1),
    "kb.gaps.state.closed": ("0", 0),
    "kb.hints.state.queued": ("2", 2),
    "kb.hints.state.closed": ("1", 1),
    "kb.hints.state.needs_operator": ("0", 0),
    "proxy.identity_hit_share": ("0.75", 4),
    "proxy.pair_hit_share": ("0.5", 2),
    "host.robots_skip:" + HOST_A: ("5", 16),
    "host.challenge:" + HOST_A: ("1", 16),
}


def _run(monkeypatch, caplog, mode, *, tables=None, raise_on=(), redis="default", argv=None):
    mod = _mod()
    if mode is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, mode)
    client = _Client(tables if tables is not None else _tables(), raise_on=raise_on)
    rds = _Redis(_hashes()) if redis == "default" else redis
    caplog.set_level(logging.INFO)
    caplog.clear()
    rc = _attr(mod, "main")(list(argv or []), client=client, redis=rds)
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_COVERAGE]")]
    return rc, client, rds, lines


def _metrics(lines):
    out = {}
    for line in lines:
        m = METRIC_LINE.match(line)
        if m:
            out[m.group(1)] = (m.group(2), int(m.group(3)))
    return out


def _upserted(client):
    ups = [o for o in client.writes() if o["table"] == "kb_coverage_daily"]
    rows = []
    for o in ups:
        rows.extend(o["payload"] if isinstance(o["payload"], list) else [o["payload"]])
    return ups, {r["metric"]: r for r in rows}


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,want", [
    (None, "off"), ("", "off"), ("false", "off"), ("0", "off"), ("no", "off"), ("OFF", "off"),
    ("dry", "off"), ("garbage", "off"), ("true", "dry"), (" TRUE ", "dry"), ("1", "dry"), ("yes", "dry"),
    ("on", "dry"), ("apply", "apply"), (" APPLY ", "apply"),
])
def test_r1_entry_and_mode(monkeypatch, caplog, value, want):
    """R1: importable; the G2 mode matrix read per call; OFF inert (no client call, no
    Redis call, no app module newly imported, exit 0, one INFO line)."""
    mod = _mod()
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert _attr(mod, "coverage_mode")() == want, (value, want)
    if want != "off":
        return
    called = []
    monkeypatch.setattr(_common(), "_admin_client", lambda: called.append("admin") or _Client({}))
    before = {m for m in sys.modules if m == "app" or m.startswith("app.")}
    client, rds = _Client(_tables()), _Redis(_hashes())
    caplog.set_level(logging.INFO)
    caplog.clear()
    rc = _attr(mod, "main")([], client=None, redis=rds)
    after = {m for m in sys.modules if m == "app" or m.startswith("app.")}
    assert rc == 0
    assert called == [] and client.ops == [] and rds.calls == []
    assert sorted(after - before) == [], sorted(after - before)
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_COVERAGE]")]
    assert len(lines) == 1 and "mode=off" in lines[0], lines


def test_r2_metric_names_closed_and_valid(monkeypatch, caplog):
    """R2: the emitted names are exactly the closed 2.2 list for the seeded data, each
    matching KB_METRIC_REGEX (an absent host key and a candidate host emit nothing)."""
    from app.services import kb_service as kb
    rc, client, _r, lines = _run(monkeypatch, caplog, "true")
    assert rc == 0
    got = _metrics(lines)
    assert sorted(got) == sorted(EXPECTED), sorted(set(got) ^ set(EXPECTED))
    for name in got:
        assert re.match(kb.KB_METRIC_REGEX, name), name


def test_r3_values_on_seeded_kb(monkeypatch, caplog):
    """R3: the shares, the two medians (last_seen vs captured_at) and the gap / hint
    counts equal the hand-computed literals (APPLY rows and the log lines agree)."""
    _rc, client, _r, lines = _run(monkeypatch, caplog, "apply")
    _ups, rows = _upserted(client)
    for name, (value, n) in EXPECTED.items():
        assert name in rows, name
        assert Decimal(rows[name]["value"]) == Decimal(value), (name, rows[name]["value"], value)
        assert rows[name]["n"] == n, (name, rows[name]["n"], n)
    logged = _metrics(lines)
    for name, (value, n) in EXPECTED.items():
        assert Decimal(logged[name][0]) == Decimal(value) and logged[name][1] == n, (name, logged[name])


def test_r4_proxy_reads_no_personal_columns(monkeypatch, caplog):
    """R4: search_logs is selected with exactly the four columns (never user_id / query /
    error_message); synthetic and failed rows and other days are excluded."""
    _rc, client, _r, lines = _run(monkeypatch, caplog, "true")
    sel = [o for o in client.ops if o["table"] == "search_logs"]
    assert sel, "search_logs never read"
    for o in sel:
        assert o["op"] == "select" and o["columns"] == SEARCH_LOG_COLUMNS, o
    got = _metrics(lines)
    assert got["proxy.identity_hit_share"] == ("0.75", 4) or (
        Decimal(got["proxy.identity_hit_share"][0]) == Decimal("0.75")
        and got["proxy.identity_hit_share"][1] == 4), got["proxy.identity_hit_share"]
    assert Decimal(got["proxy.pair_hit_share"][0]) == Decimal("0.5") and got["proxy.pair_hit_share"][1] == 2


def test_r5_host_metrics_absent_never_zero(monkeypatch, caplog):
    """R5: a host with no kbh key emits no metric; curl 3 + woo 2 robots_skip -> 5; the
    counters come from ONE pipeline over the live + blocked hosts; never a Redis write."""
    _rc, _c, rds, lines = _run(monkeypatch, caplog, "true")
    got = _metrics(lines)
    assert Decimal(got["host.robots_skip:" + HOST_A][0]) == 5 and got["host.robots_skip:" + HOST_A][1] == 16
    assert not any(name.endswith(":" + HOST_B) for name in got), sorted(got)
    assert not any(name.endswith(":" + HOST_C) for name in got), sorted(got)
    keys = [c[1] for c in rds.calls if c[0] in ("pipeline.hgetall", "hgetall")]
    assert sorted(keys) == sorted(["kbh:20261101:" + HOST_A, "kbh:20261101:" + HOST_B]), keys
    assert [c for c in rds.calls if c[0] == "pipeline"] == [("pipeline",)], rds.calls
    assert not any(c[0].startswith("WRITE:") for c in rds.calls), rds.calls


def test_r6_apply_upserts_through_builder(monkeypatch, caplog):
    """R6: APPLY = ONE upsert with on_conflict "day,metric", every row the builder's
    output for the run day; DRY = no upsert at all."""
    from app.services import kb_service as kb
    _rc, client, _r, _l = _run(monkeypatch, caplog, "apply")
    ups, rows = _upserted(client)
    assert len(ups) == 1 and ups[0]["op"] == "upsert", ups
    assert ups[0]["kwargs"].get("on_conflict") == "day,metric", ups[0]["kwargs"]
    assert ups[0]["kwargs"].get("ignore_duplicates") in (None, False), ups[0]["kwargs"]
    assert len(rows) == len(EXPECTED)
    for name, row in rows.items():
        assert set(row) == {"day", "metric", "value", "n"} and row["day"] == "2026-11-01", row
        assert row == kb.build_coverage_row(day=DAY, metric=name, value=Decimal(row["value"]), n=row["n"]), row
    assert [o for o in client.writes() if o["table"] != "kb_coverage_daily"] == []
    _rc, client, _r, _l = _run(monkeypatch, caplog, "true")
    assert client.writes() == [], client.writes()
    _rc, client, _r, _l = _run(monkeypatch, caplog, "apply", argv=["--dry-run"])
    assert client.writes() == [], client.writes()


def test_r7_report_markdown(monkeypatch, caplog, tmp_path):
    """R7: the --report markdown holds the day, the metric / value / n table and the
    proxy disclaimer; no 8-digit run, no '@'."""
    out = tmp_path / "coverage.md"
    _run(monkeypatch, caplog, "true", argv=["--report", str(out)])
    assert out.is_file(), "no report written"
    text = out.read_text(encoding="ascii")
    assert "2026-11-01" in text
    assert re.search(r"^\|\s*metric\s*\|\s*value\s*\|\s*n\s*\|", text, re.M), text[:400]
    assert "kb.field.complete_share" in text
    assert re.search(r"proxy", text, re.I) and re.search(r"search_logs", text), text[-400:]
    assert not re.search(r"\d{8}", text), "an 8-digit run in the report"
    assert "@" not in text


def test_r8_failure_isolation(monkeypatch, caplog):
    """R8: a raising kb_specs read omits only the specs-dependent metrics (one WARNING
    with the type name); Redis None -> no host metric and totals redis=0."""
    _rc, client, _r, lines = _run(monkeypatch, caplog, "apply", raise_on={"kb_specs"}, redis=None)
    _ups, rows = _upserted(client)
    assert "kb.field.specs_cited_share" not in rows and "kb.field.complete_share" not in rows, sorted(rows)
    for name in ("kb.field.image_share", "kb.field.offer_share", "kb.gaps.state.open", "kb.products.total"):
        assert name in rows, name
    assert not any(name.startswith("host.") for name in rows), sorted(rows)
    totals = [ln for ln in lines if ln.startswith("[KB_COVERAGE] totals")]
    assert len(totals) == 1 and TOTALS_LINE.match(totals[0]) and totals[0].endswith("redis=0"), totals
    warns = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING
             and r.getMessage().startswith("[KB_COVERAGE]")]
    assert warns and all("RuntimeError" in w for w in warns), warns


def test_r9_railway_config_and_hygiene():
    """R9: railway.kbcoverage.json as C2; the script and the config LF and pure ASCII."""
    assert CONFIG.is_file(), "railway.kbcoverage.json does not exist (D17 not implemented)"
    cfg = json.loads(CONFIG.read_text(encoding="ascii"))
    assert cfg["build"]["watchPatterns"] == [
        "scripts/cron_kb_coverage.py", "scripts/kb_seed_common.py", "railway.kbcoverage.json"], cfg
    assert cfg["deploy"]["startCommand"] == "python -m scripts.cron_kb_coverage", cfg
    assert cfg["deploy"]["restartPolicyType"] == "NEVER", cfg
    assert SCRIPT.is_file(), "scripts/cron_kb_coverage.py does not exist (D17 not implemented)"
    for path in (SCRIPT, CONFIG):
        raw = path.read_bytes()
        assert b"\r" not in raw, path.name
        assert all(b < 128 for b in raw), path.name

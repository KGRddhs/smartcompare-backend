"""D17b COVERAGE-PAGING RED rows (spec S81-G7, unit D17b section 5, as amended by
RULINGS_S81_G7 R-G7-5): scripts/cron_kb_coverage.py ``_paged`` orders every paged read by
the primary key ``id`` (PostgREST paging without an ORDER BY is not stable above one
page), and the host pipeline runs through the live_robots ``exec`` / ``execute`` fallback
(upstash-redis 1.7.0: ``exec`` runs the queue, its one-argument ``execute`` only queues;
redis-py 8.1.0: ``execute`` runs).

No new flag: rides ENABLE_KB_COVERAGE_ROLLUP. The rows reuse the frozen D17 RED file's
fakes and seeded world (``tests.test_s81_d17_coverage``) plus local recorders.

Every RED row fails at base on an AssertionError only. The PIN rows are green at base and
run with the full configuration (client rows, Redis hashes, the knob set) and recorders.

Hygiene: pure ASCII, LF; bounded runner only; netguard on (in-memory fakes); synthetic
hosts and identities only; no 64-hex literal in one piece.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import logging

import pytest

D17 = "tests.test_s81_d17_coverage"
MOD = "scripts.cron_kb_coverage"
FLAG = "ENABLE_KB_COVERAGE_ROLLUP"
PAGED_RELATIONS = ("kb_products", "kb_offers_latest", "kb_variants", "kb_images", "kb_reviews", "kb_specs",
                   "kb_gaps", "search_logs")
OFF_SPELLINGS = [None, "", "false", " 0 ", "OFF", "garbage"]
# sha256 of the --report markdown bytes and of the APPLY upsert payload on the frozen D17
# world, recorded at base 6869a3e6 by the RED agent (split in two halves).
REPORT_SHA256_BASE = "05ef14afee9820b2fdf27adaf5aed997" + "609a508b5dcf0fbee1ec053ca264393b"
UPSERT_SHA256_BASE = "3f3a9a7a7502f7bf3ee1b48113ef1915" + "09f5ee9580e886fc23bd8fb25f17da31"


def _d17():
    return importlib.import_module(D17)


def _mod():
    return importlib.import_module(MOD)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    d17 = _d17()
    for name in (FLAG, "KB_COVERAGE_MAX_HOSTS", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(d17._common(), "_now", lambda: d17.NOW)
    yield


def _order_client(tables):
    """The frozen D17 client plus the orders and the range of every executed query."""
    d17 = _d17()

    class _OrderClient(d17._Client):
        def _execute(self, q):
            out = super()._execute(q)
            self.ops[-1]["orders"] = list(q.orders)
            self.ops[-1]["rng"] = q.rng
            return out
    return _OrderClient(tables)


def _main(monkeypatch, caplog, flag, client, redis, argv=()):
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)
    caplog.set_level(logging.INFO)
    caplog.clear()
    rc = _mod().main(list(argv), client=client, redis=redis)
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_COVERAGE]")]
    return rc, lines


# ---------------------------------------------------------------------------
# the unstable store (PostgREST without an ORDER BY)
# ---------------------------------------------------------------------------

class _UnstableQuery:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.orders, self.rng, self.filters, self.op = [], None, [], None

    def select(self, columns="*", **kwargs):
        self.op = "select"
        return self

    def order(self, column, desc=False, **kwargs):
        self.orders.append((column, bool(desc)))
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


class _UnstableClient:
    """Without an order, range request k of a table sees the rows rotated by 37 * k (an
    unstable scan order); with order("id") it sees the id-sorted rows."""

    def __init__(self, tables):
        self.tables = tables
        self.requests = {}
        self.read_ids = []

    def table(self, name):
        return _UnstableQuery(self, name)

    def _execute(self, q):
        d17 = _d17()
        rows = [dict(r) for r in self.tables.get(q.table, [])]
        k = self.requests.get(q.table, 0)
        self.requests[q.table] = k + 1
        if q.orders:
            for col, desc in reversed(q.orders):
                rows.sort(key=lambda r, c=col: str(r.get(c)), reverse=desc)
        elif rows:
            shift = (37 * k) % len(rows)
            rows = rows[shift:] + rows[:shift]
        if q.rng is not None:
            rows = rows[q.rng[0]:q.rng[1] + 1]
        if q.table == "kb_products":
            self.read_ids.extend(r.get("id") for r in rows)
        return d17._Resp(rows)


def _many_products(n):
    return [{"id": "fragrances|b|n-%05d" % i, "brand": "B", "name": "N %05d" % i,
             "identity_confidence": "high", "concentration": "edp"} for i in range(1, n + 1)]


# ---------------------------------------------------------------------------
# pipelines
# ---------------------------------------------------------------------------

class _PyPipe:
    """A redis-py style pipeline: execute() runs the queue; there is no exec."""

    def __init__(self, redis):
        self.redis, self.keys = redis, []

    def hgetall(self, key):
        self.redis.calls.append(("pipeline.hgetall", key))
        self.keys.append(key)
        return self

    def execute(self):
        self.redis.calls.append(("pipeline.execute", len(self.keys)))
        return [dict(self.redis.hashes.get(k, {})) for k in self.keys]

    def __getattr__(self, name):
        raise AttributeError(name)


class _UpPipe:
    """An upstash-redis style pipeline: exec() runs the queue; execute(command) only queues."""

    def __init__(self, redis):
        self.redis, self.keys = redis, []

    def hgetall(self, key):
        self.redis.calls.append(("pipeline.hgetall", key))
        self.keys.append(key)
        return self

    def exec(self):
        self.redis.calls.append(("pipeline.exec", len(self.keys)))
        return [dict(self.redis.hashes.get(k, {})) for k in self.keys]

    def execute(self, command):
        self.redis.calls.append(("pipeline.execute", list(command) if isinstance(command, list) else command))
        return self


def _redis_with(pipe_cls):
    d17 = _d17()

    class _R(d17._Redis):
        def pipeline(self):
            self.calls.append(("pipeline",))
            return pipe_cls(self)
    return _R(d17._hashes())


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_every_page_ordered_by_id(monkeypatch, caplog):
    """R1: DRY on the D17 world: every select of the eight paged relations orders by id asc."""
    d17 = _d17()
    client = _order_client(d17._tables())
    rc, _lines = _main(monkeypatch, caplog, "true", client, d17._Redis(d17._hashes()))
    assert rc == 0
    seen = set()
    for op in client.ops:
        if op["table"] in PAGED_RELATIONS and op["op"] == "select":
            seen.add(op["table"])
            assert op["orders"] == [("id", False)], (op["table"], op["orders"])
    assert seen == set(PAGED_RELATIONS), sorted(seen)


def test_r2_unordered_store_paged_completely(monkeypatch, caplog):
    """R2: 1,200 kb_products rows in an unstable store: the job reads every id exactly once."""
    client = _UnstableClient({"kb_products": _many_products(1200)})
    rc, lines = _main(monkeypatch, caplog, "true", client, None)
    assert rc == 0
    got = _d17()._metrics(lines)
    assert got["kb.products.total"][1] == 1200, got["kb.products.total"]
    assert len(client.read_ids) == 1200, len(client.read_ids)
    assert len(set(client.read_ids)) == 1200, "duplicate or missing ids: %d distinct" % len(set(client.read_ids))


def test_r3_redis_py_pipeline_executes(monkeypatch, caplog):
    """R3: a redis-py pipeline (execute only): the host metrics are present; totals redis=1."""
    d17 = _d17()
    host = d17.HOST_A
    rds = _redis_with(_PyPipe)
    rc, lines = _main(monkeypatch, caplog, "true", d17._Client(d17._tables()), rds)
    assert rc == 0
    got = d17._metrics(lines)
    assert "host.robots_skip:" + host in got, sorted(got)
    assert float(got["host.robots_skip:" + host][0]) == 5 and got["host.robots_skip:" + host][1] == 16
    totals = [ln for ln in lines if ln.startswith("[KB_COVERAGE] totals")]
    assert len(totals) == 1 and totals[0].endswith("redis=1"), totals


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

def test_p1_upstash_pipeline_uses_exec_never_queueing_execute(monkeypatch, caplog):
    """P1 (PIN): an upstash pipeline: exec runs once, the one-argument execute never; host metrics as D17 R5."""
    d17 = _d17()
    host = d17.HOST_A
    rds = _redis_with(_UpPipe)
    rc, lines = _main(monkeypatch, caplog, "true", d17._Client(d17._tables()), rds)
    assert rc == 0
    got = d17._metrics(lines)
    assert "host.robots_skip:" + host in got and "host.challenge:" + host in got, sorted(got)
    assert float(got["host.robots_skip:" + host][0]) == 5 and got["host.robots_skip:" + host][1] == 16, got
    assert float(got["host.challenge:" + host][0]) == 1 and got["host.challenge:" + host][1] == 16, got
    assert [c for c in rds.calls if c[0] == "pipeline.exec"] == [("pipeline.exec", 2)], rds.calls
    assert [c for c in rds.calls if c[0] == "pipeline.execute"] == [], rds.calls


def _report_and_payload(monkeypatch, caplog, tmp_path):
    d17 = _d17()
    out = tmp_path / "coverage.md"
    client = d17._Client(d17._tables())
    rc, _lines = _main(monkeypatch, caplog, "apply", client, d17._Redis(d17._hashes()),
                       argv=["--report", str(out)])
    assert rc == 0
    ups = [o for o in client.writes() if o["table"] == "kb_coverage_daily"]
    assert len(ups) == 1, ups
    payload = json.dumps(ups[0]["payload"], sort_keys=True, default=str).encode("ascii")
    return out.read_bytes(), payload


def test_p2_small_tables_byte_identical(monkeypatch, caplog, tmp_path):
    """P2 (PIN): the D17 world: the --report bytes and the APPLY upsert payload equal base."""
    report, payload = _report_and_payload(monkeypatch, caplog, tmp_path)
    assert hashlib.sha256(report).hexdigest() == REPORT_SHA256_BASE, report.decode("ascii")[:400]
    assert hashlib.sha256(payload).hexdigest() == UPSERT_SHA256_BASE, payload[:400]


@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=["unset", "empty", "false", "pad0", "OFF", "garbage"])
def test_p3_flag_off_no_io(monkeypatch, caplog, value):
    """P3 (PIN): the full configuration with the flag OFF: exit 0, zero client ops, zero Redis calls."""
    d17 = _d17()
    monkeypatch.setenv("KB_COVERAGE_MAX_HOSTS", "3")
    client = _order_client(d17._tables())
    rds = d17._Redis(d17._hashes())
    admin = []
    monkeypatch.setattr(d17._common(), "_admin_client", lambda: admin.append("admin") or client)
    rc, lines = _main(monkeypatch, caplog, value, client, rds, argv=["--report", "unused.md"])
    assert rc == 0
    assert client.ops == [] and rds.calls == [] and admin == [], (client.ops, rds.calls, admin)
    assert len(lines) == 1 and "mode=off" in lines[0], lines

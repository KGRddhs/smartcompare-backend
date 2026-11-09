"""S81-G10 / D-S22-J1 JUDGE-JSONB-FILTER -- RED and PIN rows.

Spec .qa-s80/S81-G10_UNIT_SPEC.md section J1.5 as amended by RULINGS_S81_G10 (R-G10-8: the
RED pins the REQUEST the pinned postgrest client sends, read through an httpx MockTransport
recorder, never the source text). Base 90d4ed74.

The judge's step 0 (`_resume`) reads the jsonb column compare_judgements.flags with a
containment filter. On the pinned postgrest 2.31.0 a Python list renders as the PostgreSQL
array literal `cs.{batch_pending}`, which PostgREST rejects on a jsonb column (400, the
2026-11-07 DRY run: errors.APIError=1, runs_read=0); the JSON operand `cs.["batch_pending"]`
is the form PostgREST parses as jsonb containment.

Every RED row fails at base on an AssertionError only (scripts.cron_compare_judge is resolved
through find_spec inside the test body and asserted). The doubles: a fake PostgREST behind a
REAL postgrest.SyncPostgrestClient (httpx.MockTransport: no socket; it answers 400 to the
array literal and 200 + one pending marker to the JSON form; unknown routes answer 200 []),
a fake Anthropic batches client, and breaker recorders on spend_breaker_enabled / reserve /
settle / record. Hermetic: no network, no .env, no credential (a synthetic low-entropy
ANTHROPIC_API_KEY value built at run time and set through monkeypatch only); synthetic ids.
Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.main as app_main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
import httpx
from postgrest import SyncPostgrestClient

from app.services import llm_spend_breaker as br
from scripts import kb_seed_common as common

ROOT = Path(__file__).resolve().parents[1]
MOD = "scripts.cron_compare_judge"
FLAG = "ENABLE_BATCH_JUDGE"
KNOBS = {"JUDGE_MAX_USD": "0.5", "JUDGE_MAX_RUNS": "50", "JUDGE_WINDOW_DAYS": "2", "JUDGE_SAMPLE_PCT": "10",
         "JUDGE_ESCALATION_MAX_PER_DAY": "3", "JUDGE_ESCALATION_MAX_USD": "0.2", "RECOMPARE_WINDOW_DAYS": "5"}
CLEAR = (FLAG, "ENABLE_JUDGE_WEB_SEARCH", "ANTHROPIC_API_KEY", "ENABLE_LLM_SPEND_BREAKER",
         "ANTHROPIC_MODEL_CRITIC", "ANTHROPIC_MODEL_ESCALATION", "ENABLE_COMPARE_RUN_LEDGER",
         "DEVICE_KEY_PEPPER") + tuple(KNOBS)
NOW = datetime(2026, 11, 9, 9, 0, 0, tzinfo=timezone.utc)
RUN_ID = "-".join(["0" * 8, "0" * 4, "4000", "8000", "0" * 11 + "1"])  # synthetic, built at run time
BATCH = "msgbatch_g10"
HAIKU = "claude-haiku-5-5"
BASE_URL = "https://probe.invalid/rest/v1"
JSON_OPERAND = 'cs.["batch_pending"]'
ARRAY_OPERAND = "cs.{batch_pending}"
RAW_JSON_PARAM = "flags=cs.%5B%22batch_pending%22%5D"
RAW_ARRAY_PREFIX = "cs.%7B"
SYN_VALUE = "s22j1-" + "synthetic-value"
OFF_SPELLINGS = [None, "", "false", "0", "off", " FALSE "]
OFF_IDS = ["unset", "empty", "false", "zero", "off", "padded-FALSE"]

# P2: the DRY request list with no pending rows (the resume read's flags param set aside),
# recorded at base 90d4ed74 on the pinned postgrest 2.31.0 with KNOBS and NOW above
# (a transport answering 200 [] to both operand forms).
DRY_REQUESTS_BASE = [
    ["GET", "compare_judgements", [["select", "run_id,batch_id,model,flags"], ["judge", "eq.haiku"],
                                   ["order", "id.asc"], ["offset", "0"], ["limit", "500"]]],
    ["GET", "compare_runs", [["select", "id,created_at,query_hmac,device_key,recompare"],
                             ["created_at", "gte.2026-11-02T09:00:00+00:00"], ["order", "id.asc"],
                             ["offset", "0"], ["limit", "500"]]],
    ["GET", "compare_runs", [["select", "id,created_at,consent_version,comparison_id,compare_request_id,"
                                        "device_key,query_hmac,llm_calls,evidence,winner_supported,"
                                        "identity_confidence,judged_at,recompare"],
                             ["created_at", "gte.2026-11-07T09:00:00+00:00"], ["judged_at", "is.null"],
                             ["consent_version", "gte.3"], ["order", "id.asc"], ["offset", "0"],
                             ["limit", "500"]]],
    ["HEAD", "compare_runs", [["select", "id"], ["created_at", "lt.2026-11-07T09:00:00+00:00"],
                              ["judged_at", "is.null"]]],
    ["HEAD", "compare_judgements", [["select", "id"], ["judge", "eq.sonnet"],
                                    ["created_at", "gte.2026-11-08T21:00:00+00:00"]]],
    ["HEAD", "compare_runs", [["select", "id"], ["created_at", "lt.2025-11-09T09:00:00+00:00"]]],
    ["HEAD", "kb_feedback", [["select", "id"], ["created_at", "lt.2025-11-09T09:00:00+00:00"]]],
]
RESUME_PARAMS_JSON = [["select", "run_id,batch_id,model,flags"], ["judge", "eq.haiku"], ["flags", JSON_OPERAND],
                      ["order", "id.asc"], ["offset", "0"], ["limit", "500"]]
UPSERT_COLUMNS = {"run_id", "judge", "model", "batch_id", "verdicts", "flags", "note", "cost_usd"}


def _cj():
    spec = importlib.util.find_spec(MOD)
    assert spec is not None, "scripts/cron_compare_judge.py is missing"
    return importlib.import_module(MOD)


class FakePostgrest:
    """The PostgREST double behind the real client: records every request and answers the
    resume read by its operand form (400 / 22P02 to the array literal, as production did;
    200 + the pending markers to the JSON form)."""

    def __init__(self, pending=None, lenient=False):
        self.pending = list(pending or [])
        self.lenient = lenient
        self.requests = []

    def handler(self, request):
        params = [list(p) for p in request.url.params.multi_items()]
        raw_query = request.url.query.decode("ascii") if isinstance(request.url.query, bytes) else str(
            request.url.query)
        body = request.content.decode("utf-8") if request.content else ""
        self.requests.append({"method": request.method, "table": request.url.path.rsplit("/", 1)[-1],
                              "params": params, "raw_query": raw_query,
                              "prefer": request.headers.get("prefer"),
                              "json": json.loads(body) if body else None})
        flags = dict(request.url.params.multi_items()).get("flags")
        if request.url.path.endswith("/compare_judgements") and flags is not None:
            if flags == JSON_OPERAND or self.lenient:
                return httpx.Response(200, json=[dict(r) for r in self.pending])
            if flags == ARRAY_OPERAND:
                return httpx.Response(400, json={"code": "22P02", "message": "invalid input syntax for type json",
                                                 "details": None, "hint": None})
            return httpx.Response(400, json={"code": "PGRST100", "message": "unexpected operand",
                                             "details": None, "hint": None})
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-range": "*/0"})
        return httpx.Response(200, json=[], headers={"content-range": "*/0"})

    def client(self):
        return SyncPostgrestClient(base_url=BASE_URL, headers={"apikey": "probe"},
                                   http_client=httpx.Client(base_url=BASE_URL,
                                                            transport=httpx.MockTransport(self.handler)))

    def of(self, method=None, table=None):
        return [r for r in self.requests
                if (method is None or r["method"] == method) and (table is None or r["table"] == table)]

    def resume_reads(self):
        return [r for r in self.requests if r["table"] == "compare_judgements"
                and any(p[0] == "flags" for p in r["params"])]


def _marker():
    return {"run_id": RUN_ID, "batch_id": BATCH, "model": HAIKU, "flags": ["batch_pending"]}


def _answer_text():
    return json.dumps({"identity_ok": True, "price_ok": True, "specs_ok": True, "verdict_supported": True,
                       "flags": [], "note": "fine"})


class FakeAnthropic:
    def __init__(self, cj, *, status="ended", retrieve_raise=None):
        self.cj = cj
        self.status = status
        self.retrieve_raise = retrieve_raise
        self.order = []
        self.deleted = []
        self.factory_calls = []
        self.messages = SimpleNamespace(batches=SimpleNamespace(
            create=self._create, retrieve=self._retrieve, results=self._results, delete=self._delete))

    def factory(self, **kw):
        self.factory_calls.append(sorted(kw))
        return self

    def _create(self, requests):
        self.order.append(("batches.create", len(requests)))
        return {"id": "msgbatch_unexpected"}

    def _retrieve(self, batch_id):
        self.order.append(("batches.retrieve", batch_id))
        if self.retrieve_raise is not None:
            raise self.retrieve_raise
        return {"processing_status": self.status}

    def _results(self, batch_id):
        self.order.append(("batches.results", batch_id))
        yield {"custom_id": self.cj.custom_id(RUN_ID), "result": {"type": "succeeded", "message": {
            "stop_reason": "end_turn", "content": [{"text": _answer_text()}],
            "usage": {"input_tokens": 1000, "output_tokens": 50}}}}

    def _delete(self, batch_id):
        self.deleted.append(batch_id)
        self.order.append(("batches.delete", batch_id))


class Breaker:
    def __init__(self, monkeypatch, enabled):
        self.calls = []
        self.enabled = enabled
        monkeypatch.setattr(br, "spend_breaker_enabled", lambda: self.enabled)

        def _reserve(lane, bound):
            self.calls.append(("reserve", lane))
            return SimpleNamespace(lane=lane, bound=bound)

        def _settle(ticket, actual):
            self.calls.append(("settle", getattr(ticket, "lane", None)))

        def _record(lane, actual, admitted_usd=None):
            self.calls.append(("record", lane))

        monkeypatch.setattr(br, "reserve", _reserve)
        monkeypatch.setattr(br, "settle", _settle)
        monkeypatch.setattr(br, "record", _record)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    mod = importlib.import_module(MOD) if importlib.util.find_spec(MOD) is not None else None
    if mod is not None:
        monkeypatch.setattr(mod, "_now", lambda: NOW, raising=False)
        monkeypatch.setattr(mod, "_sleep", lambda _s: None, raising=False)
    monkeypatch.setattr(common, "_now", lambda: NOW, raising=False)

    def _no_admin():
        raise AssertionError("the service-role client was built")

    monkeypatch.setattr(common, "_admin_client", _no_admin)
    yield


def _full(monkeypatch, *, mode, key, companions):
    for name, value in KNOBS.items():
        monkeypatch.setenv(name, value)
    if mode is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, mode)
    if key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", SYN_VALUE)
    monkeypatch.setenv("ENABLE_JUDGE_WEB_SEARCH", "true" if companions else "false")
    monkeypatch.setenv("ENABLE_LLM_SPEND_BREAKER", "true" if companions else "false")
    return Breaker(monkeypatch, enabled=companions)


def _run(cj, fake, tmp_path, fa=None):
    path = tmp_path / "judge_report.json"
    rc = cj.main(["--report", str(path)], client=fake.client(),
                 anthropic_factory=fa.factory if fa is not None else None)
    report = json.loads(path.read_text(encoding="ascii")) if path.exists() else None
    return rc, report


def _flags_param(req):
    vals = [p[1] for p in req["params"] if p[0] == "flags"]
    return vals[0] if vals else None


# =============================================================== RED rows (R1-R6)

def test_r1_resume_operand_is_json(monkeypatch, tmp_path):
    """R1: DRY main over the real client: the resume read sends `flags=cs.["batch_pending"]`
    (the decoded param), every other param of that request unchanged."""
    cj = _cj()
    _full(monkeypatch, mode="true", key=False, companions=False)
    fake = FakePostgrest(pending=[_marker()])
    rc, _report = _run(cj, fake, tmp_path)
    assert rc == 0
    reads = fake.resume_reads()
    assert len(reads) == 1, [(r["method"], r["table"]) for r in fake.requests]
    got = _flags_param(reads[0])
    assert got == JSON_OPERAND, "the resume read sent %r (the PostgreSQL array literal 400s on jsonb)" % (got,)
    assert reads[0]["method"] == "GET" and reads[0]["params"] == RESUME_PARAMS_JSON, reads[0]["params"]


def test_r2_resume_raw_query(monkeypatch, tmp_path):
    """R2: the same request's RAW query carries the percent-encoded JSON operand and no
    array-literal brace."""
    cj = _cj()
    _full(monkeypatch, mode="true", key=False, companions=False)
    fake = FakePostgrest(pending=[_marker()])
    _run(cj, fake, tmp_path)
    raw = fake.resume_reads()[0]["raw_query"]
    assert RAW_JSON_PARAM in raw, raw
    assert RAW_ARRAY_PREFIX not in raw, raw


def test_r3_dry_end_to_end_provider_absent(monkeypatch, tmp_path):
    """R3: DRY, no ANTHROPIC_API_KEY: the fake PostgREST (400 to the array literal) finds
    the pending marker: errors {}, resume.batches 1, resume.still_pending 1, rc 0."""
    cj = _cj()
    _full(monkeypatch, mode="true", key=False, companions=False)
    fake = FakePostgrest(pending=[_marker()])
    rc, report = _run(cj, fake, tmp_path)
    assert rc == 0
    assert report["errors"] == {}, report["errors"]
    assert report["resume"]["batches"] == 1 and report["resume"]["still_pending"] == 1, report["resume"]
    assert report["mode"] == "dry"


def test_r4_dry_end_to_end_batch_ended(monkeypatch, tmp_path):
    """R4: DRY with the provider: an ended batch is read (resume.filled 1) and NOTHING is
    written (no POST / PATCH / DELETE request, no ledger insert, no batches.delete)."""
    cj = _cj()
    _full(monkeypatch, mode="true", key=True, companions=False)
    fake = FakePostgrest(pending=[_marker()])
    fa = FakeAnthropic(cj, status="ended")
    rc, report = _run(cj, fake, tmp_path, fa)
    assert rc == 0
    assert report["resume"]["filled"] == 1, (report["resume"], report["errors"])
    assert report["errors"] == {}, report["errors"]
    assert [r["method"] for r in fake.requests if r["method"] not in ("GET", "HEAD")] == []
    assert fake.of(table="llm_spend_ledger") == [] and fa.deleted == []
    assert ("batches.retrieve", BATCH) in fa.order and ("batches.results", BATCH) in fa.order


def test_r5_apply_end_to_end_batch_ended(monkeypatch, tmp_path):
    """R5: apply, an ended batch: exactly ONE llm_spend_ledger POST, ONE compare_judgements
    upsert (POST, on_conflict run_id,judge) carrying the haiku row with flags [], ONE
    compare_runs PATCH judged_at (a clean answer) and ONE batches.delete."""
    cj = _cj()
    _full(monkeypatch, mode="apply", key=True, companions=False)
    fake = FakePostgrest(pending=[_marker()])
    fa = FakeAnthropic(cj, status="ended")
    rc, report = _run(cj, fake, tmp_path, fa)
    assert rc == 0
    assert report["resume"]["filled"] == 1, (report["resume"], report["errors"])
    ledger = fake.of("POST", "llm_spend_ledger")
    assert len(ledger) == 1, [(r["method"], r["table"]) for r in fake.requests]
    assert ledger[0]["json"]["provider_batch_id"] == BATCH and ledger[0]["json"]["model"] == HAIKU
    ups = fake.of("POST", "compare_judgements")
    assert len(ups) == 1, ups
    params = dict(ups[0]["params"])
    assert params.get("on_conflict") == "run_id,judge", params
    assert set(params.get("columns", "").replace('"', "").split(",")) == UPSERT_COLUMNS, params
    assert "resolution=merge-duplicates" in (ups[0]["prefer"] or ""), ups[0]["prefer"]
    rows = ups[0]["json"]
    assert isinstance(rows, list) and len(rows) == 1, rows
    assert rows[0]["run_id"] == RUN_ID and rows[0]["judge"] == "haiku" and rows[0]["flags"] == [], rows
    assert rows[0]["batch_id"] == BATCH and rows[0]["verdicts"] and all(rows[0]["verdicts"].values()), rows
    patches = fake.of("PATCH", "compare_runs")
    assert len(patches) == 1, patches
    assert patches[0]["params"] == [["id", "in.(%s)" % RUN_ID]] and set(patches[0]["json"]) == {"judged_at"}
    assert patches[0]["json"]["judged_at"] == "2026-11-09T09:00:00+00:00"
    assert fa.deleted == [BATCH]
    assert report["ledger"] == {"failed": 0, "written": 1} and report["judged_at_set"] == 1


def test_r6_apply_batch_lost(monkeypatch, tmp_path):
    """R6: apply, retrieve raises a 404-shaped error: ONE upsert of the marker row with
    flags ["batch_lost"]; resume.lost 1; no ledger row, no judged_at, no delete."""
    cj = _cj()
    _full(monkeypatch, mode="apply", key=True, companions=False)
    fake = FakePostgrest(pending=[_marker()])
    lost = type("NotFoundError", (Exception,), {"status_code": 404})
    fa = FakeAnthropic(cj, retrieve_raise=lost("gone"))
    rc, report = _run(cj, fake, tmp_path, fa)
    assert rc == 0
    assert report["resume"]["lost"] == 1, (report["resume"], report["errors"])
    ups = fake.of("POST", "compare_judgements")
    assert len(ups) == 1, ups
    assert dict(ups[0]["params"]).get("on_conflict") == "run_id,judge"
    rows = ups[0]["json"]
    assert [(r["run_id"], r["judge"], r["flags"], r["batch_id"]) for r in rows] == [
        (RUN_ID, "haiku", ["batch_lost"], BATCH)], rows
    assert fake.of("POST", "llm_spend_ledger") == [] and fake.of("PATCH", "compare_runs") == []
    assert fa.deleted == []


# =============================================================== PIN rows (P1-P4)

@pytest.mark.parametrize("companions", [True, False], ids=["companions-on", "companions-off"])
@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p1_off_makes_no_request(monkeypatch, tmp_path, value, companions):
    """P1 (PIN, the FULL configuration): with ENABLE_BATCH_JUDGE unset / blank / false / 0 /
    off / padded FALSE the run returns 0 before ANY read: zero requests on the transport,
    the service-role client factory never called, the Anthropic factory never called, no
    breaker call, no report file."""
    cj = _cj()
    breaker = _full(monkeypatch, mode=value, key=True, companions=companions)
    fake = FakePostgrest(pending=[_marker()], lenient=True)
    built = []

    def _admin():
        built.append("admin")
        return fake.client()

    monkeypatch.setattr(common, "_admin_client", _admin)
    fa = FakeAnthropic(cj, status="ended")
    path = tmp_path / "judge_report.json"
    rc = cj.main(["--report", str(path)], client=None, anthropic_factory=fa.factory)
    assert rc == 0
    assert fake.requests == [] and built == [] and fa.factory_calls == [] and fa.order == []
    assert breaker.calls == [] and not path.exists()


@pytest.mark.parametrize("companions", [True, False], ids=["companions-on", "companions-off"])
def test_p2_other_requests_unchanged(monkeypatch, tmp_path, companions):
    """P2 (PIN): DRY with no pending rows: the ordered (method, table, params) list, the
    resume read's flags param set aside, equals the list recorded at base; the flags param
    is one of the two operand forms; nothing is written."""
    cj = _cj()
    breaker = _full(monkeypatch, mode="true", key=False, companions=companions)
    fake = FakePostgrest(pending=[], lenient=True)
    rc, report = _run(cj, fake, tmp_path)
    assert rc == 0 and report["errors"] == {}, report["errors"]
    got = [[r["method"], r["table"], [p for p in r["params"] if p[0] != "flags"]] for r in fake.requests]
    assert got == DRY_REQUESTS_BASE, json.dumps(got, indent=1)
    assert _flags_param(fake.requests[0]) in (JSON_OPERAND, ARRAY_OPERAND)
    assert breaker.calls == []


def _py_files(*roots):
    for root in roots:
        for path in sorted((ROOT / root).rglob("*.py")):
            yield path


def test_p3_containment_sweep():
    """P3 (PIN): over app/ and scripts/ exactly ONE `.contains(` call on a chained PostgREST
    builder (the judge's _resume), no `.overlaps(` / `.ov(` / `.cs(` / `.cd(` /
    `.contained_by(` call and no string literal starting `cs.{` / `ov.{` / `cd.{`."""
    contains, other, literals = [], [], []
    for path in _py_files("app", "scripts"):
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(node):
                    funcs.setdefault(id(sub), node.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if attr == "contains" and isinstance(node.func.value, ast.Call):
                    contains.append((rel, funcs.get(id(node))))
                elif attr in ("overlaps", "ov", "cs", "cd", "contained_by"):
                    other.append((rel, node.lineno, attr))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.startswith(("cs.{", "ov.{", "cd.{")):
                    literals.append((rel, node.lineno))
    assert contains == [("scripts/cron_compare_judge.py", "_resume")], contains
    assert other == [] and literals == [], (other, literals)


def test_p4_flags_column_is_jsonb_array():
    """P4 (PIN): 048 declares compare_judgements.flags as a jsonb array (the operand PostgREST
    parses as JSON)."""
    sql = " ".join((ROOT / "migrations" / "048_compare_runs.sql").read_text(encoding="utf-8").split())
    assert "flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(flags) = 'array')" in sql

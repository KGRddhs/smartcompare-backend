"""S81-SF1 SURFACES-BE -- the GREEN-owned gate rows (GATE_S81_SF1 GC-10).

G-SF1-GR1  the three narrowed except arms (feedback_service.save_feedback,
           feedback_service.track_events_batch, database_service.log_search) log one
           constants-only line each: no exc_info / stack_info, no f-string, no exception
           object or its text as an argument (R-SF1-27), read from the AST.
G-SF1-GR2  the ONE client line: SmartCompareApp/src/screens/HomeScreen.tsx carries
           exactly one trackEvent('category_coming_soon_tap' literal, inside
           handleComingSoon, after the iOS announce and before the toast timer; the
           launchSurfaces service carries none (read by path from the repo root).
G-SF1-GR3  migration 046 writes the 'sf1_dropped_not_null' column comment inside its
           guarded DROP NOT NULL block, and its rollback gates SET NOT NULL on
           col_description(...) = 'sf1_dropped_not_null' with no short-circuit
           ('IF TRUE OR' shape absent). The behavioural proof is the G9 cluster run of
           the GREEN report (GC-5, M40b).
G-SF1-GR4  the merchant_id value rule of the events filter is the KB host pattern
           (migration 045's kb_merchants host CHECK): feedback_routes pins it equal to
           the KB leaf's constant (feedback_routes may not import the leaf).
G-SF1-GR5  database_service.postgrest_error_code returns None, never exception text, for a
           ValueError, an httpx.ConnectError and a code-less / text-code APIError whose
           str carries a synthetic failing-row marker; the three narrowed except-arm
           records carry no marker, in both flag states (the final round, RB-SF1-2a).
G-SF1-GR6  a 300-character host-shaped store_cta_tap merchant_id is DROPPED by the
           unflagged property filter (the 253-character cap in use; a 253-character
           host is kept), counted once in the INFO line (the final round, RB-SF1-2a).

Pure ASCII, LF; reads files only, no network.
"""
from __future__ import annotations

import ast
import asyncio
import logging
import re
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]

ARMS = (
    ("app/services/feedback_service.py", "save_feedback",
     "[FEEDBACK] save failed type=%s code=%s"),
    ("app/services/feedback_service.py", "track_events_batch",
     "[EVENTS] batch insert failed type=%s code=%s"),
    ("app/services/database_service.py", "log_search",
     "[SEARCH_LOG] insert failed type=%s code=%s"),
)


def _function(rel, name):
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError("%s: %s not found" % (rel, name))


def _is_logger_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "logger")


def _allowed_arg(arg, exc_name):
    """type(<exc>).__name__ or postgrest_error_code(<exc>): a class name or a short code."""
    if (isinstance(arg, ast.Attribute) and arg.attr == "__name__"
            and isinstance(arg.value, ast.Call) and isinstance(arg.value.func, ast.Name)
            and arg.value.func.id == "type" and len(arg.value.args) == 1
            and isinstance(arg.value.args[0], ast.Name) and arg.value.args[0].id == exc_name):
        return True
    if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
            and arg.func.id == "postgrest_error_code" and len(arg.args) == 1
            and isinstance(arg.args[0], ast.Name) and arg.args[0].id == exc_name
            and not arg.keywords):
        return True
    return False


def test_gr1_except_arms_log_constants_only():
    for rel, fn_name, template in ARMS:
        fn = _function(rel, fn_name)
        handlers = [n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]
        assert len(handlers) == 1, (rel, fn_name, len(handlers))
        handler = handlers[0]
        exc_name = handler.name
        assert exc_name, (rel, fn_name, "the arm must bind the exception")
        calls = [n for n in ast.walk(handler) if _is_logger_call(n)]
        assert len(calls) == 1, (rel, fn_name, len(calls))
        call = calls[0]
        assert call.func.attr == "warning", (rel, fn_name, call.func.attr)
        kw = [k.arg for k in call.keywords]
        assert kw == [], (rel, fn_name, "keywords on the log call: %s" % kw)
        assert call.args, (rel, fn_name)
        first = call.args[0]
        assert isinstance(first, ast.Constant) and first.value == template, (
            rel, fn_name, ast.dump(first)[:120])
        rest = call.args[1:]
        assert len(rest) == 2, (rel, fn_name, len(rest))
        for arg in rest:
            assert _allowed_arg(arg, exc_name), (rel, fn_name, ast.dump(arg)[:160])
        for node in ast.walk(call):
            assert not isinstance(node, ast.JoinedStr), (rel, fn_name, "an f-string")


HOME = ROOT / "SmartCompareApp" / "src" / "screens" / "HomeScreen.tsx"
LAUNCH = ROOT / "SmartCompareApp" / "src" / "services" / "launchSurfaces.ts"
NEEDLE = "trackEvent('category_coming_soon_tap'"


def test_gr2_client_line_once_inside_handle_coming_soon():
    text = HOME.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text.count(NEEDLE) == 1, text.count(NEEDLE)
    start = text.index("const handleComingSoon = ")
    end = text.index("\n  };\n", start)
    body = text[start:end]
    at = body.find(NEEDLE)
    assert at >= 0, "the line is outside handleComingSoon"
    line = body[at:body.index("\n", at)]
    assert line == "trackEvent('category_coming_soon_tap', { category: key });", line
    announce = body.index("announceForAccessibility")
    timer = body.index("comingSoonTimerRef.current = setTimeout(")
    assert announce < at < timer, (announce, at, timer)
    assert NEEDLE not in LAUNCH.read_text(encoding="utf-8")


M046 = ROOT / "migrations" / "046_comparison_feedback_v2.sql"
R046 = ROOT / "migrations" / "rollback" / "046_comparison_feedback_v2.sql"


def _sql_code(path):
    lines = path.read_text(encoding="ascii").replace("\r\n", "\n").split("\n")
    return re.sub(r"\s+", " ", " ".join(ln for ln in lines if not ln.strip().startswith("--")))


def test_gr3_046_comment_and_rollback_gate():
    code = _sql_code(M046)
    assert code.count("COMMENT ON COLUMN public.comparison_feedback.useful IS "
                      "'sf1_dropped_not_null';") == 1
    drop = code.index("ALTER COLUMN useful DROP NOT NULL;")
    comment = code.index("COMMENT ON COLUMN public.comparison_feedback.useful IS "
                         "'sf1_dropped_not_null'")
    guard = code.rindex("= 'NO' THEN", 0, drop)
    assert guard < drop < comment < code.index("END IF;", comment)
    rb = _sql_code(R046)
    gate = re.search(r"IF\s+col_description\(\s*'public\.comparison_feedback'::regclass", rb)
    assert gate, "the rollback's SET NOT NULL is not gated on col_description first"
    assert re.search(r"\)\)\s*=\s*'sf1_dropped_not_null'\s+THEN", rb), "the gate value"
    assert not re.search(r"\bIF\s+(TRUE|1\s*=\s*1|NOT\s+FALSE)\s+OR\b", rb, re.I), "short-circuit"
    assert not re.search(r"\bOR\s+TRUE\b", rb, re.I), "short-circuit"
    set_nn = rb.index("ALTER COLUMN useful SET NOT NULL")
    assert gate.start() < set_nn
    assert rb.index("COMMENT ON COLUMN public.comparison_feedback.useful IS NULL") > set_nn


def test_gr4_merchant_rule_is_the_kb_host_pattern():
    from app.api import feedback_routes as fr
    from app.services import kb_service as kb

    assert fr.MERCHANT_HOST_PATTERN == kb.KB_HOST_REGEX
    assert fr.MERCHANT_HOST_MAX_CHARS == 253


# --------------------------------------------------------------- G-SF1-GR5 / GR6
# The final round (RULINGS_REBASE_S81_SF1 RB-SF1-2a; the correctness adversary's m1 / m3).

_FLAG_NAMES = ("ENABLE_FEEDBACK_V2", "ENABLE_SURFACES_FIELD", "APP_SURFACES_LIVE",
               "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", "ENABLE_SYNC_DB_OFFLOAD")


class _Records(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        if not any(r is record for r in self.records):
            self.records.append(record)


def _capture(loggers):
    handler = _Records()
    saved = []
    for lg in loggers:
        saved.append((lg, lg.level))
        lg.setLevel(logging.DEBUG)
        lg.addHandler(handler)

    def _release():
        for lg, level in saved:
            lg.removeHandler(handler)
            lg.setLevel(level)

    return handler.records, _release


def _formatted(record):
    return logging.Formatter("%(name)s %(levelname)s %(message)s").format(record)


def _marker():
    return "sf1-gr5-row-" + uuid.uuid4().hex[:8]


def _failures(marker):
    """A ValueError, an httpx.ConnectError, a code-less APIError and a text-code APIError,
    each carrying a synthetic failing-row marker in its str."""
    import httpx
    from postgrest.exceptions import APIError

    row = "Failing row contains (sf1-row, " + marker + ")."
    return [
        ValueError(row),
        httpx.ConnectError(row),
        APIError({"message": row, "details": row, "hint": None}),
        APIError({"message": row, "code": marker, "details": row, "hint": None}),
    ]


def _raising_client(exc):
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = exc
    return client


@pytest.mark.parametrize("state", [None, "true"])
def test_gr5_postgrest_error_code_never_returns_exception_text(monkeypatch, state):
    from app.main import app  # noqa: F401 - import first (the dotenv guard)
    from app.services import database_service as ds
    from app.services import feedback_service as fs

    for name in _FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    if state is not None:
        monkeypatch.setenv("ENABLE_FEEDBACK_V2", state)
    marker = _marker()
    for exc in _failures(marker):
        assert ds.postgrest_error_code(exc) is None, (type(exc).__name__,)
    records, release = _capture([logging.getLogger(), fs.logger, ds.logger,
                                 logging.getLogger("app")])
    try:
        for exc in _failures(marker):
            monkeypatch.setattr(fs, "get_supabase_client", lambda e=exc: _raising_client(e))
            monkeypatch.setattr(ds, "get_supabase_client", lambda e=exc: _raising_client(e))
            out = asyncio.run(fs.save_feedback(user_id=None, comparison_id=None, useful=True,
                                               mattered_most=[], change_suggestion=None))
            assert out["success"] is False
            asyncio.run(fs.track_events_batch([{"event_type": "save", "event_data": {}}]))
            asyncio.run(ds.log_search("sf1-gr5-query", user_id="sf1-gr5"))
    finally:
        release()
    warn = [r.getMessage() for r in records if r.levelno >= logging.WARNING]
    expected = []
    for exc in _failures(marker):
        cls = type(exc).__name__
        expected += ["[FEEDBACK] save failed type=%s code=None" % cls,
                     "[EVENTS] batch insert failed type=%s code=None" % cls,
                     "[SEARCH_LOG] insert failed type=%s code=None" % cls]
    assert warn == expected, warn
    for r in records:
        text = _formatted(r)
        assert marker not in text, text[:300]
        assert "Failing row" not in text, text[:300]


def test_gr6_merchant_host_cap_in_use(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.api import feedback_routes as fr

    for name in _FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    long_host = "m" * (300 - len(".com")) + ".com"
    edge_host = "m" * (253 - len(".com")) + ".com"
    assert len(long_host) == 300 and len(edge_host) == 253
    pattern = re.compile(fr.MERCHANT_HOST_PATTERN)
    assert pattern.fullmatch(long_host) and pattern.fullmatch(edge_host)
    assert fr._filter_event_properties("store_cta_tap", {"merchant_id": long_host}) == ({}, 1)
    assert fr._filter_event_properties("store_cta_tap", {"merchant_id": edge_host}) == (
        {"merchant_id": edge_host}, 0)

    calls = []

    async def _noop():
        return []

    def _rec(events):
        calls.append([dict(e) for e in events])
        return _noop()

    def _ff(coro, label=None, **_k):
        coro.close()

    monkeypatch.setattr(fr, "track_events_batch", _rec)
    monkeypatch.setattr(fr, "fire_and_forget", _ff)
    records, release = _capture([logging.getLogger(), fr.logger, logging.getLogger("app")])
    try:
        resp = TestClient(app).post("/api/v1/events", json={"events": [
            {"event_type": "store_cta_tap", "event_data": {"merchant_id": long_host}},
            {"event_type": "store_cta_tap", "event_data": {"merchant_id": edge_host}},
        ]})
    finally:
        release()
    assert resp.status_code == 200, resp.text[:300]
    data = [e["event_data"] for e in calls[0]]
    assert data == [{}, {"merchant_id": edge_host}], [sorted(d) for d in data]
    lines = [r for r in records if r.getMessage().startswith("[EVENTS]")]
    assert [r.getMessage() for r in lines] == [
        "[EVENTS] properties dropped type=store_cta_tap n=1"], [r.getMessage() for r in lines]
    assert all(r.levelno == logging.INFO for r in lines)
    for r in records:
        assert long_host not in _formatted(r) and edge_host not in _formatted(r)

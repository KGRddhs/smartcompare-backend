"""D22c PROFILE-SELECT RED rows (spec S81-G7, unit D22c part (1) section 5, as amended by
RULINGS_S81_G7: R-G7-2 BOTH selects of _update_behavior_profile repointed under the one
flag; R-G7-3 the flag name ENABLE_BEHAVIOR_PROFILE_REBUILD (the spec's
ENABLE_BEHAVIOR_PROFILE_EVENT_DATA is renamed), default OFF, read per call as the first
operand of the select choice).

ON: comparisons select ``category_used:full_response->>category_used,
products:full_response->products, created_at`` and user_events select
``event_type, metadata:event_data`` (the live columns), with NULL payloads normalised
before build_behavior_profile. OFF: the two base select strings and the except arm
byte-identical, pinned by the three-scenario golden tests/fixtures/
s81_d22c_flag_off_golden.json recorded at base 6869a3e6 by the RED agent through
``record_golden()`` below (pytest never writes it).

Every RED row fails at base on an AssertionError only (the reader is read with getattr
and asserted). The PIN rows run with the full configuration (the flag variable set to each
OFF spelling, a recorder on run_db, a recording fake client) and are green at base.

Hygiene: pure ASCII, LF; bounded runner only; netguard on (an in-memory fake client);
synthetic ids built at run time; no 64-hex literal in one piece.
"""
from __future__ import annotations

import app.main  # noqa: F401,I001  (FIRST: the dotenv guard)

import ast
import asyncio
import copy
import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import pytest

from app.services import behavior_service as bs_mod
from app.services import database_service
from app.services import structured_comparison_service as scs

ROOT = Path(__file__).resolve().parents[1]
FLAG = "ENABLE_BEHAVIOR_PROFILE_REBUILD"
GOLDEN = ROOT / "tests" / "fixtures" / "s81_d22c_flag_off_golden.json"
SCS_PATH = ROOT / "app" / "services" / "structured_comparison_service.py"
BS_PATH = ROOT / "app" / "services" / "behavior_service.py"
# sha256 of the golden file bytes and of behavior_service.py (LF-normalised), recorded at base.
GOLDEN_DIGEST = "8c793a16b1bbb1bffd789dd96a3c88d2" + "14deee2adc46d125f1efa48cd17eff0a"
BEHAVIOR_SERVICE_SHA256_BASE = ("34182edd21e0692979" + "4641538e65430d"
                                + "7a291d6ba4e4e3f5f440082b8232965e")
V2_COMPARISONS = "category_used:full_response->>category_used, products:full_response->products, created_at"
V2_EVENTS = "event_type, metadata:event_data"
BASE_COMPARISONS = "category_used, products, created_at"
BASE_EVENTS = "event_type, metadata"
WARN_PREFIX = "Failed to update behavior profile: "
OFF_SPELLINGS = [None, "", "false", " 0 ", "OFF"]
ON_SPELLINGS = ["true", " TRUE ", "On", "1", "yes"]
LIVE_COLUMNS = {
    "comparisons": {"created_at", "full_response", "id", "input_type", "product_names", "query", "schema_version",
                    "share_token", "user_id"},
    "comparison_feedback": {"id", "user_id", "comparison_id", "useful", "created_at"},
    "user_events": {"id", "user_id", "event_type", "event_data", "comparison_id", "created_at"},
    "users": {"id", "behavior_profile"},
}
FIXED_NOW = datetime(2026, 11, 5, 3, 0, 0)


def _uid():
    return "u-" + "synthetic-a"


# ---------------------------------------------------------------------------
# the fake store
# ---------------------------------------------------------------------------

class PgColumnError(Exception):
    """A PostgREST-shaped error (code 42703: undefined column)."""

    def __init__(self, table, column):
        super().__init__("column %s.%s does not exist" % (table, column))
        self.code = "42703"


class _Resp:
    def __init__(self, data):
        self.data = data


def _parse_select(columns):
    """[(alias, column, [(op, key), ...])] for 'a, b:c->>d, e:f->g'."""
    out = []
    for item in str(columns).split(","):
        item = item.strip()
        if not item:
            continue
        alias, expr = (item.split(":", 1) if ":" in item else (item, item))
        parts = re.split(r"(->>|->)", expr.strip())
        column, path = parts[0].strip(), []
        for i in range(1, len(parts) - 1, 2):
            path.append((parts[i], parts[i + 1].strip()))
        out.append((alias.strip(), column, path))
    return out


def _resolve(row, column, path):
    value = row.get(column)
    for op, key in path:
        value = value.get(key) if isinstance(value, dict) else None
        if op == "->>" and value is not None and not isinstance(value, str):
            value = json.dumps(value)
    return copy.deepcopy(value)


class _Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.op, self.columns, self.filters, self.payload = None, None, [], None
        client.calls.append(["table", table])

    def select(self, columns="*", **kwargs):
        self.op, self.columns = "select", columns
        self.client.calls.append(["select", columns])
        return self

    def update(self, payload, **kwargs):
        self.op, self.payload = "update", copy.deepcopy(payload)
        self.client.calls.append(["update", copy.deepcopy(payload)])
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        self.client.calls.append(["eq", column, value])
        return self

    def order(self, column, desc=False, **kwargs):
        self.client.calls.append(["order", column, bool(desc)])
        return self

    def limit(self, n, **kwargs):
        self.client.calls.append(["limit", n])
        return self

    def single(self):
        self.client.calls.append(["single"])
        return self

    def execute(self):
        self.client.calls.append(["execute", self.table])
        return self.client._execute(self)


class _Store:
    """mode 'live': a select naming a column outside LIVE_COLUMNS raises PgColumnError (the
    production schema); 'permissive': every select answers the raw rows' keys; 'raise_events':
    permissive except user_events, which raises; 'raise_all': every execute raises."""

    def __init__(self, mode, tables):
        self.mode = mode
        self.tables = copy.deepcopy(tables)
        self.calls = []
        self.updates = []

    def table(self, name):
        return _Query(self, name)

    def _execute(self, q):
        if self.mode == "raise_all":
            raise PgColumnError(q.table, "any")
        if self.mode == "raise_events" and q.table == "user_events":
            raise PgColumnError(q.table, "metadata")
        rows = [r for r in self.tables.get(q.table, []) if all(str(r.get(c)) == str(v) for c, v in q.filters)]
        if q.op == "update":
            self.updates.append((q.table, q.payload, list(q.filters)))
            return _Resp([])
        spec = _parse_select(q.columns)
        if self.mode == "live":
            for _alias, column, _path in spec:
                if column not in LIVE_COLUMNS.get(q.table, set()):
                    raise PgColumnError(q.table, column)
        out = []
        for r in rows:
            out.append({alias: _resolve(r, column, path) for alias, column, path in spec})
        return _Resp(out)


def _live_tables(uid, *, comparisons=None, feedback=None, events=None):
    return {
        "comparisons": comparisons if comparisons is not None else [],
        "comparison_feedback": feedback if feedback is not None else [],
        "user_events": events if events is not None else [],
        "users": [{"id": uid, "behavior_profile": {}}],
    }


def _permissive_tables(uid):
    """Rows carrying BOTH the base names and the live names (a permissive store)."""
    return {
        "comparisons": [
            {"id": "c-1", "user_id": uid, "created_at": "2026-11-01T10:00:00+00:00", "category_used": "fragrances",
             "products": [{"name": "Nova A", "price": {"amount": 40.0, "currency": "BHD"}},
                          {"name": "Nova B", "price": {"amount": 60.0, "currency": "BHD"}}],
             "full_response": {"category_used": "fragrances"}},
            {"id": "c-2", "user_id": uid, "created_at": "2026-10-30T10:00:00+00:00", "category_used": "electronics",
             "products": [{"name": "Dune A", "price": 120.0}], "full_response": {"category_used": "electronics"}},
        ],
        "comparison_feedback": [{"id": "f-1", "user_id": uid, "useful": True}, {"id": "f-2", "user_id": uid,
                                                                                 "useful": False}],
        "user_events": [
            {"id": "e-1", "user_id": uid, "event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 4000},
             "event_data": {"to": "specs", "dwell_ms": 4000}, "created_at": "2026-11-01T10:00:00+00:00"},
            {"id": "e-2", "user_id": uid, "event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 1000},
             "event_data": {"to": "reviews", "dwell_ms": 1000}, "created_at": "2026-11-01T10:01:00+00:00"},
        ],
        "users": [{"id": uid, "behavior_profile": {}}],
    }


def _scenarios(uid):
    return {
        "A_live_like": ("live", _live_tables(uid, comparisons=_permissive_tables(uid)["comparisons"],
                                             feedback=_permissive_tables(uid)["comparison_feedback"],
                                             events=_permissive_tables(uid)["user_events"])),
        "B_permissive": ("permissive", _permissive_tables(uid)),
        "C_events_raise": ("raise_events", _permissive_tables(uid)),
    }


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW if tz is None else FIXED_NOW.replace(tzinfo=tz)


def _arm(mp, store, run_db_calls):
    """Point the function-local seams at the store, record run_db, fix behavior_service's clock."""
    mp.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    mp.setattr(database_service, "get_supabase_client", lambda *a, **k: store)
    mp.setattr(bs_mod, "datetime", _FixedDatetime)
    if hasattr(bs_mod.get_behavior_service, "_instance"):
        mp.delattr(bs_mod.get_behavior_service, "_instance")

    async def _run_db(call):
        run_db_calls.append("run_db")
        return call()
    mp.setattr(scs, "run_db", _run_db)


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages = []

    def emit(self, record):
        if record.levelno >= logging.WARNING:
            self.messages.append(record.getMessage())


def _drive(mp, mode, tables):
    """One _update_behavior_profile call against a fresh store; returns the record."""
    store = _Store(mode, tables)
    run_db_calls = []
    _arm(mp, store, run_db_calls)
    cap = _Capture()
    lg = logging.getLogger(scs.__name__)
    lg.addHandler(cap)
    try:
        asyncio.run(scs.StructuredComparisonService._update_behavior_profile(None, _uid()))
    finally:
        lg.removeHandler(cap)
    return {"calls": store.calls, "run_db": len(run_db_calls), "warnings": cap.messages,
            "updates": [[t, p, [list(f) for f in fl]] for t, p, fl in store.updates]}, store


def record_golden(mp):
    """The flag-OFF record of the three scenarios (the flag variable unset)."""
    mp.delenv(FLAG, raising=False)
    out = {}
    for name, (mode, tables) in sorted(_scenarios(_uid()).items()):
        rec, _store = _drive(mp, mode, tables)
        out[name] = rec
    return out


def _golden_bytes(record):
    return (json.dumps(record, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode("ascii")


def _set_flag(mp, value):
    if value is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, value)


def _reader():
    fn = getattr(scs, "behavior_profile_rebuild_enabled", None)
    assert callable(fn), "structured_comparison_service.behavior_profile_rebuild_enabled is missing (D22c)"
    return fn


def _selects(store, table):
    out, current = [], None
    for call in store.calls:
        if call[0] == "table":
            current = call[1]
        elif call[0] == "select" and current == table:
            out.append(call[1])
    return out


def _executes(store):
    return [c for c in store.calls if c[0] == "execute"]


def _live_world(uid):
    comparisons = [
        {"id": "c-1", "user_id": uid, "created_at": "2026-11-01T10:00:00+00:00",
         "full_response": {"category_used": "fragrances",
                           "products": [{"name": "Nova A", "price": {"amount": 40.0, "currency": "BHD"}}]}},
        {"id": "c-2", "user_id": uid, "created_at": "2026-10-31T10:00:00+00:00",
         "full_response": {"category_used": "fragrances",
                           "products": [{"name": "Nova B", "price": {"amount": 60.0, "currency": "BHD"}}]}},
    ]
    feedback = [{"id": "f-1", "user_id": uid, "useful": True}]
    events = [
        {"id": "e-1", "user_id": uid, "event_type": "tab_switch", "event_data": {"to": "specs", "dwell_ms": 5000},
         "created_at": "2026-11-01T10:00:00+00:00"},
        {"id": "e-2", "user_id": uid, "event_type": "share", "event_data": None,
         "created_at": "2026-11-01T10:02:00+00:00"},
    ]
    return _live_tables(uid, comparisons=comparisons, feedback=feedback, events=events)


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_reader_spellings(monkeypatch):
    """R1: the per-call reader: the house truthy set ON (padded / mixed case), all else OFF."""
    fn = _reader()
    for value in ON_SPELLINGS:
        monkeypatch.setenv(FLAG, value)
        assert fn() is True, value
    for value in [None, "", "false", " 0 ", "OFF", "garbage"]:
        _set_flag(monkeypatch, value)
        assert fn() is False, value


def test_r2_on_selects_live_columns(monkeypatch):
    """R2: flag ON on the live-like store: the V2 comparisons and events selects; four executes."""
    monkeypatch.setenv(FLAG, "true")
    _rec, store = _drive(monkeypatch, "live", _live_world(_uid()))
    assert _selects(store, "comparisons") == [V2_COMPARISONS], _selects(store, "comparisons")
    assert _selects(store, "user_events") == [V2_EVENTS], _selects(store, "user_events")
    assert _selects(store, "comparison_feedback") == ["useful"], _selects(store, "comparison_feedback")
    assert len(_executes(store)) == 4, _executes(store)


def test_r3_on_writes_a_profile(monkeypatch):
    """R3: flag ON, live-like store: ONE users.update with a non-empty profile; no WARNING."""
    monkeypatch.setenv(FLAG, "true")
    rec, store = _drive(monkeypatch, "live", _live_world(_uid()))
    assert rec["warnings"] == [], rec["warnings"]
    assert len(store.updates) == 1, store.updates
    table, payload, filters = store.updates[0]
    assert table == "users" and filters == [("id", _uid())], (table, filters)
    profile = payload["behavior_profile"]
    assert profile["category_affinity"] == {"fragrances": 1.0}, profile
    assert profile["price_range_preference"]["avg_price_viewed"] == 50.0, profile
    assert profile["winner_agreement"]["agreed"] == 1, profile
    assert profile["dimension_sensitivity"], profile
    assert profile["comparison_count"] == 2, profile


def test_r4_on_null_payloads_do_not_raise(monkeypatch):
    """R4: flag ON, a tab_switch whose event_data is NULL and a comparison whose full_response
    is NULL: one update, no WARNING (the ON normalisation)."""
    uid = _uid()
    monkeypatch.setenv(FLAG, "true")
    tables = _live_tables(uid, comparisons=[{"id": "c-1", "user_id": uid, "created_at": "2026-11-01T10:00:00+00:00",
                                             "full_response": None}],
                          feedback=[], events=[{"id": "e-1", "user_id": uid, "event_type": "tab_switch",
                                                "event_data": None, "created_at": "2026-11-01T10:00:00+00:00"}])
    rec, store = _drive(monkeypatch, "live", tables)
    assert rec["warnings"] == [], rec["warnings"]
    assert len(store.updates) == 1, store.updates


def test_r5_flag_read_per_call(monkeypatch):
    """R5: ON then OFF between two calls: the first issues the V2 strings, the second the base."""
    monkeypatch.setenv(FLAG, "true")
    _rec, first = _drive(monkeypatch, "permissive", _permissive_tables(_uid()))
    monkeypatch.setenv(FLAG, "false")
    _rec, second = _drive(monkeypatch, "permissive", _permissive_tables(_uid()))
    assert _selects(first, "comparisons") == [V2_COMPARISONS], _selects(first, "comparisons")
    assert _selects(first, "user_events") == [V2_EVENTS], _selects(first, "user_events")
    assert _selects(second, "comparisons") == [BASE_COMPARISONS], _selects(second, "comparisons")
    assert _selects(second, "user_events") == [BASE_EVENTS], _selects(second, "user_events")


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=["unset", "empty", "false", "pad0", "OFF"])
def test_p1_flag_off_golden(monkeypatch, value):
    """P1 (PIN): every OFF spelling: the three scenarios equal the golden recorded at base."""
    raw = GOLDEN.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_DIGEST, "the golden file changed"
    golden = json.loads(raw.decode("ascii"))
    _set_flag(monkeypatch, value)
    got = {}
    for name, (mode, tables) in sorted(_scenarios(_uid()).items()):
        rec, _store = _drive(monkeypatch, mode, tables)
        got[name] = json.loads(json.dumps(rec, sort_keys=True))
    assert got == golden, json.dumps(got, sort_keys=True)[:1500]
    assert golden["A_live_like"]["run_db"] == 1 and golden["A_live_like"]["updates"] == []
    assert golden["B_permissive"]["run_db"] == 4 and len(golden["B_permissive"]["updates"]) == 1
    assert golden["C_events_raise"]["run_db"] == 3 and golden["C_events_raise"]["updates"] == []


def test_p2_on_raising_store_keeps_except_arm(monkeypatch):
    """P2 (PIN): flag ON, every execute raises: no raise escapes, one WARNING, no update."""
    monkeypatch.setenv(FLAG, "true")
    rec, store = _drive(monkeypatch, "raise_all", _permissive_tables(_uid()))
    assert len(rec["warnings"]) == 1 and rec["warnings"][0].startswith(WARN_PREFIX), rec["warnings"]
    assert store.updates == [], store.updates


def _is_call_site(node):
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_fire_and_forget"):
        return False
    if len(node.args) != 2 or node.keywords:
        return False
    inner, label = node.args
    return (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "_update_behavior_profile" and isinstance(inner.func.value, ast.Name)
            and inner.func.value.id == "self" and len(inner.args) == 1 and isinstance(inner.args[0], ast.Name)
            and inner.args[0].id == "user_id" and isinstance(label, ast.Constant)
            and label.value == "behavior_profile_update")


def test_p3_label_and_call_sites_unchanged():
    """P3 (PIN): exactly two _fire_and_forget(self._update_behavior_profile(user_id), "behavior_profile_update")."""
    tree = ast.parse(SCS_PATH.read_text(encoding="utf-8"))
    sites = [n for n in ast.walk(tree) if _is_call_site(n)]
    assert len(sites) == 2, len(sites)


def test_p4_behavior_service_untouched():
    """P4 (PIN): behavior_service.py (LF-normalised) equals its base bytes."""
    raw = BS_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == BEHAVIOR_SERVICE_SHA256_BASE

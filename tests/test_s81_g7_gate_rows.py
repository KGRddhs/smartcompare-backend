"""S81-G7 GREEN-owned gate rows (RULINGS_REBASE_S81_G7 RB-G7-1 / RB-G7-2; the adversary's
MIN-1 and MIN-4, survivors ADV-O1 / ADV-O2 / ADV-O4).

G7-GR1 test_g7_gr1_read_by_every_chunk (RB-G7-1, kills ADV-O1): ``cron_learning._read_by``
over 250 distinct values (three 100-value IN chunks) returns every row of every chunk,
each request id-ordered and IN-filtered on at most 100 values; with a cap below the total
the read stops at the cap, reports ``capped`` and never asks for a row past it. The edit
"return after the first chunk" is killed (only the first chunk's rows come back).

G7-GR2 test_g7_gr2_render_escapes_del (RB-G7-2, kills ADV-O2): ``_render`` escapes DEL
(0x7F) exactly like the C0 range (``\\x7f``); a printable name stays unchanged.

G7-GR3 test_g7_gr3_dropped_counts_wrong_unclean_only (RB-G7-2, kills ADV-O4): the
dropped_deidentify counter of ``_gather`` (``dropped_fields``) counts only kb_feedback
rows whose verdict is ``wrong`` AND whose field name is unclean: a clean-named wrong row
and an unclean-named non-wrong row leave it unchanged.

Every row drives scripts/cron_learning.py directly through a small in-memory fake of the
supabase query chain (select / in_ / gte / lt / order / range / execute); netguard on, no
socket, synthetic ids and names built at run time (the at sign is chr(64)); pure ASCII, LF.
"""
from __future__ import annotations

import importlib

import pytest

MOD = "scripts.cron_learning"


def _mod():
    return importlib.import_module(MOD)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    from app.services import kb_service  # noqa: F401 - the dotenv guard: the leaf loads first
    monkeypatch.delenv("ENABLE_LEARNING_JOB", raising=False)
    yield


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, fake, table, columns):
        self.fake = fake
        self.op = {"table": table, "columns": columns, "in": None, "orders": [], "rng": None}

    def in_(self, column, values):
        self.op["in"] = (column, list(values))
        return self

    def gte(self, column, value):
        return self

    def lt(self, column, value):
        return self

    def order(self, column, *args, **kwargs):
        self.op["orders"].append(column)
        return self

    def range(self, start, end):
        self.op["rng"] = (start, end)
        return self

    def execute(self):
        self.fake.ops.append(self.op)
        rows = list(self.fake.tables.get(self.op["table"], []))
        if self.op["in"] is not None:
            column, values = self.op["in"]
            wanted = set(values)
            rows = [r for r in rows if r.get(column) in wanted]
        if "id" in self.op["orders"]:
            rows = sorted(rows, key=lambda r: str(r.get("id")))
        if self.op["rng"] is not None:
            start, end = self.op["rng"]
            rows = rows[start:end + 1]
        return _Resp(rows)


class _Table:
    def __init__(self, fake, table):
        self.fake = fake
        self.table = table

    def select(self, columns):
        return _Query(self.fake, self.table, columns)


class _Fake:
    def __init__(self, tables):
        self.tables = tables
        self.ops = []

    def table(self, name):
        return _Table(self, name)


def _spec_world(n_values=250, per_value=3):
    values = ["p-gr1-%03d" % i for i in range(n_values)]
    rows = []
    for i, v in enumerate(values):
        for j in range(per_value):
            rows.append({"id": "row-gr1-%03d-%d" % (i, j), "product_id": v, "field": "season"})
    return values, rows


def test_g7_gr1_read_by_every_chunk():
    mod = _mod()
    assert mod.IN_CHUNK == 100
    values, rows = _spec_world()
    fake = _Fake({"kb_specs": rows})
    got, status = mod._read_by(fake, "kb_specs", "product_id,field", "product_id", values, 5000)
    assert status == "ok"
    assert len(got) == 750, len(got)
    ids = [r["id"] for r in got]
    assert len(set(ids)) == 750
    assert {r["product_id"] for r in got} == set(values)
    in_sets = [tuple(op["in"][1]) for op in fake.ops]
    assert len(in_sets) == 3, len(in_sets)
    assert [len(s) for s in in_sets] == [100, 100, 50]
    assert sorted(v for s in in_sets for v in s) == sorted(values)
    for op in fake.ops:
        assert op["in"][0] == "product_id"
        assert op["orders"] == ["id"]

    # the cap honoured: 700 < 750 rows; the third chunk asks only for the 100 rows left
    fake2 = _Fake({"kb_specs": rows})
    got2, status2 = mod._read_by(fake2, "kb_specs", "product_id,field", "product_id", values, 700)
    assert status2 == "capped"
    assert len(got2) == 700
    assert len({r["id"] for r in got2}) == 700
    assert len(fake2.ops) == 3
    assert fake2.ops[-1]["rng"] == (0, 99)
    assert all(op["rng"][1] - op["rng"][0] + 1 <= 500 for op in fake2.ops)


def test_g7_gr2_render_escapes_del():
    mod = _mod()
    name = "Nova" + chr(0x7F) + "Oud"
    out = mod._render(name)
    assert chr(0x7F) not in out
    assert out == "Nova" + "\\x7f" + "Oud"
    assert mod._render("Nova" + chr(0x1F) + "Oud") == "Nova" + "\\x1f" + "Oud"
    assert mod._render("Nova Oud EDP") == "Nova Oud EDP"


def _kbfb(i, field, verdict):
    return {"id": "row-gr3-%02d" % i, "compare_request_id": "req-gr3-%02d" % i, "product_id": "p-gr3-a",
            "field": field, "verdict": verdict, "device_key": "dev-gr3-%02d" % i,
            "created_at": "2026-11-04T10:00:00+00:00"}


def _dropped(rows):
    mod = _mod()
    fake = _Fake({mod.KB_FEEDBACK_TABLE: rows})
    gathered = mod._gather(fake, "fragrances", "2026-11-04T00:00:00+00:00", "2026-11-05T00:00:00+00:00", 1000)
    return gathered["dropped_fields"]


def test_g7_gr3_dropped_counts_wrong_unclean_only():
    unclean = "season" + chr(64) + "x"
    assert _dropped([_kbfb(1, unclean, "wrong")]) == 1
    # a clean-named wrong row leaves the counter unchanged
    assert _dropped([_kbfb(1, unclean, "wrong"), _kbfb(2, "season", "wrong")]) == 1
    # an unclean-named non-wrong row leaves the counter unchanged
    assert _dropped([_kbfb(1, unclean, "wrong"), _kbfb(3, unclean, "correct")]) == 1
    assert _dropped([_kbfb(3, unclean, "correct"), _kbfb(4, "season", "wrong")]) == 0

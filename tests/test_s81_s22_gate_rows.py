"""S81-22 COMPARE-RUNS + capped judge -- the GREEN-owned gate rows (GATE_S81_22 GC-10).

G22-GR1: at the three text exits (POST, GET, the stream's delivered terminal), the camera exit
and the URL exit, ``_compare_runs.record_compare_run(...)`` is a plain expression statement
(never awaited, never wrapped), the sibling right after the exit's ``capture_result_status``
statement; exactly 3 / 1 / 1 such calls per route file; and the stream generator's finally
holds no Await / AsyncFor / AsyncWith (the G20-GR2 form; base had none).
G22-GR2 (GC-5): the 048 guard raises on an existing compare_runs / compare_judgements ONLY
when its column set (information_schema.columns, names only) differs from the one 048
creates: both tables are read from information_schema.columns, the guard's column arrays
equal the CREATE TABLE column sets exactly, the raise sits behind
``v_cols IS NOT NULL AND NOT (v_cols @> <set> AND v_cols <@ <set>)``, and there is no bare
"the table exists" raise.
G22-GR3 (E2): the two P02_ALLOWED entries for scripts/cron_compare_judge.py are present, every
kb_* relation literal of the judge sits on exactly those two lines, and the judge reaches the
KB layer only through kb_seed_common (no kb_service import anywhere in the file).

Pure static reads of the repository files: hermetic, no network, no .env. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import inspect
import re
import textwrap
from pathlib import Path

import pytest

import app.main as app_main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
from app.api import text_routes
from tests import test_s81_kb_schema as kb_schema

ROOT = Path(__file__).resolve().parents[1]
M048 = ROOT / "migrations" / "048_compare_runs.sql"
JUDGE = ROOT / "scripts" / "cron_compare_judge.py"
SITES = {"app/api/text_routes.py": ("text", "text", "text_stream"),
         "app/api/image_routes.py": ("camera",),
         "app/api/url_routes.py": ("url",)}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _is_record_call(node) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "record_compare_run" and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "_compare_runs")


def _is_capture_stmt(node) -> bool:
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name) and node.value.func.id == "capture_result_status")


# =============================================================== G22-GR1

@pytest.mark.parametrize("rel", sorted(SITES))
def test_g22_gr1_plain_call_after_capture_at_every_site(rel):
    tree = ast.parse(_read(ROOT / rel))
    calls = [n for n in ast.walk(tree) if _is_record_call(n)]
    assert [c.args[1].value for c in calls] == list(SITES[rel]), [ast.dump(c)[:120] for c in calls]
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    for call in calls:
        stmt = parents[id(call)]
        # a plain expression statement: not awaited, not assigned, not an argument
        assert isinstance(stmt, ast.Expr) and stmt.value is call, ast.dump(stmt)[:160]
        assert not isinstance(parents.get(id(stmt)), ast.Await)
        block = parents[id(stmt)]
        body = next(b for b in (getattr(block, f, None) for f in ("body", "orelse", "finalbody"))
                    if isinstance(b, list) and stmt in b)
        pos = body.index(stmt)
        assert pos > 0 and _is_capture_stmt(body[pos - 1]), (rel, call.lineno)
        assert body[pos - 1].value.args[1].value == call.args[1].value or call.args[1].value == "text_stream"
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Await) and _is_record_call(n.value)]


def _event_generator_finally():
    src = textwrap.dedent(inspect.getsource(text_routes.text_compare_stream))
    gens = [n for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "event_generator"]
    assert len(gens) == 1, len(gens)
    tries = [n for n in ast.walk(gens[0]) if isinstance(n, ast.Try) and n.finalbody]
    assert len(tries) == 1, len(tries)
    return tries[0].finalbody


def test_g22_gr1_stream_call_inside_finally_and_no_await_there():
    body = _event_generator_finally()
    nodes = [n for stmt in body for n in ast.walk(stmt)]
    assert [n for n in nodes if isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith))] == []
    records = [n for n in nodes if _is_record_call(n)]
    assert len(records) == 1 and records[0].args[1].value == "text_stream", len(records)
    assert isinstance(records[0].args[0], ast.Name) and records[0].args[0].id == "complete_response"


# =============================================================== G22-GR2 (GC-5)

def _guard() -> str:
    m = re.search(r"DO \$guard\$(.*?)\$guard\$;", _read(M048), re.S)
    assert m, "no guard block"
    return m.group(1)


def _create_columns(table: str) -> set:
    m = re.search(r"CREATE TABLE IF NOT EXISTS public\.%s \((.*?)\n\);" % table, _read(M048), re.S)
    assert m, table
    cols = set()
    for line in m.group(1).split("\n"):
        word = line.strip().split(" ", 1)[0]
        if re.match(r"^[a-z_]+$", word) and word not in ("constraint",) and line.startswith("    ") \
                and not line.startswith("        "):
            cols.add(word)
    return cols


@pytest.mark.parametrize("table", ["compare_runs", "compare_judgements"])
def test_g22_gr2_guard_raises_only_on_a_differing_column_set(table):
    g = _guard()
    blk = re.search(
        r"SELECT array_agg\(col\.column_name::text\)\s+INTO v_cols\s+FROM information_schema\.columns AS col\s+"
        r"WHERE col\.table_schema = 'public'\s+AND col\.table_name = '%s';\s+"
        r"IF v_cols IS NOT NULL AND NOT \(\s+v_cols @> ARRAY\[(.*?)\]::text\[\]\s+"
        r"AND v_cols <@ ARRAY\[(.*?)\]::text\[\]\s+\) THEN\s+"
        r"RAISE EXCEPTION '048 guard: %s exists with a different column set';\s+END IF;" % (table, table),
        g, re.S)
    assert blk, table
    want = _create_columns(table)
    assert len(want) == {"compare_runs": 25, "compare_judgements": 10}[table], sorted(want)
    for arr in (blk.group(1), blk.group(2)):
        got = re.findall(r"'([a-z_]+)'", arr)
        assert len(got) == len(set(got)) and set(got) == want, (table, sorted(set(got) ^ want))


def test_g22_gr2_no_bare_exists_raise():
    g = _guard()
    assert "to_regclass('public.compare_runs')" not in g
    assert "to_regclass('public.compare_judgements')" not in g
    assert g.count("information_schema.columns") == 3  # kb_feedback.compare_request_id + the two sets
    raises = re.findall(r"RAISE EXCEPTION '([^']*)'", g)
    assert [r for r in raises if "compare_runs" in r or "compare_judgements" in r] == [
        "048 guard: compare_runs exists with a different column set",
        "048 guard: compare_judgements exists with a different column set"]


# =============================================================== G22-GR3 (E2)

E2_ENTRIES = {("scripts/cron_compare_judge.py", 'KB_PRUNE_FEEDBACK_RPC = "kb_prune_feedback"'),
              ("scripts/cron_compare_judge.py", 'KB_FEEDBACK_TABLE = "kb_feedback"')}


def test_g22_gr3_e2_entries_present():
    assert E2_ENTRIES <= set(kb_schema.P02_ALLOWED)
    assert {e for e in kb_schema.P02_ALLOWED if e[0] == "scripts/cron_compare_judge.py"} == E2_ENTRIES


def test_g22_gr3_judge_kb_literals_only_on_the_e2_lines():
    text = JUDGE.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    hits = sorted({lines[n.lineno - 1].strip() for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and n.value in kb_schema.KB_RELATION_NAMES})
    assert hits == sorted(e[1] for e in E2_ENTRIES), hits
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported |= {"%s.%s" % (n.module, a.name) for a in n.names}
    assert not [m for m in imported if "kb_service" in m], sorted(imported)
    assert "scripts.kb_seed_common" in imported
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert [n.module for n in top if isinstance(n, ast.ImportFrom) and n.module.startswith(("app", "scripts"))] \
        == ["scripts"], "only kb_seed_common at module top"

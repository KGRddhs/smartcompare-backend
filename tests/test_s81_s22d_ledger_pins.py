"""S81-22d LEDGER-PINS-FLAG-SAFE RED rows (spec S81-G9 unit S81-22d section 5;
RULINGS_S81_G9 R-G9-5: EK1 = the two delenv lines on the frozen S81-03 file are
GREEN's edit; these rows measure the S03 file as it is).

  R1-R3  fail at base on an AssertionError only
  P1-P2  green at base

The S03 rows are reached through the module object
(tests.test_s81_s03_llm_ledger_v2; its rows are not collected twice); the S03
autouse fixture is replayed here (UNIT_ENV deleted, the limiter disabled).
Run this file twice: flag unset and ENABLE_COMPARE_RUN_LEDGER=true exported in
the runner call only. Pure ASCII, LF.
"""
import ast
import hashlib
from pathlib import Path

import pytest

from tests import test_s81_s03_llm_ledger_v2 as s03

ROOT = Path(__file__).resolve().parents[1]
LEDGER_FLAG = "ENABLE_COMPARE_RUN_LEDGER"
S03_FILE = ROOT / "tests" / "test_s81_s03_llm_ledger_v2.py"
ROWS = ("test_i2_camera_flag_off_no_metadata_llm", "test_i6_off_camera_real_compare_total_cost_is_base")
NODES = [(ROWS[0], "false"), (ROWS[0], None), (ROWS[1], None), (ROWS[1], "false")]
S22_LF_SHA = {
    "tests/test_s81_s22_compare_runs.py": "db13c005e04f3e9986190a538f6baa77ddaa587178ab1677f8399360922000eb",
    "tests/test_s81_s22_judge.py": "86614fb4998b981b08adca3b20c01224ad8b927da9dccaa5c1d39099abacc99e",
    "tests/test_s81_s22_gate_rows.py": "fc22cc7e1313694520409605f3e31ba8f6760e69100c53540ce32011ae6e61b2",
}


@pytest.fixture(autouse=True)
def _s03_env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in s03.UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(s03.limiter, "enabled", False)
    yield


def _source():
    return S03_FILE.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")


def _functions(tree):
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ROWS:
            out[node.name] = node
    assert set(out) == set(ROWS), sorted(out)
    return out


def _names_flag(stmt):
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return False
    call = stmt.value
    func = call.func
    if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "monkeypatch"):
        return False
    if not call.args or not (isinstance(call.args[0], ast.Constant) and call.args[0].value == LEDGER_FLAG):
        return False
    if func.attr == "delenv":
        return True
    return (func.attr == "setenv" and len(call.args) > 1 and isinstance(call.args[1], ast.Constant)
            and call.args[1].value == "false")


def _row(name, flag, monkeypatch):
    fn = getattr(s03, name)
    try:
        fn(monkeypatch, flag)
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001 - only an AssertionError may leave a row
        raise AssertionError("%s[%r] raised %s" % (name, flag, type(exc).__name__))


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_rows_name_the_flag():
    funcs = _functions(ast.parse(_source()))
    for name in ROWS:
        body = list(funcs[name].body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]
        assert body and _names_flag(body[0]), "%s: the first statement must delete %s" % (name, LEDGER_FLAG)


@pytest.mark.parametrize("name,flag", NODES, ids=["i2-false", "i2-None", "i6off-None", "i6off-false"])
def test_r2_rows_green_with_flag_exported(monkeypatch, name, flag):
    monkeypatch.setenv(LEDGER_FLAG, "true")
    _row(name, flag, monkeypatch)


def test_r3_flag_named_only_in_the_two_rows():
    src = _source()
    funcs = _functions(ast.parse(src))
    spans = [(f.lineno, f.end_lineno) for f in funcs.values()]
    hits = [i for i, line in enumerate(src.split("\n"), start=1) if LEDGER_FLAG in line]
    assert len(hits) == 2, hits
    for line in hits:
        assert any(a <= line <= b for a, b in spans), line
    assert all(any(a <= line <= b for line in hits) for a, b in spans), (hits, spans)


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,flag", NODES, ids=["i2-false", "i2-None", "i6off-None", "i6off-false"])
def test_p1_rows_green_with_flag_unset(monkeypatch, name, flag):
    monkeypatch.delenv(LEDGER_FLAG, raising=False)
    _row(name, flag, monkeypatch)


def test_p2_s22_frozen_files_unchanged():
    for rel, want in sorted(S22_LF_SHA.items()):
        got = hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert got == want, rel

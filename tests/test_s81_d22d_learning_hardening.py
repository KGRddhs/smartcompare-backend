"""D22d LEARNING-HARDENING RED rows (spec S81-G7, unit D22d section 5, as amended by
RULINGS_S81_G7: R-G7-7 ``_read_by`` paged id-ordered per 100-id chunk up to the cap; an
unclean kb_feedback field-name row counts in dropped_deidentify (E2, GREEN's); control
characters (C0 / C1 / U+2028 / U+2029) escaped at the three render sites; R-G7-8 unclean
kb_gaps field names do NOT count; R-G7-9 the backslash mutant M7 equivalent, no row).

No new flag: rides ENABLE_LEARNING_JOB. Every row drives scripts/cron_learning.py through
the frozen D22 RED file's fake client and world builders (``tests.test_s81_d22_nightly_learning``)
and the frozen G5 gate-rows world ``_kb_field_world`` (``tests.test_s81_g5_gate_rows``).

Every RED row fails at base on an AssertionError only (``_render`` is read with getattr and
asserted). The PIN rows are green at base and run with the full configuration.

Hygiene: pure ASCII, LF (control characters are built with chr() at run time); bounded
runner only; netguard on; synthetic ids and names only; no 64-hex literal in one piece.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import logging

import pytest

MOD = "scripts.cron_learning"
SEASON_URL = "https://" + "store-a.example.com/p/season-final"
# sha256 of the --report-md bytes of the default D22 world, recorded at base 6869a3e6.
MD_SHA256_BASE = "a0fd45285e22498e21353c45fbfe1efa" + "f1c603d7143dabcf3b1a476c63f20f24"
# the exemplar / eval_case log lines of the default D22 world, recorded at base 6869a3e6.
_EX_FR = '[LEARNING] exemplar category=fragrances version=2026-11-04.bqft5qxhq5rtcv7m names='
_EX_EL = '[LEARNING] exemplar category=electronics version=2026-11-04.oyujt6dq4fi6q7yg names='
BASE_NAME_LINES = [
    _EX_EL + 'Ion Phone Pro || Jet Phone Max',
    _EX_FR + 'Acme Rose EDP || Birch Oud EDT',
    _EX_FR + 'Cedar Musk EDP || Dune Amber EDP',
    _EX_FR + 'Elm Vetiver EDT || Fern Citrus EDT',
    _EX_FR + 'Gale Iris EDP || Haze Vanilla EDP',
    '[LEARNING] eval_case category=electronics winner=0 prices=0 names=Ion Phone Pro || Jet Phone Max',
    '[LEARNING] eval_case category=fragrances winner=0 prices=1 names=Acme Rose EDP || Birch Oud EDT',
    '[LEARNING] eval_case category=fragrances winner=1 prices=0 names=Cedar Musk EDP || Dune Amber EDP',
    '[LEARNING] eval_case category=fragrances winner=0 prices=0 names=Elm Vetiver EDT || Fern Citrus EDT',
    '[LEARNING] eval_case category=fragrances winner=0 prices=0 names=Gale Iris EDP || Haze Vanilla EDP',
    '[LEARNING] eval_case category=fragrances winner=0 prices=0 names=Opal Bloom EDP || Pine Smoke EDT',
]


def _red():
    return importlib.import_module("tests.test_s81_d22_nightly_learning")


def _g5():
    return importlib.import_module("tests.test_s81_g5_gate_rows")


def _mod():
    return importlib.import_module(MOD)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    red = _red()
    red._leaf()  # the dotenv guard: the leaf (and its imports) load before any env is set
    for name in (red.FLAG,) + red.KNOBS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(red._common(), "_now", lambda: red.NOW)
    yield


def _control_set():
    chars = {chr(c) for c in range(0x00, 0x20)} | {chr(c) for c in range(0x7F, 0xA0)}
    return chars | {chr(0x2028), chr(0x2029)}


def _season_world(extra_specs=900):
    red = _red()
    pid = red.P_A
    kbfb = [{"id": "row-kf-s-%d" % i, "compare_request_id": red._rid(60 + i), "product_id": pid, "field": "season",
             "verdict": "wrong", "device_key": red._dev(ch), "created_at": red.T_IN}
            for i, ch in ((1, "a"), (2, "b"), (3, "c"))]
    others = ("concentration", "scent_family", "longevity", "sillage")
    specs = [{"id": "row-ks-a-%04d" % i, "product_id": pid, "field": others[i % len(others)],
              "source_url": "https://" + "store-a.example.com/p/other-%d" % (i % 7), "cited": True}
             for i in range(extra_specs)]
    specs.append({"id": "row-ks-z-final", "product_id": pid, "field": "season", "source_url": SEASON_URL,
                  "cited": True})
    return {red.T_KBFB: kbfb, red.T_SPECS: specs}


def _spec_ranges(run):
    red = _red()
    return [(op["rng"], op["orders"]) for op in run.fake.selects(red.T_SPECS)]


def _metric(run, name):
    found = [m for m in run.report["metrics"] if m[0] == name]
    assert len(found) == 1, (name, run.report["metrics"])
    return found[0][1], found[0][2]


def _name_lines(run):
    return [m for m in run.messages() if m.startswith("[LEARNING] exemplar ") or m.startswith("[LEARNING] eval_case ")]


def _control_world():
    red = _red()
    world = red._world()
    world[red.T_COMPARISONS][0]["product_names"] = ["Nova" + chr(10) + "[LEARNING] forged",
                                                    "Dune" + chr(27) + "[2J" + chr(0x2028) + "x"]
    return world


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_r1_specs_grounding_survives_paging(monkeypatch, tmp_path, caplog):
    """R1: 900 cited spec rows of P on other fields sort before its one cited season row: the
    spec_wrong / kb / season proposal is still grounded on that row."""
    red = _red()
    run = red._run(monkeypatch, tmp_path, caplog, "true", world=_season_world())
    assert run.rc == 0
    props = [p for p in run.report["proposals"]
             if (p["bucket"], p["source"], p["field"]) == ("spec_wrong", "kb", "season")]
    assert len(props) == 1, run.report["proposals"]
    assert props[0]["grounding"] == [{"product_id": red.P_A, "field": "season", "source_url": SEASON_URL}], props
    assert props[0]["proposed_action"] == _mod()._action("spec_wrong", "kb", props[0]["grounding"]), props
    assert props[0]["proposed_action"] == "recheck_source", props


def test_r2_specs_pages_ranges(monkeypatch, tmp_path, caplog):
    """R2: one 100-value chunk, two id-ordered pages of 500 (the second short); 901 rows ok."""
    red = _red()
    run = red._run(monkeypatch, tmp_path, caplog, "true", world=_season_world())
    assert _spec_ranges(run) == [((0, 499), [("id", False)]), ((500, 999), [("id", False)])], _spec_ranges(run)
    assert run.report["tables"][red.T_SPECS] == {"rows": 901, "status": "ok", "error": None}, \
        run.report["tables"][red.T_SPECS]


def test_r3_specs_cap_across_pages(monkeypatch, tmp_path, caplog):
    """R3: LEARNING_MAX_ROWS=100 (the floor): one page of 100, status capped, the capped metric (100, 100)."""
    red = _red()
    run = red._run(monkeypatch, tmp_path, caplog, "true", world=_season_world(),
                   env={"LEARNING_MAX_ROWS": "100"})
    assert _spec_ranges(run) == [((0, 99), [("id", False)])], _spec_ranges(run)
    assert run.report["tables"][red.T_SPECS]["status"] == "capped", run.report["tables"][red.T_SPECS]
    value, n = _metric(run, "learning.capped." + red.T_SPECS)
    assert (float(value), n) == (100.0, 100), (value, n)


def test_r4_unclean_field_counted(monkeypatch, tmp_path, caplog):
    """R4: the G5-GR6 world (six unclean kb_feedback field-name rows): dropped_deidentify 6."""
    red = _red()
    for flag in ("true", "apply"):
        run = red._run(monkeypatch, tmp_path, caplog, flag, world=_g5()._kb_field_world())
        assert run.rc == 0
        assert run.report["dropped_deidentify"] == 6, (flag, run.report["dropped_deidentify"])
        value, n = _metric(run, "learning.dropped.deidentify")
        assert (float(value), n) == (6.0, 6), (flag, value, n)


def test_r5_control_chars_escaped_on_render(monkeypatch, tmp_path, caplog):
    """R5: product names carrying a newline, ESC and U+2028 render escaped in the markdown
    exemplar line and in every log line; no forged line appears."""
    red = _red()
    controls = _control_set()
    run = red._run(monkeypatch, tmp_path, caplog, "true", world=_control_world(), md=True)
    assert run.rc == 0
    md = run.md_path.read_text(encoding="ascii")
    for line in md.split("\n"):
        assert not any(ch in controls for ch in line), repr(line)
        assert not line.startswith("[LEARNING] forged"), repr(line)
    for msg in run.messages():
        assert not any(ch in controls for ch in msg), repr(msg)
    exemplar = [m for m in run.messages() if m.startswith("[LEARNING] exemplar ")]
    assert any(("Nova" + "\\" + "x0a[LEARNING] forged") in m for m in exemplar), exemplar


def test_r6_render_helper():
    """R6: _render escapes C0 / C1 / U+2028 / U+2029 as backslash escapes, leaves the rest."""
    fn = getattr(_mod(), "_render", None)
    assert callable(fn), "scripts.cron_learning._render is missing (D22d)"
    assert fn("a" + chr(9) + "b") == "a" + "\\" + "x09b"
    assert fn(chr(0x85)) == "\\" + "x85"
    assert fn(chr(0x2029)) == "\\" + "u2029"
    assert fn("Plain Name EDP") == "Plain Name EDP"


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

def test_p1_clean_names_byte_identical(monkeypatch, tmp_path, caplog):
    """P1 (PIN): the default D22 world: the markdown bytes and the exemplar / eval_case log
    lines equal base."""
    red = _red()
    run = red._run(monkeypatch, tmp_path, caplog, "true", md=True)
    assert run.rc == 0
    assert hashlib.sha256(run.md_path.read_bytes()).hexdigest() == MD_SHA256_BASE
    assert _name_lines(run) == BASE_NAME_LINES, _name_lines(run)


def test_p2_report_keeps_raw_names(monkeypatch, tmp_path, caplog):
    """P2 (PIN): R5's world: the JSON report keeps the raw names (json-escaped on disk)."""
    red = _red()
    run = red._run(monkeypatch, tmp_path, caplog, "true", world=_control_world())
    names = _control_world()[red.T_COMPARISONS][0]["product_names"]
    found = [e for block in run.report["exemplar_candidates"].values() for e in block["exemplars"]
             if e["product_names"] == names]
    assert len(found) == 1, run.report["exemplar_candidates"]
    raw = run.report_path.read_bytes()
    assert all(b < 128 for b in raw)
    assert json.loads(raw.decode("ascii"))["exemplar_candidates"] == run.report["exemplar_candidates"]


def test_p3_clean_off_vocabulary_not_counted(monkeypatch, tmp_path, caplog):
    """P3 (PIN): a clean off-vocabulary kb_feedback field name maps to other and is not counted."""
    red = _red()
    world = _season_world(extra_specs=0)
    for row in world[red.T_KBFB]:
        row["field"] = "Bad-Name"
    run = red._run(monkeypatch, tmp_path, caplog, "true", world=world)
    kb = [c for c in run.report["clusters"] if c["bucket"] == "spec_wrong" and c["source"] == "kb"]
    assert [c["field"] for c in kb] == ["other"], kb
    assert run.report["dropped_deidentify"] == 0, run.report["dropped_deidentify"]


def test_p4_comparisons_read_single_page(monkeypatch, tmp_path, caplog):
    """P4 (PIN): the default world: each comparisons select carries one in_ on id, orders by
    id and the read returns every one of the eight ids."""
    red = _red()
    run = red._run(monkeypatch, tmp_path, caplog, "true")
    sel = run.fake.selects(red.T_COMPARISONS)
    assert len(sel) == 1, sel
    assert [f[0] for f in sel[0]["filters"]] == ["in_"] and sel[0]["filters"][0][1][0] == "id", sel[0]["filters"]
    assert sel[0]["orders"] == [("id", False)], sel[0]["orders"]
    assert run.report["tables"][red.T_COMPARISONS] == {"rows": 8, "status": "ok", "error": None}


@pytest.mark.parametrize("value", [None, "", "false", " 0 ", "OFF", "garbage"],
                         ids=["unset", "empty", "false", "pad0", "OFF", "garbage"])
def test_p5_flag_off_no_io(monkeypatch, caplog, value):
    """P5 (PIN): the full configuration with the flag OFF: rc 0, one INFO line, no client touch."""
    red = _red()
    red._full_config(monkeypatch)
    red._set_flag(monkeypatch, value)
    built = []
    monkeypatch.setattr(red._common(), "_admin_client", lambda: built.append("admin") or red._Recorder())
    rec = red._Recorder()
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    rc = _mod().main(["--report", "unused.json"], client=rec)
    assert rc == 0
    assert rec.calls == [] and built == [], (rec.calls, built)
    lines = [r.getMessage() for r in caplog.records if r.name == "cron_learning"]
    assert lines == [red.OFF_LINE], lines

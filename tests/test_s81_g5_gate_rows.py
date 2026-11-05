"""S81-G5 GREEN-owned gate rows (GATE_S81_G5 GC-2 / GC-3, the RED's open questions 1 and 2).

G5-GR1 test_g5_gr1_two_actors_one_case (GC-2): one comparison reported price-wrong by
TWO users is ONE case and TWO actors: ``cases`` counts distinct case keys and
``actors`` counts the distinct actors over EVERY report that maps to the cluster's
cases (never the first reporter only). With LEARNING_MIN_CASES=1 the cluster is
systematic (1 case, 2 actors); with the default 3 it is not. The inverse edit (an
actor recorded only when its case is first seen) is killed: actors 1.

G5-GR2 test_g5_gr2_screen_before_cut (GC-3, GC-4): seven confirmed fragrance rows,
one of which carries an e-mail shape in its winner_reason and sorts inside the first
five, with LEARNING_EXEMPLARS_PER_CATEGORY at its default 5: the de-identification
screen runs BEFORE the per-category cut, so the dropped candidate frees its slot:
five clean exemplar candidates, learning.dropped.deidentify 1; the eval candidate of
the same comparison is kept (its shape carries no winner_reason): seven eval
candidates. The inverse edit (cut first, screen after) is killed: four candidates.

G5-GR3..GR7 (RULINGS_REBASE_S81_G5 RB-G5-2, the adversary's MIN-2; each proven RED on a
byte copy of scripts/cron_learning.py carrying the adversary's edit): GR3 a 64-hex run
inside a longer token in a winner_reason drops the exemplar candidate (A4-anchored);
GR4 a Bahrain dialling prefix in a winner_reason and an 8-digit run in a product name drop their
candidates (A2-no973, A1-no8digit); GR5 a uuid shape with no 8-digit run in a
winner_reason drops the candidate (A3-nouuid); GR6 unclean kb_feedback field names
(an 8-digit run, an at sign) map to `other` and never reach a cluster, a grounding or
any output (A11-fieldname-noscreen); GR7 m0 and m1 both in SOURCE_METHODS and
different cluster under source `mixed`, never `unknown` (A12-mixed-unknown).

Every row drives scripts/cron_learning.py through the frozen RED file's fake client and
world builders (reached through ``tests.test_s81_d22_nightly_learning``); netguard on,
no socket, synthetic names and ids built at run time; pure ASCII, LF.
"""
from __future__ import annotations

import importlib
import json
import logging
import re

import pytest


def _red():
    return importlib.import_module("tests.test_s81_d22_nightly_learning")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    red = _red()
    red._leaf()  # the dotenv guard: the leaf (and its imports) load before any env is set
    for name in (red.FLAG,) + red.KNOBS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(red._common(), "_now", lambda: red.NOW)
    yield


def _run(monkeypatch, tmp_path, caplog, world, env=None, tag="run"):
    red = _red()
    mod = importlib.import_module("scripts.cron_learning")
    monkeypatch.setenv(red.FLAG, "true")
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)
    path = tmp_path / ("gr-%s.json" % tag)
    caplog.set_level(logging.DEBUG)
    rc = mod.main(["--report", str(path)], client=red._Client(world))
    assert rc == 0
    return json.loads(path.read_text(encoding="ascii"))


def _cluster(report, key):
    found = [c for c in report["clusters"] if (c["bucket"], c["category"], c["source"], c["field"]) == key]
    assert len(found) == 1, report["clusters"]
    return found[0]


def _metric(report, name):
    found = [m for m in report["metrics"] if m[0] == name]
    assert len(found) == 1, report["metrics"]
    return found[0][1], found[0][2]


# ---------------------------------------------------------------------------
# G5-GR1
# ---------------------------------------------------------------------------

def _two_reporter_world():
    red = _red()
    comparisons = [red._cmp(1, red._uid(1), "fragrances", ("Anise Rose EDP", "Basil Oud EDT"),
                            "page_scrape", "page_scrape")]
    feedback = [red._fb(1, red._uid(1), 1, price_correct="wrong"),
                red._fb(2, red._uid(2), 1, price_correct="wrong")]
    return {red.T_COMPARISONS: comparisons, red.T_FEEDBACK: feedback}


def test_g5_gr1_two_actors_one_case(monkeypatch, tmp_path, caplog):
    key = ("price_wrong", "fragrances", "page_scrape", "price")
    report = _run(monkeypatch, tmp_path, caplog, _two_reporter_world(), tag="gr1-default")
    cluster = _cluster(report, key)
    assert (cluster["cases"], cluster["actors"], cluster["systematic"]) == (1, 2, False), cluster
    assert (report["buckets"]["price_wrong"]["cases"], report["buckets"]["price_wrong"]["actors"]) == (1, 2)
    assert _metric(report, "learning.cases.price_wrong") == (1, 2)
    assert report["proposals"] == []
    report = _run(monkeypatch, tmp_path, caplog, _two_reporter_world(), env={"LEARNING_MIN_CASES": "1"},
                  tag="gr1-min1")
    cluster = _cluster(report, key)
    assert (cluster["cases"], cluster["actors"], cluster["systematic"]) == (1, 2, True), cluster
    assert [(p["cases"], p["distinct_actors"], p["proposed_action"]) for p in report["proposals"]] == [
        (1, 2, "recheck_source")]


# ---------------------------------------------------------------------------
# G5-GR2
# ---------------------------------------------------------------------------

_PAIRS = (("Anise Rose EDP", "Basil Oud EDT"), ("Birch Musk EDP", "Cedar Amber EDP"),
          ("Cumin Smoke EDP", "Dill Leaf EDT"), ("Daisy Bloom EDP", "Elder Wood EDP"),
          ("Ebony Iris EDP", "Fig Vanilla EDP"), ("Fennel Spice EDT", "Ginger Citrus EDT"),
          ("Gorse Moss EDP", "Hazel Rose EDP"))
_UNCLEAN_INDEX = 2


def _confirmed_world():
    red = _red()
    comparisons, feedback = [], []
    for i, names in enumerate(_PAIRS):
        n = 50 + i
        wr = ("Ask " + red._email() + " for the decant.") if i == _UNCLEAN_INDEX else None
        comparisons.append(red._cmp(n, red._uid(2), "fragrances", names, "page_scrape", "page_scrape", wr=wr))
        feedback.append(red._fb(200 + i, red._uid(3), n, useful=True, winner_correct="correct"))
    return {red.T_COMPARISONS: comparisons, red.T_FEEDBACK: feedback}


def test_g5_gr2_screen_before_cut(monkeypatch, tmp_path, caplog):
    report = _run(monkeypatch, tmp_path, caplog, _confirmed_world(), tag="gr2")
    assert report["thresholds"]["exemplars_per_category"] == 5
    block = report["exemplar_candidates"]["fragrances"]
    got = [tuple(e["product_names"]) for e in block["exemplars"]]
    clean = [p for i, p in enumerate(_PAIRS) if i != _UNCLEAN_INDEX]
    assert (block["count"], got) == (5, clean[:5]), got
    assert _PAIRS[_UNCLEAN_INDEX] not in got
    assert report["dropped_deidentify"] == 1
    assert _metric(report, "learning.dropped.deidentify") == (1, 1)
    assert _metric(report, "learning.exemplar_candidates") == (5, 1)
    evals = [tuple(e["product_names"]) for e in report["eval_candidates"]]
    assert evals == list(_PAIRS), evals
    assert _metric(report, "learning.eval_candidates") == (7, 7)


# ---------------------------------------------------------------------------
# G5-GR3..GR7 (RULINGS_REBASE_S81_G5 RB-G5-2): the screen shapes inside SELECTED
# fields, the field-name screen and the mixed price source. Every sentinel is built
# at run time (no shape literal in this file).
# ---------------------------------------------------------------------------

def _hex64_inside():
    return "Lot" + ("f" * 64) + "z"


def _bh_prefix():
    return "Call " + "+97" + "3" + " desk"


def _eight_run():
    return "Sz" + "1234" + "5678" + "x"


def _uuid_letters():
    return "abcdefab" + "-cdef" + "-4abc" + "-8def" + "-" + ("abcdef" * 2)


def _shape_res():
    return {
        "hex64": re.compile("[0-9a-fA-F]{" + "64}"),
        "bh": re.compile(re.escape("+97" + "3")),
        "eight": re.compile("[0-9]{" + "8}"),
        "uuid": re.compile("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE),
        "at": re.compile(re.escape(chr(64))),
    }


def _confirmed_rows(rows):
    """rows: (n, names, wr) -> a world of confirmed (useful + winner correct) comparisons."""
    red = _red()
    comparisons, feedback = [], []
    for n, names, wr in rows:
        comparisons.append(red._cmp(n, red._uid(2), "fragrances", names, "page_scrape", "page_scrape", wr=wr))
        feedback.append(red._fb(300 + n, red._uid(3), n, useful=True, winner_correct="correct"))
    return {red.T_COMPARISONS: comparisons, red.T_FEEDBACK: feedback}


def _exemplar_pairs(report):
    block = report["exemplar_candidates"].get("fragrances", {"exemplars": []})
    return [tuple(e["product_names"]) for e in block["exemplars"]]


def _eval_pairs(report):
    return [tuple(e["product_names"]) for e in report["eval_candidates"]]


_CLEAN = ("Anise Rose EDP", "Basil Oud EDT")


def test_g5_gr3_hex64_inside_selected_field_drops(monkeypatch, tmp_path, caplog):
    unclean = ("Birch Musk EDP", "Cedar Amber EDP")
    sentinel = _hex64_inside()
    assert _shape_res()["hex64"].search(sentinel) and not _shape_res()["eight"].search(sentinel)
    world = _confirmed_rows([(60, _CLEAN, None), (61, unclean, "Batch " + sentinel + " sealed.")])
    report = _run(monkeypatch, tmp_path, caplog, world, tag="gr3")
    assert _exemplar_pairs(report) == [_CLEAN]
    assert report["dropped_deidentify"] == 1
    assert _metric(report, "learning.dropped.deidentify") == (1, 1)
    assert _eval_pairs(report) == [_CLEAN, unclean]  # the eval shape carries no winner_reason (GC-4)
    assert not _shape_res()["hex64"].search(json.dumps(report, sort_keys=True))


def test_g5_gr4_bh_prefix_and_eight_digit_run_drop(monkeypatch, tmp_path, caplog):
    res = _shape_res()
    reason_pair = ("Cumin Smoke EDP", "Dill Leaf EDT")
    name_pair = ("Rose " + _eight_run() + " EDP", "Elder Wood EDP")
    assert res["bh"].search(_bh_prefix()) and not res["eight"].search(_bh_prefix())
    assert res["eight"].search(name_pair[0]) and not res["hex64"].search(name_pair[0])
    world = _confirmed_rows([(62, _CLEAN, None), (63, reason_pair, _bh_prefix() + " for the decant."),
                             (64, name_pair, None)])
    report = _run(monkeypatch, tmp_path, caplog, world, tag="gr4")
    got = _exemplar_pairs(report)
    assert reason_pair not in got and name_pair not in got
    assert got == [_CLEAN]
    # the winner_reason drop: 1 exemplar; the name drop: 1 exemplar + 1 eval candidate
    assert report["dropped_deidentify"] == 3
    assert _metric(report, "learning.dropped.deidentify") == (3, 3)
    assert _eval_pairs(report) == [_CLEAN, reason_pair]
    text = json.dumps(report, sort_keys=True)
    assert not res["bh"].search(text) and not res["eight"].search(text)


def test_g5_gr5_uuid_without_eight_digit_run_drops(monkeypatch, tmp_path, caplog):
    res = _shape_res()
    unclean = ("Daisy Bloom EDP", "Fig Vanilla EDP")
    sentinel = _uuid_letters()
    assert res["uuid"].search(sentinel)
    assert not res["eight"].search(sentinel) and not res["hex64"].search(sentinel)
    world = _confirmed_rows([(65, _CLEAN, None), (66, unclean, "Lot " + sentinel + " sealed.")])
    report = _run(monkeypatch, tmp_path, caplog, world, tag="gr5")
    assert _exemplar_pairs(report) == [_CLEAN]
    assert report["dropped_deidentify"] == 1
    assert _metric(report, "learning.dropped.deidentify") == (1, 1)
    assert not res["uuid"].search(json.dumps(report, sort_keys=True))


def _kb_field_world():
    red = _red()
    pid = "fragrances|x|y"
    eight_field = "f" + "1234" + "5678"
    at_field = "conc" + chr(64) + "x"
    kbfb = []
    for j, field in enumerate((eight_field, at_field)):
        for i, ch in ((1, "a"), (2, "b"), (3, "c")):
            kbfb.append({"id": "row-kf-%d-%d" % (j, i), "compare_request_id": red._rid(10 * j + i),
                         "product_id": pid, "field": field, "verdict": "wrong", "device_key": red._dev(ch),
                         "created_at": red.T_IN})
    specs = [{"id": "row-ks-%d" % j, "product_id": pid, "field": field,
              "source_url": "https://" + "store-a.example.com/p/ok-%d" % j, "cited": True}
             for j, field in enumerate((eight_field, at_field))]
    return {red.T_KBFB: kbfb, red.T_SPECS: specs}


def test_g5_gr6_unclean_kb_field_name_screened(monkeypatch, tmp_path, caplog):
    """An unclean kb_feedback field name never reaches a cluster, a grounding entry or any output.

    The 8-digit field name passes the field-name shape (^[a-z][a-z0-9_]{0,63}$) and is
    stopped only by the de-identification screen inside _field_name (A11); the at-sign one
    is stopped by the shape first. Both map to the field `other`, so the cited kb_specs rows
    of the raw names never ground the cluster. The field-name screen maps, it does not drop
    a candidate; D22d counts each unclean field-name row in learning.dropped.deidentify
    (G5-GR6 amended, E2: six rows here).
    """
    red = _red()
    res = _shape_res()
    for flag in ("true", "apply"):
        run = red._run(monkeypatch, tmp_path, caplog, flag, world=_kb_field_world(), md=True)
        assert run.rc == 0
        kb_spec = [c for c in run.report["clusters"] if c["bucket"] == "spec_wrong" and c["source"] == "kb"]
        assert [c["field"] for c in kb_spec] == ["other"], kb_spec
        assert (kb_spec[0]["cases"], kb_spec[0]["actors"]) == (6, 3)
        props = [p for p in run.report["proposals"] if p["bucket"] == "spec_wrong"]
        assert [(p["field"], p["grounding"], p["proposed_action"]) for p in props] == [
            ("other", [], "needs_operator")], props
        assert run.report["dropped_deidentify"] == 6
        texts = [run.report_path.read_text(encoding="ascii")]
        if run.md_path.exists():
            texts.append(run.md_path.read_text(encoding="ascii"))
        texts += [r.getMessage() for r in run.records]
        for w in run.fake.writes():
            texts += [json.dumps(r, sort_keys=True) for r in (w["payload"] or [])]
        for text in texts:
            assert not res["eight"].search(text), text[:300]
            assert not res["at"].search(text), text[:300]


def test_g5_gr7_mixed_price_source_clusters_as_mixed(monkeypatch, tmp_path, caplog):
    red = _red()
    mod = importlib.import_module("scripts.cron_learning")
    assert "page_scrape" in mod.SOURCE_METHODS and "local_bhd" in mod.SOURCE_METHODS
    world = {red.T_COMPARISONS: [red._cmp(67, red._uid(1), "fragrances", _CLEAN, "page_scrape", "local_bhd")],
             red.T_FEEDBACK: [red._fb(267, red._uid(2), 67, price_correct="wrong")]}
    report = _run(monkeypatch, tmp_path, caplog, world, env={"LEARNING_MIN_CASES": "1", "LEARNING_MIN_DEVICES": "1"},
                  tag="gr7")
    price = [c for c in report["clusters"] if c["bucket"] == "price_wrong"]
    assert [(c["category"], c["source"], c["field"]) for c in price] == [("fragrances", "mixed", "price")], price
    assert price[0]["systematic"] is True
    assert [(p["source"], p["proposed_action"]) for p in report["proposals"]] == [("mixed", "needs_operator")]

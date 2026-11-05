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

Both rows drive scripts/cron_learning.py through the frozen RED file's fake client and
world builders (reached through ``tests.test_s81_d22_nightly_learning``); netguard on,
no socket, synthetic names and ids built at run time; pure ASCII, LF.
"""
from __future__ import annotations

import importlib
import json
import logging

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

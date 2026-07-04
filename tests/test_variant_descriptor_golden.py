# -*- coding: utf-8 -*-
"""genuine-price Wave-2 A0 — GOLDEN EQUIVALENCE replay (design lane R5 STEP 0 / R6).

Replays every case of tests/data/variant_descriptor_golden_corpus.json through the
LIVE decision functions (_axis_mismatch / _selection_match / is_exact_match /
_backstop_identity_ok / _category_type_added) and asserts every verdict is
IDENTICAL to the committed pin. This is the behavior-identity gate for the Phase-A
VariantDescriptor refactor: the refactored implementation must reproduce the corpus
byte-for-byte (including pinned exceptions, recorded as {"error": "<Type>"}).

Free-unit suite: no network, no marks. The corpus is regenerated ONLY via
scripts/dump_descriptor_golden_corpus.py (a deliberate, reviewed re-pin) — never
edited by hand and never regenerated to "make the test pass".
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO / "tests" / "data" / "variant_descriptor_golden_corpus.json"
DUMP_SCRIPT = REPO / "scripts" / "dump_descriptor_golden_corpus.py"


def _load_dump_module():
    """Import compute_verdicts from the dump script so the replay computes verdicts
    EXACTLY the way the corpus was recorded (single source of truth, no drift)."""
    spec = importlib.util.spec_from_file_location(
        "dump_descriptor_golden_corpus", str(DUMP_SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fmt(value):
    """ASCII-safe rendering for failure output (Windows console discipline)."""
    return ascii(value)


@pytest.fixture(scope="module")
def corpus():
    with open(str(CORPUS_PATH), encoding="utf-8") as fh:
        return json.load(fh)


def test_corpus_shape(corpus):
    meta = corpus["_meta"]
    assert meta["n_cases"] == len(corpus["cases"])
    assert meta["n_cases"] >= 900, "coverage floor: the corpus must stay >=900 cases"
    # every required axis the dump enforces is present in the tally
    assert meta["axis_tally"], "axis tally missing"
    assert all(n >= 1 for n in meta["axis_tally"].values())


def test_golden_corpus_equivalence(corpus, monkeypatch):
    """Every pinned verdict must reproduce through the live functions."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE",
                       corpus["_meta"]["env"]["ENABLE_EXACT_PRICE_GATE"])
    dump = _load_dump_module()

    mismatches = []
    for case in corpus["cases"]:
        expected = case["verdicts"]
        actual = dump.compute_verdicts(case)
        if actual == expected:
            continue
        # collect per-key detail for the report
        detail = []
        for key in sorted(expected):
            if key == "selection_match":
                for sk in sorted(expected[key]):
                    if expected[key][sk] != actual[key].get(sk):
                        detail.append("selection_match[{}]: pinned={} actual={}".format(
                            sk, _fmt(expected[key][sk]), _fmt(actual[key].get(sk))))
            elif expected[key] != actual.get(key):
                detail.append("{}: pinned={} actual={}".format(
                    key, _fmt(expected[key]), _fmt(actual.get(key))))
        mismatches.append(
            "case {} [{}] query={} title={} brand={} axes={}\n    {}".format(
                case["id"], case["category"], _fmt(case["query"]), _fmt(case["title"]),
                _fmt(case["brand"]), case["axes"], "\n    ".join(detail)))

    if mismatches:
        shown = mismatches[:20]
        pytest.fail(
            "GOLDEN CORPUS DIVERGENCE: {} of {} cases changed verdict "
            "(first {} shown).\nA Phase-A refactor must be behavior-identical; if a "
            "change is DELIBERATE (Phase B), regenerate the corpus via "
            "scripts/dump_descriptor_golden_corpus.py in the same reviewed commit.\n\n"
            "{}".format(len(mismatches), len(corpus["cases"]), len(shown),
                        "\n\n".join(shown)))

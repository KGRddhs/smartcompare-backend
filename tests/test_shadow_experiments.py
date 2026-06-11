"""Unit tests for scripts/shadow_experiments.py — the I4 shadow harness.

All tests here are FREE (no OpenAI, no Serper, no DB): they exercise the pure
reconstruction + grading + aggregation logic with hand-built fixtures. The
live verdict arms (o3-mini / multi-agent / reviews-trim) and the L2 reader are
tested separately and marked live_unit / live_db.

Grading parity is the load-bearing invariant: shadow grading must call the
SAME eval_runner functions production grading does, so a shadow "winner flip"
means the same thing the gold eval means.
"""
from __future__ import annotations

import json

import pytest

from scripts import shadow_experiments as se


# ---------------------------------------------------------------------------
# Baseline grade loading + subset selection
# ---------------------------------------------------------------------------

def _write_baseline(tmp_path, records):
    p = tmp_path / "baseline.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return p


def test_load_baseline_grades_keys_by_id(tmp_path):
    recs = [
        {"id": "elec-001", "category": "electronics", "error": None,
         "price_pass": True, "specs_score": 0.5, "winner_pass": False,
         "factual_pass": True, "weighted_score": 0.5, "passing": False},
        {"id": "make-013", "category": "makeup", "error": None,
         "price_pass": True, "specs_score": 1.0, "winner_pass": False,
         "factual_pass": True, "weighted_score": 0.7, "passing": False},
    ]
    p = _write_baseline(tmp_path, recs)
    loaded = se.load_baseline_grades(p)
    assert set(loaded) == {"elec-001", "make-013"}
    assert loaded["make-013"]["specs_score"] == 1.0


def test_load_baseline_grades_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        se.load_baseline_grades(tmp_path / "nope.jsonl")


def test_select_bias45_applies_all_five_criteria(tmp_path):
    recs = [
        # qualifies: pure winner-bias
        {"id": "a", "category": "x", "error": None, "price_pass": True,
         "factual_pass": True, "specs_score": 0.6, "winner_pass": False},
        # disqualified: winner already passes
        {"id": "b", "category": "x", "error": None, "price_pass": True,
         "factual_pass": True, "specs_score": 0.9, "winner_pass": True},
        # disqualified: price fails
        {"id": "c", "category": "x", "error": None, "price_pass": False,
         "factual_pass": True, "specs_score": 0.9, "winner_pass": False},
        # disqualified: specs below 0.5
        {"id": "d", "category": "x", "error": None, "price_pass": True,
         "factual_pass": True, "specs_score": 0.4, "winner_pass": False},
        # disqualified: error row
        {"id": "e", "category": "x", "error": "http_400", "price_pass": True,
         "factual_pass": True, "specs_score": 0.9, "winner_pass": False},
        # disqualified: factual fails
        {"id": "f", "category": "x", "error": None, "price_pass": True,
         "factual_pass": False, "specs_score": 0.9, "winner_pass": False},
    ]
    baseline = se.load_baseline_grades(_write_baseline(tmp_path, recs))
    assert se.select_bias45(baseline) == ["a"]


def test_select_graded200_excludes_error_rows(tmp_path):
    recs = [
        {"id": "ok1", "error": None, "category": "x"},
        {"id": "err1", "error": "http_400", "category": "x"},
        {"id": "ok2", "error": None, "category": "x"},
        {"id": "err2", "error": "http_502", "category": "x"},
    ]
    baseline = se.load_baseline_grades(_write_baseline(tmp_path, recs))
    assert set(se.select_graded200(baseline)) == {"ok1", "ok2"}


# ---------------------------------------------------------------------------
# Query splitting + L2 matching
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected", [
    ("iPhone 15 vs Galaxy S24", ("iPhone 15", "Galaxy S24")),
    ("NOW Foods D3 vs Solgar D3", ("NOW Foods D3", "Solgar D3")),
    ("Bertolli olive oil vs. Carbonell olive oil", ("Bertolli olive oil", "Carbonell olive oil")),
    ("Daikin 1.5 ton split AC VS LG 1.5 ton DualCool", ("Daikin 1.5 ton split AC", "LG 1.5 ton DualCool")),
])
def test_split_products_from_query(query, expected):
    assert se._split_products_from_query(query) == expected


def test_split_products_from_query_no_separator_returns_none():
    assert se._split_products_from_query("just one product") is None
    assert se._split_products_from_query("vs") is None


def test_match_l2_product_exact_brand_name():
    rows = [
        {"brand": "NOW Foods", "name": "D3", "category": "supplements"},
        {"brand": "Solgar", "name": "D3", "category": "supplements"},
    ]
    m = se.match_l2_product("NOW Foods D3", "supplements", rows)
    assert m is not None and m["brand"] == "NOW Foods"


def test_match_l2_product_subsequence_brand_prefix():
    # gold phrase carries the brand the L2 row omits in name ('Apple iPhone 15'
    # vs row brand=Apple name='iPhone 15').
    rows = [{"brand": "Apple", "name": "iPhone 15", "category": "electronics"}]
    m = se.match_l2_product("Apple iPhone 15", "electronics", rows)
    assert m is not None and m["name"] == "iPhone 15"


def test_match_l2_product_token_overlap_picks_best():
    rows = [
        {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics"},
        {"brand": "Samsung", "name": "Galaxy Tab S9", "category": "electronics"},
    ]
    m = se.match_l2_product("Galaxy S24", "electronics", rows)
    assert m is not None and m["name"] == "Galaxy S24"


def test_match_l2_product_no_shared_token_returns_none():
    rows = [{"brand": "Sony", "name": "WH-1000XM5", "category": "electronics"}]
    assert se.match_l2_product("Dyson V15", "electronics", rows) is None


def test_match_l2_product_category_breaks_tie():
    rows = [
        {"brand": "Dove", "name": "soap", "category": "grocery"},
        {"brand": "Dove", "name": "soap", "category": "skincare"},
    ]
    m = se.match_l2_product("Dove soap", "skincare", rows)
    assert m is not None and m["category"] == "skincare"


# ---------------------------------------------------------------------------
# product_data assembly
# ---------------------------------------------------------------------------

def test_assemble_product_data_shapes_both_products():
    gold = {"category": "supplements"}
    row_a = {"brand": "NOW Foods", "name": "D3", "variant": None,
             "category": "supplements", "specs": {"iu": "5000"},
             "reviews": {"consensus": "good"},
             "price": {"amount": 5.5, "currency": "BHD"}}
    row_b = {"brand": "Solgar", "name": "D3", "variant": None,
             "category": "supplements", "specs": {"iu": "1000"},
             "reviews": {"consensus": "ok"},
             "price": {"amount": 8.0, "currency": "BHD"}}
    pd = se.assemble_product_data("supp-001", gold, row_a, row_b)
    assert pd is not None and len(pd) == 2
    assert pd[0]["full_name"] == "NOW Foods D3"
    assert pd[0]["best_price"] == 5.5
    assert pd[0]["specs"] == {"iu": "5000"}
    assert pd[1]["brand"] == "Solgar"


def test_assemble_product_data_unmatched_returns_none():
    assert se.assemble_product_data("x", {}, None, {"brand": "a", "name": "b"}) is None
    assert se.assemble_product_data("x", {}, {"brand": "a", "name": "b"}, None) is None


def test_assemble_product_data_missing_price_omits_best_price():
    row = {"brand": "B", "name": "N", "category": "other", "specs": {}, "reviews": {}}
    pd = se.assemble_product_data("x", {}, dict(row), dict(row))
    assert "best_price" not in pd[0]
    assert "price" not in pd[0]


# ---------------------------------------------------------------------------
# Verdict -> eval body splicing (the grading-parity bridge)
# ---------------------------------------------------------------------------

def test_verdict_to_eval_body_winner_index_reads_back():
    from scripts.eval_runner import extract_winner_index

    body = se._verdict_to_eval_body({"winner_index": 1}, [{}, {}])
    assert extract_winner_index(body) == 1


def test_verdict_to_eval_body_winner_idx_alias():
    from scripts.eval_runner import extract_winner_index

    body = se._verdict_to_eval_body({"winner_idx": 0}, [{}, {}])
    assert extract_winner_index(body) == 0


def test_verdict_to_eval_body_collects_all_prose_for_factual():
    from scripts.eval_runner import collect_verdict_text

    verdict = {
        "winner_index": 0,
        "winner_reason": "iPhone wins on camera",
        "key_tradeoff": "Galaxy has bigger screen",
        "best_for": {"product_0": "power users", "product_1": "budget buyers"},
        "value_context": {"product_0": "premium tier", "product_1": "mid tier"},
        "factual_verdict": {"line1": "8K video recording claim", "line2": "second line"},
    }
    text = collect_verdict_text(se._verdict_to_eval_body(verdict, [{}, {}]))
    # every prose surface must be present so forbidden-fact scanning works
    assert "camera" in text
    assert "bigger screen" in text
    assert "power users" in text
    assert "premium tier" in text
    assert "8K video recording" in text


def test_verdict_to_eval_body_factual_grade_catches_forbidden_fact():
    verdict = {"winner_index": 0, "winner_reason": "has 8K video recording on base"}
    body = se._verdict_to_eval_body(verdict, [{}, {}])
    assert se.grade_factual(se.collect_verdict_text(body), ["8K video recording"]) is False
    assert se.grade_factual(se.collect_verdict_text(body), ["USB-C 3.2"]) is True


@pytest.mark.parametrize("field,idx,expected", [
    ("plain string", 0, "plain string"),
    ("plain string", 1, ""),
    ({"product_0": "a", "product_1": "b"}, 1, "b"),
    (["first", "second"], 1, "second"),
    (None, 0, ""),
    (123, 0, ""),
])
def test_per_product_text(field, idx, expected):
    assert se._per_product_text(field, idx) == expected


# ---------------------------------------------------------------------------
# Arm grading: flip detection + axis inheritance
# ---------------------------------------------------------------------------

def _vi(**kw):
    base = dict(
        id="t-1", category="electronics", query="A vs B", region="bahrain",
        comparison_type="value", expected_winner_index=1,
        forbidden_facts=[], product_data=[{}, {}], scores_summary="",
        baseline_price_pass=True, baseline_specs_score=1.0,
        baseline_winner_pass=False, baseline_factual_pass=True,
    )
    base.update(kw)
    return se.VerdictInput(**base)


_WEIGHTS = {"price": 0.25, "specs": 0.25, "winner": 0.30, "factual": 0.20}


def test_grade_arm_verdict_flip_to_correct():
    # baseline winner_pass=False, expected=1; arm picks 1 -> flips to correct
    vi = _vi(expected_winner_index=1, baseline_winner_pass=False)
    g = se.grade_arm_verdict(vi, {"winner_index": 1}, verdict_ms=1200, cost_usd=0.008,
                             weights=_WEIGHTS)
    assert g.winner_pass is True
    assert g.winner_flipped_to_correct is True
    assert g.winner_flipped_to_wrong is False
    # price+specs inherited from baseline
    assert g.price_pass is True and g.specs_score == 1.0


def test_grade_arm_verdict_flip_to_wrong_is_a_regression():
    # baseline winner_pass=True, expected=0; arm picks 1 -> flips to WRONG
    vi = _vi(expected_winner_index=0, baseline_winner_pass=True)
    g = se.grade_arm_verdict(vi, {"winner_index": 1}, verdict_ms=900, cost_usd=0.001,
                             weights=_WEIGHTS)
    assert g.winner_pass is False
    assert g.winner_flipped_to_wrong is True
    assert g.winner_flipped_to_correct is False


def test_grade_arm_verdict_weighted_uses_canonical_weights():
    # price T (.25) + specs 1.0(.25) + winner T(.30) + factual T(.20) = 1.0
    vi = _vi(expected_winner_index=0, baseline_price_pass=True,
             baseline_specs_score=1.0, baseline_factual_pass=True)
    g = se.grade_arm_verdict(vi, {"winner_index": 0}, verdict_ms=1000, cost_usd=0.008,
                             weights=_WEIGHTS)
    assert g.weighted_score == pytest.approx(1.0)
    assert g.passing is True


def test_grade_arm_verdict_error_scores_winner_and_factual_false():
    vi = _vi()
    g = se.grade_arm_verdict(vi, {}, verdict_ms=0, cost_usd=0.0, weights=_WEIGHTS,
                             error="openai_timeout")
    assert g.error == "openai_timeout"
    assert g.winner_pass is False and g.factual_pass is False
    assert g.passing is False
    # price/specs still reflect baseline (honest about which axis failed)
    assert g.price_pass is True and g.specs_score == 1.0


def test_grade_arm_verdict_factual_regression_flagged_via_weighted():
    # arm emits a forbidden fact -> factual flips False even though winner correct
    vi = _vi(expected_winner_index=0, forbidden_facts=["8K video"],
             baseline_factual_pass=True)
    g = se.grade_arm_verdict(vi, {"winner_index": 0, "winner_reason": "shoots 8K video"},
                             verdict_ms=1000, cost_usd=0.008, weights=_WEIGHTS)
    assert g.factual_pass is False
    assert g.winner_pass is True


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def test_aggregate_arm_counts_flips_and_costs():
    grades = [
        se.ArmGrade(id="a", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=True, factual_pass=True, weighted_score=1.0,
                    passing=True, baseline_winner_pass=False, baseline_weighted=0.7,
                    winner_flipped_to_correct=True, winner_flipped_to_wrong=False,
                    verdict_ms=1000, cost_usd=0.008),
        se.ArmGrade(id="b", category="x", price_pass=True, specs_score=0.5,
                    winner_pass=False, factual_pass=True, weighted_score=0.45,
                    passing=False, baseline_winner_pass=True, baseline_weighted=0.75,
                    winner_flipped_to_correct=False, winner_flipped_to_wrong=True,
                    verdict_ms=2000, cost_usd=0.012),
    ]
    r = se.aggregate_arm("test_arm", grades)
    assert r.n_covered == 2
    assert r.winner_flips_to_correct == 1
    assert r.winner_flips_to_wrong == 1
    assert r.net_winner_flips == 0
    assert r.total_cost_usd == pytest.approx(0.02)
    assert r.mean_cost_usd == pytest.approx(0.01)
    assert r.n_passing == 1
    assert r.p50_verdict_ms in (1000, 2000)


def test_aggregate_arm_excludes_errored_from_cost_and_latency():
    grades = [
        se.ArmGrade(id="ok", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=True, factual_pass=True, weighted_score=1.0,
                    passing=True, baseline_winner_pass=False, baseline_weighted=0.7,
                    winner_flipped_to_correct=True, winner_flipped_to_wrong=False,
                    verdict_ms=1500, cost_usd=0.008),
        se.ArmGrade(id="err", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=False, factual_pass=False, weighted_score=0.5,
                    passing=False, baseline_winner_pass=True, baseline_weighted=0.7,
                    winner_flipped_to_correct=False, winner_flipped_to_wrong=True,
                    verdict_ms=0, cost_usd=0.0, error="timeout"),
    ]
    r = se.aggregate_arm("a", grades)
    assert r.n_errors == 1
    # cost + latency means computed over the 1 successful row only
    assert r.mean_cost_usd == pytest.approx(0.008)
    assert r.mean_verdict_ms == 1500.0
    assert r.n_covered == 2

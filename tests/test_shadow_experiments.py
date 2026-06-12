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


@pytest.fixture(autouse=True)
def _reset_l2_cache():
    """The all-category L2 dump is cached at module level (one DB/dump read per
    process). Clear it before every test so a real load never leaks into the
    pure-logic tests and SHADOW_L2_DUMP monkeypatches take effect cleanly."""
    se._L2_DUMP_CACHE = None
    yield
    se._L2_DUMP_CACHE = None


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


def test_match_l2_product_alias_expansion_ps5():
    # gold phrase 'PS5' shares ZERO raw tokens with 'Sony PlayStation 5' —
    # the alias expansion recovers the join.
    rows = [{"brand": "Sony", "name": "PlayStation 5", "category": "electronics"}]
    m = se.match_l2_product("PS5", "electronics", rows)
    assert m is not None and m["name"] == "PlayStation 5"


def test_expand_aliases_is_additive():
    out = se._expand_aliases({"ps5"})
    assert "ps5" in out  # original kept
    assert "playstation" in out and "5" in out  # expansion added


def test_match_l2_product_alias_does_not_overmatch():
    # 'PS5' must NOT match an unrelated playstation-free row just because of
    # the expansion — still needs a genuine shared token with the L2 row.
    rows = [{"brand": "Microsoft", "name": "Xbox Series X", "category": "electronics"}]
    assert se.match_l2_product("PS5", "electronics", rows) is None


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


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def test_call_cost_usd_gpt4o():
    # (1000 * 2.50 + 500 * 10.00) / 1e6 = 0.0075
    assert se.call_cost_usd("gpt-4o", 1000, 500) == pytest.approx(0.0075)


def test_call_cost_usd_mini():
    # (1000 * 0.15 + 1000 * 0.60) / 1e6 = 0.00075
    assert se.call_cost_usd("gpt-4o-mini", 1000, 1000) == pytest.approx(0.00075)


def test_call_cost_usd_o3_mini():
    # (1000 * 1.10 + 1000 * 4.40) / 1e6 = 0.0055
    assert se.call_cost_usd("o3-mini", 1000, 1000) == pytest.approx(0.0055)


def test_call_cost_usd_unknown_model_falls_back_to_mini():
    assert se.call_cost_usd("ghost-model", 1000, 1000) == pytest.approx(0.00075)


def test_multiagent_cost_split_prices_each_leg_at_own_rate():
    # 3 mini analysts: 3000 pt + 600 ct ; 4o editor: 2000 pt + 400 ct
    res = se.ArmCallResult(
        verdict={"winner_index": 0, "_shadow_cost_split": {
            "gpt-4o-mini": {"pt": 3000, "ct": 600},
            "gpt-4o": {"pt": 2000, "ct": 400},
        }},
        prompt_tokens=5000, completion_tokens=1000, model="multiagent",
    )
    mini = se.call_cost_usd("gpt-4o-mini", 3000, 600)
    editor = se.call_cost_usd("gpt-4o", 2000, 400)
    assert se._arm_call_cost(res) == pytest.approx(mini + editor)


def test_arm_call_cost_single_model_uses_model_rate():
    res = se.ArmCallResult(verdict={"winner_index": 1}, prompt_tokens=1000,
                           completion_tokens=500, model="gpt-4o")
    assert se._arm_call_cost(res) == pytest.approx(0.0075)


# ---------------------------------------------------------------------------
# build_verdict_inputs skip paths (L2 + scoring mocked — no DB, no network)
# ---------------------------------------------------------------------------

def _gold(queries):
    return {"_metadata": {"axis_weights": {
        "price_accuracy": 0.25, "specs_correctness": 0.25,
        "winner_correctness": 0.30, "factual_claim_integrity": 0.20}},
        "queries": queries}


def test_build_verdict_inputs_skips_error_and_missing(monkeypatch, tmp_path):
    gold = _gold([
        {"id": "ok-1", "query": "Apple iPhone 15 vs Samsung Galaxy S24",
         "category": "electronics", "region": "bahrain",
         "expected_winner_index": 0, "forbidden_facts": []},
        {"id": "err-1", "query": "X vs Y", "category": "electronics"},
        {"id": "nosplit-1", "query": "single product", "category": "electronics"},
    ])
    baseline = {
        "ok-1": {"error": None, "price_pass": True, "specs_score": 1.0,
                 "winner_pass": False, "factual_pass": True},
        "err-1": {"error": "http_400", "price_pass": False, "specs_score": 0.0,
                  "winner_pass": False, "factual_pass": False},
        "nosplit-1": {"error": None, "price_pass": True, "specs_score": 1.0,
                      "winner_pass": False, "factual_pass": True},
    }
    # Mock L2 to return matchable rows for the electronics products.
    l2_rows = [
        {"brand": "Apple", "name": "iPhone 15", "variant": None,
         "category": "electronics", "specs": {"os": "iOS"}, "reviews": {},
         "price": {"amount": 300.0, "currency": "BHD"}},
        {"brand": "Samsung", "name": "Galaxy S24", "variant": None,
         "category": "electronics", "specs": {"os": "Android"}, "reviews": {},
         "price": {"amount": 280.0, "currency": "BHD"}},
    ]
    monkeypatch.setattr(se, "_fetch_l2_rows_for_category", lambda cat: l2_rows)
    monkeypatch.setattr(se, "_compute_scores_summary_offline", lambda pd: "SCORES")

    built, skipped = se.build_verdict_inputs(gold, baseline, ["ok-1", "err-1", "nosplit-1"])
    assert [b.id for b in built] == ["ok-1"]
    assert built[0].scores_summary == "SCORES"
    assert built[0].product_data[0]["full_name"] == "Apple iPhone 15"
    reasons = {s["id"]: s["reason"] for s in skipped}
    assert reasons["err-1"].startswith("baseline_error")
    assert reasons["nosplit-1"] == "unsplittable_query"


def test_build_verdict_inputs_skips_l2_unmatched(monkeypatch):
    gold = _gold([{"id": "u-1", "query": "Obscure Thing vs Other Thing",
                   "category": "other", "region": "bahrain",
                   "expected_winner_index": 1, "forbidden_facts": []}])
    baseline = {"u-1": {"error": None, "price_pass": True, "specs_score": 1.0,
                        "winner_pass": False, "factual_pass": True}}
    # L2 has nothing matching.
    monkeypatch.setattr(se, "_fetch_l2_rows_for_category", lambda cat: [])
    monkeypatch.setattr(se, "_compute_scores_summary_offline", lambda pd: "")
    built, skipped = se.build_verdict_inputs(gold, baseline, ["u-1"])
    assert built == []
    assert skipped[0]["reason"] == "l2_unmatched"
    assert skipped[0]["matched_a"] is False


def test_build_verdict_inputs_caches_l2_per_category(monkeypatch):
    gold = _gold([
        {"id": "e-1", "query": "Apple iPhone 15 vs Samsung Galaxy S24",
         "category": "electronics", "region": "bahrain",
         "expected_winner_index": 0, "forbidden_facts": []},
        {"id": "e-2", "query": "Apple iPhone 15 vs Samsung Galaxy S24",
         "category": "electronics", "region": "bahrain",
         "expected_winner_index": 0, "forbidden_facts": []},
    ])
    baseline = {
        "e-1": {"error": None, "price_pass": True, "specs_score": 1.0,
                "winner_pass": False, "factual_pass": True},
        "e-2": {"error": None, "price_pass": True, "specs_score": 1.0,
                "winner_pass": False, "factual_pass": True},
    }
    rows = [
        {"brand": "Apple", "name": "iPhone 15", "variant": None,
         "category": "electronics", "specs": {}, "reviews": {}, "price": None},
        {"brand": "Samsung", "name": "Galaxy S24", "variant": None,
         "category": "electronics", "specs": {}, "reviews": {}, "price": None},
    ]
    calls = {"n": 0}

    def _fetch(cat):
        calls["n"] += 1
        return rows

    monkeypatch.setattr(se, "_fetch_l2_rows_for_category", _fetch)
    monkeypatch.setattr(se, "_compute_scores_summary_offline", lambda pd: "")
    built, _ = se.build_verdict_inputs(gold, baseline, ["e-1", "e-2"])
    assert len(built) == 2
    assert calls["n"] == 1  # electronics L2 fetched ONCE, reused for e-2


# ---------------------------------------------------------------------------
# L2 dump path + cross-category fallback
# ---------------------------------------------------------------------------

def test_load_l2_dump_groups_by_category(tmp_path):
    dump = tmp_path / "l2.jsonl"
    dump.write_text(
        json.dumps({"brand": "A", "name": "1", "category": "electronics",
                    "specs": {}, "reviews": {}, "price": None}) + "\n"
        + json.dumps({"brand": "B", "name": "2", "category": "grocery",
                      "specs": {}, "reviews": {}, "price": None}) + "\n",
        encoding="utf-8",
    )
    by_cat = se._load_l2_dump(dump)
    assert set(by_cat) == {"electronics", "grocery"}
    assert by_cat["electronics"][0]["brand"] == "A"


def test_fetch_l2_uses_dump_env_no_db(monkeypatch, tmp_path):
    dump = tmp_path / "l2.jsonl"
    dump.write_text(
        json.dumps({"brand": "Bionaire", "name": "air cooler",
                    "category": "electronics", "specs": {}, "reviews": {},
                    "price": None}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SHADOW_L2_DUMP", str(dump))
    # category 'other' should STILL find the electronics row via cross-cat fallback
    rows = se._fetch_l2_rows_for_category("other")
    assert any(r["name"] == "air cooler" for r in rows)


def test_fetch_l2_cross_category_fallback_prefers_requested_first(monkeypatch, tmp_path):
    dump = tmp_path / "l2.jsonl"
    dump.write_text(
        json.dumps({"brand": "X", "name": "thing", "category": "grocery",
                    "specs": {}, "reviews": {}, "price": None}) + "\n"
        + json.dumps({"brand": "Y", "name": "gadget", "category": "electronics",
                      "specs": {}, "reviews": {}, "price": None}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SHADOW_L2_DUMP", str(dump))
    rows = se._fetch_l2_rows_for_category("electronics")
    # requested category rows come first, others appended for fallback matching
    assert rows[0]["category"] == "electronics"
    assert any(r["category"] == "grocery" for r in rows)


# ---------------------------------------------------------------------------
# inputs round-trip
# ---------------------------------------------------------------------------

def test_verdict_inputs_jsonl_roundtrip(tmp_path):
    vi = se.VerdictInput(
        id="t-1", category="electronics", query="A vs B", region="bahrain",
        comparison_type="value", expected_winner_index=1, forbidden_facts=["x"],
        product_data=[{"brand": "A"}, {"brand": "B"}], scores_summary="S",
        baseline_price_pass=True, baseline_specs_score=0.5,
        baseline_winner_pass=False, baseline_factual_pass=True,
    )
    p = tmp_path / "in.jsonl"
    se.write_verdict_inputs([vi], p)
    loaded = se.read_verdict_inputs(p)
    assert len(loaded) == 1
    assert loaded[0].id == "t-1"
    assert loaded[0].forbidden_facts == ["x"]
    assert loaded[0].product_data[1]["brand"] == "B"


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def test_write_evidence_report_emits_table_and_blocks(tmp_path):
    base = se.aggregate_arm("baseline_4o", [
        se.ArmGrade(id="a", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=False, factual_pass=True, weighted_score=0.7,
                    passing=False, baseline_winner_pass=False, baseline_weighted=0.7,
                    winner_flipped_to_correct=False, winner_flipped_to_wrong=False,
                    verdict_ms=1000, cost_usd=0.0075),
    ])
    o3 = se.aggregate_arm("o3_mini", [
        se.ArmGrade(id="a", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=True, factual_pass=True, weighted_score=1.0,
                    passing=True, baseline_winner_pass=False, baseline_weighted=0.7,
                    winner_flipped_to_correct=True, winner_flipped_to_wrong=False,
                    verdict_ms=2200, cost_usd=0.0055),
    ])
    out = tmp_path / "results.md"
    se.write_evidence_report({"baseline_4o": base, "o3_mini": o3}, out,
                             coverage_note="covered 1 of 1")
    text = out.read_text(encoding="utf-8")
    assert "Lane I4 Shadow Experiment Results" in text
    assert "| baseline_4o |" in text
    assert "| o3_mini |" in text
    assert "covered 1 of 1" in text
    # delta line present in the o3 block
    assert "vs baseline_4o:" in text


def test_format_arm_report_shows_delta_vs_baseline():
    base = se.aggregate_arm("baseline_4o", [
        se.ArmGrade(id="a", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=False, factual_pass=True, weighted_score=0.7,
                    passing=False, baseline_winner_pass=False, baseline_weighted=0.7,
                    winner_flipped_to_correct=False, winner_flipped_to_wrong=False,
                    verdict_ms=1000, cost_usd=0.0075),
    ])
    arm = se.aggregate_arm("reviews_trim", [
        se.ArmGrade(id="a", category="x", price_pass=True, specs_score=1.0,
                    winner_pass=True, factual_pass=True, weighted_score=1.0,
                    passing=True, baseline_winner_pass=False, baseline_weighted=0.7,
                    winner_flipped_to_correct=True, winner_flipped_to_wrong=False,
                    verdict_ms=800, cost_usd=0.0050),
    ])
    block = se.format_arm_report(arm, baseline=base)
    assert "vs baseline_4o:" in block
    assert "latency -200ms" in block


# ---------------------------------------------------------------------------
# Arm call mechanics with a MOCKED OpenAI client (no live calls, no $)
# ---------------------------------------------------------------------------

async def _no_sleep(*_a, **_k):
    """Stub asyncio.sleep so retry/backoff tests run instantly."""
    return None


class _FakeUsage:
    def __init__(self, pt, ct):
        self.prompt_tokens = pt
        self.completion_tokens = ct
        self.total_tokens = pt + ct


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content, pt=1000, ct=300, model=""):
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(pt, ct)
        self.model = model  # served model id (resp.model)


class _FakeChatCompletions:
    def __init__(self, content_by_model, served_model_by_request=None):
        self.content_by_model = content_by_model
        # maps requested model -> served resp.model; defaults to echoing the
        # requested model (the honest case). Override to simulate a fallback.
        self.served_model_by_request = served_model_by_request or {}
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        model = kwargs["model"]
        content = self.content_by_model.get(model, '{"winner_index": 0}')
        served = self.served_model_by_request.get(model, model)
        return _FakeResponse(content, model=served)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, content_by_model, served_model_by_request=None):
        self.chat = _FakeChat(_FakeChatCompletions(content_by_model,
                                                   served_model_by_request))


def _one_input(expected=1):
    return se.VerdictInput(
        id="t-1", category="electronics", query="A vs B", region="bahrain",
        comparison_type="value", expected_winner_index=expected, forbidden_facts=[],
        product_data=[{"brand": "A", "name": "1", "specs": {}, "reviews": {}},
                      {"brand": "B", "name": "2", "specs": {}, "reviews": {}}],
        scores_summary="A leads reviews 8 to 6",
        baseline_price_pass=True, baseline_specs_score=1.0,
        baseline_winner_pass=False, baseline_factual_pass=True,
    )


@pytest.mark.asyncio
async def test_arm_baseline_4o_mocked_grades_winner_flip(monkeypatch):
    # mock the system-prompt builder so we don't import the heavy prompt stack
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    client = _FakeClient({"gpt-4o": '{"winner_index": 1, "winner_reason": "A wins by 2"}'})
    report = await se.run_arm("baseline_4o", [_one_input(expected=1)],
                              weights=_WEIGHTS, concurrency=2, client=client)
    assert report.n_covered == 1
    assert report.arm_winner_rate == 1.0
    assert report.net_winner_flips == 1
    # cost metered from fake usage (1000 pt + 300 ct at gpt-4o rate)
    assert report.mean_cost_usd == pytest.approx(se.call_cost_usd("gpt-4o", 1000, 300))
    # the call actually requested json_object on gpt-4o
    call = client.chat.completions.calls[0]
    assert call["model"] == "gpt-4o"
    assert call["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_arm_o3_mini_uses_max_completion_tokens_no_temperature(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    client = _FakeClient({"o3-mini": '{"winner_index": 0}'})
    await se.run_arm("o3_mini", [_one_input(expected=0)], weights=_WEIGHTS, client=client)
    call = client.chat.completions.calls[0]
    assert call["model"] == "o3-mini"
    # reasoning-model contract: max_completion_tokens, NO temperature/max_tokens
    assert "max_completion_tokens" in call
    assert "temperature" not in call
    assert "max_tokens" not in call


# ---------------------------------------------------------------------------
# Response-model capture (G5 evidence hygiene — proves the served model)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_json_returns_served_response_model(monkeypatch):
    # the fake echoes the requested model as resp.model -> _chat_json captures it
    client = _FakeClient({"o3-mini": '{"winner_index": 0}'})
    _v, _pt, _ct, served = await se._chat_json(client, "o3-mini", "S", "U")
    assert served == "o3-mini"


@pytest.mark.asyncio
async def test_arm_records_served_response_model(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    # served model echoes the request -> ArmGrade.response_model == 'o3-mini'
    client = _FakeClient({"o3-mini": '{"winner_index": 0}'})
    report = await se.run_arm("o3_mini", [_one_input(expected=0)],
                              weights=_WEIGHTS, client=client)
    assert report.per_query[0].response_model == "o3-mini"


@pytest.mark.asyncio
async def test_arm_records_SILENT_FALLBACK_in_response_model(monkeypatch):
    # THE failure the dispatcher flagged: request o3-mini, but the API silently
    # serves gpt-4o. response_model must record the FALLBACK so it's detectable.
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    client = _FakeClient(
        {"o3-mini": '{"winner_index": 0}'},
        served_model_by_request={"o3-mini": "gpt-4o-2024-08-06"},  # silent fallback
    )
    report = await se.run_arm("o3_mini", [_one_input(expected=0)],
                              weights=_WEIGHTS, client=client)
    g = report.per_query[0]
    assert g.response_model == "gpt-4o-2024-08-06"  # NOT o3-mini -> caught
    assert g.response_model != "o3-mini"


@pytest.mark.asyncio
async def test_multiagent_response_model_records_all_legs(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    client = _FakeClient({
        "gpt-4o-mini": "analyst note",
        "gpt-4o": '{"winner_index": 1}',
    })
    report = await se.run_arm("multiagent", [_one_input(expected=1)],
                              weights=_WEIGHTS, client=client)
    rm = report.per_query[0].response_model
    # both the editor (4o) and analysts (mini) served models recorded
    assert "gpt-4o" in rm and "gpt-4o-mini" in rm


@pytest.mark.asyncio
async def test_arm_multiagent_runs_four_calls_and_blends_cost(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    # 3 mini analysts + 1 4o editor
    client = _FakeClient({
        "gpt-4o-mini": "spec/price/review note",
        "gpt-4o": '{"winner_index": 1, "winner_reason": "synthesis"}',
    })
    report = await se.run_arm("multiagent", [_one_input(expected=1)],
                              weights=_WEIGHTS, client=client)
    # 4 calls total: 3 analysts (mini) + 1 editor (4o)
    models = [c["model"] for c in client.chat.completions.calls]
    assert models.count("gpt-4o-mini") == 3
    assert models.count("gpt-4o") == 1
    assert report.arm_winner_rate == 1.0
    # blended cost = 3x mini(1000/300) + 1x 4o(1000/300)
    expected_cost = 3 * se.call_cost_usd("gpt-4o-mini", 1000, 300) \
        + se.call_cost_usd("gpt-4o", 1000, 300)
    assert report.mean_cost_usd == pytest.approx(expected_cost)
    # the cost-split helper must NOT leak into the graded verdict prose
    assert "_shadow_cost_split" not in str(report.per_query[0].__dict__)


@pytest.mark.asyncio
async def test_create_with_retry_backs_off_then_succeeds(monkeypatch):
    # first 2 calls raise 429, 3rd succeeds — must NOT surface as an error
    monkeypatch.setattr(se.asyncio, "sleep", _no_sleep)
    attempts = {"n": 0}

    class _Flaky:
        async def create(self, **kwargs):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("Error code: 429 - rate limit reached")
            return _FakeResponse('{"winner_index": 0}')

    client = _FakeClient({})
    client.chat.completions = _Flaky()
    resp = await se._create_with_retry(client, model="gpt-4o", messages=[])
    assert attempts["n"] == 3
    assert resp.choices[0].message.content == '{"winner_index": 0}'


@pytest.mark.asyncio
async def test_create_with_retry_non_rate_error_raises_immediately(monkeypatch):
    monkeypatch.setattr(se.asyncio, "sleep", _no_sleep)
    attempts = {"n": 0}

    class _Boom:
        async def create(self, **kwargs):
            attempts["n"] += 1
            raise ValueError("bad request 400")

    client = _FakeClient({})
    client.chat.completions = _Boom()
    with pytest.raises(ValueError):
        await se._create_with_retry(client, model="gpt-4o", messages=[])
    assert attempts["n"] == 1  # no retry on a non-rate error


@pytest.mark.asyncio
async def test_create_with_retry_gives_up_after_max(monkeypatch):
    monkeypatch.setattr(se.asyncio, "sleep", _no_sleep)
    attempts = {"n": 0}

    class _AlwaysRate:
        async def create(self, **kwargs):
            attempts["n"] += 1
            raise RuntimeError("429 ratelimit")

    client = _FakeClient({})
    client.chat.completions = _AlwaysRate()
    with pytest.raises(RuntimeError):
        await se._create_with_retry(client, model="gpt-4o", messages=[])
    assert attempts["n"] == se._MAX_RETRIES


@pytest.mark.asyncio
async def test_arm_error_is_captured_not_raised(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")

    class _BoomCompletions:
        async def create(self, **kwargs):
            raise RuntimeError("openai 500")

    client = _FakeClient({})
    client.chat.completions = _BoomCompletions()
    report = await se.run_arm("baseline_4o", [_one_input()],
                              weights=_WEIGHTS, client=client)
    assert report.n_errors == 1
    assert report.per_query[0].error is not None
    # errored row contributes zero cost + is excluded from latency mean
    assert report.total_cost_usd == 0.0


@pytest.mark.asyncio
async def test_arm_reviews_trim_truncates_review_payload(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    vi = _one_input(expected=0)
    # give product 0 a large reviews blob so the trim has something to cut
    vi.product_data[0]["reviews"] = {"consensus": "x" * 5000}
    client = _FakeClient({"gpt-4o": '{"winner_index": 0}'})
    await se.run_arm("reviews_trim", [vi], weights=_WEIGHTS, client=client)
    call = client.chat.completions.calls[0]
    # the trimmed user message must be shorter than an untrimmed serialization
    user_msg = call["messages"][1]["content"]
    assert "x" * 2500 not in user_msg or len(user_msg) < 6000
    assert call["max_tokens"] == 600


# ---------------------------------------------------------------------------
# Prompt-arm (directive 2) — exemplar-FILE swap via the real prod prompt path
# ---------------------------------------------------------------------------

def test_swapped_exemplar_file_noop_when_path_none():
    # path None -> context manager is a pure no-op (reads on-disk file)
    with se._swapped_exemplar_file(None):
        pass  # must not raise, must not touch the loader


def test_swapped_exemplar_file_off_env_is_noop(monkeypatch):
    monkeypatch.setenv("SHADOW_EXEMPLAR_OFF", "1")
    # even with a path, OFF forces the on-disk file (no swap)
    with se._swapped_exemplar_file("/some/path.json"):
        pass  # no-op, no raise


def test_swapped_exemplar_file_swaps_and_restores(monkeypatch, tmp_path):
    # the context manager must point the loader at the given file inside the
    # block and restore the original path + reset cache on exit
    from app.services import verdict_exemplar_loader as vel
    original = vel._EXEMPLAR_FILE
    swap = tmp_path / "i1_exemplars.json"
    swap.write_text("{}", encoding="utf-8")
    monkeypatch.delenv("SHADOW_EXEMPLAR_OFF", raising=False)
    with se._swapped_exemplar_file(str(swap)):
        assert str(vel._EXEMPLAR_FILE) == str(swap)
    # restored on exit
    assert vel._EXEMPLAR_FILE == original


@pytest.mark.asyncio
async def test_arm_prompt_exemplars_uses_swapped_file_via_prod_path(monkeypatch, tmp_path):
    # I1's filled exemplar file (a category with a recognizable anti-pattern)
    # must reach the system prompt through the REAL build_verdict_prompt path.
    i1_file = tmp_path / "verdict_exemplars.json"
    i1_file.write_text(json.dumps({
        "electronics": {
            "exemplars": [],
            # loader's _render_anti_pattern needs name + rule
            "anti_patterns": [
                {"name": "SHADOW_TEST_AP", "rule": "uniquely-detectable marker"}
            ],
        }
    }), encoding="utf-8")
    monkeypatch.setenv("SHADOW_EXEMPLAR_FILE", str(i1_file))
    monkeypatch.delenv("SHADOW_EXEMPLAR_OFF", raising=False)
    client = _FakeClient({"gpt-4o": '{"winner_index": 1, "winner_reason": "x"}'})
    report = await se.run_arm("prompt_exemplars", [_one_input(expected=1)],
                              weights=_WEIGHTS, client=client)
    sys_msg = client.chat.completions.calls[0]["messages"][0]["content"]
    # the swapped file's anti-pattern must have rendered into the prod prompt
    assert "SHADOW_TEST_AP" in sys_msg or "uniquely-detectable marker" in sys_msg
    assert report.arm_winner_rate == 1.0


@pytest.mark.asyncio
async def test_arm_baseline_uses_ondisk_exemplar_file_not_swapped(monkeypatch, tmp_path):
    # baseline_4o must NOT pick up SHADOW_EXEMPLAR_FILE — it reads whatever is
    # on disk (the prod default). With a marker file set, baseline's prompt must
    # NOT contain the marker (only the prompt-arm swaps).
    i1_file = tmp_path / "verdict_exemplars.json"
    i1_file.write_text(json.dumps({
        "electronics": {"exemplars": [],
                        "anti_patterns": [{"name": "ONLY_IN_SWAP_MARKER"}]}
    }), encoding="utf-8")
    monkeypatch.setenv("SHADOW_EXEMPLAR_FILE", str(i1_file))
    client = _FakeClient({"gpt-4o": '{"winner_index": 0}'})
    await se.run_arm("baseline_4o", [_one_input(expected=0)],
                     weights=_WEIGHTS, client=client)
    sys_msg = client.chat.completions.calls[0]["messages"][0]["content"]
    assert "ONLY_IN_SWAP_MARKER" not in sys_msg


def test_prompt_exemplars_registered_in_arms():
    assert "prompt_exemplars" in se.ARMS


@pytest.mark.asyncio
async def test_prompt_exemplars_t0_uses_temperature_zero_and_swaps_file(monkeypatch, tmp_path):
    # G3 pre-read arm: prompt-arm at T=0, exemplar file swapped via prod path
    i1_file = tmp_path / "verdict_exemplars.json"
    i1_file.write_text(json.dumps({
        "electronics": {"exemplars": [],
                        "anti_patterns": [{"name": "T0_SWAP_AP", "rule": "marker rule"}]}
    }), encoding="utf-8")
    monkeypatch.setenv("SHADOW_EXEMPLAR_FILE", str(i1_file))
    monkeypatch.delenv("SHADOW_EXEMPLAR_OFF", raising=False)
    client = _FakeClient({"gpt-4o": '{"winner_index": 1}'})
    await se.run_arm("prompt_exemplars_t0", [_one_input(expected=1)],
                     weights=_WEIGHTS, client=client)
    call = client.chat.completions.calls[0]
    assert call["temperature"] == 0.0  # T=0 prod parity
    assert "T0_SWAP_AP" in call["messages"][0]["content"] or \
           "marker rule" in call["messages"][0]["content"]


def test_g3_preread_arms_registered():
    # the G3 pre-read pair: temp0 (baseline@T=0) + prompt_exemplars_t0 (exemplars@T=0)
    assert "temp0" in se.ARMS
    assert "prompt_exemplars_t0" in se.ARMS


# ---------------------------------------------------------------------------
# Variance-reduction arms: T=0 + best-of-3 majority
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_arm_temp0_sets_temperature_zero(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    client = _FakeClient({"gpt-4o": '{"winner_index": 1}'})
    await se.run_arm("temp0", [_one_input(expected=1)], weights=_WEIGHTS, client=client)
    call = client.chat.completions.calls[0]
    assert call["model"] == "gpt-4o"
    assert call["temperature"] == 0.0


@pytest.mark.asyncio
async def test_arm_best_of_3_runs_three_calls_and_majority_votes(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")

    # 3 samples: winner 1, 1, 0 -> majority = 1
    seq = ['{"winner_index": 1, "winner_reason": "a"}',
           '{"winner_index": 1, "winner_reason": "b"}',
           '{"winner_index": 0, "winner_reason": "c"}']
    idx = {"i": 0}

    class _Seq:
        async def create(self, **kwargs):
            content = seq[idx["i"] % len(seq)]
            idx["i"] += 1
            return _FakeResponse(content)

    client = _FakeClient({})
    client.chat.completions = _Seq()
    report = await se.run_arm("best_of_3", [_one_input(expected=1)],
                              weights=_WEIGHTS, client=client)
    assert idx["i"] == 3  # exactly 3 verdict calls
    assert report.arm_winner_rate == 1.0  # majority winner=1 == gold=1
    # cost = 3x a single call's metered tokens
    assert report.mean_cost_usd == pytest.approx(3 * se.call_cost_usd("gpt-4o", 1000, 300))


@pytest.mark.asyncio
async def test_arm_best_of_3_majority_picks_wrong_when_two_agree_wrong(monkeypatch):
    monkeypatch.setattr(se, "_build_verdict_system_prompt", lambda vi: "SYS")
    # 0,0,1 -> majority 0; gold expects 1 -> winner wrong
    seq = ['{"winner_index": 0}', '{"winner_index": 0}', '{"winner_index": 1}']
    idx = {"i": 0}

    class _Seq:
        async def create(self, **kwargs):
            content = seq[idx["i"] % len(seq)]
            idx["i"] += 1
            return _FakeResponse(content)

    client = _FakeClient({})
    client.chat.completions = _Seq()
    report = await se.run_arm("best_of_3", [_one_input(expected=1)],
                              weights=_WEIGHTS, client=client)
    assert report.arm_winner_rate == 0.0


def test_variance_arms_registered():
    assert "temp0" in se.ARMS
    assert "best_of_3" in se.ARMS


# ---------------------------------------------------------------------------
# Structural / variance split reporting
# ---------------------------------------------------------------------------

def test_structural_variance_id_sets_are_disjoint_and_sized():
    assert len(se.STRUCTURAL_IDS) == 24
    assert len(se.VARIANCE_IDS) == 19
    assert len(se.SPLIT_IDS) == 2
    assert not (se.STRUCTURAL_IDS & se.VARIANCE_IDS)
    assert not (se.STRUCTURAL_IDS & se.SPLIT_IDS)
    assert not (se.VARIANCE_IDS & se.SPLIT_IDS)


def test_split_winner_rate_buckets_correctly():
    grades = [
        se.ArmGrade(id="elec-012", category="electronics", price_pass=True,
                    specs_score=1.0, winner_pass=False, factual_pass=True,
                    weighted_score=0.7, passing=False, baseline_winner_pass=False,
                    baseline_weighted=0.7, winner_flipped_to_correct=False,
                    winner_flipped_to_wrong=False, verdict_ms=1000, cost_usd=0.01),
        se.ArmGrade(id="hair-001", category="haircare", price_pass=True,
                    specs_score=1.0, winner_pass=True, factual_pass=True,
                    weighted_score=1.0, passing=True, baseline_winner_pass=False,
                    baseline_weighted=0.7, winner_flipped_to_correct=True,
                    winner_flipped_to_wrong=False, verdict_ms=1000, cost_usd=0.01),
        se.ArmGrade(id="groc-002", category="grocery", price_pass=True,
                    specs_score=1.0, winner_pass=True, factual_pass=True,
                    weighted_score=1.0, passing=True, baseline_winner_pass=False,
                    baseline_weighted=0.7, winner_flipped_to_correct=True,
                    winner_flipped_to_wrong=False, verdict_ms=1000, cost_usd=0.01),
    ]
    split = se.split_winner_rate(grades)
    assert split["structural"]["n"] == 1 and split["structural"]["winner_rate"] == 0.0
    assert split["variance"]["n"] == 1 and split["variance"]["winner_rate"] == 1.0
    assert split["split"]["n"] == 1 and split["split"]["winner_rate"] == 1.0

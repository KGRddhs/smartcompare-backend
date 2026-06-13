"""Tests for scripts/eval_runner.py — Bundle B Phase B.6 eval-loop runner.

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4 (F4.1–F4.4)

The runner hits the deployed comparison endpoint once per gold-truth query
(?nocache=true), records the response + wall time, then grades it along 4
axes. ALL tests here use a mocked httpx transport (httpx.MockTransport) — no
live network, no cost. Three single-query LIVE probes against prod are run
manually by the lane agent (announced to dispatcher), never in this suite.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from pathlib import Path

import httpx
import pytest

from scripts import eval_runner


REPO_ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = REPO_ROOT / "data" / "validation_gold_truth.json"


# ---------------------------------------------------------------------------
# Fixtures — a minimal but realistic /text/compare response body.
# ---------------------------------------------------------------------------

def _make_response_body(
    *,
    winner_idx: int = 0,
    p0_price: float = 320.0,
    p1_price: float = 300.0,
    p0_specs: dict | None = None,
    p1_specs: dict | None = None,
    verdict_text: str = "The iPhone 15 wins on camera quality and ecosystem.",
) -> dict:
    """Shape mirrors response_builder.build_comparison_response() — the
    fields the grader reads: scoring_v2.overall_score.winner_idx,
    overview.products[i].price.amount, specs.products[i].specs, and the
    verdict text fields."""
    return {
        "success": True,
        "overview": {
            "winner": {
                "product_index": winner_idx,
                "declaration": verdict_text,
                "reason": "Better camera, stronger resale.",
                "key_tradeoff": "Higher price for ecosystem lock-in.",
            },
            "products": [
                {
                    "name": "iPhone 15",
                    "price": {"amount": p0_price, "currency": "BHD"},
                },
                {
                    "name": "Galaxy S24",
                    "price": {"amount": p1_price, "currency": "BHD"},
                },
            ],
        },
        "specs": {
            "products": [
                {"name": "iPhone 15", "specs": p0_specs or {"storage": "128GB", "os": "iOS"}},
                {"name": "Galaxy S24", "specs": p1_specs or {"storage": "128GB", "os": "Android"}},
            ],
        },
        "reviews": {"products": [{"review_summary": {}}, {"review_summary": {}}]},
        "scoring_v2": {
            "overall_score": {"product_a": 78, "product_b": 71, "winner_idx": winner_idx},
            "factual_verdict": {"line1": "iPhone 15 leads.", "line2": "Galaxy S24 wins on price."},
        },
    }


def _mock_transport(body: dict, status: int = 200):
    """Build an httpx.MockTransport that returns `body` for any request."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# load_gold_truth
# ---------------------------------------------------------------------------

def test_load_gold_truth_returns_metadata_and_queries():
    gold = eval_runner.load_gold_truth(GOLD_PATH)
    assert "_metadata" in gold
    assert isinstance(gold["queries"], list)
    # Count-agnostic: the gold set grows (50 -> 200 in S1); shape, not size.
    assert len(gold["queries"]) >= 50


def test_load_gold_truth_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        eval_runner.load_gold_truth(REPO_ROOT / "data" / "does_not_exist.json")


# ---------------------------------------------------------------------------
# UTF-8 read-path integrity (Windows cp1252 codec-trap regression)
# ---------------------------------------------------------------------------
#
# A gold file is UTF-8. If any read in the measurement layer decodes it via
# the platform default (cp1252 on Windows), a forbidden-fact like "Mövenpick
# robusta blend" loads as "MÃ¶venpick robusta blend" and then never substring-
# matches a correct API response containing real "Mövenpick" - silently
# passing a factual violation. These tests pin the read->grade path to UTF-8.

def _write_utf8_gold(query_record: dict) -> str:
    """Write a one-query gold file as UTF-8 (explicit), return its path."""
    doc = {
        "_metadata": {
            "queries": 1,
            "axis_weights": {
                "price_accuracy": 0.25, "specs_correctness": 0.25,
                "winner_correctness": 0.30, "factual_claim_integrity": 0.20,
            },
        },
        "queries": [query_record],
    }
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(doc, fh, ensure_ascii=False)  # keep the ö as a real UTF-8 byte
    fh.close()
    return fh.name


def test_forbidden_fact_with_non_ascii_survives_read_then_grades():
    # Forbidden fact carries the umlaut; the response carries the SAME real
    # umlaut. A UTF-8-clean read path detects the forbidden fact (grade False).
    record = {
        "id": "groc-codec", "query": "Nescafe Gold vs Mövenpick Gold",
        "category": "grocery", "region": "bahrain",
        "expected_prices": {}, "expected_specs": {},
        "expected_winner_index": None,
        "forbidden_facts": ["Mövenpick robusta blend"],
        "max_wall_seconds": 30.0,
    }
    path = _write_utf8_gold(record)
    try:
        gold = eval_runner.load_gold_truth(path)
        loaded_fact = gold["queries"][0]["forbidden_facts"][0]
        # The byte 0xc3 0xb6 round-trips to a single ö (U+00F6), not "Ã¶".
        assert loaded_fact == "Mövenpick robusta blend"
        assert "ö" in loaded_fact and "Ã" not in loaded_fact
        # And it actually grades: a response asserting the forbidden claim fails.
        response_text = "This blend is the Mövenpick robusta blend, full-bodied."
        assert eval_runner.grade_factual(response_text, gold["queries"][0]["forbidden_facts"]) is False
        # Control: a clean response (no forbidden claim) passes.
        assert eval_runner.grade_factual("A smooth arabica roast.", gold["queries"][0]["forbidden_facts"]) is True
    finally:
        os.unlink(path)


def test_query_string_with_non_ascii_survives_read():
    # The query field is what we send to the API; mojibake here degrades
    # extraction. Confirm it round-trips through load_gold_truth intact.
    record = {
        "id": "groc-codec2", "query": "Nescafe Gold vs Mövenpick Gold instant coffee",
        "category": "grocery", "region": "bahrain",
        "expected_prices": {}, "expected_specs": {},
        "expected_winner_index": None, "forbidden_facts": [], "max_wall_seconds": 30.0,
    }
    path = _write_utf8_gold(record)
    try:
        gold = eval_runner.load_gold_truth(path)
        assert gold["queries"][0]["query"] == "Nescafe Gold vs Mövenpick Gold instant coffee"
        assert "Ã" not in gold["queries"][0]["query"]
    finally:
        os.unlink(path)


def test_real_gold_file_forbidden_facts_have_no_mojibake_markers():
    # Guard the actual gold file: no forbidden_fact / query / note carries a
    # double-encoded marker that would mean a producer wrote mojibake.
    gold = eval_runner.load_gold_truth(GOLD_PATH)
    markers = ("Ã", "â‚¬", "�")  # cp1252-of-utf8 tells + replacement char
    for q in gold["queries"]:
        blob = json.dumps(q, ensure_ascii=False)
        for m in markers:
            assert m not in blob, f"{q['id']} carries mojibake marker {m!r}"


# ---------------------------------------------------------------------------
# run_query (async, single query, mocked transport)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_query_hits_compare_endpoint_with_nocache():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=_make_response_body())

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        record = {"id": "elec-001", "query": "iPhone 15 vs Galaxy S24",
                  "region": "bahrain", "max_wall_seconds": 25.0}
        result = await eval_runner.run_query(client, record)

    assert "/api/v1/text/compare" in captured["url"]
    assert captured["params"].get("nocache") == "true"
    assert captured["params"].get("q") == "iPhone 15 vs Galaxy S24"
    assert captured["params"].get("region") == "bahrain"
    assert result.http_status == 200
    assert result.error is None
    assert result.response is not None
    assert result.wall_ms >= 0


@pytest.mark.asyncio
async def test_run_query_records_http_error():
    transport = _mock_transport({"success": False}, status=500)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        record = {"id": "elec-001", "query": "x", "region": "bahrain", "max_wall_seconds": 25.0}
        result = await eval_runner.run_query(client, record)
    assert result.http_status == 500
    assert result.error is not None
    assert "500" in result.error


@pytest.mark.asyncio
async def test_run_query_records_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        record = {"id": "elec-001", "query": "x", "region": "bahrain", "max_wall_seconds": 25.0}
        result = await eval_runner.run_query(client, record)
    assert result.error is not None
    assert result.response is None


# ---------------------------------------------------------------------------
# run_eval (orchestrator, concurrency, mocked transport)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_eval_grades_all_queries():
    body = _make_response_body(winner_idx=0)
    transport = _mock_transport(body)
    queries = [
        {"id": "elec-001", "query": "iPhone 15 vs Galaxy S24", "category": "electronics",
         "region": "bahrain", "expected_prices": {"product_0": {"min": 290, "max": 400},
         "product_1": {"min": 260, "max": 360}},
         "expected_specs": {"product_0": {"storage": "128GB"}, "product_1": {"storage": "128GB"}},
         "expected_winner_index": 0, "forbidden_facts": ["8K video recording"],
         "max_wall_seconds": 25.0},
    ]
    report = await eval_runner.run_eval(queries, base_url="http://test",
                                        transport=transport, concurrency=3)
    assert report.queries_total == 1
    assert len(report.per_query) == 1
    pq = report.per_query[0]
    assert pq.id == "elec-001"
    # winner_idx 0 == expected 0; prices in range; specs match; no forbidden fact
    assert pq.winner_pass is True
    assert pq.price_pass is True
    assert pq.specs_score == 1.0
    assert pq.factual_pass is True
    assert pq.weighted_score == pytest.approx(1.0)
    assert pq.passing is True


@pytest.mark.asyncio
async def test_run_eval_respects_concurrency_limit():
    """Concurrency cap means no more than N in-flight requests at once."""
    import asyncio

    in_flight = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, max_seen
        async with lock:
            in_flight += 1
            max_seen = max(max_seen, in_flight)
        await asyncio.sleep(0.02)
        async with lock:
            in_flight -= 1
        return httpx.Response(200, json=_make_response_body())

    # MockTransport supports async handlers via AsyncClient.
    transport = httpx.MockTransport(slow_handler)
    queries = [
        {"id": f"q-{i}", "query": "x", "category": "electronics", "region": "bahrain",
         "expected_prices": {}, "expected_specs": {}, "expected_winner_index": None,
         "forbidden_facts": [], "max_wall_seconds": 25.0}
        for i in range(9)
    ]
    report = await eval_runner.run_eval(queries, base_url="http://test",
                                        transport=transport, concurrency=3)
    assert report.queries_total == 9
    assert max_seen <= 3


@pytest.mark.asyncio
async def test_run_eval_aggregates_pass_rate_and_axis_averages():
    # Two queries: one fully passing, one with wrong winner.
    pass_body = _make_response_body(winner_idx=0)
    queries = [
        {"id": "q-pass", "query": "x", "category": "electronics", "region": "bahrain",
         "expected_prices": {"product_0": {"min": 290, "max": 400}, "product_1": {"min": 260, "max": 360}},
         "expected_specs": {"product_0": {"storage": "128GB"}, "product_1": {"storage": "128GB"}},
         "expected_winner_index": 0, "forbidden_facts": [], "max_wall_seconds": 25.0},
        {"id": "q-fail-winner", "query": "y", "category": "electronics", "region": "bahrain",
         "expected_prices": {"product_0": {"min": 290, "max": 400}, "product_1": {"min": 260, "max": 360}},
         "expected_specs": {"product_0": {"storage": "128GB"}, "product_1": {"storage": "128GB"}},
         "expected_winner_index": 1, "forbidden_facts": [], "max_wall_seconds": 25.0},
    ]
    transport = _mock_transport(pass_body)
    report = await eval_runner.run_eval(queries, base_url="http://test",
                                        transport=transport, concurrency=3)
    assert report.queries_total == 2
    # winner axis: one hit, one miss → 0.5 average
    assert report.axis_avg_winner == pytest.approx(0.5)
    # price/specs/factual all pass on both
    assert report.axis_avg_price == pytest.approx(1.0)
    assert report.axis_avg_specs == pytest.approx(1.0)
    assert report.axis_avg_factual == pytest.approx(1.0)
    assert 0.0 <= report.pass_rate <= 1.0


@pytest.mark.asyncio
async def test_run_eval_computes_wall_percentiles():
    transport = _mock_transport(_make_response_body())
    queries = [
        {"id": f"q-{i}", "query": "x", "category": "electronics", "region": "bahrain",
         "expected_prices": {}, "expected_specs": {}, "expected_winner_index": None,
         "forbidden_facts": [], "max_wall_seconds": 25.0}
        for i in range(5)
    ]
    report = await eval_runner.run_eval(queries, base_url="http://test",
                                        transport=transport, concurrency=3)
    assert report.wall_p50_ms is not None
    assert report.wall_p95_ms is not None
    assert report.wall_p95_ms >= report.wall_p50_ms


# ---------------------------------------------------------------------------
# S2 I3.6 — missing-dimension coverage metric in eval metadata
# ---------------------------------------------------------------------------

def _body_with_missing_cells(count: int, *, winner_idx: int = 0) -> dict:
    """Response body carrying metadata.missing_dim_cells (the I3.6 KPI dial)."""
    body = _make_response_body(winner_idx=winner_idx)
    body["metadata"] = {
        "missing_dim_cells": {"count": count, "total": 12,
                              "fraction": round(count / 12, 4)},
    }
    return body


def test_extract_missing_dim_cells_reads_count():
    body = _body_with_missing_cells(3)
    assert eval_runner.extract_missing_dim_cells(body) == 3


def test_extract_missing_dim_cells_absent_returns_zero():
    """A body without the metric (older backend / error row) → 0, no crash."""
    assert eval_runner.extract_missing_dim_cells(_make_response_body()) == 0
    assert eval_runner.extract_missing_dim_cells({}) == 0
    assert eval_runner.extract_missing_dim_cells({"metadata": {}}) == 0


def test_grade_run_result_captures_missing_dim_cells():
    body = _body_with_missing_cells(4)
    run_result = eval_runner.QueryRunResult(
        id="q1", query="x", category="electronics",
        http_status=200, wall_ms=1000, error=None, response=body,
    )
    record = {"id": "q1", "expected_prices": {}, "expected_specs": {},
              "expected_winner_index": None, "forbidden_facts": []}
    graded = eval_runner.grade_run_result(run_result, record)
    assert graded.missing_dim_cells == 4


def test_error_row_has_zero_missing_dim_cells():
    """An errored query (no response body) reports 0 missing cells — the
    metric measures DATA gaps in successful runs, not error starvation."""
    run_result = eval_runner.QueryRunResult(
        id="q-err", query="x", category="electronics",
        http_status=400, wall_ms=30000, error="http_400", response=None,
    )
    record = {"id": "q-err", "expected_prices": {}, "expected_specs": {},
              "expected_winner_index": None, "forbidden_facts": []}
    graded = eval_runner.grade_run_result(run_result, record)
    assert graded.missing_dim_cells == 0


@pytest.mark.asyncio
async def test_run_eval_aggregates_missing_dim_cells():
    """EvalReport surfaces the run-level total + mean missing-dim cells so
    persist_eval_run can write them into the eval_runs metadata jsonb."""
    transport = _mock_transport(_body_with_missing_cells(2))
    queries = [
        {"id": f"q-{i}", "query": "x", "category": "electronics", "region": "bahrain",
         "expected_prices": {}, "expected_specs": {}, "expected_winner_index": None,
         "forbidden_facts": [], "max_wall_seconds": 25.0}
        for i in range(4)
    ]
    report = await eval_runner.run_eval(queries, base_url="http://test",
                                        transport=transport, concurrency=2)
    # 4 queries × 2 cells = 8 total; mean 2.0.
    assert report.missing_dim_cells_total == 8
    assert report.missing_dim_cells_mean == pytest.approx(2.0)


def test_aggregate_missing_dim_cells_empty_run():
    """Aggregating an empty graded list → 0 total, 0.0 mean (no ZeroDiv)."""
    report = eval_runner.aggregate([])
    assert report.missing_dim_cells_total == 0
    assert report.missing_dim_cells_mean == 0.0


# ---------------------------------------------------------------------------
# S3 L4.1 — estimate-share metric (price source_method == "estimated")
#
# The North-star KPI for "no false estimates": of the price fields the engine
# actually PRODUCED (have a source_method), what fraction fell to the Tier-3
# GPT `estimated` path vs real data (local_bhd / converted_usd / page_scrape /
# firecrawl / scrapedo_rendered / ...). A product with NO price at all is in
# neither bucket — the metric measures the honesty of produced prices, not
# coverage. Mirrors the I3.6 missing_dim_cells thread end-to-end.
# ---------------------------------------------------------------------------

def _body_with_price_methods(method_p0, method_p1, *, winner_idx: int = 0) -> dict:
    """Response body whose overview.products[i].price carries a source_method.

    Pass a method string ('estimated', 'local_bhd', ...) to set it, or None to
    drop the whole price object for that product (simulating no price found)."""
    body = _make_response_body(winner_idx=winner_idx)
    products = body["overview"]["products"]
    for idx, method in enumerate((method_p0, method_p1)):
        if method is None:
            # No price produced for this product at all.
            products[idx]["price"] = None
        else:
            products[idx]["price"] = {
                "amount": 300.0, "currency": "BHD", "source_method": method,
            }
    return body


def test_extract_price_source_method_reads_enum():
    body = _body_with_price_methods("estimated", "local_bhd")
    assert eval_runner.extract_price_source_method(body, 0) == "estimated"
    assert eval_runner.extract_price_source_method(body, 1) == "local_bhd"


def test_extract_price_source_method_none_when_no_price():
    """No price object (or no source_method key) → None, no crash."""
    body = _body_with_price_methods(None, "local_bhd")
    assert eval_runner.extract_price_source_method(body, 0) is None
    # Out-of-range index is safe.
    assert eval_runner.extract_price_source_method(body, 5) is None
    # Price object without a source_method key → None.
    body2 = _make_response_body()  # price = {amount, currency}, no source_method
    assert eval_runner.extract_price_source_method(body2, 0) is None
    # Empty/garbage bodies don't raise.
    assert eval_runner.extract_price_source_method({}, 0) is None


def test_extract_price_source_method_empty_string_is_none():
    """An empty/whitespace source_method is phantom provenance → None, so it
    does not dilute the priced denominator (defensive: backend emits a real
    enum, but a blank must not count as a produced price)."""
    body = _make_response_body()
    body["overview"]["products"][0]["price"] = {"amount": 300.0, "source_method": ""}
    body["overview"]["products"][1]["price"] = {"amount": 300.0, "source_method": "   "}
    assert eval_runner.extract_price_source_method(body, 0) is None
    assert eval_runner.extract_price_source_method(body, 1) is None
    # Both phantom → (0, 0), not (0, 2).
    assert eval_runner.count_price_source_cells(body) == (0, 0)


def test_count_price_cells_all_estimated():
    """Both products priced via the Tier-3 estimate → 2 estimated / 2 priced."""
    body = _body_with_price_methods("estimated", "estimated")
    estimated, priced = eval_runner.count_price_source_cells(body)
    assert (estimated, priced) == (2, 2)


def test_count_price_cells_mixed():
    """One real, one estimate → 1 estimated / 2 priced."""
    body = _body_with_price_methods("local_bhd", "estimated")
    estimated, priced = eval_runner.count_price_source_cells(body)
    assert (estimated, priced) == (1, 2)


def test_count_price_cells_all_real():
    """Both real (one local, one converted) → 0 estimated / 2 priced."""
    body = _body_with_price_methods("local_bhd", "converted_usd")
    estimated, priced = eval_runner.count_price_source_cells(body)
    assert (estimated, priced) == (0, 2)


def test_count_price_cells_one_missing_price():
    """A product with no price is excluded from BOTH buckets — the surviving
    estimate is 1/1, not 1/2 (honesty of produced prices, not coverage)."""
    body = _body_with_price_methods("estimated", None)
    estimated, priced = eval_runner.count_price_source_cells(body)
    assert (estimated, priced) == (1, 1)


def test_count_price_cells_no_prices_at_all():
    """No priced products → (0, 0); the run-level share guards the ZeroDiv."""
    body = _body_with_price_methods(None, None)
    assert eval_runner.count_price_source_cells(body) == (0, 0)


def test_grade_run_result_captures_price_source_cells():
    body = _body_with_price_methods("estimated", "local_bhd")
    run_result = eval_runner.QueryRunResult(
        id="q1", query="x", category="electronics",
        http_status=200, wall_ms=1000, error=None, response=body,
    )
    record = {"id": "q1", "expected_prices": {}, "expected_specs": {},
              "expected_winner_index": None, "forbidden_facts": []}
    graded = eval_runner.grade_run_result(run_result, record)
    assert graded.estimated_price_cells == 1
    assert graded.priced_cells == 2


def test_error_row_has_zero_price_source_cells():
    """An errored query (no response body) reports 0/0 — no produced prices."""
    run_result = eval_runner.QueryRunResult(
        id="q-err", query="x", category="electronics",
        http_status=400, wall_ms=30000, error="http_400", response=None,
    )
    record = {"id": "q-err", "expected_prices": {}, "expected_specs": {},
              "expected_winner_index": None, "forbidden_facts": []}
    graded = eval_runner.grade_run_result(run_result, record)
    assert graded.estimated_price_cells == 0
    assert graded.priced_cells == 0


@pytest.mark.asyncio
async def test_run_eval_aggregates_estimate_share():
    """EvalReport surfaces run-level estimated/priced totals + the share ratio
    so persist_eval_run writes them into the eval_runs metadata jsonb."""
    # Every query: 1 estimated / 2 priced → run share = 0.5.
    transport = _mock_transport(_body_with_price_methods("estimated", "local_bhd"))
    queries = [
        {"id": f"q-{i}", "query": "x", "category": "electronics", "region": "bahrain",
         "expected_prices": {}, "expected_specs": {}, "expected_winner_index": None,
         "forbidden_facts": [], "max_wall_seconds": 25.0}
        for i in range(4)
    ]
    report = await eval_runner.run_eval(queries, base_url="http://test",
                                        transport=transport, concurrency=2)
    # 4 queries × (1 estimated, 2 priced) → 4 estimated / 8 priced.
    assert report.estimated_price_cells_total == 4
    assert report.priced_cells_total == 8
    assert report.estimate_share == pytest.approx(0.5)


def test_aggregate_estimate_share_empty_run():
    """Empty graded list → 0/0 totals, 0.0 share (no ZeroDiv)."""
    report = eval_runner.aggregate([])
    assert report.estimated_price_cells_total == 0
    assert report.priced_cells_total == 0
    assert report.estimate_share == 0.0


def test_aggregate_estimate_share_all_errors_no_zerodiv():
    """A run where every query errored → no priced cells → share 0.0, no crash."""
    graded = [
        eval_runner.GradedQuery(
            id=f"q-{i}", category="electronics", wall_ms=30000, http_status=400,
            error="http_400", price_pass=False, specs_score=0.0, winner_pass=False,
            factual_pass=False, weighted_score=0.0, passing=False, wall_over_cap=True,
        )
        for i in range(3)
    ]
    report = eval_runner.aggregate(graded)
    assert report.priced_cells_total == 0
    assert report.estimate_share == 0.0


def test_format_report_shows_estimate_share():
    """The CLI report surfaces the estimate-share line (KPI visibility)."""
    transport_body = _body_with_price_methods("estimated", "local_bhd")
    graded = eval_runner.grade_run_result(
        eval_runner.QueryRunResult(
            id="q1", query="x", category="electronics", http_status=200,
            wall_ms=1000, error=None, response=transport_body,
        ),
        {"id": "q1", "expected_prices": {}, "expected_specs": {},
         "expected_winner_index": None, "forbidden_facts": []},
    )
    report = eval_runner.aggregate([graded])
    text = eval_runner._format_report(report)
    assert "estimate-share" in text.lower() or "estimate share" in text.lower()
    # The 50.0% share should be rendered.
    assert "50" in text


def test_per_query_jsonl_includes_price_source_cells():
    """The --out JSONL row carries the per-query estimated/priced cell counts
    (dataclasses.asdict serialization of the new GradedQuery fields)."""
    graded = eval_runner.grade_run_result(
        eval_runner.QueryRunResult(
            id="q1", query="x", category="electronics", http_status=200,
            wall_ms=1000, error=None,
            response=_body_with_price_methods("estimated", "estimated"),
        ),
        {"id": "q1", "expected_prices": {}, "expected_specs": {},
         "expected_winner_index": None, "forbidden_facts": []},
    )
    row = dataclasses.asdict(graded)
    assert row["estimated_price_cells"] == 2
    assert row["priced_cells"] == 2

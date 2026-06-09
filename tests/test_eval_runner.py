"""Tests for scripts/eval_runner.py — Bundle B Phase B.6 eval-loop runner.

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4 (F4.1–F4.4)

The runner hits the deployed comparison endpoint once per gold-truth query
(?nocache=true), records the response + wall time, then grades it along 4
axes. ALL tests here use a mocked httpx transport (httpx.MockTransport) — no
live network, no cost. Three single-query LIVE probes against prod are run
manually by the lane agent (announced to dispatcher), never in this suite.
"""
from __future__ import annotations

import json
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
    assert len(gold["queries"]) == 50


def test_load_gold_truth_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        eval_runner.load_gold_truth(REPO_ROOT / "data" / "does_not_exist.json")


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

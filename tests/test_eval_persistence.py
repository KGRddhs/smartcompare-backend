"""Tests for scripts/eval_persistence.py — Bundle B Phase B.6 (F4.3).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.3
Schema: migrations/031_eval_runs.sql

One eval_runs row per run, written via the service-role Supabase client.
gold_truth_version = git SHA of data/validation_gold_truth.json. TDD with a
fully mocked Supabase client — no live DB.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts import eval_persistence
from scripts.eval_runner import EvalReport, GradedQuery


def _make_report() -> EvalReport:
    graded = [
        GradedQuery(id="elec-001", category="electronics", wall_ms=12000, http_status=200,
                    error=None, price_pass=True, specs_score=1.0, winner_pass=True,
                    factual_pass=True, weighted_score=1.0, passing=True, wall_over_cap=False),
        GradedQuery(id="supp-001", category="supplements", wall_ms=18000, http_status=200,
                    error=None, price_pass=True, specs_score=0.5, winner_pass=False,
                    factual_pass=True, weighted_score=0.6, passing=False, wall_over_cap=False),
    ]
    return EvalReport(
        queries_total=2, queries_passing=1, pass_rate=0.5,
        axis_avg_price=1.0, axis_avg_specs=0.75, axis_avg_winner=0.5, axis_avg_factual=1.0,
        wall_p50_ms=12000, wall_p95_ms=18000, per_query=graded,
        failing_ids=["supp-001"], p95_over_cap=False,
    )


def _mock_client_returning(row_id: str):
    """Build a MagicMock Supabase client whose insert().execute() returns a
    row with the given id (mirrors supabase-py's chained builder)."""
    client = MagicMock()
    execute_result = MagicMock()
    execute_result.data = [{"id": row_id}]
    client.table.return_value.insert.return_value.execute.return_value = execute_result
    return client


def test_persist_writes_one_row_with_mapped_columns():
    client = _mock_client_returning("11111111-1111-1111-1111-111111111111")
    with patch("scripts.eval_persistence.get_admin_supabase_client", return_value=client):
        run_id = eval_persistence.persist_eval_run(
            _make_report(), run_kind="manual", gold_version="abc123",
            metadata={"base_url": "http://x", "subset": "smoke20"},
        )

    assert run_id == "11111111-1111-1111-1111-111111111111"
    # exactly one table('eval_runs').insert(...).execute()
    client.table.assert_called_once_with("eval_runs")
    insert_payload = client.table.return_value.insert.call_args.args[0]
    assert insert_payload["run_kind"] == "manual"
    assert insert_payload["gold_truth_version"] == "abc123"
    assert insert_payload["queries_total"] == 2
    assert insert_payload["queries_passing"] == 1
    assert insert_payload["pass_rate"] == 0.5
    assert insert_payload["axis_avg_price"] == 1.0
    assert insert_payload["axis_avg_specs"] == 0.75
    assert insert_payload["axis_avg_winner"] == 0.5
    assert insert_payload["axis_avg_factual"] == 1.0
    assert insert_payload["wall_p50_ms"] == 12000
    assert insert_payload["wall_p95_ms"] == 18000


def test_persist_metadata_carries_failing_ids():
    client = _mock_client_returning("row-2")
    with patch("scripts.eval_persistence.get_admin_supabase_client", return_value=client):
        eval_persistence.persist_eval_run(
            _make_report(), run_kind="ci_pr", gold_version="sha",
            metadata={"branch": "feature/B6-eval-pipeline"},
        )
    payload = client.table.return_value.insert.call_args.args[0]
    md = payload["metadata"]
    # caller metadata is merged with run-derived context
    assert md["branch"] == "feature/B6-eval-pipeline"
    assert md["failing_ids"] == ["supp-001"]
    assert md["p95_over_cap"] is False


def test_persist_rejects_invalid_run_kind():
    with pytest.raises(ValueError):
        eval_persistence.persist_eval_run(_make_report(), run_kind="bogus",
                                          gold_version="sha")


def test_persist_returns_none_on_db_error_and_does_not_raise():
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")
    with patch("scripts.eval_persistence.get_admin_supabase_client", return_value=client):
        run_id = eval_persistence.persist_eval_run(_make_report(), run_kind="manual",
                                                   gold_version="sha")
    assert run_id is None


def test_fetch_baseline_row_returns_axis_dict():
    client = MagicMock()
    execute_result = MagicMock()
    execute_result.data = [{
        "id": "base-1", "pass_rate": 0.92, "axis_avg_price": 0.9,
        "axis_avg_specs": 0.85, "axis_avg_winner": 0.95, "axis_avg_factual": 1.0,
    }]
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_result
    with patch("scripts.eval_persistence.get_admin_supabase_client", return_value=client):
        row = eval_persistence.fetch_eval_run("base-1")
    assert row is not None
    assert row["pass_rate"] == 0.92
    assert row["axis_avg_winner"] == 0.95


def test_fetch_baseline_missing_returns_none():
    client = MagicMock()
    execute_result = MagicMock()
    execute_result.data = []
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_result
    with patch("scripts.eval_persistence.get_admin_supabase_client", return_value=client):
        assert eval_persistence.fetch_eval_run("nope") is None

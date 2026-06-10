"""Tests for scripts/cron_eval_nightly.py — Bundle B Phase B.6 (F4.5).

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md Lane F4.5
Pattern: scripts/cron_reengagement.py

Nightly eval cron: runs the FULL gold set against TARGET_BASE_URL, persists
one eval_runs row (run_kind='nightly'), logs the report incl. p95-vs-cap.
Railway cron registration is a DISPATCHER decision — the script documents
the command + env in its docstring and registers nothing.

All tests mock run_eval + persistence — no live network, no DB, no cost.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts import cron_eval_nightly
from scripts.eval_runner import EvalReport, load_gold_truth


def _report(p95_over_cap=False, wall_p95_ms=20000) -> EvalReport:
    return EvalReport(
        queries_total=50, queries_passing=46, pass_rate=0.92,
        axis_avg_price=0.9, axis_avg_specs=0.88, axis_avg_winner=0.94,
        axis_avg_factual=1.0, wall_p50_ms=12000, wall_p95_ms=wall_p95_ms,
        per_query=[], failing_ids=["supp-005"], p95_over_cap=p95_over_cap,
    )


def test_flag_off_skips_run(monkeypatch):
    monkeypatch.delenv("ENABLE_EVAL_CRON", raising=False)
    with patch("scripts.cron_eval_nightly.run_eval", new=AsyncMock()) as run_mock:
        asyncio.run(cron_eval_nightly.main())
    run_mock.assert_not_called()


def test_flag_on_runs_full_set_and_persists(monkeypatch):
    monkeypatch.setenv("ENABLE_EVAL_CRON", "true")
    monkeypatch.setenv("TARGET_BASE_URL", "https://web-production-58776.up.railway.app")
    report = _report()
    with patch("scripts.cron_eval_nightly.run_eval", new=AsyncMock(return_value=report)) as run_mock, \
         patch("scripts.cron_eval_nightly.persist_eval_run", return_value="nightly-row-1") as persist_mock, \
         patch("scripts.cron_eval_nightly.gold_truth_version", return_value="sha-abc"):
        asyncio.run(cron_eval_nightly.main())

    run_mock.assert_awaited_once()
    # Full set passed to run_eval — count-agnostic vs the real gold file.
    _, kwargs = run_mock.await_args
    queries_arg = run_mock.await_args.args[0]
    assert len(queries_arg) == len(load_gold_truth()["queries"])
    assert kwargs["base_url"] == "https://web-production-58776.up.railway.app"

    # persisted with run_kind='nightly' + the git SHA
    persist_mock.assert_called_once()
    _, pkwargs = persist_mock.call_args
    assert pkwargs["run_kind"] == "nightly"
    assert pkwargs["gold_version"] == "sha-abc"


def test_over_cap_logs_warning(monkeypatch, caplog):
    monkeypatch.setenv("ENABLE_EVAL_CRON", "true")
    report = _report(p95_over_cap=True, wall_p95_ms=31000)
    with patch("scripts.cron_eval_nightly.run_eval", new=AsyncMock(return_value=report)), \
         patch("scripts.cron_eval_nightly.persist_eval_run", return_value="row"), \
         patch("scripts.cron_eval_nightly.gold_truth_version", return_value="sha"):
        with caplog.at_level("WARNING"):
            asyncio.run(cron_eval_nightly.main())
    assert any("p95" in r.message.lower() and "cap" in r.message.lower()
               for r in caplog.records)


def test_run_failure_does_not_raise(monkeypatch):
    """A failed eval run (network/etc.) must not crash the cron process."""
    monkeypatch.setenv("ENABLE_EVAL_CRON", "true")
    with patch("scripts.cron_eval_nightly.run_eval",
               new=AsyncMock(side_effect=RuntimeError("network down"))), \
         patch("scripts.cron_eval_nightly.persist_eval_run") as persist_mock, \
         patch("scripts.cron_eval_nightly.gold_truth_version", return_value="sha"):
        # should swallow and return cleanly
        asyncio.run(cron_eval_nightly.main())
    persist_mock.assert_not_called()


def test_flag_on_helper_accepts_truthy_values(monkeypatch):
    for val in ("true", "1", "yes", "on", "TRUE"):
        monkeypatch.setenv("ENABLE_EVAL_CRON", val)
        assert cron_eval_nightly._flag_on() is True
    for val in ("false", "0", "", "no"):
        monkeypatch.setenv("ENABLE_EVAL_CRON", val)
        assert cron_eval_nightly._flag_on() is False

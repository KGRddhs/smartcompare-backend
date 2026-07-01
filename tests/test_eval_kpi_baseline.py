"""Wave-1 Task A — the regression-gate baseline id must be a FULL uuid.

A truncated id (e.g. the CLAUDE.md-cited `54b603e8`) triggers Postgres
`22P02 invalid input syntax for type uuid`, which `fetch_eval_run` swallows in
its try/except and turns into a silent `None` → the gate reports "baseline not
found", indistinguishable from a genuinely-missing row. This pins a CLEAR,
distinct error for a malformed/truncated id BEFORE the DB round-trip, so a
next-session operator who fat-fingers the truncated anchor gets told exactly
what is wrong (and the full-uuid form to use).
"""
from __future__ import annotations

import types
from unittest import mock

from scripts import eval_gate


_FULL_UUID = "54b603e8-4eab-41c9-a34d-a5e391446559"
_TRUNCATED = "54b603e8"


def _report(**axes):
    """Minimal EvalReport stand-in: axis_avg_<axis> attrs + pass_rate."""
    base = {"axis_avg_price": 0.5, "axis_avg_specs": 0.5,
            "axis_avg_winner": 0.5, "axis_avg_factual": 0.5, "pass_rate": 0.9}
    base.update(axes)
    return types.SimpleNamespace(**base)


def test_truncated_baseline_id_gives_clear_malformed_error_not_not_found():
    # A truncated (non-full-uuid) id must be rejected with a CLEAR malformed-id
    # message that names the full-uuid form — NOT the ambiguous "not found".
    passed, msg = eval_gate.evaluate_gate(
        _report(), mode="regression", baseline_run_id=_TRUNCATED,
    )
    assert passed is False
    low = msg.lower()
    assert "uuid" in low
    # It must be distinguishable from the genuinely-missing-row message.
    assert "not found" not in low
    # And it should point at the correct full-uuid form.
    assert _FULL_UUID in msg


def test_truncated_baseline_id_never_hits_the_db():
    # The format check short-circuits BEFORE fetch_eval_run, so a malformed id
    # never even issues the 22P02-triggering query.
    with mock.patch.object(eval_gate, "fetch_eval_run") as m:
        eval_gate.evaluate_gate(
            _report(), mode="regression", baseline_run_id=_TRUNCATED,
        )
        m.assert_not_called()


def test_full_uuid_proceeds_to_fetch_then_reports_not_found():
    # A well-formed full uuid PASSES the format check and reaches fetch_eval_run;
    # a None there is the genuine "not found" path (distinct from malformed).
    with mock.patch.object(eval_gate, "fetch_eval_run", return_value=None) as m:
        passed, msg = eval_gate.evaluate_gate(
            _report(), mode="regression", baseline_run_id=_FULL_UUID,
        )
        m.assert_called_once_with(_FULL_UUID)
    assert passed is False
    assert "not found" in msg.lower()


def test_full_uuid_with_found_baseline_passes_when_no_axis_drop():
    baseline = {"axis_avg_price": 0.5, "axis_avg_specs": 0.5,
                "axis_avg_winner": 0.5, "axis_avg_factual": 0.5}
    with mock.patch.object(eval_gate, "fetch_eval_run", return_value=baseline):
        passed, msg = eval_gate.evaluate_gate(
            _report(), mode="regression", baseline_run_id=_FULL_UUID,
        )
    assert passed is True
    assert "PASS" in msg

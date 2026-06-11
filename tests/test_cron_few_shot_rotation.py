"""Tests for scripts/cron_few_shot_rotation.py — Bundle B S2 Lane I1 (I1.4).

Plan: docs/plans/2026-06-11-bundle-b-s2-plan.md § I1.4
Pattern: scripts/cron_eval_nightly.py + scripts/cron_reengagement.py

Weekly few-shot rotation cron: regenerates data/verdict_exemplars.json from
the top-decile of comparison_feedback rows (useful=true AND
winner_correct='correct', migration 027 columns), keeping the I1.2 synthetic
seed as the cold-start fallback. Privacy: only product names + verdict text
are read from the linked comparison — never user identity.

Railway cron registration is a DISPATCHER decision — the script documents the
command + env in its docstring and registers nothing (same fail-CLOSED posture
as ENABLE_EVAL_CRON).

All tests mock the Supabase client + filesystem — no live network, no DB, no
cost.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from scripts import cron_few_shot_rotation as rot


# ---------------------------------------------------------------------------
# Fixtures — fake feedback rows joined to their comparison payloads
# ---------------------------------------------------------------------------

def _fb_row(category, names, winner_idx, winner_reason, key_tradeoff,
            vc0, vc1, *, useful=True, winner_correct="correct"):
    """A comparison_feedback row pre-joined to its comparison payload, in the
    shape _fetch_top_decile_feedback is contracted to return."""
    return {
        "useful": useful,
        "winner_correct": winner_correct,
        "comparison": {
            "product_names": names,
            "full_response": {
                "overview": {"products": [{"name": names[0]}, {"name": names[1]}],
                             "category": category},
                "comparison": {
                    "winner_index": winner_idx,
                    "winner_reason": winner_reason,
                    "key_tradeoff": key_tradeoff,
                    "value_context": {"product_0": vc0, "product_1": vc1},
                },
            },
        },
    }


@pytest.fixture
def good_rows():
    return [
        _fb_row("makeup", ["Brand A glow", "Brand B filter"], 0,
                "Near-identical glow at 65% less.",
                "The pricier filter has a finer shade range.",
                "Outstanding value-per-dinar.", "You pay a prestige premium."),
        _fb_row("electronics", ["Printer X", "Printer Y"], 0,
                "About 40% lower cost per page.",
                "The rival prints sharper first-page text.",
                "Stronger value-per-dinar for a home office.",
                "Dearer toner narrows its value."),
    ]


# ---------------------------------------------------------------------------
# Flag gating (fail-closed) — mirrors cron_eval_nightly contract
# ---------------------------------------------------------------------------

def test_flag_off_skips_run(monkeypatch):
    monkeypatch.delenv("ENABLE_FEWSHOT_ROTATION", raising=False)
    with patch.object(rot, "_fetch_top_decile_feedback") as fetch_mock, \
         patch.object(rot, "_write_exemplar_file") as write_mock:
        asyncio.run(rot.main())
    fetch_mock.assert_not_called()
    write_mock.assert_not_called()


def test_flag_on_helper_accepts_truthy_values(monkeypatch):
    for val in ("true", "1", "yes", "on", "TRUE"):
        monkeypatch.setenv("ENABLE_FEWSHOT_ROTATION", val)
        assert rot._flag_on() is True
    for val in ("false", "0", "", "no"):
        monkeypatch.setenv("ENABLE_FEWSHOT_ROTATION", val)
        assert rot._flag_on() is False


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------

def test_flag_on_regenerates_file(monkeypatch, good_rows):
    monkeypatch.setenv("ENABLE_FEWSHOT_ROTATION", "true")
    with patch.object(rot, "get_admin_supabase_client", return_value=MagicMock()), \
         patch.object(rot, "_fetch_top_decile_feedback", return_value=good_rows), \
         patch.object(rot, "_write_exemplar_file") as write_mock:
        asyncio.run(rot.main())
    write_mock.assert_called_once()
    written = write_mock.call_args.args[0]
    # categories present from the harvested rows
    assert "makeup" in written and "electronics" in written
    # each category has the {exemplars, anti_patterns} shape
    for cat in ("makeup", "electronics"):
        assert set(written[cat].keys()) >= {"exemplars", "anti_patterns"}
        assert isinstance(written[cat]["exemplars"], list)


def test_empty_feedback_falls_back_to_seed(monkeypatch):
    """Cold start: zero qualifying feedback rows → keep the synthetic seed,
    never write an empty exemplar file that would blank production."""
    monkeypatch.setenv("ENABLE_FEWSHOT_ROTATION", "true")
    with patch.object(rot, "get_admin_supabase_client", return_value=MagicMock()), \
         patch.object(rot, "_fetch_top_decile_feedback", return_value=[]), \
         patch.object(rot, "_write_exemplar_file") as write_mock:
        asyncio.run(rot.main())
    # no write at all when there's nothing to learn from (seed is left intact)
    write_mock.assert_not_called()


def test_privacy_only_names_and_verdict(good_rows):
    """The generated exemplars must contain ONLY product names + verdict text,
    never user_id / device / email or any identity field."""
    built = rot._build_exemplars_from_feedback(good_rows)
    blob = json.dumps(built)
    for forbidden in ("user_id", "device", "email", "fingerprint"):
        assert forbidden not in blob


def test_build_filters_to_correct_and_useful():
    """Only useful=true AND winner_correct='correct' rows are mined."""
    rows = [
        _fb_row("makeup", ["A", "B"], 0, "65% less.", "trade", "v0", "v1",
                useful=True, winner_correct="correct"),
        _fb_row("makeup", ["C", "D"], 1, "wrong call.", "trade", "v0", "v1",
                useful=True, winner_correct="wrong"),
        _fb_row("makeup", ["E", "F"], 0, "not useful.", "trade", "v0", "v1",
                useful=False, winner_correct="correct"),
    ]
    built = rot._build_exemplars_from_feedback(rows)
    # only the first row qualifies
    names_used = json.dumps(built)
    assert "65% less." in names_used
    assert "wrong call." not in names_used
    assert "not useful." not in names_used


def test_run_failure_does_not_raise(monkeypatch):
    """A failed fetch/parse must not crash the cron worker."""
    monkeypatch.setenv("ENABLE_FEWSHOT_ROTATION", "true")
    with patch.object(rot, "get_admin_supabase_client", return_value=MagicMock()), \
         patch.object(rot, "_fetch_top_decile_feedback",
                      side_effect=RuntimeError("db down")), \
         patch.object(rot, "_write_exemplar_file") as write_mock:
        asyncio.run(rot.main())  # swallows + logs
    write_mock.assert_not_called()


def test_exemplar_schema_compatible(good_rows):
    """Generated exemplars must carry the I1.1 contract fields so the I2 loader
    can render them: title, teaches, setup, verdict_json, _provenance."""
    built = rot._build_exemplars_from_feedback(good_rows)
    for cat, block in built.items():
        for ex in block["exemplars"]:
            assert {"title", "teaches", "setup", "verdict_json",
                    "_provenance"} <= set(ex.keys())
            vj = ex["verdict_json"]
            assert vj["winner_index"] in (0, 1)
            assert "personalized_insights" not in vj
            # rotation-sourced provenance is flagged non-synthetic
            assert ex["_provenance"]["synthetic"] is False
            assert ex["_provenance"]["source"] == "comparison_feedback"

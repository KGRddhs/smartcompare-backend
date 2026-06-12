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
    """The mined exemplars must contain ONLY product names + verdict text,
    never user_id / device / email or any identity field. existing={} isolates
    the feedback-mined output (the merge-base preservation is covered separately)."""
    built = rot._build_exemplars_from_feedback(good_rows, existing={})
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
    can render them: title, teaches, setup, verdict_json, _provenance. Isolate
    feedback-mined exemplars with existing={} (so seed rows from the real file
    aren't mixed in — those are synthetic:true by design)."""
    built = rot._build_exemplars_from_feedback(good_rows, existing={})
    for cat, block in built.items():
        for ex in block["exemplars"]:
            assert {"title", "teaches", "setup", "verdict_json",
                    "_provenance"} <= set(ex.keys())
            vj = ex["verdict_json"]
            assert vj["winner_index"] in (0, 1)
            assert "personalized_insights" not in vj
            # B3: mined exemplars are synthetic:false (truthful) + carry the
            # comparison_id as source_pattern_id + the abridged marker.
            assert ex["_provenance"]["synthetic"] is False
            assert ex["_provenance"]["source"] == "comparison_feedback"
            assert ex["_provenance"].get("source_pattern_id")
            assert "abridged, do not copy structure or content" in ex["setup"]


# ---------------------------------------------------------------------------
# B2 read-merge-write preservation — REAL write (not mocked), proving rotation
# never clobbers I2's anti_patterns / _schema and never blanks unfed categories.
# ---------------------------------------------------------------------------

def _seeded_existing():
    """An existing file shaped like the real post-G3 canonical: I2 _schema +
    per-category anti_patterns + an I1 synthetic seed in exemplars[]."""
    return {
        "_schema": {"note": "I2 schema doc", "version": 1},
        "_meta": {"version": 1, "custom_i2_key": "keep me"},
        "electronics": {
            "exemplars": [{"title": "seed-elec", "teaches": "H4",
                           "_provenance": {"source_pattern_id": "elec-024",
                                           "synthetic": True}}],
            "anti_patterns": [{"name": "identical on paper", "rule": "r", "teaches": "H4"}],
        },
        "grocery": {
            "exemplars": [{"title": "seed-groc", "teaches": "H1"}],
            "anti_patterns": [{"name": "global prestige", "rule": "r", "teaches": "H2"}],
        },
    }


def test_real_write_preserves_anti_patterns_and_schema(tmp_path):
    """REAL write (no mock): I2's anti_patterns + the _schema block survive a
    rotation that only has feedback for an unrelated category."""
    existing = _seeded_existing()
    p = tmp_path / "verdict_exemplars.json"
    p.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

    makeup_row = _fb_row("makeup", ["A", "B"], 0, "65% less.", "t", "value v0",
                         "premium v1")
    makeup_row["comparison_id"] = "cmp-xyz"
    built = rot._build_exemplars_from_feedback([makeup_row], existing=existing)
    rot._write_exemplar_file(built, path=p, existing=existing)

    written = json.loads(p.read_text(encoding="utf-8"))
    # _schema preserved verbatim
    assert written["_schema"]["note"] == "I2 schema doc"
    # I2's category anti_patterns preserved
    assert len(written["electronics"]["anti_patterns"]) == 1
    assert len(written["grocery"]["anti_patterns"]) == 1
    # custom _meta key preserved; rotation note stamped
    assert written["_meta"]["custom_i2_key"] == "keep me"
    assert "rotation_note" in written["_meta"]


def test_real_write_keeps_seed_for_unfed_categories(tmp_path):
    """Categories WITHOUT qualifying feedback keep their existing synthetic seed
    — rotation never blanks them."""
    existing = _seeded_existing()
    p = tmp_path / "verdict_exemplars.json"
    p.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

    # feedback only for makeup → electronics + grocery keep their seed
    makeup_row = _fb_row("makeup", ["A", "B"], 0, "65% less.", "t", "v0", "v1")
    built = rot._build_exemplars_from_feedback([makeup_row], existing=existing)
    rot._write_exemplar_file(built, path=p, existing=existing)

    written = json.loads(p.read_text(encoding="utf-8"))
    assert written["electronics"]["exemplars"][0]["title"] == "seed-elec"
    assert written["grocery"]["exemplars"][0]["title"] == "seed-groc"
    # makeup got the feedback exemplar
    assert written["makeup"]["exemplars"][0]["_provenance"]["source"] == "comparison_feedback"


def test_fed_category_replaces_exemplars_keeps_its_aps(tmp_path):
    """A category WITH feedback gets its exemplars[] replaced but KEEPS its own
    anti_patterns."""
    existing = _seeded_existing()
    p = tmp_path / "verdict_exemplars.json"
    p.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

    # feedback for grocery (which has an existing seed + AP)
    groc_row = _fb_row("grocery", ["X", "Y"], 1, "30% more value.", "t", "v0", "v1")
    built = rot._build_exemplars_from_feedback([groc_row], existing=existing)
    rot._write_exemplar_file(built, path=p, existing=existing)

    written = json.loads(p.read_text(encoding="utf-8"))
    # grocery exemplars REPLACED by feedback (seed-groc gone)
    titles = [e["title"] for e in written["grocery"]["exemplars"]]
    assert "seed-groc" not in titles
    assert written["grocery"]["exemplars"][0]["_provenance"]["source"] == "comparison_feedback"
    # grocery's AP still preserved
    assert len(written["grocery"]["anti_patterns"]) == 1

"""Tests for A-L4.4 — Instagram feasibility helper.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.4
Doc:  docs/plans/2026-06-08-A-instagram-feasibility-test.md

The script wraps human observation collection — these tests cover its
deterministic bits: init schema, summary decision rule, stub query
coverage (5 categories), and JSON shape stability.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "instagram_feasibility_test.py"


def _load_helper():
    spec = importlib.util.spec_from_file_location("instagram_feasibility_test", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["instagram_feasibility_test"] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load_helper()


# ---------------------------------------------------------------------------
# Stub queries cover the 5 required categories
# ---------------------------------------------------------------------------

def test_stub_queries_has_5_entries():
    assert len(helper.STUB_QUERIES) == 5


def test_stub_queries_cover_required_categories():
    required = {"fragrances", "makeup", "fashion", "electronics", "supplements"}
    seen = {q["category"] for q in helper.STUB_QUERIES}
    assert seen == required


def test_stub_queries_each_have_brand_main_and_tiktok():
    for q in helper.STUB_QUERIES:
        assert q["instagram_brand_main_handle"].startswith("@")
        assert q["tiktok_hashtag"].startswith("#")


def test_stub_queries_unique_ids():
    ids = [q["id"] for q in helper.STUB_QUERIES]
    assert len(set(ids)) == 5


# ---------------------------------------------------------------------------
# _empty_finding shape
# ---------------------------------------------------------------------------

def test_empty_finding_has_all_required_keys():
    stub = helper.STUB_QUERIES[0]
    finding = helper._empty_finding(stub)
    required = {
        "id", "category", "query", "tested_at", "tester",
        "instagram_brand_main", "instagram_influencers", "tiktok",
        "score", "decision_rationale",
    }
    assert set(finding.keys()) >= required
    assert finding["score"] is None  # un-scored stub
    assert len(finding["instagram_influencers"]) == 3
    assert finding["instagram_brand_main"]["handle"] == stub["instagram_brand_main_handle"]
    assert finding["tiktok"]["hashtag_reviewed"] == stub["tiktok_hashtag"]


# ---------------------------------------------------------------------------
# Init writes a valid file
# ---------------------------------------------------------------------------

def test_init_writes_valid_file(tmp_path):
    out_path = tmp_path / "findings.json"
    args = argparse_ns(cmd="init", out=str(out_path), force=False)
    rc = helper.cmd_init(args)
    assert rc == 0

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "_metadata" in data
    assert "findings" in data
    assert len(data["findings"]) == 5
    assert data["_metadata"]["schema_version"] == 1


def test_init_refuses_overwrite_without_force(tmp_path):
    out_path = tmp_path / "findings.json"
    out_path.write_text("{}", encoding="utf-8")
    args = argparse_ns(cmd="init", out=str(out_path), force=False)
    rc = helper.cmd_init(args)
    assert rc == 1
    assert out_path.read_text(encoding="utf-8") == "{}"


def test_init_overwrites_with_force(tmp_path):
    out_path = tmp_path / "findings.json"
    out_path.write_text("{}", encoding="utf-8")
    args = argparse_ns(cmd="init", out=str(out_path), force=True)
    rc = helper.cmd_init(args)
    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "_metadata" in data


# ---------------------------------------------------------------------------
# Summary decision rule (>=3 of 5 score >=3 → green-light)
# ---------------------------------------------------------------------------

def _make_findings_file(tmp_path, scores):
    """scores: list of 5 int scores or None for un-scored entries."""
    findings = []
    for stub, score in zip(helper.STUB_QUERIES, scores):
        f = helper._empty_finding(stub)
        f["score"] = score
        f["decision_rationale"] = f"score={score}"
        findings.append(f)
    payload = {"_metadata": {"schema_version": 1}, "findings": findings}
    out = tmp_path / "f.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def test_summary_pending_when_unscored(tmp_path, capsys):
    out = _make_findings_file(tmp_path, [5, 4, None, 2, 1])
    helper.cmd_summary(argparse_ns(cmd="summary", out=str(out)))
    cap = capsys.readouterr().out
    assert "1 pending" in cap or "pending" in cap


def test_summary_green_light_when_three_pass(tmp_path, capsys):
    out = _make_findings_file(tmp_path, [5, 4, 3, 2, 1])
    helper.cmd_summary(argparse_ns(cmd="summary", out=str(out)))
    cap = capsys.readouterr().out
    assert "GREEN-LIGHT" in cap


def test_summary_cut_when_below_threshold(tmp_path, capsys):
    out = _make_findings_file(tmp_path, [2, 2, 2, 2, 5])
    helper.cmd_summary(argparse_ns(cmd="summary", out=str(out)))
    cap = capsys.readouterr().out
    assert "CUT" in cap


def test_summary_exact_threshold_green_lights(tmp_path, capsys):
    # 3 of 5 scoring >=3 — exactly at threshold
    out = _make_findings_file(tmp_path, [3, 3, 3, 1, 1])
    helper.cmd_summary(argparse_ns(cmd="summary", out=str(out)))
    cap = capsys.readouterr().out
    assert "GREEN-LIGHT" in cap


# ---------------------------------------------------------------------------
# Bootstrapped file in data/ has the right shape
# ---------------------------------------------------------------------------

def test_bootstrapped_findings_file_exists_and_is_valid():
    path = REPO_ROOT / "data" / "instagram_feasibility_findings.json"
    assert path.exists(), "run scripts/instagram_feasibility_test.py init"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["findings"]) == 5
    cats = {f["category"] for f in data["findings"]}
    assert cats == {"fragrances", "makeup", "fashion", "electronics", "supplements"}


# ---------------------------------------------------------------------------
# argparse-Namespace helper for tests
# ---------------------------------------------------------------------------

class argparse_ns:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

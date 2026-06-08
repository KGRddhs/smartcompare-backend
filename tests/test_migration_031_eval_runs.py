"""Drift guard for Migration 031 — eval_runs.

Plan: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.5
Migration: migrations/031_eval_runs.sql
Rollback:  migrations/rollback/031_eval_runs.sql

Aggregate observability table for the eval loop. 4-value run_kind enum
+ pass_rate [0..1] bounded + 4 per-axis averages bounded + count
invariants (passing <= total). No FKs. Service-role-only access.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL = REPO_ROOT / "migrations" / "031_eval_runs.sql"
ROLLBACK_SQL = REPO_ROOT / "migrations" / "rollback" / "031_eval_runs.sql"

EXPECTED_RUN_KINDS = {"ci_pr", "nightly", "manual", "staging_smoke"}
EXPECTED_AXES = ("price", "specs", "winner", "factual")
EXPECTED_INDEXES = (
    "idx_eval_runs_kind_created",
    "idx_eval_runs_pass_rate",
    "idx_eval_runs_gold_truth_version",
)


def _strip_sql_line_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


# ---------------------------------------------------------------------------
# Files exist
# ---------------------------------------------------------------------------

def test_migration_031_file_exists():
    assert MIGRATION_SQL.exists(), f"missing {MIGRATION_SQL}"


def test_rollback_031_file_exists():
    assert ROLLBACK_SQL.exists(), f"missing {ROLLBACK_SQL}"


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------

def test_migration_031_creates_table_if_not_exists():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.eval_runs" in sql


def test_migration_031_has_required_columns():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for pat in (
        r"id\s+uuid\s+PRIMARY KEY",
        r"run_kind\s+text\s+NOT NULL",
        r"gold_truth_version\s+text\s+NOT NULL",
        r"queries_total\s+integer\s+NOT NULL",
        r"queries_passing\s+integer\s+NOT NULL",
        r"pass_rate\s+numeric\(5,4\)\s+NOT NULL",
        r"axis_avg_price\s+numeric\(5,4\)\s+NULL",
        r"axis_avg_specs\s+numeric\(5,4\)\s+NULL",
        r"axis_avg_winner\s+numeric\(5,4\)\s+NULL",
        r"axis_avg_factual\s+numeric\(5,4\)\s+NULL",
        r"wall_p50_ms\s+integer\s+NULL",
        r"wall_p95_ms\s+integer\s+NULL",
        r"metadata\s+jsonb\s+NULL",
        r"created_at\s+timestamptz\s+NOT NULL",
    ):
        assert re.search(pat, sql, re.IGNORECASE), f"missing column matching {pat}"


def test_migration_031_no_foreign_keys():
    """eval_runs is a standalone observability table — no FKs to users
    / comparisons / etc."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    # Look for any REFERENCES clause inside the CREATE TABLE block.
    m = re.search(
        r"CREATE TABLE IF NOT EXISTS public\.eval_runs\s*\((.*?)\)\s*;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert m is not None, "could not isolate CREATE TABLE block"
    block = m.group(1)
    assert "REFERENCES" not in block.upper(), (
        "eval_runs should have no FK REFERENCES — it's a standalone "
        "observability table per preflight § 4.5"
    )


# ---------------------------------------------------------------------------
# run_kind enum — drift guard
# ---------------------------------------------------------------------------

def _extract_run_kinds(sql: str) -> set:
    sql = _strip_sql_line_comments(sql)
    m = re.search(
        r"CONSTRAINT eval_runs_run_kind_check\s+CHECK\s*\(\s*run_kind\s+IN\s*\(([^)]+)\)\s*\)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert m is not None, "could not find eval_runs_run_kind_check"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def test_migration_031_run_kind_enum_matches_canonical():
    kinds = _extract_run_kinds(MIGRATION_SQL.read_text(encoding="utf-8"))
    only_in_sql = kinds - EXPECTED_RUN_KINDS
    only_in_expected = EXPECTED_RUN_KINDS - kinds
    assert kinds == EXPECTED_RUN_KINDS, (
        f"run_kind enum drift.\n"
        f"  Only in SQL: {sorted(only_in_sql)}\n"
        f"  Only in expected: {sorted(only_in_expected)}"
    )


def test_migration_031_run_kind_count_is_4():
    kinds = _extract_run_kinds(MIGRATION_SQL.read_text(encoding="utf-8"))
    assert len(kinds) == 4


# ---------------------------------------------------------------------------
# Range CHECK constraints — pass_rate + 4 per-axis averages
# ---------------------------------------------------------------------------

def test_migration_031_pass_rate_bounded_0_to_1():
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    pat = re.compile(
        r"CONSTRAINT eval_runs_pass_rate_range\s+CHECK\s*\(\s*pass_rate\s*>=\s*0\s+AND\s+pass_rate\s*<=\s*1\s*\)",
        re.IGNORECASE,
    )
    assert pat.search(sql), "pass_rate range CHECK missing or malformed"


def test_migration_031_each_axis_avg_bounded_0_to_1():
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    for axis in EXPECTED_AXES:
        pat = re.compile(
            rf"CONSTRAINT eval_runs_axis_avg_{axis}_range\s+CHECK\s*\(\s*"
            rf"axis_avg_{axis}\s+IS\s+NULL\s+OR\s+\(\s*axis_avg_{axis}\s*>=\s*0\s+AND\s+axis_avg_{axis}\s*<=\s*1\s*\)\s*\)",
            re.IGNORECASE,
        )
        assert pat.search(sql), f"axis_avg_{axis} range CHECK missing or malformed"


def test_migration_031_passing_lte_total_check():
    """queries_passing must be in [0, queries_total]."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    pat = re.compile(
        r"CONSTRAINT eval_runs_passing_lte_total\s+CHECK\s*\(\s*"
        r"queries_passing\s*>=\s*0\s+AND\s+queries_passing\s*<=\s*queries_total\s*\)",
        re.IGNORECASE,
    )
    assert pat.search(sql), "passing<=total CHECK missing or malformed"


# ---------------------------------------------------------------------------
# RLS posture — service-role only
# ---------------------------------------------------------------------------

def test_migration_031_enables_rls():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_migration_031_has_no_user_facing_policy():
    """Per preflight § 6 + team-lead Q2 decision: internal observability
    only. NO CREATE POLICY in this migration."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    pat = re.compile(
        r"CREATE POLICY [a-z_]+\s+ON public\.eval_runs",
        re.IGNORECASE,
    )
    assert not pat.search(sql), (
        "eval_runs migration should not create a user-facing policy. "
        "Service-role-only access."
    )


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

def test_migration_031_creates_all_expected_indexes():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for idx in EXPECTED_INDEXES:
        assert idx in sql, f"missing expected index {idx}"


def test_migration_031_kind_created_index_is_composite():
    """idx_eval_runs_kind_created should be (run_kind, created_at DESC)
    — order matters for the time-series scan."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert re.search(
        r"idx_eval_runs_kind_created[\s\S]+?\(\s*run_kind\s*,\s*created_at\s+DESC\s*\)",
        sql,
        re.IGNORECASE,
    ), "idx_eval_runs_kind_created should be (run_kind, created_at DESC)"


# ---------------------------------------------------------------------------
# Transaction wrapping + docs
# ---------------------------------------------------------------------------

def test_migration_031_wraps_in_transaction():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


def test_migration_031_documents_critical_columns():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert re.search(r"COMMENT ON TABLE public\.eval_runs", sql, re.IGNORECASE)
    assert re.search(r"COMMENT ON COLUMN public\.eval_runs\.run_kind", sql, re.IGNORECASE)
    assert re.search(r"COMMENT ON COLUMN public\.eval_runs\.gold_truth_version", sql, re.IGNORECASE)


# ---------------------------------------------------------------------------
# Rollback symmetry
# ---------------------------------------------------------------------------

def test_rollback_031_drops_table():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS public.eval_runs" in sql


def test_rollback_031_drops_all_indexes_explicitly():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for idx in EXPECTED_INDEXES:
        assert f"DROP INDEX IF EXISTS public.{idx}" in sql, f"rollback missing DROP INDEX {idx}"


def test_rollback_031_does_not_drop_policy():
    sql = _strip_sql_line_comments(ROLLBACK_SQL.read_text(encoding="utf-8"))
    assert "DROP POLICY" not in sql


def test_rollback_031_wraps_in_transaction():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql

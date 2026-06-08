"""Drift guard for Migration 027 — comparison_feedback correctness columns.

Plan: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.1
Migration: migrations/027_comparison_feedback_correctness.sql
Rollback:  migrations/rollback/027_comparison_feedback_correctness.sql

The 3 columns + their CHECK constraints must enforce a strict
`correct | wrong | unsure | NULL` enum. These tests parse the migration
SQL + the rollback SQL and assert structural invariants. They do NOT
hit a live database; the live apply happens at B.1 dispatch via
Supabase MCP `apply_migration`.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL = REPO_ROOT / "migrations" / "027_comparison_feedback_correctness.sql"
ROLLBACK_SQL = REPO_ROOT / "migrations" / "rollback" / "027_comparison_feedback_correctness.sql"

EXPECTED_COLUMNS = ("winner_correct", "price_correct", "specs_correct")
EXPECTED_ENUM_VALUES = {"correct", "wrong", "unsure"}


def _strip_sql_line_comments(sql: str) -> str:
    """Strip `-- ... \\n` line comments — same helper as 028 tests."""
    return re.sub(r"--[^\n]*", "", sql)


# ---------------------------------------------------------------------------
# Files exist
# ---------------------------------------------------------------------------

def test_migration_027_file_exists():
    assert MIGRATION_SQL.exists(), f"missing {MIGRATION_SQL}"


def test_rollback_027_file_exists():
    assert ROLLBACK_SQL.exists(), f"missing {ROLLBACK_SQL}"


# ---------------------------------------------------------------------------
# Column adds
# ---------------------------------------------------------------------------

def test_migration_027_adds_all_3_columns():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        pat = re.compile(
            rf"ALTER TABLE public\.comparison_feedback\s+ADD COLUMN IF NOT EXISTS {col} text NULL",
            re.IGNORECASE,
        )
        assert pat.search(sql), f"Missing ADD COLUMN for {col!r}"


def test_migration_027_columns_are_nullable():
    """Each new column MUST be NULL — the existing thumbs-up/down path
    must continue to work without per-axis prompting."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        # Find the ADD COLUMN line, assert NULL keyword present + no
        # `NOT NULL` adjacency before next semicolon.
        pat = re.compile(
            rf"ADD COLUMN IF NOT EXISTS {col} text\s+(NULL|NOT NULL)",
            re.IGNORECASE,
        )
        m = pat.search(sql)
        assert m is not None, f"Could not find {col} ADD COLUMN line"
        assert m.group(1).upper() == "NULL", (
            f"{col} must be nullable (got {m.group(1)!r}). Existing thumbs-up/down "
            f"feedback rows have no per-axis signal and must remain valid."
        )


# ---------------------------------------------------------------------------
# CHECK constraint enums
# ---------------------------------------------------------------------------

def _extract_check_values(sql: str, col: str) -> set:
    """Find the CHECK clause for `col` and pull every single-quoted string."""
    pat = re.compile(
        rf"CONSTRAINT comparison_feedback_{col}_check\s+CHECK\s*\(([^)]+)\)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pat.search(sql)
    assert m is not None, f"Could not find CHECK for {col}"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def test_migration_027_check_constraints_use_canonical_enum():
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    for col in EXPECTED_COLUMNS:
        values = _extract_check_values(sql, col)
        assert values == EXPECTED_ENUM_VALUES, (
            f"{col} CHECK enum drift: expected {EXPECTED_ENUM_VALUES}, got {values}"
        )


def test_migration_027_check_constraints_allow_null():
    """Each CHECK must include `<col> IS NULL OR <col> IN (...)` so NULL
    is accepted alongside the 3 enum values."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    for col in EXPECTED_COLUMNS:
        pat = re.compile(
            rf"CONSTRAINT comparison_feedback_{col}_check\s+CHECK\s*\(\s*{col}\s+IS\s+NULL\s+OR\s+{col}\s+IN",
            re.IGNORECASE,
        )
        assert pat.search(sql), f"{col} CHECK does not allow NULL"


def test_migration_027_drops_constraint_before_adding():
    """Re-runnability: each ADD CONSTRAINT must be preceded by a
    DROP CONSTRAINT IF EXISTS for the same name. Postgres 15 doesn't
    support ADD CONSTRAINT IF NOT EXISTS — drop-then-add is the
    idempotent shape."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        drop_pos = sql.find(f"DROP CONSTRAINT IF EXISTS comparison_feedback_{col}_check")
        add_pos = sql.find(f"ADD CONSTRAINT comparison_feedback_{col}_check")
        assert drop_pos != -1, f"missing DROP CONSTRAINT for {col}"
        assert add_pos != -1, f"missing ADD CONSTRAINT for {col}"
        assert drop_pos < add_pos, f"DROP must come before ADD for {col}"


# ---------------------------------------------------------------------------
# Partial index
# ---------------------------------------------------------------------------

def test_migration_027_partial_index_present():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "idx_comparison_feedback_correctness_present" in sql


def test_migration_027_partial_index_is_partial():
    """The eval-loop index should be a partial index gated on
    `WHERE (... IS NOT NULL OR ... IS NOT NULL OR ...)` so it stays
    small until per-axis adoption ramps up via B.3."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"CREATE INDEX IF NOT EXISTS idx_comparison_feedback_correctness_present[^;]+;",
        sql,
        re.IGNORECASE,
    )
    assert m is not None
    block = m.group(0)
    # Every per-axis column should appear in the WHERE clause.
    assert "WHERE" in block.upper()
    for col in EXPECTED_COLUMNS:
        assert col in block, f"{col} missing from partial-index WHERE"


# ---------------------------------------------------------------------------
# Transaction wrapping
# ---------------------------------------------------------------------------

def test_migration_027_wraps_in_transaction():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


# ---------------------------------------------------------------------------
# COMMENT ON for documentation
# ---------------------------------------------------------------------------

def test_migration_027_documents_each_column():
    """All 3 new columns should have a COMMENT ON for psql / Supabase
    dashboard self-documentation (matches Migration 028 pattern)."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        pat = re.compile(rf"COMMENT ON COLUMN public\.comparison_feedback\.{col}", re.IGNORECASE)
        assert pat.search(sql), f"missing COMMENT ON for {col}"


# ---------------------------------------------------------------------------
# Rollback symmetry
# ---------------------------------------------------------------------------

def test_rollback_027_drops_each_column():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        assert f"DROP COLUMN IF EXISTS {col}" in sql, f"rollback missing DROP COLUMN {col}"


def test_rollback_027_drops_each_constraint():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        assert f"DROP CONSTRAINT IF EXISTS comparison_feedback_{col}_check" in sql


def test_rollback_027_drops_index():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "DROP INDEX IF EXISTS public.idx_comparison_feedback_correctness_present" in sql


def test_rollback_027_constraints_before_columns():
    """DROP CONSTRAINT must precede DROP COLUMN — Postgres allows the
    reverse but it's brittle if a column constraint references another
    column. Explicit ordering keeps the rollback robust."""
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for col in EXPECTED_COLUMNS:
        constraint_pos = sql.find(f"DROP CONSTRAINT IF EXISTS comparison_feedback_{col}_check")
        column_pos = sql.find(f"DROP COLUMN IF EXISTS {col}")
        assert constraint_pos != -1 and column_pos != -1
        assert constraint_pos < column_pos, f"DROP CONSTRAINT must precede DROP COLUMN for {col}"


def test_rollback_027_wraps_in_transaction():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql

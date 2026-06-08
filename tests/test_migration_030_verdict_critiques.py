"""Drift guard for Migration 030 — verdict_critiques.

Plan: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.4
Migration: migrations/030_verdict_critiques.sql
Rollback:  migrations/rollback/030_verdict_critiques.sql

5 critique axes (0..10 integer, nullable) + regeneration trace + cost
trace. RLS posture: service-role-only (no user-facing SELECT policy
per team-lead Q2 decision). Tests validate the CHECK range constraints
on all 5 axes plus the regenerated-then-reason invariant.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL = REPO_ROOT / "migrations" / "030_verdict_critiques.sql"
ROLLBACK_SQL = REPO_ROOT / "migrations" / "rollback" / "030_verdict_critiques.sql"

CRITIQUE_AXES = (
    "bias_score",
    "vagueness_score",
    "hedging_score",
    "missing_citation_score",
    "pain_workflow_align_score",
)


def _strip_sql_line_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


# ---------------------------------------------------------------------------
# Files exist
# ---------------------------------------------------------------------------

def test_migration_030_file_exists():
    assert MIGRATION_SQL.exists(), f"missing {MIGRATION_SQL}"


def test_rollback_030_file_exists():
    assert ROLLBACK_SQL.exists(), f"missing {ROLLBACK_SQL}"


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------

def test_migration_030_creates_table_if_not_exists():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.verdict_critiques" in sql


def test_migration_030_has_required_columns():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for pat in (
        r"id\s+uuid\s+PRIMARY KEY",
        r"comparison_id\s+uuid\s+NOT NULL",
        r"regenerated\s+boolean\s+NOT NULL\s+DEFAULT\s+false",
        r"regen_reason\s+text\s+NULL",
        r"critic_model\s+text\s+NOT NULL",
        r"critic_tokens_used\s+integer\s+NULL",
        r"created_at\s+timestamptz\s+NOT NULL",
    ):
        assert re.search(pat, sql, re.IGNORECASE), f"missing column matching {pat}"


def test_migration_030_has_all_5_critique_axes():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for axis in CRITIQUE_AXES:
        # Each axis MUST be integer NULL (nullable for partial critiques).
        pat = re.compile(rf"{axis}\s+integer\s+NULL", re.IGNORECASE)
        assert pat.search(sql), f"missing axis {axis!r} or wrong type/nullness"


def test_migration_030_comparison_id_cascades_on_delete():
    """Purging a comparison purges its critique — no analytic value in
    dangling critique rows pointing at gone IDs."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"comparison_id\s+uuid\s+NOT NULL\s+REFERENCES\s+public\.comparisons\(id\)\s+ON DELETE\s+(\w+)",
        sql,
        re.IGNORECASE,
    )
    assert m is not None
    assert m.group(1).upper() == "CASCADE"


# ---------------------------------------------------------------------------
# CHECK range constraints on all 5 axes
# ---------------------------------------------------------------------------

def test_migration_030_each_axis_has_range_check():
    """Each of the 5 critique-axis columns must have a CHECK constraint
    enforcing the 0..10 range and accepting NULL."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    for axis in CRITIQUE_AXES:
        # Match: CONSTRAINT vc_<axis>_range CHECK (<axis> IS NULL OR <axis> BETWEEN 0 AND 10)
        pat = re.compile(
            rf"CONSTRAINT vc_{axis}_range\s+CHECK\s*\(\s*{axis}\s+IS\s+NULL\s+OR\s+{axis}\s+BETWEEN\s+0\s+AND\s+10\s*\)",
            re.IGNORECASE,
        )
        assert pat.search(sql), f"missing or malformed range CHECK for axis {axis!r}"


def test_migration_030_regen_reason_check_present():
    """If regenerated=true, regen_reason should be NOT NULL — the eval
    loop wants to know WHY the regeneration fired."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    pat = re.compile(
        r"CONSTRAINT vc_regen_reason_when_regenerated\s+CHECK\s*\(\s*regenerated\s*=\s*false\s+OR\s+regen_reason\s+IS\s+NOT\s+NULL\s*\)",
        re.IGNORECASE,
    )
    assert pat.search(sql), "vc_regen_reason_when_regenerated CHECK missing or malformed"


# ---------------------------------------------------------------------------
# RLS posture — service-role only (NO user-facing SELECT policy)
# ---------------------------------------------------------------------------

def test_migration_030_enables_rls():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_migration_030_has_no_user_facing_policy():
    """Per team-lead Q2 decision 2026-06-08: internal observability only.
    NO CREATE POLICY should exist in this migration. Service-role
    bypasses RLS naturally."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    # Strip comments so we don't match policy mentions inside docs.
    sql_no_comments = _strip_sql_line_comments(sql)
    # Find any CREATE POLICY for verdict_critiques.
    pat = re.compile(
        r"CREATE POLICY [a-z_]+\s+ON public\.verdict_critiques",
        re.IGNORECASE,
    )
    assert not pat.search(sql_no_comments), (
        "verdict_critiques migration should NOT create a user-facing SELECT policy. "
        "Service-role-only access per preflight § 6 + team-lead Q2 ratification."
    )


# ---------------------------------------------------------------------------
# Indexes — 4 expected per preflight § 4.4
# ---------------------------------------------------------------------------

EXPECTED_INDEXES = (
    "idx_vc_comparison_id",
    "idx_vc_regenerated",
    "idx_vc_low_align",
    "idx_vc_created_at",
)


def test_migration_030_creates_all_expected_indexes():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for idx in EXPECTED_INDEXES:
        assert idx in sql, f"missing expected index {idx}"


def test_migration_030_regenerated_index_is_partial():
    """idx_vc_regenerated should be a partial index gated on
    `WHERE regenerated = true` — most rows will be false, partial
    index keeps it small."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"CREATE INDEX IF NOT EXISTS idx_vc_regenerated[^;]+;",
        sql,
        re.IGNORECASE,
    )
    assert m is not None
    block = m.group(0)
    assert "WHERE" in block.upper()
    assert "regenerated = true" in block.lower() or "regenerated=true" in block.lower()


def test_migration_030_low_align_index_is_partial():
    """idx_vc_low_align should filter `pain_workflow_align_score < 7`
    — eval loop hot path."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"CREATE INDEX IF NOT EXISTS idx_vc_low_align[^;]+;",
        sql,
        re.IGNORECASE,
    )
    assert m is not None
    block = m.group(0)
    assert "WHERE" in block.upper()
    assert "pain_workflow_align_score" in block
    # whitespace-flexible: collapse all whitespace and look for `<7`
    assert "<7" in re.sub(r"\s+", "", block)


# ---------------------------------------------------------------------------
# Transaction wrapping + docs
# ---------------------------------------------------------------------------

def test_migration_030_wraps_in_transaction():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


def test_migration_030_documents_critical_columns():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert re.search(r"COMMENT ON TABLE public\.verdict_critiques", sql, re.IGNORECASE)
    assert re.search(r"COMMENT ON COLUMN public\.verdict_critiques\.pain_workflow_align_score", sql, re.IGNORECASE)
    assert re.search(r"COMMENT ON COLUMN public\.verdict_critiques\.regen_reason", sql, re.IGNORECASE)


# ---------------------------------------------------------------------------
# Rollback symmetry
# ---------------------------------------------------------------------------

def test_rollback_030_drops_table():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS public.verdict_critiques" in sql


def test_rollback_030_drops_all_indexes_explicitly():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for idx in EXPECTED_INDEXES:
        assert f"DROP INDEX IF EXISTS public.{idx}" in sql, f"rollback missing DROP INDEX {idx}"


def test_rollback_030_wraps_in_transaction():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


def test_rollback_030_does_not_drop_policy():
    """Migration 030 created NO policy; the rollback shouldn't mention
    DROP POLICY (a stray drop would silently no-op via IF EXISTS but
    indicates inconsistent thinking)."""
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    sql_no_comments = _strip_sql_line_comments(sql)
    assert "DROP POLICY" not in sql_no_comments, (
        "Migration 030 created no policy; rollback should not reference DROP POLICY"
    )

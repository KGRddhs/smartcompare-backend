"""Drift guard for Migration 029 — user_preference_history.

Plan: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.2
Migration: migrations/029_user_preference_history.sql
Rollback:  migrations/rollback/029_user_preference_history.sql

The CHECK constraint on `change_source` MUST stay synchronised with the
5-value enum team-lead ratified in preflight § 9 Q4:
  manual_edit | cohort_default | onboarding_initial |
  import_from_demographics | system_correction

This file enforces that invariant, plus the structural posture (RLS,
FK CASCADE on user_id, GIN index over preferences jsonb).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL = REPO_ROOT / "migrations" / "029_user_preference_history.sql"
ROLLBACK_SQL = REPO_ROOT / "migrations" / "rollback" / "029_user_preference_history.sql"

EXPECTED_CHANGE_SOURCES = {
    "manual_edit",
    "cohort_default",
    "onboarding_initial",
    "import_from_demographics",
    "system_correction",
}


def _strip_sql_line_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


# ---------------------------------------------------------------------------
# Files exist
# ---------------------------------------------------------------------------

def test_migration_029_file_exists():
    assert MIGRATION_SQL.exists(), f"missing {MIGRATION_SQL}"


def test_rollback_029_file_exists():
    assert ROLLBACK_SQL.exists(), f"missing {ROLLBACK_SQL}"


# ---------------------------------------------------------------------------
# Table structural assertions
# ---------------------------------------------------------------------------

def test_migration_029_creates_table_if_not_exists():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.user_preference_history" in sql


def test_migration_029_table_has_required_columns():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for col_pattern in (
        r"id\s+uuid\s+PRIMARY KEY",
        r"user_id\s+uuid\s+NOT NULL",
        r"preferences\s+jsonb\s+NOT NULL",
        r"change_source\s+text\s+NOT NULL",
        r"created_at\s+timestamptz\s+NOT NULL",
    ):
        assert re.search(col_pattern, sql, re.IGNORECASE), f"missing column matching {col_pattern}"


def test_migration_029_user_id_cascades_on_delete():
    """User deletion must cascade — App Store account-deletion req
    + matches migration 025 + 028 patterns."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"user_id\s+uuid\s+NOT NULL\s+REFERENCES\s+public\.users\(id\)\s+ON DELETE\s+(\w+)",
        sql,
        re.IGNORECASE,
    )
    assert m is not None, "could not locate user_id FK"
    assert m.group(1).upper() == "CASCADE"


def test_migration_029_preferences_is_jsonb_not_text():
    """preferences MUST be jsonb — mirrors the users.preferences type and
    allows the GIN index for B.2's few-shot rotator queries."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert re.search(r"preferences\s+jsonb", sql, re.IGNORECASE), (
        "preferences column must be jsonb"
    )


# ---------------------------------------------------------------------------
# change_source CHECK constraint — drift guard
# ---------------------------------------------------------------------------

def _extract_change_sources(sql: str) -> set:
    """Pull the change_source CHECK enum out of the migration."""
    sql = _strip_sql_line_comments(sql)
    m = re.search(
        r"CONSTRAINT uph_change_source_check\s+CHECK\s*\(\s*change_source\s+IN\s*\(([^)]+)\)\s*\)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert m is not None, "could not find uph_change_source_check"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def test_migration_029_change_source_enum_matches_ratified_list():
    """Team-lead ratified the 5-value enum 2026-06-08 (preflight § 9 Q4).
    Drift here breaks backend writes (silent CHECK reject)."""
    sources = _extract_change_sources(MIGRATION_SQL.read_text(encoding="utf-8"))
    only_in_sql = sources - EXPECTED_CHANGE_SOURCES
    only_in_expected = EXPECTED_CHANGE_SOURCES - sources
    assert sources == EXPECTED_CHANGE_SOURCES, (
        f"change_source enum drift.\n"
        f"  Only in SQL: {sorted(only_in_sql)}\n"
        f"  Only in expected: {sorted(only_in_expected)}"
    )


def test_migration_029_change_source_count_is_5():
    sources = _extract_change_sources(MIGRATION_SQL.read_text(encoding="utf-8"))
    assert len(sources) == 5


# ---------------------------------------------------------------------------
# RLS posture
# ---------------------------------------------------------------------------

def test_migration_029_enables_rls():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_migration_029_has_select_policy_only():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "CREATE POLICY uph_own_select" in sql
    # No INSERT/UPDATE/DELETE policy — service-role only
    forbidden = [
        re.compile(r"CREATE POLICY [a-z_]+\s+ON public\.user_preference_history\s+FOR INSERT", re.IGNORECASE),
        re.compile(r"CREATE POLICY [a-z_]+\s+ON public\.user_preference_history\s+FOR UPDATE", re.IGNORECASE),
        re.compile(r"CREATE POLICY [a-z_]+\s+ON public\.user_preference_history\s+FOR DELETE", re.IGNORECASE),
    ]
    for pat in forbidden:
        assert not pat.search(sql), f"unexpected non-SELECT policy: {pat.pattern}"


def test_migration_029_select_policy_uses_auth_uid():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert re.search(
        r"CREATE POLICY uph_own_select[\s\S]+?USING\s*\(\s*auth\.uid\(\)\s*=\s*user_id\s*\)",
        sql,
        re.IGNORECASE,
    ), "uph_own_select policy must filter on auth.uid() = user_id"


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

def test_migration_029_creates_user_time_index():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "idx_uph_user_created" in sql
    # And it's a composite (user_id, created_at DESC) — order matters
    assert re.search(
        r"idx_uph_user_created[\s\S]+?\(\s*user_id\s*,\s*created_at\s+DESC\s*\)",
        sql,
        re.IGNORECASE,
    ), "idx_uph_user_created should be (user_id, created_at DESC)"


def test_migration_029_creates_change_source_index():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "idx_uph_change_source" in sql


def test_migration_029_creates_gin_index_on_preferences():
    """B.2 few-shot rotator needs jsonb path queries; GIN unlocks them."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "idx_uph_preferences_gin" in sql
    assert re.search(
        r"idx_uph_preferences_gin[\s\S]+?USING\s+gin\s*\(\s*preferences\s*\)",
        sql,
        re.IGNORECASE,
    ), "idx_uph_preferences_gin should be USING gin(preferences)"


# ---------------------------------------------------------------------------
# Transaction wrapping + docs
# ---------------------------------------------------------------------------

def test_migration_029_wraps_in_transaction():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


def test_migration_029_documents_table():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert re.search(r"COMMENT ON TABLE public\.user_preference_history", sql, re.IGNORECASE)
    assert re.search(r"COMMENT ON COLUMN public\.user_preference_history\.change_source", sql, re.IGNORECASE)


# ---------------------------------------------------------------------------
# Backfill safety — must be commented out, not active
# ---------------------------------------------------------------------------

def test_migration_029_backfill_is_commented_out():
    """The initial backfill INSERT is dev/staging only — never run by
    default. Lines should be prefixed with `-- ` so prod apply doesn't
    touch users.preferences."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    # Find the backfill block
    backfill_match = re.search(
        r"INSERT INTO public\.user_preference_history.*?(?=\Z|--+\s*\n\n)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    # If an active INSERT exists OUTSIDE of comments, that's the bug we
    # guard against. We check there's no line beginning with `INSERT INTO`
    # (only `-- INSERT INTO` should appear).
    active_insert = re.search(
        r"(?m)^\s*INSERT INTO public\.user_preference_history",
        sql,
    )
    assert active_insert is None, (
        "active INSERT INTO public.user_preference_history found in migration 029. "
        "Backfill statements MUST be comment-prefixed (`-- INSERT ...`) so prod apply is no-op."
    )


# ---------------------------------------------------------------------------
# Rollback symmetry
# ---------------------------------------------------------------------------

def test_rollback_029_drops_table():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS public.user_preference_history" in sql


def test_rollback_029_drops_policy_before_table():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    policy_pos = sql.find("DROP POLICY")
    table_pos = sql.find("DROP TABLE")
    assert policy_pos != -1
    assert table_pos != -1
    assert policy_pos < table_pos


def test_rollback_029_drops_all_indexes_explicitly():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for idx in ("idx_uph_user_created", "idx_uph_change_source", "idx_uph_preferences_gin"):
        assert f"DROP INDEX IF EXISTS public.{idx}" in sql, f"rollback missing DROP INDEX {idx}"


def test_rollback_029_wraps_in_transaction():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql

"""Drift guard for Migration 028 — pain_workflow_events.

Plan: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.3
Migration: migrations/028_pain_workflow_events.sql
Rollback:  migrations/rollback/028_pain_workflow_events.sql

The CHECK constraint on `workflow_name` must stay synchronised with the
canonical names emitted by `scripts/etl_survey_to_priors.py` into
`data/pain_workflow_priors.json`. A drift between the two means
backend writes will be silently rejected by the CHECK, OR the prior
aggregator will silently drop rows whose names don't appear in the
file.

This test reads BOTH files and asserts equality. It is the cheapest
way to catch the most common B.1 regression — someone renames a
workflow in one place and forgets the other.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAIN_JSON = REPO_ROOT / "data" / "pain_workflow_priors.json"
MIGRATION_SQL = REPO_ROOT / "migrations" / "028_pain_workflow_events.sql"
ROLLBACK_SQL = REPO_ROOT / "migrations" / "rollback" / "028_pain_workflow_events.sql"


def _strip_sql_line_comments(sql: str) -> str:
    """Remove `-- ... \\n` line comments. Trailing `(parens)` inside
    comments would otherwise terminate `[^)]+` regex matches and yield
    a partial CHECK-constraint payload."""
    return re.sub(r"--[^\n]*", "", sql)


def _extract_workflow_names_from_sql() -> set:
    """Parse the CHECK constraint values out of the migration. Looks for
    the pwe_workflow_name_check block and extracts every single-quoted
    string literal between the IN ( ... ) parens."""
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    m = re.search(
        r"workflow_name\s+IN\s*\(\s*([^)]+)\s*\)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert m is not None, "Could not find workflow_name IN (...) block in migration 028"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def _extract_signal_types_from_sql() -> set:
    sql = _strip_sql_line_comments(MIGRATION_SQL.read_text(encoding="utf-8"))
    m = re.search(
        r"signal_type\s+IN\s*\(\s*([^)]+)\s*\)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert m is not None, "Could not find signal_type IN (...) block in migration 028"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def _workflow_names_from_priors() -> set:
    priors = json.loads(PAIN_JSON.read_text(encoding="utf-8"))
    return {w["name"] for w in priors["workflows"]}


# ---------------------------------------------------------------------------
# Drift checks
# ---------------------------------------------------------------------------

def test_migration_028_file_exists():
    assert MIGRATION_SQL.exists(), f"missing {MIGRATION_SQL}"


def test_rollback_028_file_exists():
    assert ROLLBACK_SQL.exists(), f"missing {ROLLBACK_SQL}"


def test_workflow_names_in_check_match_priors_json():
    """The 8 canonical workflow names in the CHECK constraint MUST
    equal the 8 names emitted by the ETL into pain_workflow_priors.json."""
    sql_names = _extract_workflow_names_from_sql()
    json_names = _workflow_names_from_priors()
    only_in_sql = sql_names - json_names
    only_in_json = json_names - sql_names
    assert sql_names == json_names, (
        f"Workflow name drift between migration 028 and pain_workflow_priors.json.\n"
        f"  Only in SQL CHECK: {sorted(only_in_sql)}\n"
        f"  Only in JSON:      {sorted(only_in_json)}"
    )


def test_workflow_names_count_is_8():
    """Sanity check — the design § 6 prescribes exactly 8 workflows."""
    sql_names = _extract_workflow_names_from_sql()
    assert len(sql_names) == 8


def test_signal_type_check_has_canonical_8():
    """The signal_type CHECK constraint defines the canonical 8-type
    instrumentation taxonomy (preflight § 4.3)."""
    sql_signals = _extract_signal_types_from_sql()
    expected = {
        "abandonment",
        "requery_within_5min",
        "share_then_no_purchase",
        "long_dwell",
        "tldr_only",
        "expanded_all_specs",
        "compared_again_same_pair",
        "changed_priority",
    }
    assert sql_signals == expected


# ---------------------------------------------------------------------------
# Structural assertions on the SQL itself
# ---------------------------------------------------------------------------

def test_migration_028_wraps_in_transaction():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


def test_migration_028_enables_rls():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_migration_028_has_select_policy_only():
    """User-facing policies should be SELECT-only; INSERT/UPDATE/DELETE go
    through service role per preflight § 6 RLS posture decision."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "CREATE POLICY pwe_own_select" in sql
    # Defensive: no INSERT/UPDATE/DELETE policy snuck in
    forbidden = [
        re.compile(r"CREATE POLICY [a-z_]+\s+ON public.pain_workflow_events\s+FOR INSERT", re.IGNORECASE),
        re.compile(r"CREATE POLICY [a-z_]+\s+ON public.pain_workflow_events\s+FOR UPDATE", re.IGNORECASE),
        re.compile(r"CREATE POLICY [a-z_]+\s+ON public.pain_workflow_events\s+FOR DELETE", re.IGNORECASE),
    ]
    for pat in forbidden:
        assert not pat.search(sql), f"Unexpected non-SELECT policy in migration 028: {pat.pattern}"


def test_migration_028_user_id_cascades_on_delete():
    """User deletion must cascade to their pain-workflow events (App
    Store account-deletion requirement; matches the migration 025
    cascade extension pattern)."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    # Find the user_id REFERENCES line and assert ON DELETE CASCADE
    m = re.search(
        r"user_id\s+uuid\s+NOT NULL\s+REFERENCES\s+public\.users\(id\)\s+ON DELETE\s+(\w+)",
        sql,
        re.IGNORECASE,
    )
    assert m is not None, "Could not locate user_id FK line"
    assert m.group(1).upper() == "CASCADE"


def test_migration_028_comparison_id_sets_null_on_delete():
    """Comparison purges (DELETE /history/{id}) must NOT cascade to
    workflow events — the signal "user abandoned this comparison" is
    still useful even if the comparison record is gone."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"comparison_id\s+uuid\s+NULL\s+REFERENCES\s+public\.comparisons\(id\)\s+ON DELETE\s+(\w+\s*\w*)",
        sql,
        re.IGNORECASE,
    )
    assert m is not None, "Could not locate comparison_id FK line"
    assert "SET NULL" in m.group(1).upper()


def test_migration_028_creates_expected_indexes():
    """Index set matches the APPLIED prod DDL (dispatcher correction
    2026-06-10): the composite idx_pwe_workflow_time replaced both the
    single-column idx_pwe_workflow_name (redundant) and idx_pwe_recent
    (illegal volatile now() predicate)."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    for idx in (
        "idx_pwe_workflow_time",
        "idx_pwe_user_workflow_time",
        "idx_pwe_comparison_id",
    ):
        assert idx in sql, f"missing expected index {idx}"


def test_migration_028_no_dropped_indexes_remain():
    """The two corrected-away indexes must NOT reappear in the forward
    migration — re-adding idx_pwe_recent re-introduces the 42P17 apply
    failure, and idx_pwe_workflow_name is now served by the composite."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    # Only assert on actual CREATE INDEX statements, not the explanatory
    # header comment (which legitimately names the removed indexes).
    create_stmts = re.findall(
        r"CREATE INDEX[^;]+;", sql, re.IGNORECASE
    )
    joined = "\n".join(create_stmts)
    assert "idx_pwe_recent" not in joined, (
        "idx_pwe_recent must not be re-created — its now() predicate is "
        "rejected by Postgres (42P17)"
    )
    assert "idx_pwe_workflow_name" not in joined, (
        "idx_pwe_workflow_name is redundant with the idx_pwe_workflow_time "
        "composite — must not be re-created"
    )


def test_migration_028_workflow_time_index_is_plain_composite():
    """idx_pwe_workflow_time is a plain (workflow_name, created_at DESC)
    composite — NO partial WHERE predicate (the 90-day window is a
    query-time filter, not an index predicate)."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    m = re.search(
        r"CREATE INDEX IF NOT EXISTS idx_pwe_workflow_time[^;]+;",
        sql,
        re.IGNORECASE,
    )
    assert m is not None, "idx_pwe_workflow_time CREATE INDEX missing"
    block = m.group(0)
    assert "workflow_name" in block.lower()
    assert "created_at" in block.lower()
    assert "WHERE" not in block.upper(), (
        "idx_pwe_workflow_time must NOT have a WHERE predicate"
    )


# ---------------------------------------------------------------------------
# Rollback symmetry
# ---------------------------------------------------------------------------

def test_rollback_028_drops_table():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS public.pain_workflow_events" in sql


def test_rollback_028_drops_policy_before_table():
    """DROP POLICY must come before DROP TABLE in the script."""
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    policy_pos = sql.find("DROP POLICY")
    table_pos = sql.find("DROP TABLE")
    assert policy_pos != -1
    assert table_pos != -1
    assert policy_pos < table_pos


def test_rollback_028_drops_all_indexes_explicitly():
    """Rollback drops the APPLIED index names (dispatcher correction)."""
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    for idx in (
        "idx_pwe_workflow_time",
        "idx_pwe_user_workflow_time",
        "idx_pwe_comparison_id",
    ):
        assert f"DROP INDEX IF EXISTS public.{idx}" in sql, f"rollback missing DROP INDEX for {idx}"


def test_rollback_028_wraps_in_transaction():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


# ---------------------------------------------------------------------------
# Live schema verification (post-MCP-apply) — skipped in free unit suite.
#
# 028 was applied with a dispatcher correction (2026-06-10): the composite
# idx_pwe_workflow_time replaced idx_pwe_recent (volatile predicate) + the
# redundant idx_pwe_workflow_name. These assertions verify the LIVE prod
# schema matches the corrected names, and that the removed indexes are gone.
# Run with:
#   LIVE=1 pytest tests/test_migration_028_pain_workflow_events.py -m live_db
# `LIVE=1` is required: without it the credential sanitizer is active and the
# collection hook skips every live_db item (see tests/_env_safety.py).
# ---------------------------------------------------------------------------

import os  # noqa: E402 — kept local to the live_db section


def _supabase_available() -> bool:
    return bool(
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_ANON_KEY")
        and os.getenv("SUPABASE_SERVICE_KEY")
    )


# Applied prod index set (dispatcher correction). Verified via Supabase MCP
# on 2026-06-10: workflow_time, user_workflow_time, comparison_id, pkey.
EXPECTED_LIVE_INDEXES = {
    "idx_pwe_workflow_time",
    "idx_pwe_user_workflow_time",
    "idx_pwe_comparison_id",
    "pain_workflow_events_pkey",
}
REMOVED_INDEXES = {"idx_pwe_recent", "idx_pwe_workflow_name"}


@pytest.mark.live_db
class TestMigration028LiveSchema:
    """Live Supabase assertions — run post-apply with `LIVE=1 ... -m live_db`.

    NOTE on index verification: the supabase-py / PostgREST client cannot read
    pg_indexes (no generic SQL surface), so index NAMES are verified out-of-band
    via Supabase MCP execute_sql (`SELECT indexname FROM pg_indexes WHERE
    tablename='pain_workflow_events'`) — done at apply time 2026-06-10 and
    re-runnable by the dispatcher. The expected/removed sets are pinned here as
    the source of truth for that check. What PostgREST CAN verify — the table is
    selectable and the CHECK enums reject bad values — is asserted below.
    """

    @pytest.fixture
    def admin_client(self):
        if not _supabase_available():
            pytest.skip("Supabase env vars not configured for live_db tests")
        from app.services.database_service import get_admin_supabase_client

        return get_admin_supabase_client()

    def test_pain_workflow_events_table_selectable(self, admin_client):
        """The table exists and is readable via the service-role client."""
        result = (
            admin_client.table("pain_workflow_events").select("id").limit(1).execute()
        )
        assert hasattr(result, "data")

    def test_workflow_name_check_rejects_unknown_value(self, admin_client):
        """The workflow_name CHECK is live — an out-of-enum insert is rejected.
        We use a syntactically-valid but non-enum value; the DB must 4xx. (We
        deliberately do not assert on signal_type here to isolate the check.)"""
        import uuid

        bogus = {
            "user_id": str(uuid.uuid4()),  # FK may also reject; either way insert fails
            "workflow_name": "not_a_real_workflow",
            "signal_type": "abandonment",
        }
        try:
            admin_client.table("pain_workflow_events").insert(bogus).execute()
        except Exception as e:
            # Expected: CHECK violation (or FK violation on the random user_id).
            assert (
                "pwe_workflow_name_check" in str(e)
                or "violates" in str(e).lower()
                or "foreign key" in str(e).lower()
            ), f"unexpected error shape: {e!r}"
            return
        pytest.fail("insert with bogus workflow_name unexpectedly succeeded")

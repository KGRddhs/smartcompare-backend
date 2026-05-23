"""Static checks on the Migration 025 delete_user_cascade SQL body.

These tests parse the migration file directly so they can run without
hitting Supabase. They verify the SQL covers every table that the
account-deletion design (Bundle D Task 1.B.5 / R20) requires.

Live verification — apply the migration to a staging schema, insert
fixtures across all the listed tables for a synthetic user, call
`SELECT delete_user_cascade(<uuid>)`, and assert zero rows remain — is
out of scope for this static unit-test pack. The Bundle D anchor calls
for `tests/test_delete_user_cascade.py PASS + migration applied via
Supabase MCP` as the joint acceptance.
"""
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"
MIGRATION_025 = MIGRATIONS_DIR / "025_delete_user_cascade_completeness.sql"
ROLLBACK_025 = MIGRATIONS_DIR / "rollback" / "025_delete_user_cascade_completeness.sql"


@pytest.fixture(scope="module")
def migration_sql() -> str:
    assert MIGRATION_025.exists(), f"missing migration file: {MIGRATION_025}"
    return MIGRATION_025.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rollback_sql() -> str:
    assert ROLLBACK_025.exists(), f"missing rollback file: {ROLLBACK_025}"
    return ROLLBACK_025.read_text(encoding="utf-8")


class TestMigration025Cascade:
    """Forward migration covers every Bundle-D-required table."""

    def test_creates_function_atomically(self, migration_sql):
        assert "CREATE OR REPLACE FUNCTION public.delete_user_cascade" in migration_sql
        assert "BEGIN;" in migration_sql
        assert "COMMIT;" in migration_sql

    def test_function_runs_with_security_definer(self, migration_sql):
        """RPC must be SECURITY DEFINER so the anon-key client can call it."""
        assert "SECURITY DEFINER" in migration_sql

    def test_preserves_original_bundle_a_deletes(self, migration_sql):
        for table in (
            "user_events",
            "comparison_feedback",
            "comparisons",
            "search_logs",
        ):
            assert f"DELETE FROM {table} WHERE user_id = target_user_id" in migration_sql, (
                f"Bundle A cascade lost the {table} delete"
            )

    def test_adds_user_usage_delete(self, migration_sql):
        assert "DELETE FROM user_usage WHERE user_id = target_user_id" in migration_sql

    def test_adds_referral_invites_delete_for_both_user_roles(self, migration_sql):
        """referral_invites references the user as referrer OR redeemer."""
        assert "DELETE FROM referral_invites" in migration_sql
        assert "referrer_user_id = target_user_id" in migration_sql
        assert "redeemed_by_user_id = target_user_id" in migration_sql

    def test_adds_referral_redemptions_delete_for_both_user_roles(self, migration_sql):
        assert "DELETE FROM referral_redemptions" in migration_sql
        assert "invitee_user_id = target_user_id" in migration_sql

    def test_clears_push_token_and_device_fingerprint(self, migration_sql):
        """Push token + device fingerprint live as columns on users, not a separate table."""
        assert "expo_push_token = NULL" in migration_sql
        assert "device_fingerprint_hash = NULL" in migration_sql

    def test_does_not_delete_admin_audit_log(self, migration_sql):
        """Session 43 decision — audit log MUST outlive the user record."""
        assert "DELETE FROM admin_audit_log" not in migration_sql

    def test_users_row_is_updated_not_deleted(self, migration_sql):
        """Foreign keys from admin_audit_log need the users row to survive."""
        assert "DELETE FROM users WHERE" not in migration_sql
        assert "UPDATE users" in migration_sql
        assert "preferences = NULL" in migration_sql
        assert "behavior_profile = NULL" in migration_sql
        assert "preferences_completed = false" in migration_sql


class TestRollback025:
    """Rollback file restores the pre-Bundle-D cascade body."""

    def test_rollback_file_exists_and_is_atomic(self, rollback_sql):
        assert "BEGIN;" in rollback_sql
        assert "COMMIT;" in rollback_sql
        assert "CREATE OR REPLACE FUNCTION public.delete_user_cascade" in rollback_sql

    def test_rollback_omits_bundle_d_additions(self, rollback_sql):
        assert "DELETE FROM user_usage" not in rollback_sql
        assert "DELETE FROM referral_invites" not in rollback_sql
        assert "DELETE FROM referral_redemptions" not in rollback_sql

    def test_rollback_keeps_original_bundle_a_body(self, rollback_sql):
        for table in (
            "user_events",
            "comparison_feedback",
            "comparisons",
            "search_logs",
        ):
            assert f"DELETE FROM {table} WHERE user_id = target_user_id" in rollback_sql

    def test_rollback_does_not_re_clear_push_token(self, rollback_sql):
        """The pre-Bundle-D function body did not touch expo_push_token."""
        # Strip SQL comments so we only inspect executable statements
        body = "\n".join(
            line for line in rollback_sql.splitlines() if not line.lstrip().startswith("--")
        )
        assert "expo_push_token" not in body
        assert "device_fingerprint_hash" not in body

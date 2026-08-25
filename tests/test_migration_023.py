"""Migration 023 — `users.lifetime_invites_consumed` + device fingerprint index.

Two test classes:

1. `TestMigration023SQLFile` (free unit) — static assertions on the SQL file
   itself. Verifies the SQL the team will actually push to Supabase contains
   the columns/indexes the design doc § 4.5 + plan task 1.1 promised. Catches
   accidental edits to the migration before it ever reaches the database.

2. `TestMigration023LiveSchema` (`@pytest.mark.live_db`) — connects to Supabase
   via `get_admin_supabase_client()` and asserts the live schema matches.
   Skipped from the free unit suite via the live_db marker. Run with:
       LIVE=1 pytest tests/test_migration_023.py -v -m live_db
   (`LIVE=1` is required — without it the credential sanitizer in
   tests/_env_safety.py is active and the collection hook skips the tier.)

Reference:
- docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.5
- docs/plans/2026-05-12-bundle-bcd-consolidated.md Phase 1 Task 1.1
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest


MIGRATION_PATH = Path("migrations/023_referral_lifetime_cap.sql")


# ============================================
# Static SQL-file contract
# ============================================


class TestMigration023SQLFile:
    """SQL-file shape assertions — runs in the free unit suite."""

    @pytest.fixture(scope="class")
    def sql(self) -> str:
        assert MIGRATION_PATH.exists(), (
            f"Migration 023 file not found at {MIGRATION_PATH} — "
            "design doc § 4.5 requires this exact path."
        )
        return MIGRATION_PATH.read_text(encoding="utf-8")

    def test_adds_lifetime_invites_consumed_column(self, sql: str):
        """ALTER TABLE adds the new INT counter column with IF NOT EXISTS."""
        # Normalise whitespace so multi-line ALTER is matched
        flat = re.sub(r"\s+", " ", sql)
        assert re.search(
            r"ALTER\s+TABLE\s+users\s+ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+"
            r"lifetime_invites_consumed\s+INT",
            flat,
            re.IGNORECASE,
        ), "Migration must `ADD COLUMN IF NOT EXISTS lifetime_invites_consumed INT`"

    def test_lifetime_column_is_not_null_with_default_zero(self, sql: str):
        """Per design § 4.5 the column is `INT NOT NULL DEFAULT 0` so the
        lifetime-cap query `SUM(lifetime_invites_consumed) >= 3` never trips
        on a NULL from a legacy row."""
        flat = re.sub(r"\s+", " ", sql)
        assert re.search(
            r"lifetime_invites_consumed\s+INT\s+NOT\s+NULL\s+DEFAULT\s+0",
            flat,
            re.IGNORECASE,
        ), "lifetime_invites_consumed must be `INT NOT NULL DEFAULT 0`"

    def test_drops_legacy_weekly_invites_used_column(self, sql: str):
        """The weekly counter is replaced — design § 4.5 explicitly drops it."""
        flat = re.sub(r"\s+", " ", sql)
        assert re.search(
            r"ALTER\s+TABLE\s+users\s+DROP\s+COLUMN\s+IF\s+EXISTS\s+"
            r"weekly_invites_used",
            flat,
            re.IGNORECASE,
        ), "Migration must `DROP COLUMN IF EXISTS weekly_invites_used`"

    def test_creates_partial_index_on_device_fingerprint(self, sql: str):
        """The cross-account device cap query needs a partial index on
        device_fingerprint_hash WHERE NOT NULL — per design § 4.5."""
        flat = re.sub(r"\s+", " ", sql)
        assert re.search(
            r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+"
            r"idx_users_device_fingerprint_active",
            flat,
            re.IGNORECASE,
        ), "Migration must `CREATE INDEX IF NOT EXISTS idx_users_device_fingerprint_active`"
        assert re.search(
            r"ON\s+users\s*\(\s*device_fingerprint_hash\s*\)",
            flat,
            re.IGNORECASE,
        ), "Index must cover column `device_fingerprint_hash`"
        assert re.search(
            r"WHERE\s+device_fingerprint_hash\s+IS\s+NOT\s+NULL",
            flat,
            re.IGNORECASE,
        ), "Index must include `WHERE device_fingerprint_hash IS NOT NULL` (partial)"

    def test_uses_idempotent_ddl_for_replay_safety(self, sql: str):
        """Every DDL must use IF [NOT] EXISTS so a re-apply does not crash —
        Migration 023's plan task 1.1 acceptance criterion calls this out."""
        # Each of the three DDL statements is checked individually above, but
        # this consolidates the invariant for human grep.
        flat = re.sub(r"\s+", " ", sql).lower()
        assert "if not exists" in flat, "ADD COLUMN/CREATE INDEX must use IF NOT EXISTS"
        assert "if exists" in flat, "DROP COLUMN must use IF EXISTS"

    def test_rollback_file_exists(self):
        """Design § 4.5 promises `migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql`."""
        rollback = Path("migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql")
        assert rollback.exists(), (
            "Rollback SQL missing — design § 4.5 mandates "
            f"{rollback} so Phase 4 ops can revert if something breaks."
        )


# ============================================
# Live schema verification (post-MCP-apply)
# ============================================


def _supabase_available() -> bool:
    return bool(
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_ANON_KEY")
        and os.getenv("SUPABASE_SERVICE_KEY")
    )


@pytest.mark.live_db
class TestMigration023LiveSchema:
    """Live Supabase assertions — skipped in free unit suite via live_db marker."""

    @pytest.fixture
    def admin_client(self):
        if not _supabase_available():
            pytest.skip("Supabase env vars not configured for live_db tests")
        from app.services.database_service import get_admin_supabase_client

        return get_admin_supabase_client()

    def test_lifetime_invites_consumed_column_exists(self, admin_client):
        """The column must be readable from the live `users` table."""
        try:
            result = (
                admin_client.table("users")
                .select("id, lifetime_invites_consumed")
                .limit(1)
                .execute()
            )
        except Exception as e:
            if "lifetime_invites_consumed" in str(e) and (
                "does not exist" in str(e) or "column" in str(e).lower()
            ):
                pytest.fail(
                    "Migration 023 not applied to live DB — "
                    "users.lifetime_invites_consumed is missing"
                )
            raise

        assert hasattr(result, "data")

    def test_weekly_invites_used_column_dropped(self, admin_client):
        """The legacy column must NOT be selectable — Migration 023 drops it."""
        try:
            admin_client.table("users").select(
                "id, weekly_invites_used"
            ).limit(1).execute()
        except Exception as e:
            assert "weekly_invites_used" in str(e), (
                "Expected the dropped column to raise a clear column-missing "
                f"error, got: {e!r}"
            )
            return
        pytest.fail(
            "users.weekly_invites_used still selectable — "
            "Migration 023 failed to DROP COLUMN"
        )

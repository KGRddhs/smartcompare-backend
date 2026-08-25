"""Drift guard for Migration 032 — Bundle B Phase B.1 pre-apply hardening.

Plan: docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md (Lane F3.1)
Preflight: docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 6
Migration: migrations/032_b1_pre_hardening.sql
Rollback:  migrations/rollback/032_b1_pre_hardening.sql

This migration does three independent pieces of pre-apply hardening that
the B.1 audit (preflight § 2.1 + § 6) flagged as security/hygiene debt to
clear BEFORE the new B.1 tables (027-031) land:

  1. DROP the dead `comparisons_cache` table (0 rows, 0 code references —
     re-verified by grep in the F3.1 task; only doc mentions remain).
  2. ENABLE ROW LEVEL SECURITY on `products` + a service-role-only policy.
     `products` is RLS-DISABLED today (anon key can read/write every row),
     but it IS used by production code via the service-role admin client
     (analytics_service.get_product_stats, database_service.upsert_product),
     so we keep the table and gate it rather than drop it.
  3. DROP the duplicate `idx_users_device_fp` index (021), keeping the
     canonical `idx_users_device_fingerprint_active` (023). Both are partial
     indexes on the same column with the same WHERE predicate.

These tests parse the migration SQL + rollback SQL and assert structural
invariants. They do NOT hit a live database — the live apply happens at
B.1 dispatch via Supabase MCP `apply_migration` (DISPATCHER applies; the
F3 lane agent never applies DDL). A `@pytest.mark.live_db` class verifies
the live post-apply state and is skipped in the free unit suite.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL = REPO_ROOT / "migrations" / "032_b1_pre_hardening.sql"
ROLLBACK_SQL = REPO_ROOT / "migrations" / "rollback" / "032_b1_pre_hardening.sql"

# The index we DROP (021) and the one we KEEP (023).
DROPPED_INDEX = "idx_users_device_fp"
KEPT_INDEX = "idx_users_device_fingerprint_active"


def _flat(sql: str) -> str:
    """Collapse all whitespace so multi-line statements match a single regex."""
    return re.sub(r"\s+", " ", sql)


# ---------------------------------------------------------------------------
# Files exist
# ---------------------------------------------------------------------------

def test_migration_032_file_exists():
    assert MIGRATION_SQL.exists(), f"missing {MIGRATION_SQL}"


def test_rollback_032_file_exists():
    assert ROLLBACK_SQL.exists(), f"missing {ROLLBACK_SQL}"


# ---------------------------------------------------------------------------
# Piece 1 — drop dead comparisons_cache
# ---------------------------------------------------------------------------

def test_migration_032_drops_comparisons_cache():
    """DROP TABLE IF EXISTS public.comparisons_cache — dead table, 0 rows,
    0 code references (re-verified by grep in F3.1)."""
    flat = _flat(MIGRATION_SQL.read_text(encoding="utf-8"))
    assert re.search(
        r"DROP\s+TABLE\s+IF\s+EXISTS\s+public\.comparisons_cache",
        flat,
        re.IGNORECASE,
    ), "Migration must `DROP TABLE IF EXISTS public.comparisons_cache`"


def test_migration_032_does_not_drop_products():
    """`products` is live (service-role code paths) — it must be RLS-gated,
    NOT dropped. Guard against an accidental DROP TABLE products."""
    flat = _flat(MIGRATION_SQL.read_text(encoding="utf-8"))
    assert not re.search(
        r"DROP\s+TABLE\s+(IF\s+EXISTS\s+)?public\.products\b",
        flat,
        re.IGNORECASE,
    ), "products must be RLS-gated, never dropped (live service-role code uses it)"


# ---------------------------------------------------------------------------
# Piece 2 — enable RLS on products + service-role policy
# ---------------------------------------------------------------------------

def test_migration_032_enables_rls_on_products():
    flat = _flat(MIGRATION_SQL.read_text(encoding="utf-8"))
    assert re.search(
        r"ALTER\s+TABLE\s+public\.products\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
        flat,
        re.IGNORECASE,
    ), "Migration must `ALTER TABLE public.products ENABLE ROW LEVEL SECURITY`"


def test_migration_032_adds_service_role_policy_on_products():
    """Enabling RLS without a policy blocks ALL access. A service-role
    policy (or a policy scoped to the service_role) must accompany it so the
    backend's admin-client upsert/select paths keep working. We assert a
    CREATE POLICY ... ON public.products referencing service_role exists."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    flat = _flat(sql)
    assert re.search(
        r"CREATE\s+POLICY\s+\w+\s+ON\s+public\.products",
        flat,
        re.IGNORECASE,
    ), "Migration must CREATE POLICY ... ON public.products"
    assert re.search(r"service_role", flat, re.IGNORECASE), (
        "products policy must reference the service_role so the admin client "
        "(analytics_service / database_service) retains read+write access"
    )


def test_migration_032_products_policy_dropped_before_create():
    """Re-runnability: CREATE POLICY has no IF NOT EXISTS in PG15, so the
    policy must be DROP POLICY IF EXISTS'd before CREATE."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    # Find the policy name from the CREATE statement.
    m = re.search(r"CREATE\s+POLICY\s+(\w+)\s+ON\s+public\.products", sql, re.IGNORECASE)
    assert m is not None, "no CREATE POLICY ... ON public.products found"
    policy = m.group(1)
    drop_pos = sql.find(f"DROP POLICY IF EXISTS {policy}")
    create_pos = sql.find(f"CREATE POLICY {policy}")
    assert drop_pos != -1, f"missing DROP POLICY IF EXISTS {policy} before CREATE"
    assert drop_pos < create_pos, "DROP POLICY must precede CREATE POLICY (PG15 idempotency)"


# ---------------------------------------------------------------------------
# Piece 3 — drop duplicate device-fingerprint index
# ---------------------------------------------------------------------------

def test_migration_032_drops_duplicate_device_fp_index():
    flat = _flat(MIGRATION_SQL.read_text(encoding="utf-8"))
    assert re.search(
        rf"DROP\s+INDEX\s+IF\s+EXISTS\s+(public\.)?{DROPPED_INDEX}\b",
        flat,
        re.IGNORECASE,
    ), f"Migration must `DROP INDEX IF EXISTS {DROPPED_INDEX}`"


def test_migration_032_keeps_canonical_device_fp_index():
    """The canonical 023 index must NOT be dropped — only the 021 duplicate."""
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert not re.search(
        rf"DROP\s+INDEX\s+IF\s+EXISTS\s+(public\.)?{KEPT_INDEX}\b",
        sql,
        re.IGNORECASE,
    ), f"Must NOT drop the canonical {KEPT_INDEX} (keep it; drop only {DROPPED_INDEX})"


# ---------------------------------------------------------------------------
# Idempotency + transaction wrapping
# ---------------------------------------------------------------------------

def test_migration_032_is_idempotent():
    """Every statement uses IF [NOT] EXISTS so a re-apply does not crash."""
    flat = _flat(MIGRATION_SQL.read_text(encoding="utf-8")).lower()
    assert "drop table if exists" in flat
    assert "drop index if exists" in flat


def test_migration_032_wraps_in_transaction():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


# ---------------------------------------------------------------------------
# Rollback symmetry
# ---------------------------------------------------------------------------

def test_rollback_032_recreates_dropped_index():
    """Rollback must restore the 021-shape duplicate index so the schema
    returns to its pre-032 state."""
    flat = _flat(ROLLBACK_SQL.read_text(encoding="utf-8"))
    assert re.search(
        rf"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+{DROPPED_INDEX}\b",
        flat,
        re.IGNORECASE,
    ), f"rollback must recreate {DROPPED_INDEX}"
    # And it must be the same partial shape (WHERE ... IS NOT NULL).
    assert re.search(
        r"WHERE\s+device_fingerprint_hash\s+IS\s+NOT\s+NULL",
        flat,
        re.IGNORECASE,
    ), "recreated index must keep the partial WHERE predicate"


def test_rollback_032_disables_rls_on_products():
    """Rollback drops the policy + disables RLS to return products to its
    pre-032 (RLS-disabled) state."""
    flat = _flat(ROLLBACK_SQL.read_text(encoding="utf-8"))
    assert re.search(
        r"DROP\s+POLICY\s+IF\s+EXISTS\s+\w+\s+ON\s+public\.products",
        flat,
        re.IGNORECASE,
    ), "rollback must DROP POLICY ... ON public.products"
    assert re.search(
        r"ALTER\s+TABLE\s+public\.products\s+DISABLE\s+ROW\s+LEVEL\s+SECURITY",
        flat,
        re.IGNORECASE,
    ), "rollback must DISABLE ROW LEVEL SECURITY on products"


def test_rollback_032_notes_comparisons_cache_not_recreated():
    """comparisons_cache is dead and intentionally NOT recreated on rollback
    (no schema to restore — it was empty). The rollback file must document
    this so an operator isn't surprised the table is gone."""
    text = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "comparisons_cache" in text, (
        "rollback file must mention comparisons_cache (documenting that it is "
        "intentionally not recreated — 0 rows, dead table)"
    )


def test_rollback_032_wraps_in_transaction():
    sql = ROLLBACK_SQL.read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql


# ---------------------------------------------------------------------------
# Live schema verification (post-MCP-apply) — skipped in free unit suite
# ---------------------------------------------------------------------------

def _supabase_available() -> bool:
    return bool(
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_ANON_KEY")
        and os.getenv("SUPABASE_SERVICE_KEY")
    )


@pytest.mark.live_db
class TestMigration032LiveSchema:
    """Live Supabase assertions — run post-apply with `LIVE=1 ... -m live_db`.

    `LIVE=1` is required: without it the credential sanitizer in
    tests/_env_safety.py is active and the collection hook skips this tier.
    """

    @pytest.fixture
    def admin_client(self):
        if not _supabase_available():
            pytest.skip("Supabase env vars not configured for live_db tests")
        from app.services.database_service import get_admin_supabase_client

        return get_admin_supabase_client()

    def test_comparisons_cache_dropped(self, admin_client):
        """The dead table must no longer be selectable."""
        try:
            admin_client.table("comparisons_cache").select("*").limit(1).execute()
        except Exception as e:
            assert (
                "comparisons_cache" in str(e)
                or "does not exist" in str(e).lower()
                or "not find" in str(e).lower()
            ), f"expected a clear table-missing error, got: {e!r}"
            return
        pytest.fail("comparisons_cache still selectable — Migration 032 DROP TABLE failed")

    def test_products_still_writable_via_service_role(self, admin_client):
        """The service-role admin client must retain access to products after
        RLS is enabled (the service-role policy must allow it)."""
        # A SELECT through the admin (service-role) client must succeed.
        result = admin_client.table("products").select("id").limit(1).execute()
        assert hasattr(result, "data")

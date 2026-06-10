-- Rollback for migration 032_b1_pre_hardening.sql
--
-- Reverts the two REVERSIBLE pieces of 032 and documents the one piece that
-- is intentionally NOT reverted.
--
-- Plan reference:
--   docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md (Lane F3.1)
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 6
--
-- Reversible:
--   2. products RLS — DROP the service-role policy + DISABLE row level
--      security, returning products to its pre-032 (RLS-disabled) state.
--   3. idx_users_device_fp — recreate the 021-shape duplicate partial index.
--
-- NOT reverted (documented, not executed):
--   1. comparisons_cache — this table was DEAD (0 rows, 0 code references,
--      dead since pre-Migration-010). There is no meaningful schema to
--      restore and nothing reads it, so the rollback intentionally does NOT
--      recreate it. If an operator genuinely needs it back (they should not),
--      the original DDL lived in docs/ARCHITECTURE_V3.md § "Table:
--      comparisons_cache". Recreating it would re-open the RLS-disabled
--      advisory, so this is deliberate.
--
-- Safe to re-run (IF EXISTS / IF NOT EXISTS guards on every statement).

BEGIN;

-- ---------------------------------------------------------------------------
-- Revert 2 — products RLS back to disabled (pre-032 state).
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS products_service_role_all ON public.products;
ALTER TABLE public.products DISABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- Revert 3 — recreate the 021-shape duplicate device-fingerprint index.
-- (Matches migrations/021_device_fingerprint_users.sql exactly.)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_device_fp
  ON public.users (device_fingerprint_hash)
  WHERE device_fingerprint_hash IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Revert 1 — comparisons_cache is intentionally NOT recreated. See header.
-- (No statement here on purpose. The table reference above keeps this file
-- grep-discoverable for operators reviewing what 032 touched.)
-- ---------------------------------------------------------------------------

COMMIT;

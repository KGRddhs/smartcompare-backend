-- Migration 032: Bundle B Phase B.1 — pre-apply hardening
--
-- Clears three pieces of schema security/hygiene debt that the B.1 audit
-- flagged (preflight § 2.1 + § 6) and that must land BEFORE the new B.1
-- tables (027-031) so the schema is clean when observability data starts
-- flowing.
--
-- Plan reference:
--   docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md (Lane F3.1)
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 6
--
-- Three independent pieces (order within the transaction is irrelevant —
-- they touch different objects):
--
-- 1. DROP dead `comparisons_cache`.
--    Production state (audited 2026-06-08): 0 rows, RLS DISABLED. Re-verified
--    2026-06-10 (F3.1 grep): zero code references in app/ or scripts/ — only
--    documentation mentions remain (docs/ARCHITECTURE_V3.md is stale design).
--    Dead since pre-Migration-010. Dropping it also clears the RLS-disabled
--    advisory for this table (anon key could read/write every row).
--
-- 2. ENABLE ROW LEVEL SECURITY on `products` + a service-role-only policy.
--    Production state: 0 rows but RLS DISABLED — anon key can read/write
--    every row (security boundary issue). Unlike comparisons_cache, `products`
--    IS used by live code: app/services/analytics_service.py:163
--    (get_product_stats) and app/services/database_service.py:510
--    (upsert_product) — BOTH via get_supabase_client() which returns the
--    service-role admin client. Service-role bypasses RLS, so enabling RLS +
--    a permissive service-role policy keeps those paths working while closing
--    the anon hole. We KEEP the table (not drop) because it has live readers.
--
--    Policy posture: a single permissive policy FOR ALL TO service_role.
--    No anon/authenticated policy at all → anon key gets zero access (the
--    desired closure). The backend admin client carries the service_role and
--    is unaffected (it bypasses RLS regardless, but the explicit policy makes
--    intent legible and survives any future move to a scoped client).
--
-- 3. DROP duplicate `idx_users_device_fp`.
--    Two partial indexes cover users.device_fingerprint_hash with the same
--    WHERE predicate: idx_users_device_fp (Migration 021) and
--    idx_users_device_fingerprint_active (Migration 023). They are redundant.
--    Keep the 023 canonical name (referenced by tests/test_migration_023.py
--    + the anti-farming cap query); drop the 021 one.
--
-- Idempotent: DROP ... IF EXISTS + DROP POLICY IF EXISTS before CREATE POLICY
-- (Postgres 15 has no CREATE POLICY IF NOT EXISTS).
-- Rollback: migrations/rollback/032_b1_pre_hardening.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Drop dead comparisons_cache (0 rows, 0 code refs).
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS public.comparisons_cache;

-- ---------------------------------------------------------------------------
-- 2. Enable RLS on products + service-role-only policy.
-- ---------------------------------------------------------------------------
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

-- DROP-then-CREATE for re-runnability (PG15 has no CREATE POLICY IF NOT EXISTS).
DROP POLICY IF EXISTS products_service_role_all ON public.products;
CREATE POLICY products_service_role_all
  ON public.products
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 3. Drop the duplicate device-fingerprint index (021), keep 023 canonical.
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS public.idx_users_device_fp;

COMMENT ON POLICY products_service_role_all ON public.products IS
  'Service-role-only full access. RLS enabled to close the anon read/write '
  'hole (preflight § 6). Backend uses the service-role admin client '
  '(analytics_service / database_service); anon/authenticated get no policy '
  'and therefore no access.';

COMMIT;

-- Rollback for migration 030_verdict_critiques.sql
--
-- Drops the verdict_critiques table + its indexes. No RLS policy was
-- created (internal observability — no user-facing SELECT path),
-- so the rollback is shorter than 028/029.
--
-- IMPORTANT: this is destructive — any self-critique scores collected
-- since migration apply are permanently lost. Export before rollback:
--
--   COPY (SELECT row_to_json(vc) FROM public.verdict_critiques vc)
--     TO '/tmp/vc_backup_<date>.jsonl';
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.4

BEGIN;

-- No DROP POLICY needed — none were created (service-role-only access).
-- Indexes drop automatically with the table, but explicit DROP makes
-- the rollback diff easier to read.

DROP INDEX IF EXISTS public.idx_vc_created_at;
DROP INDEX IF EXISTS public.idx_vc_low_align;
DROP INDEX IF EXISTS public.idx_vc_regenerated;
DROP INDEX IF EXISTS public.idx_vc_comparison_id;

DROP TABLE IF EXISTS public.verdict_critiques;

COMMIT;

-- Rollback for migration 028_pain_workflow_events.sql
--
-- Drops the pain_workflow_events table + its indexes + RLS policy.
-- Safe to re-run (IF EXISTS guards on every drop).
--
-- IMPORTANT: this is destructive — any pain-workflow signal history
-- collected since migration apply is permanently lost. Export to
-- jsonl before running rollback if recovery may be needed:
--
--   COPY (SELECT row_to_json(pwe) FROM public.pain_workflow_events pwe)
--     TO '/tmp/pwe_backup_<date>.jsonl';
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.3

BEGIN;

-- DROP POLICY before DROP TABLE so PostgreSQL doesn't complain about
-- orphaned policies on missing tables (rare edge case but harmless).
DROP POLICY IF EXISTS pwe_own_select ON public.pain_workflow_events;

-- Indexes are dropped automatically when the table is dropped, but
-- explicit DROP makes the rollback diff easier to read.
DROP INDEX IF EXISTS public.idx_pwe_recent;
DROP INDEX IF EXISTS public.idx_pwe_comparison_id;
DROP INDEX IF EXISTS public.idx_pwe_user_workflow_time;
DROP INDEX IF EXISTS public.idx_pwe_workflow_name;

DROP TABLE IF EXISTS public.pain_workflow_events;

COMMIT;

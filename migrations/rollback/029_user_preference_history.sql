-- Rollback for migration 029_user_preference_history.sql
--
-- Drops the user_preference_history table + its indexes + RLS policy.
-- Safe to re-run (IF EXISTS guards on every drop).
--
-- IMPORTANT: this is destructive — any preference snapshots collected
-- since migration apply are permanently lost. The current
-- users.preferences row is preserved (this table is a HISTORY log,
-- not the source of truth). Export before rollback if recovery may
-- be needed:
--
--   COPY (SELECT row_to_json(uph)
--           FROM public.user_preference_history uph)
--     TO '/tmp/uph_backup_<date>.jsonl';
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.2

BEGIN;

-- DROP POLICY before DROP TABLE.
DROP POLICY IF EXISTS uph_own_select ON public.user_preference_history;

-- Indexes are dropped automatically with the table, but explicit
-- DROP makes the rollback diff easier to read.
DROP INDEX IF EXISTS public.idx_uph_preferences_gin;
DROP INDEX IF EXISTS public.idx_uph_change_source;
DROP INDEX IF EXISTS public.idx_uph_user_created;

DROP TABLE IF EXISTS public.user_preference_history;

COMMIT;

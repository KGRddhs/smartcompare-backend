-- Rollback for migration 031_eval_runs.sql
--
-- Drops the eval_runs table + its indexes. No RLS policy was created
-- (internal observability — service-role only), so the rollback is
-- shorter than 028/029.
--
-- IMPORTANT: this is destructive — any eval-run history collected
-- since migration apply is permanently lost. Export before rollback:
--
--   COPY (SELECT row_to_json(er) FROM public.eval_runs er)
--     TO '/tmp/eval_runs_backup_<date>.jsonl';
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.5

BEGIN;

-- No DROP POLICY needed — none were created.

DROP INDEX IF EXISTS public.idx_eval_runs_gold_truth_version;
DROP INDEX IF EXISTS public.idx_eval_runs_pass_rate;
DROP INDEX IF EXISTS public.idx_eval_runs_kind_created;

DROP TABLE IF EXISTS public.eval_runs;

COMMIT;

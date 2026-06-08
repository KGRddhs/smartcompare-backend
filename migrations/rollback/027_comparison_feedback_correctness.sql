-- Rollback for migration 027_comparison_feedback_correctness.sql
--
-- Drops the 3 per-axis correctness columns + their CHECK constraints
-- and the partial index. Production state at migration apply time
-- (2026-06-08 audit) was 0 rows in comparison_feedback, so this
-- rollback is fully reversible without data loss when run promptly
-- after a botched 027 apply.
--
-- POST-PROD WARNING: once B.3 wires the per-axis UI and feedback rows
-- accumulate non-null values, rollback DESTROYS that signal. Export
-- before running:
--
--   COPY (SELECT id, winner_correct, price_correct, specs_correct
--           FROM public.comparison_feedback
--          WHERE winner_correct IS NOT NULL
--             OR price_correct  IS NOT NULL
--             OR specs_correct  IS NOT NULL)
--     TO '/tmp/feedback_correctness_backup_<date>.csv' WITH CSV HEADER;
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.1

BEGIN;

-- Drop CHECK constraints before columns so dependency order is explicit.
ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_winner_correct_check;
ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_price_correct_check;
ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_specs_correct_check;

DROP INDEX IF EXISTS public.idx_comparison_feedback_correctness_present;

ALTER TABLE public.comparison_feedback
  DROP COLUMN IF EXISTS winner_correct;
ALTER TABLE public.comparison_feedback
  DROP COLUMN IF EXISTS price_correct;
ALTER TABLE public.comparison_feedback
  DROP COLUMN IF EXISTS specs_correct;

COMMIT;

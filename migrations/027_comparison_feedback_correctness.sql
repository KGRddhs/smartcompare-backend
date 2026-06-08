-- Migration 027: Bundle B Phase B.1 — comparison_feedback per-axis correctness
--
-- Adds 3 nullable 3-state columns to comparison_feedback so the eval loop
-- (design § 6) can correlate user-reported per-axis correctness with the
-- deterministic scoring / factual outputs. Each is nullable so the
-- existing fast-path thumbs-up/down feedback continues to work without
-- mandatory per-axis prompting.
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.1
--   docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6
--
-- 3-state enum chosen over boolean to capture "unsure" — the design § 6
-- failure-mode catalog calls out cases where users don't have enough
-- domain knowledge to call one product objectively better, but their
-- abandonment signal is still useful as a soft negative.
--
-- Note on production state (audited 2026-06-08): comparison_feedback
-- table has 0 rows in production. No historical backfill required —
-- columns default to NULL on existing rows (vacuously safe).
--
-- Idempotent: every ALTER uses IF NOT EXISTS.
-- Rollback: migrations/rollback/027_comparison_feedback_correctness.sql

BEGIN;

ALTER TABLE public.comparison_feedback
  ADD COLUMN IF NOT EXISTS winner_correct text NULL;

ALTER TABLE public.comparison_feedback
  ADD COLUMN IF NOT EXISTS price_correct text NULL;

ALTER TABLE public.comparison_feedback
  ADD COLUMN IF NOT EXISTS specs_correct text NULL;

-- 3-state enum enforced via CHECK constraints. NULL allowed so that
-- existing thumbs-up/down feedback (useful + mattered_most) keeps
-- working without per-axis prompting required.
--
-- NOTE: Postgres ALTER TABLE … ADD CONSTRAINT does NOT support
-- "IF NOT EXISTS" in 12-15 ranges. We DROP-then-ADD idempotently
-- so re-runs don't fail. (16+ added IF NOT EXISTS but Supabase
-- prod is on 15 as of audit.)

ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_winner_correct_check;
ALTER TABLE public.comparison_feedback
  ADD CONSTRAINT comparison_feedback_winner_correct_check
    CHECK (winner_correct IS NULL OR winner_correct IN ('correct','wrong','unsure'));

ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_price_correct_check;
ALTER TABLE public.comparison_feedback
  ADD CONSTRAINT comparison_feedback_price_correct_check
    CHECK (price_correct IS NULL OR price_correct IN ('correct','wrong','unsure'));

ALTER TABLE public.comparison_feedback
  DROP CONSTRAINT IF EXISTS comparison_feedback_specs_correct_check;
ALTER TABLE public.comparison_feedback
  ADD CONSTRAINT comparison_feedback_specs_correct_check
    CHECK (specs_correct IS NULL OR specs_correct IN ('correct','wrong','unsure'));

-- Partial index for the eval loop — only rows with at least one non-null
-- per-axis signal are interesting for the correctness aggregator. Drops
-- the index size by ~95% once feedback flows in at scale (most rows
-- will be NULL across all three until B.3 wires the per-axis UI).
CREATE INDEX IF NOT EXISTS idx_comparison_feedback_correctness_present
  ON public.comparison_feedback (created_at DESC)
  WHERE (winner_correct IS NOT NULL
      OR price_correct  IS NOT NULL
      OR specs_correct  IS NOT NULL);

COMMENT ON COLUMN public.comparison_feedback.winner_correct IS
  '3-state: ''correct'' | ''wrong'' | ''unsure''. NULL means user did not '
  'provide a per-axis signal (only the boolean ''useful'' thumbs-up/down).';

COMMENT ON COLUMN public.comparison_feedback.price_correct IS
  '3-state: ''correct'' | ''wrong'' | ''unsure''. Used by the eval loop '
  'to correlate Bahrain retail-price extraction accuracy with user truth.';

COMMENT ON COLUMN public.comparison_feedback.specs_correct IS
  '3-state: ''correct'' | ''wrong'' | ''unsure''. Used by the eval loop '
  'to track spec-extraction quality (correct field counts / units).';

COMMIT;

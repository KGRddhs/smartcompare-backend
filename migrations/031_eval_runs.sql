-- Migration 031: Bundle B Phase B.1 — eval_runs
--
-- Aggregate record of eval-loop sessions (CI runs of the 50/200-query
-- gold set, nightly cron runs, manual dispatcher invocations). Each
-- row captures the pass-rate + per-axis averages + p50/p95 wall-time
-- + the git SHA of the gold-truth file in effect.
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.5
--   docs/plans/2026-06-08-A-validation-matrix-50q.md (50-query merge gate)
--   docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6 (eval loop)
--
-- gold_truth_version chosen: git SHA (team-lead Q3 decision 2026-06-08).
-- A git SHA pins the exact data/validation_gold_truth.json content
-- without needing a content hash — reproducible against the repo.
--
-- run_kind taxonomy:
--   - 'ci_pr'         per-PR eval run on the feature branch
--   - 'nightly'       daily cron against main
--   - 'manual'        dispatcher-invoked run (M2 integration gate, ad-hoc)
--   - 'staging_smoke' post-deploy smoke against Railway preview
--
-- RLS posture (per preflight § 6):
--   - NO user-facing SELECT policy — internal observability only.
--     Same posture as verdict_critiques (Migration 030). Admin
--     dashboard reads via service-role.
--   - INSERT/UPDATE/DELETE: service-role only.
--
-- No FKs: eval_runs is a standalone observability table. It does not
-- reference users / comparisons / etc, so it has no cascade behaviour.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
-- Rollback: migrations/rollback/031_eval_runs.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.eval_runs (
  id                  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  run_kind            text          NOT NULL,
  gold_truth_version  text          NOT NULL,
  queries_total       integer       NOT NULL,
  queries_passing     integer       NOT NULL,
  pass_rate           numeric(5,4)  NOT NULL,
  axis_avg_price      numeric(5,4)  NULL,
  axis_avg_specs      numeric(5,4)  NULL,
  axis_avg_winner     numeric(5,4)  NULL,
  axis_avg_factual    numeric(5,4)  NULL,
  wall_p50_ms         integer       NULL,
  wall_p95_ms         integer       NULL,
  metadata            jsonb         NULL,
  created_at          timestamptz   NOT NULL DEFAULT now(),

  CONSTRAINT eval_runs_run_kind_check CHECK (run_kind IN (
    'ci_pr',
    'nightly',
    'manual',
    'staging_smoke'
  )),

  -- pass_rate is bounded [0..1] by definition.
  CONSTRAINT eval_runs_pass_rate_range
    CHECK (pass_rate >= 0 AND pass_rate <= 1),

  -- Per-axis averages are also bounded [0..1] when present.
  CONSTRAINT eval_runs_axis_avg_price_range
    CHECK (axis_avg_price IS NULL OR (axis_avg_price >= 0 AND axis_avg_price <= 1)),
  CONSTRAINT eval_runs_axis_avg_specs_range
    CHECK (axis_avg_specs IS NULL OR (axis_avg_specs >= 0 AND axis_avg_specs <= 1)),
  CONSTRAINT eval_runs_axis_avg_winner_range
    CHECK (axis_avg_winner IS NULL OR (axis_avg_winner >= 0 AND axis_avg_winner <= 1)),
  CONSTRAINT eval_runs_axis_avg_factual_range
    CHECK (axis_avg_factual IS NULL OR (axis_avg_factual >= 0 AND axis_avg_factual <= 1)),

  -- Passing count can't exceed total.
  CONSTRAINT eval_runs_passing_lte_total
    CHECK (queries_passing >= 0 AND queries_passing <= queries_total)
);

ALTER TABLE public.eval_runs ENABLE ROW LEVEL SECURITY;

-- NO SELECT policy — internal observability. Same posture as
-- verdict_critiques per preflight § 6.

-- Indexes per preflight § 4.5.
--
-- 1) Time-series scan per run_kind ("latest 30 nightly runs"):
CREATE INDEX IF NOT EXISTS idx_eval_runs_kind_created
  ON public.eval_runs (run_kind, created_at DESC);

-- 2) Pass-rate alarm scan ("find runs below 0.80 gate"):
CREATE INDEX IF NOT EXISTS idx_eval_runs_pass_rate
  ON public.eval_runs (pass_rate);

-- 3) gold-truth-version drift analysis ("did this gold-truth update
--    change the pass rate?"):
CREATE INDEX IF NOT EXISTS idx_eval_runs_gold_truth_version
  ON public.eval_runs (gold_truth_version);

-- Documentation.
COMMENT ON TABLE public.eval_runs IS
  'Aggregate record of eval-loop sessions. Each row = one execution '
  'of scripts/run_validation_matrix.py. Service-role-only writes + '
  'reads; admin dashboard aggregates across rows.';

COMMENT ON COLUMN public.eval_runs.run_kind IS
  '4-value enum: ci_pr | nightly | manual | staging_smoke. See '
  'migration 031 source for intent per value.';

COMMENT ON COLUMN public.eval_runs.gold_truth_version IS
  'Git SHA of data/validation_gold_truth.json content as of the run. '
  'Used for ratification-vs-run drift attribution.';

COMMENT ON COLUMN public.eval_runs.metadata IS
  'Free-form jsonb for run context: branch name, Railway deploy SHA, '
  'runner version, failing query IDs, etc. Schema-on-read.';

COMMIT;

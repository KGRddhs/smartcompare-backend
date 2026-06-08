-- Migration 030: Bundle B Phase B.1 — verdict_critiques
--
-- Records the GPT-4o-mini self-critique scores (design § 6) for every
-- shipped verdict so the eval loop can correlate "low align score →
-- user feedback says wrong / unsure." Powers the regenerate-on-low-score
-- guard: any axis < 7/10 triggers a re-run of the verdict prompt with
-- explicit feedback ("your previous verdict scored 4/10 on
-- pain_workflow_alignment; regenerate following the 8 workflow
-- constraints").
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.4
--   docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6
--
-- 5 critique axes (0..10 integer, NULLable for partial critiques):
--   bias_score              — bias toward one product without scoring evidence
--   vagueness_score         — generic statements that don't reference the
--                              specific products at hand
--   hedging_score           — "could be," "might want to," "depending on"
--   missing_citation_score  — claims without source-count grounding
--   pain_workflow_align_score — does the verdict honor the cohort's top-3
--                              pain workflows from data/pain_workflow_priors.json
--
-- RLS posture (per preflight § 6 + team-lead Q2 decision 2026-06-08):
--   - NO user-facing SELECT policy — internal observability only.
--     Admin dashboard reads via service-role. B.3 reasoning-depth
--     experiment may add a transparency surface later if self-critique
--     proves to lift quality.
--   - INSERT/UPDATE/DELETE: service-role only.
--
-- FK ON DELETE:
--   - comparison_id → CASCADE (purging a comparison purges its critique;
--     no analytic value in dangling critique rows pointing at gone IDs)
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
-- Rollback: migrations/rollback/030_verdict_critiques.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.verdict_critiques (
  id                         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  comparison_id              uuid        NOT NULL REFERENCES public.comparisons(id) ON DELETE CASCADE,

  -- 5 critique axes — integers 0..10, nullable for partial-critique passes.
  bias_score                 integer     NULL,
  vagueness_score            integer     NULL,
  hedging_score              integer     NULL,
  missing_citation_score     integer     NULL,
  pain_workflow_align_score  integer     NULL,

  -- Regeneration trace — what the critic did about a low score.
  regenerated                boolean     NOT NULL DEFAULT false,
  regen_reason               text        NULL,

  -- Cost trace for budget audit (design § 6: ~$0.001/comparison budget).
  critic_model               text        NOT NULL,
  critic_tokens_used         integer     NULL,
  created_at                 timestamptz NOT NULL DEFAULT now(),

  -- All 5 axes constrained to the 0..10 inclusive range when present.
  CONSTRAINT vc_bias_score_range
    CHECK (bias_score IS NULL OR bias_score BETWEEN 0 AND 10),
  CONSTRAINT vc_vagueness_score_range
    CHECK (vagueness_score IS NULL OR vagueness_score BETWEEN 0 AND 10),
  CONSTRAINT vc_hedging_score_range
    CHECK (hedging_score IS NULL OR hedging_score BETWEEN 0 AND 10),
  CONSTRAINT vc_missing_citation_score_range
    CHECK (missing_citation_score IS NULL OR missing_citation_score BETWEEN 0 AND 10),
  CONSTRAINT vc_pain_workflow_align_score_range
    CHECK (pain_workflow_align_score IS NULL OR pain_workflow_align_score BETWEEN 0 AND 10),

  -- If regenerated=true, regen_reason should explain why (analytics).
  -- Not strictly required by the schema (NULL allowed) but helpful.
  CONSTRAINT vc_regen_reason_when_regenerated
    CHECK (regenerated = false OR regen_reason IS NOT NULL)
);

ALTER TABLE public.verdict_critiques ENABLE ROW LEVEL SECURITY;

-- NO SELECT policy — internal observability only. Service-role bypasses
-- RLS. If a user-facing transparency tab ships in B.3+, add a SELECT
-- policy at that point gated on:
--   USING (auth.uid() = (SELECT user_id FROM public.comparisons WHERE id = verdict_critiques.comparison_id))

-- Indexes per preflight § 4.4.
--
-- 1) Single-comparison lookup (post-critique read after regeneration):
CREATE INDEX IF NOT EXISTS idx_vc_comparison_id
  ON public.verdict_critiques (comparison_id);

-- 2) Regeneration-rate aggregator (admin dashboard: "how often is
--    self-critique firing the regeneration path?"):
CREATE INDEX IF NOT EXISTS idx_vc_regenerated
  ON public.verdict_critiques (regenerated)
  WHERE regenerated = true;

-- 3) Low-align-score scan (eval loop: "find verdicts where the model
--    failed to honor the cohort's pain workflows"):
CREATE INDEX IF NOT EXISTS idx_vc_low_align
  ON public.verdict_critiques (pain_workflow_align_score)
  WHERE pain_workflow_align_score IS NOT NULL
    AND pain_workflow_align_score < 7;

-- 4) Time-series for budget burn analysis (token usage per day):
CREATE INDEX IF NOT EXISTS idx_vc_created_at
  ON public.verdict_critiques (created_at DESC);

-- Documentation.
COMMENT ON TABLE public.verdict_critiques IS
  'Per-verdict GPT-4o-mini self-critique scores (design § 6). Internal '
  'observability — service-role-only writes + reads. Admin dashboard '
  'aggregates across rows; users never see individual critique data.';

COMMENT ON COLUMN public.verdict_critiques.bias_score IS
  '0..10 — verdict bias toward one product without supporting evidence. '
  '0=heavily biased, 10=balanced. NULL=axis not evaluated this run.';

COMMENT ON COLUMN public.verdict_critiques.pain_workflow_align_score IS
  '0..10 — does the verdict honor the cohort''s top-3 pain workflows '
  'from data/pain_workflow_priors.json? Below 7 triggers regeneration.';

COMMENT ON COLUMN public.verdict_critiques.regen_reason IS
  'Free-text explanation for regeneration. Required by CHECK when '
  'regenerated=true. Typical values: ''bias<7'', ''vagueness<7'', '
  '''pain_workflow_align<7''. Combine with the axis cols for full context.';

COMMIT;

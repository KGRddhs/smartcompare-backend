-- Migration 028: Bundle B Phase B.1 — pain_workflow_events
--
-- Records per-comparison observed pain-workflow signals (abandonment,
-- re-query within 5min, share+immediate-purchase, long dwell) so the
-- Living Prompt System (design § 6) can refresh `data/pain_workflow_priors.json`
-- weights from observed behaviour rather than survey aggregate alone.
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.3
--   docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6
--
-- Source of canonical workflow names:
--   data/pain_workflow_priors.json — 8 ranked workflows shipped in Sprint A-L4.1.
--   The CHECK constraint MUST stay synchronised with that file's workflow names.
--
-- RLS posture (per preflight § 6):
--   - SELECT gated on auth.uid() = user_id (users can read their own history)
--   - INSERT/UPDATE/DELETE: service-role only (no client-side policy)
--     so the audit trail is tamper-resistant from the mobile/web client
--
-- FK ON DELETE:
--   - user_id        → CASCADE  (delete user → delete their workflow events)
--   - comparison_id  → SET NULL (preserve workflow events when comparison
--                                is purged via /history DELETE; the signal
--                                "user abandoned a comparison" is still
--                                useful even if the comparison record is gone)
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
-- Rollback: migrations/rollback/028_pain_workflow_events.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.pain_workflow_events (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  comparison_id   uuid        NULL     REFERENCES public.comparisons(id) ON DELETE SET NULL,
  workflow_name   text        NOT NULL,
  signal_type     text        NOT NULL,
  signal_payload  jsonb       NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),

  -- Canonical workflow names — sync with data/pain_workflow_priors.json.
  -- A drift here means the prior aggregator silently drops the row;
  -- consider an integration test that asserts equality.
  CONSTRAINT pwe_workflow_name_check CHECK (workflow_name IN (
    'close_option_paralysis',
    'too_many_specs',
    'value_budget_uncertainty',
    'trust_paralysis',
    'post_decision_regret',
    'brand_loyalty_vs_evidence',
    'warranty_aftersales_missing',
    'decision_speed'
  )),

  -- Signal type taxonomy — extend as instrumentation grows.
  CONSTRAINT pwe_signal_type_check CHECK (signal_type IN (
    'abandonment',              -- user exited Results screen without tapping share/save/CTA
    'requery_within_5min',      -- new compare request within 5min of the first one
    'share_then_no_purchase',   -- share event but no subsequent purchase intent click
    'long_dwell',               -- > 60s on Results without scrolling (cognitive lock)
    'tldr_only',                -- user only viewed the first verdict sentence (decision_speed positive)
    'expanded_all_specs',       -- user opened the full spec accordion (too_many_specs negative)
    'compared_again_same_pair', -- ran the exact same compare again (close_option_paralysis positive)
    'changed_priority'          -- user edited preferences mid-decision (brand_loyalty + value)
  ))
);

ALTER TABLE public.pain_workflow_events ENABLE ROW LEVEL SECURITY;

-- SELECT: users read their own workflow events. Service-role bypasses RLS.
CREATE POLICY pwe_own_select
  ON public.pain_workflow_events
  FOR SELECT
  USING (auth.uid() = user_id);

-- No INSERT/UPDATE/DELETE policy for authenticated/anon — only the service
-- role (via the backend) writes here. This keeps the audit-trail tamper-
-- resistant from the mobile client even if a client JWT is compromised.

-- Indexes per preflight § 4.3 — covered by the canonical access patterns:
--   1) Workflow weight aggregator: SUM by workflow_name → date bucket
--   2) Per-user pain history (analytics dashboard): user_id + workflow_name + time DESC
--   3) Comparison-to-workflow join: comparison_id lookup
--
-- DISPATCHER CORRECTION 2026-06-10 (applied prod DDL): the original draft had
-- a single-column idx_pwe_workflow_name AND a partial idx_pwe_recent gated on
-- `WHERE created_at > now() - interval '90 days'`. Postgres rejects volatile
-- functions in an index predicate (now() is STABLE, not IMMUTABLE → ERROR
-- 42P17), so the whole transaction rolled back. The fix collapses both into a
-- single composite idx_pwe_workflow_time (workflow_name, created_at DESC):
--   * its leading column serves the workflow-weight aggregator (was
--     idx_pwe_workflow_name — now redundant, dropped),
--   * (workflow_name, created_at DESC) serves the recent-events scan via a
--     normal `WHERE created_at > ...` at query time (was idx_pwe_recent — the
--     90-day window is a query-time filter, not a partial-index predicate).
-- Net: same query coverage, one fewer index, no volatile predicate. If index
-- size ever matters at volume, revisit with BRIN or a scheduled reindex.
-- This file now matches the live prod schema exactly.

CREATE INDEX IF NOT EXISTS idx_pwe_workflow_time
  ON public.pain_workflow_events (workflow_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pwe_user_workflow_time
  ON public.pain_workflow_events (user_id, workflow_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pwe_comparison_id
  ON public.pain_workflow_events (comparison_id)
  WHERE comparison_id IS NOT NULL;

-- Documentation comments — visible via psql \d+ and Supabase dashboard.
COMMENT ON TABLE public.pain_workflow_events IS
  'Per-comparison observed pain-workflow signals. Feeds the Living Prompt System '
  'weight refresh (design § 6). Service-role-only writes; users SELECT own rows.';

COMMENT ON COLUMN public.pain_workflow_events.workflow_name IS
  'Canonical name from data/pain_workflow_priors.json (8 ranked workflows). '
  'CHECK constraint must stay synchronised — drift drops rows silently.';

COMMENT ON COLUMN public.pain_workflow_events.signal_type IS
  'Behaviour type that triggered this workflow signal. See migration 028 source '
  'for the canonical enum + intended semantics per type.';

COMMENT ON COLUMN public.pain_workflow_events.signal_payload IS
  'Optional per-signal context. Schema-on-read JSON; typical keys: '
  'dwell_ms, requery_text, scroll_depth, expanded_sections. Never user PII.';

COMMIT;

-- ---------------------------------------------------------------------------
-- Sample inserts (DEV / staging only — comment out before applying to prod)
-- ---------------------------------------------------------------------------
-- These 3 inserts exercise each of the 3 most common signal-type+workflow
-- pairings so the prior aggregator can be smoke-tested immediately after
-- migration apply. Replace the user_id + comparison_id UUIDs with real
-- values from your dev project before uncommenting.
--
-- INSERT INTO public.pain_workflow_events
--   (user_id, comparison_id, workflow_name, signal_type, signal_payload)
-- VALUES
--   ('00000000-0000-0000-0000-000000000001'::uuid,
--    '11111111-1111-1111-1111-111111111111'::uuid,
--    'close_option_paralysis',
--    'compared_again_same_pair',
--    '{"first_compare_ts": "2026-06-08T14:00:00Z", "second_compare_ts": "2026-06-08T14:03:00Z"}'::jsonb),
--
--   ('00000000-0000-0000-0000-000000000001'::uuid,
--    '22222222-2222-2222-2222-222222222222'::uuid,
--    'too_many_specs',
--    'expanded_all_specs',
--    '{"sections_expanded": 6, "dwell_ms": 47200}'::jsonb),
--
--   ('00000000-0000-0000-0000-000000000002'::uuid,
--    '33333333-3333-3333-3333-333333333333'::uuid,
--    'decision_speed',
--    'tldr_only',
--    '{"dwell_ms": 4200, "scroll_depth_pct": 12}'::jsonb);

-- Migration 029: Bundle B Phase B.1 — user_preference_history
--
-- Append-only log of `users.preferences` jsonb snapshots so the eval loop
-- can correlate "preferences changed at T1 → verdicts at T2 felt
-- better/worse." Powers the prior aggregator's "did this user shift
-- their priorities in a way that explains the rating dip?" attribution
-- analysis. Also feeds B.2 few-shot example rotation (top-decile
-- verdicts get more weight when the user's preferences match the
-- preference snapshot in effect when the verdict was generated).
--
-- Plan reference:
--   docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md § 4.2
--   docs/plans/2026-06-08-backend-comparison-overhaul-design.md § 6
--
-- RLS posture (per preflight § 6):
--   - SELECT gated on auth.uid() = user_id (users read own history)
--   - INSERT/UPDATE/DELETE: service-role only (tamper-resistant audit)
--
-- FK ON DELETE:
--   - user_id → CASCADE (App Store account-deletion requirement; the
--     migration 025 cascade extension covers this implicitly through
--     RLS scope, but explicit CASCADE makes the FK-level guarantee
--     match the function-level promise)
--
-- change_source taxonomy (team-lead-ratified 2026-06-08, see
-- preflight § 9 Q4):
--   - 'manual_edit'              user-driven preference change via EditProfile UI
--   - 'cohort_default'           inferred-from-cohort backfill on first compare
--   - 'onboarding_initial'       17-step onboarding first-time write
--   - 'import_from_demographics' demographics_profile → preferences inference
--   - 'system_correction'        backend repair of malformed preference row
--
-- Initial backfill from existing users.preferences happens via a
-- separate ad-hoc INSERT (see end of file, commented for safety).
-- Production state at audit (2026-06-08) was 16 users → 16 backfill
-- inserts, runs in < 1s.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
-- Rollback: migrations/rollback/029_user_preference_history.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_preference_history (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  preferences   jsonb       NOT NULL,
  change_source text        NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),

  -- Canonical change_source enum (preflight § 9 Q4 ratified). Adding
  -- a new source requires a follow-up migration that updates this
  -- CHECK — caller code must NOT silently insert unknown values.
  CONSTRAINT uph_change_source_check CHECK (change_source IN (
    'manual_edit',
    'cohort_default',
    'onboarding_initial',
    'import_from_demographics',
    'system_correction'
  ))
);

ALTER TABLE public.user_preference_history ENABLE ROW LEVEL SECURITY;

-- SELECT: users read their own history. Service-role bypasses RLS for
-- the eval loop and admin dashboard.
CREATE POLICY uph_own_select
  ON public.user_preference_history
  FOR SELECT
  USING (auth.uid() = user_id);

-- No INSERT/UPDATE/DELETE policy — service-role only. Append-only
-- audit semantics: once a snapshot is recorded, it cannot be edited
-- or deleted from the client even if the JWT is compromised.

-- Indexes per preflight § 4.2.
--
-- 1) Per-user history scan (analytics dashboard, eval-loop join):
CREATE INDEX IF NOT EXISTS idx_uph_user_created
  ON public.user_preference_history (user_id, created_at DESC);

-- 2) Change-source aggregator (B.2 wants to know "of all
--    preference snapshots, what share came from cohort inference?"):
CREATE INDEX IF NOT EXISTS idx_uph_change_source
  ON public.user_preference_history (change_source);

-- 3) GIN over preferences jsonb so the few-shot rotator can query
--    "find all snapshots where preferences->>'priority_1' = 'price'":
CREATE INDEX IF NOT EXISTS idx_uph_preferences_gin
  ON public.user_preference_history USING gin (preferences);

-- Documentation.
COMMENT ON TABLE public.user_preference_history IS
  'Append-only log of users.preferences snapshots. Feeds the Living '
  'Prompt System eval-loop correlation analysis (design § 6). '
  'Service-role-only writes; users SELECT own rows.';

COMMENT ON COLUMN public.user_preference_history.change_source IS
  '5-value enum identifying which path produced the snapshot. '
  'See migration 029 source for canonical list + intent per value.';

COMMENT ON COLUMN public.user_preference_history.preferences IS
  'Full jsonb snapshot of users.preferences at write time. Mirrors '
  'the users.preferences default (''{}''::jsonb) when user has not '
  'completed onboarding yet.';

COMMIT;

-- ---------------------------------------------------------------------------
-- One-shot initial backfill (DEV / staging — comment out before prod apply)
-- ---------------------------------------------------------------------------
-- Run this AFTER the table + indexes land. Pushes the current snapshot
-- for every user who has populated preferences (skips '{}'::jsonb to
-- avoid noise from never-onboarded accounts). Production has 16 users
-- as of 2026-06-08; ETA < 1s. Re-running is idempotent ONLY if you
-- guard on the WHERE NOT EXISTS clause inside the SELECT.
--
-- INSERT INTO public.user_preference_history
--   (user_id, preferences, change_source)
-- SELECT u.id, u.preferences, 'system_correction'
--   FROM public.users u
--  WHERE u.preferences IS NOT NULL
--    AND u.preferences != '{}'::jsonb
--    AND NOT EXISTS (
--      SELECT 1 FROM public.user_preference_history h WHERE h.user_id = u.id
--    );

-- Migration 038: users consent capture — ToS acceptance + 13+ age attestation
--
-- W3-16. Until now no account-creating path recorded that the user accepted the
-- Terms or attested to being 13 or older: POST /api/v1/auth/register and the
-- first-sign-in branch of POST /api/v1/auth/social-login inserted only
-- {id, email, subscription_tier} / {id, email, auth_provider, subscription_tier}.
-- The mobile client now sends terms_accepted / terms_version / age_attested; the
-- backend turns them into a consent record (app/services/consent_service.py).
--
-- This adds three nullable columns to public.users so that record can be
-- persisted as legal evidence. They are NOT folded into users.preferences
-- (save_user_preferences overwrites that JSONB wholesale on every save).
--
-- ROLLOUT ORDER (important):
--   1. apply THIS migration;
--   2. flip ENABLE_CONSENT_PERSIST=true on `web` (writes the three columns on
--      the users insert; flag OFF = the insert dict is byte-identical to today);
--   3. ship the client half to phones (eas update --branch preview);
--   4. only then flip ENABLE_CONSENT_REQUIRED=true (rejects an account creation
--      that carries no acceptance with 400 TERMS_ACCEPTANCE_REQUIRED). Flipping
--      it before the OTA refuses every registration from phones on 97b5f15.
-- Flipping PERSIST before this migration is applied would make the users
-- insert reference unknown columns — apply 038 first.
--
-- Rollback: migrations/rollback/038_users_consent_capture.sql
-- Additive + nullable → safe, no backfill, no index, no function.

BEGIN;

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS terms_version TEXT,
  ADD COLUMN IF NOT EXISTS age_attested_at TIMESTAMPTZ;

COMMENT ON COLUMN public.users.terms_accepted_at IS
  'W3-16: when the user accepted the Terms (server UTC time of the account '
  'creation that carried the acceptance). Written only when '
  'ENABLE_CONSENT_PERSIST is ON. Nullable: accounts created before 038 / the '
  'flag, or by clients that sent no acceptance, have NULL.';

COMMENT ON COLUMN public.users.terms_version IS
  'W3-16: the Terms version string the client showed and the user accepted '
  '(recorded as sent, e.g. 2026-03-26). Written only when ENABLE_CONSENT_PERSIST '
  'is ON. Nullable.';

COMMENT ON COLUMN public.users.age_attested_at IS
  'W3-16: when the user attested to being 13 or older (same timestamp as '
  'terms_accepted_at: one control carries both attestations). Written only when '
  'ENABLE_CONSENT_PERSIST is ON. Nullable.';

COMMIT;

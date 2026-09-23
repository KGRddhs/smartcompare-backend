-- Rollback 038: drop the users consent-capture columns
--
-- Flip BOTH ENABLE_CONSENT_REQUIRED and ENABLE_CONSENT_PERSIST OFF BEFORE
-- running this rollback, so no in-flight users insert references the columns,
-- then drop them. Dropping them discards any recorded consent evidence.

BEGIN;

ALTER TABLE public.users
  DROP COLUMN IF EXISTS terms_accepted_at,
  DROP COLUMN IF EXISTS terms_version,
  DROP COLUMN IF EXISTS age_attested_at;

COMMIT;

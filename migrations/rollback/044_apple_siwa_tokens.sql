-- Rollback for migration 044_apple_siwa_tokens.sql (B3-B, S79)
--
-- Flip ENABLE_APPLE_TOKEN_REVOCATION off FIRST (Railway `web`), then run this.
-- With the flag still ON the store and the read would fail soft against a
-- missing table (logged WARNINGs, no revoke).
--
-- IMPORTANT: this is destructive. The stored Apple refresh tokens are lost and
-- those users can no longer be revoked from the server (the TN3194 fallback:
-- the user removes the app under Settings > Apple ID > Sign in with Apple).

BEGIN;

DROP TABLE IF EXISTS public.apple_siwa_tokens;

COMMIT;

-- Migration 044: public.apple_siwa_tokens -- Sign in with Apple refresh tokens (B3-B, S79)
--
-- Apple asks apps that offer Sign in with Apple to revoke the user's tokens
-- through its REST API when the account is deleted. The backend can only do
-- that if it holds a token: with ENABLE_APPLE_TOKEN_REVOCATION ON, an Apple
-- sign-in that carries the client's authorization_code exchanges it at
-- appleid.apple.com/auth/token and upserts the refresh token here
-- (app/services/apple_siwa_service.py + auth_service.store_apple_refresh_token);
-- DELETE /api/v1/auth/account reads it before the cascade and posts it to
-- appleid.apple.com/auth/revoke before the auth delete.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION (the flag defaults OFF).
--
-- APPLY ORDER (important): apply 044 BEFORE flipping
-- ENABLE_APPLE_TOKEN_REVOCATION. Flag ON without the table makes every store
-- and read fail soft (a logged WARNING), so revocation silently never happens.
--
-- Service role only: RLS on, no policy, REVOKE ALL from PUBLIC / anon /
-- authenticated, and one explicit GRANT to service_role (ruling B6, the 037
-- precedent). The token is never readable with a user's own JWT.
-- Rows leave with the account: FK to auth.users ON DELETE CASCADE, so the auth
-- delete (the last step of delete_user_account) removes the row in either
-- public.users FK branch; the 043 cascade function is untouched (ruling Q1 A).
-- No index (the primary key serves the one lookup), no function.
--
-- Owner postcheck: relrowsecurity = true; has_table_privilege for service_role
-- INSERT and SELECT = true; for anon and authenticated SELECT = false.
--
-- Rollback: migrations/rollback/044_apple_siwa_tokens.sql

BEGIN;

CREATE TABLE IF NOT EXISTS public.apple_siwa_tokens (
  user_id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  refresh_token text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.apple_siwa_tokens ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.apple_siwa_tokens FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE ON public.apple_siwa_tokens TO service_role;

COMMENT ON TABLE public.apple_siwa_tokens IS
  'Apple refresh token kept only so account deletion can revoke it at Apple. Written and read by the service role only; removed with the auth user.';

COMMENT ON COLUMN public.apple_siwa_tokens.refresh_token IS
  'Apple refresh token from the authorization-code exchange. Never logged. Posted to appleid.apple.com/auth/revoke on account deletion.';

COMMIT;

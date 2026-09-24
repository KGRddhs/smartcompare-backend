-- 040_revoke_cleanup_expired_ratings.sql
-- W1-2b — the rest of CR-SECURITY-01: public.cleanup_expired_ratings.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION. It is a file in a repo until
-- somebody applies it. It does not depend on 035, 036, 037 (or 038/039, which
-- are other units' numbers: 038 is W3-16's, 039 is reserved for the M13-29 RLS
-- migration) and may be applied before or after any of them.
--
-- ============================================================================
-- WHY THIS FILE EXISTS
-- ============================================================================
-- The consolidated review named cleanup_expired_ratings as one of three
-- SECURITY DEFINER functions the anon role can execute. 037 dismissed it as
-- nonexistent because a repo grep finds nothing — but the function was created
-- OUT OF BAND, so no grep of this repo can see it. The live review measured it
-- present: docs/investigations/2026-09-06-full-review-verified.json records
-- that it "exists live but in NO migration", and an anon-key GET on
-- /rpc/cleanup_expired_ratings returned SQLSTATE 25006 ("cannot execute DELETE
-- in a read-only transaction"): the anon role passed the EXECUTE check and the
-- body ran as far as its DELETE. A POST would not have been read-only.
--
-- WHAT THIS FILE DOES, AND DOES NOT DO
--   * REVOKE ALL ... FROM PUBLIC, anon, authenticated on EVERY function named
--     cleanup_expired_ratings in schema public, looked up BY NAME in pg_proc.
--     The live signature is unknown to the repo, so a hardcoded
--     `cleanup_expired_ratings()` would fail (or, behind a guessed
--     to_regprocedure, silently skip) on any other argument list.
--   * Revoke ONLY. Nothing is granted: there is no caller of this function in
--     app/ or scripts/ (pinned by tests/test_retro_w1_2b.py). On a stock
--     Supabase project service_role keeps its own explicit default-privilege
--     grant; where it has none, it loses EXECUTE here too, which no repo caller
--     notices. If a caller ever appears, decide its grant BEFORE applying.
--   * It neither creates nor drops the function. Its body is unknown, and a
--     live object nobody has read is not ours to destroy.
--   * Idempotent: on a database without the function it is a no-op (a NOTICE),
--     and a re-run revokes nothing new.
--
-- ============================================================================
-- RUN THESE FIRST, IN THE SAME SESSION, AND KEEP THE OUTPUT
-- ============================================================================
-- 1. The function itself — real signature, SECURITY DEFINER flag, ACL, and the
--    live body, which exists in no migration:
--
--     SELECT p.oid::regprocedure AS signature,
--            p.prosecdef,
--            p.proacl,
--            pg_get_functiondef(p.oid) AS definition
--       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--      WHERE n.nspname = 'public' AND p.proname = 'cleanup_expired_ratings';
--
--    An `anon=X/...` entry, a bare `=X/...` entry (the empty grantee IS
--    PUBLIC) or a NULL proacl (PUBLIC default in force) means anon can call it.
--
-- 2. The census of EVERY SECURITY DEFINER function in public that anon can
--    execute — the question a repo grep cannot answer:
--
--     SELECT p.oid::regprocedure AS signature, p.proacl
--       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--      WHERE n.nspname = 'public'
--        AND p.prosecdef
--        AND has_function_privilege('anon', p.oid, 'EXECUTE')
--      ORDER BY 1;
--
--    Expected BEFORE 040: cleanup_expired_ratings is listed. Expected AFTER 040
--    (and 037): only resolve_referral_code, which is DELIBERATELY anon-callable
--    (signup resolves an invite code before the account exists). Any OTHER row
--    is a further out-of-band function and needs its own migration.
--
-- AFTER APPLYING: re-run both queries. Then an anon-key GET on
-- /rest/v1/rpc/cleanup_expired_ratings must answer 42501 permission denied
-- (or 404/PGRST202 after a schema reload) and must NEVER again answer 25006.

BEGIN;

DO $$
DECLARE
  fn record;
  n_revoked integer := 0;
BEGIN
  FOR fn IN
    SELECT
      p.proname,
      pg_get_function_identity_arguments(p.oid) AS args
    FROM pg_proc AS p
    INNER JOIN pg_namespace AS n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = 'cleanup_expired_ratings'
  LOOP
    EXECUTE format(
      'REVOKE ALL ON FUNCTION public.%I(%s) FROM PUBLIC, anon, authenticated',
      fn.proname, fn.args
    );
    n_revoked := n_revoked + 1;
  END LOOP;
  RAISE NOTICE
    '040: revoked EXECUTE on % public.cleanup_expired_ratings signature(s)',
    n_revoked;
END
$$;

COMMIT;

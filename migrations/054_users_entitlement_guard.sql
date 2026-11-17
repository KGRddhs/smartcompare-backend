-- Migration 054 (INC-T1b USERS-ENTITLEMENT-GUARD): a BEFORE INSERT OR UPDATE
-- row trigger on public.users that refuses an entitlement change made by a
-- signed-in (or anonymous) API caller.
--
-- WHY: public.users has RLS on, its UPDATE policies are USING (auth.uid() = id)
-- with no WITH CHECK, and the authenticated role holds UPDATE on every column
-- (010_enable_rls.sql:19-22, 011). A signed-in user calling the REST API
-- directly with the public key could raise their own subscription_tier or
-- reset lifetime_comparisons_used. RLS decides WHICH row; it cannot say WHICH
-- column. This trigger closes the column half.
--
-- THE ROLE TEST (the function body below): the write passes untouched when
--   current_user is neither anon nor authenticated
--   AND the request role (request.jwt.claims ->> 'role', else the legacy
--       request.jwt.claim.role setting) is NULL or 'service_role'.
-- That is: the backend admin client (PostgREST switches to service_role, the
-- claims say service_role), a SECURITY DEFINER function called through it
-- (delete_user_cascade, increment_lifetime_comparisons: current_user is the
-- owner, the claims say service_role), migrations, the SQL editor and any
-- other direct session (no request role). Every other caller is checked:
-- PostgREST runs a signed-in request as current_user = authenticated, so a
-- forged claim can never lift it; a SECURITY DEFINER function called by a
-- signed-in user carries the claims role 'authenticated' and is checked too.
-- An unparsable request.jwt.claims value raises (22P02): the write fails closed.
--
-- THE GUARDED COLUMNS (eleven): subscription_tier, subscription_expires_at,
-- lifetime_comparisons_used, referral_bonus_comparisons_this_month,
-- referral_bonus_reset_at, lifetime_invites_consumed, device_fingerprint_hash,
-- referral_code, terms_accepted_at, terms_version, age_attested_at.
-- On INSERT each must equal its column default (011, 014, 023: 'free', 0, the
-- month default; NULL for the rest); on UPDATE none may change
-- (IS DISTINCT FROM). Every other column stays writable by its owner under RLS.
--
-- REFUSAL: SQLSTATE 42501 (insufficient_privilege; PostgREST answers 403) with
-- one fixed message that carries no row data.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION: the file is written, not applied.
-- APPLY: the relay, in one window on the owner's yes, after the read-only check
-- docs/investigations/2026-11-17-session-97-state/APPLY_054_CHECK.sql; the
-- same check again after. ROLLBACK: migrations/rollback/054_users_entitlement_guard.sql.

BEGIN;

DO $guard$
DECLARE
  missing text;
BEGIN
  IF to_regclass('public.users') IS NULL THEN
    RAISE EXCEPTION '054 guard: public.users missing';
  END IF;
  SELECT string_agg(c.col, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'subscription_tier', 'subscription_expires_at',
      'lifetime_comparisons_used', 'referral_bonus_comparisons_this_month',
      'referral_bonus_reset_at', 'lifetime_invites_consumed',
      'device_fingerprint_hash', 'referral_code', 'terms_accepted_at',
      'terms_version', 'age_attested_at'
    ]) AS c (col)
   WHERE NOT EXISTS (
     SELECT 1
       FROM information_schema.columns AS i
      WHERE i.table_schema = 'public'
        AND i.table_name = 'users'
        AND i.column_name = c.col
   );
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '054 guard: public.users lacks column(s): %', missing;
  END IF;
END
$guard$;

CREATE OR REPLACE FUNCTION public.users_entitlement_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_request_role text;
BEGIN
  v_request_role := coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role',
    nullif(current_setting('request.jwt.claim.role', true), '')
  );
  IF current_user NOT IN ('anon', 'authenticated')
     AND (v_request_role IS NULL OR v_request_role = 'service_role') THEN
    RETURN NEW;
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.subscription_tier IS DISTINCT FROM 'free'
       OR NEW.subscription_expires_at IS NOT NULL
       OR NEW.lifetime_comparisons_used IS DISTINCT FROM 0
       OR NEW.referral_bonus_comparisons_this_month IS DISTINCT FROM 0
       OR NEW.referral_bonus_reset_at IS DISTINCT FROM (date_trunc('month', now()) + interval '1 month')
       OR NEW.lifetime_invites_consumed IS DISTINCT FROM 0
       OR NEW.device_fingerprint_hash IS NOT NULL
       OR NEW.referral_code IS NOT NULL
       OR NEW.terms_accepted_at IS NOT NULL
       OR NEW.terms_version IS NOT NULL
       OR NEW.age_attested_at IS NOT NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '42501',
        MESSAGE = 'users entitlement columns are server-managed (INC-T1b)';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.subscription_tier IS DISTINCT FROM OLD.subscription_tier
     OR NEW.subscription_expires_at IS DISTINCT FROM OLD.subscription_expires_at
     OR NEW.lifetime_comparisons_used IS DISTINCT FROM OLD.lifetime_comparisons_used
     OR NEW.referral_bonus_comparisons_this_month IS DISTINCT FROM OLD.referral_bonus_comparisons_this_month
     OR NEW.referral_bonus_reset_at IS DISTINCT FROM OLD.referral_bonus_reset_at
     OR NEW.lifetime_invites_consumed IS DISTINCT FROM OLD.lifetime_invites_consumed
     OR NEW.device_fingerprint_hash IS DISTINCT FROM OLD.device_fingerprint_hash
     OR NEW.referral_code IS DISTINCT FROM OLD.referral_code
     OR NEW.terms_accepted_at IS DISTINCT FROM OLD.terms_accepted_at
     OR NEW.terms_version IS DISTINCT FROM OLD.terms_version
     OR NEW.age_attested_at IS DISTINCT FROM OLD.age_attested_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '42501',
      MESSAGE = 'users entitlement columns are server-managed (INC-T1b)';
  END IF;
  RETURN NEW;
END;
$function$;

CREATE OR REPLACE TRIGGER users_entitlement_guard
BEFORE INSERT OR UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.users_entitlement_guard();

COMMENT ON FUNCTION public.users_entitlement_guard() IS
'INC-T1b: refuses an entitlement-column change on public.users by an anon or authenticated caller (SQLSTATE 42501).';

DO $assert$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_trigger AS t
     WHERE t.tgrelid = 'public.users'::regclass
       AND t.tgname = 'users_entitlement_guard'
       AND t.tgfoid = 'public.users_entitlement_guard()'::regprocedure
       AND t.tgenabled = 'O'
       AND (t.tgtype::integer & 23) = 23
       AND (t.tgtype::integer & 8) = 0
  ) THEN
    RAISE EXCEPTION '054 assert: trigger missing, disabled or not BEFORE INSERT OR UPDATE FOR EACH ROW';
  END IF;
  IF NOT EXISTS (
    SELECT 1
      FROM pg_proc AS p
     WHERE p.oid = 'public.users_entitlement_guard()'::regprocedure
       AND NOT p.prosecdef
       AND EXISTS (
         SELECT 1 FROM unnest(p.proconfig) AS cfg (setting)
          WHERE cfg.setting LIKE 'search_path=%'
       )
  ) THEN
    RAISE EXCEPTION '054 assert: function lost SECURITY INVOKER or its search_path';
  END IF;
END
$assert$;

COMMIT;

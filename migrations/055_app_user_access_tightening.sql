-- Migration 055 (INC-SEC-1 DATABASE-ACCESS): narrows what the two app roles
-- (anon = the public key with no sign-in, authenticated = a signed-in user's
-- token) may do on the tables the mobile app never reaches directly. Our
-- server talks to the database with its own service key; the app has no
-- database client. Every change below removes a permission no server path
-- uses (the walk in the INC-SEC-1 notes, 127 references, 18 user-scoped).
--
-- WHY, per finding (what is permitted today, and what changes):
-- F1  comparisons: any caller may read every row that carries a share token.
--     Changes to: a signed-in user reads only their own rows. The share page
--     reads with the server key, so it is unchanged.
-- F4  comparisons: a signed-in user may insert and update comparison rows.
--     Changes to: no app-role insert or update; delete of an own row stays.
-- F2  rating_cache (no CREATE in the repo): fully open to the app roles.
--     Changes to: closed, when the table exists.
-- F3  admin_audit_log, comparison_feedback, search_logs, user_events: rows
--     may be added without a sign-in, and with any content.
--     Changes to: no app-role writes; the server writes them.
-- F12 duplicate policies on comparison_feedback, user_events and users.
--     Changes to: one policy per purpose.
-- F11 users: a signed-in user may create their own users row.
--     Changes to: no app-role insert or delete on users.
-- F5  users: six more profile columns are writable by the row's owner
--     (email, created_at, attribution_source, last_comparison_at,
--     behavior_profile, demographics_profile).
--     Changes to: a second row trigger refuses an app-role change of them.
-- F6  the three vw_cohort_* views run with their owner's rights and are
--     granted to the app roles. Changes to: not selectable by the app roles.
-- F7  user_usage: owner insert and update. Changes to: server only.
-- F10 referral_invites: the invitee may read the invite row.
--     Changes to: only the referrer reads it.
-- F8  resolve_referral_code(text) is executable by the app roles.
--     Changes to: the server role only (it is the only caller), with a fixed
--     search_path.
-- F9  TRUNCATE, TRIGGER and REFERENCES are granted to the app roles on every
--     granted relation, and three tables are closed only by a missing policy.
--     Changes to: those three privileges revoked; eval_runs,
--     verdict_critiques and products closed by privilege.
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION: the file is written, not applied.
--
-- ORDER (R-18): 054 applied and verified, THEN the server deploy carrying
-- the feedback-write change (C2 / C2b) is live, THEN this file, in its own
-- window on the owner's yes.
-- FORBIDDEN: this file applied while the server runs a deploy before C2
-- (signed-in feedback would then be refused quietly). Never roll the server
-- back past the C2 commit while 055 is applied; roll 055 back first.
--
-- CHECK (before and after):
-- docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql
-- ROLLBACK: migrations/rollback/055_app_user_access_tightening.sql

BEGIN;

SET LOCAL lock_timeout = '5s';

DO $guard$
DECLARE
  missing text;
BEGIN
  SELECT string_agg(o.obj, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'public.users', 'public.comparisons', 'public.comparison_feedback',
      'public.search_logs', 'public.user_events', 'public.admin_audit_log',
      'public.user_usage', 'public.referral_invites', 'public.products',
      'public.eval_runs', 'public.verdict_critiques',
      'public.vw_cohort_match_rate', 'public.vw_cohort_persona_distribution',
      'public.vw_cohort_feedback_lift'
    ]) AS o (obj)
   WHERE to_regclass(o.obj) IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '055 guard: missing relation(s): %', missing;
  END IF;
  IF to_regprocedure('public.resolve_referral_code(text)') IS NULL THEN
    RAISE EXCEPTION '055 guard: public.resolve_referral_code(text) missing';
  END IF;
  SELECT string_agg(c.col, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'email', 'created_at', 'attribution_source', 'last_comparison_at',
      'behavior_profile', 'demographics_profile'
    ]) AS c (col)
   WHERE NOT EXISTS (
     SELECT 1
       FROM information_schema.columns AS i
      WHERE i.table_schema = 'public'
        AND i.table_name = 'users'
        AND i.column_name = c.col
   );
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '055 guard: public.users lacks column(s): %', missing;
  END IF;
END
$guard$;

-- F1 / F4: comparisons.
DROP POLICY IF EXISTS comparisons_select ON public.comparisons;
CREATE POLICY comparisons_select ON public.comparisons AS PERMISSIVE FOR SELECT TO authenticated
USING (auth.uid() = user_id);
DROP POLICY IF EXISTS comparisons_insert ON public.comparisons;
DROP POLICY IF EXISTS comparisons_update ON public.comparisons;
REVOKE INSERT, UPDATE ON public.comparisons FROM anon, authenticated;

-- F2: rating_cache, only when the table exists (it has no CREATE in the repo).
DO $rc$
BEGIN
  IF to_regclass('public.rating_cache') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role has full access to rating_cache" ON public.rating_cache'; -- noqa: RF05
    EXECUTE 'REVOKE ALL ON public.rating_cache FROM anon, authenticated';
  ELSE
    RAISE NOTICE '055: the ratings table is absent, skipped';
  END IF;
END
$rc$;

-- F3: admin_audit_log.
DROP POLICY IF EXISTS audit_insert ON public.admin_audit_log;
REVOKE ALL ON public.admin_audit_log FROM anon, authenticated;

-- F3 / F4 / F12: comparison_feedback (feedback_select kept).
DROP POLICY IF EXISTS feedback_insert ON public.comparison_feedback;
DROP POLICY IF EXISTS "Users can insert own feedback" ON public.comparison_feedback; -- noqa: RF05
DROP POLICY IF EXISTS "Users can read own feedback" ON public.comparison_feedback; -- noqa: RF05
REVOKE INSERT, UPDATE, DELETE ON public.comparison_feedback FROM anon, authenticated;

-- F3 / F4: search_logs (search_logs_select kept).
DROP POLICY IF EXISTS search_logs_insert ON public.search_logs;
REVOKE INSERT, UPDATE, DELETE ON public.search_logs FROM anon, authenticated;

-- F3 / F4 / F12: user_events (events_select kept).
DROP POLICY IF EXISTS events_insert ON public.user_events;
DROP POLICY IF EXISTS "Users can insert own events" ON public.user_events; -- noqa: RF05
REVOKE INSERT, UPDATE, DELETE ON public.user_events FROM anon, authenticated;

-- F11 / F12: users (users_select and users_update kept; the server role
-- passes row security by BYPASSRLS).
DROP POLICY IF EXISTS users_insert ON public.users;
DROP POLICY IF EXISTS "Users can read own data" ON public.users; -- noqa: RF05
DROP POLICY IF EXISTS "Users can update own data" ON public.users; -- noqa: RF05
DROP POLICY IF EXISTS "Service role full access" ON public.users; -- noqa: RF05
REVOKE INSERT, DELETE ON public.users FROM anon, authenticated;

-- F5: the six profile columns (its own function and trigger; the 054
-- objects are not touched). The role test is 054's, byte for byte.
CREATE OR REPLACE FUNCTION public.users_profile_guard()
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
    IF NEW.email IS NOT NULL
       OR NEW.created_at IS DISTINCT FROM now()
       OR NEW.attribution_source IS NOT NULL
       OR NEW.last_comparison_at IS NOT NULL
       OR NEW.behavior_profile IS DISTINCT FROM '{}'::jsonb
       OR NEW.demographics_profile IS NOT NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '42501',
        MESSAGE = 'users profile columns are server-managed (INC-SEC-1)';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.email IS DISTINCT FROM OLD.email
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
     OR NEW.attribution_source IS DISTINCT FROM OLD.attribution_source
     OR NEW.last_comparison_at IS DISTINCT FROM OLD.last_comparison_at
     OR NEW.behavior_profile IS DISTINCT FROM OLD.behavior_profile
     OR NEW.demographics_profile IS DISTINCT FROM OLD.demographics_profile THEN
    RAISE EXCEPTION USING
      ERRCODE = '42501',
      MESSAGE = 'users profile columns are server-managed (INC-SEC-1)';
  END IF;
  RETURN NEW;
END;
$function$;

CREATE OR REPLACE TRIGGER users_profile_guard
BEFORE INSERT OR UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.users_profile_guard();

COMMENT ON FUNCTION public.users_profile_guard() IS
'INC-SEC-1: refuses a profile-column change on public.users by an anon or authenticated caller (SQLSTATE 42501).';

-- F6: the cohort views (a revoke; the server role keeps its grant).
REVOKE ALL ON public.vw_cohort_match_rate, public.vw_cohort_persona_distribution, public.vw_cohort_feedback_lift
FROM anon, authenticated;

-- F7: user_usage (usage_select kept).
DROP POLICY IF EXISTS usage_insert ON public.user_usage;
DROP POLICY IF EXISTS usage_update ON public.user_usage;
REVOKE INSERT, UPDATE, DELETE ON public.user_usage FROM anon, authenticated;

-- F10: referral_invites, the referrer only.
DROP POLICY IF EXISTS referral_invites_select_own ON public.referral_invites;
CREATE POLICY referral_invites_select_own ON public.referral_invites AS PERMISSIVE FOR SELECT TO authenticated
USING (referrer_user_id = auth.uid());

-- F8: resolve_referral_code, the server role only (its 037 grant stays).
REVOKE EXECUTE ON FUNCTION public.resolve_referral_code(text) FROM anon, authenticated;
ALTER FUNCTION public.resolve_referral_code(text) SET search_path = public;

-- F9: three privileges no app path uses, and three tables closed by privilege.
REVOKE TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON public.eval_runs, public.verdict_critiques, public.products FROM anon, authenticated;

DO $assert$
BEGIN
  -- 1. no app-role policy on the ten tables keeps an open branch.
  IF EXISTS (
    SELECT 1
      FROM pg_catalog.pg_policies AS p
     WHERE p.schemaname = 'public'
       AND p.tablename IN (
         'admin_audit_log', 'comparison_feedback', 'comparisons', 'products', 'rating_cache',
         'referral_invites', 'search_logs', 'user_events', 'user_usage', 'users'
       )
       AND p.roles && ARRAY['public', 'anon', 'authenticated']::name []
       AND (
         coalesce(p.qual, '') ILIKE '%user_id IS NULL%'
         OR coalesce(p.with_check, '') ILIKE '%user_id IS NULL%'
         OR coalesce(p.qual, '') ILIKE '%share_token%'
         OR coalesce(p.with_check, '') ILIKE '%share_token%'
         OR p.qual = 'true'
         OR p.with_check = 'true'
       )
  ) THEN
    RAISE EXCEPTION '055 assert: an app-role policy keeps an open branch';
  END IF;
  -- 2. no INSERT (or ALL) policy is left on the seven written tables.
  IF EXISTS (
    SELECT 1
      FROM pg_catalog.pg_policies AS p
     WHERE p.schemaname = 'public'
       AND p.tablename IN (
         'comparisons', 'comparison_feedback', 'search_logs', 'user_events',
         'admin_audit_log', 'users', 'user_usage'
       )
       AND p.cmd IN ('INSERT', 'ALL')
  ) THEN
    RAISE EXCEPTION '055 assert: an insert policy is left';
  END IF;
  -- 3. and 6. every closed privilege is closed for anon and authenticated.
  IF EXISTS (
    SELECT 1
      FROM (VALUES
        ('public.comparisons', 'INSERT'), ('public.comparisons', 'UPDATE'),
        ('public.admin_audit_log', 'SELECT'), ('public.admin_audit_log', 'INSERT'),
        ('public.admin_audit_log', 'UPDATE'), ('public.admin_audit_log', 'DELETE'),
        ('public.comparison_feedback', 'INSERT'), ('public.comparison_feedback', 'UPDATE'),
        ('public.comparison_feedback', 'DELETE'),
        ('public.search_logs', 'INSERT'), ('public.search_logs', 'UPDATE'), ('public.search_logs', 'DELETE'),
        ('public.user_events', 'INSERT'), ('public.user_events', 'UPDATE'), ('public.user_events', 'DELETE'),
        ('public.users', 'INSERT'), ('public.users', 'DELETE'),
        ('public.user_usage', 'INSERT'), ('public.user_usage', 'UPDATE'), ('public.user_usage', 'DELETE'),
        ('public.rating_cache', 'SELECT'), ('public.rating_cache', 'INSERT'),
        ('public.rating_cache', 'UPDATE'), ('public.rating_cache', 'DELETE'),
        ('public.vw_cohort_match_rate', 'SELECT'), ('public.vw_cohort_persona_distribution', 'SELECT'),
        ('public.vw_cohort_feedback_lift', 'SELECT'),
        ('public.eval_runs', 'SELECT'), ('public.eval_runs', 'INSERT'),
        ('public.verdict_critiques', 'SELECT'), ('public.verdict_critiques', 'INSERT'),
        ('public.products', 'SELECT'), ('public.products', 'INSERT')
      ) AS v (rel, priv)
     CROSS JOIN (VALUES ('anon'), ('authenticated')) AS r (role_name)
     WHERE coalesce(has_table_privilege(r.role_name, to_regclass(v.rel)::oid, v.priv), false)
  ) THEN
    RAISE EXCEPTION '055 assert: an app role still holds a closed privilege';
  END IF;
  IF EXISTS (
    SELECT 1
      FROM pg_catalog.pg_class AS c
      JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
     CROSS JOIN (VALUES ('anon'), ('authenticated')) AS r (role_name)
     WHERE n.nspname = 'public'
       AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
       AND (
         has_table_privilege(r.role_name, c.oid, 'TRUNCATE')
         OR has_table_privilege(r.role_name, c.oid, 'TRIGGER')
         OR has_table_privilege(r.role_name, c.oid, 'REFERENCES')
       )
  ) THEN
    RAISE EXCEPTION '055 assert: an app role still holds TRUNCATE, TRIGGER or REFERENCES';
  END IF;
  -- 4. the trigger: present, enabled, BEFORE INSERT OR UPDATE FOR EACH ROW.
  IF NOT EXISTS (
    SELECT 1
      FROM pg_catalog.pg_trigger AS t
     WHERE t.tgrelid = 'public.users'::regclass
       AND t.tgname = 'users_profile_guard'
       AND t.tgfoid = 'public.users_profile_guard()'::regprocedure
       AND t.tgenabled = 'O'
       AND (t.tgtype::integer & 23) = 23
       AND (t.tgtype::integer & 8) = 0
  ) THEN
    RAISE EXCEPTION '055 assert: trigger missing, disabled or not BEFORE INSERT OR UPDATE FOR EACH ROW';
  END IF;
  -- 5. the function: invoker, with a search_path entry.
  IF NOT EXISTS (
    SELECT 1
      FROM pg_catalog.pg_proc AS p
     WHERE p.oid = 'public.users_profile_guard()'::regprocedure
       AND NOT p.prosecdef
       AND EXISTS (
         SELECT 1 FROM unnest(p.proconfig) AS cfg (setting)
          WHERE cfg.setting LIKE 'search_path=%'
       )
  ) THEN
    RAISE EXCEPTION '055 assert: function lost SECURITY INVOKER or its search_path';
  END IF;
  -- 7. resolve_referral_code: the server role only.
  IF has_function_privilege('anon', 'public.resolve_referral_code(text)', 'EXECUTE')
     OR has_function_privilege('authenticated', 'public.resolve_referral_code(text)', 'EXECUTE')
     OR NOT has_function_privilege('service_role', 'public.resolve_referral_code(text)', 'EXECUTE') THEN
    RAISE EXCEPTION '055 assert: resolve_referral_code grants are not the server role only';
  END IF;
END
$assert$;

COMMIT;

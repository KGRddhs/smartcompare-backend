-- Rollback for migration 055_app_user_access_tightening.sql (INC-SEC-1 DATABASE-ACCESS)
--
-- THIS RE-OPENS EVERY GAP 055 CLOSES: the shared-row read, the app-role
-- writes to the log, feedback, event, audit and comparison tables, the six
-- profile columns, the cohort views, the referral lookup and the invitee
-- read. Run it only on a ruled rollback.
--
-- It drops 055's own trigger and function, re-creates every policy 055
-- dropped or replaced (verbatim from the 2026-11-17 catalog, each after a
-- DROP POLICY IF EXISTS, so a second run is a no-op), and grants back exactly
-- what 055 revoked, on named objects only. After it, the read-only check
-- docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql must
-- print a grid byte-equal to the BEFORE grid.

BEGIN;

SET LOCAL lock_timeout = '5s';

DROP TRIGGER IF EXISTS users_profile_guard ON public.users;

DROP FUNCTION IF EXISTS public.users_profile_guard();

-- comparisons
DROP POLICY IF EXISTS comparisons_select ON public.comparisons;
CREATE POLICY comparisons_select ON public.comparisons AS PERMISSIVE FOR SELECT TO public
USING (((auth.uid() = user_id) OR (share_token IS NOT NULL)));
DROP POLICY IF EXISTS comparisons_insert ON public.comparisons;
CREATE POLICY comparisons_insert ON public.comparisons AS PERMISSIVE FOR INSERT TO public
WITH CHECK ((auth.uid() = user_id));
DROP POLICY IF EXISTS comparisons_update ON public.comparisons;
CREATE POLICY comparisons_update ON public.comparisons AS PERMISSIVE FOR UPDATE TO public
USING ((auth.uid() = user_id));

-- admin_audit_log
DROP POLICY IF EXISTS audit_insert ON public.admin_audit_log;
CREATE POLICY audit_insert ON public.admin_audit_log AS PERMISSIVE FOR INSERT TO public
WITH CHECK (true);

-- comparison_feedback
DROP POLICY IF EXISTS feedback_insert ON public.comparison_feedback;
CREATE POLICY feedback_insert ON public.comparison_feedback AS PERMISSIVE FOR INSERT TO public
WITH CHECK (((auth.uid() = user_id) OR (user_id IS NULL)));
DROP POLICY IF EXISTS "Users can insert own feedback" ON public.comparison_feedback; -- noqa: RF05
CREATE POLICY "Users can insert own feedback" ON public.comparison_feedback AS PERMISSIVE FOR INSERT TO public -- noqa: RF05
WITH CHECK (((auth.uid() = user_id) OR (user_id IS NULL)));
DROP POLICY IF EXISTS "Users can read own feedback" ON public.comparison_feedback; -- noqa: RF05
CREATE POLICY "Users can read own feedback" ON public.comparison_feedback AS PERMISSIVE FOR SELECT TO public -- noqa: RF05
USING ((auth.uid() = user_id));

-- search_logs
DROP POLICY IF EXISTS search_logs_insert ON public.search_logs;
CREATE POLICY search_logs_insert ON public.search_logs AS PERMISSIVE FOR INSERT TO public
WITH CHECK (((auth.uid() = user_id) OR (user_id IS NULL)));

-- user_events
DROP POLICY IF EXISTS events_insert ON public.user_events;
CREATE POLICY events_insert ON public.user_events AS PERMISSIVE FOR INSERT TO public
WITH CHECK (((auth.uid() = user_id) OR (user_id IS NULL)));
DROP POLICY IF EXISTS "Users can insert own events" ON public.user_events; -- noqa: RF05
CREATE POLICY "Users can insert own events" ON public.user_events AS PERMISSIVE FOR INSERT TO public -- noqa: RF05
WITH CHECK (((auth.uid() = user_id) OR (user_id IS NULL)));

-- users
DROP POLICY IF EXISTS users_insert ON public.users;
CREATE POLICY users_insert ON public.users AS PERMISSIVE FOR INSERT TO public
WITH CHECK ((auth.uid() = id));
DROP POLICY IF EXISTS "Users can read own data" ON public.users; -- noqa: RF05
CREATE POLICY "Users can read own data" ON public.users AS PERMISSIVE FOR SELECT TO public -- noqa: RF05
USING ((auth.uid() = id));
DROP POLICY IF EXISTS "Users can update own data" ON public.users; -- noqa: RF05
CREATE POLICY "Users can update own data" ON public.users AS PERMISSIVE FOR UPDATE TO public -- noqa: RF05
USING ((auth.uid() = id));
DROP POLICY IF EXISTS "Service role full access" ON public.users; -- noqa: RF05
CREATE POLICY "Service role full access" ON public.users AS PERMISSIVE FOR ALL TO public -- noqa: RF05
USING ((auth.role() = 'service_role'::text));

-- user_usage
DROP POLICY IF EXISTS usage_insert ON public.user_usage;
CREATE POLICY usage_insert ON public.user_usage AS PERMISSIVE FOR INSERT TO public
WITH CHECK ((auth.uid() = user_id));
DROP POLICY IF EXISTS usage_update ON public.user_usage;
CREATE POLICY usage_update ON public.user_usage AS PERMISSIVE FOR UPDATE TO public
USING ((auth.uid() = user_id));

-- referral_invites
DROP POLICY IF EXISTS referral_invites_select_own ON public.referral_invites;
CREATE POLICY referral_invites_select_own ON public.referral_invites AS PERMISSIVE FOR SELECT TO authenticated
USING (((referrer_user_id = auth.uid()) OR (redeemed_by_user_id = auth.uid())));

-- the two tables with no CREATE in the repo: only when present.
DO $absent$
BEGIN
  IF to_regclass('public.rating_cache') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role has full access to rating_cache" ON public.rating_cache'; -- noqa: RF05
    EXECUTE 'CREATE POLICY "Service role has full access to rating_cache" ON public.rating_cache AS PERMISSIVE FOR ALL TO public USING (true)'; -- noqa: RF05
    EXECUTE 'GRANT ALL ON public.rating_cache TO anon, authenticated';
  ELSE
    RAISE NOTICE '055 rollback: the ratings table is absent, skipped';
  END IF;
  IF to_regclass('public.bahrain_approved_drugs') IS NOT NULL THEN
    EXECUTE 'GRANT TRUNCATE, TRIGGER, REFERENCES ON public.bahrain_approved_drugs TO anon, authenticated';
  ELSE
    RAISE NOTICE '055 rollback: the drugs table is absent, skipped';
  END IF;
END
$absent$;

-- grants back, on named objects only.
GRANT INSERT, UPDATE ON public.comparisons TO anon, authenticated;
GRANT ALL ON public.admin_audit_log TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.comparison_feedback TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.search_logs TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.user_events TO anon, authenticated;
GRANT INSERT, DELETE ON public.users TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.user_usage TO anon, authenticated;
GRANT ALL ON public.vw_cohort_match_rate, public.vw_cohort_persona_distribution, public.vw_cohort_feedback_lift
TO anon, authenticated;
GRANT ALL ON public.eval_runs, public.verdict_critiques, public.products TO anon, authenticated;
GRANT TRUNCATE, TRIGGER, REFERENCES ON
public.admin_audit_log, public.comparison_feedback, public.comparisons, public.deep_review_credits,
public.eval_runs, public.pain_workflow_events, public.products, public.re_engagement_events,
public.referral_invites, public.referral_redemptions, public.search_logs, public.user_events,
public.user_preference_history, public.user_usage, public.users, public.verdict_critiques,
public.vw_cohort_feedback_lift, public.vw_cohort_match_rate, public.vw_cohort_persona_distribution
TO anon, authenticated;

-- resolve_referral_code: the grant and the default search_path back.
GRANT EXECUTE ON FUNCTION public.resolve_referral_code(text) TO anon, authenticated;
ALTER FUNCTION public.resolve_referral_code(text) RESET search_path;

COMMIT;

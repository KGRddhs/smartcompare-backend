-- 043_delete_user_cascade_full_erasure.sql
-- S71 U8b: account deletion erases every user-owned row and every personal
-- column of the kept users row (App Store guideline 5.1.1(v)).
--
-- MERGING THIS CHANGES NOTHING IN PRODUCTION. Ahmed applies it in the Supabase
-- SQL editor from the one-paste files in
-- docs/investigations/2026-10-03-session-71-state/ (PRECHECK, ONE_PASTE,
-- POSTCHECK, and the optional BACKFILL). Apply order: 037 must already be
-- applied (it was, 2026-09-24); 039 stays reserved; 035/036 are not needed.
--
-- WHAT 025 MISSED (measured at eb86075e):
--   * four tables created with user_id FKs to public.users whose ON DELETE
--     CASCADE fires only when the public.users row itself is deleted, which
--     happens in branch A on the auth delete and never in branch B:
--     deep_review_credits and re_engagement_events (014),
--     pain_workflow_events (028), user_preference_history (029);
--   * every users column except preferences, behavior_profile,
--     preferences_completed, expo_push_token and device_fingerprint_hash:
--     email, display_name, demographics (013), referral code (014), push
--     opt-in (015), attribution (019), consent (038) and the rest;
--   * the IP address on the user's admin_audit_log rows.
--   * 025's reason for keeping the row ("admin_audit_log foreign keys") is
--     false in the files: 011 creates admin_audit_log.user_id with no FK.
--
-- WHAT THIS KEEPS: users.id, users.created_at and users.updated_at (set to
-- the erasure time) as a de-identified stub, and admin_audit_log rows with
-- their ip_address removed.
--
-- SAFETY (all inside ONE transaction; any RAISE or error rolls back the whole
-- file and leaves the 025 function in force):
--   * the guard block aborts if a table this function touches is missing, if
--     a users column it writes is missing live or is NOT NULL where it writes
--     NULL, or if admin_audit_log.ip_address is missing or NOT NULL;
--   * the guard block's last step writes the 25 tombstone values into a temp
--     copy of public.users (LIKE ... INCLUDING DEFAULTS INCLUDING
--     CONSTRAINTS), so a live CHECK that rejects 'free', 0, false or now()
--     aborts the apply instead of the first real deletion;
--   * the assert block first calls the new function with the NIL uuid (no
--     account has it), so a missing user_id / comparison_id column aborts
--     here, then proves SECURITY DEFINER, the pinned search_path and the 037
--     ACL. CREATE OR REPLACE keeps the owner and the ACL (PostgreSQL 18 docs,
--     CREATE FUNCTION), so the 037 GRANT is not restated here
--     (tests/test_migration_037_security_definer_grants.py pins exactly one);
--     the REVOKE is restated because the order-aware census in
--     tests/test_retro_w1_2d.py requires one after every (re)definition.
--
-- BODY ORDER: 025's seven DELETEs (same order: user_events before
-- comparisons); immediately before the comparisons DELETE, other users'
-- user_events and comparison_feedback rows that point at the target's
-- comparisons are detached (comparison_id set to NULL), so a NO ACTION FK
-- cannot block the deletion; then the four U8b DELETEs, then the
-- admin_audit_log IP UPDATE, then the users UPDATE. No comment lives inside a
-- dollar-quoted body: the SQL editor paste joins lines, where a comment would
-- swallow code.
--
-- Rollback: migrations/rollback/043_delete_user_cascade_full_erasure.sql
-- restores the 025 body. It cannot restore erased data.

BEGIN;

DO $guard$
DECLARE
  missing text;
  not_nullable text;
BEGIN
  SELECT string_agg(t.tbl, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'public.users', 'public.user_events', 'public.comparison_feedback',
      'public.comparisons', 'public.search_logs', 'public.user_usage',
      'public.referral_invites', 'public.referral_redemptions',
      'public.deep_review_credits', 'public.re_engagement_events',
      'public.pain_workflow_events', 'public.user_preference_history',
      'public.admin_audit_log'
    ]) AS t (tbl)
   WHERE to_regclass(t.tbl) IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '043 guard: missing table(s): %', missing;
  END IF;

  SELECT string_agg(c.col, ', ')
    INTO missing
    FROM unnest(ARRAY[
      'email', 'display_name', 'auth_provider', 'subscription_tier',
      'subscription_expires_at', 'updated_at', 'preferences',
      'preferences_completed', 'behavior_profile', 'lifetime_comparisons_used',
      'demographics_profile', 'demographics_dismissed_count',
      'demographics_dismissed_at', 'referral_code',
      'referral_bonus_comparisons_this_month', 'referral_bonus_reset_at',
      'expo_push_token', 'notifications_enabled', 'last_comparison_at',
      'attribution_source', 'device_fingerprint_hash',
      'lifetime_invites_consumed', 'terms_accepted_at', 'terms_version',
      'age_attested_at'
    ]) AS c (col)
   WHERE NOT EXISTS (
     SELECT 1
       FROM information_schema.columns AS i
      WHERE i.table_schema = 'public'
        AND i.table_name = 'users'
        AND i.column_name = c.col
   );
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION '043 guard: public.users lacks column(s): %', missing;
  END IF;

  SELECT string_agg(i.column_name, ', ')
    INTO not_nullable
    FROM information_schema.columns AS i
   WHERE i.table_schema = 'public'
     AND i.table_name = 'users'
     AND i.is_nullable = 'NO'
     AND i.column_name = ANY (ARRAY[
       'email', 'display_name', 'auth_provider', 'subscription_expires_at',
       'preferences', 'behavior_profile', 'demographics_profile',
       'demographics_dismissed_at', 'referral_code', 'referral_bonus_reset_at',
       'expo_push_token', 'last_comparison_at', 'attribution_source',
       'device_fingerprint_hash', 'terms_accepted_at', 'terms_version',
       'age_attested_at'
     ]);
  IF not_nullable IS NOT NULL THEN
    RAISE EXCEPTION '043 guard: NOT NULL live, cannot erase to NULL: %', not_nullable;
  END IF;

  IF NOT EXISTS (
    SELECT 1
      FROM information_schema.columns AS i
     WHERE i.table_schema = 'public'
       AND i.table_name = 'admin_audit_log'
       AND i.column_name = 'ip_address'
       AND i.is_nullable = 'YES'
  ) THEN
    RAISE EXCEPTION '043 guard: admin_audit_log.ip_address missing or NOT NULL';
  END IF;

  CREATE TEMP TABLE u8b_probe (LIKE public.users INCLUDING DEFAULTS INCLUDING CONSTRAINTS) ON COMMIT DROP;
  INSERT INTO u8b_probe (id) VALUES ('00000000-0000-0000-0000-000000000000');
  UPDATE u8b_probe
     SET email = NULL,
         display_name = NULL,
         auth_provider = NULL,
         subscription_tier = 'free',
         subscription_expires_at = NULL,
         updated_at = now(),
         preferences = NULL,
         preferences_completed = false,
         behavior_profile = NULL,
         lifetime_comparisons_used = 0,
         demographics_profile = NULL,
         demographics_dismissed_count = 0,
         demographics_dismissed_at = NULL,
         referral_code = NULL,
         referral_bonus_comparisons_this_month = 0,
         referral_bonus_reset_at = NULL,
         expo_push_token = NULL,
         notifications_enabled = false,
         last_comparison_at = NULL,
         attribution_source = NULL,
         device_fingerprint_hash = NULL,
         lifetime_invites_consumed = 0,
         terms_accepted_at = NULL,
         terms_version = NULL,
         age_attested_at = NULL;
END
$guard$;

CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
BEGIN
  DELETE FROM public.user_events WHERE user_id = target_user_id;
  DELETE FROM public.comparison_feedback WHERE user_id = target_user_id;
  UPDATE public.user_events
     SET comparison_id = NULL
   WHERE comparison_id IN (
     SELECT c.id FROM public.comparisons AS c WHERE c.user_id = target_user_id
   );
  UPDATE public.comparison_feedback
     SET comparison_id = NULL
   WHERE comparison_id IN (
     SELECT c.id FROM public.comparisons AS c WHERE c.user_id = target_user_id
   );
  DELETE FROM public.comparisons WHERE user_id = target_user_id;
  DELETE FROM public.search_logs WHERE user_id = target_user_id;
  DELETE FROM public.user_usage WHERE user_id = target_user_id;
  DELETE FROM public.referral_invites
   WHERE referrer_user_id = target_user_id
      OR redeemed_by_user_id = target_user_id;
  DELETE FROM public.referral_redemptions
   WHERE referrer_user_id = target_user_id
      OR invitee_user_id = target_user_id;

  DELETE FROM public.deep_review_credits WHERE user_id = target_user_id;
  DELETE FROM public.re_engagement_events WHERE user_id = target_user_id;
  DELETE FROM public.pain_workflow_events WHERE user_id = target_user_id;
  DELETE FROM public.user_preference_history WHERE user_id = target_user_id;

  UPDATE public.admin_audit_log
     SET ip_address = NULL
   WHERE user_id = target_user_id;

  UPDATE public.users
     SET email = NULL,
         display_name = NULL,
         auth_provider = NULL,
         subscription_tier = 'free',
         subscription_expires_at = NULL,
         updated_at = now(),
         preferences = NULL,
         preferences_completed = false,
         behavior_profile = NULL,
         lifetime_comparisons_used = 0,
         demographics_profile = NULL,
         demographics_dismissed_count = 0,
         demographics_dismissed_at = NULL,
         referral_code = NULL,
         referral_bonus_comparisons_this_month = 0,
         referral_bonus_reset_at = NULL,
         expo_push_token = NULL,
         notifications_enabled = false,
         last_comparison_at = NULL,
         attribution_source = NULL,
         device_fingerprint_hash = NULL,
         lifetime_invites_consumed = 0,
         terms_accepted_at = NULL,
         terms_version = NULL,
         age_attested_at = NULL
   WHERE id = target_user_id;
END;
$function$;

REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid)
FROM PUBLIC, anon, authenticated;

DO $assert$
BEGIN
  PERFORM public.delete_user_cascade('00000000-0000-0000-0000-000000000000'::uuid);
  IF NOT EXISTS (
    SELECT 1
      FROM pg_proc AS p
     WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure
       AND p.prosecdef
       AND p.proconfig = ARRAY['search_path=public']
  ) THEN
    RAISE EXCEPTION '043 assert: SECURITY DEFINER or search_path=public lost';
  END IF;
  IF NOT has_function_privilege(
    'service_role', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION '043 assert: service_role cannot EXECUTE (apply 037 first)';
  END IF;
  IF has_function_privilege(
    'anon', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) OR has_function_privilege(
    'authenticated', 'public.delete_user_cascade(uuid)', 'EXECUTE'
  ) THEN
    RAISE EXCEPTION '043 assert: anon or authenticated can EXECUTE';
  END IF;
END
$assert$;

COMMIT;

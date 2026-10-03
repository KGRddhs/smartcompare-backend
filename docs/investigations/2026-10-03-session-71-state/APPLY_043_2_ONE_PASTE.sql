-- 043 ONE-PASTE APPLY (Supabase SQL editor: ONE paste, ONE run = ONE transaction)
-- Run APPLY_043_1_PRECHECK.sql first and resolve every STOP before this file.
-- A guard/assert RAISE aborts everything and leaves the 025 function in force; that is the
-- safety, not a failure to work around. So does ANY other error in this run (the tombstone
-- probe hitting a live CHECK or NOT NULL, the nil-uuid dry run hitting a missing column).
-- Do not edit and retry: send the error text back instead.
-- Assembled from migrations/043_delete_user_cascade_full_erasure.sql, byte-for-byte body.
-- Success looks like: Success. No rows returned. Then run APPLY_043_3_POSTCHECK.sql.

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

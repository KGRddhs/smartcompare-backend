-- Rollback of migration 048 (S81-22): restores the 043 delete_user_cascade body
-- (the kb_feedback hook removed; the function text is 043's own, byte for byte),
-- then drops compare_runs_prune(integer) and drops compare_runs and
-- compare_judgements. The run rows are lost (the judgements go with them). Roll
-- back 048 before 045. The REVOKE is restated; the one GRANT stays 037's.
-- There is no comment inside a dollar body.

BEGIN;

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

DROP FUNCTION IF EXISTS public.compare_runs_prune(integer);
DROP TABLE IF EXISTS public.compare_judgements;
DROP TABLE IF EXISTS public.compare_runs;

COMMIT;

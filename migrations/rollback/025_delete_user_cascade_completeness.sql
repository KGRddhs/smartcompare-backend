-- Rollback for Migration 025: restore the pre-Bundle-D body of delete_user_cascade
--
-- This restores the exact function body that was in production on 2026-05-23
-- BEFORE Migration 025 added user_usage / referral_invites / referral_redemptions
-- and the expanded users-row UPDATE.
--
-- WARNING: after rollback, any account-deletion request will leave behind
-- rows in user_usage, referral_invites, referral_redemptions, and the
-- expo_push_token / device_fingerprint_hash columns on users will NOT be
-- cleared. Only run this rollback if Migration 025 itself caused a
-- regression in cascade behavior.

BEGIN;

CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
BEGIN
  DELETE FROM user_events WHERE user_id = target_user_id;
  DELETE FROM comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM comparisons WHERE user_id = target_user_id;
  DELETE FROM search_logs WHERE user_id = target_user_id;
  UPDATE users SET preferences = NULL, behavior_profile = NULL,
    preferences_completed = false WHERE id = target_user_id;
END;
$function$;

COMMIT;

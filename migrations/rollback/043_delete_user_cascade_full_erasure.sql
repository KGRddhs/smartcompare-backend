-- rollback/043_delete_user_cascade_full_erasure.sql
-- Restores public.delete_user_cascade to the 025 body. The CREATE statement
-- below is migrations/025_delete_user_cascade_completeness.sql lines 28-70
-- verbatim (it carries 025's em dash, so this file is UTF-8, not ASCII).
-- CREATE OR REPLACE keeps the function's owner and the 037 ACL
-- ({postgres,service_role} only), so no GRANT is restated; the REVOKE is
-- restated for the order-aware census (tests/test_retro_w1_2d.py).
--
-- WARNING: this restores the FUNCTION only. Rows and columns 043 erased stay
-- erased, and admin_audit_log.ip_address values it cleared do not come back.
-- After this rollback a deletion is the 025 behaviour again:
--   * in both FK branches the IP stays on the user's admin_audit_log rows;
--   * in branch B (no users.id -> auth.users FK) the users row keeps email,
--     display_name, demographics, consent and the other personal columns,
--     and the rows of deep_review_credits, re_engagement_events,
--     pain_workflow_events and user_preference_history stay behind; in
--     branch A they go only when the auth delete succeeds (the users row and
--     its FK children cascade);
--   * the failure review correction C2 fixed comes back: 025 does not detach
--     other users' or anonymous user_events / comparison_feedback rows that
--     point at the deleted user's comparisons, so where that comparison_id
--     FK is NO ACTION or RESTRICT (PRECHECK section 4; section 10 counts such
--     rows) the deletion fails with a 500 and erases nothing.
-- The backend changes of U8b (cache purge, type-only log lines) work with
-- either function and stay.
--
-- Paste note: the 025 body carries whole-line comments inside its
-- $function$ body. Paste this file as-is, or drop the whole-line comments
-- first; never join its lines while a comment remains.

BEGIN;

CREATE OR REPLACE FUNCTION public.delete_user_cascade(target_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
BEGIN
  -- Original Bundle A cascade
  DELETE FROM user_events WHERE user_id = target_user_id;
  DELETE FROM comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM comparisons WHERE user_id = target_user_id;
  DELETE FROM search_logs WHERE user_id = target_user_id;

  -- Bundle D additions (Task 1.B.5)
  -- Freemium counters
  DELETE FROM user_usage WHERE user_id = target_user_id;

  -- Smart Decision Referrals: rows where this user is the referrer OR the redeemer
  DELETE FROM referral_invites
   WHERE referrer_user_id = target_user_id
      OR redeemed_by_user_id = target_user_id;

  -- Referral redemptions: this user as referrer OR invitee
  DELETE FROM referral_redemptions
   WHERE referrer_user_id = target_user_id
      OR invitee_user_id = target_user_id;

  -- Clear push token, device fingerprint, preferences, behavior profile
  -- (App Store delete-cascade — no residual PII tied to the user row).
  -- We keep the row so admin_audit_log foreign keys resolve, but every
  -- user-specific column is wiped.
  UPDATE users
     SET preferences = NULL,
         behavior_profile = NULL,
         preferences_completed = false,
         expo_push_token = NULL,
         device_fingerprint_hash = NULL
   WHERE id = target_user_id;

  -- admin_audit_log: INTENTIONALLY NOT DELETED (Session 43 decision).
  -- Security audit events must outlive the user record.
END;
$function$;

REVOKE ALL ON FUNCTION public.delete_user_cascade(uuid)
FROM PUBLIC, anon, authenticated;

COMMIT;

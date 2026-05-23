-- Migration 025: Expand delete_user_cascade to cover all user-owned tables
--
-- Bundle D Task 1.B.5 (R20).
--
-- The current cascade misses three tables added since Bundle A:
--   - user_usage          (freemium counters; user_id column)
--   - referral_invites    (Smart Decision Referrals; referrer_user_id + redeemed_by_user_id)
--   - referral_redemptions (Loop 2 grants; referrer_user_id + invitee_user_id)
--
-- Notes on tables I considered but excluded:
--   - expo_push_tokens: NO SUCH TABLE. Push token lives as a single column
--     `users.expo_push_token` (text). The existing users UPDATE handles
--     that — we extend it to clear the push token + device fingerprint
--     hash as well (App Store delete-cascade requirement).
--   - admin_audit_log: RETAIN per Session 43 design decision. Security
--     events MUST outlive the user record for compliance / forensics.
--
-- All deletes are user-scoped via user_id (or the per-table equivalent
-- like referrer_user_id / invitee_user_id) so RLS-protected rows owned
-- by other users are untouched.
--
-- Idempotent: function is CREATE OR REPLACE; safe to re-apply.
-- Rollback: migrations/rollback/025_delete_user_cascade_completeness.sql
--           restores the pre-Bundle-D body of the function.

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

COMMIT;

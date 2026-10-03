-- 043 BACKFILL (U8b, ruling Q2 / UR4). OPTIONAL: run it ONLY when PRECHECK section 9 c or d
-- was above 0, and ONLY after the POSTCHECK passed (and PRECHECK section 12 showed 0 nil-uuid rows).
-- Erases the users rows whose auth user was deleted before 043 (branch B leftovers) with the
-- new function, and clears the IPs of audit rows whose user has no auth.users row.
--
-- IT ALSO CHANGES ROWS OF LIVE USERS (the 043 semantics, applied after the fact):
--   * where an orphan was the REDEEMER of a live user's invite, that referral_invites row
--     and its referral_redemptions row are DELETED, so the live inviter loses that invite
--     and the bonus it carried (025 behaviour, kept by ruling UR8);
--   * live users' (and anonymous) user_events and comparison_feedback rows that point at an
--     orphan's comparison are kept, with comparison_id set to NULL (review correction C2).
-- IT DOES NOT ERASE the rows of an account deleted OUTSIDE the app that left no users row
-- (for example from the Supabase Auth dashboard in branch A): comparisons, user_events,
-- comparison_feedback and search_logs rows whose user has neither an auth.users nor a
-- public.users row stay. They are counted as f_after below (PRECHECK section 9 f);
-- f_after above 0 = send the grid back (erasing them needs an orchestrator ruling).
--
-- ONE paste, ONE run = ONE transaction. Output = the counts AFTER. Re-runnable: a second run
-- changes no personal data (it only re-stamps updated_at on those stubs).
BEGIN;
SELECT public.delete_user_cascade(u.id)
  FROM public.users AS u
 WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id);
UPDATE public.admin_audit_log AS l
   SET ip_address = NULL
 WHERE l.user_id IS NOT NULL
   AND l.ip_address IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = l.user_id);
COMMIT;
SELECT
  (SELECT count(*) FROM public.users AS u
    WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id)
      AND (u.email IS NOT NULL OR u.display_name IS NOT NULL OR u.demographics_profile IS NOT NULL)) AS c_after,
  (SELECT count(*) FROM public.admin_audit_log AS l
    WHERE l.user_id IS NOT NULL AND l.ip_address IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = l.user_id)) AS d_after,
  (
      (SELECT count(*) FROM public.comparisons AS t
        WHERE t.user_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
          AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id))
    + (SELECT count(*) FROM public.comparison_feedback AS t
        WHERE t.user_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
          AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id))
    + (SELECT count(*) FROM public.search_logs AS t
        WHERE t.user_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
          AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id))
    + (SELECT count(*) FROM public.user_events AS t
        WHERE t.user_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
          AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id))
  ) AS f_after;
-- EXPECTED: c_after = 0, d_after = 0. f_after is NOT erased by this file (it equals the sum of
-- the PRECHECK section 9 f rows); above 0 = send the grid back.

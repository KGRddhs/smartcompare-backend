-- Rollback for migration 049 (S81-SF1 SURFACES-BE): share_target widening and the
-- two compare_request_id columns.
--
-- Unset ENABLE_FEEDBACK_V2 on web FIRST. Refuses (RAISE, the whole rollback rolls
-- back) while an invite with share_target sms / email / more exists: the six-value
-- CHECK of 014 cannot be restored over them (owner call: delete or relabel them).
-- DESTRUCTIVE for user_events.compare_request_id and search_logs.compare_request_id
-- (the columns and their partial indexes are dropped).

BEGIN;

DO $$
BEGIN
    IF exists(
        SELECT 1 FROM public.referral_invites
        WHERE share_target IN ('sms', 'email', 'more')
    ) THEN
        RAISE EXCEPTION 'rollback 049: sms / email / more invites exist; the six-value CHECK cannot be restored';
    END IF;
END
$$;

ALTER TABLE public.referral_invites
DROP CONSTRAINT IF EXISTS referral_invites_share_target_check;

ALTER TABLE public.referral_invites
ADD CONSTRAINT referral_invites_share_target_check
CHECK (share_target IN ('whatsapp', 'copy', 'x', 'telegram', 'snapchat', 'other'));

ALTER TABLE public.user_events
DROP COLUMN IF EXISTS compare_request_id;

ALTER TABLE public.search_logs
DROP COLUMN IF EXISTS compare_request_id;

COMMIT;

NOTIFY pgrst, 'reload schema';

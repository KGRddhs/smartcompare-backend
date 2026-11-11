-- Migration 049: share_target widening + compare_request_id columns (S81-SF1 SURFACES-BE)
--
-- WRITTEN NOT APPLIED. MERGING THIS FILE CHANGES NOTHING IN PRODUCTION: the owner
-- applies it (APPLY_049_1_PRECHECK, APPLY_049_2_ONE_PASTE, APPLY_049_3_POSTCHECK in
-- the session-81 state folder) after 046, and only then turns ENABLE_FEEDBACK_V2 on
-- (RULINGS_S81_SF1 R-SF1-29). Independent of 046 in content; applied after it.
--
-- 1. public.referral_invites.share_target: the 014 inline CHECK (six values) is
--    re-created with nine values (+ 'sms', 'email', 'more', the share builder's new
--    targets). The live constraint name is resolved from pg_constraint inside the
--    guard (exactly one CHECK mentioning share_target, else RAISE) and dropped by
--    that name; the new one is named referral_invites_share_target_check.
-- 2. public.user_events.compare_request_id and public.search_logs.compare_request_id:
--    uuid NULL (the per-compare request id) + the partial indexes
--    idx_user_events_request / idx_search_logs_request (an immutable predicate; the
--    column is all NULL at apply time).
--
-- Locks: every ALTER holds ACCESS EXCLUSIVE on its table until COMMIT, the new CHECK
-- validates every referral_invites row and each partial index build scans its table;
-- lock_timeout 5s makes a busy table fail fast. Apply in a quiet window.
--
-- No function, no RLS policy, no GRANT / REVOKE.
-- Rollback: migrations/rollback/049_share_target_and_request_ids.sql (unset the flag
-- first; it refuses while an sms / email / more invite exists).

BEGIN;

SET LOCAL lock_timeout = '5s';

DO $$
DECLARE
    n_checks integer;
    live_name text;
BEGIN
    IF to_regclass('public.referral_invites') IS NULL
        OR to_regclass('public.user_events') IS NULL
        OR to_regclass('public.search_logs') IS NULL THEN
        RAISE EXCEPTION '049 guard: referral_invites, user_events or search_logs is missing';
    END IF;
    SELECT
        count(*),
        min(k.conname)
    INTO n_checks, live_name
    FROM pg_constraint AS k
    WHERE
        k.conrelid = 'public.referral_invites'::regclass
        AND k.contype = 'c'
        AND pg_get_constraintdef(k.oid) ILIKE '%share_target%';
    IF n_checks <> 1 THEN
        RAISE EXCEPTION '049 guard: expected exactly one share_target CHECK, found %', n_checks;
    END IF;
    EXECUTE format('ALTER TABLE public.referral_invites DROP CONSTRAINT %I', live_name);
END
$$;

ALTER TABLE public.referral_invites
ADD CONSTRAINT referral_invites_share_target_check
CHECK (
    share_target IN (
        'whatsapp', 'copy', 'x', 'telegram', 'snapchat', 'other', 'sms', 'email', 'more'
    )
);

ALTER TABLE public.user_events
ADD COLUMN IF NOT EXISTS compare_request_id uuid NULL;

CREATE INDEX IF NOT EXISTS idx_user_events_request
ON public.user_events (compare_request_id)
WHERE compare_request_id IS NOT NULL;

ALTER TABLE public.search_logs
ADD COLUMN IF NOT EXISTS compare_request_id uuid NULL;

CREATE INDEX IF NOT EXISTS idx_search_logs_request
ON public.search_logs (compare_request_id)
WHERE compare_request_id IS NOT NULL;

DO $$
BEGIN
    IF (
        SELECT count(*)
        FROM pg_constraint AS k
        WHERE
            k.conrelid = 'public.referral_invites'::regclass
            AND k.contype = 'c'
            AND k.conname = 'referral_invites_share_target_check'
            AND pg_get_constraintdef(k.oid) ILIKE '%''sms''%'
            AND pg_get_constraintdef(k.oid) ILIKE '%''email''%'
            AND pg_get_constraintdef(k.oid) ILIKE '%''more''%'
    ) <> 1 THEN
        RAISE EXCEPTION '049 assert: the widened share_target CHECK is missing';
    END IF;
    IF (
        SELECT count(*)
        FROM information_schema.columns AS c
        WHERE
            c.table_schema = 'public'
            AND c.table_name IN ('user_events', 'search_logs')
            AND c.column_name = 'compare_request_id'
            AND c.data_type = 'uuid'
    ) <> 2 THEN
        RAISE EXCEPTION '049 assert: a compare_request_id column is missing';
    END IF;
    IF to_regclass('public.idx_user_events_request') IS NULL
        OR to_regclass('public.idx_search_logs_request') IS NULL THEN
        RAISE EXCEPTION '049 assert: a compare_request_id index is missing';
    END IF;
END
$$;

COMMIT;

NOTIFY pgrst, 'reload schema';

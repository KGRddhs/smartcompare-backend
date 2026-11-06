-- APPLY_049_3_POSTCHECK (S81-SF1 SURFACES-BE): READ-ONLY, one row, AFTER the one
-- paste. Expected: share_target_check_count 1, share_target_check_name
-- referral_invites_share_target_check, share_target_check_def carrying the nine values
-- (... 'other', 'sms', 'email', 'more'), events_request_uuid t,
-- search_logs_request_uuid t, events_request_index t, search_logs_request_index t.
SELECT
    (
        SELECT count(*) FROM pg_constraint AS k
        WHERE k.conrelid = to_regclass('public.referral_invites') AND k.contype = 'c'
            AND pg_get_constraintdef(k.oid) ILIKE '%share_target%'
    ) AS share_target_check_count,
    (
        SELECT min(k.conname) FROM pg_constraint AS k
        WHERE k.conrelid = to_regclass('public.referral_invites') AND k.contype = 'c'
            AND pg_get_constraintdef(k.oid) ILIKE '%share_target%'
    ) AS share_target_check_name,
    (
        SELECT min(pg_get_constraintdef(k.oid)) FROM pg_constraint AS k
        WHERE k.conrelid = to_regclass('public.referral_invites') AND k.contype = 'c'
            AND pg_get_constraintdef(k.oid) ILIKE '%share_target%'
    ) AS share_target_check_def,
    (
        SELECT c.data_type = 'uuid' FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'user_events'
            AND c.column_name = 'compare_request_id'
    ) AS events_request_uuid,
    (
        SELECT c.data_type = 'uuid' FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name = 'search_logs'
            AND c.column_name = 'compare_request_id'
    ) AS search_logs_request_uuid,
    to_regclass('public.idx_user_events_request') IS NOT NULL AS events_request_index,
    to_regclass('public.idx_search_logs_request') IS NOT NULL AS search_logs_request_index;

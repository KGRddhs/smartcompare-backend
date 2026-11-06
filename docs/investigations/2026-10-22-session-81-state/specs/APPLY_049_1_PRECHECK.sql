-- APPLY_049_1_PRECHECK (S81-SF1 SURFACES-BE): READ-ONLY, one row, AFTER 046 and
-- BEFORE APPLY_049_2_ONE_PASTE. Expected: the three tables present,
-- share_target_check_count 1, share_target_check_def the six 014 values,
-- request_columns_absent t. RECORD share_target_check_name (the live name 049 drops)
-- and the three row counts (the CHECK validates every invite; each partial index
-- build scans its table).
SELECT
    to_regclass('public.referral_invites') IS NOT NULL AS invites_present,
    to_regclass('public.user_events') IS NOT NULL AS events_present,
    to_regclass('public.search_logs') IS NOT NULL AS search_logs_present,
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
        SELECT count(*) = 0 FROM information_schema.columns AS c
        WHERE c.table_schema = 'public' AND c.table_name IN ('user_events', 'search_logs')
            AND c.column_name = 'compare_request_id'
    ) AS request_columns_absent,
    (SELECT count(*) FROM public.referral_invites) AS invites_row_count,
    (SELECT count(*) FROM public.user_events) AS events_row_count,
    (SELECT count(*) FROM public.search_logs) AS search_logs_row_count;

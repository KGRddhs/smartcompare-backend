-- APPLY_048_1_PRECHECK.sql: S81-22 migration 048 (compare_runs + compare_judgements +
-- compare_runs_prune + the delete_user_cascade kb_feedback hook), step 1 of 3.
--
-- Read-only. Paste into the Supabase SQL editor and Run. Expected grid (one row):
--   pg15_or_later              = true
--   cascade_043_applied        = true  (the live delete_user_cascade body names
--                                       user_preference_history; if false, STOP:
--                                       043 is not applied)
--   kb_045_applied             = true  (public.kb_feedback exists; if false, STOP:
--                                       apply 045 first, then come back)
--   kb_feedback_request_column = true  (kb_feedback.compare_request_id exists)
--   comparisons_id_column      = true  (public.comparisons.id exists)
--   compare_runs_absent        = true  (048 not applied yet; if false, send the
--                                       grid: the guard refuses a stale table with
--                                       a different column set)
--   compare_judgements_absent  = true
--   service_role_exists        = true
--   anon_exists                = true
--   authenticated_exists       = true
--   cascade_body_md5           = (record it: the live 043 body, for the rollback check)
-- Any other value: do not run step 2; send the grid back.

SELECT
    current_setting('server_version_num')::int >= 150000 AS pg15_or_later,
    position('user_preference_history' IN pg_get_functiondef(
        'public.delete_user_cascade(uuid)'::regprocedure
    )) > 0 AS cascade_043_applied,
    to_regclass('public.kb_feedback') IS NOT NULL AS kb_045_applied,
    exists(
        SELECT 1 FROM information_schema.columns AS col
        WHERE col.table_schema = 'public' AND col.table_name = 'kb_feedback'
            AND col.column_name = 'compare_request_id'
    ) AS kb_feedback_request_column,
    exists(
        SELECT 1 FROM information_schema.columns AS col
        WHERE col.table_schema = 'public' AND col.table_name = 'comparisons'
            AND col.column_name = 'id'
    ) AS comparisons_id_column,
    to_regclass('public.compare_runs') IS NULL AS compare_runs_absent,
    to_regclass('public.compare_judgements') IS NULL AS compare_judgements_absent,
    exists(SELECT 1 FROM pg_roles WHERE rolname = 'service_role') AS service_role_exists,
    exists(SELECT 1 FROM pg_roles WHERE rolname = 'anon') AS anon_exists,
    exists(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') AS authenticated_exists,
    md5(pg_get_functiondef('public.delete_user_cascade(uuid)'::regprocedure)) AS cascade_body_md5;

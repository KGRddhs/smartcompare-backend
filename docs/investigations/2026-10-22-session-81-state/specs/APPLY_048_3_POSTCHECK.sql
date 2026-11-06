-- APPLY_048_3_POSTCHECK.sql: S81-22 migration 048, step 3 of 3.
--
-- Read-only except the bounded prune proof (compare_runs_prune(3650) deletes rows older
-- than ten years: none exist). Run AFTER step 2. Expected grid (one row):
--   runs_present             = true
--   judgements_present       = true
--   runs_rls                 = true
--   judgements_rls           = true
--   policy_count             = 0
--   runs_column_count        = 25
--   judgements_column_count  = 10
--   runs_sr_insert           = true
--   runs_sr_update           = true
--   runs_anon_select         = false
--   runs_authenticated_select = false
--   judgements_sr_insert     = true
--   judgements_anon_select   = false
--   prune_sr_execute         = true
--   prune_anon_execute       = false
--   prune_result             = 0
--   cascade_has_hook         = true  (the live body deletes from public.kb_feedback)
--   cascade_secdef           = true
--   cascade_sr_execute       = true
--   cascade_anon_execute     = false
--   cascade_auth_execute     = false
--   run_row_count            = 0     (nothing writes until ENABLE_COMPARE_RUN_LEDGER)
-- Any other value: send the grid back before any S81-22 flag flips.

SELECT
    to_regclass('public.compare_runs') IS NOT NULL AS runs_present,
    to_regclass('public.compare_judgements') IS NOT NULL AS judgements_present,
    (
        SELECT c.relrowsecurity FROM pg_class AS c
        INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname = 'compare_runs'
    ) AS runs_rls,
    (
        SELECT c.relrowsecurity FROM pg_class AS c
        INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname = 'compare_judgements'
    ) AS judgements_rls,
    (
        SELECT count(*) FROM pg_policies AS p
        WHERE p.schemaname = 'public' AND p.tablename IN ('compare_runs', 'compare_judgements')
    ) AS policy_count,
    (
        SELECT count(*) FROM information_schema.columns AS col
        WHERE col.table_schema = 'public' AND col.table_name = 'compare_runs'
    ) AS runs_column_count,
    (
        SELECT count(*) FROM information_schema.columns AS col
        WHERE col.table_schema = 'public' AND col.table_name = 'compare_judgements'
    ) AS judgements_column_count,
    has_table_privilege('service_role', 'public.compare_runs', 'INSERT') AS runs_sr_insert,
    has_table_privilege('service_role', 'public.compare_runs', 'UPDATE') AS runs_sr_update,
    has_table_privilege('anon', 'public.compare_runs', 'SELECT') AS runs_anon_select,
    has_table_privilege('authenticated', 'public.compare_runs', 'SELECT') AS runs_authenticated_select,
    has_table_privilege('service_role', 'public.compare_judgements', 'INSERT') AS judgements_sr_insert,
    has_table_privilege('anon', 'public.compare_judgements', 'SELECT') AS judgements_anon_select,
    has_function_privilege(
        'service_role', 'public.compare_runs_prune(integer)', 'EXECUTE'
    ) AS prune_sr_execute,
    has_function_privilege('anon', 'public.compare_runs_prune(integer)', 'EXECUTE') AS prune_anon_execute,
    public.compare_runs_prune(3650) AS prune_result,
    position('public.kb_feedback' IN pg_get_functiondef(
        'public.delete_user_cascade(uuid)'::regprocedure
    )) > 0 AS cascade_has_hook,
    (
        SELECT p.prosecdef FROM pg_proc AS p
        WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure
    ) AS cascade_secdef,
    has_function_privilege(
        'service_role', 'public.delete_user_cascade(uuid)', 'EXECUTE'
    ) AS cascade_sr_execute,
    has_function_privilege('anon', 'public.delete_user_cascade(uuid)', 'EXECUTE') AS cascade_anon_execute,
    has_function_privilege(
        'authenticated', 'public.delete_user_cascade(uuid)', 'EXECUTE'
    ) AS cascade_auth_execute,
    (SELECT count(*) FROM public.compare_runs) AS run_row_count;

-- 043 POST-CHECK (U8b). ONE run, AFTER the one-paste. Paste the WHOLE grid back.
-- The dry run calls the function with the NIL uuid: no account has it (Supabase mints v4 uuids;
-- PRECHECK section 12 showed 0 nil-uuid rows), so every statement runs, every table and column
-- resolves, and zero rows change. The CTE call is VOLATILE, so it is evaluated exactly once.
WITH dry AS (
    SELECT public.delete_user_cascade('00000000-0000-0000-0000-000000000000'::uuid) AS r
)
SELECT x.sec, x.kind, x.item, x.detail
FROM (
    SELECT 1 AS sec, 'dry_run' AS kind, 'delete_user_cascade(nil uuid)' AS item, 'ok' AS detail
      FROM dry
    UNION ALL
    SELECT 2, 'function', p.oid::regprocedure::text,
           'secdef=' || p.prosecdef::text
           || ' config=' || coalesce(array_to_string(p.proconfig, ','), '-')
           || ' owner=' || pg_get_userbyid(p.proowner)::text
           || ' acl=' || coalesce(p.proacl::text, 'NULL')
           || ' md5_norm=' || md5(btrim(regexp_replace(
                  regexp_replace(p.prosrc, '^\s*-{2}.*$', '', 'gn'), '\s+', ' ', 'g')))
      FROM pg_proc AS p
     WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure
    UNION ALL
    SELECT 3, 'execute_privilege', r.rolname::text,
           has_function_privilege(r.rolname, 'public.delete_user_cascade(uuid)', 'EXECUTE')::text
      FROM pg_roles AS r
     WHERE r.rolname IN ('service_role', 'anon', 'authenticated')
    UNION ALL
    SELECT 4, 'count', 'users rows with the nil uuid', count(*)::text
      FROM public.users
     WHERE id = '00000000-0000-0000-0000-000000000000'::uuid
) AS x
ORDER BY x.sec, x.item;
-- EXPECTED:
--   1 dry_run ok
--   2 secdef=true config=search_path=public owner=postgres
--     acl=<unchanged from PRECHECK section 6> md5_norm=970e7ecc98821f8e97581ee76d4162c9
--   3 service_role true, anon false, authenticated false
--   4 count 0
-- Any other value: STOP and send the grid back. To undo the FUNCTION (not the data), run
-- migrations/rollback/043_delete_user_cascade_full_erasure.sql as one paste.

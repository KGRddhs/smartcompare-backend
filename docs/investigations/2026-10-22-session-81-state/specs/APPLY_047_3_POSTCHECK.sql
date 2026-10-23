-- APPLY_047_3_POSTCHECK.sql -- S81-14 migration 047 (the 012-table REVOKE), step 3 of 3.
--
-- Read-only. Run AFTER step 2. Expected grid (three rows, one per table), every row:
--   relrowsecurity        = true
--   policy_count          = 0      (the eight 012 policies are dropped by name)
--   anon_select           = false
--   anon_insert           = false
--   anon_update           = false
--   anon_delete           = false
--   authenticated_select  = false
--   authenticated_insert  = false
--   authenticated_update  = false
--   authenticated_delete  = false
--   public_any            = false  (no privilege of any kind left to PUBLIC)
--   sr_select             = true   (every app reader and writer uses the service-role client)
--   sr_insert             = true
--   sr_update             = true
--   sr_delete             = true   (the text_routes cache flush DELETEs product_prices)
-- Any other value: send the grid back.

SELECT
    c.relname AS table_name,
    c.relrowsecurity,
    (
        SELECT count(*)
        FROM pg_policies AS pol
        WHERE pol.schemaname = 'public' AND pol.tablename = c.relname
    ) AS policy_count,
    has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
    has_table_privilege('anon', c.oid, 'INSERT') AS anon_insert,
    has_table_privilege('anon', c.oid, 'UPDATE') AS anon_update,
    has_table_privilege('anon', c.oid, 'DELETE') AS anon_delete,
    has_table_privilege('authenticated', c.oid, 'SELECT') AS authenticated_select,
    has_table_privilege('authenticated', c.oid, 'INSERT') AS authenticated_insert,
    has_table_privilege('authenticated', c.oid, 'UPDATE') AS authenticated_update,
    has_table_privilege('authenticated', c.oid, 'DELETE') AS authenticated_delete,
    has_table_privilege('public', c.oid, 'SELECT')
    OR has_table_privilege('public', c.oid, 'INSERT')
    OR has_table_privilege('public', c.oid, 'UPDATE')
    OR has_table_privilege('public', c.oid, 'DELETE')
    OR has_table_privilege('public', c.oid, 'TRUNCATE') AS public_any,
    has_table_privilege('service_role', c.oid, 'SELECT') AS sr_select,
    has_table_privilege('service_role', c.oid, 'INSERT') AS sr_insert,
    has_table_privilege('service_role', c.oid, 'UPDATE') AS sr_update,
    has_table_privilege('service_role', c.oid, 'DELETE') AS sr_delete
FROM pg_class AS c
INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
WHERE n.nspname = 'public' AND c.relname IN ('product_specs', 'product_prices', 'product_reviews')
ORDER BY c.relname;

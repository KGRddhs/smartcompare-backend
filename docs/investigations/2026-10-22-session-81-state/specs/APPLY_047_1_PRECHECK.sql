-- APPLY_047_1_PRECHECK.sql -- S81-14 migration 047 (the 012-table REVOKE), step 1 of 3.
--
-- Read-only: the live pg_policies read 047 waits on. Paste into the Supabase SQL editor and
-- Run, then send the whole grid back (three rows, one per table) BEFORE step 2; the
-- orchestrator confirms the policy names and records the relacl text (the rollback restores
-- the stock grants and must be compared with it). Expected today (migration 012 as written):
--   product_specs    policies = specs_select:SELECT:{public}, specs_insert:INSERT:{public},
--                               specs_update:UPDATE:{public}            policy_count = 3
--   product_prices   policies = prices_select:SELECT:{public}, prices_insert:INSERT:{public}
--                                                                       policy_count = 2
--   product_reviews  policies = reviews_select:SELECT:{public}, reviews_insert:INSERT:{public},
--                               reviews_update:UPDATE:{public}          policy_count = 3
--   relrowsecurity = true on all three;
--   anon_* and authenticated_* privileges: true on a stock project (the poisoning path 047
--   closes); sr_* (service_role) = true for SELECT, INSERT, UPDATE, DELETE.
-- A policy name beyond those eight: still run 047 (a REVOKE removes the table privilege, a
-- policy cannot grant one), and the extra policy is dropped by name in a follow-up.

SELECT
    c.relname AS table_name,
    c.relrowsecurity,
    c.relacl::text AS relacl_text,
    (
        SELECT
            string_agg(
                pol.policyname || ':' || pol.cmd || ':' || pol.roles::text, ', '
                ORDER BY pol.policyname
            )
        FROM pg_policies AS pol
        WHERE pol.schemaname = 'public' AND pol.tablename = c.relname
    ) AS policies,
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
    has_table_privilege('service_role', c.oid, 'SELECT') AS sr_select,
    has_table_privilege('service_role', c.oid, 'INSERT') AS sr_insert,
    has_table_privilege('service_role', c.oid, 'UPDATE') AS sr_update,
    has_table_privilege('service_role', c.oid, 'DELETE') AS sr_delete
FROM pg_class AS c
INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
WHERE n.nspname = 'public' AND c.relname IN ('product_specs', 'product_prices', 'product_reviews')
ORDER BY c.relname;

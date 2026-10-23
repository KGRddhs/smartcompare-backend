-- APPLY_045_1_PRECHECK.sql -- S81-14 migration 045 (the kb_* knowledge-base core), step 1 of 3.
--
-- Read-only. Paste into the Supabase SQL editor and Run. Expected grid (one row):
--   pg15_or_later           = true   (045 refuses PostgreSQL < 15: security_invoker views)
--   kb_relations_present    = 0      (no table, view or index named kb_* yet; if > 0, STOP and
--                                     send the grid: CREATE TABLE IF NOT EXISTS would skip a stale
--                                     table and leave its columns, checks and grants unchanged)
--   kb_functions_present    = 0      (none of the five 045 functions exists yet)
--   gen_random_uuid_present = true   (pg 13+ built-in; migrations 002, 011, 012 use it)
--   service_role_exists     = true
--   anon_exists             = true
--   authenticated_exists    = true
-- Any other value: do not run step 2; send the grid back.

SELECT
    current_setting('server_version_num')::int >= 150000 AS pg15_or_later,
    (
        SELECT count(*)
        FROM pg_class AS c
        INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname LIKE 'kb\_%'
    ) AS kb_relations_present,
    (
        SELECT count(*)
        FROM pg_proc AS p
        INNER JOIN pg_namespace AS n ON p.pronamespace = n.oid
        WHERE
            n.nspname = 'public'
            AND p.proname IN (
                'kb_gtin_check_digit_ok', 'kb_set_updated_at', 'kb_prune_offers',
                'kb_prune_feedback', 'kb_product_card'
            )
    ) AS kb_functions_present,
    EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'gen_random_uuid') AS gen_random_uuid_present,
    EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'service_role') AS service_role_exists,
    EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'anon') AS anon_exists,
    EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') AS authenticated_exists;

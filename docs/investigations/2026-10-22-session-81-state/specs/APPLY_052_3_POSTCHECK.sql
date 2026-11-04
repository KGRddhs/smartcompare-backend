-- APPLY_052_3_POSTCHECK.sql: S81-16b migration 052 (public.kb_brands), step 3 of 3.
--
-- Read-only. Run AFTER step 2. Expected grid (one row), every column as shown:
--   table_present         = true
--   relrowsecurity        = true
--   policy_count          = 0
--   column_count          = 7     (qid, label_en, label_ar, official_host, source, created_at, updated_at)
--   check_count           = 6     (qid; label_en + btrim; label_ar + btrim; official_host; source; the top-label constraint)
--   fk_count              = 0     (no foreign key: kb_products.brand stays free text)
--   trigger_present       = true  (kb_brands_set_updated_at, BEFORE UPDATE)
--   host_index_present    = true  (idx_kb_brands_official_host, partial)
--   host_index_unique     = false (two brands may share one official host)
--   sr_select             = true
--   sr_insert             = true
--   sr_update             = true
--   sr_delete             = true
--   sr_truncate           = false (REVOKE ALL removed the default grant)
--   anon_select           = false
--   anon_insert           = false
--   anon_update           = false
--   anon_delete           = false
--   anon_truncate         = false
--   authenticated_select  = false
--   authenticated_insert  = false
--   authenticated_update  = false
--   authenticated_delete  = false
--   authenticated_truncate = false
--   row_count             = 0     (nothing writes the table until ENABLE_KB_BRANDS=apply)
-- Any other value: send the grid back before any ENABLE_KB_BRANDS command runs.

SELECT
    to_regclass('public.kb_brands') IS NOT NULL AS table_present,
    (
        SELECT c.relrowsecurity FROM pg_class AS c
        INNER JOIN pg_namespace AS n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public' AND c.relname = 'kb_brands'
    ) AS relrowsecurity,
    (
        SELECT count(*) FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'kb_brands'
    ) AS policy_count,
    (
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'kb_brands'
    ) AS column_count,
    (
        SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'public.kb_brands'::regclass AND contype = 'c'
    ) AS check_count,
    (
        SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'public.kb_brands'::regclass AND contype = 'f'
    ) AS fk_count,
    exists(
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'public.kb_brands'::regclass AND tgname = 'kb_brands_set_updated_at'
    ) AS trigger_present,
    to_regclass('public.idx_kb_brands_official_host') IS NOT NULL AS host_index_present,
    coalesce((
        SELECT i.indisunique FROM pg_index AS i
        WHERE i.indexrelid = to_regclass('public.idx_kb_brands_official_host')
    ), false) AS host_index_unique,
    has_table_privilege('service_role', 'public.kb_brands', 'SELECT') AS sr_select,
    has_table_privilege('service_role', 'public.kb_brands', 'INSERT') AS sr_insert,
    has_table_privilege('service_role', 'public.kb_brands', 'UPDATE') AS sr_update,
    has_table_privilege('service_role', 'public.kb_brands', 'DELETE') AS sr_delete,
    has_table_privilege('service_role', 'public.kb_brands', 'TRUNCATE') AS sr_truncate,
    has_table_privilege('anon', 'public.kb_brands', 'SELECT') AS anon_select,
    has_table_privilege('anon', 'public.kb_brands', 'INSERT') AS anon_insert,
    has_table_privilege('anon', 'public.kb_brands', 'UPDATE') AS anon_update,
    has_table_privilege('anon', 'public.kb_brands', 'DELETE') AS anon_delete,
    has_table_privilege('anon', 'public.kb_brands', 'TRUNCATE') AS anon_truncate,
    has_table_privilege('authenticated', 'public.kb_brands', 'SELECT') AS authenticated_select,
    has_table_privilege('authenticated', 'public.kb_brands', 'INSERT') AS authenticated_insert,
    has_table_privilege('authenticated', 'public.kb_brands', 'UPDATE') AS authenticated_update,
    has_table_privilege('authenticated', 'public.kb_brands', 'DELETE') AS authenticated_delete,
    has_table_privilege('authenticated', 'public.kb_brands', 'TRUNCATE') AS authenticated_truncate,
    (SELECT count(*) FROM public.kb_brands) AS row_count;

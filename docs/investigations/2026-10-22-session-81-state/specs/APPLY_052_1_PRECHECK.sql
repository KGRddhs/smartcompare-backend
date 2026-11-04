-- APPLY_052_1_PRECHECK.sql: S81-16b migration 052 (public.kb_brands), step 1 of 3.
--
-- Read-only. Paste into the Supabase SQL editor and Run. Expected grid (one row):
--   pg15_or_later        = true  (045, which 052 builds on, needs PostgreSQL 15)
--   kb_045_applied       = true  (public.kb_set_updated_at exists; if false, STOP:
--                                 apply 045 then 047 first, owner item 29)
--   kb_brands_absent     = true  (052 not applied yet; if false, STOP and send the
--                                 grid: CREATE TABLE IF NOT EXISTS would keep a stale table)
--   service_role_exists  = true
--   anon_exists          = true
--   authenticated_exists = true
-- Any other value: do not run step 2; send the grid back.

SELECT
    current_setting('server_version_num')::int >= 150000 AS pg15_or_later,
    to_regprocedure('public.kb_set_updated_at()') IS NOT NULL AS kb_045_applied,
    to_regclass('public.kb_brands') IS NULL AS kb_brands_absent,
    exists(SELECT 1 FROM pg_roles WHERE rolname = 'service_role') AS service_role_exists,
    exists(SELECT 1 FROM pg_roles WHERE rolname = 'anon') AS anon_exists,
    exists(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') AS authenticated_exists;

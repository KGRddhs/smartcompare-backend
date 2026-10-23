-- APPLY_050_1_PRECHECK.sql -- S81-03 migration 050 (public.llm_spend_ledger), step 1 of 3.
--
-- Read-only. Paste into the Supabase SQL editor and Run. Expected grid (one row):
--   table_absent            = true   (050 not applied yet; if false, STOP: compare the live
--                                     columns with migrations/050_llm_spend_ledger.sql first,
--                                     because CREATE TABLE IF NOT EXISTS would skip a stale table)
--   gen_random_uuid_present = true   (pgcrypto / pg 13+ built-in; migrations 002, 011, 012 use it)
--   service_role_exists     = true
--   anon_exists             = true
--   authenticated_exists    = true
-- Any other value: do not run step 2; send the grid back.

SELECT
    to_regclass('public.llm_spend_ledger') IS NULL AS table_absent,
    EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'gen_random_uuid') AS gen_random_uuid_present,
    EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') AS service_role_exists,
    EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') AS anon_exists,
    EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') AS authenticated_exists;

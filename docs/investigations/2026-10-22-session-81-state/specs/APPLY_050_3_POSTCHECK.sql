-- APPLY_050_3_POSTCHECK.sql -- S81-03 migration 050 (public.llm_spend_ledger), step 3 of 3.
--
-- Read-only. Run AFTER step 2. Expected grid (one row), every column as shown:
--   table_present        = true
--   relrowsecurity       = true
--   policy_count         = 0
--   column_count         = 22    (id, created_at + the 20 SPEND_LEDGER_COLUMNS)
--   sr_insert            = true
--   sr_select            = true
--   sr_update            = false  (append-only by grant: the service_role default grant was revoked)
--   sr_delete            = false
--   sr_truncate          = false
--   anon_select          = false
--   anon_insert          = false
--   authenticated_select = false
--   authenticated_insert = false
--   row_count            = 0     (nothing writes the table yet)
-- Any other value: send the grid back before anything else is applied.

SELECT
    to_regclass('public.llm_spend_ledger') IS NOT NULL AS table_present,
    (SELECT c.relrowsecurity FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public' AND c.relname = 'llm_spend_ledger') AS relrowsecurity,
    (SELECT count(*) FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'llm_spend_ledger') AS policy_count,
    (SELECT count(*) FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'llm_spend_ledger') AS column_count,
    has_table_privilege('service_role', 'public.llm_spend_ledger', 'INSERT') AS sr_insert,
    has_table_privilege('service_role', 'public.llm_spend_ledger', 'SELECT') AS sr_select,
    has_table_privilege('service_role', 'public.llm_spend_ledger', 'UPDATE') AS sr_update,
    has_table_privilege('service_role', 'public.llm_spend_ledger', 'DELETE') AS sr_delete,
    has_table_privilege('service_role', 'public.llm_spend_ledger', 'TRUNCATE') AS sr_truncate,
    has_table_privilege('anon', 'public.llm_spend_ledger', 'SELECT') AS anon_select,
    has_table_privilege('anon', 'public.llm_spend_ledger', 'INSERT') AS anon_insert,
    has_table_privilege('authenticated', 'public.llm_spend_ledger', 'SELECT') AS authenticated_select,
    has_table_privilege('authenticated', 'public.llm_spend_ledger', 'INSERT') AS authenticated_insert,
    (SELECT count(*) FROM public.llm_spend_ledger) AS row_count;

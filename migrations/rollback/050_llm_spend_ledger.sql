-- Rollback for migration 050_llm_spend_ledger.sql (S81-03, S81)
--
-- No flag needs flipping first: no flag reads or writes the table.
--
-- IMPORTANT: this is destructive. The recorded off-clock spend history is
-- lost (the rows are list-price records, not a bill; the provider consoles
-- keep their own usage).

BEGIN;

DROP TABLE IF EXISTS public.llm_spend_ledger;

COMMIT;

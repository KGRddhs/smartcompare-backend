-- rollback/042_search_logs_is_synthetic.sql
--
-- WARNING -- this DISCARDS the is_synthetic classification (the 042 backfill
-- and every caller-classified row written since the flag flipped).
--
-- Turn ENABLE_SEARCH_LOG_SYNTHETIC_MARKER OFF FIRST, before running this:
-- with the flag ON, every log_search insert names the dropped column, fails,
-- and is swallowed silently (lost analytics), and every admin reader selects
-- the missing column and returns zeros.
--
-- Re-applying 042 afterwards re-runs its backfill idempotently (it only
-- touches rows WHERE is_synthetic IS NULL); rows written between the flip and
-- this rollback lose their caller classification for good.

BEGIN;

ALTER TABLE public.search_logs
DROP COLUMN IF EXISTS is_synthetic;

COMMIT;

NOTIFY pgrst, 'reload schema';

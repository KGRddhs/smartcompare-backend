-- Rollback for Migration 036 (home_savings_aggregate, issue #116).
--
-- Safe at any time: the only caller (app/api/home_routes.py) is gated by
-- ENABLE_HOME_SAVINGS_AGGREGATE and degrades to the legacy inline scan when
-- the rpc errors — but turn the flag OFF first so cache misses do not pay a
-- failed round trip before falling back.

BEGIN;

DROP FUNCTION IF EXISTS public.home_savings_aggregate(uuid);

COMMIT;

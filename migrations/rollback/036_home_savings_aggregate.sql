-- Rollback for 036_home_savings_aggregate.sql (#116).
-- Safe while ENABLE_HOME_SAVINGS_AGGREGATE is OFF (the only caller); with the
-- flag ON the route degrades to the empty payload on the missing function
-- (home_routes fail-safe), so flip the flag OFF before/with this rollback.
DROP FUNCTION IF EXISTS public.home_savings_aggregate(uuid);

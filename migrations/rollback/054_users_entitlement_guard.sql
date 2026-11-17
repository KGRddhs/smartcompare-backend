-- Rollback for migration 054_users_entitlement_guard.sql (INC-T1b USERS-ENTITLEMENT-GUARD)
--
-- Drops exactly what 054 creates: the trigger on public.users, then its
-- function. No row is touched. After this runs, a signed-in API caller can again
-- change their own entitlement columns (the hole 054 closes): run it only on a
-- ruled rollback, then run the read-only check
-- docs/investigations/2026-11-17-session-97-state/APPLY_054_CHECK.sql and expect
-- section 1 and section 2 empty.

BEGIN;

DROP TRIGGER IF EXISTS users_entitlement_guard ON public.users;

DROP FUNCTION IF EXISTS public.users_entitlement_guard();

COMMIT;

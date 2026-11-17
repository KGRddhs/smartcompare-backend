-- 054 CHECK (INC-T1b USERS-ENTITLEMENT-GUARD). Read-only: catalog facts only.
-- Run it ONCE BEFORE the apply of migrations/054_users_entitlement_guard.sql and
-- ONCE AFTER it. Paste the whole grid back. No section reads a public.users row:
-- every section prints names, flags, counts or column defaults.
--
-- Sections, the expected BEFORE / AFTER shape, and the STOP rules (any STOP before
-- the apply: send the grid back, apply nothing):
--   1 trigger_on_users: BEFORE no row named users_entitlement_guard. AFTER one row
--     users_entitlement_guard, enabled=O, function=users_entitlement_guard,
--     before=true, row_level=true, on_insert=true, on_update=true, on_delete=false.
--     STOP before the apply on any other user trigger on public.users (review it).
--   2 guard_function: BEFORE no row. AFTER one row: secdef=false,
--     config holds a search_path entry, owner recorded.
--   3 rls_flags: rls_enabled=true both times (forced may be false).
--   4 policies: one row per policy on public.users with its name, permissive, cmd,
--     roles and the full USING and WITH CHECK text (pg_get_expr). STOP on every
--     DELETE or ALL policy except ONE expected row: policy_name
--     Service role full access, permissive true, cmd ALL, roles public,
--     using_text exactly (auth.role() = 'service_role'::text), with_check_text
--     empty (NULL). That USING test holds only for the server role. Any other
--     DELETE or ALL policy: a self-delete followed by a self-insert at the
--     defaults would reset the counters, which 054 does not stop.
--   5 column_grants: anon / authenticated UPDATE and INSERT counts over the eleven
--     guarded columns (recorded; 054 changes no grant, so BEFORE = AFTER).
--   6 guarded_column_defaults: the eleven guarded columns. STOP unless
--     subscription_tier defaults to 'free'::text, lifetime_comparisons_used,
--     referral_bonus_comparisons_this_month and lifetime_invites_consumed to 0,
--     referral_bonus_reset_at to (date_trunc('month'::text, now()) + '1 mon'::interval)
--     and the other six have no default (NULL). The INSERT arm compares against
--     these values; a different live default makes a signed-in self-insert that
--     omits the column fail (no app path does one: the backend inserts as service role).
--   7 auth_users_triggers: every user trigger on auth.users with its function and
--     security mode (an out-of-band handle_new_user runs without a request role:
--     it passes the guard; recorded for review).
--   8 definer_functions_writing_users: every SECURITY DEFINER function whose body
--     writes public.users, with its owner and whether anon / authenticated may
--     EXECUTE it. STOP on a row where authenticated_exec or anon_exec is true:
--     the guard checks its writes too (the claims role is the caller's).

-- 1 trigger_on_users
SELECT
  '1 trigger_on_users' AS section,
  t.tgname AS trigger_name,
  t.tgenabled AS enabled,
  p.proname AS function_name,
  (t.tgtype::integer & 2) = 2 AS before,
  (t.tgtype::integer & 1) = 1 AS row_level,
  (t.tgtype::integer & 4) = 4 AS on_insert,
  (t.tgtype::integer & 16) = 16 AS on_update,
  (t.tgtype::integer & 8) = 8 AS on_delete
FROM pg_catalog.pg_trigger AS t
INNER JOIN pg_catalog.pg_proc AS p ON t.tgfoid = p.oid
WHERE
  t.tgrelid = 'public.users'::regclass
  AND NOT t.tgisinternal
ORDER BY t.tgname;

-- 2 guard_function
SELECT
  '2 guard_function' AS section,
  p.proname AS function_name,
  p.prosecdef AS secdef,
  p.proconfig AS config,
  pg_catalog.pg_get_userbyid(p.proowner) AS owner
FROM pg_catalog.pg_proc AS p
INNER JOIN pg_catalog.pg_namespace AS n ON p.pronamespace = n.oid
WHERE
  n.nspname = 'public'
  AND p.proname = 'users_entitlement_guard';

-- 3 rls_flags
SELECT
  '3 rls_flags' AS section,
  c.relrowsecurity AS rls_enabled,
  c.relforcerowsecurity AS rls_forced
FROM pg_catalog.pg_class AS c
WHERE c.oid = 'public.users'::regclass;

-- 4 policies
SELECT
  '4 policies' AS section,
  pol.polname AS policy_name,
  pol.polpermissive AS permissive,
  CASE pol.polcmd
    WHEN 'r' THEN 'SELECT'
    WHEN 'a' THEN 'INSERT'
    WHEN 'w' THEN 'UPDATE'
    WHEN 'd' THEN 'DELETE'
    WHEN '*' THEN 'ALL'
  END AS cmd,
  pg_catalog.concat_ws(
    ',',
    CASE WHEN 0::oid = ANY(pol.polroles) THEN 'public' END,
    nullif(
      pg_catalog.array_to_string(
        ARRAY(
          SELECT r.rolname
          FROM pg_catalog.pg_roles AS r
          WHERE r.oid = ANY(pol.polroles)
          ORDER BY r.rolname
        ),
        ','
      ),
      ''
    )
  ) AS roles,
  pg_catalog.pg_get_expr(pol.polqual, pol.polrelid) AS using_text,
  pg_catalog.pg_get_expr(pol.polwithcheck, pol.polrelid) AS with_check_text
FROM pg_catalog.pg_policy AS pol
WHERE pol.polrelid = 'public.users'::regclass
ORDER BY pol.polname;

-- 5 column_grants
SELECT
  '5 column_grants' AS section,
  cp.grantee,
  cp.privilege_type,
  count(*) AS guarded_columns
FROM information_schema.column_privileges AS cp
WHERE
  cp.table_schema = 'public'
  AND cp.table_name = 'users'
  AND cp.grantee IN ('anon', 'authenticated')
  AND cp.privilege_type IN ('INSERT', 'UPDATE')
  AND cp.column_name IN (
    'subscription_tier', 'subscription_expires_at',
    'lifetime_comparisons_used', 'referral_bonus_comparisons_this_month',
    'referral_bonus_reset_at', 'lifetime_invites_consumed',
    'device_fingerprint_hash', 'referral_code', 'terms_accepted_at',
    'terms_version', 'age_attested_at'
  )
GROUP BY cp.grantee, cp.privilege_type
ORDER BY cp.grantee, cp.privilege_type;

-- 6 guarded_column_defaults
SELECT
  '6 guarded_column_defaults' AS section,
  col.column_name,
  col.data_type,
  col.is_nullable,
  col.column_default
FROM information_schema.columns AS col
WHERE
  col.table_schema = 'public'
  AND col.table_name = 'users'
  AND col.column_name IN (
    'subscription_tier', 'subscription_expires_at',
    'lifetime_comparisons_used', 'referral_bonus_comparisons_this_month',
    'referral_bonus_reset_at', 'lifetime_invites_consumed',
    'device_fingerprint_hash', 'referral_code', 'terms_accepted_at',
    'terms_version', 'age_attested_at'
  )
ORDER BY col.column_name;

-- 7 auth_users_triggers
SELECT
  '7 auth_users_triggers' AS section,
  t.tgname AS trigger_name,
  t.tgenabled AS enabled,
  n.nspname AS function_schema,
  p.proname AS function_name,
  p.prosecdef AS secdef
FROM pg_catalog.pg_trigger AS t
INNER JOIN pg_catalog.pg_proc AS p ON t.tgfoid = p.oid
INNER JOIN pg_catalog.pg_namespace AS n ON p.pronamespace = n.oid
WHERE
  t.tgrelid = 'auth.users'::regclass
  AND NOT t.tgisinternal
ORDER BY t.tgname;

-- 8 definer_functions_writing_users
SELECT
  '8 definer_functions_writing_users' AS section,
  n.nspname AS function_schema,
  p.proname AS function_name,
  pg_catalog.pg_get_userbyid(p.proowner) AS owner,
  pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated_exec,
  pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_exec
FROM pg_catalog.pg_proc AS p
INNER JOIN pg_catalog.pg_namespace AS n ON p.pronamespace = n.oid
WHERE
  p.prosecdef
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND p.prosrc ~* '(update|insert\s+into)\s+(public\.)?users\M'
ORDER BY n.nspname, p.proname;

-- 055 CHECK (INC-SEC-1 DATABASE-ACCESS). Read-only: catalog facts only.
-- Run it ONCE BEFORE the apply of migrations/055_app_user_access_tightening.sql
-- and ONCE AFTER it (and after a rollback). ONE statement, so one Run shows one
-- grid with the columns section, object, fact, value. It reads pg_catalog and
-- information_schema only and never a row of a public table.
--
-- Sections (BEFORE / AFTER / STOP; any STOP before the apply: send the grid
-- back, apply nothing):
--   K01 policies: every policy on the ten tables (name, permissive, cmd,
--       roles, USING, WITH CHECK). BEFORE the 26 measured rows; STOP on any
--       row not in the 2026-11-17 catalog. AFTER 10 rows: comparisons_select
--       (authenticated, own rows), comparisons_delete, feedback_select,
--       search_logs_select, events_select, users_select, users_update,
--       usage_select, referral_invites_select_own (referrer only),
--       products_service_role_all.
--   K02 app_role_privileges: every public relation where anon or
--       authenticated holds any privilege, with its kind, owner and the seven
--       privileges per role. STOP BEFORE when set_equals_measured_21 is false.
--       public_acl rows: PUBLIC's own ACL entries (aclexplode, grantee 0).
--       STOP if PUBLIC holds a privilege 055 revokes.
--   K03 service_role: SELECT / INSERT / UPDATE / DELETE on nine tables, SELECT
--       on the three views, and rolbypassrls. STOP on any false, before or after.
--   K04 users_triggers: BEFORE none or 054's trigger; AFTER users_profile_guard
--       plus 054's. STOP on any other.
--   K05 guard_function: AFTER secdef false and a search_path entry.
--   K06 column_defaults: STOP unless email none, created_at now(),
--       attribution_source none, last_comparison_at none, behavior_profile
--       '{}'::jsonb, demographics_profile none.
--   K07 views: reloptions and SELECT for anon and authenticated.
--   K08 resolve_referral_code: secdef, config, EXECUTE per role and PUBLIC's
--       ACL entry. STOP if PUBLIC holds EXECUTE (the 055 assert would abort).
--   K09 table_facts: row security per table, and whether rating_cache exists.
--   K10 definer_functions_writing_users: SECURITY DEFINER functions whose
--       body writes public.users, with EXECUTE for anon or authenticated.
--       STOP on true.
--   K11 server_version_num: STOP unless it is 140000 or more.

WITH grid AS (
  -- K01 policies
  SELECT
    'K01 policies' AS section,
    p.tablename || '.' || p.policyname AS object,
    'policy' AS fact,
    p.permissive || ' | ' || p.cmd || ' | ' || p.roles::text || ' | '
    || coalesce(p.qual, '-') || ' | ' || coalesce(p.with_check, '-') AS value
  FROM pg_catalog.pg_policies AS p
  WHERE
    p.schemaname = 'public'
    AND p.tablename IN (
      'admin_audit_log', 'comparison_feedback', 'comparisons', 'products', 'rating_cache',
      'referral_invites', 'search_logs', 'user_events', 'user_usage', 'users'
    )

  UNION ALL

  -- K02 app_role_privileges: per relation
  SELECT
    'K02 app_role_privileges' AS section,
    c.relname AS object,
    r.role_name AS fact,
    c.relkind::text || ' owner=' || pg_catalog.pg_get_userbyid(c.relowner) || ' '
    || (
      SELECT string_agg(
        pr.priv || '=' || CASE WHEN pg_catalog.has_table_privilege(r.role_name, c.oid, pr.priv) THEN 't' ELSE 'f' END,
        ',' ORDER BY pr.priv
      )
      FROM (
        VALUES ('DELETE'), ('INSERT'), ('REFERENCES'), ('SELECT'), ('TRIGGER'), ('TRUNCATE'), ('UPDATE')
      ) AS pr (priv)
    ) AS value
  FROM pg_catalog.pg_class AS c
  INNER JOIN pg_catalog.pg_namespace AS n ON c.relnamespace = n.oid
  CROSS JOIN (VALUES ('anon'), ('authenticated')) AS r (role_name)
  WHERE
    n.nspname = 'public'
    AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
    AND EXISTS (
      SELECT 1
      FROM (
        VALUES ('DELETE'), ('INSERT'), ('REFERENCES'), ('SELECT'), ('TRIGGER'), ('TRUNCATE'), ('UPDATE')
      ) AS pq (priv)
      CROSS JOIN (VALUES ('anon'), ('authenticated')) AS rq (role_name)
      WHERE pg_catalog.has_table_privilege(rq.role_name, c.oid, pq.priv)
    )

  UNION ALL

  -- K02 app_role_privileges: the set against the measured 21
  SELECT
    'K02 app_role_privileges' AS section,
    '(set)' AS object,
    'set_equals_measured_21' AS fact,
    (
      coalesce(array_agg(c.relname::text ORDER BY c.relname::text), ARRAY[]::text [])
      = ARRAY[
        'admin_audit_log', 'bahrain_approved_drugs', 'comparison_feedback', 'comparisons',
        'deep_review_credits', 'eval_runs', 'pain_workflow_events', 'products', 'rating_cache',
        're_engagement_events', 'referral_invites', 'referral_redemptions', 'search_logs',
        'user_events', 'user_preference_history', 'user_usage', 'users', 'verdict_critiques',
        'vw_cohort_feedback_lift', 'vw_cohort_match_rate', 'vw_cohort_persona_distribution'
      ]::text []
    )::text AS value
  FROM pg_catalog.pg_class AS c
  INNER JOIN pg_catalog.pg_namespace AS n ON c.relnamespace = n.oid
  WHERE
    n.nspname = 'public'
    AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
    AND (
      pg_catalog.has_table_privilege('anon', c.oid, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')
      OR pg_catalog.has_table_privilege(
        'authenticated', c.oid, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER'
      )
    )

  UNION ALL

  -- K02 app_role_privileges: PUBLIC's own ACL entries on public relations
  SELECT
    'K02 app_role_privileges' AS section,
    '(public_acl)' AS object,
    'entries' AS fact,
    coalesce(
      (
        SELECT string_agg(c.relname || ':' || a.privilege_type, ',' ORDER BY c.relname, a.privilege_type)
        FROM pg_catalog.pg_class AS c
        INNER JOIN pg_catalog.pg_namespace AS n ON c.relnamespace = n.oid
        CROSS JOIN LATERAL pg_catalog.aclexplode(c.relacl) AS a
        WHERE
          n.nspname = 'public'
          AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
          AND a.grantee = 0
      ),
      'none'
    ) AS value

  UNION ALL

  -- K03 service_role
  SELECT
    'K03 service_role' AS section,
    t.rel AS object,
    pr.priv AS fact,
    coalesce(pg_catalog.has_table_privilege('service_role', to_regclass(t.rel)::oid, pr.priv), false)::text AS value
  FROM (
    VALUES
    ('public.users'), ('public.comparisons'), ('public.comparison_feedback'), ('public.search_logs'),
    ('public.user_events'), ('public.admin_audit_log'), ('public.referral_invites'),
    ('public.user_usage'), ('public.products')
  ) AS t (rel)
  CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE')) AS pr (priv)

  UNION ALL

  SELECT
    'K03 service_role' AS section,
    v.rel AS object,
    'SELECT' AS fact,
    coalesce(pg_catalog.has_table_privilege('service_role', to_regclass(v.rel)::oid, 'SELECT'), false)::text AS value
  FROM (
    VALUES
    ('public.vw_cohort_match_rate'), ('public.vw_cohort_persona_distribution'), ('public.vw_cohort_feedback_lift')
  ) AS v (rel)

  UNION ALL

  SELECT
    'K03 service_role' AS section,
    'service_role' AS object,
    'rolbypassrls' AS fact,
    coalesce((SELECT ro.rolbypassrls FROM pg_catalog.pg_roles AS ro WHERE ro.rolname = 'service_role'), false)::text
    AS value

  UNION ALL

  -- K04 users_triggers
  SELECT
    'K04 users_triggers' AS section,
    t.tgname::text AS object,
    'trigger' AS fact,
    t.tgenabled::text || ' tgtype=' || t.tgtype::text || ' function=' || t.tgfoid::regprocedure::text AS value
  FROM pg_catalog.pg_trigger AS t
  WHERE
    t.tgrelid = to_regclass('public.users')
    AND NOT t.tgisinternal

  UNION ALL

  -- K05 guard_function
  SELECT
    'K05 guard_function' AS section,
    'public.users_profile_guard()' AS object,
    'present_secdef_config' AS fact,
    coalesce(
      (
        SELECT 'present secdef=' || p.prosecdef::text || ' config=' || coalesce(array_to_string(p.proconfig, ';'), '')
        FROM pg_catalog.pg_proc AS p
        WHERE p.oid = to_regprocedure('public.users_profile_guard()')
      ),
      'absent'
    ) AS value

  UNION ALL

  -- K06 column_defaults
  SELECT
    'K06 column_defaults' AS section,
    col.column_name::text AS object,
    'default' AS fact,
    coalesce(col.column_default::text, 'none') AS value
  FROM information_schema.columns AS col
  WHERE
    col.table_schema = 'public'
    AND col.table_name = 'users'
    AND col.column_name IN (
      'email', 'created_at', 'attribution_source', 'last_comparison_at',
      'behavior_profile', 'demographics_profile'
    )

  UNION ALL

  -- K07 views
  SELECT
    'K07 views' AS section,
    c.relname::text AS object,
    'reloptions_select' AS fact,
    'options=' || coalesce(c.reloptions::text, 'none')
    || ' anon=' || pg_catalog.has_table_privilege('anon', c.oid, 'SELECT')::text
    || ' authenticated=' || pg_catalog.has_table_privilege('authenticated', c.oid, 'SELECT')::text AS value
  FROM pg_catalog.pg_class AS c
  INNER JOIN pg_catalog.pg_namespace AS n ON c.relnamespace = n.oid
  WHERE
    n.nspname = 'public'
    AND c.relname IN ('vw_cohort_match_rate', 'vw_cohort_persona_distribution', 'vw_cohort_feedback_lift')

  UNION ALL

  -- K08 resolve_referral_code
  SELECT
    'K08 resolve_referral_code' AS section,
    'public.resolve_referral_code(text)' AS object,
    'secdef_config_execute' AS fact,
    'secdef=' || p.prosecdef::text
    || ' config=' || coalesce(array_to_string(p.proconfig, ';'), '')
    || ' anon=' || pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')::text
    || ' authenticated=' || pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')::text
    || ' service_role=' || pg_catalog.has_function_privilege('service_role', p.oid, 'EXECUTE')::text AS value
  FROM pg_catalog.pg_proc AS p
  WHERE p.oid = to_regprocedure('public.resolve_referral_code(text)')

  UNION ALL

  SELECT
    'K08 resolve_referral_code' AS section,
    'public.resolve_referral_code(text)' AS object,
    'public_acl' AS fact,
    CASE
      WHEN p.proacl IS NULL THEN 'default_acl_public_execute'
      ELSE coalesce(
        (
          SELECT string_agg(a.privilege_type, ',' ORDER BY a.privilege_type)
          FROM pg_catalog.aclexplode(p.proacl) AS a
          WHERE a.grantee = 0
        ),
        'none'
      )
    END AS value
  FROM pg_catalog.pg_proc AS p
  WHERE p.oid = to_regprocedure('public.resolve_referral_code(text)')

  UNION ALL

  -- K09 table_facts
  SELECT
    'K09 table_facts' AS section,
    t.rel AS object,
    'rls_forced' AS fact,
    coalesce(
      (
        SELECT c.relrowsecurity::text || ' ' || c.relforcerowsecurity::text
        FROM pg_catalog.pg_class AS c
        WHERE c.oid = to_regclass('public.' || t.rel)
      ),
      'absent'
    ) AS value
  FROM (
    VALUES
    ('admin_audit_log'), ('comparison_feedback'), ('comparisons'), ('products'), ('rating_cache'),
    ('referral_invites'), ('search_logs'), ('user_events'), ('user_usage'), ('users')
  ) AS t (rel)

  UNION ALL

  -- K10 definer_functions_writing_users
  SELECT
    'K10 definer_functions_writing_users' AS section,
    n.nspname || '.' || p.proname AS object,
    'app_role_execute' AS fact,
    (
      pg_catalog.has_function_privilege('anon', p.oid, 'EXECUTE')
      OR pg_catalog.has_function_privilege('authenticated', p.oid, 'EXECUTE')
    )::text AS value
  FROM pg_catalog.pg_proc AS p
  INNER JOIN pg_catalog.pg_namespace AS n ON p.pronamespace = n.oid
  WHERE
    p.prosecdef
    AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    AND p.prosrc ~* '(update|insert\s+into)\s+(only\s+)?(public\.)?users\M'

  UNION ALL

  -- K11 server_version_num
  SELECT
    'K11 server_version_num' AS section,
    'server' AS object,
    'at_least_140000' AS fact,
    current_setting('server_version_num') || ' ' || (current_setting('server_version_num')::integer >= 140000)::text
    AS value
)

SELECT
  g.section,
  g.object,
  g.fact,
  g.value
FROM grid AS g
ORDER BY g.section, g.object, g.fact, g.value;

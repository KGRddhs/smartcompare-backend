-- 043 PRE-CHECK (U8b). Read-only. ONE run, BEFORE the one-paste. Paste the WHOLE grid back.
-- No row prints an email, a name or a token: every section prints metadata or a count.
--
-- Sections and STOP rules (any STOP: send the grid back, apply nothing):
--   1 users_column: 27 rows (id, created_at and the 25 erased columns). STOP on a
--     missing or extra column, or nullable=NO on a column 043 sets to NULL.
--   2 users_constraint / 3 users_index: STOP on a CHECK, UNIQUE or unique index
--     (including an expression index such as lower(email)) that a tombstone value
--     ('free', 0, false, now(), NULL) would violate; on a UNIQUE constraint or a
--     unique index declared NULLS NOT DISTINCT (two tombstones then collide on
--     NULL, so the SECOND deletion fails); and on any FOREIGN KEY (contype f)
--     from users to a table other than auth.users, for example
--     subscription_tier -> a plans table without 'free'. The apply-time probe
--     tests CHECK and NOT NULL only: a unique index or an outgoing FK lets the
--     apply pass and then fails a real deletion with a 500.
--   4 fk_into_users_auth_or_comparisons: users_id_fkey ... REFERENCES auth.users
--     ON DELETE CASCADE = branch A; absent = branch B. Shows every FK into
--     public.comparisons (043 detaches other users' user_events and
--     comparison_feedback rows before deleting the comparisons). STOP on an FK
--     into public.comparisons with on_delete=NO ACTION or RESTRICT from a
--     table other than user_events and comparison_feedback (another user's row
--     there blocks the deletion). STOP on an FK
--     into public.users or auth.users from a table that is not one of the 13
--     (users, admin_audit_log, user_events, comparison_feedback, comparisons,
--     search_logs, user_usage, referral_invites, referral_redemptions,
--     deep_review_credits, re_engagement_events, pain_workflow_events,
--     user_preference_history): 043 does not erase that table, and in branch B
--     its rows survive the deletion.
--   5 user_ref_column: every personal-looking column outside users (review).
--   6 function: expect secdef=true config=search_path=public owner=postgres
--     acl={postgres=X/postgres,service_role=X/postgres}
--     md5_norm=76e8e2f65e9d5cb3b29c5ab57ab9bf61 (the 025 body). STOP if the md5
--     differs: the live body is not 025.
--   7 execute_privilege: service_role true, anon false, authenticated false.
--   8 trigger / rule: any user trigger or rewrite rule on the 13 tables or
--     auth.users is reviewed before applying (an archive trigger, a BEFORE
--     DELETE trigger or a DO ALSO / DO INSTEAD rule defeats the erase).
--   9 count: recorded. If c > 0 or d > 0, run APPLY_043_4_BACKFILL_ORPHANS
--     after the POSTCHECK passes. The f rows count rows of accounts deleted
--     OUTSIDE the app (for example from the Supabase Auth dashboard in branch
--     A): comparisons, user_events, comparison_feedback and search_logs rows
--     whose user has neither an auth.users nor a public.users row. Neither 043
--     nor the backfill erases them. If any f is above 0, send the grid back:
--     not a STOP for the apply, but erasing them needs an orchestrator ruling
--     before the privacy policy may say that past deletions are complete.
--   10 cross_user_comparison_refs: rows of OTHER users (or anonymous rows) that
--     point at a comparison; above 0 means 025 deletions may already fail live.
--   11 table_owner_rls: STOP if FORCE ROW LEVEL SECURITY is on for any table, or
--     if the function owner neither owns the table nor has BYPASSRLS (an
--     RLS-filtered DELETE or UPDATE changes 0 rows with no error).
--   12 nil_uuid_rows: STOP if any count is above 0 (the dry runs would erase them).
--   13 auth_audit_log: rows in the Supabase auth audit log (platform data that
--     043 does not touch); recorded for the privacy policy wording.
SELECT x.sec, x.kind, x.item, x.detail
FROM (
    SELECT 1 AS sec, 'users_column' AS kind,
           lpad(c.ordinal_position::text, 2, '0') || ' ' || c.column_name::text AS item,
           c.data_type::text || ' nullable=' || c.is_nullable::text
           || ' default=' || coalesce(c.column_default::text, '-') AS detail
      FROM information_schema.columns AS c
     WHERE c.table_schema = 'public' AND c.table_name = 'users'
    UNION ALL
    SELECT 2, 'users_constraint', con.conname::text,
           con.contype::text || ' ' || pg_get_constraintdef(con.oid)
      FROM pg_constraint AS con
     WHERE con.conrelid = 'public.users'::regclass
    UNION ALL
    SELECT 3, 'users_index', i.indexname::text, i.indexdef
      FROM pg_indexes AS i
     WHERE i.schemaname = 'public' AND i.tablename = 'users'
    UNION ALL
    SELECT 4, 'fk_into_users_auth_or_comparisons',
           con.conrelid::regclass::text || ' ' || con.conname::text,
           'on_delete=' || CASE con.confdeltype
               WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT' WHEN 'c' THEN 'CASCADE'
               WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' END
           || ' ' || pg_get_constraintdef(con.oid)
      FROM pg_constraint AS con
      JOIN pg_class AS rel ON rel.oid = con.conrelid
      JOIN pg_namespace AS ns ON ns.oid = rel.relnamespace
     WHERE con.contype = 'f'
       AND ns.nspname = 'public'
       AND con.confrelid IN ('public.users'::regclass, 'auth.users'::regclass,
                             'public.comparisons'::regclass)
    UNION ALL
    SELECT 5, 'user_ref_column', c.table_name::text || '.' || c.column_name::text,
           c.data_type::text || ' nullable=' || c.is_nullable::text
      FROM information_schema.columns AS c
     WHERE c.table_schema = 'public'
       AND c.table_name <> 'users'
       AND c.column_name::text ~ ('(^|_)(user|owner|account|profile|member|customer|actor|author|referrer|invitee|redeemer)(_user)?_id$'
           || '|^(created|updated|deleted)_by$|email|phone|full_name|first_name|last_name|display_name|address'
           || '|fingerprint|device_id|install_id|anon_id|push_token|(^|_)ip($|_)|ip_address|remote_addr'
           || '|user_agent|session_id|governorate|gender|birth')
    UNION ALL
    SELECT 6, 'function', p.oid::regprocedure::text,
           'secdef=' || p.prosecdef::text
           || ' config=' || coalesce(array_to_string(p.proconfig, ','), '-')
           || ' owner=' || pg_get_userbyid(p.proowner)::text
           || ' acl=' || coalesce(p.proacl::text, 'NULL')
           || ' md5_norm=' || md5(btrim(regexp_replace(
                  regexp_replace(p.prosrc, '^\s*-{2}.*$', '', 'gn'), '\s+', ' ', 'g')))
      FROM pg_proc AS p
     WHERE p.proname = 'delete_user_cascade'
       AND p.pronamespace = 'public'::regnamespace
    UNION ALL
    SELECT 7, 'execute_privilege', r.rolname::text,
           has_function_privilege(r.rolname, 'public.delete_user_cascade(uuid)', 'EXECUTE')::text
      FROM pg_roles AS r
     WHERE r.rolname IN ('service_role', 'anon', 'authenticated')
    UNION ALL
    SELECT 8, 'trigger', t.tgrelid::regclass::text || ' ' || t.tgname::text, pg_get_triggerdef(t.oid)
      FROM pg_trigger AS t
     WHERE NOT t.tgisinternal
       AND t.tgrelid IN ('auth.users'::regclass,
                         'public.users'::regclass,
                         'public.admin_audit_log'::regclass,
                         'public.user_events'::regclass,
                         'public.comparison_feedback'::regclass,
                         'public.comparisons'::regclass,
                         'public.search_logs'::regclass,
                         'public.user_usage'::regclass,
                         'public.referral_invites'::regclass,
                         'public.referral_redemptions'::regclass,
                         'public.deep_review_credits'::regclass,
                         'public.re_engagement_events'::regclass,
                         'public.pain_workflow_events'::regclass,
                         'public.user_preference_history'::regclass)
    UNION ALL
    SELECT 8, 'rule', rw.ev_class::regclass::text || ' ' || rw.rulename::text,
           regexp_replace(pg_get_ruledef(rw.oid), '\s+', ' ', 'g')
      FROM pg_rewrite AS rw
     WHERE rw.rulename <> '_RETURN'
       AND rw.ev_class IN ('auth.users'::regclass,
                           'public.users'::regclass,
                           'public.admin_audit_log'::regclass,
                           'public.user_events'::regclass,
                           'public.comparison_feedback'::regclass,
                           'public.comparisons'::regclass,
                           'public.search_logs'::regclass,
                           'public.user_usage'::regclass,
                           'public.referral_invites'::regclass,
                           'public.referral_redemptions'::regclass,
                           'public.deep_review_credits'::regclass,
                           'public.re_engagement_events'::regclass,
                           'public.pain_workflow_events'::regclass,
                           'public.user_preference_history'::regclass)
    UNION ALL
    SELECT 9, 'count', 'a public.users rows', count(*)::text FROM public.users
    UNION ALL
    SELECT 9, 'count', 'b users rows with no auth.users row', count(*)::text
      FROM public.users AS u
     WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id)
    UNION ALL
    SELECT 9, 'count', 'c (b) rows still holding email, display_name or demographics', count(*)::text
      FROM public.users AS u
     WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = u.id)
       AND (u.email IS NOT NULL OR u.display_name IS NOT NULL OR u.demographics_profile IS NOT NULL)
    UNION ALL
    SELECT 9, 'count', 'd admin_audit_log rows with ip_address whose user has no auth.users row',
           count(*)::text
      FROM public.admin_audit_log AS l
     WHERE l.user_id IS NOT NULL AND l.ip_address IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = l.user_id)
    UNION ALL
    SELECT 9, 'count', 'e rows in 014/028/029 tables whose user has no auth.users row', (
          (SELECT count(*) FROM public.deep_review_credits AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
        + (SELECT count(*) FROM public.re_engagement_events AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
        + (SELECT count(*) FROM public.pain_workflow_events AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
        + (SELECT count(*) FROM public.user_preference_history AS t
            WHERE NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id))
      )::text
    UNION ALL
    SELECT 9, 'count', 'f comparisons rows of a user with no auth.users and no public.users row',
           count(*)::text
      FROM public.comparisons AS t
     WHERE t.user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
       AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id)
    UNION ALL
    SELECT 9, 'count', 'f comparison_feedback rows of a user with no auth.users and no public.users row',
           count(*)::text
      FROM public.comparison_feedback AS t
     WHERE t.user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
       AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id)
    UNION ALL
    SELECT 9, 'count', 'f search_logs rows of a user with no auth.users and no public.users row',
           count(*)::text
      FROM public.search_logs AS t
     WHERE t.user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
       AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id)
    UNION ALL
    SELECT 9, 'count', 'f user_events rows of a user with no auth.users and no public.users row',
           count(*)::text
      FROM public.user_events AS t
     WHERE t.user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE a.id = t.user_id)
       AND NOT EXISTS (SELECT 1 FROM public.users AS u WHERE u.id = t.user_id)
    UNION ALL
    SELECT 10, 'cross_user_comparison_refs', 'user_events.comparison_id', count(*)::text
      FROM public.user_events AS e
      JOIN public.comparisons AS c ON c.id = e.comparison_id
     WHERE e.user_id IS DISTINCT FROM c.user_id
    UNION ALL
    SELECT 10, 'cross_user_comparison_refs', 'comparison_feedback.comparison_id', count(*)::text
      FROM public.comparison_feedback AS f
      JOIN public.comparisons AS c ON c.id = f.comparison_id
     WHERE f.user_id IS DISTINCT FROM c.user_id
    UNION ALL
    SELECT 11, 'table_owner_rls', cl.oid::regclass::text,
           'owner=' || pg_get_userbyid(cl.relowner)::text
           || ' relrowsecurity=' || cl.relrowsecurity::text
           || ' relforcerowsecurity=' || cl.relforcerowsecurity::text
           || ' fn_owner=' || coalesce((
                SELECT pg_get_userbyid(p.proowner)::text || ' rolbypassrls=' || r.rolbypassrls::text
                  FROM pg_proc AS p
                  JOIN pg_roles AS r ON r.oid = p.proowner
                 WHERE p.oid = 'public.delete_user_cascade(uuid)'::regprocedure), '-')
      FROM pg_class AS cl
     WHERE cl.oid IN ('public.users'::regclass,
                      'public.admin_audit_log'::regclass,
                      'public.user_events'::regclass,
                      'public.comparison_feedback'::regclass,
                      'public.comparisons'::regclass,
                      'public.search_logs'::regclass,
                      'public.user_usage'::regclass,
                      'public.referral_invites'::regclass,
                      'public.referral_redemptions'::regclass,
                      'public.deep_review_credits'::regclass,
                      'public.re_engagement_events'::regclass,
                      'public.pain_workflow_events'::regclass,
                      'public.user_preference_history'::regclass)
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'users.id', count(*)::text
      FROM public.users WHERE id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'admin_audit_log.user_id', count(*)::text
      FROM public.admin_audit_log WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'user_events.user_id', count(*)::text
      FROM public.user_events WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'comparison_feedback.user_id', count(*)::text
      FROM public.comparison_feedback WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'comparisons.user_id', count(*)::text
      FROM public.comparisons WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'search_logs.user_id', count(*)::text
      FROM public.search_logs WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'user_usage.user_id', count(*)::text
      FROM public.user_usage WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'referral_invites.referrer_user_id', count(*)::text
      FROM public.referral_invites WHERE referrer_user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'referral_invites.redeemed_by_user_id', count(*)::text
      FROM public.referral_invites WHERE redeemed_by_user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'referral_redemptions.referrer_user_id', count(*)::text
      FROM public.referral_redemptions WHERE referrer_user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'referral_redemptions.invitee_user_id', count(*)::text
      FROM public.referral_redemptions WHERE invitee_user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'deep_review_credits.user_id', count(*)::text
      FROM public.deep_review_credits WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 're_engagement_events.user_id', count(*)::text
      FROM public.re_engagement_events WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'pain_workflow_events.user_id', count(*)::text
      FROM public.pain_workflow_events WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 12, 'nil_uuid_rows', 'user_preference_history.user_id', count(*)::text
      FROM public.user_preference_history WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid
    UNION ALL
    SELECT 13, 'auth_audit_log', 'auth.audit_log_entries rows',
           CASE
               WHEN to_regclass('auth.audit_log_entries') IS NULL THEN 'absent'
               WHEN NOT has_table_privilege('auth.audit_log_entries', 'SELECT') THEN 'no select privilege'
               ELSE substring(query_to_xml(
                        'SELECT count(*) AS c FROM auth.audit_log_entries', false, false, ''
                    )::text FROM '<c>([0-9]+)</c>')
           END
) AS x
ORDER BY x.sec, x.item;

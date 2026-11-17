# INC-SEC-1 DATABASE-ACCESS: unit spec DRAFT (S96 lane, 2026-11-17; class FOCUS: spec, spec review, RED, GREEN, two adversaries)

Written, not applied. Nothing here touches a database. Repo PUBLIC: every gap is described by what is permitted and what must change. ESTABLISHED = read in code or in the catalog. LIKELY = the best reading.

## 0 WHAT
- One companion migration **055** (`migrations/055_app_user_access_tightening.sql`), its rollback, a read-only check, and live proofs written as single DO blocks.
- Three small server changes the walk requires (C1, C2, C3), plus one the brief's F4 line requires (C2b).
- 054 is not changed: it stays byte-equal to PR #415 head 77ac43a9.
- The walk is the sibling file `sec1/INC_SEC1_WALK.md`: 127 references in app/ and scripts/, of which 18 are user-scoped.

## 1 BASE STATE
- origin/main **5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9** (fetched 2026-11-17). PR #415 head **77ac43a945f83587d37b51c1748e8cb9d591c05a** (054, open).
- Catalog: notes `security-review-2026-11-17/catalog/`, read 2026-11-17. The R2 findings are F1-F16; the R1 items are R1-02, R1-05, R1-07, R1-08, R1-09 and R1-10.
- Corrections to R2 found by the walk (ESTABLISHED):
  - **(a)** `create_share_token` already runs on the service client: its only caller (share_routes.py:29) passes no access_token, so database_service.py:611 takes the service branch. The user branch is dead; C1 removes it; no product path changes.
  - **(b)** admin_audit_log and user_usage ARE created in the repo (011:34, 011:8); only rating_cache and bahrain_approved_drugs have no CREATE in migrations/.
  - **(c)** behavior_profile has readers (home_routes.py:763, profile_routes.py:494, structured_comparison_service.py:6068).

## 2 MEASURED GAPS (catalog file:line; each is what is permitted today)
| id | permitted today | catalog |
|---|---|---|
| F1 | Anyone with the public key can read every row whose share token is set, whoever owns it | policies.txt:11 (comparisons_select, `{public}`, own OR share_token NOT NULL) |
| F2 | Anyone can read, add, change and delete rating_cache rows | policies.txt:16 (ALL, `{public}`, USING true); table_grants.txt:23-24 |
| F3 | Signed-out callers can add audit, feedback, search and event rows | policies.txt:3 (audit_insert WITH CHECK true); :5, :7 (feedback x2), :20 (search_logs), :22-23 (events x2), each `OR user_id IS NULL` |
| F4 | A signed-in caller can add or rewrite comparison rows; add feedback naming any comparison; add search and event rows of any content | policies.txt:10, :12 (comparisons insert / update), :5, :7, :20, :22-23 |
| F5 / R1-05 | After 054, the owner of a row can still change email, created_at, attribution_source, last_comparison_at, behavior_profile and demographics_profile (including its server-computed cohort_match) | policies.txt:31, :34 (UPDATE, no WITH CHECK); columns.txt:432-459 |
| F11 / R1-07 | A signed-in caller with no users row can create one outside our sign-up flow | policies.txt:32 (users_insert); table_grants.txt:39-40 |
| F6 | Anyone can read the three cohort views (owner rights) | views.txt:5-7; table_grants.txt:43-48 |
| F12 | Duplicate and out-of-repo policies | policies.txt:5-8, :22-23, :29-31 |
| F7 | A user can insert and update their own user_usage counter | policies.txt:26, :28 |
| F8 | Anyone can call resolve_referral_code (owner rights, no fixed search path) | functions.txt:13 |
| F9 | The app roles hold TRUNCATE, TRIGGER and REFERENCES on 21 objects. eval_runs, verdict_critiques and products are closed by a missing policy only | table_grants.txt:3, :17-18, :21-22, :41-42 |
| F10 | An invitee can read the referrer's invite row | policies.txt:18 |

R1-05's code defect (ESTABLISHED):
- `_load_invitee` selects `id, email, subscription_tier, display_name` (referral_service.py:793), and its fallback dict carries no device field (:686-689).
- So `evaluate_invite` always reads `invitee.get("device_fingerprint_hash")` as None (abuse_detection_service.py:249), and `is_same_device` returns False at :124.
- Result: the same-device control never fires.

## 3 THE WALK, VERDICT PER REMOVAL (the full table: `INC_SEC1_WALK.md`, sections A-G)
| 055 removes | user-scoped references to it | verdict |
|---|---|---|
| the comparisons read branch for shared rows (F1) | 7 reads (database_service.py:517, :550, :718; home_routes.py:270, :804; profile_routes.py:201, :328), each filtered on the caller's user_id or re-checked by the route (history_routes.py:150-154) | SAFE. The share page reads with the server key (database_service.py:684) |
| comparisons INSERT and UPDATE (F4) | 1: database_service.py:640, in create_share_token (dead in production, correction 1a) | CODE CHANGE C1; the insert writer (database_service.py:493) is service |
| comparison_feedback INSERT (F3, F4) | 1: feedback_service.py:184 / :220, the signed-in path | CODE CHANGE C2 (load-bearing: deploy BEFORE 055) |
| search_logs and user_events INSERT (F3, F4) | 0. Writers: database_service.py:830, feedback_service.py:259 and :298, all service | SAFE |
| admin_audit_log INSERT (F3) | 0. Writer: audit_service.py:30-31, service; readers: admin_routes.py:618, :640, :1069, service | SAFE |
| rating_cache, all access (F2) | 0 in app/ or scripts/. Only backend/rating_extractor.py:245, :286 (not deployed) | SAFE |
| users INSERT and the duplicate policies (F11, F12) | 0. Inserts: auth_service.py:408, :830; database_service.py:379, all service | SAFE |
| users: six more guarded columns (F5) | 3 user-scoped writers write only expo_push_token (auth_routes.py:1466) or preferences (:1548, :1622). Every writer of the six is service: database_service.py:916 (demographics), :954 (attribution), structured_comparison_service.py:6103 (behavior_profile), the inserts above (email), delete_user_cascade (048:259-279). Nothing writes created_at or last_comparison_at after insert | SAFE |
| the three cohort views' SELECT (F6) | 0. Readers: admin_routes.py:681, :688, :746, service (:677, :743) | SAFE |
| user_usage INSERT and UPDATE (F7) | 0 references in app/ or scripts/ | SAFE |
| referral_invites: the invitee branch of the read (F10) | 0. Every reader is service (referral_service.py self.client :232; abuse_detection_service.py:112; admin_routes.py) | SAFE |
| resolve_referral_code EXECUTE for anon and authenticated (F8) | 0. Its only caller is referral_service.py:429 (service). The app ships no database client (walk D) | SAFE |
| TRUNCATE, TRIGGER and REFERENCES; full revoke on eval_runs, verdict_critiques and products (F9) | 0 (PostgREST never issues the first three; eval_persistence.py:82, database_service.py:855 and analytics_service.py:182 are service) | SAFE |

The mobile app (walk D) has no supabase dependency and no direct database call: ESTABLISHED. The crons (walk E) all use the service client. backend/ (walk F) is not deployed.

## 4 THE 055 CONTRACT, STATEMENT BY STATEMENT (one transaction; idempotent: every DROP is IF EXISTS, every CREATE follows its own DROP or is OR REPLACE, REVOKE / ALTER FUNCTION SET re-run as no-ops)
Header comment: the WHY per finding (permitted / must change, no misuse text); "MERGING THIS CHANGES NOTHING IN PRODUCTION"; the apply order (section 7); the rollback path; the check path.

| # | statement | closes |
|---|---|---|
| S00 | `BEGIN;` | |
| S01 | `SET LOCAL lock_timeout = '5s';` (inside the transaction, so nothing leaks to a pooled editor session: R1-14 closed by construction) | |
| S02 | `DO $guard$`: raise a fixed `'055 guard: ...'` message if any repo object is missing (users and the six columns, comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, user_usage, referral_invites, the three views, `public.resolve_referral_code(text)`). rating_cache is NOT required (it is out of repo; see S08) | |
| S03-S04 | `DROP POLICY IF EXISTS comparisons_select ON public.comparisons;` then `CREATE POLICY comparisons_select ON public.comparisons FOR SELECT TO authenticated USING (auth.uid() = user_id);` | F1 |
| S05-S06 | `DROP POLICY IF EXISTS comparisons_insert ...; DROP POLICY IF EXISTS comparisons_update ...;` (comparisons_delete is kept) | F4 |
| S07 | `REVOKE INSERT, UPDATE ON public.comparisons FROM anon, authenticated;` | F4, second layer |
| S08 | `DO $rc$`. If `to_regclass('public.rating_cache')` is set, run through EXECUTE: drop the policy named "Service role has full access to rating_cache", and `REVOKE ALL ON public.rating_cache FROM anon, authenticated`. Otherwise raise a NOTICE that it was skipped. The quoted name carries `-- noqa: RF05` as in 041:75 | F2 |
| S09-S10 | `DROP POLICY IF EXISTS audit_insert ON public.admin_audit_log; REVOKE ALL ON public.admin_audit_log FROM anon, authenticated;` | F3 |
| S11-S14 | Drop feedback_insert, "Users can insert own feedback" and "Users can read own feedback" (a duplicate of feedback_select, which is kept). Then `REVOKE INSERT, UPDATE, DELETE ON public.comparison_feedback FROM anon, authenticated;` | F3, F4, F12 |
| S15-S16 | Drop search_logs_insert (search_logs_select is kept). Then REVOKE INSERT, UPDATE, DELETE from anon and authenticated | F3, F4 |
| S17-S19 | Drop events_insert and "Users can insert own events" (events_select is kept). Then REVOKE INSERT, UPDATE, DELETE from anon and authenticated | F3, F4, F12 |
| S20-S23 | Drop users_insert, "Users can read own data", "Users can update own data" and "Service role full access". users_select and users_update are kept. The last one is harmless (it holds only when the request role is the service role), but it is the ALL policy R1-01 had to explain away | F11, F12 |
| S24 | `REVOKE INSERT, DELETE ON public.users FROM anon, authenticated;` (SELECT and UPDATE stay: the three user-scoped writers need UPDATE) | F11, second layer |
| S25 | `CREATE OR REPLACE FUNCTION public.users_profile_guard() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $function$ ... $function$;` See 4.1 | F5, R1-05 |
| S26 | `CREATE OR REPLACE TRIGGER users_profile_guard BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.users_profile_guard();` | F5 |
| S27 | `COMMENT ON FUNCTION public.users_profile_guard() IS 'INC-SEC-1: ...';` | |
| S28 | `REVOKE ALL ON public.vw_cohort_match_rate, public.vw_cohort_persona_distribution, public.vw_cohort_feedback_lift FROM anon, authenticated;` (revoke, not security_invoker: the admin reads with the server key; an invoker view would still answer app users with aggregates over their own rows) | F6 |
| S29-S31 | Drop usage_insert and usage_update (usage_select is kept). Then REVOKE INSERT, UPDATE, DELETE on user_usage from anon and authenticated | F7 (candidate, IN) |
| S32-S33 | Drop referral_invites_select_own, then re-create it `FOR SELECT TO authenticated USING (referrer_user_id = auth.uid())` | F10 (candidate, IN) |
| S34-S35 | `REVOKE EXECUTE ON FUNCTION public.resolve_referral_code(text) FROM anon, authenticated;` (NOT FROM PUBLIC: 037 already did that, and naming PUBLIC trips test_migration_037 :570-611) and `ALTER FUNCTION public.resolve_referral_code(text) SET search_path = public;` (the body names `users` unqualified, 014:100, so '' would break it). The service_role grant from 037 stays | F8 (candidate, IN, gate ruling Q1) |
| S36 | `REVOKE TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;` | F9 / R1-10 |
| S37 | `REVOKE ALL ON public.eval_runs, public.verdict_critiques, public.products FROM anon, authenticated;` | F9 |
| S38 | `DO $assert$`, raising a fixed `'055 assert: ...'` message if any of these fails: the end state; no policy on the ten tables whose text contains `user_id IS NULL`, `share_token` or a bare `true`; no INSERT policy left on comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, users; `has_table_privilege` false for anon and authenticated on each closed privilege; the trigger is present, enabled O and BEFORE INSERT OR UPDATE ROW (the 054 bit tests); the function is invoker with a search_path entry; the views are not selectable by the app roles; the function is not executable by the app roles and IS executable by service_role | |
| S39 | `COMMIT;` | |

### 4.1 users_profile_guard (its OWN function and trigger; 054's are never named)
- **The role test** is byte-equal, after compaction, to 054's ROLE_TEST (tests/test_inc_t1b_users_entitlement_guard.py:81-88 at 77ac43a9) and is the first branch. So every caller class R1 section 4 walked behaves the same: the service key, definer functions called by the server, postgres, the editor and the auth service pass. anon, authenticated and a forged claim are checked.
- **The guarded columns (six), in this order:** email, created_at, attribution_source, last_comparison_at, behavior_profile, demographics_profile.
- **RULING: the whole demographics_profile column, not only its cohort_match key.**
  - The walk finds no user-scoped writer of the column. Its one writer is the service route (database_service.py:916).
  - The raw answers (country, language, governorate) reach the AI system message just as cohort_match does (extraction_service.py:2041-2073).
  - The key-only form leaves those answers open and costs a jsonb path test.
- **UPDATE arm:** `NEW.<col> IS DISTINCT FROM OLD.<col>` for each of the six.
- **INSERT arm** (a second layer: S24 already removes INSERT; the values are the live defaults, columns.txt:434-445 and :453-454):
  - email IS NOT NULL;
  - created_at IS DISTINCT FROM now();
  - attribution_source IS NOT NULL;
  - last_comparison_at IS NOT NULL;
  - behavior_profile IS DISTINCT FROM '{}'::jsonb;
  - demographics_profile IS NOT NULL.
- **Refusal:** `RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'users profile columns are server-managed (INC-SEC-1)';` twice. The words `server-managed` keep 054's log searches (R1-03) counting both rules. There is no `%`, no DETAIL and no row value.
- **Trigger order:** both rules are BEFORE row triggers and fire in name order: users_entitlement_guard (054) first, then users_profile_guard. Neither changes NEW, so the order only decides which fixed message a mixed write shows.

### 4.2 Rollback (`migrations/rollback/055_app_user_access_tightening.sql`, one transaction)
1. Drop exactly 055's trigger and function (`DROP TRIGGER IF EXISTS users_profile_guard ON public.users; DROP FUNCTION IF EXISTS public.users_profile_guard();`).
2. Re-create every dropped or replaced policy BY ITS MEASURED NAME, cmd, roles (`{public}`, or `authenticated` for referral_invites_select_own), USING text and WITH CHECK text, verbatim from policies.txt. rating_cache goes inside the same to_regclass DO guard.
3. Grant back exactly the revoked privileges, on objects named one by one. TRUNCATE, TRIGGER and REFERENCES go back to the 21 measured objects (table_grants.txt:7-48), never with ON ALL TABLES: that would over-grant the 15 tables that have no grant today.
4. `GRANT EXECUTE` resolve_referral_code to anon and authenticated, then `ALTER FUNCTION ... RESET search_path`.

Rules for the file:
- It names nothing of 054.
- The header warns that it RE-OPENS every gap above. Run it only on a ruled rollback, after which the check grid equals the BEFORE grid.
- Code C1-C3 needs no rollback with it: the service key works under either state.

### 4.3 The read-only check (`docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql`)
**Shape:**
- ONE statement (a WITH plus UNION ALL), so the editor's last-result-only display shows the whole grid in one Run. This improves on 054's eight separate runs.
- Text columns: section, object, fact, value.
- It reads pg_catalog and information_schema only. prosrc appears only in a WHERE clause. It never selects FROM a public table.

**Sections; each says BEFORE / AFTER / STOP:**
1. **K1 policies.** Every policy on the ten tables, with its USING and WITH CHECK text (the R1-01 lesson).
   - BEFORE: the 26 rows of policies.txt on these tables.
   - AFTER: comparisons_select (own, authenticated), comparisons_delete, feedback_select, search_logs_select, events_select, users_select, users_update, usage_select, and referral_invites_select_own (referrer only).
   - STOP BEFORE on any policy that is not in policies.txt.
2. **K2 app-role privileges.** has_table_privilege for anon and authenticated, all seven privileges, on the 21 objects plus rating_cache.
3. **K3 service_role privileges.** SELECT, INSERT, UPDATE and DELETE on users, comparisons, comparison_feedback, search_logs, user_events, admin_audit_log and referral_invites; SELECT on the views. STOP BEFORE on any false: the server's writes rest on them.
4. **K4 users triggers.** BEFORE: none, or users_entitlement_guard only. AFTER: users_profile_guard, plus 054's if it is applied. STOP on any other trigger.
5. **K5 guard function.** secdef false, and search_path present.
6. **K6 the six column defaults.** STOP unless: email none, created_at now(), attribution_source none, last_comparison_at none, behavior_profile '{}'::jsonb, demographics_profile none.
7. **K7 views.** Their options, and the anon and authenticated SELECT.
8. **K8 resolve_referral_code.** secdef, config, and EXECUTE for anon, authenticated and service_role.
9. **K9 table facts.** Row security on for the ten tables; whether rating_cache is present.
10. **K10 054's section-8 rule.** SECURITY DEFINER functions whose body names users, with EXECUTE for anon and authenticated. STOP on true.

### 4.4 Live proofs (the R1-02 lesson)
**Where they live:** notes root `INC-SEC-1_PROOFS_055.sql`, not the public repo. Each proof:
- is ONE self-contained `DO` block run in one Run;
- switches role with `SET LOCAL ROLE` inside the block and sets claims with `set_config(..., true)`;
- makes each write inside an inner BEGIN / EXCEPTION block;
- ALWAYS ends with `RAISE EXCEPTION` carrying a fixed verdict ('Pn PASS ...' or 'Pn FAIL <object name>'). So nothing ever commits, and the one visible line is the verdict.

The proofs print no count, id or value.

**The proofs:**
- **P0** The editor can switch to anon and to authenticated (pg_has_role MEMBER); otherwise P0 STOP.
- **P1** As anon: no comparisons row is visible.
- **P2** As authenticated with a block-generated sub: no comparisons row is visible.
- **P3** As anon and as authenticated: rating_cache, the three views and resolve_referral_code are each refused with 42501.
- **P4** As anon and as authenticated: an INSERT into admin_audit_log, comparison_feedback, search_logs, user_events, comparisons (own sub) and user_usage is refused each time (12 of 12).
- **P5** As authenticated: an INSERT into users is refused.
- **P6, needing the throwaway auth user of the 054 note:**
  - as that user, a control UPDATE of expo_push_token touches 1 row (else STOP);
  - each of the six columns changed alone is refused with the 055 message.
- **P7** As service_role with service claims: the six columns and a feedback, search, event and audit insert each touch 1 row.
- **P8** As the throwaway user: a comparison row made inside the block as postgres is visible and deletable by its owner.

## 5 SERVER CODE CHANGES (unflagged: C1 and C2 keep every product row the same; C2b and C3 fix defects, see Q2 and Q3)
- **C1** `app/services/database_service.py` create_share_token (:596-675):
  - Drop the `access_token` parameter and the user branch at :611. The client is always `get_admin_supabase_client()`.
  - The ownership read at :617 passes no token.
  - The PermissionError, ShareTokenError and idempotent-token behaviour are unchanged.
  - Keep building the client where it is built today (tests/test_share_routes.py:197-235 rely on today's order).
  - Caller app/api/share_routes.py:29 is unchanged; it already passes two arguments.
- **C2** `app/services/feedback_service.py` save_feedback (:147-228): the client is `get_supabase_client()` for both arms. The `access_token` keyword stays in the signature, because the route kwargs are pinned at tests/test_s81_sf1_surfaces_be.py:79-80 and :470-479. It no longer picks the client. The docstring at :169-174 is re-worded to say the database refuses every app-role write (055).
- **C2b** (the brief's "feedback must name the caller's own comparison"; once C2 moves the write to the server key, the database no longer checks it):
  - When `user_id` and `comparison_id` are both set, one service read of `comparisons.user_id` for that id runs before the insert.
  - If the row is missing, owned by someone else, or the read fails, the feedback row is still written but WITHOUT comparison_id. The server logs one WARNING with constants only: `[FEEDBACK] FEEDBACK_COMPARISON_NOT_OWNED` or `FEEDBACK_OWNERSHIP_UNREAD`.
  - The anonymous arm is unchanged, because anonymous compares save no row (persist only when user_id is set: text_routes.py:903, image_routes.py:755 and url_routes.py:372; the other text sites read as LIKELY the same). Stated limit L6.
- **C3** `app/services/referral_service.py` `_load_invitee` (:789-801): the select at :793 adds `device_fingerprint_hash`. The fallback dict at :686-689 gains `"device_fingerprint_hash": None`. The same-device control then fires as designed (abuse_detection_service.py:248-252). The email half of R1-05 is closed by the S25 guard: the server never updates users.email after the insert, and update_user_email at auth_service.py:887-897 changes only the auth record.

Not changed: the mobile app (no OTA), 054, any ENABLE_* flag, Railway variables.

## 6 FLAG AND ORDER WALK
| state | signed-in feedback | share link and page | users writes | logs, audit, events | verdict |
|---|---|---|---|---|---|
| today (5cd93c6a, 054 and 055 off) | written through the user client | service | 054 and 055 columns open to their owner | open to anyone | the gaps |
| deploy C1-C3, 055 not applied | service; C2b may drop a foreign id | service (C1 is a no-op in production) | unchanged | unchanged | SAFE; same-device invites now flagged (C3) |
| **055 applied BEFORE the deploy** | **refused, quietly**: a 42501 at the insert; the route still answers "Feedback received"; the warning logs only the type and code (feedback_service.py:225-227) | service, unaffected | guarded | closed | **FORBIDDEN. The deploy carrying C2 must be live before 055 applies** |
| deploy, then 055; 054 off | service | service | the six closed; 054's eleven still open | closed | SAFE (054's hole remains until 054) |
| deploy, 054, 055 | service | service | seventeen columns closed | closed | TARGET |
| 055 rolled back, deploy live | service | service | the six open again | open again | works, holes re-open |
| 054 rolled back, 055 on | unaffected | unaffected | the eleven open again, the six closed | closed | independent |

Flags walked (055 reads none; none changes): ENABLE_FEEDBACK_V2 (both arms, one table, one client after C2); ENABLE_HOME_SAVINGS_AGGREGATE (stays off by the HARD RULE; 055 leaves its function alone; the fallback reads own rows); ENABLE_SUPABASE_CLIENT_REUSE (client building only); ENABLE_COHORT_PERSONALIZATION (service read, database_service.py:928); ENABLE_PAID_ROUTE_METERING and ENABLE_SEARCH_LOG_TRUTH (service writers); ENABLE_DEVICE_DAILY_QUOTA (no 055 table).

## 7 RULINGS
- **R-A, the users guard is a second TRIGGER, not the R1-08 column grant.** Why:
  1. It is the pattern A-1 measured on the throwaway cluster (30 cases).
  2. It refuses with a fixed `server-managed` message, which the R1-03 log searches already count. A column-grant refusal is a generic permission error.
  3. It also checks writes made through a privileged function on a user's behalf. A column grant is checked against the function owner, so it would let such writes pass.
  4. It touches no column a user-scoped writer writes. A grant change to the users table is the bigger blast radius for a first window.

  The column grant (UPDATE on expo_push_token and preferences only) is recommended as a FOLLOW unit after one quiet week. It closes the columns that stay open (L4) and any future column by default.
- **R-B, the window takes 054 FIRST, then 055** (the same window or later), and always after the C1-C3 deploy.
  - The SQL of 055 is order-independent: it names no 054 object, its guard requires no 054 object, and its assert checks only its own trigger.
  - GREEN and A-1 prove that on the cluster in both orders, and each rollback with the other present.
  - But 054's own check has a STOP on "any other user trigger on public.users" (APPLY_054_CHECK.sql:11-12). It would fire on users_profile_guard if 055 went first.
  - If the relay ever must run 055 first, the apply note names users_profile_guard as the one expected exception to that STOP. That is a note line; 054's files are not changed.
- **R-C, feedback goes to the server key (Option A), and its app-role INSERT goes entirely.** Option B kept the user client with a WITH CHECK requiring the caller's own comparison (an EXISTS over comparisons). It needed no code, but a signed-in key holder could still write feedback directly, bypassing the route's enum and size checks and its 30-a-minute limit. That is exactly the judge and learning input R2 F4 names. Option A closes the table to app users. C2b restores the ownership rule at the server.
- **R-D, the proofs live in the notes, not in the repo:** the repo is public, and the proofs are verification steps for the window.

## 8 TEST METHOD (measured from PR #415)
- **House style, ESTABLISHED:** the repo test for a migration is a STATIC file. tests/test_inc_t1b_users_entitlement_guard.py (77ac43a9), its header at :8-10: "Nothing here touches a database: every row is a text or AST scan of repo files".
  - The 30 rows are M, C, D, K, L and W rows: SQL text pins, a sqlfluff lint with the repo .sqlfluff, and AST writer walks over app/ and scripts/.
  - CI runs only these.
- **The throwaway PostgreSQL, ESTABLISHED** (notes lane-s97/t1b/adv_a1/INC_T1B_ADV_A1_REPORT.md:9, initdb.out, setup.sql, attacks.sql): adversary A-1 executed the committed blobs on a local PostgreSQL 18.1 cluster.
  - The binaries were already installed at `C:/Program Files/PostgreSQL/18` (`postgres --version` prints 18.1). Nothing was installed and docker was not used.
  - initdb went into a notes folder, the server listened on a loopback high port with trust auth, and it was stopped afterwards.
  - setup.sql built Supabase-shaped roles (anon, authenticated, service_role with BYPASSRLS, authenticator), the Supabase `auth.uid()` body, the repo defaults, the 010 policies and full grants. attacks.sql ran BEGIN / SET LOCAL ROLE / ROLLBACK cases and DO blocks.
  - The check was run before, after and after-rollback, and the grids compared.
- **For 055:**
  - RED and GREEN rows in `tests/test_inc_sec1_app_user_access.py` (static).
  - GREEN, then A-1, run the committed blobs on a fresh throwaway cluster. setup.sql is extended with the ten tables, the 26 measured policies by name and text, the 21-object grants, the three views (013:23-56), resolve_referral_code (014:97-102 plus the 037 grants) and the 048 delete_user_cascade.
  - That run covers: P0-P8 adapted to synthetic ids; 054 then 055, and 055 then 054; each rollback; a check grid after rollback byte-equal to before; a re-run of 055 (idempotence).
- **Limit:** the cluster is 18.1, production is 15 (027:40-43). Every statement used exists in 15: CREATE OR REPLACE TRIGGER needs 14+, and REVOKE ... ON ALL TABLES IN SCHEMA, ALTER FUNCTION ... SET and DROP POLICY IF EXISTS are all older. The out-of-repo rating_cache sits behind a to_regclass guard, so DROP POLICY IF EXISTS on a missing table is never reached.

## 9 RED ROWS (tests/test_inc_sec1_app_user_access.py; every row fails at base on an AssertionError, never an import error; PIN rows are named)
**M-rows (the migration):**
- **M01** 055 up, down and check each exist once; 039, 051 and 053 stay unused.
- **M02** 055 is the highest number and 054 sits beside it.
- **M03** ASCII only; no 8-digit run; no id-shaped literal.
- **M04** one transaction; S01 is the first statement after BEGIN; no session-level SET.
- **M05** the header is SECURITY INVOKER with `SET search_path = ''`; no SECURITY DEFINER anywhere in the file.
- **M06** the trigger statement as in S26; exactly one CREATE TRIGGER.
- **M07** the role test is equal to 054's ROLE_TEST and comes first; RETURN NEW appears 3 times; no auth.* call in the body.
- **M08** the UPDATE arm is exactly the six columns in order. NEW and OLD name only them, with no overlap with 054's eleven.
- **M09** the INSERT arm uses the 4.1 values.
- **M10** the fixed message appears twice with 42501. It contains `server-managed`, differs from 054's message, and has no `%` and no DETAIL.
- **M11** the guard and assert blocks are present and ordered guard < function < assert.
- **M12** the up file never names users_entitlement_guard and never alters or drops 054's objects.

**P-rows (policies and privileges):**
- **P01** S03-S07: comparisons_select is re-created own-only; insert and update are dropped; delete is untouched; INSERT and UPDATE are revoked.
- **P02** no created policy contains `IS NULL`, `share_token` or `USING (true)`.
- **P03** every DROP POLICY names a policy in the measured census (policies.txt, a constant in the test); no policy loop.
- **P04** the revoke map per table equals section 4.
- **P05** the rating_cache statements are inside a to_regclass-guarded DO and run through EXECUTE.
- **P06** the users drops and REVOKE INSERT, DELETE are present; users_select and users_update are not dropped.
- **P07** the views revoke is present.
- **P08** the F7, F10, F8 and F9 statements: the F8 revoke names anon and authenticated, never PUBLIC; search_path = public.
- **P09** the assert block names each end-state check.
- **P10** every migration numbered 055 or later that CREATEs a table also ENABLEs ROW LEVEL SECURITY on it (F9, a forward pin).

**D01 (the rollback):**
- It drops exactly 055's function and trigger.
- It re-creates every dropped or replaced policy with the measured text verbatim (the census constant).
- It grants back exactly what was revoked, on named objects only (no ON ALL TABLES).
- It never names 054; it is one transaction; its header warns that the gaps re-open.

**K-rows (the check):**
- **K01** one SELECT or WITH statement; no write word, SET, DO, set_config or pg_sleep.
- **K02** sources are pg_catalog and information_schema only; prosrc only in WHERE.
- **K03** the ten section names and the six-column list.

**L01** sqlfluff is clean on the up, down and check files.

**W-rows (the writer walk; AST over app/ and scripts/):**
- **W01** the user-scoped WRITE set is exactly: update_push_token, update_reengagement_subs, update_preference_toggles (auth_routes.py) and delete_comparison (database_service.py). It is RED at base because create_share_token and save_feedback are in it today.
- **W02 PIN** no user-scoped function inserts into or updates comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, rating_cache or user_usage, or inserts into users. RED at base through the same two.
- **W03 PIN** the user-scoped users writers touch none of the six. Green at base.
- **W04 PIN** every writer of the six is service: save_user_demographics, save_user_attribution, _update_behavior_profile, register_user, sign_in_with_social, create_user. Green.
- **W05 PIN** SmartCompareApp/package.json has no supabase dependency; src has no createClient and no rest/v1. Green.
- **W06 PIN** share_routes.py calls create_share_token with two arguments; get_shared_comparison builds the admin client. Green.

**C-rows (the code):**
- **C01** create_share_token has no access_token parameter and no get_user_supabase_client.
- **C02** with a token, save_feedback calls the service client's `table("comparison_feedback")` and never builds a user client.
- **C03** C2b, four cases: owned keeps the id; foreign drops the id and logs the fixed word; an unreadable read drops the id and logs its word; anonymous is unchanged.
- **C04** `_load_invitee` selects device_fingerprint_hash; try_trigger_loop2 with an invitee hash equal to the referrer's flags SAME_DEVICE and grants nothing.

**X01 PIN** 054's three files are byte-equal to their 77ac43a9 sha256 values (the owner summary's hashes): 054 is not changed.

**Mutants (GREEN runs them on copies; all must be killed), each with its killing row:** shared branch kept (P01); `OR user_id IS NULL` kept (P02); misspelled policy name (P03); feedback REVOKE removed (P04); rating_cache outside the DO (P05); SECURITY DEFINER (M05); role test without service_role (M07); email out of the UPDATE arm (M08); behavior_profile vs NULL (M09); 054's message (M10); rollback ON ALL TABLES (D01); rollback missing a policy (D01); check reads public.users (K02); create_share_token user branch (C01, W01); save_feedback user branch (C02, W01); select without the hash (C04); up drops users_entitlement_guard (M12); F8 names PUBLIC (P08). 18 in all.

## 10 EXISTING PINS THIS UNIT MOVES (each a named ruling, never a silent edit)
1. tests/test_m13_29_feedback_uuid.py:107-136, `test_save_feedback_uses_user_client_when_authenticated`, is INVERTED by R-C (the authenticated write uses the service client). Its module docstring (:7) is re-worded.
2. tests/test_inc_t1b_users_entitlement_guard.py:137-142 (`test_m02_next_free_number`, `numbers[-1] == 54`) fails once 055 exists.
   - Whichever PR merges second amends that TEST row to "054 exists, 053 absent". This is not a change to 054's SQL, which stays pinned by X01.
   - If 055 is cut before #415 merges, the 055 branch is based on the 054 branch.
3. tests/test_migration_037_security_definer_grants.py:353-357 and :570-579 call the anon grant on resolve_referral_code a "product requirement".
   - The walk shows no anonymous caller: the app ships no database client, and referral_routes goes through the server (037:101-112 says so itself).
   - The rows still pass mechanically: S34 does not name PUBLIC. Their comments are re-worded IF F8 is ruled IN (Q1).
4. Unchanged and must stay green: tests/test_share_routes.py:197-235 (C1 keeps two-argument calls); tests/test_s81_sf1_surfaces_be.py:79-80 and :470-479 (C2 keeps the kwargs); tests/test_referral_service.py:777-800 (no select string is pinned); tests/test_migration_041_* (they pin 041's own file only).
5. The comm set: the unit's file, every file above, test_migration_037, test_migration_index_predicate_immutability, test_security_regression, the referral and feedback suites, the source-scanning pins and the fourteen client jest fences (app/ literals move).

## 11 FILES
- migrations/055_app_user_access_tightening.sql (working name)
- migrations/rollback/055_app_user_access_tightening.sql
- docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql
- tests/test_inc_sec1_app_user_access.py
- app/services/database_service.py (C1), app/services/feedback_service.py (C2, C2b), app/services/referral_service.py (C3)
- the tests moved by section 10
- notes root: INC-SEC-1_OWNER_SUMMARY.md, INC-SEC-1_APPLY_NOTE.md, INC-SEC-1_PROOFS_055.sql (GREEN writes them; outlines in section 14)

## 12 STATED LIMITS
- **L1** Proven on a local 18.1 cluster, not on production 15. The live proof is the window's P0-P8.
- **L2** An unreadable request.jwt.claims raises 22P02 without the fixed message (the same as 054, R1-11).
- **L3** A trigger guards the columns it names: a column added later is open to its owner until the R1-08 FOLLOW.
- **L4** Still writable by the row's owner: display_name (shown to the referrer), auth_provider, updated_at (vw_cohort_match_rate groups on it, 013:24), preferences_completed and the two demographics_dismissed fields. All go to the R1-08 FOLLOW.
- **L5** Default privileges for new tables are unchanged (F9, the remaining FOLLOW). P10 pins row security for new migrations instead.
- **L6** Anonymous feedback naming a comparison id is not owner-checked (no owner exists). After F1 and F10, no app-role read hands out another user's comparison id.
- **L7** rating_cache and bahrain_approved_drugs stay outside migration control (no CREATE is folded in). F16 (the drug registry read) is untouched.
- **L8** The catalog is the 2026-11-17 snapshot. The BEFORE grid is the live truth, and a STOP sends it back.
- **L9** Not in this unit: R1-04 (the fail-open entitlement read) and R2 F5's second half (escaping profile fields before they reach a prompt).
- **L10** That the editor can switch roles inside a DO block was measured on the cluster only. P0 checks it live first.

## 13 OPEN QUESTIONS (for the spec review)
- **Q1** F8 overturns 037's deliberate retention of the anon grant (037:101-112). Recommended IN on the walk's evidence; otherwise FOLLOW, and S34-S35 move out.
- **Q2** C2b on a foreign or unread id: drop the id and keep the row (recommended: no feedback is lost), or refuse the row.
- **Q3** C3 changes what a user sees: invites made from the referrer's own device stop earning (the designed control). Should the owner be told in the summary? Recommended yes; no flag.
- **Q4** R-A's whole demographics_profile column, against the brief's cohort_match key only.
- **Q5** Does service_role really hold SELECT on the three views live? K3 shows it; table_grants.txt lists only the app roles.
- **Q6** A later unit could revoke everything from anon on the user tables (no server path uses the bare anon role on a table). Not in 055.

## 14 OUTLINES (GREEN writes the files; plain words, like INC-T1B_OWNER_SUMMARY.md)
**INC-SEC-1_OWNER_SUMMARY.md:**
1. **Title and status:** written and tested, NOT applied; the branch commit.
2. **What is permitted today and stops,** one line each: reading other people's shared results; the old ratings table; adding audit, feedback, search and event rows (signed out, or directly while signed in); writing comparison rows; changing six more account fields (e-mail among them); reading the company metrics views; the referral lookup.
3. **What stays possible:** everything the app does. The app never talks to the database; our server does it with its own key.
4. **The server change that ships first,** and why the order matters: feedback from a signed-in user would otherwise be lost quietly. Also the referral same-device check that now works.
5. **The exact SQL,** with the sha256 of the up, down and check files.
6. **The undo,** and that it re-opens everything.
7. **What could go wrong and how it would show:** a refusal is quiet on the phone, so the logs are the proof. Search for `server-managed` and `permission denied`.
8. **Tested on** a throwaway local PostgreSQL 18.1 (the case counts); not yet live.
9. **Known limits:** L3, L4, L6.
10. **Order:** 054 first, then the deploy, then 055.

**INC-SEC-1_APPLY_NOTE.md:**
1. **Order:**
   - (a) 054 applied and verified;
   - (b) the deploy carrying C1-C3 is live (the relay confirms the deployed commit);
   - (c) the 055 window.
2. **File hashes** of the merged blobs.
3. **BEFORE:** the check, ONE Run, one grid, with the STOP rules of 4.3.
4. **APPLY:** the whole file in one Run (lock_timeout is inside it).
5. **AFTER:** the grid again; compare it with 4.3's AFTER.
6. **Proofs:** P0-P8, each one Run, verdict lines only in the ledger. The throwaway auth user is created and deleted as in the 054 note, and is named in the owner's yes.
7. **The real-path proof, from the owner's phone:**
   - one compare, which appears in history;
   - one share link, which opens;
   - one signed-in feedback;
   - one push-token registration (HTTP 200).
8. **Logs over the window and the next 24 hours:**
   - Railway: the plain words `server-managed` and `permission denied` (no brackets in the filter); expect 0.
   - Supabase Postgres logs: the same words. A hit from service_role or postgres means roll back. A hit from anon or authenticated is the rule working.
9. **Rollback:** the file, then the grid, which must equal the BEFORE grid.
10. **Stated limits:** L1, L2, L8, L10.

## 15 CANDIDATES (sized; the gate rules)
| id | size | verdict | why |
|---|---|---|---|
| F7 user_usage | 3 statements, 0 code | IN | no reference in app/ or scripts/ |
| F8 resolve_referral_code | 2 statements, 2 test comments | IN (gate ruling Q1) | only caller is service; the app has no database client |
| F9 TRUNCATE / TRIGGER / REFERENCES, and full revoke on eval_runs, verdict_critiques, products | 2 statements plus P10 | IN | PostgREST never issues them; all three tables are service-only |
| F9 default privileges for new tables | platform-owned (Supabase default privileges belong to its own admin role) | FOLLOW | needs a live read of pg_default_acl first |
| F10 referral_invites read | 2 statements | IN | every reader is service |
| R1-08 column grant on users | 2 statements plus the check, and the blast radius of a grant change | FOLLOW (R-A) | after one quiet week of 054 and 055 |

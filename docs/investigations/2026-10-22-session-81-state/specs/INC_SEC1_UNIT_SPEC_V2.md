# INC-SEC-1 DATABASE-ACCESS: unit spec V2 (S96 lane, 2026-11-17; class FOCUS: spec, spec review, RED, GREEN, two adversaries)

Written, not applied. Nothing here touches a database. Repo PUBLIC: every gap is described by what is permitted and what must change; synthetic UUIDs only. ESTABLISHED = read in code or the catalog; LIKELY = best reading. The walk stays in `sec1/INC_SEC1_WALK.md` (updated with the afde168f re-scan).

## CHANGES FROM THE DRAFT (each ruling of RULINGS_INC_SEC1.md, and where it lands)
- **Base moved:** section 1 (main afde168f; worktree sc-s96-sec1, branch fix/inc-sec1-app-user-access; node_modules junction, `cmd /c rmdir` first).
- **R-1:** X01 (9).
- **R-2:** section 10 items 2-5.
- **R-3:** S38, K1, the cluster setup (8).
- **R-4:** apply note step 8.
- **R-5:** the FORBIDDEN row (6); the apply note and the owner summary (14).
- **R-6:** C2b (5); C03 (9).
- **R-7:** C04 (9).
- **R-8:** the rollback (4.2); K1.
- **R-9:** K2 and K8.
- **R-10:** P4 and P8.
- **R-11 a-g:** S08-S23 and the rollback; M05; P10; L4; C2; K3; K11.
- **R-12:** L11.
- **R-13:** C3 dark (5); its flag rows (6); C04; the CLAUDE.md row (11); the owner summary (14).
- **R-14:** S34-S35; section 10 item 3.
- **R-15:** 4.1.
- **R-16:** K3.
- **R-17:** section 15.
- **R-18:** sections 6 and 14.
- **R-19:** section 8 and K11.

Found by this amendment's re-scan (no ruling covers them; each is named, see 13 Q7-Q9):
- **N-1** tests/test_s81_sf1_gate_rows.py:81-85 (test_gr1) asserts save_feedback holds exactly ONE except handler. So C2b's ownership read lives in its own helper (5 C2b), never inside save_feedback.
- **N-2** Three more record-asserting fixtures call save_feedback with a comparison_id on a bare MagicMock client: tests/test_s80_b1_feedback.py:149-157 (test_b1_f5), tests/test_s81_sf1_surfaces_be.py:482-499 (test_p12) and :529-542 (test_r14). Under R-6 they read as "owned by someone" and lose the id. They move like test_feedback.py (R-2): each fixture configures the ownership read as "no row" (data = []), and every assertion stays.
- **N-3** The walk header said its scan ran at 5cd93c6a. The five structured_comparison_service.py lines (:6068, :6092-6094, :6103) are the 6473769e / afde168f numbers; at 5cd93c6a they were 22 lower (:6046, :6070-6072, :6081). Every cited line is right at afde168f.
- **A-1 (my amendment, the gate may veto)** M02 for 055 asserts "055 and 054 exist, 053 absent", never "055 is the highest". "Highest" is the trap that moves test_m02 today.

## 0 WHAT
- **Migration 055** (`migrations/055_app_user_access_tightening.sql`), with:
  - its rollback;
  - a read-only check;
  - live proofs, each a single DO block.
- **Four server changes:**
  - C1: the share-token write.
  - C2: the feedback write.
  - C2b: feedback must name the caller's own comparison.
  - C3: the same-device referral check, DARK behind a new switch.
- **054 is not changed.** Its SQL stays byte-equal to the merged blobs (X01). Only its test row test_m02 is amended (R-2, 10 item 2).

## 1 BASE STATE
- **main = afde168f21703baba4bc4857eedf1042e5432196.** It holds #416 (6473769e) and #415 (054). 5cd93c6a..afde168f changes in app/ only image_relevance.py, image_service.py, woocommerce_service.py and structured_comparison_service.py.
- **The re-scan at afde168f, ESTABLISHED:**
  - The walk AST scan (`sec1/walk_scan_v2.py`) prints 110 rows, byte-equal to walk_raw.txt.
  - The reviewer's scan (`sec1/review_scan_v2.py`) prints 209 calls, byte-equal to review_scan_main.txt.
  - The hand-read lines are unchanged: their files are not in the diff.
  - So **no line of the walk moves.** The only correction is N-3.
- **The merged 054 blobs at afde168f** (sha256 over the LF blob bytes; the blobs hold no CR):
  - up migrations/054_users_entitlement_guard.sql: base64 `dzEHMoM39ECzRbswCy/grDuWCAvspNfDlPGht/vBbSo=`, 7019 bytes;
  - down migrations/rollback/054_users_entitlement_guard.sql: base64 `TkmljMAY+mTld2UlAUpcgL5+qMK3+OyYDO/ON4S91Vk=`;
  - check docs/investigations/2026-11-17-session-97-state/APPLY_054_CHECK.sql: base64 `UWhFixGKdV+L7StjzH1bcH4Tdl4X4RjGhylpmY6ecHQ=`.

  They equal the 41ce0c5f values (F-01). Re-read facts that bind 055:
  - The role test (test file :81-88) is unchanged.
  - The message is `users entitlement columns are server-managed (INC-T1b)`.
  - The trigger is users_entitlement_guard, BEFORE INSERT OR UPDATE FOR EACH ROW.
  - 054 has no lock_timeout.
  - The 054 check section 1 STOPs on any other user trigger on public.users (:11). Section 4 STOPs on DELETE / ALL policies except "Service role full access". A missing row is not a STOP.
- **Catalog:** notes `security-review-2026-11-17/catalog/`, read 2026-11-17. Its findings are R2 F1-F16, plus R1-02, R1-05, R1-07, R1-08, R1-09 and R1-10.
- **Draft corrections stand (ESTABLISHED):**
  - (a) create_share_token's user branch is dead: share_routes.py:29 passes no token, so database_service.py:611 takes the service branch.
  - (b) admin_audit_log and user_usage are created in the repo (011:34, 011:8). Only rating_cache and bahrain_approved_drugs have no CREATE.
  - (c) behavior_profile has readers: home_routes.py:763, profile_routes.py:494 and structured_comparison_service.py:6068.

## 2 MEASURED GAPS (each is what is permitted today)
Unchanged from the draft (catalog lines there):
- **F1** shared rows readable by anyone.
- **F2** rating_cache fully open.
- **F3** signed-out log rows.
- **F4** signed-in comparison writes, foreign feedback ids, free-form log rows.
- **F5 / R1-05** six more owner-writable users columns.
- **F11 / R1-07** self-created users rows.
- **F6** the cohort views.
- **F12** duplicate policies.
- **F7** the user_usage writes.
- **F8** resolve_referral_code open to all.
- **F9** TRUNCATE / TRIGGER / REFERENCES, and three tables closed only by a missing policy.
- **F10** the invitee read.

**The ten tables** (R-3) hold the 26 policies of policies.txt rows :3, :5-12, :15-16, :18, :20-24 and :26-34:
- admin_audit_log 1, comparison_feedback 4, comparisons 4, products 1, rating_cache 1;
- referral_invites 1, search_logs 2, user_events 3, user_usage 3, users 6.

**The 21 granted objects**, each holding all seven privileges for anon and authenticated:
- admin_audit_log, bahrain_approved_drugs, comparison_feedback, comparisons, deep_review_credits, eval_runs, pain_workflow_events;
- products, rating_cache, re_engagement_events, referral_invites, referral_redemptions, search_logs, user_events;
- user_preference_history, user_usage, users, verdict_critiques and the three vw_cohort_* views.

rating_cache is one of the 21; the draft's "21 plus rating_cache" is corrected.

**R1-05's code defect (ESTABLISHED):**
- `_load_invitee` selects `id, email, subscription_tier, display_name` (referral_service.py:793).
- So `evaluate_invite` reads `invitee.get("device_fingerprint_hash")` as None (abuse_detection_service.py:249).
- is_same_device returns False (:124), and the same-device control never fires.

## 3 THE WALK, VERDICT PER REMOVAL (full table: INC_SEC1_WALK.md A-G; unchanged at afde168f)
- **F1, the shared-row read:** 7 user-scoped reads (database_service.py:517, :550, :718; home_routes.py:270, :804; profile_routes.py:201, :328), each own-filtered or re-checked (history_routes.py:150-154). SAFE: the share page reads with the server key (:684).
- **F4, comparisons INSERT / UPDATE:** 1, database_service.py:640, dead in production. C1.
- **F3 / F4, comparison_feedback INSERT:** 1, feedback_service.py:220. C2 plus C2b. **Deploy BEFORE 055.**
- **Zero user-scoped references, all SAFE:**
  - search_logs / user_events / admin_audit_log INSERT;
  - rating_cache (backend/ only, not deployed);
  - users INSERT and the duplicate policies;
  - the views;
  - user_usage;
  - the referral_invites invitee read;
  - resolve_referral_code (only referral_service.py:429, service; R-14);
  - F9.
- **F5, the six columns:** the 3 user-scoped users writers write only expo_push_token (auth_routes.py:1466) or preferences (:1548, :1622; notifications_enabled is inside preferences). Every writer of the six is service (database_service.py:916, :954; structured_comparison_service.py:6103; the inserts; 048:259-279). SAFE.

## 4 THE 055 CONTRACT (one transaction; idempotent)
- Every DROP is IF EXISTS. Every CREATE follows its own DROP or is OR REPLACE. REVOKE and ALTER FUNCTION SET re-run as no-ops.
- **Header:**
  - the WHY per finding (permitted / must change, no misuse text);
  - "MERGING THIS CHANGES NOTHING IN PRODUCTION";
  - the order of R-18;
  - the FORBIDDEN rule of R-5;
  - the rollback and check paths.

| # | statement | closes |
|---|---|---|
| S00 | `BEGIN;` | |
| S01 | `SET LOCAL lock_timeout = '5s';` | |
| S02 | `DO $guard$`: a fixed `'055 guard: ...'` exception if a repo object is missing: users and the six columns, comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, user_usage, referral_invites, products, eval_runs, verdict_critiques, the three views, `public.resolve_referral_code(text)`. rating_cache is not required (S08) | |
| S03-S04 | `DROP POLICY IF EXISTS comparisons_select ON public.comparisons;` then `CREATE POLICY comparisons_select ON public.comparisons AS PERMISSIVE FOR SELECT TO authenticated USING (auth.uid() = user_id);` | F1 |
| S05-S06 | drop comparisons_insert and comparisons_update (comparisons_delete kept) | F4 |
| S07 | `REVOKE INSERT, UPDATE ON public.comparisons FROM anon, authenticated;` | F4 |
| S08 | `DO $rc$`: if `to_regclass('public.rating_cache')` is set, EXECUTE the drop of "Service role has full access to rating_cache" and `REVOKE ALL ON public.rating_cache FROM anon, authenticated`; else a NOTICE | F2 |
| S09-S10 | drop audit_insert; `REVOKE ALL ON public.admin_audit_log FROM anon, authenticated;` | F3 |
| S11-S14 | drop feedback_insert, "Users can insert own feedback", "Users can read own feedback" (feedback_select kept); REVOKE INSERT, UPDATE, DELETE on comparison_feedback | F3, F4, F12 |
| S15-S16 | drop search_logs_insert (search_logs_select kept); REVOKE INSERT, UPDATE, DELETE | F3, F4 |
| S17-S19 | drop events_insert and "Users can insert own events" (events_select kept); REVOKE INSERT, UPDATE, DELETE | F3, F4, F12 |
| S20-S23 | drop users_insert, "Users can read own data", "Users can update own data", "Service role full access" (users_select and users_update kept; service_role passes by BYPASSRLS, checked in K3) | F11, F12 |
| S24 | `REVOKE INSERT, DELETE ON public.users FROM anon, authenticated;` | F11 |
| S25 | `CREATE OR REPLACE FUNCTION public.users_profile_guard() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $function$ ... $function$;` (4.1) | F5, R1-05 |
| S26 | `CREATE OR REPLACE TRIGGER users_profile_guard BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.users_profile_guard();` | F5 |
| S27 | `COMMENT ON FUNCTION public.users_profile_guard() IS 'INC-SEC-1: ...';` | |
| S28 | `REVOKE ALL ON public.vw_cohort_match_rate, public.vw_cohort_persona_distribution, public.vw_cohort_feedback_lift FROM anon, authenticated;` (a revoke, not security_invoker) | F6 |
| S29-S31 | drop usage_insert, usage_update (usage_select kept); REVOKE INSERT, UPDATE, DELETE on user_usage | F7 |
| S32-S33 | drop referral_invites_select_own; re-create it `AS PERMISSIVE FOR SELECT TO authenticated USING (referrer_user_id = auth.uid())` | F10 |
| S34-S35 | `REVOKE EXECUTE ON FUNCTION public.resolve_referral_code(text) FROM anon, authenticated;` (never names PUBLIC; the service_role grant from 037 stays) and `ALTER FUNCTION public.resolve_referral_code(text) SET search_path = public;` | F8 (R-14) |
| S36 | `REVOKE TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;` (K2 STOPs BEFORE if the app-role set is not the measured 21) | F9 / R1-10 |
| S37 | `REVOKE ALL ON public.eval_runs, public.verdict_critiques, public.products FROM anon, authenticated;` | F9 |
| S38 | `DO $assert$`: a fixed `'055 assert: ...'` exception if any end-state check fails (below) | |
| S39 | `COMMIT;` | |

**Quoting (R-11a).** Every quoted policy name carries `-- noqa: RF05`, as at 041:75. That covers S08's EXECUTE string, S11-S13, S17-S18, S20-S23 and the rollback CREATEs.

**S38, the end-state checks (R-3):**
1. No policy on the ten tables whose roles overlap `{public, anon, authenticated}` has USING or WITH CHECK text that holds `user_id IS NULL` or `share_token`, or that equals `true`. Policies whose roles are only service_role are out of scope, so products_service_role_all passes.
2. No INSERT policy is left on comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, users or user_usage.
3. has_table_privilege is false for anon and authenticated on each closed privilege.
4. users_profile_guard is present, enabled O, BEFORE INSERT OR UPDATE FOR EACH ROW: `(tgtype & 23) = 23` and `(tgtype & 8) = 0`, as in 054.
5. The function is invoker, with a search_path entry.
6. The views are not selectable by the app roles.
7. resolve_referral_code is not executable by anon or authenticated, and IS executable by service_role.

### 4.1 users_profile_guard (its OWN function and trigger; 054's are never named)
- **The role test** is byte-equal, after compaction, to 054's ROLE_TEST (test file :81-88 at afde168f). It is the first branch.
- **Guarded columns (six, in this order; R-15, the WHOLE demographics_profile):**
  - email, created_at, attribution_source, last_comparison_at, behavior_profile, demographics_profile.
  - The walk finds no user-scoped writer of any of them.
  - demographics_profile's raw answers also reach the AI system message (extraction_service.py:2041-2073).
- **UPDATE arm:** `NEW.<col> IS DISTINCT FROM OLD.<col>` for each of the six.
- **INSERT arm** (a second layer behind S24; the values are the live defaults, columns.txt:434-445, :453-454):
  - email IS NOT NULL;
  - created_at IS DISTINCT FROM now();
  - attribution_source IS NOT NULL;
  - last_comparison_at IS NOT NULL;
  - behavior_profile IS DISTINCT FROM '{}'::jsonb;
  - demographics_profile IS NOT NULL.
- **Refusal:** `RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'users profile columns are server-managed (INC-SEC-1)';`, twice. There is no `%`, no DETAIL and no row value.
- **Trigger order:** BEFORE row triggers fire in name order, so users_entitlement_guard runs before users_profile_guard. Neither changes NEW.

### 4.2 Rollback (`migrations/rollback/055_app_user_access_tightening.sql`, one transaction, idempotent; R-8)
1. `DROP TRIGGER IF EXISTS users_profile_guard ON public.users; DROP FUNCTION IF EXISTS public.users_profile_guard();`
2. **Re-create every policy 055 dropped or replaced,** by its measured name, cmd, roles, USING and WITH CHECK, verbatim from policies.txt.
   - Each CREATE is preceded by `DROP POLICY IF EXISTS <name> ON <table>;`.
   - Each states `AS PERMISSIVE`.
   - So comparisons_select and referral_invites_select_own replace 055's versions, and a second run is a no-op.
   - The roles are `TO public` for every row except referral_invites_select_own, which is `TO authenticated`.
   - rating_cache's policy goes inside the same to_regclass DO guard, through EXECUTE.
3. **Grant back exactly what was revoked,** on named objects only:
   - TRUNCATE, TRIGGER and REFERENCES to the 21 objects;
   - ALL on eval_runs, verdict_critiques and products;
   - the per-table INSERT / UPDATE / DELETE lists of S07, S10, S14, S16, S19, S24 and S31;
   - ALL on the views and on admin_audit_log;
   - rating_cache inside the guard.

   Never ON ALL TABLES (it would over-grant the 15 tables that have none).
4. `GRANT EXECUTE ON FUNCTION public.resolve_referral_code(text) TO anon, authenticated;` then `ALTER FUNCTION public.resolve_referral_code(text) RESET search_path;`
5. **Header:**
   - it RE-OPENS every gap;
   - run it only on a ruled rollback;
   - after it, the check grid must be byte-equal to the BEFORE grid.

   It names nothing of 054.

### 4.3 The read-only check (`docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql`)
**Shape:**
- ONE statement: a WITH plus UNION ALL, so one Run shows one grid.
- Columns: section, object, fact, value (all text).
- Sources: pg_catalog and information_schema only; prosrc only inside WHERE; never FROM a public table.

**Each section names its BEFORE, AFTER and STOP:**
- **K1 policies (R-8).** Every policy on the ten tables: name, permissive, cmd, roles, USING, WITH CHECK.
  - BEFORE: the 26 rows. STOP on any row not in policies.txt.
  - AFTER, 10 rows: comparisons_select (authenticated, own), comparisons_delete, feedback_select, search_logs_select, events_select, users_select, users_update, usage_select, referral_invites_select_own (referrer only), **products_service_role_all** (R-3).
- **K2 app-role privileges (R-9).**
  - Every public relation where anon or authenticated holds any privilege, with its relkind, its owner and the seven has_table_privilege values per role.
  - STOP BEFORE when that relation set is not the measured 21.
  - Also PUBLIC's ACL entries (aclexplode, grantee 0) on those relations. STOP if PUBLIC holds any privilege 055 revokes.
- **K3 service_role.**
  - SELECT, INSERT, UPDATE and DELETE on users, comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, referral_invites, user_usage and products.
  - **SELECT on the three views (R-16)** and `rolbypassrls` of service_role (R-11f).
  - STOP on any false, before or after.
- **K4 users triggers.**
  - BEFORE: none, or users_entitlement_guard.
  - AFTER: users_profile_guard, plus 054's.
  - STOP on any other.
- **K5 guard function.** secdef false and a search_path entry.
- **K6 the six column defaults.** STOP unless: email none, created_at now(), attribution_source none, last_comparison_at none, behavior_profile '{}'::jsonb, demographics_profile none.
- **K7 views.** reloptions, and SELECT for anon and authenticated.
- **K8 resolve_referral_code.**
  - Prints secdef, proconfig, EXECUTE for anon / authenticated / service_role, and PUBLIC's ACL entry (R-9).
  - STOP if PUBLIC holds EXECUTE: S38 would abort.
- **K9 table facts.** Row security for the ten tables, and whether rating_cache is present.
- **K10 054's section-8 rule.** SECURITY DEFINER functions whose body names users, with EXECUTE for anon or authenticated. STOP on true.
- **K11 server_version_num (R-11g).** STOP unless it is >= 140000. A simple-query Run parses every statement before running any, so a pre-14 server would fail on CREATE OR REPLACE TRIGGER with a syntax error. K11 is the guard that runs first.

### 4.4 Live proofs (notes root `INC-SEC-1_PROOFS_055.sql`, never the repo; the R1-02 form)
**Form of each proof:**
- ONE DO block per Run.
- `SET LOCAL ROLE` and `set_config(..., true)` inside the block.
- Each write sits in an inner BEGIN / EXCEPTION.
- The block ALWAYS ends with a fixed `RAISE EXCEPTION 'Pn PASS'` or `'Pn FAIL <object>'`, so nothing commits.
- No count, id or value is printed.

**The proofs:**
- **P0.** The editor is a member of anon and of authenticated (pg_has_role MEMBER), else STOP.
- **P1.** As anon, no comparisons row is visible.
- **P2.** As authenticated with a block-generated sub, no comparisons row is visible.
- **P3.** As anon and as authenticated, each of these is refused with 42501: rating_cache (skipped with a fixed word when absent), the three views and resolve_referral_code.
- **P4.** As anon and as authenticated, an INSERT into each of these is refused: admin_audit_log, comparison_feedback, search_logs, user_events, comparisons (own sub) and user_usage. **Plus (R-10):** as authenticated, an UPDATE of its own comparisons row and an UPDATE of user_usage, each refused with 42501. The privilege check runs before row security, so no row is needed. 14 of 14.
- **P5.** As authenticated, an INSERT into users is refused.
- **P6** (the throwaway auth user of the 054 note):
  - a control UPDATE of expo_push_token touches 1 row, else STOP;
  - each of the six columns, changed alone, is refused with the 055 message.
- **P7.** As service_role with service claims, each of these touches 1 row: the six columns, and a feedback, search, event and audit insert.
- **P8,** as the throwaway user:
  - (a) a comparison made in the block as postgres is visible to its owner and deletable;
  - (b) (R-10) an invite row made in the block, with that user as redeemed_by and a second throwaway user as referrer (referrer_user_id and comparison_id are NOT NULL foreign keys, 014:20-21), is NOT visible to the invitee. The same row IS visible to the referrer.

## 5 SERVER CODE CHANGES
- **C1** `app/services/database_service.py` create_share_token (:596-675), unflagged (dead code):
  - Drop the access_token parameter and the user branch at :611. The client is always the admin client, built where it is built today.
  - The ownership read at :617 passes no token.
  - PermissionError, ShareTokenError and the idempotent token are unchanged.
  - Its caller share_routes.py:29 is unchanged.
- **C2** `app/services/feedback_service.py` save_feedback (:147-228), unflagged: the client is `get_supabase_client()` for both arms.
  - The access_token keyword stays: tests/test_s81_sf1_surfaces_be.py:79-80 and :470-479 pin it.
  - The docstring (:169-174) is re-worded **(R-11e):** after 055 the database refuses every app-role write to comparison_feedback, so the server writes with its own key, and C2b keeps the ownership rule.
  - The single except arm and its template `[FEEDBACK] save failed type=%s code=%s` are unchanged (GR1).
  - The `record["comparison_id"] = comparison_id` assignment stays in save_feedback, so the d22 key scan at test_s81_d22_nightly_learning.py:1592 holds.
- **C2b** (R-6). A new module-level helper in feedback_service.py: `async def _owned_comparison_id(client, user_id, comparison_id) -> Optional[str]`. It is called once from save_feedback, only when comparison_id is set, before the record is built. With no comparison_id there is no read.
  - **The read:** `await run_db(lambda: client.table("comparisons").select("user_id").eq("id", comparison_id).limit(1).execute())`, on the service client.
  - **Signed-in caller (user_id set):** keep the id only when a row exists and its user_id equals the caller. A missing row or a foreign row drops the id and logs `FEEDBACK_COMPARISON_NOT_OWNED`.
  - **Anonymous caller (user_id None)** owns no row. Drop the id when a row exists with a non-null user_id (log `FEEDBACK_COMPARISON_NOT_OWNED`). Keep it when no row exists or the row's user_id is null: anonymous compares persist no row (text_routes.py:903, image_routes.py:755, url_routes.py:372).
  - **Read fails:** drop the id and log `FEEDBACK_OWNERSHIP_UNREAD`.
  - The helper's single except arm logs one constant line, with no exception argument.
  - Every log line is `logger.warning("[FEEDBACK] FEEDBACK_COMPARISON_NOT_OWNED")` or `"[FEEDBACK] FEEDBACK_OWNERSHIP_UNREAD"`: constants only, no id.
  - The row is always written (Q2: no feedback is lost).
  - The helper lives outside save_feedback because test_gr1 (test_s81_sf1_gate_rows.py:81-85) requires exactly one except handler there (N-1).
- **C3** (R-13), DARK behind `ENABLE_REFERRAL_SAME_DEVICE_CHECK`:
  - A module helper `_referral_same_device_check_enabled()` in referral_service.py, in the house idiom: `os.getenv("ENABLE_REFERRAL_SAME_DEVICE_CHECK", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call. It is the first statement of `_load_invitee` (:789-801) that decides the select.
  - **OFF:** the select string is byte-identical: `"id, email, subscription_tier, display_name"`. So the invitee dict, evaluate_invite and every reward are byte-identical to today.
  - **ON:** the select is `"id, email, subscription_tier, display_name, device_fingerprint_hash"`, and the same-device check fires as designed (abuse_detection_service.py:248-252).
  - The fallback dict at :686-689 is NOT changed: `.get()` already yields None. That keeps OFF identical and is smaller than the draft.
  - The email half of R1-05 is closed by the 055 trigger, which has no switch.
- **Not changed:** the mobile app (no OTA), 054's SQL, Railway variables. The only switch is the new dark one.

## 6 FLAG AND ORDER WALK
| state | signed-in feedback | share | users writes | logs / audit / events | verdict |
|---|---|---|---|---|---|
| today (afde168f, 054 and 055 not applied) | user client | service | 054 and 055 columns open to the owner | open | the gaps |
| deploy C1 / C2 / C2b, 055 not applied | service; C2b may drop a foreign id | service | unchanged | unchanged | SAFE |
| **055 applied, the deploy carrying C2 NOT live** | **refused quietly**: 42501 at the insert; the route still answers "Feedback received"; only `[FEEDBACK] save failed` logs (feedback_service.py:225-227) | service | guarded | closed | **FORBIDDEN** |
| **055 applied, server rolled back to a deploy before C2 (R-5)** | the same quiet refusal | service | guarded | closed | **FORBIDDEN. Never roll the server back past the C2 commit while 055 is applied; roll 055 back first** |
| deploy, then 055; 054 not applied | service | service | the six closed; 054's eleven open | closed | SAFE |
| 054, then deploy, then 055 (R-18) | service | service | 17 columns closed | closed | TARGET |
| 055 rolled back, deploy live | service | service | the six open | open | works, gaps re-open |
| 054 rolled back, 055 applied | unaffected | unaffected | the eleven open, the six closed | closed | independent |
| C3 OFF (default), any database state | | | | | invitee select and abuse result byte-identical |
| C3 ON (the owner's flip, separate) | | | | | same-device invites are flagged SAME_DEVICE and earn nothing |

**Flags walked.** 055 reads none, and none changes:
- ENABLE_FEEDBACK_V2: one client after C2.
- ENABLE_HOME_SAVINGS_AGGREGATE: stays OFF by the HARD RULE; its function is untouched.
- ENABLE_SUPABASE_CLIENT_REUSE, ENABLE_COHORT_PERSONALIZATION, ENABLE_PAID_ROUTE_METERING and ENABLE_SEARCH_LOG_TRUTH: service paths.
- ENABLE_DEVICE_DAILY_QUOTA: pauses rewards independently of C3.

## 7 RULINGS (from the draft, kept)
- **R-A:** a second trigger, not the column grant (that grant is a FOLLOW, R-17).
- **R-B, now R-18:** the SQL is order-independent, and the cluster proves both orders. If 055 ever goes first, users_profile_guard is the one expected exception to 054 check section 1.
- **R-C:** feedback goes to the server key, and the app-role INSERT goes; C2b restores ownership.
- **R-D:** the proofs live in the notes.

## 8 TEST METHOD
- **House style, ESTABLISHED:** static rows, as in tests/test_inc_t1b_users_entitlement_guard.py:8-10. CI runs only these.
- **The throwaway cluster (R-19):**
  - PostgreSQL 18.1 at `C:/Program Files/PostgreSQL/18` (already installed; install nothing, no docker).
  - initdb into the scratchpad; loopback port; trust auth; stopped afterwards.
  - setup.sql extends the A-1 setup with: Supabase-shaped roles (service_role with BYPASSRLS); the auth.uid() / auth.role() bodies; the ten tables with the 26 measured policies by name and text (products_service_role_all included, R-3); the 21-object grants; the three views (013:23-56); resolve_referral_code (014:97-102 plus the 037 grants); 048 delete_user_cascade.
- **The runs:**
  1. base + 054;
  2. base + 054 + 055, with P0-P8 and the R-10 additions adapted to synthetic ids;
  3. each rollback, after which the K grid is byte-equal to the grid before;
  4. a re-run of 055 (idempotent) and a re-run of the rollback;
  5. 055 without 054;
  6. 055, then 054.

  S38 must pass in each run.
- **Stated limit:** production is PG 15. Every statement exists in 15: CREATE OR REPLACE TRIGGER needs 14+, AS PERMISSIVE needs 10+, and the rest is older. K11 guards it.

## 9 RED ROWS (tests/test_inc_sec1_app_user_access.py)
Every row fails at base on an AssertionError, never an import error. PIN rows are named.

**M-rows:**
- **M01** 055's up, down and check files exist once each; 039, 051 and 053 stay unused.
- **M02** (A-1) 055 and 054 exist, and 053 is absent.
- **M03** ASCII only, no 8-digit run, no id-shaped literal.
- **M04** One transaction, with S01 the first statement after BEGIN, and no session-level SET.
- **M05** (R-11b) Comments are stripped first. Then the function header is SECURITY INVOKER with `SET search_path = ''`, and no SECURITY DEFINER appears anywhere.
- **M06** The trigger is as in S26, and there is exactly one CREATE TRIGGER.
- **M07** The role test equals 054's ROLE_TEST and is first. RETURN NEW appears 3 times. No auth.* call is in the body.
- **M08** The UPDATE arm is exactly the six columns, in order, with no overlap with 054's eleven.
- **M09** The INSERT arm uses the 4.1 values.
- **M10** The message appears twice with 42501, contains `server-managed` and differs from 054's. It has no `%` and no DETAIL.
- **M11** Order: guard < function < assert.
- **M12** The up file never names users_entitlement_guard and never alters 054's objects.

**P-rows:**
- **P01** S03-S07.
- **P02** (R-3) No CREATE POLICY whose TO list includes public, anon or authenticated holds `IS NULL`, `share_token` or a bare `true`.
- **P03** Every DROP POLICY names a policy of the measured census constant (26 names over the ten tables). No policy loop.
- **P04** The revoke map per table equals section 4.
- **P05** rating_cache sits only inside a to_regclass DO, through EXECUTE.
- **P06** The users drops, and REVOKE INSERT, DELETE. users_select and users_update are not dropped.
- **P07** The views revoke.
- **P08** The F7, F10, F8 and F9 statements: F8 names anon and authenticated, never PUBLIC; search_path = public.
- **P09** S38 names each end-state check, including the role-overlap filter (`public`, `anon`, `authenticated`).
- **P10** (R-11c) Every migration numbered 055 or later that CREATEs a table also ENABLEs ROW LEVEL SECURITY on it. Its detector is a helper with a positive control: in-memory SQL with a CREATE TABLE and no ENABLE is flagged, and the same SQL with ENABLE is clean. It has a detector mutant (11).

**D-rows (rollback):**
- **D01** It drops exactly 055's function and trigger. It re-creates each dropped or replaced policy verbatim from the census. Every CREATE POLICY is preceded by a DROP POLICY IF EXISTS of the same name and states AS PERMISSIVE (R-8). It grants back on named objects only (no ON ALL TABLES). It never names 054. It is one transaction, and its header warns.

**K-rows (check):**
- **K01** One SELECT / WITH statement. No write word, SET, DO, set_config or pg_sleep.
- **K02** Sources are pg_catalog and information_schema only; prosrc only in WHERE.
- **K03** The eleven section names, the six-column list, the measured-21 list, and the words `rolbypassrls`, `server_version_num` and `aclexplode`.

**L01** sqlfluff is clean on up, down and check, with the repo .sqlfluff (large_file_skip_byte_limit = 0, max_line_length = 180).

**W-rows (AST over app/ and scripts/):**
- **W01** The user-scoped WRITE set is exactly update_push_token, update_reengagement_subs, update_preference_toggles and delete_comparison. RED at base through create_share_token and save_feedback.
- **W02 PIN** No user-scoped function inserts into or updates comparisons, comparison_feedback, search_logs, user_events, admin_audit_log, rating_cache or user_usage, or inserts into users. RED at base through the same two.
- **W03 PIN** The user-scoped users writers touch none of the six.
- **W04 PIN** Every writer of the six is service.
- **W05 PIN** The app has no supabase dependency, no createClient and no rest/v1.
- **W06 PIN** share_routes calls create_share_token with two arguments, and get_shared_comparison builds the admin client.

**C-rows (code):**
- **C01** create_share_token has no access_token parameter and no get_user_supabase_client.
- **C02** With a token, save_feedback uses the service client's `table("comparison_feedback")` and never builds a user client. save_feedback still holds exactly one except handler, and `_owned_comparison_id` exists at module level.
- **C03** (R-6) C2b, nine cases, each with a call recorder:
  1. signed-in owner: kept;
  2. signed-in foreign: dropped, NOT_OWNED;
  3. signed-in missing row: dropped, NOT_OWNED;
  4. signed-in read raises: dropped, UNREAD;
  5. anonymous, no row: kept;
  6. anonymous, row owned by a user: dropped, NOT_OWNED;
  7. anonymous, row with a null owner: kept;
  8. anonymous, read raises: dropped, UNREAD;
  9. no comparison_id: `table("comparisons")` is never called.

  In every case the row is written and the log line equals the constant.
- **C04** (R-7, R-13) A projecting fake client: select(cols) records the string, and execute returns only those keys of a stored full row that carries a synthetic device hash. With the full configuration present (B1):
  - (a) OFF, the switch unset and also set to `"false"`, `" OFF "` and `"0"`: the select string equals today's literal exactly, the invitee dict has no device key, and try_trigger_loop2 grants as today.
  - (b) ON, as `"true"`, `" TRUE "`, `"1"`, `"yes"` and `"on"`: the select string carries device_fingerprint_hash, and with the invitee hash equal to the referrer's, try_trigger_loop2 flags SAME_DEVICE and grants nothing.
  - (c) The switch is read per call: flip it between two calls.

**X01 PIN** (R-1) 054's three files, CRLF normalised to LF, hash to the base64 values in section 1. The constant names avoid gitleaks words, e.g. M054_UP_LF_SHA256.

**Mutants** (GREEN runs them on byte copies; all must be killed), with their killing rows:
- shared branch kept: P01
- `OR user_id IS NULL` kept: P02
- a misspelled policy name: P03
- feedback REVOKE removed: P04
- rating_cache outside the DO: P05
- SECURITY DEFINER in the header: M05
- SECURITY DEFINER only in a comment (must stay green, R-11b control): M05
- the role test without service_role: M07
- email out of the UPDATE arm: M08
- behavior_profile compared with NULL: M09
- 054's message: M10
- rollback ON ALL TABLES: D01
- rollback missing a policy: D01
- rollback CREATE POLICY without its DROP: D01
- the check reads public.users: K02
- the check without the PUBLIC ACL rows: K03
- create_share_token user branch: C01, W01
- save_feedback user branch: C02, W01
- the ownership read moved inside save_feedback: C02, GR1
- C2b skipped for anonymous callers: C03 case 6
- C2b keeps the id on a read failure: C03 cases 4 and 8
- C3 selecting the hash when OFF: C04 a
- C3 switch read at import: C04 c
- up drops users_entitlement_guard: M12
- F8 names PUBLIC: P08
- S38 without the role filter (cluster abort on products_service_role_all): P09, cluster run 2
- P10 detector returns early: P10 positive control

28 in all.

## 10 EXISTING PINS THIS UNIT MOVES (each a named ruling)
1. **tests/test_m13_29_feedback_uuid.py:108-137** `test_save_feedback_uses_user_client_when_authenticated` is INVERTED by R-C: the service client is used, and the user client is never built. The docstrings at :1-12 are re-worded. :139-151 (the anonymous row, comparison_id None) stays.
2. **tests/test_inc_t1b_users_entitlement_guard.py:137-142** `test_m02_next_free_number` (R-2): `numbers[-1] == 54` becomes "54 in numbers, 52 in numbers, 53 not in numbers"; the docstring says 054 was the next free number after 052. 054's SQL is untouched (X01).
3. **tests/test_migration_037_security_definer_grants.py** (R-2, R-14):
   - The live_db pin `test_anon_can_still_resolve_a_referral_code` (:995-1016) is inverted: `test_anon_cannot_resolve_a_referral_code`, expecting PostgreSQL 42501, in the shape of the neighbours at :941-993. It is the post-055 truth and is never run by agents.
   - The comments are re-worded to "037 kept the anon grant; 055 (INC-SEC-1) revokes it after the walk showed the server is the only caller": the module table and notes at :51 and :62, the comment at :354-356, the docstring at :570-579 and the class docstring at :883-895.
   - The static row at :570-611 still passes: 055 names no PUBLIC.
4. **tests/test_s81_s22b_self_critique_retire.py:110-111** (R-2), the listing digests for the file name `055_app_user_access_tightening.sql`:
   - MIG_LISTING_DIGEST `jtbmq/Yp8zE3jEdKLiwyPUaVSGyKl/E1pjX84AE2LPg=`
   - MIG_RB_LISTING_DIGEST `X08X/ecPH0JVnov9RLBSUUppIUZJSJ1tDBxIcYc4sOU=`

   Computed from the afde168f tree listing (46 and 30 entries). The method reproduces today's two values exactly. A renamed file recomputes them.
5. **tests/test_feedback.py:19-43** (R-2): the fixture configures the comparisons read as owned (`data = [{"user_id": "user-1"}]` on the `select().eq().limit().execute()` chain). Every assertion stays.
6. **N-2, the same move (needs the gate's word, Q7):** tests/test_s80_b1_feedback.py:149-157, tests/test_s81_sf1_surfaces_be.py:482-499 and :529-542. Each recording client configures the ownership read as no row (data = []), and every assertion, the key order included, stays.
7. **Unchanged and must stay green:**
   - tests/test_share_routes.py:197-235;
   - test_s81_sf1_surfaces_be.py:79-80, :470-479;
   - test_s81_sf1_gate_rows.py (GR1);
   - test_s81_d22_nightly_learning.py:1592;
   - test_referral_service.py:777-800 (a select string is not pinned there);
   - test_retro_w1_2b.py (the census; :153 is a historical comment, left);
   - test_retro_w1_2d.py:294;
   - test_security_regression.py:778, :995-1025;
   - test_s81_kb_schema.py:1186 (the policy census covers the 012 tables only) and :468;
   - test_migration_041_*, 042, 043, 044 and index_predicate;
   - 054's own rows.
8. **The comm set (union rule):**
   - the unit file and every file above;
   - every migration scanner: tests/_retro_r_mig_sql.py and its importers, test_delete_user_cascade, test_migration_037 / 041 / 042 / 043 / 044, test_migration_index_predicate_immutability, test_retro_w1_2b / 2d, test_s81_kb_schema, test_s81_s03_llm_ledger_v2, test_security_regression, test_s81_s22b, test_inc_t1b;
   - the feedback suites: test_feedback, test_m13_29, test_s80_b1_feedback, test_s81_sf1_surfaces_be, test_s81_sf1_gate_rows, test_s81_d22_nightly_learning, test_retro_w1_9;
   - the referral and abuse suites, and test_share_routes;
   - the source-scanning pins;
   - the CLAUDE.md readers (test_ci_gates, test_behavior_dimension_translation), because CLAUDE.md gains the flag row;
   - the fourteen client jest fences (app/ and migrations/ move).

## 11 FILES
- migrations/055_app_user_access_tightening.sql
- migrations/rollback/055_app_user_access_tightening.sql
- docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql (a new folder)
- tests/test_inc_sec1_app_user_access.py
- app/services/database_service.py (C1)
- app/services/feedback_service.py (C2, C2b)
- app/services/referral_service.py (C3)
- CLAUDE.md: one ENABLE_REFERRAL_SAME_DEVICE_CHECK row (default OFF, read per call, the owner's flip, the R-13 effect in one line)
- the tests of section 10 (items 1-6)
- notes root: INC-SEC-1_OWNER_SUMMARY.md, INC-SEC-1_APPLY_NOTE.md, INC-SEC-1_PROOFS_055.sql (written by GREEN)

## 12 STATED LIMITS
- **L1** Proven on a local 18.1 cluster, not on production 15. The live proof is P0-P8, and K11 guards the version.
- **L2** An unreadable request.jwt.claims raises 22P02 without the fixed message (as in 054, R1-11).
- **L3** A column added later is open to its owner until the R1-08 FOLLOW.
- **L4** (R-11d) Still writable by the row's owner: display_name, auth_provider, updated_at (013:24), preferences_completed, notifications_enabled, demographics_dismissed_count and demographics_dismissed_at. All go to the R1-08 FOLLOW.
- **L5** Default privileges for new tables are unchanged (FOLLOW). P10 pins row security instead.
- **L6** C2b keeps an anonymous comparison_id that names no row, or a row with a null owner (the legitimate anonymous case).
- **L7** rating_cache and bahrain_approved_drugs stay outside migration control. F16 is untouched.
- **L8** The catalog is the 2026-11-17 snapshot. The BEFORE grid is the truth, and a STOP sends it back.
- **L9** Out of scope: R1-04, and R2 F5's prompt escaping.
- **L10** Role switching inside a DO block was measured on the cluster only. P0 checks it live.
- **L11** (R-12) The AST writer walk sees a user-scoped client only when it is built in the same function. A client passed in as a parameter, or a new builder, slips past it. Today every client-parameter helper receives a service client (review section 1).
- **L12** The inverted 037 live_db row is false until 055 is applied.
- **L13** Until the C3 flip, the same-device control still never fires. That is the owner's choice (R-13).

## 13 OPEN QUESTIONS
- **Q7** N-2: may the three further feedback fixtures configure the ownership read as "no row" under R-2? Recommended yes, with every assertion unchanged.
- **Q8** C2 and C2b ship unflagged by R-6 and R-13. Under R-A1 only byte-identical changes ship unflagged. C2 keeps every response the same. C2b changes the stored record only when the id names another user's row. Confirm unflagged.
- **Q9** P8(b) needs a second throwaway auth user, the referrer, created and deleted like the first. It must be named in the owner's yes. Without it, P8(b) runs on the cluster only and its live line becomes a stated limit.

## 14 OUTLINES (GREEN writes them; plain words, like INC-T1B_*)
**INC-SEC-1_OWNER_SUMMARY.md:**
1. **Status:** written and tested, NOT applied; the branch commit.
2. **What is permitted today and stops,** one line each: reading other people's shared results; the old ratings table; adding audit, feedback, search and event rows; writing comparison rows; changing six more account fields (e-mail among them); the company metrics views; the referral lookup.
3. **What stays:** everything the app does. The app never talks to the database; our server does, with its own key.
4. **The order:** 054, then the server deploy, then 055. Why: signed-in feedback would otherwise be lost quietly.
   - **Never roll the server back past the feedback change while 055 is applied: roll 055 back first.**
5. **The switch, in plain words (R-13):** "Invites made from your own phone can be stopped from earning rewards. This is a new switch, off. Turned on, an invite redeemed on the same device as the inviter earns nothing. That is your choice." The e-mail lock needs no switch.
6. **The exact SQL,** with the sha256 of the up, down and check files.
7. **The undo,** and that it re-opens everything.
8. **How a failure would show:** refusals are quiet on the phone, so the logs are the proof (the apply-note words).
9. **Tested on** a throwaway local PostgreSQL 18.1 (the case counts); not yet live.
10. **Known limits:** L3, L4, L6, L13.

**INC-SEC-1_APPLY_NOTE.md:**
1. **Order (R-18):**
   - (a) 054 applied and verified;
   - (b) the deploy carrying C1 / C2 / C2b is live, and the relay confirms the deployed commit;
   - (c) the 055 window.

   The C3 flip is a separate window. If 055 must ever go first, users_profile_guard is the one expected exception to the 054 check's section-1 STOP.
2. **File hashes** of the merged blobs.
3. **BEFORE:** one Run, one grid, with the 4.3 STOP rules (K2 measured 21, K2 / K8 PUBLIC, K3, K11).
4. **APPLY:** the whole file in one Run.
5. **AFTER:** the grid again, compared with 4.3 AFTER.
6. **Proofs:** P0-P8 one Run each, with verdict lines only in the ledger. The throwaway user or users are named in the owner's yes (Q9).
7. **The real-path proof, from the owner's phone:**
   - one compare, which appears in history;
   - one share link, which opens;
   - one signed-in feedback, then **no `save failed` line within a minute** (R-4);
   - one push-token registration (HTTP 200).
8. **Logs over the window and the next 24 hours (R-4):**
   - Railway, plain words without brackets, each expected at 0:
     - `save failed`
     - `push token update failed`
     - `reengagement-subs update failed`
     - `preference-toggles update failed`
     - `Error deleting comparison`
     - `Share-token write failed`
     - plus `server-managed` and `permission denied`
   - Recorded, not a STOP: FEEDBACK_COMPARISON_NOT_OWNED and FEEDBACK_OWNERSHIP_UNREAD.
   - Supabase Postgres log: a permission-denied from authenticated on comparison_feedback, comparisons (delete) or users means **STOP and roll 055 back**. A hit from service_role or postgres also means roll back.
9. **Rollback:** the file, then the grid, which must equal the BEFORE grid. Never roll the server back past the C2 commit while 055 is applied (R-5).
10. **Stated limits:** L1, L2, L8, L10, L12.

## 15 CANDIDATES AND FOLLOWS
- **IN:** F7, F8 (R-14), F9's revoke plus P10, and F10.
- **FOLLOW (R-17):**
  - Q6: revoke everything from anon on the user tables;
  - F9 default privileges, which need a live pg_default_acl read;
  - the R1-08 column grant on users, after one quiet week.

Not done in this spec: no RED file, no SQL file, no notes file, no checkout edit, no database contact.

# INC-SEC-1 DATABASE-ACCESS (055): spec review (S96, 2026-11-17, Opus 5.5)

Read-only. Git plumbing only (`fetch` of main and pull/415 once each, then `show` / `grep` / `ls-tree`). No database, no Railway, no checkout edit, no pytest run (not needed). The repo is public: every gap below is written as what is permitted and what must change.

## Verdict: AMEND (0 BLOCKING, 6 MAJOR, 7 MINOR)

The walk holds. I redid it on my own and found no user-scoped writer or reader that the draft missed, so 055 causes no quiet refusal in the app as long as the order is kept. The SQL contract, the rollback idea, the check shape and the R1-02 proof form are sound. Six things must change before RED:
- one pin is stale;
- three existing tests move without a named ruling;
- one assert would abort the apply on a policy we keep;
- the apply note's log search cannot see the one quiet refusal the spec names;
- a server rollback state is not walked;
- C2b leaves the anonymous feedback arm unchecked, for a reason that is not complete.

## Base state seen at review time (ESTABLISHED)
- origin/main has moved: **6473769e** (PR #416, INC-I2b). The spec says 5cd93c6a. The change touches images, structured_comparison_service.py, CLAUDE.md and tests only.
- PR #415 head has moved: **41ce0c5f** (3b607254, "the 054 check prints DELETE and ALL policy USING text", then a merge of main). 054 up and down are unchanged (sha256 77310733... and 4e49a58c... at both heads). **APPLY_054_CHECK.sql changed**: it is 555c3347... at 77ac43a9 and 5168458b... at 41ce0c5f.
- I re-ran my own AST scan (every `.table(` / `.rpc(` / `.from_(` call in app/ and scripts/, with the enclosing function, whether it builds a user client, and helpers that take a client parameter) at both 5cd93c6a and 6473769e. The output is the same, line for line (209 calls). So every app/ and scripts/ line the walk cites is still right at the new main.

## 1. The walk, redone (CHECK 1, 2, 4)
- **User-scoped references (ESTABLISHED, scan `sec1/review_scan_out.txt` / `review_scan_main.txt`):**
  - The same 18 as walk section G: database_service.py :517 :550 :570 :640 :718; home_routes.py :270 :763 :804 :983; profile_routes.py :201 :328 :494; auth_routes.py :1466 :1543 :1548 :1614 :1622; feedback_service.py :220.
  - Plus profile_routes.py:351 (referral_redemptions, which 055 does not touch).
  - The only user-scoped WRITES on a table 055 closes are database_service.py:640 (C1) and feedback_service.py:220 (C2).
  - The three users writers write only expo_push_token (:1467) or preferences (:1549, :1623). notifications_enabled sits inside preferences.
- **Helpers that take a client parameter** (admin_routes `_openai_rows` / `_llm_rows`, auth_routes `_inherit_device_counter*`, usage_service `_maybe_reset_referral_bonus`, cron_reengagement `_fetch_eligible_users`): every caller passes a service client (auth_routes.py:739-741, usage_service.py:891, admin_routes.py:497/:523/:1145/:1194, cron_reengagement.py:131).
- **ReferralService and AbuseDetectionService:** both write through `self.client = get_admin_supabase_client()` (referral_service.py:232, abuse_detection_service.py:112). `user_client` is never used.
- **RPC callers** (referral_service.py:429, usage_service.py:868 / :1121, database_service.py:419, kb_serve.py:170, cron_compare_judge.py:798) are service. home_routes.py:101 calls a function that does not exist live (functions.txt has no such row).
- **Raw SQL and other clients:** no asyncpg, psycopg, sqlalchemy, DATABASE_URL or pg8000 in app/ or scripts/. The public-key client in auth_service (`get_auth_client`) only calls `.auth.*`. Every `.table(` in auth_service goes through `get_admin_client`.
- **Mobile app:** SmartCompareApp has no supabase dependency. Its src has no createClient, apikey or rest/v1 (only comments). `.github` uses dummy values. landing/ and cloudflare-workers/ have no reference.
- **Share page (CHECK 2):** ESTABLISHED.
  - share_routes.py:29 calls `create_share_token` with two arguments, so database_service.py:611 takes the service branch.
  - The ownership read (:617, no token) is service.
  - The public page reads through the service client at :684.
  - The referral share path (referral_service.create_invite and resolve_invite) is service.
  - C1 removes dead code only.
- **Order (CHECK 4):** ESTABLISHED. C2 is the only code change that must deploy before 055. C1 is dead in production. C3 is independent of 055. But see F-04 and F-05.

## 2. 054 and order independence (CHECK 3)
- 055 as specified names no 054 object, its guard needs none, and its assert checks only its own trigger. The order independence holds.
- The 054 check at the new head adds a section-4 STOP "on every DELETE or ALL policy except the Service role full access row". If 055 goes first, that row is gone, and a missing row is not a STOP, so R-B's only exception stays section 1 (APPLY_054_CHECK.sql:11).
- X01 is stale (F-01).

## 3. Rollback (CHECK 5), check and proofs (CHECK 6), tests (CHECK 7), text (CHECK 8)
- **Rollback:** named objects, measured text, no ON ALL TABLES, RESET search_path and the anon / authenticated re-grant. This restores today's state for what 055 removes, with the gaps in F-08 and F-09.
- **Check:** one statement over pg_catalog and information_schema, with prosrc only in WHERE. It prints catalog facts only.
- **Proofs:** one DO block each, ending in a fixed RAISE. They commit nothing and print no count, id or value. The role switch works because SET ROLE checks the session user's membership; P0 checks it live.
- **RED rows:** sound, except C04 (F-07) and the vacuous P10 (F-11).
- **Text:** no misuse text, key or project ref in the draft or the walk (grep run). The catalog INDEX in the notes names the project; no planned repo file copies it.

## 4. Findings
| id | sev | where | claim | fix |
|---|---|---|---|---|
| F-01 | MAJOR | draft 9 X01; 1 BASE STATE | X01 pins 054's three files to "their 77ac43a9 sha256 values (the owner summary's hashes)". These disagree for the check file: 555c3347... at 77ac43a9, but 5168458b... in INC-T1B_OWNER_SUMMARY.md:206 and at PR #415 head 41ce0c5f. As written, X01 fails against the 054 that will merge. Also, main is now 6473769e | Pin X01 to the 054 blobs at the head that merges (today 41ce0c5f: up 773107328337..., down 4e49a58cc018..., check 5168458b118a...), and re-read them at the cut. Re-state the base as 6473769e. The walk lines are unchanged there (independent scan) |
| F-02 | MAJOR | draft 10 (pins moved) | Three existing rows break, and section 10 does not name them: (a) tests/test_s81_s22b_self_critique_retire.py:110-111 and :452-453 (at 41ce0c5f) pin sha digests of the migrations/ and rollback/ listings, which change when the 055 files are added (054 had to re-pin them); (b) tests/test_feedback.py:19-43 calls save_feedback with user_id plus comparison_id on an un-configured MagicMock and asserts comparison_id is kept, but C2b's ownership read on that mock reads as "not owned" and drops it; (c) tests/test_migration_037_security_definer_grants.py:995-1016, the live_db pin `test_anon_can_still_resolve_a_referral_code` (and the :883-895 docstring), becomes false once F8 is IN | Add all three to section 10 as named rulings: (a) a re-pin; (b) the fixture configures the comparisons read as owned; (c) inverted to "anon is refused with 42501" if Q1 is IN, otherwise left alone. Add test_feedback.py and test_s81_s22b to the comm set |
| F-03 | MAJOR | draft S38; 4.3 K1 | S38 refuses any policy "on the ten tables" whose text holds a bare true, but the ten tables are never named. K1 BEFORE says 26 rows. The nine tables 055 names carry 25 policies (policies.txt), so the tenth is LIKELY products, whose kept products_service_role_all (policies.txt:15) is USING true WITH CHECK true for service_role. As specified, the assert would abort the apply. K1 AFTER also omits that policy | Name the ten tables. Apply the bare-true, IS NULL and share_token tests only to policies whose roles include public, anon or authenticated. List products_service_role_all in K1 AFTER. Put products_service_role_all in the cluster setup so GREEN proves the assert passes |
| F-04 | MAJOR | draft 14 apply note 7-8 | The one quiet refusal the spec forbids (signed-in feedback refused because 055 is ahead of the deploy) is invisible to the planned searches. (1) feedback_service.py:225-227 logs only "[FEEDBACK] save failed type=... code=...", which contains neither "server-managed" nor "permission denied". (2) Step 8 says a Postgres-log hit "from anon or authenticated is the rule working". But the server's own user-scoped client runs as authenticated, so its refusals would be read as success. The "one signed-in feedback" proof cannot fail: the route always answers "Feedback received" | Railway search adds the plain words: save failed, push token update failed, reengagement-subs update failed, preference-toggles update failed, Error deleting comparison, Share-token write failed; expect 0. A Postgres-log "permission denied" from authenticated on comparison_feedback, comparisons (delete) or users means STOP and roll 055 back. The real-path feedback proof is: no "save failed" line within a minute of the owner's feedback |
| F-05 | MAJOR | draft 6 flag and order walk | It does not walk "055 applied, server rolled back to a deploy before C2". That brings back the FORBIDDEN quiet refusal of signed-in feedback, and a server rollback is the usual emergency move. "Code C1-C3 needs no rollback" (4.2) is true only in the other direction | Add the row (FORBIDDEN). In the apply note and the owner summary: never roll the server back past the C2 commit while 055 is applied; roll 055 back first. The F-04 search words also catch it |
| F-06 | MAJOR | draft 5 C2b; 12 L6 | C2b checks ownership only for signed-in callers. L6 says no app-role read hands out another user's comparison id. But our own auth-optional invite endpoints return the referrer's comparison id (referral_service.py:478 and :521, through referral_routes.py:285-303 with get_optional_user). Anonymous feedback naming that id is still written with it, and the judge counts winner_correct = wrong by comparison_id (cron_compare_judge.py:612-620). The brief's F4 line ("must name the caller's own comparison") is not met for that arm | Run C2b for anonymous callers too. They own no row (anonymous compares save none, text_routes.py:903), so drop comparison_id whenever the read finds an owned row or fails, with the same fixed log words. Add the cases to C03. Otherwise rule it as an owner-visible limit, with the correct reason |
| F-07 | MINOR | draft 9 C04 | The behavioural half (same invitee hash flags SAME_DEVICE) passes at base if the fake client returns its configured data whatever the select string. tests/test_referral_service.py:779-787 shows that mock shape | Use a fake that projects the select list, or assert on the select call's argument |
| F-08 | MINOR | draft 4.2, 4.3 | The rollback re-creates comparisons_select and referral_invites_select_own, which 055 replaced. A CREATE with an existing name fails unless the 055 version is dropped first. Rollback idempotence is not stated. K1 does not print permissive or roles, though the new 054 check does | DROP POLICY IF EXISTS before every rollback CREATE POLICY, AS PERMISSIVE stated. K1 prints name, permissive, cmd, roles, USING and WITH CHECK |
| F-09 | MINOR | draft S36, 4.3 K2 / K8 | S36 is ON ALL TABLES, but K2 checks a fixed list of 22 objects. A relation that gained app-role grants after the snapshot would lose TRUNCATE, TRIGGER and REFERENCES with no STOP and no rollback. If PUBLIC holds a privilege 055 revokes from anon (a table privilege, or EXECUTE on resolve_referral_code), S38 aborts the window with no BEFORE warning | K2 lists every public relation where anon or authenticated holds any privilege, plus its owner, and STOPs BEFORE when that set is not the measured 21. K2 and K8 also print what PUBLIC holds (the ACL) and STOP if PUBLIC holds anything 055 revokes |
| F-10 | MINOR | draft 4.4 | Not proven live: an authenticated UPDATE of its own comparison (S05-S07); the F10 invitee read; a user_usage UPDATE | Add them to P4 and P8 |
| F-11 | MINOR | draft 4, 8, 9, 12 | Smaller gaps: (a) the quoted policy names in S11-S23 and the rollback CREATEs need `-- noqa: RF05`, not only S08; (b) M05 must strip comments before "no SECURITY DEFINER"; (c) P10 passes vacuously, so add its detector mutant; (d) L4 omits the notifications_enabled column; (e) C2's new docstring should say "after 055"; (f) K3 has no service_role rolbypassrls row, though dropping "Service role full access" rests on it; (g) no server_version_num row, though CREATE OR REPLACE TRIGGER needs 14+ and "prod is 15" is LIKELY (027:40-43 "as of audit") | Fold each into its row |
| F-12 | MINOR | draft 9 W01 / W02 | The AST walk sees a user-scoped write only through a `get_user_supabase_client` call in the same function. A user client passed in as a parameter, or a new builder, slips past it | State it as a limit, or extend W01 to callers that pass a user client into a helper |
| F-13 | MINOR | draft 13 Q3; 5 C3 | C3 changes rewards (same-device invites stop earning) with no flag. Under the standing rules a product-visible change is the owner's call | Keep Q3, and make the owner's ruling a gate item rather than a summary line |

## 5. File:line (CHECK 9)
- Correct at 5cd93c6a (and unchanged at 6473769e): every app/ and scripts/ line in the draft that I spot-checked (database_service :379 :493 :517 :550 :570 :596-675 :611 :617 :640 :684 :718 :830 :855 :916 :929 :954; feedback_service :147-228 :184 :220 :225-227; share_routes :29; history_routes :150-154; audit_service :30-31; admin_routes :618 :640 :677 :681 :688 :743 :746 :1069; auth_routes :1466 :1548 :1622; auth_service :408 :830 :887-897; referral_service :232 :429 :686-689 :789-801 :793; abuse_detection :112 :124 :248-252; extraction_service :2041-2073; structured_comparison_service :6068 :6103).
- Migrations: 011:8 and :34, 014:97-102 and :100, 013:24, 027:40-43, 037:101-112, 041:75 and 048:259-279 are correct.
- Catalog: policies.txt, table_grants.txt, views.txt, functions.txt :13 and columns.txt :432-459, :434-445 and :453-454 are correct.
- Off: X01 (F-01). test_migration_037 ":353-357" is the comment at :354-356. APPLY_054_CHECK.sql ":11-12" is the STOP at :11.

## 6. Not checked
- The live database (by rule). Whether service_role holds SELECT on the views (Q5) and BYPASSRLS stays LIKELY until K3 runs.
- Whether the throwaway-cluster setup will carry products_service_role_all (F-03) is for GREEN to prove.

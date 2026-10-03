## U8b: account deletion erases every personal column and every user-owned row (migration 043, NOT applied by this merge)

### What changes
- **`migrations/043_delete_user_cascade_full_erasure.sql`** (new, unapplied). One transaction that replaces `public.delete_user_cascade(uuid)`. It still runs as SECURITY DEFINER with `search_path=public`, and the 037 ACL (`{postgres,service_role}`) is kept. In order:
  - **guard block:** the 13 tables exist; the 25 users columns the function writes exist; none of the 17 columns erased to NULL is NOT NULL live; `admin_audit_log.ip_address` is nullable. It then writes the 25 tombstone values into a temp copy of `public.users` (`LIKE ... INCLUDING DEFAULTS INCLUDING CONSTRAINTS`), so a live CHECK or NOT NULL that rejects a tombstone value aborts the apply instead of the first real deletion. (The probe cannot see unique indexes or foreign keys; PRECHECK covers those.)
  - **the function:** 025's seven DELETEs in 025's order. Immediately before the comparisons DELETE, it detaches other users' (and anonymous) `user_events` / `comparison_feedback` rows that point at the target's comparisons (`comparison_id = NULL`), so a NO ACTION FK can no longer block a deletion. Then it DELETEs from `deep_review_credits`, `re_engagement_events`, `pain_workflow_events` and `user_preference_history`, sets `admin_audit_log.ip_address = NULL` on the target's rows, and writes a 25-column tombstone UPDATE on `users`. Only `id`, `created_at` and `updated_at` (the erasure time) keep a value; the three NOT NULL columns get 0 / false / 0, `subscription_tier` gets 'free' and the counters get 0;
  - **REVOKE** from PUBLIC, anon and authenticated (no GRANT is restated);
  - **assert block:** first a nil-uuid dry run (`PERFORM public.delete_user_cascade('00000000-...'::uuid)`), so a missing user_id / comparison_id column aborts inside the transaction. It then proves SECURITY DEFINER, `proconfig = {search_path=public}`, service_role EXECUTE, and no EXECUTE for anon or authenticated.
- **`migrations/rollback/043_...`**: restores the 025 statement byte for byte (025:28-70). It restores the function only (see the rollback note below).
- **Four one-paste files** in `docs/investigations/2026-10-03-session-71-state/`: `APPLY_043_1_PRECHECK.sql` (read-only), `APPLY_043_2_ONE_PASTE.sql` (byte-identical body), `APPLY_043_3_POSTCHECK.sql` and `APPLY_043_4_BACKFILL_ORPHANS.sql` (optional).
- **Backend (R6):** `auth_service.delete_user_account` now runs the cascade, then a fail-soft purge of the five per-user caches derived from erased rows (`home:savings`, `home:smart_pick`, `profile_recent`, `monthly_stats`, `priorities_weighted`), then the auth delete. Under `ENABLE_ASYNC_REDIS_OFFLOAD` the purge runs off the loop. A cascade failure skips the purge and the auth delete; a purge failure never blocks the auth delete.
- **Backend (R7):** the two deletion log lines log the exception TYPE (and the SQLSTATE in the cascade line), never `str(e)`, and attach no traceback. A PostgREST APIError's string carries `details` = "Failing row contains (...)", which is the user's whole row.
- **Tests:** `tests/test_migration_043_delete_user_cascade.py` (51 nodes: 043 pins plus a widened static fence), `tests/test_account_deletion_u8b.py` (10 nodes) and `tests/test_account_deletion_u8b_fix_pins.py` (10 nodes, added in the fix round: no traceback on either log line, no exception-text fallback in the SQLSTATE slot, the purge really runs off the loop under the flag, the purge WARNING names the type only).

### Why
App Store guideline 5.1.1(v) requires account deletion to delete the account's data. The 025 function keeps the `users` row and erases only 5 columns.

Measured by the GREEN agent on a local PostgreSQL 18 stand-in with a fully seeded user, **025 leaves 23 non-null `users` columns** (email, display_name, auth_provider, demographics_profile, demographics_dismissed_at, referral_code, referral_bonus_reset_at, subscription_expires_at, last_comparison_at, attribution_source, terms_accepted_at, terms_version, age_attested_at, the counters, created_at, updated_at, id). It also leaves **4 rows** (one each in deep_review_credits, re_engagement_events, pain_workflow_events, user_preference_history) and **the audit-log IP**.

The static fence lists **25 gaps at base**: 20 users columns, `admin_audit_log.ip_address` and 4 tables. Under 043 the same user keeps 10 non-null columns (id, created_at, updated_at, and 'free' / 0 / false), has 0 rows left in the 11 tables, and only the target's audit IP is nulled.

025's stated reason for keeping the row ("admin_audit_log foreign keys") is false: 011 creates `admin_audit_log.user_id` with no FK.

Two code findings are fixed:
- **F-CACHE:** for up to 6 h after a deletion, Redis still served content derived from the erased rows.
- **F-LOG:** a failing cascade logged the user's row to Railway, and via Sentry's logging integration.

### NOTHING IS APPLIED BY MERGING. Apply runbook for the owner (Supabase SQL editor)
1. **Run `APPLY_043_1_PRECHECK.sql` alone and send the whole grid back.** STOP (apply nothing) if any of these hold:
   - section 1 does not show exactly 27 columns, or shows `nullable=NO` on a column 043 sets to NULL;
   - section 2 or 3 shows a CHECK, UNIQUE or unique index (including `lower(email)`) that a tombstone value ('free', 0, false, now(), NULL) violates; or a UNIQUE constraint / unique index declared `NULLS NOT DISTINCT` (two tombstones collide on NULL, so the second deletion fails); or any FOREIGN KEY from `users` to a table other than `auth.users` (for example `subscription_tier` -> a plans table without 'free'). The apply-time probe only tests CHECK and NOT NULL: these pass the apply and then fail a real deletion with a 500;
   - section 4 shows an FK into `public.comparisons` with NO ACTION or RESTRICT from a table other than `user_events` and `comparison_feedback`, or an FK into `public.users` or `auth.users` from a table that is not one of the 13 (043 does not erase that table; in branch B its rows survive);
   - section 6 is not `secdef=true config=search_path=public owner=postgres acl={postgres=X/postgres,service_role=X/postgres} md5_norm=76e8e2f65e9d5cb3b29c5ab57ab9bf61`;
   - section 7 is not service_role true / anon false / authenticated false;
   - section 8 shows any trigger or rewrite rule (review it first: an archive trigger or a DO ALSO / DO INSTEAD rule defeats the erase);
   - section 11 shows FORCE ROW LEVEL SECURITY, or a function owner that neither owns the table nor has BYPASSRLS;
   - section 12 shows any nil-uuid row.
   Section 9 is recorded: a, b, c, d, e decide the backfill; the four **f** rows count rows of accounts deleted OUTSIDE the app (for example from the Supabase Auth dashboard in branch A) whose user has neither an auth.users nor a public.users row. Neither 043 nor the backfill erases them; if any f is above 0, send the grid back (not a STOP for the apply). Sections 10 and 13 are informational.
2. **Run `APPLY_043_2_ONE_PASTE.sql`** (one paste, one run). Success looks like "Success. No rows returned". Any error (a guard or assert RAISE, a probe CHECK or NOT NULL violation, the dry run hitting a missing column) rolls back everything and leaves 025 in force. Do not edit and retry: send the error back.
3. **Run `APPLY_043_3_POSTCHECK.sql`.** Expected:
   - section 1 `dry_run ok`;
   - section 2 `secdef=true config=search_path=public owner=postgres acl=<unchanged> md5_norm=970e7ecc98821f8e97581ee76d4162c9`;
   - section 3 service_role true, anon false, authenticated false;
   - section 4 `0`.
4. **Run `APPLY_043_4_BACKFILL_ORPHANS.sql` ONLY if PRECHECK section 9 c or d was above 0**, after the POSTCHECK passed. Expected `c_after = 0, d_after = 0`; `f_after` equals the sum of the section 9 f rows and is NOT erased by this file (above 0 = send it back). It can be re-run. **It also changes rows of live users:** where an orphan was the redeemer of a live user's invite, that invite and its redemption are deleted (the inviter loses that bonus; 025 behaviour kept by UR8), and live users' or anonymous `user_events` / `comparison_feedback` rows that point at an orphan's comparison keep the row with `comparison_id` set to NULL.
- **Rollback:** paste `migrations/rollback/043_delete_user_cascade_full_erasure.sql`. It restores the 025 FUNCTION only: rows and columns 043 erased stay erased, and cleared audit IPs do not come back. After a rollback a deletion is the 025 behaviour again: the IP stays on the user's audit rows in both branches; in branch B the users row keeps its personal columns and the four 014/028/029 tables keep their rows (in branch A those go only when the auth delete succeeds); and the C2 failure returns: where `user_events.comparison_id` or `comparison_feedback.comparison_id` is NO ACTION/RESTRICT, any other user's or anonymous row pointing at the target's comparison makes the deletion fail with a 500 and erase nothing (measured under 025: `update or delete on table "comparisons" violates foreign key constraint "comparison_feedback_comparison_id_fkey"`). The backend changes work with either function and stay.

### Privacy defaults the owner may change BEFORE applying (each is one place in the tombstone map or function body; the test fence's expected map changes with it)
- **UR3:** `admin_audit_log` rows of the deleted user are kept for abuse forensics, with `ip_address` set to NULL.
- **UR5:** the consent columns (`terms_accepted_at`, `terms_version`, `age_attested_at`) are erased.
- **UR10:** deleting and re-registering on the same device resets the free quota, because the device fingerprint is erased (true since 025).

### Policy statement U8 may use (after 043 is applied and POSTCHECK passes, after the backfill when section 9 c or d > 0, and only if every section 9 f row is 0 or the f follow-up has shipped; corrected per review C10 and the fix round)
> When you delete your account (Profile, then Edit profile, then Delete account), we immediately and permanently delete from our servers your comparisons and the links you shared, your searches, feedback, usage, referral and in-app activity records and your preference history, and we erase your email address, name, sign-in provider, demographic answers, referral code, notification token, device identifier, preferences, consent records and other profile details from your account record. We keep only a de-identified record (a random account number, the date the account was created and the date it was erased) [only if PRECHECK section 4 shows `users_id_fkey ... ON DELETE CASCADE`: , which is removed together with your sign-in account] and security logs linked to that number with your IP address removed: sign-in events, referral-abuse checks and, if you joined with an invite code, the record of that redemption (which keeps the inviter's code). Short-lived usage counters keyed by that number (how many comparisons were used today and this month) expire within about 32 days. Records of failed sign-in attempts and lockouts are not linked to your account and keep the IP address (and, for lockouts, a one-way hash of the email address) for [retention period]. If your account redeemed an invite, that invite and its redemption are removed too, including the bonus the inviter received from it. Copies in our backups and service logs (including our hosting, error-monitoring and sign-in providers' logs) expire on those systems' schedules.

Do not claim that searches saved on the device are deleted until the `@qaren_recent_searches` follow-up ships, and do not claim that accounts removed outside the app before or after 043 are fully erased while any PRECHECK section 9 f row is above 0.

### Deploy behaviour
- The backend changes are **unflagged and live at deploy**: the cache purge and the type-only log lines. They work with either 025 or 043 in the database; the RPC name and arguments are unchanged.
- The database function changes **only when the owner applies 043**.

### Process
- The spec was adversarially reviewed (corrections C1-C14) and ruled by the orchestrator (UR1-UR15).
- RED tests were written by an Opus agent and gated PASS by the orchestrator (UG1-UG6): at base 35 failed / 26 passed.
- GREEN was written by an Opus agent; an SQL/privacy adversary and a backend adversary (both Opus) reviewed it (verdict SOUND, minors only).
- A fix round (Opus) applied the minors: PRECHECK/BACKFILL/rollback wording and visibility, the policy text, and a new pin file for five surviving backend mutants. 043, the one-paste body, POSTCHECK and the three backend files are unchanged by the fix round.

### Gates (verbatim)
- RED at base: `[pyt] tag=u8b-green-red-at-head ... elapsed=14s bound=600s status=FAIL rc=1` -- 35 failed, 26 passed.
- G1: py_compile rc=0; ruff `E9,F63,F7,F82`: All checks passed! (re-run in the fix round with the new pin file: same.)
- G2: sqlfluff on 043 and rollback/043: All Finished! (rc 0), re-run after the rollback header change.
- G3 (fix round): `[pyt] tag=u8b-fix-red-final start=2026-10-03 12:00:12 end=2026-10-03 12:00:48 elapsed=36s bound=600s status=OK rc=0` -- 61 passed; netguard 0.
- New pins: `[pyt] tag=u8b-fix-newpins start=2026-10-03 11:46:46 end=2026-10-03 11:46:51 elapsed=5s bound=600s status=OK rc=0` -- 10 passed; mutants MD1, MD2, MS, MG, MG2, MW each KILLED (2/2/3/1/1/1 failures), every restore sha-equal.
- G4 PIN set (fix round): `[pyt] tag=u8b-fix-pins start=2026-10-03 12:01:04 end=2026-10-03 12:02:13 elapsed=69s bound=1200s status=OK rc=0` -- 242 passed, 4 deselected. The +1 over base is the new `test_index_predicates_are_immutable[043_...]` node.
- `tests/test_security_regression.py` (fix round): `[pyt] tag=u8b-fix-secreg start=2026-10-03 12:02:43 end=2026-10-03 12:03:21 elapsed=39s bound=600s status=OK rc=0` -- 104 passed.
- G5 comm gate (GREEN, confirmed by the backend adversary; not re-run in the fix round because no app/ file changed):
  - set: 114 files, `auth_service|database_service|auth_routes|cache_service|migrations`, base `ca604e0a`;
  - 5 chunks per side, -rA; pytest summary totals base 2906 passed / 2 failed / 2 skipped, head 2907 passed / 2 failed / 2 skipped;
  - FAILED+ERROR base 2 / head 2 (`test_auth_interceptor` x2, both in `.pre_impl_failures.txt`);
  - **comm -13 empty**;
  - the only difference is the new 043 parameter node.
- G6: 20 of 20 spec mutants killed (M1-M15 from spec 5.4, M16-M20 from C1-C3/C4/C2), plus the six fix-round backend mutants above. Every restore is sha-equal.
- G8, PostgreSQL 18.1 single-user (no listener, no network; stand-in schema plus all forward migrations; only 036 fails, as in production where it is unapplied):
  - PRECHECK at 025 gives `md5_norm=76e8e2f65e9d5cb3b29c5ab57ab9bf61`;
  - 043 applies, and POSTCHECK gives `dry_run ok`, `md5_norm=970e7ecc98821f8e97581ee76d4162c9`, ACL `{postgres=X/postgres,service_role=X/postgres}`, true / false / false, `0`;
  - a seeded user deleted as service_role leaves the exact 25-column tombstone and 0 rows in 11 tables, nulls the audit IP for the target only, and detaches the cross-user and anonymous refs. A second call changes only `users.updated_at` (re-stamped); no other column or row changes. anon gets `permission denied`. A branch-A auth delete removes the stub;
  - rollback restores `76e8...` with the ACL unchanged; 043 applied twice is idempotent;
  - backfill in branch B gives `c_after 0 | d_after 0`, twice;
  - abort paths through the one-paste, each leaving `76e8...` (025) in force:
    - missing users column: `043 guard: public.users lacks column(s): terms_version`;
    - renamed child column: `column "user_id" does not exist ... delete_user_cascade(uuid) line 26`;
    - NOT NULL email: `043 guard: NOT NULL live, cannot erase to NULL: email`;
    - CHECK violated by the tombstone: `new row for relation "u8b_probe" violates check constraint`, at both the probe INSERT and the probe UPDATE;
  - the comment-stripped, one-line-joined paste gives the same `970e...`.
  - fix round (fresh cluster): the new PRECHECK runs read-only with 0 errors; section 8 lists an archive trigger AND a `DO ALSO` rule on `search_logs`; a branch-A dashboard deletion of a user shows section 9 f = 1 comparisons / 1 comparison_feedback / 2 user_events and the backfill reports `c_after=0 | d_after=0 | f_after=4` (honest, no longer an all-clear); in branch B the backfill deleted a live inviter's invite and redemption and detached his event, while keeping his email and IP; rollback/043 with the new header restores `76e8...`, and re-applying gives `970e...`; RLS IS enforced in the single-user backend for a table whose OID is >= 16384 (OID 17061: the deletion returned no error, left the preference row and tombstoned the users row), and PRECHECK sections 6 and 11 flag that configuration (`owner=fnowner`, `fn_owner=fnowner rolbypassrls=false`).

### Stated limits
- RLS: single-user mode enforces RLS only for tables with OIDs >= 16384 (measured both ways); an RLS-filtered DELETE or UPDATE changes 0 rows with no error, so PRECHECK section 11 (and the section 6 owner) must be read before applying; nothing detects a later owner change.
- The live constraints, triggers, rules and FK branch are decided by PRECHECK; the apply-time probe tests CHECK and NOT NULL only.
- Repeated calls re-stamp `updated_at`, so the stub's erasure date moves with every retry or backfill re-run.
- Races: a compare in flight during the deletion can still write after the cascade. A late `user_events` row (no FK) survives in both branches; a late `comparisons` row survives in branch B until a manual backfill, and in branch A unless `comparisons.user_id` has a live FK to `auth.users`; a late `search_logs` row in branch A blocks the auth delete (FK NO ACTION, 002:7) and the user sees a 500 (a retry then succeeds). Neither PRECHECK section 9 nor the backfill counts late rows of a user whose users row still exists.
- With `ENABLE_ASYNC_REDIS_OFFLOAD` unset (the production default) the purge runs 5 blocking Upstash DELs on the event loop (the R6 shape, the `history_routes` idiom; the route is limited to 1/minute); with `ENABLE_UPSTASH_BOUNDED_TRANSPORT` also unset a stalled Upstash can hold the worker for up to ~13 s per key.
- During a Redis outage each deletion adds 5 ERROR lines from the pre-existing `Cache delete error: {e}` log in `cache_service.delete_cached` (and, via Sentry's logging integration, up to 5 events); the purge's own type-only WARNING is reachable only if `delete_cached` itself raises.
- Pre-existing at base: the route raises `HTTPException(500)` inside `except`, so the Starlette/FastAPI Sentry integration sends the chained exception's text for a RuntimeError / httpx / AuthApiError (backend adversary probe); a PostgREST APIError sends `.message` only, never `details`.
- Not covered:
  - Railway and Sentry logs already written;
  - Supabase backups and PITR;
  - the GoTrue auth audit log (PRECHECK section 13 only counts it);
  - data already sent to OpenAI;
  - anonymous `search_logs` and `user_events` rows that carry no user id;
  - unlinked `login_failed` and `brute_force_lockout` rows;
  - rows of accounts removed outside the app that left no users row (PRECHECK section 9 f);
  - Sign in with Apple token revocation (U11).

### Follow-ups
- **Needs an orchestrator ruling:** erase (or detach) the comparisons / user_events / comparison_feedback / search_logs rows of accounts removed outside the app that left no users row (PRECHECK section 9 f); this changes R9 and the frozen backfill test.
- **Needs an orchestrator ruling:** `raise HTTPException(...) from None` in `delete_account` so Sentry no longer carries the chained exception text (changes the R7-frozen raise line).
- `cache_service.delete_cached` should log the exception type, not `{e}` (Redis-outage noise on the delete path).
- Widen the reverse cache-key fence to `.format` / `%` / concatenated keys and other per-user id names (none exist today: grep census of `app/`).
- Client: clear `@qaren_recent_searches` in the delete handler and in `clearSession` (OTA; ship before U8 claims device searches are deleted).
- An `admin_audit_log` retention window (for example 12 months), covering ALL rows, especially the unlinked `login_failed` and lockout rows that keep IPs.
- The referral side effect: deleting an account that redeemed an invite deletes the inviter's invite and redemption rows, and with them the inviter's bonus (025 behaviour, kept by UR8; the backfill applies it to past orphans too).
- `users.governorate` is read by `scripts/cron_reengagement.py` and `reengagement_service.py` but does not exist live (filed separately by the orchestrator).

## Orchestrator review (session 71)
- Process: Opus spec, Opus adversarial spec review (14 corrections), orchestrator rulings UR1-UR15, Opus RED gated PASS (UG1-UG6), Opus GREEN, two Opus adversaries (SQL and privacy on a fresh PostgreSQL 18 single-user cluster in both FK branches; backend regression with the module-reference comm gate re-run), both SOUND with 0 defects; the fix round changed no app code, rewrote the PRECHECK STOP rules, the BACKFILL header and the rollback warning, and added one pin file that the orchestrator gated (rulings UF1-UF8 in the spec).
- The orchestrator re-hashed the thirteen files against the fix report, read migration 043, the backend diff (three files, 49 lines) and the pin file, fast-forwarded the branch to main `0a7446b4` and re-ran the three unit files (71 passed) and the 8-file pin set (242 passed, 4 deselected).
- Follow-ups filed from the adversaries: rows of accounts deleted outside the app (PRECHECK section 9 f) are reported but not erased; `raise ... from None` on the deletion route so Sentry stops carrying the chained exception text; the Redis-outage ERROR lines of `delete_cached`; a guard-level check for NULLS NOT DISTINCT indexes and outgoing FKs; the client `@qaren_recent_searches`; an audit-log retention window.
- Until the first follow-up ships, accounts are deleted through the app (or `select public.delete_user_cascade(<id>)` before an auth delete), never from the Supabase Auth dashboard alone.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

> **HELD FOR THE OWNER: do not merge while he is away (orchestrator ruling ORCH-SEC1-B).** This PR changes a live write path (feedback) with no switch, so its merge word comes from the owner, together with the apply of migration 055. Order for his sitting: (1) his yes, (2) merge, (3) the deploy seen healthy, (4) 055 in its own window with the check before and after, (5) the proofs, the phone and the log searches. **055 is written and tested, NOT applied anywhere.**

## What this does

The database's public key is public by design. Today a holder of that key can do more in the database than the app ever needs. Migration 055 closes these openings; the server, which uses its own key, is unaffected.

**What the public key may do today, and stops after 055:**
- read other users' shared comparison rows;
- read and change `rating_cache`;
- add audit, feedback, search and event rows while signed out;
- add or rewrite comparison rows when signed in;
- change six more fields of the user's own row than 054 guards (`email`, `created_at`, `attribution_source`, `last_comparison_at`, `behavior_profile` and the whole `demographics_profile`);
- read the three cohort views;
- call `resolve_referral_code` directly (037's anon grant is withdrawn).

After 055 a signed-in user still reads, and may delete, only their own comparisons.

**Server changes (deploy before 055):**
- **C1:** `create_share_token` always uses the admin client. The user-key branch was never used in production.
- **C2:** `save_feedback` writes with the service client. It must be live before 055, or signed-in feedback is refused quietly. No switch, by ruling Q8: a switch would only add that silent-loss state.
- **C2b:** `_owned_comparison_id` keeps a feedback row's `comparison_id` only when the comparison is the sender's own. The row is always written.
- **C3:** the referral same-device check, dark behind the new server-side switch `ENABLE_REFERRAL_SAME_DEVICE_CHECK` (default OFF, read per call). With it OFF the select string and the abuse result are byte-identical to today. Turning it on changes who earns rewards, so it is the owner's flip, in its own window. It is not a user-facing switch.

**The database side:**
- A new `users_profile_guard()` trigger, SECURITY INVOKER with `search_path ''`, in the 054 pattern.
- It refuses app-role changes to the six columns with 42501 and the fixed message "users profile columns are server-managed (INC-SEC-1)".
- Down migration: `migrations/rollback/055_app_user_access_tightening.sql`.
- Read-only check, printing no row data: `docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql`.

## Files (17 over main)
- **The migration and its files:** `migrations/055_app_user_access_tightening.sql`, `migrations/rollback/055_app_user_access_tightening.sql`, `docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql`.
- **Server:** `app/services/database_service.py` (C1), `app/services/feedback_service.py` (C2, C2b), `app/services/referral_service.py` (C3).
- **Docs and lint:** `CLAUDE.md` (the C3 flag row, one insertion), `.github/black-clean-paths.txt` (the new test file).
- **New tests:** `tests/test_inc_sec1_app_user_access.py`.
- **Moved pins, each a named ruling (R-2, Q7, A-1):**
  - `tests/test_feedback.py`: the ownership read is configured as owned.
  - `tests/test_m13_29_feedback_uuid.py`: inverted to "the service client is used and no user client is built".
  - `tests/test_s80_b1_feedback.py` and `tests/test_s81_sf1_surfaces_be.py` (p12 x7, r14): the ownership read finds no row; assertions unchanged.
  - `tests/test_inc_t1b_users_entitlement_guard.py::test_m02`: asserts that 055 and 054 exist and 053 is absent, never "highest".
  - `tests/test_s81_s22b_self_critique_retire.py`: the two migration-listing digests are re-pinned.
  - `tests/test_migration_037_security_definer_grants.py`: the live_db pin is inverted to expect 42501, and its comments re-worded.
- **Separate commit, E27 deflake (orchestrator request):** `tests/test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait`. `metadata.elapsed_seconds` is `round(elapsed, 2)`, so it can sit up to 0.005 s under the true time while the bind wait is whole milliseconds (seen: 0.42 against 0.421). The row now allows 0.006 s. Test only.

## Can a legitimate signed-in user lose the comparison link through C2b? (ORCH-SEC1-C, adversary 2, with evidence)
1. **Feedback on a fresh compare: KEPT.** The comparison id reaches the phone only after the awaited insert, on text POST (`text_routes.py:925-929`), text GET (`:1146-1150`) and the stream (`:1395-1412`). The image and URL routes return no id.
2. **A compare made signed-out, rated after sign-in: no link exists.** Signed-out compares save no row and return no id, so nothing is dropped.
3. **A History item: KEPT.** The History GET returns only the owner's row (`history_routes.py:147-154`), and the client sends that id (`api.ts:525`, `ResultsScreen.tsx:458`).
4. **A shared comparison opened by another signed-in user: no feedback card.** The History GET answers 404 for another user, and the referral landing has no feedback card. A hand-made request has its link DROPPED, which is right.
5. **Found by the adversary: an expired or refused sign-in.** With `ENABLE_STRICT_OPTIONAL_AUTH` OFF, such a user arrives as anonymous, and the link to their own comparison is dropped. Base would have kept it. The row is kept; this is rare and is counted by `FEEDBACK_COMPARISON_NOT_OWNED`. It is a stated limit (L14).

Every drop logs a fixed word, `FEEDBACK_COMPARISON_NOT_OWNED` or `FEEDBACK_OWNERSHIP_UNREAD`, with no id.

## Evidence
- **RED:** 56 rows fail at base afde168f, each on an AssertionError; 61 of 61 pass at the head.
- **Throwaway PostgreSQL 18.1 cluster, six runs:**
  - before 055, proofs P1-P6 and P8 fail (the gaps are real); after it, P0-P8 pass;
  - each rollback grid is byte-equal to its starting grid; 055 and the rollback are idempotent;
  - 055 works without 054, and 055 then 054 works.
- **Mutants:** 26 of 27 killed; MU07 is the comment-only control and stays green as required.
- **Related tests, at the 7f672cfe merge (e4cfe89e); the head is 84ebda79 after main 9bc13109:** the union comm set (246 files) shows no new failure. The 18 failed and 2 errors are all in the base record; they are hygiene rows on this box and the cold tiktoken cache.
- **One-process CI-order run:** at e4cfe89e it ran with the two latch files last, and its failed set is the same as base. After merging main 9bc13109 (#419) at 84ebda79 it was re-run (with `tests/test_inc_t0_conftest_breaker_reset.py` added): 18 failed, 13,845 passed, 2 errors, the identical failed set. The union comm set at the new head is the same 246 files.
- **Client fences:** 4 failed / 246 passed, the accepted `nativeBundle.w37` base failure.
- **Lint:** ruff (CI tier) clean, sqlfluff 0, and the new test file is black-clean. The pre-commit hook passed on every commit.
- **Two adversaries (FOCUS), both SOUND:**
  - ADV-1 on the SQL and the database, with its own cluster and fresh probes;
  - ADV-2 on the code paths and the deploy order.
  - Their minors are fixed in the notes or listed below.

## Deploy and apply states
| Server | 055 | State |
|---|---|---|
| before this PR | not applied | today, OK |
| this PR | not applied | OK; links dropped only in the cases above |
| this PR | applied | the target, OK |
| **any build without C2** | **applied** | **FORBIDDEN**: signed-in feedback is refused quietly, and only `save failed` is logged |

**Never run a server build without this PR's C2 commit while 055 is applied** (no rollback past it, no deploy of an older branch). Roll 055 back first.

## Stated limits
- L1: proven on a local 18.1 cluster, not on production 15. K11 STOPs below 140000, and the live P0-P8 are the proof.
- L2: unreadable JWT claims raise 22P02 without the fixed message (as in 054).
- L3, L4: a column added later, and `display_name`, `auth_provider`, `updated_at`, `preferences_completed`, `notifications_enabled`, `demographics_dismissed_count`, `demographics_dismissed_at`, stay writable by the row's owner until the R1-08 follow-up.
- L5: default privileges for new tables are unchanged (follow-up). P10 pins row security instead.
- L6: C2b keeps an anonymous `comparison_id` that names no row, or a row with no owner.
- L7: `rating_cache` and `bahrain_approved_drugs` stay outside migration control.
- L8: the catalog is the 2026-11-17 snapshot; the BEFORE grid is the truth, and a STOP sends it back.
- L10: role switching inside a DO block was measured on the cluster only; P0 checks it live.
- L11: the AST writer walk sees a user client only when it is built in the same function. Today every client-parameter helper receives a service client.
- L12: the inverted 037 live_db row is false until 055 is applied.
- L13: until the C3 flip, the same-device control never fires (the owner's choice).
- L14 (ADV-2 M-1): an expired or refused sign-in loses the link to the user's own comparison; the row is kept.
- L15 (ADV-1 M3): `resolve_referral_code` gets `search_path = public`, and its body names its table without a schema. After 055 only the service role and the owner may execute it. A schema-qualified body is a follow-up.
- L16 (ADV-1 M4): K10 lists only SECURITY DEFINER functions that write `users`. A wider row (every public definer function an app role may execute, expected empty AFTER) is a follow-up.
- P8(b), the invitee read on live data, is a cluster-only proof. The apply note offers one option on the owner's two tester-level accounts, which runs only if his yes names it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

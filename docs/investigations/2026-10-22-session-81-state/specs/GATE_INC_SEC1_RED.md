# GATE INC-SEC-1 RED (S96 orchestrator, 2026-11-17 about 11:55 AST): RED ACCEPTED, GREEN may start

Round: wf_2e171984-48f. Agents: AMEND (cached), plus three RED agents (stopped by box orders at 07:47 and 10:25). All ran on claude-opus-5-5, checked in each first transcript. Base afde168f.

## What I checked, against RULINGS R-1..R-19
- **RED file:** tests/test_inc_sec1_app_user_access.py, 52,164 B, sha 00b0d187..., ASCII, LF.
  - At base: 56 E rows fail, every one on an AssertionError, and the 5 PIN rows (X01, W03-W06) pass.
  - At the prototype: 61 of 61 pass.
- **Cluster (R-19):** PG 18.1 throwaway, six runs.
  - Before 055, P1-P6 and P8 fail, so the gaps are real.
  - After 055, P0-P8 pass. P4 is 14 of 14 with the R-10 UPDATEs, and P8 covers (a) and (b).
  - Each rollback grid is byte-equal to its starting grid.
  - Re-applying 055 is idempotent, and so is re-running the rollback.
  - 055 alone without 054 works, and 055 then 054 works.
  - The S38 role-filter mutant aborts the apply and leaves the grid unchanged.
  - The cluster is stopped: no postmaster.pid. The PostgreSQL service processes were not ours and were left alone.
- **Mutants:** 27 run. 26 are killed, each on an assertion. MU07, the comment-only SECURITY DEFINER control (R-11b), stays green as required.
- **Comm set:** 242 files, set sha 242c28ae.
  - Run in chunks: no new failure at the prototype; the 21 non-RED base failures are identical.
  - Run in one process in CI order on the prototype: 18 failed + 2 errors, all in the base set by node id. test_retro_w0_4_efg.py and test_s77_redis_offloop.py ran last and are green.
  - The RED file turns on neither latch switch, so it has no latch fixture.
- **Necessity run:** the base bytes of the moved test files fail at the prototype on exactly the spec-10 nodes (13 failed).
- **Client fences:** 4 failed / 246 passed at the prototype. They are the same 4 nativeBundle.w37 nodes (d5, k2, k4, k5) as at base, and this lane does not touch them.
- **Lint:**
  - ruff (CI tier) is clean, and sqlfluff shows 0 violations.
  - The 10 touched .py files already drift from black at base and are not on .github/black-clean-paths.txt.
- **Restore:** the hash-object compare matches, the lock is removed, and git status shows only the RED file.

## Rulings on the open questions
- **Q7 YES.** The three N-2 fixtures (test_s80_b1 b1_f5; test_s81_sf1_surfaces_be p12 x7 and r14) configure the ownership read as "no row", and every assertion stays unchanged. They are moved pins under the R-2 family, named in the PR body.
- **Q8 YES: C2 and C2b ship unflagged.**
  - C2 must be live before 055 applies. A switch on C2 would only add one more FORBIDDEN mix (switch OFF while 055 is applied means feedback is lost silently).
  - C2b changes the stored row only when the comparison id names a row that is not the caller's. That is an integrity fix with no response change.
  - Both are stated in the PR body and in the owner summary.
- **Q9:** the live P8(b) proof needs a second throwaway sign-in user as the referrer. It is put to the relay. By default P8(b) runs on the cluster only, as a stated limit, unless the owner's yes names that user.
- **A-1 ACCEPTED.** M02 asserts that 055 and 054 exist and 053 is absent, never "highest", so the next migration does not move this pin (the lesson from 054's test_m02).
- **test_gr1 shape ACCEPTED:** C2b lives in its own helper, _owned_comparison_id, and save_feedback keeps one except handler.
- **Walk N-3:** noted. No line moves at afde168f.
- **"No new user-facing switch":** ENABLE_REFERRAL_SAME_DEVICE_CHECK (C3) is server-side, default OFF and dark, so it is not user-facing. Its flip is the owner's, in a separate window (R-13, R-18).

## GREEN orders
1. **Bytes:** the prototype bytes (red/proto_bytes, cmp-equal to proto_src) are the starting point. Commit them on branch fix/inc-sec1-app-user-access, with the RED file as its own first commit.
2. **Merge main in:** first 7f672cfe; later the INC-H2/INC-T0 main once the relay sends its sha. Use a merge, never a rebase or force push.
   - Re-run the source-scanning pins and the CLAUDE.md readers after each merge (CLAUDE.md collides).
   - After INC-T0 lands, add no second shared latch reset.
3. **black:** format the RED file and add it to .github/black-clean-paths.txt, as I2b did. Touched files that drift at base stay off the list (stated limit).
4. **Notes, in plain words, PUBLIC-safe (no step-by-step misuse text):**
   - the owner summary <notes>/INC-SEC-1_OWNER_SUMMARY.md;
   - the apply note <notes>/INC-SEC-1_APPLY_NOTE.md, giving the order (054 / deploy C1-C2-C2b / 055), the K check before and after, the six search words, the STOP rule, the FORBIDDEN rollback, and Q9.
5. **E27 deflake:** its own small commit (TODO_E27_DEFLAKE.md), named in the PR body.
6. **Gates:**
   - the RED file;
   - the comm set in chunks;
   - one process in CI order, ending with test_retro_w0_4_efg.py and test_s77_redis_offloop.py;
   - the client fences;
   - the cluster re-run once on the committed SQL, if any SQL byte differs from proto_src.
7. **Then two adversaries (FOCUS):** ADV-1 SQL and the database (policies, grants, the trigger, the rollback, the check, PG 15); ADV-2 the code paths and flag mixes (C1/C2/C2b/C3, the walk, the deploy order).

# INC-SEC-1 RED REPORT (agents 1-3, Opus 5.5; resumed after the 07:47 and 10:25 box stops; finished 11:50 AST)

Unit: INC-SEC-1 DATABASE-ACCESS. Worktree sc-s96-sec1, branch fix/inc-sec1-app-user-access, base afde168f21703baba4bc4857eedf1042e5432196. Nothing touched a live database, Railway or Supabase. Synthetic ids only.

## RED file
- tests/test_inc_sec1_app_user_access.py: sha256 00b0d187bc161fa429884abb37a3c2c432ced2454df0c459ba946583463bcf56, 52164 bytes, ASCII, LF, ruff E9/F63/F7/F82 clean. 61 nodes (M01-M12, P01-P10, D01, K01-K03, L01 x3, X01, W01-W06, C01-C04 with params).

## Base run (RED at base)
- [pyt] tag=s96s-red-base1 start=2026-11-17 09:37:13 end=2026-11-17 09:37:23 elapsed=11s bound=600s status=FAIL rc=1
- 56 failed, 5 passed. Every failure is an AssertionError (56/56), no import or setup error. Passing = the PINs X01, W03, W04, W05, W06.

## Prototype (by the spec, in place under .qa-mutation.lock, base byte copies in red/base_copies)
- [pyt] tag=s96s-red-proto1 start=2026-11-17 09:59:33 end=2026-11-17 09:59:44 elapsed=11s bound=600s status=OK rc=0 -> 61 passed.
- Files: migrations/055 up + rollback, docs/investigations/2026-11-17-session-96-state/APPLY_055_CHECK.sql, app/services/database_service.py (C1), feedback_service.py (C2, C2b), referral_service.py (C3 dark switch ENABLE_REFERRAL_SAME_DEVICE_CHECK), CLAUDE.md (one flag entry on the Feature Flags line), the moved pins of spec 10 items 1-6.
- Moved pins (necessity run: the BASE bytes of the 7 moved test files against the prototype code), [pyt] tag=s96s-red-unmoved start=2026-11-17 10:12:05 elapsed=14s status=FAIL rc=1, 13 failed / 325 passed, exactly these nodes:
  - test_feedback.py::TestFeedbackService::test_save_feedback_success (fixture now configures the comparisons read as owned)
  - test_inc_t1b_users_entitlement_guard.py::test_m02_next_free_number (54 highest -> 54 and 52 in, 53 not in)
  - test_m13_29_feedback_uuid.py::test_save_feedback_uses_user_client_when_authenticated (inverted: service client, no user client)
  - test_s80_b1_feedback.py::test_b1_f5_four_field_body_record_identical (N-2: ownership read = no row; assertions unchanged)
  - test_s81_s22b_self_critique_retire.py::test_p3_the_table_and_its_migration_kept (listing digests re-pinned to the spec values)
  - test_s81_sf1_surfaces_be.py::test_p12_feedback_off_stored_row x7 params and ::test_r14_feedback_on_stored_row (N-2)
  - test_migration_037_security_definer_grants.py: only the live_db pin is inverted (never run by agents) and comments re-worded; its static rows stay green.
- Lint: ruff E9,F63,F7,F82 clean on the 10 touched .py + the RED file; py_compile clean; black --check: the 10 touched files already drift at base and at proto, none is on .github/black-clean-paths.txt (the CI black gate does not cover them); sqlfluff (repo .sqlfluff) 0 violations on up/down/check (also row L01 green).
- proto.diff: red/proto.diff (141879 B). proto bytes: red/proto_bytes/ (14 files, repo-relative, cmp-equal to red/proto_src).

## Comm set (union rule, minus the precommit-hook files)
- 242 files, digest sha256 over sorted names joined by LF plus a final LF = 242c28aeedbd14db6ed9d2003495dd04df1453f83223ac6a3136d15ff62299f2; list red/comm_set.txt, reasons red/comm_set_reasons.txt.
- Base record (no LC-6 record existed at afde168f): 10 chunks s96s-red-cb00..cb09, stored at harness/base_records/afde168f.../242c28ae....txt. 77 failed/error ids = the 56 RED rows + 21 others.
- Base non-RED failures (21): 2 ERROR test_prompt_truth (cold tiktoken, known), test_inc_i2a_picture_not_cut::test_e27_elapsed_includes_the_wait (rounding flake, TODO_E27_DEFLAKE.md), test_s81_d16 r10, d22c p1 x5, s07 r35, s10 r06, s16 r27 x5, s18b r2, s22 b02, s22 j01, s24 p83 and r92.
- Prototype: 10 chunks s96s-red-cp00..cp09: 21 failed/error ids, identical to the base 21; comm -13 base proto = EMPTY; the 56 RED rows fixed.
- CI-order one process (prototype, 242 files alphabetical, then test_retro_w0_4_efg.py and test_s77_redis_offloop.py LAST): [pyt] tag=s96s-red-ciorder start=2026-11-17 10:12:33 end=2026-11-17 10:24:05 elapsed=693s bound=1200s status=FAIL rc=1 -> 18 failed, 2 errors, 13423 passed. By node id every one of the 20 is in the base set (the 21 minus i2a test_e27, which passes here); the two latch files are green. The RED file turns on neither ENABLE_LLM_SPEND_BREAKER nor ENABLE_ANTHROPIC_VERDICT (grep), so no latch fixture was needed.
- Client fences (14 suites, 15 files) on the prototype: [jest] tag=s96s-red-fence_proto start=11:43:28 end=11:43:34 rc=1, 4 failed / 246 passed; the 4 = nativeBundle.w37 d5, k2, k4, k5, identical to base ([jest] tag=s96s-red-fence_base start=09:58:47 end=09:58:54 rc=1). No new client failure. (A first fence_proto at 10:25 was cut by the box stop; kept as fence_proto.interrupted_1025.out, not counted.)

## Cluster (R-19): PostgreSQL 18.1, initdb in red/pgdata, 127.0.0.1:55497, trust; on the proto_src SQL (bytes equal to the prototype)
- run 1 base + 054: rc 0; proofs before 055: P0 P7 PASS, P1-P6 and P8 FAIL (the gaps are real).
- run 2 + 055: rc 0, P0-P8 PASS (P4 14/14 with the R-10 UPDATEs; P8 a and b).
- run 3 rollback: grid g3 == g1 byte-equal; rollback re-run == g1; rollback 055 + rollback 054 == g0.
- run 4 055 re-apply and re-run: grid == g2 (idempotent).
- run 5 055 without 054: rc 0, P0-P8 PASS, rollback grid == h0.
- run 6 055 then 054: rc 0, grid == g2, P0-P8 PASS.
- cluster mutant S38 without the role filter: apply aborts with '055 assert: an app-role policy keeps an open branch', grid unchanged.
- Stopped with pg_ctl stop -m fast at 07:46 (pg.log: database system is shut down); now pg_ctl status = no server running, no postmaster.pid, nothing listens on 55497. The running postgres.exe processes are the Windows service postgresql-x64-18, not this cluster.

## Mutants (prototype, RED file alone each; tags s96s-red-mu01..mu27, status from harness/pyt_ledger.jsonl)
- 26 KILLED on AssertionError, 1 control GREEN as required (MU07 definer only in a comment). Killing rows: MU01 p01, MU02 p02, MU03 p03, MU04 p04, MU05 p05, MU06 m05, MU08 m07, MU09 m08, MU10 m09, MU11 m10, MU12-14 d01, MU15 k02, MU16 k03, MU17 c01 + w01, MU18 c02 x2 + w01, MU19 c02 + gr1, MU20 c03 cases 5-8, MU21 c03 cases 4 and 8, MU22 c04_a x4, MU23 c04_c, MU24 m12, MU25 p08, MU26 p09, MU27 p10. Every restore sha-equal.

## Restore
- protoctl.py restore: proto bytes saved first; 11/11 existing files git hash-object == HEAD blob; the 3 new SQL files and the session-96 docs folder removed; .qa-mutation.lock removed.
- git status --short: ?? tests/test_inc_sec1_app_user_access.py (only).

## Deviations
- The spec mutant list holds 27 items though it says 28; 27 were run.
- Per-mutant [pyt] lines were not kept by the driver; the status of each comes from the harness ledger (same runner).
- CI-order run is on the prototype; compared by node id with the base chunk record.
- i2a test_e27 is a base flake (fails in both chunk records, passes in CI order).
- The work spans three agents (box stops 07:47 and 10:25); finished logs were reused, not re-run, as ordered.

## Open questions for the gate
- Q7 N-2 fixtures moved (three files): needs the gate's word.
- Q8 C2 / C2b unflagged: confirm.
- Q9 the second throwaway user for live P8(b).
- A-1 M02 asserts 055 and 054 exist, 053 absent (not 'highest'): the gate may veto.

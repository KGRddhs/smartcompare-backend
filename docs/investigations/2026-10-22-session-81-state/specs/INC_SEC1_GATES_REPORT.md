# INC-SEC-1 GATES REPORT (Opus 5.5, 2026-11-17 12:08-12:37 AST): GREEN steps 5, 6, 9 at the merged head

W = C:/Users/SynAckITPC/Documents/AI/sc-s96-sec1. HEAD e4cfe89e9601857161a7f7fdb91f4e49a4e3aeb8, parents 89d94d25 + 7f672cfe, git status --short empty before and after. No commit, no edit in W, no live system touched, no cluster started (step 7 not in scope).

## (a) RED file at head
- tests/test_inc_sec1_app_user_access.py: 61 passed.
- [pyt] tag=s96s-gates-red start=2026-11-17 12:09:47 end=2026-11-17 12:09:59 elapsed=12s bound=600s status=OK rc=0
- [hermeticity] sentinel checked 61 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)

## (b) Comm set by the union rule at the merged head
- red/comm_set.py rule re-run on the head tree (gates/comm_set_head.py, OUT moved to the gates folder): 246 files, set sha256 9993e9ba92bdd4612eb6a61833e9cd0bf3f50889d46d72c9c2837273f89e8d82; removed 0.
- Added 4 (main since afde168f): test_inc_p2_seam.py, test_inc_t1_tester_tier.py, test_inc_u1_gate_rows.py, test_inc_u1_link_result.py (reasons: p2_seam src_reader; t1_tester_tier mod:referral_service; u1_gate_rows src_reader; u1_link_result mod:database_service). The other 3 files main added (test_inc_p2_fix1, test_inc_p2_price_not_lost, test_inc_u1_fix1) match no union class.
- Head: 10 chunks of at most 25, bound 1200: chunks 00-03, 05, 09 status=OK; 04, 06, 07, 08 status=FAIL rc=1 (12:10:23-12:22:45). Failed set = 18 FAILED + 2 ERROR (test_prompt_truth cold tiktoken), every node in the cached afde168f record (comm -13 EMPTY). The base record's flaky test_inc_i2a::test_e27 passes at head (deflake 89d94d25). None of the 4 added files fails at head.
- Base for the added files: origin/main 7f672cfe in a DETACHED scratch worktree gates/base7f (python only): [pyt] tag=s96s-gates-base7f00 start=2026-11-17 12:22:46 end=2026-11-17 12:22:59 elapsed=13s bound=1200s status=OK rc=0, 418 passed, 0 failed. Cached as harness/base_records/7f672cfe.../56c0d7c3....txt. Worktree removed (git worktree remove --force; git worktree list shows no base7f).
- new_failures: NONE.

## (c) One process in CI order
- 246 files alphabetical, test_retro_w0_4_efg.py and test_s77_redis_offloop.py LAST (gates/ciorder.txt).
- [pyt] tag=s96s-gates-ciorder start=2026-11-17 12:23:00 end=2026-11-17 12:34:41 elapsed=701s bound=1500s status=FAIL rc=1
- 18 failed, 13841 passed, 35 skipped, 35 deselected, 36 xfailed, 2 errors; [hermeticity] sentinel checked 13908 test(s); [netguard] blocked 333 attempt(s) from 111 node(s)
- Failed set byte-identical to red/ciorder_failed.txt (the RED-round CI-order run) and inside the base set; the two latch files have no failing node.

## (d) Client fences (red/fencedrive.sh fence_merged)
- jest 29.7.0, babel core present. [jest] tag=s96s-red-fence_merged start=12:34:55 end=12:35:00 rc=1
- Test Suites: 1 failed, 14 passed, 15 total; Tests: 4 failed, 246 passed, 250 total. FAIL __tests__/config/nativeBundle.w37.test.ts only: d5, k2, k4, k5 = the accepted base failure.

## (e) MAIN_SHA.txt
- Absent at 12:08; at 12:37 it reads 9bc13109769d6ca4010e3ead4c62d597a577457f (#419 INC-H2 with INC-T0, merged 12:07:55 AST). origin/main in W = 9bc13109. NOT an ancestor of HEAD e4cfe89e. NOT merged (as ordered). Per ORCH_RULINGS METER ORDER, after that merge only the CI-order one-process run and the source-scanning pins need a re-run; tests/conftest.py then resets both latches (add no second shared reset).

## Deviations
- Comm-set head ran by chunk in W; base for the 242 RED-round members = the cached afde168f record (LC-6), base for the 4 added members = 7f672cfe measured once.
- The fence driver writes its outputs into red/ (fence_merged.out, fence_merged.waitfree) as the script is built.

## Files (gates folder)
red.log/.stdout, comm_set.txt, comm_set_reasons.txt, added.txt, comm_head/, comm_base7f/, head_failed.txt, base_afde_failed.txt, ciorder.txt, ciorder.log/.stdout, ciorder_failed.txt, run1.sh, commdrive.sh, gatesmaster.sh, comm_set_head.py, notes.md.

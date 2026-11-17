# INC-P2 FIX ROUND 1 - RE-VERIFIER REPORT, lens CORRECTNESS (Claude Opus 5.5, 2026-11-17)

VERDICT: NOT_READY (0 blocking, 1 major, 6 minor). Every code measurement of the fix round below is sound. The one MAJOR is a documentation-against-bytes defect in the FLIP NOTE canary filter; it is a docs-only fix (LC-2).

Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-p2, branch fix/inc-p2-price-not-lost, HEAD f0efe65dfdd47f459b6376527a6d2856b245fdcd, verified at the start and at the end. `git merge-base --is-ancestor 5cd93c6a HEAD` is true. `git status --short` was empty at the start and at the end, and the worktree was never edited.
Every pytest ran in my detached scratch worktree C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-P2_fix1_adv at f0efe65d. Its app files and CLAUDE.md were sha-equal to the fix report's working-copy values before the first mutant and after the last restore (`sha256sum -c` OK). It was removed with `git worktree remove --force`, and `git worktree list` no longer shows it.
The jest fences ran read-only in the real worktree, the only checkout with the node_modules junction. Merged, NOT yet proven: nothing here is phone proof.

## 0. RED files re-hashed (committed blobs at HEAD, start and end)
- tests/test_inc_p2_fix1.py b148541e397451a5aed7fb0f01f73a70542ac8b42429e17087bbe827543f664e (0 bytes > 127, LF, no 8-digit run, no sk- / eyJ shape)
- tests/test_inc_p2_price_not_lost.py 43d309db521ca62b7df79450e937a0eb44f54c839e8843a4514960dd0bae0dee (unchanged)
- tests/test_inc_p2_seam.py 07d72b74a83b7a8d104354ac92dd6fe60b756cbae80219155bf28654e2b69b86 (unchanged)
In sc-inc-p2 the working copies of the two frozen files are CRLF by core.autocrlf (sha 6c2e73f7... / 8833409d...); `git diff` is empty.

## 1. Rebase hunks read against both parents
- App files: the sorted +/- line multiset of `git diff fd983471 8abc5115` equals that of `git diff 5cd93c6a 0c66ca4e` for price_service, response_builder, SCS and text_routes (sha12 ec6c5409 / 5d018d29 / 6009ae6e / f7cc273f on each side). The branch does not change image_service.py, image_relevance.py or .github/black-clean-paths.txt.
- A -U0 hunk overlap test compared `git diff 5cd93c6a HEAD` (old side) with #413's `git diff 2e7a1229 5cd93c6a` (new side). SCS: 24 branch hunks against 18 #413 hunks, with no overlap or adjacency. No other app file is shared. The only SCS lines removed (2 lines, the `observed` converted filter) are GREEN's own edit: present at fd983471 and removed the same way in 8abc5115.
- CLAUDE.md H1 (:341): main's line becomes HEAD's line by ONE pure insertion of 152 bytes at offset 9227 (GREEN's offset 8683 + #413's 544-byte insertion). Nothing of #413 is removed. H2: the INC-P2 block is a pure insertion after #413's INC-I2a block and before `## Tests`.
- No #413 line changed anywhere, so there is no MAJOR here.

## 2. Runs (gate.py, pinned venv, one pytest at a time)
- Unit files ON (ENABLE_PRICE_NOT_LOST=true in the runner env only): 721 passed. [hermeticity] sentinel checked 721. [netguard] blocked 13 attempts from 13 nodes (only the neutralized.supabase.invalid sentinel).
  [pyt] tag=inc-p2-rv-unit-on start=2026-11-17 06:03:36 end=2026-11-17 06:03:50 elapsed=14s bound=600s status=OK rc=0
- Unit files OFF: 721 passed, with the same hermeticity and netguard lines.
  [pyt] tag=inc-p2-rv-unit-off start=2026-11-17 06:04:23 end=2026-11-17 06:04:37 elapsed=14s bound=600s status=OK rc=0
- RED check: the five app files and text_routes at 0c66ca4e were laid into the scratch tree as byte copies, then restored (6/6 sha OK). On tests/test_inc_p2_fix1.py: 63 failed, 163 passed. Every failure is an AssertionError (62 top-level + 1, 3 nested; no other exception class). This equals the fix report's 63 / 163.
  [pyt] tag=inc-p2-rv-red-at-0c66 start=2026-11-17 06:23:49 end=2026-11-17 06:23:57 elapsed=7s bound=600s status=FAIL rc=1
- F2 base PIN: the same files at 5cd93c6a, with -k "f2 or f4d". f2[off], f2[on], f2b and f4d[44] are all green at main. The 5 failures are not F2 rows: they are walk nodes that my -k caught through their f2_travel param ids (f1e x2, f4e x3). These are flag-ON rows that need branch code; 2 of them raise AttributeError from absent branch symbols. Restores 6/6 sha OK.
  [pyt] tag=inc-p2-rv-f2-at-5cd start=2026-11-17 06:24:04 end=2026-11-17 06:24:09 elapsed=5s bound=600s status=FAIL rc=1
- CI-order set, ONE alphabetical process, the fix round's 36 files: 2568 passed, 0 failed. E27 passed this time; the flake in the fix report did not recur.
  [gate] tag=inc-p2-rv-ci waited=706s (another lane is queued, another lane's run is live)
  [pyt] tag=inc-p2-rv-ci start=2026-11-17 06:16:24 end=2026-11-17 06:18:22 elapsed=118s bound=1200s status=OK rc=0
- Comm set, chunk placement: the 10 readers of home_routes / profile_routes are all in the 761 list, in chunks 01 07 09 10 17 21 23 30. tests/test_inc_i2a_picture_not_cut.py is in chunk 10. The SCS importers (224 files by git grep) reach ALL 31 chunks, so I re-ran all 31 of the fix round's chunks at f0efe65d, with the flag unset.
- Comm set, result: 30,951 passed, 26 failed + 2 errors = 28 ids, 55 skipped; 0 TIMEOUT, 0 BUSY. The 28 ids EQUAL the base record C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-P2/red/b_base_comm_failed.txt (CR-normalised). branch-only-NEW is EMPTY and base-only is EMPTY. test_s80_b1 (GREEN Q2, chunk 21) is green.
- Comm set, membership: my own transitive import closure over tests/ (the edited modules + app.main + eval_runner) gives 535 test files, and none is missing from the 761 list. Every eng MAJ-3 member is present. test_bias_matrix_probe and test_migration_042 import none of the edited modules.
  [pyt] tag=inc-p2-rv-c01 start=2026-11-17 06:24:16 end=2026-11-17 06:24:49 elapsed=33s bound=1200s status=OK rc=0
  [gate] tag=inc-p2-rv-c02 waited=3891s (another lane is queued)
  [pyt] tag=inc-p2-rv-c02 start=2026-11-17 07:46:09 end=2026-11-17 07:46:37 elapsed=28s bound=1200s status=FAIL rc=1
  [pyt] tag=inc-p2-rv-c03 start=2026-11-17 07:46:44 end=2026-11-17 07:47:10 elapsed=26s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c04 start=2026-11-17 07:47:17 end=2026-11-17 07:48:09 elapsed=53s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c05 start=2026-11-17 07:48:16 end=2026-11-17 07:48:44 elapsed=28s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c06 start=2026-11-17 07:48:51 end=2026-11-17 07:49:05 elapsed=14s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c07 start=2026-11-17 06:24:56 end=2026-11-17 06:25:15 elapsed=20s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c08 start=2026-11-17 07:49:12 end=2026-11-17 07:49:43 elapsed=32s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c09 start=2026-11-17 06:25:22 end=2026-11-17 06:26:33 elapsed=71s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c10 start=2026-11-17 06:26:40 end=2026-11-17 06:27:53 elapsed=73s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c11 start=2026-11-17 07:49:50 end=2026-11-17 07:50:18 elapsed=29s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c12 start=2026-11-17 07:50:25 end=2026-11-17 07:51:05 elapsed=40s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c13 start=2026-11-17 07:51:11 end=2026-11-17 07:51:24 elapsed=13s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c14 start=2026-11-17 07:51:31 end=2026-11-17 07:51:51 elapsed=21s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c15 start=2026-11-17 07:51:58 end=2026-11-17 07:52:25 elapsed=27s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c16 start=2026-11-17 07:52:32 end=2026-11-17 07:53:09 elapsed=37s bound=1200s status=FAIL rc=1
  [gate] tag=inc-p2-rv-c17 waited=204s (another lane is queued, another lane's run is live)
  [pyt] tag=inc-p2-rv-c17 start=2026-11-17 06:31:18 end=2026-11-17 06:31:40 elapsed=22s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c18 start=2026-11-17 07:53:16 end=2026-11-17 07:53:35 elapsed=19s bound=1200s status=FAIL rc=1
  [pyt] tag=inc-p2-rv-c19 start=2026-11-17 07:53:41 end=2026-11-17 07:55:36 elapsed=115s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c20 start=2026-11-17 07:55:43 end=2026-11-17 07:57:11 elapsed=88s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c21 start=2026-11-17 06:31:47 end=2026-11-17 06:33:32 elapsed=106s bound=1200s status=FAIL rc=1
  [pyt] tag=inc-p2-rv-c22 start=2026-11-17 07:57:18 end=2026-11-17 07:59:00 elapsed=102s bound=1200s status=FAIL rc=1
  [pyt] tag=inc-p2-rv-c23 start=2026-11-17 06:33:39 end=2026-11-17 06:34:45 elapsed=66s bound=1200s status=FAIL rc=1
  [pyt] tag=inc-p2-rv-c24 start=2026-11-17 07:59:06 end=2026-11-17 07:59:45 elapsed=39s bound=1200s status=FAIL rc=1
  [pyt] tag=inc-p2-rv-c25 start=2026-11-17 07:59:52 end=2026-11-17 08:00:52 elapsed=61s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c26 start=2026-11-17 08:00:59 end=2026-11-17 08:01:20 elapsed=21s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c27 start=2026-11-17 08:01:27 end=2026-11-17 08:02:09 elapsed=43s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c28 start=2026-11-17 08:02:16 end=2026-11-17 08:02:52 elapsed=36s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c29 start=2026-11-17 08:02:59 end=2026-11-17 08:03:27 elapsed=28s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c30 start=2026-11-17 06:34:52 end=2026-11-17 06:35:29 elapsed=36s bound=1200s status=OK rc=0
  [pyt] tag=inc-p2-rv-c31 start=2026-11-17 08:03:34 end=2026-11-17 08:03:41 elapsed=7s bound=1200s status=OK rc=0
- The four pre-commit hook files ALONE: -k "not dash" 167 passed / 160 deselected; -k dash 157 passed, 3 skipped / 167 deselected.
  [pyt] tag=inc-p2-rv-hook1 start=2026-11-17 06:35:36 end=2026-11-17 06:38:37 elapsed=181s bound=1800s status=OK rc=0
  [pyt] tag=inc-p2-rv-hook2 start=2026-11-17 06:38:43 end=2026-11-17 06:41:17 elapsed=154s bound=1800s status=OK rc=0
- The fourteen client fences: 15 suites by path from C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-P2_fix1/fence_list.txt, jest 29.7.0, with @babel/core and .bin/jest present. The H5 probe was empty and gate.py --wait-only ran first ([gate] tag=wait-only waited=4598s). Result: 246 passed, 4 failed = the four accepted config/nativeBundle.w37 drift nodes (d5, k2, k4, k5).
  [jest] tag=inc-p2-rv-fences start=2026-11-17 07:51:32 end=2026-11-17 07:51:37 rc=1
- Lint and hygiene: ruff --select E9,F63,F7,F82 --no-cache on the five app files and the fix-round file: All checks passed. py_compile OK. No edited file is listed in .github/black-clean-paths.txt. The app / CLAUDE.md diff of the fix commit adds 0 bytes > 127.

## 3. Mutants
Method: 15 mutants, written as my own expressions rather than the fix agent's strings. Each is a byte copy with one exact edit that matches once (a dry run counted 1 for each). Each ran the three unit files with the flag ON in the runner env, --maxfail=6, then a restore and a sha256 compare. The mutation lock was created and removed.
Results are in C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-P2_fix1_rv/mutants_result.jsonl and the logs in mut_<ID>.log. 15 KILLED / 0 SURVIVED. Every kill is an AssertionError, and every restore is sha-verified:
- RV-F1a (app/services/response_builder.py): KILLED by test_f1a_wire_fault_body_and_alias[cap1]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f1a start=2026-11-17 06:18:34 end=2026-11-17 06:18:39 elapsed=5s bound=600s status=FAIL rc=1
- RV-F1b (app/services/response_builder.py): KILLED by test_f1a_wire_fault_body_and_alias[cap1]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f1b start=2026-11-17 06:18:46 end=2026-11-17 06:18:51 elapsed=5s bound=600s status=FAIL rc=1
- RV-F2 (app/services/structured_comparison_service.py): KILLED by test_f2_l1_hit_with_a_non_str_variant[off]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f2 start=2026-11-17 06:18:58 end=2026-11-17 06:19:12 elapsed=14s bound=600s status=FAIL rc=1
- RV-F2b (app/services/price_service.py): KILLED by test_f2b_trace_before_list_outside_the_guard; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f2b start=2026-11-17 06:19:19 end=2026-11-17 06:19:33 elapsed=15s bound=600s status=FAIL rc=1
- RV-F3u (app/services/structured_comparison_service.py): KILLED by test_f3a_partner_size_never_written_under_a_bare_key[cap1]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f3u start=2026-11-17 06:19:40 end=2026-11-17 06:19:47 elapsed=6s bound=600s status=FAIL rc=1
- RV-F3t (app/services/structured_comparison_service.py): KILLED by test_f3f_typed_size_must_be_in_the_key_text; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f3t start=2026-11-17 06:19:53 end=2026-11-17 06:20:08 elapsed=14s bound=600s status=FAIL rc=1
- RV-F4m (app/api/home_routes.py): KILLED by test_f4h_every_mode_but_same_size_is_skipped[unknown-True]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f4m start=2026-11-17 06:20:30 end=2026-11-17 06:20:45 elapsed=14s bound=600s status=FAIL rc=1
- RV-F4p (app/api/profile_routes.py): KILLED by test_f4a_cross_size_rows_skipped[t3_01-cap1]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f4p start=2026-11-17 06:20:52 end=2026-11-17 06:20:59 elapsed=7s bound=600s status=FAIL rc=1
- RV-F7a (app/services/price_service.py): KILLED by test_f7a_outcome_reads_the_notes_under_their_write_key[variant_in_name]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f7a start=2026-11-17 06:21:05 end=2026-11-17 06:21:20 elapsed=14s bound=600s status=FAIL rc=1
- RV-F7b (app/services/price_service.py): KILLED by test_f7b_floor_pend_logs_reconcile_floor[cap1]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-f7b start=2026-11-17 06:21:27 end=2026-11-17 06:21:41 elapsed=14s bound=600s status=FAIL rc=1
- RV-X01 (app/services/price_service.py): KILLED by test_f6_x01_floor_boundary[29-False]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-x01 start=2026-11-17 06:21:48 end=2026-11-17 06:22:02 elapsed=14s bound=600s status=FAIL rc=1
- RV-X04 (app/services/price_service.py): KILLED by test_f6_x04_no_stamp_without_url; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-x04 start=2026-11-17 06:22:09 end=2026-11-17 06:22:23 elapsed=14s bound=600s status=FAIL rc=1
- RV-X05 (app/services/price_service.py): KILLED by test_f6_x05_restore_region_currency_guard[guard_on]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-x05 start=2026-11-17 06:22:30 end=2026-11-17 06:22:44 elapsed=14s bound=600s status=FAIL rc=1
- RV-E06 (app/services/structured_comparison_service.py): KILLED by test_f6_e06_flag_off_token_logs_cap_none; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-e06 start=2026-11-17 06:23:07 end=2026-11-17 06:23:21 elapsed=14s bound=600s status=FAIL rc=1
- RV-E12 (app/services/response_builder.py): KILLED by test_f6_e12_alias_mirrors_a_restored_side[ysl_lveb]; restore sha OK=True.
  [pyt] tag=inc-p2-rv-mut-e12 start=2026-11-17 06:23:28 end=2026-11-17 06:23:42 elapsed=14s bound=600s status=FAIL rc=1
What each mutant does:
- F1a strips only `_p2_shown*` keys, so _p2_open stays.
- F1b scans only product 0 for private keys.
- F2 computes the trace key outside the try.
- F2b narrows the except to KeyError.
- F3u lets an untyped side write any known size.
- F3t accepts a key text that has no size.
- F4m skips only mode=different_sizes.
- F4p passes metadata (the wrong argument) to the profile skip.
- F7a drops the variant-in-name key form.
- F7b misspells the floor reason.
- X01 lowers the floor from 30 to 26.
- X04 stamps on the retailer instead of the url.
- X05 lets USD pass the region guard.
- E06 binds the capability while ignoring the flag.
- E12 mirrors the stale best_price.

## 4. Findings

### MAJOR-1 (docs against bytes): the canary filter `cap=0` in the FLIP NOTE and in CLAUDE.md matches no line the code writes
- Bytes: response_builder `_p2_price_outcome` prints `cap=%s`, filled with `"price_size" if _ps.price_size_cap() else "none"`. The format string is at :212-215 and the argument at :227. P2R-21 defines `cap=price_size|none`, row f6_e06 asserts cap == "none", and the PR body's own proof table says `cap=price_size` / `cap=none`.
- Docs: the PR body FLIP NOTE says "Canary filters (plain words, never brackets): `PRICE_OUTCOME`, then `cap=0`, ...". The CLAUDE.md owner-steps bullet (:750) says "filter the Railway log on the plain words `PRICE_OUTCOME`, then `cap=0`, ...". The wording comes from ruling D2 (and GATE line 34), which named "cap=0", and the fix agent followed the ruling.
- Effect: during the flip window the relay's cap0 filter returns zero lines, whatever the traffic. That reads as "no old-app phone saw a held side", when in fact every store / OTA phone is cap0. This is a wrong measurement inside the production canary procedure.
- Fix (docs only, LC-2, no re-verifier needed): write `cap=none` (and `cap=price_size` for cap1) in the PR body flip note and in the CLAUDE.md bullet. The orchestrator amends D2 and GATE to match.

### Minors (stated limits by LC-4 unless the orchestrator rules otherwise)
- m1 The proof-table row "Ted Baker M 30ml" vs "Dior Sauvage EDP" (the mixed pair):
  - Its cap1 / cap0 cells assume there is no 30 ml Dior listing among the candidates.
  - Sauvage 30 ml is a common listing. My mutant RV-F3u's log shows the fixture world re-selecting it: `price:75da9259ce6d` = "Sauvage EDP 30ml".
  - When such a listing exists, V2 re-selects the untyped Dior to the partner's 30 ml. Both sides are then shown at 30 ml on EVERY app, as same_size, with no note and `reconcile=reselect`. F3 writes nothing, and the log carries `PRICE_CACHE_SKIP reason=size_basis site=reselect`.
  - The row should name this outcome and its backing line; that line is also the phone-side proof of F3.
- m2 The rollback sentence (PR body SL5, FLIP NOTE, CLAUDE.md) has two gaps:
  - "which the flag-OFF path reads as a genuine price for that key" is imprecise: a converted entry (24 h) is read as a converted price, not a genuine one.
  - The DV1 effect (flag OFF then shows a pair it used to pend, at 100 ml) is stated in SL5 only, not in the flip note or CLAUDE.md.
- m3 DV1 departs from the binding F3c wording ("every flag-OFF body equals its no-prior-write base body"). The departure follows from F3 (b) itself and is measured, but it needs the orchestrator's ruling.
- m4 The response_builder comment above `_p2_wire_prices` (:1917-1918) still says "None when OFF or on any fault, so the body is the flag-OFF body". After F1 the keys no longer leak. But on a wire fault, a rule-4 projection pair (A19 / A30) ships both sides pending where flag OFF shows both, so rule 4 does not hold on that fault path. The path is an internal exception only and logs one WARNING `INC-P2 p2 wire skipped`. Comment fix or stated limit.
- m5 The comm-set base record is the b0ad2603 record: two merges before 5cd93c6a, and the 741-file set rather than a 5cd93c6a / 761-file record (LC-6 recomputes on a changed sha or set). No regression is hidden: the HEAD set equals the base set exactly, and none of the 28 ids is in a #412 / #413 file. My skip count (55) differs from the fix report's (91); this is a count difference only.
- m6 f4f drives the marker only through the GET route's persist. The POST persists (:926 / :936 / :947) and the stream persists (:1546 / :1554) hand over the same `result` / complete body; I read these, but no row drives them.

## 5. Closure of the previous round's findings
- corr MAJOR-1 = eng MAJ-2 (private keys on a wire fault): CLOSED by F1.
  - f1a-f1e are RED at 0c66ca4e and green at HEAD. RV-F1a and RV-F1b were killed.
  - `_kb_ingest_tail.build_job` copies named fields only, so it carries no `_p2` key. The price L1 write strips `_` keys.
- corr MAJOR-2 (an unflagged evaluation outside its guard): CLOSED by F2.
  - f2 was re-measured green at 5cd93c6a and is RED at 0c66ca4e. RV-F2 and RV-F2b were killed.
  - My audit of every unflagged line the branch adds found no other argument evaluated outside a guard. text_routes `client_price_size` reads the flag first and is guarded. price_miss_note / price_trace_* are guarded inside and take local or id() arguments. The `_p2_trace_reconcile` call sits in a try. `_guard_rejected_diag` is bound at RB :1796.
- corr MAJOR-3 (a partner-dictated size cached): CLOSED by F3 (a)/(b); rows f3a-f3f; RV-F3u and RV-F3t killed. The rollback docs are corrected, apart from the wording in m2 above.
- eng MAJ-1 (savings added across sizes): CLOSED by the F4 unflagged extractors; rows f4a-f4h; RV-F4m and RV-F4p killed. The 036 RPC is the FLIP PRECONDITION, stated in the flip note, in CLAUDE.md and in the D7 table.
- eng MAJ-3 (comm set members): CLOSED. The list holds 761 files, my closure check finds none missing, and the re-run of 31/31 chunks has an empty branch-only-NEW.
- corr m1 / eng m1 (proof table, P2R-37 verbatim): CLOSED. The table has cap1 / cap0 columns and the P2R-37 sentence appears verbatim once; m1 above is a new gap.
- corr m2: stated (the corr m2 bullet and the D7 row).
- corr m3 / eng m2: CLOSED (the D3 wording in the PR body and CLAUDE.md).
- corr m4: CLOSED (F7a; RV-F7a killed). corr m5: CLOSED (F7b; RV-F7b killed).
- corr m6 / eng m3 (X01, X04 = E09, X05, E06, E12): CLOSED by the killing rows; my five re-expressed mutants were killed.
- corr m7 = eng m7: the orchestrator's (the gate byte count). corr m8: stated.
- eng m4 / m5 / m6 / m8: stated in the PR body; D6 names the five missing rules.
- GREEN Q2: re-checked, green. GREEN Q3 / Q4: stated.

## 6. PR body and CLAUDE.md checked against the bytes
- The PR body is 24,570 B (< 25,600) and LF. Its only non-ASCII is the robot line (4 bytes). The title is unchanged, as D4 orders.
- Sentences that hold against the bytes:
  - the F1 rows list;
  - F2 green at 5cd93c6a;
  - F3 (a)/(b) and its resolver reachability (f3d res0 / res1 green);
  - the F4 skip rule: unflagged and keyed on the stamp;
  - F7: the ledger is read under every write key, and a floor pend logs `floor`;
  - "OFF: ... byte identical": the F1 strip is a no-op with the flag OFF (f1f asserts identity), and F4 reads a stamp that a flag-OFF body never carries (f4d green);
  - the gate counts: 63 / 163 RED, 721 / 721, the 36-file CI set, 761 files, 28 = 28 ids, hooks 167 / 157 + 3 skipped, fences 246 + 4;
  - the TTLs (the price_cache_ttl docstring: 7 d genuine / 24 h converted);
  - the marker modes same_size | different_sizes | unknown (pair_price_sizes);
  - the D7 table rows as ruled;
  - the P2R-37 sentence, verbatim.
- Not true against the bytes: the `cap=0` filter (MAJOR-1).
- Imprecise: the rollback "genuine" wording (m2) and the mixed-pair proof row (m1).

## 7. NOT MEASURED
- None of the gates the rulings order.
- Not re-run: the fix agent's E27 base comparison (E27 passed in my CI-order run).

Files under C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-P2_fix1_rv/: chain1.sh, chain2.sh, jest.sh, jprobe.ps1, mutants_rv.py, mutdrive_rv.py, revert_run.py, mutants_result.jsonl, mutdrive.out, mut_*.log, unit_on/off.log, ci.log, c01..c31.log, hook1/2.log, jest_fences.log, comm_pyt_lines.txt, sha_start.txt, inc-p2-rv-red-at-0c66.log, inc-p2-rv-f2-at-5cd.log.

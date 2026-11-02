# S81-G1 PRICE-PIPELINE: REBASE ROUND report (onto origin/main eaccd550, the folded post-adversary items)

- Unit: S81-G1 PRICE-PIPELINE (D08 JSONLD-WIDEN: ENABLE_IMAGE_PIPELINE_V2 + ENABLE_JSONLD_RATING; S81-23 BYPASS-RETIRE: ENABLE_SCRAPEDO_SUPER), the rebase round. Agent: REBASE-AND-GATES, Opus 5.5 (claude-opus-5-5). Window 2026-11-02 15:06 - 16:04 AST. Written through the shell (report_build.py over figures.json / extra.json / the logs), not the Write tool.
- Binding: RULINGS_REBASE_S81_G1 (RB-G1-1..6), then RULINGS_FIX1_S81_G1 (F1-G1-1..6, GR-G1-1..8), GATE_S81_G1, RULINGS_S81_G1.
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g1, branch feature/s81-g1-price-pipeline. HEAD before 6da5aa6819728b27242df804a58d0ec305b0db6b (git status empty, verified first). Base fetched: origin/main = eaccd550a0ba747b7fc56219cfaef15a83dcb50e.
- HEAD after: dae4c5357a3ac0766570183cfe00533bd64a85a2 (two commits on eaccd550: f67ccca30daae8de09a74a0c42fe7d63a12ebe1f = the GREEN commit replayed; dae4c5357a3ac0766570183cfe00533bd64a85a2 = the round commit).
- VERDICT: READY_FOR_PR: every gate the rulings name measured green or equal to base (unit 220 / 220 in five states, the corpus figure equal, comm -13 EMPTY, fences and the full jest suite green bar the four accepted drift nodes); two commits, both through the hook

## 1. Rebase (RB-G1-1)
- git fetch origin main: origin/main = eaccd550a0ba747b7fc56219cfaef15a83dcb50e (#379 S81-09); merge-base with 6da5aa68 = 6c14ac95.
- Re-measured before the rebase: `git merge-tree --write-tree --name-only origin/main HEAD` -> CONFLICT (content) in CLAUDE.md ONLY (no other conflicted file: no STOP).
- `git rebase origin/main`: 1 commit to replay (6da5aa68), stopped on CLAUDE.md; resolved (section 2); `git add CLAUDE.md`; `git diff --cached --check` rc 0; the repo hook run BY HAND on the staged replay (the sequencer commits a resolved pick with -n): `[hook] tag=g1rb-hook-replayed-staged start=2026-11-02 15:11:04 end=2026-11-02 15:11:15 rc=0`; `GIT_EDITOR=true git rebase --continue` -> f67ccca30daae8de09a74a0c42fe7d63a12ebe1f, 'Successfully rebased and updated refs/heads/feature/s81-g1-price-pipeline'; `git diff --check HEAD~1 HEAD` rc 0; status empty.
- `git diff --name-status origin/main...HEAD` after the replay = exactly the 26 files (M CLAUDE.md, extraction_service, price_service, response_builder, scrapedo_service, structured_comparison_service, seed_spec_spine, seed_zyte_luxury, test_prompt_fence, test_seed_zyte_guard, test_zyte_seed_variant; A jsonld_widen.py, the golden, the two RED files, the gate-rows file; D judgeme_service.py, the 8 judgeme_c5 fixtures, test_m6_c5_judgeme_html_reviews.py); unchanged after the round commit (diff of the two name-status listings empty); `git diff --stat` shows no whole-file diff (26 files, +3244 / -1022 at the end).
- `git diff --name-only 6da5aa68 HEAD~1` lists 13 files = main's 12 non-CLAUDE S81-09 files + CLAUDE.md; intersected with the group's 26 files only CLAUDE.md remains, so the group's 25 non-CLAUDE files are blob-identical to 6da5aa68's (RB-G1-3).
- Round commit dae4c5357a3ac0766570183cfe00533bd64a85a2 through the hook (`git commit -F`, never --no-verify; the hook printed All checks passed!); Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>; 3 files, +162 / -4: CLAUDE.md (1 line), app/services/jsonld_widen.py (1 docstring line), tests/test_s81_g1_gate_rows.py (the four rows).
- No push, no PR, no other git write besides the detached scratch worktree (created and removed, section 6.5).

## 2. Conflicts and resolutions
- CLAUDE.md, ONE region (working-copy lines 531-543 with markers): HEAD side = main's S81-09 block (the `**SESSION 81 flags (S81-09 DEVICE-QUOTA-RIYADH, ...)**` heading + 5 bullets); the replayed side = the S81-G1 block (heading + 3 bullets); both added at the same anchor (after the S81-08 block, before `## Tests`). The 'both sides added at the same anchor' class.
- Resolution = UNION in merge order (RB-G1-2 b): main's S81-09 block, one blank line, the S81-G1 block, the blank line, `## Tests`; written with Python over the CRLF bytes (split / join on CRLF; 0 lone LF, 0 lone CR); the conflicted copy saved as CLAUDE.md.conflicted.bak (sha b8edbe10...), the resolved working copy sha 3c90522a... .
- Union check (line-level difflib on LF-normalised text, never a char-level diff of the whole file): (resolved vs main) removed/added multiset == (branch vs base) [13 removed, 19 added]; (resolved vs branch) == (main vs base). Non-ASCII characters: base 1353, main 1351, branch 1347, resolved 1345 (the GREEN's in-place rewrites removed 6, main's S81-09 line rewrite removed 2; this round added none; HEAD after the round commit 1345).
- RB-G1-2 (a): the `**Feature Flags:**` pointer line auto-merged to main's text (it carries the S81-04, S81-06, S81-08b, S81-15 and S81-09 pointers; no S81-08 pointer exists on it); the GREEN put NO S81-G1 pointer on that line (measured: the branch's line == the base's line), so the ruling's 'plus this group's entry where the GREEN put it' had nothing to carry; no pointer was invented (RB-G1-6 'nothing else moves'). Deviation stated for a ruling.
- RB-G1-2 (c): the six wall-praising lines and the two judge.me lines stay as the GREEN wrote them (main did not move them; they replayed without conflict).
- RB-G1-2 (d), in the round commit: the D08 row's sentence 'before D14 the rating flag only REMOVES fabricated ratings' rewritten in place (dated 2026-11-02, F1-G1-2) to name both ON effects (the review-sentiment signal lost: `_score_reliability`'s +0.05 / -0.10 adjustment, measured 0.80 / 0.65 OFF both 0.75 ON, the reliability-mapped dimensions and in a close pair the winner can move; `metadata.data_freshness_shaky` condition (ii) always holds, build 3 does not render the key), and the row's rollback sentence carries the GR-G1-5 note (reviews cached while ON carry no model average_rating; until the reviews TTL 7 d L1 / 14 d L2 the GPT fallback has nothing to promote; the remedy is a reviews cache flush, the owner's). One physical line changed (both edits sit on the D08 bullet), ASCII, CRLF kept; the G1 block stays contiguous (3 bullets) and keeps ENABLE_SCRAPEDO_SUPER + the robots-policy file name (test_s23_r8).
- No test file conflicted, so the rule's list-entry / clear-list / recorder unions and the numeric-count rule had nothing to apply to; `grep` for <<<<<<< / >>>>>>> over CLAUDE.md, app/ and tests/ at HEAD: no match (`git grep` over HEAD rc 1; the working-tree grep empty).

## 3. Frozen RED files (re-hashed at start and end)
| file | frozen sha256 (rulings) | at start, on disk | at end, blob (git show HEAD:path) | at end, on disk |
|---|---|---|---|---|
| tests/test_s81_d08_jsonld_widen.py | a0748bcff862e91dffa0ff99905f59b689ebefa4f2bfbfeafa081530b82c040c | a0748bcff862e91dffa0ff99905f59b689ebefa4f2bfbfeafa081530b82c040c | a0748bcff862e91dffa0ff99905f59b689ebefa4f2bfbfeafa081530b82c040c | 6239f9a7f6e28c66776c93d71f6ccb4f96a6eb8960e4a104713573338e5fd682 |
| tests/fixtures/s81_d08_rating_flag_off_golden.json | 92d0686b6adcf53f3c07aa06bd40a55c1e6d59cb12de58c624d0e49331742c33 | 92d0686b6adcf53f3c07aa06bd40a55c1e6d59cb12de58c624d0e49331742c33 | 92d0686b6adcf53f3c07aa06bd40a55c1e6d59cb12de58c624d0e49331742c33 | 696085a85242b6fee58f7489af31b253c5eab1ef5f978ddc3e7eceef78bb0201 |
| tests/test_s81_s23_bypass_retire.py | 6cf8c6d3f701636f839ab0073d4f29c73d8fcc602648458aa15190bfb7c930dc | 6cf8c6d3f701636f839ab0073d4f29c73d8fcc602648458aa15190bfb7c930dc | 6cf8c6d3f701636f839ab0073d4f29c73d8fcc602648458aa15190bfb7c930dc | 28d93fa602d275aecf29b294948eaab1b866bc7c18ae35132a7a224fe2d4391d |

Blob identity holds for all three (the house identity: blob = git show HEAD:path). The working-copy bytes changed from LF to CRLF because the rebase re-checked the files out under core.autocrlf=true (the RED files were written LF and never rewritten by git before); no tool of this round wrote them. Stated as a deviation.

## 4. Files of the round commit dae4c535 (sha256)
| path | blob sha256 at HEAD | on-disk sha256 (CRLF) | change |
|---|---|---|---|
| CLAUDE.md | a1723c2ccfd3b6b59f666d8eb6e2de7cbe05511e479abc3b794020688c0ccb63 | 625c65590508a3b2f9507cbcf6763d3ebf64ac07da7572dbeba22577de2d595b | RB-G1-2 (d): the D08 row sentence (F1-G1-2) + the rollback note (GR-G1-5); 1 line |
| app/services/jsonld_widen.py | 28f6b9ce95b39de2515e34397aa5a463ec5ebf46e4c3df685217ee1cbed84bd4 | e0978ac45c4017f69e06b593af633921376b2b7363e8cdbd4bb3ca844a7757bc | F1-G1-3: one docstring line of rules_allow; comment-only |
| tests/test_s81_g1_gate_rows.py | 4a4841a72701b69e0d9742f5c508411a7c100363e5a42a33d4fa9cba1dfad8a2 | a64fb581a7d35340157c82ac42e12a9385eb47175669e0b55865739ec2d811d9 | F1-G1-4: the four rows A-M18 (first), A-M27, A-M29, A-M30 + the docstring index; 10 -> 14 nodes |

## 5. The four pin rows (F1-G1-4) and their mutants (in place, under .qa-mutation.lock, byte copy -> exact edit -> pyt.py -k row -> restore -> sha256 compare)
| mutant | row | edit | verdict | failure | sha before / restored |
|---|---|---|---|---|---|
| A-M18 | test_g1_am18_first_party_label_boundary | first-party suffix match without the '.' boundary | KILLED | E       AssertionError: assert 'https://evilstore-a.example.com/img/a.jpg' is None | e0978ac45c40 / e0978ac45c40 (equal) |
| A-M27 | test_g1_am27_first_allowed_image_wins | stamp keeps the LAST allowed image | KILLED | E       AssertionError: assert {'amount': 45...g/second.jpg'} == {'amount': 45...mg/first.jpg'} | e0978ac45c40 / e0978ac45c40 (equal) |
| A-M29 | test_g1_am29_rating_fact_lower_bound | rating_fact lower bound dropped (0.0..5.0) | KILLED | E       AssertionError: assert {'value': 0.2, 'count': None} is None | e0978ac45c40 / e0978ac45c40 (equal) |
| A-M30 | test_g1_am30_channel1_range_check | channel1_rating's own 1..5 range check dropped | KILLED | E           AssertionError: 6.0 | e0978ac45c40 / e0978ac45c40 (equal) |

```
[pyt] tag=g1rb-gaterows-pre start=2026-11-02 15:18:58 end=2026-11-02 15:19:01 elapsed=3s bound=600s status=OK rc=0   # 22 passed, 1 warning (the first, parametrised draft of the four rows; restructured to four functions before the commit)
[pyt] tag=g1rb-gaterows-pre2 start=2026-11-02 15:19:47 end=2026-11-02 15:19:50 elapsed=3s bound=600s status=OK rc=0   # 14 passed, 1 warning
[pyt] tag=g1rb-mut-a-m18 start=2026-11-02 15:20:23 end=2026-11-02 15:20:26 elapsed=3s bound=600s status=FAIL rc=1   # 1 failed, 13 deselected (KILLED, AssertionError)
[pyt] tag=g1rb-mut-a-m27 start=2026-11-02 15:20:27 end=2026-11-02 15:20:29 elapsed=3s bound=600s status=FAIL rc=1   # 1 failed, 13 deselected (KILLED, AssertionError)
[pyt] tag=g1rb-mut-a-m29 start=2026-11-02 15:20:30 end=2026-11-02 15:20:32 elapsed=3s bound=600s status=FAIL rc=1   # 1 failed, 13 deselected (KILLED, AssertionError)
[pyt] tag=g1rb-mut-a-m30 start=2026-11-02 15:20:33 end=2026-11-02 15:20:35 elapsed=3s bound=600s status=FAIL rc=1   # 1 failed, 13 deselected (KILLED, AssertionError)
```

## 6. Gates ([pyt] / [jest] / [hook] lines, every one pasted)
### 6.1 lint
- `ruff check --select E9,F63,F7,F82 --no-cache` over the 14 touched .py files (app/services/{extraction_service,jsonld_widen,price_service,response_builder,scrapedo_service,structured_comparison_service}.py, scripts/{seed_spec_spine,seed_zyte_luxury}.py, tests/{test_prompt_fence,test_s81_d08_jsonld_widen,test_s81_g1_gate_rows,test_s81_s23_bypass_retire,test_seed_zyte_guard,test_zyte_seed_variant}.py): All checks passed!; `py_compile` rc 0; the golden JSON loads.
- Byte checks after every write: the three edited files CRLF only (0 lone LF, 0 lone CR); the gate-rows file and jsonld_widen.py 0 non-ASCII bytes; the CLAUDE.md G1 block 0 non-ASCII characters; `git diff --check` rc 0.
### 6.2 unit run (2 RED files + the gate-rows file): 220 / 220 in five states
```
[pyt] tag=g1rb-unit-off start=2026-11-02 15:21:51 end=2026-11-02 15:21:55 elapsed=5s bound=600s status=OK rc=0   # 220 passed, 1 warning; flags + SCRAPEDO_SUPER unset
[pyt] tag=g1rb-unit-on start=2026-11-02 15:22:07 end=2026-11-02 15:22:12 elapsed=5s bound=600s status=OK rc=0   # 220 passed, 1 warning; ENABLE_IMAGE_PIPELINE_V2 + ENABLE_JSONLD_RATING + ENABLE_SCRAPEDO_SUPER = true
[pyt] tag=g1rb-unit-img start=2026-11-02 15:22:12 end=2026-11-02 15:22:17 elapsed=5s bound=600s status=OK rc=0   # 220 passed, 1 warning; ENABLE_IMAGE_PIPELINE_V2 = true alone
[pyt] tag=g1rb-unit-rating start=2026-11-02 15:22:18 end=2026-11-02 15:22:22 elapsed=4s bound=600s status=OK rc=0   # 220 passed, 1 warning; ENABLE_JSONLD_RATING = true alone
[pyt] tag=g1rb-unit-s23kill start=2026-11-02 15:22:22 end=2026-11-02 15:22:26 elapsed=4s bound=600s status=OK rc=0   # 220 passed, 1 warning; ENABLE_SCRAPEDO_SUPER=false + SCRAPEDO_SUPER=true
```
Each log also carries `[hermeticity] sentinel checked 220 test(s)` and `[netguard] blocked 0 attempt(s) from 0 node(s)`.
### 6.3 single gates (flag OFF, once each): R8 pair, metering, CI-order set (30 files, list ciorder_rb.txt), the two CLAUDE.md readers
```
[pyt] tag=g1rb-r8pair start=2026-11-02 15:43:23 end=2026-11-02 15:43:44 elapsed=22s bound=600s status=OK rc=0   # 273 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 273 test(s)
[pyt] tag=g1rb-metering start=2026-11-02 15:43:44 end=2026-11-02 15:43:49 elapsed=4s bound=600s status=OK rc=0   # 21 passed, 13 warnings; [netguard] blocked 2 attempt(s) from 2 node(s); [hermeticity] sentinel checked 21 test(s)
[pyt] tag=g1rb-ciorder start=2026-11-02 15:43:49 end=2026-11-02 15:44:41 elapsed=52s bound=1200s status=OK rc=0   # 3145 passed, 1 skipped, 13 warnings; [netguard] blocked 28 attempt(s) from 4 node(s); [hermeticity] sentinel checked 3146 test(s)
[pyt] tag=g1rb-claudemd start=2026-11-02 15:44:41 end=2026-11-02 15:44:46 elapsed=5s bound=600s status=OK rc=0   # 79 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 79 test(s)
```
- The R8 pair and tests/test_paid_route_metering.py ran ONCE, flag OFF (the task's ruling: cheap, once); the 'with the flag exported' leg of the generic gate (4) was not run by that ruling.
- No test file was conflicted (CLAUDE.md only), so the generic gate (2) has no member; the CLAUDE.md readers ran alone (g1rb-claudemd) and inside the CI-order set.
### 6.4 corpus gate (RB-G1-4 c) at HEAD dae4c535 after the docstring edit
- `start 2026-11-02 15:24:40 cwd=C:/Users/SynAckITPC/Documents/AI/sc-s81-g1 HEAD=dae4c5357a3ac0766570183cfe00533bd64a85a2`
- `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`
- `OVERALL SHA256 9f9f9aeb185f7e811aa4292141d57a567e0aaaf7a1cc28f3b5ece0ac51ecaf33` (expected 9f9f9aeb185f7e811aa4292141d57a567e0aaaf7a1cc28f3b5ece0ac51ecaf33: EQUAL)
- `rc=0 end 2026-11-02 15:31:31`
### 6.5 comm set (union rule) at BASE eaccd550 and at HEAD
- Derivation: the GREEN's union-rule script (comm_derive_head.py, copied unchanged) at the rebased HEAD, unioned with the GREEN's 595-file list: derived 597, union 597; additions vs the 595: tests/test_s81_s09_device_quota.py (classes: app-main-importer, ast-parse, file-reader, module-file-path, module:extraction_service, seed-grep) and tests/test_s81_s09_gate_rows.py (app-main-importer); tests/test_s81_st1_usage_path_offloop.py and tests/test_s81_s05_request_context.py were already members; nothing dropped; excluded: tests/test_m6_c5_judgeme_html_reviews.py (deleted) and the 4 test_precommit_hook*.py files. List comm/comm_files_head.txt, reasons comm/comm_reasons_head.tsv, sorted-list sha256 406b86f4563c9396a01ca7eff2672c7e4d3f41c12a374d46aad98dea96868473.
- BASE: no record existed under harness/base_records/eaccd550a0ba747b7fc56219cfaef15a83dcb50e/, so the whole set ran ONCE at base in a detached scratch worktree (`git -c core.longpaths=true worktree add --detach <notes>/wtb eaccd550`; no junction, no .env; the three G1 test files + the golden copied in untracked from the dae4c535 blobs so every member runs, as record 49929b45 did), one pytest at a time, the 4 NETWORK_FLAKY_EXCLUDE nodes deselected, unit flags + SCRAPEDO_SUPER removed from the child env. Stored per LC-6: 406b86f4563c9396a01ca7eff2672c7e4d3f41c12a374d46aad98dea96868473.txt (the FAILED/ERROR node ids), 406b86f4563c9396a01ca7eff2672c7e4d3f41c12a374d46aad98dea96868473.pyt.log (header + every [pyt] line + per-chunk summaries), 406b86f4563c9396a01ca7eff2672c7e4d3f41c12a374d46aad98dea96868473.files (the sorted list). Then `git worktree remove --force <notes>/wtb`, verified gone (`git worktree list` has no entry, the directory is gone).
- Totals: BASE 22 runs status=OK, 5 status=FAIL, 0 TIMEOUT; 25303 passed, 123 failed, 3 error, 56 skipped, 59 deselected, 39 xfailed; HEAD 24 runs status=OK, 3 status=FAIL, 0 TIMEOUT; 25437 passed, 6 failed, 2 error, 53 skipped, 59 deselected, 39 xfailed. The passed delta (+134) = the G1 files (220 green at HEAD vs 89 PIN rows green at base: +131) + 3 nodes skipped at base only, all in chunk 02 (same file list both sides: 1070 passed / 3 skipped at base vs 1073 passed at HEAD): of that chunk's files with a skip condition, tests/test_category_payload_completeness.py reads its prod fixtures from a path relative to the worktree's PARENT (../smartcompare/.qa-bias-rerun/_discovery/prod), which exists beside sc-s81-g1 and not beside the scratch checkout; an environment difference, not code (inferred from the skip conditions; the logs carry no -rs list).
- Chunking, identical on both sides: tests/test_secret_scan_static.py ALONE (bound 600); the two RED files; the gate-rows file ALONE (at base it cannot import the leaf: a collection ERROR, rc 2, that would abort a shared chunk); the other 593 files in sorted order, at most 25 each (bound 1200): 27 pytest runs per side.
BASE [pyt] lines (scratch worktree wtb at eaccd550):
```
[pyt] tag=g1rb-cb-secret start=2026-11-02 15:24:30 end=2026-11-02 15:24:39 elapsed=9s bound=600s status=OK rc=0   # 31 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 31 test(s)
[pyt] tag=g1rb-cb-red start=2026-11-02 15:24:39 end=2026-11-02 15:24:48 elapsed=8s bound=1200s status=FAIL rc=1   # 117 failed, 89 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 206 test(s)
[pyt] tag=g1rb-cb-rows start=2026-11-02 15:24:48 end=2026-11-02 15:24:50 elapsed=2s bound=1200s status=FAIL rc=2   # 1 error; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 0 test(s)
[pyt] tag=g1rb-cb-00 start=2026-11-02 15:24:50 end=2026-11-02 15:25:33 elapsed=43s bound=1200s status=FAIL rc=1   # 2 failed, 831 passed, 1 deselected, 19 warnings; [netguard] blocked 26 attempt(s) from 8 node(s); [hermeticity] sentinel checked 833 test(s)
[pyt] tag=g1rb-cb-01 start=2026-11-02 15:25:33 end=2026-11-02 15:25:56 elapsed=23s bound=1200s status=OK rc=0   # 633 passed, 23 warnings; [netguard] blocked 15 attempt(s) from 5 node(s); [hermeticity] sentinel checked 633 test(s)
[pyt] tag=g1rb-cb-02 start=2026-11-02 15:25:56 end=2026-11-02 15:27:07 elapsed=71s bound=1200s status=OK rc=0   # 1070 passed, 3 skipped, 6 deselected, 13 warnings; [netguard] blocked 27 attempt(s) from 11 node(s); [hermeticity] sentinel checked 1073 test(s)
[pyt] tag=g1rb-cb-03 start=2026-11-02 15:27:07 end=2026-11-02 15:27:40 elapsed=33s bound=1200s status=OK rc=0   # 1170 passed, 1 skipped, 2 deselected, 1 xfailed, 11 warnings; [netguard] blocked 4 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1172 test(s)
[pyt] tag=g1rb-cb-04 start=2026-11-02 15:27:40 end=2026-11-02 15:27:56 elapsed=15s bound=1200s status=OK rc=0   # 540 passed, 13 warnings; [netguard] blocked 1 attempt(s) from 1 node(s); [hermeticity] sentinel checked 540 test(s)
[pyt] tag=g1rb-cb-05 start=2026-11-02 15:27:56 end=2026-11-02 15:28:14 elapsed=18s bound=1200s status=OK rc=0   # 447 passed, 2 skipped, 1 warning; [netguard] blocked 10 attempt(s) from 4 node(s); [hermeticity] sentinel checked 448 test(s)
[pyt] tag=g1rb-cb-06 start=2026-11-02 15:28:14 end=2026-11-02 15:29:20 elapsed=65s bound=1200s status=OK rc=0   # 2031 passed, 11 warnings; [netguard] blocked 50 attempt(s) from 16 node(s); [hermeticity] sentinel checked 2031 test(s)
[pyt] tag=g1rb-cb-07 start=2026-11-02 15:29:20 end=2026-11-02 15:30:24 elapsed=64s bound=1200s status=OK rc=0   # 1377 passed, 1 skipped, 5 deselected, 18 warnings; [netguard] blocked 29 attempt(s) from 28 node(s); [hermeticity] sentinel checked 1378 test(s)
[pyt] tag=g1rb-cb-08 start=2026-11-02 15:30:25 end=2026-11-02 15:30:59 elapsed=35s bound=1200s status=OK rc=0   # 559 passed, 1 xfailed, 13 warnings; [netguard] blocked 13 attempt(s) from 2 node(s); [hermeticity] sentinel checked 560 test(s)
[pyt] tag=g1rb-cb-09 start=2026-11-02 15:30:59 end=2026-11-02 15:31:23 elapsed=24s bound=1200s status=OK rc=0   # 383 passed, 13 warnings; [netguard] blocked 3 attempt(s) from 3 node(s); [hermeticity] sentinel checked 383 test(s)
[pyt] tag=g1rb-cb-10 start=2026-11-02 15:31:23 end=2026-11-02 15:31:36 elapsed=13s bound=1200s status=OK rc=0   # 373 passed, 1 skipped, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 374 test(s)
[pyt] tag=g1rb-cb-11 start=2026-11-02 15:31:36 end=2026-11-02 15:32:06 elapsed=30s bound=1200s status=OK rc=0   # 3648 passed, 1 skipped, 10 deselected, 3 warnings; [netguard] blocked 7 attempt(s) from 1 node(s); [hermeticity] sentinel checked 3649 test(s)
[pyt] tag=g1rb-cb-12 start=2026-11-02 15:32:06 end=2026-11-02 15:32:42 elapsed=35s bound=1200s status=FAIL rc=1   # 4 failed, 665 passed, 21 skipped, 16 warnings; [netguard] blocked 147 attempt(s) from 18 node(s); [hermeticity] sentinel checked 669 test(s)
[pyt] tag=g1rb-cb-13 start=2026-11-02 15:32:42 end=2026-11-02 15:33:05 elapsed=24s bound=1200s status=OK rc=0   # 571 passed, 3 skipped, 15 deselected, 10 warnings; [netguard] blocked 15 attempt(s) from 5 node(s); [hermeticity] sentinel checked 571 test(s)
[pyt] tag=g1rb-cb-14 start=2026-11-02 15:33:06 end=2026-11-02 15:33:25 elapsed=20s bound=1200s status=FAIL rc=1   # 492 passed, 5 skipped, 2 deselected, 1 xfailed, 13 warnings, 2 errors; [netguard] blocked 93 attempt(s) from 9 node(s); [hermeticity] sentinel checked 496 test(s)
[pyt] tag=g1rb-cb-15 start=2026-11-02 15:33:25 end=2026-11-02 15:36:05 elapsed=159s bound=1200s status=OK rc=0   # 859 passed, 261 warnings; [netguard] blocked 20 attempt(s) from 1 node(s); [hermeticity] sentinel checked 859 test(s)
[pyt] tag=g1rb-cb-16 start=2026-11-02 15:36:05 end=2026-11-02 15:37:33 elapsed=88s bound=1200s status=OK rc=0   # 1335 passed, 13 warnings; [netguard] blocked 4 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1335 test(s)
[pyt] tag=g1rb-cb-17 start=2026-11-02 15:37:33 end=2026-11-02 15:39:13 elapsed=99s bound=1200s status=OK rc=0   # 4026 passed, 1 xfailed, 94 warnings; [netguard] blocked 24 attempt(s) from 2 node(s); [hermeticity] sentinel checked 4027 test(s)
[pyt] tag=g1rb-cb-18 start=2026-11-02 15:39:13 end=2026-11-02 15:40:17 elapsed=64s bound=1200s status=OK rc=0   # 920 passed, 13 warnings; [netguard] blocked 17 attempt(s) from 9 node(s); [hermeticity] sentinel checked 920 test(s)
[pyt] tag=g1rb-cb-19 start=2026-11-02 15:40:17 end=2026-11-02 15:40:40 elapsed=23s bound=1200s status=OK rc=0   # 661 passed, 1 skipped, 2 deselected, 13 warnings; [netguard] blocked 10 attempt(s) from 2 node(s); [hermeticity] sentinel checked 661 test(s)
[pyt] tag=g1rb-cb-20 start=2026-11-02 15:40:40 end=2026-11-02 15:41:34 elapsed=54s bound=1200s status=OK rc=0   # 506 passed, 7 skipped, 8 deselected, 22 warnings; [netguard] blocked 96 attempt(s) from 37 node(s); [hermeticity] sentinel checked 513 test(s)
[pyt] tag=g1rb-cb-21 start=2026-11-02 15:41:34 end=2026-11-02 15:42:27 elapsed=53s bound=1200s status=OK rc=0   # 517 passed, 8 deselected, 35 xfailed, 13 warnings; [netguard] blocked 84 attempt(s) from 29 node(s); [hermeticity] sentinel checked 552 test(s)
[pyt] tag=g1rb-cb-22 start=2026-11-02 15:42:27 end=2026-11-02 15:43:02 elapsed=35s bound=1200s status=OK rc=0   # 951 passed, 13 warnings; [netguard] blocked 8 attempt(s) from 8 node(s); [hermeticity] sentinel checked 951 test(s)
[pyt] tag=g1rb-cb-23 start=2026-11-02 15:43:02 end=2026-11-02 15:43:20 elapsed=18s bound=1200s status=OK rc=0   # 618 passed, 10 skipped, 1 warning; [netguard] blocked 12 attempt(s) from 4 node(s); [hermeticity] sentinel checked 628 test(s)
```
HEAD [pyt] lines (sc-s81-g1 at dae4c535):
```
[pyt] tag=g1rb-ch-secret start=2026-11-02 15:44:46 end=2026-11-02 15:44:55 elapsed=9s bound=600s status=OK rc=0   # 31 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 31 test(s)
[pyt] tag=g1rb-ch-red start=2026-11-02 15:44:55 end=2026-11-02 15:44:59 elapsed=4s bound=1200s status=OK rc=0   # 206 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 206 test(s)
[pyt] tag=g1rb-ch-rows start=2026-11-02 15:44:59 end=2026-11-02 15:45:03 elapsed=4s bound=1200s status=OK rc=0   # 14 passed, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 14 test(s)
[pyt] tag=g1rb-ch-00 start=2026-11-02 15:45:04 end=2026-11-02 15:45:38 elapsed=35s bound=1200s status=FAIL rc=1   # 2 failed, 831 passed, 1 deselected, 19 warnings; [netguard] blocked 26 attempt(s) from 8 node(s); [hermeticity] sentinel checked 833 test(s)
[pyt] tag=g1rb-ch-01 start=2026-11-02 15:45:38 end=2026-11-02 15:45:59 elapsed=20s bound=1200s status=OK rc=0   # 633 passed, 23 warnings; [netguard] blocked 15 attempt(s) from 5 node(s); [hermeticity] sentinel checked 633 test(s)
[pyt] tag=g1rb-ch-02 start=2026-11-02 15:45:59 end=2026-11-02 15:46:59 elapsed=60s bound=1200s status=OK rc=0   # 1073 passed, 6 deselected, 13 warnings; [netguard] blocked 27 attempt(s) from 11 node(s); [hermeticity] sentinel checked 1073 test(s)
[pyt] tag=g1rb-ch-03 start=2026-11-02 15:46:59 end=2026-11-02 15:47:29 elapsed=30s bound=1200s status=OK rc=0   # 1170 passed, 1 skipped, 2 deselected, 1 xfailed, 11 warnings; [netguard] blocked 4 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1172 test(s)
[pyt] tag=g1rb-ch-04 start=2026-11-02 15:47:29 end=2026-11-02 15:47:43 elapsed=14s bound=1200s status=OK rc=0   # 540 passed, 13 warnings; [netguard] blocked 1 attempt(s) from 1 node(s); [hermeticity] sentinel checked 540 test(s)
[pyt] tag=g1rb-ch-05 start=2026-11-02 15:47:43 end=2026-11-02 15:48:00 elapsed=17s bound=1200s status=OK rc=0   # 447 passed, 2 skipped, 1 warning; [netguard] blocked 10 attempt(s) from 4 node(s); [hermeticity] sentinel checked 448 test(s)
[pyt] tag=g1rb-ch-06 start=2026-11-02 15:48:00 end=2026-11-02 15:49:03 elapsed=63s bound=1200s status=OK rc=0   # 2031 passed, 11 warnings; [netguard] blocked 50 attempt(s) from 16 node(s); [hermeticity] sentinel checked 2031 test(s)
[pyt] tag=g1rb-ch-07 start=2026-11-02 15:49:03 end=2026-11-02 15:50:02 elapsed=58s bound=1200s status=OK rc=0   # 1377 passed, 1 skipped, 5 deselected, 18 warnings; [netguard] blocked 29 attempt(s) from 28 node(s); [hermeticity] sentinel checked 1378 test(s)
[pyt] tag=g1rb-ch-08 start=2026-11-02 15:50:02 end=2026-11-02 15:50:33 elapsed=31s bound=1200s status=OK rc=0   # 559 passed, 1 xfailed, 13 warnings; [netguard] blocked 13 attempt(s) from 2 node(s); [hermeticity] sentinel checked 560 test(s)
[pyt] tag=g1rb-ch-09 start=2026-11-02 15:50:33 end=2026-11-02 15:50:55 elapsed=22s bound=1200s status=OK rc=0   # 383 passed, 13 warnings; [netguard] blocked 3 attempt(s) from 3 node(s); [hermeticity] sentinel checked 383 test(s)
[pyt] tag=g1rb-ch-10 start=2026-11-02 15:50:55 end=2026-11-02 15:51:06 elapsed=11s bound=1200s status=OK rc=0   # 373 passed, 1 skipped, 1 warning; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 374 test(s)
[pyt] tag=g1rb-ch-11 start=2026-11-02 15:51:07 end=2026-11-02 15:51:37 elapsed=30s bound=1200s status=OK rc=0   # 3648 passed, 1 skipped, 10 deselected, 3 warnings; [netguard] blocked 7 attempt(s) from 1 node(s); [hermeticity] sentinel checked 3649 test(s)
[pyt] tag=g1rb-ch-12 start=2026-11-02 15:51:37 end=2026-11-02 15:52:10 elapsed=33s bound=1200s status=FAIL rc=1   # 4 failed, 665 passed, 21 skipped, 16 warnings; [netguard] blocked 147 attempt(s) from 18 node(s); [hermeticity] sentinel checked 669 test(s)
[pyt] tag=g1rb-ch-13 start=2026-11-02 15:52:10 end=2026-11-02 15:52:31 elapsed=21s bound=1200s status=OK rc=0   # 571 passed, 3 skipped, 15 deselected, 10 warnings; [netguard] blocked 15 attempt(s) from 5 node(s); [hermeticity] sentinel checked 571 test(s)
[pyt] tag=g1rb-ch-14 start=2026-11-02 15:52:31 end=2026-11-02 15:52:50 elapsed=19s bound=1200s status=FAIL rc=1   # 492 passed, 5 skipped, 2 deselected, 1 xfailed, 13 warnings, 2 errors; [netguard] blocked 93 attempt(s) from 9 node(s); [hermeticity] sentinel checked 496 test(s)
[pyt] tag=g1rb-ch-15 start=2026-11-02 15:52:50 end=2026-11-02 15:55:27 elapsed=156s bound=1200s status=OK rc=0   # 859 passed, 261 warnings; [netguard] blocked 20 attempt(s) from 1 node(s); [hermeticity] sentinel checked 859 test(s)
[pyt] tag=g1rb-ch-16 start=2026-11-02 15:55:27 end=2026-11-02 15:56:50 elapsed=83s bound=1200s status=OK rc=0   # 1335 passed, 13 warnings; [netguard] blocked 4 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1335 test(s)
[pyt] tag=g1rb-ch-17 start=2026-11-02 15:56:51 end=2026-11-02 15:58:48 elapsed=118s bound=1200s status=OK rc=0   # 4026 passed, 1 xfailed, 94 warnings; [netguard] blocked 24 attempt(s) from 2 node(s); [hermeticity] sentinel checked 4027 test(s)
[pyt] tag=g1rb-ch-18 start=2026-11-02 15:58:49 end=2026-11-02 15:59:54 elapsed=65s bound=1200s status=OK rc=0   # 920 passed, 13 warnings; [netguard] blocked 17 attempt(s) from 9 node(s); [hermeticity] sentinel checked 920 test(s)
[pyt] tag=g1rb-ch-19 start=2026-11-02 15:59:55 end=2026-11-02 16:00:14 elapsed=19s bound=1200s status=OK rc=0   # 661 passed, 1 skipped, 2 deselected, 13 warnings; [netguard] blocked 10 attempt(s) from 2 node(s); [hermeticity] sentinel checked 661 test(s)
[pyt] tag=g1rb-ch-20 start=2026-11-02 16:00:14 end=2026-11-02 16:01:03 elapsed=49s bound=1200s status=OK rc=0   # 506 passed, 7 skipped, 8 deselected, 22 warnings; [netguard] blocked 97 attempt(s) from 37 node(s); [hermeticity] sentinel checked 513 test(s)
[pyt] tag=g1rb-ch-21 start=2026-11-02 16:01:03 end=2026-11-02 16:01:53 elapsed=50s bound=1200s status=OK rc=0   # 517 passed, 8 deselected, 35 xfailed, 13 warnings; [netguard] blocked 84 attempt(s) from 29 node(s); [hermeticity] sentinel checked 552 test(s)
[pyt] tag=g1rb-ch-22 start=2026-11-02 16:01:54 end=2026-11-02 16:02:26 elapsed=33s bound=1200s status=OK rc=0   # 951 passed, 13 warnings; [netguard] blocked 8 attempt(s) from 8 node(s); [hermeticity] sentinel checked 951 test(s)
[pyt] tag=g1rb-ch-23 start=2026-11-02 16:02:26 end=2026-11-02 16:02:43 elapsed=17s bound=1200s status=OK rc=0   # 618 passed, 10 skipped, 1 warning; [netguard] blocked 12 attempt(s) from 4 node(s); [hermeticity] sentinel checked 628 test(s)
```
- base failed (126): tests/test_auth_interceptor.py::test_sign_in_with_social_exception, tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully, tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities, tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable + 118 node(s) of the three G1 files (their RED state at base)
- HEAD failed (8): tests/test_auth_interceptor.py::test_sign_in_with_social_exception, tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully, tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities, tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- comm -13 (HEAD-only, branch-only-new): EMPTY
- the eight base failures identical on both sides; none turned green; the 118 base-only failures are the RED state of the three G1 files (green at HEAD)
- netguard (the box guard blocks and records every egress / sentinel attempt; a blocked attempt does not fail a test): nodes with a blocked attempt at BASE 207, at HEAD 207; HEAD-only nodes: none; BASE-only nodes: none.
### 6.6 client fences and the full jest suite (node v24.11.1, jest 29.7.0, by path through the orchestrator junction; never npx, never npm, the junction untouched)
- medicalNote.s74 (first; reads app/services/extraction_service.py): Test Suites: 1 passed, 1 total; Tests: 15 passed, 15 total; `[jest] tag=g1rb-jest-medicalnote start=2026-11-02 15:25:05 end=2026-11-02 15:25:08 rc=0`
- the other 13: Test Suites: 1 failed, 12 passed, 13 total; Tests: 4 failed, 221 passed, 225 total; `[jest] tag=g1rb-jest-fences13 start=2026-11-02 15:25:15 end=2026-11-02 15:25:22 rc=1`; the 4 failures = nativeBundle.w37 d5 / k2 / k4 / k5 (the accepted drift nodes)
- FULL suite once (LC-7): Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total; Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total; `[jest] tag=g1rb-jest-full start=2026-11-02 15:25:51 end=2026-11-02 15:26:10 rc=1`; the 4 failures = the same four drift nodes; passed 3,794 = the S81-09 rebase's full-suite figure, and no SmartCompareApp file differs between 6c14ac95, eaccd550 and HEAD (`git diff --name-only` empty both ways), so it is main's count; no -u, no .snap, git status empty after
### 6.7 hook
- replayed commit f67ccca3: the sequencer commits a resolved pick with -n, so the hook ran BY HAND on the staged replay before --continue: `[hook] tag=g1rb-hook-replayed-staged start=2026-11-02 15:11:04 end=2026-11-02 15:11:15 rc=0` (the hook's own output: All checks passed!).
- round commit dae4c535: through the hook at commit time (`git commit -F`, 15:20:51-15:20:59, rc 0, All checks passed!).
- tests/test_precommit_hook*.py: NOT re-run (the group touches no .githooks file; RULINGS_REBASE_S81_G1 RB-G1-4 names no hook-file run and the task brief rules them not re-run).

## 7. NOT MEASURED
- tests/test_precommit_hook*.py (generic gate 9): not run, by ruling (no .githooks change).
- tests/test_paid_route_metering.py and the R8 pair WITH a flag exported (generic gates 3 / 4): run once flag OFF only, by the task's ruling.
- Generic gate (2) 'each conflicted test file alone': no test file conflicted.
- No TIMEOUT occurred; nothing else is NOT MEASURED.

## 8. Deviations
- D-1 RB-G1-2 (a): no S81-G1 pointer added to the `**Feature Flags:**` line: the GREEN placed none there (its line == base), so the union is main's text; adding one would be new text from neither side (RB-G1-6 'nothing else moves'). Ruling owed if a pointer is wanted (a one-sentence docs edit in a later round).
- D-2 The frozen RED files' WORKING-COPY bytes are now CRLF (git re-checked them out during the rebase under core.autocrlf=true; at the start they were LF on disk); their blobs are byte-identical to the frozen hashes, and no tool of this round wrote them. On-disk sha256 at the end: see section 3.
- D-3 The replayed commit's hook ran by hand on the staged tree (the sequencer uses -n), not as a commit-time hook (house precedent: the S81-09 rebase).
- D-4 The four rows are four test functions (not parametrised) so the node count is the ruled 220 (206 RED + 14 gate rows); a first parametrised draft (12 nodes, 22 in the file) ran green once (g1rb-gaterows-pre) and was restructured before any mutant ran or anything was committed. A-M30's row also drives the real `_fetch_product_data` rating block (the scs harness COPIED from the RED file, never imported), so 'no jsonld_rating, the slot untouched' is pinned, not only the leaf's None.
- D-5 The docstring edit is one physical line (131 characters wide in the file, wider than its neighbours) so the diff stays a ONE-LINE change as ruled; the text: "Unlike ``robots_eval.can_fetch``, a ';' path param is kept (D14 picks one normalisation); same rule order (the longest matching".
- D-6 The base record covers the three G1 test files as untracked copies at eaccd550 (their RED state: 98 + 19 AssertionError rows and the gate-rows collection ERROR); the record's header says so, so a unit reusing it reads those nodes as the RED baseline, not as box noise.
- D-7 'the RED file sha after the pin rows' in the PR-body instruction is read as the gate-rows file (the only test file that gained rows); the three frozen RED files are unchanged and their blob hashes are restated.

## 9. Questions for the orchestrator
- Q1 RB-G1-2 (a): add an S81-G1 pointer sentence to the `**Feature Flags:**` line in a later docs pass (the S81-04 / 06 / 08b / 15 / 09 house pattern), or leave the block findable by grep only?
- Q2 The stored eaccd550 record serves the S81-10 rebase only if S81-10 rebases onto eaccd550; once G1 merges, main moves and LC-6 recomputes for the new sha (the per-file results can still be reused where the file set and the sha's bytes for those files are unchanged).

## 10. git status --short (end)
```
(empty)
```
- `git worktree list` has no S81-G1_rebase/wtb entry: yes
- PR body: C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_rebase\PR_BODY.md (24844 bytes, pure ASCII, no trailer; the orchestrator appends it)

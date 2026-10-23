# ST1 LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP): engineering adversary report

- Lens: engineering. Agent: adversary, Opus 5.5 (claude-opus-5-5). 2026-10-23 08:14-09:40 AST.
- Unit worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-st1`, branch `feature/s81-st1-usage-path-offloop`, HEAD verified `feb39dc08cf4b5fb2405a71d2a4d80d27812c695` at the start and at the end (`git status --short` empty both times; never edited).
- Scratch: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_adv_engineering` (`git worktree add --detach` at feb39dc0; removed at the end). Notes and logs: `.../scratchpad/ST1_ADV/eng_*` (this folder is case-insensitively the brief's `ST1_adv`).
- Inputs read: s81-common.txt (start + end), PLAN_S81 (Context, Standing constraints, M1 ST1, flip order), RULINGS_ST1 (whole), GATE_ST1 (whole), the spec sections 3 / 4 / 7 / 8 / 9 and line 345, the review corrections 4 / 9 / 10, the GREEN report, the PR body draft, GREEN's comm builder and lists, the RED base comm records. The correctness adversary's report was read only AFTER my own measurements (cross-references below are marked).

## Verdict: NOT_READY (0 blocking, 1 major, 8 minor)

The code and the flag-OFF identity hold on every gate I ran; the one major is the comm-set derivation under the union rule (the brief: "a missing file is a MAJOR"). It is procedural, closed by a measurement in this report (the four files are green at HEAD, so `comm -13` is empty by construction), and needs no code change.

## Hashes

| file | sha256 (bytes on disk in sc-s81-st1, end of run) |
|---|---|
| tests/test_s81_st1_usage_path_offloop.py | b5ba0bab8586d75ed5fcc21075f0f440d72c7e754350d4d28a2255f4fa8f8337 (116,678 B, LF; the committed blob is the same bytes) |
| same file, first 114,275 bytes | feb447667a1fd2f5d239b4ae4e0eb3a7ddba13644030bdcec2262800e7a05cc5 = the frozen RED sha: prefix byte-identical; the only addition is the GT-2 r31b block at EOF |
| app/utils/redis_offloop.py | 955e25e5ce9b1841a8649153851d7530f158afd69186e6cfdf796106125704e7 |
| app/services/usage_service.py | ec0492a1e1490e367034022af3b75778c06a838d4ceb312de946f924c53ab5fd |
| app/services/review_service.py | 5ec6eba6988cde626ba5f7cbceac178467110e61a858860cca92dc21222260e9 |
| CLAUDE.md | d5830ccf16e48086f98517ebea2d03399484c4b22df16e1646776b619510664e |

All equal the GREEN report's "after" column. (In a fresh autocrlf checkout the RED file is CRLF, sha 62c55f98...; the index blob is LF = b5ba0bab..., consistent with the repo convention.)

## Runs (every pytest through pyt.py; one of mine at a time; scratch worktree; flag unset unless stated)

- `[pyt] tag=st1eng-unit-off start=2026-10-23 08:26:41 end=2026-10-23 08:27:02 elapsed=21s bound=600s status=OK rc=0` 515 passed; `[hermeticity] sentinel checked 515 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- `[pyt] tag=st1eng-unit-on start=2026-10-23 08:27:28 end=2026-10-23 08:27:46 elapsed=19s bound=600s status=OK rc=0` (ENABLE_USAGE_PATH_OFFLOOP=true exported) 515 passed; hermeticity 515; netguard 0. PROVE-NOTHING as a separate gate: the file's autouse `_st1_env` fixture deletes the flag before every node (verified at the fixture), so this is the OFF run again; the ON evidence is inside the rows that set the flag (same finding as the correctness adversary's MIN-6).
- `[pyt] tag=st1eng-collect start=2026-10-23 08:28:41 end=2026-10-23 08:28:45 elapsed=5s bound=600s status=OK rc=0` (--collect-only; per-row counts below).
- `[pyt] tag=st1eng-ci-order start=2026-10-23 08:29:31 end=2026-10-23 08:30:33 elapsed=63s bound=1200s status=OK rc=0` GREEN's 31-file CI-order set, one process: 1502 passed; hermeticity 1502; `[netguard] blocked 2 attempt(s) from 2 node(s)` (the two test_paid_route_metering.py sentinel nodes of the base record).
- `[pyt] tag=st1eng-comm-04 start=2026-10-23 08:30:52 end=2026-10-23 08:32:16 elapsed=84s bound=1200s status=OK rc=0` 1722 passed, 1 skipped, 2 deselected; hermeticity 1722; netguard 20 / 8 (= base record base_04 and GREEN head_04).
- `[pyt] tag=st1eng-comm-05 start=2026-10-23 08:32:53 end=2026-10-23 08:33:51 elapsed=57s bound=1200s status=OK rc=0` 1049 passed, 10 skipped, 14 deselected, 35 xfailed; hermeticity 1094; netguard 65 / 21 (= base_05 and head_05).
- `[pyt] tag=st1eng-comm-02 start=2026-10-23 08:34:39 end=2026-10-23 08:35:08 elapsed=29s bound=1200s status=OK rc=0` 579 passed, 4 deselected; hermeticity 579; netguard 2 / 2 (= base_02 and head_02).
- `[pyt] tag=st1eng-pins-readers start=2026-10-23 08:35:49 end=2026-10-23 08:37:20 elapsed=91s bound=1200s status=OK rc=0` 34 files: the source-scanning pins (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py), the two CLAUDE.md readers (test_ci_gates.py, test_behavior_dimension_translation.py), the migration / manifest / legal readers (test_migration_023 ... _044 (12 files), test_legal_docs_u8.py, _u8_d3c.py, _u8_polish.py, test_legal_disclosure_s77.py, test_legal_s78.py, test_sqlfluff_config.py, test_secret_scan_static.py) and the seven path readers missing from GREEN's set (MAJ-E1 / MIN-E6): 1526 passed, 10 deselected; hermeticity 1526; netguard 0.
- `[pyt] tag=st1eng-ci-order-on start=2026-10-23 08:39:59 end=2026-10-23 08:41:07 elapsed=69s bound=1200s status=FAIL rc=1` (flag exported) 9 failed, 1493 passed: exactly the nine nodes of CLAUDE.md limit (13) / the PR table (six test_s77_redis_offloop.py, two test_review_source_consult.py, one test_youtube_reviews_race.py).
- `[pyt] tag=st1eng-probe-reset start=2026-10-23 08:43:14 end=2026-10-23 08:43:18 elapsed=4s bound=600s status=OK rc=0` (my probe file, scratch only, removed after; 4 nodes; MIN-E1).
- Mutants: `[pyt] tag=st1eng-mut-EM1 start=2026-10-23 08:45:12 end=2026-10-23 08:45:23 elapsed=11s bound=600s status=OK rc=0`; `[pyt] tag=st1eng-mut-EM2 start=2026-10-23 08:45:24 end=2026-10-23 08:45:31 elapsed=7s bound=600s status=FAIL rc=1`; `[pyt] tag=st1eng-mut-EM3 start=2026-10-23 08:45:32 end=2026-10-23 08:45:39 elapsed=7s bound=600s status=FAIL rc=1`; `[pyt] tag=st1eng-mut-EM4 start=2026-10-23 08:45:40 end=2026-10-23 08:45:52 elapsed=12s bound=600s status=OK rc=0`.
- Hook files: `[pyt] tag=st1eng-hook-collect start=2026-10-23 08:37:51 end=2026-10-23 08:38:00 elapsed=9s bound=600s status=OK rc=0` (327 nodes: 62 / 30 / 114 / 121); `[pyt] tag=st1eng-hook-a start=2026-10-23 08:46:47 end=2026-10-23 08:56:40 elapsed=593s bound=590s status=TIMEOUT rc=124` (test_precommit_hook.py + _round2.py, 17 of 92 nodes done, about 35 s per node under sibling load); re-run once alone: `[pyt] tag=st1eng-hook-a2 start=2026-10-23 08:58:17 end=2026-10-23 09:28:24 elapsed=1807s bound=1800s status=TIMEOUT rc=124` (about 45 of 92 nodes passed, 0 failed, before the bound; no orphan process left).
- Static: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the three app files + the RED file: `All checks passed!`; `py_compile` rc 0 on the same four; a wider `--select F,B,E7,E9,W6` shows the same two pre-existing F401 in review_service.py at base and head (nothing new); `git diff --check 95cf6f86 HEAD` clean.
- Box: `node -e 0` 0.81 s / 1.16 s; a sibling session's pytest (not mine, other cwd) was running during the hook gates and left alone.

## Diff hygiene (measured)

- `git diff --stat 95cf6f86 HEAD`: 5 files, +2561 / -15 (CLAUDE.md 7, review_service.py 73, usage_service.py 88, redis_offloop.py 30, the new RED file 2378); no whole-file diff.
- Line endings (scratch checkout): redis_offloop 141/141 CRLF, usage_service 830/830, review_service 1157/1157, CLAUDE.md 943/943; the index blobs carry 0 CR (LF index, CRLF working copy, as the repo convention).
- Non-ASCII: base == head for the three app files (0 / 105 / 251 bytes); CLAUDE.md 3961 -> 3952 bytes (-9 = the two em dashes and one arrow of the rewritten M13-05 line, GREEN deviation 3). Added lines of the diff: 2561, 0 with a byte > 127. Added-line sweep (@gmail, +973, 8-digit runs, sk-/eyJ/AKIA/xox, credentialed URL, PEM): 0 hits.
- The 15 removed lines are all moved or rewritten in place: usage_service 8 (the bonus read moved up in get_usage_status; the two counter reads + comment + blank of each function moved into the OFF tail, R-ST1-3), review_service 5 (the import line extended; the L1 read and three `set_cached` lines wrapped in the flag branch), CLAUDE.md 2 (the two 8.2 in-place rewrites).
- Imports: usage_service gains one line (`from app.utils.redis_offloop import run_redis_offloop_pool, usage_path_offloop_enabled`; spec 3 allowed two, one dropped with run_db_offloop); review_service extends the existing redis_offloop line (spec 3) and adds stdlib `import copy` (not listed in spec 3, but required by R-ST1-4's deepcopy snapshot; stdlib; accepted); redis_offloop.py adds no import (stdlib-only pin intact). No import cycle (redis_offloop is a stdlib leaf).
- None of the five files is in `.github/black-clean-paths.txt` (55 rows); no black step applies.
- Rebase predictability (`git merge-tree --write-tree --merge-base 95cf6f86`): onto d0e24c32 and onto 84c861f6 the only conflict is CLAUDE.md (the expected anchor union after the B3 row); review_service.py auto-merges with D03 into a clean import-block union (verified in the merged tree: the ST1 redis_offloop line followed by D03's deny_hosts line).

## Comm set (re-derived; compared with GREEN's 152)

GREEN's list (`ST1_green/comm/comm_list.txt`, sha256 prefix 3ef806f92cfb8706, 152 files) is byte-identical to the RED base list (same prefix, 152). My independent derivation (`eng_comm.py`: module and symbol grep for the edited modules / symbols, plus every test that reads app/ by path in any form: path literals, `"app"` path joins, `Path(<module>.__file__)` with a read, ast.parse / getsource, walkers) found:

- every whole-tree walker (rglob / glob / os.walk / iterdir / listdir / ls-files) is in GREEN's set except the four hook files (excluded by rule) and the migrations helpers;
- GREEN's set contains 40 files my narrower grep did not pick (its /health, usage_status, consume / refund symbol and globber sources): superset there;
- files mine selects and GREEN's does not: 10 reference only the orchestrator's `svc._get_reviews` (a different symbol, patched, review_service never reached: not required), 2 call youtube_service directly (not required), and 7 READ app/ BY PATH (MAJ-E1 / MIN-E6).

## Findings

### MAJ-E1 (comm set, union rule): four source-reading tests missing from GREEN's comm set

The union rule includes "every test that walks or reads app/ by path". GREEN's builder catches that class only through string-literal regexes (`"app/(services|api|utils|middleware)`, `"app" /`, rglob, os.walk, inspect.getsource, getsourcefile), so it misses the `Path(<module>.__file__).read_text()` form. Four tests read app source that way and are in neither the comm set, the pin set nor the CI-order set:

- tests/test_iherb_page_currency_signal.py (`PRICE_SERVICE_SRC = Path(price_service.__file__)`, ast.parse at :478 / :562)
- tests/test_nasser_adapter.py (`Path(ps.__file__).read_text()` at :206 / :242)
- tests/test_s70_prefetch_gather_retrieved.py (`ast.parse(pathlib.Path(scs.__file__).read_text())` at :213)
- tests/test_u3c_referral_push_name.py (`ast.parse(Path(push_service.__file__).read_text())` at :211)

Exposure: nil by construction (each reads a module ST1 does not edit, and a `__file__` reader always names its module, so a unit that edits that module catches it by the module grep). Measured: all four green at HEAD in `st1eng-pins-readers` (head FAILED set empty, so `comm -13` is empty whatever the base set). Fix (no code change): add the four files to the unit's comm record with this run as the head measurement, and add the `Path\(\s*[\w.]+\.__file__\s*\)` form to the shared comm builder (RED and GREEN reuse it) so later units do not repeat the gap. Classified MAJOR only because the brief says a missing file is a MAJOR; the orchestrator may rule it closed by this measurement.

### Minors (documentation / hygiene rulings for the orchestrator)

- MIN-E1 (documentation truth, measured; independently found by the correctness adversary as MIN-2): CLAUDE.md row limit (8) and PR body limit 8 say two concurrent first reads after a past `reset_at` "can both issue the reset UPDATE under ON (measured 2 vs 1 OFF)". False at these bytes. Probe (`eng_probe_reset.py`, two concurrent `get_usage_status`, a STATEFUL fake users row whose UPDATE rolls reset_at forward, the real `_maybe_reset_referral_bonus`): UPDATEs = 1 / 1 (ST1 off / on) with ENABLE_SYNC_DB_OFFLOAD OFF and 2 / 2 with it ON; bodies equal in all four (`eng_probe_reset_out.jsonl`). The 2-vs-1 figure was the review's probe G of the dropped run_db_offloop / blocking-twin design (review refuted claim 10). Rewrite in place: the double UPDATE is a property of ENABLE_SYNC_DB_OFFLOAD (base included), not of ST1. Limit (7)'s "with a past reset_at a second reset UPDATE" is likewise reachable only with ENABLE_SYNC_DB_OFFLOAD ON (with it OFF the tier task completes its select + UPDATE in its first step, before any pool future can fail); "can" keeps it true, a qualifier would make it exact.
- MIN-E2 (PR body truth): the defect table cites "the slow Home / Paywall mounts behind MYEZ-015". MYEZ-015 is the Scan-path delay ("~40 s scan with a silent loader", S80 DEFECT_LEDGER row; QA audit heading at QA_UX_AUDIT_2026-10-18.md:100), not the Home / Paywall mounts; ST1 has no MYEZ id in either defect ledger (the S81 ledger row ST1 names none). Inherited verbatim from the spec (ST1_UNIT_SPEC.md:345). Cite the prod_evidence finding (findings[7]: usage_status p50 4,164 ms; 4,266 ms with child spans under 0.8 s; that part is verified) and drop or correct the MYEZ id.
- MIN-E3 (CLAUDE.md, principle 5 in-place truth): the S77 `ENABLE_PRICE_PATH_REDIS_OFFLOOP` row still says the /health `redis_offloop_pool` key "appears only once the pool exists (the flag was ON at least once in this process)"; with ST1 the same pool is built by `run_redis_offloop_pool` with the S77 flag OFF (r26, ST1 limit 11). Rewrite the parenthetical to name either flag; S77 limit (3)'s FIFO list could gain the usage GETs and the reviews writes (the ST1 row's limit 3 already says it).
- MIN-E4 (unpinned documented claim; mutant EM1 SURVIVED): the `fire_and_forget` label `reviews.l1_write` (named in the CLAUDE.md row and the PR body, and the drain's attribution for a straggler) is pinned by no row: renaming it keeps r19 / r21 / r22 / r31 / r31b / r32 green. Same class as the correctness adversary's MIN-4 (the registry membership); one assertion in r19 or r21 on the task name and `_BACKGROUND_TASKS` membership closes both.
- MIN-E5 (unpinned defensive arm; mutant EM4 SURVIVED, equivalent in practice): `await asyncio.wait([prev])` replaced by `await prev` keeps every row green. Equivalent today: `_write` swallows every Exception, so `prev` never raises, and nothing cancels the task except interpreter-exit cleanup; with `await prev` a cancelled `prev` would drop the next write. Document as equivalent or pin with a cancelled-prev row.
- MIN-E6 (comm set, not required by the clause structure): three more tests read app/ by path but not source (test_legal_docs_u8_d3c.py and test_legal_docs_u8_polish.py read app/legal/*.md; test_content_blocklist_arabic_parity.py reads app/data/content_blocklist.json); the separate "migration / manifest / legal readers when legal text changes" clause implies they are not required here (GREEN's set nevertheless includes three other legal readers). Ran green in `st1eng-pins-readers`. For consistency of the shared builder only.
- MIN-E7 (wording): CLAUDE.md row "**Effect ON:** `get_usage_status` / `check_usage_allowed` (zero production callers) ..." reads as if both had no caller (`usage_routes.py:3/:12` calls `get_usage_status`; only `check_usage_allowed` has none, grep of app/ and scripts/); "No new response key, no new code" means no new error code (the PR body says "no new status or code"). PR body: "the non-awaited design of R-ST1-4 adds the last four" is off by one row against its own table (the four added nodes are `test_parity_s6[nocache]` plus the three consult / YouTube nodes; the table's last four include `test_off_no_new_suspension_on_hit_paths[s6_l1_hit-off]`, one of the review's five). The commit message calls the flag-OFF identity rows "RED rows r08/r09/r12/r13/r16/r23/r25b/r27/r34/r35"; all but r35 are PIN rows (fix at the squash / PR).
- MIN-E8 (row classification): the PR table lists r31b under PIN rows, while r31b sets the flag itself and fails at base by design (it asserts the writes land after the response on pool threads); GT-2 called it a PIN, the PR text after the table discloses it, and the house definition (PIN = green at base) does not fit. Annotate the table cell ("PIN by GT-2; fails at base") or move it to the RED column.

### Prove-nothing rows

- The "unit file ON (flag exported)" gate (GREEN `st1green-unit-on`, mine `st1eng-unit-on`): the autouse fixture deletes the flag, so it re-measures OFF (correctness MIN-6). The ON path in CI lives only inside the RED file's rows that set the flag; every existing pin that would see an ON regression runs only with the flag exported (as limit 13 says).
- GREEN's "pre-commit hook passed on the commit (38 s)" cannot be re-measured from the bytes; the hook test files are NOT MEASURED here (below).

## Claims checked against the bytes (hold unless a minor says otherwise)

- PR table node counts: every row count matches the collection (r02 16, r03a 2, r05 88, r06 2, r07 2, r08 22, r09 88, r10 88, r12 88, r13 4, r14 4, r15 2, r16 18, r17 4, r19 2, r20 2, r23 6, r24 2, r25b 28, r26 2, r27 8, r28b 2, r30 4, r31 2, r31b 2, r33 2, r35 11, the rest 1); RED 232 + PIN 281 + r31b 2 = 515.
- r25b's 28 digests include consume_comparison_credit, _refund_credit_sync, refund_comparison_credit, every key helper (_daily_key, _monthly_key, _previous_daily_key, _previous_monthly_key), the two gathered helpers, `_atomic_consume*`, `_bump_counters*`, TIER_LIMITS, db_offload.run_db / sync_db_offload_enabled and the S77 reader / pool functions: the CLAUDE.md "AST-digest pinned" sentence holds.
- Line counts 141 / 830 / 1157 / 943 CRLF, non-ASCII unchanged, the comm list sha prefix 3ef806f92cfb8706 = RED's, chunk 01 base netguard 57 / 34 (base_01.log): the PR body numbers hold.
- Flag reader per call, first statement of both public functions, one read per get_reviews call; run_redis_offloop byte-unchanged; db_offload.py untouched (r25c and the diff): hold.
- The two gathered helpers swallow their own exceptions (usage_service.py `_get_user_tier_info` / `_get_active_referral_bonus` except arms), so in practice the ON `except Exception` fires on a pool dispatch failure only; a compute-body exception would also be logged as "dispatch failed" and re-raised by the inline fallback (the correctness adversary's MIN-3; same response).
- CLAUDE.md placement: the ST1 row is line 479, directly after the SESSION 80 B3 row (476-477), before `## Tests` (482): GT-8 holds. The row carries every "Stated limit that stays" of RULINGS_ST1 (L1, L2, L3, L5, L6, L9, L10, L11 restated, L12, L13, L14, the correction-4 duplicate read, the R-ST1-1 production shape) plus GT-5 (12) and L8 (13); the canary has no /health p95 claim.
- The prod-evidence sentence (usage_status p50 4.2 s, child spans under 0.8 s): prod_evidence.json findings[7].evidence[0..1] hold.
- "read on every Home and Paywall mount by build 3": `usageService.ts:45` + the Paywall's per-mount fetch (CLAUDE.md #255) hold.
- Limit (13)'s nine nodes: exact (measured `st1eng-ci-order-on`).
- `check_usage_allowed` has no production caller; `get_usage_status` has one (`usage_routes.py`).

## Mutants applied (scratch worktree, `.qa-mutation.lock`, byte copy -> exact-once edit -> pyt.py -k -> restore -> sha256 compare; all four restores sha-identical, lock removed)

| id | file | mutation | rows | result |
|---|---|---|---|---|
| EM1 | review_service.py | fire_and_forget label `reviews.l1_write` -> `reviews.l1` | r19, r21, r22, r31, r31b, r32 (10 nodes) | SURVIVED (MIN-E4) |
| EM2 | usage_service.py | get_usage_status WARNING says fn=check_usage_allowed | r14, r15 | KILLED by r14 (AssertionError on the template) |
| EM3 | redis_offloop.py | run_redis_offloop_pool default durable=True (reads shielded) | r03 | KILLED by r03c (AssertionError) |
| EM4 | review_service.py | `await asyncio.wait([prev])` -> `await prev` | r19, r21, r22, r31, r31b, r32 | SURVIVED (MIN-E5, equivalent in practice) |

(The full mutation table is the correctness lens: GREEN's 40 and the correctness adversary's 31 runs.)

## Answers to GREEN's questions (engineering view)

- Q2 (GT-5 comments on r06 / r07 / r31): a RED edit; r31b's comment plus row limit (12) and PR limit 12 carry the rule; no engineering need to touch frozen rows.
- Q3 (rebase): merge-tree onto 84c861f6 and d0e24c32: CLAUDE.md anchor conflict only; review_service.py auto-merges with D03 (import union).
- Q4 (black-clean-paths): do not add the RED file (frozen and not black-clean; reformatting it would change the frozen bytes); none of the edited app files is listed either.
- Q1 / Q5: correctness rulings (the M40 guard; limit 14 is true and optional in the row).

## NOT MEASURED

- The pre-commit hook test files: test_precommit_hook.py + _round2.py timed out at 590 s (17 / 92 nodes, about 35 s per node under sibling load) and the once-alone re-run is recorded above (TIMEOUT again at 1800 s: NOT MEASURED, about 45 / 92 passed and 0 failed before the bound); test_precommit_hook_phase_b.py and _phase_b_round2.py (235 nodes) were not run within the budget. ST1 edits no file under .githooks and GREEN did not run them either.
- Comm chunks 00, 01, 03, 06 (GREEN's head records; I re-ran 02, 04, 05).
- Production / Railway / Supabase: never touched; no .env read or copied.

## Deviations

- The hook re-run used the background runner (bound 1800, the brief's hook bound) because the Bash tool caps a foreground call at 600 s; no other pytest of mine ran while it ran.
- `git merge-tree --write-tree` (rebase dry run) writes unreferenced objects into the shared object store; no ref, index or worktree changed.
- One merge-tree output was first written to /tmp and deleted at once; the kept copy is in the notes folder.

## Final state

- sc-s81-st1: HEAD feb39dc08cf4b5fb2405a71d2a4d80d27812c695, `git status --short` empty, file shas as in the table.
- Scratch worktree: removed with `git worktree remove --force` (absent from `git worktree list`, directory gone; it held no .env, no junction, no lock); my probe file lived only there.

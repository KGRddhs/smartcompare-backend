# ST1 GREEN report: LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP)

- Unit ST1, lane B for files (R-ST1-5). Agent: GREEN, Opus 5.5 (claude-opus-5-5). 2026-10-23 05:05-07:00 AST.
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-st1`; branch `feature/s81-st1-usage-path-offloop` cut from base 95cf6f864b4e70980ca191daa064c0118e223c13; GREEN commit HEAD `feb39dc08cf4b5fb2405a71d2a4d80d27812c695` (one commit, through the pre-commit hook, not pushed, not rebased).
- Inputs read in full: scripts/s81-common.txt (re-read at the end: the 06:24 revision names D03 #368 merged = origin/main 84c861f6), PLAN_S81 (context, standing constraints, VERIFY corrections, M1 ST1, flip order), RULINGS_ST1 (whole), GATE_ST1 (whole), spec e4830eb3, review 058677bf, ST1_RED_REPORT.md / .json, ST1_red/proto.diff.
- Notes folder: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_green/` (notes.md, every log, mutants_green.py, mutate_green.py, mut_results.jsonl, mut_table.md, mut_pyt_lines.txt, comm/, PR_BODY.md). Before copies + SHA256SUMS: `.../scratchpad/ST1_green_before/`.

## Files (sha256 of the bytes on disk = the committed working copy)

| path | before | after | numstat |
|---|---|---|---|
| app/utils/redis_offloop.py | 31d36e39286b5fe4e06e01f75d9735c0b9b4008b25c7e5bcffa088d4eaa2d4a8 | 955e25e5ce9b1841a8649153851d7530f158afd69186e6cfdf796106125704e7 | +30 -0 |
| app/services/usage_service.py | e00584adff64b9a878f23c7d61db77c7df56174131180ef77668e7d79931992d | ec0492a1e1490e367034022af3b75778c06a838d4ceb312de946f924c53ab5fd | +80 -8 |
| app/services/review_service.py | ab6979ece0bac60c9997ddb55d052bd03a7255e1924fe54cf86219cb0aec3931 | 5ec6eba6988cde626ba5f7cbceac178467110e61a858860cca92dc21222260e9 | +68 -5 |
| CLAUDE.md | cf89f79567a7157a5d46b4fbed0b98b1bb5ede5527d8ff8ec843bfef804d2093 | d5830ccf16e48086f98517ebea2d03399484c4b22df16e1646776b619510664e | +5 -2 |
| tests/test_s81_st1_usage_path_offloop.py | feb447667a1fd2f5d239b4ae4e0eb3a7ddba13644030bdcec2262800e7a05cc5 (frozen RED) | b5ba0bab8586d75ed5fcc21075f0f440d72c7e754350d4d28a2255f4fa8f8337 | +2378 (new file) |

`app/utils/db_offload.py` untouched (a61545c8..., R-ST1-1). RED file: the frozen 114,275 bytes are a byte-identical prefix of the new file; the only addition is the r31b block at EOF (2,403 bytes, 0 bytes > 127, LF; GT-2). Line endings: the three app files and CLAUDE.md CRLF on every line (141 / 830 / 1157 / 943), non-ASCII totals unchanged (0 / 105 / 251; CLAUDE.md -9: see deviation 3); added lines of `git diff` 0 bytes > 127; added-line sweep 0 hits. `git status --short` after the commit: empty.

## Implementation (symbols at HEAD)

- `redis_offloop.py:119 usage_path_offloop_enabled`, `:126 run_redis_offloop_pool` (after `run_redis_offloop`, which is unchanged; module docstring gains one paragraph).
- `usage_service.py:17` one import line; `:619 _usage_reads_offloop` (keys on the loop; reads list; GT-6 close on a synchronous raise; one gather); `:650 check_usage_allowed` (flag fork first, then the base reads; lifetime-free OFF calls the body with 0, 0); `:689 _usage_allowed_body` (the base compute in place); `:768 get_usage_status` (flag fork first, then the base reads); `:792 _usage_status_body` (the base compute in place, base key order).
- `review_service.py:8 import copy`; `:21` import union (`run_redis_offloop, run_redis_offloop_pool, usage_path_offloop_enabled`); `:664 _reviews_l1_write_offloop` (deepcopy snapshot on the loop, guarded; fire_and_forget task `reviews.l1_write` waits `prev` inside the task, durable pool write, dispatch failure logged by type and swallowed); `get_reviews :722` flag read once; ON read via the pool; the persist block keeps `if not offloop: set_cached(...)` then the base save scheduling then `if offloop: l1_write = ...`; the two re-cache sites `if offloop: chained write else: base set_cached`. Four direct `set_cached` calls and the one `run_redis_offloop(get_cached, ...)` remain in `get_reviews` (S77 inventory + r25a).

## Runs (every pytest through pyt.py, one at a time)

- `[pyt] tag=st1green-unit-off start=2026-10-23 05:16:53 end=2026-10-23 05:17:16 elapsed=24s bound=600s status=OK rc=0` 515 passed; `[hermeticity] sentinel checked 515 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- `[pyt] tag=st1green-unit-on start=2026-10-23 05:17:42 end=2026-10-23 05:18:10 elapsed=28s bound=600s status=OK rc=0` (ENABLE_USAGE_PATH_OFFLOOP=true exported) 515 passed; hermeticity 515; netguard 0.
- `[pyt] tag=st1green-r14-werror start=2026-10-23 05:18:24 end=2026-10-23 05:18:49 elapsed=25s bound=600s status=OK rc=0` (-k "r14 or r15 or r19b" -W error::RuntimeWarning -W error::pytest.PytestUnraisableExceptionWarning) 7 passed; hermeticity 7; netguard 0.
- `[pyt] tag=st1green-pins-off start=2026-10-23 05:23:38 end=2026-10-23 05:24:30 elapsed=51s bound=1200s status=OK rc=0` (28 files: spec 4.2's 25 + test_w4_13_flag_off_ledger.py + test_w4_13_measurement_truth.py + test_shutdown_drain.py) 908 passed; hermeticity 908; `[netguard] blocked 2 attempt(s) from 2 node(s)` (test_paid_route_metering.py::test_camera_success_consumes_once_and_never_refunds and ::test_url_compare_saves_history_with_input_type_url, sentinel neutralized.supabase.invalid:443 = base 1.10).
- `[pyt] tag=st1green-pins-on start=2026-10-23 05:24:44 end=2026-10-23 05:25:34 elapsed=51s bound=1200s status=FAIL rc=1` (flag exported) 9 failed / 899 passed; hermeticity 908; netguard 2 (same pair). The 9 = L8 measured at HEAD (list in PR_BODY.md "Deliberate pin changes").
- `[pyt] tag=st1green-metering-on start=2026-10-23 05:26:30 end=2026-10-23 05:26:42 elapsed=12s bound=600s status=OK rc=0` (ENABLE_PAID_ROUTE_METERING=true exported) 21 passed; hermeticity 21; netguard 2 (same pair).
- `[pyt] tag=st1green-claude-readers start=2026-10-23 05:29:17 end=2026-10-23 05:31:16 elapsed=118s bound=600s status=OK rc=0` (34 CLAUDE.md readers) 1289 passed, 9 skipped, 11 deselected, 35 xfailed; hermeticity 1333; `[netguard] blocked 81 attempt(s) from 27 node(s)` (sentinel / egress baseline class).
- Mutants: 40 `[pyt] tag=st1green-mut-M01..M40` lines in `mut_pyt_lines.txt` (37 status=FAIL rc=1, 3 status=OK rc=0: M21, M32, M40; no TIMEOUT), e.g. `[pyt] tag=st1green-mut-M38 ... status=FAIL rc=1`.
- Comm chunks 00-06 (152 files; lines in PR_BODY.md): 00 739 passed (hermeticity 739, netguard 18/6), 01 1037 passed (1037, 54/33), 02 579 passed (579, 2/2), 03 1063 passed + 2 ERROR (1066, 2/2), 04 1722 passed (1722, 20/8), 05 1049 passed (1094, 65/21), 06 28 passed (28, 0/0).
- `[pyt] tag=st1green-ci-order start=2026-10-23 06:51:17 end=2026-10-23 06:52:34 elapsed=78s bound=1200s status=OK rc=0` (31 files sorted) 1502 passed; hermeticity 1502; netguard 2.
- `[pyt] tag=st1green-unit-head start=2026-10-23 06:54:50 end=2026-10-23 06:55:13 elapsed=23s bound=600s status=OK rc=0` (at the commit) 515 passed; hermeticity 515; netguard 0.

## Counts

- Unit file: 515 nodes = 232 RED (RED gate) + 281 PIN + 2 r31b (GT-2, appended). All 515 green ON and OFF.
- Mutants: 40 run, 37 KILLED (36 AssertionError in the call phase; M39 under -W error on r14 per GT-6, ExceptionGroup), 3 SURVIVED: M21 (EQUIVALENT by R-ST1-7), M32 (EQUIVALENT by GT-1), M40 (the snapshot guard removed; unpinned defensive arm, for a ruling). Table: `ST1_green/mut_table.md`. Every restore sha256-identical; lock created and removed; final shas = the committed bytes.
- Comm set: 152 files / 7 chunks; HEAD FAILED/ERROR set = base set (the two cold-tiktoken test_prompt_truth ERROR nodes); branch-only-NEW EMPTY.

## Deviations

1. Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, not the task's "Claude Fable 5.1": the common brief requires the committing agent's own model and forbids claiming another; this agent is Opus 5.5.
2. r31b is one row with two parametrized nodes (s77_off / s77_on, as r31); its `# timing row` comment is on r31b only: r06 / r07 / r31 carry none in the frozen file and GREEN may not edit existing rows (GT-2 / GT-10), so GT-5's comment on those three is left for the orchestrator.
3. CLAUDE.md line 383 (the M13-05 row, rewritten in place per spec 8.2): its three pre-existing non-ASCII characters (two em dashes, one arrow) were rewritten as ASCII (`-`, `->`) so the spec 7.1 added-line gate reads 0 bytes > 127.
4. The spec 8.2 rewrite text was adapted to R-ST1-1: the usage functions' Supabase reads already go through run_db, so the rewrite says the counter GETs and the reviews L1 calls move under ST1; dated 2026-10-23 (the GREEN date) instead of 2026-10-22.
5. L8 measured at HEAD = 9 nodes (the review's 5 + `test_parity_s6[nocache]` + the three consult / YouTube persist-before-consult pins), a consequence of the non-awaited write design (R-ST1-4); recorded in the CLAUDE.md row limit (13) and the PR body; no pin edited.
6. Mutant batches: the Bash tool caps a foreground call at 600 s, so batch 1 (M01-M14) was moved to the background by the tool and batch 2 (M15-M27) was launched in the background; each mutant still ran as ONE bounded pyt.py process and no other pytest of this agent ran concurrently (batches 3-4 and every other gate ran in the foreground).
7. GREEN-only code beyond the prototype: the GT-6 close loop in `_usage_reads_offloop` (pinned by M39 under -W error) and a try/except around the snapshot deepcopy in `_reviews_l1_write_offloop` (parity with the base `set_cached`, which swallows its own errors; unpinned, M40).
8. PR body stated limit 14 (cross-request write order for one reviews key) is not in the CLAUDE.md row.

## Questions for the orchestrator

- Q1 M40: keep the snapshot guard and add a pin row in the fix round, or drop the guard (a deepcopy failure would then fail the reviews leg where base swallows)?
- Q2 GT-5: allow a hygiene edit adding `# timing row` comments to r06 / r07 / r31 (frozen rows), or rule that r31b's comment plus the CLAUDE.md / PR limit suffice?
- Q3 Rebase: the updated common brief names origin/main 84c861f6 (= + #368 D03); the task names d0e24c32. D03 edits `review_service.py` (import block) and CLAUDE.md (row after the B3 row): expected unions at the rebase.
- Q4 The RED file is not black-clean (`black 26.5.1 --check`: would reformat) and is not in `.github/black-clean-paths.txt` (not on this unit's change list); D03 added its RED file there. Rule whether ST1 should.
- Q5 Limit 14 into the CLAUDE.md row in the fix round?

## NOT MEASURED

- Nothing timed out. Not run: the pre-commit hook test files (no .githooks change); the comm set with the flag exported (only the 28-file pin set was measured ON); production / Railway / Supabase (never touched).
- Box note: `node -e 0` took 2.95 s at 05:52 while a sibling S81-03 adversary ran hook tests (tag s03adve-hook-notdash; not this agent's, left alone); mutant runs slowed from about 23 s to 124 s at that time.

## Final state

- `git status --short`: empty; HEAD feb39dc08cf4b5fb2405a71d2a4d80d27812c695; no `.qa-mutation.lock`; no pytest process with an st1green tag alive.

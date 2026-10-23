# ST1 FIX1 report: LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP), fix round 1

- Unit ST1, fix round 1 per `specs/RULINGS_FIX1_ST1.md` (F1-1..F1-10). Agent: fix agent, Opus 5.5 (claude-opus-5-5). 2026-10-23 09:37-10:40 AST.
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-st1`, branch `feature/s81-st1-usage-path-offloop`. Start HEAD `feb39dc08cf4b5fb2405a71d2a4d80d27812c695` verified, `git status --short` empty, RED file sha `b5ba0bab8586d75ed5fcc21075f0f440d72c7e754350d4d28a2255f4fa8f8337` re-hashed = GREEN / both adversaries.
- New HEAD: `e0ffed64986a69a9d33b54f43f579c8d84ba5b42` (ONE commit through the pre-commit hook, `git add <paths>` + `git commit -m ... -- <paths>`, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; no push, no rebase, no stash). `git status --short` after the commit: empty.
- Notes folder: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_fix1/` (notes.md, rows_f1.py.txt, mutants_f1.py, mutate_f1.py, mut_results.jsonl, mut_*.log, mut_exc_*.jsonl, run_chunk.py, comm/head_*.log + head_*_failed.txt + base_failed_ids.txt, pyt_lines.txt, before/ byte copies + SHA256SUMS.json, PR_BODY.md).
- Inputs read: s81-common.txt (start and end), PLAN_S81 (Context, Standing constraints, M1 ST1, flip order), RULINGS_ST1, GATE_ST1, RULINGS_FIX1_ST1, ST1_ADV1_correctness.md, ST1_ADV1_engineering.md, ST1_GREEN_REPORT.md, GREEN PR_BODY.md, GREEN mutation harness.

## Files (sha256 of the bytes on disk = the committed working copy)

| path | before (feb39dc0) | after (e0ffed64) | numstat |
|---|---|---|---|
| tests/test_s81_st1_usage_path_offloop.py | b5ba0bab8586d75ed5fcc21075f0f440d72c7e754350d4d28a2255f4fa8f8337 | 65088fa52c15ec652bcc2ac8bb340443883a05efaef8a5df846223cf1a7b7cbf (blob = working copy, LF) | +390 -0 |
| app/services/usage_service.py | ec0492a1e1490e367034022af3b75778c06a838d4ceb312de946f924c53ab5fd | 6940fddd7f6cb2cc3bb78d9569251b24aee5e08b315f6dfcc16abc9949e7c89d | +17 -8 |
| CLAUDE.md | d5830ccf16e48086f98517ebea2d03399484c4b22df16e1646776b619510664e | 8e30d0a4926083bf8d6c656bdb8a6fa5c88c1ccc71dee977540f42a6e1b595fd | +3 -3 |
| app/services/review_service.py | 5ec6eba6988cde626ba5f7cbceac178467110e61a858860cca92dc21222260e9 | unchanged | 0 |
| app/utils/redis_offloop.py | 955e25e5ce9b1841a8649153851d7530f158afd69186e6cfdf796106125704e7 | unchanged | 0 |

Bytes: the appended RED block is 18,025 bytes, LF, 0 bytes > 127; the old 116,678 bytes are a byte-identical prefix (and the frozen RED gate sha feb44766... is still the prefix of those). usage_service.py CRLF 839 / 839, non-ASCII 105 (unchanged). CLAUDE.md CRLF 943 / 943, non-ASCII 3952 (unchanged), added lines 0 bytes > 127. Added-line sweep (@gmail, +973, 8-digit runs, sk- / eyJ / AKIA / xox, PEM, credentialed URL): 0 hits. `git diff --check`: clean.

## RED step (rows appended; procedure: r37 fails at feb39dc0, r36 / r38-r41 PINs proven by mutants)

Rows (16 nodes): r36 `test_r36_reviews_on_write_respects_the_persist_guard[extraction_error|serper_failure|unified_timeout]` (F1-2), r37 `test_r37_compute_failure_is_not_a_dispatch_failure[get_usage_status|check_usage_allowed x null_lifetime|body_raises]` (F1-3), r38 `test_r38_reviews_write_task_is_in_the_drain_registry` (F1-4), r39 `test_r39_durable_pool_job_failure_is_retrieved_quietly[direct_cancelled|reviews_write]` (F1-5), r40 `test_r40_cancelled_previous_write_does_not_drop_the_next` (F1-6), r41 `test_r41_reviews_snapshot_failure_skips_the_write_and_keeps_the_response` (F1-7), r42 `test_r42_on_gets_are_in_flight_before_the_inline_supabase_reads[get_usage_status|check_usage_allowed]` (F1-8, timing row), r42b `test_r42b_partial_sync_dispatch_failure_closes_what_was_built[get_usage_status|check_usage_allowed]` (GT-6 under F1-8). Every row sets the flag itself (the autouse fixture deletes it).

- At the feb39dc0 code: `[pyt] tag=st1fix1-red-head start=2026-10-23 09:54:24 end=2026-10-23 09:54:51 elapsed=27s bound=600s status=FAIL rc=1` - 6 failed, 525 passed, 43 warnings (= GREEN's 43); `[hermeticity] sentinel checked 531 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`. The 6 = r37 x4 + r42 x2, each a call-phase AssertionError (exception-type plugin `st1_red_excinfo`: red_head_exc.jsonl). r37 failed on "a compute failure was logged as a dispatch failure"; r42 on "the counter GETs were dispatched after the inline Supabase reads" (GET t0 at +0.30 s vs the first Supabase read ending at +0.15 s). The 515 existing nodes and the 10 new PIN nodes passed.
- r05 / r07 / r12 / r13 (F1-8 re-record clause): none encodes the gather order (r05 sorted op multiset; r07 overlap of the reads; r12 / r13 consume / refund, untouched); not re-recorded, all green after the reorder. r06 / r07 / r31 untouched (F1-10).

## GREEN step (usage_service.py only)

- `_usage_reads_offloop`: the two `run_redis_offloop_pool(_get_redis_count, key)` appends first, then `_get_user_tier_info` / `_get_active_referral_bonus`; `daily_used, monthly_used, user_info, bonus = await asyncio.gather(*reads)`; returns `[user_info, bonus, daily_used, monthly_used]` (contract unchanged); docstring line added; GT-6 close loop unchanged (F1-8).
- `check_usage_allowed` / `get_usage_status` fork: `try: reads = await _usage_reads_offloop(user_id)` / `except Exception` WARNING (unchanged template) / `else: return _usage_*_body(*reads)` (F1-3). The flag read is still the first statement; the OFF path is byte-unchanged.

## Gates (every pytest through pyt.py, one at a time, foreground)

- `[pyt] tag=st1fix1-unit-off start=2026-10-23 09:56:21 end=2026-10-23 09:56:41 elapsed=20s bound=600s status=OK rc=0` 531 passed; hermeticity 531; netguard 0.
- `[pyt] tag=st1fix1-unit-on-exported start=2026-10-23 10:10:44 end=2026-10-23 10:11:09 elapsed=25s bound=600s status=OK rc=0` 531 passed; hermeticity 531; netguard 0 (flag exported for the runner call; neutralised by the file's autouse fixture, so this is the OFF measurement again - the ON evidence is inside the rows that set the flag).
- `[pyt] tag=st1fix1-werror start=2026-10-23 10:11:17 end=2026-10-23 10:11:23 elapsed=5s bound=600s status=OK rc=0` (-k "r14 or r15 or r19b or r37 or r39 or r40 or r41 or r42b", -W error::RuntimeWarning -W error::pytest.PytestUnraisableExceptionWarning) 17 passed; hermeticity 17; netguard 0.
- `[pyt] tag=st1fix1-pins-off start=2026-10-23 10:06:35 end=2026-10-23 10:07:26 elapsed=51s bound=1200s status=OK rc=0` (the 28-file 4.2 pin set incl. the W4-13 ledger pair, metering, shutdown drain) 908 passed; hermeticity 908; `[netguard] blocked 2 attempt(s) from 2 node(s)` (the two test_paid_route_metering.py sentinel nodes of the base record).
- `[pyt] tag=st1fix1-pins-on start=2026-10-23 10:07:50 end=2026-10-23 10:08:42 elapsed=52s bound=1200s status=FAIL rc=1` (flag exported) 9 failed / 899 passed: the same 9 nodes as CLAUDE.md limit (13) (six test_s77_redis_offloop.py, two test_review_source_consult.py, one test_youtube_reviews_race.py); hermeticity 908; netguard 2.
- `[pyt] tag=st1fix1-metering-on start=2026-10-23 10:11:36 end=2026-10-23 10:11:41 elapsed=5s bound=600s status=OK rc=0` (ENABLE_PAID_ROUTE_METERING=true) 21 passed; hermeticity 21; netguard 2 (same pair). Metering OFF is inside pins-off.
- `[pyt] tag=st1fix1-claude-readers start=2026-10-23 10:12:01 end=2026-10-23 10:13:58 elapsed=117s bound=600s status=OK rc=0` (the 34 CLAUDE.md reader files incl. tests/test_ci_gates.py and tests/test_behavior_dimension_translation.py, after the CLAUDE.md edits) 1289 passed, 9 skipped, 11 deselected, 35 xfailed; hermeticity 1333; `[netguard] blocked 81 attempt(s) from 27 node(s)` (= GREEN's record).
- `[pyt] tag=st1fix1-ci-order start=2026-10-23 10:14:35 end=2026-10-23 10:15:53 elapsed=78s bound=1200s status=OK rc=0` (31 files sorted, one process) 1518 passed (= 1502 + 16 new); hermeticity 1518; netguard 2.
- Comm set at HEAD (chunks 00-06 = the GREEN / RED 152 files, chunk 07 = the F1-1 four + tests/test_s75_fanout_identity.py (FY25); test_s75_fanout_starve.py (FY19) and test_s77_redis_offloop.py are in the 152):
  - `[pyt] tag=st1fix1-comm-head-00 start=2026-10-23 10:17:24 end=2026-10-23 10:18:00 elapsed=36s bound=1200s status=OK rc=0` 739 passed, 1 deselected; hermeticity 739; netguard 18 / 6 (base 18 / 6)
  - `[pyt] tag=st1fix1-comm-head-01 start=2026-10-23 10:18:12 end=2026-10-23 10:19:55 elapsed=103s bound=1200s status=OK rc=0` 1037 passed; 1037; 57 / 34 (base 57 / 34)
  - `[pyt] tag=st1fix1-comm-head-02 start=2026-10-23 10:19:57 end=2026-10-23 10:20:24 elapsed=27s bound=1200s status=OK rc=0` 579 passed, 4 deselected; 579; 2 / 2 (base 2 / 2)
  - `[pyt] tag=st1fix1-comm-head-03 start=2026-10-23 10:20:43 end=2026-10-23 10:22:22 elapsed=99s bound=1200s status=FAIL rc=1` 1063 passed, 26 skipped, 2 deselected, 1 xfailed, 2 errors (the cold-tiktoken pair); 1066; 2 / 2 (base 2 / 2)
  - `[pyt] tag=st1fix1-comm-head-04 start=2026-10-23 10:22:25 end=2026-10-23 10:24:33 elapsed=128s bound=1200s status=OK rc=0` 1722 passed, 1 skipped, 2 deselected; 1722; 20 / 8 (base 20 / 8)
  - `[pyt] tag=st1fix1-comm-head-05 start=2026-10-23 10:25:00 end=2026-10-23 10:25:56 elapsed=56s bound=1200s status=OK rc=0` 1049 passed, 10 skipped, 14 deselected, 35 xfailed; 1094; 65 / 21 (base 65 / 21)
  - `[pyt] tag=st1fix1-comm-head-06 start=2026-10-23 10:25:59 end=2026-10-23 10:26:04 elapsed=5s bound=1200s status=OK rc=0` 28 passed; 28; 0 / 0 (base 0 / 0)
  - `[pyt] tag=st1fix1-comm-head-07 start=2026-10-23 10:16:56 end=2026-10-23 10:17:09 elapsed=13s bound=1200s status=OK rc=0` 82 passed; 82; 0 / 0 (no base record)
  - HEAD failed set (union) = `tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence`, `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable` = the base record (`ST1_red/comm/base_failed.txt`); `comm -13` EMPTY. Chunk 07: HEAD failed set empty, so `comm -13` is empty by construction (MAJ-E1 closed: the four module-path readers green at HEAD).
- `[pyt] tag=st1fix1-unit-head start=2026-10-23 10:34:46 end=2026-10-23 10:35:19 elapsed=32s bound=600s status=OK rc=0` (at the commit) 531 passed; hermeticity 531; netguard 0.
- Static: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on redis_offloop.py, usage_service.py, review_service.py and the RED file: `All checks passed!`; `py_compile` rc 0 on the same four; the pre-commit hook passed on the commit (`All checks passed!`).

## Mutation table (fix-round bytes; `.qa-mutation.lock` held and removed; byte copies in mut_copies/; exact-once edits; whole unit file per mutant at bound 600; restore sha256-identical every time)

| id | file | mutation | result | killing rows |
|---|---|---|---|---|
| C02 | review_service | ON baseline L1 write moved out of the persist guard | KILLED 2 | r36[extraction_error, unified_timeout] |
| C16 | review_service | ON bypasses the persist guard (`if offloop or (...)`) | KILLED 2 | r36 |
| C06 | review_service | `asyncio.ensure_future` instead of `fire_and_forget` | KILLED 1 | r38 |
| EM1 | review_service | label `reviews.l1_write` -> `reviews.l1` | KILLED 1 | r38 |
| C07 | redis_offloop | durable branch of run_redis_offloop_pool drops `_retrieve_quietly` | KILLED 1 | r39[direct_cancelled] |
| EM4 | review_service | `await asyncio.wait([prev])` -> `await prev` | KILLED 1 | r40 |
| M40 | review_service | snapshot deepcopy guard removed | KILLED 1 | r41 |
| MB1 | usage_service | get_usage_status body back inside the dispatch try | KILLED 2 | r37 |
| MB2 | usage_service | check_usage_allowed body back inside the dispatch try | KILLED 2 | r37 |
| MG1 | usage_service | GET order reverted (helpers before the pool GETs) | KILLED 2 | r42 |
| M39 | usage_service | GT-6 close loop removed (whole file) | KILLED 2 | r42b |
| M39w | usage_service | GT-6 close loop removed, `-k "r14 or r42b"` under -W error | KILLED 2 | r42b (r14 4 / 4 GREEN under the new order) |
| M01 | redis_offloop | flag reader always True | KILLED 107 | r02 r09 r23 r26 r28 r28b r36 ... |
| C05n | usage_service | daily / monthly GETs swapped (new order) | KILLED 166 | r05 r06 r07 r08 r10 r17 r27 r35 ... |
| M10n | usage_service | four sequential awaits instead of one gather | KILLED 4 | r07, r15 |
| M15n | usage_service | get_usage_status fork without try/except | KILLED 3 | r14 (AssertionError); r42b also fails with the escaped RuntimeError |
| M17n | usage_service | flag hoisted (read once per process) | KILLED 46 | r09, r26, r28 |
| M19n | usage_service | check_usage_allowed ON returns _usage_status_body | KILLED 115 | r08 r10 r11 r17 r35 r37 r42 |
| M23n | usage_service | check_usage_allowed fork condition negated | KILLED 138 | r09 r10 r11 r14 r37 r42 r42b |

19 run, 19 KILLED, every kill by a call-phase AssertionError (M15n's r42b node additionally records the escaped RuntimeError; its r14 nodes are AssertionErrors). Every [pyt] line is in `pyt_lines.txt` (rebuilt from the runner ledger), e.g. `[pyt] tag=st1fix1-mut-C02 start=2026-10-23 09:58:40 end=2026-10-23 09:59:00 elapsed=20s bound=600s status=FAIL rc=1`, `[pyt] tag=st1fix1-mut-C07 start=2026-10-23 10:00:11 end=2026-10-23 10:00:37 elapsed=25s bound=600s status=FAIL rc=1`, `[pyt] tag=st1fix1-mut-MG1 start=2026-10-23 10:02:16 end=2026-10-23 10:02:38 elapsed=22s bound=600s status=FAIL rc=1`, `[pyt] tag=st1fix1-mut-M23n start=2026-10-23 10:31:54 end=2026-10-23 10:32:23 elapsed=30s bound=600s status=FAIL rc=1`. The other 35 GREEN mutants' target text is unchanged by this round (exact-once matches re-checked with GREEN's harness: only M10, M15, M17, M19, M23 no longer match, re-derived here as the n variants).

## Documentation (F1-9)

- CLAUDE.md, the ST1 row rewritten in place: header cites RULINGS_FIX1_ST1 F1-1..F1-10; Effect ON names `get_usage_status` as called by `usage_routes.py` and `check_usage_allowed` as the only one with no production caller; the GETs-first gather (F1-8) and the narrowed try (F1-3); a fix-round pins sentence (r36-r42b); "no new error code"; limit (7) qualified (the second reset UPDATE is reachable only with ENABLE_SYNC_DB_OFFLOAD ON); limit (8) rewritten (a property of ENABLE_SYNC_DB_OFFLOAD: 1 / 1 OFF, 2 / 2 ON, in both ST1 states); limit (12) adds r42; limit (13) re-measured at the fix-round commit plus the autouse-fixture sentence (the "unit file ON (flag exported)" wording); new limit (14) cross-request write order. The S77 row's `/health redis_offloop_pool` parenthetical names either flag (MIN-E3).
- PR body draft `ST1_fix1/PR_BODY.md`: the defect citation is the prod_evidence `usage_status` p50 4,164 ms finding (MYEZ-015 dropped; ST1 carries no MYEZ id); r31b in the RED column with its GT-2 note; the four-node sentence corrected (the review's five = the five S77 nodes other than test_parity_s6[nocache]; R-ST1-4 adds test_parity_s6[nocache] + the three consult / YouTube nodes); the row-class correction of the GREEN commit message (r08 / r09 / r12 / r13 / r16 / r23 / r25b / r27 / r34 are PINs; r35 RED); the gate sentence for the exported-flag run; limits 5 / 7 / 8 / 12 / 13 / 14; "no new status, no new error code"; the comm builder rule incl. the `Path(<module>.__file__)` module-path readers (F1-1); a fix-round table F1-1..F1-10. Pure ASCII except the 4-byte attribution line (as the D03 drafts).
- F1-10: the RED file is NOT in `.github/black-clean-paths.txt`; r06 / r07 / r31 untouched.

## Deviations (each with the reason)

1. Two rows beyond the named r36-r41: r42 (F1-8): no existing row encodes the gather order, so without it the gate's required GET-order mutant (MG1) would survive; r42b: with the GETs listed first, r14's sync-raise case raises on the first build and builds nothing, so M39 (the GT-6 close loop removed) passed r14 under -W error (measured, M39w: r14 4 / 4 green); r42b (the second dispatch raises after the first was built; all built coroutines must be CORO_CLOSED) restores the kill without -W error.
2. r36 carries the positive control the correctness adversary proposed (MIN-1 (c), the honest Serper-failure payload lands one L1 write and one L2 save, inline OFF and on the pool ON); r39 has two parts (direct_cancelled kills C07; reviews_write pins the type-only WARNING for an in-pool write failure); r41 pins the code's skip-with-WARNING branch (the ruling allowed a shallow-copy fallback or the skip).
3. r37 uses two raisers: the realistic NULL `lifetime_comparisons_used` and a patched body raising a synthetic RuntimeError; both functions.
4. The mutation set was widened to 19 (the 9 named F1 mutants + M39 / M39w + M01 + C05n + the 5 GREEN mutants whose exact text this round edited, re-derived).
5. The commit message carries the ruled subject verbatim plus one body paragraph and the trailer.
6. The `scripts/s81-common.txt` comm-set sentence and the shared comm builder (`ST1_red/comm_build.py`) are NOT edited by me (F1-1 assigns them to the orchestrator; sc-docs-70 is read-only for agents); the four files were added to this unit's comm record as chunk 07.
7. Mutants and gates ran in the real worktree in place (byte copies, lock), as GREEN did; no scratch worktree was created.

## Questions for the gate

- Q1: accept r42 / r42b as fix-round rows beyond r36-r41 (reasons in deviation 1)?
- Q2: M39 is now killed by r42b only (r14 no longer kills it under the GETs-first order, measured); acceptable, or should r14 gain a partial-raise case (a frozen-row edit)?
- Q3: r42 is a timing row (0.15 s per op; asserts both GET start times precede the end of the first inline Supabase read); GT-5 applies.

## NOT MEASURED

- The fix-round rows at base 95cf6f86 (the procedure measures them at feb39dc0).
- The comm set with the flag exported (only the 28-file pin set was measured ON).
- The pre-commit hook test files (no .githooks change).
- Production / Railway / Supabase: never touched; no .env read, copied or printed; no flag set outside one runner call.

## Final state

- sc-s81-st1: HEAD `e0ffed64986a69a9d33b54f43f579c8d84ba5b42` on `feature/s81-st1-usage-path-offloop`; `git status --short` empty; no `.qa-mutation.lock`; no pytest process of this agent alive.

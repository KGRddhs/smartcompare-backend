# S81-04 SPEND-BREAKER fix round 1: RE-VERIFIER report (lens: correctness, with the engineering items the fix rulings name)

| Header | Value |
|---|---|
| Unit | S81-04 SPEND-BREAKER, `ENABLE_LLM_SPEND_BREAKER` (lane B) |
| HEAD verified | `f1b29405c06e6b5e3e6a49992450e4353b61ef08` on `feature/s81-s04-spend-breaker` (sc-s81-s04), `git status --short` empty at start and end; 3 commits on `e1878dd8` (c4490e91, b5f29e35, f1b29405) |
| RED file re-hash | `tests/test_s81_s04_spend_breaker.py` = `d9bb55b5237f7dba9ecc06fdd273ef596f94f29e48670452720a32f8564bb7cd` (LF, 2,446 lines) at start and end = the task's figure; leaf `app/services/llm_spend_breaker.py` = `802cb806cbbbc9b39ab24092af3e867fbbcce8562c5f2959cb2dee05f26ee230` (= fix report). Frozen-row check (diff b5f29e35..HEAD of the unit file): only r06, r07, r18, r28, r33, r40b re-pinned (each named by F1-1 / F1-4 / F1-7, deviation D6) and r47-r58 + two gate fakes appended; every other row byte-identical |
| Scratch | `<scratchpad>/S81-04_fix1_adv` (detached at f1b29405; CRLF checkout, blob hashes equal to the worktree's: test e6292171, leaf 44f00352; sha-verified before and after every mutant; probe files added and deleted; removed with `git worktree remove --force`, absent from `git worktree list`). `<scratchpad>/S81-04_fix1_rv_pre` (detached at b5f29e35 + the final unit file, removed). No node_modules junction, no `.qa-mutation.lock` left, no `.env` in either notes folder, no pytest process of mine alive |
| Notes | `<scratchpad>/S81-04_fix1_rv/` (notes.md, mutate_rv.py, mut_rv_b1.json, mut_rv_b2.json, mut_logs/, probe_*.json, test_zz_s04rv_probes.py, test_zz_s04rv_probe2.py, comm/, ci_on_failed.txt, logs) |
| Verdict | **SOUND** (0 blocking, 0 major, 8 minor) |

## 1. Runs (every pytest through pyt.py, one at a time; [pyt] lines verbatim)

| Run | Result | [pyt] |
|---|---|---|
| unit file, flag unset | 267 passed (`[hermeticity] sentinel checked 267 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)`: r42 + p08, sentinel `neutralized.supabase.invalid:443` only) | `[pyt] tag=s04rv-unit-off start=2026-10-24 00:38:45 end=2026-10-24 00:39:04 elapsed=19s bound=600s status=OK rc=0` |
| unit file, `ENABLE_LLM_SPEND_BREAKER=true` | 267 passed (same guard lines; no never-awaited / never-retrieved / destroyed-pending lines in either log) | `[pyt] tag=s04rv-unit-on start=2026-10-24 00:39:15 end=2026-10-24 00:39:23 elapsed=9s bound=600s status=OK rc=0` |
| unit file `--collect-only` | 267 nodes; per-row counts equal the PR body table (r07 12, r57 8, r55 2, r56 2, r28 5, r18 3, r19b 5, r23 6, r46 4, p01 8, ...) | `[pyt] tag=s04rv-collect start=2026-10-24 01:30:33 end=2026-10-24 01:30:46 elapsed=12s bound=600s status=OK rc=0` |
| the final unit file on a scratch copy of the PRE-FIX bytes b5f29e35 | 29 failed / 238 passed; 29 `E AssertionError`, 0 `DID NOT RAISE`, no other class; the 29 = r06, r07 x4, r28, r40b, r47, r47b, r48, r49, r51, r52, r52b, r53, r54, r54b, r55 x2, r56 x2, r57 x8 (the PR body / fix report claim "29 failed AssertionError-only / 238 passed" TRUE) | `[pyt] tag=s04rv-prefix-red start=2026-10-24 01:28:04 end=2026-10-24 01:28:34 elapsed=30s bound=600s status=FAIL rc=1` |
| CI-order set (the fix's 24 files, CI order, one call), flag unset | 1771 passed; `[netguard] blocked 165 attempt(s) from 9 node(s)` (all baseline nodes of tests/.network_attempt_baseline.txt + r42 / p08 sentinel) | `[pyt] tag=s04rv-ci-off start=2026-10-24 00:53:13 end=2026-10-24 00:54:43 elapsed=90s bound=1200s status=OK rc=0` (a first call died rc=4 in 2 s on a CR-carrying file list: `[pyt] tag=s04rv-ci-off start=2026-10-24 00:52:45 end=2026-10-24 00:52:47 elapsed=2s bound=1200s status=FAIL rc=4`, a usage error, re-run with an LF list) |
| the same 24 files, flag exported ON (limit 15) | 34 failed / 1737 passed = 6 `test_retro_w0_4_efg` + 7 `test_s77_redis_offloop` + 21 `test_s81_s03_llm_ledger_v2`; the failed-node list is IDENTICAL (diff empty) to the fix agent's `ci_on_failed.txt` (= the GREEN's); FY25 nine digests, W4-13 ledger, T23 (test_s71_u13), U3c, K1, both CLAUDE.md readers green ON | `[pyt] tag=s04rv-ci-on start=2026-10-24 00:55:08 end=2026-10-24 00:56:19 elapsed=71s bound=1200s status=FAIL rc=1` |
| comm set at HEAD (the 335-file GREEN set, 14 chunks of <= 24, the 4 NETWORK_FLAKY nodes deselected), flag unset | 6 failed nodes = the 4 `.pre_impl_failures.txt` rows (test_auth_interceptor x2, test_page_scraping x2) + the 2 cold-tiktoken ERRORs of test_prompt_truth; vs the GREEN base record (`S81-04_green/comm/base_failed.txt`, 7 nodes): **branch-only-new EMPTY** (Python set difference; base-only = the ST1 timing row `test_r07_usage_status_on_reads_in_one_gather[sync_on]`, as in the GREEN and the fix) | 14 lines below |
| hook test files ALONE, `-k black` | 4 passed, 323 deselected | `[pyt] tag=s04rv-hook-black start=2026-10-24 01:19:27 end=2026-10-24 01:23:19 elapsed=232s bound=1200s status=OK rc=0` |
| mutants (22) | section 2 | 22 lines below |
| probes (5) + probe 2 (twice) | section 3 | `[pyt] tag=s04rv-probes start=2026-10-24 00:50:32 end=2026-10-24 00:50:50 elapsed=18s bound=600s status=OK rc=0`; `[pyt] tag=s04rv-probe2 start=2026-10-24 01:32:22 end=2026-10-24 01:32:40 elapsed=18s bound=600s status=OK rc=0`; `[pyt] tag=s04rv-probe2b start=2026-10-24 01:33:10 end=2026-10-24 01:33:19 elapsed=9s bound=600s status=OK rc=0` |

Comm chunks (head; files / summary / [pyt]):
- 01: 24, 2 failed (auth_interceptor x2), 845 passed: `[pyt] tag=s04rv-comm-head-01 start=2026-10-24 00:57:41 end=2026-10-24 00:58:33 elapsed=52s bound=1200s status=FAIL rc=1`
- 02: 24, 1226 passed, 5 deselected: `[pyt] tag=s04rv-comm-head-02 start=2026-10-24 00:58:34 end=2026-10-24 00:59:38 elapsed=64s bound=1200s status=OK rc=0`
- 03: 24, 997 passed, 1 skipped, 12 deselected: `[pyt] tag=s04rv-comm-head-03 start=2026-10-24 00:59:40 end=2026-10-24 01:00:45 elapsed=66s bound=1200s status=OK rc=0`
- 04: 24, 919 passed, 1 skipped: `[pyt] tag=s04rv-comm-head-04 start=2026-10-24 01:00:47 end=2026-10-24 01:01:24 elapsed=38s bound=1200s status=OK rc=0`
- 05: 24, 1563 passed, 5 deselected: `[pyt] tag=s04rv-comm-head-05 start=2026-10-24 01:01:26 end=2026-10-24 01:03:53 elapsed=148s bound=1200s status=OK rc=0`
- 06: 24, 366 passed: `[pyt] tag=s04rv-comm-head-06 start=2026-10-24 01:04:23 end=2026-10-24 01:05:12 elapsed=49s bound=1200s status=OK rc=0`
- 07: 24, 574 passed: `[pyt] tag=s04rv-comm-head-07 start=2026-10-24 01:05:13 end=2026-10-24 01:05:40 elapsed=27s bound=1200s status=OK rc=0`
- 08: 24, 2 failed (page_scraping x2), 501 passed, 7 deselected: `[pyt] tag=s04rv-comm-head-08 start=2026-10-24 01:05:43 end=2026-10-24 01:06:25 elapsed=42s bound=1200s status=FAIL rc=1`
- 09: 24, 642 passed, 3 skipped, 2 deselected, 1 xfailed, 2 errors (cold tiktoken): `[pyt] tag=s04rv-comm-head-09 start=2026-10-24 01:06:26 end=2026-10-24 01:08:10 elapsed=104s bound=1200s status=FAIL rc=1`
- 10: 24, 1127 passed: `[pyt] tag=s04rv-comm-head-10 start=2026-10-24 01:08:12 end=2026-10-24 01:10:57 elapsed=165s bound=1200s status=OK rc=0`
- 11: 24, 2967 passed (the unit file + test_s81_st1 + test_security_hardening): `[pyt] tag=s04rv-comm-head-11 start=2026-10-24 01:11:22 end=2026-10-24 01:13:32 elapsed=130s bound=1200s status=OK rc=0`
- 12: 24, 622 passed, 2 skipped, 11 deselected: `[pyt] tag=s04rv-comm-head-12 start=2026-10-24 01:13:33 end=2026-10-24 01:14:54 elapsed=81s bound=1200s status=OK rc=0`
- 13: 24, 463 passed, 8 deselected: `[pyt] tag=s04rv-comm-head-13 start=2026-10-24 01:14:57 end=2026-10-24 01:16:23 elapsed=86s bound=1200s status=OK rc=0`
- 14: 23, 1204 passed, 9 skipped, 35 xfailed: `[pyt] tag=s04rv-comm-head-14 start=2026-10-24 01:16:24 end=2026-10-24 01:17:31 elapsed=67s bound=1200s status=OK rc=0`

Comm-set coverage re-check: every source-scanning pin (test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_model_config x2, test_prompt_fence, test_u3c) and both CLAUDE.md readers are in the 335; the only test that names a fix-round path outside the set is `tests/test_precommit_hook.py` (hook file, excluded by rule; it writes its own tmp allowlist, so the repo allowlist is checked by `test_ci_gates::test_black_allowlist_entries_are_actually_clean`, green OFF and ON).

Non-pytest gates (scratch, pinned venv): black 26.5.1 `--check --config pyproject.toml` leaf "1 file would be left unchanged", `app/services/llm_pricing.py` "1 file would be reformatted" (D1's refuted premise CONFIRMED); `ruff check --select E9,F63,F7,F82 --no-cache` on the leaf, scs, main.py, unit file: All checks passed; `--select F401,F841` leaf + unit file: All checks passed; `py_compile` of the 4: ok. Fix-commit diff (b5f29e35..HEAD): 6 files +1070 / -182, `git diff --check` clean; added-line sweep: 0 runs of 8+ digits, 0 @gmail / +973 / sk- / eyJ / PEM / credentialed-URL shapes; bytes > 127: 66 added = 66 removed, byte multisets equal, all on the one re-added Feature Flags line (net 0, the PR body's sentence TRUE); CLAUDE.md / scs / main.py / black-clean-paths.txt 0 bare LF (CRLF kept), leaf and unit file LF.

## 2. Mutation table (my harness `mutate_rv.py` on the scratch worktree: byte copy, an exact edit matching once, the FULL unit file `-x -q` with the flag unset, restore, sha256 compare = restored every time; lock created and removed)

| # | Mutant (fix covered) | Status | First killer | [pyt] |
|---|---|---|---|---|
| F11a | F1-1 settle on the settle-time day | KILLED | r47 | `[pyt] tag=s04rv-f11a start=2026-10-24 00:41:56 end=2026-10-24 00:42:18 elapsed=23s bound=600s status=FAIL rc=1` |
| F11b | F1-1 settle with today's EXPIREAT | KILLED | r47 | `[pyt] tag=s04rv-f11b start=2026-10-24 00:42:21 end=2026-10-24 00:43:00 elapsed=39s bound=600s status=FAIL rc=1` |
| F11c | F1-1 negative clamp removed | KILLED | r48 | `[pyt] tag=s04rv-f11c start=2026-10-24 00:43:01 end=2026-10-24 00:43:12 elapsed=10s bound=600s status=FAIL rc=1` |
| F12 | F1-2 a GET after a landed write replaces the base | KILLED | r49 | `[pyt] tag=s04rv-f12 start=2026-10-24 00:43:14 end=2026-10-24 00:43:26 elapsed=12s bound=600s status=FAIL rc=1` |
| F13 | F1-3 no cancelled-record settle callback | KILLED | r51 | `[pyt] tag=s04rv-f13 start=2026-10-24 00:43:27 end=2026-10-24 00:43:35 elapsed=8s bound=600s status=FAIL rc=1` |
| F14a | F1-4a a late record counted as a fail-open | KILLED | r52 | `[pyt] tag=s04rv-f14a start=2026-10-24 00:43:36 end=2026-10-24 00:43:49 elapsed=13s bound=600s status=FAIL rc=1` |
| F14b | F1-4b no single flight | KILLED | r53 | `[pyt] tag=s04rv-f14b start=2026-10-24 00:43:50 end=2026-10-24 00:43:59 elapsed=8s bound=600s status=FAIL rc=1` |
| F14c | F1-4c no fail-open window | KILLED | r54 | `[pyt] tag=s04rv-f14c start=2026-10-24 00:44:00 end=2026-10-24 00:44:09 elapsed=9s bound=600s status=FAIL rc=1` |
| F15 | F1-5 a zero admit bound valid | KILLED | r55[0] | `[pyt] tag=s04rv-f15 start=2026-10-24 00:44:10 end=2026-10-24 00:44:24 elapsed=14s bound=600s status=FAIL rc=1` |
| F16r | F1-6 REST entry on LANE_LIVE | KILLED | r56[rest] | `[pyt] tag=s04rv-f16r start=2026-10-24 00:44:25 end=2026-10-24 00:44:37 elapsed=12s bound=600s status=FAIL rc=1` |
| F16s | F1-6 stream entry on LANE_LIVE | KILLED | r56[stream] | `[pyt] tag=s04rv-f16s start=2026-10-24 00:44:38 end=2026-10-24 00:44:48 elapsed=10s bound=600s status=FAIL rc=1` |
| F17 | F1-7 every OpenAI id takes the 4o image bound | KILLED | r07[image_mini] | `[pyt] tag=s04rv-f17 start=2026-10-24 00:45:12 end=2026-10-24 00:45:21 elapsed=9s bound=600s status=FAIL rc=1` |
| X1 | `_spent_async` awaits `asyncio.wrap_future(shared GET)` instead of `_follow` | **SURVIVED** (minor m4) | - | `[pyt] tag=s04rv-x1 start=2026-10-24 00:45:22 end=2026-10-24 00:45:31 elapsed=9s bound=600s status=OK rc=0` |
| X2 | round-1 A09: record shield removed | KILLED | r52 | `[pyt] tag=s04rv-x2 start=2026-10-24 00:45:32 end=2026-10-24 00:45:51 elapsed=19s bound=600s status=FAIL rc=1` |
| X3 | round-1 A03: /health `exhausted` ignores the memo day | **SURVIVED** (minor m5) | - | `[pyt] tag=s04rv-x3 start=2026-10-24 00:45:52 end=2026-10-24 00:46:01 elapsed=9s bound=600s status=OK rc=0` |
| X4 | round-1 A04: /health ignores the in-flight deltas | **SURVIVED** (minor m5) | - | `[pyt] tag=s04rv-x4 start=2026-10-24 00:46:02 end=2026-10-24 00:46:12 elapsed=10s bound=600s status=OK rc=0` |
| X5 | round-1 A05: admin snapshot ignores the in-flight deltas | KILLED | r50 | `[pyt] tag=s04rv-x5 start=2026-10-24 00:46:14 end=2026-10-24 00:46:32 elapsed=18s bound=600s status=FAIL rc=1` |
| X6 | `_record_gave_up` drops a failure that finished before the awaiter gave up | **SURVIVED** (minor m6, race arm) | - | `[pyt] tag=s04rv-x6 start=2026-10-24 00:46:33 end=2026-10-24 00:46:49 elapsed=17s bound=600s status=OK rc=0` |
| X7 | round-1 A02: an EVAL observation lowers the base | KILLED | r50 | `[pyt] tag=s04rv-x7 start=2026-10-24 00:46:50 end=2026-10-24 00:47:05 elapsed=15s bound=600s status=FAIL rc=1` |
| X8 | M50: in-flight delta never settled | KILLED | r50 | `[pyt] tag=s04rv-x8 start=2026-10-24 00:47:06 end=2026-10-24 00:47:19 elapsed=13s bound=600s status=FAIL rc=1` |
| X9 | the late INFO line removed (counter kept) | KILLED | r52 | `[pyt] tag=s04rv-x9 start=2026-10-24 00:47:24 end=2026-10-24 00:47:36 elapsed=11s bound=600s status=FAIL rc=1` |
| X10 | settle delta sign reversed (bound - actual) | KILLED | r40b | `[pyt] tag=s04rv-x10 start=2026-10-24 00:47:38 end=2026-10-24 00:47:47 elapsed=9s bound=600s status=FAIL rc=1` |

Counts: 22 mutants, 18 KILLED (every one by an assertion failure in the named row), 4 SURVIVED (X1, X3, X4, X6: test gaps, none a ruling-named behaviour). Every fix F1-1..F1-7 has at least one killed mutant (F1-1 x3, F1-2 x3 incl. X7 / X8, F1-3, F1-4 a/b/c x5 incl. X2 / X9, F1-5, F1-6 x2, F1-7).

## 3. Probes re-run on the fix bytes (hermetic, through pyt.py in the scratch worktree; JSON in the notes folder)

- Cross-midnight, with a fake that applies REAL expiry (a key at or past its EXPIREAT is gone; EXPIREAT in the past deletes): reserve offclock 1.5 at 23:50 Riyadh 2026-10-23, then (a) settle 0.4 at 02:00 Riyadh 2026-10-24 (after the 01:00 grace): store after the settle `{}` (the D1 key was expired and the script's EXPIREAT deleted the briefly-negative value), no negative key, the D2 key untouched, the next-day admit of 1.9 did not fail open (fail_open 0), the next-day reserves of 1.5 against 2.00 = [admitted, refused], D2 key 1.5; (b) settle at 00:30 Riyadh (inside the grace): D1 key 0.4, D2 untouched, the same [admitted, refused]. The round-1 MAJOR (D2 -1.1, 3.0 USD held on a 2.0 cap) is CLOSED.
- Herd on a HEALTHY slow Upstash (0.18 s per GET / EVAL, 4 workers, 0.5 s bound): k = 4 / 8 / 12 / 16 concurrent stale-memo admits -> exactly 1 GET each time, max admit 0.172-0.188 s, fail_open 0 (pre-fix: k GETs, 4 / 8 fail-opens at k = 12 / 16). Records queued FIRST then one admit: 4 records -> 0.359 s, 0 fail-open; 8 -> the read fails open at 0.515 s (fail_open 1, the window opens); 12 -> 0.516 s, fail_open 1, `llm_spend_late_records` 4 (F1-4a works: the late landings are not fail-opens).
- Stall (every command 3.0 s): 12 sequential `admit_async` took 0.516 s IN TOTAL (pre-fix 6.06 s), 1 GET issued, the entry check inside the window 0.0 s (False), `record_soon` inside the window returns None (nothing sent), fail_open 1.
- Single flight waiter isolation (pool saturated by 4 jobs of 1.2 s; waiter A at 0 s, waiter B joins the same GET at 0.3 s): real code A and B both return (fail-open at their own bound), the shared GET still runs (gets 1); with mutant X1 (`wrap_future`) A's timeout CANCELS the queued shared GET (gets 0) and B's `admit_async` raises `CancelledError` (not an Exception, so it escapes the fail-open arm). The `_follow` claim is real and load-bearing but unpinned (m4).
- Cross-day memo clobber (m1): see finding m1 (measured: the memo view of D2 1.0 against a true D2 total 1.4; an admit of 0.7 against the 2.00 cap ADMITTED where the control refuses).
- Window drop magnitude (m2): 12 records queued first, one admit -> the read times out at the bound, the window opens; 18 `record_soon` calls over the next 4.5 s: 18 / 18 not sent; 0.12 of 0.30 USD intended reached Upstash.

## 4. Findings

### BLOCKING
None.

### MAJOR
None.

### MINOR
1. m1 (F1-2 residual, cross-day clobber; the row / PR body / leaf docstring claim "a GET submitted before a record landed never lowers the memo below that record's total" overclaims): `_observe_write_locked` REPLACES the lane's memo when the observed EVAL is for a DIFFERENT day (`entry["day"] != day`), including an OLDER day: a settle of a previous-day ticket (the normal F1-1 case for batches, at any hour of the next day) or a record submitted before 00:00 Riyadh that lands after it. When that older-day EVAL lands between a new-day record's EVAL and the return of a new-day GET submitted before that record, `_observe_read` finds an entry of another day, skips the F1-2 `max`, and stores the stale GET total. Measured (sync admit GET gated, D2 seeded 1.0, D2 record 0.4 lands, then a D1 settle lands, then the GET returns 1.0): memo view 1.0, true 1.4, `admit("offclock", 0.7)` against cap 2.00 ADMITTED (true 2.1); the control without the settle keeps 1.4 and refuses. Transient (until the next own EVAL of the lane or the 5 s memo expiry), bounded by the new-day records that landed during one GET; also makes `/health llm_spend.<lane>.day` and the admin `spent_usd` show the older day (a negative amount after an after-grace settle) until the next read. Fix suggestion (one line): in `_observe_write_locked`, never replace a memo entry of a LATER day with an older-day observation (ISO dates compare as strings); pin it with the interleave above. Latent for offclock (no reserve / settle caller yet); for live it needs a pre-midnight record landing inside one GET round trip after midnight.
2. m2 (F1-4c consequence, informs the open gate question Q3): the per-lane window is also opened by FIFO congestion on a HEALTHY Upstash (the row says so: about 8-9 queued EVALs push a due read past its bound), and every `record_soon` inside the window is dropped: measured 18 of 18 records over 4.5 s not sent (60 % of the interval's spend never recorded). `record_soon` is non-awaited, so windowing it saves no caller latency, only pool load. The behaviour is ruled (F1-4c) and stated (row limit 1); recommendation for Q3: keep the windowed record's delta in the local memo (or do not window `record_soon`), so this process at least sees its own spend.
3. m3 (F1-7 premise): the leaf comment, the CLAUDE.md row limit text and the PR body derive `OPENAI_MINI_IMAGE_TOKENS_UPPER = 37_000` from "2,833 + 5,667 x 6 at the 6-tile maximum of a 768-px-short-side scaled image", while the SAME leaf derives the 4o bound from the same resize at 8 tiles ("at most 8 tiles (768 x 2048 after the resize)"). With 8 tiles the mini maximum is 2,833 + 5,667 x 8 = 48,169 tokens, so 37,000 is NOT an upper bound for a tall image (admit-side under-bound up to 11,169 tokens, about 0.0017 USD per image at mini list price; records use the served usage). The row's "over-bounding only refuses earlier near the cap" is therefore not established. Already marked UNVERIFIED for S81-07; the gate should either re-derive the constant at 8 tiles (48,169, or 48,500 rounded) or reword the premise.
4. m4 (test gap, F1-4b): the `_follow` property "a waiter's timeout cancels only its own follower, never the shared GET" is unpinned (mutant X1 survives the whole unit file) although the probe shows it matters (with `wrap_future` a second waiter's admit raises CancelledError and the shared GET is cancelled). A two-waiter row on a saturated pool would pin it.
5. m5 (round-1 survivors not recorded): round-1 correctness mutants A03 (/health `exhausted` for an earlier-day memo) and A04 (/health ignores in-flight deltas) still SURVIVE on the fix bytes (X3, X4); the fix report and the PR body mention A02 / M50 only, not A03 / A04 (A05 and A09 are now killed, by r50 and r52). Record them or add the two snapshot rows.
6. m6 (test gap, race arm): `_record_gave_up`'s "a job that already failed is a fail-open now" arm is unpinned (X6 survives); counter accuracy only, inside a narrow race. Note or pin.
7. m7 (wording nit, row limit 1 and PR body limit 1): "about 9 or more queued EVALs can still push a due read past its bound" while the same row reports "8: the read failed open at 0.516 s" and the post-fix probe measures the read failing open with 8 queued EVALs (0.515 s): say "8 or more queued EVALs (the read is the 9th job)".
8. m8 (counter semantics nit): a `record_soon` task cancelled at loop shutdown (`_record_task` CancelledError arm calls `_record_gave_up`) whose shielded EVAL then lands is counted in `llm_spend_late_records`, though it was not slow. Affects scripts' `asyncio.run` exit only (web's loop lives for the process). Note only.

## 5. Previous-round findings: closed or recorded

Correctness round 1 (S81_04_ADV1_correctness.md):
- MAJOR-1 settle day: CLOSED (F1-1; ReserveTicket + settle on the ticket day / EXPIREAT; r47 / r47b / r48; F11a / F11b / F11c / X10 killed; real-expiry probe clean).
- m1 memo undercount race: CLOSED for the same-day case (F1-2; r49 / r50; F12 / X7 / X8 killed); a cross-day residual is new m1 above.
- m2 cancelled queued sync record: CLOSED (F1-3; r51; F13 killed).
- m3 late shielded record counted as fail-open: CLOSED (F1-4a; r52 / r52b; F14a / X2 / X9 killed; probe: late 4, fail_open not inflated).
- m4 stall cost: CLOSED (F1-4c window + row limit 1; probe 12 admits 0.516 s).
- m5 mid-compare refusal billed: CLOSED (row limit 5 reworded per F1-10).
- m6 vision bound under mini: CLOSED per ruling (F1-7, per-model bound; r07 / r28 / r57; F17 killed); premise inconsistency is new m3.
- m7 zero bound: CLOSED (F1-5; r55; F15 killed).
- m8 two scripts outside the chokepoint: CLOSED (leaf opening lines + row limit 16).
- m9 limit 3 wording: CLOSED (row limit 3 rewritten).
- m10 entry lane hard-coded: CLOSED (F1-6; r56 x2; F16r / F16s killed).
- m11 GC-3 wording vs code: no ruling; the row now states the code's behaviour (priced model: own rate x 16,384; garbage / zero bound and unpriced model: the conservative rate): consistent, recorded.
- prove-nothing rows: A09 (r22 durable) CLOSED by r52; M50 / A02 CLOSED by r50; A05 CLOSED by r50; A03 / A04 still open (new m5); A24 / A25: A25 closed by r55, A24 harmless (unchanged).
Engineering round 1 (S81_04_ADV1_engineering.md):
- m1 8-digit run in `_cents`: CLOSED (F1-9; the added-line sweep finds 0 runs).
- m2 herd: CLOSED (F1-4b single flight, measured 1 GET for k up to 16) and stated (records sharing the FIFO, the window; nit m7).
- m3 limit 11: CLOSED (F1-11 wording: interpreter exit waits).
- m4 "bounded by": CLOSED (row and leaf).
- m5 rollback wording: CLOSED (RO18 sentence in the row and the PR body).
- m6 stall cost: CLOSED (as correctness m4).
- m7 PR body non-ASCII sentence: CLOSED ("net 0 ... re-adds its 66 pre-existing bytes", measured true).
- m8 Feature Flags pointer: CLOSED (names the row; r38's extract from the row header to the next `**SESSION` header).
- m9 black ratchet: CLOSED for the leaf (F1-8; joined, black-clean, allowlist test green); `llm_pricing.py` NOT joined: deviation D1 with Q1, its premise measured false (black would reformat it).
GREEN Q1-Q4: answered by F1-4 / F1-7 / F1-2 / F1-10.

## 6. CLAUDE.md row and PR body, sentence by sentence (against the bytes)

TRUE: the flag idiom and the four gated branches; every knob name, default and clamp (`_positive_float_knob`, `chokepoint_lane`); pool of 4 as a constant; admit before the W1-3 admission (`guarded_llm_create`); the prompt bound (UTF-8 bytes + 4 / message + 16 / call + `response_format` / `tools` JSON bytes; the leaf also counts extra message keys, more conservative); the per-model image bound mechanics (1,445 for an id priced at the 4o row; 37,000 otherwise incl. unpriced / missing; 4,784 Anthropic; the max for an unknown provider); 16,384 output fallback; the unpriced conservative bound (4o row / Sonnet 5.5 row); the zero / garbage admit bound fallback (unknown-provider branch, Sonnet rate); strict admit, inclusive entry predicate, one helper; the WARNING templates (ints only); the record (durable `llm_spend.record` task, one EVAL, list price else the admitted bound, nothing on a raise / cancel); the key and the EXPIREAT; single flight; the async / sync bounds; no client = no submit; the entry on `chokepoint_lane()`; /health keys and their RO18 persistence; the admin block ON only; ReserveTicket / settle on the ticket's day and EXPIREAT, a 0 actual releases the bound, a non-ticket is a ValueError; the negative clamp WARNING; flag-OFF byte identity (P01-P09, FY25, W4-13 green); limits 2-6, 8-16 (limit 15's 34 nodes measured identical); owner steps; canary; rollback.
OVERCLAIMED / INCONSISTENT: "a GET submitted before a record landed never lowers the memo below that record's EVAL total" (row R-S04-1 sentence, PR body memo bullet, leaf docstring): false across days (m1); "2,833 base + 5,667 per tile at the 6-tile maximum" and "over-bounding only refuses earlier near the cap" (row limit 7 / effect text, PR body limit 6): inconsistent with the leaf's own 8-tile rule (m3); "about 9 or more queued EVALs" (row limit 1, PR body limit 1): measured 8 (m7).
PR body tables: node counts per row TRUE (collect-only); "29 failed AssertionError-only / 238 passed" on the pre-fix bytes TRUE; CI-order 1771 / ON 34 TRUE; hook `-k black` 4 passed TRUE; comm branch-only-new EMPTY TRUE; lint / black / bytes / CRLF sentences TRUE; "the pre-commit hook ran on every commit": NOT MEASURED by me (no trace beyond the fix report). Its 45-mutant claim was not re-run in full; my 22 agree on every overlapping fix and add the 4 survivors above.

## 7. NOT MEASURED
- The 323 hook-file nodes outside `-k black` (about 74 s per node on this box, beyond the 1800 s ceiling; the unit edits no `.githooks` file; CI covers them).
- Upstash's real EVAL / GET latency and its acceptance of the two Lua scripts (canary); the production Railway-to-Upstash RTT (the herd and window thresholds scale with it).
- The gpt-4o-mini image token rule against OpenAI's page (no web read).
- The comm set at base (the GREEN base record used, as ruled).
- That the pre-commit hook ran on the fix commit (the fix report's statement only).

## 8. Final state
- sc-s81-s04: HEAD `f1b29405`, `git status --short` empty, RED file `d9bb55b5...` and leaf `802cb806...` unchanged, never edited; no `.qa-mutation.lock`.
- Both scratch worktrees removed and absent from `git worktree list`; no `.env` in `<scratchpad>/S81-04_fix1_rv/` or `<scratchpad>/S81-04_fix1/`; no pytest process of mine alive (the only python.exe is the orchestrator's stall monitor).

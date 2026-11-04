# S81-G3 fix round 1 RE-VERIFY report (correctness lens, RULINGS_FIX1_S81_G3 F1-8)

Agent: the G3 fix-round-1 re-verifier, model Opus 5.5. Written through the shell. sc-s81-g3 verified at start and end: branch feature/s81-g3-kb-ingest, HEAD 32f9b76a558d99c57656934d70415cfba9df7c7b, `git status --short` EMPTY, never edited (one read-only `git fetch origin main`: origin/main still 744616e3). Probes and mutants ran in my own detached scratch worktree S81-G3_fix1_adv at 32f9b76a; its seven new files were re-written from the committed LF blobs so all 15 diff files are sha-equal to the worktree (checked file by file); removed at the end with `git worktree remove --force` (gone from `git worktree list`; no junction).

## Verdict: SOUND (0 blocking, 0 major, 5 minor = stated limits / wording, LC-4)

## Frozen and fix files (sha256, worktree bytes, start and end)
- tests/test_s81_d14_live_robots.py 542cd259... ; tests/test_s81_s17_kb_ingest.py 547cdb74... ; tests/fixtures/s81_d14_flag_off_golden.json 55851c04... ; tests/fixtures/s81_s17_flag_off_golden.json 514d1cd2... = GC-1 (byte-identical; `git diff efa33a81 HEAD` touches none of them).
- tests/test_s81_g3_gate_rows.py 4a8e4399... ; app/services/price_service.py 31fa1630... ; app/services/live_robots.py deafa9e5... (= the fix report).
- Fix diff efa33a81..HEAD: live_robots.py +4/-1, price_service.py +1/-1, gate rows +197/-0; no other file.

## F1-1 (M-1) closed
- `git diff --numstat 744616e3 HEAD -- app/services/price_service.py` = 18 / 0 (also with -w); the + lines are exactly the import beside :46 (3 lines) and the curl_fetch_html / curl_fetch_html_same_site hooks; no `-` line.
- HEAD line 51 = `ENABLE_PAGE_SCRAPE = os.environ.get("ENABLE_PAGE_SCRAPE", "true").lower() != "false"` + CR = base line 48 byte for byte; 17302 / 17302 CRLF lines; added lines ASCII.
- Corpus gate at 32f9b76a (scratch worktree, venv python, scripts/verify_flag_byte_identity.py --proof-root sc-scraper-proof/_proof, the four G3 flags forced OFF; 16:37:33-16:44:10, rc=0): `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef` = base. Not a pytest; no pytest ran beside it.
- RV-7 (the byte re-broken) is not test-killable by design; the numstat gate sees it (19 / 1).

## F1-2 (M-2 + m-3) closed: G3-GR3
- (a1) the S17 RED driver `_compare` with the full config, ENABLE_KB_INGEST=false, ENABLE_FIELD_STATUS_METADATA=" OFF ", delegating recorders on build_job / _now / assess_result: zero calls, no kb_ingest label; (a2) a raising build_job: no KB_INGEST WARNING; (b) main + health ON, bind / 2 records / flush / repeated flush, twice on one context, the redis-offloop pool faked by to_thread: 2 pipelines, 2 execs, own-host HINCRBY each.
- Not vacuous: under S17-M3, (a1) records ['_now', 'build_job', 'assess_result'] on rest AND stream, so the success tail is reached.

## F1-3 (m-1) closed: exec / execute
- Code: `fn = getattr(pipe, "exec", None) or getattr(pipe, "execute")`; `fn()`.
- Measured on the PINNED SDKs (no connection made): redis 8.1.0 `redis.Redis(...).pipeline()` has no `exec` -> `execute` picked; upstash-redis 1.7.0 `Redis(...).pipeline()` has `exec` (and `execute`) -> `exec` picked; hincrby / expire present. G3-GR4 fakes cover both shapes: each flushes once, no raise, the right HINCRBY / EXPIRE payload.
- Client None -> silent return (D14-L11); a raising client / pipeline -> caught in _flush_job, one WARNING.

## Mutation table (scratch byte copies, .qa-mutation.lock, restore + sha256 after each: all True; pre / post sha of live_robots, scs, price_service equal; every failure an AssertionError)

| id | mutant | kill set | result | killers |
|---|---|---|---|---|
| S17-M3 | `if not (ingest or expose): return` removed | gate rows | KILLED | gr3[rest], gr3[stream] |
| ADV-8 | `_ATTEMPTS_CTX.set(None)` dropped in flush_attempts | gate rows | KILLED | gr3[rest], gr3[stream] (4 pipelines) |
| G3-GRM4 | fallback dropped (`pipe.exec()`) | gate rows | KILLED | gr4[execute] |
| RV-1 | `fn = getattr(pipe, "execute")` (exec dropped) | gate rows | KILLED | gr4[exec], gr3 x2 |
| RV-2 | `fn` resolved, never called | gate rows | KILLED | gr4 x2, gr3 x2 |
| RV-3 | unbind moved AFTER the empty-bucket / health-OFF return | gate rows + 2 RED | SURVIVED (equivalent in the compare lifecycle; mi-1) | - |
| RV-4 | `if not (ingest and expose)` | gate rows + 2 RED | KILLED | S4 x2, S5, S7 x2, S8 x2, S9 x2, S21 x3 |
| RV-5 | a `kb_ingest._now()` call before the flag reads | gate rows | KILLED | gr3[rest], gr3[stream] |
| RV-6 | bind_attempts binds nothing | gate rows + 2 RED | KILLED | 28 nodes (gr2 x7, gr3 x2, L4 x10, L5 x3, L8 x4, L9 x2) |
| RV-7 | price_service :51 space removed again | numstat | DETECTED (19 / 1) | the diff gate |

10 applied: 8 KILLED by tests, 1 detected by the diff gate, 1 equivalent survivor (RV-3).

```
[pyt] tag=g3rv-s17-m3 start=2026-11-04 16:29:41 end=2026-11-04 16:29:46 elapsed=5s bound=600s status=FAIL rc=1   (2 failed, 12 passed)
[pyt] tag=g3rv-adv-8 start=2026-11-04 16:29:46 end=2026-11-04 16:29:52 elapsed=6s bound=600s status=FAIL rc=1   (2 failed, 12 passed)
[pyt] tag=g3rv-g3-grm4 start=2026-11-04 16:29:52 end=2026-11-04 16:29:58 elapsed=6s bound=600s status=FAIL rc=1   (1 failed, 13 passed)
[pyt] tag=g3rv-rv-1 start=2026-11-04 16:30:13 end=2026-11-04 16:30:18 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g3rv-rv-2 start=2026-11-04 16:30:19 end=2026-11-04 16:30:24 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=g3rv-rv-3 start=2026-11-04 16:30:25 end=2026-11-04 16:30:40 elapsed=16s bound=600s status=OK rc=0
[pyt] tag=g3rv-rv-4 start=2026-11-04 16:30:41 end=2026-11-04 16:31:15 elapsed=34s bound=600s status=FAIL rc=1
[pyt] tag=g3rv-rv-5 start=2026-11-04 16:31:15 end=2026-11-04 16:31:20 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=g3rv-rv-6 start=2026-11-04 16:31:20 end=2026-11-04 16:31:55 elapsed=34s bound=600s status=FAIL rc=1
```
Every mutant run: [netguard] blocked 0.

## Gates at 32f9b76a (scratch worktree = exact bytes; one pytest at a time)
```
[pyt] tag=g3rv-unit-off start=2026-11-04 16:27:19 end=2026-11-04 16:27:40 elapsed=21s bound=600s status=OK rc=0   (729 passed: 2 RED files + gate rows + test_s81_kb_schema.py)
[pyt] tag=g3rv-unit-on start=2026-11-04 16:27:53 end=2026-11-04 16:28:14 elapsed=21s bound=600s status=OK rc=0   (729 passed; the four flags exported in ONE runner call)
[pyt] tag=g3rv-ci-off start=2026-11-04 16:32:37 end=2026-11-04 16:33:27 elapsed=50s bound=1200s status=FAIL rc=1   (1957 passed / 1 failed = s10 r06, a base-record node)
[pyt] tag=g3rv-comm-17 start=2026-11-04 16:33:52 end=2026-11-04 16:35:15 elapsed=82s bound=1200s status=OK rc=0   (3775 passed; [netguard] blocked 24 attempt(s) from 2 node(s): the two s04 spend_breaker sentinel nodes, neutralized.supabase.invalid, = GREEN / fix)
[pyt] tag=g3rv-comm-18 start=2026-11-04 16:35:16 end=2026-11-04 16:36:14 elapsed=59s bound=1200s status=FAIL rc=1   (6 failed = r06 + the five s16 r27 CRLF nodes, all in the base record)
[pyt] tag=g3rv-comm-secret start=2026-11-04 16:36:25 end=2026-11-04 16:36:39 elapsed=14s bound=1200s status=OK rc=0   (31 passed)
[pyt] tag=g3rv-hooks start=2026-11-04 16:44:24 end=2026-11-04 17:14:26 elapsed=1802s bound=1800s status=TIMEOUT rc=124   (the four hook files alone; test_precommit_hook.py complete, phase_b partly, 0 F / 0 E seen)
[pyt] tag=g3rv-hooks2 start=2026-11-04 17:14:47 end=2026-11-04 17:40:23 elapsed=1536s bound=1800s status=OK rc=0   (re-run alone: hook_round2 + phase_b_round2, 151 passed)
```
Every other run: [netguard] blocked 0; [hermeticity] sentinel checked = the node count.
- The 200 G3 nodes pass ON inside g3rv-unit-on (a superset run with kb_schema).
- Comm: GREEN's chunk lists 17 + 18 (the three G3 files and test_s81_kb_schema.py) + test_secret_scan_static.py alone vs the STORED base record base_records/744616e3.../ba26af35....txt (REUSED, LC-6, 14 ids): HEAD FAILED 6, `comm -13` branch-only-NEW EMPTY.
- Hook files: TIMEOUT once (all four), re-run once alone split by file; test_precommit_hook_phase_b.py NOT fully MEASURED (partial in run 1, no failure seen). No .githooks file in the diff; the fix commit passed the hook.
- Lint: ruff E9,F63,F7,F82 on the three touched files: All checks passed; py_compile OK; 0 CR and 0 bytes > 127 in live_robots.py and the gate rows.

## PR body (S81-G3_green/PR_BODY.md, 18,988 B < 25,600; 0 CR; 1 non-ASCII line = the attribution glyph) and CLAUDE.md, sentence by sentence
- HEAD line, M-1 (18 / 0), M-2 + m-3 (GR3 a / b, S17-M3 / ADV-8 killed), m-1 (exec else execute, GR4, GRM4), m-2 / m-4 / m-6 as D14-L10 / S81-17-L10 / D14-L11, m-5 CONFIRMED, m-7 (re-run at the fix HEAD; B905 left): each matches the bytes and my measurements.
- Counts: 186 + 14 + 529 = 729 (gate rows GR1 x3 + GR2 x7 + GR3 x2 + GR4 x2 = 14); 1757 + 200 = 1957; corpus SHA equal: reproduced.
- The Redis sentence (a raising client = one WARNING; no client = silent) matches `_flush_sync` / `_flush_job`.
- CLAUDE.md not edited in the fix: correct per F1-5 (the S81-17 row says kb_products / kb_variants "for fragrance products" and gaps of an "identity high OR medium fragrance product").

## Previous round (S81_G3_ADV1_correctness.md) closure
M-1 CLOSED (F1-1). M-2 CLOSED (G3-GR3; S17-M3 killed). m-1 CLOSED (code + GR4 + the pinned SDK shapes measured). m-2 RECORDED D14-L10. m-3 CLOSED (ADV-8 killed). m-4 RECORDED S81-17-L10. m-5 RULED (F1-5) and stated. m-6 RECORDED D14-L11 + the corrected sentence. m-7 CLOSED (gates at the fix HEAD, named in the PR body; B905 left, report-only).

## MINOR (stated limits / wording, LC-4; none production-visible)
- mi-1 RV-3 survives: the unbind in flush_attempts is pinned only for a non-empty bucket with the health flag ON; moving it after the `not bucket or not health_flush_enabled()` return is unseen. Equivalent in production (bind_attempts re-binds at each compare start, nothing records after the compare's finally, a health-OFF bucket is never sent).
- mi-2 G3-GR3 part (b) drives the seam (bind / record / flush / repeated flush on one context), not two full compares (the fix report's DV-F2); its docstring and the PR body say "two consecutive compares" / "per compare".
- mi-3 the CLAUDE.md S81-G3 block lags the fix: its header names the gate rows "(G3-GR1 / G3-GR2)" only, and the D14 row says "ONE Upstash pipeline ... a failure one WARNING" without the redis-py `execute` path and the silent no-client case (D14-L11). For the final round's docs pass.
- mi-4 PR body "Counts and gates (fix HEAD 32f9b76a unless named)": the G3-GRM1 / G3-GRM2 kills cited there ran at GREEN efa33a81, not named.
- mi-5 test_precommit_hook_phase_b.py not fully measured (the TIMEOUT rule); no .githooks change.

Files in S81-G3_fix1_rv/: unit_off.log, unit_on.log, ci_off.log, comm-17.log, comm-18.log, comm-secret.log, comm_head_failed.txt, b2 (base set), h2 (head set), hooks.log, hooks2.log, corpus_head.log, corpus_time.txt, gate_head.json, mutate_rv.py, mut_*.log, mut_results.json, premut_sha.txt.

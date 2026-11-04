# S81-G3 FIX ROUND 1 REPORT (RULINGS_FIX1_S81_G3 F1-1..F1-7)

Agent: the G3 fix agent, model Opus 5.5 (claude-opus-5-5). Written through the shell (python). Worktree sc-s81-g3, branch feature/s81-g3-kb-ingest; verified at start: HEAD efa33a81dc6eca04f8f41c024cf3fc627a22032f, `git status --short` empty. ONE commit through the hook (ruff in the hook: All checks passed; never --no-verify): HEAD 32f9b76a558d99c57656934d70415cfba9df7c7b. No push, no rebase, no PR, no stash. `git status --short` at the end: empty.

## Files (git diff --numstat efa33a81 HEAD; sha256 of the working-copy bytes)

| file | +/- | sha256 before (efa33a81) | sha256 after (32f9b76a) |
|---|---|---|---|
| app/services/price_service.py (CRLF kept) | 1/1 | 477299a52b98675a8d263f83201e5a23b710fd85b8349bd06279dca675210459 | 31fa163063331951ae32d2be452d8051c90e1afbfd57120cbdde109c932c3787 |
| app/services/live_robots.py (LF, ASCII) | 4/1 | dd30877efa8ecab452b0e5f24f78199f4574087990bb18d3370cff6411096a9f | deafa9e57834ebbd3fc12ce2d81709c0dbd16de52e68ede99468122ed9fc6d58 |
| tests/test_s81_g3_gate_rows.py (LF, ASCII) | 197/0 | 16c37591af3fa22142d3418cca96886f23d814c3ca79eaffab1f8a6f412190b5 | 4a8e43998c21f4a2704286e3e83155e5095169d4a16f1400c6f2323abcc1c6fd |

Byte copies before the first edit: S81-G3_fix1/before/ (SHA256SUMS.txt; scs copied too, never edited). Bytes > 127 added: 0; CR in the two LF files: 0. CLAUDE.md NOT edited (F1-5: the S81-17 row already says cards "for fragrance products" and gaps "of an identity high OR medium fragrance product").

Frozen RED files re-hashed FIRST (16:10) and LAST (after the commit): 542cd259... 547cdb74... 55851c04... 514d1cd2... = GC-1 (sha256sum -c OK x4, frozen_first.txt).

## F1-1 (M-1)
`ENABLE_PAGE_SCRAPE =os.environ` -> `ENABLE_PAGE_SCRAPE = os.environ` (one exact-bytes replace, CRLF kept). `git diff --stat 744616e3 HEAD -- app/services/price_service.py`: 18 insertions, 0 deletions; the `+` lines are exactly the import beside :46 (3 lines) and the curl_fetch_html / curl_fetch_html_same_site hooks; base line 48 == HEAD line 51 byte for byte.

## F1-2 (M-2 + m-3): G3-GR3 `test_g3_gr3_no_projection_and_unbind_when_off[rest|stream]`
(a1) the S17 RED compare driver (`tests.test_s81_s17_kb_ingest._compare` / `_full_config`, imported, never edited) with ENABLE_KB_INGEST=false, ENABLE_FIELD_STATUS_METADATA=" OFF ", the full configuration (KB_INGEST_GAP_MAX, ENABLE_SYNC_DB_OFFLOAD on, the raising _admin_client, the to_thread recorder, the health sub-flag and TTL set) and delegating recorders on kb_ingest.build_job / kb_ingest._now / result_gate.assess_result: ZERO calls and no `kb_ingest` label; (a2) build_job replaced by a raising function: no WARNING containing KB_INGEST; (b) main + health ON, two consecutive compares on one context (bind, two records, the finally flush, a repeated flush), the redis-offloop pool faked by asyncio.to_thread: exactly 2 pipelines + 2 execs, each carrying only its own compare's HINCRBY. Green at the fix bytes; S17-M3 killed by (a1) (`['_now', 'build_job', 'assess_result']`), ADV-8 killed by (b) (4 pipelines), AssertionError only.

## F1-3 (m-1): `_flush_sync`
`pipe.exec()` -> `fn = getattr(pipe, "exec", None) or getattr(pipe, "execute")`; `fn()` (+ a 2-line comment). G3-GR4 `test_g3_gr4_flush_uses_exec_or_execute[exec|execute]`: one pipeline, the right flush method, the HINCRBY / EXPIRE payload, no raise (an exception is reported as an assertion). RED at efa33a81: [execute] FAILED `AssertionError: ('execute', 'AttributeError')` (the only failure; 13 passed). G3-GRM4 (fallback dropped) KILLED by [execute].

## Mutation table (byte copies, .qa-mutation.lock, restore + sha256 after each; mutate.py; killing set the gate-rows file, bound 600)

| id | mutant | result | killer |
|---|---|---|---|
| S17-M3 | `if not (ingest or expose): return` removed from _kb_ingest_tail | KILLED (at efa33a81 bytes and again at the fix bytes) | gr3[rest], gr3[stream] |
| ADV-8 | `_ATTEMPTS_CTX.set(None)` dropped in flush_attempts | KILLED (both byte states) | gr3[rest], gr3[stream] (part b) |
| G3-GRM4 | exec / execute fallback dropped (`pipe.exec()`) | KILLED | gr4[execute] |

Every restore sha-identical (scs 79b1f729..., live_robots dd30877e... then deafa9e5...).

## F1-4 / F1-5 / F1-6 docs
PR body S81-G3_green/PR_BODY.md patched in place through the shell (backup S81-G3_fix1/PR_BODY.before.md): HEAD line, the fix round 1 section (M-1 / M-2 / m-1..m-7), D14-L10, D14-L11, S81-17-L10, the corrected Redis sentence (a raising client = one WARNING; no client = silent, spec 2.2 wins), the exec / execute wording, the gate-row nodes, the counts, the HEAD each gate ran at, the fix [pyt] lines; 18988 bytes measured with python (< 25,600). B905 left (report-only).

## Gates (every pytest through pyt.py, one at a time)

Lint: ruff --select E9,F63,F7,F82 --no-cache on the three touched files: All checks passed; py_compile OK.

```
[pyt] tag=g3fix1-red-gr start=2026-11-04 16:11:32 end=2026-11-04 16:11:37 elapsed=6s bound=600s status=FAIL rc=1   (1 failed, 13 passed, 11 warnings in 4.52s)
[pyt] tag=g3fix1-s17-m3 start=2026-11-04 16:12:02 end=2026-11-04 16:12:06 elapsed=4s bound=600s status=FAIL rc=1   (3 failed, 11 passed, 11 warnings in 3.51s)
[pyt] tag=g3fix1-adv-8 start=2026-11-04 16:12:06 end=2026-11-04 16:12:12 elapsed=6s bound=600s status=FAIL rc=1   (3 failed, 11 passed, 11 warnings in 4.52s)
[pyt] tag=g3fix1-green-gr start=2026-11-04 16:12:35 end=2026-11-04 16:12:39 elapsed=5s bound=600s status=OK rc=0   (14 passed, 11 warnings in 3.93s)
[pyt] tag=g3fix1-g3-grm4 start=2026-11-04 16:12:40 end=2026-11-04 16:12:46 elapsed=6s bound=600s status=FAIL rc=1   (1 failed, 13 passed, 11 warnings in 4.56s)
[pyt] tag=g3fix1-s17-m3 start=2026-11-04 16:13:00 end=2026-11-04 16:13:05 elapsed=4s bound=600s status=FAIL rc=1   (2 failed, 12 passed, 11 warnings in 3.53s)
[pyt] tag=g3fix1-adv-8 start=2026-11-04 16:13:05 end=2026-11-04 16:13:11 elapsed=6s bound=600s status=FAIL rc=1   (2 failed, 12 passed, 11 warnings in 4.56s)
[pyt] tag=g3fix1-unit-off start=2026-11-04 16:13:35 end=2026-11-04 16:13:55 elapsed=20s bound=600s status=OK rc=0   (729 passed, 11 warnings in 18.89s)
[pyt] tag=g3fix1-unit-on start=2026-11-04 16:13:56 end=2026-11-04 16:14:16 elapsed=20s bound=600s status=OK rc=0   (729 passed, 11 warnings in 18.93s)
[pyt] tag=g3fix1-ci-off start=2026-11-04 16:15:25 end=2026-11-04 16:16:12 elapsed=48s bound=1200s status=FAIL rc=1   (1 failed, 1957 passed, 11 warnings in 46.01s)
[pyt] tag=g3fix1-ci-g3-on start=2026-11-04 16:16:13 end=2026-11-04 16:16:28 elapsed=15s bound=1200s status=OK rc=0   (200 passed, 11 warnings in 14.25s)
[pyt] tag=g3fix1-comm-17 start=2026-11-04 16:16:47 end=2026-11-04 16:18:09 elapsed=83s bound=1200s status=OK rc=0   (3775 passed, 63 warnings in 80.22s (0:01:20))
[pyt] tag=g3fix1-comm-18 start=2026-11-04 16:18:10 end=2026-11-04 16:19:09 elapsed=58s bound=1200s status=FAIL rc=1   (6 failed, 1865 passed, 1 xfailed, 43 warnings in 56.35s)
[pyt] tag=g3fix1-comm-secret start=2026-11-04 16:19:10 end=2026-11-04 16:19:24 elapsed=14s bound=1200s status=OK rc=0   (31 passed, 1 warning in 13.14s)
```
Every run: [hermeticity] sentinel checked N; [netguard] blocked 0, except g3fix1-comm-17: `[netguard] blocked 24 attempt(s) from 2 node(s)` (the two test_s81_s04_spend_breaker sentinel nodes, neutralized.supabase.invalid; identical to GREEN's g3green-comm-17 line). The first s17-m3 / adv-8 runs show a third failure, gr4[execute], because F1-3 was not applied yet (the RED state); the re-runs at the fix bytes fail exactly the two gr3 nodes.

- Unit (2 RED files + gate rows + kb_schema): 729 / 729 OFF and 729 / 729 with the four flags exported in ONE runner call (pre-commit bytes == the committed bytes).
- CI-order at the fix HEAD 32f9b76a: the 13 existing members OFF + the three G3 files OFF: 1957 passed / 1 failed (r06 base node) = 1757 + 200; the three G3 files ON: 200 passed.
- Corpus gate at the fix HEAD 32f9b76a (scripts/verify_flag_byte_identity.py, venv python, cwd the worktree, the four flags forced OFF, 16:16:40-16:23:29, rc=0): `RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656`, `OVERALL SHA256 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef` = base 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef. Output gate_head.json, corpus_head.log. (It ran beside comm-17/18/secret: not a pytest, stated.)
- Comm at the fix HEAD: GREEN's chunks 17 (holds test_s81_d14_live_robots.py, test_s81_g3_gate_rows.py, test_s81_kb_schema.py) and 18 (holds test_s81_s17_kb_ingest.py) + test_secret_scan_static.py alone, against the STORED base record base_records/744616e3.../ba26af35....txt (REUSED, LC-6; 14 ids): HEAD FAILED = r06 + the five s16 r27 CRLF nodes (all in the base record); `comm -13` branch-only-NEW: EMPTY (comm_head_failed.txt).
- NOT run (F1-7 / LC-7, the final round): the full 612-file comm set, the fourteen client fences, the FULL jest suite, the hook test files (no .githooks change).

## Deviations
- DV-F1: G3-GR3 imports the frozen S17 RED module's compare driver (`importlib.import_module("tests.test_s81_s17_kb_ingest")`) instead of copying ~120 lines; the frozen file is read, never edited (sha unchanged).
- DV-F2: G3-GR3 part (b) models the two compares at the live_robots seam on ONE context (bind / record / flush / repeated flush) rather than through two full compares: a full compare runs in a fresh task context and re-binds, so a context-level unbind is only observable on a repeated flush of the same context (the adversary's probe shape).
- DV-F3: the corpus gate ran concurrently with the three comm pytest runs (one pytest at a time held).

## Open questions
- none. The re-verifier (F1-8) is the orchestrator's next launch on these bytes.

# S81-G2 FIX ROUND 2 RE-VERIFY REPORT (correctness lens, Opus 5.5, 2026-11-04)

Unit S81-G2 KB-SEED fix round 2. Worktree sc-s81-g2, branch feature/s81-g2-kb-seed, HEAD e3cd49ecd240eb0fe6ebbb48c068663073436e01 (verified first and last; `git status --short` EMPTY first and last; never edited; no .qa-mutation.lock). Probes and mutants ran in a detached scratch worktree <scratchpad>/S81-G2_fix2_adv at e3cd49ec, the 17 branch files (c6fb6533..HEAD) overwritten with the real worktree bytes (sha-equal before and after: 0 mismatches), removed with `git worktree remove --force` (worktree list: none). Logs: <scratchpad>/S81-G2_fix2/rv/. Probe kept as rv/test_zz_rv2_probe_g2.py.txt (never in the repo).

VERDICT: SOUND (0 blocking, 0 major, 3 minor = stated limits by LC-4).

## RED files re-hashed (first and last, real worktree)
f014ea81 test_s81_s16_kb_seed.py; d48d38c3 s81_s16_batch_request_golden.json; 3928d706 test_s81_d09_feed_walker.py; d2fbbcf2 s81_d09_feeds.json; 2d4a6e47 test_s81_d11_pdp_discovery.py; 9489efd8 s81_d11_sitemaps.json; 0a0dfea8 test_s81_g2_gate_rows.py: all byte-identical to the brief. scripts/seed_kb_batch.py 58d7cb2d (= fix report). numstat 3d849160..HEAD: CLAUDE.md 1/1, scripts/seed_kb_batch.py 22/9, tests/test_s81_g2_gate_rows.py 90/0. seed_kb_batch.py + gate rows: LF, 0 CR, 0 bytes > 127; CLAUDE.md CRLF 1015 = LF 1015, the changed line ends CR, 0 bytes > 127 in it. ruff E9,F63,F7,F82 (+F401,F841) and py_compile clean. Commit trailer: Co-Authored-By: Claude Opus 5.5.

## The fix diff read (F2-1)
main(): `if args.resume is None:` keeps the GREEN line byte-for-byte (filter + cap); `else: kept = sorted(juices)`; `seeded = frozenset(done)` on resume only, threaded to _apply -> _read_results; `if pid in seeded: bump already_seeded` after the custom_id lookup, the result still parsed and written (insert-ignore). Resume counts start {already_seeded: 0, unmatched: 0}. Ledger / settle / delete code unchanged from fix round 1. Matches F2-1 as worded.

## RED step re-measured (GR6 / GR7 against the 3d849160 bytes of seed_kb_batch.py, in scratch, restored + sha-verified 58d7cb2d)
[pyt] tag=g2rv2-red-at-3d84 start=2026-11-04 09:46:52 end=2026-11-04 09:46:56 elapsed=4s bound=600s status=FAIL rc=1 (1 failed GR6 on `assert 'results' in ['db:kb_merchants:select', 'db:kb_specs:select']` = AssertionError; GR7 passed)

## Units ON / OFF (three RED files + tests/test_s81_kb_schema.py + the gate-rows file, real worktree)
[pyt] tag=g2rv2-units-off start=2026-11-04 09:07:56 end=2026-11-04 09:08:10 elapsed=13s bound=600s status=OK rc=0 (826 passed)
[pyt] tag=g2rv2-units-on start=2026-11-04 09:08:17 end=2026-11-04 09:08:30 elapsed=14s bound=600s status=OK rc=0 (826 passed; ENABLE_KB_SEED=apply ENABLE_FEED_WALKER=apply ENABLE_PDP_DISCOVERY=apply ENABLE_CC_CDX=true ENABLE_LLM_SPEND_BREAKER=true for that one call)

## End-to-end probe, the REAL llm_spend_breaker over the S81-04 FakeUpstash (scratch)
[pyt] tag=g2rv2-probe start=2026-11-04 09:09:20 end=2026-11-04 09:09:24 elapsed=4s bound=600s status=OK rc=0 (6 passed)
- tail_all (every juice yielded, then the stream raises; the partial run's 4 kb_specs rows carried into the resume DB): partial run = one EVAL (the reserve), offclock key = 5.0, no ledger, no delete. Resume events [kb_merchants select, kb_specs select, factory, retrieve, results, llm_spend_ledger insert, kb_products/variants/specs upsert, delete]; no further EVAL, key still 5.0; ONE ledger row {provider_batch_id = the batch, request_count 4, cost_complete True}; delete once; counts `already_seeded=4 ... succeeded=4 unmatched=0`. RV-M1 CLOSED.
- raise_after_3 (3 rows carried): same shape, ledger request_count 4, `already_seeded=3 ... unmatched=0`.
- fresh run with every juice seeded (real breaker): no factory, no EVAL, `nothing to seed` (R-G2-6 unchanged).
- fresh run with 2 of 4 seeded: the batch carries exactly the 2 unseeded juices.
- DEV-1 (cap 2, juice #0 seeded by an earlier batch, the fresh batch = #1,#2, tail raise): resume maps both (`already_seeded=2 unmatched=0`), ledger once, delete once.
- complete read whose delete FAILED, then `--resume`: total ledger rows for the batch = 2 (see rv2-m1).

## Mutants (scratch, byte copies in place, exact single-match edits, run on gate rows + test_s81_s16_kb_seed.py + the probe; restored sha 58d7cb2d verified after each and at the end)
- M2a seeded filter kept on resume: KILLED (GR6) [pyt] tag=g2rv2-mut-M2a start=2026-11-04 09:10:03 end=2026-11-04 09:10:11 elapsed=8s bound=600s status=FAIL rc=1
- M2b delete skipped on resume: KILLED (GR3, GR6, R19) [pyt] tag=g2rv2-mut-M2b start=2026-11-04 09:10:11 end=2026-11-04 09:10:19 elapsed=8s bound=600s status=FAIL rc=1
- M2c filter dropped on fresh runs: KILLED (GR7, R6) [pyt] tag=g2rv2-mut-M2c start=2026-11-04 09:10:19 end=2026-11-04 09:10:27 elapsed=8s bound=600s status=FAIL rc=1
- R1 juice cap kept on resume (DEV-1 reverted): SURVIVED the committed rows, killed only by the scratch probe [pyt] tag=g2rv2-mut-R1 start=2026-11-04 09:10:27 end=2026-11-04 09:10:36 elapsed=9s bound=600s status=FAIL rc=1 (probe only) -> rv2-m2
- R2 seeded never passed: KILLED (GR6) [pyt] tag=g2rv2-mut-R2 start=2026-11-04 09:10:36 end=2026-11-04 09:10:44 elapsed=8s bound=600s status=FAIL rc=1
- R3 already_seeded bump removed: KILLED (GR6) [pyt] tag=g2rv2-mut-R3 start=2026-11-04 09:10:44 end=2026-11-04 09:10:52 elapsed=8s bound=600s status=FAIL rc=1
- R4 resume counts init {}: KILLED (GR6, unmatched=0 term) [pyt] tag=g2rv2-mut-R4 start=2026-11-04 09:10:52 end=2026-11-04 09:11:00 elapsed=8s bound=600s status=FAIL rc=1
- R5 seeded results skipped (no insert-ignore re-write): KILLED (GR6) [pyt] tag=g2rv2-mut-R5 start=2026-11-04 09:11:00 end=2026-11-04 09:11:08 elapsed=8s bound=600s status=FAIL rc=1
- R6 no ledger on resume: KILLED (GR3, GR6, R19) [pyt] tag=g2rv2-mut-R6 start=2026-11-04 09:11:09 end=2026-11-04 09:11:17 elapsed=8s bound=600s status=FAIL rc=1
- R7 seeded counted unmatched (the rv-m3 pre-state): KILLED (GR6) [pyt] tag=g2rv2-mut-R7 start=2026-11-04 09:11:17 end=2026-11-04 09:11:25 elapsed=8s bound=600s status=FAIL rc=1
- R8 seeded set passed on fresh runs too: EQUIVALENT (a fresh run's batch excludes every seeded pid, so the bump is unreachable) [pyt] tag=g2rv2-mut-R8 start=2026-11-04 09:11:25 end=2026-11-04 09:11:32 elapsed=7s bound=600s status=OK rc=0
9 of 10 non-equivalent mutants KILLED by committed rows on AssertionError (one per fix half: the resume branch M2a/R2/R3/R4/R5/R7, the fresh branch M2c, the ledger/delete M2b/R6); R1 survives (stated, rv2-m2); R8 equivalent.

## CI-order set, comm chunks, secret scan (real worktree)
[pyt] tag=g2rv2-ci-order start=2026-11-04 09:11:56 end=2026-11-04 09:13:09 elapsed=74s bound=1200s status=OK rc=0 (spec 12.2 + gate rows, 13 files: 1381 passed)
[pyt] tag=g2rv2-comm-c3 start=2026-11-04 09:13:10 end=2026-11-04 09:13:52 elapsed=42s bound=1200s status=OK rc=0 (c3 + s08b gate rows + G2 gate rows, 23 files: 1227 passed)
[pyt] tag=g2rv2-comm-c1 start=2026-11-04 09:14:06 end=2026-11-04 09:15:12 elapsed=66s bound=1200s status=OK rc=0 (951 passed; holds the CLAUDE.md readers test_ci_gates.py + test_behavior_dimension_translation.py)
[pyt] tag=g2rv2-comm-c2 start=2026-11-04 09:15:12 end=2026-11-04 09:17:28 elapsed=135s bound=1200s status=OK rc=0 (3286 passed; re-run because CLAUDE.md changed and the fix agent did not run c2)
[pyt] tag=g2rv2-secret start=2026-11-04 09:13:52 end=2026-11-04 09:14:00 elapsed=7s bound=600s status=OK rc=0 (test_secret_scan_static.py ALONE: 31 passed)
HEAD FAILED set EMPTY over every chunk; the cached base records are EMPTY: branch-only-new EMPTY.

## Hook test files ALONE (scratch, as the previous re-verifier ran them; no TIMEOUT, slower than 08:37 on a loaded box)
[pyt] tag=g2rv2-hook-nodash start=2026-11-04 09:17:33 end=2026-11-04 09:30:32 elapsed=780s bound=1800s status=OK rc=0 (167 passed, 160 deselected)
[pyt] tag=g2rv2-hook-dash start=2026-11-04 09:30:33 end=2026-11-04 09:46:36 elapsed=964s bound=1800s status=OK rc=0 (157 passed, 3 skipped, 167 deselected)

## CLAUDE.md row and PR body against the bytes (sentence by sentence, the fix-2 hunks)
- CLAUDE.md S81-16: "`--resume <batch id>` re-derives the juice set without that filter or the juice cap (R-G2-6 governs fresh runs only)" = the else branch: TRUE. "reads that batch completely (no bound check, no reserve, no create" = bound check gated `args.resume is None`, breaker = `resume is None and ...`, no create on resume: TRUE. "a juice already owning kb_seed_batch rows counts already_seeded and its rows go through the insert-ignore writer" = the bump without continue + KbWriter upsert ignore_duplicates: TRUE (R5 killed). "no ledger row until a complete read (--resume writes it once)": TRUE for the partial-read paths (mid-stream and tail, probe); see rv2-m1 for a resume after a COMPLETE read.
- PR body S81-16 resume sentence: same claims + "(not unmatched)", "the ONE ledger row is written, then the batch is deleted after the writes" (delete gated on results_ok and writes_ok): TRUE.
- PR body "Fix round 2": the defect narrative = RV-M1 as measured: TRUE; "One code file, +22 / -9": TRUE (numstat); "(9 nodes)": TRUE (7 + 2; units 824 -> 826); GR6 RED at 3d849160 on an AssertionError, GR7 green there: TRUE (re-measured above); M2a/M2b/M2c killed as stated: TRUE (re-measured); "Juice cap on resume" rationale: TRUE (probe DEV-1; with the cap kept the resume reads `unmatched` for batch juices outside the first N sorted).
- PR body Counts (rv-m2 wording verbatim per F2-3; 826 / 826; fix round 2 3 / 3): TRUE. Gates (fix round 1) c1 sentence cites g2rv-comm-c1 951 passed, elapsed 64s: TRUE (rv-m1). Gates (fix round 2): matches the fix report's [pyt] lines; TRUE.
- PR body 22,512 B (<= 25,600), 0 CR, only the 4 emoji bytes > 127; sha f2a1eb36 = the fix report.

## Previous round's findings
- RV-M1 (MAJOR, resume after a tail raise): CLOSED (GR6, M2a, the real-breaker probe: one ledger row, the delete, no EVAL).
- rv-m1 (c1 sentence): CLOSED (PR body cites g2rv-comm-c1).
- rv-m2 (Counts wording): CLOSED (verbatim F2-3).
- rv-m3 (resume counts `unmatched`; long docstring line): CLOSED (already_seeded, R7 killed; the docstring line rewritten, no line > 100 in lines 1-25).
- Earlier rounds (M1 settle side, M2 s08b comm set, m1..m7): unchanged, closed or recorded as stated by the fix-1 re-verifier; nothing in fix 2 reopens them (GR1..GR5 green in every run above).

## MINOR (stated limits by default, LC-4)
- rv2-m1 (a second ledger row on a resume after a COMPLETE read): when a complete read has already written the ledger row but the batch delete failed (`batch delete failed` WARNING) or a write failed, an operator `--resume <id>` now reads the batch again and inserts a SECOND llm_spend_ledger row (probe: total 2; llm_spend_ledger has no unique key on provider_batch_id, 050). The delete-failed case is NEW in fix 2 (at 3d849160 that resume stopped at `nothing to seed`; M2a re-measures total 1); the write-failed case existed at GREEN / fix 1. Not production-visible (dark flag; no message directs a resume after a complete read; the breaker is not touched on resume, so the spend cap is unaffected; the ledger over-counts, the conservative side). Suggested wording for the PR body limits: "a --resume of a batch whose results read already completed writes a second ledger row; resume only a batch whose WARNING says to". A later hardening: skip the ledger insert on resume when a row with that provider_batch_id exists.
- rv2-m2 (DEV-1 unpinned): dropping the juice cap on resume has no committed row (mutant R1 survives GR1..GR7 and the s16 file; only the scratch probe kills it). Reachable only when the corpus holds more juices than KB_SEED_MAX_JUICES (500; the held corpora give at most ~50, S16 L1).
- rv2-m3 (cosmetic): on resume main() still builds requests for every corpus juice, so the `bound=... requests=N` line and the --report `requests` / `juices` list the whole corpus, not the batch (no spend effect: the bound check and the breaker are skipped on resume).

## Not run
The fourteen client fences and the full jest suite (the rebase round, LC-7; no literal under app/, .github/ or docs/ moved).

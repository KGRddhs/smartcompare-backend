# S81-G2 FIX ROUND 1 RE-VERIFY REPORT (correctness lens, Opus 5.5, 2026-11-04)

Unit S81-G2 KB-SEED fix round 1. Worktree sc-s81-g2, branch feature/s81-g2-kb-seed, HEAD 3d849160e88671bb5c01c2ef0b3c75441af11813 (verified first and last; `git status --short` EMPTY first and last; never edited). Probes and mutants ran in a detached scratch worktree <scratchpad>/S81-G2_fix1_adv at 3d849160 (the G2 files rewritten to their LF blob bytes so R27 is not environmental there; blob equality re-checked before removal: 0 mismatches; removed with `git worktree remove --force`, `git worktree list` shows none). Logs: <scratchpad>/S81-G2_fix1/rv/.

VERDICT: NOT_READY (0 blocking, 1 MAJOR, 3 minor).

## RED files re-hashed (real worktree bytes; scratch = blob bytes, equal)
f014ea81... test_s81_s16_kb_seed.py; d48d38c3... s81_s16_batch_request_golden.json; 3928d706... test_s81_d09_feed_walker.py; d2fbbcf2... s81_d09_feeds.json; 2d4a6e47... test_s81_d11_pdp_discovery.py; 9489efd8... s81_d11_sitemaps.json; f228584e... test_s81_g2_gate_rows.py: all byte-identical to the brief. numstat 07cabe47..HEAD: CLAUDE.md 2/2, scripts/seed_kb_batch.py 21/10, tests/test_s81_g2_gate_rows.py 190/0. CLAUDE.md CRLF kept (CRLF 1015 = LF 1015; the two changed lines end CR, 0 bytes > 127 in them). PR body 18,041 B (<= 25,600), 0 CR, the only bytes > 127 are the 4 of the attribution emoji.

## MAJOR
RV-M1 (F1-1 (b) not met on a reachable path; a regression vs GREEN in that case): the fix's guarantee "no ledger row until a complete read (--resume writes it once)" (RULINGS_FIX1 F1-1 (b), the CLAUDE.md S81-16 row, the PR body S81-16 + fix sections, the seed_kb_batch.py module docstring) is FALSE when the partial read has already yielded, parsed and written EVERY juice of the batch before it raises (a stream that breaks after its last JSONL line, e.g. an incomplete chunked read at the tail). The partial run then writes all juices' kb_specs rows (extractor kb_seed_batch) and, by F1-1, no ledger row and no delete; the owner's `--resume <id>` re-derives the juice set THROUGH existing_seeded (R-G2-6, main() ~L400-407), finds every juice seeded, logs "nothing to seed" and returns 0 BEFORE _apply: no results read, no llm_spend_ledger row EVER for that batch, no delete. At GREEN (07cabe47) that same run wrote one ledger row (here with all records). The breaker side stays conservative (the bound held), so the spend CAP is safe; the loss is the S81-03 ledger accounting row the owner's step 7 tells them to record, and the undeleted batch. Runtime proof (scratch probe test_zz_rv_probe_g2.py, the real llm_spend_breaker over the S81-04 FakeUpstash, the s16 Rig, synthetic values):
[pyt] tag=g2rv-probe2 start=2026-11-04 08:50:31 end=2026-11-04 08:50:35 elapsed=4s bound=600s status=FAIL rc=1 (1 failed, 3 passed)
 - raise_after_3 (realistic resume with the partial run's 3 kb_specs rows in the DB): resume events [kb_merchants select, kb_specs select, factory, retrieve, results, llm_spend_ledger insert, kb_products/variants/specs upsert, delete]; ONE ledger row with request_count 4, cost_complete True: CORRECT (the 3 already-seeded juices count `unmatched`, their usage still recorded).
 - raise_after_all (all 4 yielded, then the stream raises): seeded_after_partial=4, rc2=0, resume events [kb_merchants select, kb_specs select] only, ledger_rows=0: FAILED "the resume wrote no ledger row: the batch carries none at all".
G2-GR3 does not catch this because its resume Rig starts with an EMPTY kb_specs table (no spec_rows), so the R-G2-6 filter never sees the partial run's rows. Remedy options for the orchestrator (not chosen here): under --resume, bypass the existing_seeded filter (or still read the batch and write the ledger row) when the juice set would be empty; or write the ledger row on a partial read whose records already cover every request; plus a gate row whose resume Rig carries the partial run's kb_specs rows (both a 3-of-4 and an all-then-raise variant). If the orchestrator instead rules the tail-raise case acceptable, it becomes a stated limit and the three "--resume writes it once" sentences (CLAUDE.md, PR body, docstring) must carry the exception.

## MINOR (stated limits by default, LC-4)
rv-m1 (PR body "Gates (fix round 1)"): "Chunk c1 not re-run (no file it reaches changed)" is inaccurate: c1 holds tests/test_behavior_dimension_translation.py and tests/test_ci_gates.py, both CLAUDE.md readers, and CLAUDE.md changed. Measured here: c1 at HEAD 951 passed (below), no regression; the sentence should cite this run.
rv-m2 (PR body "Counts"): "Mutants: 50 / 50 KILLED in the RED round (re-run by the adversary on these bytes)" reads as if the adversary re-confirmed 50/50; the adversary re-applied 45 and 4 survived (W-M10, D-M5, X6, X12; answered by F1-4 / F1-5 / F1-6). Reword.
rv-m3 (cosmetic): seed_kb_batch.py docstring line 17 is about 104 chars (only E9/F63/F7/F82 are gated); on a realistic resume the already-seeded juices' results are counted `unmatched` in the counts line (harmless; can mislead the owner reading the log).

## Units ON / OFF (three RED files + tests/test_s81_kb_schema.py + the gate-rows file)
[pyt] tag=g2rv-units-off start=2026-11-04 08:28:07 end=2026-11-04 08:28:21 elapsed=14s bound=600s status=OK rc=0 (824 passed; [hermeticity] sentinel checked 824; [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=g2rv-units-on start=2026-11-04 08:28:21 end=2026-11-04 08:28:35 elapsed=13s bound=600s status=OK rc=0 (824 passed; ENABLE_KB_SEED=apply ENABLE_FEED_WALKER=apply ENABLE_PDP_DISCOVERY=apply ENABLE_CC_CDX=true ENABLE_LLM_SPEND_BREAKER=true for that one call; hermeticity 824; netguard 0)

## Partial-read path end to end, breaker ON (F1-10): the real llm_spend_breaker over FakeUpstash
[pyt] tag=g2rv-probe start=2026-11-04 08:29:23 end=2026-11-04 08:29:27 elapsed=4s bound=600s status=OK rc=0 (2 passed; hermeticity 2; netguard 0)
 - partial read (3 of 4 then raise): the offclock key holds exactly the 5.0 bound (one EVAL = the reserve; settle(None) issues no command), no ledger row, no delete; the --resume makes no EVAL, the key still 5.0, ONE ledger row, the delete.
 - complete read: two EVALs (reserve + settle), the key settles below the bound to the actual, one ledger row.
 (The tail-raise variant with a realistic DB is RV-M1.)

## Mutants (scratch worktree, byte copies in place, exact single-match edits, run on the gate-rows file + the probe file, restored, sha256 verified; lock created and removed)
M1a settle(ticket, partial sum): KILLED (GR1, rv probe) [pyt] tag=g2rv-mut-00 elapsed=5s bound=600s status=FAIL rc=1
M1b ledger row on a partial read: KILLED (GR1, GR2, GR3, rv probe) [pyt] tag=g2rv-mut-01 elapsed=5s status=FAIL rc=1
M1c second ledger row on resume: KILLED (GR3, rv probe) [pyt] tag=g2rv-mut-02 elapsed=5s status=FAIL rc=1
W-M10 (Woo path, brand from the title's first word): KILLED (GR4[absent], GR4[empty]) [pyt] tag=g2rv-mut-03 elapsed=5s status=FAIL rc=1
X12 (the D11 origin url_gate removed): KILLED (GR5[qarenbot], GR5[star]) [pyt] tag=g2rv-mut-04 elapsed=5s status=FAIL rc=1
RV-1 failed-open partial read records 0.0: KILLED (GR2) [pyt] tag=g2rv-mut-05 elapsed=5s status=FAIL rc=1
RV-2 WARNING without the batch id: KILLED (GR1, GR2) [pyt] tag=g2rv-mut-06 elapsed=5s status=FAIL rc=1
RV-3 partial read skips the parsed writes: KILLED (GR1, GR2) [pyt] tag=g2rv-mut-07 elapsed=5s status=FAIL rc=1
RV-4 partial read deletes the batch: KILLED (GR1, GR2, rv probe) [pyt] tag=g2rv-mut-08 elapsed=5s status=FAIL rc=1
RV-5 resume calls the breaker: KILLED (GR3, rv probe) [pyt] tag=g2rv-mut-09 elapsed=5s status=FAIL rc=1
RV-6 the partial-read breaker branch removed (falls to the actual settle): KILLED (GR1, GR2, rv probe) [pyt] tag=g2rv-mut-10 elapsed=5s status=FAIL rc=1
11 / 11 KILLED on AssertionError; restored sha256 seed_kb_batch.py 3196b9ff..., cron_feed_walker.py 2b224972..., cron_pdp_discovery.py b74b2eca... D-M5 / X6 EQUIVALENT per F1-6 (not reported as survivors).

## CI-order set (spec 12.2 + the gate-rows file)
[pyt] tag=g2rv-ci-order start=2026-11-04 08:31:22 end=2026-11-04 08:32:35 elapsed=73s bound=1200s status=OK rc=0 (1379 passed; [hermeticity] sentinel checked 1379; [netguard] blocked 22 attempt(s) from 21 node(s) = the hermeticity self-tests, base noise)

## Comm chunks (GREEN's chunk lists; all three re-run because CLAUDE.md readers sit in c1, c2 and c3)
[pyt] tag=g2rv-comm-c1 start=2026-11-04 08:33:08 end=2026-11-04 08:34:12 elapsed=64s bound=1200s status=OK rc=0 (951 passed; hermeticity 951; netguard blocked 22 attempt(s) from 21 node(s))
[pyt] tag=g2rv-comm-c2 start=2026-11-04 08:34:20 end=2026-11-04 08:36:36 elapsed=135s bound=1200s status=OK rc=0 (3286 passed; hermeticity 3286; netguard blocked 24 attempt(s) from 2 node(s) = the S81-04 sentinels)
[pyt] tag=g2rv-comm-c3 start=2026-11-04 08:36:45 end=2026-11-04 08:37:28 elapsed=43s bound=1200s status=OK rc=0 (c3 + tests/test_s81_s08b_gate_rows.py + the gate-rows file: 1225 passed; hermeticity 1225; netguard blocked 8 attempt(s) from 8 node(s) = the w49 sentinels)
[pyt] tag=g2rv-secret start=2026-11-04 08:37:28 end=2026-11-04 08:37:33 elapsed=5s bound=600s status=OK rc=0 (tests/test_secret_scan_static.py ALONE: 31 passed; hermeticity 31; netguard 0)
HEAD FAILED set EMPTY over the 73-file set; the cached base records (74b84ef9..., 3535b18a..., 5032a609...) are EMPTY: branch-only-new EMPTY. F1-2 record checked: base_records/c6fb6533.../5032a609...{files,txt}: 73 files incl. tests/test_s81_s08b_gate_rows.py, the set hash re-derived = 5032a609..., the .txt empty.

## Hook test files ALONE (no .githooks change; run as briefed)
[pyt] tag=g2rv-hook-nodash start=2026-11-04 08:37:45 end=2026-11-04 08:42:16 elapsed=271s bound=1800s status=OK rc=0 (167 passed, 160 deselected; hermeticity 167; netguard 0)
[pyt] tag=g2rv-hook-dash start=2026-11-04 08:42:25 end=2026-11-04 08:49:21 elapsed=416s bound=1800s status=OK rc=0 (157 passed, 3 skipped, 167 deselected; hermeticity 160; netguard 0)
No TIMEOUT.

## CLAUDE.md row and PR body against the bytes (the fix hunks, sentence by sentence)
- "the batch deleted only after a complete results read and every write succeeded" = `if results_ok and writes_ok:`: TRUE (F1-8).
- "one llm_spend_ledger row per batch (050), written only after a complete results read" = `if results_ok:`: TRUE.
- "a WARNING with the exception type name and the batch id": TRUE (exactly one WARNING; GR1/GR2 + RV-2).
- "the rows parsed so far are written; no delete": TRUE (RV-3, RV-4).
- "the reserve stays held (the ticket is settled with no actual; a failed-open reserve records nothing)": TRUE (llm_spend_breaker.settle returns before any command for an invalid actual; probe: key = bound).
- "no ledger row until a complete read (`--resume` writes it once)": FALSE in the tail-raise case: RV-M1.
- F1-3 R27 sentence: TRUE (adversary m1 measured; my scratch used the LF blob bytes, R27 green).
- F1-7 owner step (11): the three railway.*.json watchPatterns each list scripts/kb_seed_common.py: TRUE.
- PR body "One code file, +21 / -10": TRUE (numstat). GR-2 list: 21 names (4+3+10+2+1+1): TRUE. "73 files; ... record 5032a609...": TRUE. "Chunk c1 not re-run (no file it reaches changed)": rv-m1. "50 / 50 KILLED ... re-run by the adversary": rv-m2.

## The previous round's findings
M1 (partial settle): the settle / record side CLOSED (GR1, GR2, M1a, RV-1, RV-6, the probe); the ledger side closed for a mid-stream raise but RV-M1 open for a tail raise.
M2 (s08b gate rows in the comm set): CLOSED (record 5032a609..., run in c3 here, green).
m1 R27 CRLF: CLOSED as the F1-3 stated limit (CLAUDE.md + PR body) + the EOL-ATTRS follow-up.
m2 W-M10 Woo: CLOSED (GR4 kills it). m3 X12: CLOSED (GR5 kills it).
m4 D-M5 / X6: EQUIVALENT by F1-6, recorded.
m5 watch patterns: CLOSED as the F1-7 stated limit (CLAUDE.md step 11 + PR body).
m6 batch id at INFO: accepted (GR-1); the WARNING now also carries it per F1-1 (d).
m7 CLAUDE.md delete wording: CLOSED (F1-8).

## Not run
The fourteen client fences and the full jest suite (the rebase round, LC-7; no literal under app/, .github/ or docs/ moved). The scratch probe is kept as <scratchpad>/S81-G2_fix1/rv/test_zz_rv_probe_g2.py.txt (never in the repo).

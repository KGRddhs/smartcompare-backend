# S81-G2 FIX ROUND 1 REPORT (fix agent, Opus 5.5, 2026-11-04)

Unit S81-G2 KB-SEED (S81-16 + D09 + D11), worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g2, branch feature/s81-g2-kb-seed.
Start: HEAD 07cabe47a7bf052c43ef2c526869d2e36657df99, `git status --short` EMPTY (verified). End: HEAD 3d849160e88671bb5c01c2ef0b3c75441af11813 (ONE commit through the hook, "All checks passed!", trailer Co-Authored-By: Claude Opus 5.5), `git status --short` EMPTY.
Rulings applied: RULINGS_FIX1_S81_G2 F1-1..F1-9 (F1-10 / F1-11 belong to later rounds).

## Frozen RED files (re-hashed first and last: byte-identical)
f014ea81... tests/test_s81_s16_kb_seed.py; d48d38c3... tests/fixtures/s81_s16_batch_request_golden.json; 3928d706... tests/test_s81_d09_feed_walker.py; d2fbbcf2... tests/fixtures/s81_d09_feeds.json; 2d4a6e47... tests/test_s81_d11_pdp_discovery.py; 9489efd8... tests/fixtures/s81_d11_sitemaps.json.

## Files (sha256 on disk after commit; numstat vs 07cabe47)
- scripts/seed_kb_batch.py 3196b9ffa61cbba693b71af4b3f2189a7e575bf541d382eacaa62d029ed70bed (+21 -10; LF, 0 bytes > 127)
- tests/test_s81_g2_gate_rows.py f228584e9a744e52e3b776dfcfaf16001a6bb5db2016139f0e1d6a650a413ecd (+190, new; LF, 0 bytes > 127)
- CLAUDE.md 855b9863116e850c7c06dde5ce4e3fce72de196145cf8c5e1ba783e435715faa (+2 -2; CRLF kept: CR 1015 = LF 1015; 0 bytes > 127 in the added lines)
- PR body (outside the repo) <scratchpad>/S81-G2_green/PR_BODY.md 65bf30f94756bc349e25622a27dec4dbd1a8b3a6af69b2fbb14a9480aa6dac9f, 18,041 bytes (<= 25,600); backup of the pre-fix body PR_BODY.pre_fix1.bak; the only non-ASCII bytes are the 4 of the pre-existing attribution emoji.

## F1-1 code change (scripts/seed_kb_batch.py)
- `_apply`: the ledger write is wrapped in `if results_ok:`; then `if breaker and not results_ok:` settles a held ticket with `br.settle(ticket, None)` (no record when the reserve failed open), `elif breaker:` keeps the GREEN settle / record of the summed actual. Rows parsed so far are still written; the delete stays gated on `results_ok and writes_ok` (unchanged).
- `_read_results`: the WARNING is now `"%s results read failed (%s); resume with --resume batch_id=%s"` (type name + the opaque batch id, GR-1 / spec 2.8); still exactly one WARNING (R22 green).
- Module docstring: "one llm_spend_ledger row per batch, written only after a complete results read ...".
- Flag OFF: unchanged (the edit sits after the mode read and inside APPLY only; R2 / the OFF rows green).

## RED step (tests/test_s81_g2_gate_rows.py at HEAD 07cabe47)
[pyt] tag=g2fix1-red-head start=2026-11-04 08:15:00 end=2026-11-04 08:15:04 elapsed=4s bound=600s status=FAIL rc=1 ([hermeticity] sentinel checked 7 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)); 3 failed, 4 passed:
- G2-GR1 FAILED AssertionError: the ticket was settled with a partial actual (assert 0.0003 is None)
- G2-GR2 FAILED AssertionError: a failed-open reserve recorded a partial actual ([('record', 'offclock', 0.0003, 5.0)])
- G2-GR3 FAILED AssertionError: the batch carries 2 llm_spend_ledger rows across the partial run and the resume
- G2-GR4 [absent, empty] and G2-GR5 [qarenbot, star] green (pin existing behaviour; proven by W-M10 / X12 below)
Existing rows at HEAD: [pyt] tag=g2fix1-existing-head elapsed=13s bound=600s status=OK rc=0 (817 passed; hermeticity 817; netguard 0) over the three RED files + tests/test_s81_kb_schema.py.
GREEN: [pyt] tag=g2fix1-rows-green elapsed=3s bound=600s status=OK rc=0 (7 passed; hermeticity 7; netguard 0).

## Mutants (byte copies in place, exact single-match edits, -k on the killing rows, restored, sha256 verified; lock file created and removed; logs mut_*.log)
- M1a settle(ticket, partial sum) -> KILLED by GR1 ([pyt] tag=g2fix1-mut-M1a elapsed=4s status=FAIL rc=1, AssertionError)
- M1b ledger row on a partial read (`if True:`) -> KILLED by GR1 / GR2 ([pyt] tag=g2fix1-mut-M1b elapsed=4s status=FAIL rc=1)
- M1c a second ledger row on resume -> KILLED by GR3 ([pyt] tag=g2fix1-mut-M1c elapsed=4s status=FAIL rc=1)
- W-M10 (Woo path, the adversary's exact edit: brand or the title's first word) -> KILLED by GR4 x2 ([pyt] tag=g2fix1-mut-W-M10 elapsed=4s status=FAIL rc=1)
- X12 (the adversary's exact edit: the D11 origin url_gate removed) -> KILLED by GR5 x2 ([pyt] tag=g2fix1-mut-X12 elapsed=4s status=FAIL rc=1)
Restored sha256: seed_kb_batch.py 3196b9ff..., cron_feed_walker.py 2b224972..., cron_pdp_discovery.py b74b2eca... (= the pre-mutation bytes). 5 / 5 KILLED. D-M5 / X6 EQUIVALENT per F1-6 (not re-run).

## F1-2 base record (comm set 73 files)
Detached scratch worktree <scratchpad>/S81-G2_fix1/g2base at c6fb65336deab4f48275b13d3847e0f42b298984 (no junction, no node_modules), removed with `git worktree remove --force`, `git worktree list` shows none.
[pyt] tag=g2fix1-base-s08b start=2026-11-04 08:18:04 end=2026-11-04 08:18:08 elapsed=4s bound=600s status=OK rc=0 (tests/test_s81_s08b_gate_rows.py: 29 passed; hermeticity 29; netguard 0).
Record: <scratchpad>/harness/base_records/c6fb65336deab4f48275b13d3847e0f42b298984/5032a609783350df813f4ede30f9ed4e1abad3ad0a3cdda63585e202c0159add.{files,txt (EMPTY),header.txt,pyt.log}; set sha256 = sha256 of the sorted LF-joined list + trailing newline (the convention of 74b84ef9... / 3535b18a..., re-derived); 73 files = the 69-file record 3535b18a... + the three G2 RED files (absent at base) + tests/test_s81_s08b_gate_rows.py.

## Gates (every pytest through pyt.py, one at a time)
- ruff --select E9,F63,F7,F82 --no-cache scripts/seed_kb_batch.py tests/test_s81_g2_gate_rows.py: All checks passed; py_compile OK.
- [pyt] tag=g2fix1-units-off start=2026-11-04 08:18:48 elapsed=13s bound=600s status=OK rc=0 (824 passed; [hermeticity] 824; [netguard] blocked 0 attempt(s) from 0 node(s)) - the three RED files + tests/test_s81_kb_schema.py + the gate-rows file, ambient OFF.
- [pyt] tag=g2fix1-units-on start=2026-11-04 08:19:01 elapsed=13s bound=600s status=OK rc=0 (824 passed; hermeticity 824; netguard 0) - ENABLE_KB_SEED=apply ENABLE_FEED_WALKER=apply ENABLE_PDP_DISCOVERY=apply ENABLE_CC_CDX=true exported for that one call.
- [pyt] tag=g2fix1-ci-order start=2026-11-04 08:19:21 elapsed=70s bound=1200s status=OK rc=0 (spec 12.2 twelve files + the gate-rows file: 1379 passed; [hermeticity] 1379; [netguard] blocked 22 attempt(s) from 21 node(s) = the hermeticity self-tests, base noise as at GREEN).
- [pyt] tag=g2fix1-comm-c2 start=2026-11-04 08:20:44 elapsed=134s bound=1200s status=OK rc=0 (GREEN chunk2, 25 files, holds tests/test_s81_kb_schema.py: 3286 passed; hermeticity 3286; [netguard] blocked 24 attempt(s) from 2 node(s) = the S81-04 sentinels).
- [pyt] tag=g2fix1-comm-c3 start=2026-11-04 08:23:10 elapsed=41s bound=1200s status=OK rc=0 (GREEN chunk3, 21 files, holds tests/test_s81_s16_kb_seed.py, + tests/test_s81_s08b_gate_rows.py: 1218 passed; hermeticity 1218; [netguard] blocked 8 attempt(s) from 8 node(s) = the w49 sentinels).
- HEAD FAILED set of c2 + c3 EMPTY; cached base records 74b84ef9... / 3535b18a... / 5032a609... EMPTY (REUSED per LC-6 for the 72 files, the new member run at base this round): branch-only-new EMPTY. Chunk c1 not re-run (no file it reaches changed: c1 holds neither the edited script's test module nor CLAUDE.md readers touched by this diff beyond the c3 member).
- [pyt] tag=g2fix1-secret start=2026-11-04 08:23:51 elapsed=5s bound=600s status=OK rc=0 (tests/test_secret_scan_static.py ALONE: 31 passed; hermeticity 31; netguard 0).
- The fourteen client fences NOT re-run: no literal moved in app/, scripts/ (beyond a WARNING template not read by any fence), docs/ or .github/; the rebase round runs them by path.
- The FULL jest suite NOT run (the rebase round, LC-7).
- The hook test files NOT run (no .githooks change).

## Docs rulings
- CLAUDE.md G2 block (CRLF kept, names only): S81-16 row "the batch deleted only after a complete results read and every write succeeded" (F1-8); the ledger sentence + the rewritten failure-table row (F1-1); the R27 environmental stated limit (F1-3, EOL-ATTRS follow-up); owner step (11) with the kb_seed_common.py watch-pattern clause and the deliberate-run recipe (F1-7).
- PR body (patched in place through a python script): S81-16 section (F1-1 / F1-8), a "Fix round 1" section (F1-1 change, the gate rows, the mutants, F1-2 73-file set + record 5032a609..., F1-6 equivalents, the GR-2 sentence naming the 21 consumed private names), counts 824 / 824, a "Gates (fix round 1)" section, stated limits F1-3 / F1-7 / F1-1, owner step 11.

## Deviations / notes
- GR1 / GR2 force the per-run bound to 5.0 by monkeypatching `seed.request_bound` (the ruling's "reserve 5.0"); KB_SEED_MAX_USD set to 10 for those rows.
- GR3 counts the ledger rows across BOTH runs (partial then resume) - the only form that is RED at HEAD (a bare resume already writes one row at HEAD, as R19 pins).
- GR4 / GR5 are parametrized (absent / empty brands; qarenbot / star agent): 7 nodes for 5 rows.
- The gate-rows file defines its own autouse env fixture (the union of the three RED files' env deletes) and imports the three RED modules as module objects (no RED row is collected twice).
- The R27 CRLF nodes: not observed here (the worktree holds the LF bytes; the new commit's checkout warnings say LF will become CRLF the next time git touches the files, which is F1-3's environmental class).

# S81-G2 FIX ROUND 2 REPORT (fix agent, Opus 5.5, 2026-11-04)

Unit S81-G2 KB-SEED, worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g2, branch feature/s81-g2-kb-seed.
Start: HEAD 3d849160e88671bb5c01c2ef0b3c75441af11813, git status --short EMPTY. End: HEAD e3cd49ecd240eb0fe6ebbb48c068663073436e01 (ONE commit through the hook, All checks passed, trailer Co-Authored-By: Claude Opus 5.5), git status --short EMPTY, no .qa-mutation.lock.
Rulings applied: RULINGS_FIX2_S81_G2 F2-1..F2-4.

## Frozen RED files (re-hashed first and last: byte-identical)
f014ea81 test_s81_s16_kb_seed.py; d48d38c3 s81_s16_batch_request_golden.json; 3928d706 test_s81_d09_feed_walker.py; d2fbbcf2 s81_d09_feeds.json; 2d4a6e47 test_s81_d11_pdp_discovery.py; 9489efd8 s81_d11_sitemaps.json.

## Files (sha256 after commit; numstat vs 3d849160)
- scripts/seed_kb_batch.py 58d7cb2d6d916c1f26b61ce70dfa25c1123133e86c7cceb534ef5cd653fc14a4 (+22 -9; LF, 0 bytes > 127)
- tests/test_s81_g2_gate_rows.py 0a0dfea8467430eefe23e42292f2a470f8d9e477d3cf0cb92428cb99dfb536cb (+90; LF, 0 bytes > 127)
- CLAUDE.md 57e5edd9d5a218d5f6ac8fed47acffa3ba4273b5664a3fe5fec2a241632bc16e (+1 -1; CRLF 1015 = LF 1015; 0 bytes > 127 in the new text): the S81-16 row --resume sentence (without that filter or the juice cap; reads the batch completely; already_seeded; insert-ignore writer).
- PR body <scratchpad>/S81-G2_green/PR_BODY.md f2a1eb36ea3f91c9941f24b579719df29b1b5213e26b6060cc0bb2ef35593ab3, 22,512 B (<= 25,600), 0 CR, only the 4 emoji bytes > 127; backup <scratchpad>/S81-G2_fix2/PR_BODY.pre_fix2.bak.

## F2-1 code change
- main: fresh line kept byte-for-byte under `if args.resume is None:`; `else: kept = sorted(juices)` (no seeded filter, no juice cap); `seeded = frozenset(done)` only on resume, passed to _apply.
- _apply: kwarg seeded; resume counts start {already_seeded: 0, unmatched: 0} (fresh {} unchanged); passed to _read_results.
- _read_results: kwarg seeded; after the pid lookup `if pid in seeded: bump already_seeded`; the result is still parsed and written (insert-ignore). Ledger / settle / delete code untouched.
- Docstring --resume sentence rewritten (the rv-m3 long line gone with it). Flag OFF unchanged.

## RED step (gate-rows file at 3d849160, before any script edit)
[pyt] tag=g2fix2-red-head start=2026-11-04 08:57:52 end=2026-11-04 08:58:00 elapsed=9s bound=600s status=FAIL rc=1 ([hermeticity] sentinel checked 9 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)); 1 failed, 8 passed.
- G2-GR6 FAILED AssertionError: the resume never read the batch (the seeded filter emptied the juice set); assert 'results' in ['db:kb_merchants:select', 'db:kb_specs:select']
- G2-GR7 green (pins R-G2-6; M2c is the proof); GR1..GR5 (7 nodes) green.
GREEN: [pyt] tag=g2fix2-rows-green start=2026-11-04 08:58:26 end=2026-11-04 08:58:33 elapsed=8s bound=600s status=OK rc=0 (9 passed; hermeticity 9; netguard 0).

## Mutants (byte copy in place, single-match edits, lock created and removed, restored sha 58d7cb2d verified; <scratchpad>/S81-G2_fix2/mutants.py)
- M2a (seeded filter kept on resume): KILLED by GR6 [pyt] tag=g2fix2-mut-M2a start=2026-11-04 08:58:47 end=2026-11-04 08:58:52 elapsed=4s bound=600s status=FAIL rc=1 (AssertionError)
- M2b (delete skipped on a complete resume read): KILLED by GR6 [pyt] tag=g2fix2-mut-M2b start=2026-11-04 08:58:52 end=2026-11-04 08:58:56 elapsed=4s bound=600s status=FAIL rc=1 (AssertionError)
- M2c (filter dropped on fresh runs too): KILLED by GR7 + test_s16_r06 [pyt] tag=g2fix2-mut-M2c start=2026-11-04 08:58:56 end=2026-11-04 08:59:01 elapsed=4s bound=600s status=FAIL rc=1 (AssertionError)
3 / 3 KILLED.

## Gates
- ruff --select E9,F63,F7,F82 + py_compile on both touched python files: clean.
- [pyt] tag=g2fix2-units-off start=2026-11-04 08:59:30 end=2026-11-04 08:59:43 elapsed=13s bound=600s status=OK rc=0 (826 passed; hermeticity 826; netguard blocked 0 from 0)
- [pyt] tag=g2fix2-units-on start=2026-11-04 08:59:43 end=2026-11-04 08:59:57 elapsed=13s bound=600s status=OK rc=0 (826 passed; hermeticity 826; netguard 0; ENABLE_KB_SEED=apply ENABLE_FEED_WALKER=apply ENABLE_PDP_DISCOVERY=apply ENABLE_CC_CDX=true for that one call)
- [pyt] tag=g2fix2-ci-order start=2026-11-04 09:00:10 end=2026-11-04 09:01:23 elapsed=73s bound=1200s status=OK rc=0 (spec 12.2 + gate rows: 1381 passed; hermeticity 1381; netguard blocked 22 from 21 nodes = hermeticity self-tests, base noise)
- [pyt] tag=g2fix2-comm-c3 start=2026-11-04 09:01:29 end=2026-11-04 09:02:11 elapsed=42s bound=1200s status=OK rc=0 (chunk3 + test_s81_s08b_gate_rows.py + gate rows: 1227 passed; hermeticity 1227; netguard blocked 8 from 8 = w49 sentinels)
- extra CLAUDE.md reader: [pyt] tag=g2fix2-claudemd-reader start=2026-11-04 09:02:25 end=2026-11-04 09:02:28 elapsed=2s bound=600s status=OK rc=0 (test_behavior_dimension_translation.py 27 passed; netguard 0); test_ci_gates.py green in the CI-order set.
- HEAD FAILED set EMPTY; cached base records 74b84ef9 / 3535b18a / 5032a609 EMPTY, REUSED (LC-6): branch-only-new EMPTY.
- [pyt] tag=g2fix2-secret start=2026-11-04 09:02:18 end=2026-11-04 09:02:25 elapsed=7s bound=600s status=OK rc=0 (test_secret_scan_static.py ALONE 31 passed; netguard 0)
- NOT run (the rebase round): the fourteen client fences, the FULL jest, the hook test files (no .githooks change). No TIMEOUT.

## Docs (F2-3)
- PR body: S81-16 --resume sentence; Counts line reworded as F2-3 rv-m2 says (+ 826 / 826 and the fix-round tallies); c1 sentence cites [pyt] tag=g2rv-comm-c1 951 passed (rv-m1); new Fix round 2 and Gates (fix round 2) sections.
- CLAUDE.md: the one S81-16 sentence (needed: the old wording beside the R-G2-6 skip clause implied the filter on resume).

## Deviations
- DEV-1: on --resume the KB_SEED_MAX_JUICES cap is dropped as well as the filter (the cap bounds what is SENT; a capped unfiltered set could leave batch juices unmapped -> unmatched -> rows lost after the delete). No dedicated row pins it.
- DEV-2: resume counts start with already_seeded=0 unmatched=0 so the apply line always carries both terms; fresh counts unchanged.
- GR6 uses its own tail-raise generator (Rig.results_raise_after cannot raise after the last item); caplog cleared before the resume.

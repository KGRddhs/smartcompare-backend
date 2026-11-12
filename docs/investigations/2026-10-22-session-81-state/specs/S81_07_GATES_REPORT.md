# S81-07 MEAS-CLAUDE-GATE: GATES AND DOCS REPORT (Opus 5.5, 2026-11-12, 05:45-07:00 AST)

Written by a shell python step (the harness refuses a subagent's Write of a report .md).
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s07, branch feature/s81-07-meas-claude-gate.
Start: HEAD 4ed9226bbacce930bf3829f0090fc6e4078238b7, git status empty (verified). RED file 30ac9d7b... unchanged (frozen; not edited).
End: HEAD f10c6ae34fcf72232f88362e094801bad954a80c (ONE docs commit, CLAUDE.md only, through the hook, no --no-verify; HEAD moved verified). git status --short: empty.
Footprint 6b909e0a..HEAD: CLAUDE.md, scripts/meas_claude_gate.py, tests/_env_safety.py, tests/fixtures/s81_s07/{_gen_fixtures.py, compare_pairs.json, fragrance_names.json, moderation_parity.json, verdict_gold.json, web_search_domains.json}, tests/test_s81_s07_meas_harness.py. No app/ byte.

## (1) Mutation table on the REAL script (GC-17)
- Detached scratch worktree <notes>/scratch at 4ed9226b (python only, no junction). The autocrlf checkout made the six s81_s07 fixtures CRLF, so R35 was red there (1 failed / 163 passed, [pyt] tag=s07g-mutbase elapsed=85s status=FAIL rc=1); the fixtures were rewritten from their git blobs (sha256 equal to the GREEN report's) -> [pyt] tag=s07g-mutbase start=2026-11-12 05:56:12 end=2026-11-12 05:57:24 elapsed=72s bound=600s status=OK rc=0 (164 passed; hermeticity 164; netguard 0).
- 78 mutants: M01-M61 (59 strings as the RED round's table; M04 and M42 re-anchored, same meaning) + G06, G07, G08, G09a, G09b, G10, G11a, G11b, G12a-d (four comparison flips), G13a-d, G14. Each an exact-string edit matching once (checked: 78/78), CRLF kept, under <scratch>/.qa-mutation.lock, the unit file through pyt.py (bound 600, -x), restored from the byte copy, sha256 verified after EVERY run (CRLF c38854da...; LF form = 44f6eb83... = the committed blob). Lock removed.
- RESULT: 78 KILLED, 0 SURVIVED, 0 NOT MEASURED, 0 ERROR nodes; all 78 [pyt] lines status=FAIL rc=1, slowest 60 s. 77 die on an AssertionError at the first killing row. M60's first row (R25) failed on a KeyError (the stage stops), so it was re-run alone with -k "r65 or r25": R65 fails on an AssertionError ([pyt] tag=s07g-mut-M60 start=2026-11-12 06:50:42 end=2026-11-12 06:50:50 elapsed=8s bound=600s status=FAIL rc=1). Netguard 0 on 77 runs; on G08 the pytest netguard blocked the R68 sentinel resolve the mutant lets through.
- Full table: MUTATION_TABLE_S81_07.md (sha256 0088bb6a...), raw: mutation_results.json (-x run), mutation_results_k.json (M60 recheck), logs mut_<id>.log (mut_M60_x.log = the -x run).
- Scratch worktree removed with git worktree remove --force (twice: after the table and after the M60 recheck); absent from git worktree list; path gone.

## (2) Comm set at HEAD (GC-15, GC-17)
- The RED list (156) UNION 26 files of a HEAD re-derivation (derive_comm.py: unit refs, _env_safety importers, CLAUDE.md readers, scripts readers, walkers, router / pricing / model / breaker importers; the 26 are scripts readers of other scripts and repo walkers, added for union safety) = 182, minus the pre-commit hook files; lists written LF and read back; 8 chunks (25 x 7 + 7), bound 1200, one at a time, wait-free probe before, 45 s after. CLAUDE.md block in place (the readers test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire are members).
- [pyt] tag=s07g-comm-c1 start=2026-11-12 06:31:10 end=2026-11-12 06:32:14 elapsed=65s bound=1200s status=OK rc=0
- [pyt] tag=s07g-comm-c2 start=2026-11-12 06:33:01 end=2026-11-12 06:33:15 elapsed=14s bound=1200s status=OK rc=0
- [pyt] tag=s07g-comm-c3 start=2026-11-12 06:34:04 end=2026-11-12 06:36:08 elapsed=124s bound=1200s status=OK rc=0
- [pyt] tag=s07g-comm-c4 start=2026-11-12 06:37:03 end=2026-11-12 06:39:01 elapsed=118s bound=1200s status=OK rc=0
- [pyt] tag=s07g-comm-c5 start=2026-11-12 06:39:51 end=2026-11-12 06:42:01 elapsed=130s bound=1200s status=FAIL rc=1
- [pyt] tag=s07g-comm-c6 start=2026-11-12 06:42:53 end=2026-11-12 06:44:23 elapsed=91s bound=1200s status=FAIL rc=1
- [pyt] tag=s07g-comm-c7 start=2026-11-12 06:45:10 end=2026-11-12 06:46:24 elapsed=74s bound=1200s status=OK rc=0
- [pyt] tag=s07g-comm-c8 start=2026-11-12 06:47:11 end=2026-11-12 06:47:23 elapsed=12s bound=1200s status=OK rc=0
- Summaries: c1 1321 passed; c2 473 passed; c3 724 passed; c4 1129 passed; c5 1 failed / 2398 passed; c6 11 failed / 2490 passed; c7 961 passed / 35 xfailed; c8 483 passed.
- HEAD failures 12 = base_failed_ids.txt 12 (the CRLF hygiene nodes); branch-only-new EMPTY; base-only none. Netguard blocked 241 attempts at HEAD = 241 in the base record (per-host equality not compared).

## (3) Client fences (14, by path through the junction; no foreign jest)
- jest 29.7.0; [jest] tag=s07g-fences start=2026-11-12 06:07:21 end=2026-11-12 06:07:45 rc=1
- Test Suites: 1 failed, 13 passed, 14 total / Tests: 4 failed, 236 passed, 240 total. The only failures: config/nativeBundle.w37 d5, k2, k4, k5 = the four accepted node_modules drift nodes. Green by the accepted-base rule. Nothing else of the client suite run.

## (4) CLAUDE.md
- Written from the git blob (LF) after asserting the CRLF working copy equals blob CRLF-converted; the S81-07 block (9 lines + one blank) after the S81-04c owner-steps bullet, one blank line before ## Tests; the :341 Feature Flags pointer sentence after the S81-04c one (merge order). Added text pure ASCII (the one non-ASCII added line is the pre-existing :341 line). Committed blob sha256 5bb55974...; diff 11 insertions, 1 deletion. Names only, no value; no key=value literal (the hook passed).
- Content: stages, the credential (one variable, stripped, removed from the environment, explicit client, request hook), refused names, the guard in every mode, the hard ceiling (reservation, intent line, booking table, lock released on every exit), the sticky StageStop and exit codes, pass bars by reference to R-S07-31, who runs it + the R-S07-28 command shape + the dry-run totals, L1-L15, follow-up ids none, owner steps.
- Readers run in the comm set (above): green.

## (5) PR body
- PR_BODY.md sha256 f6cc57cd..., 23,648 bytes (<= 24,000, python), 0 CR, pure ASCII apart from the last line (the robot line, checked).

## Deviations / notes (stated)
- D1 the mutation table ran with -x (the first killing row recorded); the full killing set per mutant is not recorded except M60 (re-run with -k).
- D2 a fresh Windows checkout with core.autocrlf=true gives CRLF fixtures and a red R35 (the GC-15 CRLF-hygiene class; the blobs and the unit worktree are LF). Stated in the PR body's limits; no .gitattributes change made (out of this unit's footprint).
- D3 the docs commit was made before the comm run (content identical; the comm ran on the committed bytes).
- D4 the scratch worktree was created twice (sequentially, same path; one at a time), the second only for the M60 recheck.
- No network, no live API, no variable set, no .env read, no secret printed.

## Verdict
READY_FOR_ADVERSARIES: 78/78 killed, branch-only-new EMPTY, fences green (accepted base nodes only).

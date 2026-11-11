# MON1 fix round 1 RE-VERIFIER report (correctness lens; Opus 5.5; 2026-11-12)

HEAD verified 95f50119ac9aeb05d8025bad4400aa6d93c0ad69 (sc-inc-mon1, fix/inc-mon1-llm-credential-health); worktree status clean at start and end; never edited. Scratch: detached worktree <SP>/m1rv at 95f50119 (core.autocrlf=false, so bytes = blobs), sha-verified, mutation lock created and removed, removed with `git worktree remove --force` + prune (0 rows left).

## VERDICT: SOUND (0 blocking, 0 major; minors = stated limits by LC-4)

## Hashes (start and end, worktree and scratch)
- tests/test_inc_mon1_credential_health.py 10061c0a64da034588602258d5020c015f97e95f7020e9eb0251a2c94bf56c71 (frozen, unchanged)
- tests/test_inc_mon1_probe.py 2950c33e70d30a3dd69361a9726ce1421b778c4a9a00354067b213a530845880 (frozen, unchanged)
- tests/test_inc_mon1_gate_rows.py d8a07d4fed1be7e6c62a9f6986972f58b5bfca1389afef27a3f31e567aff05dc (G1-G4 byte-identical: the diff c6592b53..HEAD is one pure-append hunk after line 154)
- app/services/llm_credential_health.py blob d1cfd190...5c49; CLAUDE.md blob e9134bf3...3131 (both = the fix report)

## Footprint
`git diff --stat c6592b53 95f50119` = CLAUDE.md (2 lines rewritten in place, no whole-file diff), app/services/llm_credential_health.py, tests/test_inc_mon1_gate_rows.py. Nothing outside B.3 + gate rows + the CLAUDE.md block. content_safety_service.py unchanged. Fix-round added lines: 0 bytes > 127; no sk-/eyJ/PEM/credentialed-URL/8-digit shape.

## Runs ([pyt] lines)
- [pyt] tag=inc-mon1-rv-unit-on start=2026-11-12 00:51:09 end=2026-11-12 00:51:37 elapsed=29s bound=600s status=OK rc=0 (ENABLE_LLM_CREDENTIAL_PROBE=true; 146 passed; netguard 0; hermeticity 146)
- [pyt] tag=inc-mon1-rv-unit-off start=2026-11-12 00:51:43 end=2026-11-12 00:52:12 elapsed=29s bound=600s status=OK rc=0 (=false; 146 passed; netguard 0)
- [pyt] tag=inc-mon1-rv-ciorder start=2026-11-12 01:00:24 elapsed=1s status=FAIL rc=4 (MY usage error: CR in the file list; not a result). Re-run: [pyt] tag=inc-mon1-rv-ciorder2 start=2026-11-12 01:00:33 end=2026-11-12 01:01:56 elapsed=83s bound=1200s status=OK rc=0 (1535 passed, 0 failed; the fix round's GC-11 order, 21 files: the s20 lifespan user first, the RED files, the gate rows, the sentry suites; netguard blocked 69 from 13 nodes = the fix agent's count). The fix agent's 1533 + 2 s24 CRLF failures = 1535: in the LF scratch the two base CRLF rows pass.
- Comm chunks of B.4 (the fix agent's 69 files = 68 + the gate-rows file; re-derived independently by git grep over tests/ for llm_credential_health|content_safety_service|sentry_service|"/health: my 56 hits are inside the 69 except tests/conftest.py and tests/_env_safety.py, which are not test files):
  - [pyt] tag=inc-mon1-rv-comm-00 start=2026-11-12 01:02:29 end=01:03:40 elapsed=71s bound=1200s status=OK rc=0 (2004 passed, 1 skipped; netguard 3 from 3)
  - [pyt] tag=inc-mon1-rv-comm-01 start=2026-11-12 01:03:47 end=01:06:21 elapsed=154s bound=1200s status=OK rc=0 (2498 passed; netguard 26 from 4)
  - [pyt] tag=inc-mon1-rv-comm-02 start=2026-11-12 01:06:28 end=01:07:48 elapsed=80s bound=1200s status=OK rc=0 (2562 passed; netguard 123 from 58)
  - Zero FAILED ids at HEAD in all three: `comm -13` against base record 23f5330f is EMPTY (the three base-record failures the fix agent saw are CRLF / environmental and pass in the LF scratch).
  - Extra chunk (CLAUDE.md changed, so the CLAUDE.md readers + the named source-scanning pins absent from the 69): [pyt] tag=inc-mon1-rv-comm-03x start=2026-11-12 01:08:02 end=01:08:18 elapsed=16s bound=1200s status=OK rc=0 (257 passed: test_ci_gates, test_behavior_dimension_translation, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69)
- Hook test files ALONE (no TIMEOUT, no re-run needed):
  - [pyt] tag=inc-mon1-rv-hooks-nodash start=2026-11-12 01:08:26 end=01:32:08 elapsed=1422s bound=1800s status=OK rc=0 (167 passed, 160 deselected)
  - [pyt] tag=inc-mon1-rv-hooks-dash start=2026-11-12 01:34:13 end=02:01:32 elapsed=1639s bound=1800s status=OK rc=0 (157 passed, 3 skipped, 167 deselected)

## Mutants (15 applied on sha-verified byte copies in the scratch; every restore sha256-verified; driver MON1_fix1/rv/rv_mutants.py, logs MON1_fix1/rv/mut_*.log; each run over the three unit files, bound 600)
| id | change | result |
|---|---|---|
| RV1 (B.5) | pending mark never set | KILLED G11 + G12 (AssertionError); [pyt] inc-mon1-rv-mut-rv1_ 30s FAIL rc=1 |
| RV2 (B.5) | pending emitted without waiting for the cool-down | KILLED G11 + G12; rv2_ 30s FAIL rc=1 |
| RV3 (B.5) | sliding window (a suppressed send re-stamps) | KILLED G10; rv3_ 29s FAIL rc=1 |
| RV4 (B.5) | moderation success clears quota | KILLED G13; rv4_ 30s FAIL rc=1 |
| RV5 (B.5) | note_success moved above the awaited moderation call (content_safety_service) | KILLED G14; rv5_ 30s FAIL rc=1 |
| RV6 (own, F1-1) | mark survives a transition out | KILLED G11 transition-out; rv6_ 30s FAIL rc=1 |
| RV7 (own, F1-1) | two events for one mark (mark not deleted) | KILLED G11 + G12; rv7_ 30s FAIL rc=1 |
| RV8 (own, F1-1) | pending fires on a NON-confirming outcome (a transition out sends the held event) | KILLED L08 + G10 + G11 transition-out; rv8_ 30s FAIL rc=1 |
| RV9 (own, F1-1/F1-2) | the late event does not stamp the window (line 237 removed) | SURVIVED (146 passed; rv9_ 28s OK rc=0) -> minor m1 |
| RV10 (own, F1-3) | moderation ignores its own source (a moderation-raised 403) | KILLED H08; rv10 30s FAIL rc=1 |
| RV11 (own, F1-3) | moderation clears any rejected (a dispatch 403 too) | KILLED G13; rv11 30s FAIL rc=1 |
| RV12 (own) | _reset_credential_health_state keeps _PENDING | SURVIVED (146 passed; rv12 29s OK rc=0) -> minor m2 (test helper) |
| RX1 (prev AM22) | snapshot returns live records, on the FIX bytes | KILLED G9; rx1_ 30s FAIL rc=1 |
| RX2 (prev AM17) | cancel without await, on the fix bytes | first anchor matched twice (INVALID, not run); unique anchor: KILLED G6 (done False, cancelled False); rx2_ 30s FAIL rc=1 |
| RX3 (prev A09) | monitor leaf absent -> 503 | KILLED G5; rx3_ 30s FAIL rc=1 |
13 valid kills (all AssertionError), 2 survivors (gaps on correct code): the five B.5 mutants + six of my own against F1-1 / F1-3 + three previous survivors.

## Flap replay (MON1_fix1/rv/flap_replay.py, output flap_replay.out; the real leaf, the real openai 401 class, a fake clock, a fake sender)
1. The adversary's sequence (rejected dispatch 401 at t0, moderation ok t+1, rejected t+6 inside the window, ten failures hourly): events [rejected, ok, rejected]; the third is emitted by the first failure after the window (t+3606) and never again; final newest=rejected held=rejected. Before the fix: [rejected, ok] for ever.
2. The same with a dispatch recovery: [rejected, ok] until the failure at t+1006, then [rejected, ok, rejected], no further event.
3. A suppressed recovery with no later traffic: newest=ok held=ok (the earlier ok event already agrees).
4. A suppressed recovery then a served call after the window: a second `ok` event is sent (m3).
5. A late event then a quick flap: the late rejected stamps the window; a rejected 10 s later is suppressed and held pending (newest ok, held rejected until the next confirming failure after the window: by design, F1-1).

## Code read (llm_credential_health.py at HEAD)
F1-1: the mark is set only when emit_alert returns False and the provider still holds that state (:256-260); a confirming outcome after the window deletes the mark, stamps and sends once outside the lock (:232-238, :244-245); any transition clears every mark of the provider over STATES incl. ok (:239-242). F1-2: `_cooled` only reads; only an admitted or a late event stamps (:205-209, :292, :237). F1-3: `_moderation_may_clear` (:194-202) mirrors `_probe_may_clear`; its early return writes no state and emits nothing; the router maps the Claude moderation site to source moderation (llm_router.py:990, :1007); a dispatch success clears any state. No await, no I/O, no new import, no new log line; emit_alert returns bool and its exception arm returns True (no pending mark on an internal error).

## Previous-round findings
Correctness: minor 1 (PP3) closed by F1-4 (PP3 + owner step 1); minor 2 (flap) closed by F1-1 (replayed above); minor 3 (moderation clears quota / 403) closed by F1-3 (G13, RV4, RV11); minor 4 survivors AM08 / AM17 / AM18 / AM22 closed by G10 / G6 / G8 / G9 (AM17 and AM22 re-killed on the fix bytes here); minor 5 sha labels recorded in the fix report ("working-copy bytes (CRLF)"); minor 6 serper_keys conditional: PP1; minor 7 the first ok line: L-16. Observability: M1 closed (PP3: one more EVENT, a second NOTIFICATION only after 24 h, matching A1-2); m1 G5 (A09 re-killed here), m2 G6, m3 G7, m4 G14 (RV5), m5 L-3 + F1-1, m6 L-14, m7 L-15, m8 L-17. None open.

## PR body (MON1_fix1/PR_BODY.md) against the bytes
22,990 bytes (python), limit 25,600; 4 bytes > 127 = the attribution line only; LF. "merged, NOT yet proven" present; no "resolved" / "done"; the one "fixed" is "fixed cool-down window". O2 and O3 named OPEN. PP3 is passable as worded. The alert bullet, the moderation sentence (incl. the Claude moderation site), "No new log line", L-3, L-9, L-14..L-17, the defect table and the fix-round numbers (146 / 146, 1533 + 2, 2004 / 2498 / 2559 + 3, eight fix mutants, nine pin kills) match the code and the measured runs. The CLAUDE.md block: both rewritten sentences match the code.

## MINORS (stated limits by default, LC-4; none production-visible)
- m1 RV9 survives: the stamp of a late (pending) event, app/services/llm_credential_health.py:237, is unpinned; without it a re-entry into the same state right after a late event would send a second event inside 900 s. Runtime correct (replay 5). A one-row follow-up (late event, flap, re-entry inside the window -> no event) would pin it.
- m2 RV12 survives: `_reset_credential_health_state` clearing `_PENDING` (:386) is unpinned (test-support helper only).
- m3 A suppressed recovery is emitted late even when the newest emitted event already says ok (replay 4: events [rejected, ok, ok]); one redundant info-level event in the same issue; conforms to F1-1 as written.
- m4 `_PENDING` stores the suppressed status (:260) but the late send uses the confirming outcome's status (:245); the stored value is never read (dead data, harmless).
- m5 PR_BODY.md:79 says "the 69 test files that name ... plus the gate-rows file"; the measured set is 68 files plus the gate-rows file = 69.
- m6 The fix round's comm chunks did not include the CLAUDE.md readers although CLAUDE.md changed (brief union rule); closed by measurement here (comm-03x, 257 passed).
- m7 PR_BODY.md:114, owner step 1 carries the meta phrase "One sentence on what follows from that:" (cosmetic).

## Not measured
Nothing; no TIMEOUT. Client jest fences not run (no literal they read moves in this round, agreeing with the fix report).

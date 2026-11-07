# S81-24 FIX ROUND 1 RE-VERIFIER REPORT (correctness lens), Opus 5.5, 2026-11-07

## VERDICT: NOT_READY (0 blocking, 1 MAJOR, 4 minor). The F1-1 code fix holds at runtime on CPython 3.12.9 and every mutant is killed. The MAJOR is another comm-closure membership miss. It measured green, so it can be closed by recording the measurement.

HEAD verified ba4079cce1bb0adfcab2fb6f35efa9f31278bc92 (sc-s81-s24, status clean). The scratch worktree S81-24_fix1_adv was detached, with core.autocrlf=false so the LF working copies equal the blobs, and had no junction. It was sha-verified before and after, then REMOVED. The real worktree was never edited.

Hashes (the blob and the working copy are equal):
- frozen RED 7fdf71db5b2cc43e34b24674b62d3eb57e117b1c8fa683719471b10c4c562228
- fix1_rows f96a9dd8e47c65641c3b01da15200f56c21f640ac32f13e91d969e8419bc23ba
- gate_rows 5b5916139bd6a1b43708a681f7b8c05ddd3a086940cd99d9c8c444961590c233
- auth_throttle.py 4ed97e78fef5f74ca26735ba844fcd545671fb45870ab79bed1993c97b2590c7 (matches the fix report)

The frozen file was re-hashed last from the LF blob: 7fdf71db..., unchanged.

## Runs ([pyt] lines)
- [pyt] tag=s24rv-red-off start=2026-11-07 12:12:25 end=2026-11-07 12:12:34 elapsed=9s bound=600s status=OK rc=0 (212 passed; flags unset)
- [pyt] tag=s24rv-red-on start=2026-11-07 12:12:34 end=2026-11-07 12:12:42 elapsed=8s bound=600s status=OK rc=0 (212 passed; V2, a synthetic pepper, the 8 knobs and the hop flag exported)
- [pyt] tag=s24rv-probe start=2026-11-07 12:15:49 end=2026-11-07 12:15:57 elapsed=8s bound=600s status=OK rc=0 (my 9 probes passed)
- [pyt] tag=s24rv-missed start=2026-11-07 12:24:04 end=2026-11-07 12:24:11 elapsed=7s bound=1200s status=OK rc=0 (27 passed: test_s81_d17b_coverage_paging, test_m13_04_full_stream_deadline, test_m18_region_guard_prescoring)
- [pyt] tag=s24rv-ci start=2026-11-07 12:24:40 end=2026-11-07 12:25:33 elapsed=53s bound=1200s status=FAIL rc=1 (2 failed, 789 passed, 1 skipped; the 2 failures are the two baselined test_auth_interceptor social nodes, same as base)
- [pyt] tag=s24rv-comm-chunk_00 start=2026-11-07 12:25:49 end=2026-11-07 12:26:17 elapsed=29s bound=1200s status=FAIL rc=1 (2 failed, the same two social ids; 780 passed)
- [pyt] tag=s24rv-comm-chunk_10 start=2026-11-07 12:26:18 end=2026-11-07 12:27:28 elapsed=70s bound=1200s status=OK rc=0 (2406 passed; includes test_s81_s10_gate_rows)
- [pyt] tag=s24rv-comm-chunk_11 start=2026-11-07 12:27:28 end=2026-11-07 12:28:37 elapsed=69s bound=1200s status=OK rc=0 (2139 passed, 1 xfailed)
- [pyt] tag=s24rv-off-identity start=2026-11-07 12:29:05 end=2026-11-07 12:29:10 elapsed=5s bound=600s status=OK rc=0 (P70-P73, 103 passed)
- [pyt] tag=s24rv-hooks start=2026-11-07 12:29:18 end=2026-11-07 12:47:27 elapsed=1089s bound=1200s status=OK rc=0 (the four test_precommit_hook*.py ALONE: 324 passed, 3 skipped; no TIMEOUT)
- The 12 mutant runs: tags s24rv-RV-*, 12:18:44 to 12:21:38, 14 to 19 s each, every one status=FAIL rc=1 (table below).

Notes on the runs:
- Chunks 10 and 11: in an LF checkout, the fix agent's 7 + 8 environmental failures pass. They are CRLF working-copy hygiene artifacts. No failure appears only on the branch.
- OFF identity: both flags were set to false, with the pepper and every knob exported on top of the rows' own _full_config. Result: no EVAL; the Redis command sequence is the W1-9b one; the header sets are equal; no [AUTH_THROTTLE] or [HOP_PROBE] line; the pool is never built.

## F1-1 runtime truth (probe file S81-24_fix1_rv/test_zz_rv_probe.py)
Setup: CPython 3.12.9, the module's REAL 4-thread pool, the real shield + wait_for, and the DEFAULT loop exception handler (logger 'asyncio').

- p1, three error types (ConnectionError, a class named UpstashError, TimeoutError). wait_for times out at 0.05 s and the job raises at 0.25 s with a message that contains the email. Results:
  - no 'never retrieved' record;
  - exactly one WARNING `[AUTH_THROTTLE] record failed endpoint=login_fail type=<T>`;
  - one memoised skipped TimeoutError line;
  - no message text, no email, no exc_info;
  - the EVAL landed (LOGIN_FAIL_SCRIPT, finished).
- p2, four concurrent abandoned writes that fail. No never-retrieved record. FOUR record-failed WARNINGs (they are not memoised) and ONE skipped line (memoised). See m-RV2.
- p3, a timeout followed by a late success. Nothing is logged beyond the skipped line, and the write landed.
- p4, a fast failure the caller sees. Only the skipped line; no record-failed line.
- p5, a task cancel (a client disconnect) followed by a late raise. CancelledError propagates, one record-failed WARNING is logged, and there is no skipped line.
- p6, a gate-read timeout followed by a late raise. Only `skipped endpoint=login type=TimeoutError`; no never-retrieved record.
- RV-M10 reverts the hunk to f8f64d9d. It fails p1 (all three), p2, p5 and both F1-R1 nodes, so the probe detects the original defect.

## Mutants
Each mutant was applied in place from a sha-verified byte copy (under S81-24_fix1_rv/mut/) and restored sha-equal afterwards. Each ran against the frozen file, both new files and the probe. Details are in S81-24_fix1_rv/mutants.json.

| id | change | result (killed by) |
|---|---|---|
| RV-M1 | add_done_callback removed | KILLED, 7 nodes (F1-R1 x2 + probes) |
| RV-M2 | the callback re-raises (fut.result()) | KILLED, 7 nodes (F1-R1 x2 + probes) |
| RV-M3 | the WARNING carries the message text | KILLED, 6 nodes (F1-R1 x2, p1 x3, p5) |
| RV-M4 | pepper.strip() removed from the HMAC key | KILLED, 3 nodes (G24-GR1 x3) |
| RV-M5 | unknown-endpoint guard removed | KILLED, 5 nodes (G24-GR2 x5) |
| RV-M6 | the three presence booleans by truthiness (request_id.py) | KILLED, 1 node (G24-GR3) |
| RV-M7 | the abandoned flag is never set | KILLED, 7 nodes (F1-R1 x2 + probes) |
| RV-M8 | shield removed from the durable write | KILLED, 9 nodes (frozen r68, F1-R1, F1-R3, probes) |
| RV-M9 | the gate read is shielded | KILLED, 3 nodes (frozen r68, F1-R2, p6) |
| RV-O1 | retry floor max(1,..) changed to max(0,..) (an original-class mutant) | KILLED, 2 nodes (frozen r51) |
| RV-O2 | SKIP_LOG_MEMO_SECONDS changed from 60 to 0 (an original-class mutant) | KILLED, 3 nodes (frozen r01, r67, p2) |
| RV-M10 | the F1-1 hunk reverted | KILLED, 7 nodes |

12 of 12 killed, 0 survivors.

## Closure completeness
I derived the closure myself with an AST walk over tests/**/*.py. It covers:
- Import and ImportFrom, including relative imports;
- a bare `import test_x`;
- ANY string constant `tests.<mod>` anywhere in a file, which catches the variable-indirect form importlib.import_module(NAME);
- a scan for by-path loaders.

**MAJOR MAJ-RV1.** tests/test_s81_d17b_coverage_paging.py imports the member tests/test_s81_d17_coverage.py, through `D17 = "tests.test_s81_d17_coverage"` (:26) and `importlib.import_module(D17)` (:39). It is in NEITHER the 364 (a9a3f4b3) NOR the widened 370 (e3b889e4).
- Why it was missed: the fix agent's walk read only literal import_module arguments, so it missed the form where the argument is a name. Its sibling test_s81_d16b_operator_dates.py uses the same form and is already a member.
- Rule: RULINGS_FIX1 D says "a missing member is a MAJOR".
- Measured: 0 failed at HEAD (s24rv-missed). Its base outcome at daf86d32 is in the stored ea0d2f1b... record (the file is a member there, with 0 FAILED ids). So `comm -13` stays EMPTY with the file included.
- Fix:
  - add the file to the comm set of record, as a new record = e3b889e4 + this file, reusing the base from ea0d2f1b;
  - add it to the final round's replay set;
  - name it in the PR body's closure sentence.
  - No code change is needed.

Other derived hits:
- test_s81_s10_gate_rows: added by the fix, correctly.
- The two fixtures/_gen_* generators and test_precommit_hook_phase_b_round2: excluded, correctly. The hook files ran alone here and were green.
- Support direction (not required by F1-2): the fix took the five first-level modules. Two second-level modules, test_m13_04_full_stream_deadline and test_m18_region_guard_prescoring, are imported by the addition test_prescoring_showable_guard and are not in the set. They ran green here (m-RV3).
- By-path loader scan: no test loads a member by file path.
- In the widened set but not derived by me: none.

## CLAUDE.md block and PR body checked against the bytes
**CLAUDE.md** (2 lines edited in place, LF blob). Every statement checks out:
- the leaf wording (stdlib + fastapi.HTTPException);
- the done-callback / record-failed sentence: constants only, and never the never-retrieved ERROR, in every ordering including the L-F1 race;
- the ints-only parser sentence matches _parse_reply;
- the G24-GR1..GR3 sentence matches the rows;
- L1 narrowed, L8 and L-S24-17..19 match F1-4.

Not stated in the block: the record-failed WARNING has no memo, and L-F1 appears only in the PR body (both are m-RV2).

**PR body** (15,621 bytes, within 25,600; ASCII except the 4-byte attribution emoji; LF). Every sentence checks out except these three:
- (a) The closure sentence leaves out test_s81_d17b_coverage_paging (part of MAJ-RV1).
- (b) The change table is headed "git diff --numstat daf86d32 HEAD" but carries the GREEN numbers: auth_throttle.py shows 464 lines, and at HEAD it is 495 (m-RV1).
- (c) "The four tests/test_precommit_hook*.py NOT RUN" is the fix agent's statement. This re-verifier ran them alone: 324 passed, 3 skipped.

## Previous-round findings
**Correctness adversary:**
- MAJ-C1: closed for test_s81_s10_gate_rows (added, green both sides). The closure re-derivation itself is incomplete (MAJ-RV1).
- m1, m2, m3: closed by G24-GR1..GR3 (RV-M4, M5 and M6 killed).
- m4: closed (the PR body states the ints-only parser).
- m5: closed (the CLAUDE.md wording).
- m6: closed (L1 narrowed).
- m7a / m7b: recorded as L-S24-18 / L-S24-17.
- m8: recorded as a process note (re-hash from the blob). I reproduced it here with autocrlf=false.

**Security adversary:**
- F1: CLOSED. Verified at runtime by p1-p6 and by mutants M1, M2, M3, M7 and M10.
- m1: recorded as L-S24-19.
- m2: recorded as L8.
- m3: the DAY_KEY_TTL_SECONDS ruled exception is stated.
- m4: stated in the PR body.

## Minors (LC-4: stated limits)
- m-RV1: the PR body's change table has stale numbers (auth_throttle.py 464 instead of 495 at HEAD). The final round re-cuts the body.
- m-RV2: the record-failed WARNING fires once per abandoned failing write and sits outside the 60 s memo (in p2, 4 writes gave 4 WARNINGs). WARNING is below Sentry's event level, so the effect is log volume only. L-F1 is also missing from the CLAUDE.md block. State both.
- m-RV3: the support-direction widening "for completeness" goes one level deep only. test_m13_04 and test_m18_region_guard_prescoring are missing; both are green here. F1-2 does not require them.
- m-RV4: part of the fix agent's 20 environmental failure ids are a CRLF working-copy artifact (15 of them pass in an LF checkout). The set is identical on both sides, so comm -13 is unaffected.

## State
- No .env was read. Synthetic values were exported in single runner calls only.
- One pytest at a time; the only other Python processes were the two stall_monitor processes.
- Every mutant target was restored sha-equal.
- The scratch worktree was removed; `git worktree list` no longer shows fix1_adv.
- sc-s81-s24 is at HEAD ba4079cc with a clean status.

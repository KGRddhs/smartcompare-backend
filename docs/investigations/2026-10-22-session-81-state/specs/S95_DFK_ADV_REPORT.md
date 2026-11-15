# S95-DFK ADVERSARY REPORT (one adversary, LC-1; Opus 5.5), 2026-11-15 21:44-22:15 AST

VERDICT: SOUND. Blocking 0, major 0, minors 4 (stated limits by LC-4).

## Bytes under review
- HEAD 5e5912d630e2b0c3d75c65c91406d6118f87b768 (verified), branch fix/s95-deflake-retro-w0-1, git status --short empty (before, after, and after my lock removal).
- 6104eebd..HEAD: ONE commit, ONE file tests/test_retro_w0_1.py (+30 / -7); merge-base = base. Blob 7209787b -> 0c7bb578.
- app/utils/url_validator.py identical at base and HEAD (blob f7024383; wc sha256 595f6e58...).
- Commit subject exactly as spec section 3; body 4 lines; trailer Co-Authored-By: Claude Opus 5.5.

## CHECK 1 - line by line (static1.py, AST over git show bytes)
- Assertions: LOST 0. The only new one is the D1 precondition (assert blocker in stub.started_at, with a message). Raw count 91 -> 93 because ast.walk visits the nested _drive from both functions.
- Changed top-level defs: _start_near_deadline and test_red_late_start_healthy_host_is_not_blacklisted ONLY. The sibling test_red_resolve_started_just_before_deadline_is_not_memoised is AST-identical. With on_caller_returned=None the helper is base + D1, so the sibling changes only by D1.
- Removed: await asyncio.sleep(0.1) (D1) and time.sleep(0.4) (D3). Added waits: a 5 ms poll bounded at 5 s, and caller_returned.wait(10.0). No new time.sleep and no new fixed-duration assumption.
- Every wait on the flaky path is bounded: D1 5 s; the late wait_for 2.0 s; await parked (the blocker's wait_for) 2.0 s; late_done poll 10 s; retry 2.0 s; worker threads 20 s (blocker) and 10 s (late).
- Bytes: 0 non-ASCII, 0 tabs, 1041 lines all CRLF; working copy == blob with CRLF; not a whole-file diff.
- Docstrings (helper and flaky test) match the code. No other file references the helper; nothing under tests/ or app/ reads this file as source (grep).

## CHECK 2 - the race is gone by construction
- Event order at HEAD:
  1. wait_for times out at the 2.0 s bound.
  2. validate_external_url_async returns False; any memo write happens here, before the return.
  3. _drive calls on_caller_returned -> caller_returned.set().
  4. Only now can _late_healthy leave its wait, set late_done and return _PUBLIC; the cfut result and the done-callback follow.
- So the resolve result cannot exist before the caller's timeout fired. The only escape is the 10 s bound on the wait, and that needs a loop blocked for about 8 s. "verdict is False" is causal now, no longer a timing outcome. The D1 poll waits for a real event (the blocker's resolve STARTED, recorded inside the worker), and the FIFO single worker then guarantees the late job queues behind it.
- R1: 20 separate runner calls (s95k-adv-r1-01..20, each after waitfree, -k the flaky test): 20/20 "1 passed, 29 deselected" in about 3.95 s, status=OK rc=0, netguard blocked 0, hermeticity 1 each.
  - In-process repeat is NOT usable here: pytest 9.1.1 collects 3 items with --keep-duplicates but RUNS 1 (s95k-adv-collect, s95k-adv-r1-flaky20: "1 passed").
- Caveat: on this Windows box the BASE flaky test does not fail either (deflake P1: 0/30, the same-iteration tie under the 15.6 ms clock). So these passes are necessary but not sufficient; the proof is the causal order above.

## CHECK 3 - power (my own driver advdrv.py and my own mutant texts)
- Method:
  - Lock W/.qa-mutation.lock created 21:58:21 and removed after the last restore.
  - Byte copies taken before every mutant; after each run, sha256 restore AND git hash-object == the HEAD blob, both MATCH for all 14 runs.
  - Base = the test file swapped to the base bytes (sha256 4acaadc8...d708, checked), restored after each run.
- Mutants:
  - M1 = "if ran is not None:" (memoise any started timeout)
  - M2 = an early return at the top of _clear_negative_if_resolved_public
  - M3 = the stamp moved from inside _resolve to just before submit
  - M12 = M1 + M2
  - extra M4 = the late-write re-check (if cfut.done(): _clear_negative_if_resolved_public(...)) removed
  - extra M14 = M1 + M4
- Results, near-deadline pair (killed by; F = flaky test, S = sibling):

| mutant | base | head | same |
|---|---|---|---|
| M1 nd | S (memo_now False, ran 0.41 s); F passes | S; F passes | yes |
| M2 nd | none (2 passed) | none (2 passed) | yes |
| M3 nd | S (ran 0.41 s); F passes | S; F passes | yes |
| M12 nd | S + F (memo_later still False) | S + F | yes |
| M14 nd | S; F passes | S; F passes | yes |

- Whole-file mutant runs (identical kill sets at base and HEAD):
  - M2: 4 nodes: test_pin_callback_treats_a_cancelled_resolve_as_a_normal_outcome, test_pin_negative_written_after_the_zombie_returned_is_still_dropped, test_pin_zombie_success_clears_but_never_writes_a_positive_memo, test_red_slow_but_successful_resolve_leaves_no_negative_memo. My M2 is broader than the deflake agent's pop->pass M2 (3 nodes), which accounts for the extra cancelled-callback node.
  - M4: test_pin_negative_written_after_the_zombie_returned_is_still_dropped.
- Every kill is an AssertionError on an existing message. No mutant killed at base survives at HEAD: no weakening.
- M4 matters: the HEAD flaky test never exercises the late-write re-check, by construction. That path keeps its own killing pin, so the file lost no power.
- [pyt] lines: s95k-adv-{head,base}-{M1,M3,M12,M14}-nd status=FAIL rc=1; s95k-adv-{head,base}-M2-nd status=OK rc=0; s95k-adv-{head,base}-{M2,M4}-file status=FAIL rc=1 (full lines in mutants.jsonl).

## CHECK 4 - whole file and P5 at HEAD
- [pyt] tag=s95k-adv-r2-file 22:06:36-22:06:54 elapsed=19s bound=600s status=OK rc=0: 30 passed in 17.99s (30 PASSED), hermeticity 30, netguard 0.
- [pyt] tag=s95k-adv-r3-p5 22:06:55-22:08:32 elapsed=97s bound=600s status=OK rc=0: test_retailer_url_bahrain_l13, test_retro_r_auth_fixer_pins, test_retro_w0_1, test_retro_w0_2, test_retro_w0_4 in C order, one process: 237 passed, 23 warnings in 96.06s; hermeticity 237, netguard 0.

## MINORS (stated limits)
- m1 Root cause inferred, CI log not read (no network here; the deflake report also lists CI as NOT MEASURED). The fix removes the zero-margin verdict race. It does not touch the 0.4 s-margin preconditions: the Timer at 0.8 T must fire and the late job must start before the 2.0 s deadline, for both late_started is not None and late_done.is_set(). GATE QUESTION: confirm from one CI failure (#403 / #404 / #405 era / #407) that the failing line was "assert verdict is False" ("assert True is False").
- m2 With on_caller_returned set, the helper's observations (returned_at, memo_now, late_started) are read only AFTER the zombie is released. So they are no longer "IMMEDIATELY after the late call returned" for such a caller; under M1, memo_now may already be cleared. Spec D2 prescribes this order and the new docstring sentence states it. The only caller that sets the hook discards returned_at and memo_now. Calling the hook after the three reads would have kept the contract strict for every caller. No assertion is affected today.
- m3 Pre-existing, untouched: _drive_and_retry still settles with a fixed await asyncio.sleep(0.2) after late_done (late_done is set before the resolve returns and its done-callback runs). The real code never writes a memo for the late host, so nothing depends on it. Under M1 it can only add kills, never hide one.
- m4 Pre-existing: the flaky test's start precondition is late_started is not None, not the sibling's late_started < returned_at. If the late job starts just after the deadline (it loses the cancel race), the test passes while exercising the queued-never-started path. Not introduced by this diff.

## NOT MEASURED
- Linux / CI behaviour (no network, no push).
- I did not re-run the base 30+30 margin probe (P1/P2); the HEAD claim is proven by the causal order and R1.

## Files (notes folder)
- advdrv.py (driver), static1.py, mkreport.py, base_lf.py / head_lf.py / head_wc.bytes (byte snapshots)
- mutants.jsonl, runs.jsonl, the r1_*, r2_file, r3_p5 and mut_* logs and outs
- uv_copy_* / tf_copy_* restore copies, notes.md

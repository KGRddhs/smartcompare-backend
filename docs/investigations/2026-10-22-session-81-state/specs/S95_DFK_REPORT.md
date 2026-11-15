# S95-DFK REPORT (deflake agent, Opus 5.5), 2026-11-15

- Unit S95-DFK, TEST-ONLY, one file: tests/test_retro_w0_1.py. Verdict: COMMITTED.
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s95-dfk, branch fix/s95-deflake-retro-w0-1.
- Base 6104eebd7020cc009589b87afb4a73eb8aa5434d. HEAD 5e5912d630e2b0c3d75c65c91406d6118f87b768 (parent = base).
- Step 0: HEAD = base, git status --short empty, file blob sha256 7c320d454976de0f14500970dabf4c06f33f01422b09d91e08dd85fde1385d45 (matches the spec prefix 7c320d454976de0f).
- Box clocks (measured): time.monotonic = GetTickCount64, resolution 0.015625 s; asyncio ProactorEventLoop _clock_resolution 0.015625. Python 3.12.9 win64, pytest 9.1.1.

## P1 BASE MEASUREMENT (base bytes, working copy sha256 4acaadc8...d708)
Mechanism: an UNCOMMITTED probe in the notes folder (probe_s95dfk.py) runs the REAL test bodies 30 times each in ONE runner process (parametrized items). Per item it wraps _start_near_deadline (late-behaviour finish stamp, drive tuple) and uv._validate_url_offloop_or_sync (late caller return stamp), all with time.perf_counter.
margin = (late resolve finish) - (late caller return).
No shared state, proved per item by an entry check (all 120 items, 0 problems): memo empty, uv._DNS_POOL pristine, helper and entry not patched, FLAG / TIMEOUT / POOL env unset, no live dns-resolve worker or Timer thread after a bounded wait. Threads at entry were always 2 (main + this item's pytest-timeout timer). Each item has its own monkeypatch and the module's autouse _zero_network / _isolate fixtures.

| test (base) | runs | failures | margin min | median | max | negative |
|---|---|---|---|---|---|---|
| flaky test_red_late_start_healthy_host_is_not_blacklisted | 30 | 0 | -0.000795 s | -0.000352 s | +0.024282 s | 23/30 |
| sibling test_red_resolve_started_just_before_deadline_is_not_memoised | 30 | 0 | +0.000342 s | +0.000399 s | +0.000516 s | 0/30 |

- Flaky base detail: late begin 1.6007..1.6135 s after the call; late run 0.4000..0.4005 s; caller return 1.9890..2.0143 s; finish 2.0009..2.0139 s after the call's start stamp.
- THE RACE DID NOT SHOW AS A FAILURE ON THIS BOX (0/30 flaky, 0/30 sibling). The margins do show the zero designed margin: in 23/30 runs the late resolve FINISHED BEFORE ITS CALLER RETURNED (by 0.3-0.8 ms).
- Why the verdict stayed False on this box, read from the code plus these timings: the result's IOCP wakeup made the loop process the overdue timeout in the same iteration, and wait_for's timeout cancel wins a same-iteration tie. Also, the Windows threading.Timer wakes 0.7-13.5 ms late, so here the finish always landed after call start + 2.0 s.
- On Linux CI (ns loop clock, ~0.1 ms wakeups) the finish lands within a fraction of a millisecond of the precise deadline. A result that lands first wins wait_for: verdict True, the observed CI failure. This is an inference; CI itself was NOT measured.
- Sibling base: positive by construction (its late resolve hangs until the finally). ran_for 0.375..0.422 s (< 0.5 T).
- Void attempts (probe defects, not measurements), kept as void_* / coarse_monotonic_* files:
  - s95k-p1-flaky: the entry check counted pytest-timeout's own per-item Timer thread.
  - s95k-p1-flaky2: monotonic stamps at 15.6 ms resolution; 30 passed, 25/30 margins exactly 0.

## P2 HEAD MEASUREMENT (head bytes, working copy sha256 b675d15d...d3f; same probe, same mechanism)
| test (head) | runs | failures | margin min | median | max | negative |
|---|---|---|---|---|---|---|
| flaky | 30 | 0 | +0.000067 s | +0.000081 s | +0.000117 s | 0/30 |
| sibling | 30 | 0 | +0.000342 s | +0.000387 s | +0.000522 s | 0/30 |
- Flaky head: positive in 30/30 by construction. The resolve blocks on caller_returned, which the helper sets after the late await returned. Timings:
  - callback - caller return 0.0000 s; finish - callback +0.0001 s
  - late run 0.378..0.421 s (~0.2 T at the caller's timeout); ran_for 0.375..0.422 s (< 0.75 T, so not memoised, as ruling 2 needs)
  - memo_now None 30/30; verdict False 30/30

## P3 POWER (byte copies of app/utils/url_validator.py; lock W/.qa-mutation.lock created 21:31:33, removed 21:37:37 after the last restore; every restore sha256 MATCH 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d)
Selection nd = the two near-deadline tests of the REAL file (-k on both names).
- M1 = "if ran is not None:" in place of the 0.75 T gate (memoise any started timeout).
- M2 = the done-callback's _DNS_MEMO.pop(hostname, None) -> pass (keep the negative).
- M3 = started_at initialised to [time.monotonic()] at submit, the append inside _resolve removed.
- M12 = M1 + M2 (an extra row: the flaky test's own memo power).

| mutant | base: killed by | head: killed by | same at head |
|---|---|---|---|
| M1 | sibling (memo_now False) ; flaky PASSES | sibling ; flaky PASSES | yes |
| M2 | NONE of the two (2 passed) | NONE of the two (2 passed) | yes |
| M3 | sibling (memo_now False, ran 0.41 s) ; flaky PASSES | sibling ; flaky PASSES | yes |
| M12 | sibling (memo_now) AND flaky (memo_later still False) | sibling AND flaky | yes |

- M2, whole file (-k none), killed at base AND head by the same three nodes:
  - test_pin_negative_written_after_the_zombie_returned_is_still_dropped
  - test_pin_zombie_success_clears_but_never_writes_a_positive_memo
  - test_red_slow_but_successful_resolve_leaves_no_negative_memo
  (base 3 failed 27 passed in 18.93s; head 3 failed 27 passed in 18.70s)
- Why M2 escapes both near-deadline tests: no False is ever written for the late host while ruling 2 holds, so there is nothing for ruling 3 to drop. The flaky test pins rulings 2 + 3 only jointly (M12). The original R-W0 PR text in docs/investigations/2026-09-24-session-66-close-state/journal_R-W0-green.json already states this ("removing either one alone leaves that test green. Each mechanism has its own killing pin").
- No mutant killed at base survives at head: the spec's BLOCKED condition is not met.

## P4 (head, whole file)
- s95k-p4-file: 30 passed in 18.12s (-v: 30 PASSED).
- ruff --select E9,F63,F7,F82: "All checks passed!". py_compile OK.
- Added bytes: 0 non-ASCII, 0 tabs.
- 1041 lines, all CRLF (0 bare LF). git diff --stat: 1 file, 30 insertions(+), 7 deletions(-), not a whole-file diff.

## P5 (CI single-process order)
- s95k-p5-ciorder ran ONE call with the C-sorted neighbours, two on each side: tests/test_retailer_url_bahrain_l13.py, test_retro_r_auth_fixer_pins.py, test_retro_w0_1.py, test_retro_w0_2.py, test_retro_w0_4.py.
- Result: 237 passed, 23 warnings in 98.18s.

## COMMIT
- 5e5912d630e2b0c3d75c65c91406d6118f87b768 on fix/s95-deflake-retro-w0-1, parent 6104eebd. Through .githooks/pre-commit (ruff "All checks passed!"); no --no-verify, no push.
- Subject exactly as the spec, body 4 lines, trailer "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
- show --stat: tests/test_retro_w0_1.py | 37 (30+, 7-), 1 file. git status --short after: empty.
- Committed blob sha256 (LF) 1f84495638de7aba04d4759f926f6c7bf34e25834ee47ad4084586a36c7e140b; working copy (CRLF) b675d15d56ec783b096508eb137d5f7d96ba674d3c2ea1ef954fc60e6db14d3f.

## THE CHANGE (D1-D3, Edit tool, after a byte copy base_test_retro_w0_1.py.bytes sha256 4acaadc8...d708)
- D1: _drive polls blocker in stub.started_at every 0.005 s for at most 5 s, then asserts it. The message: "precondition: the blocker must occupy the single resolver worker before the late call starts (its resolve had not started after 5 s)".
- D2: _start_near_deadline(monkeypatch, *, late_behaviour, on_caller_returned=None). It is called right after the late await and before returned_at is read.
- D3: _late_healthy runs caller_returned.wait(10.0), then late_done.set(), then returns _PUBLIC. The test passes on_caller_returned=caller_returned.set.
- Docstring of the flaky test rewritten (ASCII): the order comes from an event, not a 0.2 T sleep.
- Every existing assertion and message is unchanged; one assertion was added (D1).

## DEVIATIONS / OBSERVATIONS
1. P1 expectation "some negative or failing": negatives YES (23/30 flaky), failures NO (0/30). The race does not fail on this Windows box (see P1); the zero margin is the defect.
2. P3 expectation "each mutant KILLED by at least one of the two near-deadline tests": M2 is NOT killed by either, at base AND at head (identical, so not a weakening). Evidence for ruling 3:
   - the three killing nodes of the same file, at base and head
   - the extra combined row M12, killed by both tests at base and head
3. The helper docstring gained one sentence documenting the new keyword (part of D2). No other docstring, test, helper or file changed.
4. The "second race" in spec section 0 (the late host taking the worker first), checked by reading the code, not by measurement. The blocker's submit happens in the parked task's first step, before the late call, and the ThreadPoolExecutor queue is FIFO, so the worker always takes the blocker first. D1 still makes the parked-worker precondition explicit and drops the fixed sleep.
5. P1/P2 used the one-process repeat mechanism with the per-item entry check. No separate -k runner calls of the real file were made beyond the mutant, P4 and P5 calls.
6. Probe jsonl fields caller_rel and returned_at_minus_caller_ret mix the monotonic and perf_counter epochs. They are INVALID and not used.

## STATED LIMITS (spec section 4, unchanged)
- L-1: the sibling keeps its own wall-clock bound (it gains only D1).
- L-2: the other timing-based tests are untouched.

## NOT MEASURED
- Linux / CI behaviour (no CI run, no push). The CI failure mechanism above is inferred from the code and the measured margins.

## FILES (sha256 on disk)
- C:/Users/SynAckITPC/Documents/AI/sc-s95-dfk/tests/test_retro_w0_1.py b675d15d56ec783b096508eb137d5f7d96ba674d3c2ea1ef954fc60e6db14d3f
- C:/Users/SynAckITPC/Documents/AI/sc-s95-dfk/app/utils/url_validator.py 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/base_test_retro_w0_1.py.bytes 4acaadc87d8e7053fdeb61c65caed37f98d834e15951ca6ac9fcf25f1929d708
- <notes>/coarse_monotonic_base_flaky.jsonl d9cdaf05bdf01761fd507a195dd1290c1171b73af3de5e8760b08c8098a0ae1e
- <notes>/commit_msg.txt 63b504ad478d20ee6ae17f9d6ba731906b8c68476993d5fc1dff7556253a8794
- <notes>/mutants.jsonl 21c111e9629dd52c59c01745d38c7dd5e93fd2eaf7130f2e517dfc2f8885e005
- <notes>/mutdrv.py 27f09d68587a45cc24c8e69c3b920000dbd786bc4e2deb0fd279c4567a20ee84
- <notes>/notes.md 99d6f00838d08682f63767413c1574882bebbcad878a25ab781cfd8aa87b039e
- <notes>/probe_4acaadc87d8e7053_flaky.jsonl c2e5b7c7aa9aa7eb5f2e17bc2553ff02bdb447bbc9d6926cd749cd7b961f047a
- <notes>/probe_4acaadc87d8e7053_sibling.jsonl 05809ddcf2c93fb2b225751344b2a7cc28b6a208840ae52a4c9335daf5c2c294
- <notes>/probe_b675d15d56ec783b_flaky.jsonl db7890f9a4f83e3ffb5732bb3089951f9246ebaa8ca371bb4521a7b0cf872ccf
- <notes>/probe_b675d15d56ec783b_sibling.jsonl ac3b5c67c5387932be04fff1bdac344384638bc11a35786e75ccfa22ac37351e
- <notes>/probe_part1.txt 161ec72d2214cc2b0e8d2cf520a2ddff3e69565f52489ccbd6fdf6dc74d2eca2
- <notes>/probe_part2.txt acd0a1971df3d75faf8985c32cb6f20f3f6ea5c82b240ab0519902a2c4ea761e
- <notes>/probe_s95dfk.py 69a78ddf06702f2625ff3a7aeb01c5e16efa8cf4129be3abdc18e99d39f557ae
- <notes>/summ.py 410e2b9573b7d2033914906babc103c1a2a04beb77d6df62b83c77abc5d59fcf
- <notes>/uv_copy_base_M1.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_base_M12.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_base_M2.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_base_M3.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_head_M1.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_head_M12.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_head_M2.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/uv_copy_head_M3.bytes 595f6e58b97b888fca47ad5f94b146d108424b9072be50cdb037e0dffbda056d
- <notes>/void_probe_defect_pytest_timeout_timer.jsonl a4eb0d3c67b972e32e39a31797580546d2991a1d3640e2efaee3f781f21b7f95

## GIT STATUS (worktree, after the commit)
- git status --short: empty (no untracked file; the mutation lock was removed).


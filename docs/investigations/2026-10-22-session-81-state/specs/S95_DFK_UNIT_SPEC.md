# S95-DFK RETRO-W0-1 DEFLAKE: unit spec (session 95, 2026-11-15)

- Unit: S95-DFK, TEST-ONLY (one file: `tests/test_retro_w0_1.py`), no flag, SAFE by LC-1; one adversary; no re-verifier for a test-only fix round (LC-2).
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s95-dfk, branch fix/s95-deflake-retro-w0-1, base = origin/main 6104eebd7020cc009589b87afb4a73eb8aa5434d (git status empty at start; NO node_modules junction: no client gate applies). The file's base git sha256 prefix 7c320d454976de0f.
- Evidence: the orchestrator (2026-11-15): `tests/test_retro_w0_1.py::test_red_late_start_healthy_host_is_not_blacklisted` failed the FIRST CI run of #403, #404, the #405 era and #407; each passed on one re-run.

## 0. WHAT (the race, read by the orchestrator at base)
`_start_near_deadline` (:458-492) uses a one-worker pool and the bound T = 2.0 s. It parks a blocker on the worker after a fixed `await asyncio.sleep(0.1)`, starts a `threading.Timer(0.8 * T, release_blocker.set)`, then calls the validator for the "late" host, whose resolve can start only after the blocker is released (about 0.8 T after the call began). In the flaky test (:540-583), `_late_healthy` then sleeps 0.4 s (0.2 T) and returns a public address, so the late resolve FINISHES at about 0.8 T + 0.2 T = T, exactly the caller's 2.0 s deadline: zero designed margin. Scheduler jitter decides whether the caller has already timed out (`verdict is False`, as asserted) or sees the resolve finish first (`verdict` True: the assertion fails). Second race: the fixed 0.1 s sleep assumes the blocker reached the single worker; on a slow runner it may not have, and the late host could take the worker first.

## 1. THE CHANGE (test-only; every assertion and message of the file stays)
- D1: in `_start_near_deadline._drive`, replace `await asyncio.sleep(0.1)` with a bounded wait until the stub records that the BLOCKER started (`stub.started_at` holds the blocker host), polling every 0.005 s for at most 5 s; then assert that precondition with a clear message. Both near-deadline tests use the helper and both gain this.
- D2: `_start_near_deadline` gains one optional keyword `on_caller_returned=None` (a no-argument callable), called inside `_drive` immediately after `verdict = await uv._validate_url_offloop_or_sync(...)` and before `returned_at` is read. Default None: the other caller (`test_red_resolve_started_just_before_deadline_is_not_memoised`) is unchanged apart from D1.
- D3: in `test_red_late_start_healthy_host_is_not_blacklisted`, `_late_healthy` waits on a `threading.Event` `caller_returned` (set through `on_caller_returned`) with a 10 s bound instead of `time.sleep(0.4)`, then sets `late_done` and returns `_PUBLIC`. So the late resolve finishes strictly AFTER its caller timed out, by construction. Its run time when the caller timed out stays about 0.2 T (it still starts at about 0.8 T), which is what ruling 2 (memoise a timeout only when the resolve ran for the bound) needs. If `caller_returned` is not set within 10 s, the resolve still returns (a bounded wait), and the test's existing preconditions report it.
- The docstring of the flaky test says (ASCII) that the late resolve finishes after the caller returned by an event, not by a 0.2 T sleep. No other test, helper or file changes.

## 2. PROOF (the deflake agent)
- P1 BASE MEASUREMENT: at base bytes, run the flaky test and its sibling 30 times each (separate runner calls with -k, or one process with a repeat mechanism you prove does not share state across iterations), and measure the race directly with an UNCOMMITTED probe in your notes folder that instruments the same helper: the margin = (late resolve finish time) - (caller return time) per run; report min / median / max and the failure count. Expected: margins near 0, some negative or failing.
- P2 HEAD MEASUREMENT: the same 30 + 30 runs at the change: 0 failures; the margin is positive in every run by construction.
- P3 POWER (the test still pins what it pinned): on byte copies of `app/utils/url_validator.py` (restore and sha-check after each, under the mutation lock), mutants: M1 memoise a timeout regardless of how long the resolve ran (break ruling 2); M2 keep a negative memo after a successful zombie resolve (break ruling 3); M3 record the start time at submit instead of inside `_resolve`. Each mutant must be KILLED by at least one of the two near-deadline tests at head exactly as at base (record which test kills which mutant at base and at head; a mutant killed at base and not at head is a weakening = BLOCKED).
- P4: the whole file at head through the runner (all nodes pass); ruff E9/F63/F7/F82 and py_compile on it; pure ASCII added bytes; CRLF kept (a whole-file diff is a defect).
- P5: no CI-order side effect: run the file together with the test files alphabetically adjacent to it in tests/ in ONE runner call (the CI single-process order), all pass.

## 3. COMMIT
ONE commit holding only `tests/test_retro_w0_1.py`; subject `test(s95): deflake the late-start healthy-host race in test_retro_w0_1 (event ordering instead of a zero-margin sleep)`; a body of at most four lines; the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; through the hook, never --no-verify, never a push.

## 4. STATED LIMITS
- L-1: the sibling test `test_red_resolve_started_just_before_deadline_is_not_memoised` keeps its own wall-clock bound (its late resolve hangs on an event); it gains only D1.
- L-2: the other timing-based tests of the file (the zombie and run-fraction pins) are not touched; the CI record shows no flake in them.

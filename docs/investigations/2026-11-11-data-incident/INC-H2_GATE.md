# GATE_INC_H2: the RED gate of INC-H2 STORED-ROW GUARDS (orchestrator S96-FIX, 2026-11-17 ~09:40 AST)

VERDICT: RED GATE PASSED. GREEN starts once PR #418 has merged to main, branching from that merge.

## 1. The frozen file
- tests/test_inc_h2_smart_pick_guard.py, sha256 e0bbb9958a493d4a2a02d20293a65c425df720485e5d263a670cb30dd92371c1, 20,190 bytes.
- It is untracked in C:/Users/SynAckITPC/Documents/AI/sc-inc-h2 (detached at 8bb97fe0).
- Re-hash it first and last. A wrong row is reported, never edited.

## 2. The base run at 8bb97fe0
- 66 RED rows fail, every one on an AssertionError; 35 PIN rows pass.
- The prototype passes 101/101 with the flag ON and 101/101 with it OFF.
- Mutants: 13 of 14 killed. M03b survived.

## 3. Rulings
- H2R-10 (M03b): EQUIVALENT, accepted. Reading ENABLE_SMART_PICK_BHD_ONLY once per `_select_smart_pick` call, before the loop, is still read per call. It does no currency read while the flag is OFF and behaves the same. GREEN may read it either there or as the predicate's first statement, and states which.
- H2R-11 (D3): the reader's name is `home_routes.smart_pick_bhd_only_enabled`, as B0 and B5 pin it.
- H2R-12 (D1, D2, D4): the deviations are accepted. Frozen literal goldens replace the digests. Rows A6, B0, B5, B6, R1b and R1c are added. A6 reads "right after the status skip" through the module global.
- H2R-13: the client fences were deferred from RED, which is accepted. GREEN runs them once by path.
- H2R-14 (INC-T0, the relay's ruling of 09:25): INC-H2's PR also carries INC-T0 CONFTEST-BREAKER-RESET.
  - What it adds: tests/conftest.py gets an autouse fixture that, after each test, calls llm_spend_breaker._reset_spend_breaker_state() and llm_router._reset_router_state(). Each call is guarded the way the existing _reset_credential_health_state fixture is.
  - Its RED rows go in the same new test file? NO: the H2 file is frozen. They go in a second new file, tests/test_inc_t0_conftest_breaker_reset.py, written by GREEN as a RED-first step. It holds two rows, each of which sets a latch in one test and reads /health in the next test of the same file. Prove the rows RED at base before the conftest edit.
  - The P2 files' own fixtures stay as they are; they are harmless duplicates.

## 4. GREEN builds
- On app/api/home_routes.py:
  - part A: `if _pair_price_sizes_differ(full): continue` right after the status skip;
  - part B: the reader plus a currency predicate, exactly the rule at :190;
  - the INC-T0 conftest fixture.
- In CLAUDE.md: the flag row, plus a short unit block after the INC-P2 block.
- Comm set: the RED comm list (<SP>/INC-H2/red/comm_list.txt) plus every test file that reads /health, plus the CLAUDE.md readers, plus the fourteen client fences.
- Then run the whole tests/ tree in ONE alphabetical process. INC-T0 touches the shared conftest, so a chunked record is not enough (feedback-chunked-record-hides-cross-file-state-leaks).
- Commit trailer: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>. No push, no PR.

## 5. Flip note items
- Part A goes live on merge, and stays inert until P2 stamps rows.
- ENABLE_SMART_PICK_BHD_ONLY gets its own window.
- The link lane's INC-U1b needs ENABLE_SMART_PICK_BHD_ONLY ON.
- Rollback: set the flag false.

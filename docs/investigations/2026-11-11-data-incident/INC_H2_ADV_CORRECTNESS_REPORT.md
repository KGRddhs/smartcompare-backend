# INC-H2 ADVERSARY REPORT, lens: correctness (engineering checks folded in, LC-1 SAFE unit)

Unit: INC-H2 STORED-ROW GUARDS (part A unflagged, part B ENABLE_SMART_PICK_BHD_ONLY) + INC-T0 CONFTEST-BREAKER-RESET.
Agent: adversary, Opus 5.5, 2026-11-17 11:00-11:45 AST.
HEAD verified: 623993126836d75979d70ed6ed71c83c134e6974 (real worktree before and after; scratch worktree head_start = head_end). Base 7f672cfe.
RED file tests/test_inc_h2_smart_pick_guard.py sha256 e0bbb9958a493d4a2a02d20293a65c425df720485e5d263a670cb30dd92371c1 first and last (real worktree and the committed blob). The real worktree was never edited; git status --short empty at the end.
Scratch worktree: <SP>/INC-H2_adv_correctness (detached at 62399312), removed with git worktree remove --force; absent from git worktree list. Note: core.autocrlf=true re-checked-out the two new LF test files as CRLF; I wrote the committed blob bytes back (sha e0bbb995... / a7e25335...) before every run, so all runs used the exact bytes. app/api/home_routes.py 688e07e2..., tests/conftest.py 8af68629... (= the real worktree bytes).

VERDICT: SOUND. Blocking 0, major 0, minors 6 (documentation rulings).

## 1. Runs ([pyt] lines; every pytest via pyt.py with PYT_VIA_GATE=1, one at a time, BOX_GO present)
[pyt] tag=inc-h2-advc-unit-off start=2026-11-17 11:04:28 end=2026-11-17 11:04:32 elapsed=4s bound=600s status=OK rc=0   (105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-advc-unit-on start=2026-11-17 11:04:33 end=2026-11-17 11:04:37 elapsed=4s bound=600s status=OK rc=0   (ENABLE_SMART_PICK_BHD_ONLY=true; 105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-advc-pins start=2026-11-17 11:10:02 end=2026-11-17 11:11:30 elapsed=88s bound=1200s status=FAIL rc=1   (19 files: test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_migration_index_predicate_immutability, test_migration_043_delete_user_cascade, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_start_command, the CLAUDE.md readers by import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire, test_inc_r1_seam, test_s81_s07_meas_harness), test_home_routes, test_profile_routes: 1 failed = base node test_s81_s07_meas_harness.py::test_r35_fixtures (CRLF checkout), 1233 passed; hermeticity 1234; netguard blocked 24 sentinel attempts from 2 s04 nodes)
[pyt] tag=inc-h2-advc-c03 start=2026-11-17 11:11:31 end=2026-11-17 11:13:47 elapsed=136s bound=1200s status=OK rc=0   (GREEN chunk c03: home_routes, /health readers, MON1, INC-P2 trio; 1745 passed)
[pyt] tag=inc-h2-advc-c05 start=2026-11-17 11:13:48 end=2026-11-17 11:15:16 elapsed=88s bound=1200s status=FAIL rc=1   (c05: model_config_enforced, prompt_fence; 1106 passed, 2 errors = base test_prompt_truth tiktoken nodes; hermeticity 1110; netguard 2)
[pyt] tag=inc-h2-advc-c07 start=2026-11-17 11:15:17 end=2026-11-17 11:17:34 elapsed=137s bound=1200s status=FAIL rc=1   (c07: s04 spend breaker, s06 router + gate rows; 12 failed = base nodes, 3191 passed; hermeticity 3203; netguard 24)
[pyt] tag=inc-h2-advc-tree start=2026-11-17 11:17:35 end=2026-11-17 11:34:51 elapsed=1036s bound=1800s status=FAIL rc=1   (CI-order set = whole tests/ tree in ONE alphabetical process, GREEN's arguments: 20 failed, 31926 passed, 59 skipped, 124 deselected, 39 xfailed, 2 errors; the 22 ids are ALL in the base record; e27 PASSED this time)
[pyt] tag=inc-h2-advc-hook-nodash start=2026-11-17 11:34:52 end=2026-11-17 11:37:45 elapsed=173s bound=1800s status=OK rc=0   (the four test_precommit_hook*.py, -k "not dash": 167 passed)
[pyt] tag=inc-h2-advc-hook-dash start=2026-11-17 11:37:46 end=2026-11-17 11:40:13 elapsed=147s bound=1800s status=OK rc=0   (-k dash: 157 passed, 3 skipped)
Chunk failures (pins + c03 + c05 + c07, 14 ids) minus GREEN HEAD list = EMPTY; minus base record = EMPTY. Tree failures (22 ids) minus base record = EMPTY. Logs: <SP>/INC-H2_adv/corr/*.log, pyt_lines.txt, chunks_failed.txt, tree_failed.txt.
ruff --select E9,F63,F7,F82 on the four python files: All checks passed. py_compile: OK. Full ruff on home_routes.py: 4 pre-existing findings (none on added lines), as GREEN said.

## 2. Mutants (20 applied by hand on sha-verified byte copies in the scratch worktree; mutation lock taken and removed; each restored and sha-compared; killing set = both unit files, flag unset)
| id | mutant | result | killing rows |
|---|---|---|---|
| M01 | drop part A | KILLED 14 | a1, a2, a5, a6, r1, r1b |
| M02 | invert part A (if not ...) | KILLED 58 | a1-a6, b2-b6, r1, r1b, r1c, r2 |
| M03 | flag captured at import | KILLED 39 | b1, b4, b5, b6, r1c |
| M04 | AND instead of OR (both non-BHD) | KILLED 39 | b1, b4, b5, b6, r1c |
| M05 | strip+upper the currency | KILLED 12 | b1, b4 |
| M06 | marker skip before the status skip | KILLED 1 | a6 only (order is behaviourally equivalent) |
| M07 | default-ON reader | KILLED 10 | b0, b2, b5, r2 |
| M08 | missing currency passes | KILLED 6 | b1, b4 |
| M09 | currency read before the flag test | KILLED 22 | b2, r2 (the read recorder) |
| M10 | drop the part B call | KILLED 39 | b1, b4, b5, b6, r1c |
| M11 | part A behind ENABLE_PRICE_NOT_LOST | KILLED 11 | a1, a2, a5, a6, r1, r1b |
| M12 | winner currency only | KILLED 13 | b1, b4, b6 |
| M13 | loser currency only | KILLED 27 | b1, b4, b5, b6, r1c |
| M14 | flag test inverted | KILLED 61 | b1, b2, b4, b5, b6, r1c, r2 |
| M15 | reader parse without "1" | KILLED 7 | b0, b1 |
| M16 | part A behind the H2 flag | KILLED 11 | a1, a2, a5, a6, r1, r1b |
| T1 | conftest fixture not autouse | KILLED 2 | t0_1b, t0_2b (AssertionError only: confirms the RED-at-base claim) |
| T2 | drop the spend-breaker reset | KILLED 1 | t0_1b |
| T3 | drop the router reset | KILLED 1 | t0_2b |
| T4 | reset BEFORE each test instead of after | SURVIVED | equivalent for the T0 rows (see m1) |
19 of 20 killed; every kill is an AssertionError. Each mutant's [pyt] line is in <SP>/INC-H2_adv/corr/mutants.tsv (tags inc-h2-advc-m01-... through inc-h2-advc-t4-..., each status=FAIL rc=1 except t4 status=OK rc=0, elapsed 4-5 s, bound 600 s).

## 3. Runtime truth of the claims
- Flag-OFF identity: _smart_pick_not_bhd_pair returns False as its first statement when OFF (M09 / M14 killed by the B2 / R2 read recorder). Differential fuzz (not pytest; <SP>/INC-H2_adv/corr/fuzz.py, fuzz.out): head _select_smart_pick vs the base 7f672cfe module over 12,000 random row sets (valid / malformed products, prices, currencies incl. lower / padded / missing / list / int, winner_index 0/1/2/None, metadata with and without result_status and pair_price_sizes incl. malformed markers, non-dict full_response), with the oracle head(rows) == base(rows minus the rows head must skip): mismatch 0; flag OFF with no stamp: head == base in every case; no new exception class. skipped_rows 10,668.
- Part A inert today: the stamp is written only under the INC-P2 wire (response_builder.py ~2426-2431, `if _p2_wire:` = ENABLE_PRICE_NOT_LOST ON); the spec (2026-11-17 08:50) records the relay holding that flag OFF until part A is on main. The only consumer of _select_smart_pick is home_smart_pick (home_routes.py:866); profile_routes already carries the F4 skip; no other app/ or scripts/ reader of winner_price_bhd / runner_up_price_bhd.
- Error-handler mapping: no new raise path. _pair_price_sizes_differ is total (isinstance-guarded); the part B reads run only after the amount reads on the same dicts succeeded, so they cannot raise where base did not (fuzz: no new exception). The route and app/middleware/error_handler.py are unchanged.
- Billing R-A3: the smart-pick route is not metered (no credit reserve, usage or quota dependency; only get_current_user + the 30/minute limiter). Nothing to refund.
- Contract freeze (PLAN_S80 section 0): no key added, removed, renamed or retyped. A skip can only turn a pick into an older pick or into the existing empty envelope {smart_pick: null, empty_state: true, cta_text_key: home.smart_pick.empty_cta} that build 3 already renders.
- CLAUDE.md row: the Feature Flags pointer sentence and the unit block (after the INC-U1 block, before ## Tests: merge order, GREEN D2). Checked: the route path (router prefix /api/v1/home), the reader name and parse, "first statement of _smart_pick_not_bhd_pair", BOTH currencies exactly BHD, OFF byte-identical incl. the cached value (R2 pins key, bytes, TTL 300), INC-T0 resets AFTER every test, the INC-U1b dependency (H2R-6). All true against the bytes. Added CLAUDE.md lines: pure ASCII, CRLF kept in the working copy.
- PR body (11,129 bytes < 25,600): every number checked against the bytes and logs: 5 files +578 / -1; +25 / +18 / +7-1 / 465 / 63; 101 + 4 = 105 nodes; 234 comm files in 10 chunks (9 x 25 + 9); 22 HEAD ids, base record 23; tree 21 failed + 2 errors = 22 base + e27; e27 `0.41 >= 0.421` (GREEN tree.log:583) and INC-P2 m3 `0.42 >= 0.421` (<SP>/INC-P2_m3/e27_1.log, e27_2.log); jest 15 suites, 246 passed, 4 failed w37 drift. All match.

## 4. Engineering checks (folded in)
- Diff hygiene: 571 added lines, 0 bytes > 127, 0 deleted lines in app/ and tests/; the one CLAUDE.md "-" line is the Feature Flags line edited by insertion only (common prefix/suffix check: removed = empty). Working copies: home_routes.py / conftest.py / CLAUDE.md all CRLF (0 bare LF); the two new test files LF. No new import in app/ (conftest imports inside the fixture). No secret, personal or long-digit shape on added lines.
- Comm set re-derived with the union rule (CLAUDE.md readers by literal and CLAUDE_MD import; home_routes / smart_pick / _select_smart_pick / _pair_price_sizes_differ / _result_status_supported / _extract_winner_loser_prices refs; /health readers; llm_spend_breaker / llm_router / reset-helper users; conftest readers; rglob / walk / listdir / scandir / getsource / ast.parse / glob scanners; .github and black-clean readers; the named pins): 220 test files, ALL inside GREEN's 234 (the only names outside are non-test helpers and fixture generators). No missing file. In any case the conftest edit makes the whole tree the true set, and the tree ran in one process (GREEN and here).
- Black-clean list: neither new test file is listed (GREEN Q1); not required by any reader.

## 5. Findings
BLOCKING: none.
MAJOR: none.
MINOR (documentation rulings; none is production-visible):
- m1 T4 (reset BEFORE each test) survives: equivalent for the T0 rows. The AFTER-only reset (as H2R-14 ruled) does not clear a latch tripped during a module- or session-scoped fixture's setup or teardown, so such a latch still reaches the next file's first test (the sibling fixtures _reset_credential_health_state / the serper one reset BEFORE). No such case exists today (tree clean); before+after would be strictly stronger. Stated limit L3 covers half of it; suggest adding the teardown half.
- m2 Empty-state copy: when every row in the five-row window is skipped (cross-size, or non-BHD under ON), the card returns home.smart_pick.empty_cta ("run your first comparison") to a user who has history. Same pre-existing class as the B1 skip; the PR's PROOF mentions "or the empty state" but the stated limits do not name the copy mismatch.
- m3 The CLAUDE.md owner-steps bullet says "Rollback = unset it" without the 300 s per-user cache lag that the PR body's L1 states.
- m4 The GREEN report's Runs heading is garbled ("... with [pyt] tag=inc-h2-green-t0-base ... 246 passed)_VIA_GATE=1)": the pyt block was spliced into the sentence). The report only; the PR body is clean.
- m5 Q1 (black-clean list for the two new test files) is open for the orchestrator; INC-P2's files are not listed either.
- m6 The prove-nothing rows below.

## 6. Prove-nothing rows
- tests/test_inc_t0_conftest_breaker_reset.py::test_t0_1a_* and ::test_t0_2a_*: setters, green at base and head; they prove only that the seam trips a visible latch.
- ::test_t0_1b_* and ::test_t0_2b_*: vacuous when run alone, under -k, or in any order that does not put the setter first (GREEN D4). CI has no pytest-randomly and keeps file order, so they hold there.
- test_a6_marker_read_right_after_the_status_skip: pins call order through module globals. The order mutant M06 is behaviourally equivalent and only A6 kills it, so this is a structure pin and not a behaviour proof (accepted by H2R-12).
- test_b0_*: the second assertion re-pins the existing caption reader's parse and proves nothing about this unit.
- A3 / A4 / B2 / B3 / R2 are PIN rows. They prove no over-reach and flag-OFF identity, not the fix.
- The whole-tree, chunk and fuzz results are hermetic. None of them is the production proof: the owner's phone is (merged, NOT yet proven).

## 7. End state
Real worktree HEAD 62399312, git status --short empty, RED sha e0bbb995... unchanged. The scratch worktree is removed. No inc-h2-advc pytest is alive.

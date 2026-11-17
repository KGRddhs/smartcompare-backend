# INC-H2 STORED-ROW GUARDS + INC-T0 CONFTEST-BREAKER-RESET

Merged, NOT yet proven: the proof is the owner's phone (PROOF ON THE PHONE below). Suites and gates are necessary; they are not the production proof.

## What it does
- **Part A (UNFLAGGED, ruled like INC-P2 F4).** `app/api/home_routes.py::_select_smart_pick` (GET /api/v1/home/smart-pick) skips a stored comparison whose `metadata.pair_price_sizes.mode` is present and is not `same_size`. It uses the existing `_pair_price_sizes_differ`, called right after the B1 `_result_status_supported` skip.
  - Inert today: no stored row carries the stamp while `ENABLE_PRICE_NOT_LOST` is OFF.
  - Once rows carry it, a cross-size pair is never the Home smart pick, and it stays skipped after a rollback.
  - It is a flip precondition of `ENABLE_PRICE_NOT_LOST`.
- **Part B, `ENABLE_SMART_PICK_BHD_ONLY` (default OFF, read per call).** The reader is `home_routes.smart_pick_bhd_only_enabled`, with the same parse as `smart_pick_verdict_caption_enabled` (strip, lower, then 1 / true / yes / on).
  - The reader is the FIRST statement of the predicate `_smart_pick_not_bhd_pair`. H2R-10 allowed either form; this PR reads the flag inside the predicate, not once before the loop. The predicate runs after the amount test.
  - Flag ON: a row is skipped unless BOTH `products[winner].price.currency` and `products[loser].price.currency` equal `BHD` exactly. This is the savings reader's rule in `_extract_winner_loser_prices`, with no normalisation, so a missing, lower-case or padded currency is skipped.
  - Flag OFF: every smart-pick body and the cached `home:smart_pick:<user>` value are byte-identical, and no currency is read.
- **INC-T0 (test infrastructure, H2R-14).** The new autouse `tests/conftest.py::_reset_llm_process_latches` calls `llm_spend_breaker._reset_spend_breaker_state()` and `llm_router._reset_router_state()` AFTER every test, import-guarded like `_reset_credential_health_state`.
  - Effect: a test that trips either latch can no longer leak `llm_spend*` or `anthropic_breaker` into a later /health body in CI's one alphabetical process (the #418 CI red).
  - The INC-P2 files' own reset fixtures stay as harmless duplicates.

## Files (5; +578 / -1)
| file | +/- | role |
|---|---|---|
| app/api/home_routes.py | +25 / -0 | the part A line; the part B reader, predicate and call |
| tests/conftest.py | +18 / -0 | the INC-T0 autouse reset |
| CLAUDE.md | +7 / -1 | the Feature Flags pointer, and the unit block after the INC-U1 block (merge order) |
| tests/test_inc_h2_smart_pick_guard.py | +465 (new) | the frozen RED file, sha256 e0bbb995..., 101 nodes |
| tests/test_inc_t0_conftest_breaker_reset.py | +63 (new) | the INC-T0 rows, written RED-first by GREEN |

## Defect ids -> RED node ids
| defect | rows (tests/test_inc_h2_smart_pick_guard.py unless named) | at base |
|---|---|---|
| ORCH-H2 part A: a stored row stamped `different_sizes` / `unknown` can become the smart pick | test_a1_stamped_row_alone_is_no_pick[x2], test_a2_older_unstamped_row_is_picked[x2], test_a5_marker_skip_holds_under_every_flag[x6], test_a6_marker_read_right_after_the_status_skip, test_r1_route_skips_the_stamped_row[x2], test_r1b_route_stamped_only_is_empty_state | RED |
| ORCH-H2 part B: a non-BHD stored row is shown under `*_price_bhd` | test_b0_reader_exists_and_parses_like_the_caption_reader[x13], test_b1_flag_on_skips_a_non_bhd_pair[x30], test_b4_flag_on_older_bhd_row_is_picked[x6], test_b5_flag_read_per_call, test_b6_flag_on_reads_both_currencies, test_r1c_route_flag_on_skips_the_usd_row | RED |
| flag-OFF identity, same_size and malformed markers | test_a3[x2]; test_a4[x6]; test_b2_flag_off_picked_as_today[x18] (frozen literal goldens, no currency read); test_b3[x5]; test_r2_route_flag_off_byte_identical[x4] (the body, plus the cached bytes, key and TTL 300) | PIN |
| INC-T0: a latch leaks across tests (the #418 CI red) | tests/test_inc_t0_conftest_breaker_reset.py: test_t0_1b_spend_breaker_latch_does_not_leak_into_the_next_test and test_t0_2b_router_latch_does_not_leak_into_the_next_test, each paired with its setter row 1a / 2a | RED (2 AssertionErrors before the conftest edit, inc-h2-green-t0-base) |

RED gate on the H2 file at 8bb97fe0: 66 RED rows (all AssertionError) and 35 PIN rows. The prototype mutation table killed 13 of 14 mutants; M03b was ruled equivalent (H2R-10). The RED report holds that table and the per-row evidence; the orchestrator files it.

## Deliberate pin changes (spec 4.1)
None: no existing test file changed. The only shared-test edit is the conftest addition, and the whole-tree run in one process covers it.

## Gates (HEAD 62399312, branch base = main 7f672cfe)
- Lint and bytes:
  - py_compile is clean.
  - ruff `E9,F63,F7,F82` is clean on the four python files, and the pre-commit hook ran it again.
  - The added lines are pure ASCII. home_routes.py, conftest.py and CLAUDE.md keep their CRLF.
- Unit files, flag OFF and ON: 105 / 105 each (the H2 file's 101 plus T0's 4).
- Comm set at HEAD: 234 files in 10 chunks of up to 25. It is the RED union list (195) re-derived at HEAD, plus the /health readers, the latch users, the conftest readers, the CLAUDE.md readers by import graph and the two unit files. The precommit hook files are excluded.
  - HEAD failures: 22 nodes, 2 of them errors.
  - Base record: 23 nodes (the RED report, 8bb97fe0, rb2 XMLs).
  - **branch-only-NEW = EMPTY.**
  - Base-only: test_retro_w0_4.py::test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag[scs._fetch_page_price], a timing node that passed at HEAD.
- Whole tests/ tree in ONE alphabetical process (GATE 4 / INC-T0). test_integration.py and the four precommit hook files are ignored, and the 8 baseline nodes of tests/.pre_impl_failures.txt are deselected. Result: 23 failed or errored ids.
  - 22 of them are the recorded base nodes.
  - The 23rd is tests/test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait (`0.41 >= 0.421`), a rounding race between `elapsed_seconds` (2 decimals) and the bind wait in ms.
  - It is a base flake. It failed 2 of 2 on the identical base tree (the 629b21ca tree equals the 7f672cfe tree, 95b2556c) in INC-P2's m3 round (inc-p2-m3-e27-1 and -2, `0.42 >= 0.421`).
  - It passed in this branch's comm chunk, and again when the file was re-run alone at HEAD.
- Client fences (the fourteen; 15 suites, run once by path): 246 passed and 4 failed. The 4 failures are the accepted config/nativeBundle.w37 drift nodes, identical to the INC-P2 rb2 record.

```
[pyt] tag=inc-h2-green-t0-base start=2026-11-17 10:25:35 end=2026-11-17 10:25:40 elapsed=5s bound=600s status=FAIL rc=1  (before the conftest edit: 2 failed (T0-1b, T0-2b, AssertionError only), 2 passed; hermeticity 4; netguard 0)
[pyt] tag=inc-h2-green-unit-off start=2026-11-17 10:25:58 end=2026-11-17 10:26:02 elapsed=4s bound=600s status=OK rc=0  (105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-green-unit-on start=2026-11-17 10:26:03 end=2026-11-17 10:26:07 elapsed=4s bound=600s status=OK rc=0  (ENABLE_SMART_PICK_BHD_ONLY=true; 105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-green-pins start=2026-11-17 10:26:14 end=2026-11-17 10:26:58 elapsed=44s bound=600s status=FAIL rc=1  (15 files; 1 failed = the base node test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, 1821 passed; netguard blocked 13 sentinel attempts)
[pyt] tag=inc-h2-green-c01 start=2026-11-17 10:27:41 end=2026-11-17 10:28:15 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c02 start=2026-11-17 10:28:16 end=2026-11-17 10:29:00 elapsed=44s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c03 start=2026-11-17 10:29:01 end=2026-11-17 10:31:19 elapsed=138s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c04 start=2026-11-17 10:31:20 end=2026-11-17 10:31:51 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c05 start=2026-11-17 10:31:51 end=2026-11-17 10:33:18 elapsed=87s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c06 start=2026-11-17 10:33:19 end=2026-11-17 10:35:08 elapsed=109s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c07 start=2026-11-17 10:35:09 end=2026-11-17 10:37:27 elapsed=137s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c08 start=2026-11-17 10:37:27 end=2026-11-17 10:38:16 elapsed=49s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c09 start=2026-11-17 10:38:17 end=2026-11-17 10:39:18 elapsed=61s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c10 start=2026-11-17 10:39:19 end=2026-11-17 10:39:31 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-tree start=2026-11-17 10:39:32 end=2026-11-17 10:56:51 elapsed=1039s bound=1800s status=FAIL rc=1  (whole tests/ tree, ONE alphabetical process: 21 failed, 31928 passed, 56 skipped, 124 deselected, 39 xfailed, 2 errors in 1030.77s)
[pyt] tag=inc-h2-green-e27-rerun start=2026-11-17 10:57:43 end=2026-11-17 10:58:17 elapsed=34s bound=600s status=OK rc=0  (tests/test_inc_i2a_picture_not_cut.py alone at HEAD: 67 passed)
[jest] tag=inc-h2-green-fences start=2026-11-17 10:56:52 end=2026-11-17 10:56:58 rc=1  (jest 29.7.0; 15 suites / 250 tests: 4 failed = the accepted config/nativeBundle.w37 drift nodes d5 / k2 / k4 / k5, 246 passed)
```

## Adversary (correctness, one, SMALL unit per the leaner chain)
- Verdict at head 62399312: **SOUND**. 0 blocking, 0 major, 6 minor.
  - m1 and m2 are stated above as L3 and L6.
  - m3: the CLAUDE.md rollback words omit the 300 s cache lag. That is stated in L1 and in Owner steps here.
  - m4: a report-only typo.
  - m5: L7.
  - m6: the prove-nothing rows are listed in the adversary report.
- Mutants: 19 of 20 killed (M01-M16 for parts A and B, T1-T3 for the conftest). T4 (reset before instead of after) survives as equivalent for the T0 rows; see L3.
- Differential fuzz, head vs base: 12,000 row sets with 0 mismatches against the skip oracle. With the flag OFF and no stamp, the result is identical in every case.
- Its own re-runs:
  - unit OFF / ON: 105 / 105;
  - pins: 1 base node;
  - comm chunks c03 / c05 / c07: base nodes only;
  - the whole tree in one process: 22 ids, all in the base record; branch-only-NEW is EMPTY and e27 passed;
  - the precommit hook files: 167 and 157 passed, 3 skipped.

## Stated limits
- L1: parts A and B read only the stored row. Rows already cached under `home:smart_pick:<user>` (TTL 300 s) are served until they expire.
- L2: part B keeps the savings reader's exact rule, so under ON a legacy row with a lower-case or missing currency stops being the pick even when its amount was BHD. This is by design per the spec, and it is why part B is flagged.
- L3: INC-T0 resets AFTER each test (H2R-14). This has two consequences.
  - A test that relies on a latch tripped earlier in its module would lose it.
  - A latch tripped in a module- or session-scoped fixture's setup or teardown is not cleared before the next file's first test. The sibling fixtures reset before each test instead (adversary m1; mutant T4, reset-before, survives as equivalent for the T0 rows).
  - No such case exists today: the whole-tree run is clean apart from base nodes.
- L4: the e27 timing node in test_inc_i2a_picture_not_cut.py is a base flake of the one-process run, and this PR does not address it.
- L5: every measurement here is hermetic. None of it is the production proof.
- L6: when every row in the five-row window is skipped (cross-size, or non-BHD under ON), the card shows `home.smart_pick.empty_cta` ("run your first comparison") to a user who has history. This is the same class as the existing B1 skip, and the copy is not changed here (adversary m2).
- L7: `tests/test_inc_t0_conftest_breaker_reset.py` and the H2 file are not added to `.github/black-clean-paths.txt`. The INC-P2 files are not listed either, and no reader requires it.

## PROOF ON THE PHONE
- Part A, once `ENABLE_PRICE_NOT_LOST` has stamped rows:
  - On the owner's phone, compare a typed cross-size pair (for example a 50 ml bottle of one fragrance against a 100 ml bottle of another), then open Home.
  - Expected: the Smart Pick card does not show that pair. It shows an older same-size BHD pair, or the empty state.
  - Backing check: the stored comparisons row carries `metadata.pair_price_sizes.mode` = `different_sizes`.
- Part B, in the `ENABLE_SMART_PICK_BHD_ONLY` window:
  - The canary: for a BHD history, the Home card is unchanged.
  - A row whose saved price currency is not BHD is never the card.

## Owner steps (names only; a dated ledger line per step)
- Nothing to do at merge. Part A goes live on merge and stays inert until P2 stamps rows.
- The relay flips `ENABLE_SMART_PICK_BHD_ONLY` on web in its own window. Rollback = unset it (it is read per call; cached cards drain within the 300 s TTL, L1).
- The link lane's INC-U1b needs `ENABLE_SMART_PICK_BHD_ONLY` ON (H2R-6).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

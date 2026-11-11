# G-INC-1 RED REPORT (INC-X9 + INC-X10 + INC-X8 + INC-X2a), RED agent Opus 5.5, 2026-11-11

Base a74caba7e3ff66b12e94178c912197c845ccbd14 (worktree HEAD verified before and after). Rulings applied: R-G1-5..14 (batch) over the spec. Notes folder: <SP>/G-INC-1/red/.

## Files written (real worktree, untracked; pure ASCII, LF, 0 bytes > 127, 0 CR)
- tests/test_inc_x9_cohort_line_retire.py  17303 B sha256 b2ef4d349021d3dca49016f34d576e707eddd92f74a77d04b872b330e1f69c5a
- tests/test_inc_x10_listing_match_guard.py 10824 B sha256 f1c7f3303ada54ef4cb215fb4017e4e5d59812b2e808743fd867acc2ed594d9b
- tests/test_inc_x8_phase2_cached_rating.py 22420 B sha256 8a2cc6d6dc9fcfbbdff10935240684abb100e84116ab9dab188917ce0673a861
- tests/test_inc_x2a_image_tier_timing.py  13307 B sha256 febb83de596fcb366ad59ff6a3957489bd3562a4ab6995275d4f0612884154eb
ruff E9,F63,F7,F82,F401,F841 on the four: All checks passed.

## (2) Deferred base-pass sets (section 1.10 of each unit), alone, at base
[pyt] tag=inc-x9-base start=2026-11-11 19:55:43 end=2026-11-11 19:55:48 elapsed=5s bound=600s status=OK rc=0 (46 passed, 1 deselected)
[pyt] tag=inc-x10-base start=2026-11-11 19:55:58 end=2026-11-11 19:56:11 elapsed=13s bound=600s status=OK rc=0 (230 passed)
[pyt] tag=inc-x8-base start=2026-11-11 19:56:12 end=2026-11-11 19:56:31 elapsed=19s bound=600s status=OK rc=0 (193 passed)
[pyt] tag=inc-x2a-base start=2026-11-11 19:56:32 end=2026-11-11 19:56:44 elapsed=12s bound=600s status=OK rc=0 (180 passed; [netguard] blocked 3 attempt(s) from 1 node: tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] getaddrinfo api.openai.com:443, pre-existing, the node is green)
Walkers of tests/ after the four files were written (R-G1-13):
[pyt] tag=inc-g1-walkers start=2026-11-11 20:18:29 end=2026-11-11 20:19:35 elapsed=66s bound=600s status=OK rc=0 (test_hermeticity_pins.py + test_ci_gates.py + test_scoring_rubric_truth.py: 238 passed, 1 xfailed; the netguard lines are the hermeticity pins' own designed probes)

## (4) The four RED files at base (final bytes)
[pyt] tag=inc-g1-red-base3 start=2026-11-11 20:14:26 end=2026-11-11 20:14:35 elapsed=9s bound=600s status=FAIL rc=1 -> 40 failed, 44 passed; [hermeticity] sentinel checked 84 test(s); [netguard] blocked 0 attempt(s)
Every failure is an AssertionError (40 of 40 'E AssertionError' lines; no import, attribute or setup error). Failed node ids: <SP>/G-INC-1/red/red_base_failed.txt
Per file: X9 6 RED fail / 5 PIN pass; X10 21 RED fail (R10-1..R10-10 + P10-3 x11 params) / 22 PIN pass; X8 6 RED fail (R8-1 x2 incl. R8-2, R8-3, R8-4, R8-5, P8-5) / 10 PIN pass (P8-0, P8-1 x5, P8-2, P8-3, P8-4, P8-6); X2a 7 RED fail / 7 PIN pass.
Earlier per-file runs: inc-x2a-red (7 failed, 7 passed), inc-x10-red (21 failed, 22 passed), inc-x9-red (6 failed, 5 passed), inc-x8-red3 (6 failed, 10 passed), AssertionError only.
X10 truth table base values CONFIRMED by running: every row T1..T18 is _selection_match True at base (P10-2 asserts it under 5 OFF spellings); should_cache_price(T1) True at base (R10-10 kept); backstop (True, None) and cache read True at base.

## (5) Prototype (scratch worktree <SP>/G-INC-1/red/g1_scratch, detached at base; script <SP>/G-INC-1/red/proto.py)
Change list as ruled: X9 per R-G1-6 (_build_cohort_summary = docstring + return None; _COHORT_GOV_SKIP removed: git grep at base shows no other reader; the was_cohort_block_active import is still used by the two metadata sites); X8 helpers + block exactly as X8.2; X10 table / reader / predicate + H1 + H2 exactly as X10.2; X2a imports + _log_img_tier + bookkeeping + CancelledError arm. py_compile + ruff E9/F63/F7/F82 clean.
ON (all four files): [pyt] tag=inc-g1-proto-on4 start=2026-11-11 20:14:37 end=2026-11-11 20:14:48 elapsed=10s bound=600s status=OK rc=0 -> 84 passed
OFF (the flag-OFF identity rows of the two dark units: P10-2 x5, P10-4 x2, P8-0, P8-1 x5, P8-3, P8-6): [pyt] tag=inc-g1-proto-off2 start=2026-11-11 20:14:49 end=2026-11-11 20:14:53 elapsed=4s bound=600s status=OK rc=0 -> 15 passed
Existing pins on the prototype (informational): [pyt] tag=inc-g1-proto-pins start=2026-11-11 20:07:55 end=2026-11-11 20:08:35 elapsed=40s bound=600s status=FAIL rc=1 -> 373 passed, 3 failed = exactly the spec's E-rows E9-1..E9-3 (tests/test_cohort_summary_orchestrator.py::test_returns_peer_count_and_governorate_when_resolved, ::test_peer_count_sourced_from_cohort_match_n, ::test_broadened_governorate_quality_still_emits). The wiring guard test_all_three_build_sites_pass_cohort_summary, test_response_builder_cohort_summary.py, the golden corpus, pr9 fixes, s75 fanout starve, s81 s18 kb-first-serve, the image suites, model_config_enforced and prompt_fence are all green on the prototype.

## (6) Mutation table (25 mutants on byte copies of the prototype; each restored + sha256-verified; lock <scratch>/.qa-mutation.lock created and removed; results <SP>/G-INC-1/red/mutation_results.json, logs mut_<id>.log; every run bound 600, status=FAIL rc=1, 4-10 s)
| M | mutation | result | killing rows |
|---|---|---|---|
| M9-1 | restore a live body (a dict when was_cohort_block_active) | KILLED (6 nodes) | test_r9_1_resolved_cohort_yields_none , test_r9_2_none_for_padded_flag_and_broadened , test_r9_3_partial_response_has_no_block , test_r9_4_entry_response_has_no_block[camera] , test_r9_4_entry_response_has_no_block[stream] , test_r9_4_entry_response_has_no_block[text] |
| M9-2 | return None -> return {} | KILLED (2 nodes) | test_r9_1_resolved_cohort_yields_none , test_r9_2_none_for_padded_flag_and_broadened |
| M9-4 | streaming call site -> literal {peer_count 1, Capital} | KILLED (2 nodes) | test_p9_5_call_sites_unchanged , test_r9_4_entry_response_has_no_block[stream] |
| M10-1 | delete the predicate's flag check | KILLED (5 nodes) | test_p10_2_flag_off_identity_full_config[false] , test_p10_2_flag_off_identity_full_config[garbage] , test_p10_2_flag_off_identity_full_config[padFALSE] , test_p10_2_flag_off_identity_full_config[unset] , test_p10_2_flag_off_identity_full_config[zero] |
| M10-2 | != default_side -> == | KILLED (13 nodes) | test_p10_1_keep_rows_accept_flag_on[T14] , test_p10_1_keep_rows_accept_flag_on[T7] , test_p10_1_keep_rows_accept_flag_on[T9] , test_r10_10_should_cache_refuses_the_womens_listing , test_r10_1_eros_for_women_rejected , test_r10_2_eros_pour_femme_rejected , test_r10_3_aventus_for_her_pronoun_rejected , test_r10_4_light_blue_pour_homme_rejected , test_r10_5_dylan_blue_pour_femme_rejected , test_r10_6_select_best_skips_the_womens_listing , test_r10_7_only_the_womens_listing_gives_no_price , test_r10_8_backstop_rejects_on_read_and_display , test_r10_9_poisoned_cache_entry_rejected |
| M10-3 | delete the query-gender guard | KILLED (3 nodes) | test_p10_1_keep_rows_accept_flag_on[T15] , test_p10_1_keep_rows_accept_flag_on[T8] , test_p10_5_gendered_query_never_consults_the_table |
| M10-4 | women words without the pronouns | KILLED (1 nodes) | test_r10_3_aventus_for_her_pronoun_rejected |
| M10-5 | delete hook H1 | KILLED (8 nodes) | test_r10_10_should_cache_refuses_the_womens_listing , test_r10_1_eros_for_women_rejected , test_r10_2_eros_pour_femme_rejected , test_r10_3_aventus_for_her_pronoun_rejected , test_r10_4_light_blue_pour_homme_rejected , test_r10_5_dylan_blue_pour_femme_rejected , test_r10_6_select_best_skips_the_womens_listing , test_r10_7_only_the_womens_listing_gives_no_price |
| M10-6 | delete hook H2 | KILLED (2 nodes) | test_r10_8_backstop_rejects_on_read_and_display , test_r10_9_poisoned_cache_entry_rejected |
| M10-7 | H1 without cat == fragrances | KILLED (3 nodes) | test_p10_1_keep_rows_accept_flag_on[T16] , test_p10_4_rule_is_fragrance_scoped[fashion] , test_p10_4_rule_is_fragrance_scoped[none] |
| M10-8 | c_men == c_women -> not (c_men or c_women) | KILLED (1 nodes) | test_p10_1_keep_rows_accept_flag_on[T18] |
| M10-9 | reader == 'true' | KILLED (3 nodes) | test_p10_3_flag_reader_hygiene[on] , test_p10_3_flag_reader_hygiene[one] , test_p10_3_flag_reader_hygiene[yes] |
| M8-1 | drop _phase2_cached_rating_enabled() | KILLED (5 nodes) | test_p8_1_flag_off_identity_full_config[false] , test_p8_1_flag_off_identity_full_config[garbage] , test_p8_1_flag_off_identity_full_config[padFALSE] , test_p8_1_flag_off_identity_full_config[unset] , test_p8_1_flag_off_identity_full_config[zero] |
| M8-2 | drop and _phase2_skip | KILLED (2 nodes) | test_p8_2_not_skipped_runs_phase2_as_today , test_p8_3_guard_off_never_reads |
| M8-3 | accept any confidence | KILLED (1 nodes) | test_r8_3_tier3_rows_give_no_rating_and_a_miss_line |
| M8-4 | await self._get_verified_rating instead | KILLED (5 nodes) | test_p8_5_no_new_keys , test_r8_1_skipped_product_gets_the_in_memory_rating[padTRUE] , test_r8_1_skipped_product_gets_the_in_memory_rating[true] , test_r8_4_extractor_error_is_contained , test_r8_5_factcheck_view_is_used |
| M8-5 | no try/except | KILLED (1 nodes) | test_r8_4_extractor_error_is_contained |
| M8-6 | ignore _fc_view | KILLED (1 nodes) | test_r8_5_factcheck_view_is_used |
| M8-7 | drop and not _kb_full | KILLED (1 nodes) | test_p8_6_kb_full_hit_keeps_the_card_rating |
| M2-1 | delete the bare raise | KILLED (2 nodes) | test_p2_6_cancel_propagates , test_r2_7_handler_has_no_await_and_reraises |
| M2-2 | name[:60] in a tier line | KILLED (2 nodes) | test_r2_1_search_payload_hit_lines , test_r2_6_lines_carry_no_name_or_url |
| M2-3 | Tier-1 budget + search before Tier 1.5b | KILLED (8 nodes) | test_p2_1_kg_hit_calls_nothing_paid , test_p2_2_serper_hit_call_order , test_p2_3_all_miss_call_order , test_p2_4_budget_denied , test_p2_5_search_raises_still_tries_gpt , test_r2_4_error_and_denied_outcomes , test_r2_5_cancel_line_names_the_tier_in_flight , test_r2_6_lines_carry_no_name_or_url |
| M2-4 | cancel line reads a constant tier | KILLED (2 nodes) | test_r2_5_cancel_line_names_the_tier_in_flight , test_r2_6_lines_carry_no_name_or_url |
| M2-5 | await asyncio.sleep(0) in the handler | KILLED (1 nodes) | test_r2_7_handler_has_no_await_and_reraises |
| M2-6 | serper_budget always hit | KILLED (1 nodes) | test_r2_4_error_and_denied_outcomes |

Result: 25 of 25 KILLED, all on an AssertionError (M8-5's RuntimeError is re-raised by R8-4 as an AssertionError). The spec's M9-3 is NOT APPLICABLE under R-G1-6 (no predicate remains to reorder). M8-7 is KILLED by the new P8-6 KB full-hit row (R-G1-10). No survivor, no equivalent.

## (7) Comm set (R-G1-13: built, NOT run)
- base list <SP>/G-INC-1/red/comm/comm_list_base.txt: 732 files, sha256 04a6d9c49c625d263cadd0aac9d190202db7e73a2416555eda5cfbc02a00ffe2 (= the spec's union-rule set <SP>/G-INC-1/spec/comm_set.txt, re-used unchanged; the four test_precommit_hook*.py excluded, asserted)
- head list <SP>/G-INC-1/red/comm/comm_list_head.txt: 736 files (+ the four RED files), sha256 fe0bddde40b77fb4f264c14cc62c885f2aa430f806810d8ad2e1442b4946e0dc
- per-file reasons <SP>/G-INC-1/red/comm/comm_reasons.tsv (first reason: names scs/ps/img 344, closure member 209, app.main/TestClient 111, spec-union text 53; plus named-pin / CLAUDE.md-reader / SmartCompareApp-scan / source-scan tags)
- NETWORK_FLAKY_EXCLUDE is a node-level deselect applied at run time (no file removed). 30 chunks of <= 25 at base; NOT RUN per R-G1-13 (the MON1 RED agent records the whole-tree base at a74caba7).

## (8) Restore check
git status --short = the four new test files only; git diff --quiet = no tracked diff; HEAD a74caba7 unchanged. The scratch worktree is removed (git worktree list has no g1_scratch). No python -m pytest process alive after the last run.

## Deviations from the spec (rulings applied, or spec facts corrected by measurement)
1. X9 R-G1-6: added R9-4 (3 params: text / stream complete / camera through the REAL entries over the copied s18 FY25 driver; user_id + a stubbed get_user_demographics; metadata.cohort_injected True asserted as a precondition). P9-5 adapted: was_cohort_block_active( is counted OUTSIDE the helper (== 2, the two metadata sites), since the ruled helper no longer calls it (the spec's count of 3 would fail at GREEN).
2. X9 M9-3 not applicable under R-G1-6; M9-1 re-cut as 'restore a live body'.
3. X9 P9-2 / P9-3: volatile keys are dropped by NAME at any depth (timestamp, generated_at, created_at, elapsed_ms, elapsed_seconds, request_id, cached_at, fetched_at, retrieved_at) after a first version that diffed two builds was measured FLAKY (one base run failed on a metadata clock value differing between builds); the row also asserts two None-builds equal after the drop.
4. X8 R-G1-10: P8-6 added (KB full hit via copied S81-18 helpers: two full cards, ENABLE_KB_FIRST_SERVE ON, the guard ON with knob 100 so both products skip, X8 ON): asserts 2 skip lines, no live leg / rating call, no cached-rating line, the card rating 4.6 / 31. It kills M8-7.
5. X8 fixture: PRODUCT is brand 'Ajmal', name 'Ajmal Aristocrat' so the W4-7 key ('Ajmal Ajmal Aristocrat') differs from full_name ('Ajmal Aristocrat'); with the spec's s75 PRODUCT the two keys are EQUAL and M8-6 would be unkillable (P8-0 asserts the difference). TIER3_ROWS is ONE eBay row: three identical eBay rows form a Google consensus (high, verified), not a tier-3 fixture.
6. X8 R8-2 is a parameter of R8-1 (ids true / padTRUE). R8-4 converts an escaped RuntimeError into an AssertionError so M8-5 dies on an assertion.
7. X10 P10-3 is RED (as the spec says); P10-2 / P10-5 install the recording table with raising=False (absent at base).
8. X2a outcomes as written for GREEN: piggyback 'skipped' when page_scrape_image is falsy; search_payload 'skipped' when the payload is None and 'miss' when a dict has no image; serper_images 'skipped' when the budget is denied; llm_pick 'skipped' with no organic results; error:<Type> only in the two existing except arms.

## Open questions for the gate
- Q1: P9-5 count re-defined (outside the helper == 2): accept?
- Q2: GREEN must keep the exact X8 log prefix '[L2.6] phase 2 cached rating outcome=' and the X2a grammar (the rows match them by regex).

## NOT MEASURED
- The comm-set base chunks (by ruling R-G1-13). Client jest fences (not in this round). The X9 E-rows were measured failing on the prototype only (GREEN edits them).

# B1 RESULT-STATUS + TELEMETRY: `ENABLE_RESULT_STATUS_METADATA` (S80, measure before enforce)

Branch `feature/s80-b1-result-status` from base `81df2b641454e0301cca51a3ba01bf8ef3d7e649`; GREEN commit `2bbd58a9eae6aa172339ee7cc717e875ff2bbc73` (rebase target `origin/main 4a38ce93`, the orchestrator's step). Spec `.qa-s80/B1_UNIT_SPEC.md` (sha256 `05d48e2c...`), review `B1_SPEC_REVIEW.md`, rulings `RULINGS_BATCH1.md` (Common G-1..G-4, B1-R1..B1-R12), RED gate `specs/GATE_B1.md` (GA-1..GA-9), RULINGS_R0 R0-1/R0-2/R0-4/R0-5/R0-6/R0-7, PLAN_S80 sections 0-1. Every pytest run below went through the bounded runner; one process at a time.

## What the flag does

`ENABLE_RESULT_STATUS_METADATA` (default OFF; `app/services/result_gate.py::result_status_metadata_enabled`, the house idiom, read PER CALL, the FIRST statement of every gated predicate). **ON:** every text and camera body built by `build_comparison_response` carries `metadata.result_status` {supported_result, partial_no_winner, needs_identification, unsupported_category, failed}, `identity_confidence` {high, medium, low, unresolved}, `data_coverage` (0-4, the AUDITABLE reading of R0-5: both prices showable and not estimated, both ratings real, a real two-sided spec row that is not a tier-3 synthesis, a non-sentinel non-low dimension with margin >= 3) beside `data_coverage_literal` (R0's literal tally, so production sizes the 4/27-vs-1/27 gap before B2 flips), `product_categories` (the per-product pair captured BEFORE the pair-category write-back in both orchestrator paths), `section_status` {specs, reviews, pros_cons, price: available | partial | unavailable}, `overview.winner.supported` (bool) and `metadata.winner_index = None` on every non-supported body (its first writer, MYEZ-027). `home_routes` savings and smart pick skip stamped non-supported rows by `result_status` through the unflagged reader `_result_status_supported` (never via `winner_index`; an unstamped row counts as today). One PII-free Sentry info message `comparison_result_status` per DELIVERY exit (text POST / GET, a stream `complete` the client received, camera success, URL success): enum / small-int tags, `vision_ms` / `compare_ms` as bucket tags (the bucket's lower edge in ms, 1000 / 5000-ms steps, GA-2) with the raw ints as extras; recomputed from the body; a non-success body never emits (B1-R6); synchronous, one try/except, no `fire_and_forget` label. Camera `vision_ms` / `vision_moderation_ms` / `compare_ms` go only into an EXISTING `metadata.stage_timings_ms` dict (R0-6). `sentry_service.compare_traces_sampler` samples the four compare paths at 1.0 under the flag; otherwise the parent decision, else the LIVE client `traces_sample_rate` (B1-R1), installed beside the kept `traces_sample_rate=0.1`. Nothing abstains (B2); the crown (`winner_index`, `overview.winner.product_index`, `scoring_v2.overall_score`, `comparison.winner_index`) never moves; a failure inside the stamp leaves the body as with the flag OFF (ONE WARNING `[RESULT_STATUS] assess failed: <TypeName>`). **OFF:** byte-identical on every body and stored row, no message, no timing key, the SDK's own sampling rule; the only OFF-state work is the per-call flag read, three `perf_counter` reads on the camera route and the two-string category capture on the partial build ctx (never serialised OFF).

**Unflagged (R-A1(a), R0-2):** `VALID_EVENT_TYPES` += `scan_start, scan_identity_resolved, scan_comparison_ready, scan_failed, scan_cancelled, image_load_failed` (C7); `VALID_MATTERED_MOST` += `wrong_product, missing_info, unclear_reasons, slow, wrong_winner, unsure` (C6); `FeedbackRequest` gains optional `winner_correct` / `price_correct` / `specs_correct` (`Literal` correct | wrong | unsure, default None, off-enum = 422) written to the live 027 columns only when sent; both lists append-only; `mattered_most: []` still accepted.

## Defect ids -> RED node ids -> flag -> activation precondition

| MYEZ id | defect | RED / PIN nodes (`tests/test_s80_b1.py` unless noted) | flag | precondition |
|---|---|---|---|---|
| MYEZ-002 | a winner on two Unknown Products (V09) | `test_b1_r2_placeholder_identity[*]`, `test_b1_r10_builder_unknown_product_pair_needs_identification[*]`, `test_b1_r10b_v09_shape_reasons_exact`, `test_b1_r17b_telemetry_non_supported_body_tags` | `ENABLE_RESULT_STATUS_METADATA` (measure; B2 refuses) | none (first flip after approval) |
| MYEZ-003 | a winner with an empty spec table (V10, no evidence) | `test_b1_r5_price_facts[*]`, `test_b1_r6_real_spec_rows_excludes_na_and_tier3`, `test_b1_r7_dim_facts[*]`, `test_b1_r8_builder_stamps_manama_partial_no_winner[12-14]`, `test_b1_r9_builder_stamps_lane1_supported[*]`, `test_b1_r9b_builder_lane1_stamped_prices_reach_coverage_4[*]`, `test_b1_r13_builder_june_rows_brand_empty_supported[15-19]`, `test_b1_r14_builder_partial_rows`, `test_b1_r15_orchestrator_rest_and_stream_stamp` | same | none |
| MYEZ-004 | two different shirts as one identity (V07) | `test_b1_r3_same_identity[*]`, `test_b1_r11_builder_same_identity_pair` | same (B2 refuses; B3 adds the features axis) | none |
| MYEZ-011 | the badge always shows confidence (visual confidence vs weak data) | `test_b1_r8_*` (`overview.winner.supported` False, `metadata.winner_index` None), `test_b1_r12_builder_category_conflict`, `test_b1_r16_orchestrator_vision_pair_product_categories`, `test_b1_r4_identity_coherence[*]`, `test_b1_p6_builder_flag_on_does_not_move_the_crown` | same (C1 renders the three states) | none |
| MYEZ-012 | a credit consumed on an unusable compare | measured, not fixed here: the delivered-partial status series (`test_b1_r14_builder_partial_rows`, `test_b1_r15_*` gather partial, the `partial_stage` tag in `test_b1_r17_*`) sizes the owner's billing decision; B2 makes the abstain a non-delivery (R-A3) | same (measure) | none |
| MYEZ-015 | ~40 s scan with a silent loader | `test_b1_r20_camera_timings_written_only_into_existing_dict[*]`, `test_b1_r20b_stamp_camera_stage_timings_skips_none`, `test_b1_r18_telemetry_camera_and_url`, `test_b1_r21_sampler_flag_on_compare_paths[*]`, `test_b1_r21b_init_sentry_installs_the_sampler`; `tests/test_s80_b1_feedback.py::test_b1_f2_new_event_types_accepted[*]` (the C7 event names) | same + the unflagged allowlist | none; C7 fires the names after the OTA |
| MYEZ-022 | empty sections look loaded | `test_b1_r8_*` / `test_b1_r9_*` (`section_status`), `test_b1_c9e_section_status_partial_when_one_side_empty` | same (C1 renders honest rows) | none |
| MYEZ-023 | feedback cannot say "not useful" | `tests/test_s80_b1_feedback.py::test_b1_f1_new_mattered_most_values_accepted[*]`, `::test_b1_f3_correctness_fields_accepted_and_written[*]`, `::test_b1_f4_off_enum_value_422s[*]`, PINs f5 / f6 / f7 | none (unflagged allowlist, R-A1(a)) | the widening deploys BEFORE the C6 OTA fires the chips |
| MYEZ-027 | unreliable results saved and shared as decisions | `test_b1_r22_home_savings_skips_stamped_non_supported_rows`, `test_b1_r23_home_smart_pick_skips_stamped_non_supported_rows`, `test_b1_p7_history_list_null_neutral_for_stamped_row`, `test_b1_p8_home_savings_unstamped_rows_count_as_today` | same (the stamp); the readers are unflagged and keyed on the stamp | none |

Telemetry contract: `test_b1_r17_telemetry_text_post_get_stream`, `test_b1_r18_*`, `test_b1_r18b_telemetry_camera_unsuccessful_emits_nothing[*]`, `test_b1_r19_telemetry_stream_client_gone_emits_nothing`, `test_b1_p12_url_body_never_stamped`. Flag-OFF identity: `test_b1_p1_*[5 values]`, `test_b1_p2_*[2]`, `test_b1_p3_*[2]`, `test_b1_p4_*[2]`, `test_b1_p5_*[42]`, `test_b1_p5a`, `test_b1_p5b_*[3]`, `test_b1_p13_stamp_failure_degrades_to_flag_off`. Purity and source pins: `test_b1_p10_*`, `test_b1_p11_result_gate_is_pure`, `test_b1_c9c_assess_result_not_success_is_failed`.

## Deliberate pin changes (spec 4.1)

| # | test | before | after | reason |
|---|---|---|---|---|
| E1 | `tests/test_s75_fanout_identity.py` `UNIT_ENV` tuple | nine FANOUT / timing names popped per scenario | + `"ENABLE_RESULT_STATUS_METADATA"`; the nine digests UNCHANGED (no re-record; the file passes 3/3 and under the flag exported, smoke run 2) | a developer `.env` carrying the new flag would otherwise move the flag-OFF digests |

No other existing assertion changed. `tests/.pre_impl_failures.txt`, the fixtures, `requirements*`, `processors.json`, migrations and client files are untouched.

## Gates (every line verbatim from the bounded runner; base = 81df2b64, HEAD = 2bbd58a9)

Unit files (RED frozen: `tests/test_s80_b1.py` sha256 `88130f32...35dfb`, `tests/test_s80_b1_feedback.py` `0bd11178...59ab3`, both re-hashed equal at the start and the end):
```
187 passed (flag ON exported)   [pyt] tag=b1green-unit-on start=2026-10-20 03:41:39 end=2026-10-20 03:41:47 elapsed=8s bound=600s status=OK rc=0
187 passed (flag unset)         [pyt] tag=b1green-unit-off start=2026-10-20 03:41:48 end=2026-10-20 03:41:56 elapsed=8s bound=600s status=OK rc=0
27 passed (feedback)            [pyt] tag=b1green-unit-fb start=2026-10-20 03:41:57 end=2026-10-20 03:42:00 elapsed=3s bound=600s status=OK rc=0
after the one post-run touch (ruff C420 on the new module): 187 / 187 / 27 passed
  [pyt] tag=b1green-unit-on2 start=2026-10-20 03:47:27 end=2026-10-20 03:47:36 elapsed=9s bound=600s status=OK rc=0
  [pyt] tag=b1green-unit-off2 start=2026-10-20 03:47:36 end=2026-10-20 03:47:45 elapsed=8s bound=600s status=OK rc=0
  [pyt] tag=b1green-unit-fb2 start=2026-10-20 03:47:45 end=2026-10-20 03:47:48 elapsed=3s bound=600s status=OK rc=0
```
Identity pins alone at HEAD (spec 4.2 / gate step 3, B1-R1's two child-process files included):
```
run1 (feedback, events superset, feedback superset, history, home) 119 passed  [pyt] tag=b1green-run1 start=2026-10-20 03:42:45 end=2026-10-20 03:42:50 elapsed=5s bound=600s status=OK rc=0
test_s75_fanout_identity.py 3 passed          [pyt] tag=b1green-id-fy25 start=2026-10-20 03:42:51 end=2026-10-20 03:42:55 elapsed=4s bound=600s status=OK rc=0
test_w4_13_flag_off_ledger.py 2 passed        [pyt] tag=b1green-id-w413 start=2026-10-20 03:42:56 end=2026-10-20 03:42:59 elapsed=4s bound=600s status=OK rc=0
test_stage_timings.py 2 passed (18 egress blocks = the base baseline class)  [pyt] tag=b1green-id-stage start=2026-10-20 03:43:00 end=2026-10-20 03:43:09 elapsed=9s bound=600s status=OK rc=0
test_s71_u13_compare_auth_required.py 137 passed  [pyt] tag=b1green-id-u13 start=2026-10-20 03:43:10 end=2026-10-20 03:43:15 elapsed=5s bound=600s status=OK rc=0
test_paid_route_metering.py 21 passed (2 sentinel blocks = baseline)  [pyt] tag=b1green-id-meter start=2026-10-20 03:43:15 end=2026-10-20 03:43:19 elapsed=4s bound=600s status=OK rc=0
test_sentry_channels_u8d_unit.py 141 passed   [pyt] tag=b1green-id-u8dunit start=2026-10-20 03:43:20 end=2026-10-20 03:43:29 elapsed=10s bound=600s status=OK rc=0
test_observability.py 24 passed               [pyt] tag=b1green-id-obs start=2026-10-20 03:43:30 end=2026-10-20 03:43:33 elapsed=3s bound=600s status=OK rc=0
test_retro_w1_1.py 39 passed                  [pyt] tag=b1green-id-retro start=2026-10-20 03:43:34 end=2026-10-20 03:43:42 elapsed=7s bound=600s status=OK rc=0
test_sentry_channels_u8d.py 131 passed        [pyt] tag=b1green-id-u8dchild start=2026-10-20 03:43:42 end=2026-10-20 03:43:48 elapsed=6s bound=600s status=OK rc=0
```
Flag-ON smoke of the spec 1.10 files (information; no existing pin reddens under the flag):
```
run1 119 passed [pyt] tag=b1green-smoke-run1 start=2026-10-20 03:47:49 end=2026-10-20 03:47:54 elapsed=5s bound=600s status=OK rc=0
run2 7 passed   [pyt] tag=b1green-smoke-run2 start=2026-10-20 03:47:54 end=2026-10-20 03:48:06 elapsed=11s bound=600s status=OK rc=0
run3 225 passed [pyt] tag=b1green-smoke-run3 start=2026-10-20 03:48:06 end=2026-10-20 03:48:21 elapsed=15s bound=600s status=OK rc=0
```
Comm set at HEAD: 305 files (the RED list of 288 UNION 17 tests that walk or read `app/` by path, found by the union rule at HEAD; `scripts/comm_set.py` does not exist in the tree, so the list is `comm_set_green.py`'s), 13 chunks of at most 25 files, bound 1200, the four NETWORK_FLAKY_EXCLUDE node ids deselected on every chunk:
```
comm-00 788 passed                 [pyt] tag=b1green-comm-00 start=2026-10-20 03:48:21 end=2026-10-20 03:48:58 elapsed=37s bound=1200s status=OK rc=0
comm-01 3 failed, 997 passed       [pyt] tag=b1green-comm-01 start=2026-10-20 03:48:58 end=2026-10-20 03:50:08 elapsed=69s bound=1200s status=FAIL rc=1
comm-02 518 passed                 [pyt] tag=b1green-comm-02 start=2026-10-20 03:50:08 end=2026-10-20 03:50:26 elapsed=18s bound=1200s status=OK rc=0
comm-03 2989 passed                [pyt] tag=b1green-comm-03 start=2026-10-20 03:50:27 end=2026-10-20 03:51:56 elapsed=90s bound=1200s status=OK rc=0
comm-04 594 passed                 [pyt] tag=b1green-comm-04 start=2026-10-20 03:51:57 end=2026-10-20 03:52:33 elapsed=36s bound=1200s status=OK rc=0
comm-05 465 passed                 [pyt] tag=b1green-comm-05 start=2026-10-20 03:52:33 end=2026-10-20 03:52:52 elapsed=19s bound=1200s status=OK rc=0
comm-06 4 failed, 580 passed       [pyt] tag=b1green-comm-06 start=2026-10-20 03:52:53 end=2026-10-20 03:53:27 elapsed=35s bound=1200s status=FAIL rc=1
comm-07 343 passed, 2 errors       [pyt] tag=b1green-comm-07 start=2026-10-20 03:53:28 end=2026-10-20 03:53:53 elapsed=26s bound=1200s status=FAIL rc=1
comm-08 1642 passed                [pyt] tag=b1green-comm-08 start=2026-10-20 03:53:54 end=2026-10-20 03:56:36 elapsed=163s bound=1200s status=OK rc=0
comm-09 1197 passed                [pyt] tag=b1green-comm-09 start=2026-10-20 03:56:36 end=2026-10-20 03:57:50 elapsed=74s bound=1200s status=OK rc=0
comm-10 367 passed                 [pyt] tag=b1green-comm-10 start=2026-10-20 03:57:51 end=2026-10-20 03:58:39 elapsed=49s bound=1200s status=OK rc=0
comm-11 1152 passed, 35 xfailed    [pyt] tag=b1green-comm-11 start=2026-10-20 03:58:40 end=2026-10-20 03:59:24 elapsed=45s bound=1200s status=OK rc=0
comm-12 81 passed                  [pyt] tag=b1green-comm-12 start=2026-10-20 03:59:25 end=2026-10-20 03:59:36 elapsed=11s bound=1200s status=OK rc=0
```
HEAD failures (9 node ids): the seven `tests/.pre_impl_failures.txt` baseline nodes the RED base run recorded (`test_camera_vision.py::TestIdentifyProductsMocked` x3, `test_page_scraping.py` x2, `test_personalization_bundle_c.py` x2) plus the two `tests/test_prompt_truth.py` nodes (`test_render_digests_match_base_except_the_fence`, `test_truth_on_prefix_static_and_cacheable`: the netguard refusing the cold tiktoken encoding download `openaipublic.blob.core.windows.net`, the environmental class the common brief names). That file was not in the RED base list, so it was re-run ALONE at base (a detached scratch worktree at 81df2b64, removed afterwards) and at HEAD: the SAME two ERRORs, the same cause, both sides:
```
base 31 passed, 2 skipped, 1 xfailed, 2 errors [pyt] tag=b1green-pt-base start=2026-10-20 04:01:19 end=2026-10-20 04:01:22 elapsed=3s bound=600s status=FAIL rc=1
HEAD 31 passed, 2 skipped, 1 xfailed, 2 errors [pyt] tag=b1green-pt-head start=2026-10-20 04:01:23 end=2026-10-20 04:01:26 elapsed=3s bound=600s status=FAIL rc=1
```
**branch-only-NEW = EMPTY.** The unit's own 191 RED rows pass at HEAD (they were the only other base failures).

CI-order set (20 files in alphabetical order: the two unit files + every pin file above + `test_w4_13_measurement_truth.py`, `test_comparison_id_echo.py`, the two CLAUDE.md readers), one process:
```
1155 passed [pyt] tag=b1green-ci-order start=2026-10-20 03:59:36 end=2026-10-20 04:00:20 elapsed=44s bound=1200s status=OK rc=0
```
Lint: `ruff check --select E9,F63,F7,F82` clean on every changed file; `py_compile` clean; full default ruff before == after on every edited file (pre-existing noise only) and 0 on the new module; the pre-commit hook passed (`All checks passed!`). Added-line sweep over `git diff 81df2b64` + the new files: 0 key shapes, 0 JWT / PEM / credentialed-URL shapes, 0 personal values (the only 8-digit runs are the frozen RED files' synthetic UUID literals). CRLF kept on every edited file (bare-LF lines 0; non-ASCII byte counts unchanged); the three new files are LF; `git diff --stat` content lines only.

## Stated limits

- `identity_confidence` has no vision signal until B3 threads `assess_result(vision_confidences=...)`; `medium` means an empty brand or a product with no corroborating signal, never "the model was unsure".
- `unsupported_category` is reachable only through a per-product category conflict (every `category_used` is one of the nine), and only when BOTH names carry a generic category word: the explicit-pair path stamps `['other','other']` for brand-only names, so the cross-category rule cannot fire there (GA-1, measured: `Casio G-Shock watch` -> `other`); the parser path and the stream carry the LLM's per-product category.
- `failed` is unreachable through any B1 exit (every emitter site is success-only); a direct `assess_result` call only.
- The URL envelope is never stamped (R0-1; B4 owns it); its telemetry reads a body without prices or `scoring_v2`, so its status is mostly `partial_no_winner`.
- The stream emits no message for a terminal the client never received (refunded, not delivered).
- `profile_routes.py:75/:97/:141` (recent decisions) still crown a stamped non-supported row: ruling B1-R11 Q7 asked for the same `result_status` skip "with a P8-style pin" in this unit, but the frozen RED files carry no row for it and an unpinned reader change would violate R-A13, so it is NOT implemented here (open question for the gate; the CLAUDE.md row states it).
- The compare-route transaction volume rises to 100 % of compare requests under the flag (the Sentry transaction quota is the owner's reading before the flip); the sampler changes the SDK code path in both states, with the OFF decision identical by construction (parent decision else the live rate).
- A mid-request flip can yield a stamped body without a message, or the reverse, for at most one in-flight request.
- Stored rows carry the tier-3 marker on 3 of 52 corpus products only, so B2 must honour the STAMPED status, not recompute it on old rows.
- CR1 (B1-R12, accepted): after the flip and before the C1 OTA a stamped non-supported row shows no winner highlight and placeholder tiles in the build-3 History list; the flip is post-approval.
- Mutant X19 (the stamp moved before the price chokepoint) is the correctness adversary's hand mutant (GA-4).

## Owner steps (names only)

1. Nothing before merge; nothing before approval (UB-R4; no OTA).
2. After approval, the FIRST flip of the R-A2 order: set `ENABLE_RESULT_STATUS_METADATA=true` on `web`; read one canary window in Sentry (Issues: the `comparison_result_status` message grouped by the `result_status` and `input_type` tags; Performance: the four compare transactions at 100 %) and the Railway log for `[RESULT_STATUS]` WARNING lines (expected none).
3. Check the Sentry plan's transaction quota against the compare request rate before the flip.
4. The allowlist widening is live at merge (unflagged) and must be deployed BEFORE any client bundle fires the six event names or the six chip values (the C6 / C7 OTAs after approval).
5. Rollback: unset the variable (per call, immediate); rows stamped during the window stay stamped and keep being skipped by Home.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

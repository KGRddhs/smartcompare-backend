## B3 VISION-IDENTITY-V2: camera identification v2 behind `ENABLE_VISION_IDENTITY_V2` (dark)

Branch `feature/s80-b3-vision-identity-v2`, GREEN commit `764d44162dd83563dc5c9aa930dcb9c192f35f89` on base `81df2b641454e0301cca51a3ba01bf8ef3d7e649` (not yet rebased; the orchestrator rebases onto `origin/main` `4a38ce93` after the adversaries, GB-11). Spec `.qa-s80/B3_UNIT_SPEC.md` of the unit worktree as amended by the review (C1-C15), rulings B3-R1..B3-R7 + G-1..G-4 (`RULINGS_BATCH1.md`) and the RED gate GB-1..GB-11 (`specs/GATE_B3.md`), all in `docs/investigations/2026-10-19-session-80-state/`.

### What the flag does

`ENABLE_VISION_IDENTITY_V2` (default OFF, read per call: the FIRST statement of `identify_products`, and once per camera request at the compare site) + knob `VISION_TIMEOUT_SECONDS` (default 20.0 s; garbage / inf / nan / <= 0 -> 20.0 with one WARNING naming the variable; read only under the flag).

**ON**
- `identify_products` sends a SECOND prompt `VISION_PROMPT_V2` (exact-label OCR kept; no brand or name invented from shape: unreadable fields null + confidence low; Arabic-script labels transliterated with the Latin brand kept; the nine canonical categories; a 0-based `image_index`) with `response_format` = strict json_schema `vision_products_v2` (category branch `anyOf [{type string, enum of nine}, {type null}]`, GB-3), `max_tokens` 1000 through the same `token_limit_kwargs` / `sampling_kwargs` / `guarded_llm_create` chokepoint, under `asyncio.wait_for(VISION_TIMEOUT_SECONDS)`.
- A second normaliser accepts the object or a bare array; drops non-dict items and `is_product` false candidates; keeps ONE best candidate per `image_index` (highest confidence, ties keep the earlier) and the best TWO for a one-image request (B3-R6(2)); keeps an `image_index` that names no image of the request UNPAIRED (`_image_index` None) after the paired picks in reply order (B3-R6(3) / GB-1); no product-count cap (GB-2).
- Each product keeps the five public keys and carries `_image_index, _category, _product_type, _distinguishing_features, _is_product`; the route strips every underscore key from every wire body (`public_vision_products`, unconditional, a no-op on V1 products) while `compare_from_text` receives the un-stripped list; the orchestrator's REST and stream identity dicts gain `_vision_confidence, _vision_category, _vision_distinguishing_features, _vision_is_product, _vision_image_index` (presence-gated on `_is_product`, never on the wire).
- A refused / None / choice-less reply raises `LLMUnavailableError`; a vision expiry raises `TimeoutError`; both ride the route's EXISTING coded 503 `LLM_UNAVAILABLE` (never `TIMEOUT`, B3-R6(1); never a 500). `finish_reason=length` is the V1-shaped parse failure (the existing `action:"error"` exit, refunded).
- A signed-in scan gets the text route's personalisation: `user_id` and, only when `preferences_completed`, `user_preferences` as CONDITIONAL kwargs (fail-soft read, `[IMAGE] preferences read failed: <Type>`); with `user_id` the orchestrator also reads the behaviour profile + demographics and writes the behaviour profile after a delivered compare (B3-R3).
- Log lines: `[VISION_V2] candidates= kept= dropped_not_product= unpaired_index= dropped_non_dict= unknown_brand= unknown_name= images= finish_reason=` (INFO), `[VISION_V2] no content: finish_reason= refused=`, `[VISION_V2] finish_reason=length; ...`, `[VISION_V2] vision call timed out after <x.x>s` (WARNING): ints, bools, the finish_reason literal, type names; never a product string.

**OFF**: byte-identical: the base prompt (sha256 `bb737687...`), message layout and kwargs `{model, messages, max_tokens 500, temperature 0, store False}` (no `response_format`, no `wait_for`, no knob read), the base five-key normaliser, the base six-key identity dicts, the base three-kwarg camera call with no preferences read, and the base bodies.

### Defect ids -> RED node ids -> flag -> activation precondition

| defect | RED / PIN nodes (tests/test_s80_b3_vision_identity_v2.py) | flag | precondition |
|---|---|---|---|
| MYEZ-001 products that are not the photographed ones (V04) | R1, R3, R6, R6b, R7, R7b, R8, R8c, R8d, R18, R21 (identification + evidence carried; the refusal is B2's) | ENABLE_VISION_IDENTITY_V2 | owner's structured-output smoke test; after ENABLE_RESULT_STATUS_METADATA; full fix with B2 ENABLE_RESULT_GATE + B7 |
| MYEZ-004 two different shirts as one identity (V07) | R2, R13, R14, R15, R19 (distinguishing features + image index carried to the identity dicts for B2) | ENABLE_VISION_IDENTITY_V2 | as above; the refusal is B2's |
| MYEZ-015 ~40 s scan (vision bound) | R10, R10b, R11 | ENABLE_VISION_IDENTITY_V2 (+ VISION_TIMEOUT_SECONDS) | as above |
| OWNER-CAMERA the AI cannot spot products | R1, R2, R5, R6, R6b, R7, R8, R8b, R8c, R8d, R9, R18, R19, R20, R22 | ENABLE_VISION_IDENTITY_V2 | OPENAI_MODEL_VISION smoke-tested by the owner (names only) |
| OWNER-OPENAI (vision half) json_schema, finish_reason, refusal, bound | R3, R4 x3, R4b, R5, R5b, R10, R10b, R22 | ENABLE_VISION_IDENTITY_V2 | as above |
| R0-4 camera personalisation | R16, R16b x3, R16c (PIN-ON), P6 | ENABLE_VISION_IDENTITY_V2 | as above |
| wire hygiene (no internal key on the wire) | R17 x6 arms, R23, P7 x6 | unflagged (no-op on V1, R-A1(c)) | none |
| flag-OFF identity | P1 x7, P2 x7, P3, P3b, P4/P5 x3, P6 x2, P7 x6, P8 x7, P10 | n/a | none |

RED at base (orchestrator re-run, GATE_B3): 69 failed / 36 passed, every failure an AssertionError. GREEN at HEAD: 105 passed, flag unset and flag ON.

### Deliberate pin changes (spec 4.1, E1-E5 per GB-9, plus E6-E8)

| # | file / node | before | after | reason |
|---|---|---|---|---|
| E1 | `tests/test_camera_vision.py::TestIdentifyProductsMocked::test_malformed_response_returns_error` | FAILED at base (TypeError at `openai_service.py:81`), deselected in CI | PASSES; `types.SimpleNamespace` usage, assertions unchanged | fixture defect (R-A14) |
| E2 | `...::test_successful_identification` | FAILED at base | PASSES, assertions unchanged | same |
| E3 | `...::test_empty_product_fields_normalized` | FAILED at base | PASSES, assertions unchanged | same |
| E4 | `tests/.pre_impl_failures.txt` (3 rows + header) + `tests/PRE_IMPL_FAILURE_BASELINE.md` | 11 ids | 8 ids; a dated PRUNED paragraph with no `::` on any comment line (GB-6); mirror regenerated with `python -m scripts.gen_baseline_mirror` (`--check`: OK, 8 nodes) | per-row prune with pass proof; `tests/test_ci_gates.py::test_baseline_count_is_rederivable_from_the_committed_file` green at HEAD |
| E5 | the four clear-lists: `tests/test_model_config_enforced.py` `_clean_env`, `tests/w4_11_prompt_digest_recorder.py` `FLAGS`, `tests/test_prompt_fence.py` `_W411_FLAGS`, `tests/test_s71_u13_compare_auth_required.py` `CLEAN_ENV` | without the flag | + `ENABLE_VISION_IDENTITY_V2` | R0-6; the W4-11 digest fixture and the T23 OpenAPI fixture are untouched |
| E6 | `tests/test_model_config_enforced.py::test_no_call_site_passes_raw_sampling_kwargs` | 15 sites | 16 sites (the V2 call), assertion unedited (`>= 15`, no raw `temperature=` / `max_tokens=`) | by design of the pin |
| E7 | `CLAUDE.md` (the 11 -> 8 sentences, the flag row, `VISION_TIMEOUT_SECONDS`) | 11 | 8, dated | principle 5 |
| E8 | `tests/test_regression_gate_diff.py::test_load_baseline_reads_committed_file` (:183) | asserted a `test_camera_vision.py` id is a documented baseline member | asserts `test_auth_interceptor.py` is a member AND `test_camera_vision.py` is absent | NOT in the spec's list: the prune broke it (green at base, red at the first HEAD comm pass); found by the comm set, fixed minimally; reported as a deviation for the gate |

The camera_vision pass proof at HEAD (verbatim):

```
================ 25 passed, 1 deselected, 11 warnings in 4.74s ================
[hermeticity] sentinel checked 25 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3green-camera-vision-head start=2026-10-20 07:29:59 end=2026-10-20 07:30:05 elapsed=6s bound=600s status=OK rc=0
```

### Gates (every pytest through the bounded runner, one process at a time)

```
unit file, flag unset (HEAD bytes):  105 passed
[pyt] tag=b3green-unit-off-final start=2026-10-20 07:27:42 end=2026-10-20 07:27:47 elapsed=5s bound=600s status=OK rc=0
unit file, ENABLE_VISION_IDENTITY_V2=true in the runner env only:  105 passed
[pyt] tag=b3green-unit-on-final start=2026-10-20 07:27:48 end=2026-10-20 07:27:53 elapsed=5s bound=600s status=OK rc=0
CI-order set at HEAD 764d4416 (30 files): 1359 passed, 1 skipped, 1 deselected; [hermeticity] 1360; [netguard] blocked 29 attempt(s) from 23 node(s)
[pyt] tag=b3green-ciorder-head start=2026-10-20 07:29:06 end=2026-10-20 07:29:49 elapsed=43s bound=1200s status=OK rc=0
```

CI-order set (sorted): b2_strict_optional_auth, backend_cleanup, camera_vision, ci_gates, comparison_id_echo, cost_meter_s74, explicit_pair_category, image_identify_llm_unavailable_s69, legal_docs_u8, logger_no_query_leak, m13_03_paid_work_gating, m13_26_image_error_envelope, m18_openai_tpm_sizing, model_config, model_config_enforced, openai_key_log_hygiene_s69, paid_route_metering, prompt_fence, regression_gate_diff, retro_w2_1, s71_u13_compare_auth_required, s75_fanout_identity, s80_b3_vision_identity_v2, security_regression, sentry_channels_u8d_unit, shutdown_drain, text_error_envelope_no_raw_exception, u3c_store_false_pin, w4_13_flag_off_ledger, w4_13_measurement_truth.

**Comm set (zero-regression gate).** HEAD list = the RED base list (246 files: module grep 204 + symbol grep + source-scanning pins + CLAUDE.md readers + SmartCompareApp scanners, minus the hook tests) UNION the HEAD re-derivation with the symbols this unit introduces or newly references (`public_vision_products`, `vision_identity_v2_enabled`, `_vision_identity_fields`, `_camera_user_preferences`, `VISION_*`, `ENABLE_VISION_IDENTITY_V2`, `get_user_preferences`) = **248 files, 10 chunks** (head-only: `tests/test_auth_preference_toggles_w314.py`, the unit file; nothing in the RED list fell out). Base FAILED/ERROR set (RED, 7) = the three camera_vision rows, the two `test_page_scraping.py` baseline rows, the two cold-tiktoken `test_prompt_truth.py` ERRORs. HEAD set (4) = the two page_scraping rows + the two tiktoken ERRORs. **branch-only-NEW (`comm -13` base head) = EMPTY**; fixed = the three camera_vision rows. (The first HEAD pass of chunk 7 showed `test_regression_gate_diff.py::test_load_baseline_reads_committed_file` as branch-only-new; E8 fixed it and chunk 7 was re-run on the final bytes.)

```
c01 779 passed, 5 deselected; [hermeticity] 779; [netguard] blocked 60 attempt(s) from 18 node(s)
[pyt] tag=b3green-comm-head-c01 start=2026-10-20 06:51:59 end=2026-10-20 06:53:15 elapsed=76s bound=1200s status=OK rc=0
c02 1125 passed, 1 skipped, 2 deselected; [hermeticity] 1126; [netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=b3green-comm-head-c02 start=2026-10-20 06:53:16 end=2026-10-20 06:55:31 elapsed=136s bound=1200s status=OK rc=0
c03 1943 passed, 1 skipped; [hermeticity] 1943; [netguard] blocked 59 attempt(s) from 19 node(s)
[pyt] tag=b3green-comm-head-c03 start=2026-10-20 06:56:11 end=2026-10-20 06:57:34 elapsed=83s bound=1200s status=OK rc=0
c04 1671 passed, 5 deselected; [hermeticity] 1671; [netguard] blocked 39 attempt(s) from 30 node(s)
[pyt] tag=b3green-comm-head-c04 start=2026-10-20 06:57:35 end=2026-10-20 07:01:36 elapsed=241s bound=1200s status=OK rc=0
c05 551 passed, 4 deselected; [hermeticity] 551; [netguard] blocked 8 attempt(s) from 2 node(s)
[pyt] tag=b3green-comm-head-c05 start=2026-10-20 07:07:31 end=2026-10-20 07:08:13 elapsed=43s bound=1200s status=OK rc=0
c06 2 failed (the two page_scraping baseline rows), 487 passed, 7 deselected; [hermeticity] 489; [netguard] blocked 156 attempt(s) from 21 node(s)
[pyt] tag=b3green-comm-head-c06 start=2026-10-20 07:08:14 end=2026-10-20 07:08:57 elapsed=42s bound=1200s status=FAIL rc=1
c07 (final) 885 passed, 4 skipped, 2 deselected, 1 xfailed, 2 errors (the two tiktoken ERRORs); [hermeticity] 889; [netguard] blocked 111 attempt(s) from 9 node(s)
[pyt] tag=b3green-comm-head-c07 start=2026-10-20 07:19:44 end=2026-10-20 07:21:37 elapsed=113s bound=1200s status=FAIL rc=1
c08 1701 passed; [hermeticity] 1701; [netguard] blocked 22 attempt(s) from 10 node(s)
[pyt] tag=b3green-comm-head-c08 start=2026-10-20 07:11:39 end=2026-10-20 07:15:26 elapsed=226s bound=1200s status=OK rc=0
c09 401 passed, 2 skipped, 12 deselected; [hermeticity] 402; [netguard] blocked 126 attempt(s) from 47 node(s)
[pyt] tag=b3green-comm-head-c09 start=2026-10-20 07:16:46 end=2026-10-20 07:18:10 elapsed=84s bound=1200s status=OK rc=0
c10 1085 passed, 6 deselected, 35 xfailed; [hermeticity] 1120; [netguard] blocked 81 attempt(s) from 32 node(s)
[pyt] tag=b3green-comm-head-c10 start=2026-10-20 07:18:11 end=2026-10-20 07:19:30 elapsed=79s bound=1200s status=OK rc=0
```

The netguard counts are sentinel-neutralised ratchet nodes (no egress). Chunks c01/c02 ran before the CLAUDE.md edit; the two CLAUDE.md readers were re-run on the final bytes with the E8 file: `111 passed, 1 skipped` `[pyt] tag=b3green-rgd-and-claude-readers start=2026-10-20 07:16:17 end=2026-10-20 07:16:37 elapsed=20s bound=600s status=OK rc=0`.

Lint / syntax: `ruff check --select E9,F63,F7,F82` clean on all ten changed Python files; `py_compile` clean; the full default ruff rule set reports the same per-rule counts at base and HEAD on the three source files (no new finding). Byte hygiene: every added line ASCII (high-byte counts unchanged per file), CRLF kept on every existing file (no bare LF), the RED file LF and byte-identical (sha256 `36b78a40...`). Pre-commit hook: passed.

GREEN mutation spot-check on the GREEN bytes (14 mutants, byte copy / exact edit / unit file / restore / sha256): 14 KILLED by AssertionError, 14 restores verified (flag-first branch removed; route forwarding ungated; metadata strip removed; unpaired before paired; one image keeps one; feature cap removed; `_vision_image_index` dropped; `wait_for` unbounded; raising preferences read propagates; unknown confidence -> medium; None content returns a failure dict; knob read before the flag; preferences forwarded when not completed; missing `is_product` -> False). The RED agent's 70-mutant table on the prototype is in the RED report.

### Stated limits

1. Whether the live vision model accepts strict structured outputs with image input is unmeasured offline; a `BadRequestError` on `response_format` takes today's non-transient 500 branch until the flag is unset.
2. A 1-based `image_index` reply degrades to V1 pairing (index 1 paired with the second photo, index 2 unpaired), counted by `unpaired_index`.
3. No product-count cap (GB-2): the prompt bounds the reply at 4; the route compares `products[0]` and `products[1]`; extra products reach only `metadata.identified_products`.
4. `is_product` false candidates are dropped, so B2 sees only their absence.
5. V2 alone still compares a low-confidence pair (V04) and a same-identity pair (V07); the refusal is B2's. V2's no-invention rule can raise the `Unknown` / `Unknown Product` share against V1 (`unknown_brand` / `unknown_name` size it).
6. The `wait_for` cancels only the awaiting coroutine (OpenAI may still bill; the SDK retries sit inside the bound; the breaker records nothing on a cancellation).
7. The cost figure stays the mini list price whatever `OPENAI_MODEL_VISION` resolves to.
8. A signed-in scan under ON adds the preferences read (inline on the loop while `ENABLE_SYNC_DB_OFFLOAD` is OFF), the behaviour-profile + demographics reads and the profile write.
9. The stream twin is pinned by source text only (R15); the camera route is REST-only.
10. The one client-visible value change: under ON an unknown confidence reads `low` instead of `medium` (build 3 does not render it).
11. `metadata.identified_products` is a copy (equal by value).
12. No `selected_category` on the camera path (T23 forbids a new route parameter; B8).
13. Arabic transliteration quality is unmeasured offline; `OPENAI_MODEL_VISION` is UNKNOWN on `web` (R-A15).
14. The exit-2 copy for a `finish_reason=length` reply blames the photo for a token cap (client copy is C1's).
15. The three mocked `tests/test_camera_vision.py` nodes do not clear the flag: never set `ENABLE_VISION_IDENTITY_V2` in a local `.env` (they would take the V2 path); CI runs flag OFF.
16. GB-7: `test_extraction_prompt_bundle_c.py::test_response_builder_strips_inference_source` and the `test_supplement_branch_genuine.py` baseline row pass on this box at base and HEAD; they stay listed until proven on CI (#89).

### Owner steps (names only)

1. HARD PRECONDITION: one live structured-output smoke test through the deployed route with two labelled photos; the `[VISION_V2] candidates=` line appears and no `BadRequestError` (a `BadRequestError` = do not flip). `OPENAI_MODEL_VISION` stays an env knob (default gpt-4o-mini).
2. Set `VISION_TIMEOUT_SECONDS` only if 20 s is wrong for the chosen model.
3. Flip `ENABLE_VISION_IDENTITY_V2` on `web` in its R-A2 window (after `ENABLE_RESULT_STATUS_METADATA`, before `ENABLE_IMAGE_PIPELINE_V2`), explicit yes, one canary window: two never-compared photo pairs (labelled + label-less); watch the `[VISION_V2]` counts, the 503 `LLM_UNAVAILABLE` and `action:"error"` rates on `/image/identify`, p50 vision latency vs 20 s, the camera `scoring_method` mix, the `behavior_profile_update` WARNING count, `BadRequestError` in the Railway log; one dated ledger line.
4. B2 (`ENABLE_RESULT_GATE`) is where the V04 / V07 refusals land.
5. Rollback: unset the variable (per call, immediate).

### Rebase note (for the orchestrator)

`CLAUDE.md` line 502 was edited at base and main `4a38ce93` (#363) edited the same line (`:109` -> `:81`); B3's line already carries `openai_service.py:81` (B3-R4), so the resolution is to take B3's line. The flag row sits after the SESSION 79 B3-B block (G-2); B1's row lands first and B3's goes after it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

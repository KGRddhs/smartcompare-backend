# B3 VISION-IDENTITY-V2 -- ADVERSARY REPORT, lens: correctness

- Unit B3 (ENABLE_VISION_IDENTITY_V2 + knob VISION_TIMEOUT_SECONDS). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s80-b3, branch feature/s80-b3-vision-identity-v2.
- HEAD verified at start and at end: 764d44162dd83563dc5c9aa930dcb9c192f35f89. `git status --short` of the real worktree: empty at start and at end. No .qa-mutation.lock left there.
- Frozen RED file tests/test_s80_b3_vision_identity_v2.py sha256 36b78a404deefbc4fbea66b2d75574f203346a8e53550a3ddf04d3550e4af15e at start AND at end (real worktree, bytes on disk).
- Real worktree source shas at end equal the GREEN report: openai_service.py ff15a9fe...1a3d, image_routes.py 4502ff0e...19ae, structured_comparison_service.py deaed222...3409.
- All probes and mutants ran in MY detached scratch worktree <scratchpad>/B3_adv_correctness @764d4416 (created with `git worktree add --detach`, removed with `git worktree remove --force`; `git worktree list | grep -c B3_adv_correctness` = 0; directory gone). The real worktree was never edited.
- Window 2026-10-20 07:41 -> 08:10 AST. No .env read, no secret printed, no network (netguard on every run), no personal values (synthetic ids "b3adv-<node>", product strings only). One pytest at a time; every run through pyt.py.

## VERDICT: SOUND (0 blocking, 0 major, 10 minor documentation / pin-gap rulings)

The GREEN bytes do what the spec, rulings B3-R1..R7 and gate GB-1..GB-11 require. Flag OFF is byte-identical on every path I could reach (prompt, layout, kwargs, normaliser, identity dicts, route call, bodies, ledger); flag ON maps every new failure onto an EXISTING refunded exit with the codes build 3 already renders; no internal key reaches any wire body. Every finding below is a pin gap in the frozen RED file or a documentation inaccuracy; none is a behaviour defect in the GREEN bytes.

## Minors (for the orchestrator's rulings)

- min-1 (doc, activation) The HARD PRECONDITION in the CLAUDE.md row and PR-body owner step 1 is not executable as written: "one live structured-output smoke test THROUGH THE DEPLOYED ROUTE ... the `[VISION_V2] candidates=` line appears ... before the flip". The flag is read per call from the `web` env and there is no per-request override, so the `[VISION_V2]` line can only appear on the deployed route AFTER the flag is ON there: the "smoke before the flip" IS the flip. Ruling B3-R6(4) says only "one live call with two photos". Suggested wording: either an off-route smoke (the owner runs `identify_products` with the production key and `ENABLE_VISION_IDENTITY_V2=true` in that ONE process env, e.g. a `railway run -s web -- env ENABLE_VISION_IDENTITY_V2=true <venv python> <script>`, two labelled photos, names only), or state plainly that the first canary call IS the smoke and the rollback is an immediate unset on a `BadRequestError`.
- min-2 (pin gap, MYEZ-001 core) The V2 prompt's two load-bearing rules are unpinned: deleting the no-invention rule (Z1), or renumbering images from 1 (Z2: "numbered from 1 ... image_index 1 is the first image"; Z3: "the 1-based number") all SURVIVE the 105-node unit file (R3 pins six substrings + two negatives and `text == VISION_PROMPT_V2`, which is self-referential). The GREEN report's "VISION_PROMPT_V2 equals the spec 2.2 block character for character, sha256 7d7f2c83..." is TRUE (I re-measured: 3,170 chars, ASCII, equal to the spec block, sha 7d7f2c83b11dfb8b05cb9541379b798bcaa6fe0cfeb16526bf38e8966723dd24) but no test enforces it. R-A13 "never exists again" for MYEZ-001 rests on that sentence. Suggested: a `VISION_PROMPT_SHA_ON` pin (the P1 pattern) or substrings "0-based", "do NOT invent", "set confidence to \"low\"" in a follow-up pin (the RED file is frozen; needs a gate ruling).
- min-3 (stated-limit gap, ruling consequence) Two-photo request where the model reports BOTH products at image_index 0 (one photo shows both items; the other photo shows nothing identifiable or a close-up of one of them): V2 keeps ONE (the best of index 0). Measured by probe: reply `[{idx0 A high}, {idx0 B high}]` on IMG(2) -> kept `['A']` -> the route ends in `need_second_product` where V1 compared A vs B; with a close-up of B as photo 2, V2 pairs best-of-photo-1 with B and can turn a valid V1 pair into a same-identity pair (crowned until B2). This is the literal consequence of ruling B3-R6(2) ("else one per image_index"), so GREEN is compliant; but neither the CLAUDE.md row nor the PR-body limits state it (limits 2/3 cover 1-based indices and the count cap only). Add it as a stated limit and a canary reading (`kept` < `candidates` with `images=2`), or re-rule (e.g. when one paired index is empty, keep the best two of the other).
- min-4 (doc accuracy) "The one client-visible value change: under ON a missing / unknown confidence reads `low`" (CLAUDE.md row; PR-body limit 10) is not true as worded. Under ON, other client-visible changes exist: the identified SET and therefore the `action` (comparison vs need_second_product vs error: dedupe per index, is_product drops, R7b/probe); a refused / None-content vision reply is 503 LLM_UNAVAILABLE where base 500s; a slow vision is a 503 after 20 s where base waited; a model `brand: null` reads "Unknown" (V1 shipped null); stripped strings; and for signed-in scans the whole personalised result (scores, scoring_method, personalization block). Suggested: "the one change in a field's value vocabulary" or drop the sentence (the row already lists the rest).
- min-5 (doc, test hazard understated) Limit 14 says only the three mocked test_camera_vision.py nodes go red with the flag set. Measured with `ENABLE_VISION_IDENTITY_V2=true` in the runner env over the 21-file camera identity set: those 3 fail, AND 53 nodes (56 attempts) of tests/test_retro_w2_1.py / test_paid_route_metering.py / test_m13_26 etc. now reach the REAL `get_user_preferences` through the unstubbed authed route and attempt a (sentinel-neutralised) Supabase connection; flag OFF the same set shows 3 attempts from 3 nodes (the existing ratchet rows). The netguard ratchet would report ~50 NEW egress nodes. Same rule (never set the flag in a local .env), wider blast radius; add it to the limit, or add the flag to those files' env hygiene in a follow-up.
- min-6 (pin gap, hand block-move XB1, the X19 analogue) Moving the route's `_compare_extra` block (flag read + preferences read) out of the compare `try` to BEFORE `identify_products` SURVIVES all 105 unit nodes: no row asserts that a non-delivery exit makes NO preferences read. Under the mutant every signed-in scan pays the Supabase read even when vision fails, refuses, times out or yields 0-1 products. GREEN's placement is correct (my probes: refusal 503, BadRequest 500, need_second_product -> `prefs.calls == []`); the probes kill the mutant (4 nodes).
- min-7 (pin gap) XB2: moving the `finish_reason == "length"` check above the no-content check survives; a length reply with NO content then becomes exit 2 (200 action:error) instead of the coded 503. GREEN order is right (probe `length + content None -> LLMUnavailableError` passes on GREEN, kills XB2).
- min-8 (pin gap) XB3: moving the flag-first branch below the V1 content build survives (V1 base64-encodes every image, then V2 encodes them again). The row/report claim "read ... as the FIRST statement of identify_products" is TRUE in the bytes but unpinned; a probe counting `encode_image_bytes_to_base64` calls (2 for IMG(2)) kills it.
- min-9 (pin gaps, observability) Y1 (dropping `_log_cache_telemetry` from the V2 path), Y2 (broadening `except asyncio.TimeoutError` to `except Exception`, which logs "[VISION_V2] vision call timed out" on a BadRequestError / 429 and would mislead the canary's timeout reading) and Y3 (ignoring a refusal when content is a string) all survive the unit file; GREEN behaviour is right on each (probes pass on GREEN, kill each mutant). Also observed: on a V2 expiry the route's existing line is `[IMAGE] Vision call failed: ` with an EMPTY tail (str(TimeoutError()) is ""), so the `[VISION_V2] vision call timed out` WARNING is the only discriminator in Railway/Sentry; worth one canary sentence.
- min-10 (doc, spend) Limit 5 says V2 "can RAISE the Unknown / Unknown Product share"; it does not say that such a placeholder pair ("Unknown Unknown Product vs ...") runs the full paid pipeline (Serper + LLM) and is DELIVERED and BILLED until B2 (ENABLE_RESULT_GATE) flips, which R-A2 orders several windows later. One clause in the limit and a canary item (billed camera compares with `unknown_name` > 0) would make the window's cost explicit.
- Note (not a finding) "X19 block-move by hand": X19 is B1's mutant id (scripts/wf_unit_green.js inserts the phrase for every unit); B3 has no X19. I applied three hand block-moves on B3's own seams instead (XB1-XB3 above).

## Runtime truth of the GREEN claims (probed, scratch worktree, real code paths)

| claim | probe | result |
|---|---|---|
| flag OFF byte-identical (prompt sha, layout, kwargs, no wait_for, no knob read, V1 normaliser, identity dicts, route call, bodies) | unit file OFF + ON; 21-file camera identity set OFF (W2-1 body pins, T23, FY25, W4-13 ledger, cost meter, M1 / U3c / prompt-fence / u8d / key-hygiene / logger pins) | TRUE: 105/105 both states; identity set 939 passed OFF |
| V2 parser on REAL openai SDK objects (ChatCompletion.model_validate, CompletionUsage with prompt_tokens_details) | test_probe_real_sdk_objects_v2_parse | TRUE: object reply -> 2 products, cost 2.4e-05; content null + refusal -> LLMUnavailableError; length -> parse failure naming finish_reason=length; content_filter + null -> LLMUnavailableError |
| refused / None / choice-less -> coded 503 LLM_UNAVAILABLE, both refunds, no compare (error-handler mapping) | test_probe_503_body_shape_and_no_history + R4b | TRUE: 503 body keys [code, error, request_id, success], success False, code LLM_UNAVAILABLE; refunds == consumes; lifetime [], history [], log_search [] (R-A3) |
| vision expiry -> 503 LLM_UNAVAILABLE (never TIMEOUT), refunds incl. ANON with consumed_keys | test_probe_anon_refund_on_v2_timeout (anon gate ON, metering ON, knob 0.05, fake delay 2 s) | TRUE: 503 LLM_UNAVAILABLE; anon refund called once with ("a"*64, {"daily": "ad"}); no compare, no prefs read |
| BadRequestError on response_format -> today's non-transient 500 (stated limit 1) | test_probe_badrequest_is_500_with_refund | TRUE: 500 body {"code": "SERVER_ERROR", "error": "Image analysis failed. Please try again.", "success": false, request_id}; build 3 maps SERVER_ERROR to engineUnavailable; refunds == consumes; no compare, no prefs read, no history, no lifetime |
| preferences read only at the compare site (not on non-delivery exits) | test_probe_need_second_product_under_v2_has_no_prefs_read + the two above | TRUE in the bytes (prefs.calls == [] on 503, 500, need_second_product); UNPINNED in the unit file (min-6) |
| mid-request flip (identify ON, compare-site read OFF) | test_probe_route_vision_ms_and_identity | safe: no user_id/prefs forwarded, compare gets the internal keys, `'"_' not in resp.text` |
| internal keys never on the wire | R17 x6 arms + probes; grep of every `products` / `vision_result` use in image_routes.py (6 wire sites, all wrapped) and of every `vision_products` / identity-dict consumer in scs (only `_resolve_pair_category` + `_fetch_product_data`, which builds a fresh dict; the stream twin is unreachable with vision products: the only `compare_from_text_streaming` caller, text_routes.py:1097, passes none) | TRUE |
| user_id forwarding effects (B3-R3 / row) | code read: scs:4332-4336 (behaviour profile + demographics concurrent with the gather), :4687-4691 (`_update_behavior_profile` fire-and-forget only on the delivered return), :4443-4445 + :4469/:4494 (cohort profile into scoring and the verdict); no persistence / metering inside the orchestrator (no save_comparison / record_* / log_search in scs) | TRUE |
| user_preferences `{}` divergence vs the text route (text forwards `{}`, camera forwards nothing) | response_builder.py:1570 `personalized = user_preferences is not None and bool(user_preferences)` | equivalent (no finding) |
| breaker interplay on a wait_for cancellation (limit 6) | code read api_budget_service.guarded_llm_create: CancelledError releases a half-open probe and records nothing; flag OFF the breaker is not read | TRUE |
| VISION_PROMPT_V2 == spec 2.2 block, ASCII, 3,170 chars, sha 7d7f2c83... | probe_prompt.py (imports the module, extracts the fenced spec block) | TRUE (but unpinned: min-2) |
| 8 baseline rows, mirror current, no camera_vision row | `python -m scripts.gen_baseline_mirror --check`; `regression_gate_diff.parse_failure_ids` | TRUE: "OK: mirror is current (8 nodes)"; 8 ids; camera_vision absent |
| limit 14 (camera_vision red with the flag set) | camera_vision with the flag ON in the runner env | TRUE (3 failed); understated (min-5) |
| contract freeze (PLAN 0) | build-3 codes only (LLM_UNAVAILABLE coded 503, SERVER_ERROR 500, action:error / need_second_product decided before compare_from_text, never comparison_failed for a vision outcome); public key set and types unchanged; no top-level `result` key added | TRUE |
| byte hygiene of the 13 files | bytes_check.py: high-byte counts base == head except .pre_impl_failures.txt 45 -> 42 (the deleted em-dash bullet); 0 bare LF in every CRLF file | TRUE |
| commit trailer | `git log -1` | `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (matches the ledger's model record for GREEN; D2 is a record question, not a defect) |

## Mutation table (scratch worktree; byte copy -> exact edit matching once -> unit file via pyt.py bound 600 -> restore from the copy -> sha256 compare; lock <scratch>/.qa-mutation.lock held and removed)

Spec mutants KILLED (39, each by AssertionError; no non-assert E-lines; every restore sha-equal):
M1 (17 nodes: P1 x7, P2 x7, P3, P3b, P10), M2 (R12 TRUE/ON/" true "), M3 (P1 x7, P2 x7, R10), M4 (R10, R10b), M5 (R11 -3/0/1e400/inf/nan), M6b (R3), M7a (R3), M8 (R4 x3, R4b), M9 (R4 x3, R4b), M10 (R5, R5b), M11a (9: R1, R6, R6b, R7, R7b, R8d, R9, R18, R20), M12 (R6, R6b), M13b (R6, R6b), M14 (R7, R7b), M15b (R8), M16b (R9), M17b (R9), M18 (R9), M19b (6: R1, R2, R7b, R9, R18, R20), M20b (R17 a/b, R18, R19, R20), M20c (R17 d), M21 (8: R17 a,b,d,e,f, R18, R19, R20), M22a (R16b x3), M23 (P6 x2), M24 (R16b not_completed), M25a (R16b raises, P8 route x3), M26 (P4/P5 x3, R13 v1), M27b (R13 v2), M27c (R13 x2, R14), M28 (R15), M29 (R21, R3), M30a (R4 refusal, P8 x4), M31 (test_model_config_enforced::test_no_call_site_passes_raw_sampling_kwargs, run with the unit file), M33b (R22), M36 (R8b), M39 (R6b), M42 (R10, R10b), M44b (P1 x7; M44's first edit string matched twice -- the sentence is shared by V1 and V2 -- and was retargeted to the V1-only "Identify products even WITHOUT packaging"), M45 (P2 x7).

Non-spec / hand mutants (on the frozen unit file):
| id | mutant | unit file | killed by my probes |
|---|---|---|---|
| XB1 | route prefs block moved above the vision call (hand block-move) | SURVIVED | KILLED (4 probe nodes) |
| XB2 | length check moved above the no-content check (hand block-move) | SURVIVED | KILLED (length + None content) |
| XB3 | flag-first branch moved below the V1 content build (hand block-move) | SURVIVED | KILLED (encode call count) |
| Y1 | `_log_cache_telemetry` dropped from V2 | SURVIVED | KILLED |
| Y2 | `except asyncio.TimeoutError` -> `except Exception` | SURVIVED | KILLED |
| Y3 | refusal ignored when content is a str | SURVIVED | KILLED |
| Y4 | duplicate `region` kwarg forwarded | KILLED (15 nodes) | - |
| Z1 | no-invention rule deleted from VISION_PROMPT_V2 | SURVIVED | not behaviour-testable (needs a text pin, min-2) |
| Z2 | "numbered from 1 ... image_index 1 is the first image" | SURVIVED | same |
| Z3 | "the 1-based number of the image" | SURVIVED | same |

Equivalent survivors: none of the above is equivalent in the strict sense; XB2 and Y3 differ only on inputs the live API rarely emits (length with null content; a refusal with a content string), XB3 only in CPU work. All are reported for a ruling, not fixed.

Final restore: `sha256sum -c` of the three source files in the scratch worktree OK after every batch (sha_before_mut.txt: ff15a9fe..., 4502ff0e..., deaed222...).

## Prove-nothing rows (unit file)

- R15: a source-text pin on the STREAM twin's splat; the stream twin is unreachable with vision products (the only `compare_from_text_streaming` caller, text_routes.py:1097, passes no `vision_products`), so the row proves lockstep text only.
- P4/P5 flag axis (3 nodes) and R14's `_full_config(..., "true")`: the orchestrator reads no flag (presence gating), so the flag parametrisation proves nothing beyond one node; the presence-gating assertion itself is real (kills M26).
- P8 at base: vacuous by design (no [VISION_V2] lines exist at base); non-vacuous on GREEN (kills M30a, M25a).
- R3's `text == VISION_PROMPT_V2`: self-referential (the sent text equals the module constant); the content check is only the 6 substrings + 2 negatives (min-2).
- R5b body half: identical at base; only the WARNING assertion makes it RED.
- R17 arm b (flag OFF with a V2-shaped stub): a state production reaches only through a mid-request flip; a design pin (kills M48 in the RED table), not a production scenario.

## Runs (every pytest through pyt.py; [hermeticity] / [netguard] lines)

```
unit file, flag unset:  105 passed, 10 warnings in 4.47s; [hermeticity] sentinel checked 105 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3adv-unit-off start=2026-10-20 07:46:01 end=2026-10-20 07:46:07 elapsed=6s bound=600s status=OK rc=0
unit file, ENABLE_VISION_IDENTITY_V2=true in the runner env only:  105 passed, 10 warnings in 3.09s; [hermeticity] 105; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3adv-unit-on start=2026-10-20 07:46:13 end=2026-10-20 07:46:17 elapsed=4s bound=600s status=OK rc=0
camera_vision, flag unset:  25 passed, 1 deselected, 11 warnings in 2.42s; [hermeticity] 25; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3adv-camera-vision start=2026-10-20 07:46:19 end=2026-10-20 07:46:24 elapsed=5s bound=600s status=OK rc=0
camera_vision, flag ON:  3 failed (the three TestIdentifyProductsMocked nodes, limit 14), 22 passed, 1 deselected; [hermeticity] 25; [netguard] blocked 0
[pyt] tag=b3adv-camera-vision-on start=2026-10-20 07:46:31 end=2026-10-20 07:46:35 elapsed=4s bound=600s status=FAIL rc=1
probes (7 nodes, GREEN bytes):  7 passed; [hermeticity] 7; [netguard] blocked 0
[pyt] tag=b3adv-probe-1 start=2026-10-20 07:50:07 end=2026-10-20 07:50:11 elapsed=4s bound=600s status=OK rc=0
probes (12 nodes, GREEN bytes):  12 passed; [hermeticity] 12; [netguard] blocked 0
[pyt] tag=b3adv-probe-2 start=2026-10-20 07:57:27 end=2026-10-20 07:57:32 elapsed=4s bound=600s status=OK rc=0
camera identity set (21 files: retro_w2_1, image_identify_llm_unavailable_s69, paid_route_metering, m13_26, w4_13 ledger + truth, cost_meter_s74, s75_fanout_identity, explicit_pair_category, s71_u13 (T23), m13_03, b2_strict_optional_auth, comparison_id_echo, model_config_enforced, u3c_store_false_pin, prompt_fence, sentry_channels_u8d_unit, logger_no_query_leak, openai_key_log_hygiene_s69, model_config, camera_vision), flag unset:
  939 passed, 1 deselected, 13 warnings in 59.89s; [hermeticity] 939; [netguard] blocked 3 attempt(s) from 3 node(s) (the existing ratchet rows: paid_route_metering x2, m13_26 x1, neutralized.supabase.invalid)
[pyt] tag=b3adv-identity-off start=2026-10-20 07:59:17 end=2026-10-20 08:00:20 elapsed=62s bound=1200s status=OK rc=0
same set, flag ON:  3 failed (camera_vision x3), 936 passed, 1 deselected; [hermeticity] 939; [netguard] blocked 56 attempt(s) from 53 node(s) (min-5)
[pyt] tag=b3adv-identity-on start=2026-10-20 08:00:30 end=2026-10-20 08:01:27 elapsed=57s bound=1200s status=FAIL rc=1
remaining camera-path files (backend_cleanup, security_regression, shutdown_drain, text_error_envelope_no_raw_exception), flag ON:  173 passed
[pyt] tag=b3adv-camera-rest-on start=2026-10-20 08:06:20 end=2026-10-20 08:06:30 elapsed=11s bound=1200s status=OK rc=0
```
Mutant [pyt] lines (all bound=600s; KILLED = status=FAIL rc=1, SURVIVED = status=OK rc=0):
```
[pyt] tag=b3adv-mut-M2 start=2026-10-20 07:52:01 end=2026-10-20 07:52:06 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M5 start=2026-10-20 07:52:06 end=2026-10-20 07:52:11 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M6b start=2026-10-20 07:52:12 end=2026-10-20 07:52:17 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M7a start=2026-10-20 07:52:17 end=2026-10-20 07:52:22 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M8 start=2026-10-20 07:52:23 end=2026-10-20 07:52:28 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M9 start=2026-10-20 07:52:29 end=2026-10-20 07:52:34 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M10 start=2026-10-20 07:52:34 end=2026-10-20 07:52:39 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M11a start=2026-10-20 07:52:40 end=2026-10-20 07:52:45 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M13b start=2026-10-20 07:52:45 end=2026-10-20 07:52:51 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M14 start=2026-10-20 07:52:51 end=2026-10-20 07:52:56 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M15b start=2026-10-20 07:52:56 end=2026-10-20 07:53:02 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M17b start=2026-10-20 07:53:02 end=2026-10-20 07:53:07 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M18 start=2026-10-20 07:53:07 end=2026-10-20 07:53:12 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M20b start=2026-10-20 07:53:13 end=2026-10-20 07:53:18 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M20c start=2026-10-20 07:53:18 end=2026-10-20 07:53:23 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M22a start=2026-10-20 07:53:23 end=2026-10-20 07:53:28 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M23 start=2026-10-20 07:53:28 end=2026-10-20 07:53:34 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M24 start=2026-10-20 07:53:34 end=2026-10-20 07:53:43 elapsed=9s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M26 start=2026-10-20 07:53:43 end=2026-10-20 07:53:49 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M27b start=2026-10-20 07:53:49 end=2026-10-20 07:53:55 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M28 start=2026-10-20 07:53:55 end=2026-10-20 07:54:00 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M29 start=2026-10-20 07:54:01 end=2026-10-20 07:54:06 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M30a start=2026-10-20 07:54:06 end=2026-10-20 07:54:11 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M33b start=2026-10-20 07:54:12 end=2026-10-20 07:54:17 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M42 start=2026-10-20 07:54:18 end=2026-10-20 07:54:26 elapsed=9s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M31 start=2026-10-20 07:54:27 end=2026-10-20 07:54:34 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-XB1 start=2026-10-20 07:54:34 end=2026-10-20 07:54:38 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-XB2 start=2026-10-20 07:54:39 end=2026-10-20 07:54:43 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-XB3 start=2026-10-20 07:54:44 end=2026-10-20 07:54:48 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-Y1 start=2026-10-20 07:54:48 end=2026-10-20 07:54:52 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-Y2 start=2026-10-20 07:54:53 end=2026-10-20 07:54:57 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-Y3 start=2026-10-20 07:54:58 end=2026-10-20 07:55:03 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-Y4 start=2026-10-20 07:55:04 end=2026-10-20 07:55:09 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M44b start=2026-10-20 07:55:44 end=2026-10-20 07:55:49 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M1 start=2026-10-20 07:55:49 end=2026-10-20 07:55:55 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M3 start=2026-10-20 07:55:55 end=2026-10-20 07:56:00 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M4 start=2026-10-20 07:56:00 end=2026-10-20 07:56:09 elapsed=9s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M12 start=2026-10-20 07:56:10 end=2026-10-20 07:56:15 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M16b start=2026-10-20 07:56:15 end=2026-10-20 07:56:21 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M19b start=2026-10-20 07:56:21 end=2026-10-20 07:56:26 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M21 start=2026-10-20 07:56:26 end=2026-10-20 07:56:32 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M25a start=2026-10-20 07:56:32 end=2026-10-20 07:56:37 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M27c start=2026-10-20 07:56:38 end=2026-10-20 07:56:43 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M36 start=2026-10-20 07:56:43 end=2026-10-20 07:56:48 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M39 start=2026-10-20 07:56:48 end=2026-10-20 07:56:53 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-M45 start=2026-10-20 07:56:53 end=2026-10-20 07:56:58 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-XB1-probe start=2026-10-20 07:57:40 end=2026-10-20 07:57:46 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-XB2-probe start=2026-10-20 07:57:47 end=2026-10-20 07:57:52 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-XB3-probe start=2026-10-20 07:57:53 end=2026-10-20 07:57:59 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-Y1-probe start=2026-10-20 07:58:00 end=2026-10-20 07:58:08 elapsed=8s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-Y2-probe start=2026-10-20 07:58:08 end=2026-10-20 07:58:26 elapsed=17s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-Y3-probe start=2026-10-20 07:58:27 end=2026-10-20 07:58:38 elapsed=11s bound=600s status=FAIL rc=1
[pyt] tag=b3adv-mut-Z1 start=2026-10-20 08:03:26 end=2026-10-20 08:03:30 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-Z2 start=2026-10-20 08:03:30 end=2026-10-20 08:03:35 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=b3adv-mut-Z3 start=2026-10-20 08:03:36 end=2026-10-20 08:03:41 elapsed=5s bound=600s status=OK rc=0
```
No TIMEOUT. No pytest left running (every run foreground, one at a time).

## Counts

Unit file 105/105 OFF and ON. Spec mutants applied 39 (+ M44 skipped as a double match, retargeted M44b) -> 39 KILLED; hand block-moves 3 + extras 7 -> 1 killed by the unit file (Y4), 9 survivors on the unit file, 6 of them killed by my 12 probe nodes, 3 (Z1-Z3) need a prompt-text pin. Probes on GREEN bytes 12/12 green.

## Questions for the gate

- Q1 (min-1) Rewrite the HARD PRECONDITION as an off-route smoke or as "the first canary call is the smoke, unset on BadRequestError"?
- Q2 (min-2) Add a VISION_PROMPT_SHA_ON (or three rule substrings) pin now (a RED-file change: needs a ruling) or as a follow-up row?
- Q3 (min-3) State the two-photos-both-at-index-0 limit, or amend B3-R6(2) for the case where one paired index is empty?
- Q4 (min-5) Widen GREEN's Q2 (camera_vision env hygiene) to the route-pin files whose authed rows reach the real get_user_preferences under ON?
- Q5 (min-6..9) Fold the six behaviour probes (tests/test_zz_b3adv_probe.py, saved as <scratchpad>/B3_adv/test_zz_b3adv_probe.py.txt) into a follow-up pin file, or accept as stated gaps?

## NOT MEASURED

- The comm set and the full CI-order set (the engineering lens's duty); I ran the 21-file camera identity set (a CI-order superset for the camera route minus ci_gates / backend_cleanup / legal / tpm files) and the 4 remaining camera-path files flag ON.
- Live OpenAI behaviour (strict json_schema with image input, Arabic transliteration, index base) -- canary items.
- The stream twin at runtime (unreachable with vision products, see prove-nothing).

## Files written (all in <scratchpad>/B3_adv/ except the removed scratch worktree; pure ASCII, LF)

- correctness_REPORT.md (this file)
- notes.md, run.sh, mutate.py, probe_prompt.py, bytes_check.py, sha_before_mut.txt, mut_results.jsonl, logs/*.log, mut_logs/*.log, mut_backup/* (byte copies used for restore)
- test_zz_b3adv_probe.py.txt sha256 49c52d064092e4f4951170ac9df749f3a4f8d794bbc5fcba536db7f7c27fcadf (copy of the probe file that lived only in the removed scratch worktree)

## git status --short (real worktree sc-s80-b3, at the end)

(empty) -- HEAD 764d44162dd83563dc5c9aa930dcb9c192f35f89; RED sha 36b78a40...f15e unchanged.

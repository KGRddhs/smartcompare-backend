# B1 RED report: RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA)

Agent: b1-red (Fable, claude-fable-5-1). Window 2026-10-20 02:29 - 03:18 AST. Worktree
C:/Users/SynAckITPC/Documents/AI/sc-s80-b1 at 81df2b641454e0301cca51a3ba01bf8ef3d7e649 (HEAD == base before and after;
`git status --short` = only the two new test files; `git diff --stat` empty). Spec sha256
05d48e2cef8c17ca472e6cad9696fa582ac2ba37eedc2b823aeb74dc00289bd6 (101368 B); review sha256
9ecbdf3809133d0d636403605f929df93d3ef4d1fdd367193894977f9dd5a9c5 (23068 B). Rulings applied: RULINGS_BATCH1 Common G-1..G-4,
B1-R1..B1-R12; RULINGS_R0 R0-1/R0-2/R0-4/R0-5/R0-6/R0-7. Scratch worktree <scratchpad>/B1_scratch (detached at the base sha,
no node_modules, no .env) created 02:34 and removed 03:17 (`git worktree remove --force`; `git worktree list` shows no
B1_scratch; the directory is gone). No .env read, no production / Railway / Supabase / Sentry / network access; every leaf faked.
Notes: <scratchpad>/B1_red/notes.md. Measurement logs: <scratchpad>/B1_red/*.log, <scratchpad>/B1_red/mutants/,
<scratchpad>/B1_red/comm/. Prototype kept for GREEN as text only: <scratchpad>/B1_red/proto/result_gate.py +
<scratchpad>/B1_red/proto/prototype_tracked.diff (the scratch worktree itself is removed).

## Files written (the ONLY writes in the real worktree; pure ASCII, LF, 0 bytes > 127)

| file | sha256 | bytes |
|---|---|---|
| tests/test_s80_b1.py | 88130f327757d9e53feb47bbe877f9a065783b2e3a01f90c623360de46a35dfb | 59270 |
| tests/test_s80_b1_feedback.py | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 | 7874 |

No existing test or source file was edited. No .env, no secret value, no personal value; the synthetic Sentry DSN is built by
concatenation at run time; the JPEG bytes are `bytes([255, 216]) + bytes(64)`.

## Step 2: the four NOT-MEASURED files, each ALONE at base (G-3)

```
tests/test_sentry_channels_u8d.py          131 passed; [hermeticity] 131; [netguard] blocked 0
[pyt] tag=b1red-nm1-sentry-u8d start=2026-10-20 02:29:55 end=2026-10-20 02:30:08 elapsed=12s bound=600s status=OK rc=0
tests/test_retro_w1_1.py                    39 passed; [netguard] blocked 0
[pyt] tag=b1red-nm2-retro-w1-1 start=2026-10-20 02:30:27 end=2026-10-20 02:30:57 elapsed=30s bound=600s status=OK rc=0
tests/test_s71_u13_compare_auth_required.py 137 passed; [netguard] blocked 0
[pyt] tag=b1red-nm3-u13-auth start=2026-10-20 02:31:26 end=2026-10-20 02:31:54 elapsed=28s bound=600s status=OK rc=0
tests/test_paid_route_metering.py           21 passed; [netguard] blocked 2 attempt(s) from 2 node(s) (the ratchet baseline's
  `sentinel` class: test_camera_success_consumes_once_and_never_refunds, test_url_compare_saves_history_with_input_type_url,
  socket.create_connection neutralized.supabase.invalid:443)
[pyt] tag=b1red-nm4-metering start=2026-10-20 02:32:30 end=2026-10-20 02:32:34 elapsed=4s bound=600s status=OK rc=0
```

## Base measurements that set the RED expectations (scratch worktree, the base builder + the prototype's pure predicates)

```
[pyt] tag=b1red-probe start=2026-10-20 02:37:56 end=2026-10-20 02:38:00 elapsed=4s bound=600s status=OK rc=0   (probe_out.json)
[pyt] tag=b1red-probe2 start=2026-10-20 02:43:19 end=2026-10-20 02:43:22 elapsed=3s bound=600s status=OK rc=0  (the P1 digests, built twice, stable)
```
- The chokepoint pends every lane1 / w412 price lacking the exact-gate identity stamp (the google search url is a listing url):
  lane1 unstamped = coverage 3 (dims, ratings, specs), price section unavailable (grocery, iphone15, tomford) or partial
  (now_vs_solgar: the converted_usd Solgar price survives); stamped (price.name/brand/url/in_stock) = coverage 4 on grocery /
  now_vs_solgar / iphone15 (tomford stays 3: its product-0 price pends even stamped).
- w412 rows 12-14: partial_no_winner, reasons [no_evidence], identity medium, coverage 0, literal 1, section_status
  {specs unavailable, reviews available, pros_cons available, price unavailable}. Rows 15-19: supported, medium, coverage 1-2.
  Row 24 (partial post_gather): coverage 1 (reliability 65/90), supported. Row 26: coverage 2.
- FY25 fakes: rest_q_full / stream complete = supported, high, coverage 3 (price, ratings, specs; every dim ties), literal 2;
  rest_pair_full = supported, MEDIUM (brand '' on the explicit pair), coverage 3; the gather partial = coverage 1 (the stash's
  one real spec row on both sides) -> supported_result, partial_stage gather.
- classify_category_from_text: 'Samsung Galaxy S24 phone' -> electronics; 'Dior Sauvage eau de parfum' -> fragrances;
  'Casio G-Shock watch' -> other; 'Apple MacBook laptop' -> electronics.
- P1 base digests (sorted-key JSON, FY25 VOLATILE dropped): w412_12 31c07498...29f4, w412_15 c505b678...7be8, w412_24 (partial
  metadata) abaa208c...b8fc, lane1_grocery a96f6cf3...970f (the full values are literals in the test file).

## Step 4: the unit files at base (real worktree)

```
tests/test_s80_b1.py          run 1: 169 failed / 18 passed; 2 TypeError in the test's own stream-chunk check (str chunks
                              tested with a bytes needle) -> the helper _text() was fixed; no expectation changed
[pyt] tag=b1red-unit-base start=2026-10-20 02:49:38 end=2026-10-20 02:49:50 elapsed=12s bound=600s status=FAIL rc=1
tests/test_s80_b1.py          run 2: 167 failed / 20 passed; failure exception types: 167 AssertionError, 0 other
[pyt] tag=b1red-unit-base2 start=2026-10-20 02:51:08 end=2026-10-20 02:51:20 elapsed=12s bound=600s status=FAIL rc=1
tests/test_s80_b1_feedback.py 24 failed / 3 passed; 24 AssertionError, 0 other
[pyt] tag=b1red-unitfb-base start=2026-10-20 02:50:18 end=2026-10-20 02:50:22 elapsed=4s bound=600s status=FAIL rc=1
```
PIN rows green at base (20): p1 x5, p2 x2, p3 x2, p4 x2, p5a, p6, p7, p8, r18b x3 (zero entries, PIN-shaped), r20[absent],
r20[notdict]. Feedback PINs green at base (3): f5, f6, f7. Every other node is RED on an AssertionError (the module /
attribute is asserted through find_spec / getattr / inspect.signature, never imported at module top).
Failed node ids at base (167 + 24): the full list is the `FAILED` lines of <scratchpad>/B1_red/unit_base2.log and
unitfb_base.log; by test: r1 x11, r2 x11, r3 x9, r4 x9, r5 x8, r6, r7 x10, r8 x3, r9 x4, r9b x3, r10 x2, r10b, r11, r12,
r13 x5, r14, r15, r16, r17, r17b, r18, r19, r20[dict], r20b, r21 x21, r21b, r22, r23, p5 x42, p5b x3, p10, p11, p12, p13,
c9c, c9d x4, c9e; f1 x6, f2 x6, f3 x9, f4 x3.

## Step 5: prototype (scratch worktree; the spec's change list 1-10 applied with exact-anchor edits; CRLF kept)

```
ON  run 1 (ENABLE_RESULT_STATUS_METADATA=true exported on the runner call): 213 passed / 1 failed
    (R15: the explicit pair carries the keyword-stub per-product categories ['other','other'], not electronics -> test corrected)
[pyt] tag=b1red-proto-on start=2026-10-20 02:54:49 end=2026-10-20 02:54:57 elapsed=9s bound=600s status=FAIL rc=1
ON  run 2: 214 passed
[pyt] tag=b1red-proto-on2 start=2026-10-20 02:56:42 end=2026-10-20 02:56:51 elapsed=9s bound=600s status=OK rc=0
OFF (flag unset on the runner call): 214 passed (PIN rows green, P1 digests equal, FY25 digests equal, zero messages)
[pyt] tag=b1red-proto-off start=2026-10-20 02:56:52 end=2026-10-20 02:57:00 elapsed=9s bound=600s status=OK rc=0
```
Prototype notes for GREEN: the spec is implementable as written with these amendments: (a) `is_placeholder_identity` must
compare `norm(text)` against the NORMALISED placeholder set (the literal `"n/a"` is never equal to `norm("n/a") == "n a"`);
(b) the variant / size / distinguishing_features veto applies to BOTH same_identity arms (the spec's own R3 row needs it on
the identity-equality arm); (c) `price_is_present_literal` needs a numeric non-bool amount (`{"amount": True}` -> False);
(d) `telemetry_extras(vision_ms, compare_ms)` is a new pure helper (B1-R10): the tags carry the bucket's lower edge in ms as
a digit string (vision 1000-ms steps, compare 5000-ms steps), the raw ints ride `extras`; (e) the sampler's OFF branch reads
`sentry_sdk.get_client().options.get("traces_sample_rate")` and falls back to 0.1 (B1-R1); (f) the camera emitter is gated on
`result.get("success") is True` (B1-R6) and the stream emitter on `complete_response.get("success") is True` inside the
M18 gate; (g) the builder stamp block sits between `result["tier_context"]` and `_strip_inference_markers(result)`, wrapped in
try/except with ONE WARNING `[RESULT_STATUS] assess failed: <TypeName>`; (h) scs captures `product_categories` immediately
before BOTH write-back loops (REST before the `_partial_build_ctx.update`, stream before the dict literal) and passes it to
the three builds. Flag OFF the prototype is byte-identical on every measured body (P1 x4 digests, the nine FY25 digests).

## Step 6: mutation table (byte copy, exact-string edit matching once, pyt.py -k, restore, sha256 equal; lock held)

35 mutants applied, 35 KILLED, every restore sha-equal; X19 NOT MEASURED (a block move with no exact-string form; see
open questions). The killing rows and the [pyt] line of every mutant follow (also <scratchpad>/B1_red/mutant_table.txt and
<scratchpad>/B1_red/mutants/results_*.json):

X18 | product_categories captured AFTER the write-back (REST) | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r16_orchestrator_vision_pair_product_categories | [pyt] tag=b1red-mut-X18 start=2026-10-20 03:00:42 end=2026-10-20 03:00:46 elapsed=4s bound=600s status=FAIL rc=1
X20 | telemetry emitted with the flag OFF | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p4_flag_off_no_message_on_any_exit[0]; tests/test_s80_b1.py::test_b1_p4_flag_off_no_message_on_any_exit[None] | [pyt] tag=b1red-mut-X20 start=2026-10-20 03:00:47 end=2026-10-20 03:00:51 elapsed=5s bound=600s status=FAIL rc=1
X21 | telemetry tags carry the query | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r10b_v09_shape_reasons_exact; tests/test_s80_b1.py::test_b1_r17_telemetry_text_post_get_stream | [pyt] tag=b1red-mut-X21 start=2026-10-20 03:00:52 end=2026-10-20 03:00:56 elapsed=5s bound=600s status=FAIL rc=1
X22 | telemetry on the camera unsuccessful path | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r18b_telemetry_camera_unsuccessful_emits_nothing[None-None] | [pyt] tag=b1red-mut-X22 start=2026-10-20 03:00:56 end=2026-10-20 03:01:01 elapsed=5s bound=600s status=FAIL rc=1
X23 | telemetry outside the stream gate | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r19_telemetry_stream_client_gone_emits_nothing | [pyt] tag=b1red-mut-X23 start=2026-10-20 03:01:01 end=2026-10-20 03:01:06 elapsed=5s bound=600s status=FAIL rc=1
X24 | camera timings written with the flag OFF | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p3_flag_off_camera_timings_untouched[None]; tests/test_s80_b1.py::test_b1_p3_flag_off_camera_timings_untouched[false] | [pyt] tag=b1red-mut-X24 start=2026-10-20 03:01:06 end=2026-10-20 03:01:11 elapsed=5s bound=600s status=FAIL rc=1
X25 | camera timings create the dict when absent | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r20_camera_timings_written_only_into_existing_dict[absent]; tests/test_s80_b1.py::test_b1_r20_camera_timings_written_only_into_existing_dict[notdict] | [pyt] tag=b1red-mut-X25 start=2026-10-20 03:01:11 end=2026-10-20 03:01:15 elapsed=5s bound=600s status=FAIL rc=1
X26 | sampler returns 1.0 with the flag OFF | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p5_flag_off_sampler_is_the_sdk_rule[None-False-/api/v1/image/identify]; tests/test_s80_b1.py::test_b1_p5_flag_off_sampler_is_the_sdk_rule[None-False-/api/v1/text/compare/stream]; tests/test_s80_b1.py::test_b1_p5_flag_off_sampler_is_the_sdk_rule[None-False-/api/v1/text/compare] | [pyt] tag=b1red-mut-X26 start=2026-10-20 03:01:16 end=2026-10-20 03:01:21 elapsed=5s bound=600s status=FAIL rc=1
X27 | sampler path set lacks the stream | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r21_sampler_flag_on_compare_paths[False-/api/v1/text/compare/stream]; tests/test_s80_b1.py::test_b1_r21_sampler_flag_on_compare_paths[None-/api/v1/text/compare/stream] | [pyt] tag=b1red-mut-X27 start=2026-10-20 03:01:21 end=2026-10-20 03:01:25 elapsed=4s bound=600s status=FAIL rc=1
X28 | sampler ignores parent_sampled OFF | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p5_flag_off_sampler_is_the_sdk_rule[None-False-/api/v1/comparisons/history]; tests/test_s80_b1.py::test_b1_p5_flag_off_sampler_is_the_sdk_rule[None-False-/api/v1/health]; tests/test_s80_b1.py::test_b1_p5_flag_off_sampler_is_the_sdk_rule[None-False-/api/v1/image/identify] | [pyt] tag=b1red-mut-X28 start=2026-10-20 03:01:25 end=2026-10-20 03:01:31 elapsed=5s bound=600s status=FAIL rc=1
X29 | init_sentry drops traces_sample_rate | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p5a_init_sentry_kwargs_kept; tests/test_s80_b1.py::test_b1_r21b_init_sentry_installs_the_sampler | [pyt] tag=b1red-mut-X29 start=2026-10-20 03:01:31 end=2026-10-20 03:01:36 elapsed=5s bound=600s status=FAIL rc=1
X30 | home skip keyed on winner_index is None | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r22_home_savings_skips_stamped_non_supported_rows | [pyt] tag=b1red-mut-X30 start=2026-10-20 03:01:36 end=2026-10-20 03:01:41 elapsed=5s bound=600s status=FAIL rc=1
X31 | home skip when result_status is ABSENT | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p8_home_savings_unstamped_rows_count_as_today | [pyt] tag=b1red-mut-X31 start=2026-10-20 03:01:41 end=2026-10-20 03:01:46 elapsed=5s bound=600s status=FAIL rc=1
X32 | FeedbackRequest field typed Optional[str] | KILLED | killed_by: tests/test_s80_b1_feedback.py::test_b1_f4_off_enum_value_422s[maybe] | [pyt] tag=b1red-mut-X32 start=2026-10-20 03:01:46 end=2026-10-20 03:01:51 elapsed=4s bound=600s status=FAIL rc=1
X33 | save_feedback writes the key when None | KILLED | killed_by: tests/test_s80_b1_feedback.py::test_b1_f5_four_field_body_record_identical | [pyt] tag=b1red-mut-X33 start=2026-10-20 03:01:51 end=2026-10-20 03:01:55 elapsed=4s bound=600s status=FAIL rc=1
X34 | one allowlist name misspelled | KILLED | killed_by: tests/test_s80_b1_feedback.py::test_b1_f1_new_mattered_most_values_accepted[unsure] | [pyt] tag=b1red-mut-X34 start=2026-10-20 03:01:56 end=2026-10-20 03:02:00 elapsed=4s bound=600s status=FAIL rc=1
X35 | assess_result raise not caught in the builder | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p13_stamp_failure_degrades_to_flag_off | [pyt] tag=b1red-mut-X35 start=2026-10-20 03:02:00 end=2026-10-20 03:02:05 elapsed=5s bound=600s status=FAIL rc=1
X1 | flag default true | KILLED | killed_by: tests/test_s80_b1.py::test_b1_p1_flag_off_builder_bodies_identical[None]; tests/test_s80_b1.py::test_b1_p2_flag_off_orchestrator_digests_unchanged[None]; tests/test_s80_b1.py::test_b1_p3_flag_off_camera_timings_untouched[None] | [pyt] tag=b1red-mut-X1 start=2026-10-20 02:58:51 end=2026-10-20 02:58:58 elapsed=7s bound=600s status=FAIL rc=1
X2 | flag read once at import | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r1_flag_reader_per_call[ TRUE -True]; tests/test_s80_b1.py::test_b1_r1_flag_reader_per_call[-False]; tests/test_s80_b1.py::test_b1_r1_flag_reader_per_call[0-False] | [pyt] tag=b1red-mut-X2 start=2026-10-20 02:58:58 end=2026-10-20 02:59:02 elapsed=5s bound=600s status=FAIL rc=1
X3 | reader drops on | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r1_flag_reader_per_call[on-True] | [pyt] tag=b1red-mut-X3 start=2026-10-20 02:59:03 end=2026-10-20 02:59:07 elapsed=4s bound=600s status=FAIL rc=1
X4 | placeholder on brand alone | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r13_builder_june_rows_brand_empty_supported[15]; tests/test_s80_b1.py::test_b1_r13_builder_june_rows_brand_empty_supported[16]; tests/test_s80_b1.py::test_b1_r13_builder_june_rows_brand_empty_supported[17] | [pyt] tag=b1red-mut-X4 start=2026-10-20 02:59:07 end=2026-10-20 02:59:12 elapsed=4s bound=600s status=FAIL rc=1
X5 | same_identity ignores the brand | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r3_same_identity[p03-p13-False]; tests/test_s80_b1.py::test_b1_r3_same_identity[p04-p14-False]; tests/test_s80_b1.py::test_b1_r9_builder_stamps_lane1_supported[grocery] | [pyt] tag=b1red-mut-X5 start=2026-10-20 02:59:12 end=2026-10-20 02:59:17 elapsed=4s bound=600s status=FAIL rc=1
X6 | Jaccard threshold 0.5 | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r3_same_identity[p05-p15-False] | [pyt] tag=b1red-mut-X6 start=2026-10-20 02:59:17 end=2026-10-20 02:59:21 elapsed=4s bound=600s status=FAIL rc=1
X7 | coherence treats other as a conflict | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r12_builder_category_conflict; tests/test_s80_b1.py::test_b1_r4_identity_coherence[cats1-True] | [pyt] tag=b1red-mut-X7 start=2026-10-20 02:59:21 end=2026-10-20 02:59:26 elapsed=4s bound=600s status=FAIL rc=1
X8 | price_is_showable accepts estimated | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r5_price_facts[price0-False-False] | [pyt] tag=b1red-mut-X8 start=2026-10-20 02:59:26 end=2026-10-20 02:59:30 elapsed=4s bound=600s status=FAIL rc=1
X9 | rating_is_real ignores rating_derived | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[12]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[13]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[14] | [pyt] tag=b1red-mut-X9 start=2026-10-20 02:59:31 end=2026-10-20 02:59:35 elapsed=4s bound=600s status=FAIL rc=1
X10 | real_spec_rows counts N/A | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r6_real_spec_rows_excludes_na_and_tier3; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[12]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[13] | [pyt] tag=b1red-mut-X10 start=2026-10-20 02:59:35 end=2026-10-20 02:59:40 elapsed=4s bound=600s status=FAIL rc=1
X10a | NA check through norm | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r6_real_spec_rows_excludes_na_and_tier3 | [pyt] tag=b1red-mut-X10a start=2026-10-20 02:59:40 end=2026-10-20 02:59:44 elapsed=4s bound=600s status=FAIL rc=1
X11 | ignores tier3 | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r6_real_spec_rows_excludes_na_and_tier3 | [pyt] tag=b1red-mut-X11 start=2026-10-20 02:59:45 end=2026-10-20 02:59:49 elapsed=4s bound=600s status=FAIL rc=1
X12 | dim drops the margin test | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r7_dim_facts[85-85-high-None-price-missing0-False-False]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[12]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[13] | [pyt] tag=b1red-mut-X12 start=2026-10-20 02:59:49 end=2026-10-20 02:59:53 elapsed=4s bound=600s status=FAIL rc=1
X13 | strict drops the sentinel / low checks | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r7_dim_facts[65.0-50-medium-None-function-missing3-True-False]; tests/test_s80_b1.py::test_b1_r7_dim_facts[88-82-low-None-reviews-missing4-True-False] | [pyt] tag=b1red-mut-X13 start=2026-10-20 02:59:54 end=2026-10-20 02:59:58 elapsed=4s bound=600s status=FAIL rc=1
X14 | supported when coverage 0 | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[12]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[13]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[14] | [pyt] tag=b1red-mut-X14 start=2026-10-20 02:59:58 end=2026-10-20 03:00:03 elapsed=4s bound=600s status=FAIL rc=1
X15 | winner_index None on every body | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r13_builder_june_rows_brand_empty_supported[15]; tests/test_s80_b1.py::test_b1_r13_builder_june_rows_brand_empty_supported[16]; tests/test_s80_b1.py::test_b1_r13_builder_june_rows_brand_empty_supported[17] | [pyt] tag=b1red-mut-X15 start=2026-10-20 03:00:03 end=2026-10-20 03:00:08 elapsed=5s bound=600s status=FAIL rc=1
X16 | supported always True | KILLED | killed_by: tests/test_s80_b1.py::test_b1_r10_builder_unknown_product_pair_needs_identification[brands0]; tests/test_s80_b1.py::test_b1_r10_builder_unknown_product_pair_needs_identification[brands1]; tests/test_s80_b1.py::test_b1_r8_builder_stamps_manama_partial_no_winner[12] | [pyt] tag=b1red-mut-X16 start=2026-10-20 03:00:08 end=2026-10-20 03:00:12 elapsed=4s bound=600s status=FAIL rc=1
X17 | section_status available on one side | KILLED | killed_by: tests/test_s80_b1.py::test_b1_c9e_section_status_partial_when_one_side_empty; tests/test_s80_b1.py::test_b1_r9_builder_stamps_lane1_supported[now_vs_solgar] | [pyt] tag=b1red-mut-X17 start=2026-10-20 03:00:13 end=2026-10-20 03:00:17 elapsed=4s bound=600s status=FAIL rc=1

## Step 7: comm set at base (real worktree)

List: <scratchpad>/B1_red/comm_files.txt (293 entries = 288 unique files; 5 slash-variant duplicates ran twice:
test_ci_gates, test_prompt_fence, test_s80_b1, test_s80_b1_feedback, test_sentry_channels_u8d_unit); reasons per file:
<scratchpad>/B1_red/comm_reasons.tsv (module-ref 270 for structured_comparison_service / response_builder / result_gate /
image_routes / text_routes / url_routes / home_routes / history_routes / feedback_routes / feedback_service / sentry_service;
source-scanning pins 8; CLAUDE.md readers 2; SmartCompareApp scanners 23; the two new unit files; the 2
test_precommit_hook*.py files excluded; the 4 NETWORK_FLAKY_EXCLUDE node ids deselected on every chunk). 12 chunks of at most
25 files, bound 1200 each, one process at a time:

chunk00 (25 files): non-unit failures 0, unit RED rows 191
[pyt] tag=b1red-comm-00 start=2026-10-20 03:02:33 end=2026-10-20 03:03:25 elapsed=52s bound=1200s status=FAIL rc=1
chunk01 (25 files): non-unit failures 3, unit RED rows 0
[pyt] tag=b1red-comm-01 start=2026-10-20 03:03:25 end=2026-10-20 03:04:25 elapsed=59s bound=1200s status=FAIL rc=1
chunk02 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-02 start=2026-10-20 03:04:25 end=2026-10-20 03:04:50 elapsed=25s bound=1200s status=OK rc=0
chunk03 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-03 start=2026-10-20 03:05:37 end=2026-10-20 03:06:20 elapsed=43s bound=1200s status=OK rc=0
chunk04 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-04 start=2026-10-20 03:06:20 end=2026-10-20 03:07:02 elapsed=42s bound=1200s status=OK rc=0
chunk05 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-05 start=2026-10-20 03:07:02 end=2026-10-20 03:07:18 elapsed=16s bound=1200s status=OK rc=0
chunk06 (25 files): non-unit failures 4, unit RED rows 0
[pyt] tag=b1red-comm-06 start=2026-10-20 03:07:33 end=2026-10-20 03:08:05 elapsed=32s bound=1200s status=FAIL rc=1
chunk07 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-07 start=2026-10-20 03:08:06 end=2026-10-20 03:09:35 elapsed=90s bound=1200s status=OK rc=0
chunk08 (25 files): non-unit failures 0, unit RED rows 191
[pyt] tag=b1red-comm-08 start=2026-10-20 03:09:36 end=2026-10-20 03:11:22 elapsed=106s bound=1200s status=FAIL rc=1
chunk09 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-09 start=2026-10-20 03:11:40 end=2026-10-20 03:12:44 elapsed=64s bound=1200s status=OK rc=0
chunk10 (25 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-10 start=2026-10-20 03:12:44 end=2026-10-20 03:13:48 elapsed=65s bound=1200s status=OK rc=0
chunk11 (18 files): non-unit failures 0, unit RED rows 0
[pyt] tag=b1red-comm-11 start=2026-10-20 03:13:49 end=2026-10-20 03:14:10 elapsed=21s bound=1200s status=OK rc=0

Failures outside the unit's own RED rows (7 node ids, every one in tests/.pre_impl_failures.txt at base):
tests/test_camera_vision.py::TestIdentifyProductsMocked::{test_empty_product_fields_normalized,
test_malformed_response_returns_error, test_successful_identification}; tests/test_page_scraping.py::TestFetchPagePriceJsonLD::
test_jsonld_nested_offers_picks_lowest; tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction;
tests/test_personalization_bundle_c.py::{test_applied_shifts_list_is_default_empty_when_no_priorities,
test_full_response_payload_audit_no_magnitude_keys}. The two tests/test_prompt_truth.py tiktoken ERRORs did not occur
(warm cache). The unit's RED rows failed in chunks 00 and 08 (191 lines each = 167 + 24, the duplicate entry).

## Step 8: restore check

`git status --short` in sc-s80-b1 = `?? tests/test_s80_b1.py`, `?? tests/test_s80_b1_feedback.py` only; `git diff --stat`
empty (no tracked file touched); HEAD 81df2b641454e0301cca51a3ba01bf8ef3d7e649. Scratch worktree removed; `git worktree list`
has no B1_scratch; no `.qa-mutation.lock` left (the driver removed it); pytest processes alive after the last run: 0.

## Deviations from the spec (each measured, none silently applied to a spec file)

1. R15 `metadata.product_categories` on the EXPLICIT-PAIR path is `["other", "other"]` (the keyword stubs for brand-only
   names), not `["electronics", "electronics"]`; the parser path (q) and the stream carry the LLM per-product category.
   The test asserts the measured values per path.
2. R15 `identity_confidence`: rest_pair_full = `medium` (brand '' on the explicit pair); q / stream = `high`.
3. R15 gather partial: coverage 1 -> `supported_result` (the stash spec row), as the spec's own fallback sentence anticipated.
4. R3 `100ml vs 50ml -> False` requires the axis veto on the identity-equality arm too (spec 2.2 placed it on the
   brand+Jaccard arm only).
5. R2 `("", "n/a") -> True` requires the placeholder set to be compared after `norm` on both sides.
6. R5 `{"amount": True} -> literal False` requires a numeric non-bool amount in `price_is_present_literal`.
7. R9 lane1 unstamped: coverage 3 with the price section unavailable (grocery / iphone15 / tomford) or partial (now_vs_solgar);
   the B1-R5 stamped variant (r9b) reaches 4 on grocery / now_vs_solgar / iphone15 only.
8. R13 rows 15-19: `supported_result`, `medium`, coverage >= 1 (B1-R5).
9. R19 carries a positive half (one message when the client is present) and is therefore RED at base, not PIN-shaped.
10. P5 / P5b assert the sampler exists and are RED at base (the spec's split keeps only P5a green at base).
11. B1-R10 representation: the `vision_ms` / `compare_ms` TAGS carry the bucket's lower edge in ms as a digit string
    (1000 / 5000 ms steps); the raw ints ride `extras` under the same keys (`telemetry_extras`, a new helper).
12. P4's body-equality half (recorder present vs absent) is not implemented; P4 asserts zero entries and no stamp on all five
    exits (the byte identity is P1 / P2 / P3's job).
13. X19 (stamp before the chokepoint) NOT MEASURED.
14. The stream exits (R17 third leg, R19, P4) are driven by a direct `text_compare_stream` call with a fake request (the
    W4-13 idiom), not through TestClient.

## Open questions for the gate

1. Accept deviation 1 as the measured contract (the explicit-pair path cannot fire B2's cross-category rule on brand-only
   names; only a parser-path or vision pair carrying category words can)?
2. B1-R10: is the lower-edge-in-ms digit string an acceptable bucket label, or should GREEN emit a labelled enum
   (e.g. `5s_10s`) with the test's grammar check unchanged?
3. R19: keep the positive half (RED) or revert to the spec's PIN-only shape?
4. X19: accept NOT MEASURED, or have GREEN's adversary apply the block move by hand?
5. The five duplicate entries of the comm list are slash variants of the same files; the orchestrator's `scripts/comm_set.py`
   at GREEN will dedupe them (the entries ran twice here, harmlessly).

## NOT MEASURED

- Mutant X19 (the stamp block placed before the chokepoint).
- The spec 1.10 NOT-MEASURED files other than the four named in the task (tests/test_w4_13_measurement_truth.py,
  tests/test_comparison_id_echo.py, tests/test_camera_vision.py, tests/test_image_routes*.py, tests/test_url_*) ran inside the
  comm chunks at base, not alone.
- Flag-ON smoke of the 1.10 files (spec gate step 4) was not run (GREEN's step).

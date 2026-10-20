# B3 RED REPORT: VISION-IDENTITY-V2 (ENABLE_VISION_IDENTITY_V2)

- Unit B3, flag ENABLE_VISION_IDENTITY_V2. Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s80-b3, base 81df2b641454e0301cca51a3ba01bf8ef3d7e649 (HEAD verified before and after).
- Agent: B3 RED (session 80). Window 2026-10-20 05:40 -> 06:30 AST. Notes and every artifact: <scratchpad>/B3red/ (notes.md, logs, mutation_results.jsonl, mut_logs/, comm_logs/, prototype_diff_ascii.txt).
- Inputs read in full: s80-common.txt, PLAN_S80.md sections 0-1, RULINGS_R0.md, RULINGS_BATCH1.md (Common G-1..G-4, B3-R1..B3-R7), .qa-s80/B3_UNIT_SPEC.md, .qa-s80/B3_SPEC_REVIEW.md. Precedence applied: rulings > review corrections > spec.
- Only file written in the real worktree: tests/test_s80_b3_vision_identity_v2.py (untracked; pure ASCII, LF, 65,236 B, sha256 36b78a404deefbc4fbea66b2d75574f203346a8e53550a3ddf04d3550e4af15e). No existing test or source file was edited there; no git write command was run in it.
- No .env read, no secret printed, no network; the dummy key is built by concatenation ("sk-" + "b3-unit-dummy-key"); no personal values (product strings only, synthetic user ids "b3-<node>").

## 1. Step 2: the review's NOT-MEASURED files, each alone at base (ruling G-3)

```
tests/test_s71_u13_compare_auth_required.py  137 passed, 11 warnings in 5.71s; [hermeticity] sentinel checked 137; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-base-u13 start=2026-10-20 05:40:58 end=2026-10-20 05:41:05 elapsed=7s bound=600s status=OK rc=0
tests/test_prompt_fence.py  61 passed, 1 warning in 3.69s; [hermeticity] 61; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-base-prompt-fence start=2026-10-20 05:41:12 end=2026-10-20 05:41:17 elapsed=5s bound=600s status=OK rc=0
tests/test_model_config.py  37 passed, 1 warning in 1.82s; [hermeticity] 37; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-base-model-config start=2026-10-20 05:41:24 end=2026-10-20 05:41:27 elapsed=3s bound=600s status=OK rc=0
tests/test_ci_gates.py  52 passed, 1 warning in 6.06s; [hermeticity] 52; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-base-ci-gates start=2026-10-20 05:41:33 end=2026-10-20 05:41:40 elapsed=7s bound=600s status=OK rc=0
tests/test_backend_cleanup.py  18 passed, 21 warnings in 14.56s; [hermeticity] 18; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-base-backend-cleanup start=2026-10-20 05:41:51 end=2026-10-20 05:42:11 elapsed=20s bound=600s status=OK rc=0
tests/test_m18_openai_tpm_sizing.py  11 passed, 1 warning in 2.30s; [hermeticity] 11; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-base-m18-tpm start=2026-10-20 05:42:21 end=2026-10-20 05:42:26 elapsed=6s bound=600s status=OK rc=0
```

## 2. Step 4: the unit file at base (final bytes)

```
69 failed, 36 passed, 10 warnings in 9.01s; [hermeticity] sentinel checked 105 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3red-unit-base-final start=2026-10-20 06:14:51 end=2026-10-20 06:15:01 elapsed=10s bound=600s status=FAIL rc=1
```
Earlier iterations of the same file (before R17 arm f and the R9 .get hardening): `[pyt] tag=b3red-unit-base-1 ... elapsed=10s status=FAIL rc=1` and `[pyt] tag=b3red-unit-base-2 start=2026-10-20 05:52:47 end=2026-10-20 05:52:58 elapsed=12s bound=600s status=FAIL rc=1` (68 failed / 36 passed).

Every one of the 69 failures is an AssertionError: checked through --junitxml (every failure's E-lines carry AssertionError or a rewritten `assert`), and `grep -E "^E +(KeyError|IndexError|AttributeError|TypeError|ImportError|NameError|Failed)"` over the log = 0. Zero collection errors. The failed node list: <scratchpad>/B3red/unit_base_final_failed.txt.

RED nodes (69): R1, R2, R3, R4[refusal|none|no_choice], R4b, R5, R5b, R6, R6b, R7, R7b, R8, R8c, R8d, R8b, R9, R10, R10b, R11 x11, R12 x15, R13 x5, R14, R15, R16, R16b x3, R17 x6 (a_on_delivery, b_off_delivery, c_need_second, d_comparison_failed, e_envelope, f_envelope_meter_off), R18, R19, R20, R21, R22, R23.
PIN nodes green at base (36): P1 x7, P2 x7, P3, P3b, P10, P4/P5 x3 (flag true / unset / false), R16c (PIN-ON, anonymous), P6 x2, P7 x6, P8 x7.

## 3. Step 5: prototype (detached scratch worktree <scratchpad>/B3red/b3_scratch @81df2b64, now removed)

Prototype = spec change list items 1-7 as amended (proto_apply.py; diff kept as prototype_diff_ascii.txt, non-ASCII base text escaped). It includes the GREEN pin changes E1-E5 (SimpleNamespace fixture in test_camera_vision.py, the 3-row prune of .pre_impl_failures.txt, the regenerated mirror (gen_baseline_mirror wrote 8 nodes; --check OK), the flag in the four clear-lists).

```
unit file, flag unset in env:  104 passed  [pyt] tag=b3red-proto-off start=2026-10-20 05:56:56 end=2026-10-20 05:57:06 elapsed=10s bound=600s status=OK rc=0
unit file, ENABLE_VISION_IDENTITY_V2=true exported for the runner only: 104 passed  [pyt] tag=b3red-proto-on start=2026-10-20 05:57:22 end=2026-10-20 05:57:27 elapsed=5s bound=600s status=OK rc=0
CI-order pin set (27 files incl. the unit file): 1 failed, 1296 passed, 1 deselected  [pyt] tag=b3red-proto-ciorder start=2026-10-20 05:57:42 end=2026-10-20 05:58:39 elapsed=57s bound=1200s status=FAIL rc=1
   FAILED tests/test_ci_gates.py::test_baseline_count_is_rederivable_from_the_committed_file  (spec trap, deviation D1 below; fixed in the prototype)
test_camera_vision.py + test_ci_gates.py after the wording fix: 77 passed, 1 deselected (camera_vision 25 passed + 1 live deselected = the E1-E3 pass proof)
   [pyt] tag=b3red-proto-cigates-camera start=2026-10-20 05:59:20 end=2026-10-20 05:59:26 elapsed=6s bound=600s status=OK rc=0
unit file + R17 arm f: 105 passed  [pyt] tag=b3red-proto-off-2 start=2026-10-20 06:02:40 end=2026-10-20 06:02:47 elapsed=7s bound=600s status=OK rc=0
FINAL bytes OFF: 105 passed, [hermeticity] 105, [netguard] blocked 0  [pyt] tag=b3red-proto-off-final start=2026-10-20 06:13:32 end=2026-10-20 06:13:49 elapsed=17s bound=600s status=OK rc=0
FINAL bytes ON:  105 passed, [hermeticity] 105, [netguard] blocked 0  [pyt] tag=b3red-proto-on-final start=2026-10-20 06:13:50 end=2026-10-20 06:14:15 elapsed=24s bound=600s status=OK rc=0
```
The CI-order set on the prototype (27 files: b2_strict_optional_auth, backend_cleanup, camera_vision, ci_gates, comparison_id_echo, cost_meter_s74, image_identify_llm_unavailable_s69, legal_docs_u8, logger_no_query_leak, m13_03, m13_26, m18_tpm, model_config, model_config_enforced (M1 site count 16 tolerated), openai_key_log_hygiene_s69, paid_route_metering, prompt_fence, retro_w2_1, s71_u13 (T23 unchanged), the unit file, security_regression, sentry_channels_u8d_unit, shutdown_drain, text_error_envelope_no_raw_exception, u3c_store_false_pin, w4_13 ledger + truth) was otherwise green: the spec's design is satisfiable without moving any other pin.

## 4. Step 6: mutation table (70 mutants, byte copies of the prototype, exact-string edits, unit file through pyt.py bound 600 each; restore from the byte copy + sha256 compare after every mutant; lock file <scratch>/.qa-mutation.lock held for the run)

Result: 70 / 70 KILLED, 70 / 70 restores sha-verified, 0 equivalent survivors. Full [pyt] lines per mutant: mutation_results.jsonl and mut_logs/b3red-mut-<id>.log. Spec mutants M1-M35 are covered (M1-M30 as listed, with the rulings' amendments); M41/M43 numbers unused; M36-M48 and M20e are added for the review corrections and the rulings.

| # | mutant | file | killed by (failing nodes, abbreviated) | result | restore sha | [pyt] |
|---|---|---|---|---|---|---|
| M1 | flag check removed (always V2) | openai_service.py | P10, P1 x7, P2 x7, P3, P3b | KILLED | ok | elapsed=14s status=FAIL rc=1 |
| M2 | reader without strip/lower | openai_service.py | R12[ true ], R12[ON], R12[TRUE] | KILLED | ok | elapsed=7s status=FAIL rc=1 |
| M3 | knob read before the flag check | openai_service.py | P1 x7, P2 x7, R10 (knob read twice) (15) | KILLED | ok | elapsed=8s status=FAIL rc=1 |
| M4 | wait_for unbounded | openai_service.py | R10, R10b | KILLED | ok | elapsed=10s status=FAIL rc=1 |
| M5 | knob accepts inf/nan/<=0 | openai_service.py | R11['-3','0','1e400','inf','nan'] | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M6a | response_format dropped | openai_service.py | R3 | KILLED | ok | elapsed=8s status=FAIL rc=1 |
| M6b | strict False | openai_service.py | R3 | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M6c | category enum-with-null (pre-ruling-4 form) | openai_service.py | R3 | KILLED | ok | elapsed=8s status=FAIL rc=1 |
| M6d | a required key missing | openai_service.py | R3 | KILLED | ok | elapsed=7s status=FAIL rc=1 |
| M7a | V2 prompt keeps WITHOUT packaging | openai_service.py | R3 | KILLED | ok | elapsed=7s status=FAIL rc=1 |
| M7b | V2 prompt lacks the enumeration | openai_service.py | R3 | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M8 | None content returns the parse-failure dict | openai_service.py | R4 x3, R4b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M9 | bare RuntimeError | openai_service.py | R4 x3, R4b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M10 | finish_reason length parsed anyway | openai_service.py | R5, R5b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M11a | object shape rejected | openai_service.py | R1, R6, R6b, R7, R7b, R8d, R9, R18, R20 | KILLED | ok | elapsed=7s status=FAIL rc=1 |
| M11b | bare array rejected | openai_service.py | R2, R8, R8b, R8c, R19, R22 | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M12 | per-index dedupe removed | openai_service.py | R6, R6b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M13a | best pick = last | openai_service.py | R6, R6b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M13b | best pick = lowest confidence | openai_service.py | R6, R6b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M13c | best pick = first in reply order | openai_service.py | R6, R6b | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M14 | is_product false kept | openai_service.py | R7, R7b | KILLED | ok | elapsed=6s status=FAIL rc=1 |
| M15a | range check dropped | openai_service.py | R8, R8d | KILLED | ok | elapsed=8s status=FAIL rc=1 |
| M15b | bool index accepted | openai_service.py | R8 | KILLED | ok | elapsed=8s status=FAIL rc=1 |
| M15c | str index accepted | openai_service.py | R8c | KILLED | ok | elapsed=5s status=FAIL rc=1 |
| M15d | unpaired DROPPED (pre-ruling-3 rule) | openai_service.py | R8, R8c, R8d | KILLED | ok | see jsonl |
| M15e | unpaired placed first | openai_service.py | R8, R8c, R8d | KILLED | ok | see jsonl |
| M16a | confidence not lower-stripped | openai_service.py | R9 | KILLED | ok | see jsonl |
| M16b | unknown confidence -> medium | openai_service.py | R9 | KILLED | ok | see jsonl |
| M17a | category not canonicalised | openai_service.py | R9 | KILLED | ok | see jsonl |
| M17b | empty category -> other | openai_service.py | R9 | KILLED | ok | see jsonl |
| M18 | missing is_product -> False | openai_service.py | R9 | KILLED | ok | see jsonl |
| M19a | public key renamed | openai_service.py | R1, R2, R7b (assertions); R9 also hit a KeyError before its .get hardening (now .get) | KILLED | ok | see jsonl |
| M19b | internal key without underscore | openai_service.py | R1, R2, R7b, R9, R18, R20 | KILLED | ok | see jsonl |
| M20a | strip removed at need_second_product | image_routes.py | R17[c_need_second], R7b | KILLED | ok | see jsonl |
| M20b | strip removed at metadata injection | image_routes.py | R17[a], R17[b], R18, R19, R20 | KILLED | ok | see jsonl |
| M20c | strip removed at comparison_failed | image_routes.py | R17[d] | KILLED | ok | see jsonl |
| M20d | strip removed at the envelope (metering ON site) | image_routes.py | R17[e] | KILLED | ok | see jsonl |
| M20e | strip removed at the envelope (metering OFF + envelope ON site) | image_routes.py | R17[f] | KILLED | ok | see jsonl |
| M21 | strip applied INTO compare_from_text | image_routes.py | R17[a,b,d,e,f], R18, R19, R20 | KILLED | ok | see jsonl |
| M22a | user_preferences=None forwarded | image_routes.py | R16b x3 | KILLED | ok | see jsonl |
| M22b | user_id=None forwarded (anonymous) | image_routes.py | R16c | KILLED | ok | see jsonl |
| M23 | forwarding / prefs read regardless of the flag | image_routes.py | P6 x2 | KILLED | ok | see jsonl |
| M24 | prefs forwarded when not completed | image_routes.py | R16b[not_completed] | KILLED | ok | see jsonl |
| M25a | raising prefs read propagates | image_routes.py | R16b[raises], P8[route_v01,route_v04,route_v07] | KILLED | ok | see jsonl |
| M25b | prefs WARNING logs str(e) | image_routes.py | R16b[raises] | KILLED | ok | see jsonl |
| M26 | _vision_identity_fields not presence-gated | structured_comparison_service.py | P4/P5 x3, R13[v1] | KILLED | ok | see jsonl |
| M27a | _vision_category dropped | structured_comparison_service.py | R13[v2], R13[v2_unpaired_none_feats], R14 | KILLED | ok | see jsonl |
| M27b | features copied by reference | structured_comparison_service.py | R13[v2] | KILLED | ok | see jsonl |
| M27c | _vision_image_index not carried (ruling 11) | structured_comparison_service.py | R13 x2, R14 | KILLED | ok | see jsonl |
| M28 | stream twin without the splat | structured_comparison_service.py | R15 | KILLED | ok | see jsonl |
| M29 | VISION_CATEGORY_KEYS reordered | openai_service.py | R21, R3 | KILLED | ok | see jsonl |
| M30a | no-content line logs the refusal text | openai_service.py | R4[refusal], P8[service_refusal], P8[route_refusal] | KILLED | ok | see jsonl |
| M30b | counts line logs the kept brands | openai_service.py | P8[service_v04, route_v04, route_v07, route_v01] | KILLED | ok | see jsonl |
| M31 | literal max_tokens= at the V2 site | openai_service.py | tests/test_model_config_enforced.py::test_no_call_site_passes_raw_sampling_kwargs (P9, run with the unit file) | KILLED | ok | see jsonl |
| M32 | V2 call bypasses guarded_llm_create | openai_service.py | R3; test_model_config_enforced::test_image_tier3_dispatches_through_the_breaker_chokepoint; test_u3c_store_false_pin::test_u3c_02_no_chat_dispatch_outside_the_chokepoint_under_app | KILLED | ok | see jsonl |
| M33 | usage None crashes the V2 path | openai_service.py | R22 | KILLED | ok | see jsonl |
| M34 | camera_vision fixture back to MagicMock (E1-E3) | test_camera_vision.py | TestIdentifyProductsMocked::test_successful_identification (the reintroduced TypeError, by design) | KILLED | ok | see jsonl |
| M35 | rows pruned, mirror not regenerated (E4) | PRE_IMPL_FAILURE_BASELINE.md | test_ci_gates::test_baseline_count_is_rederivable_from_the_committed_file | KILLED | ok | see jsonl |
| M36 | non-dict items not dropped (review C7) | openai_service.py | R8b | KILLED | ok | see jsonl |
| M37 | optional strings not stripped (C8) | openai_service.py | R9 | KILLED | ok | see jsonl |
| M38a | features not capped at 8 (C8) | openai_service.py | R9 | KILLED | ok | see jsonl |
| M38b | features not cut at 80 (C8) | openai_service.py | R9 | KILLED | ok | see jsonl |
| M39 | one image keeps only one (ruling 2) | openai_service.py | R6b | KILLED | ok | see jsonl |
| M40 | unknown_brand counter dead (ruling 5) | openai_service.py | R9 | KILLED | ok | see jsonl |
| M42 | bound fixed at the default (knob ignored) | openai_service.py | R10, R10b | KILLED | ok | see jsonl |
| M44 | V1 prompt edited (OFF byte identity) | openai_service.py | P1 x7 | KILLED | ok | see jsonl |
| M45 | V1 kwargs gain response_format (OFF identity) | openai_service.py | P2 x7 | KILLED | ok | see jsonl |
| M46 | timeout WARNING missing | openai_service.py | R10 | KILLED | ok | see jsonl |
| M47 | length WARNING missing | openai_service.py | R5, R5b | KILLED | ok | see jsonl |
| M48 | wire strip gated on the flag (design pin, ruling 9) | image_routes.py | R17[b_off_delivery] | KILLED | ok | see jsonl |

The machine-generated table with every mutant's [pyt] elapsed/status/rc: <scratchpad>/B3red/mutation_table.md.

## 5. Step 7: comm set at base in the REAL worktree

- Rule applied: module grep (openai_service|image_routes|identify_products|structured_comparison_service|pre_impl_failures|PRE_IMPL_FAILURE_BASELINE|gen_baseline_mirror|regression_gate_diff) UNION symbol grep (vision_products|compare_from_text|StructuredComparisonService|clean_json_response|_product_display_identity|LLM_UNAVAILABLE_FRIENDLY_MESSAGE|camera_failure_envelope) UNION source-scanning pins (the brief's named files + test_start_command* + every test combining a path-walk/read with an app path literal) UNION the CLAUDE.md readers (test_ci_gates, test_behavior_dimension_translation) UNION the SmartCompareApp-scanning tests (belt) MINUS test_precommit_hook*.py MINUS the new unit file; NETWORK_FLAKY_EXCLUDE node ids passed as --deselect in the chunks holding their files.
- Result: 246 files (by reason: modref 204, symbol 122, srcscan 47, client_scan 23, claude_md_reader 2), a strict superset of the spec's 213-file list (comm -23 empty). List: <scratchpad>/B3red/comm_base_list.txt (sha256 e86eb8e086a6994c5202a1e3c8d1ec348c155b04cef2f4ea2a3468f80b661f14); per-file reasons: comm_base_reasons.tsv (sha256 65209ec9d38b0c4077787ba2e54cf7b24295eb75397a3ae3fa27fce32981c586); script comm_set.py; runner comm_run.py.
- 10 chunks (9 x 25 + 21), bound 1200, one at a time:

```
c01 3 failed, 1337 passed, 5 deselected; [hermeticity] 1340; [netguard] blocked 60 attempt(s) from 18 node(s)
[pyt] tag=b3red-comm-base-c01 start=2026-10-20 06:16:14 end=2026-10-20 06:17:06 elapsed=53s bound=1200s status=FAIL rc=1
c02 550 passed, 1 skipped, 2 deselected; [hermeticity] 551; [netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=b3red-comm-base-c02 start=2026-10-20 06:17:07 end=2026-10-20 06:18:31 elapsed=84s bound=1200s status=OK rc=0
c03 2042 passed, 1 skipped; [hermeticity] 2042; [netguard] blocked 81 attempt(s) from 40 node(s)
[pyt] tag=b3red-comm-base-c03 start=2026-10-20 06:18:36 end=2026-10-20 06:20:27 elapsed=111s bound=1200s status=OK rc=0
c04 1593 passed, 5 deselected; [hermeticity] 1593; [netguard] blocked 20 attempt(s) from 9 node(s)
[pyt] tag=b3red-comm-base-c04 start=2026-10-20 06:20:27 end=2026-10-20 06:21:16 elapsed=49s bound=1200s status=OK rc=0
c05 535 passed, 4 deselected; [hermeticity] 535; [netguard] blocked 8 attempt(s) from 2 node(s)
[pyt] tag=b3red-comm-base-c05 start=2026-10-20 06:21:16 end=2026-10-20 06:21:38 elapsed=22s bound=1200s status=OK rc=0
c06 2 failed, 480 passed, 7 deselected; [hermeticity] 482; [netguard] blocked 162 attempt(s) from 23 node(s)
[pyt] tag=b3red-comm-base-c06 start=2026-10-20 06:21:43 end=2026-10-20 06:22:23 elapsed=40s bound=1200s status=FAIL rc=1
c07 890 passed, 4 skipped, 2 deselected, 1 xfailed, 2 errors; [hermeticity] 894; [netguard] blocked 105 attempt(s) from 7 node(s)
[pyt] tag=b3red-comm-base-c07 start=2026-10-20 06:22:23 end=2026-10-20 06:24:12 elapsed=108s bound=1200s status=FAIL rc=1
c08 1606 passed, 1 skipped, 2 deselected; [hermeticity] 1606; [netguard] blocked 29 attempt(s) from 11 node(s)
[pyt] tag=b3red-comm-base-c08 start=2026-10-20 06:24:12 end=2026-10-20 06:26:21 elapsed=129s bound=1200s status=OK rc=0
c09 452 passed, 1 skipped, 12 deselected; [hermeticity] 453; [netguard] blocked 181 attempt(s) from 66 node(s)
[pyt] tag=b3red-comm-base-c09 start=2026-10-20 06:26:31 end=2026-10-20 06:27:29 elapsed=58s bound=1200s status=OK rc=0
c10 1017 passed, 4 deselected, 35 xfailed; [hermeticity] 1052; [netguard] blocked 20 attempt(s) from 12 node(s)
[pyt] tag=b3red-comm-base-c10 start=2026-10-20 06:27:29 end=2026-10-20 06:27:57 elapsed=28s bound=1200s status=OK rc=0
```
- Base FAILED/ERROR set (7, file comm_base_failed_sorted.txt): exactly the expected classes of spec 1.10.
  - .pre_impl_failures.txt rows: tests/test_camera_vision.py::TestIdentifyProductsMocked::{test_empty_product_fields_normalized, test_malformed_response_returns_error, test_successful_identification} (the three B3 fixes), tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction.
  - the two known environmental tiktoken ERRORs: tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ::test_truth_on_prefix_static_and_cacheable.
  - Observation: two baseline rows whose files are in the set PASS at base on this box: tests/test_extraction_prompt_bundle_c.py::test_response_builder_strips_inference_source and tests/test_supplement_branch_genuine.py::TestCatalogSupplementSourceAttribution::test_cde2_attributes_catalog_supplement_domain_when_flag_on (not this unit's; recorded so GREEN's head run is read against the same truth).
- The netguard counts are the existing ratchet nodes (sentinel-neutralised, no egress); GREEN compares head against these.

## 6. Step 8: restore check

- sha256 manifest of all 3,406 tracked files in the real worktree before the scratch worktree was created and after the comm set: identical (manifest sha a4b8f769167c8b67d2d9319daf0e1a752b6e09347b48bd14a0327087fa11c0a6 both sides); `git diff --stat` empty; HEAD 81df2b641454e0301cca51a3ba01bf8ef3d7e649.
- `git status --short` of the real worktree: `?? tests/test_s80_b3_vision_identity_v2.py` only.
- Scratch worktree removed with `git worktree remove --force`; `git worktree list | grep -c b3_scratch` = 0; the directory is gone; no .qa-mutation.lock left in either worktree.
- No orphan pytest: no python.exe process whose command line names b3red / sc-s80-b3 / b3_scratch. The B1 adversary's concurrent pytest (its own cwd/tag) was not touched.

## 7. Deviations from the spec (rulings applied; each is deliberate)

- D1 SPEC TRAP for GREEN (E4, measured on the prototype): spec 3.5's PRUNED paragraph puts `test_camera_vision.py::TestIdentifyProductsMocked` on a `#` comment line. scripts/regression_gate_diff.parse_failure_ids strips each line at the first " - " and then counts ANY line containing "::" as a baseline id, so the comment line becomes a 9th id and tests/test_ci_gates.py::test_baseline_count_is_rederivable_from_the_committed_file goes red (mirror 8 vs file 9). Existing header lines survive only because they start with "#   - ". GREEN must keep "::" off every comment line of tests/.pre_impl_failures.txt (the prototype writes "test_camera_vision.py TestIdentifyProductsMocked rows"), or start such a line with "#   - ".
- D2 The new test file is LF (the orchestrator rule "Pure ASCII and LF in every file you write"); spec 5 said CRLF like its neighbours. The index is LF either way.
- D3 Ruling B3-R6(3): an image_index that does not name one of the request's images (out of range, negative, bool, str, missing) is KEPT unpaired with `_image_index` None, appended after the paired picks in reply order (the review K2 design); counter `unpaired_index` (replaces `dropped_out_of_range`). Rows: R8 (7, -1, True), R8c (str "0", missing key), R8d (a 1-based reply on two images keeps both products). The spec's R8 expectation (one product) is superseded.
- D4 Ruling B3-R6(2): R6b uses its own fixture (ONE_IMAGE_THREE: A high, D low, B medium at index 0, IMG(1)) and expects ["A", "B"] (best two in rank order); the spec's R6b (one product, dropped_out_of_range=1) is superseded.
- D5 R6 uses a richer fixture (PICK_BEST: B medium, A high, E medium at index 0; C low, F low at index 1) so the first / last / lowest-confidence / no-dedupe mutants are all distinguishable; expects ["A", "C"], candidates=5.
- D6 The [VISION_V2] counts line is pinned by its exact key set {candidates, kept, dropped_not_product, unpaired_index, dropped_non_dict, unknown_brand, unknown_name, images, finish_reason} (rulings B3-R6(3) rename + B3-R6(5) counters), parsed as k=v pairs (order free), INFO level, one line per call. unknown_brand / unknown_name count KEPT products whose brand is "Unknown" / name is "Unknown Product" (R9 expects 1 / 1).
- D7 Ruling B3-R6(4): R3 pins the category schema as `{"anyOf": [{"type": "string", "enum": [nine]}, {"type": "null"}]}` (the review K1 literal form); the comparison JSON-normalises tuples and sorts every `required` list. R3 also pins the V2 kwargs key set exactly ({model, messages, max_tokens, temperature, store, response_format}), the prompt as pure ASCII and free of "JSON array" and "WITHOUT packaging".
- D8 Ruling B3-R6(11): R13 / R14 expect FIVE `_vision_*` keys (adds `_vision_image_index`, None for an unpaired product).
- D9 R17 gained arm f (metering OFF + envelope ON: the second `_camera_failure_envelope` call site, which the spec's arm e does not reach); found by mutant M20e.
- D10 Added rows beyond the spec table: R8b (review C7), R8c, R8d, R22 (P10's ON half as its own RED node), P3b (OFF non-dict still raises AttributeError: R-A1, the base is not repaired OFF), R23 (public_vision_products direct: new list, new dicts, non-dict pass-through, None -> []). P10 is the OFF half only (PIN).
- D11 P2 additionally pins that no asyncio.wait_for wraps the OFF dispatch (a delegating recorder on asyncio.wait_for; asserts no wrapped coroutine named guarded_llm_create).
- D12 P8 (ruling B3-R1) checks the unit's own records (prefix "[VISION_V2]" or "[IMAGE] preferences") for brand / name / refusal text over 7 ON scenarios (3 service, 4 route), and allows ERROR records on the two watched loggers only for the two existing vision exit lines; the compare-raise scenario is not in P8 (its base ERROR line "[IMAGE] Comparison failed after identification" is pre-existing).
- D13 RED rows never use pytest.raises where base does not raise (pytest's Failed is not an AssertionError): a `_capture()` helper returns (result, exception) and the row asserts on it. Every missing symbol is read through getattr(..., None) and asserted.
- D14 UNIT_ENV also deletes ENABLE_SEARCH_LOG_SYNTHETIC_MARKER and ENABLE_STRICT_OPTIONAL_AUTH (beyond B3-R5's two additions; both are read on the camera route path).
- D15 P9 is not a node of the new file: it is the existing M1 / chokepoint nodes; mutants M31 / M32 were run together with tests/test_model_config_enforced.py (+ tests/test_u3c_store_false_pin.py) and killed there.
- D16 The comm set is 246 files, a superset of the spec's 213 (symbol references, a cleaner app-path literal regex, and the 23 SmartCompareApp-scanning files as the belt the spec left to the orchestrator).
- D17 Observation for GREEN: a fresh detached worktree of this repo checked the app files out with LF line endings (cat -A at openai_service.py:126-131), not the CRLF spec 1.9 measured in sc-s80-b3; GREEN edits the real worktree, so 1.9 still governs there.

## 8. Questions for the gate

- Q1 (ruling 3 scope) Confirm "unpaired" covers every index that is not an int in [0, n_images) (bool, str, missing, negative), not only out-of-range ints, and that unpaired products are appended after the paired picks in reply order (R8 / R8c / R8d pin this).
- Q2 (ruling 2 + 3 together) With one image, the prototype keeps the best two candidates at index 0 and then appends unpaired candidates (so a one-image reply can carry more than two products; the route compares products[0] and products[1]). No row pins a cap; confirm no cap is wanted (the prompt says at most 4).
- Q3 (ruling 4 wording) R3 requires `"type": "string"` inside the enum branch of the category anyOf (the review K1 literal). Confirm, or rule the bare `{"enum": [...]}` branch.
- Q4 `candidates` in the counts line counts every list item including non-dicts in the prototype; no row pins candidates when non-dicts are present (R8b pins kept and dropped_non_dict only). Rule if it matters.
- Q5 R16b pins the exact message "[IMAGE] preferences read failed: RuntimeError" (WARNING). Confirm the wording.
- Q6 D1: does the orchestrator want the PRUNED wording rewritten in the spec now (so GREEN does not rediscover the trap), and should scripts/regression_gate_diff skip "#" lines (out of scope for B3; a one-line hardening for a later unit)?

## 9. NOT MEASURED

Nothing in the procedure was left unmeasured. Not part of RED by design: the comm set at HEAD (GREEN), the live model's structured-output acceptance, Arabic transliteration and the 1-based index rate (canary items).

## 10. Files

- tests/test_s80_b3_vision_identity_v2.py (real worktree, untracked): sha256 36b78a404deefbc4fbea66b2d75574f203346a8e53550a3ddf04d3550e4af15e, 65,236 B, 0 bytes > 127, 0 CR.
- Scratch artifacts (not in any worktree): <scratchpad>/B3red/{notes.md, test_s80_b3_vision_identity_v2.py (same bytes), proto_apply.py, prototype_diff_ascii.txt, mutate.py, mutation_results.jsonl, mutation_table.md, mut_logs/, comm_set.py, comm_run.py, comm_base_list.txt, comm_base_reasons.tsv, comm_base_failed_sorted.txt, comm_base_pyt_lines.txt, comm_logs/, unit_base_final.log/.xml, unit_base_final_failed.txt, base_*.log, proto_*.log, sha_manifest.py, manifest_before.json, manifest_after.json}.

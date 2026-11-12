# S81-07c CLAUDE-ROLE-FIX: RED round report (RED agent, Opus 5.5; written through the shell)

VERDICT: BLOCKED on one spec contradiction (quoted below). Every other RED deliverable is complete and measured.

## The contradiction (found at s07c-r-proto-c1, 20:20)

- Spec 2, T1: "`SITES["image_tier3"] = SiteSpec("text", 256, None, True)`: option (b)."
- Spec 4.2: "Stay green (no E-row allowed): ... `tests/test_s81_s22b_self_critique_retire.py:79`; ..."
- Measured: :79 is `"disambiguate": ["text", 256, True, False], "image_tier3": ["text", 256, True, False],` in SITES_BASE, whose comment (:76) reads `# site -> [role, claude_max_tokens, expects_json, schema is None]`; test_p2_router_and_model_tables_kept (:427) compares it with the live SITES. With T1 applied it fails: `{'image_tier3': ['text', 256, True, True]} != {'image_tier3': ['text', 256, True, False]}`. T1 and 4.2 cannot both hold.
- Proposed resolution (the orchestrator's ruling): E5 = the one-field re-pin of :79 to `["text", 256, True, True]` (E_ROWS.md; applied only in the removed prototype, where the file is then green).
- After finding it I continued steps 5-7 (E-rows, mutation table, cleanup): none of them rests on the contradicted clause.

## Unit and files

- W = C:/Users/SynAckITPC/Documents/AI/sc-s81-s07c, detached at c6ebbd2ed593081cb6241915c36ae29af4c29bca; git status --short: `?? tests/test_s81_s07c_role_fix.py` (only).
- RED file tests/test_s81_s07c_role_fix.py: sha256 a197e2f2..., 31,671 bytes, LF, 0 bytes > 127, 17 nodes (one function per row); ruff E9,F63,F7,F82 clean; py_compile ok.
- Notes folder: notes.md, E_ROWS.md, proto.diff (the change list + E1 E2 E4a-c E5), proto_edit.py, proto_erows.py, mut.py, run_mut.sh, proto_orig/ (byte copies), mut_bak/, the pyt logs, candidates.txt, srcscan_extra.txt.
- Prototype: git worktree add --detach <notes>/proto c6ebbd2e (20:14); git worktree remove --force (20:58); git worktree list then shows only W for s07c.

## Step 1: spec section 1 at c6ebbd2e

Every line re-measured with git show: all match. Two +1 line offsets only: IMAGE_TIER3_SCHEMA is at llm_router.py:104-109 (spec :103-108; heading comment :101-103) and the SITES comment at :209-211 (spec :208-210); the image_tier3 row is :221. Box fact: verdict_gold.json is CRLF in this working copy (core.autocrlf=true, no .gitattributes); the LF-normalised sha256 78134acf... equals the git blob; V11 pins that value.

## Every [pyt] line

```
[pyt] tag=s07c-r-base-c1 start=2026-11-12 19:52:34 end=2026-11-12 19:54:48 elapsed=135s bound=600s status=FAIL rc=1  (7 candidate files at base: 1 failed, 736 passed, 2 skipped, 1 xfailed, 2 errors; [hermeticity] sentinel checked 740 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s07c-r-base-c2 start=2026-11-12 19:56:06 end=2026-11-12 19:58:19 elapsed=133s bound=600s status=OK rc=0  (41 candidate files at base: 2213 passed; [hermeticity] sentinel checked 2213 test(s); [netguard] blocked 131 attempt(s) from 53 node(s))
[pyt] tag=s07c-r-red-base1 start=2026-11-12 20:09:55 end=2026-11-12 20:10:09 elapsed=14s bound=600s status=FAIL rc=1  (RED file at base, first pass: 15 failed, 2 passed; T06 failed only on the placeholder vision_v2 hash, whose base value it printed; [hermeticity] 17; [netguard] blocked 0)
[pyt] tag=s07c-r-red-base2 start=2026-11-12 20:12:01 end=2026-11-12 20:12:11 elapsed=10s bound=600s status=FAIL rc=1  (THE RED GATE RUN at base: 14 failed, 3 passed; [hermeticity] sentinel checked 17 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
[pyt] tag=s07c-r-red-proto1 start=2026-11-12 20:16:13 end=2026-11-12 20:16:25 elapsed=12s bound=600s status=OK rc=0  (RED file in the prototype: 17 passed; [hermeticity] 17; [netguard] blocked 0)
[pyt] tag=s07c-r-proto-c1 start=2026-11-12 20:17:04 end=2026-11-12 20:20:36 elapsed=212s bound=600s status=FAIL rc=1  (7 candidate files, prototype with the change list only: 6 failed, 731 passed, 2 skipped, 1 xfailed, 2 errors; [hermeticity] 740; [netguard] blocked 0)
[pyt] tag=s07c-r-proto-c1e start=2026-11-12 20:24:17 end=2026-11-12 20:26:24 elapsed=127s bound=600s status=FAIL rc=1  (the same 7 files + the RED file with E1 E2 E4a-c E5 applied: 1 failed, 753 passed, 2 skipped, 1 xfailed, 2 errors = the base failed set; [hermeticity] 757; [netguard] blocked 0)
[pyt] tag=s07c-r-proto-c2 start=2026-11-12 20:27:05 end=2026-11-12 20:29:18 elapsed=133s bound=600s status=OK rc=0  (41 candidate files in the prototype: 2213 passed; [hermeticity] 2213; [netguard] blocked 131 attempt(s) from 53 node(s) = base)
[pyt] tag=s07c-r-mut-M01 start=2026-11-12 20:31:46 end=2026-11-12 20:31:52 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M02 start=2026-11-12 20:32:22 end=2026-11-12 20:32:30 elapsed=8s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M03 start=2026-11-12 20:33:01 end=2026-11-12 20:33:07 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M04 start=2026-11-12 20:33:50 end=2026-11-12 20:33:56 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M05 start=2026-11-12 20:34:27 end=2026-11-12 20:34:32 elapsed=5s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M06 start=2026-11-12 20:35:07 end=2026-11-12 20:35:14 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M07 start=2026-11-12 20:35:45 end=2026-11-12 20:35:55 elapsed=10s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M08 start=2026-11-12 20:36:49 end=2026-11-12 20:36:55 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M09 start=2026-11-12 20:37:29 end=2026-11-12 20:37:40 elapsed=10s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M10 start=2026-11-12 20:38:25 end=2026-11-12 20:38:36 elapsed=11s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M11 start=2026-11-12 20:39:07 end=2026-11-12 20:39:12 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M12 start=2026-11-12 20:39:59 end=2026-11-12 20:40:06 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M13 start=2026-11-12 20:41:08 end=2026-11-12 20:41:14 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M14 start=2026-11-12 20:42:19 end=2026-11-12 20:42:24 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M15 start=2026-11-12 20:42:57 end=2026-11-12 20:43:05 elapsed=8s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-mut-M16 start=2026-11-12 20:43:47 end=2026-11-12 20:44:01 elapsed=13s bound=600s status=FAIL rc=1
[pyt] tag=s07c-r-base-s1 start=2026-11-12 20:46:09 end=2026-11-12 20:47:09 elapsed=60s bound=600s status=OK rc=0  (22 extra source-scanning files at base: 895 passed, 1 skipped, 2 deselected; [hermeticity] 896; [netguard] blocked 17 attempt(s) from 5 node(s))
[pyt] tag=s07c-r-base-s2 start=2026-11-12 20:47:50 end=2026-11-12 20:51:24 elapsed=214s bound=600s status=FAIL rc=1  (21 extra files at base: 6 failed, 2416 passed, 1 skipped, 10 deselected; [hermeticity] 2423; [netguard] blocked 89 attempt(s) from 23 node(s))
[pyt] tag=s07c-r-proto-s1 start=2026-11-12 20:52:07 end=2026-11-12 20:53:08 elapsed=61s bound=600s status=OK rc=0  (prototype: 895 passed = base; [hermeticity] 896; [netguard] blocked 17 attempt(s) from 5 node(s))
[pyt] tag=s07c-r-proto-s2 start=2026-11-12 20:53:48 end=2026-11-12 20:57:22 elapsed=214s bound=600s status=FAIL rc=1  (prototype: the same 6 failed, 2416 passed; [hermeticity] 2423; [netguard] blocked 89 attempt(s) from 23 node(s))
```

Base failures (recorded, not fixed; identical at base and prototype): test_s81_s07_meas_harness.py::test_r35_fixtures (b'\r' in the CRLF working copy: this box only); test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable and ::test_render_digests_match_base_except_the_fence ERROR (cold tiktoken cache noise); test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset|empty|false|pad0|OFF]; test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (root cause not investigated).

## Candidate files (step 2)

git grep over tests/*.py (IMAGE_TIER3_SCHEMA | image_tier3 | generate_comparison | score_winner | meas_claude_gate | w4_11_prompt_digest_recorder | router SITES readers): 48 files; the score_winner hit (tests/test_validation_matrix_runner.py) is an unrelated runner helper, run anyway:

tests/test_arabic_verdict_output_w414.py tests/test_backend_cleanup.py tests/test_comparison_quality_v2.py tests/test_cost_tracking.py tests/test_diagnostics_flag_gated.py tests/test_explicit_pair_integration_mocked.py tests/test_extraction_pros_cons_diagnostic.py tests/test_guidance_insights.py tests/test_inc_x8_phase2_cached_rating.py tests/test_inc_x9_cohort_line_retire.py tests/test_m13_04_full_stream_deadline.py tests/test_m18_openai_tpm_sizing.py tests/test_model_config_enforced.py tests/test_paid_route_metering.py tests/test_partial_response_no_fabricated_scores.py tests/test_personalization.py tests/test_prescoring_showable_guard.py tests/test_price_fallback_may_decline.py tests/test_prompt_fence.py tests/test_prompt_truth.py tests/test_rating_provenance.py tests/test_retro_w2_1.py tests/test_review_prompt_quality.py tests/test_s70_model_router_downgrade.py tests/test_s75_fanout_identity.py tests/test_s80_url_mode_v2.py tests/test_s81_d14_live_robots.py tests/test_s81_s04c_refusal_log_hygiene.py tests/test_s81_s06_anthropic_router.py tests/test_s81_s06_router_gate_rows.py tests/test_s81_s07_meas_harness.py tests/test_s81_s09_device_quota.py tests/test_s81_s10b_links_gate.py tests/test_s81_s17_kb_ingest.py tests/test_s81_s18_kb_first_serve.py tests/test_s81_s22b_self_critique_retire.py tests/test_security_regression.py tests/test_singleton_state.py tests/test_stage_timings.py tests/test_streaming.py tests/test_url_compare_category.py tests/test_validation_matrix_runner.py tests/test_verdict_prompt_unification.py tests/test_verdict_response_format.py tests/test_w4_12_display_contract.py tests/test_w49_extraction_catch_redaction.py tests/test_winner_prose_reconciliation.py tests/test_youtube_flag_and_cache.py

Extra, beyond the spec grep: the 43 source-scanning tests naming the four edited modules by path (minus the candidates and the precommit hook files), base and prototype: the same failed set.

## Row table

| row | function | at base (measured, s07c-r-red-base2) | prototype | spec |
|---|---|---|---|---|
| V01 | test_v01_signature_score_winner_index_last_default_none | RED (AssertionError: 10 == 11 params) | green | RED |
| V02 | test_v02_block_bytes_index_0_and_1 | RED (AssertionError: _FIXED_WINNER_BLOCK is None) | green | RED |
| V03 | test_v03_identity_outside_the_block | RED (AssertionError: signature) | green | RED |
| V04 | test_v04_placement_after_scores_before_preferences | RED (AssertionError: signature) | green | RED |
| V05 | test_v05_invalid_values_are_byte_identical | RED by signature (AssertionError) | green | PIN where runnable, else RED by signature |
| V06 | test_v06_no_scores_summary_is_byte_identical | RED by signature (AssertionError) | green | as V05 |
| V07 | test_v07_claude_request_keeps_the_block | RED (AssertionError: signature) | green | RED |
| V08 | test_v08_both_production_callers_pass_the_scorer_index | RED (AssertionError: keyword count 0 at :5561) | green | RED |
| V09 | test_v09_url_caller_unchanged | PIN green | green | PIN |
| V10 | test_v10_harness_a6_and_a1_request_parity | RED (AssertionError: 120 of 120 A6 requests without the block) | green, 0 socket attempts | RED |
| V11 | test_v11_evaluation_unchanged | PIN green | green | PIN |
| T01 | test_t01_image_tier3_site_option_b | RED (AssertionError: schema present) | green | RED |
| T02 | test_t02_image_tier3_claude_request | RED (AssertionError: format present) | green | RED |
| T03 | test_t03_image_tier3_schema_constant_deleted | RED (AssertionError: constant present) | green | RED |
| T04 | test_t04_claude_branch_fence_and_parse | RED (AssertionError: base returns [URL, None, None, None, URL]) | green | RED where the base path differs |
| T05 | test_t05_harness_a1_counts_image_tier3_as_json_not_schema | RED (AssertionError: (2, 2) != (0, 0)) | green | RED |
| T06 | test_t06_other_schema_sites_unchanged | PIN green | green | PIN |

## E-rows (full old / new text in E_ROWS.md, appended below)

- E1 test_s81_s06_anthropic_router.py:752-759 R02c: AttributeError at the prototype; image_tier3 output_schema None + expects_json True.
- E2 test_s81_s06_anthropic_router.py:671 R01: IMAGE_TIER3_SCHEMA dropped from the exported-name list.
- E3 (spec): NOT NEEDED, measured green (R04 / R13b / R14 read the schema from SITES live).
- E4a test_s81_s07_meas_harness.py:2525 R87: the schema pin moves to disambiguate (20, 20); image_tier3 (0, 40, 40).
- E4b test_s81_s07_meas_harness.py:2473-2474 _decision_run: the scripted 400 moves from k == 7 (image_tier3) to k == 15 (disambiguate).
- E4c test_s81_s07_meas_harness.py:2548 R88: disambiguate (20, 19); image_tier3 (schema_n, json_n) == (0, 40).
- E5 PROPOSED (contradicts spec 4.2): test_s81_s22b_self_critique_retire.py:79 image_tier3 [..., False] -> [..., True].

## Mutation table (prototype; .qa-mutation.lock 20:30:47 to 20:44; byte copy, one exact edit, -k rows bound 600, restore, sha256)

| mutant | edit (prototype, exact string, count 1) | rows (-k) | result | restore |
|---|---|---|---|---|
| M01 | the append becomes `_unused = _FIXED_WINNER_BLOCK.format(` | V02 | KILLED (AssertionError) | sha256 MATCH |
| M02 | `label=score_winner_index, index=score_winner_index` | V02 | KILLED (AssertionError) | sha256 MATCH |
| M03 | `isinstance(score_winner_index, int)` (bool accepted) | V05 | KILLED (AssertionError) | sha256 MATCH |
| M04 | the append moved in front of the scores f-string (one region rewrite) | V04 | KILLED (AssertionError) | sha256 MATCH |
| M05 | the append moved after the preferences / cohort block | V04 | KILLED (AssertionError) | sha256 MATCH |
| M06 | the append outside `if scores_summary:` | V06 | KILLED (AssertionError) | sha256 MATCH |
| M07 | the streaming caller omits the keyword | V08 | KILLED (AssertionError) | sha256 MATCH |
| M08 | the REST caller passes `scoring_result.get("winner_index", 0)` | V08 | KILLED (AssertionError) | sha256 MATCH |
| M09 | the A6 builder passes `score_winner_index=0` | V10 | KILLED (AssertionError) | sha256 MATCH |
| M10 | the A1 builder omits the keyword | V10 | KILLED (AssertionError) | sha256 MATCH |
| M11 | "Do not re-decide" -> "Do not revisit" in the constant | V02 | KILLED (AssertionError) | sha256 MATCH |
| M12 | image_tier3 SiteSpec keeps an inline closed schema | T01, T02 | KILLED (both, AssertionError) | sha256 MATCH |
| M13 | image_tier3 expects_json False | T01, T02 | KILLED (both, AssertionError) | sha256 MATCH |
| M14 | image_tier3 claude_max_tokens 120 | T01 | KILLED (AssertionError) | sha256 MATCH |
| M15 | IMAGE_TIER3_SCHEMA re-added | T03 | KILLED (AssertionError) | sha256 MATCH |
| M16 | `ctx.gold[case["case_id"]] = 0` in the A6 plan builder | V11 | KILLED (AssertionError) | sha256 MATCH |

16 of 16 KILLED by assertions; 0 survivors; 0 equivalents; the four prototype source files re-verified at their post-edit sha256.

## Deviations

- Continued steps 5-7 after the contradiction (above).
- T04 adds a ```JSON (upper-case tag) fence case beside ```json: measured, it is where the base path differs (base None), so T04 is RED.
- V03 adds ENABLE_GPT_WINNER + ENABLE_ARABIC_VERDICT_OUTPUT ON (output_lang ar); V06 checks index 0 and 1; V04 also pins the no-preferences tail; V07 also pins the JSON-only line at the end.
- V11 pins the LF-normalised gold sha256, REPS_MAX, the plan's gold read (ctx.gold and each A6 item's gold in plan order) and evaluate_role('VERDICT') on the synthetic metrics (M16 killable).
- T06 also pins every other SITES row and the vision_v2 schema by canonical-JSON sha256 bffe493b... (read from the first base run's failure; the second base run is the gate).
- M04 / M05 / M06 are single contiguous-region rewrites (one exact-string edit each).
- Prototype edits by Python exact-string replacement on the CRLF bytes; git diff --stat shows no whole-file diff.

## Questions for the gate

- Q1: rule E5 (s22b :79 re-pin) against spec 4.2, or change T1.
- Q2: accept E4b (the scripted 400 moved to disambiguate) as the E4 'move to disambiguate' reading.

## NOT MEASURED

- The comm set by the union rule at base and HEAD (GREEN gate).
- The fourteen client jest fences (GREEN gate).
- The offline main() --dry-run of the harness text stage under its process-wide socket guard (gate 7); V10 / V11 run _plan_text offline under a row-local socket recorder only.
- CLAUDE.md rows (GREEN).
- Root causes of the base failures d22c P1 x5 and s10 R06 (identical at base and prototype).

## E_ROWS.md (verbatim)

# S81-07c RED round: E-rows measured at the prototype (base c6ebbd2e + the spec 2-3 change list)

Every edit is an exact-string replacement (count 1) on the file's working-copy text (CRLF kept).
Applied in the prototype by proto_edit.py (change list) then proto_erows.py (these rows); with all six
applied, every candidate file's failed set equals its base failed set (s07c-r-proto-c1e, s07c-r-proto-c2).
The spec's E3 (s06 :1540-1559, :525, :602) is NOT needed: measured green at the prototype (R04 / R13b /
R14 read the schema from SITES live).

## E1

- file: tests/test_s81_s06_anthropic_router.py:752-759 test_r02c_mandated_schemas
- reason: AttributeError at the prototype: the row reads r.IMAGE_TIER3_SCHEMA and pins image_tier3 == that schema
- spec clause: spec 4.1 E1; contract T1 (SiteSpec("text", 256, None, True)) + T2 (constant deleted)
- match count: 1

old text:

```
    """R02c RED (R-S06-1, R-S06-10): image_tier3 = IMAGE_TIER3_SCHEMA; vision_v2 reuses the B3 V2
    identity schema; vision_v1 requests {"products": [...]}; disambiguate is the
    ["true", "false", "unknown"] enum with the confidence enum."""
    sites = _sym("SITES")
    r = _router()
    assert sites["image_tier3"].output_schema == r.IMAGE_TIER3_SCHEMA
    assert r.IMAGE_TIER3_SCHEMA["required"] == ["image_url"]
```

new text:

```
    """R02c RED (R-S06-1, R-S06-10; S81-07c T1 / T2): image_tier3 takes option (b) (no schema, the
    JSON-only line); vision_v2 reuses the B3 V2 identity schema; vision_v1 requests
    {"products": [...]}; disambiguate is the ["true", "false", "unknown"] enum with the confidence enum."""
    sites = _sym("SITES")
    r = _router()
    assert sites["image_tier3"].output_schema is None and sites["image_tier3"].expects_json is True
```

## E2

- file: tests/test_s81_s06_anthropic_router.py:671 test_r01_router_module_and_symbols
- reason: AssertionError at the prototype: 'llm_router.IMAGE_TIER3_SCHEMA is missing' (the exported-name list)
- spec clause: spec 4.1 E2; contract T2
- match count: 1

old text:

```
                 "ESCALATION_CAP_PER_COMPARE", "PROVIDER", "SITES", "IMAGE_TIER3_SCHEMA",
```

new text:

```
                 "ESCALATION_CAP_PER_COMPARE", "PROVIDER", "SITES",
```

## E4a

- file: tests/test_s81_s07_meas_harness.py:2525 test_r87_decision_path_pass
- reason: AssertionError at the prototype: assert (0, 0) == (40, 40) (has_schema is read from SITES at report time)
- spec clause: spec 4.1 E4 (the :2525 synthetic schema_n row moves to disambiguate); contract T1
- match count: 1

old text:

```
    assert (sites["image_tier3"]["schema_n"], sites["image_tier3"]["schema_accepted"]) == (40, 40)
```

new text:

```
    assert (sites["disambiguate"]["schema_n"], sites["disambiguate"]["schema_accepted"]) == (20, 20)
    assert (sites["image_tier3"]["schema_n"], sites["image_tier3"]["json_n"],
            sites["image_tier3"]["json_valid"]) == (0, 40, 40)
```

## E4b

- file: tests/test_s81_s07_meas_harness.py:2473-2474 _decision_run (the fail script)
- reason: with image_tier3 at option (b) the scripted 400 no longer crosses schema_accept_min; moved to the round-0 disambiguate call (k == 15) so R88's TEXT cell keeps 'schema_accept_min'
- spec clause: spec 4.1 E4 (moves to disambiguate); contract T1
- match count: 1

old text:

```
            if fail and k == 7 and r == 0:
                return _status_exc(400)
```

new text:

```
            if fail and k == 15 and r == 0:  # S81-07c: a schema site (disambiguate) since image_tier3 is (b)
                return _status_exc(400)
```

## E4c

- file: tests/test_s81_s07_meas_harness.py:2548 test_r88_decision_path_fail
- reason: AssertionError at the prototype: assert (0, 0) == (40, 39)
- spec clause: spec 4.1 E4 (the :2548 synthetic schema_n row moves to disambiguate); contract T1
- match count: 1

old text:

```
    assert (sites["image_tier3"]["schema_n"], sites["image_tier3"]["schema_accepted"]) == (40, 39)
```

new text:

```
    assert (sites["disambiguate"]["schema_n"], sites["disambiguate"]["schema_accepted"]) == (20, 19)
    assert (sites["image_tier3"]["schema_n"], sites["image_tier3"]["json_n"]) == (0, 40)
```

## E5  (PROPOSED: contradicts spec 4.2)

- file: tests/test_s81_s22b_self_critique_retire.py:79 SITES_BASE (read by test_p2_router_and_model_tables_kept :427)
- reason: AssertionError at the prototype: {'image_tier3': ['text', 256, True, True]} != {'image_tier3': ['text', 256, True, False]} (the fourth field = schema is None)
- spec clause: NOT EXPLAINED by the spec: spec 4.2 names this line 'Stay green (no E-row allowed)'; contract T1 forces it red. PROPOSED, pending the orchestrator's ruling.
- match count: 1

old text:

```
    "disambiguate": ["text", 256, True, False], "image_tier3": ["text", 256, True, False],
```

new text:

```
    "disambiguate": ["text", 256, True, False], "image_tier3": ["text", 256, True, True],
```



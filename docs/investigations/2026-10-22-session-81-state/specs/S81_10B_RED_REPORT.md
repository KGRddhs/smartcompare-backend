# S81-10b LINKS-GATE RED report (RED agent Opus 5.5, 2026-11-04 06:27-07:00 AST)

Unit S81-10b (FOCUS, LC-1), flag ENABLE_FRAGRANCE_ONLY_GATE (shared with S81-10), base c6fb65336deab4f48275b13d3847e0f42b298984.
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10b (detached at the base). This report was written through the shell by a script (the harness refuses a subagent Write of a report .md).
Read in full: s81-common.txt, the spec (.qa-s80/S81-10b_UNIT_SPEC.md), the review (.qa-s80/S81-10b_SPEC_REVIEW.md), RULINGS_S81_10B.md.

## Files written (the real worktree; nothing else touched)
- tests/test_s81_s10b_links_gate.py  55,343 B  sha256 2df272ff30b54271ac72af0d05235fab3fc98be1372923b66bc6811dc16488d0 (ASCII, LF)
- tests/fixtures/s81_s10b_flag_off_golden.json  34,734 B  sha256 aebccaa6afedec3a4e9b541c4f7742b2b29c1ced2b7d4205296066358f745eae (ASCII, LF; recorded AT BASE with S81_S10B_RECORD_GOLDEN=1, the flag unset, the full configuration incl. the tier recorder and the fixed X-Request-ID s10b-rid; UG01-UG19)
- git status --short after: only the two files above untracked; HEAD c6fb6533; no tracked diff.

## Counts
- RED rows R01-R20 (+ R18d): 41 nodes, all FAIL at base on AssertionError ONLY (41 'E AssertionError', no other type).
- PIN rows P01-P06: 34 nodes (P01 x5, P02 x6, P03 x10, P04 x5, P05 x2, P06 x6), all PASS at base.
- Prototype (scratch worktree): ambient OFF 75/75 passed, ambient ON (ENABLE_FRAGRANCE_ONLY_GATE=true for that one call) 75/75 passed.
- Mutants: 33 (M01-M33) all KILLED by AssertionError; M-EQ1, M-EQ2, M-EQ4 SURVIVED (declared equivalent); M-EQ3 KILLED (deviation D3).

## Every [pyt] line (from the runner's ledger; logs under C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red)
[pyt] tag=s10b-red-rec start=2026-11-04 06:34:35 end=2026-11-04 06:34:40 elapsed=4s bound=600s status=FAIL rc=1
[pyt] tag=s10b-red-base start=2026-11-04 06:34:54 end=2026-11-04 06:35:00 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-red-base2 start=2026-11-04 06:37:49 end=2026-11-04 06:37:55 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-proto-off start=2026-11-04 06:39:06 end=2026-11-04 06:39:12 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-proto-off2 start=2026-11-04 06:39:30 end=2026-11-04 06:39:36 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-proto-on start=2026-11-04 06:39:36 end=2026-11-04 06:39:42 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-proto-off3 start=2026-11-04 06:39:57 end=2026-11-04 06:40:02 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s10b-proto-on2 start=2026-11-04 06:40:02 end=2026-11-04 06:40:07 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s10b-proto-s10-noek2 start=2026-11-04 06:40:28 end=2026-11-04 06:40:35 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-proto-s10-ek2 start=2026-11-04 06:40:36 end=2026-11-04 06:40:43 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-proto-off4 start=2026-11-04 06:42:37 end=2026-11-04 06:42:43 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s10b-proto-on3 start=2026-11-04 06:42:43 end=2026-11-04 06:42:48 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s10b-mut-m01 start=2026-11-04 06:42:54 end=2026-11-04 06:43:00 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m02 start=2026-11-04 06:43:01 end=2026-11-04 06:43:07 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m03 start=2026-11-04 06:43:07 end=2026-11-04 06:43:14 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m04 start=2026-11-04 06:43:15 end=2026-11-04 06:43:21 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m05 start=2026-11-04 06:43:21 end=2026-11-04 06:43:27 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m06 start=2026-11-04 06:43:48 end=2026-11-04 06:43:54 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m07 start=2026-11-04 06:43:55 end=2026-11-04 06:44:01 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m08 start=2026-11-04 06:44:01 end=2026-11-04 06:44:08 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m09 start=2026-11-04 06:44:40 end=2026-11-04 06:44:46 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m10 start=2026-11-04 06:44:57 end=2026-11-04 06:45:03 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m11 start=2026-11-04 06:45:03 end=2026-11-04 06:45:09 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m12 start=2026-11-04 06:45:10 end=2026-11-04 06:45:16 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m13 start=2026-11-04 06:45:16 end=2026-11-04 06:45:23 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m14 start=2026-11-04 06:45:23 end=2026-11-04 06:45:30 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m15 start=2026-11-04 06:45:30 end=2026-11-04 06:45:37 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m16 start=2026-11-04 06:45:37 end=2026-11-04 06:45:44 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m17 start=2026-11-04 06:45:44 end=2026-11-04 06:45:50 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m18 start=2026-11-04 06:45:51 end=2026-11-04 06:45:57 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m19 start=2026-11-04 06:45:57 end=2026-11-04 06:46:03 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m20 start=2026-11-04 06:46:04 end=2026-11-04 06:46:10 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m21 start=2026-11-04 06:46:42 end=2026-11-04 06:46:49 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m22 start=2026-11-04 06:46:49 end=2026-11-04 06:46:55 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m23 start=2026-11-04 06:46:56 end=2026-11-04 06:47:02 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m24 start=2026-11-04 06:47:02 end=2026-11-04 06:47:08 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m25 start=2026-11-04 06:47:09 end=2026-11-04 06:47:15 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m26 start=2026-11-04 06:47:16 end=2026-11-04 06:47:22 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m27 start=2026-11-04 06:47:22 end=2026-11-04 06:47:28 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m28 start=2026-11-04 06:47:29 end=2026-11-04 06:47:36 elapsed=7s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m29 start=2026-11-04 06:47:36 end=2026-11-04 06:47:42 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m30 start=2026-11-04 06:47:43 end=2026-11-04 06:47:49 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m31 start=2026-11-04 06:47:49 end=2026-11-04 06:47:55 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m32 start=2026-11-04 06:47:56 end=2026-11-04 06:48:02 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m33 start=2026-11-04 06:48:02 end=2026-11-04 06:48:08 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m-eq1 start=2026-11-04 06:48:09 end=2026-11-04 06:48:14 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s10b-mut-m-eq2 start=2026-11-04 06:48:15 end=2026-11-04 06:48:20 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s10b-mut-m-eq3 start=2026-11-04 06:48:21 end=2026-11-04 06:48:26 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-mut-m-eq4 start=2026-11-04 06:48:27 end=2026-11-04 06:48:32 elapsed=6s bound=600s status=OK rc=0
[pyt] tag=s10b-red-base3 start=2026-11-04 06:52:12 end=2026-11-04 06:52:18 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s10b-comm-base-c00 start=2026-11-04 06:53:00 end=2026-11-04 06:53:48 elapsed=48s bound=1200s status=OK rc=0
[pyt] tag=s10b-comm-base-c01 start=2026-11-04 06:54:20 end=2026-11-04 06:55:24 elapsed=64s bound=1200s status=OK rc=0
[pyt] tag=s10b-comm-base-c02 start=2026-11-04 06:55:25 end=2026-11-04 06:56:31 elapsed=66s bound=1200s status=FAIL rc=1

[hermeticity]/[netguard]: unit-file runs 'sentinel checked 74/75 test(s)', 'blocked 0 attempt(s) from 0 node(s)'; S81-10 rows 176 / 0; comm c00 2022 / 47 attempts from 26 nodes, c01 1374 / 209 from 16, c02 842 / 143 from 65 (neutralized-host sentinels and one example.com getaddrinfo in test_rate_limiting_complete: base noise).
Note: runone.py waits for any live pytest on the box before each launch (the G2 lane ran in parallel); the check is racy, so a few mutant runs overlapped a G2 prototype run by seconds (no DUPLICATE, no TIMEOUT).

## Base unit run (final file, tag s10b-red-base3): 41 failed, 34 passed. Failed ids:
FAILED tests/test_s81_s10b_links_gate.py::test_r01_url_routes_read_the_shared_flag_reader
FAILED tests/test_s81_s10b_links_gate.py::test_r02_budget_spent_never_billed[post-acct]
FAILED tests/test_s81_s10b_links_gate.py::test_r02_budget_spent_never_billed[post-dev]
FAILED tests/test_s81_s10b_links_gate.py::test_r02_budget_spent_never_billed[get-acct]
FAILED tests/test_s81_s10b_links_gate.py::test_r02_budget_spent_never_billed[get-dev]
FAILED tests/test_s81_s10b_links_gate.py::test_r03_budget_order_reserve_and_consent
FAILED tests/test_s81_s10b_links_gate.py::test_r04_budget_subject_axes_and_anonymous
FAILED tests/test_s81_s10b_links_gate.py::test_r05_budget_fail_open_and_exemptions
FAILED tests/test_s81_s10b_links_gate.py::test_r06_post_extract_refusal[post-v1]
FAILED tests/test_s81_s10b_links_gate.py::test_r06_post_extract_refusal[get-v1]
FAILED tests/test_s81_s10b_links_gate.py::test_r06_post_extract_refusal[post-v2]
FAILED tests/test_s81_s10b_links_gate.py::test_r06_post_extract_refusal[get-v2]
FAILED tests/test_s81_s10b_links_gate.py::test_r07_mixed_pair_refused_per_product[ab]
FAILED tests/test_s81_s10b_links_gate.py::test_r07_mixed_pair_refused_per_product[ba]
FAILED tests/test_s81_s10b_links_gate.py::test_r08_blind_pair_classified_chip_free[nochip]
FAILED tests/test_s81_s10b_links_gate.py::test_r08_blind_pair_classified_chip_free[other]
FAILED tests/test_s81_s10b_links_gate.py::test_r08_blind_pair_classified_chip_free[fragrances]
FAILED tests/test_s81_s10b_links_gate.py::test_r08_blind_pair_classified_chip_free[electronics]
FAILED tests/test_s81_s10b_links_gate.py::test_r09_blind_houses_with_a_real_chip_proceed_without_a_classifier
FAILED tests/test_s81_s10b_links_gate.py::test_r10_classifier_other_proceeds_uncounted
FAILED tests/test_s81_s10b_links_gate.py::test_r11_form_override_compares_as_fragrances[mist-first]
FAILED tests/test_s81_s10b_links_gate.py::test_r11_form_override_compares_as_fragrances[mist-second]
FAILED tests/test_s81_s10b_links_gate.py::test_r12_rule1_on_extracted_names[blind]
FAILED tests/test_s81_s10b_links_gate.py::test_r12_rule1_on_extracted_names[llm-fragrances]
FAILED tests/test_s81_s10b_links_gate.py::test_r13_house_beside_a_product_word_goes_to_the_classifier
FAILED tests/test_s81_s10b_links_gate.py::test_r14_device_debit_refunded_on_the_link_refusal
FAILED tests/test_s81_s10b_links_gate.py::test_r15_failure_row_and_no_delivery_side_effects
FAILED tests/test_s81_s10b_links_gate.py::test_r16_log_hygiene_and_grammar
FAILED tests/test_s81_s10b_links_gate.py::test_r17_service_signature_and_order
FAILED tests/test_s81_s10b_links_gate.py::test_r18_category_gate_resolver_classified
FAILED tests/test_s81_s10b_links_gate.py::test_r18d_route_labels
FAILED tests/test_s81_s10b_links_gate.py::test_r19_mixed_jsonld_pair_refused_per_product[laptop-edt-first]
FAILED tests/test_s81_s10b_links_gate.py::test_r19_mixed_jsonld_pair_refused_per_product[laptop-edt-second]
FAILED tests/test_s81_s10b_links_gate.py::test_r19_mixed_jsonld_pair_refused_per_product[shampoo-edt-first]
FAILED tests/test_s81_s10b_links_gate.py::test_r19_mixed_jsonld_pair_refused_per_product[shampoo-edt-second]
FAILED tests/test_s81_s10b_links_gate.py::test_r20_no_chip_blind_pair_one_a2b[fragrances-nochip]
FAILED tests/test_s81_s10b_links_gate.py::test_r20_no_chip_blind_pair_one_a2b[fragrances-other]
FAILED tests/test_s81_s10b_links_gate.py::test_r20_no_chip_blind_pair_one_a2b[fashion-nochip]
FAILED tests/test_s81_s10b_links_gate.py::test_r20_no_chip_blind_pair_one_a2b[fashion-other]
FAILED tests/test_s81_s10b_links_gate.py::test_r20_no_chip_blind_pair_one_a2b[other-nochip]
FAILED tests/test_s81_s10b_links_gate.py::test_r20_no_chip_blind_pair_one_a2b[other-other]

## Golden
Recorded by s10b-red-rec. UG01-06 200; UG07 400 bare string; UG08 400 NOT_PRODUCT_PAGE (category); UG09 429 USAGE_LIMIT; UG10 503 LLM_UNAVAILABLE; UG11 200 admin key; UG12 400 homepage; UG13 400 SSRF; UG14 200 detect; UG15 200 retailers; UG16 200 extract; UG17 200 + success row; UG18 400 + failure row; UG19 200 GET v2 FRAG (R-S10B-12). P01 green under the five OFF spellings at base and on the prototype (OFF and ON ambient).

## Prototype (scratch worktree C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/proto, detached c6fb6533, no junction; removed with git worktree remove --force; diff C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/prototype.diff; script C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/apply_proto.py)
- code: 3.1 category_gate (_ROUTE_LABELS + url.post/url.get; resolver_classified keyword-only default True; the R-S10B-2 branch: no chip / 'other' with resolver_classified False -> ONE classify, no evidence shortcut; the real-chip arm unchanged; docstring route list); 3.2 url_routes (module-alias import; _url_fragrance_gate_kwargs; _url_refusal_budget; the deadline forwarder; gate_route on _compare_urls_metered as its FIRST statement; _gate_kw on the four call sites); 3.3 url_extraction_service (keyword-only fragrance_gate; _url_fragrance_decision: pair rule 1, per-product rule 1 on 'other' pages over SHALLOW COPIES carrying search_query '<brand> <name>', post_resolve_refusal(resolver_classified=False, classify=a wrapper reading extraction_service.classify_category_llm at call time), the GC-1 rewrite, the R-S10B-3 fragrances rewrite on a recorded A2b answer); 3.4 text_routes comment (comment only).
- ek2: deletes P02 :2291-2294 and rewrites the :1026 comment (EK1 'the first of the two'; EK2 = R-S10B-4). The GREEN-owned gate-rows docstring :3-4 was NOT edited in the prototype.
- S81-10 RED + gate rows WITHOUT EK2: 2 failed (R06 environmental; P02 red), 174 passed. WITH EK2: 1 failed (R06 environmental only), 175 passed.
- Frozen file LF blob sha256: before fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e; after EK2 (apply_proto.py's comment text) 8750e81caed4aebe89f3f88154b03c1b37278da2fffc6d30613b0d73a6efeff7.
- R06 (test_r06_production_lexicon_content) stays environmental (CRLF working copy of data/fragrance_lexicon.json), red at base and on the prototype alike.

## Mutation table (prototype byte copies, exact-string edits matching once, the whole RED file through the runner, restored and sha256-verified after each; mutants.py, mutants.jsonl, mut_logs/; lock .qa-mutation.lock created and removed)
| M | mutant | outcome | killing nodes (first 4) |
|---|---|---|---|
| M01 | the budget line removed | KILLED (11 nodes, AssertionError) | test_r02_budget_spent_never_billed[post-acct], test_r02_budget_spent_never_billed[post-dev], test_r02_budget_spent_never_billed[get-acct], test_r02_budget_spent_never_billed[get-dev] ... |
| M02 | the budget line moved below the reserve | KILLED (5 nodes, AssertionError) | test_r02_budget_spent_never_billed[post-acct], test_r02_budget_spent_never_billed[post-dev], test_r02_budget_spent_never_billed[get-acct], test_r02_budget_spent_never_billed[get-dev] ... |
| M03 | an account-only budget subject | KILLED (25 nodes, AssertionError) | test_r02_budget_spent_never_billed[post-acct], test_r02_budget_spent_never_billed[post-dev], test_r02_budget_spent_never_billed[get-acct], test_r02_budget_spent_never_billed[get-dev] ... |
| M04 | the admin-mark check dropped | KILLED (2 nodes, AssertionError) | test_p05_admin_key_bypass[post], test_p05_admin_key_bypass[get] |
| M05 | the predicate re-parses the env locally | KILLED (1 nodes, AssertionError) | test_r01_url_routes_read_the_shared_flag_reader |
| M06 | the budget line moved after the S81-06 consent gate | KILLED (1 nodes, AssertionError) | test_r03_budget_order_reserve_and_consent |
| M07 | the service block moved after the write-back | KILLED (5 nodes, AssertionError) | test_r07_mixed_pair_refused_per_product[ab], test_r08_blind_pair_classified_chip_free[fragrances], test_r08_blind_pair_classified_chip_free[electronics], test_r11_form_override_compares_as_fragrances[mist-first] ... |
| M08 | the service block moved after generate_comparison | KILLED (27 nodes, AssertionError) | test_r01_url_routes_read_the_shared_flag_reader, test_r04_budget_subject_axes_and_anonymous, test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1] ... |
| M09 | resolver_classified=False not passed | KILLED (12 nodes, AssertionError) | test_r01_url_routes_read_the_shared_flag_reader, test_r08_blind_pair_classified_chip_free[nochip], test_r08_blind_pair_classified_chip_free[other], test_r10_classifier_other_proceeds_uncounted ... |
| M10 | the pair rule-1 outcome ignored | KILLED (1 nodes, AssertionError) | test_r12_rule1_on_extracted_names[llm-fragrances] |
| M11 | the decision's evidence forced False | KILLED (1 nodes, AssertionError) | test_r09_blind_houses_with_a_real_chip_proceed_without_a_classifier |
| M12 | the GC-1 rewrite of category_used removed | KILLED (1 nodes, AssertionError) | test_r11_form_override_compares_as_fragrances[mist-first] |
| M13 | record_refusal_async removed | KILLED (21 nodes, AssertionError) | test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1], test_r06_post_extract_refusal[post-v2], test_r06_post_extract_refusal[get-v2] ... |
| M14 | record_refusal_async awaited twice | KILLED (21 nodes, AssertionError) | test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1], test_r06_post_extract_refusal[post-v2], test_r06_post_extract_refusal[get-v2] ... |
| M15 | the refusal result built with code INSUFFICIENT_DATA | KILLED (24 nodes, AssertionError) | test_r01_url_routes_read_the_shared_flag_reader, test_r04_budget_subject_axes_and_anonymous, test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1] ... |
| M16 | the url failure arm skips the refund for CATEGORY_NOT_LIVE | KILLED (22 nodes, AssertionError) | test_r01_url_routes_read_the_shared_flag_reader, test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1], test_r06_post_extract_refusal[post-v2] ... |
| M17 | CATEGORY_NOT_LIVE added to _URL_V2_REFUSAL_CODES | KILLED (2 nodes, AssertionError) | test_r06_post_extract_refusal[post-v2], test_r06_post_extract_refusal[get-v2] |
| M18 | url.post / url.get not added to _ROUTE_LABELS | KILLED (6 nodes, AssertionError) | test_r02_budget_spent_never_billed[post-acct], test_r02_budget_spent_never_billed[post-dev], test_r02_budget_spent_never_billed[get-acct], test_r02_budget_spent_never_billed[get-dev] ... |
| M19 | resolver_classified defaulting to False | KILLED (1 nodes, AssertionError) | test_r18_category_gate_resolver_classified |
| M20 | the service block keyed on the flag instead of the kwarg | KILLED (3 nodes, AssertionError) | test_p02_service_without_the_kwarg_is_base[true], test_p05_admin_key_bypass[post], test_p05_admin_key_bypass[get] |
| M21 | the POST handler passes gate_route whatever the flag | KILLED (5 nodes, AssertionError) | test_r01_url_routes_read_the_shared_flag_reader, test_p01_flag_off_golden[unset], test_p01_flag_off_golden[false], test_p01_flag_off_golden[0] ... |
| M22 | the 429 detail built by refusal_detail | KILLED (4 nodes, AssertionError) | test_r02_budget_spent_never_billed[post-acct], test_r02_budget_spent_never_billed[post-dev], test_r02_budget_spent_never_billed[get-acct], test_r02_budget_spent_never_billed[get-dev] |
| M23 | the GET handler passes no _gate_kw | KILLED (4 nodes, AssertionError) | test_r02_budget_spent_never_billed[get-acct], test_r02_budget_spent_never_billed[get-dev], test_r06_post_extract_refusal[get-v1], test_r06_post_extract_refusal[get-v2] |
| M24 | _compare_with_deadline drops fragrance_gate | KILLED (2 nodes, AssertionError) | test_r06_post_extract_refusal[post-v2], test_r06_post_extract_refusal[get-v2] |
| M25 | an A2b 'other' counted (record before the refused check) | KILLED (9 nodes, AssertionError) | test_r09_blind_houses_with_a_real_chip_proceed_without_a_classifier, test_r10_classifier_other_proceeds_uncounted, test_r11_form_override_compares_as_fragrances[mist-first], test_r11_form_override_compares_as_fragrances[mist-second] ... |
| M26 | log_refused stage post_resolve | KILLED (11 nodes, AssertionError) | test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1], test_r06_post_extract_refusal[post-v2], test_r06_post_extract_refusal[get-v2] ... |
| M27 | vision_texts(products) replaced by the bare names | KILLED (2 nodes, AssertionError) | test_r09_blind_houses_with_a_real_chip_proceed_without_a_classifier, test_r13_house_beside_a_product_word_goes_to_the_classifier |
| M28 | the refusal returned before record_refusal_async | KILLED (21 nodes, AssertionError) | test_r06_post_extract_refusal[post-v1], test_r06_post_extract_refusal[get-v1], test_r06_post_extract_refusal[post-v2], test_r06_post_extract_refusal[get-v2] ... |
| M29 | the GET v2 call site passes gate_route whatever the flag | KILLED (5 nodes, AssertionError) | test_p01_flag_off_golden[unset], test_p01_flag_off_golden[false], test_p01_flag_off_golden[0], test_p01_flag_off_golden[off] ... |
| M30 | the per-product rule-1 pass dropped | KILLED (5 nodes, AssertionError) | test_r17_service_signature_and_order, test_r19_mixed_jsonld_pair_refused_per_product[laptop-edt-first], test_r19_mixed_jsonld_pair_refused_per_product[laptop-edt-second], test_r19_mixed_jsonld_pair_refused_per_product[shampoo-edt-first] ... |
| M31 | the copies not made (the extracted dicts rewritten) | KILLED (1 nodes, AssertionError) | test_r17_service_signature_and_order |
| M32 | the no-chip arm takes the evidence shortcut | KILLED (7 nodes, AssertionError) | test_r18_category_gate_resolver_classified, test_r20_no_chip_blind_pair_one_a2b[fragrances-nochip], test_r20_no_chip_blind_pair_one_a2b[fragrances-other], test_r20_no_chip_blind_pair_one_a2b[fashion-nochip] ... |
| M33 | the fragrances rewrite on the A2b answer dropped | KILLED (2 nodes, AssertionError) | test_r20_no_chip_blind_pair_one_a2b[fragrances-nochip], test_r20_no_chip_blind_pair_one_a2b[fragrances-other] |
| M-EQ1 | apply_form_override_stubs(verdict, products) added | SURVIVED |  |
| M-EQ2 | the predicate reads request.state before the flag | SURVIVED |  |
| M-EQ3 | selected_category dropped from the post_resolve_refusal call | KILLED (1 nodes, AssertionError) | test_r09_blind_houses_with_a_real_chip_proceed_without_a_classifier |
| M-EQ4 | category_used dropped from the post_resolve_refusal call | SURVIVED |  |

## Comm set (R-S10B-11)
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/comm_files.txt: 108 files, sha256 3e2570e2f4b52365abd81eee4cfe6dbdd34c24c8a801fb13113fc2bfb1e8d84b = the spec's 96 (S81_10B_COMM_with_text_routes.txt 7bae4082...) + tests/test_s81_s08b_gate_rows.py + the 11 SmartCompareApp scanners of RF5; reasons C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/comm_reasons.tsv (classes incl. claude and client-scan; the two brief-named files carry 'brief-named').
- Re-derived with commset_10b.py (the spec's classes + claude by any CLAUDE.md mention or CLAUDE_MD-style constant + client-scan by any SmartCompareApp mention): 130 raw hits; the 24 extras are comment-only mentions (checked by grep: none reads the file); only the 2 brief-named files of the 108 carry no grep class.
- BASE RECORD (LC-6): C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/harness/base_records/c6fb65336deab4f48275b13d3847e0f42b298984/3e2570e2f4b52365abd81eee4cfe6dbdd34c24c8a801fb13113fc2bfb1e8d84b.txt (+ .files, .pyt.log). 70 files run here in 3 chunks (25/25/20, bound 1200, alphabetical); the 38 overlap files REUSED from the G2 RED's base run at the same sha (its record 74b84ef9... in the same folder, FAILED set empty; its chunks c1-c3 OK and tests/test_secret_scan_static.py ALONE 31 passed); no file run twice.
- Sorted FAILED at base: tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (environmental = spec 1.10).
- Not run: the four test_precommit_hook*.py (excluded); the fourteen client fences (GREEN's; no junction).

## Deviations from the spec / review / rulings
- D1 (R12 / M10): with R-S10B-1's per-product rule 1 the spec's M10 killer (R12 on TV, A2b 0) no longer kills, because the per-product pass refuses each blind TV page by its own rule 1 at no A2b. Added R12 node [llm-fragrances] (TV pages the extraction LLM labelled 'fragrances': the pair rule 1 still refuses at $0); it kills M10 and pins R-S10B-6. Assumption: the pair rule over an LLM page label is intended (spec 2.5 step 1 precedes the per-product decision); rule if not.
- D2 (R11 mist-second): green at base through the base resolver (products[0] is the fragrance page); 'one MGET' added to R11 so both nodes are RED at base.
- D3 (M-EQ3 NOT equivalent): R-S10B-16 declares M-EQ3 (selected_category dropped from post_resolve_refusal) equivalent, but R-S10B-2 makes the chip decisive (a real chip -> the evidence arm; none -> one A2b): KILLED by R09 (HOUSES_BLIND + chip fragrances then takes an A2b). M-EQ4 stays equivalent (survived).
- D4 (R01 a): with only the shared reader patched ON (env unset) the error handler's own reader stays OFF, so the 400 ships without category / categories_live (the C15 mechanism); R01(a) asserts the status, the code, refund 1 and A2b 1.
- D5 (count): 33 numbered mutants M01-M33 + 4 declared equivalents were run (R-S10B-16 says 32).
- D6 (R08 / R20): the A2b names asserted are the '<brand> <name>' texts of the copies (R-S10B-1 / C12), e.g. ('Prada Paradoxe', 'Gucci Bloom').
- D7 (R05): (a)-(d) in one node (RED at base through (a)); (c) clears the allow-list (b) set.
- D8 (R14): the quota Redis fake is a copy of the gate-rows _QuotaRedis, not an import (a GREEN edit of that file cannot move this RED).
- D9 (R17): node part (b) added (EDT + laptop JSON-LD pages): the extracted dicts keep 'other' and carry no search_query; it is what kills M31.
- D10 (prototype): my first prototype docstring wrote the flag literal into url_routes.py; R01(c) caught it; fixed (GREEN must not write it either).

## Questions for the gate
- Q-G1: accept D1 (the new R12 [llm-fragrances] node)?
- Q-G2: withdraw M-EQ3 from the equivalents (D3)?
- Q-G3: the EK2 'after' sha holds only for apply_proto.py's comment text; GREEN records its own.

## NOT MEASURED
- The 1.10 pin sets a-d and the rest of the comm set on the prototype (GREEN's gate; the review measured them on its own prototype).
- The fourteen client fences, jest, the hook files.

## Paths
This report: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_RED_REPORT.md (copy C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/S81-10b_RED_REPORT.md); notes C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/notes.md; comm list C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/comm_files.txt + comm_reasons.tsv; prototype diff C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/prototype.diff; mutation harness C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_red/mutants.py + mutants.jsonl.

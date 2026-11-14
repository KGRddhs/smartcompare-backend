# S95-LG URL-WINNER-GUARD: RED report (RED round, Opus 5.5, 2026-11-14)

- Unit S95-LG, flag ENABLE_URL_WINNER_GUARD (new, default OFF). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s95-lg, branch feature/s95-url-winner-guard, base 731bcddf531a7e123963246168ca19f262859337 (git status empty at start).
- File written (the only one): tests/test_s95_lg_url_winner_guard.py, 19607 bytes, 0 non-ASCII bytes, LF only (0 CR), sha256 7b6aec460c27b91ea832694287e72a0ef4302b7731770248e90b717e401cb537; py_compile + ruff E9/F63/F7/F82 clean.
- Notes folder: this folder (notes.md, every log, base_record.txt, proto_record.txt, proto.diff, proto_tool.py).
- Time: first tool call 19:46, report 20:27 AST.

## 1. Base state re-measured (git -C W show HEAD:<path>)
| spec row | measured at 731bcddf |
|---|---|
| ues.py:1347 compare_from_urls | 1347 (ok) |
| ues.py:1383-1384 local imports | 1383-1384 (ok) |
| ues.py:1440-1452 resolve / fragrance / write-back | 1441 local import of _resolve_pair_category, 1442-1444 the call, 1445-1451 the S81-10b decision, 1452-1453 the write-back loop (off by one) |
| ues.py:1466-1469 generate_comparison call | 1466 try, 1467-1469 the call (ok) |
| ues.py:1470-1476 except LLMUnavailableError | 1470-1475 |
| ues.py:1488-1497 truthy error -> LLM_UNAVAILABLE | 1487-1496 |
| ues.py:1499-1503 V2 fill / raw keys | 1498-1502 |
| ues.py:1505-1514 delivered dict | 1504-1513 |
| ues.py:116 url_mode_v2_enabled | 116 (ok) |
| extraction_service.py:2568-2580 generate_comparison | 2568-2580 (ok); _FIXED_WINNER_BLOCK :2558; appended at :2639-2642 only inside `if scores_summary:` and for type(...) is int in (0, 1) |
| scoring_service.py:1357 / :3017 / :3111 | 1357 / 3017 / 3111 (ok); compute_tradeoff_pairs :2722 |
| response_builder.py:248 reconcile_winner_prose | 248 (ok); the WINNER_INDEX_MISMATCH warning :327-336 logs scoring_name / gpt_name with %r (product names) |
| scs.py:1271 _display_product_names | 1271 (ok); the text path's calls scs.py:5521 / 5527 / 5528 / 5623-5627 / 5636 |

L-1 measured: the scorer reads top-level `rating`, `review_count`, `fact_check` (scoring_service.py:1815, :2110, :1831); normalize_product_data (ues.py:1202) puts rating / count under `reviews` and has no fact_check, so on a link pair the review, reliability and popularity signals are MISSING on both products; only price.amount and specs score (fragrances: character = spec, longevity = spec_secondary, wear_value = price + spec; projection / versatility / presentation missing on both).

## 2. Q1 (is the scorer pure on link products?): YES, NO STOP
- scoring_service.py module imports: logging, os, re, typing, extraction_service (CATEGORY_SPEC_SCHEMAS, canonicalize_category: pure, re only). Local imports: text_sanitize.dedup_brand_name (re only), math. No httpx / requests / redis / supabase / socket / asyncio / threading / importlib anywhere in the module (grep).
- compute_scores (:1357-1702), build_scores_summary (:3017-3104), compute_tradeoff_pairs (:2722-2789, + _loser_strongest_dim) and compute_dimension_winners are pure computations over the dicts; env reads only (ENABLE_* scorer flags per call).
- Module state touched: _BUNDLE_C_SCORING_FLAG (:410-421, a process memo of the ENABLE_BUNDLE_C_SCORING env flag, read in _compute_raw_scores :1857) and the _scoring_service singleton (:3108-3116; ScoringService has no __init__ and no self.<attr> writes). Neither holds product data. compute_scores does not mutate products_data (the only product write, :2704, is apply_value_badges, not called).
- reconcile_winner_prose: an in-place dict edit + one WARNING + the ENABLE_WINNER_PROSE_RECONCILE read.
- Measured: every RED test call with the real scorer runs under 5 ms (pytest --durations: 7 of the 8 slowest phases < 0.005 s; the one 0.26 s entry is the first test's setup); [netguard] blocked 0 attempt(s) in every RED run.

## 3. The RED file
Hermetic: extract_from_url patched on ues; _resolve_pair_category patched on structured_comparison_service and generate_comparison on extraction_service (where the call-time local imports of compare_from_urls resolve, ues.py:1384 / :1441); fragrance_gate=None. The REAL scorer and the REAL reconcile. Link products built with the real normalize_product_data (synthetic SynthA / SynthB pages on shop-a.example / shop-b.example). The verdict double records (args, kwargs) deep copies and returns (verdict, usage). Every row that relies on the scorer asserts the pick first (PRECONDITION: the real scorer picks index 1). The predicate is read through getattr. Flags set with monkeypatch only (an autouse fixture delenvs the unit flag, ENABLE_URL_MODE_V2, ENABLE_WINNER_PROSE_RECONCILE and every llm_router role flag name).

| row | node(s) | asserts | base | proto |
|---|---|---|---|---|
| G1 | test_g1_on_ships_the_scorer_winner_and_drops_the_model_prose | ON, model picks 0, scorer picks 1: frozen key set; winner_index 1; comparison.winner_index 1; declaration '' / key_tradeoff '' / reason == _QUALITATIVE_WINNER_REASON(NAME_B) (prose flag OFF); no winner string names the loser; exactly one WINNER_INDEX_MISMATCH record | FAIL (assert 0 == 1) | PASS |
| G2 | test_g2_on_passes_the_scores_summary_and_the_scorer_winner | ON: one verdict call; args == base; kwargs keys == {category, scores_summary, score_winner_index}; summary a non-empty str equal to the in-test scorer summary; type(score_winner_index) is int == scorer's == 1 | FAIL ({'category'} != the 3 keys) | PASS |
| G3 | test_g3_on_scorer_failure_is_unguarded_base_with_one_constant_warning | ON, ScoringService.compute_scores raises SyntheticScorerFault: delivered == the base golden; verdict call == base; reconcile never called; no mismatch record; exactly one record '[URL_GUARD] scorer failed type=SyntheticScorerFault' (WARNING, the ues logger), no name / host / exception text in it | FAIL ([] != the warning) | PASS |
| G4 | test_g4_on_verdict_error_is_the_coded_non_delivery_without_a_reconcile | ON, verdict {winner_index 0, error 'x'}: == {success False, code LLM_UNAVAILABLE, error LLM_UNAVAILABLE_FRIENDLY_MESSAGE}; the reconcile (call-through recorder) never called; no mismatch record | PASS = a PIN (no guard to skip at base, as the spec allowed) | PASS |
| G5 | test_g5_on_with_url_mode_v2_the_recommendation_names_the_scorer_winner | ON + url_mode_v2: winner_index 1; recommendation names NAME_B, not NAME_A, == _QUALITATIVE_WINNER_REASON(NAME_B) | FAIL (assert 0 == 1) | PASS |
| G6 | test_g6_predicate_spellings[x10] | TRUE / ' on ' / 1 / yes -> True; '' / false / 0 / off / garbage / unset -> False; a per-call flip | FAIL x10 (missing) | PASS x10 |
| P1 | test_p1_off_full_configuration_is_byte_identical_base[unset,false x v1,v2] | B1: guard unset / 'false'; ENABLE_URL_MODE_V2 'true'/'false' matching url_mode_v2; ENABLE_WINNER_PROSE_RECONCILE and every role flag name (ROLE_FLAGS + ESCALATION + PRE_V3) 'true'; tripwires that RECORD and raise on get_scoring_service, ScoringService.compute_scores / build_scores_summary / compute_tradeoff_pairs, reconcile_winner_prose, _display_product_names (+ raising=False shadows on ues): nothing reached; the verdict call == base; delivered == the GOLDEN_DELIVERED literal; no guard / mismatch record | PASS x4 | PASS x4 |
| P2 | test_p2_off_ships_the_model_winner[unset,false,off] | OFF with the full config, the REAL scorer (precondition: picks 1), the model picks 0: winner_index 0, comparison == golden, delivered == golden, no records | PASS x3 | PASS x3 |

Counts: 22 nodes = 14 RED (G1, G2, G3, G5, G6 x10) + 8 PIN (G4, P1 x4, P2 x3). Every base failure ends on an AssertionError (14 of 14; no import / attribute / setup error); the preconditions hold at base.

## 4. Every run (one pytest at a time, waitfree.ps1 -OwnTagPrefix s95g- before each)

- [pyt] tag=s95g-red-base1 start=2026-11-14 20:00:02 end=2026-11-14 20:00:08 elapsed=5s bound=600s status=FAIL rc=1 (14 failed, 8 passed) [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-cb0 start=2026-11-14 20:01:20 end=2026-11-14 20:02:01 elapsed=42s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_base_0.log | [hermeticity] sentinel checked 765 test(s) [netguard] blocked 9 attempt(s) from 3 node(s)
- [pyt] tag=s95g-red-cb1 start=2026-11-14 20:02:54 end=2026-11-14 20:04:38 elapsed=104s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_base_1.log | [hermeticity] sentinel checked 867 test(s) [netguard] blocked 169 attempt(s) from 39 node(s)
- [pyt] tag=s95g-red-cb2 start=2026-11-14 20:04:52 end=2026-11-14 20:06:59 elapsed=127s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_base_2.log | [hermeticity] sentinel checked 3007 test(s) [netguard] blocked 27 attempt(s) from 3 node(s)
- [pyt] tag=s95g-red-cb3 start=2026-11-14 20:07:16 end=2026-11-14 20:09:28 elapsed=132s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_base_3.log | [hermeticity] sentinel checked 2633 test(s) [netguard] blocked 24 attempt(s) from 9 node(s)
- [pyt] tag=s95g-red-cb4 start=2026-11-14 20:09:42 end=2026-11-14 20:10:54 elapsed=72s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_base_4.log | [hermeticity] sentinel checked 1074 test(s) [netguard] blocked 73 attempt(s) from 25 node(s)
- [pyt] tag=s95g-red-cb5 start=2026-11-14 20:11:02 end=2026-11-14 20:11:20 elapsed=19s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_base_5.log | [hermeticity] sentinel checked 624 test(s) [netguard] blocked 20 attempt(s) from 12 node(s)
- [pyt] tag=s95g-red-proto1 start=2026-11-14 20:12:04 end=2026-11-14 20:12:07 elapsed=3s bound=600s status=OK rc=0 (22 passed) [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-cp0 start=2026-11-14 20:12:16 end=2026-11-14 20:12:53 elapsed=37s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_proto_0.log | [hermeticity] sentinel checked 765 test(s) [netguard] blocked 9 attempt(s) from 3 node(s)
- [pyt] tag=s95g-red-cp1 start=2026-11-14 20:12:53 end=2026-11-14 20:14:32 elapsed=98s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_proto_1.log | [hermeticity] sentinel checked 867 test(s) [netguard] blocked 169 attempt(s) from 39 node(s)
- [pyt] tag=s95g-red-cp2 start=2026-11-14 20:15:09 end=2026-11-14 20:17:15 elapsed=126s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_proto_2.log | [hermeticity] sentinel checked 3007 test(s) [netguard] blocked 27 attempt(s) from 3 node(s)
- [pyt] tag=s95g-red-cp3 start=2026-11-14 20:17:16 end=2026-11-14 20:19:22 elapsed=126s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_proto_3.log | [hermeticity] sentinel checked 2633 test(s) [netguard] blocked 24 attempt(s) from 9 node(s)
- [pyt] tag=s95g-red-cp4 start=2026-11-14 20:20:17 end=2026-11-14 20:21:28 elapsed=72s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_proto_4.log | [hermeticity] sentinel checked 1074 test(s) [netguard] blocked 73 attempt(s) from 25 node(s)
- [pyt] tag=s95g-red-cp5 start=2026-11-14 20:21:29 end=2026-11-14 20:21:47 elapsed=18s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\comm_proto_5.log | [hermeticity] sentinel checked 624 test(s) [netguard] blocked 20 attempt(s) from 12 node(s)
- [pyt] tag=s95g-red-mutM1 start=2026-11-14 20:22:49 end=2026-11-14 20:22:52 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\mut_M1.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-mutM2 start=2026-11-14 20:22:53 end=2026-11-14 20:22:56 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\mut_M2.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-mutM3 start=2026-11-14 20:22:57 end=2026-11-14 20:23:00 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\mut_M3.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-mutM4 start=2026-11-14 20:23:11 end=2026-11-14 20:23:15 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\mut_M4.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-mutM5 start=2026-11-14 20:23:15 end=2026-11-14 20:23:19 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\mut_M5.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-mutM6 start=2026-11-14 20:23:20 end=2026-11-14 20:23:23 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\mut_M6.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s95g-red-base2 start=2026-11-14 20:24:57 end=2026-11-14 20:25:00 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\red\red_base2.log | [hermeticity] sentinel checked 22 test(s) [netguard] blocked 0 attempt(s) from 0 node(s) (restored base, --durations=8: 14 failed, 8 passed, identical to base1)

Chunk results: base cb0 764 passed (+1 skipped, 2 deselected); cb1 867 passed; cb2 3004 passed + 2 ERROR; cb3 2626 passed + 7 FAILED; cb4 1073 passed; cb5 624 passed. Proto cp0 764; cp1 867; cp2 3004 + the same 2 ERROR; cp3 2625 passed + 8 FAILED; cp4 1073; cp5 624. No TIMEOUT anywhere. The per-node [netguard] egress lines (api.openai.com getaddrinfo from test_explicit_pair_integration_mocked, test_personalization, test_streaming, ...) are identical in count at base and proto (blocked, pre-existing).

## 5. Comm set and base record (the union rule)
- Set (135 files, comm_set.txt, sha256 306abcc2ec1917ae10bf7842826cea6bd09be353d6656095ab8dffdba870f915): 102 test files from the module / symbol grep over tests/ (url_extraction_service, compare_from_urls, generate_comparison, reconcile_winner_prose, compute_scores, build_scores_summary, compute_tradeoff_pairs, _display_product_names) UNION the 8 named source-scanning pins (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit) UNION the CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s07_meas_harness (reads CLAUDE.md at :2113, missing from the brief's named list), test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows (imports CLAUDE_MD)) and test_s81_s23_bypass_retire UNION 38 glob / rglob / walk / listdir walkers that name app/ UNION the 4.2 list UNION the importers of the w4_11_prompt_digest_recorder helper (it references ues and generate_comparison); MINUS the 4 test_precommit_hook*.py files; the RED file run separately. Chunks of 25/25/25/25/25/10 in sorted order (chunk_0..5.txt), the same chunks at base and proto.
- Helpers in the grep that are not tests: tests/_env_safety.py, _hermeticity.py (the #186 compute_scores shadow sentinel: the RED file patches the CLASS attribute, never the singleton), conftest.py, w4_11_prompt_digest_recorder.py, and four fixture generator scripts (not collected).
- BASE RECORD at 731bcddf (base_record.txt, 9 node ids; LC-6 cache candidate for base_records/731bcddf531a7e123963246168ca19f262859337/306abcc2...txt, filed by the orchestrator, not by me):
  - tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
  - tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  - tests/test_s81_s07_meas_harness.py::test_r35_fixtures
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
  - tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
  The two prompt_truth ERRORs are the brief's known cold-tiktoken noise; the seven FAILED nodes are LF / ASCII byte checks failing on the autocrlf=true CRLF working copy (assert b'\r' not in raw), environmental, identical at proto.

## 6. Prototype (spec 3 item 1, in place, under the lock) and the moved pins
- Lock W/.qa-mutation.lock created 20:11:50 (agent=s95lg-red); base byte copy base_copy.py sha256 d235862b305f1e8e5f12e498ed22925fdef547d7293361107646a76213170830 (71862 bytes, CRLF); prototype sha256 a83844dda54f2c426caaed35c2b928454b3cfd4ffb2bdc7f8b2f2640ae5c18de (74532 bytes); git diff --stat: 1 file, +49 / -1 (no whole-file diff); py_compile + ruff E9/F63/F7/F82 clean. Diff: proto.diff (82 lines, sha256 853ccb9b471be1b139493eda6c10caa666d3ba17a8583d500156b8eb63c936d5).
- Shape: url_winner_guard_enabled() after url_mode_v2_enabled() (the house idiom, the first statement); after the write-back loop `guard_scoring = None` and, under the predicate (read once per call), ONE try with the local imports (get_scoring_service, _display_product_names), compute_scores(products), the names, build_scores_summary, except Exception -> ONE `[URL_GUARD] scorer failed type=%s` warning; `verdict_kwargs` = {} or {scores_summary, score_winner_index} and the one call `generate_comparison(products[0], products[1], region, category=category_used, **verdict_kwargs)` (OFF: no keyword added at run time); after the error check, under guard_scoring, its own try: the local reconcile import, compute_tradeoff_pairs(dimension_winners, names, winner_index, scores=...), reconcile_winner_prose(comparison, ...) in place, except -> ONE `[URL_GUARD] reconcile failed type=%s` warning; then the base tail.
- RED at proto: 22 passed (s95g-red-proto1).
- MOVED PIN (1, a deliberate-change E-row the GREEN round must handle; spec 4.1 said none expected): tests/test_s81_s07c_role_fix.py::test_v09_url_caller_unchanged (green at base, red at proto). Its assertion (tests/test_s81_s07c_role_fix.py:428-435):

      def test_v09_url_caller_unchanged():
          """V09 PIN (V4): url_extraction_service.py's one generate_comparison call passes no
          score_winner_index (products[0], products[1], region, category=category_used)."""
          calls = _calls_named(URL_PATH, "generate_comparison")
          assert len(calls) == 1, len(calls)
          call = calls[0]
          assert [ast.unparse(a) for a in call.args] == ["products[0]", "products[1]", "region"]
          assert [(k.arg, ast.unparse(k.value)) for k in call.keywords] == [("category", "category_used")]

  At proto it fails at :435 with "Left contains one more item: (None, 'verdict_kwargs')". ANY implementation of the section 2 contract moves it (a guarded call needs the new keywords at that call site; a two-call if / else form would also fail its len(calls) == 1). It pins the S81-07c V4 ruling (the URL caller passes no score_winner_index), which this unit deliberately supersedes: the GREEN round re-pins it to the GREEN call shape in the same unit (E1), and the PR body says so.
- No other node moved: comm -13 of the sorted failing sets = exactly that one id; comm -23 = empty (proto_record.txt, 10 ids = the 9 base + E1). Every 4.2 stay-green file is green at base and proto (test_url_compare_category, test_s80_url_mode_v2, test_s81_s10b_links_gate (+ s81_s10b_flag_off_golden.json), test_s81_s06_anthropic_router, test_s81_s06_router_gate_rows, test_s81_s20_result_gate, test_retro_w2_1, test_paid_route_metering, test_s71_u13_compare_auth_required (+ s71_u13_flag_off_baseline.json), test_w4_13_measurement_truth, test_response_builder_winner_card_consistency, every other reconcile_winner_prose reader, the named source-scanning pins).

## 7. Mutants (each from the prototype byte copy, the RED file alone, bound 600, restore + sha check after each)
| id | exact edit | result | killed_by (all AssertionError) |
|---|---|---|---|
| M1 | drop the `"score_winner_index": ...` entry of verdict_kwargs | KILLED (1 failed) | G2 (:328, the kwargs key set) |
| M2 | the reconcile call -> `pass` | KILLED (2 failed) | G1 (:306 winner_index), G5 (:392) |
| M3 | the reconcile block moved above `if comparison.get("error"):` | KILLED (1 failed) | G4 (:380, the recorder ran on a non-delivery) |
| M4 | predicate `return True or os.getenv(...)` | KILLED (17 failed) | P1 x4 (:454 the tripwires were reached), P2 x3 (:470 the scorer winner shipped OFF), G6 x10 (:408 / :410) |
| M5 | the scorer warning gains `name=%s` with products[0].get("name") | KILLED (1 failed) | G3 (:355 the exact constant message) |
| M6 | the scorer warning -> `pass` (swallowed) | KILLED (1 failed) | G3 (:355 no record) |
6 of 6 KILLED, 0 survivors. Mutant file sha256s: M1 7c66b748..., M2 42e0ff20..., M3 566b0887..., M4 054dc68c..., M5 4fda0ef1..., M6 ccadfacc...; after each, restore-proto printed sha a83844dd... (the prototype bytes).

## 8. Restore proof
- restore-base: sha256 d235862b305f1e8e5f12e498ed22925fdef547d7293361107646a76213170830 == the snapshot; git hash-object of the working copy e08412906c579c60708aa6544fc3532e4b6c765f == HEAD blob e08412906c579c60708aa6544fc3532e4b6c765f (sha_match true).
- The lock W/.qa-mutation.lock deleted after the last restore (lock_removed true; ls: no such file).
- git -C W status --short: `?? tests/test_s95_lg_url_winner_guard.py` (only the RED file); git diff --stat empty.
- The restored base re-ran the RED file identically (s95g-red-base2: 14 failed, 8 passed).

## 9. Deviations
- D1 (patch site): generate_comparison and _resolve_pair_category are patched on extraction_service / structured_comparison_service, not "on the url_extraction_service module": compare_from_urls imports both at call time (ues.py:1384 / :1441), so a ues attribute would never be read (the house idiom of tests/test_url_compare_category.py). extract_from_url IS patched on ues. Recorders for the new symbols are set on their source modules plus raising=False shadows on ues, so a module-level-import GREEN is caught too.
- D2 (spec 1 line numbers): six rows are off by one (table in section 1); the facts hold.
- D3 (spec 4.1): one moved pin measured (E1 = test_s81_s07c_role_fix.py::test_v09_url_caller_unchanged) where the spec expected none.
- D4 (G4): passes at base: a PIN, as the spec allowed (no guard to skip); M3 proves it is not vacuous at proto.
- D5 (runner): the base comm chunk 0 was launched with the Bash tool's background mode while I waited for it (one pytest live, no concurrent run); every other run in the foreground. waitfree.ps1 ran before every pytest.
- D6 (union rule): tests/test_s81_s07_meas_harness.py joins the CLAUDE.md readers (it reads CLAUDE.md at :2113) though the brief's named list omits it; the 38 app/ walkers and the w4_11 recorder importers joined by class.
- D7 (extra strictness beyond the spec text, stated so the gate can rule): G1 exact reconciled strings with ENABLE_WINNER_PROSE_RECONCILE unset (the production state, L-3) + the frozen key set; G2 the exact kwargs key set and summary == the in-test scorer summary (_display_product_names names); G3 delivered == the base golden, reconcile never ran, the exact constant message; G6 a per-call flip; P1 parametrized guard unset / 'false' x url_mode_v2 False / True with tripwires also on _display_product_names; P2 parametrized unset / 'false' / 'off' and run with the full config.
- D8 (assumption): "the role flag names set to synthetic values" is read as every llm_router ROLE_FLAGS name + ESCALATION_FLAG + PRE_V3_FLAG set to 'true' (the production-like ON state; any_role_enabled() is then evaluated True at ues.py:1398), because a role flag has no credential value to synthesise and ON is the state that reaches the most base code.
- D9: the base record is stored in this notes folder (base_record.txt) and not under harness/base_records (my touch rule is W + the notes folder).

## 10. Open questions for the gate
- Q-E1: rule the E-row for V09 (test_s81_s07c_role_fix.py:428-435): the GREEN round re-pins the URL caller shape it chooses (the prototype's form is one call with `**verdict_kwargs`; an explicit if / else would also break len(calls) == 1). The S81-07c V4 ruling is superseded by S95-LG and the PR body should say so.
- Q-2 (coverage gaps, no RED row): the reconcile-failure arm (`[URL_GUARD] reconcile failed type=%s`, failure table "reconcile raises -> the verdict as the model wrote it"), the LLMUnavailableError-under-ON arm, the scorer-winner-None legacy branch and "a refused or failed extraction never reads the predicate" are not pinned; a GREEN that drops the reconcile try / except, logs a name there, or reads the flag before extraction survives every row. Candidates for GREEN gate rows (the RED file is frozen).
- Q-3: the in-place reconcile can leave a partially reconciled dict if it raised mid-way (practically unreachable: plain dict writes after the log). Stated-limit candidate.
- Q-4: with ENABLE_WINNER_PROSE_RECONCILE OFF (production) a mismatch row ships comparison.winner_declaration == '' (dropped, not replaced) and the link path has no overview.winner.name fallback (compare_from_urls returns the raw dict), so the section 8 canary item "the declaration names the shipped winner" holds only on agreement rows or with the prose flag ON; suggest "no winner-facing string names the loser" as the canary wording. (The client src has no winner_declaration reader: grep, measured.)
- Q-5: the reconcile's WINNER_INDEX_MISMATCH line logs both product names with %r (response_builder.py:327-336); under ON the link path starts emitting it. The spec carves it out as unchanged; confirm the carve-out for the link path.
- Q-6 (L-1 measured): on a link pair the scorer sees price + specs only (section 1); for fragrances three of six dims are missing on both sides, so the link winner rests on the spec / longevity / value dims. The RED fixture relies on exactly that (the thin-page product A with a 4.9 rating loses to the full-spec cheaper B).

## 11. NOT MEASURED
- The CLAUDE.md block (change list 3) and its readers at a prototype: not part of this round (no CLAUDE.md edit was made; the readers ran green at base and at the code prototype only).
- The fourteen client jest fences: not run (no client-read literal moves; the spec says none expected; no jest in this round).
- No live, network, Railway or provider measurement of any kind.

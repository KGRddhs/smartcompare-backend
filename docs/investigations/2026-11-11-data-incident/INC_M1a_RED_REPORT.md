# INC-M1a RESOLVER FOLD: RED REPORT (Claude Opus 5.5, 2026-11-17)

Base 7f672cfef1445233b58c323a08515baec7aae4bd (real worktree sc-inc-m1a, branch fix/inc-m1a-resolver-fold, HEAD verified before and after). Flag: none new; rides ENABLE_PRODUCT_RESOLVER (OFF on web).
Written through the shell (python). Nothing here says a production problem is fixed: hermetic gates are not the phone proof.

## Files
- NEW tests/test_inc_m1a_resolver_fold.py: sha256 63fc6a67b082317f3346d702a97d1880e2ca4dca8c9df66314b212d7cef0cfd3, 49076 bytes, 0 bytes > 127, LF, py_compile + ruff E9,F63,F7,F82,F401,F841 clean. 128 nodes (62 RED, 66 PIN).
- No other file in the real worktree changed: sha256 manifest of the 3626 tracked files equal before and after (INC-M1a/manifest_before.txt, manifest_after.txt); git status = ?? tests/test_inc_m1a_resolver_fold.py only.

## Runner note
The prompt names harness/pyt.py; called directly it refused: [pyt] tag=inc-m1a-red-base0 status=BUSY rc=126 NOT started: call harness/gate.py with the same arguments, never the runner itself. Every run went through harness/gate.py (common brief H12 (e) / H13 (e)), only after BOX_GO existed (created 12:07, seen 12:17).

## Step 2: files the review listed as not measured
None (no adversarial review; the facts report lists no not-measured test file). No run.

## Step 4: the unit file at base
- recording run: [pyt] tag=inc-m1a-red-base0 start=2026-11-17 12:35:53 end=2026-11-17 12:36:00 elapsed=7s bound=600s status=FAIL rc=1 (70 failed / 58 passed: the 62 RED + the 8 PIN-0 rows whose digest literal was the placeholder RECORD; the recorded digests were equal for unset and 'false' per kind/pair, then written into BASE_OFF_DIGEST)
- OFFICIAL: [pyt] tag=inc-m1a-red-base1 start=2026-11-17 12:54:01 end=2026-11-17 12:54:08 elapsed=8s bound=600s status=FAIL rc=1 ; [hermeticity] sentinel checked 128 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
- 62 failed, 66 passed. Every failure is an AssertionError (0 other exception lines in the log). The 66 PIN rows are green at base.
- RED rows by test: AR-0 data 1, AR-0c loader 1, AR-1 5, AR-2 16 (rest/stream x waw/ya x 4 flag mixes), AR-3 3, AR-4 4, AR-5 9, SEED-1 data 1, SEED-1 typed 17, SEED-2 reject 5.
- Failed node ids at base (INC-M1a/red_base1_failed.txt):
```
tests/test_inc_m1a_resolver_fold.py::test_ar0_arabic_aliases_in_the_lines_file
tests/test_inc_m1a_resolver_fold.py::test_ar0c_loader_reads_fourteen_lines
tests/test_inc_m1a_resolver_fold.py::test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arB]
tests/test_inc_m1a_resolver_fold.py::test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arBya]
tests/test_inc_m1a_resolver_fold.py::test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_latB]
tests/test_inc_m1a_resolver_fold.py::test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arB_latA]
tests/test_inc_m1a_resolver_fold.py::test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arBya_latA]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-waw-text_off]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-waw-text_on_c2]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-waw-text_on_c3]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-waw-text_on_c3_words]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-ya-text_off]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-ya-text_on_c2]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-ya-text_on_c3]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[rest-ya-text_on_c3_words]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-waw-text_off]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-waw-text_on_c2]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-waw-text_on_c3]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-waw-text_on_c3_words]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-ya-text_off]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-ya-text_on_c2]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-ya-text_on_c3]
tests/test_inc_m1a_resolver_fold.py::test_ar2_seam_queries_equal_the_latin_twin[stream-ya-text_on_c3_words]
tests/test_inc_m1a_resolver_fold.py::test_ar3_arabic_accept_sets_equal_the_golden[arA]
tests/test_inc_m1a_resolver_fold.py::test_ar3_arabic_accept_sets_equal_the_golden[arB]
tests/test_inc_m1a_resolver_fold.py::test_ar3_arabic_accept_sets_equal_the_golden[arBya]
tests/test_inc_m1a_resolver_fold.py::test_ar4_picture_identity_equals_the_latin_twin[waw-words_off]
tests/test_inc_m1a_resolver_fold.py::test_ar4_picture_identity_equals_the_latin_twin[waw-words_on]
tests/test_inc_m1a_resolver_fold.py::test_ar4_picture_identity_equals_the_latin_twin[ya-words_off]
tests/test_inc_m1a_resolver_fold.py::test_ar4_picture_identity_equals_the_latin_twin[ya-words_on]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[edp_waw_lexicon]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[edp_ya]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[edp_waw_plain_alef]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[edp_ya_plain_alef]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[edt_waw_lexicon]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[edt_ya]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[parfum]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[bleu_waw_edp]
tests/test_inc_m1a_resolver_fold.py::test_ar5_arabic_concentration_phrase_resolves[bleu_ya_edp_ya]
tests/test_inc_m1a_resolver_fold.py::test_seed1_data_rows
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[YSL Y EDP]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[YSL Y]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Yves Saint Laurent Y Eau de Parfum]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Rasasi Hawas]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Creed Aventus Cologne]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Aventus Cologne]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Rasasi Hawas for Her]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Hawas for Her]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Hawas Ice]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Rasasi Hawas Ice]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Lattafa Khamrah Qahwa]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Khamrah Qahwa]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Lattafa Khamrah Dukhan]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Creed Aventus for Her]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[Creed Aventus Absolu]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[YSL Libre Intense]
tests/test_inc_m1a_resolver_fold.py::test_seed1_typed_names_resolve[YSL Libre EDT]
tests/test_inc_m1a_resolver_fold.py::test_seed2_validator_rejects_non_boolean[1]
tests/test_inc_m1a_resolver_fold.py::test_seed2_validator_rejects_non_boolean[0]
tests/test_inc_m1a_resolver_fold.py::test_seed2_validator_rejects_non_boolean[str_true]
tests/test_inc_m1a_resolver_fold.py::test_seed2_validator_rejects_non_boolean[blank]
tests/test_inc_m1a_resolver_fold.py::test_seed2_validator_rejects_non_boolean[null]
```

## Step 5: the prototype (scratch worktree, thrown away)
Change list applied in INC-M1a/m1a_scratch (detached at the base): data/fragrance_lines.json (Arabic house + line aliases as JSON escapes incl. the explicit YA Bleu alias; YSL Y; Rasasi Hawas with the lexicon's Arabic Rasasi; flankers of Libre / Khamrah / Aventus; Libre [EDT, EDP]; single_concentration on Aventus / Layton / Khamrah / Hawas; 14 lines, ASCII); app/services/product_resolver.py: (1) the validator refuses a non-bool single_concentration; (2) the Arabic concentration phrases are read from the lexicon's concentration terms (category_gate.load_lexicon), mapped through a 5-word Arabic->Latin word map onto CONCENTRATION_PHRASES, YA variants added, used by _typed_concentration and _strip_concentrations; (3) a flanker made of generic words (Cologne) is matched against the tokens before the generic drop. Prototype copies: INC-M1a/proto/copies/ (resolver sha 9b8e8247..., data 98c02e04...).
- flag ON (whole file): [pyt] tag=inc-m1a-proto-on start=2026-11-17 12:54:33 end=2026-11-17 12:54:38 elapsed=5s bound=600s status=OK rc=0 -> 128 passed
- flag OFF (ENABLE_PRODUCT_RESOLVER=false exported for that one call; PIN rows: -k 'pin or ar0b or ar5b or ar5c or ar5d'): [pyt] tag=inc-m1a-proto-off start=2026-11-17 12:54:52 end=2026-11-17 12:54:57 elapsed=5s bound=600s status=OK rc=0 -> 66 passed, 62 deselected (the PIN-0 flag-OFF digests equal the base literals with the prototype in place)
- E-row probe (existing resolver suites against the prototype): [pyt] tag=inc-m1a-proto-erows start=2026-11-17 12:55:12 end=2026-11-17 12:55:35 elapsed=23s bound=1200s status=FAIL rc=1 -> 7 failed, 693 passed over test_inc_r1_resolver, test_inc_r1_seam, test_inc_u1_link_result, test_inc_u1_gate_rows, test_s81_s10_fragrance_gate, test_inc_i2b_guard_words_shop_image, test_inc_i2b_addenda. Deliberate E-rows GREEN must carry (frozen INC-R1 pins the spec contradicts): test_inc_r1_resolver.py::test_r05_lines_file (12 lines, flankers == [] except SWY), ::test_r11_residual_not_high[Creed Aventus for Her], ::test_r11_residual_not_high[YSL Libre Intense], ::test_r15_arabic_never_lexicon_high, ::test_r21_guard[g8], ::test_r21_guard[g8b] (the Arabic side now resolves in the lexicon arm, so the model is no longer called). The 7th, test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, is the CRLF working copy on this box (it fails at base too).

## Step 6: mutation table (byte copy of the prototype, unit file, bound 600, restore + sha256 check)
| id | mutant | result | killed by (first rows) | pyt |
|---|---|---|---|---|
| MA1 | drop the Arabic Sauvage line alias (house alias kept) | KILLED (33 failed, 95 passed, 15 warnings in 5.44s) | test_ar0_arabic_aliases_in_the_lines_file, test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arB], test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arBya] | [pyt] tag=inc-m1a-mut-ma1 start=2026-11-17 12:56:00 end=2026-11-17 12:56:06 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA2 | drop the YA Bleu de Chanel alias (WAW kept) | KILLED (2 failed, 126 passed, 15 warnings in 4.80s) | test_ar0_arabic_aliases_in_the_lines_file, test_seed1_data_rows | [pyt] tag=inc-m1a-mut-ma2 start=2026-11-17 12:56:13 end=2026-11-17 12:56:18 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA3 | Arabic concentration phrases read with the WAW particle only | KILLED (4 failed, 124 passed, 15 warnings in 4.91s) | test_ar5_arabic_concentration_phrase_resolves[bleu_ya_edp_ya], test_ar5_arabic_concentration_phrase_resolves[edp_ya], test_ar5_arabic_concentration_phrase_resolves[edp_ya_plain_alef] | [pyt] tag=inc-m1a-mut-ma3 start=2026-11-17 12:56:25 end=2026-11-17 12:56:30 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA4 | every Arabic concentration phrase mapped to EDT | KILLED (7 failed, 121 passed, 15 warnings in 4.92s) | test_ar5_arabic_concentration_phrase_resolves[bleu_waw_edp], test_ar5_arabic_concentration_phrase_resolves[bleu_ya_edp_ya], test_ar5_arabic_concentration_phrase_resolves[edp_waw_lexicon] | [pyt] tag=inc-m1a-mut-ma4 start=2026-11-17 12:56:37 end=2026-11-17 12:56:43 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA5 | flanker matched AFTER the generic-word drop (today's order) | KILLED (2 failed, 126 passed, 15 warnings in 4.79s) | test_seed1_typed_names_resolve[Aventus, test_seed1_typed_names_resolve[Creed | [pyt] tag=inc-m1a-mut-ma5 start=2026-11-17 12:56:50 end=2026-11-17 12:56:55 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA6 | single_concentration accepted as any value (no bool check) | KILLED (5 failed, 123 passed, 15 warnings in 4.85s) | test_seed2_validator_rejects_non_boolean[0], test_seed2_validator_rejects_non_boolean[1], test_seed2_validator_rejects_non_boolean[blank] | [pyt] tag=inc-m1a-mut-ma6 start=2026-11-17 12:57:02 end=2026-11-17 12:57:07 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA7 | the Arabic aliases written as raw UTF-8 bytes | KILLED (101 failed, 27 passed, 15 warnings in 6.32s) | test_ar0_arabic_aliases_in_the_lines_file, test_ar0b_lines_file_ascii_and_loads, test_ar0c_loader_reads_fourteen_lines | [pyt] tag=inc-m1a-mut-ma7 start=2026-11-17 12:57:14 end=2026-11-17 12:57:21 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Use |
| MA8 | apply_resolution keeps the typed Arabic as search_query | KILLED (21 failed, 107 passed, 15 warnings in 5.11s) | test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arB], test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arBya], test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_latB] | [pyt] tag=inc-m1a-mut-ma8 start=2026-11-17 12:57:28 end=2026-11-17 12:57:34 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA9 | Libre concentrations left as [EDP] | KILLED (2 failed, 126 passed, 15 warnings in 4.84s) | test_seed1_data_rows, test_seed1_typed_names_resolve[YSL | [pyt] tag=inc-m1a-mut-ma9 start=2026-11-17 12:57:40 end=2026-11-17 12:57:46 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Use |
| MA10 | (added) the core strip ignores the Arabic phrases | KILLED (9 failed, 119 passed, 15 warnings in 4.95s) | test_ar5_arabic_concentration_phrase_resolves[bleu_waw_edp], test_ar5_arabic_concentration_phrase_resolves[bleu_ya_edp_ya], test_ar5_arabic_concentration_phrase_resolves[edp_waw_lexicon] | [pyt] tag=inc-m1a-mut-ma10 start=2026-11-17 12:57:53 end=2026-11-17 12:57:58 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Us |
| MA11 | (added) the typed concentration ignores the Arabic phrases | KILLED (7 failed, 121 passed, 15 warnings in 5.15s) | test_ar5_arabic_concentration_phrase_resolves[bleu_waw_edp], test_ar5_arabic_concentration_phrase_resolves[bleu_ya_edp_ya], test_ar5_arabic_concentration_phrase_resolves[edp_waw_lexicon] | [pyt] tag=inc-m1a-mut-ma11 start=2026-11-17 12:58:05 end=2026-11-17 12:58:11 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Us |
| MA12 | (added) single_concentration written on every line | KILLED (1 failed, 127 passed, 15 warnings in 4.81s) | test_seed1_data_rows | [pyt] tag=inc-m1a-mut-ma12 start=2026-11-17 12:58:18 end=2026-11-17 12:58:23 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Us |
| MA13 | (added) the Arabic Chanel house alias dropped | KILLED (2 failed, 126 passed, 15 warnings in 4.90s) | test_ar0_arabic_aliases_in_the_lines_file, test_seed1_data_rows | [pyt] tag=inc-m1a-mut-ma13 start=2026-11-17 12:58:30 end=2026-11-17 12:58:36 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Us |

All 13 KILLED (MA1-MA9 the spec's, MA10-MA13 added). MA2 is killed only by the data rows (AR-0 and SEED-1 data): with the WAW alias the OSA-1 fuzzy match still resolves the YA spelling, as the facts measured, so the explicit-alias data row is the M1R-3 pin. MA7 also raised UnicodeDecodeError in two data rows (they decode the file as ASCII); it is killed by AssertionError (AR-0b asserts 0 bytes > 127; 80+ resolver rows assert). After the last mutant: resolver 9b8e8247..., data 98c02e04... (equal to the prototype copies); the mutation lock was created and removed.

## Step 7: comm set at base (real worktree)
- list: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/e8bbde46-f2b1-4f83-9479-dcdff600313a/scratchpad/INC-M1a/comm/comm_list.txt (156 files, 7 chunks of <= 25: comm/chunk_01..07.txt); reasons: comm/comm_reasons.tsv; dropped: comm/comm_dropped.tsv (tests/conftest.py, two non-test helpers, the four test_precommit_hook*.py).
- union: module / symbol grep (product_resolver, fragrance_lines, LINES_PATH, ENABLE_PRODUCT_RESOLVER, resolve_lexicon, _link_key, ENABLE_URL_LINK_RESULT, _typed_name, _typed_image_text, _resolve_explicit_pair) + lexicon readers + facts Q8 seed and its source-scanning list + the named source-scanning / digest / hermeticity pins + CLAUDE.md readers (grep and the import graph; GREEN edits CLAUDE.md) + every glob / dir walker (app/, data/, tests/: they read the new RED file). No SmartCompareApp-scanning tests (no client-visible change). No NETWORK_FLAKY_EXCLUDE list exists (the 6104eebd base record says so too).
- [pyt] tag=inc-m1a-comm-base-c01 start=2026-11-17 12:59:10 end=2026-11-17 12:59:42 elapsed=32s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c01.log
- [pyt] tag=inc-m1a-comm-base-c02 start=2026-11-17 12:59:49 end=2026-11-17 13:02:02 elapsed=134s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c02.log
- [pyt] tag=inc-m1a-comm-base-c03 start=2026-11-17 13:02:09 end=2026-11-17 13:02:57 elapsed=47s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c03.log
- [pyt] tag=inc-m1a-comm-base-c04 start=2026-11-17 13:03:04 end=2026-11-17 13:04:46 elapsed=103s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c04.log
- [pyt] tag=inc-m1a-comm-base-c05 start=2026-11-17 13:04:53 end=2026-11-17 13:06:44 elapsed=111s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c05.log
- [pyt] tag=inc-m1a-comm-base-c06 start=2026-11-17 13:06:51 end=2026-11-17 13:07:43 elapsed=52s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c06.log
- [pyt] tag=inc-m1a-comm-base-c07 start=2026-11-17 13:07:50 end=2026-11-17 13:08:07 elapsed=17s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a\comm\base_c07.log
- base failures (16 ids):
```
ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
FAILED tests/test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
FAILED tests/test_s81_s07_meas_harness.py::test_r35_fixtures
FAILED tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
FAILED tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
```
- Every one is in the INC-R1 base record at 6104eebd (harness/base_records/6104eebd.../8748c144....txt) EXCEPT tests/test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait (a later unit; failed on rounding: assert 0.42 >= 0.421, a timing flake that touches no resolver code). The rest are the known environmental ones (tiktoken cold cache, CRLF working copies on this box). Spec section 1.10 does not exist (deviation 1), so this list is the base record for GREEN.

## Step 8: restore check
- real worktree: HEAD 7f672cfe; manifest of 3626 tracked files equal before / after (7ef3013b...); git status only ?? tests/test_inc_m1a_resolver_fold.py.
- scratch worktree removed with git worktree remove --force (no node_modules junction in it); git worktree list no longer shows it. No pytest / gate process of this unit alive afterwards.

## Deviations and findings for the gate
1. Spec section 1.10 (the pre-existing base failures) does not exist; section 1 ends at 1.7. The comm-set base list above stands in.
2. The prompt's runner (pyt.py) refuses direct calls; gate.py was used for every run.
3. url_extraction_service._link_key (INC-U1, S97's file) reads resolve_lexicon and _typed_concentration with no flag of its own (reached only under ENABLE_URL_LINK_RESULT). The data and the Arabic-phrase change MOVE its key for page names that name a new seed line (Y, Hawas), a flanker (Aventus Cologne ...), Libre EDT or Arabic text. PIN-0 pins the unchanged lines' page keys; the moved ones are deliberate and must be listed in the gate (the spec names the file read-only, so no row asserts the new keys).
4. E-rows owed by GREEN (frozen INC-R1 rows the spec contradicts): test_inc_r1_resolver.py r05, r11 x2, r15, r21 g8 / g8b (step 5). The spec has no EXISTING PINS section.
5. AR-5d (PIN) pins that the Arabic phrases are read through category_gate.load_lexicon (a FRAGRANCE_LEXICON_PATH seam without them -> not EDP). A GREEN that reads data/fragrance_lexicon.json by a fixed path would fail it; the spec says only 'reads them from the lexicon'.
6. PIN-0 pins the resolver word tables (CONCENTRATION_PHRASES, GENERIC_WORDS, QUALIFIER_WORDS) unchanged (M1R-2 no second table; spec 1.2.4 matches the flanker before the drop, it does not change the sets).
7. AR-3 golden: the facts Q4 probe used the query 'Bleu de Chanel EDP'; the resolved full_name is 'Chanel Bleu de Chanel EDP'. Measured at base with the real modules: the same 4-title selection set and showable count 13, so the frozen golden holds (PIN row green at base).
8. AR-4 with ENABLE_IMAGE_GUARD_WORDS ON compares the identity with query_words cleared and relevance_kwargs without 'typed': the typed carrier is the Arabic text by design (I-8); the verdicts per title are equal (facts Q5).

## Open questions
1. 'Libre Le Parfum' and 'YSL Y Le Parfum': the flanker 'Le Parfum' contains the concentration word parfum, which D2 strips before D7, so with the prototype both stay medium. Spec 1.2.4 lists only generic / qualifier words; no row asserts these. Rule whether GREEN must resolve them to the flanker.
2. 'YSL Y Elixir' resolves with the prototype to (Yves Saint Laurent, Y, Elixir, flanker Elixir) through the concentration-flanker rule, as 'Stronger With You Parfum' does; not asserted.
3. Spec 1.2.1 asks for a product_resolver accessor for later readers of the Arabic spellings; no name is specified, so no row pins one.
4. The single-letter alias 'y' fuzzy-matches a 1-2 letter typed token within OSA 1; PIN-1 found no change on the R4 typed set, but the adversary should probe short tokens.

## PROOF ON THE PHONE (from the spec / facts; not done here)
With ENABLE_PRODUCT_RESOLVER ON on web: type the two Arabic placeholder examples (Dior Sauvage EDP / Bleu de Chanel EDP in Arabic) and see the Latin-identity price and picture equal to the Latin-typed pair; backing check: the [RESOLVE] line shows a=lexicon/high b=lexicon/high and no model call. Merged code is 'merged, NOT yet proven' until then.

# INC-M1a GREEN REPORT (Claude Opus 5.5, 2026-11-17)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-m1a, branch fix/inc-m1a-resolver-fold (already existed at main 9bc13109; no checkout -b run). HEAD 06deda559bc1bdebf249edf3b23c072e5b37956b (one commit on 9bc13109). Written through python.

## Files (sha256 after; before from INC-M1a_green/before/)
- app/services/product_resolver.py: +139 -7; before cb8cce491f8dbbb5c7080fc115ef94e85e005250036ecad7345d8b0769d3ce82; after 88c3276b4b94f407cb3cfeb3a1516bab8658f8a945f694627e25f8f2f379d7a7
- data/fragrance_lines.json: +9 -7; before b63e8c9b553594d24ca8ad7343640be01da6736d01a6bd79eb9b9bdde906fc32; after 24ad79b52ba192dbcca417ddb991e59b924624c9c5d2a5bfffef0057f2df564f
- CLAUDE.md: +2 -1; before 2c4b8fd71864ba1f3bac1ece794a1cf95d6a057a1d11b35bd5b898f6c8d99259; after 9b68487720c50381869bf3f349245debd33af074c0f71d98f92289924a8d2bf4
- tests/test_inc_r1_resolver.py: +63 -11; before f9402b1ab7c9162762ab314cb3cd0cbb30b8d6be6641f8d238416105b379bd21; after 1a97be3c18efd88c826d2218a3db2db65c696f37146eff05dc10afb9414c0ff9
- tests/test_inc_m1a_resolver_fold.py: +1064 -0; before (new, frozen RED); after 63fc6a67b082317f3346d702a97d1880e2ca4dca8c9df66314b212d7cef0cfd3
- RED file re-hashed at start and end: 63fc6a67b082317f3346d702a97d1880e2ca4dca8c9df66314b212d7cef0cfd3 (unchanged).

## Runs
- [pyt] tag=inc-m1a-green-unit-on2 start=2026-11-17 13:47:45 end=2026-11-17 13:47:56 elapsed=11s bound=600s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\unit_on2.log
- [pyt] tag=inc-m1a-green-unit-off2 start=2026-11-17 13:47:57 end=2026-11-17 13:48:08 elapsed=11s bound=600s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\unit_off2.log
- [pyt] tag=inc-m1a-green-comm-c01 start=2026-11-17 13:20:56 end=2026-11-17 13:21:28 elapsed=32s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c01.log
- [pyt] tag=inc-m1a-green-comm-c02 start=2026-11-17 13:21:29 end=2026-11-17 13:23:42 elapsed=132s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c02.log
- [pyt] tag=inc-m1a-green-comm-c03 start=2026-11-17 13:23:42 end=2026-11-17 13:24:31 elapsed=49s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c03.log
- [pyt] tag=inc-m1a-green-comm-c04 start=2026-11-17 13:24:32 end=2026-11-17 13:26:14 elapsed=102s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c04.log
- [pyt] tag=inc-m1a-green-comm-c05 start=2026-11-17 13:26:15 end=2026-11-17 13:28:07 elapsed=112s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c05.log
- [pyt] tag=inc-m1a-green-comm-c06 start=2026-11-17 13:28:08 end=2026-11-17 13:29:00 elapsed=52s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c06.log
- [pyt] tag=inc-m1a-green-comm-c07 start=2026-11-17 13:29:01 end=2026-11-17 13:29:18 elapsed=17s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\comm\head_c07.log
- [pyt] tag=inc-m1a-green-tree start=2026-11-17 13:29:54 end=2026-11-17 13:47:21 elapsed=1047s bound=1800s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_green\tree.log

## Comm set
156 files / 7 chunks (INC-M1a/comm/chunk_01..07); re-derived grep at HEAD (regrep.txt, 15 files) all inside. HEAD failures (15):
- tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
- tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
- tests/test_s81_s07_meas_harness.py::test_r35_fixtures
- tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
- tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
Base (RED report, 16 ids) minus HEAD = test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait (the timing flake; passed at HEAD). branch-only-NEW = EMPTY.

## Whole tree, one process
- 20 failed, 32057 passed, 56 skipped, 124 deselected, 39 xfailed, 575 warnings, 2 errors in 1038.84s (0:17:18)
- failed ids at HEAD: 22; not in INC-H2_green/tree_head_failed.txt: NONE

## E-rows: see PR_BODY.md (E1-E5)

## Deviations
1. D5 one-character alias tokens match only exactly (app/services/product_resolver.py::_token_distance). Not in the spec or the prototype: added because the M1R-11 (d) probe on the new data (probe_short.py / probe_short.txt) found false highs: YSL L'Homme, YSL B, YSL by, YSL X, YSL 1, YSL Ya, YSL Yo and YSL + a one-letter Arabic token all resolved to (YSL, Y, EDT) high/lexicon. After the rule (probe_short_after.txt) only typed Y / Y EDP / YSL Y / Saint Laurent Y / YSL Y EDP / YSL Y Elixir resolve to Y. No base alias has a one-character token (PIN-1 green); the rule also applies to the model-arm line guard for a one-character line token (stricter).
2. The CI-order set is the whole tree in one process at bound 1800 (the gate's module-state rule: the unit adds _AR_PHRASES_MEMO, reset by _reset_resolver_state) instead of a 1200 s subset.
3. The fourteen client fences NOT MEASURED: no SmartCompareApp/node_modules junction in the worktree.
4. Spec section 8.1 does not exist; the CLAUDE.md row follows spec 1.5 + gate section 4: one new bullet inside the INC-R1 block before its Owner steps, plus the in-place rewrite of the INC-R1 stated-limits sentence (12 seeded lines / Arabic only through the model arm).
5. A docstring-only edit of _arabic_concentration landed after comm chunk c01 ran (c02-c07 and the tree ran on the final bytes).
6. The prompt names two RED files; the frozen RED set is one file (tests/test_inc_m1a_resolver_fold.py).

## Open questions
1. A bare typed 'Y' (or 'Y EDP') resolves to YSL Y high (an exact alias with no house typed). Rule whether a single-letter line needs a typed house or a pair context.
2. Arabic Elixir and an Arabic Le Parfum are not in the lexicon, so they are not read (stated limit).

## PROOF ON THE PHONE: see PR_BODY.md (merged, NOT yet proven).

# INC-R1 RESOLVE-OR-ASK: GREEN report (GREEN round; Opus 5.5 GREEN agent of the S95-FIX lane; 2026-11-15)

Unit INC-R1 (flag ENABLE_PRODUCT_RESOLVER; knobs PRODUCT_RESOLVER_TIMEOUT_SECONDS, PRODUCT_RESOLVER_ASK). Base 6104eebd7020cc009589b87afb4a73eb8aa5434d (main after #407 INC-I1; GC-15). Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-r1, branch fix/inc-r1-resolve-or-ask, HEAD 1860fbe7f76dbd73470b8164be411d251c70d140 (one commit, not pushed, no PR). Binding: GATE_INC_R1 (GC-1..GC-17), RULINGS_INC_R1 (R1-R1..R1-R31), the review's corrections, the spec (0676c198...). Every pytest ran through <SP>/harness/gate.py (the runner itself never called), one at a time, by the sequential driver <SP>/INC-R1_green/seqrun.py; nothing waited inside a runner. Nothing here says a production problem is fixed: the unit is "merged, NOT yet proven" once merged, until the owner's phone proof (H6); a green suite is not that proof.

## 0. STEP 0 (GC-16), before any edit

(a) The two frozen RED files re-hashed (e47fa219..., 9c30052f...: equal) and re-run at 6104eebd: the gated state (195 failed, every one an AssertionError; 51 passed; the node set and every per-node state identical to the RED round's inc-r1-red-base2):

    195 failed, 51 passed, 17 warnings in 14.09s
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 7 attempt(s) from 7 node(s)
    [pyt] tag=inc-r1-green-red-base start=2026-11-15 21:44:12 end=2026-11-15 21:44:27 elapsed=15s bound=600s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-red-base.log
    classification (junit): counts {'failed': 195, 'passed': 51}; failure classes {'AssertionError': 195}; the 246-node set and every per-node state equal the RED round's red_base2.json

(b) The comm set re-derived at 6104eebd by the spec's union rule (<SP>/INC-R1_green/comm_set_green.py; git ls-tree + cat-file over the base blobs): 785 test files at 6104eebd; union 502 files (class sizes {'a_module_ref': 259, 'a_symbol_ref': 103, 'a_app_main_or_testclient': 164, 'b_edited_test_support_importers': 13, 'c_source_scanners': 297, 'c_named_pins': 8, 'd_claude_md_readers': 7, 'e_data_readers': 87, 'g_client_scanners': 29, 'h_red_and_green_amendments': 7, 'i_red_list_union': 499}) MINUS the four tests/test_precommit_hook*.py; delta vs the RED's 499: +3 ['tests/test_inc_i1_noon_and_wiring.py', 'tests/test_inc_i1_picture_must_match.py', 'tests/test_retailer_quotes.py'] (the two INC-I1 test files, which import structured_comparison_service / read app source, and tests/test_retailer_quotes.py, caught by the widened symbol regex `SITES\b` through RETAILER_QUOTE_SITES: kept, harmless); none of the RED's 499 dropped; 279 files left out; list <SP>/INC-R1_green/comm_list.txt (sha256 8748c1448e50573f4f2f3934df2c227b793216607ed017859a6543f06e9c606d), reasons comm_reasons.tsv.

(c) The FRESH BASE PASS of that set at 6104eebd, chunk by chunk (the RED's 20-chunk map unchanged + c21 for the files new at 6104eebd), stored as the new base record <SP>/harness/base_records/6104eebd7020cc009589b87afb4a73eb8aa5434d/8748c1448e50573f4f2f3934df2c227b793216607ed017859a6543f06e9c606d.{txt,files,header.txt,pyt.log} (totals {'passed': 25291, 'failed': 24, 'error': 2, 'skipped': 88}):

    2 failed, 806 passed, 25 warnings in 40.76s
    [pyt] tag=inc-r1-gbase-c01 start=2026-11-15 21:46:58 end=2026-11-15 21:47:40 elapsed=42s bound=1200s status=FAIL rc=1
    1211 passed, 5 deselected, 31 warnings in 37.62s
    [pyt] tag=inc-r1-gbase-c02 start=2026-11-15 21:47:47 end=2026-11-15 21:48:25 elapsed=39s bound=1200s status=OK rc=0
    1056 passed, 1 skipped, 2 deselected, 15 warnings in 60.23s (0:01:00)
    [pyt] tag=inc-r1-gbase-c03 start=2026-11-15 21:48:32 end=2026-11-15 21:49:34 elapsed=61s bound=1200s status=OK rc=0
    434 passed, 1 skipped, 3 deselected, 17 warnings in 12.93s
    [pyt] tag=inc-r1-gbase-c04 start=2026-11-15 21:49:40 end=2026-11-15 21:49:54 elapsed=14s bound=1200s status=OK rc=0
    2026 passed, 1 skipped, 14 warnings in 58.84s
    [pyt] tag=inc-r1-gbase-c05 start=2026-11-15 21:50:01 end=2026-11-15 21:51:01 elapsed=60s bound=1200s status=OK rc=0
    1549 passed, 1 skipped, 5 deselected, 22 warnings in 77.93s (0:01:17)
    [pyt] tag=inc-r1-gbase-c06 start=2026-11-15 21:51:08 end=2026-11-15 21:52:27 elapsed=79s bound=1200s status=OK rc=0
    562 passed, 1 xfailed, 17 warnings in 37.30s
    [pyt] tag=inc-r1-gbase-c07 start=2026-11-15 21:52:34 end=2026-11-15 21:53:12 elapsed=38s bound=1200s status=OK rc=0
    335 passed, 17 warnings in 14.72s
    [pyt] tag=inc-r1-gbase-c08 start=2026-11-15 21:53:19 end=2026-11-15 21:53:34 elapsed=16s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-gbase-c09 waited=26s (another lane is queued)
    3639 passed, 2 skipped, 10 deselected, 3 warnings in 27.01s
    [pyt] tag=inc-r1-gbase-c09 start=2026-11-15 21:54:02 end=2026-11-15 21:54:30 elapsed=28s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-gbase-c10 waited=63s (another lane is queued, another lane took the slot, another lane's run is live)
    2 failed, 518 passed, 21 skipped, 3 deselected, 21 warnings in 35.67s
    [pyt] tag=inc-r1-gbase-c10 start=2026-11-15 21:55:35 end=2026-11-15 21:56:12 elapsed=37s bound=1200s status=FAIL rc=1
    [gate] tag=inc-r1-gbase-c11 waited=110s (another lane is queued, another lane's run is live)
    684 passed, 6 skipped, 4 deselected, 1 xfailed, 17 warnings, 2 errors in 29.60s
    [pyt] tag=inc-r1-gbase-c11 start=2026-11-15 21:58:03 end=2026-11-15 21:58:34 elapsed=31s bound=1200s status=FAIL rc=1
    [gate] tag=inc-r1-gbase-c12 waited=99s (another lane is queued, another lane's run is live)
    923 passed, 1 skipped, 365 warnings in 155.98s (0:02:35)
    [pyt] tag=inc-r1-gbase-c12 start=2026-11-15 22:00:15 end=2026-11-15 22:02:52 elapsed=158s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-gbase-c13 waited=110s (another lane is queued, another lane's run is live)
    1891 passed, 17 warnings in 89.19s (0:01:29)
    [pyt] tag=inc-r1-gbase-c13 start=2026-11-15 22:04:44 end=2026-11-15 22:06:15 elapsed=91s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-gbase-c14 waited=152s (another lane is queued, another lane's run is live)
    7 failed, 2068 passed, 18 warnings in 64.15s (0:01:04)
    [pyt] tag=inc-r1-gbase-c14 start=2026-11-15 22:08:48 end=2026-11-15 22:09:53 elapsed=65s bound=1200s status=FAIL rc=1
    9 failed, 2226 passed, 137 warnings in 111.87s (0:01:51)
    [pyt] tag=inc-r1-gbase-c15 start=2026-11-15 22:10:00 end=2026-11-15 22:11:54 elapsed=114s bound=1200s status=FAIL rc=1
    4 failed, 1744 passed, 1 xfailed, 49 warnings in 50.51s
    [pyt] tag=inc-r1-gbase-c16 start=2026-11-15 22:12:00 end=2026-11-15 22:12:53 elapsed=52s bound=1200s status=FAIL rc=1
    1219 passed, 17 warnings in 64.40s (0:01:04)
    [pyt] tag=inc-r1-gbase-c17 start=2026-11-15 22:12:59 end=2026-11-15 22:14:05 elapsed=66s bound=1200s status=OK rc=0
    492 passed, 8 skipped, 10 deselected, 26 warnings in 53.44s
    [pyt] tag=inc-r1-gbase-c18 start=2026-11-15 22:14:12 end=2026-11-15 22:15:07 elapsed=55s bound=1200s status=OK rc=0
    555 passed, 8 deselected, 35 xfailed, 17 warnings in 45.63s
    [pyt] tag=inc-r1-gbase-c19 start=2026-11-15 22:15:13 end=2026-11-15 22:16:00 elapsed=47s bound=1200s status=OK rc=0
    1225 passed, 10 skipped, 17 warnings in 33.13s
    [pyt] tag=inc-r1-gbase-c20 start=2026-11-15 22:16:07 end=2026-11-15 22:16:41 elapsed=34s bound=1200s status=OK rc=0
    128 passed in 3.16s
    [pyt] tag=inc-r1-gbase-c21 start=2026-11-15 22:16:48 end=2026-11-15 22:16:52 elapsed=4s bound=1200s status=OK rc=0

Base FAILED / ERROR ids (26):

    tests/test_auth_interceptor.py::test_sign_in_with_social_exception
    tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
    tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
    tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
    tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
    tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
    tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
    tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
    tests/test_s81_s07_meas_harness.py::test_r35_fixtures
    tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
    tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
    tests/test_s81_s18b_store_label.py::test_r2_table_shape
    tests/test_s81_s19_gap_queue.py::test_r15_hygiene
    tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
    tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
    tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
    tests/test_s81_s24_auth_throttle.py::test_r92_hygiene

Versus the 731bcddf record 8c08a677... (27 ids): new at 6104eebd: none; gone at 6104eebd: ['tests/test_retro_w0_4.py::test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag[scs._fetch_page_price]']

(d) The branch fix/inc-r1-resolve-or-ask was created from 6104eebd (the one git branch command of this round), before any edit.

## 1. Files (byte copies first: <SP>/INC-R1_green_before/ with manifest.json)

| path | +/- | sha256 before | sha256 after |
|---|---|---|---|
| .github/black-clean-paths.txt | +3 / -0 | a56c73324451137b3671dd58397cd28984fd008139dc643c5b2791b9f9a53908 | daba56601af8944137e94f9a8c6a0e66a3591b990c43a5535bd38ffe80fd4149 |
| CLAUDE.md | +7 / -1 | 45724a6f91c170323202d7b89cee8ec683b8236b1c2fb5d42735d8dde161943e | 14c2ae8544ee77c247970b6b644e420acf50269b4b3dd9c591c1487b888f8061 |
| app/api/text_routes.py | +89 / -0 | f6540988d8185a0387659a59ff8eac6953ebbdde1b5f101a1ac60bc1c5a6b5ba | 72b8b33ecb892148f1294a5cd71bf9412c6e5246964fc787106e9157dfce45d0 |
| app/middleware/error_handler.py | +59 / -0 | a6af83ebcd1b2594f8e9812f1de4f4e506dda51358b1dd790f08a12b0ce3a1bd | e2b5fdf3df2001984468e5c0ca7be16e58e1af66543ce52c8bc6cfcf4fbc3361 |
| app/services/llm_router.py | +4 / -2 | 9c14b241cf4a9beb4732c36490e14ddc40376ab5849eb9f77f0338966d8733d2 | 2192dd55a9c9e00715547a0b43077e9fc5b0845fb704f1b6aacf82c973c3752e |
| app/services/product_resolver.py | +1431 / -0 | (new) | ed1e8a7b23ecaad85f85f2bfb9ecddaa2fb7edce5a153e51644b6dcbab78af0f |
| app/services/structured_comparison_service.py | +63 / -2 | de8c77ce164620d6e9de376edb47ce27f30a884fb7e2e05e65efee61ccb23bc1 | acd5b4340ff14eefc1b4f45be984f54fbdaea14f116479cf76f34fe48d004ad2 |
| data/fragrance_lines.json | +18 / -0 | (new) | 2fbf6caef382049caab504a52eab19ca6d736d82fdbcac68e30582a090d60d53 |
| tests/test_inc_r1_resolver.py | +1907 / -0 | (new) | e47fa219e60d673c9d0aaa042e517ddb48d507a13622bde944633690fc6ade70 |
| tests/test_inc_r1_seam.py | +1440 / -0 | (new) | 9c30052f0cc3f9aa7a2058e70f5feafafe7c1d2a20f12264ea106178ab6a539f |
| tests/test_s75_fanout_identity.py | +3 / -1 | a4198be47a3fa75a79f9b635528d2212c073c2efc97f802fddd913be04f0e769 | 222beb38a0015d524937c37c08bed2b119ddd313cca01cef3d86f5b7afb9dbcc |
| tests/test_s81_kb_schema.py | +4 / -2 | af8ccdb47c8db47d306358daa56f4d0cb99898e83deecd13cda2899e0fc9d5af | 792fe75ba0358f330fd4be7c18fd434efc8263e3f66db1fff8d9dd12138c363f |
| tests/test_s81_s06_anthropic_router.py | +4 / -1 | d130bea8201a88d3d6c647d3ce62fa05cdfb6825454cd8cf3255abfac24f12e2 | 95304d8207b5512cec4ade66c57879388ff353d878ad3037d77fc515614cd65d |
| tests/test_s81_s06_router_gate_rows.py | +8 / -5 | 16757c30a0a7611efacc731776e39e3cb8a0cb85da85c65e01de1858eb29e21e | 2eaf414411a2ce0817075d3ad14ca436f13b74861607e0fe8520592692c858fe |
| tests/test_s81_s07_meas_harness.py | +2 / -1 | 26a67c967c97281dec57d32e47832d453c7c049943b5685b1ab2e969a50c5876 | 04944dee8cd0adbb220e81801da301bd5ad5ef6f9b40b95cc4b3e057ef32c363 |
| tests/test_s81_s07c_role_fix.py | +2 / -1 | 52577c1308571dabee044cd19d009920622e3d4832a0266b66bd297e62f0992c | 797d5060d1de46f6692e92c1121e27633f7090c028883478c43a558dc38d2b02 |
| tests/test_s81_s22b_self_critique_retire.py | +1 / -0 | 9d8e0e35f4fcc132ae717a63c5b88975b6246762ca0bc4d766a43f208829ee69 | da2d5ad8f14b10fb4d110cd00f92d556d1e022dd39c15113cf35c28cf6eac659 |

## 2. What was built (the spec change list as amended)

- C1 NEW data/fragrance_lines.json: the exact spec 2.2 content (12 lines, ASCII, LF, 2,458 bytes).
- C3 NEW app/services/product_resolver.py (ASCII, LF, black 26.5.1 clean, ruff tier clean): the flag and the two knobs (house idiom / _float_knob semantics / R1-R28 OFF values), Side / Resolution, resolve_lexicon (D1-D12 as amended by R1-R4 qualifiers, R1-R5 span-based size removal, R1-R8 pair fragrance context, R1-R11 + GC-5 Q2, R1-R13 OSA; the compiled index memoised on (the load_lexicon() object, the lines-file (resolved path, mtime_ns, size)), an unreadable / invalid lines file = no lines with ONE WARNING per file state), the model arm (R1-R6: only under llm_router.decide('text') == 'anthropic'; R1-R3 (d) skip; ONE routed call in the literal disambiguate form, the two bare census spreads, asyncio.wait_for on PRODUCT_RESOLVER_TIMEOUT_SECONDS; the per-process LRU keyed on (decision, normalised a, normalised b), parsed answers only, TTL 86,400 s, 2,000 entries), the guard (a)-(d) (R1-R4 qualifiers allowed outside the window; R1-R23 concentration), the decision (R1-R3 (b), R1-R15), ONE INFO [RESOLVE] line with cached=<0|1> (R1-R16; a typed-token brand logs '-', C-14), apply_resolution (C-4: no doubled concentration), refusal_result (the gate_refusal_body key order + candidates last), valid_candidates, http_detail_extras (flag FIRST), is_ask_refusal (flag FIRST; the route twins' predicate), _reset_resolver_state. Never raises (one WARNING 'resolver failed class=...').
- C2 EDIT app/services/llm_router.py (R1-R2 / R1-R7): SITES['resolve'] = SiteSpec('text', 384, None, True) and the comment above SITES; route() byte-equal (MON1's G01 digest green unedited); no schema, no NO_ESCALATION_SITES.
- C4 EDIT app/services/structured_comparison_service.py: the import (after the category_gate import, beside INC-I1's image_relevance import which stays); `_rv_fragrance_pair = False` beside each `_profile_task = None`; the two hooks at the end of each explicit-pair branch, each opening with its own `if _product_resolver.product_resolver_enabled():` (the sync / stream lines carry distinct trailing comments so a mutant edit matches once); the shared hook body `_resolve_explicit_pair` (usage tracked through self._track_gpt_cost before the refusal is built, the ask refusal returned (sync) / yielded as ('error', ...) then return (stream), total per C-7: any exception restores the base Step-1 dicts with ONE WARNING by type); both _resolve_pair_category calls take parser_path=_parser_path or _rv_fragrance_pair (R1-8). INC-I1's import and image-task keyword untouched (GC-17).
- C5 EDIT app/api/text_routes.py: the import; the 400 builder's extras (http_detail_extras, setdefault after the S81-20 clause); the ask-exit twins of the S81-20 exits (R1-R9 / R1-R10 / GC-5 Q6): _resolver_ask_exit (POST / GET, checked BEFORE the generic failure arm, so the ask never takes the no-keys refund) and _resolver_stream_settle (scheduled from the event generator's finally by one fire_and_forget, no await there), each: the S81-10 budget (ENABLE_FRAGRANCE_ONLY_GATE ON only), ONE refund with the consume's keys (label usage_refund.<route>.resolver:placeholder_identity), the count once, ONE failure row with error_message = the ask sentence, the 400 through _surface_comparison_failure; no save, no lifetime. No route function, signature, docstring or response model changed (T23).
- C6 EDIT app/middleware/error_handler.py: _product_resolver_keys_enabled (local one-liner), _RESOLVER_CONCENTRATIONS, _RESOLVER_CANDIDATE_KEYS, _resolver_candidates; the block after the S81-20 block: the refusal marker FIRST, then the flag (R1-R18 / RC-2), reason by setdefault, candidates only when valid (dropped whole otherwise).
- C8 CLAUDE.md (CRLF kept): the INC-R1 block after the INC-I1 block, one blank line before it and the blank line before '## Tests' kept; the pointer sentence in the '**Feature Flags:**' line after INC-I1's (R1-R12, GC-17). All added text ASCII.
- C9 .github/black-clean-paths.txt: app/services/product_resolver.py, tests/test_inc_r1_resolver.py, tests/test_inc_r1_seam.py after INC-I1's three lines (R1-R17, GC-17).
- C7 the six E-rows of GC-4 (E1-E6), each the smallest edit; the black-allowlisted E2 file stays black-clean; plus E5b, E5's companion re-pin in tests/test_s81_kb_schema.py (see the deviations).

## 3. Gates at HEAD

RED files (flag exported ON; nothing exported):

    246 passed, 15 warnings in 10.45s
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=inc-r1-green-red-on start=2026-11-15 22:19:10 end=2026-11-15 22:19:21 elapsed=11s bound=600s status=OK rc=0 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-red-on.log
    246 passed, 15 warnings in 10.33s
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=inc-r1-green-red-off start=2026-11-15 22:19:27 end=2026-11-15 22:19:39 elapsed=11s bound=600s status=OK rc=0 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-red-off.log

Identity pins (spec 4.2) and the E-row files (G3 / G4):

    1 failed, 859 passed, 2 deselected, 17 warnings in 92.28s (0:01:32)
    [hermeticity] sentinel checked 860 test(s)
    [netguard] blocked 73 attempt(s) from 23 node(s)
    [pyt] tag=inc-r1-green-erows start=2026-11-15 22:19:54 end=2026-11-15 22:21:28 elapsed=94s bound=1200s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-erows.log
    981 passed, 2 skipped, 1 xfailed, 137 warnings, 2 errors in 43.72s
    [hermeticity] sentinel checked 984 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    [pyt] tag=inc-r1-green-llm start=2026-11-15 22:21:34 end=2026-11-15 22:22:19 elapsed=45s bound=1200s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-llm.log
    1 failed, 1098 passed, 17 warnings in 24.78s
    [hermeticity] sentinel checked 1099 test(s)
    [netguard] blocked 48 attempt(s) from 33 node(s)
    [pyt] tag=inc-r1-green-routes start=2026-11-15 22:22:26 end=2026-11-15 22:22:52 elapsed=26s bound=1200s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-routes.log
    1 failed, 1176 passed, 17 warnings in 72.81s (0:01:12)
    [hermeticity] sentinel checked 1177 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    [pyt] tag=inc-r1-green-claude start=2026-11-15 22:22:59 end=2026-11-15 22:24:14 elapsed=74s bound=1200s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-claude.log

FAILED / ERROR ids in the four sets: ['tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence', 'tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable', 'tests/test_s81_s07_meas_harness.py::test_r35_fixtures', 'tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content']; outside the fresh base record: none.

Static: py_compile 14 files rc=0
ruff E9,F63,F7,F82 14 files rc=0: All checks passed!
black 26.5.1 --check --diff 5 allowlisted files rc=0: 5 files would be left unchanged.
data/fragrance_lines.json json.loads ok version=1 lines=12 bytes=2458 non-ascii=0 CR=0
app/services/product_resolver.py bytes=54178 non-ascii=0 CR=0
added lines (vs 6104eebd) 5045, non-ASCII added lines 1

Comm set HEAD pass (504 files: the 502 + the two RED files in c21):

    [gate] tag=inc-r1-head-c01 waited=26s (another lane is queued, another lane's run is live)
    2 failed, 806 passed, 25 warnings in 33.71s
    [pyt] tag=inc-r1-head-c01 start=2026-11-15 22:25:04 end=2026-11-15 22:25:39 elapsed=35s bound=1200s status=FAIL rc=1
    1211 passed, 5 deselected, 31 warnings in 36.85s
    [pyt] tag=inc-r1-head-c02 start=2026-11-15 22:25:45 end=2026-11-15 22:26:23 elapsed=38s bound=1200s status=OK rc=0
    1056 passed, 1 skipped, 2 deselected, 15 warnings in 57.72s
    [pyt] tag=inc-r1-head-c03 start=2026-11-15 22:26:30 end=2026-11-15 22:27:29 elapsed=59s bound=1200s status=OK rc=0
    434 passed, 1 skipped, 3 deselected, 17 warnings in 12.48s
    [pyt] tag=inc-r1-head-c04 start=2026-11-15 22:27:36 end=2026-11-15 22:27:49 elapsed=13s bound=1200s status=OK rc=0
    2026 passed, 1 skipped, 14 warnings in 57.25s
    [pyt] tag=inc-r1-head-c05 start=2026-11-15 22:27:56 end=2026-11-15 22:28:54 elapsed=59s bound=1200s status=OK rc=0
    1549 passed, 1 skipped, 5 deselected, 22 warnings in 76.45s (0:01:16)
    [pyt] tag=inc-r1-head-c06 start=2026-11-15 22:29:01 end=2026-11-15 22:30:19 elapsed=78s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-head-c07 waited=502s (another lane took the slot, another lane's run is live)
    562 passed, 1 xfailed, 17 warnings in 36.22s
    [pyt] tag=inc-r1-head-c07 start=2026-11-15 22:38:42 end=2026-11-15 22:39:19 elapsed=37s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-head-c08 waited=16s (another lane is queued)
    335 passed, 17 warnings in 14.48s
    [pyt] tag=inc-r1-head-c08 start=2026-11-15 22:39:36 end=2026-11-15 22:39:52 elapsed=15s bound=1200s status=OK rc=0
    3639 passed, 2 skipped, 10 deselected, 3 warnings in 26.69s
    [pyt] tag=inc-r1-head-c09 start=2026-11-15 22:39:58 end=2026-11-15 22:40:26 elapsed=28s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-head-c10 waited=512s (another lane is queued, another lane took the slot, another lane's run is live)
    2 failed, 518 passed, 21 skipped, 3 deselected, 21 warnings in 35.11s
    [pyt] tag=inc-r1-head-c10 start=2026-11-15 22:49:00 end=2026-11-15 22:49:36 elapsed=36s bound=1200s status=FAIL rc=1
    [gate] tag=inc-r1-head-c11 waited=68s (another lane is queued, another lane's run is live)
    684 passed, 6 skipped, 4 deselected, 1 xfailed, 17 warnings, 2 errors in 29.57s
    [pyt] tag=inc-r1-head-c11 start=2026-11-15 22:50:46 end=2026-11-15 22:51:16 elapsed=31s bound=1200s status=FAIL rc=1
    [gate] tag=inc-r1-head-c12 waited=37s (another lane is queued, another lane's run is live)
    923 passed, 1 skipped, 365 warnings in 154.84s (0:02:34)
    [pyt] tag=inc-r1-head-c12 start=2026-11-15 22:51:54 end=2026-11-15 22:54:31 elapsed=157s bound=1200s status=OK rc=0
    1891 passed, 17 warnings in 88.52s (0:01:28)
    [pyt] tag=inc-r1-head-c13 start=2026-11-15 22:54:38 end=2026-11-15 22:56:08 elapsed=90s bound=1200s status=OK rc=0
    8 failed, 2067 passed, 18 warnings in 64.15s (0:01:04)
    [pyt] tag=inc-r1-head-c14 start=2026-11-15 22:56:15 end=2026-11-15 22:57:20 elapsed=65s bound=1200s status=FAIL rc=1
    9 failed, 2226 passed, 137 warnings in 111.66s (0:01:51)
    [pyt] tag=inc-r1-head-c15 start=2026-11-15 22:57:27 end=2026-11-15 22:59:21 elapsed=114s bound=1200s status=FAIL rc=1
    4 failed, 1744 passed, 1 xfailed, 49 warnings in 49.51s
    [pyt] tag=inc-r1-head-c16 start=2026-11-15 22:59:27 end=2026-11-15 23:00:18 elapsed=51s bound=1200s status=FAIL rc=1
    1219 passed, 17 warnings in 63.88s (0:01:03)
    [pyt] tag=inc-r1-head-c17 start=2026-11-15 23:00:25 end=2026-11-15 23:01:30 elapsed=65s bound=1200s status=OK rc=0
    492 passed, 8 skipped, 10 deselected, 26 warnings in 52.53s
    [pyt] tag=inc-r1-head-c18 start=2026-11-15 23:01:37 end=2026-11-15 23:02:31 elapsed=54s bound=1200s status=OK rc=0
    555 passed, 8 deselected, 35 xfailed, 17 warnings in 44.96s
    [pyt] tag=inc-r1-head-c19 start=2026-11-15 23:02:38 end=2026-11-15 23:03:24 elapsed=46s bound=1200s status=OK rc=0
    1225 passed, 10 skipped, 17 warnings in 33.29s
    [pyt] tag=inc-r1-head-c20 start=2026-11-15 23:03:30 end=2026-11-15 23:04:05 elapsed=34s bound=1200s status=OK rc=0
    374 passed, 14 warnings in 12.11s
    [pyt] tag=inc-r1-head-c21 start=2026-11-15 23:04:12 end=2026-11-15 23:04:25 elapsed=13s bound=1200s status=OK rc=0
    [gate] tag=inc-r1-head-c14r waited=73s (another lane took the slot, another lane's run is live)
    7 failed, 2068 passed, 18 warnings in 64.37s (0:01:04)
    [pyt] tag=inc-r1-head-c14r start=2026-11-15 23:07:32 end=2026-11-15 23:08:38 elapsed=66s bound=1200s status=FAIL rc=1
    [gate] tag=inc-r1-head-c16r waited=99s (another lane is queued, another lane's run is live)
    4 failed, 1744 passed, 1 xfailed, 49 warnings in 49.67s
    [pyt] tag=inc-r1-head-c16r start=2026-11-15 23:10:19 end=2026-11-15 23:11:10 elapsed=51s bound=1200s status=FAIL rc=1

First HEAD pass totals {'passed': 25536, 'failed': 25, 'error': 2, 'skipped': 88}: branch-only = ['tests/test_s81_kb_schema.py::test_s14_p06_identity_nodes_untouched[tests/test_s75_fanout_identity.py]'] (fixed by E5b, the deviation below). After E5b, c14 and c16 re-run at HEAD (tags inc-r1-head-c14r / c16r). Effective HEAD totals {'passed': 25537, 'failed': 24, 'error': 2, 'skipped': 88}; HEAD FAILED / ERROR ids (26): ['tests/test_auth_interceptor.py::test_sign_in_with_social_exception', 'tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully', 'tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest', 'tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction', 'tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence', 'tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable', 'tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only', 'tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene', 'tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]', 'tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]', 'tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]', 'tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]', 'tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]', 'tests/test_s81_s07_meas_harness.py::test_r35_fixtures', 'tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content', 'tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]', 'tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]', 'tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]', 'tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]', 'tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]', 'tests/test_s81_s18b_store_label.py::test_r2_table_shape', 'tests/test_s81_s19_gap_queue.py::test_r15_hygiene', 'tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf', 'tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first', 'tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene', 'tests/test_s81_s24_auth_throttle.py::test_r92_hygiene']. Base ids (26). branch-only-NEW = HEAD minus base: EMPTY. Fixed at HEAD (base minus HEAD): none.

CI-order set (GC-8: spec 7.1 G5 + C-11, alphabetical and reversed, one process each):

    2 failed, 2087 passed, 2 deselected, 86 warnings in 130.31s (0:02:10)
    [hermeticity] sentinel checked 2089 test(s)
    [netguard] blocked 97 attempt(s) from 32 node(s)
    [pyt] tag=inc-r1-green-ciorder start=2026-11-15 23:11:50 end=2026-11-15 23:14:02 elapsed=132s bound=1200s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-ciorder.log
    2 failed, 2087 passed, 2 deselected, 87 warnings in 128.75s (0:02:08)
    [hermeticity] sentinel checked 2089 test(s)
    [netguard] blocked 97 attempt(s) from 32 node(s)
    [pyt] tag=inc-r1-green-ciorder-rev start=2026-11-15 23:14:09 end=2026-11-15 23:16:20 elapsed=131s bound=1200s status=FAIL rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-ciorder-rev.log

FAILED / ERROR ids (both orders): ['tests/test_s81_s07_meas_harness.py::test_r35_fixtures', 'tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content']; outside the fresh base record: none.

Client fences (GC-10, once, last; after gate.py --wait-only; the junction checked: node_modules/@babel/core and node_modules/.bin/jest exist):

    [jest] version 29.7.0 (node v24.11.1)
    Test Suites: 1 failed, 13 passed, 14 total
    Tests:       4 failed, 236 passed, 240 total
    Time:        6.769 s
    FAIL __tests__/config/nativeBundle.w37.test.ts; the other 13 suites PASS
    FAILED (accepted drift node) W3-7 (d) runtime dependencies are imported, justified, or pending removal > d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
    FAILED (accepted drift node) session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k2 package-lock.json and node_modules resolve the five packages at or above those patches
    FAILED (accepted drift node) session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
    FAILED (accepted drift node) session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude
    [jest] tag=inc-r1-green-fences start=2026-11-15 23:17:47 end=2026-11-15 23:17:55 rc=1 log=C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-R1_green/logs/inc-r1-green-fences.log

D12 figure (not a test row): timeit (D12, not a test row): {"cold_first_pass_ms_10_names": 946.7, "warm_per_name_ms": 0.926, "runs": 20, "names": 10}; the cold first pass includes the first import of price_service / extraction_service / category_gate in a process that had not loaded them (in the app SCS loads them at import), the lexicon compile and the lines-file load

## 4. Deviations and interpretations (each with the reason it beats the alternative)

- E5b (a seventh E-row file, outside GC-9's list): the HEAD comm pass found ONE branch-only failure, tests/test_s81_kb_schema.py::test_s14_p06_identity_nodes_untouched[tests/test_s75_fanout_identity.py]: P06 pins the LF sha256 of the FY25 file, which E5 (binding, GC-4) edits. The smallest edit re-pins that one value (93c59246... -> e8c4bccf..., computed from the HEAD bytes with the pin's own LF read) and adds one docstring sentence, exactly as S81-06 (E11, RB6-11) and S81-20 (E8) did for their UNIT_ENV entries (the docstring records both). The two comm chunks holding the file and its importer (tests/test_s81_s22_gate_rows.py) were re-run at HEAD after the edit: base-record ids only. Dropping E5 instead would break GC-4; leaving P06 red would break the EMPTY branch-only rule.
- GC-5 Q6 label: the refund label of the sync twin is f'usage_refund.{where}.resolver:placeholder_identity' and of the stream settle 'usage_refund.text_stream.resolver:placeholder_identity' (the ruled marker after the house prefix, so the route stays visible in the label as in every other refund label; the log row label is log_search.<route>.resolver). If the gate meant the bare string as the label, it is a one-token edit.
- The two SCS hooks share one method body (_resolve_explicit_pair) instead of two inline copies: one place for the totality (C-7) and the usage tracking; each hook keeps its own flag test (M02 / M03 stay separately constructible) and its own return / yield. A mutant of the shared body (e.g. M08 'usage not tracked') now reddens both R13[rest] and R13[stream].
- is_ask_refusal (the route predicate) requires success False, code INSUFFICIENT_DATA, reason placeholder_identity, error == ASK_MESSAGE and a list under candidates, after the flag: an S81-20 refusal never reaches it (the result gate refuses a success body later, through its own exit). A flag flip between the orchestrator's ask and the route's check would send that one request through the generic failure arm (a coded 400 without the reason, refunded without keys): a stated limit.
- GC-5 Q2 implemented: 'stronger with you parfum' resolves HIGH (line Stronger With You, concentration Parfum, the flanker carried as the concentration, no candidates); a concentration-word flanker counts as sold only when no other flanker word was typed ('stronger with you intensely parfum' stays MEDIUM). No frozen row pins it.
- GC-5 Q3: the resolver-local EXTRA_NON_FRAGRANCE_WORDS = {pen, pens} beside category_gate.scan; the lexicon file is not edited.
- Guard (d): the allowed outside-window tokens are the brand's normalised tokens expanded by their alias groups AND by the line-file house aliases of the display house the brand names (so 'Bulgari Aqva ...' typed with the model brand 'Bvlgari' is not rejected for the spelling variant; R1-4c makes the line file the carrier of such spellings).
- Alias groups: a _BRAND_ALIAS_GROUPS form that normalises to more than one token ('d&g', 'v&r') is not used as a token form (it would otherwise add the single letters d / g / v / r to a group).
- D6: the house is searched as a contiguous run of the core outside the line window (not over the core with the window cut out, which would join the tokens on both sides of the window), the longest house first, the leftmost among the longest; the alias-group absorption runs whenever a house or a line matched.
- R1-R8 pair context: the chip, a concentration or lexicon form word on either side, or a lexicon-resolved partner (a second pass of the deterministic arm for the pending side); a partner resolved only by the model arm does not re-run the deterministic arm (the model answer already covers that side).
- The route exits log no extra INFO line: the orchestrator's [RESOLVE] ... outcome=ask line is the one backing line (R1-R26), so a RESOLVE filter sees exactly one line per comparison.
- Resolution carries an additive `cached` field and Side three internal fields (hint, context_pending, typed_brand) beside the spec 2.2 fields; resolve_lexicon takes a keyword-only `context` (the RED report's noted R1-R8 shape).
- Commit trailer: 'Co-Authored-By: Claude Opus 5.5' (GC-11, H12 (a)); the task template's 'Claude Fable 5.1' trailer was not used.

## 5. Open questions for the gate

- Q0 (E5b, recommended YES): rule the IDENTITY_NODES re-pin of tests/test_s81_kb_schema.py as E5's companion E-row (the S81-06 E11 / S81-20 E8 precedent) and widen GC-9's footprint by that one test file.
- Q1 (GC-5 Q6 wording): confirm the refund label form usage_refund.<route>.resolver:placeholder_identity (recommended, the house prefix kept) over the bare 'resolver:placeholder_identity'.
- Q2: the stated limit for a flag flip between the orchestrator's ask and the route twin (one request through the generic failure arm) is accepted as a limit (recommended) rather than carrying a marker key in the refusal dict (a new key the bundles would see).

## 6. NOT MEASURED / not run in this round

- The mutation table on the GREEN bytes: GC-3 assigns the sample (>= 8 mutants) to both adversaries; this round ran none (no exploratory runs, H12 (h)).
- The resolve site's live latency and the Claude answer quality (no network, no provider call: unmeasurable hermetically, SL8).
- The full jest suite (R1-R21: a backend unit with no client file runs the fourteen fences only).
- Nothing pushed, no PR opened, no merge (the orchestrator's, after the adversaries).

## 7. End state

    git status --short:
    (clean)
    HEAD 1860fbe7f76dbd73470b8164be411d251c70d140 on fix/inc-r1-resolve-or-ask
    git log --oneline -2:
    1860fbe7 fix(compare): INC-R1 RESOLVE-OR-ASK typed-pair resolver, dark behind ENABLE_PRODUCT_RESOLVER
    6104eebd Merge pull request #407 from KGRddhs/fix/inc-i1-picture-must-match
    RED files re-hashed at the end:
    e47fa219e60d673c9d0aaa042e517ddb48d507a13622bde944633690fc6ade70 tests/test_inc_r1_resolver.py
    9c30052f0cc3f9aa7a2058e70f5feafafe7c1d2a20f12264ea106178ab6a539f tests/test_inc_r1_seam.py

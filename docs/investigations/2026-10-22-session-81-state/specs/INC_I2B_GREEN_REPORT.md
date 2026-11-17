# INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER: GREEN report (S96 main lane, 2026-11-17 02:55-03:57 AST)

Unit: INC-I2b, three dark flags ENABLE_IMAGE_GUARD_WORDS (W), ENABLE_SHOP_PAGE_IMAGE (A), ENABLE_SHOPPING_THUMB_IMAGE (B), default OFF; FOCUS. Worktree sc-s96-i2b, branch fix/inc-i2b-guard-words-shop-tier. Gate GATE_INC_I2B.md, rulings I-1..I-19, spec V2, RED report read in full.

## Commits
- unit commit: aec760b5a6657765fed22f591a40d76fdd891435 (parent 5cd93c6a; the pre-commit hook ran: ruff "All checks passed!", black "4 files would be left unchanged"; no --no-verify; not pushed)
- G-8: git fetch origin main -> origin/main == 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9 (did not move): no merge. head = unit commit.
- git status --short at the end: empty.

## State inherited (verified first)
HEAD 5cd93c6a, branch right, tracked tree clean, the three frozen files byte-equal to the gate shas (c206cfd2..., 73e94432..., 510d42d7...), no mutation lock, node_modules junction present. Frozen shas re-checked before the commit: unchanged.

## G-1 addenda (tests/test_inc_i2b_addenda.py, ASCII 0 bytes > 127, LF, black + ruff clean, sha 5935d9e1...)
- AX-1 (parametrized S ON / OFF): both Arabic placeholders (chr code points), R OFF, brands Latin / Arabic / empty x 4 probe titles each: the check() reason equals the probe's base reason (arprobe/out_on.txt) with W unset AND equals it with W ON.
- AX-2: post-INC-M1 identity (Latin brand + line, Arabic typed product name): W unset and W ON, Latin titles None, Arabic titles brand (L15).
- AX-3: an Arabic title + an Arabic gift word (hdyh, hdaya; front and back), Arabic brand and empty brand: None with W unset and ON.
- AX-4 (parametrized rest / stream): GOLD4 pair through the INC-R1 seam FY25 harness, R + G + S ON, the real image cascade on the RED tier fakes, a recorder on the verdict call; W unset run vs W ON run: no "_typed_name" in the payload / events, the verdict call repr, ANTH / OAI calls or any log line; payload underscore keys equal the W unset run's; no IMG_ line holds sauvage / chanel / bleu / dior / edp. At the head (hasattr _typed_image_text) it also asserts the carrier on the fetch input == "Dior Sauvage EDP", the typed text in the guard relevance, and an [IMG_RELEVANCE] line exists (non-vacuous).
- AX-5 (GB-6): ENABLE_SHOP_PAGE_IMAGE read exactly 1 per Woo match call with a winner (A unset and A ON), 2 for two calls, 0 for a no-winner call.
- AX-6 (GB-7, E13), two rows: L OFF: positive control (B ON, no cap: thumb, 1 thumbnail call) then a 0.8 s outer cap while the price leg hangs with the Shopping items cached: 0 thumbnail calls, no IMG_SHOP thumb line. L ON: positive control (bind shopping, thumb) then the same cap + _late_image_drain_now: no shop_thumb on the entry, image != thumb, one bind line in (none, missed_at_deadline), 0 thumbnail calls.
- AX-7 (GB-7, E8): L ON + W ON fetch: get_cached reads exactly the s1w1:EDP name (typed EDP), a pick pre-stored under s1w0 is not read, the late pick is stored under the w1 name; W unset: s1w0.
- Base run: [pyt] tag=s96b-green-axbase1 elapsed=4s status=FAIL rc=1: 4 failed (AX-5 "assert 0 == 1", AX-6 L OFF and L ON positive controls "None == thumb", AX-7 the b39b9d79 s1 name), all AssertionError; 6 passed (AX-1 x2, AX-2, AX-3, AX-4 x2); netguard 0.
- Head run: all 10 pass (head1 and g8 below).

## G-2 prototype applied
- red/proto_bytes/* copied to the four app paths; CLAUDE.md and tests/test_inc_i2a_picture_not_cut.py built from git show HEAD: + their proto.diff hunks (patch), written CRLF like the working copy.
- git hash-object of each == the proto.diff post-image blob: image_relevance 03c75bb9, image_service 0a86cf7f, structured_comparison_service e3d4aa25, woocommerce_service b927f810, CLAUDE.md 43bbeb9d, I2a test d61e2883. No lint latitude used (bytes as the prototype).
- PICK_GUARD_RULES = "a9bdcc90" (image_service.py:489) == the digest of the final bytes: E19 (RED) and E22 (I2a) pass.
- G-3: AX-4 shows no leak, so no pop of the carrier; no deviation.

## G-6 lint
- .github/black-clean-paths.txt + tests/test_inc_i2b_guard_words_shop_image.py, tests/test_inc_i2b_addenda.py.
- ruff --select E9,F63,F7,F82 clean on the 7 touched .py; full ruff clean on image_relevance.py, the RED file, the addenda; black --check over all 44 allowlisted files: unchanged (a py3.15 target warning prints); py_compile of the four app files OK.

## G-3/G-4 head runs
- head1 (RED + addenda + I2a): [pyt] tag=s96b-green-head1 elapsed=38s status=OK rc=0: 105 passed (28 + 10 + 67); E27 did not need a re-run; netguard 0.
- g8 (RED, addenda, I2a, test_ci_gates, test_behavior_dimension_translation, test_inc_r1_seam at the committed head): [pyt] tag=s96b-green-g8 elapsed=46s status=OK rc=0: 264 passed; netguard 0.
- Comm set: s96/i2b/red/commset.txt (321) UNION s96/i2a/red/commset.txt (467) + the two new test files, minus tests/test_precommit_hook*.py, kept only files at base (git ls-tree HEAD; all existed): 499 files, sha256(list) a69b1dfd0e0a6ccc8e9c6c32c15fdd93428517db89deb91ecc398481bc65c571 (green/commset.txt; includes the six helper / conftest members the i2a set listed).
- Base: the cached record 80ec8352 (321 files, 24 FAILED, LC-6 reused) + an extended base record run at 5cd93c6a BEFORE G-2 for the 176 members absent from it (8 chunks xb_*): 2 FAILED (tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities, ::test_full_response_payload_audit_no_magnitude_keys); xb_07 rc=5 (tests/w4_11_prompt_digest_recorder.py alone, a helper: no tests). Stored as NEW files harness/base_records/5cd93c6a.../2f256debc02c8f99a047a741d2034a6e78b1aa04db10c94ad2babadab3a767eb.txt (+ .files.txt); the cached 80ec8352 files untouched. The two new files: RED base = 22 E fail (the RED report), addenda base = axbase1.
- Head: 20 chunks hd_* of <= 25 files, bound 1200: 24528 passed, 24 failed, 2 errors; FAILED/ERROR id set (26) == the base union (24 + 2); comm -13 EMPTY (new_failures = []), comm -23 EMPTY. No TIMEOUT, no 0xC0000142. Chunks 09 10 13 14 15 rc=1 hold only base ids.

## G-5 jest fences (jest 29.7.0, project jest by path from SmartCompareApp; @babel/core and .bin/jest present)
- [jest] tag=s96b-green-fences start=03:54:32 end=03:54:40 rc=1: 20 suites (the 11 of i2a fence_find.out + the 9 named files), 19 pass, 306 passed / 310; the only failures are the 4 nativeBundle.w37 drift nodes (the accepted base failure). Full suite not run (no client file).
### jest per file
- __tests__/App.navigation.test.tsx passed=4 failed=0 
- __tests__/DimensionBars.perCategory.test.tsx passed=45 failed=0 
- __tests__/ResultsScreen.timeout.test.tsx passed=24 failed=0 
- __tests__/b3a/nativeStrings.b3a.test.ts passed=6 failed=0 
- __tests__/brand/inAppMark.u4c.test.ts passed=13 failed=0 
- __tests__/clientTruth/medicalNote.s74.test.tsx passed=15 failed=0 
- __tests__/clientTruth/privacyManifest.s74.test.ts passed=2 failed=0 
- __tests__/clientTruth/shareTruth.s74.test.tsx passed=10 failed=0 
- __tests__/clipboardFallbackService.edges.test.ts passed=10 failed=0 
- __tests__/clipboardFallbackService.test.ts passed=8 failed=0 
- __tests__/config/nativeBundle.w37.test.ts passed=54 failed=4 FAILED: W3-7 (d) runtime dependencies are imported, justified, or pending removal d5 react-native-gesture-handler is removed from package.j
- __tests__/honestCounts.s69.test.tsx passed=14 failed=0 
- __tests__/landing.brand.s69.test.ts passed=5 failed=0 
- __tests__/landing.domain.s76.test.ts passed=9 failed=0 
- __tests__/landing.handoff.s69.test.ts passed=18 failed=0 
- __tests__/legal/legalScreenLang.u8.test.tsx passed=27 failed=0 
- __tests__/navigation/linking.w315.test.ts passed=12 failed=0 
- __tests__/onboarding/step05Trust.s69.test.tsx passed=13 failed=0 
- __tests__/playInstallReferrerService.edges.test.ts passed=10 failed=0 
- __tests__/playInstallReferrerService.test.ts passed=7 failed=0 

## Every [pyt] line
- [pyt] tag=s96b-green-base-xb_00 start=2026-11-17 03:16:15 end=2026-11-17 03:16:50 elapsed=35s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-base-xb_01 start=2026-11-17 03:16:51 end=2026-11-17 03:17:36 elapsed=45s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-base-xb_02 start=2026-11-17 03:17:36 end=2026-11-17 03:18:04 elapsed=27s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-base-xb_03 start=2026-11-17 03:18:04 end=2026-11-17 03:18:25 elapsed=21s bound=1200s status=FAIL rc=1
- [pyt] tag=s96b-green-base-xb_04 start=2026-11-17 03:18:26 end=2026-11-17 03:19:55 elapsed=89s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-base-xb_05 start=2026-11-17 03:19:56 end=2026-11-17 03:20:21 elapsed=25s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-base-xb_06 start=2026-11-17 03:20:22 end=2026-11-17 03:20:48 elapsed=27s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-base-xb_07 start=2026-11-17 03:20:49 end=2026-11-17 03:20:50 elapsed=1s bound=1200s status=FAIL rc=5
- [pyt] tag=s96b-green-head-hd_00 start=2026-11-17 03:22:32 end=2026-11-17 03:23:03 elapsed=31s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_01 start=2026-11-17 03:23:03 end=2026-11-17 03:23:43 elapsed=39s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_02 start=2026-11-17 03:23:43 end=2026-11-17 03:24:50 elapsed=67s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_03 start=2026-11-17 03:24:51 end=2026-11-17 03:25:09 elapsed=18s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_04 start=2026-11-17 03:25:09 end=2026-11-17 03:25:56 elapsed=46s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_05 start=2026-11-17 03:25:56 end=2026-11-17 03:27:12 elapsed=75s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_06 start=2026-11-17 03:27:12 end=2026-11-17 03:28:31 elapsed=79s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_07 start=2026-11-17 03:28:32 end=2026-11-17 03:29:13 elapsed=41s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_08 start=2026-11-17 03:40:16 end=2026-11-17 03:40:34 elapsed=18s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_09 start=2026-11-17 03:40:35 end=2026-11-17 03:41:10 elapsed=35s bound=1200s status=FAIL rc=1
- [pyt] tag=s96b-green-head-hd_10 start=2026-11-17 03:41:10 end=2026-11-17 03:41:50 elapsed=39s bound=1200s status=FAIL rc=1
- [pyt] tag=s96b-green-head-hd_11 start=2026-11-17 03:41:50 end=2026-11-17 03:43:37 elapsed=106s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_12 start=2026-11-17 03:43:37 end=2026-11-17 03:45:54 elapsed=137s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_13 start=2026-11-17 03:45:55 end=2026-11-17 03:47:06 elapsed=71s bound=1200s status=FAIL rc=1
- [pyt] tag=s96b-green-head-hd_14 start=2026-11-17 03:47:07 end=2026-11-17 03:49:13 elapsed=126s bound=1200s status=FAIL rc=1
- [pyt] tag=s96b-green-head-hd_15 start=2026-11-17 03:49:14 end=2026-11-17 03:50:07 elapsed=53s bound=1200s status=FAIL rc=1
- [pyt] tag=s96b-green-head-hd_16 start=2026-11-17 03:50:07 end=2026-11-17 03:51:15 elapsed=68s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_17 start=2026-11-17 03:51:16 end=2026-11-17 03:52:09 elapsed=53s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_18 start=2026-11-17 03:52:09 end=2026-11-17 03:52:51 elapsed=42s bound=1200s status=OK rc=0
- [pyt] tag=s96b-green-head-hd_19 start=2026-11-17 03:52:52 end=2026-11-17 03:53:18 elapsed=26s bound=1200s status=OK rc=0

## The 26 FAILED/ERROR ids at base and at head (identical)
- tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
- tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
- tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
- tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
- tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
- tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
- tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
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
- tests/test_s81_s18b_store_label.py::test_r2_table_shape
- tests/test_s81_s19_gap_queue.py::test_r15_hygiene
- tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
- tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
- tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
- tests/test_s81_s24_auth_throttle.py::test_r92_hygiene

## Files (sha256 over bytes on disk at the unit commit)
- b7a56eaae689c2a75f9c7b495c51f1d36f07d7a495ea2df888e731e5cc0df992 app/services/image_relevance.py
- 14230ee554ec9979cdb30dc3318576affedfdd04558483150cde720658ae85ab app/services/image_service.py
- cab0c667babe10ea9259700b3d2f60319e595d0b2b24ff51c79a8aebd8fcc16f app/services/structured_comparison_service.py
- 80de94464e965cd4026b415a0e2e411094a177831da17a10dd25d7c00ed4319d app/services/woocommerce_service.py
- fb0b3d96df95364a79cc4be73a103f65e02cb3b9984e11adcbbbcc0a7dc9fa38 CLAUDE.md
- be8ed39cad9c4b88a6e4a17ae499e49d7f237b751600ed6efed32947da1a5381 .github/black-clean-paths.txt
- 323e944cd856e79acf6993bafcfc2976b7042ff44b42cb5e147cff57cae89106 tests/test_inc_i2a_picture_not_cut.py
- c206cfd2dd4601bac2d7938f1f3d86a122599b186a6fca47d4d3ef8154feb06a tests/test_inc_i2b_guard_words_shop_image.py
- 5935d9e14dc5b935f1d9d73024ad658c1493f80a519f55f4e553c80d247a6a41 tests/test_inc_i2b_addenda.py
- 73e94432da4236d6d4d183a63c78277fdfa08f4e0dfc55f6594086a6f45cd9b8 tests/fixtures/inc_i2b_flag_off_golden.json
- 510d42d756d6e6ed621636698dc3a6d826b3fc21622ff12971bd6a02a137e18a tests/fixtures/inc_i2b_guard_words_corpus.json

## Deviations
- AX-6 is a _fetch_product_data-level cap (an outer asyncio.wait_for of 0.8 s while the price leg hangs with the Shopping items cached, then _late_image_drain_now for L ON), not a whole-compare STREAM_HARD_CAP run; each row opens with a positive control so it fails at base on an assertion.
- AX-4 runs the two compares at the service level (compare_from_text / compare_from_text_streaming through the FY25 harness); the History / compare_runs save payloads are the route's copy of that response body, so the body check stands for them; no route-level persist recorder was run.
- The comm set keeps the six non-test members of the i2a set (helpers, conftest); the extended base chunk holding only tests/w4_11_prompt_digest_recorder.py ended rc=5 (no tests), not a failure.

## Open questions
- none beyond the gate's; no NOT MEASURED item.

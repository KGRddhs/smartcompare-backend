# REBASE_REPORT G-INC-1 final round (agent Opus 5.5, 2026-11-12 09:11-10:35 AST)

unit: G-INC-1 RESULT-TRUTH (INC-X9 + INC-X10 + INC-X8 + INC-X2a), worktree sc-inc-g1, branch fix/inc-g1-result-truth
head_before: dcdbf53027cb8f114b190429282cf46652d9571b (verified, git status --short empty before)
base (origin/main fetched): ea47cbfbe67d19da49b078169a5c4cf854555e68
head_after: b5e8624c8e4ff6c431cf3b80e727a9633d2ff744 (commits 103f38d0 GREEN, b5e8624c fix round 1); nothing pushed, no commit of my own (no pin row owed)

## Conflicts and resolutions
- Commit 1/2 (a92b0ba3): CONFLICT CLAUDE.md, one hunk: the `**Feature Flags:**` line (:342 at HEAD). Main inserted the S81-04c and S81-12 LEGAL-V3 pointer sentences, the unit inserted its G-INC-1 sentence, both at the same anchor (word diff against a74caba7: one insert each, same offset). Resolution = UNION in merge order (S81-04c, S81-12, then G-INC-1), written with Python on the bytes (CRLF kept; 1112 CRLF = 1112 LF). Verified: every line of main CLAUDE.md is present except the two lines the unit edits (the Feature Flags union and the `- **Results redesign:**` line, which main never changed since a74caba7); every unit-added line present. The unit block auto-merged after the S81-12 block (:641), blank line before and after, before `## Tests` (:650).
- Commit 2/2 (dcdbf530): replayed with no conflict.
- After continue: git diff --check clean; no <<<<<<< / >>>>>>> in CLAUDE.md, app/, tests/; footprint `git diff --stat origin/main...HEAD` = exactly the ten ruled files (10 files, 1811+, 105-), no whole-file diff; .githooks diff empty. app/+tests/ patch-id of the unit identical before and after the replay (a1450568...).
- Note: git rebase does not run the pre-commit hook on replayed commits; the hook was not run in this round.

## Frozen files (sha256 of the git blob, first = last, unchanged; no test file edited, RB-G1F-2)
b2ef4d349021d3dca49016f34d576e707eddd92f74a77d04b872b330e1f69c5a tests/test_inc_x9_cohort_line_retire.py
8419549c2861055f93a33f8fcf66a1060bdf2ab1ace7b76a64a1281078f01a18 tests/test_inc_x10_listing_match_guard.py
8a2cc6d6dc9fcfbbdff10935240684abb100e84116ab9dab188917ce0673a861 tests/test_inc_x8_phase2_cached_rating.py
febb83de596fcb366ad59ff6a3957489bd3562a4ab6995275d4f0612884154eb tests/test_inc_x2a_image_tier_timing.py
96858246713929bb04dbfaf91c08d367f806995b181979d15b86e721e6f16f5a tests/test_inc_g1_gate_rows.py

## Pin rows and mutants
NONE (RB-G1F-2): no pin row, no test edit, no mutant, no .qa-mutation.lock created.

## Gates ([pyt] lines)

- unit off/on: 88 passed each; ciorder: 728 passed (24 files, wave_b first).
- ruff 0.16.5 --select E9,F63,F7,F82 --no-cache: All checks passed (9 touched python files); py_compile rc=0; black: none of the touched files in .github/black-clean-paths.txt.

## Whole free tier (RB-G1F-4 (3))
- list: every tests/test_*.py at ea47cbfb minus the 4 tests/test_precommit_hook*.py = 765 (tests/perf/test_latency_bench.py is not matched by tests/test_*.py); head = 765 + 5 unit files = 770.
- base record: harness/base_records/ea47cbfbe67d19da49b078169a5c4cf854555e68/68dbc2e1f363f0a09f04627e64e3b0e03ad15c1aa7f8f1161753a449053e7d42.{files,header.txt,txt,pyt.log}; detached scratch worktree G-INC-1_final/b removed with git worktree remove --force and verified gone (worktree list, ls).
- head record: harness/base_records/b5e8624c8e4ff6c431cf3b80e727a9633d2ff744/9a02556dc22a63c7a22b5bbe901d887bd6dbc0819c72b602d68fbd44a8e3266c.*
- base 27 ids, head 27 ids, comm -13 EMPTY, comm -23 EMPTY; prompt_truth pair ERROR both sides; unit files 0 failed. Totals base 29593 passed/25 failed/2 errors; head 29684/25/2.
- several base ids are byte-level hygiene rows (CRLF in the checkout) and golden digests of s81 files; observed identically at head.
- base ids:
tests/test_auth_interceptor.py::test_sign_in_with_social_exception
tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
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

### base [pyt] lines
[pyt] tag=inc-g1-final-base-01 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-01 start=2026-11-12 09:20:03 end=2026-11-12 09:21:35 elapsed=92s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-02 start=2026-11-12 09:21:38 end=2026-11-12 09:22:31 elapsed=53s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-base-03 waited=3s for the box pytest slot
[pyt] tag=inc-g1-final-base-03 start=2026-11-12 09:22:34 end=2026-11-12 09:23:14 elapsed=40s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-04 start=2026-11-12 09:23:16 end=2026-11-12 09:24:21 elapsed=65s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-05 start=2026-11-12 09:24:23 end=2026-11-12 09:26:10 elapsed=107s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-06 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-06 start=2026-11-12 09:26:15 end=2026-11-12 09:26:54 elapsed=40s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-07 waited=8s for the box pytest slot
[pyt] tag=inc-g1-final-base-07 start=2026-11-12 09:27:04 end=2026-11-12 09:27:34 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-08 waited=7s for the box pytest slot
[pyt] tag=inc-g1-final-base-08 start=2026-11-12 09:27:43 end=2026-11-12 09:28:21 elapsed=38s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-09 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-09 start=2026-11-12 09:28:25 end=2026-11-12 09:31:24 elapsed=179s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-10 start=2026-11-12 09:31:28 end=2026-11-12 09:34:46 elapsed=198s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-11 waited=4s for the box pytest slot
[pyt] tag=inc-g1-final-base-11 start=2026-11-12 09:34:56 end=2026-11-12 09:36:01 elapsed=65s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-12 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-12 start=2026-11-12 09:36:04 end=2026-11-12 09:37:04 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-13 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-13 start=2026-11-12 09:37:08 end=2026-11-12 09:37:41 elapsed=33s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-14 waited=8s for the box pytest slot
[pyt] tag=inc-g1-final-base-14 start=2026-11-12 09:37:52 end=2026-11-12 09:38:25 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-15 waited=4s for the box pytest slot
[pyt] tag=inc-g1-final-base-15 start=2026-11-12 09:38:32 end=2026-11-12 09:39:28 elapsed=56s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-16 waited=4s for the box pytest slot
[pyt] tag=inc-g1-final-base-16 start=2026-11-12 09:39:37 end=2026-11-12 09:40:42 elapsed=64s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-base-17 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-17 start=2026-11-12 09:40:47 end=2026-11-12 09:41:32 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-18 waited=7s for the box pytest slot
[pyt] tag=inc-g1-final-base-18 start=2026-11-12 09:41:41 end=2026-11-12 09:42:22 elapsed=41s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-base-19 waited=3s for the box pytest slot
[pyt] tag=inc-g1-final-base-19 start=2026-11-12 09:42:29 end=2026-11-12 09:43:03 elapsed=35s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-20 waited=7s for the box pytest slot
[pyt] tag=inc-g1-final-base-20 start=2026-11-12 09:43:11 end=2026-11-12 09:48:04 elapsed=293s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-21 waited=11s for the box pytest slot
[pyt] tag=inc-g1-final-base-21 start=2026-11-12 09:48:19 end=2026-11-12 09:50:51 elapsed=151s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-22 start=2026-11-12 09:50:54 end=2026-11-12 09:52:29 elapsed=95s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-base-23 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-23 start=2026-11-12 09:52:32 end=2026-11-12 09:54:18 elapsed=106s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-base-24 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-24 start=2026-11-12 09:54:21 end=2026-11-12 09:55:19 elapsed=58s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-base-25 waited=3s for the box pytest slot
[pyt] tag=inc-g1-final-base-25 start=2026-11-12 09:55:23 end=2026-11-12 09:57:03 elapsed=100s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-26 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-26 start=2026-11-12 09:57:06 end=2026-11-12 09:57:33 elapsed=28s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-27 waited=3s for the box pytest slot
[pyt] tag=inc-g1-final-base-27 start=2026-11-12 09:57:39 end=2026-11-12 09:58:41 elapsed=63s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-28 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-base-28 start=2026-11-12 09:58:44 end=2026-11-12 09:59:36 elapsed=52s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-29 waited=3s for the box pytest slot
[pyt] tag=inc-g1-final-base-29 start=2026-11-12 09:59:40 end=2026-11-12 10:00:19 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-30 start=2026-11-12 10:00:22 end=2026-11-12 10:01:03 elapsed=42s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-base-31 start=2026-11-12 10:01:06 end=2026-11-12 10:01:26 elapsed=20s bound=1200s status=OK rc=0

### head [pyt] lines
[pyt] tag=inc-g1-final-head-01 start=2026-11-12 10:01:30 end=2026-11-12 10:02:41 elapsed=70s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-02 waited=4s for the box pytest slot
[pyt] tag=inc-g1-final-head-02 start=2026-11-12 10:02:49 end=2026-11-12 10:04:02 elapsed=73s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-head-03 start=2026-11-12 10:04:05 end=2026-11-12 10:04:34 elapsed=29s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-04 start=2026-11-12 10:04:36 end=2026-11-12 10:05:31 elapsed=55s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-05 start=2026-11-12 10:05:35 end=2026-11-12 10:06:24 elapsed=50s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-06 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-head-06 start=2026-11-12 10:06:28 end=2026-11-12 10:06:45 elapsed=17s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-07 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-head-07 start=2026-11-12 10:06:48 end=2026-11-12 10:07:08 elapsed=20s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-08 start=2026-11-12 10:07:12 end=2026-11-12 10:07:38 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-09 start=2026-11-12 10:07:40 end=2026-11-12 10:09:35 elapsed=115s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-10 start=2026-11-12 10:09:39 end=2026-11-12 10:11:10 elapsed=92s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-11 start=2026-11-12 10:11:13 end=2026-11-12 10:11:31 elapsed=18s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-12 start=2026-11-12 10:11:35 end=2026-11-12 10:12:24 elapsed=49s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-13 start=2026-11-12 10:12:26 end=2026-11-12 10:12:43 elapsed=17s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-14 start=2026-11-12 10:12:45 end=2026-11-12 10:13:00 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-15 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-head-15 start=2026-11-12 10:13:04 end=2026-11-12 10:13:46 elapsed=42s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-16 start=2026-11-12 10:13:48 end=2026-11-12 10:14:29 elapsed=41s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-head-17 start=2026-11-12 10:14:31 end=2026-11-12 10:15:02 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-18 waited=3s for the box pytest slot
[pyt] tag=inc-g1-final-head-18 start=2026-11-12 10:15:06 end=2026-11-12 10:15:30 elapsed=24s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-head-19 start=2026-11-12 10:15:32 end=2026-11-12 10:15:50 elapsed=18s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-20 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-head-20 start=2026-11-12 10:15:54 end=2026-11-12 10:19:20 elapsed=206s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-21 start=2026-11-12 10:19:22 end=2026-11-12 10:21:03 elapsed=100s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-22 start=2026-11-12 10:21:05 end=2026-11-12 10:21:51 elapsed=46s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-head-23 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-head-23 start=2026-11-12 10:21:54 end=2026-11-12 10:23:31 elapsed=96s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-head-24 start=2026-11-12 10:23:33 end=2026-11-12 10:25:15 elapsed=102s bound=1200s status=FAIL rc=1
[pyt] tag=inc-g1-final-head-25 start=2026-11-12 10:25:18 end=2026-11-12 10:26:31 elapsed=73s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-26 start=2026-11-12 10:26:34 end=2026-11-12 10:27:26 elapsed=52s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-27 start=2026-11-12 10:27:29 end=2026-11-12 10:28:16 elapsed=48s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-28 start=2026-11-12 10:28:18 end=2026-11-12 10:29:02 elapsed=44s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-29 start=2026-11-12 10:29:06 end=2026-11-12 10:29:47 elapsed=41s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-30 waited=2s for the box pytest slot
[pyt] tag=inc-g1-final-head-30 start=2026-11-12 10:29:50 end=2026-11-12 10:30:20 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=inc-g1-final-head-31 start=2026-11-12 10:30:23 end=2026-11-12 10:30:40 elapsed=18s bound=1200s status=OK rc=0

## Hook files
NOT run per RB-G1F-4 (3): the unit touches no .githooks file (`git diff --stat origin/main...HEAD -- .githooks` empty).

## Full jest (LC-7), H5 probe printed nothing at 10:01:48
jest 29.7.0
29.7.0
[jest] tag=inc-g1-final-jest-full start=2026-11-12 10:01:55 end=2026-11-12 10:02:42 rc=1
{'numTotalTestSuites': 412, 'numPassedTestSuites': 408, 'numFailedTestSuites': 1, 'numPendingTestSuites': 3, 'numTotalTests': 4069, 'numPassedTests': 4039, 'numFailedTests': 4, 'numPendingTests': 13, 'numTodoTests': 13}
FENCE __tests__/config/nativeBundle.w37.test.ts failed passed=54 failed=4
FENCE __tests__/clipboardFallbackService.test.ts passed passed=8 failed=0
FENCE __tests__/clientTruth/privacyManifest.s74.test.ts passed passed=2 failed=0
FENCE __tests__/playInstallReferrerService.edges.test.ts passed passed=10 failed=0
FENCE __tests__/playInstallReferrerService.test.ts passed passed=7 failed=0
FENCE __tests__/ResultsScreen.timeout.test.tsx passed passed=24 failed=0
FENCE __tests__/landing.domain.s76.test.ts passed passed=9 failed=0
FENCE __tests__/clientTruth/shareTruth.s74.test.tsx passed passed=10 failed=0
FENCE __tests__/onboarding/step05Trust.s69.test.tsx passed passed=13 failed=0
FENCE __tests__/clientTruth/medicalNote.s74.test.tsx passed passed=15 failed=0
FENCE __tests__/honestCounts.s69.test.tsx passed passed=14 failed=0
FENCE __tests__/DimensionBars.perCategory.test.tsx passed passed=45 failed=0
FENCE __tests__/navigation/linking.w315.test.ts passed passed=12 failed=0
FENCE __tests__/brand/inAppMark.u4c.test.ts passed passed=13 failed=0
FAILED __tests__/config/nativeBundle.w37.test.ts :: W3-7 (d) runtime dependencies are imported, justified, or pending removal d5 react-native-gesture-handler is removed fro
FAILED __tests__/config/nativeBundle.w37.test.ts :: session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion k2 package-lock.json and node_modules resolve the
FAILED __tests__/config/nativeBundle.w37.test.ts :: session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion k4 eslint-config-expo is on the SDK-54 line (~10.
FAILED __tests__/config/nativeBundle.w37.test.ts :: session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion k5 offline expo-install consistency: every declar

## PR body
PR_BODY.md: 25126 bytes (python), 0 non-ASCII bytes, no attribution line, sha256 84afcc0d18239e2f5fefa2243df02666ff7f3f9102fe21591490cff3c297a7ed

## NOT MEASURED
- the pre-commit hook on the replayed commits (git rebase skips it)

## Deviations
- the full jest run (10:01:55-10:02:42) overlapped head-side pytest chunk 01 (10:01:30-10:02:41) instead of strictly after (3) (separate H5 slots; done for the budget); head id set still equals base.
- the chunk driver's own failed_ids.txt counted 28 because it also caught captured-log lines starting 'ERROR    app...'; the records use the 27 tests/ node ids re-extracted from the logs.

## git status --short (worktree)
(empty)

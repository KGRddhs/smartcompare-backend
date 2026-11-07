# S81-G8 GREEN REPORT (B1b URL-TELEMETRY + S81-11b RESULT-AGGREGATES + S81-18b STORE-LABEL)

Agent: Opus 5.5 (claude-opus-5-5), GREEN, 2026-11-07 07:2x-08:2x AST. Written through the shell (python), as the harness requires.
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g8, branch feature/s81-g8-followups cut from daf86d32d222a885c42dc537e83c25483527a83b (= origin/main).
HEAD fe2ba6703d22e48842bf4af2d714d0716aa5f8bf (ONE commit through the pre-commit hook; hook output "All checks passed!"; no push, no PR, no rebase).
Binding inputs read: s81-common.txt, GATE_S81_G8 GC-1..GC-12, RULINGS_S81_G8 R-G8-1..13, the spec (B1b / 11b / 18b sections + 12), the brief, the RED report. The RED prototype was NOT applied: every hunk written by hand from the spec contract (the prototype diff was not read).

## 1. Frozen files (GC-1), re-hashed first (07:2x) and last (after the commit, disk AND HEAD blob): all four EQUAL
- tests/test_s81_b1b_url_telemetry.py 7dc7f8aa9f79ba0d241bfebf9ce5486c1f0a307f75b53741ac82d666355cee71
- tests/test_s81_s11b_result_aggregates.py 957020e30f9a88358c43e00db3fd4293b98271d3c3cb6c483bbae8c3ef4a0cf0
- tests/test_s81_s18b_store_label.py 4fc4b3996834e09626a712aa68d88319f5139414aac845ee2d9511123b048adf
- tests/fixtures/s81_g8_flag_off_golden.json 497754da580815222767a5138226cf2d16bc2e981bcac3dff462ea86fc15eb8f (NOT re-recorded)

## 2. Files changed (sha256 of the working-copy bytes; existing files CRLF, new files LF; byte copies of every existing file before the edits under S81-G8_green_before/ with SHA256SUMS.txt)
| path | numstat | sha256 before | sha256 after |
|---|---|---|---|
| CLAUDE.md | +10 / -4 | c0413fec0cdd8affbad6101d1f85c60305ec95e8663e3629190851f21aa80ed2 | 31fffe43a7c57004c6f02dcb65d49fd368929696b7b129dc0c62d22fc0a11146 |
| app/services/compare_runs.py | +2 / -1 | ff5aac7535825ae0aaad4d7fd929f12a2db75e0a3b7fcd2732e5101f1758e8cd | e341e4559bedd96744ea0642e08f77c860f1cb045ff3777fdbd71f8187f84173 |
| app/services/kb_serve.py | +44 / -0 | 82bb323e1e2662e0d83bd6a9af4a82f7714ea0821dd64566752c1ba047f3e898 | cc0228487926c58fbee4dc8db38a4d5fa9d05c8d98f9ccb4d35057c77afc0d27 |
| app/services/response_builder.py | +31 / -0 | e90326dd15cf96c4c29076d95b2ee7904e4fe155336d257a980d7372e31f3fe9 | 8dbe4ba4400d620af2382f0ce4148567490b5a81bdbccbaae1e98985ee165549 |
| app/services/result_gate.py | +25 / -10 | bb6d46a53293380907fa936b29145e9b8192978978d4ff5034fcfd1308689d9e | 7d1d5e934b8838e531b35212a3981b9baab80a1295ee5bd0e47ab3280e01f4ce |
| app/services/sentry_service.py | +4 / -2 | 5aed8ebf139b9f26c19a3e3cbaadf6d86f7fa5d07cb2ce3827da0a70fb004200 | 81e02147e37efdd7b1545c4a3a924ba7a66978b156f70e2a726e1f40a5ce2990 |
| app/services/structured_comparison_service.py | +10 / -0 | 4f21254651a8081662528f98c46749daa4316354836d811c8390ee7ed282fdf0 | 42716f8490fc3d85b9e06bd6d5f7d27fc32cc2e1d1d54121ffbf9a23a7c17737 |
| app/services/store_labels.py | +179 / -0 | (new) | bd9ae0ba7a4c2ffb2eefae6e1115a3e19eb67474c41ead6ffb6c3305066343d9 |
| data/merchant_labels.json | +137 / -0 | (new) | afef66a95efb5db4e5ce5cd295b1119a55024725512cc15901e29bc51544a081 |

Change list in the spec's section-0 order (GC-6):
- B1b: result_gate.py: `_facts(result, *, strict, url_mode=False)` (the price / ratings facts through `_url_price` / `_url_rating` in both readings when url_mode); `_corroborated(result, i, url_mode=False)`; `assess_result(..., url_mode: bool = False)` keyword-only, facts / facts_literal through `_facts(..., url_mode=url_mode)`, `_corroborated(body, i, url_mode)`; one module-docstring sentence (no P11 banned substring). sentry_service.py: the one `assess_result` call with `**({"url_mode": True} if input_type == "url" else {})` + one docstring sentence. compare_runs.py :438 (R-G8-3): the same conditional kwarg, nothing else.
- S81-11b: kb_serve.py: `result_aggregates_enabled()` beside the two readers; `AGGREGATE_FIELDS`, `_slot_aggregate`, `result_aggregates(views)` after `served`; one module-docstring bullet. response_builder.py: the leaf import `from app.services import kb_serve as _kb_serve`, the kwarg `kb_views` after `product_categories`, a docstring paragraph, the stamp after the S81-20 block (flag FIRST; one WARNING `[RESULT_AGGREGATES] stamp skipped: <Type>`). scs: `kb_views=getattr(self, "_kb_views", None),  # S81-11b` at the partial / REST / stream builder calls.
- S81-18b: NEW data/merchant_labels.json (version 1, 33 hosts of spec 18b.2.4, en = the spec's labels, ar = en, json.dumps(ensure_ascii, indent=1, sort_keys) + LF; 2,496 B, 0 bytes > 127, 0 CR). NEW app/services/store_labels.py (stdlib + deny_hosts.normalize_host; LABELS_PATH, load_labels (stat-keyed cache under a Lock, ONE WARNING `[STORE_LABEL] table unavailable type=<Type>` per file state, set capped at 64), label_for, label_prices (labels computed first, then a NEW `{**price, "store_label": label}` per slot on products[i] and overview.products[i]), _reset_label_cache; the host regex copied locally (no kb_service import: S81-14 P01)). response_builder.py: the leaf import, the kwarg `output_lang` after `kb_views`, the pass after the D08 block (flag FIRST; one WARNING `[STORE_LABEL] pass skipped: <Type>`). scs: `output_lang=ctx.get("output_lang")` (partial), `output_lang=output_lang` (REST, stream), and `**({"output_lang": output_lang} if output_lang else {})` in both `_partial_build_ctx` literals.
- CLAUDE.md LAST (GC-7, CRLF kept, the added text pure ASCII): the G8 block (heading + three rows + one owner-steps bullet) after the S81-22 block, before `## Tests`, one blank line before its heading; the :341 pointer clause gains the G8 sentence after the S81-22 sentence; the B1 row clause rewritten in place ("its telemetry reads the URL evidence (S81-G8 B1b)"); the S81-20 L19 sentence rewritten in place and the Canary sentence gains "and B1's URL message"; the dated apply record (:92) gains the 045 / 050 / 052 applied 2026-11-06 sentence (047 declined, 046 / 048 / 049 written NOT applied) before "A migration missing from this record". No new line carries both scoring_method and enum (the 2 such lines are pre-existing); none of the five S23 forbidden phrases.
- No migration, client file, requirements, .githooks, railway config or route file edited.

## 3. Gates (cheapest first)
- ruff --select E9,F63,F7,F82 --no-cache on the 7 Python files + the 3 RED files: All checks passed; the default ruff set on store_labels / kb_serve / result_gate / compare_runs: All checks passed (SIM103 + B905 fixed in store_labels before the unit runs); py_compile clean; json.loads on the table OK (the R2 row also passes); bytes > 127 = 0 in store_labels.py and merchant_labels.json; `git diff --stat` hunks only (126 insertions, 17 deletions over 7 existing files).
- Added-line sweep: no 64-hex literal, no @gmail / +973 / 8-digit run / sk- / eyJ / PEM / credentialed URL; no constant named with access / auth / api / credential / creds / key / password / secret / token (LABELS_PATH, LABEL_LANGS, AGGREGATE_FIELDS, _LABEL_CACHE, _LABEL_LOCK, _LABEL_WARNED, _LABEL_WARNED_CAP, _DIACRITICS, _HOST_RX, _TRUTHY); no personal value (the table holds public store names only, no URL).
- The 34 nodes:
  - [pyt] tag=g8green-units-off start=2026-11-07 07:35:07 end=2026-11-07 07:35:13 elapsed=6s bound=600s status=OK rc=0 | 34 passed, 11 warnings in 5.35s | [hermeticity] sentinel checked 34 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
  - [pyt] tag=g8green-units-on (ENABLE_RESULT_STATUS_METADATA=true ENABLE_RESULT_AGGREGATES=true ENABLE_STORE_LABEL=true in the runner call only) start=2026-11-07 07:35:27 end=2026-11-07 07:35:33 elapsed=6s bound=600s status=OK rc=0 | 34 passed, 11 warnings in 5.04s | [hermeticity] sentinel checked 34 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s)
- CI-order set of spec 12.1 (23 files, flags unset), once:
  - [pyt] tag=g8green-ciorder start=2026-11-07 07:36:54 end=2026-11-07 07:38:21 elapsed=88s bound=1200s status=FAIL rc=1 | 1 failed, 1716 passed, 18 warnings in 85.56s | the one failure tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (known CRLF environmental, failing at base too); equal to the RED prototype figure (1716 + r06), i.e. the base 1694 + the 22 RED nodes now green. No existing pin reddened: E-rows none (GC-3).
- tests/test_secret_scan_static.py alone: [pyt] tag=g8green-secretscan start=2026-11-07 07:59:20 end=2026-11-07 07:59:27 elapsed=7s bound=600s status=OK rc=0 | 31 passed | [netguard] blocked 0 attempt(s) from 0 node(s)
- Corpus gate ONCE at HEAD (working tree = the committed bytes; every flag unset; no pytest running on the box, checked with the process list): `scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_RESULT_AGGREGATES,ENABLE_STORE_LABEL,ENABLE_RESULT_STATUS_METADATA` rc=0: RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 200474dfcecf2bcc625eb66b3c3fbe65a4a66f2d35b51037aaf5a6b13351dc3f = the base (RED) value: EQUAL. Log corpus_head.log.
- Client fences BY PATH through the junction (node_modules/@babel/core and .bin/jest verified; the junction never touched; node v24.11.1, jest 29.7.0; `node node_modules/jest/bin/jest.js --ci <15 paths>` from SmartCompareApp under timeout -k 15 1800):
  - [jest] tag=g8green-fences start=2026-11-07 08:09:27 end=2026-11-07 08:09:36 rc=1 | Test Suites: 1 failed, 14 passed, 15 total | Tests: 4 failed, 242 passed, 246 total | the red suite = config/nativeBundle.w37 with exactly the four drift nodes (d5 react-native-gesture-handler, k2, k4, k5); b3a/nativeStrings green: 13 / 14 fences + b3a as expected.
- FULL jest NOT run (LC-7: the final round). The four tests/test_precommit_hook*.py files NOT RUN (no .githooks change).

## 4. Comm set (R-G8-11, LC-6)
- Set = the RED's 712 (S81-G8_red/COMM_SET.txt = specs/S81_G8_COMM_SET.txt, sorted-list sha256 ea0d2f1beeeec1668aae965d6514dd51ce0d3771919fd9d5b888f08c049b46f5) + the three RED files = 715 files (comm_head_members.txt). Union re-check for my edits: the only tests naming store_labels / merchant_labels / STORE_LABEL / RESULT_AGGREGATES / result_aggregates are the two RED files; the data/ walkers and the CLAUDE.md readers not in the 712 = only tests/test_precommit_hook_phase_b.py (excluded: no .githooks change). No member added.
- Base: the STORED record harness/base_records/daf86d32d222a885c42dc537e83c25483527a83b/ea0d2f1beeeec1668aae965d6514dd51ce0d3771919fd9d5b888f08c049b46f5.txt REUSED (same main sha, same set hash; no base pytest run).
- HEAD: 29 chunks of <= 25 files, bound 1200, one at a time, flags stripped from the env (driver chunks_head.py):
- [pyt] tag=g8green-comm-c00 start=2026-11-07 07:39:06 end=2026-11-07 07:39:39 elapsed=33s bound=1200s status=OK rc=0 | 752 passed, 11 warnings in 31.67s | [netguard] blocked 22 attempt(s) from 5 node(s)
- [pyt] tag=g8green-comm-c01 start=2026-11-07 07:39:39 end=2026-11-07 07:40:07 elapsed=28s bound=1200s status=FAIL rc=1 | 2 failed, 745 passed, 31 warnings in 26.49s | [netguard] blocked 19 attempt(s) from 8 node(s)
- [pyt] tag=g8green-comm-c02 start=2026-11-07 07:40:07 end=2026-11-07 07:40:33 elapsed=25s bound=1200s status=OK rc=0 | 434 passed, 31 deselected, 11 warnings in 24.21s | [netguard] blocked 17 attempt(s) from 4 node(s)
- [pyt] tag=g8green-comm-c03 start=2026-11-07 07:40:33 end=2026-11-07 07:41:21 elapsed=48s bound=1200s status=OK rc=0 | 1048 passed, 5 deselected, 13 warnings in 46.74s | [netguard] blocked 10 attempt(s) from 7 node(s)
- [pyt] tag=g8green-comm-c04 start=2026-11-07 07:41:26 end=2026-11-07 07:41:56 elapsed=31s bound=1200s status=OK rc=0 | 1409 passed, 1 skipped, 2 deselected, 1 xfailed, 11 warnings in 29.34s | [netguard] blocked 4 attempt(s) from 2 node(s)
- [pyt] tag=g8green-comm-c05 start=2026-11-07 07:41:57 end=2026-11-07 07:42:10 elapsed=14s bound=1200s status=OK rc=0 | 393 passed, 9 deselected, 13 warnings in 12.52s | [netguard] blocked 2 attempt(s) from 1 node(s)
- [pyt] tag=g8green-comm-c06 start=2026-11-07 07:42:10 end=2026-11-07 07:42:28 elapsed=18s bound=1200s status=OK rc=0 | 508 passed, 1 skipped, 11 warnings in 16.89s | [netguard] blocked 10 attempt(s) from 4 node(s)
- [pyt] tag=g8green-comm-c07 start=2026-11-07 07:42:29 end=2026-11-07 07:43:00 elapsed=32s bound=1200s status=OK rc=0 | 1511 passed, 1 skipped, 11 warnings in 30.53s | [netguard] blocked 44 attempt(s) from 14 node(s)
- [pyt] tag=g8green-comm-c08 start=2026-11-07 07:43:01 end=2026-11-07 07:44:12 elapsed=71s bound=1200s status=OK rc=0 | 1977 passed, 16 warnings in 69.76s (0:01:09) | [netguard] blocked 28 attempt(s) from 23 node(s)
- [pyt] tag=g8green-comm-c09 start=2026-11-07 07:44:12 end=2026-11-07 07:44:26 elapsed=14s bound=1200s status=OK rc=0 | 460 passed, 1 skipped, 5 deselected, 13 warnings in 13.13s | [netguard] blocked 7 attempt(s) from 7 node(s)
- [pyt] tag=g8green-comm-c10 start=2026-11-07 07:44:37 end=2026-11-07 07:45:13 elapsed=37s bound=1200s status=OK rc=0 | 497 passed, 9 deselected, 1 xfailed, 13 warnings in 35.78s | [netguard] blocked 13 attempt(s) from 2 node(s)
- [pyt] tag=g8green-comm-c11 start=2026-11-07 07:45:14 end=2026-11-07 07:45:29 elapsed=15s bound=1200s status=OK rc=0 | 168 passed, 13 warnings in 14.21s | [netguard] blocked 3 attempt(s) from 3 node(s)
- [pyt] tag=g8green-comm-c12 start=2026-11-07 07:45:29 end=2026-11-07 07:45:41 elapsed=12s bound=1200s status=OK rc=0 | 460 passed, 1 skipped, 6 deselected, 2 warnings in 11.21s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8green-comm-c13 start=2026-11-07 07:45:41 end=2026-11-07 07:46:14 elapsed=32s bound=1200s status=OK rc=0 | 3823 passed, 22 skipped, 4 deselected, 4 warnings in 30.58s | [netguard] blocked 128 attempt(s) from 7 node(s)
- [pyt] tag=g8green-comm-c14 start=2026-11-07 07:46:14 end=2026-11-07 07:46:48 elapsed=34s bound=1200s status=FAIL rc=1 | 4 failed, 738 passed, 3 skipped, 3 deselected, 18 warnings in 33.20s | [netguard] blocked 26 attempt(s) from 12 node(s)
- [pyt] tag=g8green-comm-c15 start=2026-11-07 07:46:48 end=2026-11-07 07:47:12 elapsed=23s bound=1200s status=OK rc=0 | 351 passed, 10 deselected, 11 warnings in 22.25s | [netguard] blocked 31 attempt(s) from 7 node(s)
- [pyt] tag=g8green-comm-c16 start=2026-11-07 07:47:12 end=2026-11-07 07:47:31 elapsed=19s bound=1200s status=FAIL rc=1 | 452 passed, 4 skipped, 2 deselected, 1 xfailed, 13 warnings, 2 errors in 17.89s | [netguard] blocked 97 attempt(s) from 12 node(s)
- [pyt] tag=g8green-comm-c17 start=2026-11-07 07:47:36 end=2026-11-07 07:48:07 elapsed=31s bound=1200s status=OK rc=0 | 330 passed, 1 skipped, 1 deselected, 18 warnings in 30.05s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8green-comm-c18 start=2026-11-07 07:48:07 end=2026-11-07 07:50:46 elapsed=159s bound=1200s status=OK rc=0 | 1021 passed, 260 warnings in 156.82s (0:02:36) | [netguard] blocked 20 attempt(s) from 1 node(s)
- [pyt] tag=g8green-comm-c19 start=2026-11-07 07:50:46 end=2026-11-07 07:52:31 elapsed=105s bound=1200s status=FAIL rc=1 | 2 failed, 2457 passed, 14 warnings in 102.73s (0:01:42) | [netguard] blocked 4 attempt(s) from 2 node(s)
- [pyt] tag=g8green-comm-c20 start=2026-11-07 07:52:31 end=2026-11-07 07:53:47 elapsed=76s bound=1200s status=FAIL rc=1 | 11 failed, 2690 passed, 63 warnings in 74.39s (0:01:14) | [netguard] blocked 24 attempt(s) from 2 node(s)
- [pyt] tag=g8green-comm-c21 start=2026-11-07 07:53:47 end=2026-11-07 07:54:42 elapsed=55s bound=1200s status=FAIL rc=1 | 3 failed, 1873 passed, 1 xfailed, 45 warnings in 53.49s | [netguard] blocked 24 attempt(s) from 9 node(s)
- [pyt] tag=g8green-comm-c22 start=2026-11-07 07:54:43 end=2026-11-07 07:55:21 elapsed=39s bound=1200s status=OK rc=0 | 912 passed, 13 warnings in 36.92s | [netguard] blocked 13 attempt(s) from 7 node(s)
- [pyt] tag=g8green-comm-c23 start=2026-11-07 07:55:21 end=2026-11-07 07:56:08 elapsed=47s bound=1200s status=OK rc=0 | 712 passed, 1 skipped, 2 deselected, 12 warnings in 45.43s | [netguard] blocked 14 attempt(s) from 4 node(s)
- [pyt] tag=g8green-comm-c24 start=2026-11-07 07:56:20 end=2026-11-07 07:57:02 elapsed=42s bound=1200s status=OK rc=0 | 491 passed, 7 skipped, 8 deselected, 20 warnings in 40.74s | [netguard] blocked 79 attempt(s) from 21 node(s)
- [pyt] tag=g8green-comm-c25 start=2026-11-07 07:57:02 end=2026-11-07 07:57:38 elapsed=37s bound=1200s status=OK rc=0 | 513 passed, 8 deselected, 12 warnings in 35.43s | [netguard] blocked 102 attempt(s) from 45 node(s)
- [pyt] tag=g8green-comm-c26 start=2026-11-07 07:57:39 end=2026-11-07 07:58:11 elapsed=33s bound=1200s status=OK rc=0 | 421 passed, 35 xfailed, 11 warnings in 31.64s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8green-comm-c27 start=2026-11-07 07:58:11 end=2026-11-07 07:58:47 elapsed=36s bound=1200s status=OK rc=0 | 1236 passed, 9 skipped, 13 warnings in 34.24s | [netguard] blocked 20 attempt(s) from 12 node(s)
- [pyt] tag=g8green-comm-c28 start=2026-11-07 07:58:47 end=2026-11-07 07:58:58 elapsed=11s bound=1200s status=OK rc=0 | 224 passed, 1 skipped, 10 warnings in 9.61s | [netguard] blocked 0 attempt(s) from 0 node(s)
- HEAD FAILED set (24 ids, head_failed.txt) == the base record (24 ids): `comm -13` EMPTY, `comm -23` EMPTY. The 24 = the 22 known environmental ids + the two S81-22 CRLF hygiene rows (GC-4 D7):
  - tests/test_auth_interceptor.py::test_sign_in_with_social_exception
  - tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
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
  - tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
  - tests/test_s81_s19_gap_queue.py::test_r15_hygiene
  - tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
  - tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
- branch_only_new: EMPTY.

## 5. Deviations
- DV1 (the commit trailer): step 7 of the task text names "Co-Authored-By: Claude Fable 5.1"; GC-9 and the common brief say the trailer names the committing agent's OWN model, so the trailer is "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" (this agent runs on Opus 5.5).
- DV2 (CLAUDE.md :92): GC-7's sentence is appended at the end of the dated apply record as ruled; the earlier clause of the same line ("045 ... and 047 ... WRITTEN, NOT APPLIED (the owner applies 045 ...)") was NOT rewritten (GC-7 names only the appended sentence). Open question Q1.
- DV3 (G8 block heading date): the heading reads 2026-11-07 (the GREEN day) where spec 12.5 proposed 2026-11-06 (the spec day); the rest of the heading as the spec words it.
- DV4 (store_labels host regex): the KB_HOST_REGEX shape is copied as a local `_HOST_RX` instead of imported from kb_service (S81-14 P01 forbids a kb_service importer); the RED R2 row asserts the table against kb_service.KB_HOST_REGEX itself.
- DV5 (label_for signature): `label_for(price, lang, labels=None)`: the optional third argument lets label_prices load the table ONCE per pass; callers with two arguments behave as the spec contract.
- No E-row; no existing test edited; the golden not re-recorded; the RED files byte-identical.

## 6. Prove-nothing / not measured
- Mutants were not re-run at GREEN (the RED round killed 24 / 24 on the prototype; the adversary re-applies at least ten on these bytes, GC-11).
- The FULL jest (final round) and the hook test files (no .githooks change) not run.

## 7. Open questions
- Q1: CLAUDE.md :92 now says both "045 ... WRITTEN, NOT APPLIED" (the older clause) and "045 ... applied 2026-11-06" (the GC-7 sentence, later in the line). Principle 5 (edit in place) suggests rewriting the older clause; GC-7 named only the append. Rule whether the final round rewrites the older clause in place.

## 8. State at the end
- `git status --short` of sc-s81-g8: empty (every file committed); HEAD fe2ba6703d22e48842bf4af2d714d0716aa5f8bf on feature/s81-g8-followups.
- No flag set in any .env or the OS environment (exported only inside the one runner call); no .env read; no network beyond the netguard-blocked attempts inside the tests; no package manager; no git write in any other worktree; no pytest left running.
- Artifacts (all under <scratchpad>/S81-G8_green/): PR_BODY.md, S81-G8_GREEN_REPORT.md, units_off.log, units_on.log, ciorder.log, secretscan.log, comm_head_c00..c28.log, chunks_head_driver.log, comm_pyt_lines.txt, comm_head_members.txt, head_failed.txt, base_failed.txt, corpus_head.log, fences.log, commit.log, commit_msg.txt, files_table.json, edit_claude.py, chunks_head.py, write_pr_body.py; byte copies in <scratchpad>/S81-G8_green_before/.

# S81-G3 GREEN REPORT (G3 KB-INGEST: S81-17 KB-INGEST + D05 FIELD-STATUS, D14 LIVE-ROBOTS)

Agent: the G3 GREEN agent, model Opus 5.5 (claude-opus-5-5); the commit trailer names Opus 5.5 (the brief's template said Fable 5.1; the brief also says the trailer names the agent's own model). Written through the shell (python). Base 744616e37d031923e522e30740b687de76482ee9; branch feature/s81-g3-kb-ingest; HEAD efa33a81dc6eca04f8f41c024cf3fc627a22032f (ONE commit through the hook, ruff in the hook: All checks passed); no push, no PR, no rebase.

## Files (git diff --numstat 744616e3 HEAD; sha256 of the working-copy bytes)

| file | +/- | sha256 before | sha256 after |
|---|---|---|---|
| app/services/live_robots.py (NEW, LF, ASCII) | 510/0 | - | dd30877efa8ecab452b0e5f24f78199f4574087990bb18d3370cff6411096a9f |
| app/services/kb_ingest.py (NEW, LF, ASCII) | 509/0 | - | 8b09ed2090f9ed6aea67883326956b4160992d7653d62321f6d6ef5a03eef604 |
| app/services/price_service.py | 19/1 | 8f78106dbbff733ee2fbf4013f40395e48382b8882c7ffe375813c7320de4f4b | 477299a52b98675a8d263f83201e5a23b710fd85b8349bd06279dca675210459 |
| app/services/shopify_pdp_service.py | 10/0 | 9e97c7886e0a43fb1bf0a8674729807b8a60030ecefe2bfab8dc24a26fc701f6 | 81d4f55fa3b5d5921f2b16da57339b433319daf30d800e1fc0d96b9c22d39d89 |
| app/services/woocommerce_service.py | 13/0 | d9ff135036ed7a73a9623121bcf31b5f5f4305db6b6abaa47c2db7ed5da59317 | 36f4839232bf4d6b3d5954fdc989f540b171ed5b9f64e88fd26169712eea8557 |
| app/services/algolia_service.py | 16/0 | 4cf165ade89d42166671c0dfcc0ad357f09174f7d661c745f4f6e84c365ae157 | 0b53c10ea830db659be06ee6a4ac115d0eaabf157dd92105450b7f85faf1ec35 |
| app/services/url_extraction_service.py | 23/3 | f0cfb93415af8b695d6d5e357811e616f93a39914a4404fb664a392e8d13e542 | 7fb81322ca9886de97bc4eb313cf0afeb4805c1b60e7b80a62d65f25dac48684 |
| app/services/structured_comparison_service.py | 66/0 | 2b9218bcca913fe49cbe16168a70de5fadf107c15ac9c32d6f90565dc72840fe | 79b1f729c46f4c48e403702660e31ce01547563a7a9a811308c7d340dfd45998 |
| tests/test_s81_kb_schema.py (E1 / E2) | 9/1 | c75c62d37b161a9170284529b2600402cf6b577559a37e1bbd562647563cefa4 | 9f420bc0a82b5610732f91279c8f3cfbfdcc97aae02f15341a498757011ed59e |
| tests/test_s81_g3_gate_rows.py (NEW, LF, ASCII) | 351/0 | - | 16c37591af3fa22142d3418cca96886f23d814c3ca79eaffab1f8a6f412190b5 |
| CLAUDE.md (CRLF kept) | 6/1 | d5aa3fdd9d6ef4146c0987abdecb3bf96130f73b781593908826aa448798c8d6 | 4dbfca973ab868156ab6ed1544236c9c9135d74e927a8347c45c843e03e8e4c0 |
| the four FROZEN RED files | committed unchanged | GC-1 hashes | 542cd259... / 547cdb74... / 55851c04... / 514d1cd2... (re-hashed first and last: equal) |

Byte copies of every existing file before the first edit: S81-G3_green_before/ (SHA256SUMS.txt). Existing files keep CRLF (the Edit tool; git diff --stat shows hunks only, 162 insertions / 6 deletions over the 8 edited files); new files LF + 0 bytes > 127. Footprint 15 files = spec 12.3's 14 + the gate-rows file (GC-10): the SAFE class holds.

## Implementation notes (own code; the RED prototype read as a reference only)

- live_robots.py: readers; VERDICT_REASONS; url_verdict (G2 order, `_origin_of` re-implemented, rating_host_allowed for the robots leg, fail-closed bad_url); host_of; match_row (exact, else the longest registry parent host; shared with kb_ingest); the memo {rows, loaded_at, good_at, warned_at} under a threading.Lock, single-flight refresh per loop in a fresh contextvars.Context through asyncio.wait_for(asyncio.to_thread(_read_rows)) (columns host,status,deny,robots,challenge, in_ status live/blocked, order host, range 0..499 pages), one WARNING per memo window on failure; records_snapshot age-aware (R-G3-5); load_records_sync stores the good load; gate (flag first; skip = robots_skip + one INFO line source/host/reason); record / record_response / record_url / outcome_of (headers optional, never raises); bind_attempts / flush_attempts (read + unbind, health sub-flag, no-loop DEBUG drop, async_utils.fire_and_forget label live_robots_health_flush -> run_redis_offloop_pool -> ONE pipeline HINCRBY + EXPIRE, one exec; a failure one WARNING `[LIVE_ROBOTS] health flush failed: <type>`); robots_entry_lookup assigned to jsonld_widen.ROBOTS_ENTRY_LOOKUP at import. Seams _now / _monotonic / _admin_client / _redis_client (called; the RED fakes are callable). No `robots_registry`, `QarenBot`, `shopify_pdp_service` text; never imports shopify_pdp_service.
- Hooks: price_service (module import beside :46; curl_fetch_html gate + record per response + except fail; same_site initial + every hop gate, record per terminal response, except fail); shopify _fetch_once (function-local import after _hop_is_allowed_async, gate per hop, record per non-3xx response, except fail); woo (gate before each GET incl. the /v1 retry, record per final response, except fail); algolia (gate the merchant origin before the harvest and before the first explicit query; record the harvest landing GET and each explicit query outcome, except fail); url_extraction (gate at the extract_from_url caller, ok/fail from the fetch_page result; _fetch_page_v2 initial + every hop gate, record the terminal response, except fail; `_V2_FETCH_OUTCOME_REASONS` + robots_skip). fetch_page byte-unchanged (AST source compare base == HEAD: True). UA / impersonate unchanged.
- kb_ingest.py: readers, gap_max knob, seams, kb_leaf (the one function-local import), rung_for, field_status (closed 2.2 vocabulary; vision default False; the identity source kept when unknown), build_job (deep-copied projection, assess_result identity), run_job as spec 2.3 (snapshot else load_records_sync; cards + offers + images + reviews at high; gaps at high or medium; GC-6 Decimal match; CAS with gap_cas_lost; pdp_ guard as an explicit skip, never an assert; GAP_MAX; ONE ints-only INFO line with elapsed_ms). The six KB_*_TABLE constants one per line.
- scs: two module imports beside the jsonld_widen import; `live_robots.bind_attempts()` in _init_provider_attempts; `_kb_ingest_tail` beside _stamp_unit_metadata (flags first; projection in try/except one WARNING; exposure only under ENABLE_FIELD_STATUS_METADATA; `_fire_and_forget(asyncio.to_thread(kb_ingest.run_job, snap), "kb_ingest")`); REST call between the moderation refusal block and the behaviour-profile block; stream call before `yield ("settle_complete", ...)`; vision=bool(vision_products) at both exits; two bare `finally: live_robots.flush_attempts()` arms (no return in a finally).

## Runs (every pytest through pyt.py, one at a time)

```
[pyt] tag=g3green-red-off1 ... elapsed=18s bound=600s status=OK rc=0   (2 RED files + kb_schema: 715 passed)
[pyt] tag=g3green-gr-off1 ... status=FAIL rc=1   (my own GR2 algolia_explicit expectation: an empty-hits 200 retries the core term, 2 ok; the row fixed to a non-empty hits list)
[pyt] tag=g3green-gr-off2 start=2026-11-04 12:19:38 end=2026-11-04 12:19:41 elapsed=3s bound=600s status=OK rc=0   (10 passed)
[pyt] tag=g3green-unit-off start=2026-11-04 12:19:49 end=2026-11-04 12:20:07 elapsed=18s bound=600s status=OK rc=0   (725 passed)
[pyt] tag=g3green-unit-on start=2026-11-04 12:20:08 end=2026-11-04 12:20:26 elapsed=18s bound=600s status=OK rc=0   (725 passed, the four flags exported in ONE runner call)
[pyt] tag=g3green-g3-grm1 start=2026-11-04 12:20:46 end=2026-11-04 12:20:49 elapsed=4s bound=600s status=FAIL rc=1   (G3-GRM1 KILLED by GR1[returned_numeric-0])
[pyt] tag=g3green-g3-grm2 start=2026-11-04 12:20:50 end=2026-11-04 12:20:53 elapsed=4s bound=600s status=FAIL rc=1   (G3-GRM2 KILLED by GR2[algolia_explicit, algolia_harvest, url_extraction_base, url_extraction_v2])
[pyt] tag=g3green-ci-off start=2026-11-04 12:21:02 end=2026-11-04 12:21:48 elapsed=46s bound=1200s status=FAIL rc=1   (3 failed: r06 + two test_shopify_pdp_json TestWiringStaysFlagGated nodes: my live_robots docstring named shopify_pdp_service; text removed)
[pyt] tag=g3green-ci-off2 start=2026-11-04 12:22:12 end=2026-11-04 12:22:58 elapsed=46s bound=1200s status=FAIL rc=1   (1953 passed / 1 failed = r06 only: 1757 existing + 196 G3)
[pyt] tag=g3green-final-off start=2026-11-04 13:01:38 end=2026-11-04 13:01:57 elapsed=19s bound=600s status=OK rc=0   (725 passed at HEAD)
[pyt] tag=g3green-final-on start=2026-11-04 13:01:58 end=2026-11-04 13:02:16 elapsed=19s bound=600s status=OK rc=0   (725 passed at HEAD, four flags ON)
```
Every run: [hermeticity] sentinel checked N test(s); [netguard] blocked 0 attempt(s) from 0 node(s). Mutants on byte copies under .qa-mutation.lock, restored and sha256-verified (mutate.py). The 24 + 2 spec / RED mutants were NOT re-applied by GREEN (the adversary's step).

Lint: ruff --select E9,F63,F7,F82 --no-cache on the 2 new modules, the 6 edited app files, test_s81_kb_schema.py and the gate-rows file: All checks passed; py_compile OK.

Corpus gate at HEAD (venv python, cwd the worktree, the four flags forced OFF; ran at 12:23-12:3x, before the final docstring-only edit of live_robots.py, which no corpus path imports text from): RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef == base. Output gate_head.json, log corpus_head.log.

## Comm set (LC-6: the STORED base record at 744616e3 REUSED, ba26af35...txt, 14 FAILED ids)

612 files = the RED's 609 (COMM_SET.txt, sha ba26af35...) + tests/test_s81_d14_live_robots.py, tests/test_s81_s17_kb_ingest.py, tests/test_s81_g3_gate_rows.py (COMM_SET_HEAD.txt); 611 in 25 chunks of at most 25 (bound 1200) + tests/test_secret_scan_static.py ALONE. Chunks 00-10 ran before the last edit (12:42:12, a docstring word in live_robots.py that tests/test_legal_disclosure_s77.py::test_s77_d9_bot_page_claim_matches_the_runtime pins: the QarenBot emitter set) and were RE-RUN at the final bytes (tags ...b); the final set is the post-edit logs. HEAD FAILED ids = 14, identical to the base record; `comm -13` branch-only-NEW: EMPTY.

```
[pyt] tag=g3green-comm-00b start=2026-11-04 12:54:30 end=2026-11-04 12:55:01 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-01b start=2026-11-04 12:55:01 end=2026-11-04 12:55:23 elapsed=23s bound=1200s status=FAIL rc=1
[pyt] tag=g3green-comm-02b start=2026-11-04 12:55:24 end=2026-11-04 12:56:23 elapsed=59s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-03b start=2026-11-04 12:56:23 end=2026-11-04 12:56:54 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-04b start=2026-11-04 12:56:54 end=2026-11-04 12:57:08 elapsed=14s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-05b start=2026-11-04 12:57:08 end=2026-11-04 12:57:25 elapsed=16s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-06b start=2026-11-04 12:57:25 end=2026-11-04 12:58:36 elapsed=71s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-07b start=2026-11-04 12:58:36 end=2026-11-04 12:59:37 elapsed=61s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-08b start=2026-11-04 12:59:37 end=2026-11-04 13:00:07 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-09b start=2026-11-04 13:00:07 end=2026-11-04 13:00:29 elapsed=22s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-10b start=2026-11-04 13:00:30 end=2026-11-04 13:00:41 elapsed=11s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-11 start=2026-11-04 12:42:22 end=2026-11-04 12:42:49 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-12 start=2026-11-04 12:42:49 end=2026-11-04 12:43:15 elapsed=26s bound=1200s status=FAIL rc=1
[pyt] tag=g3green-comm-13 start=2026-11-04 12:43:15 end=2026-11-04 12:43:45 elapsed=29s bound=1200s status=FAIL rc=1
[pyt] tag=g3green-comm-14 start=2026-11-04 12:43:45 end=2026-11-04 12:44:06 elapsed=21s bound=1200s status=FAIL rc=1
[pyt] tag=g3green-comm-15 start=2026-11-04 12:44:07 end=2026-11-04 12:46:27 elapsed=140s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-16 start=2026-11-04 12:46:27 end=2026-11-04 12:47:54 elapsed=87s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-17 start=2026-11-04 12:47:54 end=2026-11-04 12:49:12 elapsed=78s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-18 start=2026-11-04 12:49:13 end=2026-11-04 12:50:10 elapsed=57s bound=1200s status=FAIL rc=1
[pyt] tag=g3green-comm-19 start=2026-11-04 12:50:10 end=2026-11-04 12:51:10 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-20 start=2026-11-04 12:51:10 end=2026-11-04 12:51:28 elapsed=18s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-21 start=2026-11-04 12:51:28 end=2026-11-04 12:52:27 elapsed=59s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-22 start=2026-11-04 12:52:28 end=2026-11-04 12:53:14 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-23 start=2026-11-04 12:53:14 end=2026-11-04 12:53:42 elapsed=29s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-24 start=2026-11-04 12:53:43 end=2026-11-04 12:53:55 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=g3green-comm-secret start=2026-11-04 12:53:56 end=2026-11-04 12:54:07 elapsed=12s bound=1200s status=OK rc=0
```

HEAD FAILED (== base, GC-9 / DV-9):
```
tests/test_auth_interceptor.py::test_sign_in_with_social_exception
tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
```

## Client fences (by path through the junction; jest by path, never npx / npm)

13/14 suites PASS; nativeBundle.w37 FAIL with exactly the 4 known drift nodes (d5, k2, k4, k5); Tests 4 failed / 236 passed; jest 29.7.0, node v24.11.1; [jest] tag=g3green-fences start=13:00:53 end=13:01:05 rc=1. Suites: brand/inAppMark.u4c, clientTruth/medicalNote.s74, privacyManifest.s74, shareTruth.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService (+ .edges), ResultsScreen.timeout. Log fences.log. The hook test files NOT run (no .githooks change). The FULL jest suite NOT run (LC-7: the last round before the PR).

## Deviations

- DV-G1: the job writes cards AND gaps only for products whose category is `fragrances` (KB_CATEGORY). Spec 2.3 step 3 names the category for the cards; step 8 (gaps) does not. Measured: kb_product_id mints `fragrances|apple|15-iphone|-` for an electronics name, so without the check a non-fragrance compare would seed fragrance gap rows. Stricter than the spec; every RED row uses fragrance products.
- DV-G2: the comm set ran in 25 chunks, not 17: 611 files at <= 25 per chunk cannot fit 17 (the RED's 17 chunks covered its 421 run-at-base members).
- DV-G3: GC-5 recording placement chosen by GREEN: algolia records the harvest landing GET (merchant origin) and each explicit-store query outcome (None = fail) under the merchant host; the harvest-path DSN queries are not counted; the URL base path records ok / fail from the fetch_page result (no status, so no challenge) at the caller (fetch_page untouched). An exception raised after a recorded response (a non-JSON 200 at woo, a body read at curl) can count ok + fail for one attempt (stated limit).
- DV-G4: helpers beyond the spec's surface in live_robots: host_of, match_row (shared by row_for_host and kb_ingest), outcome_of, record_response, record_url, health_ttl_seconds; in kb_ingest: gap_max, rung_for, D05_FIELDS.
- DV-G5: the commit trailer names Opus 5.5 (this agent's model), not the template's Fable 5.1.
- DV-G6: the CI-order OFF run (ci-off2) and the corpus gate predate the final docstring-only edit of live_robots.py; the final unit runs (final-off / final-on) and the comm chunks ran at the committed bytes.

## Open questions

- Q-G1: accept DV-G1 (fragrance-only gaps) or follow spec step 8 literally?
- Q-G2: should the harvest-path Algolia DSN queries also count outcomes (today only the landing GET and the explicit-store queries do)?

## git status --short at the end

(empty: everything committed at efa33a81)

Files in this folder: PR_BODY.md, S81-G3_GREEN_REPORT.md, gate_head.json, corpus_head.log, red_off1.log, gr_off*.log, unit_off.log, unit_on.log, final_off.log, final_on.log, ci_off.log, ci_off2.log, G3-GRM1.log, G3-GRM2.log, mutate.py, comm/ (chunk logs and lists), comm_head.py, comm_rerun.py, comm_progress.txt, comm_pyt_lines.txt, comm_head_failed.txt, comm_branch_only_new.txt, COMM_SET_HEAD.txt, fences.log, fences_summary.txt, claude_md_edit.py.

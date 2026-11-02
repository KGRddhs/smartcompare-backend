# S81-G1 PRICE-PIPELINE RED report (D08 JSONLD-WIDEN + S81-23 BYPASS-RETIRE)

- Agent: RED, Opus 5.5 (claude-opus-5-5). Window 2026-11-02 12:36 - 13:25 AST. Written through the shell (python), not the Write tool (harness rule 2026-10-24).
- Base: 6c14ac954f601902d322547de04982033aca5925 (origin/main). Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g1, detached at the base, `git status --short` EMPTY at 12:36 before any run.
- e7c81956 -> 6c14ac95 re-measure: `git diff --stat e7c81956 6c14ac95 -- app scripts tests migrations .github` is EMPTY (only SmartCompareApp/, CLAUDE.md and docs/privacy-data-inventory.md differ), so every app/ / scripts/ / tests/ file:line of the spec holds at 6c14ac95. The six pin files were re-run at 6c14ac95 (below). CLAUDE.md anchors re-measured at 6c14ac95 (992 lines): :141 (Scrape.do residential sentence), :142 (curl_cffi impersonate paragraph), :338 (ZYTE_API_KEY 'cracks Akamai'), :348 (M6 judge.me clause), :377 (runbook step (2)) UNCHANGED; S81-15 block :517-520; the NEW S81-08 block :522-530 is the last SESSION 81 block (the S81-G1 block goes after it); the sephora bullet moved :805-808 -> :814-817, 'controls curl cracks free' :813 -> :822, 'Scrape.do - narrow keeper' :818-820 -> :827-829 (the file spells it with an EM DASH, the spec quotes an ASCII hyphen).
- Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-G1_red (notes.md, comm_files.txt, comm_reasons.tsv, comm_derive.py, run_base_driver.py, prototype.diff, proto_apply.py, mutants.py, mutants_results.jsonl, mut_logs/, the run logs).

## 1. Files written (only these three, untracked, in the real worktree)

| path | bytes | sha256 | bytes>127 | CR | 8+digit runs |
|---|---|---|---|---|---|
| tests/test_s81_d08_jsonld_widen.py | 51451 | a0748bcff862e91dffa0ff99905f59b689ebefa4f2bfbfeafa081530b82c040c | 0 | 0 | 0 |
| tests/fixtures/s81_d08_rating_flag_off_golden.json | 9194 | 92d0686b6adcf53f3c07aa06bd40a55c1e6d59cb12de58c624d0e49331742c33 | 0 | 0 | 0 |
| tests/test_s81_s23_bypass_retire.py | 17402 | 6cf8c6d3f701636f839ab0073d4f29c73d8fcc602648458aa15190bfb7c930dc | 0 | 0 | 0 |

All pure ASCII, LF, no 8+ digit literal (GTINs built from short parts), no credential shape (tokens/keys built at run time from low-entropy words), synthetic hosts only (store-a/store-b/pharmacy-a/brand-a/cdn-a .example.com, img.other-b.example.net; cdn.shopify.com is the spec's frozen CDN tuple; fimgs.net / fragrantica / parfumo appear only as DENIED inputs). ruff --select E9,F63,F7,F82,F401,F841: All checks passed; py_compile OK; the golden json.loads OK.

## 2. Base measurements at 6c14ac95 (step 2)

### 2.1 The six spec pin files + the secret scan (real worktree, before the RED files existed)
    [pyt] tag=g1red-secret start=2026-11-02 12:42:29 end=2026-11-02 12:42:37 elapsed=8s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-secret.log
    [pyt] tag=g1red-pins6 start=2026-11-02 12:42:37 end=2026-11-02 12:42:44 elapsed=6s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-pins6.log
    g1red-pins6: 183 passed, 1 warning in 5.39s  (spec at e7c81956: 183 passed)
    g1red-secret (tests/test_secret_scan_static.py ALONE): 31 passed, 1 warning in 7.64s

### 2.2 The corpus gate at BASE (R-G1-8, the base figure of record)
Command (scratch worktree S81-G1_red/wt detached at 6c14ac95, .venv-qaren): `python scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_IMAGE_PIPELINE_V2,ENABLE_JSONLD_RATING --out S81-G1_red/gate_base.json` (12:46:01 - 12:52:47, rc=0):
    RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656
    OVERALL SHA256 9f9f9aeb185f7e811aa4292141d57a567e0aaaf7a1cc28f3b5ece0ac51ecaf33
    rc=0

### 2.3 The comm set at base = the BASE RECORD (LC-6)
- Derivation (comm_derive.py, union rule): the spec's single seed grep reproduced with Python re (the shell ERE form has an unbalanced paren) = **539** files at 6c14ac95, exactly the spec's count; 532 are test modules and 7 are non-test helpers (tests/_env_safety.py, tests/_hermeticity.py, tests/_retro_r_mig_sql.py, tests/conftest.py, tests/fixtures/_gen_rubric_truth_flag_off_digests.py, tests/fixtures/_gen_rubric_truth_flag_on_golden.py, tests/w4_11_prompt_digest_recorder.py). UNION module + symbol references (17 modules incl. scrapedo_service / seed_zyte_luxury / source_router, 24 symbols), the named source-scanning pins, string-path / __file__ / inspect / ast / walker / read_text readers of app/ or scripts/ / .github readers, app.main importers + TestClient users, CLAUDE.md readers, the W4-11 digest recorder users: +61. MINUS tests/test_m6_c5_judgeme_html_reviews.py (deleted by D08, R-G1-4) and the 4 test_precommit_hook*.py. **592 files**; NETWORK_FLAKY_EXCLUDE (4 nodes) deselected where present. List: S81-G1_red/comm_files.txt; per-file reasons: S81-G1_red/comm_reasons.tsv. No SmartCompareApp-scanning class: the change is not client-visible (backend, dark).
- Reuse: 416 files taken per file from the stored 6c14ac95 records (0ea73814... S81-12 rebase-fix: 108 members; 336233f0... S81-10 RED: 413; c9f7585d... S81-09 rebase: 183; they agree on shared files); the 176 not yet recorded ran here in 8 chunks of 22 (bound 1200), ONE driver, one pytest at a time, in the REAL worktree at the base with the RED files not yet present, unit flags and SCRAPEDO_SUPER removed from the child env.
- Stored: harness/base_records/6c14ac954f601902d322547de04982033aca5925/89037313e1996445e90b7147ea2ebcab9c41cb06a993f4ed33988d7d9877ed41.{files,txt,pyt.log}.
- [pyt] lines (driver S81-G1_red/g1red_driver.log):
    [pyt] tag=g1red-cb-00 start=2026-11-02 12:42:44 end=2026-11-02 12:42:55 elapsed=11s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-00.log
    [pyt] tag=g1red-cb-01 start=2026-11-02 12:42:55 end=2026-11-02 12:43:07 elapsed=12s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-01.log
    [pyt] tag=g1red-cb-02 start=2026-11-02 12:43:07 end=2026-11-02 12:43:17 elapsed=10s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-02.log
    [pyt] tag=g1red-cb-03 start=2026-11-02 12:43:17 end=2026-11-02 12:43:29 elapsed=12s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-03.log
    [pyt] tag=g1red-cb-04 start=2026-11-02 12:43:29 end=2026-11-02 12:43:41 elapsed=12s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-04.log
    [pyt] tag=g1red-cb-05 start=2026-11-02 12:43:41 end=2026-11-02 12:43:54 elapsed=12s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-05.log
    [pyt] tag=g1red-cb-06 start=2026-11-02 12:43:54 end=2026-11-02 12:44:05 elapsed=11s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-06.log
    [pyt] tag=g1red-cb-07 start=2026-11-02 12:44:05 end=2026-11-02 12:44:16 elapsed=11s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\comm\g1red-cb-07.log
    [netguard]   <collection>: 1 attempt(s) outside any test, e.g. socket.getaddrinfo openaipublic.blob.core.windows.net:443
    FAILED tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
    FAILED tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
- Chunk summaries:
    g1red-cb-00: 519 passed, 1 warning in 10.41s
    g1red-cb-01: 579 passed, 1 xfailed, 1 warning in 10.72s
    g1red-cb-02: 374 passed, 1 warning in 9.19s
    g1red-cb-03: 267 passed, 1 xfailed, 1 warning in 10.55s
    g1red-cb-04: 2 failed, 534 passed, 1 skipped, 8 deselected, 1 warning in 11.22s
    g1red-cb-05: 489 passed, 1 warning in 11.45s
    g1red-cb-06: 458 passed, 1 warning in 10.13s
    g1red-cb-07: 338 passed in 10.35s
- BASE FAILED set of the 592-file set (8 nodes): tests/test_auth_interceptor.py::test_sign_in_with_social_exception, tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully, tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities, tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  Six are tests/.pre_impl_failures.txt rows (CI-deselected: test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2 -- the last two measured here, deterministic TypeErrors); test_prompt_truth x2 = the known cold-tiktoken base noise (the netguard line above is tiktoken's encoding download at collection). The spec 1.10 names only the six pin files (183 green); nothing else fails.
- The fourteen backend-scanning CLIENT jest fences are GREEN's and the rebase's duty (orchestrator junction): brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout. medicalNote.s74 reads app/services/extraction_service.py (the _PHARMACY_TABLET_TOKENS set; D08 does not move it).

## 3. The RED run at base (step 4, the final bytes, REAL worktree)
    [hermeticity] sentinel checked 173 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [hermeticity] sentinel checked 33 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=g1red-d08-base2 start=2026-11-02 13:17:21 end=2026-11-02 13:17:27 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\d08_base2.log
    [pyt] tag=g1red-s23-base2 start=2026-11-02 13:17:28 end=2026-11-02 13:17:32 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\s23_base2.log
- D08 tests/test_s81_d08_jsonld_widen.py: 98 failed, 75 passed, 1 warning in 5.66s; every failure an AssertionError (98 `E ... AssertionError` lines, 0 ERROR nodes); the failed set is exactly every param of R1-R21 (R1 11, R2 6, R3 15, R4 12, R5 1, R6 2, R7 3, R8 1, R9 4, R10 11, R11 4, R12 17, R13-R14 1 each, R15 2, R16-R20 1 each, R21 2); every PIN row green (P1 24, P2 6, P3 12, P4 12, P5 5, P6 2, P7 6, P8 6, P9 2 = 75). Ids: S81-G1_red/d08_base_failed_ids.txt.
- S81-23 tests/test_s81_s23_bypass_retire.py: 19 failed, 14 passed, 1 warning in 3.10s; every failure an AssertionError (19, 0 ERROR nodes); failed = every param of R1-R9 (R1 8, R2 4, R3-R9 1 each); PIN rows green (P1 6, P2 6, P3 1, P4 1 = 14). Ids: S81-G1_red/s23_base_failed_ids.txt.
- The same run on the previous bytes (identical rows and asserts; only the explicit space-free / digit-free pytest ids were added after it), real worktree: d08 98 / 75, s23 19 / 14, all AssertionError:
    [pyt] tag=g1red-d08-base start=2026-11-02 13:12:22 end=2026-11-02 13:12:29 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\d08_base.log
    [pyt] tag=g1red-s23-base start=2026-11-02 13:12:29 end=2026-11-02 13:12:33 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\s23_base.log
- Earlier base runs in the scratch worktree (before R15 gained its second param and one unused import was dropped): d08 97 failed / 75 passed, s23 19 / 14, all AssertionError:
    [pyt] tag=g1red-d08-base-s start=2026-11-02 12:59:08 end=2026-11-02 12:59:14 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\d08_base_scratch.log
    [pyt] tag=g1red-s23-base-s start=2026-11-02 12:59:30 end=2026-11-02 12:59:34 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\s23_base_scratch.log
- The literals (P1/P2/P3/P4/P7, S81-23 P2) and the golden were RECORDED AT BASE by a temporary recorder test in the scratch worktree only (deleted after): [pyt] tag=g1red-recorder start=2026-11-02 12:58:20 end=2026-11-02 12:58:24 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\recorder.log
- Rows: 30 RED (D08 R1-R21, S81-23 R1-R9) + 13 PIN (D08 P1-P9, S81-23 P1-P4) as R-G1-9 states; 173 + 33 = 206 test nodes.

## 4. Prototype (step 5; scratch worktree, thrown away; diff S81-G1_red/prototype.diff, applier proto_apply.py)
- Change list implemented as spec 3 (both units) + R-G1-1..7: the leaf app/services/jsonld_widen.py (readers, allowed_image_url, valid_gtin, size_text, rules_allow fail-closed, rating_host_allowed, stamp_jsonld_facts, channel1_rating, ROBOTS_ENTRY_LOOKUP = _no_entry, _now); price_service (best_rating under the rating flag, size under the image flag, the gated stamp before `return _finish(result)` in the JSON-LD branch, the pharmacy dict stamped); scs (piggyback ON branch first, channel-1 block, GPT fallback only OFF); response_builder (derive loop guarded by one read, reviews post-pass); extraction_service (REVIEWS_EXTRACTION_SYSTEM_NO_RATING by two count-checked replaces, the per-call pick, the normaliser belt); judge.me module + pin + 8 fixtures deleted; seed_spec_spine docstring; scrapedo_service tri-state reader + per-call params; seed_zyte_luxury lists emptied; CLAUDE.md five phrases rewritten + the S81-G1 block after the S81-08 block.
- [pyt] lines (both unit files in one run):
    ON (ENABLE_IMAGE_PIPELINE_V2/ENABLE_JSONLD_RATING/ENABLE_SCRAPEDO_SUPER=true exported): 205 passed, 1 warning in 4.03s
    [pyt] tag=g1red-proto-on start=2026-11-02 13:02:36 end=2026-11-02 13:02:41 elapsed=5s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\proto_on.log
    OFF (unset): 205 passed, 1 warning in 3.26s
    [pyt] tag=g1red-proto-off start=2026-11-02 13:02:47 end=2026-11-02 13:02:51 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\proto_off.log
    ON, final RED bytes: 206 passed, 1 warning in 3.65s
    [pyt] tag=g1red-proto-on2 start=2026-11-02 13:11:54 end=2026-11-02 13:11:58 elapsed=5s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\proto_on2.log
    OFF, final RED bytes: 206 passed, 1 warning in 3.77s
    [pyt] tag=g1red-proto-off2 start=2026-11-02 13:11:59 end=2026-11-02 13:12:04 elapsed=5s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\proto_off2.log
    ON, FINAL bytes (scratch worktree re-created at 6c14ac95, the identical prototype re-applied: tracked diff and leaf byte-equal to round 1): 206 passed, 1 warning in 3.91s
    [pyt] tag=g1red-proto-on3 start=2026-11-02 13:18:09 end=2026-11-02 13:18:14 elapsed=5s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\proto_on3.log
    OFF, FINAL bytes: 206 passed, 1 warning in 3.50s
    [pyt] tag=g1red-proto-off3 start=2026-11-02 13:18:14 end=2026-11-02 13:18:19 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\proto_off3.log
  Every RED row green and every PIN row green in both states (each row sets its own flag state, so the exported ON and the unset runs are equal by design).
- Flag-OFF byte identity of the prototype over the corpus (same command as 2.2, run on the prototype, 13:03:03 - 13:09:45):
    RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656
    OVERALL SHA256 9f9f9aeb185f7e811aa4292141d57a567e0aaaf7a1cc28f3b5ece0ac51ecaf33
    rc=0
  = the base OVERALL SHA256 (equal).

## 5. Mutation table (step 6; run TWICE: round 1 on the pre-id bytes (mutants_results_round1.jsonl, mut_logs_round1/, tags g1red-mut-*), round 2 on the FINAL bytes (below: mutants_results.jsonl, mut_logs/, tags g1red-mut2-*), identical verdicts; byte copies of the prototype, exact-string edit matching once, the FULL unit file per mutant (a superset of the -k rows), restore + sha256 compare = OK for all 28, mutation lock held and released)

| id | mutant | file | spec killers | killed by (every failing row) | assertion only | [pyt] |
|---|---|---|---|---|---|---|
| D-M1 | image flag default true | jsonld_widen.py | P1, P6 | d08_p1_reduced_result_off_literal, d08_p2_pharmacy_off_literal, d08_p3_candidate_off_literal, d08_p4_piggyback_off, d08_p6_seam_never_called_off, d08_r1_flag_readers_per_call | yes | elapsed=4s FAIL rc=1 |
| D-M2 | rating flag reader cached at import | jsonld_widen.py | R1 | d08_r13_default_seam_no_rating, d08_r14_channel1_fills_empty_slot, d08_r15_provider_rating_wins, d08_r16_no_derive_on, d08_r17_reviews_projection_jsonld_rating, d08_r18_prompt_variant, d08_r19_normaliser_belt, d08_r1_flag_readers_per_call, d08_r21_candidate_additions_on, d08_r7_rating_fact_on_scaled, d08_r8_pharmacy_producer_on | yes | elapsed=5s FAIL rc=1 |
| D-M3 | allowed_image_url accepts http | jsonld_widen.py | R3, R9 | d08_r3_image_policy_refuses, d08_r5_reduced_result_image_url_on, d08_r9_piggyback_on | yes | elapsed=4s FAIL rc=1 |
| D-M4 | raster check dropped | jsonld_widen.py | R3 | d08_r3_image_policy_refuses | yes | elapsed=4s FAIL rc=1 |
| D-M5 | deny check behind data_guards_v2_enabled() | jsonld_widen.py | R3 | d08_r3_image_policy_refuses | yes | elapsed=4s FAIL rc=1 |
| D-M6 | first-party match drops the www. normalisation | jsonld_widen.py | R2 | d08_r2_image_policy_accepts | yes | elapsed=4s FAIL rc=1 |
| D-M7 | gtin check digit not verified | jsonld_widen.py | R4, R6 | d08_r4_valid_gtin, d08_r6_reduced_result_facts_on | yes | elapsed=4s FAIL rc=1 |
| D-M8 | rules_allow evaluates only star | jsonld_widen.py | R12 (qarenbot row) | d08_r12_host_rule_refuses | yes | elapsed=4s FAIL rc=1 |
| D-M9 | expiry ignores next_reread | jsonld_widen.py | R12 (expired) | d08_r12_host_rule_refuses | yes | elapsed=4s FAIL rc=1 |
| D-M10 | rules_allow fails OPEN on a malformed rule | jsonld_widen.py | R10 | d08_r10_rules_allow, d08_r12_host_rule_refuses | yes | elapsed=4s FAIL rc=1 |
| D-M11 | channel 1 overwrites a provider rating | structured_comparison_service.py | R15 | d08_r15_provider_rating_wins | yes | elapsed=4s FAIL rc=1 |
| D-M12 | GPT fallback still applied ON | structured_comparison_service.py | R13 | d08_r13_default_seam_no_rating | yes | elapsed=4s FAIL rc=1 |
| D-M13 | derive loop not guarded | response_builder.py | R16 | d08_r16_no_derive_on | yes | elapsed=4s FAIL rc=1 |
| D-M14 | stamp not gated (call outside the flag check) | price_service.py | P1, P6 | d08_p1_reduced_result_off_literal, d08_p6_seam_never_called_off | yes | elapsed=5s FAIL rc=1 |
| D-M15 | piggyback ON falls through to the base http branch | structured_comparison_service.py | R9 | d08_r9_piggyback_on | yes | elapsed=5s FAIL rc=1 |
| D-M16 | prompt variant keeps total_reviews | extraction_service.py | R18 | d08_r18_prompt_variant | yes | elapsed=4s FAIL rc=1 |
| D-M17 | rating not rescaled by best_rating | jsonld_widen.py | R7 | d08_r7_rating_fact_on_scaled | yes | elapsed=4s FAIL rc=1 |
| D-M18 | _jsonld_facts written without the _ prefix | jsonld_widen.py | P9 / R5 | d08_p9_wide_pin_both_states, d08_r6_reduced_result_facts_on, d08_r7_rating_fact_on_scaled, d08_r8_pharmacy_producer_on | yes | elapsed=4s FAIL rc=1 |
| S-M1 | unset new name treated as OFF (the clean cut) | scrapedo_service.py | P1 (true), P2 | s23_p1_unset_matches_base_params, s23_p2_unset_matches_base_routing, s23_p3_reset_hook_callable, s23_p4_geocode_default, s23_r3_per_call_no_reset | yes | elapsed=4s FAIL rc=1 |
| S-M2 | legacy read gains .strip() | scrapedo_service.py | P1 ( true) | s23_p1_unset_matches_base_params, s23_p2_unset_matches_base_routing | yes | elapsed=4s FAIL rc=1 |
| S-M3 | legacy read accepts 1 | scrapedo_service.py | P1 (1) | s23_p1_unset_matches_base_params, s23_p2_unset_matches_base_routing | yes | elapsed=4s FAIL rc=1 |
| S-M4 | new flag read once and cached | scrapedo_service.py | R3 | s23_r1_reader_exists_and_wins, s23_r2_new_false_kills_legacy, s23_r3_per_call_no_reset, s23_r4_render_params_new_off, s23_r5_routing_new_off | yes | elapsed=4s FAIL rc=1 |
| S-M5 | new false ignored when legacy true | scrapedo_service.py | R2, R4, R5 | s23_r2_new_false_kills_legacy, s23_r3_per_call_no_reset, s23_r4_render_params_new_off, s23_r5_routing_new_off | yes | elapsed=4s FAIL rc=1 |
| S-M6 | _super_enabled still reads the cache | scrapedo_service.py | R5 | s23_r5_routing_new_off | yes | elapsed=4s FAIL rc=1 |
| S-M7 | a seed entry left in TRUTH_CRITICAL_SEEDS | seed_zyte_luxury.py | R6, R7 | s23_r6_seed_lists_retired, s23_r7_main_makes_no_zyte_call | yes | elapsed=4s FAIL rc=1 |
| S-M8 | geoCode default changed | scrapedo_service.py | P4 | s23_p4_geocode_default | yes | elapsed=4s FAIL rc=1 |
| O-M1 | SCRAPEDO_SUPER (legacy) cached at import under the new flag | scrapedo_service.py | P1, R3 | s23_p1_unset_matches_base_params, s23_p2_unset_matches_base_routing, s23_p3_reset_hook_callable, s23_p4_geocode_default, s23_r3_per_call_no_reset | yes | elapsed=4s FAIL rc=1 |
| O-M2 | channel 1 overwrites a non-empty (unverified) rating slot | structured_comparison_service.py | R15 (unverified) | d08_r15_provider_rating_wins | yes | elapsed=5s FAIL rc=1 |

Result: 28 of 28 KILLED (26 spec mutants D-M1..D-M18, S-M1..S-M8 + the 2 orchestrator mutants of R-G1-9: O-M1 the legacy SCRAPEDO_SUPER cached at import under the new flag; O-M2 channel 1 overwriting a non-empty (unverified) rating slot). No survivor, no equivalence ruling needed. Every failure in every mutant log is an assertion failure (0 non-assertion exception types). Full [pyt] lines:
    [pyt] tag=g1red-mut2-d-m1 start=2026-11-02 13:18:28 end=2026-11-02 13:18:32 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m1.log
    [pyt] tag=g1red-mut2-d-m2 start=2026-11-02 13:18:33 end=2026-11-02 13:18:37 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m2.log
    [pyt] tag=g1red-mut2-d-m3 start=2026-11-02 13:18:38 end=2026-11-02 13:18:42 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m3.log
    [pyt] tag=g1red-mut2-d-m4 start=2026-11-02 13:18:42 end=2026-11-02 13:18:47 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m4.log
    [pyt] tag=g1red-mut2-d-m5 start=2026-11-02 13:18:47 end=2026-11-02 13:18:51 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m5.log
    [pyt] tag=g1red-mut2-d-m6 start=2026-11-02 13:18:51 end=2026-11-02 13:18:56 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m6.log
    [pyt] tag=g1red-mut2-d-m7 start=2026-11-02 13:18:56 end=2026-11-02 13:19:00 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m7.log
    [pyt] tag=g1red-mut2-d-m8 start=2026-11-02 13:19:00 end=2026-11-02 13:19:05 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m8.log
    [pyt] tag=g1red-mut2-d-m9 start=2026-11-02 13:19:05 end=2026-11-02 13:19:10 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m9.log
    [pyt] tag=g1red-mut2-d-m10 start=2026-11-02 13:19:10 end=2026-11-02 13:19:14 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m10.log
    [pyt] tag=g1red-mut2-d-m11 start=2026-11-02 13:19:14 end=2026-11-02 13:19:19 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m11.log
    [pyt] tag=g1red-mut2-d-m12 start=2026-11-02 13:19:19 end=2026-11-02 13:19:23 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m12.log
    [pyt] tag=g1red-mut2-d-m13 start=2026-11-02 13:19:24 end=2026-11-02 13:19:28 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m13.log
    [pyt] tag=g1red-mut2-d-m14 start=2026-11-02 13:19:28 end=2026-11-02 13:19:33 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m14.log
    [pyt] tag=g1red-mut2-d-m15 start=2026-11-02 13:19:34 end=2026-11-02 13:19:38 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m15.log
    [pyt] tag=g1red-mut2-d-m16 start=2026-11-02 13:19:38 end=2026-11-02 13:19:43 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m16.log
    [pyt] tag=g1red-mut2-d-m17 start=2026-11-02 13:19:43 end=2026-11-02 13:19:47 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m17.log
    [pyt] tag=g1red-mut2-d-m18 start=2026-11-02 13:19:48 end=2026-11-02 13:19:52 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-d-m18.log
    [pyt] tag=g1red-mut2-s-m1 start=2026-11-02 13:19:52 end=2026-11-02 13:19:56 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m1.log
    [pyt] tag=g1red-mut2-s-m2 start=2026-11-02 13:19:56 end=2026-11-02 13:20:00 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m2.log
    [pyt] tag=g1red-mut2-s-m3 start=2026-11-02 13:20:00 end=2026-11-02 13:20:04 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m3.log
    [pyt] tag=g1red-mut2-s-m4 start=2026-11-02 13:20:04 end=2026-11-02 13:20:08 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m4.log
    [pyt] tag=g1red-mut2-s-m5 start=2026-11-02 13:20:08 end=2026-11-02 13:20:11 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m5.log
    [pyt] tag=g1red-mut2-s-m6 start=2026-11-02 13:20:12 end=2026-11-02 13:20:15 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m6.log
    [pyt] tag=g1red-mut2-s-m7 start=2026-11-02 13:20:15 end=2026-11-02 13:20:19 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m7.log
    [pyt] tag=g1red-mut2-s-m8 start=2026-11-02 13:20:20 end=2026-11-02 13:20:23 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-s-m8.log
    [pyt] tag=g1red-mut2-o-m1 start=2026-11-02 13:20:24 end=2026-11-02 13:20:27 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-o-m1.log
    [pyt] tag=g1red-mut2-o-m2 start=2026-11-02 13:20:27 end=2026-11-02 13:20:32 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fe82d828-54b9-4af1-9c1d-685173488382\scratchpad\S81-G1_red\mut_logs\g1red-mut2-o-m2.log

## 6. Restore check (step 8)
- Real worktree: HEAD 6c14ac954f601902d322547de04982033aca5925; `git status --porcelain --untracked-files=all` = exactly the three new files (??); `git diff --quiet` rc=0 and `git diff --quiet HEAD` rc=0; `git ls-files -m` empty. sha256 manifest of all 3454 tracked working-copy files after: S81-G1_red/tracked_manifest_after.txt (digest bde22cdd...). No tracked file was written (the RED files were copied in at 13:12 and their final bytes at 13:17, after every comm / pin / corpus base run).
- Scratch worktree S81-G1_red/wt (no node_modules / junction; created twice, the second time for the final-bytes prototype and mutation round 2) removed both times with `git worktree remove --force` (rc=0); `git worktree list` holds no S81-G1_red entry. The temporary recorder test lived only in the scratch worktree. No pytest of mine is alive (every pyt.py run returned).

## 7. Deviations from the spec (reported, not silently changed)
- Comm set = 592 files, not 'about 540': the spec's seed grep reproduces exactly 539 at 6c14ac95, but 7 of them are non-test helpers (never collected); the union rule's classes add 61 test modules (source readers of app/ or scripts/, CLAUDE.md readers incl. test_cohort_personalization_load / test_eval_kpi_baseline / test_scraping_mode, app.main importers, symbol references); minus the judgeme pin. A superset, recorded at base (sha 89037313...).
- P5 golden: 16 records (the full 2 x 4 x 2 cross product of the spec's own axes: provider present/absent x average present/absent/out-of-range/string x facts carrying/lacking), not 12.
- tests/fixtures/judgeme_c5/ holds 8 files (SOURCES.json + 7 .html: albayan_junk_body_1char, false_positive_webpixel, myperfumes_full_jsonld, no_judgeme_control, parfum_ae_shell_badge_only, shell_placeholder_zero_badge, swissarabian_thin_dom), not 'SOURCES.json and six .html': GREEN's deletion is 10 paths, not 9.
- scripts/seed_spec_spine.py:129-131: the judgeme mention spans two lines ('Mirrors' ends line 129; '``judgeme_service._iter_jsonld_nodes``; kept local ...' is line 130); the spec's replacement sentence covers both.
- CLAUDE.md anchors moved at 6c14ac95 (S81-08 block :522-530 inserted): sephora bullet :814-817, 'controls curl cracks free' :822, the Scrape.do narrow-keeper bullet :827-829 (EM DASH in the file, ASCII hyphen in the spec's quote); the S81-G1 block goes after :530.
- R15 strengthened: parametrized over a verified AND an unverified provider rating (rating_verified False). The orchestrator mutant O-M2 in its subtle form (overwrite unless verified) is killed only by the unverified param.
- R10 / R11 / R12 / R3 carry extra params inside the spec's stated contract: R10 query-counts, malformed-arity, malformed-type; R11 inside-grace (now = next_reread + 23 h), no-challenge-key, challenge-parked-past; R12 fetched-at-garbage, robots-not-dict, malformed-rules; R3 a .php path, a .test host (2.2 rule 2), a non-str input; the R3 denied rows are FIRST-PARTY (image host == page host) so only the deny check refuses (this is what kills D-M5 with ENABLE_DATA_GUARDS_V2 unset).
- R20 also pins the absence of tests/test_m6_c5_judgeme_html_reviews.py (R-G1-4 lists it) and scans text files only (skips __pycache__ and binaries, so a stale .pyc never counts).
- P9 strengthened: ON may add only {image_url, _jsonld_facts} over the OFF result and every OFF key keeps its value (kills D-M18 by itself).
- B1 config of P1-P6: besides the ALLOWING seam recorder, the rows wrap jsonld_widen.stamp_jsonld_facts and jsonld_widen.channel1_rating with counters and assert zero. D-M14 ('stamp not gated') leaves the P1 literal equal (the stamp re-reads each flag) and is killed ONLY by the counter (P1 + P6), as the spec's killer column says. This assumes GREEN calls the stamp / channel-1 through the module attribute (jsonld_widen.stamp_jsonld_facts(...), as spec 3.2(c) writes it); a from-import would make the counter vacuous, not red.
- allowed_image_url: the spec 2.2 header names (url, page_url) but (c) and 2.6 pass brand_domains as a third positional; R2 / R3 call it with three positional args (url, page_url, brand_domains).
- size_text: 2.2 says it uses price_service._jsonld_scalar_text while 3.1 says the leaf never imports price_service (a contradiction); the prototype re-implemented the Text branch in the leaf. R21 pins the Text and QuantitativeValue forms only through the candidate.
- The mutation runs used the FULL unit file per mutant (a superset of `pyt.py -k <killing rows>`), so the killed-by column lists every failing row.
- The literal P1 / P3 / P4 / P2 dicts were recorded at base by executing the code, not by reading it; ENABLE_JSONLD_FIRST (default ON) is why P1 carries capture_outcome 'ok'; the extract-path flags whose defaults the literals assume are deleted per row (EXTRACT_PATH_FLAGS).

## 8. Open questions for the gate
- R14 pins rating_source.retrieved_at as the _now seam formatted '%Y-%m-%dT%H:%M:%SZ' ('2026-10-29T12:00:00Z'; the fixed now has zero microseconds, so isoformat().replace('+00:00', 'Z') gives the same string). Acceptable?
- R14 / R15 assert 'rating_derived never set' as the KEY ABSENT (a GREEN that writes rating_derived=False goes red). Acceptable reading of 2.7 step 2?
- R11 / R12 leave challenge=None (a DB NULL) unpinned either way; the spec says 'absent or {}'. Pin it as allowed?
- R13 asserts the default seam answers None (jsonld_widen.ROBOTS_ENTRY_LOOKUP(host) is None): the R-G1-1 'no reader' contract made a row.
- R17 pins reviews.products[i].jsonld_rating only when the flag is ON AND the product dict carries a truthy jsonld_rating; the post-pass is assumed to run after the base list is built (OFF lists byte-identical, P5).
- The E-rows E3 / E4 / E5 (test_zyte_seed_variant, test_seed_zyte_guard) and E1 (the judgeme pin deletion) were not exercised by this RED (GREEN's change list); whether any OTHER existing pin reddens under the prototype was NOT measured here (the comm set at HEAD is GREEN's).

## 9. NOT MEASURED in this RED
- The HEAD comm set and the fourteen client fences (GREEN's / the rebase's; they need GREEN's bytes and an orchestrator junction).
- The corpus ON-vs-OFF information run (--flags-on ... --compare) and the JSON-LD image-host distribution over the 92 Gulf PDPs (R-G1-3: GREEN's information step).
- Existing pins against the prototype (which E-rows fire) - see open question 6.

## 10. For GREEN (carry)
- The corpus gate command of record (identical --flags both sides): `python scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_IMAGE_PIPELINE_V2,ENABLE_JSONLD_RATING --out <notes>/gate_<side>.json`; BASE OVERALL SHA256 9f9f9aeb185f7e811aa4292141d57a567e0aaaf7a1cc28f3b5ece0ac51ecaf33 (n=414, calls=1656, non_none=829); the RED prototype printed the same.
- The base record of the comm set: harness/base_records/6c14ac954f601902d322547de04982033aca5925/89037313e1996445e90b7147ea2ebcab9c41cb06a993f4ed33988d7d9877ed41.txt (reuse it when the HEAD set minus the two RED files and the golden equals comm_files.txt; GREEN's HEAD set adds tests/test_s81_d08_jsonld_widen.py and tests/test_s81_s23_bypass_retire.py, whose base state is this RED run).
- The RED files read the leaf through find_spec/getattr only; the P rows wrap stamp_jsonld_facts / channel1_rating by module attribute; the scs harness patches _get_specs/_get_price/_get_reviews/_get_verified_rating/search_web/get_product_image_url/tier2/tier3 exactly like the D03 file; the reviews-call recorder replaces extraction_service._llm_router and get_client.

## 11. git status --short of the real worktree (end)
    ?? tests/fixtures/s81_d08_rating_flag_off_golden.json
    ?? tests/test_s81_d08_jsonld_widen.py
    ?? tests/test_s81_s23_bypass_retire.py


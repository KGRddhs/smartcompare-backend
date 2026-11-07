# S81-G8 ADVERSARY REPORT - correctness lens (privacy / data checks folded in, R-G8-1)

Agent: Opus 5.5 (claude-opus-5-5), 2026-11-07 08:14-08:40 AST. Rendered through the shell (python, from a staging source file; the mutation table is spliced in by the script).
Verdict: SOUND (0 blocking, 0 major, 4 minor -> stated limits / documentation rulings, LC-4).

## 1. HEAD and bytes
- sc-s81-g8 HEAD = fe2ba6703d22e48842bf4af2d714d0716aa5f8bf (verified first; status clean; branch feature/s81-g8-followups; one commit over daf86d32).
- Scratch worktree <scratchpad>/S81-G8_adv_correctness (`git worktree add --detach ... fe2ba670`, no junction). The box has core.autocrlf=true (system gitconfig), so the checkout was CRLF; the 13 changed files were rewritten from their HEAD blobs so every probe ran on the exact committed bytes (each sha-equal to its blob).
- GC-1 frozen files: HEAD blobs AND the sc-s81-g8 working copy = 7dc7f8aa... / 957020e3... / 4fc4b399... / 497754da... (EQUAL first and last).
- GREEN table: the seven existing files in the sc-s81-g8 working copy hash exactly to the GREEN 'after' column (CRLF working copy; the repo blobs are LF, base and HEAD alike); store_labels.py bd9ae0ba... and merchant_labels.json afef66a9... equal disk, blob and table.
- numstat matches the report. The 17 deleted lines are the rewritten B1b signatures / docstrings / calls + the 4 CLAUDE.md in-place lines: each justified.

## 2. RED files re-run from the exact bytes
- [pyt] tag=g8adv-units-off start=2026-11-07 08:16:14 end=2026-11-07 08:16:20 elapsed=6s bound=600s status=OK rc=0 | 34 passed, 11 warnings | [hermeticity] sentinel checked 34 | [netguard] blocked 0
- [pyt] tag=g8adv-units-on (the three flags =true in the runner call only) start=2026-11-07 08:16:25 end=2026-11-07 08:16:31 elapsed=6s bound=600s status=OK rc=0 | 34 passed | [netguard] blocked 0

## 3. Mutants (sha-verified byte copies in the scratch worktree; restored and re-hashed after each; flags stripped; one pytest at a time; driver S81-G8_adv/mutants.py, logs S81-G8_adv/mut/)
23 of the 24 spec mutants re-applied by hand from the spec descriptions (11b-M4 not re-applied) + 14 own. Spec: 23 / 23 KILLED. Own: 8 KILLED, 6 SURVIVED (OWN-3/4/5/6/8/9; OWN-5 equivalent).
| id | result | killing rows |
|---|---|---|
| B1b-M1 | KILLED | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags, test_r4_string_ratings_only, test_r5_same_identity_keeps_needs_identification, test_r6_url_route_tags_follow_the_url_reading |
| B1b-M2 | KILLED | test_p2_text_camera_stream_tags_byte_equal |
| B1b-M3 | KILLED | test_r4_string_ratings_only |
| B1b-M4 | KILLED | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags, test_r5_same_identity_keeps_needs_identification, test_r6_url_route_tags_follow_the_url_reading, test_r7_compare_runs_row_follows_the_url_reading |
| B1b-M5 | KILLED | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags |
| B1b-M6 | KILLED | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags |
| B1b-M7 | KILLED | test_p2_text_camera_stream_tags_byte_equal, test_p3_assess_result_default_unchanged, test_r1_assess_result_url_mode_keyword, test_r7_compare_runs_row_follows_the_url_reading |
| B1b-M8 | KILLED | test_r7_compare_runs_row_follows_the_url_reading |
| 11b-M1 | KILLED | test_p1_flag_off_golden_full_config, test_p2_kb_off_bodies_unchanged, test_r4_builder_stamps_under_the_flag, test_r7_flag_read_first |
| 11b-M2 | KILLED | test_r2_helper_hosts_and_newest, test_r3_helper_nulls_and_zero, test_r4_builder_stamps_under_the_flag, test_r5_orchestrator_rest_and_stream, test_r6_partial_builder_carries_it |
| 11b-M3 | KILLED | test_r2_helper_hosts_and_newest, test_r3_helper_nulls_and_zero, test_r4_builder_stamps_under_the_flag, test_r5_orchestrator_rest_and_stream |
| 11b-M5 | KILLED | test_r2_helper_hosts_and_newest, test_r3_helper_nulls_and_zero, test_r4_builder_stamps_under_the_flag, test_r6_partial_builder_carries_it |
| 11b-M6 | KILLED | test_r5_orchestrator_rest_and_stream |
| 11b-M7 | KILLED | test_r6_partial_builder_carries_it |
| 11b-M8 | KILLED | test_p1_flag_off_golden_full_config, test_p2_kb_off_bodies_unchanged, test_r7_flag_read_first |
| 18b-M1 | KILLED | test_p1_flag_off_golden_full_config, test_r4_builder_pass_both_surfaces, test_r8_flag_read_first |
| 18b-M2 | KILLED | test_r3_label_for_lookup_and_lang, test_r7_fail_safe_table |
| 18b-M3 | KILLED | test_r3_label_for_lookup_and_lang, test_r4_builder_pass_both_surfaces, test_r5_orchestrator_kb_and_live, test_r6_partial_builder_lang_from_ctx |
| 18b-M4 | KILLED | test_r3_label_for_lookup_and_lang |
| 18b-M5 | KILLED | test_r4_builder_pass_both_surfaces, test_r5_orchestrator_kb_and_live, test_r6_partial_builder_lang_from_ctx, test_r7_fail_safe_table |
| 18b-M6 | KILLED | test_r4_builder_pass_both_surfaces |
| 18b-M7 | KILLED | test_r6_partial_builder_lang_from_ctx |
| 18b-M8 | KILLED | test_r7_fail_safe_table |
| OWN-1 | KILLED | test_r3_label_for_lookup_and_lang |
| OWN-2 | KILLED | test_r7_fail_safe_table |
| OWN-3 | SURVIVED |  |
| OWN-4 | SURVIVED |  |
| OWN-5 | SURVIVED |  |
| OWN-6 | SURVIVED |  |
| OWN-7 | KILLED | test_r3_helper_nulls_and_zero, test_r5_orchestrator_rest_and_stream |
| OWN-8 | SURVIVED |  |
| OWN-9 | SURVIVED |  |
| OWN-10 | KILLED | test_r5_orchestrator_kb_and_live |
| OWN-11 | KILLED | test_p2_text_camera_stream_tags_byte_equal |
| OWN-12 | KILLED | test_r4_builder_pass_both_surfaces, test_r5_orchestrator_kb_and_live, test_r6_partial_builder_lang_from_ctx, test_r7_fail_safe_table |
| OWN-13 | KILLED | test_r5_orchestrator_kb_and_live |
| OWN-14 | KILLED | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags, test_r4_string_ratings_only, test_r5_same_identity_keeps_needs_identification, test_r6_url_route_tags_follow_the_url_reading, test_r7_compare_runs_row_follows_the_url_reading |
Own mutants: OWN-1 url-host second lookup dropped; OWN-2 a WARNING on every call; OWN-3 REST `_partial_build_ctx` output_lang entry dropped; OWN-4 stream `_partial_build_ctx` entry dropped; OWN-5 REST entry unconditional (EQUIVALENT: ctx.get returns None either way, ctx never serialized); OWN-6 host count not case / space folded; OWN-7 aggregates over slot 0 only; OWN-8 the label-value URL guard dropped; OWN-9 exact `lang == "ar"`; OWN-10 / OWN-13 REST / stream site passes no output_lang; OWN-11 url_mode also for camera; OWN-12 products[i] not labelled; OWN-14 url_mode dropped from the strict reading.
Every kill is an AssertionError (11b-M1 / 11b-M8 / 18b-M1 also RuntimeError from the raising recorders).

## 4. Runtime truth per unit (probe_b1b.log; probe_18b_11b.py -> probe_18b_11b.log: 38 / 38 PASS)
B1b:
- The four real JSON-LD fixtures (bh: curl_bh_bheshop + curl_bh_godukkan; ae: ae_lulu + ae_samawa) in the RED envelopes: base reading partial_no_winner coverage 0 -> url_mode supported_result data_coverage 1, identity high; ratings-only 0 -> supported 1; same identity stays needs_identification; no evidence stays partial_no_winner; placeholder stays needs_identification. On all seven envelopes the url_mode status agrees with url_gate_reason. The CLAUDE.md claim (supported_result with data_coverage 1 instead of partial_no_winner) is TRUE.
- Default path byte-identical by construction: evidence_facts(b) is _facts(b, strict=True) and evidence_facts_literal is _facts(b, strict=False); assess_result now calls _facts(..., url_mode=False) directly (same function, same arguments); no test or app module monkeypatches evidence_facts. P2 green; OWN-11 / B1b-M2 prove P2 bites.
- sentry_service and compare_runs gain only the conditional kwarg for input_type "url"; the only "url" caller is url_routes.py:393 (text :886 / :1092, text_stream :1485, camera image_routes :783 unchanged). The compare_runs row under its flag: R7 green; B1b-M8 killed by R7 alone.
- Purity: no new import in result_gate; P6 green.
S81-11b:
- Distinct hosts case / whitespace folded ("A.com" / "a.com " = 1), unparseable as_of ignored, newest as_of chosen; miss -> all null; a card with zero offers -> store_count 0, price_checked_at null (R-G8-5); views None / short -> two all-null entries; compare_count null; the aggregates carry counts and a timestamp only (no retailer string, no user data).
- kb_serve.classify returns hit "miss" without a card and "full" / "partial" with one, so the null-vs-0 split follows exactly.
- The flag read is the first statement of the stamp (11b-M8 killed by P1 / P2 / R7). Three call sites: partial :3923, REST :4827, stream :5754 (11b-M6 / M7 killed). `_kb_views` lifetime: get_comparison_service() returns a NEW service per request and image_routes builds its own, so no cross-request view leak.
S81-18b:
- normalize_host on the retailer ("WWW.<HOST>:443" -> the row); the url-host second lookup for a name-shaped retailer; a non-http url ignored; a malformed url does not raise; retailer None + url -> the url row; " AR " -> ar, None -> en; no row -> the retailer string; nothing -> None.
- Both surfaces labelled; the price objects never mutated (deep snapshot equal); products[i] stays the same product dict carrying a NEW price dict (the D2 / L-S18b-5 reading re-read and confirmed: the rebind lands on the shared product dict under ENABLE_EXACT_PRICE_GATE OFF, exactly like the builder's own public_price_view rebind); the same product in both lists ok; price None skipped.
- Post-build consumers of product_data re-read: _kb_ingest_tail -> kb_ingest.build_job copies only _PRICE_KEYS (store_label never persisted); the stage-timings pop is product-level. No compare route has a response_model that could strip the key.
- Fail-safe table: missing file -> the fallback with ONE WARNING over three calls; an AR diacritic, a URL-shaped value, an unnormalised key -> {} with ONE WARNING per file state; a valid replacement reloads with no warning (stat-keyed cache); the warning carries the exception type only (no label, host or URL in any log line; the builder's `[STORE_LABEL] pass skipped: <Type>` likewise).
- Table: version 1, 33 keys, sorted, each key == normalize_host(key), AR == EN in all 33, pure ASCII + LF, no 'http' / '://' / '@' / 'www.' (no URL, no personal value: public store names). zip(strict=True) is safe on the pinned Python 3.12.9 / CI 3.12.
- SSE prices frame: the pass runs only inside build_comparison_response (three callers, all scs); earlier frames are serialized before the build and the new-dict rebind cannot reach them (P3 green).

## 5. OFF identity with the FULL configuration
- 11b P1 (the shared golden over every TRUTH_STATE x the four OFF spellings of BOTH new flags, raising recorders, ENABLE_KB_FIRST_SERVE ON with both cards present) and 18b P1 green at HEAD; 11b-M1 / M8 and 18b-M1 killed by them. The golden is the RED's recording (blob 497754da..., not re-recorded).
- The corpus gate was not re-run by the adversary (GREEN's single HEAD run: OVERALL 200474df... = base; GC-11 does not assign it here).

## 6. Comm set (union rule re-derived independently: S81-G8_adv/comm_adv.py, AST import closure over app/ scripts/ tests/ incl. relative and import_module imports, + CLAUDE.md / data/ / app-source-path / symbol / stem text reasons)
- The RED list sha256 ea0d2f1b... verified (byte-equal to specs/S81_G8_COMM_SET.txt); GREEN's 715 = 712 + the 3 RED files.
- Mine 693 vs the 715: 4 candidates outside the set, all non-members on inspection: test_abuse_detection.py, test_abuse_detection_internals.py, test_database_service.py (the 'app/services' hit is the docstring naming their own target; no source read); test_migration_044_apple_siwa_tokens.py (a function-level import of the member test_migration_043, used only for its migration-file fence helpers; no edited module reached). 27 of the 715 lie outside my rule (over-inclusion, harmless). No MISSING member: no MAJOR.
- The stored base record (harness/base_records/daf86d32.../ea0d2f1b....txt) = GREEN's head_failed.txt (24 ids, set-equal).
- Three chunks re-run at HEAD (flags stripped), every failure inside the 24 base ids:
  - [pyt] tag=g8adv-comm-c08 start=2026-11-07 08:31:17 end=2026-11-07 08:32:33 elapsed=76s bound=1200s status=OK rc=0 | 1977 passed
  - [pyt] tag=g8adv-comm-c14 start=2026-11-07 08:32:40 end=2026-11-07 08:33:16 elapsed=37s bound=1200s status=FAIL rc=1 | 4 failed, 738 passed (test_page_scraping x2, test_personalization_bundle_c x2: base ids)
  - [pyt] tag=g8adv-comm-c20 start=2026-11-07 08:34:43 end=2026-11-07 08:36:02 elapsed=79s bound=1200s status=FAIL rc=1 | 11 failed, 2690 passed (d22c p1 x5, s10 r06, s16 r27 x5: base ids)
  (= GREEN's c08 / c14 / c20 figures exactly.)
- CI-order set (the RED's 23 files): [pyt] tag=g8adv-ciorder start=2026-11-07 08:36:38 end=2026-11-07 08:38:14 elapsed=96s bound=1200s status=FAIL rc=1 | 1 failed, 1716 passed (s10 r06 only, environmental) = GREEN's figure. (A first attempt with tag g8adv-ciorder at 08:36:22 collected nothing, rc=4, a driver parsing bug of mine; re-run as above.)
- Source-scanning pins + the six CLAUDE.md readers + the migration readers (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_s81_kb_schema, test_secret_scan_static, test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire, test_migration_043_delete_user_cascade, test_hermeticity_pins): [pyt] tag=g8adv-pins start=2026-11-07 08:26:12 end=2026-11-07 08:27:40 elapsed=87s bound=1200s status=OK rc=0 | 1433 passed.
- One pytest at a time: the S81-24 lane's pytest ran between my sets; my gated runner waited for no '-m pytest' process on the box before each set (waits 95 s / 75 s logged); no pytest I did not start was touched.
- Hook test files NOT run (no .githooks change). Client fences NOT run (no junction in the adversary worktree, GC-11); GREEN's 13 / 14 + b3a stands.

## 7. Hygiene, CLAUDE.md, PR body
- ruff --select E9,F63,F7,F82 on the 7 app files + 3 RED files: All checks passed; default ruff on store_labels / kb_serve / result_gate / compare_runs: All checks passed; py_compile clean.
- Added lines: no non-ASCII except two pre-existing CLAUDE.md lines (:92, :341) whose pre-existing en-dashes are byte-preserved (word diff: insertions only); no 64-hex literal outside the tests; no keyword-named constant; no personal value.
- CLAUDE.md (word diff vs daf86d32): :92 sentence appended before 'A migration missing from this record' as GC-7 words it; :341 the G8 sentence after the S81-22 sentence; :475 the B1 clause now 'its telemetry reads the URL evidence (S81-G8 B1b)'; :585 'L19 B1's URL telemetry reads the URL evidence since S81-G8 B1b' and the Canary gains 'and B1's URL message'; the G8 block at :610-614 after the S81-22 block with one blank line before its heading and before '## Tests'. No new line carries scoring_method + enum. Every row claim probed in section 4 is true.
- PR body: 10,967 B (<= 25,600), ASCII except the attribution line; base / HEAD / corpus SHA pair correct; the 33 [NATIVE READ] rows equal the table rows in order (host, ar, en); L-B1b-1..4 / L-S11b-1..4 / L-S18b-1..5 + the R-G8-3 note present; the commit trailer names Opus 5.5.

## 8. Findings
Blocking: none. Major: none.
Minor (LC-4: stated limits / documentation rulings, no pin-fix round):
- MIN-1 (CLAUDE.md :92; GREEN Q1 confirmed): the line now says both '045 ... and 047 ... WRITTEN, NOT APPLIED (the owner applies 045 ...)' and '045 ... applied 2026-11-06', and its closing sentence still says the record does not cover 'anything newer than 044' while the appended sentence records 045 / 050 / 052. A reader of the house record gets two contradicting facts on one line. Ruling owed: the final round rewrites the older clause and that parenthesis in place (names only), or the PR body states it as a limit.
- MIN-2 (test gap, 18b): the two `_partial_build_ctx` literal entries (scs :4354, :5230) are unpinned: OWN-3 / OWN-4 SURVIVE because R6 assigns svc._partial_build_ctx directly. The code is correct by reading (both literals carry the conditional entry; the partial builder reads ctx.get("output_lang")); a later edit dropping an entry would silently give a hard-cap partial on an ar request EN labels. Stated limit.
- MIN-3 (test gap, 11b): the host case / whitespace fold in _slot_aggregate is unpinned (OWN-6 SURVIVES); probed correct at runtime. Stated limit.
- MIN-4 (test gap, 18b): the label-value URL guard of _valid_value (OWN-8) and the lang strip / lower in label_for (OWN-9) are unpinned; probed correct at runtime ('https://x' value -> table unavailable with one WARNING; ' AR ' -> ar). normalize_output_lang already yields 'ar' / 'en' / None upstream, so OWN-9 is near-equivalent in production. Stated limit.

## 9. Prove-nothing rows
- units-on (GREEN's and mine): the RED rows set their flags through monkeypatch, so exporting the three flags re-proves the same 34 outcomes (it proves only that the env does not break the rows).
- 11b P3 (classify shapes untouched) and 18b P2 (the classify price dict key set): green at base and HEAD by construction (no hunk touches classify / _price_dict); they guard R-G8-9 only.
- B1b P6 (purity restated) and P4 (the URL gate reading unchanged): source / unchanged-code pins; no hunk could redden P4.
- OWN-5 is an equivalent mutant (ctx internal, never serialized; ctx.get returns None either way).
- The corpus gate with every flag OFF cannot see the new keys by construction (both stamps sit behind a first-statement flag read); it proves only that nothing else moved.

## 10. Cleanup
- The scratch worktree is removed with `git worktree remove --force` after the last re-hash; no edit in sc-s81-g8; no flag set in any .env or the OS environment; no .env read (the B1b probe set a dummy OPENAI_API_KEY placeholder for one process so app.main imports; no real value); no package manager; no network beyond netguard-blocked test attempts.

- Final: sc-s81-g8 HEAD fe2ba670 unchanged, status clean, the four frozen files re-hashed EQUAL; the scratch worktree had no drift from its blobs after the mutants and was removed (git worktree list no longer shows it).

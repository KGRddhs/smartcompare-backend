# S81-10 FRAGRANCE-ONLY-GATE fix round 1: RE-VERIFIER report (correctness lens; Opus 5.5; written through the shell)

- unit: S81-10 FRAGRANCE-ONLY-GATE (lane A backend, FOCUS; ENABLE_FRAGRANCE_ONLY_GATE default OFF, read per call); fix round 1 under specs/RULINGS_FIX1_S81_10.md (LC-2: the round touches app/, hence this re-verifier, scoped to the fix diff)
- unit worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10, branch feature/s81-s10-fragrance-only-gate: HEAD verified 0e4b69e8065654293db548f0c114ff09714cf4e6 at the start (15:22) and at the end (16:40); `git status --short` EMPTY both times; never written (no file, no lock, no pytest run there)
- my scratch worktree: <scratchpad>/S81-10_fix1_adv (`git -c core.longpaths=true worktree add --detach ... 0e4b69e8`); the five LF working copies of the unit worktree (category_gate.py, fragrance_lexicon.json, the two RED files, the gate rows) copied in byte for byte, so all 3,459 tracked files were sha256-equal to the unit worktree before the first run and again after the last mutant restore (align.py, 0 differing); removed at the end (no node_modules inside; `git -c core.longpaths=true worktree remove --force` rc 0; absent from `git worktree list`; the folder is gone)
- notes / logs / scripts: <scratchpad>/S81-10_fix1/reverify/ (notes.md, align.py, static_checks.py, rv_mut.py, rv_reparse.py, rv_comm.py, probe_plugin/rv_clock_shift.py, test_zz_rv_probe.py, logs/, rv_mut_results_batch{1,2}.json, comm_s10rvc.json, comm_s10rvx.json)
- VERDICT: SOUND (0 blocking, 0 major, 6 minors: documentation / coverage, none production-visible)

## 1. RED files (re-hashed: the unit worktree bytes and the HEAD blobs)
- tests/test_s81_s10_fragrance_gate.py: frozen d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac at 0523a06f -> fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e at HEAD (working copy == blob; git blob 3857c91e02cfd5cac120e20f09b774ee49d3e819); 111,629 B, LF, 0 bytes > 127. `git diff 0523a06f HEAD` of the file: +30 / -0, every added line belongs to EK1 (the comment, GOLDEN_RECORD_INSTANT, _RecordInstantDatetime, _at_record_instant, and the one monkeypatch line at the top of _run_golden). Default-config ruff on the file reports the same 3 findings (B904 x2, SIM102) as on the frozen d988882a bytes (none in the amendment).
- tests/fixtures/s81_s10_flag_off_golden.json: 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a at 0523a06f and at HEAD (byte-identical; blob 18bd5ff2e1005f84332ee315789ac079ff8bad79). A scan of the 12 scenarios finds exactly ONE clock-derived span ("updated_at":"3d ago" in G10) and no ISO date or epoch value anywhere.

## 2. Diff scope (0523a06f..0e4b69e8, one commit, trailer Co-Authored-By: Claude Opus 5.5)
- 5 files: CLAUDE.md (1 line changed; CRLF kept: 996 CRLF / 0 bare LF; bytes > 127 3,937 before and after), app/services/category_gate.py (+15: apply_form_override_stubs; LF, 0 bytes > 127), app/services/structured_comparison_service.py (+4: one comment + one call on each path; CRLF kept: 9,895 / 0, no whole-file diff), the RED file (+30, EK1), tests/test_s81_s10_gate_rows.py (+352 / -6: 18 new nodes; F1-7 removes the two static asserts and their comment; the import lines change).
- added lines 402, bytes > 127 in added lines 0; sweep of the added lines for @gmail / +973 / 8-digit runs / sk- / AKIA / xox / JWT / credentialed URL / PEM / e-mail shapes: 0 hits.
- branch vs base 6c14ac95: 14 files; no migration, no lock, no client file; tests/ = the RED pair + the gate rows + exactly the two sanctioned E-row files (043 census, s05 p01).
- ruff `--select E9,F63,F7,F82` + py_compile on the 4 touched Python files: clean; default ruff on category_gate.py and the gate rows: clean.

## 3. F1-2 re-read against B1's result gate (HEAD code)
- post_resolve_refusal (category_gate.py:669-712): on the explicit / vision path a product whose name (search_query or name) has scan().fragrance_type counts as 'fragrances' and sets form_override; any positive non-fragrance per-product category refuses FIRST. Hence in every PROCEEDING override pair each other product's canonical stub is 'fragrances' or 'other'.
- apply_form_override_stubs (:726-738): returns unless verdict.form_override; rewrites product['category'] = 'fragrances' for exactly the products that pass the SAME expression as post_resolve_refusal (search_query or name, a non-empty str, scan([name]).fragrance_type). form_override is never True on the q= path, so the q= path is untouched (R-S10-5).
- call sites (structured_comparison_service.py sync :4380, stream :5066): inside `if fragrance_gate is not None:`, after the refused-return and after the GC-1 rewrite; then the B1 capture `product_categories = [canonicalize_category(p.get('category')) ...]` (sync :4388, stream :5069) and the A3 write-back that sets every product to category_used. So the rewrite reaches nothing but B1's capture: no fetch, cache key, schema or scoring input changes. Without a decision (flag OFF, /text/quick, the URL path, the warmer) the block never runs (mutant F12i, the call moved out of the block, is killed by P05 x12, gc1_without x2 and F1-2 (d)).
- the B1 flow: the captured list object is the one passed to build_comparison_response (sync :4704, stream :5596) and, through the ctx, to the partial builder (:3868); scs never reassigns it (7 references, grep). response_builder stamps metadata.product_categories and runs result_gate.assess_result -> identity_coherence (result_gate.py:193: False only for two canonical, non-'other', DIFFERENT categories). After F1-2 every proceeding override pair is [fragrances, fragrances] or [fragrances, other]: coherent, no 'category_conflict'. sentry_service and telemetry_tags re-assess from the stamped categories (the same answer).
- measured on a BUILT body (my probe P-F12-partial: the real build_comparison_response + the B1 stamp on the partial path, fed by the ctx the gate block captured, ENABLE_RESULT_STATUS_METADATA on): 'Kerastase Genesis Hair Mist' / 'Dior Sauvage EDT' on the explicit path AND on the vision path (vision_products Kerastase + Genesis Hair Mist / Dior + Sauvage EDT): ctx category_used fragrances, ctx product_categories [fragrances, fragrances]; the built body's metadata.product_categories [fragrances, fragrances], metadata.result_status supported_result, assess_result reasons [] (coherent True). Control, the same pair with the flag ON and NO decision: ctx and stamp [haircare, fragrances], reasons [category_conflict], result_status unsupported_category, i.e. exactly the m5 defect F1-2 removes (the probe discriminates).
- the F1-2 STOP condition: R31 asserts the fetch count and no EVAL only; no RED row reads product_categories; the GC-1 rows assert the fetch categories and the ctx category_used / switched only. No frozen row pins the old stub, so the code change was the right form.
- DV1 (the rewrite also when category_used was already fragrances): consistent with the ruling's purpose; no other effect (the write-back follows immediately).

## 4. EK1 (F1-1) verification
- mechanism: _run_golden monkeypatches home_routes._format_updated_at with a wrapper that swaps the stdlib attribute datetime.datetime for a subclass whose now() returns 2026-11-02T08:30:00Z for the duration of the REAL formatter call, restored in a finally. The formatter's function-local `from datetime import datetime, timezone` (home_routes.py:514) reads that attribute at call time and the route calls the module global (home_routes.py:657), so the patch reaches it. Frozen elapsed = 3 d 22.5 h -> "3d ago" = the recorded byte. Nothing else in the golden reads the clock (section 1 scan).
- my own, BROADER clock probe (probe_plugin/rv_clock_shift.py, outside the repo; shifts the stdlib datetime.datetime and datetime.date AND the 26 app.* / tests.* module-level bindings of the two classes, kb_service and llm_pricing excluded for their isinstance checks; the shifted function-local now is written to a marker file): P01 x5 + R54 x5 + R49 + P03 + R50 x6 + R51 = 19 / 19 green at +1 d, +10 d, +400 d and -2 d (marker: function_local_now 2026-11-03 / 2026-11-12 / 2027-12-07 / 2026-10-31).
- non-vacuity: EK1a (the monkeypatch line dropped) -> the ten nodes red at the real clock with AssertionError ("3d ago" vs "4d ago"); EK1a under my +10 d probe -> the ten red with "Older" (10 mentions; the 11th failure there, R46, is my probe's artifact: it patches the RED module's `date` name, so isinstance(real_date, ShiftedDate) is False); EK1b (the frozen instant +1 d) -> the ten red. The freeze is what holds the golden.
- R49 / P03 ("wherever R49 / P03 build the same rows"): neither asserts formatter output (R49 compares comparison_id, empty_state and the home I/O; P03 compares the OFF and ON History bodies inside one test; History carries no relative label); green at all four shifted clocks. Leaving them unfrozen is correct.

## 5. Runs (every pytest through pyt.py, one process at a time, all in MY scratch worktree; the full [pyt] list is Appendix A)
- RED + gate rows, flag unset: 171 passed (140 + 31); ambient ENABLE_FRAGRANCE_ONLY_GATE=true: 171 passed; collect: 140 + 31 nodes (18 new: F1-2 x2, F1-4 x2, F1-5, F1-6 x3, QB02 x5, QB03 x3, QB04 x2). [hermeticity] 171, [netguard] 0 both.
- clock-shift runs: 4 x 19 passed (section 4).
- CI-order set (the GREEN's 30 files, flag unset): 2461 passed, 4 deselected (= 2443 + 18), [hermeticity] 2461, [netguard] blocked 89 attempts from 34 nodes (the neutralized.supabase.invalid sentinel and the blocked api.openai.com resolve: the same 89 / 34 as the fix agent's run). A first attempt (s10rv-ciorder, rc=4 in 0.5 s) was a usage error of MINE (CR characters in my file list), not a result.
- the ruled comm SUBSET + the complement (section 7); tests/test_secret_scan_static.py ALONE: 31 passed; the hook files ALONE (section 8); the probes (section 6).

## 6. Probes of documented behaviour (tests/test_zz_rv_probe.py, copied into the scratch worktree for one run and deleted; production lexicon where the documented example needs it)
- 10 / 10 passed (`[pyt] tag=s10rv-probe ... status=OK`); records in Appendix D.
- P-F12-partial (explicit, vision) + P-F12-ctl: section 3.
- P-m4 (L4, F1-8 m4): 'Dior Sauvage EDT' / 'Apple iPhone 15 Pro', explicit, no chip, production lexicon: decision proceed (evidence True); the compare reached the fetch with both products as fragrances, ctx category_used fragrances, B1 [fragrances, other] (coherent), 0 A2b, 0 EVAL. L4 TRUE.
- P-m6 (L11, F1-8 m6): 'Clean Reserve Skin' / 'Clean Reserve Warm Cotton', explicit, production lexicon: decision proceed (no $0 refusal), then post-resolve CATEGORY_NOT_LIVE category skincare, 1 EVAL, 0 fetch, 0 A2b, both with chip None and chip fragrances. L11 TRUE.
- P-m10 / P-m11 (F1-8 m10 / m11), production lexicon: "apple watch vs galaxy watch" -> refuse, category fashion; "krim nivea vs krim dove" (Arabic krim) -> proceed; "12 saa vs 8 saa" (Arabic saa) -> proceed; "krim nivea vs lushan dove" -> refuse skincare. TRUE.
- P-L17 (load_lexicon() calls = os.stat calls per gated request): q= path 1 (the decision only); explicit / vision without an override 3 (the decision + one scan per product name in post_resolve_refusal); with the form override 5 (F1-2's apply re-scans both names). L17's "one os.stat per gated request" holds on q= only (rv-m2).
- informational (not a finding of this round): tests/test_s80_b1.py with ENABLE_FRAGRANCE_ONLY_GATE=true AMBIENT: 7 failed / 192 passed at HEAD and the SAME 7 with the fix-round app hunk reverted to the GREEN bytes (rv_green_app.py, byte copies, restored sha-equal): B1's electronics pairs are refused by rule 1 at $0, its smart-pick rows are not fragrance rows, and two B1 rows call a route with a fake request that has no .state (the gate block reads request.state only after the flag, so flag OFF is untouched). The flag's design, not F1-2; the B1 file is green with the flag OFF (comm subset).

## 7. Comm set (LC-6; the cached base record 336233f08c08d9faf8c0b8a45c3e5a0902f5c8e96e57fe01f2667cde7870cba1.txt at 6c14ac95, whose name is the sha256 of specs/S81_10_COMM_SET.txt and whose .files list equals it)
- the ruled SUBSET, re-derived independently (the 425 files whose text at the HEAD bytes contains structured_comparison_service): 192 files = the fix agent's comm_subset.txt exactly; 8 chunks (bound 1200): HEAD failures = tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest + ::TestFetchPagePriceOpenGraph::test_og_meta_extraction = the base record's failures for these files; branch-only-new (comm -13) EMPTY; base-only none. Chunk counts equal the fix agent's except s10rvc-04 (820 passed / 6 deselected vs 818 / 8): my driver does NOT deselect the four NETWORK_FLAKY nodes the base record and the fix driver deselect; the two in this subset (tests/test_price_cache_bust_probe.py::TestPriceReadBypass x2) ran and PASSED.
- EXTRA, beyond the ruled subset (the app-walker / glob source-scanning pins need not name scs): the 233-file complement in 10 chunks: HEAD failures = tests/test_auth_interceptor.py x2 + tests/test_prompt_truth.py x2 (ERROR, the cold-tiktoken pair) = the base record's failures for these files; branch-only-new EMPTY; base-only none. The other two NETWORK_FLAKY nodes' files (tests/test_algolia_service.py in s10rvx-00, tests/test_rate_limiting_complete.py in s10rvx-05) ran without a --deselect: no failure from them.
- so the FULL 425-file set at 0e4b69e8 vs the base record: branch-only-new EMPTY, the six GC-7 failures identical on both sides.

## 8. The pre-commit hook test files ALONE (TIMEOUT rule; 4 files at HEAD: tests/test_precommit_hook.py, _phase_b.py, _phase_b_round2.py, _round2.py; 327 nodes, 160 'dash')
- `-k "not dash"`: `[pyt] tag=s10rv-hook-notdash start=2026-11-02 16:03:49 end=2026-11-02 16:19:08 elapsed=919s bound=1800s status=OK rc=0`: 167 passed, 160 deselected; [hermeticity] 167; [netguard] blocked 0.
- `-k dash`: `[pyt] tag=s10rv-hook-dash start=2026-11-02 16:20:56 end=2026-11-02 16:39:50 elapsed=1134s bound=1800s status=OK rc=0`: 157 passed, 3 skipped (environment skips of the hook files themselves, e.g. "gitleaks not on PATH"), 167 deselected.
- identical counts to the S81-09 rebase round's hook runs on this box today (s09rb-hook-notdash 167 passed / 160 deselected; s09rb-hook-dash 157 passed / 3 skipped / 167 deselected). No TIMEOUT, so no re-run was needed. (The round changes no .githooks byte; the run is the task's explicit instruction.)

## 9. CLAUDE.md row (line 532, the S81-10 block 531-533 after the S81-08 block, before `## Tests` at 535, no new heading; the Feature Flags pointer on line 341) and the PR body (<scratchpad>/S81-10_green/PR_BODY.md, 25,290 B <= 25,600, sha256 745aa91deff14bf205f805ac5d6d3ffdfbe5e16043cb1cf2e276a886dc0297d3 = PR_BODY_after_fix1.md; 494 bytes > 127 = the [NATIVE READ] Arabic column + the attribution line; LF) checked sentence by sentence against the bytes
- header: HEAD 0e4b69e8 = GREEN 0523a06f + fix round 1 TRUE; base 6c14ac95 TRUE, but "(origin/main)" is stale since 13:07 (origin/main = eaccd550; the rebase round rewrites the header: rv-m6); "no migration, no lock change, no client file, no route docstring edit, no new external host, no personal value" TRUE (section 2).
- What the flag does 1 (rule 1 before the preferences read, the budget read and the consume; house / note defers; the marked AR terms) TRUE (category_gate.evaluate / text_gate; the routes call text_gate first).
- 2 (ONE MGET of acct always + dev when bound; 429 scope / retry_after_seconds + Retry-After / resets_at; never billed; exemptions read only when spent, never the rules) TRUE (budget_keys, _read_counts, budget_state_async, budget_exempt_async).
- 3 (post-resolve after _resolve_pair_category, before the profile task, the write-back and any fetch, only with a decision; per product, chip-free; refund by the existing arm; ONE EVAL, EXPIREAT next reset + 1 h; 'other' proceeds uncounted; q= never calls A2b; the GC-1 rewrite; F1-2 so B1 agrees and no category_conflict) TRUE (section 3 + the probe); "reuses the resolver's A2b when no chip was sent ... and makes ONE A2b call otherwise" is imprecise for a chip 'other', which the code and the F1-5 row treat as no chip (rv-m4).
- 4 (camera: the budget before the consume in any metering state; the rules after the paid vision call; rule-1 pair / single product refunded and counted; HTTP 200 action:error, never comparison_failed) TRUE (image_routes.py:330-339, :500-506, :528-534, :566-569; R36-R40 + the QB rows).
- 5 (admin marker only in require_paid_route_user's admin branch; all four routes skip; pinned POST / GET / stream / camera; only while ENABLE_COMPARE_AUTH_REQUIRED is ON, the auth-OFF early return precedes the branch) TRUE (text_routes.py:315-341; P06, test_qb03_admin_key_bypass_get_and_stream[get|stream], test_gc6_admin_key_camera_bypasses_the_gate, test_qb03_admin_key_with_auth_flag_off_is_gated; A02 / A03 killed).
- 6 (surfaces) and 7 (error_handler) TRUE (R49-R51, P03, R41 / R42 / P07 green).
- Flag OFF paragraph incl. the EK1 sentence TRUE (sections 1 and 4).
- Files table: TRUE row by row (category_gate.py stdlib-only at module level: lines 41-52 import only the stdlib; the lexicon has 43 Arabic terms and 3 marks; scs carries the kwarg on the three entries :4019 / :4178 / :4814; the RED pair line "the golden byte-identical; the RED file changed ONLY by EK1 (+30 lines)"; 31 gate-row nodes; the CLAUDE.md placement).
- Requirement map and E-rows table: TRUE (the E-row files are the only existing test files the branch changes; both files green in the CI-order set).
- Gates, GREEN line: GREEN's own record (not re-run here except as stated). Fix-round lines: every quoted tag exists in the pyt ledger with the quoted status (s10fix1-red-{off,on}-d{0,10,400} OK, -final OK, gaterows-final / -on / -d400 OK, ciorder OK 2461, s10f1c-00..07, secretscan OK) and my re-runs reproduce the counts (171, 2461, the subset's 2 base failures, 31). "not run: the fourteen client fences": the fourteen fences read docs/brand, scripts/render_myez_icons.py, app/services/extraction_service.py, referral_service.py, robots_eval.py, sitemap_discovery_service.py, docs/privacy-data-inventory.md, landing/ and SmartCompareApp sources; none reads CLAUDE.md, category_gate.py or structured_comparison_service.py (grep of the fence files), so the round cannot move a fence (not run by me either: no node_modules junction in a scratch worktree).
- Fix round 1 section: EK1 (mechanism, +30 / -0, the three shas, the before / after proof, "R49 / P03 assert no recorded formatter output") TRUE (section 4); F1-2 TRUE (section 3); F1-7 TRUE; Rows TRUE (18 new nodes; "F1-2 red at 0523a06f on an AssertionError": my F12a, equivalent to the 0523a06f code, is red on an AssertionError); Mutants "15 / 15 KILLED" TRUE (my 23-mutant table includes all 15 behaviours); Re-verifier line PENDING -> this report.
- Stated limits: L3 (WITH a chip GC-2 / WITHOUT a chip D3: refused AND counted, one EVAL, one refund, one A2b; ten lock the subject out) TRUE (post_resolve_refusal branches; test_f1_4_* green; the camera never sends a chip: image_routes has no selected_category at all) with the 'other' chip caveat of rv-m4; L4 (m4) TRUE per probe P-m4; L5 incl. the GR-9 a clause TRUE (R49's last part); L11 incl. 'Clean Reserve Skin' TRUE per probe P-m6; L17 "one os.stat per gated request" NOT exact (rv-m2, probe P-L17); F1-8 m7 TRUE (parser_path: the parse category decides, no override); m10 / m11 TRUE per probe P-m10-m11; F1-11 / F1-12 TRUE (QB04 rows) but "the budget 429" is, on the camera, an HTTP 200 action:error body (rv-m5); F1-14 TRUE and recorded in PLAN_STATUS_S81_2026-10-24.md line 63; C27 incl. the F1-12 m9 clause TRUE; the remaining limits (L1, L2, L6-L10, L12-L16, L18, the multi-key EVAL, the seams, M26) describe code the round did not touch and match it.
- Flip preconditions, Canary (+ the F1-13 pair and the F1-14 read), Owner steps: TRUE as rulings text. [NATIVE READ] table: programmatically equal to the lexicon's 43 Arabic terms, groups and the 3 needs_second_token marks, in order. GREEN deviations line: TRUE (GR-2 / GR-3 / GR-5 / GR-6).
- CLAUDE.md row (7,580 characters, 0 non-ASCII): every clause above has its twin in the row and holds the same way (the knob parsing "unset / garbage / inf / nan / below 1 -> 10" = refusal_daily_budget(); "re-read when the file's mtime or size changes" = load_lexicon(); "(as in production since 2026-10-03)" = the s81-common ledger fact for ENABLE_COMPARE_AUTH_REQUIRED; Rollback "the fragrance trending key idles and expires in 1 h" = the 3600 s set in R50). The same two wording imprecisions apply to the row (rv-m4: "the resolver's own A2b when no chip was sent"; rv-m5: "the budget 429 is never billed ..." in the camera clause).

## 10. The previous round's adversary findings: closure (every MAJOR: none existed; every MINOR)
| finding | ruling | state at 0e4b69e8 | evidence |
|---|---|---|---|
| correctness B1 / quota B1-qb (wall-clock golden) | F1-1 EK1 | CLOSED | section 4: green at the real clock and at +1 / +10 / +400 / -2 d; EK1a / EK1b red |
| c-m1 / q-m1 (GET / stream admin bypass unpinned) | F1-3 / F1-11 | CLOSED | QB03 rows; A02 / A03 KILLED |
| c-m2 (D3 unpinned; L3 wording) | F1-4 | CLOSED | test_f1_4_d3_*, test_f1_4_qb06_*; A11 KILLED; L3 + the row reworded |
| c-m3 (chip 'other') | F1-5 | CLOSED | test_f1_5_*; A12 KILLED (wording nit rv-m4) |
| c-m4 (blind product beside a fragrance) | F1-8 | RECORDED | L4 + the row; probe P-m4 |
| c-m5 (GC-1 x B1) | F1-2 | CLOSED | code + test_f1_2_* (sync / stream); 9 F1-2 mutants, 8 KILLED + F12f (rv-m3); built-body probe |
| c-m6 (stub collision) | F1-8 | RECORDED | L11 + the row; probe P-m6 |
| c-m7 (q= hair mist) | F1-8 | RECORDED | F1-8 bullet + the row |
| c-m8 (A14 / A17 / A22 / A29) | F1-6 / F1-11 | CLOSED | f1_6 rows; A14, A14r, A17, A29, A29b KILLED; A22 = QM09 KILLED by QB04 |
| c-m9 (static asserts) | F1-7 | CLOSED | the two asserts gone; the row keeps the fetch categories and the ctx |
| c-m10 (watch label) | F1-8 | RECORDED | F1-8 bullet + the row; probe P-m10 |
| c-m11 (same marked AR term twice) | F1-8 | RECORDED | F1-8 bullet + the row; probe P-m11 |
| q-m2 (route-level double count) | F1-10 | CLOSED | QB02 rows; QM12 and my text twin QM12t KILLED |
| q-m3 (anon refunds) | F1-11 | CLOSED (QM09) / RECORDED (QM10, QM15 unreachable) | QB04 metering_on row; F1-11 bullet + the row |
| q-m4 (bypass only under auth ON) | F1-12 | CLOSED | item 5 + the row; test_qb03_admin_key_with_auth_flag_off_is_gated |
| q-m5 (anon debit with metering OFF) | F1-12 | RECORDED | F1-11 / F1-12 bullet + the row; QB04 metering_off row (wording nit rv-m5) |
| q-m6 (D3 budget consequence) | F1-13 | RECORDED | L3 + the row + the canary pair; QB06 ported |
| q-m7 (stream refusal -> REST retry) | F1-14 | RECORDED | F1-14 bullet, flip preconditions, the row, PLAN_STATUS line 63 |
| q-m8 (QM22 equivalent) | F1-15 | RECORDED | equivalent at 6c14ac95; re-checked at the seam collapse (RB10-6) |
| q-m9 (billing-adjacent files) | - | informational | no action ruled |
| GR-9 a (smart pick with no fragrance row among five) | F1-8 | RECORDED | L5 + the row |

## 11. BLOCKING
none.

## 12. MAJOR
none.

## 13. MINOR (LC-4: stated limits by default; each is documentation or coverage, none changes a response byte in production)
- rv-m1 (stale sha in a test docstring) tests/test_s81_s10_gate_rows.py lines 2-3 still say the frozen RED file is "sha256 d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac" and "keep their bytes"; since the sanctioned EK1 it is fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e. One docstring line in a GREEN-owned file (the rebase round can carry it).
- rv-m2 (L17 understated) "one os.stat per gated request": load_lexicon() stats once per CALL and scan() calls it once per invocation; measured (P-L17) 1 on the q= path, 3 on the explicit / vision path (GREEN: the decision + one scan per name), 5 when the form override fires (F1-2's apply re-scans both names). Negligible cost (a stat each); wording only.
- rv-m3 (coverage, my extra mutant F12f) widening apply_form_override_stubs' per-product test from scan().fragrance_type to scan().evidence SURVIVES the RED + gate rows: a house-only partner (for example 'Dior Homme' beside 'Kerastase Genesis Hair Mist') would be stamped 'fragrances' instead of keeping 'other'. Equivalent for result_gate (both [fragrances, fragrances] and [fragrances, other] are coherent; status, reasons and identity_confidence unchanged); only metadata.product_categories' label differs, under two dark flags. A killing row: F12_ONE's partner replaced by a house-only name, expecting [fragrances, other].
- rv-m4 (wording) PR body item 3, L12 and the CLAUDE.md row say the resolver's A2b is reused "when no chip was sent" and L3 says "WITH a client chip": the code (and the F1-5 row) treat a chip 'other' exactly as no chip, so it reads "no chip or the chip 'other'" / "a chip other than 'other'".
- rv-m5 (wording) the F1-11 / F1-12 limit and its CLAUDE.md twin say "the budget 429 is never billed for signed-in callers, for anonymous ones only with metering ON" in the camera context; the camera's budget refusal is an HTTP 200 action:"error" body (category_gate.camera_budget_body), not a 429.
- rv-m6 (stale header) the PR body header "base 6c14ac95 (origin/main)": origin/main is eaccd550 since 13:07 (s81-common MOVING MAIN); RULINGS_REBASE_S81_10 rewrites the header in the rebase round.

## 14. Questions for the gate
- Q1: carry rv-m1 (one docstring line) and rv-m3 (one row) into the rebase round's gate rows, or state them (LC-4)?
- Q2: confirm DV1 (the stub rewrite also when category_used was already fragrances): this lens finds it correct and effect-free beyond B1's capture.

## 15. NOT MEASURED
- the fourteen client fences and the full jest suite (no node_modules junction in a scratch worktree; static: no fence reads a file this round changed; the rebase round runs them, LC-7).
- a DELIVERED full compare through Phase 2 (the probe uses the real builder on the partial path; the full path passes the same list object, by reading).
- a live Upstash MGET / multi-key EVAL (no Lua runtime; unchanged by the round).
- the S81-09 composition (the rebase round, RB10-6 / RB10-7).

## 16. End state
- unit worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10 at 16:40: HEAD 0e4b69e8065654293db548f0c114ff09714cf4e6, branch feature/s81-s10-fragrance-only-gate, `git status --short` 0 lines, the RED file fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e and the golden 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a, no .qa-mutation.lock. Nothing of mine was ever written there.
- my scratch worktree: every tracked file sha-equal to the unit worktree after the last restore (align_final.tsv, 0 differing), the probe file deleted, no lock; then removed (rc 0, absent from `git worktree list`, the folder gone).
- no pytest of mine running (every run finished; harness/locks empty); no process killed.
- files written: only under <scratchpad>/S81-10_fix1/reverify/ (scripts, logs, JSON results, notes.md, rv_report_body.txt) and this report <scratchpad>/S81-10_fix1/REVERIFY_REPORT.md, written by make_rv_report.py through the shell (ASCII, LF).
- the PR body (<scratchpad>/S81-10_green/PR_BODY.md) was read, never edited: its "Re-verifier ... PENDING" line is the orchestrator's to replace (25,290 B now; 310 B of headroom under 25,600).

## Appendix A: every [pyt] line of this re-verification (rebuilt field by field from the runner's own ledger pyt_ledger.jsonl, elapsed at the ledger's precision, log= dropped; the mutation and comm-chunk lines are in Appendices B and C as printed)
```
[pyt] tag=s10rv-red-off start=2026-11-02 15:29:49 end=2026-11-02 15:29:55 elapsed=6.8s bound=600s status=OK rc=0
[pyt] tag=s10rv-red-on start=2026-11-02 15:30:03 end=2026-11-02 15:30:10 elapsed=6.8s bound=600s status=OK rc=0
[pyt] tag=s10rv-collect start=2026-11-02 15:30:30 end=2026-11-02 15:30:34 elapsed=4.2s bound=600s status=OK rc=0
[pyt] tag=s10rv-shift-d1 start=2026-11-02 15:32:08 end=2026-11-02 15:32:13 elapsed=5.9s bound=600s status=OK rc=0
[pyt] tag=s10rv-shift-d10 start=2026-11-02 15:32:14 end=2026-11-02 15:32:19 elapsed=4.7s bound=600s status=OK rc=0
[pyt] tag=s10rv-shift2-d1 start=2026-11-02 15:32:35 end=2026-11-02 15:32:39 elapsed=4.6s bound=600s status=OK rc=0
[pyt] tag=s10rv-shift2-d10 start=2026-11-02 15:32:40 end=2026-11-02 15:32:44 elapsed=4.7s bound=600s status=OK rc=0
[pyt] tag=s10rv-shift2-d400 start=2026-11-02 15:32:45 end=2026-11-02 15:32:49 elapsed=4.5s bound=600s status=OK rc=0
[pyt] tag=s10rv-shift2-d-2 start=2026-11-02 15:32:50 end=2026-11-02 15:32:54 elapsed=4.6s bound=600s status=OK rc=0
[pyt] tag=s10rv-ciorder start=2026-11-02 15:42:01 end=2026-11-02 15:42:02 elapsed=0.5s bound=1200s status=FAIL rc=4
[pyt] tag=s10rv-ciorder2 start=2026-11-02 15:42:17 end=2026-11-02 15:43:47 elapsed=90.6s bound=1200s status=OK rc=0
[pyt] tag=s10rv-secretscan start=2026-11-02 16:03:01 end=2026-11-02 16:03:09 elapsed=8.0s bound=600s status=OK rc=0
[pyt] tag=s10rv-hookcollect start=2026-11-02 16:03:21 end=2026-11-02 16:03:25 elapsed=4.2s bound=600s status=OK rc=0
[pyt] tag=s10rv-hook-notdash start=2026-11-02 16:03:49 end=2026-11-02 16:19:08 elapsed=918.7s bound=1800s status=OK rc=0
[pyt] tag=s10rv-hook-dash start=2026-11-02 16:20:56 end=2026-11-02 16:39:50 elapsed=1133.9s bound=1800s status=OK rc=0
[pyt] tag=s10rv-c4collect start=2026-11-02 15:52:51 end=2026-11-02 15:53:03 elapsed=12.5s bound=600s status=OK rc=0
[pyt] tag=s10rv-probe start=2026-11-02 16:19:25 end=2026-11-02 16:19:28 elapsed=3.9s bound=600s status=OK rc=0
[pyt] tag=s10rv-b1-on start=2026-11-02 16:19:44 end=2026-11-02 16:19:55 elapsed=11.2s bound=600s status=FAIL rc=1
[pyt] tag=s10rv-b1-on-greenapp start=2026-11-02 16:20:33 end=2026-11-02 16:20:44 elapsed=10.9s bound=600s status=FAIL rc=1
  red_off: [hermeticity] sentinel checked 171 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 171 passed, 11 warnings in 5.80s
  red_on: [hermeticity] sentinel checked 171 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 171 passed, 11 warnings in 5.88s
  shift2_d1: [hermeticity] sentinel checked 19 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 19 passed, 121 deselected, 11 warnings in 3.68s
  shift2_d10: [hermeticity] sentinel checked 19 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 19 passed, 121 deselected, 11 warnings in 3.78s
  shift2_d400: [hermeticity] sentinel checked 19 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 19 passed, 121 deselected, 11 warnings in 3.61s
  shift2_d-2: [hermeticity] sentinel checked 19 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 19 passed, 121 deselected, 11 warnings in 3.70s
  ciorder2: [hermeticity] sentinel checked 2461 test(s) | [netguard] blocked 89 attempt(s) from 34 node(s) | 2461 passed, 4 deselected, 313 warnings in 88.27s (0:01:28)
  secretscan: [hermeticity] sentinel checked 31 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 31 passed, 1 warning in 7.29s
  hook_notdash: [hermeticity] sentinel checked 167 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 167 passed, 160 deselected, 7 warnings in 917.00s (0:15:17)
  hook_dash: [hermeticity] sentinel checked 160 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 157 passed, 3 skipped, 167 deselected, 7 warnings in 1133.05s (0:18:53)
  probe: [hermeticity] sentinel checked 10 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 10 passed, 10 warnings in 3.00s
  b1_on: [hermeticity] sentinel checked 199 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 7 failed, 192 passed, 11 warnings in 9.89s
  s10rv-b1-on-greenapp: [hermeticity] sentinel checked 199 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | 7 failed, 192 passed, 11 warnings in 9.61s
```

## Appendix B: the mutation runs (byte copies in MY scratch worktree; RED file + gate rows per run)
```
id	verdict	file	failed	error types	killing nodes (first 3)	[pyt]
EK1a	KILLED	tests/test_s81_s10_fragrance_gate.py	10	AssertionError	test_r54_off_calls_nothing_of_the_gate[unset], test_r54_off_calls_nothing_of_the_gate[false], test_r54_off_calls_nothing_of_the_gate[0] (+7)	[pyt] tag=s10rv-mut-ek1a start=2026-11-02 15:35:51 end=2026-11-02 15:36:01 elapsed=9s bound=600s status=FAIL rc=1
EK1a+10d	KILLED	tests/test_s81_s10_fragrance_gate.py	11	AssertionError	test_r46_reset_window_seam, test_r54_off_calls_nothing_of_the_gate[unset], test_r54_off_calls_nothing_of_the_gate[false] (+8)	[pyt] tag=s10rv-mut-ek1a10d start=2026-11-02 15:36:01 end=2026-11-02 15:36:10 elapsed=9s bound=600s status=FAIL rc=1
EK1b	KILLED	tests/test_s81_s10_fragrance_gate.py	10	AssertionError	test_r54_off_calls_nothing_of_the_gate[unset], test_r54_off_calls_nothing_of_the_gate[false], test_r54_off_calls_nothing_of_the_gate[0] (+7)	[pyt] tag=s10rv-mut-ek1b start=2026-11-02 15:36:10 end=2026-11-02 15:36:20 elapsed=9s bound=600s status=FAIL rc=1
F12a	KILLED	app/services/category_gate.py	2	AssertionError	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	[pyt] tag=s10rv-mut-f12a start=2026-11-02 15:36:20 end=2026-11-02 15:36:28 elapsed=8s bound=600s status=FAIL rc=1
F12b	KILLED	app/services/category_gate.py	2	AssertionError	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	[pyt] tag=s10rv-mut-f12b start=2026-11-02 15:36:28 end=2026-11-02 15:36:36 elapsed=7s bound=600s status=FAIL rc=1
F12c	KILLED	app/services/category_gate.py	2	AssertionError	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	[pyt] tag=s10rv-mut-f12c start=2026-11-02 15:36:36 end=2026-11-02 15:36:44 elapsed=8s bound=600s status=FAIL rc=1
F12d	KILLED	app/services/structured_comparison_service.py	1	AssertionError	test_f1_2_form_override_rewrites_the_overridden_stub[sync]	[pyt] tag=s10rv-mut-f12d start=2026-11-02 15:36:44 end=2026-11-02 15:36:52 elapsed=8s bound=600s status=FAIL rc=1
F12e	KILLED	app/services/structured_comparison_service.py	1	AssertionError	test_f1_2_form_override_rewrites_the_overridden_stub[stream]	[pyt] tag=s10rv-mut-f12e start=2026-11-02 15:36:53 end=2026-11-02 15:37:01 elapsed=8s bound=600s status=FAIL rc=1
F12f	SURVIVED	app/services/category_gate.py	0	-		[pyt] tag=s10rv-mut-f12f start=2026-11-02 15:37:01 end=2026-11-02 15:37:08 elapsed=7s bound=600s status=OK rc=0
F12g	KILLED	app/services/category_gate.py	2	AssertionError	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	[pyt] tag=s10rv-mut-f12g start=2026-11-02 15:37:08 end=2026-11-02 15:37:16 elapsed=8s bound=600s status=FAIL rc=1
F12i	KILLED	app/services/structured_comparison_service.py	15	AssertionError	test_p05_orchestrator_order_without_the_kwarg[unset-q-sync], test_p05_orchestrator_order_without_the_kwarg[unset-pair-sync], test_p05_orchestrator_order_without_the_kwarg[false-q-sync] (+12)	[pyt] tag=s10rv-mut-f12i start=2026-11-02 15:37:16 end=2026-11-02 15:37:24 elapsed=8s bound=600s status=FAIL rc=1
A11	KILLED	app/services/category_gate.py	2	AssertionError	test_f1_4_d3_house_pair_no_chip_refused_chip_proceeds, test_f1_4_qb06_camera_house_pair_refused_and_counted	[pyt] tag=s10rv-mut-a11 start=2026-11-02 15:38:27 end=2026-11-02 15:38:35 elapsed=8s bound=600s status=FAIL rc=1
A12	KILLED	app/services/category_gate.py	1	AssertionError	test_f1_5_other_chip_refused_with_one_a2b_call	[pyt] tag=s10rv-mut-a12 start=2026-11-02 15:38:35 end=2026-11-02 15:38:44 elapsed=8s bound=600s status=FAIL rc=1
A14	KILLED	app/services/category_gate.py	1	AssertionError	test_f1_6_retry_after_rounds_up_a_fractional_second	[pyt] tag=s10rv-mut-a14 start=2026-11-02 15:38:44 end=2026-11-02 15:38:52 elapsed=8s bound=600s status=FAIL rc=1
A14r	KILLED	app/services/category_gate.py	1	AssertionError	test_f1_6_retry_after_rounds_up_a_fractional_second	[pyt] tag=s10rv-mut-a14r start=2026-11-02 15:38:52 end=2026-11-02 15:39:01 elapsed=8s bound=600s status=FAIL rc=1
A17	KILLED	app/services/category_gate.py	1	AssertionError	test_f1_6_camera_vision_texts_carry_the_brand	[pyt] tag=s10rv-mut-a17 start=2026-11-02 15:39:01 end=2026-11-02 15:39:09 elapsed=8s bound=600s status=FAIL rc=1
A29	KILLED	app/services/category_gate.py	1	AssertionError	test_f1_6_exemption_allow_list_matches_any_case	[pyt] tag=s10rv-mut-a29 start=2026-11-02 15:39:09 end=2026-11-02 15:39:19 elapsed=9s bound=600s status=FAIL rc=1
A29b	KILLED	app/services/category_gate.py	2	AssertionError	test_r47_budget_exempt_allow_list, test_f1_6_exemption_allow_list_matches_any_case	[pyt] tag=s10rv-mut-a29b start=2026-11-02 15:39:19 end=2026-11-02 15:39:28 elapsed=9s bound=600s status=FAIL rc=1
QM12	KILLED	app/api/image_routes.py	2	AssertionError	test_f1_4_qb06_camera_house_pair_refused_and_counted, test_qb02_camera_post_resolve_counted_once_refunded_once	[pyt] tag=s10rv-mut-qm12 start=2026-11-02 15:39:28 end=2026-11-02 15:39:36 elapsed=8s bound=600s status=FAIL rc=1
QM12t	KILLED	app/api/text_routes.py	2	AssertionError	test_f1_4_d3_house_pair_no_chip_refused_chip_proceeds, test_qb02_sync_refusal_counted_once_refunded_once[post]	[pyt] tag=s10rv-mut-qm12t start=2026-11-02 15:39:36 end=2026-11-02 15:39:44 elapsed=8s bound=600s status=FAIL rc=1
A02	KILLED	app/api/text_routes.py	1	AssertionError	test_qb03_admin_key_bypass_get_and_stream[get]	[pyt] tag=s10rv-mut-a02 start=2026-11-02 15:39:44 end=2026-11-02 15:39:52 elapsed=8s bound=600s status=FAIL rc=1
A03	KILLED	app/api/text_routes.py	1	AssertionError	test_qb03_admin_key_bypass_get_and_stream[stream]	[pyt] tag=s10rv-mut-a03 start=2026-11-02 15:39:52 end=2026-11-02 15:40:00 elapsed=8s bound=600s status=FAIL rc=1
QM09	KILLED	app/api/image_routes.py	1	AssertionError	test_qb04_camera_budget_anon_metering_on_refunds_once	[pyt] tag=s10rv-mut-qm09 start=2026-11-02 15:40:00 end=2026-11-02 15:40:08 elapsed=8s bound=600s status=FAIL rc=1
```

## Appendix C: comm chunks (192-file ruled SUBSET s10rvc-*, 233-file complement s10rvx-*)
```
s10rvc-00 25 files | 1295 passed, 12 warnings in 75.27s (0:01:15) | failed=[]
   [pyt] tag=s10rvc-00 start=2026-11-02 15:44:06 end=2026-11-02 15:45:22 elapsed=77s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 1295 test(s)
   [netguard] blocked 50 attempt(s) from 11 node(s)
s10rvc-01 25 files | 548 passed, 1 skipped, 11 warnings in 34.05s | failed=[]
   [pyt] tag=s10rvc-01 start=2026-11-02 15:45:23 end=2026-11-02 15:45:58 elapsed=35s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 548 test(s)
   [netguard] blocked 56 attempt(s) from 19 node(s)
s10rvc-02 25 files | 1570 passed, 5 deselected, 13 warnings in 47.10s | failed=[]
   [pyt] tag=s10rvc-02 start=2026-11-02 15:45:58 end=2026-11-02 15:46:47 elapsed=49s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 1570 test(s)
   [netguard] blocked 19 attempt(s) from 4 node(s)
s10rvc-03 25 files | 2 failed, 637 passed, 16 warnings in 34.78s | failed=['tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest', 'tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction']
   [pyt] tag=s10rvc-03 start=2026-11-02 15:46:47 end=2026-11-02 15:47:23 elapsed=36s bound=1200s status=FAIL rc=1
   [hermeticity] sentinel checked 639 test(s)
   [netguard] blocked 154 attempt(s) from 19 node(s)
s10rvc-04 25 files | 820 passed, 6 deselected, 10 warnings in 106.82s (0:01:46) | failed=[]
   [pyt] tag=s10rvc-04 start=2026-11-02 15:47:48 end=2026-11-02 15:49:36 elapsed=108s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 820 test(s)
   [netguard] blocked 54 attempt(s) from 9 node(s)
s10rvc-05 25 files | 3340 passed, 12 warnings in 166.46s (0:02:46) | failed=[]
   [pyt] tag=s10rvc-05 start=2026-11-02 15:49:36 end=2026-11-02 15:52:25 elapsed=169s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 3340 test(s)
   [netguard] blocked 43 attempt(s) from 11 node(s)
s10rvc-06 25 files | 414 passed, 2 skipped, 12 deselected, 16 warnings in 54.44s | failed=[]
   [pyt] tag=s10rvc-06 start=2026-11-02 15:53:53 end=2026-11-02 15:54:49 elapsed=56s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 415 test(s)
   [netguard] blocked 128 attempt(s) from 47 node(s)
s10rvc-07 17 files | 946 passed, 6 deselected, 13 warnings in 28.06s | failed=[]
   [pyt] tag=s10rvc-07 start=2026-11-02 15:54:49 end=2026-11-02 15:55:18 elapsed=29s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 946 test(s)
   [netguard] blocked 84 attempt(s) from 32 node(s)
s10rvx-00 25 files | 2 failed, 621 passed, 3 skipped, 31 warnings in 25.12s | failed=['tests/test_auth_interceptor.py::test_sign_in_with_social_exception', 'tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully']
   [pyt] tag=s10rvx-00 start=2026-11-02 15:55:28 end=2026-11-02 15:55:54 elapsed=26s bound=1200s status=FAIL rc=1
   [hermeticity] sentinel checked 623 test(s)
   [netguard] blocked 7 attempt(s) from 6 node(s)
s10rvx-01 25 files | 972 passed, 4 skipped, 11 deselected, 13 warnings in 30.37s | failed=[]
   [pyt] tag=s10rvx-01 start=2026-11-02 15:55:55 end=2026-11-02 15:56:26 elapsed=32s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 976 test(s)
   [netguard] blocked 11 attempt(s) from 8 node(s)
s10rvx-02 25 files | 1952 passed, 1 skipped, 15 warnings in 92.56s (0:01:32) | failed=[]
   [pyt] tag=s10rvx-02 start=2026-11-02 15:56:26 end=2026-11-02 15:58:01 elapsed=94s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 1953 test(s)
   [netguard] blocked 23 attempt(s) from 22 node(s)
s10rvx-03 25 files | 449 passed, 1 skipped, 13 warnings in 25.77s | failed=[]
   [pyt] tag=s10rvx-03 start=2026-11-02 15:58:01 end=2026-11-02 15:58:28 elapsed=27s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 450 test(s)
   [netguard] blocked 10 attempt(s) from 10 node(s)
s10rvx-04 25 files | 442 passed, 1 skipped, 10 deselected, 12 warnings in 25.95s | failed=[]
   [pyt] tag=s10rvx-04 start=2026-11-02 15:58:28 end=2026-11-02 15:58:55 elapsed=27s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 443 test(s)
   [netguard] blocked 0 attempt(s) from 0 node(s)
s10rvx-05 25 files | 3733 passed, 28 skipped, 1 deselected, 1 xfailed, 14 warnings, 2 errors in 31.24s | failed=['tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence', 'tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable']
   [pyt] tag=s10rvx-05 start=2026-11-02 15:59:02 end=2026-11-02 15:59:35 elapsed=33s bound=1200s status=FAIL rc=1
   [hermeticity] sentinel checked 3737 test(s)
   [netguard] blocked 87 attempt(s) from 6 node(s)
s10rvx-06 25 files | 855 passed, 1 skipped, 263 warnings in 84.94s (0:01:24) | failed=[]
   [pyt] tag=s10rvx-06 start=2026-11-02 15:59:35 end=2026-11-02 16:01:02 elapsed=87s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 856 test(s)
   [netguard] blocked 2 attempt(s) from 2 node(s)
s10rvx-07 25 files | 2049 passed, 1 xfailed, 95 warnings in 42.76s | failed=[]
   [pyt] tag=s10rvx-07 start=2026-11-02 16:01:02 end=2026-11-02 16:01:46 elapsed=44s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 2050 test(s)
   [netguard] blocked 2 attempt(s) from 2 node(s)
s10rvx-08 25 files | 619 passed, 6 skipped, 35 xfailed, 16 warnings in 48.77s | failed=[]
   [pyt] tag=s10rvx-08 start=2026-11-02 16:01:46 end=2026-11-02 16:02:36 elapsed=50s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 660 test(s)
   [netguard] blocked 1 attempt(s) from 1 node(s)
s10rvx-09 8 files | 311 passed, 10 skipped, 1 warning in 5.89s | failed=[]
   [pyt] tag=s10rvx-09 start=2026-11-02 16:02:37 end=2026-11-02 16:02:43 elapsed=7s bound=1200s status=OK rc=0
   [hermeticity] sentinel checked 321 test(s)
   [netguard] blocked 0 attempt(s) from 0 node(s)
```

## Appendix D: probe records (tests/test_zz_rv_probe.py, run once in the scratch worktree, then deleted)
```
{"probe": "f12_partial_explicit", "value": {"coherent": true, "ctx_cats": ["fragrances", "fragrances"], "ctx_used": "fragrances", "md_cats": ["fragrances", "fragrances"], "md_status": "supported_result", "reasons": [], "res_code": "INSUFFICIENT_DATA"}}
{"probe": "f12_partial_vision", "value": {"coherent": true, "ctx_cats": ["fragrances", "fragrances"], "ctx_used": "fragrances", "md_cats": ["fragrances", "fragrances"], "md_status": "supported_result", "reasons": [], "res_code": "INSUFFICIENT_DATA"}}
{"probe": "f12_control_no_decision", "value": {"ctx_cats": ["haircare", "fragrances"], "md_cats": ["haircare", "fragrances"], "md_status": "unsupported_category", "reasons": ["category_conflict"]}}
{"probe": "m4", "value": {"classify": 0, "ctx_cats": ["fragrances", "other"], "ctx_used": "fragrances", "decision": ["proceed", true], "evals": 0, "fetch": [["fetch", 0, "fragrances"], ["fetch", 1, "fragrances"]], "res_code": "INSUFFICIENT_DATA"}}
{"probe": "m6_None", "value": {"category": "skincare", "classify": 0, "decision": ["proceed", false], "evals": 1, "fetch": 0, "res_code": "CATEGORY_NOT_LIVE"}}
{"probe": "m6_fragrances", "value": {"category": "skincare", "classify": 0, "decision": ["proceed", false], "evals": 1, "fetch": 0, "res_code": "CATEGORY_NOT_LIVE"}}
{"probe": "l17_override", "value": {"decision_loads": 1, "total_loads": 5}}
{"probe": "l17_explicit_no_override", "value": {"decision_loads": 1, "total_loads": 3}}
{"probe": "l17_q", "value": {"decision_loads": 1, "total_loads": 1}}
{"probe": "m10_m11", "value": {"12 \\u0633\\u0627\\u0639\\u0629 vs 8 \\u0633\\u0627\\u0639\\u0629": ["proceed", null, false], "\\u0643\\u0631\\u064a\\u0645 nivea vs \\u0643\\u0631\\u064a\\u0645 dove": ["proceed", null, false], "\\u0643\\u0631\\u064a\\u0645 nivea vs \\u0644\\u0648\\u0634\\u0646 dove": ["refuse", "skincare", false], "apple watch vs galaxy watch": ["refuse", "fashion", false]}}
```

## Appendix E: files written by the re-verifier (sha256 over the bytes on disk; all under <scratchpad>/S81-10_fix1/reverify/ except this report)
```
cc0239e74c2176100dc6850d1aa3a2f816c28756a4727ec6e79a631992bdc4c6  align.py  1927 B
a10d34010fdedded5006c908a7895f90253a504ff10dd03af71e61bef86c0cd8  align_after.tsv  656233 B
a10d34010fdedded5006c908a7895f90253a504ff10dd03af71e61bef86c0cd8  align_after_mut.tsv  656233 B
d5294a91c8dbb067b03c85bae4373e425f5346ae6ccccdaf3c7c051f51da0e0c  align_apply.tsv  656243 B
22127a1ba551662e572669ea4383da47e0fa13664c5d4862d865c94d254eb090  align_before.tsv  656248 B
a10d34010fdedded5006c908a7895f90253a504ff10dd03af71e61bef86c0cd8  align_final.tsv  656233 B
0a5ed28dd8451620e69d3ff494044d9ecf5b86c87d56dd66c0b473f1d1b87ff6  chunk4_files.txt  833 B
d2f6b3c9640ce3c867cede830cc682331fe4626e61a3bf76d00a15dc8ed2807b  ciorder_files.txt  1045 B
abd3ef8af6e2c1129c4e9ccc1d8e7fe676e9f36075e93ead0d2fb6dfffa3a115  ciorder_files_fix.txt  1076 B
104dd31397ab799540f22b9a5c9154fcf9b60a9917725562324795a95b44b0c9  ciorder_list.txt  1042 B
f9f90ea83a762db5125e8aa5acb8e3067d91abf8ca43fd84517ff4341f630abf  comm_complement_rv.txt  8280 B
2a4c7fa8da2fd28798acdfa1c9e5b20fe061678a222d57d1e53ce3a99d7e2e95  comm_s10rvc.json  39256 B
fa7e46ce2aff20ce2dff80502731520cf66961e558a60be74b344926bd89ce1d  comm_s10rvx.json  25384 B
8961609cdbcf1d73e1f90e1f2644337f87e8a9950e29a255dacd18780f0b35d6  comm_subset_rv.txt  6955 B
552bfb9e7ebfc79e52a0a4e16758fd906e0a0d96360b0740f0e3dae188f26d66  make_rv_report.py  5755 B
1bc283aeb0fd5a3677ce639030598bd30eb431b272e801a21d95d65a2abcb828  mutants_for_output.json  3462 B
7db8eaf92e7270240bd38da8144eb7af5b207907e4b5ba39cd34d8b607afed13  notes.md  2407 B
e422f13a706bbfa58851b25a22f83e7f5bf9d0b61de754b0da2202d2aead5c70  prbody_diff.txt  26578 B
95b605616ca5c798ab3461fafc200821756fd8ff203546f1cfee9259aca4f2c0  rv_comm.py  4111 B
98ce8ce143f635ed3308c2236519ad927331e473ca3eec694c65315e260d11aa  rv_green_app.py  2589 B
972a8ddecda7122d045dcf962f1d27807943dcd80f505226696f790bf601f295  rv_mut.py  14409 B
cc07944d4a53445e9657b506728a6e0ae46997b670c732a630f0af7e937decf8  rv_mut_manifest.txt  835 B
cc07944d4a53445e9657b506728a6e0ae46997b670c732a630f0af7e937decf8  rv_mut_manifest_batch1.txt  835 B
26b8ffb227b49373930c0f599aa633b66c9085af208579e8d839451f493d4a38  rv_mut_results.json  14399 B
a0552adfe9f181c8ff8751cabe83533a31a995fe10fc8b2f9f999c13957925fb  rv_mut_results_batch1.json  17374 B
26b8ffb227b49373930c0f599aa633b66c9085af208579e8d839451f493d4a38  rv_mut_results_batch2.json  14399 B
90b3e40d977adb94e69cd0cf05d61f6f53d375335f0133bd406bc111b7d6d8ba  rv_reparse.py  1875 B
85779b12ae4a937bb802dd993abc45686f60c9ba66006cfbf11733f20e10dbc5  rv_report_body.txt  27589 B
86601054a378db46e0c288b8d4c48cd452869872aae84937dbeafbe960b6e661  static_checks.py  3171 B
0707885d0c7e7adf061288e6b2ab712c44343a6e56a6403ddd2a5f8f7c8353ac  static_checks.txt  2955 B
bea3ee33304ad2497a0496785b36660fbc3f7cdcb887bb4c03b9290e0b43218f  test_zz_rv_probe.py  8895 B
bea8fba1818c176d0b7c751d810ac06ee435b088b85e08e650c0b7bd06b131fd  probe_plugin/rv_clock_shift.py  3017 B
logs/ (68 files): the per-run pytest logs, mutant logs (logs/mut/), comm chunk logs (logs/comm/)
```


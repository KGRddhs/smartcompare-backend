# RULINGS_INC_P2 (orchestrator S96-FIX, Claude Opus 5.5, 2026-11-16): the rulings on .qa-s80/INC-P2_UNIT_SPEC.md (4baaede0...), .qa-s80/INC-P2_SPEC_REVIEW.md (BLOCK: B1-B4, R-1..R-13, C-1..C-11, questions 1-9) and the brief INC_P2_BRIEF.md with its ADDENDA 1 and 2 (P2-1..P2-23). Binding on the RED

Precedence: this file, then the brief's ADDENDA, then the review, then the spec, then the brief body. The RED applies these rulings to the spec's rows and change list. Its report carries an "amended rows" table: each row added, rewritten or dropped, and the ruling behind it. It does NOT rewrite the spec file.

## A. The four blocking points

- P2R-1 (B1; review question 5; ADDENDA 1-2): the RED writes rows for P2-19, P2-20 (it supersedes P2-17's mechanism), P2-21, P2-22 and P2-23. Their contracts are below (P2R-10 to P2R-14).
- P2R-2 (B2; question 2) CONFIRMED. One comparability reader per side, used for the decision, the P2-4 projection and the pair marker: the strict listing size (X1-R7), else the side's typed size (typed_size_ml), else effective_pair_size_ml. Add RED rows for "typed 30 with a size-less listing vs 100" and for "'50ml / 100ml' vs 100".
- P2R-3 (B3; R-3; question 1) KEEP C1 AS IS. A typed side's off-size listing stays pending (not_exact at the chokepoint). No size-free backstop in this unit, and X1-R3 is NOT carried over. Rewrite A08 on the measured truth. The reason this beats the alternative: neither app bundle draws any size (R-10), so a 50 ml price shown under a typed "100 ML" would be read as the 100 ml price. The T3-01 fix still holds: a side at its OWN typed size is no longer pended because the other side typed a smaller size. Correct the header's X1-R3 / X1-R12 claim (R-4). X1-R12 does apply to the size_ml / per_ml stamp: no stamp on a price with no url.
- P2R-4 (B4; R-5; R-6) ACCEPTED as the review states. should_cache_price(...) stays the gate expression at both write sites, with its body byte-identical. The refusal reason is computed only after a False, in a separate log-only helper inside its own try/except. So the scs.should_cache_price patches keep working and no traceback frame is added. Add test_m18_offload_sweep_residual.py and test_negcache_genuine_invalidation.py to 4.2.

## B. The review's other questions

- P2R-5 (question 3, K-2) The P2-7 write caches only a re-selection to the side's typed size or to the pair's common size. A converted re-selection never overwrites a genuine entry: read the key first, and skip with a PRICE_CACHE_SKIP reason when a genuine entry is there. Never a pending, estimate or floor-failing (P2R-12) price. The write is inline, bounded by asyncio.wait_for of 1.0 s, and every failure is swallowed with a WARNING. That answers spec O5: it is rare (only when a swap happened), deterministic in tests, and has no background task to drain.
- P2R-6 (question 4, P2-18 / P2-23) seen_at uses the underscore key `_seen_at` (ISO-8601 UTC), written into the L1 price dict under the flag at the moment the price was fetched or re-selected. Measure whether the L1 write path keeps underscore keys. If it strips them, use the public key `seen_at`, state that it reaches the wire, and pin that the store and OTA bundles ignore it. An L2 to L1 promotion carries L2's `fetched_at` as `_seen_at` when absent. L2 gets no new column (stated limit: L2's fetched_at is the save time). Flag OFF: cache writes byte-identical (a PIN).
- P2R-7 (question 6) ADD `marketplace=0|1` and `retailer=` (the retailer name token, cut to 30 characters) to PRICE_OUTCOME. The Whatnot proof reads those fields, not the host (R-9).
- P2R-8 (question 7) Keep walking both ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX cells. Name the cell on every pair row (C-3). A11 is RED with the fix flag OFF (R-7). The 91.780 evidence is noted in the gate report as LIKELY ON, not proof.
- P2R-9 (question 9, spec O3) YES: a showable genuine reseller hit replaces a park that _is_listing_url marks (it cannot be shown anyway). Otherwise it never replaces a genuine park.
- Question 8 (should the flip wait for the INC-C1 update that draws the size): NOT this lane's ruling. The gate report puts it to the relay with a plain statement of what today's phone draws.

## C. The ADDENDA contracts (P2R-10 to P2R-14)

- P2R-10 (P2-19) Each of the three log lines is built and emitted inside its own try/except. That includes PRICE_CACHE_HIT inside the price race task and the unflagged trace note in the fragrance branch (C-6): a raise there must not log a false "fairness reconciliation skipped". RED rows inject a raising logger or formatter at each site and assert the response or price is unchanged. A flag-OFF identity PIN covers every partial body (the verdict-window, moderation-window, stream tail and gather-time partials) with the full production configuration.
- P2R-11 (P2-20) THE MISS LEDGER. Build it on the spec's _PRICE_TRACE ContextVar (one list object per product, keyed by full_name, bound before the price task starts so it survives a cancel). PRICE_OUTCOME reads it, at the response chokepoint and at the hard-cap partial build. The fields follow R2_fetch_chain.md's section "What the PRICE_OUTCOME line needs" (slot, product cut to 60, shown, amount, currency, size_ml, method, retailer, marketplace, origin, race / race_ms, reconcile / pend_reason, display_rule, miss, miss_host, miss_status, miss_rule, fam counts, the rejected-per-check counts with at most two example titles cut to 60, cache_write).
  - REQUIRED: timed_out (race outcome); not_found; rejected with the rule name, its counts and its titles, from the filters that already run (numbers_match, select_best, size / floor, showable / display rule, implausible_low, concentration, out_of_stock, marketplace).
  - refused and no_price_parsed: recorded only at sites that already log the status today (the ADAPTER DROP lines, the Shopify catalog HTTP status, FETCH-FAIL), with a one-call note beside the existing log line. The status_out parameter for curl_fetch_html_same_site and the status in the Shopify negative sentinel are NOT in this unit. They belong to INC-P3 SHOP-POLITE, which owns _fetch_shopify_catalog. Stated limit: until INC-P3, a refusal from a cached negative entry or a curl fetch without a status reads miss=refused with miss_status=unknown, or not at all.
  - The ledger appends are pure in-memory appends inside a guard and run unflagged, so the before picture exists. Nothing in a response body reads them (PIN).
- P2R-12 (P2-21) THE FLOOR, under the flag, in reconcile_pair_sizes_v2 and the both-shown path. A candidate or current price whose comparability size is under 30 ml, or whose title carries travel, miniature, mini, atomiser or atomizer as a word, is never a side's price unless that side's typed size equals its size. A side whose current price fails the floor is re-selected from candidates that pass it. If none passes, it is pended (pending_genuine), with miss=rejected and miss_rule=floor in the ledger. RED rows use a 10 ml travel spray at 8, 10 and 12 BHD (each one passes the plausibility floor at base: prove that at base). Add PIN rows for "Mini" inside a line name if the seed or lexicon carries one (measure; otherwise state it). A typed "10ml" keeps the 10 ml price.
- P2R-13 (P2-22) Rasasi Hawas gets a _GENDER_FLIP_LINES row, with a code comment and a PR-body line that it is a data row the owner may veto. Under the flag if the reader can take a flag-gated extra tuple in two lines or fewer. Otherwise it is unflagged and stated in deploy_visible_delta. RED decides by measurement and reports which.
- P2R-14 Every reason the spec added to deploy_visible_delta is stated in plain words in the gate report (the relay's condition 3).

## D. Corrections accepted

- P2R-15 R-1 to R-13 are accepted as refutations. C-1 (the proof), C-2 (age_s=unknown), C-3, C-4 (the Feature Flags pointer sentence after INC-R1's at CLAUDE.md:341, with every CLAUDE.md reader of R-8 in the comm set), C-5 (each mutation gap gets a killing row), C-6, C-7 (the tokenizer and "the realreal" phrase; refurb sellers drop from the Tier-1 pick in every category under the flag: stated), C-8, C-9, C-10 and C-11 are accepted as written.
- P2R-16 Spec open questions: O1 keep the dry-run projection; the winner_evidence sentence on the saved row is a stated limit (no bundle renders it). O2 confirmed: a converted price also gets size_ml from its own title. O4: PRICE_CACHE_SKIP at the two genuine write sites and the P2-7 write only. O6: metadata.pair_price_sizes confirmed. O7: the SSE restore confirmed (the same step in every build). O8 / R-13: no E1 expected; the RED confirms by a run.

## E. The proof (replaces the spec's 8b where they differ)

What the phone draws after the flip, with no client change (P2-6, measured): two amounts with the existing converted label; no "No confirmed price yet" line where a price was found; no price or value bars and no cheaper line when the sizes differ; NO size (no bundle draws one until INC-C1). Checks:
1. "YSL Libre EDP" vs "Lancome La Vie Est Belle EDP": two amounts.
2. A Baccarat Rouge 540 pair: two amounts.
3. "Sauvage EDP" vs "Bleu de Chanel EDP" twice: the same two amounts. Run 1's PRICE_OUTCOME must show origin=live and reconcile=reselected for the swap to be exercised. If it shows a cache origin, the check is not exercised and is said so.
4. "Ted Baker M 30ml" vs "Dior Sauvage 100 ML Edp": two amounts, no cheaper line, `marketplace=0` on both PRICE_OUTCOME lines.
Backing: the PRICE_OUTCOME lines (both slots, reconcile, size_ml, miss); PRICE_CACHE_HIT on run 2; no pend_reason=size_mismatch.

## F. Class and next

- P2R-17 Class FOCUS: RED, then the orchestrator's gate, then GREEN with two adversaries (correctness; contract and live bundles). The RED runs the base comm set (750 files plus the CLAUDE.md readers of R-8) in chunks through gate.py, one pytest at a time across the box.

## G. RULING ORCH-P2-A (the relay, 2026-11-16 21:05 local; binding; it amends P2-3, P2-5 and section E)

- P2R-18 With ENABLE_PRICE_NOT_LOST on, a side on the both-shown path of P2-3 (its comparability size differs from the other side's) gets its price in price.amount ONLY when the request's X-Client-Capabilities header lists the token `price_size`. Parse it exactly as kb_serve.client_price_asof does (comma separated, stripped, case-insensitive) in a small reader of this unit under the P2 switch: request-scoped (a ContextVar bound at the route, or the value passed down), never dependent on ENABLE_KB_FIRST_SERVE.
- P2R-19 Without the token, that side stays as today (the pending dict flag OFF would produce: size_mismatch), and its off-size listing travels in the additive key `price.offsize_listing` = {amount, currency, size_ml, per_ml, retailer, url, title cut to 120, source_method} (X1's name, X1-R9). Today's bundles ignore it (measure both bundles once: no reader of offsize_listing). With the token, price.offsize_listing is absent and price.amount carries the price with size_ml / per_ml.
- P2R-20 Equal sizes, a typed side (P2R-3) and the T3-01 fix are unchanged. The P2-4 projection is unchanged in both cells. The floor (P2R-12) applies to the offsize_listing too.
- P2R-21 RED: every both-shown row runs in two cells (token present, token absent), plus the header reader rows (absent header, other tokens only, ' Price_Size ' mixed case and spaces, a list with it). With the switch off nothing changes (PIN with the token present). The PRICE_OUTCOME line gets `cap=price_size|none` and reconcile=both_shown or offsize_held.
- P2R-22 STABLE FIELD NAMES from now (the main lane's over-the-air unit reads them): price.size_ml (number), price.per_ml (number, 4 decimals, currency per ml), price.offsize_listing (object above), metadata.pair_price_sizes, the request token price_size in X-Client-Capabilities. Any change goes to the relay first.
- Proof (section E, check 1-2 amended): a phone without the token draws exactly today's screen for a different-sizes pair (one amount, one "No confirmed price yet"); after the main lane's update sends price_size it draws both amounts with their sizes.

## H. RULING ORCH-P2-B (the relay, 2026-11-16 22:20 local; binding; it supersedes section G wherever they differ) and the RED gate

- P2R-23 RULE 1: A side with a TYPED size shows its price whenever the listing's size equals the size typed for THAT side, whatever the other side's size and whatever the token. A listing of another size under a typed size stays pending (P2R-3), never shown unlabelled. So the T3-01 pair (30 ml typed on one side, 100 ML on the other) shows both prices on every app.
- P2R-24 RULE 2: The price_size gate applies ONLY to a side with NO typed size whose found listing is for a different bottle size than the other side's shown price (part b). Without the token that side stays pending with price.offsize_listing; with the token it is shown with size_ml / per_ml.
- P2R-25 RULE 3 (mixed pair): the typed side follows rule 1. The untyped side follows rule 2 when its listing size differs from the typed side's size.
- P2R-26 RULE 4: No state may be worse than today. A side that shows a price with the flag OFF never loses it because the token is absent. A RED row walks every fixture pair in the cap0 cell and asserts that every side shown with the flag OFF is shown with the flag ON. The P2-4 projection (no comparison when sizes differ) is unchanged.
- P2R-27 THE FROZEN SET is agent B's (red/test_inc_p2_price_not_lost.py 43cec7b7..., red/test_inc_p2_seam.py 0f3831da..., RED_REPORT_B.md), as amended by ONE RED amendment. It (a) rewrites every cap0 cell that holds a typed side (A04/A05, A19 and any other); (b) adds rows for rules 1-4, including the mixed pair; (c) ports agent A's unique rows (RED_REPORT_B.md section 11, "Only in A's") adapted to B's prototype seams; (d) re-proves base / prototype / the affected mutants plus new ones for rules 1-4; (e) installs the final pair into sc-inc-p2/tests after backing up A's two files to red/A_files/.
- P2R-28 Accepted at the gate: the five mutants killed by the injected fault escaping (M38, M43, M60, M61, M62) count as KILLED. D1 (app/api/text_routes.py, the three phone call sites, keyword price_size_cap) joins the change list. D3 (_seen_at reaches the wire only with ENABLE_EXACT_PRICE_GATE false), D4, D5 (Hawas under the flag, acts only with ENABLE_LISTING_MATCH_GUARD on), D6, D7, D8 (stream tail partials not driven) and D9 are stated limits. D2 is superseded by P2R-23.

## I. RED GATE RULINGS on the amendment (orchestrator S96-FIX, 2026-11-16 23:50 local; binding on GREEN)
- P2R-29 (amendment Q1, R1c) ACCEPTED: a TYPED side whose listing has no strict ml size is read through the P2R-2 reader as its typed size and is shown in both cells, without size_ml. Flag OFF already shows such a listing whenever fairness does not pend it.
- P2R-30 (Q2) ACCEPTED: the R4 walk exempts a side whose flag-OFF price fails the P2R-12 floor; the floor removes it in every cell, never because the token is absent.
- P2R-31 (Q3, A30) ACCEPTED, rule 4 over rule 2: when flag OFF pends nothing, a side the flag keeps at a different size (a refused marketplace re-selection) is shown in both cells; a phone without the token sees two amounts at different sizes with no size drawn, the price and value bars stay limited_data. Stated limit in the PR body and the flip note.
- P2R-32 (Q4, A's b13) NOT IN P2: a marketplace price reaching the wire by a path P2-10 does not cover stays shown with the flag ON and is visible as PRICE_OUTCOME marketplace=1. Stated limit; offered to the relay as a candidate for a later unit (no scope added here).
- P2R-33 (Q5) ACCEPTED: M01's one non-assertion node (A40, the injected fault escaping) is the P2R-28 class and counts as KILLED.
- P2R-34 The prototype's wire guard (amendment section 4 change 3: a typed side whose listing has ANOTHER strict size is never shown and never offsize-held, in either cell, whatever ENABLE_EXACT_PRICE_GATE says) is a CONTRACT of GREEN, pinned by A08's gate_off cells (mutant N07b).
- P2R-35 THE FROZEN PAIR: tests/test_inc_p2_price_not_lost.py sha256 43d309db521ca62b7df79450e937a0eb44f54c839e8843a4514960dd0bae0dee (98,120 B) and tests/test_inc_p2_seam.py sha256 07d72b74a83b7a8d104354ac92dd6fe60b756cbae80219155bf28654e2b69b86 (48,765 B); base b0ad2603: 408 RED (every one an AssertionError) / 87 PIN green; prototype ON 495/495, OFF 495/495; 26 mutants: 24 killed, N03 and N07 equivalent with stated reasons.

## J. RULING ORCH-P2-C (the relay, 2026-11-16 23:57 AST; binding)
- P2R-36 Supersedes P2R-32's offer: NO marketplace-hide unit now. Evidence first: after the ENABLE_PRICE_NOT_LOST window opens, the relay counts PRICE_OUTCOME lines carrying marketplace=1; any on a real comparison queues INC-P2m (a wire-level hide) right after INC-P3; none in the first days keeps it a stated limit. The flip note gives the plain filter words (no bracket): PRICE_OUTCOME and marketplace=1.
- P2R-37 The flip note states P2R-31 in one plain sentence: a phone without the app update can show two prices for different bottle sizes with no size drawn, and no price comparison is made. It lists the phone pairs with what the owner should see.
- The relay confirmed P2R-29, P2R-30, P2R-31, P2R-33 and P2R-34 as filed.

## K. Re-verifier rulings on fix round 1 (orchestrator S96-FIX, 2026-11-17 ~08:10 AST)
- P2R-38 (rv m3, fix DV1): ACCEPTED. The F3c walk's measured flag-OFF gain stands. After a rollback, a legitimate F3 (b) 100 ml entry lets flag OFF show both 100 ml sides where its no-write base pended them. It is a genuine price at its own size, so not a regression under rule 4. It is stated in SL5 and in the flip note's rollback.
- rv MAJOR-1: the canary filter is `cap=none` / `cap=price_size` (the logged values), not cap=0. My D2 wording and GATE line 34 were wrong.
  - Fixed in CLAUDE.md (commit 8bb97fe0) and in the PR body.
  - It is a docs-only fix under LC-2, so no new re-verifier.
- rv m1, m2: fixed in the PR body (the 30 ml reselect outcome named; the rollback wording no longer says "genuine" for converted entries).
- rv m4: stated limit. The code comment at response_builder :1917 overstates the identity on an internal wire fault; the comment is not edited in this unit.
- rv m5 and m6: stated limits.
- Rebase 2 onto bd0500a3 is done by the orchestrator; see GATE section 10.
- P2R-39 (CI backend-tests red on 8bb97fe0, 13 nodes in test_retro_w0_4_efg.py and test_s77_redis_offloop.py):
  - Cause, read from the CI log: the /health body carried llm_spend, llm_spend_fail_open and llm_spend_late_records. The three P2 files set ENABLE_LLM_SPEND_BREAKER=true (PROD_ON), and the breaker's process state (_STATE["ran"]) leaked forward in CI's one alphabetical process. conftest resets llm_credential and serper_keys per test, but not the spend breaker.
  - Fix, tests only: each P2 file gets an autouse fixture that, AFTER each test, calls llm_spend_breaker._reset_spend_breaker_state(). The rows are unchanged, so the frozen-pair sha256 pins move by ruling. The new hashes are recorded at the commit.
  - Committed as 93c6da3a (with the router reset too, after the link lane's finding).
  - New sha256: test_inc_p2_fix1.py 038c4c2a...85ecb; test_inc_p2_price_not_lost.py 9d92543f...8372a; test_inc_p2_seam.py fd1062c3...8d929d7.
  - Proof:
    - repro at 8bb97fe0: the same 13 failures as CI;
    - fixed, in the same order: 1706 passed;
    - the CI-order set of 44 files, alphabetical: 3478 passed;
    - the unit with the flag ON: 721 passed.

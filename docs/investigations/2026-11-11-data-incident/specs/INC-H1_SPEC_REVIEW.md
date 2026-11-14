# INC-H1 NO-CONFIDENT-EMPTY - ADVERSARIAL SPEC REVIEW (read-only round)

- Unit: INC-H1 NO-CONFIDENT-EMPTY, flag ENABLE_HONEST_EMPTY. Reviewer: the adversarial spec reviewer of this round (workflow agent, Opus 5.5). Date 2026-11-14.
- Spec under review: C:/Users/SynAckITPC/Documents/AI/sc-inc-h1/.qa-s80/INC-H1_UNIT_SPEC.md, re-hashed first: sha256 28504e3a5ebccd5a174024b50bb0d3daf68429a75e72c5878fdd7a8da36e788e (= the prompt's value), 111293 bytes.
- Base: 731bcddf531a7e123963246168ca19f262859337 (worktree HEAD measured = the base). `git -C <W> status --short`: EMPTY before the first probe and after the last one; no git write command was run; no file was written in the worktree except this review under the gitignored .qa-s80/ (`git check-ignore -v` -> .gitignore:72 `.qa-*/`).
- READ-ONLY round (common brief H5 c, R0-9): no pytest, no jest, no tsc, no eslint ran. Every run is DEFERRED TO RED (section 9). Plain python probes ran on committed blobs only (`git show`), never importing app code, never reading .env.
- Source reading: the plain export <SP>/src/731bcddf, re-proved byte-equal to the base blobs in this round (CRLF-normalised `git hash-object` vs `git rev-parse 731bcddf:<path>`: ES, SCS, FC, SS, RB, RV, RG, PDS, cache_service, url_extraction_service, ResultsAccordion, ConfidencePills, ResultsContent: SAME); CLAUDE.md copy = base blob ff7fe1fe (grep only). Store bundle read with `git show 683f56c0:`.
- Measurement location: <SP>/INC-IH/h1rev/ (probes/probe_prompts.py + .out, probes/probe_consensus.py + .out, probes/probe_d2f_reliability.py + .out, review_draft.txt, notes.txt). <SP> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad. Note: <SP>/INC-IH/ is shared with another review agent (its write_review.py and probes/*.py are not mine and were not touched).
- Short names as in the spec (ES, SCS, FC, SS, RB, RV, RG, PDS, HE, RA, RC, CP). Every file:line below was read at 731bcddf in this round.

## 1. Verdict: BLOCK

Three blocking issues (B1-B3, section 3). Each has a cheap unblock; none needs a redesign of the unit:
- B1: R12 asserts a count the specified change cannot produce (an unsatisfiable frozen RED row).
- B2: the S1 fact-check skip moves reliability (the fragrance Versatility bar, and one reliability-proxy dim in every one of the nine categories) for REAL data pairs; measured on the recorded pair D2F the Versatility bar of a data-rich Sauvage pair disappears. The spec says the opposite (2.5, 2.6, L-CROWN), walks no such shape, and carries no measured before/after (D2 F4 and ADV C-2 demanded one; common brief H6 c).
- B3: the dominant production path today (an account below consent 3: the egress stop turns every specs extract into an error dict) keeps building the reliability proxy from the `error` key, which S1 does not skip; H1-4's "a product with no real spec fields has a reliability total of 0" is not met there.

The design of the views (S16-S19), the cache guards, the prompt twins (hashes confirmed), the log line, the comm set and the flag-OFF identity plan are sound with the corrections of section 4.

## 2. Refuted claims (measured truth, file:line at 731bcddf)

RC1. Spec 5 R12: "each contains SEARCH_RESULTS_GUARD ... and "has_review_data" exactly once". REFUTED. The S14 change inserts the word twice: the shape line `    "has_review_data": true|false,` and the rule line `- has_review_data: true ONLY when ...`. Measured by AST evaluation of the committed ES blob (probes/probe_prompts.out): twin_base hrd 2, twin_nr hrd 2. CONFIRMED in the same probe: base REVIEWS_EXTRACTION_SYSTEM sha256 46791e1b346c8be5780004d0245f40bc0947d4445f7950aae04224b2d64987e3 (= the D08 P7 pin, tests/test_s81_d08_jsonld_widen.py:1147), NO_RATING ebe9f3f3..., both anchors once in each base constant, guard once, no `{brand}` / `{name}`, twins 3618 / 3533 chars with sha256 9bd925488019919bdc764948fbb42d56e3afca1ed09e183cce1bc57ebe1fb473 / 30fb98d183a67f3377748e94e4fd5bef13481329b694a85751b1838555a66a09 (base64 m9klSIAZkZvcdklI+7QtVuOvyh7Qnhg8zhvFfr4ftHM= / MPuY0YOmfzN3dI6U5P1b7xNIEym2lKhXUbGDhVWmagk=), pure ASCII. -> B1.

RC2. Spec 2.5 "changes nothing for real-only data" read together with 2.6 "Bars | no Versatility bar when both products have no real field; one side empty: the bar stays" and "Captions, pros / cons, prices, the crown display | unchanged (the crown can move only through the removed reliability gap: L-CROWN)", and 9 L-CROWN "No other scoring input moves". REFUTED for the common real shape (some real fields, some empty fields, some refilled fields). Measured on the recorded pair tests/fixtures/comparison_baseline_d2_post_bucket_a__fragrances.json (Tobacco Vanille vs Sauvage, the spec's own D2F fixture), probes/probe_d2f_reliability.out:
  - p0 fact_check 5 verified / 1 likely / 0 flagged / 4 unverified (the 4 unverified = its 4 empty fields), price_verified True; p1 4 / 0 / 0 / 6, price_verified True, where p1's 6 unverified = its 4 empty fields + longevity and sillage, which `_field_confidence` marks `smart_fallback`: they were "N/A" when SCS:6431-6455 graded them and were filled after the grade by the Phase-2 merges (SCS:6582-6589).
  - Today's formula (SS:2081-2104) reproduces the fixture's versatility breakdown exactly: 0.79 / 0.68 -> 79.0 / 68.0.
  - With S1: p0 (5 + 0.7) / 6 + 0.1 -> 1.0, p1 4 / 4 + 0.1 -> 1.0 -> 100.0 / 100.0, a tie of non-MISSING values, which the T-OFF branch (production, SS:2259-2268) collapses to MISSING on both sides -> `_dim_from_category_lookup` returns None (SS:3569-3571): the Versatility bar of a data-rich real pair disappears; the overalls move -4.35 / -2.70 (R OFF legacy sum, MISSING_SCORE 50, SS:297).
  - Without the price bonus the same pair reads 95.0 vs 100.0: the Versatility winner flips from p0 to p1.
  - The mechanism is general: dropping the 0.3-weight empty rows from the denominator raises reliability toward 1.0 for any product whose remaining fields verify, so "one verified field + ten empty" scores the same reliability as a fully verified sheet; and every refilled field loses its grade (today it carries the empty value's "unverified").
  - The walk (2.5) has E, E', P, F only; P6 pins only F (real values only on both sides); R19 (D2F) checks the specs projections, not scoring. -> B2.

RC3. Spec 0 / H1-1: "... `compute_scores`, the crown inputs other than the fact-check counts, and the verdict prompt's product JSON are byte-identical with the flag ON", and the CLAUDE.md block (spec 8): "The data stage (extract_specs, `_clean_specs`, the refill cascade, `compute_scores`, the verdict prompt input) is unchanged." REFUTED on two counts:
  - The verdict user message dumps each product dict with its reviews (ES:2674-2681); `_verdict_safe_product` strips only `fact_check` and `_`-prefixed keys (ES:2522-2526). Under S15 the reply carries `has_review_data` (`_normalize_review_response` keeps unknown keys, ES:1923-1976) and, for a no-data answer, the twin-instructed consensus "" / highlights [] - so the verdict prompt's product JSON changes with the flag ON for every fresh extraction. The verdict call also receives `scores_summary` built from scoring_result (SCS:4676, call SCS:4700-4704), which loses the reliability-derived dim whenever S1 moves it.
  - `compute_scores` reads `fact_check` for its reliability signal (SS:1830-1839); S1 changes that input for every product with an empty field (RC2). The code is unedited, its output is not unchanged.

RC4. Spec 1.5 (last paragraph) and 2.6 row 2: "For a short dict (some real keys), the rich path is used today and with the flag: the same rows and the same count (the NA keys never entered the rich set), so the visible table is unchanged." REFUTED for three members of the H1 token set. The client NA set is {'n/a','na','null','none','unknown',''} (RA:87 OTA, RA:82 store); "-", the em dash and "... or null" are RICH on both bundles today (filterSpecs RA:89-107). "-" and the em dash survive extract_specs (only None / "" / "null" / "or null" are stamped, ES:1686-1691; `str(val)` ES:1712) and `_clean_specs` (SCS:3551). Under H1:
  - a key whose only values are "-" leaves the rich set: the header count drops by one and its row ("-" vs "-", drawn today) disappears;
  - a "-" vs real row, drawn today with two values and the server winner on the populated side (`_spec_row_winner`, RB:690-695), becomes a one-dash row the client drops (RA:597-598) while the header still counts the key (count taken before the filter, RA:288-297);
  - an em dash value is counted as a dash by the row filter (RA:597 compares to the em dash placeholder) but is rich in the key set, so "em dash vs em dash" rows survive today on the RICH path and vanish under H1.
  The spec's own fixture SPEC_T04 (eval_regression finding 9, the recorded V10 all-dash dict {"connectivity": "-", ...}) is exactly this class; R19 (D2F, "N/A" only) cannot see it. The change is in the honest direction, but the stated "visible table is unchanged" and the 8b pair-2 wording ("the same rows a pre-flip run of the pair showed ... the rich key count unchanged") are wrong for a sheet carrying "-".

RC5. Spec 2.8: "With the flag ON, a product whose spec values are all real and whose reviews are data is byte-identical to OFF (P3)." REFUTED for production replies. S15 asks the model for `has_review_data`; a data reply then carries `has_review_data: true`, which ships in the `products[i].reviews` alias (RB:2247-2249), is persisted in the saved row and in L1 / L2 (W5 writes data dicts), and reaches the verdict prompt (RC3). P3's REV_DATA has no such key, so P3 pins a shape the honest twin will not produce. The spec's own section 2 ("One additive key: has_review_data ...") contradicts 2.8.

RC6. Spec 1.7 / 2.5: "Reachable mixes: W in {0, 1} with W = 1 implying C = 1 ... 12 mixes." REFUTED against the documented hard order the spec itself tabulates. SS:1044-1055: W flips only after C, then ENABLE_FACTCHECK_SHOPPING_KEY immediately before ENABLE_FACTCHECK_CURRENCY_NORMALIZATION, and ENABLE_CITATION_RUBRIC_V2 (#108) "must be canaried before this flag". So W=1 implies C=1, SK=1, #106=1, #108=1. #108 replaces the grading branch of verify_spec_citations (FC:231-233, `_grade_citation_v2`), which changes the P cells (snippet-sourced real values). R22's W1 cells (C only) walk an unreachable state and miss the reachable one; the reachable intermediate states C1/W0 and #108-on/W0 (C is "first of W's chain", #108 is canaried before W) are not walked.

RC7. Spec 9 L-CROWN: "the incident shape 40 vs 30 -> both MISSING removes 1.5 overall points from p0. No other scoring input moves." REFUTED twice:
  - With R OFF the overall is the legacy sum in which MISSING_SCORE 50 contributes (SS:297; the renormalisation exists only under R, SS:1436-1470): p0 GAINS 0.15 x 10 = 1.5 and p1 GAINS 0.15 x 20 = 3.0; it is p0's 1.5-point edge that disappears.
  - The reliability input moves in every category, not only for fragrance versatility: `_DIMENSION_SIGNAL_MAP` (SS:2144-2190) maps one dim per category to "reliability": electronics build_quality (weight 0.15), grocery ingredient (0.20), supplements safety (0.25), makeup skin_compat (0.20), skincare evidence (0.20), haircare ingredient (0.15), fragrances versatility (0.15), fashion durability (0.15), other build (0.15) (weights SS:65-75). ENABLE_FRAGRANCE_ONLY_GATE was not flipped (record ledger 2026-11-07 09:05 "NOT FLIPPED"; H12(c) "believed OFF"), so production serves all nine.

RC8. Spec 8b: "a consent-below-3 account gets no reviews text at all because the OpenAI egress stop refuses the call; both satisfy the checks". REFUTED as evidence. On such an account with no cached entry the egress stop (OpenAIEgressStoppedError, an LLMUnavailableError, api_budget_service.py:735) turns the specs extract into `{"brand", "model", "error"}` (ES:1742-1747), which `_clean_specs` empties (SCS:3524), and the reviews extract into `{"average_rating": None, "error": ...}` (ES:1915-1920): no dash rows, no praise and a Low chip appear EVEN WITH THE FLAG OFF, so the Specs-row, Specs-chip and Reviews checks of proof 1 pass vacuously. The [HONEST_EMPTY] line cannot tell them apart either: reviews=no_data for an error dict (2.2 log_product) and specs_dropped=0 for an error or a timeout.

RC9. Spec 1.9: "gitleaks names (H7): no new constant name with a scanner keyword (HONEST_NA_TOKENS, ... are clean)" and the header rule "no constant whose name contains ... key ... token". REFUTED: HONEST_NA_TOKENS contains "TOKEN"; SPEC_META_KEYS and REVIEW_TEXT_LIST_KEYS (2.1) contain "KEY". The values are short, low-entropy strings, so the practical scanner risk is small, but the claim is false and the names break the spec's own rule (the pre-commit dotenv-name class keys on *KEY* / *TOKEN*, .githooks/pre-commit:407).

RC10. Spec 2.3 S4: "the two `(pd.get("reviews") or {})` reads (SCS:5482, SCS:5489) read `_honest_empty.wire_reviews(pd.get("reviews"))` once per product". Taken literally this drops the `or {}` coalesce. wire_reviews OFF returns its input, and a timed-out reviews race leaves `pd["reviews"]` None (SCS:6312 / SCS:6317 via `_price_fallback_on_miss`, SCS:6984-6993), so the OFF stream would raise AttributeError on `None.get(...)` - the PYTHON-FASTAPI-J class the comment at SCS:5480-5481 and tests/test_response_builder_phase1_none_guard.py guard. The correct form is `(_honest_empty.wire_reviews(pd.get("reviews")) or {})`; "once per product" inside the comprehension needs a stated form (a precomputed per-product list).

RC11. Spec 2.3 S19: "at the top of each iteration ... rebind `pd["specs"]` to `_h1_views[i][0]`". The alias loop is `for pd in product_data:` (RB:2227) with no index; S19 must edit the loop header (enumerate or zip), an edit of an existing line the change list does not name.

RC12. Spec 9 L-ONESIDE frames the one-side row as a limit that "stays". Measured from the spec's own walk (2.5 row P): H1 turns 55.5 vs 30.0 (two computed numbers) into 100.0 vs 50 (one real side against the MISSING_SCORE default), and the line1 margin grows from 25.5 to 50 (`_top_dim_candidate` ignores was_missing, RB:931-942). So H1 makes the one-side bar and its "leads on Versatility" headline MORE confident than today, in the shape INC-R1 will create (one side resolved, one side empty). This is an H1-introduced regression stated as an unchanged limit (see M4).

## 3. Blocking issues

B1 (RC1). R12 asserts "has_review_data" exactly once per twin; the S14 lines put it in each twin twice (measured). The frozen RED row cannot pass at GREEN without a pin-fix of a frozen file. Fix before RED: R12 asserts `twin.count("has_review_data") == 2` and, separately, `twin.count(_H1_SHAPE_LINE) == 1` and `twin.count(_H1_RULE_LINE) == 1`.

B2 (RC2, RC7). The S1 skip is a scoring change for real data in all nine categories, and the spec states, walks and pins only the all-empty and real-only shapes. Before RED:
  (a) state it as a limit (L-DENOMINATOR: reliability counts only the extract-time real fields; a refilled field has no grade; a product with few verified fields and many empty ones reaches 1.0; ties at 1.0 collapse to MISSING under T OFF), with the D2F numbers;
  (b) add a RED row R25 over D2F at the scoring grain (the real ScoringService): OFF 79.0 / 68.0 versatility; ON no versatility dim (T0) and both fact_check counters reduced to the extract-time real grades (p0 5/1/0/0, p1 4/0/0/0);
  (c) add one non-fragrance walk case (an electronics pair with N/A fields: Build quality moves);
  (d) carry a MEASURED before/after (H6 c; D2 F4 "flag it and run the S81-07-style comparison"; ADV C-2 "run the flag-mix walk before choosing"): the cheapest hermetic form is a scoring-grain replay of the recorded bodies under tests/fixtures (the comparison_baseline_* files, tests/fixtures/w412_corpus_min.json, the golden fixtures) with H OFF vs ON, reporting per category the reliability-dim deltas, the dims that vanish, crown flips and chip changes - a hermetic measurement, never the production proof;
  (e) put the design choice to the orchestrator (Q1): accept the denominator effect, or narrow S1.

B3 (new). An extraction ERROR keeps feeding the reliability proxy under H1. verify_spec_citations skips only brand / model / variant / category (FC:213-215); the error dict `{"brand", "model", "error"}` (ES:1742-1747) is graded through its `error` key: no `error_source` -> "unverified" (FC:219-220) -> specs_unverified = 1 (FC:568) -> `_score_reliability` total 1 -> 0.3, +0.1 with a verified price (SS:2081-2104) -> versatility 30.0 / 40.0 -> a Versatility bar with "medium" (SS:3585) and "<A> leads on Versatility." (RB:1097) whenever exactly one product has a verified price. Today that is the path of EVERY request below consent 3 with no cached sheet (H12 c: such a request routes to OpenAI, where the egress stop fails the call locally; RC8); the share of such requests is not measured here. S1 skips only `spec_value_is_empty(value)`; the error message is a non-empty string, so H1 leaves this "built from nothing" headline in place. Fix (inside H1's scope, under the flag): S1 skips every key that is not a spec field - `if _h1 and (not _honest_empty.spec_field_key(key) or _honest_empty.spec_value_is_empty(value)): continue` (spec_field_key already excludes "error", 2.2). Add R7b (ON: verify_spec_citations of an error dict == {}; OFF == {"error": "unverified"}), extend R10 with an error-dict pair (OFF versatility 40 vs 30, ON no dim), add the mutant "S1 skips empties but not `error`" (killed by R7b), and add the error-dict case to 2.4, 2.5, 2.7 and 8b.

## 4. Corrections (MAJOR first; the minor ones are stated limits by default under LC-4 unless the orchestrator rules a fix)

M1 (RC3). Rewrite section 0 "What H1 does NOT move" and the CLAUDE.md block's last sentence: the specs data stage (extract_specs, `_clean_specs`, the refill triggers) is unchanged; `compute_scores`' reliability input (the fact-check counters) changes; the verdict prompt's product JSON gains `has_review_data` and the twin-shaped reviews; its scores summary follows the scoring. Replace L-PROSE (the consensus the verdict sees is the twin's, often "" for no data) and add L-VERDICT-INPUT. Ask Q8 whether `has_review_data` should be stripped from the verdict payload (one key in `_verdict_safe_product`, an ES edit).

M2 (RC4). Restate 1.5 / 2.6 row 2: the visible table is unchanged only when every non-real token is in the client NA set; a "-" / em dash / "or null" value leaves the table (row gone; count down by one, or the count kept with one fewer row drawn). Add a RED row (a T04-like pair through the RA:86-107 + RA:198-223 + RA:575-599 re-implementation: OFF rows and count, ON rows and count). Fix the 8b pair-2 wording to "every row whose two values are real (not in the H1 token set) is still shown with the same values".

M3 (phrase guard; Q2). Three risks of false EMPTY on real review data, none measured on Claude output:
  (a) R5 makes the phrase guard override `has_review_data: true` ("True: ... has_review_data True + no highlights + a phrase"): the model's explicit signal should win;
  (b) "provided search results" is a common model preamble ("Based on the provided search results, ...") rather than a no-data statement; it should fire only with a negation or only when `has_review_data` is absent;
  (c) the rule line's "(the same brand, line and concentration)" is a variant filter (RC10 / F10, out of scope per section 10), and `has_review_data` false blanks even CITED highlights (REV_FALSE, R11), so a reply that sees EDT reviews for an EDP request blanks real praise.
  Measured: the 160 recorded consensus texts in tests/fixtures and data (192 JSON files, probes/probe_consensus.out) contain 0 hits for any guard phrase and 0 mentions of "search results" - so no false positive on OpenAI-era text, and no Claude sample exists to measure. The 8b proof pair 2 checks only Specs, so a reviews regression would go unseen: add "the Reviews section shows the same praise or stars a pre-flip run showed" to pair 2, and a PIN row: has_review_data true + no positive highlight + a consensus "Based on the provided search results, ..." -> praise == the OFF praise.

M4 (RC12 / B-order; Q4). State that H1 enlarges the one-side bar (55.5 / 30 -> 100 / 50) and its headline margin (25.5 -> 50), and rule the flip order: H1 with or after INC-X6, or accept the worsened L-ONESIDE in writing. O12 ("independent of INC-X6") is not true once INC-R1 resolves one side of a pair.

M5 (cache cost; Q3). Two unstated costs of S8 / S9 / S12 / S13 under the flag, in production with ENABLE_SYNC_DB_OFFLOAD OFF (record ledger line 316: not in the ON list):
  (a) a pre-flip empty L2 entry is never promoted, so after its 7 d L1 copy lapses EVERY request for that key runs `get_cached_specs` / `get_cached_reviews` through `run_db`, which is INLINE on the event loop with the flag OFF (app/utils/db_offload.py run_db; PDS:207-213, PDS:371-377): one loop-blocking Supabase round trip per product per request until the L2 entry expires (specs up to 30 d, reviews 14 d);
  (b) an always-empty product (an unresolvable identity) is never cached, so every request re-runs the specs and reviews LLM calls (spend-breaker counted) plus two L2 misses per product.
  State both (L-RECOMPUTE, and the cost in L-OLDCACHE) and rule the alternatives: promote empty L2 entries as today, promote with a short TTL, or a short L1 negative cache for empty answers.

M6 (RC8; owner proof standard H6). Rewrite 8b so a vacuous pass is impossible:
  (a) proof 1 counts only when the [HONEST_EMPTY] line shows specs_dropped > 0 for the product (the view acted) and the saved row's `products[i].reviews` has a `review_summary` and no `error` key (a model answer, not the egress-stop error dict);
  (b) name the account: consent 3 for a fresh answer, any account while entries written by the 2026-11-13 run are still cached, IF that run wrote them (a fresh all-null reply is written; a timeout is not, ADV R-4): L1 7 d, L2 reviews 14 d, L2 specs 30 d from that write - `cached=yes` then proves the views on a cached sheet, not the twin;
  (c) after the B3 correction, add to pair 1 on a below-3 account: no Versatility bar and no "leads on Versatility" from the error dicts.

M7 (RC6). Recompute the W1 cells with C, SK, #106 and #108 ON (the documented chain) and add the reachable W0 states C1 and C1 + #108; under #108 the P cells use `_grade_citation_v2` (FC:158-201), not the legacy rubric. R22's parameter list follows.

M8 (prompt-capture seam). 2.9 names `extraction_service.get_client` as the seam; under FULL_CONFIG / PROD_SET (ENABLE_ANTHROPIC_TEXT + ENABLE_OPENAI_PRE_V3 + ENABLE_OPENAI_EGRESS_STOP ON) route("reviews") never reaches that client: consent below 3 -> `guarded_llm_create` raises the egress stop before `create`; consent 3 -> the Claude adapter (llm_router.py:1090-1104, `to_claude_request` llm_router.py:716-751). P1's "extract_reviews sends REVIEWS_EXTRACTION_SYSTEM (`is`)" and P4 (FULL_CONFIG) would then capture nothing (red at base) and "S15 not gated" would survive. Capture the `messages` kwarg at `extraction_service._llm_router.route` (or run the capture rows with the three router names unset and say so).

M9 (RC5). Change 2.8's P3 sentence to "byte-identical except the additive `has_review_data` the honest twin asks for", and give P3 a REV_DATA variant carrying `has_review_data: true` (ON body == OFF body + that key in `products[i].reviews` only).

M10 (RED / mutation completeness; R-A13 B1 rule). Add these mutants and their killers:
  - S8 inverted (`not` lost: OFF never promotes a specs L2 hit): no existing pin covers the specs L2 promotion OFF (tests stub get_cached_specs -> None: test_spec_confidence_cache.py:69-83, test_s75_fanout_starve.py:1417); give R14's L2-hit case an explicit OFF precondition (1 promotion write).
  - S6 inverted (OFF never writes the enriched copy): killed by the existing tests/test_s75_fanout_starve.py test_FY19_honest_serper_failure_payload_still_caches (`len(specs_l1) == 2`, :1497); name it. Add a behavioural ON row for W3 on the same harness (`_d5_cache_mocks` with tier2 returning {"concentration": "unknown"} over an all-"N/A" extract: ON no specs write; OFF two) - today M37 is killed by an AST row only.
  - S12 inverted: killed by tests/test_s77_redis_offloop.py test_s6_reviews_l2_promotion_set_stays_inline (:1160-1196); name it. S13 inverted: R13's OFF precondition.
  - skip_reviews_cache not gated, wire_reviews / S4 not gated, wire_views not gated, consensus_blocked (S11) not gated: list each; P1's stream fixture must hold a no-data product (REV_NODATA on product 1, as R20) or S4-not-gated survives.
  - S15 not gated: killed by P4 only once M8 is corrected.
  - review_no_data with `== False` instead of `is False`: R5 must include has_review_data 0 and "" (with highlights) -> False.
  - the log at WARNING instead of INFO: R15 asserts `levelno == logging.INFO`.
  - S19 adding a key: a row with a product lacking "reviews" / "specs" -> no key added in the alias ON.
  - B3's mutant (S1 skips empties but grades `error`): R7b.

M11 (RC10, RC11). Fix the S4 text to `(_honest_empty.wire_reviews(pd.get("reviews")) or {})` with a stated once-per-product form, and the S19 text to name the loop-header edit at RB:2227.

Minor (stated limits by default):
- m1 (RC9). Rename HONEST_NA_TOKENS -> HONEST_NA_WORDS, SPEC_META_KEYS -> SPEC_META_FIELDS, REVIEW_TEXT_LIST_KEYS -> REVIEW_TEXT_LISTS (and in 2.9, R2, R5, R6); keep the digest-constant names keyword-free.
- m2 (rollback). L-ROLLBACK: dicts cached while ON keep `has_review_data` and the honest consensus for up to 7 d (L1) / 14 d (L2), and with C ON the #107 maps cached under ON lack the empty keys (S1 runs at SCS:6898-6910 too): flag-OFF byte identity after a rollback holds for new extractions only. The reviews cache key has no prompt-variant axis (the D08 precedent).
- m3. 2.4 omits `metadata.fact_check.product_i` counters and `metadata.data_freshness_shaky` (SCS:544-570, is_data_freshness_shaky FC:588-608), and `overview.confidence.overall` (the strong count, SS:1216-1223); no bundle reads them; list them.
- m4. Post-RB readers of the S19-mutated product_data are not listed: `_kb_ingest_tail` (kb_ingest.build_job: D05 field_status and the KB card, SCS:3953-3991), compare_runs, and a hard-cap partial built from `_partial_product_data` after a completed build (SCS:3843; its captions would read the views). All OFF or rare in production; list them beside R23's interplay.
- m5. P1's digests use canonical JSON with sort_keys (the FY25 practice, tests/test_s75_fanout_identity.py:266-268): key order is not pinned. Add one order-preserving digest of the E-pair body (json.dumps without sort_keys).
- m6. The twin keeps the "2-3 sentence" consensus rule (ES:983-1000) beside the new 'consensus is ""' rule; the conditional rule follows the general one. State it under L-PHRASE (probabilistic; the guard is the belt).
- m7. P5 kills no listed mutant (H1 does not edit `_clean_specs`); keep it as documentation or drop it.
- m8. R17 must deep-copy product_data between its OFF and ON builds (the alias loop mutates pd, RB:2227-2266, and S19 rebinds).
- m9. The RED files reset llm_router's process state in the autouse fixture (`_reset_router_state`, the S81-04c pattern) when a row runs a router name ON, and restore `scoring_service._BUNDLE_C_SCORING_FLAG` by monkeypatch (the CI single-process order).
- m10. Fixture P: state p0's `price_verified` (the 0.5545 / 55.5 cell implies False; E's p0 is True).

## 5. Contract risks

- No key is removed, renamed or retyped; the leg words stay in strong / acceptable / weak (contract_freeze.json:542 RULE 2); `review_praise` null is tolerated (RA:413-421 / store RA:371-379; contract_freeze.json:435: the alias praise is not rendered when overview exists); `specs.products[i].specs` {} is truthy in JS (the bare header, L-HEADER). Confirmed.
- Additive `has_review_data` in `products[i].reviews`, the saved row, the cache and the verdict prompt JSON (RC3, RC5). Not read by either bundle (`git grep` of 731bcddf and 683f56c0 under SmartCompareApp/src: 0 hits).
- No envelope, no code, no 503, no refusal: H1 raises nothing. With ENABLE_RESULT_GATE ON (OFF on web) more INSUFFICIENT_DATA refusals can occur; that path is S81-20's (renderable code, refund) - L-RG stands.
- Billing (R-A3): no abstain, no consume, no lifetime bump, no history-row change. The LLM spend rises for always-empty products (M5 b), on the spend breaker, not on user credits.
- Camera: no envelope change; camera compares get the views through the same orchestrator and RB.
- Error-handler code mapping, cache-key axes: not touched by H1 (no new key; the existing reviews key has no prompt-variant axis: m2).
- Client: no client file; store and OTA results files are identical for every reader H1 feeds (ConfidencePills unchanged since 683f56c0; `git diff --stat f1e20c39 731bcddf -- SmartCompareApp/src/` touches only the consent / legal files). The visible deltas are RC4 (a "-" row leaves), the chip (Low), the removed bar (RC2, B3), the praise line.

## 6. Pin collisions (section 4.1 "None" re-checked)

None with the flag OFF; no E-row is needed. Checked and safe:
- D08 P7 (:1147-1158) and R18 (:836-850): the base constants are not edited; R18 runs with ENABLE_HONEST_EMPTY unset.
- tests/test_prompt_fence.py:272-287 (guard loop over base + NO_RATING only; the twins are unchecked unless O4's E-row is taken - recommended, Q6) and :325-332 (the fake-client digest-wrap rows run with the router names unset).
- tests/test_prompt_injection.py:113-117; no `{brand}` / `{name}` in the twins (measured).
- tests/test_s81_st1_usage_path_offloop.py:1996-2018: counts direct `set_cached` calls by name (4 at base); S12 wraps one, adds none.
- tests/test_s77_redis_offloop.py:1160-1196: no suspension between `get_cached_reviews` and the promotion SET; S12's predicate is synchronous.
- tests/test_s81_s04c_refusal_log_hygiene.py: P3 records `any_role_enabled` reads only; H1 adds none and keeps off ES:1742-1747 / ES:1915-1920.
- tests/test_comparison_response_image_url.py:335-352: an 800-character window after `yield ("specs"` must contain the image_url line; measured offset end 334 today, 360 after S3 (+26 chars). Name it in 4.2.
- tests/test_wall_caps_i57.py:120-131 (getsource of extract_reviews: required / forbidden substrings): S15 adds none of them. Name it in 4.2.
- The getenv recorders (tests/test_s81_s05_request_context.py:604-610, test_s81_s09_device_quota.py:1979-1990) assert absences only; a new ENABLE_HONEST_EMPTY read does not trip them.
- tests/test_hermeticity_pins.py tests/ walkers (:1497-1509, :1574-1585, tiktoken loaders): the RED files must not call tiktoken loaders.
- FY25 digests (tests/test_s75_fanout_identity.py:266-286), the W4-13 flag-OFF ledger fixture, the T23 OpenAPI fixture (no route or model change), test_retro_w2_1 URL pins (untouched path), the copy-policy fences (no client copy): flag OFF unchanged.
- tests/test_s81_s08b_legacy_fingerprint.py:820-822: exactly one `**Feature Flags:**` line (CLAUDE.md:341, measured once); the pointer anchor text "...(S81-07c CLAUDE-ROLE-FIX, ...)** block. `REAL_ACTION_MIN_SECONDS` (5)." exists; `## Tests` at CLAUDE.md:684; the S81-07c block at :675-682. Confirmed.
- If S4 lost its `or {}` (RC10) the stream None rows would go red: a defect, not an E-row.

## 7. Comm set and gates

- The comm set (743 of 783 test files, sha256 6d73dae4... of the sorted list, re-hashed) is adequate: the 40 exclusions were re-derived (all minus the set) and each read: the four pre-commit hook files, tests/test_integration.py, and 35 files that import or read no closure module, CLAUDE.md or app path (prompt_personalities, sentry_service, yotpo_service, verdict_builder, confidence_service, quality_ranker, attribution_service, data/ and migrations/ readers). Every named source-scanning pin and every CLAUDE.md reader by the import graph is IN the set; the two hand additions are in.
- The deferred commands match gate.py's usage line (`--bound S --tag inc-... --log FILE --cwd WORKTREE -- <pytest args>`; `--wait-only` before jest).
- Add to G4 / G5: tests/test_comparison_response_image_url.py, tests/test_wall_caps_i57.py, tests/test_response_builder_phase1_none_guard.py, tests/test_s75_fanout_starve.py (FY19 rows) - all in the set already; they are the cheap first look for S3 / S4 / S6.
- G9: the RED files touch process state only through monkeypatch; a CI-order run (the RED files then the later alphabetical readers of `_BUNDLE_C_SCORING_FLAG` and the router state) is cheap insurance at the final round.

## 8. Questions for the orchestrator

Q1 (B2). Accept the reliability denominator effect of S1 for real pairs in all nine categories (state L-DENOMINATOR, add the D2F row and a measured fixture replay), or narrow S1: skip empty values only in the specs-leg citation count (`_product_fact_check_pcts`) and keep them in the reliability denominator; or skip empties only when the product has no real field; or move the reliability side to INC-X6?
Q2 (M3). Should `review_no_data` yield to `has_review_data is True`; should "provided search results" fire only with a negation (or only when the key is absent); should the rule line drop "(the same brand, line and concentration)"?
Q3 (M5). For pre-flip empty L2 entries: no promotion (a loop-blocking L2 read per request with ENABLE_SYNC_DB_OFFLOAD OFF), promotion as today, or promotion with a short TTL; and may an empty answer get a short L1 negative cache to avoid re-running two LLM calls per product per request?
Q4 (M4). Flip H1 only with or after INC-X6 (the one-side bar is enlarged by H1), or accept the worsened L-ONESIDE?
Q5 (B3). Confirm that skipping the `error` key in S1 (spec_field_key) is inside H1-4 ("a product with no real spec fields has a reliability total of 0").
Q6. Take O4's E-row (the twins join tests/test_prompt_fence.py's guard loop, the D08 E2 precedent)? The reviewer recommends yes. O5 (black allowlist) is fine either way.
Q7. DEFECT_LEDGER_INCIDENT.md (record copy) has no INC-H1 row; file it before RED (R-A13: the ledger is the index).
Q8 (M1). Strip `has_review_data` from the verdict payload in `_verdict_safe_product`, or accept the verdict-prompt input change as a stated limit?

## 9. Deferred runs (DEFERRED TO RED; none ran here)

The spec's commands stand (1.10 commands 1-4, the section 5 runner line, the section 7 gates G1-G9), with <P> = PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe, <G> = <SP>/harness/gate.py, <W> = C:/Users/SynAckITPC/Documents/AI/sc-inc-h1, <N> = <SP>/INC-H1/red:
- `<P> <G> --bound 1200 --tag inc-h1-base-touch1 --log <N>/base-touch1.log --cwd <W> -- <the 22 files of 1.10 command 1>` (DEFERRED TO RED)
- `<P> <G> --bound 1200 --tag inc-h1-base-touch2 --log <N>/base-touch2.log --cwd <W> -- <the 17 files of 1.10 command 1, second call>` (DEFERRED TO RED)
- `<P> <G> --bound 600 --tag inc-h1-base-prompt --log <N>/base-prompt.log --cwd <W> -- tests/test_prompt_fence.py tests/test_prompt_injection.py tests/test_prompt_truth.py tests/test_model_config.py tests/test_model_config_enforced.py tests/test_s81_s04c_refusal_log_hygiene.py tests/test_hermeticity_pins.py` (DEFERRED TO RED)
- the comm-set base record, 30 chunks, tags inc-h1-base-c01..c30, bound 1200 (DEFERRED TO RED, LC-6)
- `<P> <G> --bound 600 --tag inc-h1-red --log <N>/red.log --cwd <W> -- tests/test_inc_h1_honest_empty.py tests/test_inc_h1_body_pins.py` (DEFERRED TO RED)
- the fourteen client fences by path after `<P> <G> --wait-only` (DEFERRED TO RED / GREEN)

## 10. Confirmed (re-measured, no change needed)

ES:213-227 (11 fields), ES:1584-1747 (stamp ES:1706-1707, `str(val)` ES:1712, sources ES:1714-1721), ES:978-1028 / ES:1031-1044 / ES:1886-1890 / ES:1915-1920 / ES:1923-1976; SCS:368-384, SCS:440-460, SCS:3520-3572, SCS:5403-5414, SCS:5466-5497, SCS:6301-6319, SCS:6431-6458, SCS:6541-6687, SCS:6829, SCS:6831-6926, SCS:1709; FC:204-263, FC:555-585; SS:1032-1070, SS:1089-1115, SS:1150-1253, SS:1830-1839, SS:2071-2106, SS:2175-2179, SS:2236-2275, SS:2553-2558, SS:3240-3420 (the three core dims always emit a neutral score, so `length >= 3` holds), SS:3503-3589, SS:3848-3935; RB:84-96, RB:635, RB:673-711, RB:735-772, RB:918-952, RB:1090-1100, RB:1134-1181, RB:1927-2085, RB:2227-2268, RB:2308-2335; RV:547-646, RV:722-851, RV:45; PDS:18-20, PDS:200-248, PDS:367-409; RG:63, RG:245-250, RG:432-445; the client rows of 1.5 in both bundles; the router reviews site has no output schema (llm_router.py:215), so Claude can return the new key; the production state of W / U / R / N / C / T (record ledger line 316 and H12(c): unset); the 0-hit names (ENABLE_HONEST_EMPTY, honest_empty, has_review_data, "not specified").

## Not done in this review

- No pytest, jest, tsc or eslint; no base pass state; no mutant run.
- No production read: the share of requests below consent 3, the cached state of the 2026-11-13 keys, and any Claude reviews sample are unmeasured here.
- The D2F and walk numbers are formula reproductions on committed fixtures (they match the fixture's own breakdown); the RED round confirms them on the real ScoringService. Nothing here is a production proof.

# FABLE REVIEW RULINGS W4-6a (binding, 2026-09-26, session 68) - these OVERRIDE the spec body and the adversarial review where they differ

Verdict on the spec + review: APPROVED WITH THE CORRECTIONS BELOW. Base stays 61585c58 (re-anchor by symbol at red time; main has since gained #202, which touches auth_service only).

R1 (V rule) - ADOPT correction C1: ENABLE_VALUE_DIM_PARTIAL_SIGNAL un-stamps the value dimension ONLY when every product in the pair has a price AND `_spec_missing` is equal across the pair (the same formula on both sides). The spec's per-product rule is REJECTED (it crowned the no-data product on `value` in 24 grid rows - the #101 inversion in the text layer). Test 7 flips (price-only vs measured partner, spec-only with no price: both STAY stamped); test 8's expected set = the 3 remaining rows (fashion/other one_missing_price, supplements both_no_price), listed in section 10 as W4-6b's.

R2 (T on presence-credit categories) - ADOPT correction C2: `_spec_sparse` returns True for any category whose HIGHER_IS_BETTER and LOWER_IS_BETTER sets are both empty (fashion, other), so T never un-collapses a 1.0 == 1.0 presence-credit tie. Test 17's craft/function half becomes a PIN that they stay stamped; add the mutation.

R3 (G, PO-RUBRIC-08) - G does NOT ship unflagged and never ships without G'. G + G' (skip any dimension the winner leads by more than 5) + the zero-margin rule (a `loser_wins` pair with margin < 1.0 is dropped - no "stays competitive" copy on a tie margin; this folds PO-RUBRIC-08b in, since its reach grows with the flags) ALL ride ENABLE_TIE_IS_NOT_MISSING. Flag OFF: today's `_loser_strongest_dim` byte-for-byte. Pins: no pair with `loser_wins.dimension == winner_wins.dimension` under T (M16); R08d/R08e produce no false "competitive on <dim>" claim under T; test 20 pins the corrected target, never "stays competitive on performance" at 45 vs 85.

R4 (red claim (c), craft tie) - ACCEPT the reframing: not closable by these flags. Keep the not-missing test plus an `xfail(strict=True)` pin of the limit with the PO id in its reason. Do NOT change fashion/other spec weights. Follow-up row W4-6c (a non-numeric merit discriminator: material / construction / origin tier table) goes to DECISIONS for Ahmed.

R5 (T coupling) - ACCEPTED: `_tie_is_not_missing_enabled()` returns False whenever ENABLE_MISSING_DIM_RENORM is ON (uncoupled it flips 8/9 unrated_vs_2star rows and reddens 6 renorm pins). Pinned both ways.

R6 (T sparsity thresholds) - ACCEPTED as measured: fact_check bucket total < 3; review_count > 0; spec coverage < CATEGORY_MIN_COVERAGE.

R7 (T moves scores) - the design is CORRECT (a measured tie is a measurement; a presence-credit tie is not, hence R2) but the FLIP is Ahmed's: pr_text states the measured movement after R2 (54/144 grid rows overall, 11 margins, 6 badges - 54 with ENABLE_CATEGORY_VALUE_BADGE ON - R02 display 78 -> 84, 0 record winner flips) and marks the activation as a product sign-off. Section 9 gains the ENABLE_CATEGORY_VALUE_BADGE interaction and the cpw-row qualifier (the fashion cpw row appears under V alone; under V+T the 8-row cap fills first).

R8 - the review's `partial_dims` additive key stays OUT (no reader on the phones).

R9 - ONE PR, both flags.

R10 (test/gate corrections, all ADOPTED) - test 13 reclassified RED with the exact T-ON missing_data lists (C4); 0.7/0.3 wording everywhere (C5); M1 row without test 17, plus M17 = a caplog pin that no `W4-6a` log line is emitted with the flags OFF (C6); E2 gets a committed generator `tests/fixtures/_gen_rubric_truth_flag_off_digests.py` (lazy app.* import, run only through a pytest probe) and the fixture header states the `_grid()` dependency on CATEGORY_SPEC_SCHEMAS (C7); the comm gate names its worktree and runs base and head in the SAME worktree (C8).

R11 (consumers the spec missed - MEASURE in red, PIN or STATE) - (a) `trust_validation_service.validate_verdict` reads the breakdown with `== MISSING_SCORE`; under T the un-collapsed values count as claims (`claims_softened` / `claims_flagged`, `confidence_adjustment` 'reduced' when flagged > 2): drive it with a stubbed GPT verdict in both flag states and PIN the shape change or state it as a canary item; (b) `home_routes.py:452-459` compares a dict to a string and can never match - record in section 3.6, do not fix here (W4-12c owns priority_match); (c) under renorm+V, `excluded_dims` (legacy flags) and `missing_data` (V-filtered) can disagree - state the shape (85 records, not new); (d) G does not cover a margin computed against the WINNER's sentinel - record, low severity.

R12 (gates) - E1 four goldens byte-unchanged; E2 base->head->base2 record-by-record over the 164 records x 3 states; E3 flag-ON golden; E4 V-neutrality + T-under-renorm identity; E5 G rows; the 241-file comm set at base and head in the same worktree with the guard, deselects, `comm -13` empty against `tests/.pre_impl_failures.txt` plus the guard-caused SSRF nodes (list them); CI-order set = the spec's list re-derived by grep for `scoring_service|ScoringService|compute_scores|build_scores_summary|compute_dimension_winners|compute_tradeoff_pairs|_loser_strongest_dim|build_dimensions_v2|count_missing_dim_cells|deterministic_verdict_fields` plus every file that pins `trust_validation_service.validate_verdict`; ruff + py_compile; the corpus harness is BLIND to this unit (state it).

R13 (files) - `app/services/scoring_service.py` only under app/ (G lives in `_loser_strongest_dim`); tests: the new `tests/test_scoring_rubric_truth.py`, the E2/E3 fixtures + generators, no edit to any golden. A change anywhere else under app/ = STOP and report.

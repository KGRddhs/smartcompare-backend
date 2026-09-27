## W4-6a: rubric truth (stop reporting measured data as missing)

Findings PO-RUBRIC-01, PO-RUBRIC-02 and PO-RUBRIC-03 (P1), plus PO-RUBRIC-08 (P2). The PO-RUBRIC-08b "stays competitive" copy is folded in.

The work follows the spec `.qa-s68/specs/W4_6A_UNIT_SPEC.md` and its adversarial review (C1-C8), under these rulings:
- Fable review rulings R1-R13;
- red-gate rulings R14-R20;
- fix-round rulings R21-R22;
- fix-round-2 ruling R23.

This is **one PR with two flags. Both default OFF and both are read per call.** Only `app/services/scoring_service.py` changes under `app/` (R13).

### Defects (measured at base 61585c58 == 04acb757 for every touched file)

**PO-RUBRIC-01.** The dimension that decides the winner is stamped missing and resolves `N/A`.
- On R01 (identical specs, 50.0 vs 52.0 BHD) the score is 72.0 vs 58.0. The whole 14.0-point margin sits on `value_score` (100 vs 30).
- That dim is in both `missing_data` lists and resolves `N/A`.
- The gpt-4o verdict prompt reads "clear lead" next to `value=N/A`.

**PO-RUBRIC-02.** The B0-A array tie-collapse turns equal *measured* signal into "missing".
- On R02 (two fully verified identical phones), 4 of 6 dims are stamped, the overall is 67.0, and the phone shows 5 v2 rows.
- Near ties collapse the same way: battery 4100 vs 4000 mAh, and saturated popularity (1500 vs 2500 reviews).

**PO-RUBRIC-03.** fashion and other have no numeric spec direction, so their spec score is presence credit (1.0 == 1.0), not merit. This PR keeps it as missing (R2) and pins the limit.

**PO-RUBRIC-08.** The runner-up card names a data void as the loser's strength.
- R08d / R08e produce "stays competitive on build quality." at margin 50 / 40.0, where that dim is the loser's 50 sentinel.
- 66 of 169 probe records carry a margin-0 "stays competitive" claim.

### Design

**ENABLE_VALUE_DIM_PARTIAL_SIGNAL ("V")**
- `compute_scores` builds the legacy list exactly as today and keeps it as `legacy_missing`.
- It drops the value-signal dims from the EMITTED `missing_data` only when every product is priced AND `_spec_missing` is equal across the pair (R1 / C1: the same value formula on both sides).
- The price-authority exemption and the renorm parity tie-break read `legacy_missing`. `_signal_missing_for` is untouched, so V moves no arithmetic.
- It emits one INFO line, `[scoring] W4-6a value dim partial: dim=... products=... category=...`. The line fires only when at least one product actually had a value dim un-stamped, never merely because the like-for-like condition held (pinned, R21).

**ENABLE_TIE_IS_NOT_MISSING ("T")**
- `_tie_is_not_missing_enabled()` is False whenever ENABLE_MISSING_DIM_RENORM is ON (R5 coupling).
- Each of the three collapse blocks (reliability, popularity, spec) fires only when the tied signal is SPARSE on EVERY product. Otherwise the tie stands.
- The sparsity rules (R6) are:
  - **reliability:** fact_check is not a dict, or the FOUR spec buckets (verified + likely + flagged + unverified) sum to < 3 (`_SPARSE_FACT_CHECK_BUCKETS = 3`). Each bucket is pinned: a fact_check whose only bucket is likely, unverified or flagged is dense at 3 and sparse at 2 (R21, R23).
  - **popularity:** `int(review_count) > 0` is not true.
  - **spec:** specs is not a dict, or coverage < `CATEGORY_MIN_COVERAGE`, tested with `<` exactly as `_score_specs` does. Coverage counts the schema's SCORING fields only, with NON_SCORING_SPEC_KEYS stripped. A field counts when it is truthy and not the string "N/A" (pinned: 3 filled fragrance fields of which one is "N/A" is sparse, R23). A category with no numeric direction (fashion, other) always counts as sparse (R2).
- It emits at most one INFO line per call each for `W4-6a tie kept: signals=...` and `W4-6a tie collapsed (sparse): signals=...`.

**Tradeoff guard (R3 + R14 + R15)**
- The guard is active when `_value_dim_partial_signal_enabled() or _tie_is_not_missing_enabled()`. Under renorm the coupled T reader is False, so the guard is active iff V is ON (R17).
- In `_loser_strongest_dim`, a dim is ELIGIBLE only if all three hold:
  1. it is not in the loser's `missing_data` (G);
  2. it is numeric in the winner's breakdown (G);
  3. the loser's lead, ROUNDED to 1 decimal, is >= 1.0. That is, `round(val - winner, 1) < 1.0` is ineligible.
- The boundary for rule 3:
  - A lead of exactly 1.0 is eligible and 0.9 is not.
  - A float-noise 1.0 lead between 1-decimal values stays eligible (64.1 - 63.1 = 0.9999999999999929), and so does a raw 0.999 lead (it rounds to 1.0).
  - Each of these is pinned (R21, R23).
- Rule 3 is R15's zero-margin rule, applied as eligibility BEFORE the pick. It contains G' ("skip a dim the winner leads by > 5") as a strict subset, so G' is not a separate line.
- The pick is the loser's strongest eligible dim. If nothing is eligible there is no pair: `tradeoffs: []` and `key_tradeoff: ""`.
- The guard adds no log line.

**Flag OFF**
- Every new branch sits behind a per-call reader and is skipped.
- `legacy_missing[pk]` is the same list `result_products[pk]["missing_data"]` held before.
- No result key is added or reordered, and no new log line is emitted (caplog-pinned).

### Flag rows (for CLAUDE.md, written at merge time)

**`ENABLE_VALUE_DIM_PARTIAL_SIGNAL`** (W4-6a, PO-RUBRIC-01)
- Default OFF, read per call via `.strip().lower()` in `scoring_service._value_dim_partial_signal_enabled`.
- When ON, the value dim leaves the emitted `missing_data` for like-for-like pairs only (both priced, equal `_spec_missing`).
- It moves 0 `overall`, `win_margin`, `winner_index`, breakdowns or badges over 169 records, measured OFF->V, R->RV and T->VT.
- It ALSO turns the tradeoff guard on (R14):
  - tradeoffs change on 71 of 169 records;
  - `key_tradeoff` is empty on 146 of 169 (78 OFF);
  - void-named loser strengths drop 2 -> 0 and margin < 1.0 claims drop 66 -> 0.
- Grid rows with a `value_score` N/A: 21 -> 3.
- Counting every value-signal dim of `_DIMENSION_SIGNAL_MAP` (`value_score`, `cpw_score`, `serving_value_score`, `perf_value_score`, `results_value_score`, `multi_value_score`, `wear_value_score`), grid rows with a value-dim N/A go 72 -> 11 under V, 40 under T and 11 under VT.
- Grid rows with a > 1-point N/A contributor go 16 (OFF) -> 3 (V) -> 3 (VT).
- Flag OFF is byte-identical.

**`ENABLE_TIE_IS_NOT_MISSING`** (W4-6a, PO-RUBRIC-02/08)
- Default OFF, read per call in `scoring_service._tie_is_not_missing_enabled`. It returns False whenever `ENABLE_MISSING_DIM_RENORM` is ON, so renorm + T is inert.
- When ON, dense ties are kept, sparse ties still collapse, and the tradeoff guard is on.
- It MOVES scores (see the next section).

### What moves (measured on this head over 169 records: 14 scenarios, 144 grid rows, 6 recorded d2 payloads, 5 extras)

**Under T, vs OFF**
- Grid: `overall` moves on 54 of 144 rows, `win_margin` on 11 and value badges on 6. There are 0 winner flips.
- Across all 169 records, `overall` moves on 68, again with 0 winner flips.
- R02 goes 67.0 -> 78.7, and its display 78 -> 84. Its phone rows go 5 -> 8.
- R01 goes from [72.0, 58.0] margin 14.0 to [80.2, 76.0] margin 4.2 ("clear lead" -> "narrow lead"). The same product wins.
- With ENABLE_CATEGORY_VALUE_BADGE ON, CB -> CBT moves badges on 32 of 144 grid rows.
- SVT vs S: `overall` moves on 90 of 144, margins on 48 and badges on 6, with 0 flips.
- **The activation is a product sign-off (R7).**

**Under V:** 0 arithmetic changes. Only the emitted `missing_data` moves, plus the guard's tradeoff effect listed above.

**validate_verdict under T (R11a):**
- 68 of 169 records change the `metadata.verdict_validation` shape.
- `claims_softened` rises: R01 2 -> 5, R02 3 -> 6, R08c 0 -> 1.
- `confidence_adjustment` changes on 0 of 169.
- Pinned in `test_verdict_validation_counts_under_tie_flag`. **Canary item.**

**The guard's effect (any flag):**
- Void-named loser strengths go 2 -> 0 and loser claims with margin < 1.0 go 66 -> 0 in every guarded state: V, T, VT, RV, RVT, SVT and CBT.
- Under R / RT / S the base counts stand at 2 / 67.
- Same-dimension pairs: 0 in every state.

**E5, tradeoffs vs base:**
- OFF equals base on 169 of 169 records (every captured field). So do R, S and CB.
- T moves 74 of 169 records and VT moves 77. The moved sets are:
  - every grid row whose F4.2 fallback named a margin-0 or sentinel dim (sweep pairs);
  - R08 / R08b / R08c / R08d / R08e;
  - the d2 skincare payload;
  - under VT only, also R03, R03c and d2 fashion.

### R16 PRODUCT NOTE (for DECISIONS_AHMED and the canary)

Under the guard, a sweep pair (the winner leads every eligible dim) ships `overview.tradeoffs: []` and `overview.winner.key_tradeoff: ""`. This reverses F4.2's "the runner-up card always renders".
- Measured: `key_tradeoff` is empty on 140 of 169 records under T and 146 of 169 under V, against 78 of 169 OFF.
- **Before flipping either flag, confirm that `RunnerUpWinsCard` renders its empty state for `tradeoffs: []`.** The phone contract has been "always a caption" since F4.2. This is a canary item, not code in this unit.

### Flag-OFF pins that get a delenv of both new names (R16, the K1 pattern; no other edit to those files)

These seven nodes are F4.2 / W4-10 flag-OFF pins that would redden when a developer exports V or T:
1. `tests/test_scoring_service.py::TestTradeoffPairs::test_sweep_with_scores_falls_back_to_loser_strongest`
2. `tests/test_scoring_service.py::TestTradeoffPairs::test_sweep_fallback_winner_idx_1`
3. `tests/test_tradeoffs_dedup_parity.py::test_tradeoffs_non_empty_for_brand_repeating_pair`
4. `tests/test_tradeoffs_dedup_parity.py::test_key_tradeoff_prose_is_non_empty_for_brand_repeating_pair`
5. `tests/test_tradeoffs_dedup_parity.py::test_hard_cap_partial_response_ships_runner_up_caption`
6. `tests/test_tradeoffs_dedup_parity.py::test_parity_repeat_vs_control`
7. `tests/test_tradeoffs_dedup_parity.py::test_mixed_pair_only_one_product_repeats`

Their flag-ON twins live in the new file as `test_sweep_pair_ships_no_runner_up_caption_under_guard[V|T|VT]`, and assert `[]` / `""`.

The OTHER flag-OFF value pins still redden when a developer exports V or T. CI never sets these flags, so they are left as they are (spec section 5, not edited):
- **V exported (11):** renorm golden fashion, fragrances and other; spec golden fashion and other; and six `test_tradeoffs_dedup_parity` pins: `test_scores_summary_dimension_leaders_use_display_spelling`, `test_control_pair_byte_identical[dimension_winners|scores]`, `test_control_summary_and_tradeoffs_unchanged`, `test_shadow_offline_control_summary_unchanged`, `test_shadow_offline_summary_does_not_import_orchestrator`.
- **T exported (9):** renorm golden fragrances; `test_identical_specs_still_collapse_to_tie`; and the parity pins above plus `test_control_pair_byte_identical[win_margin]`.
- **VT exported (13):** the union of the V and T sets.

### Gates (all measured on this head, pinned venv, every pytest run through the bounded runner with `-p qaren_netguard`)

**Unit file** `tests/test_scoring_rubric_truth.py`: 84 nodes, 83 passing plus the strict xfail (test 18). It grew in four steps:

| revision | nodes |
|---|---|
| the red's file plus the R14/R15/R16/R17 twins | 72 (71 + 1) |
| plus the mixed-sparsity pin | 75 (74 + 1) |
| plus the five R21 boundary pins | 80 (79 + 1) |
| plus the four R23 pins | 84 (83 + 1) |

Standalone in all 8 exported states (OFF, V, T, VT, R, RV, RT, RVT) it gives `83 passed, 1 xfailed` per state, with `[netguard] blocked 0`.

**The six unit files** (rubric_truth, missing_dim_renormalize, spec_field_normalization, scoring_service, tradeoffs_dedup_parity, trust_validation):
- Flags unset: 316 passed, 1 xfailed.
- In the exported states, only the flag-OFF pins listed above fail: 9 under T, 11 under V.
- `TestEdgeCases::test_all_missing_data` also fails under any exported renorm. This is pre-existing: it fails the same way at 04acb757.

**E1.** The four goldens are byte-unchanged:

| golden | sha256 |
|---|---|
| behavioral | 6b531fcb...dbbf |
| missing_dim_renorm | 43573b52...0549 |
| spec_field_norm | 8fc0e3d5...d82c |
| value_badge | b7fc3f15...e12b |

**E2.** 492 digests (164 records x OFF/R/S). Base (a 04acb757 detached scratch worktree) == head == base2 == the committed fixture, with 0 differing keys.

**E3.** `tests/fixtures/rubric_truth_flag_on_golden.json` is generated from this head through the committed generator. It carries a `_meta` header with the generating sha, states, builders and the CATEGORY_SPEC_SCHEMAS dependency.
- It equals the red's prototype copy on all 54 records.
- R14/R15 have no effect on it, because tradeoffs are computed outside `compute_scores`.

**E4.** Test 6 (V is arithmetic-neutral), test 15 (renorm + T == renorm, tradeoffs included) and the R17 twin are green.

**Comm set** (244 files; base and head in the same worktree, C8; 4 chunks; `--timeout=60`; CI deselects; run on the 75-node file):

| run | failed | passed | xfailed | netguard blocked |
|---|---|---|---|---|
| head | 0 | 6,538 | 36 | 536 |
| base | 51 (all new-file reds) | 6,487 | 36 | 533 |

- `comm -13 base head` is empty.
- The adversarial re-review re-ran the full set at head OFF in 10 chunks: 6,538 passed, 0 failed.
- The comm set was not re-run for R21 or R23, because only the unit file changed (+5, then +4 test nodes). Those nodes are covered by the 8-state runs above and below.

**CI-order set** (73 files, sorted, ONE process per state, CI deselects, on the 84-node file):

| state | failed | passed |
|---|---|---|
| OFF | 0 | 1,971 |
| V | 11 | 1,960 |
| T | 9 | 1,962 |
| VT | 13 | 1,958 |
| R | 1 | 1,970 |
| RV | 12 | 1,959 |
| RT | 10 | 1,961 |
| RVT | 14 | 1,957 |

- Every state had 2 deselected, 36 xfailed and 0 timeouts.
- OFF equals the red base run (1,888 passed) plus the 83 passing new nodes.
- Every failing id is a listed flag-OFF pin, or the pre-existing renorm-exported `test_all_missing_data`. The unit file has 0 failures in every state.
- Every failing-id set is identical to the R21 round's.
- The R21 round's run on the 80-node file had every pass count 4 lower, with the same failures: OFF 1,967, V 1,956, T 1,958, VT 1,954, R 1,966, RV 1,955, RT 1,957, RVT 1,953.
- An earlier run on the 75-node file hit the 60 s timeout on `test_explicit_pair_integration_mocked.py::test_explicit_pair_scoring_breakdown_is_fragrance_dims_e2e` under 3-process load. That test passes alone, and the single-process runs had no timeouts.

**Preserve set** (28 files, OFF): 683 passed, 2 deselected, `[netguard] blocked 52`. This is identical to the red's HEAD run.

**Mutations** (on the green bytes; byte snapshots; restores sha-verified; every edit is the adversaries' own bytes).
- Every row of the spec table as amended, plus the R14/R15/R17 rows, reddens named nodes, with three exceptions:
  - M5 is equivalent by construction.
  - A G'-only removal is equivalent under R15.
  - The "any product sparse" mutants M10g/h/i survived the red's file and are now killed by `test_mixed_sparsity_tie_is_kept`.
- The R21 round's five pins and the R23 round's four each kill the adversary's mutant:

| mutant | edit | killed by |
|---|---|---|
| A2 | guard `< 1.0` -> `<= 1.0` | `test_guard_margin_boundary_is_one_point` (+ the B1 pin) |
| B14 | guard `< 1.0` -> `< 1.1` | the same two |
| A5 | `_spec_sparse` `<` -> `<=` | `test_spec_coverage_equal_to_threshold_is_not_sparse` (+ the B2 pin) |
| A6 | `specs_flagged` dropped from the bucket sum | `test_reliability_bucket_sum_counts_specs_flagged` |
| A11 | V line on the condition alone | `test_value_partial_log_only_when_a_dim_was_unstamped` |
| A12 | NON_SCORING_SPEC_KEYS not stripped | `test_spec_coverage_is_measured_on_scoring_keys_only` (+ the A5 and B2 pins) |
| B1 | guard compares the raw lead (no `round`) | `test_guard_rounds_the_lead_before_comparing` |
| B2 | "N/A" counted as a populated spec field | `test_spec_na_string_is_not_a_populated_field` |
| B12 | `specs_unverified` dropped from the bucket sum | `test_reliability_bucket_sum_counts_likely_and_unverified[unverified]` |
| B13 | `specs_likely` dropped from the bucket sum | `test_reliability_bucket_sum_counts_likely_and_unverified[likely]` |

- The spot-checks M1, M7, M9, M11, M18, M18x, M19, M19b, M20 and M21 were re-run on the final file. Each keeps every node it reddened before.
- The whole file at the base bytes gives 60 reds, and all nine R21/R23 pins are among them.

**Lint.** `ruff` (E9, F63, F7, F82) and `py_compile` are clean.

**Corpus.** The `_proof` harness is BLIND to this unit (`price_service` imports only `PRICE_TIERS_BY_CATEGORY` from scoring), so it was not run.

**R21 premise corrections (R23).** R21 contained two premises that are false for the code it declared correct:
- **(A2) "a lead of 0.999 does not" stay eligible.** `round(0.999, 1)` is 1.0, so under the unchanged code a raw 0.999 lead IS eligible (margin 1.0), and the first ineligible 1-decimal lead is 0.9. The boundary pin keeps `<= 1.0` and `< 1.1` red. Its docstring states the rounded rule, and the rounding itself is pinned by the B1 pin.
- **(A5) "supplements 4/10 == 0.4".** No such case exists: the supplements schema has 11 scoring fields (4/11 < 0.4 < 5/11). The reachable coverage equality among direction-bearing categories is fragrances 3/10 == 0.3; fashion is directionless and always sparse. The A5 pin's case was already fragrances 3/10, a real equality, and it stands.
- R23's own float example also needed correcting: 4.3 - 3.3 is exactly 1.0 in float. The measured just-under pairs used are 64.1 - 63.1 (0.9999999999999929) and 4.1 - 3.1 (0.9999999999999996).

### Activation (each step with `tests/fixtures/rubric_truth_flag_on_golden.json` as the canary reference)

1. **V first, alone.** It is arithmetic-neutral but turns the tradeoff guard on, so check the R16 card empty state first. Canary on:
   - the `W4-6a value dim partial` line count (emitted only when a value dim was actually un-stamped);
   - the drop in `metadata.missing_dim_cells`;
   - no `value=N/A` beside a clear lead;
   - the fashion `cpw` row (V alone only);
   - the `key_tradeoff` empty rate.
2. **T second, in its own window, never with `ENABLE_MISSING_DIM_RENORM`** (renorm + T is inert by design).
   - T moves scores and displayed scores, so it needs a product sign-off.
   - Canary lines: `tie kept` vs `tie collapsed (sparse)`, and `WINNER_INDEX_MISMATCH`.
   - Check `verdict_validation` `claims_softened`.
   - Re-baseline `missing_dim_cells` on the day it flips.

### Stated limits

- **(c) is not closed** (R4). Two different fashion or other products still tie on craft/function. `test_spec_dim_can_separate_two_fashion_products` is `xfail(strict=True)`. W4-6c (a non-numeric merit table) is Ahmed's DECISIONS item.
- **The sparsity thresholds are heuristics.** Their production frequency is unknown. These details are now pinned:
  - the coverage-equality rule;
  - the scoring-keys-only rule;
  - the "N/A"-is-not-populated rule;
  - each of the four fact_check buckets;
  - the guard's rounded 1.0 boundary.
- **Still unpinned:**
  - the log LEVEL of the V line. A mutant that logs it at DEBUG instead of INFO survives the file (measured). The line's presence and gating are pinned.
  - the non-dict `specs` / `fact_check` branches of the sparsity helpers. Returning "not sparse" there is equivalent inside `compute_scores` (a non-dict yields MISSING, so there is no non-MISSING tie).
- **One-sided sentinels still carry 50 into the margin** (#101, W4-6b). The 3 remaining N/A-contributor grid rows belong to W4-6b: fashion/other `one_missing_price` and supplements `both_no_price`.
- **Uncovered sentinel case (R11d).** G does not cover a margin computed against the WINNER's sentinel. Low severity.
- **`home_routes.py:452-465` priority_match (R11b).** It compares a dict to a string, so it can never match. This is pre-existing and owned by W4-12c.
- **`excluded_dims` vs `missing_data` under renorm + V (R11c).** They can disagree. That is renorm's own design (red measurement: 40 records under both R and RV).
- **A developer `.env` carrying V or T reddens the flag-OFF pins.** They are listed above.
- **Pin-coverage limit accepted by Fable after the round-2 re-adversary (stated, not fixed):** `_spec_sparse` keeps every scoring field in the coverage DENOMINATOR, as `_score_specs` does; a mutant that also drops `"N/A"`-valued fields from the denominator (C3) survives the unit file because the pinned sparse/dense cases fall on the same side with either denominator. The behaviour matches the scorer; a denominator pin is a follow-up nit, not a defect.

### Follow-ups

- W4-6b: the #101 sentinel arithmetic, and lifting the renorm coupling.
- W4-6c: the fashion/other merit discriminator.
- W4-12c: the `home_routes` priority_match dead compare.
- R16 canary: the RunnerUpWinsCard empty state.
- Optional: a caplog level pin for the V INFO line.

### CLAUDE.md corrections for the docs PR

- Add both flag rows, including "V also turns the tradeoff guard on" (R14) and both value-dim N/A figures (21 -> 3 `value_score` rows; 72 -> 11 across all value dims).
- Add one line in `.claude/skills/qaren-scoring/SKILL.md`. Do not reflow the `scoring_method` enum line.
- The value blend is `VALUE_FORMULA_BY_PRIORITY["_default"]` 0.7 spec / 0.3 price (C5), not 0.6/0.4.
- Record that T is inert under ENABLE_MISSING_DIM_RENORM by design.

References: PO-RUBRIC-01/02/03/08 (+08b), #101 (W4-6b), W4-10 #176, #100 (spec-field-norm composition, test 16).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

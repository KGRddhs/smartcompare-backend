# LANE L3 — Winner-axis scoring / evidence

**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l3`
**Branch:** `feature/s3-l3-winner-evidence`
**Owner:** L3
**Merge order:** L5 → L4 → L2 → **L3** → L1 (I merge 4th, just before L1)

# ============================================================================
# L3 v2 — "GENUINE WINNER FROM SCORE" — BUILT + TEST-GREEN (Ahmed pivot 2026-06-13)
# ============================================================================
Ahmed directive: "best for accuracy + genuine... recommendation based on pain, prompt system, reviews, preferences, logic." Winner EMERGES from the genuine overall score, NOT a winner_index flip. Frontend already argmaxes scoring_v2.overall_score (ResultsScreen.tsx:634-641) → fix the score, everything agrees, ZERO FE change.

## BUILD STATUS — ALL BUILT + TEST-GREEN (commits 49c3476 → b525941, on feature/s3-l3-winner-evidence)
- DROPPED: A2 value-neutralization, estimate-demotion FLIP, L3.2/L3.3 tie-break index-OVERRIDES + helpers + 4 v1 test files. Winner = plain argmax(authority-adjusted overall), no flips, no markers.
- (a) PRICE-AUTHORITY score factor: `_price_authority_delta` (estimate −pts / converted_usd −pts*0.5 / real 0), hatch `WINNER_PRICE_AUTHORITY_POINTS` (default 4). Penalize-the-estimate; all-MISSING-guarded.
- (b) lever 1 VALUE-FOR-MONEY: `VALUE_FORMULA_BY_PRIORITY` default 0.60/0.40 → 0.70/0.30.
- (b) lever 2 VALUE-WEIGHT hatch: `_scale_value_weight` + `WINNER_VALUE_WEIGHT_SCALE` (default 1.0 no-op) → sweepable; FINAL default = Ahmed sign-off on the sweep.
- A1 DAMPENING (reinstated — was never actually removed from _normalize_dimension): 45+ratio*40 band, tie→65, hatch `DISABLE_DIM_NORM_DAMPENING`.
- MAGNITUDE-AWARENESS (the root fix): `_magnitude_aware_ratio` relative-gap tolerance — gap within `WINNER_DIM_GAP_TOLERANCE` (default 0.08) → tie at midpoint; beyond → lead scaled by excess (gap−tol)/(1−tol). Kills "+0.02% → 40pt lead" noise (verified: 1% battery gap now perf 50/50, was 85/45).
- (c) COHORT-into-weights — COMPLETE (scoring layer + orchestrator wire): `apply_cohort_adjustments` (±10% cap, reuses CATEGORY_PRIORITY_ADJUSTMENTS scaled 0.10/0.30); `compute_scores(cohort_profile=...)` applied only when no explicit prefs; scoring_method='cohort'. Orchestrator `_derive_cohort_profile` seeds demographics→cohort prefs (cohort_service.seed_preferences) at BOTH compute_scores sites (sync + streaming), fail-soft (explicit-prefs-win / no-demographics / error → None). Fires for logged-in users with demographics + no explicit prefs.
- (d) MISSING_SCORE=50 collision fix: `compute_dimension_winners` reads explicit `missing_data` lists, NOT `==50` value-equality (a computed 50 = rating 2.5★ / reliability 0.5 is a REAL score). Band-independent.
- (e) #2 GPT-winner → LOG-ONLY: response_builder logs `GPT_WINNER_DISAGREES` on grounded disagreement, NO index override. Shipped winner = genuine argmax; verdict explains it.
- `build_winner_evidence`: qualitative genuine-winner reasons (real BH price / stronger reviews / overall lead), no internals.
- OFFLINE SWEEP HARNESS (`.qa-i2-refute/offline_param_sweep.py`, ZERO Serper): re-scores ONE captured full-200 body-set over the 4-param grid (price-authority × gap-tolerance × value-weight × A1) vs gold, picks max-winner subject to no-regression guard (price≥.84/specs≥.87/factual≥.94/pass≥.425). VALIDATED end-to-end on a 4-row synthetic set. **fact_check gap noted**: the live capture omits per-product fact_check → re-score uses fact_check=None uniformly (relative ranking valid; add fact_check to the capture DEBUG for exact fidelity — still ONE live run).
- Tests: 46 new v2 (genuine-score 8 / denoise 10 / cohort-scoring 5 / cohort-wire 5 / missing-collision 5 / value-weight 5 / #2 8) + ~398 core scoring regression GREEN (437-test consolidated v2+scoring run all green). **v2 BUILD COMPLETE — nothing left to build; awaiting dispatcher full-200 capture → offline sweep → set hatched defaults to winning combo (Ahmed sign-off) → merge.**

## ✅ GATE FIX-DELTA A+B+C — DONE (commit `ecfcc37`, pushed; ready for serialized re-review)
ultracode gate verdict was ISSUES/fix-before-merge. All three fixed under TDD (failing test first), full v2 suite (81) + broad scoring regression (464) + response_builder (39) GREEN; no-regression guard intact.
- **A [HIGH] CALIBRATION-COLLAPSE wrong-winner** (`response_builder._build_scoring_v2`): FE reads `(product_a>=product_b)?0:1` (ResultsScreen.tsx), never winner_idx. `calibrate_score=int(round(70+(raw-50)*0.5))` collapses sub-~2pt raw gaps to a calibrated tie → FE crowns product_0 even when winner_index=1 (hero ring split from verdict/evidence/name) — v2 made this the MODAL outcome. FIX: enforce `argmax(score_a,score_b)==winner_index`, nudge the LOSER strictly below the winner (clamp to band floor 60), winner keeps its honest score. Backend-only, zero FE change. Test `test_calibration_collapse_v2.py` (6). **This was the bug that invalidated the "argmax→FE matches→zero-FE-change" premise — now genuinely true.**
- **B [MED] MISSING_SCORE=50 collision** — a real 2.5★ → `_normalize_review`=EXACTLY 50.0; 0.5 reliability/popularity → `_normalize_direct`=50.0, both collide with the sentinel. FOUR sites filtered `==MISSING_SCORE` and dropped real values: (1) `_normalize_scores` producer → `_signal_missing_for` (per-signal `_<sig>_missing` flags); (2) `_dim_from_category_lookup`+`_compose_delta_text` → `missing_data`/score-is-None, `_ABSENT`-sentinel fallback to value-equality for the legacy synthetic shape; (3) spec_secondary blend → gate on `_spec_missing`/`_review_missing` (real 2.5★ now BLENDED not dropped); (4) `count_missing_dim_cells` (Ahmed's "no missing data" KPI dial) → `missing_data` authoritative. Tests +4 (collision) +3 (coverage). **Legacy synthetic fixtures (no `missing_data` key) preserved via the `_ABSENT` fallback → `test_dim_winner_one_sided_missing` stays green.**
- **C [MED] magnitude denom** (`_magnitude_aware_ratio`): `rel_gap` divided by `abs(hi)`, but with negatives `abs(hi)` can be the SMALLER magnitude (lo=-100,hi=-10 → |hi|=10≪|lo|=100) → under-reports scale → INFLATES rel_gap → modest gap reads decisive (the noise→decisive failure A1 targets). FIX: `denom = max(|hi|,|lo|)` (sign-agnostic, never < |hi|, positive-only pairs unchanged). Tests +4 (negative/sign-crossing edges).

## ✅ GATE RE-REVIEW HOLES CLOSED — DONE (commit `0e68cfc`, pushed)
Re-review of ecfcc37 said A/B/C correct on the default path but flagged TWO completeness holes (same "incomplete sweep" pattern). Both TDD; v2 suite (89) + scoring/response regression (503) green; value_math RED-by-design unchanged (35 pre == 35 post, stash-verified).
- **A floor-edge hole** (`_build_scoring_v2`): the loser-nudge can't separate when BOTH calibrate to the FLOOR (60) → `max(60,min(60,59))==60` → still a tie → FE crowns the loser at winner_index=1. Unreachable on default flags but `DISABLE_DIM_NORM_DAMPENING`'s legacy 30-100 band reaches it. FIX: when the WINNER is at/below the floor, RAISE it above the loser (clamp ceiling 95) instead of lowering the loser; else keep winner honest + lower loser. Holds on BOTH flag paths. Now imports `_CALIBRATION_FLOOR/_CEILING`. Tests +4.
- **B value-score ==MISSING_SCORE** (`_compute_value_score`, the 4th site): in prod (Bundle C OFF) a REAL spec/price normalizing to EXACTLY 50.0 was misread as missing → value dim dropped a real contribution → corrupted overall+winner. FIX: thread the authoritative `_spec_missing`/`_price_missing` flags (module fn + method + `_normalize_scores` call site); default None → legacy `==MISSING_SCORE` so scalar-only callers/tests keep sentinel semantics. Tests +4.
- **Cleanup** (gate-flagged minor): `_dim_winner` dropped the redundant `score_a==MISSING_SCORE and score_b==MISSING_SCORE` value-equality (only fired on a genuine real-50/50 tie the tie-margin check already handles; it was the very collision this pass kills).
**Both holes closed → genuine-winner invariant now complete on both flag paths.**

## ✅ v2 APPROVED + MERGE-PREP DONE + REVIEW-DENSITY ALIGNED — ready for v2→main ff
- **v2 APPROVED** by team-lead (re-verify clean: A unified floor/ceiling, B flag-thread + legacy fallback, cleanup all correct; 89 v2 + 503 regression green).
- **Merge-prep (path-a) DONE** — merge commit `34bf3d0` (origin/main 28ffc38 / L2 youtube INTO the branch). Sole conflict = extraction_service.py, resolved keep-both (my #2 `_gpt_winner_lever_enabled`/`_build_independent_winner_block` + append; L2's youtube trio + `_p1/_p2` dual scrub). response_builder + ssc auto-merged. **COEXISTENCE PROVEN: 159 green** (89 v2 + 70 L2 youtube together, YOUTUBE_API_KEY set). team-lead confirmed merge-tree v2→main = exit 0 conflict-free.
- **Review-density test ALIGNED to v2** — commit `fb5e2d5` (HEAD). `test_review_density_verdict` (b) tie-break tests rewritten: the pre-pivot L3.3 index-FLIP is GONE; YouTube view-count NEVER enters compute_scores (citation-only in factual_verdict + verdict prompt). Now asserts density does NOT flip the genuine winner (verified fixture: identical real signals → overall 61.8/61.8 TIE, winner_evidence []). 7/7 green. **This was the last gate before the v2→main ff merge.**
- **Two pre-existing reds characterized (deferred per team-lead):** (1) `test_extraction_prompt_bundle_c::test_response_builder_strips_inference_source` = ANCIENT pre-S3 (RED on S3-base 38d8368, temp-worktree verified) — C.3.5 `_internal.processor_inference_source` masking the builder never did; test-only, close-out hygiene. (2) YouTube import-order fragility (`youtube_service.py:47` reads key into a module constant at import) — close-out lazy-key-read hardening; Railway/.env sets the key so prod unaffected.

## ✅ OFFLINE SWEEP HARNESS — SELF-GRADE LOADER ALIGNED + VALIDATED ON REAL ROWS (capture RUNNING)
`.qa-i2-refute/offline_param_sweep.py` (scratch, never committed). **Capture is a RAW body-dump** `{id, query, category, region, body, error, wall_ms}` — NO pre-grading, `_debug_capture=None` (EVAL_CAPTURE_DEBUG stayed OFF per Ahmed — no prod config change). Loader **SELF-GRADES** (team-lead ruling): joins captured `id` → gold `data/validation_gold_truth.json` for `expected_winner_index`, builds `QueryRunResult` + calls `scripts.eval_runner.grade_run_result` → price/specs/factual graded ONCE per body, FIXED across combos; CANONICAL gold `_metadata.axis_weights` via `load_axis_weights` (baseline parity, 0.25/0.25/0.30/0.20). Then per combo re-runs compute_scores → `_build_scoring_v2` → `overall_score.winner_idx` EXACTLY as `eval_runner.extract_winner_index` (winner = the ONLY swept axis). fact_check→None offline (relative-valid; conservative absolute). Error rows → products=None → winner can't pass (eval mirror); id-not-in-gold → skip+warn. Grid = WINNER_PRICE_AUTHORITY_POINTS[4/2/6] x WINNER_DIM_GAP_TOLERANCE[.08/.05/.12] x WINNER_VALUE_WEIGHT_SCALE[1.0/.85/.70] x DISABLE_DIM_NORM_DAMPENING[on/off] = 54; guard price>=.84/specs>=.87/factual>=.94/weighted>=.425.
- **VALIDATED on REAL captured rows** (`--realrow` on the live `full200_bodies.jsonl` partial): default-combo re-score == captured winner_idx on EVERY row (reconstruction faithful); self-grading real (elec-001 price=False = genuine 131.97 vs gold 290-400 BHD miss, graded via extract_price_amount); full sweep dry-run on 21 partial rows runs end-to-end (load→grade→54 combos→rank→table; levers move winner% 14.3→23.8). Synthetic self-test ALL PASS; py_compile clean.
- Modes: `--selftest` (synthetic + relabel), `--realrow <file>` (validate loader on real rows), `--bodies <file>` (the 2-pass sweep).
- **2-PASS HONEST-PROVENANCE ADDED** (team-lead): Pass A = as-deployed; Pass B = `relabel_price_provenance` flips `local_bhd`→`converted_usd` keyed on `gl=us` in price.url (primary) + non-BH-retailer backup (NON-circular, never gold). Reports A→B winner delta overall + per-category + relabel count. Relabel self-test GREEN (gl=us/non-BH flip; lulu/sharafdg STAY local_bhd; estimated/converted_usd untouched).
- **KEY FINDING (partial 53 rows): A→B delta = +0.0pp** (90 prices relabeled). Traced: relabel DOES reach the score (authority delta [0,0]→[-2,-2]) but **44/46 rows have BOTH products gl=us → symmetric -2/-2 penalty CANCELS → winner can't move**; only 2 asymmetric, ZERO genuine-BH-contrast rows. AND relabel changes source_method ONLY not the cheap AMOUNT → value dim (reads price_raw) UNCHANGED. **=> The S3.1 fix is NOT relabel-provenance (no-op here); it's REPLACE gl=us prices with genuine BH prices / reject the cheap amount. The winner gap is an L1/price-COVERAGE gap (engine finds NO real BH price, falls to gl=us for BOTH every time), not a scoring-lever gap.** Harness prints the symmetric/asymmetric breakdown + this caveat inline.
- **CLEAN-vs-TAINTED SUBSET SPLIT ADDED** (team-lead; Pass C SKIPPED as circular): `Row.tainted` = `_is_gl_us_fallback` on >=1 as-deployed product (NON-circular, never gold). CLEAN = both genuinely sourced (BH local_bhd / iHerb / page_scrape / official_brand / real converted_usd / estimated). Reports CLEAN vs TAINTED winner% + counts + per-cat on the best AS-DEPLOYED combo = separates scoring-QUALITY (CLEAN) from sourcing-COVERAGE cap (TAINTED). Self-test GREEN.
- **STARK PARTIAL FINDING (71 rows): CLEAN=0 / TAINTED=55 / ERROR=16.** source_method distribution across ALL partial prices = `local_bhd`:107, None:3 — EVERY price stamped local_bhd, every one gl=us; ZERO genuine BH/iHerb/page_scrape/official_brand. TAINTED winner% (sourcing-capped) = 44.4% (24/54). **Definitive: on this chunk the engine NEVER returns a real BH price — 100% gl=us mislabeled local_bhd. The winner gap is a price-SOURCING-COVERAGE gap, not scoring.** CAVEAT: partial = elec+frag+makeup+skin+hair+fash+groc+other (least BH coverage); supplements NOT in chunk yet → iHerb supplement prices should give the first CLEAN rows in the full 200 → that's the scoring-quality read.
- **HARNESS COMPLETE**: A (ship combo) + B (relabel ~0 no-op proof) + CLEAN/TAINTED split + guard — all 5 self-test sections GREEN + validated on the real format. **Capture RUNNING** (~55/200 last signal) → `.qa-i2-refute/full200_bodies.jsonl`. Run: `python .qa-i2-refute/offline_param_sweep.py --bodies .qa-i2-refute/full200_bodies.jsonl`. Awaiting full-capture done signal → sweep → ship Pass-A winning combo as v2 defaults (Ahmed sign-off); B + CLEAN/TAINTED are diagnostics not ship.

## 🔴 #1 S3.1 FOLLOW-UP — PAIN → SCORE WEIGHTS (deferred, team-lead-ratified)
Pain (`pain_workflow_priors.json`) currently shapes the recommendation's EXPLANATION (verdict prose, extraction_service.py:1188 — LIVE), NOT the score weights. The 8 pain workflows are VERDICT-PROSE constraints ("lead with TL;DR", "max 3 differences", "cite source counts"), not a clean what-matters→dimension signal — only ~4/8 have any fuzzy dim affinity + some (value_budget) FIGHT the value-reduction. A proper pain→dimension-weight mapping (per-category, ±10% cap, validated against the other levers) is a dedicated design sub-project = THE #1 S3.1 item. Surfaced to Ahmed via team-lead.

## 🔴 #2 S3.1 ITEM — gl=us / cheap-marketplace prices MISLABELED `source_method=local_bhd` (team-lead-ratified; DO NOT chase mid-capture)
Read-only audit of the partial capture (30 rows) found **27 product-prices labeled `local_bhd` whose amount is <70% of the gold floor** — NOT electronics-only: spans electronics, fragrances (frag-001..006: 0.90–45 BHD vs gold floors 10–120), makeup (make-001..005: 2.61–7.52 BHD vs floors 4–22), skincare. The amounts are implausible as real local Bahrain prices (currency/unit/cheap-marketplace artifacts) yet carry the authoritative `local_bhd` provenance label. **Two score impacts (team-lead's read, corroborated):** (a) v2 price-authority gives `local_bhd` ZERO penalty (should be `converted_usd −2` for a US-converted/marketplace price) → no demotion; (b) the value dim (`_normalize_price`: lower=higher) REWARDS the artificially-cheap price → depresses the winner toward the fake-cheap product. **Candidate root cause of the electronics+multi-cat winner gap.** S3.1 FIX = correct the gl=us→`converted_usd` (or reject) labeling in the price pipeline (L1/price_service provenance), THEN the price-authority penalty + value dim behave honestly. The sweep measures the engine AS DEPLOYED (faithful) — it will show the real number; we INTERPRET the winner% knowing this mislabel suppresses it. Evidence audit lives in this session's transcript; reproduce via the read-only source_method-vs-gold-floor scan.

## DROP (confirmed removable, all winner-index-flip mechanisms)
- A2 value-axis neutralization (`_winner_without_value_dim` + `winner_value_neutralized` marker + the cross-tier recompute block in compute_scores L1164-1180). Reason: no-op on its own target case (proven), re-injects first-index bias (o0>=o1→0), UI contradiction. GONE.
- Estimate-demotion winner_index FLIP + the price-authority/review-density tie-break OVERRIDE (`apply_winner_evidence_tiebreak` index-override paths). Replaced by score factors below. GONE.
- L3.2 price-authority tie-break + L3.3 review-density tie-break (the index tilts) — folded into the SCORE, not a flip.

## REPLACE WITH (winner emerges from the genuine `overall`)
### (a) PRICE-AUTHORITY AS A SCORE FACTOR (not a flip)
- WHERE: in `compute_scores`, after the per-product `overall` is computed (L1137), apply a multiplicative/additive authority adjustment per product BEFORE the argmax. Real BH price (source_method in `_PRICE_TRUST_SET`) → modest BUMP; `estimated` → modest PENALTY; `converted_usd` → neutral-to-small penalty (not a real local price but not fabricated).
- MAGNITUDE (proposed, to be tuned empirically): additive ±~4 points on the 0-100 overall (real: +2, estimate: −2; net ~4pt swing). Rationale: must be SMALLER than a decisive signal lead so a clearly-better estimated product still wins (kills the over-fire finding, gate c=0.92 case), but large enough to tip genuine close calls (<~4pt) to the real-priced side. 4pt ≈ half the old 8pt tie band — close calls only. EXACT magnitude measured on full-200 (escape-hatch env `WINNER_PRICE_AUTHORITY_POINTS`, default the chosen value).
- "Facts beat estimates" now lives IN the score → visible + consistent in rings/verdict/share. No fabrication: it's a confidence weight on REAL vs ESTIMATED provenance, not a made-up price.

### (b) VALUE / CHEAPER-PRICE DOMINANCE REDUCTION (the core accuracy lever)
- ROOT CAUSE (S2-pinned): the value dim rewards ABSOLUTE cheapness (`_normalize_price`: lower price→higher score), but gold's winner is the PRICIER product 64% of priced rows. The value dim (electronics weight 0.20) + its price-component drag the winner toward cheap.
- APPROACH: two levers, BOTH measured (NOT guessed):
  1. RESHAPE value → value-FOR-MONEY: the value dim already blends spec+price via `_compute_value_score` (default spec 0.60/price 0.40). Shift the default toward spec (e.g. 0.70/0.30) so "what you get" dominates "how cheap" — i.e. value rewards strong specs at a fair price, not raw cheapness.
  2. REDUCE value dim WEIGHT in `CATEGORY_DIMENSION_WEIGHTS` (electronics 0.20 → ~0.12-0.15), redistributing to specs/reviews so genuine quality drives the pick. CAUTION: this is the delicate lever — touches the weight table the gate flagged as Ahmed-scope. Propose a SMALL reduction + measure the winner delta per-category on full-200; tune via escape-hatch before committing the number.
- MEASUREMENT: full-200 winner_pass per-category, sweep value-weight/coeff candidates (escape-hatch envs), pick the config that maximizes winner without regressing price/specs/factual. Don't ship a guessed number.

### (c) PAIN + PREFERENCES INTO THE WEIGHTS (genuinely applied)
- CURRENT STATE (verified): `compute_scores` already receives `preferences=user_preferences` + `behavior_profile` and applies them — `_compute_weights` applies `CATEGORY_PRIORITY_ADJUSTMENTS` (priorities) + budget adj; `apply_behavioral_adjustments` applies the behavior profile. So PREFERENCES + BEHAVIOR genuinely shape the dimension weights TODAY. ✓
- GAP: `pain_workflow_priors` + `demographics_profile` (cohort) do NOT reach `compute_scores` — they only feed the VERDICT prompt (orchestrator L1462 `pain_workflow_context`; L1444 `demographics_profile`). So "pain" currently shapes the EXPLANATION, not the SCORE.
- DECISION NEEDED (your call): do we wire pain_workflow + cohort into the SCORE weights now (NEW: a `pain_workflow`/`cohort` → dimension-emphasis mapping passed to compute_scores, capped like behavioral ±10%), or KEEP pain/cohort as verdict-only for v2 and note score-wiring as a follow-up? My lean: wire COHORT into weights now (it's already fetched + has a clean priors structure), DEFER pain_workflow score-wiring (pain_workflow_loader's shape is verdict-oriented; mapping it to dim weights is a design sub-project). Confirm.

### (d) A1 KEEP-OR-DROP + MISSING_SCORE=50 collision
- A1 (normalization dampening 30+r*70 → 45+r*40): it is PURELY COSMETIC for the winner (compresses dim bars symmetrically, preserves order — proven 0/4 fixture flips). With the winner now emerging from `overall`, A1 changes only displayed bars. RECOMMENDATION: DROP A1 for v2 simplicity (one fewer moving part, no UX-risk, no winner benefit) UNLESS you want the honesty/calibration UX win — then keep behind `DISABLE_DIM_NORM_DAMPENING`. My lean: DROP (Ahmed wants genuine accuracy, not bar cosmetics; revisit in a calibration pass).
- MISSING_SCORE=50 COLLISION (real bug, pre-existing, independent of A1): MULTIPLE legitimate real scores == 50.0 — `_normalize_review` rating 2.5★ → 50.0; `_normalize_direct` reliability/popularity raw 0.5 → 50.0. Sites that filter `score == MISSING_SCORE` then DROP these real values: `_non_price_overall` L704 (going away with A2) + `compute_dimension_winners` L1887 + `_dim_winner` L2563 + `_dim_from_category_lookup` L2551. FIX: stop using `==50` as the missing sentinel. Track missing via the EXISTING explicit per-product `_<dim>_missing` flags / the `missing_data` list (already computed at L1143) + `was_missing_*` markers — they're robust. Audit the `==MISSING_SCORE` filter sites; replace value-equality checks with the explicit flags where a real 50 could be dropped. (Some sites are display-only + low-risk; I'll list the load-bearing ones in the build.)

### (e) #2 GPT-WINNER → GROUNDED CROSS-CHECK LOG ONLY
- KEEP the #2 producer (extraction_service `_build_independent_winner_block`, flag-gated) — it's the "prompt system" signal. KEEP the consumer reading `independent_winner_*`.
- CHANGE: NO index override. In response_builder, when ENABLE_GPT_WINNER on AND GPT's GROUNDED independent winner != the genuine deterministic argmax → LOG it (like WINNER_INDEX_MISMATCH: `GPT_WINNER_DISAGREES deterministic=X gpt=Y grounded=true basis=...`) for S3.1 investigation. Shipped winner = genuine deterministic argmax ALWAYS. The GPT verdict EXPLAINS that winner, grounded in the same signals. (Removes the consistency trap; preserves the signal for the S3.1 adoption decision.)

## KEEP (unchanged, now describing the genuine winner)
- `winner_evidence` qualitative reasons — repoint to describe the GENUINE winner ("real Bahrain price + stronger reviews + fits your priority"). Built from the same score factors (price provenance, review strength, the priority that drove the weights).

## MEASUREMENT PLAN (escape-hatches for empirical tuning)
- Env knobs (default to chosen values): `WINNER_PRICE_AUTHORITY_POINTS`, value-weight/coeff override. Full-200 on PROD (dispatcher) sweeps candidates; pick max-winner-no-axis-regression. The value re-weight is delicate → measure, don't guess.

## SEQUENCING
DESIGN (this) → team-lead review → BUILD (TDD) → measure full-200 (PROD) → tune via hatches → merge. Main-merge HELD until v2 built + measured. SUPERSEDES merge-as-is + marker-fix + merge-resolution (A2/demotion gone).
# ============================================================================

## WINNER-ONLY INVARIANT (team-lead merge-gate requirement — VERIFIED 2026-06-13)
The winner-mechanism interventions must NOT mutate the per-product `overall`/`breakdown` data the eval's price/specs axes read. Verified by code inspection:
- **A2 (value-axis neutralization)** + `_winner_without_value_dim`: WINNER-ONLY. A2 block writes only `winner_index`/`win_margin`/`winner_value_neutralized`. `_winner_without_value_dim` READS breakdowns (local copies via `.get`) + computes local `o0/o1`; does NOT mutate `result_products`. ✓
- **tie-break + estimate-demotion** (`apply_winner_evidence_tiebreak`, incl. `_non_price_overall`, `_review_density_*`): WINNER-ONLY. ZERO assignments to `result_products[...]`/`products_data[...]`/`["overall"]`/`["breakdown"]` — returns `(winner_index, winner_evidence)` only. ✓
- **A1 (normalization dampening)**: NOT winner-only — by design it changes `_normalize_dimension` output, so the displayed `breakdown` dim-bar values shift (45–85 band). HOWEVER the EVAL axes are still insulated: eval `price_pass`/`specs_score`/`factual_pass` read `overview.products[i].price`/`specs` + verdict text, which are INDEPENDENT of the scoring breakdown (confirmed eval_runner L560-590). So A1 cannot regress price/specs/factual; it only re-scales the user-visible scoring_v2 dim bars (the intended display effect + escape-hatch `DISABLE_DIM_NORM_DAMPENING`).
- **#2 GPT-winner (response_builder)**: WINNER-ONLY + flag-OFF in prod. Overrides `winner_index` only; no breakdown mutation.
NET: all 4 are eval-axis-safe (price/specs/factual cannot regress from any of them). Only the WINNER axis is affected — exactly the intended blast radius.

## Mission
Ground the winner pick in real evidence so it stops being a coin-flip (.495 → ≥0.60 full-200).
Consume signals that ALREADY EXIST in the response:
- `price.source_method` (enum incl. `estimated`) — every response today. L1 makes more "real"; my mechanism benefits automatically.
- L2's `reviews["youtube_review_signal"]` (DONE on `feature/s3-l2-youtube`).

## Tasks (plan §L3)
- [x] **L3.1 winner-discriminator audit** (diagnostic, NON-credit) — DONE (findings below)
- [x] **L3.2 Bahrain availability + price-authority into the winner pick** — DONE (evidence-weighted tie-break in compute_scores; GUARDS decisive-margin + both-MISSING; order-independent). 7 tests + 304 scoring-suite regression green.
- [x] **L3.3 review-density into the verdict** — DONE. Two surfaces: (a) factual_verdict CITED review-density candidate (channel + humanized views) competing for line1, flag-gated; (b) review-density as the SECOND tie-break axis in apply_winner_evidence_tiebreak (price authority stays first). 7 tests + regression green.
- [x] **L3.4 `winner_evidence` surfaced in scoring_v2** — DONE. `_build_scoring_v2` threads `scoring_result["winner_evidence"]` into the `scoring_v2` payload (always-list, str-coerced, malformed→[]). End-to-end chain pin (compute_scores tie-break → scoring_v2) green. 6 tests + regression green.

**ALL L3 SHIPPED (L3.1–L3.4 + ESTIMATE-DEMOTION + A1 + A2 + #2) — FINAL rulings 2026-06-13.** smoke20 (A+#2 ON) RUNNING vs baseline 4aee8e88 against local uvicorn. NO merge until measured (I merge 4th).

## FINAL DISPOSITION (team-lead consolidated rulings 2026-06-13)
**A1 normalization dampening — KEEP, DEFAULT ON (restored via revert-of-revert ad5d96e).** `_normalize_dimension` 30+ratio*70 (30–100) → 45+ratio*40 (45–85), tie 70→65. Kept for honesty (don't manufacture 70pt swings from noise — Ahmed's accuracy directive) + possible winner help (measured). Escape hatch `DISABLE_DIM_NORM_DAMPENING` (default OFF) if Ahmed vetoes the bar-compression. Constants `_DIM_NORM_*`. Tests: tests/test_normalization_dampening_a1.py (8).
**A2 value-axis neutralization — KEEP, DEFAULT ON (214e689 + 8b5a638).** Cross-tier: recompute winner with value-type dim removed → cheaper-wins anti-signal (gold winner pricier 64%) stops deciding. Winner-only. OFF-switch `DISABLE_WINNER_VALUE_NEUTRALIZATION`. Tests (5).
**#2 GPT-qualitative-winner lever — BUILT, FLAG-GATED DEFAULT OFF (commit a9ea45d).** PRODUCER (extraction_service `_build_independent_winner_block`, gated `ENABLE_GPT_WINNER`): verdict prompt asks for an INDEPENDENT winner judged purely on product facts (not the deterministic scores), hard no-guessing rule + honest `grounded:true/false` self-report + cited basis (additive JSON keys). CONSUMER (response_builder `_grounded_gpt_winner` at the H1 site): overrides deterministic winner ONLY IF grounded (no-estimation guardrail) + valid 0/1. Flag OFF → byte-identical. Tests: tests/test_gpt_winner_lever.py (7).
**ADOPTION GATE (#2):** flip ON in prod ONLY IF winner UP AND factual_pass ≥.94 AND no axis regresses. Else #2 ships flag-OFF dormant + documented.
**SAFETY:** A1+A2 winner-only-relevant for the eval (winner reads overall; eval price/specs read overview.products); #2 default-OFF. 254 broad L3 regression GREEN.
**SMOKE20 IN FLIGHT:** local uvicorn (127.0.0.1:8099) serving worktree, A1+A2+demotion default-ON + ENABLE_GPT_WINNER=true; `TARGET_BASE_URL` + smoke20 --concurrency 1 --mode regression vs 4aee8e88; out → .qa-i2-refute/smoke20_A_plus_2.jsonl. Will report winner delta PER-CATEGORY + factual_pass + watch A2/budget + A1/large-margin flips.

## ESTIMATE-AUTHORITY DEMOTION (Ahmed directive: "facts, accuracy, NO estimation — an estimated-price product can never out-rank a real-priced one on fabricated confidence")
- **Hole found + reproduced:** `_compute_raw_scores` feeds `price.amount` into the value/price dims REGARDLESS of `source_method`, so a GPT-estimated cheap price inflated the value dim and handed an estimated product a DECISIVE 14pt win (71.4 vs 57.4) over a real-priced competitor with identical specs/rating. The band-limited L3.2 tie-break didn't catch it (margin outside the 8pt band).
- **Fix (fact-preserving):** in `apply_winner_evidence_tiebreak`, when one product is real-priced and the other estimated, an estimate that wins is DEMOTED to the real-priced product UNLESS it also leads on NON-PRICE evidence (specs/reviews/reliability/popularity, via `_non_price_overall` excluding the value-derived dim) by >= the tie band. Applies at ANY margin (checked before the decisive-margin rule). A real-priced product is NEVER demoted. Cited `winner_evidence`.
- `apply_winner_evidence_tiebreak` gained a `category` param (threaded from compute_scores) so `_non_price_overall` picks the right dim map.
- Guards: both-estimated / converted_usd-vs-estimate (neither real) → no demotion; estimate that genuinely leads on specs+reviews → keeps win; real-already-wins → no-op. Order-independent.
- Tests: tests/test_estimate_authority_demotion.py (6) + 486 broad scoring regression GREEN.

## L3.3 implementation (committed)
- `scoring_service.py`: review-density as the 2nd evidence axis in `apply_winner_evidence_tiebreak` — helpers `_youtube_source_enabled` (flag), `_youtube_views`, `_youtube_channel`, `_review_density_leader` (decisive-gap detector: floor `_REVIEW_DENSITY_MIN_VIEWS=10k`, ratio `_REVIEW_DENSITY_DOMINANCE_RATIO=3.0`). Fires ONLY inside the tie band when price authority does NOT discriminate (both/neither real price) and one product has decisively more YouTube attention. Price authority is checked first (stronger BH signal). Flag OFF → no-op.
- `response_builder.py`: `_review_density_candidate(products, winner_index)` reads L2's `reviews.youtube_review_signal` (flag-gated `_yt_signal_for`), normalizes the gap into the 0–1 candidate band, wired into `_build_factual_verdict`'s candidate list. `_format_line1` renders a `review_density` kind ("draws far more reviewer attention (~2.4M YouTube views, led by MKBHD)"). Local `_humanize_views` (no cross-module import; survives merge order). NEVER raw integer / "estimated".
- Both surfaces flag-gated on ENABLE_YOUTUBE_SOURCE (mirrors L2 rollback safety — 14d cache can carry a signal past a flag flip).

## L3.2 implementation (committed)
- `scoring_service.py`: module-level `apply_winner_evidence_tiebreak(products_data, result_products, overalls, naive_winner_index, win_margin, n_dims) -> (winner_index, winner_evidence)`; helpers `_has_real_price` (trust-set membership), `_product_all_missing`; const `_WINNER_TIE_BAND=8.0`. Wired into `compute_scores` right after the naive argmax; `winner_evidence` added to the return dict.
- Fires ONLY inside the 8pt tie band with exactly one real BH price (source_method in `_PRICE_TRUST_SET`) vs an estimate → tilts to real-data side + qualitative reason. Decisive margin / both-MISSING / neither-or-both-real → no tilt (argmax stands). Order-independent (kills the product_0 `.index(max())` bias).
- `winner_evidence` is qualitative strings only (no coefficients/caps/%) — test_winner_evidence_has_no_backend_internals pins it.
- L3.4 will read `scoring_result["winner_evidence"]` and surface it in scoring_v2.

## Edit surfaces (confirmed by code-read)
- `app/services/scoring_service.py`
  - `compute_scores()` L798-800: `winner_index = overalls.index(max(overalls))` — pure argmax, NO explicit tie-break. THIS is where L3.2's evidence-weighted tie-break lands (has `products_data` with `price.source_method`). Both orchestrator sites read `scoring_result["winner_index"]`, so one fix covers sync + streaming.
  - `_product_source_method()` L523 + `_PRICE_TRUST_SET` L501 already exist — reuse for "real vs estimated".
  - `MISSING_SCORE=50` L296; the both-MISSING overall tie → argmax returns 0 (product_0 bias). GUARD this path.
- `app/services/response_builder.py`
  - `_build_factual_verdict()` L559 + helpers (`_price_candidate` L394 / `_rating_candidate` L418 / `_top_dim_candidate` L441) — L3.3 review-density into line2 evidence.
  - `_build_scoring_v2()` L659 — emit `winner_evidence` here (L3.4).
- `app/services/extraction_service.py` — verdict prompt already gets L2's `_build_youtube_signal_block` (flag-gated). L3.3 confidence wiring may read it.

## L2 contract (for L3.3 — read off `feature/s3-l2-youtube`)
- `reviews.youtube_review_signal` dict, gated `ENABLE_YOUTUBE_SOURCE`. Fields seen in L2 code:
  `top_channel`, `top_video_title`, `total_views`, `video_count`, `video_url`, `review_count_signal`.
  Per-product surface: `response.reviews.products[i].youtube_review_signal`.
- L2 helpers: `extraction_service._extract_youtube_signal(product)`, `_humanize_count(n)`,
  `_build_youtube_signal_block(p1,p2)`; `review_service.youtube_source_enabled()`.
- Rollback-safe: flag OFF → None even with stale 14d cache. I MUST mirror this (flag-gate, never presence-gate).

## L3.1 AUDIT FINDINGS (S2 JSONL `.qa-bias-rerun/s2_exit_full200.jsonl`, read-only + gold `data/validation_gold_truth.json`)
- 200 rows; winner_pass 99/200 = **49.5%** (full) / 99/189 = 52.4% (clean 200-OK rows).
- Gold winner dist: **idx0=131, idx1=69**. ALWAYS-pick-product_0 baseline = **65.5%**.
- **We score 49.5% — BELOW the always-pick-0 baseline.** => the deterministic argmax is ACTIVELY NOISY, not just under-informed. Biggest single lever in S3.
- **74 of 159 clean rows (47%) with price_pass+factual_pass+specs≥.5 ALL GOOD still FAIL winner.** Many have specs=1.0 (perfect) yet winner wrong. So the winner failure is NOT primarily a data gap — the *pick* is wrong even with full data.
- `missing_dim_cells==0` rows (11) are total engine failures (price/specs/factual all 0, wscore 0) — those are L5.4's error rows, NOT "full data wrong winner".
- Winner-fail rate by category (worst→best): other 68% · electronics 62% · fashion 59% · makeup 56% · fragrances 50% · skincare 47% · grocery 44% · haircare 43% · supplements 27%.
- **Mechanism diagnosis (INITIAL — superseded by the deep mechanism report below):** tie-break coin-flip is secondary; dominant cause is weighted-dimension mis-weighting vs gold's qualitative rationale.

## DEEP MECHANISM REPORT (2026-06-13, team-lead top-priority ask — evidence-pinned)
**Q1 — gold idx0-skew is an AUTHORING ARTIFACT (mostly).** Gold winner == FIRST-NAMED product in "X vs Y" in 131/200 = 66% (per-cat 55–83%). The 69 idx1 rows have genuine rationales, so gold is fact-grounded, but the winner POSITION tracks author word-order. CONSEQUENCE: the 65.5% always-pick-0 "floor" is a MIRAGE (exploits word-order; an order-independent scorer can't/shouldn't reproduce it). Honest baseline for an order-independent 2-way pick ≈ 50%. So our 49.5% = UNINFORMED/RANDOM, NOT actively-perverse. My L3.2 order-independence is CORRECT — keep it.
**Q2 — the 47%-wrong-on-clean mechanism (pinned on 4 lane1 prod fixtures mapping to gold; 4/4 mismatch).** Two structural drivers, both in NORMALIZATION (not weights-as-such, not argmax bug, not random):
  1. NORMALIZATION AMPLIFICATION: `_normalize_dimension` = `30 + ratio*70` → the slightly-higher raw spec/price number gets 100, the other 30 — a 70pt gap from noise. iphone15: iPhone (gold winner "camera+ecosystem") performance 30 vs Galaxy 100 + value 30 vs 100 → 54.5 vs 89.0. Driver: Galaxy RAM 8GB/4000mAh > iPhone 6GB/3349mAh. Camera QUALITY + ecosystem (gold's reason) aren't rankable numbers → invisible to the spec scorer. SodaStream-vs-Aarke: 6/12 dims pinned at 30/100.
  2. VALUE/PRICE AXIS ANTI-CORRELATED WITH GOLD: gold's winner is the MORE EXPENSIVE product in 107/166 = 64% of priced rows. Our value_score gives the CHEAPER product up to 100 vs 30 (weight ~0.20). So value is ≤50/50 noise and actively WRONG on the 64% premium-justified majority. tomford/creed: Creed (pricier, gold winner) got wear_value 10 vs 82 → we picked Tom Ford; gold says Creed.
**Q3 SAFETY FACT:** eval price_pass/specs_score/factual_pass read overview.products + verdict text, INDEPENDENT of winner_index (eval_runner L560-590). A winner-discriminator change CANNOT regress price/specs/factual — winner-only blast radius.
**RECOMMENDATION sent to team-lead:** Option A (LOW RISK, bounded evidence-tilts, NO weight-table edit): A1 dampen `_normalize_dimension` spread (e.g. 30+ratio*70 → 45+ratio*40) to stop manufacturing 70pt swings; A2 neutralize the value/price anti-signal (value dim contributes to winner only within-tier / damp on large price gap). Option B (recalibrate CATEGORY_DIMENSION_WEIGHTS) = higher risk, PAUSED pending team-lead ruling. Option C (re-add product_0 tilt to chase the 66% artifact) = REJECT (fits noise, fails real users). **PAUSED on any scoring change pending ruling.**

## Discipline
- TDD: failing test → confirm fail → minimal impl → confirm pass → commit.
- Path-restricted commits; push-per-commit (`git push -u origin feature/s3-l3-winner-evidence`); NO stash.
- LANE_STATE.md updated every commit. ACK every team-lead message.
- **CREDIT GATE: no full-200 / live-Serper without team-lead GO** — fixtures + the S2 JSONL only.

## Log
- (init) Read §L3 + CLAUDE.md (scoring winner / factual_verdict / no_backend_internals) + L2 youtube contract (response_builder + extraction_service diffs on feature/s3-l2-youtube) + scoring_service.py (full) + response_builder _build_scoring_v2/_build_factual_verdict + orchestrator winner_index sites. Wrote LANE_STATE.
- L3.1 GREEN (diagnostic, no commit): winner axis is below the always-pick-0 baseline; 47% of full-data rows still mis-pick. Mechanism = noisy weighted argmax + secondary both-MISSING coin-flip. Sent to team-lead. Scaffolding L3.2.

## Commits
- 19f36d5 L3.2 evidence-weighted winner tie-break (price authority)
- d72b18e L3.3 review-density (YouTube) into verdict + winner tie-break
- 2f95c77 L3.4 winner_evidence surfaced in scoring_v2
- (this) L3.4 prod-fixture pins (lane1 captures)

## Test inventory (all GREEN, free-tier)
- tests/test_winner_evidence_tiebreak.py (7) — L3.2
- tests/test_review_density_verdict.py (7) — L3.3
- tests/test_winner_evidence_scoring_v2.py (6) — L3.4 incl. end-to-end chain pin
- tests/test_winner_evidence_prod_fixtures.py (10) — §L3.4 "pin with prod fixtures": all 9 lane1 captures → winner_evidence always-list; iphone15 decisive both-real-price capture → no spurious tilt
- 372+ existing scoring/verdict/response regression green; py_compile clean.

## Gate-readiness notes (for dispatcher)
- All L3 changes are ADDITIVE + behavior-gated: winner tie-break fires ONLY inside the 8pt tie band with discriminating real-price OR (flag-on) decisive review-density; outside that, argmax + responses are byte-identical to pre-L3. ENABLE_YOUTUBE_SOURCE OFF (prod default) → review-density paths are no-ops.
- Touches shared files: scoring_service.py (compute_scores winner block + new module helpers), response_builder.py (_build_factual_verdict candidate list + _build_scoring_v2). Overlaps L2 (response_builder reviews section — DIFFERENT functions; L2 added _youtube_signal_for_response + a reviews-section key, I added _review_density_candidate + _build_scoring_v2 winner_evidence — no line overlap) and L1 (none expected; L1 is source_router/price_service/structured_comparison). Merge order L3 before L1 (4th).
- I merge AFTER L2 (3rd). My L3.3 reads L2's reviews.youtube_review_signal by DATA SHAPE (no L2 helper import), so it lights up only once L2 is also merged + flag flipped — zero coupling risk at merge.

## Blockers
(none)

# LANE L3 — Winner-axis scoring / evidence

**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l3`
**Branch:** `feature/s3-l3-winner-evidence`
**Owner:** L3
**Merge order:** L5 → L4 → L2 → **L3** → L1 (I merge 4th, just before L1)

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

**ALL L3 TASKS COMPLETE (L3.1–L3.4) + ESTIMATE-DEMOTION (Ahmed directive 2026-06-13).** Ready for gate. Awaiting team-lead GO for smoke20 (CREDIT GATE).

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
- **Mechanism diagnosis:** tie-break coin-flip (both-MISSING → argmax→0) is REAL but secondary; the dominant cause is **weighted-dimension argmax mis-weighting** vs the gold's qualitative rationale ("camera + ecosystem"). L3.2 (price-authority edge) is a directional nudge that helps only when gold-winner == real-price side; L3.3 (review-density) adds the second evidence axis. Neither alone reaches gold's qualitative bar — the combined evidence tilt + guarding the noisy tie-break is the play.

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

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
- [ ] L3.3 review-density into the verdict (consume L2 youtube_review_signal + usage="review" Arabic sources into factual_verdict evidence + winner confidence — cited, never a raw score) — NEXT
- [ ] L3.4 `winner_evidence` surfaced in scoring_v2 (qualitative reasons ONLY — no coefficients/caps/% per no_backend_internals_in_reveals)

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

## Last commit
(none yet — diagnostic phase)

## Blockers
(none)

# Bundle E Manual QA Checklist (Ahmed's device)

Source: design doc `2026-05-13-results-quality-overhaul-design.md` § Section 1 (9-symptom table) + § Success Criteria + plan task list.

Test device baseline: Android (Ahmed's primary). iOS deferred — no Apple Developer enrollment yet. Ahmed runs through this list at the end of each phase. Tick boxes on PASS only — every FAIL becomes a `SEND-BACK` entry in `2026-05-13-bundle-e-qa-log.md`.

---

## Phase 0 — Hotfix sprint (Tasks 0.1, 0.2, 0.3 cherry-pick to main)

Original failure symptoms #6, #7, #8 from § Section 1 table:

- [ ] **History tap → no crash on a recent v2 row.** Pre-Bundle-E baseline: white screen + `Cannot read property 'comparison_id' of undefined`. Expected: Results renders fully.
- [ ] **History tap → empty-state card on a v1/legacy row.** Expected: card with title `results.emptyState.title` + CTA `results.emptyState.cta` ("Back to history"). No crash.
- [ ] **`testID="results-empty-state"` present** when result is undefined (confirmed by `findByTestId` in jest, also verifiable via React DevTools on device).
- [ ] **No "What's next?" button** anywhere on Results. Symptom #6 gone.
- [ ] **No "Save" button** on Results trailing actions row. Symptom #7 gone. Share remains.
- [ ] **i18n key removal** — `results.whatsNext` and `results.save` removed from both `en.json` and `ar.json`. Grep `grep -rn "results\.whatsNext\|results\.save" SmartCompareApp/src/` returns 0 lines.
- [ ] **No `common.or` literal** in auth divider (LoginScreen / RegisterScreen). Pre-existing pre-Bundle-E bug, folded in per design § Open Question 6. Expected: renders "or" (EN) / "أو" (AR).
- [ ] **Cherry-pick landed on main and deploy verified** — Task 0.3. Railway redeployed within 90s of merge. Frontend EAS update pushed to `preview` channel.

---

## Phase 1 — Backend foundations (Tasks 1.1–1.5)

- [ ] **`/api/v1/text/compare` response carries `scoring.dimensions[]` array** alongside legacy keys (`price_score`, `spec_score`). Backward-compat preserved per design § Decision 2.
- [ ] **`dimensions[]` always contains 3 core entries** (`is_core: true`): `price`, `reviews`, `value`. No comparison is allowed to omit any of these. Verified by `test_scoring_service.py` snapshot + integration test.
- [ ] **0–3 contextual dimensions** appended when both products have the data. `build`/`popularity`/category-specific keys. Never emitted when either product lacks the source data — i.e. NO empty bars.
- [ ] **`delta_text` field** is factual, no banned vocab. Validator rejects: `best`, `pick`, `excellent`, `great`, `recommend`, `winner`, `worst`, `better`, `worse`, `beats`, `smart`, `good`, `choose`.
- [ ] **`confidence` field** per dimension uses enum `high` | `medium` | `low`. `overall_confidence` removed from response top level (Decision 7).
- [ ] **Calibrated scores** in `overall_score.product_a` / `product_b` land in 70-95 range for above-average commercial products. `calibrate_score()` formula: `clamp(70 + (raw - 50) * 0.5, 60, 95)`.
- [ ] **100-comparison calibration validation** — re-running historical comparisons through new calibration produces ≥60% of overall scores in 80-89 band, <10% below 70. Run script: `scripts/calibration_validation.py` (Agent A authors).
- [ ] **Honesty guard** — products with all raw signals <40 still score <70 after calibration. Tested in `test_scoring_service.py`.
- [ ] **`build_factual_verdict()` deterministic** — produces 2 sentences max, zero banned vocab, pulls top-3 winning deltas. Tested in `test_response_builder.py`.
- [ ] **`fact_check.overall_confidence` removed** from the response payload (Decision 7). Per-dimension confidence is the only confidence surface.

---

## Phase 2 — Scatter-gather pipeline (Tasks 2.1–2.5)

Design § Decision 8 + § Decision 9.

- [ ] **`SCRAPING_MODE` env var honored** — `hard` (default for tester phase) fans out everything; `soft` fans out Firecrawl/Scrape.do conditionally on luxury domain or suspicious Serper.
- [ ] **First paint SSE event arrives ≤13s** on cold mouse-vs-keyboard query (the original failure case). Measured by `tests/perf/test_latency_bench.py`.
- [ ] **`settle_complete` SSE event arrives ≤25s** (hard cap). Stream closes regardless of in-flight work.
- [ ] **Quality ranker `select_best_price()`** picks highest-ranked source. Verified rank order matches `PRICE_SOURCE_RANK` in design § Decision 8.
- [ ] **Cancellation behavior** — when confirmed price (rank ≥85 or 2 sources agree) lands early, remaining price scrapers for that product cancel. Confirm via backend debug logs that only 2-3 scrapers ran end-to-end on a fast-confirm case.
- [ ] **Other fields (reviews, specs) keep running** independently after one product's price is confirmed.
- [ ] **New SSE event types emitted**: `first_paint`, `settle_update`, `settle_complete`, `confidence_upgrade`. Legacy `complete` event still fires at settle_complete (backward compat).
- [ ] **Frontend SSE handler merges `settle_update` payload in place** — late price swaps in via fade animation, no full re-render flash.
- [ ] **`confidence_upgrade` event flips dimension dot from gray to emerald** when a second source confirms.
- [ ] **Soft-mode credit conservation** — on a non-luxury cold query, Firecrawl + Scrape.do credit deltas are zero unless Serper returns suspicious data within 5s. Verify via `api_budget_service` counters before/after.
- [ ] **Circuit breaker still active** — 3 failures → 10-min cooldown unchanged from Bundle B/C/D.

---

## Phase 3 — Frontend rebuild (Tasks 3.1–3.10)

Design § Decision 3 + § Decision 5 + § Decision 7.

### Hero card

- [ ] **Two SVG radial rings** render side-by-side, 88px diameter, 8px stroke. (`HeroRings.tsx`)
- [ ] **Emerald fill on top-match ring**, neutral gray on the lower. **Never orange or red.** Visually confirmed on device.
- [ ] **Animated fill** 0 → score, 600ms ease-out, fires after the ~3.2s loading sequence completes.
- [ ] **Center label** shows the calibrated number then `/100` in smaller weight. No adjective ("Great", "Excellent") below.
- [ ] **"Top match" pill** above the higher-scoring ring (EN) / **"الأنسب لك"** (AR). Emerald bg, white text, no trophy icon.
- [ ] **Delta line** below rings reads e.g. `"BHD 30 less, 0.2★ higher, 12g lighter"` — sourced from top-3 winning `dimensions[].delta_text`. Minimum 1 delta shown.
- [ ] **Share icon** in top-right of hero card (repositioned from bottom row).

### Dimension bars

- [ ] **One row per dimension** from `dimensions[]` — 3 to 6 rows total. Original symptom #3 (empty Price/Specs/Popularity bars) gone.
- [ ] **Two horizontal bars per row** (one per product, with product column header above).
- [ ] **Bar color: emerald = higher score, gray = lower** — never orange.
- [ ] **Label** left in Inter Medium, **score number** right in tabular figures.
- [ ] **Low-confidence rows** render at 0.6 opacity + small gray "≈" prefix on the score number. No banner.

### Copy + framing (Decision 5)

- [ ] **No "Best Pick" / "Best Choice" / "Winner"** anywhere on Results. Replaced by "Top match".
- [ ] **No "Excellent" / "Great" / "Good" / "Smart pick"** evaluative adjectives. Number stands alone.
- [ ] **No "Choose this" / "Get this" / "This is right"** imperative endorsements.
- [ ] **No "Better" / "Worse" / "Beats"** — replaced by factual delta.
- [ ] **"Why we picked this" → "How they compare"**.
- [ ] **No "We recommend"** first-person endorsement — replaced by attributed ("Reviewers note…").
- [ ] **GPT-invented score numbers** like "wins with higher value score of 82.0" (symptom #4) — gone. Verdict pulled deterministically from `dimensions[].delta_text`.
- [ ] **`results.bestPick`, `results.smartPick`** removed from `en.json` + `ar.json`. New keys `results.topMatch`, `results.howTheyCompare`, `results.dataFreshness.settling` present.
- [ ] **ESLint rule `qaren/no-evaluative-copy`** loaded from `.copy-policy.json`. Build fails on banned-vocab violation. Verified by manually adding a banned word and confirming lint exit ≠ 0.
- [ ] **Per-product `best_for` lines** stay GPT-generated but contain zero numbers and no "loser" framing — both products get one.

### Removed elements

- [ ] **"Low confidence data" red pill at top of Results — GONE** by default (symptom #2). Only the subtle gray inline notice `results.dataFreshness.settling` appears at the bottom of bars when ≥2 of: no prices, no reviews, all-estimated specs.
- [ ] **"Default weights applied" footer text — GONE.**
- [ ] **"Save" + "What's next?" buttons — GONE** (already confirmed in Phase 0, re-check after frontend rebuild).

### Arabic / RTL

- [ ] Hero pill width `auto` not fixed — "الأنسب لك" (8ch) renders without truncation.
- [ ] All RTL mirrored correctly (`flexDirection: I18nManager.isRTL ? 'row-reverse' : 'row'`).
- [ ] EN/AR i18n parity strict — `npm run i18n:parity` returns equal key count.
- [ ] Arabic AI-proofread keys present (`scripts/i18n_parity_check.js` GREEN).

---

## Phase 4 — Integration + perf + final regression (Tasks 4.1–4.6)

### Integration tests (Task 4.1, `tests/test_bundle_e_integration.py`)

- [ ] E2E test: POST `/api/v1/text/compare` for mouse-vs-keyboard returns valid `dimensions[]` payload + calibrated scores in 70-95 band.
- [ ] E2E test: SSE stream for the same query emits `first_paint` → `settle_update`* → `settle_complete` in order.
- [ ] E2E test: warm cache hit returns within 3s.
- [ ] E2E test: history list does NOT contain v1 rows (`schema_version=1` filtered).
- [ ] E2E test: feedback endpoint still accepts the 4-field shape (`useful, comparison_id, mattered_most, change_suggestion`).

### Perf bench (Task 4.2, `tests/perf/test_latency_bench.py`)

- [ ] **P50 first-paint ≤ 10s** measured over 20 cold queries against Railway preview.
- [ ] **P95 first-paint ≤ 14s.**
- [ ] **P99 settle_complete ≤ 25s** (hard cap).
- [ ] Runbook `docs/runbooks/bundle-e-perf-bench.md` documents how to reproduce.

### Full regression gauntlet (Task 4.4)

- [ ] `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py` → **GREEN** (all pre-existing pytest tests pass, 144+ baseline from Bundle B/C/D).
- [ ] `python -m pytest tests/test_security_regression.py -v` → **GREEN** (98+ security tests, no regression).
- [ ] `cd SmartCompareApp && npx tsc --noEmit` → **0 errors**.
- [ ] `cd SmartCompareApp && npx eslint src/ --max-warnings 0` → **0 errors / 0 warnings** (including the new `qaren/no-evaluative-copy` rule).
- [ ] `cd SmartCompareApp && npx jest --watchAll=false` → **GREEN** (792+ jest tests + new HeroRings, DimensionBars, FactualVerdict, no-evaluative-copy suites).
- [ ] EN/AR i18n parity: keys count equal, 0 token mismatches.
- [ ] Snapshot tests for HeroRings + DimensionBars + FactualVerdict committed and stable.

### Final manual QA (Task 4.6 — Ahmed runs on his device)

Original 9-symptom regression table from § Section 1 — every row must produce the expected behavior on the **original mouse-vs-keyboard query**:

- [ ] **Symptom #1 (84.5s latency) — FIXED:** End-to-end perceived latency ≤15s. First paint ≤13s on cold cache.
- [ ] **Symptom #2 ("Low confidence data" pill) — FIXED:** Pill never appears by default. Subtle settling notice only when genuinely shaky data.
- [ ] **Symptom #3 (empty Price/Specs/Popularity bars) — FIXED:** All bars populated; dimensions with missing data simply not emitted.
- [ ] **Symptom #4 ("wins with higher value score of 82.0") — FIXED:** Verdict text contains zero numbers from a score.
- [ ] **Symptom #5 ("Best Pick" badge) — FIXED:** Replaced by "Top match" pill, no trophy icon.
- [ ] **Symptom #6 ("What's next?" NAVIGATE error) — FIXED:** Button removed entirely.
- [ ] **Symptom #7 ("Save" button redundant) — FIXED:** Button removed; History remains the canonical save surface.
- [ ] **Symptom #8 (History tap white screen) — FIXED:** No crash. Empty-state for v1 rows.
- [ ] **Symptom #9 (cross-category garbage) — FIXED:** Mouse vs keyboard produces a complete, coherent Results screen.

### Additional case sweeps (Decision 8 + Success Criteria)

- [ ] **Two iPhones (warm cache, same category)** — ≤3s first paint. Identical category produces a category-specific contextual dimension.
- [ ] **Luxury case (LV bag vs Hermès)** — Firecrawl tier fires within fan-out. Hard mode burns ~30 credits/comparison; soft mode ≤5.
- [ ] **Supplements (iHerb path)** — pricing intact post-refactor. Bahrain drug DB injection still happens for supplement queries.
- [ ] **Cold cache, no Firecrawl credits left** — pipeline degrades gracefully to Serper + curl_cffi + GPT, hard cap still respected.

### EAS update + soft-launch

- [ ] `eas update --branch preview --message "bundle-e results overhaul"` pushed. New OTA group recorded in CONTEXT_SESSION_LOG.
- [ ] APK build on Ahmed's device picks up the OTA on next open.
- [ ] No crash reports in Sentry within 24h of OTA.

---

## Append-only QA log reference

Every PASS box ticked here corresponds to a verification command run. Every FAIL → `SEND-BACK` entry in `2026-05-13-bundle-e-qa-log.md` with `file:line` + design-doc-quote citing the violated requirement.

`FINAL-SIGN-OFF` is granted only when **every box in this checklist is ticked** AND the QA log shows zero unresolved `SEND-BACK` entries.

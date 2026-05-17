# Bucket A Bugs — Design

**Date:** 2026-05-17
**Status:** Approved, ready for implementation plan
**Owner:** Ahmed + Claude
**Scope:** 4 user-visible bugs that make the app feel broken (not slow). Fixes ship together as Bucket A so D2 Section 3 can land against a known-good baseline.

---

## Goal

Restore feature correctness so the app stops feeling broken. Four bugs, all surfaced in Session 49 triage + the D1 ship verifier:

1. **History "No comparison loaded"** — tapping any History list item opens an empty Results screen.
2. **Camera Compare button doesn't fire** — capturing 2 products + tapping Compare silently discards the photos, no comparison runs.
3. **Asymmetric specs** — iPhone 17 shows Front Camera + Water Resistance values; Galaxy S25 Ultra shows N/A for the same public-knowledge specs.
4. **Currency conversion (SGD-as-BHD)** — luxury bench surfaced LV/Gucci prices of 2998/3050 BHD that are actually SGD values from Farfetch Singapore (no conversion applied). Other source currencies (JPY, CNY, INR) likely silently fail the same way.

**Hard constraint:** combined post-Bucket-A + D2-Section-3 cold mainstream wall time must land **10-15s** (down from 18-23s post-D1). Bucket A fixes must NOT regress wall time. The smart-fallback Serper query in Bug 3 runs in parallel with the existing Phase 2 stage to absorb its 1-3s cost into idle wall time.

---

## Out of scope (explicit non-goals)

- **D2 Section 3** (prompt caching + combine specs+reviews) — separate design doc, written after Bucket A ships per the agreed sequence A → D2 → B → C.
- **Bucket B** (two-input text/URL UX redesign) — separate brainstorm, 4-Opus team scope.
- **Bucket C** (scoring/personalization tuning, pros/cons quality) — depends on D2 landing first.
- **Backend list endpoint bloat fix** (hydrate `full_response` into `/api/v1/comparisons/history` list response) — rejected: 20+ history items × ~15KB each = 300KB list payload; current summary-only design is intentional.
- **Per-region currency display for non-Bahrain testers right now** — the fix wires region-aware conversion correctly, but Ahmed is the only tester pre-launch and is in Bahrain → practical display stays BHD for the next few weeks. Future GCC testers automatically get their region's currency.
- **Adding ALL world currencies to the rate table** — only GCC targets (6 currencies) + most-common source currencies that have actually appeared in scraped data (USD, EUR, GBP, SGD, JPY, CNY, INR). Other exotic currencies stay rejected at the price source level.

---

## Bug 1 — History "No comparison loaded"

### Root cause

- `SmartCompareApp/src/screens/HistoryScreen.tsx:134` passes `item.full_response` via React Navigation params to `Results`.
- `SmartCompareApp/src/screens/ResultsScreen.tsx:102` reads `route.params.result`; renders empty state at lines 381-407 when missing.
- Backend `/api/v1/comparisons/history` list endpoint returns summary fields only (`product_names`, `created_at`, `query`, `id`) — NOT `full_response`. Comment at `HistoryScreen.tsx:163-173` documents this exact gap; the fix was started but never completed.
- Result: `item.full_response` is `null` → Results renders empty state → user sees "No comparison loaded".

### Fix

**Fetch on mount in ResultsScreen** when `route.params.result` is missing AND `route.params.comparison_id` is present:

1. Add `comparison_id` to the navigation params HistoryScreen passes (alongside removing `full_response: item.full_response`).
2. In ResultsScreen `useEffect`, detect the case `!result && comparison_id` → call `getComparison(id)` via api.ts → set local state with the returned full payload.
3. While fetching, render the existing `LoadingRings` + skeleton state (the same one HomeScreen uses) with a **min-display floor of 1.2s** per the Qaren UX redesign brand-moment requirement → `RevealBurst` → render the cached comparison.
4. On 401: clear session + redirect to auth (existing pattern).
5. On 404: render the existing "comparison not found" empty state with "Back to history" CTA (already in code, just unreachable for non-null `result`).
6. On other errors: render the same empty state + Sentry capture.

### Test gates

- Unit: `tests/test_history_routes.py` — pre-existing endpoint coverage. Add 1 test asserting `GET /api/v1/comparisons/{id}` returns full payload with `specs`, `reviews`, `scoring`, `metadata` keys.
- Frontend manual: tap any history item → see loading animation → see comparison render with full data. Tap a deleted/expired comparison ID → see "not found" empty state with CTA.
- No new backend code (endpoint exists); frontend ~50 lines in ResultsScreen + 5 lines in HistoryScreen.

---

## Bug 2 — Camera Compare button doesn't fire

### Root cause

- `SmartCompareApp/src/screens/ScanCameraScreen.tsx:147-156` defines `onCompare()` which navigates to `Results` with `{vision_products: visionProducts}` (array of photo URIs).
- ResultsScreen NEVER consumes the `vision_products` param — only handles `route.params.result`. Photos silently discarded.

### Fix

**ResultsScreen detects `vision_products` on mount → calls identify+stream itself** (mirrors HomeScreen's streaming pattern for consistency):

1. In ResultsScreen `useEffect`, detect the case `!result && vision_products?.length === 2` → call the image-comparison API endpoint via api.ts.
2. Identify backend endpoint: `POST /api/v1/image/identify` (or whichever exact route in `image_routes.py` handles two-photo identify-then-compare). If a single endpoint chains identify+compare, use it. Otherwise: identify first → use the returned product names to call the regular streaming text-compare endpoint with `vision_products` flag so backend's `_fetch_product_data` knows to skip parsing.
3. Use the same `StreamingProductCard` stage-gated UI (init→title→specs→prices→reviews→verdict) as text-search comparisons. SSE events from `/api/v1/text/compare/stream` feed the stages naturally.
4. While streaming: same haptics on stage transitions per the Qaren UX redesign vocabulary `{chip: light, stage: light, winner: medium}`.
5. On any error during identify or stream: existing parseApiError flow + Sentry capture + retry CTA.

### Test gates

- Unit: `tests/test_image_routes.py` — confirm the endpoint accepts 2 photo URIs and returns identified product names. Add 1 test asserting the response shape matches what frontend expects.
- Frontend manual: capture 2 products → tap Compare → see instant nav to Results → see theatrical loading → see comparison render with both products identified.
- ~50-80 lines of frontend in ResultsScreen (parallel branch to existing text-comparison logic); backend likely needs no changes if image endpoint already exists.

---

## Bug 3 — Asymmetric specs (S25 N/A where iPhone has data)

### Root cause

- `app/services/extraction_service.py:176-235` extraction prompt has a contradiction:
  - Line 188: template forces every schema key to `null` (so GPT sees the shape).
  - Line 209: system prompt says "Only include fields that are GENUINELY RELEVANT" and "Omit irrelevant fields rather than writing N/A".
- GPT obeys the system instruction → omits fields it doesn't have data for. For iPhone 17, GPT has Center Stage in training data; for S25 Ultra, thin Serper snippets at extraction time → GPT plays safe → omits.
- Frontend treats missing keys as "N/A" → asymmetric display.

### Fix — hybrid strategy with parallel smart-fallback

**Three coordinated changes:**

#### 3a. Remove "omit irrelevant" for schema-listed fields (~5 lines)

Replace the contradictory system-prompt instruction with: *"For fields explicitly listed in the schema (e.g. front_camera, water_resistance, processor), you MUST attempt to provide a value. Use snippets first, training data as fallback. Only return `null` if you genuinely don't know."*

A field appearing in `CATEGORY_SPEC_SCHEMAS[category]` is BY DEFINITION relevant — that's why it's in the schema. The "omit irrelevant" instruction should only apply to fields OUTSIDE the schema (which GPT might invent for niche specs).

#### 3b. Allow GPT training-data fallback for schema fields with confidence marker (~10 lines)

When GPT fills a schema field from training data instead of snippets, stamp `_field_confidence[key] = "training_data"` in the result. Frontend shows a subtle ℹ️ tooltip on training-data values: "This spec is from general product knowledge, not the current search results."

Snippet-derived values get `_field_confidence[key] = "snippet"` (existing path).

#### 3c. Smart-fallback Serper queries for STILL-missing critical schema fields (~30-50 lines)

After 3a + 3b, identify schema fields still `null` for either product. Critical fields are a category-specific subset (e.g. for electronics: `front_camera`, `rear_camera`, `processor`, `ram`, `battery`, `water_resistance` — NOT every field). Run ONE targeted Serper query per missing field (max 2 queries per product to cap cost), then call GPT again to extract JUST those fields. Cache result so subsequent comparisons of the same product reuse the filled values.

**Critical wall-time optimization:** run smart-fallback queries **IN PARALLEL with Phase 2 (reviews + rating)** via `asyncio.gather`. Phase 2 already takes ~3.3s p50 — if fallback completes within that window, zero added wall time. Cap fallback with `asyncio.wait_for(timeout=3.0)` — if it doesn't finish, skip it gracefully (gap stays unfilled this run; gets filled on next comparison after cache hit on Phase 1).

### Quality fallback

If after all 3 sub-fixes a field is STILL `null`, frontend hides the row entirely (don't display "N/A" — legitimate "we don't have this data" signal). Cleaner than scary "N/A" text.

### Test gates

- Unit: `tests/test_extraction_service.py` — add 3 tests:
  1. Schema field marked "must attempt" gets non-null value when training data has it (mock GPT returns training data).
  2. `_field_confidence` dict present in response with `snippet` / `training_data` markers.
  3. Smart-fallback fires for critical missing field but not for non-critical missing field.
- Unit: `tests/test_structured_comparison_service.py` — add 1 test asserting smart-fallback runs in parallel with Phase 2 (mock both, assert total wall time = max(phase2, fallback), not sum).
- **Spec parity regression test:** for the iPhone 17 vs Galaxy S25 Ultra baseline at `tests/fixtures/comparison_baseline_d2.json`, run post-Bucket-A and assert:
  - Both products have `front_camera` populated (not null, not "N/A").
  - Both products have `water_resistance` populated.
  - No baseline-present field disappears (100% key parity).
  - Phase 2A timing data (cached in design doc) — post-fix total wall ≤ pre-fix total wall + 0.5s (allow small buffer for smart-fallback parallel runtime variance).
- Frontend manual: re-run iPhone 17 vs Galaxy S25 Ultra → verify both phones show Front Camera + Water Resistance values; tooltip appears on training-data values.

---

## Bug 4 — Currency (SGD-as-BHD + missing exotic source currencies)

### Root cause

- `app/services/price_service.py:203-211` `_convert_to_bhd()` uses a hardcoded rates dict that's missing SGD.
- `app/services/exchange_rate_service.py:18-28` `FALLBACK_RATES` dict also missing SGD.
- When a non-listed currency comes in: `rates.get('SGD', 1.0)` returns 1.0 → no conversion → price displayed in source units with target currency label. **Silent failure** — no exception, no log warning.
- Affected: SGD (confirmed), JPY, CNY, INR (likely), GBP (partial).

### Fix — region-aware conversion + defensive currency hardening

**Three coordinated changes:**

#### 4a. Add missing source currencies to FALLBACK_RATES (~10 lines)

Add to `FALLBACK_RATES` in `exchange_rate_service.py` (BHD-anchored rates as of 2026-05-17, refresh during fix):
```python
"SGD": 0.282,  # 1 SGD = 0.282 BHD
"GBP": 0.476,
"JPY": 0.0025,
"CNY": 0.052,
"INR": 0.0045,
```

#### 4b. Region-aware target conversion (~20 lines)

`_convert_price_to_region_currency(price_dict, region_code)` — converts FROM scraped currency TO the region's native currency:

- `bahrain` → BHD (default; existing path)
- `saudi_arabia` → SAR (already in FALLBACK_RATES)
- `uae` → AED (already in)
- `kuwait` → KWD (already in)
- `qatar` → QAR (already in)
- `oman` → OMR (already in)

Use `exchange_rate_service.get_rate(from_currency, to_currency=region_native)`. Region → native currency mapping lives in a constant in `exchange_rate_service.py` for reuse.

#### 4c. Strict-fail when conversion rate is missing (~5 lines)

If `get_rate(X, Y)` returns `None` OR `1.0` for currencies that AREN'T the same:
- Log a clear warning: `[CURRENCY] No rate found for {X} → {Y}, REJECTING price (would silently display wrong value)`.
- Drop that price candidate entirely (don't return it from `_get_price`). Let the next-best source in the cascade try.
- If ALL prices fail conversion, Tier 3 GPT estimate fires as the safety net.

**Better to show no price than wrong price** — per CLAUDE.md price philosophy: "MOST AUTHORITATIVE, not LOWEST reasonable."

### Test gates

- Unit: `tests/test_exchange_rate_service.py` — add tests asserting each new currency converts within ±5% of a known reference rate (use frankfurter.app live for the test if available, else hardcoded expected values).
- Unit: `tests/test_price_service.py` — add tests:
  1. SGD-priced source converted to BHD when region=bahrain.
  2. USD-priced source converted to SAR when region=saudi_arabia.
  3. Exotic currency without a rate → price REJECTED (not returned with `source_method=local_<X>`).
- **Regression test:** re-run LV Neverfull vs Gucci Marmont luxury bench → verify returned prices are in BHD range (1000-3000 BHD for typical luxury handbags), NOT 2998+ BHD which would be SGD-mislabeled. Direct counter-test for the bug discovered in Task 8.
- Frontend manual: comparison results show BHD prefix consistently; no "BHD 2998" for obvious-luxury-bag scenarios.

---

## Sequencing

Strict sequential because Bug 3 changes Phase 1 extraction behaviour, and Bug 1 / 2 change ResultsScreen consumption of route params — both need careful test coverage and the fixes touch overlapping files where conflicts would otherwise occur:

1. Write + commit this design doc (now).
2. Write implementation plan via `writing-plans` skill (next).
3. Execute Bug 4 first (trivial, lowest risk, builds Railway confidence).
4. Execute Bug 1 (small, frontend-only, well-defined).
5. Execute Bug 2 (medium, frontend-heavy, mirrors Bug 1's pattern).
6. Execute Bug 3 (medium, backend + tricky parallelism + quality regression gate — last because the spec-parity fixture lets us prove it didn't break anything).
7. Combined verification bench: 3 cold mainstream + 1 luxury + manual frontend tap-through history + manual camera capture-and-compare.

After Bucket A ships:
8. Brainstorm + execute D2 Section 3 (prompt caching + combine specs+reviews). Target: cold mainstream p50 ≤ 13s, p95 ≤ 17s. Quality gate: spec parity vs the freshly-captured baseline at `tests/fixtures/comparison_baseline_d2.json` (updated mid-Bucket-A after Bug 3 fix lands so the baseline reflects post-Bug-3 keys).

---

## Combined Bucket A success criteria

- All 4 bugs fixed; manual UX verifications pass.
- Spec-parity regression test green: iPhone vs S25 Ultra has all critical schema fields populated on BOTH products.
- Cold mainstream total wall time ≤ post-D1 baseline + 0.5s tolerance (smart-fallback runs parallel, shouldn't regress).
- Luxury bench prices in plausible BHD range (NOT 3000+ BHD for a handbag).
- All unit tests green (≤17 pre-existing failures from Session 47/48 baseline, no new failures).
- Sentry has no new error classes appearing in 1h post-deploy.

## Rollback playbook

Per fix:
- Bug 4 (currency): pure data change + helper function. Revert with `git revert <bug4-commit>` if conversion math is wrong → no Railway impact since old behavior was "silently wrong" which is what we'd return to.
- Bug 1 (history): frontend-only. Revert `git revert <bug1-commit>` → users see "No comparison loaded" again but no data corruption.
- Bug 2 (camera): frontend + possibly api.ts. Revert → camera Compare goes back to silent failure, same as today.
- Bug 3 (asymmetric specs): backend extraction prompt + smart-fallback. Highest risk because it changes Phase 1 wall behaviour. Revert with `git revert <bug3-commit>` → specs go back to asymmetric, mainstream wall returns to pre-fix.

For ANY rollback: `git push origin main` triggers Railway redeploy; verify `/health` 200 + run targeted bench to confirm pre-deploy behavior restored.

## Open risks

- **Bug 2 backend endpoint shape unknown.** Need to confirm `/api/v1/image/*` route accepts 2 photo URIs and returns identifiable product names compatible with the text-comparison streaming flow. If the existing image endpoint only handles 1 photo at a time, frontend needs to call it twice + assemble. Mitigation: read `app/api/image_routes.py` before implementation; if shape doesn't match, add a small backend wrapper endpoint that takes 2 URIs.
- **Bug 3 smart-fallback timing may exceed Phase 2 wall time on slow Serper days.** 3s cap mitigates worst case but a borderline-slow run could add 0.5-1s anyway. Acceptable per the +0.5s tolerance in success criteria.
- **Bug 3 GPT training-data values may be incorrect for products released after GPT's training cutoff.** S25 Ultra launched Jan 2025; well within gpt-4o-mini's late-2024 cutoff window. But future products (S26 in 2027) would fail. Mitigation: smart-fallback Serper queries compensate; `_field_confidence` marker lets us track this in analytics if it becomes an issue.
- **Bug 4 frankfurter.app fallback may rate-limit.** `exchange_rate_service` already caches 24h via Redis; new currencies inherit that caching. Worst case: cold load fails → FALLBACK_RATES kick in. Already handled.
- **Combined Bucket A wall time discipline.** If any fix accidentally adds >0.5s, that eats into D2's headroom for hitting the 10-15s target. Mitigation: each fix has explicit timing guard in tests where applicable.

---

## References

- Session 49 triage and brainstorm transcript
- Bug 1 surface: `SmartCompareApp/src/screens/HistoryScreen.tsx:134,163-173`, `SmartCompareApp/src/screens/ResultsScreen.tsx:102,381-407`
- Bug 2 surface: `SmartCompareApp/src/screens/ScanCameraScreen.tsx:147-156,213-224`, `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Bug 3 surface: `app/services/extraction_service.py:176-235` (esp. lines 188, 209), `app/services/structured_comparison_service.py::_fetch_product_data` (Phase 2 gather around line 990)
- Bug 4 surface: `app/services/price_service.py:203-211`, `app/services/exchange_rate_service.py:18-28`
- Spec parity baseline: `tests/fixtures/comparison_baseline_d2.json` (captured pre-D1, committed `5aa5c22`)
- D1 verified post-deploy: 85s → 34s luxury, real `page_scrape_jsonld` prices (commit `5e2e79b` on prod)
- Phase 2A diagnostic data: `docs/plans/2026-05-17-comparison-speed-fixes-design.md` "Phase 2A Diagnostic Results" appendix (commit `9a87f61`)
- Qaren UX redesign brand-moment requirements: CLAUDE.md "Qaren UX Redesign" section (StreamingProductCard stages, LoadingRings, RevealBurst, 1.2s min-display floor, haptic vocabulary)

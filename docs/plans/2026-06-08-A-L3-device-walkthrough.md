# Lane A-L3 Device Walkthrough — Sprint A Mobile Wiring

**Owner:** L3-fe-mobile (executed by Ahmed on real device)
**Plan:** `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md` § L3.9
**Sprint:** A — Backend Comparison Engine Overhaul

This is the step-by-step manual device walkthrough covering all 4 design
screens (1: hero pair + verdict + dim bars + confidence pills; 2: reviews
accordion w/ retailer quotes; 3: pros/cons w/ winner-star; 4: specs table
w/ per-row emerald) plus the 88s wall-time instrumentation tag inspection
in Sentry.

**Pre-requisite:** Sprint A merged + OTA fired to `preview` channel.
Verify with `eas update:list --branch=preview | head -5` showing the
A-Merge group ID before starting. Fresh launch = bundle propagates on
second relaunch (two-launch propagation gotcha noted in CLAUDE.md).

---

## Surfaces under test

The eight surfaces under test by lane:
- L3.1 — variant string on each product card
- L3.2 — per-row emerald winner highlighting in specs table
- L3.3 — winner-star (★) on the pros/cons winning column
- L3.4 — per-retailer review quote cards (Amazon / Noon / X)
- L3.5 — confidence pills + bottom-sheet "What we know" with factual lines
- L3.6 — dimension bars use category-aware labels + honor `dim.winner`
- L3.7 — wall-time Sentry tags (`wall_time.{stage}_ms`) on
  `comparison_wall_time` info event

The supporting backend contract (L1) ships:
- `overview.products[i].variant`
- `specs.specs_comparison: [{field, p0_value, p1_value, winner}]`
- `reviews.products[i].retailer_quotes: [{retailer, rating, text}]`
- `scoring_v2.dimensions: [{key, label, score_a, score_b, delta_text, winner, ...}]`
- `scoring_v2.confidence_legs: {price, reviews, specs}`
- `scoring_v2.confidence_details: {price?: [], reviews?: [], specs?: []}`
- `scoring_v2.factual_verdict: {line1, line2}`

---

## Procedure

### Step 0 — Bundle sanity

1. Open Qaren on the test device. Should land on Home.
2. Force-close + reopen Qaren (Bundle propagation second launch).
3. Confirm app version shown in Profile → Settings matches the latest EAS
   build expected by the merge gate. If older bundle: wait 30s, repeat.

### Step 1 — Trigger an electronics comparison

1. Tap a category chip → Electronics.
2. In TwoInputShell type:
   - Product A: `iPhone 15`
   - Product B: `Galaxy S24`
3. Tap Compare CTA.
4. Loader plays. Note the time-to-results subjectively (the L3.7
   instrumentation will give exact numbers in Sentry).

### Step 2 — Screen 1 (Hero pair + verdict + dim bars + confidence pills)

**Hero pair**:
- [ ] Both product cards render with image, brand sub, **variant caption** (e.g. "128GB · Black" — L3.1 contract).
- [ ] Winner card has the emerald border ring + slight scale-up post-reveal.
- [ ] "vs" pill sits centred between the two cards.

**Verdict block**:
- [ ] Eyebrow "WHY WE PICKED THIS" (or i18n equivalent).
- [ ] FactualVerdict carries TWO lines (line1 + line2 — L1.5 + L3.6 contract).
- [ ] No banned vocab ("best", "better", "great", "winner", "excellent"). If line1 or line2 violates, the component renders a 0-sized fail-loud guard rather than text.

**Dimension bars**:
- [ ] 4 rows minimum, labels match electronics-specific dims (Camera, Battery, Performance, Value — NOT generic Price/Reviews).
- [ ] Bar fill on each row is emerald for the higher score side; gray for the lower side.
- [ ] "BHD 30 less" or equivalent delta_text shows under the Value row.

**Confidence pills**:
- [ ] 3 pills visible (💰 Price, ⭐ Reviews, 📋 Specs).
- [ ] Tap each pill → bottom sheet slides up with 2-3 factual lines (L1.6 + L3.5 contract).
- [ ] Sheet copy never references "estimated" word (forbidden per `feedback_no_estimated_word_in_ui.md`).

### Step 3 — Screen 2 (Reviews accordion w/ retailer quotes)

1. Scroll down to "Dig deeper" → tap Reviews row.
2. Accordion expands.

**Per-product review block**:
- [ ] Product name shown.
- [ ] Consensus sentence below the name.
- [ ] Up to 3 highlight bullets with +/− sentiment prefix.

**Retailer quotes (L3.4 contract)**:
- [ ] 3 small cards under each product (Amazon / Noon / X — order may vary based on backend population).
- [ ] Each card shows the retailer in ALL CAPS (e.g. "AMAZON").
- [ ] Optional ★ rating (e.g. "★ 5") on the right.
- [ ] Quote body text on a separate line.
- [ ] Tapping does nothing — these are passive surfaces.

### Step 4 — Screen 3 (Pros/Cons w/ winner-star)

1. Tap Pros & Cons row in the accordion.

- [ ] Two columns, one per product.
- [ ] Emerald ★ prefix on the winning product's column header only (L3.3 contract).
- [ ] No ★ on the loser column.
- [ ] Pros listed with `+` prefix (emerald or primary text); cons with `−` prefix (secondary text).

### Step 5 — Screen 4 (Specs table w/ per-row emerald winner)

1. Tap Specs row in the accordion.

- [ ] "Highlights" mini-section above the spec table (when backend supplies `spec_advantages`).
- [ ] "Show only differences" Switch toggle.
- [ ] Per-row layout: spec key (UPPERCASE) on left, two value cells on right.
- [ ] **Per-row winner emerald** (L3.2 contract): the winning side's cell paints `colors.accent` + 700 weight; the loser stays default text color. For ties (e.g. storage = 128GB on both), BOTH cells stay default.
- [ ] em-dash ("—") renders for missing/N/A values.

### Step 6 — Wall-time instrumentation (L3.7)

1. Open Sentry web UI → Project: `qaren-rr/react-native`.
2. Filter: `is:unresolved`, event type: `info`, message: `comparison_wall_time`.
3. Locate the event from the comparison just run (look for `wall_time.started_at` close to the timestamp).

**Expected tags on the event**:
- [ ] `wall_time.ttfb_ms` — number string (ms since start)
- [ ] `wall_time.first_card_visible_ms` — typically within ~50ms of ttfb (cards mount synchronously after result settles)
- [ ] `wall_time.all_cards_visible_ms` — same as first_card_visible currently
- [ ] `wall_time.ready_celebration_ms` — ~800ms after first_card_visible (reveal delay)
- [ ] `wall_time.user_tappable_ms` — ~420ms after ready_celebration (spring settle)
- [ ] `wall_time.started_at` — absolute Date.now() at Compare tap

**Diagnose**: if `user_tappable_ms` > 90,000 (the 88s gap mentioned in Bundle E device walks), surface as a follow-up. The most likely sources to investigate next:
- a) SSE stream took unusually long on backend (compare against backend `metadata.stage_timings_ms` if `DEBUG_STAGE_TIMINGS=true` is on Railway)
- b) MinDisplay floor (1.2s) added to a Home loading state that already fired
- c) Theatrical loader animation block in HomeScreen->Results transition

### Step 7 — Edge cases

7a. **Tie spec winner**: trigger a comparison where backend emits `winner: null` for some spec row (e.g. same storage). Expect both cells gray.

7b. **Missing retailer_quotes**: trigger a comparison where `retailer_quotes` is absent (legacy data or low-confidence categories). Expect the retailer-quote block to disappear gracefully. Reviews accordion still works, only the quote cards are gone.

7c. **Legacy variant absent**: open a comparison from History (pre-Sprint A row). Expect product card to render without the variant caption (no empty line, no crash).

7d. **dim.winner override path**: hard to trigger in production — backed by `__tests__/ResultsContent.v2Wiring.test.tsx` test 'honors dim.winner override on per-dim emerald paint (L3.6 contract)'. The runtime path activates when L1 emits a `winner` index that disagrees with `score_a > score_b` (e.g. cross-tier value framing). In production, dim.winner usually agrees with score comparison so the L3.6 visual matches both paths.

7e. **Confidence pill hidden**: trigger a comparison where one of the prices is `source_method: estimated` (Tier 3 GPT fallback). Expect the Price pill to be ABSENT (not just muted) per spec § 5c. Reviews + Specs pills still visible.

### Step 8 — Localization (Arabic)

1. Switch language: Profile → Settings → Arabic.
2. Re-run the iPhone 15 vs Galaxy S24 comparison.
3. Spot-check that all 7 surfaces above still render correctly in RTL:
   - [ ] Variant caption right-aligns naturally
   - [ ] Emerald winner cell still paints (RTL flips column position, not winner ID)
   - [ ] Star prefix sits to the right of the product name in RTL
   - [ ] Confidence pills row reverses order
   - [ ] No forbidden Arabic vocab (`تعذر`, `فشل` per CLAUDE.md copy contract)

---

## Pass/fail criteria

**PASS:** all 8 surfaces (L3.1-L3.7 + RTL) check out on the device.
Two findings caught in Finding 1/2 of `2026-06-08-A-L3-cross-qa-of-L4.md`
(cohort coverage + matrix automation) do not block A-Merge.

**FAIL (any of):**
- Variant caption renders the literal `null` or `undefined`.
- Spec winner cell paints emerald on the LOSER side (cells inverted).
- Pros/cons star renders on both columns or wrong column.
- Retailer quote block crashes when `retailer_quotes` is missing.
- Confidence sheet shows the word "estimated" anywhere.
- Sentry `comparison_wall_time` events fail to surface OR are missing
  one or more of the 5 stage tags.

## Recovery on FAIL

1. Note which surface failed + which step number.
2. If a backend contract is wrong (L1's `winner` field, etc.), tag L1 + L4
   not L3 — L3 is a passive consumer.
3. If L3 wiring is wrong, the relevant test should have failed. Re-run
   `npx jest __tests__/ResultsContent.v2Wiring __tests__/components/ResultsAccordion.v2 __tests__/wallTimeInstrumentation` from `SmartCompareApp/` worktree to confirm.
4. Open a follow-up issue with the failure screenshot + Sentry event link.

---

## Test data shortcuts

A canned 50-query Bahrain test matrix (L4.3) lives at
`data/validation_gold_truth.json`. To re-run any of those queries on the
device, copy the `query` field into TwoInputShell or trigger via the
`scripts/run_validation_matrix.py` CLI from the backend worktree.

The frontend test fixture (consumed by Jest, not the device) lives at
`SmartCompareApp/__tests__/fixtures/v2_response_electronics.json` and
mirrors what L1's backend should produce for the iPhone 15 vs Galaxy S24
electronics query.

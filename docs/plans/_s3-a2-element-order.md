# Bundle E S3 — A2 element-order checklist

> Contract with peer-QA A1. Lane A2 (`fe-results-history`).
> Sources of truth:
> - `docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx` (1-410)
> - `docs/claude-design-handoff/ui_kits/mobile/HistoryScreen.jsx` (1-388)

State legend:
- ✓ = present in current `.tsx` in correct order
- ↕ = present but wrong order / position
- ✗ = missing — must be added
- 💀 = present in `.tsx` but NOT in JSX → DELETE in REWRITE

---

## ResultsScreen (JSX 1-410, current `.tsx` 1956L)

JSX top-down element order (consumed via `QarenResultsScreen` JSX:286-407):

| # | Element | JSX line | Current `.tsx` state |
|---|---------|----------|----------------------|
| 1 | Header bar (back chevron `bg.secondary` 36×36 + TopMatchBadge centered + share button `bg.secondary` 36×36) | 297-311 | ↕ Header exists 603-613 but center slot is `<Text>headerTitle "A vs B"</Text>` — must replace with `<TopMatchBadge />` |
| 2 | Hero — two ProductCards side-by-side with absolute `vs` pill centered on the divider | 316-333 | ↕ ProductsRow exists 627-764 with full Card variants + scoreBadge + bestPickBadge + valueBadge — JSX has lean image-square + name + sub + price; runner-up plain, winner emerald accentLight bg + 2px accent border. **No "vs" divider pill in `.tsx`. ScoreBadge + bestPickBadge are 💀 per JSX which uses TopMatchBadge in header for that role.** Per A2 plan: KEEP the lean composition + slot the `image_url` placeholder for A4 to wire. |
| 3 | Section "Why this fits you" — eyebrow + 18px verdict body + 13px secondary caption ("Weighted ↑ X ↑ Y...") | 336-346 | ↕ `results.whyWePicked` translated to "Why this fits you" via Decision 5 (Phase 3 test); section exists 770-777 but uses `styles.sectionTitle` + verdictText + tradeoffNote — JSX uses inline eyebrow style + bold pretty-wrap p + secondary caption. Re-paint per JSX. |
| 4 | DimensionBars section (3 bars: Camera, Battery, Price) — eyebrow not present in JSX wrapper; bars labelled inline | 349-353 | ↕ `<DimensionBars dimensions={scoring_v2.dimensions} winnerIndex={...} />` exists 1162-1166 inside scoring_v2 wrapper. JSX places bars OUTSIDE the wrapper, immediately after the verdict — but bars need scoring_v2 to render. **Decision: bars stay inside scoring_v2 wrapper for data dependency; visual order matches JSX once wrapper is positioned after verdict.** |
| 5 | Section "What we know" — eyebrow + 3 ConfidencePills (Price · High / Reviews · Medium / Specs · High) | 356-365 | ↕ `<ConfidencePills>` already exists 1126-1133 in scoring_v2 wrapper. JSX has eyebrow `What we know` heading above the pill row — must add. |
| 6 | Cohort line — single-line softened framing ("2,000+ shoppers in Capital leaned the same way") in `bg.secondary` rounded-12 box | 367-377 | ↕ `<CohortBadge>` exists 783-789 as separate slot — JSX shows inline pill-shape paragraph. **Decision: keep CohortBadge component but verify it renders as a single-line softened paragraph per Bundle E S1 spec (already done).** |
| 7 | `<DetailsAccordion>` — collapsible "Dig deeper" with Reviews + Pros & Cons + Specs panels | 379-381 (+ 105-211 helper) | ✗ Current `.tsx` has 3 separate sections: § 7 Reviews `<ReviewCard>` (964-1083) + § 8 Specs accordion (881-961) + § 8a scoring_v2 hero — **JSX collapses these into ONE DetailsAccordion with 3 toggles**. This is the largest structural change. Build `ResultsAccordion` component. |
| 8 | Feedback prompt — "Was this helpful?" card with 3 chips Accurate / Detailed / Fast | 383-404 | ↕ `<FeedbackCard>` already exists 1243-1247. Verify chip set matches JSX (Accurate/Detailed/Fast). |
| 9 | (NO § "What's next?" CTA, NO actions row, NO metadata footer per JSX) | n/a | 💀 `<View style={styles.actionsRow}>` (1255-1260) Share button below feedback — JSX has no second Share affordance; the header share button is the only one. **DELETE.** 💀 `metadataSection` (1262-1277) — JSX has no metadata footer. **DELETE.** |
| 10 | (No category-switched banner in JSX) | n/a | 💀 `<View style={styles.categorySwitchedBanner}>` (615-623) per `memory/feedback_no_info_banners.md` — page-level info banner FORBIDDEN. **DELETE.** |

### DELETE list — ResultsScreen REWRITE
- 💀 `categorySwitchedBanner` View 615-623 (forbidden info banner)
- 💀 Per-product `scoreBadge` 666-673 (winner pill role moves to header TopMatchBadge per JSX)
- 💀 Per-product `bestPickBadge` 658-663 (same — JSX winner shown via emerald border + accentLight bg)
- 💀 Header centered title text `<Text style={styles.headerTitle}>{a} vs {b}</Text>` 607-609 → replaced with `<TopMatchBadge />`
- 💀 Standalone § 8 specs accordion 881-961 → folds into ResultsAccordion
- 💀 Standalone § 7 Reviews section 964-1083 → folds into ResultsAccordion
- 💀 § 10 Share actions row 1255-1260 (no second Share affordance in JSX)
- 💀 Metadata footer 1262-1277 (no metadata footer in JSX)
- 💀 Legacy § 8 Score Breakdown `scoreRow` block 1184-1240 (kept gated `!scoring_v2 && scoring`; both legacy paths obsolete now that scoring_v2 ships in every payload — keep behind the existing `!scoring_v2` guard but DO NOT migrate to ResultsContent; it stays in the orchestrator's legacy-fallback branch)

### PRESERVE list (orchestration layer stays in ResultsScreen.tsx)
- ✓ All SSE / loading / error / empty-state branches (lines 100-598)
- ✓ scoring_v2 derivation + winner_index resolution
- ✓ personalization.applied_shifts → PersonalizationChip
- ✓ ConfidenceDetailsSheet driven by sheetLeg state
- ✓ RevealBurst keyed on comparisonId, fireOnce
- ✓ winnerScale Reanimated spring (settled-state initial 0.96, animated to 1.0 — verified safe per `memory/feedback_animation_initial_value_must_be_destination.md`; useEffect path-to-destination GUARANTEED via setTimeout on first mount)
- ✓ DemographicsBottomSheet trigger + handlers
- ✓ ShareBottomSheet + Loop 1 toast + lifetimeRemaining
- ✓ trackEvents pendingEventsRef batched on unmount

### Architecture
**Extract presentation → `ResultsContent.tsx`.** ResultsScreen.tsx stays the orchestrator (SSE, scoring consumption, personalization, share, demographics, navigation). ResultsContent.tsx is a pure component receiving:

```ts
interface ResultsContentProps {
  products: Product[];                      // length-2 guaranteed by parent guard
  winnerIndex: 0 | 1;
  scoringV2: ScoringV2 | undefined;
  comparisonId: string | undefined;
  cohortPeerCount: number;
  cohortGovernorate: string;
  isRTL: boolean;
  feedbackSubmitted: boolean;
  onFeedbackSubmitted: () => void;
  sheetLeg: 'price' | 'reviews' | 'specs' | null;
  onPillPress: (leg) => void;
  onCloseSheet: () => void;
  hidePricePill: boolean;
  winnerAnimStyle: AnimatedStyle;           // worklet style from parent's useSharedValue
  winnerRevealed: boolean;                  // gates the TopMatchBadge appearance + bestPick treatment
}
```

ResultsContent renders the top-down per-JSX element order. ResultsScreen passes derived props and keeps all stateful hooks/effects.

### image_url slot (A4 will wire `<Image>` tag in follow-up PR)
JSX:50-58 — square image placeholder above product name. A2 creates a `<View testID="results-product-image-slot-{idx}">` at this position with a neutral placeholder fallback (lucide camera glyph on `#EEEFF4` background). DO NOT wire `<Image source={{uri: product.image_url}}>` — A4's job.

---

## HistoryScreen (JSX 1-388, current `.tsx` 1062L)

JSX top-down element order (consumed via `QarenHistoryScreen` JSX:353-386):

| # | Element | JSX line | Current `.tsx` state |
|---|---------|----------|----------------------|
| 1 | Header — `<h1>History` 28px display | 369-373 | ✓ `<View style={styles.header}>` with QarenLogo + headerTitle (677-685). JSX has no logo but `.tsx` Bundle B/C/D Task 2.10 added it. **Decision: keep QarenLogo per shipped Bundle B/C/D design — minor divergence approved.** |
| 2 | `<HeroStats>` — stat strip (`✦ YOUR RECENT VERDICTS`, "27 decisions this month", "~240 BHD shopped smarter") + horizontal marquee of MarqueeCards | 60-109 | ✓ `<HistoryHeroStats>` exists 89-193, renders stat strip + marquee with deriveTone tones + check overlay + caption. JSX-aligned. |
| 3 | `<SearchField>` — rounded-pill search input | 183-201 | ✓ `<View style={styles.searchContainer}>` exists 698-712 |
| 4 | DateGroupV2 sections (Today/Yesterday/This Week/Older) | 307-318 | ✓ `renderSectionHeader` 631-633 + sections useMemo |
| 5 | `<HistoryRowV2>` — category eyebrow + ago + ProductBlock pair with center vs pill + verdict caption | 251-305 | ✓ `renderItem` 493-629 — fully JSX-aligned with ProductBlock variant per winner + center VS pill + verdict caption + category eyebrow + Trash2 footer |
| 6 | `<TabBarH2>` — Home/History/Profile bottom tab | 325-351 | n/a — handled by `@react-navigation/bottom-tabs` outside the screen |

**HistoryScreen verdict:** STRUCTURALLY ALIGNED. Per A2.3 Step 1, this is **close-gaps mode** — small surgical edits at most. The S2 HistoryRowV2 + HistoryHeroStats work already landed all JSX structural moves. Gaps to close:

### HistoryScreen close-gap list
1. **image_url slot:** JSX:226-233 (ProductBlock) + JSX:153-180 (MqProduct in marquee) — current `.tsx` renders `rowV2Tile` + `cardTile` as colored squares (deriveTone). A2 changes these to wrap a `testID="history-row-{id}-block-{a|b}-image-slot"` so A4 can wire the `<Image>`. The deriveTone fallback stays as the placeholder background.
2. **No additional structural changes.** All JSX elements are present in the correct order.

### DELETE list — HistoryScreen
- (none — current shape is JSX-aligned)

### PRESERVE list
- ✓ SectionList grouping (Today/Yesterday/This Week/Older)
- ✓ `dedupeBrandPrefix` defensive logic (Path A)
- ✓ `formatTimeAgoLocalized` i18n
- ✓ `deleteComparison` Alert flow + filter-out
- ✓ `viewAsResult` navigation to Results with `comparison_id`
- ✓ `authError` branch + clearSession
- ✓ `RefreshControl`

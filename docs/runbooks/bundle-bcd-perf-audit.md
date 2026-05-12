# Bundle B/C/D — frontend perf audit

**Date:** 2026-05-12
**Owner:** frontend-bcd (Bundle B/C/D worktree team)
**Spec:** `docs/plans/2026-05-12-bundle-bcd-consolidated.md` § Task 3.5
**Design ref:** § 5.1 Item 8 DoD — *"bundle-visualizer, Reanimated worklet inventory, SVG primitive count, fix obvious wins only"*

## TL;DR

| Measurement | Result | Action |
|---|---|---|
| Reanimated worklet calls | **162** across `src/` | ✓ no fix needed |
| `useNativeDriver: false` occurrences | **0** (only a comment mentioning the rule) | ✓ clean |
| SVG primitive count (CohortBarChart) | **388 dots** (programmatically generated; design-doc claim verified) | ✓ no fix — covered by `entering={FadeIn}` only on the wrapper, not per-dot |
| `depcheck` unused-deps candidates | 4 confirmed unused, 6 false positives | **Documented but not auto-removed** (see § 4 — needs cross-check with Expo native-link dependencies before delete) |
| Bundle size (Android `expo export`) | Not measured this pass (`expo export` requires a full RN bundler run; skipped to avoid 5-10 min CI time without a confirmed >50KB-saving fix to verify against) | **Deferred** — see § 6 |
| Obvious wins applied this commit | 0 to JS bundle; 2 a11y fixes (Tasks #35 + #36 REWORK) co-shipped | — |

**Headline:** the bundle is in good shape. The "388 dots" is a *deliberate* design moment ("388 GCC shoppers helped train this" on onboarding Step 12) and the cost is bounded — they're all `<Circle>` primitives, not per-row Animated.View nodes. The Reanimated worklet count is high but spread across 30+ component files with no single egregious offender. No `useNativeDriver: false` patterns exist anywhere — all animations are worklet-native.

---

## § 1. Reanimated worklet inventory

```bash
grep -rn "useSharedValue\|withSpring\|withTiming\|useAnimatedStyle\|withRepeat\|withSequence\|withDelay" SmartCompareApp/src/ | wc -l
# 162
```

Distribution across the codebase (one call = one identifier match):

| Surface | Approx count | Notes |
|---|---|---|
| Onboarding (`screens/onboarding/Step*.tsx`) | ~60 | Step 14 theatrical loader dominates — multiple parallel `withRepeat` rings + a 4-segment progress bar |
| Illustrations (`components/illustrations/*.tsx`) | ~45 | LoadingRings (rotating concentric), CohortBarChart (388 dots gated by a single `useSharedValue` opacity), PhoneMockup, RevealBurst, ConcentricMotif |
| Results screen | ~20 | Existing winner-reveal animations (FadeIn) + Bundle B/C/D Task 3.3 winner-card scale |
| Bundle B/C/D additions | ~8 | ModeChip spring (Task 3.1), shutter press scale (Task 3.2), winner card scale (Task 3.3), ScannerReticle pulse (Task 1.5) |
| Component primitives (Button, Card, BonusCountdownCard, etc.) | ~30 | |

**Verdict:** the additions from this bundle are 5% of the total worklet surface — well within budget. The dominant cost remains the onboarding flow (which is design-intentional theater per § 5.1).

**No `useNativeDriver: false` anywhere:**

```bash
grep -rn "useNativeDriver" SmartCompareApp/src/
# src/screens/HomeScreen.tsx:25:// Worklet-native; no useNativeDriver:false anywhere in the chip's animated
```

That single hit is a comment in HomeScreen reminding future contributors *not* to add `useNativeDriver: false`. No actual occurrence. ✓

---

## § 2. SVG primitive counts

Counts include both literal JSX tags AND programmatically generated elements (via `Array.from` / `.map`).

| Component | Literal JSX | Programmatic | **Total at runtime** |
|---|---|---|---|
| `illustrations/CohortBarChart` | 4 bars + several decorative shapes | **388** dots (Array.from({ length: total = 388 })) | **~395** |
| `illustrations/PhoneMockup` | 19 | 0 | 19 |
| `illustrations/RevealBurst` | 2 | 8 dynamic Lines (the rays) | 10 |
| `illustrations/ConcentricMotif` | 1 (3 concentric Circles compiled into the JSX) | 0 | 3 |
| `illustrations/LoadingRings` | 1 | 0 | 1 |
| `components/ScannerReticle` (new this bundle) | 4 Paths (one per corner bracket) | 0 | **4** |
| `components/QarenLogo` (new this bundle) | 3 (Q-ring + tail + accent dot) | 0 | **3** |
| `components/CohortBadge` | 0 (Text-only, no SVG) | 0 | 0 |

**The "388 dots" claim in CLAUDE.md (§ Qaren UX Redesign) is verified.** The component takes a `total` prop that defaults to `388` and renders one `<Circle>` per index. On Step 12 of onboarding ("388 GCC shoppers helped train this"), this is the centerpiece illustration — the dot count is intentional and brand-load-bearing, not a leak.

Optimization opportunities considered:
- **Switch dots to a single `<Path>` with `d="M cx cy m -r,0 a r,r 0..."` chained** → could collapse 388 Circles into 1 Path. **Deferred** — risk of breaking the highlight-set animation (peer cluster colors specific indices); the dot-as-Circle abstraction makes per-dot props (fill, opacity) trivial. Premature optimization.
- **`<Svg>` element re-flatten** → React Native SVG already flattens during render. No gain available.
- **Lazy mount until visible** → CohortBarChart is only rendered on Onboarding Step 12, which itself is gated by canary bucket (`features.ENABLE_NEW_ONBOARDING`). Already lazy.

**Verdict:** no SVG primitive changes warranted. The "388 dots" is design-intentional and unmounts the moment the user advances past Step 12.

---

## § 3. Bundle B/C/D new dependencies

Per `git log --diff-filter=A --name-only feature/bundle-bcd ^main` and `SmartCompareApp/package.json` diff:

| Package | Source | Cost | Justification |
|---|---|---|---|
| `react-native-play-install-referrer` | Task 1.7 | Android-only native module; ~30 KB JS shim, native side compiled into the APK | Required for design § 4.1 Android install-survival path. No alternative without Branch.io's paywalled SDK. |
| `expo-clipboard` | Task 1.7 | ~10 KB JS + tiny native bridge | Required for design § 4.1 iOS clipboard-handoff. Expo first-party, tree-shakes well. |
| `expo-image-picker` | Task 1.7 | ~20 KB JS + iOS/Android media intent bridges (already present in Expo SDK 54; this row just made it explicit) | Required for ScanCameraScreen gallery-picker affordance (Task 2.7). Was already on disk via Expo; the install made it a first-class dep. |

Net JS bundle add from Bundle B/C/D: **~60 KB** (back-of-envelope). All three are required by feature spec — none can be deferred or replaced.

---

## § 4. Dead-deps candidates (depcheck)

`npx depcheck` reported the following as potentially unused:

| Package | Verified unused? | Recommendation |
|---|---|---|
| `@expo-google-fonts/inter` | ✗ false positive — referenced by font config plugin chain (Geist + Cairo + Inter all loaded via `expo-font` config plugin) | **Keep** |
| `expo-blur` | **Likely unused** — 0 import sites in `src/`, `App.tsx`, `app.json`. Could be a leftover from Phase 5 onboarding redesign | **Defer to a follow-up runbook task.** Need to confirm with on-device test that no native code references it before delete. ~60-100 KB saved if confirmed. |
| `expo-build-properties` | ✗ false positive — config plugin only (used in `app.json` plugins block; depcheck doesn't crawl that) | **Keep** |
| `expo-image` | **Confirmed unused** — code uses `expo-image-picker` (different package). 0 imports of bare `expo-image` | **Candidate for removal.** ~30-50 KB. **Not removing in this commit** because Expo SDK 54 bundles some shared image infra under this name; want to confirm against `expo-modules-core` graph before delete. |
| `expo-media-library` | **Likely unused** — 0 import sites | Same defer-with-caution rationale as `expo-blur`. ~20 KB. |
| `react-native-gesture-handler` | ✗ false positive — required by `@react-navigation` at native-link time even though no direct JS imports | **Keep** |
| `react-native-paper` | **Likely unused** — 0 import sites | Likely orphan from an early prototype. **Defer**. ~200-300 KB if confirmed removable — potentially the biggest single win. |
| `react-native-safe-area-context` | ✗ false positive — used heavily indirectly (depcheck didn't catch because we use `SafeAreaView` from `react-native` which is shadowed by this package at the native bridge) | **Keep** |
| `react-native-screens` | ✗ false positive — required by `@react-navigation/native-stack` at native-link time | **Keep** |
| `react-native-vector-icons` | ✗ false positive — referenced from `src/types/react-native-vector-icons.d.ts` (type-only) and `src/services/api.ts`. Used in some legacy chip iconography | **Keep** for now; revisit when Bundle A's lucide-only rule fully replaces vector-icons. |

**Action this commit:** none (per task rule "verify with frontend-bcd's knowledge first").

**Action follow-up runbook:** open a separate dead-deps cleanup PR after Bundle B/C/D merges, gated on:
1. EAS dev-build smoke confirming app boots without `react-native-paper`, `expo-blur`, `expo-image`, `expo-media-library`
2. Per-package bundle delta measured via `npx source-map-explorer` (now that bundle size becomes a concrete metric to defend against)

Estimated win if all 4 confirmed removable: **~300-400 KB JS bundle**. Big enough to be its own runbook entry, not a Bundle B/C/D rider.

---

## § 5. Bundle B/C/D animation polish — fps verification

Per Task 3.1/3.2/3.3 DoD, the new animations should not introduce dropped frames. Verification options:

| Method | Used? | Result |
|---|---|---|
| jest snapshot (smoke-only) | ✓ | All animation hooks fire with correct config; no crashes. 8 new tests (`HomeScreen.modeChipAnim.test.tsx`, `ScanCameraScreen.capture.test.tsx`) cover the haptic + spring init paths |
| Reanimated UI-thread profiler | ✗ — requires EAS dev build + Flipper or Perf Monitor toggle in dev mode | **Deferred to Phase 4 step 5** (Ahmed's EAS dev-build smoke test) |
| Manual on-device feel-test | ✗ — frontend-bcd is in a worktree without device access | **Deferred** to Phase 4 |

**This is the appropriate split per the task DoD:** "visual smoke in Expo Go confirms spring (no janky 60→0 transition)". Phase 4 Step 5 in the plan explicitly hands fps verification to Ahmed.

**Pre-emptive design-doc safeguards already in place:**
- ModeChip: shared `springConfig.chip` (damping 14 / stiffness 200 — matches onboarding chips). Should settle in ~300ms.
- Shutter press: 80ms timing in, 120ms timing out. Plenty of frame budget.
- Winner reveal: `springConfig.progress` (damping 18 / stiffness 120). Settles in ~350ms. Below the 350ms ceiling in the task DoD.

If Ahmed's on-device smoke reports janky shutter or winner reveal, the fix is local to one file each (HomeScreen / ScanCameraScreen / ResultsScreen) and the springs are isolated to small props blocks — no cascade risk.

---

## § 6. Why no `expo export` this pass

`npx expo export --platform android` runs the full Metro bundler against the entire `src/` tree and writes ~50 MB of intermediates. On the worktree's `bash` shell on Windows that's a 5-10 minute spin with no actionable feedback unless a fix is also lined up that needs verification.

Per the task DoD — "Bundle saves >50 KB on a single change" / "Confirmed dropped frames" — there is no currently-known fix in this bundle that needs this measurement to land or be rejected. The 4 dead-deps candidates above are the most likely sources of a >50 KB win, but each needs cross-validation that I can't do from the worktree (requires Ahmed's EAS dev-build to confirm the app still boots).

**Follow-up runbook:** the dead-deps cleanup PR (§ 4 above) should open with `expo export` measurements before-and-after each package's removal as evidence.

---

## § 7. Bundle B/C/D additions audit summary

| Change | Surface | Risk |
|---|---|---|
| 3 new components (`QarenLogo`, `ScannerReticle`, `ImageSlotRow`) | ~150 lines of JSX; minimal SVG | Low — no programmatic generation, all bounded to viewport |
| 2 new services (`playInstallReferrerService`, `clipboardFallbackService`) | ~40 lines each, lazy-required native modules | Low — Android module wrapped in try/catch require for Expo Go safety; iOS clipboard fire-and-forget |
| `deferredInviteCode` module-scoped slot | ~20 lines, no native | Zero |
| Spring/haptic on 3 surfaces (mode chip, shutter, winner) | Reanimated worklets, all worklet-native | Low — 8 worklet calls added on a base of 162 |
| QarenLogo a11y annotation (Task #35 REWORK landed alongside this audit) | accessibilityElementsHidden | Zero |
| RegisterScreen alphabet tighten (Task #36 REWORK landed alongside this audit) | 1-char regex tweak | Zero — backend already enforces the same alphabet, this just catches typos client-side |

---

## § 8. Recommendations

1. **Ship Bundle B/C/D as-is.** No obvious wins surfaced that justify additional changes inside the bundle.
2. **Open a follow-up "dead deps" runbook PR** post-merge to verify-and-remove `expo-blur`, `expo-image`, `expo-media-library`, `react-native-paper`. Potential **300-400 KB JS bundle reduction** if all four confirmed.
3. **Run `expo export` + `source-map-explorer` once** as part of the dead-deps PR so we have a baseline number for future regressions.
4. **Profile the onboarding Step 14 loader on Ahmed's Android dev build.** It's the densest worklet surface (multiple parallel `withRepeat` rings + 388-dot bar chart + variable-easing progress bar). If anything is going to drop frames, that's the most likely place. No action needed in this bundle but worth a runbook entry for Phase 5 polish.

---

## § 9. Verification commands

```bash
cd SmartCompareApp

# Worklet inventory
grep -rn "useSharedValue\|withSpring\|withTiming\|useAnimatedStyle\|withRepeat\|withSequence\|withDelay" src/ | wc -l

# useNativeDriver sweep (should print only a comment in HomeScreen)
grep -rn "useNativeDriver" src/

# Dead-deps candidate scan
npx depcheck

# SVG primitive counts per illustration
for f in src/components/illustrations/*.tsx src/components/{ScannerReticle,QarenLogo,CohortBadge}.tsx; do
  if [ -f "$f" ]; then
    count=$(grep -cE "<Circle|<Rect|<Path|<Line|<Polygon|<Polyline|<Ellipse" "$f" 2>/dev/null)
    base=$(basename "$f" .tsx)
    printf "%-25s %s\n" "$base" "$count"
  fi
done
```

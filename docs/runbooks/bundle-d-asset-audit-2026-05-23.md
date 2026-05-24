# Bundle D — Asset Audit (Task 4.N.1, executed early)

**Date:** 2026-05-23
**Auditor:** native-ops
**Result:** BLOCKER — current assets are default Expo placeholders, NOT Qaren-branded

## Files audited

| File | Dimensions | Bytes | Content | Status |
|---|---|---|---|---|
| `SmartCompareApp/assets/icon.png` | 1024×1024 | 22380 | Light-gray concentric circles on grid background (Expo default) | NEEDS REPLACEMENT |
| `SmartCompareApp/assets/adaptive-icon.png` | 1024×1024 | 17547 | Same concentric circles, smaller, white background (Expo default) | NEEDS REPLACEMENT |
| `SmartCompareApp/assets/splash-icon.png` | 1024×1024 | 17547 | Identical to adaptive-icon.png (byte-equal) | NEEDS REPLACEMENT |
| `SmartCompareApp/assets/favicon.png` | 48×48 | 1466 | Small isometric cubes/box graphic (Expo default) | NEEDS REPLACEMENT |

## Findings

1. **No "SmartCompare" text residue.** The original audit concern (legacy brand strings) is N/A — there's no text on any asset at all.
2. **All four assets are unchanged since 2024 Day-5 commit `5d22f2b`** ("Mobile app working - camera, upload, comparison flow complete"). They are the boilerplate PNGs that ship with `npx create-expo-app`. They predate the Qaren rebrand entirely.
3. **`adaptive-icon.png` and `splash-icon.png` are byte-identical.** Either by accident or because someone copied one to the other. Either way, both are placeholder.
4. **No EN/AR locale variants.** The icon is text-free so this is moot; if Qaren wordmark uses both scripts, may need either a script-neutral mark OR a per-locale icon (rare on iOS, possible via `Assets.car` but Expo doesn't expose this).
5. **iOS densities:** Expo's `expo prebuild` auto-generates @1x/@2x/@3x from the 1024×1024 source, so a single 1024 file is sufficient.
6. **Android densities:** Expo auto-generates mdpi through xxxhdpi from `adaptive-icon.png`.

## Required Qaren-branded assets

These need to be sourced (Claude-Design / Figma / hand-designed) BEFORE Phase 3 EAS production build. Phase 2 preview build can ship with placeholders for internal smoke (TestFlight will warn about generic icon), but Apple App Store submission will reject.

| File | Required size | Required content |
|---|---|---|
| `icon.png` | 1024×1024 PNG, opaque, no transparency | Qaren brand mark — recommend monogram "ق" (or "Q") in emerald `#10B981` on appropriate background, or the concentric circles motif from `src/components/illustrations/ConcentricMotif.tsx` rendered as a flat icon. Per Apple guidelines: no rounded corners (Apple adds them), no thin strokes, fills full 1024×1024 frame, no transparent areas. |
| `adaptive-icon.png` | 1024×1024 PNG, foreground only | Same mark, but centered in inner ~66% (Android applies dynamic masks). Background color separately specified at `app.json:24` `android.adaptiveIcon.backgroundColor` (currently `#ffffff`). |
| `splash-icon.png` | 1024×1024 PNG, transparent BG | Same mark centered, transparent surrounding pixels. Background color at `app.json:13` `splash.backgroundColor` (currently `#ffffff`). Note: SDK 54 `expo-splash-screen` may have moved this config under the plugin. |
| `favicon.png` | 48×48 (or 32×32 PNG) | Same mark, simplified for tiny display. |

## Recommended approach

**Option A (fastest):** Generate from `ConcentricMotif.tsx` SVG → rasterize at 1024×1024 with the emerald `#10B981` stroke color from `theme/index.ts` filling the frame. Matches existing brand language since that component is already used in the onboarding hero. Native-ops can do this in ~30 min if Ahmed approves the direction.

**Option B (best):** Ahmed runs the Claude-Design output through Figma/equivalent to produce a proper monogram icon. Higher visual quality but slower and unscheduled.

**Option C (compromise):** Ship preview build with current placeholders (TestFlight allows it; internal testers won't blink), use Phase 4 Task 4.N.1 close-out window to land final assets before production build. TestFlight build #1 = placeholder; TestFlight build #2 (the one Apple reviews for App Store) = branded.

**Recommendation:** Option C for fastest path to a working TestFlight smoke; Option A if Ahmed wants branded testing in Phase 2; Option B before App Store submission regardless.

## Notification icon (separate, also missing)

The newly-added `expo-notifications` plugin (commit `70a34b3`) deferred the `icon` key. Android push notification icon must be **96×96 white-on-transparent PNG** (Google design guideline — any non-white pixels render as a solid block). Currently the system default Android notification icon is used. Acceptable for TestFlight v1, recommended to add by App Store submission.

## Blocking?

- Phase 2 EAS preview build: **NO** — TestFlight accepts placeholders
- Phase 3 EAS production build for App Store: **YES** — Apple submission gate ICN-0001 (or similar) rejects builds with a generic icon

## Decision needed from Ahmed (NOT BLOCKING Phase 1, blocking Phase 3)

Choose option A / B / C. Default if no answer by Phase 2 close: Option C (placeholders to TestFlight, branded before App Store).

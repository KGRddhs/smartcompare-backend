# U2 — the honest limit sheet (replace the fake subscription paywall) — unit spec

**Session 69, audit findings LL-2 / RT-2 / SA-05 (all CONFIRMED by two refuters).** Owner: Claude. Decision D2 on the launch runbook: option A (remove the paywall for v1) is the recommended and assumed answer; StoreKit is not in scope.

## 1. Why (measured, main `89f2dc6a`)

`SmartCompareApp/src/screens/PaywallScreen.tsx` (786 lines) is the Bundle E "v3 high-conversion" paywall: hero tiles, a social-proof strip with a hard-coded **"5,000+"** shoppers count and a **"4.8"** rating pill, two plan cards (**"0.9 BHD/mo"**, **"2.9 BHD"**, "10.8 BHD billed yearly · Save ~70%"), a feature list, a "HOW THE TRIAL WORKS" timeline, a sticky CTA **"Start My 3-Day Free Trial"** + "No payment due now", and Terms / Privacy / Restore links. Every CTA calls `Alert.alert('Coming soon', …)` (lines 236–247). Reachable from: `ProfileScreen.tsx:466` ("Upgrade to Premium" row → `navigation.navigate('Paywall')`), `HomeScreen.tsx` lines 354, 467, 508, 588, 614, 677 (PaywallBanner CTA), 814, and `ResultsScreen.tsx:317` (camera USAGE_LIMIT). Route registered in `App.tsx:454` as `Paywall` with params `{ initialUsage?: UsageStatus }` (`src/types/types.ts:613`).

Apple App Review: guideline 2.1(a) (placeholder/non-functional purchase UI), 2.3.1 (promoting services the app does not offer), 3.1.1/3.1.2 (a subscription offered without in-app purchase). A reviewer on a free account reaches it after 3 lifetime compares; from Profile in one tap. The launch runbook ranks it blocker #2.

## 2. Target behaviour (what the submitted build must do)

R1. **No subscription UI is reachable anywhere in the app.** Grep-provable: no rendered string or i18n value reachable from `PaywallScreen.tsx` / `ProfileScreen.tsx` / `PaywallBanner.tsx` contains a price (`BHD`), `trial`, `Restore`, `Premium` as a product, a shopper count or a star rating. `Alert.alert('Coming soon')` is gone.

R2. **The route name `Paywall` and its params stay.** Every existing `navigation.navigate('Paywall', …)` site keeps working unchanged (HomeScreen ×7, ResultsScreen ×1, PaywallBanner CTA). The screen component behind the route becomes the honest limit sheet. (Renaming the route would touch 9 call sites and their tests for no product value; a follow-up may rename it.)

R3. **The honest limit sheet** (`PaywallScreen.tsx` re-written, or a new `LimitReachedScreen.tsx` that `App.tsx` registers under the `Paywall` route — the implementer chooses; the file must be under ~200 lines):
  - Title: today's free comparisons are used up (EN key `paywall.limit.title`). When `initialUsage` (or `getUsageStatus()` on mount, as today) says the MONTHLY cap is the binding one, the title says this month's free comparisons are used up instead.
  - Body: the counts when known — reuse `paywall.usageMessage` ("{{used}} of {{limit}} comparisons used this month") and add `paywall.limit.today` ("{{used}} of {{limit}} comparisons used today"); a line saying when it resets (`paywall.limit.resets_daily` "Your free comparisons reset tomorrow." / `paywall.limit.resets_monthly` "Your free comparisons reset at the start of next month."). No promise of a paid tier, no "coming soon".
  - One primary action: close / back to Home (`common.done` or a new `paywall.limit.cta` "Back to Home") → `navigation.goBack()` when possible else `navigate('Home')` as the existing close X does today.
  - Keep the existing close X (top-left) and the `testID`s the Home tests rely on if any (check `__tests__/HomeScreen.*` for `paywall-` testIDs before deleting).
  - Arabic: every new key in `ar.json` too (native-quality MSA, no diacritics, the W3-11 i18n fence and `.copy-policy.json` banned/scary words apply — no "couldn't", "failed", "try again" style copy in EN, none of the nine Arabic banned terms).
R4. **Profile:** delete the "Upgrade to Premium" row (`ProfileScreen.tsx:466-467`) and the `profile.upgrade` key if nothing else uses it (check the i18n fence: unused keys may be flagged or may be required — follow whatever `__tests__/lint/i18nFence.w311.test.ts` enforces).
R5. **PaywallBanner (`src/components/PaywallBanner.tsx`, keys `home.compare.paywall_banner_title/body/cta`):** read the three values in EN and AR; if any promises premium/upgrade/trial, reword to the honest limit copy (title: the daily limit is reached; body: when it resets; CTA: "See details" or similar) — otherwise leave it.
R6. **Dead code removed, not flagged:** the hero, social-proof, plan-card and trial-timeline components and their unused i18n keys (`paywall.cta`, `paywall.plan.*`, `paywall.socialProof.*`, `paywall.timeline.*`, `paywall.coming_soon_*`, `paywall.subscribe`, `paywall.payment`, `paywall.restore`, `paywall.social`, `paywall.premium.*`, `paywall.free.*` if unused) are deleted from BOTH catalogs; git history keeps the design. Keys still referenced anywhere stay.
R7. **ToS:** out of scope here (U8 legal redraft removes "Premium subscribers").

## 3. Tests (the RED must fail at `89f2dc6a` for the right reason)

T1. Rewrite `__tests__/screens/PaywallScreen.bundleE.test.tsx` as `__tests__/screens/LimitReachedSheet.s69.test.tsx` (delete the old file): renders with `initialUsage` daily-exhausted → the daily title + "3 of 3 comparisons used today" + the daily reset line; monthly-exhausted → the monthly title + reset line; no `initialUsage` and `getUsageStatus` rejecting → the title still renders, no counts, no crash; the close X and the primary action call `goBack` (or the Home navigate fallback); **negative pins:** `queryByText(/BHD/)`, `/trial/i`, `/Restore/`, `/5,000/`, `/4\.8/`, `/Coming soon/i` are all null; `Alert.alert` is never called.
T2. A static fence `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts`: reads `PaywallScreen.tsx` (or the new screen file), `ProfileScreen.tsx`, `PaywallBanner.tsx`, `en.json`, `ar.json` and asserts (a) none of the screen/component sources contains `Alert.alert`, `BHD`, `trial`, `Restore`, `socialProof`, `Trusted by`; (b) `ProfileScreen.tsx` contains no `navigate('Paywall'` and no `profile.upgrade`; (c) every `paywall.*` key present in `en.json` is also in `ar.json` and vice-versa, and none of the deleted keys listed in R6 remains in either catalog; (d) `App.tsx` still registers a route named `Paywall`.
T3. Existing suites are the regression net: every `__tests__/HomeScreen.*` and `ResultsScreen.*` test that navigates to `Paywall` must still pass unchanged (the route name is kept); the W3-11 i18n fence and the copy-policy tests must pass with the new keys.

## 4. Gates (client unit; the FULL jest suite is the arbiter)

- jest by path: `'LimitReachedSheet\.s69|paywall\.noSubscriptionUi\.s69|HomeScreen|ResultsScreen|i18nFence'` under `timeout -k 15 900`.
- FULL `npx jest --ci` (no `-u`, no `.snap` in the diff; report suites/tests/snapshots) under `timeout -k 15 1700`.
- `npx tsc --noEmit`; `npx eslint` by path on every touched `.ts/.tsx`.
- `git diff --stat` shows only: the screen file(s), `ProfileScreen.tsx`, `PaywallBanner.tsx` (if reworded), `App.tsx` (only if the component was renamed), `en.json`, `ar.json`, the two test files, and the deleted old test.

## 5. Rulings (Fable, pre-launch)

- R-A: keep the `Paywall` route name (R2) — the rename is a follow-up issue, not this unit.
- R-B: the usage counts come from `initialUsage` first, then `getUsageStatus()`; a failed fetch degrades to no counts, never to an error alert.
- R-C: no new flag: the old screen is not kept behind a build constant; git history is the record.
- R-D: Arabic copy is written by the green agent, marked for native review in the PR body (Ahmed's on-device walkthrough), and must pass the copy-policy fence.
- R-E: Never `git checkout --` a file; never `npm install`; `node_modules` is a junction — do not remove it.

---
name: Bundle D Frontend Anchor
description: Per-lane scope + verification commands + risk subset for Bundle D Frontend agent
type: project
---

# Lane: Frontend

## My scope (~9 tasks across Phases 1-3)

### Phase 1 — Foundation
1. **Task 1.F.1** — Refresh-token mutex (R9) at `SmartCompareApp/src/services/api.ts`. **Module-scope singleton** `Promise<RefreshResult> | null` — NOT function-scope. Export `__resetRefreshMutex()` + `__testRefreshDedup()` for test. **Acceptance:** `__tests__/api.refreshMutex.test.ts` GREEN — 3 concurrent calls → 1 network fetch.
2. **Task 1.F.2** — Add `profile.name` i18n key. EN: "Name" / AR: "الاسم" (R11 default — ask Ahmed in PR if different). Insert alphabetically between `profile.editProfile` and `profile.settings`. **Acceptance:** `i18n.test.ts` GREEN (key counts match), `copy-policy.test.ts` GREEN.
3. **Task 1.F.3** — "Edit style profile" navigate fix. **Recommended Option A:** register `Onboarding` permanently in post-auth stack with `initialParams.mode='full'`; pass `mode='edit'` for re-entry from `App.tsx:301`. NewOnboardingHost accepts `mode` prop; in edit mode, skips non-style steps. **Acceptance:** `App.navigation.test.tsx` GREEN; tsc 0 errors.
4. **Task 1.F.4** — Camera `?` help overlay (`src/screens/ScanCameraScreen.tsx` + new `src/components/CameraHelpOverlay.tsx`). Add EN+AR copy (R17 — approved vocabulary only). Wire IconButton → setHelpVisible(true). **Acceptance:** copy-policy GREEN; visual smoke shows 3-step overlay.
5. **Task 1.F.5** — History detail fetch fix (BLOCKED ON Backend R3 RCA). If schema_version=1 root cause → only error-copy update (`t('history.error.notFound')` for 404). Otherwise implement per RCA. Wait max 30 min then dispatcher escalates per OP #8.
6. **Task 1.F.6** — C17 `ai_sharing_enabled` default OFF at `src/screens/ProfileScreen.tsx:102`. Change `?? true` → `?? false`. **R23 critical:** only `undefined` → OFF; existing `true` rows untouched. **Acceptance:** `ProfileScreen.aiSharingDefault.test.tsx` GREEN.

### Phase 2 — Integration
7. **Task 2.F.1** — Profile optimistic toggles + 5-toggle wiring audit (DEPENDS on Backend 2.B.7 reengagement subs endpoint). Optimistic update before API resolution; rollback + Alert on failure. Wire: AI sharing, Smart Decision Notifications master, Decision Insights, Peer Decision Updates, Decision Retrospectives. **Acceptance:** `ProfileScreen.optimistic.test.tsx` GREEN + integration test (live API) confirms all 5 save end-to-end.
8. **Task 2.F.2** — HomeScreen Claude-Design refresh (BLOCKED on Ahmed providing tokens.json + example .tsx). **R16 critical:** PRESERVE Bundle B contract — TwoInputShell (don't remove), paste auto-split (lines 447, 455), mode auto-switch (line 462), content moderation (line 221), all 8 analytics events still fire. Extend `src/theme/index.ts` additively (R10), don't replace. **Acceptance:** full PR #6 EN+AR walkthrough mental model GREEN; existing Bundle B test from `__tests__/HomeScreen.test.ts` still GREEN.

### Phase 3
9. **Task 3.F.1** — PR #6 Bundle B simulator sign-off. Open `memory/next-session-bundle-b-phase4-walkthroughs.md` + `.pr-6-phase4-comment.md`. On EAS preview build from 2.N.1: EN walkthrough A-L (10 visual), AR walkthrough M-P (7 RTL), haptic verification, 4 screenshots, analytics `[analytics]` console.log capture (all 8 events). Post sign-off comment on PR #6.

## Memory facts I need (anti-hallucination)
- App name is "Qaren" (قارن). NEVER write "SmartCompare" to any user-facing string. Forbidden EN vocab: `couldn't`, `try again`, `Failed to`. Forbidden AR: `تعذر`, `فشل`. NO "estimated" word in UI (backend keeps enum, UI says "indicative"/"reference").
- IDE/LSP TS diagnostics on Windows are unreliable (`typescript-lsp` plugin bug). Trust ONLY `npx tsc --noEmit` exit code.
- Expo native deps: use `npx expo install <pkg>` (NOT `npm install`).
- Tokens in `expo-secure-store` (NOT AsyncStorage). `verifyAuth()` returns `User | null` (NOT boolean).
- All `console.log` wrapped in `__DEV__`.
- `featureBucket.ts` djb2 hash on stable id (device-id pre-signup, user.id post-signup). `hashBucket(id, percent)` is pure.
- Bundle B contract preservation (R16): TwoInputShell at `HomeScreen.tsx`, paste auto-split anchored `^https?://` regex (no `.trim()` pre-strip), 4-layer content moderation (L1-L4), 3-part celebration on ready (NO shake/sound), paywall takeover strips surrounds when `canCompare=false`, dual-shape `product_a`/`product_b` on `/text/compare`.
- 1011/1011 Jest + 30 snapshots is current baseline (Bundle C frontend Section B).
- `HomeScreen.redesign.test.tsx` / `.modeChipAnim.test.tsx` / `.scanCamera.test.tsx` are RED PRE-EXISTING (pre-date Bundle B `21e7bc0` rewire) — NOT my responsibility to fix in Bundle D (design § 12 out-of-scope).
- min-display floor 1.2s on HomeScreen→Results (cached responses still show loading 1.2s per design § 3).
- haptic vocabulary: chip=light, stage=light, winner=medium — NO error/warning/heavy intensities (Build Principle #4).
- App config: `CANARY_NEW_ONBOARDING_PERCENT=100` in `src/config/features.ts` (build/test phase).
- Cohort match values are EXACT-CASE: `age_group: "25-34"`, `gender: "Male"/"Female"`.
- API client: `axios` to Railway 120s timeout; SSE via `streamComparison()` (fetch+ReadableStream, fallback non-streaming).

## Pre-flight commands (run before starting)
- `git log --oneline -5` — confirm starting commit
- `cd SmartCompareApp && npx tsc --noEmit` — confirm baseline 0 errors
- `cd SmartCompareApp && npx jest --listFailingTests 2>/dev/null | grep -v "HomeScreen.redesign\|modeChipAnim\|scanCamera" | head -5` — confirm only pre-existing 3 RED files
- `npx expo-doctor` — full health check

## Verification commands (run before "done")
- `cd SmartCompareApp && npx tsc --noEmit` — 0 errors
- `cd SmartCompareApp && npx jest` — ≥1011/1011 + 30 snapshots passing (Bundle B baseline)
- `npx jest src/__tests__/i18n.test.ts src/__tests__/copy-policy.test.ts` — gates pass
- `npx jest src/__tests__/HomeScreen.test.ts` — Bundle B contract preservation
- Mental walkthrough of PR #6 EN A-L + AR M-P (for Task 3.F.1 only)

## Risks I own (subset of R1-R24)
- **R9** Refresh-token mutex MUST be module-scope singleton — PR comment includes code excerpt showing singleton `Promise` cached at module scope, NOT function scope
- **R10** Claude-Design token conflicts — extend `src/theme/index.ts`, don't replace; tokens applied additively
- **R11** `profile.name` i18n — EN "Name" / AR "الاسم" default; ask Ahmed in PR if different
- **R16** HomeScreen redesign must NOT remove TwoInputShell behavior — full Bundle B PR #6 EN+AR walkthrough on new design; ZERO regressions on TwoInputShell contract
- **R17** Camera help overlay copy — uses approved vocabulary; copy-policy test catches violations
- **R23** `ai_sharing_enabled` default flip OFF — only `undefined` → OFF; existing `true` rows untouched (verified via SQL spot-check from QA)

## Dependencies
- **Blocked by:** Backend R3 RCA (Task 1.F.5 history detail), Backend 2.B.7 reengagement subs endpoint (Task 2.F.1 toggle wiring), Ahmed Claude-Design output (Task 2.F.2 HomeScreen refresh), Native/Ops 2.N.1 EAS preview build (Task 3.F.1 simulator sign-off)
- **Blocking:** QA Phase 2 cross-review depends on my Phase 1 commits; PR #6 sign-off comment closes a long-standing follow-up

## Rollback recipes
- **Code changes:** `git revert <commit>` → push to bundle branch → re-build via `eas update --branch preview`
- **i18n key conflict:** revert `src/i18n/en.json` + `ar.json` commit; key removed from EditProfileScreen call site stays harmless (uses fallback)
- **HomeScreen redesign regression:** revert `src/screens/HomeScreen.tsx` + `src/theme/index.ts`; existing Bundle B HomeScreen returns
- **Toggle wiring regression:** revert `src/screens/ProfileScreen.tsx` commit; user can re-toggle manually

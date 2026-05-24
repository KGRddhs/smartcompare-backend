# Bundle D — EAS Preview Smoke-Test Runbook

**Trigger:** Native/Ops Task 2.N.1 produces an EAS preview build → Ahmed installs → runs this checklist before TestFlight invite gate (Phase 3.N.2).

**Estimated wall time:** 45–60 min for a thorough single-device run. Repeat condensed (Sections 2 + 3 only) on a second device if available.

**Test data prereqs:**
- One fresh Apple ID OR Android device (uninstalled state) for Section 1 cold-start
- Email account Ahmed controls for Section 3 register/verify
- A second test account already-registered (returning-user path)
- Network inspector handy (Charles, Proxyman, or Expo dev menu) for Section 3 refresh-token probe

**Risk closures this runbook drives:**
- **R4** Apple Sign-In three-leg device verification (Section 3)
- **R10 + R16** HomeScreen Claude-Design device leg (Section 2)
- **R17** Camera help overlay device sanity (Section 7)
- **R18** Profile sub-toggle wiring end-to-end (Section 6)
- **R23** AI-sharing default OFF on fresh signup (Section 6)
- **Sentry-watch window** for QA's mega-batch ledger (Section 8)

---

## Section 1 — Cold-start path

Goal: confirm the splash → onboarding (new) OR splash → main (returning) routing works on first launch.

### 1.1 Fresh install — new user path
- [ ] Install EAS preview `.ipa` / `.apk` to a device that has never run the app
- [ ] Launch → Splash renders with new app icon brand (verify against Claude-Design icon spec)
- [ ] Splash transitions into **Onboarding step 1 (Welcome)** within 2s
- [ ] All 17 onboarding steps render without crashing (step 14 theatrical loading holds ≥ 3.2s minimum; step 16 has NO skip link)
- [ ] Step 17 (Notifications) → Allow OR Not Now → lands on **Home tab**
- [ ] Cold-start log shows `onboarding_started` analytics event with step_number=1
- [ ] **Pass criteria:** no crash, no white screen, no scary copy seen anywhere

### 1.2 Returning-user path
- [ ] Force-quit app (do NOT uninstall)
- [ ] Relaunch → Splash → directly to **Home tab** (skips onboarding)
- [ ] Bottom tab bar shows Home / History / Profile in correct order (LTR English; RTL Arabic mirrors)

### 1.3 Splash branding
- [ ] App icon on home-screen matches `assets/icon.png` from Claude-Design (NOT the Expo placeholder)
- [ ] Splash screen logo matches `assets/splash-icon.png`
- [ ] No "Expo" wordmark visible anywhere outside the dev menu

---

## Section 2 — Bundle B contract on-device (R16 device leg)

Goal: confirm the redesigned HomeScreen + TwoInputShell preserves every Bundle B PR #6 invariant. Pairs with the FE-side unit gate at `__tests__/HomeScreen.bundleB.contract.test.tsx` (3def805).

### 2.1 EN walkthrough A–L (10 visual + behavior checkpoints)
- [ ] **A** — Home renders TwoInputShell (two side-by-side input boxes + emerald "vs" pill between them). NO old SearchOverlay modal
- [ ] **B** — Type "iPhone 16" in Box A → no autocomplete forced; ghost placeholder gone after first char
- [ ] **C** — Type "Galaxy S25" in Box B → Compare CTA enables
- [ ] **D** — Paste `iPhone 15 Pro vs Galaxy S24 Ultra` into Box A (empty Box B) → **auto-split** into "iPhone 15 Pro" + "Galaxy S24 Ultra"; cursor jumps to Box B
- [ ] **E** — Paste `https://www.apple.com/iphone-16-pro/` into Box A while in TEXT mode → **mode auto-switch** to URL mode; URL persists in Box A
- [ ] **F** — In URL mode, paste only whitespace-prefixed URL ` https://...` → mode does NOT switch (anchored regex caller-side per Bundle B spec § 4.1.2)
- [ ] **G** — Tap Compare with both inputs filled → loading hero appears within 250ms; LoadingRings visible ≥ 1.2s even on cached responses
- [ ] **H** — Results screen lands; SSE streaming visible stage-by-stage (specs → prices → reviews → verdict)
- [ ] **I** — Tap Back → returns to Home with both inputs preserved
- [ ] **J** — Type sentinel string `CONTENT_SAFETY_TEST_BLOCK_ME_42` in either box → submit → **content-block alert** fires (L1 prefilter triggered, copy uses approved vocabulary)
- [ ] **K** — Trigger paywall takeover (consume all comparison credits via repeat compares as free-tier user) → Compare CTA replaced by Paywall banner takeover; surrounds stripped per design § 3
- [ ] **L** — Tap Paywall banner → Paywall modal opens (transparentModal presentation)

### 2.2 AR walkthrough M–P (7 RTL checkpoints)
Switch to Arabic via Profile → Language → العربية, restart app.

- [ ] **M** — Home renders with **RTL mirror**: Box A on right, Box B on left, vs pill between
- [ ] **N** — Arabic placeholders + labels render correctly (Cairo font, no fallback square boxes)
- [ ] **O** — Paste Arabic comparison phrase `آيفون 16 ضد سامسونج S25` → auto-split works (Arabic separator handled)
- [ ] **P** — Paywall banner copy in AR uses approved vocabulary (no `تعذر`/`فشل`)

### 2.3 8 analytics events captured
Enable Expo dev menu → React Native debugger → Console. While running 2.1 + 2.2:

- [ ] `compare_entry_view` fires on Home mount
- [ ] `compare_entry_paste_split` fires on step D
- [ ] `compare_entry_mode_autoswitch` fires on step E
- [ ] `compare_entry_ready` fires when both boxes filled
- [ ] `compare_entry_submit` fires on Compare CTA tap (payload includes `used_paste_split`, `used_autoswitch`)
- [ ] `compare_entry_content_block` fires on step J (payload includes `layer` field)
- [ ] `compare_entry_paywall_banner_view` fires on canCompare flip to false
- [ ] `compare_entry_paywall_banner_tap` fires on step L

### 2.4 3-part ready celebration (Build Principle #4)
- [ ] Visual: emerald glow pulses softly around Compare CTA when both inputs filled
- [ ] Haptic: light impact only (NOT medium/heavy/notification-error)
- [ ] **NO** shake / wobble / jitter / sound on ready transition

---

## Section 3 — Auth flows

Goal: prove R4 (Apple Sign-In device leg), R9 (refresh-token mutex), and the Google OAuth path don't regress the RNGoogleSignin baseline.

### 3.1 Email register + verify
- [ ] Tap **Register** from Login screen → Register form renders
- [ ] Enter Ahmed-controlled email + 10+ char password (with upper/lower/digit) → submit
- [ ] **No crash**; success state advances to onboarding (new user) OR Home (if existing)
- [ ] Network inspector: `POST /api/v1/auth/register` returns 200 with `session.access_token`
- [ ] Tokens stored in **Keychain (iOS) / Keystore (Android)** — verify via `npx expo-secure-store` debug if available; never AsyncStorage

### 3.2 Email login (returning user)
- [ ] Log out from Profile → returns to Login screen
- [ ] Enter same credentials → login succeeds; lands on Home
- [ ] Forgot Password link → ForgotPassword screen → enter email → check for password reset email arrival

### 3.3 Apple Sign-In (R4 device leg — CRITICAL)
**Pre-req:** Backend has the Apple Service ID + .p8 wired in Supabase (Task 1.N.2 must be CLOSED).

- [ ] Login screen on iOS shows **"Sign in with Apple"** button (gated by `isAppleSignInAvailable`)
- [ ] On Android, the same button is **NOT visible** (correctly gated off)
- [ ] Tap Apple Sign-In on iOS → native Apple sheet appears → authenticate with Touch/Face ID
- [ ] Backend `POST /api/v1/auth/social-login` called with `provider: 'apple'` + `id_token`
- [ ] Returns 200 with valid Supabase session
- [ ] **id_token validation against Supabase succeeds** — if Supabase says invalid audience/issuer, R4 is RED and the 3-leg checkpoint is wrong somewhere
- [ ] User lands on Home (new Apple user → 17-step onboarding first)

### 3.4 Google Sign-In (Sentry baseline regression check)
- [ ] Tap Google Sign-In on Login → native Google account picker → select account
- [ ] **No `RNGoogleSignin` native crash** (this was Sentry baseline issue — verify ZERO recurrence)
- [ ] Backend `social-login` returns 200 with Supabase session
- [ ] User lands on Home

### 3.5 Refresh-token mutex probe (R9 device leg)
**Setup:** stay logged in. Force a stale access-token state — easiest path is to wait until expiry (Supabase default 1hr) OR manually invalidate by overwriting the SecureStore access-token value via Expo dev menu console.

- [ ] Trigger 3 concurrent authenticated API calls within ~100ms (e.g., open Profile → History tab → trigger `getCohortProfile()` + `getComparisonHistory()` + `getPreferences()` near-simultaneously)
- [ ] In network inspector, observe: each authenticated request first hits API with stale token → backend returns 401
- [ ] **Verify exactly 1 `POST /api/v1/auth/refresh` network call fires** (NOT 3) — confirms the module-scope singleton Promise mutex from commit `03b9139` is doing its job
- [ ] All 3 original requests retry successfully with new access token

### 3.6 Logout + session clearing
- [ ] Profile → Log Out → returns to Login screen
- [ ] Inspector: `POST /api/v1/auth/logout` fires; token revoked in Redis blacklist
- [ ] SecureStore access-token + refresh-token cleared (relaunch → splash → Login, NOT Home)

---

## Section 4 — Compare flow (text + camera + URL)

### 4.1 Text compare (SSE streaming)
- [ ] Home → enter "iPhone 16 Pro" + "Galaxy S25 Ultra" → Compare
- [ ] Results screen min-display floor: LoadingRings visible ≥ 1.2s even if backend cache hit
- [ ] SSE event order observable: specs → prices → reviews → scoring → verdict → complete
- [ ] Final verdict renders with winner + tradeoffs + price comparison
- [ ] No "estimated" / "indicative" copy visible in the user-rendered UI (backend may emit enum but UI substitutes)

### 4.2 Camera compare
- [ ] Home → camera scan chip → ScanCameraScreen opens fullscreen modal
- [ ] Tap shutter → image fills slot 1
- [ ] Tap shutter again → image fills slot 2
- [ ] Compare CTA enables → tap → identifyFromImages backend call → Results lands
- [ ] If only 1 product identified → "need_more_photos" empty state appears (NO crash)

### 4.3 URL compare
- [ ] Home → switch to URL mode → paste two product URLs from e.g. apple.com + samsung.com
- [ ] Compare → Results renders; price + spec extraction from URLs

### 4.4 Min-display floor 1.2s observable
- [ ] Compare a query you've already run (warm cache) → response is near-instant from backend
- [ ] **Still observe ≥ 1.2s of LoadingRings** before Results renders (design § 3 brand-moment floor)

---

## Section 5 — History detail (Migration 026 backfill verification)

Goal: confirm Ahmed's 5 backfilled v2 comparisons appear and the 1 unrenderable v1 row stays hidden.

### 5.1 History list
- [ ] Tap History tab → date-grouped SectionList renders
- [ ] Ahmed's 5 backfilled comparisons appear:
  - iPhone 14 vs Galaxy S24 Ultra
  - 2× LV Mesh vs Hermès
  - HealthAid vs NOW D3
  - iPhone 15 vs Galaxy S24
- [ ] The v1 unrenderable Sony WH-1000XM5 vs Bose QuietComfort Ultra (id `e154397c-...`) does **NOT** appear

### 5.2 Cold-open history detail
- [ ] Tap any of the 5 backfilled rows → Results screen loads via `getComparison(id)`
- [ ] Min-display floor 1.2s respected on cold open
- [ ] Full payload renders (verdict + scoring + product cards)
- [ ] Back → returns to History list with scroll position preserved

### 5.3 Delete from history
- [ ] Swipe left on any row → Delete affordance appears
- [ ] Tap Delete → row vanishes optimistically; backend `DELETE /api/v1/comparisons/{id}` fires
- [ ] Re-load History → row stays gone (server-side delete confirmed)

### 5.4 Hidden v1 row gate
- [ ] Cannot navigate to the e154397c v1 row from anywhere in the UI
- [ ] If you manually craft a deep link to `qaren://comparison/e154397c-...` → ResultsScreen shows `results.emptyState.notFound` copy (1.F.5 contract)

---

## Section 6 — Profile + 5 toggles (R18 + R23 device legs)

### 6.1 R23 — AI-sharing default OFF on fresh signup
**Pre-req:** Create a fresh signup via Section 3.1 with a brand-new email.

- [ ] After onboarding completion, navigate to Profile → **"Share AI data" toggle reads OFF** (verify visually — switch is in off position)
- [ ] Network inspector: `GET /api/v1/auth/preferences` returns either `ai_sharing_enabled: false` or `ai_sharing_enabled: undefined`
- [ ] Existing users who had it ON before this bundle are NOT affected (cross-check via Supabase MCP from dispatcher — already QA-verified pre-build, just reconfirm post-build)

### 6.2 R18 — 5 toggle optimistic UI + rollback
- [ ] **AI sharing toggle** — tap → switch flips immediately (< 100ms perceived); network inspector shows `PUT /api/v1/auth/preferences` returning 200
- [ ] **Smart Decision Notifications master toggle** — tap → flips immediately; same `PUT /preferences` path; 3 sub-toggles below become enabled
- [ ] **Decision Insights sub-toggle** — tap → flips immediately; network inspector shows `PUT /api/v1/auth/reengagement-subs` with body `{decision_insights, peer_decision_updates, decision_retrospectives}` (Backend 228ff63 plural-keyed contract)
- [ ] **Peer Decision Updates sub-toggle** — tap → flips; `peer_decision_updates` value flips in body
- [ ] **Decision Retrospectives sub-toggle** — tap → flips; `decision_retrospectives` value flips in body

### 6.3 Rollback on artificial network failure
- [ ] Enable Airplane mode → tap any sub-toggle → switch flips OPTIMISTICALLY → after ~2s timeout, **switch reverts** to previous state + Alert appears with `profile.notifs.errorTitle` copy (EN: "Setting didn't save" / AR: "الإعداد لم يُحفظ")
- [ ] Disable Airplane mode → retry → succeeds

### 6.4 Edit Profile + Edit Style Profile (Bundle D 1.F.3 device leg)
- [ ] Profile → Edit Profile → modal opens
- [ ] Tap "Edit style profile" → Onboarding modal opens in **edit mode** (NOT a no-op; should land at step 8 priorities, NOT step 1)
- [ ] Adjust priorities/budget/brand_attitude → Continue → reaches step 10 brand_attitude → "Finish" → modal closes back to Edit Profile
- [ ] Network inspector: `PUT /preferences` fired with updated style fields
- [ ] No transition through step 11+ (attribution / cohort_proof / loading / reveal / account / notifications)

### 6.5 Email change requires current password
- [ ] Profile → Edit Profile → Email change → backend requires current password gate
- [ ] Account deletion → cascade fires → verify via dispatcher Supabase MCP that the user row + comparisons + referral_invites + user_events ALL clear

---

## Section 7 — Camera help overlay (R17 device leg)

- [ ] Home → camera scan chip → ScanCameraScreen
- [ ] Tap the **`?` button** at the top-right of the camera surface
- [ ] **CameraHelpOverlay** appears as a translucent modal with 3 numbered steps:
  - 1 — "Place each item flat with good lighting"
  - 2 — "Tap the shutter to fill slot 1, then slot 2"
  - 3 — "Hit Compare and we'll match them side by side"
- [ ] Tap outside the card → overlay closes (tap-to-dismiss)
- [ ] Reopen → tap the X close button → overlay closes
- [ ] Switch language to Arabic → reopen overlay → AR copy renders (`صوّر المنتجين`, etc.) with no fallback boxes
- [ ] No haptic on open / close (Build Principle #4 — overlay open isn't in approved chip/stage/winner vocabulary)

---

## Section 8 — Sentry MCP watch during smoke

**Workflow:** record session start timestamp BEFORE you start Section 1. After completing all sections, hand off to QA for `firstSeen:` window query.

### 8.1 Pre-smoke baseline capture
- [ ] Record current wall time: `_____` (ISO 8601, UTC). Reference: docs/plans/bundle-d-sentry-baseline-2026-05-23-v2.txt
- [ ] Note: any errors firing between baseline and pre-smoke are NOT your problem; just ensures the watch window is well-defined

### 8.2 During smoke
- [ ] Keep the app foregrounded during the full 45-60 min walkthrough
- [ ] If any UI error / red-box / crash appears, screenshot + note which section + which step
- [ ] Do NOT trigger errors deliberately outside Section 6.3 (artificial network failure is sanctioned)

### 8.3 Post-smoke handoff
- [ ] Record session end timestamp: `_____`
- [ ] Ping QA with the time window so they can `mcp__plugin_sentry_sentry__search_issues firstSeen:>{start} firstSeen:<{end}`
- [ ] **Pass criteria:** ZERO new Sentry issue types over baseline `v2`. The single rollback Alert from 6.3 is expected (NOT a Sentry event — it's an Alert.alert call, not an exception)

---

## Section 9 — Screenshots

Cross-references `docs/runbooks/bundle-d-screenshot-capture.md` (Native/Ops own that runbook).

### 9.1 Required App Store Connect screenshots
Per Native/Ops's capture list — at minimum:
- [ ] **Home (EN)** — TwoInputShell empty state with hero copy
- [ ] **Home (AR)** — RTL mirror of the same
- [ ] **Results (EN)** — winner + verdict + price tradeoffs
- [ ] **Results (AR)** — same in Arabic
- [ ] **History (EN)** — date-grouped list with 4-5 entries
- [ ] **Profile (EN)** — 5-toggle layout + cohort badge

Devices: 6.7" iPhone Pro Max (App Store required) + Android 6.4" if shipping concurrently.

### 9.2 Pass through any pending captures
- [ ] Flag to Native/Ops: which screenshots are still pending after this smoke run
- [ ] If app-icon assets are still Expo placeholders (Task 4.N.1b PENDING), screenshots are **NOT** ready for ASC upload — flag to team-lead

---

## Smoke completion checklist

When all sections above are green:
- [ ] All 9 sections completed; failures (if any) documented + escalated
- [ ] Sentry watch window handed off to QA; ZERO new types vs baseline v2
- [ ] Screenshots captured (Section 9) or pending-list logged
- [ ] R4 + R10 + R16 + R17 + R18 + R23 device-leg checkboxes can flip from `device-smoke pending` → ADDRESSED in `memory/BUNDLE_D_RISK_LEDGER.md`
- [ ] Ping team-lead with: "Bundle D EAS smoke complete, N findings, ready for TestFlight upload" OR list of blockers

## Rollback path

If a critical section fails (Section 3 Apple Sign-In, Section 6.3 rollback, Section 2 any of A-L, Section 5 backfill missing):
- [ ] Do NOT submit to TestFlight
- [ ] Block-message the appropriate lane (Native/Ops for build/auth-native, Backend for API contract, Frontend for UI behavior)
- [ ] Capture screenshot + Sentry event ID + network request ID where applicable
- [ ] Bundle D PR stays open until re-smoke green

## References

- Bundle D risk ledger: `memory/BUNDLE_D_RISK_LEDGER.md`
- Frontend anchor: `memory/BUNDLE_D_FRONTEND_ANCHOR.md`
- Bundle B contract preservation (unit gate): `SmartCompareApp/__tests__/HomeScreen.bundleB.contract.test.tsx` (commit `3def805`)
- Per-page contract preservation: `SmartCompareApp/__tests__/Screens.bundleD.contract.test.ts` (commit `cbdd183`)
- Sentry baseline v2: `docs/plans/bundle-d-sentry-baseline-2026-05-23-v2.txt`
- Screenshot runbook: `docs/runbooks/bundle-d-screenshot-capture.md`
- DNS + hosting: `docs/runbooks/bundle-d-dns-and-hosting.md`

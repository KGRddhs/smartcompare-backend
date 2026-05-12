# Bundle B/C/D Consolidated — Pre-launch Polish + Referral Hardening — Design

**Date:** 2026-05-12
**Author:** Ahmed + Claude (brainstorm session)
**Status:** Approved — ready for implementation planning
**Bundle:** B + C + D consolidated into a single PR
**Worktree:** `../smartcompare-bundle-bcd`
**Branch:** `feature/bundle-bcd`
**Bundle A precedent:** `docs/plans/2026-05-11-bundle-a-p0-fixes-design.md` (merged as PR #3, `f9bf38f`)

---

## Why this bundle exists

Bundle A shipped on 2026-05-11 covering P0 tester-feedback fixes (gift system, device-bound free tier, EditProfile, EditPreferencesFlow, ContactUs, Legal, ToggleRow, i18n discipline). Bundles B/C/D were deferred until Bundle A tester validation. This consolidated bundle merges all three deferred scopes into a single PR while Bundle A's baseline OTA is live in the `preview` channel and stability is being verified.

**Trigger for consolidation:** with only ~0-2 active testers pre-launch, running B/C/D as three separate PRs would waste agent-team setup overhead three times. Consolidating lets one 4-Opus team complete the entire polish + referral-hardening surface in a single pass, then ship one EAS dev build for combined verification.

---

## Goals + non-goals

### Goals (8 items, all in scope)

1. **Arabic deep clean** (Bundle B) — AI-assisted proofread of `ar.json`, diff approved by Ahmed before commit
2. **Cal-AI-style camera redesign** (Bundle C, expanded scope) — fullscreen scanner with reticle, dual image slots, gallery picker, replacing the current inline camera card
3. **Type-input "you need TWO products" UX hint** (Bundle C) — inline hint in SearchOverlay
4. **Category chip emoji → lucide icon glyphs** (Bundle C)
5. **Header logo glyph** (Bundle C) — SVG `<QarenLogo />` component replacing `<Text>Qaren</Text>`
6. **Cal-AI micro-animation polish** (Bundle C) — mode-chip spring, capture-button feedback, winner-reveal scale
7. **Referral install-survival + lifetime device cap** (Bundle C/D straddler, restructured) — hybrid DIY (Play Install Referrer + iOS clipboard), 3 lifetime per device, signup-decrement, 7-day bonus expiry
8. **Performance audit + obvious fixes** (Bundle D) — bundle-visualizer, Reanimated worklet inventory, SVG primitive count, fix obvious wins only

### Non-goals (explicitly out of scope)

| Item | Reason |
|---|---|
| Arabic-as-default locale | DROPPED in Bundle A — device-locale stays. Do not re-propose. |
| Avatar photo upload | Needs S3/Supabase Storage + image picker; separate later ticket |
| Branch.io / AppsFlyer / paid SDKs | Branch's free tier was paywalled to $199/mo during this brainstorm; replaced with hybrid DIY |
| Phone heat on Expo Go | Not a real bug per CLAUDE.md — Expo Go dev mode characteristic |
| iHerb / Scrape.do timeouts | Known backend bugs in CLAUDE.md "Known Remaining Bugs", not pre-launch P0 |
| ToS / Privacy content rewrite | Owned by `docs/plans/2026-05-06-tos-fact-base.md` |
| iOS TestFlight upload | Gated on Apple Developer enrollment ($99/yr) |
| EAS production build / Play Store submission | Closer-to-launch concern; this bundle ends at one internal dev build |

---

## Section 1 — Scope matrix

| # | Item | Sub-bundle | Resolution | Primary files |
|---|---|---|---|---|
| 1 | Arabic deep clean | B | AI-assisted proofread; diff to `.drafts/ar-proofread.diff`; Ahmed approves before commit | `SmartCompareApp/src/i18n/ar.json` |
| 2 | Cal-AI camera redesign | C (expanded) | Full-screen modal route from Home; reticle; 2 slots; gallery picker | `ScanCameraScreen.tsx` (new), `ScannerReticle.tsx` (new), `ImageSlotRow.tsx` (new), `App.tsx`, `HomeScreen.tsx` |
| 3 | Type-input UX hint | C | Inline hint in SearchOverlay until 2 distinct queries entered | `SearchOverlay.tsx` |
| 4 | Category glyphs | C | Lucide icons replace 9 emoji codepoints | `CategorySelector.tsx` |
| 5 | Header logo | C | New `<QarenLogo />` SVG; swap in Home/Profile/History/Splash headers | `QarenLogo.tsx` (new) + ~5 screens |
| 6 | Animation polish | C | Mode-chip spring, capture-button press, winner-reveal scale | `HomeScreen.tsx`, `ResultsScreen.tsx` |
| 7 | Referral hardening | C/D straddler | Hybrid DIY install-survival + lifetime device cap + signup-decrement + share-disable at 3 + 7-day expiry | `branchService.ts` → renamed `attributionService.ts` (new), `playInstallReferrerService.ts` (new), `clipboardFallbackService.ts` (new), `referral_service.py`, Migration 023, Cloudflare Worker for `qaren.app/r/{code}` web fallback |
| 8 | Perf audit + obvious fixes | D | Measure → report → fix only obvious wins (>50 KB bundle savings OR dropped frames) | `docs/runbooks/bundle-bcd-perf-audit.md` (new) + targeted fixes |

**Camera redesign reference:** Cal-AI-style layout — fullscreen viewfinder, centered scanner reticle (4 corner brackets with subtle pulse), `×` close top-left, `?` help top-right, dual image slots above the shutter (1 of 2 / 2 of 2), shutter button center-bottom, flash toggle bottom-left, gallery picker bottom-right, "Compare" CTA pill above shutter once both slots filled.

---

## Section 2 — Agent split + ownership

**Team: 4 Opus agents. Bundle A pattern. Strict QA protocol per Ahmed's instruction:**
- Features must be 100% complete before disband
- Every member QAs at least one other member's work; subpar/missed work returns with specifics
- Idle agents write RED→GREEN tests targeting ≥80% coverage OR wait on incoming QA
- Work is delegated, not duplicated; file ownership is disjoint

### Agent #1 — `backend-bcd` (Opus)
- **Item 7b:** Migration 023, `referral_service.py` integration of lifetime device cap + signup decrement, 7-day expiry constant, share-quota check for disable state, `attribution_service.py` (renamed from branch_service.py to reflect the DIY pivot)
- **Item 1:** Arabic AI-assisted proofread; produces `.drafts/ar-proofread.diff`; awaits Ahmed approval before committing `ar.json`
- Backend tests for above

### Agent #2 — `frontend-bcd` (Opus)
- **Item 2:** Camera redesign (ScanCameraScreen + ScannerReticle + ImageSlotRow + App.tsx modal route + HomeScreen integration)
- **Item 3:** Type-input UX hint in SearchOverlay
- **Item 4:** Category glyphs (lucide swap)
- **Item 5:** QarenLogo + header swaps
- **Item 6:** Animation polish
- **Item 7a:** Frontend referral changes — Play Install Referrer wiring, clipboard fallback service, `ReferralStatusCard` lifetime counter UI, ShareBottomSheet disable state at 3 lifetime, bonus countdown copy updates for 7-day
- **Item 8:** Frontend perf audit + obvious-win fixes

### Agent #3 — `test-bcd` (Opus)
- RED→GREEN tests written in lockstep with implementation
- Backend coverage: webhook signature (if applicable), Migration 023 idempotency, referral_service lifetime cap enforcement, device-bound cross-account counter, signup decrement, share-disable behavior, 7-day expiry computation
- Frontend coverage: ScanCameraScreen permission flow, slot fills, gallery picker, ScannerReticle render, ImageSlotRow add/remove, QarenLogo render, CategorySelector lucide render, SearchOverlay hint visibility, animation hooks (smoke), Play Install Referrer mock, clipboard fallback consent, ShareBottomSheet disable state
- **Coverage gate ≥80% on every new file** (frontend + backend); blocks merge if not met

### Agent #4 — `qa-bcd` (Opus)
- Spec compliance vs. this design doc + Cal-AI reference image
- Accessibility sweep: RTL on every new screen, screen-reader labels (shutter, slots, close, gallery, reticle), tap target 44×44, contrast
- i18n sweep: every new user-facing string in EN+AR; ESLint `i18next/no-literal-string` passes
- Integration: Play Install Referrer payload → backend attribution shape end-to-end; clipboard handoff → RegisterScreen pre-fill
- Smoke testing: every item except install-survival on Ahmed's Expo Go during development; full bundle including referral on end-of-bundle EAS dev client
- Writes `docs/plans/2026-05-12-bundle-bcd-qa-report.md` before disband

### Cross-QA pairings (mandatory before disband)

| Reviewer | Reviewing | Focus |
|---|---|---|
| qa-bcd | backend-bcd | Migration 023 idempotency, lifetime cap logic, attribution shape, Arabic diff |
| qa-bcd | frontend-bcd | Camera UX vs reference, glyph swaps complete, animation polish doesn't break worklets, clipboard consent copy |
| backend-bcd | frontend-bcd | Install Referrer payload + clipboard handoff payload match backend expectations |
| frontend-bcd | backend-bcd | Migration 023 column shape + endpoint response shape match RN expectations |
| test-bcd | qa-bcd | QA report covers all 8 items; no spec drift missed |
| test-bcd | backend-bcd + frontend-bcd | Coverage report ≥80%; no tautological tests; no skipped tests |

**Send-back protocol:** reviewer opens `REWORK: <thing>` TaskCreate item assigned to the original agent; specific description, not vague feedback. Original agent must address before disband.

### Idle protocol

When any agent finishes their primary work, in order:
1. Write additional RED→GREEN tests targeting uncovered edge cases
2. Pull extra cross-QA on a peer's PR
3. Write doc/runbook contributions (e.g. tester onboarding for dev client APK install)
4. Only after all 3 exhausted: wait on incoming QA feedback

---

## Section 3 — Sequencing + dependency edges

### Phase 1 — Foundation (parallel, ~day 1)

| Agent | Task | Edges |
|---|---|---|
| backend-bcd | Apply Migration 023 (`users.lifetime_invites_consumed` + index on `device_fingerprint_hash`) via MCP | none — start immediately |
| backend-bcd | `attribution_service.py` skeleton + signup-decrement scaffold in `referral_service.py` | blocked-by: Migration 023 applied |
| backend-bcd | Arabic proofread first pass → `.drafts/ar-proofread.diff` | none — fully independent |
| frontend-bcd | `ScanCameraScreen.tsx` skeleton + modal route in `App.tsx` | none |
| frontend-bcd | `ScannerReticle.tsx` SVG + `ImageSlotRow.tsx` components | none |
| frontend-bcd | Install `react-native-play-install-referrer` (verify presence first) | none |
| frontend-bcd | `clipboardFallbackService.ts` skeleton | none |
| test-bcd | RED tests: Migration 023 columns, ScanCameraScreen permission flow, ImageSlotRow slot fill/remove, ScannerReticle render | rolling |
| qa-bcd | Watch for spec drift; flag design ambiguities back to Ahmed early | continuous |

### Phase 2 — Core integration (parallel after Phase 1, ~day 2-3)

| Agent | Task | Edges |
|---|---|---|
| backend-bcd | Lifetime device cap in `referral_service.try_trigger_loop2` — query `SUM(lifetime_invites_consumed) WHERE device_fingerprint_hash = $1`; reject if ≥3 | blocked-by: Migration 023 applied |
| backend-bcd | Signup decrement: increment inviter's `lifetime_invites_consumed` on receiver registration via invite | blocked-by: above |
| backend-bcd | 7-day expiry constant in `create_redemption()`: `expires_at = now() + interval '7 days'` (was 3 days) | none |
| backend-bcd | Share endpoint stops decrementing on share; only returns informational `lifetime_invites_remaining` | blocked-by: signup decrement |
| backend-bcd | Arabic diff iteration → Ahmed approves → commit `ar.json` | blocked-by: Ahmed approval |
| frontend-bcd | Camera fullscreen wired in HomeScreen (gut inline camera, navigate to ScanCamera modal) | blocked-by: ScanCameraScreen + ImageSlotRow scaffolds GREEN |
| frontend-bcd | Type-input "you need TWO products" hint in SearchOverlay | none |
| frontend-bcd | Category glyphs in CategorySelector (lucide swap, per-icon imports) | none |
| frontend-bcd | `QarenLogo.tsx` + header swaps (Home, Profile, History, Splash) | none |
| frontend-bcd | Play Install Referrer service (Android native module) + RegisterScreen integration | blocked-by: native module installed |
| frontend-bcd | Clipboard fallback service + RegisterScreen consent prompt | none |
| frontend-bcd | ReferralStatusCard: lifetime counter UI (replaces weekly cap UI) | blocked-by: backend status endpoint returns `lifetime_invites_used`/`lifetime_invites_remaining` |
| frontend-bcd | ShareBottomSheet disable state at 3 lifetime + "gifted to 3 friends" copy | blocked-by: lifetime counter UI |
| frontend-bcd | BonusCountdownCard + push notification copy: "expires in N days" → 7-day version | none |
| test-bcd | GREEN tests for Phase 1; RED tests for Phase 2 (lifetime cap, signup decrement, install referrer, clipboard, share disable, 7-day) | rolling |
| qa-bcd | Spec review each item as it ships; backend ↔ frontend contract verification | rolling |

### Phase 3 — Polish (after Phase 2, sequential within frontend)

| Agent | Task | Edges |
|---|---|---|
| frontend-bcd | Animation polish — mode-chip spring, capture-button feedback, winner-reveal scale | blocked-by: camera redesign + Home structure finalized |
| frontend-bcd | Cloudflare Worker for `qaren.app/r/{code}` web fallback page (sets clipboard, redirects to store) | none |
| frontend-bcd | Perf audit report + obvious-win fixes (CohortBarChart dot density audit, dropped frame check, dead dep removal) | blocked-by: all FE features merged |
| backend-bcd | Backend perf checks (slow-query audit on logs if available); attribution endpoint observability | none — runs parallel with FE Phase 3 |
| test-bcd | Mutation testing + coverage push to ≥80% on every new file | blocked-by: all features GREEN |
| qa-bcd | Accessibility sweep (RTL, screen reader, tap targets, contrast); full integration E2E | blocked-by: Phase 3 features merged |

### Phase 4 — Exit gate (sequential)

| Step | Owner | Edges |
|---|---|---|
| 1 | Full jest + tsc + ESLint i18next gate passes | test-bcd | blocked-by: Phase 3 complete |
| 2 | Coverage ≥80% confirmed on every new file | test-bcd | blocked-by: step 1 |
| 3 | All 6 cross-QA pairs sign off | all agents | blocked-by: step 2 |
| 4 | `docs/plans/2026-05-12-bundle-bcd-qa-report.md` written | qa-bcd | blocked-by: step 3 |
| 5 | EAS dev build (`eas build --profile development --platform android`) | Ahmed runs interactively | blocked-by: step 4 |
| 6 | Ahmed installs APK + smokes Branch + full bundle per qa-bcd's smoke script | Ahmed | blocked-by: step 5 |
| 7 | Ahmed approves → PR `feature/bundle-bcd` → `main` | qa-bcd | blocked-by: step 6 |

### File conflict notes

- `HomeScreen.tsx` touched by: camera redesign (Phase 2), header logo (Phase 2), animation polish (Phase 3) — all `frontend-bcd`, sequential commits within the same agent
- `ResultsScreen.tsx` touched only by animation polish (Phase 3) — single touchpoint
- `App.tsx` touched by camera modal route (Phase 1) + Play Install Referrer init (Phase 2) + clipboard service init (Phase 2) — all `frontend-bcd`, sequential
- `referral_service.py` touched by: lifetime cap (Phase 2), signup decrement (Phase 2), 7-day expiry (Phase 2), share endpoint behavior (Phase 2) — all `backend-bcd`, sequential

### Cross-cutting invariants

- **Path-restricted commits** — no `git add .` / `git add -A` in team sessions (per CLAUDE.md)
- **Every new user-facing string** lands in BOTH `en.json` and `ar.json` in the same commit
- **No `console.log` outside `__DEV__` guard**
- **No `useNativeDriver: false`** in new animation code (Reanimated 4 worklet-native only)
- **Lucide icon imports per-icon, not barrel** — preserves tree-shaking

---

## Section 4 — Architecture (revised after Branch.io drop + late-session referral changes)

### 4.1 Install-survival: hybrid DIY (replaces Branch.io)

**Branch.io was the original design but was dropped when its free tier was discovered to have been paywalled to $199/mo.** Replaced with a hybrid platform-native approach delivering ~85% of Branch's value at $0/mo.

#### Android — Google Play Install Referrer API
- Native module `react-native-play-install-referrer`
- When user taps `qaren.app/r/QR-XXXXXX` and installs via Play, Play preserves URL query params through the install funnel
- On first app launch, `InstallReferrerClient` retrieves the original referrer → app parses `QR-XXXXXX` → routes to Register pre-filled + locked
- 100% reliable on Play Store installs (not sideloads — but sideloads are dev-only territory)
- Better than Branch's Android fingerprinting (which is also fingerprint-guessing)

#### iOS — clipboard fallback
- No SDK required
- Cloudflare Worker at `qaren.app/r/{code}` serves a JS page that:
  1. Copies the code to clipboard
  2. Shows "Code copied — open Qaren after install"
  3. Redirects to App Store
- On Register mount, app calls `Clipboard.getStringAsync()` exactly once
- If string matches `^QR-[A-Z0-9]{6}$` → shows explicit consent banner "We saw an invite code on your clipboard. Use it?" → user taps yes → code pre-fills
- iOS 14+ shows system clipboard-paste banner (privacy notice; expected behavior)
- ~70% reliability (user may have copied something else between install and first launch; explicit consent is the privacy trade-off)
- **Apple review consideration:** read clipboard only on RegisterScreen mount; ALWAYS show consent prompt; document in App Privacy

#### Web fallback page (Cloudflare Worker)
- Free tier handles 100k req/day — well above realistic referral traffic
- Detects user-agent → routes Android users via Play Store with `?referrer=QR-XXXXXX` parameter; iOS users via App Store + clipboard injection
- ~10 lines of JS; deployed via Wrangler CLI

### 4.2 Referral cap model: 3 lifetime per device

**Changed from Bundle A's 3-per-week per-user model.**

| Aspect | Bundle A (current) | Bundle B/C/D (new) |
|---|---|---|
| Cap | 3 per week per user | **3 LIFETIME per device** |
| Decrement | At share time | **At receiver's signup completion** |
| Reset | Weekly | **Never** |
| Anti-abuse boundary | Per-user | **Per device** (uses `device_fingerprint_hash` from Migration 021) |

**Why:** Bundle A's weekly cap penalized failed shares (counter ticked even if no one signed up). The lifetime device-bound model aligns with Bundle A's device-bound free-tier philosophy (Migration 021): the device is the anti-abuse boundary, not the account. A bad actor logging out + creating account #2 on the same phone still hits the same 3 lifetime cap.

### 4.3 Share gating: disable at 3 lifetime used

- `ShareBottomSheet` primary CTA disables (gray) when sender has 3 lifetime successful referrals
- Replaces with microcopy: `"You've gifted Qaren to 3 friends — thank you 🎁"` (gift framing, not punitive)
- AR equivalent: `"شاركتَ قارن مع 3 من أصدقائك — شكراً لك 🎁"`
- Copy button still works (lets sender re-share with someone the original receiver may have lost the link to)
- EN + AR i18n keys: `referrals.share.maxReached.title`, `referrals.share.maxReached.message`

### 4.4 Bonus expiry: 7 days (was 3 days)

- Bundle A's Migration 018 added `referral_redemptions.expires_at` with a 3-day window from issue
- New default: **7 days from issue**
- No new migration needed — column exists, duration is a code constant in `referral_service.create_redemption()`
- Push reminder still fires 24 hours before expiry (i.e., on day 6 now, not day 2)
- Existing 3-day expiry rows in production keep their original deadlines — only new redemptions get 7 days
- Copy updates in `BonusCountdownCard`, push notification template, expiry warning: `"expires in {{count}} day"` / `"expires in {{count}} days"` plural

### 4.5 Migration 023

```sql
-- 023_referral_lifetime_cap.sql
-- Adds lifetime device-bound referral cap; drops weekly per-user cap.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS lifetime_invites_consumed INT NOT NULL DEFAULT 0;

-- Drop weekly counter — no longer used; data is preserved in audit log if needed
ALTER TABLE users
  DROP COLUMN IF EXISTS weekly_invites_used;

-- Ensure index on device_fingerprint_hash for cross-account device queries
CREATE INDEX IF NOT EXISTS idx_users_device_fingerprint_active
  ON users(device_fingerprint_hash)
  WHERE device_fingerprint_hash IS NOT NULL;
```

Applied via Supabase MCP (`mcp__plugin_supabase_supabase__apply_migration`) before backend code touches the new column.

**Rollback** (saved at `migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql`):
```sql
ALTER TABLE users DROP COLUMN IF EXISTS lifetime_invites_consumed;
-- weekly_invites_used would need restore from backup if needed
DROP INDEX IF EXISTS idx_users_device_fingerprint_active;
```

### 4.6 Cal-AI camera redesign layout

Per Ahmed's reference screenshot, full-screen modal route launched from Home's "Scan" mode chip:

```
┌──────────────────────────────────┐
│  ×                            ?  │   ← close (preserves Home state)  /  help bottom-sheet
│                                  │
│                                  │
│         ┌──────────┐             │
│         │          │             │   ← scanner reticle (SVG 4 corner brackets,
│         │  RETICLE │             │      subtle pulse animation, ~70% viewport width)
│         │          │             │
│         └──────────┘             │
│                                  │
│                                  │
│        ┌────┐ ┌────┐             │   ← image slots (80×80, dashed when empty,
│        │ 1  │ │ 2  │             │      thumbnail + × when filled, "1 of 2" caption)
│        └────┘ └────┘             │
│                                  │
│           ⓘ 1 of 2               │
│                                  │
│              ◯                   │   ← shutter button (large white circle)
│                                  │
│   ⚡                       🖼       │   ← flash toggle (L) / gallery picker (R)
└──────────────────────────────────┘
```

- Shutter tap → capture into next empty slot
- Gallery icon → `expo-image-picker.launchImageLibraryAsync` → user picks from photos → fills next empty slot
- Slot tap → preview + replace
- Slot × → remove (decrements current slot count)
- "Compare" CTA pill appears above shutter once both slots filled → tap = navigate to Results with streaming
- × close returns to Home with slots state PRESERVED in memory (allows user to return and continue)

**Files:**
- New: `SmartCompareApp/src/screens/ScanCameraScreen.tsx` (full-screen modal)
- New: `SmartCompareApp/src/components/ScannerReticle.tsx` (SVG corner brackets + pulse animation)
- New: `SmartCompareApp/src/components/ImageSlotRow.tsx` (2 slots + add/remove logic)
- Modified: `App.tsx` (Modal stack screen `ScanCamera`)
- Modified: `HomeScreen.tsx` (scan-mode chip → navigate to ScanCamera modal; gut inline camera; `MAX_IMAGES = 2`, `MIN_IMAGES = 2`)
- New dep if absent: `expo-image-picker` (Expo bundles natively — works in Expo Go)

### 4.7 Backend changes summary

- **`referral_service.py`:**
  - `try_trigger_loop2()`: query `SUM(lifetime_invites_consumed) FROM users WHERE device_fingerprint_hash = inviter.device_fingerprint_hash`; reject if ≥ 3
  - On Loop 2 trigger success: increment inviter's `lifetime_invites_consumed`
  - `create_redemption()`: `expires_at = now() + interval '7 days'` (was 3)
  - `get_share_quota_status(user_id)`: returns `{lifetime_used, lifetime_remaining}`
- **Share endpoint (`POST /api/v1/referrals/share`):**
  - No longer decrements counter
  - Returns informational `lifetime_invites_remaining` for FE to gate UI
  - Still creates `referral_invites` row + grants Loop 1 deep-review credit
- **Status endpoint (`GET /api/v1/referrals/status`):**
  - Replaces `weekly_invites_used/remaining` with `lifetime_invites_used/remaining`
- **`attribution_service.py`:** parses Play Install Referrer payload from FE; correlates `referrer=QR-XXXXXX` parameter to invite; routes through `link_invite_to_user`

### 4.8 Frontend changes summary

- **`playInstallReferrerService.ts`** (new) — Android-only; reads Play Install Referrer on app startup; emits parsed code via React context
- **`clipboardFallbackService.ts`** (new) — iOS-only; reads clipboard on RegisterScreen mount once; emits parsed code with consent prompt
- **`attributionService.ts`** (new) — unified interface; chooses Play Install Referrer on Android, clipboard on iOS; emits code or null
- **`ReferralStatusCard.tsx`** — replaces weekly counter UI with lifetime counter; i18n: `referrals.status.lifetime`
- **`ShareBottomSheet.tsx`** — disables CTA at 3 lifetime used; shows "gifted to 3 friends" microcopy
- **`BonusCountdownCard.tsx`** — copy update: "expires in N days" for 7-day default
- Push notification template: `"Your bonus comparisons expire in 24 hours — use them!"` (day-6 timing)

### 4.9 End-to-end happy paths

**Path A — App already installed (works today via Universal Links):**
1. User A taps Share → ShareBottomSheet generates `qaren.app/r/QR-ATAUX9` → native share sheet
2. User B (app installed) taps link → Universal Link → `qaren://redeem?code=QR-ATAUX9` → Register pre-filled + locked
3. User B signs up → backend increments User A's `lifetime_invites_consumed`
4. User B's first comparison → Loop 2 reward → User A's bonus expires in 7 days

**Path B — Android user without app installed:**
1. User A taps Share → link as above
2. User B (no app, Android) taps link → Cloudflare Worker detects UA → redirects to Play Store with `?referrer=QR-ATAUX9` parameter
3. User B installs from Play → opens app → `playInstallReferrerService` reads Play Install Referrer → emits code
4. Register pre-filled + locked → User B signs up → same flow as Path A from step 3

**Path C — iOS user without app installed:**
1. User A taps Share → link as above
2. User B (no app, iOS) taps link → Cloudflare Worker → JS copies code to clipboard → "Code copied — open Qaren after install" → redirects to App Store
3. User B installs from App Store → opens app → RegisterScreen mounts → `clipboardFallbackService` checks clipboard → matches `QR-` pattern → shows consent banner "We saw an invite code. Use it?"
4. User B taps yes → code pre-fills → User B signs up → same flow as Path A from step 3

**Path D — Sender has hit 3 lifetime:**
1. User A taps Share → ShareBottomSheet shows disabled CTA + "Gifted Qaren to 3 friends" microcopy
2. Copy button still active for re-sharing existing link with new recipient (but no new bonus will fire)
3. User B taps existing link → Path A/B/C as above; backend rejects Loop 2 trigger (device cap reached); User B still signs up but receives no bonus

---

## Section 5 — QA protocol + exit criteria

### 5.1 Per-item Definition of Done

| Item | Done gate |
|---|---|
| 1. Arabic proofread | Diff committed; `npx tsc --noEmit` clean; Ahmed approved in writing; qa-bcd plausibility check |
| 2. Camera redesign | ScanCameraScreen launches from Home mode chip; reticle renders with pulse; 2 slots fill via camera AND gallery; Compare CTA gates on both slots; × preserves state; smoke-tested in Expo Go |
| 3. Type-input hint | Hint shows in SearchOverlay until 2 distinct queries; dismisses; EN + AR strings exist |
| 4. Category glyphs | All 9 categories render lucide icons; emoji codepoints fully removed; RTL renders correctly; jest snapshot covers all 9 |
| 5. Header logo | `<QarenLogo />` renders in Home/Profile/History/Splash; AR/EN both pass visual smoke; `<Text>{t('app.name')}</Text>` removed |
| 6. Animation polish | Mode-chip spring on selection; capture-button press scale-down; winner-reveal subtle scale on Results; haptic.light fires; no useNativeDriver:false in new code |
| 7. Referral hardening | Lifetime cap enforced (3 per device); signup decrement works; share disabled at 3; 7-day expiry constant in code; Play Install Referrer wired (Android); clipboard fallback wired (iOS); Cloudflare Worker deployed |
| 8. Perf audit + fixes | `docs/runbooks/bundle-bcd-perf-audit.md` committed with measurements; any fixes reducing bundle >50 KB OR dropped frames documented + applied; CohortBarChart "388 dots" claim verified or corrected |

### 5.2 Suite-level pre-merge gates

test-bcd runs these and fails the merge if any fail:

```bash
# Frontend
npx tsc --noEmit                                  # Must exit 0
npx jest --coverage                                # All pass + ≥80% on every new file
npm run lint                                       # ESLint i18next/no-literal-string passes

# Backend
python -m pytest tests/ -v --timeout=180          # All pass
python -m py_compile app/services/attribution_service.py app/services/referral_service.py
pip-audit -r requirements.txt --strict             # No HIGH/CRIT CVEs
```

**Coverage rule:** ≥80% on every NEW file. Existing files don't regress.

### 5.3 Cross-QA matrix (mandatory before disband)

See Section 2 — 6 reviewer pairings cover all 4 agents both as reviewer and reviewed.

**Send-back protocol:** if reviewer finds subpar/missed work, they open a `REWORK: <thing>` TaskCreate assigned to the original agent with specific description. Original agent must address before disband. No silent approvals.

### 5.4 EAS dev build smoke test (end of Phase 4)

```bash
cd SmartCompareApp
eas build --profile development --platform android   # Ahmed runs interactively
```

Ahmed:
1. Installs the resulting APK on his phone
2. Walks through qa-bcd's smoke-test script:
   - Launch → Onboarding → register (verify clipboard handoff if available)
   - Home → Scan mode → camera fullscreen → capture 1 photo → pick 1 from gallery → Compare → Results
   - Home → Type mode → SearchOverlay → see "need TWO products" hint → enter 2 queries → Compare → Results
   - Profile → Edit Profile → categories with new glyphs
   - Verify QarenLogo in 4 places
   - Verify AR renders correctly when locale switched
   - Verify ShareBottomSheet shows correct lifetime counter
3. Reports any issues; agents rework if found

### 5.5 Final PR sign-off

PR `feature/bundle-bcd` → `main` opens only after:
- ✅ All 8 items DoD ticked
- ✅ Suite-level gates pass
- ✅ Cross-QA matrix all reviewed + acknowledged
- ✅ EAS dev build smoke passed by Ahmed
- ✅ `docs/plans/2026-05-12-bundle-bcd-qa-report.md` written + committed
- ✅ CLAUDE.md updated with Session 46 + new patterns
- ✅ MEMORY.md updated with Bundle B/C/D learnings
- ✅ `git push` BEFORE branch deletion (CLAUDE.md rule)

---

## Section 6 — Risk + rollback

### 6.1 Risk matrix

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Camera redesign breaks existing Home flow during Phase 2 | Med | High | Feature flag `ENABLE_NEW_CAMERA_SCREEN` (default true post-merge, can flip via EAS Update OTA); inline camera fallback preserved one commit |
| Play Install Referrer permission denied on some Android devices | Low | Med | Wrap in try/catch + fallback to clipboard path; receiver always has manual code entry as last resort |
| iOS clipboard prompt rejected by Apple review | Med | High | Read clipboard ONCE on RegisterScreen mount; explicit consent banner BEFORE reading; do NOT auto-paste — show "We saw a code, use it?" prompt; documented in App Privacy; iOS 16+ also auto-shows system clipboard banner |
| Lifetime cap counter desync across logout/re-login | Med | Med | Counter stored on `users.lifetime_invites_consumed` but cross-checked at trigger time via `device_fingerprint_hash` query (SUM across users with same fingerprint). Single source of truth = device |
| Migration 023 drops `weekly_invites_used` with data still in production | Low | Low | No prod data exists yet (referral system was gated OFF in Railway during Bundle A); audit log preserves event-level history if needed |
| 7-day expiry rows leak old 3-day rows | Low | Low | New constant only applies to NEW inserts; existing rows untouched. Integration test asserts old rows keep their existing `expires_at` |
| Reanimated 4 worklet regressions from animation polish | Med | Med | All new worklets use `runOnUI` + `runOnJS` properly; jest-reanimated mock kept in sync; manual smoke on Ahmed's Expo Go before EAS dev build |
| Bundle size regression from lucide icons | Low | Low | Use `lucide-react-native` per-icon imports (NOT barrel import); budget < 10 KB added |
| AR proofread introduces regression (accidentally swaps interpolation token) | Low | High | Ahmed approves diff before commit; all 514 keys preserved (no add/remove); test that `{{count}}`, `{{name}}`, etc. tokens still appear in same positions |
| Cloudflare Worker downtime for web fallback page | Low | Med | Free tier handles 100k req/day, CDN-cached; if worker fails, link returns to Bundle A behavior (App Store redirect, no code recovery) |
| Camera permission flow regression | Med | High | New screen reuses `useCameraPermissions` hook; deny → existing "permission required" fallback; test covers granted/denied paths |
| Race condition: receiver signs up AFTER device cap reached on same device by another user | Low | Low | `try_trigger_loop2` is fail-closed at cap check; receiver completes signup, but no bonus fires; UI shows "thanks for joining via QR-X" without crediting sender |

### 6.2 Rollback strategy

**Item-level rollback (preferred):**

The bundle ships as ~30-50 commits to `feature/bundle-bcd`. Each item is 3-8 commits. If a specific item regresses post-merge:

```bash
git log --grep="^feat(<item>)" --oneline       # Find the item's commits
git revert <first-commit>..<last-commit>        # Range revert
git push origin main
# Railway auto-redeploys backend in ~90s
# EAS Update OTA pushes the JS rollback to existing dev clients
```

**Feature flag rollback (fastest):**

For items behind a flag, flip via EAS Update without a revert:
- `ENABLE_NEW_CAMERA_SCREEN` (frontend constant in `src/config/features.ts`)
- `ENABLE_LIFETIME_REFERRAL_CAP` (frontend + backend reads `os.getenv("ENABLE_LIFETIME_REFERRAL_CAP", "true")`)
- `ENABLE_INSTALL_REFERRER` (Android Play Install Referrer; defaults true)
- `ENABLE_CLIPBOARD_FALLBACK` (iOS clipboard prompt; defaults true)

OTA an update flipping any flag → reaches all dev clients in < 5 min.

**Migration 023 rollback:**

```sql
ALTER TABLE users DROP COLUMN IF EXISTS lifetime_invites_consumed;
DROP INDEX IF EXISTS idx_users_device_fingerprint_active;
-- weekly_invites_used: restore from backup if needed (likely not, pre-launch)
```

Saved at `migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql`. Apply via Supabase MCP if rollback needed.

**Branch deletion rule (CLAUDE.md):**
- `git push origin feature/bundle-bcd` BEFORE any `git branch -d`
- Keep the branch alive for ~30 days post-merge in case rollback needs cherry-pick

### 6.3 Pre-launch gate

If ANY of these surface during Ahmed's EAS dev build smoke test, **rollback the bundle and split into smaller PRs**:
- App crash on launch
- Onboarding broken
- Existing Bundle A features regressed (referral redemption, history, profile editing)
- TypeScript or runtime errors blocking compile/start

### 6.4 Out-of-band emergencies

**Backend gone bad post-merge:**
```bash
railway redeploy <previous-deployment-id>    # rollback to pre-bundle deploy in ~30s
```

**Frontend gone bad post-merge:**
```bash
cd SmartCompareApp
eas update --branch preview --message "EMERGENCY: rollback to Bundle A baseline"
# Re-publishes the Bundle A baseline OTA group (40719e26)
```

---

## Appendix A — Decisions locked in brainstorming session (2026-05-12)

| # | Question | Locked answer |
|---|---|---|
| 1 | Log access path | (b) Proceed with brainstorming; audit logs in parallel |
| 2 | Arabic proofread depth | (b) AI-assisted; Ahmed approves diff before commit |
| 3 | Branch.io vs DIY | Originally (a) full SDK; **changed to hybrid DIY** mid-session after Branch's free tier discovered paywalled to $199/mo |
| 4 | Execution model | 4-Opus team, strict QA protocol, no idling, opus-only |
| 5 | Branch.io testing path | (c) one EAS dev build at end — **now applies to Play Install Referrer + clipboard fallback verification instead** |
| 6 | Perf audit scope | (b) measure + fix obvious wins only |
| late | Referral cap shape | 3 lifetime per device (was 3 weekly per user) |
| late | Decrement timing | At receiver signup (was at share) |
| late | Share button at 3 lifetime | Disabled with gift framing copy |
| late | Bonus expiry duration | 7 days (was 3 days in Bundle A's Migration 018) |

## Appendix B — Logs reviewed

- **EAS:** clean. 1 Android build (FINISHED, runtime 1.0.0, channel `preview`, baseline OTA group `40719e26`). No failed builds. No iOS build yet (gated on Apple Dev $99/yr).
- **Railway:** CLI access blocked — was authenticated as wrong account (`aj3739125@gmail.com` / King Brad); Ahmed's account is `kinghaleem999@gmail.com`. Not pulled. Decision: proceed without; revisit if Sentry surfaces a backend issue.
- **Sentry:** SDK wired in backend (`sentry-sdk[fastapi]`), DSN in Railway env. No `sentry-cli` installed locally, no auth token in env. Not pulled. Pre-launch traffic ~0 testers — unlikely to surface material noise.

---

## Next step

Transition to `writing-plans` skill to convert this design into an executable implementation plan with task DAG, blocking edges, and per-agent task assignments.

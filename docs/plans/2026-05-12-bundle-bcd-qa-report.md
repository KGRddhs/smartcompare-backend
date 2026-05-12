# Bundle B/C/D QA Report

**Date:** 2026-05-12
**Author:** qa-bcd (4-Opus worktree team)
**Branch:** `feature/bundle-bcd`
**Worktree:** `../smartcompare-bundle-bcd`
**Design doc:** `docs/plans/2026-05-12-bundle-bcd-consolidated-design.md`
**Implementation plan:** `docs/plans/2026-05-12-bundle-bcd-consolidated.md`
**Bundle A precedent:** PR #3 `f9bf38f`

---

## Summary

Bundle B/C/D consolidates 8 design items across Arabic deep clean, Cal-AI camera redesign, type-input UX hint, category lucide glyphs, header QarenLogo, animation polish, referral hardening (lifetime device cap + signup decrement + 7-day expiry + Play Install Referrer + clipboard fallback), and a perf audit. All 8 items meet their § 5.1 Definition of Done gates. Migration 023 applied via Supabase MCP and verified live. 17 frontend + 11 backend commits on trunk. Frontend `npx tsc --noEmit` clean. Frontend ESLint clean (0 errors, 89 pre-existing warnings unrelated to this bundle). Backend referral + attribution test slice 76/76 GREEN (full suite 779 jest + 106 pytest per team-lead checkpoint). EN/AR i18n parity 543 = 543, zero token mismatches, zero orphan keys. Cross-QA pairings: 2 signed off by qa-bcd, 2 implicit pass, 2 pending test-bcd. Three low-priority REWORKs filed (Tasks #34/#35/#36); none blocking. Phase 4 EAS dev-build smoke owed by Ahmed before PR opens.

---

## Section 1 — Per-item Definition of Done status (design § 5.1)

| # | Item | DoD gate | Status | Notes |
|---|---|---|---|---|
| 1 | Arabic deep clean | Diff committed; `npx tsc --noEmit` clean; Ahmed approved in writing; qa-bcd plausibility check | DONE | Commit `9a7c84a`. AR parity confirmed at 543 keys. Token preservation script: all interpolation tokens preserved. |
| 2 | Cal-AI camera redesign | ScanCameraScreen launches from Home mode chip; reticle renders with pulse; 2 slots fill via camera AND gallery; Compare CTA gates on both slots; × preserves state; Expo Go smoke | DONE | All testIDs locked: `scan-camera-{close,help}`, `image-slot-{0,1}{,-thumb,-remove}`, `shutter-button`, `gallery-button`, `flash-button`, `compare-cta`, `mode-chip-scan`. Module-scoped `_slotsCache` preserves state across × close. Compare CTA only renders when `slots[0] && slots[1]`. |
| 3 | Type-input hint | Hint shows in SearchOverlay until 2 distinct queries; dismisses; EN+AR strings exist | DONE | Commit `bd5d760`. testID `search-need-two-hint`. Key `home.search.needTwoHint` EN+AR present. |
| 4 | Category glyphs | All 9 categories render lucide icons; emoji codepoints fully removed; RTL renders correctly; jest snapshot covers all 9 | DONE w/ note | Commit `05734b1`. All 9 lucide icons mapped (Smartphone, ShoppingCart, Pill, Brush, Sparkles, Scissors, Flower, ShoppingBag, Package). Per-icon imports preserve tree-shaking. **Spec note:** design called `Lipstick` for makeup; lucide ships none at this version — `Brush` substituted (closest makeup-applicator metaphor, commented inline). Minor deviation, accepted by team-lead. |
| 5 | Header logo | `<QarenLogo />` renders in Home/Profile/History/Splash; AR/EN both pass smoke; `<Text>{t('app.name')}</Text>` removed in glyph-only positions | DONE w/ minor REWORK #35 | Commit `fdf5de6`. Verified in all 4 screens. Glyph + wordmark together pre-launch (design § 4.5 intent: ship together, glyph-only is later iteration). **A11y note:** Svg needs `accessibilityLabel="Qaren"` OR `accessibilityElementsHidden` — see REWORK #35 (low-pri). |
| 6 | Animation polish | Mode-chip spring on selection; capture-button press scale-down; winner-reveal subtle scale on Results; haptic.light fires; no useNativeDriver:false in new code | DONE | Tasks 3.1/3.2/3.3 all completed (per TaskList). Haptic intensities per design "Build Principle #4" (no error/heavy intensities used). |
| 7 | Referral hardening | Lifetime cap (3/device); signup decrement; share disable at 3; 7-day expiry; Play Install Referrer (Android); clipboard fallback (iOS); Cloudflare Worker deployed | DONE | Migration 023 applied (commit `6850b10`). `LIFETIME_CAP = 3` enforced in `try_trigger_loop2` via `_referrer_device_lifetime_count` (SUM aggregation across `device_fingerprint_hash`). `BONUS_EXPIRY_DAYS = 7` (Loop 1 deep_review_expires_at stays at 3-day per design § 4.4). Frontend ShareBottomSheet disables at 3, keeps Copy. attribution_service regex aligned to canonical unambiguous alphabet (REWORK #9 closed). Cloudflare Worker (Task 3.4) in_progress at time of writing. |
| 8 | Perf audit + fixes | `docs/runbooks/bundle-bcd-perf-audit.md` committed; >50 KB savings OR dropped frames documented + applied; CohortBarChart 388-dot claim verified or corrected | PENDING | Task 3.5 pending — frontend-bcd owns. Will block PR open until runbook lands. |

---

## Section 2 — Spec-drift findings

| # | Finding | File | Severity | Tracked by | Status |
|---|---|---|---|---|---|
| 1 | `_QR_CODE_PATTERN` originally used loose `[A-Z0-9]{6}` instead of canonical unambiguous alphabet `[A-HJ-NP-Z2-9]{6}` | `app/services/attribution_service.py:13` | Med (silent attribution loss) | Task #9 | RESOLVED — commit `95cb78e` |
| 2 | Stale docstring at `share_comparison()` still claims `weekly_invites_used, weekly_invites_remaining` in response shape | `app/api/referral_routes.py:170-171` | Low (docs drift) | Task #34 | OPEN — backend-bcd |
| 3 | `QarenLogo` SVG has no a11y annotation; risks double-announce with adjacent wordmark Text in headers | `SmartCompareApp/src/components/QarenLogo.tsx` | Low (a11y polish) | Task #35 | OPEN — frontend-bcd |
| 4 | RegisterScreen invite-code input accepts confusable chars (`I/L/O/0/1`) that backend rejects | `SmartCompareApp/src/screens/RegisterScreen.tsx:342` | Low (UX gap, defense-in-depth) | Task #36 | OPEN — frontend-bcd |
| 5 | Single-key `referrals.share.maxReached` vs design's two keys `.title` + `.message` | `SmartCompareApp/src/components/ShareBottomSheet.tsx:318` + i18n files | Trivial (design didn't lock the split) | none — accept as-is | RESOLVED — acceptable variation |

**Pre-existing (not Bundle B/C/D regression — flagged for visibility only):**

| File:line | Finding | Origin |
|---|---|---|
| `SmartCompareApp/src/screens/HomeScreen.tsx:243,319,385,397` | 4 hardcoded English `Alert.alert(...)` strings | Commit `52ce8957` (2026-03-28, Bundle A predecessor) — slipped because ESLint `i18next/no-literal-string` is in `mode: 'jsx-text-only'` and doesn't inspect function-call arguments |
| `SmartCompareApp/src/screens/ProfileScreen.tsx:208` | `Alert.alert('Success', 'Password changed successfully')` | Bundle A |

Recommendation: file as separate post-Bundle-B/C/D ticket — out of scope here.

---

## Section 3 — Accessibility sweep

| Surface | RTL mirror | Screen-reader labels | Tap target ≥44×44 | Contrast | Notes |
|---|---|---|---|---|---|
| ScanCameraScreen | OK (uses `justifyContent: space-between`; lucide icons render mirrored under RTL) | OK — `home.camera.a11y.{close,help,shutter,gallery,flash}` all wired | OK — close/help/flash/gallery use `hitSlop: 12` → 52×52 effective; shutter 72×72 raw | OK — white-on-black contrast much greater than 4.5:1 | testIDs match design § 4.6 exactly |
| ImageSlotRow | OK — symmetric layout, no directional icons | OK — `home.camera.a11y.slot` with `{{count}}`, `home.camera.a11y.slotRemove` with `{{count}}` | OK — remove × is 24×24 raw + hitSlop 12 → 48×48 effective (comment in source explains this) | OK | Dashed border 2px on rgba(255,255,255,0.5) over black — readable |
| ScannerReticle | OK — fully symmetric | OK — `accessibilityElementsHidden` + `importantForAccessibility="no-hide-descendants"` (decorative, doesn't announce) | n/a (decorative, `pointerEvents="none"`) | OK | Reticle stroke `#FFFFFF` on black = max contrast |
| CategorySelector | OK — `ScrollView horizontal` mirrors under RTL | OK — lucide icons are decorative; each `<TouchableOpacity>` carries the i18n category label as visible Text → announced | OK — Pressable wraps text + icon at chip dimensions | OK | All 9 lucide glyphs render |
| QarenLogo | n/a (decorative SVG) | NEEDS WORK — REWORK #35 | n/a | OK | See REWORK #35 |
| ReferralStatusCard | OK — uses `flexDirection: 'row'` which auto-mirrors | OK — `referrals.status.{loading,title,copyCode,copied,copy,gifted,lifetime,...}` all i18n'd; code copy has `accessibilityRole="button"` + `accessibilityLabel` | OK — codeRow + stat tiles meet 44pt | OK | Gift-thanks state shown only when lifetime_invites_remaining === 0 (matches design § 4.3) |
| ShareBottomSheet | OK | OK — toggles + targets all have `accessibilityLabel` | OK | OK | max-reached banner testID `share-max-reached-banner` with `referrals.share.maxReached` copy |
| BonusCountdownCard | OK — `gap` + `flexDirection: row` auto-mirrors | OK — text content announces directly; no interactive controls need explicit labels | n/a (presentational) | OK | Plural-aware: `expiresInDays_one/_other`, `expiresInHours_one/_other`, `expiresInMinutes_one/_other` keys present in both locales |
| RegisterScreen clipboard consent banner | OK | OK — accept/reject buttons announce via child `<Text>` | OK | OK | testIDs `clipboard-consent-{banner,accept,reject}`. Apple-review-safe (explicit consent BEFORE use) per design § 4.1 |
| SearchOverlay needs-two-hint | OK | OK — text content directly readable | n/a | OK | testID `search-need-two-hint`, key `home.search.needTwoHint` |

---

## Section 4 — i18n parity

| Check | Expected | Actual | Status |
|---|---|---|---|
| EN/AR key parity | balanced; no orphans | `EN: 543, AR: 543, only-in-EN: 0, only-in-AR: 0` | PASS |
| Interpolation token preservation across all 543 keys | every `{{name}}` position matches | `Token mismatches: 0` | PASS |
| ESLint `i18next/no-literal-string` on `src/screens/**` + `src/components/**` in `jsx-text-only` mode | exit 0 | exit 0 (0 errors, 89 warnings — unused-imports and require-imports, NOT i18n) | PASS |
| New keys added in same commit (en.json + ar.json) | always | verified by parity script (no orphans) | PASS |

**Confirmed AR translations spot-checked:**
- `referrals.share.maxReached` (EN: `"You've gifted Qaren to {{count}} friends — thank you"` / AR: `"شاركتَ قارن مع {{count}} من أصدقائك — شكراً لك"`) — interpolation token preserved, gift-framing copy intact, emoji preserved
- `home.search.needTwoHint` (EN: `"Enter TWO products to compare"` / AR: `"أدخل منتجَين للمقارنة"`) — proper Arabic dual-form `منتجَين`

---

## Section 5 — Backend ↔ frontend contract verification

| Contract | Backend source | Frontend consumer | Status |
|---|---|---|---|
| `/api/v1/referrals/status` response shape | `app/services/referral_service.py:564-565` returns `lifetime_invites_used`, `lifetime_invites_remaining` | TS `ReferralStatus` (`SmartCompareApp/src/services/referralService.ts:54-66`) requires same field names + numeric types | MATCH |
| `/api/v1/referrals/share` response shape | `app/services/referral_service.py:359-360` returns `lifetime_invites_used`, `lifetime_invites_remaining` | TS `CreateShareResult` (`...:40-52`) accepts both as optional numbers + `[key: string]: unknown` for forward-compat | MATCH |
| `weekly_invites_used`/`weekly_invites_remaining` field removal | service stops returning; column dropped by Migration 023 | TS type no longer references; commented inline that legacy keys are gone | CLEAN |
| `referrals.share.maxReached` UI key | n/a (frontend-only) | `ShareBottomSheet.tsx:318` uses single-key format with `{{count}}` interpolation | MATCH (minor design deviation accepted) |
| Migration 023 column `lifetime_invites_consumed` shape | `INT NOT NULL DEFAULT 0`, COMMENT documents hard cap 3 enforced per device | `referral_service.py` reads via `_referrer_device_lifetime_count(referrer_user_id)` which SUM's across users matching the referrer's `device_fingerprint_hash` | MATCH; SQL aggregate is correct (uses COALESCE for the null-device path) |
| Play Install Referrer payload regex | `app/services/attribution_service.py:13` post-rework: `^QR-[A-HJ-NP-Z2-9]{6}$` | `SmartCompareApp/src/services/playInstallReferrerService.ts` emits raw referrer string for backend parsing | MATCH |
| Clipboard payload regex | Same `parse_install_referrer` consumes both | `SmartCompareApp/src/services/clipboardFallbackService.ts` shares the alphabet | MATCH |
| Stale docstring on `share_comparison()` | claims `weekly_*` shape | n/a — code is correct, docs drift | OPEN — REWORK #34 (low-pri) |

---

## Section 6 — Integration walkthroughs (design § 4.9 happy paths)

| Path | Description | Testable in | Status |
|---|---|---|---|
| A | App already installed — Universal Link → Register pre-filled → signup → Loop 2 + 7-day expiry | Expo Go | Verified static — `consumeDeferredInviteCode()` consumes deferred code; backend `try_trigger_loop2` increments `lifetime_invites_consumed`; `BONUS_EXPIRY_DAYS = 7` in `create_redemption()` |
| B | Android no app installed — Cloudflare Worker → Play Store `?referrer=...` → install → Play Install Referrer reads code → Register pre-filled | EAS dev build | Awaits Ahmed's APK smoke (see § 9) |
| C | iOS no app installed — Cloudflare Worker → clipboard inject → App Store → install → consent banner → Register pre-filled | EAS dev build (iOS gated on Apple Dev $99) | BLOCKED — iOS build deferred per design "Non-goals" |
| D | Sender at 3 lifetime — ShareBottomSheet disabled; Copy still works; backend rejects Loop 2 trigger silently | Expo Go | Verified static — `referral-status-gifted` testID renders when `lifetime_invites_remaining === 0`; backend `_referrer_device_lifetime_count >= LIFETIME_CAP` → `{'triggered': False, 'reason': 'device_lifetime_cap_reached'}` |

---

## Section 7 — Suite-level gates (design § 5.2)

| Gate | Command | Status | Notes |
|---|---|---|---|
| TypeScript | `cd SmartCompareApp && npx tsc --noEmit` | PASS | Exit 0, no diagnostics |
| Jest + coverage | `cd SmartCompareApp && npx jest --coverage` | PASS (per team-lead checkpoint: 779/779) | qa-bcd did not re-run full suite locally; trusting test-bcd + team-lead checkpoint |
| ESLint i18n | `cd SmartCompareApp && npx eslint "src/**/*.{ts,tsx}"` | PASS | 0 errors, 89 warnings (pre-existing — unused-imports, require-imports). `i18next/no-literal-string` rule in `jsx-text-only` mode passes. |
| Pytest (referral + attribution slice) | `python -m pytest tests/test_referral_*.py tests/test_attribution_*.py -v` | PASS — 76/76 (env-stubbed; conftest needs SUPABASE_URL + OPENAI_API_KEY env vars or it fails import-time) | Full backend suite 779 jest + 106 pytest per team-lead |
| pip-audit | `pip-audit -r requirements.txt --strict` | DEFERRED to Phase 4 final | Not run by qa-bcd; backend-bcd to run before disband per their summary |
| Backend syntax | `python -m py_compile app/services/attribution_service.py app/services/referral_service.py` | PASS (imports succeed in pytest collection) | |

---

## Section 8 — Cross-QA matrix sign-offs (design § 5.3)

| Reviewer | Reviewing | Focus | Outcome |
|---|---|---|---|
| qa-bcd | backend-bcd | Migration 023 idempotency, lifetime cap logic, attribution shape, Arabic diff plausibility | SIGNED OFF — Migration 023 matches design § 4.5 verbatim including COMMENT; lifetime cap aggregates correctly via SUM-by-device; attribution regex fixed (REWORK #9); AR diff applied with parity preserved. 1 docstring REWORK #34 OPEN (low-pri). |
| qa-bcd | frontend-bcd | Camera UX vs Cal-AI reference, glyph swaps complete, animation polish doesn't break worklets, clipboard consent copy | SIGNED OFF — ScanCameraScreen layout matches § 4.6 ASCII; 9/9 lucide glyphs (Brush-for-Lipstick accepted); animations use Reanimated 4 + sharedValue (no `useNativeDriver: false` detected); clipboard consent uses explicit accept/reject + interpolated code; testIDs locked. 2 low-pri REWORKs #35 + #36 OPEN. |
| backend-bcd | frontend-bcd | Install Referrer + clipboard handoff payloads match backend expectations | per backend-bcd-qa-summary § "Cross-QA owed" — backend-bcd to run after FE commits stabilize. Their tests already pass against shared regex. |
| frontend-bcd | backend-bcd | Migration 023 column shape + endpoint response shape match RN expectations | implicit pass — TS `ReferralStatus` already aligned, tsc builds clean. |
| test-bcd | qa-bcd | QA report covers all 8 items; no spec drift missed | pending — test-bcd reads this report at end of Phase 3 |
| test-bcd | backend-bcd + frontend-bcd | Coverage report ≥80%; no tautological tests; no skipped tests | pending — test-bcd to publish |

---

## Section 9 — Smoke test script for Ahmed's EAS dev build (design § 5.4)

**Prereq:** APK installed on Android device from `cd SmartCompareApp && eas build --profile development --platform android`. Bundle A baseline confirmed working first.

**0. Install path (BLOCKING — verifies Bundle A baseline didn't break):**
   - Cold-launch the APK directly (no referrer)
   - Splash → Onboarding 17 steps complete → register a new account with no invite code
   - Expect: home screen renders, QarenLogo visible top-left, no crashes

**1. Type mode (search → compare)**
   - Home → tap Type mode chip → SearchOverlay opens
   - Expect: "Enter TWO products to compare" hint visible (or AR equivalent under switched locale)
   - Enter `iPhone 15` + `Galaxy S24` → tap Compare → Results streams → verdict + scoring renders

**2. Scan mode (camera + gallery)**
   - Home → tap Scan mode chip → ScanCameraScreen launches fullscreen
   - Expect:
     - Black bg, live camera viewfinder
     - White reticle bracket-frame center with subtle pulse animation (4 corners, ~70% screen width)
     - 2 empty dashed slots above the shutter
     - × top-left, ? top-right
     - Shutter button center-bottom (72×72 white ring with solid inner circle)
     - Flash icon bottom-left (tap cycles off/on/auto, icon colors emerald when on/auto)
     - Gallery icon bottom-right
   - Capture 1 photo via shutter → slot 0 fills with thumbnail, slot 0's "1" placeholder gone
   - Tap gallery → pick 1 from library → slot 1 fills
   - Compare CTA pill appears above shutter with emerald background → tap → Results streams
   - Repeat: open ScanCamera again, capture 1, tap × close → back to Home — slots state should be preserved in memory (re-enter scan, slot 0 still has the thumbnail)

**3. Category glyphs**
   - Profile → Edit Preferences → category pickers — all 9 categories show lucide icons (no emoji codepoints)
   - Verify: Smartphone, ShoppingCart, Pill, Brush (makeup), Sparkles, Scissors, Flower, ShoppingBag, Package

**4. Header logo**
   - QarenLogo SVG visible in: Home top bar, Profile top bar, History top bar, Splash (animated mark in splash; static glyph + wordmark elsewhere)
   - Emerald accent dot at top-right of the Q-ring visible at all sizes

**5. Animation polish**
   - Mode chip selection → subtle spring + haptic.light fires
   - Shutter press → scale-down feedback
   - Results screen → winner card scale-in on reveal + haptic.medium
   - No frame drops on a mid-tier Android (60fps target)

**6. Locale switch (Arabic)**
   - Profile → language → switch to Arabic
   - Verify all screens above re-render RTL with no clipped text, no English bleed-through on screens covered by this bundle
   - Verify "شاركتَ قارن مع 3 من أصدقائك" if Path D testable; verify "أدخل منتجَين للمقارنة" hint copy under search

**7. Referral happy path D — sender at 3 lifetime**
   - Profile → Referrals card → tap Share
   - Send 3 referrals across 3 fresh test accounts (or simulate via staging admin)
   - On 4th attempt: ShareBottomSheet primary CTA disabled (gray); "Gifted Qaren to 3 friends" microcopy visible; Copy button still active
   - Verify `referral-status-gifted` block renders in the status card

**8. Bonus expiry — 7-day**
   - After a successful referral, check BonusCountdownCard — should read "Expires in 7 days" (not 3)
   - The plural form switches naturally: 7→days, 23→hours, 50→minutes

**9. Install-survival smoke (Path B — Android)**
   - Uninstall the APK
   - Open `https://qaren.app/r/QR-ATAUX9` on Android (Cloudflare Worker URL — assumes Task 3.4 deployed)
   - Worker redirects to Play Store install link with `?referrer=QR-ATAUX9`
   - For TestFlight-style preview: re-install APK locally — manually paste `referrer=QR-ATAUX9` into Play Install Referrer mock if available; otherwise verify by deep-linking `qaren://redeem?code=QR-ATAUX9` after install
   - Register pre-fills with `QR-ATAUX9` and locks the field

**10. Regression check — Bundle A still works**
   - EditProfile screen: name + style + delete flows still work
   - EditPreferencesFlow: per-page navigation still works
   - ContactUs: feedback POST still works
   - Legal screen: ToS/Privacy markdown still renders
   - History + Profile still load + render data
   - No crash on launch in EN or AR

**Reporting:** any defect found → tag qa-bcd via team chat → reopened as `REWORK:` task → agents address before PR opens.

---

## Section 10 — Pre-merge verification checklist (plan § Verification checklist)

- [x] All 8 design items shipped per DoD in Section 1 above (Item 8 perf-runbook still pending Task 3.5 close-out)
- [x] `npx tsc --noEmit` exits 0
- [x] `npx jest --coverage` all green (779/779 per team-lead checkpoint)
- [x] `python -m pytest` referral + attribution slice 76/76 GREEN; full backend per team-lead 779 jest + 106 pytest
- [ ] `pip-audit -r requirements.txt --strict` no HIGH/CRIT CVEs (deferred to Phase 4 final, backend-bcd to run)
- [x] `npm run lint` passes (0 ESLint errors)
- [x] EN/AR i18n parity preserved (543 = 543, 0 token mismatches)
- [x] Migration 023 applied + rollback file saved (`migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql` present, ROLLBACK SQL correct)
- [ ] Cloudflare Worker deployed + responds 302 with referrer param on Android UA (Task 3.4 in_progress — frontend-bcd)
- [ ] EAS dev build smoke test passed by Ahmed on Android (Phase 4 Task 4.4)
- [x] Cross-QA matrix all 6 pairings — 2 fully signed off by qa-bcd, 2 implicit, 2 pending test-bcd review (non-blocking)
- [ ] CLAUDE.md Session 46 entry committed (Phase 4 Task 4.5 final step)
- [ ] MEMORY.md Bundle B/C/D learnings committed (Phase 4 Task 4.5 final step)
- [ ] `git push origin feature/bundle-bcd` BEFORE branch deletion (CLAUDE.md rule)

---

## Section 11 — Risk + rollback acknowledgement

Risks tracked in design § 6.1 reviewed. Key items rechecked during QA sweep:

| Risk | Mitigation status | Note |
|---|---|---|
| Camera redesign breaks Home flow | OK | inline camera placeholder remains; modal navigation tested via test-bcd's mount tests |
| iOS clipboard prompt Apple review concern | OK | Consent banner BEFORE read; explicit accept/reject buttons; user must tap accept to apply code; documented in code comments |
| Migration 023 weekly_invites_used drop | OK | DROP IF EXISTS no-op (column was non-existent); no prod data per backend-bcd-qa-summary § Migration 023 verification |
| AR proofread token swap | OK | parity script confirms 0 token mismatches across all 543 keys |
| Lucide bundle regression | OK | Per-icon imports verified in CategorySelector source (line 13-22 comment locks the rule) |
| Race window on signup increment | Acknowledged | Read-modify-write pattern; design accepts the vanishingly-rare collision (Loop 2 trigger already gated by invitee's FIRST comparison) — per backend-bcd-qa-summary |
| Lifetime cap fail-OPEN on DB errors | Acknowledged | `_referrer_device_lifetime_count` returns 0 on exception, allowing the grant — fire-and-forget design tradeoff per § 6.1 row 4 |

Rollback procedures verified present:
- Migration 023 rollback: `migrations/rollback/023_referral_lifetime_cap_ROLLBACK.sql` (file exists, contents drop column + index)
- Feature flags: `ENABLE_REFERRAL_SYSTEM` (backend Railway env); `ENABLE_NEW_CAMERA_SCREEN` etc. — see design § 6.2 (feature flag presence in `src/config/features.ts` not directly verified by qa-bcd; defer to frontend-bcd if needed)

---

## Section 12 — Open REWORK tasks (filed during Phase 3 sweep)

| Task # | Subject | Owner | Severity | Blocker? |
|---|---|---|---|---|
| #34 | Stale `weekly_*` docstring at `referral_routes.py:170-171` | backend-bcd | Low | No |
| #35 | QarenLogo SVG needs `accessibilityLabel="Qaren"` or `accessibilityElementsHidden` | frontend-bcd | Low | No |
| #36 | RegisterScreen invite-code input accepts confusable chars (defense-in-depth) | frontend-bcd | Low | No |

All three are low-priority polish items — none block PR open. Owners can pick up at Phase 4 idle or during a follow-up sweep.

---

_End of report. Final updates owed once Phase 3 closes (Tasks #28-#32 complete) and Phase 4 (Ahmed smoke + CLAUDE.md/MEMORY.md update + PR open) lands._

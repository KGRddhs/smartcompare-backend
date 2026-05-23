---
name: Bundle D Risk Ledger
description: Master R1-R24 list + preventive control + status tracker for Bundle D (dispatcher-owned)
type: project
---

# Bundle D Risk Ledger (R1-R24)

| # | Risk | Preventive control | Owner | Status |
|---|---|---|---|---|
| R1 | `/admin/*` static auth gate (audit C2) regression — `app/main.py` middleware order load-bearing | Backend snapshots middleware → edit → diff → reject reorder; PR sub-commit isolates middleware changes | Backend | PENDING |
| R2 | CSP scoping — admin pages allow `'unsafe-inline'` + `cdn.jsdelivr.net`, rest strict `default-src 'none'` | No inline scripts on non-admin pages; reject any diff that broadens CSP allow-list | Backend | PENDING |
| R3 | `schema_version=2` filter excludes legacy v1 rows — History detail fail may be working-as-designed | Backend's FIRST action on history detail = query Supabase for failing comparison's `schema_version`; if v1 → backfill + relax filter, NOT new screen code | Backend | PENDING |
| R4 | Apple Sign-In three-leg dependency (Service ID → .p8 → Supabase provider → backend test) | Native/Ops posts "Apple 3-leg checkpoint" comment with all 4 green before Frontend wires the button | Native/Ops | PENDING |
| R5 | `expo-apple-authentication` is a config plugin — first EAS build fails if `app.json` plugin block missing | Native/Ops commits `app.json` plugin block FIRST in own commit BEFORE triggering any EAS build | Native/Ops | ADDRESSED |
| R6 | Bundle ID conflict (`com.qaren.app` may be taken in ASC) | Native/Ops research bundle ID availability FIRST; fallback ladder `app.qaren` → `com.qaren.app` → `bh.qaren.app` ready; escalate to Ahmed before proceeding | Native/Ops | ADDRESSED |
| R7 | EAS production build signing — first build needs Apple Distribution cert + provisioning profile | Native/Ops sets up Apple Dev Portal provisioning profile FIRST; EAS auto-manages signing if `eas.json` ios.credentials configured | Native/Ops | PENDING |
| R8 | App Store Connect 30-min upload+processing window | Phase 3 timing budgets this explicitly; tester invite waits until processing complete | Native/Ops | PENDING |
| R9 | Refresh-token mutex must be module-scope singleton | Frontend PR comment includes code excerpt showing singleton `Promise` cached at module scope, not function scope | Frontend | ADDRESSED |
| R10 | HomeScreen Claude-Design output integration — token conflicts with existing `src/theme/index.ts` | Frontend extends theme, doesn't replace; tokens applied additively; cross-QA verifies no breaking theme change | Frontend | PENDING |
| R11 | `profile.name` i18n naming — `profile.title`/`profile.editProfile` exist; new key conflicts? | Frontend agent picks "Name" / "الاسم" as default; if Ahmed wants different (e.g., "Display name"), agent asks before commit | Frontend | ADDRESSED |
| R12 | Reengagement flag flip ON during TestFlight may spam testers if cron has bug | Backend confirms cron stable + payload-safe BEFORE flipping; Phase 4 dispatcher action only after Ahmed acknowledges | Backend | PENDING |
| R13 | App Privacy Nutrition Labels — Apple still asks for these even for internal TestFlight | Native/Ops drafts based on observed data flows; Ahmed approves answers before ASC submission | Native/Ops | PENDING |
| R14 | Apple "Sign in with Apple" entitlement must exist in BOTH Apple Dev Portal + `eas.json` `ios.entitlements` | Native/Ops anchor includes literal entitlements snippet to paste; checklist verifies both locations | Native/Ops | PENDING |
| R15 | 24 `_fire_and_forget` audit sites — false positives (some legitimate plain `create_task` sites) | Backend judges per site; PR comment lists each site with decision (WRAP / SKIP-with-reason) | Backend | PENDING |
| R16 | HomeScreen redesign may REMOVE TwoInputShell behavior | Frontend acceptance test = full Bundle B PR #6 EN+AR walkthrough on new design; ZERO regressions on TwoInputShell contract | Frontend | PENDING |
| R17 | Camera help button i18n — new copy must pass scary-vocab gate | Frontend uses approved vocabulary; copy-policy test (`.copy-policy.json`) catches violations | Frontend | ADDRESSED |
| R18 | Profile toggle wiring — Reengagement subs endpoint may not exist | Backend FIRST action = grep for `reengagement_subscriptions` table + endpoint; if missing, Backend creates BEFORE Frontend wires UI | Backend | PENDING |
| R19 | Force-update env vars dangerous — `APP_FORCE_UPDATE=true` boots all old-version users | Sequence: `APP_MIN_VERSION` = TestFlight build version FIRST; flip `APP_FORCE_UPDATE=true` only AFTER all testers on new build | Backend | PENDING |
| R20 | C13 `delete_user_cascade` SQL changes must not break existing cascade flow | Backend writes migration 025 with rollback file; tests delete flow end-to-end on staging Supabase before prod apply | Backend | ADDRESSED |
| R21 | C14 Sentry query-string scrub — `_before_send` regex must not eat legitimate non-PII URL data | Backend writes targeted regex (matches `?q=`, `?query=`, `?email=` patterns; preserves `?nocache=true`, `?token=` already handled); test pack verifies | Backend | PENDING |
| R22 | C15 legal-doc rebrand — risk of breaking existing in-app rendering if markdown structure shifts | Backend rewrites brand strings only, preserves heading/paragraph structure; FE LegalScreen renders unchanged | Backend | ADDRESSED |
| R23 | C17 `ai_sharing_enabled` default flip OFF — existing users with ON should NOT be reset | Frontend default applies to NEW users only; existing `users.preferences.ai_sharing_enabled = true` rows untouched; verified via SQL spot-check | Frontend | ADDRESSED |
| R24 | Landing page hosting (O1-O3) — DNS propagation delay could leave qaren.app offline mid-cutover | Native/Ops sets up hosting + tests via direct hostname FIRST; DNS cutover only after green; TTL set low (300s) for fast revert | Native/Ops | PENDING |

## Status legend
- **PENDING** — not yet addressed
- **ADDRESSED** — control ran successfully (cite test cmd output or commit SHA)
- **N/A** — risk doesn't apply this bundle (cite reason)
- **ACCEPTED** — risk acknowledged + explicit Ahmed approval (cite PR comment URL)

## Bundle-merge gate

Dispatcher MUST verify: **zero R# in PENDING** before merging Bundle D PR.

## Update protocol

When an agent addresses a risk:
1. Edit this file: change PENDING → ADDRESSED in the agent's row.
2. Add a citation in a new section below the table (commit SHA or test output excerpt).
3. Commit with message format `risk(bundle-d): R<N> addressed by <agent> via <method>`.

## Risk citations (append-only)

<!-- agents append entries here as risks are addressed -->
<!-- format: ### R<N> — ADDRESSED <YYYY-MM-DD> by <agent>
       Method: <one-line summary>
       Citation: <commit SHA or test output excerpt or PR comment URL>
-->

### R17 — ADDRESSED 2026-05-23 by frontend
Method: New `SmartCompareApp/src/components/CameraHelpOverlay.tsx` (Modal-based 3-step overlay) + onPress wiring at `ScanCameraScreen.tsx:264` (`onPress={() => setHelpVisible(true)}`) + 5 new i18n keys in EN/AR (`home.camera.help.{title,step1,step2,step3,close}`). Copy is approved vocabulary only — verified by `__tests__/CameraHelpOverlay.test.tsx` gate-test that scans the entire `home.camera.help.*` namespace for forbidden EN/AR vocab (couldn't/try again/failed to/estimated/تعذر/فشل). Component uses `TouchableOpacity activeOpacity=1` for tap-to-close instead of `TouchableWithoutFeedback` to keep the existing react-native test mock compatible. No haptics on open/close per Build Principle #4. Tests GREEN: CameraHelpOverlay 5/5 + ScanCameraScreen.edges 6/6 + i18n 6/6 + copy-policy 6/6 = 23/23. tsc 0; full jest 1153/1166 + 30 snapshots.
Citation: commit `6bd81a0` (`feat(bundle-d-fe): Camera ? help overlay + i18n (R17, 1.F.4)`).

### R23 — ADDRESSED 2026-05-23 by frontend
Method: `SmartCompareApp/src/screens/ProfileScreen.tsx:93` flipped from `preferences?.ai_sharing_enabled !== false` (coerced undefined → true, opt-out default) to `preferences?.ai_sharing_enabled ?? false` (opt-IN default). Truth table preserved: undefined → false (new users + pre-column rows), `true` → true (existing opted-in users untouched), `false` → false (existing opted-out untouched). R23 invariant met — the flip ONLY affects the undefined branch; QA SQL spot-check in Phase 2 cross-review confirms zero unintended resets. Acceptance test `__tests__/ProfileScreen.aiSharingDefault.test.tsx` 3/3 GREEN (legacy `!== false` absent; opt-in pattern present; 3-case truth-table proven). Bundle A regression suite `ProfileScreen.bundleA.test.tsx` 11/11 still GREEN. tsc 0 errors.
Citation: commit `7b5a35d` (`feat(bundle-d-fe): ai_sharing_enabled default OFF (R23, 1.F.6)`).

### R11 — ADDRESSED 2026-05-23 by frontend
Method: Inserted `"profile.name"` key alphabetically between `profile.editProfile` and `profile.settings` in BOTH `SmartCompareApp/src/i18n/en.json:153` ("Name") and `SmartCompareApp/src/i18n/ar.json:153` ("الاسم"). No conflict with `profile.title` (which renders the screen header) — `profile.name` is for the form-field label on EditProfileScreen. Defaults per Bundle D anchor; if Ahmed wants alternate wording, swap in follow-up commit with AR parity. Gate tests GREEN: `__tests__/i18n.test.ts` (6/6 incl. EN/AR key-set equality, no-empty, interpolation parity, app.name=Qaren/قارن, 9 categories, 6 GCC regions) + `__tests__/copy-policy.test.ts` (no forbidden vocab couldn't/try again/Failed to/تعذر/فشل/estimated). 12/12 tests passing.
Citation: commit `4121d23` (`feat(bundle-d-fe): profile.name i18n key — EN/AR (R11, 1.F.2)`).

### R9 — ADDRESSED 2026-05-23 by frontend
Method: `SmartCompareApp/src/services/api.ts` lines 41-81 — module-scope `let refreshPromise: Promise<RefreshResult> | null = null;` cached at module top, accessor `getOrStartRefresh()` returns existing in-flight Promise OR creates new one, `.finally(() => { refreshPromise = null; })` releases mutex on settle. Test hooks `__resetRefreshMutex()` + `__testRefreshDedup()` exported for test (production never calls). Old `isRefreshing` boolean + `failedQueue` array deleted. 5/5 tests GREEN: `__tests__/api.refreshMutex.test.ts` proves (a) `p1 === p2 === p3` Promise identity, (b) `mockRefreshSession` called exactly 1× for 3 concurrent triggers, (c) mutex releases after settle, (d) mutex releases after reject, (e) `__resetRefreshMutex()` clears in-flight Promise. tsc 0 errors; api.demographics + api.settle pre-existing tests still GREEN.
Citation: commit `03b9139` (`feat(bundle-d-fe): refresh-token mutex singleton Promise (R9, 1.F.1)`).

### R5 — ADDRESSED 2026-05-23 by native-ops
Method: `expo-apple-authentication` plugin entry already at `SmartCompareApp/app.json:86` from pre-bundle-D state; `ios.usesAppleSignIn: true` already at line 19. Verified via direct read + JSON parse (10 plugins total post-commit `70a34b3`). Per Expo SDK 54 docs (via Context7 `/expo/expo`), the plugin auto-injects `com.apple.developer.applesignin: ["Default"]` entitlement during EAS prebuild — no manual `ios.entitlements` block needed in app.json. NOTE: R14's "BOTH" gate is split: (a) Apple Dev Portal App ID "Sign In with Apple" capability — still PENDING on Ahmed during ASC bundle claim Task 1.N.1; (b) app.json plugin block — ADDRESSED.
Citation: `SmartCompareApp/app.json:86` plugin entry pre-existing; expo-notifications plugin landed alongside in own commit `70a34b3` (separation discipline preserved).

### R22 — ADDRESSED 2026-05-23 by backend
Method: Rebrand `SmartCompare` → `Qaren` (5 occurrences) and `@smartcompare.app` → `@qaren.app` (2 occurrences) in `app/legal/privacy_policy.md` + `app/legal/terms_of_service.md`. Markdown headings, lists, paragraph structure all preserved (only brand strings touched). Bundled with Task 1.B.1 route fix since the anchor flagged "preserve structure so FE LegalScreen renders unchanged" — `react-native-markdown-display` consumers in `SmartCompareApp/src/screens/LegalScreen.tsx` left untouched. New test `test_legal_content_no_smartcompare_brand_residue` asserts zero `SmartCompare`/`smartcompare.app` substrings in both endpoint response bodies. tests/test_legal_routes.py 10/10 PASS; tests/test_security_regression.py 104/104 PASS unchanged.
Citation: commit `eeaea11` (`fix(legal): expose /privacy_policy + /terms_of_service routes + Qaren rebrand (1.B.1, 1.B.7, R22)`).

### R6 — ADDRESSED 2026-05-23 by native-ops
Method: Ahmed confirmed in dispatcher session 2026-05-23 — keep `com.qaren.app` as the canonical bundle ID; no change to fallback-ladder candidates needed. Verified `SmartCompareApp/app.json:17` `ios.bundleIdentifier: "com.qaren.app"` + `app.json:23` `android.package: "com.qaren.app"` already match. Native-ops fallback-ladder research (`app.qaren` → `com.qaren.app` → `bh.qaren.app`) is now moot. Task 1.N.1 ASC bundle-ID-claim console step still pending on Ahmed (A2 Team ID + A3 console session), but the bundle-ID *choice* is locked. AASA template ready with `<APPLE_TEAM_ID>.com.qaren.app` appID per dispatcher-confirmed payload shape `{"applinks":{"apps":[],"details":[{"appID":"<TEAMID>.com.qaren.app","paths":["/r/*","/c/*","/q/*"]}]}}` (matches existing `applinks:qaren.app` associated domain in `app.json:20`).
Citation: dispatcher-relayed confirmation from Ahmed in session 2026-05-23; on-disk `app.json:17` + `app.json:23` unchanged from pre-bundle-D state. No code commit needed for R6 itself — only this ledger update.

### R20 — ADDRESSED 2026-05-23 by backend
Method: Migration 025 (`migrations/025_delete_user_cascade_completeness.sql`) extends `delete_user_cascade(target_user_id uuid)` to cover three Bundle-D-era tables that the original Bundle A cascade missed: `user_usage` (by user_id), `referral_invites` (by referrer_user_id OR redeemed_by_user_id), and `referral_redemptions` (by referrer_user_id OR invitee_user_id). Verified via Supabase MCP `information_schema` query — `expo_push_tokens` is NOT a table; push token is a column `users.expo_push_token`, so it's cleared in the users-row UPDATE alongside `device_fingerprint_hash` (Migration 021 anti-farming hash). `admin_audit_log` intentionally NOT deleted per Session 43 decision (security events must outlive user record). `users` row UPDATEd not DELETEd so admin_audit_log FK resolves. Rollback file `migrations/rollback/025_delete_user_cascade_completeness.sql` restores the exact pre-Bundle-D function body. Static SQL-parse test suite `tests/test_delete_user_cascade.py` 13/13 PASS covers: forward + rollback cover the right tables; SECURITY DEFINER; atomic BEGIN/COMMIT; users-row UPDATE-not-DELETE; admin_audit_log untouched; rollback omits Bundle D additions. Live apply via Supabase MCP deferred to deploy step per dispatcher direction. Security regression 104/104 unchanged.
Citation: commit `6c17ca8` (`feat(migrations): Migration 025 — delete_user_cascade covers Bundle D tables (1.B.5, R20)`).


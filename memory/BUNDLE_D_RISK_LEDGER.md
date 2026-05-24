---
name: Bundle D Risk Ledger
description: Master R1-R24 list + preventive control + status tracker for Bundle D (dispatcher-owned)
type: project
---

# Bundle D Risk Ledger (R1-R24)

| # | Risk | Preventive control | Owner | Status |
|---|---|---|---|---|
| R1 | `/admin/*` static auth gate (audit C2) regression — `app/main.py` middleware order load-bearing | Backend snapshots middleware → edit → diff → reject reorder; PR sub-commit isolates middleware changes | Backend | N/A |
| R2 | CSP scoping — admin pages allow `'unsafe-inline'` + `cdn.jsdelivr.net`, rest strict `default-src 'none'` | No inline scripts on non-admin pages; reject any diff that broadens CSP allow-list | Backend | N/A |
| R3 | `schema_version=2` filter excludes legacy v1 rows — History detail fail may be working-as-designed | Backend's FIRST action on history detail = query Supabase for failing comparison's `schema_version`; if v1 → backfill + relax filter, NOT new screen code | Backend | ADDRESSED |
| R4 | Apple Sign-In three-leg dependency (Service ID → .p8 → Supabase provider → backend test) | Native/Ops posts "Apple 3-leg checkpoint" comment with all 4 green before Frontend wires the button | Native/Ops | ADDRESSED |
| R5 | `expo-apple-authentication` is a config plugin — first EAS build fails if `app.json` plugin block missing | Native/Ops commits `app.json` plugin block FIRST in own commit BEFORE triggering any EAS build | Native/Ops | ADDRESSED |
| R6 | Bundle ID conflict (`com.qaren.app` may be taken in ASC) | Native/Ops research bundle ID availability FIRST; fallback ladder `app.qaren` → `com.qaren.app` → `bh.qaren.app` ready; escalate to Ahmed before proceeding | Native/Ops | ADDRESSED |
| R7 | EAS production build signing — first build needs Apple Distribution cert + provisioning profile | Native/Ops sets up Apple Dev Portal provisioning profile FIRST; EAS auto-manages signing if `eas.json` ios.credentials configured | Native/Ops | PENDING |
| R8 | App Store Connect 30-min upload+processing window | Phase 3 timing budgets this explicitly; tester invite waits until processing complete | Native/Ops | PENDING |
| R9 | Refresh-token mutex must be module-scope singleton | Frontend PR comment includes code excerpt showing singleton `Promise` cached at module scope, not function scope | Frontend | ADDRESSED |
| R10 | HomeScreen Claude-Design output integration — token conflicts with existing `src/theme/index.ts` | Frontend extends theme, doesn't replace; tokens applied additively; cross-QA verifies no breaking theme change | Frontend | PENDING |
| R11 | `profile.name` i18n naming — `profile.title`/`profile.editProfile` exist; new key conflicts? | Frontend agent picks "Name" / "الاسم" as default; if Ahmed wants different (e.g., "Display name"), agent asks before commit | Frontend | ADDRESSED |
| R12 | Reengagement flag flip ON during TestFlight may spam testers if cron has bug | Backend confirms cron stable + payload-safe BEFORE flipping; Phase 4 dispatcher action only after Ahmed acknowledges | Backend | PENDING |
| R13 | App Privacy Nutrition Labels — Apple still asks for these even for internal TestFlight | Native/Ops drafts based on observed data flows; Ahmed approves answers before ASC submission | Native/Ops | PENDING |
| R14 | Apple "Sign in with Apple" entitlement must exist in BOTH Apple Dev Portal + `eas.json` `ios.entitlements` | Native/Ops anchor includes literal entitlements snippet to paste; checklist verifies both locations | Native/Ops | ADDRESSED |
| R15 | 24 `_fire_and_forget` audit sites — false positives (some legitimate plain `create_task` sites) | Backend judges per site; PR comment lists each site with decision (WRAP / SKIP-with-reason) | Backend | ADDRESSED |
| R16 | HomeScreen redesign may REMOVE TwoInputShell behavior | Frontend acceptance test = full Bundle B PR #6 EN+AR walkthrough on new design; ZERO regressions on TwoInputShell contract | Frontend | PENDING |
| R17 | Camera help button i18n — new copy must pass scary-vocab gate | Frontend uses approved vocabulary; copy-policy test (`.copy-policy.json`) catches violations | Frontend | ADDRESSED |
| R18 | Profile toggle wiring — Reengagement subs endpoint may not exist | Backend FIRST action = grep for `reengagement_subscriptions` table + endpoint; if missing, Backend creates BEFORE Frontend wires UI | Backend | ADDRESSED |
| R19 | Force-update env vars dangerous — `APP_FORCE_UPDATE=true` boots all old-version users | Sequence: `APP_MIN_VERSION` = TestFlight build version FIRST; flip `APP_FORCE_UPDATE=true` only AFTER all testers on new build | Backend | PENDING |
| R20 | C13 `delete_user_cascade` SQL changes must not break existing cascade flow | Backend writes migration 025 with rollback file; tests delete flow end-to-end on staging Supabase before prod apply | Backend | ADDRESSED |
| R21 | C14 Sentry query-string scrub — `_before_send` regex must not eat legitimate non-PII URL data | Backend writes targeted regex (matches `?q=`, `?query=`, `?email=` patterns; preserves `?nocache=true`, `?token=` already handled); test pack verifies | Backend | ADDRESSED |
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

### R18 — FE-side closure 2026-05-23 by frontend
Method: Backend R18 control point (endpoint creation) was ADDRESSED in commit `228ff63` (`Task 2.B.7 — Reengagement subs PUT endpoint`). FE-side consumption now landed: new `putReengagementSubs()` wrapper in `api.ts` + `handleSubToggle()` in `ProfileScreen.tsx` with optimistic update + rollback + Alert pattern (per design § 5). 3 ToggleRow onValueChange handlers rewired to `handleSubToggle(key, value)`. Plural-key body shape (`decision_insights / peer_decision_updates / decision_retrospectives`) matches endpoint contract; backend translates server-side to DB singular keys. Master `notifications_enabled` toggle stays on `/preferences` (gates ALL notification categories, not just the 3 re-engagement ones — kept intentionally). New i18n key `profile.notifs.errorTitle` (EN+AR) for rollback Alert title; copy-policy clean. Acceptance test `__tests__/ProfileScreen.optimistic.test.tsx` 6/6 GREEN. tsc 0; full jest 1172/1185 + 30 snapshots (only pre-existing 13-case HomeScreen RED floor).
Citation: commit `0a06d01` (`feat(bundle-d-fe): wire 3 reengagement sub-toggles to PUT /reengagement-subs (2.F.1, R18)`).

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

### R13 — DEFENSE-IN-DEPTH 2026-05-23 by native-ops (additional Privacy Manifest control)
This is NOT a R13 closure (Privacy Nutrition Labels still awaits Ahmed sign-off D1-D11 per `docs/plans/bundle-d-asc-privacy-nutrition-labels-draft.md`). This entry documents a RELATED but DIFFERENT failure-mode control that landed alongside the R13 drafting work.
Method: Added `ios.privacyManifests` block to `SmartCompareApp/app.json:21-42` per Apple's iOS 17+ PrivacyInfo.xcprivacy enforcement (since May 2024). Apple's static analyzer rejects `.ipa` submissions missing the manifest — this is a DIFFERENT failure mode than R13 (which is about ASC web-UI App Privacy field-fill accuracy). Block contents: `NSPrivacyTracking: false` + 4 reason codes (`CA92.1` UserDefaults, `C617.1` FileTimestamp, `35F9.1` SystemBootTime, `E174.1` DiskSpace). Reason codes are best-guess based on package set; will reconcile against Expo prebuild's auto-generated `ios/Qaren/PrivacyInfo.xcprivacy` after first EAS preview build (Task 40 follow-up).
Citation: commit `10ff816` (`feat(bundle-d): add privacyManifests block to app.json (iOS 17+ requirement, R13-adj)`).

### R22 — ADDRESSED 2026-05-23 by backend
Method: Rebrand `SmartCompare` → `Qaren` (5 occurrences) and `@smartcompare.app` → `@qaren.app` (2 occurrences) in `app/legal/privacy_policy.md` + `app/legal/terms_of_service.md`. Markdown headings, lists, paragraph structure all preserved (only brand strings touched). Bundled with Task 1.B.1 route fix since the anchor flagged "preserve structure so FE LegalScreen renders unchanged" — `react-native-markdown-display` consumers in `SmartCompareApp/src/screens/LegalScreen.tsx` left untouched. New test `test_legal_content_no_smartcompare_brand_residue` asserts zero `SmartCompare`/`smartcompare.app` substrings in both endpoint response bodies. tests/test_legal_routes.py 10/10 PASS; tests/test_security_regression.py 104/104 PASS unchanged.
Citation: commit `eeaea11` (`fix(legal): expose /privacy_policy + /terms_of_service routes + Qaren rebrand (1.B.1, 1.B.7, R22)`).

### R6 — ADDRESSED 2026-05-23 by native-ops
Method: Ahmed confirmed in dispatcher session 2026-05-23 — keep `com.qaren.app` as the canonical bundle ID; no change to fallback-ladder candidates needed. Verified `SmartCompareApp/app.json:17` `ios.bundleIdentifier: "com.qaren.app"` + `app.json:23` `android.package: "com.qaren.app"` already match. Native-ops fallback-ladder research (`app.qaren` → `com.qaren.app` → `bh.qaren.app`) is now moot. Task 1.N.1 ASC bundle-ID-claim console step still pending on Ahmed (A2 Team ID + A3 console session), but the bundle-ID *choice* is locked. AASA template ready with `<APPLE_TEAM_ID>.com.qaren.app` appID per dispatcher-confirmed payload shape `{"applinks":{"apps":[],"details":[{"appID":"<TEAMID>.com.qaren.app","paths":["/r/*","/c/*","/q/*"]}]}}` (matches existing `applinks:qaren.app` associated domain in `app.json:20`).
Citation: dispatcher-relayed confirmation from Ahmed in session 2026-05-23; on-disk `app.json:17` + `app.json:23` unchanged from pre-bundle-D state. No code commit needed for R6 itself — only this ledger update.

### R20 — ADDRESSED 2026-05-23 by backend
Method: Migration 025 (`migrations/025_delete_user_cascade_completeness.sql`) extends `delete_user_cascade(target_user_id uuid)` to cover three Bundle-D-era tables that the original Bundle A cascade missed: `user_usage` (by user_id), `referral_invites` (by referrer_user_id OR redeemed_by_user_id), and `referral_redemptions` (by referrer_user_id OR invitee_user_id). Verified via Supabase MCP `information_schema` query — `expo_push_tokens` is NOT a table; push token is a column `users.expo_push_token`, so it's cleared in the users-row UPDATE alongside `device_fingerprint_hash` (Migration 021 anti-farming hash). `admin_audit_log` intentionally NOT deleted per Session 43 decision (security events must outlive user record). `users` row UPDATEd not DELETEd so admin_audit_log FK resolves. Rollback file `migrations/rollback/025_delete_user_cascade_completeness.sql` restores the exact pre-Bundle-D function body. Static SQL-parse test suite `tests/test_delete_user_cascade.py` 13/13 PASS covers: forward + rollback cover the right tables; SECURITY DEFINER; atomic BEGIN/COMMIT; users-row UPDATE-not-DELETE; admin_audit_log untouched; rollback omits Bundle D additions. Live apply via Supabase MCP deferred to deploy step per dispatcher direction. Security regression 104/104 unchanged.
Citation: commit `6c17ca8` (`feat(migrations): Migration 025 — delete_user_cascade covers Bundle D tables (1.B.5, R20)`).

### R21 — ADDRESSED 2026-05-23 by backend
Method: Added `_scrub_query_string(url)` helper in `app/services/sentry_service.py` with targeted regex `(?<=[?&])(q|query|email|search|text)=[^&#]*` (case-insensitive). Wired into `_before_send` (request.url path) AND `_strip_tokens_from_breadcrumb` (breadcrumb.data.url path — sentry-sdk httpx integration outbound URLs). Five PII param names scrubbed → `[QUERY_REDACTED]` marker (distinct from existing `[TOKEN_REDACTED]` so Sentry UI greps can tell scrub-type apart). Negative-test pack proves bookkeeping params round-trip untouched: `?nocache=true`, `?limit=20`, `?offset=0`, `?sort=desc` all preserved. `?token=` already handled by `_scrub_dict` key-name denylist + wholesale `[a-f0-9]{32,}` pattern — no double-coverage. Tests `tests/test_sentry_service.py` 12/12 PASS (2 pre-Bundle-D preserved + 7 new positive + 3 new negative). Security regression `tests/test_security_regression.py` 104/104 PASS unchanged.
Citation: commit `c12a7c6` (`feat(sentry): scrub PII query-string values in before_send + breadcrumb URLs (1.B.6, R21)`).

### R3 — ADDRESSED 2026-05-23 by backend
Method: Investigation via Supabase MCP found 8 of 11 comparison rows had `schema_version=1` (pre-Migration-020), of which 7 passed the same `_validate_renderable` predicate `database_service.py` uses to gate v2 writes — they were renderable but hidden from the history list/get/count queries by the `eq("schema_version", 2)` filter. One row (Sony WH-1000XM5 vs Bose, `e154397c-...`) had `n_products=0` — failed save, INTENTIONALLY left v1. Migration 026 (`migrations/026_backfill_renderable_v1_comparisons.sql`) is a predicate-gated `UPDATE … SET schema_version = 2 WHERE <Python predicate>` so it remains correct even if extra v1 rows are inserted between dispatch + apply. Rollback uses explicit UUIDs (not predicate) so subsequent v2 inserts can't be accidentally demoted. Per anchor R3 recipe: "if v1 → backfill, NOT new screen code." No FE code change; no read-path filter change. Frontend 1.F.5 confirmed by Native/Ops + Frontend as not needing schema_version logic — error-copy only.
Citation: commit `52e7f01` (`fix(history): Migration 026 — backfill 7 renderable v1 comparisons (R3)`). Applied to prod Supabase via `mcp__plugin_supabase_supabase__apply_migration` 2026-05-23 by team-lead dispatcher session. Pre-apply: 3 v2 / 8 v1. Post-apply: **10 v2 / 1 v1** (exactly the predicted delta — the lone v1 row is the known unrenderable Sony/Bose).

### R20 — APPLIED 2026-05-23 by team-lead (post-merge addendum to existing R20 citation above)
Migration 025 applied to prod Supabase via `mcp__plugin_supabase_supabase__apply_migration` 2026-05-23. `pg_get_functiondef` post-apply confirmed function body matches commit `6c17ca8` byte-for-byte: SECURITY DEFINER preserved, `search_path 'public'` set, 7 DELETE statements + 1 UPDATE present, comment headers intact. Dispatcher pre-apply schema verification cross-checked the actual prod column names — confirmed anchor's `inviter_user_id` was incorrect, backend's `referrer_user_id` is the real column. Live cascade now covers all Bundle-D-era tables.

### R18 — ADDRESSED 2026-05-23 by backend
Method: Anchor R18 first action — grep `reengagement-subs|reengagement_subscriptions` in `app/api/` → ZERO matches. The data path existed (`UserPreferencesRequest.notification_types` accepts the 3-key dict and `reengagement_service.evaluate()` short-circuits on each sub-toggle) but no dedicated FE-facing endpoint did. Added `PUT /api/v1/auth/reengagement-subs` (10/min rate limit, auth required) with body `{decision_insights, peer_decision_updates, decision_retrospectives}` per design § 11 Default #6. Server-side translates the user-facing PLURAL keys (matching FE toggle labels) to the existing SINGULAR keys in `users.preferences.notification_types` (`decision_insight` / `cohort_curiosity` / `decision_retrospective`) so the `reengagement_service` short-circuit logic in `evaluate()` continues to work unchanged. Read-modify-write on `users.preferences` with user-scoped Supabase client (RLS enforces ownership); other prefs fields (budget, priorities, lifestyle, brand_attitude, ai_sharing_enabled, notifications_enabled) preserved. 6 new endpoint tests + 2 pre-Bundle-D RED tests in `TestReengagementSubToggles` (Test agent's triage) flipped GREEN by `@patch _flag_on=True` (fail-CLOSED env). `tests/test_push_token_endpoint.py` 20/20 PASS. `tests/test_security_regression.py` 104/104 unchanged.
Citation: commit `228ff63` (`feat(auth): PUT /api/v1/auth/reengagement-subs endpoint (2.B.7, R18)`).

### R15 — ADDRESSED 2026-05-23 by backend
Method: Audited the 22 `asyncio.create_task` sites in `app/api/*` (anchor said 24; actual grep shows 22 in `app/api/` + the 5 already-wrapped sites in `structured_comparison_service.py` for the 27 total). Per-site judgement: **ALL 22 sites WRAPPED** — every one performs audit/analytics/cohort writeback work where silent exception = lost forensics or wrong KPI. No "skip-with-reason" sites — that pattern doesn't exist in this codebase. Mechanics: extracted the existing M6 helper to `app/utils/async_utils.fire_and_forget(coro, label)`; kept `structured_comparison_service._fire_and_forget` as a thin alias so the 5 in-service call sites keep their import. Each new wrap call carries a stable `label="..."` so Sentry/Railway log aggregation buckets failure patterns. Full WRAP/SKIP decision list lives in the commit message body. Removed 4 now-unused `import asyncio` lines. Tests: 181/181 GREEN (security_regression + push_token_endpoint + legal_routes + account_deletion + delete_user_cascade + sentry_service) + 58/58 GREEN (handler-specific). Zero behaviour change — only the exception-handling done-callback is added per site.
Citation: commit `78aeb23` (`feat(async): _fire_and_forget audit — wrap all 22 sites in app/api/* (2.B.6, R15)`).

### R4 — ADDRESSED 2026-05-23 by backend (Apple 3-leg checkpoint complete)
Method: Apple Sign-In end-to-end checkpoint verified live in prod.
  - **Leg 1 — Service ID + Bundle ID:** `app.qaren.signin` (web flow) + `com.qaren.app` (native iOS Bundle ID) configured by Ahmed in Apple Developer Portal.
  - **Leg 2 — Key + .p8:** Key Name "Qaren Sign in with Apple Key", Key ID `7S9CT35UX7`, Team ID `8K562M549D`. .p8 private key contents handed off via dispatcher session transcript (never committed to repo per security discipline).
  - **Leg 3 — Supabase provider ON:** Ahmed completed A8 dashboard step 2026-05-23. Apple provider toggled to enabled at https://supabase.com/dashboard/project/qulajmyxdbdkchvecmvc/auth/providers with Client IDs field set to `app.qaren.signin,com.qaren.app` (comma-separated dual audience), Secret Key field left blank (web OAuth not needed for native id_token flow), "Allow users without email" ON.
  - **Leg 4 — Backend curl provider-enabled check:** Endpoint discovered as `POST /api/v1/auth/social-login` (single endpoint, provider in body — NOT `/social/apple` as anchor suggested). Gradient triangulation verified: (a) Pydantic accepts `provider:"apple"` Literal whitelist passing; (b) `apple` returns 401 + AUTH_REQUIRED + "Something went wrong" — IDENTICAL response shape to known-enabled `google` baseline (both providers traverse `auth_client.auth.sign_in_with_id_token()`); (c) `bogus` provider rejected by Pydantic 422 before reaching Supabase. The apple-vs-google parity is the GREEN signal — if Apple were not enabled, the upstream Supabase exception ("provider not enabled") would still wrap into the generic "Something went wrong" body, but the apple-vs-google response shapes would not match if one were pre-flight rejected and the other reached id_token validation.
Backend wiring already in place at `app/services/auth_service.py:302 sign_in_with_social(provider, id_token, nonce)` — no code change needed. Caveat: 100% confirmation of the GREEN signal would require Railway log inspection (`Auth error in social_login: ...invalid id_token...` vs `...provider not enabled...`); Railway MCP was unauthenticated at the time of test, so the parity-with-google evidence is the operational substitute. Native/Ops can flip R14's "BOTH" gate to fully ADDRESSED in follow-up.
Citation: A8 dispatcher confirmation 2026-05-23. Prod curl evidence: `apple` HTTP 401 (request_id `a59eb83b-fc97-458a-bc59-cc7ecd3c3ded`) parity with `google` HTTP 401 (request_id `d937a28b-5202-45d7-8297-cfc29cdfcce1`).

### R14 — ADDRESSED 2026-05-23 by native-ops (BOTH legs green)
Method: R14's "BOTH" gate requires (a) Apple Dev Portal "Sign in with Apple" capability on the App ID + (b) entitlement present in the iOS build via `eas.json` / `app.json`. Both legs are now green:
- **Leg a (Apple Dev Portal):** Ahmed completed A3-A7 dispatcher session 2026-05-23 — App ID `com.qaren.app` has "Sign in with Apple" capability enabled, Service ID `app.qaren.signin` created, Key `Qaren Sign in with Apple Key` (Key ID `7S9CT35UX7`) generated with the same capability, .p8 downloaded.
- **Leg b (build-time entitlement):** `expo-apple-authentication` plugin already at `SmartCompareApp/app.json:86` from pre-bundle-D state + `ios.usesAppleSignIn: true` at line 19. Per Expo SDK 54 docs (verified via Context7 `/expo/expo`), the plugin auto-injects `com.apple.developer.applesignin: ["Default"]` into the iOS build's `PrivacyInfo.xcprivacy`-adjacent entitlements file during EAS prebuild — NO manual `ios.entitlements` block needed in app.json. Will be verifiable via `find ios -name "*.entitlements"` after Task 2.N.1 first EAS preview build runs.

Companion controls in the same chain (already addressed in other rows):
- R4 ADDRESSED by backend `faead5e` — full Apple 3-leg checkpoint complete (Service ID → .p8 → Supabase provider → backend curl parity-with-google).
- R5 ADDRESSED by native-ops `03cdc1e` — `expo-apple-authentication` plugin block in app.json.

Citation: `SmartCompareApp/app.json:86` (plugin pre-existing) + `app.json:19` (`usesAppleSignIn: true`) + commit `03cdc1e` (R5 closure) + backend's `faead5e` (R4 closure cross-references the Apple Dev Portal artifacts) + Ahmed A3-A7 dispatcher session confirmation 2026-05-23 for Key ID `7S9CT35UX7` + Service ID `app.qaren.signin`.

### R1 — N/A 2026-05-23 by QA (preventive control surface absent in Bundle D scope)
Method: R1's preventive control is "snapshot middleware → edit → diff → reject reorder" — specifically to catch regression of the `/admin/*` static auth gate (audit C2) when the request_id → security → error → CORS → rate_limiter middleware chain in `app/main.py` is reordered. Verification: `git diff bca2ffe..HEAD -- app/main.py app/middleware/` returns **0 lines** across all 6 middleware files (`__init__.py`, `error_handler.py`, `logging_config.py`, `rate_limiter.py`, `request_id.py`, `security.py`) AND `app/main.py` itself. The preventive control surface is wholly absent in Bundle D scope — Backend's commit set is dominated by service-layer (`app/services/`), route-handler (`app/api/`), and migration changes. No middleware reorder occurred, so no R1 regression is possible.
Citation: `git diff bca2ffe..HEAD -- app/main.py app/middleware/ | wc -l` = 0 (verified by QA 2026-05-23). Bundle D base commit `bca2ffe`.

### R2 — N/A 2026-05-23 by QA (preventive control surface absent in Bundle D scope)
Method: R2's preventive control is "reject any diff that broadens CSP allow-list" — specifically to prevent the strict `default-src 'none'` policy outside `/admin/*` from being weakened. CSP is implemented in `app/middleware/security.py`. Verification: same diff command as R1 above — `app/middleware/security.py` shows 0 lines changed since Bundle D base. No CSP modification occurred, so no R2 regression is possible.
Citation: `git diff bca2ffe..HEAD -- app/middleware/security.py | wc -l` = 0 (verified by QA 2026-05-23). Bundle D base commit `bca2ffe`.


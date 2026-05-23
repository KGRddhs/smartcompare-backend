---
name: Bundle D Native/Ops Anchor
description: Per-lane scope + verification commands + risk subset for Bundle D Native/Ops agent
type: project
---

# Lane: Native/Ops

## My scope (~10 tasks across Phases 1-4 + 3 web consoles)

### Phase 1 — Foundation
1. **Task 1.N.1** — Bundle ID claim in ASC. **Fallback ladder (R6):** `app.qaren` → `com.qaren.app` → `bh.qaren.app` → escalate to Ahmed. Update `SmartCompareApp/app.json` `ios.bundleIdentifier` with claimed value.
2. **Task 1.N.2** — Apple Developer Portal Service ID + .p8 key. Service ID `app.qaren.signin` configured to primary App ID `app.qaren`; domains `qaren.app`; return URL `https://web-production-58776.up.railway.app/api/v1/auth/social/apple/callback`. Download .p8 to local secrets vault (NOT in repo). Hand off Service ID + Team ID + Key ID + .p8 contents to Backend via secure channel (NOT PR comment). Update R4 ledger.
3. **Task 1.N.3** — `expo-apple-authentication` install + plugin (R5 critical). `cd SmartCompareApp && npx expo install expo-apple-authentication`. Add plugin entry to `app.json` + `ios.usesAppleSignIn: true` + `ios.entitlements: {"com.apple.developer.applesignin": ["Default"]}`. **Commit plugin block BEFORE any EAS build trigger** (R5).
4. **Task 1.N.4** — C16 `expo-notifications` plugin. Verify installed via `grep expo-notifications SmartCompareApp/package.json`. Add plugin block with iOS `NSUserNotificationUsageDescription` + Android `POST_NOTIFICATIONS`. Plugin object form with icon/color/sounds.
5. **Task 1.N.5** — EAS secret `SENTRY_AUTH_TOKEN`. Ahmed creates Sentry auth token (Account → Auth Tokens; scopes `project:read/write/releases`). `eas secret:create --scope project --name SENTRY_AUTH_TOKEN --value "<token>"`. Remove `SENTRY_DISABLE_AUTO_UPLOAD=true` + `SENTRY_ALLOW_FAILURE=true` from `eas.json` preview profile.
6. **Task 1.N.6** — DNS planning for `qaren.app`. Recommend Vercel for static landing + subpages. Document in PR comment: A/AAAA to Vercel, subpages `/privacy`, `/terms`, `/support`; `www.qaren.app` 301 → apex; TTL 300s during cutover (R24). No commit yet.

### Phase 2 — Integration
7. **Task 2.N.1** — EAS preview build. Verify all Phase 1 ops commits in place via `git log --oneline | head -10`. `cd SmartCompareApp && eas build --profile preview --platform ios --non-interactive`. Wait ~15 min. `eas build:list --limit 1` shows finished + .ipa URL. Install on Ahmed's device. Smoke Google + Apple Sign-In.
8. **Task 2.N.2** — Landing page hosting. Create Vercel project; serve `/index.html` (placeholder "Qaren — Coming soon to App Store / Google Play"), `/privacy.html` + `/terms.html` (markdown→HTML render of post-C15 rebranded legal docs), `/support` 301 → `mailto:support@qaren.app`. Verify on Vercel preview URL FIRST (R24), then Cloudflare DNS A/AAAA → Vercel TTL 300s.

### Phase 3 — TestFlight Pipeline
9. **Task 3.N.1** — EAS production build. `eas build --profile production --platform ios --non-interactive`. Wait ~20 min.
10. **Task 3.N.2** — App Store Connect upload via `eas submit --profile production --platform ios --latest`. Wait Apple processing ~30 min (R8). Once "Ready to Test": configure internal test group, add Ahmed's email. Ahmed installs TestFlight → installs Qaren → cold-starts.
11. **Task 3.N.3** — ASC Privacy Nutrition Labels (R13). Draft per data flows: Contact Info (Email), Identifiers (device fingerprint SHA-256, user ID), Usage Data (analytics), User Content (search queries when `ai_sharing_enabled=true`), Diagnostics (Sentry crash logs). **BLOCKING:** post draft to PR for Ahmed approval BEFORE ASC submission.

### Phase 4 — Close-out
12. **Task 4.N.1** — App icon + splash final audit. `assets/icon.png` + `assets/splash.png`: zero "SmartCompare" residue, Qaren wordmark only, iOS densities @1x/@2x/@3x present (or single 1024×1024 auto-scaling), Android mdpi through xxxhdpi, EN+AR locales render correctly.

## Memory facts I need (anti-hallucination)
- App name is "Qaren" (قارن). NEVER write "SmartCompare" anywhere — icon, splash, plugin descriptions, ASC strings.
- Two-lever launch model: Backend deploys (Railway via git push, ~90s) and mobile JS bundle (EAS update/build) are **independent**. Merging to main does NOT push frontend code to phones.
- `appVersionSource: "remote"` in `eas.json`. EAS builds bump version via `--auto-submit` flow.
- Interactive Expo commands (`eas login`, `eas build` first-run) need a real terminal — Ahmed runs these directly.
- `expo-apple-authentication` is a **config plugin** — first EAS build FAILS if `app.json` plugin block missing (R5). MUST commit plugin block FIRST.
- Apple Sign-In entitlement MUST exist in BOTH Apple Dev Portal Service ID + `eas.json` `ios.entitlements` (R14).
- Bundle ID conflict possible — fallback ladder ready (R6).
- ASC upload + processing window is ~30 min (R8). Phase 3 budgets this explicitly; tester invite waits.
- Age policy locked: 13+ general audience including teens. Apple **12+**, Google Play **Teen**. Do NOT enroll in Apple "Kids" or Google "Designed for Families".
- Sentry RN sourcemap upload currently DISABLED in `eas.json` preview (`SENTRY_DISABLE_AUTO_UPLOAD=true` + `SENTRY_ALLOW_FAILURE=true`). Task 1.N.5 enables.
- `expo-notifications` plugin missing from `app.json` today (C16 gap surfaced 2026-05-23). Push won't work without it.
- DNS TTL 300s during cutover (R24) for fast revert.
- Apple Developer subscription ($99/year) acquired by Ahmed — Apple Sign-In path UNBLOCKED.

## Pre-flight commands (run before starting)
- `git log --oneline -5` — confirm starting commit
- `cd SmartCompareApp && grep -E '"expo-apple-authentication"|"expo-notifications"' package.json` — pre-install state
- `cd SmartCompareApp && cat app.json | head -50` — current plugin list
- `cd SmartCompareApp && cat eas.json` — current build profiles + env
- `eas whoami` — confirm Ahmed logged in
- `mcp__plugin_supabase_supabase__get_project` — confirm Supabase access

## Verification commands (run before "done")
- `cd SmartCompareApp && npx expo-doctor` — config health check after `app.json` edits
- `cd SmartCompareApp && eas build:list --limit 3` — recent builds status
- `curl -i https://qaren.app/privacy.html` — landing page subpage 200
- `curl -i https://qaren.app/` — placeholder 200
- ASC TestFlight tab shows "Ready to Test" status
- Ahmed confirms installed + cold-start green via PR comment

## Risks I own (subset of R1-R24)
- **R4** Apple Sign-In 3-leg checkpoint — post comment with all 4 GREEN (Service ID, .p8, Supabase ON, backend curl 200) BEFORE Frontend wires button
- **R5** `expo-apple-authentication` config plugin — `app.json` plugin block committed FIRST in own commit BEFORE EAS build
- **R6** Bundle ID conflict — fallback ladder ready; escalate to Ahmed before proceeding if all 3 taken
- **R7** EAS production build signing — Apple Distribution cert + provisioning profile via Apple Dev Portal; EAS auto-manages if `eas.json` ios.credentials configured
- **R8** ASC 30-min upload+processing window — Phase 3 budgets explicitly; tester invite waits until processing complete
- **R13** ASC Privacy Nutrition Labels — drafted per observed data flows; Ahmed approves before ASC submission
- **R14** Apple Sign-In entitlement in BOTH Apple Dev Portal + `eas.json` `ios.entitlements` — checklist verifies both
- **R24** DNS propagation delay — hosting tested via direct Vercel hostname FIRST; DNS cutover only after green; TTL 300s

## Dependencies
- **Blocked by:** Ahmed Apple Developer Team ID (Tasks 1.N.1, 1.N.2 final), Ahmed approval of Privacy Nutrition Labels (Task 3.N.3), Ahmed Claude-Design output (landing page Phase 2 if non-placeholder), Ahmed TestFlight invite acceptance (Task 3.N.2 close)
- **Blocking:** Backend 1.B.4 (Apple provider) waits on my 1.N.2 Service ID + .p8; Frontend Phase 3 simulator sign-off (3.F.1) waits on my 2.N.1 EAS preview build; Backend Phase 3 prod curl smoke can run independent; Phase 4 sign-off waits on my 4.N.1 asset audit + 3.N.2 TestFlight ready

## Rollback recipes
- **EAS build broken:** keep prior preview build live; do not promote production; revert offending app.json/eas.json/package.json commit; rebuild via `eas build --profile preview --platform ios`
- **TestFlight build crashes:** do not promote production; investigate via Sentry; rebuild after fix
- **Bundle ID claimed-but-wrong:** ASC bundle IDs cannot be deleted — register a new bundle from fallback ladder; deprecate prior
- **DNS broken:** rollback Cloudflare A/AAAA to prior records (TTL 300s honors quickly); landing page falls back to GitHub Pages placeholder if needed
- **expo-notifications plugin breaks build:** revert `app.json` plugin block commit; push receipts continue to fail silently (pre-Bundle-D state)

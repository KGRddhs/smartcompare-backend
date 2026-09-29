---
name: qaren-eas-deploy
description: Use when shipping OTA updates via eas update, building APKs / iOS bundles via eas build, configuring EAS channels (development / preview / production), bumping expo.version, runtime version policy, two-lever launch model, or when JS-only fixes need to reach testers. Covers Apple Developer ($99/yr) gating.
last_verified: 2026-07-04 (partial re-check 2026-09-29: channels, OTA groups, store-build rules, App Store link; the Apple-subscription gating section was not re-verified)
update_when_changing:
  - SmartCompareApp/eas.json
  - SmartCompareApp/app.json
  - SmartCompareApp/package.json (when bumping expo SDK)
---

# Qaren EAS Update Infrastructure

## EAS project details

Expo project `@kersher2/qaren` (ID `387a4fcb-76f6-4857-a2fb-39482ca4bd40`). `runtimeVersion.policy: "appVersion"` — bumping `expo.version` forces a rebuild; pure-JS fixes ship via OTA. Channels in `SmartCompareApp/eas.json`: `development` / `preview` / `production`. `appVersionSource: "remote"`.
- **OTA push:** `cd SmartCompareApp && eas update --branch <channel> --message "..."`. Free, no rebuild, lands on next app open.
- **Rebuild required when:** native module added/removed, app.json plugin/permission changes, `expo.version` bumped.
- **`eas login` / `eas credentials` (interactive credential setup) need a real terminal** — Claude's Bash cannot pipe TTY. BUT once credentials exist, `eas build --profile preview --platform ios --non-interactive --no-wait` and `eas update --branch <ch> --non-interactive` **run headless from Claude's Bash** (verified 2026-07-04 — Ahmed's account has ad-hoc certs valid to May 2027 + 2 registered iPhone UDIDs; `eas whoami` = `kersher2`). `--no-wait` queues + returns a build URL immediately.
- **`eas build:configure` gotcha:** duplicates existing `app.json` entries (associatedDomains, intentFilters, permissions). Dedupe manually after running.

## OTA propagation + build troubleshooting (learned 2026-07-04)

- **OTA needs TWO cold launches to activate.** expo-updates default `fallbackToCacheTimeout:0` → on cold start the app loads the CACHED bundle and downloads the new one in the background; the new bundle runs on the NEXT cold start. One relaunch = still old code; two full quit→reopen = new code. A "stuck" OTA is almost always this propagation, NOT a config problem.
- **Verify the update is served (device's-eye view) before blaming config:** `curl "https://u.expo.dev/387a4fcb-76f6-4857-a2fb-39482ca4bd40" -H "expo-platform: ios" -H "expo-runtime-version: 1.0.0" -H "expo-channel-name: preview"` → the manifest `id` returned IS the update a matching device receives. Cross-check `eas channel:view preview` (current group), `eas build:list` (installed build's runtime/channel), `railway deployment list --service web --json` (live backend commit — a backend fix reaches phones WITHOUT an OTA; only JS changes need `eas update`/`eas build`, don't conflate).
- **Fresh iOS `eas build` can fail at `pod install` with ZERO code change** — managed Expo pins no `Podfile.lock`, so transitive Google/Firebase pods (via `@react-native-google-signin`) resolve to LATEST; a drift → e.g. "AppCheckCore depends on GoogleUtilities/RecaptchaInterop which do not define modules". **Fix (PR #22):** `expo-build-properties` → `"ios": { "extraPods": [{ "name": "GoogleUtilities", "modular_headers": true }, { "name": "RecaptchaInterop", "modular_headers": true }] }` (v1.0.10 supports `extraPods`+`modular_headers`+`useFrameworks`; NO global `useModularHeaders`).
- **Debug a failed build:** `eas build:view <id> --json` → `error.message` names the phase; `logFiles[0]` is a GZIP signed GCS URL → `curl --compressed <url>` (or gzip.decompress) → bundled JSONL logs; grep the failing phase (e.g. `INSTALL_PODS`).

## Two-lever launch model

Backend deploys (Railway via `git push origin main`, ~90s) and mobile JS bundle deploys (EAS via `eas update` / `eas build`) are **independent**. Merging to main does NOT push frontend code to phones — phones run their last-bundled JS until an EAS update/build reaches them. New mobile features need BOTH levers fired.

## Channels in `SmartCompareApp/eas.json`

- `development` — dev client builds, debug bundle
- `preview` — internal tester channel
  - Current group: `561d2cba-f374-40e8-866b-3bfe6c7c9c3b` (published 2026-09-24 from main `ab9442ae`, runtime 1.0.0) — every client merge after `ab9442ae` (incl. session 69 #251/#253/#255/#257/#258/#269/#274) is NOT on phones until the next OTA or the store build
  - (history) Bundle A baseline `40719e26`, Bundle E `d540c1e6-c07c-46d7-ac69-5103dde1fb56` — superseded
- `production` — App Store / Play: `autoIncrement`, channel `production`, which has NEVER received an update (every OTA so far went to `preview`). Store-build rules (session 69, EXPO-11 / BLD-BP-05): the App Store build runs exactly the JS it was built with, so build it from a main that already contains every fix (`eas build --profile production` then `eas submit`; U10 fills the `submit.production` block once the ASC app id exists); after launch ship JS hotfixes with `eas update --branch production` (never `preview`); bump `expo.version` for every native change and never for a JS-only hotfix. #254's native config (supportsTablet false, locales, purpose strings, privacy manifest) reaches users only in this build; #253's cert pins are OTA-capable but must also be in the store binary.

## Apple Developer subscription ($99/yr) — gating dependencies

Until subscribed, the following are blocked:
- iOS production builds
- TestFlight distribution
- App Store ID swap in Cloudflare Worker (`idTBD` → real ID)
  **SESSION 69 CORRECTION (2026-09-29):** (#273) also fill `APP_STORE_URL` in `landing/open.html` (the /c/ /r/ /q/ hand-off page, empty until the App Store record exists) and redeploy the landing (`railway up landing --path-as-root -s qaren-landing -d`).
- Real-user iOS QA on Bundle E rings/dimension-bars/factual-verdict

## EAS dev APK + Android emulator storage gotcha (Bundle B/C/D)

Dev client APKs are ~200+ MB (Hermes + debugger + bundle). Default AVD ships with 6 GB internal storage which fills fast → `adb: failed to install ... INSTALL_FAILED_INSUFFICIENT_STORAGE`. Fix: Android Studio → Device Manager → ⋮ next to AVD → Wipe Data → Cold Boot (frees several GB by resetting the user partition). Alternative: increase Internal Storage to 8+ GB in AVD Advanced Settings.

## Sources (verify against current state before recommending changes)

- `SmartCompareApp/eas.json` — channels + `appVersionSource: "remote"`
- `SmartCompareApp/app.json` — runtime version policy, plugin list, permissions
- Expo project: `@kersher2/qaren` (ID `387a4fcb-76f6-4857-a2fb-39482ca4bd40`)
- Operational runbook: `docs/runbooks/qaren-canary-onboarding.md`
- Bundle E EAS state: `docs/SESSION_BUNDLES.md` (Bundle E section, EAS state post-merge)

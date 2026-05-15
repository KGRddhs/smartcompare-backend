---
name: qaren-eas-deploy
description: Use when shipping OTA updates via eas update, building APKs / iOS bundles via eas build, configuring EAS channels (development / preview / production), bumping expo.version, runtime version policy, two-lever launch model, or when JS-only fixes need to reach testers. Covers Apple Developer ($99/yr) gating.
last_verified: 2026-05-16
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
- **Interactive Expo commands** (`eas login`, `eas build`, `wrangler login`) need a real terminal — Claude's `!` prefix cannot pipe TTY; Ahmed runs these directly.
- **`eas build:configure` gotcha:** duplicates existing `app.json` entries (associatedDomains, intentFilters, permissions). Dedupe manually after running.

## Two-lever launch model

Backend deploys (Railway via `git push origin main`, ~90s) and mobile JS bundle deploys (EAS via `eas update` / `eas build`) are **independent**. Merging to main does NOT push frontend code to phones — phones run their last-bundled JS until an EAS update/build reaches them. New mobile features need BOTH levers fired.

## Channels in `SmartCompareApp/eas.json`

- `development` — dev client builds, debug bundle
- `preview` — internal tester channel
  - Bundle A baseline group `40719e26`
  - Bundle E group `d540c1e6-c07c-46d7-ac69-5103dde1fb56` (live, both iOS + Android, runtime 1.0.0)
- `production` — App Store / Play (not used until Apple Developer subscription active)

## Apple Developer subscription ($99/yr) — gating dependencies

Until subscribed, the following are blocked:
- iOS production builds
- TestFlight distribution
- App Store ID swap in Cloudflare Worker (`idTBD` → real ID)
- Real-user iOS QA on Bundle E rings/dimension-bars/factual-verdict

## EAS dev APK + Android emulator storage gotcha (Bundle B/C/D)

Dev client APKs are ~200+ MB (Hermes + debugger + bundle). Default AVD ships with 6 GB internal storage which fills fast → `adb: failed to install ... INSTALL_FAILED_INSUFFICIENT_STORAGE`. Fix: Android Studio → Device Manager → ⋮ next to AVD → Wipe Data → Cold Boot (frees several GB by resetting the user partition). Alternative: increase Internal Storage to 8+ GB in AVD Advanced Settings.

## Sources (verify against current state before recommending changes)

- `SmartCompareApp/eas.json` — channels + `appVersionSource: "remote"`
- `SmartCompareApp/app.json` — runtime version policy, plugin list, permissions
- Expo project: `@kersher2/qaren` (ID `387a4fcb-76f6-4857-a2fb-39482ca4bd40`)
- Operational runbook: `docs/runbooks/qaren-canary-onboarding.md`
- Bundle E EAS state: `docs/SESSION_BUNDLES.md` (Bundle E section, EAS state post-merge)

# Bundle D — Landing Page Static Templates

**Status:** READY TO DEPLOY (Phase 2, Task 2.N.2) — pending two placeholder substitutions
**Date:** 2026-05-23
**Owner:** native-ops

## Files

### `apple-app-site-association.json`
Universal Links AASA file. **MUST be served at:**
- Path: `https://qaren.app/.well-known/apple-app-site-association`
- **NO `.json` extension** in URL (Apple's CDN looks for the extensionless path)
- `Content-Type: application/json` (Vercel header override required)

**Placeholder to substitute before deploy:**
- `APPLE_TEAM_ID_PLACEHOLDER` → Ahmed's Apple Developer Team ID (A2, 10 chars alphanumeric)

Shape per dispatcher confirmation in 2026-05-23 session: `appID` (single string) + `paths` (array). Compatible with iOS 9+ (deprecated `applinks.apps` empty array kept for backward compat).

Paths `/r/*` `/c/*` `/q/*` match existing app.json wiring:
- `/r/*` — referral invite codes (handled by referral_routes.py + Loop 1/2 flow)
- `/c/*` — shared comparison links (handled by share_routes.py public GET)
- `/q/*` — quick query deep links (future — currently scaffolded only)

### `assetlinks.json`
Android Digital Asset Links. **MUST be served at:**
- Path: `https://qaren.app/.well-known/assetlinks.json`
- Path INCLUDES `.json` extension (Google convention, unlike Apple)
- `Content-Type: application/json`

**Placeholder to substitute before deploy:**
- `ANDROID_SIGNING_CERT_SHA256_PLACEHOLDER` → SHA-256 fingerprint of production Android signing cert. Pull AFTER Task 2.N.1 EAS preview build via:
  ```bash
  cd SmartCompareApp && eas credentials -p android --profile production
  # OR after first prod build:
  eas credentials -p android --profile production --keystore-info
  ```

Package name `com.qaren.app` matches `app.json:23` `android.package`. Confirmed locked by Ahmed dispatcher session 2026-05-23.

## Deploy step-by-step

1. Wait for A2 (Apple Team ID) — substitute placeholder in `apple-app-site-association.json`.
2. Wait for Task 2.N.1 EAS preview build to complete — pull Android signing cert SHA-256 — substitute placeholder in `assetlinks.json`.
3. Copy both files into the Vercel deployment under `public/.well-known/`:
   ```
   public/
     .well-known/
       apple-app-site-association     ← NO .json extension
       assetlinks.json                ← WITH .json extension
     index.html
     privacy.html
     terms.html
   vercel.json                        ← Content-Type override block
   ```
4. Deploy to Vercel preview URL FIRST (R24 — verify-before-flip).
5. Validate:
   ```bash
   curl -sI https://qaren-landing.vercel.app/.well-known/apple-app-site-association | grep -i content-type
   # Expect: content-type: application/json

   curl -s https://qaren-landing.vercel.app/.well-known/apple-app-site-association | python -m json.tool
   # Expect: valid JSON, no placeholders, Team ID populated

   curl -sI https://qaren-landing.vercel.app/.well-known/assetlinks.json | grep -i content-type
   # Expect: content-type: application/json

   curl -s https://qaren-landing.vercel.app/.well-known/assetlinks.json | python -m json.tool
   # Expect: valid JSON, no placeholders, cert SHA-256 populated
   ```
6. Once green on preview URL, flip DNS A/AAAA to Vercel (TTL 300s per R24).
7. Validate Apple CDN cached the new AASA (may take 24h):
   ```bash
   curl -i https://app-site-association.cdn-apple.com/a/v1/qaren.app
   ```

## Why these files matter

- **AASA on iOS:** without it, when Mobile Safari sees `https://qaren.app/r/QR-ABC123`, it WILL NOT open the Qaren app — it'll just load the URL in Safari. AASA tells iOS "the Qaren app claims these paths."
- **assetlinks.json on Android:** without it, Chrome on Android shows a disambiguation prompt ("Open in Qaren / Open in Chrome") on every link tap, breaking the deep-link UX. With it, the app opens directly.
- **App-side wiring already in place:** `app.json:20` `applinks:qaren.app` + Android intent filters at `app.json:30-46`. The native side trusts these files at the verified domain.

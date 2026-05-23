# Qaren Landing Page (Bundle D Task 2.N.2 — pre-build)

**Status:** READY for Vercel preview deploy + Ahmed QA pass. NOT yet on `qaren.app`.
**Date:** 2026-05-23
**Owner:** native-ops

## What this is

The static landing site that goes live at `https://qaren.app/` post-Phase-2. Per dispatcher's Phase 2 narrowing: built in Phase 1 idle so Phase 2 collapses to "deploy + DNS cutover" instead of "build + deploy + cutover."

## File tree

```
landing/
├── README.md                                      ← this file
├── index.html                                     ← "Coming soon" placeholder
├── privacy.html                                   ← Privacy Policy (HTML render of app/legal/privacy_policy.md post-Qaren-rebrand commit eeaea11)
├── terms.html                                     ← Terms of Service (same source)
├── support.html                                   ← Support — meta-refresh to mailto + visible button fallback
├── vercel.json                                    ← Headers config (cleanUrls: true → /support resolves to /support.html)
└── .well-known/
    ├── apple-app-site-association                 ← AASA, NO file extension, Team ID 8K562M549D substituted
    └── assetlinks.json                            ← Android App Links, cert SHA-256 placeholder
```

**Note on `/support`:** an HTTP 301/308 redirect with `mailto:` destination does NOT work cross-browser (Chrome/Safari inconsistent, Firefox rejects). Instead, `vercel.json` `cleanUrls: true` resolves `/support` → `/support.html`, which combines a `<meta http-equiv="refresh" content="0; url=mailto:support@qaren.app">` immediate-redirect with a visible "Email support@qaren.app" button as the no-redirect fallback.

## Design notes

- **Brand:** emerald `#10B981` accent, Geist-equivalent fallback Inter font (Inter loaded via Google Fonts CDN), Cairo for Arabic title.
- **Visual mark:** inline SVG concentric-circles motif matching `src/components/illustrations/ConcentricMotif.tsx` (the app's brand language). Avoids dependency on `assets/icon.png` which is still an Expo placeholder per asset audit (A5 pending).
- **Mobile-first:** clamp() responsive type, viewport-fit cover for notch devices, prefers-color-scheme dark variant.
- **Zero scary copy:** no "couldn't" / "try again" / "Failed to" anywhere. "Coming soon" framed as anticipation, not delay.
- **App Store + Google Play badges:** present but `pointer-events: none` + opacity 0.6 — visual placeholder only. Wire up real links post-TestFlight Phase 3.
- **No JavaScript.** Pure HTML+CSS+webfonts. Reduces attack surface; lighthouse scores stay green.
- **Favicon:** `index.html` references `/favicon.png` — same Expo-placeholder issue as the app icon (A5 blocker). Will copy `SmartCompareApp/assets/favicon.png` into `landing/` only after the asset audit's Option A/B/C choice lands. Not blocking preview deploy — browsers tolerate missing favicons.

## Deploy step-by-step (Phase 2 Task 2.N.2)

### 1. Vercel project setup (one-time, Ahmed runs)
```bash
# From repo root:
cd landing/
vercel link            # or: vercel deploy --prebuilt
# Choose project name: qaren-landing (or whatever Ahmed prefers)
# Confirm directory + scope
```

### 2. Preview deploy
```bash
vercel deploy --prebuilt    # OR just: vercel
# Returns preview URL like https://qaren-landing-abc123.vercel.app/
```

### 3. Preview validation (before DNS cutover — R24)
```bash
PREV="https://qaren-landing-abc123.vercel.app"

curl -sI "$PREV/" | head -5
# Expect: HTTP/2 200, content-type: text/html

curl -sI "$PREV/privacy.html"
curl -sI "$PREV/terms.html"
# Both 200

curl -sI "$PREV/.well-known/apple-app-site-association" | grep -i content-type
# Expect: content-type: application/json

curl -s "$PREV/.well-known/apple-app-site-association" | python -m json.tool
# Expect: valid JSON, appID populated with 8K562M549D.com.qaren.app

curl -sI "$PREV/.well-known/assetlinks.json" | grep -i content-type
# Expect: content-type: application/json

curl -sI "$PREV/support" | head -3
curl -sI "$PREV/support.html" | head -3
# Expect: both 200 with text/html (cleanUrls true → /support resolves to /support.html).
# /support.html ships a <meta http-equiv="refresh"> to mailto: AND a visible
# "Email support@qaren.app" button as the no-redirect fallback (HTTP 301 to
# mailto: does NOT work cross-browser; this two-track approach does).

# Security headers smoke
curl -sI "$PREV/" | grep -iE 'strict-transport|x-frame|x-content|referrer|permissions'
# Expect: 5 headers, all present
```

### 4. Ahmed QA pass on preview URL
- Visual check (light + dark mode)
- Mobile breakpoint check (iPhone SE width / iPhone 15 Pro Max width)
- Link audit (Privacy, Terms, Support, footer)
- AASA + assetlinks.json content correctness

### 5. DNS cutover (Cloudflare A/AAAA, TTL 300s — R24)
Per `docs/runbooks/bundle-d-dns-and-hosting.md` § "Phase 2 step-by-step." Brief reprise:
1. Drop TTL to 300s 24h ahead.
2. Flip A 76.76.21.21 + AAAA + CNAME www.
3. Wait 5-15 min propagation.
4. Validate at apex via `curl -i https://qaren.app/.well-known/apple-app-site-association`.
5. Validate Apple CDN cached the AASA after ~24h.

## Pre-deploy substitutions still pending

- ☑ Apple Team ID `8K562M549D` — DONE (commit `6121432`)
- ☐ Android signing cert SHA-256 in `.well-known/assetlinks.json` — pull from `eas credentials -p android --profile production` AFTER Task 2.N.1 EAS preview build completes. Until substituted, Android App Links will not auto-open Qaren from web links — Chrome on Android will show disambiguation prompt instead.

## Known content gaps (NOT blocking preview deploy)

1. **Stale referral copy in `terms.html` § 12.** ToS references "3 shares per week" but per Migration 023 + CLAUDE.md the cap moved to **3 LIFETIME per device** in Bundle B/C/D. Backend's `eeaea11` rebrand only changed brand strings (SmartCompare → Qaren); did NOT update the policy math. Surfaced to dispatcher — fix is Backend's R22 territory.
2. **Two new email addresses** the legal docs introduce: `privacy@qaren.app` (Privacy § 12) and `legal@qaren.app` (Terms § 14). Plus `support@qaren.app` from A7. Ahmed needs to set up forwarding for ALL THREE before launch — combine into single A7 ask.
3. **Arabic mirror** of all 3 HTML pages — deferred. Body already has `body:lang(ar)` Cairo + RTL CSS hooks; building the AR pages is a Phase 2 polish item.
4. **Favicon** — Expo placeholder (no Qaren brand). Same A5 dependency as the asset audit.
5. **Open Graph image** — not yet shipped. `<meta property="og:image">` missing in `index.html`. Quick win for Phase 2 polish.

## Why these files are committed in `landing/` not deployed yet

- DNS cutover is Phase 2 work, blocked on A4 + A6 + A7.
- Vercel project creation is interactive (Ahmed runs `vercel link` in a real terminal).
- Pre-committing the static files lets Ahmed QA the visuals via preview URL FIRST per R24 (verify-before-flip).

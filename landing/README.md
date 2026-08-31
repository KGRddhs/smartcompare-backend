# Qaren Landing Page (Bundle D Task 2.N.2 — pre-build)

**Status:** READY for Railway deploy + Ahmed QA pass. NOT yet on `qaren.app`.
**Date:** 2026-05-23 (refit for Railway hosting per dispatcher A6 decision)
**Owner:** native-ops

## What this is

The static landing site that goes live at `https://qaren.app/` post-Phase-2. Per dispatcher's Phase 2 narrowing: built in Phase 1 idle so Phase 2 collapses to "deploy + DNS cutover" instead of "build + deploy + cutover."

**Hosting:** Railway (chosen by Ahmed for single-vendor consolidation with the existing FastAPI backend; was Vercel in earlier drafts — see `docs/runbooks/bundle-d-landing-templates/vercel.json.alternative` for the prior config).

## File tree

```
landing/
├── README.md                                      ← this file
├── index.html                                     ← "Coming soon" placeholder + Compare Smart tagline
├── privacy.html                                   ← Privacy Policy (HTML render of app/legal/privacy_policy.md post-Qaren-rebrand + post-a23ed51-policy-fix)
├── terms.html                                     ← Terms of Service (same source)
├── support.html                                   ← Support — meta-refresh to mailto + visible button fallback
├── Dockerfile                                     ← nginx:alpine static-serve image for Railway
├── nginx.conf.template                            ← envsubst template (binds nginx to $PORT) + headers + .well-known MIME
├── railway.toml                                   ← Railway service config (DOCKERFILE builder, /healthz)
└── .well-known/
    ├── apple-app-site-association                 ← AASA, NO file extension, Team ID 8K562M549D substituted
    └── assetlinks.json                            ← Android App Links, cert SHA-256 placeholder
```

**Note on `/support`:** an HTTP 301/308 redirect with `mailto:` destination does NOT work cross-browser (Chrome/Safari inconsistent, Firefox rejects). Instead, nginx's `location = /support { try_files /support.html =404; }` serves `support.html` directly. The HTML combines `<meta http-equiv="refresh" content="0; url=mailto:support@qaren.app">` immediate-redirect with a visible "Email support@qaren.app" button as the no-redirect fallback. Same behavior as the Vercel `cleanUrls` approach in the archived alternative config.

## Design notes

- **Brand:** emerald `#10B981` accent, Geist (EN) + Cairo (AR) loaded via Google Fonts CDN (Inter retired 2026-08-31 to match the app's Phase-1 Geist swap, `SmartCompareApp/src/theme/fonts.ts`).
- **Listing identity:** "Compare Smart" tagline appears below the Qaren wordmark in `index.html`, matching the Ahmed-locked ASC App Name "Qaren — Compare Smart."
- **Visual mark:** inline SVG concentric-circles motif matching `src/components/illustrations/ConcentricMotif.tsx` (the app's brand language). Avoids dependency on `assets/icon.png` which is still an Expo placeholder per asset audit (A5 pending).
- **Mobile-first:** clamp() responsive type, viewport-fit cover for notch devices, prefers-color-scheme dark variant.
- **Zero scary copy:** no "couldn't" / "try again" / "Failed to" anywhere. "Coming soon" framed as anticipation, not delay.
- **App Store + Google Play badges:** present but `pointer-events: none` + opacity 0.6 — visual placeholder only. Wire up real links post-TestFlight Phase 3.
- **No JavaScript.** Pure HTML+CSS+webfonts. Reduces attack surface; lighthouse scores stay green.
- **Favicon:** `index.html` references `/favicon.png` — same Expo-placeholder issue as the app icon (A5 blocker). nginx silently 404s the favicon (`log_not_found off`) until A5 resolves so the access logs don't fill with noise. Browsers tolerate missing favicons.

## Deploy step-by-step (Phase 2 Task 2.N.2 — Railway)

### 1. Local Docker smoke (optional but recommended)
```bash
cd landing/
docker build -t qaren-landing:dev .
docker run --rm -p 8080:8080 -e PORT=8080 qaren-landing:dev
# In another terminal:
curl -sI http://localhost:8080/
curl -s http://localhost:8080/.well-known/apple-app-site-association | python -m json.tool
```

### 2. Railway service creation (one-time, Ahmed runs in real terminal)
```bash
cd landing/
railway login              # cached in %USERPROFILE%\.railway if previously authed
railway link               # link this dir to an existing Railway project, OR:
railway init               # create a new "qaren-landing" service in the existing Qaren project
# Confirm project + environment selections.
```

The landing/ directory becomes a **separate service** from the existing FastAPI backend service (`web-production-58776.up.railway.app`). Both live under the same Railway project; different Dockerfiles + different entrypoints.

### 3. Deploy preview
```bash
railway up                 # builds Dockerfile, pushes to Railway, deploys
# Returns deployment URL like https://qaren-landing-production.up.railway.app
```

### 4. Preview validation (BEFORE DNS cutover — R24 verify-before-flip)
```bash
PREV="https://qaren-landing-production.up.railway.app"

curl -sI "$PREV/" | head -5
# Expect: HTTP/2 200, content-type: text/html

curl -sI "$PREV/healthz"
# Expect: HTTP/2 200, content-type: text/plain, body "ok"

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
# Expect: both 200 with text/html (nginx try_files: /support → /support.html).
# /support.html ships a <meta http-equiv="refresh"> to mailto: AND a visible
# "Email support@qaren.app" button as the no-redirect fallback.

# Security headers smoke
curl -sI "$PREV/" | grep -iE 'strict-transport|x-frame|x-content|referrer|permissions'
# Expect: 5 headers (HSTS, X-Frame-Options, X-Content-Type-Options,
# Referrer-Policy, Permissions-Policy)
```

### 5. Ahmed QA pass on Railway preview URL
- Visual check (light + dark mode via prefers-color-scheme)
- Mobile breakpoint check (iPhone SE width / iPhone 15 Pro Max width)
- Link audit (Privacy, Terms, Support, footer)
- AASA + assetlinks.json content correctness

### 6. DNS cutover (TTL 300s — R24)
Per `docs/runbooks/bundle-d-dns-and-hosting.md` § "Phase 2 step-by-step (Railway)." Brief reprise:
1. Drop existing `qaren.app` DNS records to TTL 300s, 24h ahead.
2. Railway dashboard → Settings → Domains → add custom domain `qaren.app` (and optionally `www.qaren.app`).
3. Railway issues a CNAME target like `qaren-landing-production.up.railway.app` for the apex.
4. **Apex CNAME limitation:** DNS doesn't strictly allow CNAME at the apex (RFC 1034). Use CNAME-flattening if your DNS host supports it (Cloudflare ALIAS, Vercel apex, Route 53 ALIAS, DNSimple ALIAS). Otherwise CNAME on `www.qaren.app` only + A-record forwarding for apex via Cloudflare-flat / Netlify-style ALIAS.
5. Wait 5-15 min propagation. `dig +short qaren.app @8.8.8.8`.
6. Railway auto-issues a Let's Encrypt cert (5-10 min after DNS resolves).
7. Validate at apex via `curl -i https://qaren.app/.well-known/apple-app-site-association`.
8. Validate Apple CDN cached the AASA after ~24h: `curl -i https://app-site-association.cdn-apple.com/a/v1/qaren.app`.
9. Once stable for 48h, raise TTLs back to 3600s.

## Pre-deploy substitutions still pending

- ☑ Apple Team ID `8K562M549D` — DONE (commit `6121432`)
- ☐ Android signing cert SHA-256 in `.well-known/assetlinks.json` — pull from `eas credentials -p android --profile production` AFTER Task 2.N.1 EAS preview build completes. Until substituted, Android App Links will not auto-open Qaren from web links — Chrome on Android will show disambiguation prompt instead.

## Known content gaps (NOT blocking preview deploy)

1. ~~Stale referral copy in `terms.html` § 12.~~ **RESOLVED 2026-05-23**: Backend landed `a23ed51 fix(legal): update referral cap to 3 lifetime per device per Migration 023` updating `app/legal/terms_of_service.md` § 12; `landing/terms.html` regenerated to match in commit `6bbe14d`.
2. **Three new email addresses** the legal docs introduce: `privacy@qaren.app` (Privacy § 12), `legal@qaren.app` (Terms § 14), `support@qaren.app` (already-in-use). Ahmed's A7 ask now covers all three.
3. ~~Arabic mirror of all 4 HTML pages.~~ **RESOLVED 2026-05-23** — AR mirror landed at `landing/ar/{index,privacy,terms,support}.html` with full RTL layout + Cairo-only font stack (Inter dropped — uses Cairo as the sole sans-serif for AR; Latin fragments like `Qaren` + `support@qaren.app` rendered in Cairo's Latin glyphs). Route choice: `/ar/*` sibling-directory pattern over `Accept-Language` sniffing — user-controlled, crawler-friendly URLs, matches mobile app's manual-locale-switch behavior. Each EN page now has `<link rel="alternate" hreflang="ar">` + footer `العربية` switch; each AR page has the reverse. nginx `location = /ar/support` mirrors the EN clean-URL rule. AASA + assetlinks.json stay locale-agnostic (shared from `/.well-known/`). AR translation notes: tagline "قارن بذكاء" (Compare Smart), H1 "قرارات منتجات أذكى لدول الخليج" (smarter product decisions for the GCC); referral § 12 mirrors backend `a23ed51` policy exactly ("3 دعوات ناجحة لكل جهاز" + "7 أيام"). When Ahmed lands Claude-Design fonts (Arabic font choice may differ from Cairo), reconcile the AR font stack then.
4. **Favicon** — Expo placeholder (no Qaren brand). Same A5 dependency as the asset audit.
5. **Open Graph image** — not yet shipped. `<meta property="og:image">` missing in `index.html`. Quick win for Phase 2 polish.

## Why these files are committed in `landing/` not deployed yet

- Railway service creation is interactive (Ahmed runs `railway link` or `railway init` in a real terminal).
- DNS cutover is Phase 2 work, blocked on A4 + A7 (mailbox forwarding).
- Pre-committing the static + Docker files lets Ahmed `railway up` and immediately get a working preview URL for R24 verify-before-flip.

## Migration history (audit trail)

- 2026-05-23 — Original draft used Vercel (`vercel.json` + `landing/` static dir).
- 2026-05-23 — Ahmed A6 decision: switch to Railway for vendor consolidation.
- Refit (this commit): added `Dockerfile`, `nginx.conf.template`, `railway.toml`; moved `vercel.json` → `docs/runbooks/bundle-d-landing-templates/vercel.json.alternative` (don't delete — useful reference if we ever migrate back).

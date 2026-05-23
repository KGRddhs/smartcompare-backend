# Bundle D — DNS + Landing Page Hosting Plan

**Status:** DRAFT (Phase 1, Task 1.N.6 — no DNS change yet; lands in Phase 2 with hosting setup)
**Owner:** native-ops
**Risk:** R24 (DNS propagation delay)
**Date drafted:** 2026-05-23

## Goal

Stand up `qaren.app` to serve:
1. Landing page (`https://qaren.app/`) — "Qaren — Coming soon to App Store / Google Play" placeholder
2. Privacy policy (`https://qaren.app/privacy.html`) — markdown render of post-C15 rebranded `app/legal/privacy_policy.md`
3. Terms of service (`https://qaren.app/terms.html`) — markdown render of post-C15 rebranded `app/legal/terms_of_service.md`
4. Support (`https://qaren.app/support`) — 301 redirect to `mailto:support@qaren.app`
5. Universal links AASA file (`https://qaren.app/.well-known/apple-app-site-association`)
6. Android App Links assetlinks (`https://qaren.app/.well-known/assetlinks.json`)
7. Optional: `https://www.qaren.app/*` → 301 to apex

## Hosting recommendation: Vercel

**Why Vercel over alternatives:**
- Free Hobby tier covers static landing-page traffic comfortably (100 GB/mo bandwidth)
- Auto-HTTPS via Let's Encrypt + automatic renewal — matches the SPKI rotation cadence the certificate-pinning code expects
- Automatic global edge cache (good for Bahrain/GCC TTFB)
- Native support for `/.well-known/*` static files served with correct `Content-Type: application/json`
- Zero-config deploys via `vercel.json` or just `public/` folder
- Preview deployments per branch — lets us verify pages on `bundle-d-landing.vercel.app` BEFORE flipping DNS (R24 prerequisite)

**Alternatives considered, not picked:**
- **Cloudflare Pages** — would be next choice if Vercel hit pricing wall; same edge-cache profile, but adds a second control plane (DNS is in Cloudflare already if Ahmed chose it as registrar/DNS host)
- **GitHub Pages** — free but no `/.well-known/*` MIME-type control, slower TTFB from GCC, harder to add response headers
- **Netlify** — equivalent to Vercel; Vercel chosen for marginally simpler `vercel.json` for AASA Content-Type

**Decision needed from Ahmed (NOT BLOCKING Phase 1):** Vercel free Hobby account vs. Cloudflare Pages. Default: Vercel unless Ahmed prefers Cloudflare for single-vendor consolidation.

## DNS records (target state at cutover)

Assuming current DNS host is Cloudflare (verify with `dig NS qaren.app` before Phase 2):

| Record | Name | Value | TTL | Proxy |
|---|---|---|---|---|
| A | `qaren.app` | `76.76.21.21` (Vercel apex) | **300s** | DNS-only (gray cloud) |
| AAAA | `qaren.app` | `2606:4700:4400::1111:7714` (Vercel apex v6) | **300s** | DNS-only |
| CNAME | `www.qaren.app` | `cname.vercel-dns.com` | **300s** | DNS-only |

**Why DNS-only (not proxied):** Cloudflare proxy would terminate TLS at Cloudflare's edge, breaking Vercel's automatic Let's Encrypt provisioning. If Ahmed wants Cloudflare's DDoS protection, switch to Cloudflare Pages instead of Vercel + proxied mode.

**TTL discipline (R24):** Cut TTL to 300s 24h BEFORE the actual DNS flip. Once flip is stable (24-48h, all testers + Ahmed report green), raise TTL back to 3600s for stability. Low TTL during cutover = fast revert window if AASA serves wrong Team ID / Bundle ID.

## Universal links — `apple-app-site-association` (AASA)

**Location served:** `https://qaren.app/.well-known/apple-app-site-association`
**Content-Type:** `application/json` (Vercel auto-handles via `vercel.json` headers block — see below)
**NO `.json` extension** on the file (Apple specifically looks for the extensionless path)

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["<APPLE_TEAM_ID>.com.qaren.app"],
        "components": [
          { "/": "/r/*", "comment": "referral invite codes" },
          { "/": "/c/*", "comment": "shared comparison links" },
          { "/": "/q/*", "comment": "quick query deep links" }
        ]
      }
    ]
  }
}
```

**Blocked on Ahmed (A2):** Apple Developer Team ID is the 10-character prefix in `appIDs`. Format: `ABC1234DEF.com.qaren.app`. Will be substituted in once Ahmed shares Team ID.

**Validation after Phase 2 cutover:**
```bash
curl -i https://qaren.app/.well-known/apple-app-site-association
# Expect: HTTP/2 200, Content-Type: application/json, body is the JSON above
# Apple CDN cache: https://app-site-association.cdn-apple.com/a/v1/qaren.app
```

## Android App Links — `assetlinks.json`

**Location served:** `https://qaren.app/.well-known/assetlinks.json`
**Content-Type:** `application/json`

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.qaren.app",
      "sha256_cert_fingerprints": ["<ANDROID_SIGNING_CERT_SHA256>"]
    }
  }
]
```

**Blocked on EAS build:** Android signing cert SHA-256 fingerprint comes from `eas credentials` output (only available after the first EAS Android build OR `eas credentials -p android --profile production --keystore-info`). Will pull this in Phase 2 after Task 2.N.1 EAS preview build (Ahmed-run).

## `vercel.json` snippet (Phase 2)

```json
{
  "headers": [
    {
      "source": "/.well-known/apple-app-site-association",
      "headers": [
        { "key": "Content-Type", "value": "application/json" }
      ]
    },
    {
      "source": "/.well-known/assetlinks.json",
      "headers": [
        { "key": "Content-Type", "value": "application/json" }
      ]
    },
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ],
  "redirects": [
    { "source": "/support", "destination": "mailto:support@qaren.app", "permanent": true }
  ]
}
```

## Phase 2 step-by-step (Task 2.N.2)

1. Ahmed creates Vercel project linked to `kersher2/smartcompare` or a new `qaren-landing` repo. (Or I can prep a minimal `landing/` directory inside this repo if Ahmed prefers monorepo.)
2. Native-ops authors `public/index.html`, `public/privacy.html`, `public/terms.html`, `public/.well-known/apple-app-site-association`, `public/.well-known/assetlinks.json`, `vercel.json`.
3. Privacy + Terms content sourced from **post-C15-rebrand** `app/legal/privacy_policy.md` + `app/legal/terms_of_service.md` (currently still SmartCompare-branded — DO NOT publish until Task 1.B.7 rebrand merges).
4. Deploy to Vercel preview URL (e.g. `qaren-landing-git-bundle-d.vercel.app`).
5. **Verify via direct Vercel hostname BEFORE DNS flip** (R24):
   ```bash
   curl -i https://qaren-landing.vercel.app/
   curl -i https://qaren-landing.vercel.app/privacy.html
   curl -i https://qaren-landing.vercel.app/.well-known/apple-app-site-association
   ```
   All return 200, AASA returns valid JSON with correct Team ID.
6. 24h before flip: drop existing `qaren.app` DNS records to TTL 300s.
7. Flip DNS: A/AAAA → Vercel IPs, CNAME `www` → Vercel, all TTL 300s.
8. Wait for propagation (typically 5-15 min globally with 300s TTL):
   ```bash
   dig +short qaren.app @8.8.8.8
   dig +short qaren.app @1.1.1.1
   ```
   Both return the new Vercel IPs.
9. Validate Apple's CDN picked up the new AASA (Apple caches aggressively; may take 24h):
   ```bash
   curl -i https://app-site-association.cdn-apple.com/a/v1/qaren.app
   ```
10. Once stable for 48h, raise TTLs back to 3600s.

## Rollback recipe (R24)

- DNS broken / wrong AASA published: revert `qaren.app` A/AAAA records to prior values (TTL 300s honors quickly). Landing page falls back to whatever was there before (or 404 — acceptable; testers don't depend on landing page for app functionality).
- AASA mismatched Team ID after Apple CDN cache populated: bump the AASA file content (Apple re-fetches on cache miss after ~24h), OR if urgent, ask Apple Developer Support to force-refresh.
- Vercel project deleted / unreachable: re-deploy from repo; same domain config; Vercel re-issues LE cert automatically.

## Open questions for Ahmed (NOT BLOCKING Phase 1)

- (Q1) Vercel vs Cloudflare Pages? Default: Vercel.
- (Q2) Where does `qaren.app` DNS currently live? `dig NS qaren.app` will answer; flag if it's at a registrar Ahmed wants to migrate.
- (Q3) Does `support@qaren.app` mailbox already exist? If not, the `/support` 301 lands users on a mailto that doesn't deliver. Quick fix: forward `support@qaren.app` → `ahmeddeniro2100@gmail.com` at the email host (most registrars include free forwards).
- (Q4) Should privacy + terms pages render markdown→HTML at build-time (e.g. via `marked`) OR be hand-converted to HTML once? Recommendation: hand-converted once for v1; markdown→HTML pipeline overkill for two static pages.

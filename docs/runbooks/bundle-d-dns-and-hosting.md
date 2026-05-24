# Bundle D — DNS + Landing Page Hosting Plan

**Status:** READY (Phase 2, Task 2.N.2 — refit for Railway per dispatcher A6 decision 2026-05-23)
**Owner:** native-ops
**Risk:** R24 (DNS propagation delay)
**Date drafted:** 2026-05-23 (Vercel) → 2026-05-23 refit (Railway)

## Goal

Stand up `qaren.app` to serve:
1. Landing page (`https://qaren.app/`) — "Qaren — Coming soon to App Store / Google Play" placeholder with "Compare Smart" tagline
2. Privacy policy (`https://qaren.app/privacy.html`) — HTML render of post-`eeaea11`-rebrand + post-`a23ed51`-policy-fix `app/legal/privacy_policy.md`
3. Terms of service (`https://qaren.app/terms.html`) — HTML render of `app/legal/terms_of_service.md`
4. Support (`https://qaren.app/support`) — nginx `try_files` resolves to `support.html` which combines meta-refresh-to-mailto + visible CTA button (HTTP redirect to `mailto:` scheme is broken cross-browser — Firefox rejects, Chrome/Safari inconsistent)
5. Universal links AASA file (`https://qaren.app/.well-known/apple-app-site-association`)
6. Android App Links assetlinks (`https://qaren.app/.well-known/assetlinks.json`)
7. Optional: `https://www.qaren.app/*` → 301 to apex
8. Health check (`https://qaren.app/healthz`) → `200 ok` for Railway monitoring

## Hosting: Railway (dispatcher A6 decision 2026-05-23)

Ahmed picked Railway for single-vendor consolidation with the existing FastAPI backend service (`web-production-58776.up.railway.app`). The landing/ directory deploys as a **separate Railway service** (different Dockerfile, different entrypoint, different domain) inside the same Railway project.

**Implementation:**
- `landing/Dockerfile` — `nginx:1.27-alpine` base, COPY static files to `/usr/share/nginx/html`, COPY `nginx.conf.template` to `/etc/nginx/templates/default.conf.template`
- `landing/nginx.conf.template` — envsubst-rendered at boot. Binds to `${PORT}` (Railway-assigned). Sets `application/json` Content-Type for `/.well-known/*`. Adds 5 security headers (HSTS, X-Content-Type-Options, X-Frame-Options:DENY, Referrer-Policy, Permissions-Policy disabling camera/mic/geo). nginx `try_files` resolves `/support` → `/support.html` for the cleanURL behavior we wanted from Vercel's `cleanUrls`.
- `landing/railway.toml` — `[build] builder = "DOCKERFILE"`, `[deploy] healthcheckPath = "/healthz"`, restart policy `ON_FAILURE`

**Why Railway over the prior Vercel plan:**
- Single-vendor: backend already runs on Railway under the existing Qaren project. One billing entity, one auth, one monitoring surface.
- Custom domain support: Railway issues Let's Encrypt certs automatically when a custom domain is added via the dashboard.
- Dockerfile-driven: full nginx config control (notably for `.well-known/*` MIME types — Apple's AASA validator is strict).

**Archive of the Vercel plan:** `docs/runbooks/bundle-d-landing-templates/vercel.json.alternative` retains the original headers config. Useful as a fallback if Railway ever fails for the landing-page workload.

## DNS records (target state at cutover)

`qaren.app`'s current DNS host: verify with `dig NS qaren.app` before Phase 2.

| Record | Name | Value | TTL | Notes |
|---|---|---|---|---|
| CNAME (or ALIAS / flattened CNAME at apex) | `qaren.app` | `<railway-service>.up.railway.app` (Railway will surface the exact target in the dashboard's Custom Domains section) | **300s** | RFC 1034 disallows CNAME at apex — use ALIAS/CNAME-flattening if the DNS host supports it (Cloudflare ALIAS, Route 53 ALIAS, DNSimple ALIAS). Cloudflare auto-flattens. |
| CNAME | `www.qaren.app` | `<railway-service>.up.railway.app` | **300s** | Standard CNAME (subdomain, no apex restriction). |

**TTL discipline (R24):** Cut TTL to 300s 24h BEFORE the actual DNS flip. Once flip is stable (24-48h, all testers + Ahmed report green), raise TTL back to 3600s for stability. Low TTL during cutover = fast revert window if AASA serves wrong Team ID / Bundle ID.

**Why DNS-only (not Cloudflare-proxied):** Cloudflare proxy would terminate TLS at Cloudflare's edge, breaking Railway's automatic Let's Encrypt provisioning for the custom domain. If Ahmed later wants Cloudflare DDoS protection, switch to Cloudflare Pages or run Railway behind a Cloudflare Worker proxy — but for v1 stay DNS-only.

## Universal links — `apple-app-site-association` (AASA)

**Location served:** `https://qaren.app/.well-known/apple-app-site-association`
**Content-Type:** `application/json` (nginx `nginx.conf.template` sets it via `default_type application/json` inside `location = /.well-known/apple-app-site-association {}`)
**NO `.json` extension** on the file (Apple specifically looks for the extensionless path)

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["8K562M549D.com.qaren.app"],
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

**A2 RESOLVED 2026-05-23:** Apple Developer Team ID is `8K562M549D` (provided by Ahmed via dispatcher session). The 10-character alphanumeric prefix in `appIDs` is now substituted in the snippet above and in the deploy-ready template at `docs/runbooks/bundle-d-landing-templates/apple-app-site-association.json` (and in the actual served file at `landing/.well-known/apple-app-site-association`).

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

## nginx config (lives at `landing/nginx.conf.template`)

See `landing/nginx.conf.template` for the actual file. Key choices:

- `listen ${PORT};` — Railway assigns the listening port dynamically via the `$PORT` env var; nginx:alpine's docker-entrypoint runs envsubst on `/etc/nginx/templates/*.conf.template` to render real config at boot.
- `location = /.well-known/apple-app-site-association` + `location = /.well-known/assetlinks.json` — explicit `default_type application/json` for these two paths (Apple's AASA validator rejects `application/octet-stream`).
- `location = /support` → `try_files /support.html =404` — clean URL behavior matching the Vercel `cleanUrls: true` approach we had before.
- 5 security headers via `add_header ... always` directives at server scope.
- `/healthz` returns `200 ok\n` for Railway's healthchecks per `railway.toml`.
- `log_not_found off` for `/favicon.png` to keep the access logs from filling with noise until A5 (icon decision) resolves.

## Phase 2 step-by-step (Task 2.N.2 — Railway)

1. **Pre-flight local Docker smoke** (optional but recommended):
   ```bash
   cd landing/
   docker build -t qaren-landing:dev .
   docker run --rm -p 8080:8080 -e PORT=8080 qaren-landing:dev
   # Another terminal:
   curl -sI http://localhost:8080/.well-known/apple-app-site-association | grep -i content-type
   # Expect: content-type: application/json
   ```
2. **Service creation (Ahmed in real terminal):**
   ```bash
   cd landing/
   railway login                                # cached in %USERPROFILE%\.railway
   railway link                                 # to existing Qaren project — OR:
   railway init                                 # create a new "qaren-landing" service inside the project
   ```
3. **Deploy:**
   ```bash
   railway up
   # Returns deployment URL like https://qaren-landing-production.up.railway.app
   ```
4. **Verify via Railway preview URL BEFORE DNS flip** (R24 verify-before-flip):
   ```bash
   PREV="https://qaren-landing-production.up.railway.app"
   curl -sI "$PREV/" | head -3                                                       # Expect 200 text/html
   curl -sI "$PREV/healthz" | head -3                                                # Expect 200 text/plain "ok"
   curl -sI "$PREV/privacy.html"                                                     # Expect 200
   curl -sI "$PREV/terms.html"                                                       # Expect 200
   curl -sI "$PREV/.well-known/apple-app-site-association" | grep -i content-type    # Expect application/json
   curl -s  "$PREV/.well-known/apple-app-site-association" | python -m json.tool     # Expect appID 8K562M549D.com.qaren.app
   curl -sI "$PREV/.well-known/assetlinks.json" | grep -i content-type               # Expect application/json
   curl -sI "$PREV/support" "$PREV/support.html"                                     # Expect both 200 text/html
   curl -sI "$PREV/" | grep -iE 'strict-transport|x-frame|x-content|referrer|permissions'  # Expect 5 headers
   ```
5. **24h before flip:** drop existing `qaren.app` DNS records to TTL 300s.
6. **Add custom domain in Railway dashboard:** Service → Settings → Domains → add `qaren.app` (and optionally `www.qaren.app`). Railway will show the CNAME target. Let's Encrypt cert auto-issues after DNS resolves (~5-10 min).
7. **Flip DNS:** CNAME (or ALIAS) to Railway target, TTL 300s. Optional `www.qaren.app` CNAME → Railway target.
8. **Wait for propagation** (typically 5-15 min globally with 300s TTL):
   ```bash
   dig +short qaren.app @8.8.8.8
   dig +short qaren.app @1.1.1.1
   ```
   Both return the Railway CNAME target.
9. **Validate at apex:**
   ```bash
   curl -i https://qaren.app/.well-known/apple-app-site-association
   ```
   Expect 200 + `Content-Type: application/json` + body with appID `8K562M549D.com.qaren.app`.
10. **Validate Apple's CDN** picked up the new AASA (Apple caches aggressively; may take 24h):
    ```bash
    curl -i https://app-site-association.cdn-apple.com/a/v1/qaren.app
    ```
11. **Once stable for 48h,** raise TTLs back to 3600s.

## Rollback recipe (R24)

- **DNS broken / wrong AASA published:** revert `qaren.app` DNS records to prior values (TTL 300s honors quickly). Landing page falls back to whatever was there before (or 404 — acceptable; testers don't depend on landing page for app functionality).
- **AASA mismatched Team ID after Apple CDN cache populated:** bump the AASA file content + redeploy (Apple re-fetches on cache miss after ~24h), OR if urgent, ask Apple Developer Support to force-refresh.
- **Railway service deleted / unreachable:** Railway keeps deployment history → roll back to last good deployment via dashboard. Re-deploy from repo if needed; same domain config; Railway re-issues LE cert automatically.
- **nginx config bad / 500s:** Railway healthcheck on `/healthz` flags the bad deploy; Railway auto-rolls back per `restartPolicyMaxRetries = 3`. Worst-case, push a known-good Dockerfile + nginx config from this repo's main branch and redeploy.

## Open questions for Ahmed (NOT BLOCKING Phase 1)

- ☑ ~~(Q1) Vercel vs Cloudflare Pages?~~ **A6 RESOLVED 2026-05-23: Railway.**
- (Q2) Where does `qaren.app` DNS currently live? `dig NS qaren.app` will answer; flag if it's at a registrar Ahmed wants to migrate.
- (Q3) `support@qaren.app` + `privacy@qaren.app` + `legal@qaren.app` mailbox forwarding (A7) — does Ahmed want all three forwarding to his personal Gmail, OR routing through a help-desk SaaS? If forwarding, the registrar's free email-forwarding is the simplest path.
- (Q4) Should privacy + terms pages render markdown→HTML at build-time (e.g. via `marked`) OR be hand-converted to HTML once? **Resolved**: hand-converted to `landing/privacy.html` + `landing/terms.html` in commit `d9a4d2f` + `6bbe14d`. Markdown→HTML pipeline overkill for two static pages.

---

## R24 verify-before-flip deep-dive

This section deepens the Phase 2 step-by-step above with explicit "verify via direct hostname FIRST, then DNS cutover with TTL 300s" discipline that R24 wants. Every step has a verification gate that must pass before proceeding.

### Step 0 — `railway up` deploys the landing service

Ahmed runs from a real terminal (interactive Railway auth):

```bash
cd C:\Users\SynAckITPC\Documents\ai\smartcompare-bundle-d\landing
railway login                                # opens browser; auth cached in %USERPROFILE%\.railway
railway link                                 # link to existing Qaren project (Ahmed already has Railway project for FastAPI backend)
                                             # OR: railway init (if Ahmed wants a separate project — recommend SAME project, different service)
railway up                                   # builds Dockerfile, pushes image, deploys, returns service URL
```

Railway returns a deployment URL like `https://qaren-landing-production.up.railway.app` (exact subdomain depends on Ahmed's project/service naming).

**Verification gate 0:** Railway dashboard:
- New service in the Qaren project, separate from FastAPI backend (web-production-58776.up.railway.app)
- Service deployment status = "ACTIVE"
- Healthcheck on `/healthz` passing (per `landing/railway.toml`)
- If `/healthz` failing: check build logs → most likely cause is nginx envsubst error on `${PORT}`. Fix: confirm `landing/Dockerfile` `ENV PORT=8080` + `EXPOSE 8080` lines present.

### Step 1 — curl direct against the railway.app URL (BEFORE any DNS change)

```bash
PREV="https://qaren-landing-production.up.railway.app"   # replace with actual URL from Step 0

# Test 1: landing page
curl -sI "$PREV/" | head -5                                                       # HTTP/2 200, text/html

# Test 2: healthcheck
curl -sI "$PREV/healthz" ; curl -s "$PREV/healthz"                                # 200 + "ok\n"

# Test 3: EN privacy + terms
curl -sI "$PREV/privacy.html" ; curl -sI "$PREV/terms.html"                       # both 200 text/html

# Test 4: support clean URL
curl -sI "$PREV/support" ; curl -sI "$PREV/support.html"                          # both 200 text/html

# Test 5: AASA — Apple-validator-mandatory content-type
curl -sI "$PREV/.well-known/apple-app-site-association" | grep -i content-type    # application/json
curl -s  "$PREV/.well-known/apple-app-site-association" | python -m json.tool     # valid JSON, appID 8K562M549D.com.qaren.app

# Test 6: Android assetlinks
curl -sI "$PREV/.well-known/assetlinks.json" | grep -i content-type               # application/json
curl -s  "$PREV/.well-known/assetlinks.json" | python -m json.tool                # valid JSON; cert SHA-256 still placeholder pre-Task-2.N.1

# Test 7: AR mirror routes
for p in /ar/ /ar/privacy.html /ar/terms.html /ar/support; do
  curl -sI "$PREV$p" -o /dev/null -w "$p → %{http_code}\n"
done                                                                              # all 200

# Test 8: security headers on HTML responses
curl -sI "$PREV/" | grep -iE 'strict-transport|x-frame|x-content|referrer|permissions'
# Expect 5 headers (HSTS, X-Frame-Options:DENY, X-Content-Type-Options:nosniff,
# Referrer-Policy:strict-origin-when-cross-origin, Permissions-Policy disabling
# camera/mic/geo). NOTE: per QA's nginx add_header inheritance note (Phase 3
# polish, not blocking), these headers are NOT present on /.well-known/* paths
# because the inner location blocks have their own add_header directives that
# replace (not merge) server-scope ones. Acceptable since AASA/assetlinks are
# consumed by OS validators, not browsers.
```

**Verification gate 1 (R24 critical):** ALL 8 tests must pass against the direct railway.app URL BEFORE any DNS change. Fix any failures in Dockerfile/nginx.conf.template + `railway up` again BEFORE proceeding.

**Why this matters:** if you flip DNS first then discover a missing header or wrong Content-Type on AASA, you've polluted Apple's CDN cache (Apple aggressively caches AASA for ~24h). The verify-against-railway.app-URL-FIRST discipline catches the error before Apple ever fetches the file.

### Step 2 — Add custom domain in Railway dashboard

Only after Step 1 all-green:

- Railway dashboard → qaren-landing service → **Settings** → **Domains** → **Custom Domain** → add `qaren.app`
- Railway shows the target value to point DNS at. For apex (`qaren.app` with no subdomain), Railway typically gives a CNAME-like target — but apex CNAME has RFC 1034 issues, so actual record depends on DNS host:
  - **Cloudflare** (most common for new domains): CNAME record + Cloudflare auto-flattens to A/AAAA at edge. DNS-only (gray cloud) — proxied mode breaks Railway's Let's Encrypt provisioning.
  - **Route 53:** ALIAS record (AWS-specific apex-CNAME equivalent)
  - **DNSimple:** ALIAS record
  - **GoDaddy/Namecheap/legacy:** NO apex-CNAME support → fallback is `qaren.app` 301 redirect to `www.qaren.app` + CNAME on `www.qaren.app` to Railway target
- Also add `www.qaren.app` → CNAME → same Railway target (subdomain, no RFC issue, works on any DNS host)

### Step 3 — DNS flip with TTL 300s (R24 control)

```bash
# 24h BEFORE the flip:
# Drop existing qaren.app DNS records' TTL to 300s.
# Pre-positions the cache so the flip propagates fast.

# At T=0 (the flip):
# Add the Railway-target CNAME/ALIAS records per Step 2. TTL: 300s (5 min).
```

**Verification gate 3:** dig from multiple resolvers immediately after the flip:

```bash
dig +short qaren.app @8.8.8.8        # Google
dig +short qaren.app @1.1.1.1        # Cloudflare
dig +short qaren.app @9.9.9.9        # Quad9
dig +short www.qaren.app @8.8.8.8
```

All should return either: Railway CNAME target string, OR the flattened IPs Railway points to.

If different resolvers return stale records (pre-flip values): wait 5-10 min — TTL 300s honors quickly across the resolver fleet but isn't instantaneous globally.

### Step 4 — Let's Encrypt cert provisioning

Railway's auto-issuer fires when DNS resolves to its edge:

```bash
# Wait 5-10 min after DNS resolves globally.
curl -sI https://qaren.app/ 2>&1 | head -3
# Expect: HTTP/2 200 (cert valid, served via Let's Encrypt)
# "SSL certificate problem" → Railway hasn't completed provisioning yet. Wait + retry.

curl -vI https://qaren.app/ 2>&1 | grep -iE 'subject|issuer|expire'
# Expect: subject=qaren.app, issuer=Let's Encrypt, expire=~90 days out
```

If cert provisioning stalls >15 min:
- Railway dashboard → Settings → Domains → "Re-issue Certificate"
- If still stalls: check DNS isn't proxied through Cloudflare (gray-cloud DNS-only required). Proxied mode terminates TLS at Cloudflare, blocking Railway's cert challenge.

### Step 5 — End-to-end verification at apex

Re-run all 8 tests from Step 1 against `https://qaren.app/`:

```bash
PROD="https://qaren.app"
for path in "/" "/healthz" "/privacy.html" "/terms.html" "/support" "/support.html" "/.well-known/apple-app-site-association" "/.well-known/assetlinks.json" "/ar/" "/ar/privacy.html" "/ar/terms.html" "/ar/support"; do
  printf "%s → %s\n" "$path" "$(curl -sI "$PROD$path" -o /dev/null -w '%{http_code}')"
done
# Expect: every line ends with 200

# AASA payload + Apple-CDN cache check:
curl -i https://qaren.app/.well-known/apple-app-site-association
curl -i https://app-site-association.cdn-apple.com/a/v1/qaren.app
# Apple CDN may 404 for first 1-6 hours after the flip — populates on its own
# cycle. Universal Links still work on devices because Apple fetches AASA
# directly from qaren.app initially.
```

### Step 6 — Cloudflare proxy interaction (only if Cloudflare is in front)

If DNS host is Cloudflare AND Ahmed turns on proxy (orange cloud):

**Headers Cloudflare may strip or override:**
- **HSTS:** Cloudflare may inject its own (dashboard → SSL/TLS → Edge Certificates → "HSTS"). Our nginx HSTS becomes redundant; not harmful.
- **X-Frame-Options + X-Content-Type-Options:** Cloudflare doesn't strip.
- **Content-Type on AASA:** Cloudflare's "Auto Minify" may strip Content-Type metadata for JSON. Disable Auto Minify for the AASA path OR keep proxy OFF for `.well-known/*` via a Cloudflare Page Rule.
- **Cache TTL on AASA:** Cloudflare's default cache may serve stale AASA after we redeploy. Add Page Rule: `qaren.app/.well-known/*` → Cache Level: Bypass.

**Recommendation:** Keep Cloudflare DNS-only (gray cloud) for v1. Revisit proxied mode only if Bahrain/GCC DDoS protection becomes a priority.

### Step 7 — Stability check (24-48h)

After 24h:
- Re-run Step 5 verification
- Check Railway logs:
  ```bash
  railway logs --service qaren-landing --limit 200
  ```
- Check Apple's AASA CDN cache:
  ```bash
  curl -i https://app-site-association.cdn-apple.com/a/v1/qaren.app
  ```
  Should return 200 with our AASA JSON body by hour 24.

After 48h of stability:
- Raise DNS TTL from 300s back to 3600s (1 hour) for steady-state. Lower TTL = faster revert window but slightly higher query volume; for a static landing page the trade-off favors stability post-cutover.

### Rollback path during cutover

If ANY verification gate fails between Step 2 and Step 5:

1. Revert DNS records to pre-flip state (remove CNAME/ALIAS for `qaren.app` + `www.qaren.app`)
2. TTL 300s makes revert propagate within ~10 min globally
3. Worst case during revert window: `qaren.app` returns NXDOMAIN or stale records — landing page intermittently broken, but no app functionality affected (mobile app uses `https://web-production-58776.up.railway.app/...` for API, not `qaren.app`)
4. Universal Links from the mobile app continue working because the OS already has AASA cached on device (persists across app launches)

If verification fails AFTER Step 5 (we go live but realize AASA is wrong / page has scary copy / etc.):

1. Fix in landing/ source
2. `cd landing && railway up` (redeploys; same Domains config; no DNS change)
3. Curl-verify per Step 1 against railway.app URL → wait 5-10 min for Railway to swap traffic to new deployment
4. Re-curl against `https://qaren.app/` to confirm fix live at apex

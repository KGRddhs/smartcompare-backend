# Bundle D — CLAUDE.md + MEMORY.md native-ops seed (Phase 4 close-out prep)

**Task:** #69 — pre-draft Phase-4-close-out inserts for CLAUDE.md +
MEMORY.md so the actual edits land quickly during Phase 4 sign-off.
**Author:** native-ops
**Date drafted:** 2026-05-24
**Status:** DRAFT — not yet applied to CLAUDE.md / MEMORY.md.
Dispatcher applies during Phase 4 close-out (Bundle D merge).

**Scope boundary:** this seed covers NATIVE-OPS deltas only. Backend,
frontend, qa, test will each contribute their own deltas during Phase
4. Don't edit those areas without coordination.

**Orthogonal to existing CLAUDE.md inserts:** the dispatcher-added
"🚨 APP STORE PRODUCTION SHIP-BLOCKERS" top-section already covers
the icon-byte-identity + legal-doc-redraft ship-gates. This seed does
NOT touch that section.

---

## A. CLAUDE.md "EAS Update infrastructure" section delta

Locate the existing skill-pointer section:

```
### EAS Update infrastructure
See skill: `qaren-eas-deploy` (auto-loads when `eas update`, `eas build`,
channel names, `runtimeVersion.policy`, or `expo.version` bumps are
mentioned). Quick recall: OTA via `cd SmartCompareApp && eas update
--branch <channel> --message "..."` — free, lands on next app open.
Rebuild required for native module / app.json plugin changes.
`appVersionSource: "remote"`. Interactive Expo commands (`eas login`,
`eas build`) need a real terminal — Ahmed runs these directly.
```

Append a "Bundle D delta" paragraph immediately after:

```
**Bundle D delta (2026-05-24, native-ops):**
- **iOS Privacy Manifest** at `SmartCompareApp/app.json:21-42` —
  `ios.privacyManifests` block with `NSPrivacyTracking: false` + 4
  `NSPrivacyAccessedAPITypes` reason codes (`CA92.1` UserDefaults,
  `C617.1` FileTimestamp, `35F9.1` SystemBootTime, `E174.1` DiskSpace).
  iOS 17+ Apple submission requirement (May 2024 enforcement).
  Reconcile against Expo prebuild auto-generated
  `ios/Qaren/PrivacyInfo.xcprivacy` after first EAS preview build.
- **Apple Sign-In via Expo SDK 54 plugin auto-inject** —
  `expo-apple-authentication` plugin at `app.json:86` +
  `ios.usesAppleSignIn: true` at `app.json:19`. Plugin auto-injects
  `com.apple.developer.applesignin: ["Default"]` entitlement at EAS
  prebuild. NO manual `ios.entitlements` block needed. Service ID
  `app.qaren.signin`, Key ID `7S9CT35UX7`, Team ID `8K562M549D` —
  see MEMORY.md for the full Apple chain.
- **Sentry sourcemap upload enabled** (commit `43cca75`) — `eas env`
  secret `SENTRY_AUTH_TOKEN` set for `production` + `preview`
  environments. Plugin defaults to upload-enabled (no
  `disableAutoUpload: true` in app.json). Crash reports resolve to
  original TS/TSX source lines instead of minified Hermes bundle
  line numbers.
- **expo-notifications plugin** at `app.json:88-92` with
  `color: "#10B981"` (Qaren brand emerald). Auto-adds Android
  `POST_NOTIFICATIONS` at prebuild.
- **Bundle ID:** `com.qaren.app` (ios + android). Locked. Claimed in
  ASC under Team ID `8K562M549D`.
- **Universal Links + App Links:**
  `ios.associatedDomains: ["applinks:qaren.app"]` at `app.json:20`;
  Android intent filters for `qaren.app/r/*`, `/c/*`, `/q/*` at
  `app.json:30-46`. AASA + assetlinks.json served from
  `landing/.well-known/` (Railway-hosted post-Phase-2 cutover).
- **Landing page Railway-hosted** at `qaren.app` (post Phase 2
  cutover). nginx:alpine via Dockerfile. AR mirror at `/ar/*`.
  See `docs/runbooks/bundle-d-dns-and-hosting.md` for full deploy +
  R24 cutover procedure.
```

---

## B. CLAUDE.md "Detailed Context" index — new runbook references

Locate the existing index section near the bottom:

```
## Detailed Context
Index: `docs/CLAUDE_CODE_CONTEXT.md`. Key files: `CONTEXT_ARCHITECTURE.md`,
`CONTEXT_SESSION_LOG.md`, `CONTEXT_REFERENCE.md`.
```

Append:

```
### Bundle D runbooks (native-ops)
- `docs/runbooks/bundle-d-dns-and-hosting.md` — DNS plan + Railway
  deploy + R24 verify-before-flip deep-dive (apex-CNAME RFC 1034
  caveats, Cloudflare proxy interaction, Let's Encrypt provisioning,
  rollback path)
- `docs/runbooks/bundle-d-screenshot-capture.md` — App Store screenshot
  capture procedure for Ahmed (6.7" iPhone + iPad Pro 12.9", 6
  recommended scenes, xcrun simctl cheat sheet)
- `docs/runbooks/bundle-d-testflight-internal-invite.md` — ASC
  TestFlight internal-tester invite click-path + cold-start smoke
  checklist + Sentry crash triage (post Phase 3 EAS production build)
- `docs/runbooks/bundle-d-asset-audit-2026-05-23.md` — early asset
  audit that flagged the Expo-placeholder byte-identity issue
  (resolved as v1.2 followup per
  `docs/plans/bundle-d-followups.md`)
- `docs/runbooks/bundle-d-landing-templates/` — AASA template +
  assetlinks template + vercel.json.alternative (pre-Railway-pivot
  reference)

### Bundle D plans (native-ops)
- `docs/plans/bundle-d-asc-submission-checklist.md` — ASC metadata
  drafts (App Name, Subtitle, Description, Keywords, Privacy/Support
  URLs, Categories, Age Rating, screenshots) + 6 Ahmed decision
  items D6-D11
- `docs/plans/bundle-d-asc-privacy-nutrition-labels-draft.md` — App
  Privacy Nutrition Labels draft (10 collected types + 9 not-collected
  + 5 D1-D5 decision items, all Tracking=N per Apple's narrow
  definition)
- `docs/plans/bundle-d-followups.md` — v1.2 deferrals (App Store
  production icon regeneration; A.8.2 dimension provenance unification)
```

---

## C. MEMORY.md ops-section entries

Locate the existing "## Auth System Notes" / "## Database" / "## Deploy"
ops sections. Append a new "## Bundle D ops state (2026-05-24)" section:

```
## Bundle D ops state (2026-05-24)

### Apple Sign-In chain (R4 + R5 + R14 all ADDRESSED)
- **Team ID:** `8K562M549D`
- **Bundle ID:** `com.qaren.app` (locked, claimed in ASC)
- **Service ID:** `app.qaren.signin` (web-flow optional for native
  id_token, but configured per R4 backend curl gradient evidence)
- **Key Name:** "Qaren Sign in with Apple Key"
- **Key ID:** `7S9CT35UX7`
- **.p8:** on Ahmed's disk + Supabase Auth dashboard. NEVER in repo.
- **Supabase provider:** ENABLED 2026-05-23 (A8 dispatcher session).
  Client IDs field: `app.qaren.signin,com.qaren.app` (comma-separated
  dual audience). Secret Key field: blank (web OAuth not needed for
  native id_token flow). "Allow users without email": ON.
- **Backend curl validation:** R4 closure cite — `apple` HTTP 401
  parity with `google` HTTP 401 (request_id pair documented in
  ledger).
- **Frontend wiring:** `expo-apple-authentication` plugin at
  `app.json:86` + `ios.usesAppleSignIn: true` at `app.json:19`.
  Expo SDK 54 plugin auto-injects entitlement at EAS prebuild
  (verifiable post-build via `find ios -name "*.entitlements"`).

### Sentry sourcemap upload (A4 ADDRESSED)
- **EAS env secret:** `SENTRY_AUTH_TOKEN` (visibility=secret,
  type=string) set for `production` + `preview` environments via
  `eas env:create --environment <env>`
- **Auth Token scopes:** `project:read`, `project:write`,
  `project:releases`
- **Sentry org/project:** `qaren-rr/react-native`
- **Plugin config:** `@sentry/react-native` at `app.json:122-129`
  with `url: "https://de.sentry.io/"`, `organization: "qaren-rr"`,
  `project: "react-native"`. NO `disableAutoUpload: true` flag —
  upload-enabled by default at prebuild.
- **eas.json:** `build.preview.env` empty (no disable flags),
  `build.production.env` not declared (implicit injection from the
  EAS secret).
- **Impact:** mobile crash stack traces resolve to original TS/TSX
  source lines instead of minified Hermes bundle line numbers.
  Diagnostic-quality dramatically improves for TestFlight tester
  crash triage.

### Landing page deployment (Railway, A6)
- **Service:** separate Railway service in the existing Qaren project
  (different Dockerfile, different entrypoint from FastAPI backend
  service `web-production-58776.up.railway.app`)
- **Build:** `nginx:1.27-alpine` via `landing/Dockerfile`
- **Config:** `landing/nginx.conf.template` envsubst-renders
  `${PORT}` at boot
- **Custom domain:** `qaren.app` apex + `www.qaren.app` subdomain
- **DNS:** CNAME / ALIAS to Railway-target. TTL 300s during cutover.
  Apex-CNAME RFC 1034 caveat: use Cloudflare DNS-only (gray cloud,
  auto-flattening) OR Route 53 ALIAS / DNSimple ALIAS / fallback to
  www-only-CNAME for legacy DNS hosts.
- **Cert:** Let's Encrypt auto-issued by Railway when DNS resolves
  to its edge (~5-10 min). Cloudflare proxy (orange cloud) blocks
  this — keep DNS-only.
- **Universal Links AASA:** served from
  `https://qaren.app/.well-known/apple-app-site-association` with
  `Content-Type: application/json`. appID `8K562M549D.com.qaren.app`,
  paths `/r/*` `/c/*` `/q/*`.
- **Android App Links assetlinks:** served from
  `https://qaren.app/.well-known/assetlinks.json`. SHA-256 cert
  fingerprint placeholder until Task 2.N.1 EAS preview build —
  `eas credentials -p android --profile production --keystore-info`
  extracts the production-signing cert fingerprint.
- **AR locale mirror:** `https://qaren.app/ar/*` for all 4 pages
  (index, privacy, terms, support). RTL + Cairo-only font stack.
- **Mailbox addresses needed (A7):** `support@qaren.app`,
  `privacy@qaren.app`, `legal@qaren.app` — all 3 referenced in
  legal docs + footer; Ahmed sets up forwarding via registrar's
  free email-forward OR a help-desk SaaS (TBD).

### ASC App Store metadata (pending Ahmed D1-D11)
- **Listing name:** "Qaren — Compare Smart" (20 chars, em-dash
  separator; Ahmed-locked)
- **Bundle ID:** `com.qaren.app`
- **Subtitle:** 2 candidates — "Smart Compare for the GCC" (24
  chars) OR "Compare products instantly" (26 chars). Ahmed D6.
- **Description draft + Keywords draft + Promotional Text draft:**
  see `docs/plans/bundle-d-asc-submission-checklist.md`
- **Privacy Nutrition Labels draft:** see
  `docs/plans/bundle-d-asc-privacy-nutrition-labels-draft.md`. 10
  collected data types + 9 not-collected, all Tracking=N (no
  third-party ad SDKs, no IDFA access). Awaits Ahmed D1-D5
  sign-off.
- **Privacy URL:** `https://qaren.app/privacy.html` post-Phase-2
  cutover; Railway endpoint fallback during interim.
- **Support URL:** `https://qaren.app/support` post-cutover; mailto
  fallback.
- **App Store production submission blockers:** icon byte-identity
  (v1.2 followup) + legal-doc redraft (separate Ahmed-facing legal
  decisions bundle). TestFlight internal proceeds with current state.
```

---

## D. Application protocol for Phase 4 close-out

When dispatcher (or future native-ops session) lands this seed:

1. Apply Section A by inserting the "Bundle D delta" paragraph into
   CLAUDE.md right after the existing "EAS Update infrastructure"
   skill-pointer block.
2. Apply Section B by appending the "Bundle D runbooks" + "Bundle D
   plans" subsections to CLAUDE.md's "## Detailed Context" section.
3. Apply Section C by inserting the "## Bundle D ops state
   (2026-05-24)" section into MEMORY.md after the existing "## Deploy"
   section.
4. Verify CLAUDE.md doesn't exceed the soft 320-line target — Bundle
   D adds ~30 lines net (section A ~20 + section B ~10). Currently
   CLAUDE.md is at ~340 lines per recent count. If we hit hard limits,
   the soft path is to extract A or B as a skill auto-loader pointer.
5. Verify MEMORY.md index isn't bloated — Section C adds substantive
   ops content (~80 lines) but as a single new section, not many
   one-line index entries. Acceptable.
6. Cross-reference: leave the dispatcher-added "🚨 APP STORE
   PRODUCTION SHIP-BLOCKERS" section untouched — it's orthogonal
   scope and stays at the top of CLAUDE.md.

---

## E. Reference: Bundle D native-ops commit list (for cite-checking)

For any future audit that needs to verify the citations in Sections
A-C resolve, here's the native-ops commit log on
`feature/bundle-d-testflight-readiness` as of 2026-05-24:

- `70a34b3` expo-notifications plugin block (C16)
- `03cdc1e` R5 ledger ADDRESSED (Apple-Auth plugin)
- `9008e5f` DNS+Vercel runbook (later refit to Railway)
- `1f4e380` Asset audit findings (early)
- `975f921` R6 ledger ADDRESSED (bundle ID claim confirmed)
- `fbbb078` AASA + assetlinks templates
- `5b24dee` Privacy Nutrition Labels draft
- `6121432` Apple Team ID 8K562M549D substituted in AASA
- `8101248` Privacy Nutrition Labels Row 4 correction (search_logs
  unconditional storage)
- `d9a4d2f` Vercel landing page pre-built (later refit to Railway)
- `c2aec12` Replace broken mailto-redirect with support.html
- `148d735` ASC submission checklist + metadata draft
- `6bbe14d` landing/terms.html regen from backend a23ed51
- `a8110cb` Compare Smart tagline on landing/index.html
- `10ff816` privacyManifests block in app.json (iOS 17+)
- `17b5a50` Railway refit (A6 Ahmed decision)
- `fff259a` landing/vercel.json deletion cleanup
- `f7732dd` Screenshot capture runbook
- `b2e4c7e` R13 defense-in-depth note (Privacy Manifest cite)
- `0c54d2d` AR locale mirror of landing/
- `3095304` R14 BOTH-gate ADDRESSED
- `43cca75` Sentry sourcemap upload enabled (A4)
- `2c797d9` Claude-Design logo-wordmark.png
- `8aed1ad` TestFlight internal-tester invite runbook
- `f7c3d81` R24 verify-before-flip deep-dive in DNS runbook
- `7df7b74` v1.2 followup entry for App Store icon regeneration

**R-ledger contributions by native-ops:**
- ADDRESSED: R5 (`03cdc1e`), R6 (`975f921`), R14 (`3095304`)
- PENDING (Phase 2/3 trigger-gated): R7 (EAS prod-build signing),
  R8 (ASC 30-min upload window), R13 (Privacy Nutrition Labels
  Ahmed sign-off), R24 (DNS cutover)
- Defense-in-depth note: R13 cite to Privacy Manifest `10ff816`
  (no ledger row flip)

**Other contributions (no R-row flip):**
- A4 Sentry sourcemap upload (`43cca75`) — ops quality-of-life
- Task #32 Bundle D close (`7df7b74`) — App Store regeneration
  deferred to v1.2 per Ahmed visual-approval
- Bundle ID + Team ID + Service ID + Key ID — Ahmed A3-A7 session
- A6 Railway hosting choice — Ahmed
- A8 Supabase Apple provider — Ahmed

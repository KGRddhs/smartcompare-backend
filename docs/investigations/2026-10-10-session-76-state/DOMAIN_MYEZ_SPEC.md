# DOMAIN-MYEZ -- move the product web host from qaren.app to getmyez.com (session 76)

Unit: DOMAIN-MYEZ. Branch `feature/s76-domain-getmyez` (worktree `sc-s76-domain`), cut from main
`a8f4552b`. Every line number below is at `a8f4552b` unless a PR #330 number is named.
Spec + RED author: DOMAIN-MYEZ RED agent (Opus), 2026-10-10.

## 0. Decision and scope

* OWNER DECISION (2026-10-10, binding): the product domain is **getmyez.com**; **qaren.app is retired**.
  Brand MYEZ. Identifiers stay qaren (section 1).
* ASSUMPTION, flagged and NOT decided: the mailboxes move to `support@getmyez.com` and
  `privacy@getmyez.com`. The owner has not confirmed. Every e-mail change sits behind ONE constant per
  file (section 3) so GREEN flips one line per file if the owner picks other addresses.
* The landing site stays the Railway service `qaren-landing` (name unchanged); its Railway URL
  `https://qaren-landing-production.up.railway.app` stays valid and stays in use where it is used today
  (landing/README.md smoke commands; #330's LegalScreen test uses it as the landing host).
* Measured by the orchestrator 2026-10-10: getmyez.com serves an unrelated page titled "PAUSE Fragrance
  Study" behind Cloudflare; `https://getmyez.com/.well-known/apple-app-site-association` is 404.
* IN scope: client (app.json, linking, push host boundary, Contact Us mailto, comments), landing chrome
  (9 pages outside legal regions, nginx comment, README), backend constants (share link base, admin cost
  label, crawler UA info URL), two scripts, the pins that encode the web host, the Worker's retirement note.
* OUT of scope: anything inside a legal region (PR #330), `app/legal/*.md` (PR #330 replaces them
  wholesale), the docs lane (CLAUDE.md, MEMORY.md, memory/*, docs/** except the two named living docs,
  .claude/skills/*), DNS / Railway / Cloudflare / Supabase / EAS actions (owner steps, section 7).

## 1. KEEP identifiers (stated once; never changed by this unit)

| Identifier | Where | Why it stays |
|---|---|---|
| scheme `qaren` / `qaren://` | app.json:15, :170; linking.ts:47; open.html hand-off targets | the deep-link scheme is baked into every installed binary, push payloads (`qaren://profile/referrals`) and open.html; a scheme is not a domain |
| bundle id / package `com.qaren.app` | app.json:21, :150; AASA appID `8K562M549D.com.qaren.app`; assetlinks package; authService.ts:881 diagnostic | App Store / Play identity; immutable once an app record exists; contains the retired host only as a substring |
| EAS slug `qaren`, owner `kersher2` | app.json:4 and owner | the EAS project id and update channel hang off them |
| Google `iosUrlScheme` `com.googleusercontent.apps.21336192767-...` | app.json:228 | the OAuth iOS client; holds no web host |
| Supabase recovery redirect `qaren://reset-password` | backend default of `PASSWORD_RESET_REDIRECT_URL` (auth_service) | owner decision: unchanged; it is a scheme URL, not a host |
| Railway service name `qaren-landing` | landing/Dockerfile:35, landing/README.md:3,9,57,58,69,78,83, .claude/skills/qaren-eas-deploy/SKILL.md:46 | service name unchanged by decision |
| Worker name `qaren-redirect` | cloudflare-workers/qaren-redirect/** | retired with its zone, code kept (section 6) |

Scanners strip `\bcom\.qaren\.app\b` before looking for `qaren.app`; nothing else is allowlisted by pattern.

## 2. Occurrence table (git grep -n -i -E "qaren\.app|qaren-landing|@qaren\.app", minus docs/investigations, docs/plans: 335 lines)

Decision codes: **R** = REPLACE in GREEN (replacement given), **K** = KEEP (reason), **330** = owned by
PR #330, do not touch, **DOCS** = docs lane, KEEP in this unit.

### 2.1 Client (SmartCompareApp)

| file:line | text today | decision | replacement |
|---|---|---|---|
| app.json:24 | `"associatedDomains": ["applinks:qaren.app"]` | R (native: NEW BUILD) | `["applinks:getmyez.com"]` |
| app.json:162,163,164 | `"host": "qaren.app"` (pathPrefix /r/ /c/ /q/) | R (native: NEW BUILD) | `"host": "getmyez.com"` (paths unchanged, autoVerify stays true) |
| app.json:21,150 | `com.qaren.app` | K | bundle id / package |
| src/navigation/linking.ts:47 | `prefixes: ['qaren://', 'https://qaren.app']` | R | `['qaren://', 'https://getmyez.com']` (retired host dropped, not kept as a third prefix: no binary has ever shipped, no TestFlight build exists, so no link in the wild relies on it, and keeping it would keep honouring a domain a stranger could re-register) |
| src/navigation/linking.ts:41,43 | comments `qaren.app/c/...`, `qaren.app/r/...` | R | `getmyez.com/c/...`, `getmyez.com/r/...` |
| src/services/pushNavigation.ts:86,89,90 | HOST BOUNDARY doc comment (`https://qaren.app`, `qaren.appcomparison`, `qaren.app.evil.com`) | R (comment only; the logic in `pathFromPushUrl` is host-agnostic and unchanged) | `https://getmyez.com`, `getmyez.comcomparison`, `getmyez.com.evil.com` |
| src/screens/ContactUsScreen.tsx:218 | `Linking.openURL('mailto:support@qaren.app?subject=MYEZ%20Support')` | R + one constant | add `const SUPPORT_EMAIL = 'support@getmyez.com';` (module level, above `RATE_LIMIT_MS`, with an `ASSUMPTION` comment) and use `` Linking.openURL(`mailto:${SUPPORT_EMAIL}?subject=MYEZ%20Support`) `` |
| src/screens/ReferralLandingScreen.tsx:5 | doc comment `qaren.app/c/{share_token}?ref=...` | R | `getmyez.com/c/...` |
| src/types/types.ts:639 | comment `qaren.app/r/QR-XXXXXX` | R | `getmyez.com/r/QR-XXXXXX` |
| src/services/authService.ts:881 | diagnostic naming `com.qaren.app` | K | bundle id |

No occurrence in eas.json, App.tsx, index.ts, locales/**, src/i18n/** (measured by D4).

### 2.2 Landing (outside legal regions; region rule in section 4)

| file:line | decision | replacement |
|---|---|---|
| landing/index.html:12 (og:url), 15 (canonical), 16-18 (hreflang en/ar/x-default) | R | `https://getmyez.com/`, `/ar/` as today's paths |
| landing/index.html:267 (`Questions? mailto + text`), 273 (footer Support mailto) | R (email ASSUMPTION) | `support@getmyez.com` |
| landing/ar/index.html:12, 16-19 | R | as index.html with `/ar/` canonical |
| landing/ar/index.html:264, 270 | R (email) | `support@getmyez.com` |
| landing/privacy.html:10-13 (canonical + 3 hreflang) | R | `https://getmyez.com/privacy.html`, `/ar/privacy.html` |
| landing/privacy.html:293 (footer Support mailto) | R (email) | `support@getmyez.com` |
| landing/privacy.html:285 (`privacy@qaren.app` body contact) | **330** | none here: inside #330's hunk `-285 +317,3`; #330 renders `<PLACEHOLDER:PRIVACY_EMAIL>` inside its region |
| landing/terms.html:10-13, 280 | R | `/terms.html`, `/ar/terms.html`; footer `support@getmyez.com` |
| landing/terms.html:272 (`legal@qaren.app` body contact) | **330** | none here (hunk `-272 +256,2`; #330 drops legal@, ruling C29) |
| landing/support.html:7 (meta description), 9 (meta refresh mailto), 11-14 (canonical + hreflang), 199 (CTA mailto), 204, 207 (`<code>` address) | R | host `https://getmyez.com/support`, `/ar/support`; address `support@getmyez.com` |
| landing/ar/privacy.html:10-13, 287 | R | as privacy.html |
| landing/ar/privacy.html:279 (body contact) | **330** | none (hunk `-279 +311,3`) |
| landing/ar/terms.html:10-13, 271 | R | as terms.html |
| landing/ar/terms.html:263 (body contact) | **330** | none (hunk `-263 +247,2`) |
| landing/ar/support.html:7, 9, 11-14, 198, 203, 206 | R | as support.html |
| landing/open.html:23 (two mentions in the header comment), 120 (script comment naming the linking prefixes) | R, keep exactly **3** host mentions (landing.brand.s69 ADDRESS_COUNTS `open.html: 3` must still hold with the widened regex) | line 23-24: "only once getmyez.com points at this service (on 2026-10-10 getmyez.com still served an unrelated page, so the page is reachable on the Railway host alone)"; line 120: `'https://getmyez.com'` |
| landing/nginx.conf.template:59-60 | R (comment only) | "only once getmyez.com points at this service" |
| landing/nginx.conf.template:7 `server_name _;` | K | catch-all; Railway routes by Host; no change needed for a new custom domain |
| landing/.well-known/apple-app-site-association:6 | K | appID `8K562M549D.com.qaren.app`, paths `/r/* /c/* /q/*`; NO host appears in the file (L6 pins it) |
| landing/.well-known/assetlinks.json:6 | K | package `com.qaren.app`; no host; the SHA-256 is still `ANDROID_SIGNING_CERT_SHA256_PLACEHOLDER` (pre-existing gap, not this unit) |
| landing/Dockerfile:35 | K | `qaren-landing` image tag = service name |
| landing/README.md:3,4,9,57,58,69,78,83 | K | service name / Railway URL |
| landing/README.md:99 | K | appID identifier |
| landing/README.md:6,15,37,39,108,124,125,127,128,130,131,142,143 | R | rewrite to getmyez.com; the status block (lines 3-9) says qaren.app is retired 2026-10-10 (a line that names the old host must carry the word "retired"; L4 enforces); section 6 "DNS cutover" re-targets getmyez.com (apex CNAME-flattening at Cloudflare, `dig +short getmyez.com`, AASA at `https://getmyez.com/.well-known/apple-app-site-association`, Apple CDN `https://app-site-association.cdn-apple.com/a/v1/getmyez.com`); line 142 mailboxes become the ASSUMED `privacy@getmyez.com` / `support@getmyez.com` (legal@ is dropped by #330) |

### 2.3 Backend (app/, scripts/)

| file:line | decision | replacement |
|---|---|---|
| app/services/referral_service.py:50 `APP_BASE_URL = "https://qaren.app"` | R | `"https://getmyez.com"` (no trailing slash; the builder at :348 appends `/c/...`) |
| app/api/admin_routes.py:922 `{"line": "Domain (qaren.app)", "monthly_usd": 1.5, "notes": "$18/yr"}` | R (label) | `"Domain (getmyez.com)"`; `monthly_usd` / `notes` stay until the owner gives the .com price (open question Q4) |
| app/services/sitemap_discovery_service.py:387 `_ROBOTS_UA = "%s/1.0 (+https://qaren.app/bot; contact: kingzatel@gmail.com)"` | R | `+https://getmyez.com/bot`. Read: this is NOT a scraping-domain list and NOT a sitemap exclusion of our own site; it is the info URL inside OUR crawler's named User-Agent (robots.txt reads), which "mirrors the off-clock resolver's UA". The URL must name a domain we control. `tests/test_robots_unreadable_ruling.py:312` pins only `startswith(NAMED_AGENT)`, unaffected |
| scripts/resolve_search_descriptors.py:80 `USER_AGENT` | R | same string as `_ROBOTS_UA` (T4 pins the mirror) |
| scripts/bundle_d_prod_smoke.py:18 (docstring), :177 `f"bundle-d-smoke-{timestamp}@qaren.app"` | R + one constant | `SMOKE_EMAIL_DOMAIN = "getmyez.com"` and `f"bundle-d-smoke-{timestamp}@{SMOKE_EMAIL_DOMAIN}"`. Reason: the script registers REAL Supabase users; a retired domain can be re-registered by a stranger, who would then receive the confirmation mails |
| app/legal/privacy_policy.md:93 `privacy@qaren.app` | **330** / K | the OLD draft; PR #330 replaces the file wholesale (addresses from placeholders). Left untouched here; T5 allowlists it with the reason |
| app/legal/terms_of_service.md:96 `legal@qaren.app` | **330** / K | same |

### 2.4 Cloudflare Worker (cloudflare-workers/qaren-redirect)

| file:line | decision |
|---|---|
| wrangler.toml:5,7 (comments), :10 `routes = [{ pattern = "qaren.app/r/*", zone_name = "qaren.app" }]` | R: RETIRE. Comment the `routes` entry out and add a header `# RETIRED 2026-10-10 with qaren.app -- do not deploy` so an accidental `wrangler deploy` binds no route |
| README.md:3,51,62,72 | R: add a "RETIRED 2026-10-10" banner at the top (the body stays as history; the banner names the reasons below) |
| src/index.ts:2, __tests__/index.test.ts:2,14, package.json:5 | K: code kept as-is (history; not run by CI, no node_modules) |

### 2.5 Tests that name the retired host (GREEN amends only the ones that PIN the web host)

| file:line | pins | decision |
|---|---|---|
| SmartCompareApp/__tests__/services/pushNavigation.w315.test.ts:250-262, 276, 459, 480-488 | the host boundary on the linking prefix (P4f, P9, P9b) | R: mechanical host swap to `getmyez.com` (`qaren.appcomparison` -> `getmyez.comcomparison`, etc.); semantics identical |
| SmartCompareApp/__tests__/navigation/linking.w315.test.ts:154,156 | L9b resolve + `prefixes` toEqual | R: `https://getmyez.com/c/TOK1?ref=QR-1`; `['qaren://', 'https://getmyez.com']` |
| SmartCompareApp/__tests__/linking.resetPassword.w36.test.ts:161 | `prefixes` toEqual | R: `['qaren://', 'https://getmyez.com']` |
| SmartCompareApp/__tests__/landing.brand.s69.test.ts:123,125 ONLY | "every qaren.app address survives" count | R: line 125 regex `/qaren\.app\|getmyez\.com/g` (every address survives, re-hosted); line 123 comment. Do NOT touch lines 11-12, 21-25, 43, 53-80, 88 (#330's hunks are 21-25, 43, 59-61, 64-66, 71, 73-80, 88). ADDRESS_COUNTS stay as they are on BOTH sides: main after GREEN = 7/9/7 (5 getmyez + the 2 #330-owned body addresses on the legal pages), #330 after merge = 5/9/5 (measured by simulation, section 9) |
| SmartCompareApp/__tests__/brand.hardcoded.s69.test.ts:142-146 | "the support mailto keeps its address" `toBe('mailto:support@qaren.app?subject=MYEZ%20Support')` | R: the source now builds the mailto from `SUPPORT_EMAIL`; amend to resolve the constant (assert `const SUPPORT_EMAIL = 'support@getmyez.com'` and `` mailto:${SUPPORT_EMAIL}?subject=MYEZ%20Support ``); lines 20-21 header comment re-worded (R-B / D14 "addresses stay on qaren" is superseded by the 2026-10-10 decision). ADDRESS_RE (line 37) may stay (getmyez.com carries no "Qaren") |
| SmartCompareApp/__tests__/landing.handoff.s69.test.ts:8 | header comment only | R (comment) |
| tests/test_password_reset_deep_link.py:134,141,665,666 | the knob honours an arbitrary universal-link value (host-agnostic) | R (sample value): `https://getmyez.com/reset-password`; the default `qaren://reset-password` stays (K) |
| tests/test_landing_fallback_pages_s69.py:3,9 | docstring | R (docstring) |
| SmartCompareApp/__tests__/authService.bootOptimistic.a3.test.ts:94,100 | inert fixture e-mail | K |
| SmartCompareApp/__tests__/AuthScreens.socialDiagnostic.pa8.test.tsx:92 | bundle id | K |
| SmartCompareApp/__tests__/ShareBottomSheet.deviceFingerprint.w3-3.test.tsx:73 | inert mocked API value | K |
| SmartCompareApp/__tests__/clipboardFallbackService.test.ts:57 | negative case (code embedded in text); host irrelevant | K |
| SmartCompareApp/__tests__/clientTruth/shareTruth.s74.test.tsx:10 | comment about a removed placeholder | K |
| tests/test_referral_routes.py:177,218; tests/test_referral_e2e.py:107 (prod capture comment), :126; tests/test_referral_share_privacy.py:273 | mocked `create_invite` return; assertions read only token / `?ref=` | K (inert; no assertion reads the host) |
| tests/test_profile_routes.py:29; tests/test_home_routes.py:31; tests/test_endpoint_shapes_vs_jsx.py:163; tests/test_supabase_client_reuse.py:151 | inert fake-user e-mails | K |

### 2.6 Docs and agent files (KEEP in this unit unless named)

| file:lines | decision |
|---|---|
| docs/runbooks/bundle-d-landing-templates/README.md:11, 27, 74, 79, 81 | R (living doc): paths `https://getmyez.com/.well-known/...`, Apple CDN URL, `applinks:getmyez.com` |
| docs/runbooks/bundle-d-landing-templates/README.md:16, 39, 43 | K (appID / package identifiers) |
| docs/runbooks/bundle-d-landing-templates/README.md:59, 62, 65, 68 (`qaren-landing.vercel.app`) | K (the never-deployed Vercel alternative; history) |
| docs/runbooks/bundle-d-landing-templates/apple-app-site-association.json:6, assetlinks.json:6 | K (identifiers) |
| docs/privacy-data-inventory.md | no occurrence (nothing to do) |
| docs/claude-design-handoff/ui_kits/mobile/ShareBottomSheet.jsx:132 | K (design artefact) |
| docs/runbooks/bundle-d-dns-and-hosting.md (61), docs/runbooks/2026-08-31-affiliate-signup-answers.md (11: Awin / CJ / ArabClicks "Promotional Space URL" = `https://qaren.app` at :54, :116, :179), docs/CONTEXT_SESSION_LOG.md (12), docs/superpowers/** (12), docs/SESSION_BUNDLES.md (3), docs/runbooks/bundle-d-testflight-internal-invite.md (4), bundle-d-screenshot-capture.md (2), bundle-d-ota-delivery-troubleshooting.md (2), docs/CONTEXT_ARCHITECTURE.md (2), docs/runbooks/bundle-bcd-coverage.md (1), docs/CONTEXT_REFERENCE.md (1), docs/CLAUDE_CODE_CONTEXT.md (1), docs/skills/claude-web/qaren-meta-campaign-setup-bahrain.md:17 (Instagram handle idea) | DOCS (the session docs PR re-targets the DNS runbook; the rest is history) |
| CLAUDE.md:7,19,76,188,502,511,541,548,557,561,562,565,566,607,613,681 | DOCS (lines 7,19,188 are `com.qaren.app` = K) |
| MEMORY.md:215,269,271,281; memory/BUNDLE_D_RISK_LEDGER.md:16,34,91,95,123,125,132; memory/BUNDLE_D_NATIVE_OPS_ANCHOR.md:12,13,17,21,57,58; memory/BUNDLE_D_BACKEND_ANCHOR.md:18 | DOCS |
| .claude/skills/qaren-referrals/SKILL.md:25,33,34; .claude/skills/qaren-eas-deploy/SKILL.md:46 | DOCS (46 = service name, K) |

## 3. One-constant-per-file rule for e-mail addresses (ASSUMPTION support@ / privacy@getmyez.com)

* ContactUsScreen.tsx: exactly one address literal in the file, `const SUPPORT_EMAIL = 'support@getmyez.com'`,
  marked `// ASSUMPTION (S76, owner unconfirmed)`; the mailto is built from it (D8, D9).
* scripts/bundle_d_prod_smoke.py: `SMOKE_EMAIL_DOMAIN` (a throwaway domain, not a mailbox).
* Each RED test names the mailbox once: `SUPPORT_EMAIL` in domain.s76.test.ts and in landing.domain.s76.test.ts.
* Landing HTML is static (nginx, no templating): the address is written literally on the chrome lines
  of section 2.2. A different owner choice = the test constant + one mechanical replace over exactly
  those lines (L3 lists every address outside the legal regions, so a missed one reddens).
* `privacy@getmyez.com` appears in NO file this unit owns: on main the privacy address lives only in
  #330-owned lines; #330 renders `<PLACEHOLDER:PRIVACY_EMAIL>` / `<PLACEHOLDER:SUPPORT_EMAIL>` and
  `scripts/fill_in_legal.py` fills them from the owner's answers (`tests/fixtures/legal_fill_in_u8.json`
  keys `PRIVACY_EMAIL`, `SUPPORT_EMAIL`, both null today). If the assumption holds, the owner's
  fill-in answers are `privacy@getmyez.com` and `support@getmyez.com`.

## 4. Legal-region rule (PR #330)

* Marker syntax, read on `origin/feature/s73-u8-legal` (`scripts/render_legal_landing.py:54-55`):
  `REGION_BEGIN = "<!-- legal:begin -->"`, `REGION_END = "<!-- legal:end -->"`; one region per page on
  privacy, terms, support, EN + AR. Everything outside (head, wordmark, footer, hreflang, language switch)
  is hand-written chrome.
* **This unit never edits a line between the markers, and on main (no markers yet) never edits a line
  inside a #330 hunk.** The lines it edits in the six pages (main numbers; #330 numbers after the arrow):
  * landing/privacy.html: 10, 11, 12, 13, 293 (-> #330 326)
  * landing/terms.html: 10, 11, 12, 13, 280 (-> 264)
  * landing/support.html: 7, 9, 11, 12, 13, 14, 199, 204, 207 (same numbers on #330; its region is inserted after 208)
  * landing/ar/privacy.html: 10, 11, 12, 13, 287 (-> 320)
  * landing/ar/terms.html: 10, 11, 12, 13, 271 (-> 255)
  * landing/ar/support.html: 7, 9, 11, 12, 13, 14, 198, 203, 206 (same; region after 207)
* NOT edited (owned by #330): privacy.html:285, terms.html:272, ar/privacy.html:279, ar/terms.html:263.
* #330 hunks in these pages at main numbers: privacy 106-116 and 192-288; terms 106-116 and 181-275;
  support insertion after 208; ar/privacy 100-110 and 186-282; ar/terms 100-110 and 172-266;
  ar/support insertion after 207. Nearest distance from an edited line to a #330 hunk: 5 lines
  (privacy 293 vs 288; terms 280 vs 275), 1 unchanged line (support 207 vs insertion after 208).
* landing.domain.s76.test.ts implements the rule: it skips region lines when markers exist and, on a
  marker-less tree, skips only the `mailto:privacy@` / `mailto:legal@` body line of the four legal pages.

## 5. Native consequence

* `ios.associatedDomains` is an entitlement and `android.intentFilters` are manifest entries: D1/D2 ship
  ONLY with a NEW store build (EAS build), never an OTA. UB-R4 (no OTA / store build before PR #330 is
  live) already holds every client change; this unit rides the next build with #330.
* Universal links work only once `https://getmyez.com/.well-known/apple-app-site-association` is served
  with `Content-Type: application/json`, HTTP 200 and **no redirect** (apex, no www hop). nginx already
  serves it that way (`landing/nginx.conf.template:15-20`); today the host serves another site (404).
* Apple fetches the AASA through its CDN (`https://app-site-association.cdn-apple.com/a/v1/getmyez.com`)
  at install time and caches results, a 404 included: the domain must serve the file BEFORE any build
  carrying `applinks:getmyez.com` is installed on a test device.
* Android App Links additionally need the real signing SHA-256 in `assetlinks.json` (still a
  placeholder: a pre-existing gap, not this unit).
* The JS half (linking prefix, Contact Us address) alone would be OTA-able, but it must ship WITH the
  entitlement: an OTA that drops `https://qaren.app` while a binary still claims it changes nothing
  useful, and no binary has shipped. Rule: no OTA for this unit; the next build carries all of it.
* Backend deploy changes every NEW share link to `https://getmyez.com/c/...` immediately: deploy the
  backend only after `https://getmyez.com/c/x` serves open.html (owner step 6 before step 9).

## 6. The redirect Worker: RETIRE (keep the code with a README note)

Reasons, measured: (1) its only route is `qaren.app/r/*` on the retired zone (wrangler.toml:10);
(2) re-pointed at `getmyez.com/r/*` it would intercept `/r/*` before the Railway origin and shadow the
tested open.html hand-off (landing.handoff.s69 + test_landing_fallback_pages_s69), giving `/r/` and
`/c/` two different behaviours; (3) its store targets are wrong or placeholders: `PLAY_STORE_PACKAGE =
'com.kersher2.qaren'` (src/index.ts:28) does not match `android.package` `com.qaren.app`, and
`APP_STORE_ID = 'idTBD'` (:29); (4) the backend builds `/c/` links, not `/r/` (referral_service.py:348).
The install-survival ideas (Play Install Referrer, iOS clipboard) can move into open.html later if wanted.

## 7. Owner steps (only the owner can do these; in order)

1. Decide the mailboxes (Q1) and what happens to the PAUSE Fragrance Study site now on getmyez.com (Q2).
2. Cloudflare (getmyez.com zone) -> DNS: export the current records first (the PAUSE site's apex/www
   records and any MX/TXT). Note them before deleting anything.
3. If the PAUSE site is kept, give it its own host first (for example `pause.getmyez.com`). Note: the
   landing sends `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   (nginx.conf.template:48), so every getmyez.com subdomain must serve HTTPS.
4. Railway -> project -> service `qaren-landing` -> Settings -> Networking -> Custom Domain -> add
   `getmyez.com` (optional `www.getmyez.com`, Q5). Copy the exact CNAME target (and any verification
   TXT) Railway shows.
5. Cloudflare -> DNS: replace the apex record with `CNAME @ -> <Railway target>` (Cloudflare flattens
   apex CNAMEs); same for `www` if added. Proxy status: DNS only (grey cloud) until Railway shows the
   certificate issued. If proxied later: SSL/TLS mode Full (strict), turn OFF Email Address
   Obfuscation (Scrape Shield; it rewrites the `mailto:` links and the support page's meta refresh),
   and keep Bot Fight Mode / challenges off `/.well-known/*` (Apple's CDN fetches the AASA). No page
   rule may redirect the apex (the AASA must answer 200 without a redirect).
6. Verify: `curl -sI https://getmyez.com/.well-known/apple-app-site-association` -> 200,
   `content-type: application/json`, no `location:`; `curl -s https://getmyez.com/c/x | grep -c qaren://`
   >= 1; `curl -sI https://getmyez.com/support` -> 200. After about 24 h:
   `curl -s https://app-site-association.cdn-apple.com/a/v1/getmyez.com` returns the JSON.
7. Cloudflare -> getmyez.com -> Email -> Email Routing: enable (it adds the MX and SPF TXT records; they
   conflict with any existing MX from step 2), add a verified destination inbox, create custom addresses
   `support@getmyez.com` and `privacy@getmyez.com` (ASSUMPTION, Q1) forwarding to it. Email Routing is
   receive-only: replying "as" support@ needs a separate sending setup.
8. Supabase -> Authentication -> URL Configuration: leave the redirect allow-list entry
   `qaren://reset-password` unchanged (decision). Check the Site URL and the e-mail templates: if either
   names qaren.app, change it to `https://getmyez.com` (not verified by this agent: no Supabase access).
9. Merge this unit; Railway web redeploys with `APP_BASE_URL = https://getmyez.com` (new share links)
   and redeploy the landing (`railway up landing --path-as-root -s qaren-landing -d` from the repo root,
   landing/README.md:9) so the getmyez.com chrome is live.
10. EAS: nothing to change (slug `qaren`, owner `kersher2`). The next store build (after PR #330 is live,
    UB-R4) carries `applinks:getmyez.com`; EAS capability sync keeps Associated Domains enabled on the
    App ID `com.qaren.app`. Build only after step 6 passes.
11. External listings that name qaren.app: App Store Connect support / privacy / marketing URLs
    (`https://getmyez.com/support`, `https://getmyez.com/privacy.html`, `https://getmyez.com/`) when the
    app record exists; Google Cloud OAuth consent screen (authorized domains, home page, privacy policy
    URL) if set; affiliate applications Awin / CJ / ArabClicks "Promotional Space URL"
    (docs/runbooks/2026-08-31-affiliate-signup-answers.md:54,116,179) if submitted; Sign in with Apple
    "email communication" domains if qaren.app was registered there.
12. qaren.app itself: decide renew-or-lapse (Q3). If it lapses, a stranger can buy it; this unit removes
    every runtime use so nothing of ours resolves through it.

## 8. Tests

### 8.1 RED (written, run, failing for the right reason on the untouched tree)

* `SmartCompareApp/__tests__/config/domain.s76.test.ts` (9 nodes):
  D1 associatedDomains == `["applinks:getmyez.com"]`; D2 every https intent-filter host == getmyez.com,
  paths `/r/ /c/ /q/`, autoVerify true; D3 (control) KEEP identifiers; D4 no `qaren.app` under src/**,
  app.json, eas.json, App.tsx, index.ts, locales/** after stripping `com.qaren.app`; D5 `linking.prefixes`
  == `['qaren://', 'https://getmyez.com']`; D6 `pathFromPushUrl` host boundary on getmyez.com with
  parity against the real `extractPathFromURL` (look-alikes and the retired host rejected; the
  case-insensitive row without parity); D7 `actionFromPushUrl` resolves a getmyez.com share link to
  ReferralLanding and rejects the retired host; D8 the Contact Us fallback opens
  `mailto:<SUPPORT_EMAIL>?subject=MYEZ%20Support`; D9 the screen names the mailbox once, in `const SUPPORT_EMAIL`.
* `SmartCompareApp/__tests__/landing.domain.s76.test.ts` (7 nodes): L0 page set; L1 no `qaren.app` outside
  legal regions; L2 canonical / hreflang / og:url table on getmyez.com; L3 every address outside a region
  == SUPPORT_EMAIL, every page but open.html publishes it, support meta refresh; L4 nginx template,
  open.html, Dockerfile, README (README: only a "retired" line may name the old host) + open.html names
  `'https://getmyez.com'`; L5 (control) open.html maps getmyez.com `/c/<t>?ref`, `/r/<code>`, `/q/<t>`,
  `/c/?ref`, `/` to qaren://; L6 (control) .well-known identifiers unchanged, no host in them.
* `tests/test_domain_s76.py` (6 nodes): T1 APP_BASE_URL; T2 `create_invite` share link ==
  `https://getmyez.com/c/<token>?ref=<code>`; T3 admin cost label; T4 the two robots UAs mirror and name
  `https://getmyez.com/bot`; T5 no `qaren.app` under app/ or scripts/ (allowlist: the two #330-owned
  legal drafts, reasons >= 40 chars); T5b (control) scanner positive control on runtime-built literals.

### 8.2 GREEN amends (existing pins that encode the web host; measured red under the probe)

Exactly 7 nodes go red when the section-2 edits are applied (green probe, section 9):
brand.hardcoded.s69 "the support mailto keeps its address but its subject says MYEZ";
landing.brand.s69 "every <title> names the brand ... addresses kept"; linking.w315 L9b;
pushNavigation.w315 P4f, P9, P9b; linking.resetPassword.w36 "both prefixes survive the move".
Amend per section 2.5. Optional (host-agnostic, recommended): test_password_reset_deep_link sample value,
test_landing_fallback_pages_s69 and landing.handoff.s69 header text.

## 9. Gate set (GREEN)

* jest (ONE call, from sc-s76-domain/SmartCompareApp): the two RED files + pushNavigation.w315,
  navigation/linking.w315, linking.resetPassword.w36, landing.brand.s69, brand.hardcoded.s69,
  landing.handoff.s69, ContactUsScreen.test.tsx, App.pushTap.w315, App.referral, ReferralLandingScreen.test,
  ReferralLandingScreen.redesign, LegalScreen.test; then the FULL jest suite once (a rebased client unit
  runs the full suite before the PR; source-scanning suites are the collision points). tsc --noEmit;
  eslint on the changed files.
* pytest (pyt.py, CI-order chunks <= 25 files, bound 1200): test_domain_s76, test_referral_service,
  test_referral_service_internals, test_referral_routes, test_referral_e2e, test_referral_must_fixes,
  test_referral_share_status_lifetime, test_referral_share_privacy, test_admin_referral_endpoints,
  test_cost_dashboard, test_cost_meter_s74, test_admin_key_and_sentry_scrub, test_security_regression,
  test_security_hardening, test_robots_unreadable_ruling, test_sitemap_discovery,
  test_m6_c1_normalize_and_sitemap_match, test_m6_c2_sitemap_pdp_markers, test_search_descriptor_d3,
  test_retro_w0_4, test_transient_negcache, test_landing_fallback_pages_s69, test_password_reset_deep_link,
  test_health_brand_s69, test_retro_w1_2d, test_s71_u13_harness_auth.
* Source-scanning pins (always, by the session-75 rule): test_model_config, test_model_config_enforced,
  test_hermeticity_pins, test_ci_gates, test_events_allowlist_superset, test_auth_error_log_hygiene,
  test_retro_w0_4_efg, test_retro_w1_2b, test_sentry_channels_u8d_unit, test_shopify_pdp_json,
  test_u3b_sharing_branch_removed, test_u3c_store_false_pin, test_w4_13_measurement_truth,
  test_migration_043_delete_user_cascade, test_be_harness, test_prompt_fence, test_scoring_rubric_truth,
  test_s75_fanout_identity; the pre-commit hook files (test_precommit_hook*.py) in their OWN runner call
  (bound 1200).
* Lint: ruff E9,F63,F7,F82 + py_compile on the changed .py files.

## 10. Conflicts with PR #330 (feature/s73-u8-legal; worktree sc-s70-u4b)

* Textual: NONE, measured. `git merge-file -p` of (main + this unit's planned edits) x main x #330
  (3533e860) over the six legal pages and landing.brand.s69.test.ts: 0 conflicts each, 0 `qaren.app`
  left in the merged pages; host-mention counts 7/9/7 on main after GREEN and 5/9/5 merged with #330,
  matching both sides' ADDRESS_COUNTS. Files #330 changes that this unit also changes: the six pages and
  landing.brand.s69.test.ts only (different lines, section 4 and 2.5).
* Semantic (a rebase fix ON #330, not in this unit): #330's `tests/test_legal_docs_u8.py:751`
  `FIRST_PARTY_HOST_SUFFIXES = ("qaren.app",)` excludes only qaren.app from the T7b scan of
  app/services (`_external_host`, `URL_HOST = https?://([A-Za-z0-9.-]+)` over every non-docstring
  string literal). After this unit two literals carry `https://getmyez.com`: referral_service.py:50
  and the UA format string in sitemap_discovery_service.py:387. Both modules become "found": 
  `test_t7_scanner_positive_controls` (`:915` asserts referral_service.py is not found) reddens, and the
  T7b coverage rule reddens for both (neither module is in `NOT_PERSONAL` nor in any processors.json
  row: checked on 3533e860). Fix at #330's rebase, one line: `FIRST_PARTY_HOST_SUFFIXES = ("qaren.app",
  "getmyez.com")` (`:894`'s positive-control literal may stay). MEASURED: #330's own `_scan_source`
  (extracted from 3533e860 by AST, executed over the planned edits in memory) finds `[]` today,
  `['getmyez.com']` in both modules after this unit, and `[]` again with the two-suffix tuple.
* Data-only mentions in #330 (no conflict): test_legal_docs_u8_polish.py uses `privacy@qaren.app` /
  `support@qaren.app` as fill-in sample values and docstrings ("the landing chrome publishes
  support@qaren.app"); legalScreenLang.u8.test.tsx:45 uses the Railway landing host (stays valid).
* Merge order: either order works textually. If this unit lands first, #330 rebases with the one-line
  suffix fix above; if #330 lands first, this unit rebases with no change (the legal-region skip and the
  T5 allowlist tolerate both trees).

## 11. Open questions

* Q1 Mailboxes: support@getmyez.com and privacy@getmyez.com (ASSUMPTION) or others? legal@ is dropped by #330.
* Q2 The PAUSE Fragrance Study site on getmyez.com: retire it or move it to a subdomain?
* Q3 qaren.app: renew as a defensive registration, or let it lapse? (Lapse = anyone can buy it.)
* Q4 Admin cost line: the getmyez.com registrar and yearly price (the line keeps 1.5 USD/mo "$18/yr",
  the .app figure, until answered); a second line if qaren.app is renewed.
* Q5 www.getmyez.com: attach (and redirect to the apex) or not? Universal links are claimed for the apex only.
* Q6 Crawler UA: the info URL `https://getmyez.com/bot` has no page (nginx 404s it, as qaren.app 522d);
  add a landing/bot.html? And the UA contact is a personal Gmail address: move it to a getmyez.com mailbox?
* Q7 Legal entity (owner note 2026-10-10): a D-U-N-S application to move from sole proprietor to a company
  under SYNACKSOFTWARE was filed long ago. Its status decides the #330 fill-in `CONTROLLER_NAME` ("exact
  legal name as on the Apple membership") and `CR_NUMBER`, the Apple Developer account type (an
  organization account needs a D-U-N-S number; the seller name changes), and the getmyez.com registrant.
  This unit changes none of them; record the status before the #330 fill-in.

## 12. Measurements (this agent, 2026-10-10)

* RED jest (domain.s76 + landing.domain.s76, untouched tree): `Tests: 12 failed, 4 passed, 16 total`
  (passing = D3, L0, L5, L6 controls); every failure names `qaren.app` / `support@qaren.app`.
* RED pytest: `5 failed, 1 passed` (T5b control passes); `[pyt] tag=domain-red ... status=FAIL rc=1`.
* Current pins on the untouched tree: jest 8 suites `Tests: 94 passed, 94 total`; pytest
  test_referral_routes + test_landing_fallback_pages_s69 + test_password_reset_deep_link `69 passed`,
  `[pyt] tag=domain-base-pins ... status=OK rc=0`.
* GREEN-feasibility probe (section-2 edits applied to 22 files, then every byte restored and
  sha256-verified, lock removed): jest `Tests: 7 failed, 103 passed, 110 total` (both RED files pass; the
  7 = section 8.2); pytest 7 files `159 passed`, `[pyt] tag=domain-green-probe ... status=OK rc=0`.
* tsc --noEmit rc=0; eslint on the two new files rc=0, 0 warnings; ruff + py_compile clean.

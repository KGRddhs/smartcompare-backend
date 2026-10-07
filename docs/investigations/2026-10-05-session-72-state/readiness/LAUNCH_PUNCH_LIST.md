# MYEZ iOS launch punch list (session 72, 2026-10-05)

Synthesis of four read-only finder reports at main `845ece15`. Written 2026-10-05 about 14:10-14:40 AST.

- Finder reports (sha256 checked before use):
  - config `readiness/config/CONFIG_AUDIT_DELTA.md` (8363d33d...)
  - backend `readiness/backend/READINESS_BACKEND.md` (97f4cbad...)
  - client `readiness/client/READINESS_CLIENT.md` (cdc93bef...)
  - issues `readiness/issues/ISSUE_TRIAGE.md` (770dbfd9...)
- PRD: the session-69 launch runbook (sections 2, 3, 4, 6), the session-69 state doc, the session-71 state (section 0), ledger and implementation plan.
- Every line carries the finder row ids in brackets. Nothing here is new work that no finder named.
- The synthesis re-read six claims in code at `845ece15` (marked "synth read"). Everything else is the finders' evidence.
- "NOT VERIFIED" is carried from the finder that wrote it.
- Binding scope (PRD out-of-scope list): no LLM provider switch, no StoreKit/IAP, no iPad, no scraper flag flips and no dark-flag activation before App Store approval, none of the fourteen session-68b flags. Findings that would break this rule are parked in POST-LAUNCH or turned into an explicit owner decision.

Tier legend used in section C:
- MUST = it ships inside the store binary, or it is a hard gate on the path to Submit for Review.
- SHOULD = it makes the launch safer or more truthful, but Submit is possible without it.
- POST-LAUNCH = after approval, with the reason.

---

## A. VERDICT

**The app cannot be submitted today.** Funding OpenAI alone does not make it submittable.

The code side is close. Every Claude unit that needed no owner input has merged:
- session 69: #253 #254 #255 #257 #258 #269 #271 #273 #274
- session 71: #279 #288 #290 #297 #307 #310 #313

What remains is mostly owner input, plus a short chain of Claude units that wait on it.

Seven hard stops remain. Each one alone blocks Submit:

| # | Hard stop | Owner | Rows |
|---|---|---|---|
| 1 | OpenAI unfunded: every compare fails (Sentry 429 credit_balance_exhausted, last seen 2026-10-03) | Ahmed | [RB-1] |
| 2 | Privacy policy and terms are the 2026-03-26 DRAFT template. They say Qaren, promise an AI opt-out that routes nothing, and mention "Premium subscribers". The in-app Legal screen, the consent sheet link, two backend routes and four landing pages all serve them | Ahmed inputs, then Claude U8 | [RB-3, LL-1/RT-3, RB-2, RB-11, U8] |
| 3 | The Profile "Help improve AI quality" toggle is on screen and does nothing (`select_client_for_user` has 0 callers) | Ahmed D3, then Claude U3b | [#266, LL-4/PM-2, RB-7, U3b] |
| 4 | No App Store screenshots | Ahmed | [RB-5, SA-01] |
| 5 | No ASC app record, no App Store profile, no ASC API key (Hussain's Individual team) | Ahmed + Hussain | [RB-6, EXPO-03] |
| 6 | No premium demo account for a login-gated app | Ahmed | [RB-8, S3-E1] |
| 7 | No iOS binary since 2026-07-04; the new icon, launch screen and native config reach a phone only in a NEW binary | Ahmed (builds) | [RB-29, BP-06, EXPO-01/SA-02 DONE in code] |

Estimate (synthesis arithmetic over the finders' unit sizes and owner minutes; NOT VERIFIED against real EAS or Apple processing times):
- About 4 to 6 working days of elapsed time, counted from the day Ahmed sends the decisions reply AND holds the Apple session with Hussain.
- That assumes no device check fails. A failed native check (Google sign-in, splash flash) adds about 1 day and one more preview build.
- Owner hands-on time is about 12 to 16 hours, spread over those days.

### A1. Critical path to "Submit for Review"

Each step names its owner, its estimate and the steps it waits for. A Claude loop = spec, review, RED, GREEN, adversaries, PR, about half a day of wall clock on this box. At most two gate-heavy workflows run at once (principle 4).

| # | Owner | Step | Estimate | Waits for | Rows |
|---|---|---|---|---|---|
| 1 | Ahmed | Send the decisions reply (section D) | 30-45 min | - | [S3-B-legal, RB-19, RB-7, #296, S3-B-D10, DEL-043, CL-CANARY] |
| 2 | Ahmed | Fund OpenAI: read tier/TPM; data sharing OFF (if D3=A); prepaid low cap, project budget, 50/80% alerts; NEW key on `web` from his own terminal | 30 min | - (the data-sharing switch follows 1) | [RB-1, S3-A1.1, S3-A1.5, RB-23] |
| 3 | Ahmed | Supabase paid plan; read Confirm-email, sender and templates; add `qaren://reset-password` to the redirect URLs | 25 min | - | [RB-22, BE-05, BE-07, RB-38g] |
| 4 | Ahmed (testers) | Open the current app signed in and run the Sentry deep-link test (B10). Claude reads Sentry `react-native` | 15 min | - | [CL-SENTRY, RN-SENTRY, ISS-G1, U13-watch] |
| 5 | Claude | BE-HARNESS: canary script enforces the runbook A1.8 rule; authenticated warm-up script; runbook A1.8/E2 rewritten for U13 | 1 loop | - | [BE-01, BE-02, RB-13, S3-A1.8] |
| 6 | Ahmed, then Claude | Migration 043: PRECHECK grid, Claude reads it, then ONE_PASTE + POSTCHECK (+ BACKFILL if section 9 c or d > 0) | 30-45 min over 2 sittings | 1 | [U8b-043, DEL-today, DEL-043] |
| 7 | Ahmed + Hussain | Apple session: ASC API key, app record (send the numeric ascAppId), `eas credentials` production (cert, App Store profile, APNs, capabilities), Sentry token in the EAS production env, optional SIWA key | 1-2 h | - (schedule only) | [RB-6, RB-27, EXPO-05, EXPO-12, S3-C3] |
| 8 | Ahmed + Claude | Post-funding canary with the fixed script via `railway run`; then revoke the old key | 10-15 min | 2, 5 | [S3-A1.8, S3-A1.9] |
| 9 | Claude | U8 legal redraft (the spec can start today with placeholders; no legal fact is invented) | 1-2 loops, about 1 day | 1, 6 | [U8, RB-3, RB-2, RB-11, RB-38d, LL-14, BE-12, #296] |
| 10 | Claude | U3b: toggle, policy section 11 and the router, plus the approved consent-withdrawal control | 1 loop | 1 (D3) | [U3b, #266, RB-7] |
| 11 | Claude | Client copy and canary: U-COPY (+ #239 rider) and U-CANARY | 1 loop together | 1 | [CL-COPY, CL-CANARY, ISS-G3, #239] |
| 12 | Claude | LISTING-TRUTH: correct runbook section 6 EN/AR text and review notes | about half a loop (docs) | 1 (final Google line after 15) | [RB-17, RB-31, BE-03, BE-04, BE-06, BE-08, BE-09] |
| 13 | Ahmed | Landing redeploy `railway up landing --path-as-root -s qaren-landing -d` | 5 min | 9 | [RB-3, OWNER-10] |
| 14 | Claude | U10: fill `eas.json` `submit.production` (interactive `eas submit` is the fallback) | XS, 1-2 h | 7 | [U10, RB-38e, EXPO-03/BP-04] |
| 15 | Ahmed | Preview build from the release commit; delete the old app on both iPhones; run the NEW-binary device checks (B13) | 1 build cycle + 2-3 h | 9, 10, 11 merged | [RB-29, BP-06, CL-DEVCHECKS, CL-GOOGLE, CL-SPLASH-FLASH] |
| 16 | Claude (conditional) | U-GOOGLE, U-SPLASH or U-SNT, only if their device check fails | 0.5-1 day each; a native fix needs one more preview build | 4, 15 | [CL-GOOGLE, BE-04, CL-SPLASH-FLASH, CL-SENTRY] |
| 17 | Ahmed | Two premium demo accounts: confirmed, onboarded, `subscription_tier=premium`; passwords only in ASC | 30 min | 3 (and 6, so a deleted demo email can be re-registered) | [RB-8, BE-06, S3-E1] |
| 18 | Ahmed | Production build from the same commit; `eas submit`; internal TestFlight smoke on the exact binary; read the ASC processing email (ITMS-90683/91053/91061); one Expo test push | 1 build cycle + 1-2 h; Apple processing time NOT VERIFIED | 7, 14, 15, 16 | [RB-29, RB-38b/PM-7, EXPO-05] |
| 19 | Ahmed | Warm-up with the authenticated script; only passing pairs go into the review notes | 15 min, within 24 h of submission | 5, 8 | [RB-13, BE-02] |
| 20 | Ahmed | Six real screenshots on a physical iPhone; Claude resizes and strips alpha | about half a day | 8, 11, 15 (or the early OTA in T2), 17, 19 | [RB-5, SA-01] |
| 21 | Ahmed | ASC listing: corrected section 6, App Privacy from the inventory (Tracking = No), age questionnaire + 13+ override, copyright per D5, the Railway landing URLs, review notes, demo credentials | 1 h | 7, 12, 13, 17, 20 | [RB-17, S3-E5, RB-20, RB-19, RB-31] |
| 22 | Ahmed | Submit for Review; re-warm daily while in review | 5 min + 15 min/day | 18, 19, 21 | [S3-E7, RB-13] |

### A2. Runs in PARALLEL today, without any owner input

Claude:
- P1. DOCS-CONFIG unit first (docs only): every Opus agent now receives CLAUDE.md, which still tells agents to copy `.env` [CFG-01, CFG-03, CFG-04, CFG-02, R3, R17, CFG-05].
- P2. BE-HARNESS (critical-path step 5) [BE-01, BE-02].
- P3. OBS redaction unit (#311 family) and the #66 cost meter, before real OpenAI traffic starts [#311, #226, #301, #68, #66].
- P4. #295 device purge and the #79 SSRF fix (small, no input) [#295, #79].
- P5. The U8 spec with `<PLACEHOLDER>` fields; RED waits for the inputs [U8].
- P6. T0b Phase B, off the critical path [#315, R11].
- Pairing for the two gate-heavy slots: BE-HARNESS + OBS first. The docs unit is light and can run beside them.

Ahmed, independent of each other:
- T1. Steps 2, 3, 4 and 7 above.
- T2. Optional preview OTA from main (`npm ls` first, one phone first). It puts U4c, U4d and U13c on the testers' phones so the OTA column of the device checklist can start now [CL-OTA, CL-DEVCHECKS].
- T3. Optional early preview build from `845ece15`. It surfaces the Google sign-in and splash-flash outcomes days earlier. Either can trigger a conditional unit [CL-GOOGLE, CL-SPLASH-FLASH, BP-06].

### A3. Already DONE in code (proof), so nobody re-does it

| Item | Proof | Reaches users via | Rows |
|---|---|---|---|
| MYEZ launcher icon + native launch screen | #279 (de66a25f) | NEW binary only | [EXPO-01/SA-02] |
| supportsTablet false, honest mic strings, no Face ID string, Arabic bundle localization | #254; app.json:22, :197, :203, :212-213, :220-221 | NEW binary only | [runbook #9/#10/#30] |
| 13 certificate pins + Sentry mismatch listener | #253; certificatePinning.ts:52-85, :111-125 | binary + OTA | [CL-PIN] |
| Honest limit sheet; no fake paywall | #255 | already on phones | [runbook #2] |
| MYEZ rename | #257 | phones + landing | [D12/D13 de facto] |
| AI consent sheet naming OpenAI | #274 | on phones | [RB-7 half] |
| Account deletion route; erasure code half | #290, #310; auth_routes.py:1165-1181 | backend live; migration 043 NOT applied | [DEL-route, U8c] |
| Paid routes require a caller (U13), active in prod | #297; anonymous compare = 401 | backend | [U13] |
| Camera 401 refresh-and-retry | #313 | OTA or NEW binary | [CL-OTA] |
| In-app MYEZ mark, reveal badge | #288, #307 | OTA or NEW binary | [CL-OTA] |
| Landing hand-off page /c/ /r/ /q/ | #273, live on the Railway landing | dead on qaren.app until attached | [RB-12] |
| pip-audit blocking in CI | ci.yml:213-216 | CI | [CL-pip] |

---

## B. AHMED ORDERED CHECKLIST

Order: money and keys, then decisions, then Apple, then devices and builds, then listing. Items marked TODAY have no dependency.

### B-money and keys

| # | What | Where (screen or exact command) | How Claude verifies afterwards | Unblocks | Time | Rows |
|---|---|---|---|---|---|---|
| B1 TODAY | OpenAI: read tier and TPM; prepaid credit per D8; project budget + 50/80% alerts; data sharing OFF if D3=A; read the Chat Completions storage default; NEW project key | platform.openai.com: Settings -> Limits, Settings -> Billing, the project budget page, Data controls. Key into Railway `web` from your own terminal (never pasted into a chat or transcript) | The fixed canary passes (step 8). No new 429 `credit_balance_exhausted` in Sentry `python-fastapi`. No 429 in the Railway HTTP log | Canary, warm-up, screenshots, real-verdict device checks, demo history | 30 min | [RB-1, S3-A1.1, S3-A1.5, RB-23] |
| B2 TODAY | Supabase: move to a paid plan; read Auth -> Email "Confirm email", the sender and whether the templates still say Qaren; add `qaren://reset-password` | Supabase dashboard: Billing; Authentication -> Providers -> Email; Authentication -> Email Templates; Authentication -> URL Configuration -> Redirect URLs | You send the three readings. Claude cannot read them: the Supabase MCP is unauthenticated (NOT VERIFIED) | Demo-account recipe; removes the auto-pause risk (a Supabase outage is a total compare outage under U13) | 25 min | [RB-22, BE-05, BE-07, RB-38g] |
| B3 | Railway: confirm the paid plan, card and usage cap; mirror the config-as-code settings into the dashboard before 2026-12-01 | Railway dashboard: Billing; each service's Settings (start command, healthcheck, draining 30 s, warmer watch paths) | You confirm. Claude re-reads railway.json for the list to mirror | Keeps prod up through review | 20 min | [RB-37] |
| B4 | GitHub plan check before the repo goes private | GitHub: Settings -> Billing and plans | The orchestrator reads repo visibility and branch protection through the REST helper | The repo-private decision (REPO) | 10 min | [BE-13] |
| B5 | Apply the permission deny rules (now, and again after Claude extends the list per CFG-05; the script is idempotent) | `python C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-03-session-71-state/scripts/apply_audit_batch_a.py --apply` in a real terminal | Key-only read: `~/.claude/settings.json` has `permissions.deny` with the expected count. No live probe yet (NOT VERIFIED that deny blocks Bash readers) | Agent safety for the remaining units | 2 min | [R1, BE-14, CFG-05] |
| B6 | Revoke the old OpenAI key | platform.openai.com: API keys | Next canary still passes | Closes the old key | 5 min | [S3-A1.9] |

### B-decisions

| # | What | Where | How Claude verifies | Unblocks | Time | Rows |
|---|---|---|---|---|---|---|
| B7 TODAY | Send the section D reply in one message | Chat | Claude records each answer in the state doc and the unit specs | U8, U3b, U-COPY, U-CANARY, LISTING-TRUTH, 043 apply, DEL-FOLLOWUPS, UI-9 | 30-45 min | [S3-B-legal, D3-D14] |
| B8 | Migration 043, sitting 1: run PRECHECK and send the grid back | Supabase SQL editor; file `sc-docs-70/docs/investigations/2026-10-03-session-71-state/APPLY_043_1_PRECHECK.sql` | Claude reads the grid against the STOP rules in PR #290 (FK branch A/B, #294 shapes) | Sitting 2 | 15-20 min | [U8b-043, #294] |
| B9 | Migration 043, sitting 2: ONE_PASTE, then POSTCHECK, then BACKFILL only if section 9 c or d > 0 | Supabase SQL editor; the `APPLY_043_*` files in the same folder | Claude reads the POSTCHECK output and records the apply | U8 deletion wording; #303 SQL cleanup; 044 | 20-30 min | [DEL-today, DEL-043, #291] |

### B-Apple

| # | What | Where | How Claude verifies | Unblocks | Time | Rows |
|---|---|---|---|---|---|---|
| B10 | Hussain session, part 1: ASC API key (Team key, Admin role; `.p8` stored outside the repo; record Key ID and Issuer ID) | App Store Connect -> Users and Access -> Integrations -> App Store Connect API (Account Holder only) | Not readable by Claude. Hussain confirms | `eas submit` | 15 min | [RB-6] |
| B11 | Part 2: app record. New App, iOS, name `MYEZ - Compare Smart` (or `MYEZ`), English, bundle `com.qaren.app`, SKU `qaren-ios`. Send Claude the numeric Apple ID | App Store Connect -> Apps -> + | U10 pins `ascAppId` to digits and validates with the resolved submit schema | U10, listing | 10 min | [RB-6, U10] |
| B12 | Part 3: credentials in a real terminal: `cd SmartCompareApp` then `eas credentials -p ios`. Production profile; reuse the Distribution cert; generate the App Store profile; Push = yes (APNs); upload the ASC key; sync capabilities (Sign in with Apple, Associated Domains, Push). In the EAS dashboard, confirm `SENTRY_AUTH_TOKEN` in the production environment or add `SENTRY_ALLOW_FAILURE=true`. Optional: a Sign in with Apple key | Real terminal + expo.dev project environment | The production build succeeds (B16) | Production build | 30-60 min | [RB-27, EXPO-05, EXPO-12, S3-C3] |
| B13 | Domain and mail (per decision DNS): attach `qaren.app` to `qaren-landing`; fix the Cloudflare record behind the 522; then Cloudflare Email Routing for support@, privacy@ and legal@ with one test mail each | Railway -> qaren-landing -> Settings -> Networking -> Custom Domain; Cloudflare DNS; Cloudflare -> Email -> Routing | The orchestrator checks that `https://qaren.app/.well-known/apple-app-site-association` returns 200 `application/json` with no redirect | Share and referral links, universal links, the support e-mail in the listing | 45-60 min | [RB-12, RB-38c, EXPO-06/RT-8] |

### B-devices and builds

| # | What | Where | How Claude verifies | Unblocks | Time | Rows |
|---|---|---|---|---|---|---|
| B14 TODAY | Testers open the current app (OTA e2bde9c9) signed in. In Safari, open `qaren://comparison/sentry-check`, accept "Open in MYEZ", wait 2 s, close Results | Tester iPhones | Sentry org `qaren-rr`, project `react-native`: a `comparison_wall_time` info event. Railway HTTP log: mobile-UA requests. The U13 `[paid-auth]` histogram | Precondition P7; the U13 24 h watch; decides whether U-SNT is needed | 15 min | [CL-SENTRY, RN-SENTRY, ISS-G1, U13-watch] |
| B15 (optional, TODAY) | Preview OTA from main: `cd SmartCompareApp`, `npm ls` (must show the U4b version set), then `eas update --branch preview --clear-cache --message "..."`. Smoke on ONE phone first. Two cold launches per phone | Real terminal from a clean checkout of main | Claude records the EAS group id; testers run the OTA column (rows 1-16) of the client checklist | Early device checks; screenshots with the new mark | 30 min + checks | [CL-OTA, CL-DEVCHECKS] |
| B16 | Preview build from the release commit (main containing U8, U3b, U-COPY, U-CANARY and the merged SHOULD client units): `eas build -p ios --profile preview`. Delete the old app on both iPhones, install, run the NEW-binary checks: Apple, Google and email sign-in; launcher icon; launch-screen hand-off with no white flash (fresh install and after an OTA); camera and photo prompts in EN and AR; no mic or Face ID prompt; home-screen name; pinning active (no "running unpinned"); Sentry event on release transport; iPad compatibility mode if an iPad is available | Real terminal + both iPhones | Claude reads each check result against client checklist rows 3-8, 10, 17-23 | Production build; conditional units | 1 build cycle + 2-3 h | [RB-29, BP-06, CL-DEVCHECKS, CL-GOOGLE, CL-SPLASH-FLASH] |
| B17 | Two premium demo accounts. Register in the app; confirm in Supabase if Confirm-email is ON; complete onboarding once; Table editor `users.subscription_tier = premium` (check `preferences_completed = true`). Passwords only in ASC, never in the repo | App + Supabase dashboard | A signed-in compare on each account returns a real verdict | Screenshots (History needs 3+ entries), review notes | 30 min | [RB-8, BE-06, S3-E1] |
| B18 | Production build from the same commit: `eas build -p ios --profile production`, then `eas submit -p ios --profile production --latest`, then internal TestFlight smoke on the exact binary, the ASC processing email, one Expo test push | Real terminal; TestFlight | Claude reads the ITMS lines of the processing email and the smoke results | Submit | 1 build cycle + 1-2 h | [RB-29, RB-38b/PM-7, EXPO-05, U10] |
| B19 | Warm-up after BE-HARNESS lands: `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python scripts/review_warmup.py`, within 24 h of submission and daily in review | Real terminal | The script's pass table. Only passing pairs go into the review notes | Review notes, screenshots | 15 min/day | [RB-13, BE-02] |

### B-listing

| # | What | Where | How Claude verifies | Unblocks | Time | Rows |
|---|---|---|---|---|---|---|
| B20 | Six screenshots: Home with two products, Results winner card, dimension bars / runner-up, confidence pills, camera framing two products, History with 3+ entries. One iPhone set: 6.9" (1320x2868, 1290x2796 or 1260x2736) or 6.5" (1284x2778 or 1242x2688). No splash, sign-in, loading or limit sheet | Physical iPhone (side button + volume up) | Claude resizes and strips alpha, then checks the pixel sizes (live ASC spec page NOT re-checked today) | Listing | about half a day | [RB-5, SA-01] |
| B21 | Landing redeploy after U8 merges | `railway up landing --path-as-root -s qaren-landing -d` | `grep -ri draft app/legal landing` = 0; each legal URL returns 200 with no banner | Privacy Policy URL in ASC | 5 min | [RB-3, U8] |
| B22 | ASC fields: the corrected section 6 text, App Privacy row by row from `docs/privacy-data-inventory.md` (Tracking = No), age questionnaire then Override -> 13+ (per D9), copyright `2026 <OWNER per D5>`, Privacy and Support URLs on the Railway landing, review notes, demo credentials | App Store Connect -> the app | Claude re-verifies the labels against the inventory before you paste | Submit | 1 h | [RB-17, S3-E5, RB-20, RB-19, RB-31] |
| B23 | Submit for Review | App Store Connect | - | - | 5 min | [S3-E7] |
| B24 | After approval: `APP_STORE_URL` on `web`; Worker redeploy after Claude replaces `idTBD`; JS hotfixes go to `--branch production` | Railway; Cloudflare Worker; real terminal | Claude edits `cloudflare-workers/qaren-redirect/src/index.ts:29` and the canary runbook line 430 | - | 10 min | [RB-38f, RB-26, S3-F] |

### B-off-path settings (not on the launch path; batch B is yours)

- Disable the 10 Cowork plugins in Claude Desktop (keep `legal` only if U8 uses it). Each agent start then skips about 40 auth probes and a 30 s salesforce timeout [R6].
- Disable unused claude.ai connectors and anthropic-skills for Code [T5, T14].
- Update `qaren-brand-voice` to MYEZ in the claude.ai skills settings [R23, NOT VERIFIED content].
- Decide on `effortLevel: xhigh`, the codex plugin and typescript-lsp [T16, R26, CFG-06].

---

## C. CLAUDE UNITS

Lever key: backend deploy (Railway on merge) | OTA | new binary | landing redeploy | docs/tooling. "OTA-capable" client code must still be in the store binary, because the production channel has never received an update.

### C1. MUST (in the binary, or a hard gate on the path to Submit)

| Unit | Scope | Files | Size | Lever | Waits for | Rows |
|---|---|---|---|---|---|---|
| BE-HARNESS | `verify_after_credits.py` enforces the A1.8 rule (no `comparison.error`, specs, a price amount, pros/cons, stream terminal `success:true`, the `product_a`/`product_b` probe). New `scripts/review_warmup.py` (six pairs x2, opt-in admin key, paced, pass table). Runbook A1.8 and E2 rewritten for U13 | `docs/investigations/2026-09-29-session-69-state/verify_after_credits.py` (:38, :67, :68 synth read), `scripts/review_warmup.py`, a hermetic test, the runbook | S | docs/tooling | none | [BE-01, BE-02, RB-13, S3-A1.8] |
| U8 legal redraft | Replace both `app/legal/*.md`: MYEZ, controller, full processor list (incl. Bright Data, Firecrawl, Scrape.do, Expo push, Apple/Google sign-in, Cloudflare), the data rows, deletion truth matching 043, retention per #296, 10/15 working days, log/IP disclosure, no section 11 opt-out, no "Premium subscribers". Move every version anchor together; optional `?lang=ar` + LegalScreen lang param and version-keyed cache. Merge before the production build | `app/legal/*.md`, `app/api/legal_routes.py` (x2), `app/services/consent_service.py:31`, `SmartCompareApp/src/services/consent.ts:12`, `landing/{privacy,terms}.html`, `landing/ar/{privacy,terms}.html`, `LegalScreen.tsx`, tests; #308 favicon rider | L (1-2 loops) | backend deploy + landing redeploy + new binary | legal inputs L1-L4, L6, L8a; D3; D5; #296; D10 wording; 043 applied | [U8, RB-3, RB-2, RB-11, RB-19, RB-38d, LL-14, BE-12, #296, #308] |
| U3b | D3=A: remove the Profile toggle (ProfileScreen.tsx:503-510) and its en/ar keys, delete `select_client_for_user` and the `OPENAI_API_KEY_PRIVATE` branch. Add the consent-withdrawal control approved on 2026-10-03. D3=B: wire every call site, `AI_CONSENT_VERSION` 2 | `ProfileScreen.tsx`, `src/i18n/{en,ar}.json`, `app/services/openai_service.py` (+ callers), `auth_routes.py` preference toggles, tests | M | backend deploy + new binary | D3 | [U3b, #266, RB-7, LL-4/PM-2] |
| U-COPY (+ #239 rider) | Replace two placeholder lines on the reviewer's path, EN + AR under the copy-policy and i18n fences: "Photo upload coming soon" (EditProfileScreen.tsx:188, en.json:919; synth read) on the deletion screen, and "Pricing lands in an upcoming update." (en.json:155, ResultsContent.tsx:139; synth read). Rider: plural "retail sources" | `EditProfileScreen.tsx`, `src/i18n/en.json`, `ar.json`, `confidenceDetailsLines.ts`, tests | S | new binary (OTA-capable) | COPY approval + Arabic native review | [CL-COPY, #239] |
| U-CANARY | Set `CANARY_NEW_ONBOARDING_PERCENT` (features.ts:30 = 100 today; synth read) per decision CAN, with a jest pin and the CLAUDE.md :255/:506 and canary-runbook lines | `src/config/features.ts`, a test, `CLAUDE.md`, `docs/runbooks/qaren-canary-onboarding.md` | XS | new binary | CAN | [CL-CANARY, ISS-G3, BE-16] |
| LISTING-TRUTH | Correct runbook section 6: estimated prices are never labelled (BE-03); Google claim per the device check (BE-04); spare demo account (BE-06); "interface in English and Arabic; write-ups in English" (BE-08); "Bahrain market (BHD) prices from retailers across the GCC" (BE-09); deletion path "Profile -> gear -> Delete account" (ProfileScreen.tsx:366; synth read). Redraft ar-SA under the MYEZ Arabic name for native review | runbook section 6 (docs) | S | docs/tooling | D11, D5 (copyright), GOO outcome | [RB-17, RB-31, BE-03, BE-04, BE-06, BE-08, BE-09] |
| U-GOOGLE (conditional) | If Google sign-in fails on the preview build: hide the Google row for 1.0 behind a JS constant and replace the text "G" with the official asset; or fix. Rider: remove the TEMP social-login trace that logs a token head at INFO | `LoginScreen.tsx:115-122`, Register/Step 16, assets, `app/services/auth_service.py:795-806`, tests | S | new binary + backend deploy | device check 4; GOO | [CL-GOOGLE, BE-04, ISS-G2, BE-11] |
| U-SPLASH (conditional) | If the launch-screen to JS-splash hand-off flashes white: native `expo-splash-screen` hold until the mark `onLoad`. The orchestrator runs the package install | `app.json` plugins, `package.json`, `SplashScreen.tsx`, tests | M | NEW binary (+ one more preview build) | device check 18; SPL | [CL-SPLASH-FLASH] |
| U-SNT (conditional) | If B14 shows no `react-native` event: an info-event delivery probe per install + update id, release/dist tags, and an investigation | `src/services/sentry.ts` or a bootstrap-safe module, tests | S | OTA | B14 result | [CL-SENTRY, RN-SENTRY, ISS-G1] |

### C2. SHOULD (before submission; Submit is possible without them)

| Unit | Scope | Files | Size | Lever | Waits for | Rows |
|---|---|---|---|---|---|---|
| DOCS-CONFIG (do first) | Delete the three "copy .env" instructions (L286 c and g, L203) and make principle 10 say never copy `.env`. L21 "U4d in flight" -> merged #307. Drop or restate the L290 Ultracode rules. Label LIVE/prod/install commands owner-only. Fold the correction pairs (incl. L361/L441 vs #299). L90: one-paste SQL files primary. Extend the deny script with the CFG-05 forms (cat/type/Get-Content of `.env`, `Get-ChildItem env:`, `set`, `export -p`, `railway run ... env/printenv`, `git restore <file>`, `rm -rf`; keep `git restore --staged` and `git worktree remove --force`) | `CLAUDE.md`, `scripts/apply_audit_batch_a.py` (state folder) | S | docs/tooling | none | [CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, R3, R2, R17] |
| OBS redaction (UI-2) | #311: five except-arms type-only + `from None`, ErrorHandlerMiddleware text off, `cache_service` via `exc_summary` (#293), span URL scrub. #226: `str(e)` error fields. #301: raw query/URL INFO -> length + hash. #68: fire-and-forget write failures reach Sentry. Riders #286, #321 (cap), #304 (strip). Best before funding | `app/api/{auth,image,share,text,url}_routes.py`, `app/middleware/error_handler.py`, `app/services/{cache_service,sentry_service,extraction_service,log_scrub,database_service}.py`, `app/utils/async_utils.py`, `admin_routes.py` | M | backend deploy | none | [#311, #226, #301, #68, #293, #286, #321, #304] |
| COST-METER (UI-8) | `/admin/costs` reads `full_response.metadata.total_cost` so launch-week OpenAI spend is not 0 | `app/api/admin_routes.py:130`, `tests/test_cost_dashboard.py` | S | backend deploy | none | [#66, RB-35] |
| DEVICE-PURGE (UI-3) | Remove `@qaren_recent_searches` after a successful account deletion, so U8 can say device data is deleted | `src/services/authService.ts`, `HomeScreen.tsx` key, tests | S | new binary (OTA-capable) | none | [#295] |
| SSRF-PHARMACY (UI-6) | Match pharmacy domains by parsed hostname; fetch them and the lazy backfill page through the same-site guard that validates every redirect hop | `app/services/price_service.py` (:16745, :16763, :16789-16792), `structured_comparison_service.py:3025`, tests | S | backend deploy (price path: corpus gate) | none | [#79] |
| SMOKE-HYGIENE | Smoke password env-required; probe deletes its account at the end; asserts a real verdict. SQL one-paste to count and erase the existing smoke accounts (cascade first, then the auth delete) | `scripts/bundle_d_prod_smoke.py`, a new APPLY sql | S | docs/tooling + SQL (Ahmed runs) | 043 applied (for the SQL) | [#303, #267, #320] |
| SHARE-LINKS | `create_invite` mints the share token; optional `APP_BASE_URL` env override (default unchanged) so links can point at the Railway landing until qaren.app is attached | `app/services/referral_service.py:50, :348`, tests | S | backend deploy | DNS decision | [#272, RB-12] |
| DEL-FOLLOWUPS (044) | #291 orphan backfill for dashboard-deleted accounts; #296 audit-row purge after N days; #294 apply guards; #318 one multi-key purge + `run_db` | `migrations/044_*` + rollback + APPLY files, `auth_service.py`, `database_service.py`, tests | M | backend deploy + SQL (Ahmed applies) | 043 applied; R296 | [#291, #296, #294, #318] |
| PUSH-OPTOUT (UI-9) | Only if D10=B: `send_push`, `send_loop2_push` and the bonus-expiry cron skip users with `notifications_enabled` false; widen the pre-prompt copy | `app/services/push_service.py`, `scripts/cron_expire_bonuses.py`, `src/i18n/{en,ar}.json`, tests | S | backend deploy (+ copy in the binary) | D10 | [#264, S3-B-D10] |
| U10 | `submit.production.ios`: `ascAppId` (quoted digits) + `appleTeamId` 8K562M549D; validated with the resolved submit schema; jest pin. Interactive `eas submit` is the fallback | `SmartCompareApp/eas.json:23-25` (present but empty; synth read) | XS | docs/tooling | ascAppId (B11) | [U10, RB-38e, EXPO-03/BP-04] |
| RELEASE-CHECKS | `npm audit` triage note on the release commit (the orchestrator runs npm); QA static grep pack re-run + a user-visible "Qaren" residue grep over app/legal and landing; App Privacy labels re-verified against the inventory; the canary runbook :430 production-OTA rule rewritten in the production-build PR | `docs/plans/bundle-d-static-audit-pre-merge.txt`, `docs/privacy-data-inventory.md`, `docs/runbooks/qaren-canary-onboarding.md` | S | docs/tooling | the release commit | [CL-npm, CL-grep, S3-E5, RB-26, EXPO-11] |
| T0b Phase B | gitleaks pass + `.gitleaks.toml` + CI secret scan + ESLint on staged files; `--text --no-textconv` for binary-looking blobs; riders #316, #317. Off the critical path | `.githooks/pre-commit`, `.gitleaks.toml`, `.github/workflows/ci.yml`, `tests/test_precommit_hook*.py`, `tests/test_ci_gates.py` | M | docs/tooling | orchestrator ruling | [#315, #316, #317, R11, R28] |
| CLAUDE-SLIM (optional) | T1-T3: move the 17 Active-runtime blocks and the flag registry to docs; about 86K -> 20-25K tokens per agent. Approved under batch C. Not a launch gate; run only when no other unit edits CLAUDE.md | `CLAUDE.md`, `docs/SESSION_BUNDLES.md`, `docs/FLAGS.md` | M | docs/tooling | none | [T1, T2, T3, R21, R22, R31] |
| ISSUE-HOUSEKEEPING | Close #63 #64 #69 #72 #128 with their proofs; comment on #58 that Step 1 shipped; close PR #39 and #42 per decision PRS; set `sentry@claude-plugins-official` false in `.claude/settings.json` | REST helper; `.claude/settings.json` | XS | docs/tooling | ISS, PRS | [#63, #64, #69, #72, #128, #58, PR #39, PR #42, R15] |

### C3. POST-LAUNCH (with the reason)

| Item | Reason | Rows |
|---|---|---|
| W0 load flags (`ENABLE_OFFLOOP_DNS_RESOLVE`, parse offload, Supabase reuse, Upstash transport) and the M13-W3 offloads | Dark-flag activation is out of scope before approval. Decision W0 lets Ahmed grant an exception | [RB-14, #71, S3-A3.3] |
| #299 per-user limiter key (+ #114, #72) | A new flag that cannot be activated before approval buys nothing pre-launch. The prepaid cap is the backstop | [#299, #114, #72] |
| U11 Sign in with Apple token revocation | Needs a SIWA key and a product call; runbook marks it optional. Listed as a rejection risk in E | [RB-34, LL-9, U11] |
| D7 preflight breaker; breaker census comment | Dark flag; keep it as the incident lever | [RB-25, RB-38k] |
| `ENABLE_PASSWORD_RESET_DEEP_LINK`; `APP_STORE_URL`; Worker `idTBD`; production-channel OTA rule | After the store build and approval (runbook F) | [RB-38g, RB-38f, RB-26, S3-F] |
| #284 re-engagement reads `users.governorate` | Fix before enabling re-engagement pushes (prod flag value NOT VERIFIED) | [#284] |
| Server-side consent record | Follow-up per Ahmed's 2026-10-03 answer | [U3b scope note] |
| Batch D housekeeping: MEMORY.md trim, skill prune, update settings, AGENTS.md fork, worktree prune (23 merged, junction-safe), parent-dir layer, flag registry, stale facts | Ahmed: batch D after the launch lane | [R12, R14, R19, R29, R30, R32, R10, R21, R22, R31, R24, R26, CFG-06] |
| Scraper coverage and price truth: #61 #75 #76 #77 #78 #93 #94 #96 #236; PR #42; re-file PR #39's two defects as one issue | Scope rule: no scraper flag flips before approval | [#61, #75-#78, #93, #94, #96, #236, PR #39, PR #42] |
| Dark-flag follow-ups (W4 family): #206 #215 #216 #219 #220 #225 #229 #230 #231 #232 #234 #237 #238 #240 #245 #248 | Behind default-OFF flags or Ahmed product calls | [issues triage section 6] |
| Arabic verdict prose and i18n follow-ups: #244 #246 #247 #233 #235 | Verdict prose stays English for 1.0 (listing wording covers it) | [#244, #246, #247, #233, #235, BE-08] |
| Perf and ops: #65 #70 #73 #74 #80 #81 #217 #218 #241 #287 #302 | Review traffic is one user; no reviewer path breaks | [issues triage section 6] |
| Test hygiene: #89 #210 #211 #222 #281 #282 #300 #309 #314 #319 #320 #322 | Tests and tidy-ups only | [issues triage section 6] |
| Remaining small items: #203 #221 #224 #259 #260 #261 #262 #263 | Low; no reviewer path breaks | [issues triage section 6] |
| #58 step 2 (gpt-5 defaults) | A model switch is out of launch scope | [#58] |
| LLM provider switch, StoreKit/IAP, iPad, the fourteen session-68b flags | PRD out-of-scope list | [IMPLEMENTATION_PLAN] |

---

## D. DECISIONS REPLY BLOCK

Answer with letters (and the few free-text fields) in one message. A template line is at the end. "(rec)" marks the recommended default.

**Money and infrastructure**

- **D8 - OpenAI billing mode and amount** [RB-23, S3-A1.1]
  - A (rec): prepaid, low cap, now; consider auto-recharge after approval. Amount: ___ USD (the session-69 memo modelled about $76 for review + demo week + month 1; it recommended $100, minimum $50). Consequence: a hard spend cap, but the app goes dark if the balance runs out during review.
  - B: auto-recharge now with alerts (the session-69 memo's advice). Consequence: always available; no hard cap. See conflict G17.
- **SB - Supabase plan** [RB-22, BE-05]
  - A (rec): paid plan before submission. Consequence: no auto-pause during review.
  - B: stay free + a signed-in keep-alive. Consequence: pause risk stays; under U13 a pause is a total compare outage.
- **REPO - repository visibility** [BE-13]
  - A (rec): stay public until a paid GitHub plan is confirmed. Consequence: CI and branch protection keep working.
  - B: private on the Free plan now. Consequence: about 21 CI minutes per run, about 5 days to exhaust 2,000 min; branch protection is dropped.
  - C: upgrade the plan, then go private.
- **DNS - qaren.app** [RB-12, #272, RB-38c]
  - A (rec): attach qaren.app to `qaren-landing` before submission (45-60 min), then SHARE-LINKS fixes the empty token. Consequence: share, referral and universal links work; support@ can be verified.
  - B: submit on the Railway landing URLs; Claude adds an `APP_BASE_URL` override so share links use the Railway host. Consequence: universal links stay dead (harmless to review); no domain work.
  - C: neither. Consequence: every share link a reviewer taps is a Cloudflare 522 page.

**Legal (the eight inputs, minus the answered ones)**

- **D3 - OpenAI data sharing** (= legal input 7) [RB-7, #266, S3-A1.5]
  - A (rec): do not enroll. You turn org data sharing OFF; Claude deletes the toggle, policy section 11 and `select_client_for_user`. Consequence: U3b is M; consistent with the consent sheet.
  - B: keep sharing with a second non-sharing key; every call routed through the toggle; `AI_CONSENT_VERSION` 2 re-asks everyone. Consequence: a larger unit; session-71 research flags conflicts with Apple 5.1.2, KSA IR Art 11(1)(e) and Bahrain PDPL Art 3(2).
- **D5 - publisher and data controller** [RB-19]
  - A (rec): Hussain Aseeri as an individual (+ trade name if any), with a written IP licence or assignment between you. Fastest. Sets the copyright string `2026 <OWNER>`.
  - B: an organization account (needs a D-U-N-S number; weeks).
- **L1 - controller name:** free text (follows D5).
- **L2 - CR number:** free text, or "none" if not a company.
- **L3 - postal address:** free text.
- **L4 - contact e-mails** [RB-38c]
  - A (rec): keep privacy@, support@ and legal@qaren.app (the D14 default); verify delivery (B13).
  - B: give other monitored addresses.
- **L5 - response time:** ANSWERED 2026-10-03 (10 working days for rectification, erasure and objection; 15 for access). No reply needed.
- **L6 - effective date**
  - A (rec): the date U8 is published.
  - B: a fixed date: ___.
- **L8a - lawyer review**
  - A (rec): no blocking review for 1.0; send the U8 draft to counsel in parallel and fold changes into a later revision. Consequence: residual legal risk; Apple does not require counsel review.
  - B: counsel reviews before submission. Consequence: adds days to step 9.
- **L8b - "Beta" label:** ANSWERED 2026-10-03 (no). No reply needed.
- **R296 - audit-log rows of deleted accounts** [#296]
  - A: keep them indefinitely (IP-free after 043) and say so in the policy. Consequence: no 044 purge; weaker under storage limitation.
  - B (rec): purge after N days; the 044 purge ships in DEL-FOLLOWUPS. N = ___ (no source document gives a number; your call).
- **M043 - apply migration 043** [U8b-043, DEL-today]
  - A (rec): apply now (PRECHECK first). Consequence: deletion is full erasure; U8 can say so.
  - B: defer. Consequence: in FK branch B, e-mail, name, demographics, consent and attribution survive deletion, and U8 must say so.
- **M043D - the three 043 privacy defaults** (audit IP nulled, consent timestamps erased, free quota resets on delete-and-re-register) [DEL-043]
  - A (rec): accept as written and reviewed.
  - B: change one or more. Consequence: a 044 unit first.
- **D10 - are re-engagement pushes marketing?** [S3-B-D10, #264]
  - A: not marketing; U8 drops the per-type off-switch promise (ToS line 91). Consequence: no code; the Profile toggle still does not stop every sender.
  - B (rec): not marketing, and every sender honours `notifications_enabled` (PUSH-OPTOUT, S). Consequence: the ToS promise becomes true; lower guideline 4.5.4 risk.
  - C: treat them as marketing (explicit opt-in). Consequence: more copy and code.

**App Store and product**

- **D9 - age rating** [RB-20, LL-8]
  - A (rec, runbook): answer honestly, Override -> 13+, Age Assurance = No (a checkbox is not age assurance).
  - B: Age Assurance = Yes, self-declared (the LL-8 finding's fix text). See conflict G9.
- **D11 - listing localization** [RB-31, RB-17]
  - A: EN + ar-SA, after a native Arabic review of the LISTING-TRUTH redraft.
  - B (rec): EN only for 1.0; add ar-SA in an update. Consequence: no native-review dependency on the path; the app UI still ships in Arabic.
- **D12 / D13 - spelling MYEZ and the Arabic form:** A (rec): confirm as shipped in #257. B: change (a new rename unit).
- **D14 - domain and addresses:** A (rec): keep qaren.app addresses. B: a new domain (renames every address and landing link).
- **D6 - guest mode** [S3-B-D6]
  - A (rec): later. Consequence: none for review; the notes explain the login.
  - B: now. Consequence: reopens anonymous paid calls that U13 closed.
- **D7 - preflight breaker** [RB-25]
  - A (rec): keep OFF (dark flag, scope rule); use it as the incident lever.
  - B: ON at tier >= 2 (an exception to the scope rule).
- **W0 - load flags before review** [RB-14, #71]
  - A (rec): keep OFF until approval (binding scope rule). Consequence: one reviewer Link compare to a black-holed host can freeze the worker 11-12 s; review traffic is one user.
  - B: exception for `ENABLE_OFFLOOP_DNS_RESOLVE` only (the P0), one canary, after funding.
  - C: the full W0 order before submission (runbook A3.2), one canary per flag (about half a day elapsed).
- **CAN - onboarding canary in the store binary** [CL-CANARY, ISS-G3, BE-16]
  - A (rec by the client and issues finders): keep 100 for 1.0 and record the rule change in CLAUDE.md and the canary runbook. Consequence: every new account gets the reviewed 17-step flow.
  - B: set 10 before the production build (the CLAUDE.md rule). Consequence: about 90% of new accounts, including a reviewer who signs in with Apple, get the legacy 6-step flow, which no device has run in months; add it to the device checklist.
- **GOO - if Google sign-in fails on the preview build** [CL-GOOGLE, BE-04]
  - A (rec): hide the Google row for 1.0 (JS constant) and drop the claim from the review notes.
  - B: fix it before the build. Consequence: unknown size; it blocks the build.
- **COPY - the two placeholder lines** [CL-COPY]
  - A (rec): approve Claude's replacement copy (EN + AR, Arabic native review).
  - B: remove both lines entirely.
- **N388 - "388 GCC shoppers helped train this."** [CL-NUMBERS]
  - A: 388 is the real survey respondent count; keep it.
  - B (rec unless you confirm A): reword without a number (ride U-COPY).
- **SPL - if the splash hand-off flashes white on the preview build** [CL-SPLASH-FLASH]
  - A (rec): build the native U-SPLASH unit before the store build. Consequence: one more preview build.
  - B: accept the flash for 1.0.
- **U11 - Sign in with Apple token revocation** [RB-34, LL-9]
  - A (rec, finders): after launch. Consequence: residual rejection risk (E8).
  - B: before submission. Consequence: needs a SIWA key from Hussain and an M unit.
- **DEMO - demo accounts** [BE-06]
  - A (rec): two premium accounts. Consequence: a reviewer who deletes one does not end the review.
  - B: one account + a 20-minute recreate recipe.
- **LIM - #299 per-user limiter before approval:** A (rec): no, post-launch. B: build and activate as a scope exception.
- **PRS - old PRs #39 and #42:** A (rec): close both; re-file #39's two defects as one post-launch issue. B: leave them parked.
- **ISS - close #63 #64 #69 #72 #128 with proofs:** A (rec): close. B: keep open.
- **DENY - permission deny rules:** A (rec): run the script now and again after Claude extends it (idempotent). B: wait for the extended list.
- **PLG - the ten Cowork plugins:** A (rec): disable them (keep legal only if U8 uses it). B: keep.

Reply template (copy, fill the blanks, send):

```
D8=A USD=___  SB=A  REPO=A  DNS=A
D3=A  D5=A  L1=___  L2=___  L3=___  L4=A  L6=A  L8a=A
R296=B N=___  M043=A  M043D=A  D10=B
D9=A  D11=B  D12=A  D13=A  D14=A  D6=A  D7=A  W0=A
CAN=A  GOO=A  COPY=A  N388=B  SPL=A  U11=A  DEMO=A
LIM=A  PRS=A  ISS=A  DENY=A  PLG=A
```

---

## E. REJECTION RISKS that remain when every row is green (ranked)

1. **The backend fails or degrades during review.** Verdicts are never cached. A reviewer's compare calls OpenAI live and runs 20-40 s. A drained prepaid balance or the modelled Tier-1 ceiling (about 5 verdicts/min, MODELLED, not read) gives a failed or degraded result. Guideline 2.1. Mitigation: D8 balance, daily warm-up, the canary [RB-13, RB-23, S3-A1.1, RB-1].
2. **Google sign-in fails on the reviewer's device** although it passed on two test iPhones. It is a first-row button [CL-GOOGLE, BE-04, ISS-G2].
3. **The reviewer does not use the demo account.** Sign in with Apple creates a new free account: 3 lifetime compares, then the limit sheet. With CAN=B it also lands in the legacy onboarding [RB-8, BE-16, ISS-G3]. The reviewer can also delete the demo account [BE-06].
4. **Listing and metadata accuracy (2.3).** Even with LISTING-TRUTH, a reviewer sees Bahrain-only BHD prices, English verdict prose in Arabic mode and hidden (not labelled) estimated prices [BE-03, BE-08, BE-09, RT-13].
5. **Privacy disclosures (5.1.1 / 5.1.2).** Labels versus real flows: caller IPs in the Railway HTTP log; query text in INFO logs until #301 lands; consent stored only on the device [S3-E5, BE-12, #301, U3b scope note].
6. **Infrastructure outage.** Supabase or Railway down means a total compare outage under U13; `/health` has no DB probe [RB-22, BE-05, #81]. A certificate chain outside the 13 pins makes every call fail, and the only alarm is mobile Sentry [CL-PIN].
7. **iPad compatibility testing.** App Review may run the iPhone-only app on an iPad [runbook #9, client checklist row 21].
8. **Sign in with Apple tokens are not revoked on deletion.** Apple's account-deletion page says SIWA apps should revoke. Finders rate it low; the runbook rates it medium [RB-34, LL-9]. See G8.
9. **Forgot password ends outside the app.** The reset e-mail returns to the Site URL until the dark deep-link flag is flipped after the store build [RB-38g, RT-10].
10. **Share links.** With DNS=C every share link is a 522 page [RB-12, #272].
11. **Push guideline 4.5.4.** With D10=A, re-engagement pushes ignore the Profile toggle [#264].
12. **Generic legal text.** Apple may push back on jurisdiction even after U8; L8a=A leaves counsel review for later [CLAUDE.md blocker 2, S3-B-legal].
13. **Event-loop stalls.** With W0=A, one worker and no load flags; a Link compare can freeze the loop 11-12 s [RB-14, #71].
14. **Arabic quality.** AR strings (labels, consent sheet, purpose strings) still need a native review [CL-DEVCHECKS row 16, runbook #30].
15. **A number that reads as invented.** "388 GCC shoppers" if N388=A without a source [CL-NUMBERS].

---

## F. NOT VERIFIED

From the finders (carried as written):
- Every production variable value; quoted from the ledger and CLAUDE.md with dates only [backend].
- Supabase plan, Confirm-email setting, sender, templates and built-in sender limits [backend BE-07].
- The live `users.id` FK branch (A or B) and any `comparison_id` FK; PRECHECK decides [backend DEL-today].
- qaren.app 522 today (the orchestrator's last measurement only) [backend, client].
- `npm audit` at `845ece15` after the #279 bumps, and whether any high/critical advisory is in a direct dependency [backend CL-npm, client].
- Whether `dependency-audit` is one of the five required checks [backend].
- Google Sign-In on any build since session 54 [backend BE-04, client CL-GOOGLE, issues ISS-G2].
- The client half of "photograph one and type the other" [backend].
- Arabic listing text quality; AR legal page content beyond the draft markers [backend].
- Railway HTTP log retention; whether `price-warmer` redeployed on the 2026-10-03 key rotation [backend].
- The Sentry DSN-to-project mapping; any EAS dashboard `EXPO_PUBLIC_SENTRY_DSN`; Release Health sessions [client].
- That `comparison_wall_time` fires on a not-found Results visit (read, not executed) [client].
- Screenshot pixel sizes against the live ASC help page [client].
- The source of the "388 GCC shoppers" figure [client CL-NUMBERS].
- EAS dashboard environment variable names per environment [client].
- Device-only behaviour: white flash, mark sharpness, FormData re-send, RTL reload [client].
- Whether `ENABLE_REENGAGEMENT_PUSHES` is set in production [issues #284].
- Whether #226's `str(e)` reaches the client payload or only `search_logs` [issues].
- How many smoke accounts exist in production [issues #303].
- Whether PR #39's dose cache-key collision still exists on main [issues].
- #311's five except-arm anchors re-read one by one (accepted because the diff since c60926f8 is docs-only) [issues].
- #76, #77, #78, #93, #94 classified from their bodies [issues].
- Whether the permission deny rules block when probed live, and whether Read deny rules bind Bash/PowerShell readers [config R1, CFG-05].
- User-scope MCP entries (railway, sentry) and Supabase auth state [config].
- The account skills' content (R23); where bypass mode is set; exact skill-listing size; token figures are chars/4 [config].
- No pytest, jest, tsc or eslint run by any finder (read-only audits).

Added by this synthesis:
- The 4-6 working-day estimate and the 12-16 owner hours are arithmetic over the finders' sizes, not measurements. EAS build duration and Apple processing time are NOT VERIFIED.
- Which "388" occurrence #269 removed. The session-69 state says it is gone; `en.json:623` still renders it (synth read; see G6).
- Apple's current wording on SIWA revocation was not re-read today; the quoted line comes from the LL-9 evidence of 2026-09-29.

---

## G. CONFLICTS (finder vs finder, and document vs code; none resolved silently)

| # | Conflict | Sides | Stronger evidence | Effect on this list |
|---|---|---|---|---|
| G1 | Does the onboarding canary affect the App Review reviewer? | client: no, the demo account is onboarded [CL-CANARY]. issues: below 100 "the reviewer included" gets the legacy flow [ISS-G3]. backend: "most reviewers see the old onboarding" [BE-16] | Both partly right. The client reading holds for the demo account (`preferences_completed` true skips onboarding; backend demo section agrees). The bucket is keyed on `user.id` (features.ts:108-110, synth read), so a reviewer who signs in with Apple gets a new account and, at 10, about a 90% chance of the legacy flow. The client's "not affected either way" is too strong | Decision CAN; risk E3 |
| G2 | Severity and tier of #295, #301, #303, #315 | issues: medium, PRE-LAUNCH-SHOULD. backend: low. client: #295 low. config: R11/#315 medium | Same facts on all sides; the split is judgement. Backend's #303 analysis (an attacker gains only the free tier `/auth/register` gives anyone) is the more detailed. All four are cheap | All four in SHOULD; none on the critical path |
| G3 | #299 per-user limiter | issues: PRE-LAUNCH-SHOULD behind a new default-OFF flag. backend: low, post-launch | Backend, under the binding scope rule: a flag that cannot be activated before approval buys nothing pre-launch | POST-LAUNCH; decision LIM |
| G4 | #304 whitespace admin key | backend: fold into OBS-311 now. issues: post-launch rider | Equal; it is a one-line fix | Rider of the OBS unit (SHOULD) |
| G5 | W0 load flags before submission | backend: owner step 6, before submission [RB-14, OWNER-6]. issues: activation is a dark-flag flip barred before approval [#71] | The PRD out-of-scope list is binding ("any dark flag activation"). The runbook A3.2 step predates it. U13's activation is a precedent for an explicit owner exception | POST-LAUNCH by default; decision W0 |
| G6 | "388 GCC shoppers" | session-69 state 4.4 U6 row: "388 ... gone" via #269. client: still rendered [CL-NUMBERS] | Code. `en.json:623` "388 GCC shoppers helped train this." is rendered at `Step12CohortProof.tsx:116` (synth read). Which 388 #269 removed is NOT VERIFIED | Decision N388; risk E15 |
| G7 | The canary script's pass rule | session-69 state section 2 says the script enforces a real verdict. backend: it passes a degraded 200 [BE-01] | Code: `verify_after_credits.py:38` (`has_verdict` = verdict or `overview.winner`), `:67` (pass = 200 + success + has_verdict), `:68` (stream: any event) (synth read) | BE-HARNESS is MUST and runs before the funding canary |
| G8 | Sign in with Apple revocation severity | runbook row 34: medium. backend RB-34: low, optional. LL-9 `severity_final`: low after refuters | The refuted, verified finding (low) is the stronger record. Apple's page says SIWA apps "should" revoke (LL-9 evidence, 2026-09-29) | POST-LAUNCH; decision U11; risk E8 |
| G9 | Age Assurance answer | runbook D9: No. LL-8 fix text: Yes (self-declared) | Not settled by evidence; the runbook is the later synthesis and states its reason (a checkbox is not age assurance) | Decision D9 (A = runbook) |
| G10 | The `eas.json` submit block | runbook: "missing". client and backend: present but empty | Code: `eas.json:23-25` `"submit": {"production": {}}` (synth read) | U10 fills the existing block |
| G11 | Review-notes deletion path | runbook section 6: "gear icon -> Edit profile -> Delete account". client: the gear opens Edit profile itself | Code: `ProfileScreen.tsx:366` navigates straight to `EditProfile` (synth read) | LISTING-TRUTH corrects it |
| G12 | `/admin/costs` as the launch-week cost watch | backend RB-35: Ahmed reads `/admin/costs` twice a day. issues #66: it reports OpenAI cost 0 (`admin_routes.py:130` selects an absent column) | issues (file:line) | COST-METER in SHOULD, before funding |
| G13 | CLAUDE.md L21 "U4d in flight" | CLAUDE.md vs merged #307 [CFG-03] | Git: #307 (72b13bc5) is an ancestor of `845ece15` | DOCS-CONFIG fixes L21 |
| G14 | The anonymous canary and warm-up recipes | runbook A1.8 curl and E2 "unauthenticated" vs U13 active since 2026-10-03 14:23 [BE-02] | Production: an anonymous compare returns 401 (orchestrator, 2026-10-05) | BE-HARNESS rewrites both recipes |
| G15 | Is the qaren.app attach needed before submission? | runbook A4: optional before submitting. client: high, share links on the reviewer path are 522 | Both facts hold; the split is judgement | Decision DNS (A recommended) |
| G16 | Mobile Sentry framing | backend: "never observed working" (OPEN-AHMED, high). client: the code path should deliver; unproven, not broken | No evidence conflict. Both rest on 0 events and 0 mobile requests | One device test (B14) settles it |
| G17 | OpenAI billing mode | session-69 decision memo: auto-recharge + spend alerts, not hard caps. session-71 state: "prepaid, low cap, until U13's flag is on" (U13 is now on). backend RB-23: prepaid + alerts | Not settled by evidence; it is an owner call. The session-71 wording ties the cap to a condition that is now met | Decision D8 (A = prepaid now, the more conservative) |

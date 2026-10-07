# MYEZ: Ahmed's tasks to reach "Submit for Review" (session 73, 2026-10-07)

Consolidated from the session-72 plan (`../2026-10-05-session-72-state/IMPLEMENTATION_PLAN_S72.md`), the punch list (`readiness/LAUNCH_PUNCH_LIST.md`, sections B and D) and the legal form (`specs/U8_INPUT_FORM_AHMED.md`). Only you can do these; every Claude unit that waits on one of them is named. Nothing here flips production without your word, and no key or password ever goes into a chat.

## 0. Where the code side stands (so you know what is parallel)

- Merged and live: U13 (sign-in required for every compare), U8b (account deletion, code), U8d (Sentry text channels), the Phase A repo tooling. `main` = `1156f03c`.
- Running now: T0b Phase B (secret scanning: hook, gitleaks config, the CI `secret-scan` job) in its last fix-and-adversary round; the session-72 docs PR #326 (checks re-triggered).
- Ready to start, waiting for YOUR APPROVAL (they were not in the session-71 plan): U3c, BE-HARNESS, U13e, CLIENT-TRUTH, DOCS-CONFIG, COST-METER, SSRF-PHARMACY (one line each in section 2).
- Written, waiting for your inputs: U8 (legal redraft), U3b (AI-consent toggle), LISTING-TRUTH, U10.

## 1. Money and keys (do today; no dependency)

### 1a. OpenAI (about 30 minutes, platform.openai.com)

1. Settings -> Billing: add prepaid credit. Decision D8: A = prepaid now (recommended $100, minimum $50; the session-69 memo modelled about $76 for review week + demo week + month 1) or B = auto-recharge with alerts. Fund EARLY: a small prepayment in submission week can leave the account on the lowest rate tier (not verified against OpenAI's current tier rules).
2. Settings -> Limits: read the usage tier and the TPM / RPM for the model in use; send me the tier name only.
3. Project -> Budget: set a monthly budget with alerts at 50 % and 80 %.
4. Data controls: turn organisation data sharing OFF (decision D3 = A, recommended). Read whether Chat Completions storage is on by default for the project and tell me yes/no (unit U3c then pins `store=False` in code regardless).
5. API keys: create a NEW project key. Put it into Railway on EVERY service that holds the variable name (`web` and any worker that has `OPENAI_API_KEY`) from your own terminal or the Railway dashboard. Tell me "new key in place" with the variable NAME only.
6. Tell me when 1-5 are done: I run the post-funding canary and read the JSON against the runbook A1.8 rule (until BE-HARNESS lands, I read it by hand).
7. After the canary passes: revoke the OLD key (API keys page). I re-run the canary.

Unblocks: the canary, the review warm-up, real-verdict device checks, demo-account history, screenshots. Sentry `python-fastapi` has shown the 429 `credit_balance_exhausted` family since 2026-10-03; no compare has reached a provider since.

### 1b. Supabase (about 25 minutes)

1. Billing: move to a paid plan (decision SB = A), so the project never auto-pauses during review (under U13 a pause is a total compare outage).
2. Authentication -> Providers -> Email: read whether "Confirm email" is ON; Authentication -> Email Templates: read the sender name/address and whether the templates still say "Qaren"; send me the three readings (I cannot read them: the Supabase MCP is unauthenticated).
3. Authentication -> URL Configuration -> Redirect URLs: add `qaren://reset-password`.
4. If "Confirm email" is ON: decision SMTP (custom SMTP or not).

### 1c. Railway, GitHub, Sentry, deny rules (about 40 minutes)

1. Railway: confirm the paid plan, the card and the usage cap; before 2026-12-01 mirror the config-as-code settings (start command, healthcheck, 30 s draining, warmer watch paths) into each service's dashboard settings.
2. GitHub: Settings -> Billing and plans: read the plan, so decision REPO (stay public / go private) can be made with CI minutes in mind.
3. Sentry (org `qaren-rr`): enable "Prevent Storing of IP Addresses" on BOTH projects (`python-fastapi`, `react-native`). U8d is live, so this is the last Sentry owner setting.
4. Permission deny rules, in a real terminal (idempotent; run again after DOCS-CONFIG extends the list):

```bash
python C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-03-session-71-state/scripts/apply_audit_batch_a.py --apply
```

## 2. Decisions and approvals (one chat message; about 45 minutes)

### 2a. Approve or reject the seven new units

| Unit | One line | Why it is on the path |
|---|---|---|
| U3c | `store=False` on every OpenAI call (AST pin) + the referral push never shows an email prefix | makes two privacy-policy sentences true; backend only; no decision needed |
| BE-HARNESS | the post-funding canary script fails on a degraded 200; a signed-in warm-up script for review week | the current canary passes on a broken verdict; every anonymous runbook recipe now returns 401 |
| U13e | `/url/detect` behind the admin guard (decision W0 = guard) | anonymous callers can freeze the single worker 11-12 s per request; no app screen calls it |
| CLIENT-TRUTH | Share sheet: remove the "+1 Deep Review credit" reward, the "2x deeper" toast, the placeholder link; the two placeholder lines; a "not medical advice" line on supplements; drop the clipboard read on Register; "retail sources" plural; clear recent searches on deletion; privacy-manifest purposes | App Review guidelines 2.3.1(a), 2.1(a), 1.4.1; must be in the store binary |
| DOCS-CONFIG | CLAUDE.md stops telling agents to copy `.env`; stale lines fixed; the deny-rules script extended | agent safety for the remaining units |
| COST-METER | `/admin/costs` reads the real cost field (#66) | launch-week OpenAI spend is shown as 0 today |
| SSRF-PHARMACY | pharmacy domains matched by parsed hostname, fetched through the redirect-validating guard (#79) | an SSRF hole on the price path |

Reply: `UNITS: all` or the names you reject.

### 2b. The decisions block (section D of the punch list)

Copy, fill, send. "(rec)" = the recommended default, already pre-filled:

```
D8=A USD=___  SB=A  REPO=A  DNS=A
D3=A  D5=A  L1=___  L2=___  L3=___  L4=A  L6=A  L8a=A
R296=B N=___  M043=A  M043D=A  D10=B
D9=A  D11=B  D12=A  D13=A  D14=A  D6=A  D7=A  W0=A
CAN=A  GOO=A  COPY=A  N388=B  SPL=A  U11=A  DEMO=A
LIM=A  PRS=A  ISS=A  DENY=A  PLG=A
SHARE=A  MED=A  CLIP=A  TERR=A  SMTP=___
```

The new ones (SHARE, MED, CLIP, TERR, SMTP): SHARE = remove the Deep Review claims for 1.0; MED = the "not medical advice" line; CLIP = drop the clipboard read on Register; TERR = GCC storefronts only for 1.0 (no EU trader declaration); SMTP = custom SMTP if Supabase "Confirm email" is on (answer after 1b).

### 2c. The legal form (`specs/U8_INPUT_FORM_AHMED.md`, 12 items) plus three additions

Answer by item number. The additions from the adversarial review (C17, C18, C20):

- the EXACT legal name as it appears on the Apple Developer membership (the seller on the App Store);
- whether a written IP licence or assignment exists between you and the account holder (Hussain), or should be drafted;
- D14 confirmed (keep the `qaren.app` addresses) and whether a data-protection guardian or officer was appointed (default: no).

Items that need a real fact: 4 (postal address), 5 (do `privacy@` and `support@qaren.app` deliver: send one test mail to each), 9 (hosting regions from the Supabase, Railway and Upstash pages, optional), 10 (retention period for logs not tied to an account; recommended B = 12 months).

Unblocks: U8 (both documents, EN + AR, the landing pages), U3b, LISTING-TRUTH, 043 apply, DEL-FOLLOWUPS.

## 3. Migration 043 (two sittings in the Supabase SQL editor; about 45 minutes)

1. Sitting 1: run `APPLY_043_1_PRECHECK.sql` from `../2026-10-03-session-71-state/` and send me the grid. I read it against the STOP rules of PR #290 (FK branch A/B, #294 shapes).
2. Sitting 2 (after my reading): `ONE_PASTE`, then `POSTCHECK`, then `BACKFILL` only if section 9 c or d > 0. Send me the POSTCHECK output.

Unblocks: the deletion paragraph of U8 ("delete your account and its data" becomes true), #303, 044.

## 4. Testers and the first mobile Sentry signal (15 minutes, today)

A tester opens the CURRENT app (OTA `e2bde9c9`) signed in and runs one compare. Then in Safari open `qaren://comparison/sentry-check`, accept "Open in MYEZ", wait 2 s, close Results. Mobile Sentry has NEVER shown an event; this decides whether unit U-SNT is needed. I check Sentry `react-native` and the Railway HTTP log for mobile-UA requests afterwards.

## 5. The Apple session with Hussain (about 1-1.5 hours, his Individual team)

1. Pending agreements accepted in App Store Connect (Account Holder).
2. API key: Users and Access -> Integrations -> App Store Connect API: a Team key with Admin role; the `.p8` stored OUTSIDE the repo; record Key ID and Issuer ID (never in chat).
3. App record: New App, iOS, name `MYEZ - Compare Smart` (or `MYEZ`), English, bundle `com.qaren.app`, SKU `qaren-ios`. Send me the NUMERIC Apple ID (unit U10 pins it).
4. Credentials, in a real terminal from `SmartCompareApp`: `eas credentials -p ios`: production profile, reuse the distribution certificate, generate the App Store profile, Push = yes, upload the ASC key, sync capabilities (Sign in with Apple, Associated Domains, Push). In the EAS dashboard confirm `SENTRY_AUTH_TOKEN` exists in the production environment (or set `SENTRY_ALLOW_FAILURE=true`).
5. Territories: GCC only for 1.0 (decision TERR).

## 6. Domain and mail (per decision DNS; 45-60 minutes)

DNS = A: attach `qaren.app` to the `qaren-landing` Railway service, fix the Cloudflare record behind the 522, then Cloudflare Email Routing for `support@`, `privacy@`, `legal@` with one test mail each. I verify `https://qaren.app/.well-known/apple-app-site-association` returns 200 JSON without a redirect. (DNS = B: submit on the Railway landing URLs; Claude adds `APP_BASE_URL`.)

## 7. Builds and devices (after the client units merge)

1. Optional today: preview OTA from main (`npm ls` first, then `eas update --branch preview --clear-cache`), smoke on one phone, then the OTA column of the client checklist.
2. Preview BUILD from main containing CLIENT-TRUTH and U3b (`eas build -p ios --profile preview`). Delete the old app on both iPhones, install, run the NEW-binary checks: Apple, Google and email sign-in; launcher icon; launch-screen hand-off (fresh install and after an OTA); camera and photo prompts in EN and AR; no mic or Face ID prompt; home-screen name; pinning active; a Sentry event on the release transport. Google sign-in has been recorded as failing since session 54 and was never re-verified: decision GOO if it fails.
3. Two demo accounts: register in the app, confirm the email if required, complete onboarding once, set `users.subscription_tier = premium` in the table editor; passwords only in App Store Connect. Never called "premium" in the review notes (they are "a review account with a raised daily limit").
4. Production build from the release commit (`eas build -p ios --profile production`), then `eas submit -p ios --profile production --latest`, internal TestFlight smoke on the exact binary, the processing email (send me the ITMS lines), one Expo test push.
5. Warm-up within 24 h of submission and daily during review (after BE-HARNESS lands): `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python scripts/review_warmup.py`; only passing pairs go into the review notes.

## 8. Listing and submission

1. Six screenshots on a physical iPhone (6.9" or 6.5" set): Home with two products, Results winner card, dimension bars, confidence pills, camera framing two products, History with 3+ entries. No splash, sign-in, loading or limit sheet. I resize and check the pixel sizes.
2. Landing redeploy in the same hour as the U8 merge: `railway up landing --path-as-root -s qaren-landing -d`.
3. App Store Connect fields: the LISTING-TRUTH text, App Privacy row by row from `docs/privacy-data-inventory.md` (Tracking = No), age questionnaire then Override -> 13+ (D9), copyright `2026 <owner per D5>`, Privacy and Support URLs, review notes, demo credentials, "Manually release this version".
4. Submit for Review; backend merge freeze until approval except reviewer-path fixes.
5. After approval: `APP_STORE_URL` on `web`; the redirect Worker after I replace `idTBD`; JS hotfixes go to `--branch production`.

## 9. Off the launch path (whenever)

Disable the ten Cowork plugins in Claude Desktop (keep `legal` only if U8 uses it); disable unused claude.ai connectors; update `qaren-brand-voice` to MYEZ; decide on `effortLevel: xhigh`, the codex plugin and typescript-lsp; close PRs #39 / #42 and issues #63 #64 #69 #72 #128 per decisions PRS / ISS.

## Order that unblocks the most, soonest

1a OpenAI -> 2a + 2b + 2c (one message) -> 4 testers -> 1b Supabase -> 3 migration 043 sitting 1 -> 5 Apple session -> 1c the rest -> 6 domain -> 7 builds -> 8 listing. The elapsed estimate from the decisions reply AND the Apple session is 4 to 6 working days (EAS build and Apple processing times not verified); your hands-on time about 12 to 16 hours.

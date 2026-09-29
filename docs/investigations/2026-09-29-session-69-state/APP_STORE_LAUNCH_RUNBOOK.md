# MYEZ iOS: App Store launch runbook

Repo `smartcompare` main `eed4ee10`, written 2026-09-29. Two finding sets both used the `BP-` prefix. In this runbook, **BLD-BP-xx** means the build-pipeline findings and **PRD-BP-xx** means the backend-prod findings. All other ids are as filed. When findings were merged, the row takes the highest `severity_final` among them.

---

## 1. Can we submit today?

**No.** The feature a reviewer will test first, comparing two products, does not work right now. OpenAI is returning `429 insufficient_quota`, so every compare path fails (RT-1, PRD-BP-01):

* **Text compare:** fails with 400 or times out. One live pass instead got a 200 with an empty verdict, no prices and no specs.
* **Camera:** returns a 500 and lands in a "Still gathering prices / Tap to retry" loop.

Guideline 2.1 asks you to "turn on your back-end service!".

Four more things block review even with a working backend:

* A subscription paywall with prices and a trial whose buttons only say "Coming soon", plus invented "5,000+ shoppers" and "4.8" ratings. It can be reached from Profile in one tap (LL-2, RT-2).
* The in-app privacy policy and terms start with "DRAFT — This document is a template" (RT-3, LL-1).
* The app icon is the Expo placeholder art (EXPO-01).
* There are no App Store screenshots (SA-01).

Nothing iOS has ever been signed for the App Store. There has been no production build, no `eas submit`, and there is no App Store Connect record. The Apple team is Hussain Aseeri's Individual account 8K562M549D, so he, or an API key he creates, is needed once (BLD-BP-02).

**On "OpenAI or Anthropic credits":**

* The backend calls only OpenAI, through `openai.AsyncOpenAI`: `openai_service.py`, `llm_provider.py`, `model_config.py`. There is no Anthropic SDK in requirements (PRD-BP-01 votes; backend-prod notes).
* Adding **OpenAI** credits is what makes the app work.
* Anthropic credits do nothing for the app unless the code is changed. The change would be provider code plus a full re-test. The privacy policy and the consent text would also have to name the new provider (legal-listing notes: `OPENAI_BASE_URL` at `llm_provider.py:128`).
* Do not switch providers for launch.

---

## 2. Ranked blocker table

| # | Severity (final) | Owner | Title | Fix | Effort | IDs |
|---|---|---|---|---|---|---|
| 1 | **blocker** | ahmed | OpenAI unfunded, so every compare path fails (text 400 / timeout / empty verdict; camera 500 loop) | Fund OpenAI. Mint a **new** key after Claude's U1 is deployed. Set it on Railway with the retry settings. Canary with the strict assertions in §3 A1. | 30 min + 10 min canary | RT-1, PRD-BP-01 |
| 2 | **blocker** | claude | Fake subscription paywall: BHD plans, "Start My 3-Day Free Trial", Restore/Terms/Privacy all "Coming soon", hard-coded 5,000+ and 4.8. Reachable from Profile, the Home header counter and 8 quota paths | Replace it with an honest "daily free limit reached" sheet with no prices, trial or ratings. Remove the Profile upgrade row. Ahmed drops "Premium subscribers" from ToS §12. | 2–3 h + jest | LL-2, RT-2, SA-05 |
| 3 | **blocker** | either | Privacy/Terms say DRAFT, dated March 26, 2026, both in the app (LegalScreen reads `/api/v1/legal/*`) and on the landing pages (EN + AR) | Ahmed answers the 8 legal inputs in §3 B. Claude rewrites both .md files, `legal_routes.py` `last_updated`, `TERMS_VERSION` (consent.ts + consent_service.py) and the 4 landing HTML pages, then deploys backend and landing. | Ahmed 30 min; Claude 2–3 h | RT-3, LL-1 |
| 4 | **blocker** | either | Icon/splash/adaptive are the create-expo-app placeholder. Changing the bytes of the same image is **not** a fix, because reviewers judge pixels | Ahmed approves real brand art (e.g. emerald #10B981 Qaren mark or wordmark) as an opaque 1024² PNG. Claude writes 3 distinct files and sets `ICON_ART_SUPPLIED=true` (nativeBundle.w37.test.ts:233). Must land before the production build. | 1–2 h after art | EXPO-01, SA-02 |
| 5 | **blocker** | ahmed | No App Store screenshots. The 22 design PNGs are 920×1840 mock-ups and cannot be used | Once credits are live, capture 5–6 real flows on a physical iPhone. Claude resizes and strips alpha. If iPad stays on, a 13" set is also needed. | ~½ day | SA-01 |
| 6 | high | ahmed | No App Store signing, provisioning profile, ASC API key or ASC app record. The Individual team means Hussain's login or his API key is required, and adding Ahmed as an ASC user does not give certificate rights | See §3 C. | 1–2 h with Hussain once | BLD-BP-02, EXPO-02, EXPO-03 |
| 7 | high | either | Queries and photos go to OpenAI with no disclosure or explicit permission (5.1.2(i)). The "Help improve AI quality" opt-out does nothing (`select_client_for_user` has 0 callers). UI default OFF vs server default ON. Policy §11 promises an opt-out that doesn't work | Ahmed decides **D3**. Claude adds a one-time AI-processing consent sheet naming OpenAI before the first compare or scan, plus a camera pre-sheet, and removes or wires the toggle. | M | PM-1, LL-4, RT-5, PM-2 |
| 8 | high | ahmed | Login-gated app: review needs a demo account. A free account gets 3 compares on day 1, then the paywall. `FREE_TIER_DAILY_LIMIT` is dead config | Create a confirmed, onboarded email/password account. Set `users.subscription_tier='premium'` (10 per day, 70 per month). Name the account features in the review notes (5.1.1(v)). | 20 min after credits | LL-3, RT-4, PRD-BP-06 |
| 9 | high | either | `supportsTablet: true` means the portrait UI rotates on iPad, 13" screenshots are required, and iPad support cannot be dropped after it ships | **D1**, recommended A: set `supportsTablet:false` for 1.0.0. One-line change, native, in the pre-build config unit. | 5 min | EXPO-04, SA-03, BLD-BP-09, LL-12 |
| 10 | high | either | `microphonePermission:false` removes `NSMicrophoneUsageDescription`, but expo-camera still links audio APIs. Likely ITMS-90683 at upload | Set a specific, honest mic string on expo-camera and expo-image-picker before the production build. Update the W3-7 test. | 15 min | EXPO-07 |
| 11 | high | claude | Privacy policy leaves out demographics, device fingerprint, country and push token. The processor list leaves out Expo push, Bright Data, Firecrawl, Scrape.do, Cloudflare and YouTube. No equal-protection clause. No named controller | Fold into row 3's redraft. | ~1 h | LL-5 |
| 12 | high | either | The ASC URL plan uses qaren.app, which returns a Cloudflare 522. The fallback is a JSON endpoint and a mailto. Universal links and every share link (`qaren.app/c/…`) are dead, and the landing site has no `/c/` or `/r/` pages | Use the Railway landing URLs (§6). Ahmed attaches qaren.app to the landing service. Claude adds `/c/*` and `/r/*` fallback pages. | 15 min URLs; 30 min DNS; 1 h pages | LL-7, SA-07, EXPO-06, RT-8 |
| 13 | high | either | Verdicts are never cached, so OpenAI must stay funded through the whole review window. The price cache lasts 24 h | Warm-up plan in §3 E; re-warm daily. | 15 min/day | RT-6 |
| 14 | high | ahmed | A 24 s event-loop stall on the single uvicorn worker. The W0 load flags, including the P0 off-loop DNS, are unset | Flip the W0 flags in the documented order, one canary each (§3 A3). Claude root-causes any stall that remains with `DEBUG_STAGE_TIMINGS`. | ~½ day | PRD-BP-05 |
| 15 | medium | either | Sign in with Apple buttons have no Apple logo (Login, Register, onboarding Step16). The Login row is narrower than 140 pt | Use `AppleAuthenticationButton` (CONTINUE, BLACK), full width, on all 3 screens. | 2–3 h | LL-10 |
| 16 | medium | claude | Onboarding says "we never share your budget", but the verdict prompt sends the budget to OpenAI | Remove "Your budget" from en, ar and the defaultValue at Step05Trust.tsx:99. | S | PM-3 |
| 17 | medium | either | The ASC description draft advertises COMING SOON features (voice doesn't exist), "authorized retailers", and a one-photo camera claim that isn't true | Use the §6 text. | 30–45 min | SA-04, LL-11 |
| 18 | medium | either | The checklist still points to the May nutrition-label draft, which contradicts the enforced manifest | Repoint to `docs/privacy-data-inventory.md` and mark the draft SUPERSEDED. Ahmed fills ASC from the inventory. | S + 30 min | PM-4 |
| 19 | medium | ahmed | Publisher identity: the seller will be Hussain Aseeri (Individual), but the policy and ToS name only "Qaren" | **D5**. | decision | LL-6, SA-11 |
| 20 | medium | ahmed | The age rating "12+" no longer exists | Answer the questionnaire honestly, then use Override → 13+ to match the ToS minimum age. | 15 min | LL-8, SA-08 |
| 21 | medium | claude | Certificate pins match only ISRG Root X2 in today's chain. YE2 and Root YE are unpinned, and pin failures are never reported | Add YE2 and Root YE (plus YE1/YE3/YR*/Root YR), fix the stale comment, send pin errors to Sentry. | 1–2 h | BLD-BP-01 |
| 22 | medium | ahmed | Supabase free-plan auto-pause (it has happened once). `/health` never touches the database | Move Supabase to a paid plan, or add a signed-in keep-alive (`/api/v1/usage/status`). `/app/version` and `/legal` do not touch the DB. | 10–20 min | PRD-BP-07 |
| 23 | medium | ahmed | No app-level dollar cap on OpenAI (`MAX_MONTHLY_COST` is dead config) | Set a project budget and alerts, and decide auto-recharge vs prepaid (**D8**). | 10 min | PRD-BP-08 |
| 24 | medium | ahmed | Retry settings unset (6 attempts per verdict chain). The SSE tail is unbounded (the app uses REST by default) | Set `OPENAI_MAX_RETRIES=1` and `OPENAI_FALLBACK_MAX_RETRIES=0` together with the new key. | 10 min | PRD-BP-03 |
| 25 | medium | ahmed | Outage errors blame the user's input | **D7**: breaker ON only at Tier ≥2. Claude adds an `LLM_UNAVAILABLE` copy key. | 2 min + 1 h | PRD-BP-04, RT-1 |
| 26 | medium | either | After launch, OTAs must go to `--branch production`, but CLAUDE.md:598, the runbook and CI all say never to | Rewrite the rule in the PR that records the first production build. | S | BLD-BP-05, EXPO-11 |
| 27 | medium | ahmed | Push needs an APNs key in EAS credentials | Confirm or create it in the §3 C4 session. Send one test push to TestFlight. | 10 min | EXPO-05 |
| 28 | medium | claude | expo patch drift (6 native packages). Orphan react-native-gesture-handler | Apply the patches, exclude react-native-svg, uninstall gesture-handler (one unit). | 1 h | BLD-BP-03, EXPO-09, BLD-BP-07 |
| 29 | medium | ahmed | No iOS build since 2026-07-04. Pods are unlocked | Run a preview build from the release commit before the production build. | 2 build cycles | BLD-BP-06 |
| 30 | medium | claude | No Arabic bundle localization. Permission prompts and the home-screen name are English-only | Add `supportedLocales ["en","ar"]` and `locales.ar` (display name قارن + AR purpose strings, native review). | 30 min | EXPO-10, SA-10 |
| 31 | medium | claude | No ar-SA listing. The keyword limit is 100 **bytes** | Paste the AR block in §6. | drafted | SA-06 |
| 32 | medium | claude | Trending tap ignores the pair. The "view counts" are invented | Prefill the pair and run it; drop the counts. | 1–2 h | RT-7 |
| 33 | medium | claude | A wrong password shows "Request failed with status code 401" | Map the status to i18n keys. | 1 h | RT-9 |
| 34 | medium | either | Sign in with Apple tokens are not revoked on account deletion | Ahmed creates a SIWA key. Claude adds `authorizationCode` handling and `/auth/revoke`. | 3–4 h | LL-9 |
| 35 | medium | ahmed | Bright Data (4,500 per month) is the only live search budget | Watch `/api/v1/admin/costs` twice a day in launch week. | 10 min/day | PRD-BP-09 |
| 36 | medium | ahmed | One shared 10-per-minute limiter bucket | Keep #114 OFF. Soft launch. Watch the 429 count. | monitoring | PRD-BP-10 |
| 37 | medium | ahmed | Railway paid plan and card. Config-as-code deprecated on 2026-12-01 | Confirm billing. Mirror the settings into the dashboard before December. | 10 min | PRD-BP-11 |
| 38 | low | mixed | EXPO-08 Face ID string · EXPO-12 Sentry `SENTRY_ALLOW_FAILURE` · PM-5 CustomerSupport type · PM-6 ProductPersonalization purpose · PM-7 post-build privacy report · PM-8 IP triggers in the inventory · LL-13/RT-11 test support@/privacy@/legal@ · LL-14 AR legal endpoint · BLD-BP-04 submit block · BLD-BP-08 gate list · BLD-BP-10 `APP_STORE_URL` + `idTBD` · RT-10 reset deep link · RT-12 push prompt at login · RT-13 Bahrain-only note · RT-14 first-launch RTL · PRD-BP-02 key-suffix log line · PRD-BP-12 `DAILY_4O_CAP` · PRD-BP-13 stale comment · SA-09 keywords | see §3 and §4 | S each | as listed |

---

## 3. Ahmed does (in this order)

### A. Money and backend (today)

**A1. OpenAI** (RT-1, PRD-BP-01/03/08, LL-4)

1. OpenAI dashboard → **Settings → Limits**. Record the tier and the gpt-4o / gpt-4o-mini TPM in `docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md` §1. At Tier 1 the verdict step allows about 4.4–5.2 compares per minute.
2. **Settings → Billing**: add prepaid credit that covers at least the review window.
3. **Decision D8:** choose auto-recharge (keeps the app available) or prepaid-only (hard spending cap).
4. On the project, set a monthly budget with email alerts at 50% and 80%.
5. **Decision D3 (recommended A):** turn **off** the organization's data-sharing setting in OpenAI's data controls. The exact label wasn't checked.
6. **Wait** until Claude's U1 (the log-line fix) is merged and deployed. Then create a **new** project key.
7. Railway → `web` → Variables, in **one** change (never print the value):
   * `OPENAI_API_KEY=<new key>`
   * `OPENAI_MAX_RETRIES=1`
   * `OPENAI_FALLBACK_MAX_RETRIES=0`
8. Canary:
   * Run `python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py`.
   * Then run the app-shaped REST compare:
     ```
     curl -s -m 60 -G 'https://web-production-58776.up.railway.app/api/v1/text/compare' \
       --data-urlencode 'product_a=iPhone 15' --data-urlencode 'product_b=Samsung Galaxy S24' \
       --data-urlencode 'region=bahrain'
     ```
   * `success:true` alone does **not** count as a pass (RT-1). A pass requires all of:
     * no `comparison.error`
     * `specs` non-empty
     * at least one price `amount` non-null
     * pros and cons present
     * no 429 in the Railway log
   * Then test one camera compare from the phone.
9. Revoke the old key.

**A2. Supabase** (PRD-BP-07, RT-10)

1. Move the project to a paid plan so it doesn't auto-pause.
2. Authentication → URL Configuration → Redirect URLs: add `qaren://reset-password`.
3. After the production build is live, set `ENABLE_PASSWORD_RESET_DEEP_LINK=true` on Railway. Send one test reset.

**A3. Railway `web`** (PRD-BP-05/04/11/10)

1. Billing: confirm a paid plan and a valid card, with any usage cap set well above the expected launch spend.
2. W0 flags: one per change, with a canary after each. The canary is 3 app-shaped compares, then read `/health` and check `loop_lag_max_60s_ms` is under 1000:
   1. `ENABLE_OFFLOOP_DNS_RESOLVE=true`
   2. `ENABLE_PRICE_PARSE_OFFLOAD=true`
   3. `ENABLE_SUPABASE_CLIENT_REUSE=true`
   4. `ENABLE_UPSTASH_BOUNDED_TRANSPORT=true` (needs a restart)
3. Optional: `ENABLE_FULL_STREAM_DEADLINE=true`, then `ENABLE_PREVERDICT_DISCONNECT_ABORT=true`. Keep `ENABLE_HONEST_PARTIAL_SCORING` **OFF** (CLAUDE.md:443).
4. **Decision D7:** `ENABLE_LLM_PREFLIGHT_BREAKER=true` only if the tier is ≥2. Otherwise keep it as the lever for an incident.
5. **Keep OFF:**
   * all fourteen session-68b flags
   * `ENABLE_PROXY_AWARE_RATELIMIT`
   * `ENABLE_DEFAULT_RATE_LIMITS`
   * `ENABLE_LIMITER_ENDPOINT_KEY`
   * `ENABLE_ANON_USAGE_GATE`
   * `ENABLE_TPM_AWARE_ROUTING`
   * `ENABLE_HONEST_PARTIAL_SCORING`
6. These variables do nothing, so don't rely on them: `FREE_TIER_DAILY_LIMIT`, `MAX_MONTHLY_COST`, `ENABLE_HYBRID_MODEL_ROUTING`.

**A4. Domain and email** (EXPO-06, LL-7, LL-13, RT-11; optional before submitting)

1. Railway → `qaren-landing` → Settings → Networking → Custom Domain: add `qaren.app`. Fix the Cloudflare DNS/proxy record that is returning 522.
2. Verify that `https://qaren.app/.well-known/apple-app-site-association` returns 200 `application/json` with no redirect.
3. Cloudflare → Email → Routing: confirm `support@`, `privacy@` and `legal@` forward to a monitored inbox. Send one test email to each.

### B. Decisions (reply with letters)

* **D1 iPad:** (A) `supportsTablet:false` for 1.0.0 (recommended), or (B) keep iPad, which means iPad QA, `requireFullScreen`, and 13" screenshots. (EXPO-04)
* **D2 Paywall:** (A) remove it for v1 and show an honest limit sheet (recommended), or (B) build StoreKit IAP before launch. (LL-2)
* **D3 OpenAI data sharing:** (A) don't enroll; delete §11 and the toggle (recommended), or (B) keep it; create a second non-sharing key `OPENAI_API_KEY_PRIVATE` and Claude routes every call through the toggle. Either way, the explicit AI consent sheet is required. (PM-2, LL-4)
* **D4 Icon art:** supply or approve real brand art. The concentric-circles image is the template. (EXPO-01)
* **D5 Publisher and data controller:** (A) Hussain Aseeri as an individual, with `<TRADE NAME>` if any, and a written IP licence or assignment between you (fastest), or (B) an organization account (needs a D-U-N-S number; weeks). This sets the copyright string `2026 <OWNER>` (no ©; ASC adds it). (LL-6, SA-11)
* **Legal inputs, never invented** (LL-1):
  1. controller: `<ENTITY NAME / PERSON>`
  2. `<CR NUMBER>`, only if it's a company
  3. `<POSTAL ADDRESS>`
  4. confirm `privacy@`/`support@qaren.app` receive mail, or give `<EMAILS>`
  5. deletion/data-request response time (30 days proposed)
  6. effective date = publication date
  7. D3
  8. lawyer review yes/no, and whether to label it "Beta" (#14, #15)
* **D6 Guest mode** (optional, removes the 5.1.1(v) risk): yes or later. (LL-3)
* **D7** preflight breaker, see A3. **D8** auto-recharge vs prepaid, see A1.
* **D9 Age rating:** answer honestly, then **Override to Higher Age Rating → 13+**. Answer "Age Assurance" No, because a checkbox is not age assurance. (LL-8)
* **D10 Re-engagement pushes:** are they marketing? Default: no. The payloads are the user's own comparisons. (PM-6, RT-12)
* **D11** Approve the EN and AR listing text in §6 after a native Arabic review.

### C. Apple: one session with Hussain, or his API key (BLD-BP-02, EXPO-02/03/05)

1. Hussain (Account Holder), App Store Connect → Users and Access → Integrations → App Store Connect API:
   * Request API access. Only the Account Holder can do this.
   * Create a **Team** key with the **Admin** role.
   * Download the `.p8` once and store it outside the repo. `*.p8` is gitignored anyway.
   * Record the Key ID and Issuer ID.
2. App Store Connect → Apps → **+ New App**:
   * iOS
   * name `MYEZ — Compare Smart` (or `MYEZ`); this also checks the name is free
   * primary language English
   * bundle ID `com.qaren.app`
   * SKU `qaren-ios`
   * Send Claude the numeric **Apple ID** (`<ascAppId>`).
3. Optional (LL-9): Certificates, Identifiers & Profiles → Keys → new key with **Sign in with Apple**. Put the `.p8`, Key ID and Team ID on Railway as secrets. Claude will supply the variable names.
4. In a **real terminal** (Claude's Bash has no TTY):
   ```
   cd SmartCompareApp
   eas credentials -p ios
   ```
   Choose the **production** profile. Reuse the Distribution certificate (valid to May 2027). Generate the App Store provisioning profile. Answer **yes** to Push Notifications (APNs key). Upload the ASC API key for submit. Sync capabilities: Sign in with Apple, Associated Domains, Push.

### D. Builds (after Claude's U2–U8 are merged): §5

1. Run the preview build, then a smoke test on the 2 registered iPhones:
   * Apple and Google sign-in
   * camera
   * a compare
   * push
   * the Arabic walkthrough, including the 51 labels already owed
2. Production build, then `eas submit`, then **internal TestFlight** (no App Review needed). Pass the same smoke test on the exact binary.
3. Check the App Store Connect processing email for ITMS-90683, 91053 and 91061 (EXPO-07, PM-7).
4. Send one test push through Expo's push tool (EXPO-05).

### E. Listing, account, screenshots, submit

1. **Demo account** (LL-3, RT-4, PRD-BP-06):
   * Register `<REVIEW EMAIL>` in the app.
   * Supabase → Authentication → Users: confirm the email.
   * Complete onboarding once.
   * Table editor → `users` → `subscription_tier = premium`.
   * Put the password only into App Store Connect. Never in the repo.
2. **Warm-up (RT-6):** run the six curated pairs twice each, pacing within the 10-per-minute limit:
   * iPhone 15 / Samsung Galaxy S24
   * Bose QuietComfort Ultra / Sony WH-1000XM5
   * Nivea Soft / Cetaphil Moisturizing Cream
   * HealthAid Vitamin D3 / NOW Foods Vitamin D-3
   * L'Oreal Revitalift / Olay Regenerist
   * Tom Ford Tobacco Vanille / Creed Aventus. Drop this pair if the result is partial; fragrance spec coverage is thin.

   Put only pairs that pass the A1 assertions into the review notes. Re-warm every 24 h while in review.
3. **Screenshots** (SA-01) on the iPhone, using side button + volume up. Shoot 6 real screens:
   * Home with two products entered
   * Results winner card
   * dimension bars / "where the runner-up wins"
   * confidence pills
   * the camera framing two products
   * History with 3 or more entries

   Do not use splash, sign-in, loading or paywall screens. Optionally repeat everything in Arabic for the AR set.
4. Paste the §6 fields.
5. App Privacy: fill it row by row from `docs/privacy-data-inventory.md`, not from the May draft (PM-4). Tracking: No.
6. Age rating: D9.
7. **Submit for Review.**

### F. After approval

1. Railway `web`: `APP_STORE_URL=https://apps.apple.com/app/id<ascAppId>` (BLD-BP-10, EXPO-11). Never raise `APP_MIN_VERSION` with `APP_FORCE_UPDATE=true` until this is set.
2. Replace `idTBD` in `cloudflare-workers/qaren-redirect/src/index.ts:29`. Claude makes the edit and you redeploy.
3. JS hotfixes: publish to `--branch preview` first, check on a device, then `eas update --branch production` with the same commit (BLD-BP-05).

---

## 4. What Claude does next (in order, each with its check)

| Unit | Contents | Verification gate |
|---|---|---|
| **U1** (today; before the new key) | `extraction_service.py:66`: log `bool(api_key)` instead of the key suffix, plus a caplog test that no substring of the key appears (PRD-BP-02) | pytest green, CI green, deployed before step A1.7 |
| **U2** paywall | Honest limit sheet with no price, trial, Restore, rating or user count. Remove the Profile upgrade row. Point the header counter and the 8 quota paths at the sheet. Delete the 5,000+ and 4.8. Old screen goes behind a default-OFF flag (LL-2, RT-2, SA-05) | full jest, tsc, eslint, EN/AR i18n parity; grep shows `paywall.cta` / `2.9 BHD` unreachable |
| **U3** AI consent | One-time sheet naming OpenAI before the first compare or scan, stored the way consent.ts records acceptance, and blocking until accepted. Camera pre-sheet. Consent-row wording. Act on D3 (toggle and §11 removed, or `select_client_for_user` wired with unset = OFF). Remove "Your budget" (PM-1, PM-2, LL-4, RT-5, PM-3) | jest + pytest; grep for `select_client_for_user` callers matches D3; AR strings queued for native review |
| **U4** native config (**must land before the production build**) | `supportsTablet:false` (D1). Mic strings on expo-camera and image-picker. `faceIDPermission:false`. expo-localization `supportedLocales ["en","ar"]` + `locales.ar` (قارن + AR camera/photo strings). Manifest: add CustomerSupport; ProductPersonalization on SearchHistory/ProductInteraction (in both inventory and app.json). `npx expo install expo@~54.0.37 expo-font expo-localization expo-screen-capture expo-updates` with `expo.install.exclude:["react-native-svg"]`. Uninstall gesture-handler and delete PENDING_REMOVAL + d3 todo. Icons once D4 lands, with `ICON_ART_SUPPLIED=true` (EXPO-04/07/08/10, SA-10, PM-5/6, BLD-BP-03/07, EXPO-01) | full jest incl. nativeBundle.w37; tsc; `npx expo config --type introspect` shows the mic string, no Face ID key, `CFBundleLocalizations`, and device family iPhone only; `npx expo install --check` clean apart from the exclusion; `npx expo-doctor` |
| **U5** cert pins | Pin YE2 `s/tdAOmUzd8syaTuqfgGvFcn6DzA5Cmb+Vby1ST+U3Y=`, Root YE `sCkq5UWXjg+7mKu9lMhhYF5bGLsy7VI/UNW3tccdR7w=`, plus YE1/YE3/YR1-3/Root YR from the letsencrypt.org PEMs. `addSslPinningErrorListener` → Sentry. Fix the stale comment (BLD-BP-01) | openssl-derived hashes match; jest asserts the live-chain hashes are present |
| **U6** auth and first-run UX | `AppleAuthenticationButton` full-width on Login, Register and Step16 (LL-10). 401/429 → i18n keys (RT-9). Stop requesting push permission on login/launch and let Step 17 ask (RT-12). One-time `reloadAsync` when RTL flips on first launch, with the flag written before the reload (RT-14). Trending tap prefills and runs the pair, no counts (RT-7) | full jest; device check in the preview build |
| **U7** error honesty | `errorCopy.ts` gets an `LLM_UNAVAILABLE` / outage key (EN+AR). A verdict carrying `comparison.error` is shown as a degraded result. Camera vision 5xx no longer maps to the "still gathering prices" loop. Optional preflight in `image_routes` → 503 (RT-1, PRD-BP-04) | jest + pytest |
| **U8** legal (after §3 B inputs) | Rewrite `app/legal/*.md` with the §2 data rows, full processor list, equal-protection clause, deletion path and response time, and no DRAFT lines. `legal_routes.py` `last_updated`. `TERMS_VERSION` in consent.ts **and** consent_service.py. Landing `privacy.html`, `terms.html`, `ar/privacy.html`, `ar/terms.html`. Landing `/c/*` and `/r/*` fallback pages. Optional `?lang=ar` endpoint (LL-1, RT-3, LL-5, LL-14, RT-8) | pytest/jest version-pin tests; `grep -ri "draft" app/legal landing` returns 0 matches; after deploy, curl each URL returns 200 with no banner |
| **U9** docs | Checklist: row 17 and line 173 point to the inventory, May draft marked SUPERSEDED (PM-4); URLs in rows 6–8 (LL-7); age 13+ via override (LL-8); keywords (SA-09); description (SA-04/LL-11); 6.9"/13" sizes (SA-01). Inventory "Not collected" names the Cloudflare and `ENABLE_PROXY_AWARE_RATELIMIT` triggers (PM-8). CLAUDE.md: `@sentry/react-native` is 7.2.0, the fixed stale lines, and the production-OTA rule + `expo.version` bump rule (BLD-BP-05, EXPO-11). CI: add a non-blocking `expo install --check` step (BLD-BP-08) | docs-only PR; CI green |
| **U10** after the ascAppId arrives | Fill the `eas.json` submit block (§5) (BLD-BP-04) | `eas config` / JSON parse passes |
| **U11** optional | SIWA token revocation (LL-9, needs the key from §3 C3). `DAILY_4O_CAP` read from env (PRD-BP-12). Breaker census comment (PRD-BP-13). Guest mode (D6) | jest + pytest |

Before every mobile PR: rebase on main and run the **full** jest suite (memory rule). No node_modules junction removal with recursive delete.

---

## 5. `eas.json` submit block and command sequence

Add this to `SmartCompareApp/eas.json`. It contains only placeholders, no secrets (BLD-BP-04). If the API key is stored on EAS through `eas credentials`, drop the three `ascApiKey*` lines.

```json
"submit": {
  "production": {
    "ios": {
      "ascAppId": "<numeric Apple ID from ASC › App Information>",
      "appleTeamId": "8K562M549D",
      "ascApiKeyPath": "<ABSOLUTE path outside the repo>/AuthKey_<KEY_ID>.p8",
      "ascApiKeyIssuerId": "<issuer UUID from ASC › Users and Access › Integrations>",
      "ascApiKeyId": "<KEY_ID>"
    }
  }
}
```

Command sequence. Ahmed runs this in a real terminal, on a clean checkout of the release commit. The repo root has 25 untracked files, so don't build from the shared clone.

```
cd SmartCompareApp
npm ci
npx tsc --noEmit
npx jest --ci
npx eslint "src/**/*.{ts,tsx}"
npx expo install --check        # clean except the react-native-svg exclude
npx expo-doctor
npm audit --audit-level=high    # report only
eas whoami                      # kersher2 (eas-cli 18.8.1 works; upgrading to latest is advisable)
eas credentials -p ios          # production profile — §3 C4
eas build -p ios --profile preview        # smoke on the 2 registered iPhones
eas build -p ios --profile production     # autoIncrement, remote build number, channel production
eas submit -p ios --profile production --latest
# if pod install fails: eas build:view <id> --json  → read the INSTALL_PODS phase
```

Optional: in the EAS dashboard, add a plain `SENTRY_ALLOW_FAILURE=true` to the **production** environment. A bad Sentry token then warns instead of failing the build (EXPO-12). The first production build resolves native config once. Anything native (icons, `supportsTablet`, strings, locales, pins as installed) must be in U4 and U5 before it runs. Changes after launch need a new `expo.version` (BLD-BP-05).

---

## 6. App Store Connect fields to paste

| Field | EN | AR (ar-SA localization; native review required) |
|---|---|---|
| Name (≤30) | `MYEZ — Compare Smart` (20). Reserve it by creating the record. | `ميّز - مقارنة المنتجات` (22). Alternative: `ميّز: قرار شراء أذكى` |
| Subtitle (≤30) | `Two products. One clear pick.` (29) | `قارن منتجين واحصل على حكم واضح` (30) |
| Promotional text (≤170) | `Type or photograph two products and get a clear verdict built from specs, reviews and GCC retailer prices. Prices are live; we always show how confident we are.` (160) | `اكتب منتجين أو صوّرهما، واحصل على حكم واضح مبني على المواصفات والتقييمات وأسعار المتاجر في الخليج. الأسعار حية وقد تتغير، ونبيّن لك مستوى الثقة دائماً.` (151) |
| Keywords (≤100 **bytes**) | `prices,shopping,fragrance,perfume,phone,supplements,skincare,GCC,Bahrain,Saudi,UAE,Kuwait,Qatar` (95 bytes; adds Oman only if room is freed) | `مقارنة,أسعار,تسوق,عطور,جوال,مكملات,البحرين,السعودية` (95 bytes) |
| Privacy Policy URL | `https://qaren-landing-production.up.railway.app/privacy.html` | `https://qaren-landing-production.up.railway.app/ar/privacy.html` |
| Support URL | `https://qaren-landing-production.up.railway.app/support` | `https://qaren-landing-production.up.railway.app/ar/support` |
| Marketing URL | blank | blank |
| Category | Primary: Shopping · Secondary: Lifestyle (or Utilities) | same |
| Copyright | `2026 <OWNER per D5>` (no ©) | same |
| Age rating | Questionnaire answers: no web view/unrestricted web, no UGC, no messaging, no ads, no gambling or mature themes; Medical/Wellness as it truthfully applies. Then **Override → 13+**. | same |
| Export compliance | Handled: `ITSAppUsesNonExemptEncryption=false` (app.json:129) | same |
| App Privacy | Row by row from `docs/privacy-data-inventory.md` after U4; Tracking = No | same |
| Sign-in required | Yes: `<REVIEW EMAIL>` / `<REVIEW PASSWORD>` (premium tier) | — |

**Things to settle before pasting the listing:**

* The URLs are pasted after U8 has removed the DRAFT banner. They can be edited later if qaren.app goes live.
* Fragrance and perfume keywords stay only if the fragrance pair passes the warm-up (RT-6).
* Promo, description and keywords must not include brand names (2.3.7).
* The support email in the description stays only if LL-13 passes.

**Description (EN).** About 1,500 characters. No COMING SOON section, no "authorized retailers", no "in seconds" (SA-04, LL-11).

```
MYEZ helps you choose between two products with confidence. Type two product names or photograph them, and we gather specs, reviews and prices from retailers serving the GCC, then give you a clear verdict: which one fits you better, why, and where the other one wins.

WHAT YOU GET
• A clear verdict instead of a long spec sheet: the winner, the reason, and where the runner-up is stronger.
• Prices from stores serving Bahrain, Saudi Arabia, the UAE, Kuwait, Qatar and Oman. Prices are live and change over time; when a price is estimated or converted from another currency, we say so.
• A confidence level on every comparison showing how strong the price, spec and review data is.
• Camera compare: photograph two products, or photograph one and type the other.
• Results that respect your priorities — tell us what matters, like battery, quality or value.
• A history of your comparisons, and sharing a result with others.

CATEGORIES
Electronics, supplements, fragrances, makeup, skin and hair care, fashion and groceries.

BUILT FOR THE GULF
Available in English and Arabic with full right-to-left support.

YOUR PRIVACY
Your searches and photos are processed by OpenAI to generate comparisons. We don't sell your data, we don't track you across other apps, and we show no third-party ads. You can delete your account and its data from inside the app at any time.

Note: MYEZ is a decision aid. Information is gathered from public sources and may not always be accurate — check the price with the retailer before you buy.

Support: support@qaren.app
```

**Description (AR):** use the SA-06 draft verbatim, saved at `scratchpad/sa/ar_description.txt`. Add the Arabic form of the OpenAI-processing sentence to «خصوصيتك» so it matches EN and U3.

**App Review notes (EN).** Paste this only after U2 and U3 have shipped and the A1 canary has passed (SA-05, LL-3, RT-13).

```
Demo account: <REVIEW EMAIL> / <REVIEW PASSWORD> (premium tier). Sign in with Apple and Google are also available.
Sign-in is required because the account holds saved comparison history, personalization preferences and a per-account usage quota.
MYEZ compares two products. On Home, type two products, e.g. "<PAIR THAT PASSED WARM-UP>", or use Scan to photograph two products (you can also pick two photos from the library). A comparison usually takes 20–40 seconds while we gather specs, reviews and live prices.
Results currently use the Bahrain market; prices are shown in Bahraini Dinar (BHD). Prices are fetched live from retailers serving the GCC and change over time; some are labelled estimated.
Queries and photos are processed by OpenAI to generate the comparison; users are asked for permission before the first comparison.
Account deletion: Profile tab → gear icon → Edit profile → Delete account.
This version sells no subscriptions or in-app purchases.
```

---

## 7. Checked and found fine (no action needed)

**Build and config (expo-config, build-pipeline notes)**

* Bundle `com.qaren.app` matches the AASA appID `8K562M549D.com.qaren.app`.
* Version 1.0.0 with a remote auto-incrementing build number, so no conflict with preview build 1.
* `ITSAppUsesNonExemptEncryption=false` is correct: HTTPS/TLS, SPKI pinning and expo-crypto are all exempt.
* Camera and photo purpose strings are specific. No `NSPhotoLibraryAddUsageDescription` is needed because the app only reads the library.
* The camera uses `CameraOnlyPermissionRequester`, so it works at runtime without the mic string.
* Sign in with Apple entitlement is generated and wired next to Google, which satisfies 4.8. Google `iosUrlScheme` equals the reversed client id.
* Leaving `expo-dev-client` in a Release build is supported and harmless.
* API base URL and Sentry DSN have fallbacks in code. The only EAS env var is `SENTRY_AUTH_TOKEN`, present in the production, preview and development environments.
* The EAS SDK-54 image is macOS 15.6 / Xcode 26.0 / Node 20.19.4, which meets Apple's Xcode 26 rule from 2026-04-28. iOS minimum is 15.1+.
* The Play install referrer is Android-only and guarded.
* No `ios/`/`android/` folders (CNG). Secrets patterns are gitignored.
* `/api/v1/app/version` returns min/latest 1.0.0 with `force_update:false`, so a 1.0.0 store build is not blocked.
* u.expo.dev has no production update, so the store build runs its embedded bundle and the preview OTA 561d2cba can't reach it.

**Privacy (privacy-manifest notes)**

* All `NSPrivacy*` identifiers and the four reason codes (CA92.1, C617.1, 35F9.1, E174.1) are valid Apple values. The W3-7 spelling question is closed.
* Dependency pod manifests are covered.
* `NSPrivacyTracking=false` is consistent: no ad SDK, no ATT.
* Sentry `sendDefaultPii` is false on mobile and backend.
* The device fingerprint is a SHA-256 hash, not IDFA.
* Photos are transient on the server.
* The clipboard is read only for the invite code.
* Demographics correctly fall outside Apple's "Sensitive Info".
* The inventory and app.json are kept equal by a jest test.
* No coarse location is collected today.

**Listing and legal (legal-listing, store-assets notes)**

* In-app account deletion is a full delete, satisfying 5.1.1(v).
* There is an in-app privacy link, working even when signed out.
* No UGC, messaging or social feed, so answer "No" to UGC.
* No IAP libraries and no external payment links.
* The AASA is served correctly on the Railway host.
* The landing EN and AR pages all return 200.
* support@qaren.app has Cloudflare MX records and SPF.
* The English character limits in the draft fit.
* No web view, so Unrestricted Web Access = No.
* A preview video and "What's New" are optional.
* None of the legal items block **internal** TestFlight.

**Runtime and backend (runtime-under-review, backend-prod notes)**

* `/health` is 200. `/home/trending` is public.
* 401 responses on auth-only endpoints degrade to empty states.
* Cert pinning passes today through ISRG Root X2.
* The `[B4-DIAG]` strings are never rendered.
* Compare error copy never shows raw backend strings, except for RT-9.
* The English locale resolves to `en`.
* All auth goes through the backend.
* The demographics prompt can be dismissed, and onboarding cannot trap the reviewer.
* The breaker design is fail-open and read-only.
* `LLM_UNAVAILABLE` returns 503 and refunds the credit.
* The URL compare refuses to return a result without a verdict.
* `generate_comparison` no longer leaks `str(e)`.
* Failed authenticated compares are refunded.
* `ENABLE_BRIGHTDATA_BUDGET_GATE` is on.

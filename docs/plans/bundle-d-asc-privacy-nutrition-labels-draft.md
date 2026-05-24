# Bundle D — ASC Privacy Nutrition Labels (Draft for Ahmed Approval)

**Task:** 3.N.3 — BLOCKING-Ahmed approval before ASC submission
**Risk:** R13 (App Privacy Nutrition Labels)
**Date drafted:** 2026-05-23
**Drafter:** native-ops
**Status:** AWAITING AHMED APPROVAL — do NOT submit to ASC until each row signed off

## How to read this doc

Apple's "App Privacy" section in App Store Connect uses these terms:

- **Data Type** — Apple's fixed category list (Contact Info → Email; Identifiers → User ID, Device ID; Usage Data → Product Interaction; etc.). You don't make these up.
- **Collected?** — Y if the app or backend receives this data from the user/device, even transiently.
- **Linked to user?** — Y if the data is tied to a user identity (account, login, persistent ID). N if anonymous/aggregated only.
- **Tracking?** — Apple's NARROW definition (`AppTrackingTransparency`): linking with third-party data for **targeted advertising** OR sharing with **data brokers**. Internal analytics / crash reporting are NOT tracking unless cross-app-linked. Qaren does NEITHER — every row below is Tracking=N.
- **Purpose** — Apple's fixed purpose list (App Functionality, Analytics, Product Personalization, Developer's Advertising or Marketing, Third-Party Advertising, Other). Cite multiple if applicable.

Apple is strict on accuracy. **Be conservative**: if uncertain, mark "needs Ahmed input" rather than guess. Misdeclaration risks App Store rejection or removal.

## Summary table (Ahmed: sign off each row)

| # | Data Type | Collected? | Linked? | Tracking? | Purpose(s) | Ahmed sign-off |
|---|---|---|---|---|---|---|
| 1 | Contact Info → **Email Address** | Y | Y | N | App Functionality, Analytics | ☐ |
| 2 | Identifiers → **User ID** (Supabase UUID) | Y | Y | N | App Functionality, Analytics, Product Personalization | ☐ |
| 3 | Identifiers → **Device ID** (SHA-256 device fingerprint) | Y | Y | N | App Functionality (anti-abuse only) | ☐ |
| 4 | User Content → **Other User Content** (search query text) | Y | Y (when `ai_sharing_enabled=true`, ON by default) OR N (when user opts out) | N | App Functionality, Product Personalization, Analytics | ☐ |
| 5 | User Content → **Photos or Videos** (camera product photos) | Y (transient, NOT persisted) | N | N | App Functionality | ☐ |
| 6 | Usage Data → **Product Interaction** (event_type from `user_events` table) | Y | Y (when logged in) OR N (anonymous) | N | Analytics, App Functionality | ☐ |
| 7 | Diagnostics → **Crash Data** (Sentry) | Y | Y (via Sentry user.id mapping) | N | App Functionality, Analytics | ☐ |
| 8 | Diagnostics → **Performance Data** (Sentry traces) | Y | Y | N | App Functionality, Analytics | ☐ |
| 9 | Location → **Coarse Location** (CF-IPCountry from Cloudflare) | Y | Y (saved to demographics_profile) | N | App Functionality, Product Personalization | ☐ |
| 10 | Sensitive Info → **Demographics** (age_group, gender, governorate) | Y (only if user submits demographics survey) | Y | N | Product Personalization, Analytics | ☐ |
| 11 | Financial Info — **NOT collected** | N | — | — | — | ☐ |
| 12 | Health & Fitness — **NOT collected** | N | — | — | — | ☐ |
| 13 | Browsing History — **NOT collected** | N | — | — | — | ☐ |
| 14 | Search History (in-app) — see Row 4 (User Content) | — | — | — | — | — |
| 15 | Audio Data — **NOT collected** | N | — | — | — | ☐ |
| 16 | Gameplay Content — **NOT collected** | N | — | — | — | ☐ |
| 17 | Customer Support — **see Row 1 + Row 4** (contact-us encodes category as `[Bug] subject\n\nbody` prefix in `change_suggestion`) | — | — | — | — | — |
| 18 | Purchases — **NOT collected** (no IAP yet) | N | — | — | — | ☐ |
| 19 | Other Data — **NOT collected** | N | — | — | — | ☐ |

---

## Row-by-row evidence + answer rationale

### Row 1 — Contact Info → Email Address

**Collected?** Y
- **Where:** `POST /api/v1/auth/register` (`app/api/auth_routes.py:334` → `register_user(body.email, body.password)`) and `POST /api/v1/auth/login` (line 459 → `login_user(body.email, body.password)`).
- **Storage:** Supabase `auth.users` table (managed by Supabase Auth) and shadowed in `public.users` via Supabase trigger.
- **Used for:** account identification, password reset (`/forgot-password`), email change (requires current password per `update_user_email`), feedback channel (account-linked feedback submissions).

**Linked to user?** Y — email is the primary user identifier for Supabase Auth.

**Tracking?** N — emails are never shared with third parties for advertising, never linked to advertising IDs, never sold to data brokers. Apple's "Tracking" definition does NOT apply.

**Purpose:**
- **App Functionality** — login, password reset, account management
- **Analytics** — login frequency, retention cohort analysis (account-bound, NOT third-party advertising)

NOTE: If Qaren ever ships a marketing-email program (newsletters, promo campaigns), add **Developer's Advertising or Marketing** purpose.

NOTE: `support@qaren.app` mailto outbound from ContactUsScreen / Profile is the OTHER place a user's email is exposed. The Bundle D DNS+hosting plan (`docs/runbooks/bundle-d-dns-and-hosting.md`) covers the `/support` 301 redirect to `mailto:support@qaren.app`. The forwarding policy (whether the mailbox is a Gmail forward to Ahmed's personal account, a shared inbox, or an external help-desk SaaS like Front / HelpScout / Zendesk) is A7 — pending Ahmed. **Impact on Privacy Nutrition Labels:** if Ahmed routes `support@qaren.app` through a third-party help-desk SaaS, that SaaS becomes a sub-processor and MUST be listed in the Privacy Policy (Row 1 storage list expands). If `support@qaren.app` is a Gmail forward to Ahmed personally, Gmail is the sub-processor — already in scope as standard email infrastructure. Native-ops will revisit this row when A7 resolves.

---

### Row 2 — Identifiers → User ID (Supabase UUID)

**Collected?** Y
- **Where:** Created automatically by Supabase Auth on `register`. Used as primary key for `public.users`, foreign key on `comparisons`, `user_events`, `comparison_feedback`, `user_usage`, `referral_invites/redemptions`, etc.
- **Storage:** Supabase PostgreSQL. UUIDs are app-internal — never Apple's `IDFA`, never Google's `Advertising ID`.

**Linked to user?** Y — by definition, this IS the user identity.

**Tracking?** N — internal UUIDs only; never joined with third-party data sets for advertising; never sold or shared with data brokers.

**Purpose:**
- **App Functionality** — primary user identity
- **Analytics** — `user_id` is the join key on `user_events` for retention/funnel analysis
- **Product Personalization** — cohort matching (`cohort_service.py`), behavioral profile (`behavior_service.py`), personalized scoring (`scoring_service.py` ±30/10/5% caps)

---

### Row 3 — Identifiers → Device ID (SHA-256 device fingerprint)

**Collected?** Y
- **Where:** `X-Device-Fingerprint` HTTP header on `POST /api/v1/auth/register`. Must match `^[a-f0-9]{64}$` (SHA-256 hex). See CLAUDE.md "X-Device-Fingerprint header" + Migration 021 + Bundle A reference at `users.device_fingerprint_hash`.
- **Storage:** Supabase `public.users.device_fingerprint_hash` (already a SHA-256 hash — raw device identifier is computed client-side and ONLY the hash leaves the device).
- **Used for:** anti-abuse — prevents log-out-and-re-signup farming of free tier (Migration 021); 3-LIFETIME referral cap per device (Migration 023, Bundle B/C/D).

**Linked to user?** Y — stored on `users` row, joined with `user_id`.

**Tracking?** N — NEVER used for cross-app linking, NEVER joined with advertising IDs (the SDK never collects IDFA/AAID), NEVER shared with third parties. Pure server-side anti-abuse signal.

**Purpose:**
- **App Functionality** — fraud prevention only

NOTE: Apple sometimes asks "Is this a static device identifier like IDFA?" — answer: **NO**, the fingerprint hash is app-internal, computed from non-Apple-restricted client signals, hashed before transit, never exposed to third parties.

---

### Row 4 — User Content → Other User Content (search query text)

**Collected?** Y
- **Where:** `GET /api/v1/text/compare?q=...` (`app/api/text_routes.py` → `compare_from_text(query, region, ...)`). Plus `POST /api/v1/share/...` saves comparison + query in `comparisons.product_names`.
- **Storage destinations (FOUR, ordered by always→conditional):**
  1. **ALWAYS — `search_logs` Supabase table** (`app/services/database_service.py:451-475` `log_search(query, input_type, user_id, products_found, success, error_message, cost, duration_ms)`). Fire-and-forget via `asyncio.create_task` at 8 call sites: `text_routes.py:153/179/254/275/429/442` + `image_routes.py:219/237`. UNCONDITIONAL — runs regardless of `ai_sharing_enabled`. Includes the raw `query` string + `user_id` (NULL when anonymous). Used by `analytics_service.py` to power the `/admin/costs` operator dashboard.
  2. **ALWAYS — Redis L1 cache** (24h prices, 7d specs/reviews) per query, normalized.
  3. **CONDITIONAL on auth — `comparisons` table** (`comparisons.product_names` + `comparisons.user_id`) so the query renders in the History tab. Anonymous queries are NOT written here.
  4. **CONDITIONAL on `ai_sharing_enabled=true` (default OFF post-Bundle-D) — OpenAI servers** for the shared/improvement-eligible project. Opt-OFF routes to the private OpenAI project where data is not used for training.

**Linked to user?** Y when authenticated (search_logs.user_id, comparisons.user_id, OpenAI metadata if opted in). N when anonymous (search_logs row exists with user_id=NULL — the query text is there but not linked to identity).

**Tracking?** N — search queries are NEVER shared with third parties for advertising or sold to data brokers. The four destinations are:
- `search_logs` + Redis + `comparisons` — internal Qaren stores; queried only by Qaren's own admin operators (X-Admin-Key gated) and by the user themselves via the History tab.
- OpenAI — operational service provider under contract; subject to the user's explicit opt-in via `ai_sharing_enabled=true` (default OFF post-Bundle-D per `auth_routes.py:166` + `openai_service.py:56-65 select_client_for_user`).

None of the four flows match Apple's definition of Tracking (3rd-party advertising joins / data broker sales).

**Purpose:**
- **App Functionality** — execute the comparison (query → AI extraction); show user their own History
- **Product Personalization** — query history feeds personalized scoring (last-N category affinity, price tier signal)
- **Analytics** — `search_logs` powers the operator admin dashboard (cost/usage trends) AND aggregate trending-categories analysis

NOTE: Bundle D ships `ai_sharing_enabled=false` default for NEW users (Task 1.F.6, R23 — COMPLETED). Existing users with `ai_sharing_enabled=true` are NOT reset. Apple labels reflect the **default state for new installs**, which post-Bundle-D = OFF for the OpenAI-shared-project destination. The `search_logs` + Redis + `comparisons` destinations are ALWAYS-ON and reflected as such in the table.

NOTE: When a user shares a comparison via `POST /api/v1/share`, the share URL is public; the GET endpoint strips personalization but the query + product names remain readable. This is consensual — user actively shares.

NOTE: `search_logs` query strings are subject to existing security-regression test pack — `tests/test_security_regression.py` SQL-LIKE escaping (~98 tests). Direct SQL injection through query field is structurally blocked.

---

### Row 5 — User Content → Photos or Videos (camera product photos)

**Collected?** Y (transient, NOT persisted)
- **Where:** `POST /api/v1/image/...` → GPT-4o-mini vision API extracts product identification → auto-compare.
- **Storage:** Photo is uploaded as `multipart/form-data`, transcoded to JPEG client-side (`SmartCompareApp/src/services/api.ts`), sent to OpenAI Vision API for parsing, and **discarded after the request completes**. NOT saved to Supabase, NOT saved to Railway disk.

**Linked to user?** N — photos are NOT stored against the user. The DERIVED product identification (text strings like "iPhone 15 Pro 256GB") IS stored as a `comparisons` row when the user is authenticated.

**Tracking?** N — photos transit OpenAI only (subject to the `ai_sharing_enabled` toggle, same as text queries). NEVER shared with advertising networks or data brokers.

**Purpose:**
- **App Functionality** — recognize what product the user is holding

NOTE: Photo upload requires `expo-camera` (with `cameraPermission` message at `app.json:71`) + `expo-image-picker` (with `photosPermission` message at `app.json:77`). Both ask for permission via standard iOS prompt; user can deny.

---

### Row 6 — Usage Data → Product Interaction (`user_events` table)

**Collected?** Y
- **Where:** `POST /api/v1/events` batch endpoint (`app/api/feedback_routes.py:111-133`). Whitelisted `event_type` values: `["save", "share", "source_click", "tab_switch", "feedback_submit", "result_view_duration"]` (line 24). Plus `comparison_id`, free-form `event_data` dict (max 10 KB per validator at line 62).
- **Storage:** Supabase `public.user_events` with RLS.
- **Optional `event_data`:** payload size capped at 10 KB; depending on event_type may include numeric durations, UI state strings, click targets — NEVER raw passwords, payment details, photos.

**Linked to user?** Y when authenticated (`user_id` populated from `get_optional_user`). N when anonymous (`user_id` is NULL — `auth-optional` per route docstring at line 114).

**Tracking?** N — events are app-internal product analytics only. NOT shared with third-party advertising/analytics SaaS (no Mixpanel, no Amplitude, no Firebase Analytics — confirmed by grep). Sentry receives crash/performance data (Rows 7-8) but NOT these product events.

**Purpose:**
- **Analytics** — funnel/retention dashboards, A/B-test bucket performance
- **App Functionality** — drives behavioral_profile decay-weighted updates (`behavior_service.py`)

NOTE: `feedback_submit` event corresponds to `POST /api/v1/feedback` which writes to `comparison_feedback` table (`useful` bool, `mattered_most` enum array, `change_suggestion` free text up to 1 KB). Feedback IS Customer Support content per Row 17.

---

### Row 7 — Diagnostics → Crash Data (Sentry)

**Collected?** Y
- **Where:** Mobile SDK `@sentry/react-native@8.11.1` (`SmartCompareApp/src/services/sentry.ts`); backend `sentry-sdk` initialized in `app/services/sentry_service.py`. Both write to `qaren-rr` Sentry org (different projects: `react-native` mobile vs server-side backend).
- **Storage:** Sentry SaaS (sentry.io). Retention per Sentry plan default.

**Linked to user?** Y — when authenticated, the user's UUID is attached to the Sentry event context (so we can correlate "this crash happened to user X"). Anonymous sessions submit crashes without user.id.

**Tracking?** N — Sentry is a single-app diagnostics tool, NOT a cross-app behavioral profile. NEVER joined with advertising networks. Apple's Privacy Nutrition Labels guide explicitly carves out "single-app crash and performance data" as NON-tracking.

**Purpose:**
- **App Functionality** — fix bugs, prevent regressions
- **Analytics** — error rate trends, performance regressions

NOTE: Sentry `before_send` hook in `app/services/sentry_service.py:66-87` scrubs JWTs, OpenAI keys, Firecrawl keys, Bearer tokens, Authorization headers, X-Admin-Key headers, Cookie headers, and any dict-value whose key matches `api_key|apikey|token|secret|password`. The mobile SDK mirrors these scrub patterns per CLAUDE.md "sentry.ts" section. PII leakage to Sentry is structurally minimized.

NOTE: Bundle D task R21 (Task 1.B.6) further tightens this: `_before_send` will scrub query-string PII patterns (`?q=`, `?query=`, `?email=`) while preserving non-PII (`?nocache=true`). Reduces the risk of search-query text reaching Sentry payload as part of an exception URL.

---

### Row 8 — Diagnostics → Performance Data (Sentry traces)

**Collected?** Y
- **Where:** Same Sentry SDKs as Row 7 (`@sentry/react-native` for mobile, `sentry-sdk` for backend). Includes API latency, slow-screen timings, crash-free session rate.
- **Storage:** Sentry SaaS.

**Linked to user?** Y — sessions tagged with user UUID when authenticated.

**Tracking?** N — same rationale as Row 7.

**Purpose:**
- **App Functionality** — diagnose slow paths
- **Analytics** — performance over time

---

### Row 9 — Location → Coarse Location (CF-IPCountry from Cloudflare)

**Collected?** Y
- **Where:** `app/api/auth_routes.py:807-814` `_derive_country` reads `cf-ipcountry` header from Cloudflare-proxied request OR falls back to explicit payload `country` field. Defaults to "Bahrain" when no signal.
- **Storage:** Supabase `users.demographics_profile.country` JSONB key.

**Linked to user?** Y — saved to the user's demographics row.

**Tracking?** N — country code only (e.g., "BH", "AE"), NOT precise GPS, NOT IP address itself. Used only for region-specific pricing/availability. Never shared with third parties for advertising.

**Purpose:**
- **App Functionality** — region detection for GCC market routing
- **Product Personalization** — country/language thin context for cohort priors

NOTE: Apple's "Precise Location" requires GPS or similar (~city-level or finer). Country code is "Coarse Location" — country-level only.

---

### Row 10 — Sensitive Info → Demographics (age_group, gender, governorate)

**Collected?** Y — only if the user submits the demographics survey during onboarding (NOT required to use the app).
- **Where:** `PUT /api/v1/auth/demographics` (`auth_routes.py:817-862`). Payload: `age_group`, `gender`, `governorate`, `language`, `country`. All 5 fields optional per Pydantic at line 226-230.
- **Storage:** Supabase `users.demographics_profile` JSONB.
- **Used for:** cohort matching via `cohort_service.py` — privacy invariant per CLAUDE.md "Cohort personalization (Phase 1 LIVE)": **NO raw age/gender/identity in prompt**, only country/language/governorate thin context is forwarded to GPT.

**Linked to user?** Y — stored on the user row.

**Tracking?** N — never shared with third parties, never sold, never joined with external data sets. Used only for product personalization within Qaren.

**Purpose:**
- **Product Personalization** — primary use (cohort priors)
- **Analytics** — aggregate cohort breakdowns visible at `/admin/cohort` dashboard (operator-only, X-Admin-Key gated)

NOTE: Apple categorizes gender as "Sensitive Info." Demographics submission is FULLY OPTIONAL per Pydantic (all 5 fields default `None`); the user can skip the demographics step in onboarding entirely. The labels MUST reflect this conditional collection.

NOTE: User can update or clear demographics via subsequent `PUT /api/v1/auth/demographics` calls; deletion cascades through `delete_user_cascade()` (App Store requirement, currently planned as Bundle D Task 1.B.5 R20).

---

### Row 11-13, 15, 16, 18, 19 — NOT collected

| Category | Why not |
|---|---|
| Financial Info | No payment processing in v1 (no IAP, no Stripe). Will change when subscription tier ships. |
| Health & Fitness | App is for product comparison only; no HealthKit/Fitness integration. |
| Browsing History | App doesn't track Safari/Chrome/external browsing. |
| Audio Data | No microphone use beyond what `RECORD_AUDIO` Android permission allows (currently scaffolded for future voice input; NOT wired). |
| Gameplay Content | Not a game. |
| Purchases | No IAP yet. |
| Other Data | None identified. |

**Action item for Ahmed:** confirm "Financial Info" and "Purchases" must be marked when subscription tier ships post-launch.

---

### Row 14 — Search History (in-app) → see Row 4

Apple's "Search History" category traditionally refers to in-app search-bar text. Qaren's search queries ARE Row 4 "Other User Content." Apple's classification accepts either bucket; Row 4 is more accurate because the queries get processed by GPT (not just stored as a literal search log).

### Row 17 — Customer Support → see Row 1 + Row 4

`POST /api/v1/feedback` (`feedback_routes.py:84-106`) accepts `change_suggestion` free text up to 1 KB. The ContactUsScreen prefixes bug-report category as `[Bug] subject\n\nbody` (CLAUDE.md note). This routes through the same `change_suggestion` field, which is User Content (Row 4 covers content; Row 1 covers the email association when authenticated).

---

## Tracking summary — Apple's narrow definition

Apple defines **Tracking** as:
1. Linking user/device data collected in this app with user/device data collected by OTHER companies' apps/sites/services for **targeted advertising or advertising measurement**.
2. Sharing user/device data with **data brokers**.

Qaren does NEITHER. Therefore **every row above marks Tracking=N**.

Specifically:
- **No third-party advertising SDKs** in `package.json` (verified by grep for `react-native-google-mobile-ads`, `react-native-fbsdk-next`, `appsflyer`, `branch`, `adjust`, `singular` — all absent).
- **No data broker integrations** — backend only writes to Supabase, Redis, OpenAI, Serper, Firecrawl, Scrape.do, Sentry. None of these are data brokers; all are operational service providers under contract.
- **`AppTrackingTransparency` prompt is NOT required** — we don't access `IDFA` (Apple's advertising identifier). Confirm by grep for `setUserTrackingAuthorization` or `requestTrackingAuthorization` — should return zero matches.

When ASC asks "Does your app use the AppTrackingTransparency framework?" — answer **NO**.

---

## Apple's "Data Used to Track You" section

Apple shows a "Data Used to Track You" section even if you say no tracking. Since Tracking=N across all 10 collected rows, this section will be **EMPTY** in our label.

## Apple's "Data Linked to You" section

Per the answers above, this section lists:
- Contact Info → Email (Row 1)
- User ID (Row 2)
- Device ID (Row 3)
- User Content → Other User Content (Row 4, when `ai_sharing_enabled=true`)
- Usage Data → Product Interaction (Row 6, when authenticated)
- Diagnostics → Crash Data (Row 7)
- Diagnostics → Performance Data (Row 8)
- Location → Coarse Location (Row 9)
- Sensitive Info → Demographics (Row 10, when user opts in via demographics survey)

## Apple's "Data Not Linked to You" section

Per the answers above:
- User Content → Photos or Videos (Row 5) — transient, not stored
- Usage Data → Product Interaction (Row 6) when user is anonymous (no `user_id` populated)
- User Content → Other User Content (Row 4) when user is anonymous

NOTE: Apple is strict that the SAME data type can appear in both "Linked" and "Not Linked" sections if applicable. We legitimately have this case for Rows 4 + 6 (auth-optional endpoints).

---

## Privacy URL declaration

Apple also requires a Privacy Policy URL in the App Information section of ASC.

- **Current state:** Privacy policy lives at `app/legal/privacy_policy.md`, served by `GET /api/v1/legal/privacy_policy` (Task 1.B.1 routing fix landed via commit `eeaea11`).
- **Production-facing URL needed:** Likely `https://qaren.app/privacy.html` after Bundle D Task 2.N.2 landing page lands. Until then, use `https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy` as a placeholder. Apple accepts JSON-returning endpoints if they render properly in a browser; the route returns text/markdown and the FastAPI default renderer makes it browser-readable. **Action item for Ahmed:** confirm final Privacy URL choice (Railway endpoint vs qaren.app/privacy.html post-Task-2.N.2).

---

## Decisions required from Ahmed (per dispatcher feedback: "Be conservative — needs Ahmed input")

1. **(D1)** Approve each of 10 collected rows above (☐ in summary table) — particularly Row 4 (`ai_sharing_enabled` flip default) and Row 10 (demographics as Sensitive Info).
2. **(D2)** Confirm "No tracking" + "No AppTrackingTransparency" stance is accurate (verify no advertising SDKs slip in via transitive deps).
3. **(D3)** Confirm Privacy URL for ASC App Information section: Railway endpoint (pre-Task-2.N.2) vs qaren.app/privacy.html (post).
4. **(D4)** Confirm marketing-email program is NOT planned for v1 — so Row 1 purpose does NOT include "Developer's Advertising or Marketing." If a newsletter ships within 30 days of launch, the label must be updated (Apple allows in-app label updates without re-submission).
5. **(D5)** Confirm subscription / IAP is NOT shipping in v1 — so Row 11 (Financial Info) and Row 18 (Purchases) stay "Not Collected."

## Rollback / update path

If Apple flags an answer during review:
1. Update the disputed row in this doc with the actual factual position.
2. Update the ASC label (ASC allows label edits without re-submitting the binary).
3. Reply to App Review with the corrected interpretation + citation.
4. Note that Apple sometimes interprets categories differently than the developer — be ready to defer to their classification rather than argue.

## When can this be submitted to ASC?

This draft is BLOCKING-ready: dispatcher relays to Ahmed → Ahmed signs off each row (D1) + answers D2-D5 → native-ops applies any corrections + commits final version → submit to ASC during Phase 3 Task 3.N.2 ASC upload window.

The labels are entered into ASC via the App Information → App Privacy section. Apple does NOT charge for label changes after initial submission; you can iterate.

# U8 - privacy policy and terms of service redraft (spec)

Session 72, 2026-10-05. Opus spec agent under the synack-build-orchestrator loop. LAUNCH BLOCKER.

## 0. Base, status, how to read

- Base: main `845ece15f118a8e3e99c9778fab7985a96f19bb3`, read-only checkout `C:/Users/SynAckITPC/Documents/AI/sc-s71-u13` (porcelain empty at 13:49 AST). Every `file:line` below is at that SHA unless marked otherwise.
- Status: the owner's inputs (runbook section 3 B items 1-8, D3, D5, D14) have NOT arrived. This spec does everything that does not need them. Every fact only the owner can give is a `<PLACEHOLDER:ID>` token whose ID matches a numbered question in `U8_INPUT_FORM_AHMED.md`.
- No legal advice is given here. This is a truthful technical description of what the code does plus a drafting plan for the owner and his counsel. Legal-research items are cited as M1-M17 of `docs/investigations/2026-10-03-session-71-state/RESEARCH_DIGEST.md` (sc-docs-70), which carries the primary citations.
- Web-derived claims carry their URL and the date 2026-10-05. Anything not confirmed is in section 9 (NOT VERIFIED).
- Sections 1 and 2 (truth table, processors) are the source for every factual sentence in section 4. Where section 4 cites `T<n>` it means truth-table row n; `P<n>` means processor row n; `C<n>` means contradiction n.
- Owner answers ALREADY given (never re-ask): response times 10 working days (rectification, erasure, objection) and 15 working days (access); no Beta label; an in-app consent withdrawal control ships in U3b; account deletion is fixed in code (U8b = PR #290, migration 043 written, NOT applied in production); age 13+ (locked); app name MYEZ / Arabic form as in the catalogs; identifiers and addresses stay `qaren` (D14 default as applied by #257).

---

## 1. Data-flow truth table (from the code at 845ece15)

Columns: what | collected at (file:line) | stored at | retention as implemented | who receives it | purpose | deletion TODAY (025 in production) | deletion under 043 (written, unapplied).

"025" = `migrations/025_delete_user_cascade_completeness.sql` (the function live in production). "043" = `migrations/043_delete_user_cascade_full_erasure.sql`. Deletion path for both: `DELETE /api/v1/auth/account` -> `auth_service.delete_user_account` (`app/services/auth_service.py:1008-1023`): cascade RPC, then five per-user Redis purges (#290 R6), then `admin.auth.admin.delete_user` (Supabase Auth). Client side: `SmartCompareApp/src/screens/EditProfileScreen.tsx:135-142` calls the route, `clearAiConsent`, `clearSession`.

| # | Data | Collected at | Stored at | Retention (implemented) | Receives | Purpose | Deletion today (025) | Deletion under 043 |
|---|---|---|---|---|---|---|---|---|
| T1 | Email address | client `authService.ts` register/login bodies; social id_token claims; backend `auth_service.py:397-410` (register), `:827-833` (social) | Supabase Auth (auth.users); `public.users.email` | until account deletion; no expiry | Supabase (P2); Apple/Google as identity provider only for social sign-in (P11, P12) | account, sign-in, password reset | auth user deleted (Supabase Auth); `users.email` KEPT (025 does not null it; measured in PR #290 body) | `users.email` = NULL (043:205); auth user deleted |
| T2 | Password | register/login body -> backend -> `client.auth.sign_up` (`auth_service.py:397-400`) | Supabase Auth only (hashed by Supabase; never in `public.*`) | Supabase-managed | Supabase (P2) | sign-in | deleted with the auth user | same |
| T3 | Display name | `PUT /api/v1/auth/profile` -> `auth_service.py:906` | `users.display_name` | until deletion | Supabase | profile | KEPT by 025 | NULL (043:206) |
| T4 | Sign-in provider; Apple full name scope | `authService.ts:1037-1041` requests FULL_NAME + EMAIL; backend stores `auth_provider` only (`auth_service.py:830`) | `users.auth_provider`; any name claim stays in Supabase Auth user metadata (NOT VERIFIED whether GoTrue stores it) | until deletion | Apple / Google, Supabase | social sign-in | `auth_provider` KEPT | NULL (043:207) |
| T5 | Demographics: age_group, gender, governorate, language, country (+ cohort_match snapshot, submitted_at) | client `api.ts:996-1002,1044` -> `auth_routes.py:1516-1560` (language/country auto-derived from Accept-Language / CF-IPCountry, `:1505-1512`) -> `database_service.py:881` | `users.demographics_profile` (JSONB) | until deletion | Supabase; OpenAI receives ONLY country, language, governorate and cohort-level aggregate priors, never raw age/gender (`extraction_service.py:2017-2045`) | cohort personalization (ENABLE_COHORT_PERSONALIZATION ON in prod since 2026-05-05 per CLAUDE.md) | KEPT by 025 | NULL (043:215) |
| T6 | Preferences (priorities, budget, lifestyle, brand_attitude, ai_sharing_enabled, notifications_*) | `api.ts:478` -> `auth_service.py:958` | `users.preferences`; snapshots `user_preference_history` (`database_service.py:959`) | until deletion; history append-only, no expiry | Supabase; OpenAI (priorities, budget level etc. in the verdict prompt) | personalization | `users.preferences` NULL (025:60); `user_preference_history` rows KEPT | both erased (043:211, :198) |
| T7 | Behaviour profile (derived) | derived from `user_events` tab dwell (`structured_comparison_service.py:5221-5233`, `behavior_service.py`) | `users.behavior_profile` | until deletion; recomputed | Supabase; influences scoring weights only (not sent raw to OpenAI) | personalization | NULL (025) | NULL (043:213) |
| T8 | Device fingerprint hash (SHA-256 of app id + OS build id + random nonce) | client `deviceFingerprint.ts:27-35` -> `X-Device-Fingerprint`; backend `auth_routes.py:521-523` | `users.device_fingerprint_hash`; `referral_invites` (device field); Redis `anon:{fp}` counters (`usage_service.py:61`) | users: until deletion; Redis daily 24 h / monthly ~32 d | Supabase, Upstash | anti-farming of the free quota, referral abuse checks | NULL (025) | NULL (043:225) |
| T9 | Expo push token | `pushTokenService.ts:81-90` -> `auth_routes.py:1314` | `users.expo_push_token` | until deletion | Supabase; Expo push service (P7) with each push; Apple APNs downstream | referral and re-engagement notifications | NULL (025) | NULL (043:221) |
| T10 | Comparison queries (typed product names; link URLs; camera result "brand name vs brand name") and the full result | text routes; `url_routes.py:201-202` (query = "url1 vs url2"); `image_routes.py:429` | `comparisons` (`database_service.py:470`: full_response, query, input_type, product_names, user_id) | until the user deletes the entry (`database_service.py:542-552`, DELETE /comparisons/{id}) or the account; no expiry job | Supabase; OpenAI (the query text, P1); search providers and retailer sites receive product search terms (P5, P6, P13) | the comparison, history, sharing | DELETED (025:38) | DELETED (043:185), after detaching other users' refs (043:175-183) |
| T11 | Photos (camera / picker) | `api.ts:245-285` multipart -> `image_routes.py`; sent in memory as base64 to OpenAI vision (`openai_service.py:199-217`) | NOT written to disk or DB by our code (`TEMP_DIR` is created at `image_routes.py:149-150` and never written - grep); OpenAI keeps abuse-monitoring logs up to 30 days (P1) | none on our side | OpenAI | product identification | n/a (not stored) | n/a |
| T12 | Link-mode page text | `/url/compare` fetches the two pages and sends up to 4,000 chars of each to OpenAI (`url_extraction_service.extract_with_ai`; U3a PR #274 evidence) | not stored except inside `comparisons.full_response` | as T10 | target retailer site (fetched by our server), OpenAI | compare by link | as T10 | as T10 |
| T13 | Search log rows | `database_service.py:745-799` (query, input_type, products_found, success, cost, duration_ms, user_id if signed in, error_message, is_synthetic) | `search_logs` | no expiry job (no retention cron in `scripts/`) | Supabase; read by admin analytics (`analytics_service`) | operations, analytics, cost control | rows with user_id DELETED (025:39); anonymous rows (no user_id) never | same (043:186); anonymous rows untouched |
| T14 | In-app events | `api.ts:888-898` -> `feedback_service.py:271,304` (event_type, event_data, user_id, comparison_id, session_id) | `user_events` | no expiry job | Supabase | analytics; tab-dwell feeds T7 | user's rows DELETED (025:36); anonymous rows never | same (043:173) + other users' refs to the user's comparisons detached |
| T15 | Feedback and Contact Us messages | `FeedbackCard`, `ContactUsScreen.tsx:84-96` -> `feedback_service.py:236` (useful, mattered_most, change_suggestion free text, user_id, comparison_id) | `comparison_feedback` | no expiry job | Supabase; (ENABLE_FEWSHOT_ROTATION, fail-closed, not registered: verdict text + product names of feedback-rated comparisons could become prompt examples, `scripts/cron_few_shot_rotation.py:1-40`) | quality, support | user's rows DELETED (025:37) | same (043:174) |
| T16 | Usage counters | `usage_service.py:250-261, 698-702`, `cache_service` `usage:{uid}:{day}`; lifetime RPC `increment_lifetime_comparisons` (`usage_service.py:514,706`) | Redis `usage:daily:{uid}:{d}` (24 h), `usage:monthly:{uid}:{m}` (~32 d); `user_usage` table; `users.lifetime_comparisons_used`, `last_comparison_at` | Redis TTL; table until deletion | Upstash, Supabase | free-tier limits | `user_usage` DELETED (025:43); users counters KEPT; Redis expire by TTL | table DELETED, users counters 0/NULL (043:187, :214, :223); Redis expire by TTL (not purged, #290 R4 KEEP list) |
| T17 | Referral data: referral_code, invites, redemptions, deep-review credits, bonus counters | `referral_service.py:106, 331-339, 537, 851-910`; register `invite_code` | `users.referral_code`; `referral_invites`, `referral_redemptions`, `deep_review_credits` | no expiry job; bonus rows expire logically after 7 days (`BONUS_EXPIRY_DAYS = 7`, `referral_service.py:46`) | Supabase | Smart Decision Referrals (ENABLE_REFERRAL_SYSTEM ON in prod per CLAUDE.md SESSION 65b) | invites/redemptions DELETED (025:46-55); `referral_code`, bonus counters KEPT; `deep_review_credits` KEPT | all erased (043:188-195, :218-220) |
| T18 | Attribution source ("how did you hear") | `POST /auth/attribution` -> `database_service.py:919` | `users.attribution_source` | until deletion | Supabase | marketing analytics | KEPT | NULL (043:224) |
| T19 | Consent records (terms accepted at, terms version AS SENT, age attested at) | `consent_service.consent_columns` at register/social (`auth_service.py:409, 832`); ENABLE_CONSENT_PERSIST ON in prod since 2026-09-24 | `users.terms_accepted_at`, `terms_version`, `age_attested_at` | until deletion | Supabase | evidence of acceptance | KEPT | NULL (043:227-229; owner privacy default UR5) |
| T20 | AI-processing consent | `aiConsent.ts:78-86` | device AsyncStorage `@qaren_ai_consent_<userId>` `{version, at}` only; no server record | until account deletion on that device (`EditProfileScreen.tsx:138-140`); survives logout | none | evidence of the 5.1.2(i) permission | cleared on the device that deletes | same |
| T21 | IP address (security log) | `rate_limiter.audit_client_ip` (`app/middleware/rate_limiter.py:62-70`) = `request.client.host` with ENABLE_PROXY_AWARE_RATELIMIT OFF (prod) = the TCP peer (Railway edge per CLAUDE.md; NOT VERIFIED it can never be the user's IP); written at `auth_routes.py:662` (invite_code_redeemed, with user_id), `:690`, `:1067` (brute_force_lockout, NO user_id, details email_hash = sha256(lowercased email)[:16]), `:713` (login_failed, NO user_id), `:731` (login_success, with user_id) | `admin_audit_log.ip_address` (`audit_service.py:31-38`) | no expiry job | Supabase | security, abuse forensics | KEPT on all rows | NULLED on rows with the user's user_id (043:200-202); unlinked login_failed / lockout rows keep the IP (PR #290 C10b) |
| T22 | Request IP in platform logs | Railway edge / HTTP logs; uvicorn access log | Railway platform | platform schedule (NOT VERIFIED) | Railway (P3) | hosting | not touched | not touched |
| T23 | Application logs | `logger.*` lines carry user ids and some queries (e.g. `database_service.py:433-434` logs user_id) | Railway logs | platform schedule (NOT VERIFIED) | Railway | operations | not touched | not touched |
| T24 | Crash / performance data (backend) | `sentry_service.py:300-328`: send_default_pii False, include_local_variables False, traces 0.1, before_send scrub | Sentry org `qaren-rr` (EU region, see P4) | Sentry plan retention (NOT VERIFIED) | Sentry | diagnostics | not touched | not touched |
| T25 | Crash / performance data (app) | `sentry.ts:235-245` (sendDefaultPii false, traces 0.1, scrub hooks); DSN host `*.ingest.de.sentry.io` | Sentry | as T24 | Sentry | diagnostics | not touched | not touched |
| T26 | Device storage | AsyncStorage: `@qaren_user`, `@qaren_recent_searches` (`HomeScreen.tsx:94`), `@qaren_onboarding_draft_v1`, `@qaren_free_comparisons_used`, `@qaren_language`, `@qaren_push_token_registered`, `@qaren_push_preprompt_answered`, `@qaren_rtl_bootstrapped`, `qaren.demographicsPromptState.v1`, `legal_cache_{privacy,terms}`; SecureStore: `qaren_token`, `qaren_refresh_token`, `device_fp_nonce`, `qaren_device_id_v1` | the device | until removed | none | app state | delete handler clears tokens + `@qaren_user` + AI consent only (`authService.ts:626-637`); `@qaren_recent_searches` SURVIVES (follow-up UR7) | same (client unchanged by 043) |
| T27 | Shared comparison links | POST /share/{comparison_id} -> `comparisons.share_token` | `comparisons` | until the comparison or account is deleted | anyone holding the link (public GET strips personalization per CLAUDE.md) | sharing | deleted with comparisons | same |
| T28 | Revocation and lockout keys | `revoked:{sha256(token)}` 1 h; `failed_login:{sha256(email)[:16]}` 900 s (`auth_service.py:44-45, 1190-1255`) | Upstash | TTL | Upstash | security | expire by TTL | same |
| T29 | Per-user view caches | `home:savings:{uid}` 6 h, `home:smart_pick:{uid}`, `profile_recent`, `monthly_stats`, `priorities_weighted` 5 min | Upstash | TTL | Upstash | performance | purged at deletion (#290 R6, live since merge) | same |
| T30 | Self-critique rows | `verdict_critique_service.py:279` (only with ENABLE_SELF_CRITIQUE, default OFF) | `verdict_critiques` | no expiry | Supabase | quality | not in 025 | not in 043 (no user_id column measured; NOT VERIFIED) |

Derived findings the policy must respect:
- F-A. Nothing in `scripts/` expires `search_logs`, `user_events`, `comparison_feedback`, `admin_audit_log` or `comparisons` (crons present: `cron_eval_nightly`, `cron_expire_bonuses`, `cron_few_shot_rotation`, `cron_index_sitemaps`, `cron_reengagement`, `cron_warm_price_cache`). Account-linked data therefore lives until the account (or the single comparison) is deleted; anonymous rows have no retention period at all.
- F-B. With 043 unapplied, "delete your account and all associated data" is FALSE: 025 keeps 23 non-null `users` columns including email, display_name, demographics, consent columns, referral code, attribution (PR #290 body, measured on PG18), keeps rows in `deep_review_credits`, `re_engagement_events`, `pain_workflow_events`, `user_preference_history`, and keeps the audit IP.
- F-C. Even under 043: a de-identified stub (id, created_at, updated_at) survives in branch B (removed in branch A with the auth user); unlinked security rows keep the IP; Railway / Sentry / OpenAI / backup copies are outside the erase; `@qaren_recent_searches` stays on the device; accounts deleted from the Supabase dashboard (not the app) are not fully erased (#291 / PRECHECK section 9 f).
- F-D. No server-side record of the AI-processing consent exists (T20).
- F-E. `pain_workflow_events` has no writer in `app/` or `scripts/` at 845ece15 (grep `pain_workflow` finds only the prompt loader); 043 deletes its rows anyway.

---

## 2. Processor and recipient list (from the code)

"Flag state" is per CLAUDE.md at 845ece15 unless marked NOT VERIFIED. "Region" only where code or a document states one.

| # | Recipient | Data it receives | Where in code | Gate and state | Region |
|---|---|---|---|---|---|
| P1 | OpenAI (chat completions incl. vision; moderations) | typed product names, link page text, photos (base64), profile preferences, country, language, governorate, cohort aggregate priors, search-result snippets; moderation input text | `openai_service.py:141-217, 328, 403`; `extraction_service.py` (8 sites); `content_safety_service.py:252`; `url_extraction_service.py`; `verdict_critique_service.py:163`; `image_service.py` (15 call sites via `guarded_llm_create`) | always on; no `user`, `metadata`, `store`, `safety_identifier` sent (RESEARCH_DIGEST U3b, AST scan of 17 sites) | US (fact base 2026-05-06; NOT VERIFIED for this org) |
| P2 | Supabase (Postgres + Auth) | every T row stored in a table; email + password via Auth; Auth emails (confirmation, reset) | `database_service.py`, `auth_service.py` | always | NOT VERIFIED (dashboard) |
| P3 | Railway | all request traffic and application logs (T22, T23) | `railway.json` | always | NOT VERIFIED (dashboard) |
| P4 | Sentry (two projects, org `qaren-rr`) | scrubbed error and performance events from backend and app | `sentry_service.py:283-328`; `SmartCompareApp/src/services/sentry.ts:235-245`; `app.json:252` `https://de.sentry.io/` | backend: only when `SENTRY_DSN` set (set per CLAUDE.md); app: fallback DSN always | EU, Frankfurt: storage location is per organization and the app DSN is `*.ingest.de.sentry.io`; https://docs.sentry.io/organization/data-storage-location/ (2026-10-05) |
| P5 | Upstash (Redis) | user-id-keyed counters and caches (T16, T28, T29), device-fingerprint counters (T8), cached comparison/product data | `cache_service.py`, `usage_service.py` | always | NOT VERIFIED (dashboard) |
| P6 | Serper (Google search API) | product search terms derived from the user's query | `serper_service.py` (`google.serper.dev`) | key set; on `web` `SERPER_LIFETIME_LIMIT=0` (CLAUDE.md says every search leg then goes to Bright Data) - which provider serves live searches is NOT VERIFIED | NOT VERIFIED |
| P7 | Expo push service (then Apple APNs) | push token + notification title/body (re-engagement bodies contain product names and "people near you" lines, `reengagement_service.py:316-366`) + deep-link data | `push_service.py:22` (`exp.host`) | referral pushes: ENABLE_REFERRAL_SYSTEM ON; re-engagement: ENABLE_REENGAGEMENT_PUSHES (prod state NOT VERIFIED); bonus expiry: ENABLE_BONUS_EXPIRY_PUSHES (NOT VERIFIED) | NOT VERIFIED |
| P8 | Expo EAS Update (`u.expo.dev`) | update requests from the app (device platform/runtime headers, network IP - platform knowledge, NOT VERIFIED) | `app.json:267-268` | always in store builds | NOT VERIFIED |
| P9 | Bright Data (SERP API) | product search terms | `brightdata_service.py:41` | ENABLE_BRIGHTDATA_FALLBACK armed on `web` + `price-warmer`, budget gate ON (CLAUDE.md) | NOT VERIFIED |
| P10 | Firecrawl | retailer page URLs (built from product search terms) | `firecrawl_service.py:13` | ENABLE_FIRECRAWL true | NOT VERIFIED |
| P11 | Scrape.do | retailer page URLs | `scrapedo_service.py:13` | ENABLE_SCRAPEDO true | NOT VERIFIED |
| P12 | Apple (Sign in with Apple; APNs) | identity exchange initiated by the user (email, full name on first sign-in); push delivery | `authService.ts:1037-1045`; via P7 | user choice | n/a |
| P13 | Google (Google Sign-In) | identity exchange initiated by the user | `authService.ts:18-30, 831-853` | user choice (Google sign-in reported failing on preview builds, CLAUDE.md) | n/a |
| P14 | YouTube Data API (Google) | product names as search terms | `youtube_service.py:47-48` | ENABLE_YOUTUBE_SOURCE, prod state NOT VERIFIED (not in CLAUDE.md flag lists) | n/a |
| P15 | Retailer websites and their search APIs (noon, Salla stores, Algolia `*-dsn.algolia.net`, Unbxd `search.unbxd.io`, Magento/OCC endpoints, iHerb, pharmacies, etc.) | product search terms or product page requests from OUR servers; never the user's identity | `price_service.py`, `algolia_service.py:297`, `unbxd_service.py:192`, registry `data/bh_gcc_sources.json` | ENABLE_BH_GCC_CATALOG_SOURCES ON | n/a (third parties, not processors) |
| P16 | Cloudflare | email sent to `support@` / `privacy@` / `legal@qaren.app` via Email Routing (runbook section 3 A4.3); DNS/proxy of `qaren.app` once attached; `cloudflare-workers/qaren-redirect` | not in app code | Email Routing state NOT VERIFIED (LL-13); does NOT front the API today per `docs/privacy-data-inventory.md:49` | NOT VERIFIED |
| P17 | Zyte | none on the user path (off-clock seed only, curated product list) | `zyte_service.py:52`; `structured_comparison_service.py:6352-6362` | ENABLE_ZYTE_RENDER OFF | excluded from the policy list (no user data) |
| P18 | frankfurter.app | currency codes only | `exchange_rate_service.py:173` | always | excluded (no personal data) |

Could not classify / not verified: Supabase Auth email sender (Supabase SMTP or custom SMTP); whether GoTrue keeps the Apple/Google name claim in `auth.users.raw_user_meta_data`; Yotpo and judge.me modules have no production importer (CLAUDE.md) and are excluded; `api.salla.dev` (salla slug resolve, ENABLE_SALLA_SLUG_RESOLVE default OFF) is retailer-class P15.

Grep recipe used (reproducible): `grep -rhoE 'https?://[a-zA-Z0-9.-]+' app/services app/api app/utils app/main.py scripts/cron_*.py | sort | uniq -c`, then `grep -rnE '(firecrawl\.dev|scrape\.do|zyte\.com|algolia\.net|unbxd|exp\.host|googleapis\.com/youtube|yotpo|frankfurter|brightdata)'`; client: same over `SmartCompareApp/src app.json`.

---

## 3. Contradiction list (current text vs sections 1-2)

Severity: FALSE = contradicted by code; OVER = overbroad or unverifiable promise; GAP = required content missing; STALE = brand/date/draft.

Privacy policy (`app/legal/privacy_policy.md`; the EN landing `landing/privacy.html` mirrors it verbatim, 45 of 46 body units measured; the AR page translates it):
- C1 STALE `:3` "Qaren - Product Comparison App"; `:11` "Qaren ... operates the Qaren mobile application"; `:74`, `:82` Qaren. Landing EN Qaren at 199, 271, 277; AR the Arabic old name in body lines 193-274.
- C2 STALE `:5` "Last Updated: March 26, 2026"; `:7` and `:95` DRAFT/template lines; landing EN 195/196/288, AR 189/190/282.
- C3 GAP `:11` no named controller, no address (M1, M2).
- C4 GAP `:16-23` omits demographics (T5), device fingerprint (T8), push token (T9), attribution (T18), consent records (T19), referral data (T17), Contact Us messages (T15), link page text (T12), behaviour profile (T7), audit IP (T21) - runbook row 11.
- C5 OVER `:22` "Device type, operating system, and app version" - the backend stores none of these; only Sentry device context (T24-T25). Replace with what is true.
- C6 GAP/OVER `:23` photos "not stored on our servers" is true for our servers (T11) but omits that they go to OpenAI and sit in its abuse-monitoring logs up to 30 days (P1).
- C7 FALSE-by-omission `:41` processor list omits Expo push (P7), EAS Update (P8), Bright Data (P9), Firecrawl (P10), Scrape.do (P11), Apple/Google sign-in (P12, P13), YouTube (P14 if on), Cloudflare email (P16); no equal-protection sentence (M5).
- C8 FALSE `:46` "Deleted upon account deletion request" while 025 is live (F-B).
- C9 FALSE `:48` "Anonymous Analytics: Aggregated, non-identifiable" - `search_logs` / `user_events` are row-level, user-linked while the account exists, with no retention period (T13, T14, F-A).
- C10 STALE `:49` cache periods describe product data, not personal data (L2 caches are 30 d / 24 h / 14 d per CLAUDE.md); drop.
- C11 OVER `:54` "View your personal data through the App" - only history, profile and preferences are viewable.
- C12 FALSE `:56` "Delete your account and all associated data from within the App" (F-B today; F-C even after 043).
- C13 GAP `:57` export by contacting us: no deadline (owner: 15 working days).
- C14 FALSE `:58` "Withdraw Consent: Stop using the App" is not a withdrawal mechanism (M10); the U3b control is the real one.
- C15 GAP `:60-66` no breach-notification commitment (M14).
- C16 GAP `:68-70` under-13 only; nothing on users without full legal capacity (M13).
- C17 OVER `:74` "We comply with applicable data protection laws" - unverifiable claim.
- C18 OVER `:78` "notify you ... through the App or via email" - no change-notification mechanism exists in code.
- C19 FALSE `:80-88` section 11: "we participate in OpenAI's Data Sharing Program" is unverified (D3, an org dashboard setting) and the opt-out ("Settings -> Privacy -> Help improve AI quality") routes nothing: `select_client_for_user` (`openai_service.py:82-91`) has zero callers (#266), the toggle lives on Profile (`ProfileScreen.tsx:106-140`) not "Settings -> Privacy", and it cites both PDPLs for a right the code does not honour.
- C20 OVER `:93` `privacy@qaren.app` - mail delivery not verified (LL-13; qaren.app web is a 522).
- C21 FALSE (AR only) `landing/ar/privacy.html:273` garbled phrase (see 4.5).

Terms of service (`app/legal/terms_of_service.md`; landing mirrors, 47 of 48 units verbatim):
- C22 STALE `:3, :11, :15, :41, :56, :83, :91` Qaren; `:5` date; `:7, :98` DRAFT.
- C23 FALSE `:41` "The App, including its design, code, AI models, and branding, is the property of Qaren" - no entity "Qaren" exists (D5) and the AI models are OpenAI's.
- C24 OVER `:60` "Loss of data beyond what is covered by our backup systems" implies backups we do not operate (Supabase platform, NOT VERIFIED).
- C25 FALSE `:65` "permanently remove all your data" (F-B, F-C).
- C26 OPEN `:75, :79` Bahrain law and courts - correct only if the controller is in Bahrain (D5, M17).
- C27 FALSE `:85` "Premium subscribers earn 10 per conversion" - no subscription is sold (D2-A, #255); the code grants 10 to `subscription_tier='premium'` (`referral_service.py:700`), a tier set only by hand (demo account). Drop the sentence.
- C28 FALSE (partly) `:91` "Disable any type in Settings -> Notifications" - `send_push` / `send_loop2_push` ignore `notifications_enabled` (#264); referral pushes are stoppable only in iOS Settings.
- C29 OVER `:96` `legal@qaren.app` - unverified mailbox; a third address not needed (see form item 5).
- C30 GAP no AI-generated-content clause, no not-medical-advice clause for supplements, no free-limit disclosure, no Apple EULA position (fact base flags A, B, G; M17).

Consent sheet, onboarding and other copy (`SmartCompareApp/src/i18n/en.json`):
- Consent sheet `:694-698` is ACCURATE against P1 (product names, links with page text, photos, preferences incl. budget level, country, language, area; no name/email/account). No change needed; the policy must match it, not the reverse.
- C31 OVER `:567-568` "What we never share: Your name. Your email. Not now, not ever." - email and name are disclosed to processors (Supabase stores them; Apple/Google supply them; Supabase sends auth emails). True only if scoped ("never to OpenAI or retailers" / "never sold"). Copy fix belongs with U3b or U8 (onboarding key; no consent fence).
- C32 FALSE `:417` "profile.aiSharing.subtitle ... Share your queries to make MYEZ smarter" - the toggle does nothing (#266); U3b removes it under D3 = A.
- C33 low `:270-271, :742-743` "We work for you - never paid by sellers." - true today (no affiliate code found); becomes false the day an affiliate link ships (Awin/CJ were explored). Note only.

App Privacy inventory (`docs/privacy-data-inventory.md`):
- C34 OPEN row 5 SearchHistory purposes omit Analytics, while `search_logs` feeds admin analytics (`analytics_service` daily stats / popular queries). Changing it is an app.json + inventory edit (native). Orchestrator/counsel call; out of U8's files.
- C35 OPEN "Not collected: IP address" (`:49`) rests on `request.client.host` being Railway's edge, not the user (T21), and ignores platform HTTP logs (T22). Unverifiable from code.

Runbook listing text (`APP_STORE_LAUNCH_RUNBOOK.md` section 6):
- C36 FALSE `:351` "You can delete your account and its data from inside the app at any time." while 043 is unapplied (F-B).
- C37 GAP `:315` Support URL leads to a mailto with no name or address (M2).
- C38 OPEN `:318` copyright `2026 <OWNER per D5>`.

Age, entity, Beta, subscription: age 13+ is consistent everywhere (ToS `:25`, consent attestation `en.json:994`); the entity is missing everywhere (C3, C23); no Beta wording exists in the legal docs (the decisions-pending default "Beta - early access" is superseded by the owner's "no Beta label"); subscription wording = C27 only.

---

## 4. The spec

### 4.1 Ordering (binding proposal for the orchestrator)

1. **U3b merges first.** The new policy describes the AI-processing consent and its withdrawal control (M10) and, under D3 = A, the absence of any sharing toggle. Those must exist in the shipped app on the publication date. U3b fixes the control's path; U8's text uses `<PLACEHOLDER:WITHDRAW_PATH>` until then (filled from U3b's merged code, not from the owner). Under D3 = B, U3b ships the separate opt-in and `AI_CONSENT_VERSION = 2`; U8 then uses variant B text.
2. **Migration 043 is applied in production BEFORE the policy is published** (PRECHECK grid sent back -> ONE_PASTE -> POSTCHECK -> BACKFILL only if PRECHECK section 9 c or d > 0). "Published" = the backend deploy that serves the new markdown (merge to main auto-deploys in about 90 s) and the landing redeploy. If 043 is not applied, U8 must ship deletion variant D-OLD (4.2 section 9), which is truthful but describes 025's partial erase; recommended: do not ship D-OLD, apply 043 first.
3. **Merge U8, then fire the landing lever in the same window:** `railway up landing --path-as-root -s qaren-landing -d` (owner or delegated). The ASC Privacy Policy URL points at the landing page, so the landing must not lag the in-app copy. Verify with curl: 200, no "DRAFT", no unresolved placeholder.
4. **The production `eas build` must come from a main that contains U8** (consent.ts TERMS_VERSION, LegalScreen language parameter). The in-app EN text updates for every build at deploy time (server-served); the AR in-app text and the new TERMS_VERSION reach phones only by OTA or the store build.
5. Prerequisite owner actions that make sentences true: OpenAI org data sharing OFF (D3 = A); the three mailboxes receive mail (form item 5); hosting regions read (form item 9).

### 4.2 Privacy policy (English) - section outline, sources, near-final text

Front matter: `# Privacy Policy`, `**MYEZ**`, `*Effective date: <PLACEHOLDER:EFFECTIVE_DATE>*` (filled by the orchestrator at merge with the publication date; owner rule I6), no DRAFT line.

1. **Who we are.** Source M1, M2; form items 1-4.
   Text: "MYEZ (the "App") is provided by <PLACEHOLDER:CONTROLLER_NAME><PLACEHOLDER:TRADE_NAME_CLAUSE>, <PLACEHOLDER:POSTAL_ADDRESS> ("we", "us"). We decide how and why your personal data is processed in the App. Contact: <PLACEHOLDER:PRIVACY_EMAIL>." Variant D5-B adds "commercial registration number <PLACEHOLDER:CR_NUMBER>".
2. **Summary.** Near-final: "MYEZ compares two products for you. To do that we process the products you enter or photograph, your account details and the preferences you choose to give us. We use OpenAI to identify products and write comparisons, and we search retailer websites for prices. We do not sell your personal data, we do not show third-party ads and we do not track you across other companies' apps." Sources: P1, P15; `NSPrivacyTracking=false` (inventory `:27`); no ad SDK (inventory `:58`).
3. **What we collect, why, and on what basis.** One table per category, rows T1-T19, T21. Columns: data, source, purpose, legal basis, required or optional. Legal-basis column = `<PLACEHOLDER:LEGAL_BASIS_*>` per row ONLY if counsel reviews (form item 8); default text when no counsel review: contract necessity for account, comparison, history, security rows; consent for AI processing (T10-T12 to OpenAI), demographics (T5), push notifications (T9), attribution (T18) - research M4 and the minors pitfall (RESEARCH_DIGEST U3b pitfalls) say counsel decides. Required/optional (code facts): email and password required to register; display name, demographics, preferences, attribution, push optional (the app works without them: demographics sheet is dismissible `demographics_dismissed_*`, push is opt-in `pushTokenService.ts`); what happens if not provided: "you cannot create an account" / "comparisons are less personalised".
4. **Comparisons made with AI (OpenAI).** Source M6, P1, consent sheet `en.json:695`, OpenAI page.
   Near-final (D3 = A): "To identify products and write your comparison, we send OpenAI (contracting entity NOT VERIFIED; name it from the owner's OpenAI account terms) the product names you type, the links you paste together with the text of those web pages, and the photos you take or pick. We may also send the preferences on your profile, such as your priorities and budget level, and your country, language and area. We do not send your name, email address or account identifiers. We ask your permission in the App before your first comparison or scan, and you can withdraw it at any time in <PLACEHOLDER:WITHDRAW_PATH>; without it the App cannot run comparisons. Under OpenAI's API terms, data sent to its API is not used to train its models unless the developer opts in, and we have not opted in; OpenAI keeps API data in abuse-monitoring logs for up to 30 days. Comparisons are generated by AI and can be wrong; see our Terms of Service." Source for the OpenAI sentences: https://developers.openai.com/api/docs/guides/your-data (2026-10-05): "not used to train or improve OpenAI models (unless you explicitly opt in...)"; abuse monitoring default 30 days; moderations: no retention. "we have not opted in" is TRUE only after the owner turns data sharing off (form item 6).
   Variant D3 = B: replace the opt-in sentence with "Separately, and only if you turn on 'Help improve AI quality', we let OpenAI use your comparison queries to improve its models. This is off unless you turn it on, and turning it off stops future sharing." and require `AI_CONSENT_VERSION = 2` (U3b).
5. **Who receives your data.** Source M5, section 2. Near-final list (one line each): Supabase (database and sign-in), Railway (hosting), Upstash (temporary storage and usage counters), Sentry (error reports, EU), OpenAI (section 4), Expo (push notifications and app updates), Apple and Google (only if you sign in with them; Apple also delivers notifications), search providers Serper and Bright Data and page-retrieval providers Firecrawl and Scrape.do (they receive product search terms and retailer page addresses, never your identity), Cloudflare (delivery of email you send to our addresses)<PLACEHOLDER:YOUTUBE_CLAUSE>. Then: "Each provider processes data only to provide its service to us, and we require each to protect it at least as well as this policy does." (the equal-protection sentence; contracts are the owner's, M5) + "We may disclose data where the law requires it." YOUTUBE_CLAUSE is filled by the orchestrator from the prod flag read (names only), not by the owner: ", and YouTube (Google) receives product names when we look for review videos" if ENABLE_YOUTUBE_SOURCE is on, else empty.
6. **Retailer websites.** Source P15. Near-final: "To find prices we search public retailer websites and their search services for the products in your comparison. Those requests come from our servers and contain only product search terms; they do not include your identity."
7. **Transfers outside Bahrain.** Source M7, P1-P16, form item 9. Near-final: "Our providers process data outside Bahrain, including in the United States (OpenAI) and Germany (Sentry)<PLACEHOLDER:HOSTING_REGIONS_CLAUSE>. <PLACEHOLDER:TRANSFER_BASIS>". TRANSFER_BASIS default when no counsel: "We transfer data only to providers that are required by contract to protect it." Research note (M7): Bahrain Order 42/2022 lists the US and Germany as adequate - counsel to confirm before citing it (NOT VERIFIED by this agent).
8. **How long we keep data.** Source M8, F-A, T16, T28, T29, form item 10. Near-final: account data, preferences, demographics, history, feedback and activity records "until you delete them or your account"; usage counters "up to about 32 days"; sign-in security records "<PLACEHOLDER:SECURITY_LOG_RETENTION>"; records not linked to an account (anonymous searches and events) "<PLACEHOLDER:ANON_LOG_RETENTION>"; photos "not stored by us; OpenAI up to 30 days"; "copies in our providers' backups and logs are deleted on their schedules".
9. **Deleting your account.** Source M11, PR #290 "Policy statement U8 may use" (binding text, corrected per C10), F-C. Path: "Profile, then the settings icon, then Edit profile, then Delete account" (EditProfileScreen; runbook review note `:369`).
   Variant D-NEW (043 applied + POSTCHECK passed + BACKFILL if needed + every PRECHECK 9 f row = 0 or #291 shipped): use the PR #290 paragraph verbatim, with "[retention period]" = SECURITY_LOG_RETENTION and the bracketed branch-A clause kept or dropped per PRECHECK section 4. Must say "from our servers" (UR7: `@qaren_recent_searches` survives on the device until that follow-up ships) and must not claim erasure of accounts removed outside the App.
   Variant D-OLD (043 not applied; NOT recommended): "When you delete your account we delete your comparisons, searches, feedback, activity, usage and referral records and your sign-in account, and remove your preferences, notification token and device identifier from your profile. Your email address, name, demographic answers and some profile details remain in our database until <...>" - this is the 025 truth and reads badly; it exists only to show why 043 must be applied first.
   Plus: Sign in with Apple token revocation is NOT done (U11 unbuilt) - say nothing about revocation (do not promise it).
10. **Your rights.** Source M9, M10, owner answers. Near-final: access and a copy of your data (we reply within 15 working days), correction, deletion, objection and restriction (we reply within 10 working days), withdrawal of consent (in the App at <PLACEHOLDER:WITHDRAW_PATH>, or by email; withdrawal does not affect processing before it), how to ask (<PLACEHOLDER:PRIVACY_EMAIL>; we may ask you to confirm your identity), complaints: Bahrain Personal Data Protection Authority (https://www.pdp.gov.bh) and, variant GCC (form item 7), the Saudi Data and AI Authority (SDAIA). Deadline source: Bahrain PDPL Art 18 (15 working days for access) via https://www.pdp.gov.bh/en/assets/pdf/regulations.pdf (2026-10-05, official search summary); the 10-working-day articles (20, 21, 23) per RESEARCH_DIGEST M9 / pitfalls. KSA 30 days (IR Art 3) is satisfied by the shorter Bahrain SLA.
11. **Notifications.** Source M12, T9, P7, C28. Near-final: "If you allow notifications, we send referral updates (for example when a friend you invited completes a comparison) and, if enabled, up to one reminder a week about your past comparisons. We do not send advertising. You can turn notifications off in your iPhone's Settings at any time<PLACEHOLDER:INAPP_NOTIF_CLAUSE>." INAPP_NOTIF_CLAUSE stays empty until #264 is fixed (today the in-app switch does not stop referral pushes).
12. **Children and young people.** Source M13, ToS `:25`, consent attestation `en.json:994`, form item 11. Near-final: "The App is for people aged 13 and over. We do not knowingly collect data from children under 13; if you believe a child has given us data, contact us and we will delete it." + `<PLACEHOLDER:MINORS_CLAUSE>` (guardian sentence, form item 11).
13. **Security.** Source M14, code. Near-final: "Data is encrypted in transit (HTTPS/TLS) and the App checks our server's certificate before sending data (certificate pinning). Your sign-in tokens are kept in your device's secure storage (Keychain). Administrative functions require a secret key. Error reports are scrubbed of tokens and keys before they leave our servers. If a breach puts your data at risk, we will notify you and the competent authority as the law requires." Sources: `certificatePinning.ts` (13 SPKIs, #253), `authService.ts` SecureStore, `sentry_service.py` scrub, admin routes behind `X-Admin-Key` (`admin_routes.py`, CLAUDE.md). Breach timing words left to counsel (KSA IR Art 24: 72 h to SDAIA per digest).
14. **Data kept on your device.** Source T26. Near-final: "The App keeps your sign-in tokens in secure storage and settings, your recent searches and a cached copy of this policy on your device. Signing out removes your sign-in tokens; deleting the App removes the rest."
15. **Changes to this policy.** Source C18. Near-final: "If we change this policy we will update the effective date above and, for material changes, show a notice in the App before the change applies to you." (A notice mechanism does not exist yet -> open question Q6; until it exists use: "...update the effective date above and publish the new version in the App and on our website.")
16. **Contact.** <PLACEHOLDER:PRIVACY_EMAIL>, <PLACEHOLDER:POSTAL_ADDRESS>, support <PLACEHOLDER:SUPPORT_EMAIL>.

### 4.3 Terms of Service (English) - outline, sources, near-final text

Front matter as 4.2. Sections:
1. **Agreement; who we are.** M17, form items 1-4. "These Terms are an agreement between you and <PLACEHOLDER:CONTROLLER_NAME>..."
2. **The service.** Near-final: "MYEZ helps you compare two products. It gathers specifications, reviews and prices from public sources and uses AI to write a verdict. MYEZ is a decision aid: it does not sell products, and prices come from third-party retailers and can change." Source: listing text runbook `:334-353`.
3. **Eligibility and your account.** Keep ToS `:23-26` (13+, accurate info, one account per person, no automated sign-up) + MINORS_CLAUSE.
4. **Free use and limits.** Source `usage_service.py:138-149`, `en.json:938`. Near-final: "Use of MYEZ is free. Each account can run a limited number of comparisons (currently 3 a day and up to 10 a month, after 3 introductory comparisons). We may change these limits. This version of the App sells no subscriptions or in-app purchases." Source for "no purchases": runbook `:370`, #255.
5. **Acceptable use.** Keep `:30-37`.
6. **AI-generated content and accuracy.** Flags A and B (fact base `:742-756`). Near-final: "Verdicts, summaries and recommendations are generated by AI from public information and may be incomplete or wrong. Prices may be estimated, converted from another currency or out of date; check with the retailer before you buy. Nothing in MYEZ is medical, health, financial or professional advice; for supplements and health products, consult a qualified professional."
7. **Retailers and links.** "Links take you to third-party retailers. We are not responsible for their products, prices, stock, delivery or terms."
8. **Intellectual property.** Fix C23: "The App, its design, code and branding belong to <PLACEHOLDER:IP_OWNER> (or are licensed to us). Product information and reviews belong to their owners. Your comparison history is yours and is handled under our Privacy Policy." IP_OWNER = CONTROLLER_NAME under D5-A only if the IP licence/assignment exists (runbook D5-A).
9. **Smart Decision Referrals.** Keep the pinned strings ("3 successful invites per device", "7 days"; `tests/test_legal_routes.py:104-123`) and the code facts (`referral_service.py:40, 46, 700`): sharing earns a Deep Review credit; 5 comparisons per conversion; no cash value; abuse checks use device identifiers, email validation and timing (`abuse_detection_service`). DROP "Premium subscribers earn 10" (C27).
10. **Notifications.** Same facts as policy section 11 (C28 fix).
11. **Disclaimers.** Keep `:47` "as is" + `:49-52`; drop the backup sentence (C24).
12. **Limitation of liability.** Keep `:56-61` minus the backup line, named party.
13. **Suspension, termination and deletion.** Fix C25: "You can delete your account in the App at any time (Profile, then the settings icon, then Edit profile, then Delete account). What is deleted and what is kept is described in our Privacy Policy."
14. **Changes.** Keep `:71`, plus the notice wording of policy section 15.
15. **Governing law and disputes.** `<PLACEHOLDER:GOVERNING_LAW>` derived from form item 4 (country of the postal address) unless counsel says otherwise; default when the address is in Bahrain: keep `:75` and `:79`.
16. **Apple.** M17: if the owner does not upload a custom EULA in ASC, Apple's standard EULA applies; state: "If you downloaded the App from the Apple App Store, Apple's Licensed Application End User License Agreement also applies, and Apple is not responsible for the App or for support." (keeps us out of the custom-EULA minimum-terms requirement; counsel to confirm).
17. **Contact.** SUPPORT_EMAIL, POSTAL_ADDRESS (drop `legal@`, C29, unless form item 5 says keep).

### 4.4 Variant forks (one switch each; the GREEN builds all branches as data, the fill-in selects)

| Fork | Values | Text affected | Code affected |
|---|---|---|---|
| D3 | A (recommended) / B | policy 4; profile toggle copy (U3b) | U3b only; B forces `AI_CONSENT_VERSION = 2` |
| D5 | A individual (+ optional trade name, IP licence) / B organisation (CR number) | policy 1, 16; ToS 1, 8, 15, 17; ASC copyright | none |
| Counsel review | yes / no | legal-basis column (4.2 s3), transfer basis (s7), breach wording (s13), minors clause (s12), governing law (s15) | none; if "yes" the fill-in waits for counsel's markup |
| Territories | Bahrain only / GCC (Bahrain + KSA + UAE + Kuwait + Qatar + Oman) | complaint routes (s10: SDAIA added for GCC), transfer section, ToS governing law note | none |
| 043 | applied (D-NEW) / not (D-OLD) | policy 9, ToS 13 | none (owner applies) |

Placeholder map (owner form item -> token; "derived" = filled by the orchestrator, never asked):

| Token | Source |
|---|---|
| CONTROLLER_NAME, IP_OWNER | form 1 (IP_OWNER only once the licence/assignment exists) |
| TRADE_NAME_CLAUSE | form 2 (empty by default) |
| CR_NUMBER | form 3 (D5-B only) |
| POSTAL_ADDRESS; GOVERNING_LAW | form 4; governing law derived from its country unless counsel says otherwise |
| PRIVACY_EMAIL, SUPPORT_EMAIL | form 5 |
| (D3 variant A/B) | form 6 |
| (territories variant) | form 7 |
| LEGAL_BASIS_*, TRANSFER_BASIS, MINORS_CLAUSE wording | form 8 (counsel) or the defaults above; MINORS_CLAUSE presence = form 11 |
| HOSTING_REGIONS_CLAUSE | form 9 (empty fallback) |
| SECURITY_LOG_RETENTION, ANON_LOG_RETENTION | form 10 (B = "12 months" + a cleanup unit before publication) |
| (043 variant D-NEW / D-OLD) | form 12 + POSTCHECK result |
| EFFECTIVE_DATE | derived: publication date |
| WITHDRAW_PATH | derived from U3b's merged code |
| YOUTUBE_CLAUSE | derived from a names-only prod flag read (ENABLE_YOUTUBE_SOURCE) |
| INAPP_NOTIF_CLAUSE | derived: empty until #264 ships |

### 4.5 Arabic plan

- The Arabic translation is produced in the SAME unit as the English, from the final English text, and every Arabic legal page is marked for native review (D11 / LL-14) before the landing redeploy; the PR body lists the review as an owner gate.
- New files: `app/legal/privacy_policy_ar.md`, `app/legal/terms_of_service_ar.md` (served in-app, M16); the AR landing pages are rewritten from them (4.9).
- Measured state of the current AR pages: same heading count as EN (privacy 15 = 15, terms 14 = 14; `landing_measure.json` in the notes folder); DRAFT lines at `landing/ar/privacy.html:190, 282` and `landing/ar/terms.html:176, 266`; the old Arabic brand as a WORD (the #257 fence regex, `ar_brand.json` in the notes folder) at privacy lines 193, 265, 271 and terms lines 179, 182, 212, 227, 253, 258. A plain substring search also hits privacy 188, 200, 201, 206, 219-221, 237, 272-274 and terms 174, 184, 214, 254, but those are the word for "comparison" that contains the old brand's letters, not the brand - T3 must use the word-boundary regex, never a substring test.
- Garbled line: `landing/ar/privacy.html:273`, the "what we never share" sentence reads "عمرك ومثل-جنسك المحدّدَين" (a broken rendering of "your specific age or gender"); the whole section 11 it belongs to is deleted under D3 = A anyway.
- Stale content in the AR pages is the same as C1-C30 (they translate the English); nothing in them is salvageable as legal text. Rewrite, do not patch.
- Arabic text follows the app's copy policy (`SmartCompareApp/src/i18n/.copy-policy.json` banned terms) and uses Western digits, MSA.

### 4.6 Version and date anchors

The EIGHT anchors CLAUDE.md names, all verified at 845ece15 (all read `2026-03-26` / `March 26, 2026`):
1. `app/api/legal_routes.py:30` (privacy `last_updated`)
2. `app/api/legal_routes.py:47` (terms `last_updated`)
3. `app/legal/terms_of_service.md:5`
4. `app/legal/privacy_policy.md:5`
5. `landing/terms.html:184`
6. `landing/privacy.html:195`
7. `app/services/consent_service.py:31` (`TERMS_VERSION`)
8. `SmartCompareApp/src/services/consent.ts:12` (`TERMS_VERSION`)
U8 adds four more that must move with them: `landing/ar/privacy.html:189`, `landing/ar/terms.html:175` (both carry the Arabic "last updated" date today and are NOT in the CLAUDE.md eight), and the date line of the two new `*_ar.md` files. Total 12.

Tests that pin them today: `tests/test_consent_capture_w3_16.py:39` (`TERMS_VERSION = "2026-03-26"` literal) and `:531-545` (B12: route `last_updated` == backend TERMS_VERSION == client literal); `tests/test_legal_routes.py:57-65` (date format only); client suites import the constant (`__tests__/auth/appleButton.s69.test.tsx:30`, `LoginScreen.consent.w3-16.test.tsx:16`, `RegisterScreen.consent.w3-16.test.tsx:26`, `services/authService.consent.w3-16.test.ts:17`) and need no edit. Tests that pin the OLD brand and must change: `tests/test_legal_routes.py:81` and `:91` (`assert "Qaren" in body["content"]`) -> assert "MYEZ". `SmartCompareApp/__tests__/landing.brand.s69.test.ts:21-26, 71-81` exempts legal body text from the brand fence "for U8": U8 removes the LEGAL exemption (brand fence covers the whole legal page) and keeps `ADDRESS_COUNTS` exact (privacy/terms 7 per page) or updates them deliberately if the contact block changes.

Format rule: ISO `YYYY-MM-DD` in code anchors; "Effective date: <Month D, YYYY>" in EN text; the AR text uses the same date in Western digits. The privacy and terms dates are the same date (one TERMS_VERSION).

### 4.7 AI_CONSENT_VERSION rule (answer)

- The fence (`SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts:32-49`) hashes ONLY `aiConsent.title` + `aiConsent.body` (EN then AR). The policy text is not in the hash. `ensureAiConsent` (`aiConsent.ts:72-75, 112-118`) re-asks only when the stored `version` differs from `AI_CONSENT_VERSION`.
- The consent copy is accurate against the code (section 3). Under D3 = A the redraft does NOT change the consent copy, so `AI_CONSENT_VERSION` stays 1 and the fence stays green. The policy changes materially, but the purpose the user agreed to (send these items to OpenAI to produce the comparison) is unchanged; the legal research ties re-consent to a change of purpose (KSA IR Art 11(1)(e), Apple 5.1.2(ii) "repurposing") - so no re-ask is required by either the fence logic or the research item. Counsel may still want existing users told about the new policy (open question Q6).
- Under D3 = B a new purpose (letting OpenAI use the data) appears: U3b bumps to 2 and adds a separate opt-in; U8 must not ship before that.
- U8 must NOT edit `aiConsent.*` keys. If U8 rewrites the onboarding "never share" line (C31), that key is outside the fence.

### 4.8 Files to touch (U8)

Backend: `app/legal/privacy_policy.md`, `app/legal/terms_of_service.md` (replace), NEW `app/legal/privacy_policy_ar.md`, NEW `app/legal/terms_of_service_ar.md`, NEW `app/legal/processors.json` (4.10 T7), `app/api/legal_routes.py` (dates; `lang` query param `en|ar`, default `en`, unknown -> `en`), `app/services/consent_service.py:31`.
Client: `SmartCompareApp/src/services/consent.ts:12`; `SmartCompareApp/src/screens/LegalScreen.tsx` (send `lang` from i18next, cache key `legal_cache_{doc}_{lang}`); optionally the onboarding copy keys of C31 (en.json/ar.json `onboarding.s5.privacy_never_*`) if the orchestrator assigns C31 to U8 rather than U3b.
Landing: `landing/privacy.html`, `landing/terms.html`, `landing/ar/privacy.html`, `landing/ar/terms.html`.
Tests: `tests/test_legal_routes.py` (brand asserts), `tests/test_consent_capture_w3_16.py:39`, NEW `tests/test_legal_docs_u8.py`, NEW client `__tests__/legal/legalScreenLang.u8.test.tsx`, `__tests__/landing.brand.s69.test.ts` (drop the legal exemption), `__tests__/LegalScreen.test.tsx` (endpoint now carries `lang`).
Docs (orchestrator at merge): CLAUDE.md ship-blocker 2 and the "eight anchors" sentence (-> twelve); runbook rows 3, 11, 19 status.
Not U8: `docs/privacy-data-inventory.md` / app.json (C34, C35), #264 (push opt-out), #291, UR7 recent-searches clear, server consent record.

### 4.9 Landing pages: hand-edit vs generation (measured)

- Relation measured: 45 of 46 privacy and 47 of 48 terms markdown body units appear verbatim in the EN HTML (the one miss each is the subtitle the #257 rename changed); headings 15/15 and 14/14. No generator exists: no script in `scripts/` references the legal markdown, and the only regeneration in history is a hand edit (`git show 6bbe14dc`: "Substitution mirrors backend's diff exactly"). The pages are hand-written mirrors that drift only when someone forgets.
- Recommendation: generate. Add `scripts/render_legal_landing.py` (stdlib only, no new dependency: a ~60-line converter for the subset the docs use - `##`/`###` headings, paragraphs, `-` lists, `**bold**`, `*em*`, links, a table renderer for the section 3 table) that writes ONLY the region between two markers (`<!-- legal:begin -->` / `<!-- legal:end -->`) inside each of the four pages, keeping the hand-made chrome (head, wordmark, footer, `hreflang`). A parity test (T5) re-renders in memory and asserts byte equality with the committed region, so drift becomes a red test. Rationale: four pages x every future legal edit; the #257 fence already treats the legal body as derived ("a render of app/legal/*.md", `landing/README.md:25`). Alternative if the orchestrator rejects a new script: hand-edit plus the same parity test written as a normalised-text comparison (the measure script in the notes folder shows the method).

### 4.10 Tests (RED first, then PIN)

RED (fail at base, pass after fill-in):
- T1 `test_no_draft_text`: no case-insensitive "draft", "template", "legal counsel before publication" in the four markdown files and the four landing pages (base: 2 hits per md, 3 per page).
- T2 `test_no_unresolved_placeholder`: no `<PLACEHOLDER` in served docs or landing pages. This is the LAST red to turn green (only the fill-in commit greens it); the orchestrator may merge GREEN-minus-T2 only to a branch, never to main.
- T3 `test_no_old_brand_in_legal_text`: no "Qaren" (Latin) and no standalone Arabic old brand word (reuse `landing.brand.s69` word-boundary regex) in user-visible legal text, after stripping addresses (`qaren.app`, `@qaren.app`, `qaren://`) and identifiers; markdown and HTML.
- T4 `test_en_ar_heading_parity`: same number of `##`/`###` headings and the same section numbering in EN vs AR markdown, and in EN vs AR landing pages.
- T5 `test_landing_matches_markdown` (if generation is accepted, 4.9).
- T6 `test_version_anchors_move_together`: all 12 anchors equal one date; `TERMS_VERSION` (backend + client) equals it; supersedes the narrower B12 (keep B12).
- T7 `test_policy_names_every_processor`: `app/legal/processors.json` rows `{id, name_en, name_ar, kind, personal_data, module, hosts}`; (a) every row with `personal_data: true` has `name_en` in `privacy_policy.md` and `name_ar` in `privacy_policy_ar.md`; (b) every `app/services/*.py` defining a module-level `*_URL` / `*_API_URL` / `BASE_URL` constant with an external host, and every module constructing `AsyncOpenAI(`, `create_client(`, `sentry_sdk.init(` or an Upstash/Redis client, maps to a manifest row or to a `NOT_PERSONAL` allowlist entry with a reason of at least 40 characters (frankfurter, zyte off-clock, schema.org). Reasoned alternative to a full host scan: retailer hosts number in the hundreds (registry JSON) and are one class (P15), so they are one manifest row of `kind: retailer` and are excluded from (b) by module (`price_service`, adapters).
- T8 `test_consent_copy_and_policy_ai_section_agree`: reads `en.json` `aiConsent.body` and the policy section 4; every item in a fixed keyword map (product names, links, page text, photos, preferences, budget, country, language, area, OpenAI) appears in the section; the not-sent trio (name, email, account) appears as not sent; under D3 = A the section contains none of "opt out", "Help improve AI quality", "Data Sharing Program"; same for AR with an Arabic keyword map (written at GREEN, native-reviewed).
- T9 `test_legal_route_serves_new_date_and_lang`: `/api/v1/legal/{privacy_policy,terms_of_service}` return `last_updated == TERMS_VERSION`; `?lang=ar` returns the AR file; unknown `lang` returns EN; legacy paths unchanged.
- T10 client `legalScreenLang.u8`: LegalScreen requests `lang=ar` when i18next language starts with `ar`, caches per language.
- T11 `test_deletion_text_matches_043_state`: the policy deletion section contains the D-NEW marker sentence only when a constant `DELETION_POLICY_VARIANT = "043"` is set (a reviewed constant flipped by the orchestrator after the owner's POSTCHECK) - a forcing function so D-NEW cannot ship by accident before 043.
PIN (green at base and after): `tests/test_legal_routes.py` route/no-auth/format/referral tests (with the brand assert changed to MYEZ), `test_consent_capture_w3_16.py` B12, the AI consent fence, `landing.brand.s69` (address counts), `test_security_regression.py` legal-route entries if any.
Mutants (each must redden its test): re-insert a DRAFT line (T1); leave one placeholder (T2); "Qaren" in a body paragraph (T3); drop one AR heading (T4); hand-edit one landing paragraph (T5); change one anchor date (T6); remove "Bright Data" from the policy (T7); add a `FOO_API_URL = "https://api.example.net"` module (T7b); add "opt out" to section 4 (T8); `lang=ar` ignored (T9, T10).

### 4.11 Gates

Backend: py_compile + ruff `E9,F63,F7,F82` on changed `.py`; `pyt.py` unit files (600 s): `tests/test_legal_docs_u8.py tests/test_legal_routes.py tests/test_consent_capture_w3_16.py`; comm gate = module-reference set for `legal_routes|consent_service` plus `grep -rl SmartCompareApp tests/` (backend tests that read client catalogs) at BASE and HEAD, `comm -13` empty. Client (only `sc-s70-u4b` has real node_modules; the orchestrator assigns): jest subset `LegalScreen|legal|consent|landing.brand`, then the FULL suite (rebased client unit rule), tsc, eslint on changed files. Landing: the curl list of `landing/README.md` section 4 after redeploy (owner). Copy: native Arabic review sign-off recorded in the PR body. Mutation matrix as 4.10.

---

## 5. What the owner must do so the text is TRUE on publication day (not inputs; actions)

1. Apply 043 (PRECHECK grid back first). 2. Turn OpenAI organisation data sharing OFF (D3 = A) and read the Chat Completions storage default in the dashboard. 3. Confirm the three mailboxes receive mail (send one test each). 4. Read the Supabase, Railway and Upstash regions. 5. Redeploy the landing in the same window as the U8 merge. 6. (Controller duty, not text) Bahrain PDPA notification or a data protection guardian, if counsel says it applies (RESEARCH_DIGEST pitfall, Art 14).

---

## 6. Stated limits

- Nothing here was run against production; flag states come from CLAUDE.md, not from Railway.
- The truth table covers code paths found by grep over `app/`, `scripts/cron_*.py` and `SmartCompareApp/src`; dynamic hosts in `data/*.json` registries are summarised as P15, not enumerated.
- Legal-basis, transfer-basis, breach-timing, minors and governing-law words are placeholders or defaults for counsel; this spec chooses none of them as advice.
- The 043 deletion text is only as true as the PRECHECK says (branch A/B, section 9 f).

## 7. Assumptions (with reasons)

- A1. D3 = A is the drafting default (variant B kept as data): lowest review risk per RESEARCH_DIGEST U3b pitfalls; the owner has not ruled.
- A2. The in-app AR policy is in U8's scope (M16; IMPLEMENTATION_PLAN U8 files list LegalScreen "language parameter"): an Arabic-first market reading an English-only policy fails 5.1.1(i) "easily accessible" in spirit; cost is two files and a query parameter.
- A3. Privacy and terms share one date and one TERMS_VERSION: the code already ties terms `last_updated` to TERMS_VERSION (B12); two dates would need a second constant for no benefit.
- A4. The YouTube clause is decided by a names-only flag read, not by the owner: it is a code-state fact, and asking the owner a technical question he cannot answer from memory wastes his ten minutes.
- A5. `legal@qaren.app` is dropped (one privacy address + one support address): fewer unverified mailboxes; the owner can keep it via form item 5.

## 8. Open questions for the orchestrator

- Q1. Accept generation of the landing legal body (4.9) or hand-edit + normalised parity test? Recommend generation.
- Q2. Who owns C31 (onboarding "never share" line) and C32 (toggle copy): U3b or U8? Recommend U3b (it already edits those catalog regions; U8 keeps the AI-consent keys untouched).
- Q3. Merge policy for T2: build GREEN with placeholders on the branch and fill in later, or wait for inputs before RED? Recommend: RED + GREEN now on placeholders (T2 the only red), fill-in commit after the form returns.
- Q4. C34 (SearchHistory purposes omit Analytics) and C35 (IP "not collected") are inventory/app.json issues with native-build reach: file as a pre-build follow-up (owner/counsel decide)?
- Q5. Bundled fallback for the in-app policy when the backend is down (RESEARCH_DIGEST pitfall): add a landing-URL link on the error state of LegalScreen, or bundle the markdown in the binary (then every legal edit needs a build)? Recommend the landing link.
- Q6. Existing users accepted TERMS_VERSION 2026-03-26 (the DRAFT). There is no re-acceptance or "policy updated" notice mechanism in code; old builds will record the old version while seeing the new server-served text. Is a one-time in-app notice in scope for U8, a separate unit, or not needed (counsel)? Recommend a separate small client unit after counsel's answer.
- Q7. The 10/15 working-day promise is an operational commitment with no ticketing behind it; record the inbox owner in the runbook?
- Q8. `pain_workflow_events` has no writer (F-E) and `users.governorate` does not exist yet `cron_reengagement` reads it: the cohort-curiosity push line ("people near you") cannot work today - irrelevant to the policy text but worth a tracked issue (likely already filed by the orchestrator per U8B UR2).

## 9. NOT VERIFIED

- Hosting regions of Supabase, Railway, Upstash, Serper, Bright Data, Firecrawl, Scrape.do, Expo (dashboards / vendor pages not read).
- OpenAI org settings: data sharing enrolment, usage tier, storage default for this org; the OpenAI contracting entity named in the owner's account terms.
- That `request.client.host` on Railway is always the edge address and never the user's IP; Railway platform log retention and whether it records client IPs.
- Sentry plan retention; backend DSN region (derived as EU only because region is per organisation and both projects share org `qaren-rr`).
- Supabase backup / PITR window; Supabase Auth email sender; whether GoTrue keeps the Apple/Google name claim.
- Prod state of ENABLE_YOUTUBE_SOURCE, ENABLE_REENGAGEMENT_PUSHES, ENABLE_BONUS_EXPIRY_PUSHES, ENABLE_FEWSHOT_ROTATION; which of Serper / Bright Data serves live searches.
- Cloudflare Email Routing for the qaren.app addresses (LL-13).
- Bahrain Order 42/2022 adequacy list and the article numbers for the 10-working-day deadlines (taken from RESEARCH_DIGEST, not re-fetched); KSA SDAIA complaint window (digest: 90 days).
- Apple 5.1.1(i), 5.1.1(v), 5.1.2(i), 2.2 wording WAS verified: https://developer.apple.com/app-store/review/guidelines/ (2026-10-05). OpenAI training default, 30-day abuse logs and moderations no-retention WERE verified: https://developers.openai.com/api/docs/guides/your-data (2026-10-05). Bahrain Art 18 15 working days WAS confirmed via the official PDF's search summary: https://www.pdp.gov.bh/en/assets/pdf/regulations.pdf (2026-10-05). Sentry EU = Frankfurt WAS verified: https://docs.sentry.io/organization/data-storage-location/ (2026-10-05).

# Agent A — Backend Forensics Report

**Model:** Opus | **Returned:** 2026-05-06
**Scope:** SmartCompare/Qaren backend (FastAPI on Railway)

---

# SECTION 1: API endpoints inventory

All routers are registered in `app/main.py:119-130`. Middleware order (outer→inner): RequestID → SecurityHeaders → ErrorHandler → CORS (`app/main.py:88-116`). Default rate limits set globally: `100/day, 10/minute` per remote IP (`app/middleware/rate_limiter.py:13,29`).

## 1.1 Auth router — `/api/v1/auth/*` (`app/api/auth_routes.py:45`)

- **POST `/api/v1/auth/register`** (`auth_routes.py:281-318`) — auth: none. Rate limit: `3/minute` (`:282`). Body: `RegisterRequest{email: EmailStr, password: 10+ chars 1U/1L/1D, invite_id?: str ≤64}` (`:65-77`). Returns `AuthResponse{success, user{id,email,preferences_completed,display_name,auth_provider}, session{access_token,refresh_token,expires_at}, message}` (`:215-220`, `:99-112`).
- **POST `/api/v1/auth/login`** (`auth_routes.py:321-370`) — auth: none. Rate limit: `5/minute` (`:322`). Body: `LoginRequest{email, password}` (`:79-81`). Returns same `AuthResponse`. Brute-force lockout via `check_account_locked` (`:330`) — 5 fails / 15 min (`auth_service.py:14-15`).
- **POST `/api/v1/auth/refresh`** (`auth_routes.py:373-387`) — auth: none. Rate limit: `10/minute`. Body: `RefreshRequest{refresh_token}` (`:84-85`).
- **POST `/api/v1/auth/logout`** (`auth_routes.py:390-402`) — auth: required. Revokes the bearer token in Redis blacklist with 1-hour TTL (`auth_service.py:265-273`).
- **GET `/api/v1/auth/me`** (`auth_routes.py:405-439`) — auth: required.
- **POST `/api/v1/auth/password-reset`** (`auth_routes.py:442-454`) — auth: none. Rate limit: `3/minute`. Always returns success to prevent enumeration.
- **GET `/api/v1/auth/verify`** — auth: required.
- **PUT `/api/v1/auth/profile`** — auth: required. Body: `{display_name: 2-100 chars}`.
- **PUT `/api/v1/auth/email`** — auth: required. Requires current password.
- **PUT `/api/v1/auth/password`** — auth: required.
- **POST `/api/v1/auth/social-login`** — auth: none. Rate limit: `10/minute`. Body: `{provider: "google"|"apple", id_token, nonce?}`.
- **DELETE `/api/v1/auth/account`** — auth: required. Rate limit: `1/minute`. Calls `delete_user_account` → `delete_user_cascade` RPC.
- **POST `/api/v1/auth/resend-verification`** — auth: none. Rate limit: `3/minute`. Always success to avoid enumeration.
- **GET `/api/v1/auth/preferences`** — auth: required.
- **PUT `/api/v1/auth/preferences`** — auth: required. Body: `UserPreferencesRequest{priorities: 1-3 of 14 enums, budget: budget|mid|premium, lifestyle: 0+ of 11 tags, brand_attitude: 1 of 4, ai_sharing_enabled?, notifications_enabled?, notification_types?}`.
- **PUT `/api/v1/auth/push-token`** — auth: required. Rate limit: `10/minute`. Body: `{expo_push_token: 1-256 chars}`.
- **PUT `/api/v1/auth/demographics`** — auth: required. Rate limit: `5/minute`. Auto-derives language from `Accept-Language`, country from `CF-IPCountry` headers.
- **GET `/api/v1/auth/cohort-profile`** — auth: required.

## 1.2 Text router — `/api/v1/text/*`

- **POST/GET `/api/v1/text/compare`** — auth: optional. Rate limit: `10/minute`. Body: `TextCompareRequest{query, region, include_specs, include_reviews, include_pros_cons}`.
- **GET `/api/v1/text/compare/stream`** — auth: optional. Rate limit: `10/minute`. SSE stream.
- **POST `/api/v1/text/quick`** — auth: none. Rate limit: `10/minute`.
- **GET `/api/v1/text/prices/{product}`** — auth: none. Rate limit: `20/minute`.
- **DELETE `/api/v1/text/cache`** — auth: admin (`Depends(verify_admin_key)`).
- **GET `/api/v1/text/parse`** — auth: admin.

## 1.3 Image router — `/api/v1/image/*`

- **POST `/api/v1/image/identify`** — auth: optional. Rate limit: `10/minute`. Body: 1-4 image files (10MB each max), MIME validated to JPEG/PNG/WebP/GIF only. HEIC explicitly rejected. Images held in memory only.

## 1.4 URL router — `/api/v1/url/*`

All endpoints SSRF-validate via `validate_external_url` (`url_validator.py:10-49`).

- **GET `/api/v1/url/retailers`** — auth: none. No rate limit.
- **POST/GET `/api/v1/url/extract`** — auth: none. Rate limit: `10/minute`.
- **POST/GET `/api/v1/url/compare`** — auth: none. Rate limit: `10/minute`.
- **POST/GET `/api/v1/url/detect`** — auth: none. Rate limit: `20/minute`.

## 1.5 History router — `/api/v1/comparisons/*`

All endpoints require auth.
- **GET `/api/v1/comparisons/history`** — Rate limit: `30/minute`.
- **GET `/api/v1/comparisons/{comparison_id}`** — Rate limit: `20/minute`. Uses `hmac.compare_digest` for ownership check.
- **DELETE `/api/v1/comparisons/{comparison_id}`** — Rate limit: `20/minute`.

## 1.6 Share router — `/api/v1/share/*`

- **POST `/api/v1/share/{comparison_id}`** — auth: required. Rate limit: `10/minute`. Token: `secrets.token_urlsafe(16)` ~22 chars.
- **GET `/api/v1/share/{token}`** — auth: none. Rate limit: `30/minute`. Strips `personalized`, `personalization_factors`, `personalization_prompt`.

## 1.7 Feedback router — `/api/v1/{feedback,events}`

- **POST `/api/v1/feedback`** — auth: optional. Rate limit: `30/minute`. Body: `{useful: bool, comparison_id?, mattered_most: subset of [price,specs,reviews,brand,value,warranty,ratings], change_suggestion ≤1000 chars}`.
- **POST `/api/v1/events`** — auth: optional. Rate limit: `60/minute`. Body: `{events: max 50 items}` each `{event_type ∈ [save,share,source_click,tab_switch,feedback_submit,result_view_duration], event_data ≤10KB, comparison_id?}`.

## 1.8 Admin router — `/api/v1/admin/*`

All endpoints require `X-Admin-Key` header verified via `hmac.compare_digest`. All rate limited `30/minute`.
- Stats, costs, audit-log, cohort metrics, referrals metrics, etc.

## 1.9 Other routers

- **Legal** — `/api/v1/legal/{privacy,terms}` — auth: none, no rate limit. Reads markdown.
- **Version** — `GET /api/v1/app/version` — auth: none.
- **Usage** — `GET /api/v1/usage/status` — auth: required.
- **Referrals** — `/api/v1/referrals/*` — gated by env `ENABLE_REFERRAL_SYSTEM` (default OFF).
- **Health/root** — `GET /` and `GET /health` — auth: none.
- **Static admin assets** — `/admin/*` mounted from `app/static/admin/`.

---

# SECTION 2: External API calls — what data leaves the backend

## 2.1 OpenAI

Two clients: module-level singleton in `openai_service.py:15` and lazy in `extraction_service.py:22-29`. A second project-aware factory `get_client(use_shared_project: bool)` exists for the PDPL opt-out path; `select_client_for_user` reads `user_prefs.ai_sharing_enabled` and routes to `OPENAI_API_KEY_PRIVATE` when the user opted out.

**Vision call — `identify_products`:** Model `gpt-4o-mini`. Sends image bytes base64-encoded as data URLs plus a system prompt instructing GPT to OCR brand/name/size/visible_price/confidence. **No `user_id`, email, or auth token in the OpenAI payload.** No caching — every camera upload makes a fresh call.

**Text extraction calls** (`gpt-4o-mini`):
- `parse_product_query` — sanitized query truncated to 500 chars, wrapped in `<USER_INPUT>...</USER_INPUT>`.
- `extract_specs` — sanitized brand/name/variant + Serper search context truncated to 3000 chars. Optional `drug_context` is deterministic data from `bahrain_approved_drugs`.
- `extract_price` — brand/name/variant/region + 2000 chars of search context.
- `extract_price_from_training_data` — brand/name/variant/region only.
- `extract_reviews` — brand/name/variant/category + 4000 chars of search context.
- `generate_comparison` — verdict generator. Routes via `model_router_service` to `gpt-4o` if priority="high" and daily cap < 80%, else `gpt-4o-mini`. Retries once with mini on 429.

**OpenAI prompt-construction trace — what goes into messages:**

For `generate_comparison` (the verdict, biggest payload):
- system message starts with `COMPARISON_SYSTEM` (`extraction_service.py:353-394`).
- Appended: `build_personality_prompt(category)` — category-specific tone instructions, no user data.
- Optionally `scores_summary` — deterministic numeric scores from `scoring_service`, no user data.
- Optionally `_build_preferences_prompt(user_preferences, demographics_profile=...)`:
  - Renders: `priorities` (joined list), `budget`, `lifestyle` (joined list), `brand_attitude`.
  - Then calls `_build_cohort_priors_block(demographics_profile)` (`extraction_service.py:749-832`).
- `_build_cohort_priors_block`:
  - Gated by `_is_cohort_personalization_enabled()` env flag.
  - **Renders ONLY:** `country`, `language`, `governorate`, the cohort `n` count, and aggregate modal fields (`top_deciding_factor`, `second_deciding_factor`, `spend_bracket`, `preferred_assistance_style`, `top_difficulties`, `trust_sources`).
  - **Does NOT render:** `age_group`, `gender`, raw `cohort_match`, persona label, user_id, email — verified by re-reading the f-string on `:817-832`.
- The user message wraps the two product objects (`product1`, `product2` JSON dumps) and `region` + `concern` in `<USER_INPUT>...</USER_INPUT>`. Product objects come from spec/price/review pipelines and contain product brand/name/variant/specs/price/retailer/reviews — NOT the end user's identity.

**✅ CONFIRMED:** the privacy invariant in `CLAUDE.md` ("no raw demographics in prompts — only country/language/governorate thin context line + aggregate findings") matches the code. No `age_group`, no `gender`, no `email`, no `user_id` is interpolated into any GPT message. Sanitizer (`prompt_sanitizer.py:6-24`) strips control chars and prompt delimiters.

**OpenAI usage caching:**
- Specs: Redis L1 7d, DB L2 30d (`product_data_service.py:17`).
- Prices: Redis L1 24h, DB L2 24h (`product_data_service.py:18`).
- Reviews: Redis L1 7d, DB L2 14d (`product_data_service.py:19`).
- `nocache=true` query param bypasses both layers.

## 2.2 Serper (Google Search/Shopping)

Endpoint base `https://google.serper.dev`. API key in `X-API-KEY` header. 15s timeout.
- `search_web` — POST `/search` with `{q, num, gl, hl}`. **Sends only the search query string and country code; nothing user-identifying.**
- `search_product_prices`, `search_price_organic`, `search_videos`, `search_images`, `search_news`.
- Caching: results passed into specs/reviews caches via the unified search pre-fetch.
- Budget tracking via `api_budget_service` Redis counter.

## 2.3 Supabase

Two clients: `get_user_supabase_client(access_token)` (anon key + JWT, RLS enforced) and `get_admin_supabase_client()` (service-role key, bypasses RLS). Auth client separate.

Auth operations: `sign_up`, `sign_in_with_password`, `refresh_session`, `get_user`, `sign_out`, `sign_in_with_id_token`, `admin.update_user_by_id`, `admin.delete_user`, `reset_password_email`, `resend`.

**No caching** — every auth call hits Supabase. User-identifiable data sent: email, password, JWTs, user_id, all preferences, demographics, comparison full_response, search queries, push tokens, behavioral profile.

## 2.4 Upstash Redis

Initialized in `cache_service.py:14-46`. Uses `upstash-redis` REST client when URL starts with `https://`.

Data sent (with TTLs):
- Specs/prices/reviews JSON cached by hashed `product_key` (no user data) — TTLs above.
- `revoked:{sha256(token)}` blacklist — 1 hour TTL.
- `failed_login:{sha256(email)[:16]}` brute-force counter — 15 minutes.
- `usage:daily:{user_id}:{YYYY-MM-DD}`, `usage:monthly:{user_id}:{YYYY-MM}` — 24h / 32d.
- `cost:{YYYY-MM}` monthly API spend — 32d.
- `usage:{user_id}:{date}` legacy daily counter — 24h.
- `exchange_rates:{YYYY-MM-DD}` — 24h.
- `budget:{provider}:lifetime` / `budget:{provider}:{YYYY-MM}` — Firecrawl/Scrape.do/Serper counters.
- `circuit:{provider}` — circuit-breaker state, 1h TTL.
- `openai:4o:tokens:{YYYY-MM-DD}` — 36h TTL.

User-identifiable data in Redis: `user_id` is plaintext in usage keys; tokens and emails are SHA-256 hashed before inclusion in keys.

## 2.5 Sentry

Initialized in `sentry_service.py:73-102`. No-op when `SENTRY_DSN` env var unset. `traces_sample_rate=0.1`, `send_default_pii=False`.

**`before_send` scrubber trace (`sentry_service.py:40-61`):**

Scrubs exception `value` strings using `_scrub_string` — applies regex patterns from `_SENSITIVE_PATTERNS`:
- JWTs (`eyJ...eyJ...`) → `[JWT_REDACTED]`
- OpenAI keys (`sk-proj-...`) → `[OPENAI_KEY_REDACTED]`
- Firecrawl keys (`fc-...`) → `[FIRECRAWL_KEY_REDACTED]`
- 40+ char hex strings → `[TOKEN_REDACTED]`
- `Bearer ...` headers → `Bearer [REDACTED]`

Scrubs breadcrumb `data` (recursively) and `message` strings. Scrubs request headers — only `Authorization`, `X-Admin-Key`, and `Cookie` are replaced wholesale with `[REDACTED]`. Other request headers (User-Agent, Accept-Language, CF-IPCountry, X-Forwarded-For, etc.) **pass through to Sentry**.

`_strip_tokens_from_breadcrumb` only scrubs the `url` field of breadcrumb data. Does NOT recurse, does NOT scrub `query`, `body`, or `params`.

**⚠️ Pass-through fields (NOT scrubbed):** request URL paths, **query strings (e.g. `/api/v1/text/compare?q=...`)**, email values that don't match a token pattern, `request_id`, response status codes, `user_id` in log message bodies that aren't tokens.

`ErrorHandlerMiddleware.dispatch` calls `sentry_sdk.capture_exception(exc)` on any unhandled exception.

## 2.6 Firecrawl

Endpoint `https://api.firecrawl.dev/v1/scrape`. Auth: Bearer token. Sends: `{url, formats: ["html"], waitFor: 5000}`. Returns rendered HTML. Used only for retailer/brand product URLs — no user data.

## 2.7 Scrape.do

Endpoint `https://api.scrape.do`. Sends: `?token={SCRAPEDO_API_TOKEN}&url={url}&render=true`. Same as Firecrawl — only product URLs.

## 2.8 Frankfurter (exchange rates)

GET `https://api.frankfurter.app/latest?from=USD`. No headers, no auth, no user data. 5s timeout. Cached in Redis 24h.

## 2.9 Expo Push

Endpoint `https://exp.host/--/api/v2/push/send`. POST JSON body `{to: token, title, body, sound, data}`. The Expo push token (read from `users.expo_push_token`) is sent. Loop 2 push includes invitee display name in body text.

## 2.10 Apple/Google identity (via Supabase)

Backend forwards `id_token` to Supabase, which forwards to the IdP. Backend never directly contacts Google/Apple.

---

# SECTION 3: Data the backend stores

(See full table inventory in agent-c-report.md — Agent A's findings concur with Agent C's schema analysis.)

**Cascade-delete coverage** (key points):

`delete_user_cascade` PL/pgSQL function (`migrations/010_enable_rls.sql:70-84`):
```sql
DELETE FROM user_events WHERE user_id = target_user_id;
DELETE FROM comparison_feedback WHERE user_id = target_user_id;
DELETE FROM comparisons WHERE user_id = target_user_id;
DELETE FROM search_logs WHERE user_id = target_user_id;
UPDATE users SET preferences = NULL, behavior_profile = NULL,
  preferences_completed = false WHERE id = target_user_id;
```

Then `auth_service.py:432` calls `admin.auth.admin.delete_user(user_id)` which deletes the auth row, and FK `ON DELETE CASCADE` on `users.id` cascades to referral tables and product cache tables. So the auth-user delete eventually cascades the rest via FK constraints.

**Not deleted:**
- `admin_audit_log` — audit records with `user_id` matching the deleted user are NOT removed (no FK CASCADE, no explicit delete in cascade function).
- `products`, `bahrain_approved_drugs`, `product_specs`, `product_prices`, `product_reviews` — no user FK (deduped product taxonomy and cache).

---

# SECTION 4: Authentication, sessions, and security posture

## 4.1 Token storage
Backend does not persist user tokens server-side except as a **revocation blacklist** in Redis: `revoked:{sha256(token)}` with 1-hour TTL.

## 4.2 JWT verification flow
`get_current_user` extracts `Bearer <token>` and calls `verify_token`:
1. Check Redis blacklist.
2. Call Supabase `auth.get_user(token)` — validates JWT signature and expiry.
3. Returns `{id, email}` or None.

## 4.3 Session token TTL
The Supabase `expires_at` is forwarded to client. Backend does not set this — controlled by Supabase project config. Cannot determine the exact TTL from code.

## 4.4 Rate-limiter rules — every `@limiter.limit`

Auth endpoints: register=3/min, login=5/min, refresh=10/min, password-reset=3/min, social-login=10/min, delete account=1/min, resend-verification=3/min, push-token=10/min, demographics=5/min.

Text: compare 10/min, quick 10/min, prices 20/min.
Image: identify 10/min.
URL: extract/compare 10/min, detect 20/min.
History: list 30/min, get/delete 20/min.
Share: create 10/min, view 30/min.
Feedback: 30/min, events: 60/min.
Admin: 30/min on ALL endpoints.
Referral share: 10/min.
Global default: 100/day, 10/min per IP.

## 4.5 Account deletion

Path: DELETE `/api/v1/auth/account` → `delete_user_account` → `delete_user_data_cascade` → RPC `delete_user_cascade` → then `admin.auth.admin.delete_user(user_id)`.

`delete_user_cascade` hard-deletes from `user_events`, `comparison_feedback`, `comparisons`, `search_logs`. Nullifies `preferences`, `behavior_profile`, sets `preferences_completed=false` on `users`. Then auth-user delete cascades the rest via FK constraints.

**`admin_audit_log` is not deleted** — login_failed, login_success, brute_force_lockout, referral_* events with `user_id` persist after account deletion.

## 4.6 Brute-force lockout
Threshold 5 failures, window 900 seconds = 15 minutes. Email is SHA-256 hashed before being used as Redis key. Fails open if Redis unavailable.

## 4.7 HTTPS enforcement
HSTS header set globally: `Strict-Transport-Security: max-age=31536000; includeSubDomains`. Backend relies on Railway TLS termination — no code-level HTTPS redirect.

## 4.8 CSP rules (verbatim from `security.py:24-36`)

For paths matching `/admin/*`:
```
default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'
```

For all other paths:
```
default-src 'none'; frame-ancestors 'none'
```

Other security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-XSS-Protection: 1; mode=block`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`.

## 4.9 Admin authentication
`verify_admin_key` reads `X-Admin-Key` header, compares against `ADMIN_API_KEY` env using `hmac.compare_digest`. 403 on mismatch.

## 4.10 API key storage
All keys read from environment variables only (no hardcoded secrets observed):
`OPENAI_API_KEY`, `OPENAI_API_KEY_PRIVATE`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`, `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN`, `SENTRY_DSN`, `CORS_ORIGINS`.

## 4.11 Other notable security items
- Swagger docs disabled when `RAILWAY_ENVIRONMENT` env var is set.
- Prompt injection sanitizer applied before every GPT call (`prompt_sanitizer.py:6-49`).
- SSRF protection on URL endpoints — resolves DNS, blocks private/loopback/link-local/reserved IPs and non-http(s) schemes (`url_validator.py:10-49`).
- LIKE wildcards escaped before search query.
- Share token regex `^[A-Za-z0-9_-]{18,30}$` enforced.
- Email enumeration prevention: `/password-reset` and `/resend-verification` always return success.

---

# SECTION 5: Logging

## 5.1 Logging configuration
- All log records formatted as JSON with `timestamp, level, module, message, request_id?, exception?`.
- Single handler: `StreamHandler(sys.stdout)`. Goes to Railway's stdout collector.
- Default level: `INFO` (overridden by `LOG_LEVEL` env).
- Third-party loggers `httpx, httpcore, uvicorn.access, urllib3` quieted to `WARNING`.

## 5.2 What gets logged that contains identifiers

- `auth_routes.py:425` — `f"Profile lookup failed for {current_user['id']}: {e}"` — INFO. **Contains user_id.**
- `auth_routes.py:532` — `f"Account deletion failed for user {current_user['id']}: {e}"` — ERROR. **Contains user_id.**
- `auth_routes.py:670` — `f"push token update failed for {current_user['id']}: {exc}"` — WARNING. **Contains user_id.**
- `text_routes.py:73` — `logger.info(f"Text comparison request: {body.query}")` — INFO. **Contains raw user query string.** Same in `text_routes.py:178, 270, 305`.
- `text_routes.py:86, 178, 270` — `[PREFS] Authenticated user {user.get('id', 'unknown')} has no preferences. prefs_result: {prefs_result}` — WARNING. **Contains user_id and preferences blob.**
- `image_routes.py:73, 103, 134, 161` — image upload events log shapes/byte counts and product names; no user_id directly.
- `url_routes.py:89, 146` — `f"URL extraction request: {body.url}"` — INFO. **Contains the user-supplied URL.**
- `auth_service.py:67, 407, 421` — log `user_id` on lookup/save errors.
- `database_service.py:124, 514, 529` — log `user_id` in cascade-delete and demographics save errors.
- `push_service.py:51, 85, 112, 132, 150` — log `user_id` (and referrer_user_id) on push delivery errors.
- `usage_service.py:205` — log `user_id` on usage-record errors.

**Email-containing logs:** No log line directly containing the email after sanitisation found. Auth errors are categorised in `_categorize_auth_error` before being logged.

## 5.3 What gets logged at each level (sample)

- INFO: incoming compare requests with the raw query (`text_routes.py:73`), Firecrawl/Scrape.do success messages with URL, Redis/Sentry init status, model_router transitions.
- WARNING: failed lookups, fallback triggers, link_invite_to_user failures, push delivery errors, exception backstops with user_id context.
- ERROR: auth errors with full context, share token write failures, unhandled exceptions in `ErrorHandlerMiddleware.dispatch`.
- DEBUG: cache misses, push token absence.

## 5.4 IP addresses in logs

- `audit_service.py:33` — writes `ip_address` to `admin_audit_log` table (not stdout). Caller passes `request.client.host`.
- The middleware logging itself does not log client IPs.
- The `uvicorn.access` log is set to WARNING, so per-request access logs are suppressed.

## 5.5 Prompts/outputs in logs

- `extraction_service.py:27` — `Initializing OpenAI client with key ending in: ...{api_key[-10:]}` — INFO. Logs the last 10 chars of the OpenAI key.
- `extraction_service.py:420` — `f"Injection pattern detected in query: {query[:100]}"` — WARNING. Logs first 100 chars of suspicious query.
- `image_routes.py:114-115` — vision raw response logged at DEBUG only.
- **No code path logs full GPT prompts or full GPT responses at INFO/WARNING/ERROR.**

---

# SECTION 6: Existing legal docs vs. code (Backend perspective — Agent A findings)

## 6.1 Privacy Policy claims

| Claim | Status |
|-------|--------|
| Email address, display name, password collected | ✅ Confirmed |
| Preferences (priorities, budget, lifestyle, brand attitude) | ⚠️ **Stale** — missing `ai_sharing_enabled`, `notifications_enabled`, `notification_types` |
| Feedback (thumbs up/down, suggestions) | ✅ Confirmed |
| Usage data (event interactions) | ✅ Confirmed |
| Device data (type, OS, app version) | ⚠️ Cannot determine from code — no backend table column or log line for OS/device-type |
| Camera data not stored on servers | ✅ Confirmed (held in memory only) |
| Social login: receive email + basic profile, do NOT receive passwords | ✅ Confirmed |
| Service providers list (Railway, Supabase, OpenAI, Serper, Upstash, Sentry) | ⚠️ **Stale** — missing **Firecrawl**, **Scrape.do**, **frankfurter.app**, **Expo Push** |
| Account data deleted upon deletion request | ⚠️ **Stale** — `admin_audit_log` keeps `user_id` |
| Cache: prices 24h, specs/reviews 7d | ⚠️ **Stale** — omits L2 DB cache (specs 30d, reviews 14d) |
| User export right "by contacting us" | ❌ **No export endpoint exists in code** |
| Notification of material changes via email | ❌ **No marketing-email path found in backend** |
| AI Quality Improvement Program — what is/isn't shared | ✅ **Verified by code line-by-line** |
| Opt-out path "Settings → Privacy → 'Help improve AI quality'" | ✅ Backend supports `ai_sharing_enabled`; frontend UI presence cannot be confirmed from backend code |
| Contact `privacy@smartcompare.app` | ⚠️ Brand mismatch (app is "Qaren") |

## 6.2 Terms of Service claims

| Claim | Status |
|-------|--------|
| Categories: electronics, groceries, supplements, cosmetics, fashion, fragrances | ⚠️ **Stale** — code has 9 categories: electronics, grocery, supplements, makeup, skincare, haircare, fragrances, fashion, other |
| 13+ minimum age | ✅ Stated; not technically enforced (relies on user attestation) |
| Automated account creation prevented | ✅ 3/min rate limit on register |
| Acceptable Use bullets | (No specific technical claims to verify) |
| Price marked "estimated" | ✅ Confirmed (Tier 3 fallback) |
| Account deletion permanently removes all data | ⚠️ **Stale** (admin_audit_log retains user_id) |
| Governing Law: Bahrain | (No code-level evidence either way) |
| 3 shares per week limit | ✅ Confirmed (`_WEEKLY_INVITE_CAP = 3`) |
| 5 (Free) / 10 (Premium) per conversion | ✅ Confirmed |
| Maximum 15 referral comparisons per month | ❌ **NOT enforced in code** — additive (`referral_service.py:707-709`); 3 invites/wk × 4 wk × 5 = 60/month free or 120/month premium possible |
| Fair use / abuse signals | ✅ Confirmed (same-device, disposable email, real-action gate) |
| Credits expire 30 days after grant | ✅ Confirmed (`expires_at DEFAULT now() + interval '30 days'`) |
| 1 re-engagement notification per week | ✅ Confirmed (`_RECENT_PUSH_WINDOW_DAYS = 7`) |
| 3 notification detector types | ✅ Confirmed |
| Disable in Settings → Notifications | ✅ Confirmed (master + per-type sub-toggles) |
| Contact `legal@smartcompare.app` | ⚠️ Brand mismatch |

## 6.3 Summary of staleness flags

| Item | Status |
|------|--------|
| App name "SmartCompare" | ⚠️ Stale (brand is "Qaren" in code) |
| Service-providers list | ⚠️ Stale (missing Firecrawl, Scrape.do, frankfurter.app, Expo Push) |
| Cache TTL "prices 24h, specs/reviews 7d" | ⚠️ Stale (omits L2 DB cache: specs 30d, reviews 14d) |
| "Deleted upon account deletion request" | ⚠️ Stale (admin_audit_log keeps user_id) |
| Preference fields | ⚠️ Stale (missing AI-sharing/notification toggles) |
| Categories | ⚠️ Stale (9 categories in code, splits cosmetics into makeup/skincare/haircare; lists "other") |
| Export right ("Request a copy of your data by contacting us") | ❌ No export endpoint found |
| "Maximum 15 referral comparisons per month" | ❌ Not enforced in code |
| Communicate service updates with consent | ❌ No marketing-email path found |
| AI Sharing data scope | ✅ Matches code exactly |
| Referral mechanics (3/wk, +5/+10, 30-day expiry, abuse signals) | ✅ Matches code |
| Notification limits (1/wk, 3 detector types, sub-toggles) | ✅ Matches code |

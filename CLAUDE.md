# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SmartCompare (app brand: **Qaren / قارن**) — Intelligent product comparison engine for the GCC market (Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman). Goal: if users still go to Google or ChatGPT after using us, we failed.

## Operating Principles

1. **Quality first, then optimize.** Show confidence, never false certainty.
2. **Don't fetch what you already have, don't call twice when once is enough, don't guess when you can verify.** Every API call costs money.
3. **Plan → Approve → Implement → Test.** Read `docs/CLAUDE_CODE_CONTEXT.md` before major changes.
4. **Multi-file features (3+ files, FE+BE):** use parallel agent teams (TeamCreate with 4 Opus agents: backend, frontend, test, qa).
5. **After major features:** update CLAUDE.md, MEMORY.md, `docs/CONTEXT_SESSION_LOG.md`.
6. **Path-restricted commits in team sessions:** `git commit -m "msg" -- <paths>` — NOT `git commit -- <paths> -m "msg"` (the `--` is a path separator; anything after it is treated as a path and `-m` errors).
7. **Push before deleting branches.** `git push` before `git branch -d`. Local-only commits become orphaned (recoverable via `git cherry-pick <hash>` from reflog within ~30 days, but invisible to teammates and at risk of garbage collection).
8. **Multi-agent silent stalls: escalate after 30 min.** 4-Opus teams (TeamCreate) work well for Phase 0–1 but tend to stop processing inbox messages mid-task while remaining in "available" idle state. If a team agent goes silent past 30 min with uncommitted state on disk despite explicit `SendMessage` nudges, escalate to dispatcher takeover immediately — agents do not self-rescue. Pattern surfaced in Session 47 (Bundle E); dispatcher absorbed Tasks 2.2-2.5, 3.1-3.8, and 4.4 directly.

## Critical: Two app/ Directories

- **`app/`** (root) — The DEPLOYED backend. Railway runs `uvicorn app.main:app` from root.
- **`backend/app/`** — Older/alternate version. NOT deployed. Do NOT edit.
- Always edit files in root `app/` for changes to take effect.

## Commands

### Backend
```bash
# Run locally
uvicorn app.main:app --reload --port 8000

# Syntax check a file
python -m py_compile app/services/structured_comparison_service.py

# Test endpoint (production)
curl https://web-production-58776.up.railway.app/health
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"

# Deploy: push to main, Railway auto-deploys in ~90s
git push origin main
```

### Frontend (React Native / Expo)
```bash
cd SmartCompareApp
npx expo start                    # Dev server (use --clear after dep changes)
npx tsc --noEmit                  # TypeScript check (ground truth — see below)
npx expo install --check          # Verify deps match SDK version
npx expo-doctor                   # Full project health check
eas update --branch <channel>     # OTA push of JS bundle to existing builds
eas build --profile <profile>     # Fresh native build for testers / App Store
```
IDE/LSP TS diagnostics on Windows are unreliable (`typescript-lsp` plugin bug, see MEMORY.md). Trust ONLY `npx tsc --noEmit` exit code — ignore stale "Cannot find module" / "JSX flag not set" errors from system-reminders unless `tsc` actually fails.

**Two-lever launch model:** Backend deploys (Railway via `git push origin main`, ~90s) and mobile JS bundle deploys (EAS via `eas update`/`eas build`) are **independent**. Merging to main does NOT push frontend code to phones — phones run their last-bundled JS until an EAS update/build reaches them. New mobile features need BOTH levers fired.

### Dependencies
- Backend: `pip install -r requirements.txt` (Railway uses this, NOT pyproject.toml)
- Frontend: `npm install` in `SmartCompareApp/`
- **Expo native deps:** use `npx expo install <pkg>` (not `npm install`). JS/native version mismatch causes cryptic `NativeWorklets` / `HostFunction` crashes in Expo Go.

### Migrations
Supabase DDL (`migrations/*.sql`): preferred path is **Supabase MCP** (`mcp__plugin_supabase_supabase__apply_migration`) — tracks migration history table. Fallback: [SQL Editor](https://supabase.com/dashboard/project/qulajmyxdbdkchvecmvc/sql/new). **Gotcha:** SQL Editor wraps multi-statement scripts in one transaction, so a failing view rolls back the ALTER TABLE before it — always verify schema after apply (`information_schema.columns`). Before `CREATE TABLE IF NOT EXISTS`, check existing schema — stale tables with different columns cause silent index/policy failures.

Applied 010–023 (all via MCP since 013). Migration files in `migrations/*.sql` with rollbacks at `migrations/rollback/*.sql`. Highlights: **018** bonus expiry columns + partial idx. **019** `users.attribution_source` + CHECK enum mirror. **020** `comparisons.schema_version` (v1=legacy/hidden, v2=renderable; default 2). **021** `users.device_fingerprint_hash` + partial idx (anti-farming). **022** `referral_invites.source` + relaxed `comparison_id` + CHECK `source∈{share_link,code_redeem}`. **023** (Bundle B/C/D, 2026-05-12 via MCP) drops `weekly_invites_used`; adds `lifetime_invites_consumed INT NOT NULL DEFAULT 0` + partial idx on `device_fingerprint_hash` — referral cap moved to 3 LIFETIME per device. **024** (Bundle C, pending via MCP) adds `'top_tier'` to `users.preferences.budget` CHECK enum; existing rows untouched, backwards-compat with 3-tier values; rollback at `migrations/rollback/024_top_tier_budget.sql`.

## Architecture

### Backend (FastAPI + Python 3.12)

**Entry:** `app/main.py` — env vars, middleware stack, registers 14 routers in `app/api/`:
- `/api/v1/text/*` → `text_routes.py` → `structured_comparison_service.py` (primary flow + SSE, rate limited)
- `/api/v1/image/*` → `image_routes.py` → GPT-4o-mini vision → auto-compare (rate limited, HEIC detection)
- `/api/v1/url/*` → `url_routes.py` (single URL compare, SSRF-protected, 10/min)
- `/api/v1/auth/*` → `auth_routes.py` → Supabase Auth (login, register, refresh, profile, email, password, social, account deletion, demographics, cohort-profile). Rate limited per route.
- `/api/v1/comparisons/*` → `history_routes.py` (auth required)
- `/api/v1/share/*` → `share_routes.py` (POST auth, GET public — strips personalization)
- `/api/v1/feedback`, `/api/v1/events` → `feedback_routes.py` (auth-optional, fire-and-forget). `FeedbackRequest` has 4 fields only — `useful, comparison_id, mattered_most, change_suggestion`. NO `feedback_type`. ContactUsScreen encodes category as `[Bug] Subject\n\nBody` prefix in `change_suggestion`; operators grep `change_suggestion LIKE '[Bug]%'`.
- `/api/v1/referrals/*` → `referral_routes.py` (gated by `ENABLE_REFERRAL_SYSTEM`)
- `/api/v1/admin/*` → `admin_routes.py` (X-Admin-Key, timing-safe `hmac.compare_digest`, 30/min)
- `/api/v1/legal/*` → `legal_routes.py` (no auth, reads markdown files)
- `/api/v1/app/*` → `version_routes.py` (force-update from env vars)
- `/api/v1/usage/*` → `usage_routes.py` (freemium tier enforcement)

**Middleware stack** (outermost → innermost): RequestID → SecurityHeaders (HSTS, CSP, X-Frame-Options) → ErrorHandler → CORS → slowapi rate limiter

**Unified error format:** `{ success: false, error: "msg", code: "ERROR_CODE", request_id: "uuid" }`. Codes: `AUTH_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `RATE_LIMITED`, `VALIDATION_ERROR`, `INTERNAL_ERROR`. Frontend `parseApiError()` handles both `.error` (new) and `.detail` (legacy FastAPI).

**Core service:** `app/services/structured_comparison_service.py` (~1,500 lines — orchestrator only)
- `StructuredComparisonService` — **per-request instances** via `get_comparison_service()` (NOT singleton, for concurrency safety)
- `compare_from_text(query, region, vision_products?, selected_category?, user_id?)` — main entry point
- `compare_from_text_streaming(...)` — async generator yielding SSE events (specs→prices→reviews→scores→verdict→complete)
- **Pre-fetch:** Unified web search (1 Serper call) shared by specs + reviews — gated by cache check
- **Phase 1:** specs + price in parallel (specs reuses unified search)
- **Phase 2:** reviews + rating in parallel (reviews reuses unified search; shopping data from Phase 1 feeds ratings)
- **Scoring:** deterministic via `scoring_service.py` (zero API cost) — value badges, tradeoff pairs, confidence indicators
- **Behavioral profile:** fetched before scoring, updated fire-and-forget after response
- `_shopping_items_cache` populated during price search, cleared per-request
- **Response keys:** `overview`, `specs`, `reviews`, `scoring`, `personalization`, `metadata`. Backward-compat aliases: `products`, `comparison`, `winner_index`, `recommendation`, `key_differences`.

**Decomposed modules** (extracted from monolith):
- `price_service.py` — pricing tiers, currency conversion, page scraping, iHerb, pharmacy JSON-LD
- `rating_service.py` — Tiered rating extraction, Google consensus, retailer classification
- `review_service.py` — Review fetching, content cleaning, citation replacement
- `fact_check_service.py` — Citation verification, cross-validation, confidence computation
- `response_builder.py` — `build_comparison_response()` for sync + streaming paths

**Price pipeline (3 tiers + page scraping + pharmacy JSON-LD):**
1. Serper Shopping API direct extraction (structured prices)
2. GPT-4o-mini extraction from organic search results (with Tier 3 sanity check)
3. GPT training data estimate (marked `estimated: true`)

- **Page scraping:** `_fetch_page_price()` → `_curl_fetch_html()` + `_extract_price_from_html()` extracts JSON-LD/OG/microdata. Used in Tier 1.5 cascade and supplement pipeline. Feature flag: `ENABLE_PAGE_SCRAPE`.
- **Firecrawl Smart Wait** (Tier 1.5a): `firecrawl_service.scrape_page_with_status()` for SPA pages. `source_method: "firecrawl"`. **Timeout 30s** (luxury SPAs need >15s). Validated on LV, Gucci, Bloomingdales.
- **Scrape.do fallback** (Tier 1.5d): residential proxies. Used only when curl_cffi fetched HTML but found no price (`failed_curl_urls`). `source_method: "scrapedo_rendered"`.
- **API budget + circuit breakers** (`api_budget_service.py`): credits (Firecrawl 450/lifetime, Scrape.do 900/mo, Serper 2200/lifetime), 3 failures → 10min cooldown. Fail-open on Redis unavailability.
- **Gate 0 validation:** `_validate_price_query()` rejects garbage queries; `_validate_scrape_url()` rejects search/category pages before burning scrape credits.
- **Price philosophy:** "MOST AUTHORITATIVE" not "LOWEST reasonable". Source priority: official brand > authorized retailers > major marketplaces. Counterfeit sources filtered (DHgate, AliExpress, Temu, Wish). `OFFICIAL_BRAND_DOMAINS` (25+) sorted first.
- Each price tagged `source_method`: `local_bhd`, `converted_usd`, `page_scrape`, `page_scrape_rendered`, `firecrawl`, `scrapedo_rendered`, `estimated`. `price_method_mismatch` flag set when products use different methods.
- **Supplements:** iHerb direct scrape → Bahrain pharmacy JSON-LD → Serper organic + GPT → Tier 3.

**Rating pipeline:** Tier 1 (Serper Shopping, trusted retailers) → Tier 2 (known retailers incl. luxury/fashion) → Tier 3 (eBay if review_count > 1000) → Fallback (GPT, unverified). Consensus: 3+ identical → Google product aggregate. iHerb ratings extracted during price scrape (zero extra calls). All ratings displayed without verified/unverified badges.

**URL sourcing:** Serper Shopping `link` primary, `_build_retailer_url()` fallback. Frontend `openRatingSource()` uses `rating_source.url` first.

**Supplement-specific:**
- Serper Shopping returns ZERO results for supplements — iHerb direct scrape via `curl_cffi` instead.
- Non-iHerb brands (HealthAid, Vitabiotics): `_fetch_pharmacy_price()` → `site:bn.boots.com` search → JSON-LD parsing. Brand matching is space-insensitive.
- bolo.bh NOT indexed by Google (Vue.js SPA); bn.boots.com IS indexed with JSON-LD prices.
- **Bahrain Drug Database**: 655 products in `bahrain_approved_drugs`. `find_matching_drugs()` via full-text search, injected into spec prompt for supplements only.
- **Supabase gotcha:** `text_search()` needs `options={"type": "plain", "config": "english"}` (NOT keyword args); `.limit()` BEFORE `.text_search()` in chain.

**Key services** (in `app/services/`):
- `extraction_service.py` — GPT prompts, `CATEGORY_SPEC_SCHEMAS` (9 categories), structured verdict + review_summary. Injects prompt personality + trust rules.
- `scoring_service.py` — Deterministic scoring ($0). Category-specific 6 dimensions via `CATEGORY_DIMENSIONS`. Personalization caps: ±30% / ±10% / ±5%.
- `prompt_personalities.py` — Per-category comparison "language". `build_personality_prompt(category)`.
- `trust_validation_service.py` — Cross-checks GPT claims against deterministic scores.
- `behavior_service.py` — Decay-weighted profiles (30-day half-life). Category affinity, price range, dimension sensitivity.
- `cache_service.py` — Use `_redis_get/_set/_incr/_expire` helpers for general use. `api_budget_service` uses `redis_client.incrby()` / `incrbyfloat()` directly for atomic operations.
- `api_budget_service.py` — Credit tracking + circuit breakers (Firecrawl, Scrape.do, Serper).
- `exchange_rate_service.py` — Daily rates from frankfurter.app, Redis-cached 24h, hardcoded GCC fallbacks. `get_rate(from_currency, to_currency="BHD")`.
- `firecrawl_service.py` / `scrapedo_service.py` — JS rendering wrappers.
- `database_service.py` — **Dual Supabase client**: `get_user_supabase_client(token)` (anon key + JWT, RLS enforced) vs `get_admin_supabase_client()` (service-role, admin-only). User-facing DB functions accept `access_token`. Old `get_supabase_client()` is deprecated alias for admin.
- `usage_service.py` — Freemium tier. Free: 3 lifetime + 10/month + 3/day. Premium: 70/month + 10/day. Redis counters + Supabase persistence. **Device-bound (Migration 021, Bundle A):** registration accepts `X-Device-Fingerprint` header → SHA-256 stored at `users.device_fingerprint_hash`. Free-tier counters inherit on re-signup from the same device. Prevents log-out + re-signup freebie farming.
- `audit_service.py` — Fire-and-forget security event logging (`admin_audit_log`). Events: login, lockout, usage_limit, injection_attempt.
- `product_data_service.py` — L2 DB cache: specs (30d), prices (24h, append-history), reviews (14d). Redis miss → DB check → API call.
- `cohort_service.py` — Survey-driven cohort matching. Singleton loads `data/cohort_priors.json` once at startup. Hierarchical fallback (exact → broadened_governorate → broadened_language → broadened_age → population). Built by `scripts/build_cohorts.py` from gitignored CSVs in `data/surveys/`; only `data/cohort_priors.json` is committed.
- `model_router_service.py` — Hybrid model routing. `get_model(priority="high")` returns `gpt-4o` below 80% of `DAILY_4O_CAP`, else `gpt-4o-mini`. Atomic `INCRBY` per UTC date. 429 retries to mini once. Fail-open on Redis. Used by verdict generation; specs/prices/reviews stay on mini.
- `referral_service.py` — Smart Decision Referrals. `link_invite_to_user`, `try_trigger_loop2`, code generation.
- `abuse_detection_service.py` — `evaluate_invite()` priority: SAME_DEVICE > DISPOSABLE_EMAIL > BELOW_REAL_ACTION_THRESHOLD (`elapsed_seconds` proxy from `metadata.elapsed_seconds`, `REAL_ACTION_MIN_SECONDS` env, default 5s).
- `push_service.py` — Expo Push (deep-link `qaren://profile/referrals`).
- `reengagement_service.py` — Daily cron `scripts/cron_reengagement.py`. 3 detectors: `decision_insight`, `cohort_curiosity`, `decision_retrospective`. 7-day per-user cap. Gated by `ENABLE_REENGAGEMENT_PUSHES` + `REENGAGEMENT_CANARY_PERCENT` (via `app/utils/feature_bucket.py::hash_bucket()`).
- Other: `serper_service`, `feedback_service`, `drug_database_service`, `openai_service`, `sentry_service`, `analytics_service`, `auth_service`, `url_extraction_service`.

**Security** (`app/utils/`): `url_validator.py` — SSRF: resolves hostnames, blocks private/loopback/link-local IPs, allows only http/https.

**Middleware** (`app/middleware/`): request_id, security headers (HSTS, CSP, X-Frame-Options, nosniff), rate_limiter (slowapi, 10/min on compare), error_handler (Sentry capture + `before_send` JWT/key scrubbing), logging_config (structured JSON).

### Frontend (React Native + Expo)

**Location:** `SmartCompareApp/`. **App name:** Qaren (قارن). Bilingual EN/AR with full RTL support.

**Navigation:** Bottom tabs (Home/History/Profile) via `@react-navigation/bottom-tabs`. Results as modal. Auth stack (Login/Register/ForgotPassword). Splash → Onboarding → Auth → Main flow in `App.tsx`.

**Screens (10):** Splash, Onboarding (6-step wizard), Login, Register, ForgotPassword, Home (camera-first + search overlay + categories), Results (single-scroll + skeleton + winner reveal), History (date-grouped FlatList), Profile (settings/language/account), Paywall (bottom-sheet placeholder).

**Design system:** `src/theme/index.ts` (emerald #10B981, Inter+Cairo). Components: Button, Card, Chip, SkeletonLoader, ProgressBar, IconButton, ComparisonCounter, SearchOverlay. i18n: `src/i18n/` (180+ keys EN/AR).

**Services:**
- `api.ts` — Axios to Railway (120s timeout). SSE via `streamComparison()` (fetch+ReadableStream, fallback to non-streaming). JPEG transcoding before upload.
- `authService.ts` — Supabase auth + social login. **`verifyAuth()` returns `User | null` (NOT boolean).** Tokens in `expo-secure-store` (NOT AsyncStorage). OAuth nonces via `expo-crypto`. All `console.log` wrapped in `__DEV__`.
- `certificatePinning.ts` — SSL pinning for Railway backend (LE intermediate SPKI). Initialized once from `api.ts`. Requires EAS dev build (no-op in Expo Go). SPKI hashes + rotation in `docs/SECURITY_HARDENING_CONTEXT.md`.
- `sentry.ts` — Mobile crash + breadcrumb reporting via `@sentry/react-native@8.11.1`. Mirrors backend `before_send` scrub patterns (JWT/OpenAI/Firecrawl/Bearer/sensitive headers). DSN → `qaren-rr/react-native` project. Sourcemap upload deferred (needs `SENTRY_AUTH_TOKEN` in EAS env + plugin config object form).

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have. ~2,500 credits remaining (rotated 2026-02-28); cached = free, only `nocache=true` burns credits. Rotate via new free account at serper.dev.
- **Supabase** — PostgreSQL + Auth. Tables: users, comparisons, search_logs, product_* (specs/prices/reviews), comparison_feedback, user_events, user_usage, admin_audit_log, referral_invites/redemptions, bahrain_approved_drugs. Full schema in `migrations/010-022`.
- **Upstash Redis** — Response caching (prices 24h, specs/reviews 7d).

## Important Patterns

### Fact-checking (zero-cost cross-validation)
Every product has a `fact_check` object (`overall_confidence`: high/medium/low). Spec citations verified against snippets, review sentiment vs. Serper (0.8 tolerance), price vs. Shopping median (30%). Zero extra API calls. **Ratings are NEVER AI-generated** — GPT prompt explicitly forbids generating `source_ratings`.

### `product.price` is an object, not a number
Backend returns `{ amount, currency, retailer, url, estimated }`. Frontend code must access `product.price.amount`.

### GCC_REGIONS keys (extraction_service.py)
Keys are: `bahrain`, `saudi_arabia`, `uae`, `kuwait`, `qatar`, `oman`. Note: `saudi_arabia` NOT `saudi`.

### Per-request service instances
`get_comparison_service()` returns a **new instance per call** (not singleton). Each request gets fresh `total_cost`, `api_calls`, `_shopping_items_cache`. No manual reset needed.

### Cost budget + caching
Target: **$0.01/comparison**. Achieved via unified search (1 Serper call shared by specs + reviews in `_fetch_product_data()`). Track with `self.total_cost` and `self._track_cost()`. **Two-layer cache:** L1 Redis (specs/reviews 7d, prices 24h) → L2 DB via `product_data_service.py` (specs 30d, prices 24h, reviews 14d) → API call. `?nocache=true` bypasses both. Camera input passes `vision_products` directly, skipping `parse_product_query()`.

### Deterministic scoring + Prompt personalities + Personalization
See skill: `qaren-scoring` (auto-loads when `scoring_service.py`, dimension scores, value badges, personalization caps ±30/10/5%, behavior_service, or `scoring_v2` contract are mentioned). Key recall: 9 categories × 6 dimensions via `CATEGORY_DIMENSIONS`; price tiers budget/mid/premium/luxury; three-layer personalization (explicit ±30% → behavioral ±10% → session ±5%); `scoring_method` enum: `category_weighted` / `personalized` / `behavioral` / `invitee_quiz`. Rollback V1: `docs/ROLLBACK_SCORING_V1.md`.

### Auth + security hardening
- **Dual Supabase client** (see `database_service.py` above).
- **RLS active** on all user-data tables (migration 010). Cascade delete via `delete_user_cascade()` SECURITY DEFINER → `.rpc()`.
- **Token security:** `expo-secure-store` (Keychain/Keystore), revocation on logout via Redis blacklist (`revoked:{sha256(token)}`, 1hr TTL). `verify_token()` checks blacklist before Supabase validation.
- **Account deletion** cascades atomically (App Store requirement, 1/min). **Password:** 10+ chars, 1 upper/lower/digit. **Email change** requires current password.
- **Admin endpoints** rate limited 30/min. **History routes** use `hmac.compare_digest` + merged 404/403. **Swagger** disabled in prod. **SQL LIKE wildcards** escaped. **Sentry `before_send`** scrubs JWT/API keys.
- **CSP scoping** (`app/middleware/security.py`): strict `default-src 'none'` everywhere EXCEPT `/admin/*` static dashboards (which get `'unsafe-inline'` + `cdn.jsdelivr.net` for inline scripts/styles + Chart.js). Admin pages sit behind `X-Admin-Key`.
- **Login response shape:** `POST /api/v1/auth/login` returns `{success, user, session, message, error}` — access token at `session.access_token` (NOT top-level).
- **Regression tests:** `tests/test_security_regression.py` (~98 tests) — DO NOT delete or skip.

### SSE streaming
`GET /api/v1/text/compare/stream` → 10 SSE events with `progress` field (10/20/50/80). Frontend uses fetch+ReadableStream (not EventSource) with fallback to non-streaming.

### Feedback and event tracking
`POST /api/v1/feedback` + `POST /api/v1/events` (batch). Both auth-optional, fire-and-forget. Tables: `comparison_feedback` + `user_events` with RLS.

### Cohort personalization (Phase 1 LIVE)
See skill: `qaren-cohort` (auto-loads when `/api/v1/auth/demographics`, `cohort_priors.json`, `build_cohorts.py`, or `ENABLE_COHORT_PERSONALIZATION` are mentioned). Critical inline: flag is **ON in production**, code default `false`. Privacy invariant — NO raw age/gender/identity in prompt, only country/language/governorate thin context. Cohort match is **exact-case** — values must match `cohort_priors.json` keys exactly (`age_group: "25-34"`, `gender: "Male"/"Female"`, etc.). `VALID_PRIORITIES` extended with 6 cohort enums; `VALID_BRAND_ATTITUDE` adds `trust_known_brands`.

### Category selection (soft validation)
9 categories: Electronics, Grocery, Supplements, Makeup, Skincare, Haircare, Fragrances, Fashion, Other. `selected_category` is a hint — backend AI makes final call via `PRODUCT_PARSER_PROMPT`. Mismatch → `category_switched: true` + frontend info banner. Each category has dedicated spec schema in `CATEGORY_SPEC_SCHEMAS` (`extraction_service.py`).

### Sharing + History
22-char URL-safe token (`token_urlsafe(16)`) in `comparisons.share_token` (TEXT post-migration 017). Public access strips personalization. History: paginated, searchable, ownership-checked. On 401, clears session + redirects to auth. `create_share_token` raises `ShareTokenError` on persistence failure (loud-fail). **schema_version gate (Migration 020):** `save_comparison` only writes when `_validate_renderable(payload)` passes; sets `schema_version=2` + denormalized `product_names`. History list/count/get filter on `schema_version=2` — v1 rows invisible (use `include_legacy=True` for DELETE cleanup only).

### Qaren UX Redesign (merged 2026-05-07 — PR #2 ee91a87)
Cal-AI-Lite 17-step onboarding + black/emerald hybrid identity (emerald = signal color reserved for winner reveal, success ticks, cohort accents — NOT primary CTA). `CANARY_NEW_ONBOARDING_PERCENT` in `SmartCompareApp/src/config/features.ts`; **currently 100 for build/test (commit 462b399)**. Drop to 10 via EAS Update before App Store soft-launch, ramp 10→50→100 (NOT a Railway env var). Plan/spec: `docs/plans/2026-05-06-qaren-ux-redesign{,.design}.md`.
- **Bucketing (`featureBucket.ts` + App.tsx):** djb2 hash on stable id (device-id pre-signup via `expo-secure-store`, user.id post-signup). `hashBucket(id, percent)` is pure — same `(id, percent)` → same boolean every call. Monotonic ramp invariant tested.
- **Theme + motion** live in `SmartCompareApp/src/theme/{index.ts,motion.ts}`. Geist (EN, SIL OFL v1.1) + Cairo (AR). `arabicLineHeightMultiplier = 1.7/1.5`. haptic vocabulary {chip:light, stage:light, winner:medium} — explicitly NO error/warning/heavy intensities (Build Principle #4: never frame the app as scary).
- **17-step onboarding (`src/screens/onboarding/`):** OnboardingFlow orchestrator + 17 steps. Cohort-key types use exact-case strings ('Capital', '25-34', 'Male'/'Female') matching `cohort_priors.json`. Step 14 theatrical loading enforces 3.2s minimum. Step 16 "Save your advisor" has NO skip link — forced sign-in (verified by negative-assertion test).
- **Hero illustrations** (hand-coded SVG + Reanimated, ZERO Lottie): PhoneMockup, CohortBarChart, ConcentricMotif, LoadingRings, RevealBurst. Stage-gated SSE on StreamingProductCard (init→title→specs→prices→reviews→verdict). StageChecklist haptic fires ONLY on transition INTO done state, never on initial mount.
- **Results redesign:** section titles per design § 4g — "Why we picked this" / "Where the runner-up wins" / "What's next?". CohortBadge inline below verdict.
- **Bonus expiry (Migration 018):** 3-day window default. `cron_expire_bonuses.py` gated by `ENABLE_BONUS_EXPIRY_PUSHES`, 1000-row LIMIT, 24h-before push. `usage_service.get_user_active_bonus_count()` filters live rows — entitlement computed from rows, NOT from a stale INT counter (analytics/display only, MUST NOT drive entitlement). **Bundle B/C/D extends this to 7 days for new redemptions; existing rows untouched.**
- **Attribution endpoint (Migration 019):** `POST /api/v1/auth/attribution` (auth, 30/min). Pydantic Literal['friend','instagram','tiktok','app_store','google','other'] + DB CHECK mirror.
- **Min-display floor 1.2s** on HomeScreen→Results per design § 3 (cached responses still show loading 1.2s so brand moment lands). Pattern at `HomeScreen.tsx` lines 206/267/320.
- **Onboarding analytics (`OnboardingFlow.tsx`):** `onboarding_started` on mount, `onboarding_step_completed` BEFORE setStep so payload reflects FINISHED step, `onboarding_completed` on Step 17.
- **Copy contract:** ZERO scary copy in user-facing i18n. Forbidden: `couldn't`, `try again`, `Failed to`, `تعذر`, `فشل`. Approved vocabulary in design doc §6.

### Smart Decision Referrals
See skill: `qaren-referrals` (auto-loads when `/api/v1/referrals/*` routes, invite codes (QR-XXXXXX), Loop 1/Loop 2, redemption chain, or `referral_invites`/`referral_redemptions` tables are mentioned). Critical inline: gated by `ENABLE_REFERRAL_SYSTEM` (default OFF in code, flipped in Railway). Bundle B/C/D moved cap to **3 LIFETIME per device** with fail-OPEN on DB error. Code redemption is **register-only** — `RegisterRequest.invite_code` accepts `^QR-[A-HJ-NP-Z2-9]{6}$`. Re-engagement gated by `ENABLE_REENGAGEMENT_PUSHES`.

### Bundle history (sessions 44-52)
See `docs/SESSION_BUNDLES.md` — Bundles A (PR #3), B/C/D (PR #4), E (PR #5 + Session 48 merge `e67d583`), Session 49 (D1 scatter-gather + Bucket A 4-bug fix + D2 design+plan), Session 50 (D2 Section 3 + smart-fallback tuning + partial fragrances Tier 1.5 fix, head `378952d`), **Session 51 (2026-05-17)** ((a) D2 follow-up diagnostic: `DEBUG_STAGE_TIMINGS` per-task instrumentation `c38262c`; supplements + fragrances bottlenecks measured & RESOLVED (per-stage instrumentation, no code changes needed); (b) **Bundle B brainstorm** complete: spec `a491d46` + plan `91e1638` on `feature/bundle-b-two-input` (pushed); (c) **Bundle C scoring brainstorm** complete: spec `adb4f2b` + 4-Opus plan `67ae50d`, 5,785 lines / 170 tasks on `feature/bundle-c-scoring`), **Session 52 (2026-05-19)** Bundle B IMPLEMENTATION shipped (PR #6 + PR #7 merged `0c392f7` / `9ebf27d` — TwoInputShell + PaywallBanner + content_safety_service L1-L4 moderation + Tier 1.5 sentinel + ar/en i18n); Bundle C IMPLEMENTATION shipped this session (always-on, Option A — no flag-gating retrofit). 4-Opus team executed §1 trifecta fixes (A.3.1 `15f6b8e` pros/cons via `response_format=json_object`, A.3.2 `fb07ed8` factual_verdict builder restored, A.3.3 fix-1 `762946b` Serper meter + fix-2 `eca2e9d` gl=us GCC fallback), full A.5.x tier expansion + Migration 024 (5-tier budget incl `top_tier`), A.4.x calibration cascade (kill missing-data floor of 50, fabricated-defaults removal, calibrate_score has_signal short-circuit, comparison_quality detector, caption_key='limited_data', silent dim omission, Tier 2 spec fallback `74d49d5` with 4s asyncio.wait_for + asyncio.gather), A.6.1 VALUE_FORMULA_BY_PRIORITY (priority-driven coefficients, internal-only), A.7.1 confidence threshold loosening (qualitative legs), A.9.1 applied_shifts qualitative-only contract, A.10.1/A.10.2 diagnostics flag-gating + verdict prompt forbidden-words audit; Section B full UX (BudgetPicker 5-tier, DimensionBars overhaul incl silent omission + insufficient row + delta hero + value-match captions + hero+expand, ConfidencePills + ConfidenceDetailsSheet + sourceMethod helper, PersonalizationChip, ResultsScreen integration, all 5 critical rules enforced: no info banners / no backend internals in reveals / no "estimated" word in UI / no scary copy / diagnostic-first §1a/§1b/§1c). Deferred to v1.1: B.0 response_builder signature refactor, A.8.1 build_dimensions_v2 thin adapter from CATEGORY_DIMENSIONS, A.4.8 Tier 3 GPT-4o batched synthesis, A.6.2-A.6.5 value math richer copy, A.7.2 backend "estimated" leakage audit. **Active state:** Bundle E + Session 49 EAS group on `preview` is the latest `eas update`; Bundle C frontend pending EAS Update push T+24h post-merge tester-device verification. `STREAM_HARD_CAP_SECONDS=25.0` locks streaming p95 ≤25s. `SCRAPING_MODE=soft` URL gate **wired** at Firecrawl + Scrape.do call sites. Cold-cache wall floor measured Session 52 PRE-MERGE (fragrances 15.43s / electronics 14.74s / supplements 10.44s — all <25s lock). Bundle C v1 ship evidence: full pytest sweep + 1011/1011 frontend Jest + tsc 0 errors + security 98/98 + Migration 024 rollback drill clean + A.4.7 wall-budget code review verified. Post-merge 7-commit hot-fix sweep (`50e3290`/`44a0539`/`ed514c1`/`8798f5e`/`eb0f675`/`523bbfd`/`3d0bacf`) + 2 D.9 docs (`a18c387`/`3a1094a`) + retraction `d6e6014`. **FINAL: 9 of 9 backend contract items WORKING in production** (verified iPhone+Galaxy + CeraVe+Cetaphil — real `local_bhd` prices with retailers Best Buy/Walmart/Target). §1a "stuck empty" was qa parser bug (reading `products[*].pros` flat-None instead of `products[*].pros_cons.pros` nested-4 — see `memory/feedback_nested_field_path_in_parsers.md`). §1c non-supplements unblocked by Ahmed's Railway env-var swap (Serper `SERPER_API_KEY` was old key `d7f575f8...` returning HTTP 400 "Not enough credits"; swapped to active key `1d3cf422...` with 2139 credits — diagnostic capture by SERPER_SHOPPING_NON_200 instrumentation, see `memory/feedback_curl_test_vs_production_code.md` for false-positive lesson). Serper meter ticking confirmed (64/2200 used post-swap, was 0). Diagnostic logs persist (PROS_POP/RESPONSE_DIAG, GL_FALLBACK_TRACE, SHOPPING_QUERY_CLEAN, SERPER_SHOPPING_NON_200) — all flag-gated except SERPER_SHOPPING_NON_200 which is always-on (low-volume warning). Sentry CLEAN through T+~140min. Cold-cache wall 24.8s for iPhone+Galaxy approaches `STREAM_HARD_CAP_SECONDS=25` upper edge (v1.1 watch). **Pending v1.1 (polish only, NO ship-blocking bugs):** (1) B.0 response_builder kwarg refactor (greens 3 RED tests on metadata/personalization round-trip); (2) A.8.1 build_dimensions_v2 thin adapter from CATEGORY_DIMENSIONS; (3) A.4.8 Tier 3 GPT-4o batched synthesis (final-tier spec fallback when Tier 2 also blank); (4) A.6.2-A.6.5 richer value-math delta_text + cross-tier framing + per-product `value_match` + `budget_mismatch` metadata; (5) A.7.2 backend strip `price.note` field when `source_method=estimated` (defense-in-depth; UI already silent per `ca84eff`); (6) wall-budget watch + possible STREAM_HARD_CAP extension to 30s; (7) 4 edge-case probes (same-product, cross-cat, severe-missing, authenticated cohort). Bahrain Google Shopping merchant feed remains long-term op need (gl=us fallback is stopgap — see `memory/project_bahrain_shopping_feed_gap.md`). **Workflows:** worktree-team (`git worktree add -b feature/<name> ../smartcompare-<name> main` → 4-Opus TeamCreate, `mode: "bypassPermissions"` REQUIRED — sandbox blocks Bash otherwise → cross-QA → merge `--no-ff`); subagent-driven (`Agent(isolation: "worktree")` x2 in parallel for backend-only ~6-8-task scope, validated Session 50); **plan-writing-via-4-Opus (Session 51)** — pre-create plan skeleton with `<!-- OWNED BY: name -->` section anchors so 4 parallel agents can Edit one document without conflicts. **Arabic-as-default DROPPED** (Session 44).

### EAS Update infrastructure
See skill: `qaren-eas-deploy` (auto-loads when `eas update`, `eas build`, channel names, `runtimeVersion.policy`, or `expo.version` bumps are mentioned). Quick recall: OTA via `cd SmartCompareApp && eas update --branch <channel> --message "..."` — free, lands on next app open. Rebuild required for native module / app.json plugin changes. `appVersionSource: "remote"`. Interactive Expo commands (`eas login`, `eas build`) need a real terminal — Ahmed runs these directly.

### Luxury brand detection
`_is_luxury_brand()` + `COUNTERFEIT_KEYWORDS` filter across ALL categories. Tier 1.5 cascade: official brand → authorized retailers → GCC retailers (9 domains).

### Review + spec quality
Reviews: `_clean_review_content()` strips garbage (min 8 words), fixes sentiment misclassification, then `_clean_review_citations()` replaces `[snippet_N]` with domain attributions. Specs: GPT omits irrelevant fields (not "N/A"). Frontend filters nulls. Scoring applies `CATEGORY_MIN_COVERAGE` penalty.

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN` (backend + mobile share org `qaren-rr`, different DSNs), `LOG_LEVEL` (default INFO), `CORS_ORIGINS`, `STREAM_HARD_CAP_SECONDS` (default 25.0 — outermost `asyncio.wait_for` on `compare_from_text_streaming`), `SCRAPING_MODE` (`hard` default / `soft` skips Firecrawl+Scrape.do for non-luxury URLs via `firecrawl_service.should_fan_out`), `DEBUG_STAGE_TIMINGS` (default false — opt-in per-stage `metadata.stage_timings_ms` from `_fetch_product_data` + `compare_from_text`; cached at process init, zero prod overhead with flag off; disable after capture via Railway CLI)
**Price Scraping:** `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN` (timing out on GCC sites), `ENABLE_FIRECRAWL` (default true), `ENABLE_SCRAPEDO` (default true), `ENABLE_PAGE_SCRAPE` (curl_cffi).
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE`.
**Feature Flags:** `ENABLE_COHORT_PERSONALIZATION` (ON in Railway since 2026-05-05), `ENABLE_REFERRAL_SYSTEM`, `ENABLE_HYBRID_MODEL_ROUTING`, `ENABLE_REENGAGEMENT_PUSHES` (gates both `evaluate_user()` + cron — fail-CLOSED), `REENGAGEMENT_CANARY_PERCENT` (default 100; uses `app/utils/feature_bucket.py::hash_bucket()` djb2 mirror of `featureBucket.ts`). All flags default OFF in code; flip in Railway during canary. `REAL_ACTION_MIN_SECONDS` (default 5).

Operational rollout sequence + canary monitoring guidance: see `docs/CONTEXT_SESSION_LOG.md`.

## Tests

```bash
# Free unit tests (~$0)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Live unit tests (iHerb, Serper, GPT — ~$0.03)
python -m pytest tests/ -v -m "not (live_db or integration)"

# Integration tests (live Railway — ~$0.06)
python -m pytest tests/test_integration.py -v -m integration

# Full suite
python -m pytest tests/ -v --timeout=180
```

- `python -m py_compile <file>` for syntax checks; `npx tsc --noEmit` for frontend types.
- `conftest.py` auto-loads `.env` via python-dotenv.
- ~100 test files (`test_<feature>.py`, one per service). 80%+ coverage target for new features.
- No regressions: all existing tests must pass before merging.

### Dependency Scanning (pre-deploy)
```bash
pip-audit -r requirements.txt --strict
cd SmartCompareApp && npm audit --audit-level=high
```

## Pre-launch (App Store / Google Play)

ToS/Privacy fact base, code-side blockers (delete cascade, expo-notifications plugin, Sentry URL scrubbing, ToS clickwrap + 13+ gate, `ai_sharing_enabled` default), stale legal docs, and the 25-item DECISIONS REQUIRED block: see `docs/plans/2026-05-06-tos-fact-base.md` and `docs/plans/2026-05-06-tos-evidence/`. Stale legal markdown at `app/legal/{privacy_policy,terms_of_service}.md` is served live but says "SmartCompare" / `@smartcompare.app` — REPLACE, do not patch.

**Age policy (locked):** 13+ general audience including teens. Apple **12+**, Google Play **Teen**. Do NOT enroll in Apple "Kids" or Google "Designed for Families".

**Canary phasing:** With <10 testers pre-launch, set new-feature canary % to 100 — lower % statistically hash-buckets a small tester set out of the feature being tested. Drop to 10 only at App Store soft-launch, then ramp 10→50→100 per `docs/runbooks/qaren-canary-onboarding.md`.

## Known Remaining Bugs (deferred)
- **Scrape.do timing out** on GCC luxury retailers (Ounass, Bloomingdales). Firecrawl is primary — Scrape.do is Tier 1.5d fallback only. Investigation `docs/investigations/2026-05-16-scrapedo-timeout-analysis.md` — recommendation: **accept current behavior** (graceful Tier 2 fallback).
- **Apple Sign-In:** deferred — requires Apple Developer subscription ($99/year); code is ready.

## Detailed Context
Index: `docs/CLAUDE_CODE_CONTEXT.md`. Key files: `CONTEXT_ARCHITECTURE.md`, `CONTEXT_SESSION_LOG.md`, `CONTEXT_REFERENCE.md`.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SmartCompare — An INTELLIGENT product comparison engine for the GCC market (Saudi Arabia, UAE, Kuwait, Qatar, Bahrain, Oman). The goal: if users still go to Google or ChatGPT after using SmartCompare, we failed.

## Philosophy: SMART, Not Just Cheap

Be intelligent about every decision:
- **Smart data usage:** Extract maximum value from every API call
- **Smart caching:** Know WHEN data is still valid vs needs refresh
- **Smart fallbacks:** Graceful degradation with quality indicators
- **Smart decisions:** Use the right tool for each task

**Intelligence principles — apply these to every change:**
1. Don't fetch what you already have (smart caching)
2. Don't call twice when once is enough (call merging)
3. Don't guess when you can verify (data validation)
4. Don't hide data — show confidence levels (transparency)
5. Don't waste vision data — use what you see (OCR utilization)

## Quality Standards (Non-Negotiable)

- Accurate specs from reliable sources
- Ratings from real sources — all displayed without verified/unverified badges
- Real prices with retailer attribution
- Honest recommendations based on data, not guesses

## Workflow Rules

1. Read `docs/CLAUDE_CODE_CONTEXT.md` before major changes — learn from what worked and what didn't
2. Think before calling — is this API call necessary?
3. Quality first, then optimize
4. Show confidence, not false certainty
5. Plan → Approve → Implement → Test
6. For multi-file features (3+ files, frontend+backend): use parallel agent teams (TeamCreate with 4 Opus agents: backend, frontend, test, qa)
7. After major features: update CLAUDE.md (project context), MEMORY.md (learnings), CONTEXT_SESSION_LOG.md (what changed)

## Pending Manual Setup (as of 2026-05-04)

1. ~~Apply migration 013~~ — **DONE 2026-05-04** (vw_cohort_feedback_lift had a column-name bug, fixed in df8bf8a then applied).
2. **Migrate Railway hosting** to new account (sub trial expired 2026-05-03). Re-add ALL env vars from old project; see Environment Variables section. Old Railway URL `web-production-58776.up.railway.app` will go offline.
3. **Add NEW env var during Railway migration:** `ENABLE_COHORT_PERSONALIZATION=false` (defaults `false` in code; explicit set documents Phase 1 intent).
4. **Phase 1 cohort rollout** (after 2-3 done): flip flag for admin accounts only → watch `/admin/cohort.html` metrics → 10% canary → full. See design doc Section 6.6.
5. **Open backfill PR** (optional, do alongside 2-4): `gh pr create` not available locally — manually compare `553b091...main` via GitHub web UI for review trail of the 30+ cohort commits. Scope includes the 12c2879 fix that wires B end-to-end.

## Critical: Two app/ Directories

- **`app/`** (root) — The DEPLOYED backend. Railway runs `uvicorn app.main:app` from root.
- **`backend/app/`** — Older/alternate version. NOT deployed. Do NOT edit.
- Always edit files in root `app/` for changes to take effect.

## Commands

### Backend
```bash
# Run locally
cd C:\Users\SynAckITPC\Documents\AI\smartcompare
uvicorn app.main:app --reload --port 8000

# Syntax check a file
python -m py_compile app/services/structured_comparison_service.py

# Test endpoint (production)
curl https://web-production-58776.up.railway.app/health
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"

# Deploy: push to main, Railway auto-deploys in ~90s
git push origin main

# After deploy: verify new features work in production
# Example: Test category selection with wrong category (should switch)
curl -s "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&selected_category=grocery&nocache=true" | python -c "import sys, json; r=json.load(sys.stdin); print(f\"switched: {r.get('category_switched')}, used: {r.get('category_used')}\")"
```

### Frontend (React Native / Expo)
```bash
cd SmartCompareApp
npx expo start                    # Dev server (use --clear after dep changes)
npx tsc --noEmit                  # TypeScript check (0 errors as of Mar 8 2026)
npx expo install --check          # Verify deps match SDK version
npx expo-doctor                   # Full project health check
```

### Dependencies
- Backend: `pip install -r requirements.txt` (Railway uses this, NOT pyproject.toml)
- Frontend: `npm install` in `SmartCompareApp/`
- **Expo version alignment:** All native packages MUST match Expo SDK version. Use `npx expo install <pkg>` (not `npm install`) for native deps. JS/native version mismatch causes cryptic `NativeWorklets`/`HostFunction` crashes in Expo Go.

### Migrations
Supabase DDL migrations (`migrations/*.sql`) must be applied manually via [SQL Editor](https://supabase.com/dashboard/project/qulajmyxdbdkchvecmvc/sql/new). No psql or Management API token available locally. Before running `CREATE TABLE IF NOT EXISTS`, check existing schema — stale tables with different columns cause silent index/policy failures.
- `011_security_completion_freemium.sql` — APPLIED. user_usage, admin_audit_log, RLS, subscription_tier column, increment_lifetime_comparisons function.
- `012_product_data_tables.sql` — APPLIED. product_specs, product_prices, product_reviews + RLS.
- `013_demographics_cohort.sql` — APPLIED 2026-05-04. demographics_profile column on users + dismissal tracking + 3 metric views (vw_cohort_match_rate, vw_cohort_persona_distribution, vw_cohort_feedback_lift). Note: `vw_cohort_feedback_lift` uses `comparison_feedback.useful` (boolean) — the original spec assumed a non-existent `rating` column; fixed in commit df8bf8a before apply.

## Architecture

### Backend (FastAPI + Python 3.12)

**Entry:** `app/main.py` — loads env vars, configures middleware stack, registers 11 routers (in `app/api/`):
- `/api/v1/text/*` — `text_routes.py` → `structured_comparison_service.py` (primary flow + SSE streaming, rate limited)
- `/api/v1/image/*` — `image_routes.py` → GPT-4o-mini vision → auto-compare (rate limited, HEIC detection)
- `/api/v1/url/*` — `url_routes.py` (single URL compare only, SSRF-protected, rate limited 10/min)
- `/api/v1/auth/*` — `auth_routes.py` → Supabase Auth (login, register, refresh, profile, email, password, social-login, **account deletion**, resend-verification, **demographics**, **cohort-profile**). Rate limited: login 5/min, register 3/min, delete 1/min, demographics 5/min.
- `/api/v1/comparisons/*` — `history_routes.py` → comparison history (GET list, GET single, DELETE). Auth required.
- `/api/v1/share/*` — `share_routes.py` → POST create share link (auth), GET public share (no auth, strips personalization)
- `/api/v1/feedback`, `/api/v1/events` — `feedback_routes.py` → feedback collection + event tracking
- `/api/v1/admin/*` — `admin_routes.py` → analytics endpoints + cost dashboard (X-Admin-Key auth, timing-safe `hmac.compare_digest`, rate limited 30/min)
- `/api/v1/legal/*` — `legal_routes.py` → GET privacy policy + terms of service (no auth, reads markdown files)
- `/api/v1/app/*` — `version_routes.py` → GET version check (min/latest/force_update from env vars, no auth)
- `/api/v1/usage/*` — `usage_routes.py` → GET usage status (auth required). Freemium tier enforcement.

**Middleware stack** (outermost → innermost): RequestID → SecurityHeaders (HSTS, CSP, X-Frame-Options) → ErrorHandler → CORS → slowapi rate limiter

**Unified error format:** All error responses use `{ success: false, error: "message", code: "ERROR_CODE", request_id: "uuid" }`. Codes: `AUTH_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `RATE_LIMITED`, `VALIDATION_ERROR`, `INTERNAL_ERROR`. Frontend `parseApiError()` handles both `.error` (new) and `.detail` (legacy FastAPI) formats.

**Core service:** `app/services/structured_comparison_service.py` (1,454 lines — orchestrator only)
- `StructuredComparisonService` — **per-request instances** via `get_comparison_service()` (NOT singleton, for concurrency safety)
- `compare_from_text(query, region, vision_products?, selected_category?, user_id?)` — main entry point
- `compare_from_text_streaming(..., user_id?)` — async generator yielding SSE events (specs→prices→reviews→scores→verdict→complete)
- **Pre-fetch:** Unified web search (1 Serper call) shared by specs + reviews — gated by cache check
- **Phase 1:** specs + price fetched in parallel (specs reuses unified search)
- **Phase 2:** reviews + rating fetched in parallel (reviews reuses unified search, shopping data from Phase 1 feeds ratings)
- **Scoring:** deterministic scoring after Phase 2 via `scoring_service.py` (zero API cost), plus value badges, tradeoff pairs, confidence indicators
- **Behavioral profile:** `_fetch_behavior_profile()` before scoring, `_update_behavior_profile()` fire-and-forget after response assembly
- `_shopping_items_cache` — populated during price search, used by rating/review injection. Cleared per-request.
- **Response format:** Top-level keys: `overview`, `specs`, `reviews`, `scoring`, `personalization`, `metadata`. Backward compat aliases preserved (`products`, `comparison`, `winner_index`, `recommendation`, `key_differences`).

**Decomposed modules** (extracted from monolith in Session 35):
- `price_service.py` (932 lines) — All pricing: tiers, currency conversion, page scraping, iHerb, pharmacy JSON-LD
- `rating_service.py` (292 lines) — Tiered rating extraction, Google consensus, retailer classification
- `review_service.py` (227 lines) — Review fetching, content cleaning, citation replacement
- `fact_check_service.py` (217 lines) — Citation verification, cross-validation, confidence computation
- `response_builder.py` (190 lines) — `build_comparison_response()` for both sync and streaming paths

**Price pipeline (3 tiers + page scraping + pharmacy JSON-LD):**
1. Serper Shopping API direct extraction (structured prices)
2. GPT-4o-mini extraction from organic search results (with Tier 3 sanity check)
3. GPT training data estimate (marked `estimated: true`)
- **Page scraping**: `_fetch_page_price()` → `_curl_fetch_html()` + `_extract_price_from_html()` extracts JSON-LD/OG/microdata from product pages. Used in Tier 1.5 cascade and supplement pipeline.
- **Firecrawl Smart Wait**: `firecrawl_service.scrape_page_with_status()` renders SPA pages via Firecrawl `/v1/scrape` API. Used in Tier 1.5a for official brand sites. `source_method: "firecrawl"`. **Timeout: 30s** (luxury SPAs like LV/Gucci need >15s to render). Validated: LV (14,600 AED), Gucci ($3,450), Bloomingdales (AED 560).
- **Scrape.do fallback**: `scrapedo_service.render_page_with_status()` renders pages with residential proxies. Used in Tier 1.5d only when curl_cffi fetched HTML but found no price (`failed_curl_urls`). `source_method: "scrapedo_rendered"`.
- **API budget + circuit breakers**: `api_budget_service.py` tracks credits (Firecrawl 450/lifetime, Scrape.do 900/mo, Serper 2200/lifetime) and circuit breakers (3 failures → 10min cooldown). Fail-open on Redis unavailability.
- **Gate 0 validation**: `_validate_price_query()` rejects garbage queries, `_validate_scrape_url()` rejects search/category pages before burning scrape credits.
- **Feature flag**: `ENABLE_PAGE_SCRAPE` (curl_cffi). Firecrawl/Scrape.do availability checked via `is_available()` (env var + feature flag).
- **Price philosophy:** "MOST AUTHORITATIVE" not "LOWEST reasonable". Source priority: official brand sites > authorized retailers > major marketplaces. Counterfeit sources filtered (DHgate, AliExpress, Temu, Wish).
- Official domain boost: prices from `OFFICIAL_BRAND_DOMAINS` (25+ domains) sorted first in Shopping results.
- Each price tagged with `source_method`: `local_bhd` (direct BHD price), `converted_usd` (USD→BHD conversion), `page_scrape` (curl_cffi HTML), `page_scrape_rendered` (JS-rendered HTML), or `estimated` (GPT training data). `price_method_mismatch` flag set when products have different source methods.
- Supplements: iHerb direct scrape → Bahrain pharmacy JSON-LD → Serper organic + GPT → Tier 3
- Non-iHerb brands (HealthAid, Vitabiotics): `_fetch_pharmacy_price()` parses JSON-LD from bn.boots.com product pages

**Rating pipeline:** Tier 1 (Serper Shopping, trusted retailers) → Tier 2 (known retailers incl. luxury/fashion) → Tier 3 (eBay if review_count > 1000) → Fallback (GPT `average_rating`, unverified). Consensus: 3+ identical → Google product aggregate. iHerb ratings extracted during price scrape (zero extra calls). All ratings displayed without verified/unverified badges.

**URL sourcing:** Serper Shopping `link` field primary, `_build_retailer_url()` fallback. Frontend `openRatingSource()` uses `rating_source.url` first.

**Supplement-specific behavior:**
- Serper Shopping returns ZERO results for supplements — iHerb direct scrape via `curl_cffi` used instead
- Non-iHerb brands: `_fetch_pharmacy_price()` → `site:bn.boots.com` search → JSON-LD parsing. Brand matching is space-insensitive.
- bolo.bh NOT indexed by Google (Vue.js SPA); bn.boots.com IS indexed with JSON-LD prices
- **Bahrain Drug Database**: 655 registered health products in `bahrain_approved_drugs` table. `find_matching_drugs()` via full-text search, injected into spec prompt for supplements only.
- **Supabase gotcha**: `text_search()` needs `options={"type": "plain", "config": "english"}` (NOT keyword args); `.limit()` BEFORE `.text_search()` in chain

**Key services** (in `app/services/`):
- `extraction_service.py` — GPT prompts, `CATEGORY_SPEC_SCHEMAS` (9 categories), structured verdict + review_summary. Injects prompt personality + trust rules.
- `scoring_service.py` — Deterministic scoring ($0). Category-specific 6 dimensions via `CATEGORY_DIMENSIONS`. Value badges, tradeoffs, confidence. Personalization caps: ±30%/±10%/±5%.
- `prompt_personalities.py` — Per-category comparison "language". `build_personality_prompt(category)`.
- `trust_validation_service.py` — Cross-checks GPT claims against deterministic scores. Zero cost.
- `behavior_service.py` — Decay-weighted profiles (30-day half-life). Category affinity, price range, dimension sensitivity.
- `cache_service.py` — **IMPORTANT**: use `_redis_get()`, `_redis_set()`, `_redis_incr()`, `_redis_expire()` helpers for general use. `api_budget_service` uses `redis_client.incrby()`/`incrbyfloat()` directly for atomic operations.
- `api_budget_service.py` — Credit tracking + circuit breakers for Firecrawl, Scrape.do, Serper. Uses atomic Redis ops.
- `exchange_rate_service.py` — Daily rates from frankfurter.app, Redis-cached 24h, hardcoded GCC fallbacks. `get_rate(from_currency, to_currency="BHD")`.
- `firecrawl_service.py` / `scrapedo_service.py` — Firecrawl Smart Wait + Scrape.do JS rendering wrappers.
- `database_service.py` — Dual Supabase client (`get_user_supabase_client(token)` for RLS, `get_admin_supabase_client()` for admin ops). Share tokens, cascade delete, history queries.
- `usage_service.py` — Freemium tier enforcement. Free: 3 lifetime + 10/month + 3/day. Premium: 70/month + 10/day. Redis counters + Supabase persistence. `check_usage_allowed()`, `record_comparison()`, `get_usage_status()`.
- `audit_service.py` — Fire-and-forget security event logging to `admin_audit_log` table. Events: login, lockout, usage_limit, injection_attempt.
- `product_data_service.py` — L2 DB cache for specs (30d), prices (24h), reviews (14d). Redis miss → DB check → API call. Prices append (history), specs/reviews upsert. Fire-and-forget saves.
- `cohort_service.py` — Survey-driven cohort matching (Session 41). Singleton loads `data/cohort_priors.json` once at startup. `match(demographics)` does hierarchical fallback (exact → broadened_governorate → broadened_language → broadened_age → population). `seed_preferences()` maps cohort modal → existing 4 preference fields with `_sources` tags. `get_display_profile()` returns Profile-card dict (None for low/population matches). Zero per-request IO. Built by `scripts/build_cohorts.py` from Fillout survey CSVs in `data/surveys/` (gitignored — only `data/cohort_priors.json` is committed).
- Other services: `serper_service`, `feedback_service`, `drug_database_service`, `openai_service`, `sentry_service`, `analytics_service`

**Security** (`app/utils/`):
- `url_validator.py` — SSRF protection: resolves hostnames, blocks private/loopback/link-local IPs, allows only http/https

**Middleware** (`app/middleware/`): request_id, security headers (HSTS, CSP, X-Frame-Options, nosniff), rate_limiter (slowapi, 10/min on compare), error_handler (Sentry capture + `before_send` JWT/key scrubbing), logging_config (structured JSON)

### Frontend (React Native + Expo)

**Location:** `SmartCompareApp/`

**App name:** Qaren (قارن). Bilingual EN/AR with full RTL support.

**Navigation:** Bottom tabs (Home/History/Profile) via `@react-navigation/bottom-tabs`. Results as modal. Auth stack (Login/Register/ForgotPassword). Splash → Onboarding → Auth → Main flow in `App.tsx`.

**Screens (10):** SplashScreen (logo animation), OnboardingScreen (6-step wizard), LoginScreen, RegisterScreen, ForgotPasswordScreen, HomeScreen (camera-first + search overlay + categories), ResultsScreen (single-scroll + skeleton loading + winner reveal), HistoryScreen (date-grouped FlatList), ProfileScreen (settings/language/account), PaywallScreen (bottom sheet placeholder).

**Design system:** `src/theme/index.ts` (emerald #10B981 accent, Inter+Cairo fonts). Components: Button, Card, Chip, SkeletonLoader, ProgressBar, IconButton, ComparisonCounter, SearchOverlay. i18n: `src/i18n/` (180+ keys EN/AR).

**Deleted screens:** CameraScreen (absorbed into HomeScreen), AccountScreen (replaced by ProfileScreen), PreferencesScreen (replaced by OnboardingScreen).

**Services:**
- `api.ts` — Axios to Railway (120s timeout). SSE via `streamComparison()` (fetch+ReadableStream, fallback to non-streaming). JPEG transcoding before upload.
- `authService.ts` — Supabase auth + social login. `verifyAuth()` returns `User | null` (NOT boolean). Tokens in `expo-secure-store` (NOT AsyncStorage). OAuth nonces via `expo-crypto`. All console.log wrapped in `__DEV__` guards.
- `certificatePinning.ts` — SSL pinning for Railway backend (LE intermediate SPKI). Initialized once from `api.ts`.

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls intelligently.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have.
- **Supabase** — PostgreSQL (users, comparisons, search_logs, bahrain_approved_drugs, comparison_feedback, user_events, user_usage, admin_audit_log, product_specs, product_prices, product_reviews) + Auth. Cache strategically.
- **Upstash Redis** — Response caching (prices 24h, specs/reviews 7d)

## Important Patterns

### Fact-checking (zero-cost cross-validation)
Every product has a `fact_check` object (`overall_confidence`: high/medium/low). Spec citations verified against snippets, review sentiment checked against Serper (0.8 tolerance), price vs Shopping median (30% threshold). Zero extra API calls. **Ratings are NEVER AI-generated** — GPT prompt explicitly forbids generating `source_ratings`.

### `product.price` is an object, not a number
Backend returns `{ amount, currency, retailer, url, estimated }`. Frontend code must access `product.price.amount`, not `product.price` directly.

### GCC_REGIONS keys (extraction_service.py)
Keys are: `bahrain`, `saudi_arabia`, `uae`, `kuwait`, `qatar`, `oman`. Note: it's `saudi_arabia` NOT `saudi`.

### Per-request service instances
`get_comparison_service()` returns a **new instance per call** (not a singleton). Each request gets fresh `total_cost`, `api_calls`, `_shopping_items_cache`. No manual reset needed.

### Cost budget + caching
Target: **$0.01/comparison**. Achieved via unified search (1 Serper call shared by specs + reviews in `_fetch_product_data()`). Track with `self.total_cost` and `self._track_cost()`. **Two-layer cache:** L1 Redis (specs/reviews 7d, prices 24h) → L2 DB via `product_data_service.py` (specs 30d, prices 24h, reviews 14d) → API call. `?nocache=true` bypasses both layers. Camera input passes `vision_products` directly, skipping `parse_product_query()`.

### Deterministic scoring (zero cost)
`scoring_service.py` computes **category-specific scores** from structured data. No API calls — pure math.
- Each of 9 categories has its own 6 scoring dimensions via `CATEGORY_DIMENSIONS`. Old universal keys (`price_score`, `spec_score`, etc.) NO LONGER EXIST except in "other" category.
- Price tiers: budget(<11 BHD), mid(11-57), premium(57-189), luxury(189+). Cross-tier uses expectations formula, same-tier uses spec/price blend.
- Personalization caps: explicit ±30%, behavioral ±10%, session ±5%.
- Outputs: dimension scores, value badges, tradeoff pairs, confidence indicators, dimension winners.
- `build_scores_summary()` injects tier info and dimension leaders into verdict prompt.
- Rollback: V1 system preserved in `docs/ROLLBACK_SCORING_V1.md`.

### Prompt personalities + trust validation
Each category gets unique GPT comparison tone via `build_personality_prompt(category)` — zero extra cost. `validate_verdict()` cross-checks GPT claims against deterministic scores (returns `winner_aligned`, `claims_flagged`, `confidence_adjustment`).

### Auth + security hardening (Session 38)
**Dual Supabase client:** `get_user_supabase_client(access_token)` (anon key + JWT, RLS enforced) vs `get_admin_supabase_client()` (service-role, admin-only). User-facing DB functions accept `access_token` param. Old `get_supabase_client()` is deprecated alias for admin client.
**RLS active:** All user-data tables have row-level security policies (applied via `migrations/010_enable_rls.sql`). Cascade delete via `delete_user_cascade()` SECURITY DEFINER function called through `.rpc()`.
**Token security:** Tokens stored in `expo-secure-store` (Keychain/Keystore), NOT AsyncStorage. Token revocation on logout via Redis blacklist (`revoked:{sha256(token)}`, 1hr TTL). `verify_token()` checks blacklist before Supabase validation.
**Certificate pinning:** `certificatePinning.ts` pins Let's Encrypt E8+E5 intermediate SPKI hashes. Requires EAS dev build (no-op in Expo Go). See `docs/SECURITY_HARDENING_CONTEXT.md` for SPKI hashes and rotation process.
**Other:** Account deletion cascades atomically (App Store requirement, rate limited 1/min). Password: 10+ chars, 1 upper, 1 lower, 1 digit. Email change requires current password. Admin endpoints rate limited 30/min. History routes use `hmac.compare_digest` + merged 404/403. Swagger docs disabled in prod. SQL LIKE wildcards escaped. Sentry `before_send` scrubs JWT/API keys from events. CORS origins configurable via `CORS_ORIGINS` env var.
**Regression tests:** `tests/test_security_regression.py` (57 tests) — guards against removing protections. Do NOT delete or skip these tests.

### SSE streaming
`GET /api/v1/text/compare/stream` → 10 SSE events with `progress` field (10/20/50/80). Frontend uses fetch+ReadableStream (not EventSource) with fallback to non-streaming.

### Feedback and event tracking
`POST /api/v1/feedback` + `POST /api/v1/events` (batch). Both auth-optional, fire-and-forget. Tables: `comparison_feedback` + `user_events` with RLS.

### Personalization (zero extra cost)
4 preference dimensions collected once after first login (PreferencesScreen): priorities (1-3 of 8 + 6 cohort-derived), budget (budget/mid/premium), lifestyle (0+ of 11 tags), brand attitude. Stored as JSONB in `public.users.preferences` along with `_sources` sub-object marking each field as `user_stated` or `inferred`. `GET/PUT /api/v1/auth/preferences`.
- **Three-layer system:** Explicit preferences (±30%) → Behavioral profile (±10%, decay-weighted 30-day half-life) → Session signals (±5%) → Category defaults
- `_build_preferences_prompt()` appends to verdict prompt — zero extra API cost
- `behavior_service.py`: category affinity, price range, winner agreement, dimension sensitivity. Fire-and-forget profile update after each comparison.
- `scoring_method`: "category_weighted" (anon), "personalized" (explicit prefs), "behavioral" (behavior/session active)
- VALID_PRIORITIES extended in Session 41: original 8 + 6 cohort enums (`quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`). VALID_BRAND_ATTITUDE adds `trust_known_brands`.

### Cohort personalization (Session 41 — feature-flagged)
Survey-driven priors from ~400 Fillout responses bootstrap personalization for new/anonymous users. **Feature flag `ENABLE_COHORT_PERSONALIZATION` defaults false** in code (per design 6.6); turn on once Phase 1 internal QA validates.
- **PUT /api/v1/auth/demographics** (auth, 5/min) — accepts age_group/gender/governorate/language/country (all optional, "Prefer not to say" treated as missing). Auto-derives language from Accept-Language and country from CF-IPCountry. Stores `users.demographics_profile` JSONB with cached `cohort_match` snapshot. If user has no preferences (or all are inferred), seeds them from cohort modal — never overwrites `user_stated`.
- **GET /api/v1/auth/cohort-profile** (auth) — returns Profile-screen "style profile" card data, or `{display: null}` for low/population matches.
- **PUT /api/v1/auth/preferences** — extended to flip `_sources` to `user_stated` when user edits a previously-inferred field.
- `_build_preferences_prompt(prefs, demographics_profile=...)` (extraction_service) appends a ~120-token cohort priors block when match_quality ∈ {exact, broadened_governorate, broadened_language} AND feature flag on. Privacy: NO raw age/gender/identity in prompt — only country/language/governorate thin context line + aggregate findings.
- `cohort_service.match()` is in-memory only (singleton loads `data/cohort_priors.json` once at startup). Re-run `python -m scripts.build_cohorts` to regenerate.
- Admin metrics: `GET /api/v1/admin/cohort/{metrics,feedback,retention}` + dashboard at `/admin/cohort.html` (Chart.js, X-Admin-Key auth).

### Category selection (soft validation)
9 categories: Electronics, Grocery, Supplements, Makeup, Skincare, Haircare, Fragrances, Fashion, Other. `selected_category` is a hint — backend AI makes final decision via `PRODUCT_PARSER_PROMPT`. Mismatch → `category_switched: true` + frontend info banner. Each category has a dedicated spec schema in `CATEGORY_SPEC_SCHEMAS` (extraction_service.py). Zero extra API cost.

### Sharing + History
Sharing: 22-char URL-safe token (128-bit, `token_urlsafe(16)`) in `comparisons.share_token`, public access strips personalization. History: paginated, searchable, ownership-checked. On 401, clears session + redirects to auth.

### Luxury brand detection
`_is_luxury_brand()` + `COUNTERFEIT_KEYWORDS` filter across ALL categories. Tier 1.5 cascade: official brand → authorized retailers → GCC retailers (9 domains). See price pipeline above for details.

### Review + spec quality
Reviews: `_clean_review_content()` strips garbage (min 8 words), fixes sentiment misclassification, then `_clean_review_citations()` replaces `[snippet_N]` with domain attributions. Specs: GPT omits irrelevant fields (not "N/A"). Frontend filters nulls. Scoring applies `CATEGORY_MIN_COVERAGE` penalty.

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN` (enables error tracking), `LOG_LEVEL` (default: INFO), `CORS_ORIGINS` (comma-separated allowed origins, defaults to Railway + localhost)
**Price Scraping:** `FIRECRAWL_API_KEY` (firecrawl.dev, 500 lifetime free — deployed), `SCRAPEDO_API_TOKEN` (scrape.do, 1000/mo free — deployed, but timing out on GCC sites), `ENABLE_FIRECRAWL` (default true), `ENABLE_SCRAPEDO` (default true). Both keys live in Railway since Session 34.
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE` (all optional, used by `/api/v1/app/version`)
**Cohort Personalization (PENDING — Railway sub renewal needed):** `ENABLE_COHORT_PERSONALIZATION` (default `false` in code, so absence is safe). Add when Railway account is migrated. See memory `pending_railway_migration.md`.

### Serper API Credits
~2,500 credits (rotated Feb 28 2026). ~3-4 calls/comparison. Cached = free, only `nocache=true` burns credits. **To rotate**: new account at serper.dev (free tier 2,500), update `SERPER_API_KEY` in Railway.

## Tests

```bash
# Free unit tests (~1618+ tests, ~23s, $0)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Live unit tests (iHerb, Serper, GPT — ~$0.03)
python -m pytest tests/ -v -m "not (live_db or integration)"

# Integration tests (live Railway — ~$0.06)
python -m pytest tests/test_integration.py -v -m integration

# Full suite
python -m pytest tests/ -v --timeout=180
```

- `python -m py_compile <file>` for syntax checks, `npx tsc --noEmit` for frontend types
- `conftest.py` auto-loads `.env` via python-dotenv
- ~65 test files named `test_<feature>.py`, one per service. 80%+ coverage for new features.
- No regressions: all existing tests must pass before merging

### Dependency Scanning (pre-deploy)
```bash
pip-audit -r requirements.txt --strict
cd SmartCompareApp && npm audit --audit-level=high
```

## Known Remaining Bugs (deferred)

These are known issues that have been intentionally deferred:
- **Scrape.do timing out**: Scrape.do free tier times out (15s) on GCC luxury retailers (Ounass, Bloomingdales). Firecrawl works — it's the primary scraper. Scrape.do is Tier 1.5d fallback only.
- **value_context identical for all products**: `overview.products[i].value_context` uses same string from comparison dict for all products. Minor UX issue.
- Google Sign-In: Supabase Google provider needs to be enabled in dashboard (client IDs configured in code)
- Apple Sign-In: deferred — requires Apple Developer subscription ($99/year); code is ready

## Detailed Context
See `docs/CLAUDE_CODE_CONTEXT.md` for the index of all context files. Key files: CONTEXT_ARCHITECTURE.md (system design), CONTEXT_SESSION_LOG.md (development history), CONTEXT_REFERENCE.md (testing/deploy).

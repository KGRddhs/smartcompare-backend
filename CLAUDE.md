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
```
IDE/LSP TS diagnostics on Windows are unreliable (`typescript-lsp` plugin bug, see MEMORY.md). Trust ONLY `npx tsc --noEmit` exit code — ignore stale "Cannot find module" / "JSX flag not set" errors from system-reminders unless `tsc` actually fails.

### Dependencies
- Backend: `pip install -r requirements.txt` (Railway uses this, NOT pyproject.toml)
- Frontend: `npm install` in `SmartCompareApp/`
- **Expo native deps:** use `npx expo install <pkg>` (not `npm install`). JS/native version mismatch causes cryptic `NativeWorklets` / `HostFunction` crashes in Expo Go.

### Migrations
Supabase DDL (`migrations/*.sql`): preferred path is **Supabase MCP** (`mcp__plugin_supabase_supabase__apply_migration`) — tracks migration history table. Fallback: [SQL Editor](https://supabase.com/dashboard/project/qulajmyxdbdkchvecmvc/sql/new). **Gotcha:** SQL Editor wraps multi-statement scripts in one transaction, so a failing view rolls back the ALTER TABLE before it — always verify schema after apply (`information_schema.columns`). Before `CREATE TABLE IF NOT EXISTS`, check existing schema — stale tables with different columns cause silent index/policy failures.

Applied: 010 (RLS), 011 (freemium + audit log), 012 (product data tables), 013 (demographics + cohort views, applied 2026-05-05 via MCP after a 2026-05-04 SQL Editor rollback), 014 (referral system), 015 (push tokens), 016 (referral invite privacy JSONB), 017 (share_token VARCHAR→TEXT), 018 (referral_redemptions.expires_at + expiry_reminder_sent_at + referral_invites.deep_review_expires_at + partial-WHERE index, 2026-05-07 via MCP — verified live), 019 (users.attribution_source TEXT NULLABLE with CHECK enum mirror, 2026-05-07).

## Architecture

### Backend (FastAPI + Python 3.12)

**Entry:** `app/main.py` — env vars, middleware stack, registers 14 routers in `app/api/`:
- `/api/v1/text/*` → `text_routes.py` → `structured_comparison_service.py` (primary flow + SSE, rate limited)
- `/api/v1/image/*` → `image_routes.py` → GPT-4o-mini vision → auto-compare (rate limited, HEIC detection)
- `/api/v1/url/*` → `url_routes.py` (single URL compare, SSRF-protected, 10/min)
- `/api/v1/auth/*` → `auth_routes.py` → Supabase Auth (login, register, refresh, profile, email, password, social, account deletion, demographics, cohort-profile). Rate limited per route.
- `/api/v1/comparisons/*` → `history_routes.py` (auth required)
- `/api/v1/share/*` → `share_routes.py` (POST auth, GET public — strips personalization)
- `/api/v1/feedback`, `/api/v1/events` → `feedback_routes.py` (auth-optional, fire-and-forget)
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
- `usage_service.py` — Freemium tier. Free: 3 lifetime + 10/month + 3/day. Premium: 70/month + 10/day. Redis counters + Supabase persistence.
- `audit_service.py` — Fire-and-forget security event logging (`admin_audit_log`). Events: login, lockout, usage_limit, injection_attempt.
- `product_data_service.py` — L2 DB cache: specs (30d), prices (24h, append-history), reviews (14d). Redis miss → DB check → API call.
- `cohort_service.py` — Survey-driven cohort matching. Singleton loads `data/cohort_priors.json` once at startup. Hierarchical fallback (exact → broadened_governorate → broadened_language → broadened_age → population). Built by `scripts/build_cohorts.py` from gitignored CSVs in `data/surveys/`; only `data/cohort_priors.json` is committed.
- `model_router_service.py` — Hybrid model routing. `get_model(priority="high")` returns `gpt-4o` below 80% of `DAILY_4O_CAP`, else `gpt-4o-mini`. Atomic `INCRBY` per UTC date. 429 retries to mini once. Fail-open on Redis. Used by verdict generation; specs/prices/reviews stay on mini.
- `referral_service.py` — Smart Decision Referrals. `link_invite_to_user`, `try_trigger_loop2`, code generation.
- `abuse_detection_service.py` — `evaluate_invite()` priority: SAME_DEVICE > DISPOSABLE_EMAIL > BELOW_REAL_ACTION_THRESHOLD (`elapsed_seconds` proxy from `metadata.elapsed_seconds`, `REAL_ACTION_MIN_SECONDS` env, default 5s).
- `push_service.py` — Expo Push (deep-link `qaren://profile/referrals`).
- `reengagement_service.py` — Daily cron `scripts/cron_reengagement.py`. 3 detectors: `decision_insight`, `cohort_curiosity`, `decision_retrospective`. 7-day per-user cap.
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

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have. ~2,500 credits remaining (rotated 2026-02-28); cached = free, only `nocache=true` burns credits. Rotate via new free account at serper.dev.
- **Supabase** — PostgreSQL + Auth. Tables: users, comparisons, search_logs, bahrain_approved_drugs, comparison_feedback, user_events, user_usage, admin_audit_log, product_specs, product_prices, product_reviews, referral_invites, referral_redemptions.
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

### Deterministic scoring (zero cost)
`scoring_service.py` computes **category-specific scores** from structured data — pure math, no API calls.
- Each of 9 categories has its own 6 dimensions via `CATEGORY_DIMENSIONS`. Old universal keys (`price_score`, `spec_score`) NO LONGER EXIST except in `other`.
- Price tiers: budget(<11 BHD), mid(11-57), premium(57-189), luxury(189+). Cross-tier uses expectations formula; same-tier uses spec/price blend.
- Personalization caps: explicit ±30%, behavioral ±10%, session ±5%.
- Outputs: dimension scores, value badges, tradeoff pairs, confidence indicators, dimension winners.
- Rollback V1 system in `docs/ROLLBACK_SCORING_V1.md`.

### Prompt personalities + trust validation
Each category gets unique GPT verdict tone via `build_personality_prompt(category)` — zero extra cost. `validate_verdict()` cross-checks GPT claims against deterministic scores (returns `winner_aligned`, `claims_flagged`, `confidence_adjustment`).

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

### Personalization (zero extra cost)
4 preference dimensions (collected once after first login): priorities (1-3 of 8 + 6 cohort-derived), budget (budget/mid/premium), lifestyle (0+ of 11 tags), brand attitude. Stored as JSONB in `public.users.preferences` with `_sources` sub-object marking each field `user_stated` or `inferred`. `GET/PUT /api/v1/auth/preferences`.
- **Three-layer system:** Explicit prefs (±30%) → Behavioral profile (±10%, decay-weighted 30-day half-life) → Session signals (±5%) → Category defaults.
- `_build_preferences_prompt()` appends to verdict prompt — zero extra API cost.
- `behavior_service.py`: category affinity, price range, winner agreement, dimension sensitivity. Fire-and-forget update after each comparison.
- `scoring_method`: `category_weighted` (anon), `personalized` (explicit), `behavioral` (behavior/session active), `invitee_quiz` (referral landing).
- `VALID_PRIORITIES`: original 8 + 6 cohort enums (`quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`). `VALID_BRAND_ATTITUDE` adds `trust_known_brands`.

### Cohort personalization (Phase 1 LIVE 2026-05-05)
Survey-driven priors from ~400 Fillout responses bootstrap personalization for new/anonymous users. Feature flag `ENABLE_COHORT_PERSONALIZATION` is **ON in production**; code default remains `false`. Flag is global — no per-user gating yet.
- **PUT /api/v1/auth/demographics** (auth, 5/min) — accepts age_group/gender/governorate/language/country (all optional, "Prefer not to say" → missing). Auto-derives language from Accept-Language and country from CF-IPCountry. Stores `users.demographics_profile` JSONB. Seeds preferences from cohort modal if user has none/all-inferred — never overwrites `user_stated`.
- **GET /api/v1/auth/cohort-profile** (auth) — Profile-card data, or `{display: null}` for low/population matches.
- **PUT /api/v1/auth/preferences** — flips `_sources` to `user_stated` when user edits previously-inferred fields.
- **Privacy invariant:** NO raw age/gender/identity in prompt — only country/language/governorate thin context + aggregate findings. Active when `match_quality ∈ {exact, broadened_governorate, broadened_language}` AND flag on.
- **Cohort match is exact-case** — `_key_part()` doesn't normalize. Valid values must match `cohort_priors.json` keys exactly: `age_group: "25-34"`, `gender: "Male"/"Female"`, `governorate: "Capital"/"Muharraq"/"Northern"/"Southern"`, `language: "English"/"Arabic"/"Both equally"`, `country: "Bahrain"`. Pydantic accepts any string but doesn't validate values.
- Admin metrics: `GET /api/v1/admin/cohort/{metrics,feedback,retention}` + dashboard at `/admin/cohort.html`.
- Re-run `python -m scripts.build_cohorts` to regenerate priors.

### Category selection (soft validation)
9 categories: Electronics, Grocery, Supplements, Makeup, Skincare, Haircare, Fragrances, Fashion, Other. `selected_category` is a hint — backend AI makes final call via `PRODUCT_PARSER_PROMPT`. Mismatch → `category_switched: true` + frontend info banner. Each category has dedicated spec schema in `CATEGORY_SPEC_SCHEMAS` (`extraction_service.py`).

### Sharing + History
22-char URL-safe token (`token_urlsafe(16)`) in `comparisons.share_token` (TEXT post-migration 017 — was VARCHAR(12), causing silent insert failures pre-fix in commit 0b01d9a). Public access strips personalization. History: paginated, searchable, ownership-checked. On 401, clears session + redirects to auth. `create_share_token` raises `ShareTokenError` on persistence failure (loud-fail).

### Qaren UX Redesign (Phase 5 canary LIVE 2026-05-07)
Cal-AI-Lite 17-step onboarding + black/emerald hybrid identity (emerald = signal color reserved for winner reveal, success ticks, cohort accents, the one-time invitee "See how it scores for YOU" CTA — NOT primary CTA). Canary at 10% via `CANARY_NEW_ONBOARDING_PERCENT` const in `SmartCompareApp/src/config/features.ts`; ramp 10→50→100 via EAS Update (NOT a Railway env var). Plan/spec at `docs/plans/2026-05-06-qaren-ux-redesign{,.design}.md`. Session 43 in `CONTEXT_SESSION_LOG.md`.
- **Bucketing:** `featureBucket.ts` djb2 hash on stable id (device-id pre-signup via `expo-secure-store`, user.id post-signup). `hashBucket(id, percent)` is pure — same `(id, percent)` → same boolean every call, every device. Monotonic ramp invariant verified by tests.
- **App.tsx wiring:** `getStableId()` resolves BEFORE state setters that gate onboarding render. After auth: `setStableUserId(authUser.id) + setFlagStableId(authUser.id)` re-bucket on user.id for cross-device consistency.
- **Theme tokens (`SmartCompareApp/src/theme/index.ts`):** `colors.cta.primary = '#0A0A0B'` (black, NOT emerald), `colors.bg.inverse`, `colors.text.onInverse`, `colors.accentGlow`. Typography: `hero` (36/Bold/-0.02em), `display` (28/Bold/-0.01em), `bodyEmphasis` (16/SemiBold), `eyebrow` (11/SemiBold/UPPERCASE/+0.10em). `radii.hero = 24`. Geist font (SIL OFL v1.1, ~125KB/weight, local TTF + expo-font config plugin). `arabicLineHeightMultiplier = 1.7/1.5` consumed by typography hooks for AR readability.
- **Motion (`src/theme/motion.ts`):** screenTransition (320ms cubic-bezier(0.32, 0.72, 0, 1)), springConfig {chip, progress, tab}, variableEasing {fast, slow, snap} for theatrical loading bar. haptic {chip:light, stage:light, winner:medium} — explicitly NO error/warning/heavy intensities (Build Principle #4: never frame the app as scary).
- **17-step onboarding (`src/screens/onboarding/`):** OnboardingFlow orchestrator + 17 step components. Cohort-key types use exact-case strings ('Capital', '25-34', 'Male'/'Female') matching `cohort_priors.json` keys. Step 14 theatrical loading enforces 3.2s minimum even when API faster. Step 16 "Save your advisor" has NO skip link — forced sign-in (verified by negative-assertion test).
- **Hero illustrations (5 total, all hand-coded SVG + Reanimated, ZERO Lottie/JSON):** PhoneMockup #1 (placeholder pending designer Figma; testID contract preserved), CohortBarChart #2 (4 bars + 388-dot grid + spiral-from-center peer cluster), ConcentricMotif #3, LoadingRings #4 (centerpiece for screen 14), RevealBurst #5 (8 lines + Q-badge + check). Bundle impact ~0.
- **Reusable components:** CounterTicker (animated 0→target, safety-floor pattern for jest+on-device parity), StageChecklist (5-row ✓/⟳/○ with haptic on transition INTO done — never on initial mount), ProgressBar with `variableEasing` prop (4-segment fast/slow/fast/snap), StreamingProductCard (stage-gated SSE reveal: init→title→specs→prices→reviews→verdict), LoadingTipsCarousel (5 tips after 8s), CohortBadge (RTL-aware slide direction via prop).
- **Results redesign (`ResultsScreen.tsx`):** "Why we picked this" / "Where the runner-up wins" / "What's next?" section titles per design § 4g (NOT "Verdict" / "Key Differences" / "Compare another"). Specs collapsed by default. CohortBadge inline below verdict.
- **Bonus expiry (Migration 018):** `referral_redemptions.expires_at` (3-day window from issue), `expiry_reminder_sent_at` (idempotency stamp), partial-WHERE index `idx_referral_redemptions_expires_at WHERE consumed_at IS NULL`. `cron_expire_bonuses.py` gated by `ENABLE_BONUS_EXPIRY_PUSHES` (default OFF), 1000-row LIMIT, sends 24h-before push with gift-framing copy. `usage_service.get_user_active_bonus_count()` filters `expires_at > now() AND consumed_at IS NULL` — entitlement is computed from rows, NOT from a stale INT counter (which "stays for analytics/display only and MUST NOT drive entitlement" per code comment).
- **Attribution endpoint (Migration 019):** `POST /api/v1/auth/attribution` (auth, 30/min). Pydantic Literal['friend','instagram','tiktok','app_store','google','other'] + DB CHECK constraint mirror (defense-in-depth).
- **Min-display floor 1.2s** on HomeScreen→Results navigation per design § 3 ("Even cached responses (~200ms) show loading for 1.2s minimum so the brand moment lands"). Pattern at `HomeScreen.tsx` lines 206/267/320.
- **Onboarding analytics (`OnboardingFlow.tsx`):** fires `onboarding_started` on mount, `onboarding_step_completed` on every Continue (BEFORE setStep so payload reflects FINISHED step), `onboarding_completed` on Step 17. Payload `{step_number, step_name, locale, flow_variant}` with stable English slugs and `flow_variant: "new"` locked at mount. Powers Task 47 canary drop-off heatmap. Legacy OnboardingScreen analytics symmetry tracked as Task #60 (frontend-flow follow-up before #48 ramp).
- **Copy contract:** ZERO scary copy in user-facing i18n. Forbidden: "couldn't / try again / unusual / locked / unlock / connection lost / something went wrong / Could not / Failed to / تعذر / فشل / حاول مرة". Approved vocabulary: "Hold on — X. Tap to retry." / "Reconnecting…" / "Sharper match coming up" / "expired or moved" / "are paused right now" / "is on the way" / "Snap that one more time".
- **Test coverage:** frontend 588/588 jest, tsc 0, ≥80% coverage on all redesign-touched files. Backend redesign-owned tests 100% (referral_expiry 7/7, cron_expire_bonuses 8/8, loop2_gift_copy 4/4, attribution 14/14).

### Smart Decision Referrals (Phase 1 LIVE 2026-05-05)
Virality system with dual-loop rewards. 4 endpoints under `/api/v1/referrals/*` gated by `ENABLE_REFERRAL_SYSTEM` (default OFF in code, flipped in Railway).
- **POST /share** (auth, 10/min) — creates `referral_invites` row, grants Loop 1 Deep Review credit (`source='share_loop1'`), returns `share_link` like `qaren.app/c/{token}?ref=QR-XXXXXX`. 3-per-week cap. ShareRequest accepts flat `show_name`/`show_result`/`show_reasons` toggles + nested `privacy={...}` (back-compat); `extra='ignore'` drops `show_budget` (locked OFF per design). Persisted to `referral_invites.privacy` JSONB.
- **GET /status** (auth) — `{referral_code, weekly_invites_used/remaining, monthly_bonus_comparisons, deep_review_credits_available, total_lifetime_redemptions}`. Lazy-creates code on first read.
- **GET /invite/{share_token}?ref={code}** (anon-friendly) — invitee landing. Reads privacy flags, drops winner/recommendation (show_result), verdict/key_differences/tradeoffs (show_reasons), swaps display_name to "A friend" (show_name). Strips preferences/budget/behavior_profile via `_strip_personalization`.
- **POST /invite/{token}/quiz** (anon-friendly) — 4-question rescoring. Returns `personalization.scoring_method = "invitee_quiz"`. Stores NO PII pre-signup.
- **Loop 2 chain:** invite → register-with-`invite_id` → `link_invite_to_user` (fire-and-forget) → first comparison → `try_trigger_loop2` → AbuseDetectionService → on pass: redemption row, +5 (Free) / +10 (Premium) bonus comparisons, invitee credit, Expo Push.
- **Re-engagement** (`ENABLE_REENGAGEMENT_PUSHES`, default OFF): daily cron iterates users with `notifications_enabled` AND `last_comparison_at >= now() - 60d` (1000/run cursor-paginated). Master + per-type sub-toggles in `users.preferences.notification_types`.
- **Admin:** `/admin/referrals/{metrics,viral,cohort_uplift,abuse}` + `/admin/costs/{subscriptions,api,function_map,gauges}` (X-Admin-Key, 30/min). Dashboards at `/admin/referrals.html` + `/admin/costs.html` (Chart.js v4.4.1 + SRI hash, sessionStorage key cache, `escapeHtml` on all inline values).
- **Frontend:** ShareBottomSheet, result-aware Results CTA, ReferralStatusCard, ReferralLandingScreen (deep-link `qaren://` + `https://qaren.app/c/:token`), InviteeQuizScreen (4Q wizard), Notifications card (master + 3 sub-toggles), `pushTokenService.tryRegisterPushToken()` (lazy-import, in-flight coalescing). Loop 1 honesty: if Share intent fails AFTER backend invite created, still fire `onShared` callback — never lie about server state.

### Luxury brand detection
`_is_luxury_brand()` + `COUNTERFEIT_KEYWORDS` filter across ALL categories. Tier 1.5 cascade: official brand → authorized retailers → GCC retailers (9 domains).

### Review + spec quality
Reviews: `_clean_review_content()` strips garbage (min 8 words), fixes sentiment misclassification, then `_clean_review_citations()` replaces `[snippet_N]` with domain attributions. Specs: GPT omits irrelevant fields (not "N/A"). Frontend filters nulls. Scoring applies `CATEGORY_MIN_COVERAGE` penalty.

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN`, `LOG_LEVEL` (default INFO), `CORS_ORIGINS` (comma-separated, defaults to Railway + localhost)
**Price Scraping:** `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN` (timing out on GCC sites), `ENABLE_FIRECRAWL` (default true), `ENABLE_SCRAPEDO` (default true), `ENABLE_PAGE_SCRAPE` (curl_cffi).
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE`.
**Feature Flags:** `ENABLE_COHORT_PERSONALIZATION` (ON in Railway since 2026-05-05), `ENABLE_REFERRAL_SYSTEM`, `ENABLE_HYBRID_MODEL_ROUTING`, `ENABLE_REENGAGEMENT_PUSHES`. All default OFF in code; flip in Railway during canary. `REAL_ACTION_MIN_SECONDS` (default 5) — anti-abuse threshold for Loop 2.

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

## Known Remaining Bugs (deferred)
- **Scrape.do timing out** on GCC luxury retailers (Ounass, Bloomingdales). Firecrawl is primary — Scrape.do is Tier 1.5d fallback only.
- **value_context identical for all products** — `overview.products[i].value_context` reuses the same string. Minor UX issue.
- **Google Sign-In:** Supabase Google provider needs to be enabled in dashboard (client IDs already configured in code).
- **Apple Sign-In:** deferred — requires Apple Developer subscription ($99/year); code is ready.

## Detailed Context
See `docs/CLAUDE_CODE_CONTEXT.md` for the index of all context files. Key files: `CONTEXT_ARCHITECTURE.md` (system design), `CONTEXT_SESSION_LOG.md` (development history), `CONTEXT_REFERENCE.md` (testing/deploy).

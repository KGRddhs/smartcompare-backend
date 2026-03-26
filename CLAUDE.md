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
npx expo start                    # Dev server
npx tsc --noEmit                  # TypeScript check (0 errors as of Mar 8 2026)
```

### Dependencies
- Backend: `pip install -r requirements.txt` (Railway uses this, NOT pyproject.toml)
- Frontend: `npm install` in `SmartCompareApp/`

## Architecture

### Backend (FastAPI + Python 3.12)

**Entry:** `app/main.py` (v2.4.0) — loads env vars, configures middleware stack, registers 10 routers:
- `/api/v1/text/*` — `text_routes.py` → `structured_comparison_service.py` (primary flow + SSE streaming, rate limited)
- `/api/v1/image/*` — `image_routes.py` → GPT-4o-mini vision → auto-compare (rate limited, HEIC detection)
- `/api/v1/url/*` — `url_routes.py` (single URL compare only, multi-compare stub removed)
- `/api/v1/auth/*` — `auth_routes.py` → Supabase Auth (login, register, refresh, profile, email, password, social-login, **account deletion**, resend-verification). Rate limited: login 5/min, register 3/min, delete 1/min.
- `/api/v1/comparisons/*` — `history_routes.py` → comparison history (GET list, GET single, DELETE). Auth required.
- `/api/v1/share/*` — `share_routes.py` → POST create share link (auth), GET public share (no auth, strips personalization)
- `/api/v1/feedback`, `/api/v1/events` — `feedback_routes.py` → feedback collection + event tracking
- `/api/v1/admin/*` — `admin_routes.py` → analytics endpoints + cost dashboard (X-Admin-Key auth)
- `/api/v1/legal/*` — `legal_routes.py` → GET privacy policy + terms of service (no auth, reads markdown files)
- `/api/v1/app/*` — `version_routes.py` → GET version check (min/latest/force_update from env vars, no auth)

**Middleware stack** (outermost → innermost): RequestID → SecurityHeaders → ErrorHandler → CORS → slowapi rate limiter

**Unified error format** (Session 24): All error responses use `{ success: false, error: "message", code: "ERROR_CODE", request_id: "uuid" }`. Codes: `AUTH_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `RATE_LIMITED`, `VALIDATION_ERROR`, `INTERNAL_ERROR`. Frontend `parseApiError()` handles both `.error` (new) and `.detail` (legacy FastAPI) formats.

**Core service:** `app/services/structured_comparison_service.py`
- `StructuredComparisonService` is a **singleton** (`get_comparison_service()`)
- `compare_from_text(query, region, vision_products?, selected_category?, user_id?)` — main entry point
- `compare_from_text_streaming(..., user_id?)` — async generator yielding SSE events (specs→prices→reviews→scores→verdict→complete)
- **Pre-fetch:** Unified web search (1 Serper call) shared by specs + reviews — gated by cache check
- **Phase 1:** specs + price fetched in parallel (specs reuses unified search)
- **Phase 2:** reviews + rating fetched in parallel (reviews reuses unified search, shopping data from Phase 1 feeds ratings)
- **Scoring:** deterministic scoring after Phase 2 via `scoring_service.py` (zero API cost), plus value badges, tradeoff pairs, confidence indicators
- **Behavioral profile:** `_fetch_behavior_profile()` before scoring, `_update_behavior_profile()` fire-and-forget after response assembly
- `_shopping_items_cache` — populated during price search, used by rating/review injection. Cleared per-request.
- **Response format (Session 29):** Top-level keys: `overview`, `specs`, `reviews`, `scoring`, `personalization`, `metadata`. Backward compat aliases preserved (`products`, `comparison`, `winner_index`, `recommendation`, `key_differences`).

**Price pipeline (3 tiers + page scraping + pharmacy JSON-LD):**
1. Serper Shopping API direct extraction (structured prices)
2. GPT-4o-mini extraction from organic search results (with Tier 3 sanity check)
3. GPT training data estimate (marked `estimated: true`)
- **Page scraping** (Session 27): `_fetch_page_price()` → `_curl_fetch_html()` + `_extract_price_from_html()` extracts JSON-LD/OG/microdata from product pages. Used in Tier 1.5 cascade and supplement pipeline.
- **Firecrawl Smart Wait** (Session 32): `firecrawl_service.scrape_page_with_status()` renders SPA pages via Firecrawl `/v1/scrape` API. Used in Tier 1.5a for official brand sites. `source_method: "firecrawl"`.
- **Scrape.do fallback** (Session 32): `scrapedo_service.render_page_with_status()` renders pages with residential proxies. Used in Tier 1.5d only when curl_cffi fetched HTML but found no price (`failed_curl_urls`). `source_method: "scrapedo_rendered"`.
- **API budget + circuit breakers** (Session 32): `api_budget_service.py` tracks credits (Firecrawl 450/lifetime, Scrape.do 900/mo, Serper 2200/lifetime) and circuit breakers (3 failures → 10min cooldown). Fail-open on Redis unavailability.
- **Gate 0 validation**: `_validate_price_query()` rejects garbage queries, `_validate_scrape_url()` rejects search/category pages before burning scrape credits.
- **Feature flag**: `ENABLE_PAGE_SCRAPE` (curl_cffi). Firecrawl/Scrape.do availability checked via `is_available()` (env var + feature flag).
- **Price prompt philosophy (Session 25):** "MOST AUTHORITATIVE" not "LOWEST reasonable". Source priority hierarchy: official brand sites > authorized retailers > major marketplaces. Counterfeit sources filtered (DHgate, AliExpress, Temu, Wish).
- Official domain boost: prices from `OFFICIAL_BRAND_DOMAINS` (25+ domains) sorted first in Shopping results.
- Each price tagged with `source_method`: `local_bhd` (direct BHD price), `converted_usd` (USD→BHD conversion), `page_scrape` (curl_cffi HTML), `page_scrape_rendered` (JS-rendered HTML), or `estimated` (GPT training data). `price_method_mismatch` flag set when products have different source methods.
- Supplements: iHerb direct scrape → Bahrain pharmacy JSON-LD → Serper organic + GPT → Tier 3
- Non-iHerb brands (HealthAid, Vitabiotics): `_fetch_pharmacy_price()` parses JSON-LD from bn.boots.com product pages

**Rating pipeline (4 tiers):**
- Tier 0: Expert review JSON-LD scrape (dead code — never called)
- Tier 1: Serper Shopping, trusted retailers (Amazon, Best Buy, iHerb, Sephora, Ulta, + luxury/fashion retailers)
- Tier 2: Known retailers (Fragrantica, Sally Beauty, LookFantastic, BeautyBay, Nykaa, Bath & Body Works, Boots, + 18 luxury/fashion retailers)
- Tier 3: Marketplace (eBay) if review_count > 1000
- Consensus: 3+ sellers with identical rating → Google product aggregate (verified)
- Fallback: GPT `average_rating` from reviews (unverified, `extract_method: "gpt_review_aggregate"`)
- iHerb ratings extracted during price scrape (data-ga-rating/data-ga-review-count attributes, zero extra API calls)
- Rating display shows all ratings without verified/unverified badges

**URL sourcing for prices and ratings:**
- Primary: Serper Shopping `link` field (Google Shopping product-specific URLs with catalog IDs)
- Fallback: `_build_retailer_url()` generates retailer search page URLs from `RETAILER_SEARCH_URLS` map
- Frontend `openRatingSource()` uses backend `rating_source.url` first, falls back to Google Shopping search

**Supplement-specific behavior:**
- `_is_supplement_query()` detects vitamins/supplements by keyword
- Serper Shopping returns ZERO results for supplements — iHerb direct scrape used instead
- iHerb scrape via `curl_cffi` (bypasses Cloudflare TLS fingerprinting) → brand + word matching
- Non-iHerb brands: `_fetch_pharmacy_price()` → tries pharmacy URLs from Serper → targeted `site:bn.boots.com` search → JSON-LD `Product` schema parsing
- `PHARMACY_DOMAINS` map: `bolo.bh→Bolo`, `bn.boots.com→Boots`, `aldeerahpharmacy.com→Al Deerah Pharmacy`
- Brand matching is space-insensitive: "HealthAid" matches "Health Aid" in JSON-LD
- bolo.bh NOT indexed by Google (Vue.js SPA); bn.boots.com IS indexed with JSON-LD prices

**Bahrain Drug Database (supplement enrichment):**
- `drug_database_service.py` — `find_matching_drugs(query, limit=5)` queries `bahrain_approved_drugs` table via full-text search
- `format_drug_context(drugs)` — formats matches for GPT prompt injection
- Only triggered for `category == "supplements"` — injected into spec extraction prompt as ground truth
- 655 registered health products (vitamins, supplements, OTC drugs) with trade names, ingredients, forms, pack sizes
- Supabase table with `TSVECTOR` column + `GIN` index for fast full-text search
- Supabase `text_search()` API: use `options={"type": "plain", "config": "english"}` (NOT keyword args); `.limit()` must come BEFORE `.text_search()` in chain

**Key services:**
- `extraction_service.py` — GPT prompts, `CATEGORY_SPEC_SCHEMAS` (9 categories), `extract_specs()`, `extract_reviews()`, `generate_comparison(category=...)`. Injects category-specific prompt personality + trust rules into verdict. Structured review_summary (consensus-based) + structured verdict (winner_declaration, winner_reason, key_tradeoff, value_context, best_for).
- `scoring_service.py` — Deterministic scoring engine. **Category-specific 6 dimensions per category** (Session 33): `CATEGORY_DIMENSIONS` maps each category to unique dimension keys (e.g., electronics: performance/value/build_quality/feature/ecosystem/futureproof; fragrances: character/longevity/projection/versatility/wear_value/presentation). `_DIMENSION_SIGNAL_MAP` maps 5 raw signals → category-specific keys. `CATEGORY_DIMENSION_WEIGHTS` (aliased as `CATEGORY_WEIGHTS`), `CATEGORY_PRIORITY_ADJUSTMENTS` (8 priorities × 9 categories), `CATEGORY_BUDGET_ADJUSTMENTS`, `DIMENSION_DISPLAY_NAMES`. Price tier detection, tier-aware value scoring, dimension winners. Personalized weights capped at ±30%. `compute_value_badge()`, `compute_tradeoff_pairs()`, `compute_confidence()`, `apply_behavioral_adjustments()` (±10%), `apply_session_signals()` (±5%). Pure math, $0 cost.
- `prompt_personalities.py` — `CATEGORY_PROMPT_PERSONALITIES` dict (9 categories), `UNIVERSAL_TRUST_RULES`, `build_personality_prompt(category)`. Each category gets a different comparison "language" (electronics=numbers/benchmarks, fragrances=evocative descriptions, makeup=real-world experience).
- `trust_validation_service.py` — `validate_verdict(verdict, scoring_result, category)`. Cross-checks GPT winner alignment and dimension claims against deterministic scores. Zero extra cost.
- `behavior_service.py` — Behavioral learning service (Session 29). Decay-weighted profiles (30-day half-life), category affinity, price range, winner agreement, dimension sensitivity, session signals. `build_behavior_profile()`, `compute_session_signals()`.
- `feedback_service.py` — `save_feedback()`, `track_event()`, `track_events_batch()`. Fire-and-forget pattern (asyncio.create_task).
- `drug_database_service.py` — Bahrain drug database lookup + GPT context formatting (supplements only)
- `serper_service.py` — Serper API calls (`search_product_prices()`, `search_price_organic()`, `search_web()`)
- `cache_service.py` — Upstash Redis caching, monthly budget tracking. **IMPORTANT**: exposes helper functions `_redis_get(key)`, `_redis_set(key, value, ex)`, `_redis_incr(key)`, `_redis_expire(key, seconds)` — there is NO raw Redis client getter. All new code must use these helpers.
- `openai_service.py` — GPT-4o-mini vision for camera identification (`detail: "auto"`, OCR-focused prompt)
- `database_service.py` — Supabase client singleton (`get_supabase_client()`), `delete_user_data_cascade(user_id)` for account deletion
- `sentry_service.py` — `init_sentry()` (opt-in via `SENTRY_DSN` env var)
- `analytics_service.py` — Admin analytics queries (`get_daily_stats()`, `get_popular_queries()`, etc.)
- `api_budget_service.py` — Credit tracking + circuit breakers for Firecrawl, Scrape.do, Serper. Uses cache_service Redis helpers.
- `firecrawl_service.py` — Thin async wrapper around Firecrawl `/v1/scrape` with Smart Wait (5s waitFor, 15s timeout).
- `scrapedo_service.py` — Thin async wrapper around Scrape.do `render=true` API (15s timeout).

**Middleware** (`app/middleware/`):
- `request_id.py` — UUID generation per request, X-Request-ID header
- `security.py` — Security response headers (nosniff, DENY frame, etc.)
- `rate_limiter.py` — slowapi limiter, in-memory storage, 10/min on compare
- `error_handler.py` — Global exception handler, clean 500 JSON, Sentry capture
- `logging_config.py` — Structured JSON logging, one-line per log entry

### Frontend (React Native + Expo)

**Location:** `SmartCompareApp/`

**Screens:**
- `HomeScreen.tsx` — CategorySelector (9 categories), text/camera/URL input tabs, uses SSE streaming (`streamComparison()`). Gear icon navigates to AccountScreen.
- `ResultsScreen.tsx` — Tabs: Overview, Specs, Reviews. Scoring display (ScoreBadge, breakdown bars, winner margin). FeedbackCard below results. Event tracking (tab_switch, source_click, result_view_duration).
- `CameraScreen.tsx` — Camera capture, calls `POST /api/v1/image/identify`
- `HistoryScreen.tsx` — Comparison history from Supabase. Shows "Sign In Required" prompt on 401 (not crash).
- `AccountScreen.tsx` — Account panel: inline name/email editing, password change modal, Google/Apple connect, logout, "My Preferences" link.
- `PreferencesScreen.tsx` — 4-card onboarding (priorities, budget, lifestyle, brand attitude). Shown once after first login, editable from Account.
- `LoginScreen.tsx` — Email login + Google/Apple sign-in buttons + inline field validation.
- `RegisterScreen.tsx` — Email register + Google/Apple sign-in buttons + inline field validation.

**Components:**
- `CategorySelector.tsx` — Horizontal scrolling chip selector for 9 product categories (Electronics, Grocery, Supplements, Makeup, Skincare, Haircare, Fragrances, Fashion, Other)
- `FeedbackCard.tsx` — Thumbs up/down + mattered-most chips + optional text. Fire-and-forget submit, collapses after submission.

**Services:**
- `api.ts` — Axios instance pointing to Railway production URL (120s timeout). SSE streaming via `streamComparison()` (fetch+ReadableStream, fallback to non-streaming). `submitFeedback()`, `trackEvents()`. JPEG transcoding via `expo-image-manipulator` before image upload.
- `authService.ts` — Login/register/refresh with Supabase. `signInWithGoogle()` and `signInWithApple()` for social login. Stores access_token + refresh_token in AsyncStorage. `verifyAuth()` returns `User | null` (NOT boolean).

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls intelligently.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have.
- **Supabase** — PostgreSQL (users, comparisons, products, prices, specs, reviews, search_logs, bahrain_approved_drugs, comparison_feedback, user_events) + Auth. Cache strategically.
- **Upstash Redis** — Response caching (prices 24h, specs/reviews 7d)

## Important Patterns

### Fact-checking (zero-cost cross-validation)
Every product in the API response has a `fact_check` object with `overall_confidence` (high/medium/low). Built from:
- **Spec citations**: GPT must cite `snippet_N` or `"training"` for each spec field. Citations verified against actual search snippet text. Cross-validated against Serper Shopping titles.
- **Review sentiment**: GPT `average_rating` cross-checked against weighted Serper `source_ratings` average. Flagged if deviation > 0.8.
- **Price verification**: Final price compared against Serper Shopping median. Flagged if deviation > 30%.
- Zero additional API calls — all verification uses data already fetched.

### Ratings are NEVER AI-generated
Ratings come from real Serper Shopping data or GPT review aggregation (marked unverified). The GPT extraction prompt explicitly forbids generating `source_ratings`.

### `product.price` is an object, not a number
Backend returns `{ amount, currency, retailer, url, estimated }`. Frontend code must access `product.price.amount`, not `product.price` directly.

### GCC_REGIONS keys (extraction_service.py)
Keys are: `bahrain`, `saudi_arabia`, `uae`, `kuwait`, `qatar`, `oman`. Note: it's `saudi_arabia` NOT `saudi`.

### Singleton service state
`StructuredComparisonService` is a singleton. `total_cost`, `api_calls`, and `_shopping_items_cache` are reset at the start of each `compare_from_text()` call. Any new per-request state must also be reset there.

### Cost budget
Target: **$0.009-0.01/comparison** (current: ~$0.010 electronics, ~$0.010 supplements). Achieved via unified search merging (one Serper call shared by specs + reviews). Pharmacy JSON-LD adds +$0.001 only when targeted search triggers (non-iHerb brands). Track with `self.total_cost` and `self._track_cost()`.

### Unified search optimization
`_fetch_product_data()` does ONE web search pre-fetch (gated by cache check) and passes results to both `_get_specs(search_results=...)` and `_get_reviews(search_results=...)`. Each function skips its own Serper call when pre-fetched results are provided. This saves $0.001/product ($0.002/comparison).

### Cache bypass
`?nocache=true` query param bypasses Redis cache. Useful for testing after schema changes. Stale cache (7-day TTL for specs/reviews) can serve outdated formats.

### Vision products bypass query parsing
Camera input passes `vision_products` directly to `compare_from_text()`, skipping `parse_product_query()`. The `size_or_count` field (e.g., "360 Softgels") is appended to the product name in `image_routes.py` before comparison.

### Deterministic scoring (zero cost, Session 26 → 33 overhaul)
`scoring_service.py` computes **category-specific scores** from structured data. No API calls — pure math.
- **Category-specific dimensions (Session 33)**: Each of 9 categories has its own 6 scoring dimensions. `CATEGORY_DIMENSIONS` defines keys (e.g., electronics: `performance_score`, `value_score`, `build_quality_score`, `feature_score`, `ecosystem_score`, `futureproof_score`). Old universal keys (`price_score`, `spec_score`, etc.) NO LONGER EXIST except in "other" category.
- **Signal mapping**: `_DIMENSION_SIGNAL_MAP` maps 5 raw signals (spec, price, review, reliability, popularity) to category-specific dimension keys. `_compute_raw_scores()` extracts signals, `_normalize_scores()` maps to category dimensions.
- **Category weights**: `CATEGORY_DIMENSION_WEIGHTS` (aliased as `CATEGORY_WEIGHTS`) — per-category weight profiles summing to 1.0. `CATEGORY_PRIORITY_ADJUSTMENTS` (8 priorities × 9 categories), `CATEGORY_BUDGET_ADJUSTMENTS` (budget/mid/premium × 9 categories).
- **Price tiers**: `PRICE_TIERS` — budget(<11 BHD), mid(11-57), premium(57-189), luxury(189+). Cross-tier detection via `_is_cross_tier()`.
- **Tier-aware value score**: Cross-tier uses `50 + (delivery - expected) * 0.8` formula. Same-tier uses `spec*0.6 + price*0.4` blend.
- **Dimension winners**: `compute_dimension_winners(result, names, category)` — per-dimension comparison, tie threshold=3.0.
- **Coverage penalty**: `CATEGORY_MIN_COVERAGE` thresholds per category (electronics=0.5, fashion=0.3).
- **Personalization**: `MAX_WEIGHT_SHIFT_RATIO = 0.30`, `MAX_BEHAVIORAL_SHIFT_RATIO = 0.10`, `MAX_SESSION_SHIFT_RATIO = 0.05`.
- **Value badges**: `compute_value_badge()` → great_value/fair_price/premium_price/overpriced.
- **Tradeoff pairs**: `compute_tradeoff_pairs()` — margin>5%, max 3, sorted by combined impact.
- **Confidence indicators**: `compute_confidence()` — price/rating/specs/overall (high/medium/low).
- **Enriched verdict prompt**: `build_scores_summary()` injects tier info, dimension leaders (using `DIMENSION_DISPLAY_NAMES`), category weights.
- **Rollback**: V1 universal 6-dimension system preserved in `docs/ROLLBACK_SCORING_V1.md`.

### Prompt personalities + trust validation (Session 33)
- Each category gets a different comparison "language" via `prompt_personalities.py`
- Electronics: quantifiable benchmarks. Makeup: real-world experience. Fragrances: evocative descriptions. Supplements: clinical evidence + Bahrain registration.
- `build_personality_prompt(category)` injects into verdict prompt — zero extra cost
- `trust_validation_service.py`: `validate_verdict()` cross-checks GPT claims against deterministic scores post-generation
- Returns: `winner_aligned`, `claims_validated`, `claims_softened`, `claims_flagged`, `confidence_adjustment`

### Account deletion + auth hardening (Session 33)
- `DELETE /api/v1/auth/account` — cascade deletes user_events, comparison_feedback, comparisons, search_logs, clears preferences/behavior_profile, deletes auth user. Rate limited 1/min.
- Password strength: 10+ chars, 1 uppercase, 1 lowercase, 1 digit. Applied to register + change password.
- `POST /api/v1/auth/resend-verification` — rate limited 3/min.

### SSE streaming
`GET /api/v1/text/compare/stream` returns Server-Sent Events. 10 events: status(parsing) → status(fetching) → specs → prices → status(reviews) → reviews → scores → status(verdict) → verdict → complete. Status events include `progress` field (10/20/50/80). Frontend uses fetch+ReadableStream (not EventSource) with fallback to non-streaming. Non-streaming endpoint unchanged.

### Feedback and event tracking
`POST /api/v1/feedback` (useful bool, mattered_most[], change_suggestion) + `POST /api/v1/events` (batch event tracking). Both auth-optional, fire-and-forget. FeedbackCard shown in ResultsScreen Overview tab. Events tracked: tab_switch, source_click, result_view_duration. Tables: `comparison_feedback` + `user_events` with RLS.

### Personalization (zero extra cost)
The frontend collects 4 preference dimensions once after first login (PreferencesScreen with 4 swipeable cards — all mandatory, no skip):
- **Priorities** (1-3 of 8: price, quality, brand_reputation, durability, latest_features, ease_of_use, eco_friendly, health_safety)
- **Budget** (budget/mid/premium)
- **Lifestyle** (0+ of 11 tags)
- **Brand attitude** (brand_loyal/function_first/best_of_both)

Stored as JSONB in `public.users.preferences` column. `preferences_completed` boolean controls onboarding flow.
- `GET/PUT /api/v1/auth/preferences` — read/write preferences (auth required)
- Login/register/social responses include `preferences_completed`
- `_build_preferences_prompt()` in extraction_service.py appends to verdict prompt
- Response includes `personalized: true/false` + `personalization_factors` list
- Zero extra API cost — preferences ride on existing GPT prompt tokens
- **Three-layer personalization (Session 29):** Explicit preferences (±30% cap) → Behavioral profile (±10% cap) → Session signals (±5% cap) → Category defaults
- `behavior_profile` JSONB column on `public.users` — decay-weighted (30-day half-life), updated fire-and-forget after each comparison
- `behavior_service.py`: category affinity, price range, winner agreement, dimension sensitivity
- `scoring_method`: "category_weighted" (anon), "personalized" (explicit prefs), "behavioral" (behavior/session active)

### Category selection (soft validation)
The frontend provides 9 category options: Electronics, Grocery, Supplements, Makeup, Skincare, Haircare, Fragrances, Fashion, Other. The `selected_category` parameter is passed to `/api/v1/text/compare` as a hint, but the backend AI always makes the final category decision via `PRODUCT_PARSER_PROMPT`. Product-type binding (Session 25): the parser prompt maps product types to categories (e.g., "shoes" -> fashion, "perfume" -> fragrances). If a mismatch is detected (`selected_category != detected_category`), the response includes `category_switched: true` and the frontend shows an info banner. Each category has a dedicated spec schema in `CATEGORY_SPEC_SCHEMAS` (extraction_service.py) — fashion has 10 fields, "other" schema cleaned of electronics fields. Zero extra API cost -- category detection happens within the existing product parser call.

### Sharing (Session 24)
`POST /api/v1/share/{comparison_id}` creates an 8-char URL-safe token (`secrets.token_urlsafe(6)`) stored in `comparisons.share_token`. `GET /api/v1/share/{token}` returns the comparison data publicly (strips personalization fields). Frontend `shareComparison()` in api.ts gets the share link, falls back to text-only OS sharing if no comparison_id or API fails.

### History (Session 24)
`GET /api/v1/comparisons/history` (auth required, paginated, searchable), `GET /api/v1/comparisons/{id}` (full response), `DELETE /api/v1/comparisons/{id}` (ownership check). Frontend HistoryScreen passes stored blob directly to ResultsScreen. On 401, calls `clearSession()` + `onLogout()` to redirect to auth flow.

### Luxury brand detection (Session 25 → 26)
Category-independent multi-layer defense against counterfeit pricing:
- `LUXURY_BRAND_KEYWORDS` (30+ brands): Chanel, Gucci, Louis Vuitton, Hermes, Prada, etc.
- `OFFICIAL_BRAND_DOMAINS` (25+ domains): chanel.com, gucci.com, louisvuitton.com, etc.
- `_is_luxury_brand(product_name)` checks product name against keyword list
- **Counterfeit filter** (Session 26): `COUNTERFEIT_KEYWORDS` (20 terms), `_is_counterfeit_listing()` — first filter in shopping extraction and title match
- **Official domain search** (Session 26): `_get_official_domain()` + Tier 1.5 `site:domain.com` Serper search when Tier 1 Shopping fails (+$0.001)
- **Sanity thresholds** (Session 26): official domain (retailer_score>=1.0) bypasses sanity check; luxury uses 1.8x/0.6x thresholds
- Works across ALL categories (fragrances, fashion, makeup, etc.), not just fashion
- **Page scraping** (Session 27): `_fetch_page_price()` with `_curl_fetch_html()` + `_extract_price_from_html()` for JSON-LD/OG/microdata extraction
- **Firecrawl + Scrape.do** (Session 32): Replaced Cloudflare/Microlink. Firecrawl Tier 1.5a (official sites), Scrape.do Tier 1.5d (failed curl URLs only). Circuit breakers + budget tracking via `api_budget_service.py`.
- **Expanded GCC retailers** (Session 32): `GCC_LUXURY_RETAILERS` now 9 domains: ounass, namshi, bloomingdales, level-shoes, harveynichols, galerieslafayette, theluxurycloset, boutique1.
- **Timeouts**: `PAGE_SCRAPE_TIMEOUT=5` (curl_cffi), `FIRECRAWL_TIMEOUT=15`, `SCRAPEDO_TIMEOUT=15`.

### Review quality (Session 25 → 26)
- `_clean_review_citations()` replaces `[snippet_N]` with "Per domain.com:" attributions
- **Review post-processing** (Session 26): `_clean_review_content()` strips garbage text (`GARBAGE_PATTERNS`), enforces min 8 words, removes sentiment misclassification (positive-only in complaints). Called BEFORE `_clean_review_citations()`.
- Review prompt hardened with CONTENT QUALITY rules, BAD/GOOD examples, sentiment alignment

### Smart spec field handling (Session 25 → 26)
Spec extraction prompt instructs GPT to omit irrelevant fields instead of forcing "N/A". Frontend `SpecsTab` filters out N/A/null/empty values and `_source` metadata fields. Scoring applies N/A penalty with `CATEGORY_MIN_COVERAGE` thresholds (electronics=0.5, fashion=0.3, etc.).

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN` (enables error tracking), `LOG_LEVEL` (default: INFO)
**Price Scraping:** `FIRECRAWL_API_KEY` (firecrawl.dev, 500 lifetime free), `SCRAPEDO_API_TOKEN` (scrape.do, 1000/mo free), `ENABLE_FIRECRAWL` (default true), `ENABLE_SCRAPEDO` (default true). Without these, scraping gracefully skips.
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE` (all optional, used by `/api/v1/app/version`)

### Serper API Credits
- **Rotated Feb 28 2026**: Fresh 2,500 credits (~625-833 nocache comparisons)
- Each comparison uses ~3-4 Serper calls (shopping + web search + occasional pharmacy search)
- Cached responses (default) cost zero Serper calls — only `nocache=true` burns credits
- **To rotate**: Create new Serper account at serper.dev (free tier = 2,500 credits), update `SERPER_API_KEY` in Railway env vars. No code changes needed — the key is stateless.

## Tests

- `python -m py_compile <file>` for syntax checks
- `curl` against Railway production (`?nocache=true` for fresh data)
- `npx tsc --noEmit` for frontend type checking

**Test coverage expectations:**
- New features: 80%+ coverage, test-driven development (red-green-refactor)
- No regressions: All existing tests must pass before merging
- Test types: Unit tests (free), live_unit tests (~$0.03), integration tests (Railway ~$0.06)

### Run commands
```bash
# All free unit tests (~1418 tests, ~10s, $0)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Include live unit tests (iHerb, Serper, GPT vision — ~$0.03)
python -m pytest tests/ -v -m "not (live_db or integration)"

# Live database tests (needs Supabase credentials in .env)
python -m pytest tests/test_drug_database_service.py -v -m live_db

# Integration tests only (live Railway — ~$0.06, ~4 min)
python -m pytest tests/test_integration.py -v -m integration

# Full suite
python -m pytest tests/ -v --timeout=180
```

**Note:** `tests/conftest.py` auto-loads `.env` via `python-dotenv` so all tests pick up Supabase credentials.

### Test files (~1418 unit, ~63 files; plus 14 live_unit + 6 live_db + 10 integration)
- `tests/test_auth_interceptor.py` — 93 tests: auth endpoints, token verify, optional/required user, profile, password, social login, MIME detection edge cases
- `tests/test_fact_checking.py` — 48 tests: spec citation verification, shopping cross-validation, review sentiment, price verification, fact_check assembly
- `tests/test_error_paths.py` — 31 tests: currency conversion, freshness, price parsing, supplement detection, title/number matching
- `tests/test_analytics.py` — 30 tests: analytics service queries, admin endpoint auth + all 5 routes
- `tests/test_spec_verification_strict.py` — 27 tests: strict numeric matching, cross-validation, training/no-source handling
- `tests/test_camera_vision.py` — 26 tests: vision pipeline, JSON cleanup, size_or_count enrichment, HEIC detection, MIME validation, endpoint rejection
- `tests/test_observability.py` — 24 tests: Sentry init, structured JSON formatter, configure_logging, error handler middleware
- `tests/test_review_prompt_quality.py` — 73 tests: review + verdict prompt structure, citations, examples, completeness, garbage rejection, sentiment alignment, review_summary format, structured verdict, normalize edge cases, preferences prompt
- `tests/test_url_quality.py` — 18 tests: retailer URL generation, null for unknowns, Serper link extraction
- `tests/test_security_middleware.py` — 16 tests: request ID generation/preservation, security headers, rate limiting (under/over/429)
- `tests/test_rating_tiers.py` — 16 tests: tier classification, consensus logic, accessory filtering
- `tests/test_price_fallback.py` — 12 tests: shopping extraction, currency conversion, all-tiers-fail
- `tests/test_pharmacy_jsonld.py` — 12 tests: pharmacy JSON-LD price extraction
- `tests/test_drug_database_service.py` — 11 tests: drug DB (5 unit + 6 `live_db`)
- `tests/test_history.py` — 10 tests: save_comparison, get history, delete, search, product name extraction
- `tests/test_db_improvements.py` — 9 tests: log_search, upsert_product, error handling
- `tests/test_url_extraction.py` — 8 tests: URL extraction (price + rating link logic)
- `tests/test_iherb_scraping.py` — 7 tests: word normalization, live iHerb scraping, brand filtering
- `tests/test_unified_search.py` — 4 tests: search sharing (specs/reviews), cost budget tracking
- `tests/test_category_selection.py` — 46 tests: schema validation, prompt building, API params, category switching, parser prompt, live GPT extraction
- `tests/test_personalization.py` — 52 tests: preference validation, GET/PUT endpoints, service functions, auth response flag, prompt injection, comparison metadata, valid options
- `tests/test_scoring_service.py` — 122 tests: category-specific dimension weights, price tiers, value score, dimension winners, coverage thresholds, personalization, determinism, value badges, tradeoff pairs, confidence indicators, behavioral weight adjustments
- `tests/test_feedback.py` — 29 tests: feedback submission, event tracking, validation, batch, fire-and-forget
- `tests/test_streaming.py` — 26 tests: SSE format, event sequence, generator, endpoint, error handling, new response structure, progress events
- `tests/test_behavior_service.py` — 30 tests: decay weight, category affinity, price range, winner agreement, dimension sensitivity, session signals, full profile
- `tests/test_behavior_integration.py` — 13 tests: scoring param acceptance, weight adjustments, profile fetch/update, route integration
- `tests/test_singleton_state.py` — 3 tests: singleton pattern, cache leak prevention, state reset
- `tests/test_iherb_rating.py` — 5 tests: iHerb rating extraction from HTML attributes, cache injection
- `tests/test_price_source.py` — 10 tests: source_method tagging, price_method_mismatch flag
- `tests/test_history_routes.py` — 15 tests: history list, single, delete, pagination, ownership, auth
- `tests/test_share_routes.py` — 12 tests: create share link, public access, ownership, collision retry
- `tests/test_error_middleware.py` — 10 tests: unified error format, HTTP/validation/rate-limit exceptions
- `tests/test_fashion_category.py` — 12 tests: fashion schema validation, category detection, spec fields
- `tests/test_luxury_brands.py` — 23 tests: luxury brand detection, official domain matching, counterfeit filtering, counterfeit listing detection, official domain lookup
- `tests/test_price_priority.py` — 11 tests: authoritative price sorting, official domain boost, source priority hierarchy, title match rejection
- `tests/test_citation_cleanup.py` — 13 tests: snippet reference replacement, domain attribution, edge cases
- `tests/test_review_cleanup.py` — 19 tests: garbage pattern filtering, sentiment misclassification, derived ratings, edge cases
- `tests/test_js_rendering.py` — 14 tests: Firecrawl/Scrape.do architecture verification, dead code removal assertions (Session 32 rewrite)
- `tests/test_page_scraping.py` — 15 tests: _fetch_page_price curl_cffi only, _got_html signal, JSON-LD/OG/microdata extraction (Session 32 update)
- `tests/test_luxury_price_tiers.py` — tests for Tier 1.5 cascade, authorized/GCC retailers, expanded domains (Session 32 update)
- `tests/test_api_budget_service.py` — 51 tests: credit tracking, circuit breaker states, Redis fail-open, budget keys, usage summary
- `tests/test_firecrawl_service.py` — 28 tests: scrape_page, scrape_page_with_status, is_available, error handling, boundary cases
- `tests/test_scrapedo_service.py` — 25 tests: render_page, render_page_with_status, is_available, error handling
- `tests/test_cascade_hardening.py` — 29 tests: Gate 0, Firecrawl gating, circuit breaker classification, Scrape.do Tier 1.5d, dead code
- `tests/test_input_validation.py` — 30 tests: _validate_price_query boundaries, _validate_scrape_url patterns
- `tests/test_cost_dashboard.py` — 8 tests: /api/v1/admin/costs endpoint auth, response format
- `tests/test_category_dimensions.py` — 28 tests: CATEGORY_DIMENSIONS config, weights, priority adjustments, display names, backward compat aliases
- `tests/test_scoring_edge_cases.py` — 25 tests: all-category scoring, empty specs, null prices, extreme personalization, behavioral edges
- `tests/test_prompt_personalities.py` — 12 tests: all 9 categories have personalities, required keys, trust rules, category-specific content
- `tests/test_trust_validation.py` — 11 tests: winner alignment, misalignment, dimension claims, confidence adjustment
- `tests/test_trust_edge_cases.py` — 9 tests: None values, empty scoring, single product, all tied, unknown category
- `tests/test_personality_edge_cases.py` — 9 tests: empty/None/mixed-case category, token budget, uniqueness
- `tests/test_account_deletion.py` — 21 tests: deletion auth, cascade, password strength, resend verification
- `tests/test_legal_routes.py` — 7 tests: privacy/terms endpoints, no auth required, content validation
- `tests/test_version_routes.py` — 7 tests: version endpoint, env var reading, defaults
- `tests/test_integration.py` — 10 tests: live Railway (~$0.10, ~5 min)

## Known Remaining Bugs (deferred)

These are known issues that have been intentionally deferred:
- **Luxury prices pending validation** (Session 32): Firecrawl + Scrape.do implemented but not yet tested with real API keys. Phase 0 validation spike needed: sign up at firecrawl.dev + scrape.do, add keys to .env, test 3 luxury URLs. Then add keys to Railway and deploy.
- **value_context identical for all products** (Session 29): `overview.products[i].value_context` uses same string from comparison dict for all products. Minor UX issue — GPT generates one value context, not per-product.
- Google Sign-In: Supabase Google provider needs to be enabled in dashboard (client IDs configured in code)
- Apple Sign-In: deferred — requires Apple Developer subscription ($99/year); code is ready

## Detailed Context
See `docs/CLAUDE_CODE_CONTEXT.md` for the index of all context files. Key files: CONTEXT_ARCHITECTURE.md (system design), CONTEXT_SESSION_LOG.md (development history), CONTEXT_REFERENCE.md (testing/deploy).

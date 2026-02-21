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
- Ratings with confidence indicators (verified vs unverified) — never hide data
- Real prices with retailer attribution
- Honest recommendations based on data, not guesses

## Workflow Rules

1. Read `docs/CLAUDE_CODE_CONTEXT.md` before major changes — learn from what worked and what didn't
2. Think before calling — is this API call necessary?
3. Quality first, then optimize
4. Show confidence, not false certainty
5. Plan → Approve → Implement → Test

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
curl https://smartcompare-backend-production.up.railway.app/health
curl "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"

# Deploy: push to main, Railway auto-deploys in ~90s
git push origin main
```

### Frontend (React Native / Expo)
```bash
cd SmartCompareApp
npx expo start                    # Dev server
npx tsc --noEmit                  # TypeScript check (7 pre-existing errors as of Feb 18 2026)
```

### Dependencies
- Backend: `pip install -r requirements.txt` (Railway uses this, NOT pyproject.toml)
- Frontend: `npm install` in `SmartCompareApp/`

## Architecture

### Backend (FastAPI + Python 3.12)

**Entry:** `app/main.py` — loads env vars, registers 5 routers:
- `/api/v1/text/*` — `text_routes.py` → `structured_comparison_service.py` (primary flow)
- `/api/v1/image/*` — `image_routes.py` → GPT-4o-mini vision → auto-compare
- `/api/v1/url/*` — `url_routes.py` (partially implemented)
- `/api/v1/auth/*` — `auth_routes.py` → Supabase Auth
- `/api/v1/*` — `routes.py` (legacy image comparison, has broken function calls)

**Core service:** `app/services/structured_comparison_service.py`
- `StructuredComparisonService` is a **singleton** (`get_comparison_service()`)
- `compare_from_text(query, region, vision_products?)` — main entry point
- **Pre-fetch:** Unified web search (1 Serper call) shared by specs + reviews — gated by cache check
- **Phase 1:** specs + price fetched in parallel (specs reuses unified search)
- **Phase 2:** reviews + rating fetched in parallel (reviews reuses unified search, shopping data from Phase 1 feeds ratings)
- `_shopping_items_cache` — populated during price search, used by rating/review injection. Cleared per-request.

**Price pipeline (3 tiers + pharmacy JSON-LD):**
1. Serper Shopping API direct extraction (structured prices)
2. GPT-4o-mini extraction from organic search results (with Tier 3 sanity check)
3. GPT training data estimate (marked `estimated: true`)
- Supplements: iHerb direct scrape → Bahrain pharmacy JSON-LD → Serper organic + GPT → Tier 3
- Non-iHerb brands (HealthAid, Vitabiotics): `_fetch_pharmacy_price()` parses JSON-LD from bn.boots.com product pages

**Rating pipeline (4 tiers):**
- Tier 0: Expert review JSON-LD scrape (dead code — never called)
- Tier 1: Serper Shopping, trusted retailers (Amazon, Best Buy)
- Tier 2: Known retailers
- Tier 3: Marketplace (eBay) if review_count > 1000
- Consensus: 3+ sellers with identical rating → Google product aggregate (verified)
- Fallback: GPT `average_rating` from reviews (unverified, `extract_method: "gpt_review_aggregate"`)

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
- `extraction_service.py` — GPT prompts, `CATEGORY_SPEC_SCHEMAS` (electronics/grocery/supplements/other), `extract_specs()`, `extract_reviews()`, `generate_comparison()`
- `drug_database_service.py` — Bahrain drug database lookup + GPT context formatting (supplements only)
- `serper_service.py` — Serper API calls (`search_product_prices()`, `search_price_organic()`, `search_web()`)
- `cache_service.py` — Upstash Redis caching, monthly budget tracking
- `openai_service.py` — GPT-4o-mini vision for camera identification (`detail: "auto"`, OCR-focused prompt)
- `database_service.py` — Supabase client singleton (`get_supabase_client()`)

### Frontend (React Native + Expo)

**Location:** `SmartCompareApp/`

**Screens:**
- `HomeScreen.tsx` — Text input, calls `GET /api/v1/text/compare`
- `ResultsScreen.tsx` — Tabs: Overview, Specs, Reviews. Has local type definitions that diverge from `src/types/types.ts`.
- `CameraScreen.tsx` — Camera capture, calls `POST /api/v1/image/identify`
- `HistoryScreen.tsx` — Comparison history from Supabase

**Services:**
- `api.ts` — Axios instance pointing to Railway production URL (120s timeout)
- `authService.ts` — Login/register/refresh with Supabase. Stores access_token + refresh_token in AsyncStorage. `verifyAuth()` returns `User | null` (NOT boolean).

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls intelligently.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have.
- **Supabase** — PostgreSQL (products, prices, specs, reviews, search_logs, bahrain_approved_drugs) + Auth. Cache strategically.
- **Upstash Redis** — Response caching (prices 24h, specs/reviews 7d)

## Important Patterns

### Ratings are NEVER AI-generated
Ratings come from real Serper Shopping data or GPT review aggregation (marked unverified). The GPT extraction prompt explicitly forbids generating `source_ratings`.

### `product.price` is an object, not a number
Backend returns `{ amount, currency, retailer, url, estimated }`. Frontend code must access `product.price.amount`, not `product.price` directly.

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

## Environment Variables (Railway)
`OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`

## Tests

- `python -m py_compile <file>` for syntax checks
- `curl` against Railway production (`?nocache=true` for fresh data)
- `npx tsc --noEmit` for frontend type checking
- `python -m pytest tests/test_url_extraction.py -v` — 8 tests for URL extraction (price + rating link logic)
- `python -m pytest tests/test_pharmacy_jsonld.py -v` — 12 tests for pharmacy JSON-LD price extraction
- `python -m pytest tests/test_drug_database_service.py -v -m "not live_db"` — 5 unit tests for drug DB (6 live_db tests auto-skip without Supabase access)
- `python -m pytest tests/test_integration.py -v -m integration` — 6 integration tests against live Railway (~$0.06, ~4 min)

## Known Remaining Bugs (deferred)

These are known issues that have been intentionally deferred:
- Legacy `/api/v1/compare` route (`routes.py`): all function calls use wrong arg counts — 4 TypeErrors
- No axios auth interceptor — token never sent on API requests
- Missing `expo-camera`/`expo-image-picker` plugins in `app.json` (breaks EAS builds)
- `ResultsScreen.tsx` has local type definitions that diverge from `src/types/types.ts`
- `.gitignore` corrupted with PowerShell heredoc wrapper text
- `pyproject.toml` diverged from `requirements.txt` (openai v1 vs v2)
- Dead code: `_get_pros_cons()`, `_get_expert_review()` (Tier 0 — defined but never called)

## Detailed Context
See `docs/CLAUDE_CODE_CONTEXT.md` for full session history, all decisions made, and known issues. **Read this before major changes** — learn from what worked and what didn't.

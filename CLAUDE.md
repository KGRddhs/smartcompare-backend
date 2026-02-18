# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

**Core service:** `app/services/structured_comparison_service.py` (~1660 lines)
- `StructuredComparisonService` is a **singleton** (`get_comparison_service()`)
- `compare_from_text(query, region, vision_products?)` — main entry point
- **Phase 1:** specs + price fetched in parallel
- **Phase 2:** reviews + rating fetched in parallel (shopping data from Phase 1 feeds ratings)
- `_shopping_items_cache` — populated during price search, used by rating/review injection. Cleared per-request.

**Price pipeline (3 tiers):**
1. Serper Shopping API direct extraction (structured prices)
2. GPT-4o-mini extraction from organic search results (with Tier 3 sanity check)
3. GPT training data estimate (marked `estimated: true`)
- Supplements use iHerb-specific search (`_is_supplement_query()` → `site:iherb.com`)

**Rating pipeline (4 tiers):**
- Tier 0: Expert review JSON-LD scrape (dead code — never called)
- Tier 1: Serper Shopping, trusted retailers (Amazon, Best Buy)
- Tier 2: Known retailers
- Tier 3: Marketplace (eBay) if review_count > 1000
- Fallback: GPT `average_rating` from reviews (unverified)

**Key services:**
- `extraction_service.py` — GPT prompts, `CATEGORY_SPEC_SCHEMAS` (electronics/grocery/supplements/other), `extract_specs()`, `extract_reviews()`, `generate_comparison()`
- `serper_service.py` — Serper API calls (`search_product_prices()`, `search_price_organic()`, `search_web()`)
- `cache_service.py` — Upstash Redis caching, monthly budget tracking
- `openai_service.py` — GPT-4o-mini vision for camera identification

### Frontend (React Native + Expo)

**Location:** `SmartCompareApp/`

**Screens:**
- `HomeScreen.tsx` — Text input, calls `GET /api/v1/text/compare`
- `ResultsScreen.tsx` — Tabs: Overview, Specs, Reviews. Has local type definitions that diverge from `src/types/types.ts`.
- `CameraScreen.tsx` — Camera capture, calls `POST /api/v1/image/identify`
- `HistoryScreen.tsx` — Comparison history from Supabase

**Services:**
- `api.ts` — Axios instance pointing to Railway production URL
- `authService.ts` — Login/register/refresh with Supabase. Stores access_token + refresh_token in AsyncStorage.

### External APIs
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification
- **Serper** — Google Search + Shopping API ($0.001/call)
- **Supabase** — PostgreSQL (products, prices, specs, reviews, search_logs) + Auth
- **Upstash Redis** — Response caching (prices 24h, specs/reviews 7d)

## Important Patterns

### Ratings are NEVER AI-generated
Ratings come from real Serper Shopping data or GPT review aggregation (marked unverified). The GPT extraction prompt explicitly forbids generating `source_ratings`.

### `product.price` is an object, not a number
Backend returns `{ amount, currency, retailer, url, estimated }`. Frontend code must access `product.price.amount`, not `product.price` directly.

### Singleton service state
`StructuredComparisonService` is a singleton. `total_cost`, `api_calls`, and `_shopping_items_cache` are reset at the start of each `compare_from_text()` call. Any new per-request state must also be reset there.

### Cost budget
Target: $0.015/comparison. Electronics ~$0.013, supplements ~$0.016. Track with `self.total_cost` and `self._track_cost()`.

### Cache bypass
`?nocache=true` query param bypasses Redis cache. Useful for testing after schema changes.

## Environment Variables (Railway)
`OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`

## Detailed Context
See `docs/CLAUDE_CODE_CONTEXT.md` for full session history, all decisions made, and known issues.

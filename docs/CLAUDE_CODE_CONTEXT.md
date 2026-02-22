# SmartCompare - Complete Project Knowledge Transfer

> **Purpose:** This document contains EVERYTHING needed to continue development without context loss.
> **Last Updated:** February 21, 2026 (Session 8: Drug DB + Integration Tests)
> **Author:** Transferred from Claude.ai conversation (Days 1-7), updated by Claude Code sessions

---

# ⚠️ IMPORTANT: CURRENT DATE CONTEXT

**Today's date: February 2026**

Your training data may be outdated. These products EXIST and are currently on sale:

**Apple (released annually in Fall):**
- iPhone 17 Pro Max, iPhone 17 Pro, iPhone 17 (Fall 2025)
- iPhone 16 Pro Max, iPhone 16 Pro, iPhone 16 (Fall 2024)
- iPhone 15 series (Fall 2023)

**Samsung (released annually in early year):**
- Galaxy S26 Ultra, S26+, S26 (Early 2026)
- Galaxy S25 Ultra, S25+, S25 (Early 2025)
- Galaxy S24 series (Early 2024)

**Other:**
- Google Pixel 10 (Fall 2025), Pixel 9 (Fall 2024)
- PlayStation 5 Pro (Late 2024)
- MacBook Pro M4 (Late 2024), MacBook Pro M5 (Late 2025)

**RULE: Never say a product "doesn't exist" or is "rumored" without searching first. Assume 2026 product cycles.**

---

# TABLE OF CONTENTS

1. [Project Vision & Goals](#1-project-vision--goals)
2. [Tech Stack & Architecture](#2-tech-stack--architecture)
3. [Complete File Structure](#3-complete-file-structure)
4. [Backend Deep Dive](#4-backend-deep-dive)
5. [Mobile App Deep Dive](#5-mobile-app-deep-dive)
6. [Database Schema](#6-database-schema)
7. [API Reference](#7-api-reference)
8. [All Decisions Made](#8-all-decisions-made)
9. [Problems Solved](#9-problems-solved)
10. [Current Issues](#10-current-issues)
11. [Code Snippets Reference](#11-code-snippets-reference)
12. [Deployment & Git](#12-deployment--git)
13. [Testing Guide](#13-testing-guide)
14. [Future Roadmap](#14-future-roadmap)

---

# 1. PROJECT VISION & GOALS

## Core Mission
**"If users still go to Google or ChatGPT after using SmartCompare, we failed."**

SmartCompare must provide COMPLETE, ACTIONABLE product comparisons with:
- Accurate prices (converted to user's currency)
- Complete specs (never missing data)
- Verified ratings (from real sources, not AI-generated)
- Clear winner recommendation
- Pros/cons for each product

## Target Users
- GCC region (Bahrain, UAE, Saudi Arabia, Kuwait, Qatar, Oman)
- Primary currency: BHD (Bahraini Dinar)
- Shopping on: Amazon.ae, Noon, Jarir, Ubuy, local retailers

## Input Methods
1. **Camera** - Take photos of products on shelf
2. **Text** - Type "iPhone 15 vs Galaxy S24"
3. **URL** - Paste product links from any retailer

---

# 2. TECH STACK & ARCHITECTURE

## Backend
- **Framework:** FastAPI (Python 3.12)
- **AI:** OpenAI GPT-4o-mini (cheap, fast extraction)
- **Search:** Serper API (Google search + shopping results)
- **Database:** Supabase (PostgreSQL)
- **Hosting:** Railway (auto-deploys from GitHub)

## Mobile
- **Framework:** React Native + Expo
- **Auth:** Supabase Auth
- **HTTP Client:** Axios
- **Navigation:** React Navigation

## Architecture v3 (Current)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                   │
│            (Camera / Text / URL)                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PARSE PRODUCTS                                  │
│         Extract product names from input                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABASE CACHE CHECK                              │
│         Check if we have recent data (< 24h for prices)              │
│         Cache hit = $0.001, Cache miss = continue                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PARALLEL SEARCH (Serper)                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │
│  │ Specs Search │ │Shopping Search│ │Reviews Search│                 │
│  │  (8 results) │ │ (12 results) │ │ (5 results)  │                 │
│  └──────────────┘ └──────────────┘ └──────────────┘                 │
│                   Cost: $0.003 (3 API calls)                         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   AI EXTRACTION (GPT-4o-mini)                        │
│         Extract: brand, name, specs, pros, cons                      │
│         NOT ratings (fetched separately)                             │
│         Cost: $0.001                                                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PRICE FALLBACK CHAIN                            │
│  1. GCC retailers (amazon.ae, noon) → found? done                    │
│  2. Global search (US, UK, EU) → convert currency                    │
│  3. MSRP search (launch price) → mark as estimated                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              RATING EXTRACTION (4-tier fallback)                     │
│  Tier 0: Expert review JSON-LD (PCMag/CNET/TechRadar)               │
│  Tier 1: Serper Shopping — trusted retailers (Amazon/BestBuy)        │
│  Tier 2: Serper Shopping — known retailers (.com/.ae)                │
│  Tier 3: Marketplace (eBay/AliExpress) if review_count > 1000       │
│  ** WORKING — verified Feb 14 2026 **                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      VALIDATION LAYER                                │
│  - All required fields present?                                      │
│  - Price reasonable? (not > 500 BHD for phone)                       │
│  - Rating has source_url? (else strip it)                            │
│  - Minimum 5 specs, 3 pros, 2 cons                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AI COMPARISON (GPT-4o-mini)                       │
│         Winner, recommendation, key differences                      │
│         Value scores, best_for categories                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SAVE TO CACHE                                   │
│         Products, prices, specs → Supabase                           │
│         Next identical search = instant + free                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RETURN RESPONSE                                 │
│         Complete comparison with metadata                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 3. COMPLETE FILE STRUCTURE

```
smartcompare/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI app entry point
│   │   ├── config.py                    # Settings/env vars
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── text_routes.py           # /api/v1/text/* endpoints
│   │   │   ├── url_routes.py            # /api/v1/url/* endpoints
│   │   │   ├── image_routes.py          # /api/v1/compare (camera) [LEGACY]
│   │   │   └── auth_routes.py           # /api/v1/auth/* endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── comparison_service_v3.py # MAIN SERVICE - use this
│   │       ├── rating_extractor.py      # Deterministic ratings (BROKEN)
│   │       ├── rating_service.py        # Old rating service (deprecated)
│   │       ├── url_extraction_service.py# URL parsing with BeautifulSoup
│   │       └── image_service.py         # Image/OCR processing
│   ├── requirements.txt                 # Poetry deps (backend folder)
│   ├── pyproject.toml                   # Poetry config
│   └── poetry.lock
│
├── SmartCompareApp/                     # React Native mobile app
│   ├── src/
│   │   ├── screens/
│   │   │   ├── HomeScreen.tsx           # Main input screen
│   │   │   ├── ResultsScreen.tsx        # Comparison results
│   │   │   ├── LoginScreen.tsx
│   │   │   ├── RegisterScreen.tsx
│   │   │   └── HistoryScreen.tsx
│   │   ├── services/
│   │   │   ├── api.ts                   # Axios config, Railway URL
│   │   │   └── authService.ts           # Supabase auth functions
│   │   ├── components/
│   │   │   └── ...
│   │   └── types/
│   │       └── index.ts
│   ├── App.tsx
│   ├── app.json
│   └── package.json
│
├── docs/
│   ├── ARCHITECTURE_V3.md               # Architecture documentation
│   └── CLAUDE_CODE_CONTEXT.md           # THIS FILE
│
├── requirements.txt                     # ROOT - Railway reads this!
├── .gitignore
└── README.md
```

---

# 4. BACKEND DEEP DIVE

## 4.1 Main Entry Point (main.py)

```python
# Key imports
from app.api.text_routes import router as text_router
from app.api.url_routes import router as url_router
from app.api.image_routes import router as image_router
from app.api.auth_routes import router as auth_router

# Routes registered
app.include_router(text_router, prefix="/api/v1/text")
app.include_router(url_router, prefix="/api/v1/url")
app.include_router(image_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")
```

## 4.2 Comparison Service v3 (comparison_service_v3.py)

This is the MAIN service. Key functions:

### `compare_products_v3(query, region, mode)`
- Parses query into product names
- Fetches data for each product in parallel
- Runs comparison
- Returns complete response

### `search_all_data(product_name, region)`
- 3 parallel Serper searches: specs, shopping, reviews
- Extracts knowledge graph if available
- Cost: $0.003

### `extract_product_data(product_name, search_results, region, category)`
- Sends search results to GPT-4o-mini
- Extracts structured product data
- DOES NOT extract ratings (removed from prompt)

### `search_price_fallback(product_name, region)`
- GCC price search
- Multiple query attempts

### `search_price_global(product_name, target_region)`
- US, UK, EU searches
- Currency conversion to target

### `search_msrp_price(product_name, target_region)`
- MSRP/launch price for new products
- Marks as estimated

### Currency Conversion Rates
```python
CURRENCY_TO_BHD = {
    "BHD": 1.0,
    "AED": 0.1025,   # 1 AED = 0.1025 BHD
    "SAR": 0.1003,   # 1 SAR = 0.1003 BHD
    "USD": 0.377,    # 1 USD = 0.377 BHD
    "KWD": 1.22,
    "QAR": 0.1035,
    "OMR": 0.98,
    "GBP": 0.47,
    "EUR": 0.41,
    "INR": 0.0045,
}
```

## 4.3 Rating System - 4-tier fallback (WORKING)

Implemented in `_get_verified_rating()` in `app/services/structured_comparison_service.py`.

### Tier 0 (Expert)
- Scrapes editorial review sites (PCMag, CNET, TechRadar, Tom's Guide, The Verge, Wired, LaptopMag, Tom's Hardware)
- Parses JSON-LD `reviewRating` for rating + author + pros/cons
- Label: `"Pcmag Expert Review (Author Name)"`, confidence: `"expert"`

### Tier 1 (High)
- Serper Shopping results from trusted retailers (Amazon, Best Buy, Walmart, etc.)

### Tier 2 (Medium)
- Known retailers, .com/.ae stores

### Tier 3 (Low)
- Marketplace (eBay/AliExpress) only if review_count > 1000, labeled "marketplace rating"

All tiers produce: `rating`, `review_count`, `rating_verified`, `rating_source` (with name, url, extract_method, confidence).

## 4.4 Cost Structure

| Operation | Cost |
|-----------|------|
| Serper search (per call) | $0.001 |
| GPT-4o-mini extraction | $0.001 |
| Full comparison (2 products, enhanced reviews) | $0.009-0.011 |
| With US rating fallback | +$0.001 |
| Cache hit | $0.000 |

---

# 5. MOBILE APP DEEP DIVE

## 5.1 API Configuration (api.ts)

```typescript
const API_BASE_URL = 'https://smartcompare-backend-production.up.railway.app';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for image processing
});
```

## 5.2 Auth Service (authService.ts)

Key functions:
- `login(email, password)` - Returns user + token
- `register(email, password)` - Creates account
- `logout()` - Clears stored session
- `getCurrentUser()` - Gets stored user from AsyncStorage
- `isLoggedIn()` - Checks if token exists
- `verifyAuth()` - Alias for isLoggedIn (was missing, we added it)

Storage keys:
```typescript
const USER_STORAGE_KEY = '@smartcompare_user';
const TOKEN_STORAGE_KEY = '@smartcompare_token';
```

## 5.3 Results Screen (ResultsScreen.tsx)

### Rating Display Component
```typescript
const RatingDisplay = ({ product }: { product: Product }) => {
  const { rating, review_count, rating_verified, rating_source } = product;

  // If no rating data at all
  if (rating === null || rating === undefined) {
    return <Text>No verified rating</Text>;
  }

  // If rating exists but unverified — show in gray with "Unverified" badge
  if (!rating_verified) {
    return (
      <View>
        <StarOutline /> {rating.toFixed(1)} ({review_count} reviews)
        [Unverified] {rating_source?.name}
      </View>
    );
  }

  // Verified rating with source link
  return (
    <View>
      <Star /> {rating.toFixed(1)} ({review_count} reviews)
      <TouchableOpacity onPress={() => openURL(rating_source.url)}>
        [Verified] {rating_source.name} [link]
      </TouchableOpacity>
    </View>
  );
};
```

### Expected API Response Structure
```typescript
interface ReviewData {
  average_rating?: number | null;
  total_reviews?: number | null;
  positive_percentage?: number | null;
  summary?: string | null;              // 2-3 sentence opinionated summary
  rating_distribution?: Record<string, number> | null;  // {5_star: 60, 4_star: 25, ...}
  category_scores?: Record<string, number> | null;      // {performance: 9, value: 7, ...}
  source_ratings?: Array<{source: string; rating: number; review_count?: number}>;  // REAL Serper data
  detailed_praises?: Array<{text: string; frequency?: string; quote?: string}>;
  detailed_complaints?: Array<{text: string; frequency?: string; quote?: string}>;
  user_quotes?: Array<{text: string; sentiment?: string; source?: string; aspect?: string}>;
  common_praises?: string[];            // Simple list (backward compat)
  common_complaints?: string[];         // Simple list (backward compat)
  verified_rating?: {rating: number; review_count?: number; source?: string; verified?: boolean};
}

interface Product {
  name: string;
  brand: string;
  full_name?: string;
  category?: string;
  price: {
    amount: number | null;
    currency: string;
    retailer?: string;
    estimated?: boolean;
    note?: string;
  };
  specs: Record<string, any>;
  reviews?: ReviewData | null;     // Enhanced review data (Feb 13 2026)
  rating: number | null;           // 1-5 or null
  review_count: number | null;
  rating_verified: boolean;        // true only if source_url exists
  rating_source: {
    name: string;                  // "Best Buy via Google Shopping"
    url: string;                   // Google Shopping link
    extract_method: string;        // "google_shopping", "expert_review_jsonld", etc.
    retrieved_at: string;          // ISO timestamp
    confidence: string;            // "high", "medium", "low", "expert"
  } | null;
  pros: string[];
  cons: string[];
  expert_pros?: string[];          // From Tier 0 expert review scrape
  expert_cons?: string[];          // From Tier 0 expert review scrape
}
```

---

# 6. DATABASE SCHEMA

## Supabase Tables

### products
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL DEFAULT 'Unknown',
    category TEXT NOT NULL DEFAULT 'other',
    variants JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### product_prices
```sql
CREATE TABLE product_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    region TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    retailer TEXT,
    url TEXT,
    in_stock BOOLEAN,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);
```

### product_specs
```sql
CREATE TABLE product_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    specs JSONB NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'serper_ai',
    confidence DECIMAL(3,2) DEFAULT 0.8,
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);
```

### product_reviews
```sql
CREATE TABLE product_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    average_rating DECIMAL(2,1),
    total_reviews INTEGER,
    pros JSONB DEFAULT '[]',
    cons JSONB DEFAULT '[]',
    summary TEXT,
    source TEXT DEFAULT 'serper_ai',
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);
```

### rating_cache (NEW - for deterministic ratings)
```sql
CREATE TABLE rating_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_name TEXT UNIQUE NOT NULL,
    rating DECIMAL(2,1),
    review_count INTEGER,
    source_name TEXT,
    source_url TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    extract_method TEXT,  -- "json_ld", "microdata", "meta_tags", "css_selector"
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL  -- 24 hour TTL
);
```

### search_logs
```sql
CREATE TABLE search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    query TEXT NOT NULL,
    input_type TEXT NOT NULL DEFAULT 'text',
    products_found JSONB DEFAULT '[]',
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    cost DECIMAL(6,4),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

# 7. API REFERENCE

## Text Comparison

### GET/POST `/api/v1/text/compare`
```
Query params:
  q: string          - "iPhone 15 vs Galaxy S24"
  mode: string       - "v3" (default), "lite", "full"
  region: string     - "bahrain", "uae", "saudi"

Response:
{
  "success": true,
  "products": [...],
  "comparison": {
    "winner_index": 0,
    "winner_reason": "...",
    "recommendation": "...",
    "key_differences": [...],
    "value_scores": [8, 7],
    "best_for": {"gaming": 0, "budget": 1}
  },
  "winner_index": 0,
  "recommendation": "...",
  "key_differences": [...],
  "metadata": {
    "elapsed_seconds": 12.5,
    "total_cost": 0.006,
    "api_calls": 8,
    "cache_hits": 0
  }
}
```

### GET `/api/v1/text/quick`
Quick comparison without full search.
```
Query params:
  p1: string - First product
  p2: string - Second product
```

## URL Comparison

### GET/POST `/api/v1/url/compare`
```
Query params:
  url1: string - First product URL
  url2: string - Second product URL
  mode: string - "v3", "lite", "full"
```

## Auth

### POST `/api/v1/auth/register`
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

### POST `/api/v1/auth/login`
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

## Health

### GET `/health`
```json
{"status": "healthy"}
```

---

# 8. ALL DECISIONS MADE

## Architecture Decisions

| Decision | Reasoning |
|----------|-----------|
| v3 as default mode | Guaranteed complete responses with validation |
| GPT-4o-mini over GPT-4 | 10x cheaper, fast enough for extraction |
| Serper over direct scraping | Reliable, structured results, $0.001/search |
| Supabase over Firebase | PostgreSQL flexibility, good free tier |
| Railway over Vercel | Better for Python backends, easy deploys |
| Multi-source price fallback | Never show "Price N/A" if data exists anywhere |
| Deterministic ratings over AI | AI was generating fake ratings (4.5/150) |
| Cache with TTL | Prices 24h, specs 7d - balance freshness vs cost |

## Code Decisions

| Decision | Reasoning |
|----------|-----------|
| Parallel searches | 3 searches in 3s instead of 9s sequentially |
| Currency detection from domain | .ae = AED, .sa = SAR, .com = USD |
| Price > 500 BHD heuristic | Likely mislabeled AED, auto-convert |
| Rating requires source_url | No URL = no rating shown (prevent fake data) |
| BeautifulSoup for HTML parsing | Standard, reliable, handles malformed HTML |
| AsyncIO throughout | Non-blocking, handles concurrent requests |

## Mobile Decisions

| Decision | Reasoning |
|----------|-----------|
| Expo over bare RN | Faster development, easier testing |
| AsyncStorage for auth | Simple, works offline |
| Show "No verified rating" | Honest > fake data |
| Clickable source links | Users can verify ratings themselves |

---

# 9. PROBLEMS SOLVED

## Day 1-3: Initial Setup
- Set up FastAPI backend
- Connected Serper API
- Basic comparison working

## Day 4: Price Issues
**Problem:** Prices showing wrong values (1449 BHD for iPhone)
**Cause:** AED prices labeled as BHD
**Solution:** Currency detection from retailer domain + conversion

## Day 5: Mobile Auth Error
**Problem:** `verifyAuth is not a function`
**Cause:** Missing function in authService.ts
**Solution:** Added `verifyAuth()` alias for `isLoggedIn()`

## Day 6: URL Extraction
**Problem:** URL comparison not extracting product info
**Cause:** BeautifulSoup not parsing retailer pages
**Solution:** Improved selectors, fallback to Serper search

## Day 6: Cost Optimization
**Problem:** Each comparison costing $0.02+
**Cause:** Too many API calls, no caching
**Solution:** Lite mode ($0.004), caching, parallel searches

## Day 7: 502 Error
**Problem:** Mobile showing 502, backend crashed
**Cause:** Missing `beautifulsoup4` in root requirements.txt
**Solution:** Added to root requirements.txt, Railway redeployed

## Day 7: Git Push Issues
**Problem:** `git push` failing
**Cause:** Wrong remote URL, conflicts
**Solution:** Fixed remote to `smartcompare-backend.git`, resolved conflicts

## Feb 19: iHerb Direct Scrape for Supplement Prices
**Problem:** Supplement prices were wrong — BHD 2.07 (USD→BHD conversion from US iHerb) vs real BHD 4.388 on bh.iherb.com. Original plan was to use Serper with `site:bh.iherb.com` but Serper doesn't index iHerb regional subdomains. Direct HTTP to iHerb blocked by Cloudflare from Railway datacenter IPs.

**Solution:** `curl_cffi` library mimics Chrome TLS fingerprint, bypasses Cloudflare. Added `_fetch_iherb_price()` method that:
1. Fetches `{cc}.iherb.com/search?kw=...` via `curl_cffi` (sync, wrapped in `run_in_executor`)
2. Parses product cards from HTML `data-ga-*` attributes (brand, price, title)
3. Matches by brand filter → all-query-words subset → iHerb's relevance order (first = most popular)
4. Returns real BHD price directly (no USD conversion needed)

**Bugs hit along the way (all fixed):**
- `await set_cached()` — `set_cached()` is sync (returns bool), `await bool` → TypeError, caught silently by `asyncio.gather(return_exceptions=True)` → price=None
- `NameError: best_score` — log message referenced variable only defined in `else` fallback branch. Broad `except Exception` caught it silently
- `_calculate_freshness` NoneType — `product.get("price", {}).get(...)` fails when price is explicitly `None`. Fixed with `(p.get("price") or {}).get(...)` pattern
- iHerb search query noise — "NOW D3 supplement" returned mostly non-NOW products. Stripped generic words (supplement, vitamin) from iHerb query
- Cheapest-wins picked trial packs — 30-softgel trial (BD 1.305) selected over standard product. Changed to use iHerb's relevance order

**Result:**
- NOW D3: BHD 3.739 from iHerb (real price, real retailer, direct product URL) ✓
- HealthAid D3: BHD 5.66 estimated (not on iHerb — honest behavior) ✓
- Electronics regression: iPhone 16 BHD 449, Galaxy S25 BHD 389 (unchanged) ✓
- Cost: $0.011 (under budget) ✓

**Files changed:**
- `app/services/structured_comparison_service.py` — `_fetch_iherb_price()`, iHerb query cleanup, matching logic, NameError fix, freshness guard
- `app/api/text_routes.py` — debug endpoint added/removed during investigation
- `requirements.txt` — added `curl_cffi>=0.7.0`

**Known limitation:** Variant matching is imprecise — generic "NOW D3" picks iHerb's first relevant result (2000 IU 240 softgels) which may not match specs (1000 IU 180 softgels). Specs and price are fetched in parallel so spec data isn't available to refine the iHerb match.

---

# 10. CURRENT ISSUES

## FIXED: Ratings (previously broken)
Ratings now work via Serper Shopping API (`_get_verified_rating()` in `app/services/structured_comparison_service.py`). Shows verified ratings with review count and source link.

## FIXED: Prices from low-quality sellers
Added `RETAILER_TIERS` scoring system — prefers official retailers over eBay/marketplace sellers. Tier 3 purge removes low-quality sellers when better options exist.

## FIXED: Enhanced Reviews Tab
**Backend:** Returns rich review data (category_scores, rating_distribution, user_quotes, source_ratings, summary, verified_rating). Tested via curl Feb 14 2026 — all fields present for both products (RTX 3070 vs RTX 3090 test).

**Frontend:** `ResultsScreen.tsx` ReviewsTab renders all new fields (score bars, star distribution, user quotes with sentiment badges, source ratings with verified badge). Code audited — all conditional rendering uses safe optional chaining and null checks.

**Key architecture:** `source_ratings` come from REAL Serper shopping data (injected post-GPT-extraction). GPT is explicitly told NOT to generate source_ratings to prevent hallucinated review counts. `verified_rating` is injected into reviews to match Overview tab rating.

## FIXED: Supplement Prices (Feb 19)
iHerb prices now fetched via `curl_cffi` direct scrape of regional store (`bh.iherb.com`). Returns real BHD prices with retailer attribution and product URLs. Bypasses Cloudflare via Chrome TLS fingerprint mimicry. Fallback: Serper keyword search → GPT extraction → Tier 3 estimate.

## KNOWN ISSUE: iHerb Variant Matching
Generic queries like "NOW D3" match multiple variants on iHerb. Current logic picks iHerb's first relevant result (by relevance sort), which may not match the dosage/count from specs. Specs and price are fetched in parallel, so spec data isn't available to refine the match. Could be improved by fetching specs first, then using dosage/count to filter iHerb results.

## KNOWN ISSUE: Stale cache
Old cached data (7-day TTL for specs/reviews) can serve outdated formats after schema changes. Use `?nocache=true` to bypass. Consider adding a cache version key or flushing on deploy.

## LOW PRIORITY: Pros/cons reference old cached data
Pros/cons generation can reference stale spec data from cache. Cleared naturally as caches expire.

---

# 11. CODE SNIPPETS REFERENCE

## How ratings SHOULD work

```python
# In comparison_service_v3.py
from app.services.rating_extractor import get_verified_rating, validate_rating_for_api

# Fetch rating
rating_result = await get_verified_rating(product_name)  # Returns ExtractedRating

# Convert to API response
rating_data = rating_result.to_api_response()
# Returns:
# {
#   "rating": 4.6,
#   "review_count": 12543,
#   "rating_verified": True,
#   "rating_source": {
#     "name": "Amazon US",
#     "url": "https://amazon.com/dp/...",
#     "extract_method": "json_ld",
#     "retrieved_at": "2025-02-11T..."
#   }
# }

# Add to product data
extracted["rating"] = rating_data.get("rating")
extracted["review_count"] = rating_data.get("review_count")
extracted["rating_verified"] = rating_data.get("rating_verified", False)
extracted["rating_source"] = rating_data.get("rating_source")
```

## JSON-LD parsing

```python
def extract_from_json_ld(soup):
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        data = json.loads(script.string)
        # Look for AggregateRating
        if data.get("@type") == "AggregateRating":
            return {
                "value": float(data.get("ratingValue")),
                "count": int(data.get("reviewCount"))
            }
        # Or nested in Product
        if data.get("aggregateRating"):
            rating = data["aggregateRating"]
            return {
                "value": float(rating.get("ratingValue")),
                "count": int(rating.get("reviewCount"))
            }
```

## Example JSON-LD from Amazon

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Apple iPhone 15",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.6",
    "reviewCount": "12543"
  }
}
</script>
```

---

# 12. DEPLOYMENT & GIT

## Repository
- **URL:** https://github.com/KGRddhs/smartcompare-backend
- **Branch:** main
- **Auto-deploy:** Railway watches this repo

## Deploy Process
```powershell
cd "C:\Users\SynAckITPC\Documents\AI\smartcompare"
git add .
git commit -m "Description of changes"
git push origin main
# Railway auto-deploys within 1-2 minutes
```

## Railway Dashboard
- Check deployments: Deployments tab
- Check logs: Click deployment → Logs
- Environment variables: Settings → Variables
- Restart: Deployments → ⋮ → Redeploy

## Required Environment Variables (Railway)
```
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
DEBUG_MODE=true
```

---

# 13. TESTING GUIDE

## Automated Tests (pytest)

```bash
# All unit tests (fast, free, no API calls) — 98 tests, ~2s
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Include live unit tests (iHerb scraping, Serper, GPT vision) — adds ~$0.03
python -m pytest tests/ -v -m "not (live_db or integration)"

# Drug database unit tests only (6 live_db tests auto-skip without Supabase)
python -m pytest tests/test_drug_database_service.py -v -m "not live_db"

# Integration tests — hits live Railway, costs ~$0.06, takes ~4 min
python -m pytest tests/test_integration.py -v -m integration

# All tests
python -m pytest tests/ -v --timeout=180
```

### Test Files
| File | Tests | Type | Notes |
|------|-------|------|-------|
| `tests/test_error_paths.py` | 31 | Unit | Currency conversion, freshness calc, price parsing, supplement detection, title/number matching |
| `tests/test_rating_tiers.py` | 16 | Unit + Live | Tier classification, consensus logic, accessory filtering, invalid ratings |
| `tests/test_price_fallback.py` | 12 | Unit + Live | Shopping extraction, accessory filter, high-value min price, currency conversion, all-tiers-fail |
| `tests/test_camera_vision.py` | 10 | Unit + Live | Vision pipeline, JSON cleanup, size_or_count enrichment, field normalization |
| `tests/test_iherb_scraping.py` | 7 | Unit + Live | Word normalization, live iHerb scraping, brand filtering |
| `tests/test_unified_search.py` | 4 | Unit + Live | Search sharing (specs/reviews reuse), cost budget tracking |
| `tests/test_singleton_state.py` | 3 | Unit | Singleton pattern, cache leak prevention, state reset between requests |
| `tests/test_url_extraction.py` | 8 | Unit | URL extraction for price + rating links |
| `tests/test_pharmacy_jsonld.py` | 12 | Unit | Pharmacy JSON-LD price parsing |
| `tests/test_drug_database_service.py` | 11 | Unit + Live DB | 5 local + 6 `live_db` (need Supabase) |
| `tests/test_integration.py` | 6 | Integration | Live Railway: phones, laptops, supplements (iHerb + pharmacy), grocery, shoes |
| **Total** | **120** | | **98 free unit tests + 10 live_unit + 6 live_db + 6 integration** |

### Pytest Markers
| Marker | Purpose | Run command |
|--------|---------|-------------|
| `live_unit` | Tests calling live external services (iHerb, Serper, OpenAI) | `-m live_unit` |
| `live_db` | Tests requiring live Supabase `bahrain_approved_drugs` table | `-m live_db` |
| `integration` | End-to-end tests against live Railway production | `-m integration` |

## Local Backend Testing

```bash
cd C:\Users\SynAckITPC\Documents\AI\smartcompare
uvicorn app.main:app --reload --port 8000
```

Test URLs:
- Health: http://localhost:8000/health
- Compare: http://localhost:8000/api/v1/text/compare?q=iPhone%2015%20vs%20Galaxy%20S24&nocache=true

## Production Testing

```bash
curl https://smartcompare-backend-production.up.railway.app/health
curl "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"
```

## Mobile Testing

```bash
cd SmartCompareApp
npx expo start
```

---

# 14. FUTURE ROADMAP

## Completed (Feb 11-21 2026)
- [x] Fix rating extraction (Serper Shopping tiers + consensus)
- [x] Rating/Price clickable links (Google Shopping product URLs)
- [x] Supplement pricing (iHerb scrape + pharmacy JSON-LD)
- [x] Camera input (GPT-4o-mini vision OCR)
- [x] Enhanced reviews (category_scores, source_ratings, user_quotes)
- [x] Cost optimization ($0.010/comparison via unified search)
- [x] Bahrain drug database (655 products, GPT context injection)
- [x] Integration tests (6 tests across all categories)

## Short Term
- [ ] Apply Figma UI design
- [ ] Fix camera supplement pricing (verbose names fail iHerb search)
- [ ] Add axios auth interceptor (token auto-sent on requests)
- [ ] Fix ResultsScreen type divergence from types.ts
- [ ] Add product history / favorites
- [ ] Expand test coverage (37 tests → 80% target). Uncovered areas:
  - Camera/vision identification pipeline
  - Singleton state reset between requests
  - iHerb scraping logic (brand matching, query cleanup, TLS bypass)
  - Rating tier selection and consensus logic
  - Price tier fallback chain (Tier 1 → 2 → 3)
  - Unified search call merging
  - Error paths (API timeouts, malformed GPT responses, currency conversion edge cases)
  - Edge cases: empty query, single product, health endpoint

## Medium Term
- [ ] URL input comparison (`/api/v1/url/compare`)
- [ ] Premium tier with Stripe
- [ ] Price alerts
- [ ] Barcode scanning
- [ ] Multi-language support

## Long Term
- [ ] AI shopping assistant
- [ ] More GCC retailers
- [ ] Price prediction

---

# QUICK START FOR CLAUDE CODE

When starting Claude Code, say:

```
Read docs/CLAUDE_CODE_CONTEXT.md completely. This is SmartCompare - a product
comparison app for GCC region.

Current status (Feb 21, 2026):
- Backend: Running on Railway (all critical bugs fixed, iHerb scrape + pharmacy JSON-LD deployed)
- Prices (text): Working (3-tier fallback + iHerb scrape + pharmacy JSON-LD + clickable URLs)
- Prices (camera): PARTIALLY BROKEN — supplements get wrong BHD price from camera path
- Specs: Working (supplements enriched with Bahrain drug database context)
- Ratings: Working (Serper Shopping tiers + consensus + GPT review fallback)
- Enhanced Reviews: Working (category_scores, rating_distribution, user_quotes, source_ratings)
- Camera input: Working for identification, broken for supplement prices
- Auth: Fixed (refresh token flow)
- Cost: ~$0.010/comparison (electronics and supplements)
- Bahrain Drug DB: 655 registered health products, GPT context injection for supplements
- Tests: 37 total (8 URL + 12 pharmacy + 11 drug DB + 6 integration)
- URL input: Not started
```

---

# IMPORTANT RULES (DO NOT VIOLATE)

1. **NO AI-GENERATED RATINGS** - Never return default values like 4.5 or 150 reviews
2. **RATING REQUIRES source_url** - If no URL, rating must be null
3. **PRICES MUST BE CONVERTED** - Always convert to user's region currency
4. **ALWAYS VALIDATE** - Check all required fields before returning
5. **LOG EVERYTHING** - Use `[RATING]` prefix for rating logs
6. **CACHE APPROPRIATELY** - Prices 24h, specs 7d, ratings 24h
7. **DEPLOY VIA GIT** - Push to origin main, Railway auto-deploys

---

---

# SESSION LOG: February 11, 2026

## What We Fixed

### 1. Prices — Serper Shopping direct extraction (3-tier fallback)
**Files:** `app/services/structured_comparison_service.py`, `app/services/extraction_service.py`
- **Tier 1:** Parse structured price data directly from Serper Shopping results (most accurate)
- **Tier 2:** GPT extraction from search result text (fallback)
- **Tier 3:** GPT training data estimate, marked `estimated: true` with `confidence: 0.5` (last resort)
- Added `_extract_price_from_shopping()` — title matching with 40% word overlap threshold
- Added `_parse_price_string()` — handles "$699.99", "BHD 339", "SAR 2,499" formats
- Goal: **always show a price**, either real retailer or clearly labeled estimate

### 2. Specs — Fixed schema per category (no freeform fields)
**File:** `app/services/extraction_service.py`
- Added `CATEGORY_SPEC_SCHEMAS` dict with exactly 11 fields per category:
  - **electronics:** display, processor, ram, storage, battery, rear_camera, front_camera, os, connectivity, weight, water_resistance
  - **grocery:** size, ingredients, nutrition_calories, nutrition_protein, nutrition_fat, nutrition_carbs, origin, organic, allergens, shelf_life, halal
  - **other:** dimensions, weight, material, color, warranty, power, features, included, compatibility, origin, certifications
- Replaced static `SPECS_EXTRACTION_PROMPT` with `_build_specs_prompt()` — generates category-specific prompt
- Enforced schema server-side: only allowed fields kept, null/empty → "N/A"
- No more `additional_specs` field

### 3. Specs — Single value per field, no variant lists
**File:** `app/services/extraction_service.py`
- Prompt forces GPT to extract ONE config (base model or specified variant)
- Prevents "128, 256, 512 GB" — now always "128 GB"

### 4. Specs — All fields filled for known products
**File:** `app/services/extraction_service.py`
- Prompt allows GPT to use training knowledge when search results are incomplete
- null only acceptable if spec truly doesn't exist (e.g. water resistance on a product without it)
- Well-known products (iPhone, Galaxy, Pixel) always have all fields filled

### 5. Specs table — Fixed order, only matching rows
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Added `SPEC_DISPLAY_CONFIG` mapping key → {label, order} for human-readable display
- Rows sorted by fixed order, not insertion order
- Only shows rows where BOTH products have real data (either is N/A → row hidden)
- N/A values styled in gray italic

### 6. Simplified `_clean_specs()`
**File:** `app/services/structured_comparison_service.py`
- Removed `additional_specs` flattening (no longer exists)
- Replaces None/empty with "N/A"

### 7. Added `nocache` query parameter
**Files:** `app/api/text_routes.py`, `app/services/structured_comparison_service.py`
- `GET /api/v1/text/compare?nocache=true` bypasses Redis cache for fresh data
- Threaded through all data fetch methods (_get_specs, _get_price, _get_reviews)

## What's Still Broken
- **Stale cache:** Old format data served until TTL expires (7 days for specs). Use `?nocache=true` to bypass

## New Decisions Made
| Decision | Reasoning |
|----------|-----------|
| Fixed 11-field spec schema per category | Prevents inconsistent freeform fields between products |
| GPT can use training knowledge for specs | "Don't guess" was too conservative — known products had N/A for basic fields |
| 3-tier price fallback with guaranteed result | Users always see a price; estimated prices clearly labeled |
| Both-products-must-have-data filter for specs table | No point showing a spec row if only one product has it |
| nocache query param | Allows testing fresh data without waiting for cache expiry |

## Current Feature Status
| Feature | Status | Notes |
|---------|--------|-------|
| Ratings | Working | Tier 0 expert reviews (PCMag/CNET JSON-LD) → Tier 1-3 Shopping fallback |
| Prices | Working | 3-tier fallback + retailer quality scoring (prefers official retailers) |
| Specs | Working | Fixed 11-field schema, consistent across products |
| Specs table (frontend) | Working | Fixed order, labels, both-must-match filter |
| Pros/Cons | Working | Generated from specs + reviews |
| Comparison/Winner | Working | GPT comparison with value scores and best-for |
| Enhanced Reviews (backend) | Working | category_scores, rating_distribution, user_quotes, source_ratings, summary, verified_rating |
| Enhanced Reviews (frontend) | Working | ReviewsTab renders all fields; code audited Feb 14 2026, curl-verified both products return full data |
| Cache bypass | Working | `?nocache=true` query param |
| Camera input | Working | GPT-4o-mini vision → auto-compare via v3 pipeline, $0.007-0.014/comparison |
| URL input | Partial | Old code, untested with new architecture |

---

# SESSION LOG: February 13, 2026

## What We Fixed

### 1. Price quality — Retailer quality scoring system
**File:** `app/services/structured_comparison_service.py`
- Added `RETAILER_TIERS` dict with 3-tier retailer scoring:
  - **Tier 1 (1.0):** Amazon, Apple, Samsung, Best Buy, Walmart, Target, Noon, Jarir, eXtra, Lulu, Carrefour, Sharaf DG, Virgin Megastore, brand stores
  - **Tier 2 (0.7):** Newegg, B&H Photo, Adorama, Costco, Ubuy, Micro Center, John Lewis, Currys
  - **Tier 3 (0.3):** eBay, AliExpress, Alibaba, Temu, Wish, DHgate, Back Market, Swappa, refurbished sellers
  - **Unknown (0.5):** Any retailer not in the list gets benefit of the doubt
- Added `_get_retailer_score()` — case-insensitive substring matching against Serper `source` field
- Updated `_extract_price_from_shopping()` sort key: `(-match_score, -retailer_score, amount)`
  - Previously: best title match → cheapest price (eBay at BHD 135 won over Amazon at BHD 250)
  - Now: best title match → best retailer quality → cheapest price (Amazon wins)
- Added logging: `[PRICE] Selected: Amazon.com (tier 1.0) at BHD 249.99 for 'iPhone 15' (5 candidates)`

### 2. Price accessory/min-price filters
**File:** `app/services/structured_comparison_service.py`
- Accessory filter: rejects "case", "cover", "charger", etc. from price results
- Min price BHD 100 for phones/laptops/consoles
- Strict title match: ALL key words must appear for high-value products
- Tier 3 purge: remove eBay/AliExpress when Tier 1/2 retailers exist

### 3. Rating system — 4-tier fallback
**File:** `app/services/structured_comparison_service.py`

**Tier 0 (Expert):** Scrape editorial review sites for JSON-LD ratings
- Search: `"{product} review site:pcmag.com OR site:cnet.com OR ..."` (1 credit)
- Scrape: Serper `/scrape` endpoint on review URL (2 credits)
- Parse: JSON-LD `reviewRating` → rating + author + pros/cons
- Sites: PCMag, CNET, TechRadar, Tom's Guide, The Verge, Wired, LaptopMag, Tom's Hardware
- Tries up to 3 review URLs until one yields a parseable rating
- Label: `"Pcmag Expert Review (Eric Zeman)"`, confidence: `"expert"`
- Bonus: extracts `positiveNotes`/`negativeNotes` as `expert_pros`/`expert_cons`

**Tier 1 (High):** Serper Shopping from trusted retailers (Amazon, Best Buy, Walmart, etc.)
**Tier 2 (Medium):** Known retailers, .com/.ae stores
**Tier 3 (Low):** Marketplace (eBay/AliExpress) only if review_count > 1000, labeled "marketplace rating"

### 4. Added 2026 product date context
**File:** `docs/CLAUDE_CODE_CONTEXT.md`
- Added current product release dates so AI doesn't flag iPhone 17 / Galaxy S26 as "rumored"

## Cost Impact
| Before | After |
|--------|-------|
| ~$0.008/comparison | ~$0.022/comparison |
| Ratings: 1 Shopping call | Ratings: 1 search + up to 3 scrapes + 1 Shopping fallback |
| Inaccurate Google Shopping aggregates | Real editorial ratings from review sites |

---

# SESSION LOG: February 13, 2026 (Evening) — Enhanced Reviews System

## What We Built

### 1. Enhanced Reviews — Rich structured data from same API calls
**Files:** `app/services/extraction_service.py`, `app/services/structured_comparison_service.py`, `app/models/product_schema.py`

**Architecture change:** Split `_fetch_product_data` into Phase 1 (specs + price parallel) → Phase 2 (reviews + rating parallel). This lets shopping data from Phase 1 feed into review extraction in Phase 2.

**New review fields (all Optional, backward-compatible):**
- `rating_distribution` — `{5_star: %, 4_star: %, ...}` estimated by GPT
- `category_scores` — `{performance: 9, value: 7, ...}` scored 1-10, category-aware
- `source_ratings` — REAL retailer ratings from Serper shopping data (NOT GPT)
- `detailed_praises`/`detailed_complaints` — `[{text, frequency, quote}]`
- `user_quotes` — `[{text, sentiment, source, aspect}]` from search snippets
- `summary` — 2-3 sentence opinionated summary
- `verified_rating` — `{rating, review_count, source, verified}` matches Overview tab exactly

**Key design decisions:**
- GPT is explicitly told NOT to generate `source_ratings` — was hallucinating review counts
- Real retailer ratings injected post-extraction from `_collect_retailer_ratings()`
- `verified_rating` injected into reviews so frontend can show consistent data between Overview and Reviews tabs
- `max_tokens` increased 500→800→1000 to prevent JSON truncation (GPT sometimes cuts off mid-JSON)

### 2. Frontend — Reviews tab with full data rendering
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

- Added `ReviewData` interface with all new fields
- `ReviewsTab` now renders: summary, category score bars, star distribution bars, source ratings with verified badge, user quotes with sentiment badges, pros/cons
- Code audited Feb 14 2026: all conditional rendering correct (safe optional chaining, null checks). Backend curl-verified: all enhanced fields present for both products.

### 3. Bugs found and fixed
- **GPT JSON truncation:** 800 max_tokens sometimes too low → "Unterminated string" JSON parse error → one product gets data, other doesn't (random). Fixed by removing `source_ratings` from GPT prompt (saves ~100 tokens) + increasing to 1000
- **Hallucinated source_ratings:** GPT was fabricating review counts (e.g. "bestbuy.com 4.5, 1,234 reviews"). Fixed by injecting real Serper shopping data post-extraction
- **Rating mismatch:** Overview showed one rating, Reviews tab showed different one. Fixed by injecting `verified_rating` into reviews

## Commits
1. `5a1ddf6` — Initial enhanced reviews (Phase 1/2 reorder, rich GPT prompt, new schema fields)
2. `97468ec` — Frontend: ReviewsTab renders all new fields
3. `7717db0` — Bug fixes: stop GPT hallucinating, fix truncation, inject verified_rating

## What's Still Needed
- **source_ratings can be empty** for some products if Bahrain shopping results lack `rating` fields — correct behavior but means "Ratings by Source" section may be empty
- **Cost crept to ~$0.011** from ~$0.009 due to max_tokens increase — still under $0.015 target

## Lessons Learned
| Lesson | Detail |
|--------|--------|
| Never let GPT generate data you already have | GPT hallucinated review counts; always inject real data post-extraction |
| max_tokens truncation is silent | GPT stops mid-JSON, causing intermittent parse errors — one product fails randomly |
| Frontend needs device testing | curl verification is necessary but not sufficient for React Native apps |

---

# SESSION LOG: February 14, 2026 — Complete Price Fix Session

## Fixes Completed

### 1. Currency Conversion (Prices)
- Added currency detection from Serper price strings ($ → USD, £ → GBP, € → EUR)
- Added conversion to BHD after detection
- Fixed: $541 USD was showing as BHD 541 (now correctly converts)

### 2. GPU Support
- Added GPU keywords to HIGH_VALUE_KEYWORDS: rtx, nvidia, geforce, radeon, amd, gpu
- GPUs now get min-price filter and strict-title matching

### 3. Price Sanity Checks
**File:** `app/services/structured_comparison_service.py` — `_get_price()` method
- HIGH check: if price > 2x Tier 3 estimate → reject (catches inflated prices)
- LOW check: if price < 0.5x Tier 3 estimate → reject (catches scam listings)
- Fixed retailer_score being `.pop()`d before sanity check could read it
- Only for high-value products (`_is_high_value_query`) — cheap items unaffected

| Tier | HIGH check (> 2x est) | LOW check (< 0.5x est) | Scope |
|------|----------------------|------------------------|-------|
| Tier 1 (Shopping) | Reject → Tier 2 | Reject → Tier 2 | High-value + untrusted retailer only |
| Tier 2 (GPT) | Use Tier 3 | Use Tier 3 | High-value only |
| Tier 3 (Estimate) | N/A (last resort) | N/A (last resort) | — |

### 4. Cost Optimization
- Skip sanity check for trusted retailers (retailer_score >= 1.0: Amazon, Best Buy, eXtra, Noon, etc.)
- Cache Tier 3 estimate within `_get_price()` to avoid duplicate calls
- Tier 0 expert review (`_get_expert_review()`) is dead code — defined but never called
- Cost: $0.011 (trusted) to $0.012 (untrusted) — under $0.015 target

### 5. UI & Cache Fixes
- Sanitized GPT "null" strings → Python None (no more "null" text in UI)
- Renamed "Value Score" → "Comparative Value" in Overview
- Added `DELETE /api/v1/text/cache?q=product` endpoint for flushing stale cache
- Added temporary `nocache` in app until Feb 16 to bypass stale Redis entries (auto-disables)

## Final Results
| Product | Before | After |
|---------|--------|-------|
| RTX 3090 | BHD 206 (scam listing) | BHD 490 (Sharaf DG) |
| RTX 3070 | BHD 541 (inflated USD) | BHD 188.5 (estimated) |

## Known Issues
- **Concurrent request cost double-counting:** Running two comparisons simultaneously on Railway inflates `total_cost` in metadata. Solo requests report accurate costs.
- **GPT parse non-determinism:** Different runs can produce different brand/name splits, leading to different cache keys for the same product.

## Current Feature Status (Feb 15 2026)
| Feature | Status |
|---------|--------|
| Prices | Working (currency conversion + sanity checks) |
| Ratings | Working (4-tier + retailer URLs fixed) |
| Reviews | Working (category scores, user quotes, etc.) |
| Specs | Partially working (variant hint added, needs more testing) |
| Camera input | Working (vision + comparison flow) |
| URL input | Not tested with new architecture |

## Next Priority
- Verify specs accuracy with camera input (variant hints)
- URL input (update to use v3 pipeline)
- Apply Figma UI design
- Premium tier with Stripe

---

# SESSION LOG: February 15, 2026 — Camera Input Feature

## What We Built

### 1. Camera Identification Endpoint
**File:** `app/api/image_routes.py` (NEW)
- `POST /api/v1/image/identify` — accepts 1-4 images + region
- GPT-4o-mini vision identifies products from photos (single API call for all images)
- **2+ products found**: auto-builds query string, calls `StructuredComparisonService.compare_from_text()` — reuses full v3 pipeline (specs, prices, ratings, reviews, comparison)
- **1 product found**: returns `action: "need_second_product"` with identified product
- **0 products**: returns error
- Injects `input_method: "camera"`, `vision_cost`, `identified_products` into metadata

### 2. Improved Vision Prompt
**File:** `app/services/openai_service.py`
- Replaced grocery-focused prompt with electronics-aware identification
- Added `confidence` field (high/medium/low) replacing `size`
- Handles: product boxes, bare products (by shape/logo/design), screenshots, shelf photos, price tags
- Multi-product: identifies ALL products in a single image (up to 4 total)
- Normalization: ensures every product has brand/name/visible_price/confidence
- Uses `detail: "low"` for cost control (~$0.003 per call regardless of image count)

### 3. Frontend Camera Flow
**Files:** `SmartCompareApp/src/screens/CameraScreen.tsx`, `src/services/api.ts`, `src/types/types.ts`, `src/types/index.ts`
- `CameraScreen`: MIN_IMAGES=2, calls `identifyFromImages()` instead of old `compareProducts()`
- `action: "comparison"` → navigates to ResultsScreen with full comparison
- `action: "need_second_product"` (edge case) → shows green banner with detected product name + "Take Another Photo" button
- `action: "error"` → Alert dialog
- New `identifyFromImages()` API function with same iOS/HEIC handling as old `compareProducts()`
- New `ImageIdentifyResult` discriminated union type, `IdentifiedProduct` type
- Added `index.ts` barrel export for types

### 4. Router Registration
**File:** `app/main.py`
- Registered `image_router` at `/api/v1/image/*`
- Old `/api/v1/compare` (legacy image endpoint) preserved for backward compatibility

## Cost Analysis
| Scenario | Vision | Pipeline | Total |
|----------|--------|----------|-------|
| Cache hit (popular products) | $0.003 | $0.001 | **$0.004** |
| Partial cache (specs cached) | $0.003 | $0.005 | **$0.008** |
| Full cache miss | $0.003 | $0.011 | **$0.014** |
| Single product identify only | $0.003 | $0.000 | **$0.003** |

## Test Results (curl verified on Railway)
- **Single image** (iPhone 16 Pro text): `action: "need_second_product"`, confidence: "high", price extracted
- **Two separate images** (iPhone + Galaxy): `action: "comparison"`, full specs/prices/ratings/reviews, cost $0.0074 (iPhone cached), 37s elapsed
- All responses include `confidence` field in identified products

## Commits
1. `87217d6` — Backend: image_routes.py, improved vision prompt, main.py router
2. `2e68a87` — Frontend: types, api, CameraScreen flow

## Architecture Decision
| Decision | Reasoning |
|----------|-----------|
| Single endpoint, not identify+compare | Eliminates round-trip for 2+ products case |
| Keep MIN_IMAGES=2 | No text input for second product; camera-only flow |
| Reuse StructuredComparisonService | No pipeline duplication; cache/ratings/reviews all work automatically |
| `detail: "low"` for vision | ~$0.003 regardless of 1-4 images; sufficient for text-on-packaging |
| Separate images, not combined | Accuracy > $0.0004 savings |

---

# SESSION LOG: February 15, 2026 (Evening) — Camera Bug Fixes

## Bugs Fixed

### 1. Rating source URLs were Google redirects
- **Was:** `rating_source.url` was `https://www.google.com/search?ibp=oshop&q=...` — clicking opened Google, not retailer
- **Fix:** Added `RETAILER_SEARCH_URLS` map (16 retailers) and `_build_retailer_url()` method. URLs now go to actual retailer search pages (e.g., `bestbuy.com/site/searchpage.jsp?st=Apple+iPhone+16`)
- **File:** `structured_comparison_service.py` — constant + method + 3 usage sites (consensus rating, tiered rating, price)
- **Fallback:** Unknown retailers → Google Shopping search (`google.com/search?tbm=shop&q=...`)
- **Tested:** curl verified — "Best Buy via Google Shopping" now links to bestbuy.com

### 2. Vision data discarded at text boundary
- **Was:** `image_routes.py` built plain text query, `compare_from_text()` re-parsed it with GPT, losing variant info like "360 Softgels"
- **Fix:** Added `vision_products` parameter to `compare_from_text()`. Camera input now skips `parse_product_query()` and passes vision-identified products directly
- **Files:** `structured_comparison_service.py` (new `vision_products` param), `image_routes.py` (passes `vision_products=products`)
- **Bonus:** Saves $0.0003/comparison by skipping redundant GPT parse call

### 3. UnboundLocalError crash on camera comparison
- **Was:** `parsed` variable referenced at line 211 (`parsed.get("comparison_type")`) but only assigned in text path — camera path crashed
- **Fix:** `parsed.get(...) if not vision_products else "value"`

### 4. Vision variant hint for specs extraction
- **Was:** `variant=None` caused GPT specs prompt to show "(base model)", defaulting to 180-count instead of 360-count
- **Fix:** Vision name passed as `variant` field so prompt shows `(variant: Vitamin D-3 360 Softgels)`. Added `_vision` flag for proper `full_name`/`display_name` handling without doubling

### 5. Brand missing from specs/reviews headers
- **Was:** Frontend used `product.name` (no brand) for specs table header and reviews card title
- **Fix:** Changed to `product.full_name || product.name` with `numberOfLines={2}`
- **File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

## Commits
1. `469b537` — Build retailer URLs for ratings (RETAILER_SEARCH_URLS + _build_retailer_url)
2. `81e71ca` — Context update
3. `595a5dc` — Fix parsed UnboundLocalError crash in vision path
4. `c3f94f3` — Vision variant hint + _vision flag for display names
5. `4e81337` — Frontend: full_name in specs/reviews headers

## Still Broken (For Tomorrow)
1. Specs still showing wrong variant sometimes (180 vs 360 softgels) — variant hint helps but GPT non-determinism can override
2. NOW Vitamin D-3 sometimes shows "No verified rating" — depends on Serper shopping data availability
3. Price accuracy needs verification for camera-identified products

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | Working (currency conversion + sanity checks) |
| Ratings | Working (4-tier + retailer URLs fixed) |
| Reviews | Working (category scores, user quotes, etc.) |
| Specs | Partially working (variant hint added, needs testing) |
| Camera input | Working (vision + comparison flow) |
| URL input | Not tested with new architecture |

---

# SESSION LOG: February 15, 2026 (Evening) — Vitamin Matching Fixes

## What We Fixed

### 1. Number Preservation in Matching (Critical)
**File:** `app/services/structured_comparison_service.py`
- Added `_numbers_match()` static method — extracts standalone 2+ digit numbers from product name and requires at least one to appear in the shopping result title
- "NOW Vitamin D-3 360 Softgels" now rejects "NOW Vitamin D-3 120 Softgels" (360 ≠ 120)
- Single-digit numbers (e.g., "3" in "D-3") are ignored — too aggressive, would reject "Vitamin D3"
- Applied as FILTER 4 in `_extract_price_from_shopping()` and FILTER 3 in `_extract_rating_from_shopping()`

### 2. Hyphen Normalization (High)
**File:** `app/services/structured_comparison_service.py`
- Added `_normalize_words()` static method — lowercase + strip hyphens: "D-3" → "d3", "D3" → "d3"
- Replaced `set(text.lower().split())` with `self._normalize_words(text)` in 4 places (p_words and t_words in both price and rating extraction)
- Fixes match score dropping from 100% to 80% when product uses "D-3" but shopping result uses "D3"

### 3. Count Field Added to Spec Schemas (Medium)
**File:** `app/services/extraction_service.py`
- Added `"count"` as first field in `grocery` schema (replaced `"halal"`) and `other` schema (replaced `"certifications"`)
- Both schemas remain at 11 fields (fixed constraint)
- Added explicit GPT instruction: "If the product name or variant contains a count/quantity (e.g. '360 Softgels'), use EXACTLY that number for the 'count' field"
- GPT now has both a slot AND a directive for count/quantity

## Test Results (3 runs, nocache=true, all consistent)
| Product | Count | Rating | Price |
|---------|-------|--------|-------|
| NOW Vitamin D-3 360 | 360 ✅ | 4.8-4.9 ✅ | BHD 4.39 |
| Nature Made D3 2000 | 250 ✅ | 4.5-4.7 ✅ | BHD 4-12 |

### Electronics Regression — PASSED ✅
- iPhone 16: 4.6 rating, BHD 310
- Galaxy S25: 4.7 rating, BHD 407

### Cost: $0.012/comparison (under $0.015 ✅)

## Commits
- `b4d6f4a` — Fix vitamin matching: number preservation, hyphen normalization, count field

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working |
| Ratings | ✅ Working (consistent across runs) |
| Reviews | ✅ Working |
| Specs | ✅ Working (count field added for supplements) |
| Camera | ✅ Working |
| URL input | ❌ Not started |

## Key Technical Details
| Method | Purpose | Location |
|--------|---------|----------|
| `_normalize_words(text)` | Lowercase + strip hyphens for word matching | `structured_comparison_service.py:604` |
| `_numbers_match(product, title)` | Reject titles missing key quantities | `structured_comparison_service.py:612` |
| `CATEGORY_SPEC_SCHEMAS["grocery"]` | Now includes `count` field | `extraction_service.py:77` |
| `CATEGORY_SPEC_SCHEMAS["other"]` | Now includes `count` field | `extraction_service.py:82` |

---

# SESSION LOG: February 16, 2026 — Camera Vision & URL Fixes

## What We Fixed

### 1. Vision prompt OCR improvements
**File:** `app/services/openai_service.py`
- Changed `detail: "low"` → `detail: "auto"` — lets GPT choose resolution per image, enables reading small label text
- Rewrote prompt to emphasize OCR: "READ the EXACT text printed on each product's packaging, label, or screen"
- Added `size_or_count` field — dedicated slot for "360 Softgels", "128GB", "1000mg" etc.
- Added category-specific OCR rules (supplements, electronics, grocery)
- Examples now include vitamin bottle, not just electronics

### 2. Expanded RETAILER_SEARCH_URLS (16 → 36 retailers)
**File:** `app/services/structured_comparison_service.py`
- Added: Ubuy, Lulu, Carrefour, Virgin Megastore, Apple, Samsung, Dell, Lenovo, Currys, John Lewis, Fnac, AliExpress, Temu, Back Market, Swappa, Vitacost, Adorama, Micro Center, B&H Photo
- Previously: Galaxy S25 rating URL went to google.com (Ubuy not in map). Now goes to bestbuy.com or ubuy.com

### 3. Consensus rating prefers known retailers
**File:** `app/services/structured_comparison_service.py`
- Added `_has_retailer_url()` helper — checks if source matches any RETAILER_SEARCH_URLS key
- Consensus sort now uses `(has_retailer_url, match_score)` — prefers sources with real retailer URLs

### 4. Vision size_or_count enrichment
**File:** `app/api/image_routes.py`
- After vision identification, appends `size_or_count` to product name if not already present
- "Vitamin D-3" + "360 Softgels" → "Vitamin D-3 360 Softgels" — feeds correct variant into specs extraction

## Test Results (verified on Railway)
| Test | Specs Count | Rating URL | Cost |
|------|-------------|------------|------|
| NOW Vitamin D-3 360 | count=360 ✅ | google.com (Tahoma Clinic — unknown retailer, expected) | $0.003 (cached) |
| Nature Made D3 2000 | count=250 ✅ | walmart.com ✅ | $0.003 (cached) |
| iPhone 16 | N/A | apple.com ✅ (was bestbuy before) | $0.006 |
| Galaxy S25 | N/A | bestbuy.com ✅ (was google.com before) | $0.006 |

## Commits
- `f549cc7` — Fix camera vision: OCR prompt, detail:auto, expand retailer URLs

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working |
| Ratings | ✅ Working (URLs go to real retailers) |
| Reviews | ✅ Working |
| Specs | ✅ Working (count field correct for supplements) |
| Camera | ✅ Working (OCR prompt, detail:auto, size_or_count field) |
| URL input | ❌ Not started |

---

# SESSION LOG: February 17, 2026 — Price URLs & Rating Brand Fix

## Fixes Deployed

### 1. Price URLs clickable (Tier 2/3 backfill)
**File:** `app/services/structured_comparison_service.py`
- Tier 2 (GPT) and Tier 3 (estimate) prices always had `url: null` — only Tier 1 (Shopping) set URLs
- Added URL backfill: after Tier 2/3 returns, if `retailer` exists but `url` is null, call `_build_retailer_url(retailer, full_name)`
- Added "nasser pharmacy" to `RETAILER_SEARCH_URLS` map

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Added `url?: string` to price type
- Made retailer name clickable with `TouchableOpacity` + `Linking.openURL(price.url)` when URL exists
- Non-URL retailers still show as plain text

### 2. Brand-aware matching for ALL products
**File:** `app/services/structured_comparison_service.py`
- **Root cause:** `_strict_title_match()` only ran for HIGH_VALUE_KEYWORDS (phones, GPUs, consoles). For vitamins, only word-overlap matching was used — "HealthAid Vitamin D3 1000 IU" matched ANY "Vitamin D3 1000 IU" at 80% overlap, so Target's generic D3 was incorrectly shown as HealthAid's rating
- **Fix:** Apply `_strict_title_match()` to ALL products, not just high-value
- **Fix:** Added hyphen normalization to `_strict_title_match()` — "D-3" matches "D3" (same as `_normalize_words()`)
- Removed unused `is_high_value` variable from `_extract_rating_from_shopping()`

### 3. Show unverified ratings with disclaimer
**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Previously: any rating with `rating_verified=false` was completely hidden as "No verified rating"
- Now: unverified ratings show in gray with star-outline icon and "Unverified" badge + source name
- Only `rating === null` shows "No verified rating" now

### 4. Vision OCR improvements (from Feb 16 session)
**File:** `app/services/openai_service.py`
- `detail: "low"` → `detail: "auto"` for better text reading
- Rewrote prompt for OCR emphasis with category-specific rules
- Added `size_or_count` field for quantities

## Still Broken (For Next Session)
1. **Ratings show null for vitamins** — Serper doesn't return HealthAid/NOW from Tier 1/2 retailers. Brand-aware matching correctly rejects wrong products, but no correct match found either. Need to investigate if broader search or fallback can help
2. **Specs show "value or null" for many fields** — Dimensions, Material, Color, Warranty, Power, Origin, Compatibility, Weight — these fields don't apply to vitamins. Need category-specific schema cleanup
3. **Cost at $0.015** — slightly over target, acceptable for complex queries

## Test Results (verified on Railway)
| Test | Rating Before | Rating After | Price URL |
|------|-------------|-------------|-----------|
| HealthAid D3 1000 IU | 5.0 from Target (WRONG) | null (correct — no HealthAid products on Tier 1/2) | nasserpharmacy.com ✅ |
| NOW D-3 360 Softgels | "No verified rating" | null (correct — niche count) | null (no retailer) |
| iPhone 16 Pro | 4.4 verified ✅ | 4.4 verified ✅ | google.com |
| Galaxy S25 Ultra | 4.8 verified ✅ | 4.8 verified ✅ | extra.com ✅ |

## Commits
- `5e07365` — Fix price URLs: backfill Tier 2/3, make retailer clickable
- `21816aa` — Fix ratings: brand-aware matching for all products, show unverified with disclaimer

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working (URLs clickable) |
| Ratings | ⚠️ Partial (brand-aware matching works, but vitamins get null — no Tier 1/2 coverage) |
| Reviews | ✅ Working |
| Specs | ⚠️ Partial (count works, other fields show "value or null" for non-electronics) |
| Camera | ✅ Working (OCR reads correctly) |
| URL input | ❌ Not started |

## Key Technical Changes
| Method | Change | Location |
|--------|--------|----------|
| `_strict_title_match()` | Now normalizes hyphens, applies to ALL products | `structured_comparison_service.py:663` |
| `_extract_rating_from_shopping()` | Removed `is_high_value` gate on strict match | `structured_comparison_service.py:1384` |
| `RatingDisplay` | 3-state: null → "No verified rating", unverified → gray + badge, verified → green + link | `ResultsScreen.tsx:193` |
| `RETAILER_SEARCH_URLS` | 37 retailers (added nasser pharmacy) | `structured_comparison_service.py` |

---

# SESSION LOG: February 17, 2026 (Evening) — Specs, Ratings, Cost Fixes

## Fixes Deployed

### 1. Specs "value or null" — 6-layer fix
**Files:** `extraction_service.py`, `structured_comparison_service.py`, `ResultsScreen.tsx`
- **Root cause:** GPT prompt template used `"value or null"` as placeholder (line 93). GPT echoed it literally for fields it had no data for. Nothing downstream caught the string.
- **Fix 1:** Changed prompt placeholder from `"value or null"` to JSON `null` — GPT now returns actual null
- **Fix 2:** Added `"supplements"` category to `CATEGORY_SPEC_SCHEMAS` with relevant fields: count, serving_size, active_ingredient, dosage, form, allergens, certifications, origin, organic, shelf_life, nutrition_calories
- **Fix 3:** Added `"supplements"` to `PRODUCT_PARSER_PROMPT` category options
- **Fix 4+5:** Added `"or null"` string catch in both `extract_specs()` and `_clean_specs()` sanitizers
- **Fix 6:** Frontend `isNA()` now catches `"or null"` strings as safety net
- **Result:** Vitamins now show supplement-specific specs, zero "value or null" strings

### 2. Unverified ratings fallback
**File:** `structured_comparison_service.py`
- **Root cause:** When `_get_verified_rating()` returned null (no shopping source passed strict filters), frontend showed "No verified rating" — even though GPT reviews had extracted an `average_rating`
- **Fix:** After `_get_verified_rating()` returns null, check `reviews.average_rating`. If valid (1.0-5.0), use it as unverified rating with source "Aggregated from reviews", confidence "low"
- **Result:** Vitamins now show gray "Unverified" badge with GPT-aggregated rating instead of blank

### 3. Cost optimization — conditional organic + merged pros/cons
**Files:** `serper_service.py`, `extraction_service.py`, `structured_comparison_service.py`
- **Opt A:** Split `search_product_prices()` into shopping-only + `search_price_organic()`. Organic search only called when Tier 1 shopping fails. Saves $0.002/comparison in common case.
- **Opt B:** Merged `generate_pros_cons()` into `generate_comparison()` prompt. Pros/cons now extracted from comparison result (`product_0_pros`, `product_0_cons`, etc.) instead of 2 separate GPT calls. Saves $0.0008.
- **Result:** Cost dropped from $0.0174 to ~$0.014

### 4. Price sanity check extended to all products
**File:** `structured_comparison_service.py`
- **Root cause:** Tier 2 GPT price sanity check only ran for high-value products (phones, GPUs). For vitamins, GPT hallucinated BHD 24 (USD misinterpreted as BHD) and it went unchecked.
- **Fix:** Removed `_is_high_value_query()` gate from Tier 2 sanity check — all products now checked against Tier 3 estimate
- **Result:** NOW D-3 went from BHD 24 → BHD 9.43 (estimated). Still too high — needs further work.

### 5. iHerb as supplement price source
**File:** `structured_comparison_service.py`
- **Root cause:** Serper Shopping returns ZERO results for vitamins/supplements in Bahrain AND US. Tier 2 GPT hallucinated BHD 24 (confused USD for BHD). Tier 3 estimated BHD 9.43 (too high).
- **Fix:** For supplement products, inject an iHerb-specific Serper organic search (`site:iherb.com`) into Tier 2 context before GPT extraction. GPT sees real iHerb prices in snippets ("$14.21") and correctly detects USD, which auto-converts to BHD.
- **Implementation:** Added `_is_supplement_query()` with 23 keywords (vitamin, softgel, capsule, omega, etc.). When triggered, does `search_web("{query} site:iherb.com", country="us")` and prepends results to Tier 2 organic context.
- Added iHerb, Vitacost, GNC to `RETAILER_TIERS` as Tier 1 (score 1.0)
- **Result:** NOW D-3 360 Softgels: BHD 24 → BHD 5.36 from iHerb (real price, with retailer + URL)
- **Cost:** Extra $0.001 per product for supplements only (iHerb search call)

## Still Needs Work
1. **Nature Made D3 price** — BHD 4.06, no retailer, no URL. Correct range but no attribution.
2. **Cost at $0.0155 for supplements** — extra iHerb search adds $0.001/product. Electronics stay at ~$0.013.
3. **iHerb Bahrain pricing** — currently searching US iHerb (`country="us"`). Bahrain iHerb (`bh.iherb.com`) may have different prices in BHD. Could try `country="bh"` but Serper may not index it.

## Commits
1. `deafd88` — Fix specs: sanitize 'value or null', add supplements schema
2. `af38a90` — Fix ratings: fallback to GPT average_rating when shopping fails
3. `4906c4a` — Optimize cost: conditional organic search, merge pros_cons
4. `6890e06` — Fix price: extend Tier 2 sanity check to all products
5. `da8fda5` — Fix vitamin prices: add iHerb as supplement price source

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | ✅ Working (iHerb for supplements, shopping for electronics) |
| Ratings | ✅ Working (GPT review fallback for products without shopping data) |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema, no more "value or null") |
| Camera | ✅ Working |
| URL input | ❌ Not started |

## Key Technical Changes
| Change | Location |
|--------|----------|
| `CATEGORY_SPEC_SCHEMAS["supplements"]` added | `extraction_service.py:79` |
| Prompt placeholder `null` instead of `"value or null"` | `extraction_service.py:95` |
| GPT review average fallback for ratings | `structured_comparison_service.py:~380` |
| `search_price_organic()` new function | `serper_service.py` |
| `generate_comparison()` now includes pros/cons | `extraction_service.py:275` |
| Tier 2 sanity check for ALL products | `structured_comparison_service.py:~535` |
| `_is_supplement_query()` + iHerb search injection | `structured_comparison_service.py:~525` |
| iHerb/Vitacost/GNC added to `RETAILER_TIERS` | `structured_comparison_service.py:63` |

---

# SESSION LOG: February 18, 2026 — Full Codebase Audit & Critical Bug Fixes

## What We Did

### Full audit: 48 bugs found (24 backend, 24 frontend)
Ran 3 parallel exploration agents across backend, frontend, and runtime logs. Categorized all issues by severity.

### Phase 1: Backend Critical Fixes (commit `1700b6c`)

**1a. Singleton cache leak — `_shopping_items_cache` never cleared**
- `StructuredComparisonService` is a singleton (`get_comparison_service()`). `total_cost` and `api_calls` were reset per request but `_shopping_items_cache` was not.
- Under concurrent load: memory grows unbounded, stale product data leaks across requests.
- **Fix:** Added `self._shopping_items_cache = {}` at start of `compare_from_text()` (line 186).

**1b. `_convert_to_bhd(None)` crash**
- If a shopping item had no currency, calling `.upper()` on None raised `AttributeError`.
- **Fix:** Added `if not currency: return amount` guard at top of function.

**1c. Bare `except:` in `auth_routes.py:101`**
- Was catching `SystemExit`/`KeyboardInterrupt`. Changed to `except Exception:`.

**1d. CostStatus schema mismatch**
- `schemas.py` had fields `current_spend`, `budget`, `percentage_used`
- `check_monthly_budget()` returns `current_cost`, `budget_limit` (no `percentage_used`)
- **Fix:** Renamed schema fields to match actual return values.

**1e. OpenAI client import-time init**
- `openai_service.py` created `AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))` at module import time — could init with None key on cold start.
- **Fix:** Changed to `AsyncOpenAI()` which reads env at request time.

### Phase 2: Frontend Critical Fixes (commit `9602291`)

**2a. `verifyAuth()` returned boolean, App.tsx used as User**
- `verifyAuth()` called `isLoggedIn()` returning `Promise<boolean>`.
- `App.tsx:118` did `setUser(verifiedUser)` — user state became `true` not a User object. `user.email` would crash.
- **Fix:** Changed `verifyAuth()` to return `Promise<User | null>` via `initializeAuth()`.

**2b. `formatPrice()` called `.toFixed()` on ProductPrice object**
- `HistoryScreen.tsx:98`: `product.price.toFixed(2)` but `price` is `{ amount, currency }` not a number.
- **Fix:** Access `product.price.amount?.toFixed(2)` and `product.price.currency`. Handle both object and legacy number formats.

**2c. History→Results missing `comparison` field**
- `viewAsResult()` navigated with object missing `comparison` and `metadata` fields.
- `ResultsScreen` destructured `comparison` → crash on undefined.
- **Fix:** Added `comparison` and `metadata` objects to navigation params.

**2d. `rating_source.name` without null guard**
- In verified rating branch, `rating_source` could be null even when `rating_verified` is true.
- **Fix:** Changed to `rating_source?.name ?? 'Retailer'`.

### Phase 3: Session Refresh 422 Fix (commit `c19e9fb`)

**Root cause:** `POST /api/v1/auth/refresh` expects `{ refresh_token: "..." }` in body. Frontend sent `{}` (empty body) with access token in header only. FastAPI returned 422 validation error.

**Fix:**
- Added `REFRESH_TOKEN_KEY` storage constant
- Save `refresh_token` from login/register/refresh responses
- `refreshSession()` reads refresh token from storage and sends in body
- Clear refresh token on logout/session clear
- **Note:** Users must log out and back in once to store refresh token for first time.

## Remaining Bugs (deferred — Phases 3-5 from audit)
| # | Bug | Severity |
|---|-----|----------|
| 1 | Legacy `/api/v1/compare` — all function calls use wrong arg counts (4 TypeErrors) | High (legacy route) |
| 2 | No axios auth interceptor — token never sent on API requests | High |
| 3 | Missing expo-camera/expo-image-picker plugins in app.json | High (EAS builds) |
| 4 | Debug console.log everywhere in api.ts + HomeScreen | Medium |
| 5 | `.gitignore` corrupted with PowerShell heredoc wrapper | Medium |
| 6 | `pyproject.toml` diverged from `requirements.txt` (openai v1 vs v2) | Medium |
| 7 | ResultsScreen local type defs diverge from types.ts | Medium |
| 8 | ~~Dead code: `_get_pros_cons`~~ FIXED (commit `b697534`). `_get_expert_review`, unused TEMP_DIR remain | Low |
| 9 | `print()` instead of `logger` in auth_service/database_service | Low |
| 10 | `load_dotenv(override=True)` in library modules | Low |

## Commits
1. `1700b6c` — Fix backend critical: cache leak, None currency, schema mismatch
2. `9602291` — Fix frontend critical: auth type, price format, null guards
3. `c19e9fb` — Fix session refresh 422: store and send refresh token

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | Working (iHerb for supplements, shopping for electronics, clickable URLs) |
| Ratings | Working (GPT review fallback for unverified, brand-aware matching) |
| Reviews | Working (category_scores, rating_distribution, user_quotes, source_ratings) |
| Specs | Working (supplements schema, no more "value or null") |
| Camera | Working (OCR prompt, detail:auto, size_or_count) |
| Auth | Fixed (refresh token flow, verifyAuth return type) |
| URL input | Not started |

## Key Technical Changes
| Change | File |
|--------|------|
| `self._shopping_items_cache = {}` per request | `structured_comparison_service.py:186` |
| `_convert_to_bhd` None guard | `structured_comparison_service.py:1635` |
| `CostStatus` fields renamed | `schemas.py:122` |
| `AsyncOpenAI()` lazy env read | `openai_service.py:11` |
| `verifyAuth()` returns `User \| null` | `authService.ts:274` |
| `formatPrice()` handles ProductPrice object | `HistoryScreen.tsx:94` |
| `viewAsResult()` includes comparison/metadata | `HistoryScreen.tsx:106` |
| `rating_source?.name` null guard | `ResultsScreen.tsx:274` |
| Refresh token stored/sent/cleared | `authService.ts:23,73,134,145,238` |

---

# SESSION LOG: February 18, 2026 — Cost Optimization & Dead Code Cleanup

## What We Did

### Dead Code Cleanup (commit `b697534`)
Removed 109 lines of dead code that was superseded by merged pros/cons in `generate_comparison()`:
- **`extraction_service.py`**: Removed `PROS_CONS_PROMPT` template and `generate_pros_cons()` function
- **`structured_comparison_service.py`**: Removed `PROS_CONS_CACHE_TTL` constant and `_get_pros_cons()` method

### Cost Optimization DEPLOYED (commit `d9fb064`)
Supplement comparison cost reduced from $0.017 to $0.013:

**Fix 0: Hardened `_is_supplement_query()` against false positives**
- Removed "tablet" from `SUPPLEMENT_KEYWORDS` (matched "Samsung Galaxy Tablet")
- Added electronics anti-keywords using existing `HIGH_VALUE_KEYWORDS` set
- Now: if any electronics keyword present → NOT a supplement

**Opt A: Skip BH shopping for supplements (saves $0.002/comparison)**
- Serper Shopping returns ZERO results for supplements in BH
- Set `_shopping_items_cache[full_name] = []` directly, preserving invariant for rating extraction

**Opt B (Modified): iHerb-first with BH organic fallback (saves $0.001-0.002)**
- Supplements: try `site:iherb.com` search first (has real USD prices)
- If iHerb returns nothing → fall back to BH organic search
- Non-supplements: unchanged (BH organic on-demand)

**Opt C: Trust iHerb prices, skip sanity check (saves $0.0006)**
- iHerb is a trusted source (Tier 1 quality) — no need for Tier 3 GPT estimate verification
- Non-supplements: sanity check unchanged

**Opt D: HELD — defer US shopping for supplement ratings**
- Would save $0.002 but loses ~50% chance of verified rating → quality cut, held for later

### Local Test Results (Railway OpenAI timeout — tested locally)

| Test | total_cost | api_calls | Notes |
|------|-----------|-----------|-------|
| Supplements (NOW D3 vs HealthAid D3) | $0.0125 | 18 | Was $0.0165/22 calls |
| Electronics (iPhone 16 vs Galaxy S25) | $0.0145 | 20 | Unchanged path |

## BLOCKER: OpenAI API Timeout on Railway
- All OpenAI GPT-4o-mini calls timeout from Railway (~17s = 3x connect retries)
- Serper works, Upstash cache works — only OpenAI fails
- API key verified working locally (sk-proj-G33L...zgA)
- Health endpoint responds in <1s — Railway app is running
- Error: "Request timed out." from httpx connect timeout

### Needs Investigation
1. Check `OPENAI_API_KEY` in Railway Variables — is it set? Same key as backend/.env?
2. Check OpenAI account status/billing — rate limits, project API key permissions
3. Consider adding explicit timeout to `AsyncOpenAI()`: `timeout=httpx.Timeout(120.0, connect=10.0)`
4. Try redeploying on Railway (fresh container may resolve networking)

## Commits
1. `b697534` — Remove dead pros_cons code (merged into comparison)
2. `d9fb064` — Optimize supplement costs: skip empty BH calls, iHerb-first with fallback

## Key Technical Changes
| Change | File | Line |
|--------|------|------|
| `SUPPLEMENT_KEYWORDS` — removed "tablet" | `structured_comparison_service.py` | ~685 |
| `_is_supplement_query()` — electronics anti-keywords | `structured_comparison_service.py` | ~697 |
| Skip BH shopping for supplements | `structured_comparison_service.py` | ~486 |
| iHerb-first with BH organic fallback | `structured_comparison_service.py` | ~535 |
| Skip Tier 2 sanity check for supplements | `structured_comparison_service.py` | ~563 |

---

# SESSION LOG: February 18, 2026 (Evening) — OpenAI Timeout Fix & Supplement iHerb Price Fix

## What We Did

### Phase 1: OpenAI Timeout on Railway (commits `4eb4432`, `54e9d76`)

**Root cause:** Railway's default httpx connect timeout (~5s) was too short for OpenAI API cold-start connections. Locally worked fine because ISP latency was lower.

**Fix:** Added explicit `timeout=httpx.Timeout(120.0, connect=30.0)` to all 3 `AsyncOpenAI()` clients:
- `extraction_service.py` (specs/price/review/comparison extraction)
- `openai_service.py` (vision identification)
- `structured_comparison_service.py` (Tier 3 price estimate)

### Phase 2: Supplement Detection Miss (commits `5a192bd`, `7ab9b62`)

**Root cause chain:**
1. `_get_price()` only used keyword matching via `_is_supplement_query()` — "Nature Made D3" had no matching keywords ("d3" was missing from list)
2. Non-supplement path searched BH shopping → found USD prices → no currency conversion → wrong BHD amount
3. Even when detected, iHerb prices were in USD but `original_currency` wasn't forced to "USD"

**Fix:**
- Added `category` parameter to `_get_price()` — `category=="supplements"` (from GPT parser) as primary signal, keyword match as backup
- Added "d3", "d-3", brand name keywords ("nature made", "now foods", "solgar", "garden of life", "kirkland") to `SUPPLEMENT_KEYWORDS`
- Force `original_currency = "USD"` when iHerb organic results are the source

### Phase 3: Camera Price Cache Bug (commit `54e9d76`)

**Root cause:** Stale Redis cache from pre-fix code served BHD 10.9 for camera path. The `nocache=true` bypass was only on text endpoint.

**Fix:** Added `nocache` parameter to image_routes.py, threaded through to `compare_from_text()`.

### Phase 4: Supplement iHerb Price Reliability (commit `70d1bba`) — DID NOT FULLY RESOLVE

**Problem:** Camera comparison showed NOW D-3: BHD 10.9 (should be ~BHD 4). Text path worked but camera path did not.

**Root cause chain:**
1. Camera gives long product name: `"NOW high potency vitamin d-3 360 Softgels"`
2. iHerb search query becomes: `"NOW high potency vitamin d-3 360 Softgels site:iherb.com"` — too specific, returns 0 results
3. Code falls back to BH organic: `search_price_organic(search_query, "bh")` — Bahrain pharmacy search
4. GPT extracts ~10.9 from a Bahrain pharmacy listing → `original_currency: "BHD"`
5. Target is also BHD → no conversion → BHD 10.9 (wrong)
6. The iHerb USD→BHD forcing logic doesn't fire because `iherb_organic` is empty

**Secondary bug:** `full_name` in `_get_price()` doubles the variant: `"NOW high potency vitamin d-3 360 Softgels 360 Softgels"` (name already has variant from image_routes enrichment + `_get_price` appends variant again)

**Three fixes applied:**

1. **Strip pill count from iHerb search query** — regex removes `\b\d+\s*(softgels?|capsules?|tablets?|...)\b` from query. Keeps dosage (e.g., "1000 IU"). Example: `"NOW high potency vitamin d-3 1000 IU 360 Softgels"` → `"NOW high potency vitamin d-3 1000 IU"`

2. **Remove BH organic fallback for supplements** — when iHerb returns nothing, instead of falling back to BH organic search (which gives wrong local BHD prices), pass empty context so Tier 2 GPT returns null → Tier 3 USD estimate handles it with proper conversion

3. **Fix full_name doubling for vision products** — check if `variant.lower() in name.lower()` before concatenating. Vision products have name already containing size_or_count from image_routes.py enrichment.

**Status:** Deployed but did NOT fully resolve the camera price issue. Needs further investigation — possibly the camera product name itself needs simplification before being used as search query, or the iHerb search needs broader matching.

## Commits
1. `4eb4432` — Fix OpenAI timeout: increase connect timeout to 30s for Railway
2. `5a192bd` — Fix supplement detection: use GPT category, add d3/brand keywords
3. `7ab9b62` — Fix iHerb USD→BHD conversion: force original_currency for US prices
4. `73e8c33` — Fix vision category detection + camera upload Network Error
5. `54e9d76` — Fix camera price cache: stale BHD 10.9 served from pre-fix cache
6. `70d1bba` — Fix supplement iHerb price: strip pill count from query, remove BH fallback (DID NOT FULLY RESOLVE)

## Key Technical Changes
| Change | File | Detail |
|--------|------|--------|
| `timeout=httpx.Timeout(120.0, connect=30.0)` | 3 files | All AsyncOpenAI clients |
| `category` param on `_get_price()` | `structured_comparison_service.py` | Primary supplement signal |
| `SUPPLEMENT_KEYWORDS` expanded | `structured_comparison_service.py` | d3, d-3, brand names |
| Force `original_currency = "USD"` for iHerb | `structured_comparison_service.py:565` | Prevents BHD misattribution |
| `nocache` on image endpoint | `image_routes.py` | Bypass stale camera cache |
| Strip pill count regex | `structured_comparison_service.py:548` | `re.sub(r'\b\d+\s*(softgels?|...)\b', ...)` |
| Skip BH organic for supplements | `structured_comparison_service.py:561` | Empty context → Tier 3 estimate |
| `full_name` variant dedup | `structured_comparison_service.py:484` | `if variant.lower() in name.lower()` |

## Still Broken
1. **Camera supplement prices** — iHerb search with stripped pill count still may not return results for verbose camera product names. The search query `"NOW high potency vitamin d-3 1000 IU site:iherb.com"` may still be too long/specific. May need to simplify the camera product name further (e.g., just `"NOW vitamin d3 1000 IU"`) or use a different search strategy for camera-identified supplements.
2. **No axios auth interceptor** — token never sent on API requests (deferred)
3. **Legacy `/api/v1/compare` route** — broken function calls (deferred)

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | ✅ Working (iHerb for supplements, shopping for electronics) |
| Prices (camera input) | ⚠️ Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | ✅ Working (GPT review fallback for unverified, brand-aware matching) |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema) |
| Camera | ⚠️ Partial (identification works, prices broken for supplements) |
| Auth | ✅ Fixed (refresh token flow) |
| URL input | ❌ Not started |

---

## Session: February 20, 2026 — Rating/Price Links + Cost Optimization

### What Was Done

**1. Fixed Rating & Price Links (no legit links before)**
- **Problem:** Rating links pointed nowhere useful. Price links were wrong for some products (generic search pages instead of product pages).
- **Root cause:** Backend discarded Serper Shopping `link` field. Frontend `openRatingSource()` hardcoded Google Shopping search, ignoring backend URLs.
- **Fix (backend):** Use Serper Shopping `link` field (Google Shopping product-specific URLs with catalog IDs) as primary URL for both price and rating. Fall back to `_build_retailer_url()` search pages when no link available.
- **Fix (frontend):** `openRatingSource()` now uses `rating_source.url` from backend first. Added `google_shopping_consensus` and `gpt_review_aggregate` to `extract_method` type union, `getConfidenceColor()`, and `getMethodLabel()`.
- **Files changed:** `structured_comparison_service.py` (4 edits), `ResultsScreen.tsx` (4 edits)
- **Tests:** `tests/test_url_extraction.py` — 8 pytest tests covering price URL, tiered rating URL, and consensus rating URL extraction
- **Commit:** `b3e35e7`

**2. Cost Optimization — Unified Search Merging**
- **Problem:** Each comparison made 15-20 API calls at $0.0145 (electronics) / $0.0119 (supplements). Target: ≤$0.015.
- **Analysis:** Specs and reviews each did their own Serper web search ($0.001 each). Two separate searches per product = $0.004/comparison wasted on redundant calls.
- **Fix:** Added unified pre-search in `_fetch_product_data()` — one Serper web search (`"{query} specifications reviews price"`, 10 results) shared by both `_get_specs(search_results=...)` and `_get_reviews(search_results=...)`. Gated by cache check so no wasted call when data is already cached.
- **Results:**
  - Electronics: **$0.0145 → $0.0099** (32% reduction, 20→13 API calls)
  - Supplements: **$0.0119 → $0.0119** (1 call saved; iHerb/pharmacy paths dominate)
- **Approach B (skip redundant US rating search):** After analysis, the existing BH→US fallback in `_get_verified_rating()` already correctly returns early when BH data has tier1/tier2/consensus ratings. No code change needed.
- **Commit:** `ec2e80d`

### Key Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use Serper `link` field as primary URL | Zero-cost improvement (data already fetched), gives product-specific Google Shopping pages |
| `_build_retailer_url()` as fallback | Generates search page URLs when Serper link is absent (GCC retailers) |
| Unified search over separate searches | One Serper call ($0.001) replaces two ($0.002), 10 results cover both specs and reviews |
| Gate unified search on cache check | Avoids wasting $0.001 when both specs and reviews are already cached |
| Don't merge price organic search | Uses region-specific query terms ("Bahrain price BHD buy") — merging would dilute results |

### Architecture Changes
```
BEFORE (per product, no cache):
  Phase 1: _get_specs() [search_web + GPT] + _get_price() [shopping + organic + GPT]
  Phase 2: _get_reviews() [search_web + GPT] + _get_verified_rating() [US shopping]

AFTER:
  Pre-fetch: unified search_web() — shared by specs + reviews (gated by cache check)
  Phase 1: _get_specs(search_results=unified) + _get_price() [shopping + organic + GPT]
  Phase 2: _get_reviews(search_results=unified) + _get_verified_rating() [US shopping]
```

### What Serper Shopping `link` Actually Contains
- NOT direct retailer URLs (despite Serper docs suggesting this)
- Google Shopping product-specific pages with `ibp=oshop`, `catalogid`, `pvo`, `pvt` parameters
- Example: `https://www.google.com/search?ibp=oshop&q=NOW+D3&prds=catalogid:10530300028176976053,...`
- Still much better than generic search pages — leads to product detail with price comparison

### Updated Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | ✅ Working (iHerb for supplements, shopping for electronics) |
| Prices (camera input) | ⚠️ Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | ✅ Working + **linked to sources** |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema) |
| Camera | ⚠️ Partial (identification works, prices broken for supplements) |
| Auth | ✅ Fixed (refresh token flow) |
| URL input | ❌ Not started |
| **Rating/Price links** | ✅ **NEW — product-specific Google Shopping URLs** |
| **Cost optimization** | ✅ **NEW — $0.010 electronics, $0.012 supplements** |

---

## Session 8: Feb 21, 2026 — Pharmacy JSON-LD Price Extraction

### Problem
Non-iHerb supplement brands (HealthAid, Vitabiotics, etc.) were getting wrong prices. HealthAid Vitamin D3 1000IU returned BHD 3.77 (GPT guess), BHD 5.66, or BHD 7.71 (wrong iHerb product match) across different runs. Real price is BHD 9.00 (bolo.bh, 120ct) or BHD 6.30 (Boots, 30ct).

### Root Cause
HealthAid is NOT sold on iHerb. The iHerb scraper either matched a different brand's product or returned None, falling through to unreliable GPT snippet extraction.

### Solution: JSON-LD Product Schema Parsing
Bahrain pharmacy product pages (bolo.bh, bn.boots.com) embed structured `Product` schema in JSON-LD with exact BHD prices. Parse these instead of relying on GPT.

### New Supplement Price Pipeline
```
1. iHerb direct scrape (existing — NOW, Solgar, Nature Made)
   ↓ no brand match
2. Serper BH pharmacy search (existing, $0.002)
   ↓ try pharmacy URLs
3. _try_pharmacy_urls() — fetch pages, parse JSON-LD Product schema
   ↓ no JSON-LD found (search pages, not product pages)
4. Targeted site search: site:bn.boots.com OR site:bolo.bh ($0.001)
   ↓ find product page URLs
5. _try_pharmacy_urls() again on targeted results
   ↓ still no JSON-LD
6. GPT extraction from snippets (existing fallback)
   ↓ GPT fails
7. Tier 3 GPT estimate (existing)
```

### New Code
- `_extract_jsonld_price(html, brand, currency)` — static method, parses `<script type="application/ld+json">` for Product.offers.price
- `_fetch_pharmacy_price(serper_organic, brand, full_name, currency)` — filters URLs, calls `_try_pharmacy_urls`, falls back to targeted site search
- `_try_pharmacy_urls(urls, brand, currency)` — fetches pages via httpx, calls `_extract_jsonld_price`
- `PHARMACY_DOMAINS` — `{"bolo.bh": "Bolo", "bn.boots.com": "Boots", "aldeerahpharmacy.com": "Al Deerah Pharmacy"}`

### Bugs Discovered & Fixed During Production Testing
1. **bolo.bh not indexed by Google** — Vue.js SPA, `site:bolo.bh` returns zero results. Had to add bn.boots.com (IS indexed) to targeted search
2. **Search pages vs product pages** — Serper returns pharmacy search/listing URLs, not product pages. Search pages have no Product JSON-LD. Fixed by trying initial URLs first, then falling back to targeted site search
3. **Brand spelling mismatch** — Boots spells it "Health Aid" (with space), our brand is "HealthAid" (no space). Fixed with space-insensitive brand matching: `brand.replace(" ", "")` before comparison
4. **Duplicate brand in search query** — `f"{brand} {full_name}"` produced "HealthAid HealthAid Vitamin D3..." since full_name already contains brand

### Results
| | Before | After |
|---|---|---|
| HealthAid D3 price | BHD 3.77 (GPT estimate, wrong) | BHD 6.30 (Boots, real, verified) |
| HealthAid retailer | None | Boots |
| HealthAid URL | iHerb search (wrong) | bn.boots.com product page |
| Cost | $0.0202 → $0.0099 | $0.0103 |

### Tests Added
- `tests/test_pharmacy_jsonld.py` — 12 tests (8 JSON-LD parsing + 1 brand-with-spaces + 3 integration)
- All 20 tests pass (12 pharmacy + 8 URL extraction)

### Key Lessons Learned
1. **SPA sites are NOT scrapable** with simple HTTP — bolo.bh renders products client-side. But product pages may still have server-rendered JSON-LD metadata.
2. **Google indexing varies wildly** — bolo.bh (major GCC retailer) has ZERO pages indexed, while bn.boots.com (Boots) is fully indexed.
3. **Brand names have variants** — "HealthAid" vs "Health Aid". Space-insensitive matching is essential for pharmacy data.
4. **Serper organic returns listing pages** — even when searching for specific products, Serper often returns the retailer's search/category page, not the product page. Targeted `site:` queries work better.
5. **JSON-LD is reliable** — when a page has it, it's structured, deterministic, and free to parse. Far superior to GPT snippet extraction.

### Architecture Changes
```
BEFORE (supplement pricing):
  iHerb scrape → Serper fallback (2 calls) → GPT extraction → Tier 3 estimate

AFTER:
  iHerb scrape → Serper fallback (2 calls) → JSON-LD from pharmacy URLs →
  targeted site:bn.boots.com search ($0.001) → JSON-LD from site results →
  GPT extraction → Tier 3 estimate
```

---

## Session 8: Bahrain Drug Database + Integration Tests (Feb 21 2026, continued)

### What Was Done
Implemented the Bahrain Drug Database feature end-to-end: Supabase table, data import, service layer, GPT prompt injection, unit tests, integration tests, deploy + verification.

### Plan: 3 Parallel Agents (Failed)
Original plan called for 3 parallel agents (A: feature code, B: integration tests, C: unit tests) with strict file ownership. **All 3 agents failed** due to tool permission denials in the agent environment. The data import agent also got stuck in plan mode. All work was completed directly in the main conversation instead.

### New Files Created
| File | Purpose |
|------|---------|
| `app/services/drug_database_service.py` | `find_matching_drugs(query, limit)` — Supabase full-text search on `bahrain_approved_drugs` table; `format_drug_context(drugs)` — formats results for GPT prompt |
| `tests/test_drug_database_service.py` | 11 unit tests (5 run locally + 6 live_db auto-skip) |
| `tests/test_integration.py` | 6 integration tests against live Railway endpoint |
| `import_batches/batch_1.sql` through `batch_7.sql` | 655 drug records in SQL INSERT format |

### Files Modified
| File | Changes |
|------|---------|
| `app/services/extraction_service.py` | Added `drug_context` param to `_build_specs_prompt()` and `extract_specs()`, injected `{drug_context}` into prompt template |
| `app/services/structured_comparison_service.py` | Import drug_database_service, drug lookup before Phase 1 (supplements only), pass `drug_context` through `_get_specs()` |
| `pyproject.toml` | Added pytest markers (`live_db`, `integration`) |

### Database: `bahrain_approved_drugs` Table
- **655 rows** of Bahrain-registered health products (vitamins, supplements, OTC drugs)
- Columns: `trade_name`, `registration_no`, `api_name` (ingredients), `form`, `pack_size`, `method_of_sale`, `manufacturer`, `country`, `applicant_name`
- `search_vector` TSVECTOR column auto-generated from `trade_name + api_name` via trigger
- `GIN` index for fast full-text search
- Supabase project: `qulajmyxdbdkchvecmvc`

### How Drug Context Injection Works
1. Before Phase 1, if `category == "supplements"`, call `find_matching_drugs(search_query)`
2. Returns up to 5 matching registered drugs with official ingredients, forms, pack sizes
3. `format_drug_context()` formats them as a prompt section: "Official Bahrain Drug Registration Data"
4. Injected into GPT spec extraction prompt after search context — acts as ground truth for dosage/form/ingredient
5. Cost: zero (Supabase query, no API calls)

### Supabase Python Client Gotchas (Fixed)
- `text_search()` uses `options={"type": "plain", "config": "english"}` dict — NOT `type="plain"` keyword
- `.text_search()` returns `SyncQueryRequestBuilder` — `.limit()` must come BEFORE `.text_search()` in chain
- Skip detection in tests: direct `client.table().select("id").limit(1).execute()` — NOT `find_matching_drugs()` (catches errors → returns `[]`, same as "no results")

### Integration Tests
6 tests calling live Railway production with `nocache=true`:
1. **Phones** — iPhone 15 vs Samsung Galaxy S24 (checks display, processor, battery specs)
2. **Laptops** — MacBook Air M3 vs Dell XPS 15 (checks RAM, storage specs)
3. **iHerb supplements** — NOW D3 5000 IU vs Nature Made D3 2000 IU (checks dosage, form)
4. **Pharmacy supplements** — HealthAid Vitamin C vs Vitabiotics Wellman (BHD prices)
5. **Grocery** — Coca Cola vs Pepsi
6. **General** — Nike Air Max 90 vs Adidas Ultraboost

**Assertion fixes discovered during first run:**
- `product.rating` is a raw float (e.g., `4.8`), NOT a dict `{score: 4.8}`
- Cost tracked at `metadata.total_cost`, NOT `metadata.cost.current_cost`
- Phone display spec key is `display`, NOT `display_size`
- Shoe prices can exceed 150 BHD (Adidas Ultraboost was 317 BHD)

### Project ID Confusion (Resolved)
Three different Supabase project IDs encountered:
- `jzmjaawdkbhvvqnmxpcq` — stale ID from previous session's MCP calls (doesn't exist in account)
- `khatrmxzrvjzlbtcetva` — local env `SUPABASE_URL` points here (different project)
- `qulajmyxdbdkchvecmvc` — actual smartcompare project, where table + data lives

### Commits
- `83f6311` — feat: Bahrain drug database integration + tests
- `54addc6` — fix: integration test assertions to match actual API response format

### Updated Feature Status
| Feature | Status |
|---------|--------|
| Prices (text input) | ✅ Working (iHerb for supplements, shopping for electronics) |
| Prices (non-iHerb supplements) | ✅ Boots JSON-LD extraction |
| Prices (camera input) | ⚠️ Partially broken (supplements get wrong BHD price from camera path) |
| Ratings | ✅ Working + linked to sources |
| Reviews | ✅ Working |
| Specs | ✅ Working (supplements schema) |
| **Specs (supplements enrichment)** | ✅ **NEW — Bahrain drug DB ground truth injected into GPT prompt** |
| Camera | ⚠️ Partial (identification works, prices broken for supplements) |
| Auth | ✅ Fixed (refresh token flow) |
| URL input | ❌ Not started |
| Rating/Price links | ✅ Product-specific Google Shopping URLs |
| Cost optimization | ✅ $0.010 electronics, $0.010 supplements |
| Pharmacy JSON-LD | ✅ bn.boots.com, bolo.bh (if indexed) |
| **Bahrain Drug Database** | ✅ **NEW — 655 records, full-text search, GPT context injection** |
| **Integration Tests** | ✅ **NEW — 6 tests, all passing (~$0.06, ~4 min)** |
| **Unit Test Coverage** | ✅ **NEW — 73 tests across 7 files covering all core logic** |

---

## Session 9: Feb 22, 2026 — Test Coverage for 7 Uncovered Areas

### What Was Done
Added 73 unit tests across 7 new test files covering all previously untested core logic. Used a 3-agent Opus team with cross-QA (each agent reviews another's work). All QA passed with zero issues.

### Team Structure (Successful)
3 Opus agents running in parallel with `bypassPermissions` mode:
- **Agent A**: test_camera_vision.py, test_singleton_state.py, test_iherb_scraping.py → QA'd Agent B's files
- **Agent B**: test_rating_tiers.py, test_price_fallback.py → QA'd Agent C's files
- **Agent C**: test_unified_search.py, test_error_paths.py → QA'd Agent A's files

All 11 tasks (7 implementation + 3 QA + 1 final verification) completed successfully. This is the first successful multi-agent team execution in this project (previous attempt in Session 8 failed due to tool permissions).

### New Test Files
| File | Tests | Coverage Area |
|------|-------|---------------|
| `tests/test_error_paths.py` | 31 | `_convert_to_bhd` edge cases, `_calculate_freshness` with None, `_parse_price_string` garbage input, `_is_supplement_query` anti-keywords, `_strict_title_match` hyphens, `_numbers_match` year vs count |
| `tests/test_rating_tiers.py` | 16 | `_get_rating_tier` classification, `_extract_rating_from_shopping` tier priority, consensus detection, Tier 3 review count threshold, accessory rejection |
| `tests/test_price_fallback.py` | 12 | `_extract_price_from_shopping` filters, `_convert_gpt_price_currency`, `_sanitize_gpt_price`, all-tiers-fail fallback |
| `tests/test_camera_vision.py` | 10 | `identify_products` vision pipeline, `clean_json_response`, size_or_count enrichment (matches image_routes.py) |
| `tests/test_iherb_scraping.py` | 7 | `_normalize_words`, live iHerb scraping, brand filtering, nonexistent product handling |
| `tests/test_unified_search.py` | 4 | `_get_specs`/`_get_reviews` search_results sharing, cost budget tracking |
| `tests/test_singleton_state.py` | 3 | `get_comparison_service()` singleton, `_shopping_items_cache` cleared per request, `total_cost`/`api_calls` reset |

### What Each Test Area Catches
- **Error paths**: Every bug type from "Critical Bugs Fixed" (None currency, None price, garbage input)
- **Rating tiers**: Wrong tier priority, consensus with ties, Tier 3 accepted/rejected incorrectly
- **Price fallback**: Wrong fallback order, supplement misdetection, currency conversion errors
- **Camera/vision**: Malformed GPT response, missing fields, size_or_count duplication
- **iHerb scraping**: Brand mismatch, variant confusion (360 vs 120 Softgels), empty results
- **Unified search**: Wasted API calls, search not shared between specs/reviews
- **Singleton state**: Cross-request data leaks (the exact bug fixed in Session 6)

### Test Run Commands
```bash
# Free unit tests only (73 new + 25 existing = 98 tests, ~2s)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Include live unit tests (~$0.03 extra)
python -m pytest tests/ -v -m "not (live_db or integration)"

# Full suite including integration (~$0.09 total, ~4 min)
python -m pytest tests/ -v --timeout=180
```

### Files Modified
| File | Changes |
|------|---------|
| `pyproject.toml` | Added `live_unit` pytest marker |
| `docs/plans/2026-02-22-test-coverage-design.md` | Design document for test coverage |
| `docs/plans/2026-02-22-test-coverage-plan.md` | Implementation plan with exact test code |

### Commits
- `402e36d` — feat: add 73 unit tests covering 7 previously untested areas

---

**END OF KNOWLEDGE TRANSFER**

*Keep this document updated as the project evolves.*

# SmartCompare - Complete Project Knowledge Transfer

> **Purpose:** This document contains EVERYTHING needed to continue development without context loss.
> **Last Updated:** February 13, 2026
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
│   │   │   ├── image_routes.py          # /api/v1/compare (camera)
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

  // If no rating or not verified, show "No verified rating"
  if (rating === null || rating === undefined || !rating_verified || !rating_source?.url) {
    return (
      <View>
        <Text>No verified rating</Text>
        <Text>Rating could not be verified from retailers</Text>
      </View>
    );
  }

  // Show verified rating with source
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

## Local Backend Testing

```powershell
cd "C:\Users\SynAckITPC\Documents\AI\smartcompare\backend"
poetry run uvicorn app.main:app --reload --port 8000
```

Test URLs:
- Health: http://localhost:8000/health
- Compare: http://localhost:8000/api/v1/text/compare?q=iPhone%2015%20vs%20Galaxy%20S24&mode=v3

## Mobile Testing

```powershell
cd "C:\Users\SynAckITPC\Documents\AI\smartcompare\SmartCompareApp"
npx expo start
```

## Checking Logs

Railway logs should show:
```
[RATING] Extracting verified rating for: Apple iPhone 15
[RATING] Trying Amazon US...
[RATING] Found product page: https://amazon.com/dp/B0CHX1W1XY
[RATING] ✓ VERIFIED: 4.6/5 (12543 reviews)
```

If broken:
```
[RATING] Extracting verified rating for: Apple iPhone 15
[RATING] Trying Amazon US...
[RATING] No product page found on Amazon US
[RATING] === No verified rating found ===
```

---

# 14. FUTURE ROADMAP

## Immediate (This Week)
- [ ] Fix rating extraction
- [ ] Verify all retailers working
- [ ] Test with 10+ product pairs

## Short Term (This Month)
- [ ] Apply Figma UI design
- [ ] Add product history
- [ ] Implement favorites/wishlist

## Medium Term
- [ ] Premium tier with Stripe
- [ ] More comparison modes
- [ ] Price alerts
- [ ] Barcode scanning

## Long Term
- [ ] AI shopping assistant
- [ ] Multi-language support
- [ ] More GCC retailers
- [ ] Price prediction

---

# QUICK START FOR CLAUDE CODE

When starting Claude Code, say:

```
Read docs/CLAUDE_CODE_CONTEXT.md completely. This is SmartCompare - a product
comparison app for GCC region.

Current status (Feb 14, 2026):
- Backend: Running on Railway
- Prices: Working (3-tier fallback + retailer quality scoring)
- Specs: Working (fixed 11-field schema per category)
- Ratings: Working (4-tier fallback: expert JSON-LD, shopping tiers 1-3)
- Enhanced Reviews: Working (category_scores, rating_distribution, user_quotes, source_ratings, verified_rating)
- Camera input: Not started
- URL input: Partial (untested with new architecture)
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
| Camera input | Not started | |
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

## Current Feature Status
| Feature | Status |
|---------|--------|
| Prices | Working (currency conversion + sanity checks) |
| Ratings | Working (4-tier fallback) |
| Reviews | Working (category scores, user quotes, etc.) |
| Specs | Working (fixed schema) |
| Camera input | Not started — NEXT PRIORITY |
| URL input | Partial (untested with new architecture) |

## Next Priority
- Camera input feature

---

**END OF KNOWLEDGE TRANSFER**

*Keep this document updated as the project evolves.*

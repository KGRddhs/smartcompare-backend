# SmartCompare - Complete Project Knowledge Transfer

> **Purpose:** This document contains EVERYTHING needed to continue development without context loss.
> **Last Updated:** February 11, 2025, ~6:30 PM GST
> **Author:** Transferred from Claude.ai conversation (Days 1-7)

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
│              RATING EXTRACTION (Deterministic)                       │
│  1. Find product page on Amazon/Newegg/BestBuy                       │
│  2. Fetch actual HTML page                                           │
│  3. Parse JSON-LD/schema.org AggregateRating                         │
│  4. Return rating + source_url (REQUIRED)                            │
│  ** CURRENTLY BROKEN - Returns null **                               │
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

## 4.3 Rating Extractor (rating_extractor.py) - BROKEN

### Design Intent
```python
async def extract_rating_deterministic(product_name: str) -> ExtractedRating:
    """
    1. Find product page on supported retailers
    2. Fetch actual HTML page
    3. Parse JSON-LD schema.org/AggregateRating
    4. Return rating + review_count + source_url
    """
```

### Supported Retailers
```python
SUPPORTED_RETAILERS = {
    "amazon.com": {"name": "Amazon US", "search_query": "{product} site:amazon.com"},
    "amazon.ae": {"name": "Amazon UAE", "search_query": "{product} site:amazon.ae"},
    "newegg.com": {"name": "Newegg", "search_query": "{product} site:newegg.com"},
    "bestbuy.com": {"name": "Best Buy", "search_query": "{product} site:bestbuy.com"},
    "walmart.com": {"name": "Walmart", "search_query": "{product} site:walmart.com"},
    "bhphotovideo.com": {"name": "B&H Photo", "search_query": "{product} site:bhphotovideo.com"},
    "noon.com": {"name": "Noon", "search_query": "{product} site:noon.com"},
    "ubuy.com.bh": {"name": "Ubuy Bahrain", "search_query": "{product} site:ubuy.com.bh"},
}
```

### Extraction Methods (in order)
1. **JSON-LD** - `<script type="application/ld+json">` containing AggregateRating
2. **Microdata** - `itemprop="ratingValue"` attributes
3. **Meta tags** - `<meta property="product:rating:value">`
4. **CSS Selectors** - Site-specific patterns

### CURRENT PROBLEM
The rating extractor returns null for all products. Possible causes:
- Product pages not being found (search issue)
- Pages fetched but blocked (bot protection)
- JSON-LD not being parsed correctly
- BeautifulSoup parsing issue

### Required Fix
Debug by checking Railway logs for `[RATING]` messages:
```
[RATING] Starting deterministic extraction for: iPhone 15
[RATING] Trying Amazon US...
[RATING] Found product page: https://...  (or "No product page found")
[RATING] Fetching page...
[RATING] Parsing JSON-LD...
[RATING] ✓ SUCCESS or ✗ Failed
```

## 4.4 Cost Structure

| Operation | Cost |
|-----------|------|
| Serper search (per call) | $0.001 |
| GPT-4o-mini extraction | $0.001 |
| Full v3 comparison (2 products) | $0.005-0.008 |
| With global fallbacks | +$0.003 |
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
interface Product {
  name: string;
  brand: string;
  price: {
    amount: number | null;
    currency: string;
    retailer?: string;
    estimated?: boolean;
    note?: string;
  };
  specs: Record<string, any>;
  rating: number | null;           // 1-5 or null
  review_count: number | null;
  rating_verified: boolean;        // true only if source_url exists
  rating_source: {
    name: string;                  // "Amazon US"
    url: string;                   // "https://amazon.com/dp/..."
    extract_method: string;        // "json_ld", "microdata", etc.
    retrieved_at: string;          // ISO timestamp
  } | null;
  pros: string[];
  cons: string[];
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

## CRITICAL: Ratings Not Working

**Symptom:** All products show "No verified rating"

**Expected behavior:**
1. Find product page on Amazon/Newegg
2. Fetch HTML
3. Parse JSON-LD for AggregateRating
4. Show: ⭐ 4.6 (12,543 reviews) via Amazon US [link]

**What's happening:**
- `rating_extractor.py` returns `ExtractedRating()` (empty)
- All products have `rating: null`, `rating_verified: false`

**Debug steps needed:**
1. Check Railway logs for `[RATING]` lines
2. Is `find_product_page()` finding URLs?
3. Is `fetch_page_content()` getting HTML?
4. Is `extract_from_json_ld()` parsing correctly?

**Possible causes:**
- Serper search not returning product pages
- Bot protection blocking page fetch
- JSON-LD structure different than expected
- BeautifulSoup parsing issue

**Files to check:**
- `backend/app/services/rating_extractor.py`
- `backend/app/services/comparison_service_v3.py` (lines ~1440-1480)

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

Current status:
- Backend: Running on Railway ✅
- Prices: Working ✅  
- Specs: Working ✅
- Ratings: BROKEN ❌ (shows "No verified rating" for everything)

The rating_extractor.py should fetch real product pages and parse JSON-LD 
AggregateRating, but it's returning null.

Help me debug and fix the rating extraction.
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

**END OF KNOWLEDGE TRANSFER**

*Keep this document updated as the project evolves.*

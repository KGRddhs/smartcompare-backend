# SmartCompare — Architecture & Design

# IMPORTANT: CURRENT DATE CONTEXT

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

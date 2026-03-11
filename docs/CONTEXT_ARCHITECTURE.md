# SmartCompare — Architecture & Design

# IMPORTANT: CURRENT DATE CONTEXT

**Today's date: March 2026**

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
├── app/                                 # ROOT — deployed code (Railway runs this!)
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entry + middleware stack
│   ├── api/
│   │   ├── __init__.py
│   │   ├── text_routes.py               # /api/v1/text/* endpoints (rate limited)
│   │   ├── url_routes.py                # /api/v1/url/* endpoints
│   │   ├── image_routes.py              # /api/v1/image/* (camera, HEIC detection)
│   │   ├── auth_routes.py               # /api/v1/auth/* (login, register, profile, social-login)
│   │   ├── admin_routes.py              # /api/v1/admin/* analytics (X-Admin-Key auth)
│   │   └── routes.py                    # /api/v1/compare (legacy, broken)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py                # X-Request-ID generation/propagation
│   │   ├── security.py                  # Security headers (nosniff, DENY, etc.)
│   │   ├── rate_limiter.py              # slowapi rate limiter (10/min on compare)
│   │   ├── error_handler.py             # Global error handler (clean 500 JSON)
│   │   └── logging_config.py            # Structured JSON logging
│   └── services/
│       ├── __init__.py
│       ├── structured_comparison_service.py  # MAIN — orchestrator, pricing, ratings
│       ├── extraction_service.py        # GPT prompts, spec/review extraction
│       ├── serper_service.py            # Serper API (search, shopping)
│       ├── cache_service.py             # Upstash Redis caching
│       ├── database_service.py          # Supabase client + history/logging
│       ├── drug_database_service.py     # Bahrain drug DB lookup
│       ├── openai_service.py            # GPT-4o-mini vision
│       ├── sentry_service.py            # Sentry init (opt-in via SENTRY_DSN)
│       └── analytics_service.py         # Admin analytics queries
│
├── backend/app/                         # OLD — NOT deployed. Do NOT edit.
│
├── SmartCompareApp/                     # React Native mobile app
│   ├── src/
│   │   ├── screens/
│   │   │   ├── HomeScreen.tsx           # Main input screen (gear icon → AccountScreen)
│   │   │   ├── ResultsScreen.tsx        # Comparison results
│   │   │   ├── CameraScreen.tsx         # Camera capture + identify
│   │   │   ├── HistoryScreen.tsx        # Comparison history (401 → sign-in prompt)
│   │   │   ├── AccountScreen.tsx        # Account panel (name/email edit, password, social accounts)
│   │   │   ├── LoginScreen.tsx          # Email login + Google/Apple sign-in + inline validation
│   │   │   └── RegisterScreen.tsx       # Email register + Google/Apple sign-in + inline validation
│   │   ├── services/
│   │   │   ├── api.ts                   # Axios config + auth interceptors + JPEG transcoding
│   │   │   └── authService.ts           # Supabase auth + Google/Apple sign-in
│   │   ├── components/
│   │   │   └── ...
│   │   └── types/
│   │       └── index.ts
│   ├── App.tsx
│   ├── app.json                         # EAS plugins: expo-camera, expo-image-picker, expo-image-manipulator, google-signin, apple-auth
│   └── package.json
│
├── tests/                               # 18 test files, 366 tests
│   ├── conftest.py                      # Auto-loads .env for all tests
│   ├── test_auth_interceptor.py         # 93 tests (was 45 — added social login, profile, MIME)
│   ├── test_fact_checking.py            # 48 tests
│   ├── test_error_paths.py              # 31 tests
│   ├── test_analytics.py               # 30 tests
│   ├── test_camera_vision.py           # 26 tests (was 10 — added HEIC detection/rejection)
│   ├── test_observability.py            # 24 tests
│   ├── test_security_middleware.py      # 16 tests
│   ├── test_rating_tiers.py            # 16 tests
│   ├── test_price_fallback.py          # 12 tests
│   ├── test_pharmacy_jsonld.py         # 12 tests
│   ├── test_drug_database_service.py   # 11 tests
│   ├── test_history.py                 # 10 tests
│   ├── test_db_improvements.py         # 9 tests
│   ├── test_url_extraction.py          # 8 tests
│   ├── test_iherb_scraping.py          # 7 tests
│   ├── test_unified_search.py          # 4 tests
│   ├── test_singleton_state.py         # 3 tests
│   └── test_integration.py            # 6 integration tests (live Railway)
│
├── .github/workflows/ci.yml            # GitHub Actions CI pipeline
├── docs/                                # Context docs, plans, designs
├── migrations/                          # SQL migration files
├── requirements.txt                     # ROOT — Railway reads this!
├── pyproject.toml
├── .gitignore
└── README.md
```

---

# 4. BACKEND DEEP DIVE

## 4.1 Main Entry Point (main.py) — v2.1.0

```python
# Middleware stack (order matters: outermost added last in Starlette)
# Request flow: RequestID → SecurityHeaders → ErrorHandler → [CORS] → route handler
app.add_middleware(CORSMiddleware, ...)     # Innermost
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)      # Outermost

# Rate limiter (slowapi — decorator-based, not middleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routes registered
app.include_router(text_router)      # /api/v1/text/*
app.include_router(url_router)       # /api/v1/url/*
app.include_router(image_router)     # /api/v1/image/*
app.include_router(auth_router)      # /api/v1/auth/*
app.include_router(admin_router, prefix="/api/v1/admin")  # /api/v1/admin/*

# Sentry (opt-in): init_sentry() — no-op if SENTRY_DSN not set
# Structured logging: configure_logging() — JSON format, quiets noisy libs
```

## 4.2 Auth Endpoints (auth_routes.py)

```python
# Existing endpoints
POST /api/v1/auth/login         # Email + password login
POST /api/v1/auth/register      # Email + password registration
POST /api/v1/auth/refresh       # Refresh token → new access token
GET  /api/v1/auth/me            # Get current user (requires auth)

# New in Session 15
PUT  /api/v1/auth/profile       # Update display name (requires auth)
PUT  /api/v1/auth/email         # Update email (triggers Supabase verification)
PUT  /api/v1/auth/password      # Change password (current password required)
POST /api/v1/auth/social-login  # Google/Apple idToken → Supabase signInWithIdToken
```

### Social Login Flow
1. Frontend calls native Google/Apple SDK to get `idToken`
2. Frontend sends `POST /auth/social-login` with `{ provider: "google"|"apple", id_token: "..." }`
3. Backend calls `supabase.auth.sign_in_with_id_token(provider, id_token)`
4. Supabase creates user if new, returns session
5. Backend returns `{ user, session }` — frontend stores tokens same as email login

### HEIC Image Detection (image_routes.py)
`_detect_mime_type(file_bytes)` reads magic bytes to detect:
- JPEG (`FF D8 FF`)
- PNG (`89 50 4E 47`)
- WebP (`52 49 46 46` + `57 45 42 50`)
- GIF (`47 49 46 38`)
- HEIC/HEIF (`66 74 79 70` at offset 4 — `heic`, `heix`, `mif1`, `msf1`)
- Returns `None` for unsupported formats → 400 error response

Frontend also transcodes via `expo-image-manipulator` to JPEG before upload (belt-and-suspenders).

## 4.3 Comparison Service v3 (comparison_service_v3.py)

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
const API_BASE_URL = 'https://web-production-58776.up.railway.app';

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
- `signInWithGoogle()` - Native Google Sign-In SDK → `POST /auth/social-login`
- `signInWithApple()` - Native Apple Authentication with nonce → `POST /auth/social-login`
- `updateProfile(displayName)` - `PUT /auth/profile`
- `updateEmail(newEmail)` - `PUT /auth/email`
- `changePassword(currentPassword, newPassword)` - `PUT /auth/password`

Storage keys:
```typescript
const USER_STORAGE_KEY = '@smartcompare_user';
const TOKEN_STORAGE_KEY = '@smartcompare_token';
```

## 5.3 AccountScreen (AccountScreen.tsx)

New screen accessible via gear icon on HomeScreen:
- **Inline editing**: display name and email fields with edit/save/cancel buttons
- **Password change**: modal with current password, new password, confirm fields
- **Connected accounts**: Google and Apple connection buttons (shows "Connected" or "Connect")
- **Logout button**: clears all stored tokens and navigates to login

## 5.4 Input Validation (LoginScreen, RegisterScreen)

Inline per-field validation:
- Email: regex validation, shown on blur
- Password: minimum 6 characters
- Confirm password: must match (RegisterScreen only)
- Errors shown inline below each field in red text

## 5.5 Results Screen (ResultsScreen.tsx)

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

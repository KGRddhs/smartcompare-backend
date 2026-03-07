# SmartCompare — Database & API Reference

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

### users (Session 16, Mar 4 2026)
```sql
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT,
    auth_provider TEXT DEFAULT 'email',          -- 'email', 'google', 'apple'
    subscription_tier TEXT DEFAULT 'free',
    subscription_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
-- RLS: users read/update own row, service_role full access
```

### comparisons
```sql
CREATE TABLE comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    input_type TEXT NOT NULL DEFAULT 'text',
    product_names TEXT[] DEFAULT '{}',
    response_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
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

## Admin Analytics (protected by X-Admin-Key header)

### GET `/api/v1/admin/stats/daily`
Daily comparison stats (count, cost, avg duration) for last 30 days.

### GET `/api/v1/admin/stats/popular`
Top 20 most queried products.

### GET `/api/v1/admin/stats/costs`
Cost trends (daily total cost + avg per comparison) for last 30 days.

### GET `/api/v1/admin/stats/errors`
Error stats (count + recent error messages) for last 7 days.

### GET `/api/v1/admin/stats/products`
Product catalog stats (total count, top categories, recent additions).

**Auth:** All admin endpoints require `X-Admin-Key` header matching `ADMIN_API_KEY` env var.

## Health

### GET `/health`
```json
{"status": "healthy"}
```

# SmartCompare v3 Architecture
## Production-Grade Product Comparison System

---

## 🎯 Core Principle
**"Every comparison MUST return complete, actionable data. If a user needs to Google after using SmartCompare, we failed."**

---

## 📊 Data Requirements (Non-Negotiable)

Every product comparison MUST include:

| Field | Required | Fallback if Missing |
|-------|----------|---------------------|
| Product Name | ✅ YES | Error - cannot proceed |
| Brand | ✅ YES | Extract from name |
| Price | ✅ YES | "Price unavailable" + link to retailer |
| Currency | ✅ YES | Default to region currency |
| Specs (5+ fields) | ✅ YES | Generic category specs |
| Rating | ⚠️ Preferred | "No ratings found" |
| Review Count | ⚠️ Preferred | null |
| Pros (3+) | ✅ YES | Generate from specs |
| Cons (2+) | ✅ YES | Generate from specs |
| Image URL | ⚠️ Preferred | Placeholder |
| Retailer | ✅ YES | "Multiple sources" |
| In Stock | ⚠️ Preferred | null |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   📷 IMAGE          ⌨️ TEXT              🔗 URL             📊 BARCODE      │
│      │                 │                    │                    │          │
│      ▼                 ▼                    ▼                    ▼          │
│   Vision AI        Query Parser       URL Extractor      Barcode Lookup     │
│      │                 │                    │                    │          │
│      └─────────────────┴────────────────────┴────────────────────┘          │
│                                    │                                        │
│                                    ▼                                        │
│                         ┌─────────────────────┐                             │
│                         │  PRODUCT IDENTIFIER  │                             │
│                         │  (Canonical Name)    │                             │
│                         └─────────────────────┘                             │
│                                    │                                        │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE CHECK                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    Found & Fresh?    ┌─────────────────────┐             │
│   │  Supabase   │ ──────────────────▶  │  Return Cached Data │             │
│   │  Products   │        YES           │  (Cost: $0.00)      │             │
│   └─────────────┘                      └─────────────────────┘             │
│          │                                                                  │
│          │ NO (not found or stale)                                         │
│          ▼                                                                  │
└──────────┼──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA AGGREGATION LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                    PARALLEL DATA FETCHING                         │     │
│   │                                                                   │     │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │     │
│   │   │   SPECS     │  │   PRICES    │  │   REVIEWS   │             │     │
│   │   │   Search    │  │   Search    │  │   Search    │             │     │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │     │
│   │          │                │                │                     │     │
│   │          ▼                ▼                ▼                     │     │
│   │   ┌─────────────────────────────────────────────────────┐       │     │
│   │   │              MULTI-SOURCE STRATEGY                   │       │     │
│   │   │                                                      │       │     │
│   │   │  Source 1: Serper (Google Search)                   │       │     │
│   │   │  Source 2: Serper Shopping                          │       │     │
│   │   │  Source 3: Knowledge Graph                          │       │     │
│   │   │  Source 4: Database (previous extractions)          │       │     │
│   │   │  Fallback: AI Generation with [ESTIMATED] flag      │       │     │
│   │   │                                                      │       │     │
│   │   └─────────────────────────────────────────────────────┘       │     │
│   │                              │                                   │     │
│   └──────────────────────────────┼───────────────────────────────────┘     │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌─────────────────────────┐                             │
│                    │    DATA MERGER          │                             │
│                    │  (Best from all sources)│                             │
│                    └─────────────────────────┘                             │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    FIELD VALIDATOR                               │      │
│   │                                                                  │      │
│   │   □ Product Name    → Required (FAIL if missing)                │      │
│   │   □ Brand           → Required (extract from name if missing)   │      │
│   │   □ Price           → Required (retry different source)         │      │
│   │   □ Specs (5+)      → Required (use category defaults)          │      │
│   │   □ Pros (3+)       → Required (generate from specs)            │      │
│   │   □ Cons (2+)       → Required (generate from specs)            │      │
│   │   □ Rating          → Optional (mark as "No ratings")           │      │
│   │                                                                  │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌─────────────────────────┐                             │
│                    │   RETRY LOGIC           │                             │
│                    │   (If validation fails) │                             │
│                    └─────────────────────────┘                             │
│                                  │                                          │
│                    Missing price? → Try shopping search again              │
│                    Missing specs? → Try manufacturer site search           │
│                    Still missing? → Use AI estimation + flag               │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI ANALYSIS LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                 COMPARISON ENGINE (GPT-4o-mini)                  │      │
│   │                                                                  │      │
│   │   Input:                                                         │      │
│   │   - Validated Product 1 data                                    │      │
│   │   - Validated Product 2 data                                    │      │
│   │   - User's region                                               │      │
│   │   - Comparison context                                          │      │
│   │                                                                  │      │
│   │   Output:                                                        │      │
│   │   - Winner (with reasoning)                                     │      │
│   │   - Value scores (0-10)                                         │      │
│   │   - Key differences (5)                                         │      │
│   │   - Best for categories                                         │      │
│   │   - Final recommendation                                        │      │
│   │                                                                  │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                      SUPABASE DATABASE                            │     │
│   │                                                                   │     │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │     │
│   │   │  products   │  │   prices    │  │   specs     │             │     │
│   │   │  (master)   │  │  (by date)  │  │  (by prod)  │             │     │
│   │   └─────────────┘  └─────────────┘  └─────────────┘             │     │
│   │                                                                   │     │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │     │
│   │   │   reviews   │  │ comparisons │  │  searches   │             │     │
│   │   │  (cached)   │  │  (cached)   │  │   (logs)    │             │     │
│   │   └─────────────┘  └─────────────┘  └─────────────┘             │     │
│   │                                                                   │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│   Benefits:                                                                 │
│   - Instant cache hits ($0.00 cost)                                        │
│   - Price history tracking                                                  │
│   - Improved results over time                                             │
│   - Analytics and insights                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                  RESPONSE FORMATTER                              │      │
│   │                                                                  │      │
│   │   {                                                              │      │
│   │     "success": true,                                            │      │
│   │     "products": [                                               │      │
│   │       {                                                         │      │
│   │         "name": "iPhone 15",                                    │      │
│   │         "brand": "Apple",                                       │      │
│   │         "price": { "amount": 299, "currency": "BHD" },         │      │
│   │         "specs": { ... 6+ fields ... },                        │      │
│   │         "rating": 4.5,                                         │      │
│   │         "pros": ["pro1", "pro2", "pro3"],                      │      │
│   │         "cons": ["con1", "con2"],                              │      │
│   │         "data_quality": {                                       │      │
│   │           "completeness": 95,                                  │      │
│   │           "sources": ["serper", "shopping", "db"],             │      │
│   │           "confidence": "high"                                 │      │
│   │         }                                                       │      │
│   │       }                                                         │      │
│   │     ],                                                          │      │
│   │     "comparison": { ... },                                      │      │
│   │     "metadata": { cost, time, cache_hit }                       │      │
│   │   }                                                             │      │
│   │                                                                  │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Database Schema (Supabase)

### Table: products
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL,
    category TEXT NOT NULL,
    variants JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_name ON products(canonical_name);
CREATE INDEX idx_products_brand ON products(brand);
```

### Table: product_specs
```sql
CREATE TABLE product_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    specs JSONB NOT NULL,
    source TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

CREATE INDEX idx_specs_product ON product_specs(product_id);
```

### Table: product_prices
```sql
CREATE TABLE product_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    region TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    retailer TEXT,
    url TEXT,
    in_stock BOOLEAN,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX idx_prices_product_region ON product_prices(product_id, region);
CREATE INDEX idx_prices_recorded ON product_prices(recorded_at DESC);
```

### Table: product_reviews
```sql
CREATE TABLE product_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    average_rating DECIMAL(2,1),
    total_reviews INTEGER,
    pros JSONB DEFAULT '[]',
    cons JSONB DEFAULT '[]',
    summary TEXT,
    source TEXT,
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

CREATE INDEX idx_reviews_product ON product_reviews(product_id);
```

### Table: comparisons_cache
```sql
CREATE TABLE comparisons_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_ids UUID[] NOT NULL,
    region TEXT NOT NULL,
    comparison_result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX idx_comparisons_products ON comparisons_cache USING GIN(product_ids);
```

### Table: search_logs
```sql
CREATE TABLE search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    query TEXT NOT NULL,
    input_type TEXT NOT NULL,
    products_found JSONB,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    cost DECIMAL(6,4),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_created ON search_logs(created_at DESC);
CREATE INDEX idx_logs_success ON search_logs(success);
```

---

## 🔄 Data Flow: Complete Comparison

```
1. USER INPUT
   "iPhone 15 vs Galaxy S24"
   
2. PARSE → ["Apple iPhone 15", "Samsung Galaxy S24"]

3. FOR EACH PRODUCT:
   
   a. CHECK DATABASE
      → Found fresh data? Return immediately
      → Not found or stale? Continue to search
   
   b. PARALLEL SEARCH (async)
      ├─ Serper: "{product} specs features"
      ├─ Serper Shopping: "{product}"
      └─ Serper: "{product} review rating"
   
   c. AI EXTRACTION (single call)
      → Extract: name, brand, price, specs, rating, pros, cons
      → From all search results combined
   
   d. VALIDATE
      → Check all required fields present
      → Missing critical data? Retry with different query
      → Still missing? Use defaults + flag
   
   e. SAVE TO DATABASE
      → Cache for future requests

4. COMPARE
   → AI compares both products
   → Generate winner, differences, recommendation

5. SAVE COMPARISON
   → Cache comparison result

6. RETURN RESPONSE
   → Complete, validated JSON
```

---

## 🎯 Quality Guarantees

### Response Completeness Checklist

Before returning ANY response, verify:

```python
def validate_product(product: dict) -> bool:
    required = {
        "name": lambda x: len(x) > 2,
        "brand": lambda x: len(x) > 1,
        "price": lambda x: x is not None and x > 0,
        "specs": lambda x: len(x) >= 3,
        "pros": lambda x: len(x) >= 2,
        "cons": lambda x: len(x) >= 1,
    }
    
    for field, validator in required.items():
        if field not in product or not validator(product[field]):
            return False
    
    return True
```

### Fallback Strategy

| Missing Data | Fallback Action |
|--------------|-----------------|
| Price | Search "{product} price {region}" → Shopping API → "Check retailer" |
| Specs | Search "{product} specifications" → Category defaults |
| Rating | Search "{product} review" → "No ratings available" |
| Pros | Generate from specs using AI |
| Cons | Generate from specs using AI |

---

## 📈 Learning System

### How Results Improve Over Time

1. **Cache Growth**
   - Each search adds to database
   - Repeated products = instant response
   - Cost drops to $0 for cached products

2. **Price History**
   - Track prices over time
   - Show trends: "Price dropped 15% last month"
   - Alert on deals

3. **Search Pattern Learning**
   - Track which queries succeed
   - Learn product aliases
   - Improve parsing accuracy

4. **Quality Feedback**
   - Track comparison usage
   - User feedback integration
   - Flag low-quality extractions

---

## 💰 Cost Structure

### Per Comparison (No Cache)

| Component | Lite Mode | Full Mode |
|-----------|-----------|-----------|
| Parse query | $0.0003 | $0.0003 |
| Search (per product) | $0.002 | $0.004 |
| Extraction (per product) | $0.0008 | $0.002 |
| Comparison | $0.0005 | $0.001 |
| **Total (2 products)** | **$0.005** | **$0.012** |

### With Cache (Repeat Product)

| Component | Cost |
|-----------|------|
| Database lookup | $0.00 |
| Comparison only | $0.0005 |
| **Total** | **$0.0005** |

### Monthly Projections

| Usage | No Cache | 50% Cache | 80% Cache |
|-------|----------|-----------|-----------|
| 1,000 comparisons | $5-12 | $3-7 | $1.50-3 |
| 10,000 comparisons | $50-120 | $30-70 | $15-30 |

---

## 🚀 Implementation Priority

### Phase 1: Core Fixes (Today)
1. ✅ Implement validation layer
2. ✅ Add fallback strategies
3. ✅ Ensure complete responses

### Phase 2: Database Integration (Next)
1. Create Supabase tables
2. Implement caching layer
3. Store search results

### Phase 3: Learning System
1. Track search logs
2. Price history
3. Improve with usage

### Phase 4: Fine-Tuning
1. Custom model training
2. Category-specific prompts
3. Regional optimization

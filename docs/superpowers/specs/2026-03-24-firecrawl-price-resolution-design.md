# Design Spec: Multi-Layer Price Resolution with Firecrawl + Cascade Hardening

**Date:** 2026-03-24
**Status:** Draft
**Problem:** Luxury brand SPAs (Louis Vuitton, Chanel, Hermes, Gucci, Dior, Prada) and brand-exclusive products load prices via async XHR/GraphQL after React/Vue hydration. Cloudflare Browser Rendering and Microlink both render HTML successfully but find zero price data in the DOM. Current result: "estimated price" shown to users instead of real scraped prices.

**Session 30 findings:** Cloudflare `/content` endpoint works (fixed token permissions), but rendered HTML contains empty price containers. `/scrape` with 13 CSS selector types returns 0 hits. Root cause confirmed: prices loaded via XHR, not in DOM.

## Solution Overview

Replace Cloudflare Browser Rendering + Microlink with **Firecrawl** (primary, Smart Wait for SPA content) and **Scrape.do** (fallback renderer). Add cascade hardening: circuit breakers, credit tracking, input validation, cost observability.

## Pre-Implementation Validation Spike

**BEFORE any code is written**, manually test Firecrawl against 3 luxury URLs to confirm Smart Wait captures XHR-loaded prices:

1. Sign up at firecrawl.dev, get API key
2. Test these URLs via curl:
   - `https://us.louisvuitton.com/eng-us/products/neverfull-mm-monogram-nvprod4900001v`
   - `https://www.dior.com/en_us/fashion/products/M0455CBAA_M900` (Lady Dior bag)
   - `https://www.chanel.com/us/fashion/handbags/` (any product page)
3. Check if returned markdown/HTML contains price data

```bash
curl -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://us.louisvuitton.com/eng-us/products/neverfull-mm-monogram-nvprod4900001v", "formats": ["markdown", "html"]}'
```

**Decision gate:**
- If prices found in 2+ of 3 URLs → proceed with Firecrawl as Tier 1.5a
- If prices found in 0-1 URLs → Firecrawl still useful for non-luxury brands; deprioritize Tier 1.5a for luxury, focus on GCC retailer expansion instead

This spike costs 3 Firecrawl credits (~0.6% of free budget). Document results before proceeding.

## Architecture: Gated Price Cascade

```
_get_price(self, brand, name, variant, region, search_query, nocache, category)
│
├─ Gate 0: Input validation
│   ├─ brand + name combined: 3-200 chars, must start with letter
│   ├─ region: must map to valid currency in CURRENCY_SYMBOLS
│   └─ REJECT → return None (no API calls wasted)
│
├─ Gate 1: Cache check (existing Redis, unchanged)
│   └─ HIT → return cached price, STOP
│
├─ Tier 1: Serper Shopping (existing, $0.001)
│   └─ FOUND → return, STOP cascade
│
├─ Gate 2: Should we try page scraping?
│   ├─ ENABLE_PAGE_SCRAPE must be true
│   ├─ Must have official domain OR be luxury brand OR have brand-exclusive signal
│   └─ FAIL any gate → skip to Tier 2
│
├─ Tier 1.5a: Firecrawl on official brand URL (NEW)
│   ├─ Pre-check: circuit_breaker("firecrawl").is_closed?
│   ├─ Pre-check: credit_tracker("firecrawl").has_budget?
│   ├─ Pre-check: _validate_scrape_url(url)?
│   ├─ Call: Firecrawl scrape API with Smart Wait
│   ├─ FOUND → return, STOP
│   ├─ 429/503 → circuit_breaker.record_failure("firecrawl")
│   └─ No price → continue (NOT an error, don't trip breaker)
│
├─ Tier 1.5b: Authorized retailers via curl_cffi (existing, $0.001 Serper)
│   └─ FOUND → return, STOP
│
├─ Tier 1.5c: GCC retailers via curl_cffi (existing, $0.001 Serper)
│   └─ FOUND → return, STOP
│
├─ Tier 1.5d: Scrape.do rendering fallback (NEW)
│   ├─ ONLY fires if: URLs were found in 1.5b/c where curl_cffi got HTTP 200
│   │   but _extract_price_from_html() returned None (not timeouts/connection errors)
│   ├─ Pre-check: circuit_breaker("scrapedo").is_closed?
│   ├─ Pre-check: credit_tracker("scrapedo").has_budget?
│   ├─ URL selection: from failed_curl_urls, max 2, GCC retailers first
│   ├─ Call: Scrape.do render=true on selected URLs
│   ├─ FOUND → return, STOP
│   └─ 429/503 → circuit_breaker.record_failure("scrapedo")
│
├─ Tier 2: GPT extraction from search context (existing, ~$0.003)
│   └─ FOUND → return (not tagged estimated)
│
└─ Tier 3: GPT training data estimate (existing, $0, tagged estimated=true)
```

### Key Cascade Rules (Leak Prevention)

1. **Early return at every tier** — the moment a valid price is found, STOP. No "just checking" downstream.
2. **Tier 1.5d is conditional** — only fires when curl_cffi found URLs but failed extraction. NOT a blind retry of all URLs.
3. **No parallel tier execution** — tiers run sequentially top-to-bottom. Parallel only WITHIN a tier (e.g., 1.5b fetches 3 retailer URLs in parallel).
4. **Budget exhaustion skips gracefully** — if Firecrawl credits are gone, skip to 1.5b. If Scrape.do credits are gone, skip to Tier 2. No errors, no retries.
5. **Time budget unchanged** — existing `TIER_15_BUDGET_TIMEOUT = 20s` still applies across all 1.5x tiers.

### Circuit Breaker Failure Taxonomy

| Response | Trip breaker? | Rationale |
|----------|--------------|-----------|
| 429 Too Many Requests | YES | Provider rate limit, back off |
| 503 Service Unavailable | YES | Provider is down |
| Timeout (>10s) | YES | Provider unresponsive |
| Connection refused | YES | Provider unreachable |
| 200 but no price in response | NO | Page rendered fine, just no price data — expected for some URLs |
| 404 Not Found | NO | Bad URL, not provider issue |
| 403 Forbidden | NO (but add domain to per-request skip list) | Site blocks scraper — domain-level issue, not provider-level |

### `source_method` Tags

| Tier | Tag | Description |
|------|-----|-------------|
| Tier 1 | `shopping_api` | Serper Shopping direct (existing) |
| Tier 1.5a | `firecrawl` | Firecrawl Smart Wait scrape (NEW) |
| Tier 1.5b/c | `page_scrape` | curl_cffi HTML extraction (existing) |
| Tier 1.5d | `scrapedo_rendered` | Scrape.do JS rendering (NEW) |
| Tier 2 | `gpt_extracted` | GPT extraction from search (existing) |
| Tier 3 | `estimated` | GPT training data (existing) |

## New Files

### `app/services/api_budget_service.py`

Singleton service managing credit tracking and circuit breakers for external APIs.

```python
# Provider configurations
PROVIDER_CONFIGS = {
    "firecrawl": {
        "monthly_limit": 450,        # 500 lifetime, save 50 buffer
        "warn_at": 400,
        "is_lifetime": True,         # Not monthly-resetting
    },
    "scrapedo": {
        "monthly_limit": 900,        # 1,000/mo free, save 100 buffer
        "warn_at": 800,
        "is_lifetime": False,
    },
    "serper": {
        "monthly_limit": 2200,       # 2,500 credits, save 300 buffer
        "warn_at": 2000,
        "is_lifetime": True,
    },
}

# Circuit breaker settings
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 3,          # 3 consecutive failures → trip
    "recovery_timeout_seconds": 600, # 10 min cooldown
    "half_open_max_calls": 1,        # 1 test call in half-open
}
```

**Storage:** Upstash Redis (existing in stack)
- `budget:{provider}:{YYYY-MM}` → integer counter (INCR, atomic)
- `budget:{provider}:lifetime` → integer counter (for Firecrawl/Serper)
- `circuit:{provider}` → JSON `{state, failure_count, last_failure_at, tripped_at}`

**Public API:**
- `has_budget(provider: str) -> bool` — check before calling
- `record_usage(provider: str, count: int = 1)` — after successful call
- `record_failure(provider: str)` — after 429/503/timeout
- `record_success(provider: str)` — resets failure count (half-open → closed)
- `is_circuit_closed(provider: str) -> bool` — check before calling
- `get_usage_summary() -> dict` — for admin dashboard

### `app/services/firecrawl_service.py`

Thin wrapper around Firecrawl's scrape API.

```python
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"

async def scrape_page_price(url: str, product_name: str, currency: str) -> Optional[dict]:
    """
    Scrape a URL via Firecrawl with Smart Wait for SPA content.
    Returns price dict compatible with existing pipeline or None.
    """
    # Firecrawl handles:
    # - JS rendering with Smart Wait (waits for DOM stability + network idle)
    # - Anti-bot bypass via managed browser pool
    # Returns markdown/HTML that we parse for price data
```

**Environment variable:** `FIRECRAWL_API_KEY` (required to enable Firecrawl tier)
**Graceful skip:** If `FIRECRAWL_API_KEY` not set, Tier 1.5a is skipped entirely (no errors).

### `app/services/scrapedo_service.py`

Thin wrapper around Scrape.do's rendering API.

```python
SCRAPEDO_API_URL = "https://api.scrape.do"

async def render_and_extract(url: str, product_name: str, currency: str) -> Optional[dict]:
    """
    Render URL via Scrape.do (render=true) and extract price from HTML.
    Reuses existing _extract_price_from_html() for JSON-LD/OG/microdata.
    """
```

**Environment variable:** `SCRAPEDO_API_TOKEN` (required to enable Scrape.do tier)
**Graceful skip:** If token not set, Tier 1.5d is skipped entirely.

## Modified Files

### `app/services/structured_comparison_service.py`

**Changes:**
1. Import `api_budget_service`, `firecrawl_service`, `scrapedo_service`
2. Add Gate 0 (`_validate_price_query()`) at top of `_get_price()`
3. Add Gate 2 (budget/circuit checks) before Tier 1.5
4. Replace Cloudflare/Microlink calls in `_fetch_page_price()` with Firecrawl
5. Add Tier 1.5d (Scrape.do) after 1.5c with conditional trigger
6. Track `failed_curl_urls` list during 1.5b/c for Scrape.do retry in 1.5d
7. Expand `GCC_LUXURY_RETAILERS` set with new retailers
8. Add URL validation (`_validate_scrape_url()`) before any page fetch

**Removals:**
- `_fetch_rendered_html()` — Cloudflare/Microlink rendering logic (replaced by Firecrawl/Scrape.do)
- `JS_ONLY_DOMAINS` — no longer needed (Firecrawl handles all JS rendering)
- References to `RENDER_PROVIDER`, `JS_RENDER_TIMEOUT` constants
- 3 diagnostic endpoints from `app/main.py` (`/health/render-test`, `/health/render-price-test`, `/health/scrape-test`)

**Kept unchanged:**
- `_curl_fetch_html()` — still used for static HTML sites (fast, free)
- `_extract_price_from_html()` — reused by all tiers for JSON-LD/OG/microdata parsing
- `_fetch_page_price()` — restructured but same interface
- All Tier 1, 2, 3 logic
- Supplement pipeline (iHerb, pharmacy JSON-LD)

### `app/routes/admin_routes.py`

Add `GET /api/v1/admin/costs` endpoint returning:
```json
{
  "period": "2026-03",
  "providers": {
    "firecrawl": {"used": 47, "limit": 450, "remaining": 403, "lifetime_used": 47},
    "scrapedo": {"used": 120, "limit": 900, "remaining": 780},
    "serper": {"used": 1823, "limit": 2200, "remaining": 377},
    "openai": {"cost_usd": 12.40, "source": "sum of metadata.total_cost from comparisons table"}
  },
  "circuit_breakers": {
    "firecrawl": {"state": "closed", "failures": 0},
    "scrapedo": {"state": "closed", "failures": 0}
  },
  "comparisons_this_month": 890,
  "avg_cost_per_comparison": 0.0104,
  "fixed_costs_monthly": 30.00,
  "estimated_monthly_total": 39.28
}
```

### `app/main.py`

- Remove 3 diagnostic endpoints (`/health/render-test`, `/health/render-price-test`, `/health/scrape-test`)
- No new endpoints here (cost dashboard goes through admin routes)

## GCC Retailer Expansion

Add to `GCC_LUXURY_RETAILERS`:
```python
GCC_LUXURY_RETAILERS = {
    # Existing
    "ounass.ae", "namshi.com", "bloomingdales.ae", "level-shoes.com",
    # New additions
    "harveynichols.com",       # Harvey Nichols — international, ships to GCC
    "galerieslafayette.ae",    # Galeries Lafayette Dubai
    "theluxurycloset.com",     # The Luxury Closet — new + pre-owned luxury
    "boutique1.com",           # Boutique1 — Dubai multi-brand luxury
}
```

Update Tier 1.5c Serper query to include new retailers:
```python
gcc_query = f"{full_name} ounass OR bloomingdales OR namshi OR harvey nichols OR boutique1"
```

## Input Validation

### `_validate_price_query(brand, name, region)`
- `brand + " " + name` combined: 3-200 chars, must start with letter, strip whitespace
- `region` must be in existing `REGION_CURRENCIES` mapping (derives currency internally)
- Reject → return None immediately, log warning, zero API calls

### `_validate_scrape_url(url)`
- Must be http/https scheme
- Must have valid domain with TLD
- Reject search/category/collection pages: `/search`, `/category`, `/collection`, `/c/`, `/s?k=`
- Reject non-product URLs to avoid wasting Firecrawl/Scrape.do credits

## Cost Model

### Fixed Monthly Costs
| Service | Plan | Cost/month |
|---------|------|-----------|
| Railway | Hobby | $5 |
| Supabase | Pro | $25 |
| Upstash Redis | Free | $0 |
| **Total fixed** | | **$30** |

### Variable Cost Per Comparison
| Component | Cost/call | Frequency | Cost/comparison |
|-----------|-----------|-----------|-----------------|
| Serper (shopping + unified search) | $0.001 | 2x | $0.002 |
| GPT-4o-mini (specs + reviews + verdict) | ~$0.007 | 1x | $0.007 |
| Firecrawl (when official site needed) | 1 credit | ~10% | $0 (free tier) |
| Scrape.do (rendering fallback) | 1 request | ~5% | $0 (free tier) |
| **Total per comparison** | | | **~$0.010** |

**Note:** Firecrawl and Scrape.do cost $0 while on free tiers. When free credits exhaust:
- Firecrawl Hobby ($16/mo, 3,000 credits) = $0.0053/credit → adds ~$0.0005/comparison at 10% trigger rate
- Scrape.do Hobby ($29/mo, 250,000 credits) = $0.000116/req → negligible

### Monthly Projections
| Scale | Comp/month | Variable | Fixed | **Total** | Per-comp |
|-------|-----------|----------|-------|-----------|----------|
| Low (10/day) | 300 | $3 | $30 | **$33** | $0.110 |
| Medium (30/day) | 900 | $9 | $30 | **$39** | $0.043 |
| Growth (100/day) | 3,000 | $30 | $30 | **$60** | $0.020 |
| Scale (300/day) | 9,000 | $90 | $30 | **$120** | $0.013 |

### Credit Exhaustion Timeline
| Provider | Free budget | 10/day rate | 100/day rate | Lasts |
|----------|------------|-------------|--------------|-------|
| Firecrawl | 500 lifetime | 1/day | 10/day | 16mo / 1.7mo |
| Scrape.do | 1,000/month | 0.5/day | 5/day | forever / forever |
| Serper | 2,500 total | 6/day | 60/day | 13mo / 1.3mo |

### When to Upgrade
- **Firecrawl → $16/mo Hobby** when: >15 comparisons/day consistently hit official sites
- **Serper → $50 pack** when: >40 comparisons/day with nocache
- **Scrape.do** stays free until >30 comparisons/day need JS rendering fallback

## Environment Variables

### New (Optional — graceful skip if missing)
| Variable | Purpose | Where to set |
|----------|---------|-------------|
| `FIRECRAWL_API_KEY` | Firecrawl scrape API | Railway env vars |
| `SCRAPEDO_API_TOKEN` | Scrape.do rendering API | Railway env vars |

### Removed
| Variable | Reason |
|----------|--------|
| `CLOUDFLARE_ACCOUNT_ID` | Replaced by Firecrawl |
| `CLOUDFLARE_API_TOKEN` | Replaced by Firecrawl |
| `MICROLINK_API_KEY` | Replaced by Scrape.do |
| `RENDER_PROVIDER` | No longer needed |

### Kept (unchanged)
All existing env vars (`OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_*`, `UPSTASH_*`, `ADMIN_API_KEY`, `SENTRY_DSN`)

## Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_PAGE_SCRAPE` | `true` | Master switch for all page scraping (kept) |
| `ENABLE_JS_RENDER` | `true` → **removed** | Replaced by Firecrawl/Scrape.do presence |
| `ENABLE_FIRECRAWL` | `true` (if API key set) | NEW: enable/disable Firecrawl tier |
| `ENABLE_SCRAPEDO` | `true` (if token set) | NEW: enable/disable Scrape.do tier |

## Test Plan

### New test files
- `tests/test_api_budget_service.py` — credit tracking, circuit breakers, Redis keys, budget exhaustion, monthly reset
- `tests/test_firecrawl_service.py` — API call mocking, Smart Wait, price extraction, error handling, timeout
- `tests/test_scrapedo_service.py` — render=true mocking, HTML extraction, error handling
- `tests/test_cascade_hardening.py` — full cascade flow: early returns, gate checks, leak prevention, conditional 1.5d trigger
- `tests/test_input_validation.py` — price query validation, URL validation, edge cases
- `tests/test_cost_dashboard.py` — admin endpoint, usage summary format

### Modified test files
- `tests/test_js_rendering.py` → update/replace with Firecrawl/Scrape.do tests
- `tests/test_page_scraping.py` → update `_fetch_page_price` flow
- `tests/test_luxury_price_tiers.py` → add Firecrawl tier, expanded GCC retailers

### Coverage target: 80%+ on all new code

## Rollback Plan

All new providers are behind feature flags (`ENABLE_FIRECRAWL`, `ENABLE_SCRAPEDO`) AND API key presence. To disable:
- **Emergency:** Set `ENABLE_FIRECRAWL=false` or `ENABLE_SCRAPEDO=false` in Railway env vars → instant disable, no redeploy
- **Full rollback:** Remove `FIRECRAWL_API_KEY` and `SCRAPEDO_API_TOKEN` env vars → cascade skips new tiers entirely

**Critical:** Phase 4 (remove Cloudflare/Microlink code) ONLY happens after Phase 6 validation confirms new providers work in production for at least 1 week. Until then, old code stays as dead code behind removed env vars.

## Migration Plan

1. **Phase 0:** Validation spike — test Firecrawl on 3 luxury URLs (see Pre-Implementation section)
2. **Phase 1:** Add new services + budget tracking (no behavior change yet)
3. **Phase 2:** Wire Firecrawl into Tier 1.5a (behind `FIRECRAWL_API_KEY` — off if not set)
4. **Phase 3:** Wire Scrape.do into Tier 1.5d (behind `SCRAPEDO_API_TOKEN`)
5. **Phase 4:** Add cost dashboard endpoint + cascade hardening (gates, validation)
6. **Phase 5:** Deploy, set env vars, validate with `nocache=true` test calls for 1 week
7. **Phase 6:** Remove Cloudflare/Microlink dead code + diagnostic endpoints (after 1-week validation)

## Documentation Updates (Post-Implementation)

Update these CLAUDE.md sections:
- **JS rendering section:** Replace Cloudflare/Microlink references with Firecrawl/Scrape.do
- **Environment variables:** Add `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN`; mark Cloudflare/Microlink vars as removed
- **Test file registry:** Add new test files (budget, firecrawl, scrapedo, cascade, validation, cost dashboard)
- **Known Remaining Bugs:** Update luxury price status based on validation spike results
- **Key Files:** Add `api_budget_service.py`, `firecrawl_service.py`, `scrapedo_service.py`

## Out of Scope

- Self-hosted Playwright on Railway (deferred — pursue if Firecrawl doesn't work)
- Retailed.io pre-built luxury APIs (evaluate after Firecrawl validation)
- User-facing rate limit changes (current 10/min is sufficient)
- Pricing page or billing system for end users

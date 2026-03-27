# Backend Hardening & Architecture Refactor — Design Spec

**Date:** 2026-03-27
**Scope:** Security fixes, input validation, concurrency fixes, file decomposition, exchange rate service, tests
**Trigger:** Full code review by 4 parallel review agents across API/security, core services, infrastructure, and test suite

---

## 1. Security Hardening

### C1 — Auth on cache flush & parse endpoints
- Add `Depends(verify_admin_key)` to `DELETE /api/v1/text/cache` and `GET /api/v1/text/parse` in `app/api/text_routes.py`
- Import `verify_admin_key` from `app/api/admin_routes.py`

### C2 — SSRF protection
- New file: `app/utils/url_validator.py`
- Function: `validate_external_url(url: str) -> bool`
- Rejects: private IPs (10.x, 172.16-31.x, 192.168.x), localhost/127.x, link-local (169.254.x), cloud metadata (169.254.169.254), non-http(s) schemes
- Applied in `app/api/url_routes.py` before any external fetch
- Uses `socket.getaddrinfo()` to resolve hostname to IP, then `ipaddress.ip_address()` to check against private/reserved ranges
- Handles DNS rebinding: resolves BEFORE fetching, rejects if resolved IP is private

### C3 — Timing-safe admin key
- Replace `x_admin_key != expected` with `hmac.compare_digest(x_admin_key, expected)` in `app/api/admin_routes.py:25`
- Import `hmac` at top of file

### C4 — Disable docs in production
- In `app/main.py`, set `docs_url=None` and `redoc_url=None` when `RAILWAY_ENVIRONMENT` env var is set
- Locally (no env var), docs remain available at `/docs` and `/redoc`

### Security headers
- Add `Strict-Transport-Security: max-age=31536000; includeSubDomains` to `app/middleware/security.py`
- Add `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` to `app/middleware/security.py`

---

## 2. Input Validation & Endpoint Hardening

### I1 — Logout fix
- In `app/api/auth_routes.py` logout endpoint, extract the Bearer token and call `auth_service.logout_user(token)` before returning success

### I2 — Field length limits
- Add `max_length=1000` to `change_suggestion` field in `FeedbackRequest` model in `app/api/feedback_routes.py`

### I3 — Event data size limit
- Add `@field_validator("event_data")` on `EventItem` in `app/api/feedback_routes.py`
- Reject if `len(json.dumps(v)) > 10_000` (10KB)

### I4 — Rate limit URL endpoints
- Add `@limiter.limit("10/minute")` to `/extract` and `/compare` endpoints in `app/api/url_routes.py`
- Import `limiter` from `app/middleware/rate_limiter.py`

### I5 — LIKE injection escape
- In `app/services/database_service.py:183`, escape `%` → `\%` and `_` → `\_` in the `search` parameter before passing to `.ilike()`

### I6 — Scrapedo token in logs
- Add `before_breadcrumb` hook in `app/services/sentry_service.py` that strips `token=` query parameter from any URL in breadcrumb data

### I7 — SSE disconnect detection
- In `app/api/text_routes.py` SSE `event_generator()`, add `if await request.is_disconnected(): return` check inside the async for loop before yielding each event

### I8 — UUID validation on path params
- Change `comparison_id: str` to `comparison_id: UUID` (from `uuid` stdlib) in:
  - `app/api/history_routes.py` GET and DELETE endpoints
  - `app/api/share_routes.py` POST create share link endpoint

---

## 3. Concurrency Fixes

### C5 — Comparison service: stop singleton
- Change `get_comparison_service()` in `app/services/structured_comparison_service.py` to return a new `StructuredComparisonService()` on every call
- Move static constants (COUNTERFEIT_KEYWORDS, OFFICIAL_BRAND_DOMAINS, LUXURY_BRANDS, etc.) to class attributes if not already
- Per-request state (`total_cost`, `api_calls`, `gpt_calls`, `serper_calls`, `_shopping_items_cache`) stays as instance attributes — safe because each request gets its own instance
- Remove `_service_instance` global variable

### C6 — Scoring service: remove mutable instance state
- Change `_normalize_scores()` to return a tuple: `(normalized_scores, price_tiers, is_cross_tier)`
- Remove `self._price_tiers` and `self._is_cross_tier_flag` from instance state
- Pass `price_tiers` and `is_cross_tier` as parameters to downstream methods that need them
- `ScoringService` can remain a singleton since it will have zero mutable state

### C7 — Atomic Redis operations
- In `app/services/cache_service.py` `add_api_cost()`: replace get-modify-set with `redis_client.incrbyfloat(key, cost)` — single atomic call
- In `app/services/api_budget_service.py` `record_usage()`: replace `for _ in range(count): _redis_incr(key)` with `redis_client.incrby(key, count)` — single atomic call

### I13 — Trust validation flagged counter
- In `app/services/trust_validation_service.py`, add logic inside the dimension loop:
  - Compare GPT verdict's implied winner for each dimension against the scoring dimension winner
  - If they contradict (GPT says Product A wins dimension X, but scores say Product B leads), increment `flagged`
- This makes the `flagged > 2` condition (confidence "reduced") reachable

---

## 4. Architecture — File Decomposition

### Source: `app/services/structured_comparison_service.py` (3,453 lines → ~1,800 lines)

### Extract: `app/services/price_service.py` (~800 lines)
**Functions to move:**
- `_fetch_price_data()` — 3-tier price cascade orchestrator
- `_fetch_page_price()`, `_curl_fetch_html()`, `_extract_price_from_html()` — page scraping
- `_fetch_pharmacy_price()` — Bahrain pharmacy JSON-LD
- iHerb scraping methods
- `_convert_to_bhd()`, `_parse_price_string()` — currency helpers (convert_to_bhd updated to use exchange_rate_service)
- `_validate_price_query()`, `_validate_scrape_url()` — Gate 0 validators
- `_is_luxury_brand()`, `_is_supplement_query()` — detection helpers

**Constants to move:**
- COUNTERFEIT_KEYWORDS, OFFICIAL_BRAND_DOMAINS, LUXURY_BRANDS
- GCC_RETAILER_DOMAINS, TRUSTED_RETAILERS
- SUPPLEMENT_BRANDS, IHERB_BASE_URL
- Currency-related constants

### Extract: `app/services/rating_service.py` (~300 lines)
**Functions to move:**
- `_fetch_ratings()` — Tier 1-3 + fallback orchestrator
- `_extract_shopping_rating()` — parse rating from Shopping results
- `_build_retailer_url()` — URL construction
- Rating consensus logic

**Constants to move:**
- TRUSTED_RATING_RETAILERS, LUXURY_FASHION_RETAILERS

### Extract: `app/services/review_service.py` (~200 lines)
**Functions to move:**
- `_fetch_reviews()` — review pipeline
- `_clean_review_content()` — garbage filtering (min 8 words, sentiment fix)
- `_clean_review_citations()` — replace [snippet_N] with domain attributions

**Fix during extraction:**
- M5: Update `_clean_review_citations()` to process `review_summary.highlights[].point` (current format), not just legacy fields
- M6: Remove dead code that processes `detailed_praises`/`detailed_complaints` (never populated)

### Extract: `app/services/fact_check_service.py` (~200 lines)
**Functions to move:**
- `_fact_check_product()` — multi-signal cross-validation
- Citation verification, shopping cross-check, review sentiment check, price deviation check
- Confidence computation logic

### Extract: `app/services/response_builder.py` (~120 lines)
**New function:**
- `build_comparison_response(product_data, comparison, scoring_result, behavior_profile, user_prefs, from_cache, query, region, category, metadata) -> dict`
- Builds the full response dict: `overview`, `specs`, `reviews`, `scoring`, `personalization`, `metadata`
- Includes backward compatibility aliases (`products`, `comparison`, `winner_index`, `recommendation`, `key_differences`)
- Called by both `compare_from_text()` and `compare_from_text_streaming()` — eliminates I9 duplication

### Orchestrator stays: `structured_comparison_service.py` (~1,800 lines)
**What remains:**
- `compare_from_text()`, `compare_from_text_streaming()` — main entry points
- `_fetch_product_data()` — parallel coordination of price + specs
- Unified search logic (Serper call sharing)
- `parse_product_query()` — GPT query parsing
- Imports and calls extracted services

### Integration pattern
Each extracted service exposes module-level functions (not classes). The orchestrator imports and calls them:
```python
from app.services.price_service import fetch_price_data
from app.services.rating_service import fetch_ratings
from app.services.review_service import fetch_reviews, clean_review_content
from app.services.fact_check_service import fact_check_product
from app.services.response_builder import build_comparison_response
```

Functions that need shared state (e.g., `_shopping_items_cache`) receive it as a parameter from the orchestrator.

---

## 5. Exchange Rate Service

### New file: `app/services/exchange_rate_service.py` (~60 lines)

**Primary API:** frankfurter.app (free, no key, reliable, ECB data)
- Endpoint: `https://api.frankfurter.app/latest?from=USD&to=BHD,SAR,AED,KWD,QAR,OMR,EUR,GBP`
- Returns JSON with rates object

**Caching:**
- Redis key: `exchange_rates:YYYY-MM-DD`
- TTL: 24 hours
- On cache hit: return cached rates (zero latency)
- On cache miss: fetch from API, cache, return

**Fallback:**
- If API fails AND Redis is empty: use hardcoded rates (current values from `_convert_to_bhd()`)
- Log warning when using fallback

**Public function:**
- `async def get_rate(from_currency: str, to_currency: str) -> float`
- Normalizes currency codes to uppercase
- Returns the exchange rate as a float

**Integration:**
- `price_service.py`'s `_convert_to_bhd()` calls `await get_rate(currency, "BHD")` instead of the hardcoded dict lookup
- Hardcoded dict remains as fallback values only

**Supported currencies:** USD, EUR, GBP, SAR, AED, KWD, QAR, OMR ↔ BHD

---

## 6. Tests

### `tests/test_security_hardening.py` (~100 lines)
- `DELETE /cache` without admin key → 403
- `GET /parse` without admin key → 403
- SSRF validator rejects `http://169.254.169.254/`, `http://localhost/`, `http://10.0.0.1/`, `http://192.168.1.1/`
- SSRF validator allows `https://www.amazon.com/`, `https://ounass.com/`
- Admin key uses `hmac.compare_digest` (verify via mock/patch)
- Swagger returns 404 when `RAILWAY_ENVIRONMENT` is set
- HSTS and CSP headers present in responses

### `tests/test_input_validation.py` (~80 lines)
- Feedback `change_suggestion` >1000 chars → validation error
- Event data >10KB → validation error
- LIKE wildcards escaped (`%` and `_` don't act as wildcards)
- `comparison_id` non-UUID string → 422
- URL endpoints return 429 after 10 requests/min

### `tests/test_concurrency_fixes.py` (~60 lines)
- `get_comparison_service()` returns different instances on consecutive calls
- Two mocked `compare_from_text()` calls don't share `total_cost` state
- `_normalize_scores()` returns price_tiers in return value, not on self
- `add_api_cost()` calls `incrbyfloat` (assert mock)
- `record_usage(count=5)` calls `incrby` with 5 (assert mock)
- Trust validation `flagged` increments when verdict contradicts scores

### `tests/test_exchange_rate_service.py` (~40 lines)
- Fetches rates from API (mocked httpx) and returns correct BHD rate
- Second call returns cached value (no API call)
- API failure falls back to hardcoded rates with warning log
- Supports all 8 GCC currencies

### `tests/test_decomposed_services.py` (~80 lines)
- `price_service.fetch_price_data()` callable standalone with mocked dependencies
- `rating_service.fetch_ratings()` callable standalone
- `review_service.clean_review_citations()` processes `highlights[].point` format
- `review_service.clean_review_content()` does NOT process dead legacy fields
- `response_builder.build_comparison_response()` output matches expected structure
- Response builder called with same inputs produces identical output (deterministic)

### Existing test compatibility
- All 1,398 existing tests must pass
- Decomposed methods keep same function signatures — tests that mock them update import paths only
- `conftest.py` unchanged

---

## Agent Team Structure (6 agents)

| Agent | Files Modified | Files Created | Dependencies |
|-------|---------------|---------------|--------------|
| **Security** | text_routes.py, admin_routes.py, main.py, security.py | app/utils/url_validator.py | None |
| **Validation** | auth_routes.py, feedback_routes.py, url_routes.py, database_service.py, sentry_service.py, history_routes.py, share_routes.py | None | None |
| **Concurrency** | structured_comparison_service.py, scoring_service.py, cache_service.py, api_budget_service.py, trust_validation_service.py | None | None |
| **Decomposition** | structured_comparison_service.py (remove extracted code) | price_service.py, rating_service.py, review_service.py, fact_check_service.py, response_builder.py | Concurrency agent finishes first (C5 changes the file) |
| **Exchange Rates** | price_service.py (_convert_to_bhd integration) | exchange_rate_service.py | Decomposition agent finishes first (price_service.py must exist) |
| **QA + Tests** | Possibly import path fixes in existing tests | 5 new test files | All other agents finish first |

---

## Token Budget (Pro 2x Session)

**Estimated total: ~565K tokens** for 4 Opus agents + orchestrator

| Agent | Estimated Tokens | % of Budget |
|-------|-----------------|-------------|
| Security + Validation | ~100K | ~18% |
| Concurrency + Trust | ~90K | ~16% |
| Decomposition + Exchange Rates | ~205K | ~36% |
| QA + Tests | ~120K | ~21% |
| Orchestrator | ~50K | ~9% |

**Optimization tips for agents:**
- Read only the line ranges needed, not full files when possible
- Decomposition agent should plan extractions before reading the full file
- Cross-QA focuses on correctness, not style

---

## Team Execution Rules

1. **All agents are Opus** — no Sonnet or Haiku for implementation
2. **100% feature complete** before any agent considers itself done
3. **Cross-QA mandatory** — every agent QAs another agent's work before the team is disbanded:
   - Security ↔ Validation (review each other)
   - Concurrency ↔ Decomposition (review each other)
   - Exchange Rates ↔ QA agent (review each other)
4. **Subpar or missed work gets sent back** — QA reviewer has authority to reject and require rework
5. **Idle agents write tests** — any agent waiting on dependencies or QA results writes red-green tests targeting 80% coverage on the new code
6. **Team stays assembled** until all QA passes and all 1,398+ existing tests still pass

---

## Out of Scope (Deferred)

- Full test backfill for cache_service, serper_service, openai_service (C8 from review — separate session)
- Database async wrapping with `asyncio.to_thread()` (I11)
- Analytics query optimization (I12)
- Shared test fixtures in conftest.py (M9)
- httpx client reuse across services (M3 from infra review)

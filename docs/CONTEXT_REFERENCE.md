# SmartCompare — Reference Guide (Testing, Deploy, Snippets)

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
ADMIN_API_KEY=...                        # Required for /api/v1/admin/* endpoints
DEBUG_MODE=true
```

## Optional Environment Variables
```
SENTRY_DSN=https://xxx@sentry.io/xxx     # Enables Sentry error tracking (free tier: 5K errors/mo)
LOG_LEVEL=INFO                            # Structured logging level (DEBUG/INFO/WARNING/ERROR)
```

## Frontend Config (Deferred — Manual Setup Required)
```
# Google Sign-In (authService.ts + app.json)
- Google Cloud Console: create OAuth client IDs for web, iOS, Android
- Replace TODO_REPLACE_WITH_GOOGLE_WEB_CLIENT_ID in authService.ts
- Replace TODO_REPLACE_WITH_GOOGLE_IOS_CLIENT_ID in app.json
- Supabase Dashboard: enable Google provider with web client ID + secret

# Apple Sign-In (app.json)
- Requires active Apple Developer subscription ($99/year)
- Replace TODO_REPLACE_WITH_APPLE_TEAM_ID in app.json
- Enable "Sign in with Apple" capability in Xcode / Apple Developer Portal
- Supabase Dashboard: enable Apple provider

# Supabase Schema
- Add `display_name` TEXT column to auth.users (or profiles table) — needed for PUT /auth/profile
```

---

# 13. TESTING GUIDE

## Automated Tests (pytest)

```bash
# All unit tests (fast, free, no API calls) — 344 tests, ~4s
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Include live unit tests (iHerb scraping, Serper, GPT vision) — adds ~$0.03
python -m pytest tests/ -v -m "not (live_db or integration)"

# Live database tests (needs Supabase credentials in .env)
python -m pytest tests/test_drug_database_service.py -v -m live_db

# Integration tests — hits live Railway, costs ~$0.06, takes ~4 min
python -m pytest tests/test_integration.py -v -m integration

# All tests
python -m pytest tests/ -v --timeout=180
```

**Note:** `tests/conftest.py` auto-loads `.env` via `python-dotenv`, so Supabase credentials are available for all tests.

### Test Files
| File | Tests | Type | Notes |
|------|-------|------|-------|
| `tests/test_auth_interceptor.py` | 93 | Unit | Auth endpoints, token verify, optional/required user, profile, password, social login, MIME detection edge cases |
| `tests/test_fact_checking.py` | 48 | Unit | Spec citations, shopping cross-validation, review sentiment, price verification |
| `tests/test_error_paths.py` | 31 | Unit | Currency conversion, freshness calc, price parsing, supplement detection, title/number matching |
| `tests/test_analytics.py` | 30 | Unit | Analytics service (daily/popular/cost/error/product stats), admin endpoints (auth, all 5 routes) |
| `tests/test_camera_vision.py` | 26 | Unit + Live | Vision pipeline, JSON cleanup, size_or_count enrichment, HEIC detection, MIME type validation, endpoint-level rejection |
| `tests/test_observability.py` | 24 | Unit | Sentry init, structured formatter, configure_logging, error handler middleware |
| `tests/test_security_middleware.py` | 16 | Unit | Request ID, security headers, rate limiting (under/over limit, 429) |
| `tests/test_rating_tiers.py` | 16 | Unit + Live | Tier classification, consensus logic, accessory filtering, invalid ratings |
| `tests/test_price_fallback.py` | 12 | Unit + Live | Shopping extraction, accessory filter, high-value min price, currency conversion, all-tiers-fail |
| `tests/test_pharmacy_jsonld.py` | 12 | Unit | Pharmacy JSON-LD price parsing |
| `tests/test_drug_database_service.py` | 11 | Unit + Live DB | 5 local + 6 `live_db` (need Supabase) |
| `tests/test_history.py` | 10 | Unit | save_comparison, get history, delete, search, product name extraction |
| `tests/test_db_improvements.py` | 9 | Unit | log_search, upsert_product, error handling |
| `tests/test_url_extraction.py` | 8 | Unit | URL extraction for price + rating links |
| `tests/test_iherb_scraping.py` | 7 | Unit + Live | Word normalization, live iHerb scraping, brand filtering |
| `tests/test_unified_search.py` | 4 | Unit + Live | Search sharing (specs/reviews reuse), cost budget tracking |
| `tests/test_singleton_state.py` | 3 | Unit | Singleton pattern, cache leak prevention, state reset between requests |
| `tests/test_integration.py` | 6 | Integration | Live Railway: phones, laptops, supplements (iHerb + pharmacy), grocery, shoes |
| **Total** | **366** | | **344 free unit + 10 live_unit + 6 live_db + 6 integration** |

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

## Completed (Feb 11 — Mar 3, 2026)
- [x] Fix rating extraction (Serper Shopping tiers + consensus)
- [x] Rating/Price clickable links (Google Shopping product URLs)
- [x] Supplement pricing (iHerb scrape + pharmacy JSON-LD)
- [x] Camera input (GPT-4o-mini vision OCR)
- [x] Enhanced reviews (category_scores, source_ratings, user_quotes)
- [x] Cost optimization ($0.010/comparison via unified search)
- [x] Bahrain drug database (655 products, GPT context injection)
- [x] Integration tests (6 tests across all categories)
- [x] Zero-cost fact-checking (spec citations, price/review cross-validation)
- [x] Axios auth interceptors (request token attach + 401 auto-refresh)
- [x] Comparison history (save, search, delete with real auth)
- [x] Database improvements (search_logs, product dedup, dead code cleanup)
- [x] Test coverage expansion (37 → 366 tests across 18 files)
- [x] Supabase local env fix (correct project credentials + conftest.py dotenv loading)
- [x] Production readiness: rate limiting, security headers, structured logging, error handling, admin analytics, CI/CD
- [x] Sentry integration (opt-in via SENTRY_DSN)
- [x] GitHub Actions CI (pytest + py_compile + tsc on push/PR)
- [x] Account panel (AccountScreen — name/email edit, password change, connected accounts)
- [x] Google Sign-In (native `@react-native-google-signin/google-signin` + backend social-login endpoint)
- [x] Apple Sign-In (native `expo-apple-authentication` + nonce via `expo-crypto`)
- [x] Image upload HEIC fix (expo-image-manipulator JPEG transcoding + backend magic byte detection)
- [x] History 401 crash fix (sign-in prompt instead of crash)
- [x] EAS build fix (all required plugins added to app.json)
- [x] Input validation on Login/Register screens (email regex, password min 6, confirm match)
- [x] Backend profile endpoints (PUT /auth/profile, /auth/email, /auth/password)
- [x] Backend social-login endpoint (POST /auth/social-login — Google/Apple idToken → Supabase)

## Short Term — Config Setup (Manual, Deferred)
- [ ] Google Cloud Console: create OAuth client IDs (web + iOS + Android)
- [ ] Supabase: enable Google provider, add `display_name` column to users table
- [ ] Replace `TODO_REPLACE_*` placeholder client IDs in authService.ts and app.json
- [ ] Apple Developer subscription (needed for Apple Sign-In activation)
- [ ] Set up Sentry DSN for error tracking

## Short Term — Code
- [ ] Apply Figma UI design
- [ ] Fix camera supplement pricing (verbose names fail iHerb search)
- [ ] Fix ResultsScreen type divergence from types.ts

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

Current status (Mar 3, 2026 — Session 15):
- Backend: Running on Railway v2.1.0 (production-ready with middleware stack)
- Middleware: Security headers, rate limiting, structured logging, error handler, request ID
- Prices (text): Working (3-tier fallback + iHerb scrape + pharmacy JSON-LD + clickable URLs)
- Prices (camera): PARTIALLY BROKEN — supplements get wrong BHD price from camera path
- Specs: Working (supplements enriched with Bahrain drug database context)
- Ratings: Working (Serper Shopping tiers + consensus + GPT review fallback)
- Enhanced Reviews: Working (category_scores, rating_distribution, user_quotes, source_ratings)
- Camera input: Working (HEIC fix via expo-image-manipulator JPEG transcoding + backend magic byte detection)
- Auth: Fixed (refresh token flow + axios interceptors + social login endpoints)
- Account: NEW — AccountScreen with name/email edit, password change, Google/Apple connect
- Social Auth: NEW — Google Sign-In (native SDK) + Apple Sign-In (expo-apple-authentication)
  - Config needed: Google Cloud OAuth client IDs, Supabase Google provider, Apple Dev subscription
- History: Working (save, search, delete with real auth, 401 shows sign-in prompt)
- Cost: ~$0.010/comparison (electronics and supplements)
- Admin: Analytics endpoints at /api/v1/admin/* (protected by ADMIN_API_KEY)
- Sentry: Ready (opt-in when SENTRY_DSN is set)
- CI/CD: GitHub Actions runs pytest + py_compile + tsc on push/PR
- Tests: 366 total across 18 files (344 free unit + 10 live_unit + 6 live_db + 6 integration)
- EAS Build: Fixed (all plugins in app.json: expo-camera, expo-image-picker, expo-image-manipulator, google-signin, apple-auth)
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

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
DEBUG_MODE=true
```

---

# 13. TESTING GUIDE

## Automated Tests (pytest)

```bash
# All unit tests (fast, free, no API calls) — 210 tests, ~3s
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
| `tests/test_fact_checking.py` | 48 | Unit | Spec citations, shopping cross-validation, review sentiment, price verification |
| `tests/test_auth_interceptor.py` | 45 | Unit | Auth endpoints, token verify, optional/required user, profile, password reset |
| `tests/test_error_paths.py` | 31 | Unit | Currency conversion, freshness calc, price parsing, supplement detection, title/number matching |
| `tests/test_rating_tiers.py` | 16 | Unit + Live | Tier classification, consensus logic, accessory filtering, invalid ratings |
| `tests/test_price_fallback.py` | 12 | Unit + Live | Shopping extraction, accessory filter, high-value min price, currency conversion, all-tiers-fail |
| `tests/test_pharmacy_jsonld.py` | 12 | Unit | Pharmacy JSON-LD price parsing |
| `tests/test_drug_database_service.py` | 11 | Unit + Live DB | 5 local + 6 `live_db` (need Supabase) |
| `tests/test_camera_vision.py` | 10 | Unit + Live | Vision pipeline, JSON cleanup, size_or_count enrichment, field normalization |
| `tests/test_history.py` | 10 | Unit | save_comparison, get history, delete, search, product name extraction |
| `tests/test_db_improvements.py` | 9 | Unit | log_search, upsert_product, error handling |
| `tests/test_url_extraction.py` | 8 | Unit | URL extraction for price + rating links |
| `tests/test_iherb_scraping.py` | 7 | Unit + Live | Word normalization, live iHerb scraping, brand filtering |
| `tests/test_unified_search.py` | 4 | Unit + Live | Search sharing (specs/reviews reuse), cost budget tracking |
| `tests/test_singleton_state.py` | 3 | Unit | Singleton pattern, cache leak prevention, state reset between requests |
| `tests/test_integration.py` | 6 | Integration | Live Railway: phones, laptops, supplements (iHerb + pharmacy), grocery, shoes |
| **Total** | **232** | | **194 free unit + 10 live_unit + 6 live_db + 6 integration** |

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
- [x] Test coverage expansion (37 → 232 tests across 15 files)
- [x] Supabase local env fix (correct project credentials + conftest.py dotenv loading)

## Short Term
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

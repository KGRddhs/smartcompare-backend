# SmartCompare — Decisions, Problems Solved & Known Issues

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

## Feb 19: iHerb Direct Scrape for Supplement Prices
**Problem:** Supplement prices were wrong — BHD 2.07 (USD→BHD conversion from US iHerb) vs real BHD 4.388 on bh.iherb.com. Original plan was to use Serper with `site:bh.iherb.com` but Serper doesn't index iHerb regional subdomains. Direct HTTP to iHerb blocked by Cloudflare from Railway datacenter IPs.

**Solution:** `curl_cffi` library mimics Chrome TLS fingerprint, bypasses Cloudflare. Added `_fetch_iherb_price()` method that:
1. Fetches `{cc}.iherb.com/search?kw=...` via `curl_cffi` (sync, wrapped in `run_in_executor`)
2. Parses product cards from HTML `data-ga-*` attributes (brand, price, title)
3. Matches by brand filter → all-query-words subset → iHerb's relevance order (first = most popular)
4. Returns real BHD price directly (no USD conversion needed)

**Bugs hit along the way (all fixed):**
- `await set_cached()` — `set_cached()` is sync (returns bool), `await bool` → TypeError, caught silently by `asyncio.gather(return_exceptions=True)` → price=None
- `NameError: best_score` — log message referenced variable only defined in `else` fallback branch. Broad `except Exception` caught it silently
- `_calculate_freshness` NoneType — `product.get("price", {}).get(...)` fails when price is explicitly `None`. Fixed with `(p.get("price") or {}).get(...)` pattern
- iHerb search query noise — "NOW D3 supplement" returned mostly non-NOW products. Stripped generic words (supplement, vitamin) from iHerb query
- Cheapest-wins picked trial packs — 30-softgel trial (BD 1.305) selected over standard product. Changed to use iHerb's relevance order

**Result:**
- NOW D3: BHD 3.739 from iHerb (real price, real retailer, direct product URL) ✓
- HealthAid D3: BHD 5.66 estimated (not on iHerb — honest behavior) ✓
- Electronics regression: iPhone 16 BHD 449, Galaxy S25 BHD 389 (unchanged) ✓
- Cost: $0.011 (under budget) ✓

**Files changed:**
- `app/services/structured_comparison_service.py` — `_fetch_iherb_price()`, iHerb query cleanup, matching logic, NameError fix, freshness guard
- `app/api/text_routes.py` — debug endpoint added/removed during investigation
- `requirements.txt` — added `curl_cffi>=0.7.0`

**Known limitation:** Variant matching is imprecise — generic "NOW D3" picks iHerb's first relevant result (2000 IU 240 softgels) which may not match specs (1000 IU 180 softgels). Specs and price are fetched in parallel so spec data isn't available to refine the iHerb match.

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

## FIXED: Supplement Prices (Feb 19)
iHerb prices now fetched via `curl_cffi` direct scrape of regional store (`bh.iherb.com`). Returns real BHD prices with retailer attribution and product URLs. Bypasses Cloudflare via Chrome TLS fingerprint mimicry. Fallback: Serper keyword search → GPT extraction → Tier 3 estimate.

## KNOWN ISSUE: iHerb Variant Matching
Generic queries like "NOW D3" match multiple variants on iHerb. Current logic picks iHerb's first relevant result (by relevance sort), which may not match the dosage/count from specs. Specs and price are fetched in parallel, so spec data isn't available to refine the match. Could be improved by fetching specs first, then using dosage/count to filter iHerb results.

## KNOWN ISSUE: Stale cache
Old cached data (7-day TTL for specs/reviews) can serve outdated formats after schema changes. Use `?nocache=true` to bypass. Consider adding a cache version key or flushing on deploy.

## LOW PRIORITY: Pros/cons reference old cached data
Pros/cons generation can reference stale spec data from cache. Cleared naturally as caches expire.

# SmartCompare — Decisions, Problems Solved & Known Issues

# 8. ALL DECISIONS MADE

## Session 43 (2026-05-06) — Pre-launch ToS Fact Base

| Decision | Reasoning |
|----------|-----------|
| Minimum age 13+ general audience (teens + adults) | Cofounder direction. Natural use case is teen-researches / parent-buys via external retailer link. No in-app purchase, no ads, no tracking — keeps 13+ positioning low-risk. |
| Apple Age Rating 12+ / Google Play Teen | Supplements/health-product info triggers "Medical/Treatment Information" or "Infrequent/Mild Drug References" but no other mature categories apply. Do NOT enroll in Apple Kids / Google Designed for Families (those are for under-12 apps with stricter SDK + parental-consent rules). |
| ToS facts produced by code-anchored AI fact base, not lawyer | Cofounder direction (no lawyer engaged). Drafter AI receives `qaren_ai_tos_answers_english.md` (1716 lines, file:line evidence for every claim, pre-filled Apple/Google forms, PDPL article-level factual hooks). Output: ToS + Privacy Policy fit for App Store / Google Play submission. Lawyer review optional but recommended pre-publish. |
| Strict "Undecided" markers, no fabricated legal identifiers | Risk of placeholder tags slipping into published legal text — especially if the doc is forwarded to a drafter AI by a non-author. Pre-flight check in fact base preamble forces drafter AI to ask for missing decisions before producing draft. |

## Pre-launch known issues surfaced Session 43

Discovered during 4-agent forensic analysis (backend Opus + frontend/db/legal Sonnet); reports saved at `docs/plans/2026-05-06-tos-evidence/`.

- **`delete_user_cascade` cascade-completeness gap**: function explicitly DELETEs from 4 tables (user_events, comparison_feedback, comparisons, search_logs) and UPDATEs (does NOT delete) the `users` row. `admin_audit_log` rows referencing `user_id` are RETAINED. Cascade to `user_usage` / referral tables / `expo_push_token` depends on `public.users.id` FK CASCADE to `auth.users.id` — not visible in migrations 001-017 (public.users pre-existed). VERIFY in Supabase Studio → Database → Tables → users → Foreign Keys; OR extend `delete_user_cascade` with explicit deletes.
- **Sentry URL query-string passthrough**: `_before_send` scrubs JWT/keys/Bearer/40+hex/wholesale `Authorization`/`X-Admin-Key`/`Cookie` headers, but does NOT scrub request URL query strings. `/api/v1/text/compare?q=USER_QUERY` reaches Sentry verbatim. Fix: extend `_before_send` to redact query strings.
- **`expo-notifications` missing from app.json plugins**: SDK is in `package.json` but no plugin entry in `app.json`. EAS build may not auto-inject iOS `NSUserNotificationUsageDescription` / Android `POST_NOTIFICATIONS`. Verify on EAS build before App Store / Play submission.
- **No clickwrap ToS consent at registration**: existing ToS Section 1 says "by using the app you agree" (browsewrap). Apple Guideline 5.1.1(v) / 1.3 / 5.1.4 expect clickwrap. Build a registration screen with 3 required checkboxes (13+ self-attestation, ToS+Privacy agreement, cross-border transfer acknowledgement); add `users.consent_*` columns.
- **`ai_sharing_enabled` defaults to ON when undefined**: `ProfileScreen.tsx:102`. For PDPL Art. 4 / GDPR-equivalent rigor, opt-IN (default OFF) is safer; or build a prominent first-launch disclosure for opt-out.
- **Existing privacy policy promises export feature that doesn't exist**: `app/legal/privacy_policy.md` Section 6 says users can "Request a copy of your data by contacting us" — no `GET /api/v1/auth/export` endpoint exists. Either build the export feature OR restate the right as a documented manual process via support email.
- **ToS claims "max 15 referral comparisons per month" not enforced**: `app/services/referral_service.py:707-709` adds bonuses cumulatively without a 15-cap. Code path produces up to 60/month free or 120/month premium. Either enforce the cap or change the ToS language.
- **Stale legal-doc brand mismatch**: `app/legal/{privacy_policy,terms_of_service}.md` say "SmartCompare" throughout, contact emails are `@smartcompare.app`. Both marked `*DRAFT*` but served live via `legal_routes`. Treat as throwaway templates; produce fresh docs from the fact base.
- **Hosting regions unverified in repo**: Supabase project / Railway service / Upstash Redis / Sentry project regions are NOT recorded in code. Verify in each provider's dashboard before publishing the privacy policy's cross-border transfer section.

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
| slowapi in-memory rate limiting | Single Railway instance, no need for distributed Redis limiter |
| Sentry opt-in (not required) | Free tier 5K errors/mo, zero-config when DSN not set |
| Structured JSON logging | One-line JSON per log entry for Railway log aggregation |
| CORS restricted origins | Only Railway + localhost, not wildcard `["*"]` |
| Admin API key auth (not JWT) | Simple, stateless, no user session needed for admin |
| GitHub Actions CI | Free for public repos, runs unit tests + syntax check on push/PR |

## AI Quality Decisions (Session 25)

| Decision | Reasoning |
|----------|-----------|
| "MOST AUTHORITATIVE" price over "LOWEST reasonable" | Lowest price often came from counterfeit sources (DHgate, Temu). Authoritative prices from official/authorized retailers are more trustworthy. |
| Luxury brand two-layer defense (category-independent) | `LUXURY_BRAND_KEYWORDS` (30+) + `OFFICIAL_BRAND_DOMAINS` (25+) detect luxury brands across ALL categories, not just fashion. Counterfeit filtering (DHgate/AliExpress/Temu/Wish) + official domain boost in price sorting. |
| Smart spec field handling over forced N/A | Forcing GPT to fill irrelevant fields (e.g., "power" for a t-shirt) produced meaningless "N/A" values. Omitting irrelevant fields is cleaner. Frontend filters remaining N/A/null/empty. Scoring penalizes when coverage_ratio < 0.5. |
| Citation cleanup in backend not frontend | `_clean_review_citations()` replaces `[snippet_N]` with "Per domain.com:" before response. Backend owns data quality — frontend shouldn't parse raw citation markers. |
| Product-type binding in parser prompt | Explicit product-type-to-category mapping (e.g., shoes→fashion) reduces category misdetection vs free-form AI guessing. |
| Fashion as 9th category with dedicated schema | Fashion products (shoes, bags, clothing) have unique spec fields (material, sole_type, closure, sizing) that don't fit electronics or "other" schemas. |
| "Other" schema cleanup | Removed electronics-specific fields (power, compatibility, count, included) from "other" schema — they produced forced N/A for non-electronics products. |

## Scoring & Quality Decisions (Session 26)

| Decision | Reasoning |
|----------|-----------|
| Category-specific weights over single default | Fashion cares about popularity/reviews, electronics about specs/reliability, supplements about reliability/reviews. One-size-fits-all weights produced irrational scores. |
| Price tier detection (BHD thresholds) | budget/mid/premium/luxury tiers enable cross-tier comparison awareness. Without tiers, expensive = always bad on value. |
| Tier-aware value score | Cross-tier: expectation-based formula (luxury should deliver 85% quality). Same-tier: 60/40 spec/price blend. Prevents luxury items from always losing on value. |
| Counterfeit keyword filter as first filter | Must run BEFORE accessory filter — counterfeit check is higher priority and saves processing on rejected items. |
| Official domain targeted search (Tier 1.5) | When Tier 1 Shopping fails for luxury brands, try `site:domain.com` Serper search. Costs only $0.001 extra, only triggers for luxury. |
| Official domain bypasses sanity check | Prices from hermes.com/louisvuitton.com are authoritative — don't reject them based on GPT training data estimates. |
| Derived ratings display-only (not fed to scoring) | Avoids circular dependency. Ratings derived from overall score (2.5-4.8 range) fill the UI gap without corrupting the scoring pipeline. |
| Dimension winners with 3.0 tie threshold (not 2.0) | On a 0-100 scale, a 2-point difference is noise. 3.0 is a better practical threshold for "meaningfully different." |
| Review post-processing in backend | Dual defense: GPT prompt rules + backend filter. Prompt rules catch most garbage; backend filter catches what slips through (garbage patterns, sentiment misclassification, short text). |
| Verdict prompt receives full scoring context | Injecting tier info, dimension winners, category weights into GPT makes verdict data-backed instead of generic. Zero extra cost — rides on existing prompt tokens. |

## Code Decisions

| Decision | Reasoning |
|----------|-----------|
| Parallel searches | 3 searches in 3s instead of 9s sequentially |
| Currency detection from domain | .ae = AED, .sa = SAR, .com = USD |
| Price > 500 BHD heuristic | Likely mislabeled AED, auto-convert |
| Rating requires source_url | No URL = no rating shown (prevent fake data) |
| BeautifulSoup for HTML parsing | Standard, reliable, handles malformed HTML |
| AsyncIO throughout | Handles concurrent requests. NOTE (M13-05): the sync Supabase client is NOT non-blocking — its `.execute()` calls run inside `async def` and block the single-worker event loop for a full RTT. The request-path hot set (get_user_by_id, get_user_comparisons, save_comparison, usage tier/bonus reads + the lifetime rpc writes, verify_token, audit insert) is offloadable off the loop via `asyncio.to_thread` behind `ENABLE_SYNC_DB_OFFLOAD` (default OFF; flag-OFF is byte-identical, inline). Off-path/cron/script executes are a named follow-up, not yet wrapped. |

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

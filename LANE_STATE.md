# LANE L2 — #21 BH retailer scrape-adapters (Algolia harvester + Shopify verify)

**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l2`
**Branch:** `feature/s3-l2-bh-adapters` (off origin/main `3be92ce`)
**Owner:** L2 · **Task #21 (CRITICAL PATH — >70% genuine-BH-share)**
**Prior L2 (YouTube) already MERGED to main (`28ffc38`).**

## Mission (research brief: docs/plans/2026-06-14-bh-sourcing-research.md)
Build genuine-BH price adapters to parallelize with L1, hand L1 the cascade wiring diff.
1. **Generic Algolia harvester (6thStreet) — PRIMARY, the big lever (5 weak categories).**
2. **alhajis Shopify — VERIFY only** (already registered by L1; confirm /meta.json=BHD).
3. **boutiqaat + sephora — render-tier Sources** (is_render_only=True), lower priority.

## Build order ledger
- [x] #21.1 `algolia_service.py` — generic harvester. 14 TDD tests GREEN.
  - `extract_algolia_config(html, chunk_js)` generic primitive: app-id from DSN preconnect, search-key from chunk minified `adminKey="<32hex>"` default, index from HTML `enterprise_magento_*_products`/`idx=`. Namshi reuses verbatim.
  - `_harvest_config` (live page+chunk fetch via curl_cffi, 24h cache, negcache), `_algolia_query` (read-only POST /1/indexes/{index}/query, circuit-breaker), `_parse_algolia_price` (nested price[0].BHD.default), `_match_algolia_hit` (STRICT — reuses price_service strict_title_match/numbers_match/normalize_words + brand surface; REJECTS TOMS-shoes fuzzy hit for "Tom Ford" query).
  - `fetch_algolia_price` orchestrator -> source_method="local_bhd", estimated=False, ENABLE_PAGE_SCRAPE gate, content-safety, circuit-breaker. NEVER raises.
  - LIVE-VERIFIED creds (1 announced read-only smoke): 6thStreet app-id 02X7U6O3SI, index enterprise_magento_en_bh_products, key 6e9a...2f2 (browser search-only key; used read-only only). Returns genuine BHD (price[0].BHD.default + default_formated:"BHD 21.000").
- [x] #21.2 alhajis VERIFY: PASS — `alhajisbahrain.com/meta.json`=BHD (+ en-bh.ajmal.com=BHD). M1 currency path works, no wrong-stamp risk. L1's alhajis row sound.
- [x] #21.WIRING handed to L1 (in team-lead msg): (A) is_algolia flag on Source, (B) 6thStreet row `Source("en-bh.6thstreet.com","bahrain",("fashion","fragrances","makeup","skincare","haircare"),3.0,is_algolia=True)` + get_algolia_sources_for_category helper, (C) Tier-2 Algolia wave in scs after the Shopify wave (~L2990), imports. L1 #32 lands it.
- [ ] #21.3 boutiqaat + sephora render rows — PART OF the L1 diff (registry rows only, render cascade already handles is_render_only):
      `Source("boutiqaat.com","bahrain",("makeup","skincare","fragrances","haircare"),3.0,is_render_only=True)` (Firecrawl SPA, /en-bh)
      `Source("sephora.me","bahrain",("makeup","skincare","haircare","fragrances"),3.0,is_render_only=True)` (Scrape.do residential, Akamai-walled, /bh-en — authoritative-misses only)
- [x] Integration: import chain clean (no cycle); 207 source-router/shopify/registry tests + 14 algolia = green.

## KEY FINDING (reported to team-lead)
"Tom Ford Black Orchid" on 6thStreet -> 1492 hits, ALL TOMS footwear (brand_name="Toms", Algolia fuzzy "Tom"->"TOMS"). 6thStreet (Apparel Group, mid-market) does NOT carry Tom Ford luxury fragrance. The recorded fixture is the perfect NEGATIVE test — my strict matcher REJECTS it. Positive-path proof needs a product 6thStreet carries (Fenty Pro Filt'r) -> asked team-lead for the +1 live query.

## Discipline
- TDD; path-restricted commits; push-per-commit; NO stash. LANE_STATE every commit.
- STANDALONE only (NO source_router/scs edits — L1 lands the wiring from my diff).
- `.probe_*.py` + `.l2_live_smoke.py` stay UNTRACKED (dot-prefixed). `.env` gitignored.
- Live Algolia smoke = ONE announced call (done). +1 (Fenty) pending team-lead OK.

## Last commit
4550d99 (#21.1 harvester) — committing verify+wiring-state now

## Blockers
- Awaiting team-lead OK for the +1 live "Fenty Pro Filt'r" query (positive-path gate). Harvester build does NOT block on it.

# BH/GCC Genuine-Price Source Build Plan

**Date:** 2026-06-25
**Status:** NOT STARTED — discovery complete (400 sources), build is the next ultracode session.
**Input catalog (committed on branch `feature/bh-gcc-source-catalog`):**
- `data/bh_gcc_source_candidates.json` (R1, 85) · `_round2.json` (214) · `_round3.json` (83) · `_round4.json` (18) = **400 unique verified sources**
- `docs/investigations/2026-06-25-bh-gcc-price-source-discovery{,-round2,-round3,-round4}.md` — per-platform scraper map (§3 of R2/R3), cracked-API endpoints (§3 of R3, §full of R4), integration map (§4).
**Handoff (full detail + ready-to-paste kickoff):** `memory/project_bh_gcc_source_discovery.md`.

## Goal
Replace GPT price *estimates* with genuine data. The discovery proved **400 BH/GCC price sources** exist (380 $0-scrape, 152 genuine-BHD, 20 render-tier) across all 6 GCC countries — so missing-price-data is now a *wiring* problem, not a *data-availability* problem. GCC-currency sources convert to BHD via `exchange_rate_service.get_rate(<cur>, "BHD")`. **The data is now broadly available** — the build makes the scrapers hit it.

## Guiding constraints
- **NO new architecture.** `app/services/source_router.py` already has the `Source(...)` descriptor (`mechanism`/`currency`/`categories`/`locale_paths`/`pdp_url_pattern`/`status`) + per-mechanism selectors. The 2-layer price cache (L1 Redis 7d-genuine / L2 DB) + the 2 off-clock crons (`cron_index_sitemaps` discovery, `cron_warm_price_cache` warmer) are the storage + freshness layer. **This is new adapters + ~400 rows + a liveness gate — not a redesign.**
- **Verify-or-omit / no-fab** holds for every adapter (strict title match + numbers/variant/size + `is_price_showable` + L2 content-safety).
- **$0-discovery is the warmer unblock:** Shopify `/products.json`, WooCommerce Store API, Salla API, and the sitemap index are **Serper-FREE**, so the warmer keeps prices hot WITHOUT a paid-Serper blowout.
- **Run the build in a FRESH session** (clean rate-limit throttle + lean context = much faster) and **wide** (batch-6/8 or worktree-team; ramp cautiously, fall back to batched-4 only if the server-throttle wipes).

## The 6 NEW adapter shapes (build in ROI order; each stamps a genuine source-method)
1. **`fetch_salla_api_price`** — Salla storefront API. Read `"store":{"id":<N>}` from the storefront HTML, then `GET https://api.salla.dev/store/v1/products` header `Store-Identifier: <N>` (PUBLIC, unauthenticated, cursor `?page=N&per_page=M`). Price in `data[].{price,currency,sale_price,url}`; currency = store display (BHD for BH stores, else convert). **ONE adapter for the whole KSA Salla vein + BH Salla.** *Caveat: BH-native Salla is rare; the vein is mostly KSA/SAR convertible.*
2. **`fetch_woocommerce_store_api_price`** — `GET /wp-json/wc/store/products?per_page=100&page=N` → `prices.price ÷ 10^prices.currency_minor_unit` + `prices.currency_code`. **READ `currency_minor_unit` per-response** (BHD/KWD/OMR=3, AED/SAR/QAR=2, but some stores returned 1/2 quirks). Covers ~30 BH/GCC Woo stores. Some block the Store API to plain WebFetch (403/406) → `curl_cffi` fallback.
3. **`fetch_occ_rest_price`** — SAP-Hybris OCC v2: `GET {occ-host}/occ/v2/{baseSite}/products/{code}?fields=FULL` → `price.{currencyIso,value}`. baseSite/occ-host from the storefront config JS. Members: al-dawaa (`stgprevapi.al-dawaa.com`/`aldawaa`), virginmegastore.qa (`occ.virginmegastore.com`/`virginQa`); the path to crack extra.com KSA.
4. **`fetch_alshaya_graphql_price`** — Adobe-Commerce Catalog Service `POST /graphql` `productSearch`. Context from `/configs.json` (`Magento-Store-View-Code: bhr_en` + `x-api-key` + environment-id). Covers the Alshaya `*.com.bh` family (BBW/FootLocker/American Eagle/Muji/New Balance) **+ a faster structured `bn.boots.com` path**. Genuine BHD.
5. **`fetch_algolia_price`** — generic Algolia: `POST https://{appId}-dsn.algolia.net/1/indexes/{index}/query` (appId + search-only apiKey + index from page JS — all in the catalog rows). Members: sharafdg (`products_index`/`oman_products`), nahdi (`H9X4IH7M99`/`prod_en_products`), danube (`1D2IEWLQAD`/`spree_products`, filter `tenant_id=1`).
6. **`fetch_unbxd_price`** — extra.com BH: `https://search.unbxd.io/{apiKey}/{siteKey}/search?q=&rows=` → `response.products[].{sellingPrice,currency:BHD}`. + small custom JSON clients: panda (`api.panda.sa/v3/products?q=`, header `X-Panda-Source: PandaClick`), ourshopee (`api.ourshopee.com`, `x-country=6`→BHD).

**Drop-ins (ZERO adapter code — just `Source(...)` rows):** ~93 Shopify (`is_shopify=True` → existing `fetch_shopify_price` `/products.json`), ~58 curl-JSON-LD (existing `fetch_page_price`), the sitemap stores (existing `cron_index_sitemaps` + `fetch_page_price`). Special-cases: bn.boots `product-sitemap-bh.xml` (fetch PDP WITHOUT `.html`); alosra/aljazira need a `Googlebot/2.1` UA for the SSR price.

## Wiring steps
1. Build the 6 adapters TDD (each → genuine source-method stamp).
2. Add the new genuine methods (`salla_api`, `woo_store_json`, `occ_rest`, `algolia_json`, `unbxd`, …) to **`_GENUINE_BH_SOURCE_METHODS`** so genuine prices get the **7d TTL**. (Mirror in the eval genuine set for parity — `tests/test_eval_genuine_methods_parity.py`.)
3. Generate ~400 `Source(...)` rows from the 4 JSON catalogs (domain / `tier="bahrain"|"gcc"` / categories / currency / mechanism + adapter flag / `locale_paths` / `pdp_url_pattern` / `sample_url` / `status="provider-test"`). Wire the per-mechanism selectors in `source_router.py`.
4. **Liveness-gate EVERY row via `scripts/verify_source_registry.py` before flipping `status="live"`** (sources rot — verify-or-delete; the `sample_url` is the anchor).
5. Extend `data/warmer_catalog.json` with one representative SKU per (category × top genuine-BHD source) so the warmer keeps the most-compared SKUs hot.
6. Comm zero-regression gate (branch-only-NEW == []) + smoke20 vs `54b603e8` before any deploy.

## Deferred (render-tier — needs a Firecrawl/Scrape.do BH-geo headless pass, NOT $0)
20 sources stay Akamai/SPA-walled even with curl_cffi: **sephora.me** (`/bh-en`, biggest BH Western-luxury beauty), **namshi** (Noon-group, Akamai RSC), **Carrefour MAF** (`mafbhr`, Akamai `/api/v8`; `/api/v1/menu` is open), tamimimarkets, spinneys. Plus a few BH sites that were sandbox-DNS-unreachable (batelco/zain/samsung-bh/binge) → re-probe from prod DNS first.

## ROI order to wire FIRST
WooCommerce Store API + Salla API (one adapter each, huge coverage) → the ~93 Shopify drop-ins (zero code) → the cracked giants (noon via `fetch_page_price` JSON-LD, extra/Unbxd, al-dawaa/OCC, nahdi+danube/Algolia, panda) → sporter/drnutrition (genuine-BHD supplements — the previously-empty category) → the Alshaya GraphQL family.

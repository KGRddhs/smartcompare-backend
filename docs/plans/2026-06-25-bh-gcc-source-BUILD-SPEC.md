# BH/GCC Genuine-Price Source Integration — BUILD SPEC

**Date:** 2026-06-25
**Status:** Ready to execute. This is the single source of truth the BUILD agents
execute against.
**Branch base:** `feature/bh-gcc-source-catalog` (catalog committed at `6a33190`).
**Inputs:** live-confirmed recon findings (per-mechanism exact field paths +
captured fixtures + working/dead domains) + design-critic verdicts (D1–D4 + fan-out
+ loader-normalization + overall-risk). Both verified against live endpoints and the
real code; treat as authoritative.

---

## 0. Load-bearing code anchors (verified this session)

| Anchor | Location |
|---|---|
| `Source` frozen dataclass (all optional fields defaulted) | `app/services/source_router.py:19-68` |
| `SOURCE_REGISTRY: List[Source]` (module-level plain list) | `app/services/source_router.py:71-300` |
| `_TIER_ORDER = ("bahrain","gcc","global")` | `app/services/source_router.py:303` |
| `registry_tier()` (suffix-match; used by genuine-gate) | `app/services/source_router.py:333-366` |
| `get_sources_for_category` / per-mechanism selectors | `app/services/source_router.py:395-494` |
| `get_{shopify,algolia,jsonapi,sitemap}_sources_for_category` | `app/services/source_router.py:431-494` |
| `_super_routing_enabled` (lazy, fail-closed, import-time-pure) | `app/services/source_router.py:379-392` |
| `_GENUINE_BH_SOURCE_METHODS = frozenset({...})` | `app/services/price_service.py:4997-5005` |
| `_is_genuine_bh_candidate` (rejects substr `converted`/`estimate`; global-tier excluded) | `app/services/price_service.py:5008-5042` |
| `price_cache_ttl` (genuine→7d via membership; substr guard) | `app/services/price_service.py:159-161` |
| `should_negative_cache` (genuine→never) | `app/services/price_service.py:201` |
| `_showable_source_methods` (genuine ∪ `converted_usd`) | `app/services/price_service.py:947-950` |
| **LATENT BUG** `_match_shopify_product` stamps `shopify_json` even after `_convert_to_bhd` | `app/services/price_service.py:3957-3958, 3987` |
| `fetch_shopify_price` | `app/services/price_service.py:3998` |
| `fetch_nasser_price` (json_api adapter pattern) | `app/services/price_service.py:4581` |
| Eval mirror `GENUINE_BH_SOURCE_METHODS` (parity-pinned) | `scripts/eval_runner.py:400-410` |
| `count_price_provenance` (unrecognized method → no bucket) | `scripts/eval_runner.py:418-441` |
| Cascade prefetch+consume (`_prefetched_direct`, `_consume_adapter_prefetch`) | `app/services/structured_comparison_service.py:4263-4478` |
| `_sitemap_price_fetchers()` per-domain dispatch map | `app/services/structured_comparison_service.py:178-190` |
| `_ADAPTER_TIMEOUT=10.0` + `_timeout_none` (lazy zero-arg factory) | `app/services/structured_comparison_service.py:207-228` |
| Liveness gate | `scripts/verify_source_registry.py` |
| Parity test | `tests/test_eval_genuine_methods_parity.py` |
| Fixtures dir | `tests/fixtures/bh_gcc/` |

---

## 1. Scope + ROI order

Build the genuine-BH/GCC price tail in **strict ROI order** (cheapest, highest-yield
first). Every adapter is **$0** (no Serper, no paid render) and reuses the existing
2-layer price cache + `source_router` registry + the off-clock crons. **No new
architecture.**

| Wave | Work | Code cost | Genuine-BHD yield |
|---|---|---|---|
| **R0** | Shopify + curl/JSON-LD drop-ins (LOADER only, no new adapter) | zero adapter code | ~40 BHD-native Shopify + ~6 curl JSON-LD |
| **R1** | `fetch_woocommerce_store_api_price` (NEW) | 1 new file | 14 BHD-native Woo stores |
| **R2** | `fetch_salla_api_price` (NEW) | 1 new file | reefperfumes (BHD) + 15 SAR (converted) |
| **R3** | Cracked giants: `fetch_occ_rest_price`, `fetch_alshaya_graphql_price` + `fetch_magento_graphql_price`, `fetch_algolia_price` (EXTEND existing) + `fetch_unbxd_price` (NEW) | 3 new + 1 extend | virginBh OCC, 6 Alshaya + klinq + bn.boots GraphQL, sharafdg-BH Algolia, extra-BH Unbxd |
| **R4** | Custom JSON clients: `fetch_rest_json_price` (ourshopee BHD, panda SAR, beautyboothqa QAR) + noon bahrain-en JSON-LD discovery (rides EXISTING `fetch_page_price`) | 1 new + noon discovery | ourshopee (BHD), noon (BHD) |
| **DEFERRED** | 20 render-tier rows (Akamai: sephora.me, namshi, Carrefour-MAF, oman.sharafdg price=0) | — | flagged `is_render_only=True`, NOT live |

**Headline counts:** **6 new adapter modules to build** (woo, salla, occ, alshaya-graphql,
unbxd, rest-json) + **1 extend** (algolia multi-shape parser) + **1 loader** (Shopify/curl
drop-ins) + **noon discovery** on the existing curl path. **~400 catalog rows to load**
(380 $0-scrape, 152 genuine-BHD). **20 render-tier rows DEFERRED.**

> **CRITICAL cross-cutting rule (the #1 zero-regression risk — see §3.0):**
> Every new adapter MUST **stamp by ACTUAL resolved currency**: native BHD → the
> genuine method string; converted-to-BHD → the literal `"converted_usd"`. NEVER copy
> `_match_shopify_product`'s unconditional genuine stamp. A genuine stamp grants a
> 7-day cache TTL, marks the price showable, suppresses negative-caching, AND counts in
> the genuine-share KPI — a single mis-stamp ships a wrong/stale converted number for a
> week and inflates the headline metric.

---

## 2. Per-adapter build spec

> Universal recipe for all adapters: `curl_cffi` `impersonate="chrome"`,
> `allow_redirects=True`, per-request timeout 12–15s, read/write fixtures with
> `encoding="utf-8"` (Windows cp1252 trap — Arabic titles present), strict
> title-match before emitting any price (no-fab), `dict.get` defensively.

### 2.0 R0 — Shopify + curl/JSON-LD drop-ins (LOADER ONLY, NO new adapter code)

**Mechanism:** `shopify_products_json` (reuses `fetch_shopify_price`) +
`curl_jsonld` (reuses `fetch_page_price`). Confirmed live 22/22 Shopify probed,
8/12 curl JSON-LD yield a price on the catalog sample URL.

**Shape:**
- Shopify price: `products[].variants[0].price` — STRING in **MAJOR units** (`"3.300"`,
  `"175.00"`), NOT cents. `parse_price_string` already handles. **NO `/100`/`/1000`.**
- Shopify currency: `/{domain}/meta.json` → `.currency` is the **authoritative** store
  base currency (the variant price is always in this currency even on a `.bh` domain).
- Shopify stock: `variants[0].available` (bool); sale: `variants[0].compare_at_price`
  (original/strike; if present and `> price`, `price` is the sale price).
- Shopify url: `https://{domain}/products/{products[].handle}`.
- curl_jsonld price: JSON-LD `Product.offers.price` (offers may be a LIST → take `[0]`;
  string or number). Currency: `Product.offers.priceCurrency` — **TRUST THIS over the
  TLD** (`bh.cosmostore.org` claims BH but `priceCurrency=USD`). Stock:
  `offers.availability` substring `InStock` (both `http://` and `https://schema.org`,
  case-insensitive). Some PDPs put price in `AggregateOffer.lowPrice` (top-level
  `offers.price=None` → let cascade continue to honest pending, do NOT fabricate).

**Genuine-vs-converted:** `currency=="BHD"` → genuine (`shopify_json` /
`page_scrape_jsonld`); any other → `converted_usd`. **Of 151 Shopify rows only ~40 are
BHD-base; 111 are AED/SAR/QAR/KWD/OMR/USD = converted.**

**BUG TO FIX IN THIS WAVE (D4 / overall-risk):** `_match_shopify_product`
(`price_service.py:3987`) stamps `"shopify_json"` (genuine) UNCONDITIONALLY even when
`needs_conversion=True` (`:3957-3958` converted the amount). Fix **option B (preferred)**:
in `_match_shopify_product`, stamp `source_method="converted_usd"` when `needs_conversion`
is True. Add a failing-first test: a non-BHD Shopify catalog yields
`source_method=="converted_usd"`, not `"shopify_json"`. (Low-risk — no current bahrain
row triggers it; removes the trap the new GCC code must remember to avoid.)

**Fixtures (14 captured):** `shop_bh_goldencollections.json`, `shop_bh_blankbeauty.json`,
`shop_bh_alhajis.json`, `shop_bh_bhgetkuwa.json`, `shop_bh_redtag_myshopify.json`,
`shop_gcc_rasasi_AED.json`, `shop_gcc_swissarabian_USD.json`, `shop_gcc_ardalzaafaran_AED.json`,
`curl_bh_skinbeautybh.html`, `curl_bh_gamesgravity.html`, `curl_bh_bheshop.html`,
`curl_bh_godukkan.html`, `curl_bh_ishopbahrain.html`, `curl_bh_bahrainpharmacy.html`.

**Working BHD-genuine domains (sample):** goldencollections.net, blankbeautybh.com,
bh.getkuwa.com, mastermuscles.net, bhplus.shop, alzainjewellery.com, bh.mubkhar.com,
rtbahplus.myshopify.com (display = bh.redtagfashion.com); curl: skinbeautybh.com (8.000),
gamesgravity.net (134.999, OutOfStock honored), bheshop.com (490.00).

**Gotchas:**
- BHD is 3-decimal (fils): `3.300`/`134.999`/`8.000` are normal — do NOT truncate to 2dp.
- `godukkan.com` JSON-LD iPhone 15 Pro = `"4099"` BHD = implausibly high (~$10,900). The
  existing `is_implausible_high_value_price` guard checks the LOW side only — ADD a
  high-side ceiling OR drop godukkan from the genuine pool.
- Headless Shopify (`rtbahplus.myshopify.com`): `Source.domain` MUST be the
  `/products.json` host (the `.myshopify` host); `sample_url` = the storefront PDP
  (`bh.redtagfashion.com`).

**Dead/walled (OMIT now):** `leenaz.net` (404), `ishopbahrain.com` (variant-carousel,
no bound price), `markeetex.com`/`salams.com`/`touchofoud.com` (non-PDP sample URLs —
re-resolve a real PDP before live), `bh.cosmostore.org` (USD, treat as converted).

---

### 2.1 R1 — `fetch_woocommerce_store_api_price` (NEW: `app/services/woocommerce_service.py`)

**Genuine method string:** `woo_store_api`.
**Mechanism:** WooCommerce Store API, `GET /wp-json/wc/store/products` (alias
`.../wc/store/v1/products` — identical). Public, unauthenticated, MINOR-UNIT prices.

**Shape (exact paths):**
- price: `prices.price` (STRING, minor units). **Variable products:** `prices.price`
  may be `null` and `prices.price_range={min_amount,max_amount}` set instead → take
  `min_amount` (also minor-unit). Both null → skip.
- **minor unit:** `prices.currency_minor_unit` — **READ PER-RESPONSE, never infer from
  currency.** `amount = int(prices.price) / 10**int(prices.currency_minor_unit)`.
- currency: `prices.currency_code`.
- title: `name` — HTML-entity-encoded → `html.unescape` before match/display.
- url: `permalink` (absolute).
- stock: `is_in_stock` (bool) — PREFER this; `is_purchasable` can be True while
  `is_in_stock` False (iworld backorder).
- sale: top-level `on_sale` (bool) is the reliable flag (`is_on_sale` was null on a
  genuinely-discounted item); `prices.sale_price` + `prices.regular_price`.

**Access:** `GET https://<domain>/wp-json/wc/store/products?search=<term>&per_page=20`
(server-side name filter, cheaper) OR `?per_page=100&page=N` (full crawl, off-clock cron
only; `X-WP-TotalPages` header). Headers: `Accept: application/json` + **for WAF stores:**
`Referer: https://<domain>/`, `Sec-Fetch-Site: same-origin`, `Sec-Fetch-Mode: cors`,
`Sec-Fetch-Dest: empty`, `Accept-Language: en-US,en;q=0.9`. **MAKE THE WAF HEADERS
DEFAULT — they cost nothing and unlock ownperfumes/purpleorchidbh/fragrancebh (403
without).** No auth/cookie/nonce. Path: use unversioned, fall back to `/v1/` on 404.
Short retry (one transient fragrancebh timeout cleared on retry).

**Genuine-vs-converted:** stamp `woo_store_api` ONLY when `prices.currency_code=="BHD"`
(14 native-BHD stores). Any other GCC currency → `get_rate(cur,"BHD")` →
**`converted_usd`**.

**MINOR-UNIT QUIRKS (load-bearing — a hardcoded divisor 10×/100×-errors real stores):**
BHD seen as 3 (most) AND **2** (smellsoreal, almajarahgold, bitware); OMR as **1**
(mobpcom), 2 (mushtariyat/qimia/timezone), 3 (mbay/futureit/oudworlds); AED **0**
(kbeautybliss) AND 2; QAR **0** (ispotaba) AND 2.

**Fixtures (13):** `woo_alibaksh_bh.json`, `woo_iworld_bh.json`, `woo_organature_bh.json`,
`woo_theperfumesclub_bh.json`, `woo_ownperfumes_bh.json`, `woo_purpleorchidbh_bh.json`,
`woo_fragrancebh_bh.json`, `woo_smellsoreal_bh_m2.json`, `woo_head2toes_ae.json`,
`woo_kbeautybliss_ae_m0.json`, `woo_mbayoman_om.json`, `woo_mobpcom_om.json`,
`woo_mushtariyat_om.json`.

**Working BHD-genuine domains:** ownperfumes.com, purpleorchidbh.com, fragrancebh.com,
alibaksh.com, iworld.bh, organature.bh, miniso-bh.com, theperfumesclub.com,
arafaphones.com, asasiat.online, bh-en.smellsoreal.com (m2), petshomebh.com,
shop.almajarahgold.com (m2), bitware.store (m2).

**Dead/walled (OMIT):** `nexcelbahrain.com` (persistent 403 on JSON even with WAF
headers — needs HTML/JSON-LD fallback), `papita.co` (200 but non-JSON / Store API
disabled).

---

### 2.2 R2 — `fetch_salla_api_price` (NEW: `app/services/salla_service.py`)

**Genuine method string:** `salla_api`.
**Mechanism:** Salla storefront API. **Step 1** scrape storefront HTML for the store id;
**Step 2** GET the public products API with `Store-Identifier`. One adapter covers the
~4,141-store KSA Salla vein + rare BH-configured (BHD) stores. 16/16 live.

**Shape (exact paths):** price `data[].price` (bare number, store-currency MAJOR units;
equals `sale_price` when `is_on_sale`, else `regular_price`); currency `data[].currency`
(ISO, `"BHD"`/`"SAR"`); title `data[].name` (may be Arabic); url `data[].url` (absolute);
stock `data[].is_out_of_stock` (bool — RELIABLE; `quantity` is usually null, do NOT use);
sale `data[].sale_price`/`data[].regular_price`/`data[].is_on_sale`. Top-level keys:
`status,success,data,filters,cursor{current,next}`.

**Access:**
- Step 1: `GET https://<domain>/` → regex store id:
  `r'"store"\s*:\s*\{[^}]*?"id"\s*:\s*(\d+)'` (works for custom domains AND
  `salla.sa/<slug>`). **Cache store_id per Source** (stable) to skip the HTML round-trip.
- Step 2: `GET https://api.salla.dev/store/v1/products?per_page=10&keyword=<product name>`
  with headers `Store-Identifier: <store_id>` (PUBLIC, unauthenticated), `Accept:
  application/json`. **No token/cookie.**
- **Pagination is CURSOR-based** (`?page=N` is IGNORED). For a price LOOKUP use
  `?keyword=<name>&per_page=10` (search works). Full enumeration (warmer) follows
  `cursor.next`. **No per-product `/{id}` endpoint** — match by `name` within `data[]`.

**Genuine-vs-converted:** branch on `data[].currency` at RUNTIME (do NOT trust the
catalog country tag — `rend-bahrain.com` markets "bahrain" but bills SAR). `"BHD"` →
`salla_api` (genuine); else `get_rate(cur,"BHD")` → `converted_usd`. **Only
reefperfumes.com (Store-Identifier 254895921) is genuine BHD; the other 15 are SAR.**

**Fixtures (5):** `salla_api_perfumya_sar.json`, `salla_api_reefperfumes.json`,
`salla_api_psupps_sar.json`, `salla_storefront_perfumya.html`,
`salla_storefront_reefperfumes.html`.

**Working domains:** reefperfumes.com (BHD genuine, 254895921); SAR (convert):
perfumya.com (2008161730), psupps.net, novaliaperfume.com, taudsa.com, epure-sa.com,
oudbun.store, 3saf.com, bohperfume.com, invite-sa.com, suppsplanet.com, cosmetics.sa,
rend-bahrain.com, daralamirat.com.sa, somman.com, alaseel.com.

**Gotchas:** price is MAJOR units (no `/100`/`/1000`); `data[].price` already = the live
(sale) price when on sale; `brand/sku/gtin` frequently null — match on `name` only;
needs `Store-Identifier` + `impersonate=chrome` (no CF challenge observed).

---

### 2.3 R3a — `fetch_occ_rest_price` (NEW: `app/services/occ_service.py`)

**Genuine method string:** `occ_rest_bhd` (recon also writes `occ_rest`; **use
`occ_rest_bhd`** — pin it in BOTH genuine sets so parity holds).
**Mechanism:** SAP-Hybris OCC v2 REST. `GET {occ_host}/occ/v2/{baseSite}/products/{code}?fields=FULL`
or `.../products/search?query={q}&fields=FULL&pageSize={n}` (search hits carry the SAME
price/stock/url shape — one call resolves name AND price). Zero auth.

**Shape:** price `price.value` (float, native); currency `price.currencyIso`; title
`name`; url `url` (**RELATIVE** — prepend the **storefront origin**, NOT the occ-host);
stock `stock.stockLevelStatus` (`"inStock"`/`"outOfStock"`; numeric `stockLevel` may be
absent on search hits); sale `special` (al-dawaa only: `false` when no markdown, else a
price object; ABSENT on virgin → `dict.get(...,None)`; al-dawaa search hits also expose
`simulatedDiscountPrice` which MIRRORS price when no real discount — do NOT treat as a
markdown).

**Access:** **MANDATORY `Accept: application/json`** (omit → server returns
`application/xml` with identical data → breaks `json.loads`). `impersonate=chrome`,
no auth/cookie. Search pagination via `pagination.{currentPage,pageSize,...}`; use
`pageSize=3-5`, strict-title-match `products[i].name`.

**Per-store config (each Source row needs `(occ_host, baseSite, storefront_origin)`):**
- virginBh: occ_host `https://occ.virginmegastore.com`, baseSite `virginBh`, origin
  `https://www.virginmegastore.bh` — **GENUINE BHD** (107.9 BHD AirPods Pro 3).
- virginQa (QAR→convert): same occ_host, baseSite `virginQa`, origin
  `https://virginmegastore.qa`.
- virginOm (OMR→convert): same occ_host, baseSite `virginOm`, origin
  `https://virginmegastore.om` (newly discovered 4th baseSite).
- al-dawaa (SAR→convert): occ_host `https://stgprevapi.al-dawaa.com` (**NOT www** — www
  returns the SPA HTML shell), baseSite `aldawaa`, origin `https://www.al-dawaa.com`.

**Genuine-vs-converted:** `currencyIso=="BHD"` → `occ_rest_bhd` (genuine); else
`get_rate(currencyIso,"BHD")` → `converted_usd`.

**Fixtures (6):** `aldawaa_occ_product_234419.json`,
`aldawaa_occ_product_discounted_108063.json`, `aldawaa_occ_search_panadol.json`,
`virginmegastore_virginbh_occ_product_830170.json`,
`virginmegastore_virginqa_occ_product_830170.json`,
`virginmegastore_virginbh_occ_search_airpods.json`.

**Dead/walled (OMIT):** baseSites `virginAe`/`virginSa`/`virginKw` (HTTP 400 — not
exposed); `www.al-dawaa.com/occ/...` (SPA HTML, use the stg host). Filter `outOfStock`
(the verified virginBh sample 830170 is currently OOS).

---

### 2.4 R3b — `fetch_alshaya_graphql_price` + `fetch_magento_graphql_price` (NEW: `app/services/magento_graphql_service.py`)

**Genuine method string:** `magento_graphql_bhd` (recon also writes `alshaya_graphql`/
`magento_graphql`; **standardize on `magento_graphql_bhd`** for both shapes — one
genuine string, gate on the response's actual `.currency=="BHD"`).
**Mechanism:** Adobe-Commerce/Magento GraphQL, TWO shapes:

- **Shape A (Alshaya Catalog Service):** GET `https://<host>/configs.json` (a FLAT
  `{key,value}` record list under `.data[]`, 298 records — parse by `record["key"]`)
  → read `commerce-endpoint`, `commerce-environment-id`, `commerce-store-view-code`
  (`bhr_en`), `commerce-website-code` (`bhr`), `commerce-store-code` (`bahrain_store`),
  `commerce-x-api-key`. Then POST that endpoint a `productSearch(phrase,page_size)`.
  Price at `data.productSearch.items[].productView`: **SimpleProductView**
  `price.final.amount.value` (regular `price.regular.amount.value`); **ComplexProductView**
  `priceRange.minimum.final.amount.value` (regular `priceRange.minimum.regular.amount.value`).
  **You MUST request BOTH inline fragments and branch by `__typename`** (apparel/variants
  = Complex, single SKUs = Simple). currency same node `.amount.currency`; title
  `productView.name`; url `commerce-base-endpoint + "/" + productView.urlKey` (NO `.html`);
  stock `productView.inStock` (bool).
- **Shape B (vanilla Magento core, klinq/trikart/ajmal):** POST `https://<host>/graphql`
  header `Store:<store_view>` (klinq=`default`, trikart=`kwt_en`, ajmal-kwt=`default`);
  NO api-key/config. Price `data.products.items[].price_range.minimum_price.final_price.value`
  (regular `.regular_price.value`); currency `.final_price.currency`; title
  `items[].name`; url `"https://"+host+"/"+item.url_key+".html"` (**klinq REQUIRES the
  `.html` suffix** — bare path 302s to `/en/brands`); stock `items[].stock_status`
  (`IN_STOCK`/`OUT_OF_STOCK` string).

**Access:** POST both (GET only for Shape-A `/configs.json`). Shape-A headers:
`Content-Type:application/json`, `x-api-key:<from config>`, `Magento-Environment-Id:<from
config>`, `Magento-Store-View-Code:bhr_en`, `Magento-Website-Code:bhr`,
`Magento-Store-Code:bahrain_store`, `Magento-Customer-Group:0`. **Read `/configs.json`
per domain at fetch time, cache ~24h — keys DIFFER per brand and rotate; never hardcode.**
`impersonate=chrome`. No login.

**Genuine-vs-converted:** gate on the response's actual `.currency=="BHD"` (NOT the
domain). All 6 Alshaya `.com.bh` + `bn.boots.com` + klinq = native BHD = `magento_graphql_bhd`.
trikart/ajmal-kwt (KWD) → `converted_usd`. **NO minor-unit quirk** — Magento returns
decimal majors (`48.13`, `3.75`); do NOT divide.

**Fixtures (6):** `alshaya_bbw_configs.json`, `alshaya_bbw_productsearch.json`,
`alshaya_footlocker_productsearch.json`, `klinq_magento_graphql_products.json`,
`trikart_magento_graphql_products.json`, `ajmal_kwt_magento_graphql_products.json`.

**Working BHD-genuine domains:** bathandbodyworks.com.bh, footlocker.com.bh,
americaneagle.com.bh, muji.bh (host is `www.muji.bh`, NOT muji.com.bh), newbalance.com.bh,
bn.boots.com (configs at the **BARE host** `https://bn.boots.com/configs.json`, no www),
klinq.com.

**Dead/walled (OMIT):** `www.ajmal.com` bare host `/graphql` (non-JSON) — use the
per-locale `en-kwt.ajmal.com`.

---

### 2.5 R3c — `fetch_algolia_price` (EXTEND `app/services/algolia_service.py`) + `fetch_unbxd_price` (NEW: `app/services/unbxd_service.py`)

**Genuine method string:** `local_bhd` (extra-BH Unbxd + bahrain.sharafdg Algolia are
genuine BHD; all non-BHD GCC Algolia stamp `converted_usd`).
**Mechanism:** Algolia generic-search (explicit per-store appId+searchKey+index,
`POST /1/indexes/{index}/query`) + Unbxd search-API
(`GET search.unbxd.io/{apiKey}/{siteKey}/search`). **EXPLICIT-KEY path — NOT the existing
harvest path** (catalog stores don't expose appId via DSN-preconnect).

**CRITICAL — the existing `_parse_algolia_price` is WRONG for every catalog store:** it
expects `hit['price']` to be a LIST `[{'BHD':{'default':N}}]` (6thStreet shape). Build a
**multi-shape parser** trying in order: `list[0][CUR]['default']` → `dict[CUR]['default']`
→ `float(price)`, where `CUR` is the store's pinned currency:
1. FLAT FLOAT `hit['price']` (sharafdg BH/UAE, danube)
2. NESTED `hit['price'][CUR]['default']` (nahdi, CUR='SAR')
3. existing LIST shape (6thStreet — keep for back-compat).

**Currency is NOT in the hit — pin it per Source row** (implied by the index name).

**Shape (per store):**
- sharafdg: title `hit['post_title']`, url `hit['permalink']`, stock `hit['in_stock']`
  (1/0), sale `hit['sale_price']`/`hit['regular_price']` (STRINGS); `hit['price']` float
  already = sale.
- danube: title `hit['full_name_en']`, url `hit['url_en']` (**RELATIVE** → prepend
  `https://danube.sa`), stock `hit['in_stock']` (bool), `hit['original_price']`.
- nahdi: title `hit['name']`, url `hit['url']` (host `ecombe.nahdionline.com`), price
  NESTED `price['SAR']['default']`, no clean stock field (default True).
- Unbxd extra-BH: `response.products[]` (NOT `hits`); price `product['sellingPrice']`
  (sale) / `product['wasPrice']` (orig); currency `product['currency']` (present, `'BHD'`);
  title `product['title']`; url `product['productUrl']` (absolute); stock
  `product['inStockFlag']=='true'` (STRING booleans).

**Access:** Algolia POST `https://{appId}-dsn.algolia.net/1/indexes/{index}/query`
headers `X-Algolia-Application-Id`, `X-Algolia-API-Key`, `Content-Type:application/json`,
body `{"query":"...","hitsPerPage":20}` (danube ALSO needs
`"params":"filters=tenant_id%20%3D%201"`). Unbxd GET, no headers (`impersonate=chrome`).
All keys are PUBLIC search-only keys (read-only `/query` route).

**VERIFIED-LIVE credentials (pin per Source):**
- bahrain.sharafdg.com: appId `9KHJLG93J1` key `e81d5b30a712bb28f0f1d2a52fc92dd0` index
  `bahrain_products` — **BHD genuine `local_bhd`**.
- uae.sharafdg.com: SAME appId+key, index `products_index` (AED → convert).
- danube.sa: appId `1D2IEWLQAD` key `87ca3b6b2ce56f0bb76fc194a8d170e2` index
  `spree_products` (SAR → convert; REQUIRES the tenant_id filter).
- nahdionline.com: appId `H9X4IH7M99` key `2bbce1340a1cab2ccebe0307b1310881` index
  `prod_en_products` (SAR → convert; key is NOT in landing HTML — pin it, do not harvest).
- Unbxd extra.com BH: apiKey `72883ca2a4420a7c7ca07cefda404539` siteKey
  `ss-unbxd-auk-extra-bahrain-en-prod11541714990628` — **BHD genuine `local_bhd`** (if
  401, re-scrape the 32-hex apiKey from `www.extra.com/en-bh/`; siteKey is stable).

**Genuine-vs-converted:** bahrain.sharafdg + extra-BH = `local_bhd` (`estimated=False`);
uae.sharafdg/danube/nahdi → pass amount+currency up so the cascade converts → `converted_usd`.

**Fixtures (6):** `algolia_sharafdg_bh.json`, `algolia_sharafdg_uae.json`,
`algolia_sharafdg_oman.json`, `algolia_nahdi.json`, `algolia_danube.json`,
`unbxd_extra_bh.json`.

**Dead/walled (OMIT):** `oman.sharafdg.com` (works for discovery but price systematically
`0.000` — parser MUST return None for every hit; the catalog appId `1495769233` is
DNS-DEAD), `xcite.com` (server-proxied), `spinneys.com` (post-hydration keys). Reuse the
existing `strict_title_match`/`numbers_match`/`is_counterfeit`/`is_accessory` gates (these
return fuzzy cross-brand hits). Add a circuit-breaker provider `'unbxd'` (`'algolia'`
already wired).

> **NOTE on `bahrain.sharafdg.com` + `extra.com`:** both are ALREADY literal registry
> rows (`source_router.py:94-95`). This wave **upgrades** them to the Algolia/Unbxd
> direct path (`is_algolia=True` / `mechanism="unbxd"`) — it does NOT add duplicate rows.
> The loader (§3) dedups; these two are edited in place, not appended.

---

### 2.6 R4 — `fetch_rest_json_price` (NEW: `app/services/rest_json_service.py`) + noon discovery

**Genuine method string:** `rest_json_bhd` (ourshopee genuine BHD); noon rides the
EXISTING `fetch_page_price` → `page_scrape_jsonld` (genuine BHD, **no new client**).
**Mechanism:** small custom JSON clients. Four families:

- **ourshopee (BHD GENUINE):** `GET https://apios.ourshopee.com/api/product_detail?sku={SKU}`.
  price `data.product[0].display_price` (BHD); orig `old_price`; stock `.stock` (`"In
  stock"`); title `.name`; url = build `https://ourshopee.com/bahrain/{url}/{sku}/`.
  Headers (MANDATORY for BHD): `x-language:en`, `x-country:6` (6=BHD). CF-walled →
  `impersonate=chrome` REQUIRED. **Currency is RUNTIME-selected by `x-country` and NOT
  echoed in `product_detail`** — pin `x-country=6`, treat as BHD by construction.
- **noon bahrain-en (BHD GENUINE, rides `fetch_page_price`):** PDP
  `https://www.noon.com/bahrain-en/{slug}/{N#######V}/p/` → `application/ld+json`
  `Product.offers[0].price` (BHD via `offers[0].priceCurrency=="BHD"`), stock
  `offers[0].availability` endswith `InStock`. Akamai-walled → `impersonate=chrome` +
  backoff on rapid repeats. **NOON SKUs ROTATE** — always discover the live PDP from
  `/bahrain-en/search?q=` and **title-match `Product.name`** against the query; NEVER
  hardcode a SKU.
- **panda (SAR → convert):** `GET https://api.panda.sa/v3/products?q={query}`. price
  `data.products[].varieties[].price` (SAR); orig `undiscounted_price`; stock
  `varieties[].availability` (1=in stock); title `.name`. Headers MANDATORY (422
  without): `X-Panda-Source:PandaClick`, `X-PandaClick-Agent:4`, `api-version:2025-10-01`,
  `X-Language:en`. gzip → curl_cffi auto-decodes. No URL in API (build from id/sku).
- **beautyboothqa (QAR → convert):** `GET https://admin.beautybooth.qa/api/v3/products/{slug}`.
  price `best_sell.data[].net_price` (QAR); orig `stroked_price`; stock `.in_stock` (1/0);
  title `.name`.

**Genuine-vs-converted:** ourshopee(x-country=6) + noon(bahrain-en) = genuine
(`rest_json_bhd` / `page_scrape_jsonld`); panda(SAR) + beautyboothqa(QAR) →
`get_rate(cur,"BHD")` → `converted_usd`. Prices are human strings/numbers, NOT minor
units — parse as float, NO `/1000`.

**Fixtures (6):** `panda_products_milk.json`, `ourshopee_product_detail_PN1497.json`,
`ourshopee_getTopSelling.json`, `noon_pdp_iphone_bhd.html`, `noon_pdp_meta_quest_3s.html`,
`beautyboothqa_product.json`.

**Working BHD-genuine domains:** apios.ourshopee.com (ourshopee.com — 200 BHD Dell
Latitude), www.noon.com/bahrain-en (306.01 BHD iPhone 16). Convert: api.panda.sa (SAR),
admin.beautybooth.qa (QAR).

**Dead/walled (OMIT):** `noon /_svc/catalog/api/v3/search` (returns default SAR catalog —
use the bahrain-en PDP JSON-LD), `dubizzle.com.bh` (classifieds price-floor, out of
scope), `bahrain.desertcart.com` (CF "Just a moment" — leave render_required).

---

### 2.7 Adapters confirmed BLOCKED / not built (none returned `confirmed=false`)

Every probed mechanism came back `confirmed=true`. The only OMISSIONS are the
per-mechanism dead/walled domains listed above (DNS-dead, CF/Akamai render-walls, non-PDP
sample URLs, systematic `price=0`) and the **20 render-tier rows (DEFERRED)** — flagged
`is_render_only=True`, status `render-only`, NOT flipped live; they enter only the
budget-gated Firecrawl/Scrape.do escalation.

---

## 3. Wiring spec

### 3.0 Genuine-method strings → both sets (parity test still passes)

Add these genuine strings to **BOTH** `_GENUINE_BH_SOURCE_METHODS`
(`price_service.py:4997`) AND the eval mirror `GENUINE_BH_SOURCE_METHODS`
(`eval_runner.py:400`) **in the same commit** (`tests/test_eval_genuine_methods_parity.py`
asserts set equality):

```
"woo_store_api", "salla_api", "occ_rest_bhd",
"magento_graphql_bhd", "rest_json_bhd"
```

Notes:
- `local_bhd`, `page_scrape_jsonld`, `shopify_json` already present — Algolia(sharafdg-BH),
  Unbxd(extra-BH), curl JSON-LD, and Shopify(BHD) reuse them. **No new string needed for
  R0/R3c.**
- **None of the 5 new strings contains the substring `converted` or `estimate`** (verified) —
  safe past the `price_cache_ttl:159` / `_is_genuine_bh_candidate:5029` substring guards.
- **Converted GCC prices MUST stamp the literal `"converted_usd"`** — NEVER a per-platform
  `*_converted` string (it mis-buckets: not genuine, not the `converted_usd` bucket, falls
  through to no-bucket + 24h TTL).
- Add a unit test asserting each new genuine string is `is_price_showable`-true,
  `price_cache_ttl == GENUINE` (7d), `should_negative_cache == False`, and eval-bucketed
  genuine.

### 3.1 JSON→`Source` loader normalization (final, from the critic)

Build `SOURCE_REGISTRY = _LITERAL_ROWS + _load_catalog_rows()` where `_load_catalog_rows()`:
- Reads the catalog JSON via `pathlib` **relative to `__file__`** (NOT cwd — Windows
  cwd-persist gotcha), pure-stdlib (`json`+`pathlib`), `encoding="utf-8"`.
- **Wrapped in `try/except` returning `[]` on ANY failure** — a parse error must NOT brick
  every import of `price_service`/`source_router`. Validate each row (required keys, tier
  in `{bahrain,gcc,global}`, mechanism in the known set) and **SKIP-with-log** a malformed
  row rather than raising.
- Keeps the module import-time dependency-free (no network/DB — `_super_routing_enabled`
  and the lazy fetcher map rely on this).

**MECHANISM MAP** (catalog platform → `Source.mechanism` + flags + the genuine method the
adapter stamps):

| Catalog platform | `mechanism` | flags | genuine method |
|---|---|---|---|
| shopify | `shopify` | `is_shopify=True` | `shopify_json` |
| woocommerce | `woo_store_json` | — | `woo_store_api` |
| salla | `salla_api` | — | `salla_api` |
| hybris-OCC | `occ_rest` | — | `occ_rest_bhd` |
| adobe/alshaya-graphql | `magento_graphql` | — | `magento_graphql_bhd` |
| algolia | `algolia` | `is_algolia=True` | `local_bhd` |
| unbxd | `unbxd` | — | `unbxd` (→ stamp `local_bhd`) |
| plain curl / JSON-LD | `curl` or `sitemap` | — | `page_scrape_jsonld` |
| render-only | `render` | `is_render_only=True` | (deferred) |

**CATEGORY-CANON:** lowercase + map to the 9 canonical
`{electronics,grocery,supplements,makeup,skincare,haircare,fragrances,fashion,other}`;
drop unknown tokens; empty list → `()` (matches-all). Synonyms: `beauty`→`(makeup,skincare)`;
`perfume/perfumes/oud/incense/bukhoor/bakhoor`→`fragrances`; `vitamins/health/pharmacy/
sports/sports-nutrition`→`supplements`; `apparel/footwear/jewelry`→`fashion`;
`eyewear`→`fashion`; `watches`→`electronics`; `phones/laptops/gadgets/mobiles/appliances/
headphones/accessories/printers/gaming`→`electronics`; `baby/toys/kids/books/home`→`other`;
`food`→`grocery` if grocer else `other`.

**TIER-FROM-CURRENCY/COUNTRY:** `country==BH OR currency==BHD` → `tier="bahrain"`,
`weight=3.0`; `country in {KSA,UAE,KW,QA,OM} OR currency in {SAR,AED,KWD,QAR,OMR}` →
`tier="gcc"`, `weight=1.5`; else `global` `1.0`. **NEVER set `tier="global"` on a real GCC
retailer** — `_is_genuine_bh_candidate` (`price_service.py:5038`) force-downgrades a
global-tier domain's genuine scrape to converted.

**STATUS DEFAULT:** `status="provider-test-candidate"` on load; **NEVER `"live"` from the
catalog** — only `scripts/verify_source_registry.py` promotes a row to live.
`mechanism="render"` rows → `status="render-only"`, `is_render_only=True`, not flipped.

**`currency` field** set to the row's expected currency. **`usage="price"`** default
(tag `"review"` only for price-less editorial domains).

**DEDUP** against the ~40 literals: skip any JSON row whose normalized apex domain (strip
`www.`, lowercase) equals or is a registry-suffix of an existing literal. **Confirmed
overlap to exclude:** gcc.luluhypermarket.com, bahrain.sharafdg.com, extra.com,
bahrain.microless.com, bn.boots.com, bolo.bh, talabat.com, megamart.bh, alosraonline.com,
nasserpharmacy.com, bahrainpharmacy.com, sephora.me, boutiqaat.com, shopalmoayyed.com,
sonyworld.bh, bh.asgharali.com, en-bh.ajmal.com, alhajisbahrain.com, en-bh.6thstreet.com,
jalilaperfumes.com, bateel.bh, bahrain.ounass.com, noon.com, amazon.ae, sharafdg.com,
ounass.com, bloomingdales.ae, tryano.com, amazon.com, apple.com, samsung.com, sony.com,
lg.com, iherb.com, sephora.com, walmart.com, fragrantica.com, incidecoder.com, gsmarena.com,
sayidaty.net, khaleejtimes.com, gulfnews.com.
(`bahrain.sharafdg.com`/`extra.com`/`bn.boots.com`/`noon.com` are **edited in place** to
add the new mechanism flags — see §2.5/§2.4/§2.6 — not appended.)

### 3.2 New per-mechanism selectors + tier policy

Add selectors mirroring `get_{shopify,algolia,jsonapi,sitemap}_sources_for_category`
(`source_router.py:431-494`). Each filters `SOURCE_REGISTRY` by `mechanism` (+
`is_*` flag where applicable) and `(not s.categories or category in s.categories)`,
returns `[]` never raises. Add:

```
get_woo_sources_for_category(category)        # mechanism == "woo_store_json"
get_salla_sources_for_category(category)      # mechanism == "salla_api"
get_occ_sources_for_category(category)        # mechanism == "occ_rest"
get_magento_gql_sources_for_category(category)# mechanism == "magento_graphql"
get_unbxd_sources_for_category(category)      # mechanism == "unbxd"
get_restjson_sources_for_category(category)   # mechanism == "rest_json" (panda/ourshopee/beautybooth)
```

**TIER POLICY (D2/D4):** the existing Shopify/Algolia/sitemap/jsonapi selectors stay
`tier=="bahrain"`-only (safe — all bahrain rows are BHD). The **new** selectors span
`bahrain + gcc` (they serve the converted GCC tail too) — so they MUST NOT filter on
`tier=="bahrain"`; instead they return both tiers and the **adapter** stamps by actual
currency (genuine vs `converted_usd`). Order each selector's output by
`(tier_order, priority_rank, registry_order)` then apply the fan-out cap (§3.4).

### 3.3 Cascade call-sites in `scs.py` (mirror the sitemap/jsonapi prefetch+consume)

Extend the existing speculative-prefetch block
(`structured_comparison_service.py:4263-4478`). For each new mechanism:

1. **Selector call** alongside `_sitemap_sources_pf`/`_jsonapi_sources_pf` (lines
   4263-4264): `_woo_sources_pf = get_woo_sources_for_category(category)`, etc.
2. **Prefetch future** in the `if ENABLE_PAGE_SCRAPE and (...)` block (lines 4266-4342):
   add each `if _woo_sources_pf: _prefetched_direct["woo"] = asyncio.ensure_future(
   asyncio.gather(*(_timeout_none(lambda s=s: fetch_woocommerce_store_api_price(s.domain,
   full_name, currency), _ADAPTER_TIMEOUT) for s in _woo_sources_pf),
   return_exceptions=True))`. **Use the LAZY zero-arg factory `_timeout_none` wrap**
   (`scs.py:210-228`) per the Codex MEDIUM no-orphan-coroutine rule.
3. **Per-domain dispatch map** for any multi-store-config mechanism (OCC needs
   `(occ_host, baseSite, storefront_origin)`; algolia/unbxd need pinned keys; rest_json
   has 3 distinct hosts). Mirror `_sitemap_price_fetchers()` (`scs.py:178-190`): a
   `_NEW_price_fetchers()` map keyed by normalized domain → the per-store-configured
   fetcher, so adding a store is a one-line map entry. The per-store config (occ_host /
   appId / x-country) is read from the `Source` descriptor fields (`occ_host` etc. can be
   carried in the existing `sample_url`/`pdp_url_pattern`/`subdomain_patterns` fields or a
   small per-domain config dict in the adapter module — prefer the latter for the pinned
   credentials so they live next to the adapter, not in the registry row).
4. **Consume** in `_consume_adapter_prefetch` (lines 4353-4478): extend the `_sm`/`_ja`
   await blocks with `_woo`/`_salla`/`_occ`/`_gql`/`_unbxd`/`_rj` await blocks (same
   `wait_for(..., timeout=_outer_bound)` + `except asyncio.TimeoutError` shape), then add
   their dicts to the `observed` list (lines 4443-4445). The existing genuine-vs-converted
   selection (`min` by amount), `_seed_shortcircuit_candidates`, cache write, and
   `_cancel_prefetched_discovery` short-circuit all apply unchanged.
5. **`_cancel_prefetched_direct`** (lines 4344-4351) already iterates
   `_prefetched_direct.values()` — new futures are cancelled transparently.
6. **noon** needs NO new prefetch — add a bahrain-en discovery (search → title-match the
   live PDP) into the existing `fetch_page_price` path + an Akamai backoff.

### 3.4 Fan-out cap (REAL risk — confirmed by the critic)

Every selector returns ALL category rows uncapped and the cascade gathers them
concurrently — with hundreds of new rows, fragrances could fan out 30+ simultaneous
`/products.json` / Store-API GETs, blowing connection count and the 15s Phase-1 cap.

1. Add `priority_rank: int = 100` to `Source` (frozen-default → every literal row
   byte-unchanged). Curate genuine BHD-native fastest-mechanism rows (Shopify
   `/products.json`, json_api, salla) to LOW ranks.
2. Sort each selector's output by `(tier_order, priority_rank, registry_order)` then
   **top-K slice PER MECHANISM** `[:FANOUT_K]` with `FANOUT_K` env-default **6–8**
   (mirrors the existing `[:limit]` discovery caps at `source_router.py:749` /
   `scs.py:4203-4207`).
3. Lean on the shipped per-source guards as the backstop: `_ADAPTER_TIMEOUT=10.0` +
   `_timeout_none` (`scs.py:207`) wrap each coro so a slow source yields None without
   collapsing the gather; first genuine hit short-circuits and cancels the rest
   (`_cancel_prefetched_direct`/`_consume_adapter_prefetch`). Top-K ~6 × 10s caps keeps
   worst-case concurrency and wall well inside 15s.

---

## 4. Liveness gate

Extend `scripts/verify_source_registry.py` to a **sample_url-based** screen so a row only
flips `status="live"` after a real-PDP price probe (the current script only HEAD-resolves
the apex domain — insufficient for an adapter row whose API endpoint differs from the
storefront host):

1. Keep the control-calibration rail (`google.com`, `shopalmoayyed.com` must be alive in
   THIS env first; `403/405/429` = alive).
2. For each catalog-loaded row, probe the row's `sample_url` (the live-verified PDP /
   API URL captured in recon) via `curl_cffi impersonate="chrome"` and assert a non-null
   parse through the row's adapter (or, cheaply, an HTTP 200 + a price token present).
   Only on success promote `status="live"`.
3. Render-only rows are never probed by curl (they require render) — leave
   `status="render-only"`.
4. **OMIT now (recon dead/walled — do NOT load as live):** leenaz.net, ishopbahrain.com,
   markeetex.com, salams.com, touchofoud.com, bh.cosmostore.org (USD→converted),
   nexcelbahrain.com, papita.co, oman.sharafdg.com (price=0), virginAe/Sa/Kw baseSites,
   www.al-dawaa.com (use stg host), www.ajmal.com bare host, xcite.com, spinneys.com,
   noon `/_svc/catalog` endpoint, dubizzle.com.bh, bahrain.desertcart.com.

---

## 5. Test + gate plan

### 5.1 Per-adapter unit tests (offline, fixture-based — NO network)

One test file per adapter, monkeypatching `curl_cffi`'s `get`/`post` to return the
captured fixture bytes so the whole cascade (bootstrap+search+price+url) runs
deterministically:

| File | Asserts |
|---|---|
| `tests/test_woocommerce_adapter.py` | minor-unit MATRIX (BHD m3→m2, OMR m1/m2/m3, AED m0, QAR m0 — hardcoding any divisor FAILS), genuine-vs-converted, sale, stock edge (iworld OOS+purchasable), `html.unescape` title, name-miss→None |
| `tests/test_salla_api_adapter.py` | store-id regex extraction (+ negative), parse shape, genuine(BHD)-vs-converted(SAR) branch, major-units guard, stock, null sku/gtin robustness, empty `data[]`→None |
| `tests/test_occ_adapter.py` | genuine BHD (value+url-prepend+OOS), search name→code, converted SAR/QAR, `special=false` defensive + virgin-`special`-absent, `Accept:application/json` header sent, dead-baseSite 400→None |
| `tests/test_magento_graphql_adapter.py` | Shape-A config parse (flat `.data[]`), Simple+Complex `__typename` branch, Shape-B genuine(klinq) vs converted(trikart KWD+OOS), strict-title-match no-fab |
| `tests/test_algolia_service.py` (EXTEND) + `tests/test_unbxd_service.py` | multi-shape parser (flat/nested/list), oman price=0→None, Unbxd string-booleans + `currency=='BHD'`, strict cross-brand rejection, genuine-vs-converted stamp |
| `tests/test_rest_json_adapter.py` | panda(SAR header-gated)→converted, ourshopee(BHD x-country=6)→genuine, noon JSON-LD regex + SKU-rotation title-match, beautyboothqa(QAR)→converted, no-fab/422/403→None |
| `tests/test_shopify_converted_stamp.py` (R0 bug-fix) | failing-first: non-BHD Shopify catalog yields `source_method=="converted_usd"` (NOT `shopify_json`) |
| loader test | mechanism→flags, BHD→bahrain/3.0 + AED→gcc/1.5, category-map, the ~40 dedup domains SKIPPED, `currency` carried, malformed row skipped-not-raised |
| `tests/test_eval_genuine_methods_parity.py` (EXTEND) | the 5 new genuine strings present in BOTH sets (stays equal) |
| genuine-set unit | each new string: `is_price_showable` True, `price_cache_ttl==7d`, `should_negative_cache==False`, eval-bucketed genuine |

Do NOT add a `live_unit` test that depends on a rotating key (Unbxd apiKey, Alshaya
x-api-key); a single off-default BHD smoke test per adapter is acceptable to catch source
rot, gated off the `$0` run.

### 5.2 Comm zero-regression gate (authoritative)

Run the free-unit suite on a temp `main` worktree AND the branch; `comm` the SORTED
FAILED-test sets; **`branch-only-NEW == []` is the gate** (NOT per-task `git stash`).
Command (free unit, ~$0):
`python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`.
Known RED-by-design (exclude): `tests/test_value_math.py`, the order-flaky
`tests/test_rate_limiting_complete.py` (real GET).

### 5.3 smoke20 eval gate

`python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8`
(post-deploy — `eval_runner` is a PROD-HTTP harness, so it measures DEPLOYED code; a
pre-deploy eval is meaningless). ACCEPT when winner ≥ baseline 0.50, factual HELD (~1.0);
a specs dip to ~0.92–0.95 is cold-run/over-cap noise. **Gotcha:** the stale OS
`SUPABASE_*` env can false-fail the baseline-fetch — `source .env` or restart Claude Code;
read axis metrics manually if the automated baseline-fetch errors. The genuine-share KPI
will not move on a cold `nocache` eval (it measures cold scraping; the warmer/cron lever
is separate) — verify genuine yield with a fresh `nocache` prod compare per category
instead.

---

## 6. BUILD WAVE PLAN

**Shared (SEQUENTIAL — exactly one writer at a time):**
`source_router.py` (Source field add + loader + 6 selectors), `price_service.py`
(genuine-set + the `_match_shopify_product` bug-fix), `eval_runner.py` (mirror),
`structured_comparison_service.py` (cascade prefetch+consume + dispatch maps),
`verify_source_registry.py`, the catalog JSON file.

**Parallelizable (ISOLATED new files — no shared-tree contention):** each new adapter
module (`woocommerce_service.py`, `salla_service.py`, `occ_service.py`,
`magento_graphql_service.py`, `unbxd_service.py`, `rest_json_service.py`) + its test file.
The Algolia EXTEND touches the existing `algolia_service.py` (one writer).

**Wave breakdown:**

- **Wave A (FOUNDATION — SEQUENTIAL, 1 agent):** add `priority_rank` + (any new
  per-store-config fields) to `Source`; build `_load_catalog_rows()` loader + the 6 new
  selectors + the fan-out cap in `source_router.py`; add the 5 genuine strings to BOTH
  `price_service._GENUINE_BH_SOURCE_METHODS` and `eval_runner.GENUINE_BH_SOURCE_METHODS`;
  fix the `_match_shopify_product` converted-stamp bug; extend the parity test + the
  genuine-set unit test + the loader test. **Gate: comm zero-regression before Wave B.**
  (Everything else depends on the selectors + genuine set existing.)

- **Wave B (ADAPTERS — PARALLEL, up to 6 agents, isolated new files):** build the 6 new
  adapter modules + their offline fixture-based tests (R1 woo, R2 salla, R3a occ, R3b
  magento-graphql, R3c unbxd, R4 rest-json). The Algolia multi-shape EXTEND is its own
  agent (shared `algolia_service.py` — solo writer on that file). Each agent works
  TDD-first against its captured fixtures; no cross-file contention. **Per-batch ≤4
  concurrent late in a long session** (rate-limit burst worsens with session age — run
  this wave fresh).

- **Wave C (WIRING — SEQUENTIAL, 1 agent):** wire all adapters into the `scs.py` cascade
  prefetch+consume + the per-domain dispatch maps; load the R0 Shopify/curl drop-ins via
  the loader; edit-in-place the 4 dedup-overlap rows (sharafdg/extra/bn.boots/noon) to add
  the new mechanism flags. **Gate: comm zero-regression.**

- **Wave D (LIVENESS + GATE — SEQUENTIAL, 1 agent):** extend `verify_source_registry.py`
  to the sample_url probe; run it to promote rows to live (OMIT the §4 dead/walled list);
  deploy; run smoke20 vs `54b603e8`; verify genuine yield per category with a fresh
  `nocache` prod compare.

**Render-tier (20 rows):** loaded by the Wave-A loader with `is_render_only=True` /
`status="render-only"` but NOT flipped live — DEFERRED to a future Firecrawl/Scrape.do pass.

---

## 7. Dispatcher refinements (binding — supersede §3.1/§4 where they conflict)

These three refinements make the registry **zero-regression by construction** and keep the
4 immutable discovery catalogs as provenance.

**R-1 — Consolidated registry data file (one source the loader reads).**
A build-time script `scripts/build_source_registry_data.py` reads the 4 discovery catalogs
(`data/bh_gcc_source_candidates{,_round2,_round3,_round4}.json`), normalizes each row per the
§3.1 mechanism/category/tier maps, **dedups against the ~40 literals (§3.1 list) AND across
rounds (by apex domain)**, and writes ONE consolidated `data/bh_gcc_sources.json` — a list of
flat row dicts carrying every field the loader needs (`domain, tier, weight, categories,
mechanism, is_shopify, is_algolia, is_render_only, currency, sample_url, priority_rank,
status`). The 4 discovery catalogs stay **immutable** (never written back). Re-runnable
(idempotent): re-running preserves existing `status` values (merge by domain) so a liveness
verdict already written is not clobbered.

**R-2 — Loader admits ONLY promoted rows (zero-regression by construction).**
`_load_catalog_rows()` reads `data/bh_gcc_sources.json` and includes a row in
`SOURCE_REGISTRY` **only when `status in ("live", "render-only")`** (render-only rows carry
`is_render_only=True` → inert in the $0 cascade, available for the future render pass).
Default status on first consolidation is `"provider-test-candidate"` → **before the Wave-D
liveness gate runs, ZERO catalog rows are live, so `SOURCE_REGISTRY` is byte-equivalent to
today and the whole change is a no-op in prod.** This means the existing selectors need **no
status filter** — the registry simply never contains an unverified row. The liveness gate
(Wave D) is the ONLY thing that flips a row to `"live"`, so it is load-bearing, not a rubber
stamp.

**R-3 — Liveness gate writes status into the consolidated file (seeded by recon).**
Wave D's extended `verify_source_registry.py` (sample_url probe, §4) writes the verdict
(`live` / `dead` / `render-only`) back into `data/bh_gcc_sources.json` per domain. Seed the
"expected live" set from the recon `working_domains` (already live-confirmed this session);
the gate CONFIRMS them (and re-screens) before promotion. A row that fails its sample_url
probe stays `provider-test-candidate` (never loaded). Commit the consolidated file with the
promoted statuses. **Net effect:** only rows that passed BOTH recon AND the Wave-D probe ever
fire in prod.

**Consequence for the wave plan:** Wave A builds the consolidation script + the loader
(loader is a no-op until R-3 writes live statuses) + selectors + genuine set + the shopify
bug-fix. Wave D runs the consolidation + the liveness gate to actually populate live rows.
The comm zero-regression gate after Wave A therefore proves the change is inert (registry ==
today); the genuine-yield only appears after Wave D promotes rows + a fresh `nocache` prod
compare confirms per-category.

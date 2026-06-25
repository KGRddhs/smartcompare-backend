# BH / GCC Price-Source Discovery — ROUND 3 (targeted + technical: cracked giants + supplement-store breakthrough)

**Date:** 2026-06-25
**Synthesis lead role:** dedupe round-3 candidates against the 299 known R1+R2 domains, live-verify the highest-value cracked-API/uncertain sources, produce the ranked round-3 catalog + the cracked-giant endpoints.
**Data files:**
- New catalog: `data/bh_gcc_source_candidates_round3.json` (83 NEW objects, additive — R1/R2 untouched)
- Known-domain set used for the hard filter: `data/_known_domains_r12.json` (299 domains)

> **Companion to** `2026-06-??-bh-gcc-price-source-discovery.md` (R1, 85 sources) and `…-round2.md` (R2, 214 sources). This file is ADDITIVE.

---

## 0. Headline

- **83 NEW sources** (none in the 299 known R1+R2 domains — programmatically cross-checked, **zero overlap**).
- **17 genuine-BHD** (BH native), **66 convertible** (SAR/AED/KWD/QAR/OMR → BHD).
- **The two hardest structural gaps are now CRACKED:**
  1. **Genuine-BHD supplement stores** (Qaren's historically hardest category) — `sporter.com` (1,594 BH PDPs) + `drnutrition.com` (6,133 BH PDPs) + `bh.iherb.com` native-BHD, all defeated their 403/render walls via `curl_cffi impersonate=chrome`.
  2. **Render/anti-bot-walled GIANTS** — `noon.com`, `extra.com` (Unbxd), `al-dawaa` (Hybris OCC), `uae.sharafdg`/`oman.sharafdg` (Algolia), `virginmegastore.bh/.qa` (Hybris OCC), the Alshaya Adobe-Commerce GraphQL family (BBW/FootLocker/AE/Muji/New Balance) — all return JSON with a real price.
- **One reusable mechanism unlocks a whole platform:** `GET https://api.salla.dev/store/v1/products` with header `Store-Identifier:<store_id>` (public, no token) works for **all ~4,141 live KSA Salla stores** — 16 new Salla stores catalogued here; ONE adapter covers the entire vein.
- **COMBINED GRAND TOTAL across all 3 rounds = 382 unique domains** (299 + 83).

---

## 1. Hard-filter result

Built the known set from `bh_gcc_source_candidates.json` (85) + `…_round2.json` (214) = **299 unique domains**. Of the 86 round-3 raw candidate entries:

- **2 already-known** (filtered OUT of the source catalog): `noon.com`, `extra.com`. Both R1/R2 had them as `render_required`; their round-3 value is a **mechanism upgrade to `json_api`** — recorded in §3 (Cracked Giants), NOT re-listed as new sources.
- **84 candidate slots → 83 distinct NEW source objects** (the malformed salla.sa pseudo-domains `odred (salla.sa`, `batla-perfume (salla.sa`, `pe_colors (salla.sa`, `supplementscastle.com (salla.sa`, `fuelupstore.com (salla.sa` were canonicalized to `salla.sa/<slug>` or the merchant's own domain; `salla.sa` itself is also recorded as the generic-vein descriptor).

**New locale subdomains of known roots (kept as NEW — each adds a country/currency):** `en-bh.rituals.com` (parent en-sa), `kuwait.ounass.com` (parent bahrain), `uae.sharafdg.com`+`oman.sharafdg.com` (parent bahrain), `en-qa.6thstreet.com`+`en-om.6thstreet.com` (parent en-bh), `om.swissarabian.com`, `oman.afnan.com`, `om.asgharali.com`, `om.junaidperfumes.com`, `om.getkuwa.com`, `oman.ahmarket.com` (parent bahrain). Each carries `parent_root` in the JSON.

---

## 2. ROUND-3 CATALOG (ranked: genuine-BHD first, then convertible; cheapest-scrape-first; grouped by country)

Mechanism cost order (cheapest→priciest): `json_api`/`shopify_products_json` (one structured GET/POST) < `sitemap_jsonld` (sitemap + per-PDP curl) < `curl_jsonld` (per-PDP curl) < `algolia` (POST, key may rotate) < render.

### 2.1 BAHRAIN — genuine BHD (16)

| Domain | Categories | Platform | Mechanism | Price (sample) | Verified |
|---|---|---|---|---|---|
| **sporter.com** | supplements/sports-nutrition | Magento+Next | sitemap_jsonld | 56.39 BHD (Dymatize ISO 100) | ✅ LIVE |
| **drnutrition.com** | supplements/sports-nutrition | Next.js | sitemap_jsonld | 12.44 BHD (BSN NO-Xplode) | ✅ LIVE |
| **gcc.luluhypermarket.com** | electronics/grocery/supp/skin/hair/makeup/fashion | SAP Commerce | curl_jsonld (page_scrape_jsonld) | 3.250 bhd | (CLAUDE.md-cited host) |
| **bh.iherb.com** | supplements/skincare/haircare | iHerb | curl_jsonld | 2.11 BHD | ✅ LIVE |
| **virginmegastore.bh** | electronics/other/fashion | SAP Hybris | curl_jsonld | 107.9 BHD (AirPods Pro 3) | ✅ LIVE |
| **en-bh.rituals.com** | skincare/fragrances/haircare | Magento | curl_jsonld | 1.25 BHD | high |
| **revolutionbeauty.me** | makeup/skincare | Magento | curl_jsonld | 2.10 BHD | high |
| **ikea.com** (/bh/en) | other (home) | IKEA platform | curl_jsonld | 27.9 BHD (BILLY) | medium |
| **beautyandblends.com** | fragrances (oud) | Shopify | shopify_products_json | 13.500 BHD | high |
| **bitware.store** | electronics/components/maker | WooCommerce | json_api (WC Store API) | 8.00 BHD (ESP32-S3) | ✅ LIVE |
| **bathandbodyworks.com.bh** | fragrances/skincare/haircare | Adobe Commerce (Alshaya) | json_api (GraphQL) | 6.25 BHD | ✅ configs LIVE |
| **footlocker.com.bh** | fashion | Adobe Commerce (Alshaya) | json_api (GraphQL) | 65 BHD (Nike P-6000) | high |
| **americaneagle.com.bh** | fashion | Adobe Commerce (Alshaya) | json_api (GraphQL) | 19.8 BHD | high |
| **muji.bh** | other/skincare | Adobe Commerce (Alshaya) | json_api (GraphQL) | 2.25 BHD | high |
| **newbalance.com.bh** | fashion | Adobe Commerce (Alshaya) | json_api (GraphQL) | 10 BHD | high |
| **howayte.com** | other (toys/TCG) | Shopify | shopify_products_json | 22.000 BHD | high |

> **basharacare.com** (UAE-base, redirects `/en_bh` → BHD) is filed under UAE in the JSON (its base is a Magento PWA at UAE) but `serves_bh_via = local_bhd`; PDP-level extraction unconfirmed (medium).

### 2.2 KSA — convertible (SAR → BHD) (20)

| Domain | Cat | Platform | Mechanism | Price | Verified |
|---|---|---|---|---|---|
| **al-dawaa.com** | supplements/pharmacy/beauty/grocery | SAP Hybris OCC v2 | json_api | 78.94 / 1805.5 SAR | ✅ LIVE |
| **perfumya.com** | fragrances | Salla | json_api | 440 SAR (Dior J'adore) | ✅ LIVE |
| **psupps.net** | supplements | Salla | json_api | 89 SAR (NXT Ashwagandha) | ✅ LIVE |
| novaliaperfume / taudsa / epure-sa / oudbun.store / 3saf / bohperfume / invite-sa | fragrances | Salla | json_api | 36–699 SAR | high |
| suppsplanet.com | supplements | Salla | json_api | 275 SAR | high |
| cosmetics.sa | makeup/skincare/haircare | Salla | json_api | 79 SAR | high |
| salla.sa/odred, /batla-perfume, /pe_colors | fragrances | Salla | json_api | 50–190 SAR | high |
| salla.sa/supplementscastle, /fuelupstore | supplements | Salla | json_api | 60 / 90 SAR | high |
| **salla.sa** (generic vein) | all | Salla | json_api | 410.25 SAR | (descriptor) |
| banafaforoud.com | fragrances | Salla SSR | curl_jsonld | 125.01 SAR | medium |
| nike.sa | fashion/sports | SFCC | curl_jsonld | 649.00 SAR | high |

### 2.3 UAE — convertible (AED → BHD; basharacare local-BHD) (6)

| Domain | Cat | Platform | Mechanism | Price | Verified |
|---|---|---|---|---|---|
| **uae.sharafdg.com** | electronics/mobiles/computing | WooCommerce + Algolia | algolia | AED 2335 (iPhone 15 128GB) | ✅ LIVE |
| basharacare.com (`/en_bh`) | skincare/makeup/haircare | Magento PWA | curl_jsonld | 22.7 BHD | ⚠️ en_bh BHD live, PDP unconfirmed |
| vitaminshop.ae | supplements | Shopify | shopify_products_json | 136.50 AED | high |
| fitaminat.com | supplements/skincare | Shopify | shopify_products_json | 58.36 AED | high |
| shopkees.com | electronics/laptops/printers | Shopify | shopify_products_json | 710.00 AED | high |
| soukare.com | supplements/skincare | Magento | curl_jsonld | 6.60 AED | medium |

### 2.4 KUWAIT — convertible (KWD → BHD) (3)

| Domain | Cat | Platform | Mechanism | Price | Parent |
|---|---|---|---|---|---|
| kuwait.ounass.com | fashion/fragrances/makeup/skincare | Next+Algolia | sitemap_jsonld | 955 KWD | bahrain.ounass.com |
| en-kw.sssports.com | fashion | SFCC | sitemap_jsonld | 8.000 KWD | (new root) |
| healthland.com.kw | supplements | Shopify | shopify_products_json | 39.950 KWD | (new root) |

### 2.5 QATAR — convertible (QAR → BHD) (14)

| Domain | Cat | Platform | Mechanism | Price |
|---|---|---|---|---|
| virginmegastore.qa | electronics | SAP Hybris OCC | json_api | QAR 399 |
| beautyboothqa.com | skincare | Next.js | json_api (REST) | QAR 106 (CeraVe) |
| musclepumpqa.com | supplements | WooCommerce | json_api | QAR 25.00 |
| alaneesqatar.qa | electronics | WooCommerce | curl_jsonld | QAR 3299 |
| ansargallery.com | electronics/fragrances/makeup | Magento | curl_jsonld | QAR 319.75 |
| nazih.qa | makeup/fragrances | Magento | curl_jsonld | QAR 10 |
| leperfumeqa / store974 / pcbuilderqatar / princesscosmeticsqa / addoony / fyzara / qsales.qa | various | Shopify | shopify_products_json | QAR 35–4649 |
| en-qa.6thstreet.com | fashion/makeup/skincare | Magento | sitemap_jsonld | QAR (client-rendered) — parent en-bh |

### 2.6 OMAN — convertible (OMR → BHD) (24, deepest country dig)

| Domain | Cat | Platform | Mechanism | Price | Verified |
|---|---|---|---|---|---|
| **futureit.om** | electronics/mobiles/laptops/gaming | WooCommerce | json_api | 12.500 OMR | ✅ LIVE |
| oman.sharafdg.com | electronics | Algolia | algolia | 435.000 OMR | parent bahrain |
| oudworlds.com, gamingpcoman.shop, thefaceshop.om | fragrance/electronics/skincare | WooCommerce | json_api | 3.99–189 OMR | high |
| starlink.om, elitegames.om, mls.om, maryamspet.com, oulfah.com*, darbeauty.com*, glamorous-beauty.com, mummy-and-me.store, thebubblewrap.com*, bronzeom.com*, musclehouse.com* | electronics/grocery/beauty/baby/supplements | Shopify | shopify_products_json | 2.5–262 OMR | high |
| om.swissarabian.com, oman.afnan.com, om.asgharali.com, om.junaidperfumes.com, om.getkuwa.com | fragrance/supplements | Shopify | shopify_products_json | 15–43 OMR | high (new OM locale subdomains) |
| bawwaba.om, oman.ahmarket.com | electronics/makeup/grocery | Magento | curl_jsonld | 6–170 OMR | high |
| markeetex.com | grocery | Shopify (proxied) | curl_jsonld | 0.429 OMR | medium |

(\* = `ships_to_countries` includes BH — genuine OMR price, ships to Bahrain.)

---

## 3. CRACKED-API SECTION — render/anti-bot-walled GIANTS (round-3's highest-value output)

Every endpoint below returns JSON/JSON-LD with a real price via `curl_cffi impersonate=chrome` (no headless render needed). The BH/GCC-context param and how the price comes back are spelled out. **Bold = live-verified this synthesis pass.**

### 3.1 noon.com (KNOWN domain — mechanism upgrade) — genuine BHD
- **Endpoint:** `GET https://www.noon.com/bahrain-en/{slug}/N#######V/p/` — parse the **PDP JSON-LD** `Product.offers[]` (multiple seller offers).
- **BH context:** the `/bahrain-en` locale path → JSON-LD `priceCurrency:"BHD"` server-rendered.
- **Price:** `offers[].price` + `offers[].priceCurrency:"BHD"` + `seller`. **VERIFIED: 148.71 BHD (Meta Quest 3S 128GB White).**
- Catalog SPA fronts `/_svc/catalog/api/v3/search` but that path returns the **default SAR** catalog regardless of locale headers → use the bahrain-en PDP JSON-LD for genuine BHD. `curl_cffi` defeats the Akamai wall on the PDP; rate-limit on rapid repeats (add backoff).

### 3.2 extra.com (eXtra / United Electronics — KNOWN domain, mechanism upgrade) — genuine BHD
- **Endpoint:** `GET https://search.unbxd.io/72883ca2a4420a7c7ca07cefda404539/ss-unbxd-auk-extra-bahrain-en-prod11541714990628/search?q={query}&rows={n}`
- **BH context:** the site key `ss-unbxd-auk-extra-**bahrain**-en-prod…` is the Bahrain store; apiKey `72883ca2…` from page JS (may rotate — re-scrape from `www.extra.com/en-bh` source if 401).
- **Price:** `response.products[].{sellingPrice, price, wasPrice, currency:"BHD", productUrl, productCode, available}`. **VERIFIED: iPhone 15 Silicone Case 4.99 BHD, currency BHD** (and S24 Ultra 512GB 399 BHD reported by source).

### 3.3 al-dawaa.com (KSA #1 pharmacy giant, 22,160 products) — SAR
- **Endpoint:** `GET https://stgprevapi.al-dawaa.com/occ/v2/aldawaa/products/{code}?fields=FULL` (SAP-Hybris **OCC v2**, no auth).
- **Context:** baseSite `aldawaa`; product codes from `https://www.al-dawaa.com/sitemap/en/Product-en-SAR.xml`. (NOTE: `www.al-dawaa.com/occ/…` returns the SPA shell — use the `stgprevapi` host.)
- **Price:** `price.{currencyIso:"SAR", value, formattedValue}`. **VERIFIED: 78.94 SAR (Eva Gold Collagen Serum), 1805.5 SAR (Chicco crib).**

### 3.4 al-dawaa / nahdi Algolia → see §3.5/§3.6 (al-dawaa cracked via OCC above; nahdi remains an unverified lead — §5)

### 3.5 uae.sharafdg.com (Sharaf DG UAE full catalog) — AED
- **Endpoint:** `POST https://9KHJLG93J1-dsn.algolia.net/1/indexes/products_index/query` — headers `X-Algolia-Application-Id: 9KHJLG93J1`, `X-Algolia-API-Key: e81d5b30a712bb28f0f1d2a52fc92dd0`; body `{"query":"…","hitsPerPage":n}`.
- **Price:** `hits[].{post_title, price(sale, AED), regular_price, main_sku, permalink, promotion_offer_json[]}`. **VERIFIED: iPhone 15 128GB Blue = AED 2335 (reg 3399).** (Sibling index `posts_product` is 403 — key is index-scoped to `products_index`.)

### 3.6 oman.sharafdg.com (Sharaf DG Oman) — OMR
- **Endpoint:** `POST https://1495769233-dsn.algolia.net/1/indexes/oman_products/query` — `X-Algolia-API-Key: e81d5b30a712bb28f0f1d2a52fc92dd0`.
- **Price:** hits enumerate names/objectIDs; **caveat — Algolia `price` fields may read `0.000`** (resolved per-store-context server-side). If so, the index gives the full free catalog enumeration and you fetch the per-PDP price (WebFetch returned 435.000 OMR on a real PDP). Treat as Algolia-for-discovery + curl-for-price.

### 3.7 virginmegastore.bh / .qa — genuine BHD / QAR
- **BH:** PDP JSON-LD on every `/p/{code}` — `Offer.priceSpecification.{price, priceCurrency:"BHD"}`, availability honest. **VERIFIED: 107.9 BHD (AirPods Pro 3).** (No OCC base exposed in page JS — JSON-LD is the path.)
- **QA:** `GET https://occ.virginmegastore.com/occ/v2/virginQa/products/{code}` (OCC v2) → QAR 399.

### 3.8 Alshaya Adobe-Commerce GraphQL FAMILY (5 BH brand domains, one mechanism) — genuine BHD
- **Endpoint (per brand):** `POST https://www.<brand>/graphql` with a `productSearch(phrase:"…", page_size:N){ items{ productView{ name sku … on SimpleProductView{ price{ final{ amount{ value currency } } } } … on ComplexProductView{ priceRange{ minimum{ final{ amount{ value currency } } } } } } } } }` query.
- **Context (all PUBLIC in `/configs.json`):** `Magento-Store-View-Code: bhr_en`, `Magento-Store-Code`, `Magento-Website-Code: bhr`, `Magento-Environment-Id`, `x-api-key`. **VERIFIED: `bathandbodyworks.com.bh/configs.json` HTTP 200 with `bhr_en`.**
- **Price:** `…final.amount.{value, currency:"BHD"}`. Verified members: BBW (6.25 BHD), FootLocker (65 BHD), American Eagle (19.8 BHD), Muji (2.25 BHD), New Balance (10 BHD). **Also `bn.boots.com` (already in the 299) is the SAME family — its GraphQL gives Pediakid Vitamin D3 = 5.8 BHD = a faster structured path for supplements/pharmacy.**

### 3.9 sporter.com / drnutrition.com (genuine-BHD supplement giants) — BHD
- Not a hidden API but a defeated 403/render wall: `sporter` exposes `_next/data/{buildId}/en-bh/{slug}.json` AND clean JSON-LD; `drnutrition` exposes per-PDP JSON-LD. **VERIFIED: 56.39 BHD / 12.44 BHD.** Catalog via per-locale product sitemaps.

### 3.10 Salla storefront API (the whole ~4,141-store KSA vein) — SAR/BHD
- **Endpoint:** `GET https://api.salla.dev/store/v1/products` with header `Store-Identifier:<store_id>` (PUBLIC, unauthenticated, cursor `?page=N&per_page=M`).
- **store_id discovery:** every Salla storefront's HTML carries `"store":{"id":<NNN>}`.
- **Price:** `data[].{price, currency, regular_price, sale_price, url(/p<id>), sku, gtin, brand}`. **VERIFIED: perfumya 440 SAR (success:true, 15 items), psupps NXT Ashwagandha 89 SAR.** Currency is the store's configured display currency — **BHD for BH-configured stores** (reefperfumes 18 BHD), SAR for KSA.

> Not cracked this round (still render-walled): **xcite** (Algolia proxy 500s), **talabat** (per-vendor geo-gated menu API), **namshi** (Akamai RSC), **sephora.me** (Akamai 403), **Carrefour MAF** (Akamai-walled /api/v8), **Landmark** (auth catalog API), **amazon.ae/.sa** (CAPTCHA). See §5.

---

## 4. INTEGRATION DELTA

### 4.1 NEW sources that ride EXISTING (R1/R2) adapters — drop-in, no code change
- **`fetch_shopify_price` (is_shopify=True):** beautyandblends, howayte (BHD); vitaminshop.ae, fitaminat, shopkees (AED); healthland.com.kw (KWD); leperfumeqa, store974, pcbuilderqatar, princesscosmeticsqa, addoony, fyzara, qsales.qa (QAR); starlink.om, elitegames.om, mls.om, maryamspet.com, oulfah, darbeauty, glamorous-beauty, mummy-and-me.store, thebubblewrap, bronzeom, musclehouse, om.swissarabian, oman.afnan, om.asgharali, om.junaidperfumes, om.getkuwa (OMR). **= 29 sources.**
- **`fetch_woocommerce_store_api_price` (json_api, the R2 Woo Store adapter):** bitware.store (BHD); musclepumpqa (QAR); futureit.om, oudworlds, gamingpcoman.shop, thefaceshop.om (OMR — note minor_unit 3, and thefaceshop minor_unit 2 quirk → keep the per-product minor-unit guard). **= 6.**
- **`fetch_page_price` (curl/sitemap JSON-LD/microdata — the R1/R2 curl adapter):** gcc.luluhypermarket (page_scrape_jsonld), bh.iherb, virginmegastore.bh, en-bh.rituals, revolutionbeauty.me, ikea (BHD); banafaforoud, nike.sa (SAR); basharacare, soukare (AED/BHD); alaneesqatar, ansargallery, nazih.qa (QAR); bawwaba.om, oman.ahmarket, markeetex (OMR); + sporter/drnutrition/en-kw.sssports/kuwait.ounass/en-qa.6thstreet via the sitemap path. **= ~21.**
- **Salla:** the R1/R2 Salla stores used `curl_jsonld`. The 16 new Salla stores SHOULD use the strictly-better `json_api` (api.salla.dev) — see §4.2.

### 4.2 NEW adapter shapes a cracked giant needs (these are the build items)
1. **`fetch_salla_api_price`** — Salla storefront API client: read `"store":{"id"}` from HTML, then `GET api.salla.dev/store/v1/products` with `Store-Identifier` header (cursor-paginated). **One adapter for ~4,141 KSA Salla stores** — strictly better than per-store curl_jsonld. Emits BHD natively for BH stores.
2. **`fetch_occ_rest_price`** — SAP-Hybris **OCC v2** REST client: `GET {occ-host}/occ/v2/{baseSite}/products/{code}?fields=FULL` → `price.{currencyIso,value,formattedValue}`. Covers **al-dawaa** (`stgprevapi.al-dawaa.com`, baseSite `aldawaa`), **virginmegastore.qa** (`occ.virginmegastore.com`, baseSite `virginQa`), and is the path to crack **extra.com (KSA)** + others later.
3. **`fetch_alshaya_graphql_price`** — Adobe-Commerce **Catalog Service `productSearch` GraphQL** client: read `/configs.json` for `commerce-endpoint` + `bhr_en` store-view + `x-api-key` + `environment-id`, then POST the productSearch query. Covers BBW/FootLocker/American Eagle/Muji/New Balance **and** the already-known `bn.boots.com` (faster structured supplements path). Generalizes to any `<brand>.com.bh` Alshaya storefront.
4. **`fetch_algolia_price`** — generic Algolia search client (appId + search-only apiKey + index from page HTML): `POST https://{appId}-dsn.algolia.net/1/indexes/{index}/query`. Covers **uae.sharafdg** (`products_index`) + **oman.sharafdg** (`oman_products` — with the per-PDP price fallback). Reusable for the pharmacy Algolia giants (nahdi) once their keys are captured.
5. **`fetch_unbxd_price`** (OR fold into a generic search-API client) — **extra.com (BH)** Unbxd `search.unbxd.io/{apiKey}/{siteKey}/search?q=&rows=` → `response.products[].{sellingPrice,currency:BHD,productUrl}`. apiKey may rotate (re-scrape from `/en-bh` page).
6. **`fetch_rest_json_price`** — small bespoke REST clients: **beautyboothqa** (`admin.beautybooth.qa/api/v3/products/{slug}`). Low reuse; could fold into a generic JSON-path extractor.

> The noon BHD path rides `fetch_page_price` (PDP JSON-LD) — no new client needed, but add an Akamai-aware backoff if used in the warmer.

---

## 5. UPDATED COVERAGE + remaining structural gaps

### 5.1 Supplement category (was the hardest) — now SOLVED for genuine-BHD
- **Genuine-BHD supplement stores now cracked:** `sporter.com` (1,594 BH PDPs), `drnutrition.com` (6,133 BH PDPs), `bh.iherb.com` (native BHD). Plus R1/R2 genuine-BHD supplement sources (`bh.getkuwa.com`, `smartnutr.com`, `mastermuscles.net`, `livewell.bh`, etc.).
- **Convertible supplement depth:** Salla supplement stores (`psupps.net`, `suppsplanet.com`, `salla.sa/supplementscastle`, `salla.sa/fuelupstore`), `al-dawaa` OCC (22k products incl. supplements), `musclehouse.com` (OMR, ships BH), `musclepumpqa.com`, `healthland.com.kw`, `vitaminshop.ae`, `fitaminat.com`.
- **Verdict:** the supplement structural gap is closed for genuine-BHD branded SKUs.

### 5.2 Oman / Qatar depth
- **Oman:** raised hard — 24 new OM sources (from the source agent's note OM went 15→33). Genuine-OMR Shopify is dense across electronics/grocery/beauty/baby/supplements/fragrance; 5 new OM locale subdomains of known fragrance/supplement roots; several ship to BH directly.
- **Qatar:** 14 new QA sources spanning electronics/beauty/supplements/fragrance — a strong QAR layer (Shopify SMBs + virginmegastore.qa OCC + ansargallery/nazih Magento). QA is now well-covered.

### 5.3 Structural gaps that remain truly render-walled / unreachable ($0 with curl_cffi)
Recorded as `unverified_leads` (NOT promoted) — each needs a render budget (Firecrawl/Scrape.do/headless) or a browser XHR capture:
- **sephora.me** (Chalhoub, BH `/bh-en`, BHD) — Akamai 403; biggest Western-luxury beauty catalog in BH. Render-tier or capture the catalog XHR.
- **namshi.com / en-bahrain.namshi.com** (Noon-group fashion giant, BH BHD) — Akamai RSC SPA; cracking the Noon/Namshi Akamai sensor unlocks both giants.
- **Carrefour MAF (mafbhr genuine BHD)** — Akamai-walled `/api/v8`; `/api/v1/menu` is open (storeId mafsau) but product/price needs the Akamai sensor cookie. Highest-value uncracked grocery+electronics giant. `carrefourbahrain.com` also DNS-unreachable from this sandbox (retry from prod/Railway).
- **talabat.com/bahrain** (q-commerce grocery+pharmacy) — per-vendor geo-gated menu API; menu SKUs not great comparison products. Deprioritize.
- **Landmark Group** (Mothercare/Babyshop/Lifestyle `/bh`) — authenticated Omni catalog API; PDPs client-side.
- **xcite.com** (KW, KWD) — Algolia proxy `/api/algolia/proxy` returns 500; key is server-proxied. No BH context anyway → low BH priority.
- **amazon.ae / amazon.sa** — CAPTCHA; PA-API needs seller creds. No BH locale.
- **ourshopee.com / bahrain.ourshopee.com** (BH electronics, BHD) — client-side XHR; api.ourshopee.com alive but path is runtime-assembled. Capture the XHR.
- **halabh.com** (BH Shopify, BHD) — password-gated (products.json 401). Recheck if it opens.
- **batelco/zain BH telco shops, samsung.com/bh, binge.bh, activefitnessstore.com/bh** — SPA shells / DNS-unreachable from sandbox; retry from prod DNS.

### 5.4 Round 4? — **sweep is approaching saturation, but two HIGH-value cracks justify a focused round 4**
The easy-curl long tail is saturated (382 unique domains; R3's net-new is dominated by giants + locale subdomains, not fresh SMB veins). A **focused round 4** is worth it ONLY for:
1. **The Akamai giants** (sephora.me, namshi, Carrefour MAF mafbhr) — all genuine-BHD, all need a render-budget XHR-capture pass (Firecrawl/Scrape.do with BH geo). These are the last big genuine-BHD catalogs.
2. **The Salla BULK-DISCOVERY harvest** — not new cracking, but enumerating the ~4,141-store KSA Salla vein (StoreLeads + `site:salla.sa`) once `fetch_salla_api_price` exists — pure scale, $0.
3. **The OCC/Algolia giants needing one browser XHR each** — extra.com (KSA), nahdi (Algolia), panda/danube/tamimi (KSA grocery), ourshopee (BH).

Everything else (more Shopify/Woo/Salla SMBs) is **diminishing returns** — the adapter coverage already spans every platform these use. **Recommendation: declare the curl-scrapeable SMB sweep SATURATED; open a small "Round 4 — render-budget giants" only for the 3 Akamai genuine-BHD catalogs + the Salla bulk harvest.**

---

## 6. Verification log (this synthesis pass — 15 live probes via curl_cffi impersonate=chrome, all PASSED)

| Source | Result |
|---|---|
| sporter.com en-bh PDP | HTTP 200, JSON-LD BHD, price 56.39 ✅ |
| drnutrition.com en-bh PDP | HTTP 200, BHD, price 12.44 ✅ |
| al-dawaa OCC v2 /products/234419 | HTTP 200 application/json, {SAR, 1805.5} ✅ |
| api.salla.dev (perfumya 2008161730) | HTTP 200 success:true, 15 items, 440 SAR ✅ |
| api.salla.dev (psupps 711969789) | HTTP 200 success:true, NXT Ashwagandha 89 SAR ✅ |
| noon bahrain-en PDP | HTTP 200, JSON-LD price 148.71 BHD ✅ |
| extra.com Unbxd search | HTTP 200, 4.99 BHD, currency BHD ✅ |
| uae.sharafdg Algolia products_index | HTTP 200, iPhone 15 128GB AED 2335 ✅ |
| bathandbodyworks.com.bh /configs.json | HTTP 200, bhr_en store-view present ✅ |
| en-qa.6thstreet adidas listing | HTTP 200, priceCurrency QAR present ✅ |
| basharacare /en_bh | HTTP 200, redirects en_bh, BHD present ✅ |
| virginmegastore.bh PDP | HTTP 200, JSON-LD price 107.9 BHD ✅ |
| bitware.store WC Store API | HTTP 200, 8.00 BHD (price=800 minor=2) ✅ |
| futureit.om WC Store API | HTTP 200, 12.500 OMR (price=12500 minor=3) ✅ |
| bh.iherb.com PDP | HTTP 200, JSON-LD 2.11 BHD ✅ |

---

## 7. Grand totals

| Round | New sources | Notable |
|---|---|---|
| R1 | 85 | foundation Shopify/Woo/sitemap BH |
| R2 | 214 | breadth across BH/KSA/KW/OM |
| **R3** | **83** | **cracked giants + genuine-BHD supplements + Salla vein** |
| **COMBINED UNIQUE DOMAINS** | **382** | (299 + 83, zero overlap) |

# Bahrain / GCC Price-Source Discovery — Synthesis & Integration Map

**Date:** 2026-06-25
**Author:** synthesis lead (discovery-sweep dedupe + rank)
**Mission:** Replace GPT price *estimates* with genuine BH/GCC price sources. Each catalogued
source was verified by a real fetch showing a literal price string. This doc ranks them, maps each
to an existing adapter in the codebase, recommends a storage/registry schema, and reports coverage gaps.

**Companion seed file:** `data/bh_gcc_source_candidates.json` (clean JSON array, registry-ready).

---

## 0. Headline

- **85 verified sources** in the seed JSON (deduped to distinct domains; aliases collapsed —
  e.g. wojooh→faces.ae, megamartbahrain.com→megamart.bh, carrefourbahrain.com dropped as defunct).
- **66 genuine-BHD** sources vs **19 GCC-convertible** (AED/SAR/USD/QAR/KWD).
- **By mechanism:** `shopify_products_json` **27** · `curl_jsonld` **29** · `sitemap_jsonld` **15**
  · `json_api` **7** · `algolia` **2** · `render_required` **5**.
- **The cheap-scrape majority is real:** **34** sources are `shopify_products_json` or `json_api`
  (zero-cost static JSON, no Serper, no render) and **44** are `curl_jsonld`/`sitemap_jsonld`
  (one plain curl per PDP, sitemap discovery off-clock). Only **5** are `render_required` (deprioritize).
- This sweep **multiplies** the existing registry. Today the live registry has ~5 genuine-BHD
  price adapters (nasser json_api, bolo/boutiqaat sitemap, the Shopify fragrance stores, lulu
  jsonld). This sweep adds **fragrance** (10+ genuine-BHD Shopify/Woo stores), **supplements**
  (getkuwa Shopify, aldeerah/ymh/bahrainpharmacy sitemap), **electronics** (godukkan, ishopbahrain,
  bheshop, imachines, sonyworld), **fashion** (the 4 Landmark `/bh/en/` jsonld + redtag Shopify),
  and **grocery** (megamart, aljazira, alosra, dukakeen).

---

## 1. Mechanism cheat-sheet (cost order, cheapest first)

| Mechanism | Cost / call | What it is | Maps to adapter |
|---|---|---|---|
| `shopify_products_json` | $0 | `GET {domain}/products.json` → full catalog JSON, BHD in `variants[].price` | `price_service.fetch_shopify_price` + `is_shopify=True` |
| `json_api` | $0 | Store's own JSON API (WooCommerce Store API, custom newapi, Next `__NEXT_DATA__`) | `price_service.fetch_nasser_price`-style, `mechanism="json_api"` |
| `sitemap_jsonld` | $0 + off-clock index | Own XML sitemap (off-clock index) → curl PDP → JSON-LD/HTML price | `bolo`/`boutiqaat`-style: `cron_index_sitemaps` + `fetch_bolo_price`/`fetch_page_price`, `mechanism="sitemap"` |
| `curl_jsonld` | $0 | Plain curl of a PDP/listing, price in static JSON-LD/microdata/state-JSON | `price_service.fetch_page_price`, `mechanism="curl"` |
| `algolia` | $0 (after key extract) | Price lives in a public Algolia index / embedded multi-currency record | `algolia_service.fetch_algolia_price` + `is_algolia=True` |
| `render_required` | paid (Firecrawl/Scrape.do) | SPA / Akamai / CF wall — no price in static HTML | render tier, `is_render_only=True` (deprioritize) |

**Decimal convention:** native BHD stores print 3-decimal (`12.000`, `7.690`). Shopify
`products.json` prints the base-currency number with no currency field — for a `.bh`/BH-base store
the number IS BHD (validated: sonyworld, getkuwa, ajmal, redtag `meta.json` country=BH).

---

## 2. Ranked catalog

Rank key: **genuine BHD first**, then GCC-convertible; within currency, **cheapest scrape first**
(`shopify_products_json`/`json_api`/`sitemap_jsonld`/`curl_jsonld` > `algolia` > `render_required`).

### 2A. Genuine BHD — zero-cost JSON (`shopify_products_json` / `json_api`) — WIRE FIRST

| # | Domain | Categories | Mechanism | Sample price | Conf |
|---|---|---|---|---|---|
| 1 | bh.jashanmal.com | fragrances, makeup, appliances, fashion, home, luggage | shopify_products_json | `"price":"20.000"` | high |
| 2 | sonyworld.bh *(in registry)* | electronics (TV/audio/camera/gaming) | shopify_products_json | 39.000 | high |
| 3 | imachines.bh | electronics (Apple reseller) | shopify_products_json | 479.990 | high |
| 4 | en-bh.ajmal.com *(in registry)* | fragrances/oud/attar | shopify_products_json | 48.000 (Oud Nadir 50g) | high |
| 5 | alhajisbahrain.com *(in registry)* | fragrances, makeup | shopify_products_json | 12.000 (Khamrah) | high |
| 6 | bh.asgharali.com *(in registry)* | fragrances/attar/bakhoor | shopify_products_json | 3.500 | high |
| 7 | junaidperfumes.com | fragrances/oud | shopify_products_json | 23.000 | high |
| 8 | bh.azhaperfumes.com | fragrances | shopify_products_json | 27.000 | high |
| 9 | bh.afnan.com | fragrances | shopify_products_json | 11.000 | high |
| 10 | bh.getkuwa.com | supplements/vitamins/protein | shopify_products_json | 12.000 | high |
| 11 | bh.redtagfashion.com (→ rtbahplus.myshopify.com) | fashion (value) | shopify_products_json | 3.200 (meta.json=BHD) | high |
| 12 | blankbeautybh.com | skincare/makeup/K-beauty | shopify_products_json | 8.000 | high |
| 13 | bhplus.shop | other/gadgets/watches | shopify_products_json | 12.000 | high |
| 14 | goldencollections.net | fragrances/beauty | shopify_products_json | 6.600 | medium |
| 15 | betocosmetics.com | beauty/skincare/haircare | shopify_products_json | 3.500 | medium |
| 16 | valourapparel.com | fashion/activewear | shopify_products_json | 13.000 | medium |
| 17 | alzainjewellery.com | jewellery/watches | shopify_products_json | 5500.000 | medium |
| 18 | hmmba.com | home/kitchen/coffee | shopify_products_json | 7.000 | medium |
| 19 | trendbendersbh.com | beauty/haircare/gadgets | shopify_products_json | 23.500 | medium |
| 20 | ownperfumes.com | fragrances (Lattafa/Armaf) | json_api (WooCommerce Store API) | `"10500"` BHD | high |
| 21 | fragrancebh.com | fragrances | json_api (WooCommerce Store API) | `"10000"` BHD | high |
| 22 | purpleorchidbh.com | fragrances | json_api (WooCommerce Store API) | `"9000"` BHD | high |
| 23 | alibaksh.com | fragrances | json_api (WooCommerce Store API) | BHD 32.000 | high |
| 24 | nasserpharmacy.com *(in registry)* | supplements/skincare/makeup/haircare/fragrances | json_api (newapi) | BHD | high |
| 25 | dubizzle.com.bh | electronics/used (classifieds) | json_api (`__NEXT_DATA__`) | `"price":94` BHD | high |

> **WooCommerce Store API is the under-used keystone here.** Any BH WooCommerce store exposes
> `GET /wp-json/wc/store/products?per_page=100&page=N` returning `prices.price` (minor_unit=3, so
> `"10500"` = 10.500) + `prices.currency_code="BHD"` — zero-cost, paginated, genuine. Four verified
> fragrance stores (#20–23) follow this exact shape; **one adapter covers all four** and any future
> BH WooCommerce store.

### 2B. Genuine BHD — `sitemap_jsonld` (off-clock index + curl PDP) — WIRE SECOND

| # | Domain | Categories | Discovery | Sample price | Conf |
|---|---|---|---|---|---|
| 26 | bn.boots.com | skincare/makeup/haircare/supplements/fragrances | sitemap index → `product-sitemap-bh.xml` (4835 PDPs) | `"price":10.62,"BHD"` | high |
| 27 | ymhonlinepharmacy.com.bh | supplements/skincare/makeup/baby | `/product-sitemap.xml` (WP, ~1000 PDPs) | `"price":"9.889","BHD"` | high |
| 28 | healbahrain.com | skincare/supplements/haircare | `/sitemap.xml` (OpenCart, 1.55MB) | BHD 7.530 | high |
| 29 | aldeerahpharmacy.com | supplements/vitamins/baby | `/sitemap.xml` (Odoo, 650+ URLs) | 4.730 BD | high* |
| 30 | comparebh.com | electronics (multi-retailer aggregator) | Yoast `product-sitemap.xml` | `"price":"107.90","BHD"` | high |
| 31 | bh.labeb.com | electronics (aggregator) | multi-part `sitemap1-1.xml` | AggregateOffer `lowPrice:110.85 BHD` | high |
| 32 | mobile57.com | smartphones/tablets (aggregator) | `sitemap-bahrain.xml` | `"price":"507","BHD"` | high |
| 33 | bh.opensooq.com | electronics/used (classifieds) | listing JSON-LD | `"price":"220","BHD"` | high |
| 34 | bh.arabianoud.com | fragrances/oud/bakhoor | Salla sitemap + PDP JSON-LD | 49.005 BHD | high |
| 35 | vogacloset.com (`/bahrain/en/`) | haircare/makeup/fashion | JSON-LD | `price:16.5,BHD` | high |
| 36 | alosraonline.com | grocery/FMCG | sitemap + **Googlebot-UA** JSON-LD | `"price":0.4,"BHD"` | high |
| 37 | aljazirasupermarkets.com | grocery/FMCG | `/sitemap.xml` + Magento microdata (Googlebot-UA) | `data-price-amount="0.925"` BD | high |
| 38 | boutiqaat.com *(in registry)* | makeup/skincare/haircare/fragrances | own 47k-PDP products-sitemap + curl JSON-LD | `"28.290","BHD"` | high |

*\#29 aldeerah: category-page + sitemap evidence is solid; the sample PDP slug 404'd on re-fetch
(Odoo slug-id drift) — resolve PDPs from the live sitemap, do not hard-code slugs.*

> **`alosraonline.com` + `aljazirasupermarkets.com` need a `Googlebot/2.1` User-Agent** to get the
> SSR'd price (a normal-UA curl returns only the React PWA shell). The sitemap adapter must send a
> bot UA for these two. This is the cheapest path to BH **grocery** (the historically weakest category).

### 2C. Genuine BHD — `curl_jsonld` (plain curl, static price) — WIRE SECOND

| # | Domain | Categories | Price markup | Sample price | Conf |
|---|---|---|---|---|---|
| 39 | bahrainpharmacy.com *(in registry)* | skincare/makeup/supplements/haircare | JSON-LD | `"7.690","BHD"` | high |
| 40 | shop.alharamainperfumes.com (`/bahrain/`) | fragrances/oud/attar/bakhoor | Magento HTML | BHD 40.50 | high |
| 41 | bahrain.ounass.com *(in registry)* | fragrances/makeup/skincare/fashion (luxury) | raw HTML | 159.25 BHD | high |
| 42 | bahrain.sharafdg.com *(in registry)* | fragrances/electronics/beauty | raw HTML | BHD 12.885 | high† |
| 43 | bahrain.microless.com *(in registry)* | electronics/gaming/fragrances | static HTML | BHD 8.676 | high |
| 44 | godukkan.com (`/bahrain_en/`) | electronics (Apple/Magento) | raw HTML + JSON-LD | BHD 420.97 | high |
| 45 | ishopbahrain.com | electronics (WooCommerce) | raw HTML | BHD 386.97–483.97 | high |
| 46 | bheshop.com | electronics (Samsung official) | raw HTML | 490.000 BHD | high |
| 47 | gamesgravity.net | gaming/consoles (WooCommerce) | raw HTML | BHD 329.999 | high |
| 48 | skinbeautybh.com | skincare/makeup (WooCommerce) | raw HTML | 8.000 BHD | high |
| 49 | dukakeen.com | grocery/electronics (WooCommerce) | JSON-LD | `"11.000","BHD"` | high |
| 50 | megamart.bh | grocery/FMCG (Django Oscar) | span-split HTML | BD 0.890 | high |
| 51 | dyson.com.bh (`/en-BH/`) | hair tools (official) | raw HTML | BHD299.00 | high |
| 52 | centrepointstores.com (`/bh/en/`) | fashion (Landmark) | category-page Product JSON-LD | `4.25,"BHD"` | high‡ |
| 53 | splashfashions.com (`/bh/en/`) | fashion (Landmark) | category-page Product JSON-LD | `13,"BHD"` | high‡ |
| 54 | maxfashion.com (`/bh/en/`) | fashion (Landmark) | category-page Product JSON-LD | `9,"BHD"` | high‡ |
| 55 | brandsforless.com (`/en-bh/`) | fashion (off-price) | React state JSON | `161.9,"BHD"` | high‡ |
| 56 | bdutyfree.com | fragrances/makeup/electronics/watches | microdata + sitemap | BHD 74.500 | high |
| 57 | nespresso.com (`/bh/en/`) | coffee/grocery/appliances (official) | raw HTML + `"price":284.9` | BHD284.90 | high |
| 58 | asteribeauty.com (`/en-BH/`) | makeup/cosmetics | SFCC raw HTML | BHD 14.000 | high |
| 59 | buymode.shop (`/bahrain-en`) | electronics/home/gadgets | raw HTML (`NN.NNBHD`) | 9.25BHD | medium |
| 60 | bahrain.ahmarket.com | electronics/appliances/grocery/makeup | Magento HTML | 27.75 BHD | medium |

*†/‡ caveats:* `sharafdg` has BOTH a curl-scrapeable fragrance/beauty surface AND an Algolia-served
electronics surface — see §3 (treat electronics PDPs as `algolia`/`render`, beauty/fragrance listing
pages as `curl_jsonld`). The 4 Landmark fashion stores (`centrepoint`/`splash`/`max`/`brandsforless`)
serve the **category/listing** page JSON-LD to curl but the **individual PDP** loads price
client-side → **scrape the category pages, not the PDPs**.

### 2D. GCC-convertible — zero-cost JSON (convert to BHD via `exchange_rate_service`)

| # | Domain | Currency | Categories | Mechanism | Sample | Conf |
|---|---|---|---|---|---|---|
| 61 | beautytribe.com | AED | haircare/makeup/skincare (Kerastase/ghd/Olaplex) | shopify_products_json | 88.00 | high |
| 62 | rasasistore.com | AED | fragrances (official Rasasi) | shopify_products_json | 175.00 | high |
| 63 | ardalzaafaranshop.com | AED | fragrances (official) | shopify_products_json | 130.00 | high |
| 64 | swissarabian.com | USD | fragrances (official) | shopify_products_json | 74.00 | high |
| 65 | olaplex.com | USD | haircare (brand-direct) | shopify_products_json | 90.00 | high |
| 66 | parisgallery.ae | AED | fragrances (Amouage/niche) | shopify_products_json | 2137.50 | high |
| 67 | albayanperfumes.com | SAR | fragrances (dupes) | shopify_products_json | 65.00 | high |
| 68 | kuludonline.com | QAR | supplements/skincare | shopify_products_json | 163.00 | high |
| 69 | myaster.com | AED | haircare/supplements/pharmacy | json_api (`__NEXT_DATA__`) | 121 | high |

### 2E. GCC-convertible — `curl_jsonld` / `sitemap_jsonld` (convert to BHD)

| # | Domain | Currency | Categories | Mechanism | Sample | Conf |
|---|---|---|---|---|---|---|
| 70 | niceonesa.com | SAR | makeup/skincare/fragrances/haircare | sitemap_jsonld (Zid) | 194.47 SAR | high |
| 71 | lifepharmacy.com | AED | supplements/pharmacy | sitemap_jsonld | AED 68.25 | high |
| 72 | mumzworld.com (`/bh-en`) | BHD* | supplements/baby | curl_jsonld | BHD9.21 | high |
| 73 | caretobeauty.com (`/bh/`) | USD | skincare/makeup/haircare | curl_jsonld | `"13.54","USD"` | high |
| 74 | bh.cosmostore.org | USD | skincare/makeup/fragrances | curl_jsonld | `"14.95","USD"` | high |
| 75 | ounass.ae | AED | fragrances/makeup/fashion | curl_jsonld | 858 AED | high |
| 76 | faces.ae | AED | fragrances/makeup/skincare (SFCC) | curl_jsonld | from 1105 AED | high |
| 77 | amazon.ae | AED | all (needs browser UA / curl_cffi) | curl_jsonld | a-price-whole AED | high |
| 78 | pricena.com (`ae`/`sa`/`kw`/`qa`) | AED/SAR/KWD/QAR | electronics (aggregator) | curl_jsonld (`data-price`) | KWD 196.47 | medium |

*\#72 mumzworld serves a BHD price on `/bh-en` but some SKUs flag "does not ship to Bahrain" — the
price is genuine, ship-eligibility varies per SKU.*

### 2F. `algolia` (genuine BHD, needs index key extraction)

| # | Domain | Currency | Categories | Note | Conf |
|---|---|---|---|---|---|
| 79 | goldenscent.com | BHD | fragrances/makeup/skincare/haircare | BHD in embedded multi-currency Algolia record (`"BHD":{"default":81}`); ld+json defaults SAR | high |
| 80 | en-bh.6thstreet.com *(in registry)* | BHD | fashion (+ beauty via separate index) | public Algolia index — `algolia_service.fetch_algolia_price` already wired | high |

### 2G. `render_required` (deprioritize — paid render only)

| # | Domain | Currency | Why | Conf |
|---|---|---|---|---|
| 81 | noon.com (`/bahrain-en/`) | BHD | Akamai TLS-fingerprint wall (HTTP 000 to curl); price in Next RSC | medium |
| 82 | bahrain.desertcart.com | BHD | Cloudflare "Just a moment" challenge on PDPs | medium |
| 83 | ubuy.com.bh | BHD | PDP price JS-injected (listing pages curl-readable) | medium |
| 84 | amazon.sa | SAR | same Amazon stack as .ae; bot-walled, needs curl_cffi | medium |
| 85 | carrefouruae.com | AED | Akamai edge-block (53-byte empty shell); **Carrefour BH defunct since 2025-09-14** | medium |

---

## 3. Integration map (group → adapter)

The codebase already has the adapter family and the registry `Source` descriptor with
`mechanism` field + per-mechanism selectors in `source_router.py`. **No new architecture is
required — only new `Source(...)` rows + (in two cases) generalizing an existing adapter.**

### Group A — `shopify_products_json` → `price_service.fetch_shopify_price` (`is_shopify=True`)
- **Already wired pattern:** `get_shopify_sources_for_category()` → `fetch_shopify_price()` hits
  `{domain}/products.json` directly. Live examples: sonyworld.bh, shopalmoayyed.com, en-bh.ajmal.com.
- **Add rows for:** all of §2A (#1, 3, 7–19) + §2D Shopify (#61–68). **Zero adapter work** — set
  `is_shopify=True, currency="BHD"` (or the GCC currency) and they flow through the existing cascade.
- **Catalog/PDP resolution:** `fetch_shopify_price` already does title-match against `products.json`.
  For GCC-currency Shopify stores, the converted-USD/AED path stamps `converted_usd`/`converted` —
  already supported.

### Group B — `json_api` → `nasser`-style `fetch_X_price` (`mechanism="json_api"`)
- **Already wired pattern:** `fetch_nasser_price()` + `get_jsonapi_sources_for_category()`.
- **Two sub-shapes to add:**
  1. **WooCommerce Store API** (ownperfumes/fragrancebh/purpleorchid/alibaksh, #20–23) — `GET
     /wp-json/wc/store/products?per_page=100&page=N`, read `prices.price`(minor_unit=3) +
     `prices.currency_code`. **Build ONE `fetch_woocommerce_store_api_price` adapter** keyed by a
     `mechanism="json_api"` + a `json_api_kind="woo_store"` discriminator (or a per-domain endpoint
     template field) — covers all four + any future BH Woo store.
  2. **Next `__NEXT_DATA__`** (myaster #69, dubizzle #25) — read embedded JSON from the SSR HTML.
     This is a curl that parses JSON-from-HTML; can reuse `fetch_page_price` with a `__NEXT_DATA__`
     extractor branch, OR a small `fetch_next_data_price`.
- **Highest ROI in this group:** the WooCommerce Store API adapter (4 genuine-BHD fragrance stores
  for the price of one adapter).

### Group C — `sitemap_jsonld` → `bolo`/`boutiqaat`-style (sitemap index + curl) (`mechanism="sitemap"`)
- **Already wired pattern:** `cron_index_sitemaps.py` builds the `{slug → pdp_url}` Redis index
  off-clock for every `mechanism="sitemap"` BH-tier source; the 15s request path reads the index
  (`sitemap_discovery_service`) then curls the PDP via `fetch_bolo_price`/`fetch_page_price`.
- **Add rows + `_INDEX_URLS` entries for:** §2B (#26–37). Most have a standard
  `/sitemap.xml` or `/product-sitemap.xml` (WP/Yoast/OpenCart/Odoo). Add their index URLs to
  `cron_index_sitemaps._INDEX_URLS` (the builder falls back to `https://www.{domain}/sitemap.xml`).
- **Two special-casings:**
  - **bn.boots.com** — index = `product-sitemap-bh.xml`; **fetch PDPs WITHOUT the `.html` suffix**
    (the `.html` form 301s). 4835 BH PDPs.
  - **alosraonline.com / aljazirasupermarkets.com** — the curl-PDP step needs a **`Googlebot/2.1`
    User-Agent** to get the SSR'd price (normal UA → empty React shell). Add a per-source UA override.
- **boutiqaat already in registry** as `mechanism="sitemap"`; the men+women section index split is
  already handled in `_INDEX_URLS`.

### Group D — `curl_jsonld` → `price_service.fetch_page_price` (`mechanism="curl"`)
- **Already wired pattern:** `fetch_page_price` curls a PDP and extracts JSON-LD/OG/microdata.
- **Add rows for:** §2C (#39–60) + §2E curl rows (#72–78). These need a **PDP URL** — supply it via
  Serper `site:{domain}` discovery (existing path) OR a sitemap (several of these ALSO have sitemaps,
  so they could be `mechanism="sitemap"` for cheaper discovery — prefer sitemap where one exists).
- **Markup variants `fetch_page_price` must handle (most already do):** JSON-LD `Product/Offer`,
  Magento `data-price-amount` microdata (aljazira, ahmarket), span-split price (megamart Django
  Oscar — `<span class=intiger>/<span class=decimal>`), React/Next state JSON (brandsforless),
  microdata `itemprop=price` (bdutyfree). The Django-Oscar span-split + the `NN.NNBHD` suffix
  (buymode) are the only two that may need a new extractor branch.
- **Landmark fashion (#52–55):** scrape the **category/listing** page (Product JSON-LD present) NOT
  the PDP (price client-side). Model these as listing-scrape sources.

### Group E — `algolia` → `algolia_service.fetch_algolia_price` (`is_algolia=True`)
- **Already wired:** 6thStreet. **Add goldenscent.com** — but its BHD lives in an *embedded*
  multi-currency record in the PDP HTML (`"BHD":{"default":81}`), so the cheapest path is actually a
  **curl + extract the embedded record** (no Algolia query needed). Tag `mechanism="curl"` with a
  goldenscent-specific extractor (read `BHD.default`, ignore the buggy `default_formated` label and
  the SAR ld+json). Reserve the live Algolia query for sharafdg-electronics if pursued.

### Group F — `render_required` → Firecrawl/Scrape.do (`is_render_only=True`) — DO NOT WIRE YET
- noon, desertcart, ubuy(PDP), amazon.sa, carrefour. High catalog breadth but paid + bot-walled.
  Leave for the render tier; not part of the $0 genuine-share push.

### Highest-ROI sources to wire FIRST (most categories × cheapest scrape × genuine BHD)

1. **WooCommerce Store API adapter** (ownperfumes, fragrancebh, purpleorchid, alibaksh) — one
   adapter, 4 genuine-BHD fragrance stores, $0.
2. **bh.jashanmal.com** (Shopify) — fragrances + makeup + appliances + fashion + home in ONE
   genuine-BHD `/products.json`. Broadest single source.
3. **bh.getkuwa.com** (Shopify) — genuine-BHD **supplements** (the category with the worst current
   coverage; today supplements return pending/None).
4. **godukkan.com + ishopbahrain.com + bheshop.com + imachines.bh** (curl/Shopify) — genuine-BHD
   **electronics** PDPs (iPhone/Samsung/laptops) to replace converted_usd/estimate.
5. **bn.boots.com sitemap** — 4835 genuine-BHD skincare/makeup/haircare/supplement PDPs, off-clock
   indexable, standard adapter.
6. **alosraonline.com + megamart.bh + aljazirasupermarkets.com** — genuine-BHD **grocery** (curl +
   Googlebot-UA), the historically empty category.
7. **The 4 Landmark fashion + redtag Shopify** — genuine-BHD **fashion** (today fashion has no
   like-for-like basis and few prices).
8. **The remaining genuine-BHD Shopify fragrance/beauty stores** (junaid, azha, afnan, blankbeauty)
   — $0, additive.

---

## 4. Storage / architecture recommendation

The goal: scrapers hit **real data immediately**, not GPT estimates. Two stores, both tied to
existing pieces.

### 4.1 Sources registry (static, code or DB)

Today the registry is a Python list of `Source(...)` in `source_router.py` with a rich
`mechanism`/`locale_paths`/`currency`/`pdp_url_pattern`/`status` descriptor and per-mechanism
selectors (`get_shopify_sources_for_category`, `get_jsonapi_sources_for_category`,
`get_sitemap_sources_for_category`, `get_algolia_sources_for_category`). **Keep this as the source of
truth** — it is already exactly the right shape.

- **Action:** add the ~50 new rows from `data/bh_gcc_source_candidates.json`, each with
  `mechanism`, `currency`, `categories`, `tier="bahrain"` (or `"gcc"` for convertibles),
  `weight=3.0`/`1.5`, the cheapest mechanism flag (`is_shopify`/`mechanism="json_api"`/
  `mechanism="sitemap"`/`mechanism="curl"`/`is_algolia`), `sample_url` (liveness anchor) and
  `status="live"`/`"provider-test-candidate"`.
- **Liveness gate:** run each through `scripts/verify_source_registry.py` before flipping `status`
  to `live` (the existing Decision-F "verify-or-delete" posture). The `sample_url` in the seed JSON
  is the anchor for that check.
- **DB option (optional, later):** if the registry grows past ~150 rows or needs ops-time edits
  without a deploy, mirror it into a Supabase `price_sources` table
  (`domain PK, tier, categories text[], weight, mechanism, currency, locale_paths text[],
  pdp_url_pattern, sample_url, status, last_verified_at`) loaded at startup. Not needed yet — the
  Python list is fine for 50–100 rows and keeps it in code review.

### 4.2 Warmed-price store keyed by (product, region) with TTLs

Reuse the **existing two-layer price cache** (`price_service` L1 Redis + `product_data_service` L2
DB) — do not invent a new store. The TTL policy is already correct and source-method-aware:

| Price kind | L1 (Redis) | L2 (DB) | Set by |
|---|---|---|---|
| Genuine BHD (`_GENUINE_BH_SOURCE_METHODS`) | **7d** (`GENUINE_PRICE_CACHE_TTL`) | 7d (`GENUINE_L2_TTL`) | `price_cache_ttl_for()` |
| `converted_usd` | 24h (`PRICE_CACHE_TTL`) | 24h | default |
| Estimated / non-showable | 24h | 24h | default |
| Negative (no genuine source) | — | **30d** (`NEGATIVE_PRICE_CACHE_TTL`), capped to 24h for cold-sitemap | `should_negative_cache()` |

- **Cache key:** the existing `price:{normalized_product}:{region}` scheme (region = `bahrain`).
  The warmed entry is *identical in shape* to a live-scraped entry, so the request path reads it
  with zero new code (cache-first-before-scrape gate already exists).
- **`_GENUINE_BH_SOURCE_METHODS`** is the single switch that grants the 7d TTL — every new genuine-BHD
  adapter must stamp one of: `page_scrape`, `page_scrape_jsonld`, `local_bhd`, `shopify_json`,
  `official_brand` (or a render method). The WooCommerce Store API adapter should stamp
  `local_bhd` (or a new `woo_store_json` added to the genuine set). **This is the one code touch
  that makes a new adapter's price "stick" for 7 days.**

### 4.3 Cron / warmer flow (keep the $0 path $0)

Two **independent** off-clock jobs, both already present, both fail-closed:

1. **`scripts/cron_index_sitemaps.py`** (`ENABLE_SITEMAP_INDEX`, daily 03:00) — $0, Serper-free.
   Builds the `{slug → pdp_url}` Redis index for every `mechanism="sitemap"` source by curling the
   stores' OWN sitemaps. **Just add the new sitemap domains** to the registry + `_INDEX_URLS`; the
   cron auto-discovers them via `get_sitemap_sources_for_category`. This is the discovery half — it
   does NOT fetch prices.
2. **`scripts/cron_warm_price_cache.py`** (`ENABLE_PRICE_CACHE_WARMER`, schedule TBD) — pre-scrapes
   the gold/warmer catalog into the shared price cache with `PRICE_RACE_TIMEOUT=60` (off-clock, no
   15s wall). It uses the $0 adapters first (Shopify/json_api/sitemap/curl) and only falls to **paid
   Serper** for discovery when no $0 adapter resolves the product. **Most of the new sources are $0
   discovery** (Shopify `/products.json`, WooCommerce Store API, own-sitemap index) → the warmer can
   keep them fresh **without** burning Serper.

**The $0-vs-paid split is the headline architectural win:** with these sources, the *discovery* step
(product → PDP URL) for the majority of BH retail is now Serper-free:
- Shopify → `/products.json` (no discovery call at all — match in the catalog JSON).
- WooCommerce → `/wp-json/wc/store/products` (same — catalog JSON).
- sitemap stores → the off-clock Redis index (no per-request discovery call).
Paid Serper is then only needed for the `curl_jsonld` stores that lack a sitemap, and for the
render-tier. That is what unblocks "scrapers hit real data immediately instead of GPT estimates"
without a paid-Serper budget blowout.

**Recommended warmer-catalog growth:** extend `data/warmer_catalog.json` (today 16 structural
pairs) with one representative product per (category × top genuine-BHD source) so the warmer keeps
a genuine BHD price hot for the most-compared SKUs in each category.

---

## 5. Coverage / gap report

### Now well-covered (genuine BHD, $0 or near-$0)

| Category | Genuine-BHD sources | Cheapest mechanism |
|---|---|---|
| **Fragrances** | 14+ (jashanmal, ajmal, alhajis, asgharali, junaid, azha, afnan, ownperfumes, fragrancebh, purpleorchid, alibaksh, alharamain, arabianoud, goldencollections) + ounass/sharafdg/microless | shopify_products_json / WooCommerce json_api |
| **Skincare / Makeup** | bahrainpharmacy, ymh, heal, blankbeauty, skinbeauty, asteri, bn.boots, boutiqaat, sephora(render) | curl_jsonld / sitemap / shopify |
| **Electronics** | godukkan, ishopbahrain, bheshop, imachines, sonyworld, microless, sharafdg, comparebh, labeb, mobile57, gamesgravity | shopify / curl_jsonld / sitemap |
| **Haircare** | vogacloset, dyson.com.bh, gcc.lulu, beautytribe(AED), bn.boots | sitemap / curl / shopify |
| **Supplements** | bh.getkuwa (Shopify, BHD), aldeerah, ymh, bahrainpharmacy, bn.boots | shopify_products_json / sitemap |
| **Fashion** | centrepoint, splash, max, brandsforless, redtag(Shopify), 6thstreet(Algolia), valour | shopify / curl_jsonld (listing) |
| **Grocery** | alosraonline, megamart, aljazira, dukakeen, gcc.lulu, talabat(render) | sitemap (Googlebot-UA) / curl |

### Still thin / weak

1. **Grocery curl-fragility** — alosra + aljazira need a Googlebot UA; megamart needs span-parsing;
   no sitemap on megamart. Grocery is covered but the cheapest path is fussier than other categories.
   Talabat (the biggest BH grocery catalog) is Algolia/render-walled.
2. **Luxury Western fragrance/beauty in true BHD** — still partly structural: sephora.me, bolo.bh,
   noon are CF/Akamai-walled (render-only). Ounass BH + sharafdg + goldenscent(algolia) cover much of
   it, but the deep luxury tail (niche houses) still leans converted (ounass.ae AED) or render.
3. **Saudi/UAE-only convertibles for the convertible tail** — niceonesa (SAR), lifepharmacy (AED),
   rasasi/ardalzaafaran/swissarabian (AED/USD) fill brand-official gaps but need conversion; fine as
   a fallback, not a genuine-BHD win.
4. **Mega-marketplace breadth (noon)** — the single largest BHD catalog is render_required. Worth a
   dedicated Scrape.do-super / headless probe IF the $0 sources leave gaps, but the $0 sources above
   now cover most mainstream SKUs without it.

### What a follow-up discovery round should target

- **A Bahrain Talabat-Mart price path** (Algolia key extraction or the grocery JSON API) — biggest
  remaining grocery catalog.
- **A noon `/bahrain-en/` JSON/catalog API or curl_cffi(impersonate) path** — biggest remaining
  general BHD catalog; only worth it if a non-render path is found.
- **More BH WooCommerce stores** — the Store API pattern is so cheap that any additional BH Woo store
  is a free win; sweep SellerCenter / Salla / Woo BH store lists for more.
- **In-stock SKU re-probe of sharafdg/sporter/drnutrition supplements** (Algolia/CF-walled but
  genuine-BHD supplement+protein catalogs — high value if the key/PDP can be reached).

### Promote from `unverified_leads` (worth a second look)

| Lead | Why promote | Next step |
|---|---|---|
| **sporter.com** (`/en-bh`) | dedicated BHD supplement/sports-nutrition store; multi-GCC locales; only 403 blocked the fetch | re-probe via Scrape.do; if PDP has ld+json → curl_jsonld supplements |
| **niceone.bh** | BHD Nice One BH (SAR sister niceonesa.com already verified) — same Zid/Nuxt stack | re-probe past the TLS block → sitemap_jsonld |
| **halabh.com** | confirmed Shopify, en-BH locale (BHD); only `/products.json` was 401 | fetch a server-rendered collection/PDP (Shopify HTML) for the price |
| **GoBazzar** (`bh.gobazzar.com`) | real BH multi-store price-comparison engine w/ published app; only geo/edge-blocked from this env | re-probe from a GCC IP / headless → likely curl_jsonld or json_api BHD |
| **geekay.com** (`/bahrain_en`) | BHD gaming (PS5/Xbox/Nintendo); same Magento family as godukkan (verified) | curl_cffi browser UA → likely curl_jsonld |
| **drnutrition.com** (`/en-bh`) | dedicated BHD supplement store, multi-GCC | re-probe behind render/proxy |
| **soukare.com** (`/en-sa`) | GCC health/pharmacy, ships BH 3-5d, Solgar/Quest/Vitabiotics | re-probe; likely Shopify-class /products.json |
| **shop.samsung.com/bh** | official Samsung BH (BHD); SAP Hybris OCC API exists | find the baseSite code in the runtime JS → json_api |

---

## 6. Verification notes (this synthesis pass)

Re-fetched to confirm load-bearing mechanisms before cataloguing:
- `en-bh.ajmal.com/products.json` → valid Shopify, "Oud Nadir 50 gms" 48.000 ✓
- `ownperfumes.com/wp-json/wc/store/products` → valid WooCommerce Store API, "Lattafa Pride…" price
  `"10500"` currency `BHD` ✓ (confirms the json_api keystone)
- `bh.getkuwa.com/products.json` → valid Shopify (WEGOVY 1199.000), BHD base ✓ (supplements win)
- `aldeerahpharmacy.com` sample PDP → 404 (Odoo slug drift) — kept high-conf on category+sitemap
  evidence; resolve PDPs from the live sitemap, never hard-code slugs.

All other entries carry the original finder's literal-price evidence (a real fetch showing the price
string), per the verify-or-omit mission rule.

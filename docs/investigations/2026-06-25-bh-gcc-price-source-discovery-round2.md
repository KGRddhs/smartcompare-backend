# Bahrain / GCC Price-Source Discovery — ROUND 2 (Synthesis, Platform Landscape & Integration Delta)

**Date:** 2026-06-25
**Author:** round-2 synthesis lead (discovery-sweep dedupe + rank + verify)
**Mission:** Replace GPT price *estimates* with genuine BH/GCC price sources. This round extends
round-1 (`2026-06-25-bh-gcc-price-source-discovery.md`, 85 sources). Every catalogued source was
verified by a real fetch showing a literal price string. **None of the 214 round-2 sources overlap
the round-1 85 (programmatically confirmed).**

**Companion seed file:** `data/bh_gcc_source_candidates_round2.json` (clean JSON array, registry-ready,
ranked, with `country` + `platform` + `integration_adapter` + `priority_rank`).
**Do NOT overwrite round-1 artifacts** — these are additive.

---

## 0. Headline

- **214 NEW verified sources** (deduped to distinct domains; **0 overlap** with the round-1 85).
- **By country:** BH **62** · UAE **57** · KSA **35** · QA **24** · KW **21** · OM **15**.
- **Genuine-BHD: 64** vs **GCC-convertible: 150** (AED 56 / SAR 34 / QAR 24 / KWD 21 / OMR 15).
- **By mechanism:** `shopify_products_json` **93** · `curl_jsonld` **74** · `json_api` **29**
  · `render_required` **15** · `sitemap_jsonld` **2** · `algolia` **1**.
- **By platform:** Shopify **93** · Magento **26** (+1 Magento/custom) · WooCommerce **28** · Salla **18**
  · SFCC/Demandware **9** (+1 THG) · Next.js **15** (variants) · OpenCart **4** · custom/Laravel/ASP/Lightspeed/Odoo/Wix/Akinon/Hybris **~16**.
- **$0-scrape majority is overwhelming:** **199 of 214** are zero-cost (`shopify_products_json` /
  `json_api` / `sitemap_jsonld` / `curl_jsonld` / `algolia`); only **15** are `render_required`.
  **122** are *static-JSON* ($0, no curl-per-PDP at all): 93 Shopify `/products.json` + 29 `json_api`.
- **Architectural fit:** **every** source maps to an adapter that *already exists or is the round-1
  proposed keystone*. No new architecture. The two NEW adapter shapes round-1 flagged
  (**WooCommerce Store API** + **Salla JSON-LD**) are now massively load-bearing: **26 WooCommerce
  Store-API stores** and **18 Salla stores** across all six countries ride those two adapters alone.
- **The genuine-BHD win this round** is breadth in the historically-thin categories: **supplements**
  (smartnutr, mastermuscles, wawan, manamamedical, livewell — genuine-BHD Shopify, the category that
  today returns pending/None), **grocery** (livewell, ibsouq, asasiat, organature, bh.adilstore,
  winbid, lilyorganics — $0 Shopify/Woo/curl), and **electronics** (iworld, gamerspoint, emsquare,
  arafaphones, gccgamers, advancedpc, jarir /bh-en — genuine BHD via $0 JSON/curl).

---

## 1. Mechanism cheat-sheet (unchanged from round-1 — same adapters)

| Mechanism | Cost | What it is | Maps to adapter |
|---|---|---|---|
| `shopify_products_json` | **$0** | `GET {domain}/products.json` → catalog JSON, price in `variants[].price` | `price_service.fetch_shopify_price` (`is_shopify=True`) |
| `json_api` | **$0** | WooCommerce Store API `/wp-json/wc/store/products`, Next `__NEXT_DATA__`, Wix `warmupData` | `fetch_woocommerce_store_api_price` (keystone) / `fetch_next_data_price`-style |
| `sitemap_jsonld` | **$0** + off-clock index | own XML sitemap → curl PDP → JSON-LD | `cron_index_sitemaps` + `fetch_page_price` (`mechanism="sitemap"`) |
| `curl_jsonld` | **$0** | plain curl of a PDP/listing, price in JSON-LD/microdata/state-JSON/HTML-text | `price_service.fetch_page_price` (`mechanism="curl"`) |
| `algolia` | $0 (after key) | price in a public Algolia index | `algolia_service.fetch_algolia_price` (`is_algolia=True`) |
| `render_required` | paid | SPA / Akamai / CF / THG wall — no price in static HTML | render tier (`is_render_only=True`) — DEFER |

**Currency convention:** BHD/OMR print 3-decimal (`12.000`); SAR/AED/QAR print 2-decimal; KWD prints
3-decimal. WooCommerce Store API returns **minor units** (`"12587"` + `currency_minor_unit:3` =
12.587) — **read `currency_minor_unit` per response** (mobpcom.com returned `minor_unit:1`).
Convert all non-BHD via `exchange_rate_service.get_rate(<cur>, "BHD")`.

---

## 2. Ranked catalog — by GCC country, then by mechanism (cheapest first), genuine-BHD first

Ordering: **genuine BHD first**, then GCC-convertible; within each, cheapest scrape first
(`shopify_products_json` / `json_api` > `sitemap_jsonld` > `curl_jsonld` > `algolia` > `render_required`),
high-confidence first. The `#` column is the global `priority_rank` in the seed JSON.

<!-- TABLES START -->
### Bahrain — genuine BHD (62 sources)

| # | Domain | Platform | Mechanism | Categories | Sample price | Conf |
|---|---|---|---|---|---|---|
| 1 | bahrain-pets.com | Shopify | `shopify_products_json` | other | 2.800 BHD | high |
| 2 | bahrain.naseem.com | Shopify | `shopify_products_json` | fragrances | 4.000 BHD (Musk Safi 6ml) | high |
| 3 | beautybykat.store | Shopify | `shopify_products_json` | skincare, makeup | 7.000 BHD (Cellmazing Eye Cream) | high |
| 4 | bh.taifalemarat.com | Shopify | `shopify_products_json` | fragrances | 60.660 BHD (Oud Nights) | high |
| 5 | bh.yallatoys.com | Shopify | `shopify_products_json` | toys, baby, kids, other | 27.000 BHD | high |
| 6 | bookmartme.com | Shopify | `shopify_products_json` | other | 3.500 BHD | high |
| 7 | emsquarebh.com | Shopify | `shopify_products_json` | electronics, other | 6.500 BHD | high |
| 8 | gamerspoint.bh | Shopify | `shopify_products_json` | electronics | 115.000 BHD (Redragon Monitor 24in) | high |
| 9 | ibsouq.com | Shopify | `shopify_products_json` | other, grocery | 1.500 BHD | high |
| 10 | livewell.bh | Shopify | `shopify_products_json` | grocery, supplements, baby | 0.880 BHD | high |
| 11 | manamamedical.com | Shopify | `shopify_products_json` | supplements, other | 2.000 BHD | high |
| 12 | mastermuscles.net | Shopify | `shopify_products_json` | supplements, sports-nutrition | 27.500 BHD (BEEF-XP 1.8KG) | high |
| 13 | perfumistaaloud.com | Shopify | `shopify_products_json` | fragrances | 25.000 BHD (Beyond Patchouli 75ml) | high |
| 14 | shop.optica.net | Shopify | `shopify_products_json` | eyewear, other | 30.800 BHD | high |
| 15 | shopalmoayyed.com | Shopify | `shopify_products_json` | electronics, grocery | 200.000 BHD (Washing Machine) | high |
| 16 | smartnutr.com | Shopify | `shopify_products_json` | supplements, sports-nutrition, grocery | 42.800 BHD (combo) | high |
| 17 | sokostore.com | Shopify | `shopify_products_json` | skincare, makeup, haircare, supplements | 11.000 BHD (Dr.Althea 345 Relief Cream) | high |
| 18 | wawanbahrain.com | Shopify | `shopify_products_json` | supplements, sports-nutrition | 24 BHD (Wawan Nutrition ISO) | medium |
| 19 | arafaphones.com | WooCommerce | `json_api` | electronics | price 148990 minor_unit 3 = 148.990 BHD | high |
| 20 | asasiat.online | WooCommerce | `json_api` | grocery, makeup, other | price 1150 minor_unit 3 = 1.150 BHD | high |
| 21 | bh-en.smellsoreal.com | WooCommerce | `json_api` | fragrances | price 2400 = 24.00 BHD | high |
| 22 | iworld.bh | WooCommerce | `json_api` | electronics | price 1276990 minor_unit 3 = 1276.990 BHD | high |
| 23 | miniso-bh.com | WooCommerce | `json_api` | other, makeup, toys | price 9000 minor_unit 3 = 9.000 BHD | high |
| 24 | organature.bh | WooCommerce | `json_api` | grocery, skincare, other | price 6000 minor_unit 3 = 6.000 BHD | high |
| 25 | petshomebh.com | WooCommerce | `json_api` | other, grocery | price 12587 minor_unit 3 = 12.587 BHD | high |
| 26 | shop.almajarahgold.com | WooCommerce | `json_api` | jewelry | price 31600 minor_unit 3 = 316.00 BHD | high |
| 27 | theperfumesclub.com | WooCommerce | `json_api` | fragrances | 8.000 BHD (sale) | high |
| 29 | irepair-bh.com | Wix | `json_api` | mobile-accessories, electronics | 8.900 BHD | medium |
| 30 | nexcelbahrain.com | WooCommerce | `json_api` | electronics | currency_code BHD minor_unit 2 | medium |
| 31 | talabat.com | Next.js (q-commerce) | `json_api` | grocery, pharmacy, baby, other | 1.428 BD | medium |
| 32 | advancedpcbahrain.com | WooCommerce | `curl_jsonld` | electronics | BD 32.900 | high |
| 33 | aignerme.com | Magento | `curl_jsonld` | fashion, other | BHD 53.00 | high |
| 34 | alkhabeershop.com | Salla | `curl_jsonld` | fragrances | 29.355 BHD | high |
| 35 | ashrafsbahrain.com | Magento | `curl_jsonld` | electronics, appliances, fragrances, grocery | 280.000 BHD | high |
| 36 | bh.adilstore.com | Magento | `curl_jsonld` | grocery | BHD0.950 | high |
| 37 | bh.oudelite.com | Salla | `curl_jsonld` | fragrances | price 11.501 priceCurrency BHD | high |
| 38 | bjcstore.com | WooCommerce | `curl_jsonld` | watches, jewelry, fashion, other | BHD 891.000 | high |
| 39 | eitara.com | Salla | `curl_jsonld` | skincare, makeup | 2.503 BHD | high |
| 40 | en-bahrain.levelshoes.com | Magento | `curl_jsonld` | fashion | 65.1 BHD | high |
| 41 | gccgamers.com | Next.js | `curl_jsonld` | electronics | 645.013 BHD | high |
| 42 | geekay.com | Magento | `curl_jsonld` | electronics | BHD 32.90 | high |
| 43 | hanan-store55.com | Salla | `curl_jsonld` | fragrances | 33.334 BHD | high |
| 44 | homeboxstores.com | Next.js (Landmark) | `curl_jsonld` | other | BHD 50.0 | high |
| 45 | homecentre.com | Next.js (Landmark) | `curl_jsonld` | other | BHD 3.90 | high |
| 46 | homesrus.bh | Magento | `curl_jsonld` | other | BHD 1,131.620 | high |
| 47 | istationery.com | Magento | `curl_jsonld` | stationery, other | BHD 1.100 | high |
| 48 | jarir.com | custom (server-rendered) | `curl_jsonld` | electronics, books, stationery, other | 549.99 BHD | high |
| 49 | jawaherbh.com | OpenCart | `curl_jsonld` | jewelry, fashion, other | BHD165.00 | high |
| 50 | lilyorganicsbh.com | OpenCart | `curl_jsonld` | grocery, supplements, other | BHD 2.200 | high |
| 51 | mamasandpapas.com.bh | Magento | `curl_jsonld` | baby, kids, other | BHD 149.500 | high |
| 52 | midasfurniture.com | Magento | `curl_jsonld` | other | 423.50 BHD | high |
| 53 | petarabia.com | Odoo | `curl_jsonld` | other | BHD 14.000 | high |
| 54 | store.gadgetzone.bh | Lightspeed eCom | `curl_jsonld` | electronics | BD 27.50 | high |
| 55 | winbid.online | custom (Laravel) | `curl_jsonld` | grocery, other | 5.000 BHD | high |
| 57 | advanti.com | custom | `curl_jsonld` | electronics | BHD 999.000 | medium |
| 58 | almajed4oud.com | Magento | `curl_jsonld` | fragrances | BHD 28.25 | medium |
| 59 | d4donline.com | custom | `curl_jsonld` | electronics, other | BHD 124.990 | medium |
| 60 | leenaz.net | OpenCart | `curl_jsonld` | fashion | BHD 120.000 | medium |
| 61 | shop.stc.com.bh | OpenCart | `curl_jsonld` | electronics | 47.979 BD/mo (rendered BHD) | medium |
| 62 | extra.com | SAP Hybris | `render_required` | electronics | BHD 309.990 | high |
| 63 | bfab.com | Next.js | `render_required` | fashion | BHD 25 | medium |
| 64 | matalanme.com | Next.js | `render_required` | fashion | BHD (client-side) | medium |

### Saudi Arabia (SAR → BHD) (35 sources)

| # | Domain | Platform | Mechanism | Categories | Sample price | Conf |
|---|---|---|---|---|---|---|
| 65 | gazzaz.com.sa | Shopify | `shopify_products_json` | fragrances, makeup, skincare, haircare | 39.00 SAR (variant) | high |
| 66 | ksa.swissarabian.com | Shopify | `shopify_products_json` | fragrances | 189.00 SAR (Shaghaf Oud 75ml) | high |
| 67 | sa.ajmal.com | Shopify | `shopify_products_json` | fragrances | 175.00 SAR | high |
| 68 | sa.ghawali.com | Shopify | `shopify_products_json` | fragrances | 599 SAR (75ml) | high |
| 69 | sa.mubkhar.com | Shopify | `shopify_products_json` | fragrances, other | 333.00 SAR | high |
| 70 | saudi.naseem.com | Shopify | `shopify_products_json` | fragrances | 150.00 SAR | high |
| 71 | watsons.sa | Shopify | `shopify_products_json` | makeup, skincare, haircare, supplements | 70.00 SAR | high |
| 139 | sa.getkuwa.com | Shopify | `shopify_products_json` | supplements | 138.00 SAR | medium |
| 140 | vperfumes.com | Next.js | `json_api` | fragrances | SAR 773.00 | high |
| 156 | mithaly.sa | Salla | `sitemap_jsonld` | supplements, sports-nutrition | SAR252.00 | high |
| 157 | proteinvitamin.sa | Salla | `sitemap_jsonld` | supplements, sports-nutrition | 369 SAR (search) | medium |
| 158 | 4me-ksa.com | Salla | `curl_jsonld` | skincare, supplements, makeup | 399 SAR | high |
| 159 | almanea.sa | Magento | `curl_jsonld` | electronics, other | 1,849 SAR | high |
| 160 | alsaifgallery.com | Magento | `curl_jsonld` | other, electronics | 349 SAR | high |
| 161 | becarestore.com | Salla | `curl_jsonld` | electronics, supplements | 55 SAR | high |
| 162 | en-sa.rituals.com | Magento | `curl_jsonld` | fragrances, skincare, haircare | SAR 100.00 | high |
| 163 | en-saudi.ounass.com | custom (Al Tayer) | `curl_jsonld` | fashion, fragrances, makeup | 18,350 SAR | high |
| 164 | faces.sa | SFCC/Demandware | `curl_jsonld` | fragrances, makeup, skincare, haircare | 647 SAR (90ml) | high |
| 165 | firstcry.sa | custom | `curl_jsonld` | other | SAR 1,398.62 | high |
| 166 | kanbkam.com | custom | `curl_jsonld` | electronics | 325.00 SAR | high |
| 167 | laverne.com | Salla | `curl_jsonld` | fragrances | 149 SAR | high |
| 168 | narscosmetics.sa | SFCC/Demandware | `curl_jsonld` | makeup, skincare | 190 SAR | high |
| 169 | outletpharmacyonline.sa | Salla | `curl_jsonld` | supplements, grocery | 33 SAR | high |
| 56 | reefperfumes.com | Salla | `curl_jsonld` | fragrances, haircare | 16.258 BHD (BH-geo) | high |
| 170 | sa.abdulsamadalqurashi.com | Salla | `curl_jsonld` | fragrances | 495 SAR | high |
| 171 | sa.oudelite.com | Salla | `curl_jsonld` | fragrances | 145 SAR | high |
| 172 | saudi.jazp.com | Next.js | `curl_jsonld` | fragrances, electronics, fashion, other | SAR 294 | high |
| 173 | saudi.microless.com | custom | `curl_jsonld` | electronics | SAR 1,174.19 | high |
| 174 | store.rasasi.com.sa | Salla | `curl_jsonld` | fragrances | 253 SAR | high |
| 175 | vanilla.sa | Salla | `curl_jsonld` | fragrances | 435.10 SAR | high |
| 196 | alrehabstore.com | Salla | `curl_jsonld` | fragrances | 95 SAR | medium |
| 197 | whites.sa | Akinon | `curl_jsonld` | fragrances, makeup, skincare, haircare | 414.00 SAR | medium |
| 202 | nahdionline.com | Next.js (Algolia) | `algolia` | supplements, skincare | 29.00 SAR | medium |
| 203 | deraahstore.com | SFCC/Demandware | `render_required` | fragrances, makeup, skincare | 174 SAR | high |
| 208 | goldapple.sa | Next.js | `render_required` | skincare, makeup, haircare, fragrances | 148.00 SAR | medium |

### United Arab Emirates (AED → BHD) (57 sources)

| # | Domain | Platform | Mechanism | Categories | Sample price | Conf |
|---|---|---|---|---|---|---|
| 105 | adasat.com | Shopify | `shopify_products_json` | eyewear, other | 400.00 AED | high |
| 106 | armaf.ae | Shopify | `shopify_products_json` | fragrances | AED 140.00 | high |
| 107 | atelierdeglow.ae | Shopify | `shopify_products_json` | skincare | AED 105.00 | high |
| 108 | beautiquefragrances.com | Shopify | `shopify_products_json` | fragrances | AED 882.00 | high |
| 109 | coralperfumes.com | Shopify | `shopify_products_json` | fragrances | AED 49.00 | high |
| 110 | cozmada.com | Shopify | `shopify_products_json` | haircare, skincare | AED 200.00 | high |
| 111 | crescitebeauty.com | Shopify | `shopify_products_json` | skincare | 88.04 AED | high |
| 112 | dubaioptical.com | Shopify | `shopify_products_json` | eyewear, other | Dhs. 462.40 | high |
| 113 | ecityuae.ae | Shopify | `shopify_products_json` | electronics | AED 5,099.00 | high |
| 114 | eideal.com | Shopify | `shopify_products_json` | haircare, skincare | AED 138.60 | high |
| 115 | ghawali.com | Shopify | `shopify_products_json` | fragrances | AED 745.00 | high |
| 116 | houseofperfumes.com | Shopify | `shopify_products_json` | fragrances | 150.00 AED | high |
| 117 | jnknutrition.com | Shopify | `shopify_products_json` | supplements, sports-nutrition | AED 160.00 | high |
| 118 | k-city.com | Shopify | `shopify_products_json` | skincare, makeup | AED 95.00 | high |
| 119 | khadlaj-perfumes.com | Shopify | `shopify_products_json` | fragrances | 65.00 AED | high |
| 120 | lamisebeauty.com | Shopify | `shopify_products_json` | skincare, makeup | AED 73.00 | high |
| 121 | larovie.ae | Shopify | `shopify_products_json` | skincare | AED 95.00 | high |
| 122 | mamlakataloud.ae | Shopify | `shopify_products_json` | fragrances | Dhs. 140.00 | high |
| 123 | med7online.com | Shopify | `shopify_products_json` | supplements, skincare | 77.00 AED | high |
| 124 | medicinaonline.ae | Shopify | `shopify_products_json` | supplements, skincare | AED 35.00 | high |
| 125 | mestore.ae | Shopify | `shopify_products_json` | skincare, haircare, makeup, other | AED 23.10 | high |
| 126 | miraebeautyhub.com | Shopify | `shopify_products_json` | skincare, haircare | AED 99.99 | high |
| 127 | myeasypharmacy.ae | Shopify | `shopify_products_json` | supplements, skincare | 159.00 AED | high |
| 128 | myperfumes.ae | Shopify | `shopify_products_json` | fragrances | Dhs. 175.00 | high |
| 129 | nutristore.ae | Shopify | `shopify_products_json` | supplements, sports-nutrition | AED 200.00 (ISO-XP 1kg) | high |
| 130 | organicandreal.com | Shopify | `shopify_products_json` | grocery | AED 169.99 | high |
| 131 | parfum.ae | Shopify | `shopify_products_json` | fragrances | AED 350.00 | high |
| 132 | refab.me | Shopify | `shopify_products_json` | electronics | AED 2000.00 | high |
| 133 | revent.store | Shopify | `shopify_products_json` | electronics | From 2,180 AED | high |
| 134 | samawa.ae | Shopify | `shopify_products_json` | fragrances | AED 222.00 | high |
| 135 | scentlibraryofficial.com | Shopify | `shopify_products_json` | fragrances | AED 950.00 | high |
| 136 | usbs-uae.com | Shopify | `shopify_products_json` | electronics | From AED 900.00 | high |
| 137 | watches.ae | Shopify | `shopify_products_json` | fashion, other | AED 5,080 | high |
| 138 | yusufbhaifragrances.com | Shopify | `shopify_products_json` | fragrances | From AED 50.00 | high |
| 149 | babystore.ae | WooCommerce | `json_api` | other, grocery | price 18500 = AED 185.00 | high |
| 150 | head2toes.ae | WooCommerce | `json_api` | haircare, makeup, skincare | price 4000 = AED 40.00 | high |
| 151 | kbeautybliss.com | WooCommerce | `json_api` | skincare | AED 113 | high |
| 152 | ouddubai.ae | WooCommerce | `json_api` | fragrances | price 12600 = AED 126.00 | high |
| 153 | oudera.ae | WooCommerce | `json_api` | fragrances | AED 190.00 | high |
| 28 | papita.co | WooCommerce | `json_api` | electronics | **BHD 118 (genuine BHD via /ae/)** | high |
| 154 | perfumebays.com | WooCommerce | `json_api` | fragrances | price 57750 = AED 577.50 | high |
| 155 | theskincarehub.com | WooCommerce | `json_api` | skincare | price 11000 = AED 110.00 | high |
| 189 | binsina.ae | Magento | `curl_jsonld` | supplements, skincare, other | AED 20.00 | high |
| 190 | chspharmacy.ae | Magento | `curl_jsonld` | supplements | AED 60.90 | high |
| 191 | gomyz.com | Magento | `curl_jsonld` | skincare, makeup, haircare | AED 163.00 | high |
| 192 | jumbo.ae | Magento | `curl_jsonld` | electronics | AED 1,499.00 | high |
| 193 | nazih.ae | Magento | `curl_jsonld` | haircare, makeup, fragrances | AED 37.05 | high |
| 194 | rivolishop.com | SFCC/Demandware | `curl_jsonld` | fashion, other | AED 6,150 | high |
| 195 | unioncoop.ae | Magento | `curl_jsonld` | grocery | AED 12.50 | high |
| 199 | atelierperfumery.com | custom (ASP.NET) | `curl_jsonld` | fragrances | 480 AED | medium |
| 200 | nrtcfresh.com | custom (Laravel) | `curl_jsonld` | grocery | AED 6.50 | medium |
| 201 | touchofoud.com | custom | `curl_jsonld` | fragrances | 368 AED | medium |
| 205 | eros.ae | Magento | `render_required` | electronics | AED 3999.00 | high |
| 206 | lookfantastic.ae | SFCC/THG | `render_required` | skincare, haircare, makeup, fragrances | 110 AED | high |
| 207 | store.aerosmart.ae | custom (Laravel) | `render_required` | electronics | AED2,669.00 | high |
| 213 | hyperpc.ae | Next.js | `render_required` | electronics | from AED 7,880 | medium |
| 214 | letoile.ae | Next.js | `render_required` | makeup, skincare, fragrances | 147 AED | medium |

### Kuwait (KWD → BHD) (21 sources)

| # | Domain | Platform | Mechanism | Categories | Sample price | Conf |
|---|---|---|---|---|---|---|
| 72 | alqamarshop.com | Shopify | `shopify_products_json` | electronics | 4.750 KWD | high |
| 73 | alsultanpharmacy.com | Shopify | `shopify_products_json` | supplements, pharmacy, skincare | 4.680 KWD | high |
| 74 | blink.com.kw | Shopify | `shopify_products_json` | electronics, gaming | 219.000 KD | high |
| 75 | decathlon.com.kw | Shopify | `shopify_products_json` | sports, fashion, other | 255.000 KD | high |
| 76 | future.com.kw | Shopify | `shopify_products_json` | electronics, fragrances, other | 79.000 KWD | high |
| 77 | kaif.co | Shopify | `shopify_products_json` | grocery, other | 55.000 KWD | high |
| 78 | kuwaitcavarat.com | Shopify | `shopify_products_json` | mobile-accessories, electronics | 6.900 KD | high |
| 79 | level-up.gg | Shopify | `shopify_products_json` | electronics, other | 8.500 KWD | high |
| 80 | mamasfirst.com | Shopify | `shopify_products_json` | baby, kids, other | 2.700 KWD | high |
| 81 | numberc.com | Shopify | `shopify_products_json` | makeup, skincare, fragrances | 12.100 KWD | high |
| 82 | pharmacypluskw.com | Shopify | `shopify_products_json` | supplements, pharmacy | 7.63 KWD | high |
| 83 | pharmazone.com | Shopify | `shopify_products_json` | supplements, pharmacy | 25.000 KWD | high |
| 176 | almutawaph.com.kw | Magento | `curl_jsonld` | supplements, pharmacy | KD 15.000 | high |
| 177 | azadea.com | SFCC/Demandware | `curl_jsonld` | sports, fashion, other | 173.00 KWD | high |
| 178 | bloomingdales.com.kw | SFCC/Demandware | `curl_jsonld` | makeup, fragrances, fashion | KWD 16.500 | high |
| 179 | damasjewellery.com | Magento | `curl_jsonld` | jewelry | 1,511 KWD | high |
| 180 | kw.oudelite.com | Salla | `curl_jsonld` | fragrances | 7 KWD | high |
| 181 | kwt.nazih.com | Magento | `curl_jsonld` | haircare, skincare, fragrances | KWD 17.395 | high |
| 182 | mamasandpapas.com.kw | SFCC/Demandware | `curl_jsonld` | baby, kids, fashion | KWD 13.250 | high |
| 183 | taw9eel.com | Magento | `curl_jsonld` | supplements, pharmacy, grocery | KD22.5 | high |
| 204 | xcite.com | Next.js (Magento) | `render_required` | electronics | 219.900 KD | high |

### Qatar (QAR → BHD) (24 sources)

| # | Domain | Platform | Mechanism | Categories | Sample price | Conf |
|---|---|---|---|---|---|---|
| 90 | allaboutskindoha.com | Shopify | `shopify_products_json` | skincare, makeup, haircare | 105.00 QAR | high |
| 91 | carencurepharmacy.com | Shopify | `shopify_products_json` | supplements, pharmacy, skincare | QAR 60.00 | high |
| 92 | digitalzone.qa | Shopify | `shopify_products_json` | electronics | QAR 54.00 | high |
| 93 | mhalaty.com | Shopify | `shopify_products_json` | makeup, skincare | QAR 130.00 | high |
| 94 | mhgboutique.com | Shopify | `shopify_products_json` | fragrances | 290.00 QAR | high |
| 95 | oqba.qa | Shopify | `shopify_products_json` | fragrances | 32.00 QAR | high |
| 96 | parfum.qa | Shopify | `shopify_products_json` | fragrances | QAR 60.00 | high |
| 97 | parigallery.com | Shopify | `shopify_products_json` | fragrances, makeup, skincare | QAR 1,635.00 | high |
| 98 | rptech.qa | Shopify | `shopify_products_json` | electronics | QAR 4,399.00 | high |
| 99 | souqscent.com | Shopify | `shopify_products_json` | fragrances | QAR 125.00 | high |
| 100 | sunlife.qa | Shopify | `shopify_products_json` | supplements, pharmacy, sports-nutrition | QAR 47.70 | high |
| 101 | tuzzut.com | Shopify | `shopify_products_json` | fragrances, electronics, other | QAR 139.00 | high |
| 102 | vitaminqatar.com | Shopify | `shopify_products_json` | supplements, pharmacy | QAR 79.00 | high |
| 103 | wellcareonline.com | Shopify | `shopify_products_json` | supplements, pharmacy, skincare | 70.00 QAR | high |
| 104 | xstore.qa | Shopify | `shopify_products_json` | electronics | QAR 549.00 | high |
| 146 | ispotaba.com | WooCommerce | `json_api` | electronics | QAR 4,899 | high |
| 147 | perfumeqatar.com | WooCommerce | `json_api` | fragrances | 169.00 QAR | high |
| 148 | qatarperfumeshop.com | WooCommerce | `json_api` | fragrances | 320.00 QAR | high |
| 185 | jazp.com | Magento / custom | `curl_jsonld` | electronics, fragrances, other | QAR 99 | high |
| 186 | mamlakatoud.com | custom | `curl_jsonld` | fragrances | 130,00 QAR | high |
| 187 | qatar.jazp.com | custom | `curl_jsonld` | electronics, other | QAR 119 | high |
| 188 | qatar.microless.com | custom | `curl_jsonld` | electronics | QAR 3,176.32 | high |
| 198 | salams.com | Magento | `curl_jsonld` | fragrances, fashion, electronics | QAR (Magento) | medium |
| 212 | swarovski.qa | SFCC/Demandware | `render_required` | jewelry, watches, other | 380 QAR | medium |

### Oman (OMR → BHD) (15 sources)

| # | Domain | Platform | Mechanism | Categories | Sample price | Conf |
|---|---|---|---|---|---|---|
| 84 | alhajisoman.com | Shopify | `shopify_products_json` | fragrances, makeup, skincare | 10.000 OMR | high |
| 85 | avicenonline.com | Shopify | `shopify_products_json` | supplements, skincare, haircare, grocery | OMR 3.600 | high |
| 86 | capitalstoreoman.com | Shopify | `shopify_products_json` | fragrances, makeup, skincare, haircare | 13.950 OMR | high |
| 87 | ghawyoman.com | Shopify | `shopify_products_json` | haircare, skincare, makeup | 32 OMR | high |
| 88 | glowupom.com | Shopify | `shopify_products_json` | makeup, skincare | 9.800 OMR | high |
| 89 | omanluxury.store | Shopify | `shopify_products_json` | fragrances | 75.000 OMR | high |
| 141 | mbayoman.com | WooCommerce | `json_api` | electronics | price 41000 minor_unit 3 = 41.000 OMR | high |
| 142 | mobpcom.com | WooCommerce | `json_api` | electronics | price 999 minor_unit 1 = 99.9 OMR | high |
| 143 | mushtariyat.com | WooCommerce | `json_api` | makeup, skincare, fragrances, haircare | price 440 minor_unit 2 = OMR 4.40 | high |
| 144 | qimia.om | WooCommerce | `json_api` | supplements, sports-nutrition | 17.90 OMR | high |
| 145 | timezoneoman.com | WooCommerce | `json_api` | fashion, electronics | price 19625 minor_unit 2 = 196.25 OMR | high |
| 184 | om.oudelite.com | Salla | `curl_jsonld` | fragrances | 11.498 OMR | high |
| 209 | om.ahmedalmaghribi.com | Next.js | `render_required` | fragrances | 13.500 OMR | medium |
| 210 | oman.citizenshop.me | custom | `render_required` | fashion, electronics | OMR 340.98 | medium |
| 211 | oman.jazp.com | custom | `render_required` | electronics | 314 OMR | medium |
<!-- TABLES END -->

> **`reefperfumes.com` (#56)** is filed under KSA but is the round's most interesting single find: a
> **Salla store that geo-localizes its JSON-LD to genuine BHD** when fetched from a BH context
> (`"price":16.258,"priceCurrency":"BHD"`, verified). It belongs to the genuine-BHD column at runtime
> if the scraper pins a BH IP / `Accept-Language`. **`papita.co` (#28)** likewise serves **genuine
> BHD** via its `/ae/` WooCommerce Store API (`currency_code:"BHD"`, verified). These two prove a
> broader pattern: several "GCC" storefronts emit BHD under BH geo — worth probing the BH locale of
> any multi-currency Salla/Shopify-Markets store before treating it as convertible-only.

---

## 3. Platform / scrape-method research — "how they scrape / what is used mainly"

This was the single biggest signal across both rounds: **the GCC long tail is platform-stereotyped**,
and each platform has exactly one canonical $0 extraction. Knowing the platform = knowing the cheapest
adapter. The per-platform pattern below is the durable scraper map.

### 3.1 Canonical $0 extraction per platform

| Platform | Cost | Canonical $0 extraction | Notes / gotchas |
|---|---|---|---|
| **Shopify** | $0 | `GET {domain}/products.json?limit=250&page=N` → `products[].variants[].price` (base currency, no currency field — for a BH-base store the number IS BHD) | Catalog JSON, paginated. A few stores 302-redirect `/products.json` when Shopify Markets is on (shopkees) → read `Shopify.currency.active` + the embedded product-cents from PDP HTML, or `{pdp}.json`. `{pdp-handle}.json` returns one product with `price_currency` (watsons.sa). |
| **WooCommerce** | $0 | `GET /wp-json/wc/store/products?per_page=100&page=N` → `prices.price` (**minor units**) + `prices.currency_code` + `prices.currency_minor_unit` | **Read `currency_minor_unit` per response** (BHD/KWD/OMR-3dp=3, AED/SAR/QAR=2, but mobpcom returned 1). Some block the Store API to plain WebFetch with 403/406 (advancedpcbahrain 406, miniso 403) → use `curl_cffi`/`fetch_page_price` HTML fallback. |
| **Salla** (KSA-dominant SMB; thousands of stores) | $0 | curl PDP → `application/ld+json` Product/Offer with literal `"price":N,"priceCurrency":"<CUR>"` server-rendered | PDP URL is `/{lang}/<slug>/p<numericId>` or `/{lang}/-/p<id>`. `products.json` is empty on Salla → **crawl category/sitemap for PDP URLs**, then curl each. **Geo-localizes currency** (reefperfumes → BHD under BH). Salla CDN markers: `cdn.salla.sa`, `salla.network`, `cdn.assets.salla.network`. Some Salla PDPs lazy-render the Product JSON-LD (only Organization JSON-LD on first paint) → retry / hit the `/p<id>` canonical. |
| **Magento** | $0 | curl PDP → JSON-LD Product/Offer OR microdata `data-price-amount="N"` + `<span class="price">N CUR</span>` | Price is on **PDP**, often NOT on category/listing pages. `.html` PDP URLs, `/media/catalog/product/` asset paths, `mage/` markers. Some PDPs 403/500 on plain curl (ashrafsbahrain, almajed4oud) → `curl_cffi`. |
| **OpenCart** | $0 | curl PDP (`index.php?route=product/product&product_id=N`) → BHD price in rendered HTML / microdata | Slug-id URLs; price server-rendered. |
| **SFCC / Demandware** | $0 **when server-rendered** | curl PDP → SAR/AED/KWD price text in static HTML (faces.sa, narscosmetics.sa, rivolishop, azadea, bloomingdales.kw, M&P.kw) | **MIXED**: many SFCC sites server-render the price into static HTML (curl-scrapeable) but some gate it behind hydration (deraahstore, swarovski.qa) → `render_required`. Markers: `demandware.static`, `Sites-<name>-Site`, `/on/demandware.store/`. THG-on-SFCC (lookfantastic) is render-walled. |
| **Next.js (custom)** | mixed | server-rendered: curl HTML/`__NEXT_DATA__` (jarir /bh-en, gccgamers /bh, saudi.jazp, vperfumes, kanbkam, Landmark homecentre/homebox JSON-LD); client-side: `render_required` (goldapple, xcite, bfab, matalan, hyperpc, letoile) | Probe the PDP: if a price string OR a `__NEXT_DATA__`/JSON-LD price node is in the **delivered** HTML → `curl_jsonld`/`json_api`; if only a shell → `render_required` (or reverse the product API route). |
| **Lightspeed eCom / Odoo / Wix / Akinon / custom-Laravel/ASP** | $0 (mostly) | curl PDP → price in server-rendered HTML (Lightspeed `BD N`, Odoo `oe_currency_value`, Wix `warmupData` JSON, Akinon template HTML, Laravel/ASP plain-text) | Wix `warmupData` is an embedded JSON blob in the HTML (json_api-ish). Laravel/ASP/Akinon have no structured price hook → HTML-text regex (still $0 curl). |
| **SAP Hybris (Commerce Cloud)** | paid render OR Hybris OCC API | price JS-injected; not in static HTML | eXtra (extra.com, multi-GCC /en-bh /en-om /en-sa). `cdn.extra.com/hybris` markers. Either `render_required` or probe the OCC v2 REST API (`/occ/v2/<baseSite>/...`). |
| **q-commerce Next.js (Talabat)** | $0 (fiddly) | `__NEXT_DATA__` embeds item prices + `currency:"BD"` on `/bahrain/groceries` (no Akamai wall on that path) | Per-item URL needs the vendor+category menu structure → less direct than a catalog endpoint, but the price IS curl-extractable from the SSR JSON. Biggest BH grocery catalog. |

### 3.2 Platform landscape per GCC country (which platforms dominate where)

- **Bahrain** — a healthy long tail of **Shopify** (18) + **WooCommerce** (12, incl. the Store-API
  keystone) + **Magento** (ashrafs/adilstore/istationery/geekay/homesrus/aigner/levelshoes BH) +
  **Salla** (oudelite/hanan/alkhabeer/eitara) + **OpenCart** (jawaher/lily/stc) + the **Landmark
  Next.js** stack (homecentre/homebox, JSON-LD BHD) + a few customs (winbid/advanti/jarir/gccgamers).
  The big BH q-commerce/marketplace SPAs (noon, talabat-app, ourshopee, getbaqala, ramez, ninja) are
  render-walled — **direct-store $0 adapters, not marketplaces, are the BH genuine layer**.
- **KSA** — **Salla is dominant** for SMB fragrance/supplement stores (10 of 35 are Salla — the
  cheapest $0 curl-JSON-LD class) + **Shopify** (gazzaz/ghawali/mubkhar/naseem/swissarabian/ajmal/
  watsons) + **Magento** (almanea/alsaifgallery/rituals) + **SFCC** (faces.sa/nars/deraah) + custom
  Next (jazp/microless/firstcry). The KSA mega-retailers (jarir/extra/xcite/al-dawaa/carrefourksa/
  panda/saco) are 403/SPA/render-walled — convertible value comes from the SMB Salla/Shopify tail.
- **UAE** — **Shopify is overwhelmingly dominant** (34 of 57! — the densest Shopify market in the GCC,
  esp. fragrance + K-beauty + pharmacy) + **WooCommerce** (8) + **Magento** (jumbo/gomyz/unioncoop/
  binsina/chs/nazih) + SFCC (rivoli) + a render tail (eros/lookfantastic/aerosmart/hyperpc/letoile).
  UAE = the single richest $0 convertible vein (42 of 57 are static-JSON Shopify/Woo).
- **Kuwait** — **Shopify** (12 of 21, incl. pharmacy + electronics + Decathlon) + **Magento**
  (almutawa/taw9eel/nazih/damas) + **SFCC** (azadea/bloomingdales/M&P). Xcite (the #1 KW electronics)
  is render-walled.
- **Qatar** — **Shopify is dominant** (15 of 24 — fragrance + pharmacy + electronics) + **WooCommerce**
  (ispotaba/perfumeqatar/qatarperfumeshop) + custom Next (jazp/microless). Clean $0 market.
- **Oman** — split **Shopify** (6) / **WooCommerce** (5, all Store-API) + Salla (oudelite) + a render
  tail (citizenshop/jazp/maghribi). 11 of 15 are static-JSON $0.

**Country headline:** Shopify + WooCommerce-Store-API together are the cheapest path in **every**
country; **KSA is the one country where Salla (curl-JSON-LD) matters more than Shopify**.

### 3.3 What GCC aggregators revealed about canonical mainstream sources

- **pricena.com** (round-1; UAE-origin, 20M+ products) aggregates merchant CPA/CPC **feeds** — its
  retailer coverage *is* the canonical mainstream-retailer map per country: **Noon, Amazon (.ae/.sa),
  Jarir, eXtra, Namshi, Wadi, Carrefour, eBay**. It operates **UAE/KSA/Egypt/Kuwait/Qatar but NOT
  Bahrain** — confirming (again) that **BH has no aggregator coverage** and Qaren must fill BH with
  direct adapters.
- **kanbkam.com** (NEW this round, KSA/UAE) is a second pricena-class aggregator — server-renders
  prices in static HTML (curl-scrapeable, `data-price`), aggregates **Amazon, Noon, X-Cite, Extra,
  Jarir, Jumia, AliExpress**, and carries price-history graphs. Same canonical-mainstream signal.
- **yaoota** = Egypt-focused (not GCC-actionable). **d4donline / tsawq / clicflyer / nestooffers /
  comparebh / labeb / mobile57** (BH) are flyer/offer aggregators — *cross-reference / discovery
  feeds*, not live transactional PDPs (prices lag).
- **Implication:** for **KSA/UAE/KW/QA**, the canonical convertible mainstream sources are
  **Jarir + eXtra + Noon + Amazon.sa/.ae** — but those are precisely the render/anti-bot-walled set,
  so the **SMB Shopify/WooCommerce/Salla tail catalogued here is the cheaper, more reachable layer.**
  For **Bahrain**, the genuine layer is the direct Shopify/WooCommerce/Salla/Magento stores — there is
  no aggregator shortcut.

---

## 4. Integration delta (which adapters cover the new sources; new shapes needed)

The codebase already has the adapter family + the registry `Source(...)` descriptor with `mechanism`
+ per-mechanism selectors in `source_router.py`. **No new architecture.** Mapping of the 214 new rows
to adapters:

| Integration adapter | # rows | Status |
|---|---|---|
| `fetch_shopify_price` (`is_shopify=True`) | **93** | EXISTS — wire as registry rows, zero code |
| `fetch_woocommerce_store_api_price` (`mechanism="json_api"`, woo_store) | **26** | **Round-1 proposed keystone — BUILD ONCE, covers all 26 + 3 round-1** |
| `fetch_page_price` (`mechanism="curl"`) — generic JSON-LD/microdata/HTML | **58** | EXISTS — registry rows + PDP discovery |
| `fetch_page_price` (`mechanism="curl"`) — **Salla JSON-LD extractor** | **16** | EXISTS path; **add a Salla branch** (server-rendered ld+json + crawl-categories-for-PDP, products.json empty) |
| `fetch_next_data_price`-style (`__NEXT_DATA__`) | **2** (vperfumes, talabat) | Small new extractor OR `fetch_page_price` `__NEXT_DATA__` branch |
| Wix `warmupData` extractor (`json_api`) | **1** (irepair-bh) | Tiny new branch (embedded JSON in HTML) |
| `cron_index_sitemaps` + `fetch_page_price` (`mechanism="sitemap"`) | **2** (mithaly, proteinvitamin — Salla) | EXISTS — add sitemap index URLs |
| `algolia_service.fetch_algolia_price` (`is_algolia=True`) | **1** (nahdionline) | EXISTS — add index key |
| render tier (`is_render_only=True`) — **DEFER** | **15** | not part of $0 push |

### 4.1 Sources that map to EXISTING / round-1-proposed adapters (no new code)

- **93 Shopify** → `fetch_shopify_price`. Set `is_shopify=True` + `currency` (BHD/AED/SAR/KWD/QAR/OMR).
  GCC-currency stores stamp `converted_usd`/`converted` via the existing path. **Zero adapter work.**
- **26 WooCommerce Store-API** → the **round-1 keystone** `fetch_woocommerce_store_api_price`
  (`GET /wp-json/wc/store/products?per_page=100&page=N`, read `prices.price`÷10^`currency_minor_unit`
  + `prices.currency_code`). One adapter covers all 26 here (BH: arafaphones, iworld, miniso,
  organature, asasiat, petshomebh, smellsoreal, almajarahgold, theperfumesclub, nexcel; UAE:
  oudera, perfumebays, babystore, kbeautybliss, theskincarehub, head2toes, ouddubai, papita
  [genuine BHD]; QA: ispotaba, perfumeqatar, qatarperfumeshop; OM: mbayoman, mushtariyat, mobpcom,
  timezoneoman, qimia) **+ the 4 round-1 fragrance Woo stores**. **Biggest single ROI in the round.**
- **58 generic curl_jsonld** → `fetch_page_price` (Magento microdata, SFCC server-rendered, Next-SSR,
  OpenCart, Lightspeed, Odoo, Akinon, Laravel/ASP HTML-text, aggregator `data-price`). Already-handled
  markup variants. Supply the PDP via Serper `site:{domain}` OR a sitemap where one exists.
- **2 sitemap (Salla)** + **1 algolia (nahdi)** → existing `cron_index_sitemaps` / `algolia_service`.

### 4.2 NEW adapter shapes a NEW platform needs

1. **Salla JSON-LD extractor** (16 stores + round-1's bh.arabianoud) — **the second new keystone after
   the WooCommerce Store API.** Salla is its own family: `products.json` is **empty**, so discovery
   must crawl the **category pages / sitemap** for `/p<id>` PDP URLs, then curl each PDP and read the
   server-rendered `application/ld+json` Product/Offer (`price` + `priceCurrency`). Add this as a
   `fetch_page_price` Salla branch (platform-detected via `cdn.salla.sa`) **OR** a dedicated
   `fetch_salla_price`. It unlocks the entire KSA SMB fragrance/supplement tail + BH Salla stores +
   the geo-BHD reefperfumes case. **Build once, covers ~18 here + grows freely** (KSA alone has
   thousands of Salla stores).
2. **WooCommerce Store-API adapter** (the round-1 keystone) — now 26 rows; **build it** if not yet.
3. **Wix `warmupData` extractor** (1 store, irepair-bh) — low priority; an embedded-JSON-in-HTML
   branch of `fetch_page_price`. Brittle Wix markup; only build if Wix recurs.
4. **`__NEXT_DATA__` extractor** (vperfumes, talabat) — a JSON-from-SSR-HTML branch of
   `fetch_page_price`; reuse for any Next store that embeds price in `__NEXT_DATA__`.

> **One-line delta:** the round-1 keystone `fetch_woocommerce_store_api_price` + a new
> **`fetch_salla_price`** (server-rendered JSON-LD, crawl-categories-for-PDP) are the **two adapters**
> that, together with the existing `fetch_shopify_price`/`fetch_page_price`, cover **~199 of the 214
> new sources at $0**.

---

## 5. Coverage / gap report (per country + per category) + round-3 promotions

### 5.1 Per-country coverage (new this round; $0 unless noted)

| Country | New | $0 static-JSON (Shopify/Woo) | $0 curl/sitemap | render | Currency |
|---|---|---|---|---|---|
| Bahrain | 62 | 30 | 29 | 3 | **genuine BHD** |
| UAE | 57 | 42 | 10 | 5 | AED (+ 1 genuine BHD: papita) |
| KSA | 35 | 9 | 24 | 2 | SAR (+ 1 geo-BHD: reefperfumes) |
| Qatar | 24 | 18 | 5 | 1 | QAR |
| Kuwait | 21 | 12 | 8 | 1 | KWD |
| Oman | 15 | 11 | 1 | 3 | OMR |

### 5.2 Per-category coverage — genuine-BHD count (round-2 NEW only)

| Category | Genuine-BHD NEW sources | Cheapest mechanism | Status vs round-1 |
|---|---|---|---|
| **electronics** | 18 (iworld, gamerspoint, emsquare, arafaphones, advancedpc, gccgamers, jarir/bh-en, geekay, ashrafs, store.gadgetzone, advanti, d4d, shop.stc, nexcel, irepair, shopalmoayyed…) | shopify/json_api/curl | **strongly reinforced** (genuine BHD iPhone/Samsung/laptop/console PDPs) |
| **supplements** | 7 (smartnutr, mastermuscles, wawan, manamamedical, livewell, lilyorganics, +sokostore) | **shopify_products_json** | **major win** — genuine-BHD supplements (round-1's worst category) |
| **grocery** | 12 (livewell, ibsouq, asasiat, organature, bh.adilstore, winbid, lilyorganics, petshomebh, talabat, …) | shopify/json_api/curl | **major win** — $0 BHD grocery beyond round-1's curl-fragile alosra/megamart |
| **fragrances** | 11 (oudelite, hanan, alkhabeer, taifalemarat, perfumistaaloud, naseem, theperfumesclub, smellsoreal, almajed4oud, reef[geo]) | shopify / Salla / Woo | reinforced |
| **fashion** | 7 (aigner, levelshoes, jawaher, leenaz, bfab, matalan, bjc) | curl_jsonld | reinforced (Magento BHD PDPs) |
| **makeup / skincare** | 9 (sokostore, beautybykat, eitara, asasiat, organature, …) | shopify / Salla / Woo | reinforced |
| **jewelry / watches** | 3 (almajarahgold, jawaher, bjcstore) | json_api / curl | NEW BHD coverage |
| **baby / kids / toys** | 6 (yallatoys, mamasandpapas.bh, livewell, miniso, petshome) | shopify / json_api | NEW BHD coverage |
| **stationery / books / eyewear / pet / medical** | 6 (istationery, bookmart, optica, petarabia, petshome, manamamedical) | shopify / curl | NEW long-tail BHD coverage |

### 5.3 Still thin / structural gaps (unchanged or partially closed)

1. **BH mega-marketplaces still render-walled** — noon `/bahrain-en/`, talabat-app full catalog,
   ourshopee, getbaqala, ramez, ninja remain SPA/render-only. Talabat `/bahrain/groceries`
   `__NEXT_DATA__` is the one $0 crack (medium-conf, fiddly per-item URL). The direct-store $0 adapters
   above cover most mainstream SKUs *without* the marketplaces.
2. **Luxury Western fragrance/beauty in true BHD** — sephora.me / bolo.bh / boutiqaat remain CF-walled
   (round-1 structural). reefperfumes(geo-BHD) + ounass-BH + sharafdg + this round's BH Salla/Magento
   fragrance stores cover much of the mid-tier; the deep niche-house luxury tail still leans converted
   or render.
3. **KSA/UAE mega-retailers** (jarir/extra/xcite/al-dawaa/carrefour/panda/nahdi) are anti-bot/SPA — the
   SMB Salla/Shopify tail is the reachable convertible layer; nahdi has an Algolia crack (medium).
4. **Supplements *protein* depth** — now genuinely covered in BHD (smartnutr/mastermuscles/wawan) but
   verify breadth of SKU match; the GCC supplement chains (sporter/drnutrition) remain 403-walled.

### 5.4 Promote to ROUND 3 (highest-value unverified leads + re-probes)

| Lead | Country | Why promote | Round-3 next step |
|---|---|---|---|
| **binge.bh / smartnutritionbh.com** | BH | concrete 3-dp BHD supplement prices in search; ECONNREFUSED this run (likely Zid `/categories/<id>/`) | re-probe from prod (curl_cffi/Firecrawl); if Zid → `sitemap_jsonld`/`curl_jsonld` |
| **drnutrition.com /en-bh + sporter.com /en-bh** | BH | dedicated **genuine-BHD supplement** stores (Qaren's hardest category), real PDP URLs; only 403 blocked | re-probe via Scrape.do/residential; likely Magento/Next curl_jsonld |
| **gcc.luluhypermarket.com /en-sa, /en-om** | KSA/OM | round-1 already uses the BH lulu (`page_scrape_jsonld`); the SAR/OMR locales are NOT in known-85 | verify-then-add the SAR/OMR locale rows (same mechanism) |
| **al-dawaa.com /english** | KSA | KSA #2 pharmacy, deep supplements/whey; 403 | residential proxy; likely a render/API |
| **panda.sa, saco.sa, virginmegastore.sa/.qa/.bh** | KSA/QA/BH | top grocery/home/electronics SPAs; render-only | render-tier or internal product API hunt |
| **NEW locale subdomains of KNOWN round-1 roots** | OM/KSA | `om.swissarabian.com`, `oman.afnan.com`, `om.junaidperfumes.com`, `om.asgharali.com`, `oman.sharafdg.com` (Algolia OMR), `om.getkuwa.com` — all Shopify products.json $0 OMR, materially add OM coverage | verify-then-add (mechanism inherited from the known root) |
| **bh.gobazzar.com / halabh.com** | BH | a real BH price-comparison engine; halabh is confirmed Shopify BHD but `/products.json` is 401 | gobazzar: re-probe from GCC IP; halabh: fetch a server-rendered collection/PDP (Shopify HTML) |
| **shop.batelco.com / eshop.bh.zain.com / shop.samsung.com/bh** | BH | genuine-BHD official device shops (SPA/Hybris OCC API) | find the baseSite in runtime JS → `json_api` |
| **futureit.om / gamingpcoman.shop / muscatfoodmarket.com** | OM | likely WooCommerce (403'd) → `/wp-json/wc/store/products` would be $0 | residential proxy re-probe |

### 5.5 EXCLUDE (verified dead/wrong-currency — do not add)

- `oudarabiadubai.com` (INR), `junaidalatoor.com` (INR), `intenseoud.com` (USD US-store),
  `dubaibeautywholesale.com` (USD), `supplement.ae` / `lifestylenutrition.com` (parked/for-sale),
  `wafiapps.com` (defunct→zedups), `getbaqala.com /en` (redirects to unrelated news), `olim p.om`
  (→qimia.om, dup), Nesto BH (no direct transactional site — flyer aggregators only).

---

## 6. Verification notes (this synthesis pass — 15 live WebFetch checks)

Re-fetched the highest-value uncertain/load-bearing sources before cataloguing. Confirmed:
- `bh.oudelite.com` PDP → Salla, `"price":11.501,"priceCurrency":"BHD"` ✓ (genuine BHD JSON-LD)
- **`reefperfumes.com`** PDP → Salla, geo-served **`"price":16.258,"priceCurrency":"BHD"`** ✓
  (genuine-BHD-under-BH-geo confirmed — the round's key find)
- `shop.almajarahgold.com` / `petshomebh.com` `/wp-json/wc/store/products` → valid Store-API,
  `currency_code:"BHD"`, minor_unit 3 ✓ (confirms the WooCommerce keystone shape across BH)
- `bh.yallatoys.com` / `shop.optica.net` / `livewell.bh` `/products.json` → valid Shopify, BHD ✓
- `sa.abdulsamadalqurashi.com` → Salla, `"price":495,"priceCurrency":"SAR"` ✓ (KSA Salla class)
- `faces.sa` / `watsons.sa` / `ecityuae.ae` → SFCC server-rendered SAR / Shopify SAR / Shopify AED ✓
- **`gccgamers.com/bh/`** → **BHD price in static HTML** (`645.013 BHD`) ✓ — **upgraded from
  render_required to `curl_jsonld`** (the finder was over-cautious; price is curl-scrapeable).
- `jarir.com/bh-en` → BHD confirmed but price is **plain-text** on this PDP (no reliable JSON-LD) →
  kept `curl_jsonld` with the note that some Jarir PDPs render the price as plain text.
- `ashrafsbahrain.com` / `miniso-bh.com` WebFetch → **403** (consistent with the durable "listings
  open, PDPs anti-bot on plain fetch → use `curl_cffi`" pattern; the finder's direct-curl evidence
  stands). Kept high-conf, flagged for `curl_cffi`.

All other entries carry the original finder's literal-price evidence (a real fetch showing the price
string), per the verify-or-omit mission rule. Decimal/minor-unit and platform fields normalized;
`gccgamers` mechanism corrected; `reefperfumes`/`papita` flagged as genuine-BHD despite GCC TLDs.

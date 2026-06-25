# BH/GCC Price-Source Discovery — ROUND 4 (Focused FINAL Round)

**Date:** 2026-06-25
**Synthesis lead:** dispatcher (round-4 final-round synthesis)
**Inputs:** R1 (`bh_gcc_source_candidates.json`, 85) + R2 (`_round2.json`, 214) + R3 (`_round3.json`, 83) = **382 known unique domains** (verified: 85+214+83=382, no cross-round dups).
**Output:** `data/bh_gcc_source_candidates_round4.json` (18 NEW, deduped, hard-filtered against the 382).
**Method note:** R4 was deliberately FOCUSED/technical — it targeted the high-value remainder R1–R3 flagged (giant cracks needing a client-side-key extraction, Akamai alternate-doors, Salla bulk-harvest, Kuwait depth) rather than generic SMB long-tail hunting (saturated). Multiple source sub-agents fed candidates; this synthesis hard-filtered + re-verified live.

---

## 0. Dedup result — the load-bearing filter

The round-4 candidate stream carried **34 domain rows**. Programmatic exact-match against the 382:

- **18 NEW** (net-new domains, written to the R4 JSON).
- **16 were already in the 382** — but several of those are **mechanism CRACKS** of previously render-walled / uncracked entries (see §4 GIANTS). The crack is valuable; the catalog row is not new.

| Already-in-382 (NOT re-counted) | Why it surfaced again |
|---|---|
| extra.com | R2 had it as `render_required`; R4 cracked Unbxd. Mechanism upgrade only. **KSA-only, no BH delivery.** |
| nahdionline.com | Was an uncracked algolia lead; R4 cracked Algolia keys. Mechanism upgrade. |
| unioncoop.ae | Was uncracked; R4 cracked Algolia secured-key + Referer. Mechanism upgrade. |
| bahrain.sharafdg.com | R1 had it (curl_jsonld fragrance; electronics Algolia uncracked). R4 cracked the electronics Algolia. |
| bn.boots.com | R1 sitemap_jsonld; R4 found a GraphQL json_api alt door. Same domain. |
| taw9eel.com, blink.com.kw, future.com.kw, sporter.com | Known domains, mechanism re-verified/locked. |
| bahrain.ahmarket.com, blankbeautybh.com, bh.asgharali.com, mastermuscles.net, bh.getkuwa.com, noon.com, carrefouruae.com | Already catalogued (R1/R2). Re-verifications, not new. |

> The source sub-agents could not see the 382-domain JSON (returned to the orchestrator), so they reported these as "cracks" in good faith. The dedup here is the authoritative filter.

---

## 1. Live re-verification (dispatcher, 2026-06-25)

Re-verified **>12** of the most valuable NEW sources end-to-end with real retrieved prices (over the required ~12):

| # | Domain | Mechanism | Live result (dispatcher) |
|---|---|---|---|
| 1 | **klinq.com** | Magento GraphQL `Store:default` | "Miss Dior EDP" **48.13 BHD** ✓ |
| 2 | **bh.mubkhar.com** | Shopify products.json + meta.json | "Swash White" **4.000**, meta currency **BHD** ✓ |
| 3 | **danube.sa** | Algolia POST | "Milka Daim Snax 145g" (master_id 65670) ✓ |
| 4 | **panda.sa** | JSON API (gzip, X-Panda-Source header) | products[] returned ("Always Feminine Pads…") ✓ |
| 5 | **trikart.com** | Magento GraphQL `Store:kwt_en` | iPhone 15 256GB Blue **199.9 KWD** ✓ |
| 6 | **nahdionline.com** (crack of dup) | Algolia POST | hits[] returned (Panadol-class) ✓ |
| 7 | **perfumeskuwait.com** | Woo Store API | "Eternity for Men 100ml" **8.900 KWD** (8900/minor3) ✓ |
| 8 | **en-kwt.ajmal.com** | Magento GraphQL `Store:default` | "Violet Musc Hair Mist" **10 KWD** ✓ |
| 9 | **wibi.com.kw** | Shopify products.json + meta.json | ATH-M20x BT **33.500**, currency **KWD** ✓ |
| 10 | **daralamirat.com.sa** | Salla api.salla.dev `Store-Identifier:1945128061` | success:true, **199 SAR** ✓ |
| 11 | **rend-bahrain.com** | Salla `463281575` | success:true, **299 SAR** ✓ |
| 12–16 | **somman / alaseel / parfumdeal / journey1 / rose-store-27** | Salla (5 store-ids) | all success:true, SAR (300 / 62.1 / 155 / 5 / 88) ✓ |

**Sandbox-walled (recorded high/medium-confidence on source-agent's own live retrieval, prod re-probe to lock):**
- **ourshopee.com** — `apios.ourshopee.com` returned a Cloudflare JS-challenge to the dispatcher's plain `curl`; the source-agent retrieved **200 BHD** (Dell Latitude 7420, x-country=6→BHD). Medium until a prod-DNS/curl_cffi re-probe.
- **namshi.com** — Akamai-walls the storefront to WebFetch in this sandbox; the source-agent's `curl_cffi chrome120` got the **direct-PDP JSON-LD** ("48.04" BHD, Nike AF1, InStock). The /search door is 403; the PDP door is the documented mechanism (kept high-confidence on the agent's live retrieval).

---

## 2. ROUND-4 CATALOG — by country, genuine-BHD first

### Bahrain — genuine BHD (4 NEW)
| Rank | Domain | Cat | Platform | Mechanism | API |
|---|---|---|---|---|---|
| 2 | **bh.mubkhar.com** | fragrance/oud | Shopify | shopify_products_json | `/products.json` + `/meta.json`→BHD |
| 3 | **ourshopee.com** | electronics/general | Next + custom API | json_api | `apios.ourshopee.com/api/...` headers `x-country:6`→BHD |
| 4 | **namshi.com** | fashion/footwear | Akamai RSC + PDP JSON-LD | curl_jsonld | direct PDP `/bahrain-en/.../p/` JSON-LD |
| 5 | **matgarbahrain.com** | grocery/supplements | OpenCart | curl_jsonld | `?route=product/product&product_id=` JSON-LD |

### Kuwait — KWD (4 NEW) + 1 BHD beauty giant
| Rank | Domain | Cat | Platform | Mechanism | API |
|---|---|---|---|---|---|
| 1 | **klinq.com** | beauty/fragrance | Magento 2 | json_api | `POST /graphql` `Store:default` → **BHD** (the standout) |
| 8 | **trikart.com** | electronics | Magento 2 | json_api | `POST /graphql` `Store:kwt_en` → KWD |
| 9 | **en-kwt.ajmal.com** | fragrance | Magento 2 | json_api | `POST /graphql` `Store:default` → KWD |
| 10 | **wibi.com.kw** | electronics | Shopify | shopify_products_json | `/products.json` → KWD |
| 11 | **perfumeskuwait.com** | fragrance | WooCommerce | json_api | `/wp-json/wc/store/v1/products` → KWD |

> klinq.com is filed under KW (its corporate base) but the `Store:default` GraphQL store-view returns **genuine BHD** — so it counts in the genuine-BHD subset, the highest-value NEW find of the round.

### Saudi Arabia — SAR (9 NEW: 2 giants + 7 Salla)
| Rank | Domain | Cat | Platform | Mechanism | API |
|---|---|---|---|---|---|
| 6 | **panda.sa** | grocery giant | Next + custom API | json_api | `api.panda.sa/v3/products?q=` `X-Panda-Source:PandaClick` |
| 7 | **danube.sa** | grocery giant | Spree + Algolia | algolia | `1D2IEWLQAD-dsn.algolia.net` index `spree_products` |
| 13 | **daralamirat.com.sa** | makeup/skincare | Salla | json_api | `api.salla.dev` `Store-Identifier:1945128061` |
| 14 | **somman.com** | fragrance | Salla | json_api | `Store-Identifier:1825202310` |
| 15 | **alaseel.com** | fashion/thobe | Salla | json_api | `Store-Identifier:1243938682` |
| 16 | **parfumdeal.salla.sa** | fragrance | Salla | json_api | `Store-Identifier:1392351845` |
| 17 | **rose-store-27.salla.sa** | makeup/fragrance | Salla | json_api | `Store-Identifier:1189735722` |
| 18 | **journey1.salla.sa** | fragrance | Salla | json_api | `Store-Identifier:1828390823` |
| 12 | **rend-bahrain.com** | fragrance | Salla | json_api | `Store-Identifier:463281575` (KSA-billed despite "bahrain" brand) |

**Country split (NEW only):** KSA 9, BH 4, KW 5. **Currency split:** BHD 5, SAR 9, KWD 4.

---

## 3. SALLA HARVEST

**NEW Salla stores verified this round:** **7** — rend-bahrain, daralamirat, somman, alaseel, parfumdeal, rose-store-27, journey1. All returned `success:true` from `api.salla.dev` with a real price + currency.

**Currency reality:** all 7 are **SAR** (convertible-only). **Zero NEW BHD-native Salla store surfaced.** This confirms the standing finding across all rounds: the Salla long tail is overwhelmingly KSA/SAR; BH-billed Salla merchants are rare. (`bh.mubkhar.com`/`alhajisbahrain.com` look Salla-ish by URL but are Shopify — `api.salla.dev` returns 410 for them. The genuine-BHD Salla set remains just the R1 finds like `reefperfumes` BH-geo and the `bh.*` Salla subdomains in R2 — `bh.oudelite.com`, `bh.arabianoud.com`.)

**Repeatable bulk-harvest method (PROVEN + trivially scalable):**
1. **Enumerate `store_id`** — read `"store":{"id":<N>}` from any Salla storefront HTML (custom-domain `.com`/`.sa` or `salla.sa/<slug>`). Discovery feeds: StoreLeads Salla-SA report (free tier = 5/report), `site:salla.sa` search (~10/query), the Salla app-store merchant directory.
2. **Fetch prices — ONE unauthenticated GET:** `GET https://api.salla.dev/store/v1/products?per_page=M&page=N` with header `Store-Identifier:<store_id>`. Cursor-paginated; returns `data[].{name, price, regular_price, sale_price, currency, url, sku}`.
3. **Filter on `data[].currency`** — keep `BHD` as genuine-BH; treat `SAR` as convertible.

**ONE adapter** (`fetch_salla_api_price`, the `Store-Identifier` header client) covers this entire ~4,200-store KSA Salla vein + any future BH-Salla. **The remaining work is pure ENUMERATION, not cracking.** At-scale enumeration needs a paid StoreLeads/BuiltWith Salla-platform export — not Claude tokens.

---

## 4. GIANTS — cracked this round vs render-tier residual

### Cracked this round (mechanism unlocked; most are dups of the 382, value = the endpoint)
| Giant | Was | Now (R4 crack) | Endpoint |
|---|---|---|---|
| **panda.sa** (NEW) | uncracked | json_api | `api.panda.sa/v3/products?q=` + `X-Panda-Source:PandaClick` header gate |
| **danube.sa** (NEW) | uncracked | Algolia | `1D2IEWLQAD` / `spree_products` / `tenant_id=1` |
| **ourshopee.com** (NEW) | Next-SPA render lead | json_api | `apios.ourshopee.com` + `x-country:6`→BHD |
| **namshi.com** (NEW) | Akamai 403 | curl_jsonld alt-door | direct PDP `/bahrain-en/.../p/` JSON-LD (NOT the 403-walled /search) |
| **klinq.com** (NEW) | uncracked | Magento GraphQL | `Store:default`→BHD |
| **extra.com** (dup) | R2 render_required | Unbxd | `search.unbxd.io/<key>/ss-unbxd-auk-extra-*-prod*/search` |
| **nahdionline.com** (dup) | uncracked algolia | Algolia | `H9X4IH7M99` / `prod_en_products` |
| **unioncoop.ae** (dup) | uncracked | Algolia + Referer | `XOC07JLE5W` / `ucprod_english_products_price_asc` (REQUIRES `Referer:+Origin` = unioncoop.ae) |
| **bahrain.sharafdg.com** (dup, electronics half) | electronics Algolia uncracked | Algolia | `9khjlg93j1` / `bahrain_products` / key `e81d5b30…` |
| **taw9eel.com** (dup) | uncracked | Unbxd | `search.unbxd.io/a335256d…/ss-unbxd-prod-taw9eel-ar*/search` (AR key serves title_en) |

### TRULY render-tier-only residual (the honest floor — needs a render budget OR enumeration $)
| Giant | Status | Why it stays render/blocked |
|---|---|---|
| **sephora.me** /bh-en (Chalhoub, genuine-BHD luxury beauty) | RENDER_REQUIRED | Full Akamai `_abck` sensor on ALL `/bh-en/` dynamic+PDP routes; SCAPI/Algolia config env-injected (not in HTML). Root homepage SSRs a curated BHD set as a $0 stopgap, but full catalog-by-query needs a headless XHR capture. |
| **Carrefour MAF Bahrain** (mafbhr, genuine-BHD grocery+electronics) | PARTIAL | `/api/v1/menu` taxonomy is OPEN ($0, no auth) but `/api/v8/search` + `/api/v8/categories` are Akamai 403 (need a guest bearer token / sensor cookie). carrefourbahrain.com DNS-dead in sandbox → prod-DNS re-probe. |
| **xcite.com** (KW electronics) | BLOCKED | Algolia search-only key NOT client-side; routed through a server proxy `/api/algolia/proxy` (HTTP 500 to all replayed bodies — geo-IP/session-gated). Needs a browser XHR under KW geo. |
| **tamimimarkets.com** (KSA grocery) | BLOCKED | SmartStore backend, `/api` path obfuscated in minified chunks; price client-rendered (not in HTML/RSC/__NEXT_DATA__). 17098-PDP sitemap exists. Needs a headless XHR capture of the call site. |
| **spinneys.com** (UAE/KSA) | BLOCKED | Algolia index names known (`sp_products_uae`/`_ksa`) but appId+searchKey injected post-hydration by an AJAX search script. Needs a headless XHR capture. |
| **nextstore.com.kw** (KW Magento) | BLOCKED | Cloudflare "Just a moment" JS challenge on `/graphql`. Needs a CF-solver (flaresolverr) for cf_clearance, then the proven Magento crack applies. |
| **best.com.kw** (Al-Yousifi, KW) | BLOCKED | SAP Hybris OCC host + baseSite not in the SSR shell (in an un-located Angular chunk). Needs the main.js bundle grep → OCC v2 path. |
| **noon.com** /bahrain-en (genuine-BHD) | RENDER_REQUIRED | Akamai TLS-fingerprint wall (HTTP 000 to curl); price in Next RSC. PDP JSON-LD works per R3 §3.1 via curl_cffi but the search door is walled. |
| **halabh.com** (BH Shopify, genuine-BHD) | LOCKED | Shopify password gate (`/products.json` 401, root 302→shopify auth). Pre-launch/dormant — OMIT; recheck periodically. |
| **shop.tamimi / shop.batelco / bh.zain / activefitnessstore / shop.samsung.com/bh** | SPA SHELLS | tiny client-rendered shells, price XHR-loaded. Low BH-catalog priority (narrow device/equipment ranges). |

---

## 5. Integration delta — NEW sources → existing/new adapters

All 18 NEW sources map onto adapters that ALREADY exist or were already proposed in R1–R3. **Net-new client shapes this round: ZERO.**

| Adapter | NEW R4 sources routed to it | Status |
|---|---|---|
| `fetch_shopify_price` (is_shopify) | bh.mubkhar.com (BHD), wibi.com.kw (KWD) | existing |
| `fetch_woocommerce_store_api_price` (json_api) | perfumeskuwait.com (KWD) | existing |
| `fetch_page_price` (curl_jsonld) | namshi.com (PDP JSON-LD), matgarbahrain.com (OpenCart JSON-LD) | existing |
| `fetch_salla_api_price` (Store-Identifier header) | rend-bahrain, daralamirat, somman, alaseel, parfumdeal, rose-store-27, journey1 (7) | proposed R3 — single adapter, whole Salla vein |
| `fetch_algolia_price` | danube.sa (+ the dup cracks nahdi/unioncoop/sharafdg-electronics) | proposed R3 |
| `fetch_magento_graphql_price` (Store-header GraphQL) | klinq.com (BHD), trikart.com (KWD), en-kwt.ajmal.com (KWD) | **R4 confirms this as a recurring GCC pattern** — Store-header Magento GraphQL is now seen across klinq/trikart/ajmal-kwt (+ bn.boots GraphQL alt-door). One generic `Store`-header GraphQL client covers them all. Closest existing kin = the Alshaya `fetch_alshaya_graphql_price` (R2) but that uses Catalog-Service productSearch w/ x-api-key; the vanilla Magento `products(search:){price_range{...}}` form is its own thin shape. |
| `fetch_rest_json_price` (custom-header REST) | ourshopee.com (`x-country` header), panda.sa (`X-Panda-Source` header) | proposed R3 (beautybooth) — each just needs its required-header tuple |
| `fetch_unbxd_price` | (dup cracks only: extra.com, taw9eel.com) | proposed R2 |

**Takeaway:** the platform-mechanism space is fully characterized. Every NEW source slots into one of 8 adapters already on the build list. The Store-header Magento GraphQL family (klinq/trikart/ajmal/bn.boots) is the one pattern worth a dedicated thin client given how many GCC Magento stores expose it.

---

## 6. FINAL SATURATION DECLARATION

### Counts
- **R1:** 85 · **R2:** 214 · **R3:** 83 → **382 known unique domains** (zero cross-round dups).
- **R4 NEW (deduped, hard-filtered):** **18**.
- **COMBINED GRAND TOTAL across all 4 rounds: 400 unique source domains.**

### Is the sweep complete?
**Yes — this is effectively the floor of what is $0-reachable.** Evidence:

1. **Diminishing returns are explicit.** R1→R2 was +214 (broad SMB sweep), R2→R3 was +83 (GCC-sibling expansion), R3→R4 was **+18** — and R4 only got 18 by deliberately abandoning generic SMB hunting (saturated) and chasing the named high-value remainder. The yield curve has flattened.

2. **Of the 34 R4 candidates, 16 (47%) were already in the 382** — the hit rate on "new" domains is collapsing because the catalog already covers the space. New finds increasingly require either (a) a giant whose key is render-injected, or (b) Salla store-id ENUMERATION (a paid-data problem, not a discovery problem).

3. **The mechanism space is closed.** Zero genuinely-new client shapes appeared in R4. Everything maps to 8 known adapters. There is no new platform to discover.

4. **The genuine-BHD ceiling is structural, not a discovery gap.** R4 added 5 BHD sources (klinq is the prize — a real beauty-giant BHD catalog) but BHD-native Salla stays rare and the biggest BHD luxury catalogs (sephora.me, Carrefour Bahrain, noon) are Akamai/sensor-walled. No amount of further $0 discovery cracks those — they need a render budget (Scrape.do super / Firecrawl with a sensor cookie) or a headless XHR-capture pass.

### What remains truly unreachable without a render budget (the honest residual)
- **sephora.me /bh-en** (genuine-BHD luxury beauty) — Akamai `_abck` sensor.
- **Carrefour Bahrain (mafbhr)** product/price — taxonomy open, price token-gated.
- **noon.com /bahrain-en** search — Akamai TLS wall (PDP JSON-LD works via curl_cffi).
- **xcite / tamimimarkets / spinneys / nextstore / best.com.kw** — server-proxied or post-hydration-injected keys (need one headless XHR capture each to convert to json_api; then the existing adapters apply).

### Is a Round 5 ever worth it?
**No, not as a discovery round.** A 5th $0 discovery sweep would yield single-digit new domains for the token cost. The remaining leverage is in TWO non-discovery moves, both of which are cheap and high-yield:
1. **Salla enumeration via a paid StoreLeads/BuiltWith export** — converts the proven `fetch_salla_api_price` adapter into thousands of stores with zero further cracking. (Data $, not Claude tokens.)
2. **A ONE-TIME headless / render-budget XHR-capture pass** over the 5–6 walled giants (sephora.me, Carrefour-BH, xcite, tamimi, spinneys) to read their injected keys → convert each render-tier residual into a $0 json_api/algolia adapter. (One Firecrawl/Scrape.do-super session, not a recurring cost.)

**Verdict: 400 domains across 4 rounds. The $0-discoverable space is SATURATED. The catalog is the deliverable; the next dollar of value is in Salla enumeration (paid data) and a single render-budget key-capture pass — not a Round 5.**

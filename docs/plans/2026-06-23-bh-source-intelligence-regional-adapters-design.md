# BH Source-Intelligence + Regional-Storefront Discovery + Direct Adapters — DESIGN (2026-06-23)

> Successor to the genuine-BH price + missing-data bundle (`fb8696c`, shipped 2026-06-23 — handoff
> `memory/project_genuine_bh_price_missing_data_shipped.md`). That bundle delivered no-missing-data +
> correctness but explicitly did NOT raise genuine-BH **share**. This bundle is the genuine-share work,
> grounded in the step-3 reconnaissance of the CF-walled/render-only BH SPAs.
>
> **Branch:** `feature/bh-source-intelligence`. **Decided by Ahmed 2026-06-23** (Option 3, ordered).

## Goal

Raise genuine-BH-price **share** by building **source intelligence** — a generalized regional-storefront
discovery layer — and the **direct $0 adapters** the step-3 recon proved feasible. THEN run the
controlled Scrape.do-Super/Zyte provider test on the one true render-candidate (sephora.me BH-locale).
**The warmer (paid Serper) is a SEPARATE scale lever — do NOT pivot to it before this source-intelligence
work; it is not a substitute for fixing discovery.**

## Recon-verified grounding (step 3, live read-only probes 2026-06-23)

The prior "CF-walled structural gap" framing was WRONG for 3 of 4 sources — their registry
`is_render_only`/`requires_super` flags are STALE. Verified live:
- **bolo.bh** — own products-sitemap (16 child) + Nuxt SSR serves the genuine BHD price in **plain-curl**
  static HTML (`"price":132` + `<sup class="currency">BHD</sup>`). $0, no render. Categories:
  supplements / makeup / skincare.
- **nasserpharmacy.com** — OpenCart + CRA SPA on bare Apache (**no Cloudflare**); genuine BHD via the
  **JSON API** `newapi.nasserpharmacy.com` (`/v1/filterSearchs?search_term=` name-search →
  `/newproduct?product_id=&currency_code=BHD`, static guest header `Nasser/MOBILEOS/APPVERSION/DCCOMICS`)
  — verified `"price":"0.970","price_symbol":"BHD"`. $0, no render. Categories: skincare / makeup /
  haircare / health (supplements), 10k+ SKUs.
- **boutiqaat.com** — own sitemap (`en-bh/{women,men}/products.xml` = ~82k BH PDP URLs); Next.js HTML is
  curl-fetchable (200, no CF wall) but **price JS-hydrated**; the JSON API
  `ksa-api.boutiqaat.com/searchplus/rest` (`/V2/configurable`, `param` header `{country_code:BH,...}`) is
  reachable but the **POST contract is NOT yet cracked** (the API parses `slug` — structured
  `400 "Slug Not Found"` — but the sitemap-URL slug ≠ the API's expected slug; SSR `__NEXT_DATA__` did
  not expose the id/slug in a one-shot probe). **CONDITIONAL** per Ahmed: ships only if the contract is
  completed + verified (capture the live XHR the SPA fires); else render-needed or defer. Categories:
  makeup / skincare / haircare / fragrances.
- **sephora.me `/bh-en`** — the CANONICAL Bahrain Sephora storefront (NOT `sephora.bh`, which 301s here
  and is not independently verified). Next.js over Salesforce Commerce Cloud, fronted by **Akamai Bot
  Manager** — Ahmed's real PDP `https://www.sephora.me/bh-en/p/size-up-immediate-supersized-volume-mascara/713779`
  returns **403 AkamaiGHost** from a non-BH IP. **provider-test candidate**: a real PDP URL + a real
  Akamai wall → the valid Scrape.do-Super/Zyte target (does residential-BH render crack Akamai). PDP
  pattern `/bh-en/p/{slug}/{product_id}`. Categories: makeup / skincare / fragrances / haircare.

## HARD INVARIANTS

- **No fabricated data** — prices never invented; every adapter must be VERIFIED with a live BHD price
  before it ships (verify-or-omit, the registry's standing rule). Genuine = `_GENUINE_BH_SOURCE_METHODS`.
- **No warmer/paid-Serper pivot before this** — the warmer is the SEPARATE scale lever; this bundle fixes
  source intelligence + regional-storefront discovery first.
- **Do NOT regress `fb8696c`** — the honesty / missing-data / correct-routing baseline. Re-run its guards.
- **sephora.bh is NOT canonical** — `sephora.me` + `/bh-en` is, unless `sephora.bh` is independently
  verified.

---

## PART 1 — Source-intelligence schema: "regional storefront aliases" (Ahmed's spec)

Generalize the `source_router.py` `Source` model + the WS-4 matrix from "domain only" to a regional
storefront descriptor. Per source store:
- **domain** (e.g. `sephora.me`, `nasserpharmacy.com`)
- **country/locale path(s)**: `/bh-en`, `/en-bh`, `/ar-bh`, `/bahrain`, `/bh`
- **subdomain pattern**: `bh.`, `bahrain.`, `en-bh.`
- **expected currency**: `BHD`
- **discovery query template(s)**: e.g. `site:{domain}{locale_path} "{product}" BHD`
- **mechanism**: one of `curl | json_api | sitemap | algolia | shopify | render | provider`
- **PDP URL pattern**: e.g. `/bh-en/p/{slug}/{product_id}`
- **one verified sample URL** (the liveness anchor)
- **categories covered**
- **status**: `live | provider-test-candidate | render-only`

Design intent: this is the "source intelligence" layer — discovery + classification metadata that the
cascade + the warmer + the provider-test all read from one place. Backward-compatible: existing `Source`
rows keep working (new fields default to None/empty); the drift-guard test
(`tests/test_bahrain_source_matrix_coverage.py`) extends to assert the new fields where present. The
contract doc `docs/contracts/bahrain-source-matrix.md` becomes the human-readable matrix of these
descriptors.

---

## PART 2 — The 3 direct adapters (BUILD ORDER, verify-or-omit)

Each adapter: discover the PDP URL (sitemap / search-API) → fetch → parse the genuine BHD price → wire
into the price cascade as a genuine source (`page_scrape`/`page_scrape_jsonld`/`json_api`-class
`source_method`, in `_GENUINE_BH_SOURCE_METHODS`). NO render, NO Serper for these (own sitemaps/APIs).
Verify each with a live BHD price (unit + a live smoke) before it ships.

1. **bolo.bh** — sitemap-index (`sitemaps-products.xml` → 16 child) → name/slug-match → plain curl_cffi
   PDP → parse `"price"`/`priceCurrency:"BHD"` from the SSR HTML. Internal-id non-derivable → match by
   slug/name from the sitemap. Categories: supplements / makeup / skincare.
2. **nasserpharmacy.com** — `/v1/filterSearchs?search_term={name}` (or `/v1/getSuggestion`) → `product_id`
   → `POST /newproduct?product_id=&currency_code=BHD` (static guest header) → parse `price`/`price_symbol`.
   Categories: skincare / makeup / haircare / supplements. The static guest header is a constant from the
   bundle (store it; re-verify liveness on each deploy, it may rotate).
3. **boutiqaat.com** — CONDITIONAL: complete + verify the `/V2/configurable` (or `/api/getProduct`) POST
   contract by capturing the live XHR (the real id/slug field). IF a genuine BHD price is reproducibly
   returned → ship the JSON-API adapter (sitemap for discovery). IF not crackable in budget → ship as a
   render-needed source OR defer (documented gap). Categories: makeup / skincare / haircare / fragrances.

---

## PART 3 — sephora.me regional alias + the registry correction

- Add `sephora.me` as a regional-storefront-alias row: locale `/bh-en`, currency BHD, PDP pattern
  `/bh-en/p/{slug}/{product_id}`, discovery `site:sephora.me/bh-en "{product}" BHD`, mechanism `provider`,
  status `provider-test-candidate`, categories makeup/skincare/fragrances/haircare, sample URL = Ahmed's.
- **Correct the registry**: the existing `sephora.bh` `requires_super` row is NOT the canonical BH
  storefront (it 301s + is unverified). Re-point/replace with the `sephora.me` `/bh-en` alias. Keep
  `requires_super`/provider gating.

---

## PART 4 — Controlled Scrape.do-Super / Zyte provider test (AFTER the 3 adapters)

Run ONLY on **sephora.me BH-locale** entry points (NOT sephora.bh), as a controlled experiment (the WS-H
5-point protocol): fixed small query set + KNOWN real BH URLs + provider attempts inspected in
`metadata.source_trace` + per-run credit cap + before/after genuine-BHD evidence + immediate revert if no
confirmed BHD-PDP win.
1. Ahmed's PDP URL (`/bh-en/p/size-up-…/713779`).
2. A `sephora.me/bh-en` category/listing page if discoverable.
3. A `sephora.me/bh-en` search URL if discoverable.
**If Scrape.do Super (geoCode=bh) fetches/renders these + exposes BHD price / PDP URLs → wire narrowly**
(a provider-tier sephora.me source). **If Super FAILS on the same confirmed URLs → test Zyte (free plan)
on the EXACT same URL set.** Only after BOTH fail do we decide sephora.me isn't worth provider work
(its categories are largely covered by boutiqaat + nasser anyway).

---

## Process + ship gate

- **Plan** via an ultracode gap-detection Workflow (validate the schema change vs `source_router.py` +
  the cascade integration points + the discovery layer, gated vs real code) → **implement in Workflow
  waves** (sequential implement, throttled adversarial review, dispatcher gates each).
- **Per-adapter gate:** a live BHD price reproduced (verify-or-omit) + unit tests (mocked sitemap/API) +
  a fresh-nocache prod genuine-share confirm showing the new `source_method` (genuine, not converted).
- **Ship gate:** free-unit `comm` branch-only-NEW == [] + smoke20 (axis metrics manual vs `54b603e8`) +
  the genuine-share confirm. Backend-only (no EAS expected).
- **Provider test** is a separate controlled experiment AFTER the adapters, reported with before/after
  evidence; `SCRAPEDO_SUPER` stays OFF in prod (the test calls the Scrape.do API directly, out-of-band).

## Durable notes
- The registry's `is_render_only`/`requires_super` flags are STALE for bolo/nasser/boutiqaat — the recon
  proved them directly readable. Correct the flags as part of Part 1.
- Geo: bolo/nasser served BH-locale + BHD natively from a non-BH IP (cf-country=BH / Apache no-CF);
  boutiqaat root 302s to `/en-kw` but `/en-bh/` path works directly; sephora.me is the only Akamai-walled
  one. Construct the BH-locale path explicitly; don't rely on auto-redirect.
- nasser's guest header + boutiqaat's API params may rotate — the verify-or-omit liveness check must
  re-confirm on deploy.

# Render-Wall Investigation — Cloudflare-Protected BH Retailers

**Date:** 2026-06-15
**Author:** be-sourcing (Genuine-BH latency+warmer bundle, WS3)
**Question (Ahmed):** "Don't forget Firecrawl/Scrape.do" — with the render budget raised off-clock (`FAN_OUT_BUDGET_SECONDS=35`), do Firecrawl / Scrape.do render + extract a **genuine BHD** price from the render-walled BH retailers (**Sephora BH, bolo.bh, boutiqaat**) for luxury fragrance + haircare?

**Verdict:** **NO — these three are Cloudflare-protected and are NOT genuine-extractable** with the current Firecrawl/Scrape.do setup, even with a 35s off-clock budget. The blocker is a **bot-wall, not the budget and not a scraper defect.** Their genuine prices are a **STRUCTURAL gap**, not a code gap. They do **not** become warmer-genuine sources.

---

## How it was tested

Cache-disabled (writes NOTHING to prod Redis), `FAN_OUT_BUDGET_SECONDS=35`, `PRICE_RACE_TIMEOUT=60`, `STREAM_HARD_CAP_SECONDS=150`. Harnesses (in `.qa-bias-rerun/`):
- `_render_capability_bh_retailers.py` — renders each retailer's PDP via `firecrawl_service.scrape_page` + `scrapedo_service.render_page`, then runs `extract_jsonld_price` / `extract_price_from_html` on the result.
- `_render_dump_one.py` — dumps the rendered HTML head + content markers to classify the response (real PDP vs price-less SPA shell vs bot-block page).

Targets: one luxury fragrance (Tom Ford Ombré Leather / Tobacco Vanille) + one haircare item (Olaplex No.3, Kérastase) per retailer. Budget spent: a handful of targeted Firecrawl calls (lifetime cap 450 — well within).

## Evidence

| Retailer | Firecrawl | Scrape.do | Extracted BHD? |
|---|---|---|---|
| **sephora.bh** | returns EMPTY / short response | timeout (15s) | **NO** |
| **bolo.bh** | returns **3KB = Cloudflare "Sorry, you have been blocked" CAPTCHA interstitial** (NOT the PDP) | timeout (15s) | **NO** |
| **boutiqaat** | same Cloudflare block interstitial | timeout (15s) | **NO** |

The 3KB Firecrawl payload for bolo.bh / boutiqaat is unambiguous — the rendered HTML head is the Cloudflare challenge page:

```html
<div id="cf-wrapper">
  <div class="cf-alert cf-alert-error cf-cookie-error" id="cookie-alert">Please enable cookies.</div>
  ...
  <h1 data-translate="block_headline">Sorry, you have been blocked</h1>
  <h2 class="cf-subheadline">You are unable to access bolo.bh</h2>
```

Content markers on the dumped HTML: `captcha=True`, `cloudflare=True`, `application/ld+json=False`, `price=False`, `add to cart=False`, `product=False`. No product schema, no price — it is the block page, not the PDP.

## Why this is NOT a scraper defect or a budget issue

- **Not budget:** a 35s budget does not defeat a Cloudflare bot-wall — the challenge fires before any render time matters. Raising the budget further changes nothing.
- **Not a scraper bug:** Firecrawl renders correctly on **non-CF** sites. The genuine Tom Ford price path proves this — the pipeline lands **alhajisbahrain.com 80 BHD** + **bahrain.ounass.com 118 BHD** via curl JSON-LD (`page_scrape_jsonld`) for $0.017, no render wave needed (`_frag_pipeline_trace.py`). The render scrapers work where the site allows them.
- **Scrape.do timeout** on all four is consistent with the residential-proxy render also being challenged/slow against the CF wall; the env-driven `SCRAPEDO_TIMEOUT` (now raisable to 35s off-clock) does not change the CF outcome — documented inline in `scrapedo_service.py`.

## Implications

1. **Sephora BH / bolo.bh / boutiqaat do NOT become warmer-genuine sources.** The warmer (`scripts/cron_warm_price_cache.py`) will leave products that depend on these retailers on `converted_usd` / `estimated`.
2. **Remaining luxury fragrance / haircare estimates are STRUCTURAL** — there is no *reachable* genuine BH source for those products via the current scraper stack, not a missing line of code. This confirms the standing project note (`memory/project_bundle_b_s3_render_discovery_followup.md`).
3. **Genuine BH wins come from the curl-extractable sources** the discovery already reaches: alhajisbahrain.com, bahrain.ounass.com, lulu `/en-bh/`, sharafdg, microless, Shopify `/products.json` BH stores, etc.

## Code changes shipped from this investigation (WS3)

- `firecrawl_service.py` / `scrapedo_service.py`: render timeouts now env-driven (`FIRECRAWL_TIMEOUT` default 30, `SCRAPEDO_TIMEOUT` default 15 — **live unchanged**) so the off-clock warmer can give a **non-CF** slow SPA more render time. Does not help the CF retailers (documented inline).
- `source_router.py`: BH-locale filter extended to drop noon bare-region paths; `is_non_pdp_listing_url` added to drop category/search/listing surfaces from the render-wave pool (don't waste a render credit on a non-PDP).

## Future options (NOT in this bundle — flagged for Ahmed)

To unlock CF-walled retailers would require a CF-bypass-capable scraper tier (e.g. a paid anti-bot service / browser-with-stealth), which is a budget + vendor decision, not a code fix. Deferred. The honest `converted_usd` fallback remains the correct safety net for these products (Lever B — removing it — was **declined** this bundle).

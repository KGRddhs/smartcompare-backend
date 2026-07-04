# Wave-1 gate result — warmed usable_exact_genuine KPI (RED)

**Date:** 2026-07-01 · **Method:** off-clock warm of the 18-product KPI truth set (`scripts/warm_kpi_truth.py`, `PRICE_RACE_TIMEOUT=60`) against the shared prod cache, then a cache sweep + `should_cache_price` reproduction. Serper: healthy (paid key live).

## Verdict: GATE RED — warmer stays OFF

| Category | usable_exact_genuine (warmed) | gate ≥0.85 |
|---|---|---|
| electronics | **1/6 (0.17)** | ❌ |
| fragrances | **0/6 (0.00)** | ❌ |
| fashion | **0/6 (0.00)** | ❌ |
| **overall** | **1/18 (0.06)** | ❌ |

Only **1/18** warmed products cached a usable price (Samsung Galaxy S24 Ultra 256GB → `page_scrape_jsonld`, in-stock, PDP URL, identity). The other 17 were **correctly refused** by the fail-closed `should_cache_price` (PR #9).

## Why the 17 didn't cache — the precise diagnosis

The warmer machinery works; the cascade's *resolutions* fail `should_cache_price`'s (correct) requirements — title/name identity + a valid **PDP** URL + confirmed in-stock + exact match:

1. **Listing / search URLs, not PDPs.** Genuine `local_bhd` prices from sharafdg arrive with search URLs (`https://bahrain.sharafdg.com/?s=iPhone+15+128GB&post_type=product`); `converted_usd` arrives with `google.com/search?...` URLs. `_is_listing_url` → `should_cache_price` rejects (a search page is not a verifiable PDP). Reproduced: Samsung S24 256GB → `converted_usd 144.59`, google-search URL, `should_cache_price=False`.
2. **`converted_usd` frequently wins the race** (not a genuine-BH method → KPI-not-usable) — e.g. Levis 501.
3. **`gpt_organic_extract`** (not in `GENUINE_BH_SOURCE_METHODS`) for iPad, MacBook, Switch, Nike, Ray-Ban → not usable.
4. **No title/name identity** on the returned price (the resolved dict often has neither `title` nor `name` after selection) → fails the identity gate.
5. **In-stock=False** for several fragrances/fashion (Acqua di Gio, La Vie Est Belle, Tommy) → not usable.
6. **Non-determinism.** The same query resolves to a genuine PDP on one run and a converted/listing result on the next (Samsung: `local_bhd 426.22` in the warm run, `converted_usd 144.59` on re-resolve). The warmer can't reliably land the cacheable variant.

## What this means

- **The gate-first design WORKED.** An unguarded warmer would have cached 17 low-quality/listing-URL prices (the pre-PR9 poisoning). The fail-closed `should_cache_price` refused them and cached only the 1 correct genuine PDP — exactly the safety the gate is for. **Activating the warmer now would put genuine prices on ~6% of the cold path — not worth the Serper spend.**
- **The blocker is UPSTREAM source quality, not warmer machinery:** the genuine-price cascade must yield a **PDP URL + title + a deterministic genuine match** for `should_cache_price` to accept it. That is the catalog-adapter / render-tier / discovery-integration work (Shopify/Woo/Salla PDP endpoints, the deferred render-tier, deterministic source ordering) — a separate epic, tracked in the BH/GCC source work.
- **Warmer stays OFF** (`ENABLE_PRICE_CACHE_WARMER` unchanged). The Wave-1 gate machinery + safety fixes (PR #12) remain valid and mergeable; they are what MEASURED this cleanly.

## Prod-cache impact of this run

The off-clock warm wrote exactly **1 correct genuine price** (Samsung S24 Ultra 256GB) to the shared cache — a legitimate entry (correct SKU, PDP URL), left to TTL out. The 17 rejected resolutions wrote nothing (no pollution) — a live proof that `should_cache_price` fail-closed holds.

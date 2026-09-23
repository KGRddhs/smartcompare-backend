# Sitemap discovery channel — measured viability (2026-08-17)

**Verdict: not worth building as a generic channel. 7 of 47 candidate domains are viable
(3 bahrain-tier), and 7 is a CEILING, not a forecast.** Recorded here so this is not
re-investigated from scratch.

## Why "extend the sitemap index to all live sources" does not work

The sitemap channel is **not** index-only. `structured_comparison_service._sitemap_price_fetchers()`
is a hardcoded per-domain map:

```python
{"bolo.bh": fetch_bolo_price, "boutiqaat.com": fetch_boutiqaat_price}
```

and the prefetch loop (`scs.py` ~5258) **pre-filters `_sitemap_sources_pf` to domains present in
that map** — an unmapped sitemap domain resolves to `None` by design. Each mapped adapter carries
store-specific PDP parsing (bolo = Nuxt `@graph` JSON-LD with the related-products binding trap).

So registering `mechanism="sitemap"` rows or building indexes for more domains produces indexes
**nothing consumes**. Making the channel general requires a new generic adapter
(`resolve_pdp_via_sitemap` → `fetch_page_price`), which is the real cost.

## The measurement

For each of the 47 catalog sources that have a products sitemap but no platform JSON API: walk the
sitemap (preferring a product-named child sitemap), filter out policy slugs, sample up to 3 PDPs,
fetch each, and ask whether `extract_price_from_html` reads a price **when handed the page's own
product name** (from JSON-LD `Product.name`, else `<title>`).

| outcome | n |
|---|---|
| VIABLE | **7** (bahrain: ashrafsbahrain.com, d4donline.com, geekay.com) |
| NO_PDP_URLS | 24 — sitemap exposes no recognisable product URLs |
| NO_STRUCTURED_PRICE | 14 — PDP reachable, no price the generic extractor can read |
| WALLED / NO_NAME | 2 |

Viable: `ashrafsbahrain.com` 4.0 BHD · `d4donline.com` 169.0 BHD · `geekay.com` 22.43 BHD ·
`faces.ae` 500 AED · `faces.sa` 637 SAR · `jnknutrition.com` 55 AED · `mls.om` 106.26 OMR.

**This is a ceiling.** The extractor was given each page's own product name — the easiest possible
query. The live path must match an arbitrary user query through the fail-closed identity gate, so
real yield is lower.

Raw data: `phase1_sitemap_viability2.json`.

## Two measurement bugs worth remembering

A first pass reported 2/47 and was wrong on both counts:

1. **Marker matching selects policy pages.** `_PDP_PATH_MARKERS = ("/products/", "/p/")` matches
   `/p/delivery-information`, `/p/payment-methods`, `/p/our-branches`, `/p/privacy-policy`. The
   probe sampled those and recorded "no price" for perfectly good stores.
2. **Slug-derived query names are junk** (`"layala lenses layala lenses lenses"`), and the identity
   gate is fail-closed, so it rejected valid prices. `faces.ae` returns 247.0 when queried with the
   page's own title and nothing when queried with the slug.

Always separate "the page has no price" from "my query was bad" before concluding.

## Live defect found (low severity, currently dormant)

`sitemap_discovery_service._is_pdp_url` returns `True` for `/p/delivery-information`,
`/p/payment-methods`, `/p/our-branches`, `/p/privacy-policy` — they would be indexed as products
with slugs `"delivery information"`, `"payment methods"`, etc.

Severity is **low**: the matcher requires every query token ⊆ slug tokens, and no real product
query matches those slugs, so this is index bloat (wasted `_BUCKET_CAP` slots), not a wrong-price
serve. It is dormant today because `ENABLE_SITEMAP_INDEX` is off. Worth a junk-slug filter if the
channel is ever activated for a store that uses `/p/`.

## If this is revisited

The cheapest viable shape is a generic `fetch_sitemap_page_price(domain, product_name, currency,
category)` registered as the default in `_sitemap_price_fetchers()`, plus a junk-slug filter, plus
per-domain sitemap-index URLs in `scripts/cron_index_sitemaps._INDEX_URLS`. It also needs
`get_sitemap_sources_for_category` widened past bahrain-tier (most viable domains are gcc), and a
Railway cron registered for `scripts.cron_index_sitemaps` — explicitly an Ahmed decision per that
script's docstring.

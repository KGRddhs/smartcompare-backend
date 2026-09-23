# The 45 catalog sources with no owned channel (2026-08-17)

Companion to `2026-08-17-sitemap-channel-viability.md`. These are the live catalog rows that
answered **neither** a platform JSON API (Shopify `/products.json`, Woo Store API) **nor** a usable
products sitemap during the Phase-1 sweep.

## Wider endpoint sweep

Before concluding "render tier only", each of the 45 was probed against a wider platform
fingerprint set: Magento GraphQL + Magento REST, Salla, Shopify `/collections/all/products.json`,
WooCommerce `wc/v3`, generic `wp-json`, Next.js `_next/data`, SFCC OCAPI, BigCommerce storefront.

| result | n |
|---|---|
| Magento GraphQL responds | **6** — `bawwaba.om`, `bh.adilstore.com` (bahrain), `kwt.nazih.com`, `nazih.ae`, `nazih.qa`, `oman.ahmarket.com` |
| No public API of any probed shape | **39** |

No hits at all for Salla, Woo v3, SFCC, BigCommerce, or the Shopify alternate path.

## The 6 Magento hits do NOT work through the existing adapter

All 6 were tested through the production `fetch_magento_graphql_price`, using product names pulled
from **each store's own GraphQL** (so the query cannot be blamed). **All 6 miss.**

Root cause is structural, not a matcher problem — `magento_graphql_service.py:560`:

```python
store = _MAGENTO_STORES.get(host)
...
if not store:
    return None
```

`_MAGENTO_STORES` is a hardcoded per-store config registry (`klinq.com`, `trikart.com`, …) keyed by
host, carrying `shape` (A = Alshaya catalog-service, B = vanilla Magento core), `store_view` (sent
as the `Store:` header), and the store's brand-label field. An unregistered host returns `None`
immediately.

So each of the 6 needs a **bespoke config entry**, which means per-store discovery of the correct
`store_view` value and brand field, then a liveness verification. That is per-domain research, not
a data promotion.

## Assessment

Yield is 6 domains, **1 of them Bahrain-tier** (`bh.adilstore.com`, grocery), each costing
per-store reverse-engineering. Same shape of trap as the sitemap channel: the endpoint responding
is not the same as the adapter working.

Recommend leaving these alone unless a specific one becomes commercially important. The 39 with no
public API would need the render tier (Firecrawl/Scrape.do) — and note Zyte is currently
**suspended**, so the luxury/Akamai render path is already down to two vendors.

Raw data: `phase1_nochannel_probe.json`.

## Durable

An endpoint that returns 200 JSON is necessary but NOT sufficient — verify through the runtime
adapter. This sweep and the sitemap sweep both found the adapter gate (`_MAGENTO_STORES` config,
`_sitemap_price_fetchers` map) is what actually decides coverage, not the store's technology.

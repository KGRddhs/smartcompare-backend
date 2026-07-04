/**
 * Bundle C — Price provenance helper (Plan B.7.6, spec § 5c).
 *
 * `parseSourceMethod` returns approved EN phrasing for non-estimated
 * source methods. Returns `null` for `'estimated'` (and unknown values),
 * signaling callers to SUPPRESS the Price confidence pill entirely.
 *
 * `anyEstimated` is a small adapter for the Results screen layer: when
 * ANY product in the comparison has `price.source_method === 'estimated'`,
 * the Price confidence pill is hidden across the comparison (per § 5c
 * "no provenance copy anywhere in the UI").
 *
 * Critical rule #3 — NO `estimated` / `reference price` / `indicative`
 * (EN) or `تقدير` / `مُقدَّر` (AR) in any returned phrase. Guarded by
 * a regex test in __tests__/services/sourceMethod.test.ts.
 */
import type { Product, SourceMethod } from '../types';

const APPROVED: Partial<Record<SourceMethod, string>> = {
  local_bhd: 'Direct local listing',
  // Genuine-BH bundle: real BHD from a retailer Shopify /products.json — a
  // genuine local listing, same approved phrasing as the other page methods.
  shopify_json: 'Retailer page',
  converted_usd: 'Local listing',
  page_scrape: 'Retailer page',
  // Genuine-BH bundle (WS3): curl JSON-LD off a retailer PDP — a genuine
  // local listing, same approved phrasing as the other page-scrape methods.
  page_scrape_jsonld: 'Retailer page',
  page_scrape_rendered: 'Retailer page',
  firecrawl: 'Retailer page',
  scrapedo_rendered: 'Retailer page',
  // 'estimated' deliberately omitted — callers MUST suppress the UI
  // element entirely rather than render any provenance phrasing.
};

export function parseSourceMethod(method: SourceMethod | undefined): string | null {
  if (!method) return null;
  return APPROVED[method] ?? null;
}

export function anyEstimated(products: Array<Pick<Product, 'price'>>): boolean {
  return products.some((p) => p?.price?.source_method === 'estimated');
}

/**
 * A `converted_usd` price is a REAL retailer listing that was priced in USD
 * (or another non-BHD currency) and converted to BHD by the backend — it is
 * NOT a genuine local BHD listing. Any surface that shows a converted price
 * MUST render the `results.convertedUSD` caption ("(converted from USD)")
 * beside the amount, so a converted price is never presented as identical to
 * a genuine local price (the display-honesty gap this closes).
 *
 * Accepts any object carrying an optional `source_method`, so it works for
 * both the full `ProductPrice` (Results screen) and the narrow streaming
 * price shape (StreamingProductCard).
 */
export function isConvertedUsd(
  price: { source_method?: SourceMethod } | null | undefined,
): boolean {
  return price?.source_method === 'converted_usd';
}

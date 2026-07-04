/**
 * Bundle C — sourceMethod helper (Plan B.7.5)
 *
 * Spec § 5c — Price provenance is silent in the UI. The helper returns
 * approved phrasing for non-estimated methods and NULL for "estimated",
 * which signals callers to suppress the Price confidence pill entirely.
 *
 * Critical rule #3 — NO "estimated" / "reference price" / "indicative"
 * (EN) or "تقدير" / "مُقدَّر" (AR) in any returned phrase.
 */
import { parseSourceMethod, anyEstimated, isConvertedUsd } from '../../src/services/sourceMethod';

test.each([
  ['local_bhd', 'Direct local listing'],
  ['converted_usd', 'Local listing'],
  ['page_scrape', 'Retailer page'],
  ['page_scrape_rendered', 'Retailer page'],
  ['firecrawl', 'Retailer page'],
  ['scrapedo_rendered', 'Retailer page'],
])('parseSourceMethod(%s) returns approved phrasing %s', (method, expected) => {
  expect(parseSourceMethod(method as any)).toBe(expected);
});

test('parseSourceMethod("estimated") returns null (caller must suppress)', () => {
  expect(parseSourceMethod('estimated')).toBeNull();
});

test('parseSourceMethod(undefined) returns null', () => {
  expect(parseSourceMethod(undefined)).toBeNull();
});

test('anyEstimated returns true when ANY product has estimated source', () => {
  const products = [
    { price: { source_method: 'firecrawl' as const } },
    { price: { source_method: 'estimated' as const } },
  ] as any;
  expect(anyEstimated(products)).toBe(true);
});

test('anyEstimated returns false when NO product has estimated source', () => {
  const products = [
    { price: { source_method: 'firecrawl' as const } },
    { price: { source_method: 'local_bhd' as const } },
  ] as any;
  expect(anyEstimated(products)).toBe(false);
});

test('anyEstimated returns false on empty product list', () => {
  expect(anyEstimated([])).toBe(false);
});

test('anyEstimated tolerates missing price object (treats as non-estimated)', () => {
  const products = [
    { price: { source_method: 'firecrawl' as const } },
    {}, // no price field at all
  ] as any;
  expect(anyEstimated(products)).toBe(false);
});

test('anyEstimated tolerates missing source_method on a price object', () => {
  const products = [
    { price: { amount: 99.9, currency: 'BHD' } }, // no source_method
    { price: { source_method: 'firecrawl' as const } },
  ] as any;
  expect(anyEstimated(products)).toBe(false);
});

test('parseSourceMethod NEVER returns forbidden words across all approved methods', () => {
  const all = ['local_bhd', 'converted_usd', 'page_scrape', 'page_scrape_rendered', 'firecrawl', 'scrapedo_rendered'] as const;
  const forbidden = /\b(estimated|reference price|indicative|approximate)\b/i;
  const forbiddenAr = /(تقدير|مُقدَّر)/;
  for (const m of all) {
    const phrase = parseSourceMethod(m);
    expect(phrase).not.toBeNull();
    expect(phrase!).not.toMatch(forbidden);
    expect(phrase!).not.toMatch(forbiddenAr);
  }
});

// Display-honesty: converted-from-USD prices must be distinguishable from
// genuine local prices. `isConvertedUsd` gates the caption on those surfaces.
test('isConvertedUsd is true only for a converted_usd price', () => {
  expect(isConvertedUsd({ source_method: 'converted_usd' })).toBe(true);
});

test('isConvertedUsd is false for genuine, estimated, and missing methods', () => {
  expect(isConvertedUsd({ source_method: 'local_bhd' })).toBe(false);
  expect(isConvertedUsd({ source_method: 'shopify_json' })).toBe(false);
  expect(isConvertedUsd({ source_method: 'page_scrape' })).toBe(false);
  expect(isConvertedUsd({ source_method: 'firecrawl' })).toBe(false);
  expect(isConvertedUsd({ source_method: 'estimated' })).toBe(false);
  expect(isConvertedUsd({})).toBe(false);
  expect(isConvertedUsd(undefined)).toBe(false);
  expect(isConvertedUsd(null)).toBe(false);
});

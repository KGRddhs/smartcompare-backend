/**
 * confidenceDetailsLines — #105.
 *
 * The backend ships `scoring_v2.confidence_details` as nested dicts
 * (`response_builder._confidence_legs_and_details`, verified at b073918):
 *
 *   price:   { sources_count, method, method_p0, method_p1, freshness }
 *   reviews: { review_count, source, verified }
 *   specs:   { verified_pct, citation_count }
 *
 * The sheet used to type the legs as string[] and `.map` the value, so
 * every tap on a live payload threw mid-render. This adapter turns the
 * CURRENT dict shape into 1-3 readable, localized lines — and it belongs
 * to the APP, not the backend payload: the app is bilingual EN/AR (the
 * backend has no locale in scope), and every persisted schema_version=2
 * row already carries the dict shape, so history/share replay hands the
 * client dicts forever regardless of any future backend change.
 *
 * Contract:
 *  - string[] value → returned unchanged (legacy path; older payloads and
 *    the existing sheet tests render verbatim, byte-identical).
 *  - plain-object value → composed lines via t(), skipping null/undefined/
 *    zero-where-meaningless fields, capped at 3.
 *  - anything else (null, undefined, string, number, missing) → [] — an
 *    honest empty sheet, never a throw.
 *
 * Rule #2 (no backend internals): `method` is mapped to human labels
 * (retailer_verified/converted) or omitted; `method_p0`/`method_p1` are
 * internal source_method enums (page_scrape_jsonld, converted_usd, …) and
 * are ALWAYS omitted; no thresholds/percentages/coefficients are printed.
 */

import type { ConfidenceDetails } from '../../types/types';

export type ConfidenceLegKey = 'price' | 'reviews' | 'specs';

type Translate = (key: string, params?: Record<string, unknown>) => string;

const MAX_LINES = 3;

function isPositiveNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v) && v > 0;
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

function priceLines(d: Record<string, unknown>, t: Translate): string[] {
  const lines: string[] = [];
  if (isPositiveNumber(d.sources_count)) {
    lines.push(t('results.confidence.sheet.price.sources', { n: d.sources_count }));
  }
  // Human labels only — anything unmapped (incl. 'estimated') is omitted:
  // the sheet exists to say what we KNOW, and 'estimated' is forbidden
  // vocab in user-facing copy (copy-policy scary_vocab).
  if (d.method === 'retailer_verified') {
    lines.push(t('results.confidence.sheet.price.method_retailer'));
  } else if (d.method === 'converted') {
    lines.push(t('results.confidence.sheet.price.method_converted'));
  }
  if (d.freshness === 'live') {
    lines.push(t('results.confidence.sheet.price.freshness_live'));
  } else if (d.freshness === 'cached') {
    lines.push(t('results.confidence.sheet.price.freshness_cached'));
  }
  return lines;
}

function reviewsLines(d: Record<string, unknown>, t: Translate): string[] {
  const lines: string[] = [];
  if (isPositiveNumber(d.review_count)) {
    lines.push(t('results.confidence.sheet.reviews.count', { n: d.review_count }));
  }
  if (isNonEmptyString(d.source)) {
    lines.push(t('results.confidence.sheet.reviews.source', { source: d.source }));
  }
  if (d.verified === true) {
    lines.push(t('results.confidence.sheet.reviews.verified'));
  }
  return lines;
}

function specsLines(d: Record<string, unknown>, t: Translate): string[] {
  const lines: string[] = [];
  if (isPositiveNumber(d.citation_count)) {
    lines.push(t('results.confidence.sheet.specs.citations', { n: d.citation_count }));
  }
  // verified_pct stays qualitative — printing "60%" would leak a
  // threshold-shaped number (rule #2 guard regex forbids \d+%).
  if (isPositiveNumber(d.verified_pct)) {
    lines.push(t('results.confidence.sheet.specs.verified'));
  }
  return lines;
}

export function toConfidenceLines(
  leg: ConfidenceLegKey,
  details: ConfidenceDetails | null | undefined,
  t: Translate
): string[] {
  const value =
    details && typeof details === 'object' && !Array.isArray(details)
      ? (details as Record<string, unknown>)[leg]
      : undefined;

  // Legacy path — a string[] renders verbatim, unchanged.
  if (Array.isArray(value)) return value;

  // Live dict shape.
  if (value !== null && typeof value === 'object') {
    const d = value as Record<string, unknown>;
    let lines: string[];
    if (leg === 'price') lines = priceLines(d, t);
    else if (leg === 'reviews') lines = reviewsLines(d, t);
    else lines = specsLines(d, t);
    return lines.slice(0, MAX_LINES);
  }

  // Anything else (null, undefined, string, number) → honest empty sheet.
  return [];
}

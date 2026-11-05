/**
 * S81-11 D20 -- the pure readers of metadata.field_status /
 * metadata.section_status / price.as_of (R-G3-6, B1, R-G4-2) and the owner's
 * staleness rule. Absent keys = 'none' (today's rendering).
 */
import { applyDigitSystem, toAsciiDigits } from '../utils/formatNumber';

export const HONEST_PRICE_FRESH_HOURS_CONVERTED = 24;
export const HONEST_PRICE_FRESH_DAYS_GENUINE = 7;
export const HONEST_PRICE_MAX_AGE_DAYS = 30;

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;

export type FieldStateView = 'known' | 'unknown';

export type PriceProvenance =
  | { kind: 'none' }
  | { kind: 'fresh'; store: string | null; dateIso: string }
  | { kind: 'stale'; store: string | null; dateIso: string }
  | { kind: 'listed'; store: string | null; dateIso: string }
  | { kind: 'staleNoDate'; store: string | null }
  | { kind: 'unknown' };

function isPlainObject(v: unknown): v is Record<string, any> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

export function productFieldStatus(metadata: unknown, index: 0 | 1): Record<string, any> | null {
  if (!isPlainObject(metadata)) return null;
  const list = metadata.field_status;
  if (!Array.isArray(list)) return null;
  const entry = list[index];
  return isPlainObject(entry) ? entry : null;
}

export function isFieldUnknown(entry: unknown): boolean {
  return isPlainObject(entry) && entry.state === 'unknown';
}

function validDate(v: unknown): string | null {
  return typeof v === 'string' && !Number.isNaN(Date.parse(v)) ? v : null;
}

export function priceProvenance(
  price: unknown,
  fieldPrice: unknown,
  nowMs: number,
  origin: 'live' | 'stored' = 'live',
): PriceProvenance {
  const fp = isPlainObject(fieldPrice) ? fieldPrice : null;
  const fieldUnknown = fp !== null && fp.state === 'unknown';
  if (!isPlainObject(price)) return fieldUnknown ? { kind: 'unknown' } : { kind: 'none' };
  if (price.estimated === true || price.source_method === 'estimated') {
    // R-S11-12: an estimate is a model guess, never a listed price.
    return fieldUnknown ? { kind: 'unknown' } : { kind: 'none' };
  }
  if (price.unavailable === true) return fieldUnknown ? { kind: 'unknown' } : { kind: 'none' };
  if (typeof price.amount !== 'number' || !Number.isFinite(price.amount)) {
    return fieldUnknown ? { kind: 'unknown' } : { kind: 'none' };
  }
  const store =
    typeof price.retailer === 'string' && price.retailer.trim() !== '' ? price.retailer.trim() : null;
  const dateIso = validDate(price.as_of) ?? (fp ? validDate(fp.as_of) : null);
  if (!dateIso) {
    if (origin === 'live' && fp !== null && fp.state === 'stale') return { kind: 'staleNoDate', store };
    return { kind: 'none' };
  }
  if (origin === 'stored') return { kind: 'listed', store, dateIso };
  const age = Math.max(0, nowMs - Date.parse(dateIso));
  const window =
    price.source_method === 'converted_usd'
      ? HONEST_PRICE_FRESH_HOURS_CONVERTED * HOUR_MS
      : HONEST_PRICE_FRESH_DAYS_GENUINE * DAY_MS;
  if (age <= window) return { kind: 'fresh', store, dateIso };
  if (age <= HONEST_PRICE_MAX_AGE_DAYS * DAY_MS) return { kind: 'stale', store, dateIso };
  return { kind: 'unknown' };
}

export function sectionNeedsHonestLine(
  metadata: unknown,
  key: 'specs' | 'reviews' | 'pros_cons',
): boolean {
  if (!isPlainObject(metadata)) return false;
  const ss = metadata.section_status;
  if (!isPlainObject(ss)) return false;
  return ss[key] === 'unavailable';
}

/** R-S11-24: the gregorian calendar in both locales; ISO date fallback. */
export function formatAsOfDate(dateIso: string, language: 'en' | 'ar'): string {
  const d = new Date(dateIso);
  try {
    const locale = language === 'ar' ? 'ar-SA-u-ca-gregory' : 'en-US';
    const s = d.toLocaleDateString(locale, { month: 'short', day: 'numeric', calendar: 'gregory' } as any);
    return applyDigitSystem(toAsciiDigits(s));
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

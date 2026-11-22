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

/**
 * INC-C1b T7-11: the "Saved on" date of a stored result. Month, day and the
 * year (a saved result can come from an earlier year), gregorian in both
 * locales, the app's digit policy. '' when Date.parse cannot read `dateIso`
 * (never toISOString on an Invalid Date); the ISO date when the phone's ICU
 * lacks the locale.
 */
export function formatSavedOnDate(dateIso: string, language: 'en' | 'ar'): string {
  const ms = Date.parse(dateIso);
  if (!Number.isFinite(ms)) return '';
  const d = new Date(ms);
  try {
    const locale = language === 'ar' ? 'ar-SA-u-ca-gregory' : 'en-US';
    const s = d.toLocaleDateString(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      calendar: 'gregory',
    } as any);
    return applyDigitSystem(toAsciiDigits(s));
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

/**
 * INC-C1 C1-2: the whole calendar days from the local day of `dateIso` to the
 * local day of `nowMs` (the caller's clock; nothing here reads the device
 * clock). Counted between local starts of day, so 23:50 yesterday is 1 and
 * 00:10 today is 0; Math.round absorbs a 23 h or 25 h daylight-saving day. A
 * date ahead of now (the server allows a few minutes of skew) or an unparsable
 * one clamps to 0, i.e. today.
 */
export function calendarDaysAgo(dateIso: string, nowMs: number): number {
  const startOfDay = (ms: number) => {
    const d = new Date(ms);
    return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  };
  const days = Math.round((startOfDay(nowMs) - startOfDay(Date.parse(dateIso))) / DAY_MS);
  return Number.isFinite(days) && days > 0 ? days : 0;
}

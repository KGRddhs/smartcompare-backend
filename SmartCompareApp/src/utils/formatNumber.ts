/**
 * W3-11 RTL-06 / RTL-07 — one place for digits and prices.
 *
 * Digit policy (Ahmed sign-off item): ONE digit system across everything an
 * Arabic user reads — ASCII `0-9` (`APP_DIGIT_SYSTEM = 'latn'`). Flipping it
 * to 'arab' is NOT a one-constant change: the 35 `{{count}}` catalog
 * families are interpolated by i18next (they would need an interpolation
 * hook in src/i18n/index.ts) and six `toFixed` sites (ratings, whole-dinar
 * savings aggregates) emit ASCII directly — that is a separate unit.
 *
 * `formatNumber` is pure JS on purpose: Hermes' Intl coverage on Android is
 * not measurable from CI, so the jest result IS the device result here.
 * Rounding is `Number.prototype.toFixed` — binary rounding, not half-up:
 * (1.005).toFixed(2) === '1.00', (2.675).toFixed(2) === '2.67'.
 *
 * `formatNumber` returns a STRING. Callers that feed it into an i18next
 * `count` (ResultsAccordion's ratingWithCount) rely on that: a string count
 * keeps its grouping separator, a number count does not.
 */
import { localizedCurrency } from './currencyDisplay';

export type DigitSystem = 'latn' | 'arab';

// Policy pin — changing this is a deliberate, Ahmed-signed edit.
export const APP_DIGIT_SYSTEM: DigitSystem = 'latn';

// ISO 4217 minor units that differ from the default 2.
export const CURRENCY_FRACTION_DIGITS: Record<string, number> = { BHD: 3, KWD: 3, OMR: 3 };

type TranslateFn = (key: string, options?: Record<string, unknown>) => string;

const ARABIC_INDIC_ZERO = 0x0660;
const EXTENDED_ARABIC_INDIC_ZERO = 0x06f0;

/** ٠-٩ (U+0660-0669) and ۰-۹ (U+06F0-06F9) → 0-9. */
export function toAsciiDigits(s: string): string {
  return s.replace(/[٠-٩۰-۹]/g, (ch) => {
    const code = ch.charCodeAt(0);
    const base = code >= EXTENDED_ARABIC_INDIC_ZERO ? EXTENDED_ARABIC_INDIC_ZERO : ARABIC_INDIC_ZERO;
    return String(code - base);
  });
}

/** Identity under 'latn'; 0-9 → ٠-٩ under 'arab'. */
export function applyDigitSystem(s: string): string {
  if ((APP_DIGIT_SYSTEM as DigitSystem) === 'latn') return s;
  return s.replace(/[0-9]/g, (d) => String.fromCharCode(ARABIC_INDIC_ZERO + Number(d)));
}

export function formatNumber(
  n: number,
  opts: { minFraction?: number; maxFraction?: number; grouping?: boolean } = {},
): string {
  const maxFraction = opts.maxFraction ?? 3;
  const minFraction = Math.min(opts.minFraction ?? 0, maxFraction);
  const grouping = opts.grouping ?? true;

  // Callers feed untyped payload fields (ResultsAccordion sums `any`-typed
  // review_count; ResultsContent reads price.amount). The toLocaleString()
  // this replaced tolerated a non-number; toFixed throws a TypeError on one
  // and would crash the render. Coerce ONLY a non-empty numeric string; every
  // other non-number (null, undefined, '', boolean, array, object) renders as
  // String(n) — a bare Number(n) would turn null/''/[] into 0 and true into 1
  // and fabricate a price. Callers keep guarding null.
  const unknownN: unknown = n;
  const value =
    typeof unknownN === 'number'
      ? unknownN
      : typeof unknownN === 'string' && unknownN.trim() !== ''
        ? Number(unknownN)
        : NaN;
  if (!Number.isFinite(value)) return String(n);

  const fixed = value.toFixed(maxFraction);
  const negative = fixed.startsWith('-');
  const unsigned = negative ? fixed.slice(1) : fixed;
  const [intPart, rawFraction = ''] = unsigned.split('.');

  let fraction = rawFraction;
  while (fraction.length > minFraction && fraction.endsWith('0')) {
    fraction = fraction.slice(0, -1);
  }

  const groupedInt = grouping ? intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',') : intPart;
  const out = `${negative ? '-' : ''}${groupedInt}${fraction ? `.${fraction}` : ''}`;
  return applyDigitSystem(out);
}

/**
 * Amount first, then the localized currency symbol, in BOTH languages, with
 * the currency's minor-unit width: formatPrice(12.345, 'BHD', t) under ar →
 * '12.345 د.ب'; formatPrice(329, 'BHD', t) under en → '329.000 BHD'.
 * `localizedCurrency` stays the symbol resolver (uncatalogued codes fall
 * back to the raw ISO code).
 */
export function formatPrice(amount: number, currencyCode: string, t: TranslateFn): string {
  const digits = CURRENCY_FRACTION_DIGITS[currencyCode] ?? 2;
  const number = formatNumber(amount, { minFraction: digits, maxFraction: digits });
  return `${number} ${localizedCurrency(currencyCode, t)}`;
}

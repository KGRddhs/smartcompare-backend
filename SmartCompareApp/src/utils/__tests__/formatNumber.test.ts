/**
 * W3-11bcd — MB-I18N-RTL-07: prices render amount-then-symbol with the ISO
 * minor unit (BHD/KWD/OMR = 3 decimals, everything else = 2), in BOTH
 * languages, through ONE helper.
 *
 * Measured at base b63a8368 (real catalogs, lng='ar'): the live Results
 * site renders 12.345 BHD as "د.ب 12.345" (symbol first, device-locale
 * digits, no fixed width: 329 → "BHD 329"); the Home smart-pick sites
 * truncate to whole dinars ("12 د.ب"). The finding's target strings are
 * '12.345 د.ب' and '12.50 ر.س'. `localizedCurrency` stays the symbol
 * resolver (its uncatalogued-code fallback is preserved).
 *
 * formatPrice takes (amount, code, t) — the finding's 4th `language`
 * parameter is dropped because digits follow the module-level
 * APP_DIGIT_SYSTEM policy (spec R13.3).
 */
import { createInstance } from 'i18next';
import en from '../../i18n/en.json';
import ar from '../../i18n/ar.json';
import { CURRENCY_FRACTION_DIGITS, formatNumber, formatPrice } from '../formatNumber';

const inst = createInstance();

beforeAll(async () => {
  await inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: {
      en: { translation: en },
      ar: { translation: ar },
    },
    interpolation: { escapeValue: false },
  });
});

describe('formatPrice — Arabic', () => {
  it('BHD keeps its 3 decimals, amount first, then the Arabic symbol', async () => {
    await inst.changeLanguage('ar');
    expect(formatPrice(12.345, 'BHD', inst.t)).toBe('12.345 د.ب');
  });

  it('SAR is 2 decimals, zero-padded', async () => {
    await inst.changeLanguage('ar');
    expect(formatPrice(12.5, 'SAR', inst.t)).toBe('12.50 ر.س');
  });

  it('KWD is 3 decimals, zero-padded', async () => {
    await inst.changeLanguage('ar');
    expect(formatPrice(8.75, 'KWD', inst.t)).toBe('8.750 د.ك');
  });

  it('OMR is 3 decimals, zero-padded (the third ISO 3-decimal GCC currency)', async () => {
    await inst.changeLanguage('ar');
    expect(formatPrice(3.5, 'OMR', inst.t)).toBe('3.500 ر.ع');
  });
});

describe('CURRENCY_FRACTION_DIGITS — the ISO 4217 3-decimal set', () => {
  it('is exactly BHD, KWD and OMR (everything else defaults to 2)', () => {
    expect(CURRENCY_FRACTION_DIGITS).toEqual({ BHD: 3, KWD: 3, OMR: 3 });
  });
});

describe('formatNumber on untyped payload values (hardening)', () => {
  // The toLocaleString() calls this helper replaced never threw on a
  // non-number; toFixed does. ResultsAccordion sums `any`-typed review_count
  // and ResultsContent formats price.amount, so a numeric STRING from the
  // wire must format, and garbage must render as itself, never crash.
  it('formats a numeric string like the number', () => {
    expect(formatNumber('1234' as unknown as number)).toBe('1,234');
  });

  it('returns a non-numeric value as-is instead of throwing', () => {
    expect(() => formatNumber('n/a' as unknown as number)).not.toThrow();
    expect(formatNumber('n/a' as unknown as number)).toBe('n/a');
  });

  // Only a NON-EMPTY numeric string is coerced. A bare Number(n) would turn
  // null / '' / [] into 0 and true into 1 and print a price that looks real
  // ("0.000 BHD", "1.000 BHD"); every other non-number renders as String(n).
  it.each<[string, unknown, string]>([
    ['null', null, 'null BHD'],
    ['undefined', undefined, 'undefined BHD'],
    ["''", '', ' BHD'],
    ['[]', [], ' BHD'],
    ['true', true, 'true BHD'],
  ])('formatPrice(%s) fabricates no digits', async (_label, input, expected) => {
    await inst.changeLanguage('en');
    expect(formatPrice(input as number, 'BHD', inst.t)).toBe(expected);
  });
});

describe('formatPrice — English', () => {
  it('BHD renders amount-first with the fixed minor-unit width', async () => {
    await inst.changeLanguage('en');
    expect(formatPrice(329, 'BHD', inst.t)).toBe('329.000 BHD');
  });

  it('groups thousands', async () => {
    await inst.changeLanguage('en');
    expect(formatPrice(1234.5, 'BHD', inst.t)).toBe('1,234.500 BHD');
  });

  it('an uncatalogued code keeps the localizedCurrency raw-code fallback, 2 decimals', async () => {
    await inst.changeLanguage('en');
    expect(formatPrice(9.99, 'EUR', inst.t)).toBe('9.99 EUR');
  });
});

describe('formatNumber feeding an i18next count (spec R10)', () => {
  it('returns a STRING, so ratingWithCount keeps its grouping separator', async () => {
    // ResultsAccordion.tsx:664 passes `count` into
    // results.reviews.ratingWithCount, which has no plural family. Measured
    // on i18next 26.1.0: a NUMBER count renders "1234", a STRING "1,234".
    await inst.changeLanguage('ar');
    const count = formatNumber(1234);
    expect(typeof count).toBe('string');
    expect(inst.t('results.reviews.ratingWithCount', { rating: '4.5', count })).toBe(
      '4.5 · 1,234 تقييم',
    );
  });
});

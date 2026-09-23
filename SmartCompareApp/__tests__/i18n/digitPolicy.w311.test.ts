/**
 * W3-11bcd — MB-I18N-RTL-06 (digit policy) + RTL-14(f) (one percent glyph).
 *
 * Policy (spec §4.2, Ahmed sign-off item): ONE digit system across
 * everything an Arabic user reads — ASCII `0-9` (`APP_DIGIT_SYSTEM = 'latn'`).
 * Measured at base b63a8368: 32 ar.json values carry Arabic-Indic digits vs
 * 21 carry ASCII; `formatDate(…,'ar')` prints Arabic-Indic ("١١ سبتمبر")
 * while `formatTimeAgo(…,'ar')` prints ASCII ("منذ 5 دقيقة"); 4 values use
 * `٪` (U+066A) and 2 use ASCII `%`.
 *
 * `src/utils/formatNumber` does not exist at base, so it is required lazily
 * inside the tests that need it: the catalog fences below then report their
 * own measured red reason instead of the whole suite dying on import.
 */
import i18next from 'i18next';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import { formatDate, formatTimeAgo } from '../../src/utils/formatDate';

const AR = ar as Record<string, string>;
const ARABIC_INDIC = /[٠-٩۰-۹]/;
const ARABIC_PERCENT = '٪';

function loadFormatNumber(): any {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  return require('../../src/utils/formatNumber');
}

const inst = i18next.createInstance();

beforeAll(async () => {
  await inst.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
  });
});

describe('W3-11 RTL-06 (a) — the digit policy and the ar.json catalog fence', () => {
  it('APP_DIGIT_SYSTEM is latn (policy pin — changing it is a deliberate, Ahmed-signed edit)', () => {
    // Spec R8(b): a standalone pin, NOT a branch the fence reads back. Per
    // R7, flipping to 'arab' is NOT a one-constant change (it also needs an
    // i18next interpolation hook for the {{count}} families and routing the
    // unrouted toFixed sites) — that is a separate unit.
    expect(loadFormatNumber().APP_DIGIT_SYSTEM).toBe('latn');
  });

  it('no ar.json value contains an Arabic-Indic digit (U+0660-0669, U+06F0-06F9)', () => {
    const offenders = Object.entries(AR)
      .filter(([, v]) => ARABIC_INDIC.test(v))
      .map(([k, v]) => `${k} = ${JSON.stringify(v)}`);
    expect(offenders).toEqual([]);
  });
});

describe('W3-11 RTL-06 (b) — dates and relative times obey the same digit class', () => {
  it('toAsciiDigits maps Arabic-Indic and extended Arabic-Indic digits to ASCII', () => {
    const { toAsciiDigits } = loadFormatNumber();
    expect(toAsciiDigits('١١ سبتمبر')).toBe('11 سبتمبر');
    expect(toAsciiDigits('٠١٢٣٤٥٦٧٨٩')).toBe('0123456789');
    expect(toAsciiDigits('۰۱۲۳۴۵۶۷۸۹')).toBe('0123456789');
  });

  it("formatDate(…, 'ar') starts with an ASCII digit and carries no Arabic-Indic digit", () => {
    // R9: engine-independent facts only — no literal day number, no month
    // word (CI runs node 20; this box runs node 24 / ICU 77.1).
    const out = formatDate(new Date(Date.UTC(2026, 8, 11, 12)), 'ar');
    expect(out).toMatch(/^[0-9]/);
    expect(out).not.toMatch(ARABIC_INDIC);
  });

  it("formatDate(…, 'ar') and formatTimeAgo(…, 'ar', t) report the same digit class", () => {
    const dateOut = formatDate(new Date(Date.UTC(2026, 8, 11, 12)), 'ar');
    const now = Date.now();
    // Three-argument call: `t` is the parameter the fix adds (spec §4.5).
    const agoOut = formatTimeAgo(new Date(now - 5 * 60_000), 'ar', inst.t);
    const digitClass = (s: string) => ({ ascii: /[0-9]/.test(s), arabicIndic: ARABIC_INDIC.test(s) });
    expect(digitClass(dateOut)).toEqual({ ascii: true, arabicIndic: false });
    expect(digitClass(agoOut)).toEqual({ ascii: true, arabicIndic: false });
  });
});

describe('W3-11 RTL-06 (c) — formatNumber (pure JS, deterministic across engines)', () => {
  it('fixed fraction width + comma grouping', () => {
    const { formatNumber } = loadFormatNumber();
    expect(formatNumber(1234.5, { minFraction: 3, maxFraction: 3 })).toBe('1,234.500');
    expect(formatNumber(1234567)).toBe('1,234,567');
  });

  it('rounds with Number.prototype.toFixed semantics (0.5 → "1"; binary rounding, not half-up)', () => {
    const { formatNumber } = loadFormatNumber();
    expect(formatNumber(0.5, { maxFraction: 0 })).toBe('1');
  });
});

describe('W3-11 RTL-14(f) — one percent glyph in ar.json', () => {
  it('ar.json uses ASCII "%" only — zero U+066A under the latn policy, never both glyphs', () => {
    const arabicPct = Object.entries(AR).filter(([, v]) => v.includes(ARABIC_PERCENT)).map(([k]) => k);
    const asciiPct = Object.entries(AR).filter(([, v]) => v.includes('%')).map(([k]) => k);
    expect({ arabicPct, mixed: arabicPct.length > 0 && asciiPct.length > 0 }).toEqual({
      arabicPct: [],
      mixed: false,
    });
  });
});

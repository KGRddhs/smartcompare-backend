/**
 * W4-14 (`PO-CATEGORIES-I18N-10`, CHANGED by #175 W3-11bcd) — one digit system for
 * money and counts under lng='ar', across Results, History and Home.
 *
 * The finding's red claim ("a price string under lng=ar mixes numeral systems
 * between Results and History") is GREEN at the unit base: #175 put every price
 * through `formatPrice` with the `latn` digit policy, and the History price the
 * finding compared against was dead code. These rows PIN the property so it
 * cannot regress. REAL i18next + REAL catalogs.
 *
 * PIN = green at the unit base 3985eaac and must stay green.
 */
import * as fs from 'fs';
import * as path from 'path';
import i18next from 'i18next';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import { formatPrice } from '../../src/utils/formatNumber';

const ARABIC_INDIC = /[٠-٩۰-۹]/;
const ASCII_DIGIT = /[0-9]/;

function arT() {
  const inst = i18next.createInstance();
  inst.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  } as any);
  return inst.t.bind(inst) as any;
}

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) {
      if (name === '__tests__' || name === 'node_modules') continue;
      walk(p, acc);
    } else if (/\.(ts|tsx|js|jsx)$/.test(name)) {
      acc.push(p);
    }
  }
  return acc;
}

function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .map((line) => line.replace(/(^|[^:'"`])\/\/.*$/, '$1'))
    .join('\n');
}

describe('W4-14 price / count digits under lng=ar', () => {
  it('PIN 13: Results price, History hero savings, History count and Home savings count carry one digit class (ASCII, no U+0660-0669/U+06F0-06F9)', () => {
    const t = arT();
    const strings = {
      resultsPrice: formatPrice(12.345, 'BHD', t),
      historySavings: t('history.hero.savings', { amount: (12.345).toFixed(0) }),
      historyCount: t('history.hero.count', { count: 12 }),
      homeSavings: t('home.savings.count', { count: 12 }),
    };
    for (const [name, s] of Object.entries(strings)) {
      expect({ name, ascii: ASCII_DIGIT.test(s), arabicIndic: ARABIC_INDIC.test(s) }).toEqual({
        name,
        ascii: true,
        arabicIndic: false,
      });
    }
  });

  it("PIN 14: formatPrice(12.345,'BHD',t_ar) and formatPrice(250,'SAR',t_ar) are the latn-digit Arabic strings", () => {
    const t = arT();
    expect(formatPrice(12.345, 'BHD', t)).toBe('12.345 د.ب');
    expect(formatPrice(250, 'SAR', t)).toBe('250.00 ر.س');
  });

  it('PIN 15: every toLocaleString( call in src/ code (comments stripped, src/**/__tests__/ excluded) passes an explicit locale argument', () => {
    const root = path.join(__dirname, '..', '..', 'src');
    const sites: { file: string; arg: string }[] = [];
    for (const f of walk(root)) {
      const code = stripComments(fs.readFileSync(f, 'utf-8'));
      const rx = /\.toLocaleString\(\s*([^)]*)\)/g;
      let m: RegExpExecArray | null;
      // eslint-disable-next-line no-cond-assign
      while ((m = rx.exec(code))) {
        sites.push({ file: path.relative(root, f).replace(/\\/g, '/'), arg: m[1].trim() });
      }
    }
    // Non-vacuous: the two measured code sites (LoadingRings, StatBlock), both 'en-US'.
    expect(sites.length).toBeGreaterThanOrEqual(2);
    const noLocale = sites.filter((s) => !/^['"`]/.test(s.arg));
    expect(noLocale).toEqual([]);
  });
});
